"""Resume gate helpers for stage safety checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .hashing import stable_hash_object


def build_resume_signature(payload: dict[str, Any]) -> str:
    """Build deterministic signature used to validate resume compatibility."""
    return stable_hash_object(payload)


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def assert_resume_compatible(
    *,
    state_path: Path,
    expected_signature: str,
    signature_field: str = "resume_signature",
) -> dict[str, Any]:
    state = load_state(state_path)
    if state is None:
        raise FileNotFoundError(f"Missing state file for resume: {state_path}")

    seen = state.get(signature_field)
    if seen != expected_signature:
        raise ValueError(
            "Resume gate mismatch. "
            f"Expected {signature_field}={expected_signature}, found {seen}."
        )
    return state
