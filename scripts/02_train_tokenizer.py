"""Train and export a GPT-2 style byte-level BPE tokenizer."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

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

    if bool(cfg["run"].get("structured_logs", False)):
        json_handler = logging.FileHandler(run_dir / "train.jsonl", encoding="utf-8")
        json_handler.setFormatter(JsonlFormatter())
        logger.addHandler(json_handler)

    return logger


def _resolve_run_dir(cfg: dict[str, Any], run_id: str | None) -> Path:
    base = Path(cfg["run"]["output_dir"])
    resolved_run_id = run_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return base / resolved_run_id


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
        help="Optional absolute merge index at which to stop early (debug/recovery testing).",
    )
    parser.add_argument(
        "--export-dir",
        default="artifacts/tokenizer/gpt2",
        help="Directory where final tokenizer artifacts are exported.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    run_dir = _resolve_run_dir(cfg, args.run_id)

    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(
            f"Run directory already exists and is not empty: {run_dir}\n"
            "Pass a different --run-id."
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
    )

    init_state, _ = initialize_training_state(piece_counts=piece_counts, cfg=cfg, logger=logger)

    train_state = train_bpe(
        cfg=cfg,
        run_dir=run_dir,
        initial_state=init_state,
        logger=logger,
        config_hash=cfg["meta"]["config_hash"],
        pattern_hash=pattern_hash,
        stop_after_merges=args.stop_after_merges,
    )

    export_dir = Path(args.export_dir)
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
    logger.info("Tokenizer export complete: %s", export_dir)


if __name__ == "__main__":
    main()
