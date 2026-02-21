#!/usr/bin/env python3
"""Submit and monitor an OpenAI Responses API background task."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI


TERMINAL_STATUSES = {"completed", "failed", "cancelled", "expired", "incomplete"}


def _configure_line_buffering() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass


def _emit(event: str, **fields: Any) -> None:
    payload: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
    }
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=True), flush=True)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}") from exc


def _load_input(args: argparse.Namespace) -> Any:
    if args.messages_json_file is not None:
        text = _read_text(Path(args.messages_json_file))
        try:
            messages = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON in {args.messages_json_file}: {exc}") from exc

        if not isinstance(messages, list):
            raise RuntimeError(
                f"{args.messages_json_file} must contain a JSON array for input=[...]."
            )

        return messages

    if args.prompt is not None:
        messages = []
        if args.system_prompt is not None:
            messages.append(
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": args.system_prompt}],
                }
            )
        if args.developer_prompt is not None:
            messages.append(
                {
                    "role": "developer",
                    "content": [{"type": "input_text", "text": args.developer_prompt}],
                }
            )
        messages.append(
            {
                "role": "user",
                "content": [{"type": "input_text", "text": args.prompt}],
            }
        )
        return messages

    if args.prompt_file is not None:
        prompt_text = _read_text(Path(args.prompt_file))
        messages = []
        if args.system_prompt is not None:
            messages.append(
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": args.system_prompt}],
                }
            )
        if args.developer_prompt is not None:
            messages.append(
                {
                    "role": "developer",
                    "content": [{"type": "input_text", "text": args.developer_prompt}],
                }
            )
        messages.append(
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt_text}],
            }
        )
        return messages

    if args.input_json_file is not None:
        text = _read_text(Path(args.input_json_file))
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON in {args.input_json_file}: {exc}") from exc

    raise RuntimeError("No input source provided.")


def _to_plain_json(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump()  # type: ignore[no-any-return]
    if hasattr(response, "model_dump_json"):
        return json.loads(response.model_dump_json())  # type: ignore[no-any-return]
    if hasattr(response, "to_dict"):
        return response.to_dict()  # type: ignore[no-any-return]
    return {"repr": repr(response)}


def _extract_output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str):
        return text
    return ""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Submit a background Responses API task and poll until terminal status."
    )
    parser.add_argument(
        "--model",
        default="gpt-5.2",
        help="Model name (user-configurable). Default: gpt-5.2.",
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--prompt", help="Plain user prompt text.")
    input_group.add_argument("--prompt-file", help="Path to a UTF-8 prompt text file.")
    input_group.add_argument(
        "--messages-json-file",
        help="Path to JSON file containing full message array input=[...].",
    )
    input_group.add_argument(
        "--input-json-file",
        help="Path to JSON file for the full Responses API 'input' field.",
    )
    parser.add_argument(
        "--system-prompt",
        help="Optional system message prepended when using --prompt/--prompt-file.",
    )
    parser.add_argument(
        "--developer-prompt",
        help="Optional developer message prepended when using --prompt/--prompt-file.",
    )

    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=10.0,
        help="Polling interval in seconds (default: 10).",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=0,
        help="Maximum total wait time. 0 disables timeout.",
    )
    parser.add_argument(
        "--verbosity",
        choices=("low", "medium", "high"),
        default="medium",
        help="Responses API text verbosity (user-configurable). Default: medium.",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh"),
        default="medium",
        help="Responses API reasoning effort (user-configurable). Default: medium.",
    )
    parser.add_argument(
        "--show-output-text",
        action="store_true",
        help="Print final output_text if available.",
    )
    parser.add_argument(
        "--output-json-file",
        help="Write final response payload JSON to this path.",
    )
    return parser


def _poll_to_terminal(
    client: OpenAI,
    response_id: str,
    poll_seconds: float,
    max_wait_seconds: int,
) -> Any:
    started = time.monotonic()
    attempt = 0

    while True:
        attempt += 1
        response = client.responses.retrieve(response_id)
        status = getattr(response, "status", "unknown")
        elapsed_seconds = int(time.monotonic() - started)

        _emit(
            "poll",
            response_id=response_id,
            attempt=attempt,
            status=status,
            elapsed_seconds=elapsed_seconds,
        )

        if status in TERMINAL_STATUSES:
            return response

        if max_wait_seconds > 0 and elapsed_seconds >= max_wait_seconds:
            raise TimeoutError(
                f"Polling timed out after {elapsed_seconds} seconds (max {max_wait_seconds})."
            )

        time.sleep(poll_seconds)


def main() -> int:
    _configure_line_buffering()
    parser = _build_parser()
    args = parser.parse_args()

    if args.poll_seconds <= 0:
        parser.error("--poll-seconds must be greater than 0.")
    if args.max_wait_seconds < 0:
        parser.error("--max-wait-seconds must be >= 0.")

    try:
        input_data = _load_input(args)
        _emit(
            "submit_start",
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            verbosity=args.verbosity,
            poll_seconds=args.poll_seconds,
        )

        client = OpenAI()
        created = client.responses.create(
            model=args.model,
            input=input_data,
            text={"format": {"type": "text"}, "verbosity": args.verbosity},
            reasoning={"effort": args.reasoning_effort},
            background=True,
        )

        response_id = getattr(created, "id", None)
        if not response_id:
            raise RuntimeError("Responses API did not return a response id.")

        _emit(
            "submitted",
            response_id=response_id,
            status=getattr(created, "status", "unknown"),
        )

        final_response = _poll_to_terminal(
            client=client,
            response_id=response_id,
            poll_seconds=args.poll_seconds,
            max_wait_seconds=args.max_wait_seconds,
        )
        final_status = getattr(final_response, "status", "unknown")
        _emit("final", response_id=response_id, status=final_status)

        if args.output_json_file:
            output_path = Path(args.output_json_file)
            output_path.write_text(
                json.dumps(_to_plain_json(final_response), indent=2, ensure_ascii=True),
                encoding="utf-8",
            )
            _emit("wrote_json", path=str(output_path))

        if args.show_output_text:
            output_text = _extract_output_text(final_response)
            if output_text:
                print("===OUTPUT_TEXT_BEGIN===", flush=True)
                print(output_text, flush=True)
                print("===OUTPUT_TEXT_END===", flush=True)
            else:
                _emit("output_text_missing", response_id=response_id)

        return 0 if final_status == "completed" else 2
    except TimeoutError as exc:
        _emit("timeout", message=str(exc))
        return 3
    except KeyboardInterrupt:
        _emit("cancelled_by_user")
        return 130
    except Exception as exc:
        _emit("error", error_type=type(exc).__name__, message=str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
