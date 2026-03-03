from __future__ import annotations

import copy

import pytest

from tokenizer_bpe.config import (
    DEFAULT_CONFIG,
    build_pattern_hash,
    canonical_config_json,
    load_config,
)


def test_canonical_config_json_stable_with_key_order():
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}
    assert canonical_config_json(left) == canonical_config_json(right)


def test_load_config_applies_defaults_and_meta(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("run:\n  log_level: DEBUG\n", encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg["run"]["log_level"] == "DEBUG"
    assert cfg["data"]["input_format"] == DEFAULT_CONFIG["data"]["input_format"]
    assert cfg["meta"]["config_path"] == str(cfg_path.resolve())
    assert len(cfg["meta"]["config_hash"]) == 64


def test_load_config_hash_is_reproducible(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("data:\n  num_workers: 2\n", encoding="utf-8")
    first = load_config(cfg_path)
    second = load_config(cfg_path)
    assert first["meta"]["config_hash"] == second["meta"]["config_hash"]


def test_load_config_rejects_invalid_input_format(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("data:\n  input_format: csv\n", encoding="utf-8")
    with pytest.raises(ValueError, match="data.input_format"):
        load_config(cfg_path)


def test_load_config_rejects_invalid_vocab_size(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("bpe:\n  vocab_size: 255\n", encoding="utf-8")
    with pytest.raises(ValueError, match="vocab_size"):
        load_config(cfg_path)


def test_load_config_rejects_negative_max_merges(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("bpe:\n  max_merges: -1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max_merges"):
        load_config(cfg_path)


def test_load_config_rejects_negative_wal_fsync_every_commits(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("checkpointing:\n  wal_fsync_every_commits: -1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="wal_fsync_every_commits"):
        load_config(cfg_path)


def test_load_config_requires_mapping(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("- item\n- another\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Top-level config"):
        load_config(cfg_path)


def test_build_pattern_hash_changes_when_inputs_change():
    h1 = build_pattern_hash(r"\w+", 0, "none", "1.0")
    h2 = build_pattern_hash(r"\w+", 0, "NFC", "1.0")
    h3 = build_pattern_hash(r"\w+", 0, "none", "1.1")
    assert h1 != h2
    assert h1 != h3


def test_build_pattern_hash_is_stable():
    payload = {
        "pattern_str": r"\w+",
        "pattern_flags": 0,
        "normalize": "none",
        "regex_version": "1.0",
    }
    first = build_pattern_hash(**payload)
    second = build_pattern_hash(**copy.deepcopy(payload))
    assert first == second
