from __future__ import annotations

import json
from pathlib import Path

from llm_training.infra.io_atomic import atomic_append_jsonl, atomic_dump_json, atomic_dump_text


def test_atomic_append_jsonl_appends_lines(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    atomic_append_jsonl(path, {"step": 1, "loss": 1.0})
    atomic_append_jsonl(path, {"step": 2, "loss": 0.9})

    lines = path.read_text(encoding="utf-8").splitlines()
    payloads = [json.loads(line) for line in lines]
    assert payloads == [{"loss": 1.0, "step": 1}, {"loss": 0.9, "step": 2}]


def test_atomic_dump_helpers_write_payloads(tmp_path: Path) -> None:
    text_path = tmp_path / "note.txt"
    json_path = tmp_path / "state.json"

    atomic_dump_text(text_path, "hello\n")
    atomic_dump_json(json_path, {"ok": True})

    assert text_path.read_text(encoding="utf-8") == "hello\n"
    assert json.loads(json_path.read_text(encoding="utf-8")) == {"ok": True}
