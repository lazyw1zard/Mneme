from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .core import (
    CogitoEventRequest,
    DEFAULT_LEDGER_PATH,
    cycles_since,
    latest_cycle,
    record_generation_cycle,
)


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _ledger_path(value: str | None) -> Path:
    return Path(value).expanduser() if value else DEFAULT_LEDGER_PATH


def _add_ledger_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH), help="Cogito JSONL ledger path")


def _cmd_record(args: argparse.Namespace) -> int:
    metadata = {}
    if args.metadata:
        metadata = json.loads(args.metadata)
        if not isinstance(metadata, dict):
            raise ValueError("--metadata must be a JSON object")
    record = record_generation_cycle(
        CogitoEventRequest(
            runtime=args.runtime,
            adapter=args.adapter,
            movement_kind=args.movement_kind,
            cycle_kind=args.cycle_kind,
            session_ref=args.session_ref,
            turn_ref=args.turn_ref,
            model=args.model,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens,
            output_chars=args.output_chars,
            tool_call_count=args.tool_call_count,
            metadata=metadata,
        ),
        ledger_path=_ledger_path(args.ledger),
    )
    _print({"ok": True, "record": asdict(record)})
    return 0


def _cmd_latest(args: argparse.Namespace) -> int:
    record = latest_cycle(ledger_path=_ledger_path(args.ledger))
    _print({"ok": record is not None, "record": asdict(record) if record else None})
    return 0


def _cmd_count_since(args: argparse.Namespace) -> int:
    count = cycles_since(args.anchor_id, ledger_path=_ledger_path(args.ledger), runtime=args.runtime)
    _print({"ok": True, "cycles_since": count})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Runtime-neutral Cogito/generation-cycle ledger.")
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="Append one generation/effect cycle")
    _add_ledger_arg(record)
    record.add_argument("--runtime", required=True, help="Runtime name, e.g. hermes/codex/custom-runtime")
    record.add_argument("--adapter", required=True, help="Adapter name, e.g. hermes_post_api_request")
    record.add_argument("--movement-kind", default="model_generation")
    record.add_argument("--cycle-kind", default="generation")
    record.add_argument("--session-ref", default="")
    record.add_argument("--turn-ref", default="")
    record.add_argument("--model", default="")
    record.add_argument("--input-tokens", type=int, default=0)
    record.add_argument("--output-tokens", type=int, default=0)
    record.add_argument("--output-chars", type=int, default=0)
    record.add_argument("--tool-call-count", type=int, default=0)
    record.add_argument("--metadata", default="", help="Optional JSON object")
    record.set_defaults(func=_cmd_record)

    latest = sub.add_parser("latest", help="Print latest cycle")
    _add_ledger_arg(latest)
    latest.set_defaults(func=_cmd_latest)

    count_since = sub.add_parser("count-since", help="Count model-generation cycles since an anchor id")
    count_since.add_argument("anchor_id")
    _add_ledger_arg(count_since)
    count_since.add_argument("--runtime", default=None, help="Optional runtime filter")
    count_since.set_defaults(func=_cmd_count_since)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
