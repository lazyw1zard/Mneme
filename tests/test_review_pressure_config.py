from mnion.config import MnemeConfig, ReviewPressureConfig, load_mneme_config
from mnion.core import MemoryTagCaptureRequest, capture_memory_tag
from mnion.micro_consolidation import prepare_micro_consolidation_request
from mnion.review_pressure import build_review_pressure_ingress, evaluate_review_pressure


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
trigger_on_pinned_backlog = true
pinned_backlog_age_seconds = 3600

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
    assert config.review_pressure.trigger_on_pinned_backlog is True
    assert config.review_pressure.pinned_backlog_age_seconds == 3600
    assert config.storage.state_dir.as_posix().endswith("custom-mneme-state")


def test_review_pressure_pins_high_valence_singleton_without_hard_barrier(tmp_path):
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

    assert decision.needed is False
    assert decision.reasons == ["high_valence_pinned", "confirmed_valence", "insufficient_review_batch"]
    assert decision.suggested_action is None
    assert decision.semantic_auto_consolidation is False
    assert decision.packet_limit == config.review_pressure.packet_limit


def test_review_pressure_uses_high_valence_as_priority_not_hard_trigger_when_material_exists(tmp_path):
    config = MnemeConfig()
    result = type("Capture", (), {"mneme_call_seq": 3, "valence_after": 0.9, "action": "created"})()

    decision = evaluate_review_pressure(
        capture_result=result,
        active_unread_count=2,
        config=config,
    )

    assert decision.needed is False
    assert decision.reasons == ["high_valence_pinned"]
    assert decision.suggested_action is None
    assert decision.semantic_auto_consolidation is False


def test_review_pressure_uses_old_pinned_tags_as_backlog_pressure_not_high_valence_trigger(tmp_path):
    config = MnemeConfig(review_pressure=ReviewPressureConfig(pinned_backlog_age_seconds=3600))
    result = type("Capture", (), {"mneme_call_seq": 17, "valence_after": 0.2, "action": "created"})()

    decision = evaluate_review_pressure(
        capture_result=result,
        active_unread_count=3,
        config=config,
        pinned_unread_count=1,
        oldest_pinned_unread_age_seconds=3600,
    )

    assert decision.needed is True
    assert decision.reasons == ["pinned_backlog_pressure"]
    assert decision.suggested_action == "prepare_micro_consolidation_request"
    assert decision.semantic_auto_consolidation is False


def test_review_pressure_does_not_trigger_pinned_backlog_before_configured_age(tmp_path):
    config = MnemeConfig(review_pressure=ReviewPressureConfig(pinned_backlog_age_seconds=3600))
    result = type("Capture", (), {"mneme_call_seq": 17, "valence_after": 0.2, "action": "created"})()

    decision = evaluate_review_pressure(
        capture_result=result,
        active_unread_count=3,
        config=config,
        pinned_unread_count=1,
        oldest_pinned_unread_age_seconds=3599,
    )

    assert decision.needed is False
    assert decision.reasons == []
    assert decision.suggested_action is None


def test_review_pressure_does_not_make_old_pinned_singletons_into_review_packets(tmp_path):
    config = MnemeConfig(review_pressure=ReviewPressureConfig(pinned_backlog_age_seconds=3600))
    result = type("Capture", (), {"mneme_call_seq": 17, "valence_after": 0.2, "action": "created"})()

    decision = evaluate_review_pressure(
        capture_result=result,
        active_unread_count=1,
        config=config,
        pinned_unread_count=1,
        oldest_pinned_unread_age_seconds=3600,
    )

    assert decision.needed is False
    assert decision.reasons == ["pinned_backlog_pressure", "insufficient_review_batch"]
    assert decision.suggested_action is None


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


def test_review_pressure_interval_is_relative_to_last_review_seq_after_config_change(tmp_path):
    config = MnemeConfig(review_pressure=ReviewPressureConfig(call_seq_interval=8))
    before_due = type("Capture", (), {"mneme_call_seq": 96, "valence_after": 0.2, "action": "created"})()

    decision = evaluate_review_pressure(
        capture_result=before_due,
        active_unread_count=6,
        config=config,
        last_review_seq=90,
    )

    assert decision.needed is False
    assert decision.reasons == []
    assert decision.suggested_action is None

    due = type("Capture", (), {"mneme_call_seq": 98, "valence_after": 0.2, "action": "created"})()
    due_decision = evaluate_review_pressure(
        capture_result=due,
        active_unread_count=6,
        config=config,
        last_review_seq=90,
    )

    assert due_decision.needed is True
    assert due_decision.reasons == ["call_seq_interval"]
    assert due_decision.suggested_action == "prepare_micro_consolidation_request"


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


def test_review_pressure_ingress_hands_bounded_packet_to_agent_input(tmp_path):
    ledger = tmp_path / "memory_tags.jsonl"
    state = tmp_path / "mneme_seq.json"
    config = MnemeConfig(review_pressure=ReviewPressureConfig(call_seq_interval=2))
    pinned = capture_memory_tag(
        MemoryTagCaptureRequest(
            delta="Mneme should pin high-valence traces until a review packet is ready",
            valence=0.91,
            hooks=["project:mneme", "concept:pinned_ingress"],
            trigger="operator_correction",
        ),
        ledger_path=ledger,
        state_path=state,
    )
    result = capture_memory_tag(
        MemoryTagCaptureRequest(
            delta="Mneme should hand accumulated review packets to the live agent input when pressure triggers",
            valence=0.2,
            hooks=["project:mneme", "concept:agent_ingress_neighbor"],
            trigger="operator_correction_neighbor",
        ),
        ledger_path=ledger,
        state_path=state,
    )
    request = prepare_micro_consolidation_request(
        ledger_path=ledger,
        state_path=state,
        packet_limit=config.review_pressure.packet_limit,
    )
    decision = evaluate_review_pressure(
        capture_result=result,
        active_unread_count=request.selection.unread_active_count,
        config=config,
    )

    ingress = build_review_pressure_ingress(decision=decision, review_request=request)

    assert ingress is not None
    assert ingress.kind == "mneme_review_pressure_ingress"
    assert ingress.suggested_action == "agentic_micro_consolidation_review"
    assert ingress.semantic_auto_consolidation is False
    assert ingress.packet_limit == config.review_pressure.packet_limit
    assert ingress.selected_ids[:2] == [pinned.target_id, result.target_id]
    assert ingress.prompt.startswith("Find semantically close memory tags")
    assert ingress.expected_output_schema["summary"]
    assert [tag["id"] for tag in ingress.memory_tags[:2]] == [pinned.target_id, result.target_id]
    assert "MNEME_REVIEW_PRESSURE" in ingress.rendered
    assert pinned.target_id in ingress.rendered
    assert result.target_id in ingress.rendered
    assert "Do not auto-promote" in ingress.rendered
