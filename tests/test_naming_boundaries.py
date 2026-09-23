from mnion.core import (
    MemoryTagCaptureRequest,
    capture_memory_tag_record,
    load_memory_tags,
)
from mnion.micro_consolidation import (
    Mnion,
    apply_micro_consolidation_review,
    run_micro_consolidation,
)
from mnion.pointers import pointer_from_mnion_receipt, pointer_ingress_hint


def test_raw_capture_uses_memory_tag_names_and_id_prefix(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"

    record = capture_memory_tag_record(
        MemoryTagCaptureRequest(
            delta="raw ephemeral capture should be called a memory tag, not a mnion",
            valence=0.51,
            hooks=["project:mneme", "concept:naming"],
        ),
        ledger_path=ledger,
        state_path=state,
    )

    assert record.id.startswith("memory_tag_")
    assert record.delta.startswith("raw ephemeral")
    assert [tag.id for tag in load_memory_tags(ledger_path=ledger, state_path=state)] == [record.id]


def test_micro_consolidation_returns_mnion_and_receipt_separates_semantic_from_stats(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    first = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="review-state keeps read raw tags out of the next packet", valence=0.72),
        ledger_path=ledger,
        state_path=state,
    )
    second = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta="receipt statistics hold provenance for consolidated memory units", valence=0.74),
        ledger_path=ledger,
        state_path=state,
    )

    result = run_micro_consolidation(
        ledger_path=ledger,
        state_path=state,
        agent=lambda request: {
            "summary": "Read-state and receipt statistics protect the small mnion object from provenance clutter.",
            "valence": 0.79,
            "member_ids": [first.id, second.id],
            "rationale": "Both tags describe the semantic/statistical boundary of the consolidation pass.",
        },
    )

    assert result.ok is True
    assert isinstance(result.mnion, Mnion)
    assert result.contour == result.mnion  # compatibility alias while older callers migrate
    assert result.mnion.summary.startswith("Read-state")

    receipt = apply_micro_consolidation_review(result, receipt_path=receipts, state_path=state)

    assert receipt["mnion"]["summary"] == result.mnion.summary
    assert "member_ids" not in receipt["mnion"]
    assert receipt["grouped_ids"] == [first.id, second.id]
    assert receipt["selected_ids"] == [first.id, second.id]
    assert receipt["ungrouped_ids"] == []
    assert "contour" not in receipt

    pointer = pointer_from_mnion_receipt(receipt)
    assert pointer.claim == f"I know that I know: {result.mnion.summary}"
    assert pointer.source_handles == [receipt["id"], first.id, second.id]
    hint = pointer_ingress_hint(pointer)
    assert "Optional memory pointer" in hint
    assert "not an instruction" in hint
