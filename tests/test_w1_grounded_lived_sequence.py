from __future__ import annotations

import json
import math
from dataclasses import replace
from fractions import Fraction

import pytest

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
from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingResolution,
    GroundingResolutionState,
    ResolvedGroundedReferent,
    _roots_from_settlement,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.grounded_turn_conversation import (
    cue_from_resolution,
)
from dsf_ai_service.substrate.w1_grounded_demonstration import (
    W1GroundedDemonstrationOwner,
    W1GroundedDemonstrationProfile,
)
from dsf_ai_service.substrate.w1_grounded_lived_sequence import (
    W1GroundedLivedSequenceOwner,
    W1GroundedLivedSequenceProfile,
)
from tests.test_self_vocal_grounded_conversation import (
    _heard_pcm,
    _motor_fixture,
)
from tests.native_joint_occurrence_support import joint_occurrences_for


KEY = b"W1-grounded-lived-sequence-test-key"


def _visual_settlement(
    assembly_id: str,
    *,
    start: Fraction,
    end: Fraction,
):
    count = 96
    duration = end - start
    source_times = tuple(
        start + duration * Fraction(index, count)
        for index in range(count)
    )
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="lived-sequence-camera",
        substream_id="anonymous-lived-region",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("reference-frame", "body-centered"),
            NativeAxisCoordinate("region", assembly_id),
        ),
        physical_quantity="light-intensity",
        physical_unit="normalized-intensity",
        source_times=source_times,
        normalized_signal=tuple(
            math.sin(2 * math.pi * 8 * index / count)
            for index in range(count)
        ),
        phase_turns=tuple(
            Fraction(index // 12) for index in range(count)
        ),
    )
    built = build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=start,
        source_time_end=end,
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


def _grounded_cue(motif_owner, pcm, root):
    _event, experience = _heard_pcm(
        pcm,
        80,
        source_anchor=Fraction(10),
    )
    firing = motif_owner.fire(experience)
    assert firing.activations
    resolution = GroundingResolution(
        state=GroundingResolutionState.RESOLVED,
        reason="exact lived sequence grounding",
        firing_motif_neuron_ids=firing.firing_motif_neuron_ids,
        referents=(
            ResolvedGroundedReferent(
                root=root,
                contributing_motif_neuron_ids=(
                    firing.firing_motif_neuron_ids
                ),
                contributing_activations=firing.activations,
                distinction_ids=("c" * 64,),
            ),
        ),
        diagnostics=(),
        ungrounded_motif_neuron_ids=(),
    )
    return cue_from_resolution(resolution, max_elements=8)


def _proof_fixture():
    pcm, motif_owner, motor_owner, exemplar = _motor_fixture()
    first = _visual_settlement(
        "lived-sequence-first",
        start=Fraction(0),
        end=Fraction(1),
    )
    second = _visual_settlement(
        "lived-sequence-second",
        start=Fraction(1),
        end=Fraction(2),
    )
    first_root = next(
        value for value in _roots_from_settlement(first)
        if json.loads(value.value_json)["field_tuples"]
    )
    cue = _grounded_cue(motif_owner, pcm, first_root)
    world = EmbodimentWorldAuthority(
        authority_key="lived-sequence-world-authority"
    )
    emission = motor_owner.execute(
        motor_id=exemplar.motor_id,
        world_authority=world,
        causal_intent_receipt_sha256="8" * 64,
    )
    heard_event, heard_experience = _heard_pcm(pcm, 81)
    hearing = motor_owner.close_self_hearing(
        emission=emission,
        receptor_event=heard_event,
        receptor_experience=heard_experience,
        motif_owner=motif_owner,
    )
    demonstration_owner = W1GroundedDemonstrationOwner(
        authority_key=KEY,
        resource_profile=W1GroundedDemonstrationProfile.create(
            profile_id="W1-lived-sequence-demonstration-proof",
            max_demonstrations=4,
            max_scenes_per_demonstration=4,
            max_roots_per_scene=32,
            max_cue_elements=8,
            max_state_bytes=4 * 1024 * 1024,
        ),
    )
    demonstration = demonstration_owner.admit_vocal(
        challenge_cue=cue,
        response_cue=cue,
        lived_settlements=(first, second),
        self_hearing=hearing,
        motor_owner=motor_owner,
    )
    owner = W1GroundedLivedSequenceOwner(
        authority_key=KEY,
        resource_profile=W1GroundedLivedSequenceProfile.create(
            profile_id="W1-grounded-lived-sequence-proof",
            max_proofs=4,
            max_events_per_proof=4,
            max_roots_per_event=32,
            max_state_bytes=8 * 1024 * 1024,
        ),
        demonstration_owner=demonstration_owner,
    )
    return (
        owner,
        demonstration_owner,
        demonstration,
        first,
        second,
    )


def test_ordered_lived_sequence_citation_is_bounded_and_cold_restorable():
    (
        owner,
        demonstration_owner,
        demonstration,
        first,
        second,
    ) = _proof_fixture()

    proof = owner.admit(
        demonstration=demonstration,
        lived_settlements=(first, second),
    )

    assert tuple(
        value.settlement_receipt_sha256
        for value in proof.ordered_events
    ) == (
        first.authority_receipt_sha256,
        second.authority_receipt_sha256,
    )
    assert proof.ordered_events[0].source_time_end == (
        proof.ordered_events[1].source_time_start
    )
    assert proof.response_root_identities
    assert not hasattr(proof, "story")
    assert not hasattr(proof, "topic")
    assert not hasattr(proof, "text")
    encoded = owner.snapshot_encoded()
    restored = W1GroundedLivedSequenceOwner.restore_encoded(
        authority_key=KEY,
        encoded=encoded,
        demonstration_owner=demonstration_owner,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.proofs == (proof,)


def test_reordered_or_altered_lived_sequence_cannot_claim_citation():
    (
        owner,
        _demonstration_owner,
        demonstration,
        first,
        second,
    ) = _proof_fixture()

    with pytest.raises(ValueError, match="reordered"):
        owner.admit(
            demonstration=demonstration,
            lived_settlements=(second, first),
        )

    proof = owner.admit(
        demonstration=demonstration,
        lived_settlements=(first, second),
    )
    altered = replace(
        proof,
        response_root_identities=(
            ("sense:sight:topology:0", "0" * 64),
        ),
    )
    with pytest.raises(
        ValueError,
        match="response left its lived event sequence",
    ):
        owner.verify(altered)
