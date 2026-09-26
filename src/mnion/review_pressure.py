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
