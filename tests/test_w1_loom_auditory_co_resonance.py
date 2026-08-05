from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.substrate.w1_loom_auditory_bridge import (
    W1LoomAuditoryBridge,
    W1LoomAuditoryDynamicsOccurrence,
    W1LoomAuditoryLaneDynamics,
)
from dsf_ai_service.substrate.w1_loom_auditory_co_resonance import (
    AuthenticatedBilateralL6PulseClosure,
    AuthenticatedBilateralL6PulseProfile,
    restore_authenticated_bilateral_l6_pulse_closure,
)
from tests.test_w1_loom_auditory_bridge import _receptors


KEY = b"guala-test-authenticated-bilateral-l6-pulse-closure"
THING = "2" * 64


def _profile() -> AuthenticatedBilateralL6PulseProfile:
    return AuthenticatedBilateralL6PulseProfile.create(
        profile_id="test-authenticated-bilateral-l6-pulse-closure",
        max_things=4,
        max_occurrences_per_thing=8,
        max_relations_per_thing=200_000,
        max_total_relations=600_000,
        max_settlement_receipts=32,
        max_state_bytes=128 * 1024 * 1024,
    )


def _occurrence(brain: LoomBrain) -> W1LoomAuditoryDynamicsOccurrence:
    bridge = W1LoomAuditoryBridge(brain)
    bridge.settle(_receptors())
    occurrence = bridge.latest_dynamics
    assert occurrence is not None
    occurrence.verify()
    return occurrence


def _retag(
    occurrence: W1LoomAuditoryDynamicsOccurrence,
    digit: str,
) -> W1LoomAuditoryDynamicsOccurrence:
    result = replace(
        occurrence,
        source_receptor_settlement_receipt_sha256=digit * 64,
    )
    result.verify()
    return result


def _quiet(
    occurrence: W1LoomAuditoryDynamicsOccurrence,
    digit: str,
) -> W1LoomAuditoryDynamicsOccurrence:
    result = W1LoomAuditoryDynamicsOccurrence(
        source_receptor_settlement_receipt_sha256=digit * 64,
        frame_count=occurrence.frame_count,
        lanes=tuple(
            W1LoomAuditoryLaneDynamics(
                ear_route=value.ear_route,
                neuron_ids=value.neuron_ids,
                cochlear_index=value.cochlear_index,
                channel_id=value.channel_id,
                component=value.component,
                field_name=value.field_name,
                exact_winding_deltas=(0,) * occurrence.frame_count,
            )
            for value in occurrence.lanes
        ),
    )
    result.verify()
    return result


def test_repeated_source_disjoint_grounding_grows_and_settles() -> None:
    brain = LoomBrain(seed_size=8, observable="event_count")
    occurrence = _occurrence(brain)
    owner = AuthenticatedBilateralL6PulseClosure(
        brain=brain,
        profile=_profile(),
        authority_key=KEY,
    )

    first = owner.learn(
        occurrence=_retag(occurrence, "3"),
        thing_id=THING,
        grounding_authority_receipt_sha256="4" * 64,
    )
    second = owner.learn(
        occurrence=_retag(occurrence, "5"),
        thing_id=THING,
        grounding_authority_receipt_sha256="6" * 64,
    )
    owner.verify_learning_receipt(first)
    owner.verify_learning_receipt(second)
    settlement = owner.settle(_retag(occurrence, "7"))

    settlement.verify()
    owner.verify_settlement(settlement)
    assert first.locked_relation_count == 0
    assert second.locked_relation_count > 0
    assert settlement.state == "resolved"
    assert settlement.thing_ids == (THING,)


def test_unknown_is_fail_closed_and_duplicate_source_is_rejected() -> None:
    brain = LoomBrain(seed_size=8, observable="event_count")
    occurrence = _occurrence(brain)
    owner = AuthenticatedBilateralL6PulseClosure(
        brain=brain,
        profile=_profile(),
        authority_key=KEY,
    )
    learned = _retag(occurrence, "3")
    owner.learn(
        occurrence=learned,
        thing_id=THING,
        grounding_authority_receipt_sha256="4" * 64,
    )
    with pytest.raises(ValueError, match="source-disjoint"):
        owner.learn(
            occurrence=learned,
            thing_id=THING,
            grounding_authority_receipt_sha256="5" * 64,
        )
    unknown = owner.settle(_quiet(occurrence, "8"))
    owner.verify_settlement(unknown)
    assert unknown.state == "unknown"


def test_authenticated_state_cold_restores_byte_identically() -> None:
    brain = LoomBrain(seed_size=8, observable="event_count")
    occurrence = _occurrence(brain)
    owner = AuthenticatedBilateralL6PulseClosure(
        brain=brain,
        profile=_profile(),
        authority_key=KEY,
    )
    for source, grounding in (("3", "4"), ("5", "6")):
        owner.learn(
            occurrence=_retag(occurrence, source),
            thing_id=THING,
            grounding_authority_receipt_sha256=grounding * 64,
        )
    before = owner.snapshot_encoded()

    restored = restore_authenticated_bilateral_l6_pulse_closure(
        before,
        brain=brain,
        authority_key=KEY,
    )

    assert restored.snapshot_encoded() == before
    restored_result = restored.settle(_retag(occurrence, "7"))
    owner_result = owner.settle(_retag(occurrence, "7"))
    restored.verify_settlement(restored_result)
    owner.verify_settlement(owner_result)
    assert restored_result == owner_result


def test_settlement_rejects_forgery_replay_and_wrong_owner() -> None:
    brain = LoomBrain(seed_size=8, observable="event_count")
    occurrence = _occurrence(brain)
    owner = AuthenticatedBilateralL6PulseClosure(
        brain=brain,
        profile=_profile(),
        authority_key=KEY,
    )
    other = AuthenticatedBilateralL6PulseClosure(
        brain=brain,
        profile=_profile(),
        authority_key=b"other-owner-authenticated-pulse-closure-key",
    )
    for source, grounding in (("3", "4"), ("5", "6")):
        owner.learn(
            occurrence=_retag(occurrence, source),
            thing_id=THING,
            grounding_authority_receipt_sha256=grounding * 64,
        )
    settlement = owner.settle(_retag(occurrence, "7"))
    forged = replace(settlement, authority_receipt_sha256="f" * 64)

    with pytest.raises(ValueError, match="owner authority"):
        owner.verify_settlement(forged)
    with pytest.raises(ValueError, match="owner authority"):
        other.verify_settlement(settlement)
    owner.verify_settlement(settlement)
    with pytest.raises(ValueError, match="replayed"):
        owner.verify_settlement(settlement)
