# GPT-2 Style UTF-8 Byte-Level BPE Tokenizer

This is the implementation reference for tokenizer Stage 03 in this repository.

## Scope

Stage 03 trains and exports a deterministic GPT-2 style UTF-8 byte-level BPE tokenizer.

Current Stage 03 design intentionally keeps run-local outputs minimal:

1. no checkpoint/resume workflow
2. no WAL/snapshot state files
3. no persisted run log files
4. duration telemetry only (`training_telemetry.json`)

## Entrypoint

Train:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe.yaml
```

OpenWebText 32k example:

```bash
python scripts/03_train_tokenizer.py \
  --config configs/tokenizer_bpe_owt_32k.yaml \
  --run-id owt32k_run01 \
  --artifact-id tokenizer_owt_32k_run01
```

Key CLI options:

1. `--run-id` selects the run subdirectory under `run.output_dir`.
2. `--stop-after-merges` is a debug/testing knob for early stop.
3. `--artifact-id` controls published tokenizer artifact ID.

## Run and Export Outputs

Run directory (`run.output_dir/<run_id>/`) now contains:

1. `training_telemetry.json`

`training_telemetry.json` fields:

1. `training_started_at`
2. `training_ended_at`
3. `elapsed_seconds`

Export directory (`artifacts/tokenizer/exports/<artifact_id>/`) contains:

1. `vocab.json`
2. `merges.txt`
3. `tokenizer_config.json`
4. `special_tokens_map.json`
5. `training_stats.json`
6. `artifact_manifest.json`

Published tokenizer exports are registered in:

1. `artifacts/registry.jsonl`

## Configuration Contract

Config sources:

1. `configs/tokenizer_bpe.yaml`
2. `configs/tokenizer_bpe_owt_32k.yaml` (OpenWebText example)
3. defaults in `scripts/tokenizer_bpe/config.py`

Top-level config sections:

1. `run`
2. `data`
3. `pretokenizer`
4. `bpe`
5. `special_tokens`

No `checkpointing` section is used in Stage 03.

Default config:

```yaml
run:
  output_dir: "artifacts/tokenizer/runs"
  seed: 0
  log_level: "INFO"

data:
  input_paths:
    - "data/raw/train.txt"
  input_format: "text"
  jsonl_text_field: "text"
  decode_errors: "replace"
  normalize: "none"
  max_bytes: null
  max_lines: null
  num_workers: 4
  batch_lines: 2000
  min_piece_freq: 2
  max_unique_pieces: 2000000

pretokenizer:
  pattern: "gpt2_fast"
  custom_pattern: null
  flags: []

bpe:
  vocab_size: 50000
  min_merge_freq: 2
  max_merges: null
  max_word_types: 1500000
  max_piece_bytes: 200
  tie_break: "lexicographic"

special_tokens:
  tokens:
    - "<|endoftext|>"
    - "<|pad|>"
  placement: "end"
```

## Algorithm Summary

High-level flow:

1. Stage 1: pretokenize corpus and count UTF-8 piece bytes.
2. Stage 2: initialize weighted word-type state from piece counts.
3. Stage 3: learn merges by repeatedly applying highest-frequency adjacent pair.
4. Stage 4: export tokenizer artifacts.

Determinism-critical contracts:

1. Stage 1 merges worker completions in contiguous `batch_id` order.
2. Piece inventory sorting and tie-break behavior are deterministic.
3. Stage 3 best-pair selection uses heap tuples `(-count, pair_id)` with lexicographic pair tie-break via `pair_id`.
4. Export ID assignment is stable for fixed corpus + config.

## Stage 1 Notes

Module: `scripts/tokenizer_bpe/stage1_count.py`

1. Supports `text` and `jsonl` inputs (optionally `.gz`).
2. Applies optional line normalization (`none`, `NFC`, `NFKC`) before regex piece extraction.
3. Drops pieces longer than `bpe.max_piece_bytes`.
4. Uses a single deterministic memory approximation knob:
   - optional top-K capping by `data.max_unique_pieces` every 100 merged batches.
5. Emits console progress logs; no persisted Stage 1 progress files.

## Stage 2 Notes

Module: `scripts/tokenizer_bpe/stage2_init.py`

1. Converts byte-piece counts into weighted word types.
2. Initializes base byte vocabulary (`0..255`).
3. Chooses compact storage type (`array('H')` or `array('I')`) from max symbol ID bound.

## Stage 3 Notes

Module: `scripts/tokenizer_bpe/stage3_train.py`

1. No resume/WAL/snapshot mechanics.
2. Runs merge learning fully in-memory for each run.
3. Maintains `pair_count` incrementally and rebuilds heap periodically under stale-growth pressure.
4. Emits periodic console progress logs.

Stop conditions:

1. no remaining valid pair
2. best pair count below `bpe.min_merge_freq`
3. reached merge target derived from `bpe.vocab_size`/`bpe.max_merges`
4. optional debug stop via `--stop-after-merges`

## Export Contract

Module: `scripts/tokenizer_bpe/export.py`

Artifacts:

1. `vocab.json`: token string -> ID
2. `merges.txt`: merge order (`#version: 0.2` + token-string pairs)
3. `tokenizer_config.json`: pattern metadata, hashes, tokenizer metadata
4. `special_tokens_map.json`
5. `training_stats.json`

`training_stats.json` includes:

1. `run_dir`
2. `final_merge_index`
3. `vocab_size`
4. `num_merges`
5. `config_hash`
6. `pattern_hash`
7. `training_corpus_sha256`

## Testing References

Tokenizer-focused tests live under:

1. `tests/tokenizer_bpe/`

Common commands:

```bash
python -m pytest -q tests/tokenizer_bpe
python -m pytest -q tests/tokenizer_bpe -m "not integration"
```
