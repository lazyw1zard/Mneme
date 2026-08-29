from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import uuid


DEFAULT_TTL_SECONDS = 3600
MAX_DELTA_CHARS = 280
CONSOLIDATION_THRESHOLD = 0.7


@dataclass(frozen=True)
class MnionCaptureRequest:
    delta: str
    valence: float
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    hooks: list[str] | None = None
    trigger: str | None = None
    affect_hints: list[str] | None = None


@dataclass(frozen=True)
class MnionRecord:
    id: str
    delta: str
    valence: float
    ttl_seconds: int
    captured_at: str
    expires_at: str
    hooks: list[str]
    trigger: str | None
    affect_hints: list[str]


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


def _clean_trigger(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _validate_request(request: MnionCaptureRequest) -> None:
    delta = request.delta.strip()
    if not delta:
        raise ValueError("delta is required")
    if len(delta) > MAX_DELTA_CHARS:
        raise ValueError(f"delta must be <= {MAX_DELTA_CHARS} characters")
    if not 0.0 <= request.valence <= 1.0:
        raise ValueError("valence must be between 0.0 and 1.0")
    if request.ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")


def valence_crosses_threshold(
    valence: float,
    *,
    threshold: float = CONSOLIDATION_THRESHOLD,
) -> bool:
    return valence >= threshold


def capture_mnion(
    request: MnionCaptureRequest,
    *,
    ledger_path: str | Path,
    now: datetime | None = None,
) -> MnionRecord:
    """Append one cheap ephemeral mnion delta to a JSONL ledger."""
    _validate_request(request)
    captured_at = now or _utc_now()
    expires_at = captured_at + timedelta(seconds=request.ttl_seconds)
    record = MnionRecord(
        id=f"mnion_{uuid.uuid4().hex}",
        delta=request.delta.strip(),
        valence=float(request.valence),
        ttl_seconds=request.ttl_seconds,
        captured_at=_format_ts(captured_at),
        expires_at=_format_ts(expires_at),
        hooks=_clean_list(request.hooks),
        trigger=_clean_trigger(request.trigger),
        affect_hints=_clean_list(request.affect_hints),
    )

    path = Path(ledger_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return record


def _record_from_data(data: dict) -> MnionRecord:
    """Read current mnion records and tolerate the first prototype's heavier shape."""
    if "delta" in data:
        return MnionRecord(**data)

    hooks: list[str] = []
    source_ref = str(data.get("source_ref", "")).strip()
    if source_ref:
        hooks.append(source_ref)

    return MnionRecord(
        id=str(data["id"]),
        delta=str(data.get("stub", "")).strip(),
        valence=0.0,
        ttl_seconds=int(data.get("ttl_seconds", DEFAULT_TTL_SECONDS)),
        captured_at=str(data["captured_at"]),
        expires_at=str(data["expires_at"]),
        hooks=hooks,
        trigger=_clean_trigger(data.get("trigger")),
        affect_hints=_clean_list(data.get("affect_hints")),
    )


def load_mnions(
    *,
    ledger_path: str | Path,
    now: datetime | None = None,
    include_expired: bool = False,
) -> list[MnionRecord]:
    """Load mnion deltas, hiding expired tags unless requested."""
    path = Path(ledger_path).expanduser()
    if not path.exists():
        return []
    current = now or _utc_now()
    records: list[MnionRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        record = _record_from_data(data)
        if not include_expired and _parse_ts(record.expires_at) <= current:
            continue
        records.append(record)
    return records
