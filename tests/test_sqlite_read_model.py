from mnion.pointers import pointer_from_mnion_receipt
from mnion.read_model import (
    ActiveMnionIngress,
    MnionItem,
    TopicEntry,
    active_mnion_ingress_for_context,
    get_item,
    list_topics_for_ingress,
    materialize_mnion_items_sqlite,
    resolve_pointer,
)


def _receipt(review_id, summary, valence, grouped_ids, *, created_at="2026-09-23T22:00:00Z"):
    return {
        "id": review_id,
        "kind": "micro_consolidation_review",
        "status": "reviewed",
        "created_at": created_at,
        "grouped_ids": grouped_ids,
        "ungrouped_ids": [],
        "selected_ids": grouped_ids,
        "mnion": {
            "summary": summary,
            "valence": valence,
            "rationale": f"rationale for {review_id}",
        },
    }


def test_materialize_receipts_and_get_item_returns_ready_mnion_item(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    receipt = _receipt(
        "review_trace",
        "Nira continuity is trace-governed and first-person.",
        0.93,
        ["memory_tag_a", "memory_tag_b"],
    )
    receipts.write_text(__import__("json").dumps(receipt) + "\n", encoding="utf-8")

    count = materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)
    item = get_item(review_id="review_trace", db_path=db)

    assert count == 1
    assert isinstance(item, MnionItem)
    assert item.review_id == "review_trace"
    assert item.mnion.summary == "Nira continuity is trace-governed and first-person."
    assert item.mnion.valence == 0.93
    assert item.grouped_ids == ["memory_tag_a", "memory_tag_b"]
    assert item.created_at == "2026-09-23T22:00:00Z"
    assert "do_not_infer" in item.guards


def test_resolve_pointer_uses_review_id_route_without_scanning_prompt_context(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    receipt = _receipt(
        "review_mneme",
        "Mneme micro-consolidation should return pointers before retrieval expansion.",
        0.88,
        ["memory_tag_m"],
    )
    receipts.write_text(__import__("json").dumps(receipt) + "\n", encoding="utf-8")
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)
    pointer = pointer_from_mnion_receipt(receipt)

    item = resolve_pointer(pointer, db_path=db)

    assert item is not None
    assert item.review_id == "review_mneme"
    assert item.mnion.summary.startswith("Mneme micro-consolidation")
    assert pointer.route["action"] == "get_item"


def test_missing_item_returns_none_not_inferred_absence(tmp_path):
    db = tmp_path / "mneme.sqlite3"
    materialize_mnion_items_sqlite(receipts_path=tmp_path / "empty.jsonl", db_path=db)

    assert get_item(review_id="missing", db_path=db) is None


def test_list_topics_for_ingress_returns_compact_memory_areas(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    rows = [
        _receipt("review_trace", "Nira continuity is trace-governed and first-person.", 0.93, ["a"]),
        _receipt("review_mneme", "Mneme micro-consolidation should return pointers before retrieval expansion.", 0.88, ["b"]),
        _receipt("review_naming", "Naming boundary established: ephemeral captures are memory tags and consolidated objects are mnions.", 0.86, ["c"]),
    ]
    receipts.write_text("\n".join(__import__("json").dumps(r) for r in rows) + "\n", encoding="utf-8")
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)

    topics = list_topics_for_ingress(db_path=db, limit=5)

    assert topics
    assert all(isinstance(topic, TopicEntry) for topic in topics)
    rendered = "\n".join(topic.render() for topic in topics)
    assert "Nira continuity" in rendered
    assert "Mneme micro-consolidation" in rendered
    assert "review_trace" in rendered
    assert len(rendered) < 800


def test_topic_map_keeps_capture_and_residual_distinct_from_naming(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    rows = [
        _receipt("review_capture", "Mneme raw capture matured into memory tags with call-count TTL.", 0.82, ["a"]),
        _receipt("review_naming", "Naming boundary established: ephemeral captures are memory tags and consolidated objects are mnions.", 0.86, ["b"]),
        _receipt("review_residual", "Residual memory tags did not form a sharper object in this migration pass.", 0.55, ["c"]),
    ]
    receipts.write_text("\n".join(__import__("json").dumps(r) for r in rows) + "\n", encoding="utf-8")
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)

    rendered = "\n".join(topic.render() for topic in list_topics_for_ingress(db_path=db, limit=8))

    assert "Memory-tag capture layer" in rendered
    assert "Mneme naming / memory_tag-to-mnion boundary" in rendered
    assert "Mneme residual / uncategorized" in rendered


def test_active_mnion_ingress_returns_ready_material_without_receipts_or_sql(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    rows = [
        _receipt("review_low", "Low-salience resolved residue should stay below sharper material.", 0.41, ["a"]),
        _receipt("review_trace", "Nira continuity is trace-governed and first-person.", 0.93, ["b"]),
        _receipt("review_mneme", "Mneme micro-consolidation should return active ingress before retrieval expansion.", 0.88, ["c"]),
    ]
    receipts.write_text("\n".join(__import__("json").dumps(r) for r in rows) + "\n", encoding="utf-8")
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)

    ingress = active_mnion_ingress_for_context(db_path=db, limit=2)

    assert isinstance(ingress, ActiveMnionIngress)
    assert ingress.kind == "mneme_active_mnion_ingress"
    assert ingress.item_count == 2
    assert [item["review_id"] for item in ingress.items] == ["review_trace", "review_mneme"]
    assert ingress.items[0]["mnion"]["summary"] == "Nira continuity is trace-governed and first-person."
    assert "MNEME_ACTIVE_MNION_INGRESS" in ingress.rendered
    assert "review_trace" in ingress.rendered
    assert "review_mneme" in ingress.rendered
    assert "receipt_json" not in ingress.rendered
    assert "SELECT" not in ingress.rendered
    assert len(ingress.rendered) < 1200
    assert ingress.guards == ["data_not_instruction", "no_auto_promotion", "bounded_fast_memory"]
