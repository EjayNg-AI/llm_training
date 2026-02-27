## GOAL

To determine whether our current **Byte Pair Encoding (BPE)** trainer will scale to a 100+GB text  corpus and whether our current caps `max_unique_pieces` (Stage 1) and `max_word_types` (Stage 2) are “just PoC” vs “productive-grade enough”.

---

## 1) Environment + config (for reproducibility and scaling projection)

Capture these once:

* Machine: RAM size, CPU model, OS/WSL or native
* Python version
* `regex` package version (since it affects pretokenization behavior/perf)
* Your tokenizer config fields that affect scale:

  * `min_piece_freq`, `max_unique_pieces`, `max_word_types`, `max_piece_bytes`
  * `vocab_size`, `min_merge_freq`, `max_merges`
  * `num_workers`, `batch_lines`
  * checkpointing settings (snapshot frequency, WAL fsync policy)

Why: two runs with similar corpora can look wildly different if `regex`/Python/WSL differ or if checkpointing flips the bottleneck.

---

## 2) Stage 1 metrics (this is where “100+GB” mostly hurts)

Log these at end of Stage 1:

### Throughput / scaling

* **Total bytes read (uncompressed)**
* Total lines read
* Total pieces emitted by the regex pretokenizer (call this `total_pieces_seen`)
* Wall time for Stage 1 (`t_stage1`)

This lets us project to 100 GB with a simple first-order estimate:

* Stage 1 is roughly linear in bytes processed (on the same hardware and similar text).

### Tail pressure / cap impact

These are the *most important* Stage 1 numbers for cap decisions:

* `unique_before_prune` = number of distinct piece byte-strings seen before applying caps
* `unique_after_min_freq` = after dropping `< min_piece_freq` (if you do it)
* `unique_kept` = final number kept (should be `<= max_unique_pieces`)
* **Did you hit `max_unique_pieces`?** (yes/no)
* **Cutoff frequency at the cap boundary**

  * i.e., the frequency of the *last retained* piece when sorted by `(-freq, piece_bytes)`

### How much mass you retained (very telling)

Compute:

* `kept_mass = sum(freq for retained pieces)`
* `coverage = kept_mass / total_pieces_seen`

Interpretation (rule-of-thumb):

* **coverage ≥ 99.5%** and **cutoff frequency is 1–2** → cap is mostly trimming junk tail; raising it usually won’t change merges much.
* **coverage < ~98–99%** or **cutoff frequency ≥ 5–10** → you’re trimming into the “head”; raising caps or sampling strategy likely matters.

### Memory

* Peak **Resident Set Size (RSS)** during Stage 1 (RSS = memory actually resident in RAM)
* RSS at the end of Stage 1

(That tells us whether Stage 1 `Counter[bytes]` is the main memory hog.)

---

## 3) Stage 2 metrics (this tells you how big the merge-learning “state” really is)

At end of Stage 2 log:

* `word_types_total` = number of word types eligible after Stage 1 and filters
* `word_types_kept` = `len(words)` (capped by `max_word_types`)
* **Did you hit `max_word_types`?** (yes/no)
* **Cutoff frequency at word_types boundary** (same idea as Stage 1)
* Simple length stats for `words`:

  * average symbols per word type (mean)
  * 95th percentile symbols per word type (p95)
  * max symbols per word type

Also:

* RSS after Stage 2

Interpretation:

* If you hit `max_word_types` and cutoff freq is still tiny (1–2) → again, you’re trimming tail types.
* If cutoff freq is noticeably >2–3 → you’re discarding relatively common types and the cap is more likely to affect merges.

---

## 4) Stage 3 metrics (this tells you whether merges will stay stable as corpus grows)

Stage 3’s runtime is *not* primarily driven by corpus bytes once Stage 2 is fixed; it’s driven by:

* how many word types you keep,
* how long they are,
* and how big the “candidate set” per merge is.

Log at start and then every N merges (e.g., every 200 or 500):

### Progress / efficiency

* merge index
* wall time elapsed
* **median time per merge** over the last window (and p95 if easy)
* current best pair count (`best_count`) (this shows the long-tail regime kicking in)

### State size pressure

* `len(pair_count)` (how many distinct adjacent pairs exist)
* heap size (or at least its approximate size)
* avg candidate words per merge:

  * `candidates = len(pair_to_words[(a,b)])` before dedup
  * `candidates_unique` after dedup (if you track it)
* RSS peak during Stage 3

### Checkpoint overhead (if enabled)

* time spent snapshotting per snapshot
* WAL sync policy and observed cost (even a rough “checkpoint time total” helps)

Interpretation:

* If time/merge stays roughly flat and RSS stays bounded: Stage 3 is stable.
* If heap size or candidate lists grow aggressively and time/merge creeps up: Stage 3 will be the scaling limiter when you raise caps.

---

## 5) What I’d need to recommend cap changes for “100+GB productive-grade”

If your goal is: “train a 50k tokenizer for a 3–7B model on a 100+GB corpus”, the key decision is usually **not** “make caps enormous”, it’s “ensure the retained inventory captures the distribution you care about”.

So in addition to the above metrics, I’d want:

### Corpus composition snapshot

Just a rough breakdown of where the 100+GB comes from (percentages are fine):

* web text vs books vs code vs forums vs multilingual vs domain-specific content
* whether you expect lots of non-English scripts

Reason: the “tail” can be garbage for English web text, but *meaningful* for multilingual/code-heavy mixes.

### A/B stability check (cheap, very informative)

Run the tokenizer training twice on:

* two different random 5–10GB samples from the 100+GB (or two different shards)

Compare:

* overlap of learned merges (or at least how quickly merge lists diverge)
* tokenization stats on a held-out eval set (avg tokens per character or per word)

If results are stable across samples, you don’t need insane caps. If they swing a lot, you need either better sampling or higher caps (and/or different pretokenization decisions).

---

## Practical cap-adjustment heuristics (simple, non-micro)

Given your earlier result (you hit both caps on OWT-like data), here’s how I’d decide what to do for “productive-grade”:

### If your logs show:

* **Stage 1 coverage ≥ 99.5%** at `max_unique_pieces=2M`, and
* **Stage 2 cutoff freq ~1–2** at `max_word_types=1.5M`

→ Your caps are probably **already fine** for a 50k vocab tokenizer, and scaling to 100GB is mostly about **Stage 1 throughput** (more CPU / parallelism / sampling), not raising caps.

### If instead you see:

* coverage meaningfully below ~99% **or**
* cutoff frequencies at cap boundaries are noticeably >2–3

→ You’re likely chopping into meaningful mass. Productive-grade upgrades would be:

1. improve *sampling/representativeness* of the tokenizer-training text (often better than huge caps), then
2. raise caps only if needed (which will push you toward needing more memory-efficient representations).

### A “free” cap tweak if you keep your current approach

If `max_word_types` is 1.5M, keeping `max_unique_pieces` much bigger than that often just bloats Stage 1 memory without changing Stage 3 input much.

So if Stage 2 always caps at 1.5M anyway, a productive default can be:

* `max_unique_pieces` ≈ `max_word_types` (maybe +10–20% cushion)

This reduces Stage 1 memory while keeping the training state nearly unchanged.

---

## Required Output

From your redo run, consolidate this compact summary into a single markdown file:

* Stage 1: `total_bytes`, `total_pieces_seen`, `unique_before`, `unique_kept`, hit-cap?, cutoff-freq, coverage, RSS_peak, `t_stage1`
* Stage 2: `word_types_total`, `word_types_kept`, hit-cap?, cutoff-freq, avg/p95/max word length, RSS_end
* Stage 3: merges done, `t_stage3`, median ms/merge, RSS_peak, `len(pair_count)` initial and late, typical candidates/merge

And also, include any other data points mentioned in the above exposition that would be useful for the stated goal.
