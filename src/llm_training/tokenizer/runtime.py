"""Runtime byte-level BPE tokenizer loaded from exported artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import regex

from .special import SpecialTokenIds, resolve_special_token_ids


def _bytes_to_unicode() -> tuple[dict[int, str], dict[str, int]]:
    bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    byte_to_unicode = {b: chr(c) for b, c in zip(bs, cs)}
    unicode_to_byte = {u: b for b, u in byte_to_unicode.items()}
    return byte_to_unicode, unicode_to_byte


def _token_string_to_bytes(token: str, unicode_to_byte: dict[str, int]) -> bytes:
    out = bytearray()
    for ch in token:
        if ch not in unicode_to_byte:
            raise ValueError(f"Unexpected token character not in byte map: {ch!r}")
        out.append(unicode_to_byte[ch])
    return bytes(out)


def _build_merge_ranks(merge_pairs: list[tuple[bytes, bytes]]) -> dict[tuple[bytes, bytes], int]:
    return {pair: rank for rank, pair in enumerate(merge_pairs)}


class ByteLevelBPETokenizer:
    """Minimal GPT-2 style byte-level BPE runtime."""

    def __init__(
        self,
        *,
        vocab: dict[str, int],
        id_to_token_str: list[str],
        id_to_token_bytes: list[bytes],
        token_bytes_to_id: dict[bytes, int],
        merge_ranks: dict[tuple[bytes, bytes], int],
        pattern: str,
        pattern_flags: int,
        special_token_ids: SpecialTokenIds,
        special_tokens: set[str],
    ) -> None:
        self.vocab = vocab
        self.id_to_token_str = id_to_token_str
        self.id_to_token_bytes = id_to_token_bytes
        self.token_bytes_to_id = token_bytes_to_id
        self.merge_ranks = merge_ranks
        self.pattern = pattern
        self.pattern_flags = pattern_flags
        self.compiled_pattern = regex.compile(pattern, pattern_flags)
        self.special_token_ids = special_token_ids
        self.special_tokens = special_tokens

    @classmethod
    def from_dir(cls, export_dir: str | Path) -> "ByteLevelBPETokenizer":
        export_path = Path(export_dir)
        vocab_path = export_path / "vocab.json"
        merges_path = export_path / "merges.txt"
        config_path = export_path / "tokenizer_config.json"
        special_map_path = export_path / "special_tokens_map.json"

        if not vocab_path.exists() or not merges_path.exists() or not config_path.exists():
            raise FileNotFoundError(f"Tokenizer export directory is incomplete: {export_path}")

        vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
        tokenizer_config = json.loads(config_path.read_text(encoding="utf-8"))
        special_map = {}
        if special_map_path.exists():
            special_map = json.loads(special_map_path.read_text(encoding="utf-8"))

        byte_to_unicode, unicode_to_byte = _bytes_to_unicode()
        _ = byte_to_unicode  # explicit to show mapping parity with training export

        max_token_id = max(vocab.values()) if vocab else -1
        id_to_token_str = [""] * (max_token_id + 1)
        id_to_token_bytes = [b""] * (max_token_id + 1)
        for token_str, token_id in vocab.items():
            token_bytes = _token_string_to_bytes(token_str, unicode_to_byte)
            id_to_token_str[token_id] = token_str
            id_to_token_bytes[token_id] = token_bytes

        token_bytes_to_id = {token_bytes: token_id for token_id, token_bytes in enumerate(id_to_token_bytes)}

        merge_pairs: list[tuple[bytes, bytes]] = []
        lines = merges_path.read_text(encoding="utf-8").splitlines()
        for line in lines[1:]:
            if not line.strip():
                continue
            tok_a, tok_b = line.split(" ", 1)
            a_bytes = _token_string_to_bytes(tok_a, unicode_to_byte)
            b_bytes = _token_string_to_bytes(tok_b, unicode_to_byte)
            merge_pairs.append((a_bytes, b_bytes))

        special_token_ids = resolve_special_token_ids(vocab, special_map)
        special_tokens = set(tokenizer_config.get("special_tokens", []))

        return cls(
            vocab=vocab,
            id_to_token_str=id_to_token_str,
            id_to_token_bytes=id_to_token_bytes,
            token_bytes_to_id=token_bytes_to_id,
            merge_ranks=_build_merge_ranks(merge_pairs),
            pattern=tokenizer_config["pattern"],
            pattern_flags=int(tokenizer_config["pattern_flags"]),
            special_token_ids=special_token_ids,
            special_tokens=special_tokens,
        )

    def _encode_piece_bytes(self, piece_bytes: bytes) -> list[int]:
        symbols = [bytes([b]) for b in piece_bytes]
        if not symbols:
            return []

        while len(symbols) > 1:
            best_rank = None
            best_pair = None
            for i in range(len(symbols) - 1):
                pair = (symbols[i], symbols[i + 1])
                rank = self.merge_ranks.get(pair)
                if rank is None:
                    continue
                if best_rank is None or rank < best_rank:
                    best_rank = rank
                    best_pair = pair
            if best_pair is None:
                break

            merged: list[bytes] = []
            i = 0
            while i < len(symbols):
                if i + 1 < len(symbols) and (symbols[i], symbols[i + 1]) == best_pair:
                    merged.append(symbols[i] + symbols[i + 1])
                    i += 2
                else:
                    merged.append(symbols[i])
                    i += 1
            symbols = merged

        out: list[int] = []
        unk_id = self.special_token_ids.unk
        for sym in symbols:
            token_id = self.token_bytes_to_id.get(sym)
            if token_id is None:
                if unk_id is None:
                    raise ValueError("Encountered symbol missing from vocab with no unk token configured")
                token_id = unk_id
            out.append(token_id)
        return out

    def encode(self, text: str) -> list[int]:
        token_ids: list[int] = []
        for match in self.compiled_pattern.finditer(text):
            piece = match.group(0)
            token_ids.extend(self._encode_piece_bytes(piece.encode("utf-8")))
        return token_ids

    def batch_encode(self, texts: Iterable[str]) -> list[list[int]]:
        return [self.encode(text) for text in texts]

    def decode(self, ids: list[int], *, skip_special_tokens: bool = False) -> str:
        chunks: list[bytes] = []
        for token_id in ids:
            token_str = self.id_to_token_str[token_id]
            if skip_special_tokens and token_str in self.special_tokens:
                continue
            chunks.append(self.id_to_token_bytes[token_id])
        return b"".join(chunks).decode("utf-8", errors="replace")
