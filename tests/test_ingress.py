"""Hot-path ingress guarantees, exercised on the surviving metamemory reader.

The old word-gate tests are retired with their implementation. Source availability,
read-only behavior, and latency remain required for every host receptor.
"""
from __future__ import annotations

import json
import sqlite3
import time

import pytest

from mnion.active_surface import load_active_surface_from_read_model
from mnion.read_model import materialize_mnion_items_sqlite, read_model_freshness


def _receipt():
    return {
        "id": "review_ingress",
        "kind": "micro_consolidation_review",
        "status": "reviewed",
        "created_at": "2026-10-08T00:00:00Z",
        "selected_ids": ["tag_ingress"],
        "grouped_ids": ["tag_ingress"],
        "ungrouped_ids": [],
        "mnion": {"summary": "A reviewed private body must stay behind its route.", "valence": 0.8, "rationale": "private rationale"},
    }


def _model(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    receipts.write_text(json.dumps(_receipt()) + "\n", encoding="utf-8")
    db = tmp_path / "mneme.sqlite3"
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)
    return receipts, db


def test_valid_empty_model_is_distinct_from_unavailable_source(tmp_path):
    receipts = tmp_path / "receipts.jsonl"
    receipts.touch()
    db = tmp_path / "mneme.sqlite3"
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)

    result = load_active_surface_from_read_model(db_path=db)

    assert result.source_status == "ok"
    assert result.topics == []
    assert "source_unavailable" not in result.guards
    assert "no_familiarity" not in result.guards
    assert result.rendered == ""


def test_locked_read_model_returns_unavailable_promptly(tmp_path):
    _, db = _model(tmp_path)
    with sqlite3.connect(db) as writer:
        writer.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        result = load_active_surface_from_read_model(db_path=db)
        elapsed = time.monotonic() - started
        writer.rollback()

    assert elapsed < 0.5
    assert result.source_status == "unavailable"
    assert result.reason == "read_model_unavailable"
    assert result.topics == []
    assert "source_unavailable" in result.guards
    assert result.rendered == ""


def test_ingress_reads_a_read_only_model_without_mutation(tmp_path):
    _, db = _model(tmp_path)
    before = db.read_bytes()
    db.chmod(0o444)
    try:
        result = load_active_surface_from_read_model(db_path=db)
    finally:
        db.chmod(0o644)

    assert result.source_status == "ok"
    assert result.topics[0].top_review_ids == ["review_ingress"]
    assert db.read_bytes() == before
    assert "private rationale" not in result.rendered


def test_ingress_does_not_repair_stale_model(tmp_path):
    receipts, db = _model(tmp_path)
    with receipts.open("a", encoding="utf-8") as stream:
        receipt = _receipt()
        receipt["id"] = "review_new"
        stream.write(json.dumps(receipt) + "\n")
    before = db.read_bytes()
    assert read_model_freshness(receipts_path=receipts, db_path=db).status == "stale"

    result = load_active_surface_from_read_model(db_path=db)

    # This reader reports snapshot availability, not receipt freshness. Explicit
    # retrieval repairs stale models; pre-turn ingress must leave them untouched.
    assert result.source_status == "ok"
    assert result.topics[0].top_review_ids == ["review_ingress"]
    assert "review_new" not in result.rendered
    assert db.read_bytes() == before
    assert read_model_freshness(receipts_path=receipts, db_path=db).status == "stale"


def test_ingress_negative_limit_is_rejected_before_io(tmp_path):
    db = tmp_path / "missing.sqlite3"
    with pytest.raises(ValueError, match="limit"):
        load_active_surface_from_read_model(db_path=db, limit=0)
    assert not db.exists()
