from __future__ import annotations

from array import array
from collections import defaultdict
import json

import pytest

from tokenizer_bpe.export import export_tokenizer
from tokenizer_bpe.stage3_train import (
    WAL_META_NAME,
    _apply_word_pair_deltas,
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
        "special_tokens": {"tokens": ["<|endoftext|>", "<|pad|>"], "placement": "end"},
        "checkpointing": {
            "wal_fsync_each_commit": False,
            "wal_fsync_every_commits": 0,
            "snapshot_every_merges": 1,
            "snapshot_every_seconds": 999999,
            "keep_last_snapshots": 2,
        },
    }


def _write_wal_metadata(run_dir, config_hash: str = "cfg", pattern_hash: str = "pat") -> None:
    (run_dir / WAL_META_NAME).write_text(
        json.dumps({"config_hash": config_hash, "pattern_hash": pattern_hash}),
        encoding="utf-8",
    )


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
    _write_wal_metadata(run_dir)

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


def test_train_bpe_resume_rejects_wal_without_metadata_when_no_snapshot(tmp_path, tokenizer_logger):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    wal_path = run_dir / "merges.wal"
    wal_path.write_text(
        "BEGIN\t1\t1\t2\t10\n"
        "COMMIT\t1\t256\n",
        encoding="utf-8",
    )

    initial_state = {
        "words": [[1, 2, 1, 2]],
        "freqs": [10],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
    }

    with pytest.raises(ValueError, match="Cannot safely replay WAL without compatible snapshot or WAL metadata"):
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


def test_train_bpe_resume_rejects_wal_metadata_mismatch(tmp_path, tokenizer_logger):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    wal_path = run_dir / "merges.wal"
    wal_path.write_text(
        "BEGIN\t1\t1\t2\t10\n"
        "COMMIT\t1\t256\n",
        encoding="utf-8",
    )
    _write_wal_metadata(run_dir, config_hash="other_cfg", pattern_hash="other_pat")

    initial_state = {
        "words": [[1, 2, 1, 2]],
        "freqs": [10],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
    }

    with pytest.raises(ValueError, match="WAL metadata mismatch for resume"):
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


def test_train_bpe_resume_rejects_wal_merge_index_gap(tmp_path, tokenizer_logger):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    wal_path = run_dir / "merges.wal"
    wal_path.write_text(
        "BEGIN\t1\t1\t2\t10\n"
        "COMMIT\t1\t256\n"
        "BEGIN\t3\t3\t4\t7\n"
        "COMMIT\t3\t257\n",
        encoding="utf-8",
    )
    _write_wal_metadata(run_dir)

    initial_state = {
        "words": [[1, 2, 3, 4]],
        "freqs": [10],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
    }

    with pytest.raises(ValueError, match="WAL merge index mismatch"):
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


def test_train_bpe_resume_rejects_wal_merge_with_no_effect(tmp_path, tokenizer_logger):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    wal_path = run_dir / "merges.wal"
    wal_path.write_text(
        "BEGIN\t1\t9\t10\t10\n"
        "COMMIT\t1\t256\n",
        encoding="utf-8",
    )
    _write_wal_metadata(run_dir)

    initial_state = {
        "words": [[1, 2, 3, 4]],
        "freqs": [10],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
    }

    with pytest.raises(ValueError, match="had no effect"):
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


def test_apply_word_pair_deltas_removes_stale_pair_candidates():
    pair_ab = make_pair_id(1, 2)
    pair_bc = make_pair_id(2, 3)
    pair_count = {pair_ab: 5, pair_bc: 7}
    pair_to_words = defaultdict(list, {pair_ab: [0, 1], pair_bc: [0]})
    heap: list[tuple[int, int]] = []

    _apply_word_pair_deltas(
        word_idx=0,
        freq=7,
        old_pairs={pair_ab: 1, pair_bc: 1},
        new_pairs={pair_ab: 1},
        pair_count=pair_count,
        pair_to_words=pair_to_words,
        heap=heap,
    )

    assert pair_ab in pair_count
    assert pair_ab in pair_to_words
    assert pair_bc not in pair_count
    assert pair_bc not in pair_to_words


def test_apply_word_pair_deltas_indexes_only_new_local_pairs():
    pair_ab = make_pair_id(1, 2)
    pair_bc = make_pair_id(2, 3)
    pair_cd = make_pair_id(3, 4)
    pair_count = {pair_ab: 10, pair_bc: 8, pair_cd: 1}
    pair_to_words = defaultdict(list, {pair_ab: [2], pair_bc: [2], pair_cd: [5]})
    heap: list[tuple[int, int]] = []

    _apply_word_pair_deltas(
        word_idx=2,
        freq=1,
        old_pairs={pair_ab: 1, pair_bc: 1},
        new_pairs={pair_ab: 1, pair_bc: 1, pair_cd: 1},
        pair_count=pair_count,
        pair_to_words=pair_to_words,
        heap=heap,
    )

    assert pair_to_words[pair_ab] == [2]
    assert pair_to_words[pair_bc] == [2]
    assert pair_to_words[pair_cd] == [5, 2]
    assert pair_count[pair_cd] == 2
    assert (-2, pair_cd) in heap


def test_train_bpe_floor_vocab_performs_zero_merges_and_exports_full_base(tmp_path, tokenizer_logger):
    cfg = _minimal_cfg()
    cfg["bpe"]["vocab_size"] = 256

    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    initial_state = {
        "words": [[1, 2, 1, 2]],
        "freqs": [10],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
    }
    train_state = train_bpe(
        cfg=cfg,
        run_dir=run_dir,
        initial_state=initial_state,
        logger=tokenizer_logger,
        config_hash="cfg",
        pattern_hash="pat",
        resume=False,
        stop_after_merges=None,
    )

    assert train_state["merge_pairs"] == []
    assert train_state["last_merge"] == 0

    export_dir = tmp_path / "export"
    export_tokenizer(
        cfg=cfg,
        run_dir=run_dir,
        export_dir=export_dir,
        train_state=train_state,
        pattern_alias="gpt2_fast",
        pattern_str="x",
        pattern_flags=0,
        pattern_hash="pat",
        config_hash="cfg",
        corpus_hash="corp",
        logger=tokenizer_logger,
    )
    vocab = json.loads((export_dir / "vocab.json").read_text(encoding="utf-8"))
    stats = json.loads((export_dir / "training_stats.json").read_text(encoding="utf-8"))

    assert stats["num_merges"] == 0
    assert len(vocab) == 256 + len(cfg["special_tokens"]["tokens"])
    assert len(vocab) > cfg["bpe"]["vocab_size"]
