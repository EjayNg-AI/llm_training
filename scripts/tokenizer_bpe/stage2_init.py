"""Stage 2: initialize merge-learning state from piece counts."""

from __future__ import annotations

from array import array
from collections import Counter
import logging
from time import perf_counter
from typing import Any

from .telemetry import bytes_to_mb, sample_process_tree_rss_bytes


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
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = perf_counter()
    min_piece_freq = int(cfg["data"]["min_piece_freq"])
    max_word_types = int(cfg["bpe"]["max_word_types"])

    all_items = [(piece, int(freq)) for piece, freq in piece_counts.items() if int(freq) >= min_piece_freq]
    all_items.sort(key=lambda kv: (-kv[1], kv[0]))
    word_types_total = len(all_items)
    hit_max_word_types = word_types_total > max_word_types
    if hit_max_word_types:
        cutoff_freq = int(all_items[max_word_types - 1][1])
        items = all_items[:max_word_types]
    else:
        cutoff_freq = int(all_items[-1][1]) if all_items else 0
        items = all_items

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

    lengths = [len(word) for word in words]
    if lengths:
        sorted_lengths = sorted(lengths)
        p95_index = max(0, min(len(sorted_lengths) - 1, int(round(0.95 * (len(sorted_lengths) - 1)))))
        avg_symbols = float(sum(sorted_lengths) / len(sorted_lengths))
        p95_symbols = int(sorted_lengths[p95_index])
        max_symbols = int(sorted_lengths[-1])
    else:
        avg_symbols = 0.0
        p95_symbols = 0
        max_symbols = 0

    meta = {
        "word_types_total": word_types_total,
        "word_types_kept": len(words),
        "hit_max_word_types": hit_max_word_types,
        "cutoff_freq_at_word_types_cap": cutoff_freq,
        "avg_symbols_per_word_type": avg_symbols,
        "p95_symbols_per_word_type": p95_symbols,
        "max_symbols_per_word_type": max_symbols,
        "stage2_elapsed_seconds": max(0.0, perf_counter() - started),
        "rss_end_mb": bytes_to_mb(sample_process_tree_rss_bytes()),
    }
    return {
        "words": words,
        "freqs": freqs,
        "id_to_token_bytes": id_to_token_bytes,
        "word_storage_type": word_storage_type,
    }, meta
