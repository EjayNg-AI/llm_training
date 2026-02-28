# Tokenizer Data Collection Report for 10GB Probe Run

- Generated (UTC): `2026-02-27T16:29:27Z`
- Run ID: `owt32k_probe_10gb_20260227_160946`
- Artifact ID: `tokenizer_owt32k_probe_10gb_20260227_160946`
- Config Hash: `0606907a323750aa1218c4e6e9e41d4532d20b0822a6b89eb7dc9c23b291d86d`
- Pattern Hash: `0a10b5fe5e3bbecbc850fda5259aeb5dc3da062c22f6b526252f12ef00ee3667`

## Environment + Config Snapshot
- OS: `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`
- Platform Mode: `WSL`
- CPU: `13th Gen Intel(R) Core(TM) i7-13700H`
- RAM (GB): `15.480`
- Python: `3.12.3`
- regex: `2026.2.19`
- min_piece_freq: `2`
- max_unique_pieces: `2000000`
- max_word_types: `1500000`
- max_piece_bytes: `200`
- vocab_size: `32000`
- min_merge_freq: `2`
- max_merges: `None`
- num_workers: `4`
- batch_lines: `2000`
- checkpointing.enabled: `True`
- checkpointing.snapshot_every_merges: `1000`
- checkpointing.wal_fsync_mode: `periodic`
- checkpointing.wal_fsync_every_commits: `200`

## Compact Summary

### Stage 1

| total_bytes | total_pieces_seen | unique_before | unique_kept | hit_cap | cutoff_freq | coverage | RSS_peak_mb | t_stage1_s |
|---:|---:|---:|---:|:---:|---:|---:|---:|---:|
| 10737418607 | 2231287958 | 2000000 | 2000000 | no | 2 | 0.997385 | 466.324 | 1085.863 |

### Stage 2

| word_types_total | word_types_kept | hit_cap | cutoff_freq | avg_len | p95_len | max_len | RSS_end_mb |
|---:|---:|:---:|---:|---:|---:|---:|---:|
| 2000000 | 1500000 | yes | 3 | 8.404 | 14 | 200 | 561.859 |

### Stage 3

| merges_done | t_stage3_s | median_ms/merge | RSS_peak_mb | pair_count_initial | pair_count_late | typical_candidates/merge |
|---:|---:|---:|---:|---:|---:|---:|
| 31742 | 96.599 | 0.245 | 1574.246 | 13133 | 1041744 | 15.000 |

## Additional Data Points
- Stage 1 lines processed: `85203001`
- Stage 1 bytes/sec: `9888377.430`
- Stage 1 estimated time for 100GB (s): `10858.625`
- Stage 1 kept_mass: `2225453427`
- Stage 2 elapsed (s): `2.691`
- Stage 3 p95 ms/merge: `5.952`
- Stage 3 best_count initial/late: `232814105` / `5614`
- Snapshot count/total seconds: `31` / `0.265`
- WAL sync count/seconds: `159` / `1.356`

## A/B Stability
- A/B comparison is not attached to this run yet.
- Use the A/B utility to append stability metrics into `run_statistics.json`.

