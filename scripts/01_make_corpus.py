"""Create a tiny raw corpus for the laptop pipeline."""

from pathlib import Path
from typing import Iterable

import random


def clean(line: str) -> str:
    line = " ".join(line.strip().split())
    return line


def default_lines() -> Iterable[str]:
    samples = [
        "Machine learning models learn patterns from data.",
        "Good data pipelines are versioned and reproducible.",
        "Tokenization converts text to model-readable tokens.",
        "Training safety and evaluation gates should run on every release.",
        "LLM systems need governance, observability, and auditability.",
        "Clean data is usually more important than larger models.",
        "Checkpointing frequently protects long-running training jobs.",
        "LoRA fine-tuning is an efficient way to adapt language models.",
        "Always track dataset provenance and licensing.",
        "Evaluation drift can hide until production traffic changes.",
    ]
    # Repeat with lightweight variation for a minimal dataset.
    while True:
        for i, item in enumerate(samples):
            yield clean(f"{item} #{i + 1}")


def load_from_hub():
    try:
        from datasets import load_dataset
    except Exception:
        return None

    try:
        return load_dataset("wikitext", "wikitext-2-raw-v1")
    except Exception:
        return None


def main():
    out_dir = Path("data/raw")
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = load_from_hub()
    if ds is not None:
        splits = ["train", "validation", "test"]
        source = {s: ds[s]["text"] for s in splits}
        print("Loaded corpus from Hugging Face wikitext-2-raw-v1.")
    else:
        # Fallback local corpus for environments without network access.
        source = {
            "train": list(default_lines()),
            "validation": list(default_lines()),
            "test": list(default_lines()),
        }
        print("Falling back to bundled mini-corpus.")

    for split in ["train", "validation", "test"]:
        out_path = out_dir / f"{split}.txt"
        lines = source[split]
        if not isinstance(lines, list):
            lines = [x for x in lines]

        # Keep small files lightweight for local runs.
        selected = random.sample(lines, min(1000, len(lines))) if len(lines) > 1000 else list(lines)
        with out_path.open("w", encoding="utf-8") as f:
            for t in selected:
                t = clean(t)
                if len(t) >= 20:
                    f.write(t + "\n")
        print(f"Wrote {len(selected)} lines to {out_path}")


if __name__ == "__main__":
    main()
