from __future__ import annotations

import math
import json
from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    AuditoryMotifCausalGroundingOwner,
    AuditoryMotifGroundingResourceProfile,
    GroundingResolution,
    GroundingResolutionState,
    ResolvedGroundedReferent,
    _roots_from_settlement,
)
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
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.grounded_turn_conversation import (
    GroundedTurnConstructionState,
    GroundedTurnConversationOwner,
    GroundedTurnResourceProfile,
    cue_from_resolution,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalMotorResourceProfile,
    SelfVocalPCMMotorOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.w1_grounded_demonstration import (
    W1GroundedDemonstrationOwner,
    W1GroundedDemonstrationProfile,
)
from tests.native_joint_occurrence_support import joint_occurrences_for


KEY = b"self-vocal-grounded-conversation-test-key"


def _modulated_tone_pcm(amplitude: int) -> bytes:
    sample_count = 3200
    source_times = np.arange(sample_count) / REQUIRED_SAMPLE_RATE_HZ
    values = np.rint(
        amplitude
        * (
            0.55
            + 0.4 * np.sin(2 * math.pi * 5 * source_times)
        )
        * np.sin(
            2
            * math.pi
            * 440
            * source_times
        )
    ).astype("<i2")
    return values.tobytes()


def _tone_pcm() -> bytes:
    return _modulated_tone_pcm(11_000)


def _heard_pcm(
    pcm_s16le: bytes,
    occurrence: int,
    *,
    source_anchor: Fraction | None = None,
):
    capture = transduce_auditory_full_field(
        np.frombuffer(pcm_s16le, dtype="<i2").astype(np.float64)
        / 32768.0,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    if source_anchor is None:
        source_anchor = Fraction(occurrence)
    components = auditory_kernel_component_inputs(
        capture,
        source_anchor=source_anchor,
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"self-vocal-hearing-{occurrence}",
        source_time_start=source_anchor,
        source_time_end=source_anchor + Fraction(
            capture.input_sample_count,
            REQUIRED_SAMPLE_RATE_HZ,
        ),
        observed_substreams={PhysicalSense.SOUND: components}, occurrences=joint_occurrences_for({PhysicalSense.SOUND: components}),
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
    experience = receptor_experience_from_full_field_event(
        boundary.event
    )
    return boundary.event, experience


def _visual_settlement(assembly_id: str):
    count = 96
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="conversation-camera",
        substream_id="grounded-object-provenance-only",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("reference-frame", "body-centered"),
            NativeAxisCoordinate("object-identity", assembly_id),
        ),
        physical_quantity="light-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(
            Fraction(index, 200) for index in range(count)
        ),
        normalized_signal=tuple(
            math.sin(2 * math.pi * 8 * index / 200)
            for index in range(count)
        ),
        phase_turns=tuple(
            Fraction(index // 12) for index in range(count)
        ),
    )
    built = build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        observed_substreams={PhysicalSense.SIGHT: (sight,)}, occurrences=joint_occurrences_for({PhysicalSense.SIGHT: (sight,)}),
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SIGHT
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )


def _motor_fixture():
    pcm = _tone_pcm()
    motif_owner = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="self-vocal-tone-motif",
            ear_count=1,
            max_motif_neurons=12_096,
            max_pending_experiences=8,
            max_work_cells_per_observation=500_000,
            max_exact_fraction_text_bytes=4096,
            encoded_state_allocation_bytes=16 * 1024 * 1024,
        )
    )
    first_event, first = _heard_pcm(
        _modulated_tone_pcm(10_000),
        1,
    )
    second_event, second = _heard_pcm(pcm, 2)
    assert not set(first.source_event_receipt_sha256s).intersection(
        second.source_event_receipt_sha256s
    )
    motif_owner.observe(first)
    grown = motif_owner.observe(second)
    assert grown.newly_grown_motif_neuron_ids
    motor_owner = SelfVocalPCMMotorOwner(
        authority_key=KEY,
        resource_profile=SelfVocalMotorResourceProfile.create(
            profile_id="focused-self-vocal-motor",
            max_exemplars=4,
            max_total_pcm_bytes=64 * 1024,
            max_state_bytes=256 * 1024,
        ),
    )
    exemplar = motor_owner.admit_exemplar(
        pcm_s16le=pcm,
        receptor_event=second_event,
        receptor_experience=second,
        motif_owner=motif_owner,
    )
    return pcm, motif_owner, motor_owner, exemplar


def test_self_vocal_pcm_is_executed_by_self_body_and_self_heard() -> None:
    pcm, motif_owner, motor_owner, exemplar = _motor_fixture()
    world = EmbodimentWorldAuthority(
        authority_key="self-vocal-world-authority"
    )
    prepared = motor_owner.execute(
        motor_id=exemplar.motor_id,
        world_authority=world,
        causal_intent_receipt_sha256="1" * 64,
    )
    heard_event, heard_experience = _heard_pcm(pcm, 3)
    hearing = motor_owner.close_self_hearing(
        emission=prepared,
        receptor_event=heard_event,
        receptor_experience=heard_experience,
        motif_owner=motif_owner,
    )

    assert prepared.execution_receipt.actor_body_id == (
        prepared.execution_receipt.before.self_body_id
    )
    assert hearing.motor_id == exemplar.motor_id
    assert hearing.firing_motif_neuron_ids == (
        exemplar.firing_motif_neuron_ids
    )
    assert not hasattr(exemplar, "text")
    assert not hasattr(exemplar, "label")
    encoded = motor_owner.snapshot_encoded()
    restored = SelfVocalPCMMotorOwner.restore_encoded(
        authority_key=KEY,
        encoded=encoded,
    )
    restored.cross_validate_restored(motif_owner=motif_owner)
    assert restored.snapshot_encoded() == encoded
    assert restored.exemplars == motor_owner.exemplars


def test_two_lived_grounded_turns_release_only_learned_pcm_motor() -> None:
    pcm, motif_owner, motor_owner, exemplar = _motor_fixture()
    world = EmbodimentWorldAuthority(
        authority_key="grounded-turn-world-authority"
    )
    prompt_one = _visual_settlement("prompt-one")
    prompt_two = _visual_settlement("prompt-two")
    physical_root = next(
        value for value in _roots_from_settlement(prompt_one)
        if json.loads(value.value_json)["field_tuples"]
    )
    prompt_event, prompt_experience = _heard_pcm(
        pcm,
        10,
        source_anchor=Fraction(0),
    )
    firing = motif_owner.fire(prompt_experience)
    assert firing.activations
    resolution = GroundingResolution(
        state=GroundingResolutionState.RESOLVED,
        reason="exact test grounded prompt",
        firing_motif_neuron_ids=firing.firing_motif_neuron_ids,
        referents=(ResolvedGroundedReferent(
            root=physical_root,
            contributing_motif_neuron_ids=(
                firing.firing_motif_neuron_ids
            ),
            contributing_activations=firing.activations,
            distinction_ids=("a" * 64,),
        ),),
        diagnostics=(),
        ungrounded_motif_neuron_ids=(),
    )
    conversation = GroundedTurnConversationOwner(
        authority_key=KEY,
        resource_profile=GroundedTurnResourceProfile.create(
            profile_id="focused-grounded-turns",
            max_episodes=8,
            max_constructions=4,
            max_elements_per_cue=4,
            max_state_bytes=2 * 1024 * 1024,
        ),
    )
    episodes = []
    for ordinal, prompt in enumerate((prompt_one, prompt_two), start=1):
        prepared = motor_owner.execute(
            motor_id=exemplar.motor_id,
            world_authority=world,
            causal_intent_receipt_sha256=f"{ordinal + 10:064x}",
        )
        heard_event, heard_experience = _heard_pcm(pcm, 20 + ordinal)
        hearing = motor_owner.close_self_hearing(
            emission=prepared,
            receptor_event=heard_event,
            receptor_experience=heard_experience,
            motif_owner=motif_owner,
        )
        outcome = _visual_settlement(f"outcome-{ordinal}")
        episodes.append(conversation.admit_turn(
            prompt_resolution=resolution,
            prompt_settlement=prompt,
            response_exemplar=exemplar,
            self_hearing=hearing,
            outcome_settlement=outcome,
            motor_owner=motor_owner,
        ))
    construction = conversation.settle_construction(
        episodes[0].cue.structure_id
    )
    assert construction is not None
    assert construction.state is GroundedTurnConstructionState.UNIQUE

    reply = conversation.resolve_reply(resolution)

    assert reply.state == "resolved"
    assert reply.motor_id == exemplar.motor_id
    assert not hasattr(reply, "text")
    assert conversation.status()["unique_construction_count"] == 1
    encoded = conversation.snapshot_encoded()
    restored = GroundedTurnConversationOwner.restore_encoded(
        authority_key=KEY,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.resolve_reply(resolution) == reply
    independently_valid_but_empty_grounding = (
        AuditoryMotifCausalGroundingOwner(
            authority_key=KEY,
            resource_profile=AuditoryMotifGroundingResourceProfile.create(
                profile_id="cold-mismatch-grounding",
                max_episodes=8,
                max_distinctions=4,
                max_firing_motifs_per_episode=8,
                max_activations_per_episode=16,
                max_roots_per_episode=16,
                max_episode_bytes=512 * 1024,
                max_state_bytes=2 * 1024 * 1024,
            ),
        )
    )
    with pytest.raises(
        ValueError,
        match="lacks grounded distinction",
    ):
        restored.cross_validate_restored(
            grounding_owner=independently_valid_but_empty_grounding,
            motor_owner=motor_owner,
        )


def test_w1_vocal_demonstration_derives_authenticated_sources_and_restores(
) -> None:
    pcm, motif_owner, motor_owner, exemplar = _motor_fixture()
    world = EmbodimentWorldAuthority(
        authority_key="grounded-demonstration-world-authority"
    )
    lived = _visual_settlement("demonstration-lived-scene")
    physical_root = next(
        value for value in _roots_from_settlement(lived)
        if json.loads(value.value_json)["field_tuples"]
    )
    prompt_event, prompt_experience = _heard_pcm(
        pcm,
        30,
        source_anchor=Fraction(0),
    )
    firing = motif_owner.fire(prompt_experience)
    resolution = GroundingResolution(
        state=GroundingResolutionState.RESOLVED,
        reason="exact test grounded demonstration",
        firing_motif_neuron_ids=firing.firing_motif_neuron_ids,
        referents=(ResolvedGroundedReferent(
            root=physical_root,
            contributing_motif_neuron_ids=(
                firing.firing_motif_neuron_ids
            ),
            contributing_activations=firing.activations,
            distinction_ids=("b" * 64,),
        ),),
        diagnostics=(),
        ungrounded_motif_neuron_ids=(),
    )
    cue = cue_from_resolution(resolution, max_elements=4)
    prepared = motor_owner.execute(
        motor_id=exemplar.motor_id,
        world_authority=world,
        causal_intent_receipt_sha256="3" * 64,
    )
    heard_event, heard_experience = _heard_pcm(pcm, 31)
    hearing = motor_owner.close_self_hearing(
        emission=prepared,
        receptor_event=heard_event,
        receptor_experience=heard_experience,
        motif_owner=motif_owner,
    )
    owner = W1GroundedDemonstrationOwner(
        authority_key=KEY,
        resource_profile=W1GroundedDemonstrationProfile.create(
            profile_id="focused-w1-grounded-demonstrations",
            max_demonstrations=4,
            max_scenes_per_demonstration=4,
            max_roots_per_scene=16,
            max_cue_elements=4,
            max_state_bytes=2 * 1024 * 1024,
        ),
    )
    demonstration = owner.admit_vocal(
        challenge_cue=cue,
        response_cue=cue,
        lived_settlements=(lived,),
        self_hearing=hearing,
        motor_owner=motor_owner,
    )

    assert demonstration.kind == "cited_lived_sequence_response"
    assert demonstration.source_episode_receipt_sha256s == tuple(sorted((
        hearing.receptor_event_receipt_sha256,
        lived.authority_receipt_sha256,
    )))
    encoded = owner.snapshot_encoded()
    restored = W1GroundedDemonstrationOwner.restore_encoded(
        authority_key=KEY,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.demonstrations == owner.demonstrations
    with pytest.raises(
        ValueError,
        match="reuse a physical source episode",
    ):
        owner.admit_vocal(
            challenge_cue=cue,
            response_cue=cue,
            lived_settlements=(lived,),
            self_hearing=hearing,
            motor_owner=motor_owner,
        )
