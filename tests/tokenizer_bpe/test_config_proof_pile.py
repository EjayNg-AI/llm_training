from __future__ import annotations

from pathlib import Path

from tokenizer_bpe.config import load_config


ROOT = Path(__file__).resolve().parents[2]


def test_proof_pile_config_loads_expected_values():
    cfg = load_config(ROOT / "configs" / "tokenizer_bpe_proof_pile_train.yaml")

    assert cfg["run"]["output_dir"] == "artifacts/tokenizer/runs_proof_pile_train"
    assert cfg["data"]["input_paths"] == ["data/raw/proof_pile.txt"]
    assert cfg["bpe"]["vocab_size"] == 64000
