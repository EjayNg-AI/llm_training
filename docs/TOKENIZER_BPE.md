# GPT-2 Style UTF-8 Byte-Level BPE Tokenizer

This is the official tokenizer documentation for this repository.
It is both:

1. the implementation reference for the current codebase, and
2. the rebuild guide for teams that need to implement the same system from scratch.

The implementation is in:

- `scripts/03_train_tokenizer.py` (canonical stage entrypoint)
- `scripts/tokenizer_bpe/config.py`
- `scripts/tokenizer_bpe/pretokenizer.py`
- `scripts/tokenizer_bpe/stage1_count.py`
- `scripts/tokenizer_bpe/stage2_init.py`
- `scripts/tokenizer_bpe/stage3_train.py`
- `scripts/tokenizer_bpe/export.py`
- `scripts/tokenizer_bpe/byte_unicode.py`
- `scripts/tokenizer_bpe/io_atomic.py`
- `scripts/tokenizer_bpe/runtime_check.py` (training-time/runtime-check helper functions)
- `src/llm_training/tokenizer/runtime.py` (`ByteLevelBPETokenizer` runtime API used by downstream stages)
- `src/llm_training/tokenizer/special.py`

## Core Training Algorithm (Educational Walkthrough)

This section is the shortest path to understanding what must be implemented to reproduce this tokenizer.

At a high level, training is:

1. Normalize each line if configured, strip configured special-token literals, then split remaining text into regex pieces and count piece byte strings.
2. Initialize BPE state from those counts using byte IDs (`0..255`) as the base symbols.
3. Repeatedly merge the highest-frequency adjacent symbol pair.
4. Export vocab/merge artifacts and append special tokens at export time.

### 1) Vocabulary initialization + pretokenization

Training is byte-level. The base vocabulary is always the 256 single-byte tokens:

```python
id_to_token_bytes = [bytes([b]) for b in range(256)]
```

Stage 1 reads corpus lines, optionally normalizes per line, removes configured special-token literals, applies GPT-2 style regex pretokenization to the remaining text, and counts UTF-8 piece bytes:

```python
if normalize_mode != "none":
    line = unicodedata.normalize(normalize_mode, line)
for segment in split_around_special_tokens(line):
    for match in compiled_pattern.finditer(segment):
        piece = match.group(0)
        piece_counts[piece.encode("utf-8")] += 1
```

For independent implementations, this is a key contract:

1. Counted unit is piece UTF-8 bytes (not Unicode codepoints).
2. Regex matching and normalization order must match training exactly.
3. Configured special-token strings must be matched literally with escaping and ordered longest-first before splitting, so overlapping tokens do not partially consume each other.
4. Deterministic Stage 1 progress/resume behavior depends on applying completed worker results in contiguous `batch_id` order.

### 2) Build initial BPE training state

After Stage 1 capping, Stage 2 builds word types and frequencies:

```python
# pseudo-shape
inventory = sorted(piece_counts.items(), key=lambda kv: (-kv[1], kv[0]))
words = [array(word_storage_type, list(piece_bytes)) for piece_bytes, _ in inventory]
freqs = array("Q", (freq for _, freq in inventory))
```

Interpretation:

1. Each unique pretokenized piece becomes one word type (`words[idx]`).
2. `freqs[idx]` is how often that piece appeared in the corpus.
3. Merge learning operates over these weighted word types, not raw document text.

### 3) How BPE merges are computed

Core counting uses weighted adjacent pairs:

```python
pair_id = (a << 32) | b
pair_count[pair_id] += freqs[word_idx] * occurrences_of_pair_in_word
```

Best-pair selection is deterministic with heap tuples `(-count, pair_id)`:

```python
neg_count, pair_id = heapq.heappop(heap)
# max frequency first; ties resolved lexicographically by (a, b) encoded in pair_id
```

Merge application loop (conceptually):

```python
new_id = len(id_to_token_bytes)
id_to_token_bytes.append(id_to_token_bytes[a] + id_to_token_bytes[b])
pair_id = (a << 32) | b
for word_idx in pair_to_words[pair_id]:
    old_pairs = count_adjacent_pairs(words[word_idx])
    words[word_idx] = merge_symbols(words[word_idx], a, b, new_id, word_storage_type)
    new_pairs = count_adjacent_pairs(words[word_idx])
    apply_weighted_deltas(old_pairs, new_pairs, freqs[word_idx])
```

Implementation notes for SWE teams:

1. Pair counts are maintained incrementally (not fully recomputed each merge).
2. `pair_to_words` uses append-light updates plus duplicate/stale filtering; merged-pair lists are deleted after each merge.
3. Trainer stops when no valid pair remains, `best_count < min_merge_freq`, or merge target is reached.

### 4) Special tokens

Special tokens are intentionally excluded from merge learning state. They are added only during export, and literal occurrences in training text are stripped in Stage 1 before regex pretokenization:

1. `placement = "start"`: specials get lowest IDs, learned tokens are shifted.
2. `placement = "end"`: learned tokens keep IDs, specials are appended.
3. Export prefers explicit `<bos>`, `<eos>`, `<unk>`, and `<pad>` entries for `special_tokens_map.json` when they are present; otherwise it falls back to legacy `<|endoftext|>` / `<|pad|>` or positional defaults.

Any collision between special-token strings and learned token strings is a hard error.

### 5) Final output artifacts

Training/export produces:

1. `vocab.json`: token string -> token ID.
2. `merges.txt`: merge order (`#version: 0.2` + token-string pairs).
3. `tokenizer_config.json`: regex pattern/flags, hashes, and tokenizer metadata.
4. `special_tokens_map.json`: BOS/EOS/UNK/PAD mapping.
5. `training_stats.json`: merge count, corpus/config hashes, and run metadata.

For exact reproducibility, implementers should treat merge order (`merges.txt`) and ID assignment (`vocab.json` + special placement) as the canonical tokenizer function.

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
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe.yaml
```

Resume:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe.yaml --resume --run-id <run_id>
```

Key CLI options:

1. `--run-id` pins a run directory under `run.output_dir`.
2. `--stop-after-merges` is a debug/recovery test knob.
3. `--artifact-id` controls the published artifact ID under `artifacts/tokenizer/exports/`.
4. `--max-unique-pieces` overrides `data.max_unique_pieces` for a single run.
5. `--max-word-types` overrides `bpe.max_word_types` for a single run.

Run directory structure:

- `checkpoints/word_counts.snapshot.pkl`
- `checkpoints/word_counts.progress.json`
- `merges.wal`
- `wal.meta.json`
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
- `artifact_manifest.json`

Published tokenizer exports are now registered in:

- `artifacts/registry.jsonl`

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
  max_unique_pieces: 3500000

pretokenizer:
  pattern: "gpt2_fast"
  custom_pattern: null
  flags: []

bpe:
  vocab_size: 64000
  min_merge_freq: 2
  max_merges: null
  max_word_types: 3000000
  max_piece_bytes: 200
  tie_break: "lexicographic"

special_tokens:
  tokens:
    - "<|endoftext|>"
    - "</s>"
    - "<eos>"
    - "<s>"
    - "<bos>"
    - "<pad>"
    - "<unk>"
    - "<|system|>"
    - "<|user|>"
    - "<|assistant|>"
    - "<|im_start|>"
    - "<|im_end|>"
    - "<|endofmessage|>"
    - "<|sep|>"
    - "<|summarize|>"
    - "<|translate|>"
    - "<|code|>"
    - "<mask>"
    - "<fim_prefix>"
    - "<fim_middle>"
    - "<fim_suffix>"
    - "<|title|>"
    - "<|url|>"
    - "<|date|>"
    - "<|tool|>"
    - "<|function_call|>"
  placement: "end"

checkpointing:
  wal_fsync_each_commit: false
  wal_fsync_every_commits: 250
  snapshot_every_merges: 2000
  snapshot_every_seconds: 300
  keep_last_snapshots: 3
  stage1_snapshot_every_batches: 500
```

Default policy:

1. `data.max_bytes` and `data.max_lines` are unlimited by default (`null`).
2. `bpe.max_merges` is unlimited as an explicit cap by default (`null`), so target merges are derived from `vocab_size`.
3. `data.max_unique_pieces` defaults to `3500000`, `bpe.max_word_types` defaults to `3000000`, and `bpe.vocab_size` defaults to `64000`.

Validation rules currently enforced:

1. `data.input_format` in `{text, jsonl}`.
2. `data.decode_errors` in `{strict, replace, ignore}`.
3. `data.normalize` in `{none, NFC, NFKC}`.
4. `special_tokens.placement` in `{start, end}`.
5. `bpe.tie_break` must be `lexicographic`.
6. `data.num_workers >= 1`, `data.batch_lines >= 1`, `bpe.vocab_size >= 256`.
7. `data.max_bytes >= 0` when provided.
8. `data.max_lines >= 0` when provided.
9. `data.max_unique_pieces > 0` when provided.
10. `bpe.max_merges >= 0` when provided.
11. `bpe.max_word_types > 0`.
12. `checkpointing.wal_fsync_every_commits >= 0`.

Determinism hashes:

1. `config_hash` = SHA-256 of canonicalized merged config.
2. `pattern_hash` = SHA-256 of:
   - resolved regex string
   - regex flags
   - normalization mode
   - `regex` package version

`config_hash` canonicalization contract (normative):

1. Start from the merged effective config (defaults deep-merged with user config, then CLI overrides when used).
2. Do not include runtime-added `meta` keys in the hashed payload.
3. Serialize with `json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
4. Encode JSON as UTF-8 and hash with SHA-256.
5. Preserve list order as provided; do not reorder arrays.

Normative hash example:

```json
{"a":1,"b":["x",2],"c":{"k":"v","n":null}}
```

SHA-256:

```text
8e0238f8ecb010dd664f0e02608ee89bbe9429d4ce197b034f64c451a80d04b7
```

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

### 6.1 Normalization contract

Normalization is configured by `data.normalize` and is applied only in Stage 1 workers.

Normative order for each training input line:

1. Main process decodes bytes to text (`decode_errors` policy).
2. For `jsonl`, main process parses JSON and extracts `jsonl_text_field` if it is a string.
3. Worker receives decoded/extracted text.
4. Worker applies `unicodedata.normalize(normalize_mode, line)` if mode is not `none`.
5. Worker splits the normalized line around configured special-token literals and discards the matched substrings.
6. Worker runs regex pretokenization over the remaining segments and counts piece UTF-8 bytes.

Runtime contract:

1. `ByteLevelBPETokenizer.encode` does not apply Unicode normalization.
2. Normalization therefore affects merge learning statistics, not runtime input transformation.
3. `decode(encode(x)) == x` is expected for valid UTF-8 input text encoded by runtime (special-token skipping disabled).

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

The counted object is the pretokenized piece encoded as bytes after configured special-token substrings have been removed from the normalized line:

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
6. Workers normalize each received line (if configured), split around configured special-token literals, pretokenize only non-special segments, and return `Counter[bytes]` + local piece count.
7. Main process merges worker counters.

Worker init:

```python
def _worker_init(pattern_str, pattern_flags, normalize, max_piece_bytes, special_tokens):
    _WORKER_PATTERN = compile_pattern(pattern_str, pattern_flags)
    _WORKER_NORMALIZE = normalize
    _WORKER_MAX_PIECE_BYTES = max_piece_bytes
    _WORKER_SPECIAL_SPLIT_RE = _compile_special_token_splitter(special_tokens, normalize)
```

Main loop details:

1. Maintains a bounded pending future map (up to `num_workers`).
2. Each submitted batch is assigned a monotonically increasing `batch_id` and records its `end_offset`.
3. Workers are consumed as-completed (`wait(..., FIRST_COMPLETED)`) and buffered by `batch_id`.
4. Main process applies only the next contiguous completed batch (`next_batch_to_merge`) to preserve determinism.
5. `byte_offset` advances only when that contiguous batch is merged.
6. Progress therefore advances only for the contiguous merged prefix of each file.
7. `end_offset` is captured from `f.tell()` immediately after consuming whole lines via `readline()`, so checkpointed offsets are line-boundary aligned.

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

Offset and byte semantics (normative):

1. For `.txt` / `.jsonl`, `byte_offset` is the offset in the raw file stream.
2. For `.txt.gz` / `.jsonl.gz`, files are opened with `gzip.open(path, "rb")` and `byte_offset` is in the decompressed stream (`GzipFile.tell()` / `seek()` domain).
3. Resume seeks with `f.seek(byte_offset)` in that same stream domain; for gzip this can be linear-time in offset.
4. `total_bytes_processed` is incremented by `len(raw_line)` from the opened stream; for gzip this is decompressed bytes read, not compressed on-disk bytes.

### 7.5 Stage 1 pruning and memory control

Pruning logic:

1. Every 100 merged batches (after at least 10,000 lines), optionally cap in-memory counter.
2. Enforce `data.max_unique_pieces` using deterministic top-K:
   - sort key: frequency descending, bytes lexicographic ascending.
3. `data.min_piece_freq` is applied once in Stage 2 (not during Stage 1 streaming).

Final Stage 1 output:

1. capped `Counter[bytes]` (if `max_unique_pieces` is set)
2. metadata with `training_corpus_sha256` computed from sorted file path + file size + mtime_ns.

## 8) Stage 2: training state initialization

Module: `scripts/tokenizer_bpe/stage2_init.py`

Input: `piece_counts: Counter[bytes]`.

Process:

1. Filter by `data.min_piece_freq`.
2. Sort by `(-freq, piece_bytes)`.
3. Cap to `bpe.max_word_types`.
4. Build:
   - `words`: list of dense integer arrays (`array('H')` when max symbol ID fits in 16 bits, else `array('I')`).
   - `freqs`: `array('Q')` aligned to `words`.
   - `id_to_token_bytes`: initial `[bytes([0]), ..., bytes([255])]`.
   - `word_storage_type`: `'H'` or `'I'`.

Important: special tokens are not part of merge learning state.

## 9) Stage 3: merge learning with WAL + snapshots

Module: `scripts/tokenizer_bpe/stage3_train.py`

### 9.1 Core state

Main mutable training state:

1. `words: list[array]` (`array('H')` or `array('I')`)
2. `freqs: array('Q')`
3. `id_to_token_bytes: list[bytes]`
4. `merge_pairs: list[tuple[int, int]]`

Pair index structures:

1. `pair_id = (a << 32) | b`
2. `pair_count[pair_id] -> weighted frequency`
3. `pair_to_words[pair_id] -> list[word_idx]` (merged pair list removed after use; stale entries are lazily deduped at merge time)
4. max-heap entries `(-count, pair_id)` for deterministic best-pair selection

Weighted pair count definition:

`pair_count[pair_id] = sum(freq[word_idx] * occurrences_of_pair_in_word)`

Initial construction contract:

1. For each word type `words[idx]`, compute local adjacent-pair multiplicities with `count_adjacent_pairs`.
2. For each local pair `pair_id` with local count `occ`, add `freqs[idx] * occ` to `pair_count[pair_id]`.
3. Append `idx` to `pair_to_words[pair_id]` once for that word during initial build, even if `occ > 1`.
4. During later incremental updates, merge step deduplicates candidate indices with `seen_word_indices`.
5. If a pair's global count drops to non-positive, remove it from both `pair_count` and `pair_to_words`.

### 9.2 Target merge count

If `bpe.max_merges` is set, it is used directly (and must be non-negative; config validation rejects negative values).
Otherwise:

`target_merges = max(0, bpe.vocab_size - 256 - len(special_tokens))`

Edge case:

If `bpe.vocab_size < 256 + len(special_tokens)`, Stage 3 can perform zero merges, but export still includes all 256 byte tokens plus all configured special tokens.

### 9.3 Best-pair selection

Lazy heap pop:

```python
while heap:
    neg_count, pair_id = heapq.heappop(heap)
    count = -neg_count
    if pair_count.get(pair_id, 0) == count:
        a = pair_id >> 32
        b = pair_id & ((1 << 32) - 1)
        return a, b, count
return None
```

Tie-break behavior is deterministic because heap tuples are ordered as `(-count, pair_id)`.
Tie-break domain is integer token IDs `(a, b)` encoded in `pair_id`, not token strings.

### 9.4 Merge transaction flow

Each merge executes as:

1. Select best pair `(a, b, best_count)`.
2. Stop if no candidate or `best_count < bpe.min_merge_freq`.
3. Append WAL `BEGIN`.
4. Create `new_id = len(id_to_token_bytes)` and append merged bytes.
5. Update only candidate words from `pair_to_words[pair_id]`, then delete that merged pair list.
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
8. append word index to `pair_to_words` only for pairs newly introduced in that word (`new_pairs - old_pairs`).
9. occasionally rebuild heap when `len(heap)` grows too large relative to `len(pair_count)`.

Core transformation:

```python
def merge_symbols(symbols, a, b, new_id, word_storage_type):
    merged = array(word_storage_type)
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
8. `word_storage_type`

Snapshot files are checksum-protected (`.sha256`) and old snapshots are pruned to `keep_last_snapshots`.

Additional state output:

1. `state.json` (compact human-readable progress)
2. `metrics.jsonl` (timestamped structured metrics samples)

### 9.7 Resume algorithm

Resume uses this order:

1. load latest valid snapshot matching `config_hash` and `pattern_hash`.
2. validate `wal.meta.json` hash binding (`config_hash`, `pattern_hash`) when present.
3. parse WAL commits (`BEGIN`+`COMMIT` matched by merge index).
4. replay committed WAL merges beyond snapshot merge index.
5. rebuild `pair_count`, `pair_to_words`, and heap from replayed `words`.

WAL replay safety checks:

1. ignores in-flight BEGIN records without COMMIT.
2. enforces `wal_new_id == len(id_to_token_bytes)` at each replayed merge.
3. enforces contiguous replay indices (`last_merge + 1`, no gaps/duplicates after snapshot boundary).
4. enforces that each replayed merge updates at least one word type (detects divergent state/WAL).
5. if no compatible snapshot exists, replay from WAL requires valid `wal.meta.json`; otherwise resume fails fast.

Durability model:

1. WAL is append-only.
2. A merge is durable only after COMMIT line is written.
3. If `checkpointing.wal_fsync_each_commit` is true, WAL is fsync'd after each committed merge (paranoid mode).
4. Otherwise WAL is fsync'd every `checkpointing.wal_fsync_every_commits` commits when that value is greater than zero.
5. WAL is also fsync'd before snapshot writes and at trainer shutdown when pending commits exist.

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

## 11) Runtime behavior

Runtime implementations:

1. `scripts/tokenizer_bpe/runtime_check.py` (minimal helper functions used by tests).
2. `src/llm_training/tokenizer/runtime.py` (stage runtime class).
3. `src/llm_training/tokenizer/special.py` (special token ID mapping).

Primary runtime API:

```python
from llm_training.tokenizer import ByteLevelBPETokenizer

tok = ByteLevelBPETokenizer.from_dir("artifacts/tokenizer/exports/<tokenizer_id>")
ids = tok.encode("some text")
text = tok.decode(ids)
```

Runtime helpers include:

1. merge rank table construction from `merge_pairs`.
2. piece-level greedy BPE application by best-rank pair.
3. decode by concatenating token bytes and UTF-8 decoding.

Runtime contract (normative):

1. Runtime pretokenization uses exported `pattern` and `pattern_flags` from `tokenizer_config.json`.
2. Each pretokenized piece starts as single-byte symbols: `[bytes([b]) for b in piece.encode("utf-8")]`.
3. Merge application is greedy by smallest merge rank from `merges.txt` order.
4. Final symbol-to-ID mapping uses `token_bytes_to_id` built from `vocab.json`; runtime must not assume base-byte IDs are `0..255`.
5. Runtime `encode` treats input as plain text only; special-token strings are not recognized as atomic spans.
6. Runtime `decode` concatenates token bytes and UTF-8 decodes with `errors="replace"`.

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
2. deterministic Stage 1 top-K capping tie-break (frequency desc, bytes asc).
3. deterministic pair selection tie-break (`(-count, pair_id)` where `pair_id` encodes `(a, b)`).
4. deterministic Stage 2 inventory sorting.
5. hash-gated checkpoint/snapshot reuse.

Performance strategy:

1. parallelize Stage 1 only (CPU-friendly and low coupling).
2. keep Stage 3 single-process with compact integer arrays and packed pair IDs.
3. use lazy invalidation plus heap rebuild and merged-pair list cleanup to limit stale growth.
4. expose practical caps:
   - `max_piece_bytes`
   - `min_piece_freq` (applied in Stage 2)
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
