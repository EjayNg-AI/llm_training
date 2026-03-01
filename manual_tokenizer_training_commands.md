# Manual Tokenizer Training Commands

Run from repository root:

```bash
cd /home/jenni/llm_training
source .venv/bin/activate

# Optional one-time prep if only a gz file exists:
if [ ! -f data/raw/owt_train.txt ] && [ -f data/raw/owt_train.txt.gz ]; then
  gunzip -c data/raw/owt_train.txt.gz > data/raw/owt_train.txt
fi
```

## 1GB Probe Run (Recommended)

```bash
RUN_ID="owt32k_probe_1gb_25m_$(date -u +%Y%m%d_%H%M%S)"
ARTIFACT_ID="tokenizer_${RUN_ID}"

python scripts/03_train_tokenizer.py \
  --config configs/tokenizer_bpe_owt_32k_probe_1gb.yaml \
  --run-id "${RUN_ID}" \
  --artifact-id "${ARTIFACT_ID}"
```

## Full OpenWebText Run

```bash
RUN_ID="owt32k_full_25m_$(date -u +%Y%m%d_%H%M%S)"
ARTIFACT_ID="tokenizer_${RUN_ID}"

python scripts/03_train_tokenizer.py \
  --config configs/tokenizer_bpe_owt_32k.yaml \
  --run-id "${RUN_ID}" \
  --artifact-id "${ARTIFACT_ID}"
```

## Recommended Sequence: Probe -> Full -> A/B

```bash
# 1) Probe run (1GB)
PROBE_RUN_ID="owt32k_probe_1gb_25m_$(date -u +%Y%m%d_%H%M%S)"
PROBE_ARTIFACT_ID="tokenizer_${PROBE_RUN_ID}"
python scripts/03_train_tokenizer.py \
  --config configs/tokenizer_bpe_owt_32k_probe_1gb.yaml \
  --run-id "${PROBE_RUN_ID}" \
  --artifact-id "${PROBE_ARTIFACT_ID}"

# 2) Full run
FULL_RUN_ID="owt32k_full_25m_$(date -u +%Y%m%d_%H%M%S)"
FULL_ARTIFACT_ID="tokenizer_${FULL_RUN_ID}"
python scripts/03_train_tokenizer.py \
  --config configs/tokenizer_bpe_owt_32k.yaml \
  --run-id "${FULL_RUN_ID}" \
  --artifact-id "${FULL_ARTIFACT_ID}"

# 3) Attach A/B metrics and generate A/B markdown report
python scripts/09_compare_tokenizer_ab.py \
  --run-statistics "artifacts/tokenizer/runs/${FULL_RUN_ID}/run_statistics.json" \
  --export-a "artifacts/tokenizer/exports/${PROBE_ARTIFACT_ID}" \
  --export-b "artifacts/tokenizer/exports/${FULL_ARTIFACT_ID}" \
  --run-a "${PROBE_RUN_ID}" \
  --run-b "${FULL_RUN_ID}" \
  --heldout-text openwebtext_sample_3k_4k_tokens.txt \
  --report-path artifacts/tokenizer/reports/ab_compare_probe_vs_full_25m.md
```

## Optional A/B Comparison and Report Regeneration

```bash
python scripts/09_compare_tokenizer_ab.py \
  --run-statistics artifacts/tokenizer/runs/<run_id>/run_statistics.json \
  --export-a artifacts/tokenizer/exports/<artifact_a> \
  --export-b artifacts/tokenizer/exports/<artifact_b> \
  --run-a <run_a> \
  --run-b <run_b> \
  --heldout-text data/raw/<heldout.txt>
```

## Output Locations

For each training run:

- `artifacts/tokenizer/runs/<run_id>/training_telemetry.json`
- `artifacts/tokenizer/runs/<run_id>/run_statistics.json`
- `artifacts/tokenizer/runs/<run_id>/merges.wal` (checkpointing enabled)
- `artifacts/tokenizer/runs/<run_id>/snapshot_*.json` (when snapshot interval is hit)
- `artifacts/tokenizer/exports/<artifact_id>/` (tokenizer artifacts)
- `docs/data_collection_report.md` (auto-generated canonical report)
