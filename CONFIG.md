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
- `max_bytes`: optional global cap on raw bytes read; default `null` means unlimited
- `max_lines`: optional global cap on lines read; default `null` means unlimited
- `num_workers`: Stage 1 worker process count
- `batch_lines`: line batch size per worker task
- `min_piece_freq`: low-frequency filtering threshold applied during Stage 2 inventory initialization
- `max_unique_pieces`: deterministic top-K cap used as Stage 1 memory approximation control; default `2500000`

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

## Config hashing contract (`config_hash`)

Tokenizer training computes `config_hash` from the merged config payload (defaults plus user overrides) before adding runtime metadata.

Canonicalization is:

1. Serialize with `json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
2. Encode the serialized JSON as UTF-8.
3. Compute SHA-256 over those bytes.

Notes:

- List order is preserved and contributes to hash identity.
- No path normalization is applied; path strings are hashed as configured.
- The normative implementation reference is `scripts/tokenizer_bpe/config.py` and the detailed algorithm contract is in `docs/TOKENIZER_BPE.md`.

## `bpe`

- `vocab_size`: target exported vocab size (base bytes + merges + specials)
  - Floor edge case: when `vocab_size < 256 + len(special_tokens.tokens)`, Stage 3 can perform zero merges.
  - In that edge case, export still includes all 256 byte tokens plus all configured special tokens, so final exported vocab can exceed requested `vocab_size`.
- `min_merge_freq`: stop training if best pair count drops below this threshold
- `max_merges`: override merge count directly; default `null` means no explicit cap and derived target merges from `vocab_size`
- `max_word_types`: cap unique piece inventory after deterministic sorting; default `2500000`
- `max_piece_bytes`: drop unusually long pieces in Stage 1 worker path
- `tie_break`: currently `lexicographic` only

## `special_tokens`

- `tokens`: ordered list of special token strings
- `placement`: `end` (recommended) or `start` in exported vocab ID layout

## `checkpointing`

- `wal_fsync_each_commit`: paranoid mode; fsync WAL after each committed merge
- `wal_fsync_every_commits`: fsync cadence when not in paranoid mode (`0` disables periodic fsync and relies on snapshot/final fsync)
- `snapshot_every_merges`: Stage 3 snapshot interval in merges
- `snapshot_every_seconds`: Stage 1/3 time-based checkpoint interval
- `keep_last_snapshots`: number of recent Stage 3 snapshots to retain
- `stage1_snapshot_every_batches`: Stage 1 snapshot interval by merged worker results
