# AGENTS.md

## Scope

This repository is an LLM training pipeline scaffold and should remain a small, runnable foundation:

- `README.md` documents the project purpose and workflow
- `requirements.txt` tracks Python dependencies
- `scripts/` contains runnable pipeline scripts and utilities
- `configs/` contains minimal shared training configuration
- `data/` and `artifacts/` are scaffold folders for pipeline output

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

