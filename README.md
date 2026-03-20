# LLM Training Pipeline

This repository is a practical, versioned scaffold for building an end-to-end LLM training program.
It remains laptop-runnable and now includes deterministic artifact-ID based stages from corpus building through evaluation.

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

## Canonical pipeline (current)

1. `scripts/01_build_corpus.py`: raw text/jsonl -> canonical document corpus artifact.
2. `scripts/02_dedup_exact.py`: deterministic exact deduplication over corpus docs.
3. `scripts/03_train_tokenizer.py`: deterministic resumable GPT-2 style byte-level BPE training + published tokenizer artifact.
4. `scripts/04_tokenize_corpus.py`: corpus docs -> deterministic token shards with per-doc offsets.
5. `scripts/05_pack_sequences.py`: token shards -> fixed-length train/val packed blocks.
6. `scripts/06_pretrain.py`: tiny GPT-style pretraining from packed artifacts with checkpoint resume.
7. `scripts/07_sft_lora.py`: lightweight LoRA SFT over a published base model artifact.
8. `scripts/08_eval.py`: perplexity/sample evaluation producing versioned eval artifacts.

Shared contracts now applied across new stages:

1. run directory metadata (`run_meta.json`, `state.json`, `metrics.jsonl`)
2. artifact manifests (`artifact_manifest.json`)
3. append-only artifact registry (`artifacts/registry.jsonl`)
4. deterministic stage IDs based on config + inputs (unless overridden)

## Legacy scaffold scripts

The original scaffold scripts still exist and can be used for ad-hoc local experiments:

- `scripts/01_make_corpus.py`
- `scripts/02_train_tokenizer.py`
- `scripts/03_pretrain.py`
- `scripts/04_sft_lora.py`
- `scripts/05_eval_generate.py`

Use the canonical `01..08` scripts for reproducible artifact-lineage workflows.

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

### 3) (Optional) Seed tiny local raw text

```bash
python scripts/01_make_corpus.py
```

This creates `data/raw/{train,validation,test}.txt` and is useful for laptop smoke runs.

### 4) Run the canonical staged pipeline

```bash
python scripts/01_build_corpus.py --config configs/corpus.yaml
python scripts/02_dedup_exact.py --config configs/dedup.yaml
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe.yaml
python scripts/04_tokenize_corpus.py --config configs/tokenize.yaml
python scripts/05_pack_sequences.py --config configs/pack.yaml
python scripts/06_pretrain.py --config configs/train.yaml
python scripts/07_sft_lora.py --config configs/sft.yaml
python scripts/08_eval.py --config configs/eval.yaml
```

Tokenizer cap overrides can be set directly on the canonical stage entrypoint:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe.yaml --max-unique-pieces 3500000 --max-word-types 3000000
```

Tokenizer default policy:

- `max_bytes` and `max_lines` are unlimited unless explicitly set.
- `max_merges` is unlimited as an explicit cap; when unset, target merges are derived from `vocab_size`.
- `max_unique_pieces` defaults to `3500000`, `max_word_types` defaults to `3000000`, and `vocab_size` defaults to `64000`.
- Stage 1 periodic piece-count capping now stays configurable through `checkpointing.stage1_cap_every_batches` and `checkpointing.stage1_cap_start_lines`, with an optional safety cap at `max_unique_pieces * checkpointing.stage1_cap_safety_factor`.
- the default `special_tokens.tokens` inventory includes end-of-text, BOS/EOS/PAD/UNK, chat-role, message-boundary, FIM, and metadata/control markers as listed in `configs/tokenizer_bpe.yaml`
- configured `special_tokens.tokens` are stripped from Stage 1 training text before regex pretokenization, so literal special-token text does not affect learned merges

### 5) Resume tokenizer training after interruption (optional)

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe.yaml --resume --run-id <run_id>
```

### 6) Train tokenizer on `owt_train.txt` (optional large run)

Place the corpus at `data/raw/owt_train.txt` and use the dedicated run config:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_owt_train.yaml --run-id owt_bpe_64k_<date_tag>
```

Resume that exact run:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_owt_train.yaml --resume --run-id owt_bpe_64k_<date_tag>
```

For the `owt_train.txt` run wired to the Markdown/LaTeX-aware pretokenizer path (`md_latex_fast_v1`), use the dedicated config:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_owt_train_md_latex.yaml --run-id owt_md_latex_bpe_64k_<date_tag>
```

Resume that exact run:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_owt_train_md_latex.yaml --resume --run-id owt_md_latex_bpe_64k_<date_tag>
```

### 7) Train tokenizer on TinyStories (optional large run)

If the local corpus is present at `data/raw/TinyStoriesV2-GPT4-train.txt`, use the dedicated TinyStories tokenizer config:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_tinystories_32k_train.yaml --run-id tinystories_bpe_64k_<date_tag>
```

Resume that exact run:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_tinystories_32k_train.yaml --resume --run-id tinystories_bpe_64k_<date_tag>
```

For the TinyStories run wired to the Markdown/LaTeX-aware pretokenizer path (`md_latex_fast_v1`), use the dedicated config:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_tinystories_md_latex_train.yaml --run-id tinystories_md_latex_bpe_64k_<date_tag>
```

Resume that exact run:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_tinystories_md_latex_train.yaml --resume --run-id tinystories_md_latex_bpe_64k_<date_tag>
```

### 8) Train tokenizer on `proof_pile.txt` (optional large run)

If the local corpus is present at `data/raw/proof_pile.txt`, use the dedicated run config:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_proof_pile_train.yaml --run-id proof_pile_bpe_64k_<date_tag>
```

Resume that exact run:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_proof_pile_train.yaml --resume --run-id proof_pile_bpe_64k_<date_tag>
```

### 9) Run the Markdown/LaTeX tokenizer experiment config (optional)

The versioned alias `md_latex_fast_v1` is available for A/B runs through the dedicated experiment config. It keeps `gpt2_fast` as the repository default while making local LaTeX commands, `_`/`^` affixes, Markdown headings, and task boxes tokenizable as smaller units.

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_md_latex_experiment.yaml --run-id md_latex_bpe_<date_tag>
```

### 10) Run tests

Run all tests:

```bash
python -m pytest -q
```

Run tokenizer-focused tests only:

```bash
python -m pytest -q tests/tokenizer_bpe
```

Run fast tokenizer unit tests only (skip integration-marked tokenizer tests):

```bash
python -m pytest -q tests/tokenizer_bpe -m "not integration"
```

### 11) Remove `Zone.Identifier` files (optional)

```bash
python scripts/cleanup_zone_identifier.py --dry-run
python scripts/cleanup_zone_identifier.py
```

By default this scans from the repository root and skips Python virtual environment directories.

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
- Tokenizer reference details: `docs/TOKENIZER_BPE.md`, `CONFIG.md`, `CHECKPOINTING.md`

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
