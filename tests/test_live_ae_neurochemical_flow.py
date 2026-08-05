from __future__ import annotations

import json
from fractions import Fraction

import pytest

from dsf_ai_service.substrate.live_ae_neurochemical_flow import (
    LiveAENeurochemicalFlowOwner,
    SENSE_IDS,
    build_live_ae_neurochemical_manifest,
    live_ae_neurochemical_compartment_references,
)
from dsf_ai_service.substrate.ae_local_receptor import (
    verify_ae_local_receptor_activation,
)
from dsf_ai_service.substrate.whole_organism_recovery_state import (
    ExactWholeOrganismRecoveryOwner,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from tests.test_whole_organism_episode import _settlement
from tests.test_whole_organism_recovery_state import (
    RECOVERY_KEY,
    _body_owner,
)
from tests.test_whole_organism_neuron_population import (
    _settlement as _population_settlement,
)


ROOT_KEY = b"live-ae-neurochemical-flow-test-root-key"


def _stack():
    body = _body_owner()
    recovery = ExactWholeOrganismRecoveryOwner(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
    )
    owner = LiveAENeurochemicalFlowOwner(
        root_key=ROOT_KEY,
        body_authority=body,
        recovery_owner=recovery,
        max_state_bytes=8 * 1024 * 1024,
    )
    return body, recovery, owner


def _recover(recovery, settlement):
    recovery.commit_prepared(recovery.prepare_observation(settlement))


def test_manifest_is_fixed_bounded_conservative_and_not_biological_claim():
    first = build_live_ae_neurochemical_manifest(ROOT_KEY)
    second = build_live_ae_neurochemical_manifest(ROOT_KEY)
    assert first == second
    assert len(first.components) == 15
    assert len(first.impulse_routes) == 2 * len(SENSE_IDS)
    assert len(first.drift_lanes) == 3
    assert not first.conversions
    assert first.capacity.max_components == 32
    assert first.capacity.max_active_block_components == 4
    encoded = json.dumps(first.payload(), sort_keys=True)
    for forbidden in ("dopamine", "serotonin", "mood", "reward", "salience"):
        assert forbidden not in encoded
    references = live_ae_neurochemical_compartment_references(ROOT_KEY)
    assert len(references) == len(first.components)
    assert {
        value.manifest_receipt_sha256 for value in references
    } == {first.authority_receipt_sha256}


def test_two_noncontiguous_sensory_epochs_advance_one_contiguous_field():
    _body, recovery, owner = _stack()
    first = _settlement("chemical-first", start=Fraction(5))
    _recover(recovery, first)
    initial = owner.snapshot_encoded()
    initial_mass = owner.flow_state.exact_conserved_mass

    boundary_one = owner.advance(first)
    assert boundary_one is not None
    assert owner.flow_state.source_time == (
        first.source_time_end - first.source_time_start
    )
    values_one = dict(owner.flow_state.component_values)
    assert values_one["component:ae-excitation:sight:a"] == 0
    assert values_one["component:ae-excitation:sight:b"] == 1
    assert owner.flow_state.exact_conserved_mass == initial_mass
    assert owner.snapshot_encoded() != initial

    second = _settlement("chemical-second", start=Fraction(20))
    _recover(recovery, second)
    boundary_two = owner.advance(second)
    total_duration = (
        first.source_time_end - first.source_time_start
        + second.source_time_end - second.source_time_start
    )
    assert owner.flow_state.source_time == total_duration
    values_two = dict(owner.flow_state.component_values)
    assert values_two["component:ae-excitation:sight:a"] == 1
    assert values_two["component:ae-excitation:sight:b"] == 0
    assert owner.flow_state.exact_conserved_mass == initial_mass
    assert boundary_two.prior_boundary_receipt_sha256 == (
        boundary_one.authority_receipt_sha256
    )


def test_cold_restore_is_byte_exact_and_tamper_fails_closed():
    body, recovery, owner = _stack()
    settlement = _settlement("chemical-cold", start=Fraction(9))
    _recover(recovery, settlement)
    owner.advance(settlement)
    encoded = owner.snapshot_encoded()

    restored = LiveAENeurochemicalFlowOwner.restore_encoded(
        root_key=ROOT_KEY,
        body_authority=body,
        recovery_owner=recovery,
        max_state_bytes=8 * 1024 * 1024,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.flow_state == owner.flow_state
    status = restored.status()
    assert status["available"] is True
    assert status["conservative"] is True
    assert status["local_receptor_coupling"] == (
        "available_exact_event_state"
    )
    assert status["state_bytes"] <= status["state_capacity_bytes"]

    tampered = bytearray(encoded)
    tampered[-2] = ord("0") if tampered[-2] != ord("0") else ord("1")
    with pytest.raises(ValueError):
        LiveAENeurochemicalFlowOwner.restore_encoded(
            root_key=ROOT_KEY,
            body_authority=body,
            recovery_owner=recovery,
            max_state_bytes=8 * 1024 * 1024,
            encoded=bytes(tampered),
        )


def test_current_boundary_issues_one_exact_receipt_per_sense():
    _body, recovery, owner = _stack()
    settlement = _settlement("chemical-receptors", start=Fraction(4))
    _recover(recovery, settlement)
    owner.advance(settlement)

    activations = owner.local_receptor_activations(settlement)
    assert tuple(value.sense for value in activations) == SENSE_IDS
    for activation in activations:
        verify_ae_local_receptor_activation(
            activation,
            owner.local_receptor_verifier,
        )
        assert activation.settlement_receipt_sha256 == (
            settlement.authority_receipt_sha256
        )
    by_sense = {value.sense: value for value in activations}
    assert by_sense["sight"].activation_state == 1
    assert by_sense["sight"].target_id in {
        "target:ae-excitation:sight:a",
        "target:ae-excitation:sight:b",
    }
    assert {
        value.activation_state
        for sense, value in by_sense.items()
        if sense != "sight"
    } == {0}


def test_runtime_acceptance_advances_the_mounted_live_field(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "live-ae-neurochemical-runtime-test-key",
    )
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    runtime = Guala()
    try:
        runtime.load_full_state(str(tmp_path))
        settlement = _settlement("chemical-runtime", start=Fraction(0))
        before = runtime._whole_organism_neurochemical_owner.snapshot_encoded()
        runtime._accept_causal_settlement(settlement)
        owner = runtime._whole_organism_neurochemical_owner
        assert owner.snapshot_encoded() != before
        assert owner.boundary.settlement_receipt_sha256 == (
            settlement.authority_receipt_sha256
        )
        assert owner.flow_state.source_time == (
            settlement.source_time_end - settlement.source_time_start
        )
        observation = runtime.observation_snapshot()[
            "internal_neurochemical_flow"
        ]
        assert observation["available"] is True
        assert observation["conservative"] is True
        assert observation["cold_restorable"] is True
        assert (
            runtime._physical_internal_body_state.status()[
                "neurochemical_reference_count"
            ]
            == 15
        )
    finally:
        runtime.shutdown()


