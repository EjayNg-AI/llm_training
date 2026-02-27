from __future__ import annotations

from collections import Counter

from tokenizer_bpe.stage1_count import (
    _discover_input_files,
    _extract_text,
    _prune_counter,
)


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


def test_prune_counter_min_freq_and_top_k_tie_break():
    counter = Counter({b"b": 5, b"a": 5, b"c": 1})
    pruned = _prune_counter(counter, min_piece_freq=2, max_unique_pieces=1)
    assert pruned == Counter({b"a": 5})
