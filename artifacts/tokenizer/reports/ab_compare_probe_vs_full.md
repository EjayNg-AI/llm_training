# Tokenizer Data Collection Report

- Generated (UTC): `2026-02-27T17:38:34Z`
- Run ID: `owt32k_full_20260227_165243`
- Artifact ID: `tokenizer_owt32k_full_20260227_165243`
- Config Hash: `aa91ce55c0b6c0cc4b27def6ad8d87b8b2d557f53d1a2b029ee10bf8ed9d7ff5`
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
| 11920511059 | 2476979902 | 2000000 | 2000000 | no | 2 | 0.997315 | 466.168 | 1188.694 |

### Stage 2

| word_types_total | word_types_kept | hit_cap | cutoff_freq | avg_len | p95_len | max_len | RSS_end_mb |
|---:|---:|:---:|---:|---:|---:|---:|---:|
| 2000000 | 1500000 | yes | 4 | 8.397 | 14 | 200 | 562.465 |

### Stage 3

| merges_done | t_stage3_s | median_ms/merge | RSS_peak_mb | pair_count_initial | pair_count_late | typical_candidates/merge |
|---:|---:|---:|---:|---:|---:|---:|
| 31742 | 97.969 | 0.412 | 1729.500 | 13046 | 1041413 | 15.000 |

## Additional Data Points
- Stage 1 lines processed: `94568885`
- Stage 1 bytes/sec: `10028237.815`
- Stage 1 estimated time for 100GB (s): `10707.183`
- Stage 1 kept_mass: `2470329737`
- Stage 2 elapsed (s): `2.628`
- Stage 3 p95 ms/merge: `5.989`
- Stage 3 best_count initial/late: `258491340` / `6231`
- Snapshot count/total seconds: `31` / `0.261`
- WAL sync count/seconds: `159` / `1.233`

## A/B Stability
- Run A: `owt32k_probe_10gb_20260227_160946`
- Run B: `owt32k_full_20260227_165243`
- Held-out path: `owt_valid.txt`
- Merge overlap@1k: `0.999`
- Merge overlap@5k: `0.999`
- Merge overlap@10k: `0.999`
- tokens/char delta (B-A): `-0.000`
- tokens/word delta (B-A): `-0.000`

