# GPT-2 Style UTF-8 Byte-Level BPE Tokenizer

This is the implementation reference for tokenizer Stage 03 in this repository.

## Scope

Stage 03 trains and exports a deterministic GPT-2 style UTF-8 byte-level BPE tokenizer, and now records scaling-focused telemetry for Stage 1/2/3 analysis.

## Entrypoints

Train tokenizer:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe.yaml
```

OpenWebText 32k example:

```bash
RUN_ID="owt32k_full_25m_$(date -u +%Y%m%d_%H%M%S)"
ARTIFACT_ID="tokenizer_${RUN_ID}"

python scripts/03_train_tokenizer.py \
  --config configs/tokenizer_bpe_owt_32k.yaml \
  --run-id "${RUN_ID}" \
  --artifact-id "${ARTIFACT_ID}"
```

Optional A/B stability comparison + report regeneration:

```bash
python scripts/09_compare_tokenizer_ab.py \
  --run-statistics artifacts/tokenizer/runs/<run_id>/run_statistics.json \
  --export-a artifacts/tokenizer/exports/<artifact_a> \
  --export-b artifacts/tokenizer/exports/<artifact_b> \
  --run-a <run_a> \
  --run-b <run_b> \
  --heldout-text data/raw/<heldout.txt>
```

## Run and Export Outputs

Run directory (`run.output_dir/<run_id>/`) includes:

1. `training_telemetry.json`
2. `run_statistics.json`
3. `merges.wal` (when `checkpointing.enabled` and `checkpointing.wal_enabled` are true)
4. `snapshot_*.json` (when snapshots are enabled and merge index reaches interval)

Canonical markdown report output:

1. `docs/data_collection_report.md` (or `run.report_output_path` override)

Export directory (`artifacts/tokenizer/exports/<artifact_id>/`) includes:

1. `vocab.json`
2. `merges.txt`
3. `tokenizer_config.json`
4. `special_tokens_map.json`
5. `training_stats.json`
6. `artifact_manifest.json`

Published tokenizer exports are registered in:

1. `artifacts/registry.jsonl`

## Configuration Contract

Config sources:

1. `configs/tokenizer_bpe.yaml`
2. `configs/tokenizer_bpe_owt_32k.yaml`
3. `configs/tokenizer_bpe_owt_32k_probe_1gb.yaml`
4. defaults in `scripts/tokenizer_bpe/config.py`

Current OWT presets (`configs/tokenizer_bpe_owt_32k.yaml` and `configs/tokenizer_bpe_owt_32k_probe_1gb.yaml`) set:

1. `data.max_unique_pieces = 2500000`
2. `bpe.max_word_types = 2500000`

Top-level config sections:

1. `run`
2. `data`
3. `pretokenizer`
4. `bpe`
5. `special_tokens`
6. `checkpointing`

Stage 03 exposes checkpointing settings for WAL/snapshot behavior and overhead measurement. `resume_mode` is currently accepted as config but still runs as fresh training.
`bpe.vocab_size` is treated as a merge-target driver; if it is set below `256 + len(special_tokens.tokens)`, Stage 03 intentionally treats this as a zero-merge edge case and still exports at least byte-vocab + specials.

## Telemetry Contract

`training_telemetry.json` always includes:

1. `training_started_at`
2. `training_ended_at`
3. `elapsed_seconds`

It additionally includes:

1. `stage_seconds`
2. `artifact_id`
3. `run_statistics_path`
4. `report_path`

`run_statistics.json` includes:

1. environment snapshot (`os`, `platform_mode`, CPU, RAM, Python, regex)
2. scale-sensitive config snapshot
3. Stage 1 metrics (`total_bytes_processed`, `total_pieces_seen`, cap/coverage metrics including cap-engagement events, cumulative cap eviction metrics, RSS)
4. Stage 2 metrics (`word_types_total/kept`, cutoff, symbol-length stats, RSS)
5. Stage 3 metrics (merge latency, pair-state pressure, candidate stats, RSS, checkpoint overhead)
6. optional `ab_stability` section from A/B comparison utility

## Algorithm Summary

1. Stage 1: pretokenize corpus and count UTF-8 piece bytes.
2. Stage 2: initialize weighted word-type state from piece counts.
3. Stage 3: learn merges by repeatedly applying highest-frequency adjacent pair.
4. Stage 4: export tokenizer artifacts and publish manifest.

Determinism-critical contracts:

1. Stage 1 merges worker completions in contiguous `batch_id` order.
2. Stage 1/2 sorting uses deterministic tie-break ordering.
3. Stage 3 best-pair selection uses heap tuples `(-count, pair_id)` with packed `pair_id`.
4. Export ID assignment is stable for fixed config and source signature.

## Stage Notes

### Stage 1 (`scripts/tokenizer_bpe/stage1_count.py`)

1. Supports `text` and `jsonl` (with optional `.gz`) input files.
2. Applies optional normalization (`none`, `NFC`, `NFKC`) before regex extraction.
3. Drops pieces longer than `bpe.max_piece_bytes`.
4. Applies deterministic top-K approximation by `data.max_unique_pieces`.
5. Emits cap-boundary and coverage metrics for scaling analysis.
6. `hit_max_unique_pieces` is triggered by cap engagement during streaming/final truncation, not by post-cap final inventory shape.
7. `unique_before_prune` is reported as a pre-cap window maximum when `max_unique_pieces` is enabled.
8. `evicted_keys_total` and `evicted_mass_total` accumulate keys/mass trimmed by deterministic top-K cap enforcement across all cap events.
9. `evicted_mass_ratio` reports `evicted_mass_total / total_pieces_seen` to quantify discarded Stage 1 mass.

### Stage 2 (`scripts/tokenizer_bpe/stage2_init.py`)

1. Applies `min_piece_freq`, deterministic sorting, then `max_word_types` cap.
2. Builds compact `array('H'/'I')` symbol storage and `array('Q')` frequencies.
3. Emits capped inventory and symbol-length distribution telemetry.

### Stage 3 (`scripts/tokenizer_bpe/stage3_train.py`)

1. Trains merges in-memory with incremental pair-count updates.
2. Maintains heap pressure using stale-ratio rebuild.
3. Emits merge-latency window metrics and pair/candidate state pressure metrics.
4. Optionally writes WAL and periodic snapshots.
5. Captures checkpointing overhead (`snapshot_*` and WAL sync timing).
6. Records `pair_count_len_late` / `heap_size_late` from final in-memory state, even when training exits before the first metrics window.
7. Maintains pair-to-word candidate membership incrementally by appending only newly introduced pair memberships and dropping mappings when global pair count reaches zero.

Stop conditions:

1. no remaining valid pair
2. best pair count below `bpe.min_merge_freq`
3. reached merge target from `bpe.vocab_size` or `bpe.max_merges`
4. optional `--stop-after-merges`

## Testing References

Tokenizer-focused tests live under:

1. `tests/tokenizer_bpe/`

Common commands:

```bash
python -m pytest -q tests/tokenizer_bpe
python -m pytest -q tests/tokenizer_bpe -m "not integration"
```
