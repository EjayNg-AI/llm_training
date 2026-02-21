# GPT-2 Style UTF-8 Byte-Level BPE Tokenizer (Implementation Details)

This document describes the implemented tokenizer training system in this repository.

## Objective

Implement a deterministic, resumable, laptop-runnable GPT-2 style UTF-8 byte-level BPE tokenizer trainer in pure Python.

## Entrypoint

Command:

```bash
python scripts/02_train_tokenizer.py --config configs/tokenizer_bpe.yaml
```

Resume:

```bash
python scripts/02_train_tokenizer.py --config configs/tokenizer_bpe.yaml --resume --run-id <run_id>
```

## Implemented architecture

## 1) Config loading and run contract

Module:

- `scripts/tokenizer_bpe/config.py`

Behavior:

1. Loads YAML config with defaults.
2. Validates key constraints (formats, ranges, allowed enum values).
3. Computes deterministic `config_hash`.
4. Computes `pattern_hash` from:
   - pattern string
   - regex flags
   - normalization setting
   - `regex` package version

## 2) Pretokenization

Module:

- `scripts/tokenizer_bpe/pretokenizer.py`

Patterns:

1. `gpt2_fast` (default)
2. `gpt2_default` (canonical GPT-2 pattern)
3. `custom` (user-supplied)

Implementation notes:

1. Uses third-party `regex` for Unicode character classes.
2. Uses `finditer` for streaming match iteration.
3. Pattern is compiled once per worker process initializer for Stage 1.

## 3) Stage 1 piece counting (parallel + resumable)

Module:

- `scripts/tokenizer_bpe/stage1_count.py`

Behavior:

1. Discovers input files deterministically.
2. Reads in binary mode and tracks byte offsets for progress.
3. Decodes lines using configured `decode_errors` policy.
4. Applies optional normalization.
5. Pretokenizes text and counts UTF-8 piece byte strings.
6. Merges worker counters deterministically.
7. Persists checkpoints:
   - `word_counts.snapshot.pkl`
   - `word_counts.progress.json`
8. Supports pruning/caps:
   - `max_piece_bytes`
   - `min_piece_freq`
   - `max_unique_pieces`

Progress metadata includes:

1. per-file offset and completion state
2. total lines/pieces/bytes processed
3. `config_hash`
4. `pattern_hash`

## 4) Stage 2 initialization

Module:

- `scripts/tokenizer_bpe/stage2_init.py`

Behavior:

1. Converts piece bytes to base symbol ID sequences (`0..255`).
2. Keeps deterministic top inventory by frequency + lexicographic bytes.
3. Builds:
   - `words`
   - `freqs`
   - `id_to_token_bytes` base table

## 5) Stage 3 merge learning (WAL + snapshots)

Module:

- `scripts/tokenizer_bpe/stage3_train.py`

Core data structures:

1. `pair_count[(a,b)] -> weighted frequency`
2. `pair_to_words[(a,b)] -> candidate word indices` (lazy invalidation)
3. max-heap over `(-count, a, b)` for deterministic selection

Merge transaction flow:

1. Select best pair from lazy heap.
2. Append WAL `BEGIN`.
3. Create new token ID and update symbol table.
4. Update only affected words and pair deltas.
5. Append WAL `COMMIT`.
6. Periodically snapshot full core state.

Durability model:

1. WAL is append-only.
2. Merge is durable only after `COMMIT`.
3. Snapshot includes checksum sidecar.
4. Resume replays committed WAL records beyond latest valid snapshot.
5. Mismatched `config_hash` or `pattern_hash` prevents resume.

## 6) Export format

Module:

- `scripts/tokenizer_bpe/export.py`

Artifacts:

1. `vocab.json`
2. `merges.txt`
3. `tokenizer_config.json`
4. `special_tokens_map.json`
5. `training_stats.json`

ID policy:

1. Base byte tokens first.
2. Learned merges in merge order.
3. Special tokens appended (or prepended if configured).

## 7) Logging and metrics

Run files:

1. `train.log`
2. `train.jsonl` (when enabled)
3. `metrics.jsonl`
4. `state.json`

Metrics include merge index, best pair count, unique pairs, and affected word types.

## 8) Determinism guarantees implemented

1. Stable file discovery ordering.
2. Stable pruning and top-K tie-breaks.
3. Lexicographic pair tie-break via heap tuple order.
4. Hash-gated resume to avoid incompatible restarts.

## 9) Verification assets in repository

Tests:

1. `tests/tokenizer_bpe/test_config.py`
2. `tests/tokenizer_bpe/test_byte_unicode.py`
3. `tests/tokenizer_bpe/test_pretokenizer.py`
4. `tests/tokenizer_bpe/test_stage1_count_unit.py`
5. `tests/tokenizer_bpe/test_stage2_init.py`
6. `tests/tokenizer_bpe/test_stage3_core.py`
7. `tests/tokenizer_bpe/test_stage3_recovery.py`
8. `tests/tokenizer_bpe/test_export.py`
9. `tests/tokenizer_bpe/test_runtime_check.py`
10. `tests/tokenizer_bpe/test_train_tokenizer_determinism.py`
11. `tests/tokenizer_bpe/test_train_tokenizer_resume.py`

Fixtures and test utilities:

1. `tests/tokenizer_bpe/conftest.py`
2. `tests/tokenizer_bpe/helpers.py`
3. `tests/fixtures/tokenizer_bpe/tiny_corpus.txt`
4. `tests/fixtures/tokenizer_bpe/sample.jsonl`

Execution commands:

1. `python -m pytest -q tests/tokenizer_bpe`
2. `python -m pytest -q tests/tokenizer_bpe -m "not integration"`

Supporting docs:

1. `technical_spec_bpe_train_tokenizer.md`
2. `CONFIG.md`
3. `CHECKPOINTING.md`

## 10) Known open items

1. Wire tokenizer tests into CI with explicit marker selection (`integration` on merge or nightly).
2. Add stress/performance tests for larger corpora and higher merge counts.
3. Add downstream artifact-compatibility checks against `scripts/03_pretrain.py` and `scripts/05_eval_generate.py`.
