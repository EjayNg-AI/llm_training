from __future__ import annotations

import json

import pytest

from tokenizer_bpe.ab_compare import attach_ab_metrics, build_ab_stability_metrics
from tests.tokenizer_bpe.helpers import run_train, write_test_config


@pytest.mark.integration
def test_build_ab_stability_metrics_and_attach(tmp_path, tiny_corpus_text):
    corpus_a = tmp_path / "train_a.txt"
    corpus_b = tmp_path / "train_b.txt"
    corpus_a.write_text(tiny_corpus_text, encoding="utf-8")
    corpus_b.write_text(tiny_corpus_text + "extra line for shard b\n", encoding="utf-8")

    cfg_a = tmp_path / "cfg_a.yaml"
    cfg_b = tmp_path / "cfg_b.yaml"
    runs_dir = tmp_path / "runs"
    write_test_config(cfg_a, corpus_path=corpus_a, output_dir=runs_dir / "a")
    write_test_config(cfg_b, corpus_path=corpus_b, output_dir=runs_dir / "b")

    export_a = tmp_path / "export_a"
    export_b = tmp_path / "export_b"
    run_train(cfg_path=cfg_a, run_id="run_a", export_dir=export_a)
    run_train(cfg_path=cfg_b, run_id="run_b", export_dir=export_b)

    heldout = tmp_path / "heldout.txt"
    heldout.write_text("alpha beta gamma\n", encoding="utf-8")
    metrics = build_ab_stability_metrics(
        export_dir_a=export_a,
        export_dir_b=export_b,
        heldout_path=heldout,
        run_a="run_a",
        run_b="run_b",
    )
    assert 0.0 <= metrics["merge_overlap_top_1000"] <= 1.0
    assert 0.0 <= metrics["merge_overlap_top_5000"] <= 1.0
    assert "tokens_per_char_delta" in metrics
    assert "tokens_per_word_delta" in metrics

    run_stats_path = tmp_path / "run_statistics.json"
    run_stats_path.write_text(json.dumps({"run_id": "run_a"}), encoding="utf-8")
    attach_ab_metrics(run_stats_path, metrics)
    updated = json.loads(run_stats_path.read_text(encoding="utf-8"))
    assert "ab_stability" in updated
    assert updated["ab_stability"]["run_a"] == "run_a"

