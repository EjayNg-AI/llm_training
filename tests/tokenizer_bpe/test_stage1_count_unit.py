from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from tokenizer_bpe.pretokenizer import PATTERN_ALIASES
from tokenizer_bpe.stage1_count import (
    _compile_special_token_splitter,
    _discover_input_files,
    _extract_text,
    _iter_non_special_segments,
    _load_stage1_checkpoint,
    _prune_counter,
    _save_stage1_checkpoint,
    count_pieces,
)
import tokenizer_bpe.stage1_count as stage1_count_module


def _count_pieces_for_text(tmp_path, text: str, tokenizer_logger):
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text(text, encoding="utf-8")
    cfg = {
        "data": {
            "input_paths": [str(corpus_path)],
            "input_format": "text",
            "jsonl_text_field": "text",
            "decode_errors": "replace",
            "normalize": "none",
            "max_bytes": None,
            "max_lines": None,
            "num_workers": 1,
            "batch_lines": 4,
            "max_unique_pieces": 1000,
        },
        "checkpointing": {
            "stage1_snapshot_every_batches": 1,
            "snapshot_every_seconds": 999999,
        },
        "bpe": {
            "max_piece_bytes": 200,
        },
        "special_tokens": {
            "tokens": ["<|endoftext|>"],
            "placement": "end",
        },
        "meta": {
            "config_hash": "cfg",
        },
    }

    original_executor = stage1_count_module.ProcessPoolExecutor
    stage1_count_module.ProcessPoolExecutor = ThreadPoolExecutor
    try:
        return count_pieces(
            cfg=cfg,
            run_dir=tmp_path / "run",
            pattern_str=PATTERN_ALIASES["gpt2_fast"],
            pattern_flags=0,
            pattern_hash="pat",
            logger=tokenizer_logger,
            resume=False,
        )
    finally:
        stage1_count_module.ProcessPoolExecutor = original_executor


def test_discover_input_files_text_filters_and_sorts(tmp_path):
    data_dir = tmp_path / "data"
    nested = data_dir / "nested"
    nested.mkdir(parents=True)
    (data_dir / "b.txt").write_text("b", encoding="utf-8")
    (nested / "a.txt").write_text("a", encoding="utf-8")
    (nested / "skip.jsonl").write_text('{"text":"x"}\n', encoding="utf-8")
    (nested / "c.txt.gz").write_bytes(b"\x1f\x8b")

    files = _discover_input_files([str(data_dir)], "text")
    assert files == sorted(files)
    assert {path.name for path in files} == {"a.txt", "b.txt", "c.txt.gz"}


def test_discover_input_files_jsonl_filters_and_sorts(tmp_path):
    data_dir = tmp_path / "data"
    nested = data_dir / "nested"
    nested.mkdir(parents=True)
    (data_dir / "b.jsonl").write_text('{"text":"b"}\n', encoding="utf-8")
    (nested / "a.jsonl").write_text('{"text":"a"}\n', encoding="utf-8")
    (nested / "skip.txt").write_text("skip", encoding="utf-8")
    (nested / "c.jsonl.gz").write_bytes(b"\x1f\x8b")

    files = _discover_input_files([str(data_dir)], "jsonl")
    assert files == sorted(files)
    assert {path.name for path in files} == {"a.jsonl", "b.jsonl", "c.jsonl.gz"}


def test_extract_text_jsonl_cases():
    assert _extract_text("raw line\n", "text", "text") == "raw line\n"
    assert _extract_text('{"text":"hello"}\n', "jsonl", "text") == "hello"
    assert _extract_text('{"text":123}\n', "jsonl", "text") == ""
    assert _extract_text("not-json\n", "jsonl", "text") == ""


def test_special_token_splitter_prefers_longest_literal_match():
    split_re = _compile_special_token_splitter(["<|end|>", "<|endoftext|>"], "none")
    assert list(_iter_non_special_segments("a<|endoftext|>b<|end|>c", split_re)) == ["a", "b", "c"]


def test_prune_counter_min_freq_and_top_k_tie_break():
    counter = Counter({b"b": 5, b"a": 5, b"c": 1})
    pruned = _prune_counter(counter, min_piece_freq=2, max_unique_pieces=1)
    assert pruned == Counter({b"a": 5})


def test_count_pieces_discards_exact_special_token_lines(tmp_path, tokenizer_logger):
    piece_counts, metadata = _count_pieces_for_text(tmp_path, "<|endoftext|>", tokenizer_logger)
    assert piece_counts == Counter()
    assert metadata["total_lines_processed"] == 1
    assert metadata["total_pieces_seen"] == 0


def test_count_pieces_discards_inline_special_token_occurrences(tmp_path, tokenizer_logger):
    piece_counts, metadata = _count_pieces_for_text(tmp_path, "hello<|endoftext|>world", tokenizer_logger)
    assert piece_counts == Counter({b"hello": 1, b"world": 1})
    assert b"<|" not in piece_counts
    assert b"|>" not in piece_counts
    assert b"endoftext" not in piece_counts
    assert metadata["total_lines_processed"] == 1
    assert metadata["total_pieces_seen"] == 2


def test_load_stage1_checkpoint_rejects_hash_mismatch(tmp_path):
    counts_path = tmp_path / "word_counts.snapshot.pkl"
    progress_path = tmp_path / "word_counts.progress.json"
    counts = Counter({b"hello": 3})
    progress = {
        "files": [],
        "total_lines_processed": 1,
        "total_pieces_seen": 3,
        "total_bytes_processed": 10,
        "config_hash": "cfg-a",
        "pattern_hash": "pat-a",
        "snapshot_id": 1,
        "timestamp": 1,
    }
    _save_stage1_checkpoint(counts_path, progress_path, counts, progress)

    assert _load_stage1_checkpoint(counts_path, progress_path, "cfg-b", "pat-a") is None
    assert _load_stage1_checkpoint(counts_path, progress_path, "cfg-a", "pat-b") is None


def test_load_stage1_checkpoint_round_trip(tmp_path):
    counts_path = tmp_path / "word_counts.snapshot.pkl"
    progress_path = tmp_path / "word_counts.progress.json"
    counts = Counter({b"hello": 3, b"world": 2})
    progress = {
        "files": [],
        "total_lines_processed": 2,
        "total_pieces_seen": 5,
        "total_bytes_processed": 22,
        "config_hash": "cfg",
        "pattern_hash": "pat",
        "snapshot_id": 2,
        "timestamp": 42,
    }
    _save_stage1_checkpoint(counts_path, progress_path, counts, progress)
    loaded = _load_stage1_checkpoint(counts_path, progress_path, "cfg", "pat")
    assert loaded is not None
    loaded_counts, loaded_progress = loaded
    assert loaded_counts == counts
    assert loaded_progress["snapshot_id"] == 2


def test_count_pieces_stage1_safety_cap_triggers_early(tmp_path, tokenizer_logger, monkeypatch):
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text("a\nb\nc\nd\n", encoding="utf-8")

    cfg = {
        "data": {
            "input_paths": [str(corpus_path)],
            "input_format": "text",
            "jsonl_text_field": "text",
            "decode_errors": "replace",
            "normalize": "none",
            "max_bytes": None,
            "max_lines": None,
            "num_workers": 1,
            "batch_lines": 1,
            "max_unique_pieces": 2,
        },
        "checkpointing": {
            "stage1_snapshot_every_batches": 999999,
            "snapshot_every_seconds": 999999,
            "stage1_cap_every_batches": 999999,
            "stage1_cap_start_lines": 10**9,
            "stage1_cap_safety_factor": 1.0,
        },
        "bpe": {
            "max_piece_bytes": 200,
        },
        "special_tokens": {
            "tokens": ["<|endoftext|>"],
            "placement": "end",
        },
        "meta": {
            "config_hash": "cfg",
        },
    }

    call_counter = {"n": 0}
    original_top_k = stage1_count_module._counter_top_k

    def wrapped_top_k(counter, k):
        call_counter["n"] += 1
        return original_top_k(counter, k)

    monkeypatch.setattr(stage1_count_module, "_counter_top_k", wrapped_top_k)

    original_executor = stage1_count_module.ProcessPoolExecutor
    stage1_count_module.ProcessPoolExecutor = ThreadPoolExecutor
    try:
        piece_counts, metadata = count_pieces(
            cfg=cfg,
            run_dir=tmp_path / "run",
            pattern_str=PATTERN_ALIASES["gpt2_fast"],
            pattern_flags=0,
            pattern_hash="pat",
            logger=tokenizer_logger,
            resume=False,
        )
    finally:
        stage1_count_module.ProcessPoolExecutor = original_executor

    assert len(piece_counts) <= 2
    assert metadata["total_lines_processed"] == 4
    assert call_counter["n"] >= 2
