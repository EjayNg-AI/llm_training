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
