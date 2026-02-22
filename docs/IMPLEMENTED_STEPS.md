# Implemented Steps (Detailed)

This document is the implementation-level reference for what is already built in the scaffold pipeline.

## Step 01: Corpus creation (`scripts/01_make_corpus.py`)

Purpose:

1. Produce lightweight local corpus files for reproducible laptop runs.

Current behavior:

1. Attempts to load `wikitext-2-raw-v1` via `datasets`.
2. Falls back to bundled local sample lines if network/dataset access fails.
3. Cleans line whitespace and writes split files under `data/raw/`:
   - `train.txt`
   - `validation.txt`
   - `test.txt`

Artifacts:

1. `data/raw/train.txt`
2. `data/raw/validation.txt`
3. `data/raw/test.txt`

Known limitations:

1. No provenance metadata manifest emitted yet.
2. No data policy filtering beyond basic cleanup.

## Step 02: Tokenizer training (`scripts/02_train_tokenizer.py`)

Purpose:

1. Train and export a deterministic GPT-2 style UTF-8 byte-level BPE tokenizer locally.

Key components:

1. Config and hashing:
   - `scripts/tokenizer_bpe/config.py`
2. Regex pretokenizer:
   - `scripts/tokenizer_bpe/pretokenizer.py`
3. Byte-unicode mapping:
   - `scripts/tokenizer_bpe/byte_unicode.py`
4. Stage 1 counting:
   - `scripts/tokenizer_bpe/stage1_count.py`
5. Stage 2 state init:
   - `scripts/tokenizer_bpe/stage2_init.py`
6. Stage 3 merge learning:
   - `scripts/tokenizer_bpe/stage3_train.py`
7. Export:
   - `scripts/tokenizer_bpe/export.py`

Detailed behavior:

1. Pretokenization:
   - uses third-party `regex` module
   - supports `gpt2_fast` (default), `gpt2_default`, and `custom`
2. Stage 1 counting:
   - multiprocessing by line batches
   - counts UTF-8 piece byte strings
   - maintains resumable progress file with file offsets
3. Stage 2 initialization:
   - builds symbol sequences from byte IDs `0..255`
   - prepares frequency-weighted word-type inventory
4. Stage 3 merge loop:
   - incremental pair statistics
   - lazy max-heap candidate selection
   - append-only WAL (`BEGIN`/`COMMIT`)
   - periodic snapshots with checksum files
5. Export:
   - deterministic IDs
   - `vocab.json`, `merges.txt`, `tokenizer_config.json`, `special_tokens_map.json`, `training_stats.json`

Resumability contract:

1. Resume requires matching `config_hash` and `pattern_hash`.
2. `BEGIN` without `COMMIT` is ignored during recovery.
3. Snapshot validity requires readable payload and checksum match.

Runtime commands:

1. Train:
   - `python scripts/02_train_tokenizer.py --config configs/tokenizer_bpe.yaml`
2. Resume:
   - `python scripts/02_train_tokenizer.py --config configs/tokenizer_bpe.yaml --resume --run-id <run_id>`
3. Tokenizer tests:
   - `python -m pytest -q tests/tokenizer_bpe`
4. Fast tokenizer unit tests only:
   - `python -m pytest -q tests/tokenizer_bpe -m "not integration"`

Implemented tokenizer verification coverage:

1. Config validation and deterministic hashing.
2. Byte-unicode mapping invertibility and round-trip conversion.
3. Pretokenizer alias/flag behavior and whitespace-preserving segmentation.
4. Stage 1 input discovery, extraction, pruning, and checkpoint contracts.
5. Stage 2 deterministic filtering/sorting and base-vocab initialization.
6. Stage 3 merge helpers, tie-break behavior, WAL parsing, and mismatch guards.
7. Export ordering/collision contracts and stats output checks.
8. Runtime encode/decode round-trip checks.
9. Deterministic full-pipeline export equivalence checks.
10. Resume/recovery equivalence checks against uninterrupted runs.

Detailed docs:

1. `docs/TOKENIZER_BPE.md`
2. `CONFIG.md`
3. `CHECKPOINTING.md`

Known limitations:

1. CI wiring for tokenizer markers (`integration`, `recovery`, `determinism`) is not yet configured in this repository.
2. Model-training stages still need equivalent checkpoint rigor.

## Step 03: Tiny pretraining (`scripts/03_pretrain.py`)

Purpose:

1. Train a small GPT-2 style causal LM from local text to validate stage interfaces.

Current behavior:

1. Loads tokenizer from `artifacts/tokenizer/gpt2`.
2. Loads local corpus via `datasets`.
3. Tokenizes and groups into fixed block-size sequences.
4. Trains small GPT-2 config with `Trainer`.
5. Saves model and tokenizer to `artifacts/models/tiny-gpt2-from-scratch`.

Known limitations:

1. Production-grade checkpoint/recovery semantics are not yet formalized.
2. Small-model defaults are for scaffold validation, not quality target attainment.

## Step 04: LoRA SFT (`scripts/04_sft_lora.py`)

Purpose:

1. Demonstrate instruction tuning with lightweight adapters.

Current behavior:

1. Loads base model from pretraining artifact.
2. Loads Alpaca subset when available, otherwise fallback local examples.
3. Applies LoRA adapter config and trains with `Trainer`.
4. Saves adapter and tokenizer in `artifacts/models/tiny-gpt2-sft-lora`.

Known limitations:

1. Instruction dataset governance and quality gates are not yet formalized.
2. No preference optimization or safety-specific post-training stage yet.

## Step 05: Evaluation smoke test (`scripts/05_eval_generate.py`)

Purpose:

1. Run a basic generation sanity check against latest trained artifact.

Current behavior:

1. Prefers SFT artifact, falls back to base pretrained artifact.
2. Generates response from a fixed prompt with stochastic decoding.

Known limitations:

1. This is a smoke test only, not a release-grade capability/safety harness.

## Utility: Zone.Identifier cleanup (`scripts/cleanup_zone_identifier.py`)

Purpose:

1. Remove Windows-origin `Zone.Identifier` sidecar files from the repository tree.

Current behavior:

1. Recursively scans from the repository root by default.
2. Deletes any file whose filename contains `Zone.Identifier`.
3. Skips Python virtual environment folders by common directory names/prefixes and by detecting `pyvenv.cfg`.
4. Supports dry-run mode (`--dry-run`) and optional directory exclusions (`--skip-dir`).

Runtime commands:

1. Preview deletions:
   - `python scripts/cleanup_zone_identifier.py --dry-run`
2. Apply deletions:
   - `python scripts/cleanup_zone_identifier.py`

Validation:

1. `python -m unittest -q tests.test_cleanup_zone_identifier`

## Traceability matrix

Implemented step documentation pointers:

1. High-level onboarding: `README.md`
2. Architecture and north-star context: `llm_training_overview.md`
3. Current state and gaps: `docs/PROJECT_STATUS.md`
4. Stage roadmap: `docs/NEXT_STEPS.md`
5. Detailed tokenizer implementation: `docs/TOKENIZER_BPE.md`
6. Agent and repo operations: `AGENTS.md`
