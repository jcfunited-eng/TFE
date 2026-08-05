"""Decisive contracts for the seven-owner whole-organism monitor."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from dsf_ai_service.substrate.causal_mosaic_tapestry import (
    CausalMosaicTapestryOwner,
    ENVELOPE_SCHEMA as TAPESTRY_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.causal_recognition_attention import (
    CausalRecognitionAttentionOwner,
    ENVELOPE_SCHEMA as ATTENTION_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.causal_thing_action_intent import (
    CausalThingActionIntentOwner,
    ENVELOPE_SCHEMA as ACTION_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.durable_sensed_consequence import (
    DurableSensedConsequenceOwner,
    ENVELOPE_SCHEMA as CONSEQUENCE_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.live_ae_neurochemical_flow import (
    STATUS_SCHEMA as BODY_CHEMICAL_STATUS_SCHEMA,
    LiveAENeurochemicalFlowOwner,
)
from dsf_ai_service.substrate.whole_organism_neurochemical_mount import (
    ENVELOPE_SCHEMA as BODY_CHEMICAL_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.whole_organism_recovery_state import (
    COLD_SCHEMA as RECOVERY_ENVELOPE_SCHEMA,
    ExactWholeOrganismRecoveryOwner,
)
from dsf_ai_service.substrate.whole_organism_reflection_monitor import (
    REQUIRED_OWNER_IDS,
    WholeOrganismReflectionMonitorOwner,
)
from dsf_ai_service.substrate.whole_organism_structural_perturbation import (
    OWNER_STATE_ENVELOPE_SCHEMA as STRUCTURAL_ENVELOPE_SCHEMA,
    WholeOrganismStructuralPerturbationOwner,
)


KEY = b"reflection-monitor-test-authority-key"

_OWNER_TYPES = {
    "action": CausalThingActionIntentOwner,
    "attention-recognition": CausalRecognitionAttentionOwner,
    "body-chemical": LiveAENeurochemicalFlowOwner,
    "recovery": ExactWholeOrganismRecoveryOwner,
    "sensed-consequence": DurableSensedConsequenceOwner,
    "structural": WholeOrganismStructuralPerturbationOwner,
    "tapestry": CausalMosaicTapestryOwner,
}
_SNAPSHOT_SCHEMAS = {
    "action": ACTION_ENVELOPE_SCHEMA,
    "attention-recognition": ATTENTION_ENVELOPE_SCHEMA,
    "body-chemical": BODY_CHEMICAL_ENVELOPE_SCHEMA,
    "recovery": RECOVERY_ENVELOPE_SCHEMA,
    "sensed-consequence": CONSEQUENCE_ENVELOPE_SCHEMA,
    "structural": STRUCTURAL_ENVELOPE_SCHEMA,
    "tapestry": TAPESTRY_ENVELOPE_SCHEMA,
}
_STATUS_SCHEMAS = {
    "action": "guala.causal_thing.action_intent.status.v1",
    "attention-recognition": (
        "guala.causal_recognition_attention.status.v1"
    ),
    "body-chemical": BODY_CHEMICAL_STATUS_SCHEMA,
    "recovery": "guala.whole_organism.recovery.status.v1",
    "sensed-consequence": (
        "guala.durable_sensed_consequence.status.v1"
    ),
    "tapestry": "guala.causal_mosaic_tapestry.status.v1",
}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _snapshot(owner_id: str, generation: int = 0) -> bytes:
    return _canonical({
        "generation": generation,
        "schema": _SNAPSHOT_SCHEMAS[owner_id],
    })


@pytest.fixture
def exact_owners(monkeypatch):
    for owner_id, owner_type in _OWNER_TYPES.items():
        monkeypatch.setattr(
            owner_type,
            "snapshot_encoded",
            lambda self: self._test_snapshot,
        )
        if owner_id != "structural":
            monkeypatch.setattr(
                owner_type,
                "status",
                lambda self: dict(self._test_status),
            )
    monkeypatch.setattr(
        WholeOrganismStructuralPerturbationOwner,
        "current_state",
        property(lambda self: self._test_current_state),
    )
    monkeypatch.setattr(
        WholeOrganismStructuralPerturbationOwner,
        "in_flight",
        property(lambda self: self._test_in_flight),
    )

    owners = {}
    for owner_id in REQUIRED_OWNER_IDS:
        owner = object.__new__(_OWNER_TYPES[owner_id])
        owner._test_snapshot = _snapshot(owner_id)
        if owner_id == "structural":
            owner._test_current_state = SimpleNamespace(
                authority_receipt_sha256="a" * 64
            )
            owner._test_in_flight = None
        else:
            status = {
                "schema": _STATUS_SCHEMAS[owner_id],
                "state_bytes": len(owner._test_snapshot),
                "state_capacity_bytes": 1_048_576,
            }
            if owner_id in {
                "action",
                "attention-recognition",
                "tapestry",
            }:
                status.update({
                    "full_field": True,
                    "reduced_approximation": False,
                })
            if owner_id != "action":
                status["mechanism_state"] = "quiescent"
            owner._test_status = status
        owners[owner_id] = owner
    return owners


def _replace_snapshot(owners, owner_id: str, generation: int) -> None:
    owner = owners[owner_id]
    owner._test_snapshot = _snapshot(owner_id, generation)
    if owner_id != "structural":
        owner._test_status["state_bytes"] = len(owner._test_snapshot)


def _commit(owner: WholeOrganismReflectionMonitorOwner):
    prepared = owner.prepare()
    return owner.commit(prepared)


def test_no_change_is_truthful_quiescence(exact_owners):
    monitor = WholeOrganismReflectionMonitorOwner(
        authority_key=KEY,
        owners=exact_owners,
    )
    _commit(monitor)
    _commit(monitor)

    reflection = monitor.current_reflection
    assert reflection is not None
    assert reflection.sequence == 2
    assert reflection.moment_state == "quiescent"
    assert reflection.changed_owner_ids == ()
    assert reflection.meta_health == "healthy"
    assert reflection.reasons == ()


def test_multiple_owner_changes_retain_exact_facts_without_copying_state(
    exact_owners,
):
    monitor = WholeOrganismReflectionMonitorOwner(
        authority_key=KEY,
        owners=exact_owners,
    )
    _commit(monitor)
    _replace_snapshot(exact_owners, "structural", 1)
    _replace_snapshot(exact_owners, "body-chemical", 2)
    _replace_snapshot(exact_owners, "attention-recognition", 3)
    _commit(monitor)

    reflection = monitor.current_reflection
    assert reflection is not None
    assert reflection.moment_state == "perturbed"
    assert reflection.changed_owner_ids == (
        "attention-recognition",
        "body-chemical",
        "structural",
    )
    assert dict(reflection.current_snapshot_byte_counts) == {
        owner_id: len(exact_owners[owner_id]._test_snapshot)
        for owner_id in REQUIRED_OWNER_IDS
    }
    encoded = monitor.snapshot_encoded()
    assert b"exact_current_snapshots_hex" not in encoded
    assert all(
        exact_owners[owner_id]._test_snapshot not in encoded
        for owner_id in REQUIRED_OWNER_IDS
    )


def test_large_owner_states_are_never_duplicated_into_reflection_history(
    exact_owners,
):
    raw_marker = "raw-owner-state-must-not-be-durably-copied"
    for owner_id in REQUIRED_OWNER_IDS:
        owner = exact_owners[owner_id]
        owner._test_snapshot = _canonical({
            "generation": 0,
            "padding": raw_marker + ("x" * 1_048_576),
            "schema": _SNAPSHOT_SCHEMAS[owner_id],
        })
        if owner_id != "structural":
            owner._test_status["state_bytes"] = len(
                owner._test_snapshot
            )
            owner._test_status["state_capacity_bytes"] = (
                2 * 1_048_576
            )

    monitor = WholeOrganismReflectionMonitorOwner(
        authority_key=KEY,
        owners=exact_owners,
        max_history=16,
        max_state_bytes=64 * 1024,
    )
    for _ in range(40):
        _commit(monitor)

    encoded = monitor.snapshot_encoded()
    status = monitor.status()
    assert raw_marker.encode("utf-8") not in encoded
    assert status["records"] == status["history_capacity"] == 16
    assert status["state_bytes"] < 64 * 1024
    assert status["state_bytes"] == len(encoded)
    assert status["estimated_maximum_state_bytes"] == 64 * 1024


def test_missing_wrong_and_tampered_owner_fail_closed_without_mutation(
    exact_owners,
):
    missing = dict(exact_owners)
    del missing["recovery"]
    with pytest.raises(ValueError, match="exact required owner"):
        WholeOrganismReflectionMonitorOwner(
            authority_key=KEY,
            owners=missing,
        )

    wrong = dict(exact_owners)
    wrong["recovery"] = wrong["tapestry"]
    with pytest.raises(TypeError, match="owner type changed:recovery"):
        WholeOrganismReflectionMonitorOwner(
            authority_key=KEY,
            owners=wrong,
        )

    monitor = WholeOrganismReflectionMonitorOwner(
        authority_key=KEY,
        owners=exact_owners,
    )
    before = monitor.snapshot_encoded()
    exact_owners["recovery"]._test_snapshot = _canonical({
        "schema": "tampered.owner.state.v1",
    })
    with pytest.raises(ValueError, match="snapshot authority changed"):
        monitor.prepare()
    assert monitor.snapshot_encoded() == before
    assert monitor.current_reflection is None


def test_owner_health_mismatch_is_retained_as_fail_closed(exact_owners):
    monitor = WholeOrganismReflectionMonitorOwner(
        authority_key=KEY,
        owners=exact_owners,
    )
    exact_owners["sensed-consequence"]._test_status["state_bytes"] += 1
    _commit(monitor)

    reflection = monitor.current_reflection
    assert reflection is not None
    assert reflection.meta_health == "fail_closed"
    assert reflection.reasons == (
        "sensed-consequence:state_byte_count_changed",
    )
    assert monitor.status()["decision_authority"] is False
    encoded = monitor.snapshot_encoded()
    restored = WholeOrganismReflectionMonitorOwner.restore_encoded(
        authority_key=KEY,
        owners=exact_owners,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded


def test_long_run_rolls_with_authenticated_prefix_and_cold_restore(
    exact_owners,
):
    monitor = WholeOrganismReflectionMonitorOwner(
        authority_key=KEY,
        owners=exact_owners,
        max_history=5,
        max_state_bytes=32 * 1024,
    )
    for sequence in range(1, 74):
        _replace_snapshot(
            exact_owners,
            REQUIRED_OWNER_IDS[sequence % len(REQUIRED_OWNER_IDS)],
            sequence,
        )
        _commit(monitor)
        status = monitor.status()
        assert status["records"] <= 5
        assert status["state_bytes"] <= status["state_capacity_bytes"]

    status = monitor.status()
    assert status["records"] == 5
    assert status["evicted_prefix_count"] == 68
    assert status["earliest_retained_sequence"] == 69
    assert status["latest_sequence"] == 73
    assert isinstance(status["evicted_prefix_receipt_sha256"], str)
    encoded = monitor.snapshot_encoded()

    restored = WholeOrganismReflectionMonitorOwner.restore_encoded(
        authority_key=KEY,
        owners=exact_owners,
        encoded=encoded,
        max_state_bytes=32 * 1024,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.status() == status

    _replace_snapshot(exact_owners, "action", 74)
    undo = _commit(restored)
    assert restored.current_reflection.sequence == 74
    assert restored.status()["evicted_prefix_count"] == 69
    restored.rollback(undo)
    assert restored.snapshot_encoded() == encoded


def test_prepare_commit_discard_and_rollback_are_atomic(exact_owners):
    monitor = WholeOrganismReflectionMonitorOwner(
        authority_key=KEY,
        owners=exact_owners,
    )
    genesis = monitor.snapshot_encoded()

    discarded = monitor.prepare()
    with pytest.raises(RuntimeError, match="mutation is in flight"):
        monitor.snapshot_encoded()
    monitor.discard(discarded)
    assert monitor.snapshot_encoded() == genesis
    with pytest.raises(ValueError, match="preparation authority changed"):
        monitor.commit(discarded)

    prepared = monitor.prepare()
    undo = monitor.commit(prepared)
    committed = monitor.snapshot_encoded()
    assert committed != genesis
    with pytest.raises(ValueError, match="preparation authority changed"):
        monitor.commit(prepared)
    monitor.rollback(undo)
    assert monitor.snapshot_encoded() == genesis
    with pytest.raises(ValueError, match="preparation authority changed"):
        monitor.rollback(undo)


def test_authenticated_cold_restore_and_live_owner_continuity(exact_owners):
    monitor = WholeOrganismReflectionMonitorOwner(
        authority_key=KEY,
        owners=exact_owners,
    )
    _commit(monitor)
    _replace_snapshot(exact_owners, "action", 8)
    _replace_snapshot(exact_owners, "sensed-consequence", 9)
    _commit(monitor)
    encoded = monitor.snapshot_encoded()

    restored = WholeOrganismReflectionMonitorOwner.restore_encoded(
        authority_key=KEY,
        owners=exact_owners,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.current_reflection == monitor.current_reflection

    tampered = bytearray(encoded)
    tampered[-2] = ord("0") if tampered[-2] != ord("0") else ord("1")
    with pytest.raises(ValueError):
        WholeOrganismReflectionMonitorOwner.restore_encoded(
            authority_key=KEY,
            owners=exact_owners,
            encoded=bytes(tampered),
        )

    _replace_snapshot(exact_owners, "action", 10)
    with pytest.raises(ValueError, match="restored owner state changed"):
        WholeOrganismReflectionMonitorOwner.restore_encoded(
            authority_key=KEY,
            owners=exact_owners,
            encoded=encoded,
        )
