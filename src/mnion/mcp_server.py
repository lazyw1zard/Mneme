from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .core import (
    CONSOLIDATION_THRESHOLD,
    DEFAULT_TTL_SECONDS,
    MnionCaptureRequest,
    capture_mnion,
    valence_crosses_threshold,
)

DEFAULT_LEDGER_PATH = Path.home() / ".local" / "state" / "nira-mneme" / "mnions.jsonl"

CAPTURE_DESCRIPTION = (
    "Capture one cheap ephemeral mnion: a small contour delta with valence, TTL, hooks, "
    "trigger, and affect hints. Use when the live turn leaves a correction, self-promise, "
    "affect signal, contour shift, loss-cost, curiosity pull, or other movement that may "
    "deserve later consolidation. Unreinforced mnions decay. This does not create graph "
    "edges, embeddings, deep memory, kernel updates, or engrams."
)


def create_server(*, ledger_path: str | Path = DEFAULT_LEDGER_PATH) -> FastMCP:
    ledger = Path(ledger_path).expanduser()
    server = FastMCP(
        "nira-mnion-capture",
        instructions=(
            "Mnion is a capture organ, not full Mneme. Capture minimal ephemeral contour "
            "deltas when affect/significance is visible; threshold crossing only means "
            "later review pressure, not automatic promotion."
        ),
    )

    @server.tool(name="mnion_capture", description=CAPTURE_DESCRIPTION)
    def mnion_capture(
        delta: str,
        valence: float,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        hooks: list[str] | None = None,
        trigger: str | None = None,
        affect_hints: list[str] | None = None,
    ) -> dict[str, Any]:
        request = MnionCaptureRequest(
            delta=delta,
            valence=valence,
            ttl_seconds=ttl_seconds,
            hooks=hooks,
            trigger=trigger,
            affect_hints=affect_hints,
        )
        record = capture_mnion(request, ledger_path=ledger)
        crosses = valence_crosses_threshold(record.valence)
        return {
            "ok": True,
            "record": asdict(record),
            "valence_crosses_threshold": crosses,
            "threshold": CONSOLIDATION_THRESHOLD,
            "do_not_infer": [
                "This is not durable memory.",
                "Threshold crossing is review pressure, not automatic promotion.",
                "No graph edges, embeddings, deep-memory nodes, kernel notes, or engrams were created.",
            ],
        }

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
