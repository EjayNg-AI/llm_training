# Tokenizer Config Reference

The tokenizer trainer uses these config files:

1. `configs/tokenizer_bpe.yaml`
2. `configs/tokenizer_bpe_owt_32k.yaml`

## Top-level sections

1. `run`: run directory and console log level
2. `data`: corpus input and Stage 1 counting controls
3. `pretokenizer`: regex pattern configuration
4. `bpe`: merge-learning controls
5. `special_tokens`: export-time special-token placement

Tokenizer Stage 03 does not use a `checkpointing` config section.

## `run`

1. `output_dir`: root for per-run telemetry directory
2. `seed`: reserved
3. `log_level`: console log level

## `data`

1. `input_paths`: files/directories to scan
2. `input_format`: `text` or `jsonl`
3. `jsonl_text_field`: source field when `input_format=jsonl`
4. `decode_errors`: UTF-8 decode policy (`strict`, `replace`, `ignore`)
5. `normalize`: `none`, `NFC`, or `NFKC`
6. `max_bytes`: optional cap on raw bytes read
7. `max_lines`: optional cap on lines read
8. `num_workers`: Stage 1 worker process count
9. `batch_lines`: line batch size per worker task
10. `min_piece_freq`: low-frequency filter threshold used in Stage 2 inventory build
11. `max_unique_pieces`: deterministic top-K cap for Stage 1 memory control

## `pretokenizer`

1. `pattern`: `gpt2_fast`, `gpt2_default`, or `custom`
2. `custom_pattern`: required when `pattern=custom`
3. `flags`: regex flags list

## `bpe`

1. `vocab_size`: target exported vocab size (bytes + merges + specials)
2. `min_merge_freq`: stop when best pair falls below threshold
3. `max_merges`: direct merge-count override (if null, derived from `vocab_size`)
4. `max_word_types`: cap unique piece inventory after deterministic sorting
5. `max_piece_bytes`: drop overly long pieces in Stage 1 worker path
6. `tie_break`: must be `lexicographic`

## `special_tokens`

1. `tokens`: ordered special-token list
2. `placement`: `end` (recommended) or `start`
