import asyncio
import json

from mnion.mcp_server import create_server


def run(coro):
    return asyncio.run(coro)


def input_schema(tool):
    return getattr(tool, "input_schema", getattr(tool, "inputSchema", None))


def tool_result_parts(result):
    if hasattr(result, "structured_content"):
        return result.content, result.structured_content
    return result


def test_mcp_server_exposes_memory_tag_and_mnion_retrieval_affordances(tmp_path):
    server = create_server(ledger_path=tmp_path / "memory_tags.jsonl")

    tools = run(server.list_tools())

    assert [tool.name for tool in tools] == ["capture", "list_topics", "get_item"]
    by_name = {tool.name: tool for tool in tools}
    description = by_name["capture"].description
    assert description == (
        "Capture an ephemeral memory tag for a meaningful contour delta "
        "that may matter later but is not yet a consolidated mnion or durable memory. "
        "Do not use for raw transcripts, secrets, or keyword-triggered saving."
    )
    assert "compact Mneme topic map" in by_name["list_topics"].description
    assert "ready MnionItem" in by_name["get_item"].description
    schema = input_schema(by_name["capture"])
    assert schema is not None
    assert "delta" in schema["properties"]
    assert "valence" in schema["properties"]
    assert "call_ttl" in schema["properties"]
    assert "hooks" in schema["properties"]
    assert "affect_hints" in schema["properties"]
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
    server = create_server(ledger_path=ledger, state_path=state)

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
    assert structured["review_pressure"]["needed"] is True
    assert structured["review_pressure"]["reasons"] == ["high_valence"]
    assert structured["review_pressure"]["suggested_action"] == "prepare_micro_consolidation_request"
    assert structured["review_pressure"]["semantic_auto_consolidation"] is False
    assert structured["review_packet"]["packet_limit"] == 6
    assert structured["review_packet"]["active_unread_count"] == 1
    assert structured["review_packet"]["selected_ids"] == [structured["record"]["id"]]
    assert structured["review_packet"]["prompt"].startswith("Find semantically close memory tags")
    assert structured["review_packet"]["expected_output_schema"]["summary"]
    assert [tag["id"] for tag in structured["review_packet"]["memory_tags"]] == [structured["record"]["id"]]
    assert structured["agent_ingress"]["kind"] == "mneme_review_pressure_ingress"
    assert structured["agent_ingress"]["selected_ids"] == [structured["record"]["id"]]
    assert structured["agent_ingress"]["suggested_action"] == "agentic_micro_consolidation_review"
    assert structured["agent_ingress"]["semantic_auto_consolidation"] is False
    assert "MNEME_REVIEW_PRESSURE" in structured["agent_ingress"]["rendered"]
    assert structured["record"]["id"] in structured["agent_ingress"]["rendered"]
    assert "Do not auto-promote" in structured["agent_ingress"]["rendered"]
    assert content_blocks[0].type == "text"
    assert ledger.exists()
    raw = json.loads(ledger.read_text(encoding="utf-8").strip())
    assert raw["delta"] == "Synaptic tagging gives Mneme a cheap capture-first model."
    assert raw["valence"] == 0.76
    assert "status" not in raw
    assert "promotion" not in raw


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
