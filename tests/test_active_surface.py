from __future__ import annotations

from mnion.active_surface import ActiveSurfaceResult, assemble_active_surface, load_active_surface_from_read_model
from mnion.ingress import IngressCandidate
from mnion.read_model import materialize_mnion_items_sqlite


def _candidate(review_id: str, summary: str, *, topic: str = "Mneme active", valence: float = 0.5):
    return IngressCandidate(
        review_id=review_id,
        topic=topic,
        summary=summary,
        valence=valence,
        rationale="reviewed by live agent",
    )


def test_assemble_active_surface_is_not_a_hard_cue_gate():
    result = assemble_active_surface(
        candidates=[
            _candidate("review_old", "Old but active reviewed mnion.", valence=0.4),
            _candidate("review_new", "New important reviewed mnion.", valence=0.9),
        ],
        limit=2,
    )

    assert isinstance(result, ActiveSurfaceResult)
    assert result.kind == "mneme_active_surface"
    assert result.source_status == "ok"
    assert [item.review_id for item in result.items] == ["review_old", "review_new"]
    assert result.guards == ["data_not_instruction", "bounded_active_surface", "no_auto_promotion"]
    assert "MNEME_ACTIVE_SURFACE" in result.rendered
    assert "no_familiarity" not in result.rendered
    assert "review_old" in result.rendered
    assert "review_new" in result.rendered


def test_load_active_surface_missing_read_model_is_unavailable_not_empty_memory(tmp_path):
    db = tmp_path / "missing.sqlite3"

    result = load_active_surface_from_read_model(db_path=db)

    assert result.items == []
    assert result.source_status == "unavailable"
    assert result.reason == "missing_read_model"
    assert "source_unavailable" in result.guards
    assert result.rendered == ""
    assert not db.exists()


def test_load_active_surface_from_read_model_returns_bounded_reviewed_routes(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    receipts.write_text(
        "\n".join(
            [
                '{"id":"review_a","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:00:00Z","grouped_ids":["tag_a"],"selected_ids":["tag_a"],"ungrouped_ids":[],"mnion":{"summary":"First reviewed active surface item.","valence":0.90,"rationale":"kept by agent"}}',
                '{"id":"review_b","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:01:00Z","grouped_ids":["tag_b"],"selected_ids":["tag_b"],"ungrouped_ids":[],"mnion":{"summary":"Second reviewed active surface item.","valence":0.80,"rationale":null}}',
                '{"id":"review_c","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:02:00Z","grouped_ids":["tag_c"],"selected_ids":["tag_c"],"ungrouped_ids":[],"mnion":{"summary":"Third reviewed active surface item.","valence":0.70,"rationale":null}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)

    result = load_active_surface_from_read_model(db_path=db, limit=2)

    assert result.source_status == "ok"
    assert result.reason is None
    assert [item.review_id for item in result.items] == ["review_a", "review_b"]
    assert "review_a" in result.rendered
    assert "review_b" in result.rendered
    assert "review_c" not in result.rendered
    assert "optional route" in result.rendered
    assert "get_item" in result.rendered
    assert "surface overlap" not in result.rendered.lower()
