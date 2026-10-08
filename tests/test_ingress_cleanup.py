"""Retired ingress must not gate navigation or preload reviewed bodies."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

from mnion.mcp_server import create_server


def test_package_no_longer_exports_body_preload():
    import mnion

    assert not hasattr(mnion, "ActiveMnionIngress")
    assert not hasattr(mnion, "active_mnion_ingress_for_context")


def test_surface_import_does_not_load_retired_word_gate():
    result = subprocess.run(
        [sys.executable, "-c", "import sys; import mnion.active_surface; assert 'mnion.ingress' not in sys.modules"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    assert result.returncode == 0, result.stderr


def test_list_topics_returns_routes_not_bodies_and_get_item_still_opens_body(tmp_path):
    body = "Private lantern sentinel: an agent-selected understanding without familiar keywords."
    rationale = "Private rationale sentinel: selected by the reviewing agent."
    receipt = {
        "id": "review_cleanup",
        "kind": "micro_consolidation_review",
        "status": "reviewed",
        "created_at": "2026-10-08T00:00:00Z",
        "grouped_ids": ["tag_cleanup"],
        "selected_ids": ["tag_cleanup"],
        "ungrouped_ids": [],
        "mnion": {"summary": body, "valence": 0.8, "rationale": rationale},
    }
    (tmp_path / "micro_consolidation_reviews.jsonl").write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    server = create_server(
        ledger_path=tmp_path / "memory_tags.jsonl",
        state_path=tmp_path / "mneme_seq.json",
        receipts_path=tmp_path / "micro_consolidation_reviews.jsonl",
        read_model_path=tmp_path / "mneme.sqlite3",
        pending_review_path=tmp_path / "pending_review.json",
        config_path=tmp_path / "config.toml",
    )

    async def read():
        topics = await server.call_tool("list_topics", {})
        item = await server.call_tool("get_item", {"review_id": "review_cleanup"})
        def structured(result):
            return result.structured_content if hasattr(result, "structured_content") else result[1]
        return structured(topics), structured(item)

    topics, item = asyncio.run(read())
    assert "active_ingress" not in topics
    assert body not in json.dumps(topics)
    assert rationale not in json.dumps(topics)
    assert "review_cleanup" in json.dumps(topics["rendered"])
    assert item["ok"] is True
    assert item["item"]["mnion"]["summary"] == body
    assert item["item"]["mnion"]["rationale"] == rationale
