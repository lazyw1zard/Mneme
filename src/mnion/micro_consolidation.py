from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import json
import uuid

from mnion.core import MnionRecord, current_mneme_call_seq, load_mnions


@dataclass(frozen=True)
class ReviewState:
    """Derived working state for one mnion's micro-consolidation review."""

    status: str
    last_review_id: str | None = None
    last_review_seq: int | None = None
    outcome: str | None = None
    needs_rereview: bool = False
    rereview_reason: str | None = None


@dataclass(frozen=True)
class MicroConsolidationSelection:
    """Compact selection metadata for a micro-consolidation review packet."""

    strategy: str
    reason: str
    selected_ids: list[str]
    unread_active_count: int
    reviewed_active_count: int = 0
    deferred_count: int = 0
    backend: str = "derived_jsonl"


@dataclass(frozen=True)
class MicroConsolidationSelectionPacket:
    """Selected mnions plus compact metadata for agent review."""

    mnions: list[MnionRecord]
    selection: MicroConsolidationSelection


@dataclass(frozen=True)
class MicroConsolidationRequest:
    """Portable review packet for a host-provided live contour/agent."""

    mnions: list[MnionRecord]
    prompt: str
    expected_output_schema: dict[str, str]
    reason: str
    packet_limit: int
    selection: MicroConsolidationSelection


@dataclass(frozen=True)
class ConsolidatedContour:
    """Minimal experimental contour returned by a micro-consolidation agent."""

    summary: str
    valence: float
    member_ids: list[str]
    rationale: str | None = None


@dataclass(frozen=True)
class MicroConsolidationError:
    reason: str
    message: str


@dataclass(frozen=True)
class MicroConsolidationResult:
    ok: bool
    request: MicroConsolidationRequest
    contour: ConsolidatedContour | None = None
    error: MicroConsolidationError | None = None


AgentInvoker = Callable[[MicroConsolidationRequest], dict[str, Any] | ConsolidatedContour]


MICRO_CONSOLIDATION_PROMPT = """Find semantically close mnions in this review packet.
Return one minimal consolidated contour with:
- summary: short shared meaning across the selected mnions
- valence: 0.0..1.0 review pressure/salience
- member_ids: mnion ids used for this contour
- rationale: optional brief reason
Do not write durable memory, kernel notes, or engrams.
"""

EXPECTED_OUTPUT_SCHEMA = {
    "summary": "string shared meaning for this micro-consolidated contour",
    "valence": "float between 0.0 and 1.0",
    "member_ids": "list of mnion ids included in the contour",
    "rationale": "optional string explaining the semantic link",
}


def derive_review_state(review_receipts: list[dict[str, Any]]) -> dict[str, ReviewState]:
    """Derive the working per-mnion review state from append-only review receipts."""
    states: dict[str, ReviewState] = {}
    for receipt in review_receipts:
        # Receipts are the audit/evidence layer. This function builds the
        # cheap working read-model from them so the live agent never has to
        # compare receipt ids against active mnions in prompt context.
        review_id = str(receipt.get("id") or receipt.get("review_id") or "") or None
        review_seq_raw = receipt.get("mneme_call_seq") or receipt.get("review_seq")
        review_seq = int(review_seq_raw) if review_seq_raw is not None else None
        for field, status, outcome in (
            ("grouped_ids", "reviewed", "grouped"),
            ("ungrouped_ids", "reviewed", "ungrouped"),
            ("reviewed_ids", "reviewed", "reviewed"),
            ("deferred_ids", "deferred", "deferred"),
        ):
            raw_ids = receipt.get(field, [])
            if raw_ids is None:
                continue
            if not isinstance(raw_ids, list):
                raise ValueError(f"{field} must be a list")
            for mnion_id in raw_ids:
                states[str(mnion_id)] = ReviewState(
                    status=status,
                    last_review_id=review_id,
                    last_review_seq=review_seq,
                    outcome=outcome,
                )
    return states


def _eligible_for_unread_review(state: ReviewState | None) -> bool:
    if state is None:
        return True
    return state.status in {"unread", "needs_rereview"} or state.needs_rereview


def select_unread_active_mnions(
    active_mnions: list[MnionRecord],
    review_state: dict[str, ReviewState],
    *,
    packet_limit: int,
    reason: str = "unread_active_coverage",
    backend: str = "derived_jsonl",
) -> MicroConsolidationSelectionPacket:
    """Select a bounded unread-active packet without exposing receipts to the agent."""
    if packet_limit <= 0:
        raise ValueError("packet_limit must be positive")

    # The active pool has already been loaded in full. packet_limit is only
    # the review-queue step size, not a visibility filter over active mnions.
    eligible = [mnion for mnion in active_mnions if _eligible_for_unread_review(review_state.get(mnion.id))]

    # Keep counters beside the selected ids so the agent sees backlog shape
    # without seeing receipts, SQL rows, or the whole ledger.
    reviewed_count = sum(
        1
        for mnion in active_mnions
        if (state := review_state.get(mnion.id)) is not None and state.status == "reviewed" and not state.needs_rereview
    )
    deferred_count = sum(
        1
        for mnion in active_mnions
        if (state := review_state.get(mnion.id)) is not None and state.status == "deferred" and not state.needs_rereview
    )
    selected = eligible[:packet_limit]
    return MicroConsolidationSelectionPacket(
        mnions=selected,
        selection=MicroConsolidationSelection(
            strategy="unread_active_coverage",
            reason=reason,
            selected_ids=[mnion.id for mnion in selected],
            unread_active_count=len(eligible),
            reviewed_active_count=reviewed_count,
            deferred_count=deferred_count,
            backend=backend,
        ),
    )


def prepare_micro_consolidation_request(
    *,
    ledger_path: str | Path,
    state_path: str | Path | None = None,
    packet_limit: int = 10,
    reason: str = "unread_active_coverage",
    review_receipts: list[dict[str, Any]] | None = None,
    review_state: dict[str, ReviewState] | None = None,
) -> MicroConsolidationRequest:
    """Load active mnions and wrap an unread-active review packet."""
    if packet_limit <= 0:
        raise ValueError("packet_limit must be positive")

    # First read all active mnions. Fair coverage depends on seeing the whole
    # active set; packet_limit is applied only after review_state selection.
    active_mnions = load_mnions(ledger_path=ledger_path, state_path=state_path, limit=None)

    # A future SQLite read-model can provide review_state directly. Until then,
    # receipts are folded into the same shape here, preserving the API boundary.
    derived_state = review_state if review_state is not None else derive_review_state(review_receipts or [])
    packet = select_unread_active_mnions(active_mnions, derived_state, packet_limit=packet_limit, reason=reason)
    return MicroConsolidationRequest(
        mnions=packet.mnions,
        prompt=MICRO_CONSOLIDATION_PROMPT,
        expected_output_schema=dict(EXPECTED_OUTPUT_SCHEMA),
        reason=reason,
        packet_limit=packet_limit,
        selection=packet.selection,
    )


def _contour_from_agent_response(
    response: dict[str, Any] | ConsolidatedContour,
    *,
    request: MicroConsolidationRequest,
) -> ConsolidatedContour:
    if isinstance(response, ConsolidatedContour):
        contour = response
    elif isinstance(response, dict):
        try:
            summary = str(response["summary"]).strip()
            valence = float(response["valence"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid consolidated contour response: {exc}") from exc
        member_ids_raw = response.get("member_ids", [])
        if not isinstance(member_ids_raw, list):
            raise ValueError("member_ids must be a list")
        contour = ConsolidatedContour(
            summary=summary,
            valence=valence,
            member_ids=[str(member_id) for member_id in member_ids_raw],
            rationale=str(response["rationale"]).strip() if response.get("rationale") is not None else None,
        )
    else:
        raise ValueError("agent response must be a dict or ConsolidatedContour")

    if not contour.summary:
        raise ValueError("summary is required")
    if not 0.0 <= contour.valence <= 1.0:
        raise ValueError("valence must be between 0.0 and 1.0")
    known_ids = {mnion.id for mnion in request.mnions}
    unknown_ids = [member_id for member_id in contour.member_ids if member_id not in known_ids]
    if unknown_ids:
        raise ValueError(f"member_ids must come from request mnions: {unknown_ids}")
    return contour


def run_micro_consolidation(
    *,
    ledger_path: str | Path,
    agent: AgentInvoker,
    state_path: str | Path | None = None,
    packet_limit: int = 10,
    reason: str = "unread_active_coverage",
    review_receipts: list[dict[str, Any]] | None = None,
    review_state: dict[str, ReviewState] | None = None,
) -> MicroConsolidationResult:
    """Ask a host-provided agent to build one experimental consolidated contour.

    This minimal slice is intentionally host-neutral: Mneme prepares the packet,
    the caller supplies the live contour/agent, and failures are returned as
    structured errors instead of being hidden or converted into durable memory.
    """
    request = prepare_micro_consolidation_request(
        ledger_path=ledger_path,
        state_path=state_path,
        packet_limit=packet_limit,
        reason=reason,
        review_receipts=review_receipts,
        review_state=review_state,
    )
    try:
        response = agent(request)
    except Exception as exc:  # noqa: BLE001 - boundary must report failed host agent calls.
        return MicroConsolidationResult(
            ok=False,
            request=request,
            error=MicroConsolidationError(reason="agent_call_failed", message=str(exc)),
        )

    try:
        contour = _contour_from_agent_response(response, request=request)
    except Exception as exc:  # noqa: BLE001 - invalid host response is a structured review error.
        return MicroConsolidationResult(
            ok=False,
            request=request,
            error=MicroConsolidationError(reason="invalid_agent_response", message=str(exc)),
        )

    return MicroConsolidationResult(ok=True, request=request, contour=contour)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _append_jsonl(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def load_micro_consolidation_review_receipts(path: str | Path) -> list[dict[str, Any]]:
    """Load append-only micro-consolidation review receipts from JSONL."""
    target = Path(path).expanduser()
    if not target.exists():
        return []
    receipts: list[dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("review receipt line must be a JSON object")
            receipts.append(payload)
    return receipts


def apply_micro_consolidation_review(
    result: MicroConsolidationResult,
    *,
    receipt_path: str | Path,
    state_path: str | Path | None = None,
) -> dict[str, Any]:
    """Append a review receipt for a successful micro-consolidation result.

    This is the first durable closure step after semantic review. It records
    enough audit evidence to rebuild ReviewState without asking the agent to
    compare ids, inspect tables, or read the whole mnion ledger.
    """
    if not result.ok or result.contour is None:
        raise ValueError("cannot apply an unsuccessful micro-consolidation result")

    selected_ids = list(result.request.selection.selected_ids)
    grouped_ids = list(result.contour.member_ids)
    selected_set = set(selected_ids)
    unknown_grouped = [mnion_id for mnion_id in grouped_ids if mnion_id not in selected_set]
    if unknown_grouped:
        raise ValueError(f"grouped ids must come from selected mnions: {unknown_grouped}")
    ungrouped_ids = [mnion_id for mnion_id in selected_ids if mnion_id not in set(grouped_ids)]

    receipt: dict[str, Any] = {
        "id": f"review_{uuid.uuid4().hex}",
        "kind": "micro_consolidation_review",
        "status": "reviewed",
        "created_at": _utc_timestamp(),
        "mneme_call_seq": current_mneme_call_seq(state_path=state_path) if state_path is not None else None,
        "selected_ids": selected_ids,
        "grouped_ids": grouped_ids,
        "ungrouped_ids": ungrouped_ids,
        "deferred_ids": [],
        "selection": asdict(result.request.selection),
        "contour": asdict(result.contour),
    }
    _append_jsonl(receipt_path, receipt)
    return receipt
