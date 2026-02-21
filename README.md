# LLM Training Pipeline

This repository is a practical, versioned scaffold for building an end-to-end LLM training program.
It is intentionally laptop-runnable today and structured to scale to AWS-based distributed training and inference later.

## Project goals

1. Start from reproducible local workflows for data, tokenization, pretraining, SFT, and evaluation.
2. Keep interfaces stable so scale-up is mostly infrastructure swap, not project rewrite.
3. Build governance, provenance, and checkpoint discipline early, not as a retrofit.

## Guiding documents

- `README.md`: public entrypoint and quick start.
- `llm_training_overview.md`: north-star architecture and full program sequence.
- `docs/README.md`: documentation index and update policy.
- `docs/PROJECT_STATUS.md`: implemented status and current gaps.
- `docs/NEXT_STEPS.md`: stage-aligned implementation roadmap.
- `docs/IMPLEMENTED_STEPS.md`: detailed implementation docs for every built step.
- `docs/TOKENIZER_BPE.md`: detailed tokenizer architecture and behavior.
- `docs/DEVELOPMENT_WORKFLOW.md`: contributor workflow and testing/documentation expectations.
- `docs/CHANGELOG.md`: change history and release notes.
- `AGENTS.md`: operating guide for Codex and human contributors.

## What exists today

- `scripts/01_make_corpus.py`: creates local corpus files under `data/raw/`.
- `scripts/02_train_tokenizer.py`: trains a local GPT-2 style UTF-8 byte-level BPE tokenizer with resume support.
- `scripts/03_pretrain.py`: tiny GPT-2 style pretraining from local data.
- `scripts/04_sft_lora.py`: lightweight LoRA instruction tuning.
- `scripts/05_eval_generate.py`: basic generation smoke test.
- `configs/`: shared config files, including `configs/tokenizer_bpe.yaml`.
- `artifacts/`: tokenizer/model/eval outputs.

## Quick start (public users)

### 1) Clone and enter the repo

```bash
git clone <your-repo-url>
cd llm_training
```

### 2) Create a Python environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3) Run the minimal local pipeline

```bash
python scripts/01_make_corpus.py
python scripts/02_train_tokenizer.py --config configs/tokenizer_bpe.yaml
python scripts/03_pretrain.py
python scripts/04_sft_lora.py
python scripts/05_eval_generate.py
```

### 4) Resume tokenizer training after interruption (optional)

```bash
python scripts/02_train_tokenizer.py --config configs/tokenizer_bpe.yaml --resume --run-id <run_id>
```

### 5) Run tokenizer tests

Install test dependencies (manual, optional for runtime-only use):

```bash
python -m pip install pytest pytest-cov
```

Run the tokenizer suite:

```bash
python -m pytest -q tests/tokenizer_bpe
```

Run only fast unit tests (skip integration-marked tests):

```bash
python -m pytest -q tests/tokenizer_bpe -m "not integration"
```

Run outputs are written to `artifacts/`.

## Documentation system

The documentation system is split by intent:

- Entrypoint and onboarding: `README.md`
- Architecture and end-state: `llm_training_overview.md`
- Status and gaps: `docs/PROJECT_STATUS.md`
- Stage roadmap: `docs/NEXT_STEPS.md`
- Detailed implemented behavior: `docs/IMPLEMENTED_STEPS.md`
- Detailed tokenizer implementation: `docs/TOKENIZER_BPE.md`
- Contributor workflow and testing expectations: `docs/DEVELOPMENT_WORKFLOW.md`
- Change history: `docs/CHANGELOG.md`
- Repository policies and agent behavior: `AGENTS.md`
- Tokenizer reference details: `CONFIG.md`, `CHECKPOINTING.md`, `technical_spec_bpe_train_tokenizer.md`

When implementation changes behavior, update both:

1. the most specific affected document in `docs/`
2. this `README.md` if onboarding, commands, or expected outputs changed

## Scale-up intent

The local scripts are not the end-state. They are the proving ground for:

- strict artifact/version discipline
- deterministic and resumable training workflows
- testable stage boundaries
- clean transition to cloud orchestration and large-scale training/inference on AWS

For the full architecture, sequencing, and cloud rationale, follow `llm_training_overview.md`.
