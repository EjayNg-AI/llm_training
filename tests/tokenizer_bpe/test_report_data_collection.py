from __future__ import annotations

from pathlib import Path

from tokenizer_bpe.report_data_collection import render_data_collection_report, write_data_collection_report


def _sample_stats() -> dict:
    return {
        "run_id": "run_a",
        "artifact_id": "tok_a",
        "config_hash": "c" * 64,
        "pattern_hash": "p" * 64,
        "environment": {
            "os": "Linux",
            "platform_mode": "Linux native",
            "cpu_model": "cpu",
            "ram_total_gb": 16.0,
            "python_version": "3.12.0",
            "regex_version": "2025.1.1",
        },
        "scale_config": {
            "min_piece_freq": 2,
            "max_unique_pieces": 2000000,
            "max_word_types": 1500000,
            "max_piece_bytes": 200,
            "vocab_size": 50000,
            "min_merge_freq": 2,
            "max_merges": None,
            "num_workers": 4,
            "batch_lines": 2000,
            "snapshot_every_merges": 1000,
            "wal_fsync_mode": "periodic",
            "wal_fsync_every_commits": 200,
        },
        "stage1": {
            "total_bytes_processed": 1000,
            "total_pieces_seen": 500,
            "max_unique_seen": 100,
            "unique_before_prune": 100,
            "unique_kept": 90,
            "hit_max_unique_pieces": False,
            "max_unique_pieces_cap_events": 0,
            "evicted_keys_total": 0,
            "evicted_mass_total": 0,
            "evicted_mass_ratio": 0.0,
            "cutoff_freq_at_unique_cap": 1,
            "coverage": 0.99,
            "rss_peak_mb": 123.4,
            "stage1_elapsed_seconds": 2.0,
            "total_lines_processed": 10,
            "kept_mass": 495,
        },
        "stage2": {
            "word_types_total": 90,
            "word_types_kept": 80,
            "hit_max_word_types": False,
            "cutoff_freq_at_word_types_cap": 1,
            "avg_symbols_per_word_type": 4.2,
            "p95_symbols_per_word_type": 8,
            "max_symbols_per_word_type": 12,
            "rss_end_mb": 120.0,
            "stage2_elapsed_seconds": 0.5,
        },
        "stage3": {
            "merges_done": 50,
            "elapsed_seconds": 4.0,
            "median_ms_per_merge": 7.1,
            "p95_ms_per_merge": 8.3,
            "rss_peak_mb": 222.0,
            "pair_count_len_initial": 1000,
            "pair_count_len_late": 200,
            "candidates_per_merge_post_dedup_median": 12.0,
            "best_count_initial": 999,
            "best_count_late": 8,
            "checkpointing": {
                "enabled": True,
                "snapshot_every_merges": 1000,
                "wal_fsync_mode": "periodic",
                "wal_fsync_every_commits": 200,
                "snapshot_count": 1,
                "snapshot_total_seconds": 0.2,
                "wal_sync_count": 2,
                "wal_sync_seconds": 0.3,
            },
        },
    }


def test_render_data_collection_report_contains_required_sections():
    report = render_data_collection_report(_sample_stats())
    assert "# Tokenizer Data Collection Report" in report
    assert "## Environment + Config Snapshot" in report
    assert "## Compact Summary" in report
    assert "### Stage 1" in report
    assert "### Stage 2" in report
    assert "### Stage 3" in report
    assert "## A/B Stability" in report
    assert "max_unique_seen" in report
    assert "evicted_keys_total" in report
    assert "evicted_mass_total" in report
    assert "evicted_mass_ratio" in report


def test_write_data_collection_report_creates_file(tmp_path: Path):
    out = tmp_path / "docs" / "data_collection_report.md"
    write_data_collection_report(_sample_stats(), out)
    assert out.exists()
    assert "Tokenizer Data Collection Report" in out.read_text(encoding="utf-8")
