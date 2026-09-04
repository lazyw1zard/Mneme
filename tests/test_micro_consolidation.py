import json
from datetime import datetime, timezone

from mnion.core import MnionCaptureRequest, capture_mnion
from mnion.micro_consolidation import (
    ConsolidatedContour,
    MicroConsolidationError,
    prepare_micro_consolidation_request,
    run_micro_consolidation,
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


def test_prepare_micro_consolidation_request_returns_latest_ten_mnions(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    records = _capture_many(ledger, state, 12)

    request = prepare_micro_consolidation_request(ledger_path=ledger, state_path=state, limit=10)

    assert request.reason == "latest_mnions"
    assert request.limit == 10
    assert [mnion.id for mnion in request.mnions] == [record.id for record in records[-10:]]
    assert "Find semantically close mnions" in request.prompt
    assert "summary" in request.expected_output_schema
    assert "valence" in request.expected_output_schema


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

    result = run_micro_consolidation(ledger_path=ledger, state_path=state, agent=fake_agent, limit=10)

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
