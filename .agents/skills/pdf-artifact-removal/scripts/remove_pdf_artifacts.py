#!/usr/bin/env python3
"""Detect and remove tagged PDF artifact blocks (/Watermark, /Header, /Footer).

This script follows the workflow in the `pdf-artifact-removal` skill:
1) detect tagged /Artifact ... BDC ... EMC blocks
2) optionally remove selected subtypes
3) save output to a new file by default (or in-place if explicitly requested)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List

import pikepdf

SUPPORTED_SUBTYPES = ("Watermark", "Header", "Footer")
_SUBTYPE_LOOKUP = {name.lower(): name for name in SUPPORTED_SUBTYPES}
_BBOX_RE = re.compile(r"/BBox\s*\[([^\]]+)\]")


def parse_subtypes(raw_values: Iterable[str]) -> List[str]:
    parsed: List[str] = []
    for raw in raw_values:
        for part in raw.split(","):
            token = part.strip()
            if not token:
                continue
            canonical = _SUBTYPE_LOOKUP.get(token.lower())
            if canonical is None:
                raise ValueError(
                    f"Unsupported subtype '{token}'. "
                    f"Use one or more of: {', '.join(SUPPORTED_SUBTYPES)}."
                )
            if canonical not in parsed:
                parsed.append(canonical)
    if not parsed:
        raise ValueError("No valid subtypes specified.")
    return parsed


def compile_patterns(subtypes: Iterable[str]) -> Dict[str, re.Pattern[str]]:
    return {
        subtype: re.compile(
            rf"/Artifact\s*<<[^>]*?/Subtype\s*/{re.escape(subtype)}[^>]*?>>\s*BDC\s.*?EMC\s*",
            flags=re.DOTALL,
        )
        for subtype in subtypes
    }


def get_page_streams(page: pikepdf.Page) -> List[pikepdf.Object]:
    contents = page.get("/Contents", None)
    if contents is None:
        return []
    if hasattr(contents, "read_bytes"):
        return [contents]
    return [obj for obj in contents if hasattr(obj, "read_bytes")]


def decode_stream(stream: pikepdf.Object) -> str:
    return stream.read_bytes().decode("latin-1", errors="ignore")


def detect_artifacts(
    pdf_path: Path, patterns: Dict[str, re.Pattern[str]]
) -> Dict[str, Dict[str, object]]:
    detection = {s: {"total_blocks": 0, "pages": []} for s in patterns}
    with pikepdf.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_counts = {s: 0 for s in patterns}
            page_bboxes = {s: [] for s in patterns}
            for stream in get_page_streams(page):
                data = decode_stream(stream)
                for subtype, pattern in patterns.items():
                    for match in pattern.finditer(data):
                        page_counts[subtype] += 1
                        bbox_match = _BBOX_RE.search(match.group(0))
                        if bbox_match:
                            page_bboxes[subtype].append(bbox_match.group(1).strip())
            for subtype, count in page_counts.items():
                if count == 0:
                    continue
                entry = {"page": page_num, "count": count}
                if page_bboxes[subtype]:
                    entry["bboxes"] = page_bboxes[subtype]
                detection[subtype]["total_blocks"] += count
                detection[subtype]["pages"].append(entry)
    return detection


def remove_artifacts(
    input_path: Path,
    output_path: Path,
    patterns: Dict[str, re.Pattern[str]],
    in_place: bool,
) -> Dict[str, object]:
    removed = {s: 0 for s in patterns}
    pages_cleaned = 0
    cleaned_pages = []

    with pikepdf.open(input_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_removed = {s: 0 for s in patterns}
            page_changed = False
            for stream in get_page_streams(page):
                original = decode_stream(stream)
                data = original
                for subtype, pattern in patterns.items():
                    data, count = pattern.subn("", data)
                    if count:
                        removed[subtype] += count
                        page_removed[subtype] += count
                if data != original:
                    stream.write(data.encode("latin-1"))
                    page_changed = True
            if page_changed:
                pages_cleaned += 1
                cleaned_pages.append(
                    {
                        "page": page_num,
                        "removed": {k: v for k, v in page_removed.items() if v},
                    }
                )

        save_kwargs = {"allow_overwriting_input": True} if in_place else {}
        pdf.save(str(output_path), **save_kwargs)

    return {
        "removed_blocks": removed,
        "pages_cleaned": pages_cleaned,
        "cleaned_pages": cleaned_pages,
    }


def make_output_path(
    input_path: Path,
    *,
    in_place: bool,
    suffix: str,
    output_dir: Path | None,
    explicit_output: Path | None,
) -> Path:
    if in_place:
        return input_path
    if explicit_output is not None:
        return explicit_output
    target_dir = output_dir if output_dir is not None else input_path.parent
    file_suffix = suffix if suffix.lower().endswith(".pdf") else f"{suffix}.pdf"
    return target_dir / f"{input_path.stem}{file_suffix}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Detect and remove tagged /Artifact blocks "
            "for /Watermark, /Header, and /Footer."
        )
    )
    parser.add_argument("pdfs", nargs="+", help="Input PDF paths.")
    parser.add_argument(
        "--remove",
        nargs="+",
        default=list(SUPPORTED_SUBTYPES),
        help=(
            "Subtypes to detect/remove (comma or space separated). "
            "Default: Watermark Header Footer"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detection only; do not modify files.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite input file(s). Disabled by default for safety.",
    )
    parser.add_argument(
        "--suffix",
        default=" - no watermark",
        help="Suffix for output filenames when not in-place and --output not used.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional output directory for generated files.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Explicit output path (single input file only).",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Optional JSON report path.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indent level for JSON output (default: 2).",
    )
    args = parser.parse_args()

    try:
        subtypes = parse_subtypes(args.remove)
    except ValueError as exc:
        parser.error(str(exc))

    input_paths = [Path(raw) for raw in args.pdfs]
    missing = [str(path) for path in input_paths if not path.exists()]
    if missing:
        parser.error(f"Input file(s) not found: {', '.join(missing)}")

    if args.output and len(input_paths) != 1:
        parser.error("--output can only be used with a single input PDF.")
    if args.in_place and args.output:
        parser.error("--in-place cannot be combined with --output.")
    if args.in_place and args.output_dir:
        parser.error("--in-place cannot be combined with --output-dir.")

    output_dir = Path(args.output_dir) if args.output_dir else None
    explicit_output = Path(args.output) if args.output else None

    patterns = compile_patterns(subtypes)
    results = []

    for input_path in input_paths:
        output_path = make_output_path(
            input_path,
            in_place=args.in_place,
            suffix=args.suffix,
            output_dir=output_dir,
            explicit_output=explicit_output,
        )

        detection = detect_artifacts(input_path, patterns)
        result = {
            "input": str(input_path),
            "output": str(output_path),
            "dry_run": bool(args.dry_run),
            "selected_subtypes": subtypes,
            "detection": detection,
            "detection_total_blocks": sum(
                subtype_data["total_blocks"] for subtype_data in detection.values()
            ),
        }

        if not args.dry_run:
            if not args.in_place:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            removal = remove_artifacts(
                input_path=input_path,
                output_path=output_path,
                patterns=patterns,
                in_place=args.in_place,
            )
            result.update(removal)
        else:
            result["removed_blocks"] = {s: 0 for s in subtypes}
            result["pages_cleaned"] = 0
            result["cleaned_pages"] = []

        results.append(result)

    report = {"results": results}
    report_text = json.dumps(report, indent=args.indent)
    print(report_text)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
