"""Stage 1: parallel piece counting with progress checkpoints."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
import gzip
import hashlib
import json
import logging
from pathlib import Path
import re
import time
from typing import Any
import unicodedata

from .io_atomic import atomic_dump_json, atomic_dump_pickle, load_pickle_with_checksum
from .pretokenizer import compile_pattern, iter_pieces


CHECKPOINT_DIR_NAME = "checkpoints"
COUNTS_SNAPSHOT_NAME = "word_counts.snapshot.pkl"
PROGRESS_NAME = "word_counts.progress.json"

_WORKER_PATTERN = None
_WORKER_NORMALIZE = "none"
_WORKER_MAX_PIECE_BYTES = 200
_WORKER_SPECIAL_SPLIT_RE: re.Pattern[str] | None = None


def _compile_special_token_splitter(
    special_tokens: list[str] | tuple[str, ...],
    normalize: str,
) -> re.Pattern[str] | None:
    prepared_tokens = [
        unicodedata.normalize(normalize, token) if normalize != "none" else token
        for token in special_tokens
    ]
    prepared_tokens = sorted(set(prepared_tokens), key=lambda token: (-len(token), token))
    if not prepared_tokens:
        return None
    return re.compile("|".join(re.escape(token) for token in prepared_tokens))


def _iter_non_special_segments(text: str, split_re: re.Pattern[str] | None):
    if split_re is None:
        yield text
        return
    for segment in split_re.split(text):
        if segment:
            yield segment


def _worker_init(
    pattern_str: str,
    pattern_flags: int,
    normalize: str,
    max_piece_bytes: int,
    special_tokens: list[str],
) -> None:
    global _WORKER_PATTERN, _WORKER_NORMALIZE, _WORKER_MAX_PIECE_BYTES, _WORKER_SPECIAL_SPLIT_RE
    _WORKER_PATTERN = compile_pattern(pattern_str, pattern_flags)
    _WORKER_NORMALIZE = normalize
    _WORKER_MAX_PIECE_BYTES = max_piece_bytes
    _WORKER_SPECIAL_SPLIT_RE = _compile_special_token_splitter(special_tokens, normalize)


def _worker_count_batch(lines: list[str]) -> tuple[Counter[bytes], int]:
    if _WORKER_PATTERN is None:
        raise RuntimeError("Worker pretokenizer was not initialized.")

    local_counter: Counter[bytes] = Counter()
    total_pieces = 0

    for line in lines:
        if _WORKER_NORMALIZE != "none":
            line = unicodedata.normalize(_WORKER_NORMALIZE, line)
        for segment in _iter_non_special_segments(line, _WORKER_SPECIAL_SPLIT_RE):
            for piece in iter_pieces(_WORKER_PATTERN, segment):
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


def _compute_corpus_fingerprint(file_paths: list[Path]) -> str:
    h = hashlib.sha256()
    for path in sorted(file_paths):
        stat = path.stat()
        h.update(str(path).encode("utf-8"))
        h.update(str(stat.st_size).encode("utf-8"))
        h.update(str(stat.st_mtime_ns).encode("utf-8"))
    return h.hexdigest()


def _checkpoint_paths(run_dir: Path) -> tuple[Path, Path, Path]:
    checkpoint_dir = run_dir / CHECKPOINT_DIR_NAME
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    counts_path = checkpoint_dir / COUNTS_SNAPSHOT_NAME
    progress_path = checkpoint_dir / PROGRESS_NAME
    return checkpoint_dir, counts_path, progress_path


def _save_stage1_checkpoint(
    counts_path: Path,
    progress_path: Path,
    piece_counts: Counter[bytes],
    progress: dict[str, Any],
) -> None:
    snapshot_payload = {
        "piece_counts": dict(piece_counts),
        "config_hash": progress["config_hash"],
        "pattern_hash": progress["pattern_hash"],
        "timestamp": progress["timestamp"],
    }
    atomic_dump_pickle(counts_path, snapshot_payload)
    atomic_dump_json(progress_path, progress)


def _load_stage1_checkpoint(
    counts_path: Path,
    progress_path: Path,
    config_hash: str,
    pattern_hash: str,
) -> tuple[Counter[bytes], dict[str, Any]] | None:
    if not counts_path.exists() or not progress_path.exists():
        return None
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    if progress.get("config_hash") != config_hash:
        return None
    if progress.get("pattern_hash") != pattern_hash:
        return None

    try:
        snapshot = load_pickle_with_checksum(counts_path)
    except Exception:
        # Stage 1 snapshot does not require checksum sidecars; fallback to plain pickle load.
        snapshot = None
    if snapshot is None:
        return None
    if snapshot.get("config_hash") != config_hash:
        return None
    if snapshot.get("pattern_hash") != pattern_hash:
        return None
    piece_counts = Counter(snapshot.get("piece_counts", {}))
    return piece_counts, progress


def count_pieces(
    cfg: dict[str, Any],
    run_dir: Path,
    pattern_str: str,
    pattern_flags: int,
    pattern_hash: str,
    logger: logging.Logger,
    resume: bool,
) -> tuple[Counter[bytes], dict[str, Any]]:
    data_cfg = cfg["data"]
    checkpoint_cfg = cfg["checkpointing"]
    config_hash = cfg["meta"]["config_hash"]

    input_paths = _discover_input_files(data_cfg["input_paths"], data_cfg["input_format"])
    corpus_hash = _compute_corpus_fingerprint(input_paths)

    checkpoint_dir, counts_path, progress_path = _checkpoint_paths(run_dir)
    piece_counts: Counter[bytes] = Counter()
    progress = {
        "files": [{"path": str(path), "byte_offset": 0, "done": False} for path in input_paths],
        "total_lines_processed": 0,
        "total_pieces_seen": 0,
        "total_bytes_processed": 0,
        "config_hash": config_hash,
        "pattern_hash": pattern_hash,
        "snapshot_id": 0,
        "timestamp": int(time.time()),
    }

    if resume:
        loaded = _load_stage1_checkpoint(counts_path, progress_path, config_hash, pattern_hash)
        if loaded is not None:
            piece_counts, loaded_progress = loaded
            progress = loaded_progress
            logger.info(
                "Stage 1 resume loaded: lines=%s pieces=%s unique=%s",
                progress["total_lines_processed"],
                progress["total_pieces_seen"],
                len(piece_counts),
            )

    max_lines = data_cfg["max_lines"]
    max_bytes = data_cfg["max_bytes"]
    num_workers = int(data_cfg["num_workers"])
    batch_lines = int(data_cfg["batch_lines"])
    max_unique_pieces = data_cfg["max_unique_pieces"]
    snapshot_every_batches = int(checkpoint_cfg["stage1_snapshot_every_batches"])
    snapshot_every_seconds = int(checkpoint_cfg["snapshot_every_seconds"])
    stage1_cap_every_batches = int(checkpoint_cfg.get("stage1_cap_every_batches", 100))
    stage1_cap_start_lines = int(checkpoint_cfg.get("stage1_cap_start_lines", 10000))
    stage1_cap_safety_factor = float(checkpoint_cfg.get("stage1_cap_safety_factor", 1.10))

    logger.info(
        "Stage 1 starting: files=%s workers=%s batch_lines=%s",
        len(input_paths),
        num_workers,
        batch_lines,
    )

    merged_batches = 0
    last_snapshot_time = time.time()

    def should_stop() -> bool:
        if max_lines is not None and progress["total_lines_processed"] >= int(max_lines):
            return True
        if max_bytes is not None and progress["total_bytes_processed"] >= int(max_bytes):
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
            list(cfg["special_tokens"]["tokens"]),
        ),
    ) as executor:
        for file_state in progress["files"]:
            if file_state["done"]:
                continue
            if should_stop():
                break

            file_path = Path(file_state["path"])
            with _open_binary(file_path) as f:
                offset = int(file_state["byte_offset"])
                try:
                    f.seek(offset)
                except Exception:
                    # For streams where seek is unsupported, restart from beginning.
                    offset = 0
                    file_state["byte_offset"] = 0

                pending: dict[Future, tuple[int, int]] = {}
                completed: dict[int, tuple[int, Counter[bytes], int]] = {}
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
                            progress["total_lines_processed"] += 1
                            progress["total_bytes_processed"] += len(raw)
                            if should_stop():
                                break

                        if lines_read == 0:
                            reached_eof = True
                            break

                        end_offset = f.tell()
                        future = executor.submit(_worker_count_batch, batch)
                        pending[future] = (next_batch_id, end_offset)
                        next_batch_id += 1
                        if should_stop():
                            break

                    if not pending:
                        break

                    done, _ = wait(set(pending.keys()), return_when=FIRST_COMPLETED)
                    for done_future in done:
                        batch_id, end_offset = pending.pop(done_future)
                        local_counter, local_pieces = done_future.result()
                        completed[batch_id] = (end_offset, local_counter, int(local_pieces))

                    while next_batch_to_merge in completed:
                        end_offset, local_counter, local_pieces = completed.pop(next_batch_to_merge)
                        next_batch_to_merge += 1

                        piece_counts.update(local_counter)
                        progress["total_pieces_seen"] += local_pieces
                        file_state["byte_offset"] = end_offset
                        merged_batches += 1

                        # Keep a single deterministic approximation knob in Stage 1:
                        # optional top-K capping by absolute count.
                        if max_unique_pieces is not None:
                            periodic_cap = (
                                merged_batches % stage1_cap_every_batches == 0
                                and progress["total_lines_processed"] >= stage1_cap_start_lines
                            )
                            safety_cap = len(piece_counts) > int(
                                max_unique_pieces * stage1_cap_safety_factor
                            )
                            if periodic_cap or safety_cap:
                                unique_before = len(piece_counts)
                                piece_counts = _counter_top_k(piece_counts, int(max_unique_pieces))
                                if safety_cap and not periodic_cap:
                                    logger.info(
                                        "Stage 1 safety cap: unique_before=%s unique_after=%s "
                                        "max_unique_pieces=%s factor=%s",
                                        unique_before,
                                        len(piece_counts),
                                        max_unique_pieces,
                                        stage1_cap_safety_factor,
                                    )

                        now = time.time()
                        if (
                            merged_batches % snapshot_every_batches == 0
                            or (now - last_snapshot_time) >= snapshot_every_seconds
                        ):
                            progress["snapshot_id"] += 1
                            progress["timestamp"] = int(now)
                            _save_stage1_checkpoint(counts_path, progress_path, piece_counts, progress)
                            last_snapshot_time = now
                            logger.info(
                                "Stage 1 checkpoint: lines=%s pieces=%s unique=%s",
                                progress["total_lines_processed"],
                                progress["total_pieces_seen"],
                                len(piece_counts),
                            )

                if reached_eof and not should_stop():
                    file_state["done"] = True

    if max_unique_pieces is not None:
        piece_counts = _counter_top_k(piece_counts, int(max_unique_pieces))
    progress["snapshot_id"] += 1
    progress["timestamp"] = int(time.time())
    _save_stage1_checkpoint(counts_path, progress_path, piece_counts, progress)

    logger.info(
        "Stage 1 complete: lines=%s pieces=%s unique=%s",
        progress["total_lines_processed"],
        progress["total_pieces_seen"],
        len(piece_counts),
    )

    metadata = {
        "total_lines_processed": progress["total_lines_processed"],
        "total_pieces_seen": progress["total_pieces_seen"],
        "training_corpus_sha256": corpus_hash,
    }
    return piece_counts, metadata
