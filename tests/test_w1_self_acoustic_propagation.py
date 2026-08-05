from __future__ import annotations

import math
from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryMotorResourceProfile,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorEventState,
    settle_auditory_receptor_event,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
    receptor_experience_from_full_field_event,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalMotorResourceProfile,
    SelfVocalPCMMotorOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidenceAuthority,
    W1BinauralGroundingResourceProfile,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_sound_field_inputs,
    body_from_snapshot,
    calibrated_ear_positions,
    render_ear_pressure,
)
import dsf_ai_service.substrate.w1_audiovisual_physical_evidence as external_evidence
import dsf_ai_service.substrate.w1_self_acoustic_propagation as self_acoustic
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticPropagationAuthority,
    W1SelfAcousticState,
)
from tests.test_articulatory_self_vocal_motor import _program


KEY = b"W1-self-acoustic-production-law-test-key"


def _modulated_tone_pcm(amplitude: int) -> bytes:
    sample_count = 3_200
    source_times = np.arange(sample_count) / REQUIRED_SAMPLE_RATE_HZ
    values = np.rint(
        amplitude
        * (0.55 + 0.4 * np.sin(2 * math.pi * 5 * source_times))
        * np.sin(2 * math.pi * 440 * source_times)
    ).astype("<i2")
    return values.tobytes()


def _mono_experience(pcm_s16le: bytes, occurrence: int):
    capture = transduce_auditory_full_field(
        np.frombuffer(pcm_s16le, dtype="<i2").astype(np.float64)
        / 32_768.0,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    source_start = Fraction(occurrence)
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"self-acoustic-motor-learning-{occurrence}",
        source_time_start=source_start,
        source_time_end=source_start + Fraction(
            capture.input_sample_count,
            REQUIRED_SAMPLE_RATE_HZ,
        ),
        observed_substreams={
            PhysicalSense.SOUND: auditory_kernel_component_inputs(
                capture,
                source_anchor=source_start,
            )
        },
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    auditory_l5 = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="utterance")
    assert auditory_l5 is not None
    boundary = settle_auditory_receptor_event(
        capture=capture,
        auditory_l5=auditory_l5,
    )
    assert boundary.state is AuditoryReceptorEventState.OBSERVED
    assert boundary.event is not None
    return (
        boundary.event,
        receptor_experience_from_full_field_event(boundary.event),
    )


def _motor():
    training_pcm = _modulated_tone_pcm(10_000)
    motor_pcm = _modulated_tone_pcm(11_000)
    mono_q = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="self-acoustic-mono-motor-proof",
            ear_count=1,
            max_motif_neurons=12_096,
            max_pending_experiences=8,
            max_work_cells_per_observation=4_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=64 * 1024 * 1024,
        )
    )
    _training_event, training = _mono_experience(training_pcm, 1)
    motor_event, motor_experience = _mono_experience(motor_pcm, 2)
    mono_q.observe(training)
    assert mono_q.observe(
        motor_experience
    ).newly_grown_motif_neuron_ids
    motor = SelfVocalPCMMotorOwner(
        authority_key=KEY,
        resource_profile=SelfVocalMotorResourceProfile.create(
            profile_id="self-acoustic-motor",
            max_exemplars=2,
            max_total_pcm_bytes=32 * 1024,
            max_state_bytes=128 * 1024,
        ),
    )
    exemplar = motor.admit_exemplar(
        pcm_s16le=motor_pcm,
        receptor_event=motor_event,
        receptor_experience=motor_experience,
        motif_owner=mono_q,
    )
    return motor, exemplar


def test_self_motor_pressure_reaches_two_ears_and_grows_recurrent_q():
    motor = ArticulatorySelfVocalMotorOwner(
        authority_key=KEY,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="self-acoustic-current-articulatory-motor",
            max_programs=2,
            max_state_bytes=256 * 1024,
        ),
    )
    program = motor.admit_program(_program(16_000))
    world = EmbodimentWorldAuthority(
        authority_key=b"W1-self-acoustic-world-test-key"
    )
    causal = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    binaural_q = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="W1-self-acoustic-binaural-proof",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )
    authority = W1SelfAcousticPropagationAuthority(
        authority_key=KEY,
        world_authority=world,
        causal_owner=causal,
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
        binaural_motif_owner=binaural_q,
    )

    mounts = []
    for intent_digit in ("1", "2", "3"):
        before = world.observation_snapshot()
        synthesis = motor.synthesize(
            program_id=program.program_id,
            source_time_start=Fraction(
                before.revision * MAX_VOCAL_SAMPLE_COUNT,
                VOCAL_SAMPLE_RATE_HZ,
            ),
        )
        prepared_emission = motor.prepare_generated_emission(
            synthesis=synthesis,
            world_authority=world,
            causal_intent_receipt_sha256=intent_digit * 64,
        )
        prepared_mount = authority.prepare_articulatory(
            prepared_emission,
            articulatory_owner=motor,
        )
        _emission, mount, _undo = (
            authority.commit_prepared_articulatory(prepared_mount)
        )
        mounts.append(mount)

    first, second, third = mounts
    assert (
        first.receipt.source_time_end
        < second.receipt.source_time_start
        < second.receipt.source_time_end
        < third.receipt.source_time_start
    )
    for mount in mounts:
        mount.verify(KEY)
        assert mount.receipt.state is W1SelfAcousticState.OBSERVED
        assert tuple(
            ear.ear_id for ear in mount.receptor_settlement.ears
        ) == ("left", "right")
        assert all(
            tuple(name for name, _value in field_tuple.fields)
            == DSF_FIELD_ORDER
            for ear in mount.binaural_l5.ears
            for channel in ear.channels
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            )
            for field_tuple in component.field_tuples
        )
        observed = {
            sense.sense: sense
            for sense in mount.causal_settlement.interpretations
            if sense.state == SenseBoundaryState.OBSERVED.value
        }
        assert set(observed) == {
            PhysicalSense.BODY.value,
            PhysicalSense.SIGHT.value,
            PhysicalSense.SOUND.value,
            PhysicalSense.TOUCH.value,
        }
        assert all(
            tuple(name for name, _value in field_tuple.fields)
            == DSF_FIELD_ORDER
            for sense in observed.values()
            for substream in sense.substreams
            for field_tuple in substream.field_tuples
        )
        assert mount.receipt.left_ear_position != (
            mount.receipt.right_ear_position
        )
        assert not hasattr(mount.receipt, "text")
        assert not hasattr(mount.receipt, "label")
    assert first.prelearning_firing.firing_motif_neuron_ids == ()
    assert second.observation.observation.newly_grown_motif_neuron_ids
    assert third.prelearning_firing.firing_motif_neuron_ids
    assert {
        activation.ear_id
        for activation in third.prelearning_firing.activations
    } == {"left", "right"}
    grounding_profile = W1BinauralGroundingResourceProfile.create(
        profile_id="self-sound-with-simultaneous-physical-field",
        max_activations=4_096,
        max_roots=256,
        max_evidence_bytes=32 * 1024 * 1024,
    )
    grounding = W1BinauralGroundingEvidenceAuthority(
        authority_key=KEY,
        resource_profile=grounding_profile,
    )
    evidence = grounding.admit(
        settlement=third.causal_settlement,
        receptor_settlement=third.receptor_settlement,
        firing=third.prelearning_firing,
        motif_owner=binaural_q,
    )
    evidence.verify(KEY, grounding_profile)

    encoded_world = world.encoded_snapshot()
    cold_world = EmbodimentWorldAuthority(
        authority_key=b"W1-self-acoustic-world-test-key"
    )
    cold_world.restore_encoded(encoded_world)
    cold_authority = W1SelfAcousticPropagationAuthority(
        authority_key=KEY,
        world_authority=cold_world,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
        binaural_motif_owner=binaural_q,
    )
    cold_before = cold_world.observation_snapshot()
    cold_synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=Fraction(
            cold_before.revision * MAX_VOCAL_SAMPLE_COUNT,
            VOCAL_SAMPLE_RATE_HZ,
        ),
    )
    cold_prepared_emission = motor.prepare_generated_emission(
        synthesis=cold_synthesis,
        world_authority=cold_world,
        causal_intent_receipt_sha256="4" * 64,
    )
    cold_prepared_mount = cold_authority.prepare_articulatory(
        cold_prepared_emission,
        articulatory_owner=motor,
    )
    _cold_emission, cold_mount, _cold_undo = (
        cold_authority.commit_prepared_articulatory(
            cold_prepared_mount
        )
    )
    cold_mount.verify(KEY)
    assert (
        cold_mount.receipt.source_time_start
        > third.receipt.source_time_end
    )

    with pytest.raises(
        ValueError,
        match="W1 self-acoustic receipt authority changed",
    ):
        replace(
            third.receipt,
            motor_id="0" * 64,
        ).verify(KEY)


def test_external_and_self_hearing_share_one_public_acoustic_law():
    assert external_evidence._body is body_from_snapshot
    assert external_evidence._ear_positions is calibrated_ear_positions
    assert external_evidence._render_ear is render_ear_pressure
    assert external_evidence._sound_inputs is binaural_sound_field_inputs
    assert self_acoustic.body_from_snapshot is body_from_snapshot
    assert (
        self_acoustic.calibrated_ear_positions
        is calibrated_ear_positions
    )
    assert self_acoustic.render_ear_pressure is render_ear_pressure
    assert (
        self_acoustic.binaural_sound_field_inputs
        is binaural_sound_field_inputs
    )
