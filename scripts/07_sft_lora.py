"""Run lightweight LoRA SFT from a published base model artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from datasets import Dataset, load_dataset
from peft import LoraConfig, TaskType, get_peft_model
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

from llm_training.infra.hashing import stable_hash_object
from llm_training.infra.logging import setup_logger
from llm_training.infra.manifest import (
    build_artifact_manifest,
    collect_checksums,
    find_artifact,
    latest_artifact,
    publish_artifact,
    resolve_artifact_dir,
)
from llm_training.infra.run_dir import begin_run, end_run, make_run_context, write_state

from pipeline_common import load_artifact_manifest_from_entry, load_yaml_config


DEFAULT_CONFIG: dict[str, Any] = {
    "run": {
        "output_dir": "artifacts/runs/07_sft_lora",
        "log_level": "INFO",
        "structured_logs": True,
    },
    "artifacts_root": "artifacts",
    "input": {
        "base_model_id": None,
    },
    "training": {
        "seed": 0,
        "max_steps": 200,
        "batch_size": 4,
        "gradient_accumulation_steps": 4,
        "learning_rate": 0.0002,
        "eval_steps": 100,
        "save_steps": 100,
        "artifact_id": None,
        "dataset_rows": 2000,
        "max_length": 256,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/sft.yaml", help="Path to SFT stage config YAML.")
    parser.add_argument("--run-id", default=None, help="Optional run identifier under run.output_dir.")
    parser.add_argument("--base-model-id", default=None, help="Base model artifact id.")
    parser.add_argument("--resume", action="store_true", help="Resume from latest Trainer checkpoint.")
    return parser.parse_args()


def _format_example(example: dict[str, Any]) -> dict[str, str]:
    prompt = f"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['output']}\n"
    return {"text": prompt}


def _load_instruction_data(max_rows: int) -> Dataset:
    try:
        ds = load_dataset("tatsu-lab/alpaca", split=f"train[:{max_rows}]")
    except Exception:
        examples = [
            {
                "instruction": "Explain supervised fine-tuning in one sentence.",
                "output": "Supervised fine-tuning teaches a pretrained model to follow instruction-response examples.",
            },
            {
                "instruction": "What is overfitting?",
                "output": "Overfitting occurs when a model memorizes training data and performs poorly on new data.",
            },
            {
                "instruction": "Why is data provenance important?",
                "output": "It supports reproducibility and compliance by preserving dataset lineage and licensing details.",
            },
            {
                "instruction": "Describe a checkpoint.",
                "output": "A checkpoint saves model and optimizer state so training can resume safely after interruption.",
            },
        ]
        ds = Dataset.from_list(examples)

    ds = ds.map(_format_example, remove_columns=ds.column_names)
    return ds


def main() -> None:
    args = parse_args()
    cfg, cfg_path = load_yaml_config(args.config, DEFAULT_CONFIG)

    run_ctx = make_run_context(
        stage_name="07_sft_lora",
        run_output_dir=Path(cfg["run"]["output_dir"]),
        config={k: v for k, v in cfg.items() if k != "meta"},
        run_id=args.run_id,
    )
    if not args.resume and run_ctx.run_dir.exists() and any(run_ctx.run_dir.iterdir()):
        raise FileExistsError(
            f"Run directory already exists and is not empty: {run_ctx.run_dir}. "
            "Use --resume or provide a different --run-id."
        )

    logger = setup_logger(
        name="pipeline.07_sft_lora",
        run_dir=run_ctx.run_dir,
        log_level=cfg["run"]["log_level"],
        structured_logs=bool(cfg["run"]["structured_logs"]),
    )

    artifacts_root = Path(cfg["artifacts_root"])
    registry_path = artifacts_root / "registry.jsonl"

    base_model_id = args.base_model_id or cfg["input"].get("base_model_id")
    if base_model_id:
        model_entry = find_artifact(registry_path, "model", base_model_id)
        if model_entry is None:
            raise FileNotFoundError(f"Base model artifact not found: {base_model_id}")
    else:
        model_entry = latest_artifact(registry_path, "model")
        if model_entry is None:
            raise FileNotFoundError("No model artifact found in registry")

    model_manifest = load_artifact_manifest_from_entry(model_entry)
    model_dir = Path(model_entry["artifact_path"])

    resume_signature = stable_hash_object(
        {
            "config_hash": cfg["meta"]["config_hash"],
            "base_model_id": model_manifest["artifact_id"],
            "base_model_checksums": model_manifest.get("checksums", {}),
        }
    )
    sft_artifact_id = cfg["training"].get("artifact_id") or f"sft_{resume_signature[:12]}"
    sft_dir = resolve_artifact_dir(artifacts_root, "model", sft_artifact_id)

    if not args.resume and sft_dir.exists() and any(sft_dir.iterdir()):
        raise FileExistsError(
            f"SFT artifact already exists: {sft_dir}. "
            "Set training.artifact_id to publish another adapter model id."
        )

    begin_run(
        run_ctx,
        config_path=str(cfg_path.resolve()),
        inputs={"base_model_id": model_manifest["artifact_id"], "sft_artifact_id": sft_artifact_id},
    )

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_dir)

    ds = _load_instruction_data(int(cfg["training"]["dataset_rows"]))

    def tokenize(batch: dict[str, list[str]]) -> dict[str, list[list[int]]]:
        return tokenizer(batch["text"], truncation=True, max_length=int(cfg["training"]["max_length"]))

    ds_tok = ds.map(tokenize, batched=True, remove_columns=["text"]).train_test_split(test_size=0.1, seed=0)

    lora_cfg = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_cfg)

    training_args = TrainingArguments(
        output_dir=str(run_ctx.run_dir / "trainer_output"),
        per_device_train_batch_size=int(cfg["training"]["batch_size"]),
        per_device_eval_batch_size=int(cfg["training"]["batch_size"]),
        gradient_accumulation_steps=int(cfg["training"]["gradient_accumulation_steps"]),
        learning_rate=float(cfg["training"]["learning_rate"]),
        max_steps=int(cfg["training"]["max_steps"]),
        logging_steps=25,
        eval_steps=int(cfg["training"]["eval_steps"]),
        save_steps=int(cfg["training"]["save_steps"]),
        evaluation_strategy="steps",
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        seed=int(cfg["training"]["seed"]),
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=ds_tok["train"],
        eval_dataset=ds_tok["test"],
    )

    if args.resume:
        trainer.train(resume_from_checkpoint=True)
    else:
        trainer.train()

    sft_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(sft_dir)
    tokenizer.save_pretrained(sft_dir)

    checksums = collect_checksums(sft_dir)
    run_meta = json.loads(run_ctx.run_meta_path.read_text(encoding="utf-8"))
    manifest = build_artifact_manifest(
        artifact_type="model",
        artifact_id=sft_artifact_id,
        source_run_id=run_ctx.run_id,
        config_hash=cfg["meta"]["config_hash"],
        git_commit=run_meta.get("git_commit"),
        inputs=[
            {
                "artifact_type": model_manifest["artifact_type"],
                "artifact_id": model_manifest["artifact_id"],
                "hash": stable_hash_object(model_manifest.get("checksums", {})),
            }
        ],
        stats={
            "base_model_id": model_manifest["artifact_id"],
            "max_steps": int(cfg["training"]["max_steps"]),
            "dataset_rows": int(cfg["training"]["dataset_rows"]),
        },
        checksums=checksums,
        extra={"model_variant": "lora_sft"},
    )
    publish_artifact(artifacts_root=artifacts_root, artifact_dir=sft_dir, manifest=manifest)

    write_state(
        run_ctx,
        {
            "resume_signature": resume_signature,
            "status": "completed",
            "artifact_id": sft_artifact_id,
        },
    )
    end_run(
        run_ctx,
        status="completed",
        summary={
            "artifact_id": sft_artifact_id,
            "base_model_id": model_manifest["artifact_id"],
        },
    )
    logger.info("SFT complete. artifact_id=%s base_model_id=%s", sft_artifact_id, model_manifest["artifact_id"])


if __name__ == "__main__":
    main()
