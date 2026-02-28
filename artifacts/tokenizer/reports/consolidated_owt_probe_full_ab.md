# OWT Tokenizer Consolidated Data Collection Report

- Generated (UTC): `2026-02-27T17:39:32Z`
- Probe run: `owt32k_probe_10gb_20260227_160946` / `tokenizer_owt32k_probe_10gb_20260227_160946`
- Full run: `owt32k_full_20260227_165243` / `tokenizer_owt32k_full_20260227_165243`

## Source Files
- Probe run statistics: `artifacts/tokenizer/runs/owt32k_probe_10gb_20260227_160946/run_statistics.json`
- Full run statistics: `artifacts/tokenizer/runs/owt32k_full_20260227_165243/run_statistics.json`
- Copied probe markdown report: `docs/data_collection_report_10GB_probe.md`
- Copied full markdown report: `docs/data_collection_report_full_run.md`
- A/B markdown report: `artifacts/tokenizer/reports/ab_compare_probe_vs_full.md`

## Environment + Config Snapshot
| Field | Probe | Full |
|---|---:|---:|
| OS | `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39` | `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39` |
| Platform Mode | `WSL` | `WSL` |
| CPU | `13th Gen Intel(R) Core(TM) i7-13700H` | `13th Gen Intel(R) Core(TM) i7-13700H` |
| RAM (GB) | `15.480` | `15.480` |
| Python | `3.12.3` | `3.12.3` |
| regex | `2026.2.19` | `2026.2.19` |
| min_piece_freq | `2` | `2` |
| max_unique_pieces | `2000000` | `2000000` |
| max_word_types | `1500000` | `1500000` |
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
| Probe 10GB | 10737418607 | 85203001 | 2231287958 | 2000000 | 2000000 | 2000000 | no | 2 | 2225453427 | 0.997385 | 466.324 | 375.371 | 1085.863 |
| Full | 11920511059 | 94568885 | 2476979902 | 2000000 | 2000000 | 2000000 | no | 2 | 2470329737 | 0.997315 | 466.168 | 379.840 | 1188.694 |

## Stage 2 Comparison
| Run | word_types_total | word_types_kept | hit_cap | cutoff_freq | avg_len | p95_len | max_len | RSS_end_mb | t_stage2_s |
|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|
| Probe 10GB | 2000000 | 1500000 | yes | 3 | 8.404 | 14 | 200 | 561.859 | 2.691 |
| Full | 2000000 | 1500000 | yes | 4 | 8.397 | 14 | 200 | 562.465 | 2.628 |

## Stage 3 Comparison
| Run | merges_done | t_stage3_s | median_ms/merge | p95_ms/merge | RSS_peak_mb | pair_count_initial | pair_count_late | typical_candidates/merge | candidates_pre_p95 | candidates_post_p95 | snapshots | snapshot_total_s | wal_sync_count | wal_sync_s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Probe 10GB | 31742 | 96.599 | 0.245 | 5.952 | 1574.246 | 13133 | 1041744 | 15.000 | 3213.000 | 1392.000 | 31 | 0.265 | 159 | 1.356 |
| Full | 31742 | 97.969 | 0.412 | 5.989 | 1729.500 | 13046 | 1041413 | 15.000 | 3137.000 | 1369.000 | 31 | 0.261 | 159 | 1.233 |

## A/B Stability (Probe=A vs Full=B)
- Run A: `owt32k_probe_10gb_20260227_160946`
- Run B: `owt32k_full_20260227_165243`
- Held-out path: `owt_valid.txt`
- Merge overlap@1k: `0.999000`
- Merge overlap@5k: `0.999400`
- Merge overlap@10k: `0.998900`
- tokens/char delta (B-A): `-0.000006619`
- tokens/word delta (B-A): `-0.000039849`

## Key Deltas (Full - Probe)
- Stage 1 bytes: `11920511059 - 10737418607 = 1183092452`
- Stage 1 lines: `94568885 - 85203001 = 9365884`
- Stage 1 coverage delta: `-0.000070`
- Stage 1 elapsed delta (s): `102.832`
- Stage 3 median ms/merge delta: `0.167110`
- Stage 3 RSS peak delta (MB): `155.254`

## Notes
- This file consolidates all telemetry from both completed runs plus the optional A/B comparison.
- For reproducible re-generation, re-run `scripts/09_compare_tokenizer_ab.py` with the same run/export paths and held-out text file.
