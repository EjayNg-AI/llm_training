"""Artifact manifest and registry helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .hashing import sha256_file
from .io_atomic import atomic_append_jsonl, atomic_dump_json


SCHEMA_VERSION = "1.0"


ARTIFACT_PATHS: dict[str, str] = {
    "corpus": "corpora",
    "corpus_dedup": "corpora",
    "tokenizer": "tokenizer/exports",
    "tokens": "tokens",
    "packed": "packed",
    "model": "models",
    "eval": "eval",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_artifact_dir(artifacts_root: Path, artifact_type: str, artifact_id: str) -> Path:
    subpath = ARTIFACT_PATHS.get(artifact_type, artifact_type)
    return artifacts_root / subpath / artifact_id


def build_artifact_manifest(
    *,
    artifact_type: str,
    artifact_id: str,
    source_run_id: str,
    config_hash: str,
    git_commit: str | None,
    inputs: list[dict[str, Any]],
    stats: dict[str, Any],
    checksums: dict[str, str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "artifact_id": artifact_id,
        "created_at": _utc_now(),
        "source_run_id": source_run_id,
        "config_hash": config_hash,
        "git_commit": git_commit,
        "inputs": inputs,
        "stats": stats,
        "checksums": checksums,
    }
    if extra:
        payload.update(extra)
    return payload


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_checksums(artifact_dir: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for candidate in sorted(artifact_dir.rglob("*")):
        if not candidate.is_file():
            continue
        if candidate.name == "artifact_manifest.json":
            continue
        rel = candidate.relative_to(artifact_dir).as_posix()
        checksums[rel] = sha256_file(candidate)
    return checksums


def verify_checksums(artifact_dir: Path, checksums: dict[str, str]) -> None:
    for rel, expected in checksums.items():
        path = artifact_dir / rel
        if not path.exists():
            raise FileNotFoundError(f"Manifest file missing from artifact dir: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Checksum mismatch for {path}: expected {expected}, got {actual}")


def publish_artifact(
    *,
    artifacts_root: Path,
    artifact_dir: Path,
    manifest: dict[str, Any],
) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = artifact_dir / "artifact_manifest.json"
    atomic_dump_json(manifest_path, manifest)

    registry_entry = {
        "created_at": manifest["created_at"],
        "artifact_type": manifest["artifact_type"],
        "artifact_id": manifest["artifact_id"],
        "artifact_path": str(artifact_dir),
        "manifest_path": str(manifest_path),
        "source_run_id": manifest["source_run_id"],
        "config_hash": manifest["config_hash"],
        "inputs": manifest.get("inputs", []),
    }
    atomic_append_jsonl(artifacts_root / "registry.jsonl", registry_entry)
    return manifest_path


def iter_registry(registry_path: Path) -> list[dict[str, Any]]:
    if not registry_path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in registry_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        out.append(json.loads(line))
    return out


def find_artifact(registry_path: Path, artifact_type: str, artifact_id: str) -> dict[str, Any] | None:
    entries = iter_registry(registry_path)
    for entry in reversed(entries):
        if entry.get("artifact_type") == artifact_type and entry.get("artifact_id") == artifact_id:
            return entry
    return None


def latest_artifact(registry_path: Path, artifact_type: str) -> dict[str, Any] | None:
    entries = iter_registry(registry_path)
    for entry in reversed(entries):
        if entry.get("artifact_type") == artifact_type:
            return entry
    return None
