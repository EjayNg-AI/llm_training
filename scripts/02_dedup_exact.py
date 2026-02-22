"""Deterministic exact deduplication for corpus documents."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from llm_training.infra.hashing import sha256_text, stable_hash_object
from llm_training.infra.logging import setup_logger
from llm_training.infra.manifest import (
    build_artifact_manifest,
    collect_checksums,
    publish_artifact,
    resolve_artifact_dir,
)
from llm_training.infra.run_dir import begin_run, end_run, make_run_context, write_state

from pipeline_common import load_artifact_manifest_from_entry, load_registry_entry, load_yaml_config


DEFAULT_CONFIG: dict[str, Any] = {
    "run": {
        "output_dir": "artifacts/runs/02_dedup_exact",
        "log_level": "INFO",
        "structured_logs": True,
    },
    "artifacts_root": "artifacts",
    "input": {
        "corpus_id": None,
    },
    "artifact": {
        "id": None,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/dedup.yaml", help="Path to dedup stage config YAML.")
    parser.add_argument("--run-id", default=None, help="Optional run identifier under run.output_dir.")
    parser.add_argument("--corpus-id", default=None, help="Input corpus artifact id. Overrides config.")
    return parser.parse_args()


def _read_docs(path: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            docs.append(json.loads(raw))
    return docs


def main() -> None:
    args = parse_args()
    cfg, cfg_path = load_yaml_config(args.config, DEFAULT_CONFIG)

    run_cfg = cfg["run"]
    run_ctx = make_run_context(
        stage_name="02_dedup_exact",
        run_output_dir=Path(run_cfg["output_dir"]),
        config={k: v for k, v in cfg.items() if k != "meta"},
        run_id=args.run_id,
    )
    logger = setup_logger(
        name="pipeline.02_dedup_exact",
        run_dir=run_ctx.run_dir,
        log_level=run_cfg["log_level"],
        structured_logs=bool(run_cfg["structured_logs"]),
    )

    artifacts_root = Path(cfg["artifacts_root"])
    corpus_id = args.corpus_id or cfg["input"].get("corpus_id")
    corpus_entry = load_registry_entry(
        artifacts_root=artifacts_root,
        artifact_type="corpus",
        artifact_id=corpus_id,
        allow_latest=True,
    )
    corpus_manifest = load_artifact_manifest_from_entry(corpus_entry)
    corpus_artifact_dir = Path(corpus_entry["artifact_path"])
    docs_rel = str(corpus_manifest["stats"]["docs_file"])
    input_docs = corpus_artifact_dir / docs_rel
    if not input_docs.exists():
        raise FileNotFoundError(f"Corpus docs file missing: {input_docs}")

    dedup_signature = stable_hash_object(
        {
            "config_hash": cfg["meta"]["config_hash"],
            "source_corpus_id": corpus_manifest["artifact_id"],
            "source_corpus_checksums": corpus_manifest.get("checksums", {}),
        }
    )
    artifact_id = cfg["artifact"].get("id") or f"dedup_{dedup_signature[:12]}"
    artifact_dir = resolve_artifact_dir(artifacts_root, "corpus_dedup", artifact_id)

    if artifact_dir.exists() and any(artifact_dir.iterdir()):
        raise FileExistsError(
            f"Dedup artifact already exists: {artifact_dir}. Choose a different artifact.id or source corpus."
        )

    begin_run(
        run_ctx,
        config_path=str(cfg_path.resolve()),
        inputs={"corpus_id": corpus_manifest["artifact_id"], "artifact_id": artifact_id},
    )

    docs = _read_docs(input_docs)
    total_docs = len(docs)
    seen: dict[str, dict[str, Any]] = {}

    for doc in docs:
        text = doc.get("text", "")
        key = sha256_text(text)
        existing = seen.get(key)
        if existing is None or str(doc.get("doc_id", "")) < str(existing.get("doc_id", "")):
            seen[key] = doc

    deduped_docs = sorted(seen.values(), key=lambda row: str(row.get("doc_id", "")))
    kept_docs = len(deduped_docs)
    dropped_duplicates = total_docs - kept_docs

    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_docs = artifact_dir / "docs.dedup.jsonl.gz"
    with gzip.open(out_docs, "wt", encoding="utf-8") as handle:
        for doc in deduped_docs:
            handle.write(json.dumps(doc, sort_keys=True, ensure_ascii=False) + "\n")

    checksums = collect_checksums(artifact_dir)
    run_meta = json.loads(run_ctx.run_meta_path.read_text(encoding="utf-8"))
    manifest = build_artifact_manifest(
        artifact_type="corpus_dedup",
        artifact_id=artifact_id,
        source_run_id=run_ctx.run_id,
        config_hash=cfg["meta"]["config_hash"],
        git_commit=run_meta.get("git_commit"),
        inputs=[
            {
                "artifact_type": corpus_manifest["artifact_type"],
                "artifact_id": corpus_manifest["artifact_id"],
                "hash": stable_hash_object(corpus_manifest.get("checksums", {})),
            }
        ],
        stats={
            "source_corpus_id": corpus_manifest["artifact_id"],
            "total_docs": total_docs,
            "kept_docs": kept_docs,
            "dropped_duplicates": dropped_duplicates,
            "dedup_key": "sha256(text)",
            "docs_file": "docs.dedup.jsonl.gz",
        },
        checksums=checksums,
    )
    publish_artifact(artifacts_root=artifacts_root, artifact_dir=artifact_dir, manifest=manifest)

    write_state(
        run_ctx,
        {
            "resume_signature": dedup_signature,
            "status": "completed",
            "artifact_id": artifact_id,
            "source_corpus_id": corpus_manifest["artifact_id"],
            "total_docs": total_docs,
            "kept_docs": kept_docs,
            "dropped_duplicates": dropped_duplicates,
        },
    )
    end_run(
        run_ctx,
        status="completed",
        summary={
            "artifact_id": artifact_id,
            "source_corpus_id": corpus_manifest["artifact_id"],
            "kept_docs": kept_docs,
        },
    )
    logger.info(
        "Exact dedup complete. source_corpus_id=%s dedup_id=%s kept=%s dropped=%s",
        corpus_manifest["artifact_id"],
        artifact_id,
        kept_docs,
        dropped_duplicates,
    )


if __name__ == "__main__":
    main()
