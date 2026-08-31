from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
import uuid


def default_cogito_ledger_path() -> Path:
    explicit = os.environ.get("MNEME_STATE_DIR")
    if explicit:
        return Path(explicit).expanduser() / "cogito_cycles.jsonl"
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state).expanduser() / "mneme" / "cogito_cycles.jsonl"
    return Path.home() / ".local" / "state" / "mneme" / "cogito_cycles.jsonl"


DEFAULT_LEDGER_PATH = default_cogito_ledger_path()
GENERATION_MOVEMENT_KIND = "model_generation"


@dataclass(frozen=True)
class CogitoEventRequest:
    runtime: str
    adapter: str
    movement_kind: str = GENERATION_MOVEMENT_KIND
    cycle_kind: str = "generation"
    session_ref: str = ""
    turn_ref: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    output_chars: int = 0
    tool_call_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CogitoRecord:
    id: str
    ts: str
    runtime: str
    adapter: str
    movement_kind: str
    cycle_kind: str
    session_ref: str
    turn_ref: str
    model: str
    input_tokens: int
    output_tokens: int
    output_chars: int
    tool_call_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_ts(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def make_cycle_id(now: datetime | None = None) -> str:
    ts = format_ts(now or utc_now()).replace("-", "").replace(":", "")
    return f"cg_{ts}_{uuid.uuid4().hex[:8]}"


def _clean_str(value: str | None) -> str:
    return (value or "").strip()


def _nonnegative_int(value: int | None) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _record_from_request(request: CogitoEventRequest, now: datetime) -> CogitoRecord:
    return CogitoRecord(
        id=make_cycle_id(now),
        ts=format_ts(now),
        runtime=_clean_str(request.runtime),
        adapter=_clean_str(request.adapter),
        movement_kind=_clean_str(request.movement_kind) or GENERATION_MOVEMENT_KIND,
        cycle_kind=_clean_str(request.cycle_kind) or "generation",
        session_ref=_clean_str(request.session_ref),
        turn_ref=_clean_str(request.turn_ref),
        model=_clean_str(request.model),
        input_tokens=_nonnegative_int(request.input_tokens),
        output_tokens=_nonnegative_int(request.output_tokens),
        output_chars=_nonnegative_int(request.output_chars),
        tool_call_count=_nonnegative_int(request.tool_call_count),
        metadata=dict(request.metadata or {}),
    )


def record_generation_cycle(
    request: CogitoEventRequest,
    *,
    ledger_path: Path | str = DEFAULT_LEDGER_PATH,
    now: datetime | None = None,
) -> CogitoRecord:
    """Append one runtime-neutral cogito/generation cycle to a JSONL ledger."""
    ledger = Path(ledger_path).expanduser()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    record = _record_from_request(request, now or utc_now())
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return record


def _record_from_dict(raw: dict[str, Any]) -> CogitoRecord:
    return CogitoRecord(
        id=str(raw.get("id", "")),
        ts=str(raw.get("ts", "")),
        runtime=str(raw.get("runtime", "")),
        adapter=str(raw.get("adapter", "")),
        movement_kind=str(raw.get("movement_kind", "")),
        cycle_kind=str(raw.get("cycle_kind", "")),
        session_ref=str(raw.get("session_ref", "")),
        turn_ref=str(raw.get("turn_ref", "")),
        model=str(raw.get("model", "")),
        input_tokens=_nonnegative_int(raw.get("input_tokens")),
        output_tokens=_nonnegative_int(raw.get("output_tokens")),
        output_chars=_nonnegative_int(raw.get("output_chars")),
        tool_call_count=_nonnegative_int(raw.get("tool_call_count")),
        metadata=dict(raw.get("metadata") or {}),
    )


def load_cycles(
    *,
    ledger_path: Path | str = DEFAULT_LEDGER_PATH,
    movement_kind: str | None = None,
    runtime: str | None = None,
) -> list[CogitoRecord]:
    ledger = Path(ledger_path).expanduser()
    if not ledger.exists():
        return []
    records: list[CogitoRecord] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = _record_from_dict(json.loads(line))
        except json.JSONDecodeError:
            continue
        if movement_kind is not None and record.movement_kind != movement_kind:
            continue
        if runtime is not None and record.runtime != runtime:
            continue
        records.append(record)
    return records


def latest_cycle(*, ledger_path: Path | str = DEFAULT_LEDGER_PATH) -> CogitoRecord | None:
    records = load_cycles(ledger_path=ledger_path)
    return records[-1] if records else None


def cycles_since(
    anchor_id: str,
    *,
    ledger_path: Path | str = DEFAULT_LEDGER_PATH,
    runtime: str | None = None,
) -> int:
    """Count model-generation cycles after an anchor record.

    Non-generation effect events are deliberately ignored: they are receipts,
    not cogito cycles.
    """
    records = load_cycles(ledger_path=ledger_path)
    seen_anchor = False
    count = 0
    for record in records:
        if record.id == anchor_id:
            seen_anchor = True
            continue
        if not seen_anchor:
            continue
        if record.movement_kind != GENERATION_MOVEMENT_KIND:
            continue
        if runtime is not None and record.runtime != runtime:
            continue
        count += 1
    return count
