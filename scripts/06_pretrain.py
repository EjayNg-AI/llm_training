"""Run tiny GPT-style pretraining from packed token blocks."""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import random
import shutil
import struct
from typing import Any

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

import numpy as np
import torch
from transformers import GPT2Config, GPT2LMHeadModel

from llm_training.infra.hashing import stable_hash_object
from llm_training.infra.io_atomic import atomic_write_bytes
from llm_training.infra.logging import setup_logger
from llm_training.infra.manifest import (
    build_artifact_manifest,
    collect_checksums,
    find_artifact,
    latest_artifact,
    publish_artifact,
    resolve_artifact_dir,
)
from llm_training.infra.resume import assert_resume_compatible
from llm_training.infra.run_dir import begin_run, end_run, make_run_context, write_stage_metric, write_state

from pipeline_common import load_artifact_manifest_from_entry, load_yaml_config


DEFAULT_CONFIG: dict[str, Any] = {
    "run": {
        "output_dir": "artifacts/runs/06_pretrain",
        "log_level": "INFO",
        "structured_logs": True,
    },
    "artifacts_root": "artifacts",
    "input": {
        "packed_id": None,
        "tokenizer_id": None,
    },
    "model": {
        "n_embd": 384,
        "n_layer": 6,
        "n_head": 6,
    },
    "training": {
        "seed": 0,
        "max_steps": 200,
        "batch_size": 8,
        "learning_rate": 0.0003,
        "weight_decay": 0.01,
        "warmup_steps": 20,
        "eval_every": 50,
        "eval_batches": 10,
        "save_every": 50,
        "artifact_id": None,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/train.yaml", help="Path to pretrain stage config YAML.")
    parser.add_argument("--run-id", default=None, help="Optional run identifier under run.output_dir.")
    parser.add_argument("--resume", action="store_true", help="Resume from latest run checkpoint.")
    parser.add_argument("--packed-id", default=None, help="Input packed dataset artifact id.")
    parser.add_argument("--tokenizer-id", default=None, help="Tokenizer artifact id.")
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


def _save_checkpoint(
    path: Path,
    *,
    model: GPT2LMHeadModel,
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LambdaLR,
    step: int,
) -> None:
    payload = {
        "step": step,
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "scheduler_state": scheduler.state_dict(),
        "rng_state": {
            "python": random.getstate(),
            "numpy": np.random.get_state(),
            "torch": torch.random.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        },
    }
    buffer = io.BytesIO()
    torch.save(payload, buffer)
    atomic_write_bytes(path, buffer.getvalue())


def _latest_checkpoint(checkpoints_dir: Path) -> Path | None:
    checkpoints = sorted(checkpoints_dir.glob("step_*.pt"))
    if not checkpoints:
        return None
    return checkpoints[-1]


def _restore_checkpoint(
    path: Path,
    *,
    model: GPT2LMHeadModel,
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LambdaLR,
) -> int:
    payload = torch.load(path, map_location="cpu")
    model.load_state_dict(payload["model_state"])
    optimizer.load_state_dict(payload["optimizer_state"])
    scheduler.load_state_dict(payload["scheduler_state"])

    rng_state = payload.get("rng_state", {})
    if "python" in rng_state:
        random.setstate(rng_state["python"])
    if "numpy" in rng_state:
        np.random.set_state(rng_state["numpy"])
    if "torch" in rng_state:
        torch.random.set_rng_state(rng_state["torch"])
    if torch.cuda.is_available() and rng_state.get("cuda") is not None:
        torch.cuda.set_rng_state_all(rng_state["cuda"])

    return int(payload["step"])


def _evaluate(
    *,
    model: GPT2LMHeadModel,
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
            outputs = model(input_ids=input_ids, labels=input_ids)
            losses.append(float(outputs.loss.item()))
    model.train()
    return float(sum(losses) / len(losses))


def _copy_tokenizer_files(tokenizer_dir: Path, model_dir: Path) -> None:
    keep = ["vocab.json", "merges.txt", "tokenizer_config.json", "special_tokens_map.json"]
    for name in keep:
        src = tokenizer_dir / name
        if src.exists():
            shutil.copy2(src, model_dir / name)


def main() -> None:
    args = parse_args()
    cfg, cfg_path = load_yaml_config(args.config, DEFAULT_CONFIG)

    run_ctx = make_run_context(
        stage_name="06_pretrain",
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
        name="pipeline.06_pretrain",
        run_dir=run_ctx.run_dir,
        log_level=cfg["run"]["log_level"],
        structured_logs=bool(cfg["run"]["structured_logs"]),
    )

    artifacts_root = Path(cfg["artifacts_root"])
    registry_path = artifacts_root / "registry.jsonl"

    packed_id = args.packed_id or cfg["input"].get("packed_id")
    if packed_id:
        packed_entry = find_artifact(registry_path, "packed", packed_id)
        if packed_entry is None:
            raise FileNotFoundError(f"Packed artifact not found: {packed_id}")
    else:
        packed_entry = latest_artifact(registry_path, "packed")
        if packed_entry is None:
            raise FileNotFoundError("No packed artifact found in registry")

    tokenizer_id = args.tokenizer_id or cfg["input"].get("tokenizer_id")
    if tokenizer_id:
        tokenizer_entry = find_artifact(registry_path, "tokenizer", tokenizer_id)
        if tokenizer_entry is None:
            raise FileNotFoundError(f"Tokenizer artifact not found: {tokenizer_id}")
    else:
        tokenizer_entry = latest_artifact(registry_path, "tokenizer")
        if tokenizer_entry is None:
            raise FileNotFoundError("No tokenizer artifact found in registry")

    packed_manifest = load_artifact_manifest_from_entry(packed_entry)
    tokenizer_manifest = load_artifact_manifest_from_entry(tokenizer_entry)

    packed_index_path = Path(packed_entry["artifact_path"]) / "index.json"
    packed_index = json.loads(packed_index_path.read_text(encoding="utf-8"))
    seq_len = int(packed_index["seq_len"])
    token_dtype = str(packed_index["token_dtype"])

    tokenizer_config_path = Path(tokenizer_entry["artifact_path"]) / "tokenizer_config.json"
    tokenizer_config = json.loads(tokenizer_config_path.read_text(encoding="utf-8"))
    vocab_size = int(tokenizer_config["vocab_size"])

    resume_signature = stable_hash_object(
        {
            "config_hash": cfg["meta"]["config_hash"],
            "packed_id": packed_manifest["artifact_id"],
            "packed_checksums": packed_manifest.get("checksums", {}),
            "tokenizer_id": tokenizer_manifest["artifact_id"],
            "tokenizer_checksums": tokenizer_manifest.get("checksums", {}),
        }
    )
    model_artifact_id = cfg["training"].get("artifact_id") or f"model_{resume_signature[:12]}"
    model_artifact_dir = resolve_artifact_dir(artifacts_root, "model", model_artifact_id)

    checkpoints_dir = run_ctx.run_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    begin_run(
        run_ctx,
        config_path=str(cfg_path.resolve()),
        inputs={
            "packed_id": packed_manifest["artifact_id"],
            "tokenizer_id": tokenizer_manifest["artifact_id"],
            "model_artifact_id": model_artifact_id,
        },
    )

    train_path = Path(packed_entry["artifact_path"]) / packed_index["splits"]["train"]["bin"]
    val_path = Path(packed_entry["artifact_path"]) / packed_index["splits"]["val"]["bin"]
    train_blocks = _load_blocks(train_path, token_dtype=token_dtype, seq_len=seq_len)
    val_blocks = _load_blocks(val_path, token_dtype=token_dtype, seq_len=seq_len)

    seed = int(cfg["training"]["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    model_cfg = GPT2Config(
        vocab_size=vocab_size,
        n_positions=seq_len,
        n_ctx=seq_len,
        n_embd=int(cfg["model"]["n_embd"]),
        n_layer=int(cfg["model"]["n_layer"]),
        n_head=int(cfg["model"]["n_head"]),
    )
    model = GPT2LMHeadModel(model_cfg)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(cfg["training"]["learning_rate"]),
        weight_decay=float(cfg["training"]["weight_decay"]),
    )
    warmup_steps = int(cfg["training"]["warmup_steps"])
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer,
        lr_lambda=lambda step: min((step + 1) / max(1, warmup_steps), 1.0),
    )

    max_steps = int(cfg["training"]["max_steps"])
    batch_size = int(cfg["training"]["batch_size"])
    eval_every = int(cfg["training"]["eval_every"])
    eval_batches = int(cfg["training"]["eval_batches"])
    save_every = int(cfg["training"]["save_every"])

    global_step = 0
    if args.resume:
        state = assert_resume_compatible(
            state_path=run_ctx.state_path,
            expected_signature=resume_signature,
            signature_field="resume_signature",
        )
        checkpoint_path = _latest_checkpoint(checkpoints_dir)
        if checkpoint_path is None:
            raise FileNotFoundError(f"Resume requested but no checkpoint exists in {checkpoints_dir}")
        global_step = _restore_checkpoint(
            checkpoint_path,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
        )
        logger.info("Resumed from checkpoint %s at step %s", checkpoint_path.name, global_step)
    else:
        if model_artifact_dir.exists() and any(model_artifact_dir.iterdir()):
            raise FileExistsError(
                f"Model artifact already exists: {model_artifact_dir}. "
                "Set training.artifact_id to publish a different model id."
            )

    model.train()

    while global_step < max_steps:
        idx = torch.randint(0, train_blocks.shape[0], (batch_size,))
        input_ids = train_blocks[idx].to(device)

        outputs = model(input_ids=input_ids, labels=input_ids)
        loss = outputs.loss
        loss.backward()

        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        scheduler.step()

        global_step += 1

        write_stage_metric(
            run_ctx,
            {
                "event": "train_step",
                "step": global_step,
                "loss": float(loss.item()),
                "lr": float(optimizer.param_groups[0]["lr"]),
            },
        )

        if global_step % eval_every == 0:
            eval_loss = _evaluate(
                model=model,
                val_blocks=val_blocks,
                batch_size=batch_size,
                num_batches=eval_batches,
                device=device,
            )
            write_stage_metric(
                run_ctx,
                {
                    "event": "eval",
                    "step": global_step,
                    "eval_loss": eval_loss,
                },
            )
            logger.info("step=%s train_loss=%.4f eval_loss=%.4f", global_step, float(loss.item()), eval_loss)

        if global_step % save_every == 0 or global_step == max_steps:
            checkpoint_path = checkpoints_dir / f"step_{global_step:08d}.pt"
            _save_checkpoint(
                checkpoint_path,
                model=model,
                optimizer=optimizer,
                scheduler=scheduler,
                step=global_step,
            )
            write_state(
                run_ctx,
                {
                    "resume_signature": resume_signature,
                    "status": "running",
                    "global_step": global_step,
                    "latest_checkpoint": str(checkpoint_path),
                    "artifact_id": model_artifact_id,
                },
            )

    model_artifact_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(model_artifact_dir)
    _copy_tokenizer_files(Path(tokenizer_entry["artifact_path"]), model_artifact_dir)

    checksums = collect_checksums(model_artifact_dir)
    run_meta = json.loads(run_ctx.run_meta_path.read_text(encoding="utf-8"))
    manifest = build_artifact_manifest(
        artifact_type="model",
        artifact_id=model_artifact_id,
        source_run_id=run_ctx.run_id,
        config_hash=cfg["meta"]["config_hash"],
        git_commit=run_meta.get("git_commit"),
        inputs=[
            {
                "artifact_type": packed_manifest["artifact_type"],
                "artifact_id": packed_manifest["artifact_id"],
                "hash": stable_hash_object(packed_manifest.get("checksums", {})),
            },
            {
                "artifact_type": tokenizer_manifest["artifact_type"],
                "artifact_id": tokenizer_manifest["artifact_id"],
                "hash": stable_hash_object(tokenizer_manifest.get("checksums", {})),
            },
        ],
        stats={
            "global_step": global_step,
            "seq_len": seq_len,
            "vocab_size": vocab_size,
            "device": device,
        },
        checksums=checksums,
    )
    publish_artifact(artifacts_root=artifacts_root, artifact_dir=model_artifact_dir, manifest=manifest)

    write_state(
        run_ctx,
        {
            "resume_signature": resume_signature,
            "status": "completed",
            "global_step": global_step,
            "artifact_id": model_artifact_id,
        },
    )
    end_run(
        run_ctx,
        status="completed",
        summary={
            "artifact_id": model_artifact_id,
            "global_step": global_step,
            "checkpoint_count": len(list(checkpoints_dir.glob("step_*.pt"))),
        },
    )
    logger.info("Pretraining complete. artifact_id=%s step=%s", model_artifact_id, global_step)


if __name__ == "__main__":
    main()
