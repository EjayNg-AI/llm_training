# Documentation Index

This directory holds implementation-level documentation for the repository.
`llm_training_overview.md` remains the guiding architecture document for the entire program.

## Document map

- `docs/PROJECT_STATUS.md`
  - Current implementation status, completed milestones, and known gaps.
- `docs/NEXT_STEPS.md`
  - Stage-by-stage execution roadmap using the same stage headings as `llm_training_overview.md`.
- `docs/DEVELOPMENT_WORKFLOW.md`
  - Coding, testing, and contribution workflow for humans and agents.
- `docs/IMPLEMENTED_STEPS.md`
  - Detailed implementation-level documentation for each completed scaffold step.
- `docs/TOKENIZER_BPE.md`
  - Deep technical documentation for the local GPT-2 style byte-level BPE tokenizer trainer.
- `docs/CHANGELOG.md`
  - Repository change log with summary, impact, validation status, and doc updates.

Related docs outside `docs/`:

- `README.md`: public onboarding and quick start.
- `AGENTS.md`: operating rules for Codex and repository contributors.
- `CONFIG.md`: tokenizer config reference.
- `CHECKPOINTING.md`: tokenizer checkpoint/WAL recovery model.
- `technical_spec_bpe_train_tokenizer.md`: byte-level BPE trainer specification.

## Update policy

When code changes:

1. Update the most specific affected document in `docs/`.
2. Update `README.md` if setup, commands, or onboarding behavior changed.
3. Update `docs/IMPLEMENTED_STEPS.md` when implemented stage behavior changes.
4. Append notable changes to `docs/CHANGELOG.md`.
5. Update `AGENTS.md` only when repository policies or agent/user workflow changed.
6. Keep `llm_training_overview.md` as the north-star architectural reference unless the program strategy itself changes.
