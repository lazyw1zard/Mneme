import json

from mnion.core import (
    DEFAULT_ACTIVE_MNION_LIMIT,
    DEFAULT_CALL_TTL,
    MnionCaptureRequest,
    capture_mnion,
    current_mneme_call_seq,
    load_mnions,
    mneme_call_age,
    next_mneme_call_seq,
)


def test_capture_increments_mneme_call_counter_and_records_birth_seq(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"

    first = capture_mnion(
        MnionCaptureRequest(delta="first memory pass", valence=0.4),
        ledger_path=ledger,
        state_path=state,
    )
    second = capture_mnion(
        MnionCaptureRequest(delta="second memory pass", valence=0.6),
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
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"

    record = capture_mnion(
        MnionCaptureRequest(delta="short cycle ttl", valence=0.2, call_ttl=3),
        ledger_path=ledger,
        state_path=state,
    )

    assert record.call_ttl == 3
    assert json.loads(ledger.read_text(encoding="utf-8"))["call_ttl"] == 3


def test_default_active_load_is_bounded_to_prevent_prompt_flood(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    records = []
    for index in range(DEFAULT_ACTIVE_MNION_LIMIT + 5):
        records.append(
            capture_mnion(
                MnionCaptureRequest(delta=f"active mnion {index}", valence=0.2, call_ttl=100),
                ledger_path=ledger,
                state_path=state,
            )
        )

    loaded = load_mnions(ledger_path=ledger, state_path=state)

    assert len(loaded) == DEFAULT_ACTIVE_MNION_LIMIT
    assert [m.id for m in loaded] == [m.id for m in records[-DEFAULT_ACTIVE_MNION_LIMIT:]]
    assert len(load_mnions(ledger_path=ledger, state_path=state, limit=None)) == DEFAULT_ACTIVE_MNION_LIMIT + 5


def test_load_mnions_hides_records_expired_by_mneme_call_age(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"

    first = capture_mnion(
        MnionCaptureRequest(delta="expires after two later memory calls", valence=0.2, call_ttl=2),
        ledger_path=ledger,
        state_path=state,
    )
    second = capture_mnion(
        MnionCaptureRequest(delta="second pass", valence=0.2),
        ledger_path=ledger,
        state_path=state,
    )
    third = capture_mnion(
        MnionCaptureRequest(delta="third pass", valence=0.2),
        ledger_path=ledger,
        state_path=state,
    )

    assert mneme_call_age(birth_call_seq=first.birth_call_seq, state_path=state) == 2
    assert [m.id for m in load_mnions(ledger_path=ledger, state_path=state)] == [second.id, third.id]
    assert [m.id for m in load_mnions(ledger_path=ledger, state_path=state, include_expired=True)] == [
        first.id,
        second.id,
        third.id,
    ]
