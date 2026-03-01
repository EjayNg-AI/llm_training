from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from tokenizer_bpe.pretokenizer import resolve_pattern
from tokenizer_bpe.stage1_count import count_pieces
import tokenizer_bpe.stage1_count as stage1_count_module


def _cfg(corpus_path: str) -> dict:
    return {
        "data": {
            "input_paths": [corpus_path],
            "input_format": "text",
            "jsonl_text_field": "text",
            "decode_errors": "replace",
            "normalize": "none",
            "max_bytes": None,
            "max_lines": None,
            "num_workers": 1,
            "batch_lines": 2,
            "min_piece_freq": 1,
            "max_unique_pieces": 1000,
        },
        "bpe": {"max_piece_bytes": 200},
        "pretokenizer": {"pattern": "gpt2_fast", "custom_pattern": None, "flags": []},
    }


def test_stage1_count_returns_scaling_metrics(tmp_path, tokenizer_logger):
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text("alpha beta\nalpha gamma\n", encoding="utf-8")
    cfg = _cfg(str(corpus_path))
    _, pattern_str, pattern_flags, _ = resolve_pattern(cfg["pretokenizer"])

    original_executor = stage1_count_module.ProcessPoolExecutor
    stage1_count_module.ProcessPoolExecutor = ThreadPoolExecutor
    try:
        piece_counts, meta = count_pieces(
            cfg=cfg,
            run_dir=tmp_path / "run",
            pattern_str=pattern_str,
            pattern_flags=pattern_flags,
            pattern_hash="unused",
            logger=tokenizer_logger,
        )
    finally:
        stage1_count_module.ProcessPoolExecutor = original_executor

    assert piece_counts
    assert meta["total_bytes_processed"] > 0
    assert meta["total_pieces_seen"] > 0
    assert meta["stage1_elapsed_seconds"] >= 0
    assert 0.0 <= meta["coverage"] <= 1.0
    assert meta["unique_before_prune"] >= meta["unique_kept"]
    assert meta["hit_max_unique_pieces"] is False
    assert meta["max_unique_pieces_cap_events"] == 0
    assert meta["rss_peak_mb"] >= 0


def test_stage1_count_marks_unique_cap_engagement(tmp_path, tokenizer_logger):
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text("\n".join(f"token_{i}" for i in range(100)) + "\n", encoding="utf-8")
    cfg = _cfg(str(corpus_path))
    cfg["data"]["max_unique_pieces"] = 8
    cfg["data"]["batch_lines"] = 200
    _, pattern_str, pattern_flags, _ = resolve_pattern(cfg["pretokenizer"])

    original_executor = stage1_count_module.ProcessPoolExecutor
    stage1_count_module.ProcessPoolExecutor = ThreadPoolExecutor
    try:
        _, meta = count_pieces(
            cfg=cfg,
            run_dir=tmp_path / "run",
            pattern_str=pattern_str,
            pattern_flags=pattern_flags,
            pattern_hash="unused",
            logger=tokenizer_logger,
        )
    finally:
        stage1_count_module.ProcessPoolExecutor = original_executor

    assert meta["hit_max_unique_pieces"] is True
    assert meta["max_unique_pieces_cap_events"] >= 1
    assert meta["unique_before_prune"] > meta["unique_kept"]
