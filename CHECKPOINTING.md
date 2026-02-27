# Checkpointing Note

Tokenizer Stage 03 (`scripts/03_train_tokenizer.py`) no longer implements checkpoint/recovery mechanics.

Current behavior:

1. no Stage 1 checkpoint snapshots
2. no Stage 3 WAL
3. no Stage 3 state snapshots
4. no resume mode

Stage 03 is a fresh-run workflow that emits:

1. final tokenizer export artifacts under `artifacts/tokenizer/exports/<artifact_id>/`
2. duration telemetry under `run.output_dir/<run_id>/training_telemetry.json`

Other pipeline stages may still implement their own checkpointing semantics.
