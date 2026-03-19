# Changelog

All notable repository changes should be recorded in this file.

Format:

1. Use `YYYY-MM-DD` dates.
2. Group by release tag or `Unreleased`.
3. For each entry include:
   - summary
   - impacted files/modules
   - validation status
   - documentation updates

## Unreleased

### 2026-03-19 (Add TinyStories Markdown/LaTeX-aware BPE training config)

Summary:

1. Added a dedicated TinyStories tokenizer config that reuses the local TinyStories training corpus while selecting the `md_latex_fast_v1` pretokenizer path.
2. Tightened the Stage 1 worker/cap settings for that TinyStories Markdown/LaTeX-aware run to match the existing markup-heavy experiment profile.
3. Documented the manual train and resume commands and added a regression test that loads the new config.

Impacted files/modules:

1. `configs/tokenizer_bpe_tinystories_md_latex_train.yaml`
2. `tests/tokenizer_bpe/test_config_tinystories_md_latex.py`
3. `README.md`
4. `docs/IMPLEMENTED_STEPS.md`
5. `docs/DIRECTORY_STRUCTURE.md`
6. `docs/CHANGELOG.md`

Validation status:

1. Pending local config-focused pytest run.

Documentation updates:

1. Updated `README.md` with the TinyStories Markdown/LaTeX-aware train and resume commands.
2. Updated `docs/IMPLEMENTED_STEPS.md` Stage 03 config summary for the new tracked config.
3. Updated `docs/DIRECTORY_STRUCTURE.md` with the new config and regression test file.

### 2026-03-19 (Add Markdown/LaTeX-aware BPE experiment alias and Stage 1 safety caps)

Summary:

1. Added a versioned `md_latex_fast_v1` pretokenizer alias that keeps local LaTeX commands, simple `_` / `^` math affixes, Markdown headings, and Markdown task boxes together without changing the default `gpt2_fast` alias.
2. Added configurable Stage 1 periodic cap knobs plus an early deterministic safety-cap path for transient unique-piece spikes.
3. Added a tracked experiment config for Markdown/LaTeX-heavy tokenizer A/B runs.
4. Extended tokenizer unit coverage for the new alias, config validation, and early Stage 1 safety-cap behavior.

Impacted files/modules:

1. `scripts/tokenizer_bpe/pretokenizer.py`
2. `scripts/tokenizer_bpe/config.py`
3. `scripts/tokenizer_bpe/stage1_count.py`
4. `configs/tokenizer_bpe_md_latex_experiment.yaml`
5. `tests/tokenizer_bpe/test_pretokenizer.py`
6. `tests/tokenizer_bpe/test_config.py`
7. `tests/tokenizer_bpe/test_stage1_count_unit.py`
8. `README.md`
9. `docs/TOKENIZER_BPE.md`
10. `docs/IMPLEMENTED_STEPS.md`
11. `docs/DIRECTORY_STRUCTURE.md`
12. `docs/CHANGELOG.md`

Validation status:

1. Pending local tokenizer test runs.

Documentation updates:

1. Updated `README.md` with the experiment config entrypoint and Stage 1 cap summary.
2. Updated `docs/TOKENIZER_BPE.md` with the new alias contract and configurable Stage 1 pruning behavior.
3. Updated `docs/IMPLEMENTED_STEPS.md` Stage 03 summary for the additive alias and safety-cap path.
4. Updated `docs/DIRECTORY_STRUCTURE.md` with the new tracked config file.

### 2026-03-19 (Expand BPE training corpus ignore rules)

Summary:

1. Expanded `.gitignore` so local `.txt` and `.gz` corpora used for BPE training are ignored more comprehensively.
2. Added explicit ignore coverage for repository-root `proof_pile` corpora and corpus-name patterns for OWT/OpenWebText, TinyStories, and Proof Pile files outside the generic `train`/`valid` naming scheme.

Impacted files/modules:

1. `.gitignore`
2. `docs/CHANGELOG.md`

Validation status:

1. Pending local `git check-ignore` spot checks.

Documentation updates:

1. Updated `docs/CHANGELOG.md` with the new ignore-rule scope.

### 2026-03-19 (Raise default BPE training caps and target vocab)

Summary:

1. Raised the default tokenizer inventory cap `data.max_unique_pieces` from `2500000` to `3500000`.
2. Raised the default Stage 2 cap `bpe.max_word_types` from `2500000` to `3000000`.
3. Raised the default tokenizer target vocabulary size from `50000` to `64000`, and updated the TinyStories training config to follow the new default target.

Impacted files/modules:

1. `scripts/tokenizer_bpe/config.py`
2. `configs/tokenizer_bpe.yaml`
3. `configs/tokenizer_bpe_tinystories_32k_train.yaml`
4. `README.md`
5. `docs/TOKENIZER_BPE.md`
6. `docs/IMPLEMENTED_STEPS.md`
7. `docs/CHANGELOG.md`
8. `tests/tokenizer_bpe/test_config.py`

Validation status:

1. Pending local config/unit-test validation.

Documentation updates:

1. Updated `README.md` tokenizer default-policy guidance and override example.
2. Updated `docs/TOKENIZER_BPE.md` default config block and default-policy contract.
3. Updated `docs/IMPLEMENTED_STEPS.md` Stage 03 default-policy summary.

### 2026-03-19 (Add Proof Pile tokenizer training run config)

Summary:

1. Added a dedicated tokenizer config for training on the local repository-root corpus file `proof_pile.txt`.
2. Reused the default tokenizer BPE settings in effect at the time, including the then-default `50000` target vocabulary size.
3. Documented the manual train and resume commands in `README.md`.

Impacted files/modules:

1. `configs/tokenizer_bpe_proof_pile_train.yaml`
2. `README.md`
3. `docs/DIRECTORY_STRUCTURE.md`
4. `docs/CHANGELOG.md`

Validation status:

1. Pending local config validation.

Documentation updates:

1. Updated `README.md` with Proof Pile train/resume commands.
2. Updated `docs/DIRECTORY_STRUCTURE.md` with the new tracked config file and refreshed snapshot date.

### 2026-03-19 (Add TinyStories 32k tokenizer training run config)

Summary:

1. Added a dedicated tokenizer config for training on the local TinyStories corpus file `data/raw/TinyStoriesV2-GPT4-train.txt`.
2. Set the TinyStories tokenizer target vocabulary size to `32000` at the time; this config now follows the repository-wide `64000` default.
3. Documented the manual train and resume commands in `README.md`.

Impacted files/modules:

1. `configs/tokenizer_bpe_tinystories_32k_train.yaml`
2. `README.md`
3. `docs/DIRECTORY_STRUCTURE.md`
4. `docs/CHANGELOG.md`

Validation status:

1. `python -c "import sys; sys.path.insert(0, 'scripts'); from tokenizer_bpe.config import load_config; cfg = load_config('configs/tokenizer_bpe_tinystories_32k_train.yaml'); print(cfg['data']['input_paths'][0]); print(cfg['run']['output_dir']); print(cfg['bpe']['vocab_size'])"` passed at the time (`data/raw/TinyStoriesV2-GPT4-train.txt`, `artifacts/tokenizer/runs_tinystories_train`, `32000`).

Documentation updates:

1. Updated `README.md` with TinyStories train/resume commands.
2. Updated `docs/DIRECTORY_STRUCTURE.md` with the new tracked config file.

### 2026-03-18 (Expand default tokenizer special-token inventory)

Summary:

1. Expanded the default tokenizer special-token list to include the requested chat-role, message-boundary, BOS/EOS/PAD/UNK, FIM, and metadata/control markers.
2. Deduplicated repeated entries from the requested list in first-seen order before encoding them into repository defaults.
3. Updated export special-token mapping so `special_tokens_map.json` prefers explicit `<bos>`, `<eos>`, `<unk>`, and `<pad>` when those tokens exist, while preserving legacy fallback behavior for `<|endoftext|>` and `<|pad|>`.
4. Added regression coverage for the expanded default config and the updated export mapping rules.

Impacted files/modules:

1. `scripts/tokenizer_bpe/config.py`
2. `scripts/tokenizer_bpe/export.py`
3. `configs/tokenizer_bpe.yaml`
4. `tests/tokenizer_bpe/test_config.py`
5. `tests/tokenizer_bpe/test_export.py`
6. `README.md`
7. `docs/IMPLEMENTED_STEPS.md`
8. `docs/TOKENIZER_BPE.md`
9. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe/test_config.py tests/tokenizer_bpe/test_export.py` passed (`24 passed`).
2. `python -m pytest -q tests/tokenizer_bpe` passed (`62 passed`).

Documentation updates:

1. Updated `README.md` tokenizer default-policy notes.
2. Updated `docs/IMPLEMENTED_STEPS.md` Stage 03 summary for the expanded default inventory.
3. Updated `docs/TOKENIZER_BPE.md` default config and special-token export contract.

### 2026-03-18 (Fix Stage 1 special-token contamination in tokenizer BPE training)

Summary:

1. Fixed `scripts/tokenizer_bpe/stage1_count.py` so Stage 1 removes configured special-token literals after optional normalization and before regex pretokenization.
2. Added regression tests covering exact-line and inline special-token occurrences, plus longest-first literal matching for overlapping special tokens.
3. Updated tokenizer documentation to make the Stage 1 special-token exclusion contract explicit.
4. Tokenizers previously trained on corpora containing literal configured special-token text should be retrained, because the old Stage 1 counts could change merge ordering and final vocabulary.

Impacted files/modules:

1. `scripts/tokenizer_bpe/stage1_count.py`
2. `tests/tokenizer_bpe/test_stage1_count_unit.py`
3. `README.md`
4. `docs/TOKENIZER_BPE.md`
5. `docs/IMPLEMENTED_STEPS.md`
6. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe` passed (`60 passed`).

Documentation updates:

1. Updated `README.md` tokenizer training notes with the corrected special-token Stage 1 behavior.
2. Updated `docs/TOKENIZER_BPE.md` Stage 1 and special-token sections with the new exclusion order.
3. Updated `docs/IMPLEMENTED_STEPS.md` Stage 03 behavior summary.

### 2026-03-18 (Tokenizer cap override surface and default policy update)

Summary:

1. Raised tokenizer default inventory caps so `max_unique_pieces` and `max_word_types` both default to `2500000`.
2. Kept `max_bytes`, `max_lines`, and `max_merges` unlimited by default (`null` / `None`) and documented that policy explicitly.
3. Added canonical Stage 03 CLI overrides for `--max-unique-pieces` and `--max-word-types`.
4. Bound CLI overrides into effective config validation and `config_hash` generation.
5. Added regression tests for defaults, override precedence, hashing, and new validation bounds.

Impacted files/modules:

1. `scripts/tokenizer_bpe/config.py`
2. `scripts/03_train_tokenizer.py`
3. `configs/tokenizer_bpe.yaml`
4. `tests/tokenizer_bpe/test_config.py`
5. `README.md`
6. `CONFIG.md`
7. `docs/TOKENIZER_BPE.md`
8. `docs/IMPLEMENTED_STEPS.md`
9. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe/test_config.py` passed (`18 passed`).
2. `python -m pytest -q tests/tokenizer_bpe` passed (`57 passed`).

Documentation updates:

1. Updated `README.md` with the canonical CLI override example and tokenizer default-policy summary.
2. Updated `CONFIG.md` to describe unlimited defaults for `max_bytes`/`max_lines`/`max_merges` and `2500000` defaults for `max_unique_pieces`/`max_word_types`.
3. Updated `docs/TOKENIZER_BPE.md` with the new defaults, validation rules, and CLI override contract.
4. Updated `docs/IMPLEMENTED_STEPS.md` Stage 03 summary with the effective-config hash behavior and default policy.

### 2026-03-06 (Remove local OWT/TinyStories text and gzip training data files)

Summary:

1. Removed repository-local OWT/OpenWebText and TinyStories training data files in `.txt`/`.gz` format.
2. Deleted the tracked sample file `openwebtext_sample_3k_4k_tokens.txt`.
3. Deleted the local untracked file `owt_valid.txt`.

Impacted files/modules:

1. `openwebtext_sample_3k_4k_tokens.txt` (deleted)
2. `docs/CHANGELOG.md`
3. `docs/DIRECTORY_STRUCTURE.md`

Validation status:

1. `find . -type f \( -iname "*owt*.txt" -o -iname "*owt*.gz" -o -iname "*openwebtext*.txt" -o -iname "*openwebtext*.gz" -o -iname "*tinystories*.txt" -o -iname "*tinystories*.gz" \)` returns no files.

Documentation updates:

1. Added this changelog entry.
2. Refreshed `docs/DIRECTORY_STRUCTURE.md` snapshot date.

### 2026-03-04 (Ignore training/validation corpus text and gzip variants)

Summary:

1. Expanded `.gitignore` to ignore training/validation `.txt` and `.gz` corpus files across the repository.
2. Added explicit `owt_train*` and `owt_valid*` ignore patterns for both `.txt` and `.gz` variants.

Impacted files/modules:

1. `.gitignore`
2. `docs/CHANGELOG.md`

Validation status:

1. `git check-ignore -v data/raw/owt_train_shard_00.txt data/raw/owt_valid.txt.gz artifacts/tokenizer/train_chunk.txt artifacts/tokenizer/valid_chunk.gz` confirms matching ignore rules.
2. `git check-ignore -v sample.txt sample.gz` returns no matches.

Documentation updates:

1. Added this changelog entry.

### 2026-03-04 (Scope `.txt`/`.gz` ignores to training data only)

Summary:

1. Removed global `.txt` and `.gz` ignore patterns.
2. Added scoped ignore patterns for raw training data files only (`data/raw/*.txt`, `data/raw/*.gz`).

Impacted files/modules:

1. `.gitignore`
2. `docs/CHANGELOG.md`

Validation status:

1. `git check-ignore -v data/raw/example.txt data/raw/example.gz` confirms raw training data `.txt`/`.gz` files are ignored.
2. `git check-ignore -v sample.txt sample.gz` returns no matches, confirming non-training `.txt`/`.gz` files are not globally ignored.

Documentation updates:

1. Added this changelog entry.

### 2026-03-03 (OWT tokenizer training run configuration)

Summary:

1. Added a dedicated tokenizer config for training directly on `data/raw/owt_train.txt`.
2. Documented the manual train/resume commands for this large-corpus run in `README.md`.
3. Confirmed `owt_train.txt` is already in the canonical raw data location (`data/raw/owt_train.txt`), so no additional path change was required.

Impacted files/modules:

1. `configs/tokenizer_bpe_owt_train.yaml`
2. `README.md`
3. `docs/DIRECTORY_STRUCTURE.md`
4. `docs/CHANGELOG.md`

Validation status:

1. `python -c "import sys; sys.path.insert(0, 'scripts'); from tokenizer_bpe.config import load_config; cfg = load_config('configs/tokenizer_bpe_owt_train.yaml'); print(cfg['data']['input_paths'][0]); print(cfg['run']['output_dir'])"` passed (`data/raw/owt_train.txt`, `artifacts/tokenizer/runs_owt_train`).

Documentation updates:

1. Added this changelog entry.
2. Updated `README.md` with the OWT tokenizer run commands.
3. Updated `docs/DIRECTORY_STRUCTURE.md` with the new tracked config file.

### 2026-03-03 (Ignore local OWT raw training files)

Summary:

1. Added explicit ignore rules for local OpenWebText raw training files so they are not accidentally committed.

Impacted files/modules:

1. `.gitignore`
2. `docs/CHANGELOG.md`

Validation status:

1. `git check-ignore -v data/raw/owt_train.txt data/raw/owt_train.txt.gz` confirms both paths are ignored by `.gitignore`.

Documentation updates:

1. Added this changelog entry.

### 2026-03-03 (Tokenizer default checkpoint cadence tuning)

Summary:

1. Increased Stage 1 checkpoint batch interval default from 50 to 500 merged batches.
2. Increased Stage 3 snapshot merge interval default from 200 to 2000 merges.
3. Increased default periodic WAL fsync cadence from every 50 commits to every 250 commits.
4. Kept time-based checkpoint trigger unchanged at every 300 seconds.

Impacted files/modules:

1. `configs/tokenizer_bpe.yaml`
2. `scripts/tokenizer_bpe/config.py`
3. `docs/TOKENIZER_BPE.md`
4. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe/test_config.py` passed (`10 passed`).

Documentation updates:

1. Updated tokenizer default config snippet in `docs/TOKENIZER_BPE.md`.

### 2026-03-03 (Stage 3 resume/WAL integrity hardening)

Summary:

1. Added Stage 3 WAL metadata binding (`wal.meta.json`) so resume validates `config_hash` and `pattern_hash` before replay.
2. Hardened WAL replay with contiguous merge-index checks and strict replay-effect validation (replayed merges must update at least one word type).
3. Added fast-fail behavior when replaying WAL without compatible snapshot and without WAL metadata.
4. Added config validation for `bpe.max_merges` to reject negative values.
5. Added regression tests for WAL metadata mismatch/missing metadata/index gaps/no-effect replay and negative `max_merges`.

Impacted files/modules:

1. `scripts/tokenizer_bpe/stage3_train.py`
2. `scripts/tokenizer_bpe/config.py`
3. `tests/tokenizer_bpe/test_stage3_core.py`
4. `tests/tokenizer_bpe/test_config.py`
5. `docs/TOKENIZER_BPE.md`
6. `docs/IMPLEMENTED_STEPS.md`
7. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe/test_stage3_core.py tests/tokenizer_bpe/test_config.py` passed (`21 passed`).
2. `python -m pytest -q tests/tokenizer_bpe tests/tokenizer_runtime/test_runtime.py` passed (`51 passed`).

Documentation updates:

1. Updated `docs/TOKENIZER_BPE.md` resume/WAL safety contract and config validation list.
2. Updated `docs/IMPLEMENTED_STEPS.md` Stage 03 summary and resume contract with WAL metadata + replay checks.

### 2026-03-03 (Stage 3 pair-index hygiene + vocab floor contract clarification)

Summary:

1. Fixed Stage 3 incremental pair-index maintenance so candidate word indices are appended only for locally new pairs in each updated word.
2. Fixed stale candidate-list retention by removing `pair_to_words` entries when a pair's global count drops to non-positive.
3. Added explicit config contract language for the low-`vocab_size` floor edge case where zero merges can occur and exported vocab can exceed requested size due to base bytes plus specials.

Impacted files/modules:

1. `scripts/tokenizer_bpe/stage3_train.py`
2. `tests/tokenizer_bpe/test_stage3_core.py`
3. `CONFIG.md`
4. `docs/TOKENIZER_BPE.md`
5. `docs/IMPLEMENTED_STEPS.md`
6. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe/test_stage3_core.py tests/tokenizer_bpe/test_export.py tests/tokenizer_bpe/test_config.py` passed (`20 passed`).
2. `python -m pytest -q tests/tokenizer_bpe/test_stage3_recovery.py tests/tokenizer_bpe/test_train_tokenizer_resume.py` passed (`4 passed`).
3. `python -m pytest -q tests/tokenizer_bpe` passed (`44 passed`).

Documentation updates:

1. Updated `CONFIG.md` with the explicit `bpe.vocab_size` floor edge-case contract.
2. Updated `docs/TOKENIZER_BPE.md` Stage 3 behavior notes for append-light indexing and stale pair cleanup.
3. Updated `docs/IMPLEMENTED_STEPS.md` Stage 03 implementation summary to include pair-index hygiene and floor-edge behavior.

### 2026-02-26 (Tokenizer BPE robustness/scaling feedback implementation)

Summary:

1. Updated Stage 1 counting to stop streaming `min_piece_freq` pruning and keep deterministic top-K capping (`max_unique_pieces`) as the only streaming approximation knob.
2. Changed Stage 1 parallelism to allow out-of-order worker completion while applying results in deterministic `batch_id` order.
3. Refactored Stage 2/3 training state to compact integer arrays and switched Stage 3 pair keys from tuple `(a, b)` to packed integer `pair_id`.
4. Added Stage 3 pressure valves: periodic heap rebuild on stale-growth ratio and merged-pair candidate-list deletion.
5. Updated WAL durability defaults to PoC-friendly behavior with periodic fsync (`wal_fsync_every_commits`) and optional paranoid per-commit mode.
6. Updated tokenizer technical docs and checkpoint/config references to match new behavior.

Impacted files/modules:

1. `scripts/tokenizer_bpe/stage1_count.py`
2. `scripts/tokenizer_bpe/stage2_init.py`
3. `scripts/tokenizer_bpe/stage3_train.py`
4. `scripts/tokenizer_bpe/config.py`
5. `configs/tokenizer_bpe.yaml`
6. `tests/tokenizer_bpe/test_stage2_init.py`
7. `tests/tokenizer_bpe/test_stage3_core.py`
8. `CONFIG.md`
9. `CHECKPOINTING.md`
10. `docs/TOKENIZER_BPE.md`
11. `docs/IMPLEMENTED_STEPS.md`
12. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe/test_stage1_count_unit.py tests/tokenizer_bpe/test_stage2_init.py tests/tokenizer_bpe/test_stage3_core.py tests/tokenizer_bpe/test_stage3_recovery.py tests/tokenizer_bpe/test_config.py` passed (`22 passed`).
2. `python -m pytest -q tests/tokenizer_bpe` passed (`40 passed`).

Documentation updates:

1. Updated Stage 1/2/3 algorithm contracts and default config snippets in `docs/TOKENIZER_BPE.md`.
2. Updated durability semantics in `CHECKPOINTING.md`.
3. Updated tokenizer config field descriptions in `CONFIG.md`.
4. Updated Stage 03 implemented-behavior summary in `docs/IMPLEMENTED_STEPS.md`.

### 2026-02-25 (Tokenizer doc: core algorithm explainer)

Summary:

1. Added a new top-level educational section to `docs/TOKENIZER_BPE.md` that explains the full training flow for independent implementation.
2. Documented vocabulary initialization, Stage 1 pretokenization/counting, Stage 3 merge computation, special-token handling, and final exported artifacts.
3. Added implementation-oriented code snippets that map directly to the repository trainer/runtime architecture.

Impacted files/modules:

1. `docs/TOKENIZER_BPE.md`
2. `docs/CHANGELOG.md`

Validation status:

1. Documentation-only update; code behavior unchanged.

Documentation updates:

1. Expanded tokenizer reference with an educational yet implementation-precise overview near the top of the document.

### 2026-02-25 (Tokenizer reproducibility-spec clarification pass)

Summary:

1. Hardened tokenizer documentation with normative Stage 1 concurrency and progress semantics, including FIFO merge ordering and contiguous-prefix offset advancement.
2. Explicitly defined `.gz` offset domain and byte accounting semantics for Stage 1 resume/progress.
3. Added end-to-end normalization contract (training-time location and runtime non-normalization behavior).
4. Defined `config_hash` canonicalization exactly and added a normative example payload/hash pair.
5. Clarified Stage 3 initial pair-structure construction and tie-break domain as integer token IDs.
6. Expanded runtime tokenizer contract for piece initialization, merge-rank application, ID lookup semantics, and special-token handling.

Impacted files/modules:

1. `docs/TOKENIZER_BPE.md`
2. `CONFIG.md`
3. `CHECKPOINTING.md`
4. `docs/CHANGELOG.md`

Validation status:

1. Documentation-only update; code behavior unchanged.
2. Contracts were cross-checked against:
   - `scripts/tokenizer_bpe/stage1_count.py`
   - `scripts/tokenizer_bpe/config.py`
   - `scripts/tokenizer_bpe/stage3_train.py`
   - `src/llm_training/tokenizer/runtime.py`

Documentation updates:

1. Added normative algorithm semantics required for independent implementation equivalence.
2. Deferred non-essential performance/micro-policy clarifications (heap maintenance micro-optimizations and runtime piece-cache strategy) for separate review.

### 2026-02-22 (Canonical artifact-lineage pipeline implementation)

Summary:

1. Added canonical stage scripts `01..08` for corpus build, dedup, tokenizer training, corpus tokenization, sequence packing, pretraining, SFT, and evaluation.
2. Introduced shared infrastructure package under `src/llm_training/infra` for hashing, atomic I/O, run metadata/state/metrics, artifact manifests/registry, and resume gates.
3. Added runtime tokenizer package under `src/llm_training/tokenizer` with `ByteLevelBPETokenizer` API used by downstream stages.
4. Added new stage configs (`corpus`, `dedup`, `tokenize`, `pack`, `train`, `sft`, `eval`) and artifact registry contract (`artifacts/registry.jsonl` + per-artifact `artifact_manifest.json`).
5. Added unit/integration tests for infrastructure, tokenizer runtime API, and corpus->dedup->tokenize->pack pipeline flow.
6. Updated primary documentation set to reflect canonical stage flow and current status.

Impacted files/modules:

1. `src/llm_training/infra/*`
2. `src/llm_training/tokenizer/*`
3. `scripts/01_build_corpus.py`
4. `scripts/02_dedup_exact.py`
5. `scripts/03_train_tokenizer.py`
6. `scripts/04_tokenize_corpus.py`
7. `scripts/05_pack_sequences.py`
8. `scripts/06_pretrain.py`
9. `scripts/07_sft_lora.py`
10. `scripts/08_eval.py`
11. `scripts/_bootstrap.py`
12. `scripts/pipeline_common.py`
13. `configs/corpus.yaml`
14. `configs/dedup.yaml`
15. `configs/tokenize.yaml`
16. `configs/pack.yaml`
17. `configs/train.yaml`
18. `configs/sft.yaml`
19. `configs/eval.yaml`
20. `tests/conftest.py`
21. `tests/infra/test_atomic_io.py`
22. `tests/infra/test_hashing_manifest.py`
23. `tests/tokenizer_runtime/test_runtime.py`
24. `tests/pipeline/test_tokenize_pack_pipeline.py`
25. `README.md`
26. `docs/PROJECT_STATUS.md`
27. `docs/NEXT_STEPS.md`
28. `docs/IMPLEMENTED_STEPS.md`
29. `docs/TOKENIZER_BPE.md`
30. `docs/CHANGELOG.md`

Validation status:

1. `python -m compileall -q src scripts tests` passed.
2. `python -m pytest -q tests/infra tests/tokenizer_runtime` passed (`6 passed`).
3. `python -m pytest -q tests/pipeline/test_tokenize_pack_pipeline.py` passed (`1 passed`).
4. `python -m pytest -q` passed (`50 passed`).

Documentation updates:

1. Updated canonical pipeline and quick start commands in `README.md`.
2. Updated stage implementation references in `docs/IMPLEMENTED_STEPS.md`.
3. Updated status/gaps in `docs/PROJECT_STATUS.md`.
4. Updated roadmap in `docs/NEXT_STEPS.md`.
5. Updated tokenizer entrypoint/runtime references in `docs/TOKENIZER_BPE.md`.

### 2026-02-22 (Zone.Identifier cleanup utility hardening)

Summary:

1. Updated `scripts/cleanup_zone_identifier.py` to scan from the repository root by default.
2. Expanded Python virtual environment folder exclusion with common naming patterns and `pyvenv.cfg` detection.
3. Added targeted unit tests for Zone.Identifier discovery and virtualenv exclusion behavior.

Impacted files/modules:

1. `scripts/cleanup_zone_identifier.py`
2. `tests/test_cleanup_zone_identifier.py`
3. `README.md`
4. `docs/PROJECT_STATUS.md`
5. `docs/IMPLEMENTED_STEPS.md`
6. `docs/CHANGELOG.md`

Validation status:

1. `python -m unittest -q tests.test_cleanup_zone_identifier` passed (`Ran 3 tests ... OK`).
2. `python scripts/cleanup_zone_identifier.py --dry-run --root .` succeeded and reported matching files without deleting.

Documentation updates:

1. Added utility usage guidance to `README.md`.
2. Added implemented behavior details to `docs/IMPLEMENTED_STEPS.md`.
3. Recorded utility availability in `docs/PROJECT_STATUS.md`.

### 2026-02-21 (Tokenizer spec consolidation)

Summary:

1. Consolidated tokenizer technical specification content into `docs/TOKENIZER_BPE.md` and expanded it into a full rebuild guide.
2. Added detailed algorithm and operational coverage for pretokenization regexes, Stage 1 parallel counting, Stage 3 incremental merge updates, WAL recovery, and export/runtime contracts.
3. Removed `technical_spec_bpe_train_tokenizer.md` so tokenizer documentation now has a single official source.

Impacted files/modules:

1. `docs/TOKENIZER_BPE.md`
2. `technical_spec_bpe_train_tokenizer.md`
3. `README.md`
4. `docs/README.md`
5. `docs/IMPLEMENTED_STEPS.md`
6. `AGENTS.md`
7. `docs/CHANGELOG.md`

Validation status:

1. Documentation-only update; runtime tests not executed.

Documentation updates:

1. Replaced the previous tokenizer implementation summary with an implementation-grade official specification in `docs/TOKENIZER_BPE.md`.
2. Removed legacy technical-spec references from repository documentation.

### 2026-02-21 (Unit test dependency alignment)

Summary:

1. Added explicit unit-test dependencies to `requirements.txt` so pytest-based testing works after the standard project install.
2. Updated onboarding guidance to reflect that separate manual test dependency installation is no longer required.

Impacted files/modules:

1. `requirements.txt`
2. `README.md`
3. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe -m "not integration"` passed (`36 passed, 4 deselected`).

Documentation updates:

1. Updated test setup guidance in `README.md`.
2. Appended this change entry to `docs/CHANGELOG.md`.

### 2026-02-21

Summary:

1. Replaced tokenizer download script with local GPT-2 style UTF-8 byte-level BPE training pipeline.
2. Added tokenizer training modules and resumable WAL/snapshot mechanics.
3. Added documentation system layering and roadmap/status/workflow docs.

Impacted files/modules:

1. `scripts/02_train_tokenizer.py`
2. `scripts/tokenizer_bpe/*`
3. `configs/tokenizer_bpe.yaml`
4. `requirements.txt`
5. `README.md`
6. `CONFIG.md`
7. `CHECKPOINTING.md`
8. `docs/README.md`
9. `docs/PROJECT_STATUS.md`
10. `docs/NEXT_STEPS.md`
11. `docs/DEVELOPMENT_WORKFLOW.md`
12. `AGENTS.md`
13. `tests/tokenizer_bpe/*`

Validation status:

1. Tests not executed in this change set.

Documentation updates:

1. Added and updated docs listed above.

### 2026-02-21 (Documentation hardening pass)

Summary:

1. Aligned `docs/NEXT_STEPS.md` section headings to match `llm_training_overview.md` stage headings.
2. Added detailed step-level implementation documentation.
3. Added deep technical tokenizer implementation reference.
4. Added changelog operating structure for future updates.

Impacted files/modules:

1. `docs/NEXT_STEPS.md`
2. `docs/IMPLEMENTED_STEPS.md`
3. `docs/TOKENIZER_BPE.md`
4. `docs/README.md`
5. `docs/PROJECT_STATUS.md`
6. `docs/DEVELOPMENT_WORKFLOW.md`
7. `README.md`
8. `AGENTS.md`
9. `llm_training_overview.md`

Validation status:

1. Documentation changes only; no runtime validation executed.

Documentation updates:

1. Added/updated documents listed above.

### 2026-02-21 (Tokenizer test suite expansion)

Summary:

1. Migrated tokenizer tests to a pytest-based suite and fixed incorrect pretokenizer expectation around leading-space tokenization.
2. Added module-level tests for config, Stage 1 counting helpers, Stage 2 initialization, Stage 3 core behavior, export contracts, and runtime encode/decode checks.
3. Added deterministic integration tests for full tokenizer pipeline equivalence and resume/recovery convergence.
4. Added tokenizer fixture assets and shared test helpers for deterministic corpus/config setup.

Impacted files/modules:

1. `pytest.ini`
2. `tests/__init__.py`
3. `tests/tokenizer_bpe/__init__.py`
4. `tests/tokenizer_bpe/conftest.py`
5. `tests/tokenizer_bpe/helpers.py`
6. `tests/tokenizer_bpe/test_byte_unicode.py`
7. `tests/tokenizer_bpe/test_config.py`
8. `tests/tokenizer_bpe/test_export.py`
9. `tests/tokenizer_bpe/test_pretokenizer.py`
10. `tests/tokenizer_bpe/test_runtime_check.py`
11. `tests/tokenizer_bpe/test_stage1_count_unit.py`
12. `tests/tokenizer_bpe/test_stage2_init.py`
13. `tests/tokenizer_bpe/test_stage3_core.py`
14. `tests/tokenizer_bpe/test_stage3_recovery.py`
15. `tests/tokenizer_bpe/test_train_tokenizer_determinism.py`
16. `tests/tokenizer_bpe/test_train_tokenizer_resume.py`
17. `tests/fixtures/tokenizer_bpe/tiny_corpus.txt`
18. `tests/fixtures/tokenizer_bpe/sample.jsonl`
19. `README.md`
20. `docs/TOKENIZER_BPE.md`
21. `docs/IMPLEMENTED_STEPS.md`

Validation status:

1. `python -m compileall tests/tokenizer_bpe tests/fixtures/tokenizer_bpe` succeeded.
2. `python -m pytest -q tests/tokenizer_bpe` passed (`40 passed`).

Documentation updates:

1. Added tokenizer test execution commands and dependency guidance to `README.md`.
2. Expanded verification coverage section in `docs/TOKENIZER_BPE.md`.
3. Updated Step 02 testing details and known limitations in `docs/IMPLEMENTED_STEPS.md`.
