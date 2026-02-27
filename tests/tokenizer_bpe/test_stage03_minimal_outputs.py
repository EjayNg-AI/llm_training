from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]


def _load_stage03_module():
    script_path = ROOT / "scripts" / "03_train_tokenizer.py"
    spec = importlib.util.spec_from_file_location("stage03_train_tokenizer_script", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load stage03 script module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.integration
def test_stage03_writes_telemetry_statistics_and_report_outputs(tmp_path, tiny_corpus_text):
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text(tiny_corpus_text, encoding="utf-8")

    runs_dir = tmp_path / "runs"
    artifacts_root = tmp_path / "artifacts"
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg = {
        "run": {
            "output_dir": str(runs_dir),
            "seed": 0,
            "log_level": "INFO",
            "report_output_path": str(tmp_path / "docs" / "data_collection_report.md"),
            "stage3_metrics_every_merges": 2,
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
            "vocab_size": 262,
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
        "checkpointing": {
            "enabled": True,
            "snapshot_every_merges": 2,
            "wal_enabled": True,
            "wal_fsync_every_commits": 2,
            "wal_fsync_mode": "periodic",
            "resume_mode": "off",
        },
    }
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    stage03_module = _load_stage03_module()
    import tokenizer_bpe.stage1_count as stage1_count_module

    original_executor = stage1_count_module.ProcessPoolExecutor
    original_argv = sys.argv
    stage1_count_module.ProcessPoolExecutor = ThreadPoolExecutor
    try:
        sys.argv = [
            "03_train_tokenizer.py",
            "--config",
            str(cfg_path),
            "--run-id",
            "run_a",
            "--artifact-id",
            "tok_a",
            "--artifacts-root",
            str(artifacts_root),
        ]
        stage03_module.main()
    finally:
        sys.argv = original_argv
        stage1_count_module.ProcessPoolExecutor = original_executor

    run_dir = runs_dir / "run_a"
    run_files = sorted(path.name for path in run_dir.iterdir())
    assert "training_telemetry.json" in run_files
    assert "run_statistics.json" in run_files
    assert "merges.wal" in run_files
    assert any(name.startswith("snapshot_") for name in run_files)

    telemetry = json.loads((run_dir / "training_telemetry.json").read_text(encoding="utf-8"))
    assert {"training_started_at", "training_ended_at", "elapsed_seconds"} <= set(telemetry.keys())
    assert "run_statistics_path" in telemetry
    assert "report_path" in telemetry
    assert telemetry["elapsed_seconds"] >= 0

    run_stats = json.loads((run_dir / "run_statistics.json").read_text(encoding="utf-8"))
    assert "environment" in run_stats
    assert "stage1" in run_stats
    assert "stage2" in run_stats
    assert "stage3" in run_stats
    assert run_stats["stage1"]["total_pieces_seen"] >= 0
    assert run_stats["stage2"]["word_types_kept"] >= 0
    assert run_stats["stage3"]["merges_done"] >= 0

    report_path = Path(telemetry["report_path"])
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "# Tokenizer Data Collection Report" in report_text
    assert "## Compact Summary" in report_text

    export_dir = artifacts_root / "tokenizer" / "exports" / "tok_a"
    assert (export_dir / "vocab.json").exists()
    assert (export_dir / "merges.txt").exists()
    assert (export_dir / "tokenizer_config.json").exists()
    assert (export_dir / "special_tokens_map.json").exists()
    assert (export_dir / "training_stats.json").exists()
    assert (export_dir / "artifact_manifest.json").exists()
