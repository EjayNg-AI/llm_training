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

### 2026-02-27 (OWT tokenizer input path correction)

Summary:

1. Updated OpenWebText tokenizer run configs to target `data/raw/owt_train.txt` instead of `data/raw/owt_train.txt.gz`.
2. Aligned OWT config input paths with the repository's documented OWT setup flow in `README.md`.

Impacted files/modules:

1. `configs/tokenizer_bpe_owt_32k.yaml`
2. `configs/tokenizer_bpe_owt_32k_probe_10gb.yaml`
3. `docs/CHANGELOG.md`

Validation status:

1. `rg -n "owt_train\\.txt(\\.gz)?" configs/tokenizer_bpe_owt_32k*.yaml` confirms both configs now point to `.txt`.

Documentation updates:

1. Added this changelog entry documenting the OWT input-path correction.

### 2026-02-27 (Tokenizer Stage 03 scaling telemetry, checkpoint instrumentation, and report generation)

Summary:

1. Expanded Stage 03 tokenizer runtime telemetry from duration-only to full Stage 1/2/3 scaling metrics and environment/config snapshots.
2. Reintroduced Stage 3 checkpoint instrumentation with configurable WAL/snapshot behavior and measured overhead timing.
3. Added structured per-run metrics output `run_statistics.json` and auto-generated canonical markdown report `docs/data_collection_report.md`.
4. Added A/B tokenizer comparison utility (`scripts/09_compare_tokenizer_ab.py`) for merge-overlap and held-out tokenization efficiency checks.
5. Updated Stage 03 integration tests and added new tests for Stage 1 metrics, report generation, and A/B metrics attachment.
6. Added a dedicated 10GB probe config and a root markdown runbook for manual tokenizer-loop execution commands.

Impacted files/modules:

1. `scripts/03_train_tokenizer.py`
2. `scripts/02_train_tokenizer.py`
3. `scripts/09_compare_tokenizer_ab.py`
4. `scripts/tokenizer_bpe/config.py`
5. `scripts/tokenizer_bpe/stage1_count.py`
6. `scripts/tokenizer_bpe/stage2_init.py`
7. `scripts/tokenizer_bpe/stage3_train.py`
8. `scripts/tokenizer_bpe/telemetry.py`
9. `scripts/tokenizer_bpe/report_data_collection.py`
10. `scripts/tokenizer_bpe/ab_compare.py`
11. `configs/tokenizer_bpe.yaml`
12. `configs/tokenizer_bpe_owt_32k.yaml`
13. `configs/tokenizer_bpe_owt_32k_probe_10gb.yaml`
14. `tests/tokenizer_bpe/helpers.py`
15. `tests/tokenizer_bpe/test_config.py`
16. `tests/tokenizer_bpe/test_stage03_minimal_outputs.py`
17. `tests/tokenizer_bpe/test_stage2_init.py`
18. `tests/tokenizer_bpe/test_stage3_core.py`
19. `tests/tokenizer_bpe/test_stage1_metrics.py`
20. `tests/tokenizer_bpe/test_report_data_collection.py`
21. `tests/tokenizer_bpe/test_ab_compare.py`
22. `README.md`
23. `docs/TOKENIZER_BPE.md`
24. `docs/IMPLEMENTED_STEPS.md`
25. `docs/PROJECT_STATUS.md`
26. `docs/README.md`
27. `docs/NEXT_STEPS.md`
28. `docs/DIRECTORY_STRUCTURE.md`
29. `CONFIG.md`
30. `CHECKPOINTING.md`
31. `docs/data_collection_report.md`
32. `manual_tokenizer_training_commands.md`
33. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe/test_config.py tests/tokenizer_bpe/test_stage1_metrics.py tests/tokenizer_bpe/test_stage2_init.py tests/tokenizer_bpe/test_stage3_core.py tests/tokenizer_bpe/test_report_data_collection.py tests/tokenizer_bpe/test_stage03_minimal_outputs.py tests/tokenizer_bpe/test_ab_compare.py` passed (`21 passed`).
2. `python -m pytest -q tests/tokenizer_bpe` passed (`41 passed`).

Documentation updates:

1. Updated tokenizer technical contract and outputs in `docs/TOKENIZER_BPE.md`.
2. Updated Stage 03 implemented behavior and run outputs in `docs/IMPLEMENTED_STEPS.md`.
3. Updated config/checkpoint references in `CONFIG.md` and `CHECKPOINTING.md`.
4. Added canonical report file and documentation index references.

### 2026-02-27 (Tokenizer Stage 03 checkpoint/memory telemetry removal + minimal run artifacts)

Summary:

1. Removed tokenizer checkpoint engineering from Stage 03:
   - Stage 1 persisted checkpoints removed
   - Stage 3 WAL/snapshot recovery removed
   - Stage 03 resume mode removed
2. Removed tokenizer memory monitoring.
3. Kept duration reporting and simplified `training_telemetry.json` to timestamp + elapsed fields only.
4. Removed non-essential Stage 03 intermediate run artifacts:
   - run metadata/state/metrics/log files
   - run-local export manifest mirror
5. Added Stage 03 integration coverage for minimal run outputs and duration telemetry schema.

Impacted files/modules:

1. `scripts/03_train_tokenizer.py`
2. `scripts/tokenizer_bpe/stage1_count.py`
3. `scripts/tokenizer_bpe/stage3_train.py`
4. `scripts/tokenizer_bpe/export.py`
5. `scripts/tokenizer_bpe/config.py`
6. `configs/tokenizer_bpe.yaml`
7. `configs/tokenizer_bpe_owt_32k.yaml`
8. `tests/tokenizer_bpe/helpers.py`
9. `tests/tokenizer_bpe/test_stage03_minimal_outputs.py`
10. `tests/tokenizer_bpe/test_stage1_count_unit.py`
11. `tests/tokenizer_bpe/test_stage3_core.py`
12. `tests/tokenizer_bpe/test_export.py`
13. `tests/tokenizer_bpe/test_train_tokenizer_resume.py` (removed)
14. `tests/tokenizer_bpe/test_stage3_recovery.py` (removed)
15. `tests/tokenizer_bpe/test_config.py`
16. `scripts/02_train_tokenizer.py`
17. `README.md`
18. `docs/TOKENIZER_BPE.md`
19. `docs/IMPLEMENTED_STEPS.md`
20. `docs/README.md`
21. `CONFIG.md`
22. `CHECKPOINTING.md`
23. `docs/DIRECTORY_STRUCTURE.md`
24. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe` passed (`36 passed`).

Documentation updates:

1. Updated tokenizer docs to reflect no-resume/no-checkpoint workflow.
2. Updated Stage 03 behavior summary and runtime commands.
3. Updated config/checkpoint reference docs.

### 2026-02-26 (Tokenizer training telemetry + OpenWebText 32k config)

Summary:

1. Added lightweight Stage 03 runtime telemetry that records full-run start/end timestamps, elapsed seconds, and approximate peak process memory usage.
2. Emitted telemetry to run-local `training_telemetry.json` without changing exported deterministic tokenizer artifact payloads.
3. Added a dedicated OpenWebText tokenizer config targeting vocab size `32000`.
4. Moved local OpenWebText training text into `data/raw/owt_train.txt` for canonical tokenizer input-path usage.
5. Added unit tests for telemetry helpers and fallback behavior.

Impacted files/modules:

1. `scripts/03_train_tokenizer.py`
2. `scripts/tokenizer_bpe/telemetry.py`
3. `configs/tokenizer_bpe_owt_32k.yaml`
4. `tests/tokenizer_bpe/test_telemetry.py`
5. `README.md`
6. `docs/TOKENIZER_BPE.md`
7. `docs/IMPLEMENTED_STEPS.md`
8. `docs/DIRECTORY_STRUCTURE.md`
9. `docs/CHANGELOG.md`

Validation status:

1. `python -m pytest -q tests/tokenizer_bpe/test_telemetry.py tests/tokenizer_bpe/test_stage3_core.py tests/tokenizer_bpe/test_export.py` passed (`13 passed`).
2. `python -m pytest -q tests/tokenizer_bpe/test_train_tokenizer_resume.py` passed (`2 passed`).

Documentation updates:

1. Added OpenWebText 32k tokenizer command example to `README.md`.
2. Documented `training_telemetry.json` contract in `docs/TOKENIZER_BPE.md`.
3. Updated Stage 03 behavior summary in `docs/IMPLEMENTED_STEPS.md`.
4. Updated tracked structure snapshot for new config in `docs/DIRECTORY_STRUCTURE.md`.

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
