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
