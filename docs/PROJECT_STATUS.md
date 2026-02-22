# Project Status

This status reflects the current scaffold implementation and aligns to the staged roadmap in `llm_training_overview.md`.

## Completed foundation

1. Repository scaffold and stage-oriented scripts are in place.
2. Canonical artifact-lineage pipeline stages are implemented:
   - `scripts/01_build_corpus.py`
   - `scripts/02_dedup_exact.py`
   - `scripts/03_train_tokenizer.py`
   - `scripts/04_tokenize_corpus.py`
   - `scripts/05_pack_sequences.py`
   - `scripts/06_pretrain.py`
   - `scripts/07_sft_lora.py`
   - `scripts/08_eval.py`
3. Shared run/infra package exists under `src/llm_training/infra`:
   - deterministic config/input hashing
   - atomic output helpers
   - run metadata/state/metrics contract
   - artifact manifest + registry publishing
   - resume gate helpers
4. Tokenizer runtime library exists under `src/llm_training/tokenizer` with `ByteLevelBPETokenizer`.
5. Legacy scaffold scripts remain available for ad-hoc local use.
6. Repository cleanup utility exists for `Zone.Identifier` files (`scripts/cleanup_zone_identifier.py`), with virtual environment directory exclusion.

## Current maturity level

This repo is now a stronger local/laptop engineering scaffold:

- Deterministic stage outputs and lineage are enforced via artifact IDs and manifests.
- Corpus -> dedup -> tokenization -> packing -> train -> eval stage boundaries are explicit and runnable.
- Resume/checkpoint rigor has expanded beyond tokenizer training into stage infrastructure and pretraining runner.
- Still not production-grade for large-scale compliance ETL, distributed cluster orchestration, or serving SLAs.

## Key gaps versus north star

1. Governance:
   - Formal model spec, risk register, and promotion gates still need codified policy documents and enforcement hooks.
2. Data:
   - Near-dedup, contamination denylist checks, and richer provenance/license enforcement are still incomplete.
3. Dataset versioning:
   - Mixture-as-code and dataset release management are not yet fully implemented.
4. Training:
   - Distributed multi-node strategy (FSDP/ZeRO/etc.) is not implemented.
5. Evaluation:
   - Capability/safety regression suites and release thresholds remain minimal.
6. Inference/deployment:
   - Compression, deployment topology, and production monitoring pipelines are not implemented.

## What is stable right now

1. Canonical stage naming and sequence (`01..08` scripts).
2. Artifact directory conventions and append-only registry under `artifacts/`.
3. Deterministic, resumable tokenizer training behavior.
4. Shared run metadata/state/metrics and manifest contract for new pipeline stages.
5. Use of `llm_training_overview.md` as architecture guide and sequencing reference.

## Detailed implementation references

1. Step-by-step details for implemented pipeline stages: `docs/IMPLEMENTED_STEPS.md`.
2. Tokenizer implementation internals and contracts: `docs/TOKENIZER_BPE.md`.
3. Tokenizer config and recovery specifics: `CONFIG.md` and `CHECKPOINTING.md`.
