# LLM Training Pipeline

This repository is a starter implementation for an **LLM training program** based on
`llm_training_overview.md`.  
The intent is to preserve the same stages you need at scale while remaining runnable on a single machine.

## Project goal

Build a disciplined, repeatable pipeline that can progress from:

- raw text ingestion and cleaning
- tokenization and pretraining
- lightweight instruction tuning
- basic evaluation
- controlled scale-up to multi-node AWS training

The key design principle is to keep interfaces stable so moving from laptop workflows to
SageMaker/EKS/ParallelCluster/HyperPod is mostly an infrastructure swap, not a project rewrite.

## What this repo contains

- `llm_training_overview.md`: source of truth for pipeline stages and design decisions
- `requirements.txt`: Python dependencies
- `scripts/`:
  - `01_make_corpus.py`
  - `02_train_tokenizer.py`
  - `03_pretrain.py`
  - `04_sft_lora.py`
  - `05_eval_generate.py`
- `configs/` (optional): place shared experiment configs
- `data/`:
  - `raw/` and `processed/`
- `artifacts/`:
  - `tokenizer/`
  - `models/`
  - `eval/`

## Governance and operational guardrails

Before training anything, define:

- model spec (domains, context length, safety boundaries, chat format)
- data policy (licensing, PII handling, retention, provenance)
- risk register and eval gates
- artifact/version policy for datasets, tokenizers, checkpoints, and eval outputs

This is required to avoid legal, reproducibility, and safety risks later in the pipeline.

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run the steps below in order.

## Minimal laptop pipeline

### 1) Create corpus

Run:

```bash
python scripts/01_make_corpus.py
```

This downloads a small corpus and writes tokenizable text to `data/raw/`.

### 2) Pin a tokenizer

Run:

```bash
python scripts/02_train_tokenizer.py
```

This saves a tokenizer artifact under `artifacts/tokenizer/gpt2/`.

### 3) Tiny pretrain

Run:

```bash
python scripts/03_pretrain.py
```

Produces a tiny GPT-2 style checkpoint in:

- `artifacts/models/tiny-gpt2-from-scratch/`

If you run without CUDA, set `fp16=False` in `scripts/03_pretrain.py`.

### 4) Minimal SFT with LoRA

Run:

```bash
python scripts/04_sft_lora.py
```

This fine-tunes the pretrained checkpoint with a parameter-efficient adapter and saves
`artifacts/models/tiny-gpt2-sft-lora/`.

### 5) Quick smoke test

Run:

```bash
python scripts/05_eval_generate.py
```

Generates a short response from a prompt in `scripts/05_eval_generate.py`.

## Mapping to the full "North Star"

Each stage in this repo maps directly to the larger AWS-oriented program described in
`llm_training_overview.md`:

- `data/raw` + `data/processed` -> S3 data lake (`raw/`, `clean/`, partitioned by metadata)
- local scripts -> distributed Spark/EMR/Glue/Bath ETL jobs
- JSONL/shards -> streaming dataset shards in S3/FSx
- tiny local model -> distributed training with FSDP/ZeRO/tensor parallel/pipeline parallel on AWS
- local checkpoints -> durable S3-backed checkpoint strategy
- local eval output -> versioned eval artifacts tied to dataset + tokenizer + model hashes

## Planned maturity path

- v0: governance + laptop pipeline
- v1: dataset versioning, dedup/contamination checks, tokenizer versioning
- v2: cluster scheduling, checkpointing, evaluation gates
- v3: advanced post-training (DPO/RLAIF/RLHF) and serving optimizations (quantization/distillation/inference tuning)

## FAQ

- **Why this repo is small?**  
  It is intentionally minimal so you can validate the full sequence of stages before adding operational complexity.
- **Can this run at scale?**  
  Yes, by keeping interfaces stable and swapping compute/storage layers as described in the guide.

## Contributing

- Keep interfaces stable between laptop and cloud paths.
- Track package dependencies when adding training, data, or AWS integration code.
- Extend scripts in small increments and log dataset/version changes with notes in commit messages.
