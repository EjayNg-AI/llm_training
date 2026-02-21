# Next Steps (Aligned to `llm_training_overview.md`)

This roadmap uses the same stage titles as `llm_training_overview.md` so planning and execution stay synchronized.

## 0) Program governance, scope, and guardrails

Current status:

1. High-level governance intent exists in overview docs.
2. No formal repository-level policy artifact set is finalized.

Next actions:

1. Add `docs/GOVERNANCE_MODEL_SPEC.md` with domain, refusal, context, tool-use boundaries.
2. Add `docs/DATA_POLICY.md` with licensing, PII, retention, provenance rules.
3. Define release gates and risk register in `docs/RELEASE_GATES.md`.

Definition of done:

1. Policies are versioned and referenced by training/eval scripts.
2. Promotion of model artifacts depends on documented gates.

## 1) Data acquisition + provenance capture

Current status:

1. Local corpus creation exists for scaffold execution.
2. Source and license lineage is not yet captured in structured manifests.

Next actions:

1. Define corpus record schema (`source`, `license`, `hash`, `language`, `crawl_date`).
2. Emit acquisition manifest files under `artifacts/data_manifests/`.
3. Add provenance validation checks during ingestion.

Definition of done:

1. Every training text shard has machine-readable provenance metadata.

## 2) Data cleaning, normalization, and aggressive filtering

Current status:

1. Minimal text cleaning exists in local corpus script.
2. No policy-grade cleaning/filtering stages yet.

Next actions:

1. Implement dedicated `scripts/data_clean.py` stage.
2. Add configurable normalization, boilerplate removal, and quality filters.
3. Add PII and toxicity tagging hooks.

Definition of done:

1. Cleaned dataset is reproducible and policy-checkable from raw inputs.

## 3) Deduplication (exact + near-duplicate) and contamination control

Current status:

1. Not implemented.

Next actions:

1. Add exact dedup pipeline with content hashes.
2. Add near-dedup clustering stage.
3. Add benchmark contamination denylist checks.

Definition of done:

1. Dedup and contamination reports are generated per dataset version.

## 4) Dataset versioning + mixture as code

Current status:

1. Scripted flow exists but dataset versioning contracts are incomplete.

Next actions:

1. Add dataset manifest version format (`dataset_id`, source versions, cleaning config, tokenizer version).
2. Add mixture config files in `configs/dataset_mixtures/`.
3. Add changelog entries when dataset mixtures change.

Definition of done:

1. Dataset release versions are reproducible from config + manifests.

## 5) Sharding and streaming-ready data formats

Current status:

1. Text files are used for local runs.
2. Streaming-scale shard formats are not implemented.

Next actions:

1. Implement shard builder for tokenized datasets.
2. Add local streaming dataloader compatibility checks.
3. Document shard schema and partition policy.

Definition of done:

1. Training can consume dataset shards without full in-memory loading.

## 6) Tokenizer design + training (one-way door)

Current status:

1. Implemented local GPT-2 style UTF-8 byte-level BPE trainer:
   - regex pretokenization (`gpt2_fast`, `gpt2_default`)
   - Stage 1 multiprocessing piece counting with checkpoint progress
   - Stage 3 WAL + snapshot resumability
   - deterministic merge/export behavior
2. Tokenizer docs exist in `CONFIG.md`, `CHECKPOINTING.md`, and `docs/TOKENIZER_BPE.md`.

Next actions:

1. Add full integration determinism tests in CI.
2. Add tokenizer artifact compatibility matrix for downstream scripts.
3. Freeze tokenizer versioning policy for future model families.

Definition of done:

1. Tokenizer training, resume, export, and compatibility checks are enforced in automated tests.

## 7) Architecture and scaling plan

Current status:

1. Tiny GPT-2 style local pretraining path is implemented.
2. Parameter/context scaling strategy is not formalized.

Next actions:

1. Define scaling configurations by model size and token budget.
2. Add architecture config schema for consistent experiment tracking.

Definition of done:

1. Each model run has explicit parameter, token, and compute targets.

## 8) Distributed training systems and cluster orchestration

Current status:

1. Local single-machine training flow exists.
2. Distributed orchestration is not implemented.

Next actions:

1. Abstract trainer launch interface from local scripts.
2. Prototype distributed launch configuration (FSDP/ZeRO choice and constraints).
3. Add checkpoint recovery drills in distributed context.

Definition of done:

1. At least one multi-node training workflow is documented and reproducible.

## 9) Region strategy when operating from Singapore

Current status:

1. Regional strategy is documented conceptually in `llm_training_overview.md`.
2. No executable region/capacity playbook in repository docs.

Next actions:

1. Add `docs/CLOUD_REGION_STRATEGY.md` for control-plane/data-plane decisions.
2. Define data residency and cross-region replication policies.

Definition of done:

1. Region and capacity choices are documented as explicit operating policy.

## 10) Training job mechanics: checkpoints, resumes, and fault tolerance

Current status:

1. Robust checkpoint/resume is implemented for tokenizer training.
2. Equivalent rigor is not yet implemented for full model pretraining/SFT scripts.

Next actions:

1. Add model + optimizer + RNG checkpointing policy for pretraining.
2. Add forced interruption recovery tests for model training stages.

Definition of done:

1. Training jobs can resume deterministically from durable checkpoints.

## 11) Evaluation harness: quality, capability, and safety as continuous signals

Current status:

1. Basic generation smoke test exists.
2. No full capability/safety regression harness yet.

Next actions:

1. Implement benchmark suite runner for capability and safety probes.
2. Version eval outputs by model/tokenizer/dataset IDs.
3. Add pass/fail release thresholds.

Definition of done:

1. Eval gates are part of standard promotion workflow.

## 12) Post-training pipeline (the real product phase)

Current status:

1. Minimal LoRA SFT stage exists.
2. No preference-optimization or safety-specific tuning pipeline yet.

Next actions:

1. Add structured instruction dataset management and quality filters.
2. Add DPO/RLAIF-ready data and training interfaces.
3. Add safety tuning stage templates.

Definition of done:

1. Post-training variants are reproducible and policy-evaluable.

## 13) Compression and inference optimization

Current status:

1. Not implemented.

Next actions:

1. Add quantization and inference benchmark scripts.
2. Track latency/throughput/cost metrics as versioned artifacts.

Definition of done:

1. At least one compressed serving artifact with benchmark report exists.

## 14) Deployment, monitoring, and the data flywheel

Current status:

1. Not implemented.

Next actions:

1. Define serving deployment architecture and telemetry schema.
2. Add feedback capture loop for retraining data curation.

Definition of done:

1. Closed-loop process exists from production signals to dataset/model updates.
