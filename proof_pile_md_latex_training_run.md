# Proof Pile Markdown/LaTeX-Aware BPE Training Run

Recorded at: `2026-03-20 12:09:49 +08`

## Run commands

Train:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_proof_pile_md_latex_train.yaml --run-id proof_pile_md_latex_bpe_64k_<date_tag>
```

Resume:

```bash
python scripts/03_train_tokenizer.py --config configs/tokenizer_bpe_proof_pile_md_latex_train.yaml --resume --run-id proof_pile_md_latex_bpe_64k_<date_tag>
```

Config validation:

```bash
python -m pytest -q tests/tokenizer_bpe/test_config_proof_pile_md_latex.py
```

## Latest training run specs

- Config file: `configs/tokenizer_bpe_proof_pile_md_latex_train.yaml`
- Output directory: `artifacts/tokenizer/runs_proof_pile_md_latex_train`
- Input corpus: `data/raw/proof_pile.txt`
- Normalization: `none`
- Pretokenizer pattern: `md_latex_fast_v1`
- Pretokenizer custom pattern: `null`
- Pretokenizer flags: `[]`
- Worker count: `3`
- Stage 1 batch lines: `1500`
- BPE vocab size: `64000`
- Stage 1 cap every batches: `50`
- Stage 1 cap start lines: `5000`
- Stage 1 cap safety factor: `1.05`

## Run ID template

`proof_pile_md_latex_bpe_64k_<date_tag>`
