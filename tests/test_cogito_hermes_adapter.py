import json
import os
import subprocess
import sys

from cogito.hermes_hook import build_request_from_hermes_payload
from cogito.core import load_cycles


def test_hermes_payload_maps_to_runtime_neutral_cogito_request():
    payload = {
        "session_id": "20260829_221221_eccc19",
        "platform": "telegram",
        "turn_id": "turn-abc",
        "api_request_id": "api-xyz",
        "model": "gpt-5.5",
        "provider": "openai-codex",
        "api_mode": "codex_responses",
        "api_call_count": 2,
        "api_duration": 1.25,
        "finish_reason": "tool_calls",
        "usage": {"input_tokens": 100, "output_tokens": 11},
        "assistant_content_chars": 0,
        "assistant_tool_call_count": 1,
    }

    request = build_request_from_hermes_payload(payload)

    assert request.runtime == "hermes"
    assert request.adapter == "hermes_post_api_request"
    assert request.movement_kind == "model_generation"
    assert request.cycle_kind == "tool_request"
    assert request.session_ref == "telegram:20260829_221221_eccc19"
    assert request.turn_ref == "turn-abc"
    assert request.model == "gpt-5.5"
    assert request.input_tokens == 100
    assert request.output_tokens == 11
    assert request.output_chars == 0
    assert request.tool_call_count == 1
    assert request.metadata["provider"] == "openai-codex"
    assert request.metadata["api_request_id"] == "api-xyz"
    assert request.metadata["api_call_count"] == 2


def sample_post_api_request_envelope():
    return {
        "hook_event_name": "post_api_request",
        "session_id": "sess-1",
        "extra": {
            "platform": "telegram",
            "turn_id": "turn-1",
            "model": "gpt-5.5",
            "usage": {"input_tokens": 5, "output_tokens": 3},
            "assistant_content_chars": 40,
            "assistant_tool_call_count": 0,
            "finish_reason": "stop",
        },
    }


def test_hermes_shell_hook_envelope_records_one_cycle(tmp_path):
    ledger = tmp_path / "cycles.jsonl"
    envelope = sample_post_api_request_envelope()

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "cogito.hermes_hook",
            "--ledger",
            str(ledger),
        ],
        input=json.dumps(envelope),
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    output = json.loads(proc.stdout)
    assert output["ok"] is True
    assert output["record_id"].startswith("cg_")
    [record] = load_cycles(ledger_path=ledger)
    assert record.runtime == "hermes"
    assert record.adapter == "hermes_post_api_request"
    assert record.cycle_kind == "assistant_response"
    assert record.session_ref == "telegram:sess-1"


def test_wrapper_script_records_without_pythonpath(tmp_path):
    ledger = tmp_path / "cycles.jsonl"
    envelope = sample_post_api_request_envelope()

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [sys.executable, "scripts/cogito_hermes_hook.py", "--ledger", str(ledger)],
        input=json.dumps(envelope),
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    output = json.loads(proc.stdout)
    assert output["ok"] is True
    assert load_cycles(ledger_path=ledger)[0].session_ref == "telegram:sess-1"
