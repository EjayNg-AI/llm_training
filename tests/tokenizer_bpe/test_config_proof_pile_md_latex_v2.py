from __future__ import annotations

from pathlib import Path

from tokenizer_bpe.config import load_config


ROOT = Path(__file__).resolve().parents[2]


def test_proof_pile_md_latex_v2_config_loads_expected_values():
    cfg = load_config(ROOT / "configs" / "tokenizer_bpe_proof_pile_md_latex_v2_train.yaml")

    assert cfg["run"]["output_dir"] == "artifacts/tokenizer/runs_proof_pile_md_latex_v2_train"
    assert cfg["data"]["input_paths"] == ["data/raw/proof_pile.txt"]
    assert cfg["data"]["normalize"] == "none"
    assert cfg["data"]["num_workers"] == 3
    assert cfg["data"]["batch_lines"] == 1500
    assert cfg["pretokenizer"]["pattern"] == "md_latex_fast_v2"
    assert cfg["checkpointing"]["stage1_cap_every_batches"] == 50
    assert cfg["checkpointing"]["stage1_cap_start_lines"] == 5000
    assert cfg["checkpointing"]["stage1_cap_safety_factor"] == 1.05
    assert cfg["bpe"]["vocab_size"] == 64000
