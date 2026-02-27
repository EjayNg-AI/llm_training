"""Stage 3: incremental BPE merge learning."""

from __future__ import annotations

from array import array
from collections import defaultdict
import heapq
import logging
from pathlib import Path
from typing import Any, Iterable


PAIR_SHIFT = 32
PAIR_MASK = (1 << PAIR_SHIFT) - 1
HEAP_REBUILD_RATIO = 6
STAGE3_LOG_EVERY_MERGES = 200


def make_pair_id(a: int, b: int) -> int:
    return (int(a) << PAIR_SHIFT) | int(b)


def split_pair_id(pair_id: int) -> tuple[int, int]:
    return pair_id >> PAIR_SHIFT, pair_id & PAIR_MASK


def _select_word_storage_type(cfg: dict[str, Any]) -> str:
    special_tokens = cfg.get("special_tokens", {}).get("tokens", [])
    max_merges = cfg["bpe"]["max_merges"]
    if max_merges is None:
        target_merges = max(0, int(cfg["bpe"]["vocab_size"]) - 256 - len(special_tokens))
    else:
        target_merges = max(0, int(max_merges))
    max_symbol_id = 255 + target_merges
    return "H" if max_symbol_id < 65536 else "I"


def _normalize_words(raw_words: Iterable[Iterable[int]], word_storage_type: str) -> list[array]:
    words: list[array] = []
    for symbols in raw_words:
        words.append(array(word_storage_type, symbols))
    return words


def _normalize_freqs(raw_freqs: Iterable[int]) -> array:
    if isinstance(raw_freqs, array):
        return array("Q", raw_freqs)
    return array("Q", (int(freq) for freq in raw_freqs))


def count_adjacent_pairs(symbols: Iterable[int]) -> dict[int, int]:
    counts: dict[int, int] = {}
    iterator = iter(symbols)
    try:
        prev = int(next(iterator))
    except StopIteration:
        return counts
    for current in iterator:
        current_int = int(current)
        pair_id = make_pair_id(prev, current_int)
        counts[pair_id] = counts.get(pair_id, 0) + 1
        prev = current_int
    return counts


def contains_pair(symbols: Iterable[int], a: int, b: int) -> bool:
    first = True
    prev = 0
    for current in symbols:
        current_int = int(current)
        if not first and prev == a and current_int == b:
            return True
        prev = current_int
        first = False
    return False


def merge_symbols(symbols: array, a: int, b: int, new_id: int, word_storage_type: str) -> array:
    merged = array(word_storage_type)
    i = 0
    while i < len(symbols):
        if i + 1 < len(symbols) and int(symbols[i]) == a and int(symbols[i + 1]) == b:
            merged.append(new_id)
            i += 2
        else:
            merged.append(int(symbols[i]))
            i += 1
    return merged


def _build_pair_structures(
    words: list[array],
    freqs: array,
) -> tuple[dict[int, int], dict[int, list[int]], list[tuple[int, int]]]:
    pair_count: dict[int, int] = {}
    pair_to_words: dict[int, list[int]] = defaultdict(list)

    for idx, symbols in enumerate(words):
        local_pairs = count_adjacent_pairs(symbols)
        if not local_pairs:
            continue
        freq = int(freqs[idx])
        for pair_id, occ in local_pairs.items():
            pair_count[pair_id] = pair_count.get(pair_id, 0) + freq * occ
            pair_to_words[pair_id].append(idx)

    heap = [(-count, pair_id) for pair_id, count in pair_count.items() if count > 0]
    heapq.heapify(heap)
    return pair_count, pair_to_words, heap


def _pop_best_pair(
    heap: list[tuple[int, int]],
    pair_count: dict[int, int],
) -> tuple[int, int, int] | None:
    while heap:
        neg_count, pair_id = heapq.heappop(heap)
        count = -neg_count
        if pair_count.get(pair_id, 0) == count:
            a, b = split_pair_id(pair_id)
            return a, b, count
    return None


def _rebuild_heap(pair_count: dict[int, int]) -> list[tuple[int, int]]:
    heap = [(-count, pair_id) for pair_id, count in pair_count.items() if count > 0]
    heapq.heapify(heap)
    return heap


def _maybe_rebuild_heap(heap: list[tuple[int, int]], pair_count: dict[int, int]) -> None:
    if not pair_count:
        heap.clear()
        return
    if len(heap) > HEAP_REBUILD_RATIO * len(pair_count):
        heap[:] = _rebuild_heap(pair_count)


def train_bpe(
    cfg: dict[str, Any],
    run_dir: Path,
    initial_state: dict[str, Any],
    logger: logging.Logger,
    config_hash: str,
    pattern_hash: str,
    stop_after_merges: int | None,
) -> dict[str, Any]:
    del run_dir, config_hash, pattern_hash  # Compatibility with older call sites.

    bpe_cfg = cfg["bpe"]
    special_tokens = cfg["special_tokens"]["tokens"]

    vocab_size = int(bpe_cfg["vocab_size"])
    max_merges = bpe_cfg["max_merges"]
    min_merge_freq = int(bpe_cfg["min_merge_freq"])
    target_merges = int(max_merges) if max_merges is not None else max(0, vocab_size - 256 - len(special_tokens))

    word_storage_type = initial_state.get("word_storage_type") or _select_word_storage_type(cfg)
    if word_storage_type not in {"H", "I"}:
        word_storage_type = _select_word_storage_type(cfg)
    words = _normalize_words(initial_state["words"], word_storage_type)
    freqs = _normalize_freqs(initial_state["freqs"])
    id_to_token_bytes = list(initial_state["id_to_token_bytes"])
    merge_pairs: list[tuple[int, int]] = []

    pair_count, pair_to_words, heap = _build_pair_structures(words, freqs)
    logger.info("Stage 3 initialized: unique_pairs=%s", len(pair_count))

    completed = 0
    for merge_index in range(1, target_merges + 1):
        if stop_after_merges is not None and merge_index > stop_after_merges:
            logger.info("Stopping early at user-requested merge boundary: %s", stop_after_merges)
            break

        best = _pop_best_pair(heap, pair_count)
        if best is None:
            logger.info("No remaining merge candidates.")
            break
        a, b, best_count = best
        if best_count < min_merge_freq:
            logger.info("Stopping at merge %s due to min_merge_freq threshold.", merge_index)
            break

        new_id = len(id_to_token_bytes)
        id_to_token_bytes.append(id_to_token_bytes[a] + id_to_token_bytes[b])

        merged_pair_id = make_pair_id(a, b)
        candidates = pair_to_words.pop(merged_pair_id, [])
        affected_words = 0
        seen_word_indices: set[int] = set()
        for word_idx in candidates:
            if word_idx in seen_word_indices:
                continue
            seen_word_indices.add(word_idx)

            symbols = words[word_idx]
            if not contains_pair(symbols, a, b):
                continue

            old_pairs = count_adjacent_pairs(symbols)
            new_symbols = merge_symbols(symbols, a, b, new_id, word_storage_type)
            if new_symbols == symbols:
                continue

            words[word_idx] = new_symbols
            new_pairs = count_adjacent_pairs(new_symbols)
            affected_words += 1

            all_local_pair_ids = set(old_pairs.keys()) | set(new_pairs.keys())
            freq = int(freqs[word_idx])
            for pair_id in all_local_pair_ids:
                delta = (new_pairs.get(pair_id, 0) - old_pairs.get(pair_id, 0)) * freq
                if delta == 0:
                    continue
                updated = pair_count.get(pair_id, 0) + delta
                if updated <= 0:
                    pair_count.pop(pair_id, None)
                else:
                    pair_count[pair_id] = updated
                    heapq.heappush(heap, (-updated, pair_id))

            for pair_id in new_pairs.keys():
                pair_to_words[pair_id].append(word_idx)

        pair_count.pop(merged_pair_id, None)
        merge_pairs.append((a, b))
        completed = merge_index
        _maybe_rebuild_heap(heap, pair_count)

        if merge_index % STAGE3_LOG_EVERY_MERGES == 0 or merge_index == target_merges:
            logger.info(
                "Merge %s/%s best_count=%s affected=%s unique_pairs=%s",
                merge_index,
                target_merges,
                best_count,
                affected_words,
                len(pair_count),
            )

    logger.info("Stage 3 complete at merge index: %s", completed)
    return {
        "words": words,
        "freqs": freqs,
        "id_to_token_bytes": id_to_token_bytes,
        "merge_pairs": merge_pairs,
        "last_merge": completed,
        "word_storage_type": word_storage_type,
    }
