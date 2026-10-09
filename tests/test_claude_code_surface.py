import json
import os
import subprocess
import sys
from pathlib import Path

from mnion.read_model import materialize_mnion_items_sqlite

SURFACE = Path(__file__).resolve().parents[1] / "adapters" / "claude_code" / "surface.py"


def _run(*args: str, env_state: Path | None = None) -> dict:
    env = {**os.environ, "PATH": "", "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    if env_state is not None:
        env["MNEME_STATE_DIR"] = str(env_state)
    proc = subprocess.run([sys.executable, str(SURFACE), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=30)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _state_with_one_mnion(tmp_path: Path) -> Path:
    receipts = tmp_path / "micro_consolidation_reviews.jsonl"
    receipts.write_text(
        '{"id":"review_route","kind":"micro_consolidation_review","status":"reviewed",'
        '"created_at":"2026-10-06T00:00:00Z","grouped_ids":["tag_a"],"selected_ids":["tag_a"],'
        '"ungrouped_ids":[],"mnion":{"summary":"Claude Code receptor shows the metamemory surface.",'
        '"valence":0.9,"rationale":"route map first"}}\n',
        encoding="utf-8",
    )
    materialize_mnion_items_sqlite(receipts_path=receipts, db_path=tmp_path / "mneme_read_model.sqlite3")
    return tmp_path


def test_surface_cli_prints_the_core_metamemory_surface(tmp_path):
    state = _state_with_one_mnion(tmp_path)

    payload = _run("--state-dir", str(state))

    assert payload["source_status"] == "ok"
    assert payload["topics"] == 1
    assert payload["rendered"].startswith("MNEME_METAMEMORY_SURFACE")
    assert "routes=review_route" in payload["rendered"]
    # a route map, not memory content
    assert "Claude Code receptor shows the metamemory surface." not in payload["rendered"]


def test_surface_cli_reads_mneme_state_dir_from_the_environment(tmp_path):
    state = _state_with_one_mnion(tmp_path)

    payload = _run(env_state=state)

    assert payload["source_status"] == "ok"
    assert Path(payload["db_path"]) == state / "mneme_read_model.sqlite3"


def test_run_forwards_subprocess_isolation_environment(tmp_path, monkeypatch):
    isolation = {
        "HOME": str(tmp_path / "home"),
        "HERMES_HOME": str(tmp_path / "hermes-home"),
        "TMPDIR": str(tmp_path / "tmp"),
        "XDG_CONFIG_HOME": str(tmp_path / "xdg-config"),
        "XDG_DATA_HOME": str(tmp_path / "xdg-data"),
        "XDG_CACHE_HOME": str(tmp_path / "xdg-cache"),
        "XDG_STATE_HOME": str(tmp_path / "xdg-state"),
        "MNEME_STATE_DIR": str(tmp_path / "inherited-state"),
        "MNEME_CONFIG": str(tmp_path / "config.toml"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    for key, value in isolation.items():
        monkeypatch.setenv(key, value)
    (tmp_path / "config.toml").write_text("", encoding="utf-8")
    probe = tmp_path / "environment_probe.py"
    probe.write_text(
        "import json, os, sys\n"
        "print(json.dumps({key: os.environ.get(key) for key in sys.argv[1:]}))\n",
        encoding="utf-8",
    )
    override = tmp_path / "override-state"
    with monkeypatch.context() as patch:
        patch.setattr(sys.modules[__name__], "SURFACE", probe)
        inherited = _run(*isolation)
        overridden = _run(*isolation, env_state=override)

    assert inherited == isolation
    assert overridden == {**isolation, "MNEME_STATE_DIR": str(override)}
    explicit = tmp_path / "explicit-state"
    payload = _run("--state-dir", str(explicit), env_state=override)
    assert payload["source_status"] == "unavailable"
    assert payload["reason"] == "missing_read_model"
    assert Path(payload["db_path"]) == explicit / "mneme_read_model.sqlite3"
    assert not explicit.exists()
    assert not override.exists()
    assert not Path(isolation["MNEME_STATE_DIR"]).exists()


def test_surface_cli_reports_a_missing_read_model_without_failing(tmp_path):
    payload = _run("--state-dir", str(tmp_path / "nothing-here"))

    assert payload["source_status"] == "unavailable"
    assert payload["reason"] == "missing_read_model"
    assert payload["rendered"] == ""


def test_surface_cli_never_writes_to_the_state(tmp_path):
    state = _state_with_one_mnion(tmp_path)
    before = {p.name: p.stat().st_mtime_ns for p in state.iterdir()}

    _run("--state-dir", str(state))

    assert {p.name: p.stat().st_mtime_ns for p in state.iterdir()} == before
