from __future__ import annotations

from tokenizer_bpe.runtime_check import build_merge_ranks, decode_token_ids, encode_piece_bytes, encode_text_bytes


def _toy_vocab() -> tuple[list[bytes], dict[bytes, int], list[tuple[int, int]]]:
    id_to_token_bytes = [bytes([i]) for i in range(256)]
    id_to_token_bytes.append(b"ab")
    merge_pairs = [(97, 98)]
    token_bytes_to_id = {token: idx for idx, token in enumerate(id_to_token_bytes)}
    return id_to_token_bytes, token_bytes_to_id, merge_pairs


def test_encode_piece_bytes_prefers_merge_rank():
    id_to_token_bytes, token_bytes_to_id, merge_pairs = _toy_vocab()
    merge_ranks = build_merge_ranks(id_to_token_bytes, merge_pairs)
    encoded = encode_piece_bytes(b"ab", merge_ranks, token_bytes_to_id)
    assert encoded == [256]


def test_encode_decode_round_trip_with_merges():
    id_to_token_bytes, token_bytes_to_id, merge_pairs = _toy_vocab()
    merge_ranks = build_merge_ranks(id_to_token_bytes, merge_pairs)
    token_ids = encode_text_bytes(["ab", "a"], merge_ranks, token_bytes_to_id)
    assert token_ids == [256, 97]
    decoded = decode_token_ids(token_ids, id_to_token_bytes)
    assert decoded == "aba"
