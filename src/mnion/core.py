from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import uuid


DEFAULT_TTL_SECONDS = 3600
MAX_STUB_CHARS = 280


@dataclass(frozen=True)
class MnionCaptureRequest:
    stub: str
    source_ref: str
    trigger: str
    affect_hints: list[str] | None = None
    evidence: list[str] | None = None
    ttl_seconds: int = DEFAULT_TTL_SECONDS


@dataclass(frozen=True)
class MnionRecord:
    id: str
    kind: str
    status: str
    stub: str
    source_ref: str
    trigger: str
    affect_hints: list[str]
    evidence: list[str]
    ttl_seconds: int
    captured_at: str
    expires_at: str
    promotion: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _clean_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def _validate_request(request: MnionCaptureRequest) -> None:
    stub = request.stub.strip()
    if not stub:
        raise ValueError("stub is required")
    if len(stub) > MAX_STUB_CHARS:
        raise ValueError(f"stub must be <= {MAX_STUB_CHARS} characters")
    if not request.source_ref.strip():
        raise ValueError("source_ref is required")
    if not request.trigger.strip():
        raise ValueError("trigger is required")
    if request.ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")


def capture_mnion(
    request: MnionCaptureRequest,
    *,
    ledger_path: str | Path,
    now: datetime | None = None,
) -> MnionRecord:
    """Append one cheap ephemeral mnion tag to a JSONL ledger."""
    _validate_request(request)
    captured_at = now or _utc_now()
    expires_at = captured_at + timedelta(seconds=request.ttl_seconds)
    record = MnionRecord(
        id=f"mnion_{uuid.uuid4().hex}",
        kind="mnion",
        status="tag",
        stub=request.stub.strip(),
        source_ref=request.source_ref.strip(),
        trigger=request.trigger.strip(),
        affect_hints=_clean_list(request.affect_hints),
        evidence=_clean_list(request.evidence),
        ttl_seconds=request.ttl_seconds,
        captured_at=_format_ts(captured_at),
        expires_at=_format_ts(expires_at),
    )

    path = Path(ledger_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return record


def load_mnions(
    *,
    ledger_path: str | Path,
    now: datetime | None = None,
    include_expired: bool = False,
) -> list[MnionRecord]:
    """Load mnion tags, hiding expired tags unless requested."""
    path = Path(ledger_path).expanduser()
    if not path.exists():
        return []
    current = now or _utc_now()
    records: list[MnionRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        record = MnionRecord(**data)
        if not include_expired and _parse_ts(record.expires_at) <= current:
            continue
        records.append(record)
    return records
