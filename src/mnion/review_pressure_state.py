from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
import tempfile

from .micro_consolidation import derive_review_state
from .review_pressure import ReviewPressureDecision, ReviewPressureIngress


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pending_review_path_for_state_dir(state_dir: str | Path) -> Path:
    """Return the compact pending-review latch path for a Mneme state dir."""
    return Path(state_dir).expanduser() / "pending_review.json"


def load_pending_review(path: str | Path) -> dict[str, Any] | None:
    """Load the pending-review latch if it exists.

    The latch is a compact agent-facing-safe JSON artifact. It is not a receipt
    ledger, SQL view, or semantic consolidation result.
    """
    target = Path(path).expanduser()
    if not target.exists():
        return None
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("pending review latch must be a JSON object")
    return payload


def _selected_id_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    selected: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        if item != item.strip() or not item:
            return None
        selected.append(item)
    if len(set(selected)) != len(selected):
        return None
    return selected


def pending_review_schema_errors(pending: dict[str, Any]) -> list[str]:
    """Return fail-closed schema errors for a pending-review latch."""
    errors: list[str] = []
    if pending.get("kind") != "mneme_pending_review":
        errors.append("kind")
    if pending.get("status") != "pending":
        errors.append("status")

    selected_ids = _selected_id_list(pending.get("selected_ids"))
    if selected_ids is None:
        errors.append("selected_ids")

    agent_ingress = pending.get("agent_ingress")
    ingress_selected_ids: list[str] | None = None
    if not isinstance(agent_ingress, dict) or not agent_ingress.get("rendered"):
        errors.append("agent_ingress")
    else:
        ingress_selected_ids = _selected_id_list(agent_ingress.get("selected_ids"))
        if ingress_selected_ids is None:
            errors.append("agent_ingress.selected_ids")

    review_packet = pending.get("review_packet")
    packet_selected_ids: list[str] | None = None
    if not isinstance(review_packet, dict):
        errors.append("review_packet")
    else:
        packet_selected_ids = _selected_id_list(review_packet.get("selected_ids"))
        if packet_selected_ids is None:
            errors.append("review_packet.selected_ids")

    if selected_ids is not None:
        if packet_selected_ids is not None and packet_selected_ids != selected_ids:
            errors.append("review_packet.selected_ids_mismatch")
        if ingress_selected_ids is not None and ingress_selected_ids != selected_ids:
            errors.append("agent_ingress.selected_ids_mismatch")

    if pending.get("semantic_auto_consolidation") is not False:
        errors.append("semantic_auto_consolidation")
    return errors


def clear_pending_review(path: str | Path) -> None:
    """Remove the pending-review latch if present."""
    target = Path(path).expanduser()
    try:
        target.unlink()
    except FileNotFoundError:
        return


def write_pending_review(
    path: str | Path,
    *,
    decision: ReviewPressureDecision,
    review_request: Any,
    ingress: ReviewPressureIngress,
) -> dict[str, Any]:
    """Persist a compact pending-review latch with atomic replace."""
    target = Path(path).expanduser()
    memory_tags = [asdict(tag) for tag in review_request.memory_tags]
    payload: dict[str, Any] = {
        "kind": "mneme_pending_review",
        "status": "pending",
        "created_at": _utc_timestamp(),
        "mneme_call_seq": decision.mneme_call_seq,
        "reasons": list(decision.reasons),
        "selected_ids": list(review_request.selection.selected_ids),
        "packet_limit": review_request.packet_limit,
        "semantic_auto_consolidation": False,
        "review_pressure": asdict(decision),
        "agent_ingress": asdict(ingress),
        "review_packet": {
            "packet_limit": review_request.packet_limit,
            "selected_ids": list(review_request.selection.selected_ids),
            "memory_tags": memory_tags,
            "prompt": review_request.prompt,
            "expected_output_schema": dict(review_request.expected_output_schema),
            "next_tool": getattr(ingress, "next_tool", "consolidate_review"),
            "tool_guidance": getattr(ingress, "tool_guidance", {}),
            "active_unread_count": review_request.selection.unread_active_count,
            "reviewed_active_count": review_request.selection.reviewed_active_count,
            "deferred_count": review_request.selection.deferred_count,
            "reason": review_request.reason,
        },
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        Path(tmp_name).replace(target)
    except Exception:
        try:
            Path(tmp_name).unlink()
        except FileNotFoundError:
            pass
        raise
    return payload


def pending_review_is_resolved(pending: dict[str, Any], review_receipts: list[dict[str, Any]]) -> bool:
    """Return true when receipts cover every selected id in the pending latch."""
    if pending_review_schema_errors(pending):
        return False
    selected_ids = [str(item) for item in pending.get("selected_ids", [])]
    review_state = derive_review_state(review_receipts)
    for memory_tag_id in selected_ids:
        state = review_state.get(memory_tag_id)
        if state is None or state.status not in {"reviewed", "deferred"} or state.needs_rereview:
            return False
    return True
