import pytest

from tokenizer_bpe.pretokenizer import compile_pattern, iter_pieces, parse_flags, resolve_pattern


def test_gpt2_default_tokenization_whitespace_behavior():
    alias, pattern_str, flags, _ = resolve_pattern({"pattern": "gpt2_default", "flags": []})
    assert alias == "gpt2_default"
    compiled = compile_pattern(pattern_str, flags)
    text = "don't stop  now\n"
    pieces = [m.group(0) for m in compiled.finditer(text)]
    assert pieces == ["don", "'t", " stop", " ", " now", "\n"]


def test_gpt2_fast_compiles_and_matches():
    alias, pattern_str, flags, _ = resolve_pattern({"pattern": "gpt2_fast", "flags": []})
    assert alias == "gpt2_fast"
    compiled = compile_pattern(pattern_str, flags)
    text = "Hello 123!"
    pieces = list(iter_pieces(compiled, text))
    assert pieces
    assert "".join(pieces) == text


def test_custom_pattern_requires_value():
    with pytest.raises(ValueError, match="custom_pattern"):
        resolve_pattern({"pattern": "custom", "custom_pattern": None, "flags": []})


def test_parse_flags_supports_aliases():
    flags = parse_flags(["IGNORECASE", "MULTILINE"])
    assert flags != 0


def test_parse_flags_rejects_unknown_alias():
    with pytest.raises(ValueError, match="Unsupported regex flag"):
        parse_flags(["DOTALL"])
