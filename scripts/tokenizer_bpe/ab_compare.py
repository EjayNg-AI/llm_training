"""Tokenizer A/B stability comparison helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from llm_training.tokenizer.runtime import ByteLevelBPETokenizer

from .io_atomic import atomic_dump_json


def _read_merge_lines(export_dir: Path) -> list[str]:
    merges_path = export_dir / "merges.txt"
    lines = merges_path.read_text(encoding="utf-8").splitlines()
    return [line for line in lines[1:] if line.strip()]


def _overlap_ratio(a: list[str], b: list[str], top_k: int) -> float:
    if top_k <= 0:
        return 0.0
    a_set = set(a[:top_k])
    b_set = set(b[:top_k])
    denom = max(1, min(top_k, len(a_set), len(b_set)))
    return float(len(a_set & b_set) / denom)


def _token_efficiency_metrics(tokenizer: ByteLevelBPETokenizer, text: str) -> dict[str, float]:
    token_count = len(tokenizer.encode(text))
    char_count = len(text)
    word_count = len(re.findall(r"\S+", text))
    return {
        "token_count": float(token_count),
        "tokens_per_char": (float(token_count) / char_count) if char_count > 0 else 0.0,
        "tokens_per_word": (float(token_count) / word_count) if word_count > 0 else 0.0,
    }


def build_ab_stability_metrics(
    *,
    export_dir_a: Path,
    export_dir_b: Path,
    heldout_path: Path,
    run_a: str,
    run_b: str,
) -> dict[str, Any]:
    merges_a = _read_merge_lines(export_dir_a)
    merges_b = _read_merge_lines(export_dir_b)
    heldout_text = heldout_path.read_text(encoding="utf-8")

    tok_a = ByteLevelBPETokenizer.from_dir(export_dir_a)
    tok_b = ByteLevelBPETokenizer.from_dir(export_dir_b)
    eff_a = _token_efficiency_metrics(tok_a, heldout_text)
    eff_b = _token_efficiency_metrics(tok_b, heldout_text)

    return {
        "run_a": run_a,
        "run_b": run_b,
        "heldout_path": str(heldout_path),
        "merge_overlap_top_1000": _overlap_ratio(merges_a, merges_b, 1000),
        "merge_overlap_top_5000": _overlap_ratio(merges_a, merges_b, 5000),
        "merge_overlap_top_10000": _overlap_ratio(merges_a, merges_b, 10000),
        "tokens_per_char_a": eff_a["tokens_per_char"],
        "tokens_per_char_b": eff_b["tokens_per_char"],
        "tokens_per_char_delta": eff_b["tokens_per_char"] - eff_a["tokens_per_char"],
        "tokens_per_word_a": eff_a["tokens_per_word"],
        "tokens_per_word_b": eff_b["tokens_per_word"],
        "tokens_per_word_delta": eff_b["tokens_per_word"] - eff_a["tokens_per_word"],
    }


def attach_ab_metrics(run_statistics_path: Path, ab_metrics: dict[str, Any]) -> None:
    payload = {}
    if run_statistics_path.exists():
        import json

        payload = json.loads(run_statistics_path.read_text(encoding="utf-8"))
    payload["ab_stability"] = ab_metrics
    atomic_dump_json(run_statistics_path, payload)

