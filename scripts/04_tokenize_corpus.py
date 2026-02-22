"""Tokenize corpus documents into deterministic binary token shards."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import struct
from typing import Any, Iterator

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from llm_training.infra.hashing import sha256_file, stable_hash_object
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
from llm_training.tokenizer import ByteLevelBPETokenizer

from pipeline_common import load_artifact_manifest_from_entry, load_yaml_config


DEFAULT_CONFIG: dict[str, Any] = {
    "run": {
        "output_dir": "artifacts/runs/04_tokenize_corpus",
        "log_level": "INFO",
        "structured_logs": True,
    },
    "artifacts_root": "artifacts",
    "input": {
        "corpus_id": None,
        "tokenizer_id": None,
        "corpus_type": "corpus_dedup",
    },
    "output": {
        "docs_per_shard": 10000,
        "token_dtype": "uint32",
        "append_eos": True,
        "artifact_id": None,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/tokenize.yaml", help="Path to tokenize stage config YAML.")
    parser.add_argument("--run-id", default=None, help="Optional run identifier under run.output_dir.")
    parser.add_argument("--resume", action="store_true", help="Resume tokenization from prior state in run directory.")
    parser.add_argument("--corpus-id", default=None, help="Input corpus artifact id. Overrides config.")
    parser.add_argument("--tokenizer-id", default=None, help="Tokenizer artifact id. Overrides config.")
    return parser.parse_args()


def _read_registry(registry_path: Path) -> list[dict[str, Any]]:
    if not registry_path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in registry_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        out.append(json.loads(line))
    return out


def _resolve_entry(
    *,
    registry_path: Path,
    preferred_type: str,
    artifact_id: str | None,
) -> dict[str, Any]:
    if artifact_id:
        preferred = find_artifact(registry_path, preferred_type, artifact_id)
        if preferred:
            return preferred
        alternate_type = "corpus" if preferred_type == "corpus_dedup" else "corpus_dedup"
        alt = find_artifact(registry_path, alternate_type, artifact_id)
        if alt:
            return alt
        raise FileNotFoundError(f"Artifact id {artifact_id} not found in registry for corpus/corpus_dedup")

    preferred_latest = latest_artifact(registry_path, preferred_type)
    if preferred_latest is not None:
        return preferred_latest

    alternate_type = "corpus" if preferred_type == "corpus_dedup" else "corpus_dedup"
    alt_latest = latest_artifact(registry_path, alternate_type)
    if alt_latest is not None:
        return alt_latest

    raise FileNotFoundError("No corpus artifact found in registry")


def _iter_docs(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            yield json.loads(raw)


def _pack_tokens(tokens: list[int], token_dtype: str) -> bytes:
    if token_dtype == "uint16":
        max_allowed = 65535
        fmt = "<H"
    elif token_dtype == "uint32":
        max_allowed = 4294967295
        fmt = "<I"
    else:
        raise ValueError("output.token_dtype must be uint16 or uint32")

    buf = bytearray()
    for token in tokens:
        if token < 0 or token > max_allowed:
            raise ValueError(f"Token id {token} does not fit dtype {token_dtype}")
        buf.extend(struct.pack(fmt, token))
    return bytes(buf)


def _docs_file_from_manifest(manifest: dict[str, Any]) -> str:
    stats = manifest.get("stats", {})
    if "docs_file" in stats:
        return str(stats["docs_file"])
    raise KeyError("Input corpus manifest stats.docs_file is required")


def main() -> None:
    args = parse_args()
    cfg, cfg_path = load_yaml_config(args.config, DEFAULT_CONFIG)

    run_ctx = make_run_context(
        stage_name="04_tokenize_corpus",
        run_output_dir=Path(cfg["run"]["output_dir"]),
        config={k: v for k, v in cfg.items() if k != "meta"},
        run_id=args.run_id,
    )

    if args.resume:
        if not run_ctx.run_dir.exists():
            raise FileNotFoundError(f"Run directory does not exist for resume: {run_ctx.run_dir}")
    else:
        if run_ctx.run_dir.exists() and any(run_ctx.run_dir.iterdir()):
            raise FileExistsError(
                f"Run directory already exists and is not empty: {run_ctx.run_dir}. "
                "Use --resume or provide a different --run-id."
            )

    logger = setup_logger(
        name="pipeline.04_tokenize_corpus",
        run_dir=run_ctx.run_dir,
        log_level=cfg["run"]["log_level"],
        structured_logs=bool(cfg["run"]["structured_logs"]),
    )

    artifacts_root = Path(cfg["artifacts_root"])
    registry_path = artifacts_root / "registry.jsonl"
    corpus_id = args.corpus_id or cfg["input"].get("corpus_id")
    corpus_entry = _resolve_entry(
        registry_path=registry_path,
        preferred_type=str(cfg["input"]["corpus_type"]),
        artifact_id=corpus_id,
    )
    corpus_manifest = load_artifact_manifest_from_entry(corpus_entry)

    tokenizer_id = args.tokenizer_id or cfg["input"].get("tokenizer_id")
    if tokenizer_id:
        tokenizer_entry = find_artifact(registry_path, "tokenizer", tokenizer_id)
        if tokenizer_entry is None:
            raise FileNotFoundError(f"Tokenizer artifact not found in registry: {tokenizer_id}")
    else:
        tokenizer_entry = latest_artifact(registry_path, "tokenizer")
        if tokenizer_entry is None:
            raise FileNotFoundError("No tokenizer artifact found in registry")
    tokenizer_manifest = load_artifact_manifest_from_entry(tokenizer_entry)

    resume_signature = stable_hash_object(
        {
            "config_hash": cfg["meta"]["config_hash"],
            "corpus_id": corpus_manifest["artifact_id"],
            "corpus_checksums": corpus_manifest.get("checksums", {}),
            "tokenizer_id": tokenizer_manifest["artifact_id"],
            "tokenizer_checksums": tokenizer_manifest.get("checksums", {}),
            "token_dtype": cfg["output"]["token_dtype"],
            "docs_per_shard": int(cfg["output"]["docs_per_shard"]),
            "append_eos": bool(cfg["output"]["append_eos"]),
        }
    )
    token_artifact_id = cfg["output"].get("artifact_id") or f"tokens_{resume_signature[:12]}"
    token_artifact_dir = resolve_artifact_dir(artifacts_root, "tokens", token_artifact_id)
    shards_dir = token_artifact_dir / "shards"

    if args.resume:
        state = assert_resume_compatible(
            state_path=run_ctx.state_path,
            expected_signature=resume_signature,
            signature_field="resume_signature",
        )
        next_doc_index = int(state.get("next_doc_index", 0))
        next_shard_index = int(state.get("next_shard_index", 0))
        shard_summaries = list(state.get("shards", []))
        total_tokens = int(state.get("total_tokens", 0))
    else:
        if token_artifact_dir.exists() and any(token_artifact_dir.iterdir()):
            raise FileExistsError(
                f"Token artifact already exists: {token_artifact_dir}. "
                "Use output.artifact_id to force a different id."
            )
        next_doc_index = 0
        next_shard_index = 0
        shard_summaries: list[dict[str, Any]] = []
        total_tokens = 0

    begin_run(
        run_ctx,
        config_path=str(cfg_path.resolve()),
        inputs={
            "corpus_id": corpus_manifest["artifact_id"],
            "tokenizer_id": tokenizer_manifest["artifact_id"],
            "token_artifact_id": token_artifact_id,
        },
    )

    tokenizer = ByteLevelBPETokenizer.from_dir(Path(tokenizer_entry["artifact_path"]))
    eos_id = tokenizer.special_token_ids.eos
    append_eos = bool(cfg["output"]["append_eos"])
    token_dtype = str(cfg["output"]["token_dtype"])
    docs_per_shard = int(cfg["output"]["docs_per_shard"])

    corpus_docs_path = Path(corpus_entry["artifact_path"]) / _docs_file_from_manifest(corpus_manifest)
    if not corpus_docs_path.exists():
        raise FileNotFoundError(f"Corpus docs file missing: {corpus_docs_path}")

    token_artifact_dir.mkdir(parents=True, exist_ok=True)
    shards_dir.mkdir(parents=True, exist_ok=True)

    processed_docs = next_doc_index

    current_tokens: list[int] = []
    current_idx_rows: list[dict[str, Any]] = []

    def flush_shard(shard_idx: int) -> dict[str, Any] | None:
        nonlocal current_tokens, current_idx_rows, total_tokens
        if not current_idx_rows:
            return None
        shard_name = f"tokens_shard_{shard_idx:05d}.bin"
        idx_name = f"tokens_shard_{shard_idx:05d}.idx.json"
        shard_path = shards_dir / shard_name
        idx_path = shards_dir / idx_name

        atomic_write_bytes(shard_path, _pack_tokens(current_tokens, token_dtype))
        idx_payload = {
            "schema_version": "1.0",
            "token_dtype": token_dtype,
            "shard": shard_name,
            "num_docs": len(current_idx_rows),
            "num_tokens": len(current_tokens),
            "docs": current_idx_rows,
        }
        atomic_dump_json(idx_path, idx_payload)

        summary = {
            "name": shard_name,
            "idx": idx_name,
            "num_docs": len(current_idx_rows),
            "num_tokens": len(current_tokens),
            "sha256": sha256_file(shard_path),
            "idx_sha256": sha256_file(idx_path),
        }
        total_tokens += len(current_tokens)
        current_tokens = []
        current_idx_rows = []
        return summary

    for doc_index, doc in enumerate(_iter_docs(corpus_docs_path)):
        if doc_index < next_doc_index:
            continue

        text = str(doc.get("text", ""))
        token_ids = tokenizer.encode(text)
        eos_appended = False
        if append_eos and eos_id is not None:
            token_ids.append(eos_id)
            eos_appended = True

        start = len(current_tokens)
        current_tokens.extend(token_ids)
        current_idx_rows.append(
            {
                "doc_id": doc.get("doc_id"),
                "start": start,
                "length": len(token_ids),
                "eos_appended": eos_appended,
            }
        )

        processed_docs += 1
        if len(current_idx_rows) >= docs_per_shard:
            summary = flush_shard(next_shard_index)
            if summary is not None:
                shard_summaries.append(summary)
                next_shard_index += 1
            write_state(
                run_ctx,
                {
                    "resume_signature": resume_signature,
                    "artifact_id": token_artifact_id,
                    "next_doc_index": processed_docs,
                    "next_shard_index": next_shard_index,
                    "processed_docs": processed_docs,
                    "total_tokens": total_tokens,
                    "shards": shard_summaries,
                },
            )
            write_stage_metric(
                run_ctx,
                {
                    "event": "shard_committed",
                    "artifact_id": token_artifact_id,
                    "shard_index": next_shard_index - 1,
                    "processed_docs": processed_docs,
                    "total_tokens": total_tokens,
                },
            )

    summary = flush_shard(next_shard_index)
    if summary is not None:
        shard_summaries.append(summary)
        next_shard_index += 1

    index_payload = {
        "schema_version": "1.0",
        "artifact_id": token_artifact_id,
        "tokenizer_id": tokenizer_manifest["artifact_id"],
        "corpus_id": corpus_manifest["artifact_id"],
        "token_dtype": token_dtype,
        "docs_per_shard": docs_per_shard,
        "append_eos": append_eos,
        "total_docs": processed_docs,
        "total_tokens": total_tokens,
        "shards": shard_summaries,
    }
    atomic_dump_json(token_artifact_dir / "index.json", index_payload)

    checksums = collect_checksums(token_artifact_dir)
    run_meta = json.loads(run_ctx.run_meta_path.read_text(encoding="utf-8"))
    manifest = build_artifact_manifest(
        artifact_type="tokens",
        artifact_id=token_artifact_id,
        source_run_id=run_ctx.run_id,
        config_hash=cfg["meta"]["config_hash"],
        git_commit=run_meta.get("git_commit"),
        inputs=[
            {
                "artifact_type": corpus_manifest["artifact_type"],
                "artifact_id": corpus_manifest["artifact_id"],
                "hash": stable_hash_object(corpus_manifest.get("checksums", {})),
            },
            {
                "artifact_type": tokenizer_manifest["artifact_type"],
                "artifact_id": tokenizer_manifest["artifact_id"],
                "hash": stable_hash_object(tokenizer_manifest.get("checksums", {})),
            },
        ],
        stats={
            "token_dtype": token_dtype,
            "docs_per_shard": docs_per_shard,
            "append_eos": append_eos,
            "total_docs": processed_docs,
            "total_tokens": total_tokens,
            "num_shards": len(shard_summaries),
        },
        checksums=checksums,
    )
    publish_artifact(artifacts_root=artifacts_root, artifact_dir=token_artifact_dir, manifest=manifest)

    write_state(
        run_ctx,
        {
            "resume_signature": resume_signature,
            "artifact_id": token_artifact_id,
            "status": "completed",
            "next_doc_index": processed_docs,
            "next_shard_index": next_shard_index,
            "processed_docs": processed_docs,
            "total_tokens": total_tokens,
            "shards": shard_summaries,
        },
    )
    end_run(
        run_ctx,
        status="completed",
        summary={
            "artifact_id": token_artifact_id,
            "total_docs": processed_docs,
            "total_tokens": total_tokens,
            "num_shards": len(shard_summaries),
        },
    )
    logger.info(
        "Tokenization complete. artifact_id=%s docs=%s tokens=%s shards=%s",
        token_artifact_id,
        processed_docs,
        total_tokens,
        len(shard_summaries),
    )


if __name__ == "__main__":
    main()
