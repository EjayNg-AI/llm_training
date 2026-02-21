from __future__ import annotations

import logging
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def tokenizer_logger() -> logging.Logger:
    logger = logging.getLogger("tests.tokenizer_bpe")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


@pytest.fixture
def tiny_corpus_text() -> str:
    fixture_path = ROOT / "tests" / "fixtures" / "tokenizer_bpe" / "tiny_corpus.txt"
    return fixture_path.read_text(encoding="utf-8") + "\n"
