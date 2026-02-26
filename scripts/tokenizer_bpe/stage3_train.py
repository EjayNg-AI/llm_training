"""Stage 3: incremental BPE merge learning with WAL and snapshots."""

from __future__ import annotations

from array import array
from collections import defaultdict
import heapq
import logging
import os
from pathlib import Path
import time
from typing import Any, Iterable

from .io_atomic import atomic_dump_json, atomic_dump_pickle_with_checksum, load_pickle_with_checksum


PAIR_SHIFT = 32
PAIR_MASK = (1 << PAIR_SHIFT) - 1
HEAP_REBUILD_RATIO = 6


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
        if isinstance(symbols, array):
            words.append(array(word_storage_type, symbols))
        else:
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


def _append_wal_line(handle, line: str) -> None:
    handle.write(line)
    handle.flush()


def _fsync_wal(handle) -> None:
    os.fsync(handle.fileno())


def parse_wal_commits(wal_path: Path) -> list[tuple[int, int, int, int]]:
    if not wal_path.exists():
        return []
    begins: dict[int, tuple[int, int]] = {}
    commits: list[tuple[int, int, int, int]] = []
    with wal_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if parts[0] == "BEGIN" and len(parts) >= 5:
                merge_idx = int(parts[1])
                begins[merge_idx] = (int(parts[2]), int(parts[3]))
            elif parts[0] == "COMMIT" and len(parts) >= 3:
                merge_idx = int(parts[1])
                new_id = int(parts[2])
                if merge_idx in begins:
                    a, b = begins[merge_idx]
                    commits.append((merge_idx, a, b, new_id))
    commits.sort(key=lambda x: x[0])
    return commits


def _write_metrics_line(metrics_path: Path, payload: dict[str, Any]) -> None:
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with metrics_path.open("a", encoding="utf-8") as f:
        f.write(json_dumps(payload) + "\n")


def _snapshot_path(snapshot_dir: Path, merge_index: int) -> Path:
    return snapshot_dir / f"state.m{merge_index:08d}.pkl"


def _write_snapshot(
    snapshot_dir: Path,
    merge_index: int,
    core_state: dict[str, Any],
    keep_last: int,
    logger: logging.Logger,
) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(snapshot_dir, merge_index)
    atomic_dump_pickle_with_checksum(path, core_state)

    snapshots = sorted(snapshot_dir.glob("state.m*.pkl"))
    if len(snapshots) > keep_last:
        to_delete = snapshots[: len(snapshots) - keep_last]
        for old in to_delete:
            checksum_path = old.with_suffix(old.suffix + ".sha256")
            old.unlink(missing_ok=True)
            checksum_path.unlink(missing_ok=True)
    logger.info("Snapshot written: %s", path.name)


def load_latest_snapshot(
    snapshot_dir: Path,
    config_hash: str,
    pattern_hash: str,
    logger: logging.Logger,
) -> dict[str, Any] | None:
    if not snapshot_dir.exists():
        return None
    snapshots = sorted(snapshot_dir.glob("state.m*.pkl"), reverse=True)
    for path in snapshots:
        try:
            state = load_pickle_with_checksum(path)
        except Exception as exc:
            logger.warning("Skipping unreadable snapshot %s: %s", path.name, exc)
            continue
        if state.get("config_hash") != config_hash:
            continue
        if state.get("pattern_hash") != pattern_hash:
            continue
        return state
    return None


def _apply_merge_everywhere(words: list[array], a: int, b: int, new_id: int, word_storage_type: str) -> int:
    affected = 0
    for idx, symbols in enumerate(words):
        if contains_pair(symbols, a, b):
            words[idx] = merge_symbols(symbols, a, b, new_id, word_storage_type)
            affected += 1
    return affected


def json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def train_bpe(
    cfg: dict[str, Any],
    run_dir: Path,
    initial_state: dict[str, Any],
    logger: logging.Logger,
    config_hash: str,
    pattern_hash: str,
    resume: bool,
    stop_after_merges: int | None,
) -> dict[str, Any]:
    bpe_cfg = cfg["bpe"]
    checkpoint_cfg = cfg["checkpointing"]
    special_tokens = cfg["special_tokens"]["tokens"]

    vocab_size = int(bpe_cfg["vocab_size"])
    max_merges = bpe_cfg["max_merges"]
    min_merge_freq = int(bpe_cfg["min_merge_freq"])
    target_merges = int(max_merges) if max_merges is not None else max(0, vocab_size - 256 - len(special_tokens))

    snapshot_dir = run_dir / "snapshots"
    wal_path = run_dir / "merges.wal"
    metrics_path = run_dir / "metrics.jsonl"
    state_json_path = run_dir / "state.json"

    word_storage_type = initial_state.get("word_storage_type") or _select_word_storage_type(cfg)
    if word_storage_type not in {"H", "I"}:
        word_storage_type = _select_word_storage_type(cfg)
    words = _normalize_words(initial_state["words"], word_storage_type)
    freqs = _normalize_freqs(initial_state["freqs"])
    id_to_token_bytes = list(initial_state["id_to_token_bytes"])
    merge_pairs: list[tuple[int, int]] = []
    last_merge = 0

    if resume:
        snapshot_state = load_latest_snapshot(snapshot_dir, config_hash, pattern_hash, logger)
        if snapshot_state is not None:
            word_storage_type = snapshot_state.get("word_storage_type") or word_storage_type
            if word_storage_type not in {"H", "I"}:
                word_storage_type = _select_word_storage_type(cfg)
            words = _normalize_words(snapshot_state["words"], word_storage_type)
            freqs = _normalize_freqs(snapshot_state["freqs"])
            id_to_token_bytes = list(snapshot_state["id_to_token_bytes"])
            merge_pairs = [tuple(pair) for pair in snapshot_state.get("merge_pairs", [])]
            last_merge = int(snapshot_state.get("last_merge", len(merge_pairs)))
            logger.info("Resume loaded snapshot at merge %s", last_merge)

        wal_commits = parse_wal_commits(wal_path)
        for merge_idx, a, b, wal_new_id in wal_commits:
            if merge_idx <= last_merge:
                continue
            expected_new_id = len(id_to_token_bytes)
            if wal_new_id != expected_new_id:
                raise ValueError(
                    f"WAL new_id mismatch at merge {merge_idx}: wal={wal_new_id}, expected={expected_new_id}"
                )
            id_to_token_bytes.append(id_to_token_bytes[a] + id_to_token_bytes[b])
            _apply_merge_everywhere(words, a, b, wal_new_id, word_storage_type)
            merge_pairs.append((a, b))
            last_merge = merge_idx
        if wal_commits:
            logger.info("Resume replayed WAL to merge %s", last_merge)

    pair_count, pair_to_words, heap = _build_pair_structures(words, freqs)
    logger.info("Stage 3 initialized: unique_pairs=%s", len(pair_count))

    wal_path.parent.mkdir(parents=True, exist_ok=True)
    wal_file = wal_path.open("a", encoding="utf-8")
    wal_durable_each_commit = bool(checkpoint_cfg.get("wal_fsync_each_commit", False))
    wal_fsync_every_commits = int(checkpoint_cfg.get("wal_fsync_every_commits", 0))
    snapshot_every_merges = int(checkpoint_cfg["snapshot_every_merges"])
    snapshot_every_seconds = int(checkpoint_cfg["snapshot_every_seconds"])
    keep_last_snapshots = int(checkpoint_cfg["keep_last_snapshots"])

    wal_commits_since_fsync = 0
    last_snapshot_time = time.time()
    start_index = last_merge + 1
    completed = last_merge

    try:
        for merge_index in range(start_index, target_merges + 1):
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

            _append_wal_line(wal_file, f"BEGIN\t{merge_index}\t{a}\t{b}\t{best_count}\n")

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

            _append_wal_line(wal_file, f"COMMIT\t{merge_index}\t{new_id}\n")
            wal_commits_since_fsync += 1
            if wal_durable_each_commit:
                _fsync_wal(wal_file)
                wal_commits_since_fsync = 0
            elif wal_fsync_every_commits > 0 and wal_commits_since_fsync >= wal_fsync_every_commits:
                _fsync_wal(wal_file)
                wal_commits_since_fsync = 0

            _maybe_rebuild_heap(heap, pair_count)

            now = time.time()
            should_snapshot = (
                (merge_index % snapshot_every_merges == 0) or ((now - last_snapshot_time) >= snapshot_every_seconds)
            )
            if should_snapshot:
                if wal_commits_since_fsync > 0:
                    _fsync_wal(wal_file)
                    wal_commits_since_fsync = 0

                snapshot_state = {
                    "words": words,
                    "freqs": freqs,
                    "id_to_token_bytes": id_to_token_bytes,
                    "merge_pairs": merge_pairs,
                    "last_merge": merge_index,
                    "config_hash": config_hash,
                    "pattern_hash": pattern_hash,
                    "word_storage_type": word_storage_type,
                }
                _write_snapshot(snapshot_dir, merge_index, snapshot_state, keep_last_snapshots, logger)
                last_snapshot_time = now
                atomic_dump_json(
                    state_json_path,
                    {
                        "stage": "merge_training",
                        "merge_index": merge_index,
                        "target_merges": target_merges,
                        "best_pair_count": best_count,
                        "affected_word_types": affected_words,
                        "unique_pairs": len(pair_count),
                        "heap_size": len(heap),
                        "vocab_size_so_far": len(id_to_token_bytes),
                        "timestamp": int(now),
                    },
                )
                _write_metrics_line(
                    metrics_path,
                    {
                        "timestamp": int(now),
                        "stage": "stage3",
                        "merge_index": merge_index,
                        "best_pair_count": best_count,
                        "unique_pairs": len(pair_count),
                        "unique_word_types": len(words),
                        "affected_word_types": affected_words,
                    },
                )
                logger.info(
                    "Merge %s/%s best_count=%s affected=%s unique_pairs=%s",
                    merge_index,
                    target_merges,
                    best_count,
                    affected_words,
                    len(pair_count),
                )
    finally:
        if wal_commits_since_fsync > 0:
            _fsync_wal(wal_file)
        wal_file.close()

    if completed > 0:
        snapshot_state = {
            "words": words,
            "freqs": freqs,
            "id_to_token_bytes": id_to_token_bytes,
            "merge_pairs": merge_pairs,
            "last_merge": completed,
            "config_hash": config_hash,
            "pattern_hash": pattern_hash,
            "word_storage_type": word_storage_type,
        }
        _write_snapshot(snapshot_dir, completed, snapshot_state, keep_last_snapshots, logger)

    logger.info("Stage 3 complete at merge index: %s", completed)
    return {
        "words": words,
        "freqs": freqs,
        "id_to_token_bytes": id_to_token_bytes,
        "merge_pairs": merge_pairs,
        "last_merge": completed,
        "word_storage_type": word_storage_type,
    }
