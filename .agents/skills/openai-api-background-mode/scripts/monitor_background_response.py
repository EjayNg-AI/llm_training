#!/usr/bin/env python3
"""Poll an existing OpenAI Responses API background task by response id."""

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
        description="Poll an existing Responses API response_id until terminal status."
    )
    parser.add_argument("--response-id", required=True, help="Responses API response id.")
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
        "--show-output-text",
        action="store_true",
        help="Print final output_text if available.",
    )
    parser.add_argument(
        "--output-json-file",
        help="Write final response payload JSON to this path.",
    )
    return parser


def main() -> int:
    _configure_line_buffering()
    parser = _build_parser()
    args = parser.parse_args()

    if args.poll_seconds <= 0:
        parser.error("--poll-seconds must be greater than 0.")
    if args.max_wait_seconds < 0:
        parser.error("--max-wait-seconds must be >= 0.")

    try:
        client = OpenAI()
        started = time.monotonic()
        attempt = 0

        while True:
            attempt += 1
            response = client.responses.retrieve(args.response_id)
            status = getattr(response, "status", "unknown")
            elapsed_seconds = int(time.monotonic() - started)

            _emit(
                "poll",
                response_id=args.response_id,
                attempt=attempt,
                status=status,
                elapsed_seconds=elapsed_seconds,
            )

            if status in TERMINAL_STATUSES:
                _emit("final", response_id=args.response_id, status=status)

                if args.output_json_file:
                    output_path = Path(args.output_json_file)
                    output_path.write_text(
                        json.dumps(_to_plain_json(response), indent=2, ensure_ascii=True),
                        encoding="utf-8",
                    )
                    _emit("wrote_json", path=str(output_path))

                if args.show_output_text:
                    output_text = _extract_output_text(response)
                    if output_text:
                        print("===OUTPUT_TEXT_BEGIN===", flush=True)
                        print(output_text, flush=True)
                        print("===OUTPUT_TEXT_END===", flush=True)
                    else:
                        _emit("output_text_missing", response_id=args.response_id)

                return 0 if status == "completed" else 2

            if args.max_wait_seconds > 0 and elapsed_seconds >= args.max_wait_seconds:
                raise TimeoutError(
                    f"Polling timed out after {elapsed_seconds} seconds (max {args.max_wait_seconds})."
                )

            time.sleep(args.poll_seconds)
    except TimeoutError as exc:
        _emit("timeout", message=str(exc), response_id=args.response_id)
        return 3
    except KeyboardInterrupt:
        _emit("cancelled_by_user", response_id=args.response_id)
        return 130
    except Exception as exc:
        _emit(
            "error",
            error_type=type(exc).__name__,
            message=str(exc),
            response_id=args.response_id,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
