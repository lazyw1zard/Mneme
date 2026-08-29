import json
from datetime import datetime, timezone

from mnion.core import MnionCaptureRequest, capture_mnion, load_mnions


def test_capture_writes_one_ephemeral_mnion_jsonl_record(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    request = MnionCaptureRequest(
        stub="MCP visibility acts as a preconscious capture affordance.",
        source_ref="telegram:current_turn",
        trigger="architecture_correction",
        affect_hints=["contour_shift", "caution"],
        evidence=["MCP нам нужен именно как орган захвата"],
        ttl_seconds=3600,
    )

    record = capture_mnion(request, ledger_path=ledger)

    assert record.id.startswith("mnion_")
    assert record.kind == "mnion"
    assert record.status == "tag"
    assert record.stub == request.stub
    assert record.source_ref == request.source_ref
    assert record.trigger == request.trigger
    assert record.affect_hints == ["contour_shift", "caution"]
    assert record.evidence == ["MCP нам нужен именно как орган захвата"]
    assert record.ttl_seconds == 3600
    assert record.captured_at.endswith("Z")
    assert record.expires_at.endswith("Z")
    assert record.promotion is None

    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    raw = json.loads(lines[0])
    assert raw["id"] == record.id
    assert raw["status"] == "tag"
    assert "graph" not in raw
    assert "embedding" not in raw
    assert "connections" not in raw


def test_capture_requires_bounded_stub_and_source_ref(tmp_path):
    ledger = tmp_path / "mnions.jsonl"

    too_long = "x" * 281
    request = MnionCaptureRequest(stub=too_long, source_ref="telegram:turn", trigger="manual")

    try:
        capture_mnion(request, ledger_path=ledger)
    except ValueError as exc:
        assert "stub" in str(exc)
    else:
        raise AssertionError("expected long stub to be rejected")

    request = MnionCaptureRequest(stub="short", source_ref="", trigger="manual")
    try:
        capture_mnion(request, ledger_path=ledger)
    except ValueError as exc:
        assert "source_ref" in str(exc)
    else:
        raise AssertionError("expected empty source_ref to be rejected")

    assert not ledger.exists()


def test_load_mnions_skips_expired_by_default(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    old_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    request = MnionCaptureRequest(
        stub="temporary tag",
        source_ref="test:turn",
        trigger="manual",
        ttl_seconds=1,
    )
    captured = capture_mnion(request, ledger_path=ledger, now=old_now)

    later = datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc)

    assert load_mnions(ledger_path=ledger, now=later) == []
    assert [m.id for m in load_mnions(ledger_path=ledger, now=later, include_expired=True)] == [captured.id]
