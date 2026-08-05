from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    PPM,
    Q31,
    ArticulatoryMotorResourceProfile,
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
    ArticulatoryTravelingWaveState,
    LaryngealExcitationConfiguration,
    VocalTractConfiguration,
    generate_articulatory_pressure_with_quiescence,
    relax_articulatory_traveling_wave_state,
    signed_magnitude_truncating_wall_loss,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    EmbodiedBody,
    EmbodiedObject,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    PoseMM,
    PositionMM,
    VocalizeCommand,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_companion_articulatory_demonstration import (
    W1CompanionArticulatoryDemonstrationAuthority,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)


def _program(variant: int) -> ArticulatoryProgram:
    if variant == 0:
        initial = (90, 110, 150, 210, 280, 360, 470, 420)
        apex = (420, 90, 520, 120, 680, 160, 760, 980)
        final = (120, 150, 180, 240, 310, 390, 500, 520)
        peak = 14_000
    elif variant == 1:
        initial = (300, 250, 220, 190, 170, 210, 330, 860)
        apex = (100, 460, 140, 620, 180, 720, 240, 260)
        final = (360, 300, 260, 220, 190, 240, 380, 720)
        peak = 16_000
    else:
        initial = (90, 110, 150, 210, 280, 360, 470, 620)
        apex = (420, 90, 520, 120, 680, 160, 760, 620)
        final = initial
        peak = 14_000
    return ArticulatoryProgram.create(
        sample_count=3_200,
        larynx=LaryngealExcitationConfiguration(
            cycle_samples=80,
            open_samples=48,
            peak_volume_velocity_pcm=peak,
        ),
        tract=VocalTractConfiguration(
            initial_section_area_mm2=initial,
            apex_section_area_mm2=apex,
            final_section_area_mm2=final,
            radiation_load_area_mm2=900,
            wall_retention_ppm=990_000,
        ),
    )


def _system(
    *,
    capacity: int = 8,
    motor_key: bytes = b"m" * 32,
    companion_position: PositionMM = PositionMM(3_500, 2_500, 0),
):
    world = EmbodimentWorldAuthority(
        authority_key=b"w" * 32,
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                250,
                800,
            ),
            EmbodiedBody(
                "companion-body",
                PoseMM(companion_position, 180_000),
                200,
                600,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(SECOND_BODY_PORT_ID, "companion-body"),
        ),
        initial_objects=(
            EmbodiedObject(
                "object-1",
                radius_mm=100,
                mass_grams=500,
                position=PositionMM(1_500, 1_000, 0),
            ),
        ),
    )
    accepted = []
    causal = ExactCausalExperienceOwner(
        on_settlement=accepted.append,
        log_event=lambda *_args, **_kwargs: None,
    )
    motor = ArticulatorySelfVocalMotorOwner(
        authority_key=motor_key,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="external-articulator-test",
            max_programs=4,
            max_state_bytes=64 * 1024,
        ),
    )
    binaural_l5 = W1BinauralAuditoryL5Owner()
    authority = W1CompanionArticulatoryDemonstrationAuthority(
        authority_key=b"d" * 32,
        world_authority=world,
        causal_owner=causal,
        articulatory_owner=motor,
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=b"a" * 32,
            world_authority=world,
        ),
        binaural_l5_owner=binaural_l5,
        max_completed_demonstrations=capacity,
    )
    return world, causal, motor, binaural_l5, authority, accepted


def _settled_sense(result, sense: str):
    return next(
        value
        for value in result.causal_settlement.interpretations
        if value.sense == sense
    )


def test_wall_loss_extinguishes_both_prior_fixed_point_ghost_cycles_exactly():
    assert signed_magnitude_truncating_wall_loss(1, Q31 - 1) == 0
    assert signed_magnitude_truncating_wall_loss(-1, Q31 - 1) == 0

    neutral = (30, 130, 169, 191, 178, 216, 347, 201)
    ghost_states = (
        ArticulatoryTravelingWaveState(
            right_pressure=(0, 0, 0, 0, 1, 1, 0, 0),
            left_pressure=(0, 0, 0, 0, 0, 0, -1, -1),
            previous_glottal_flow=0,
        ),
        ArticulatoryTravelingWaveState(
            right_pressure=(0, 1, 0, 0, 1, 0, 0, -1),
            left_pressure=(2, 1, 0, 0, 0, 0, -1, -1),
            previous_glottal_flow=0,
        ),
    )
    for variant, ghost_state in enumerate(ghost_states):
        program = _program(variant)
        ghost_radiated, ghost_terminal = (
            relax_articulatory_traveling_wave_state(
                program=program,
                neutral_section_area_mm2=neutral,
                initial_state=ghost_state,
            )
        )
        assert ghost_radiated
        assert ghost_terminal.is_quiescent
        pressure = generate_articulatory_pressure_with_quiescence(
            program=program,
            neutral_section_area_mm2=neutral,
        )
        pressure.verify(program)
        assert pressure.quiescent_terminal_state.is_quiescent
        assert not any(
            pressure.quiescent_terminal_state.right_pressure
        )
        assert not any(
            pressure.quiescent_terminal_state.left_pressure
        )

    unity = _program(0)
    unity = ArticulatoryProgram.create(
        sample_count=unity.sample_count,
        larynx=unity.larynx,
        tract=replace(unity.tract, wall_retention_ppm=PPM),
    )
    with pytest.raises(ValueError, match="below unity"):
        generate_articulatory_pressure_with_quiescence(
            program=unity,
            neutral_section_area_mm2=neutral,
        )


def test_two_external_programs_common_cause_distinct_visible_and_binaural_fields():
    world, _causal, motor, _l5, authority, accepted = _system()
    programs = tuple(motor.admit_program(_program(index)) for index in (0, 1))

    first_synthesis = motor.synthesize(
        program_id=programs[0].program_id,
        source_time_start=authority.next_source_time_start,
    )
    first = authority.demonstrate(first_synthesis)
    second_synthesis = motor.synthesize(
        program_id=programs[1].program_id,
        source_time_start=authority.next_source_time_start,
    )
    second = authority.demonstrate(second_synthesis)

    assert accepted == []
    assert world.recent_applied_receipts()[-2].port_id == SECOND_BODY_PORT_ID
    assert world.recent_applied_receipts()[-1].port_id == SECOND_BODY_PORT_ID
    assert first.receipt.mouth_aperture_min_mm2 < (
        first.receipt.mouth_aperture_max_mm2
    )
    assert second.receipt.mouth_aperture_min_mm2 < (
        second.receipt.mouth_aperture_max_mm2
    )
    assert first.receipt.mouth_aperture_trajectory_sha256 != (
        second.receipt.mouth_aperture_trajectory_sha256
    )
    assert first.receipt.left_pressure_sha256 != (
        first.receipt.right_pressure_sha256
    )
    assert second.receipt.left_pressure_sha256 != (
        second.receipt.right_pressure_sha256
    )
    first_mouth = next(
        value
        for value in _settled_sense(first, "sight").substreams
        if value.substream_id == "visible-mouth-aperture-motion"
    )
    second_mouth = next(
        value
        for value in _settled_sense(second, "sight").substreams
        if value.substream_id == "visible-mouth-aperture-motion"
    )
    assert first_mouth.source_signal_commitment_sha256 != (
        second_mouth.source_signal_commitment_sha256
    )
    assert (
        ("optical-ray-forward-projective", "5")
        in first_mouth.coordinates
    )
    assert (
        ("optical-ray-lateral-projective", "3")
        in first_mouth.coordinates
    )
    assert _settled_sense(first, "sound").structural_fingerprint != (
        _settled_sense(second, "sound").structural_fingerprint
    )
    assert len(_settled_sense(first, "sound").substreams) == 64
    assert any(
        substream.substream_id == "visible-mouth-aperture-motion"
        for substream in _settled_sense(first, "sight").substreams
    )
    for result in (first, second):
        assert result.causal_settlement.language_events == ()
        assert result.causal_settlement.source_tags == ()
        assert result.causal_settlement.routing_chis == ()
        assert result.binaural_l5.upstream_causal_settlement_receipt_sha256 == (
            result.causal_settlement.authority_receipt_sha256
        )
        assert (
            result.binaural_receptor_settlement
            .upstream_causal_settlement_receipt_sha256
        ) == result.causal_settlement.authority_receipt_sha256
        assert result.binaural_receptor_settlement.upstream_w1_l5 == (
            result.binaural_l5
        )
        assert result.receipt.binaural_l5_receipt_sha256 == (
            result.binaural_l5.authority_receipt_sha256
        )
        assert (
            result.receipt
            .binaural_receptor_settlement_receipt_sha256
        ) == result.binaural_receptor_settlement.authority_receipt_sha256
        assert result.receipt.full_dsf_tuple_count > 0
        for sense in result.causal_settlement.interpretations:
            for substream in sense.substreams:
                for field_tuple in substream.field_tuples:
                    assert tuple(
                        name for name, _value in field_tuple.fields
                    ) == DSF_FIELD_ORDER
        authority.verify(result)
    assert authority.status() == {
        "completed": 2,
        "max_completed": 8,
        "next_source_sample": 7_360,
        "prepared": 0,
        "retained_raw_pcm_bytes": 0,
        "schema": "guala.w1.companion_articulation.status.v1",
    }


def test_continuous_rest_act_rest_keeps_two_programs_distinct_at_l2_l4(
    monkeypatch,
):
    from dsf_ai_service.substrate import (
        w1_companion_articulatory_demonstration as module,
    )

    built_fields = []
    original_build = module.build_transaction_owned_six_sense_full_field

    def capture_build(*args, **kwargs):
        built = original_build(*args, **kwargs)
        built_fields.append(built)
        return built

    monkeypatch.setattr(
        module,
        "build_transaction_owned_six_sense_full_field",
        capture_build,
    )
    _world, _causal, motor, _l5, authority, _accepted = _system()
    for variant in (0, 1):
        program = motor.admit_program(_program(variant))
        synthesis = motor.synthesize(
            program_id=program.program_id,
            source_time_start=authority.next_source_time_start,
        )
        result = authority.demonstrate(synthesis)
        assert result.receipt.pre_rest_sample_count == (
            OBSERVATION_HOP_SAMPLES
        )
        assert result.receipt.post_rest_sample_count >= (
            OBSERVATION_HOP_SAMPLES
        )

    def sound_basins(built):
        sound = next(
            boundary
            for boundary in built.boundary.boundaries
            if boundary.sense is PhysicalSense.SOUND
        )
        return tuple(
            substream.kernel_basin for substream in sound.substreams
        )

    first_basins, second_basins = (
        sound_basins(value) for value in built_fields
    )
    l2_distinct = False
    l4_distinct = False
    for first, second in zip(
        first_basins,
        second_basins,
        strict=True,
    ):
        first_trace = json.loads(
            built_fields[0].receipt_registry.resolve(
                first.exact_dsf_field_tuples[
                    0
                ].source_l0_l4_trace_receipt_sha256,
                "first continuous acoustic L0-L4 trace",
            )
        )
        second_trace = json.loads(
            built_fields[1].receipt_registry.resolve(
                second.exact_dsf_field_tuples[
                    0
                ].source_l0_l4_trace_receipt_sha256,
                "second continuous acoustic L0-L4 trace",
            )
        )
        l2_distinct = l2_distinct or (
            first_trace["L2_GateInterpretation"]
            != second_trace["L2_GateInterpretation"]
        )
        l4_distinct = l4_distinct or (
            first_trace["L4_DSF"] != second_trace["L4_DSF"]
        )
    assert l2_distinct
    assert l4_distinct

    def mouth_trace(built):
        sight = next(
            boundary
            for boundary in built.boundary.boundaries
            if boundary.sense is PhysicalSense.SIGHT
        )
        basin = next(
            substream.kernel_basin
            for substream in sight.substreams
            if substream.profile.substream_id
            == "visible-mouth-aperture-motion"
        )
        return json.loads(built.receipt_registry.resolve(
            basin.exact_dsf_field_tuples[
                0
            ].source_l0_l4_trace_receipt_sha256,
            "continuous mouth L0-L4 trace",
        ))

    first_mouth, second_mouth = (
        mouth_trace(value) for value in built_fields
    )
    assert first_mouth["L2_GateInterpretation"] != (
        second_mouth["L2_GateInterpretation"]
    )
    assert first_mouth["L4_DSF"] != second_mouth["L4_DSF"]


def test_exact_optical_ray_changes_field_without_changing_actuator_trajectory():
    left_system = _system(
        companion_position=PositionMM(3_500, 2_500, 0),
    )
    right_system = _system(
        companion_position=PositionMM(3_500, 500, 0),
    )
    results = []
    for _world, _causal, motor, _l5, authority, _accepted in (
        left_system,
        right_system,
    ):
        program = motor.admit_program(_program(0))
        synthesis = motor.synthesize(
            program_id=program.program_id,
            source_time_start=authority.next_source_time_start,
        )
        results.append(authority.demonstrate(synthesis))

    left_mouth = next(
        value
        for value in _settled_sense(results[0], "sight").substreams
        if value.substream_id == "visible-mouth-aperture-motion"
    )
    right_mouth = next(
        value
        for value in _settled_sense(results[1], "sight").substreams
        if value.substream_id == "visible-mouth-aperture-motion"
    )

    assert results[0].receipt.mouth_actuator_trajectory_sha256 == (
        results[1].receipt.mouth_actuator_trajectory_sha256
    )
    assert results[0].receipt.mouth_aperture_trajectory_sha256 != (
        results[1].receipt.mouth_aperture_trajectory_sha256
    )
    assert (
        ("optical-ray-forward-projective", "5")
        in left_mouth.coordinates
    )
    assert (
        ("optical-ray-lateral-projective", "3")
        in left_mouth.coordinates
    )
    assert (
        ("optical-ray-forward-projective", "5")
        in right_mouth.coordinates
    )
    assert (
        ("optical-ray-lateral-projective", "-1")
        in right_mouth.coordinates
    )
    assert left_mouth.source_signal_commitment_sha256 == (
        right_mouth.source_signal_commitment_sha256
    )
    assert _settled_sense(results[0], "sight").structural_fingerprint != (
        _settled_sense(results[1], "sight").structural_fingerprint
    )


def test_counterfactual_form_swap_changes_only_oracle_custody():
    _world, _causal, motor, _l5, authority, _accepted = _system()
    programs = tuple(motor.admit_program(_program(index)) for index in (0, 1))
    results = []
    for program in programs:
        synthesis = motor.synthesize(
            program_id=program.program_id,
            source_time_start=authority.next_source_time_start,
        )
        results.append(authority.demonstrate(synthesis))

    physical_receipts = tuple(
        value.receipt.authority_receipt_sha256 for value in results
    )
    oracle_first = {
        "uninterpreted-form-a": physical_receipts[0],
        "uninterpreted-form-b": physical_receipts[1],
    }
    oracle_swapped = {
        "uninterpreted-form-a": physical_receipts[1],
        "uninterpreted-form-b": physical_receipts[0],
    }

    assert oracle_first != oracle_swapped
    assert tuple(
        value.receipt.authority_receipt_sha256 for value in results
    ) == physical_receipts
    for result in results:
        serialized = str(result.receipt.payload()).lower()
        for prohibited in (
            "program_id",
            "target",
            "tutor",
            "transcript",
            "label",
            "atlas",
        ):
            assert prohibited not in serialized


def test_modified_or_foreign_synthesis_fails_before_world_execution():
    world, _causal, motor, _l5, authority, accepted = _system()
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    changed_pcm = bytearray(synthesis.radiated_pcm_s16le)
    changed_pcm[-1] ^= 1
    modified = replace(
        synthesis,
        radiated_pcm_s16le=bytes(changed_pcm),
    )
    world_before = world.encoded_snapshot()

    with pytest.raises(
        ValueError,
        match="synthesis changed physical state",
    ):
        authority.demonstrate(modified)

    foreign_motor = ArticulatorySelfVocalMotorOwner(
        authority_key=b"f" * 32,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="foreign-external-articulator-test",
            max_programs=2,
            max_state_bytes=64 * 1024,
        ),
    )
    foreign = foreign_motor.admit_program(_program(1))
    foreign_synthesis = foreign_motor.synthesize(
        program_id=foreign.program_id,
        source_time_start=authority.next_source_time_start,
    )
    with pytest.raises(ValueError):
        authority.demonstrate(foreign_synthesis)

    assert world.encoded_snapshot() == world_before
    assert accepted == []
    assert authority.status()["retained_raw_pcm_bytes"] == 0


def test_authenticated_cold_state_preserves_replay_and_source_clock():
    world, causal, motor, l5, authority, accepted = _system()
    first_program = motor.admit_program(_program(0))
    first_synthesis = motor.synthesize(
        program_id=first_program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    authority.demonstrate(first_synthesis)
    authority_state = authority.snapshot_encoded()
    l5_state = l5.encoded_snapshot()

    restored_l5 = W1BinauralAuditoryL5Owner()
    restored_l5.restore_encoded(l5_state)
    restored = W1CompanionArticulatoryDemonstrationAuthority(
        authority_key=b"d" * 32,
        world_authority=world,
        causal_owner=causal,
        articulatory_owner=motor,
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=b"a" * 32,
            world_authority=world,
        ),
        binaural_l5_owner=restored_l5,
        max_completed_demonstrations=8,
    )
    restored.restore_encoded(authority_state)

    with pytest.raises(ValueError, match="replayed"):
        restored.demonstrate(first_synthesis)
    assert restored.next_source_time_start == Fraction(6, 25)
    second_program = motor.admit_program(_program(1))
    second_synthesis = motor.synthesize(
        program_id=second_program.program_id,
        source_time_start=restored.next_source_time_start,
    )
    second = restored.demonstrate(second_synthesis)

    assert second.receipt.source_sample_start == 3_680
    assert second.receipt.source_sample_end == 7_360
    assert restored.status()["retained_raw_pcm_bytes"] == 0
    assert accepted == []


def test_static_mouth_stale_clock_replay_and_capacity_are_rejected():
    world, _causal, motor, _l5, authority, accepted = _system(capacity=1)
    static_program = motor.admit_program(_program(2))
    static_synthesis = motor.synthesize(
        program_id=static_program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    world_before = world.encoded_snapshot()
    with pytest.raises(ValueError, match="static mouth"):
        authority.demonstrate(static_synthesis)
    assert world.encoded_snapshot() == world_before

    moving_program = motor.admit_program(_program(0))
    stale = motor.synthesize(
        program_id=moving_program.program_id,
        source_time_start=Fraction(1),
    )
    with pytest.raises(ValueError, match="source clock"):
        authority.demonstrate(stale)
    assert world.encoded_snapshot() == world_before

    synthesis = motor.synthesize(
        program_id=moving_program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    authority.demonstrate(synthesis)
    committed = world.encoded_snapshot()
    with pytest.raises(ValueError, match="replayed"):
        authority.demonstrate(synthesis)
    assert world.encoded_snapshot() == committed

    second_program = motor.admit_program(_program(1))
    second = motor.synthesize(
        program_id=second_program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    with pytest.raises(ValueError, match="capacity"):
        authority.demonstrate(second)
    assert accepted == []


def test_self_port_and_resolvable_identical_ears_are_rejected(monkeypatch):
    world, causal, motor, _l5, _authority, accepted = _system()
    emitter = W1AcousticEmitterAuthority(
        authority_key=b"a" * 32,
        world_authority=world,
    )
    with pytest.raises(ValueError, match="real companion port"):
        W1CompanionArticulatoryDemonstrationAuthority(
            authority_key=b"d" * 32,
            world_authority=world,
            causal_owner=causal,
            articulatory_owner=motor,
            acoustic_emitter=emitter,
            binaural_l5_owner=W1BinauralAuditoryL5Owner(),
            companion_port_id=PORT_ID,
        )

    authority = W1CompanionArticulatoryDemonstrationAuthority(
        authority_key=b"e" * 32,
        world_authority=world,
        causal_owner=causal,
        articulatory_owner=motor,
        acoustic_emitter=emitter,
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
    )
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    world_before = world.encoded_snapshot()

    from dsf_ai_service.substrate import (
        w1_companion_articulatory_demonstration as module,
    )

    original = module.render_ear_pressure
    first_result = None
    calls = 0

    def identical_render(*args, **kwargs):
        nonlocal first_result, calls
        calls += 1
        rendered = original(*args, **kwargs)
        if calls == 1:
            first_result = rendered
            return rendered
        assert first_result is not None
        return (
            first_result[0],
            first_result[1],
            first_result[2],
            rendered[3],
            rendered[4] + 1,
            rendered[5],
        )

    monkeypatch.setattr(module, "render_ear_pressure", identical_render)
    with pytest.raises(ValueError, match="identical pressure"):
        authority.demonstrate(synthesis)

    assert world.encoded_snapshot() == world_before
    assert accepted == []


def test_companion_outside_exact_articulator_retinal_cone_is_rejected():
    world, _causal, motor, _l5, authority, accepted = _system(
        companion_position=PositionMM(1_500, 3_000, 0),
    )
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    world_before = world.encoded_snapshot()

    with pytest.raises(ValueError, match="admitted retinal cone"):
        authority.demonstrate(synthesis)

    assert world.encoded_snapshot() == world_before
    assert accepted == []
    assert authority.status()["completed"] == 0


def test_prepared_full_field_failure_discards_world_without_restore(
    monkeypatch,
):
    world, causal, motor, l5, authority, accepted = _system()
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    before = world.encoded_snapshot()

    def forbid_restore(_encoded):
        raise AssertionError("prepared physical failure attempted restore")

    def fail_settlement(*_args, **_kwargs):
        raise RuntimeError("injected full-field boundary failure")

    monkeypatch.setattr(world, "restore_encoded", forbid_restore)
    monkeypatch.setattr(causal, "settle", fail_settlement)
    with pytest.raises(RuntimeError, match="full-field boundary failure"):
        authority.demonstrate(synthesis)

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert causal.status()["atomic_sequence"] == 0
    assert causal.status()["prepared_reservation"] == 0
    assert l5.status()["atomic_sequence"] == 0
    assert l5.status()["prepared"] == 0
    assert authority.status()["completed"] == 0
    assert authority.status()["next_source_sample"] == 0
    assert authority.status()["prepared"] == 0
    assert authority._emitter.status()["prepared"] == 0


def test_final_world_commit_failure_rolls_back_published_causal_and_l5(
    monkeypatch,
):
    world, causal, motor, l5, authority, accepted = _system()
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    before = world.encoded_snapshot()

    def fail_world_commit(_prepared):
        raise RuntimeError("injected final world commit failure")

    monkeypatch.setattr(
        world,
        "commit_prepared_action",
        fail_world_commit,
    )
    with pytest.raises(RuntimeError, match="final world commit failure"):
        authority.demonstrate(synthesis)

    assert world.encoded_snapshot() == before
    assert world.recent_applied_receipts() == ()
    assert accepted == []
    assert causal.status()["settled"] == 0
    assert causal.status()["atomic_sequence"] == 0
    assert causal.status()["prepared_reservation"] == 0
    assert l5.status()["settled"] == 0
    assert l5.status()["atomic_sequence"] == 0
    assert l5.status()["prepared"] == 0
    assert authority.status()["completed"] == 0
    assert authority.status()["next_source_sample"] == 0
    assert authority.status()["prepared"] == 0
    assert authority._emitter.status()["prepared"] == 0


def test_l5_publication_failure_rolls_back_prior_causal_publication(
    monkeypatch,
):
    world, causal, motor, l5, authority, accepted = _system()
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    before = world.encoded_snapshot()

    def fail_l5_publish(_token):
        raise RuntimeError("injected L5 publication failure")

    monkeypatch.setattr(l5, "commit_atomic_sequence", fail_l5_publish)
    with pytest.raises(RuntimeError, match="L5 publication failure"):
        authority.demonstrate(synthesis)

    assert world.encoded_snapshot() == before
    assert accepted == []
    assert causal.status()["settled"] == 0
    assert causal.status()["atomic_sequence"] == 0
    assert l5.status()["settled"] == 0
    assert l5.status()["atomic_sequence"] == 0
    assert authority.status()["completed"] == 0


def test_prepared_emitter_has_no_final_emission_and_rejects_copies(
    monkeypatch,
):
    world, _causal, motor, _l5, authority, _accepted = _system()
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    emitter = authority._emitter
    original_commit = emitter.commit_prepared_emission
    observed = {}

    def inspect_and_commit(prepared):
        observed["prepared"] = prepared
        assert not hasattr(prepared, "_staged_emission")
        assert not any(
            isinstance(getattr(prepared, name), AuthenticatedW1AcousticEmission)
            for name in prepared.__slots__
        )
        with pytest.raises(ValueError, match="changed custody"):
            emitter.verify_prepared_emission(replace(prepared))
        return original_commit(prepared)

    monkeypatch.setattr(
        emitter,
        "commit_prepared_emission",
        inspect_and_commit,
    )
    authority.demonstrate(synthesis)

    prepared = observed["prepared"]
    assert emitter.status()["prepared"] == 0
    with pytest.raises(ValueError, match="changed custody"):
        emitter.verify_prepared_emission(prepared)
    with pytest.raises(ValueError, match="changed custody"):
        emitter.discard_prepared_emission(prepared)
    assert world.status()["prepared_action_execution"] == 0


def test_discarded_prepared_emitter_capability_is_permanently_stale():
    world, _causal, motor, _l5, authority, _accepted = _system()
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    emitter = authority._emitter
    epoch_token = "prepared-external-emission-test-epoch"
    before = world.observation_snapshot()
    command = VocalizeCommand(
        epoch_commitment_sha256=hashlib.sha256(
            epoch_token.encode("utf-8")
        ).hexdigest(),
        sequence=before.revision,
        source_sample_start=OBSERVATION_HOP_SAMPLES,
        pcm_sha256=hashlib.sha256(
            synthesis.radiated_pcm_s16le
        ).hexdigest(),
        sample_count=synthesis.program.sample_count,
    )
    command_payload = encode_command(command)
    prepared_world = world.prepare_port_command(
        port_id=SECOND_BODY_PORT_ID,
        command_payload=command_payload,
        causal_intent_receipt_sha256="9" * 64,
        expected_revision=before.revision,
    )
    prepared = emitter.prepare_emission(
        epoch_token=epoch_token,
        sequence=before.revision,
        source_sample_start=OBSERVATION_HOP_SAMPLES,
        prepared_world_action=prepared_world,
        command_payload=command_payload,
        emitter_port_id=SECOND_BODY_PORT_ID,
        pcm_s16le=synthesis.radiated_pcm_s16le,
    )

    emitter.discard_prepared_emission(prepared)

    assert emitter.status()["prepared"] == 0
    with pytest.raises(ValueError, match="changed custody"):
        emitter.verify_prepared_emission(prepared)
    with pytest.raises(ValueError, match="changed custody"):
        emitter.commit_prepared_emission(prepared)
    with pytest.raises(ValueError, match="changed custody"):
        emitter.discard_prepared_emission(prepared)
    world.discard_prepared_action(prepared_world)


def test_world_commit_is_last_after_bookkeeping_and_emitter_publication(
    monkeypatch,
):
    world, _causal, motor, _l5, authority, _accepted = _system()
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    order = []
    emitter = authority._emitter
    original_emitter_commit = emitter.commit_prepared_emission
    original_world_commit = world.commit_prepared_action

    def emitter_commit(prepared):
        order.append("emitter")
        return original_emitter_commit(prepared)

    def world_commit(prepared):
        order.append("world")
        state = authority.status()
        assert state["completed"] == 1
        assert state["next_source_sample"] == 3_680
        assert state["prepared"] == 1
        assert emitter.status()["prepared"] == 0
        return original_world_commit(prepared)

    monkeypatch.setattr(
        emitter,
        "commit_prepared_emission",
        emitter_commit,
    )
    monkeypatch.setattr(world, "commit_prepared_action", world_commit)

    authority.demonstrate(synthesis)

    assert order == ["emitter", "world"]


def test_cleanup_failure_is_surfaced_and_cannot_be_saved_as_complete(
    monkeypatch,
):
    world, causal, motor, _l5, authority, _accepted = _system()
    program = motor.admit_program(_program(0))
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=authority.next_source_time_start,
    )
    emitter = authority._emitter
    original_world_discard = world.discard_prepared_action
    world_discarded = []

    def fail_settlement(*_args, **_kwargs):
        raise RuntimeError("injected settlement failure")

    def fail_emitter_discard(_prepared):
        raise RuntimeError("injected emitter cleanup failure")

    def record_world_discard(prepared):
        world_discarded.append(prepared)
        return original_world_discard(prepared)

    monkeypatch.setattr(causal, "settle", fail_settlement)
    monkeypatch.setattr(
        emitter,
        "discard_prepared_emission",
        fail_emitter_discard,
    )
    monkeypatch.setattr(
        world,
        "discard_prepared_action",
        record_world_discard,
    )

    with pytest.raises(
        ExceptionGroup,
        match="cleanup failed",
    ) as captured:
        authority.demonstrate(synthesis)

    assert "injected settlement failure" in str(
        captured.value.exceptions[0]
    )
    assert any(
        "injected emitter cleanup failure" in str(error)
        for error in captured.value.exceptions[1:]
    )
    assert len(world_discarded) == 1
    assert world.status()["prepared_action_execution"] == 0
    assert authority.status()["prepared"] == 1
    with pytest.raises(
        RuntimeError,
        match="cold authorities diverged",
    ):
        authority.snapshot_encoded()
    with pytest.raises(
        RuntimeError,
        match="stranded prepared state",
    ):
        authority.demonstrate(synthesis)
