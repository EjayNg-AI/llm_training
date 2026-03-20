# Proof Pile 64k Run Comparison

Recorded at: `2026-03-20 14:55:00 +08`

## Compared runs

Baseline GPT-2-fast run:

- Run directory: `artifacts/tokenizer/runs_proof_pile_train/proof_pile_bpe_64k_20260320_1154`
- Export directory: `artifacts/tokenizer/exports/tokenizer_424657bc80f5`
- Config file: `configs/tokenizer_bpe_proof_pile_train.yaml`
- Pretokenizer alias: `gpt2_fast`

Markdown/LaTeX-aware run:

- Run directory: `artifacts/tokenizer/runs_proof_pile_md_latex_train/proof_pile_md_latex_bpe_64k_20260320_1326`
- Export directory: `artifacts/tokenizer/exports/tokenizer_20c5e03a4121`
- Config file: `configs/tokenizer_bpe_proof_pile_md_latex_train.yaml`
- Pretokenizer alias: `md_latex_fast_v1`

## Direct configuration differences

Shared settings:

- Input corpus path: `data/raw/proof_pile.txt`
- Target vocab size: `64000`
- Final merge count: `63718`

Markdown/LaTeX-aware-only settings:

- `normalize: none`
- `num_workers: 3`
- `batch_lines: 1500`
- `pretokenizer.pattern: md_latex_fast_v1`
- Stage 1 cap tuning:
  - `stage1_cap_every_batches: 50`
  - `stage1_cap_start_lines: 5000`
  - `stage1_cap_safety_factor: 1.05`

## Important caveat

This is not a perfectly controlled A/B comparison. Although both runs point at `data/raw/proof_pile.txt`, their recorded training corpus hashes differed before the later metadata standardization work. That means these observations are useful, but they should not be treated as a strict causal benchmark of regex choice alone.

## What changed in tokenizer behavior

The Markdown/LaTeX-aware tokenizer clearly learned more markup-specific vocabulary. It contains whole tokens such as:

- `\frac`
- `\begin`
- `\end`
- `\alpha`
- `\beta`
- `\gamma`
- `\sum`
- `\mathbb`
- `\mathbf`
- `[x]`

The GPT-2-fast tokenizer did not expose those same whole-command tokens in its exported vocabulary.

Vocabulary-shape comparison from the exported `vocab.json` files:

- GPT-2-fast:
  - backslash-prefixed tokens: `569`
  - heading-prefixed tokens: `16`
  - task-box tokens: `0`
  - `_{` / `^{` style affix tokens: `1143`
- Markdown/LaTeX-aware:
  - backslash-prefixed tokens: `2746`
  - heading-prefixed tokens: `13`
  - task-box tokens: `3`
  - `_{` / `^{` style affix tokens: `1205`

## Sample encoding comparisons

Representative token-count comparisons run against the two exported tokenizers:

- inline LaTeX sample:
  - GPT-2-fast: `28`
  - Markdown/LaTeX-aware: `25`
- LaTeX environment sample:
  - GPT-2-fast: `38`
  - Markdown/LaTeX-aware: `38`
- Markdown heading sample:
  - GPT-2-fast: `10`
  - Markdown/LaTeX-aware: `11`
- Markdown task-list sample:
  - GPT-2-fast: `21`
  - Markdown/LaTeX-aware: `18`
- mixed Markdown + LaTeX sample:
  - GPT-2-fast: `26`
  - Markdown/LaTeX-aware: `23`

Observed piece-level differences:

- The Markdown/LaTeX-aware tokenizer grouped checkbox syntax as ` [x]`, where the GPT-2-fast tokenizer split it into ` [`, `x`, `]`.
- The Markdown/LaTeX-aware tokenizer learned more merged LaTeX-adjacent pieces and kept more backslash-led command structure intact in vocabulary.
- The gain was not uniform on every Markdown example; simple headings did not clearly improve and were slightly worse in one sample.

## Conclusion

The Markdown/LaTeX-aware run did result in better recognition and handling of LaTeX commands and some Markdown structures, especially:

- LaTeX command names
- math-oriented backslash sequences
- checkbox/task-list syntax

The evidence is strongest at the vocabulary and tokenization-behavior level. The Markdown/LaTeX-aware tokenizer learned substantially more markup-specific units and often encoded representative markup-heavy strings with fewer tokens.

What this comparison does not prove:

- that the Markdown/LaTeX-aware run is globally better on all natural-language text
- that every Markdown pattern improved
- that the improvement magnitude is cleanly attributable to regex choice alone without rerunning both tokenizers on the exact same frozen corpus snapshot

## Recommended follow-up for a strict comparison

To turn this into a controlled benchmark:

1. Freeze one exact `proof_pile.txt` snapshot.
2. Train both configs against that same frozen file.
3. Compare token counts on a held-out suite of:
   - prose
   - Markdown documents
   - LaTeX-heavy documents
   - mixed technical notes
4. Compare downstream metrics such as sequence length inflation and reconstruction quality on markup-heavy examples.
