from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import re
import unicodedata
import uuid


DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_CALL_TTL = 32
DEFAULT_ACTIVE_MNION_LIMIT = 20
MAX_DELTA_CHARS = 280
CONSOLIDATION_THRESHOLD = 0.7
REINFORCE_THRESHOLD = 0.67
LINK_THRESHOLD = 0.34
MAX_SIGNATURE_TOKENS = 48

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)
_STOP_TOKENS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "when",
    "then",
    "than",
    "should",
    "could",
    "would",
    "using",
    "through",
    "current",
    "temporary",
    "memory",  # useful in names, too broad as a semantic discriminator
    "tag",     # useful in names, too broad inside this project
    "tags",
}


@dataclass(frozen=True)
class MnionCaptureRequest:
    delta: str
    valence: float
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    call_ttl: int = DEFAULT_CALL_TTL
    hooks: list[str] | None = None
    trigger: str | None = None
    affect_hints: list[str] | None = None


@dataclass(frozen=True)
class MnionRecord:
    id: str
    delta: str
    valence: float
    ttl_seconds: int
    call_ttl: int
    birth_call_seq: int
    captured_at: str
    expires_at: str
    hooks: list[str]
    trigger: str | None
    affect_hints: list[str]


@dataclass(frozen=True)
class MemoryTagCaptureResult:
    action: str
    target_id: str
    record: MnionRecord | None
    linked_ids: list[str]
    match_score: float
    reason: str
    valence_before: float | None
    valence_after: float
    mneme_call_seq: int
    event: dict | None = None


@dataclass(frozen=True)
class _CandidateMatch:
    record: MnionRecord
    score: float
    reason: str
    effective_valence: float


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
    if request.call_ttl <= 0:
        raise ValueError("call_ttl must be positive")


def _resolve_state_path(ledger_path: str | Path, state_path: str | Path | None) -> Path:
    if state_path is not None:
        return Path(state_path).expanduser()
    ledger = Path(ledger_path).expanduser()
    return ledger.with_name(f"{ledger.stem}.seq.json")


def current_mneme_call_seq(*, state_path: str | Path) -> int:
    """Read the simple portable Mneme/mnion call counter."""
    path = Path(state_path).expanduser()
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return int(data.get("seq", 0))


def next_mneme_call_seq(*, state_path: str | Path) -> int:
    """Increment the simple portable Mneme/mnion call counter."""
    path = Path(state_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    seq = current_mneme_call_seq(state_path=path) + 1
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({"seq": seq}, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return seq


def mneme_call_age(*, birth_call_seq: int, state_path: str | Path) -> int:
    """Return how many Mneme/mnion calls happened after this mnion was born."""
    return max(0, current_mneme_call_seq(state_path=state_path) - int(birth_call_seq))


def mnion_expired_by_call_age(record: MnionRecord, *, state_path: str | Path) -> bool:
    """Return whether a mnion exhausted its Mneme/mnion call TTL."""
    if record.birth_call_seq <= 0:
        return False
    return mneme_call_age(birth_call_seq=record.birth_call_seq, state_path=state_path) >= record.call_ttl


def valence_crosses_threshold(
    valence: float,
    *,
    threshold: float = CONSOLIDATION_THRESHOLD,
) -> bool:
    return valence >= threshold


def _new_mnion_record(
    request: MnionCaptureRequest,
    *,
    birth_call_seq: int,
    captured_at: datetime,
) -> MnionRecord:
    expires_at = captured_at + timedelta(seconds=request.ttl_seconds)
    return MnionRecord(
        id=f"mnion_{uuid.uuid4().hex}",
        delta=request.delta.strip(),
        valence=float(request.valence),
        ttl_seconds=request.ttl_seconds,
        call_ttl=request.call_ttl,
        birth_call_seq=birth_call_seq,
        captured_at=_format_ts(captured_at),
        expires_at=_format_ts(expires_at),
        hooks=_clean_list(request.hooks),
        trigger=_clean_trigger(request.trigger),
        affect_hints=_clean_list(request.affect_hints),
    )


def _append_json_line(path: str | Path, payload: dict) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def capture_mnion(
    request: MnionCaptureRequest,
    *,
    ledger_path: str | Path,
    state_path: str | Path | None = None,
    now: datetime | None = None,
) -> MnionRecord:
    """Append one cheap ephemeral mnion delta and increment Mneme/mnion call seq."""
    _validate_request(request)
    captured_at = now or _utc_now()
    seq_path = _resolve_state_path(ledger_path, state_path)
    birth_call_seq = next_mneme_call_seq(state_path=seq_path)
    record = _new_mnion_record(request, birth_call_seq=birth_call_seq, captured_at=captured_at)
    _append_json_line(ledger_path, asdict(record))
    return record


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    return normalized.replace("_", " ").replace("-", " ").replace(":", " ").replace(".", " ")


def _tokens_from_values(values: list[str] | str | None) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, list):
        text = " ".join(str(v) for v in values)
    else:
        text = str(values)
    tokens: list[str] = []
    for token in _TOKEN_RE.findall(_normalize_text(text)):
        if len(token) <= 2:
            continue
        if token in _STOP_TOKENS:
            continue
        tokens.append(token)
    return set(tokens[:MAX_SIGNATURE_TOKENS])


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))


def _similarity_score(candidate: MnionCaptureRequest, record: MnionRecord) -> tuple[float, str]:
    hook_score = _jaccard(_tokens_from_values(candidate.hooks), _tokens_from_values(record.hooks))
    delta_score = _jaccard(_tokens_from_values(candidate.delta), _tokens_from_values(record.delta))
    trigger_score = _jaccard(_tokens_from_values(candidate.trigger), _tokens_from_values(record.trigger))
    affect_score = _jaccard(_tokens_from_values(candidate.affect_hints), _tokens_from_values(record.affect_hints))
    recency_bonus = 0.05
    score = (
        0.65 * hook_score
        + 0.15 * delta_score
        + 0.10 * trigger_score
        + 0.05 * affect_score
        + recency_bonus
    )
    reasons = []
    if hook_score:
        reasons.append("hook_token_overlap")
    if delta_score:
        reasons.append("delta_token_overlap")
    if trigger_score:
        reasons.append("trigger_token_overlap")
    if affect_score:
        reasons.append("affect_token_overlap")
    return round(score, 4), "+".join(reasons) or "no_overlap"


def _effective_valence_by_id(ledger_path: str | Path) -> dict[str, float]:
    path = Path(ledger_path).expanduser()
    if not path.exists():
        return {}
    values: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if data.get("event") == "reinforcement":
            values[str(data["target_id"])] = float(data["valence_after"])
        elif "id" in data and "delta" in data:
            values[str(data["id"])] = float(data.get("valence", 0.0))
    return values


def _best_active_match(
    request: MnionCaptureRequest,
    *,
    ledger_path: str | Path,
    state_path: str | Path,
    now: datetime,
) -> _CandidateMatch | None:
    active = load_mnions(ledger_path=ledger_path, state_path=state_path, now=now)
    if not active:
        return None
    effective = _effective_valence_by_id(ledger_path)
    best: _CandidateMatch | None = None
    for record in active:
        score, reason = _similarity_score(request, record)
        match = _CandidateMatch(
            record=record,
            score=score,
            reason=reason,
            effective_valence=effective.get(record.id, record.valence),
        )
        if best is None or match.score > best.score:
            best = match
    return best


def _reinforced_valence(old: float, candidate: float) -> float:
    boost = min(max(candidate, 0.0), 1.0) * 0.25
    return round(old + boost * (1.0 - old), 6)


def _reinforcement_event(
    request: MnionCaptureRequest,
    *,
    target: MnionRecord,
    match: _CandidateMatch,
    mneme_call_seq: int,
    captured_at: datetime,
) -> dict:
    valence_after = _reinforced_valence(match.effective_valence, request.valence)
    return {
        "event": "reinforcement",
        "action": "reinforced",
        "target_id": target.id,
        "mneme_call_seq": mneme_call_seq,
        "captured_at": _format_ts(captured_at),
        "reason": match.reason,
        "match_score": match.score,
        "valence_before": match.effective_valence,
        "candidate_valence": float(request.valence),
        "valence_after": valence_after,
        "delta": request.delta.strip(),
        "hooks": _clean_list(request.hooks),
        "trigger": _clean_trigger(request.trigger),
        "affect_hints": _clean_list(request.affect_hints),
    }


def _link_event(
    *,
    source_id: str,
    target_ids: list[str],
    match: _CandidateMatch,
    mneme_call_seq: int,
    captured_at: datetime,
) -> dict:
    return {
        "event": "link",
        "action": "linked_new",
        "source_id": source_id,
        "target_ids": target_ids,
        "mneme_call_seq": mneme_call_seq,
        "captured_at": _format_ts(captured_at),
        "reason": match.reason,
        "match_score": match.score,
    }


def capture_memory_tag(
    request: MnionCaptureRequest,
    *,
    ledger_path: str | Path,
    state_path: str | Path | None = None,
    now: datetime | None = None,
) -> MemoryTagCaptureResult:
    """Capture, reinforce, or link a memory tag using a cheap bounded pre-capture filter."""
    _validate_request(request)
    captured_at = now or _utc_now()
    seq_path = _resolve_state_path(ledger_path, state_path)
    seq = next_mneme_call_seq(state_path=seq_path)
    match = _best_active_match(request, ledger_path=ledger_path, state_path=seq_path, now=captured_at)

    if match is not None and match.score >= REINFORCE_THRESHOLD:
        event = _reinforcement_event(
            request,
            target=match.record,
            match=match,
            mneme_call_seq=seq,
            captured_at=captured_at,
        )
        _append_json_line(ledger_path, event)
        return MemoryTagCaptureResult(
            action="reinforced",
            target_id=match.record.id,
            record=None,
            linked_ids=[match.record.id],
            match_score=match.score,
            reason=match.reason,
            valence_before=match.effective_valence,
            valence_after=float(event["valence_after"]),
            mneme_call_seq=seq,
            event=event,
        )

    record = _new_mnion_record(request, birth_call_seq=seq, captured_at=captured_at)
    _append_json_line(ledger_path, asdict(record))
    if match is not None and match.score >= LINK_THRESHOLD:
        event = _link_event(
            source_id=record.id,
            target_ids=[match.record.id],
            match=match,
            mneme_call_seq=seq,
            captured_at=captured_at,
        )
        _append_json_line(ledger_path, event)
        return MemoryTagCaptureResult(
            action="linked_new",
            target_id=record.id,
            record=record,
            linked_ids=[match.record.id],
            match_score=match.score,
            reason=match.reason,
            valence_before=None,
            valence_after=record.valence,
            mneme_call_seq=seq,
            event=event,
        )

    return MemoryTagCaptureResult(
        action="created",
        target_id=record.id,
        record=record,
        linked_ids=[],
        match_score=0.0 if match is None else match.score,
        reason="no_active_match" if match is None else match.reason,
        valence_before=None,
        valence_after=record.valence,
        mneme_call_seq=seq,
        event=None,
    )


def _record_from_data(data: dict) -> MnionRecord:
    """Read current mnion records and tolerate earlier prototype shapes."""
    if "delta" in data and "id" in data and "event" not in data:
        data = dict(data)
        data.setdefault("call_ttl", DEFAULT_CALL_TTL)
        data.setdefault("birth_call_seq", 0)
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
        call_ttl=DEFAULT_CALL_TTL,
        birth_call_seq=0,
        captured_at=str(data["captured_at"]),
        expires_at=str(data["expires_at"]),
        hooks=hooks,
        trigger=_clean_trigger(data.get("trigger")),
        affect_hints=_clean_list(data.get("affect_hints")),
    )


def load_mnions(
    *,
    ledger_path: str | Path,
    state_path: str | Path | None = None,
    now: datetime | None = None,
    include_expired: bool = False,
    limit: int | None = DEFAULT_ACTIVE_MNION_LIMIT,
) -> list[MnionRecord]:
    """Load bounded mnion deltas, hiding wall- or call-expired tags unless requested."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive or None")
    path = Path(ledger_path).expanduser()
    if not path.exists():
        return []
    seq_path = _resolve_state_path(path, state_path)
    current = now or _utc_now()
    raw_rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    refreshed_seq_by_id: dict[str, int] = {}
    for data in raw_rows:
        if data.get("event") == "reinforcement" and data.get("target_id"):
            target_id = str(data["target_id"])
            refreshed_seq_by_id[target_id] = max(
                refreshed_seq_by_id.get(target_id, 0),
                int(data.get("mneme_call_seq", 0)),
            )
    records: list[MnionRecord] = []
    for data in raw_rows:
        if data.get("event"):
            continue
        record = _record_from_data(data)
        wall_expired = _parse_ts(record.expires_at) <= current
        active_since_seq = max(record.birth_call_seq, refreshed_seq_by_id.get(record.id, 0))
        call_expired = False
        if active_since_seq > 0:
            call_expired = mneme_call_age(birth_call_seq=active_since_seq, state_path=seq_path) >= record.call_ttl
        if not include_expired and (wall_expired or call_expired):
            continue
        records.append(record)
    if limit is None:
        return records
    return records[-limit:]
