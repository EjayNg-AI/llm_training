"""Stage 1: parallel piece counting."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
import gzip
import hashlib
import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any
import unicodedata

from .pretokenizer import compile_pattern, iter_pieces
from .telemetry import RssSampler


_WORKER_PATTERN = None
_WORKER_NORMALIZE = "none"
_WORKER_MAX_PIECE_BYTES = 200
STAGE1_LOG_EVERY_BATCHES = 50


def _worker_init(pattern_str: str, pattern_flags: int, normalize: str, max_piece_bytes: int) -> None:
    global _WORKER_PATTERN, _WORKER_NORMALIZE, _WORKER_MAX_PIECE_BYTES
    _WORKER_PATTERN = compile_pattern(pattern_str, pattern_flags)
    _WORKER_NORMALIZE = normalize
    _WORKER_MAX_PIECE_BYTES = max_piece_bytes


def _worker_count_batch(lines: list[str]) -> tuple[Counter[bytes], int]:
    if _WORKER_PATTERN is None:
        raise RuntimeError("Worker pretokenizer was not initialized.")

    local_counter: Counter[bytes] = Counter()
    total_pieces = 0

    for line in lines:
        if _WORKER_NORMALIZE != "none":
            line = unicodedata.normalize(_WORKER_NORMALIZE, line)
        for piece in iter_pieces(_WORKER_PATTERN, line):
            piece_bytes = piece.encode("utf-8")
            if len(piece_bytes) <= _WORKER_MAX_PIECE_BYTES:
                local_counter[piece_bytes] += 1
                total_pieces += 1
    return local_counter, total_pieces


def _is_supported_file(path: Path, input_format: str) -> bool:
    name = path.name.lower()
    if input_format == "text":
        return name.endswith(".txt") or name.endswith(".txt.gz")
    if input_format == "jsonl":
        return name.endswith(".jsonl") or name.endswith(".jsonl.gz")
    return False


def _discover_input_files(input_paths: list[str], input_format: str) -> list[Path]:
    files: list[Path] = []
    for item in input_paths:
        path = Path(item)
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")
        if path.is_file():
            if _is_supported_file(path, input_format):
                files.append(path)
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and _is_supported_file(child, input_format):
                files.append(child)
    files = sorted({p.resolve() for p in files})
    if not files:
        raise ValueError("No supported input files discovered for Stage 1 counting.")
    return files


def _open_binary(path: Path):
    if path.name.lower().endswith(".gz"):
        return gzip.open(path, "rb")
    return path.open("rb")


def _extract_text(
    decoded_line: str,
    input_format: str,
    jsonl_text_field: str,
) -> str:
    if input_format == "text":
        return decoded_line
    try:
        payload = json.loads(decoded_line)
        value = payload.get(jsonl_text_field, "")
    except Exception:
        return ""
    if isinstance(value, str):
        return value
    return ""


def _counter_top_k(counter: Counter[bytes], k: int) -> Counter[bytes]:
    if len(counter) <= k:
        return counter
    keep = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
    return Counter(dict(keep))


def _prune_counter(counter: Counter[bytes], min_piece_freq: int, max_unique_pieces: int) -> Counter[bytes]:
    if min_piece_freq > 1:
        for piece, freq in list(counter.items()):
            if freq < min_piece_freq:
                del counter[piece]
    if max_unique_pieces is not None:
        counter = _counter_top_k(counter, int(max_unique_pieces))
    return counter


def _frequency_cutoff(items: list[tuple[bytes, int]], kept_count: int) -> int:
    if not items or kept_count <= 0:
        return 0
    idx = min(kept_count, len(items)) - 1
    return int(items[idx][1])


def _compute_corpus_fingerprint(file_paths: list[Path]) -> str:
    h = hashlib.sha256()
    for path in sorted(file_paths):
        stat = path.stat()
        h.update(str(path).encode("utf-8"))
        h.update(str(stat.st_size).encode("utf-8"))
        h.update(str(stat.st_mtime_ns).encode("utf-8"))
    return h.hexdigest()


def count_pieces(
    cfg: dict[str, Any],
    run_dir: Path,
    pattern_str: str,
    pattern_flags: int,
    pattern_hash: str,
    logger: logging.Logger,
) -> tuple[Counter[bytes], dict[str, Any]]:
    del run_dir, pattern_hash  # API compatibility; no run-local Stage 1 files are written.

    data_cfg = cfg["data"]
    min_piece_freq = int(data_cfg["min_piece_freq"])

    input_paths = _discover_input_files(data_cfg["input_paths"], data_cfg["input_format"])
    corpus_hash = _compute_corpus_fingerprint(input_paths)

    piece_counts: Counter[bytes] = Counter()
    total_lines_processed = 0
    total_pieces_seen = 0
    total_bytes_processed = 0

    max_lines = data_cfg["max_lines"]
    max_bytes = data_cfg["max_bytes"]
    num_workers = int(data_cfg["num_workers"])
    batch_lines = int(data_cfg["batch_lines"])
    max_unique_pieces = data_cfg["max_unique_pieces"]
    stage1_started = perf_counter()
    rss = RssSampler()
    rss.sample()

    logger.info(
        "Stage 1 starting: files=%s workers=%s batch_lines=%s",
        len(input_paths),
        num_workers,
        batch_lines,
    )

    merged_batches = 0

    def should_stop() -> bool:
        if max_lines is not None and total_lines_processed >= int(max_lines):
            return True
        if max_bytes is not None and total_bytes_processed >= int(max_bytes):
            return True
        return False

    with ProcessPoolExecutor(
        max_workers=num_workers,
        initializer=_worker_init,
        initargs=(
            pattern_str,
            pattern_flags,
            data_cfg["normalize"],
            int(cfg["bpe"]["max_piece_bytes"]),
        ),
    ) as executor:
        for file_path in input_paths:
            if should_stop():
                break

            with _open_binary(file_path) as f:
                pending: dict[Future, int] = {}
                completed: dict[int, tuple[Counter[bytes], int]] = {}
                reached_eof = False
                next_batch_id = 0
                next_batch_to_merge = 0

                while not reached_eof or pending:
                    while not reached_eof and len(pending) < num_workers and not should_stop():
                        batch: list[str] = []
                        lines_read = 0
                        for _ in range(batch_lines):
                            raw = f.readline()
                            if not raw:
                                reached_eof = True
                                break
                            lines_read += 1
                            decoded = raw.decode("utf-8", errors=data_cfg["decode_errors"])
                            text = _extract_text(
                                decoded_line=decoded,
                                input_format=data_cfg["input_format"],
                                jsonl_text_field=data_cfg["jsonl_text_field"],
                            )
                            if text:
                                batch.append(text)
                            total_lines_processed += 1
                            total_bytes_processed += len(raw)
                            if should_stop():
                                break

                        if lines_read == 0:
                            reached_eof = True
                            break

                        future = executor.submit(_worker_count_batch, batch)
                        pending[future] = next_batch_id
                        next_batch_id += 1
                        if should_stop():
                            break

                    if not pending:
                        break

                    done, _ = wait(set(pending.keys()), return_when=FIRST_COMPLETED)
                    for done_future in done:
                        batch_id = pending.pop(done_future)
                        local_counter, local_pieces = done_future.result()
                        completed[batch_id] = (local_counter, int(local_pieces))

                    while next_batch_to_merge in completed:
                        local_counter, local_pieces = completed.pop(next_batch_to_merge)
                        next_batch_to_merge += 1

                        piece_counts.update(local_counter)
                        total_pieces_seen += local_pieces
                        merged_batches += 1

                        # Keep a single deterministic approximation knob in Stage 1:
                        # optional top-K capping by absolute count.
                        if max_unique_pieces is not None and merged_batches % 100 == 0 and total_lines_processed >= 10000:
                            piece_counts = _counter_top_k(piece_counts, int(max_unique_pieces))

                        if merged_batches % STAGE1_LOG_EVERY_BATCHES == 0:
                            rss.sample()
                            logger.info(
                                "Stage 1 progress: lines=%s pieces=%s unique=%s",
                                total_lines_processed,
                                total_pieces_seen,
                                len(piece_counts),
                            )

    if max_unique_pieces is not None:
        piece_counts = _counter_top_k(piece_counts, int(max_unique_pieces))
    rss.sample()
    stage1_elapsed = max(0.0, perf_counter() - stage1_started)

    unique_before_prune = len(piece_counts)
    filtered_items = [(piece, int(freq)) for piece, freq in piece_counts.items() if int(freq) >= min_piece_freq]
    filtered_items.sort(key=lambda kv: (-kv[1], kv[0]))
    unique_after_min_freq = len(filtered_items)
    if max_unique_pieces is None:
        kept_items = filtered_items
        hit_max_unique_pieces = False
    else:
        kept_items = filtered_items[: int(max_unique_pieces)]
        hit_max_unique_pieces = unique_after_min_freq > int(max_unique_pieces)
    unique_kept = len(kept_items)
    cutoff_freq = _frequency_cutoff(filtered_items, unique_kept)
    kept_mass = int(sum(freq for _, freq in kept_items))
    coverage = float(kept_mass / total_pieces_seen) if total_pieces_seen > 0 else 0.0

    logger.info(
        "Stage 1 complete: lines=%s pieces=%s unique=%s coverage=%.6f elapsed=%.3fs",
        total_lines_processed,
        total_pieces_seen,
        len(piece_counts),
        coverage,
        stage1_elapsed,
    )

    metadata = {
        "total_lines_processed": total_lines_processed,
        "total_bytes_processed": total_bytes_processed,
        "total_pieces_seen": total_pieces_seen,
        "stage1_elapsed_seconds": stage1_elapsed,
        "unique_before_prune": unique_before_prune,
        "unique_after_min_freq": unique_after_min_freq,
        "unique_kept": unique_kept,
        "hit_max_unique_pieces": hit_max_unique_pieces,
        "cutoff_freq_at_unique_cap": cutoff_freq,
        "kept_mass": kept_mass,
        "coverage": coverage,
        "rss_peak_mb": rss.peak_mb,
        "rss_end_mb": rss.last_mb,
        "training_corpus_sha256": corpus_hash,
    }
    return piece_counts, metadata
