from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .config import MnemeConfig


MIN_REVIEW_BATCH_SIZE = 2


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
    next_tool: str
    tool_guidance: dict[str, Any]
    semantic_auto_consolidation: bool = False


def latest_review_mneme_call_seq(review_receipts: list[dict[str, Any]]) -> int | None:
    """Return the latest valid mneme_call_seq recorded by review receipts."""
    latest: int | None = None
    for receipt in review_receipts:
        value = receipt.get("mneme_call_seq")
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        latest = value if latest is None else max(latest, value)
    return latest


def consolidate_review_tool_guidance(selected_ids: list[str]) -> dict[str, Any]:
    """Return compact agent-facing guidance for closing pending Mneme review."""
    return {
        "tool": "consolidate_review",
        "purpose": "Record live-agent-authored packet outcomes for the current pending review and lift the capture write-barrier.",
        "required_fields": ["selected_ids", "summary", "valence", "member_ids"],
        "optional_fields": ["rationale", "claim"],
        "packet_mode": {
            "required_fields": ["selected_ids", "mnions"],
            "outcome_fields": ["reviewed_noise_ids", "deferred", "ungrouped_ids"],
            "coverage": "every selected id must appear in exactly one explicit outcome",
        },
        "selected_ids": list(selected_ids),
        "constraints": [
            "selected_ids must exactly match the pending review packet ids",
            "use legacy single-mnion fields or packet_mode fields, never both",
            "all summaries, rationales, and optional claims are written by the live agent; Mneme does not auto-generate semantics",
            "claim names a concrete change or understanding: non-blank single-line string or null, at most 240 Unicode characters; navigation, not evidence",
            "member ids and all explicit outcomes must be selected memory_tag ids",
            "deferred outcomes require a non-empty reason and reopen_policy",
            "this does not write kernel notes, engrams, embeddings, or external effects",
        ],
    }


def pinned_unread_backlog_stats(
    memory_tags: list[Any],
    *,
    high_valence_threshold: float,
    now: datetime | None = None,
) -> dict[str, int | None]:
    """Return model-free wall-clock pressure stats for pinned unread tags.

    The detector consumes counts/ages instead of reading ledgers itself. This
    keeps review pressure script-shaped while allowing old pinned material to
    apply pressure on the next Mneme call even when call_seq has not advanced
    during the quiet period.
    """
    now_utc = now or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    oldest: int | None = None
    count = 0
    for tag in memory_tags:
        if float(getattr(tag, "valence", 0.0)) < high_valence_threshold:
            continue
        captured_at = _parse_utc_datetime(str(getattr(tag, "captured_at", "")))
        if captured_at is None:
            continue
        age = max(0, int((now_utc - captured_at).total_seconds()))
        count += 1
        oldest = age if oldest is None else max(oldest, age)
    return {"pinned_unread_count": count, "oldest_pinned_unread_age_seconds": oldest}


def _parse_utc_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def evaluate_review_pressure(
    *,
    capture_result: Any,
    active_unread_count: int,
    config: MnemeConfig,
    last_review_seq: int | None = None,
    pinned_unread_count: int = 0,
    oldest_pinned_unread_age_seconds: int | None = None,
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
        reasons.append("high_valence_pinned")
        if action == "reinforced":
            reasons.append("confirmed_valence")

    interval = config.review_pressure.call_seq_interval
    interval_due = False
    if last_review_seq is not None:
        interval_due = seq - last_review_seq >= interval
    else:
        interval_due = seq > 0 and seq % interval == 0
    if config.review_pressure.trigger_on_interval and interval_due:
        reasons.append("call_seq_interval")

    pinned_backlog_due = (
        config.review_pressure.trigger_on_pinned_backlog
        and int(pinned_unread_count) > 0
        and oldest_pinned_unread_age_seconds is not None
        and int(oldest_pinned_unread_age_seconds) >= config.review_pressure.pinned_backlog_age_seconds
    )
    if pinned_backlog_due:
        reasons.append("pinned_backlog_pressure")

    has_hard_trigger = bool((config.review_pressure.trigger_on_interval and interval_due) or pinned_backlog_due)
    if has_hard_trigger and active_count < MIN_REVIEW_BATCH_SIZE:
        reasons.append("insufficient_review_batch")
        has_hard_trigger = False
    elif not has_hard_trigger and "high_valence_pinned" in reasons and active_count < MIN_REVIEW_BATCH_SIZE:
        reasons.append("insufficient_review_batch")

    return ReviewPressureDecision(
        needed=has_hard_trigger,
        reasons=reasons,
        mneme_call_seq=seq,
        active_unread_count=active_count,
        packet_limit=packet_limit,
        suggested_action="prepare_micro_consolidation_request" if has_hard_trigger else None,
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
        next_tool="consolidate_review",
        tool_guidance=consolidate_review_tool_guidance(selected_ids),
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
        "next_tool: consolidate_review",
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
