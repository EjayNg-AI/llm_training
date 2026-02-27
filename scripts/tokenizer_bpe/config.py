"""Config loading, validation, and hashing utilities for tokenizer training."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "run": {
        "output_dir": "artifacts/tokenizer/runs",
        "seed": 0,
        "log_level": "INFO",
        "report_output_path": "docs/data_collection_report.md",
        "stage3_metrics_every_merges": 200,
    },
    "data": {
        "input_paths": ["data/raw/train.txt"],
        "input_format": "text",
        "jsonl_text_field": "text",
        "decode_errors": "replace",
        "normalize": "none",
        "max_bytes": None,
        "max_lines": None,
        "num_workers": 4,
        "batch_lines": 2000,
        "min_piece_freq": 2,
        "max_unique_pieces": 2000000,
    },
    "pretokenizer": {
        "pattern": "gpt2_fast",
        "custom_pattern": None,
        "flags": [],
    },
    "bpe": {
        "vocab_size": 50000,
        "min_merge_freq": 2,
        "max_merges": None,
        "max_word_types": 1500000,
        "max_piece_bytes": 200,
        "tie_break": "lexicographic",
    },
    "special_tokens": {
        "tokens": ["<|endoftext|>", "<|pad|>"],
        "placement": "end",
    },
    "checkpointing": {
        "enabled": True,
        "snapshot_every_merges": 1000,
        "wal_enabled": True,
        "wal_fsync_every_commits": 200,
        "wal_fsync_mode": "periodic",
        "resume_mode": "off",
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate(cfg: dict[str, Any]) -> None:
    if cfg["data"]["input_format"] not in {"text", "jsonl"}:
        raise ValueError("data.input_format must be one of: text, jsonl")
    if cfg["data"]["decode_errors"] not in {"strict", "replace", "ignore"}:
        raise ValueError("data.decode_errors must be one of: strict, replace, ignore")
    if cfg["data"]["normalize"] not in {"none", "NFC", "NFKC"}:
        raise ValueError("data.normalize must be one of: none, NFC, NFKC")
    if cfg["special_tokens"]["placement"] not in {"start", "end"}:
        raise ValueError("special_tokens.placement must be one of: start, end")
    if cfg["checkpointing"]["wal_fsync_mode"] not in {"periodic", "per_commit"}:
        raise ValueError("checkpointing.wal_fsync_mode must be one of: periodic, per_commit")
    if cfg["checkpointing"]["resume_mode"] not in {"off", "auto"}:
        raise ValueError("checkpointing.resume_mode must be one of: off, auto")
    if cfg["bpe"]["tie_break"] != "lexicographic":
        raise ValueError("Only lexicographic tie_break is supported.")
    if not cfg["data"]["input_paths"]:
        raise ValueError("data.input_paths must not be empty")
    if int(cfg["data"]["num_workers"]) < 1:
        raise ValueError("data.num_workers must be >= 1")
    if int(cfg["data"]["batch_lines"]) < 1:
        raise ValueError("data.batch_lines must be >= 1")
    if int(cfg["run"]["stage3_metrics_every_merges"]) < 1:
        raise ValueError("run.stage3_metrics_every_merges must be >= 1")
    if int(cfg["bpe"]["vocab_size"]) < 256:
        raise ValueError("bpe.vocab_size must be >= 256")
    if int(cfg["checkpointing"]["snapshot_every_merges"]) < 0:
        raise ValueError("checkpointing.snapshot_every_merges must be >= 0")
    if int(cfg["checkpointing"]["wal_fsync_every_commits"]) < 1:
        raise ValueError("checkpointing.wal_fsync_every_commits must be >= 1")


def canonical_config_json(cfg: dict[str, Any]) -> str:
    return json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_pattern_hash(
    pattern_str: str,
    pattern_flags: int,
    normalize: str,
    regex_version: str,
) -> str:
    payload = {
        "pattern_str": pattern_str,
        "pattern_flags": pattern_flags,
        "normalize": normalize,
        "regex_version": regex_version,
    }
    return sha256_hex(canonical_config_json(payload))


def load_config(path: str | Path) -> dict[str, Any]:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Tokenizer config not found: {cfg_path}")
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Top-level config must be a mapping.")
    cfg = _deep_merge(DEFAULT_CONFIG, raw)
    _validate(cfg)

    cfg_no_meta = copy.deepcopy(cfg)
    config_hash = sha256_hex(canonical_config_json(cfg_no_meta))
    cfg["meta"] = {
        "config_path": str(cfg_path.resolve()),
        "config_hash": config_hash,
    }
    return cfg
