# GPT-2 Style UTF-8 Byte-Level BPE Tokenizer

This is the official tokenizer documentation for this repository.
It is both:

1. the implementation reference for the current codebase, and
2. the rebuild guide for teams that need to implement the same system from scratch.

The implementation is in:

- `scripts/02_train_tokenizer.py`
- `scripts/tokenizer_bpe/config.py`
- `scripts/tokenizer_bpe/pretokenizer.py`
- `scripts/tokenizer_bpe/stage1_count.py`
- `scripts/tokenizer_bpe/stage2_init.py`
- `scripts/tokenizer_bpe/stage3_train.py`
- `scripts/tokenizer_bpe/export.py`
- `scripts/tokenizer_bpe/byte_unicode.py`
- `scripts/tokenizer_bpe/io_atomic.py`
- `scripts/tokenizer_bpe/runtime_check.py`

## 1) Scope and goals

Goal: train a deterministic, resumable, laptop-runnable GPT-2 style UTF-8 byte-level BPE tokenizer in pure Python.

Required properties:

1. Byte-level and lossless over UTF-8.
2. GPT-2 style regex pretokenization with leading-space behavior.
3. Deterministic outputs for fixed corpus + config.
4. Crash-safe resume semantics.
5. Operationally practical on CPU laptops.

Explicit non-goals:

1. Exact parity with OpenAI internal token IDs.
2. GPU-accelerated merge learning.
3. Multi-language tokenizer runtime in this scaffold phase.

## 2) Entrypoint and run model

Train:

```bash
python scripts/02_train_tokenizer.py --config configs/tokenizer_bpe.yaml
```

Resume:

```bash
python scripts/02_train_tokenizer.py --config configs/tokenizer_bpe.yaml --resume --run-id <run_id>
```

Key CLI options:

1. `--run-id` pins a run directory under `run.output_dir`.
2. `--stop-after-merges` is a debug/recovery test knob.
3. `--export-dir` controls output tokenizer artifact location.

Run directory structure:

- `checkpoints/word_counts.snapshot.pkl`
- `checkpoints/word_counts.progress.json`
- `merges.wal`
- `snapshots/state.mXXXXXXXX.pkl` (+ `.sha256`)
- `state.json`
- `metrics.jsonl`
- `train.log`
- `train.jsonl` (if structured logs enabled)

Export directory structure:

- `vocab.json`
- `merges.txt`
- `tokenizer_config.json`
- `special_tokens_map.json`
- `training_stats.json`

## 3) Pipeline overview

High-level flow:

1. Stage 1: pretokenize corpus and count piece byte strings in parallel.
2. Stage 2: convert piece counts to word-type symbol sequences (`0..255`).
3. Stage 3: iteratively learn BPE merges with WAL + snapshots.
4. Stage 4: export tokenizer artifacts.

ASCII data flow:

```text
Raw text/jsonl (+ optional .gz)
  |
  v
Stage 1: regex pretokenize -> Counter[bytes]
  |
  v
Stage 2: words/freqs/id_to_token_bytes init
  |
  v
Stage 3: merge loop + WAL + snapshots
  |
  v
Stage 4: vocab.json + merges.txt + tokenizer_config.json
```

## 4) Configuration contract

Config source:

- `configs/tokenizer_bpe.yaml`
- defaults merged from `scripts/tokenizer_bpe/config.py`

Default configuration:

```yaml
run:
  output_dir: "artifacts/tokenizer/runs"
  seed: 0
  log_level: "INFO"
  structured_logs: true

data:
  input_paths:
    - "data/raw/train.txt"
  input_format: "text"
  jsonl_text_field: "text"
  decode_errors: "replace"
  normalize: "none"
  max_bytes: null
  max_lines: null
  num_workers: 4
  batch_lines: 2000
  min_piece_freq: 2
  max_unique_pieces: 2000000

pretokenizer:
  pattern: "gpt2_fast"
  custom_pattern: null
  flags: []

bpe:
  vocab_size: 50000
  min_merge_freq: 2
  max_merges: null
  max_word_types: 1500000
  max_piece_bytes: 200
  tie_break: "lexicographic"

special_tokens:
  tokens:
    - "<|endoftext|>"
    - "<|pad|>"
  placement: "end"

checkpointing:
  wal_fsync_each_commit: true
  snapshot_every_merges: 200
  snapshot_every_seconds: 300
  keep_last_snapshots: 3
  stage1_snapshot_every_batches: 50
```

Validation rules currently enforced:

1. `data.input_format` in `{text, jsonl}`.
2. `data.decode_errors` in `{strict, replace, ignore}`.
3. `data.normalize` in `{none, NFC, NFKC}`.
4. `special_tokens.placement` in `{start, end}`.
5. `bpe.tie_break` must be `lexicographic`.
6. `data.num_workers >= 1`, `data.batch_lines >= 1`, `bpe.vocab_size >= 256`.

Determinism hashes:

1. `config_hash` = SHA-256 of canonicalized merged config.
2. `pattern_hash` = SHA-256 of:
   - resolved regex string
   - regex flags
   - normalization mode
   - `regex` package version

## 5) Byte-to-unicode mapping

Module: `scripts/tokenizer_bpe/byte_unicode.py`

Purpose: represent arbitrary byte tokens as reversible printable-ish Unicode strings for JSON and text artifacts.

Algorithm (GPT-2 compatible):

```python
bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
cs = bs[:]
n = 0
for b in range(256):
    if b not in bs:
        bs.append(b)
        cs.append(256 + n)
        n += 1
```

Contracts:

1. `unicode_to_byte[byte_to_unicode[b]] == b` for all `b in 0..255`.
2. `token_bytes_to_string` and `token_string_to_bytes` are exact inverses.

## 6) Pretokenization

Module: `scripts/tokenizer_bpe/pretokenizer.py`

Uses third-party `regex` (not `re`) for Unicode classes like `\p{L}` and `\p{N}`.

Pattern aliases:

```python
PATTERN_ALIASES = {
    "gpt2_default": r"'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+",
    "gpt2_fast": r"'(?:[sdmt]|ll|ve|re)| ?\p{L}++| ?\p{N}++| ?[^\s\p{L}\p{N}]++|\s++$|\s+(?!\S)|\s",
}
```

`gpt2_fast` is the default in config. `gpt2_default` is kept for canonical GPT-2 pattern compatibility.

Supported flags via config:

1. `IGNORECASE`
2. `MULTILINE`

Matching API:

```python
for match in compiled_pattern.finditer(text):
    yield match.group(0)
```

Behavioral note: alternatives beginning with ` ?` intentionally preserve leading-space token behavior.

## 7) Stage 1: parallel piece counting

Module: `scripts/tokenizer_bpe/stage1_count.py`

### 7.1 Inputs and file discovery

Supported file extensions:

1. `text`: `.txt`, `.txt.gz`
2. `jsonl`: `.jsonl`, `.jsonl.gz`

Discovery is deterministic:

1. recurse directories with `sorted(path.rglob("*"))`
2. convert to resolved absolute paths
3. deduplicate and sort again

### 7.2 Counting unit

The counted object is the pretokenized piece encoded as bytes:

```python
piece_bytes = piece.encode("utf-8")
piece_counts[piece_bytes] += 1
```

Pieces longer than `bpe.max_piece_bytes` are dropped in workers.

### 7.3 Parallelization model

Stage 1 is where parallelism is applied.

Architecture:

1. Main process reads files in binary mode and tracks byte offsets.
2. Lines are decoded with configured `decode_errors`.
3. For JSONL, each line is parsed and `jsonl_text_field` is extracted if it is a string.
4. Main process submits decoded line batches to `ProcessPoolExecutor`.
5. Worker processes run `_worker_init` once to compile regex and load normalization config.
6. Workers return `Counter[bytes]` + local piece count.
7. Main process merges worker counters.

Worker init:

```python
def _worker_init(pattern_str, pattern_flags, normalize, max_piece_bytes):
    _WORKER_PATTERN = compile_pattern(pattern_str, pattern_flags)
    _WORKER_NORMALIZE = normalize
    _WORKER_MAX_PIECE_BYTES = max_piece_bytes
```

Main loop details:

1. Maintains a bounded pending queue of futures (up to `num_workers`).
2. Each queue item records `end_offset`, line count, and byte count metadata.
3. File progress updates when a future resolves.

### 7.4 Stage 1 checkpointing and resume

Files:

1. `checkpoints/word_counts.snapshot.pkl`
2. `checkpoints/word_counts.progress.json`

Progress payload includes:

1. per-file `{path, byte_offset, done}`
2. `total_lines_processed`
3. `total_pieces_seen`
4. `total_bytes_processed`
5. `config_hash`
6. `pattern_hash`
7. `snapshot_id`
8. `timestamp`

Write semantics use atomic replace via `scripts/tokenizer_bpe/io_atomic.py`:

1. write temp file
2. flush + fsync temp
3. `os.replace(tmp, final)`
4. best-effort directory fsync

Resume gate:

1. Stage 1 checkpoint is accepted only if both `config_hash` and `pattern_hash` match.

### 7.5 Stage 1 pruning and memory control

Pruning logic:

1. Every 100 merged batches (after at least 10,000 lines), prune in-memory counter.
2. Remove entries below `data.min_piece_freq` if > 1.
3. Enforce `data.max_unique_pieces` using deterministic top-K:
   - sort key: frequency descending, bytes lexicographic ascending.

Final Stage 1 output:

1. pruned `Counter[bytes]`
2. metadata with `training_corpus_sha256` computed from sorted file path + file size + mtime_ns.

## 8) Stage 2: training state initialization

Module: `scripts/tokenizer_bpe/stage2_init.py`

Input: `piece_counts: Counter[bytes]`.

Process:

1. Filter by `data.min_piece_freq`.
2. Sort by `(-freq, piece_bytes)`.
3. Cap to `bpe.max_word_types`.
4. Build:
   - `words`: `list[list[int]]` where each piece bytestring becomes byte IDs.
   - `freqs`: frequency list aligned to `words`.
   - `id_to_token_bytes`: initial `[bytes([0]), ..., bytes([255])]`.

Important: special tokens are not part of merge learning state.

## 9) Stage 3: merge learning with WAL + snapshots

Module: `scripts/tokenizer_bpe/stage3_train.py`

### 9.1 Core state

Main mutable training state:

1. `words: list[list[int]]`
2. `freqs: list[int]`
3. `id_to_token_bytes: list[bytes]`
4. `merge_pairs: list[tuple[int, int]]`

Pair index structures:

1. `pair_count[(a, b)] -> weighted frequency`
2. `pair_to_words[(a, b)] -> list[word_idx]` (lazy, append-only)
3. max-heap entries `(-count, a, b)` for deterministic best-pair selection

Weighted pair count definition:

`pair_count[(a, b)] = sum(freq[word_idx] * occurrences_of_pair_in_word)`

### 9.2 Target merge count

If `bpe.max_merges` is set, it is used directly.
Otherwise:

`target_merges = max(0, bpe.vocab_size - 256 - len(special_tokens))`

### 9.3 Best-pair selection

Lazy heap pop:

```python
while heap:
    neg_count, a, b = heapq.heappop(heap)
    count = -neg_count
    if pair_count.get((a, b), 0) == count:
        return a, b, count
return None
```

Tie-break behavior is deterministic because heap tuples are ordered as `(-count, a, b)`.

### 9.4 Merge transaction flow

Each merge executes as:

1. Select best pair `(a, b, best_count)`.
2. Stop if no candidate or `best_count < bpe.min_merge_freq`.
3. Append WAL `BEGIN`.
4. Create `new_id = len(id_to_token_bytes)` and append merged bytes.
5. Update only candidate words from `pair_to_words[(a, b)]`.
6. Append WAL `COMMIT`.
7. Periodically write snapshot/state/metrics.

WAL format:

```text
BEGIN\t<merge_index>\t<a>\t<b>\t<best_count>
COMMIT\t<merge_index>\t<new_id>
```

### 9.5 Incremental update algorithm

For each candidate word:

1. skip duplicate/stale word indices via `seen_word_indices`.
2. verify pair still exists (`contains_pair`).
3. count local old pairs.
4. merge all adjacent `a,b` into `new_id`.
5. count local new pairs.
6. apply pair deltas weighted by `freqs[word_idx]`.
7. push updated pair counts to heap.
8. append word index to `pair_to_words` for all pairs now present.

Core transformation:

```python
def merge_symbols(symbols, a, b, new_id):
    merged = []
    i = 0
    while i < len(symbols):
        if i + 1 < len(symbols) and symbols[i] == a and symbols[i + 1] == b:
            merged.append(new_id)
            i += 2
        else:
            merged.append(symbols[i])
            i += 1
    return merged
```

### 9.6 Snapshotting, metrics, and state files

Periodic trigger:

1. every `checkpointing.snapshot_every_merges`, or
2. every `checkpointing.snapshot_every_seconds`

Snapshot payload:

1. `words`
2. `freqs`
3. `id_to_token_bytes`
4. `merge_pairs`
5. `last_merge`
6. `config_hash`
7. `pattern_hash`

Snapshot files are checksum-protected (`.sha256`) and old snapshots are pruned to `keep_last_snapshots`.

Additional state output:

1. `state.json` (compact human-readable progress)
2. `metrics.jsonl` (timestamped structured metrics samples)

### 9.7 Resume algorithm

Resume uses this order:

1. load latest valid snapshot matching `config_hash` and `pattern_hash`.
2. parse WAL commits (`BEGIN`+`COMMIT` matched by merge index).
3. replay committed WAL merges beyond snapshot merge index.
4. rebuild `pair_count`, `pair_to_words`, and heap from replayed `words`.

WAL replay safety checks:

1. ignores in-flight BEGIN records without COMMIT.
2. enforces `wal_new_id == len(id_to_token_bytes)` at each replayed merge.

Durability model:

1. WAL is append-only.
2. A merge is durable only after COMMIT line is written.
3. If `checkpointing.wal_fsync_each_commit` is true, each BEGIN/COMMIT write is fsync'd.

## 10) Export contract

Module: `scripts/tokenizer_bpe/export.py`

### 10.1 Vocab ID policy

Base learned token strings are generated from `id_to_token_bytes` and byte-to-unicode mapping.

ID assignment:

1. if `special_tokens.placement == "start"`:
   - special tokens first, then base/merged tokens.
2. else (`end`):
   - base/merged tokens first, then special tokens.

All collisions are rejected with explicit `ValueError`.

### 10.2 `merges.txt` format

```text
#version: 0.2
<tok_a_0> <tok_b_0>
<tok_a_1> <tok_b_1>
...
```

Each merge pair uses the byte-to-unicode token string representation.

### 10.3 `tokenizer_config.json` fields

Current exported fields include:

1. `tokenizer_class`
2. `add_prefix_space`
3. `model_max_length`
4. `pattern_alias`
5. `pattern`
6. `pattern_flags`
7. `pattern_hash`
8. `byte_to_unicode_version`
9. `special_tokens`
10. `vocab_size`
11. `num_merges`
12. `training_corpus_sha256`
13. `config_hash`
14. `bos_token`, `eos_token`, `unk_token`, `pad_token` (from special token mapping rules)

Also exported:

1. `special_tokens_map.json`
2. `training_stats.json`
3. run-local `export_manifest.json`

## 11) Minimal runtime behavior (losslessness harness)

Module: `scripts/tokenizer_bpe/runtime_check.py`

Runtime helpers include:

1. merge rank table construction from `merge_pairs`.
2. piece-level greedy BPE application by best-rank pair.
3. decode by concatenating token bytes and UTF-8 decoding.

Core encode loop:

```python
while len(symbols) > 1:
    best_rank = None
    best_pair = None
    for i in range(len(symbols) - 1):
        pair = (symbols[i], symbols[i + 1])
        rank = merge_ranks.get(pair)
        if rank is None:
            continue
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_pair = pair
    if best_pair is None:
        break
    ...
```

## 12) Determinism and performance characteristics

Determinism levers implemented:

1. deterministic file discovery and sorting.
2. deterministic counter pruning/top-K tie-break.
3. deterministic pair selection tie-break (`(-count, a, b)`).
4. deterministic Stage 2 inventory sorting.
5. hash-gated checkpoint/snapshot reuse.

Performance strategy:

1. parallelize Stage 1 only (CPU-friendly and low coupling).
2. keep Stage 3 single-process with incremental data structures.
3. use lazy invalidation for `pair_to_words` and heap staleness.
4. expose practical caps:
   - `max_piece_bytes`
   - `min_piece_freq`
   - `max_unique_pieces`
   - `max_word_types`

## 13) Validation and test coverage

Primary tokenizer tests:

1. `tests/tokenizer_bpe/test_config.py`
2. `tests/tokenizer_bpe/test_byte_unicode.py`
3. `tests/tokenizer_bpe/test_pretokenizer.py`
4. `tests/tokenizer_bpe/test_stage1_count_unit.py`
5. `tests/tokenizer_bpe/test_stage2_init.py`
6. `tests/tokenizer_bpe/test_stage3_core.py`
7. `tests/tokenizer_bpe/test_stage3_recovery.py`
8. `tests/tokenizer_bpe/test_export.py`
9. `tests/tokenizer_bpe/test_runtime_check.py`
10. `tests/tokenizer_bpe/test_train_tokenizer_determinism.py`
11. `tests/tokenizer_bpe/test_train_tokenizer_resume.py`

Test commands:

```bash
python -m pytest -q tests/tokenizer_bpe
python -m pytest -q tests/tokenizer_bpe -m "not integration"
```

## 14) Rebuild checklist for SWE teams

If you are rebuilding independently, implement in this order:

1. Config loader + canonical hash functions.
2. Byte-to-unicode reversible mapping.
3. Regex pretokenizer aliases/flags with `regex` package.
4. Stage 1 parallel piece counting with resumable progress by file offset.
5. Stage 2 deterministic word-type inventory initialization.
6. Stage 3 incremental merge trainer with:
   - `pair_count`
   - `pair_to_words`
   - lazy heap validation
   - WAL BEGIN/COMMIT
   - periodic snapshots + checksum
7. Exporters for vocab/merges/config/stats.
8. Runtime encode/decode harness and full determinism/resume tests.

If the rebuilt system follows the contracts in this document, teams should produce equivalent algorithmic behavior and recoverability semantics for GPT-2 style byte-level BPE training.
