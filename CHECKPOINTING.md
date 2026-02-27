# Tokenizer Stage 03 Checkpointing

Tokenizer Stage 03 (`scripts/03_train_tokenizer.py`) now exposes checkpoint instrumentation for durability/performance measurement.

## Current behavior

1. Stage 3 can emit append-only merge WAL entries to `merges.wal`.
2. Stage 3 can emit periodic `snapshot_*.json` files.
3. WAL fsync policy is configurable (`periodic` or `per_commit`).
4. Checkpoint overhead is measured and saved in `run_statistics.json`:
   - WAL sync count and total sync seconds
   - snapshot count and total snapshot seconds

## Limits

1. `resume_mode` is accepted in config but Stage 03 currently still starts from a fresh run.
2. Snapshot files are lightweight progress snapshots intended for telemetry, not full state reconstruction.

## Relevant config fields

1. `checkpointing.enabled`
2. `checkpointing.snapshot_every_merges`
3. `checkpointing.wal_enabled`
4. `checkpointing.wal_fsync_every_commits`
5. `checkpointing.wal_fsync_mode`
6. `checkpointing.resume_mode`
