"""Atomic write helpers for robust stage outputs."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
from pathlib import Path
from typing import Any


def _fsync_directory(path: Path) -> None:
    try:
        dir_fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        # Some filesystems do not allow directory fsync.
        return


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{os.urandom(4).hex()}")
    with tmp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    _fsync_directory(path.parent)


def atomic_dump_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def atomic_dump_json(path: Path, payload: Any, *, sort_keys: bool = True, indent: int = 2) -> None:
    content = json.dumps(payload, sort_keys=sort_keys, indent=indent, ensure_ascii=False) + "\n"
    atomic_dump_text(path, content)


def atomic_append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append to a JSONL file using write-rename for crash safety."""
    path.parent.mkdir(parents=True, exist_ok=True)
    prior = b""
    if path.exists():
        prior = path.read_bytes()
    line = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    atomic_write_bytes(path, prior + line)


def atomic_dump_pickle(path: Path, payload: Any) -> None:
    atomic_write_bytes(path, pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))


def atomic_dump_pickle_with_checksum(path: Path, payload: Any) -> str:
    raw = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
    checksum = hashlib.sha256(raw).hexdigest()
    atomic_write_bytes(path, raw)
    atomic_dump_text(path.with_suffix(path.suffix + ".sha256"), checksum + "\n")
    return checksum


def load_pickle_with_checksum(path: Path) -> Any:
    raw = path.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    checksum_path = path.with_suffix(path.suffix + ".sha256")
    if checksum_path.exists():
        expected = checksum_path.read_text(encoding="utf-8").strip()
        if checksum != expected:
            raise ValueError(f"Checksum mismatch for snapshot: {path}")
    return pickle.loads(raw)
