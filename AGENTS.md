# AGENTS.md

## Scope

This repository is an LLM training pipeline scaffold and should remain a small, runnable foundation:

- `README.md` documents the project purpose and workflow
- `requirements.txt` tracks Python dependencies
- `scripts/` contains runnable pipeline scripts and utilities
- `configs/` contains minimal shared training configuration
- `data/` and `artifacts/` are scaffold folders for pipeline output

## Documentation system (mandatory)

Documentation is intentionally layered. Use the right document for the right purpose:

- `README.md`
  - Public entrypoint for cloning, setup, and local quick start.
  - Must stay high-level and newcomer-friendly.
- `llm_training_overview.md`
  - Guiding architecture document for the full program.
  - Treat this as the north-star sequencing and design reference.
- `docs/PROJECT_STATUS.md`
  - Current implementation status and known gaps.
- `docs/DIRECTORY_STRUCTURE.md`
  - Canonical repository directory structure snapshot (tracked files only).
- `docs/NEXT_STEPS.md`
  - Prioritized roadmap from current scaffold to cloud-scale system.
- `docs/DEVELOPMENT_WORKFLOW.md`
  - Coding/testing/documentation workflow expectations.
- `docs/IMPLEMENTED_STEPS.md`
  - Detailed reference for every implemented pipeline step.
- `docs/TOKENIZER_BPE.md`
  - Deep technical documentation for tokenizer training internals and contracts.
- `docs/CHANGELOG.md`
  - Chronological record of implementation and documentation updates.
- `docs/README.md`
  - Documentation index and update policy.

When code behavior changes, Codex and contributors must update documentation in the same change.
At minimum, update the most specific `docs/*` file and `README.md` when user-facing commands or onboarding steps change.
When a pipeline step changes, update `docs/IMPLEMENTED_STEPS.md` and append an entry to `docs/CHANGELOG.md`.

## Implementation policy (mandatory)

- Repository documentation must be updated after every change or newly implemented feature.
- `docs/DIRECTORY_STRUCTURE.md` must be updated whenever tracked directory structure changes, including:
  - adding, renaming, or removing tracked directories
  - adding, renaming, or removing tracked files
- Unit tests must be created for each new major code implementation (for example: RLHF framework additions, alternative tokenization processes, transformer architecture implementations, or similar major subsystems).

## User + Codex guidance

- Users: start with `README.md`, then follow `docs/NEXT_STEPS.md` for priorities.
- Codex: use `llm_training_overview.md` to align implementation decisions with long-term architecture.
- Both: use `AGENTS.md` for repository operating rules and policy constraints.
- Tokenizer-specific references remain:
  - `docs/TOKENIZER_BPE.md`
  - `CONFIG.md`
  - `CHECKPOINTING.md`

## Network policy (mandatory)

- **At session start, before any outbound network call, Codex must ask the user for approval.**
- When approval is requested, the domain whitelist must include:
  - `api.openai.com`
- No other outbound network domains should be assumed approved by default.
- If additional domains are required, get explicit user approval before proceeding.
- This applies to any operation that accesses external services (e.g., package downloads, API calls, web lookup).

## Repository conventions

- Use UTF-8 text files and keep output concise.
- Keep scripts Python-first (`.py`) and runnable from the repository root.
- Continue to protect generated artifacts and environment folders from accidental commits.
