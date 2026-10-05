import sqlite3
import time

import pytest

from mnion.ingress import (
    IngressCandidate,
    IngressCandidateLoadResult,
    ProbeDecision,
    assemble_ingress,
    load_ingress_candidate_source_from_read_model,
    load_ingress_candidates_from_read_model,
    should_probe_metamemory,
)
from mnion.read_model import materialize_mnion_items_sqlite


def _candidate(
    review_id: str,
    summary: str,
    *,
    topic: str = "Mneme ingress",
    valence: float = 0.8,
    rationale: str | None = None,
) -> IngressCandidate:
    return IngressCandidate(
        review_id=review_id,
        topic=topic,
        summary=summary,
        valence=valence,
        rationale=rationale,
    )


@pytest.mark.parametrize("cue", ["", "  ", "ok", "Ок", "спасибо"])
def test_should_probe_metamemory_closes_on_trivial_prompts(cue):
    decision = should_probe_metamemory(
        cue,
        candidates=[_candidate("review_ingress", "Mneme ingress uses a familiarity gate.")],
    )

    assert isinstance(decision, ProbeDecision)
    assert decision.should_probe is False
    assert decision.strength == "closed"
    assert "trivial_prompt" in decision.reasons
    assert decision.matched_terms == []


def test_should_probe_metamemory_uses_mneme_known_vocabulary_not_fixed_keywords():
    decision = should_probe_metamemory(
        "Вернемся к latency-safe recall для adapter boundary",
        candidates=[
            _candidate(
                "review_latency",
                "Latency-safe recall lets Mneme ingress feel like continuity, not an external report.",
                topic="Mneme latency-safe ingress",
                valence=0.94,
            ),
            _candidate(
                "review_adapter",
                "Runtime-neutral core plus host adapters keeps Mneme portable.",
                topic="Harness adapter boundary",
                valence=0.86,
            ),
        ],
    )

    assert decision.should_probe is True
    assert decision.strength == "strong"
    assert set(decision.matched_terms) >= {"latency", "recall", "adapter", "boundary"}
    assert "familiarity_overlap" in decision.reasons


def test_shared_memory_markers_only_boost_existing_familiarity():
    empty_memory_decision = should_probe_metamemory(
        "Почему мы уже выбрали такой подход?",
        candidates=[],
    )
    familiar_decision = should_probe_metamemory(
        "Почему мы уже выбрали ingress adapter?",
        candidates=[_candidate("review_adapter", "Ingress adapter boundary should stay outside core.")],
    )

    assert empty_memory_decision.should_probe is False
    assert "no_familiarity" in empty_memory_decision.reasons
    assert familiar_decision.should_probe is True
    assert "shared_marker_boost" in familiar_decision.reasons
    assert familiar_decision.score > empty_memory_decision.score


def test_should_probe_metamemory_strength_uses_best_candidate_not_union_vocabulary():
    decision = should_probe_metamemory(
        "dream git whatsapp",
        candidates=[
            _candidate("review_dream", "Dream practice keeps old traces warm.", topic="Dream"),
            _candidate("review_git", "Git preserves verified work slices.", topic="Durability"),
            _candidate("review_chat", "WhatsApp contact belongs outside Mneme.", topic="Contact"),
        ],
    )

    assert decision.should_probe is True
    assert decision.strength == "light"
    assert set(decision.matched_terms) == {"dream", "git", "whatsapp"}


def test_common_terms_do_not_open_gate_without_specific_overlap():
    decision = should_probe_metamemory(
        "Что думаешь про review?",
        candidates=[
            _candidate("review_sleep", "Review receipt for sleep support.", topic="Review"),
            _candidate("review_board", "Review receipt for Agentboard coordination.", topic="Review"),
            _candidate("review_mneme", "Review receipt for Mneme ingress.", topic="Review"),
        ],
    )

    assert decision.should_probe is False
    assert decision.strength == "closed"
    assert "weak_familiarity_overlap" in decision.reasons
    assert decision.matched_terms == ["review"]


def test_assemble_ingress_does_not_route_on_common_terms_only():
    result = assemble_ingress(
        "Что думаешь про review?",
        candidates=[
            _candidate("review_sleep", "Review receipt for sleep support.", topic="Review"),
            _candidate("review_board", "Review receipt for Agentboard coordination.", topic="Review"),
            _candidate("review_mneme", "Review receipt for Mneme ingress.", topic="Review"),
        ],
    )

    assert result.decision.should_probe is False
    assert result.routes == []
    assert "weak_familiarity_overlap" in result.decision.reasons


def test_russian_stemming_does_not_resurrect_stopwords():
    decision = should_probe_metamemory(
        "когда такое",
        candidates=[
            _candidate(
                "review_common_words",
                "Когда такое повторяется, common words must not become memory signal.",
                topic="Когда такое",
            )
        ],
    )

    assert decision.should_probe is False
    assert decision.reasons == ["no_familiarity"]
    assert decision.matched_terms == []


def test_fallback_residual_topic_label_is_not_a_familiarity_trigger():
    decision = should_probe_metamemory(
        "Mneme residual uncategorized",
        candidates=[
            _candidate(
                "review_dream",
                "Dream practice is contour hygiene.",
                topic="Mneme residual / uncategorized",
            )
        ],
    )
    content_decision = should_probe_metamemory(
        "Вернемся к dream contour",
        candidates=[
            _candidate(
                "review_dream",
                "Dream practice is contour hygiene.",
                topic="Mneme residual / uncategorized",
            )
        ],
    )

    assert decision.should_probe is False
    assert "no_familiarity" in decision.reasons
    assert content_decision.should_probe is True
    assert set(content_decision.matched_terms) >= {"dream", "contour"}


def test_slash_prefixed_input_is_not_core_trivial_prompt():
    decision = should_probe_metamemory(
        "/c/Agents путь к доске agentboard",
        candidates=[_candidate("review_agentboard", "Agentboard path keeps active tasks visible.")],
    )

    assert decision.should_probe is True
    assert "trivial_prompt" not in decision.reasons


def test_russian_light_stemming_avoids_simple_false_absence():
    decision = should_probe_metamemory(
        "Вернёмся к шлюзу",
        candidates=[_candidate("review_gateway", "Telegram шлюз должен оставаться тонким адаптером.")],
    )

    assert decision.should_probe is True
    assert "шлюз" in decision.matched_terms


def test_assemble_ingress_returns_bounded_compact_routes_without_host_rendering():
    result = assemble_ingress(
        "Нужно продолжить latency-safe Mneme ingress и adapter boundary",
        candidates=[
            _candidate(
                "review_latency",
                "Mneme ingress must be latency-safe and return compact routes.",
                topic="Mneme latency-safe ingress",
                valence=0.94,
                rationale="speed preserves continuity",
            ),
            _candidate(
                "review_adapter",
                "Mneme keeps a protocol-neutral core and host-native adapters.",
                topic="Harness adapter boundary",
                valence=0.9,
            ),
            _candidate(
                "review_sleep_paw",
                "Dream practice is contour hygiene, not productivity.",
                topic="Dream practice",
                valence=0.88,
            ),
        ],
        limit=2,
    )

    assert result.kind == "mneme_ingress"
    assert result.decision.should_probe is True
    assert [route.review_id for route in result.routes] == ["review_latency", "review_adapter"]
    assert result.routes[0].topic == "Mneme latency-safe ingress"
    assert result.routes[0].hint == "Mneme ingress must be latency-safe and return compact routes."
    assert result.routes[0].score >= result.routes[1].score
    assert result.guards == ["data_not_instruction", "bounded_ingress", "no_auto_promotion"]
    assert not hasattr(result, "rendered")


def test_assemble_ingress_route_hints_are_compact():
    long_summary = " ".join(["Agentboard route should stay compact"] * 20)

    result = assemble_ingress(
        "agentboard route",
        candidates=[_candidate("review_agentboard", long_summary, topic="Agentboard route")],
    )

    assert result.decision.should_probe is True
    assert len(result.routes) == 1
    assert len(result.routes[0].hint) <= 180
    assert result.routes[0].hint.endswith("…")


def test_assemble_ingress_returns_empty_when_gate_is_closed():
    result = assemble_ingress(
        "ok",
        candidates=[_candidate("review_latency", "Mneme ingress must be latency-safe.")],
    )

    assert result.decision.should_probe is False
    assert result.routes == []
    assert "trivial_prompt" in result.decision.reasons


def test_load_ingress_candidates_from_read_model_returns_compact_candidates(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    receipts.write_text(
        "\n".join(
            [
                '{"id":"review_latency","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:00:00Z","grouped_ids":["tag_a"],"selected_ids":["tag_a"],"ungrouped_ids":[],"mnion":{"summary":"Mneme ingress must be latency-safe and route-shaped.","valence":0.94,"rationale":"fast recall preserves continuity"}}',
                '{"id":"review_dream","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:01:00Z","grouped_ids":["tag_b"],"selected_ids":["tag_b"],"ungrouped_ids":[],"mnion":{"summary":"Dream practice is contour hygiene.","valence":0.88,"rationale":null}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)

    result = load_ingress_candidate_source_from_read_model(db_path=db, limit=1)
    candidates = load_ingress_candidates_from_read_model(db_path=db, limit=1)

    assert isinstance(result, IngressCandidateLoadResult)
    assert result.source_status == "ok"
    assert result.reason is None
    assert result.guards == []
    assert result.candidates == candidates == [
        IngressCandidate(
            review_id="review_latency",
            topic="Mneme residual / uncategorized",
            summary="Mneme ingress must be latency-safe and route-shaped.",
            valence=0.94,
            rationale="fast recall preserves continuity",
        )
    ]


def test_read_model_source_status_distinguishes_missing_database_from_empty_memory(tmp_path):
    db = tmp_path / "missing.sqlite3"

    result = load_ingress_candidate_source_from_read_model(db_path=db)

    assert result == IngressCandidateLoadResult(
        candidates=[],
        source_status="unavailable",
        reason="missing_read_model",
        guards=["source_unavailable"],
    )
    assert not db.exists()


def test_empty_existing_read_model_is_available_and_reports_no_familiarity(tmp_path):
    receipts = tmp_path / "empty_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)

    loaded = load_ingress_candidate_source_from_read_model(db_path=db)
    result = assemble_ingress(
        "Вернемся к latency-safe Mneme ingress",
        candidates=loaded.candidates,
        source_status=loaded.source_status,
    )

    assert loaded == IngressCandidateLoadResult(candidates=[], source_status="ok", reason=None, guards=[])
    assert result.source_status == "ok"
    assert result.decision.should_probe is False
    assert result.decision.reasons == ["no_familiarity"]
    assert "source_unavailable" not in result.guards


def test_locked_read_model_returns_quickly_as_unavailable_source(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    receipts.write_text(
        '{"id":"review_latency","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:00:00Z","grouped_ids":["tag_a"],"selected_ids":["tag_a"],"ungrouped_ids":[],"mnion":{"summary":"Mneme ingress must be latency-safe.","valence":0.94,"rationale":null}}\n',
        encoding="utf-8",
    )
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)
    locker = sqlite3.connect(db)
    try:
        locker.execute("BEGIN EXCLUSIVE")

        started = time.monotonic()
        result = load_ingress_candidate_source_from_read_model(db_path=db, timeout_seconds=0.001)
        elapsed = time.monotonic() - started
    finally:
        locker.rollback()
        locker.close()

    assert elapsed < 0.5
    assert result.candidates == []
    assert result.source_status == "unavailable"
    assert result.reason == "read_model_unavailable"
    assert "source_unavailable" in result.guards


def test_assemble_ingress_reports_unavailable_source_without_claiming_no_familiarity():
    result = assemble_ingress(
        "Вернемся к latency-safe Mneme ingress",
        candidates=[],
        source_status="unavailable",
    )

    assert result.source_status == "unavailable"
    assert result.decision.should_probe is False
    assert result.decision.reasons == ["source_unavailable"]
    assert "no_familiarity" not in result.decision.reasons
    assert result.routes == []
    assert "source_unavailable" in result.guards
