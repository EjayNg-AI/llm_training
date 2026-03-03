"""Stage 3: incremental BPE merge learning."""

from __future__ import annotations

from array import array
from collections import defaultdict
import heapq
import json
import logging
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

from .io_atomic import atomic_dump_json
from .telemetry import RssSampler


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


def _percentile(values: list[int | float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(float(v) for v in values)
    idx = int(round((percentile / 100.0) * (len(sorted_values) - 1)))
    idx = max(0, min(len(sorted_values) - 1, idx))
    return sorted_values[idx]


def train_bpe(
    cfg: dict[str, Any],
    run_dir: Path,
    initial_state: dict[str, Any],
    logger: logging.Logger,
    config_hash: str,
    pattern_hash: str,
    stop_after_merges: int | None,
) -> dict[str, Any]:
    del config_hash, pattern_hash  # Compatibility with older call sites.

    bpe_cfg = cfg["bpe"]
    special_tokens = cfg["special_tokens"]["tokens"]
    run_cfg = cfg.get("run", {})
    checkpoint_cfg = cfg.get("checkpointing", {})

    vocab_size = int(bpe_cfg["vocab_size"])
    max_merges = bpe_cfg["max_merges"]
    min_merge_freq = int(bpe_cfg["min_merge_freq"])
    target_merges = int(max_merges) if max_merges is not None else max(0, vocab_size - 256 - len(special_tokens))
    metrics_every = int(run_cfg.get("stage3_metrics_every_merges", STAGE3_LOG_EVERY_MERGES))

    checkpointing_enabled = bool(checkpoint_cfg.get("enabled", False))
    snapshot_every_merges = int(checkpoint_cfg.get("snapshot_every_merges", 0))
    wal_enabled = checkpointing_enabled and bool(checkpoint_cfg.get("wal_enabled", False))
    wal_fsync_every_commits = int(checkpoint_cfg.get("wal_fsync_every_commits", 1))
    wal_fsync_mode = str(checkpoint_cfg.get("wal_fsync_mode", "periodic"))
    resume_mode = str(checkpoint_cfg.get("resume_mode", "off"))

    word_storage_type = initial_state.get("word_storage_type") or _select_word_storage_type(cfg)
    if word_storage_type not in {"H", "I"}:
        word_storage_type = _select_word_storage_type(cfg)
    words = _normalize_words(initial_state["words"], word_storage_type)
    freqs = _normalize_freqs(initial_state["freqs"])
    id_to_token_bytes = list(initial_state["id_to_token_bytes"])
    merge_pairs: list[tuple[int, int]] = []

    pair_count, pair_to_words, heap = _build_pair_structures(words, freqs)
    logger.info("Stage 3 initialized: unique_pairs=%s", len(pair_count))

    rss = RssSampler()
    rss.sample()
    stage3_started = perf_counter()

    merge_durations_ms: list[float] = []
    best_counts: list[int] = []
    candidates_pre_dedup: list[int] = []
    candidates_post_dedup: list[int] = []
    progress_samples: list[dict[str, Any]] = []
    window_durations_ms: list[float] = []
    window_candidates_pre_dedup: list[int] = []
    window_candidates_post_dedup: list[int] = []

    pair_count_len_initial = len(pair_count)
    pair_count_len_late = len(pair_count)
    heap_size_initial = len(heap)
    heap_size_late = len(heap)

    wal_path = run_dir / "merges.wal"
    wal_file = None
    wal_sync_count = 0
    wal_sync_seconds = 0.0
    wal_pending_commits = 0
    wal_commits = 0
    snapshot_count = 0
    snapshot_total_seconds = 0.0

    if checkpointing_enabled and resume_mode == "auto":
        logger.warning("checkpointing.resume_mode=auto requested; Stage 3 currently starts from a fresh run.")

    if wal_enabled:
        run_dir.mkdir(parents=True, exist_ok=True)
        wal_file = wal_path.open("w", encoding="utf-8")

    def maybe_fsync_wal(*, force: bool = False) -> None:
        nonlocal wal_pending_commits, wal_sync_count, wal_sync_seconds
        if wal_file is None:
            return
        should_sync = force
        if not should_sync:
            if wal_fsync_mode == "per_commit":
                should_sync = wal_pending_commits > 0
            else:
                should_sync = wal_pending_commits >= wal_fsync_every_commits
        if not should_sync:
            return
        started = perf_counter()
        wal_file.flush()
        os.fsync(wal_file.fileno())
        wal_sync_seconds += max(0.0, perf_counter() - started)
        wal_sync_count += 1
        wal_pending_commits = 0

    completed = 0
    try:
        for merge_index in range(1, target_merges + 1):
            if stop_after_merges is not None and merge_index > stop_after_merges:
                logger.info("Stopping early at user-requested merge boundary: %s", stop_after_merges)
                break

            merge_started = perf_counter()

            best = _pop_best_pair(heap, pair_count)
            if best is None:
                logger.info("No remaining merge candidates.")
                break
            a, b, best_count = best
            if best_count < min_merge_freq:
                logger.info("Stopping at merge %s due to min_merge_freq threshold.", merge_index)
                break

            best_counts.append(int(best_count))

            new_id = len(id_to_token_bytes)
            id_to_token_bytes.append(id_to_token_bytes[a] + id_to_token_bytes[b])

            merged_pair_id = make_pair_id(a, b)
            candidates = pair_to_words.pop(merged_pair_id, [])
            affected_words = 0
            candidates_raw_count = len(candidates)
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
                        pair_to_words.pop(pair_id, None)
                    else:
                        pair_count[pair_id] = updated
                        heapq.heappush(heap, (-updated, pair_id))

                # Only append memberships for pairs newly introduced in this word.
                for pair_id in (new_pairs.keys() - old_pairs.keys()):
                    pair_to_words[pair_id].append(word_idx)

            pair_count.pop(merged_pair_id, None)
            merge_pairs.append((a, b))
            completed = merge_index
            _maybe_rebuild_heap(heap, pair_count)

            if wal_file is not None:
                wal_file.write(
                    json.dumps(
                        {"merge_index": merge_index, "a": a, "b": b, "best_count": int(best_count)},
                        sort_keys=True,
                    )
                    + "\n"
                )
                wal_commits += 1
                wal_pending_commits += 1
                maybe_fsync_wal(force=False)

            if checkpointing_enabled and snapshot_every_merges > 0 and merge_index % snapshot_every_merges == 0:
                snapshot_started = perf_counter()
                atomic_dump_json(
                    run_dir / f"snapshot_{merge_index:07d}.json",
                    {
                        "merge_index": merge_index,
                        "vocab_size": len(id_to_token_bytes) + len(special_tokens),
                        "num_merges": len(merge_pairs),
                        "unique_pairs": len(pair_count),
                        "word_types": len(words),
                    },
                )
                snapshot_total_seconds += max(0.0, perf_counter() - snapshot_started)
                snapshot_count += 1

            merge_elapsed_ms = max(0.0, (perf_counter() - merge_started) * 1000.0)
            merge_durations_ms.append(merge_elapsed_ms)
            window_durations_ms.append(merge_elapsed_ms)
            candidates_pre_dedup.append(candidates_raw_count)
            candidates_post_dedup.append(len(seen_word_indices))
            window_candidates_pre_dedup.append(candidates_raw_count)
            window_candidates_post_dedup.append(len(seen_word_indices))

            if merge_index % metrics_every == 0 or merge_index == target_merges:
                rss.sample()
                pair_count_len_late = len(pair_count)
                heap_size_late = len(heap)
                sample = {
                    "merge_index": merge_index,
                    "elapsed_seconds": max(0.0, perf_counter() - stage3_started),
                    "median_ms_per_merge_window": _percentile(window_durations_ms, 50.0),
                    "p95_ms_per_merge_window": _percentile(window_durations_ms, 95.0),
                    "best_count": int(best_count),
                    "pair_count_len": len(pair_count),
                    "heap_size": len(heap),
                    "candidates_pre_dedup_median_window": _percentile(window_candidates_pre_dedup, 50.0),
                    "candidates_post_dedup_median_window": _percentile(window_candidates_post_dedup, 50.0),
                }
                progress_samples.append(sample)
                logger.info(
                    (
                        "Merge %s/%s best_count=%s affected=%s unique_pairs=%s "
                        "median_ms/merge(last_window)=%.3f p95_ms/merge(last_window)=%.3f"
                    ),
                    merge_index,
                    target_merges,
                    best_count,
                    affected_words,
                    len(pair_count),
                    sample["median_ms_per_merge_window"],
                    sample["p95_ms_per_merge_window"],
                )
                window_durations_ms.clear()
                window_candidates_pre_dedup.clear()
                window_candidates_post_dedup.clear()
    finally:
        if wal_file is not None:
            try:
                maybe_fsync_wal(force=True)
            finally:
                wal_file.close()
        rss.sample()

    logger.info("Stage 3 complete at merge index: %s", completed)
    stage3_elapsed = max(0.0, perf_counter() - stage3_started)
    pair_count_len_late = len(pair_count)
    heap_size_late = len(heap)
    checkpoint_meta = {
        "enabled": checkpointing_enabled,
        "resume_mode": resume_mode,
        "snapshot_every_merges": snapshot_every_merges,
        "snapshot_count": snapshot_count,
        "snapshot_total_seconds": snapshot_total_seconds,
        "snapshot_avg_seconds": (snapshot_total_seconds / snapshot_count) if snapshot_count > 0 else 0.0,
        "wal_enabled": wal_enabled,
        "wal_path": str(wal_path) if wal_enabled else None,
        "wal_fsync_mode": wal_fsync_mode if wal_enabled else None,
        "wal_fsync_every_commits": wal_fsync_every_commits if wal_enabled else None,
        "wal_commits": wal_commits,
        "wal_sync_count": wal_sync_count,
        "wal_sync_seconds": wal_sync_seconds,
    }
    stage3_meta = {
        "target_merges": target_merges,
        "merges_done": completed,
        "elapsed_seconds": stage3_elapsed,
        "median_ms_per_merge": _percentile(merge_durations_ms, 50.0),
        "p95_ms_per_merge": _percentile(merge_durations_ms, 95.0),
        "pair_count_len_initial": pair_count_len_initial,
        "pair_count_len_late": pair_count_len_late,
        "heap_size_initial": heap_size_initial,
        "heap_size_late": heap_size_late,
        "best_count_initial": int(best_counts[0]) if best_counts else 0,
        "best_count_late": int(best_counts[-1]) if best_counts else 0,
        "candidates_per_merge_pre_dedup_median": _percentile(candidates_pre_dedup, 50.0),
        "candidates_per_merge_post_dedup_median": _percentile(candidates_post_dedup, 50.0),
        "candidates_per_merge_pre_dedup_p95": _percentile(candidates_pre_dedup, 95.0),
        "candidates_per_merge_post_dedup_p95": _percentile(candidates_post_dedup, 95.0),
        "rss_peak_mb": rss.peak_mb,
        "rss_end_mb": rss.last_mb,
        "progress_samples": progress_samples,
        "checkpointing": checkpoint_meta,
    }
    return {
        "words": words,
        "freqs": freqs,
        "id_to_token_bytes": id_to_token_bytes,
        "merge_pairs": merge_pairs,
        "last_merge": completed,
        "word_storage_type": word_storage_type,
        "stage3_meta": stage3_meta,
    }
