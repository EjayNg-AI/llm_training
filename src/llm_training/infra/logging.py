"""Structured logger setup for stage scripts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


class JsonlFormatter(logging.Formatter):
    """Line-delimited JSON payloads for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "run_id"):
            payload["run_id"] = getattr(record, "run_id")
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(
    *,
    name: str,
    run_dir: Path,
    log_level: str = "INFO",
    structured_logs: bool = True,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(getattr(logging, str(log_level).upper(), logging.INFO))
    logger.propagate = False

    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(console)

    text_file = logging.FileHandler(logs_dir / "run.log", encoding="utf-8")
    text_file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(text_file)

    if structured_logs:
        json_file = logging.FileHandler(logs_dir / "run.jsonl", encoding="utf-8")
        json_file.setFormatter(JsonlFormatter())
        logger.addHandler(json_file)

    return logger
