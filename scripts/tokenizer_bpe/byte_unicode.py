"""GPT-2 compatible byte-to-unicode mapping helpers."""

from __future__ import annotations

from typing import Dict, Tuple


def bytes_to_unicode() -> Tuple[Dict[int, str], Dict[str, int]]:
    bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    cs = bs[:]

    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1

    chars = [chr(c) for c in cs]
    byte_to_unicode = dict(zip(bs, chars))
    unicode_to_byte = {u: b for b, u in byte_to_unicode.items()}
    return byte_to_unicode, unicode_to_byte


def token_bytes_to_string(token_bytes: bytes, byte_to_unicode: Dict[int, str]) -> str:
    return "".join(byte_to_unicode[b] for b in token_bytes)


def token_string_to_bytes(token_string: str, unicode_to_byte: Dict[str, int]) -> bytes:
    return bytes(unicode_to_byte[ch] for ch in token_string)

