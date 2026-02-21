"""Export tokenizer artifacts from trained BPE state."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .byte_unicode import bytes_to_unicode, token_bytes_to_string
from .io_atomic import atomic_dump_json, atomic_dump_text


def _build_special_tokens_map(tokens: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if "<|endoftext|>" in tokens:
        mapping["bos_token"] = "<|endoftext|>"
        mapping["eos_token"] = "<|endoftext|>"
        mapping["unk_token"] = "<|endoftext|>"
    elif tokens:
        mapping["bos_token"] = tokens[0]
        mapping["eos_token"] = tokens[0]
        mapping["unk_token"] = tokens[0]
    if "<|pad|>" in tokens:
        mapping["pad_token"] = "<|pad|>"
    elif tokens:
        mapping["pad_token"] = tokens[-1]
    return mapping


def export_tokenizer(
    cfg: dict[str, Any],
    run_dir: Path,
    export_dir: Path,
    train_state: dict[str, Any],
    pattern_alias: str,
    pattern_str: str,
    pattern_flags: int,
    pattern_hash: str,
    config_hash: str,
    corpus_hash: str,
    logger: logging.Logger,
) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)

    id_to_token_bytes: list[bytes] = train_state["id_to_token_bytes"]
    merge_pairs: list[tuple[int, int]] = train_state["merge_pairs"]
    special_tokens: list[str] = list(cfg["special_tokens"]["tokens"])
    special_placement: str = cfg["special_tokens"]["placement"]

    byte_to_unicode, _ = bytes_to_unicode()
    base_token_strings = [token_bytes_to_string(tb, byte_to_unicode) for tb in id_to_token_bytes]

    vocab: dict[str, int] = {}
    if special_placement == "start":
        for special in special_tokens:
            if special in vocab:
                raise ValueError(f"Duplicate special token: {special}")
            vocab[special] = len(vocab)
        for token_str in base_token_strings:
            if token_str in vocab:
                raise ValueError(f"Token collision with special token: {token_str!r}")
            vocab[token_str] = len(vocab)
    else:
        for token_str in base_token_strings:
            if token_str in vocab:
                raise ValueError(f"Duplicate token string in base vocab: {token_str!r}")
            vocab[token_str] = len(vocab)
        for special in special_tokens:
            if special in vocab:
                raise ValueError(f"Special token collides with learned token: {special}")
            vocab[special] = len(vocab)

    merges_lines = ["#version: 0.2"]
    for a, b in merge_pairs:
        tok_a = base_token_strings[a]
        tok_b = base_token_strings[b]
        merges_lines.append(f"{tok_a} {tok_b}")
    merges_text = "\n".join(merges_lines) + "\n"

    special_map = _build_special_tokens_map(special_tokens)

    tokenizer_config = {
        "tokenizer_class": "GPT2Tokenizer",
        "add_prefix_space": False,
        "model_max_length": 1024,
        "pattern_alias": pattern_alias,
        "pattern": pattern_str,
        "pattern_flags": pattern_flags,
        "pattern_hash": pattern_hash,
        "byte_to_unicode_version": "gpt2",
        "special_tokens": special_tokens,
        "vocab_size": len(vocab),
        "num_merges": len(merge_pairs),
        "training_corpus_sha256": corpus_hash,
        "config_hash": config_hash,
    }
    tokenizer_config.update(special_map)

    training_stats = {
        "run_dir": str(run_dir),
        "final_merge_index": train_state["last_merge"],
        "vocab_size": len(vocab),
        "num_merges": len(merge_pairs),
        "config_hash": config_hash,
        "pattern_hash": pattern_hash,
        "training_corpus_sha256": corpus_hash,
    }

    atomic_dump_json(export_dir / "vocab.json", vocab)
    atomic_dump_text(export_dir / "merges.txt", merges_text)
    atomic_dump_json(export_dir / "tokenizer_config.json", tokenizer_config)
    atomic_dump_json(export_dir / "special_tokens_map.json", special_map)
    atomic_dump_json(export_dir / "training_stats.json", training_stats)

    # Mirror a compact metadata view into the run directory.
    atomic_dump_json(run_dir / "export_manifest.json", {"export_dir": str(export_dir), **training_stats})

    logger.info("Exported vocab size=%s merges=%s", len(vocab), len(merge_pairs))

