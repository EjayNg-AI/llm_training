"""Regex-based pretokenizer definitions for GPT-2 style tokenization."""

from __future__ import annotations

from typing import Any, Iterator, Tuple

import regex


PATTERN_ALIASES: dict[str, str] = {
    "gpt2_default": r"'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+",
    "gpt2_fast": r"'(?:[sdmt]|ll|ve|re)| ?\p{L}++| ?\p{N}++| ?[^\s\p{L}\p{N}]++|\s++$|\s+(?!\S)|\s",
}

FLAG_ALIASES = {
    "IGNORECASE": regex.IGNORECASE,
    "MULTILINE": regex.MULTILINE,
}


def parse_flags(flag_names: list[str]) -> int:
    flags = 0
    for name in flag_names:
        if name not in FLAG_ALIASES:
            raise ValueError(f"Unsupported regex flag: {name}")
        flags |= FLAG_ALIASES[name]
    return flags


def resolve_pattern(pretokenizer_cfg: dict[str, Any]) -> Tuple[str, str, int, str]:
    alias = pretokenizer_cfg.get("pattern", "gpt2_fast")
    custom_pattern = pretokenizer_cfg.get("custom_pattern")
    flag_names = pretokenizer_cfg.get("flags", [])
    flags = parse_flags(flag_names)

    if alias == "custom":
        if not custom_pattern:
            raise ValueError("pretokenizer.custom_pattern must be provided when pattern=custom")
        pattern_str = custom_pattern
    else:
        if alias not in PATTERN_ALIASES:
            raise ValueError(f"Unknown pretokenizer pattern alias: {alias}")
        pattern_str = PATTERN_ALIASES[alias]

    return alias, pattern_str, flags, regex.__version__


def compile_pattern(pattern_str: str, pattern_flags: int) -> regex.Pattern:
    return regex.compile(pattern_str, pattern_flags)


def iter_pieces(compiled_pattern: regex.Pattern, text: str) -> Iterator[str]:
    for match in compiled_pattern.finditer(text):
        yield match.group(0)

