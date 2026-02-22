## What Comes Next

From here, the “ground up” move is: **standardize the infrastructure patterns (runs, manifests, hashing, atomic I/O, resume gates) and then build the data→tokens→batches→train loop pipeline as *stages* that reuse those patterns.**

---

## 1) Unify the “run infrastructure” pattern across *all* pipeline stages

Right now the tokenizer has:

* `run_id`, `run.output_dir`
* `config_hash`, `pattern_hash`
* atomic writes, WAL, snapshots
* progress JSON and metrics JSONL

**Next step:** extract a small shared library (even if it’s just a few Python modules) so that every future stage (corpus build, tokenization, packing, training, eval) behaves the same way.

### Deliverables

Create something like:

```
src/infra/
  run_dir.py            # create run dirs, write run metadata
  hashing.py            # canonical config hashing, file hashing, corpus manifest hashing
  io_atomic.py          # reuse your existing scripts/tokenizer_bpe/io_atomic.py or move it
  logging.py            # structured JSONL + human logs
  manifest.py           # artifact manifests and registration
  resume.py             # “resume gate” helpers (hash match, version match)
```

### “Done means”

* Any script can be run as:

```bash
python scripts/XX_stage.py --config configs/stage.yaml [--resume --run-id ...]
```

and it will always produce:

* `state.json`
* `metrics.jsonl`
* `run_meta.json` (git commit, python version, pip freeze, hostname, start/end timestamps)
* atomic, checksum-protected outputs

### Why this matters

If you don’t standardize this now, you’ll reinvent it (inconsistently) 5 times later.

---

## 2) Define an Artifact Registry contract (local now, S3 later)

Your tokenizer export directory is already crisp (`vocab.json`, `merges.txt`, `tokenizer_config.json`, …). Do the same for every artifact type going forward.

### Artifact types you’ll soon have

* **Corpus snapshot** (cleaned docs + manifest)
* **Tokenized shards** (token IDs + shard index)
* **Packed dataset** (fixed-length sequences + index)
* **Model checkpoints** (weights + optimizer + trainer state)
* **Evaluation reports** (perplexity, samples, safety probes later)

### Deliverables

A consistent layout like:

```
artifacts/
  registry.jsonl                 # append-only registry of “published” artifacts
  tokenizer/
    exports/<tokenizer_id>/...
  corpora/
    <corpus_id>/...
  tokens/
    <token_shards_id>/...
  packed/
    <packed_id>/...
  models/
    <model_id>/...
  eval/
    <eval_id>/...
```

And a **manifest** file for every artifact directory:

`artifact_manifest.json` containing:

* `artifact_type`
* `artifact_id` (stable name)
* `created_at`
* `source_run_id`
* `config_hash`
* `git_commit`
* `inputs` (artifact IDs + hashes)
* `stats` (counts, sizes, token counts, etc.)
* `schema_version`

### “Done means”

* Every stage consumes artifact IDs, not ad-hoc paths.
* It’s possible to answer: *“Which exact corpus+tokenizer produced this checkpoint?”* purely from manifests.

This is the single biggest “infrastructure first” win you can get.

---

## 3) Build the **Corpus Stage** (raw → normalized docs) with the same determinism/resume ethos

Tokenizer training currently consumes `data/raw/train.txt` (lines). That’s fine for now, but your next scalable unit should be **documents**, not lines.

### Design decision (important)

Define a **canonical doc schema** you’ll use everywhere:

```json
{
  "doc_id": "...stable hash...",
  "text": "...",
  "source": "...",
  "timestamp": "...optional...",
  "meta": { "lang": "...", "license": "...", "tags": [...] }
}
```

### Deliverables

Add a stage:

* `scripts/01_build_corpus.py`
* `configs/corpus.yaml`

Outputs:

* `data/corpus/<corpus_id>/docs.jsonl.gz` (or sharded)
* `data/corpus/<corpus_id>/manifest.json` with:

  * doc count
  * total bytes
  * sha256 per shard
  * deterministic file discovery hash (like your tokenizer’s `training_corpus_sha256`, but for doc shards)

### Minimal filters (start small, add later)

* drop empty/very short docs
* normalize Unicode (you already have NFC/NFKC options in tokenizer config—mirror them here)
* enforce UTF-8 decode errors policy
* optional: crude language heuristic later

### “Done means”

* You can rebuild the corpus and get identical `manifest.json` given identical raw inputs.
* Resume works mid-shard without corrupting outputs.

---

## 4) Add **Dedup v0** (exact dedup) before tokenization

Don’t jump to MinHash yet—just do exact dedup now so your downstream token counts and training aren’t inflated.

### Deliverables

* `scripts/01b_dedup_exact.py`
* output: `data/corpus/<corpus_id>/docs.dedup.jsonl.gz`
* manifest includes:

  * `kept_docs`
  * `dropped_duplicates`
  * dedup key (e.g., sha256 of normalized text)

### “Done means”

* Deterministic: dedup results don’t depend on processing order.
* Split safety: later you can split train/val by `doc_id` without leakage.

---

## 5) Turn your tokenizer into a **runtime library** (not just a training script)

You already have `runtime_check.py` with encode/decode logic. The next step is making that a stable interface used by tokenization + training.

### Deliverables

Create:

```
src/tokenizer/
  bpe.py          # load vocab/merges, encode/decode, batch encode
  special.py      # special token handling rules (pad/eos/bos/unk)
  hf_bridge.py    # optional: export compatibility helpers
```

Expose a class:

```python
class ByteLevelBPETokenizer:
    @classmethod
    def from_dir(cls, export_dir: str) -> "ByteLevelBPETokenizer": ...
    def encode(self, text: str) -> list[int]: ...
    def decode(self, ids: list[int]) -> str: ...
```

### “Done means”

* Tokenization stage can import this class and run purely from exported artifacts.
* You have tests for:

  * losslessness
  * special token ID placement rule
  * determinism across machines (your existing tests cover much of this)

---

## 6) Build the **Tokenization Stage** (docs → token shards) with shard indexing and dtype policy

This is the true “bridge” between data and training.

### Key design choices to make now (so you don’t rewrite later)

#### 6.1 Token ID dtype

* If `vocab_size <= 65535`, you *can* store token IDs as `uint16`.
* If you might exceed that later, store as `uint32` from day one, or implement a dtype decision recorded in the manifest.

Record in manifest:

* `token_dtype: "uint16" | "uint32"`

#### 6.2 Shard format

Keep it dead simple and streamable:

* `tokens_shard_00000.bin` (raw little-endian integers)
* `tokens_shard_00000.idx.json` containing per-doc offsets:

  * `doc_id`
  * `start`
  * `length`
  * (optional) `eos_appended: true`

and a top-level `index.json` listing shards + checksums.

### Deliverables

* `scripts/03_tokenize_corpus.py`
* `configs/tokenize.yaml`

Outputs:

* `artifacts/tokens/<token_shards_id>/shards/*.bin`
* `artifacts/tokens/<token_shards_id>/index.json`
* `artifact_manifest.json`

### “Done means”

* Deterministic shard boundaries (don’t shard “whenever buffer full” unless you make it deterministic).

  * Common deterministic rule: shard by doc count, e.g. 10,000 docs per shard.
* Resume works mid-shard safely (atomic commit per shard).

---

## 7) Build the **Packing Stage** (token shards → fixed-length training sequences)

This is where you decide how the model sees the stream.

### Minimal packing strategy (good enough for v0)

* For each doc: `tokens + [eos_id]`
* Concatenate into one long stream per shard
* Produce fixed blocks of `seq_len` with stride `seq_len` (no overlap)

Output:

* `train.bin` / `val.bin` (or sharded)
* optionally `train.idx` if you want random access

### Better packing strategy (North Star-compatible)

* Still concatenate, but also record doc boundaries or “reset positions” if you later want attention masking resets.

### Deliverables

* `scripts/04_pack_sequences.py`
* `configs/pack.yaml`

Outputs:

* `artifacts/packed/<packed_id>/{train,val}/shards/*.bin`
* `index.json` with shard sizes and total token counts

### “Done means”

* You can report:

  * total tokens in train/val
  * effective steps for a target batch size
* Split is deterministic and leakage-resistant:

  * split by `doc_id` hash modulo N (stable).

---

## 8) Only now: implement the **Training Runner v0** with resume-safe checkpoints

Once the data path is stable and versioned, training becomes straightforward and reproducible.

### Infrastructure-first requirements for training (match tokenizer rigor)

* `run_id`, `config_hash`, and a `training_state.json`
* atomic checkpoint writes
* checkpoint contains:

  * model weights
  * optimizer state
  * scheduler state
  * RNG states (python, numpy, torch)
  * global step

### Deliverables

* `scripts/05_train_gpt.py`
* `configs/train.yaml`
* `src/model/gpt.py` (a small decoder-only transformer)
* `src/train/loop.py` (trainer loop + logging)

### “Done means”

* You can kill training mid-step and resume to the same loss curve (within expected nondeterminism from GPU kernels).
* The run directory points unambiguously to:

  * tokenizer artifact id
  * corpus artifact id
  * token shards artifact id
  * packed dataset artifact id

---

## 9) Add an **Evaluation Harness v0** (perplexity + sample generation + regression tests)

Treat eval like CI.

### Deliverables

* `scripts/06_eval.py`
* `configs/eval.yaml`
* outputs:

  * `eval.json`
  * `samples.txt`
  * `metrics.jsonl`

### “Done means”

* Every model checkpoint can be evaluated with a single command.
* You can diff eval outputs across runs.

---

## 10) Prepare the AWS “lift-and-shift” path *without* moving yet

Since you asked to prepare infrastructure properly first, the laptop pipeline should be cloud-ready by design even if you’re not deploying to AWS today.

### Do now (cheap, high leverage)

* **Path abstraction**: keep all I/O behind a filesystem interface so `local` and `s3://` can be swapped later.
* **Containerize**:

  * `Dockerfile`
  * pinned `requirements.txt` / `uv.lock` / `poetry.lock`
* **IaC skeleton** (even if unused for now):

  * Terraform modules or CloudFormation templates for:

    * S3 bucket layout
    * IAM roles
    * a basic training instance profile

### “Done means”

* You can run the exact same stage container locally and later on an EC2 instance, changing only:

  * input/output URIs
  * instance type / distributed launcher

---

# The immediate “next steps” (concrete checklist)

1. **Extract shared infra** from tokenizer:

   * `io_atomic`, config hashing, run dir creation, structured logs
2. **Define artifact manifest schema** + registry append log
3. **Implement `01_build_corpus.py`** producing canonical doc JSONL + manifest
4. **Implement `01b_dedup_exact.py`**
5. **Create `src/tokenizer/ByteLevelBPETokenizer`** that loads your exported artifacts
6. **Implement `03_tokenize_corpus.py`** producing deterministic token shards + per-doc offsets
7. **Implement `04_pack_sequences.py`** producing fixed-length training blocks + token counts
8. **Only then implement training v0** with robust checkpoint/resume
9. Add eval v0 and CI regression tests on a tiny golden dataset

---

# One key question you don’t need to answer now (but decide soon)

**Will your training pipeline treat the data as:**

* a *single stream* of tokens (classic GPT-2 style), or
* *document-aware batches* with boundary-aware masking?

For v0, stream is simpler. But whichever you pick, encode it into your **packed dataset format** and manifest now so scaling doesn’t force a format rewrite.
