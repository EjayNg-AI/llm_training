from __future__ import annotations

import json

import pytest

from tokenizer_bpe.byte_unicode import bytes_to_unicode, token_bytes_to_string
from tokenizer_bpe.export import export_tokenizer


def _train_state() -> dict:
    id_to_token_bytes = [bytes([i]) for i in range(256)]
    id_to_token_bytes.append(id_to_token_bytes[65] + id_to_token_bytes[66])
    return {
        "id_to_token_bytes": id_to_token_bytes,
        "merge_pairs": [(65, 66)],
        "last_merge": 1,
    }


def _cfg(placement: str, tokens: list[str]) -> dict:
    return {
        "special_tokens": {
            "tokens": tokens,
            "placement": placement,
        }
    }


def test_export_special_tokens_end_placement(tmp_path, tokenizer_logger):
    run_dir = tmp_path / "run"
    export_dir = tmp_path / "export"
    export_tokenizer(
        cfg=_cfg("end", ["<|endoftext|>", "<|pad|>"]),
        run_dir=run_dir,
        export_dir=export_dir,
        train_state=_train_state(),
        pattern_alias="gpt2_fast",
        pattern_str="x",
        pattern_flags=0,
        pattern_hash="pat",
        config_hash="cfg",
        corpus_hash="corp",
        logger=tokenizer_logger,
    )
    vocab = json.loads((export_dir / "vocab.json").read_text(encoding="utf-8"))
    assert vocab["<|endoftext|>"] == len(vocab) - 2
    assert vocab["<|pad|>"] == len(vocab) - 1


def test_export_special_tokens_start_placement(tmp_path, tokenizer_logger):
    run_dir = tmp_path / "run"
    export_dir = tmp_path / "export"
    export_tokenizer(
        cfg=_cfg("start", ["<|endoftext|>", "<|pad|>"]),
        run_dir=run_dir,
        export_dir=export_dir,
        train_state=_train_state(),
        pattern_alias="gpt2_fast",
        pattern_str="x",
        pattern_flags=0,
        pattern_hash="pat",
        config_hash="cfg",
        corpus_hash="corp",
        logger=tokenizer_logger,
    )
    vocab = json.loads((export_dir / "vocab.json").read_text(encoding="utf-8"))
    assert vocab["<|endoftext|>"] == 0
    assert vocab["<|pad|>"] == 1


def test_export_rejects_special_token_collision_with_base_vocab(tmp_path, tokenizer_logger):
    run_dir = tmp_path / "run"
    export_dir = tmp_path / "export"
    with pytest.raises(ValueError, match="Token collision"):
        export_tokenizer(
            cfg=_cfg("start", ["A"]),
            run_dir=run_dir,
            export_dir=export_dir,
            train_state=_train_state(),
            pattern_alias="gpt2_fast",
            pattern_str="x",
            pattern_flags=0,
            pattern_hash="pat",
            config_hash="cfg",
            corpus_hash="corp",
            logger=tokenizer_logger,
        )


def test_export_writes_merges_header_and_stats(tmp_path, tokenizer_logger):
    run_dir = tmp_path / "run"
    export_dir = tmp_path / "export"
    export_tokenizer(
        cfg=_cfg("end", ["<|endoftext|>", "<|pad|>"]),
        run_dir=run_dir,
        export_dir=export_dir,
        train_state=_train_state(),
        pattern_alias="gpt2_fast",
        pattern_str="x",
        pattern_flags=0,
        pattern_hash="pat",
        config_hash="cfg",
        corpus_hash="corp",
        logger=tokenizer_logger,
    )
    merges_lines = (export_dir / "merges.txt").read_text(encoding="utf-8").splitlines()
    assert merges_lines[0] == "#version: 0.2"

    byte_to_unicode, _ = bytes_to_unicode()
    expected_pair = (
        token_bytes_to_string(bytes([65]), byte_to_unicode),
        token_bytes_to_string(bytes([66]), byte_to_unicode),
    )
    assert merges_lines[1] == f"{expected_pair[0]} {expected_pair[1]}"

    stats = json.loads((export_dir / "training_stats.json").read_text(encoding="utf-8"))
    assert stats["final_merge_index"] == 1
    assert stats["num_merges"] == 1
    assert not (run_dir / "export_manifest.json").exists()
