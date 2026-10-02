import json
from datetime import datetime, timedelta, timezone

from mnion.core import (
    DEFAULT_ACTIVE_MEMORY_TAG_LIMIT,
    DEFAULT_CALL_TTL,
    MemoryTagCaptureRequest,
    capture_memory_tag,
    capture_memory_tag_record,
    current_mneme_call_seq,
    load_memory_tags,
    mneme_call_age,
    next_mneme_call_seq,
)


def test_capture_increments_mneme_call_counter_and_records_birth_seq(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"

    first = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="first memory pass", valence=0.4),
        ledger_path=ledger,
        state_path=state,
    )
    second = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="second memory pass", valence=0.6),
        ledger_path=ledger,
        state_path=state,
    )

    assert first.birth_call_seq == 1
    assert second.birth_call_seq == 2
    assert DEFAULT_CALL_TTL == 32
    assert first.call_ttl == DEFAULT_CALL_TTL
    assert second.call_ttl == DEFAULT_CALL_TTL
    assert current_mneme_call_seq(state_path=state) == 2

    raw = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert [row["birth_call_seq"] for row in raw] == [1, 2]
    assert [row["call_ttl"] for row in raw] == [DEFAULT_CALL_TTL, DEFAULT_CALL_TTL]


def test_call_counter_is_a_simple_portable_json_state(tmp_path):
    state = tmp_path / "mneme_seq.json"

    assert current_mneme_call_seq(state_path=state) == 0
    assert next_mneme_call_seq(state_path=state) == 1
    assert next_mneme_call_seq(state_path=state) == 2

    assert json.loads(state.read_text(encoding="utf-8")) == {"seq": 2}


def test_mneme_call_age_is_based_on_mneme_calls_not_wall_clock(tmp_path):
    state = tmp_path / "mneme_seq.json"
    born = next_mneme_call_seq(state_path=state)
    next_mneme_call_seq(state_path=state)
    next_mneme_call_seq(state_path=state)

    assert mneme_call_age(birth_call_seq=born, state_path=state) == 2


def test_call_ttl_can_be_overridden_per_mnion(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"

    record = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="short cycle ttl", valence=0.2, call_ttl=3),
        ledger_path=ledger,
        state_path=state,
    )

    assert record.call_ttl == 3
    assert json.loads(ledger.read_text(encoding="utf-8"))["call_ttl"] == 3


def test_default_active_load_is_bounded_to_prevent_prompt_flood(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    records = []
    for index in range(DEFAULT_ACTIVE_MEMORY_TAG_LIMIT + 5):
        records.append(
            capture_memory_tag_record(
                MemoryTagCaptureRequest(delta=f"active mnion {index}", valence=0.2, call_ttl=100),
                ledger_path=ledger,
                state_path=state,
            )
        )

    loaded = load_memory_tags(ledger_path=ledger, state_path=state)

    assert len(loaded) == DEFAULT_ACTIVE_MEMORY_TAG_LIMIT
    assert [m.id for m in loaded] == [m.id for m in records[-DEFAULT_ACTIVE_MEMORY_TAG_LIMIT:]]
    assert len(load_memory_tags(ledger_path=ledger, state_path=state, limit=None)) == DEFAULT_ACTIVE_MEMORY_TAG_LIMIT + 5


def test_load_memory_tags_hides_records_expired_by_mneme_call_age(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"

    first = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="expires after two later memory calls", valence=0.2, call_ttl=2),
        ledger_path=ledger,
        state_path=state,
    )
    second = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="second pass", valence=0.2),
        ledger_path=ledger,
        state_path=state,
    )
    third = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="third pass", valence=0.2),
        ledger_path=ledger,
        state_path=state,
    )

    assert mneme_call_age(birth_call_seq=first.birth_call_seq, state_path=state) == 2
    assert [m.id for m in load_memory_tags(ledger_path=ledger, state_path=state)] == [second.id, third.id]
    assert [m.id for m in load_memory_tags(ledger_path=ledger, state_path=state, include_expired=True)] == [
        first.id,
        second.id,
        third.id,
    ]


def test_load_memory_tags_keeps_high_valence_tags_after_call_ttl(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"

    pinned = capture_memory_tag(
        MemoryTagCaptureRequest(delta="high valence pinned trace should wait for batch review", valence=0.91, call_ttl=2),
        ledger_path=ledger,
        state_path=state,
    )
    assert pinned.record is not None
    low = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="low valence neighbor expires normally", valence=0.2, call_ttl=2),
        ledger_path=ledger,
        state_path=state,
    )
    third = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="third call ages both prior records", valence=0.2),
        ledger_path=ledger,
        state_path=state,
    )

    assert mneme_call_age(birth_call_seq=pinned.record.birth_call_seq, state_path=state) == 2
    assert mneme_call_age(birth_call_seq=low.birth_call_seq, state_path=state) == 1
    assert [m.id for m in load_memory_tags(ledger_path=ledger, state_path=state)] == [pinned.target_id, low.id, third.id]

    fourth = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="fourth call expires the low valence neighbor", valence=0.2),
        ledger_path=ledger,
        state_path=state,
    )

    assert [m.id for m in load_memory_tags(ledger_path=ledger, state_path=state)] == [pinned.target_id, third.id, fourth.id]


def test_load_memory_tags_keeps_high_valence_tags_after_wall_clock_ttl(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    captured_at = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)

    pinned = capture_memory_tag_record(
        MemoryTagCaptureRequest(
            delta="high valence pinned trace should not disappear before review",
            valence=0.91,
            ttl_seconds=1,
        ),
        ledger_path=ledger,
        state_path=state,
        now=captured_at,
    )
    low = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="low valence trace expires by wall clock", valence=0.2, ttl_seconds=1),
        ledger_path=ledger,
        state_path=state,
        now=captured_at,
    )

    loaded = load_memory_tags(
        ledger_path=ledger,
        state_path=state,
        now=captured_at + timedelta(seconds=2),
    )

    assert [record.id for record in loaded] == [pinned.id]
    assert [record.id for record in load_memory_tags(
        ledger_path=ledger,
        state_path=state,
        now=captured_at + timedelta(seconds=2),
        include_expired=True,
    )] == [pinned.id, low.id]
