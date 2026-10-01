import asyncio
import json

from mnion.mcp_server import create_server
from mnion.micro_consolidation import load_micro_consolidation_review_receipts, prepare_micro_consolidation_request


def run(coro):
    return asyncio.run(coro)


def input_schema(tool):
    return getattr(tool, "input_schema", getattr(tool, "inputSchema", None))


def tool_result_parts(result):
    if hasattr(result, "structured_content"):
        return result.content, result.structured_content
    return result


def _interval_config(tmp_path, *, call_seq_interval=2, packet_limit=2):
    config = tmp_path / "mneme_config.toml"
    config.write_text(
        f"""
[review_pressure]
enabled = true
call_seq_interval = {call_seq_interval}
trigger_on_high_valence = true
trigger_on_interval = true
packet_limit = {packet_limit}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return config


def _create_interval_pending_review(server):
    high_result = run(server.call_tool("capture", {
        "delta": "High-valence pinned trace should wait for batch review instead of becoming a singleton mnion.",
        "valence": 0.93,
        "hooks": ["project:mneme", "batch:first"],
        "trigger": "pinned_before_batch",
    }))
    _, high = tool_result_parts(high_result)
    assert high["ok"] is True
    assert high["review_pressure"]["needed"] is False

    interval_result = run(server.call_tool("capture", {
        "delta": "Interval pressure should turn accumulated distinct tags into one review packet.",
        "valence": 0.22,
        "hooks": ["project:mneme", "batch:second"],
        "trigger": "interval_batch_ready",
    }))
    _, interval = tool_result_parts(interval_result)
    assert interval["ok"] is True
    assert interval["review_pressure"]["needed"] is True
    assert interval["review_pressure"]["reasons"] == ["call_seq_interval"]
    assert len(interval["review_packet"]["selected_ids"]) == 2
    assert interval["review_packet"]["selected_ids"][0] == high["target_id"]
    return interval


def test_mcp_server_exposes_memory_tag_and_mnion_retrieval_affordances(tmp_path):
    server = create_server(ledger_path=tmp_path / "memory_tags.jsonl")

    tools = run(server.list_tools())

    assert [tool.name for tool in tools] == ["capture", "consolidate_review", "list_topics", "get_item"]
    by_name = {tool.name: tool for tool in tools}
    description = by_name["capture"].description
    assert description == (
        "Capture an ephemeral memory tag for a meaningful contour delta "
        "that may matter later but is not yet a consolidated mnion or durable memory. "
        "Do not use for raw transcripts, secrets, or keyword-triggered saving."
    )
    assert "Close the current pending Mneme review" in by_name["consolidate_review"].description
    assert "compact Mneme topic map" in by_name["list_topics"].description
    assert "ready MnionItem" in by_name["get_item"].description
    schema = input_schema(by_name["capture"])
    assert schema is not None
    assert "delta" in schema["properties"]
    assert "valence" in schema["properties"]
    assert "call_ttl" in schema["properties"]
    assert "hooks" in schema["properties"]
    assert "affect_hints" in schema["properties"]
    consolidate_schema = input_schema(by_name["consolidate_review"])
    assert consolidate_schema is not None
    assert "selected_ids" in consolidate_schema["properties"]
    assert "summary" in consolidate_schema["properties"]
    assert "valence" in consolidate_schema["properties"]
    assert "member_ids" in consolidate_schema["properties"]
    assert "rationale" in consolidate_schema["properties"]
    forbidden = json.dumps(schema).lower()
    assert "kind" not in forbidden
    assert "status" not in forbidden
    assert "source_ref" not in forbidden
    assert "evidence" not in forbidden
    assert "promotion" not in forbidden
    assert "graph" not in forbidden
    assert "embedding" not in forbidden


def test_mcp_capture_tool_appends_simplified_memory_tag(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    server = create_server(ledger_path=ledger, state_path=state, config_path=_interval_config(tmp_path, call_seq_interval=10, packet_limit=6))

    result = run(server.call_tool("capture", {
        "delta": "Synaptic tagging gives Mneme a cheap capture-first model.",
        "valence": 0.76,
        "ttl_seconds": 3600,
        "call_ttl": 5,
        "hooks": ["telegram:current_turn"],
        "trigger": "theory_import",
        "affect_hints": ["curiosity", "contour_shift"],
    }))

    content_blocks, structured = tool_result_parts(result)
    assert structured["ok"] is True
    assert structured["action"] == "created"
    assert structured["target_id"] == structured["record"]["id"]
    assert structured["record"]["id"].startswith("memory_tag_")
    assert structured["record"]["delta"] == "Synaptic tagging gives Mneme a cheap capture-first model."
    assert structured["record"]["valence"] == 0.76
    assert structured["record"]["birth_call_seq"] == 1
    assert structured["record"]["call_ttl"] == 5
    assert structured["mneme_call_seq"] == 1
    assert structured["mneme_call_age"] == 0
    assert structured["record"]["hooks"] == ["telegram:current_turn"]
    assert structured["record"]["affect_hints"] == ["curiosity", "contour_shift"]
    assert structured["valence_crosses_threshold"] is True
    assert structured["review_pressure"]["needed"] is False
    assert structured["review_pressure"]["reasons"] == ["high_valence_pinned", "insufficient_review_batch"]
    assert structured["review_pressure"]["suggested_action"] is None
    assert structured["review_pressure"]["semantic_auto_consolidation"] is False
    assert structured["review_packet"]["packet_limit"] == 6
    assert structured["review_packet"]["active_unread_count"] == 1
    assert structured["review_packet"]["selected_ids"] == [structured["record"]["id"]]
    assert structured["review_packet"]["prompt"] is None
    assert structured["review_packet"]["expected_output_schema"] == {}
    assert structured["review_packet"]["memory_tags"] == []
    assert structured["agent_ingress"] is None
    assert content_blocks[0].type == "text"
    assert ledger.exists()
    raw = json.loads(ledger.read_text(encoding="utf-8").strip())
    assert raw["delta"] == "Synaptic tagging gives Mneme a cheap capture-first model."
    assert raw["valence"] == 0.76
    assert "status" not in raw
    assert "promotion" not in raw


def test_mcp_capture_persists_pending_review_and_redirects_until_reviewed(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    read_model = tmp_path / "mneme.sqlite3"
    pending = tmp_path / "pending_review.json"
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        read_model_path=read_model,
        pending_review_path=pending,
        config_path=_interval_config(tmp_path),
    )

    interval = _create_interval_pending_review(server)
    selected_ids = interval["review_packet"]["selected_ids"]
    assert pending.exists()
    pending_payload = json.loads(pending.read_text(encoding="utf-8"))
    assert pending_payload["kind"] == "mneme_pending_review"
    assert pending_payload["status"] == "pending"
    assert pending_payload["selected_ids"] == selected_ids
    assert pending_payload["reasons"] == ["call_seq_interval"]
    assert pending_payload["packet_limit"] == 2
    assert pending_payload["semantic_auto_consolidation"] is False
    assert "MNEME_REVIEW_PRESSURE" in pending_payload["agent_ingress"]["rendered"]

    ledger_before = ledger.read_text(encoding="utf-8")
    state_before = json.loads(state.read_text(encoding="utf-8"))["seq"]

    redirected_result = run(server.call_tool("capture", {
        "delta": "Ordinary low-valence capture should be redirected while review is pending.",
        "valence": 0.2,
        "hooks": ["project:mneme"],
        "trigger": "barrier_test",
    }))
    _, redirected = tool_result_parts(redirected_result)

    assert redirected["ok"] is False
    assert redirected["action"] == "redirected_to_pending_review"
    assert redirected["target_id"] is None
    assert redirected["memory_tag"] is None
    assert redirected["record"] is None
    assert redirected["review_pressure"]["needed"] is True
    assert redirected["agent_ingress"]["kind"] == "mneme_review_pressure_ingress"
    assert "MNEME_REVIEW_PRESSURE" in redirected["agent_ingress"]["rendered"]
    assert redirected["review_packet"]["selected_ids"] == selected_ids
    assert redirected["proposed_capture"]["delta"] == "Ordinary low-valence capture should be redirected while review is pending."
    assert "receipt_json" not in json.dumps(redirected)
    assert "sql" not in json.dumps(redirected).lower()
    assert ledger.read_text(encoding="utf-8") == ledger_before
    assert json.loads(state.read_text(encoding="utf-8"))["seq"] == state_before

    receipt = {
        "id": "review_pending",
        "kind": "micro_consolidation_review",
        "status": "reviewed",
        "created_at": "2026-09-28T18:40:00Z",
        "selected_ids": selected_ids,
        "grouped_ids": selected_ids,
        "ungrouped_ids": [],
        "deferred_ids": [],
        "mnion": {"summary": "Pending review barrier works.", "valence": 0.8, "rationale": "Test receipt."},
    }
    receipts.write_text(json.dumps(receipt) + "\n", encoding="utf-8")

    third_result = run(server.call_tool("capture", {
        "delta": "Capture after covered pending review should proceed.",
        "valence": 0.2,
        "hooks": ["project:mneme"],
        "trigger": "barrier_cleared",
    }))
    _, third = tool_result_parts(third_result)

    assert third["ok"] is True
    assert third["action"] in {"created", "linked_new", "reinforced"}
    assert not pending.exists()



def test_mcp_consolidate_review_records_receipt_clears_barrier_and_materializes_item(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    pending = tmp_path / "pending_review.json"
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        read_model_path=db,
        pending_review_path=pending,
        config_path=_interval_config(tmp_path),
    )

    first = _create_interval_pending_review(server)
    selected_ids = first["review_packet"]["selected_ids"]

    assert first["agent_ingress"]["next_tool"] == "consolidate_review"
    assert first["review_packet"]["next_tool"] == "consolidate_review"
    assert pending.exists()

    redirect_result = run(server.call_tool("capture", {
        "delta": "This capture should be held until the pending review is consolidated.",
        "valence": 0.21,
        "hooks": ["project:mneme"],
        "trigger": "pending_barrier_guidance",
    }))
    _, redirect = tool_result_parts(redirect_result)
    assert redirect["ok"] is False
    assert redirect["action"] == "redirected_to_pending_review"
    assert redirect["next_tool"] == "consolidate_review"
    assert redirect["tool_guidance"]["tool"] == "consolidate_review"
    assert redirect["tool_guidance"]["required_fields"] == ["selected_ids", "summary", "valence", "member_ids"]
    assert redirect["tool_guidance"]["selected_ids"] == selected_ids
    assert "consolidate_review" in redirect["agent_ingress"]["rendered"]

    consolidate_result = run(server.call_tool("consolidate_review", {
        "selected_ids": selected_ids,
        "summary": "Mneme write-barrier must expose a closure tool so external agents can finish pending reviews.",
        "valence": 0.88,
        "member_ids": selected_ids,
        "rationale": "The barrier pointed to consolidate_review and the agent supplied the semantic mnion.",
    }))
    _, consolidated = tool_result_parts(consolidate_result)

    assert consolidated["ok"] is True
    assert consolidated["action"] == "micro_consolidation_review_recorded"
    assert consolidated["cleared_pending_review"] is True
    assert consolidated["review_id"].startswith("review_")
    assert consolidated["selected_ids"] == selected_ids
    assert consolidated["grouped_ids"] == selected_ids
    assert consolidated["route"] == "list_topics -> get_item(review_id)"
    assert consolidated["item"]["review_id"] == consolidated["review_id"]
    assert consolidated["item"]["mnion"]["summary"].startswith("Mneme write-barrier")
    assert not pending.exists()

    receipt = json.loads(receipts.read_text(encoding="utf-8").strip())
    assert receipt["id"] == consolidated["review_id"]
    assert receipt["kind"] == "micro_consolidation_review"
    assert receipt["selected_ids"] == selected_ids
    assert receipt["grouped_ids"] == selected_ids
    assert receipt["mnion"]["valence"] == 0.88

    item_result = run(server.call_tool("get_item", {"review_id": consolidated["review_id"]}))
    _, item = tool_result_parts(item_result)
    assert item["ok"] is True
    assert item["item"]["review_id"] == consolidated["review_id"]

    next_capture_result = run(server.call_tool("capture", {
        "delta": "Capture after MCP consolidate_review should proceed.",
        "valence": 0.22,
        "hooks": ["project:mneme"],
        "trigger": "barrier_closed_by_tool",
    }))
    _, next_capture = tool_result_parts(next_capture_result)
    assert next_capture["ok"] is True
    assert next_capture["action"] in {"created", "linked_new", "reinforced"}
    assert next_capture["record"]["delta"] == "Capture after MCP consolidate_review should proceed."


def test_mcp_consolidate_review_with_subset_members_clears_latch_but_keeps_ungrouped_unread(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    pending = tmp_path / "pending_review.json"
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        read_model_path=db,
        pending_review_path=pending,
        config_path=_interval_config(tmp_path),
    )

    first = _create_interval_pending_review(server)
    selected_ids = first["review_packet"]["selected_ids"]
    grouped_ids = selected_ids[:1]
    ungrouped_ids = selected_ids[1:]
    assert pending.exists()

    consolidate_result = run(server.call_tool("consolidate_review", {
        "selected_ids": selected_ids,
        "summary": "Only the first selected memory tag belongs in this mnion.",
        "valence": 0.72,
        "member_ids": grouped_ids,
        "rationale": "The remaining selected tag was reviewed but did not belong in this semantic object.",
    }))
    _, consolidated = tool_result_parts(consolidate_result)

    assert consolidated["ok"] is True
    assert consolidated["cleared_pending_review"] is True
    assert consolidated["grouped_ids"] == grouped_ids
    assert consolidated["ungrouped_ids"] == ungrouped_ids
    assert not pending.exists()

    stored = load_micro_consolidation_review_receipts(receipts)
    next_request = prepare_micro_consolidation_request(
        ledger_path=ledger,
        state_path=state,
        packet_limit=10,
        review_receipts=stored,
    )

    assert next_request.selection.selected_ids == ungrouped_ids
    assert next_request.selection.reviewed_active_count == len(grouped_ids)
    assert next_request.selection.unread_active_count == len(ungrouped_ids)



def test_mcp_consolidate_review_rejects_selected_id_mismatch_fail_closed(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    pending = tmp_path / "pending_review.json"
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        pending_review_path=pending,
        config_path=_interval_config(tmp_path),
    )

    first = _create_interval_pending_review(server)
    selected_ids = first["review_packet"]["selected_ids"]
    assert pending.exists()

    mismatch_result = run(server.call_tool("consolidate_review", {
        "selected_ids": ["memory_tag_wrong"],
        "summary": "This should not be recorded.",
        "valence": 0.75,
        "member_ids": ["memory_tag_wrong"],
        "rationale": "Wrong selected ids must fail closed.",
    }))
    _, mismatch = tool_result_parts(mismatch_result)

    assert mismatch["ok"] is False
    assert mismatch["action"] == "selected_ids_mismatch"
    assert mismatch["expected_selected_ids"] == selected_ids
    assert mismatch["cleared_pending_review"] is False
    assert pending.exists()
    assert not receipts.exists()

    redirected_result = run(server.call_tool("capture", {
        "delta": "Capture should still be blocked after failed mismatched closure.",
        "valence": 0.2,
        "hooks": ["project:mneme"],
        "trigger": "still_blocked_after_mismatch",
    }))
    _, redirected = tool_result_parts(redirected_result)
    assert redirected["ok"] is False
    assert redirected["action"] == "redirected_to_pending_review"
    assert redirected["tool_guidance"]["selected_ids"] == selected_ids



def test_mcp_consolidate_review_rejects_non_string_pending_ids_fail_closed(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    pending = tmp_path / "pending_review.json"
    pending.write_text(json.dumps({
        "kind": "mneme_pending_review",
        "status": "pending",
        "selected_ids": [123],
        "semantic_auto_consolidation": False,
        "review_pressure": {"needed": True, "reasons": ["high_valence"]},
        "agent_ingress": {
            "rendered": "MNEME_REVIEW_PRESSURE malformed numeric ids",
            "selected_ids": [123],
        },
        "review_packet": {
            "packet_limit": 6,
            "selected_ids": [123],
            "memory_tags": [{
                "id": 123,
                "delta": "Numeric ids must not be normalized into strings.",
                "valence": 0.9,
                "ttl_seconds": 3600,
                "call_ttl": 5,
                "birth_call_seq": 1,
                "captured_at": "2026-09-30T20:00:00Z",
                "expires_at": "2026-09-30T21:00:00Z",
                "hooks": [],
                "trigger": None,
                "affect_hints": [],
            }],
            "prompt": "review",
            "expected_output_schema": {},
        },
    }) + "\n", encoding="utf-8")
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        pending_review_path=pending,
    )

    result = run(server.call_tool("consolidate_review", {
        "selected_ids": ["123"],
        "summary": "This must not repair numeric ids.",
        "valence": 0.7,
        "member_ids": ["123"],
    }))
    _, structured = tool_result_parts(result)

    assert structured["ok"] is False
    assert structured["action"] == "blocked_by_invalid_pending_review"
    assert "selected_ids" in structured["errors"]
    assert "review_packet.selected_ids" in structured["errors"]
    assert "agent_ingress.selected_ids" in structured["errors"]
    assert structured["cleared_pending_review"] is False
    assert pending.exists()
    assert not receipts.exists()



def test_mcp_consolidate_review_rejects_whitespace_padded_pending_ids_fail_closed(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    pending = tmp_path / "pending_review.json"
    pending.write_text(json.dumps({
        "kind": "mneme_pending_review",
        "status": "pending",
        "selected_ids": [" memory_tag_bad "],
        "semantic_auto_consolidation": False,
        "review_pressure": {"needed": True, "reasons": ["high_valence"]},
        "agent_ingress": {
            "rendered": "MNEME_REVIEW_PRESSURE whitespace padded ids",
            "selected_ids": [" memory_tag_bad "],
        },
        "review_packet": {
            "packet_limit": 6,
            "selected_ids": [" memory_tag_bad "],
            "memory_tags": [{
                "id": " memory_tag_bad ",
                "delta": "Whitespace-padded ids must not be repaired.",
                "valence": 0.9,
                "ttl_seconds": 3600,
                "call_ttl": 5,
                "birth_call_seq": 1,
                "captured_at": "2026-09-30T20:00:00Z",
                "expires_at": "2026-09-30T21:00:00Z",
                "hooks": [],
                "trigger": None,
                "affect_hints": [],
            }],
            "prompt": "review",
            "expected_output_schema": {},
        },
    }) + "\n", encoding="utf-8")
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        pending_review_path=pending,
    )

    result = run(server.call_tool("consolidate_review", {
        "selected_ids": ["memory_tag_bad"],
        "summary": "This must not repair padded ids.",
        "valence": 0.7,
        "member_ids": ["memory_tag_bad"],
    }))
    _, structured = tool_result_parts(result)

    assert structured["ok"] is False
    assert structured["action"] == "blocked_by_invalid_pending_review"
    assert "selected_ids" in structured["errors"]
    assert "review_packet.selected_ids" in structured["errors"]
    assert "agent_ingress.selected_ids" in structured["errors"]
    assert structured["cleared_pending_review"] is False
    assert pending.exists()
    assert not receipts.exists()



def test_mcp_consolidate_review_returns_structured_error_for_malformed_memory_tag_packet(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    pending = tmp_path / "pending_review.json"
    pending.write_text(json.dumps({
        "kind": "mneme_pending_review",
        "status": "pending",
        "selected_ids": ["memory_tag_bad"],
        "semantic_auto_consolidation": False,
        "review_pressure": {"needed": True, "reasons": ["high_valence"]},
        "agent_ingress": {
            "rendered": "MNEME_REVIEW_PRESSURE malformed packet",
            "selected_ids": ["memory_tag_bad"],
        },
        "review_packet": {
            "packet_limit": 6,
            "selected_ids": ["memory_tag_bad"],
            "memory_tags": [{
                "id": "memory_tag_bad",
                "delta": "Missing fields should produce structured fail-closed response.",
                "valence": 0.9,
            }],
            "prompt": "review",
            "expected_output_schema": {},
        },
    }) + "\n", encoding="utf-8")
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        pending_review_path=pending,
    )

    result = run(server.call_tool("consolidate_review", {
        "selected_ids": ["memory_tag_bad"],
        "summary": "This malformed packet must not raise through MCP.",
        "valence": 0.7,
        "member_ids": ["memory_tag_bad"],
    }))
    _, structured = tool_result_parts(result)

    assert structured["ok"] is False
    assert structured["action"] == "blocked_by_invalid_pending_review"
    assert "ttl_seconds" in structured["reason"]
    assert structured["cleared_pending_review"] is False
    assert pending.exists()
    assert not receipts.exists()



def test_mcp_consolidate_review_returns_structured_error_for_malformed_packet_metadata(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    pending = tmp_path / "pending_review.json"
    pending.write_text(json.dumps({
        "kind": "mneme_pending_review",
        "status": "pending",
        "selected_ids": ["memory_tag_bad_meta"],
        "semantic_auto_consolidation": False,
        "review_pressure": {"needed": True, "reasons": ["high_valence"]},
        "agent_ingress": {
            "rendered": "MNEME_REVIEW_PRESSURE malformed packet metadata",
            "selected_ids": ["memory_tag_bad_meta"],
        },
        "review_packet": {
            "packet_limit": [6],
            "selected_ids": ["memory_tag_bad_meta"],
            "memory_tags": [{
                "id": "memory_tag_bad_meta",
                "delta": "Malformed packet metadata should not escape MCP structured response.",
                "valence": 0.9,
                "ttl_seconds": 3600,
                "call_ttl": 5,
                "birth_call_seq": 1,
                "captured_at": "2026-09-30T20:00:00Z",
                "expires_at": "2026-09-30T21:00:00Z",
                "hooks": [],
                "trigger": None,
                "affect_hints": [],
            }],
            "prompt": "review",
            "expected_output_schema": 7,
            "active_unread_count": [1],
        },
    }) + "\n", encoding="utf-8")
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        pending_review_path=pending,
    )

    result = run(server.call_tool("consolidate_review", {
        "selected_ids": ["memory_tag_bad_meta"],
        "summary": "Malformed metadata must not raise through MCP.",
        "valence": 0.7,
        "member_ids": ["memory_tag_bad_meta"],
    }))
    _, structured = tool_result_parts(result)

    assert structured["ok"] is False
    assert structured["action"] == "blocked_by_invalid_pending_review"
    assert "expected_output_schema" in structured["reason"] or "packet_limit" in structured["reason"]
    assert structured["cleared_pending_review"] is False
    assert pending.exists()
    assert not receipts.exists()



def test_mcp_consolidate_review_keeps_latch_when_read_model_materialization_fails(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    read_model_dir = tmp_path / "read_model_directory"
    read_model_dir.mkdir()
    pending = tmp_path / "pending_review.json"
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        read_model_path=read_model_dir,
        pending_review_path=pending,
        config_path=_interval_config(tmp_path),
    )

    first = _create_interval_pending_review(server)
    selected_ids = first["review_packet"]["selected_ids"]

    result = run(server.call_tool("consolidate_review", {
        "selected_ids": selected_ids,
        "summary": "Receipt write should be reported separately from read-model failure.",
        "valence": 0.8,
        "member_ids": selected_ids,
    }))
    _, structured = tool_result_parts(result)

    assert structured["ok"] is False
    assert structured["action"] == "review_recorded_read_model_failed"
    assert structured["review_id"].startswith("review_")
    assert structured["cleared_pending_review"] is False
    assert pending.exists()
    assert receipts.exists()

    blocked_result = run(server.call_tool("capture", {
        "delta": "Capture must remain blocked until the receipt-backed item is readable.",
        "valence": 0.2,
        "hooks": ["project:mneme"],
        "trigger": "after_read_model_failure",
    }))
    _, blocked = tool_result_parts(blocked_result)
    assert blocked["ok"] is False
    assert blocked["action"] == "redirected_to_pending_review"
    assert blocked["next_tool"] == "consolidate_review"
    assert pending.exists()



def test_mcp_capture_blocks_malformed_pending_review_fail_closed(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    pending = tmp_path / "pending_review.json"
    pending.write_text(json.dumps({
        "kind": "mneme_pending_review",
        "status": "pending",
        "selected_ids": [],
        "agent_ingress": {"rendered": "MNEME_REVIEW_PRESSURE malformed"},
        "review_packet": {},
    }) + "\n", encoding="utf-8")
    state.write_text(json.dumps({"seq": 7}) + "\n", encoding="utf-8")
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        pending_review_path=pending,
    )

    result = run(server.call_tool("capture", {
        "delta": "Capture must not bypass a malformed pending review latch.",
        "valence": 0.2,
        "hooks": ["project:mneme"],
        "trigger": "malformed_latch_test",
    }))
    _, structured = tool_result_parts(result)

    assert structured["ok"] is False
    assert structured["action"] == "blocked_by_invalid_pending_review"
    assert structured["target_id"] is None
    assert structured["record"] is None
    assert structured["pending_review"]["valid"] is False
    assert "selected_ids" in structured["pending_review"]["errors"]
    assert structured["proposed_capture"]["delta"] == "Capture must not bypass a malformed pending review latch."
    assert not ledger.exists()
    assert json.loads(state.read_text(encoding="utf-8"))["seq"] == 7
    assert pending.exists()



def test_mcp_capture_blocks_mismatched_pending_review_selected_ids(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    pending = tmp_path / "pending_review.json"
    pending.write_text(json.dumps({
        "kind": "mneme_pending_review",
        "status": "pending",
        "selected_ids": ["memory_tag_top"],
        "semantic_auto_consolidation": False,
        "review_pressure": {"needed": True, "reasons": ["high_valence"]},
        "agent_ingress": {
            "rendered": "MNEME_REVIEW_PRESSURE malformed mismatch",
            "selected_ids": ["memory_tag_ingress"],
        },
        "review_packet": {
            "selected_ids": ["memory_tag_packet"],
            "memory_tags": [],
        },
    }) + "\n", encoding="utf-8")
    receipts.write_text(json.dumps({
        "id": "review_top_only",
        "kind": "micro_consolidation_review",
        "status": "reviewed",
        "selected_ids": ["memory_tag_top"],
        "grouped_ids": ["memory_tag_top"],
        "ungrouped_ids": [],
        "deferred_ids": [],
        "mnion": {"summary": "Top id only.", "valence": 0.7},
    }) + "\n", encoding="utf-8")
    state.write_text(json.dumps({"seq": 9}) + "\n", encoding="utf-8")
    server = create_server(
        ledger_path=ledger,
        state_path=state,
        receipts_path=receipts,
        pending_review_path=pending,
    )

    result = run(server.call_tool("capture", {
        "delta": "Mismatched pending selected ids must fail closed.",
        "valence": 0.2,
        "hooks": ["project:mneme"],
        "trigger": "mismatch_latch_test",
    }))
    _, structured = tool_result_parts(result)

    assert structured["ok"] is False
    assert structured["action"] == "blocked_by_invalid_pending_review"
    assert "review_packet.selected_ids_mismatch" in structured["pending_review"]["errors"]
    assert "agent_ingress.selected_ids_mismatch" in structured["pending_review"]["errors"]
    assert not ledger.exists()
    assert json.loads(state.read_text(encoding="utf-8"))["seq"] == 9
    assert pending.exists()



def test_mcp_get_item_and_list_topics_expose_mnions_without_sql_or_receipts(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    receipt = {
        "id": "review_trace",
        "kind": "micro_consolidation_review",
        "status": "reviewed",
        "created_at": "2026-09-24T12:00:00Z",
        "grouped_ids": ["memory_tag_a"],
        "selected_ids": ["memory_tag_a"],
        "ungrouped_ids": [],
        "mnion": {
            "summary": "Nira continuity is trace-governed and first-person.",
            "valence": 0.93,
            "rationale": "Continuity decisions should be route-addressable without bulk context.",
        },
    }
    receipts.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    server = create_server(
        ledger_path=tmp_path / "memory_tags.jsonl",
        receipts_path=receipts,
        read_model_path=db,
    )

    topics_result = run(server.call_tool("list_topics", {"limit": 5}))
    _, topics = tool_result_parts(topics_result)

    assert topics["ok"] is True
    assert topics["materialized_count"] == 1
    assert topics["topics"][0]["label"] == "Nira continuity / trace-governed identity"
    assert topics["topics"][0]["top_review_ids"] == ["review_trace"]
    assert topics["active_ingress"]["kind"] == "mneme_active_mnion_ingress"
    assert topics["active_ingress"]["items"][0]["review_id"] == "review_trace"
    assert "MNEME_ACTIVE_MNION_INGRESS" in topics["active_ingress"]["rendered"]
    assert "Nira continuity is trace-governed" in topics["active_ingress"]["rendered"]
    assert "receipt_json" not in topics["active_ingress"]["rendered"]
    assert topics["do_not_infer"] == [
        "This is a compact topic map, not loaded memory content.",
        "Use get_item(review_id) for one selected mnion; do not bulk-load Mneme.",
        "Absence from this map is not proof that Mneme has no relevant memory.",
    ]
    assert "receipt_json" not in json.dumps(topics)

    item_result = run(server.call_tool("get_item", {"review_id": "review_trace"}))
    _, item = tool_result_parts(item_result)

    assert item["ok"] is True
    assert item["item"]["review_id"] == "review_trace"
    assert item["item"]["mnion"] == receipt["mnion"]
    assert item["item"]["grouped_ids"] == ["memory_tag_a"]
    assert item["item"]["guards"] == ["do_not_infer", "no_auto_promotion", "receipt_backed"]
    assert "receipt" not in item["item"]

    missing_result = run(server.call_tool("get_item", {"review_id": "missing"}))
    _, missing = tool_result_parts(missing_result)
    assert missing == {
        "ok": False,
        "review_id": "missing",
        "error": "mnion item not found",
        "do_not_infer": ["A miss is not proof that the memory never existed; the read-model may need materialization or a different route."],
    }
