The UTF-8 byte level BPE training algorithm currently uses a typical GPT-2 fast regex in the pre tokenization phase. However this regex is too generic and will not be a good regex if the text corpus is LaTeX and Markdown heavy, and the model being trained must be designed to handle Markdwon and LaTeX well. 

The following is a suggested plan to make the tokenizer algorithm LaTex and Markdown robust, without overhauling the overall logical design of the algorithm itself (the speed, memory effiicency, checkpointing should remain as these have been battle tested many times and proven to work)

## 1. Add a new versioned pretokenizer alias, and leave `gpt2_fast` untouched

Edit `scripts/tokenizer_bpe/pretokenizer.py`.

Replace the current `PATTERN_ALIASES` block with this:

```python
PATTERN_ALIASES: dict[str, str] = {
    "gpt2_default": (
        r"'s|'t|'re|'ve|'m|'ll|'d"
        r"| ?\p{L}+"
        r"| ?\p{N}+"
        r"| ?[^\s\p{L}\p{N}]+"
        r"|\s+(?!\S)|\s+"
    ),
    "gpt2_fast": (
        r"'(?:[sdmt]|ll|ve|re)"
        r"| ?\p{L}++"
        r"| ?\p{N}++"
        r"| ?[^\s\p{L}\p{N}]++"
        r"|\s++$|\s+(?!\S)|\s"
    ),
    "md_latex_fast_v1": (
        r"'(?:[sdmt]|ll|ve|re)"
        r"| ?\\(?:[A-Za-z@]+[*]?|.)"                  # \frac, \alpha, \%, \\, \[, \], \(, \)
        r"| ?[_^](?:\{[\p{L}\p{N}]\}|[\p{L}\p{N}])"   # _i, ^2, _{i}, ^{n}
        r"| ?#{1,6}(?=[ \t])"                        # Markdown headings
        r"| ?\[[ xX]\](?=[ \t])"                     # Markdown task boxes
        r"| ?\p{L}++"
        r"| ?\p{N}++"
        r"| ?[^\s\p{L}\p{N}]++"
        r"|\s++$|\s+(?!\S)|\s"
    ),
}
```

Rules for this alias:

* Keep new branches **before** the generic letter, number, and punctuation branches.
* Do **not** add an ordered-list branch like `\d+\.`.
* Do **not** add a bullet-marker branch in v1. The current generic punctuation branch already handles `-`, `+`, and `*` acceptably, so the incremental gain is small.
* Do **not** add any whole-span atomic branches for inline math, display math, links, URLs, code fences, or LaTeX environments.

Do **not** mutate `gpt2_fast` in place. Keep it stable for old configs and clean A/Bs. The repo currently has only `gpt2_default` and `gpt2_fast`, and `gpt2_fast` is the default pattern in config. ([GitHub][1])

## 2. Do not change the global default pattern yet

Keep `DEFAULT_CONFIG["pretokenizer"]["pattern"]` as `"gpt2_fast"` for now. Use the new alias only in an experiment config until it proves itself on your held-out Markdown/LaTeX data. The current default config already points to `gpt2_fast`, with `custom_pattern: null` and `flags: []`. ([GitHub][2])

Use an experiment YAML like this:

```yaml
pretokenizer:
  pattern: "md_latex_fast_v1"
  custom_pattern: null
  flags: []

data:
  normalize: "none"
```

If you want one round of regex iteration before you freeze the alias, use the same regex as a `custom_pattern` first:

```yaml
pretokenizer:
  pattern: "custom"
  custom_pattern: >-
    '(?:[sdmt]|ll|ve|re)| ?\\(?:[A-Za-z@]+[*]?|.)| ?[_^](?:\{[\p{L}\p{N}]\}|[\p{L}\p{N}])| ?#{1,6}(?=[ \t])| ?\[[ xX]\](?=[ \t])| ?\p{L}++| ?\p{N}++| ?[^\s\p{L}\p{N}]++|\s++$|\s+(?!\S)|\s
  flags: []
```

## 3. Add Stage 1 safety-cap knobs to reduce transient uniqueness spikes

Edit `scripts/tokenizer_bpe/config.py`.

In `DEFAULT_CONFIG["checkpointing"]`, add these fields:

```python
"checkpointing": {
    "wal_fsync_each_commit": False,
    "wal_fsync_every_commits": 250,
    "snapshot_every_merges": 2000,
    "snapshot_every_seconds": 300,
    "keep_last_snapshots": 3,
    "stage1_snapshot_every_batches": 500,
    "stage1_cap_every_batches": 100,
    "stage1_cap_start_lines": 10000,
    "stage1_cap_safety_factor": 1.10,
},
```

Then extend `_validate` with:

```python
if int(cfg["checkpointing"].get("stage1_cap_every_batches", 100)) < 1:
    raise ValueError("checkpointing.stage1_cap_every_batches must be >= 1")

if int(cfg["checkpointing"].get("stage1_cap_start_lines", 10000)) < 0:
    raise ValueError("checkpointing.stage1_cap_start_lines must be >= 0")

if float(cfg["checkpointing"].get("stage1_cap_safety_factor", 1.10)) < 1.0:
    raise ValueError("checkpointing.stage1_cap_safety_factor must be >= 1.0")
```

Why here: the repo already keeps Stage 1 snapshot cadence inside the `checkpointing` section, and the current Stage 1 cap cadence is hardcoded to every 100 merged batches after 10,000 lines. These new knobs preserve that default cadence while giving you an earlier deterministic cap path when uniqueness surges. ([GitHub][2])

## 4. Wire those knobs into `count_pieces` with one small patch

Edit `scripts/tokenizer_bpe/stage1_count.py`.

Right after:

```python
snapshot_every_batches = int(checkpoint_cfg["stage1_snapshot_every_batches"])
snapshot_every_seconds = int(checkpoint_cfg["snapshot_every_seconds"])
```

add:

```python
stage1_cap_every_batches = int(checkpoint_cfg.get("stage1_cap_every_batches", 100))
stage1_cap_start_lines = int(checkpoint_cfg.get("stage1_cap_start_lines", 10000))
stage1_cap_safety_factor = float(checkpoint_cfg.get("stage1_cap_safety_factor", 1.10))
```

Then replace the current hardcoded cap block:

```python
if (
    max_unique_pieces is not None
    and merged_batches % 100 == 0
    and progress["total_lines_processed"] >= 10000
):
    piece_counts = _counter_top_k(piece_counts, int(max_unique_pieces))
```

with:

```python
if max_unique_pieces is not None:
    periodic_cap = (
        merged_batches % stage1_cap_every_batches == 0
        and progress["total_lines_processed"] >= stage1_cap_start_lines
    )
    safety_cap = len(piece_counts) > int(max_unique_pieces * stage1_cap_safety_factor)

    if periodic_cap or safety_cap:
        unique_before = len(piece_counts)
        piece_counts = _counter_top_k(piece_counts, int(max_unique_pieces))

        if safety_cap and not periodic_cap:
            logger.info(
                "Stage 1 safety cap: unique_before=%s unique_after=%s max_unique_pieces=%s factor=%s",
                unique_before,
                len(piece_counts),
                max_unique_pieces,
                stage1_cap_safety_factor,
            )
```

Do **not** change `_counter_top_k`. Keep its current deterministic sort key exactly as-is. Do **not** move `min_piece_freq` into Stage 1 streaming. The current docs explicitly describe Stage 1’s deterministic top‑K cap and say `min_piece_freq` is applied later instead of during streaming. ([GitHub][3])

## 5. Add focused tests, not a new test framework

The repo already has dedicated files for pretokenizer, config, and Stage 1 counting tests, so extend those existing files rather than creating a parallel suite. ([GitHub][4])

### `tests/tokenizer_bpe/test_pretokenizer.py`

Add:

```python
def _compile_alias(name: str):
    alias, pattern_str, flags, _ = resolve_pattern({"pattern": name, "flags": []})
    assert alias == name
    return compile_pattern(pattern_str, flags)


def test_md_latex_fast_v1_keeps_local_markup_heads_only():
    compiled = _compile_alias("md_latex_fast_v1")
    text = r"We use \alpha_i and [x] today"
    pieces = list(iter_pieces(compiled, text))
    assert pieces == ["We", " use", r" \alpha", "_i", " and", " [x]", " today"]


def test_md_latex_fast_v1_does_not_make_inline_math_atomic():
    compiled = _compile_alias("md_latex_fast_v1")
    text = r"$x+y$"
    pieces = list(iter_pieces(compiled, text))
    assert "".join(pieces) == text
    assert pieces != [text]


def test_md_latex_fast_v1_does_not_special_case_ordered_list_numbers():
    compiled = _compile_alias("md_latex_fast_v1")
    assert list(iter_pieces(compiled, "12. item")) == ["12", ".", " item"]


def test_md_latex_fast_v1_heading_and_task_box():
    compiled = _compile_alias("md_latex_fast_v1")
    assert list(iter_pieces(compiled, "### Title")) == ["###", " Title"]
    assert list(iter_pieces(compiled, "[x] done")) == ["[x]", " done"]
```

### `tests/tokenizer_bpe/test_config.py`

Add:

```python
def test_load_config_stage1_cap_defaults(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text("", encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg["checkpointing"]["stage1_cap_every_batches"] == 100
    assert cfg["checkpointing"]["stage1_cap_start_lines"] == 10000
    assert cfg["checkpointing"]["stage1_cap_safety_factor"] == 1.10


def test_load_config_rejects_invalid_stage1_cap_every_batches(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text(
        "checkpointing:\n  stage1_cap_every_batches: 0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="stage1_cap_every_batches"):
        load_config(cfg_path)


def test_load_config_rejects_invalid_stage1_cap_safety_factor(tmp_path):
    cfg_path = tmp_path / "tokenizer.yaml"
    cfg_path.write_text(
        "checkpointing:\n  stage1_cap_safety_factor: 0.99\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="stage1_cap_safety_factor"):
        load_config(cfg_path)
```

### `tests/tokenizer_bpe/test_stage1_count_unit.py`

Add one unit test that proves the new safety cap can fire **before** the final end-of-stage cap. This is the one place where I do want explicit behavior coverage.

```python
def test_count_pieces_stage1_safety_cap_triggers_early(tmp_path, tokenizer_logger, monkeypatch):
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text("a\nb\nc\nd\n", encoding="utf-8")

    cfg = {
        "data": {
            "input_paths": [str(corpus_path)],
            "input_format": "text",
            "jsonl_text_field": "text",
            "decode_errors": "replace",
            "normalize": "none",
            "max_bytes": None,
            "max_lines": None,
            "num_workers": 1,
            "batch_lines": 1,
            "max_unique_pieces": 2,
        },
        "checkpointing": {
            "stage1_snapshot_every_batches": 999999,
            "snapshot_every_seconds": 999999,
            "stage1_cap_every_batches": 999999,
            "stage1_cap_start_lines": 10**9,
            "stage1_cap_safety_factor": 1.0,
        },
        "bpe": {
            "max_piece_bytes": 200,
        },
        "special_tokens": {
            "tokens": ["<|endoftext|>"],
            "placement": "end",
        },
        "meta": {
            "config_hash": "cfg",
        },
    }

    call_counter = {"n": 0}
    original_top_k = stage1_count_module._counter_top_k

    def wrapped_top_k(counter, k):
        call_counter["n"] += 1
        return original_top_k(counter, k)

    monkeypatch.setattr(stage1_count_module, "_counter_top_k", wrapped_top_k)

    original_executor = stage1_count_module.ProcessPoolExecutor
    stage1_count_module.ProcessPoolExecutor = ThreadPoolExecutor
    try:
        piece_counts, metadata = count_pieces(
            cfg=cfg,
            run_dir=tmp_path / "run",
            pattern_str=PATTERN_ALIASES["gpt2_fast"],
            pattern_flags=0,
            pattern_hash="pat",
            logger=tokenizer_logger,
            resume=False,
        )
    finally:
        stage1_count_module.ProcessPoolExecutor = original_executor

    assert len(piece_counts) <= 2
    assert metadata["total_lines_processed"] == 4
    assert call_counter["n"] >= 2  # at least one early safety cap + final cap
```

## 6. Update `docs/TOKENIZER_BPE.md`

Make three doc edits:

1. In the default config block, add:

   * `checkpointing.stage1_cap_every_batches`
   * `checkpointing.stage1_cap_start_lines`
   * `checkpointing.stage1_cap_safety_factor`

2. In the pretokenizer section, add `md_latex_fast_v1` and explain:

   * LaTeX control sequences stay local (`\frac`, `\alpha`, `\%`, `\\`, `\[`).
   * Strict math affixes stay local (`_i`, `^2`, `_{i}`, `^{n}`).
   * Markdown support is limited to local heads (`###`, `[x]`) only.
   * No whole-span atomic rules.

3. In the Stage 1 section, replace the hardcoded “every 100 batches after 10,000 lines” wording with:

   * periodic cap driven by config
   * optional safety cap when `len(piece_counts) > max_unique_pieces * stage1_cap_safety_factor`
   * deterministic `_counter_top_k` unchanged
   * `min_piece_freq` still **not** applied during Stage 1 streaming

The current docs already describe the config contract, the pretokenizer aliases, and the Stage 1 cap behavior, so this is a straight documentation patch, not a redesign. ([GitHub][5])

## 7. Roll it out conservatively on your laptop

For the first real corpus run, do **not** use the repo defaults unchanged. Use a temporary experiment config like:

```yaml
data:
  num_workers: 3
  batch_lines: 1500

pretokenizer:
  pattern: "md_latex_fast_v1"
  custom_pattern: null
  flags: []

checkpointing:
  stage1_cap_every_batches: 50
  stage1_cap_start_lines: 5000
  stage1_cap_safety_factor: 1.05
```

Then do this in order:

1. Run a small A/B on a corpus prefix with `gpt2_fast`.
2. Run the same prefix with `md_latex_fast_v1`.
3. Compare:

   * Stage 1 checkpoint logs (`unique=...`)
   * final Stage 1 complete log (`unique=...`)
   * tokenization quality on a held-out Markdown/LaTeX sample pack

The Stage 1 logger already emits `unique` counts at checkpoint and completion, so you can watch whether the new regex is increasing the exact-byte inventory too much before committing to a full run. ([GitHub][3])

## 8. Hard rules for v1

Do **not** add any branch resembling these:

````python
r"\$.*?\$"
r"\$\$.*?\$\$"
r"\[[^\]]+\]\([^)]+\)"
r"```.*?```"
r"\\begin\{.*?\}.*?\\end\{.*?\}"
````

Do **not**:

* change `gpt2_fast` in place
* change the default config to the new alias before benchmark results
* widen the `_` / `^` branch beyond single-character payloads in v1
* reintroduce `\d+\.` ordered-list atomics
* move `min_piece_freq` into Stage 1
* change `_counter_top_k` tie-break behavior
