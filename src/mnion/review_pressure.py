from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import MnemeConfig


@dataclass(frozen=True)
class ReviewPressureDecision:
    needed: bool
    reasons: list[str]
    mneme_call_seq: int
    active_unread_count: int
    packet_limit: int
    suggested_action: str | None
    semantic_auto_consolidation: bool = False


@dataclass(frozen=True)
class ReviewPressureIngress:
    kind: str
    rendered: str
    suggested_action: str
    reasons: list[str]
    mneme_call_seq: int
    packet_limit: int
    selected_ids: list[str]
    memory_tags: list[dict[str, Any]]
    prompt: str
    expected_output_schema: dict[str, str]
    semantic_auto_consolidation: bool = False


def evaluate_review_pressure(
    *,
    capture_result: Any,
    active_unread_count: int,
    config: MnemeConfig,
) -> ReviewPressureDecision:
    """Decide whether a Mneme call should invoke agentic review.

    This is deliberately model-free. It may ask the host/live agent to prepare a
    micro-consolidation review packet, but it never performs semantic
    consolidation, durable promotion, kernel writes, or model calls by itself.
    """
    seq = int(getattr(capture_result, "mneme_call_seq", 0))
    packet_limit = config.review_pressure.packet_limit

    if not config.review_pressure.enabled:
        return ReviewPressureDecision(
            needed=False,
            reasons=["review_pressure_disabled"],
            mneme_call_seq=seq,
            active_unread_count=max(0, int(active_unread_count)),
            packet_limit=packet_limit,
            suggested_action=None,
        )

    active_count = max(0, int(active_unread_count))
    if active_count <= 0:
        return ReviewPressureDecision(
            needed=False,
            reasons=["no_active_unread_memory_tags"],
            mneme_call_seq=seq,
            active_unread_count=active_count,
            packet_limit=packet_limit,
            suggested_action=None,
        )

    reasons: list[str] = []
    action = str(getattr(capture_result, "action", ""))
    valence_after = float(getattr(capture_result, "valence_after", 0.0))
    if config.review_pressure.trigger_on_high_valence and valence_after >= config.memory_tag.high_valence_threshold:
        reasons.append("high_valence")
        if action == "reinforced":
            reasons.append("confirmed_valence")

    interval = config.review_pressure.call_seq_interval
    if config.review_pressure.trigger_on_interval and seq > 0 and seq % interval == 0:
        reasons.append("call_seq_interval")

    return ReviewPressureDecision(
        needed=bool(reasons),
        reasons=reasons,
        mneme_call_seq=seq,
        active_unread_count=active_count,
        packet_limit=packet_limit,
        suggested_action="prepare_micro_consolidation_request" if reasons else None,
        semantic_auto_consolidation=False,
    )


def build_review_pressure_ingress(*, decision: ReviewPressureDecision, review_request: Any) -> ReviewPressureIngress | None:
    """Render a pressure-triggered review packet as direct agent input.

    The structured packet is useful for tools, but the live agent also needs an
    unmistakable ingress brief in the tool result so the packet is not merely
    prepared and then forgotten.
    """
    if not decision.needed:
        return None
    selected_ids = list(review_request.selection.selected_ids)
    memory_tags = [
        {
            "id": tag.id,
            "delta": tag.delta,
            "valence": tag.valence,
            "hooks": list(tag.hooks),
            "trigger": tag.trigger,
            "affect_hints": list(tag.affect_hints),
            "birth_call_seq": tag.birth_call_seq,
        }
        for tag in review_request.memory_tags
    ]
    rendered = _render_review_pressure_ingress(
        decision=decision,
        selected_ids=selected_ids,
        memory_tags=memory_tags,
    )
    return ReviewPressureIngress(
        kind="mneme_review_pressure_ingress",
        rendered=rendered,
        suggested_action="agentic_micro_consolidation_review",
        reasons=list(decision.reasons),
        mneme_call_seq=decision.mneme_call_seq,
        packet_limit=review_request.packet_limit,
        selected_ids=selected_ids,
        memory_tags=memory_tags,
        prompt=review_request.prompt,
        expected_output_schema=dict(review_request.expected_output_schema),
        semantic_auto_consolidation=False,
    )


def _render_review_pressure_ingress(
    *,
    decision: ReviewPressureDecision,
    selected_ids: list[str],
    memory_tags: list[dict[str, Any]],
) -> str:
    lines = [
        "MNEME_REVIEW_PRESSURE",
        f"mneme_call_seq: {decision.mneme_call_seq}",
        f"reasons: {', '.join(decision.reasons)}",
        "suggested_action: agentic_micro_consolidation_review",
        "boundary: Do not auto-promote; do not write kernel/engram; perform agentic semantic review only if you take this up now.",
        f"selected_ids: {', '.join(selected_ids)}",
        "memory_tags:",
    ]
    for tag in memory_tags:
        hooks = ",".join(tag.get("hooks") or [])
        lines.append(
            f"- {tag['id']} | valence={tag['valence']} | hooks={hooks} | delta={tag['delta']}"
        )
    return "\n".join(lines)
