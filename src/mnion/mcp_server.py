from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .core import DEFAULT_TTL_SECONDS, MnionCaptureRequest, capture_mnion

DEFAULT_LEDGER_PATH = Path.home() / ".local" / "state" / "nira-mneme" / "mnions.jsonl"

CAPTURE_DESCRIPTION = (
    "Capture one cheap ephemeral mnion tag for Mneme. Use when the live turn leaves "
    "a correction, self-promise, affect signal, contour shift, loss-cost, curiosity pull, "
    "or other movement that may deserve consolidation. This only appends a small tag; "
    "unreinforced tags may decay. It does not create graph edges, embeddings, deep memory, "
    "kernel updates, or engrams."
)


def create_server(*, ledger_path: str | Path = DEFAULT_LEDGER_PATH) -> FastMCP:
    ledger = Path(ledger_path).expanduser()
    server = FastMCP(
        "nira-mnion-capture",
        instructions=(
            "Mnion is a capture organ, not full Mneme. Capture minimal ephemeral tags "
            "when affect/significance is visible; do not promote them automatically."
        ),
    )

    @server.tool(name="mnion_capture", description=CAPTURE_DESCRIPTION)
    def mnion_capture(
        stub: str,
        source_ref: str,
        trigger: str,
        affect_hints: list[str] | None = None,
        evidence: list[str] | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> dict[str, Any]:
        request = MnionCaptureRequest(
            stub=stub,
            source_ref=source_ref,
            trigger=trigger,
            affect_hints=affect_hints,
            evidence=evidence,
            ttl_seconds=ttl_seconds,
        )
        record = capture_mnion(request, ledger_path=ledger)
        return {
            "ok": True,
            "record": asdict(record),
            "do_not_infer": [
                "This is not durable memory.",
                "No graph edges, embeddings, deep-memory nodes, kernel notes, or engrams were created.",
                "Promotion requires later valence/review governance.",
            ],
        }

    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
