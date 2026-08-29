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
    assert "ephemeral" in description
    assert "affect" in description
    assert "decay" in description
    schema = tools[0].inputSchema
    assert "stub" in schema["properties"]
    assert "affect_hints" in schema["properties"]
    assert "graph" not in json.dumps(schema).lower()
    assert "embedding" not in json.dumps(schema).lower()


def test_mcp_capture_tool_appends_mnion(tmp_path):
    ledger = tmp_path / "mnions.jsonl"
    server = create_server(ledger_path=ledger)

    result = run(server.call_tool("mnion_capture", {
        "stub": "Synaptic tagging gives Mneme a cheap capture-first model.",
        "source_ref": "telegram:current_turn",
        "trigger": "theory_import",
        "affect_hints": ["curiosity", "contour_shift"],
        "evidence": ["тег живёт около часа"],
        "ttl_seconds": 3600,
    }))

    content_blocks, structured = result

    assert structured["ok"] is True
    assert structured["record"]["id"].startswith("mnion_")
    assert structured["record"]["status"] == "tag"
    assert structured["record"]["promotion"] is None
    assert content_blocks[0].type == "text"
    assert ledger.exists()
    raw = json.loads(ledger.read_text(encoding="utf-8").strip())
    assert raw["stub"] == "Synaptic tagging gives Mneme a cheap capture-first model."
    assert raw["affect_hints"] == ["curiosity", "contour_shift"]
