"""Run directory lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import socket
import subprocess
from typing import Any

from .hashing import stable_hash_object
from .io_atomic import atomic_append_jsonl, atomic_dump_json, atomic_dump_text


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_run_id(explicit_run_id: str | None = None) -> str:
    if explicit_run_id:
        return explicit_run_id
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


@dataclass(slots=True)
class RunContext:
    stage_name: str
    run_id: str
    run_dir: Path
    config_hash: str
    metrics_path: Path
    state_path: Path
    run_meta_path: Path


def make_run_context(
    *,
    stage_name: str,
    run_output_dir: Path,
    config: dict[str, Any],
    run_id: str | None,
) -> RunContext:
    resolved_run_id = resolve_run_id(run_id)
    run_dir = run_output_dir / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    return RunContext(
        stage_name=stage_name,
        run_id=resolved_run_id,
        run_dir=run_dir,
        config_hash=stable_hash_object(config),
        metrics_path=run_dir / "metrics.jsonl",
        state_path=run_dir / "state.json",
        run_meta_path=run_dir / "run_meta.json",
    )


def begin_run(
    ctx: RunContext,
    *,
    config_path: str,
    inputs: dict[str, Any] | None = None,
) -> None:
    payload = {
        "stage": ctx.stage_name,
        "run_id": ctx.run_id,
        "status": "running",
        "started_at": _utc_now(),
        "config_hash": ctx.config_hash,
        "config_path": config_path,
        "inputs": inputs or {},
        "git_commit": _safe_git_commit(),
        "python_version": platform.python_version(),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
    }
    atomic_dump_json(ctx.run_meta_path, payload)
    if not ctx.metrics_path.exists():
        atomic_dump_text(ctx.metrics_path, "")
    if not ctx.state_path.exists():
        atomic_dump_json(
            ctx.state_path,
            {
                "run_id": ctx.run_id,
                "stage": ctx.stage_name,
                "status": "running",
            },
        )


def end_run(
    ctx: RunContext,
    *,
    status: str,
    summary: dict[str, Any] | None = None,
) -> None:
    prior = {}
    if ctx.run_meta_path.exists():
        import json

        prior = json.loads(ctx.run_meta_path.read_text(encoding="utf-8"))
    prior.update({"status": status, "ended_at": _utc_now(), "summary": summary or {}})
    atomic_dump_json(ctx.run_meta_path, prior)


def write_state(ctx: RunContext, state: dict[str, Any]) -> None:
    payload = {"run_id": ctx.run_id, "stage": ctx.stage_name, **state}
    atomic_dump_json(ctx.state_path, payload)


def write_stage_metric(ctx: RunContext, payload: dict[str, Any]) -> None:
    line = {
        "timestamp": _utc_now(),
        "run_id": ctx.run_id,
        "stage": ctx.stage_name,
        **payload,
    }
    atomic_append_jsonl(ctx.metrics_path, line)
