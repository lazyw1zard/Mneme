import json
import os
import subprocess
import sys


def run_cli(*args):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-m", "cogito.cli", *args],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )


def test_cli_record_latest_and_count_since_are_human_script_friendly(tmp_path):
    ledger = tmp_path / "cycles.jsonl"

    first = run_cli(
        "record",
        "--ledger",
        str(ledger),
        "--runtime",
        "manual",
        "--adapter",
        "cli",
        "--session-ref",
        "manual:test",
        "--turn-ref",
        "turn-1",
        "--model",
        "model-x",
        "--input-tokens",
        "2",
        "--output-tokens",
        "3",
        "--output-chars",
        "20",
    )
    first_payload = json.loads(first.stdout)
    assert first_payload["ok"] is True
    assert first_payload["record"]["id"].startswith("cg_")

    run_cli(
        "record",
        "--ledger",
        str(ledger),
        "--runtime",
        "manual",
        "--adapter",
        "cli",
        "--cycle-kind",
        "tool_request",
        "--tool-call-count",
        "1",
    )

    latest = json.loads(run_cli("latest", "--ledger", str(ledger)).stdout)
    assert latest["ok"] is True
    assert latest["record"]["cycle_kind"] == "tool_request"

    count = json.loads(
        run_cli(
            "count-since",
            first_payload["record"]["id"],
            "--ledger",
            str(ledger),
        ).stdout
    )
    assert count == {"ok": True, "cycles_since": 1}
