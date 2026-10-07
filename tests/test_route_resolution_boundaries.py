"""Route hints must never turn a selected item into a different memory."""
import asyncio
import json
import sqlite3
from typing import Any

import pytest

from mnion.mcp_server import create_server
from mnion.read_model import resolve_review_id
from test_route_resolution import PACKET, SINGLE, _db, _receipts


def _payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structured_content", getattr(result, "structuredContent", None))
    if structured is not None:
        return structured
    if isinstance(result, tuple):
        return result[1]
    return json.loads(next(part.text for part in result.content if part.type == "text"))


def test_invalid_tool_route_is_rejected_before_read_model_repair(tmp_path):
    db = tmp_path / "missing" / "mneme.sqlite3"
    server = create_server(ledger_path=tmp_path / "tags.jsonl", receipts_path=tmp_path / "receipts.jsonl",
                           read_model_path=db)
    result = asyncio.run(server.call_tool("get_item", {"review_id": " " + SINGLE}))
    payload = _payload(result)
    assert payload["ok"] is False
    assert payload["error_code"] == "invalid_route_query"
    assert payload["review_id"] == " " + SINGLE
    assert not db.parent.exists()


def test_retrieval_tool_advertises_hint_grammar_and_evidence_boundary(tmp_path):
    server = create_server(ledger_path=tmp_path / "tags.jsonl", receipts_path=tmp_path / "receipts.jsonl",
                           read_model_path=tmp_path / "db.sqlite3")
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}
    assert "6..32 lowercase hex" in tools["get_item"].description
    assert "did_you_mean" in tools["get_item"].description
    assert "opened mnion" in tools["get_item"].description
    assert "not evidence" in tools["list_topics"].description


def test_storage_error_during_route_resolution_is_structured(tmp_path, monkeypatch):
    import mnion.mcp_server as adapter
    def unavailable(**kwargs):
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(adapter, "resolve_review_id", unavailable)
    server = create_server(ledger_path=tmp_path / "tags.jsonl", receipts_path=_receipts(tmp_path),
                           read_model_path=tmp_path / "db.sqlite3")
    result = asyncio.run(server.call_tool("get_item", {"review_id": SINGLE}))
    payload = _payload(result)
    assert payload["ok"] is False
    assert payload["error_code"] == "read_model_unavailable"
    assert "item" not in payload


def test_missing_full_item_route_cannot_match_a_longer_item_number(tmp_path):
    db = _db(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE mnion_items SET review_id = ? WHERE review_id = ?",
                     (PACKET + ":mnion:10", PACKET + ":mnion:1"))
    for route in (PACKET + ":mnion:1", PACKET.removeprefix("review_") + ":mnion:1",
                  "review_43618c:mnion:1"):
        assert resolve_review_id(review_id=route, db_path=db) == (None, [])


@pytest.mark.parametrize("route", [
    " " + SINGLE, SINGLE + " ", "`" + SINGLE + "`", "'" + SINGLE + "'",
    '"' + SINGLE + '"', "review_ea93ee%", "review_ea93ee_", "review_ea93ee*",
    "review_ea93ee:mnion:", "review_ea93ee:mnion:0", "review_ea93ee:mnion:01",
    "review_ea93ee:mnion:1junk", "review_" + "e" * 33, None, 123,
])
def test_non_hint_queries_do_not_receive_alias_fallback(tmp_path, route):
    assert resolve_review_id(review_id=route, db_path=_db(tmp_path)) == (None, [])


def test_unknown_exact_legacy_route_is_not_a_prefix(tmp_path):
    db = _db(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE mnion_items SET review_id = ? WHERE review_id = ?",
                     ("review_legacy_long", SINGLE))
    assert resolve_review_id(review_id="review_legacy_long", db_path=db) == ("review_legacy_long", [])
    assert resolve_review_id(review_id="review_legacy", db_path=db) == (None, [])


def test_route_resolution_does_not_create_storage(tmp_path):
    db = tmp_path / "missing" / "mneme.sqlite3"
    assert resolve_review_id(review_id=SINGLE, db_path=db) == (None, [])
    assert not db.parent.exists()
    empty = tmp_path / "empty.sqlite3"
    with sqlite3.connect(empty):
        pass
    with pytest.raises(sqlite3.Error):
        resolve_review_id(review_id=SINGLE, db_path=empty)
    with sqlite3.connect(empty) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []


def test_large_ambiguous_hint_is_bounded_and_never_auto_selects(tmp_path):
    db = _db(tmp_path)
    with sqlite3.connect(db) as conn:
        template = conn.execute("SELECT * FROM mnion_items WHERE review_id = ?", (SINGLE,)).fetchone()
        conn.executemany("INSERT INTO mnion_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         [(f"review_abcdef{i:026x}", *template[1:]) for i in range(100)])
    resolved, candidates = resolve_review_id(review_id="abcdef", db_path=db)
    assert resolved is None
    assert len(candidates) == 9  # eight visible options plus a witness that more exist
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    # Preserve this materialized model during the explicit read by retaining its source marker.
    server = create_server(ledger_path=tmp_path / "tags.jsonl", receipts_path=receipts,
                           read_model_path=db)
    result = asyncio.run(server.call_tool("get_item", {"review_id": "abcdef"}))
    payload = _payload(result)
    assert payload["ok"] is False
    assert "item" not in payload
    assert len(payload["did_you_mean"]) == 8
    assert payload["has_more_candidates"] is True


def test_unique_short_hint_with_item_suffix_preserves_exact_item(tmp_path):
    db = _db(tmp_path)
    assert resolve_review_id(review_id="43618c:mnion:2", db_path=db) == (PACKET + ":mnion:2", [])
    assert resolve_review_id(review_id="review_ea93ee", db_path=db) == (SINGLE, [])


def test_route_lookup_fetches_only_bounded_rows(tmp_path, monkeypatch):
    db = _db(tmp_path)
    connect = sqlite3.connect
    fetched = []

    class Cursor:
        def __init__(self, cursor):
            self.cursor = cursor
        def fetchone(self):
            return self.cursor.fetchone()
        def fetchall(self):
            rows = self.cursor.fetchall()
            fetched.append(len(rows))
            return rows

    class Connection:
        def __init__(self, *args, **kwargs):
            self.conn = connect(*args, **kwargs)
        def execute(self, *args, **kwargs):
            return Cursor(self.conn.execute(*args, **kwargs))
        def close(self):
            self.conn.close()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(sqlite3, "connect", Connection)
    assert resolve_review_id(review_id=SINGLE, db_path=db) == (SINGLE, [])
    assert fetched == []  # exact lookup must not fetch the whole id index
