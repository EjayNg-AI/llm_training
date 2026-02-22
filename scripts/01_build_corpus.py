"""Build canonical corpus documents from raw text/jsonl inputs."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import unicodedata
from typing import Any, Iterator

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from llm_training.infra.hashing import sha256_file, sha256_text, stable_hash_object
from llm_training.infra.logging import setup_logger
from llm_training.infra.manifest import (
    build_artifact_manifest,
    collect_checksums,
    publish_artifact,
    resolve_artifact_dir,
)
from llm_training.infra.run_dir import begin_run, end_run, make_run_context, write_state

from pipeline_common import load_yaml_config


DEFAULT_CONFIG: dict[str, Any] = {
    "run": {
        "output_dir": "artifacts/runs/01_build_corpus",
        "log_level": "INFO",
        "structured_logs": True,
    },
    "artifacts_root": "artifacts",
    "data": {
        "input_paths": [
            "data/raw/train.txt",
            "data/raw/validation.txt",
            "data/raw/test.txt",
        ],
        "input_format": "text",
        "jsonl_text_field": "text",
        "decode_errors": "replace",
        "normalize": "none",
        "min_chars": 20,
        "max_docs": None,
    },
    "artifact": {
        "id": None,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/corpus.yaml", help="Path to corpus stage config YAML.")
    parser.add_argument("--run-id", default=None, help="Optional run identifier under run.output_dir.")
    return parser.parse_args()


def _iter_input_files(input_paths: list[str]) -> list[Path]:
    candidates: set[Path] = set()
    for item in input_paths:
        path = Path(item)
        if path.is_file():
            candidates.add(path.resolve())
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    candidates.add(child.resolve())
    return sorted(candidates)


def _open_text(path: Path, *, decode_errors: str):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors=decode_errors)
    return path.open("r", encoding="utf-8", errors=decode_errors)


def _iter_docs_from_file(path: Path, data_cfg: dict[str, Any]) -> Iterator[tuple[int, str]]:
    decode_errors = str(data_cfg["decode_errors"])
    input_format = str(data_cfg["input_format"])
    jsonl_text_field = str(data_cfg["jsonl_text_field"])
    normalize_mode = str(data_cfg["normalize"])

    with _open_text(path, decode_errors=decode_errors) as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            text: str | None
            if input_format == "jsonl":
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                value = payload.get(jsonl_text_field)
                text = value if isinstance(value, str) else None
            else:
                text = raw_line

            if text is None:
                continue

            cleaned = " ".join(text.strip().split())
            if normalize_mode != "none":
                cleaned = unicodedata.normalize(normalize_mode, cleaned)
            yield line_no, cleaned


def _build_doc_record(*, source: str, line_no: int, text: str) -> dict[str, Any]:
    doc_id_payload = {"source": source, "line_no": line_no, "text": text}
    doc_id = sha256_text(json.dumps(doc_id_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return {
        "doc_id": doc_id,
        "text": text,
        "source": source,
        "timestamp": None,
        "meta": {
            "lang": None,
            "license": None,
            "tags": [],
        },
    }


def main() -> None:
    args = parse_args()
    cfg, cfg_path = load_yaml_config(args.config, DEFAULT_CONFIG)

    run_cfg = cfg["run"]
    run_ctx = make_run_context(
        stage_name="01_build_corpus",
        run_output_dir=Path(run_cfg["output_dir"]),
        config={k: v for k, v in cfg.items() if k != "meta"},
        run_id=args.run_id,
    )
    logger = setup_logger(
        name="pipeline.01_build_corpus",
        run_dir=run_ctx.run_dir,
        log_level=run_cfg["log_level"],
        structured_logs=bool(run_cfg["structured_logs"]),
    )

    files = _iter_input_files(list(cfg["data"]["input_paths"]))
    if not files:
        raise FileNotFoundError("No input files found for corpus stage.")

    input_file_hashes = [{"path": str(path), "sha256": sha256_file(path)} for path in files]
    source_signature = stable_hash_object(
        {
            "config_hash": cfg["meta"]["config_hash"],
            "input_files": input_file_hashes,
        }
    )
    artifact_id = cfg["artifact"].get("id") or f"corpus_{source_signature[:12]}"

    artifacts_root = Path(cfg["artifacts_root"])
    artifact_dir = resolve_artifact_dir(artifacts_root, "corpus", artifact_id)
    if artifact_dir.exists() and any(artifact_dir.iterdir()):
        raise FileExistsError(
            f"Corpus artifact already exists: {artifact_dir}. Choose a different artifact.id or change inputs."
        )

    begin_run(
        run_ctx,
        config_path=str(cfg_path.resolve()),
        inputs={"input_paths": [str(path) for path in files], "artifact_id": artifact_id},
    )

    docs_path = artifact_dir / "docs.jsonl.gz"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    min_chars = int(cfg["data"]["min_chars"])
    max_docs = cfg["data"].get("max_docs")
    max_docs = None if max_docs is None else int(max_docs)

    kept_docs = 0
    dropped_short = 0
    total_text_bytes = 0

    logger.info("Writing corpus artifact %s to %s", artifact_id, artifact_dir)
    with gzip.open(docs_path, "wt", encoding="utf-8") as out:
        for idx, path in enumerate(files, start=1):
            source = str(path)
            for line_no, text in _iter_docs_from_file(path, cfg["data"]):
                if len(text) < min_chars:
                    dropped_short += 1
                    continue

                record = _build_doc_record(source=source, line_no=line_no, text=text)
                out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                kept_docs += 1
                total_text_bytes += len(text.encode("utf-8"))

                if max_docs is not None and kept_docs >= max_docs:
                    break

            write_state(
                run_ctx,
                {
                    "resume_signature": source_signature,
                    "artifact_id": artifact_id,
                    "processed_files": idx,
                    "total_files": len(files),
                    "kept_docs": kept_docs,
                    "dropped_short": dropped_short,
                },
            )
            if max_docs is not None and kept_docs >= max_docs:
                break

    checksums = collect_checksums(artifact_dir)
    run_meta = json.loads(run_ctx.run_meta_path.read_text(encoding="utf-8"))
    manifest = build_artifact_manifest(
        artifact_type="corpus",
        artifact_id=artifact_id,
        source_run_id=run_ctx.run_id,
        config_hash=cfg["meta"]["config_hash"],
        git_commit=run_meta.get("git_commit"),
        inputs=[
            {
                "artifact_type": "raw_files",
                "artifact_id": "raw_input",
                "files": input_file_hashes,
            }
        ],
        stats={
            "doc_count": kept_docs,
            "dropped_short": dropped_short,
            "total_text_bytes": total_text_bytes,
            "input_file_count": len(files),
            "docs_file": "docs.jsonl.gz",
        },
        checksums=checksums,
    )
    publish_artifact(artifacts_root=artifacts_root, artifact_dir=artifact_dir, manifest=manifest)

    write_state(
        run_ctx,
        {
            "resume_signature": source_signature,
            "artifact_id": artifact_id,
            "status": "completed",
            "kept_docs": kept_docs,
            "dropped_short": dropped_short,
        },
    )
    end_run(
        run_ctx,
        status="completed",
        summary={
            "artifact_id": artifact_id,
            "doc_count": kept_docs,
            "dropped_short": dropped_short,
        },
    )
    logger.info("Corpus stage complete. artifact_id=%s docs=%s", artifact_id, kept_docs)


if __name__ == "__main__":
    main()
