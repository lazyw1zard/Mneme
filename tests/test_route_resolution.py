import asyncio
import json

from mnion.mcp_server import create_server
from mnion.read_model import materialize_mnion_items_sqlite, resolve_review_id

PACKET = "review_43618c0d189940a698eedcf156aabd0a"
SINGLE = "review_ea93eed36da643ca868187fb40e533c5"


def _receipts(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    single = {
        "id": SINGLE, "kind": "micro_consolidation_review", "status": "reviewed", "created_at": "2026-09-30T00:00:00Z",
        "selected_ids": ["tag_a"], "grouped_ids": ["tag_a"], "ungrouped_ids": [],
        "mnion": {"summary": "The whole Mneme plan.", "valence": 0.8, "rationale": None},
    }
    packet = {
        "id": PACKET, "kind": "micro_consolidation_review", "status": "reviewed", "created_at": "2026-10-07T00:00:00Z",
        "selected_ids": ["tag_b", "tag_c"], "grouped_ids": ["tag_b", "tag_c"], "reviewed_noise_ids": [],
        "deferred_ids": [], "ungrouped_ids": [],
        "mnions": [
            {"review_id": PACKET + ":mnion:1", "grouped_ids": ["tag_b"],
             "mnion": {"summary": "A receptor for Claude Code.", "valence": 0.75, "rationale": None}},
            {"review_id": PACKET + ":mnion:2", "grouped_ids": ["tag_c"],
             "mnion": {"summary": "A gear modelled by a sample and printed.", "valence": 0.6, "rationale": None}},
        ],
    }
    receipts.write_text(json.dumps(single) + "\n" + json.dumps(packet) + "\n", encoding="utf-8")
    return receipts


def _db(tmp_path):
    db = tmp_path / "mneme.sqlite3"
    materialize_mnion_items_sqlite(receipts_path=_receipts(tmp_path), db_path=db)
    return db


def test_exact_ids_resolve_as_they_are(tmp_path):
    db = _db(tmp_path)
    assert resolve_review_id(review_id=PACKET + ":mnion:2", db_path=db) == (PACKET + ":mnion:2", [])
    assert resolve_review_id(review_id=SINGLE, db_path=db) == (SINGLE, [])


def test_copy_mistakes_agents_make_still_resolve(tmp_path):
    db = _db(tmp_path)
    # observed 2026-10-08: a fresh agent passed the id without "review_" (and without the suffix)
    assert resolve_review_id(review_id="43618c0d189940a698eedcf156aabd0a:mnion:2", db_path=db) == (PACKET + ":mnion:2", [])
    assert resolve_review_id(review_id="ea93eed36da643ca868187fb40e533c5", db_path=db) == (SINGLE, [])
    assert resolve_review_id(review_id="`review_ea93eed3`", db_path=db) == (SINGLE, [])   # quoted short prefix


def test_a_packet_id_without_its_suffix_names_the_candidates(tmp_path):
    db = _db(tmp_path)
    assert resolve_review_id(review_id="43618c0d189940a698eedcf156aabd0a", db_path=db) == (
        None, [PACKET + ":mnion:1", PACKET + ":mnion:2"])


def test_too_short_or_unknown_ids_stay_misses(tmp_path):
    db = _db(tmp_path)
    assert resolve_review_id(review_id="review_4", db_path=db) == (None, [])       # too short to stand for a route
    assert resolve_review_id(review_id="review_ffffffff", db_path=db) == (None, [])
    assert resolve_review_id(review_id="  ", db_path=db) == (None, [])


def test_get_item_tool_resolves_and_offers_candidates(tmp_path):
    receipts = _receipts(tmp_path)
    server = create_server(ledger_path=tmp_path / "memory_tags.jsonl", receipts_path=receipts,
                           read_model_path=tmp_path / "mneme.sqlite3")

    def call(review_id):
        result = asyncio.run(server.call_tool("get_item", {"review_id": review_id}))
        return result.structured_content if hasattr(result, "structured_content") else result[1]

    fixed = call("43618c0d189940a698eedcf156aabd0a:mnion:2")
    assert fixed["ok"] is True
    assert fixed["item"]["review_id"] == PACKET + ":mnion:2"
    assert fixed["resolved_from"] == "43618c0d189940a698eedcf156aabd0a:mnion:2"

    exact = call(SINGLE)
    assert exact["ok"] is True and "resolved_from" not in exact

    ambiguous = call("43618c0d189940a698eedcf156aabd0a")
    assert ambiguous["ok"] is False
    assert [c["review_id"] for c in ambiguous["did_you_mean"]] == [PACKET + ":mnion:1", PACKET + ":mnion:2"]
    assert ambiguous["did_you_mean"][1]["starts"] == "A gear modelled by a sample and printed."
