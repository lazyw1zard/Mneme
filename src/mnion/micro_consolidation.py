from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from mnion.core import MnionRecord, load_mnions


@dataclass(frozen=True)
class MicroConsolidationRequest:
    """Portable review packet for a host-provided live contour/agent."""

    mnions: list[MnionRecord]
    prompt: str
    expected_output_schema: dict[str, str]
    reason: str
    limit: int


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


def prepare_micro_consolidation_request(
    *,
    ledger_path: str | Path,
    state_path: str | Path | None = None,
    limit: int = 10,
    reason: str = "latest_mnions",
) -> MicroConsolidationRequest:
    """Load the latest active mnions and wrap them as a portable review request."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    return MicroConsolidationRequest(
        mnions=load_mnions(ledger_path=ledger_path, state_path=state_path, limit=limit),
        prompt=MICRO_CONSOLIDATION_PROMPT,
        expected_output_schema=dict(EXPECTED_OUTPUT_SCHEMA),
        reason=reason,
        limit=limit,
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
    limit: int = 10,
    reason: str = "latest_mnions",
) -> MicroConsolidationResult:
    """Ask a host-provided agent to build one experimental consolidated contour.

    This minimal slice is intentionally host-neutral: Mneme prepares the packet,
    the caller supplies the live contour/agent, and failures are returned as
    structured errors instead of being hidden or converted into durable memory.
    """
    request = prepare_micro_consolidation_request(
        ledger_path=ledger_path,
        state_path=state_path,
        limit=limit,
        reason=reason,
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
