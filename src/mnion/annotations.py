"""Append-only later authorship of navigation claims, never memory rewrites."""
from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Iterable
from pathlib import Path
from typing import Any
import json
import os
import re
from uuid import uuid4

from .micro_consolidation import load_micro_consolidation_review_receipts, validate_claim
from .config import default_config_path
from .review_pressure import consolidate_review_tool_guidance
from .review_pressure_state import load_pending_review, pending_review_schema_errors

_EXACT_ROUTE = re.compile(r"review_[A-Za-z0-9_-]+(?::mnion:[1-9][0-9]*)?")
_ANNOTATION_ID = re.compile(r"annotation_[A-Za-z0-9_-]+")


def is_valid_exact_item_route(route: Any) -> bool:
    """Only literal full routes; existence is checked separately, never hints."""
    return isinstance(route, str) and 0 < len(route) <= 256 and _EXACT_ROUTE.fullmatch(route) is not None


def default_annotation_state_dir() -> Path:
    explicit = os.environ.get("MNEME_STATE_DIR")
    if explicit:
        return Path(explicit).expanduser()
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))).expanduser() / "mneme"


def annotation_path_for_receipts(receipts_path: str | Path, annotations_path: str | Path | None = None) -> Path:
    return (Path(annotations_path).expanduser() if annotations_path is not None
            else Path(receipts_path).expanduser().parent / "claim_annotations.jsonl")


def load_claim_annotations(path: str | Path) -> list[dict[str, Any]]:
    """Read audit order, rejecting corrupt evidence rather than silently skipping it."""
    target = Path(path).expanduser()
    if not target.exists():
        return []
    annotations = []
    ids: set[str] = set()
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("annotation receipt must be an object")
        annotation_id = value.get("id")
        if (not isinstance(annotation_id, str) or _ANNOTATION_ID.fullmatch(annotation_id) is None
                or annotation_id in ids or value.get("kind") != "mnion_claim_annotation"
                or not is_valid_exact_item_route(value.get("route"))
                or not isinstance(value.get("created_at"), str) or not value["created_at"].strip()):
            raise ValueError("invalid annotation receipt identity, route, kind, or created_at")
        validate_claim(value.get("claim"))
        if value.get("claim") is None:
            raise ValueError("annotation claim must be non-null")
        ids.add(annotation_id)
        annotations.append(value)
    return annotations


def _pending_barrier(path: Path) -> dict[str, Any] | None:
    try:
        pending = load_pending_review(path)
        errors = pending_review_schema_errors(pending) if pending is not None else []
    except (ValueError, OSError) as exc:
        pending, errors = {}, [str(exc)]
    if pending is None:
        return None
    selected = pending.get("selected_ids", []) if not errors else []
    return {"ok": False,
            "action": "blocked_by_invalid_pending_review" if errors else "blocked_by_pending_review",
            "errors": errors, "next_tool": "consolidate_review",
            "tool_guidance": consolidate_review_tool_guidance(selected),
            "guidance": ("Repair malformed pending review before consolidation or annotation." if errors
                         else "Close the pending review with consolidate_review first; annotation never clears its latch."),
            "cleared_pending_review": False}


def append_claim_annotation(*, exact_item_route: Any, authored_claim: Any,
                            state_dir: str | Path | None = None,
                            receipts_path: str | Path | None = None,
                            annotations_path: str | Path | None = None,
                            db_path: str | Path | None = None,
                            pending_review_path: str | Path | None = None,
                            protected_paths: Iterable[str | Path] = (),
                            retry_annotation_id: Any = None) -> dict[str, Any]:
    """Governed core write, independent of MCP. Retry a recorded id, never re-append.

    Any pending latch blocks this affordance (including receipt-covered latches).
    Ordinary capture/consolidate_review owns their closure, not annotation.
    Hosts with custom artifact paths must supply them in protected_paths.
    """
    from . import read_model

    try:
        if not is_valid_exact_item_route(exact_item_route):
            raise ValueError("exact_item_route must be a literal exact review_ route; no hints, whitespace, or quotes")
        validate_claim(authored_claim)
        if authored_claim is None:
            raise ValueError("authored_claim must be non-null")
        if retry_annotation_id is not None and (not isinstance(retry_annotation_id, str)
                or _ANNOTATION_ID.fullmatch(retry_annotation_id) is None):
            raise ValueError("retry_annotation_id must be a literal annotation id")
    except ValueError as exc:
        return {"ok": False, "action": "invalid_claim_annotation_request", "error": str(exc)}

    root = Path(state_dir).expanduser() if state_dir is not None else default_annotation_state_dir()
    receipts = Path(receipts_path).expanduser() if receipts_path is not None else root / "micro_consolidation_reviews.jsonl"
    ledger = annotation_path_for_receipts(receipts, annotations_path)
    db = Path(db_path).expanduser() if db_path is not None else root / "mneme_read_model.sqlite3"
    pending = Path(pending_review_path).expanduser() if pending_review_path is not None else root / "pending_review.json"
    # SQLite owns auxiliary files for both the configured name and resolved DB
    # target. Protect their destination aliases before any append/index repair.
    protected = [receipts, db, pending, root / "memory_tags.jsonl", root / "mneme_seq.json",
                 root / "config.toml", default_config_path(),
                 *(Path(str(base) + suffix) for base in (db, db.resolve())
                   for suffix in ("-journal", "-wal", "-shm")),
                 *(Path(path).expanduser() for path in protected_paths)]
    if any(ledger.resolve() == path.resolve() or (ledger.exists() and path.exists() and ledger.samefile(path))
           for path in protected):
        return {"ok": False, "action": "invalid_claim_annotation_request",
                "error": "Annotation ledger must be separate from original receipts and other runtime artifacts."}
    blocked = _pending_barrier(pending)
    if blocked is not None:
        return blocked
    try:
        # Source existence, not an index repair or a route-prefix resolution.
        source_receipts = load_micro_consolidation_review_receipts(receipts)
        # Use projection's validated body and eligibility, never raw summary
        # truthiness; whitespace-only receipts do not define an item route.
        existing = any(route == exact_item_route and read_model._mnion_from_payload(payload).summary
                       for receipt in source_receipts
                       if isinstance(receipt.get("mnions"), list) or receipt.get("id") == exact_item_route
                       for route, payload, _ in read_model._mnion_entries_from_receipt(receipt))
        if not existing:
            return {"ok": False, "action": "unknown_item_route", "exact_item_route": exact_item_route,
                    "guidance": "Open get_item for a listed exact item route before authoring; packet audit ids are not item routes."}
        # Validate the same source payloads the projection consumes, without
        # creating/migrating the index. Known corrupt evidence must not gain
        # a new annotation merely because one exact route exists in the file.
        for receipt in source_receipts:
            for _, payload, _ in read_model._mnion_entries_from_receipt(receipt):
                read_model._mnion_from_payload(payload)
        annotations = load_claim_annotations(ledger)
    except (ValueError, TypeError, OSError) as exc:
        return {"ok": False, "action": "annotation_source_unavailable", "error": str(exc)}

    annotation = None
    if retry_annotation_id is not None:
        annotation = next((entry for entry in annotations if entry["id"] == retry_annotation_id), None)
        if annotation is None or annotation["route"] != exact_item_route or annotation["claim"] != authored_claim:
            return {"ok": False, "action": "invalid_annotation_retry",
                    "error": "Retry id must name the already-recorded exact route and authored claim; no receipt appended."}
    reused = annotation is not None
    if annotation is None:
        annotation = {"id": "annotation_" + uuid4().hex, "kind": "mnion_claim_annotation",
                      "route": exact_item_route, "claim": authored_claim,
                      "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        # Encode before opening: invalid Unicode must not create an empty ledger.
        try:
            encoded = (json.dumps(annotation, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            if ledger.exists() and ledger.stat().st_size:
                with ledger.open("rb") as handle:
                    handle.seek(-1, os.SEEK_END)
                    if handle.read(1) != b"\n":
                        encoded = b"\n" + encoded
            ledger.parent.mkdir(parents=True, exist_ok=True)
            with ledger.open("ab") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
        except (OSError, UnicodeError) as exc:
            return {"ok": False, "action": "annotation_write_failed", "error": str(exc),
                    "annotation": annotation,
                    "guidance": "Check this exact annotation id in the ledger before retrying; an I/O failure may follow a partial write."}
    try:
        recorded = load_claim_annotations(ledger)
        if not any(entry == annotation for entry in recorded):
            raise ValueError("annotation receipt read-back failed")
        read_model.materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db, annotations_path=ledger)
        item = read_model.get_item(review_id=exact_item_route, db_path=db)
        # A successful SQLite commit/read is not durable audit evidence: read
        # the sidecar again after projection, retaining the original retry id.
        recorded = load_claim_annotations(ledger)
        if not any(entry == annotation for entry in recorded):
            raise ValueError("annotation receipt post-projection read-back failed")
        latest = next(entry for entry in reversed(recorded) if entry["route"] == exact_item_route)
        if item is None or item.claim_annotation != latest or item.mnion.claim != latest["claim"]:
            raise ValueError("effective annotation projection verification failed")
    except Exception as exc:  # Fail closed after recorded evidence, preserving safe retry identity.
        return {"ok": False, "action": "claim_annotation_recorded_projection_failed",
                "annotation": annotation, "retry_annotation_id": annotation["id"],
                "reused_annotation": reused, "error": str(exc),
                "guidance": "Retry annotate_claim with the same exact_item_route/authored_claim and retry_annotation_id; do not append blindly."}
    return {"ok": True, "action": "claim_annotation_recorded", "annotation": annotation,
            "effective_annotation": item.claim_annotation, "reused_annotation": reused,
            "do_not_infer": ["Later agent-authored navigation, not the original memory passage or proof of an event.",
                             "Original receipt, body, rationale, valence, route and capture call sequence are unchanged."]}
