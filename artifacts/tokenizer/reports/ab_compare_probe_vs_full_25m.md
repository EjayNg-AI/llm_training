# Tokenizer Data Collection Report

- Generated (UTC): `2026-03-01T07:01:50Z`
- Run ID: `owt32k_full_25m_20260301_061344`
- Artifact ID: `tokenizer_owt32k_full_25m_20260301_061344`
- Config Hash: `b880477faf4ad0964502951aaab6fd87626f5ce63ab73ff0cec6aa0b68f184dc`
- Pattern Hash: `0a10b5fe5e3bbecbc850fda5259aeb5dc3da062c22f6b526252f12ef00ee3667`

## Environment + Config Snapshot
- OS: `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`
- Platform Mode: `WSL`
- CPU: `Intel(R) Core(TM) Ultra 7 155U`
- RAM (GB): `15.354`
- Python: `3.12.3`
- regex: `2026.2.19`
- min_piece_freq: `2`
- max_unique_pieces: `2500000`
- max_word_types: `2500000`
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

| total_bytes | total_pieces_seen | unique_before_cap_window | unique_kept | hit_cap | cap_events | cutoff_freq | coverage | RSS_peak_mb | t_stage1_s |
|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|
| 11920511059 | 2476979902 | 2524976 | 2500000 | yes | 368 | 2 | 0.997890 | 518.000 | 1766.177 |

### Stage 2

| word_types_total | word_types_kept | hit_cap | cutoff_freq | avg_len | p95_len | max_len | RSS_end_mb |
|---:|---:|:---:|---:|---:|---:|---:|---:|
| 2500000 | 2500000 | no | 2 | 8.791 | 15 | 200 | 744.746 |

### Stage 3

| merges_done | t_stage3_s | median_ms/merge | RSS_peak_mb | pair_count_initial | pair_count_late | typical_candidates/merge |
|---:|---:|---:|---:|---:|---:|---:|
| 31742 | 205.108 | 0.676 | 2623.695 | 15789 | 1574627 | 25.000 |

## Additional Data Points
- Stage 1 lines processed: `94568885`
- Stage 1 bytes/sec: `6749329.123`
- Stage 1 estimated time for 100GB (s): `15908.867`
- Stage 1 kept_mass: `2471754186`
- Stage 1 `unique_before_cap_window` is the max pre-cap unique inventory observed in-stream.
- Stage 2 elapsed (s): `5.424`
- Stage 3 p95 ms/merge: `11.897`
- Stage 3 best_count initial/late: `258521322` / `6288`
- Snapshot count/total seconds: `31` / `0.067`
- WAL sync count/seconds: `159` / `0.462`

## A/B Stability
- Run A: `owt32k_probe_1gb_25m_20260301_060954`
- Run B: `owt32k_full_25m_20260301_061344`
- Held-out path: `openwebtext_sample_3k_4k_tokens.txt`
- Merge overlap@1k: `0.998`
- Merge overlap@5k: `0.986`
- Merge overlap@10k: `0.977`
- tokens/char delta (B-A): `-0.000`
- tokens/word delta (B-A): `-0.002`

