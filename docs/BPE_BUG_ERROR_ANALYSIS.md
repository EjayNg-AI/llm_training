# BPE Training Bug/Error Analysis

This document records the core Stage 03 BPE training issues that were identified during review, plus the explicit config-contract update for the trivial `vocab_size` floor edge case.

It intentionally does not provide repair instructions.

## Scope

Code paths covered by this analysis:

1. `scripts/tokenizer_bpe/stage3_train.py` (core merge-learning loop and Stage 3 telemetry)
2. `CONFIG.md` (`bpe.vocab_size` contract language)

## Issue 1: Stage 3 late pair/heap telemetry could report stale values

### What was observed

`stage3_meta.pair_count_len_late` and `stage3_meta.heap_size_late` were intended to characterize late-stage state pressure, but in some runs they could remain equal to initial values rather than true final values.

### Why this happened

These fields were only refreshed inside the periodic metrics block (gated by `run.stage3_metrics_every_merges`). If training stopped before that block executed (for example, due to `min_merge_freq` threshold or no remaining candidates), the "late" fields were never updated from the final in-memory state.

### Impact

1. Run statistics could misrepresent Stage 3 pair/heap pressure for short or early-terminated runs.
2. Any downstream comparison/reporting logic using these fields could infer incorrect late-stage behavior.

## Issue 2: Candidate index (`pair_to_words`) accumulated stale/duplicate membership

### What was observed

Over long merge sequences, candidate-list tracking could grow with stale and repeated word indices beyond what current active pair states required.

### Why this happened

1. When a pair's global count dropped to zero (or below), the pair was removed from `pair_count` but its membership list in `pair_to_words` was not consistently removed.
2. During updates, word indices were appended for all `new_pairs` in an affected word, not only pairs newly introduced relative to that word's previous local pair set. That allowed repeated index appends for pairs that already had membership.

### Impact

1. Increased in-memory index size and bookkeeping overhead.
2. Higher candidate scan pressure prior to deduplication filtering.
3. No direct merge-order correctness failure was required for this issue to be harmful; it primarily affected efficiency and telemetry clarity.

## Config Contract Update: intentional floor-edge-case exception

### Edge case

`bpe.vocab_size < 256 + len(special_tokens.tokens)`

### Recorded contract meaning

`CONFIG.md` now explicitly treats this as a trivial floor condition:

1. Stage 03 can perform zero merges.
2. Export still includes the full byte vocabulary (256 tokens) and configured special tokens.
3. As a result, exported vocab size can exceed the requested `bpe.vocab_size` in this narrow edge case.

### Rationale captured in contract language

This exception is intentionally documented as a low-value boundary condition rather than treated as a primary error condition for workflow decisions.
