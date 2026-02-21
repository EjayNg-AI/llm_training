"""Stage 3: incremental BPE merge learning with WAL and snapshots."""

from __future__ import annotations

from collections import Counter, defaultdict
import heapq
import logging
import os
from pathlib import Path
import time
from typing import Any, Iterable

from .io_atomic import atomic_dump_json, atomic_dump_pickle_with_checksum, load_pickle_with_checksum


Pair = tuple[int, int]


def count_adjacent_pairs(symbols: list[int]) -> Counter[Pair]:
    counts: Counter[Pair] = Counter()
    for i in range(len(symbols) - 1):
        counts[(symbols[i], symbols[i + 1])] += 1
    return counts


def contains_pair(symbols: list[int], a: int, b: int) -> bool:
    for i in range(len(symbols) - 1):
        if symbols[i] == a and symbols[i + 1] == b:
            return True
    return False


def merge_symbols(symbols: list[int], a: int, b: int, new_id: int) -> list[int]:
    merged: list[int] = []
    i = 0
    while i < len(symbols):
        if i + 1 < len(symbols) and symbols[i] == a and symbols[i + 1] == b:
            merged.append(new_id)
            i += 2
        else:
            merged.append(symbols[i])
            i += 1
    return merged


def _build_pair_structures(
    words: list[list[int]],
    freqs: list[int],
) -> tuple[dict[Pair, int], dict[Pair, list[int]], list[tuple[int, int, int]]]:
    pair_count: dict[Pair, int] = {}
    pair_to_words: dict[Pair, list[int]] = defaultdict(list)

    for idx, symbols in enumerate(words):
        local_pairs = count_adjacent_pairs(symbols)
        if not local_pairs:
            continue
        freq = freqs[idx]
        for pair, occ in local_pairs.items():
            pair_count[pair] = pair_count.get(pair, 0) + freq * occ
            pair_to_words[pair].append(idx)

    heap = [(-count, pair[0], pair[1]) for pair, count in pair_count.items() if count > 0]
    heapq.heapify(heap)
    return pair_count, pair_to_words, heap


def _pop_best_pair(
    heap: list[tuple[int, int, int]],
    pair_count: dict[Pair, int],
) -> tuple[int, int, int] | None:
    while heap:
        neg_count, a, b = heapq.heappop(heap)
        count = -neg_count
        if pair_count.get((a, b), 0) == count:
            return a, b, count
    return None


def _append_wal_line(handle, line: str, durable: bool) -> None:
    handle.write(line)
    handle.flush()
    if durable:
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


def _apply_merge_everywhere(words: list[list[int]], a: int, b: int, new_id: int) -> int:
    affected = 0
    for idx, symbols in enumerate(words):
        if contains_pair(symbols, a, b):
            words[idx] = merge_symbols(symbols, a, b, new_id)
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

    words = [list(s) for s in initial_state["words"]]
    freqs = list(initial_state["freqs"])
    id_to_token_bytes = list(initial_state["id_to_token_bytes"])
    merge_pairs: list[tuple[int, int]] = []
    last_merge = 0

    if resume:
        snapshot_state = load_latest_snapshot(snapshot_dir, config_hash, pattern_hash, logger)
        if snapshot_state is not None:
            words = snapshot_state["words"]
            freqs = snapshot_state["freqs"]
            id_to_token_bytes = snapshot_state["id_to_token_bytes"]
            merge_pairs = snapshot_state.get("merge_pairs", [])
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
            _apply_merge_everywhere(words, a, b, wal_new_id)
            merge_pairs.append((a, b))
            last_merge = merge_idx
        if wal_commits:
            logger.info("Resume replayed WAL to merge %s", last_merge)

    pair_count, pair_to_words, heap = _build_pair_structures(words, freqs)
    logger.info("Stage 3 initialized: unique_pairs=%s", len(pair_count))

    wal_path.parent.mkdir(parents=True, exist_ok=True)
    wal_file = wal_path.open("a", encoding="utf-8")
    wal_durable = bool(checkpoint_cfg["wal_fsync_each_commit"])
    snapshot_every_merges = int(checkpoint_cfg["snapshot_every_merges"])
    snapshot_every_seconds = int(checkpoint_cfg["snapshot_every_seconds"])
    keep_last_snapshots = int(checkpoint_cfg["keep_last_snapshots"])

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

            _append_wal_line(wal_file, f"BEGIN\t{merge_index}\t{a}\t{b}\t{best_count}\n", wal_durable)

            new_id = len(id_to_token_bytes)
            id_to_token_bytes.append(id_to_token_bytes[a] + id_to_token_bytes[b])

            candidates = pair_to_words.get((a, b), [])
            touched_pairs: set[Pair] = set()
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
                new_symbols = merge_symbols(symbols, a, b, new_id)
                if new_symbols == symbols:
                    continue

                words[word_idx] = new_symbols
                new_pairs = count_adjacent_pairs(new_symbols)
                affected_words += 1

                all_local_pairs = set(old_pairs.keys()) | set(new_pairs.keys())
                freq = freqs[word_idx]
                for pair in all_local_pairs:
                    delta = (new_pairs.get(pair, 0) - old_pairs.get(pair, 0)) * freq
                    if delta == 0:
                        continue
                    updated = pair_count.get(pair, 0) + delta
                    if updated <= 0:
                        pair_count.pop(pair, None)
                    else:
                        pair_count[pair] = updated
                        heapq.heappush(heap, (-updated, pair[0], pair[1]))
                    touched_pairs.add(pair)

                for pair in new_pairs.keys():
                    pair_to_words[pair].append(word_idx)

            pair_count.pop((a, b), None)
            merge_pairs.append((a, b))
            completed = merge_index

            _append_wal_line(wal_file, f"COMMIT\t{merge_index}\t{new_id}\n", wal_durable)

            now = time.time()
            should_snapshot = (
                (merge_index % snapshot_every_merges == 0) or ((now - last_snapshot_time) >= snapshot_every_seconds)
            )
            if should_snapshot:
                snapshot_state = {
                    "words": words,
                    "freqs": freqs,
                    "id_to_token_bytes": id_to_token_bytes,
                    "merge_pairs": merge_pairs,
                    "last_merge": merge_index,
                    "config_hash": config_hash,
                    "pattern_hash": pattern_hash,
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
        }
        _write_snapshot(snapshot_dir, completed, snapshot_state, keep_last_snapshots, logger)

    logger.info("Stage 3 complete at merge index: %s", completed)
    return {
        "words": words,
        "freqs": freqs,
        "id_to_token_bytes": id_to_token_bytes,
        "merge_pairs": merge_pairs,
        "last_merge": completed,
    }

