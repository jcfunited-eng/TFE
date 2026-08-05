from __future__ import annotations

import json
from dataclasses import replace

import pytest

from dsf_ai_service.substrate.neurochemical_flow import (
    TemporalDriverKind,
)
from dsf_ai_service.substrate.whole_organism_neurochemical_mount import (
    UnavailableChemicalReaction,
    WholeOrganismNeurochemicalMountOwner,
    WholeOrganismNeurochemicalMountProfile,
)
from dsf_ai_service.substrate.whole_organism_recovery_state import (
    ExactWholeOrganismRecoveryOwner,
)
from tests.test_neurochemical_flow import (
    AUTHORITY_KEY as FLOW_KEY,
    CLOCK_ISSUER,
    _bounds,
    _manifest,
)
from tests.test_whole_organism_recovery_state import (
    BODY_KEY,
    RECOVERY_KEY,
    _body_owner,
    _settlement,
)


MOUNT_KEY = b"whole-organism-neurochemical-mount-test-key"


def _unsupported():
    return (
        UnavailableChemicalReaction.create(
            reaction_id="reaction:major-species-kinetics",
            reason="no ratified exact kinetic constants",
            derivation_evidence={
                "available_subset": "conservative_transport_and_recovery",
                "missing": "exact_species_kinetic_constants",
            },
        ),
    )


def _stack(*, all_zero=False):
    body = _body_owner()
    recovery = ExactWholeOrganismRecoveryOwner(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
    )
    settlement = _settlement(
        "chemical-boundary",
        negative_space=False,
    )
    recovery.commit_prepared(recovery.prepare_observation(settlement))
    manifest = _manifest(
        all_zero=all_zero,
        include_conversion=False,
    )
    profile = WholeOrganismNeurochemicalMountProfile.create(
        profile_id="whole-organism-neurochemical-test",
        max_upstream_receipts_per_boundary=4,
        max_state_bytes=8 * 1024 * 1024,
    )
    owner = WholeOrganismNeurochemicalMountOwner(
        authority_key=MOUNT_KEY,
        profile=profile,
        flow_authority_key=FLOW_KEY,
        flow_manifest=manifest,
        body_authority=body,
        recovery_owner=recovery,
        unavailable_reactions=_unsupported(),
    )
    receipt = CLOCK_ISSUER.sign_temporal(
        chemistry_sequence=1,
        event_id="event:whole-organism-chemical-boundary",
        source_time_start=settlement.source_time_start,
        source_time_end=settlement.source_time_end,
        driver_kind=TemporalDriverKind.INTRINSIC,
        lane_id="diffusion:a:pre-post",
        lane_enabled=True,
        physical_parameter_path=(
            "lane_state/diffusion:a:pre-post/enabled"
        ),
    )
    return (
        body,
        recovery,
        settlement,
        manifest,
        profile,
        owner,
        receipt,
    )


def test_mounted_boundary_moves_nonflat_conserves_and_targets_locally():
    (
        _body,
        _recovery,
        settlement,
        _manifest_value,
        _profile,
        owner,
        receipt,
    ) = _stack()
    initial_mass = owner.flow_state.exact_conserved_mass
    prepared = owner.prepare(
        settlement=settlement,
        upstream_receipts=(receipt,),
    )

    transition = prepared.transition
    exposures = {
        value.target_id: value for value in transition.local_target_exposures
    }
    assert len(exposures) == 2
    assert (
        _bounds(exposures["target:post-conductance"].component_value)
        != _bounds(exposures["target:post-metabolism"].component_value)
    )
    before_values = dict(owner.flow_state.component_values)
    after_values = dict(prepared._staged_flow.state.component_values)
    assert _bounds(before_values["component:a:pre"]) != _bounds(
        after_values["component:a:pre"]
    )
    assert _bounds(after_values["component:a:pre"]) != _bounds(
        after_values["component:a:post"]
    )
    assert prepared._staged_flow.state.exact_conserved_mass == initial_mass
    assert prepared.boundary.settlement_receipt_sha256 == (
        settlement.authority_receipt_sha256
    )
    assert prepared.boundary.moment_state == "perturbed"
    assert prepared.boundary.unavailable_reactions == _unsupported()
    assert not any(
        token in json.dumps(prepared.boundary.record())
        for token in ("mood", "reward", "salience", "global_score")
    )

    owner.commit(prepared)
    assert owner.flow_state == prepared._staged_flow.state


def test_exact_zero_is_true_quiescence_without_fabricated_activity():
    (
        _body,
        _recovery,
        settlement,
        _manifest_value,
        _profile,
        owner,
        receipt,
    ) = _stack(all_zero=True)
    assert owner.status()["mechanism_state"] == "quiescent"

    prepared = owner.prepare(
        settlement=settlement,
        upstream_receipts=(receipt,),
    )
    assert prepared.boundary.moment_state == "quiescent"
    assert all(
        value == 0
        for _component_id, value
        in prepared._staged_flow.state.component_values
    )
    assert prepared.transition.untouched_component_ids


def test_discard_rollback_tamper_and_cold_restore_are_atomic():
    (
        body,
        recovery,
        settlement,
        manifest,
        profile,
        owner,
        receipt,
    ) = _stack()
    before = owner.snapshot_encoded()

    staged = owner.prepare(
        settlement=settlement,
        upstream_receipts=(receipt,),
    )
    owner.discard(staged)
    assert owner.snapshot_encoded() == before

    forged = replace(receipt, ed25519_signature_hex="0" * 128)
    with pytest.raises(ValueError):
        owner.prepare(
            settlement=settlement,
            upstream_receipts=(forged,),
        )
    assert owner.snapshot_encoded() == before

    undo = owner.commit(owner.prepare(
        settlement=settlement,
        upstream_receipts=(receipt,),
    ))
    encoded = owner.snapshot_encoded()
    assert encoded != before
    cold = WholeOrganismNeurochemicalMountOwner.restore_encoded(
        authority_key=MOUNT_KEY,
        profile=profile,
        flow_authority_key=FLOW_KEY,
        flow_manifest=manifest,
        body_authority=body,
        recovery_owner=recovery,
        unavailable_reactions=_unsupported(),
        encoded=encoded,
    )
    assert cold.snapshot_encoded() == encoded
    assert cold.flow_state == owner.flow_state

    owner.rollback(undo)
    assert owner.snapshot_encoded() == before

    raw = json.loads(encoded)
    raw["body"]["boundary"]["moment_state"] = "forged"
    tampered = json.dumps(
        raw,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    with pytest.raises(ValueError, match="authority"):
        WholeOrganismNeurochemicalMountOwner.restore_encoded(
            authority_key=MOUNT_KEY,
            profile=profile,
            flow_authority_key=FLOW_KEY,
            flow_manifest=manifest,
            body_authority=body,
            recovery_owner=recovery,
            unavailable_reactions=_unsupported(),
            encoded=tampered,
        )


def test_unspecified_conversion_is_refused_inside_real_mount():
    body = _body_owner()
    recovery = ExactWholeOrganismRecoveryOwner(
        authority_key=RECOVERY_KEY,
        physical_body_authority=body,
    )
    profile = WholeOrganismNeurochemicalMountProfile.create(
        profile_id="conversion-refusal",
        max_upstream_receipts_per_boundary=2,
        max_state_bytes=8 * 1024 * 1024,
    )
    with pytest.raises(ValueError, match="refuses unspecified conversions"):
        WholeOrganismNeurochemicalMountOwner(
            authority_key=MOUNT_KEY,
            profile=profile,
            flow_authority_key=FLOW_KEY,
            flow_manifest=_manifest(include_conversion=True),
            body_authority=body,
            recovery_owner=recovery,
            unavailable_reactions=_unsupported(),
        )
