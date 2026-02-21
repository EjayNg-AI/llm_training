## North Star: a modern large language model training pipeline you can realistically build on AWS (operated from Singapore)

Canonical stage heading contract:

1. The stage headings in this document are mirrored exactly in `docs/NEXT_STEPS.md`.
2. If a stage heading changes here, the matching heading in `docs/NEXT_STEPS.md` must be updated in the same change.

This is the “gold standard” end state: not one monolithic system, but a set of **disciplined, versioned pipelines** that turn raw data into (1) a pretrained foundation model, (2) post-trained aligned variants, and (3) deployable inference artifacts—with **repeatability, governance, and auditability**.

I’ll describe the stages in the order you’d implement them in a serious program, and I’ll call out AWS-native building blocks and the “gotchas” that matter at scale.

---

### 0) Program governance, scope, and guardrails

**Goal:** prevent “we trained something” from turning into “we can’t ship it.”

**Key deliverables**

* A **model spec**: target domains, languages, context length, tool-use expectations, refusal boundaries.
* A **data policy**: what sources are allowed, licensing rules, personally identifiable information (PII) handling, retention, provenance.
* A **risk register + eval gates**: what “unsafe” means for your use case and what tests gate promotion.
* A “one-way door” list: e.g., tokenizer changes, chat template changes, system prompt changes, output safety style.

**AWS building blocks**

* Identity and Access Management (IAM), Key Management Service (KMS), CloudTrail (audit), Organizations / Control Tower (multi-account isolation), Virtual Private Cloud (VPC) segmentation.

**Common failure mode**

* Teams skip this and later discover they cannot legally use parts of the corpus, or cannot reproduce a run, or cannot explain where outputs came from.

---

### 1) Data acquisition + provenance capture

**Goal:** build a data lake where every byte is attributable and policy-compliant.

**Sources you might ingest**

* Curated licensed corpora, internal documents, permissively licensed web data, code, academic text, domain-specific sources, synthetic data.

**What “good” looks like**

* Every document has: `source`, `license`, `crawl_date`, `hash`, `language`, `quality_score`, `pii_flags`, `toxicity_flags`, `dedup_cluster_id`.

**AWS building blocks**

* Simple Storage Service (S3) for raw immutable storage, Glue Data Catalog for metadata, Athena for querying, Lake Formation for access controls.

---

### 2) Data cleaning, normalization, and *aggressive* filtering

**Goal:** reduce garbage-in effects and keep your model from learning the worst parts of the internet.

**Typical sub-stages**

* Format normalization (HTML → text), boilerplate removal, sentence boundary cleanup.
* Language ID (language identification) + script detection.
* PII detection and removal/redaction (emails, phone numbers, IDs).
* Toxicity / sexual / violence / hate filters tuned to your risk tolerance.
* Quality scoring (per-document) and mixture policies (sample high-quality more often).

**At scale, this is not optional**

* The difference between a good model and a chaotic one is often **data filtering + dedup + mixture**, not architecture.

**AWS building blocks**

* Elastic MapReduce (EMR) / Glue / Batch / Spark-on-Kubernetes for large ETL (extract-transform-load).
* Step Functions / Airflow / Dagster for orchestration.
* S3 + partitioned layouts (`s3://…/clean/v3/lang=en/year=2025/...`) for performance and reproducibility.

---

### 3) Deduplication (exact + near-duplicate) and contamination control

**Goal:** prevent memorization, benchmark leakage, and distribution collapse.

**Approach**

* Exact dedup by hashing normalized text.
* Near-dedup via MinHash / SimHash / embedding-based clustering.
* **Contamination control:** remove benchmark test sets (and close paraphrases) from pretraining corpora.

**Deliverables**

* Dedup clusters and a reproducible rule for “keep best representative.”
* A contamination report for key eval sets.

---

### 4) Dataset versioning + “mixture as code”

**Goal:** make your training set a first-class artifact.

**What to version**

* Raw corpus snapshot IDs
* Cleaning code + config
* Tokenizer version
* Mixture weights (e.g., 35% web, 25% code, 20% books, 20% domain)

**Practical advice**

* Treat the dataset mixture like a model: it should have **release versions**, changelogs, and regression tests.

---

### 5) Sharding and streaming-ready data formats

**Goal:** feed thousands of accelerators without I/O starvation.

**Typical output formats**

* JSON Lines (JSONL) for intermediate text corpora.
* Tokenized binary shards for training: WebDataset-style tar shards, or memory-mapped arrays, or other streaming datasets.

**AWS storage pattern**

* S3 for durable object storage.
* A high-throughput shared filesystem for training jobs that need POSIX semantics:

  * Amazon FSx for Lustre is designed for high-performance workloads and can reach very high throughput/IOPS with low latency. ([Amazon Web Services, Inc.][1])
  * It can integrate with S3, presenting S3 objects as files and syncing results back. ([AWS Documentation][2])

---

### 6) Tokenizer design + training (and why it’s a “one-way door”)

**Goal:** define the model’s vocabulary and text interface.

**Decisions**

* Tokenization algorithm (Byte Pair Encoding (BPE) vs unigram SentencePiece).
* Vocabulary size (trade-off: efficiency vs expressivity).
* Special tokens and chat formatting tokens.
* Multilingual strategy (single tokenizer vs language-specific segments).

**Deliverables**

* Tokenizer artifact + tests:

  * Round-trip stability tests
  * Allowed/blocked character sets
  * Chat template compatibility tests

**Why this matters**

* Changing the tokenizer later breaks comparability and complicates continued pretraining.

---

### 7) Architecture and scaling plan

**Goal:** pick a transformer variant and training recipe that can scale from “small pilot” to “frontier-ish.”

**Core choices**

* Decoder-only Transformer (standard for next-token prediction).
* Context length, attention variant (standard attention, grouped query attention, etc.).
* Training objective: causal language modeling (next token), plus optional auxiliary losses.

**Scaling plan**

* Use scaling-law thinking: if you double parameters without enough tokens, you under-train; if you over-train small models, you waste compute.
* Bake into config: target tokens, target steps, and target compute.

---

### 8) Distributed training systems and cluster orchestration

**Goal:** keep GPUs/accelerators busy and make failures non-catastrophic.

**Parallelism toolbox (define once, reuse everywhere)**

* Data parallelism (replicate model, split batch)
* Fully Sharded Data Parallel (FSDP): shard parameters/gradients/optimizer states
* ZeRO (Zero Redundancy Optimizer): similar sharding strategy (often via DeepSpeed)
* Tensor parallelism (split matrix ops across devices)
* Pipeline parallelism (split layers across devices)

**High-performance networking**

* Elastic Fabric Adapter (EFA) is AWS’s low-latency network interface aimed at high performance computing (HPC) and large-scale training. AWS documentation notes EFA supports NVIDIA Collective Communications Library (NCCL) and common Message Passing Interface (MPI) stacks (e.g., Open MPI). ([AWS Documentation][3])
* EC2 P5/P5e/P5en pages emphasize EFA support for scaling HPC/AI workloads. ([Amazon Web Services, Inc.][4])

**Orchestration options**

* Kubernetes (Elastic Kubernetes Service (EKS)) if you’re already K8s-native.
* Slurm (common HPC scheduler).
* AWS ParallelCluster if you want an AWS-supported way to stand up HPC clusters (often Slurm-based). ([Amazon Web Services, Inc.][5])
* SageMaker HyperPod for managed large-scale clusters and resiliency:

  * HyperPod is positioned to scale training/fine-tuning across **hundreds to thousands of accelerators** and provides centralized governance and fault recovery features. ([Amazon Web Services, Inc.][6])
  * AWS docs also describe HyperPod’s integration with Slurm for orchestration. ([AWS Documentation][7])

---

### 9) Region strategy when operating from Singapore

You can *operate* from Singapore and still train elsewhere, but region selection affects cost, data gravity, and accelerator availability.

**Reality check (important): Singapore region accelerator menu**

* AWS’s EC2 “instance types by Region” documentation lists **Asia Pacific (Singapore) (ap-southeast-1)** accelerated computing options including **G4dn, G5g, Inf1, Inf2, P3, and P4de**. ([AWS Documentation][8])
* The same AWS document shows nearby regions offering higher-end training instances (example: **Jakarta (ap-southeast-3)** includes **P5/P5e/P5en** in its accelerated list). ([AWS Documentation][8])

**Practical North Star pattern**

* Keep the “control plane” (metadata, orchestration, dashboards) in Singapore for operator convenience.
* Place **bulk training compute** where you can reliably get capacity (often not Singapore).
* Replicate datasets cross-region only when needed; otherwise, move compute to the data or accept replication costs.

---

### 10) Training job mechanics: checkpoints, resumes, and fault tolerance

**Goal:** make multi-week runs survivable.

**Essentials**

* Deterministic config + seed management (as much as practical).
* Periodic checkpoints (model + optimizer + RNG state).
* Separate “fast checkpoints” (local/NVMe) and “durable checkpoints” (S3).
* Spot interruption strategy (if using Spot): frequent durable checkpointing + automatic resume.

**Common failure mode**

* Teams checkpoint only weights and later can’t resume training correctly (optimizer state matters a lot).

---

### 11) Evaluation harness: quality, capability, and safety as continuous signals

**Goal:** treat eval like CI (continuous integration), not a one-off benchmark run.

**Layers**

* **Pretraining metrics:** validation loss/perplexity, churn, gradient stats.
* **Capability evals:** task suites aligned with your target domains.
* **Safety evals:** jailbreak robustness, refusal correctness, toxicity/harassment, privacy leakage probes.
* **Regression gating:** prevent “improvements” that break basic behavior.

**Implementation**

* A single eval harness that can run on:

  * a laptop (tiny model)
  * a single GPU node
  * a distributed cluster
* Store eval outputs with strict versioning (model hash + tokenizer hash + dataset version).

---

### 12) Post-training pipeline (the “real product” phase)

Pretraining makes a foundation model; post-training makes it usable.

**Typical stages**

1. **Continued pretraining** (domain adaptation)

   * Add domain corpora; keep objective the same; small learning rate; careful with catastrophic forgetting.

2. **Supervised fine-tuning (SFT)**

   * Train on instruction-response data. Strong effect on usability and style.

3. Preference optimization

   * RLHF (Reinforcement Learning from Human Feedback): reward model + policy optimization (often Proximal Policy Optimization (PPO)).
   * RLAIF (Reinforcement Learning from AI Feedback): similar, but preference labels can be generated by another model.
   * DPO (Direct Preference Optimization): a simpler and popular preference-training method that avoids explicit RL loops.

4. Safety-specific tuning

   * Refusal training, policy compliance, sensitive topic handling, tool-use constraints.

**HyperPod note**

* HyperPod is explicitly pitched for long-running model development tasks (training, fine-tuning, inference) with automated fault detection and recovery features. ([Amazon Web Services, Inc.][6])

---

### 13) Compression and inference optimization

**Goal:** take a research checkpoint and turn it into an efficient serving artifact.

**Common steps**

* Distillation (teacher → student).
* Quantization (e.g., weight-only 8-bit/4-bit).
* Kernel-optimized inference backends (vLLM, TensorRT-LLM, etc.).
* Context-length and memory optimizations (key-value cache management).

---

### 14) Deployment, monitoring, and the data flywheel

**Goal:** ship safely, measure real behavior, and improve.

**Serving concerns**

* Latency/throughput targets
* Cost per 1M tokens
* Safety filters and refusal behavior
* Observability: prompt distributions, failure clusters, drift

**Feedback loop**

* Collect user feedback and failure cases.
* Curate and label (or synthesize) new training data.
* Re-run post-training and re-evaluate through the same gates.

---

## Minimal end-to-end pipeline on a laptop (CPU + modest GPU), designed to scale up cleanly

This is a **proof-of-concept** pipeline that:

* runs on a single machine,
* keeps artifacts versionable,
* uses the same conceptual stages as the North Star,
* can later be “lifted” to AWS by swapping storage + scaling training.

I’ll give you a concrete path that works even with ~4–12 GB of GPU memory by training a **small decoder-only transformer** from scratch (quick) and then doing a tiny **instruction fine-tune**.

### A. Minimal repo structure (simple, scalable)

```
llm-pipeline/
  data/
    raw/
    processed/
  artifacts/
    tokenizer/
    models/
    eval/
  scripts/
    01_make_corpus.py
    02_train_tokenizer.py
    03_pretrain.py
    04_sft_lora.py
    05_eval_generate.py
  configs/
    base.yaml
```

You can later map this to S3 paths (same structure), and map `artifacts/` to a model registry.

---

### B. Step 1 — Create a tiny text corpus (raw → cleaned)

For a laptop, start with something small like WikiText-2 or a small Wikipedia slice.

```python
# scripts/01_make_corpus.py
from datasets import load_dataset
import re
from pathlib import Path

OUT = Path("data/raw")
OUT.mkdir(parents=True, exist_ok=True)

ds = load_dataset("wikitext", "wikitext-2-raw-v1")

def clean(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line

for split in ["train", "validation", "test"]:
    path = OUT / f"{split}.txt"
    with path.open("w", encoding="utf-8") as f:
        for t in ds[split]["text"]:
            t = clean(t)
            if len(t) >= 20:
                f.write(t + "\n")

print("Wrote:", [str(p) for p in OUT.glob("*.txt")])
```

**Scaling hook:** in the North Star, this is where your large-scale cleaning/dedup/filtering pipeline lives.

---

### C. Step 2 — Tokenizer (minimal version + scalable version)

**Minimal (recommended for laptop):** reuse GPT‑2 tokenizer to reduce moving parts.
**Scalable path:** train your own BPE/unigram tokenizer later.

Here’s the minimal approach (reuse a pretrained tokenizer):

```python
# scripts/02_train_tokenizer.py
# Minimal: just “pin” a tokenizer version and save it as an artifact.
from transformers import AutoTokenizer
from pathlib import Path

tok = AutoTokenizer.from_pretrained("gpt2")
tok.pad_token = tok.eos_token  # important for batching

OUT = Path("artifacts/tokenizer/gpt2")
OUT.mkdir(parents=True, exist_ok=True)
tok.save_pretrained(OUT)
print("Saved tokenizer to", OUT)
```

**Scaling hook:** swap this script with actual tokenizer training over a representative sample of your full corpus.

---

### D. Step 3 — Pretrain a tiny causal language model (from scratch)

This trains a small transformer fast enough to learn “something” on a laptop GPU.

```python
# scripts/03_pretrain.py
import math
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    GPT2Config,
    GPT2LMHeadModel,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)
from pathlib import Path

MODEL_OUT = Path("artifacts/models/tiny-gpt2-from-scratch")
MODEL_OUT.mkdir(parents=True, exist_ok=True)

# 1) Load tokenizer artifact (pinned)
tok = AutoTokenizer.from_pretrained("artifacts/tokenizer/gpt2")
tok.pad_token = tok.eos_token

# 2) Load raw text
data_files = {
    "train": "data/raw/train.txt",
    "validation": "data/raw/validation.txt",
}
ds = load_dataset("text", data_files=data_files)

# 3) Tokenize + chunk into fixed blocks
block_size = 256

def tokenize(batch):
    return tok(batch["text"], truncation=False)

tok_ds = ds.map(tokenize, batched=True, remove_columns=["text"])

def group_texts(examples):
    # Concatenate then split into blocks
    concat = {k: sum(examples[k], []) for k in examples.keys()}
    total_len = (len(concat["input_ids"]) // block_size) * block_size
    result = {
        k: [t[i : i + block_size] for i in range(0, total_len, block_size)]
        for k, t in concat.items()
    }
    result["labels"] = result["input_ids"].copy()
    return result

lm_ds = tok_ds.map(group_texts, batched=True)

# 4) Define a small GPT-2-like config (tiny model)
config = GPT2Config(
    vocab_size=tok.vocab_size,
    n_positions=block_size,
    n_ctx=block_size,
    n_embd=384,
    n_layer=6,
    n_head=6,
)
model = GPT2LMHeadModel(config)
model.gradient_checkpointing_enable()  # reduces VRAM

# 5) Training
args = TrainingArguments(
    output_dir=str(MODEL_OUT),
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    gradient_accumulation_steps=4,
    learning_rate=3e-4,
    warmup_steps=200,
    max_steps=3000,
    logging_steps=50,
    eval_steps=250,
    save_steps=250,
    evaluation_strategy="steps",
    save_total_limit=3,
    fp16=True,  # set False if you don’t have CUDA
    report_to=[],
)

collator = DataCollatorForLanguageModeling(tok, mlm=False)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=lm_ds["train"],
    eval_dataset=lm_ds["validation"],
    data_collator=collator,
)

trainer.train()
trainer.save_model(MODEL_OUT)
tok.save_pretrained(MODEL_OUT)

# Quick perplexity print
eval_out = trainer.evaluate()
ppl = math.exp(eval_out["eval_loss"])
print("eval_loss:", eval_out["eval_loss"], "perplexity:", ppl)
```

**Scaling hooks**

* You can later replace `Trainer` with `accelerate launch` + Fully Sharded Data Parallel (FSDP) or DeepSpeed ZeRO.
* Replace `load_dataset("text", ...)` with a streaming dataset and shards stored in S3/FSx.

---

### E. Step 4 — Minimal instruction tuning with LoRA (optional but valuable)

LoRA (Low-Rank Adaptation) is a **parameter-efficient fine-tuning** approach: you update a small number of adapter weights instead of all weights.

This is a clean bridge to the North Star because large systems often do LoRA-based adaptation loops.

```python
# scripts/04_sft_lora.py
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
from pathlib import Path

BASE = "artifacts/models/tiny-gpt2-from-scratch"
OUT  = Path("artifacts/models/tiny-gpt2-sft-lora")
OUT.mkdir(parents=True, exist_ok=True)

tok = AutoTokenizer.from_pretrained(BASE)
tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(BASE)

# Small instruction dataset (example)
ds = load_dataset("tatsu-lab/alpaca", split="train[:2000]")

def format_example(ex):
    prompt = f"### Instruction:\n{ex['instruction']}\n\n### Response:\n{ex['output']}\n"
    return {"text": prompt}

ds = ds.map(format_example, remove_columns=ds.column_names)

def tokenize(batch):
    return tok(batch["text"], truncation=True, max_length=256)

ds_tok = ds.map(tokenize, batched=True, remove_columns=["text"])
ds_tok = ds_tok.train_test_split(test_size=0.05, seed=0)

lora = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora)

args = TrainingArguments(
    output_dir=str(OUT),
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    max_steps=800,
    logging_steps=50,
    eval_steps=200,
    save_steps=200,
    evaluation_strategy="steps",
    fp16=True,
    report_to=[],
)

trainer = Trainer(model=model, args=args, train_dataset=ds_tok["train"], eval_dataset=ds_tok["test"])
trainer.train()

model.save_pretrained(OUT)
tok.save_pretrained(OUT)
print("Saved LoRA-tuned model to", OUT)
```

Install dependency:

```bash
pip install peft
```

**Scaling hooks**

* Replace Alpaca with your curated instruction data + safety data.
* Later: add preference optimization (e.g., DPO) as a new stage, rather than overloading SFT.

---

### F. Step 5 — Quick generation + sanity eval

```python
# scripts/05_eval_generate.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_DIR = "artifacts/models/tiny-gpt2-sft-lora"  # or tiny-gpt2-from-scratch

tok = AutoTokenizer.from_pretrained(MODEL_DIR)
tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR)

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
model.eval()

prompt = "### Instruction:\nExplain gradient descent in one paragraph.\n\n### Response:\n"
x = tok(prompt, return_tensors="pt").to(device)

with torch.no_grad():
    y = model.generate(
        **x,
        max_new_tokens=150,
        do_sample=True,
        temperature=0.9,
        top_p=0.95,
    )

print(tok.decode(y[0], skip_special_tokens=True))
```

---

## How this laptop pipeline scales into the North Star (conceptual mapping)

If you keep the *interfaces* stable, scaling is mostly swapping implementations:

* **Local text files → S3 data lake**
  Same logical partitions, just different storage and metadata tooling.
* **Local preprocessing → distributed ETL on Spark/Batch/EMR**
  Same outputs: cleaned JSONL + shards.
* **Single GPU training → distributed training cluster**
  Same training loop concept; add parallelism (FSDP/ZeRO/tensor parallel) and high-performance networking (EFA). ([AWS Documentation][3])
* **Local artifacts → model registry + evaluation gates**
  Same artifact types: tokenizer, base checkpoint, post-trained checkpoint, eval reports.
* **Local filesystem bottlenecks → FSx for Lustre + S3 integration**
  Same shard formats; faster feeding. ([Amazon Web Services, Inc.][1])

---

## A blunt but useful critique

Most teams over-focus on:

* architecture novelty,
* “we got H100s,”
* fancy post-training,

…and under-invest in:

* dataset provenance + licensing,
* dedup/contamination,
* mixture design,
* reproducible eval gates,
* operational fault tolerance.

If you build the North Star with **data + eval discipline** as the backbone, scaling compute later will actually pay off.

---

[1]: https://aws.amazon.com/fsx/lustre/?utm_source=chatgpt.com "Amazon FSx for Lustre | Cloud File Storage Integrated ..."
[2]: https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html?utm_source=chatgpt.com "What is Amazon FSx for Lustre?"
[3]: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html?utm_source=chatgpt.com "Elastic Fabric Adapter for AI/ML and HPC workloads on ..."
[4]: https://aws.amazon.com/ec2/instance-types/p5/?utm_source=chatgpt.com "Amazon EC2 P5 Instances"
[5]: https://aws.amazon.com/hpc/parallelcluster/?utm_source=chatgpt.com "AWS ParallelCluster - Amazon Web Services"
[6]: https://aws.amazon.com/sagemaker/ai/hyperpod/?utm_source=chatgpt.com "Amazon SageMaker HyperPod - AWS"
[7]: https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod.html?utm_source=chatgpt.com "Amazon SageMaker HyperPod"
[8]: https://docs.aws.amazon.com/ec2/latest/instancetypes/ec2-instance-regions.html "Amazon EC2 instance types by Region - Amazon EC2"
