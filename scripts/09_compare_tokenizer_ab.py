"""Compare tokenizer runs on merge overlap and held-out tokenization efficiency."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from tokenizer_bpe.ab_compare import build_ab_stability_metrics
from tokenizer_bpe.io_atomic import atomic_dump_json
from tokenizer_bpe.report_data_collection import write_data_collection_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-statistics", required=True, help="Path to base run_statistics.json to update.")
    parser.add_argument("--export-a", required=True, help="Tokenizer export dir for run A.")
    parser.add_argument("--export-b", required=True, help="Tokenizer export dir for run B.")
    parser.add_argument("--run-a", required=True, help="Identifier for run A.")
    parser.add_argument("--run-b", required=True, help="Identifier for run B.")
    parser.add_argument("--heldout-text", required=True, help="Held-out text file for tokenization efficiency checks.")
    parser.add_argument(
        "--report-path",
        default="docs/data_collection_report.md",
        help="Markdown report output path to regenerate.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_stats_path = Path(args.run_statistics)
    if not run_stats_path.exists():
        raise FileNotFoundError(f"run statistics file not found: {run_stats_path}")
    run_stats = json.loads(run_stats_path.read_text(encoding="utf-8"))

    ab_metrics = build_ab_stability_metrics(
        export_dir_a=Path(args.export_a),
        export_dir_b=Path(args.export_b),
        heldout_path=Path(args.heldout_text),
        run_a=args.run_a,
        run_b=args.run_b,
    )
    run_stats["ab_stability"] = ab_metrics
    atomic_dump_json(run_stats_path, run_stats)
    write_data_collection_report(run_stats, Path(args.report_path))


if __name__ == "__main__":
    main()

