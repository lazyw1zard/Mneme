from pathlib import Path

from mnion.mcp_server import (
    default_call_state_path,
    default_ledger_path,
    default_state_dir,
)


def test_mneme_state_dir_env_overrides_default(monkeypatch, tmp_path):
    root = tmp_path / "custom-state"
    monkeypatch.setenv("MNEME_STATE_DIR", str(root))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))

    assert default_state_dir() == root
    assert default_ledger_path() == root / "mnions.jsonl"
    assert default_call_state_path() == root / "mneme_seq.json"


def test_xdg_state_home_fallback_uses_generic_mneme_dir(monkeypatch, tmp_path):
    xdg = tmp_path / "xdg-state"
    monkeypatch.delenv("MNEME_STATE_DIR", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(xdg))

    state_dir = default_state_dir()

    assert state_dir == xdg / "mneme"
    assert state_dir.name == "mneme"


def test_home_fallback_uses_generic_mneme_dir(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.delenv("MNEME_STATE_DIR", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: home)

    state_dir = default_state_dir()

    assert state_dir == home / ".local" / "state" / "mneme"
    assert state_dir.name == "mneme"
