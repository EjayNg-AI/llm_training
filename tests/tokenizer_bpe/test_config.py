from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from tokenizer_bpe.config import (
    DEFAULT_CONFIG,
    build_pattern_hash,
    canonical_config_json,
    load_config,
)

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "03_train_tokenizer.py"
sys.path.insert(0, str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("train_tokenizer_stage03", SCRIPT_PATH)
train_tokenizer_stage03 = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(train_tokenizer_stage03)


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
    assert cfg["data"]["max_bytes"] is None
    assert cfg["data"]["max_lines"] is None
    assert cfg["data"]["max_unique_pieces"] == 2500000
    assert cfg["bpe"]["max_merges"] is None
    assert cfg["bpe"]["max_word_types"] == 2500000
    assert cfg["meta"]["config_path"] == str(cfg_path.resolve())
    assert len(cfg["meta"]["config_hash"]) == 64


def test_load_config_hash_is_reproducible(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("data:\n  num_workers: 2\n", encoding="utf-8")
    first = load_config(cfg_path)
    second = load_config(cfg_path)
    assert first["meta"]["config_hash"] == second["meta"]["config_hash"]


def test_load_config_applies_overrides_after_yaml(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text(
        "data:\n  max_unique_pieces: 123\nbpe:\n  max_word_types: 456\n",
        encoding="utf-8",
    )
    cfg = load_config(
        cfg_path,
        overrides={
            "data": {"max_unique_pieces": 789},
            "bpe": {"max_word_types": 987},
        },
    )
    assert cfg["data"]["max_unique_pieces"] == 789
    assert cfg["bpe"]["max_word_types"] == 987


def test_load_config_hash_changes_when_overrides_change(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("", encoding="utf-8")
    first = load_config(
        cfg_path,
        overrides={"data": {"max_unique_pieces": 2500001}},
    )
    second = load_config(
        cfg_path,
        overrides={"data": {"max_unique_pieces": 2500002}},
    )
    assert first["meta"]["config_hash"] != second["meta"]["config_hash"]


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


def test_load_config_rejects_negative_max_bytes(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("data:\n  max_bytes: -1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max_bytes"):
        load_config(cfg_path)


def test_load_config_rejects_negative_max_lines(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("data:\n  max_lines: -1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max_lines"):
        load_config(cfg_path)


def test_load_config_rejects_non_positive_max_unique_pieces(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("data:\n  max_unique_pieces: 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max_unique_pieces"):
        load_config(cfg_path)


def test_load_config_rejects_non_positive_max_word_types(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("bpe:\n  max_word_types: 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max_word_types"):
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


def test_stage03_parser_accepts_config_override_flags():
    args = train_tokenizer_stage03.parse_args(
        ["--max-unique-pieces", "123", "--max-word-types", "456"]
    )
    assert args.max_unique_pieces == 123
    assert args.max_word_types == 456


def test_stage03_builds_nested_config_overrides_from_args():
    args = train_tokenizer_stage03.parse_args(
        ["--max-unique-pieces", "321", "--max-word-types", "654"]
    )
    overrides = train_tokenizer_stage03._config_overrides_from_args(args)
    assert overrides == {
        "data": {"max_unique_pieces": 321},
        "bpe": {"max_word_types": 654},
    }
