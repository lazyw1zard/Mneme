import json

from mnion.core import (
    LINK_THRESHOLD,
    MnionCaptureRequest,
    REINFORCE_THRESHOLD,
    capture_memory_tag,
    load_mnions,
)


def _lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_capture_memory_tag_creates_when_no_active_match(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"

    result = capture_memory_tag(
        MnionCaptureRequest(
            delta="memory_tag_capture should use a small pre-capture filter before appending duplicates",
            valence=0.55,
            hooks=["project:mneme", "mcp:memory_tag_capture", "concept:pre_capture_filter"],
            trigger="pre_capture_filter_design",
            affect_hints=["precision"],
        ),
        ledger_path=ledger,
        state_path=state,
    )

    assert result.action == "created"
    assert result.record is not None
    assert result.record.id.startswith("mnion_")
    assert result.target_id == result.record.id
    assert result.linked_ids == []
    assert result.match_score == 0.0
    assert len(_lines(ledger)) == 1
    assert len(load_mnions(ledger_path=ledger, state_path=state)) == 1


def test_capture_memory_tag_reinforces_strong_active_match_without_duplicate(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    first = capture_memory_tag(
        MnionCaptureRequest(
            delta="memory_tag_capture should reinforce active similar tags instead of appending obvious duplicates",
            valence=0.60,
            hooks=["project:mneme", "mcp:memory_tag_capture", "concept:pre_capture_filter", "lifecycle:reinforcement"],
            trigger="pre_capture_filter_design",
            affect_hints=["precision", "confidence_update"],
        ),
        ledger_path=ledger,
        state_path=state,
    )

    second = capture_memory_tag(
        MnionCaptureRequest(
            delta="Mneme pre capture filter should not create duplicate memory_tag_capture tags when the same contour appears again",
            valence=0.50,
            hooks=["project:mneme", "mcp:memory-tag-capture", "concept:pre-capture-filter", "lifecycle:reinforcement"],
            trigger="pre-capture-filter-repeat",
            affect_hints=["precision", "confidence-update"],
        ),
        ledger_path=ledger,
        state_path=state,
    )

    assert second.action == "reinforced"
    assert second.record is None
    assert second.target_id == first.record.id
    assert second.linked_ids == [first.record.id]
    assert second.match_score >= REINFORCE_THRESHOLD
    assert second.valence_before == 0.60
    assert second.valence_after > second.valence_before
    assert second.valence_after < 1.0
    rows = _lines(ledger)
    assert len(rows) == 2
    assert rows[1]["event"] == "reinforcement"
    assert rows[1]["target_id"] == first.record.id
    assert rows[1]["action"] == "reinforced"
    assert [m.id for m in load_mnions(ledger_path=ledger, state_path=state)] == [first.record.id]


def test_capture_memory_tag_links_related_but_distinct_candidate(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    first = capture_memory_tag(
        MnionCaptureRequest(
            delta="memory_tag_capture should use a cheap pre-capture filter before appending duplicate tags",
            valence=0.56,
            hooks=["project:mneme", "mcp:memory_tag_capture", "concept:pre_capture_filter"],
            trigger="pre_capture_filter_design",
            affect_hints=["precision"],
        ),
        ledger_path=ledger,
        state_path=state,
    )

    related = capture_memory_tag(
        MnionCaptureRequest(
            delta="Mneme should keep public code and documentation portable for open source reuse",
            valence=0.58,
            hooks=["project:mneme", "oss:portable_state", "mcp:memory_tag_capture"],
            trigger="oss_cleanup_design",
            affect_hints=["precision", "agency_pull"],
        ),
        ledger_path=ledger,
        state_path=state,
    )

    assert related.action == "linked_new"
    assert related.record is not None
    assert related.target_id == related.record.id
    assert related.linked_ids == [first.record.id]
    assert LINK_THRESHOLD <= related.match_score < REINFORCE_THRESHOLD
    rows = _lines(ledger)
    assert len(rows) == 3
    assert rows[1]["id"] == related.record.id
    assert rows[2]["event"] == "link"
    assert rows[2]["source_id"] == related.record.id
    assert rows[2]["target_ids"] == [first.record.id]
    assert [m.id for m in load_mnions(ledger_path=ledger, state_path=state)] == [first.record.id, related.record.id]


def test_reinforcement_refreshes_call_life_for_active_load(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    state = tmp_path / "mneme_seq.json"
    first = capture_memory_tag(
        MnionCaptureRequest(
            delta="temporary tag should remain active after reinforcement signal appears again",
            valence=0.60,
            call_ttl=2,
            hooks=["project:mneme", "concept:refresh_life", "lifecycle:reinforcement"],
            trigger="refresh_life_design",
            affect_hints=["precision"],
        ),
        ledger_path=ledger,
        state_path=state,
    )
    reinforced = capture_memory_tag(
        MnionCaptureRequest(
            delta="temporary tag refresh life should remain active when the same reinforcement signal appears again",
            valence=0.50,
            call_ttl=2,
            hooks=["project:mneme", "concept:refresh-life", "lifecycle:reinforcement"],
            trigger="refresh-life-repeat",
            affect_hints=["precision"],
        ),
        ledger_path=ledger,
        state_path=state,
    )
    assert reinforced.action == "reinforced"

    capture_memory_tag(
        MnionCaptureRequest(
            delta="unrelated call advances the mneme sequence",
            valence=0.20,
            hooks=["project:other"],
            trigger="unrelated",
            affect_hints=["caution"],
        ),
        ledger_path=ledger,
        state_path=state,
    )

    active_ids = [m.id for m in load_mnions(ledger_path=ledger, state_path=state)]
    assert first.record.id in active_ids
