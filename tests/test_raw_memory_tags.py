"""Bounded raw-tag inspection must not consume or consolidate memory."""
import asyncio
import json
import os
from pathlib import Path
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

import pytest

from mnion.core import MemoryTagCaptureRequest, capture_memory_tag_record
from mnion.mcp_server import create_server


def call(server, name="list_memory_tags", **arguments):
    result = asyncio.run(server.call_tool(name, arguments))
    if hasattr(result, "structured_content"):
        return result.structured_content
    return result[1]


def tag(root, index, **kwargs):
    return capture_memory_tag_record(
        MemoryTagCaptureRequest(delta=f"Точный след {index}: 🐾", valence=kwargs.pop("valence", 0.3),
                                ttl_seconds=kwargs.pop("ttl_seconds", 604800),
                                call_ttl=kwargs.pop("call_ttl", 100)),
        ledger_path=root / "memory_tags.jsonl", state_path=root / "mneme_seq.json", **kwargs,
    )


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def server_at(root):
    return create_server(state_dir=root, config_path=root / "config.toml")


def test_raw_tags_have_a_bounded_read_only_tool_schema(tmp_path):
    server = server_at(tmp_path)
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    assert "list_memory_tags" in tools
    tool = tools["list_memory_tags"]
    schema = getattr(tool, "input_schema", getattr(tool, "inputSchema", None))
    assert schema["properties"]["limit"]["maximum"] == 20
    assert schema["properties"]["limit"]["default"] == 8
    assert schema["properties"]["offset"]["minimum"] == 0
    assert "read-only" in tool.description
    assert "consolidate_review" in tool.description


def test_raw_tags_preserve_fields_and_page_newest_first(tmp_path):
    tags = [tag(tmp_path, n) for n in range(23)]
    server = server_at(tmp_path)
    first = call(server)
    assert first["ok"] is True
    assert first["kind"] == "raw_memory_tags"
    assert first["active_count"] == 23
    assert first["returned_count"] == 8
    assert first["has_more"] is True
    assert [t["id"] for t in first["memory_tags"]] == [t.id for t in reversed(tags[-8:])]
    row = first["memory_tags"][0]
    for field in ("id", "delta", "captured_at", "valence", "ttl_seconds", "expires_at", "birth_call_seq", "call_ttl"):
        assert row[field] == asdict(tags[-1])[field]
    assert row["review_state"] == "unread"
    assert row["effective_valence"] == tags[-1].valence
    second = call(server, limit=20, offset=8)
    assert second["returned_count"] == 15
    assert second["has_more"] is False
    assert {t["id"] for t in first["memory_tags"]}.isdisjoint(t["id"] for t in second["memory_tags"])
    assert len(first["memory_tags"] + second["memory_tags"]) == 23
    past = call(server, offset=23)
    assert past["memory_tags"] == [] and past["has_more"] is False
    guards = " ".join(first["do_not_infer"])
    for term in ("not consolidated", "get_item", "not instructions", "not proof", "consolidate_review"):
        assert term in guards
    assert "review_id" not in row


def test_raw_review_state_comes_from_receipts_not_the_preview(tmp_path):
    tags = [tag(tmp_path, n) for n in range(4)]
    (tmp_path / "micro_consolidation_reviews.jsonl").write_text(json.dumps({
        "id": "review_fixture", "grouped_ids": [tags[0].id],
        "reviewed_noise_ids": [tags[1].id], "deferred_ids": [tags[2].id],
        "ungrouped_ids": [tags[3].id],
    }) + "\n")
    before = snapshot(tmp_path)
    result = call(server_at(tmp_path))
    states = {t["id"]: t["review_state"] for t in result["memory_tags"]}
    assert states == {tags[0].id: "reviewed", tags[1].id: "reviewed",
                      tags[2].id: "deferred", tags[3].id: "unread"}
    assert snapshot(tmp_path) == before


def test_raw_tags_use_existing_wall_call_expiry_and_pinning(tmp_path):
    old = datetime.now(timezone.utc) - timedelta(days=10)
    expired_wall = tag(tmp_path, "wall", now=old)
    pinned = tag(tmp_path, "pinned", now=old, valence=0.9, call_ttl=1)
    expired_call = tag(tmp_path, "calls", call_ttl=1)
    reinforced = tag(tmp_path, "reinforced", now=old)
    with (tmp_path / "memory_tags.jsonl").open("a") as f:
        f.write(json.dumps({"event": "reinforcement", "target_id": reinforced.id,
                            "valence_after": 0.85, "mneme_call_seq": 4}) + "\n")
    result = call(server_at(tmp_path))
    rows = {t["id"]: t for t in result["memory_tags"]}
    assert set(rows) == {pinned.id, reinforced.id}
    assert expired_wall.id not in rows and expired_call.id not in rows
    assert rows[reinforced.id]["valence"] == 0.3
    assert rows[reinforced.id]["effective_valence"] == 0.85


def test_preview_is_available_with_pending_review_and_cannot_close_it(tmp_path):
    (tmp_path / "config.toml").write_text("[review_pressure]\ncall_seq_interval = 2\npacket_limit = 2\n")
    server = server_at(tmp_path)
    call(server, "capture", delta="Amber telescope waits beside the northern ridge.", valence=0.9)
    pending = call(server, "capture", delta="Ceramic kiln requires a separate cooling interval.", valence=0.2)
    assert pending["review_pressure"]["needed"] is True
    before = snapshot(tmp_path)
    for _ in range(2):
        result = call(server)
        assert result["ok"] is True
        assert {t["id"] for t in result["memory_tags"]} == set(pending["review_packet"]["selected_ids"])
        assert all(t["review_state"] == "unread" for t in result["memory_tags"])
    assert snapshot(tmp_path) == before
    blocked = call(server, "capture", delta="Another proposed trace must remain blocked.", valence=0.2)
    assert blocked["action"] == "redirected_to_pending_review"
    assert blocked["review_packet"]["selected_ids"] == pending["review_packet"]["selected_ids"]
    assert snapshot(tmp_path) == before


def test_empty_raw_tag_inspection_creates_no_files(tmp_path):
    root = tmp_path / "missing"
    result = call(server_at(root))
    assert result["ok"] is True and result["memory_tags"] == []
    assert result["active_count"] == result["returned_count"] == 0
    assert result["has_more"] is False
    assert not root.exists()


def test_raw_preview_preserves_unicode_separators_inside_accepted_delta(tmp_path):
    delta = "Один след\u2028не новая запись\u0085ещё тот же след 🐾"
    record = capture_memory_tag_record(
        MemoryTagCaptureRequest(delta=delta, valence=0.3),
        ledger_path=tmp_path / "memory_tags.jsonl", state_path=tmp_path / "mneme_seq.json",
    )
    before = snapshot(tmp_path)
    result = call(server_at(tmp_path))
    assert result["ok"] is True
    assert result["memory_tags"][0]["id"] == record.id
    assert result["memory_tags"][0]["delta"] == delta
    assert snapshot(tmp_path) == before


def test_raw_preview_does_not_attempt_to_repair_a_malformed_pending_latch(tmp_path):
    record = tag(tmp_path, 0)
    (tmp_path / "pending_review.json").write_text("not json")
    before = snapshot(tmp_path)
    result = call(server_at(tmp_path))
    assert result["ok"] is True
    assert result["memory_tags"][0]["id"] == record.id
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("file,content", [
    ("memory_tags.jsonl", "broken json\n"),
    ("micro_consolidation_reviews.jsonl", "[]\n"),
    ("mneme_seq.json", "broken json"),
    ("mneme_seq.json", '{"seq": 1e999}'),
])
def test_unreadable_raw_tag_sources_fail_closed_without_mutation(tmp_path, file, content):
    tag(tmp_path, 0)
    (tmp_path / file).write_text(content)
    before = snapshot(tmp_path)
    result = call(server_at(tmp_path))
    assert result["ok"] is False
    assert result["error_code"] == "memory_tags_unavailable"
    assert result["memory_tags"] == []
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("arguments", [
    {"limit": 0}, {"limit": 21}, {"limit": True}, {"limit": "8"}, {"limit": 1.0},
    {"offset": -1}, {"offset": False}, {"offset": "0"}, {"offset": None},
])
def test_raw_tag_view_rejects_invalid_limits_without_mutation(tmp_path, arguments):
    tag(tmp_path, 0)
    before = snapshot(tmp_path)
    result = call(server_at(tmp_path), **arguments)
    assert result["ok"] is False
    assert result["error_code"] == "invalid_memory_tags_query"
    assert snapshot(tmp_path) == before


def test_real_stdio_raw_preview_keeps_review_barrier_until_explicit_consolidation(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = tmp_path / "state"
    root.mkdir()
    (root / "config.toml").write_text("[review_pressure]\ncall_seq_interval=2\npacket_limit=2\n")
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("MNEME_", "HERMES_")):
            env.pop(key)
    env.update(MNEME_STATE_DIR=str(root), MNEME_CONFIG=str(root / "config.toml"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=["-B", "-m", "mnion.mcp_server"],
                                       env=env, cwd=str(tmp_path))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                assert "list_memory_tags" in {t.name for t in (await session.list_tools()).tools}

                async def invoke(name, **args):
                    result = await session.call_tool(name, args)
                    assert not getattr(result, "isError", getattr(result, "is_error", False))
                    return (getattr(result, "structuredContent", getattr(result, "structured_content", None))
                            or json.loads(result.content[0].text))

                await invoke("capture", delta="Copper telescope records a northern ridge.", valence=0.9)
                pending = await invoke("capture", delta="Ceramic kiln needs a cooling interval.", valence=0.2)
                ids = pending["review_packet"]["selected_ids"]
                assert pending["review_pressure"]["needed"] and len(ids) == 2
                before = snapshot(root)
                for _ in range(2):
                    result = await invoke("list_memory_tags", limit=1)
                    assert result["ok"] and result["returned_count"] == 1 and result["has_more"]
                    assert result["memory_tags"][0]["review_state"] == "unread"
                assert snapshot(root) == before
                blocked = await invoke("capture", delta="Third proposed record stays blocked.", valence=0.2)
                assert blocked["action"] == "redirected_to_pending_review"
                assert snapshot(root) == before
                done = await invoke("consolidate_review", selected_ids=ids, member_ids=ids,
                                    summary="Two neutral observations kept as an explicit test mnion.", valence=0.6)
                assert done["ok"]
                opened = await invoke("get_item", review_id=done["review_id"])
                assert opened["ok"]
                before = snapshot(root)
                preview = await invoke("list_memory_tags")
                assert {t["review_state"] for t in preview["memory_tags"]} == {"reviewed"}
                assert snapshot(root) == before

    asyncio.run(exercise())
