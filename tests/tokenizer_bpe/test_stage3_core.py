from __future__ import annotations

from array import array

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


def test_train_bpe_respects_stop_after_merges(tmp_path, tokenizer_logger):
    initial_state = {
        "words": [[1, 2, 1, 2]],
        "freqs": [10],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
    }
    train_state = train_bpe(
        cfg=_minimal_cfg(),
        run_dir=tmp_path / "run",
        initial_state=initial_state,
        logger=tokenizer_logger,
        config_hash="cfg",
        pattern_hash="pat",
        stop_after_merges=1,
    )
    assert train_state["last_merge"] == 1
    assert len(train_state["merge_pairs"]) == 1
    assert len(train_state["id_to_token_bytes"]) == 257
    assert "stage3_meta" in train_state
    assert train_state["stage3_meta"]["merges_done"] == 1
    assert train_state["stage3_meta"]["pair_count_len_initial"] >= 1


def test_stage3_late_pair_count_metrics_reflect_final_state_after_early_stop(tmp_path, tokenizer_logger):
    cfg = _minimal_cfg()
    cfg["bpe"]["min_merge_freq"] = 15
    cfg["run"] = {"stage3_metrics_every_merges": 1000}
    cfg["checkpointing"] = {"enabled": False}

    initial_state = {
        "words": [[1, 2, 1, 2, 3]],
        "freqs": [10],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
    }
    train_state = train_bpe(
        cfg=cfg,
        run_dir=tmp_path / "run",
        initial_state=initial_state,
        logger=tokenizer_logger,
        config_hash="cfg",
        pattern_hash="pat",
        stop_after_merges=None,
    )

    final_pair_count: dict[int, int] = {}
    for symbols, freq in zip(train_state["words"], train_state["freqs"]):
        local_pairs = count_adjacent_pairs(symbols)
        for pair_id, occ in local_pairs.items():
            final_pair_count[pair_id] = final_pair_count.get(pair_id, 0) + int(freq) * occ

    assert train_state["last_merge"] == 1
    assert train_state["stage3_meta"]["pair_count_len_late"] == len(final_pair_count)


def test_stage3_candidate_windows_do_not_report_duplicate_word_indices(tmp_path, tokenizer_logger):
    cfg = {
        "bpe": {
            "vocab_size": 280,
            "max_merges": 8,
            "min_merge_freq": 1,
        },
        "special_tokens": {"tokens": ["<|endoftext|>", "<|pad|>"]},
        "run": {"stage3_metrics_every_merges": 1},
        "checkpointing": {"enabled": False},
    }
    initial_state = {
        "words": [
            [6, 0, 4, 7, 6, 4, 7, 5],
            [2, 4, 2],
            [4, 2, 4, 1, 1, 5],
            [1, 5, 6, 5, 3, 7],
        ],
        "freqs": [3, 1, 2, 2],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
    }
    train_state = train_bpe(
        cfg=cfg,
        run_dir=tmp_path / "run",
        initial_state=initial_state,
        logger=tokenizer_logger,
        config_hash="cfg",
        pattern_hash="pat",
        stop_after_merges=None,
    )

    assert train_state["stage3_meta"]["progress_samples"]
    for sample in train_state["stage3_meta"]["progress_samples"]:
        assert sample["candidates_pre_dedup_median_window"] == sample["candidates_post_dedup_median_window"]
