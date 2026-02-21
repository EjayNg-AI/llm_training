"""Run a quick sanity-generation check on a trained checkpoint."""

from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


def main():
    candidate_primary = Path("artifacts/models/tiny-gpt2-sft-lora")
    candidate_fallback = Path("artifacts/models/tiny-gpt2-from-scratch")

    if candidate_primary.exists():
        model_dir = candidate_primary
    elif candidate_fallback.exists():
        model_dir = candidate_fallback
    else:
        raise FileNotFoundError("No trained model found. Run pretrain and optionally SFT first.")

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_dir)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()

    prompt = (
        "### Instruction:\n"
        "Explain gradient descent in one paragraph.\n\n"
        "### Response:\n"
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=120,
            do_sample=True,
            temperature=0.9,
            top_p=0.95,
        )

    print(tokenizer.decode(outputs[0], skip_special_tokens=True))


if __name__ == "__main__":
    main()
