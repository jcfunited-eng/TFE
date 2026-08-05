from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.substrate.causal_thing_action_intent import (
    CausalThingActionIntentOwner,
    CausalThingActionIntentProfile,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from tests.test_causal_thing_action_deliberation import (
    KEY,
    _admission_custody,
    _close_relation,
    _closure_receipt,
    _owners,
)
from tests.test_causal_thing_mosaic import (
    ACTION_DURATION_MICROSECONDS,
    _execute,
    _fixture,
    _outcome,
)


def _ready_graph():
    world, sensory, partitions, thing_owner = _fixture(max_partitions=4)
    picked = _execute(
        world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        121,
    )
    first_outcome = _outcome(sensory, picked)
    first_partition = partitions.partition(
        outcome=first_outcome,
        observation=picked.after,
        execution=picked,
    )
    thing_owner.admit(first_partition)

    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1_000, 1_400, 0), 90_000),
            ACTION_DURATION_MICROSECONDS,
        ),
        122,
    )
    second_outcome = _outcome(sensory, moved)
    second_partition = partitions.partition(
        outcome=second_outcome,
        observation=moved.after,
        execution=moved,
        prior=first_partition,
    )
    second_mosaic = thing_owner.admit(second_partition)
    actions, _reciprocal, deliberation = _owners(thing_owner)
    action = ActionCommand.embodiment(
        PORT_ID,
        encode_command(
            MoveCommand(
                PoseMM(PositionMM(1_000, 1_400, 0), 90_000),
                ACTION_DURATION_MICROSECONDS,
            )
        ),
    )
    binding = _close_relation(
        actions,
        trigger=first_outcome.causal_settlement,
        outcome=second_outcome.causal_settlement,
        action=action,
        ordinal=123,
    )
    custody = _admission_custody(
        second_outcome.causal_settlement,
        thing_mosaic_receipt_sha256=(
            second_mosaic.authority_receipt_sha256
        ),
        focused_relation_receipt_sha256=_closure_receipt(
            actions,
            binding.binding_id,
        ),
    )
    resolution = deliberation.resolve(
        second_outcome.causal_settlement,
        cue_senses=("touch",),
        **custody,
    )
    assert resolution is not None
    assert resolution.state == "ready"
    profile = CausalThingActionIntentProfile.create(
        profile_id="causal-thing-action-intent-test",
        max_live_intents=2,
        max_witness_bytes=4 * 1024 * 1024,
        max_state_bytes=32 * 1024 * 1024,
    )
    owner = CausalThingActionIntentOwner(
        authority_key=KEY,
        profile=profile,
        deliberation_owner=deliberation,
    )
    return (
        world,
        sensory,
        partitions,
        actions,
        deliberation,
        owner,
        profile,
        first_outcome,
        second_outcome,
        second_partition,
        resolution,
        custody,
    )


def test_same_thing_variant_issues_distinct_full_field_intent_and_restores():
    (
        _world,
        _sensory,
        _partitions,
        _actions,
        deliberation,
        owner,
        profile,
        first,
        current,
        _partition,
        resolution,
        custody,
    ) = _ready_graph()

    assert (
        first.causal_settlement.structural_fingerprint
        != current.causal_settlement.structural_fingerprint
    )
    intent = owner.issue(
        settlement=current.causal_settlement,
        resolution=resolution,
        **custody,
    )
    assert owner.verify_live(intent)
    assert (
        intent.recognition_attention_receipt_sha256
        == custody["attention_state"].authority_receipt_sha256
    )
    assert (
        intent.attention_context_receipt_sha256
        == custody["attention_state"].context.authority_receipt_sha256
    )
    assert (
        intent.focused_relation_receipt_sha256
        == custody[
            "attention_state"
        ].focused_relation_receipt_sha256
    )
    assert (
        intent.self_world_state_receipt_sha256
        == custody["self_world_state"].authority_receipt_sha256
    )
    assert (
        intent.world_observation_receipt_sha256
        == custody[
            "self_world_state"
        ].world_observation_receipt_sha256
    )
    assert intent.perspective_model_receipt_sha256s == tuple(sorted(
        value.authority_receipt_sha256
        for value in custody["perspective_models"]
    ))
    assert (
        intent.current_witness.structural_fingerprint
        == current.causal_settlement.structural_fingerprint
    )
    assert (
        intent.learned_trigger_witness.structural_fingerprint
        == first.causal_settlement.structural_fingerprint
    )
    assert (
        intent.current_witness.structural_fingerprint
        != intent.learned_trigger_witness.structural_fingerprint
    )
    assert (
        intent.expected_outcome_witness.settlement_receipt_sha256
        == current.causal_settlement.authority_receipt_sha256
    )
    encoded = owner.snapshot_encoded()
    restored = CausalThingActionIntentOwner(
        authority_key=KEY,
        profile=profile,
        deliberation_owner=deliberation,
    )
    restored.restore_encoded(encoded)
    assert restored.snapshot_encoded() == encoded
    assert restored.verify_live(intent)
    assert restored.consume(
        intent_receipt_sha256=intent.authority_receipt_sha256
    ) == intent
    assert restored.status()["live_intents"] == 0


def test_stale_or_tampered_resolution_cannot_authorize_action():
    (
        _world,
        _sensory,
        _partitions,
        actions,
        deliberation,
        owner,
        _profile,
        first,
        current,
        _partition,
        resolution,
        custody,
    ) = _ready_graph()
    tampered = replace(
        resolution,
        authority_hmac_sha256="0" * 64,
    )
    with pytest.raises(ValueError, match="authority changed"):
        owner.issue(
            settlement=current.causal_settlement,
            resolution=tampered,
            **custody,
        )
    changed_attention = dict(custody)
    changed_attention["attention_state"] = replace(
        custody["attention_state"],
        focused_relation_receipt_sha256="0" * 64,
    )
    with pytest.raises(ValueError, match="not current"):
        owner.issue(
            settlement=current.causal_settlement,
            resolution=resolution,
            **changed_attention,
        )

    second_action = ActionCommand.embodiment(
        PORT_ID,
        encode_command(
            MoveCommand(
                PoseMM(PositionMM(1_100, 1_000, 0), 0),
                ACTION_DURATION_MICROSECONDS,
            )
        ),
    )
    _close_relation(
        actions,
        trigger=first.causal_settlement,
        outcome=current.causal_settlement,
        action=second_action,
        ordinal=124,
    )
    assert deliberation.resolve(
        current.causal_settlement,
        cue_senses=("touch",),
        **custody,
    ).state == "action_ambiguous"
    with pytest.raises(ValueError, match="no longer current"):
        owner.issue(
            settlement=current.causal_settlement,
            resolution=resolution,
            **custody,
        )
    assert owner.status()["live_intents"] == 0
