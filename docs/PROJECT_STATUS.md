# Project Status

This status reflects the current scaffold implementation and aligns to the staged roadmap in `llm_training_overview.md`.

## Completed foundation

1. Repository scaffold and stage-oriented scripts are in place.
2. Local corpus generation path exists (`scripts/01_make_corpus.py`).
3. Local tokenizer training is implemented with a GPT-2 style UTF-8 byte-level BPE pipeline:
   - regex-based pretokenization
   - deterministic merge learning
   - checkpoint + WAL resume mechanics
   - export artifacts under `artifacts/tokenizer/gpt2/`
4. Tiny local pretraining path exists (`scripts/03_pretrain.py`).
5. LoRA-based instruction tuning path exists (`scripts/04_sft_lora.py`).
6. Generation smoke evaluation exists (`scripts/05_eval_generate.py`).
7. Repository cleanup utility exists for `Zone.Identifier` files (`scripts/cleanup_zone_identifier.py`), with virtual environment directory exclusion.

## Current maturity level

This repo is at a practical local/laptop proof stage:

- Good for validating stage boundaries and artifact flow.
- Good for iteration on tokenizer/training mechanics.
- Not yet production-grade for compliance, large-scale ETL, distributed training, or serving SLAs.

## Key gaps versus north star

1. Governance:
   - Formal model spec, risk register, and promotion gates need to be codified.
2. Data:
   - Provenance metadata, licensing enforcement, dedup/contamination pipeline, and quality scoring are not fully implemented.
3. Dataset versioning:
   - Mixture-as-code and release-grade dataset changelog/versioning are incomplete.
4. Training:
   - Distributed scaling strategy and resilient multi-node orchestration are not implemented.
5. Evaluation:
   - Capability/safety regression harness is minimal and needs formalized suites.
6. Inference:
   - Compression, deployment topology, and production monitoring pipelines are not implemented.

## What is stable right now

1. Stage naming and script order.
2. Artifact directory conventions under `artifacts/`.
3. The principle of deterministic, resumable tokenizer training.
4. Use of `llm_training_overview.md` as architecture guide and sequencing reference.

## Detailed implementation references

1. Step-by-step details for implemented pipeline stages: `docs/IMPLEMENTED_STEPS.md`.
2. Tokenizer implementation internals and contracts: `docs/TOKENIZER_BPE.md`.
3. Tokenizer config and recovery specifics: `CONFIG.md` and `CHECKPOINTING.md`.
