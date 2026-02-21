# Tokenizer Checkpointing and Recovery

This trainer is designed to survive interrupts and power loss with deterministic recovery.

## Stage 1 checkpoints

Files:

- `runs/<run_id>/checkpoints/word_counts.snapshot.pkl`
- `runs/<run_id>/checkpoints/word_counts.progress.json`

`word_counts.progress.json` tracks:

- per-file byte offsets and completion flags
- total processed lines, pieces, and bytes
- `config_hash` and `pattern_hash`

Stage 1 writes are atomic:

1. write temp file
2. flush and fsync
3. replace target path

## Stage 3 durability model

Files:

- `runs/<run_id>/merges.wal`
- `runs/<run_id>/snapshots/state.mXXXXXXXX.pkl`
- `runs/<run_id>/snapshots/state.mXXXXXXXX.pkl.sha256`

WAL records:

- `BEGIN<TAB>merge_idx<TAB>a<TAB>b<TAB>count`
- `COMMIT<TAB>merge_idx<TAB>new_id`

Rule:

- only merges with `COMMIT` are considered durable
- `BEGIN` without matching `COMMIT` is ignored on recovery

## Snapshot validity checks

A snapshot is accepted only when:

1. pickle file can be loaded
2. checksum sidecar matches file content
3. `config_hash` matches current config
4. `pattern_hash` matches current pretokenizer contract

## Resume procedure

1. Load latest valid snapshot.
2. Parse WAL and collect committed merges.
3. Replay committed merges beyond snapshot index.
4. Rebuild pair stats/heap from recovered words.
5. Continue merge training.

If config or regex contract changes, resume fails fast by design.

