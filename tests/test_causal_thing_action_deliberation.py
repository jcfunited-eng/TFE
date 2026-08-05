from __future__ import annotations

import hashlib
from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    CausalActionCycle,
)
from dsf_ai_service.substrate.causal_mosaic_tapestry import (
    CausalMosaicTapestryOwner,
    CausalMosaicTapestryProfile,
    ObservedCausalMosaicRelationAuthority,
)
from dsf_ai_service.substrate.causal_recognition_attention import (
    CausalRecognitionAttentionOwner,
    CausalRecognitionAttentionProfile,
    CausalThingRelationPathAuthority,
    WholeOrganismAttentionContextAuthority,
)
from dsf_ai_service.substrate.causal_thing_action_deliberation import (
    CausalThingActionDeliberationOwner,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.embodied_other_perspective import (
    EmbodiedOtherPerspectiveOwner,
    EmbodiedOtherPerspectiveProfile,
    OtherBodyAccessProvenanceAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from tests.test_causal_thing_mosaic import (
    ACTION_DURATION_MICROSECONDS,
    _execute,
    _fixture,
    _outcome,
)


KEY = "causal-thing-action-deliberation-test-key-20260727"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class _PerspectiveWorld:
    @staticmethod
    def verify_observation_snapshot(value: object) -> None:
        if getattr(value, "authenticated", False) is not True:
            raise ValueError("test world observation authority changed")


def _admission_custody(
    settlement,
    *,
    thing_mosaic_receipt_sha256: str,
    focused_relation_receipt_sha256: str,
    unresolved: bool = False,
    world_receipt_sha256: str | None = None,
    lawful_action_relation_receipts: tuple[str, ...] | None = None,
):
    roots = full_field_sensory_roots(settlement)
    world_receipt = (
        world_receipt_sha256
        if world_receipt_sha256 is not None
        else _sha("world:" + settlement.authority_receipt_sha256)
    )
    world = _PerspectiveWorld()
    access = OtherBodyAccessProvenanceAuthority(
        authority_key=KEY,
        world_authority=world,
        max_objects=8,
    )
    perspective = EmbodiedOtherPerspectiveOwner(
        authority_key=KEY,
        profile=EmbodiedOtherPerspectiveProfile.create(
            profile_id="action-admission-perspective",
            max_other_bodies=4,
            max_objects_per_body=8,
            max_state_bytes=2 * 1024 * 1024,
        ),
        world_authority=world,
        access_authority=access,
    )
    observation = SimpleNamespace(
        authenticated=True,
        revision=1,
        self_body_id="body:self",
        bodies=(SimpleNamespace(
            body_id="body:self",
            as_record=lambda: {"body_id": "body:self"},
        ),),
        objects=(),
        authority_receipt_sha256=world_receipt,
    )
    perspective.commit(perspective.prepare(
        observation=observation,
        access_provenance=(),
    ))

    observations = ObservedCausalMosaicRelationAuthority(
        authority_key=KEY
    )
    tapestry = CausalMosaicTapestryOwner(
        authority_key=KEY,
        profile=CausalMosaicTapestryProfile.create(
            profile_id="action-admission-tapestry",
            max_tapestries=4,
            max_tapestry_relations=4,
            max_roots_per_tapestry=2_048,
            max_state_bytes=8 * 1024 * 1024,
        ),
        relation_authority=observations,
    )
    paths = CausalThingRelationPathAuthority(
        authority_key=KEY,
        tapestry_owner=tapestry,
    )
    contexts = WholeOrganismAttentionContextAuthority(
        authority_key=KEY
    )
    attention = CausalRecognitionAttentionOwner(
        authority_key=KEY,
        profile=CausalRecognitionAttentionProfile.create(
            profile_id="action-admission-attention",
            max_paths=4,
            max_roots=2_048,
            max_action_relations=4,
            max_inquiry_relations=4,
            max_state_bytes=16 * 1024 * 1024,
        ),
        path_authority=paths,
        context_authority=contexts,
    )
    relation_paths = []
    if not unresolved:
        senses = tuple(dict.fromkeys(root.sense for root in roots))
        if len(senses) < 2:
            raise AssertionError("test settlement lacks two senses")
        for ordinal, sense in enumerate(senses[:2], start=1):
            selected = tuple(
                root for root in roots if root.sense == sense
            )
            continuity = _sha(f"continuity:{ordinal}")
            source_episode = _sha(f"source-episode:{ordinal}")
            relation = observations.observe(
                chain_id="organism-lived-continuity:" + continuity,
                entity_continuity_hmac_sha256=continuity,
                source_mosaic_receipt_sha256=_sha(
                    f"source-mosaic:{ordinal}"
                ),
                target_mosaic_receipt_sha256=(
                    thing_mosaic_receipt_sha256
                ),
                source_learning_receipt_sha256=_sha(
                    f"source-learning:{ordinal}"
                ),
                target_learning_receipt_sha256=_sha(
                    f"target-learning:{ordinal}"
                ),
                source_episode_receipt_sha256=source_episode,
                continuity_predecessor_episode_receipt_sha256=(
                    source_episode
                ),
                target_episode_receipt_sha256=_sha(
                    f"target-episode:{ordinal}"
                ),
                source_time_start=(
                    settlement.source_time_start - Fraction(3 + ordinal)
                ),
                source_time_end=(
                    settlement.source_time_start - Fraction(2 + ordinal)
                ),
                target_time_start=settlement.source_time_start,
                target_time_end=settlement.source_time_end,
                source_full_field_roots=selected,
                target_full_field_roots=selected,
            )
            tapestry.commit(tapestry.prepare(relation))
            retained = next(
                value
                for value in tapestry.tapestries
                if value.observation == relation
            )
            relation_paths.append(
                paths.bind(retained.authority_receipt_sha256)
            )
    context = contexts.observe(
        context_id=(
            "live-observation:" + settlement.authority_receipt_sha256
        ),
        source_time_start=settlement.source_time_start,
        source_time_end=settlement.source_time_end,
        current_full_field_roots=roots,
        needs_state={"state": "exact"},
        body_state={"state": "exact"},
        chemical_state={"state": "exact"},
        causal_context={
            "world_observation_receipt_sha256": world_receipt,
        },
        lawful_action_relation_receipts=(
            lawful_action_relation_receipts
            if lawful_action_relation_receipts is not None
            else (
                (focused_relation_receipt_sha256,)
                if not unresolved
                else ()
            )
        ),
    )
    attention.commit(attention.prepare(
        context=context,
        paths=tuple(relation_paths),
    ))
    return {
        "recognition_attention_owner": attention,
        "attention_state": attention.state,
        "perspective_owner": perspective,
        "self_world_state": perspective.self_world_state,
        "perspective_models": perspective.models,
    }


def _owners(thing_owner):
    action_cycle = CausalActionCycle(authority_key=KEY)
    reciprocal = CausalThingReciprocalMosaicOwner(
        authority_key=KEY,
        thing_owner=thing_owner,
        max_classes=4,
        max_roots_per_class=1_024,
        max_cue_roots=256,
    )
    deliberation = CausalThingActionDeliberationOwner(
        authority_key=KEY,
        reciprocal_owner=reciprocal,
        action_cycle=action_cycle,
        max_candidates=8,
    )
    return action_cycle, reciprocal, deliberation


def _close_relation(
    action_cycle,
    *,
    trigger,
    outcome,
    action,
    ordinal,
):
    action_cycle.accept(trigger)
    binding = action_cycle.teach(
        trigger_reference=trigger.event_id,
        action=action,
        source="physical-lived-teaching",
        nonce=f"thing-action-teaching-{ordinal:04d}",
    )
    selection = action_cycle.select_expected(
        trigger,
        binding_id=binding.binding_id,
        action_receipt_sha256=action.authority_receipt_sha256,
    )
    assert selection.status == "committed"
    execution = action_cycle.record_execution(
        intent_receipt_sha256=(
            selection.intent.authority_receipt_sha256
        ),
        executor_receipt_sha256=f"{ordinal:064x}",
        disposition="executed",
    )
    observed = action_cycle.observe_outcome(
        execution_receipt_sha256=execution.authority_receipt_sha256,
        settlement=outcome,
    )
    action_cycle.close_observed(
        outcome_receipt_sha256=observed.authority_receipt_sha256,
    )
    return binding


def _closure_receipt(action_cycle, binding_id: str) -> str:
    return next(
        value.latest_closure_receipt_sha256
        for value in action_cycle.verified_relation_evidence()
        if value.binding_id == binding_id
    )


def test_new_view_of_same_physical_thing_retrieves_full_field_action() -> None:
    world, sensory, partitions, thing_owner = _fixture(max_partitions=4)
    picked = _execute(
        world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        81,
    )
    first_outcome = _outcome(sensory, picked)
    first_partition = partitions.partition(
        outcome=first_outcome,
        observation=picked.after,
        execution=picked,
    )
    first_mosaic = thing_owner.admit(first_partition)

    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1_000, 1_400, 0), 90_000),
            ACTION_DURATION_MICROSECONDS,
        ),
        82,
    )
    second_outcome = _outcome(sensory, moved)
    second_partition = partitions.partition(
        outcome=second_outcome,
        observation=moved.after,
        execution=moved,
        prior=first_partition,
    )
    second_mosaic = thing_owner.admit(second_partition)
    assert second_mosaic.thing_id == first_mosaic.thing_id

    action_cycle, _reciprocal, deliberation = _owners(thing_owner)
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
        action_cycle,
        trigger=first_outcome.causal_settlement,
        outcome=second_outcome.causal_settlement,
        action=action,
        ordinal=83,
    )
    custody = _admission_custody(
        second_outcome.causal_settlement,
        thing_mosaic_receipt_sha256=(
            second_mosaic.authority_receipt_sha256
        ),
        focused_relation_receipt_sha256=_closure_receipt(
            action_cycle,
            binding.binding_id,
        ),
    )
    before_actions = action_cycle.encoded_snapshot()
    before_things = thing_owner.snapshot_encoded()
    before_deliberation = deliberation.status()
    eligible = deliberation.eligible_completed_closure_receipts(
        second_outcome.causal_settlement,
        cue_senses=("touch",),
    )
    assert eligible == (
        _closure_receipt(action_cycle, binding.binding_id),
    )
    assert action_cycle.encoded_snapshot() == before_actions
    assert thing_owner.snapshot_encoded() == before_things
    assert deliberation.status() == before_deliberation

    resolution = deliberation.resolve(
        second_outcome.causal_settlement,
        cue_senses=("touch",),
        **custody,
    )
    assert resolution is not None
    deliberation.verify_resolution(resolution)

    assert resolution.state == "ready"
    assert resolution.selected is not None
    assert resolution.selected.thing_id == first_mosaic.thing_id
    assert resolution.selected.binding_id == binding.binding_id
    assert resolution.selected.action == action
    assert (
        resolution.selected.trigger_witness.settlement_receipt_sha256
        == first_outcome.causal_settlement.authority_receipt_sha256
    )
    assert (
        resolution.selected.outcome_witness.settlement_receipt_sha256
        == second_outcome.causal_settlement.authority_receipt_sha256
    )

    trigger_payload = action_cycle.perception_record(
        first_outcome.causal_settlement.event_id
    )
    assert all(
        tuple(name for name, _value in field_tuple["fields"])
        == DSF_FIELD_ORDER
        for sense in trigger_payload["interpretations"]
        for substream in sense["substreams"]
        for field_tuple in substream["field_tuples"]
    )
    assert deliberation.status() == {
        "full_field_witnesses_retained": True,
        "max_candidates": 8,
        "reduced_approximation": False,
        "schema": "guala.causal_thing.action_deliberation.status.v1",
        "signal_matching": False,
        "state_bytes": 0,
        "unseen_variant_guessing": False,
    }


def test_missing_outcome_and_competing_actions_stop_without_guessing() -> None:
    world, sensory, partitions, thing_owner = _fixture(max_partitions=3)
    picked = _execute(
        world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        91,
    )
    outcome = _outcome(sensory, picked)
    partition = partitions.partition(
        outcome=outcome,
        observation=picked.after,
        execution=picked,
    )
    mosaic = thing_owner.admit(partition)
    action_cycle, _reciprocal, deliberation = _owners(thing_owner)

    first_action = ActionCommand.embodiment(
        PORT_ID,
        encode_command(
            MoveCommand(
                PoseMM(PositionMM(1_100, 1_000, 0), 0),
                ACTION_DURATION_MICROSECONDS,
            )
        ),
    )
    action_cycle.accept(outcome.causal_settlement)
    action_cycle.teach(
        trigger_reference=outcome.causal_settlement.event_id,
        action=first_action,
        source="physical-lived-teaching",
        nonce="thing-incomplete-action-0001",
    )
    assert deliberation.eligible_completed_closure_receipts(
        outcome.causal_settlement,
        cue_senses=("touch",),
    ) == ()
    incomplete = deliberation.resolve(
        outcome.causal_settlement,
        cue_senses=("touch",),
        **_admission_custody(
            outcome.causal_settlement,
            thing_mosaic_receipt_sha256=(
                mosaic.authority_receipt_sha256
            ),
            focused_relation_receipt_sha256=_sha(
                "not-yet-completed-action-relation"
            ),
        ),
    )
    assert incomplete is not None
    assert incomplete.state == "outcome_unknown"
    assert incomplete.selected is None

    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1_100, 1_000, 0), 0),
            ACTION_DURATION_MICROSECONDS,
        ),
        92,
    )
    moved_outcome = _outcome(sensory, moved)
    moved_partition = partitions.partition(
        outcome=moved_outcome,
        observation=moved.after,
        execution=moved,
        prior=partition,
    )
    moved_mosaic = thing_owner.admit(moved_partition)
    first_binding = _close_relation(
        action_cycle,
        trigger=outcome.causal_settlement,
        outcome=moved_outcome.causal_settlement,
        action=first_action,
        ordinal=93,
    )
    second_action = ActionCommand.embodiment(
        PORT_ID,
        encode_command(
            MoveCommand(
                PoseMM(PositionMM(1_000, 1_100, 0), 0),
                ACTION_DURATION_MICROSECONDS,
            )
        ),
    )
    _close_relation(
        action_cycle,
        trigger=outcome.causal_settlement,
        outcome=moved_outcome.causal_settlement,
        action=second_action,
        ordinal=94,
    )
    custody = _admission_custody(
        moved_outcome.causal_settlement,
        thing_mosaic_receipt_sha256=(
            moved_mosaic.authority_receipt_sha256
        ),
        focused_relation_receipt_sha256=_closure_receipt(
            action_cycle,
            first_binding.binding_id,
        ),
    )
    expected_closures = tuple(sorted(
        value.latest_closure_receipt_sha256
        for value in action_cycle.verified_relation_evidence()
        if value.latest_closure_receipt_sha256 is not None
    ))
    assert len(expected_closures) == 2
    assert deliberation.eligible_completed_closure_receipts(
        moved_outcome.causal_settlement,
        cue_senses=("touch",),
    ) == expected_closures
    ambiguous = deliberation.resolve(
        moved_outcome.causal_settlement,
        cue_senses=("touch",),
        **custody,
    )
    assert ambiguous is not None
    deliberation.verify_resolution(ambiguous)
    assert ambiguous.state == "action_ambiguous"
    assert len(ambiguous.candidates) == 2
    assert ambiguous.selected is None


def test_resolution_authentication_rejects_tampering() -> None:
    world, sensory, partitions, thing_owner = _fixture(max_partitions=2)
    picked = _execute(
        world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        101,
    )
    outcome = _outcome(sensory, picked)
    partition = partitions.partition(
        outcome=outcome,
        observation=picked.after,
        execution=picked,
    )
    mosaic = thing_owner.admit(partition)
    _actions, _reciprocal, deliberation = _owners(thing_owner)
    resolution = deliberation.resolve(
        outcome.causal_settlement,
        cue_senses=("touch",),
        **_admission_custody(
            outcome.causal_settlement,
            thing_mosaic_receipt_sha256=(
                mosaic.authority_receipt_sha256
            ),
            focused_relation_receipt_sha256=_sha(
                "authenticated-empty-action-focus"
            ),
        ),
    )
    assert resolution is not None
    deliberation.verify_resolution(resolution)
    with pytest.raises(ValueError, match="authority changed"):
        deliberation.verify_resolution(replace(
            resolution,
            authority_hmac_sha256="0" * 64,
        ))


def test_quiescent_or_unresolved_attention_cannot_form_resolution() -> None:
    world, sensory, partitions, thing_owner = _fixture(max_partitions=2)
    picked = _execute(
        world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        102,
    )
    outcome = _outcome(sensory, picked)
    partition = partitions.partition(
        outcome=outcome,
        observation=picked.after,
        execution=picked,
    )
    mosaic = thing_owner.admit(partition)
    _actions, _reciprocal, deliberation = _owners(thing_owner)
    unresolved = _admission_custody(
        outcome.causal_settlement,
        thing_mosaic_receipt_sha256=mosaic.authority_receipt_sha256,
        focused_relation_receipt_sha256=_sha("unused-focus"),
        unresolved=True,
    )
    assert deliberation.resolve(
        outcome.causal_settlement,
        cue_senses=("touch",),
        **unresolved,
    ) is None
    quiescent = dict(unresolved)
    quiescent["attention_state"] = None
    assert deliberation.resolve(
        outcome.causal_settlement,
        cue_senses=("touch",),
        **quiescent,
    ) is None


def test_attention_and_perspective_must_name_same_current_context() -> None:
    world, sensory, partitions, thing_owner = _fixture(max_partitions=2)
    picked = _execute(
        world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        103,
    )
    outcome = _outcome(sensory, picked)
    partition = partitions.partition(
        outcome=outcome,
        observation=picked.after,
        execution=picked,
    )
    mosaic = thing_owner.admit(partition)
    _actions, _reciprocal, deliberation = _owners(thing_owner)
    custody = _admission_custody(
        outcome.causal_settlement,
        thing_mosaic_receipt_sha256=mosaic.authority_receipt_sha256,
        focused_relation_receipt_sha256=_sha("current-focus"),
    )
    with pytest.raises(ValueError, match="perspective custody"):
        deliberation.resolve(
            outcome.causal_settlement,
            cue_senses=("touch",),
            **(
                custody
                | {"self_world_state": replace(
                    custody["self_world_state"],
                    world_observation_receipt_sha256=_sha("stale-world"),
                )}
            ),
        )
    other_context = _admission_custody(
        outcome.causal_settlement,
        thing_mosaic_receipt_sha256=mosaic.authority_receipt_sha256,
        focused_relation_receipt_sha256=_sha("current-focus"),
        world_receipt_sha256=_sha("another-authenticated-world"),
    )
    cross_context = dict(custody)
    cross_context.update({
        "perspective_owner": other_context["perspective_owner"],
        "self_world_state": other_context["self_world_state"],
        "perspective_models": other_context["perspective_models"],
    })
    with pytest.raises(ValueError, match="another organism context"):
        deliberation.resolve(
            outcome.causal_settlement,
            cue_senses=("touch",),
            **cross_context,
        )


def test_discovery_omits_revoked_and_unrelated_completed_relations() -> None:
    world, sensory, partitions, thing_owner = _fixture(max_partitions=2)
    picked = _execute(
        world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        104,
    )
    outcome = _outcome(sensory, picked)
    partition = partitions.partition(
        outcome=outcome,
        observation=picked.after,
        execution=picked,
    )
    thing_owner.admit(partition)
    actions, _reciprocal, deliberation = _owners(thing_owner)

    def action_at(x_mm: int) -> ActionCommand:
        return ActionCommand.embodiment(
            PORT_ID,
            encode_command(MoveCommand(
                PoseMM(PositionMM(x_mm, 1_000, 0), 0),
                ACTION_DURATION_MICROSECONDS,
            )),
        )

    valid = _close_relation(
        actions,
        trigger=outcome.causal_settlement,
        outcome=outcome.causal_settlement,
        action=action_at(1_100),
        ordinal=105,
    )
    revoked = _close_relation(
        actions,
        trigger=outcome.causal_settlement,
        outcome=outcome.causal_settlement,
        action=action_at(1_200),
        ordinal=106,
    )
    actions.review_latest_closure(
        binding_id=revoked.binding_id,
        decision="revoke",
        source="physical-lived-teaching-review",
        nonce="revoke-action-discovery-0001",
    )

    other_world, other_sensory, _other_partitions, _other_owner = _fixture(
        max_partitions=1
    )
    other_execution = _execute(
        other_world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        107,
    )
    other_outcome = _outcome(other_sensory, other_execution)
    _close_relation(
        actions,
        trigger=other_outcome.causal_settlement,
        outcome=other_outcome.causal_settlement,
        action=action_at(1_300),
        ordinal=108,
    )

    before_actions = actions.encoded_snapshot()
    before_things = thing_owner.snapshot_encoded()
    assert deliberation.eligible_completed_closure_receipts(
        outcome.causal_settlement,
        cue_senses=("touch",),
    ) == (_closure_receipt(actions, valid.binding_id),)
    assert actions.encoded_snapshot() == before_actions
    assert thing_owner.snapshot_encoded() == before_things
