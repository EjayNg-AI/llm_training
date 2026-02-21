# Development Workflow

This workflow applies to both human contributors and Codex working in this repository.

## Working principles

1. Preserve deterministic behavior where possible.
2. Prefer small, stage-scoped changes over large rewrites.
3. Keep interfaces stable between local and cloud-intended paths.
4. Treat `llm_training_overview.md` as architecture guidance and sequencing truth.

## Coding expectations

1. Keep scripts runnable from repository root.
2. Use UTF-8 text files and concise logs.
3. Avoid committing generated artifacts and environment directories.
4. Keep configuration in `configs/` and avoid hidden constants in scripts.

## Testing expectations

1. Add or update tests when behavior changes.
2. Prefer deterministic tests with fixed seeds and fixed fixtures.
3. Validate stage-level behavior before integrating cross-stage changes.
4. For tokenizer changes, include:
   - determinism checks
   - resume/recovery checks
   - artifact compatibility checks

## Documentation expectations

When a change lands:

1. Update detailed docs in `docs/` for behavior/roadmap impact.
2. Update `README.md` when onboarding, setup, or script usage changes.
3. Update `docs/IMPLEMENTED_STEPS.md` when any implemented step behavior changes.
4. Append an entry to `docs/CHANGELOG.md` for notable changes.
5. Update `AGENTS.md` if contributor/agent policy changes.
6. Ensure links remain valid and docs are consistent with current scripts/configs.

## Pull request checklist

1. What changed and why.
2. How to run and verify.
3. Risks, edge cases, and rollback approach.
4. Docs updated (`README.md`, `docs/*`, `AGENTS.md` as applicable).
