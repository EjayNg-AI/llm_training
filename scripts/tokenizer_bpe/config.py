"""Config loading, validation, and hashing utilities for tokenizer training."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


DEFAULT_SPECIAL_TOKENS = [
    "<|endoftext|>",
    "</s>",
    "<eos>",
    "<s>",
    "<bos>",
    "<pad>",
    "<unk>",
    "<|system|>",
    "<|user|>",
    "<|assistant|>",
    "<|im_start|>",
    "<|im_end|>",
    "<|endofmessage|>",
    "<|sep|>",
    "<|summarize|>",
    "<|translate|>",
    "<|code|>",
    "<mask>",
    "<fim_prefix>",
    "<fim_middle>",
    "<fim_suffix>",
    "<|title|>",
    "<|url|>",
    "<|date|>",
    "<|tool|>",
    "<|function_call|>",
]


DEFAULT_CONFIG: dict[str, Any] = {
    "run": {
        "output_dir": "artifacts/tokenizer/runs",
        "seed": 0,
        "log_level": "INFO",
        "structured_logs": True,
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
        "max_unique_pieces": 3500000,
    },
    "pretokenizer": {
        "pattern": "gpt2_fast",
        "custom_pattern": None,
        "flags": [],
    },
    "bpe": {
        "vocab_size": 64000,
        "min_merge_freq": 2,
        "max_merges": None,
        "max_word_types": 3000000,
        "max_piece_bytes": 200,
        "tie_break": "lexicographic",
    },
    "special_tokens": {
        "tokens": DEFAULT_SPECIAL_TOKENS,
        "placement": "end",
    },
    "checkpointing": {
        "wal_fsync_each_commit": False,
        "wal_fsync_every_commits": 250,
        "snapshot_every_merges": 2000,
        "snapshot_every_seconds": 300,
        "keep_last_snapshots": 3,
        "stage1_snapshot_every_batches": 500,
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
    if cfg["bpe"]["tie_break"] != "lexicographic":
        raise ValueError("Only lexicographic tie_break is supported.")
    if not cfg["data"]["input_paths"]:
        raise ValueError("data.input_paths must not be empty")
    if int(cfg["data"]["num_workers"]) < 1:
        raise ValueError("data.num_workers must be >= 1")
    if int(cfg["data"]["batch_lines"]) < 1:
        raise ValueError("data.batch_lines must be >= 1")
    max_bytes = cfg["data"].get("max_bytes")
    if max_bytes is not None and int(max_bytes) < 0:
        raise ValueError("data.max_bytes must be >= 0 when provided")
    max_lines = cfg["data"].get("max_lines")
    if max_lines is not None and int(max_lines) < 0:
        raise ValueError("data.max_lines must be >= 0 when provided")
    max_unique_pieces = cfg["data"].get("max_unique_pieces")
    if max_unique_pieces is not None and int(max_unique_pieces) <= 0:
        raise ValueError("data.max_unique_pieces must be > 0 when provided")
    if int(cfg["bpe"]["vocab_size"]) < 256:
        raise ValueError("bpe.vocab_size must be >= 256")
    max_merges = cfg["bpe"].get("max_merges")
    if max_merges is not None and int(max_merges) < 0:
        raise ValueError("bpe.max_merges must be >= 0 when provided")
    if int(cfg["bpe"]["max_word_types"]) <= 0:
        raise ValueError("bpe.max_word_types must be > 0")
    if int(cfg["checkpointing"].get("wal_fsync_every_commits", 0)) < 0:
        raise ValueError("checkpointing.wal_fsync_every_commits must be >= 0")


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


def load_config(path: str | Path, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Tokenizer config not found: {cfg_path}")
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Top-level config must be a mapping.")
    cfg = _deep_merge(DEFAULT_CONFIG, raw)
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ValueError("Config overrides must be a mapping.")
        cfg = _deep_merge(cfg, overrides)
    _validate(cfg)

    cfg_no_meta = copy.deepcopy(cfg)
    config_hash = sha256_hex(canonical_config_json(cfg_no_meta))
    cfg["meta"] = {
        "config_path": str(cfg_path.resolve()),
        "config_hash": config_hash,
    }
    return cfg
