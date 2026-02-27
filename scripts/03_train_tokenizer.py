"""Train and export a GPT-2 style byte-level BPE tokenizer."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import subprocess
import time
from typing import Any

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from llm_training.infra.hashing import stable_hash_object
from llm_training.infra.manifest import (
    build_artifact_manifest,
    collect_checksums,
    publish_artifact,
    resolve_artifact_dir,
)

from tokenizer_bpe.config import build_pattern_hash, load_config
from tokenizer_bpe.export import export_tokenizer
from tokenizer_bpe.io_atomic import atomic_dump_json
from tokenizer_bpe.pretokenizer import resolve_pattern
from tokenizer_bpe.stage1_count import count_pieces
from tokenizer_bpe.stage2_init import initialize_training_state
from tokenizer_bpe.stage3_train import train_bpe


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_run_id(explicit_run_id: str | None) -> str:
    if explicit_run_id:
        return explicit_run_id
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _setup_logging(cfg: dict[str, Any]) -> logging.Logger:
    logger = logging.getLogger("tokenizer_bpe")
    logger.handlers.clear()
    logger.setLevel(getattr(logging, cfg["run"]["log_level"], logging.INFO))
    logger.propagate = False

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(console)
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/tokenizer_bpe.yaml",
        help="Path to tokenizer training config YAML.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier under run.output_dir.",
    )
    parser.add_argument(
        "--stop-after-merges",
        type=int,
        default=None,
        help="Optional absolute merge index at which to stop early (debug/testing).",
    )
    parser.add_argument(
        "--artifact-id",
        default=None,
        help="Published tokenizer artifact id under artifacts/tokenizer/exports. Deterministic if omitted.",
    )
    parser.add_argument(
        "--artifacts-root",
        default="artifacts",
        help="Root artifact directory containing registry.jsonl and stage outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    run_id = _resolve_run_id(args.run_id)
    run_dir = Path(cfg["run"]["output_dir"]) / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(
            f"Run directory already exists and is not empty: {run_dir}\n"
            "Pass a different --run-id."
        )
    run_dir.mkdir(parents=True, exist_ok=True)

    logger = _setup_logging(cfg)
    logger.info("Run directory: %s", run_dir)
    logger.info("Config hash: %s", cfg["meta"]["config_hash"])

    training_started_at = _utc_now_iso()
    timer_start = time.perf_counter()

    try:
        pattern_alias, pattern_str, pattern_flags, regex_version = resolve_pattern(cfg["pretokenizer"])
        pattern_hash = build_pattern_hash(
            pattern_str=pattern_str,
            pattern_flags=pattern_flags,
            normalize=cfg["data"]["normalize"],
            regex_version=regex_version,
        )
        logger.info(
            "Pretokenizer alias=%s regex_version=%s pattern_hash=%s",
            pattern_alias,
            regex_version,
            pattern_hash,
        )

        piece_counts, stage1_meta = count_pieces(
            cfg=cfg,
            run_dir=run_dir,
            pattern_str=pattern_str,
            pattern_flags=pattern_flags,
            pattern_hash=pattern_hash,
            logger=logger,
        )

        init_state = initialize_training_state(piece_counts=piece_counts, cfg=cfg, logger=logger)

        train_state = train_bpe(
            cfg=cfg,
            run_dir=run_dir,
            initial_state=init_state,
            logger=logger,
            config_hash=cfg["meta"]["config_hash"],
            pattern_hash=pattern_hash,
            stop_after_merges=args.stop_after_merges,
        )

        source_signature = stable_hash_object(
            {
                "config_hash": cfg["meta"]["config_hash"],
                "pattern_hash": pattern_hash,
                "corpus_hash": stage1_meta["training_corpus_sha256"],
                "vocab_size": cfg["bpe"]["vocab_size"],
                "special_tokens": cfg["special_tokens"]["tokens"],
            }
        )
        artifact_id = args.artifact_id or f"tokenizer_{source_signature[:12]}"

        artifacts_root = Path(args.artifacts_root)
        export_dir = resolve_artifact_dir(artifacts_root, "tokenizer", artifact_id)
        if export_dir.exists() and any(export_dir.iterdir()):
            raise FileExistsError(
                f"Tokenizer artifact already exists: {export_dir}. "
                "Pass --artifact-id with a new value if you need another export."
            )

        export_tokenizer(
            cfg=cfg,
            run_dir=run_dir,
            export_dir=export_dir,
            train_state=train_state,
            pattern_alias=pattern_alias,
            pattern_str=pattern_str,
            pattern_flags=pattern_flags,
            pattern_hash=pattern_hash,
            config_hash=cfg["meta"]["config_hash"],
            corpus_hash=stage1_meta["training_corpus_sha256"],
            logger=logger,
        )

        checksums = collect_checksums(export_dir)
        manifest = build_artifact_manifest(
            artifact_type="tokenizer",
            artifact_id=artifact_id,
            source_run_id=run_id,
            config_hash=cfg["meta"]["config_hash"],
            git_commit=_safe_git_commit(),
            inputs=[
                {
                    "artifact_type": "raw_files",
                    "artifact_id": "training_corpus",
                    "hash": stage1_meta["training_corpus_sha256"],
                }
            ],
            stats={
                "pattern_alias": pattern_alias,
                "pattern_hash": pattern_hash,
                "training_corpus_sha256": stage1_meta["training_corpus_sha256"],
                "vocab_size": len(train_state["id_to_token_bytes"]) + len(cfg["special_tokens"]["tokens"]),
                "num_merges": len(train_state["merge_pairs"]),
                "export_dir": str(export_dir),
                "elapsed_seconds": max(0.0, time.perf_counter() - timer_start),
            },
            checksums=checksums,
        )
        publish_artifact(artifacts_root=artifacts_root, artifact_dir=export_dir, manifest=manifest)
        logger.info("Tokenizer export complete: %s (artifact_id=%s)", export_dir, artifact_id)
    finally:
        training_ended_at = _utc_now_iso()
        elapsed_seconds = max(0.0, time.perf_counter() - timer_start)
        atomic_dump_json(
            run_dir / "training_telemetry.json",
            {
                "training_started_at": training_started_at,
                "training_ended_at": training_ended_at,
                "elapsed_seconds": elapsed_seconds,
            },
        )
        logger.info("Training duration: elapsed_seconds=%.3f", elapsed_seconds)


if __name__ == "__main__":
    main()
