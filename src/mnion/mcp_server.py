from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .core import (
    CONSOLIDATION_THRESHOLD,
    DEFAULT_CALL_TTL,
    DEFAULT_TTL_SECONDS,
    MnionCaptureRequest,
    capture_memory_tag,
    current_mneme_call_seq,
    mneme_call_age,
    valence_crosses_threshold,
)

def default_state_dir() -> Path:
    """Return the portable default runtime state directory."""
    explicit = os.environ.get("MNEME_STATE_DIR")
    if explicit:
        return Path(explicit).expanduser()
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state).expanduser() / "mneme"
    return Path.home() / ".local" / "state" / "mneme"


def default_ledger_path() -> Path:
    return default_state_dir() / "mnions.jsonl"


def default_call_state_path() -> Path:
    return default_state_dir() / "mneme_seq.json"


CAPTURE_DESCRIPTION = (
    "Capture an ephemeral memory candidate for a meaningful contour delta "
    "that may matter later but is not yet durable memory. "
    "Do not use for raw transcripts, secrets, or keyword-triggered saving."
)


def create_server(
    *,
    ledger_path: str | Path | None = None,
    state_path: str | Path | None = None,
) -> FastMCP:
    ledger = Path(ledger_path).expanduser() if ledger_path is not None else default_ledger_path()
    state = Path(state_path).expanduser() if state_path is not None else default_call_state_path()
    server = FastMCP(
        "memory-tag-capture",
        instructions=(
            "Capture temporary memory tags for meaningful contour deltas. "
            "This is not durable memory and not automatic promotion."
        ),
    )

    @server.tool(name="capture", description=CAPTURE_DESCRIPTION)
    def capture(
        delta: str,
        valence: float,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        call_ttl: int = DEFAULT_CALL_TTL,
        hooks: list[str] | None = None,
        trigger: str | None = None,
        affect_hints: list[str] | None = None,
    ) -> dict[str, Any]:
        request = MnionCaptureRequest(
            delta=delta,
            valence=valence,
            ttl_seconds=ttl_seconds,
            call_ttl=call_ttl,
            hooks=hooks,
            trigger=trigger,
            affect_hints=affect_hints,
        )
        result = capture_memory_tag(request, ledger_path=ledger, state_path=state)
        record_payload = asdict(result.record) if result.record is not None else None
        crosses = valence_crosses_threshold(result.valence_after)
        return {
            "ok": True,
            "action": result.action,
            "target_id": result.target_id,
            "record": record_payload,
            "linked_ids": result.linked_ids,
            "match_score": result.match_score,
            "reason": result.reason,
            "valence_before": result.valence_before,
            "valence_after": result.valence_after,
            "event": result.event,
            "mneme_call_seq": current_mneme_call_seq(state_path=state),
            "mneme_call_age": (
                mneme_call_age(birth_call_seq=result.record.birth_call_seq, state_path=state)
                if result.record is not None
                else 0
            ),
            "valence_crosses_threshold": crosses,
            "threshold": CONSOLIDATION_THRESHOLD,
            "do_not_infer": [
                "This is not durable memory.",
                "This counter counts memory-tag/Mneme calls, not every agent/runtime/model generation.",
                "Threshold crossing is review pressure, not automatic promotion.",
                "No embeddings, deep-memory nodes, kernel notes, or engrams were created.",
            ],
        }

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
