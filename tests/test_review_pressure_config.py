from mnion.config import MnemeConfig, load_mneme_config
from mnion.core import MemoryTagCaptureRequest, capture_memory_tag
from mnion.review_pressure import evaluate_review_pressure


def test_mneme_config_loads_memory_tag_and_review_pressure_values(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[memory_tag]
default_ttl_seconds = 120
default_call_ttl = 9
active_limit = 7
high_valence_threshold = 0.82

[review_pressure]
enabled = true
call_seq_interval = 5
trigger_on_high_valence = true
trigger_on_interval = true
packet_limit = 4

[storage]
state_dir = "~/custom-mneme-state"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_mneme_config(config_path)

    assert config.memory_tag.default_ttl_seconds == 120
    assert config.memory_tag.default_call_ttl == 9
    assert config.memory_tag.active_limit == 7
    assert config.memory_tag.high_valence_threshold == 0.82
    assert config.review_pressure.call_seq_interval == 5
    assert config.review_pressure.packet_limit == 4
    assert config.storage.state_dir.as_posix().endswith("custom-mneme-state")


def test_review_pressure_flags_high_confirmed_valence_without_semantic_auto_consolidation(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    config = MnemeConfig()

    first = capture_memory_tag(
        MemoryTagCaptureRequest(
            delta="Mneme review pressure should notice confirmed high-valence traces",
            valence=0.68,
            hooks=["project:mneme", "concept:review_pressure", "concept:agentic_review"],
            trigger="design_correction",
            affect_hints=["precision"],
        ),
        ledger_path=ledger,
        state_path=state,
    )
    reinforced = capture_memory_tag(
        MemoryTagCaptureRequest(
            delta="Review pressure should notice the same high valence trace after confirmation",
            valence=0.72,
            hooks=["project:mneme", "concept:review-pressure", "concept:agentic-review"],
            trigger="design-correction-repeat",
            affect_hints=["precision"],
        ),
        ledger_path=ledger,
        state_path=state,
    )

    assert reinforced.action == "reinforced"
    assert reinforced.valence_after >= config.memory_tag.high_valence_threshold

    decision = evaluate_review_pressure(
        capture_result=reinforced,
        active_unread_count=1,
        config=config,
    )

    assert decision.needed is True
    assert "high_valence" in decision.reasons
    assert "confirmed_valence" in decision.reasons
    assert decision.suggested_action == "prepare_micro_consolidation_request"
    assert decision.semantic_auto_consolidation is False
    assert decision.packet_limit == config.review_pressure.packet_limit


def test_review_pressure_checks_call_seq_interval_on_each_mneme_call(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    config = MnemeConfig()

    latest = None
    for index in range(config.review_pressure.call_seq_interval):
        latest = capture_memory_tag(
            MemoryTagCaptureRequest(
                delta=f"interval pressure tag {index}",
                valence=0.2,
                hooks=["project:mneme", f"interval:{index}"],
                trigger="interval_test",
            ),
            ledger_path=ledger,
            state_path=state,
        )

    assert latest is not None
    assert latest.mneme_call_seq == config.review_pressure.call_seq_interval

    decision = evaluate_review_pressure(
        capture_result=latest,
        active_unread_count=config.review_pressure.call_seq_interval,
        config=config,
    )

    assert decision.needed is True
    assert decision.reasons == ["call_seq_interval"]
    assert decision.suggested_action == "prepare_micro_consolidation_request"
    assert decision.semantic_auto_consolidation is False


def test_review_pressure_interval_does_not_trigger_without_unread_active_material(tmp_path):
    config = MnemeConfig()
    # Minimal fake shape is enough: the detector is script-level and should not
    # need receipt/table inspection for the interval decision.
    result = type("Capture", (), {"mneme_call_seq": 10, "valence_after": 0.2, "action": "created"})()

    decision = evaluate_review_pressure(
        capture_result=result,
        active_unread_count=0,
        config=config,
    )

    assert decision.needed is False
    assert decision.reasons == ["no_active_unread_memory_tags"]
    assert decision.semantic_auto_consolidation is False
