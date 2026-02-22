from __future__ import annotations

import json
from pathlib import Path

from llm_training.tokenizer.runtime import ByteLevelBPETokenizer


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


def _build_identity_export(export_dir: Path) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    byte_to_unicode, _ = _bytes_to_unicode()

    vocab: dict[str, int] = {}
    for token_id in range(256):
        vocab[byte_to_unicode[token_id]] = token_id

    vocab["<|endoftext|>"] = 256
    vocab["<|pad|>"] = 257

    tokenizer_config = {
        "tokenizer_class": "GPT2Tokenizer",
        "pattern": r"[\s\S]",
        "pattern_flags": 0,
        "special_tokens": ["<|endoftext|>", "<|pad|>"],
        "vocab_size": len(vocab),
        "num_merges": 0,
    }
    special_tokens_map = {
        "bos_token": "<|endoftext|>",
        "eos_token": "<|endoftext|>",
        "unk_token": "<|endoftext|>",
        "pad_token": "<|pad|>",
    }

    (export_dir / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
    (export_dir / "merges.txt").write_text("#version: 0.2\n", encoding="utf-8")
    (export_dir / "tokenizer_config.json").write_text(
        json.dumps(tokenizer_config, ensure_ascii=False),
        encoding="utf-8",
    )
    (export_dir / "special_tokens_map.json").write_text(
        json.dumps(special_tokens_map, ensure_ascii=False),
        encoding="utf-8",
    )


def test_runtime_encode_decode_roundtrip(tmp_path: Path) -> None:
    export_dir = tmp_path / "tokenizer"
    _build_identity_export(export_dir)

    tok = ByteLevelBPETokenizer.from_dir(export_dir)
    text = "hello 123\nnaive cafe"
    token_ids = tok.encode(text)
    decoded = tok.decode(token_ids)

    assert decoded == text


def test_runtime_exposes_special_token_ids(tmp_path: Path) -> None:
    export_dir = tmp_path / "tokenizer"
    _build_identity_export(export_dir)

    tok = ByteLevelBPETokenizer.from_dir(export_dir)
    assert tok.special_token_ids.eos is not None
    assert tok.special_token_ids.pad is not None
