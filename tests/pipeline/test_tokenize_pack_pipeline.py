from __future__ import annotations

import gzip
import json
from pathlib import Path
import subprocess
import sys

import yaml

from llm_training.infra.manifest import build_artifact_manifest, collect_checksums, publish_artifact, resolve_artifact_dir


ROOT = Path(__file__).resolve().parents[2]


def _bytes_to_unicode() -> dict[int, str]:
    bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(bs, cs)}


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=ROOT)


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _publish_identity_tokenizer(artifacts_root: Path, tokenizer_id: str) -> None:
    export_dir = resolve_artifact_dir(artifacts_root, "tokenizer", tokenizer_id)
    export_dir.mkdir(parents=True, exist_ok=True)

    byte_to_unicode = _bytes_to_unicode()
    vocab = {byte_to_unicode[b]: b for b in range(256)}
    vocab["<|endoftext|>"] = 256
    vocab["<|pad|>"] = 257

    (export_dir / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
    (export_dir / "merges.txt").write_text("#version: 0.2\n", encoding="utf-8")
    (export_dir / "tokenizer_config.json").write_text(
        json.dumps(
            {
                "pattern": r"[\s\S]+",
                "pattern_flags": 0,
                "special_tokens": ["<|endoftext|>", "<|pad|>"],
                "vocab_size": len(vocab),
                "num_merges": 0,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (export_dir / "special_tokens_map.json").write_text(
        json.dumps(
            {
                "bos_token": "<|endoftext|>",
                "eos_token": "<|endoftext|>",
                "unk_token": "<|endoftext|>",
                "pad_token": "<|pad|>",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    checksums = collect_checksums(export_dir)
    manifest = build_artifact_manifest(
        artifact_type="tokenizer",
        artifact_id=tokenizer_id,
        source_run_id="test_run",
        config_hash="test_cfg",
        git_commit="test",
        inputs=[],
        stats={"vocab_size": len(vocab), "num_merges": 0},
        checksums=checksums,
    )
    publish_artifact(artifacts_root=artifacts_root, artifact_dir=export_dir, manifest=manifest)


def test_corpus_to_pack_pipeline_with_artifact_registry(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    data_root = tmp_path / "data" / "raw"
    configs_root = tmp_path / "configs"
    configs_root.mkdir(parents=True, exist_ok=True)
    data_root.mkdir(parents=True, exist_ok=True)

    train_path = data_root / "train.txt"
    val_path = data_root / "validation.txt"
    test_path = data_root / "test.txt"

    train_path.write_text("alpha beta\ngamma\nalpha beta\n", encoding="utf-8")
    val_path.write_text("delta epsilon\n", encoding="utf-8")
    test_path.write_text("zeta eta\n", encoding="utf-8")

    corpus_cfg = {
        "run": {"output_dir": str(tmp_path / "runs" / "corpus"), "structured_logs": False},
        "artifacts_root": str(artifacts_root),
        "data": {
            "input_paths": [str(train_path), str(val_path), str(test_path)],
            "input_format": "text",
            "decode_errors": "replace",
            "normalize": "none",
            "min_chars": 1,
        },
    }
    dedup_cfg = {
        "run": {"output_dir": str(tmp_path / "runs" / "dedup"), "structured_logs": False},
        "artifacts_root": str(artifacts_root),
    }
    tokenize_cfg = {
        "run": {"output_dir": str(tmp_path / "runs" / "tokenize"), "structured_logs": False},
        "artifacts_root": str(artifacts_root),
        "input": {
            "tokenizer_id": "tok_identity",
            "corpus_type": "corpus_dedup",
        },
        "output": {
            "docs_per_shard": 2,
            "token_dtype": "uint32",
            "append_eos": True,
        },
    }
    pack_cfg = {
        "run": {"output_dir": str(tmp_path / "runs" / "pack"), "structured_logs": False},
        "artifacts_root": str(artifacts_root),
        "packing": {"seq_len": 4, "split_mod": 2, "val_remainder": 0},
    }

    corpus_cfg_path = configs_root / "corpus.yaml"
    dedup_cfg_path = configs_root / "dedup.yaml"
    tokenize_cfg_path = configs_root / "tokenize.yaml"
    pack_cfg_path = configs_root / "pack.yaml"

    _write_yaml(corpus_cfg_path, corpus_cfg)
    _write_yaml(dedup_cfg_path, dedup_cfg)
    _write_yaml(tokenize_cfg_path, tokenize_cfg)
    _write_yaml(pack_cfg_path, pack_cfg)

    _run([sys.executable, "scripts/01_build_corpus.py", "--config", str(corpus_cfg_path), "--run-id", "r1"])
    _run([sys.executable, "scripts/02_dedup_exact.py", "--config", str(dedup_cfg_path), "--run-id", "r2"])

    _publish_identity_tokenizer(artifacts_root, "tok_identity")

    _run([sys.executable, "scripts/04_tokenize_corpus.py", "--config", str(tokenize_cfg_path), "--run-id", "r3"])
    _run([sys.executable, "scripts/05_pack_sequences.py", "--config", str(pack_cfg_path), "--run-id", "r4"])

    registry = [json.loads(line) for line in (artifacts_root / "registry.jsonl").read_text(encoding="utf-8").splitlines()]
    packed_entries = [entry for entry in registry if entry["artifact_type"] == "packed"]
    assert packed_entries, "Expected a packed artifact to be published"

    packed_entry = packed_entries[-1]
    packed_dir = Path(packed_entry["artifact_path"])
    index_payload = json.loads((packed_dir / "index.json").read_text(encoding="utf-8"))

    assert index_payload["splits"]["train"]["num_blocks"] >= 0
    assert index_payload["splits"]["val"]["num_blocks"] >= 0
    assert (packed_dir / "train" / "shards" / "pack_00000.bin").exists()
    assert (packed_dir / "val" / "shards" / "pack_00000.bin").exists()

    dedup_entries = [entry for entry in registry if entry["artifact_type"] == "corpus_dedup"]
    dedup_manifest = json.loads(Path(dedup_entries[-1]["manifest_path"]).read_text(encoding="utf-8"))
    dedup_docs = Path(dedup_entries[-1]["artifact_path"]) / dedup_manifest["stats"]["docs_file"]
    with gzip.open(dedup_docs, "rt", encoding="utf-8") as handle:
        lines = handle.readlines()
    assert len(lines) >= 2
