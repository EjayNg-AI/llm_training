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


def test_custom_pattern_requires_value():
    with pytest.raises(ValueError, match="custom_pattern"):
        resolve_pattern({"pattern": "custom", "custom_pattern": None, "flags": []})


def test_parse_flags_supports_aliases():
    flags = parse_flags(["IGNORECASE", "MULTILINE"])
    assert flags != 0


def test_parse_flags_rejects_unknown_alias():
    with pytest.raises(ValueError, match="Unsupported regex flag"):
        parse_flags(["DOTALL"])
