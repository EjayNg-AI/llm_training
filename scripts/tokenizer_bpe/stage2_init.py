"""Stage 2: initialize merge-learning state from piece counts."""

from __future__ import annotations

from collections import Counter
import logging
from typing import Any


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

    words = [list(piece) for piece, _ in items]
    freqs = [freq for _, freq in items]

    id_to_token_bytes = [bytes([i]) for i in range(256)]

    logger.info(
        "Stage 2 initialized: word_types=%s base_vocab=%s",
        len(words),
        len(id_to_token_bytes),
    )
    return {
        "words": words,
        "freqs": freqs,
        "id_to_token_bytes": id_to_token_bytes,
    }

