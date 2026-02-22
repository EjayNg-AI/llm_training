"""Pack token shards into fixed-length train/val block streams."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
from typing import Any

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from llm_training.infra.hashing import sha256_file, sha256_text, stable_hash_object
from llm_training.infra.io_atomic import atomic_dump_json, atomic_write_bytes
from llm_training.infra.logging import setup_logger
from llm_training.infra.manifest import (
    build_artifact_manifest,
    collect_checksums,
    find_artifact,
    latest_artifact,
    publish_artifact,
    resolve_artifact_dir,
)
from llm_training.infra.resume import assert_resume_compatible
from llm_training.infra.run_dir import begin_run, end_run, make_run_context, write_stage_metric, write_state

from pipeline_common import load_artifact_manifest_from_entry, load_yaml_config


DEFAULT_CONFIG: dict[str, Any] = {
    "run": {
        "output_dir": "artifacts/runs/05_pack_sequences",
        "log_level": "INFO",
        "structured_logs": True,
    },
    "artifacts_root": "artifacts",
    "input": {
        "token_shards_id": None,
    },
    "packing": {
        "seq_len": 256,
        "split_mod": 10,
        "val_remainder": 0,
        "artifact_id": None,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/pack.yaml", help="Path to pack stage config YAML.")
    parser.add_argument("--run-id", default=None, help="Optional run identifier under run.output_dir.")
    parser.add_argument("--resume", action="store_true", help="Reuse completed run state when compatible.")
    parser.add_argument("--token-shards-id", default=None, help="Input token shards artifact id.")
    return parser.parse_args()


def _read_token_stream(path: Path, token_dtype: str) -> list[int]:
    if token_dtype == "uint16":
        fmt = "<H"
        width = 2
    elif token_dtype == "uint32":
        fmt = "<I"
        width = 4
    else:
        raise ValueError(f"Unsupported token dtype: {token_dtype}")

    raw = path.read_bytes()
    if len(raw) % width != 0:
        raise ValueError(f"Corrupt token stream length for dtype {token_dtype}: {path}")
    return [item[0] for item in struct.iter_unpack(fmt, raw)]


def _pack_tokens(tokens: list[int], token_dtype: str) -> bytes:
    if token_dtype == "uint16":
        fmt = "<H"
        max_allowed = 65535
    else:
        fmt = "<I"
        max_allowed = 4294967295
    buf = bytearray()
    for token in tokens:
        if token < 0 or token > max_allowed:
            raise ValueError(f"Token id {token} does not fit {token_dtype}")
        buf.extend(struct.pack(fmt, token))
    return bytes(buf)


def _split_name(doc_id: str, split_mod: int, val_remainder: int) -> str:
    bucket = int(sha256_text(doc_id)[:8], 16) % split_mod
    return "val" if bucket == val_remainder else "train"


def _packed(tokens: list[int], seq_len: int) -> tuple[list[int], int]:
    blocks = len(tokens) // seq_len
    kept = blocks * seq_len
    return tokens[:kept], blocks


def main() -> None:
    args = parse_args()
    cfg, cfg_path = load_yaml_config(args.config, DEFAULT_CONFIG)

    run_ctx = make_run_context(
        stage_name="05_pack_sequences",
        run_output_dir=Path(cfg["run"]["output_dir"]),
        config={k: v for k, v in cfg.items() if k != "meta"},
        run_id=args.run_id,
    )

    if not args.resume and run_ctx.run_dir.exists() and any(run_ctx.run_dir.iterdir()):
        raise FileExistsError(
            f"Run directory already exists and is not empty: {run_ctx.run_dir}. "
            "Use --resume or provide a different --run-id."
        )

    logger = setup_logger(
        name="pipeline.05_pack_sequences",
        run_dir=run_ctx.run_dir,
        log_level=cfg["run"]["log_level"],
        structured_logs=bool(cfg["run"]["structured_logs"]),
    )

    artifacts_root = Path(cfg["artifacts_root"])
    registry_path = artifacts_root / "registry.jsonl"

    token_shards_id = args.token_shards_id or cfg["input"].get("token_shards_id")
    if token_shards_id:
        token_entry = find_artifact(registry_path, "tokens", token_shards_id)
        if token_entry is None:
            raise FileNotFoundError(f"Token shards artifact not found: {token_shards_id}")
    else:
        token_entry = latest_artifact(registry_path, "tokens")
        if token_entry is None:
            raise FileNotFoundError("No token shards artifact found in registry")

    token_manifest = load_artifact_manifest_from_entry(token_entry)
    token_artifact_dir = Path(token_entry["artifact_path"])
    token_index_path = token_artifact_dir / "index.json"
    if not token_index_path.exists():
        raise FileNotFoundError(f"Token index missing: {token_index_path}")
    token_index = json.loads(token_index_path.read_text(encoding="utf-8"))

    seq_len = int(cfg["packing"]["seq_len"])
    split_mod = int(cfg["packing"]["split_mod"])
    val_remainder = int(cfg["packing"]["val_remainder"])
    token_dtype = str(token_index["token_dtype"])

    resume_signature = stable_hash_object(
        {
            "config_hash": cfg["meta"]["config_hash"],
            "token_shards_id": token_manifest["artifact_id"],
            "token_checksums": token_manifest.get("checksums", {}),
            "seq_len": seq_len,
            "split_mod": split_mod,
            "val_remainder": val_remainder,
        }
    )
    packed_artifact_id = cfg["packing"].get("artifact_id") or f"packed_{resume_signature[:12]}"
    packed_dir = resolve_artifact_dir(artifacts_root, "packed", packed_artifact_id)

    if args.resume:
        state = assert_resume_compatible(
            state_path=run_ctx.state_path,
            expected_signature=resume_signature,
            signature_field="resume_signature",
        )
        if state.get("status") == "completed" and (packed_dir / "index.json").exists():
            logger.info("Pack stage already completed for run_id=%s; nothing to do.", run_ctx.run_id)
            end_run(
                run_ctx,
                status="completed",
                summary={
                    "artifact_id": state.get("artifact_id"),
                    "reused": True,
                },
            )
            return
    else:
        if packed_dir.exists() and any(packed_dir.iterdir()):
            raise FileExistsError(
                f"Packed artifact already exists: {packed_dir}. "
                "Set packing.artifact_id to a new value if you need a separate output."
            )

    begin_run(
        run_ctx,
        config_path=str(cfg_path.resolve()),
        inputs={
            "token_shards_id": token_manifest["artifact_id"],
            "packed_artifact_id": packed_artifact_id,
        },
    )

    streams: dict[str, list[int]] = {"train": [], "val": []}
    raw_counts: dict[str, int] = {"train": 0, "val": 0}

    shard_entries = token_index.get("shards", [])
    for shard_idx, shard_info in enumerate(shard_entries):
        shard_tokens = _read_token_stream(token_artifact_dir / "shards" / shard_info["name"], token_dtype)
        idx_path = token_artifact_dir / "shards" / shard_info["idx"]
        idx_payload = json.loads(idx_path.read_text(encoding="utf-8"))

        for row in idx_payload["docs"]:
            start = int(row["start"])
            length = int(row["length"])
            doc_tokens = shard_tokens[start : start + length]
            split = _split_name(str(row["doc_id"]), split_mod, val_remainder)
            streams[split].extend(doc_tokens)
            raw_counts[split] += len(doc_tokens)

        write_state(
            run_ctx,
            {
                "resume_signature": resume_signature,
                "artifact_id": packed_artifact_id,
                "status": "running",
                "processed_shards": shard_idx + 1,
                "total_shards": len(shard_entries),
                "raw_train_tokens": raw_counts["train"],
                "raw_val_tokens": raw_counts["val"],
            },
        )

    packed_dir.mkdir(parents=True, exist_ok=True)
    split_meta: dict[str, dict[str, Any]] = {}

    for split in ["train", "val"]:
        split_dir = packed_dir / split / "shards"
        split_dir.mkdir(parents=True, exist_ok=True)

        packed_tokens, blocks = _packed(streams[split], seq_len)
        bin_rel = f"{split}/shards/pack_00000.bin"
        bin_path = packed_dir / bin_rel
        atomic_write_bytes(bin_path, _pack_tokens(packed_tokens, token_dtype))

        split_meta[split] = {
            "raw_tokens": raw_counts[split],
            "packed_tokens": len(packed_tokens),
            "num_blocks": blocks,
            "bin": bin_rel,
            "sha256": sha256_file(bin_path),
        }
        write_stage_metric(
            run_ctx,
            {
                "event": "split_packed",
                "split": split,
                "raw_tokens": raw_counts[split],
                "packed_tokens": len(packed_tokens),
                "num_blocks": blocks,
            },
        )

    index_payload = {
        "schema_version": "1.0",
        "artifact_id": packed_artifact_id,
        "token_shards_id": token_manifest["artifact_id"],
        "seq_len": seq_len,
        "token_dtype": token_dtype,
        "split_mod": split_mod,
        "val_remainder": val_remainder,
        "splits": split_meta,
    }
    atomic_dump_json(packed_dir / "index.json", index_payload)

    checksums = collect_checksums(packed_dir)
    run_meta = json.loads(run_ctx.run_meta_path.read_text(encoding="utf-8"))
    manifest = build_artifact_manifest(
        artifact_type="packed",
        artifact_id=packed_artifact_id,
        source_run_id=run_ctx.run_id,
        config_hash=cfg["meta"]["config_hash"],
        git_commit=run_meta.get("git_commit"),
        inputs=[
            {
                "artifact_type": token_manifest["artifact_type"],
                "artifact_id": token_manifest["artifact_id"],
                "hash": stable_hash_object(token_manifest.get("checksums", {})),
            }
        ],
        stats={
            "seq_len": seq_len,
            "token_dtype": token_dtype,
            "train_blocks": split_meta["train"]["num_blocks"],
            "val_blocks": split_meta["val"]["num_blocks"],
            "train_tokens": split_meta["train"]["packed_tokens"],
            "val_tokens": split_meta["val"]["packed_tokens"],
        },
        checksums=checksums,
    )
    publish_artifact(artifacts_root=artifacts_root, artifact_dir=packed_dir, manifest=manifest)

    write_state(
        run_ctx,
        {
            "resume_signature": resume_signature,
            "status": "completed",
            "artifact_id": packed_artifact_id,
            "train_blocks": split_meta["train"]["num_blocks"],
            "val_blocks": split_meta["val"]["num_blocks"],
        },
    )
    end_run(
        run_ctx,
        status="completed",
        summary={
            "artifact_id": packed_artifact_id,
            "train_blocks": split_meta["train"]["num_blocks"],
            "val_blocks": split_meta["val"]["num_blocks"],
        },
    )
    logger.info(
        "Packing complete. artifact_id=%s train_blocks=%s val_blocks=%s",
        packed_artifact_id,
        split_meta["train"]["num_blocks"],
        split_meta["val"]["num_blocks"],
    )


if __name__ == "__main__":
    main()
