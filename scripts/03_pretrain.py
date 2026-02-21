"""Train a tiny causal language model from the local text corpus."""

from pathlib import Path

import math
import torch
from datasets import Dataset, DatasetDict, load_dataset
from transformers import (
    AutoTokenizer,
    GPT2Config,
    GPT2LMHeadModel,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)


def _load_corpus():
    data_files = {
        "train": "data/raw/train.txt",
        "validation": "data/raw/validation.txt",
    }
    try:
        ds = load_dataset("text", data_files=data_files)
    except Exception:
        # Fallback to tiny built-in text
        samples = {
            "train": ["A reproducible pipeline starts with clean text."] * 512,
            "validation": ["Validation text should be stable."] * 128,
        }
        ds = DatasetDict(
            train=Dataset.from_dict({"text": samples["train"]}),
            validation=Dataset.from_dict({"text": samples["validation"]}),
        )
        print("Using fallback tiny in-memory corpus.")
    return ds


def main():
    tokenizer_dir = Path("artifacts/tokenizer/gpt2")
    if not tokenizer_dir.exists():
        raise FileNotFoundError("Tokenizer artifact missing. Run scripts/02_train_tokenizer.py first.")

    tok = AutoTokenizer.from_pretrained(tokenizer_dir)
    tok.pad_token = tok.eos_token

    ds = _load_corpus()
    block_size = 256

    def tokenize(batch):
        return tok(batch["text"], truncation=False)

    tok_ds = ds.map(tokenize, batched=True, remove_columns=["text"])

    def group_texts(examples):
        concat = {k: sum(examples[k], []) for k in examples.keys()}
        total_len = (len(concat["input_ids"]) // block_size) * block_size
        result = {
            k: [t[i : i + block_size] for i in range(0, total_len, block_size)]
            for k, t in concat.items()
        }
        result["labels"] = result["input_ids"].copy()
        return result

    lm_ds = tok_ds.map(group_texts, batched=True)

    config = GPT2Config(
        vocab_size=tok.vocab_size,
        n_positions=block_size,
        n_ctx=block_size,
        n_embd=384,
        n_layer=6,
        n_head=6,
    )
    model = GPT2LMHeadModel(config)
    model.gradient_checkpointing_enable()

    out_dir = Path("artifacts/models/tiny-gpt2-from-scratch")
    out_dir.mkdir(parents=True, exist_ok=True)

    fp16_enabled = torch.cuda.is_available()
    args = TrainingArguments(
        output_dir=str(out_dir),
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        gradient_accumulation_steps=4,
        learning_rate=3e-4,
        warmup_steps=50,
        max_steps=400,
        logging_steps=25,
        eval_steps=100,
        save_steps=100,
        evaluation_strategy="steps",
        save_total_limit=2,
        fp16=fp16_enabled,
        report_to=[],
    )

    collator = DataCollatorForLanguageModeling(tok, mlm=False)
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=lm_ds["train"],
        eval_dataset=lm_ds["validation"],
        data_collator=collator,
    )
    trainer.train()
    trainer.save_model(out_dir)
    tok.save_pretrained(out_dir)

    eval_out = trainer.evaluate()
    print("eval_loss:", eval_out["eval_loss"], "perplexity:", math.exp(eval_out["eval_loss"]))


if __name__ == "__main__":
    main()
