from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.substrate.physical_internal_body_state import (
    InternalBodyCapacity,
    InternalBodyEvolutionRequest,
    InternalConservationExchange,
    InternalMechanism,
    InternalMechanismMount,
    InternalPhysicalParameter,
    InternalPhysicalQuantity,
    InternalQuantityChange,
    MechanismAvailability,
    NeurochemicalCompartmentReference,
    PhysicalInternalBodyStateAuthority,
    QuantityEvolutionKind,
    REQUIRED_QUANTITY_ROLES,
    create_embodiment_proprioceptive_internal_body_authority,
    create_physical_internal_body_manifest,
)
from dsf_ai_service.substrate.live_ae_neurochemical_flow import (
    live_ae_neurochemical_compartment_references,
)


KEY = b"physical-internal-body-test-authority-key-v1"


def _receipt(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


_UNITS = {
    "position_x": "millimetre",
    "position_y": "millimetre",
    "position_z": "millimetre",
    "supported_load": "gram-force",
    "linear_acceleration_x": "millimetre-per-second-squared",
    "linear_acceleration_y": "millimetre-per-second-squared",
    "linear_acceleration_z": "millimetre-per-second-squared",
    "orientation_roll": "turn",
    "orientation_pitch": "turn",
    "orientation_yaw": "turn",
    "core_temperature": "millikelvin",
    "compartment_temperature": "millikelvin",
    "tissue_integrity": "integrity-quantity",
    "nociceptive_load": "damage-flux",
    "energy_inventory": "microjoule",
    "water_inventory": "microlitre",
    "respiratory_volume": "microlitre",
    "respiratory_pressure": "micropascal",
    "oxygen_inventory": "nanomole",
    "carbon_dioxide_inventory": "nanomole",
    "pulse_phase": "turn",
    "perfusion_rate": "microlitre-per-second",
    "visceral_load": "micropascal",
    "fatigue_load": "fatigue-quantity",
    "recovery_reserve": "recovery-quantity",
    "circadian_phase": "turn",
}

_CYCLIC_ROLES = frozenset(
    {
        "orientation_roll",
        "orientation_pitch",
        "orientation_yaw",
        "pulse_phase",
        "circadian_phase",
    }
)

_SIGNED_ROLES = frozenset(
    {
        "position_x",
        "position_y",
        "position_z",
        "linear_acceleration_x",
        "linear_acceleration_y",
        "linear_acceleration_z",
        "respiratory_pressure",
    }
)

_CONSERVATION_GROUPS = {
    "energy_inventory": "inventory:energy",
    "water_inventory": "inventory:water",
    "oxygen_inventory": "inventory:oxygen",
    "carbon_dioxide_inventory": "inventory:carbon-dioxide",
}


def _manifest(*, max_transitions: int = 8):
    quantities = []
    parameters = []
    mechanisms = []
    for mechanism in InternalMechanism:
        unavailable = mechanism is InternalMechanism.VISCERAL
        quantity_ids = []
        for role in REQUIRED_QUANTITY_ROLES[mechanism]:
            quantity_id = f"quantity:{mechanism.value}:{role}"
            quantity_ids.append(quantity_id)
            if unavailable:
                quantity = InternalPhysicalQuantity(
                    quantity_id=quantity_id,
                    mechanism=mechanism,
                    role=role,
                    unit=_UNITS[role],
                    evolution_kind=QuantityEvolutionKind.UNAVAILABLE,
                    lower_bound=None,
                    upper_bound=None,
                    initial_value=None,
                )
            elif role in _CYCLIC_ROLES:
                quantity = InternalPhysicalQuantity(
                    quantity_id=quantity_id,
                    mechanism=mechanism,
                    role=role,
                    unit=_UNITS[role],
                    evolution_kind=QuantityEvolutionKind.CYCLIC,
                    lower_bound=Fraction(0),
                    upper_bound=Fraction(1),
                    initial_value=Fraction(0),
                    cyclic_modulus=Fraction(1),
                )
            else:
                lower = (
                    Fraction(-1_000)
                    if role in _SIGNED_ROLES
                    else Fraction(0)
                )
                initial = (
                    Fraction(300)
                    if role
                    in {"core_temperature", "compartment_temperature"}
                    else Fraction(100)
                    if role == "tissue_integrity"
                    else Fraction(10)
                    if role in _CONSERVATION_GROUPS
                    else Fraction(0)
                )
                quantity = InternalPhysicalQuantity(
                    quantity_id=quantity_id,
                    mechanism=mechanism,
                    role=role,
                    unit=_UNITS[role],
                    evolution_kind=QuantityEvolutionKind.LINEAR,
                    lower_bound=lower,
                    upper_bound=Fraction(1_000),
                    initial_value=initial,
                    conservation_group_id=_CONSERVATION_GROUPS.get(
                        role
                    ),
                )
            quantities.append(quantity)
        parameter_id = f"parameter:{mechanism.value}:physical-mount"
        required_parameters = (
            ()
            if mechanism is InternalMechanism.NEUROCHEMICAL
            else (parameter_id,)
        )
        if not unavailable and required_parameters:
            parameters.append(
                InternalPhysicalParameter(
                    parameter_id=parameter_id,
                    mechanism=mechanism,
                    unit="mounted-physical-parameter",
                    value=Fraction(1),
                    derivation_receipt_sha256=_receipt(parameter_id),
                )
            )
        mechanisms.append(
            InternalMechanismMount(
                mechanism=mechanism,
                availability=(
                    MechanismAvailability.UNAVAILABLE
                    if unavailable
                    else MechanismAvailability.AVAILABLE
                ),
                quantity_ids=tuple(sorted(quantity_ids)),
                required_parameter_ids=required_parameters,
                unavailable_reason=(
                    "visceral compliance and geometry are not mounted"
                    if unavailable
                    else None
                ),
            )
        )
    return create_physical_internal_body_manifest(
        authority_key=KEY,
        manifest_id="test-physical-internal-body-v1",
        structural_time_unit="second",
        capacity=InternalBodyCapacity(
            max_quantities=64,
            max_parameters=32,
            max_neurochemical_references=8,
            max_changes_per_transition=16,
            max_conservation_exchanges_per_transition=8,
            max_transitions=max_transitions,
            max_state_bytes=2_000_000,
        ),
        mechanisms=mechanisms,
        quantities=quantities,
        parameters=parameters,
        neurochemical_references=(
            NeurochemicalCompartmentReference(
                reference_id="neurochemical:circulation:dopamine",
                species_id="species:dopamine",
                node_id="node:circulation",
                quantity_unit="molecule",
                manifest_receipt_sha256=_receipt(
                    "neurochemical-manifest"
                ),
                compartment_receipt_sha256=_receipt(
                    "neurochemical-compartment"
                ),
            ),
        ),
    )


def _request(
    authority: PhysicalInternalBodyStateAuthority,
    *,
    source_label: str,
    end: Fraction,
    position_delta: Fraction = Fraction(1),
    energy_delta: Fraction = Fraction(-1),
) -> InternalBodyEvolutionRequest:
    changes = tuple(
        sorted(
            (
                InternalQuantityChange(
                    quantity_id=(
                        "quantity:energy_water:energy_inventory"
                    ),
                    delta=energy_delta,
                ),
                InternalQuantityChange(
                    quantity_id=(
                        "quantity:proprioception:position_x"
                    ),
                    delta=position_delta,
                ),
            ),
            key=lambda value: value.quantity_id,
        )
    )
    return InternalBodyEvolutionRequest(
        source_kind="authenticated-physical-boundary",
        physical_source_receipt_sha256=_receipt(source_label),
        source_time_start=authority.state.source_time,
        source_time_end=end,
        expected_state_receipt_sha256=(
            authority.state.authority_receipt_sha256
        ),
        changes=changes,
        conservation_exchanges=(
            InternalConservationExchange(
                conservation_group_id="inventory:energy",
                net_external_delta=energy_delta,
                physical_exchange_receipt_sha256=_receipt(
                    f"{source_label}:energy-exchange"
                ),
            ),
        ),
    )


def test_manifest_retains_independent_quantities_and_unavailable_truth():
    manifest = _manifest()
    authority = PhysicalInternalBodyStateAuthority(
        authority_key=KEY,
        manifest=manifest,
    )

    assert tuple(value.mechanism for value in manifest.mechanisms) == tuple(
        InternalMechanism
    )
    assert {
        value.role for value in manifest.quantities
    }.issuperset(
        {
            role
            for roles in REQUIRED_QUANTITY_ROLES.values()
            for role in roles
        }
    )
    state = authority.state
    visceral = dict(state.quantity_values)[
        "quantity:visceral:visceral_load"
    ]
    assert visceral is None
    assert state.unavailable_mechanisms == (
        (
            "visceral",
            "visceral compliance and geometry are not mounted",
        ),
    )
    assert state.neurochemical_reference_receipts == (
        (
            "neurochemical:circulation:dopamine",
            _receipt("neurochemical-compartment"),
        ),
    )
    status = authority.status()
    assert status["sensory_lane_mapping"] is None
    assert status["cognition_authority"] is False
    assert status["reduced_body_lane"] is False


def test_prepare_commit_and_rollback_are_exact_and_atomic():
    authority = PhysicalInternalBodyStateAuthority(
        authority_key=KEY,
        manifest=_manifest(),
    )
    genesis = authority.snapshot_encoded()
    before = authority.state
    prepared = authority.prepare_evolution(
        _request(
            authority,
            source_label="physical-step-1",
            end=Fraction(1),
        )
    )

    assert authority.state == before
    assert dict(prepared.after.quantity_values)[
        "quantity:proprioception:position_x"
    ] == Fraction(1)
    assert dict(prepared.after.quantity_values)[
        "quantity:energy_water:energy_inventory"
    ] == Fraction(9)

    undo = authority.commit_prepared(prepared)
    assert authority.state == prepared.after
    assert authority.transitions == (prepared.transition,)
    authority.rollback_committed(undo)
    assert authority.snapshot_encoded() == genesis


def test_conservation_bounds_and_unavailable_evolution_fail_closed():
    authority = PhysicalInternalBodyStateAuthority(
        authority_key=KEY,
        manifest=_manifest(),
    )
    valid = _request(
        authority,
        source_label="physical-step-invalid-conservation",
        end=Fraction(1),
    )
    with pytest.raises(ValueError, match="conservation failed"):
        authority.prepare_evolution(
            replace(valid, conservation_exchanges=())
        )

    with pytest.raises(ValueError, match="physical bounds"):
        authority.prepare_evolution(
            replace(
                valid,
                physical_source_receipt_sha256=_receipt(
                    "physical-step-invalid-bound"
                ),
                changes=tuple(
                    sorted(
                        (
                            valid.changes[0],
                            InternalQuantityChange(
                                quantity_id=(
                                    "quantity:proprioception:position_x"
                                ),
                                delta=Fraction(2_000),
                            ),
                        ),
                        key=lambda value: value.quantity_id,
                    )
                ),
            )
        )

    unavailable = InternalBodyEvolutionRequest(
        source_kind="authenticated-physical-boundary",
        physical_source_receipt_sha256=_receipt(
            "physical-step-invalid-visceral"
        ),
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        expected_state_receipt_sha256=(
            authority.state.authority_receipt_sha256
        ),
        changes=(
            InternalQuantityChange(
                quantity_id="quantity:visceral:visceral_load",
                delta=Fraction(1),
            ),
        ),
    )
    with pytest.raises(ValueError, match="unavailable"):
        authority.prepare_evolution(unavailable)


def test_deterministic_replay_and_authenticated_cold_restore():
    manifest = _manifest()
    left = PhysicalInternalBodyStateAuthority(
        authority_key=KEY,
        manifest=manifest,
    )
    right = PhysicalInternalBodyStateAuthority(
        authority_key=KEY,
        manifest=manifest,
    )
    for index in range(1, 3):
        for authority in (left, right):
            prepared = authority.prepare_evolution(
                _request(
                    authority,
                    source_label=f"deterministic-source-{index}",
                    end=Fraction(index),
                )
            )
            authority.commit_prepared(prepared)

    encoded = left.snapshot_encoded()
    assert encoded == right.snapshot_encoded()
    restored = PhysicalInternalBodyStateAuthority.restore_encoded(
        authority_key=KEY,
        manifest=manifest,
        encoded=encoded,
    )
    assert restored.state == left.state
    assert restored.transitions == left.transitions
    assert restored.snapshot_encoded() == encoded

    envelope = json.loads(encoded)
    envelope["body"]["state"]["sequence"] += 1
    tampered = json.dumps(
        envelope,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="authentication failed"):
        PhysicalInternalBodyStateAuthority.restore_encoded(
            authority_key=KEY,
            manifest=manifest,
            encoded=tampered,
        )


def test_transition_capacity_fails_without_state_mutation():
    authority = PhysicalInternalBodyStateAuthority(
        authority_key=KEY,
        manifest=_manifest(max_transitions=1),
    )
    prepared = authority.prepare_evolution(
        _request(
            authority,
            source_label="capacity-source-1",
            end=Fraction(1),
        )
    )
    authority.commit_prepared(prepared)
    state_at_capacity = authority.state

    with pytest.raises(RuntimeError, match="capacity"):
        authority.prepare_evolution(
            _request(
                authority,
                source_label="capacity-source-2",
                end=Fraction(2),
            )
        )
    assert authority.state == state_at_capacity
    assert len(authority.transitions) == 1


def test_missing_law_parameters_cannot_be_declared_available():
    manifest = _manifest()
    mechanisms = tuple(
        replace(
            value,
            availability=MechanismAvailability.AVAILABLE,
            unavailable_reason=None,
        )
        if value.mechanism is InternalMechanism.VISCERAL
        else value
        for value in manifest.mechanisms
    )
    with pytest.raises(ValueError, match="physical parameters"):
        create_physical_internal_body_manifest(
            authority_key=KEY,
            manifest_id="invalid-available-visceral-v1",
            structural_time_unit="second",
            capacity=manifest.capacity,
            mechanisms=mechanisms,
            quantities=manifest.quantities,
            parameters=manifest.parameters,
            neurochemical_references=(
                manifest.neurochemical_references
            ),
        )


def _proprioceptive_authority(*, references=(), world_label="world"):
    return create_embodiment_proprioceptive_internal_body_authority(
        authority_key=KEY,
        world_observation_receipt_sha256=_receipt(world_label),
        position_x_mm=Fraction(0),
        position_y_mm=Fraction(0),
        position_z_mm=Fraction(0),
        supported_load_grams=Fraction(0),
        neurochemical_references=references,
    )


def test_exact_neurochemical_manifest_migration_archives_old_lineage():
    prior = _proprioceptive_authority()
    prior.commit_prepared(prior.prepare_evolution(
        InternalBodyEvolutionRequest(
            source_kind="authenticated-world-motion",
            physical_source_receipt_sha256=_receipt("world-motion"),
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
            expected_state_receipt_sha256=(
                prior.state.authority_receipt_sha256
            ),
            changes=(
                InternalQuantityChange(
                    quantity_id=(
                        "quantity:proprioception:position_x"
                    ),
                    delta=Fraction(7),
                ),
            ),
        )
    ))
    encoded = prior.snapshot_encoded()
    current = _proprioceptive_authority(
        references=live_ae_neurochemical_compartment_references(KEY)
    )

    migrated = PhysicalInternalBodyStateAuthority.restore_encoded(
        authority_key=KEY,
        manifest=current.manifest,
        encoded=encoded,
        prior_manifest_for_migration=prior.manifest,
    )

    assert dict(migrated.state.quantity_values)[
        "quantity:proprioception:position_x"
    ] == Fraction(7)
    assert migrated.state.source_time == Fraction(1)
    assert migrated.status()["manifest_migration_archive_present"] is True
    assert (
        migrated.status()["manifest_migration_archived_transitions"]
        == 1
    )
    migrated_encoded = migrated.snapshot_encoded()
    restored = PhysicalInternalBodyStateAuthority.restore_encoded(
        authority_key=KEY,
        manifest=current.manifest,
        encoded=migrated_encoded,
    )
    assert restored.snapshot_encoded() == migrated_encoded


def test_manifest_migration_refuses_wrong_prior_and_changed_quantity():
    prior = _proprioceptive_authority()
    encoded = prior.snapshot_encoded()
    current = _proprioceptive_authority(
        references=live_ae_neurochemical_compartment_references(KEY)
    )
    wrong_prior = _proprioceptive_authority(world_label="other-world")
    with pytest.raises(ValueError, match="prior manifest receipt"):
        PhysicalInternalBodyStateAuthority.restore_encoded(
            authority_key=KEY,
            manifest=current.manifest,
            encoded=encoded,
            prior_manifest_for_migration=wrong_prior.manifest,
        )

    quantities = tuple(
        replace(value, unit="changed-unit")
        if value.quantity_id
        == "quantity:proprioception:position_x"
        else value
        for value in current.manifest.quantities
    )
    changed = create_physical_internal_body_manifest(
        authority_key=KEY,
        manifest_id=current.manifest.manifest_id,
        structural_time_unit=current.manifest.structural_time_unit,
        capacity=current.manifest.capacity,
        mechanisms=current.manifest.mechanisms,
        quantities=quantities,
        parameters=current.manifest.parameters,
        neurochemical_references=(
            current.manifest.neurochemical_references
        ),
    )
    with pytest.raises(ValueError, match="physical contracts"):
        PhysicalInternalBodyStateAuthority.restore_encoded(
            authority_key=KEY,
            manifest=changed,
            encoded=encoded,
            prior_manifest_for_migration=prior.manifest,
        )
