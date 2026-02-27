# Manual Tokenizer Training Commands

Run from repository root:

```bash
cd /home/jenni/llm_training
source .venv/bin/activate
```

## 10GB Probe Run

```bash
RUN_ID="owt32k_probe_10gb_$(date -u +%Y%m%d_%H%M%S)"
ARTIFACT_ID="tokenizer_${RUN_ID}"

python scripts/03_train_tokenizer.py \
  --config configs/tokenizer_bpe_owt_32k_probe_10gb.yaml \
  --run-id "${RUN_ID}" \
  --artifact-id "${ARTIFACT_ID}"
```

## Full OpenWebText Run

```bash
RUN_ID="owt32k_full_$(date -u +%Y%m%d_%H%M%S)"
ARTIFACT_ID="tokenizer_${RUN_ID}"

python scripts/03_train_tokenizer.py \
  --config configs/tokenizer_bpe_owt_32k.yaml \
  --run-id "${RUN_ID}" \
  --artifact-id "${ARTIFACT_ID}"
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
