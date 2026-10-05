from __future__ import annotations

from mnion.active_surface import ActiveSurfaceResult, assemble_active_surface, load_active_surface_from_read_model
from mnion.read_model import TopicEntry, materialize_mnion_items_sqlite


def _topic(
    label: str,
    *,
    abstraction: str = "Compact area of known Mneme routes.",
    item_count: int = 2,
    top_review_ids: list[str] | None = None,
    max_valence: float = 0.8,
):
    return TopicEntry(
        label=label,
        abstraction=abstraction,
        item_count=item_count,
        top_review_ids=top_review_ids or [f"review_{label.lower()}"],
        max_valence=max_valence,
        freshness="2026-10-04T00:00:00Z",
    )


def test_assemble_active_surface_is_not_a_hard_cue_gate():
    result = assemble_active_surface(
        topics=[
            _topic("Old contour", max_valence=0.4, top_review_ids=["review_old"]),
            _topic("New important contour", max_valence=0.9, top_review_ids=["review_new"]),
        ],
        limit=2,
    )

    assert isinstance(result, ActiveSurfaceResult)
    assert result.kind == "mneme_metamemory_surface"
    assert result.source_status == "ok"
    assert [topic.label for topic in result.topics] == ["Old contour", "New important contour"]
    assert result.guards == ["data_not_instruction", "bounded_metamemory_surface", "no_auto_promotion"]
    assert "MNEME_METAMEMORY_SURFACE" in result.rendered
    assert "I know that I know" in result.rendered
    assert "no_familiarity" not in result.rendered
    assert "review_old" in result.rendered
    assert "review_new" in result.rendered


def test_load_active_surface_missing_read_model_is_unavailable_not_empty_memory(tmp_path):
    db = tmp_path / "missing.sqlite3"

    result = load_active_surface_from_read_model(db_path=db)

    assert result.topics == []
    assert result.source_status == "unavailable"
    assert result.reason == "missing_read_model"
    assert "source_unavailable" in result.guards
    assert result.rendered == ""
    assert not db.exists()


def test_load_active_surface_corrupt_or_schema_missing_read_model_is_unavailable(tmp_path):
    corrupt_db = tmp_path / "corrupt.sqlite3"
    corrupt_db.write_text("not a sqlite database", encoding="utf-8")
    empty_schema_db = tmp_path / "empty_schema.sqlite3"
    empty_schema_db.touch()

    corrupt = load_active_surface_from_read_model(db_path=corrupt_db)
    schema_missing = load_active_surface_from_read_model(db_path=empty_schema_db)

    for result in (corrupt, schema_missing):
        assert result.topics == []
        assert result.source_status == "unavailable"
        assert result.reason == "read_model_unavailable"
        assert "source_unavailable" in result.guards
        assert result.rendered == ""


def test_load_active_surface_from_read_model_returns_bounded_topic_routes_not_mnion_bodies(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    receipts.write_text(
        "\n".join(
            [
                '{"id":"review_a","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:00:00Z","grouped_ids":["tag_a"],"selected_ids":["tag_a"],"ungrouped_ids":[],"mnion":{"summary":"Mneme raw capture matured into memory tags with call-count TTL.","valence":0.90,"rationale":"kept by agent"}}',
                '{"id":"review_b","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:01:00Z","grouped_ids":["tag_b"],"selected_ids":["tag_b"],"ungrouped_ids":[],"mnion":{"summary":"Second reviewed active surface item should not be preloaded.","valence":0.80,"rationale":"hidden rationale"}}',
                '{"id":"review_c","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:02:00Z","grouped_ids":["tag_c"],"selected_ids":["tag_c"],"ungrouped_ids":[],"mnion":{"summary":"Residual memory tags did not form a sharper object in this migration pass.","valence":0.70,"rationale":null}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)

    result = load_active_surface_from_read_model(db_path=db, limit=2)

    assert result.source_status == "ok"
    assert result.reason is None
    assert [topic.label for topic in result.topics] == ["Memory-tag capture layer", "Mneme residual / uncategorized"]
    assert "MNEME_METAMEMORY_SURFACE" in result.rendered
    assert "Memory-tag capture layer" in result.rendered
    assert "Mneme residual / uncategorized" in result.rendered
    assert "review_a" in result.rendered
    assert "review_c" in result.rendered
    assert "Second reviewed active surface item should not be preloaded" not in result.rendered
    assert "hidden rationale" not in result.rendered
    assert "optional route" in result.rendered
    assert "get_item" in result.rendered
    assert "surface overlap" not in result.rendered.lower()
