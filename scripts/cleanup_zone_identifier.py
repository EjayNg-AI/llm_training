#!/usr/bin/env python3
"""Remove files with 'Zone.Identifier' in their filename from the repository."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def iter_target_files(root: Path, skip_dirs: set[str]) -> list[Path]:
    targets: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Do not descend into known Python environment folders
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".venv")]

        for name in filenames:
            if "Zone.Identifier" in name:
                targets.append(Path(dirpath) / name)
    return targets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Delete files whose filenames contain 'Zone.Identifier'."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Directory to scan (default: current directory).",
    )
    parser.add_argument(
        "--skip-dir",
        action="append",
        default=[],
        help=(
            "Additional directory names to skip (can be passed multiple times). "
            "Defaults include .venv, venv, env, ENV, .pythonenvs."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be removed without deleting.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    skip_dirs = {".venv", "venv", "env", "ENV", ".pythonenvs", ".env"}
    skip_dirs.update(args.skip_dir)

    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Root path does not exist: {root}")

    target_files = iter_target_files(root, skip_dirs)

    if args.dry_run:
        for p in target_files:
            print(p)
        print(f"Dry run: {len(target_files)} file(s) would be removed.")
        return 0

    removed = 0
    failed: list[str] = []
    for p in target_files:
        try:
            p.unlink()
            removed += 1
            print(f"removed: {p}")
        except OSError as exc:
            failed.append(f"{p}: {exc}")
            print(f"failed: {p} ({exc})")

    print(f"removed {removed} file(s).")
    if failed:
        print(f"failed to remove {len(failed)} file(s).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
