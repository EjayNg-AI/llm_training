# Background Mode Notes

Use these rules when running OpenAI API tasks in background mode from the Codex harness.

## API Rules

- Use the Responses API (`responses.create`, `responses.retrieve`).
- Set `background=True` on create requests.
- Do not use `store=True` for background tasks.
- Omit `tools` by default for this skill. Add tools only when the user explicitly asks.
- Allow user control of generation settings on create:
- `--model` (for example `gpt-5.2` or another supported model)
- `--reasoning-effort` (`none|low|medium|high|xhigh`)
- `--verbosity` (`low|medium|high`)
- For scalable conversations, prefer `--messages-json-file` with a full `input=[...]` array containing system/developer/user/assistant turns.
- For simple one-turn calls, `--prompt` or `--prompt-file` can still be used.
- Poll periodically until terminal status (`completed`, `failed`, `cancelled`, `expired`, `incomplete`).
- Use a polling interval of 10 seconds unless the user asks for a different cadence.

## Harness Execution Rules

- Run scripts with unbuffered mode:
```bash
python -u scripts/run_background_response.py ...
```
- Keep script logs flushed (`print(..., flush=True)`), so Codex can monitor progress from stdout.
- Keep the process attached while monitoring output. If interrupted, continue polling with:
```bash
python -u scripts/monitor_background_response.py --response-id <id>
```

## Network Notes

- Codex web tools and local Python commands use different network paths.
- A web search success does not imply that local Python execution from within Codex harness can reach the OpenAI API.
- Typical minimum allowlist for local background scripts:
- Domain: `api.openai.com`
- Methods: `POST` (`/v1/responses`) and `GET` (`/v1/responses/{response_id}`)
- Optional: `POST /v1/responses/{response_id}/cancel` for cancellation
