"""Generate markdown summaries for tokenizer scaling data collection runs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _fmt_float(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_int(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "n/a"


def _fmt_bool(value: Any) -> str:
    return "yes" if bool(value) else "no"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _estimate_stage1_for_100gb(stage1: dict[str, Any]) -> dict[str, float]:
    total_bytes = float(stage1.get("total_bytes_processed", 0) or 0)
    elapsed = float(stage1.get("stage1_elapsed_seconds", 0) or 0)
    if total_bytes <= 0 or elapsed <= 0:
        return {"bytes_per_second": 0.0, "estimated_seconds": 0.0}
    target_bytes = 100.0 * (1024.0**3)
    bytes_per_second = total_bytes / elapsed
    return {"bytes_per_second": bytes_per_second, "estimated_seconds": target_bytes / bytes_per_second}


def render_data_collection_report(run_stats: dict[str, Any]) -> str:
    env = run_stats.get("environment", {})
    cfg = run_stats.get("scale_config", {})
    stage1 = run_stats.get("stage1", {})
    stage2 = run_stats.get("stage2", {})
    stage3 = run_stats.get("stage3", {})
    checkpointing = stage3.get("checkpointing", {})
    projection = _estimate_stage1_for_100gb(stage1)
    ab = run_stats.get("ab_stability")

    lines: list[str] = []
    lines.append("# Tokenizer Data Collection Report")
    lines.append("")
    lines.append(f"- Generated (UTC): `{_utc_now_iso()}`")
    lines.append(f"- Run ID: `{run_stats.get('run_id', 'n/a')}`")
    lines.append(f"- Artifact ID: `{run_stats.get('artifact_id', 'n/a')}`")
    lines.append(f"- Config Hash: `{run_stats.get('config_hash', 'n/a')}`")
    lines.append(f"- Pattern Hash: `{run_stats.get('pattern_hash', 'n/a')}`")
    lines.append("")
    lines.append("## Environment + Config Snapshot")
    lines.append(f"- OS: `{env.get('os', 'n/a')}`")
    lines.append(f"- Platform Mode: `{env.get('platform_mode', 'n/a')}`")
    lines.append(f"- CPU: `{env.get('cpu_model', 'n/a')}`")
    lines.append(f"- RAM (GB): `{_fmt_float(env.get('ram_total_gb'))}`")
    lines.append(f"- Python: `{env.get('python_version', 'n/a')}`")
    lines.append(f"- regex: `{env.get('regex_version', 'n/a')}`")
    lines.append(f"- min_piece_freq: `{cfg.get('min_piece_freq', 'n/a')}`")
    lines.append(f"- max_unique_pieces: `{cfg.get('max_unique_pieces', 'n/a')}`")
    lines.append(f"- max_word_types: `{cfg.get('max_word_types', 'n/a')}`")
    lines.append(f"- max_piece_bytes: `{cfg.get('max_piece_bytes', 'n/a')}`")
    lines.append(f"- vocab_size: `{cfg.get('vocab_size', 'n/a')}`")
    lines.append(f"- min_merge_freq: `{cfg.get('min_merge_freq', 'n/a')}`")
    lines.append(f"- max_merges: `{cfg.get('max_merges', 'n/a')}`")
    lines.append(f"- num_workers: `{cfg.get('num_workers', 'n/a')}`")
    lines.append(f"- batch_lines: `{cfg.get('batch_lines', 'n/a')}`")
    lines.append(f"- checkpointing.enabled: `{checkpointing.get('enabled', 'n/a')}`")
    lines.append(f"- checkpointing.snapshot_every_merges: `{checkpointing.get('snapshot_every_merges', 'n/a')}`")
    lines.append(f"- checkpointing.wal_fsync_mode: `{checkpointing.get('wal_fsync_mode', 'n/a')}`")
    lines.append(f"- checkpointing.wal_fsync_every_commits: `{checkpointing.get('wal_fsync_every_commits', 'n/a')}`")
    lines.append("")
    lines.append("## Compact Summary")
    lines.append("")
    lines.append("### Stage 1")
    lines.append("")
    lines.append(
        "| total_bytes | total_pieces_seen | unique_before_cap_window | max_unique_seen | unique_kept | hit_cap | "
        "cap_events | evicted_keys_total | evicted_mass_total | evicted_mass_ratio | cutoff_freq | coverage | "
        "RSS_peak_mb | t_stage1_s |"
    )
    lines.append("|---:|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        "| "
        + " | ".join(
            [
                _fmt_int(stage1.get("total_bytes_processed")),
                _fmt_int(stage1.get("total_pieces_seen")),
                _fmt_int(stage1.get("unique_before_prune")),
                _fmt_int(stage1.get("max_unique_seen")),
                _fmt_int(stage1.get("unique_kept")),
                _fmt_bool(stage1.get("hit_max_unique_pieces")),
                _fmt_int(stage1.get("max_unique_pieces_cap_events")),
                _fmt_int(stage1.get("evicted_keys_total")),
                _fmt_int(stage1.get("evicted_mass_total")),
                _fmt_float(stage1.get("evicted_mass_ratio"), 6),
                _fmt_int(stage1.get("cutoff_freq_at_unique_cap")),
                _fmt_float(stage1.get("coverage"), 6),
                _fmt_float(stage1.get("rss_peak_mb")),
                _fmt_float(stage1.get("stage1_elapsed_seconds")),
            ]
        )
        + " |"
    )
    lines.append("")
    lines.append("### Stage 2")
    lines.append("")
    lines.append("| word_types_total | word_types_kept | hit_cap | cutoff_freq | avg_len | p95_len | max_len | RSS_end_mb |")
    lines.append("|---:|---:|:---:|---:|---:|---:|---:|---:|")
    lines.append(
        "| "
        + " | ".join(
            [
                _fmt_int(stage2.get("word_types_total")),
                _fmt_int(stage2.get("word_types_kept")),
                _fmt_bool(stage2.get("hit_max_word_types")),
                _fmt_int(stage2.get("cutoff_freq_at_word_types_cap")),
                _fmt_float(stage2.get("avg_symbols_per_word_type")),
                _fmt_int(stage2.get("p95_symbols_per_word_type")),
                _fmt_int(stage2.get("max_symbols_per_word_type")),
                _fmt_float(stage2.get("rss_end_mb")),
            ]
        )
        + " |"
    )
    lines.append("")
    lines.append("### Stage 3")
    lines.append("")
    lines.append("| merges_done | t_stage3_s | median_ms/merge | RSS_peak_mb | pair_count_initial | pair_count_late | typical_candidates/merge |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        "| "
        + " | ".join(
            [
                _fmt_int(stage3.get("merges_done")),
                _fmt_float(stage3.get("elapsed_seconds")),
                _fmt_float(stage3.get("median_ms_per_merge")),
                _fmt_float(stage3.get("rss_peak_mb")),
                _fmt_int(stage3.get("pair_count_len_initial")),
                _fmt_int(stage3.get("pair_count_len_late")),
                _fmt_float(stage3.get("candidates_per_merge_post_dedup_median")),
            ]
        )
        + " |"
    )
    lines.append("")
    lines.append("## Additional Data Points")
    lines.append(f"- Stage 1 lines processed: `{_fmt_int(stage1.get('total_lines_processed'))}`")
    lines.append(f"- Stage 1 bytes/sec: `{_fmt_float(projection.get('bytes_per_second'))}`")
    lines.append(f"- Stage 1 estimated time for 100GB (s): `{_fmt_float(projection.get('estimated_seconds'))}`")
    lines.append(f"- Stage 1 kept_mass: `{_fmt_int(stage1.get('kept_mass'))}`")
    lines.append("- Stage 1 `unique_before_cap_window` is the max pre-cap unique inventory observed in-stream.")
    lines.append(
        "- Stage 1 eviction totals are cumulative across cap events; a piece type can be evicted more than once "
        "if it reappears later."
    )
    lines.append(f"- Stage 2 elapsed (s): `{_fmt_float(stage2.get('stage2_elapsed_seconds'))}`")
    lines.append(f"- Stage 3 p95 ms/merge: `{_fmt_float(stage3.get('p95_ms_per_merge'))}`")
    lines.append(f"- Stage 3 best_count initial/late: `{_fmt_int(stage3.get('best_count_initial'))}` / `{_fmt_int(stage3.get('best_count_late'))}`")
    lines.append(f"- Snapshot count/total seconds: `{_fmt_int(checkpointing.get('snapshot_count'))}` / `{_fmt_float(checkpointing.get('snapshot_total_seconds'))}`")
    lines.append(f"- WAL sync count/seconds: `{_fmt_int(checkpointing.get('wal_sync_count'))}` / `{_fmt_float(checkpointing.get('wal_sync_seconds'))}`")
    lines.append("")
    lines.append("## A/B Stability")
    if isinstance(ab, dict):
        lines.append(f"- Run A: `{ab.get('run_a', 'n/a')}`")
        lines.append(f"- Run B: `{ab.get('run_b', 'n/a')}`")
        lines.append(f"- Held-out path: `{ab.get('heldout_path', 'n/a')}`")
        lines.append(f"- Merge overlap@1k: `{_fmt_float(ab.get('merge_overlap_top_1000'))}`")
        lines.append(f"- Merge overlap@5k: `{_fmt_float(ab.get('merge_overlap_top_5000'))}`")
        lines.append(f"- Merge overlap@10k: `{_fmt_float(ab.get('merge_overlap_top_10000'))}`")
        lines.append(f"- tokens/char delta (B-A): `{_fmt_float(ab.get('tokens_per_char_delta'))}`")
        lines.append(f"- tokens/word delta (B-A): `{_fmt_float(ab.get('tokens_per_word_delta'))}`")
    else:
        lines.append("- A/B comparison is not attached to this run yet.")
        lines.append("- Use the A/B utility to append stability metrics into `run_statistics.json`.")
    lines.append("")
    return "\n".join(lines)


def write_data_collection_report(run_stats: dict[str, Any], output_path: Path) -> Path:
    report_text = render_data_collection_report(run_stats)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text + "\n", encoding="utf-8")
    return output_path
