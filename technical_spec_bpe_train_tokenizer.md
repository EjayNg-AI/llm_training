## Technical spec: GPT‑2–style UTF‑8 byte‑level BPE tokenizer training in pure Python (laptop‑friendly, crash‑resumable)

### 1) Scope and objectives

**Goal:** Implement a **GPT‑2 / OpenAI GPT‑style** tokenizer trainer that learns a **byte-level Byte Pair Encoding (BPE)** merge table from text, using only Python (no Rust/C++ tokenizers), and can run on a consumer laptop (CPU-only or modest GPU; GPU is not materially useful here).

**Key properties**

* **Byte-level**: the tokenizer is lossless over UTF‑8 (all text can be represented without `<unk>`).
* **OpenAI GPT style**: regex-based pre-tokenization that preserves whitespace behavior similarly to GPT‑2 (leading-space tokens), then BPE merges over bytes.
* **Deterministic**: same inputs + config → same merges/vocab.
* **Time-efficient on laptop**: parallelize the *corpus counting* stage; keep the merge loop efficient with incremental updates and lazy heaps.
* **Always resumable**: robust checkpointing with an append-only write-ahead log (WAL) + periodic snapshots; safe against power loss mid-run.
* **Well-instrumented**: structured logs, metrics, validation checks, and clear artifacts.

---

### 2) Non-goals (explicitly)

* Not aiming to exactly reproduce OpenAI’s internal token ID assignments; only behaviorally similar.
* Not using GPU acceleration for BPE merge learning (it’s dict/heap heavy; CPU-bound).
* Not implementing a full tokenizer runtime in multiple languages in v1 (but export formats are compatible with building runtimes later).

---

### 3) Definitions

* **Byte Pair Encoding (BPE)**: an iterative compression-inspired algorithm. Start from a base alphabet (here: 256 bytes). Repeatedly merge the **most frequent adjacent pair of symbols** into a new symbol, building a merge list.
* **Byte-level**: text is UTF‑8 encoded to bytes; initial symbols are bytes 0–255; merges create multi-byte symbols.
* **Pretokenization**: split raw text into “pieces” (often word-ish units) before learning merges. GPT‑2 uses a regex that preserves leading spaces by including an optional leading space in many alternatives.

---

### 4) High-level architecture

#### 4.1 Pipeline stages

1. **Corpus scan & piece counting (parallelized)**
   Read files → decode UTF‑8 → pretokenize regex → count occurrences of each piece’s UTF‑8 byte string.

2. **Initialize BPE training state**
   Convert piece byte strings into sequences of base byte symbol IDs; create word-type inventory; build initial pair statistics.

3. **BPE merge learning loop (iterative)**
   Repeatedly select best pair → merge in affected word types → update pair statistics → checkpoint/WAL.

4. **Export artifacts**
   Produce `vocab.json`, `merges.txt`, and `tokenizer_config.json` (plus optional debug/metrics).

#### 4.2 Data flow (ASCII)

```
Raw text files
   |
   v
[Stage 1] Pretokenize + count pieces (bytes)  ---->  word_counts.pkl (checkpointed)
   |
   v
[Stage 2] Build word-type sequences + pair stats
   |
   v
[Stage 3] Learn merges with WAL + snapshots  ---->  merges.log + snapshots/
   |
   v
[Stage 4] Export vocab.json + merges.txt + config
```

---

### 5) Inputs, outputs, and file formats

#### 5.1 Inputs

* `input_paths`: list of files or directories. Supports `.txt`, `.jsonl` (configurable extraction), optionally `.gz` (optional).
* Expected encoding: UTF‑8. Invalid sequences handled by `decode_errors` policy.

#### 5.2 Outputs (artifacts)

**Primary artifacts**

* `merges.txt`
  Format:

  ```
  #version: 0.2
  <tokA> <tokB>
  <tokC> <tokD>
  ...
  ```

  Each token is a “byte-to-unicode” escaped string (see §7) so it’s JSON/text friendly.

* `vocab.json`
  JSON map `{ "token_string": token_id_int }`.

* `tokenizer_config.json`

  * regex pattern
  * byte-to-unicode version
  * special tokens list and IDs
  * training stats (corpus hash, config hash, counts)

**Training state / checkpoints**

* `checkpoints/word_counts.snapshot.pkl` + `checkpoints/word_counts.progress.json`
* `runs/<run_id>/state.snapshot.pkl` (periodic)
* `runs/<run_id>/merges.wal` (append-only WAL)

---

### 6) Configuration (single source of truth)

Use a single YAML (or JSON) config. Example schema:

```yaml
run:
  output_dir: "runs/tokenizer_run_001"
  seed: 0
  log_level: "INFO"
  structured_logs: true

data:
  input_paths: ["./data/raw/train.txt"]
  input_format: "text"        # "text" | "jsonl"
  jsonl_text_field: "text"    # if input_format=jsonl
  decode_errors: "replace"    # "strict" | "replace" | "ignore"
  normalize: "none"           # "none" | "NFKC" | "NFC"
  max_bytes: null             # optional cap for laptop
  max_lines: null             # optional cap
  num_workers: 4              # for counting
  batch_lines: 2000           # lines per worker task
  min_piece_freq: 2           # drop very rare pieces early to save RAM
  max_unique_pieces: 2000000  # optional cap; if exceeded, keep top-K by freq

pretokenizer:
  pattern: "gpt2_default"     # alias or literal regex
  custom_pattern: null

bpe:
  vocab_size: 50000           # includes base 256 + merges + specials
  min_merge_freq: 2
  max_merges: null            # derived from vocab_size if null
  max_word_types: 1500000     # cap word-type inventory for laptop
  max_piece_bytes: 200        # drop pathological long pieces
  tie_break: "lexicographic"  # deterministic tie-break

special_tokens:
  tokens: ["<|endoftext|>", "<|pad|>"]
  placement: "end"            # "start" | "end"

checkpointing:
  wal_fsync_each_commit: true
  snapshot_every_merges: 200
  snapshot_every_seconds: 300
  keep_last_snapshots: 3
```

---

### 7) Byte-to-unicode mapping (GPT‑2 style)

**Why needed:** if you store tokens as raw bytes, many bytes are control characters or invalid UTF‑8. GPT‑2 uses a reversible mapping from bytes 0–255 to a set of Unicode codepoints that are printable-ish and stable.

**Spec requirement**

* Implement `bytes_to_unicode()` producing:

  * `byte_to_unicode: dict[int, str]`
  * `unicode_to_byte: dict[str, int]`
* Deterministic mapping (no locale dependence).

**Reference algorithm (must match GPT‑2 behavior)**

* Start with a set of “printable” byte values:

  * `33..126`, `161..172`, `174..255`
* Map those bytes to the same codepoint.
* For all remaining bytes, map them to sequential codepoints starting at 256 (or higher) not overlapping prior.

**Acceptance tests**

* For all `b in 0..255`: `unicode_to_byte[byte_to_unicode[b]] == b`.
* Round-trip: for any bytes sequence `bs`, `decode(encode(bs)) == bs`.

> Implementation note: the mapping is tiny (256 entries). Build once, store in config/version stamp.

---

### 8) Pretokenization (OpenAI GPT‑2 style)

**Default regex pattern (alias: `gpt2_default`)**
Use the third-party `regex` module (not `re`) to support Unicode character properties like `\p{L}`.

Pattern:

```
's|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+
```

**Behavioral requirements**

* Produces pieces that often include a **leading space** (via ` ?...`) so the model can learn word boundaries.
* Must be compiled once at startup.
* Provide config option for alternative patterns (future: “tiktoken-like” patterns), but v1 ships with GPT‑2 default.

**Acceptance tests**

* The pattern must tokenize English contractions as separate pieces (`"don't" -> "don" + "'t"` style depending on regex matches).
* It must preserve whitespace segments in a consistent way.

---

### 9) Stage 1: corpus counting (parallel, resumable)

#### 9.1 What is being counted?

Count **piece byte strings**: for each pretokenized piece `p`:

* `p_bytes = p.encode("utf-8")`
* Increment `piece_counts[p_bytes] += 1`

This yields a multiset of “word-ish units” represented as bytes.

#### 9.2 Parallelization strategy

Best practice on a laptop: parallelize the **counting** stage, not the merge loop.

**Architecture**

* Single reader (main process) reads files line-by-line in **binary mode** to track byte offsets.
* Reader decodes each line to text (UTF‑8 with `decode_errors`).
* Reader batches decoded lines (size `batch_lines`) and submits to a `ProcessPoolExecutor`.
* Worker function:

  * applies normalization (optional)
  * applies compiled regex to each line
  * encodes each piece to UTF‑8 bytes
  * returns a local `Counter[bytes]`
* Main merges returned counters into global `Counter`.

#### 9.3 Checkpointing Stage 1

**Goal:** if power loss occurs mid-scan, resume without rescanning.

Maintain:

* `word_counts.snapshot.pkl` (atomic write)
* `word_counts.progress.json` containing:

  * list of files with:

    * `path`
    * `byte_offset` (position in file for next read)
    * `done: bool`
  * `total_lines_processed`
  * `total_pieces_seen`
  * `config_hash`, `pattern_hash`
  * `snapshot_id`, `timestamp`

**Atomicity**

* Always write snapshots as:

  * write to `tmp` → `flush` → `fsync` → `os.replace(tmp, final)`
* Progress file updated similarly.

**Snapshot frequency**

* After every N merged worker results, or every T seconds, whichever first.

#### 9.4 Memory control

Because `Counter[bytes]` can grow huge:

Mechanisms (configurable):

* Drop pieces with `len(p_bytes) > max_piece_bytes`.
* Drop pieces that are too rare early:

  * keep a rolling count and periodically prune entries with count < `min_piece_freq` (only safe after enough data has been seen; implement as periodic pruning pass).
* Hard cap `max_unique_pieces`:

  * if exceeded, keep only top-K by frequency (deterministic selection), log a warning, continue.

**Acceptance criteria**

* Stage 1 can resume from checkpoint and produce identical final `piece_counts` vs uninterrupted run (given deterministic pruning policy).

---

### 10) Stage 2: initialize BPE training state

#### 10.1 Word types and symbolization

Convert each piece (bytes) into a sequence of base symbols (byte IDs):

* Base symbol IDs: `0..255`.
* For a piece `p_bytes`, initial symbol sequence is `list(p_bytes)` (each byte value).

Build training inventory:

* `word_syms: List[List[int]]`  (one per unique piece)
* `word_freq: List[int]`        (same length)
* Optionally filter:

  * remove entries with `freq < min_piece_freq`
  * cap to top `max_word_types` by freq

#### 10.2 Token table being built

Maintain:

* `id_to_token_bytes: List[bytes]`

  * initially length 256 where `id_to_token_bytes[i] = bytes([i])`
  * each merge appends a new `bytes` sequence

Special tokens are **not used during merge learning**; they are appended to vocab at export time (or reserved up front, but simplest is append at end).

---

### 11) Stage 3: BPE merge learning algorithm (efficient on laptop)

#### 11.1 Data structures

To avoid O(num_words * merges) rescans, use incremental updates.

Core:

* `words: List[List[int]]`          # mutable symbol sequences per word type
* `freqs: List[int]`                # word type frequencies

Pair statistics:

* `pair_count: Dict[Tuple[int,int], int]`
  Weighted count across all word types:

  ```
  pair_count[(a,b)] = sum_over_words(freq[word] * occurrences_of_(a,b)_in_word)
  ```

Inverted index (for efficient updates):

* `pair_to_words: Dict[Tuple[int,int], List[int]]`
  For each pair, list of word indices where the pair occurs.
  **Important:** use **lazy invalidation** (do not remove stale indices immediately).

Candidate selection:

* `heap: List[Tuple[int, int, int]]`  (max-heap via negative counts)
  Store entries like `(-count, a, b)`.
  Use lazy popping: when popped, verify `count == pair_count[(a,b)]`; otherwise discard and continue.

Determinism:

* Tie-break rule: if equal counts, choose smallest `(a,b)` lexicographically (or configurable). Implement by pushing `( -count, a, b )` and relying on tuple order.

#### 11.2 Initialization of `pair_count` and `pair_to_words`

For each word index `i`:

* scan adjacent pairs in `words[i]`
* count occurrences per pair (within that word)
* update global:

  * `pair_count[pair] += freqs[i] * occ`
  * append `i` to `pair_to_words[pair]` once (or multiple times; recommended: append once and re-scan word when updating)

**Implementation choice (recommended for laptop):**

* Append index **once per pair presence** (not per occurrence) to keep lists smaller.
* When merging, re-scan the word to compute exact deltas for pair counts.

#### 11.3 Merge loop

Let `target_merges = vocab_size - 256 - num_special_tokens` (unless `max_merges` is specified).

For merge step `m = 1..target_merges`:

1. **Select best pair**

   * Pop from heap until entry matches current `pair_count`.
   * If best count `< min_merge_freq`, stop early.

2. **WAL “BEGIN” record**

   * Write `BEGIN\tm\ta\tb\tcount\n` to `merges.wal`
   * flush + (optional) `fsync`

3. **Create new symbol**

   * `new_id = len(id_to_token_bytes)`
   * `id_to_token_bytes.append(id_to_token_bytes[a] + id_to_token_bytes[b])`

4. **Apply merge to affected words**

   * Candidate indices = `pair_to_words[(a,b)]` (may contain stale indices).
   * For each `i` in candidates:

     * Verify `(a,b)` occurs in `words[i]` (quick scan; if not, skip).
     * Compute old local pair occurrences from `words[i]` (scan once).
     * Replace all occurrences of adjacent `a,b` with `new_id` (single pass).
     * Compute new local pair occurrences (scan once).
     * Update `pair_count` by delta weighted by `freqs[i]`:

       * For each old pair: subtract `freq * occ`
       * For each new pair: add `freq * occ`
     * For each **new pair present** in updated word:

       * append `i` to `pair_to_words[new_pair]` (lazy; no removals)
     * For each pair whose count changed, push updated count to heap.

5. **Zero-prune (optional)**

   * If `pair_count[pair] <= 0`, delete it to reduce dict size (careful with laziness).

6. **WAL “COMMIT” record**

   * Write `COMMIT\tm\tnew_id\n` to `merges.wal`
   * flush + `fsync` (if configured)

7. **Periodic snapshot**

   * Every `snapshot_every_merges` merges or `snapshot_every_seconds`:

     * Write `state.snapshot.pkl` atomically:

       * `words`, `freqs`, `id_to_token_bytes`, `m`, and minimal metadata.
     * Also write `state.json` (human-readable progress).
   * Keep only last `keep_last_snapshots`.

#### 11.4 Complexity expectations (qualitative)

* Stage 1 dominates wall time for large corpora.
* Merge loop cost is roughly proportional to:

  * total number of *word-type updates* across merges
  * average piece length (in bytes)
* Lazy invalidation trades some extra checks for greatly reduced bookkeeping overhead.

---

### 12) Crash-resumability design (must be bulletproof)

#### 12.1 Invariants

* A merge is considered “done” **only if** there is a corresponding `COMMIT` line in the WAL.
* Snapshots are treated as valid only if:

  * file loads successfully
  * embedded checksum matches
  * version/config hash matches

#### 12.2 WAL format and durability

`merges.wal` is append-only text (or binary) with:

* `BEGIN` records written **before** mutating state
* `COMMIT` written **after** mutations complete

**Durability requirement:** if `wal_fsync_each_commit=true`, then after each `COMMIT`, the run can be resumed without losing any committed merge.

**Example WAL lines**

```
BEGIN   1200    532     18      945321
COMMIT  1200    1456
```

#### 12.3 Resume procedure

On startup:

1. Load config; compute `config_hash`.
2. Find latest valid snapshot in `runs/<run_id>/snapshots/`.
3. Load snapshot state:

   * `words`, `freqs`, `id_to_token_bytes`, `last_snapshot_merge`
4. Read WAL from beginning (or from recorded WAL offset), parse merges:

   * Apply only merges with `COMMIT` and merge index > `last_snapshot_merge`
   * If a `BEGIN` exists without `COMMIT`, ignore it (it was in-flight)
5. Rebuild `pair_count`, `pair_to_words`, `heap` from current `words`:

   * This makes resume deterministic even if the snapshot didn’t store these large structures.

**Acceptance test**

* Train for N merges, crash (kill process), resume, continue to completion.
* Final `merges.txt` and `vocab.json` must match bit-for-bit against a clean uninterrupted run.

---

### 13) Logging, metrics, and documentation requirements

#### 13.1 Logging

Use Python `logging` with:

* console output (human readable)
* file output (`train.log`)
* optional JSON lines (`train.jsonl`) for structured logs

Log at least:

* Stage transitions + config hash
* Stage 1:

  * files processed, offsets, total lines, pieces/sec
  * unique piece count, memory usage (if available)
* Stage 3 (per snapshot interval, not per merge):

  * merge index, best pair count, heap size, pair_count size
  * number of affected word types updated
  * snapshot write success, WAL position

**Do not log** raw text lines (privacy).

#### 13.2 Metrics file

Write `metrics.jsonl` with periodic samples:

* timestamp
* stage
* merge_index
* best_pair_count
* unique_pairs
* unique_word_types
* RSS memory (optional, via `psutil`)
* throughput indicators

#### 13.3 Documentation deliverables

* `README.md`:

  * how to run from scratch
  * how to resume
  * how to export artifacts
  * how to validate tokenizer behavior
* `CONFIG.md`: explanation of all config fields and recommended laptop defaults
* `CHECKPOINTING.md`: WAL + snapshot design and recovery guarantees

---

### 14) Export: building `vocab.json` and `merges.txt`

#### 14.1 Token string representation

Convert token bytes sequences to printable Unicode strings using `byte_to_unicode` mapping:

* For token bytes `tb = b"\x68\x69"`:

  * token_string = `byte_to_unicode[0x68] + byte_to_unicode[0x69]`

This yields tokens that can be keys in JSON.

#### 14.2 Token IDs

Recommended simple deterministic scheme:

* IDs `0..(256 + num_merges - 1)` correspond to:

  * base byte tokens then merged tokens in merge-creation order
* Append special tokens at end:

  * `<|endoftext|>` then `<|pad|>` etc.

Write:

* `vocab.json`: map each token_string to integer ID
* `merges.txt`: header + list of merges as token_string pairs in merge order

Also write:

* `tokenizer_config.json` containing:

  * `pattern`
  * `byte_to_unicode_version`
  * `special_tokens`
  * `vocab_size`
  * `num_merges`
  * `training_corpus_sha256` (optional; computed from file list + sizes + mtimes, or from content if feasible)

---

### 15) Validation and test plan (must-have)

#### 15.1 Unit tests

1. **Byte mapping round-trip**

   * For all bytes 0–255, mapping invertible.
2. **Pretokenizer determinism**

   * Fixed string tokenizes to fixed piece list.
3. **Single merge correctness**

   * Given a small synthetic vocab, applying merge updates words and pair counts correctly.
4. **WAL recovery**

   * Simulate WAL with missing COMMIT; ensure recovery ignores in-flight merge.
5. **Checkpoint atomicity**

   * Simulate partial write (write temp only); ensure loader uses previous snapshot.

#### 15.2 Integration tests

1. **End-to-end small corpus**

   * Train to small vocab_size (e.g., 300) on tiny corpus; export; verify artifacts load.
2. **Resume test**

   * Run training, forcibly terminate mid-merge (SIGKILL), restart, and verify identical final artifacts.
3. **Tokenizer losslessness (runtime test harness)**

   * Implement a minimal encode/decode using exported merges:

     * Ensure decode(encode(text)) == original text for a corpus sample.

---

### 16) Implementation notes and best practices for laptop efficiency

* **Use Python 3.11+** if possible (not a requirement, but materially faster dict/heap operations).
* **Parallelism only in Stage 1** (counting). Merge learning is heavily stateful; parallel updates are rarely worth complexity on a laptop.
* Avoid per-merge heavy logging; log per snapshot interval.
* Prune:

  * extremely long pieces
  * extremely rare pieces (with careful, deterministic thresholds)
  * cap word types to top-K by frequency for laptop feasibility
* Keep everything deterministic:

  * stable ordering when truncating to top-K (freq desc, then bytes lexicographic)
  * stable tie-breaking for best pair selection

---

### 17) Minimal pseudocode for critical components

#### 17.1 Merge selection (lazy heap)

```python
while heap:
    neg_count, a, b = heapq.heappop(heap)
    count = -neg_count
    if pair_count.get((a,b), 0) == count:
        best = (a,b,count)
        break
else:
    best = None
```

#### 17.2 Apply merge to one word + compute deltas

```python
def merge_word(word_syms, a, b, new_id):
    # returns new_syms, old_pair_occ, new_pair_occ
    old_pairs = count_adjacent_pairs(word_syms)
    new_syms = []
    i = 0
    while i < len(word_syms):
        if i+1 < len(word_syms) and word_syms[i] == a and word_syms[i+1] == b:
            new_syms.append(new_id)
            i += 2
        else:
            new_syms.append(word_syms[i])
            i += 1
    new_pairs = count_adjacent_pairs(new_syms)
    return new_syms, old_pairs, new_pairs
```

#### 17.3 WAL transaction

```python
write_line("BEGIN\tm\ta\tb\tcount\n"); flush(); fsync()
# apply merge to state
write_line("COMMIT\tm\tnew_id\n"); flush(); fsync()
```

---

## What the SWE team should implement first (recommended order)

1. Byte-to-unicode mapping + tests
2. Pretokenizer + tests
3. Stage 1 counting with checkpoints/resume
4. Stage 3 merge learning (single-process) + WAL + snapshot + resume
5. Export + tiny runtime encode/decode validator
6. Performance tuning + pruning knobs (top-K, min freqs)
