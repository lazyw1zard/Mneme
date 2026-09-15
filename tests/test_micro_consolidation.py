import json
from datetime import datetime, timezone

from mnion.core import MnionCaptureRequest, capture_mnion
from mnion.micro_consolidation import (
    ConsolidatedContour,
    MicroConsolidationError,
    MicroConsolidationSelection,
    ReviewState,
    derive_review_state,
    prepare_micro_consolidation_request,
    run_micro_consolidation,
    select_unread_active_mnions,
)


def _capture_many(ledger, state, count):
    records = []
    now = datetime.now(timezone.utc)
    for index in range(count):
        records.append(
            capture_mnion(
                MnionCaptureRequest(
                    delta=f"mnion delta {index}",
                    valence=0.2 + index / 100,
                    hooks=["project:mneme", f"concept:{index}"],
                    trigger=f"test_{index}",
                    affect_hints=["test"],
                ),
                ledger_path=ledger,
                state_path=state,
                now=now,
            )
        )
    return records


def test_prepare_micro_consolidation_request_returns_oldest_unread_active_mnions(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    records = _capture_many(ledger, state, 12)

    request = prepare_micro_consolidation_request(ledger_path=ledger, state_path=state, packet_limit=10)

    assert request.reason == "unread_active_coverage"
    assert request.packet_limit == 10
    assert [mnion.id for mnion in request.mnions] == [record.id for record in records[:10]]
    assert request.selection.strategy == "unread_active_coverage"
    assert request.selection.selected_ids == [record.id for record in records[:10]]
    assert request.selection.unread_active_count == 12
    assert "Find semantically close mnions" in request.prompt
    assert "summary" in request.expected_output_schema
    assert "valence" in request.expected_output_schema


def test_selection_metadata_can_describe_unread_active_coverage():
    selection = MicroConsolidationSelection(
        strategy="unread_active_coverage",
        reason="backlog_pressure",
        selected_ids=["mnion_a", "mnion_b"],
        unread_active_count=7,
        reviewed_active_count=3,
        deferred_count=1,
        backend="derived_jsonl",
    )

    assert selection.strategy == "unread_active_coverage"
    assert selection.reason == "backlog_pressure"
    assert selection.selected_ids == ["mnion_a", "mnion_b"]
    assert selection.unread_active_count == 7
    assert selection.reviewed_active_count == 3
    assert selection.deferred_count == 1
    assert selection.backend == "derived_jsonl"


def test_derive_review_state_marks_reviewed_and_deferred_mnions():
    review_state = derive_review_state(
        [
            {
                "id": "review_1",
                "mneme_call_seq": 12,
                "grouped_ids": ["mnion_grouped"],
                "ungrouped_ids": ["mnion_ungrouped"],
                "deferred_ids": ["mnion_deferred"],
            }
        ]
    )

    assert review_state["mnion_grouped"] == ReviewState(
        status="reviewed",
        last_review_id="review_1",
        last_review_seq=12,
        outcome="grouped",
    )
    assert review_state["mnion_ungrouped"].status == "reviewed"
    assert review_state["mnion_ungrouped"].outcome == "ungrouped"
    assert review_state["mnion_deferred"].status == "deferred"
    assert review_state["mnion_deferred"].outcome == "deferred"


def test_derive_review_state_uses_latest_receipt_for_same_mnion():
    review_state = derive_review_state(
        [
            {"id": "review_1", "mneme_call_seq": 1, "deferred_ids": ["mnion_a"]},
            {"id": "review_2", "mneme_call_seq": 2, "grouped_ids": ["mnion_a"]},
        ]
    )

    assert review_state["mnion_a"] == ReviewState(
        status="reviewed",
        last_review_id="review_2",
        last_review_seq=2,
        outcome="grouped",
    )


def test_select_unread_active_mnions_skips_reviewed_and_bounds_packet(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    records = _capture_many(ledger, state, 5)
    review_state = {
        records[0].id: ReviewState(status="reviewed", last_review_id="review_1", outcome="grouped"),
        records[3].id: ReviewState(status="deferred", last_review_id="review_1", outcome="deferred"),
    }

    packet = select_unread_active_mnions(records, review_state, packet_limit=2)

    assert [mnion.id for mnion in packet.mnions] == [records[1].id, records[2].id]
    assert packet.selection.strategy == "unread_active_coverage"
    assert packet.selection.reason == "unread_active_coverage"
    assert packet.selection.selected_ids == [records[1].id, records[2].id]
    assert packet.selection.unread_active_count == 3
    assert packet.selection.reviewed_active_count == 1
    assert packet.selection.deferred_count == 1
    assert packet.selection.backend == "derived_jsonl"


def test_prepare_micro_consolidation_request_uses_review_receipts_to_skip_reviewed(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    records = _capture_many(ledger, state, 4)

    request = prepare_micro_consolidation_request(
        ledger_path=ledger,
        state_path=state,
        packet_limit=10,
        review_receipts=[{"id": "review_1", "grouped_ids": [records[0].id, records[2].id]}],
    )

    assert [mnion.id for mnion in request.mnions] == [records[1].id, records[3].id]
    assert request.selection.strategy == "unread_active_coverage"
    assert request.selection.selected_ids == [records[1].id, records[3].id]
    assert request.selection.unread_active_count == 2
    assert request.selection.reviewed_active_count == 2
    assert request.selection.deferred_count == 0
    assert request.selection.backend == "derived_jsonl"


def test_run_micro_consolidation_calls_agent_and_returns_contour(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    records = _capture_many(ledger, state, 3)
    seen = {}

    def fake_agent(request):
        seen["ids"] = [mnion.id for mnion in request.mnions]
        return {
            "summary": "Several mnions circle the same micro-consolidation pressure.",
            "valence": 0.73,
            "member_ids": [records[0].id, records[2].id],
            "rationale": "They both describe the same background pressure from different angles.",
        }

    result = run_micro_consolidation(ledger_path=ledger, state_path=state, agent=fake_agent, packet_limit=10)

    assert result.ok is True
    assert result.error is None
    assert seen["ids"] == [record.id for record in records]
    assert result.contour == ConsolidatedContour(
        summary="Several mnions circle the same micro-consolidation pressure.",
        valence=0.73,
        member_ids=[records[0].id, records[2].id],
        rationale="They both describe the same background pressure from different angles.",
    )


def test_run_micro_consolidation_returns_error_when_agent_call_fails(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    _capture_many(ledger, state, 2)

    def broken_agent(request):
        raise RuntimeError("agent unavailable")

    result = run_micro_consolidation(ledger_path=ledger, state_path=state, agent=broken_agent)

    assert result.ok is False
    assert result.contour is None
    assert isinstance(result.error, MicroConsolidationError)
    assert result.error.reason == "agent_call_failed"
    assert "agent unavailable" in result.error.message


def test_run_micro_consolidation_returns_error_for_invalid_agent_shape(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    _capture_many(ledger, state, 1)

    result = run_micro_consolidation(
        ledger_path=ledger,
        state_path=state,
        agent=lambda request: {"summary": "missing valence"},
    )

    assert result.ok is False
    assert result.contour is None
    assert result.error is not None
    assert result.error.reason == "invalid_agent_response"


def test_run_micro_consolidation_does_not_write_review_events_yet(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    _capture_many(ledger, state, 2)
    before = ledger.read_text(encoding="utf-8")

    run_micro_consolidation(
        ledger_path=ledger,
        state_path=state,
        agent=lambda request: {"summary": "test contour", "valence": 0.5, "member_ids": []},
    )

    assert ledger.read_text(encoding="utf-8") == before
    assert all(json.loads(line).get("event") is None for line in before.splitlines())
