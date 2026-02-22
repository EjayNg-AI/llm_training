"""Evaluate a model artifact with perplexity and sample generation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
from typing import Any

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from llm_training.infra.hashing import stable_hash_object
from llm_training.infra.io_atomic import atomic_dump_json, atomic_dump_text
from llm_training.infra.logging import setup_logger
from llm_training.infra.manifest import (
    build_artifact_manifest,
    collect_checksums,
    find_artifact,
    latest_artifact,
    publish_artifact,
    resolve_artifact_dir,
)
from llm_training.infra.run_dir import begin_run, end_run, make_run_context, write_stage_metric, write_state

from pipeline_common import load_artifact_manifest_from_entry, load_yaml_config


DEFAULT_CONFIG: dict[str, Any] = {
    "run": {
        "output_dir": "artifacts/runs/08_eval",
        "log_level": "INFO",
        "structured_logs": True,
    },
    "artifacts_root": "artifacts",
    "input": {
        "model_id": None,
        "packed_id": None,
    },
    "eval": {
        "num_eval_batches": 20,
        "eval_batch_size": 8,
        "max_new_tokens": 120,
        "do_sample": False,
        "temperature": 0.9,
        "top_p": 0.95,
        "artifact_id": None,
        "prompts": [
            "### Instruction:\nExplain gradient descent in one paragraph.\n\n### Response:\n",
            "### Instruction:\nWhy does deterministic data processing matter in ML pipelines?\n\n### Response:\n",
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/eval.yaml", help="Path to eval stage config YAML.")
    parser.add_argument("--run-id", default=None, help="Optional run identifier under run.output_dir.")
    parser.add_argument("--model-id", default=None, help="Model artifact id.")
    parser.add_argument("--packed-id", default=None, help="Packed dataset artifact id for perplexity evaluation.")
    return parser.parse_args()


def _read_token_stream(path: Path, token_dtype: str) -> list[int]:
    if token_dtype == "uint16":
        fmt = "<H"
        width = 2
    elif token_dtype == "uint32":
        fmt = "<I"
        width = 4
    else:
        raise ValueError(f"Unsupported token dtype: {token_dtype}")

    raw = path.read_bytes()
    if len(raw) % width != 0:
        raise ValueError(f"Corrupt token stream length: {path}")
    return [item[0] for item in struct.iter_unpack(fmt, raw)]


def _load_blocks(path: Path, *, token_dtype: str, seq_len: int) -> torch.Tensor:
    tokens = _read_token_stream(path, token_dtype)
    if len(tokens) % seq_len != 0:
        raise ValueError(f"Packed tokens are not divisible by seq_len={seq_len}: {path}")
    blocks = len(tokens) // seq_len
    if blocks == 0:
        raise ValueError(f"No blocks available in packed split: {path}")
    return torch.tensor(tokens, dtype=torch.long).view(blocks, seq_len)


def _infer_packed_id_from_model_manifest(model_manifest: dict[str, Any]) -> str | None:
    for item in model_manifest.get("inputs", []):
        if item.get("artifact_type") == "packed":
            return item.get("artifact_id")
    return None


def _evaluate_loss(
    *,
    model: AutoModelForCausalLM,
    val_blocks: torch.Tensor,
    batch_size: int,
    num_batches: int,
    device: str,
) -> float:
    model.eval()
    losses: list[float] = []
    with torch.no_grad():
        for _ in range(num_batches):
            idx = torch.randint(0, val_blocks.shape[0], (batch_size,))
            input_ids = val_blocks[idx].to(device)
            out = model(input_ids=input_ids, labels=input_ids)
            losses.append(float(out.loss.item()))
    return float(sum(losses) / len(losses))


def main() -> None:
    args = parse_args()
    cfg, cfg_path = load_yaml_config(args.config, DEFAULT_CONFIG)

    run_ctx = make_run_context(
        stage_name="08_eval",
        run_output_dir=Path(cfg["run"]["output_dir"]),
        config={k: v for k, v in cfg.items() if k != "meta"},
        run_id=args.run_id,
    )
    if run_ctx.run_dir.exists() and any(run_ctx.run_dir.iterdir()):
        raise FileExistsError(
            f"Run directory already exists and is not empty: {run_ctx.run_dir}. Use a different --run-id."
        )

    logger = setup_logger(
        name="pipeline.08_eval",
        run_dir=run_ctx.run_dir,
        log_level=cfg["run"]["log_level"],
        structured_logs=bool(cfg["run"]["structured_logs"]),
    )

    artifacts_root = Path(cfg["artifacts_root"])
    registry_path = artifacts_root / "registry.jsonl"

    model_id = args.model_id or cfg["input"].get("model_id")
    if model_id:
        model_entry = find_artifact(registry_path, "model", model_id)
        if model_entry is None:
            raise FileNotFoundError(f"Model artifact not found: {model_id}")
    else:
        model_entry = latest_artifact(registry_path, "model")
        if model_entry is None:
            raise FileNotFoundError("No model artifact found in registry")

    model_manifest = load_artifact_manifest_from_entry(model_entry)

    packed_id = args.packed_id or cfg["input"].get("packed_id") or _infer_packed_id_from_model_manifest(model_manifest)
    packed_entry = None
    packed_manifest = None
    if packed_id:
        packed_entry = find_artifact(registry_path, "packed", packed_id)
        if packed_entry is None:
            raise FileNotFoundError(f"Packed artifact not found: {packed_id}")
        packed_manifest = load_artifact_manifest_from_entry(packed_entry)

    resume_signature = stable_hash_object(
        {
            "config_hash": cfg["meta"]["config_hash"],
            "model_id": model_manifest["artifact_id"],
            "model_checksums": model_manifest.get("checksums", {}),
            "packed_id": packed_manifest["artifact_id"] if packed_manifest else None,
            "packed_checksums": packed_manifest.get("checksums", {}) if packed_manifest else None,
        }
    )
    eval_artifact_id = cfg["eval"].get("artifact_id") or f"eval_{resume_signature[:12]}"
    eval_dir = resolve_artifact_dir(artifacts_root, "eval", eval_artifact_id)

    if eval_dir.exists() and any(eval_dir.iterdir()):
        raise FileExistsError(
            f"Eval artifact already exists: {eval_dir}. Set eval.artifact_id to publish another evaluation run."
        )

    begin_run(
        run_ctx,
        config_path=str(cfg_path.resolve()),
        inputs={
            "model_id": model_manifest["artifact_id"],
            "packed_id": packed_manifest["artifact_id"] if packed_manifest else None,
            "eval_artifact_id": eval_artifact_id,
        },
    )

    model_dir = Path(model_entry["artifact_path"])
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_dir)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()

    eval_loss = None
    perplexity = None
    if packed_entry is not None:
        packed_index = json.loads((Path(packed_entry["artifact_path"]) / "index.json").read_text(encoding="utf-8"))
        seq_len = int(packed_index["seq_len"])
        token_dtype = str(packed_index["token_dtype"])
        val_bin = Path(packed_entry["artifact_path"]) / packed_index["splits"]["val"]["bin"]
        val_blocks = _load_blocks(val_bin, token_dtype=token_dtype, seq_len=seq_len)
        eval_loss = _evaluate_loss(
            model=model,
            val_blocks=val_blocks,
            batch_size=int(cfg["eval"]["eval_batch_size"]),
            num_batches=int(cfg["eval"]["num_eval_batches"]),
            device=device,
        )
        perplexity = float(math.exp(eval_loss))
        write_stage_metric(run_ctx, {"event": "perplexity_eval", "eval_loss": eval_loss, "perplexity": perplexity})

    prompts = list(cfg["eval"]["prompts"])
    samples: list[dict[str, str]] = []

    for prompt in prompts:
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=int(cfg["eval"]["max_new_tokens"]),
                do_sample=bool(cfg["eval"]["do_sample"]),
                temperature=float(cfg["eval"]["temperature"]),
                top_p=float(cfg["eval"]["top_p"]),
            )
        decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
        samples.append({"prompt": prompt, "output": decoded})

    eval_dir.mkdir(parents=True, exist_ok=True)
    atomic_dump_json(
        eval_dir / "eval.json",
        {
            "model_id": model_manifest["artifact_id"],
            "packed_id": packed_manifest["artifact_id"] if packed_manifest else None,
            "eval_loss": eval_loss,
            "perplexity": perplexity,
            "num_samples": len(samples),
        },
    )

    lines: list[str] = []
    for i, item in enumerate(samples, start=1):
        lines.append(f"=== SAMPLE {i} ===")
        lines.append("PROMPT:")
        lines.append(item["prompt"])
        lines.append("OUTPUT:")
        lines.append(item["output"])
        lines.append("")
    atomic_dump_text(eval_dir / "samples.txt", "\n".join(lines).rstrip() + "\n")

    checksums = collect_checksums(eval_dir)
    run_meta = json.loads(run_ctx.run_meta_path.read_text(encoding="utf-8"))
    inputs = [
        {
            "artifact_type": model_manifest["artifact_type"],
            "artifact_id": model_manifest["artifact_id"],
            "hash": stable_hash_object(model_manifest.get("checksums", {})),
        }
    ]
    if packed_manifest is not None:
        inputs.append(
            {
                "artifact_type": packed_manifest["artifact_type"],
                "artifact_id": packed_manifest["artifact_id"],
                "hash": stable_hash_object(packed_manifest.get("checksums", {})),
            }
        )

    manifest = build_artifact_manifest(
        artifact_type="eval",
        artifact_id=eval_artifact_id,
        source_run_id=run_ctx.run_id,
        config_hash=cfg["meta"]["config_hash"],
        git_commit=run_meta.get("git_commit"),
        inputs=inputs,
        stats={
            "model_id": model_manifest["artifact_id"],
            "packed_id": packed_manifest["artifact_id"] if packed_manifest else None,
            "eval_loss": eval_loss,
            "perplexity": perplexity,
            "num_samples": len(samples),
        },
        checksums=checksums,
    )
    publish_artifact(artifacts_root=artifacts_root, artifact_dir=eval_dir, manifest=manifest)

    write_state(
        run_ctx,
        {
            "resume_signature": resume_signature,
            "status": "completed",
            "artifact_id": eval_artifact_id,
            "eval_loss": eval_loss,
            "perplexity": perplexity,
            "num_samples": len(samples),
        },
    )
    end_run(
        run_ctx,
        status="completed",
        summary={
            "artifact_id": eval_artifact_id,
            "model_id": model_manifest["artifact_id"],
            "eval_loss": eval_loss,
            "perplexity": perplexity,
        },
    )
    logger.info("Eval complete. artifact_id=%s model_id=%s", eval_artifact_id, model_manifest["artifact_id"])


if __name__ == "__main__":
    main()
