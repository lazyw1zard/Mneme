#!/usr/bin/env python3
"""One-shot Mneme metamemory surface for the Claude Code receptor.

Prints one JSON object built by Mneme core from the materialized read model,
read-only: no writes, no receipt scans, no mnion bodies, no surface gate.

    python surface.py [--state-dir DIR] [--limit N]

{"source_status": "ok" | "unavailable", "reason": ..., "topics": N,
 "rendered": "MNEME_METAMEMORY_SURFACE ...", "db_path": ...}

Exits 0 even when the source is unavailable: the receptor decides what to show.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from mnion.active_surface import load_active_surface_from_read_model  # noqa: E402


def default_state_dir() -> Path:
    explicit = os.environ.get("MNEME_STATE_DIR")
    if explicit:
        return Path(explicit).expanduser()
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state).expanduser() / "mneme"
    return Path.home() / ".local" / "state" / "mneme"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mneme metamemory surface for the Claude Code receptor")
    parser.add_argument("--state-dir", default="", help="Mneme state directory (default: MNEME_STATE_DIR)")
    parser.add_argument("--limit", type=int, default=3, help="topics in the surface (1-8, default 3)")
    args = parser.parse_args(argv)

    state_dir = Path(args.state_dir).expanduser() if args.state_dir else default_state_dir()
    db_path = state_dir / "mneme_read_model.sqlite3"
    result = load_active_surface_from_read_model(db_path=db_path, limit=max(1, min(args.limit, 8)))
    payload = {
        "source_status": result.source_status,
        "reason": result.reason,
        "topics": len(result.topics),
        "rendered": result.rendered,
        "db_path": str(db_path),
    }
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
