"""Production-path proof for bounded learned causal speech actions."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import sys
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
    AuditoryIncrementalTerminalEvent,
    _event_payload,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AUDITORY_L5_SCHEMA,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    AUDITORY_RECOGNITION_OPERATOR,
    AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.causal_action import (
    CausalActionOwner,
    CausalActionSettlement,
)
from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.substrate.causal_prediction import (
    CausalPredictionAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    MAX_EMITTED_PCM_SAMPLES,
    MIN_EMITTED_PCM_SAMPLES,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()


def _actual_causal_speech_wav() -> bytes:
    samples = np.asarray(
        [
            int(12_000 * math.sin(2 * math.pi * 440 * index / 16_000))
            for index in range(800)
        ],
        dtype="<i2",
    )
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(samples.tobytes())
    return output.getvalue()


def _companion_pcm_chunk() -> bytes:
    return np.asarray(
        [
            int(12_000 * math.sin(2 * math.pi * 440 * index / 16_000))
            for index in range(1_024)
        ],
        dtype="<i2",
    ).tobytes()


def _full_field(
    name: str,
    values: tuple[Fraction, ...],
    sight_values: tuple[Fraction, ...] | None = None,
    source_time_start: Fraction = Fraction(0),
):
    duration = Fraction(1, 50)
    sample_count = 320
    capture = transduce_auditory_full_field(
        np.asarray(
            [float(values[index % len(values)]) for index in range(sample_count)],
            dtype=np.float64,
        ),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    sound_ports = auditory_kernel_component_inputs(
        capture,
        source_anchor=source_time_start,
    )
    assert len(capture.channels) == 16
    assert len(sound_ports) == AUDITORY_KERNEL_COMPONENT_COUNT
    observed = {PhysicalSense.SOUND: sound_ports}
    if sight_values is not None:
        observed[PhysicalSense.SIGHT] = (
            NativeSensorySubstreamInput(
                sense=PhysicalSense.SIGHT,
                sensor_id="test-camera",
                substream_id="test-retinal-cell",
                topology_index=0,
                coordinates=(
                    NativeAxisCoordinate("retinal-row", "0"),
                    NativeAxisCoordinate("retinal-column", "0"),
                ),
                physical_quantity="retinal-luminance",
                physical_unit="full-scale-luminance",
                source_times=tuple(
                    source_time_start
                    + duration * Fraction(index + 1, len(sight_values))
                    for index in range(len(sight_values))
                ),
                normalized_signal=sight_values,
                phase_turns=tuple(
                    Fraction(index, 16)
                    for index in range(len(sight_values))
                ),
            ),
        )
    return build_six_sense_full_field(
        assembly_id=f"causal-action-engine-{name}",
        source_time_start=source_time_start,
        source_time_end=source_time_start + duration,
        observed_substreams=observed,
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in observed
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )


def _artifacts(
    *,
    name: str,
    label: str,
    values: tuple[Fraction, ...],
    reciprocity: AuditoryReciprocityOwner,
    teach: bool = False,
    stream_id: str | None = None,
    source_sample_start: int = 0,
    routing_chis: tuple[int, ...] = (3, 1, 3),
    source_tags: tuple[str, ...] = ("auditory:unresolved_source",),
    sight_values: tuple[Fraction, ...] | None = None,
):
    built = _full_field(
        name,
        values,
        sight_values,
        source_time_start=Fraction(
            source_sample_start, REQUIRED_SAMPLE_RATE_HZ
        ),
    )
    auditory = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="utterance")
    assert auditory is not None
    if teach:
        reciprocity.teach(
            auditory,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label=label,
        )
    recognition = reciprocity.recognize(
        auditory,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
    )
    assert recognition.state.value == "unique"
    resolved_stream_id = stream_id or f"stream-{name}"
    source_sample_end = source_sample_start + 320
    event_id = _digest({
        "source_sample_end": source_sample_end,
        "source_sample_start": source_sample_start,
        "stream_id": resolved_stream_id,
        "structural_fingerprint": auditory.structural_fingerprint,
    })
    transport = (_digest({
        "kind": "transport",
        "name": name,
        "source_sample_start": source_sample_start,
    }),)
    cochlear = (_digest({
        "kind": "cochlear",
        "name": name,
        "source_sample_start": source_sample_start,
    }),)
    joint = (_digest({
        "kind": "joint",
        "name": name,
        "source_sample_start": source_sample_start,
    }),)
    payload = _event_payload(
        event_id=event_id,
        stream_id=resolved_stream_id,
        source_sample_start=source_sample_start,
        source_sample_end=source_sample_end,
        tutor_label=label,
        structural_fingerprint=auditory.structural_fingerprint,
        l5_authority_receipt_sha256=auditory.authority_receipt_sha256,
        transport_receipt_sha256s=transport,
        cochlear_receipt_sha256s=cochlear,
        joint_settlement_receipt_sha256s=joint,
        recognition_occurrence=recognition.occurrence,
        schema=AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
        l5_schema=AUDITORY_L5_SCHEMA,
        reciprocity_snapshot_schema=AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
        recognition_operator=AUDITORY_RECOGNITION_OPERATOR,
    )
    terminal = AuditoryIncrementalTerminalEvent(
        event_id=event_id,
        stream_id=resolved_stream_id,
        source_sample_start=source_sample_start,
        source_sample_end=source_sample_end,
        tutor_label=label,
        structural_fingerprint=auditory.structural_fingerprint,
        l5_authority_receipt_sha256=auditory.authority_receipt_sha256,
        transport_receipt_sha256s=transport,
        cochlear_receipt_sha256s=cochlear,
        joint_settlement_receipt_sha256s=joint,
        schema=AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
        authority_receipt_sha256=_digest(payload),
        recognition_occurrence=recognition.occurrence,
        l5_schema=AUDITORY_L5_SCHEMA,
        reciprocity_snapshot_schema=AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
        recognition_operator=AUDITORY_RECOGNITION_OPERATOR,
    )
    terminal.verify()
    settled = []
    causal_owner = ExactCausalExperienceOwner(
        on_settlement=settled.append,
        log_event=lambda *_args, **_kwargs: None,
    )
    settlement = causal_owner.settle(
        built,
        recognized_language_record=terminal.as_record(),
        routing_chis=routing_chis,
        source_tags=source_tags,
    )
    settlement.verify()
    assert settled == [settlement]
    return built, auditory, terminal, settlement


@pytest.fixture
def learned_artifacts():
    reciprocity = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    trigger = _artifacts(
        name="trigger",
        label="hello guala",
        values=(Fraction(1, 8), Fraction(1, 4), Fraction(3, 8)),
        reciprocity=reciprocity,
        teach=True,
    )
    action = _artifacts(
        name="action",
        label="hello daddy",
        values=(Fraction(5, 8), Fraction(3, 4), Fraction(7, 8)),
        reciprocity=reciprocity,
        teach=True,
    )
    return reciprocity, trigger, action


def _forbidden_legacy(*_args, **_kwargs):
    raise AssertionError("legacy emission path entered a causal spoken turn")


@pytest.mark.parametrize("phased", ("0", "1"))
def test_spoken_turn_releases_only_its_learned_causal_action(
    monkeypatch,
    learned_artifacts,
    phased,
) -> None:
    reciprocity, trigger_artifacts, action_artifacts = learned_artifacts
    _trigger_built, _trigger_l5, trigger_terminal, trigger = (
        trigger_artifacts
    )
    _action_built, _action_l5, action_terminal, action = action_artifacts
    _current_built, current_l5, current_terminal, _current = _artifacts(
        name="trigger",
        label="hello guala",
        values=(Fraction(1, 8), Fraction(1, 4), Fraction(3, 8)),
        reciprocity=reciprocity,
        stream_id=f"live-turn-{phased}",
        source_sample_start=320,
    )
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "engine-integration-key")
    monkeypatch.setenv("CONVERSE_PHASED", phased)
    monkeypatch.setenv("EMISSION_DYNAMICS", "1")
    monkeypatch.setenv("EMISSION_MODE", "grandurun")
    guala = Guala()
    try:
        guala._causal_action_cycle.accept(trigger)
        guala._causal_action_cycle.accept(action)
        binding = guala.teach_causal_action(
            trigger_experience_id=trigger_terminal.event_id,
            action_experience_id=action_terminal.event_id,
            source="joe",
        )
        assert binding["trigger_reference_id"] == trigger_terminal.event_id
        assert binding["action_reference_id"] == action_terminal.event_id
        assert binding["trigger_experience_id"] == trigger.event_id
        assert binding["action_experience_id"] == action.event_id
        assert binding["action_evidence_receipt_sha256"] == (
            action.authority_receipt_sha256
        )
        learned_evidence = (
            guala._causal_action_cycle.verified_relation_evidence()
        )
        assert len(learned_evidence) == 1
        assert (
            learned_evidence[0].teaching_evidence_receipt_sha256
            == action.authority_receipt_sha256
        )
        guala._brain_emission_candidates = _forbidden_legacy
        guala._emit_dynamics = _forbidden_legacy
        guala._compose_organism_attempt = _forbidden_legacy
        with guala._auditory_incremental_terminals._lock:
            guala._auditory_incremental_terminals._issue_locked(
                current_terminal,
                current_l5,
            )

        turn = guala.converse(
            current_terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=current_terminal,
        )

        assert turn.response == "hello daddy"
        assert turn.response_source == "causal_action_cycle_commit"
        assert turn.causal_experience_id == current_terminal.event_id
        assert turn.causal_intake_receipt_sha256 == (
            current_terminal.authority_receipt_sha256
        )
        assert turn.committed_sections == ("causal_action_cycle",)
        assert len(turn.commit_provenance) == 1
        assert turn.commit_provenance[0].binding_id == binding["binding_id"]
        observation = guala.observation_snapshot()
        assert observation["conversation"] == {
            "status": "observed",
            "input": current_terminal.tutor_label,
            "input_source": "auditory:unresolved_source",
            "response": "hello daddy",
            "response_source": "causal_action_cycle_commit",
            "emission_id": turn.emission_id,
        }
        assert observation["embodiment"]["status"] == "observed"
        assert observation["embodiment"]["location"]["region_id"] == (
            "W1-region-A"
        )
        assert guala._latest_causal_settlement is not None
        guala._latest_causal_settlement.verify()
        cycle_status = guala._causal_action_cycle.status()
        assert cycle_status["intents"] == 1
        assert cycle_status["executions"] == 1
        review = guala.review_causal_action_emission(
            emission_id=turn.emission_id,
            correct=True,
            source="joe",
        )
        assert review["status"] == "queued_until_outcome"
        speech_outcome = guala.observe_causal_speech_output(
            _actual_causal_speech_wav()
        )
        assert speech_outcome["status"] == "completed"
        reviewed_status = guala._causal_action_cycle.status()
        assert reviewed_status["binding_statuses"]["confirmed"] == 1
        assert guala._causal_cycle_pending_review is None
        prediction = guala._full_field_prediction.status()
        assert prediction["action_relations"] == 1
        assert prediction["passive_relations"] == 0
        assert prediction["armed_action"] is False
    finally:
        guala.shutdown()


def test_unknown_causal_action_is_typed_silence_not_organism_empty(
    monkeypatch,
    learned_artifacts,
) -> None:
    _reciprocity, trigger_artifacts, _action_artifacts = learned_artifacts
    _built, _auditory, _terminal, trigger = trigger_artifacts
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "engine-integration-key")
    guala = Guala()
    try:
        guala._brain_emission_candidates = _forbidden_legacy
        guala._emit_dynamics = _forbidden_legacy
        guala._compose_organism_attempt = _forbidden_legacy
        guala._accept_causal_settlement(trigger)
        settlement = guala._emit_from_invariants(
            (),
            ("hello", "guala"),
            causal_settlement=trigger,
        )
        assert settlement.status == "unknown"
        assert settlement.stop_reason == "causal_action_unknown"
        assert "organism" not in settlement.stop_reason
        assert guala._committed_emission_response(settlement) == (
            "",
            "causal_action_unknown",
        )
        with pytest.raises(ValueError, match="silent reason changed"):
            CausalActionSettlement(
                status="unknown",
                stop_reason="organism_empty",
                tick=1,
            ).verify_receipts()
    finally:
        guala.shutdown()


def test_contemporaneous_sight_remains_bound_without_blocking_spoken_action(
    learned_artifacts,
) -> None:
    reciprocity, trigger_artifacts, action_artifacts = learned_artifacts
    _trigger_built, _trigger_l5, _trigger_terminal, trigger = (
        trigger_artifacts
    )
    _action_built, _action_l5, _action_terminal, action = action_artifacts
    owner = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key="audiovisual-causal-action-key",
    )
    owner.offer_teaching_experience(trigger)
    owner.offer_teaching_experience(action)
    owner.teach(
        trigger_experience_id=trigger.event_id,
        action_experience_id=action.event_id,
        source="joe",
    )
    _built, _auditory, _terminal, audiovisual = _artifacts(
        name="trigger",
        label="hello guala",
        values=(Fraction(1, 8), Fraction(1, 4), Fraction(3, 8)),
        reciprocity=reciprocity,
        stream_id="audiovisual-current",
        source_sample_start=960,
        sight_values=(Fraction(1, 10), Fraction(9, 10)),
    )
    sight = next(
        value for value in audiovisual.interpretations
        if value.sense == "sight"
    )
    sound = next(
        value for value in audiovisual.interpretations
        if value.sense == "sound"
    )
    assert sight.state == "observed"
    assert sight.substreams[0].field_tuples
    assert sound.state == "observed"

    formed = owner.form(audiovisual, tick=31)

    assert formed.content == "hello daddy"
    assert formed.commit_provenance[0].current_settlement_receipt_sha256 == (
        audiovisual.authority_receipt_sha256
    )
    assert owner.verify_issued(formed)


def test_concurrent_full_field_formations_do_not_cross_or_expose_forgery(
    learned_artifacts,
) -> None:
    reciprocity, trigger_artifacts, action_artifacts = learned_artifacts
    _trigger_built, _trigger_l5, _trigger_terminal, trigger = (
        trigger_artifacts
    )
    _action_built, _action_l5, _action_terminal, action = action_artifacts
    owner = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key="concurrent-causal-action-key",
    )
    owner.offer_teaching_experience(trigger)
    owner.offer_teaching_experience(action)
    owner.teach(
        trigger_experience_id=trigger.event_id,
        action_experience_id=action.event_id,
        source="joe",
    )
    current = []
    for index in range(4):
        _built, _auditory, _terminal, settlement = _artifacts(
            name="trigger",
            label="hello guala",
            values=(Fraction(1, 8), Fraction(1, 4), Fraction(3, 8)),
            reciprocity=reciprocity,
            stream_id=f"concurrent-{index}",
            source_sample_start=(index + 1) * 320,
            routing_chis=(index, 3, index),
            source_tags=(f"auditory:test-{index}",),
        )
        current.append(settlement)

    with ThreadPoolExecutor(max_workers=4) as executor:
        formed = tuple(executor.map(
            lambda value: owner.form(value, tick=29),
            current,
        ))

    assert {value.content for value in formed} == {"hello daddy"}
    assert len({
        value.commit_provenance[0].current_settlement_receipt_sha256
        for value in formed
    }) == 4
    assert all(owner.verify_issued(value) for value in formed)
    repeated = owner.form(current[0], tick=30)
    assert repeated is formed[0]
    assert repeated.tick == 29
    state_bytes = owner.status()["encoded_state_bytes"]
    for index in range(512):
        assert owner.form(current[index % len(current)], tick=31 + index).content == (
            "hello daddy"
        )
    forged = replace(formed[0], content="forged")
    with pytest.raises(ValueError, match="not exact-closed"):
        owner.verify_issued(forged)
    status = owner.status()
    assert status["actions"] == 1
    assert status["witnesses"] == 2
    assert status["encoded_state_bytes"] == state_bytes
    assert status["formed"] == 517
    assert status["issued_actions"] == 4


def test_one_experience_cannot_be_taught_as_its_own_action(
    learned_artifacts,
) -> None:
    _reciprocity, trigger_artifacts, _action_artifacts = learned_artifacts
    _built, _auditory, _terminal, trigger = trigger_artifacts
    owner = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key="separate-experience-key",
    )
    owner.offer_teaching_experience(trigger)

    with pytest.raises(ValueError, match="separate trigger and action"):
        owner.teach(
            trigger_experience_id=trigger.event_id,
            action_experience_id=trigger.event_id,
            source="joe",
        )


def test_full_engine_restart_preserves_exact_learned_action(
    monkeypatch,
    tmp_path,
    learned_artifacts,
) -> None:
    _reciprocity, trigger_artifacts, action_artifacts = learned_artifacts
    _trigger_built, _trigger_l5, _trigger_terminal, trigger = (
        trigger_artifacts
    )
    _action_built, _action_l5, _action_terminal, action = action_artifacts
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "restart-integration-key")
    writer = Guala()
    restored = None
    try:
        writer._causal_action_cycle.accept(trigger)
        writer._causal_action_cycle.accept(action)
        writer.teach_causal_action(
            trigger_experience_id=trigger.event_id,
            action_experience_id=action.event_id,
            source="joe",
        )
        writer._record_causal_perception_without_dispatch(trigger)
        writer._record_causal_perception_without_dispatch(
            action,
            prediction_transition=True,
        )
        expected = writer._causal_action_cycle.encoded_snapshot()
        expected_prediction_relations = (
            writer._full_field_prediction.relation_records()
        )
        expected_prediction_latest = (
            writer._latest_full_field_prediction_observation
        )
        assert len(expected_prediction_relations) == 1
        writer.save_full_state(str(tmp_path))
        identity = writer._guala_identity
        writer.shutdown()
        writer = None

        restored = Guala()
        restored.load_full_state(str(tmp_path))

        assert restored._load_successful, restored._load_errors
        assert restored._guala_identity == identity
        assert restored._causal_action_cycle.encoded_snapshot() == expected
        assert restored._full_field_prediction.relation_records() == (
            expected_prediction_relations
        )
        assert restored._full_field_prediction.status()["active_context"] is False
        assert restored._latest_full_field_prediction_observation == (
            expected_prediction_latest
        )
        formed = restored._causal_action_cycle.select(trigger)
        assert formed.intent.action == ActionCommand.speech("hello daddy")
        assert restored._causal_action_cycle.verify_live_intent(formed.intent)
    finally:
        if writer is not None:
            writer.shutdown()
        if restored is not None:
            restored.shutdown()


def test_legacy_adjacency_prediction_is_verified_and_retired_not_migrated(
    monkeypatch,
    tmp_path,
    learned_artifacts,
) -> None:
    _reciprocity, trigger_artifacts, action_artifacts = learned_artifacts
    _trigger_built, _trigger_l5, _trigger_terminal, trigger = (
        trigger_artifacts
    )
    _action_built, _action_l5, _action_terminal, action = action_artifacts
    key = "legacy-prediction-retirement-key"
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", key)
    writer = Guala()
    restored = None
    try:
        legacy = CausalPredictionAuthority(authority_key=key)
        legacy.start(trigger)
        legacy.advance(action)
        assert legacy.status()["relations"] == 1
        payload = writer._teaching_persistence_payload()
        payload.pop("full_field_prediction")
        payload["causal_prediction"] = json.loads(
            legacy.encoded_snapshot()
        )
        writer._teaching_persistence_payload = lambda: payload
        writer.save_full_state(str(tmp_path))
        writer.shutdown()
        writer = None

        restored = Guala()
        restored.load_full_state(str(tmp_path))

        assert restored._load_successful, restored._load_errors
        assert restored._full_field_prediction.relation_records() == ()
        assert restored._legacy_causal_prediction_disposition == {
            "legacy_relations": 1,
            "reason": "automatic_adjacency_is_not_causal_evidence",
            "status": "verified_and_retired",
        }
    finally:
        if writer is not None:
            writer.shutdown()
        if restored is not None:
            restored.shutdown()


def test_full_field_intent_executes_embodiment_and_closes_on_exact_w1_outcome(
    monkeypatch,
    learned_artifacts,
) -> None:
    _reciprocity, trigger_artifacts, outcome_artifacts = learned_artifacts
    _trigger_built, _trigger_l5, _trigger_terminal, trigger = (
        trigger_artifacts
    )
    _outcome_built, _outcome_l5, _outcome_terminal, outcome = (
        outcome_artifacts
    )
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "embodiment-integration-key")
    guala = Guala()
    try:
        guala._causal_action_cycle.accept(trigger)
        command = ActionCommand.embodiment(
            PORT_ID,
            encode_command(
                MoveCommand(
                    target_pose=PoseMM(
                        position=PositionMM(1000, 2000, 0),
                        heading_millidegrees=90_000,
                    )
                )
            ),
        )
        guala._causal_action_cycle.teach(
            trigger_reference=trigger.event_id,
            action=command,
            source="joe",
            nonce="embodiment-teacher-nonce-0001",
        )
        execute = guala._causal_action_dispatcher._embodiment_executor

        def assert_conditioned_before_execution(request):
            status = guala._full_field_prediction.status()
            assert status["armed_action"] is True
            assert guala._full_field_prediction.current_attempt().mode == (
                "action_conditioned"
            )
            return execute(request)

        guala._causal_action_dispatcher._embodiment_executor = (
            assert_conditioned_before_execution
        )

        guala._accept_causal_settlement(trigger)
        emission = guala._emit_from_invariants(
            (), (), causal_settlement=trigger
        )
        assert guala._committed_emission_response(emission) == (
            "",
            "causal_action_cycle_closed",
        )
        observed = guala._embodiment_world.observation_snapshot()
        assert observed.revision == 1
        assert next(
            item for item in observed.bodies
            if item.body_id == observed.self_body_id
        ).pose.position == PositionMM(1000, 2000, 0)
        surface = guala.observation_snapshot()
        assert surface["embodied_action"]["status"] == "completed"
        assert surface["embodied_action"]["after_revision"] == 1
        self_body = next(
            item for item in surface["embodiment"]["bodies"]
            if item["body_id"] == surface["embodiment"]["self_body_id"]
        )
        assert self_body["pose"]["position"] == {
            "x_mm": 1000,
            "y_mm": 2000,
            "z_mm": 0,
        }

        status = guala._causal_action_cycle.status()
        assert status["closures"] == 1
        assert status["intents"] == 0
        assert status["executions"] == 0
        assert status["outcomes"] == 0
        assert guala._causal_action_dispatcher.status()["active"] is False
        assert guala._latest_causal_settlement != outcome
        prediction = guala._full_field_prediction
        relations = prediction.relation_records()
        assert len(relations) == 1
        assert relations[0]["mode"] == "action_conditioned"
        assert prediction.current_episode().w1_attachment is not None
        assert prediction.current_episode().w1_attachment[
            "observation"
        ]["revision"] == 1
    finally:
        guala.shutdown()


def test_unrelated_settlements_rebase_prediction_without_adjacency_learning(
    monkeypatch,
    learned_artifacts,
) -> None:
    reciprocity, trigger_artifacts, action_artifacts = learned_artifacts
    _trigger_built, _trigger_l5, _trigger_terminal, trigger = trigger_artifacts
    _action_built, _action_l5, _action_terminal, action = action_artifacts
    _repeat_built, _repeat_l5, _repeat_terminal, trigger_repeat = _artifacts(
        name="trigger",
        label="hello guala",
        values=(Fraction(1, 8), Fraction(1, 4), Fraction(3, 8)),
        reciprocity=reciprocity,
        stream_id="prediction-trigger-repeat",
        source_sample_start=640,
    )
    _outcome_built, _outcome_l5, _outcome_terminal, action_repeat = _artifacts(
        name="action",
        label="hello daddy",
        values=(Fraction(5, 8), Fraction(3, 4), Fraction(7, 8)),
        reciprocity=reciprocity,
        stream_id="prediction-action-repeat",
        source_sample_start=960,
    )
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "prediction-engine-key")
    guala = Guala()
    try:
        for settlement in (
            trigger,
            action,
            trigger_repeat,
            action_repeat,
        ):
            guala._accept_causal_settlement(settlement)

        prediction = guala._full_field_prediction
        assert prediction.current_episode().settlement_receipt_sha256 == (
            action_repeat.authority_receipt_sha256
        )
        assert prediction.current_attempt().status == "unknown"
        assert prediction.latest_resolution() is None
        assert prediction.relation_records() == ()
        assert prediction.status() == {
            "action_relations": 0,
            "active_context": True,
            "armed_action": False,
            "episodes": 4,
            "passive_relations": 0,
            "pending_status": "unknown",
        }
    finally:
        guala.shutdown()


def test_prediction_capacity_is_visible_without_rejecting_causal_settlement(
    monkeypatch,
    learned_artifacts,
) -> None:
    _reciprocity, trigger_artifacts, action_artifacts = learned_artifacts
    _trigger_built, _trigger_l5, _trigger_terminal, trigger = (
        trigger_artifacts
    )
    _action_built, _action_l5, _action_terminal, action = action_artifacts
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "prediction-capacity-key")
    guala = Guala()
    try:
        guala._record_causal_perception_without_dispatch(trigger)

        def capacity_full(_episode):
            raise RuntimeError("prediction_capacity_full")

        monkeypatch.setattr(
            guala._full_field_prediction,
            "observe_next",
            capacity_full,
        )
        guala._record_causal_perception_without_dispatch(
            action,
            prediction_transition=True,
        )

        assert guala._latest_causal_settlement == action
        assert guala._full_field_prediction.status()["active_context"] is False
        assert guala._latest_full_field_prediction_observation == {
            "reason": "prediction_capacity_full",
            "schema": "guala.full_field_prediction.engine_observation.v1",
            "settlement_receipt_sha256": action.authority_receipt_sha256,
            "status": "capacity_full",
        }
    finally:
        guala.shutdown()


def test_pre_execution_dispatch_failure_rolls_back_intent_and_prediction(
    monkeypatch,
    learned_artifacts,
) -> None:
    _reciprocity, trigger_artifacts, action_artifacts = learned_artifacts
    _trigger_built, _trigger_l5, trigger_terminal, trigger = (
        trigger_artifacts
    )
    _action_built, _action_l5, action_terminal, action = action_artifacts
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "dispatch-rollback-key")
    guala = Guala()
    try:
        guala._causal_action_cycle.accept(trigger)
        guala._causal_action_cycle.accept(action)
        guala.teach_causal_action(
            trigger_experience_id=trigger_terminal.event_id,
            action_experience_id=action_terminal.event_id,
            source="joe",
        )

        def fail_before_execution(*_args, **_kwargs):
            raise ValueError("injected pre-execution dispatch failure")

        monkeypatch.setattr(
            guala._causal_action_dispatcher,
            "dispatch_expected",
            fail_before_execution,
        )
        with pytest.raises(ValueError, match="pre-execution dispatch failure"):
            guala._accept_causal_settlement(trigger)

        assert guala._causal_action_dispatcher.status()["active"] is False
        assert guala._causal_action_cycle.status()["intents"] == 0
        assert guala._full_field_prediction.status()["armed_action"] is False
        assert guala._full_field_prediction.current_attempt().mode == "passive"
    finally:
        guala.shutdown()


def test_companion_vocal_pressure_enters_live_engine_as_binaural_w1_experience(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "companion-engine-key")
    guala = Guala()
    try:
        before = guala._embodiment_world.observation_snapshot()
        accepted_before = guala._causal_settlement_accepted

        result = guala.experience_companion_vocal_pressure(
            _companion_pcm_chunk()
        )

        after = guala._embodiment_world.observation_snapshot()
        assert result["sound_substream_count"] == 64
        assert result["world_revision_before"] == before.revision
        assert result["world_revision_after"] == before.revision + 1
        assert after.revision >= result["world_revision_after"]
        assert guala._causal_settlement_accepted == accepted_before + 1
        assert guala._latest_causal_settlement is not None
        assert result["causal_settlement_receipt_sha256"] == (
            guala._latest_causal_settlement.authority_receipt_sha256
        )
        assert result[
            "binaural_auditory_l5_authority_receipt_sha256"
        ] == (
            guala._w1_binaural_auditory_l5_owner.latest
            .authority_receipt_sha256
        )
        assert guala._w1_binaural_auditory_l5_owner.status()["settled"] == 1
        assert len(result[
            "anonymous_av_continuity_authority_receipt_sha256"
        ]) == 64
        assert guala._w1_anonymous_av_continuity_owner.status()[
            "settled"
        ] == 1
        assert guala._w1_companion_vocal_experience.status()[
            "retained_raw_media_bytes"
        ] == 0
        assert guala._w1_physical_evidence.status()["active_epochs"] == 0
    finally:
        guala.shutdown()


def test_companion_vocal_engine_failure_restores_world_and_causal_reservation(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "companion-rollback-key")
    guala = Guala()
    try:
        world_before = guala._embodiment_world.encoded_snapshot()
        accepted_before = guala._causal_settlement_accepted

        def fail_record(*_args, **_kwargs):
            raise RuntimeError("injected companion recording failure")

        monkeypatch.setattr(
            guala,
            "_record_causal_perception_without_dispatch",
            fail_record,
        )
        with pytest.raises(RuntimeError, match="recording failure"):
            guala.experience_companion_vocal_pressure(
                _companion_pcm_chunk()
            )

        assert guala._embodiment_world.encoded_snapshot() == world_before
        assert guala._causal_settlement_accepted == accepted_before
        assert guala._embodiment_outcome_causal_owner.status()[
            "prepared_reservation"
        ] == 0
        assert guala._w1_physical_evidence.status()["active_epochs"] == 0
        assert guala._w1_anonymous_av_continuity_owner.status()[
            "settled"
        ] == 0
    finally:
        guala.shutdown()


def test_companion_vocal_multiblock_episode_publishes_only_after_completion(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "companion-episode-key")
    guala = Guala()
    try:
        chunk = _companion_pcm_chunk()
        required_samples = (
            MAX_EMITTED_PCM_SAMPLES + MIN_EMITTED_PCM_SAMPLES
        )
        pcm = chunk * (
            (required_samples + len(chunk) // 2 - 1)
            // (len(chunk) // 2)
        )
        before = guala._embodiment_world.observation_snapshot()
        accepted_before = guala._causal_settlement_accepted

        result = guala.experience_companion_vocal_episode(pcm)

        assert result["block_count"] == 2
        assert result["total_sample_count"] == len(pcm) // 2
        assert result["world_revision_before"] == before.revision
        assert result["world_revision_after"] == before.revision + 2
        assert len(result["binaural_l5_authority_receipt_sha256s"]) == 2
        assert len(result[
            "anonymous_av_continuity_authority_receipt_sha256s"
        ]) == 2
        assert guala._causal_settlement_accepted == accepted_before
        assert guala._embodiment_outcome_causal_owner.status()["settled"] == 2
        assert guala._embodiment_outcome_causal_owner.status()[
            "atomic_sequence"
        ] == 0
        assert guala._w1_physical_evidence.status()["active_epochs"] == 0
        assert guala._w1_physical_evidence.status()["atomic_episode"] == 0
        assert guala._w1_anonymous_av_continuity_owner.status()[
            "settled"
        ] == 2
        assert guala._w1_companion_vocal_experience.status()[
            "has_latest_episode"
        ] is True
    finally:
        guala.shutdown()
