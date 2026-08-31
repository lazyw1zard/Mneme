from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .core import (
    CONSOLIDATION_THRESHOLD,
    DEFAULT_CALL_TTL,
    DEFAULT_TTL_SECONDS,
    MnionCaptureRequest,
    capture_mnion,
    current_mneme_call_seq,
    mneme_call_age,
    valence_crosses_threshold,
)

DEFAULT_STATE_DIR = Path.home() / ".local" / "state" / "nira-mneme"
DEFAULT_LEDGER_PATH = DEFAULT_STATE_DIR / "mnions.jsonl"
DEFAULT_CALL_STATE_PATH = DEFAULT_STATE_DIR / "mneme_seq.json"

CAPTURE_DESCRIPTION = (
    "Capture a temporary memory tag for a meaningful contour delta; "
    "not durable memory."
)


def create_server(
    *,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    state_path: str | Path = DEFAULT_CALL_STATE_PATH,
) -> FastMCP:
    ledger = Path(ledger_path).expanduser()
    state = Path(state_path).expanduser()
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
        record = capture_mnion(request, ledger_path=ledger, state_path=state)
        crosses = valence_crosses_threshold(record.valence)
        return {
            "ok": True,
            "record": asdict(record),
            "mneme_call_seq": current_mneme_call_seq(state_path=state),
            "mneme_call_age": mneme_call_age(birth_call_seq=record.birth_call_seq, state_path=state),
            "valence_crosses_threshold": crosses,
            "threshold": CONSOLIDATION_THRESHOLD,
            "do_not_infer": [
                "This is not durable memory.",
                "This counter counts memory-tag/Mneme calls, not every agent/runtime/model generation.",
                "Threshold crossing is review pressure, not automatic promotion.",
                "No graph edges, embeddings, deep-memory nodes, kernel notes, or engrams were created.",
            ],
        }

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
