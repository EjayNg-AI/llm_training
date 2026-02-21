from __future__ import annotations

import pytest

from tests.tokenizer_bpe.helpers import normalized_training_stats, run_train, write_test_config


def _assert_exports_equivalent(left_dir, right_dir):
    assert (left_dir / "merges.txt").read_text(encoding="utf-8") == (right_dir / "merges.txt").read_text(
        encoding="utf-8"
    )
    assert (left_dir / "vocab.json").read_text(encoding="utf-8") == (right_dir / "vocab.json").read_text(
        encoding="utf-8"
    )
    assert (left_dir / "tokenizer_config.json").read_text(
        encoding="utf-8"
    ) == (right_dir / "tokenizer_config.json").read_text(encoding="utf-8")
    assert normalized_training_stats(left_dir / "training_stats.json") == normalized_training_stats(
        right_dir / "training_stats.json"
    )


@pytest.mark.integration
@pytest.mark.recovery
@pytest.mark.determinism
def test_resume_matches_uninterrupted_run(tmp_path, tiny_corpus_text):
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text(tiny_corpus_text, encoding="utf-8")

    runs_dir = tmp_path / "runs"
    cfg_path = tmp_path / "tokenizer.yaml"
    write_test_config(cfg_path, corpus_path=corpus_path, output_dir=runs_dir)

    export_full = tmp_path / "export_full"
    export_resumed = tmp_path / "export_resumed"
    run_train(cfg_path=cfg_path, run_id="full", export_dir=export_full)

    run_train(cfg_path=cfg_path, run_id="resume_case", export_dir=tmp_path / "export_partial", stop_after_merges=2)
    run_train(cfg_path=cfg_path, run_id="resume_case", export_dir=export_resumed, resume=True)

    _assert_exports_equivalent(export_full, export_resumed)


@pytest.mark.integration
@pytest.mark.recovery
@pytest.mark.determinism
def test_resume_ignores_uncommitted_wal_begin(tmp_path, tiny_corpus_text):
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text(tiny_corpus_text, encoding="utf-8")

    runs_dir = tmp_path / "runs"
    cfg_path = tmp_path / "tokenizer.yaml"
    write_test_config(cfg_path, corpus_path=corpus_path, output_dir=runs_dir)

    export_full = tmp_path / "export_full"
    export_recovered = tmp_path / "export_recovered"
    run_train(cfg_path=cfg_path, run_id="full", export_dir=export_full)

    run_train(cfg_path=cfg_path, run_id="crash_case", export_dir=tmp_path / "export_partial", stop_after_merges=1)
    wal_path = runs_dir / "crash_case" / "merges.wal"
    wal_path.write_text(
        wal_path.read_text(encoding="utf-8") + "BEGIN\t999\t1\t2\t3\n",
        encoding="utf-8",
    )
    run_train(cfg_path=cfg_path, run_id="crash_case", export_dir=export_recovered, resume=True)

    _assert_exports_equivalent(export_full, export_recovered)
