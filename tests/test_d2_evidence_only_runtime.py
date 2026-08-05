from __future__ import annotations

import io
import json
import math
import struct
import wave
from fractions import Fraction

import dsf_ai_service.app as app_module
from dsf_ai_service.glew_runtime.native_resident_organism import (
    create_native_resident_organism,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodimentWorldAuthority,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
)
from dsf_ai_service.substrate.w1_coupled_material_sensory_physics import (
    build_coupled_six_sense_full_field,
)
from dsf_ai_service.v4.guala_physical_runtime import (
    Guala,
    NATIVE_RESIDENT_ORGANISM_SCHEMA,
)


def _tone_wav() -> bytes:
    sample_rate = 16_000
    samples = tuple(
        int(8_000 * math.sin(2.0 * math.pi * 440.0 * index / sample_rate))
        for index in range(320)
    )
    result = io.BytesIO()
    with wave.open(result, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return result.getvalue()


def _configure_runtime(monkeypatch) -> None:
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "0123456789abcdef0123456789abcdef",
    )
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")


def test_sound_settlement_cold_restores_exact_resident_neuron_evidence(
    monkeypatch,
    tmp_path,
) -> None:
    _configure_runtime(monkeypatch)
    writer = Guala()
    reader = None
    try:
        writer.load_full_state(tmp_path, require_exact_binary=True)
        result = writer.process_sound_frame(
            _tone_wav(),
            source="browser_microphone",
            source_anchor_ns=1_000_000_003,
            source_time_end_ns=1_020_000_003,
            auditory_event_boundary="ambient",
        )
        observed = writer.native_resident_readiness()
        state = writer._native_resident_organism.save()

        assert result["accepted"] is True
        assert writer._causal_settlement_accepted == 1
        assert writer._causal_settlement_failed == 0
        assert observed["joint_field_count"] == 1
        assert observed["joint_neuron_count"] == 2 * len(AUDITORY_CHANNELS)
        assert observed["cognitive_trace_count"] == 1
        assert observed["cognitive_mosaic_count"] == 0
        assert state.startswith(b"GLORUN01")
        assert writer._native_materialized_fabric_state is None
        assert writer._native_materialized_fabric_reference is None

        writer.save_full_state(tmp_path, publish_generation=False)
        persisted = json.loads(
            (tmp_path / "guala_core.json").read_text(encoding="utf-8")
        )
        organism_state = persisted["data"]["organism_state"]
        assert organism_state["schema"] == NATIVE_RESIDENT_ORGANISM_SCHEMA
        assert set(organism_state) == {
            "native_resident_organism",
            "schema",
        }
        assert "native_materialized_fabric" not in json.dumps(persisted)

        writer.shutdown()
        reader = Guala()
        reader.load_full_state(tmp_path, require_exact_binary=True)
        restored = reader.native_resident_readiness()
        assert reader._native_resident_organism.save() == state
        assert restored["joint_neuron_count"] == observed["joint_neuron_count"]
        assert restored["cognitive_trace_count"] == 1
        assert restored["cognitive_mosaic_count"] == 0
    finally:
        writer.shutdown()
        if reader is not None:
            reader.shutdown()


def test_recurrence_forms_one_mosaic_then_stays_byte_bounded(
    monkeypatch,
    tmp_path,
) -> None:
    _configure_runtime(monkeypatch)
    organism = Guala()
    try:
        organism.load_full_state(tmp_path, require_exact_binary=True)
        sizes = []
        observations = []
        for occurrence in range(5):
            start = 3_000_000_003 + occurrence * 30_000_000
            result = organism.process_sound_frame(
                _tone_wav(),
                source="browser_microphone",
                source_anchor_ns=start,
                source_time_end_ns=start + 20_000_000,
                auditory_event_boundary="ambient",
            )
            observed = organism.native_resident_readiness()
            assert result["accepted"] is True
            assert observed["joint_neuron_count"] == 2 * len(
                AUDITORY_CHANNELS
            )
            sizes.append(observed["state_bytes"])
            observations.append(observed)

        assert organism._causal_settlement_accepted == 5
        assert organism._causal_settlement_failed == 0
        assert observations[0]["cognitive_trace_count"] == 1
        assert observations[0]["cognitive_mosaic_count"] == 0
        assert observations[1]["cognitive_trace_count"] == 0
        assert observations[1]["cognitive_mosaic_count"] == 1
        assert all(
            value["cognitive_mosaic_count"] == 1
            for value in observations[1:]
        )
        assert all(
            value["formation_activation_count"] == 1
            for value in observations[2:]
        )
        assert len(set(sizes[1:])) == 1
        assert organism._native_resident_organism.save().startswith(
            b"GLORUN01"
        )
        assert organism._native_materialized_fabric_state is None
    finally:
        organism.shutdown()


def test_virtual_material_and_body_senses_reach_resident_neurons() -> None:
    world = EmbodimentWorldAuthority(authority_key=b"d2-world-key" * 4)
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(MoveCommand(
            PoseMM(PositionMM(1_000, 1_200, 0), 0),
            200_000,
        )),
        causal_intent_receipt_sha256="a" * 64,
        expected_revision=before.revision,
    )
    built = build_coupled_six_sense_full_field(
        assembly_id="d2-virtual-material-body-occurrence",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, 5),
        world_authority=world,
        execution_receipt=execution,
    )
    states = {
        boundary.sense.value: boundary.state.value
        for boundary in built.boundary.boundaries
    }
    substream_counts = {
        boundary.sense.value: len(boundary.substreams)
        for boundary in built.boundary.boundaries
    }
    organism = create_native_resident_organism(
        organism_identity="12345678-9abc-4def-8123-456789abcdef",
        organism_tick=0,
        max_envelope_bytes=67_108_864,
        max_fabric_bytes=67_108_000,
        max_logical_peak_bytes=536_870_912,
    )
    prepared = organism.prepare(built.native_joint_source_episode)
    observed = organism.commit(prepared.token)

    assert states == {
        "body": "observed",
        "sight": "observed",
        "smell": "observed",
        "sound": "sensor_unavailable",
        "taste": "observed",
        "touch": "observed",
    }
    assert substream_counts == {
        "body": 4,
        "sight": 162,
        "smell": 8,
        "sound": 0,
        "taste": 5,
        "touch": 6,
    }
    assert observed.joint_field_count == 1
    assert observed.joint_neuron_count == sum(substream_counts.values()) == 185
    assert prepared.transitioned_fractal_count == 185
    assert observed.cognitive_trace_count == 1
    assert observed.cognitive_mosaic_count == 0
    assert observed.python_callback_count == 0


def test_retired_python_autonomy_is_truthfully_unavailable(monkeypatch) -> None:
    _configure_runtime(monkeypatch)
    organism = Guala()
    try:
        assert organism.start_autonomous_experience_driver() == {
            "lifecycle": "unavailable",
            "reason": "legacy_python_autonomy_retired",
            "schema": "guala.autonomous_experience.unavailable.v1",
        }
    finally:
        organism.shutdown()


def test_sealed_boot_does_not_require_retired_curriculum() -> None:
    source = app_module._embedded_post_boot.__code__
    constants = tuple(
        value for value in source.co_consts if isinstance(value, str)
    )
    assert not any(
        "curriculum is absent from the sealed production engine" in value
        for value in constants
    )
    assert any("native tutoring unavailable" in value for value in constants)
