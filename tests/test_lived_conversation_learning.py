from __future__ import annotations

import json
from fractions import Fraction

import pytest

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingResolution,
    GroundingResolutionState,
    ResolvedGroundedReferent,
    _roots_from_settlement,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.grounded_turn_conversation import (
    GroundedTurnConversationOwner,
    GroundedTurnResourceProfile,
)
from dsf_ai_service.substrate.lived_conversation_learning import (
    LivedConversationLearningCoordinator,
    LivedConversationLearningProfile,
)
from tests.test_self_vocal_grounded_conversation import (
    KEY,
    _heard_pcm,
    _motor_fixture,
    _visual_settlement,
)


def _fixture():
    pcm, motifs, motors, exemplar = _motor_fixture()
    prompt_one = _visual_settlement("coordinator-prompt-one")
    prompt_two = _visual_settlement("coordinator-prompt-two")
    root = next(
        value for value in _roots_from_settlement(prompt_one)
        if json.loads(value.value_json)["field_tuples"]
    )
    _event, experience = _heard_pcm(
        pcm, 101, source_anchor=Fraction(0)
    )
    firing = motifs.fire(experience)
    resolution = GroundingResolution(
        state=GroundingResolutionState.RESOLVED,
        reason="exact full-field lived cue",
        firing_motif_neuron_ids=firing.firing_motif_neuron_ids,
        referents=(ResolvedGroundedReferent(
            root=root,
            contributing_motif_neuron_ids=(
                firing.firing_motif_neuron_ids
            ),
            contributing_activations=firing.activations,
            distinction_ids=("e" * 64,),
        ),),
        diagnostics=(),
        ungrounded_motif_neuron_ids=(),
    )
    turns = GroundedTurnConversationOwner(
        authority_key=KEY,
        resource_profile=GroundedTurnResourceProfile.create(
            profile_id="coordinator-grounded-turns",
            max_episodes=8,
            max_constructions=4,
            max_elements_per_cue=4,
            max_state_bytes=2 * 1024 * 1024,
        ),
    )
    coordinator = LivedConversationLearningCoordinator(
        authority_key=KEY,
        profile=LivedConversationLearningProfile.create(
            profile_id="lived-conversation-coordinator",
            max_proposal_witness_bytes=2 * 1024 * 1024,
            max_state_bytes=4 * 1024 * 1024,
        ),
        turn_owner=turns,
        motor_owner=motors,
    )
    world = EmbodimentWorldAuthority(
        authority_key="coordinator-grounded-turn-world"
    )
    inputs = []
    for ordinal, prompt in enumerate((prompt_one, prompt_two), 1):
        emission = motors.execute(
            motor_id=exemplar.motor_id,
            world_authority=world,
            causal_intent_receipt_sha256=f"{ordinal + 30:064x}",
        )
        heard_event, heard_experience = _heard_pcm(
            pcm, 110 + ordinal
        )
        hearing = motors.close_self_hearing(
            emission=emission,
            receptor_event=heard_event,
            receptor_experience=heard_experience,
            motif_owner=motifs,
        )
        inputs.append({
            "outcome_settlement": _visual_settlement(
                f"coordinator-outcome-{ordinal}"
            ),
            "prompt_resolution": resolution,
            "prompt_settlement": prompt,
            "response_exemplar": exemplar,
            "self_hearing": hearing,
        })
    return coordinator, motors, resolution, tuple(inputs)


def test_two_atomic_lived_experiences_release_authenticated_motor_and_restore():
    coordinator, motors, resolution, inputs = _fixture()
    for ordinal, values in enumerate(inputs):
        before = coordinator.encoded_snapshot()
        prepared = coordinator.prepare(**values)
        assert coordinator.encoded_snapshot() == before
        result = coordinator.commit(prepared)
        assert coordinator.commit(prepared) == result
        assert (result.construction is None) is (ordinal == 0)

    proposal = coordinator.propose(resolution)
    exemplar = motors.exemplars[0]
    assert proposal.motor_id == exemplar.motor_id
    assert proposal.motor_pcm_sha256
    witness = json.loads(proposal.proof_witness_json)
    assert len(witness["proof_episodes"]) == 2
    assert not hasattr(proposal, "text")
    assert not hasattr(proposal, "label")
    encoded = coordinator.encoded_snapshot()

    restored = LivedConversationLearningCoordinator.restore_encoded(
        authority_key=KEY,
        encoded=encoded,
        motor_owner=motors,
    )

    assert restored.encoded_snapshot() == encoded
    assert restored.propose(resolution) == proposal
    tampered = encoded[:-1] + (b"0" if encoded[-1:] != b"0" else b"1")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        LivedConversationLearningCoordinator.restore_encoded(
            authority_key=KEY,
            encoded=tampered,
            motor_owner=motors,
        )


def test_downstream_failure_and_explicit_rollback_preserve_exact_bytes(
    monkeypatch,
):
    coordinator, _motors, _resolution, inputs = _fixture()
    before = coordinator.encoded_snapshot()
    original = coordinator._turns.settle_construction

    def fail(_cue):
        raise RuntimeError("injected construction failure")

    monkeypatch.setattr(
        coordinator._turns, "settle_construction", fail
    )
    with pytest.raises(RuntimeError, match="construction failure"):
        coordinator.prepare(**inputs[0])
    assert coordinator.encoded_snapshot() == before

    monkeypatch.setattr(
        coordinator._turns, "settle_construction", original
    )
    prepared = coordinator.prepare(**inputs[0])
    monkeypatch.setattr(
        coordinator._turns, "settle_construction", fail
    )
    with pytest.raises(RuntimeError, match="construction failure"):
        coordinator.commit(prepared)
    assert coordinator.encoded_snapshot() == before
    monkeypatch.setattr(
        coordinator._turns, "settle_construction", original
    )
    assert coordinator.rollback(prepared) is True
    assert coordinator.rollback(prepared) is False
    assert coordinator.encoded_snapshot() == before
