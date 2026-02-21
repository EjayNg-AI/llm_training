"""Atomic write helpers for checkpoint and artifact safety."""

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
        # Some filesystems do not permit directory fsync.
        return


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{os.urandom(4).hex()}")
    with tmp.open("wb") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_directory(path.parent)


def atomic_dump_text(path: Path, text: str) -> None:
    _atomic_write_bytes(path, text.encode("utf-8"))


def atomic_dump_json(path: Path, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    atomic_dump_text(path, text)


def atomic_dump_pickle(path: Path, payload: Any) -> None:
    raw = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
    _atomic_write_bytes(path, raw)


def atomic_dump_pickle_with_checksum(path: Path, payload: Any) -> str:
    raw = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
    checksum = hashlib.sha256(raw).hexdigest()
    _atomic_write_bytes(path, raw)
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

