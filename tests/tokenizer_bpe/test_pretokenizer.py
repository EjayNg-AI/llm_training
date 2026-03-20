import pytest

from tokenizer_bpe.pretokenizer import compile_pattern, iter_pieces, parse_flags, resolve_pattern


def _compile_alias(name: str):
    alias, pattern_str, flags, _ = resolve_pattern({"pattern": name, "flags": []})
    assert alias == name
    return compile_pattern(pattern_str, flags)


def test_gpt2_default_tokenization_whitespace_behavior():
    alias, pattern_str, flags, _ = resolve_pattern({"pattern": "gpt2_default", "flags": []})
    assert alias == "gpt2_default"
    compiled = compile_pattern(pattern_str, flags)
    text = "don't stop  now\n"
    pieces = [m.group(0) for m in compiled.finditer(text)]
    assert pieces == ["don", "'t", " stop", " ", " now", "\n"]


def test_gpt2_fast_compiles_and_matches():
    compiled = _compile_alias("gpt2_fast")
    text = "Hello 123!"
    pieces = list(iter_pieces(compiled, text))
    assert pieces
    assert "".join(pieces) == text


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


def test_md_latex_fast_v2_keeps_bounded_latex_environment_markers():
    compiled = _compile_alias("md_latex_fast_v2")
    text = r"\begin{align*} x + y \end{align*}"
    pieces = list(iter_pieces(compiled, text))
    assert pieces == [r"\begin{align*}", " x", " +", " y", r" \end{align*}"]


def test_md_latex_fast_v2_keeps_environment_markers_local_not_whole_span():
    compiled = _compile_alias("md_latex_fast_v2")
    text = r"\begin{equation}x+y\end{equation}"
    pieces = list(iter_pieces(compiled, text))
    assert "".join(pieces) == text
    assert pieces[0] == r"\begin{equation}"
    assert pieces[-1] == r"\end{equation}"
    assert pieces != [text]


def test_md_latex_fast_v2_does_not_atomicize_custom_environment_names():
    compiled = _compile_alias("md_latex_fast_v2")
    text = r"\begin{myenv} body"
    pieces = list(iter_pieces(compiled, text))
    assert pieces == [r"\begin", "{", "myenv", "}", " body"]


def test_md_latex_fast_v2_leaves_trailing_env_args_split():
    compiled = _compile_alias("md_latex_fast_v2")
    text = r"\begin{array}{cc}"
    pieces = list(iter_pieces(compiled, text))
    assert pieces == [r"\begin{array}", "{", "cc", "}"]


def test_md_latex_fast_v2_anchors_headings_to_line_start():
    compiled = _compile_alias("md_latex_fast_v2")
    assert list(iter_pieces(compiled, "### Title")) == ["###", " Title"]
    assert list(iter_pieces(compiled, "See ### Title")) == ["See", " ###", " Title"]


def test_md_latex_fast_v2_keeps_full_task_list_opener():
    compiled = _compile_alias("md_latex_fast_v2")
    assert list(iter_pieces(compiled, "- [x] done")) == ["- [x]", " done"]
    assert list(iter_pieces(compiled, "  * [ ] todo")) == ["  * [ ]", " todo"]


def test_md_latex_fast_v2_keeps_bounded_math_delimiters():
    compiled = _compile_alias("md_latex_fast_v2")
    assert list(iter_pieces(compiled, "$$x+y$$")) == ["$$", "x", "+", "y", "$$"]
    assert list(iter_pieces(compiled, r"\(x+y\)")) == [r"\(", "x", "+", "y", r"\)"]


def test_md_latex_fast_v2_keeps_capped_multi_character_math_affixes():
    compiled = _compile_alias("md_latex_fast_v2")
    assert list(iter_pieces(compiled, r"x_{ij}")) == ["x", r"_{ij}"]
    assert list(iter_pieces(compiled, r"x^{n+1}")) == ["x", r"^{n+1}"]
    assert list(iter_pieces(compiled, r"x_{\text{max}}")) == ["x", r"_{\text{max}}"]


def test_md_latex_fast_v3_preserves_v2_latex_environment_behavior():
    compiled = _compile_alias("md_latex_fast_v3")
    text = r"\begin{align*} x + y \end{align*}"
    pieces = list(iter_pieces(compiled, text))
    assert pieces == [r"\begin{align*}", " x", " +", " y", r" \end{align*}"]


def test_md_latex_fast_v3_preserves_local_math_delimiters_and_affixes():
    compiled = _compile_alias("md_latex_fast_v3")
    assert list(iter_pieces(compiled, "$$x+y$$")) == ["$$", "x", "+", "y", "$$"]
    assert list(iter_pieces(compiled, r"\(x_{ij}+y^{n+1}\)")) == [r"\(", "x", r"_{ij}", "+", "y", r"^{n+1}", r"\)"]


def test_md_latex_fast_v3_keeps_headings_line_anchored():
    compiled = _compile_alias("md_latex_fast_v3")
    assert list(iter_pieces(compiled, "### Title")) == ["###", " Title"]
    assert list(iter_pieces(compiled, "See ### Title")) == ["See", " ###", " Title"]


def test_md_latex_fast_v3_keeps_task_lists_but_not_inline_task_boxes():
    compiled = _compile_alias("md_latex_fast_v3")
    assert list(iter_pieces(compiled, "- [x] done")) == ["- [x]", " done"]
    assert list(iter_pieces(compiled, "Use [x] inline")) == ["Use", " [", "x", "]", " inline"]


def test_md_latex_fast_v3_keeps_ordered_list_openers_line_anchored():
    compiled = _compile_alias("md_latex_fast_v3")
    assert list(iter_pieces(compiled, "12. item")) == ["12.", " item"]
    assert list(iter_pieces(compiled, "3) item")) == ["3)", " item"]
    assert list(iter_pieces(compiled, "In 3) we proceed")) == ["In", " 3", ")", " we", " proceed"]


def test_md_latex_fast_v3_keeps_fenced_code_openers_local():
    compiled = _compile_alias("md_latex_fast_v3")
    assert list(iter_pieces(compiled, "```python")) == ["```python"]
    assert list(iter_pieces(compiled, "~~~")) == ["~~~"]
    assert list(iter_pieces(compiled, "Use ```python")) == ["Use", " ```", "python"]


def test_md_latex_fast_v3_keeps_blockquotes_and_reference_labels_line_anchored():
    compiled = _compile_alias("md_latex_fast_v3")
    assert list(iter_pieces(compiled, "> quoted")) == [">", " quoted"]
    assert list(iter_pieces(compiled, "[lemma]: https://example.test")) == [
        "[lemma]:",
        " https",
        "://",
        "example",
        ".",
        "test",
    ]
    assert list(iter_pieces(compiled, "See [lemma]: note")) == ["See", " [", "lemma", "]:", " note"]


def test_md_latex_fast_v3_keeps_table_rows_and_hrules_line_anchored():
    compiled = _compile_alias("md_latex_fast_v3")
    assert list(iter_pieces(compiled, "| a | b |")) == ["|", " a", " |", " b", " |"]
    assert list(iter_pieces(compiled, "---")) == ["---"]
    assert list(iter_pieces(compiled, "x --- y")) == ["x", " ---", " y"]


def test_custom_pattern_requires_value():
    with pytest.raises(ValueError, match="custom_pattern"):
        resolve_pattern({"pattern": "custom", "custom_pattern": None, "flags": []})


def test_parse_flags_supports_aliases():
    flags = parse_flags(["IGNORECASE", "MULTILINE"])
    assert flags != 0


def test_parse_flags_rejects_unknown_alias():
    with pytest.raises(ValueError, match="Unsupported regex flag"):
        parse_flags(["DOTALL"])
