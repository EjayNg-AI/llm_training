"""Persist a tokenizer artifact for the tiny training pipeline."""

from pathlib import Path

from transformers import AutoTokenizer


def main():
    tok = AutoTokenizer.from_pretrained("gpt2")
    tok.pad_token = tok.eos_token

    out_dir = Path("artifacts/tokenizer/gpt2")
    out_dir.mkdir(parents=True, exist_ok=True)
    tok.save_pretrained(out_dir)
    print(f"Saved tokenizer artifact to: {out_dir}")


if __name__ == "__main__":
    main()
