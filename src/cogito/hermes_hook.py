from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import CogitoEventRequest, DEFAULT_LEDGER_PATH, record_generation_cycle


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _shell_hook_to_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("hook_event_name") != "post_api_request":
        return {}
    extra = dict(payload.get("extra") or {})
    # shell-hook protocol lifts session_id to top-level; plugin kwargs may keep it in extra.
    if payload.get("session_id") and not extra.get("session_id"):
        extra["session_id"] = payload["session_id"]
    return extra


def normalize_hermes_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept raw post_api_request kwargs or the shell-hook stdin envelope."""
    if payload.get("hook_event_name"):
        return _shell_hook_to_kwargs(payload)
    return dict(payload)


def _cycle_kind(payload: dict[str, Any]) -> str:
    if _int(payload.get("assistant_tool_call_count")) > 0:
        return "tool_request"
    if _int(payload.get("assistant_content_chars")) > 0:
        return "assistant_response"
    finish_reason = str(payload.get("finish_reason") or "").strip()
    return f"finish:{finish_reason}" if finish_reason else "model_response"


def build_request_from_hermes_payload(payload: dict[str, Any]) -> CogitoEventRequest:
    event = normalize_hermes_payload(payload)
    usage = event.get("usage") or {}
    platform = str(event.get("platform") or "hermes").strip()
    session_id = str(event.get("session_id") or "").strip()
    session_ref = f"{platform}:{session_id}" if session_id else platform
    metadata = {
        key: event.get(key)
        for key in (
            "provider",
            "api_mode",
            "api_request_id",
            "api_call_count",
            "api_duration",
            "finish_reason",
            "response_model",
        )
        if event.get(key) not in (None, "")
    }
    return CogitoEventRequest(
        runtime="hermes",
        adapter="hermes_post_api_request",
        movement_kind="model_generation",
        cycle_kind=_cycle_kind(event),
        session_ref=session_ref,
        turn_ref=str(event.get("turn_id") or "").strip(),
        model=str(event.get("model") or "").strip(),
        input_tokens=_int(usage.get("input_tokens") or usage.get("prompt_tokens")),
        output_tokens=_int(usage.get("output_tokens") or usage.get("completion_tokens")),
        output_chars=_int(event.get("assistant_content_chars")),
        tool_call_count=_int(event.get("assistant_tool_call_count")),
        metadata=metadata,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record Hermes post_api_request as a neutral CogitoEvent.")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH), help="Cogito JSONL ledger path")
    args = parser.parse_args(argv)

    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"ok": False, "error": "empty stdin"}, ensure_ascii=False))
        return 0
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("stdin JSON must be an object")
        request = build_request_from_hermes_payload(payload)
        if not request.runtime:
            print(json.dumps({"ok": False, "ignored": True}, ensure_ascii=False))
            return 0
        record = record_generation_cycle(request, ledger_path=Path(args.ledger))
        print(
            json.dumps(
                {
                    "ok": True,
                    "record_id": record.id,
                    "runtime": record.runtime,
                    "cycle_kind": record.cycle_kind,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
