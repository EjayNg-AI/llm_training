"""Minimal runtime encode/decode harness for losslessness checks."""

from __future__ import annotations

from typing import Iterable


def build_merge_ranks(
    id_to_token_bytes: list[bytes],
    merge_pairs: list[tuple[int, int]],
) -> dict[tuple[bytes, bytes], int]:
    ranks: dict[tuple[bytes, bytes], int] = {}
    for rank, (a, b) in enumerate(merge_pairs):
        ranks[(id_to_token_bytes[a], id_to_token_bytes[b])] = rank
    return ranks


def encode_piece_bytes(
    piece_bytes: bytes,
    merge_ranks: dict[tuple[bytes, bytes], int],
    token_bytes_to_id: dict[bytes, int],
) -> list[int]:
    symbols = [bytes([b]) for b in piece_bytes]
    if not symbols:
        return []

    while len(symbols) > 1:
        best_rank = None
        best_pair = None
        for i in range(len(symbols) - 1):
            pair = (symbols[i], symbols[i + 1])
            rank = merge_ranks.get(pair)
            if rank is None:
                continue
            if best_rank is None or rank < best_rank:
                best_rank = rank
                best_pair = pair
        if best_pair is None:
            break

        merged_symbols: list[bytes] = []
        i = 0
        while i < len(symbols):
            if i + 1 < len(symbols) and (symbols[i], symbols[i + 1]) == best_pair:
                merged_symbols.append(symbols[i] + symbols[i + 1])
                i += 2
            else:
                merged_symbols.append(symbols[i])
                i += 1
        symbols = merged_symbols

    return [token_bytes_to_id[s] for s in symbols]


def encode_text_bytes(
    pieces: Iterable[str],
    merge_ranks: dict[tuple[bytes, bytes], int],
    token_bytes_to_id: dict[bytes, int],
) -> list[int]:
    out: list[int] = []
    for piece in pieces:
        out.extend(encode_piece_bytes(piece.encode("utf-8"), merge_ranks, token_bytes_to_id))
    return out


def decode_token_ids(token_ids: list[int], id_to_token_bytes: list[bytes]) -> str:
    raw = b"".join(id_to_token_bytes[idx] for idx in token_ids)
    return raw.decode("utf-8")

