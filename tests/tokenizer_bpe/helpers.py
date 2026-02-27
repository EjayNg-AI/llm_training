from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]


def write_test_config(
    cfg_path: Path,
    *,
    corpus_path: Path,
    output_dir: Path,
    vocab_size: int = 262,
) -> dict[str, Any]:
    cfg = {
        "run": {
            "output_dir": str(output_dir),
            "seed": 0,
            "log_level": "INFO",
        },
        "data": {
            "input_paths": [str(corpus_path)],
            "input_format": "text",
            "jsonl_text_field": "text",
            "decode_errors": "replace",
            "normalize": "none",
            "max_bytes": None,
            "max_lines": None,
            "num_workers": 1,
            "batch_lines": 2,
            "min_piece_freq": 1,
            "max_unique_pieces": 100000,
        },
        "pretokenizer": {
            "pattern": "gpt2_fast",
            "custom_pattern": None,
            "flags": [],
        },
        "bpe": {
            "vocab_size": vocab_size,
            "min_merge_freq": 2,
            "max_merges": None,
            "max_word_types": 100000,
            "max_piece_bytes": 200,
            "tie_break": "lexicographic",
        },
        "special_tokens": {
            "tokens": ["<|endoftext|>", "<|pad|>"],
            "placement": "end",
        },
    }
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return cfg


def run_train(
    *,
    cfg_path: Path,
    run_id: str,
    export_dir: Path,
    stop_after_merges: int | None = None,
) -> None:
    # Integration tests run the full pipeline in-process because the sandbox
    # can disallow multiprocessing semaphores used by ProcessPoolExecutor.
    from concurrent.futures import ThreadPoolExecutor

    from tokenizer_bpe.config import build_pattern_hash, load_config
    from tokenizer_bpe.export import export_tokenizer
    from tokenizer_bpe.pretokenizer import resolve_pattern
    from tokenizer_bpe.stage1_count import count_pieces
    import tokenizer_bpe.stage1_count as stage1_count_module
    from tokenizer_bpe.stage2_init import initialize_training_state
    from tokenizer_bpe.stage3_train import train_bpe

    cfg = load_config(cfg_path)
    run_dir = Path(cfg["run"]["output_dir"]) / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"Run directory already exists and is not empty: {run_dir}")

    logger = logging.getLogger(f"tests.tokenizer_bpe.integration.{run_id}")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False

    pattern_alias, pattern_str, pattern_flags, regex_version = resolve_pattern(cfg["pretokenizer"])
    pattern_hash = build_pattern_hash(
        pattern_str=pattern_str,
        pattern_flags=pattern_flags,
        normalize=cfg["data"]["normalize"],
        regex_version=regex_version,
    )

    original_executor = stage1_count_module.ProcessPoolExecutor
    stage1_count_module.ProcessPoolExecutor = ThreadPoolExecutor
    try:
        piece_counts, stage1_meta = count_pieces(
            cfg=cfg,
            run_dir=run_dir,
            pattern_str=pattern_str,
            pattern_flags=pattern_flags,
            pattern_hash=pattern_hash,
            logger=logger,
        )
    finally:
        stage1_count_module.ProcessPoolExecutor = original_executor

    init_state, _ = initialize_training_state(piece_counts=piece_counts, cfg=cfg, logger=logger)
    train_state = train_bpe(
        cfg=cfg,
        run_dir=run_dir,
        initial_state=init_state,
        logger=logger,
        config_hash=cfg["meta"]["config_hash"],
        pattern_hash=pattern_hash,
        stop_after_merges=stop_after_merges,
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized_training_stats(path: Path) -> dict[str, Any]:
    stats = load_json(path)
    stats.pop("run_dir", None)
    return stats
