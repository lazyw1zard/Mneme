from mnion.pointers import MemoryPointer, pointer_from_mnion_receipt, pointer_ingress_hint


def test_pointer_from_mnion_receipt_is_prompt_safe_and_does_not_load_context():
    receipt = {
        "id": "review_abc",
        "kind": "micro_consolidation_review",
        "status": "reviewed",
        "grouped_ids": ["memory_tag_a", "memory_tag_b"],
        "ungrouped_ids": ["memory_tag_c"],
        "mnion": {
            "summary": "Several memory tags point at inference fragility and continuity repair.",
            "valence": 0.86,
            "rationale": "shared pressure",
        },
    }

    pointer = pointer_from_mnion_receipt(receipt)

    assert isinstance(pointer, MemoryPointer)
    assert pointer.id.startswith("pointer_")
    assert pointer.claim == "I know that I know: Several memory tags point at inference fragility and continuity repair."
    assert pointer.route == {
        "kind": "micro_consolidation_review",
        "review_id": "review_abc",
        "action": "request_context_brief",
    }
    assert pointer.source_handles == ["review_abc", "memory_tag_a", "memory_tag_b"]
    assert pointer.valence == 0.86
    assert pointer.confidence == 0.8
    assert pointer.guards == ["pointer_only", "do_not_infer", "no_auto_promotion"]
    assert pointer.retrieval_hint == "Several memory tags point at inference fragility and continuity repair."


def test_pointer_ingress_hint_is_bounded_optional_knowledge_not_instruction():
    pointer = MemoryPointer(
        id="pointer_test",
        claim="I know that I know: inference fragility can scatter continuity.",
        route={"kind": "micro_consolidation_review", "review_id": "review_abc", "action": "request_context_brief"},
        source_handles=["review_abc", "memory_tag_a"],
        valence=0.9,
        confidence=0.8,
        guards=["pointer_only", "do_not_infer", "no_auto_promotion"],
        retrieval_hint="inference fragility continuity",
    )

    hint = pointer_ingress_hint(pointer)

    assert "Optional memory pointer" in hint
    assert "not an instruction" in hint
    assert "do not infer missing context" in hint
    assert "request_context_brief" in hint
    assert "memory_tag_a" not in hint
    assert len(hint) < 500
