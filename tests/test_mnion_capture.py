import json
from datetime import datetime, timezone

from mnion.core import (
    CONSOLIDATION_THRESHOLD,
    MnionCaptureRequest,
    capture_mnion,
    load_mnions,
    valence_crosses_threshold,
)


def test_capture_writes_minimal_mnion_delta_valence_ttl_record(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    request = MnionCaptureRequest(
        delta="MCP capture should catch the contour delta before durable memory.",
        valence=0.62,
        ttl_seconds=3600,
        hooks=["telegram:current_turn", "concept:mneme_capture"],
        trigger="architecture_correction",
        affect_hints=["contour_shift", "caution"],
    )

    record = capture_mnion(request, ledger_path=ledger)

    assert record.id.startswith("mnion_")
    assert record.delta == request.delta
    assert record.valence == 0.62
    assert record.ttl_seconds == 3600
    assert record.birth_call_seq == 1
    assert record.call_ttl == 20
    assert record.hooks == ["telegram:current_turn", "concept:mneme_capture"]
    assert record.trigger == "architecture_correction"
    assert record.affect_hints == ["contour_shift", "caution"]
    assert record.captured_at.endswith("Z")
    assert record.expires_at.endswith("Z")

    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    raw = json.loads(lines[0])
    assert raw["id"] == record.id
    assert set(raw) == {
        "id",
        "delta",
        "valence",
        "ttl_seconds",
        "call_ttl",
        "birth_call_seq",
        "captured_at",
        "expires_at",
        "hooks",
        "trigger",
        "affect_hints",
    }
    assert "kind" not in raw
    assert "status" not in raw
    assert "source_ref" not in raw
    assert "evidence" not in raw
    assert "promotion" not in raw
    assert "graph" not in raw
    assert "embedding" not in raw
    assert "connections" not in raw


def test_capture_requires_bounded_delta_and_normalized_valence(tmp_path):
    ledger = tmp_path / "mnions.jsonl"

    too_long = "x" * 281
    request = MnionCaptureRequest(delta=too_long, valence=0.5)

    try:
        capture_mnion(request, ledger_path=ledger)
    except ValueError as exc:
        assert "delta" in str(exc)
    else:
        raise AssertionError("expected long delta to be rejected")

    request = MnionCaptureRequest(delta="short", valence=1.2)
    try:
        capture_mnion(request, ledger_path=ledger)
    except ValueError as exc:
        assert "valence" in str(exc)
    else:
        raise AssertionError("expected out-of-range valence to be rejected")

    request = MnionCaptureRequest(delta="short", valence=0.5, call_ttl=0)
    try:
        capture_mnion(request, ledger_path=ledger)
    except ValueError as exc:
        assert "call_ttl" in str(exc)
    else:
        raise AssertionError("expected non-positive call_ttl to be rejected")

    assert not ledger.exists()


def test_valence_threshold_is_explicit_and_not_status_field():
    assert CONSOLIDATION_THRESHOLD == 0.7
    assert not valence_crosses_threshold(0.69)
    assert valence_crosses_threshold(0.7)


def test_load_mnions_skips_expired_by_default(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    old_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    request = MnionCaptureRequest(
        delta="temporary contour delta",
        valence=0.2,
        ttl_seconds=1,
    )
    captured = capture_mnion(request, ledger_path=ledger, now=old_now)

    later = datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc)

    assert load_mnions(ledger_path=ledger, now=later) == []
    assert [m.id for m in load_mnions(ledger_path=ledger, now=later, include_expired=True)] == [captured.id]
