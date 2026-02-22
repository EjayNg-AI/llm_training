"""Shared helpers for stage scripts."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from llm_training.infra.hashing import stable_hash_object
from llm_training.infra.manifest import find_artifact, latest_artifact, load_manifest


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_yaml_config(path: str | Path, defaults: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Top-level YAML config must be a mapping")
    cfg = deep_merge(defaults, raw)
    cfg["meta"] = {
        "config_path": str(cfg_path.resolve()),
        "config_hash": stable_hash_object({k: v for k, v in cfg.items() if k != "meta"}),
    }
    return cfg, cfg_path


def load_registry_entry(
    *,
    artifacts_root: Path,
    artifact_type: str,
    artifact_id: str | None,
    allow_latest: bool = True,
) -> dict[str, Any]:
    registry_path = artifacts_root / "registry.jsonl"
    entry = None
    if artifact_id:
        entry = find_artifact(registry_path, artifact_type, artifact_id)
        if entry is None:
            raise FileNotFoundError(
                f"Artifact not found in registry: type={artifact_type} id={artifact_id}"
            )
    elif allow_latest:
        entry = latest_artifact(registry_path, artifact_type)
        if entry is None:
            raise FileNotFoundError(f"No artifact of type {artifact_type} found in registry")
    else:
        raise ValueError(f"artifact_id is required for type {artifact_type}")
    return entry


def load_artifact_manifest_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    manifest_path = Path(entry["manifest_path"])
    if not manifest_path.exists():
        raise FileNotFoundError(f"Artifact manifest missing: {manifest_path}")
    return load_manifest(manifest_path)


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
