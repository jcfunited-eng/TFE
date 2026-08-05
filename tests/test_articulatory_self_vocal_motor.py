from __future__ import annotations

import hashlib
import hmac
import json
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
)
from dsf_ai_service.substrate import articulatory_self_vocal_motor as module
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ARTICULATORY_STATE_SCHEMA,
    ArticulatoryCapacityError,
    ArticulatoryMotorResourceProfile,
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
    LaryngealExcitationConfiguration,
    VocalTractConfiguration,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
)


KEY = b"articulatory-self-vocal-production-test-key"


def _program(
    peak: int = 14_000,
    *,
    sample_count: int = 3_200,
) -> ArticulatoryProgram:
    return ArticulatoryProgram.create(
        sample_count=sample_count,
        larynx=LaryngealExcitationConfiguration(
            cycle_samples=80,
            open_samples=48,
            peak_volume_velocity_pcm=peak,
        ),
        tract=VocalTractConfiguration(
            initial_section_area_mm2=(
                90, 110, 150, 210, 280, 360, 470, 620
            ),
            apex_section_area_mm2=(
                420, 90, 520, 120, 680, 160, 760, 240
            ),
            final_section_area_mm2=(
                90, 110, 150, 210, 280, 360, 470, 620
            ),
            radiation_load_area_mm2=900,
            wall_retention_ppm=990_000,
        ),
    )


def _owner(max_programs: int = 4) -> ArticulatorySelfVocalMotorOwner:
    return ArticulatorySelfVocalMotorOwner(
        authority_key=KEY,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="physical-articulatory-v2",
            max_programs=max_programs,
            max_state_bytes=64 * 1024,
        ),
    )


def test_v2_synthesis_is_deterministic_transient_and_full_field():
    owner = _owner()
    first_program = owner.admit_program(_program())
    second_program = owner.admit_program(_program(16_000))
    retained = owner.snapshot_encoded()

    first = owner.synthesize(
        program_id=first_program.program_id,
        source_time_start=Fraction(1),
    )
    repeated = owner.synthesize(
        program_id=first_program.program_id,
        source_time_start=Fraction(2),
    )
    distinct = owner.synthesize(
        program_id=second_program.program_id,
        source_time_start=Fraction(3),
    )

    assert first.radiated_pcm_s16le == repeated.radiated_pcm_s16le
    assert first.excitation_pcm_s16le == repeated.excitation_pcm_s16le
    assert first.radiated_pcm_s16le != distinct.radiated_pcm_s16le
    assert first.excitation_pcm_s16le != distinct.excitation_pcm_s16le
    assert owner.snapshot_encoded() == retained
    owner.verify_synthesis(first)

    partitions = first.actuator_full_field_assembly.partitions
    assert tuple(
        (value.sample_start, value.sample_end)
        for value in partitions
    ) == ((0, 2_048), (2_048, 3_200))
    assert all(
        all(
            isinstance(getattr(field_tuple, name), Fraction)
            for name in DSF_FIELD_ORDER
        )
        for partition in partitions
        for boundary in partition.full_field.boundary.boundaries
        if boundary.sense is PhysicalSense.BODY
        for substream in boundary.substreams
        for field_tuple in substream.kernel_basin.exact_dsf_field_tuples
    )
    assert all(
        len(body.substreams) == 9
        for partition in partitions
        for body in partition.full_field.boundary.boundaries
        if body.sense is PhysicalSense.BODY
    )


def test_v2_state_retains_only_profile_and_programs():
    owner = _owner()
    program = owner.admit_program(_program())
    encoded = owner.snapshot_encoded()
    envelope = json.loads(encoded)
    assert set(envelope["body"]) == {
        "programs",
        "resource_profile",
        "schema",
    }
    assert envelope["body"]["schema"] == ARTICULATORY_STATE_SCHEMA
    assert "pcm_s16le" not in encoded.decode("utf-8")
    status = owner.status()
    assert status["retained_pcm_bytes"] == 0
    assert status["retained_cursor_bytes"] == 0
    assert status["retained_binding_count"] == 0

    restored = ArticulatorySelfVocalMotorOwner.restore_encoded(
        authority_key=KEY,
        encoded=encoded,
    )
    assert restored.programs == (program,)
    assert restored.snapshot_encoded() == encoded


def test_live_owner_rejects_authenticated_v1_and_restores_current_empty():
    owner = _owner()
    current = owner.snapshot_encoded()
    restored = ArticulatorySelfVocalMotorOwner.restore_encoded(
        authority_key=KEY,
        encoded=current,
    )
    assert restored.programs == ()
    assert restored.snapshot_encoded() == current

    current_body = json.loads(current)["body"]
    legacy_body = {
        "next_program_index": 0,
        "programs": [],
        "resource_profile": current_body["resource_profile"],
        "schema": "guala.articulatory_motor.state.v1",
        "thing_program_bindings": [{"authenticated_legacy": True}],
    }
    legacy_domain = b"guala-articulatory-state-v1\0"
    root = hashlib.sha256(KEY).digest()
    legacy_key = hashlib.sha256(legacy_domain + root).digest()
    canonical_body = json.dumps(
        legacy_body,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    legacy_envelope = {
        "body": legacy_body,
        "schema": "guala.articulatory_motor.state_hmac.v1",
        "state_hmac_sha256": hmac.new(
            legacy_key,
            legacy_domain + canonical_body,
            hashlib.sha256,
        ).hexdigest(),
    }
    legacy = json.dumps(
        legacy_envelope,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="body changed"):
        ArticulatorySelfVocalMotorOwner.restore_encoded(
            authority_key=KEY,
            encoded=legacy,
        )

    owner.admit_program(_program())
    static_envelope = json.loads(owner.snapshot_encoded())
    static_program = static_envelope["body"]["programs"][0]
    static_program.pop("body_trajectory")
    static_program["schema"] = "guala.articulatory_motor.program.v1"
    static_body = static_envelope["body"]
    canonical_static_body = json.dumps(
        static_body,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    state_domain = b"guala-articulatory-state-v2\0"
    state_key = hashlib.sha256(
        state_domain + hashlib.sha256(KEY).digest()
    ).digest()
    static_envelope["state_hmac_sha256"] = hmac.new(
        state_key,
        state_domain + canonical_static_body,
        hashlib.sha256,
    ).hexdigest()
    authenticated_static = json.dumps(
        static_envelope,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="program record changed"):
        ArticulatorySelfVocalMotorOwner.restore_encoded(
            authority_key=KEY,
            encoded=authenticated_static,
        )


def test_v2_rejects_tampering_and_program_capacity_exhaustion():
    owner = _owner(max_programs=1)
    owner.admit_program(_program())
    with pytest.raises(ArticulatoryCapacityError):
        owner.admit_program(_program(16_000))

    damaged = bytearray(owner.snapshot_encoded())
    damaged[-10] ^= 1
    with pytest.raises(ValueError):
        ArticulatorySelfVocalMotorOwner.restore_encoded(
            authority_key=KEY,
            encoded=bytes(damaged),
        )


def test_legacy_motor_custody_and_policy_surfaces_are_absent():
    owner = _owner()
    for name in (
        "thing_program_bindings",
        "claim_next_babble_program",
        "verify_thing_program_binding",
        "bind_thing_program",
        "bind_pcm_exemplar",
        "bridge_existing_pcm_exemplar",
        "hear_synthesis",
        "verify_bridge",
        "close_self_acoustic_custody",
        "verify_self_acoustic_custody",
    ):
        assert not hasattr(owner, name)
    for name in (
        "ArticulatoryThingProgramBinding",
        "ArticulatoryMonoHearing",
        "ArticulatoryPCMBridge",
        "ArticulatorySelfAcousticReceipt",
        "ArticulatorySelfAcousticCustody",
    ):
        assert not hasattr(module, name)


def test_word_length_and_world_vocal_sample_bound_are_identical():
    word_length = _program(sample_count=24_800)
    exact_world_bound = _program(
        sample_count=MAX_VOCAL_SAMPLE_COUNT
    )

    assert word_length.sample_count == 24_800
    assert exact_world_bound.sample_count == MAX_VOCAL_SAMPLE_COUNT
    assert module.MAX_ARTICULATORY_SAMPLES == MAX_VOCAL_SAMPLE_COUNT
    with pytest.raises(ValueError, match="sample count"):
        _program(sample_count=MAX_VOCAL_SAMPLE_COUNT + 1)


def test_word_length_pressure_is_transient_and_owner_state_stays_bounded():
    owner = _owner()
    retained = owner.snapshot_encoded()
    program = _program(sample_count=24_800)

    pressure = module.generate_articulatory_pressure_with_quiescence(
        program=program,
        neutral_section_area_mm2=(
            program.tract.final_section_area_mm2
        ),
    )

    assert len(pressure.active_radiated_pressure_pcm) == 24_800
    assert pressure.quiescent_terminal_state.is_quiescent
    assert owner.snapshot_encoded() == retained
    assert owner.status()["retained_pcm_bytes"] == 0
