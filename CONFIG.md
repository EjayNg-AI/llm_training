# Tokenizer Config Reference

The tokenizer trainer uses:

1. `configs/tokenizer_bpe.yaml`
2. `configs/tokenizer_bpe_owt_32k.yaml`
3. defaults in `scripts/tokenizer_bpe/config.py`

## Top-level sections

1. `run`
2. `data`
3. `pretokenizer`
4. `bpe`
5. `special_tokens`
6. `checkpointing`

## `run`

1. `output_dir`: root for run-local tokenizer outputs.
2. `seed`: reserved field.
3. `log_level`: console log level.
4. `report_output_path`: canonical markdown output path (default `docs/data_collection_report.md`).
5. `stage3_metrics_every_merges`: Stage 3 telemetry/logging interval.

## `data`

1. `input_paths`: files/directories to scan.
2. `input_format`: `text` or `jsonl`.
3. `jsonl_text_field`: source field when `input_format=jsonl`.
4. `decode_errors`: UTF-8 decode policy (`strict`, `replace`, `ignore`).
5. `normalize`: `none`, `NFC`, or `NFKC`.
6. `max_bytes`: optional cap on raw bytes read.
7. `max_lines`: optional cap on lines read.
8. `num_workers`: Stage 1 worker process count.
9. `batch_lines`: line batch size per worker task.
10. `min_piece_freq`: Stage 2 inventory filter threshold.
11. `max_unique_pieces`: deterministic Stage 1 top-K memory cap.

## `pretokenizer`

1. `pattern`: `gpt2_fast`, `gpt2_default`, or `custom`.
2. `custom_pattern`: required when `pattern=custom`.
3. `flags`: regex flags list.

## `bpe`

1. `vocab_size`: target exported vocab size (bytes + merges + specials).
2. `min_merge_freq`: stop when best pair falls below threshold.
3. `max_merges`: direct merge-count override (if null, derived from `vocab_size`).
4. `max_word_types`: cap unique piece inventory after deterministic sorting.
5. `max_piece_bytes`: drop overly long pieces in Stage 1 worker path.
6. `tie_break`: must be `lexicographic`.

## `special_tokens`

1. `tokens`: ordered special-token list.
2. `placement`: `end` (recommended) or `start`.

## `checkpointing`

1. `enabled`: turn checkpoint instrumentation on/off.
2. `snapshot_every_merges`: periodic snapshot interval (`0` disables snapshots).
3. `wal_enabled`: emit merge WAL entries when checkpointing is enabled.
4. `wal_fsync_every_commits`: periodic fsync cadence for WAL durability.
5. `wal_fsync_mode`: `periodic` or `per_commit`.
6. `resume_mode`: `off` or `auto` (currently accepted; Stage 03 still starts fresh).
