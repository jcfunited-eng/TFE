"""Bounded autonomous play over exact closed full-field relations."""

from __future__ import annotations

import hashlib
import json

import pytest

from dsf_ai_service.substrate.autonomous_causal_play import (
    AutonomousCausalPlayOwner,
)
from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    CausalActionCycle,
)
from tests.test_causal_action_cycle import _close, _settlement, _teach


KEY = "autonomous-causal-play-test-key"


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _closed_relation(*, suffix: str = "one"):
    trigger = _settlement(f"play-trigger-{suffix}", frequency=37)
    outcome = _settlement(f"play-outcome-{suffix}", frequency=41)
    cycle = CausalActionCycle(authority_key=f"{KEY}-{suffix}")
    action = ActionCommand.embodiment(
        "body.motion.primary",
        f"exact-physical-command-{suffix}".encode("ascii"),
    )
    _teach(
        cycle,
        trigger,
        action,
        f"autonomous-play-teacher-{suffix}-0001",
    )
    _close(
        cycle,
        trigger,
        outcome,
        executor_label=f"autonomous-play-executor-{suffix}",
        decision="confirm",
        feedback_nonce=f"autonomous-play-feedback-{suffix}-0001",
    )
    evidence = cycle.verified_relation_evidence()
    assert len(evidence) == 1
    assert evidence[0].latest_closure_receipt_sha256 is not None
    assert evidence[0].outcome_witness is not None
    return evidence, trigger, outcome


def _completion_record(opportunity, outcome):
    return {
        "dispatch_status": "completed",
        "steps": [{
            "action_receipt_sha256": opportunity.action_receipt_sha256,
            "binding_id": opportunity.binding_id,
            "outcome_settlement_receipt_sha256": (
                outcome.authority_receipt_sha256
            ),
        }],
        "trigger": "autonomous_play",
        "world_observation_receipt_sha256": (
            opportunity.world_observation_receipt_sha256
        ),
    }


def test_exact_closed_full_field_relation_issues_and_consumes_once() -> None:
    evidence, trigger, outcome = _closed_relation()
    owner = AutonomousCausalPlayOwner(authority_key=KEY)
    world_receipt = _digest(b"authenticated-world-observation-one")

    opportunity = owner.prepare(
        evidence=evidence,
        world_structural_fingerprint=trigger.structural_fingerprint,
        world_observation_receipt_sha256=world_receipt,
    )
    assert opportunity is not None
    assert owner.verify_opportunity(opportunity) == opportunity

    completion = owner.complete(
        opportunity,
        causal_play_record=_completion_record(opportunity, outcome),
    )
    assert completion.opportunity_id == opportunity.opportunity_id
    assert owner.status()["consumed"] == 1
    assert owner.prepare(
        evidence=evidence,
        world_structural_fingerprint=trigger.structural_fingerprint,
        world_observation_receipt_sha256=world_receipt,
    ) is None


def test_active_opportunity_and_consumption_restore_exactly() -> None:
    evidence, trigger, outcome = _closed_relation(suffix="restore")
    world_receipt = _digest(b"authenticated-world-observation-restore")
    writer = AutonomousCausalPlayOwner(authority_key=KEY)
    opportunity = writer.prepare(
        evidence=evidence,
        world_structural_fingerprint=trigger.structural_fingerprint,
        world_observation_receipt_sha256=world_receipt,
    )
    assert opportunity is not None
    active_snapshot = writer.encoded_snapshot()

    restored = AutonomousCausalPlayOwner(authority_key=KEY)
    restored.restore_encoded(active_snapshot)
    assert restored.encoded_snapshot() == active_snapshot
    restored_opportunity = restored.verify_opportunity(
        json.loads(active_snapshot)["active"]
    )
    restored.complete(
        restored_opportunity,
        causal_play_record=_completion_record(
            restored_opportunity,
            outcome,
        ),
    )
    consumed_snapshot = restored.encoded_snapshot()

    cold = AutonomousCausalPlayOwner(authority_key=KEY)
    cold.restore_encoded(consumed_snapshot)
    assert cold.encoded_snapshot() == consumed_snapshot
    assert cold.status()["active"] is False
    assert cold.status()["consumed"] == 1


def test_state_is_bounded_tamper_evident_and_ambiguity_is_silent() -> None:
    evidence, trigger, _outcome = _closed_relation(suffix="bounds")
    other_evidence, _other_trigger, _other_outcome = _closed_relation(
        suffix="other",
    )
    competing = (
        evidence[0],
        type(other_evidence[0])(
            **{
                field: getattr(other_evidence[0], field)
                for field in other_evidence[0].__dataclass_fields__
                if field != "trigger_witness"
            },
            trigger_witness=evidence[0].trigger_witness,
        ),
    )
    owner = AutonomousCausalPlayOwner(authority_key=KEY)
    assert owner.prepare(
        evidence=competing,
        world_structural_fingerprint=trigger.structural_fingerprint,
        world_observation_receipt_sha256=_digest(b"ambiguous-world"),
    ) is None

    opportunity = owner.prepare(
        evidence=evidence,
        world_structural_fingerprint=trigger.structural_fingerprint,
        world_observation_receipt_sha256=_digest(b"bounded-world"),
    )
    assert opportunity is not None
    snapshot = owner.encoded_snapshot()
    assert len(snapshot) <= 128 * 1024
    changed = json.loads(snapshot)
    changed["active"]["authority_hmac_sha256"] = "0" * 64
    tampered = json.dumps(
        changed,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="authority changed"):
        owner.restore_encoded(tampered)
    assert owner.encoded_snapshot() == snapshot
