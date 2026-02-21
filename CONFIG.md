# Tokenizer Config Reference

The tokenizer trainer uses one source-of-truth config file:

- `configs/tokenizer_bpe.yaml`

## Top-level sections

- `run`: output location and logging configuration
- `data`: corpus input settings and Stage 1 counting controls
- `pretokenizer`: regex pattern family and regex flags
- `bpe`: merge loop and vocabulary controls
- `special_tokens`: reserved tokens appended at export
- `checkpointing`: WAL and snapshot durability policy

## `run`

- `output_dir`: root directory for run state (`artifacts/tokenizer/runs`)
- `seed`: reserved for future randomized behaviors (currently deterministic path)
- `log_level`: logging level (`INFO`, `DEBUG`, ...)
- `structured_logs`: if true, writes JSONL logs in addition to text logs

## `data`

- `input_paths`: files/directories to scan
- `input_format`: `text` or `jsonl`
- `jsonl_text_field`: source field when `input_format=jsonl`
- `decode_errors`: UTF-8 decode policy (`strict`, `replace`, `ignore`)
- `normalize`: `none`, `NFC`, or `NFKC`
- `max_bytes`: optional global cap on raw bytes read
- `max_lines`: optional global cap on lines read
- `num_workers`: Stage 1 worker process count
- `batch_lines`: line batch size per worker task
- `min_piece_freq`: low-frequency filtering threshold
- `max_unique_pieces`: optional hard cap after deterministic top-K pruning

## `pretokenizer`

- `pattern`:
  - `gpt2_fast` (default; faster equivalent)
  - `gpt2_default` (canonical GPT-2 release pattern)
  - `custom` (requires `custom_pattern`)
- `custom_pattern`: explicit regex when `pattern=custom`
- `flags`: list of regex flags (`IGNORECASE`, `MULTILINE`)

Resume safety:

- Run state records `pattern_alias`, exact pattern string, flags, and `regex` module version.
- A derived `pattern_hash` is enforced at resume time; mismatches fail fast.

## `bpe`

- `vocab_size`: target exported vocab size (base bytes + merges + specials)
- `min_merge_freq`: stop training if best pair count drops below this threshold
- `max_merges`: override merge count directly (if null, derived from `vocab_size`)
- `max_word_types`: cap unique piece inventory after deterministic sorting
- `max_piece_bytes`: drop unusually long pieces in Stage 1 worker path
- `tie_break`: currently `lexicographic` only

## `special_tokens`

- `tokens`: ordered list of special token strings
- `placement`: `end` (recommended) or `start` in exported vocab ID layout

## `checkpointing`

- `wal_fsync_each_commit`: durable WAL on each BEGIN/COMMIT write
- `snapshot_every_merges`: Stage 3 snapshot interval in merges
- `snapshot_every_seconds`: Stage 1/3 time-based checkpoint interval
- `keep_last_snapshots`: number of recent Stage 3 snapshots to retain
- `stage1_snapshot_every_batches`: Stage 1 snapshot interval by merged worker results

