from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

from mnion.read_model import materialize_mnion_items_sqlite


def _install_fake_hermes_memory_contract(monkeypatch, tmp_path):
    fake_root = tmp_path / "fake_hermes"
    agent_dir = fake_root / "agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "__init__.py").write_text("", encoding="utf-8")
    (agent_dir / "memory_provider.py").write_text(
        "from dataclasses import dataclass\n"
        "from typing import Any, Dict, List, Optional\n\n"
        "@dataclass(frozen=True)\n"
        "class RecallStatus:\n"
        "    provider_label: str\n"
        "    count: int\n"
        "    glyph: str = '🧠'\n\n"
        "class MemoryProvider:\n"
        "    @property\n"
        "    def name(self) -> str:\n"
        "        raise NotImplementedError\n"
        "    def is_available(self) -> bool:\n"
        "        raise NotImplementedError\n"
        "    def initialize(self, session_id: str, **kwargs) -> None:\n"
        "        raise NotImplementedError\n"
        "    def get_tool_schemas(self) -> List[Dict[str, Any]]:\n"
        "        raise NotImplementedError\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(fake_root))
    sys.modules.pop("agent", None)
    sys.modules.pop("agent.memory_provider", None)


def _load_provider_module(monkeypatch, tmp_path):
    _install_fake_hermes_memory_contract(monkeypatch, tmp_path)
    module_path = Path(__file__).resolve().parents[1] / "adapters" / "hermes_memory_provider" / "mneme" / "__init__.py"
    module_name = f"mneme_hermes_provider_under_test_{tmp_path.name}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _materialized_read_model(tmp_path):
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    db = tmp_path / "mneme.sqlite3"
    receipts.write_text(
        "\n".join(
            [
                '{"id":"review_a","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:00:00Z","grouped_ids":["tag_a"],"selected_ids":["tag_a"],"ungrouped_ids":[],"mnion":{"summary":"First reviewed Mneme provider item.","valence":0.90,"rationale":"kept by agent"}}',
                '{"id":"review_b","kind":"micro_consolidation_review","status":"reviewed","created_at":"2026-10-04T00:01:00Z","grouped_ids":["tag_b"],"selected_ids":["tag_b"],"ungrouped_ids":[],"mnion":{"summary":"Second reviewed Mneme provider item.","valence":0.80,"rationale":null}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=db)
    return db


@dataclass
class _Context:
    provider: Any = None

    def register_memory_provider(self, provider):
        self.provider = provider


def test_hermes_provider_registers_and_exposes_no_tools(monkeypatch, tmp_path):
    module = _load_provider_module(monkeypatch, tmp_path)
    ctx = _Context()

    module.register(ctx)

    assert ctx.provider is not None
    assert ctx.provider.name == "mneme"
    assert ctx.provider.is_available() is True
    assert ctx.provider.get_tool_schemas() == []
    assert "MNEME_ACTIVE_SURFACE" in ctx.provider.system_prompt_block()


def test_hermes_provider_prefetch_returns_bounded_active_surface_and_status(monkeypatch, tmp_path):
    module = _load_provider_module(monkeypatch, tmp_path)
    db = _materialized_read_model(tmp_path)
    provider = module.MnemeMemoryProvider(config={"read_model_path": str(db), "limit": 1})
    provider.initialize(session_id="test")

    rendered = provider.prefetch("unrelated cue should not gate active surface", session_id="test")

    assert "MNEME_ACTIVE_SURFACE" in rendered
    assert "review_a" in rendered
    assert "review_b" not in rendered
    assert "no_familiarity" not in rendered
    assert "surface overlap" not in rendered.lower()
    status = provider.recall_status()
    assert status is not None
    assert status.provider_label == "Mneme"
    assert status.count == 1


def test_hermes_provider_recall_status_resets_after_missing_read_model(monkeypatch, tmp_path):
    module = _load_provider_module(monkeypatch, tmp_path)
    db = _materialized_read_model(tmp_path)
    provider = module.MnemeMemoryProvider(config={"read_model_path": str(db), "limit": 1})
    provider.initialize(session_id="test")
    assert provider.prefetch("first", session_id="test")
    assert provider.recall_status() is not None

    missing = tmp_path / "missing.sqlite3"
    provider = module.MnemeMemoryProvider(config={"read_model_path": str(missing), "limit": 1})
    provider.initialize(session_id="test")

    assert provider.prefetch("second", session_id="test") == ""
    assert provider.recall_status() is None
    assert not missing.exists()


def test_hermes_provider_locked_read_model_returns_quickly_empty(monkeypatch, tmp_path):
    module = _load_provider_module(monkeypatch, tmp_path)
    db = _materialized_read_model(tmp_path)
    provider = module.MnemeMemoryProvider(config={"read_model_path": str(db), "limit": 1})
    provider.initialize(session_id="test")
    locker = sqlite3.connect(db)
    try:
        locker.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        rendered = provider.prefetch("locked read model", session_id="test")
        elapsed = time.monotonic() - started
    finally:
        locker.rollback()
        locker.close()

    assert elapsed < 0.5
    assert rendered == ""
    assert provider.recall_status() is None


def test_hermes_provider_default_state_dir_matches_mcp_env_semantics(monkeypatch, tmp_path):
    module = _load_provider_module(monkeypatch, tmp_path)
    explicit = tmp_path / "explicit_state"
    xdg = tmp_path / "xdg_state"

    monkeypatch.setenv("MNEME_STATE_DIR", str(explicit))
    monkeypatch.setenv("XDG_STATE_HOME", str(xdg))
    assert module._default_state_dir() == explicit

    monkeypatch.delenv("MNEME_STATE_DIR")
    assert module._default_state_dir() == xdg / "mneme"
