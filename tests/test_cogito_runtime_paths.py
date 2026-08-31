from pathlib import Path

from cogito.core import default_cogito_ledger_path


def test_cogito_ledger_uses_mneme_state_dir(monkeypatch, tmp_path):
    root = tmp_path / "state"
    monkeypatch.setenv("MNEME_STATE_DIR", str(root))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg"))

    assert default_cogito_ledger_path() == root / "cogito_cycles.jsonl"


def test_cogito_ledger_xdg_fallback_is_generic(monkeypatch, tmp_path):
    xdg = tmp_path / "xdg"
    monkeypatch.delenv("MNEME_STATE_DIR", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(xdg))

    ledger = default_cogito_ledger_path()

    assert ledger == xdg / "mneme" / "cogito_cycles.jsonl"
    assert ledger.parent.name == "mneme"


def test_cogito_ledger_home_fallback_is_generic(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.delenv("MNEME_STATE_DIR", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: home)

    ledger = default_cogito_ledger_path()

    assert ledger == home / ".local" / "state" / "mneme" / "cogito_cycles.jsonl"
    assert ledger.parent.name == "mneme"
