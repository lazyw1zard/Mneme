import json
from datetime import datetime, timezone

from cogito.core import (
    CogitoEventRequest,
    cycles_since,
    latest_cycle,
    load_cycles,
    record_generation_cycle,
)


def test_record_generation_cycle_writes_runtime_neutral_jsonl(tmp_path):
    ledger = tmp_path / "cycles.jsonl"
    record = record_generation_cycle(
        CogitoEventRequest(
            runtime="test-runtime",
            adapter="manual_probe",
            movement_kind="model_generation",
            cycle_kind="assistant_response",
            session_ref="test-runtime:session-1",
            turn_ref="turn-1",
            model="model-x",
            input_tokens=12,
            output_tokens=7,
            output_chars=42,
            tool_call_count=0,
            metadata={"finish_reason": "stop"},
        ),
        ledger_path=ledger,
        now=datetime(2026, 8, 29, 22, 45, 0, tzinfo=timezone.utc),
    )

    assert record.id.startswith("cg_20260829T224500Z_")
    assert record.runtime == "test-runtime"
    assert record.adapter == "manual_probe"
    assert record.movement_kind == "model_generation"
    assert record.cycle_kind == "assistant_response"
    assert record.session_ref == "test-runtime:session-1"
    assert record.turn_ref == "turn-1"
    assert record.input_tokens == 12
    assert record.output_tokens == 7
    assert record.output_chars == 42
    assert record.tool_call_count == 0

    [line] = ledger.read_text(encoding="utf-8").splitlines()
    saved = json.loads(line)
    assert saved["id"] == record.id
    assert saved["ts"] == "2026-08-29T22:45:00Z"
    assert "hermes" not in saved


def test_cycles_since_counts_generation_cycles_after_anchor(tmp_path):
    ledger = tmp_path / "cycles.jsonl"
    first = record_generation_cycle(
        CogitoEventRequest(runtime="r", adapter="a", movement_kind="model_generation"),
        ledger_path=ledger,
        now=datetime(2026, 8, 29, 22, 0, 0, tzinfo=timezone.utc),
    )
    record_generation_cycle(
        CogitoEventRequest(runtime="r", adapter="a", movement_kind="tool_effect"),
        ledger_path=ledger,
        now=datetime(2026, 8, 29, 22, 1, 0, tzinfo=timezone.utc),
    )
    second = record_generation_cycle(
        CogitoEventRequest(runtime="r", adapter="a", movement_kind="model_generation"),
        ledger_path=ledger,
        now=datetime(2026, 8, 29, 22, 2, 0, tzinfo=timezone.utc),
    )
    record_generation_cycle(
        CogitoEventRequest(runtime="other", adapter="a", movement_kind="model_generation"),
        ledger_path=ledger,
        now=datetime(2026, 8, 29, 22, 3, 0, tzinfo=timezone.utc),
    )

    assert cycles_since(first.id, ledger_path=ledger) == 2
    assert cycles_since(first.id, ledger_path=ledger, runtime="r") == 1
    assert cycles_since(second.id, ledger_path=ledger, runtime="r") == 0


def test_latest_cycle_returns_last_record(tmp_path):
    ledger = tmp_path / "cycles.jsonl"
    assert latest_cycle(ledger_path=ledger) is None
    first = record_generation_cycle(
        CogitoEventRequest(runtime="r", adapter="a", movement_kind="model_generation"),
        ledger_path=ledger,
        now=datetime(2026, 8, 29, 22, 0, 0, tzinfo=timezone.utc),
    )
    second = record_generation_cycle(
        CogitoEventRequest(runtime="r", adapter="a", movement_kind="model_generation"),
        ledger_path=ledger,
        now=datetime(2026, 8, 29, 22, 1, 0, tzinfo=timezone.utc),
    )

    assert latest_cycle(ledger_path=ledger).id == second.id
    assert [r.id for r in load_cycles(ledger_path=ledger)] == [first.id, second.id]
