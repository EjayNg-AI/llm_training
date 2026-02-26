from __future__ import annotations

from array import array

import pytest

from tokenizer_bpe.stage3_train import (
    _build_pair_structures,
    _pop_best_pair,
    count_adjacent_pairs,
    contains_pair,
    make_pair_id,
    merge_symbols,
    train_bpe,
)


def _minimal_cfg() -> dict:
    return {
        "bpe": {
            "vocab_size": 260,
            "max_merges": None,
            "min_merge_freq": 2,
        },
        "special_tokens": {"tokens": ["<|endoftext|>", "<|pad|>"]},
        "checkpointing": {
            "wal_fsync_each_commit": False,
            "wal_fsync_every_commits": 0,
            "snapshot_every_merges": 1,
            "snapshot_every_seconds": 999999,
            "keep_last_snapshots": 2,
        },
    }


def test_count_adjacent_pairs_and_contains_pair():
    symbols = [1, 2, 1, 2, 3]
    counts = count_adjacent_pairs(symbols)
    assert counts[make_pair_id(1, 2)] == 2
    assert counts[make_pair_id(2, 1)] == 1
    assert contains_pair(symbols, 1, 2) is True
    assert contains_pair(symbols, 2, 2) is False


def test_merge_symbols_non_overlapping_left_to_right():
    assert list(merge_symbols(array("H", [1, 1, 1]), 1, 1, 9, "H")) == [9, 1]
    assert list(merge_symbols(array("H", [1, 2, 1, 2]), 1, 2, 9, "H")) == [9, 9]


def test_heap_pop_best_pair_uses_lexicographic_tie_break():
    words = [array("H", [1, 2]), array("H", [1, 3])]
    freqs = array("Q", [2, 2])
    pair_count, _, heap = _build_pair_structures(words, freqs)
    assert pair_count[make_pair_id(1, 2)] == 2
    assert pair_count[make_pair_id(1, 3)] == 2
    assert _pop_best_pair(heap, pair_count) == (1, 2, 2)


def test_train_bpe_resume_rejects_wal_new_id_mismatch(tmp_path, tokenizer_logger):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    wal_path = run_dir / "merges.wal"
    wal_path.write_text(
        "BEGIN\t1\t1\t2\t10\n"
        "COMMIT\t1\t999\n",
        encoding="utf-8",
    )

    initial_state = {
        "words": [[1, 2, 1, 2]],
        "freqs": [10],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
    }

    with pytest.raises(ValueError, match="WAL new_id mismatch"):
        train_bpe(
            cfg=_minimal_cfg(),
            run_dir=run_dir,
            initial_state=initial_state,
            logger=tokenizer_logger,
            config_hash="cfg",
            pattern_hash="pat",
            resume=True,
            stop_after_merges=None,
        )
