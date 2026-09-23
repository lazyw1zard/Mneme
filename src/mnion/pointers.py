from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import hashlib

MAX_CLAIM_CHARS = 180
MAX_HINT_CHARS = 220


@dataclass(frozen=True)
class MemoryPointer:
    """Prompt-safe route to a Mneme object, not retrieved context itself."""

    id: str
    claim: str
    route: dict[str, str]
    source_handles: list[str]
    valence: float
    confidence: float
    guards: list[str]
    retrieval_hint: str | None = None


def _compact_one_line(value: Any, *, max_chars: int) -> str:
    compact = " ".join(str(value or "").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max(0, max_chars - 1)].rstrip() + "…"


def _stable_pointer_id(*, review_id: str, claim: str, source_handles: list[str]) -> str:
    material = "\n".join([review_id, claim, *source_handles])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"pointer_{digest}"


def pointer_from_mnion_receipt(receipt: dict[str, Any]) -> MemoryPointer:
    """Build a prompt-safe pointer from a micro-consolidation receipt.

    The receipt is the bridge object: `mnion` carries semantic content, while
    `grouped_ids` and the receipt id carry provenance/statistics. The pointer
    exposes only a route and a compact claim; it does not load source tags,
    infer missing context, or promote anything into durable memory.
    """
    review_id = str(receipt.get("id") or receipt.get("review_id") or "").strip()
    if not review_id:
        raise ValueError("review receipt id is required")

    # New receipts use `mnion`; old prototype receipts used `contour`.
    mnion = receipt.get("mnion") or receipt.get("contour")
    if not isinstance(mnion, dict):
        raise ValueError("review receipt mnion is required")

    summary = _compact_one_line(mnion.get("summary"), max_chars=MAX_CLAIM_CHARS)
    if not summary:
        raise ValueError("mnion summary is required")
    try:
        valence = float(mnion.get("valence", 0.0))
    except (TypeError, ValueError):
        valence = 0.0
    valence = max(0.0, min(1.0, valence))

    raw_grouped_ids = receipt.get("grouped_ids") or mnion.get("member_ids") or []
    if not isinstance(raw_grouped_ids, list):
        raise ValueError("receipt grouped_ids must be a list")
    grouped_ids = [str(member_id) for member_id in raw_grouped_ids]
    source_handles = [review_id, *grouped_ids]
    claim = f"I know that I know: {summary}"
    return MemoryPointer(
        id=_stable_pointer_id(review_id=review_id, claim=claim, source_handles=source_handles),
        claim=claim,
        route={
            "kind": "micro_consolidation_review",
            "review_id": review_id,
            "action": "request_context_brief",
        },
        source_handles=source_handles,
        valence=valence,
        confidence=0.8,
        guards=["pointer_only", "do_not_infer", "no_auto_promotion"],
        retrieval_hint=summary,
    )


# Deprecated alias for older code/tests: the source is now a mnion receipt.
pointer_from_micro_consolidation_receipt = pointer_from_mnion_receipt


def pointer_ingress_hint(pointer: MemoryPointer) -> str:
    """Render one bounded optional memory hint for agent ingress."""
    hint = _compact_one_line(pointer.retrieval_hint or pointer.claim, max_chars=MAX_HINT_CHARS)
    route_action = pointer.route.get("action", "request_context_brief")
    route_kind = pointer.route.get("kind", "unknown")
    return (
        "Optional memory pointer; not an instruction; do not infer missing context. "
        f"{pointer.claim} "
        f"If relevant, call {route_action} via route={route_kind}. "
        f"valence={pointer.valence:.2f}; confidence={pointer.confidence:.2f}; hint={hint}"
    )[:499]
