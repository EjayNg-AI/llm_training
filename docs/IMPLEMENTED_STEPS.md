# Implemented Steps (Detailed)

This document is the implementation-level reference for what is built in the canonical scaffold pipeline.

## Canonical Stage 01: Build corpus (`scripts/01_build_corpus.py`)

Purpose:

1. Convert raw input files into canonical document records with deterministic ordering and IDs.

Current behavior:

1. Discovers input files deterministically from configured paths.
2. Supports text inputs (with optional gzip) and configurable normalization.
3. Emits canonical docs with schema:
   - `doc_id`
   - `text`
   - `source`
   - `timestamp`
   - `meta`
4. Filters short docs (`data.min_chars`).
5. Publishes artifact + manifest + registry entry.

Artifacts:

1. `artifacts/corpora/<corpus_id>/docs.jsonl.gz`
2. `artifacts/corpora/<corpus_id>/artifact_manifest.json`
3. `artifacts/registry.jsonl` append entry

Run outputs:

1. `run_meta.json`
2. `state.json`
3. `metrics.jsonl`
4. `logs/run.log` (+ optional `logs/run.jsonl`)

## Canonical Stage 02: Exact dedup (`scripts/02_dedup_exact.py`)

Purpose:

1. Remove exact duplicate documents deterministically before tokenization.

Current behavior:

1. Consumes corpus artifact from registry by ID (or latest).
2. Dedup key is `sha256(text)`.
3. Order-independent retention rule keeps lexicographically smallest `doc_id` per dedup key.
4. Publishes dedup corpus artifact + manifest + registry entry.

Artifacts:

1. `artifacts/corpora/<dedup_id>/docs.dedup.jsonl.gz`
2. `artifacts/corpora/<dedup_id>/artifact_manifest.json`
3. `artifacts/registry.jsonl` append entry

## Canonical Stage 03: Train tokenizer (`scripts/03_train_tokenizer.py`)

Purpose:

1. Train and export deterministic, resumable GPT-2 style UTF-8 byte-level BPE tokenizer artifacts.

Current behavior:

1. Reuses existing tokenizer implementation modules under `scripts/tokenizer_bpe/`:
   - regex pretokenization
   - Stage 1 multiprocessing piece counting with out-of-order worker completion and deterministic in-order merge application
   - Stage 1 special-token stripping after optional normalization and before regex pretokenization, so configured special-token literals never affect learned counts or merges
   - expanded default special-token inventory covering BOS/EOS/PAD/UNK plus chat, FIM, and metadata/control markers
   - Stage 2/3 compact integer-array state (`array('H'/'I')` words + array-backed freqs)
   - Stage 3 packed pair IDs (`pair_id = (a << 32) | b`), append-light pair index maintenance, heap pressure controls, and WAL + snapshot recovery
   - Stage 3 resume hardening with `wal.meta.json` hash binding and stricter WAL replay checks (contiguous merge indices + merge-effect validation)
   - Stage 3 PoC durability defaults (periodic fsync with paranoid per-commit option)
   - direct CLI overrides for `max_unique_pieces` and `max_word_types`, folded into the effective config hash
   - deterministic merge/export behavior
   - low-`vocab_size` floor contract: merge count can be zero while export still includes base 256 bytes plus configured specials
2. Publishes tokenizer artifacts by artifact ID under `artifacts/tokenizer/exports/<tokenizer_id>/`.
3. Registers tokenizer artifact with manifest and lineage metadata.

Artifacts:

1. `vocab.json`
2. `merges.txt`
3. `tokenizer_config.json`
4. `special_tokens_map.json`
5. `training_stats.json`
6. `artifact_manifest.json`

Resume contract:

1. `--resume --run-id <run_id>` reuses existing run directory.
2. Resume validates WAL hash binding (`wal.meta.json`) against current `config_hash`/`pattern_hash`.
3. WAL replay enforces contiguous merge indices and non-noop replay merges.
4. Default policy keeps `max_bytes`, `max_lines`, and `max_merges` unlimited unless set, while `max_unique_pieces` and `max_word_types` default to `2500000`.

## Canonical Stage 04: Tokenize corpus (`scripts/04_tokenize_corpus.py`)

Purpose:

1. Convert canonical docs to deterministic token shards with per-doc offsets.

Current behavior:

1. Consumes corpus and tokenizer by artifact IDs from registry.
2. Uses runtime tokenizer API (`ByteLevelBPETokenizer`) from `src/llm_training/tokenizer/runtime.py`.
3. Supports `uint16`/`uint32` token dtype (default `uint32`).
4. Uses deterministic shard boundaries (`docs_per_shard`).
5. Optional EOS append per doc with per-row `eos_appended` indicator.
6. Supports safe resume via stage state signature and shard-level atomic commit.

Artifacts:

1. `artifacts/tokens/<token_shards_id>/shards/tokens_shard_XXXXX.bin`
2. `artifacts/tokens/<token_shards_id>/shards/tokens_shard_XXXXX.idx.json`
3. `artifacts/tokens/<token_shards_id>/index.json`
4. `artifacts/tokens/<token_shards_id>/artifact_manifest.json`

## Canonical Stage 05: Pack sequences (`scripts/05_pack_sequences.py`)

Purpose:

1. Convert token shards into fixed-length train/val sequence blocks.

Current behavior:

1. Consumes token shard artifact by ID.
2. Deterministic split assignment via `hash(doc_id) % split_mod`.
3. Packing strategy v0:
   - stream tokens per split
   - truncate to exact multiple of `seq_len`
   - no overlap (`stride == seq_len`)
4. Emits packed train/val binary shards and index metadata.

Artifacts:

1. `artifacts/packed/<packed_id>/train/shards/pack_00000.bin`
2. `artifacts/packed/<packed_id>/val/shards/pack_00000.bin`
3. `artifacts/packed/<packed_id>/index.json`
4. `artifacts/packed/<packed_id>/artifact_manifest.json`

## Canonical Stage 06: Pretrain (`scripts/06_pretrain.py`)

Purpose:

1. Run local GPT-style pretraining from packed artifact IDs with explicit checkpointing.

Current behavior:

1. Consumes `packed` and `tokenizer` artifacts by ID.
2. Builds a small GPT2LMHeadModel from config and trains with a local loop.
3. Saves checkpoints containing:
   - model state
   - optimizer state
   - scheduler state
   - RNG states (`python`, `numpy`, `torch`, `cuda` if available)
   - global step
4. Supports resume from latest stage checkpoint.
5. Publishes model artifact and registry entry.

Artifacts:

1. `artifacts/models/<model_id>/...` (HF model files + tokenizer files)
2. `artifacts/models/<model_id>/artifact_manifest.json`
3. `artifacts/registry.jsonl` append entry

## Canonical Stage 07: LoRA SFT (`scripts/07_sft_lora.py`)

Purpose:

1. Fine-tune a published base model artifact using LoRA adapters.

Current behavior:

1. Consumes base model artifact by ID.
2. Uses Alpaca subset when available; falls back to local examples offline.
3. Trains with `Trainer` and saves SFT artifact by ID.
4. Publishes model artifact manifest and registry entry.

Artifacts:

1. `artifacts/models/<sft_id>/...`
2. `artifacts/models/<sft_id>/artifact_manifest.json`
3. `artifacts/registry.jsonl` append entry

## Canonical Stage 08: Evaluation (`scripts/08_eval.py`)

Purpose:

1. Evaluate model artifacts with perplexity (optional packed dataset) and sample generation.

Current behavior:

1. Consumes `model` artifact by ID and optional `packed` artifact for perplexity.
2. Generates eval outputs:
   - `eval.json`
   - `samples.txt`
3. Publishes eval artifact + manifest + registry entry.

Artifacts:

1. `artifacts/eval/<eval_id>/eval.json`
2. `artifacts/eval/<eval_id>/samples.txt`
3. `artifacts/eval/<eval_id>/artifact_manifest.json`
4. `artifacts/registry.jsonl` append entry

## Shared infrastructure implementation

Modules under `src/llm_training/infra/`:

1. `run_dir.py`:
   - run lifecycle metadata (`run_meta.json`)
   - stage `state.json`
   - stage `metrics.jsonl`
2. `hashing.py`:
   - canonical JSON + stable SHA-256 hashing helpers
3. `io_atomic.py`:
   - atomic write/replace for text/json/pickle
4. `logging.py`:
   - consistent stage logging format and destinations
5. `manifest.py`:
   - artifact manifest schema builder
   - artifact directory resolution
   - registry append publishing helpers
6. `resume.py`:
   - resume signature compatibility gates

Tokenizer runtime library:

1. `src/llm_training/tokenizer/runtime.py` (`ByteLevelBPETokenizer`)
2. `src/llm_training/tokenizer/special.py` (special token ID resolution)

## Legacy scaffold scripts (non-canonical)

These scripts remain in-repo for ad-hoc/local compatibility and reference:

1. `scripts/01_make_corpus.py`
2. `scripts/02_train_tokenizer.py`
3. `scripts/03_pretrain.py`
4. `scripts/04_sft_lora.py`
5. `scripts/05_eval_generate.py`

Use canonical `01..08` scripts for artifact-lineage workflows.

## Runtime commands

Canonical flow:

1. `python scripts/01_build_corpus.py --config configs/corpus.yaml`
2. `python scripts/02_dedup_exact.py --config configs/dedup.yaml`
3. `python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe.yaml`
4. `python scripts/04_tokenize_corpus.py --config configs/tokenize.yaml`
5. `python scripts/05_pack_sequences.py --config configs/pack.yaml`
6. `python scripts/06_pretrain.py --config configs/train.yaml`
7. `python scripts/07_sft_lora.py --config configs/sft.yaml`
8. `python scripts/08_eval.py --config configs/eval.yaml`

Tokenizer resume:

1. `python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe.yaml --resume --run-id <run_id>`

Tests:

1. `python -m pytest -q`
2. `python -m pytest -q tests/tokenizer_bpe`
3. `python -m pytest -q tests/tokenizer_bpe -m "not integration"`

## Validation coverage added for this stage expansion

1. Infrastructure unit tests:
   - hashing determinism
   - atomic JSONL append and atomic dump behavior
   - manifest publish + registry append behavior
2. Runtime tokenizer tests:
   - encode/decode round-trip with exported artifact format
   - special token ID mapping
3. Pipeline integration smoke test:
   - corpus build -> dedup -> tokenize -> pack using artifact registry

## Traceability matrix

1. High-level onboarding: `README.md`
2. Architecture and north-star context: `llm_training_overview.md`
3. Current state and gaps: `docs/PROJECT_STATUS.md`
4. Stage roadmap: `docs/NEXT_STEPS.md`
5. Detailed tokenizer implementation: `docs/TOKENIZER_BPE.md`
6. Agent and repo operations: `AGENTS.md`
