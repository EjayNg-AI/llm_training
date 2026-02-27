# Next Steps (Aligned to `llm_training_overview.md`)

This roadmap uses the same stage titles as `llm_training_overview.md` so planning and execution stay synchronized.

## 0) Program governance, scope, and guardrails

Current status:

1. Engineering pipeline stages are now artifact-versioned and traceable.
2. Formal governance policy artifacts are still not codified.

Next actions:

1. Add `docs/GOVERNANCE_MODEL_SPEC.md` with domain scope, refusal boundaries, and tool-use constraints.
2. Add `docs/DATA_POLICY.md` with licensing, PII handling, and retention expectations.
3. Add `docs/RELEASE_GATES.md` to define promotion criteria tied to eval outputs.

Definition of done:

1. Model promotion and dataset usage are controlled by documented policy gates.

## 1) Data acquisition + provenance capture

Current status:

1. `01_build_corpus.py` produces canonical document artifacts and manifests.
2. Raw-source policy metadata (`license`, `crawl_date`, quality tags) remains sparse.

Next actions:

1. Expand corpus schema population for source/license provenance fields.
2. Add provenance validators in corpus build stage.
3. Record raw-source acquisition manifests for each dataset release.

Definition of done:

1. Every training document has machine-readable provenance fields and validation checks.

## 2) Data cleaning, normalization, and aggressive filtering

Current status:

1. Baseline normalization and short-doc filters exist.
2. Policy-grade cleaning/filtering (PII/toxicity/quality scoring) is not yet implemented.

Next actions:

1. Add dedicated cleaning/filter stage with configurable filters.
2. Add PII/toxicity tagging hooks.
3. Add quality score output to corpus manifests.

Definition of done:

1. Cleaned dataset outputs are reproducible and policy-checkable from raw inputs.

## 3) Deduplication (exact + near-duplicate) and contamination control

Current status:

1. Exact dedup v0 is implemented in `02_dedup_exact.py`.
2. Near-dedup and contamination denylist checks are not implemented.

Next actions:

1. Add near-dedup stage (MinHash/SimHash style clustering).
2. Add contamination checks against benchmark denylist sets.
3. Emit per-release dedup/contamination reports.

Definition of done:

1. Exact+near dedup and contamination controls are run and versioned for each corpus release.

## 4) Dataset versioning + mixture as code

Current status:

1. Artifact manifests and registry now provide dataset lineage primitives.
2. Mixture-as-code policies and dataset release semantics are still incomplete.

Next actions:

1. Add dataset release schema (`dataset_id`, source versions, cleaning config, tokenizer id).
2. Add mixture configs under `configs/dataset_mixtures/`.
3. Add changelog policy for dataset mixture updates.

Definition of done:

1. Dataset releases are reproducible from config + manifests + registry lineage.

## 5) Sharding and streaming-ready data formats

Current status:

1. Tokenization and packing now emit deterministic binary shards with index files.
2. Streaming dataloader and shard-performance validation are not implemented.

Next actions:

1. Add streaming dataloader abstraction for packed shards.
2. Add shard read/throughput validation scripts.
3. Document binary schema and compatibility policy.

Definition of done:

1. Training can stream shard artifacts without full in-memory loading.

## 6) Tokenizer design + training (one-way door)

Current status:

1. Deterministic tokenizer trainer with checkpoint instrumentation is implemented and published as artifact IDs.
2. Runtime tokenizer class exists for downstream stage consumption.

Next actions:

1. Add compatibility tests across tokenizer runtime and training exports.
2. Freeze tokenizer versioning policy for future model families.
3. Add explicit tokenizer deprecation/migration protocol.

Definition of done:

1. Tokenizer training/runtime/export contracts are CI-enforced and version-governed.

## 7) Architecture and scaling plan

Current status:

1. Tiny GPT-style local pretraining is integrated into artifact-based flow.
2. Formal parameter/context/token-budget scaling targets are not codified.

Next actions:

1. Add scaling target schema by model size.
2. Add experiment templates for token budget and compute budget tracking.

Definition of done:

1. Every model run specifies planned scaling targets and budgets.

## 8) Distributed training systems and cluster orchestration

Current status:

1. Local single-node runner with checkpoint/resume is implemented.
2. Distributed launcher/orchestration is not implemented.

Next actions:

1. Abstract launch interface for local vs distributed execution.
2. Prototype FSDP/ZeRO-oriented distributed config.
3. Add distributed recovery drills.

Definition of done:

1. At least one reproducible multi-node training workflow is documented and runnable.

## 9) Region strategy when operating from Singapore

Current status:

1. Region strategy remains conceptual in `llm_training_overview.md`.
2. No executable region/capacity runbook is in repo docs.

Next actions:

1. Add `docs/CLOUD_REGION_STRATEGY.md`.
2. Document cross-region replication/cost/capacity decisions.

Definition of done:

1. Region and capacity choices are captured as operating policy.

## 10) Training job mechanics: checkpoints, resumes, and fault tolerance

Current status:

1. Checkpoint/resume rigor now exists for tokenizer and local pretraining runner.
2. SFT/eval and future distributed runs need equivalent recovery hardening.

Next actions:

1. Add explicit checkpoint schema docs for model runs.
2. Add forced interruption tests for pretrain and SFT.
3. Add checkpoint retention and durability policy.

Definition of done:

1. Long-running training stages recover from interruption with controlled drift.

## 11) Evaluation harness: quality, capability, and safety as continuous signals

Current status:

1. Eval stage v0 now emits versioned eval artifacts (`eval.json`, `samples.txt`, metrics).
2. Capability/safety benchmark suites and release gates are still minimal.

Next actions:

1. Add benchmark suite runner for capability + safety probes.
2. Add pass/fail thresholds tied to release gating docs.
3. Add regression diff tooling across eval artifact IDs.

Definition of done:

1. Eval gates are part of default promotion workflow.

## 12) Post-training pipeline (the real product phase)

Current status:

1. LoRA SFT stage is now integrated with artifact lineage and stage run contracts.
2. Preference optimization and safety-specific post-training remain unimplemented.

Next actions:

1. Add structured instruction dataset governance.
2. Add DPO/RLAIF-ready interfaces and training scripts.
3. Add safety tuning templates and eval coupling.

Definition of done:

1. Post-training variants are reproducible and policy-evaluable.

## 13) Compression and inference optimization

Current status:

1. Not implemented.

Next actions:

1. Add quantization/export scripts.
2. Add latency/throughput/cost benchmark reporting as versioned artifacts.

Definition of done:

1. At least one compressed serving artifact has reproducible benchmark evidence.

## 14) Deployment, monitoring, and the data flywheel

Current status:

1. Not implemented.

Next actions:

1. Define serving deployment architecture and telemetry schema.
2. Add feedback-to-retraining ingestion loop design.

Definition of done:

1. Closed-loop process exists from production signals to dataset/model updates.
