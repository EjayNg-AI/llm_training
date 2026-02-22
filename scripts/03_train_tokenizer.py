"""Train and export a resumable GPT-2 style byte-level BPE tokenizer."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
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
from llm_training.infra.run_dir import begin_run, end_run, make_run_context

from tokenizer_bpe.config import build_pattern_hash, load_config
from tokenizer_bpe.export import export_tokenizer
from tokenizer_bpe.pretokenizer import resolve_pattern
from tokenizer_bpe.stage1_count import count_pieces
from tokenizer_bpe.stage2_init import initialize_training_state
from tokenizer_bpe.stage3_train import train_bpe


class JsonlFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False)


def _setup_logging(run_dir: Path, cfg: dict[str, Any]) -> logging.Logger:
    logger = logging.getLogger("tokenizer_bpe")
    logger.handlers.clear()
    logger.setLevel(getattr(logging, cfg["run"]["log_level"], logging.INFO))
    logger.propagate = False

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(console)

    run_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(run_dir / "train.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)

    if cfg["run"]["structured_logs"]:
        json_handler = logging.FileHandler(run_dir / "train.jsonl", encoding="utf-8")
        json_handler.setFormatter(JsonlFormatter())
        logger.addHandler(json_handler)

    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/tokenizer_bpe.yaml",
        help="Path to tokenizer training config YAML.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing checkpoints and WAL in the selected run directory.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier under run.output_dir. Required for deterministic resume targeting.",
    )
    parser.add_argument(
        "--stop-after-merges",
        type=int,
        default=None,
        help="Optional absolute merge index at which to stop early (debug/recovery testing).",
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

    run_ctx = make_run_context(
        stage_name="03_train_tokenizer",
        run_output_dir=Path(cfg["run"]["output_dir"]),
        config={k: v for k, v in cfg.items() if k != "meta"},
        run_id=args.run_id,
    )
    run_dir = run_ctx.run_dir

    if args.resume:
        if not any(run_dir.iterdir()):
            raise FileNotFoundError(f"Run directory is empty for resume: {run_dir}")
    else:
        if run_dir.exists() and any(run_dir.iterdir()):
            raise FileExistsError(
                f"Run directory already exists and is not empty: {run_dir}\n"
                "Use --resume or pass a different --run-id."
            )

    begin_run(
        run_ctx,
        config_path=str(Path(args.config).resolve()),
        inputs={"input_paths": cfg["data"]["input_paths"]},
    )

    logger = _setup_logging(run_dir, cfg)
    logger.info("Run directory: %s", run_dir)
    logger.info("Config hash: %s", cfg["meta"]["config_hash"])

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
        resume=args.resume,
    )

    init_state = initialize_training_state(piece_counts=piece_counts, cfg=cfg, logger=logger)

    train_state = train_bpe(
        cfg=cfg,
        run_dir=run_dir,
        initial_state=init_state,
        logger=logger,
        config_hash=cfg["meta"]["config_hash"],
        pattern_hash=pattern_hash,
        resume=args.resume,
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
    run_meta = json.loads(run_ctx.run_meta_path.read_text(encoding="utf-8"))
    manifest = build_artifact_manifest(
        artifact_type="tokenizer",
        artifact_id=artifact_id,
        source_run_id=run_ctx.run_id,
        config_hash=cfg["meta"]["config_hash"],
        git_commit=run_meta.get("git_commit"),
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
        },
        checksums=checksums,
    )
    publish_artifact(artifacts_root=artifacts_root, artifact_dir=export_dir, manifest=manifest)

    end_run(
        run_ctx,
        status="completed",
        summary={
            "artifact_id": artifact_id,
            "num_merges": len(train_state["merge_pairs"]),
            "training_corpus_sha256": stage1_meta["training_corpus_sha256"],
        },
    )
    logger.info("Tokenizer export complete: %s (artifact_id=%s)", export_dir, artifact_id)


if __name__ == "__main__":
    main()
