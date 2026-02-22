from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
SCRIPTS_DIR = ROOT / "scripts"

for path in [str(SRC_DIR), str(SCRIPTS_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)
