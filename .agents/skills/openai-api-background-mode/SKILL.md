---
name: openai-api-background-mode
description: Create and run Python scripts that submit OpenAI Responses API requests in background mode, poll response status periodically, and stream progress with unbuffered stdout so Codex can monitor long-running jobs in the harness. Use when tasks require background=True calls, response_id polling, or live progress monitoring from python -u output.
---

# OpenAI API Background Mode

Use this skill to run long OpenAI tasks from local Python scripts while keeping progress visible in Codex.

## Preconditions

- Verify `OPENAI_API_KEY` is set in the shell environment before running scripts.
- Verify local command execution has outbound access to `api.openai.com`.
- Prefer `python -u` so Codex receives unbuffered progress lines immediately.

## Core Workflow

1. Choose the script:
- Use `scripts/run_background_response.py` to submit a new background job and poll it.
- Use `scripts/monitor_background_response.py` to poll an existing `response_id`.

2. Collect user-specified generation settings:
- `model`: use `--model` (default: `gpt-5.2`).
- `reasoning effort`: use `--reasoning-effort` with `none|low|medium|high|xhigh` (default: `medium`).
- `verbosity`: use `--verbosity` with `low|medium|high` (default: `medium`).
- If the user does not specify values, keep defaults and proceed.

3. Run the script in unbuffered mode:
```bash
python -u scripts/run_background_response.py \
  --model gpt-5.2 \
  --reasoning-effort medium \
  --verbosity medium \
  --prompt "Analyze this dataset and produce an executive summary." \
  --poll-seconds 10 \
  --show-output-text
```

4. Use this request shape for create calls (omit `tools` unless explicitly requested):
```python
response = client.responses.create(
    model="gpt-5.2",
    input=[],
    text={
        "format": {"type": "text"},
        "verbosity": "high",
    },
    reasoning={
        "effort": "high",
    },
    background=True,
)
```

5. For scalable multi-turn/multi-role context, pass a full message array using `--messages-json-file`.

Example `messages.json`:
```json
[
  {
    "role": "system",
    "content": [{"type": "input_text", "text": "SYSTEM_PROMPT"}]
  },
  {
    "role": "developer",
    "content": [{"type": "input_text", "text": "DEVELOPER_PROMPT"}]
  },
  {
    "role": "user",
    "content": [{"type": "input_text", "text": "Give me a short critique of the lina trilogy and the afterword."}]
  },
  {
    "role": "assistant",
    "content": [{"type": "output_text", "text": "Overall\\nThe Lina Trilogy is ..."}]
  },
  {
    "role": "user",
    "content": [{"type": "input_text", "text": "Write a short offshoot to the lina trilogy."}]
  }
]
```

Run:
```bash
python -u scripts/run_background_response.py \
  --messages-json-file messages.json \
  --model gpt-5.2 \
  --reasoning-effort high \
  --verbosity high \
  --poll-seconds 10 \
  --show-output-text
```

6. Monitor progress from stdout:
- Read JSON event lines (`submit_start`, `submitted`, `poll`, `final`) as the job progresses.
- Keep the process attached and continue polling output until a terminal status appears.
- If a command is interrupted after submission, keep the logged `response_id` and switch to monitor mode.

7. Poll an existing response ID when needed:
```bash
python -u scripts/monitor_background_response.py \
  --response-id resp_1234567890 \
  --poll-seconds 10 \
  --show-output-text
```

8. Handle terminal outcomes:
- Treat `completed` as success.
- Treat `failed`, `cancelled`, `expired`, and `incomplete` as unsuccessful outcomes and inspect the final payload.

## Execution Rules

- Use the Responses API (`client.responses.create` and `client.responses.retrieve`), not Chat Completions.
- Set `background=True` when creating the response.
- Do not include `store=True` in background requests.
- Omit `tools` by default for this skill. Add `tools` only when the user explicitly asks.
- Pass user-requested `model`, `reasoning effort`, and `verbosity` via CLI flags instead of hardcoding.
- Poll periodically. Default to 10 seconds unless the user requests a different cadence.
- Keep script output line-buffered and flushed so Codex can observe progress in real time.

## References

- Use `references/background_mode_notes.md` for network policy and background API constraints.
- Use script `--help` output to check all available options before editing scripts.

## Bundled Scripts

- `scripts/run_background_response.py`
- Submits a new background response.
- Polls until terminal status.
- Emits structured progress logs with `flush=True`.
- Optionally prints output text and writes final response JSON to disk.

- `scripts/monitor_background_response.py`
- Polls a previously created `response_id`.
- Emits structured progress logs with `flush=True`.
- Optionally prints output text and writes final response JSON to disk.
