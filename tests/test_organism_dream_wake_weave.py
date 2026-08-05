from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace

import pytest

from dsf_ai_service.substrate.organism_dream_wake_weave import (
    DreamWakeWeaveProfile,
    OrganismDreamWakeWeaveOwner,
    OriginState,
)


KEY = b"dream-wake-weave-test-authority-key" * 2


def _h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class _TapestryOwner:
    def __init__(self, *, connected: bool) -> None:
        first = SimpleNamespace(
            authority_receipt_sha256=_h("tapestry-a"),
            observation=SimpleNamespace(
                target_time_end=Fraction(2, 1),
            ),
        )
        second = SimpleNamespace(
            authority_receipt_sha256=_h("tapestry-b"),
            observation=SimpleNamespace(
                target_time_end=Fraction(4, 1),
            ),
        )
        self.tapestries = (first, second)
        self.relations = (
            (
                SimpleNamespace(
                    authority_receipt_sha256=_h("relation-a-b"),
                    source_tapestry_receipt_sha256=(
                        first.authority_receipt_sha256
                    ),
                    target_tapestry_receipt_sha256=(
                        second.authority_receipt_sha256
                    ),
                ),
            )
            if connected
            else ()
        )


class _StructuralStateOwner:
    def __init__(self) -> None:
        self.current_state = SimpleNamespace(
            authority_receipt_sha256=_h("organism-state"),
            provenance_json=json.dumps(
                {
                    "origin": "settled_whole_organism_episode",
                    "schema": "test.whole_organism.provenance.v1",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        )


class _LearningOwner:
    def __init__(self) -> None:
        self.records: tuple[object, ...] = ()


class _IntentOwner:
    def __init__(self) -> None:
        self.live: set[str] = set()

    def verify_live(self, value: object) -> bool:
        return (
            getattr(value, "authority_receipt_sha256", None)
            in self.live
        )


class _ExecutionAuthority:
    @staticmethod
    def verify(value: object) -> None:
        wrapper_receipt = getattr(
            value,
            "authority_receipt_sha256",
            None,
        )
        authenticated_wrapper_receipt = getattr(
            value,
            "authenticated_wrapper_receipt_sha256",
            wrapper_receipt,
        )
        if (
            getattr(value, "authority_valid", False) is not True
            or wrapper_receipt != authenticated_wrapper_receipt
        ):
            raise ValueError("execution authority changed")


def _profile() -> DreamWakeWeaveProfile:
    return DreamWakeWeaveProfile.create(
        profile_id="bounded-production-dream-wake-weave",
        max_dreams=8,
        max_wake_tests=8,
        max_weaves=8,
        max_transitions_per_dream=4,
        max_state_bytes=1024 * 1024,
    )


def _owner(
    *,
    connected: bool = True,
) -> tuple[
    OrganismDreamWakeWeaveOwner,
    _TapestryOwner,
    _StructuralStateOwner,
    _LearningOwner,
    _IntentOwner,
    _ExecutionAuthority,
]:
    tapestry = _TapestryOwner(connected=connected)
    structural = _StructuralStateOwner()
    learning = _LearningOwner()
    intents = _IntentOwner()
    executions = _ExecutionAuthority()
    owner = OrganismDreamWakeWeaveOwner(
        authority_key=KEY,
        profile=_profile(),
        tapestry_owner=tapestry,
        structural_state_owner=structural,
        learning_owner=learning,
        action_intent_owner=intents,
        action_execution_authority=executions,
    )
    return owner, tapestry, structural, learning, intents, executions


def _commit_dream(
    owner: OrganismDreamWakeWeaveOwner,
    structural: _StructuralStateOwner,
):
    prepared = owner.prepare_dream(
        organism_state=structural.current_state
    )
    assert prepared is not None
    owner.commit(prepared)
    return owner.dreams[-1]


def test_quiescent_genesis_and_dream_provenance_firewall() -> None:
    (
        quiescent,
        _tapestry,
        structural,
        _learning,
        _intents,
        _executions,
    ) = _owner(connected=False)
    before = quiescent.snapshot_encoded()

    assert (
        quiescent.prepare_dream(
            organism_state=structural.current_state
        )
        is None
    )
    assert quiescent.snapshot_encoded() == before
    assert quiescent.status()["mechanism_states"] == {
        "dream": "quiescent",
        "wake_test": "quiescent",
        "weave": "quiescent",
    }

    owner, _, structural, _, _, _ = _owner()
    prepared = owner.prepare_dream(
        organism_state=structural.current_state
    )
    assert prepared is not None
    dream = prepared.staged_record
    assert dream.origin is OriginState.INTERNALLY_SIMULATED
    assert dream.external_embodiment_state == "quiescent"
    assert dream.external_event_claimed is False
    assert all(
        transition.origin is OriginState.INTERNALLY_SIMULATED
        for transition in dream.transitions
    )
    assert all(
        transition.support_relation_receipt_sha256
        in dream.source_relation_receipt_sha256s
        for transition in dream.transitions
    )

    fabricated = replace(
        dream,
        origin=OriginState.EXTERNALLY_OBSERVED,
        external_event_claimed=True,
    )
    changed = replace(prepared, staged_record=fabricated)
    with pytest.raises(ValueError, match="growth record authority"):
        owner.commit(changed)
    owner.discard(prepared)
    assert owner.dreams == ()


def test_dream_cold_restore_and_replay_are_exact() -> None:
    owner, tapestry, structural, learning, intents, executions = _owner()
    first = _commit_dream(owner, structural)
    encoded = owner.snapshot_encoded()
    restored = OrganismDreamWakeWeaveOwner.restore_encoded(
        authority_key=KEY,
        profile=_profile(),
        tapestry_owner=tapestry,
        structural_state_owner=structural,
        learning_owner=learning,
        action_intent_owner=intents,
        action_execution_authority=executions,
        encoded=encoded,
    )

    assert restored.snapshot_encoded() == encoded
    assert restored.dreams == (first,)
    next_a = owner.prepare_dream(
        organism_state=structural.current_state
    )
    next_b = restored.prepare_dream(
        organism_state=structural.current_state
    )
    assert next_a == next_b
    assert next_a is not None
    assert (
        next_a.staged_record.internal_transition_start
        == first.internal_transition_end
    )
    owner.discard(next_a)
    restored.discard(next_b)


def test_wake_stays_unresolved_without_external_consequence() -> None:
    owner, _, structural, _, intents, _ = _owner()
    dream = _commit_dream(owner, structural)
    intent = SimpleNamespace(
        authority_receipt_sha256=_h("action-intent")
    )
    intents.live.add(intent.authority_receipt_sha256)

    prepared = owner.prepare_wake_test(
        dream_receipt_sha256=dream.authority_receipt_sha256,
        action_intent=intent,
    )
    owner.commit(prepared)
    wake = owner.wake_tests[0]

    assert wake.state == "unresolved"
    assert wake.origin is OriginState.COUNTERFACTUAL
    assert wake.consequence_origin is None
    assert wake.execution_receipt_sha256 is None
    assert wake.world_execution_receipt_sha256 is None
    assert owner.status()["unresolved_wake_tests"] == 1
    with pytest.raises(
        ValueError,
        match="externally settled wake test",
    ):
        owner.prepare_weave(
            wake_test_receipt_sha256=wake.authority_receipt_sha256,
            organism_state=structural.current_state,
        )


def test_wake_resolution_and_weave_require_one_later_physical_story() -> None:
    (
        owner,
        tapestry,
        structural,
        learning,
        intents,
        executions,
    ) = _owner()
    dream = _commit_dream(owner, structural)
    intent = SimpleNamespace(
        authority_receipt_sha256=_h("action-intent")
    )
    intents.live.add(intent.authority_receipt_sha256)
    wake_prepared = owner.prepare_wake_test(
        dream_receipt_sha256=dream.authority_receipt_sha256,
        action_intent=intent,
    )
    owner.commit(wake_prepared)
    pending = owner.wake_tests[0]

    execution = SimpleNamespace(
        authority_valid=True,
        authority_receipt_sha256=_h("execution"),
        world_execution_receipt_sha256=_h("world-execution"),
        intent_receipt_sha256=intent.authority_receipt_sha256,
        actual_outcome_settlement_receipt_sha256=_h("settlement"),
    )
    learning_record = SimpleNamespace(
        authority_receipt_sha256=_h("learning"),
        story=SimpleNamespace(
            action_execution_receipt_sha256=(
                execution.world_execution_receipt_sha256
            ),
            settlement_authority_receipt_sha256=(
                execution.actual_outcome_settlement_receipt_sha256
            ),
            episode_authority_receipt_sha256=_h("episode"),
            world_observation_receipt_sha256=_h("world-observation"),
            source_time_start=Fraction(5, 1),
        ),
        partition=SimpleNamespace(
            world_observation_receipt_sha256=_h(
                "world-observation"
            )
        ),
    )
    learning.records = (learning_record,)
    resolution = owner.prepare_wake_resolution(
        wake_test_receipt_sha256=pending.authority_receipt_sha256,
        execution=execution,
        consequence_learning_record=learning_record,
    )
    owner.commit(resolution)
    settled = owner.wake_tests[0]

    assert settled.origin is OriginState.COUNTERFACTUAL
    assert settled.state == "externally_settled"
    assert settled.consequence_origin is OriginState.EXTERNALLY_OBSERVED
    assert settled.consequence_learning_receipt_sha256 == _h("learning")
    assert settled.execution_receipt_sha256 == _h("execution")
    assert settled.world_execution_receipt_sha256 == _h(
        "world-execution"
    )
    assert (
        settled.execution_receipt_sha256
        != settled.world_execution_receipt_sha256
    )
    weave_prepared = owner.prepare_weave(
        wake_test_receipt_sha256=settled.authority_receipt_sha256,
        organism_state=structural.current_state,
    )
    undo = owner.commit(weave_prepared)
    weave = owner.weaves[0]

    assert weave.expression_origin == "organism_originated_embodied_action"
    assert weave.stored_language_content is False
    assert weave.support_tapestry_receipt_sha256s == (
        dream.source_tapestry_receipt_sha256s
    )
    assert weave.execution_receipt_sha256 == _h("execution")
    assert weave.world_execution_receipt_sha256 == _h(
        "world-execution"
    )
    assert weave.consequence_origin is OriginState.EXTERNALLY_OBSERVED
    encoded = owner.snapshot_encoded()
    restored = OrganismDreamWakeWeaveOwner.restore_encoded(
        authority_key=KEY,
        profile=_profile(),
        tapestry_owner=tapestry,
        structural_state_owner=structural,
        learning_owner=learning,
        action_intent_owner=intents,
        action_execution_authority=executions,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.wake_tests == owner.wake_tests
    assert restored.weaves == owner.weaves
    owner.rollback(undo)
    assert owner.weaves == ()


@pytest.mark.parametrize(
    ("crossed_receipt", "expected_error"),
    (
        ("wrapper", "execution authority changed"),
        ("world", "wake consequence crossed"),
    ),
)
def test_wake_resolution_refuses_crossed_execution_receipts(
    crossed_receipt: str,
    expected_error: str,
) -> None:
    owner, _, structural, learning, intents, _ = _owner()
    dream = _commit_dream(owner, structural)
    intent = SimpleNamespace(
        authority_receipt_sha256=_h("crossed-action-intent")
    )
    intents.live.add(intent.authority_receipt_sha256)
    prepared_wake = owner.prepare_wake_test(
        dream_receipt_sha256=dream.authority_receipt_sha256,
        action_intent=intent,
    )
    owner.commit(prepared_wake)
    pending = owner.wake_tests[0]

    authenticated_wrapper = _h("authenticated-wrapper-execution")
    execution = SimpleNamespace(
        authority_valid=True,
        authority_receipt_sha256=(
            _h("crossed-wrapper-execution")
            if crossed_receipt == "wrapper"
            else authenticated_wrapper
        ),
        authenticated_wrapper_receipt_sha256=(
            authenticated_wrapper
        ),
        world_execution_receipt_sha256=_h("world-execution-a"),
        intent_receipt_sha256=intent.authority_receipt_sha256,
        actual_outcome_settlement_receipt_sha256=_h(
            "crossed-settlement"
        ),
    )
    world_observation = _h("crossed-world-observation")
    learning_record = SimpleNamespace(
        authority_receipt_sha256=_h("crossed-learning"),
        story=SimpleNamespace(
            action_execution_receipt_sha256=(
                _h("world-execution-b")
                if crossed_receipt == "world"
                else execution.world_execution_receipt_sha256
            ),
            settlement_authority_receipt_sha256=(
                execution.actual_outcome_settlement_receipt_sha256
            ),
            episode_authority_receipt_sha256=_h(
                "crossed-episode"
            ),
            world_observation_receipt_sha256=world_observation,
            source_time_start=(
                dream.source_latest_external_time_end + 1
            ),
        ),
        partition=SimpleNamespace(
            world_observation_receipt_sha256=world_observation,
        ),
    )
    learning.records = (learning_record,)
    before = owner.snapshot_encoded()

    with pytest.raises(ValueError, match=expected_error):
        owner.prepare_wake_resolution(
            wake_test_receipt_sha256=pending.authority_receipt_sha256,
            execution=execution,
            consequence_learning_record=learning_record,
        )
    assert owner.snapshot_encoded() == before
