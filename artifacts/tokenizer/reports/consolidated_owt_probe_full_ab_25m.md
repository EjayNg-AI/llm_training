# OWT Tokenizer Consolidated Data Collection Report (2.5M Caps)

- Generated (UTC): `2026-03-01T04:50:02Z`
- Probe run: `owt32k_probe_10gb_25m_20260301_041747` / `tokenizer_owt32k_probe_10gb_25m_20260301_041747`
- Full run: `owt32k_full_25m_20260301_030751` / `tokenizer_owt32k_full_25m_20260301_030751`

## Source Files
- Probe run statistics: `artifacts/tokenizer/runs/owt32k_probe_10gb_25m_20260301_041747/run_statistics.json`
- Full run statistics: `artifacts/tokenizer/runs/owt32k_full_25m_20260301_030751/run_statistics.json`
- A/B markdown report: `artifacts/tokenizer/reports/ab_compare_probe_vs_full_25m.md`

## Environment + Config Snapshot
| Field | Probe | Full |
|---|---:|---:|
| OS | `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39` | `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39` |
| Platform Mode | `WSL` | `WSL` |
| CPU | `Intel(R) Core(TM) Ultra 7 155U` | `Intel(R) Core(TM) Ultra 7 155U` |
| RAM (GB) | `15.354` | `15.354` |
| Python | `3.12.3` | `3.12.3` |
| regex | `2026.2.19` | `2026.2.19` |
| min_piece_freq | `2` | `2` |
| max_unique_pieces | `2500000` | `2500000` |
| max_word_types | `2500000` | `2500000` |
| max_piece_bytes | `200` | `200` |
| vocab_size | `32000` | `32000` |
| min_merge_freq | `2` | `2` |
| max_merges | `None` | `None` |
| num_workers | `4` | `4` |
| batch_lines | `2000` | `2000` |
| snapshot_every_merges | `1000` | `1000` |
| wal_fsync_mode | `periodic` | `periodic` |
| wal_fsync_every_commits | `200` | `200` |

## Stage 1 Comparison
| Run | total_bytes | total_lines | total_pieces_seen | unique_before | unique_after_min_freq | unique_kept | hit_cap | cutoff_freq | kept_mass | coverage | RSS_peak_mb | RSS_end_mb | t_stage1_s |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|---:|
| Probe 10GB (2.5M) | 10737418607 | 85203001 | 2231287958 | 2500000 | 2405344 | 2405344 | no | 2 | 2226615630 | 0.997906 | 511.258 | 421.285 | 1640.394 |
| Full (2.5M) | 11920511059 | 94568885 | 2476979902 | 2500000 | 2500000 | 2500000 | no | 2 | 2471754186 | 0.997890 | 492.211 | 419.410 | 1794.892 |

## Stage 2 Comparison
| Run | word_types_total | word_types_kept | hit_cap | cutoff_freq | avg_len | p95_len | max_len | RSS_end_mb | t_stage2_s |
|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|
| Probe 10GB (2.5M) | 2405344 | 2405344 | no | 2 | 8.817 | 15 | 200 | 723.758 | 5.488 |
| Full (2.5M) | 2500000 | 2500000 | no | 2 | 8.791 | 15 | 200 | 741.566 | 5.522 |

## Stage 3 Comparison
| Run | merges_done | t_stage3_s | median_ms/merge | p95_ms/merge | RSS_peak_mb | pair_count_initial | pair_count_late | typical_candidates/merge | candidates_pre_p95 | candidates_post_p95 | snapshots | snapshot_total_s | wal_sync_count | wal_sync_s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Probe 10GB (2.5M) | 31742 | 210.125 | 0.702 | 12.125 | 2490.289 | 16015 | 1524591 | 24.000 | 5818.000 | 2315.000 | 31 | 0.070 | 159 | 0.489 |
| Full (2.5M) | 31742 | 208.779 | 0.673 | 12.041 | 2587.465 | 15789 | 1574627 | 25.000 | 6099.000 | 2427.000 | 31 | 0.070 | 159 | 0.528 |

## A/B Stability (Probe=A vs Full=B)
- Run A: `owt32k_probe_10gb_25m_20260301_041747`
- Run B: `owt32k_full_25m_20260301_030751`
- Held-out path: `openwebtext_sample_3k_4k_tokens.txt`
- Merge overlap@1k: `0.999000`
- Merge overlap@5k: `0.998800`
- Merge overlap@10k: `0.998000`
- tokens/char delta (B-A): `-0.000057498`
- tokens/word delta (B-A): `-0.000348554`

## Key Deltas (Full - Probe)
- Stage 1 bytes: `11920511059 - 10737418607 = 1183092452`
- Stage 1 lines: `94568885 - 85203001 = 9365884`
- Stage 1 coverage delta: `-0.000016`
- Stage 1 elapsed delta (s): `154.498`
- Stage 3 median ms/merge delta: `-0.028099`
- Stage 3 RSS peak delta (MB): `97.176`

## Notes
- This file consolidates telemetry from the completed 2.5M-cap probe and full runs plus A/B metrics.
- For reproducible regeneration: run `scripts/09_compare_tokenizer_ab.py` for A/B and then rebuild this consolidated markdown from both run-statistics files.
