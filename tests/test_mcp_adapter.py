import asyncio
import json

from mnion.mcp_server import create_server


def run(coro):
    return asyncio.run(coro)


def test_mcp_server_exposes_single_capture_affordance(tmp_path):
    server = create_server(ledger_path=tmp_path / "mnions.jsonl")

    tools = run(server.list_tools())

    assert [tool.name for tool in tools] == ["mnion_capture"]
    description = tools[0].description.lower()
    assert "delta" in description
    assert "valence" in description
    assert "affect" in description
    assert "ttl" in description
    assert "decay" in description
    schema = tools[0].inputSchema
    assert "delta" in schema["properties"]
    assert "valence" in schema["properties"]
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


def test_mcp_capture_tool_appends_simplified_mnion(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    server = create_server(ledger_path=ledger)

    result = run(server.call_tool("mnion_capture", {
        "delta": "Synaptic tagging gives Mneme a cheap capture-first model.",
        "valence": 0.76,
        "ttl_seconds": 3600,
        "hooks": ["telegram:current_turn"],
        "trigger": "theory_import",
        "affect_hints": ["curiosity", "contour_shift"],
    }))

    content_blocks, structured = result

    assert structured["ok"] is True
    assert structured["record"]["id"].startswith("mnion_")
    assert structured["record"]["delta"] == "Synaptic tagging gives Mneme a cheap capture-first model."
    assert structured["record"]["valence"] == 0.76
    assert structured["record"]["hooks"] == ["telegram:current_turn"]
    assert structured["record"]["affect_hints"] == ["curiosity", "contour_shift"]
    assert structured["valence_crosses_threshold"] is True
    assert content_blocks[0].type == "text"
    assert ledger.exists()
    raw = json.loads(ledger.read_text(encoding="utf-8").strip())
    assert raw["delta"] == "Synaptic tagging gives Mneme a cheap capture-first model."
    assert raw["valence"] == 0.76
    assert "status" not in raw
    assert "promotion" not in raw
