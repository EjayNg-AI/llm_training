"""Fine-tune the tiny model with a small LoRA adapter."""

from pathlib import Path

from datasets import Dataset, load_dataset
from peft import LoraConfig, TaskType, get_peft_model
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer


def format_example(example):
    prompt = f"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['output']}\n"
    return {"text": prompt}


def load_instruction_data():
    try:
        ds = load_dataset("tatsu-lab/alpaca", split="train[:2000]")
    except Exception:
        examples = [
            {
                "instruction": "Explain supervised fine-tuning in one sentence.",
                "output": "Supervised fine-tuning teaches a pretrained model to follow instruction-response examples.",
            },
            {
                "instruction": "What is overfitting?",
                "output": "Overfitting occurs when a model memorizes training data and does poorly on new data.",
            },
            {
                "instruction": "Why is data provenance important?",
                "output": "It enables reproducibility and compliance when validating dataset lineage and licenses.",
            },
            {
                "instruction": "Describe a checkpoint.",
                "output": "A checkpoint saves model state so training can resume safely after interruption.",
            },
        ]
        ds = Dataset.from_list(examples)
    ds = ds.map(format_example, remove_columns=ds.column_names)
    return ds


def main():
    base = Path("artifacts/models/tiny-gpt2-from-scratch")
    if not base.exists():
        raise FileNotFoundError("Base checkpoint missing. Run scripts/03_pretrain.py first.")

    tokenizer = AutoTokenizer.from_pretrained(base)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(base)

    ds = load_instruction_data()

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=256)

    ds_tok = ds.map(tokenize, batched=True, remove_columns=["text"]).train_test_split(test_size=0.1, seed=0)

    lora_cfg = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_cfg)

    out_dir = Path("artifacts/models/tiny-gpt2-sft-lora")
    out_dir.mkdir(parents=True, exist_ok=True)

    args = TrainingArguments(
        output_dir=str(out_dir),
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        max_steps=200,
        logging_steps=50,
        eval_steps=100,
        save_steps=100,
        evaluation_strategy="steps",
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ds_tok["train"],
        eval_dataset=ds_tok["test"],
    )
    trainer.train()
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"Saved LoRA-adapted model to {out_dir}")


if __name__ == "__main__":
    main()
