"""Stage 2: initialize merge-learning state from piece counts."""

from __future__ import annotations

from array import array
from collections import Counter
import logging
from typing import Any


def _select_word_storage_type(cfg: dict[str, Any]) -> str:
    special_tokens = cfg.get("special_tokens", {}).get("tokens", [])
    max_merges = cfg["bpe"]["max_merges"]
    if max_merges is None:
        target_merges = max(0, int(cfg["bpe"]["vocab_size"]) - 256 - len(special_tokens))
    else:
        target_merges = max(0, int(max_merges))
    max_symbol_id = 255 + target_merges
    return "H" if max_symbol_id < 65536 else "I"


def initialize_training_state(
    piece_counts: Counter[bytes],
    cfg: dict[str, Any],
    logger: logging.Logger,
) -> dict[str, Any]:
    min_piece_freq = int(cfg["data"]["min_piece_freq"])
    max_word_types = int(cfg["bpe"]["max_word_types"])

    items = [(piece, int(freq)) for piece, freq in piece_counts.items() if int(freq) >= min_piece_freq]
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    if len(items) > max_word_types:
        items = items[:max_word_types]

    word_storage_type = _select_word_storage_type(cfg)
    words = [array(word_storage_type, list(piece)) for piece, _ in items]
    freqs = array("Q", (freq for _, freq in items))

    id_to_token_bytes = [bytes([i]) for i in range(256)]

    logger.info(
        "Stage 2 initialized: word_types=%s base_vocab=%s storage=%s",
        len(words),
        len(id_to_token_bytes),
        word_storage_type,
    )
    return {
        "words": words,
        "freqs": freqs,
        "id_to_token_bytes": id_to_token_bytes,
        "word_storage_type": word_storage_type,
    }
