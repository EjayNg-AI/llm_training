from __future__ import annotations

import json

import pytest

from tests.tokenizer_bpe.helpers import normalized_training_stats, run_train, write_test_config


@pytest.mark.integration
@pytest.mark.determinism
def test_two_fresh_runs_produce_equivalent_exports(tmp_path, tiny_corpus_text):
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text(tiny_corpus_text, encoding="utf-8")

    runs_dir = tmp_path / "runs"
    cfg_path = tmp_path / "tokenizer.yaml"
    write_test_config(cfg_path, corpus_path=corpus_path, output_dir=runs_dir)

    export_a = tmp_path / "export_a"
    export_b = tmp_path / "export_b"
    run_train(cfg_path=cfg_path, run_id="run_a", export_dir=export_a)
    run_train(cfg_path=cfg_path, run_id="run_b", export_dir=export_b)

    assert (export_a / "merges.txt").read_text(encoding="utf-8") == (export_b / "merges.txt").read_text(
        encoding="utf-8"
    )
    assert (export_a / "vocab.json").read_text(encoding="utf-8") == (export_b / "vocab.json").read_text(
        encoding="utf-8"
    )
    assert (export_a / "tokenizer_config.json").read_text(
        encoding="utf-8"
    ) == (export_b / "tokenizer_config.json").read_text(encoding="utf-8")
    assert normalized_training_stats(export_a / "training_stats.json") == normalized_training_stats(
        export_b / "training_stats.json"
    )


@pytest.mark.integration
@pytest.mark.determinism
def test_exported_runtime_round_trip_fixture_text(tmp_path, tiny_corpus_text):
    from tokenizer_bpe.byte_unicode import bytes_to_unicode, token_string_to_bytes
    from tokenizer_bpe.pretokenizer import compile_pattern, iter_pieces
    from tokenizer_bpe.runtime_check import build_merge_ranks, decode_token_ids, encode_text_bytes

    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text(tiny_corpus_text, encoding="utf-8")

    runs_dir = tmp_path / "runs"
    cfg_path = tmp_path / "tokenizer.yaml"
    write_test_config(cfg_path, corpus_path=corpus_path, output_dir=runs_dir)

    export_dir = tmp_path / "export"
    run_train(cfg_path=cfg_path, run_id="run_a", export_dir=export_dir)

    vocab = json.loads((export_dir / "vocab.json").read_text(encoding="utf-8"))
    tokenizer_config = json.loads((export_dir / "tokenizer_config.json").read_text(encoding="utf-8"))
    merges_lines = (export_dir / "merges.txt").read_text(encoding="utf-8").splitlines()

    _, unicode_to_byte = bytes_to_unicode()

    id_to_token_bytes = [b"" for _ in range(len(vocab))]
    for token_str, token_id in vocab.items():
        id_to_token_bytes[token_id] = token_string_to_bytes(token_str, unicode_to_byte)
    token_bytes_to_id = {token_bytes: token_id for token_id, token_bytes in enumerate(id_to_token_bytes)}

    merge_pairs: list[tuple[int, int]] = []
    for line in merges_lines[1:]:
        if not line:
            continue
        tok_a, tok_b = line.split(" ", 1)
        tok_a_id = token_bytes_to_id[token_string_to_bytes(tok_a, unicode_to_byte)]
        tok_b_id = token_bytes_to_id[token_string_to_bytes(tok_b, unicode_to_byte)]
        merge_pairs.append((tok_a_id, tok_b_id))

    merge_ranks = build_merge_ranks(id_to_token_bytes, merge_pairs)
    compiled = compile_pattern(tokenizer_config["pattern"], int(tokenizer_config["pattern_flags"]))
    text = "banana bandana!\nbanana cabana\n"
    pieces = list(iter_pieces(compiled, text))
    token_ids = encode_text_bytes(pieces, merge_ranks, token_bytes_to_id)
    assert decode_token_ids(token_ids, id_to_token_bytes) == text
