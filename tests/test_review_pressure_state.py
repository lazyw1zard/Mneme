from mnion.review_pressure_state import pending_review_is_resolved


def _pending(selected_ids: list[str]) -> dict:
    return {
        "kind": "mneme_pending_review",
        "status": "pending",
        "selected_ids": selected_ids,
        "semantic_auto_consolidation": False,
        "agent_ingress": {"rendered": "MNEME_REVIEW_PRESSURE", "selected_ids": selected_ids},
        "review_packet": {"selected_ids": selected_ids},
    }


def test_pending_review_resolution_treats_ungrouped_ids_as_receipt_coverage_not_queue_review():
    pending = _pending(["memory_tag_a", "memory_tag_b", "memory_tag_c"])
    receipts = [
        {
            "id": "review_1",
            "grouped_ids": ["memory_tag_a"],
            "ungrouped_ids": ["memory_tag_b"],
            "deferred_ids": ["memory_tag_c"],
        }
    ]

    assert pending_review_is_resolved(pending, receipts) is True


def test_pending_review_resolution_requires_every_selected_id_to_be_covered():
    pending = _pending(["memory_tag_a", "memory_tag_b"])
    receipts = [
        {
            "id": "review_1",
            "grouped_ids": ["memory_tag_a"],
            "ungrouped_ids": [],
            "deferred_ids": [],
        }
    ]

    assert pending_review_is_resolved(pending, receipts) is False


def test_pending_review_resolution_counts_explicit_noise_separately_from_queue_state():
    pending = _pending(["memory_tag_a", "memory_tag_noise", "memory_tag_later"])
    receipt = {
        "id": "review_1",
        "grouped_ids": ["memory_tag_a"],
        "reviewed_noise_ids": ["memory_tag_noise"],
        "deferred_ids": ["memory_tag_later"],
        "ungrouped_ids": [],
    }

    assert pending_review_is_resolved(pending, [receipt]) is True
