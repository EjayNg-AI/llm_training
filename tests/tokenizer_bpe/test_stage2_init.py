from __future__ import annotations

from collections import Counter

from tokenizer_bpe.stage2_init import initialize_training_state


def _cfg(*, min_piece_freq: int, max_word_types: int) -> dict:
    return {
        "data": {"min_piece_freq": min_piece_freq},
        "bpe": {"max_word_types": max_word_types, "vocab_size": 50000, "max_merges": None},
        "special_tokens": {"tokens": ["<|endoftext|>", "<|pad|>"]},
    }


def test_initialize_training_state_filters_and_sorts(tokenizer_logger):
    piece_counts = Counter(
        {
            b"ba": 3,
            b"aa": 3,
            b"z": 1,
        }
    )
    state = initialize_training_state(
        piece_counts=piece_counts,
        cfg=_cfg(min_piece_freq=2, max_word_types=10),
        logger=tokenizer_logger,
    )
    assert [list(symbols) for symbols in state["words"]] == [[97, 97], [98, 97]]
    assert state["freqs"].tolist() == [3, 3]
    assert state["word_storage_type"] == "H"
    assert len(state["id_to_token_bytes"]) == 256
    assert state["id_to_token_bytes"][0] == b"\x00"
    assert state["id_to_token_bytes"][255] == b"\xff"


def test_initialize_training_state_applies_max_word_types(tokenizer_logger):
    piece_counts = Counter({b"aa": 5, b"ab": 4, b"ac": 3})
    state = initialize_training_state(
        piece_counts=piece_counts,
        cfg=_cfg(min_piece_freq=1, max_word_types=2),
        logger=tokenizer_logger,
    )
    assert len(state["words"]) == 2
    assert state["freqs"].tolist() == [5, 4]
