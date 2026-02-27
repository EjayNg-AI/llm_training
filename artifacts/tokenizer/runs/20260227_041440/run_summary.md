# OpenWebText BPE Tokenizer Training Summary

## Run Identity
- Run ID: `20260227_041440`
- Artifact ID: `tokenizer_080f21e74d7f`
- Artifact Type: `tokenizer`
- Source Run ID (manifest): `20260227_041440`
- Created At (UTC): `2026-02-27T04:35:31Z`
- Git Commit: `d21d3ba5759fd6643749fb38c92b9a300cd87714`

## Timing
- Training Started (UTC): `2026-02-27T04:14:40Z`
- Training Ended (UTC): `2026-02-27T04:35:31Z`
- Elapsed Seconds (telemetry): `1250.9259462580012`
- Elapsed Seconds (manifest stats): `1250.90442454`
- Approx Duration: `20m 50.9s`

## Core Training Statistics
- Vocab Size: `32000`
- Number of Learned Merges: `31742`
- Final Merge Index: `31742`
- Pretokenizer Alias: `gpt2_fast`
- Pattern Hash: `0a10b5fe5e3bbecbc850fda5259aeb5dc3da062c22f6b526252f12ef00ee3667`
- Config Hash: `cd55db9c2f1afc0436ed359bc7a4f2612fbe8943de0b91f4680b8d4711a3a25b`
- Training Corpus SHA256: `99761eb96c85330ab82c1a4656e6e81bfc7953c5aa8f1a5f5ea460c44fd28edc`

## Exported Output Files
Export Directory: `artifacts/tokenizer/exports/tokenizer_080f21e74d7f`

| File | Size | SHA256 |
|---|---:|---|
| `vocab.json` | 618K | `a010b40e5f01c02491589efe7953124c2d0f8068cf85c4a2479fed1e746f8d77` |
| `merges.txt` | 284K | `09ffadf7509f4ecc02de7200624dd0195d249412565b897cc350f693d5bf6427` |
| `tokenizer_config.json` | 791B | `bc3a3b3777e7a8db7c8d476a7a8ae91e62b538d700a180421562b32a90e4f9db` |
| `special_tokens_map.json` | 125B | `3c6bf7c09d5473c303cee8575a22bb51e5153c17d177a721b43cd4785c6d09ae` |
| `training_stats.json` | 403B | `04d994989cc3e86fdbb02ea4cdfba8724265f714cc42b34dd667717eccbabe3a` |
| `artifact_manifest.json` | 1.4K | *(manifest root file)* |

## Quick Validation: No Checkpointing / No Memory Monitoring
- Run directory contents are minimal and include only `training_telemetry.json` plus this summary.
- No checkpoint files were produced for this run.
- Telemetry includes start/end/elapsed only; no memory metrics are recorded.

## Source Files Used For This Summary
- `artifacts/tokenizer/runs/20260227_041440/training_telemetry.json`
- `artifacts/tokenizer/exports/tokenizer_080f21e74d7f/training_stats.json`
- `artifacts/tokenizer/exports/tokenizer_080f21e74d7f/artifact_manifest.json`
- `artifacts/tokenizer/exports/tokenizer_080f21e74d7f/tokenizer_config.json`
