from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.substrate import neurochemical_upstream_receipt
from dsf_ai_service.substrate import neurochemical_physical_quantity
from dsf_ai_service.glew_runtime.certified_backend import CertifiedBall
from dsf_ai_service.substrate.neurochemical_flow import (
    CausalSourceKind,
    DirectedLaneKind,
    EvolutionStatus,
    ExtracellularDiffusionInterface,
    FirstOrderNeurochemicalConversion,
    LocalNeurochemicalTarget,
    LocalTargetKind,
    MechanismAvailability,
    NeurochemicalBackendMount,
    NeurochemicalCapacity,
    NeurochemicalCausalEvent,
    NeurochemicalCompartmentMount,
    NeurochemicalFlowFieldAuthority,
    NeurochemicalFlowManifest,
    NeurochemicalDriftLane,
    NeurochemicalImpulseRoute,
    NeurochemicalNodeMount,
    NeurochemicalSpeciesMount,
    NodeKind,
    NonlinearMechanismKind,
    PhysicalReceiptRoutePermission,
    QuantityDomain,
    TemporalDriverKind,
    TemporalReceiptRoutePermission,
    UnavailableNonlinearMechanism,
    create_neurochemical_flow_manifest,
)
from dsf_ai_service.substrate.neurochemical_upstream_receipt import (
    NeurochemicalUpstreamIssuerAuthority,
    UpstreamAuthorityKind,
    verify_upstream_receipt,
)
from dsf_ai_service.substrate.neurochemical_physical_quantity import (
    PhysicalQuantityIssuerAuthority,
    SignedPhysicalQuantity,
)


AUTHORITY_KEY = b"neurochemical-flow-test-authority-key"
ACTION_ISSUER = NeurochemicalUpstreamIssuerAuthority.from_private_key_bytes(
    issuer_id="issuer:action",
    authority_kind=UpstreamAuthorityKind.ACTION,
    private_key_bytes=bytes.fromhex("11" * 32),
)
CLOCK_ISSUER = NeurochemicalUpstreamIssuerAuthority.from_private_key_bytes(
    issuer_id="issuer:clock",
    authority_kind=UpstreamAuthorityKind.CLOCK,
    private_key_bytes=bytes.fromhex("22" * 32),
)
QUANTITY_ISSUER = PhysicalQuantityIssuerAuthority.from_private_key_bytes(
    issuer_id="issuer:physical-quantity",
    private_key_bytes=bytes.fromhex("44" * 32),
)


def _evidence(identifier: str, equation: str) -> bytes:
    return json.dumps(
        {
            "equation": equation,
            "exact_arithmetic": "Fraction",
            "fact_id": identifier,
            "measurement_contract": "test-mounted-physical-fact",
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _quantity(
    identifier: str,
    value: Fraction,
    unit: str,
    *,
    positive: bool,
    equation: str,
) -> SignedPhysicalQuantity:
    del positive, equation
    if identifier == "quantity:structural-time":
        role = "manifest/structural_time_unit"
    elif identifier.startswith("quantity:mass:"):
        species_name = identifier.removeprefix("quantity:mass:")
        role = (
            f"species/species:{species_name}/conserved_mass_per_quantity"
        )
    elif identifier.startswith("quantity:volume:"):
        node_id = identifier.removeprefix("quantity:volume:")
        role = f"node/{node_id}/volume"
    elif identifier.startswith("quantity:initial:"):
        component_id = identifier.removeprefix("quantity:initial:")
        role = f"component/{component_id}/initial_quantity"
    elif identifier.startswith("quantity:rate:reaction:"):
        reaction_id = identifier.removeprefix("quantity:rate:")
        role = f"conversion/{reaction_id}/rate"
    elif identifier.startswith("quantity:ratio:reaction:"):
        reaction_id = identifier.removeprefix("quantity:ratio:")
        role = f"conversion/{reaction_id}/product_ratio"
    else:
        raise ValueError(f"test quantity lacks a signed role: {identifier}")
    return QUANTITY_ISSUER.sign(
        quantity_id=identifier,
        quantity_role=role,
        value=value,
        unit=unit,
        provenance_id=f"provenance:{identifier}",
    )


def _target(
    target_id: str,
    component_id: str,
    kind: LocalTargetKind,
) -> LocalNeurochemicalTarget:
    evidence = _evidence(
        f"evidence:{target_id}",
        f"{target_id} receives the full mounted state of {component_id}",
    )
    return LocalNeurochemicalTarget(
        target_id=target_id,
        component_id=component_id,
        kind=kind,
        receptor_activation_availability=MechanismAvailability.UNAVAILABLE,
        derivation_receipt_payload=evidence,
        derivation_receipt_sha256=hashlib.sha256(evidence).hexdigest(),
    )


def _manifest(
    *,
    initial_enabled_transport_ids: tuple[str, ...] = (
        "diffusion:a:pre-post",
        "drift:a:circulatory",
        "drift:a:csf-clearance",
    ),
    max_state_bytes: int = 2_000_000,
    max_active_block_components: int = 16,
    max_derivation_receipt_bytes: int = 4096,
    max_causal_receipt_bytes: int = 4096,
    max_event_bytes: int = 65_536,
    max_lanes: int = 32,
    temporal_permission_limit: int | None = None,
    include_conversion: bool = True,
    component_initial_overrides: dict[str, Fraction] | None = None,
    all_zero: bool = False,
):
    time = _quantity(
        "quantity:structural-time",
        Fraction(1),
        "time",
        positive=True,
        equation="one structural time unit = one SI second",
    )
    backend_evidence = _evidence(
        "evidence:backend",
        "python-flint 0.9.0 / FLINT 3.6.0, one thread, 128 bits",
    )
    backend = NeurochemicalBackendMount(
        authority_id="backend:pinned-arb-128",
        working_precision_bits=128,
        derivation_receipt_payload=backend_evidence,
        derivation_receipt_sha256=hashlib.sha256(
            backend_evidence
        ).hexdigest(),
    )
    species = (
        NeurochemicalSpeciesMount(
            species_id="species:a",
            quantity_unit="molecule-a",
            conserved_mass_per_quantity=_quantity(
                "quantity:mass:a",
                Fraction(1),
                "mass-per-molecule-a",
                positive=True,
                equation="mounted conserved mass(a)=1",
            ),
        ),
        NeurochemicalSpeciesMount(
            species_id="species:b",
            quantity_unit="molecule-b",
            conserved_mass_per_quantity=_quantity(
                "quantity:mass:b",
                Fraction(2),
                "mass-per-molecule-b",
                positive=True,
                equation="mounted conserved mass(b)=2",
            ),
        ),
    )
    node_facts = (
        ("node:circulation", NodeKind.PHYSICAL),
        ("node:csf-sink", NodeKind.EXTERNAL_SINK_RESERVOIR),
        ("node:post", NodeKind.PHYSICAL),
        ("node:pre", NodeKind.PHYSICAL),
        ("node:source", NodeKind.EXTERNAL_SOURCE_RESERVOIR),
    )
    nodes = tuple(
        NeurochemicalNodeMount(
            node_id=node_id,
            kind=kind,
            volume=_quantity(
                f"quantity:volume:{node_id}",
                Fraction(index + 1),
                "volume",
                positive=True,
                equation=f"mounted compartment volume={index + 1}",
            ),
        )
        for index, (node_id, kind) in enumerate(node_facts)
    )
    component_facts = (
        ("component:a:circulation", "species:a", "node:circulation", 0),
        ("component:a:csf-sink", "species:a", "node:csf-sink", 0),
        ("component:a:post", "species:a", "node:post", 1),
        ("component:a:pre", "species:a", "node:pre", 4),
        ("component:a:source", "species:a", "node:source", 10),
        ("component:b:post", "species:b", "node:post", 0),
        ("component:b:pre", "species:b", "node:pre", 0),
        ("component:b:source", "species:b", "node:source", 6),
    )
    overrides = component_initial_overrides or {}
    components = tuple(
        NeurochemicalCompartmentMount(
            component_id=component_id,
            species_id=species_id,
            node_id=node_id,
            initial_quantity=_quantity(
                f"quantity:initial:{component_id}",
                (
                    Fraction(0)
                    if all_zero
                    else overrides.get(component_id, Fraction(value))
                ),
                "molecule-a" if species_id == "species:a" else "molecule-b",
                positive=False,
                equation=(
                    "mounted exact initial quantity="
                    f"{0 if all_zero else overrides.get(component_id, value)}"
                ),
            ),
        )
        for component_id, species_id, node_id, value in component_facts
    )
    impulse_routes = (
        NeurochemicalImpulseRoute(
            lane_id="lane:a:retrograde",
            kind=DirectedLaneKind.RETROGRADE,
            species_id="species:a",
            source_component_id="component:a:post",
            target_component_id="component:a:pre",
        ),
        NeurochemicalImpulseRoute(
            lane_id="lane:a:source-release",
            kind=DirectedLaneKind.SYNAPTIC,
            species_id="species:a",
            source_component_id="component:a:source",
            target_component_id="component:a:circulation",
        ),
        NeurochemicalImpulseRoute(
            lane_id="lane:a:synaptic",
            kind=DirectedLaneKind.SYNAPTIC,
            species_id="species:a",
            source_component_id="component:a:pre",
            target_component_id="component:a:post",
        ),
        NeurochemicalImpulseRoute(
            lane_id="lane:b:synaptic",
            kind=DirectedLaneKind.SYNAPTIC,
            species_id="species:b",
            source_component_id="component:b:source",
            target_component_id="component:b:pre",
        ),
    )

    def signed_transport_quantity(
        quantity_id: str,
        role: str,
        value: Fraction,
        unit: str,
    ) -> SignedPhysicalQuantity:
        return QUANTITY_ISSUER.sign(
            quantity_id=quantity_id,
            quantity_role=role,
            value=value,
            unit=unit,
            provenance_id=f"provenance:{quantity_id}",
        )

    drift_lanes = (
        NeurochemicalDriftLane(
            lane_id="drift:a:circulatory",
            kind=DirectedLaneKind.CIRCULATORY,
            species_id="species:a",
            source_component_id="component:a:circulation",
            target_component_id="component:a:post",
            velocity=signed_transport_quantity(
                "quantity:velocity:drift:a:circulatory",
                "drift/drift:a:circulatory/velocity",
                Fraction(1, 7),
                "length-per-time",
            ),
            interface_area=signed_transport_quantity(
                "quantity:area:drift:a:circulatory",
                "drift/drift:a:circulatory/interface_area",
                Fraction(2),
                "area",
            ),
        ),
        NeurochemicalDriftLane(
            lane_id="drift:a:csf-clearance",
            kind=DirectedLaneKind.CSF_CLEARANCE,
            species_id="species:a",
            source_component_id="component:a:post",
            target_component_id="component:a:csf-sink",
            velocity=signed_transport_quantity(
                "quantity:velocity:drift:a:csf-clearance",
                "drift/drift:a:csf-clearance/velocity",
                Fraction(1, 5),
                "length-per-time",
            ),
            interface_area=signed_transport_quantity(
                "quantity:area:drift:a:csf-clearance",
                "drift/drift:a:csf-clearance/interface_area",
                Fraction(1),
                "area",
            ),
        ),
    )
    diffusion_interfaces = (
        ExtracellularDiffusionInterface(
            interface_id="diffusion:a:pre-post",
            species_id="species:a",
            endpoint_a_component_id="component:a:pre",
            endpoint_b_component_id="component:a:post",
            diffusion_coefficient=signed_transport_quantity(
                "quantity:diffusion:diffusion:a:pre-post",
                (
                    "diffusion/diffusion:a:pre-post/"
                    "diffusion_coefficient"
                ),
                Fraction(1, 2),
                "area-per-time",
            ),
            interface_area=signed_transport_quantity(
                "quantity:area:diffusion:a:pre-post",
                "diffusion/diffusion:a:pre-post/interface_area",
                Fraction(3),
                "area",
            ),
            path_length=signed_transport_quantity(
                "quantity:length:diffusion:a:pre-post",
                "diffusion/diffusion:a:pre-post/path_length",
                Fraction(2),
                "length",
            ),
        ),
    )
    conversions = (
        FirstOrderNeurochemicalConversion(
            reaction_id="reaction:a-to-b:post",
            node_id="node:post",
            reactant_component_id="component:a:post",
            product_component_id="component:b:post",
            rate=_quantity(
                "quantity:rate:reaction:a-to-b:post",
                Fraction(1, 4),
                "per-time",
                positive=True,
                equation="mounted first-order conversion rate=1/4",
            ),
            product_quantity_per_reactant=_quantity(
                "quantity:ratio:reaction:a-to-b:post",
                Fraction(1, 2),
                "molecule-b-per-molecule-a",
                positive=True,
                equation="1 molecule-a mass / 2 molecule-b mass = 1/2",
            ),
        ),
    )
    nonlinear_evidence = _evidence(
        "evidence:nonlinear-unavailable",
        "no exact linear generator represents saturating uptake",
    )
    receptor_evidence = _evidence(
        "evidence:receptor-unavailable",
        "chemical exposure is not a mounted R-A-D receptor population",
    )
    nonlinear = (
        UnavailableNonlinearMechanism(
            mechanism_id="mechanism:receptor-binding-activation",
            kind=NonlinearMechanismKind.RECEPTOR_BINDING_ACTIVATION,
            availability=MechanismAvailability.UNAVAILABLE,
            reason="requires mounted conserved R-A-D receptor kinetics",
            derivation_receipt_payload=receptor_evidence,
            derivation_receipt_sha256=hashlib.sha256(
                receptor_evidence
            ).hexdigest(),
        ),
        UnavailableNonlinearMechanism(
            mechanism_id="mechanism:saturating-uptake",
            kind=NonlinearMechanismKind.SATURATING_UPTAKE,
            availability=MechanismAvailability.UNAVAILABLE,
            reason="requires a separately ratified nonlinear solver",
            derivation_receipt_payload=nonlinear_evidence,
            derivation_receipt_sha256=hashlib.sha256(
                nonlinear_evidence
            ).hexdigest(),
        ),
    )
    return create_neurochemical_flow_manifest(
        authority_key=AUTHORITY_KEY,
        manifest_id="manifest:test-neurochemical-flow",
        structural_time_unit=time,
        backend=backend,
        physical_quantity_issuers=(QUANTITY_ISSUER.verifier_mount,),
        species=species,
        nodes=nodes,
        components=components,
        impulse_routes=impulse_routes,
        drift_lanes=drift_lanes,
        diffusion_interfaces=diffusion_interfaces,
        conversions=conversions if include_conversion else (),
        upstream_issuers=(
            ACTION_ISSUER.verifier_mount,
            CLOCK_ISSUER.verifier_mount,
        ),
        physical_route_permissions=(
            PhysicalReceiptRoutePermission(
                route_id="route:action:source-release",
                issuer_id="issuer:action",
                source_kind=CausalSourceKind.ACTION,
                source_component_id="component:a:source",
                lane_id="lane:a:source-release",
                destination_component_id="component:a:circulation",
                amount_unit="molecule-a",
            ),
        ),
        temporal_route_permissions=tuple(sorted(
            (
                TemporalReceiptRoutePermission(
                route_id=(
                    f"route:clock:{kind.value}:{lane_id}:"
                    f"{'enable' if lane_enabled else 'disable'}"
                ),
                issuer_id="issuer:clock",
                driver_kind=kind,
                lane_id=lane_id,
                lane_enabled=lane_enabled,
                physical_parameter_path=(
                    f"lane_state/{lane_id}/enabled"
                ),
                )
                for kind, lane_id in (
                    (
                        TemporalDriverKind.CIRCADIAN,
                        "drift:a:circulatory",
                    ),
                    (
                        TemporalDriverKind.INTRINSIC,
                        "diffusion:a:pre-post",
                    ),
                    (
                        TemporalDriverKind.PHASIC,
                        "drift:a:circulatory",
                    ),
                    (
                        TemporalDriverKind.SLEEP_COUPLED,
                        "drift:a:csf-clearance",
                    ),
                )
                for lane_enabled in (False, True)
            ),
            key=lambda value: value.route_id,
        ))[:temporal_permission_limit],
        local_targets=(
            _target(
                "target:post-conductance",
                "component:a:post",
                LocalTargetKind.MEMBRANE_CONDUCTANCE,
            ),
            _target(
                "target:post-metabolism",
                "component:b:post",
                LocalTargetKind.METABOLIC_AVAILABILITY,
            ),
        ),
        unavailable_nonlinear_mechanisms=nonlinear,
        initial_enabled_transport_ids=initial_enabled_transport_ids,
        capacity=NeurochemicalCapacity(
            max_components=32,
            max_lanes=max_lanes,
            max_reactions=8,
            max_targets=8,
            max_events_per_boundary=32,
            max_active_block_components=max_active_block_components,
            max_derivation_receipt_bytes=max_derivation_receipt_bytes,
            max_causal_receipt_bytes=max_causal_receipt_bytes,
            max_event_bytes=max_event_bytes,
            max_state_bytes=max_state_bytes,
        ),
    )


def _bounds(value) -> tuple[Fraction, Fraction]:
    if isinstance(value, Fraction):
        return value, value
    assert isinstance(value, CertifiedBall)
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


def _event_with_transfer(
    authority: NeurochemicalFlowFieldAuthority,
    *,
    event_id: str,
    start: Fraction,
    end: Fraction,
):
    transfer = ACTION_ISSUER.sign_physical(
        chemistry_sequence=int(start) + 1,
        event_id=event_id,
        source_time_start=start,
        source_time_end=end,
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    return authority.create_causal_event(
        upstream_receipts=(transfer,),
    )


def _driver_event(
    authority: NeurochemicalFlowFieldAuthority,
    *,
    kind: TemporalDriverKind,
    lane_id: str,
    event_id: str,
    start: Fraction = Fraction(0),
    end: Fraction = Fraction(1),
):
    driver = CLOCK_ISSUER.sign_temporal(
        chemistry_sequence=int(start) + 1,
        event_id=event_id,
        source_time_start=start,
        source_time_end=end,
        driver_kind=kind,
        lane_id=lane_id,
        lane_enabled=True,
        physical_parameter_path=f"lane_state/{lane_id}/enabled",
    )
    return authority.create_causal_event(upstream_receipts=(driver,))


def _additional_drift_lane(lane_id: str) -> NeurochemicalDriftLane:
    return NeurochemicalDriftLane(
        lane_id=lane_id,
        kind=DirectedLaneKind.CIRCULATORY,
        species_id="species:a",
        source_component_id="component:a:circulation",
        target_component_id="component:a:post",
        velocity=QUANTITY_ISSUER.sign(
            quantity_id=f"quantity:velocity:{lane_id}",
            quantity_role=f"drift/{lane_id}/velocity",
            value=Fraction(1, 101),
            unit="length-per-time",
            provenance_id=f"provenance:quantity:velocity:{lane_id}",
        ),
        interface_area=QUANTITY_ISSUER.sign(
            quantity_id=f"quantity:area:{lane_id}",
            quantity_role=f"drift/{lane_id}/interface_area",
            value=Fraction(1),
            unit="area",
            provenance_id=f"provenance:quantity:area:{lane_id}",
        ),
    )


def test_analytic_sparse_field_moves_nonflat_and_conserves_each_structure():
    manifest = _manifest()
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=manifest,
    )
    initial_mass = authority.state.exact_conserved_mass
    isolated_before = dict(authority.state.component_values)[
        "component:b:source"
    ]

    result = authority.evolve(
        _event_with_transfer(
            authority,
            event_id="event:excitation-release",
            start=Fraction(0),
            end=Fraction(1),
        )
    )

    assert result.status is EvolutionStatus.EVOLVED
    assert result.transition is not None
    values = dict(result.state.component_values)
    pre_lower, pre_upper = _bounds(values["component:a:pre"])
    post_lower, post_upper = _bounds(values["component:a:post"])
    sink_lower, sink_upper = _bounds(values["component:a:csf-sink"])
    product_lower, product_upper = _bounds(values["component:b:post"])
    assert pre_upper < 4
    assert post_lower > 1
    assert sink_lower > 0
    assert product_lower > 0
    assert (pre_lower, pre_upper) != (post_lower, post_upper)
    assert values["component:b:source"] is isolated_before
    assert "component:b:source" in result.transition.untouched_component_ids
    assert result.state.exact_conserved_mass == initial_mass

    weights = {
        component.component_id: next(
            species.conserved_mass_per_quantity.value
            for species in manifest.species
            if species.species_id == component.species_id
        )
        for component in manifest.components
    }
    for column in (value.component_id for value in manifest.components):
        assert sum(
            (
                weights[entry.row_component_id]
                * entry.value_per_time_unit
                for entry in result.transition.generator_entries
                if entry.column_component_id == column
            ),
            Fraction(0),
        ) == 0
    mass_lower = sum(
        _bounds(value)[0] * weights[component_id]
        for component_id, value in result.state.component_values
    )
    mass_upper = sum(
        _bounds(value)[1] * weights[component_id]
        for component_id, value in result.state.component_values
    )
    assert mass_lower <= initial_mass <= mass_upper
    assert {
        lane.kind
        for lane in (*manifest.impulse_routes, *manifest.drift_lanes)
    } == {
        DirectedLaneKind.CIRCULATORY,
        DirectedLaneKind.CSF_CLEARANCE,
        DirectedLaneKind.RETROGRADE,
        DirectedLaneKind.SYNAPTIC,
    }
    assert len(manifest.diffusion_interfaces) == 1
    assert {
        component.species_id for component in manifest.components
    } == {"species:a", "species:b"}
    assert len(result.transition.local_target_exposures) == 2
    assert all(
        exposure.receptor_activation_availability
        is MechanismAvailability.UNAVAILABLE
        for exposure in result.transition.local_target_exposures
    )
    assert all(
        target.receptor_activation_availability
        is MechanismAvailability.UNAVAILABLE
        for target in manifest.local_targets
    )
    assert any(
        mechanism.kind
        is NonlinearMechanismKind.RECEPTOR_BINDING_ACTIVATION
        and mechanism.availability is MechanismAvailability.UNAVAILABLE
        for mechanism in manifest.unavailable_nonlinear_mechanisms
    )
    assert not any(
        token in result.transition.payload()
        for token in ("mood", "relevance", "salience", "global_score")
    )


def test_total_transport_lane_capacity_is_global_and_temporally_enforced():
    with pytest.raises(
        ValueError,
        match="total mounted transport identities",
    ):
        _manifest(max_lanes=4)

    boundary_manifest = _manifest(
        max_lanes=7,
        temporal_permission_limit=7,
    )
    assert (
        len(boundary_manifest.impulse_routes)
        + len(boundary_manifest.drift_lanes)
        + len(boundary_manifest.diffusion_interfaces)
        == boundary_manifest.capacity.max_lanes
    )
    with pytest.raises(
        ValueError,
        match="total mounted transport identities",
    ):
        replace(
            boundary_manifest,
            capacity=replace(boundary_manifest.capacity, max_lanes=6),
        ).verify(AUTHORITY_KEY)

    base = _manifest()
    extra_lanes = (
        _additional_drift_lane("drift:a:extra-1"),
        _additional_drift_lane("drift:a:extra-2"),
    )
    drift_lanes = tuple(sorted(
        (*base.drift_lanes, *extra_lanes),
        key=lambda value: value.lane_id,
    ))
    extra_permission = TemporalReceiptRoutePermission(
        route_id="route:clock:phasic:drift:a:extra-2:enable",
        issuer_id="issuer:clock",
        driver_kind=TemporalDriverKind.PHASIC,
        lane_id="drift:a:extra-2",
        lane_enabled=True,
        physical_parameter_path="lane_state/drift:a:extra-2/enabled",
    )
    temporal_permissions = tuple(sorted(
        (*base.temporal_route_permissions, extra_permission),
        key=lambda value: value.route_id,
    ))
    enabled_at_runtime_bound = (
        "diffusion:a:pre-post",
        "drift:a:circulatory",
        "drift:a:csf-clearance",
        "drift:a:extra-1",
    )
    manifest = create_neurochemical_flow_manifest(
        authority_key=AUTHORITY_KEY,
        manifest_id="manifest:temporal-lane-capacity-regression",
        structural_time_unit=base.structural_time_unit,
        backend=base.backend,
        physical_quantity_issuers=base.physical_quantity_issuers,
        species=base.species,
        nodes=base.nodes,
        components=base.components,
        impulse_routes=base.impulse_routes,
        drift_lanes=drift_lanes,
        diffusion_interfaces=base.diffusion_interfaces,
        conversions=base.conversions,
        upstream_issuers=base.upstream_issuers,
        physical_route_permissions=base.physical_route_permissions,
        temporal_route_permissions=temporal_permissions,
        local_targets=base.local_targets,
        unavailable_nonlinear_mechanisms=(
            base.unavailable_nonlinear_mechanisms
        ),
        initial_enabled_transport_ids=enabled_at_runtime_bound,
        capacity=replace(base.capacity, max_lanes=9),
    )
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=manifest,
    )
    fifth_lane_receipt = CLOCK_ISSUER.sign_temporal(
        chemistry_sequence=1,
        event_id="event:reject-fifth-enabled-lane",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        driver_kind=TemporalDriverKind.PHASIC,
        lane_id="drift:a:extra-2",
        lane_enabled=True,
        physical_parameter_path="lane_state/drift:a:extra-2/enabled",
    )
    event = authority.create_causal_event(
        upstream_receipts=(fifth_lane_receipt,),
    )

    # Fault injection isolates the runtime/state barriers. Public manifest
    # admission now makes this over-enable condition unreachable.
    authority._manifest = replace(
        authority.manifest,
        capacity=replace(authority.manifest.capacity, max_lanes=4),
    )
    authority._verify_state(authority.state)
    with pytest.raises(ValueError, match="left its mounted topology"):
        authority._verify_state(
            replace(
                authority.state,
                enabled_transport_ids=(
                    *authority.state.enabled_transport_ids,
                    "drift:a:extra-2",
                ),
            ),
        )
    before = authority.snapshot_encoded()
    result = authority.evolve(event)

    assert result.status is EvolutionStatus.UNRESOLVED
    assert "enabled transport identities" in result.reason
    assert len(result.state.enabled_transport_ids) == 4
    assert authority.snapshot_encoded() == before


def test_reciprocal_diffusion_and_drift_coefficients_come_from_geometry():
    diffusion_authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(
            initial_enabled_transport_ids=(),
            include_conversion=False,
        ),
    )
    diffusion = diffusion_authority.evolve(
        _driver_event(
            diffusion_authority,
            kind=TemporalDriverKind.INTRINSIC,
            lane_id="diffusion:a:pre-post",
            event_id="event:derive-reciprocal-diffusion",
        )
    )
    assert diffusion.status is EvolutionStatus.EVOLVED
    entries = {
        (entry.row_component_id, entry.column_component_id): (
            entry.value_per_time_unit
        )
        for entry in diffusion.transition.generator_entries
    }
    assert entries[
        ("component:a:post", "component:a:pre")
    ] == Fraction(3, 16)
    assert entries[
        ("component:a:pre", "component:a:post")
    ] == Fraction(1, 4)
    assert entries[
        ("component:a:pre", "component:a:pre")
    ] == -Fraction(3, 16)
    assert entries[
        ("component:a:post", "component:a:post")
    ] == -Fraction(1, 4)

    equal_concentration = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(
            initial_enabled_transport_ids=(),
            include_conversion=False,
            component_initial_overrides={
                "component:a:pre": Fraction(4),
                "component:a:post": Fraction(3),
                "component:a:source": Fraction(0),
            },
        ),
    )
    equal_result = equal_concentration.evolve(
        _driver_event(
            equal_concentration,
            kind=TemporalDriverKind.INTRINSIC,
            lane_id="diffusion:a:pre-post",
            event_id="event:equal-concentration",
        )
    )
    equal_entries = equal_result.transition.generator_entries
    initial = {
        component.component_id: component.initial_quantity.value
        for component in equal_concentration.manifest.components
    }
    for row in ("component:a:pre", "component:a:post"):
        assert sum(
            (
                entry.value_per_time_unit
                * initial[entry.column_component_id]
                for entry in equal_entries
                if entry.row_component_id == row
            ),
            Fraction(0),
        ) == 0

    drift_authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(
            initial_enabled_transport_ids=(),
            include_conversion=False,
        ),
    )
    drift = drift_authority.evolve(
        _driver_event(
            drift_authority,
            kind=TemporalDriverKind.PHASIC,
            lane_id="drift:a:circulatory",
            event_id="event:derive-drift",
        )
    )
    drift_entries = {
        (entry.row_component_id, entry.column_component_id): (
            entry.value_per_time_unit
        )
        for entry in drift.transition.generator_entries
    }
    assert drift_entries[
        ("component:a:circulation", "component:a:circulation")
    ] == -Fraction(2, 7)
    assert drift_entries[
        ("component:a:post", "component:a:circulation")
    ] == Fraction(2, 7)


def test_one_way_diffusion_and_signed_quantity_substitution_are_rejected():
    with pytest.raises(ValueError, match="impulse-only"):
        NeurochemicalImpulseRoute(
            lane_id="forged:one-way-diffusion",
            kind=DirectedLaneKind.EXTRACELLULAR_DIFFUSION,
            species_id="species:a",
            source_component_id="component:a:pre",
            target_component_id="component:a:post",
        ).verify()

    manifest = _manifest()
    interface = manifest.diffusion_interfaces[0]
    mismatched = replace(
        manifest,
        diffusion_interfaces=(
            replace(
                interface,
                endpoint_b_component_id="component:b:pre",
            ),
        ),
    )
    with pytest.raises(ValueError, match="left physical topology"):
        NeurochemicalFlowFieldAuthority(
            authority_key=AUTHORITY_KEY,
            manifest=mismatched,
        )

    substitutions = (
        replace(
            interface,
            diffusion_coefficient=replace(
                interface.diffusion_coefficient,
                value=Fraction(99),
            ),
        ),
        replace(
            interface,
            diffusion_coefficient=replace(
                interface.diffusion_coefficient,
                unit="forged-unit",
            ),
        ),
        replace(
            interface,
            diffusion_coefficient=replace(
                interface.diffusion_coefficient,
                provenance_id="forged-old-derivation",
            ),
        ),
        replace(
            interface,
            diffusion_coefficient=replace(
                interface.diffusion_coefficient,
                ed25519_signature_hex="0" * 128,
            ),
        ),
    )
    for substituted in substitutions:
        with pytest.raises(ValueError, match="physical quantity Ed25519"):
            NeurochemicalFlowFieldAuthority(
                authority_key=AUTHORITY_KEY,
                manifest=replace(
                    manifest,
                    diffusion_interfaces=(substituted,),
                ),
            )


def test_exact_zero_field_is_canonical_quiescence_and_cold_restorable():
    manifest = _manifest(all_zero=True)
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=manifest,
    )
    assert authority.state.exact_conserved_mass == 0
    assert all(
        value == 0 for _, value in authority.state.component_values
    )
    event = _driver_event(
        authority,
        kind=TemporalDriverKind.INTRINSIC,
        lane_id="diffusion:a:pre-post",
        event_id="event:zero-quiescence",
    )
    result = authority.evolve(event)
    assert result.status is EvolutionStatus.EVOLVED
    assert all(
        isinstance(value, Fraction) and value == 0
        for _, value in result.state.component_values
    )
    assert result.transition.untouched_component_ids == tuple(
        component.component_id for component in manifest.components
    )
    encoded = authority.snapshot_encoded()
    restored = NeurochemicalFlowFieldAuthority.restore_encoded(
        authority_key=AUTHORITY_KEY,
        manifest=manifest,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.state.component_values == authority.state.component_values

    component = manifest.components[0]
    negative_quantity = QUANTITY_ISSUER.sign(
        quantity_id="quantity:negative-initial-test",
        quantity_role=(
            f"component/{component.component_id}/initial_quantity"
        ),
        value=Fraction(-1),
        unit=component.initial_quantity.unit,
        provenance_id="provenance:negative-initial-test",
    )
    negative_manifest = replace(
        manifest,
        components=(
            replace(component, initial_quantity=negative_quantity),
            *manifest.components[1:],
        ),
    )
    with pytest.raises(ValueError, match="exact mounted role"):
        NeurochemicalFlowFieldAuthority(
            authority_key=AUTHORITY_KEY,
            manifest=negative_manifest,
        )


def test_drift_direction_differs_but_driver_kind_has_no_semantic_effect():
    forward_a = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(initial_enabled_transport_ids=()),
    )
    forward_b = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(initial_enabled_transport_ids=()),
    )
    reverse = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(initial_enabled_transport_ids=()),
    )

    phasic = forward_a.evolve(
        _driver_event(
            forward_a,
            kind=TemporalDriverKind.PHASIC,
            lane_id="drift:a:circulatory",
            event_id="event:phasic-forward",
        )
    )
    circadian = forward_b.evolve(
        _driver_event(
            forward_b,
            kind=TemporalDriverKind.CIRCADIAN,
            lane_id="drift:a:circulatory",
            event_id="event:circadian-forward",
        )
    )
    retrograde = reverse.evolve(
        _driver_event(
            reverse,
            kind=TemporalDriverKind.SLEEP_COUPLED,
            lane_id="drift:a:csf-clearance",
            event_id="event:sleep-reverse",
        )
    )

    assert phasic.status is circadian.status is retrograde.status
    assert phasic.status is EvolutionStatus.EVOLVED
    assert all(
        len(event.transition.event.temporal_receipts[0].ed25519_signature_hex)
        == 128
        for event in (phasic, circadian, retrograde)
    )
    assert phasic.state.component_values == circadian.state.component_values
    assert (
        phasic.transition.generator_entries
        == circadian.transition.generator_entries
    )
    assert (
        dict(phasic.state.component_values)["component:a:post"]
        != dict(retrograde.state.component_values)["component:a:post"]
    )
    assert {
        kind.value for kind in TemporalDriverKind
    } == {
        "phasic",
        "tonic",
        "intrinsic",
        "ultradian",
        "circadian",
        "sleep_coupled",
    }


def test_tampering_and_capacity_fail_closed_without_mutation():
    manifest = _manifest()
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=manifest,
    )
    valid = _event_with_transfer(
        authority,
        event_id="event:will-be-tampered",
        start=Fraction(0),
        end=Fraction(1),
    )
    missing_lane_transfer = replace(
        valid.physical_receipts[0],
        lane_id="lane:missing",
    )
    tampered = replace(
        valid,
        physical_receipts=(missing_lane_transfer,),
    )
    before = authority.snapshot_encoded()
    unresolved = authority.evolve(tampered)
    assert unresolved.status is EvolutionStatus.UNRESOLVED
    assert authority.snapshot_encoded() == before
    assert "Ed25519 signature changed" in unresolved.reason

    first_lane = manifest.drift_lanes[0]
    coefficient_tamper = replace(
        manifest,
        drift_lanes=(
            replace(
                first_lane,
                velocity=replace(
                    first_lane.velocity,
                    value=first_lane.velocity.value + Fraction(1, 97),
                ),
            ),
            *manifest.drift_lanes[1:],
        ),
    )
    with pytest.raises(ValueError, match="physical quantity Ed25519"):
        NeurochemicalFlowFieldAuthority(
            authority_key=AUTHORITY_KEY,
            manifest=coefficient_tamper,
        )

    provenance_reuse = replace(
        manifest,
        drift_lanes=(
            replace(
                first_lane,
                velocity=replace(
                    first_lane.velocity,
                    unit="forged-old-derivation-unit",
                ),
            ),
            *manifest.drift_lanes[1:],
        ),
    )
    with pytest.raises(ValueError, match="physical quantity Ed25519"):
        NeurochemicalFlowFieldAuthority(
            authority_key=AUTHORITY_KEY,
            manifest=provenance_reuse,
        )

    initial_size = len(authority.snapshot_encoded())
    capacity_manifest = _manifest(max_state_bytes=initial_size + 1024)
    bounded = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=capacity_manifest,
    )
    bounded_before = bounded.snapshot_encoded()
    capacity_result = bounded.evolve(
        _event_with_transfer(
            bounded,
            event_id="event:capacity-boundary",
            start=Fraction(0),
            end=Fraction(1),
        )
    )
    assert capacity_result.status is EvolutionStatus.UNRESOLVED
    assert "capacity is full" in capacity_result.reason
    assert bounded.snapshot_encoded() == bounded_before


def test_authenticated_cold_restore_is_deterministic_and_bounded():
    manifest = _manifest()
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=manifest,
    )
    first = authority.evolve(
        _event_with_transfer(
            authority,
            event_id="event:first",
            start=Fraction(0),
            end=Fraction(1),
        )
    )
    assert first.status is EvolutionStatus.EVOLVED
    encoded = authority.snapshot_encoded()
    restored = NeurochemicalFlowFieldAuthority.restore_encoded(
        authority_key=AUTHORITY_KEY,
        manifest=manifest,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded

    event_original = _event_with_transfer(
        authority,
        event_id="event:second",
        start=Fraction(1),
        end=Fraction(2),
    )
    event_restored = _event_with_transfer(
        restored,
        event_id="event:second",
        start=Fraction(1),
        end=Fraction(2),
    )
    original_second = authority.evolve(event_original)
    restored_second = restored.evolve(event_restored)
    assert original_second.status is restored_second.status
    assert original_second.state == restored_second.state
    assert original_second.transition == restored_second.transition
    assert authority.snapshot_encoded() == restored.snapshot_encoded()
    assert len(authority.snapshot_encoded()) <= manifest.capacity.max_state_bytes

    envelope = json.loads(encoded)
    assert set(envelope["payload"]) == {
        "last_transition",
        "manifest_receipt_sha256",
        "schema",
        "state",
    }
    assert "history" not in json.dumps(envelope)
    corrupted = bytearray(encoded)
    corrupted[-3] = ord("0") if corrupted[-3] != ord("0") else ord("1")
    with pytest.raises(ValueError):
        NeurochemicalFlowFieldAuthority.restore_encoded(
            authority_key=AUTHORITY_KEY,
            manifest=manifest,
            encoded=bytes(corrupted),
        )


def test_source_exhaustion_driver_tamper_and_quiescence_fail_honestly():
    manifest = _manifest(
        initial_enabled_transport_ids=(),
        include_conversion=False,
    )
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=manifest,
    )
    driver = CLOCK_ISSUER.sign_temporal(
        chemistry_sequence=1,
        event_id="event:quiescent",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        driver_kind=TemporalDriverKind.INTRINSIC,
        lane_id="diffusion:a:pre-post",
        lane_enabled=False,
        physical_parameter_path=(
            "lane_state/diffusion:a:pre-post/enabled"
        ),
    )
    quiescent_event = authority.create_causal_event(
        upstream_receipts=(driver,),
    )
    tampered_driver = replace(
        driver,
        driver_kind=TemporalDriverKind.TONIC,
    )
    tampered_event = replace(
        quiescent_event,
        temporal_receipts=(tampered_driver,),
    )
    before = authority.snapshot_encoded()
    tampered_result = authority.evolve(tampered_event)
    assert tampered_result.status is EvolutionStatus.UNRESOLVED
    assert "Ed25519 signature changed" in tampered_result.reason
    assert authority.snapshot_encoded() == before

    prior_values = authority.state.component_values
    quiescent = authority.evolve(quiescent_event)
    assert quiescent.status is EvolutionStatus.EVOLVED
    assert quiescent.state.component_values == prior_values
    assert quiescent.transition.generator_entries == ()
    assert quiescent.transition.exact_active_blocks == ()
    assert quiescent.transition.untouched_component_ids == tuple(
        component.component_id for component in manifest.components
    )
    assert quiescent.state.exact_conserved_mass == (
        authority.state.exact_conserved_mass
    )
    assert set(driver.payload()) == {
        "chemistry_sequence",
        "driver_kind",
        "event_id",
        "issuer_id",
        "lane_enabled",
        "lane_id",
        "physical_parameter_path",
        "schema",
        "source_time_end",
        "source_time_start",
    }
    assert not {
        "meaning",
        "action",
        "word",
        "concept",
        "selection",
        "quantity",
    }.intersection(driver.payload())

    exhaustion = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(
            initial_enabled_transport_ids=(),
            include_conversion=False,
        ),
    )
    excessive_transfer = ACTION_ISSUER.sign_physical(
        chemistry_sequence=1,
        event_id="event:exhaust-source",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(11),
        amount_unit="molecule-a",
    )
    excessive_event = exhaustion.create_causal_event(
        upstream_receipts=(excessive_transfer,),
    )
    exhaustion_before = exhaustion.snapshot_encoded()
    exhausted = exhaustion.evolve(excessive_event)
    assert exhausted.status is EvolutionStatus.UNRESOLVED
    assert "not certified by source quantity" in exhausted.reason
    assert exhaustion.snapshot_encoded() == exhaustion_before

    impulse_only = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(
            initial_enabled_transport_ids=(),
            include_conversion=False,
        ),
    )
    impulse_transfer = ACTION_ISSUER.sign_physical(
        chemistry_sequence=1,
        event_id="event:closed-lane",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    impulse_event = impulse_only.create_causal_event(
        upstream_receipts=(impulse_transfer,),
    )
    impulse_result = impulse_only.evolve(impulse_event)
    assert impulse_result.status is EvolutionStatus.EVOLVED
    assert impulse_result.transition.generator_entries == ()

    boundary_driver = CLOCK_ISSUER.sign_temporal(
        chemistry_sequence=1,
        event_id="event:closed-lane",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        driver_kind=TemporalDriverKind.PHASIC,
        lane_id="drift:a:circulatory",
        lane_enabled=True,
        physical_parameter_path="lane_state/drift:a:circulatory/enabled",
    )
    with pytest.raises(ValueError, match="separate causal boundaries"):
        impulse_only.create_causal_event(
            upstream_receipts=(impulse_transfer, boundary_driver),
        )


def test_allocation_capacities_reject_before_state_mutation(monkeypatch):
    block_manifest = _manifest(max_active_block_components=3)
    block_authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=block_manifest,
    )
    block_before = block_authority.snapshot_encoded()
    blocked = block_authority.evolve(
        _event_with_transfer(
            block_authority,
            event_id="event:block-capacity",
            start=Fraction(0),
            end=Fraction(1),
        )
    )
    assert blocked.status is EvolutionStatus.UNRESOLVED
    assert "active neurochemical block" in blocked.reason
    assert block_authority.snapshot_encoded() == block_before

    receipt_manifest = _manifest(max_causal_receipt_bytes=64)
    receipt_authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=receipt_manifest,
    )
    receipt_before = receipt_authority.snapshot_encoded()
    assert not hasattr(receipt_authority, "exact_transfer")
    assert not hasattr(receipt_authority, "authorize_temporal_driver")
    bounded_receipt = ACTION_ISSUER.sign_physical(
        chemistry_sequence=1,
        event_id="event:receipt-capacity",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    with pytest.raises(ValueError, match="receipt exceeds authenticated"):
        receipt_authority.create_causal_event(
            upstream_receipts=(bounded_receipt,),
        )
    assert receipt_authority.snapshot_encoded() == receipt_before

    with pytest.raises(
        ValueError,
        match="manifest derivation exceeds authenticated byte capacity",
    ):
        _manifest(max_derivation_receipt_bytes=64)

    small_event_manifest = _manifest(
        max_event_bytes=5000,
        max_causal_receipt_bytes=4096,
    )
    small_event_authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=small_event_manifest,
    )
    transfer = ACTION_ISSUER.sign_physical(
        chemistry_sequence=1,
        event_id="event:too-small-capacity",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    event_before = small_event_authority.snapshot_encoded()
    with pytest.raises(ValueError, match="event exceeds authenticated"):
        small_event_authority.create_causal_event(
            upstream_receipts=(transfer,),
        )
    assert small_event_authority.snapshot_encoded() == event_before

    with pytest.raises(ValueError, match="cold state exceeds authenticated"):
        NeurochemicalFlowFieldAuthority.restore_encoded(
            authority_key=AUTHORITY_KEY,
            manifest=block_manifest,
            encoded=b"x" * (block_manifest.capacity.max_state_bytes + 1),
        )

    def forbidden_manifest_payload(_self):
        raise AssertionError("oversize manifest reached payload allocation")

    monkeypatch.setattr(
        NeurochemicalFlowManifest,
        "payload",
        forbidden_manifest_payload,
    )
    with pytest.raises(ValueError, match="pre-allocation byte capacity"):
        create_neurochemical_flow_manifest(
            authority_key=AUTHORITY_KEY,
            manifest_id="manifest:oversize-preallocation",
            structural_time_unit=block_manifest.structural_time_unit,
            backend=block_manifest.backend,
            physical_quantity_issuers=(
                block_manifest.physical_quantity_issuers
            ),
            species=block_manifest.species,
            nodes=block_manifest.nodes,
            components=block_manifest.components,
            impulse_routes=(block_manifest.impulse_routes[0],) * 20_000,
            drift_lanes=block_manifest.drift_lanes,
            diffusion_interfaces=block_manifest.diffusion_interfaces,
            conversions=block_manifest.conversions,
            upstream_issuers=block_manifest.upstream_issuers,
            physical_route_permissions=(
                block_manifest.physical_route_permissions
            ),
            temporal_route_permissions=(
                block_manifest.temporal_route_permissions
            ),
            local_targets=block_manifest.local_targets,
            unavailable_nonlinear_mechanisms=(
                block_manifest.unavailable_nonlinear_mechanisms
            ),
            initial_enabled_transport_ids=(
                block_manifest.initial_enabled_transport_ids
            ),
            capacity=replace(
                block_manifest.capacity,
                max_lanes=20_003,
            ),
        )


def test_upstream_ed25519_boundary_rejects_every_causal_substitution():
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(),
    )
    before = authority.snapshot_encoded()
    valid = ACTION_ISSUER.sign_physical(
        chemistry_sequence=1,
        event_id="event:substitution",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    verify_upstream_receipt(valid, ACTION_ISSUER.verifier_mount)
    substitutions = (
        replace(valid, issuer_id="issuer:foreign"),
        replace(valid, source_kind=CausalSourceKind.BODY),
        replace(valid, source_component_id="component:a:pre"),
        replace(valid, lane_id="lane:a:synaptic"),
        replace(valid, destination_component_id="component:a:post"),
        replace(valid, amount=Fraction(2)),
        replace(valid, amount_unit="forged-unit"),
        replace(valid, source_time_start=Fraction(-1)),
        replace(valid, source_time_end=Fraction(2)),
        replace(valid, chemistry_sequence=2),
        replace(valid, event_id="event:relabeled"),
    )
    for substituted in substitutions:
        with pytest.raises(ValueError):
            authority.create_causal_event(
                upstream_receipts=(substituted,),
            )
        assert authority.snapshot_encoded() == before

    foreign_key = NeurochemicalUpstreamIssuerAuthority.from_private_key_bytes(
        issuer_id="issuer:action",
        authority_kind=UpstreamAuthorityKind.ACTION,
        private_key_bytes=bytes.fromhex("33" * 32),
    )
    foreign_signature = foreign_key.sign_physical(
        chemistry_sequence=1,
        event_id="event:substitution",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    with pytest.raises(ValueError, match="Ed25519 signature changed"):
        authority.create_causal_event(
            upstream_receipts=(foreign_signature,),
        )
    with pytest.raises(TypeError, match="receipt is not typed"):
        authority.create_causal_event(
            upstream_receipts=(b"caller assertion",),
        )
    assert authority.snapshot_encoded() == before


def test_direct_event_member_type_tampering_is_typed_unresolved():
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(),
    )
    valid_receipt = ACTION_ISSUER.sign_physical(
        chemistry_sequence=1,
        event_id="event:direct-type-tamper",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    valid_event = authority.create_causal_event(
        upstream_receipts=(valid_receipt,),
    )
    before = authority.snapshot_encoded()
    malformed_events = (
        replace(valid_event, physical_receipts=(object(),)),
        replace(
            valid_event,
            physical_receipts=(),
            temporal_receipts=(valid_receipt,),
        ),
        NeurochemicalCausalEvent(
            event_id=valid_event.event_id,
            source_time_start=valid_event.source_time_start,
            source_time_end=valid_event.source_time_end,
            physical_receipts=[valid_receipt],
            temporal_receipts=(),
            authority_receipt_sha256=valid_event.authority_receipt_sha256,
        ),
    )
    for malformed in malformed_events:
        result = authority.evolve(malformed)
        assert result.status is EvolutionStatus.UNRESOLVED
        assert "receipts are not typed" in result.reason
        assert authority.snapshot_encoded() == before


def test_sequence_replay_gap_duplicate_and_mixed_event_roll_back_atomically():
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(),
    )
    first_receipt = ACTION_ISSUER.sign_physical(
        chemistry_sequence=1,
        event_id="event:first-sequence",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    first_event = authority.create_causal_event(
        upstream_receipts=(first_receipt,),
    )
    first = authority.evolve(first_event)
    assert first.status is EvolutionStatus.EVOLVED
    assert dict(
        first.state.last_accepted_sequence_by_issuer
    )["issuer:action"] == 1
    encoded = authority.snapshot_encoded()
    restored = NeurochemicalFlowFieldAuthority.restore_encoded(
        authority_key=AUTHORITY_KEY,
        manifest=authority.manifest,
        encoded=encoded,
    )
    assert dict(
        restored.state.last_accepted_sequence_by_issuer
    )["issuer:action"] == 1

    replay = restored.evolve(
        restored.create_causal_event(upstream_receipts=(first_receipt,))
    )
    assert replay.status is EvolutionStatus.UNRESOLVED
    assert "replayed, duplicated, or has a gap" in replay.reason
    assert restored.snapshot_encoded() == encoded

    gap_receipt = ACTION_ISSUER.sign_physical(
        chemistry_sequence=3,
        event_id="event:gap",
        source_time_start=Fraction(1),
        source_time_end=Fraction(2),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    gap = restored.evolve(
        restored.create_causal_event(upstream_receipts=(gap_receipt,))
    )
    assert gap.status is EvolutionStatus.UNRESOLVED
    assert restored.snapshot_encoded() == encoded

    with pytest.raises(ValueError, match="members are not canonical"):
        restored.create_causal_event(
            upstream_receipts=(gap_receipt, gap_receipt),
        )
    assert restored.snapshot_encoded() == encoded

    sequence_two = ACTION_ISSUER.sign_physical(
        chemistry_sequence=2,
        event_id="event:mixed-rollback",
        source_time_start=Fraction(1),
        source_time_end=Fraction(2),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    sequence_four = ACTION_ISSUER.sign_physical(
        chemistry_sequence=4,
        event_id="event:mixed-rollback",
        source_time_start=Fraction(1),
        source_time_end=Fraction(2),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    mixed_event = restored.create_causal_event(
        upstream_receipts=(sequence_two, sequence_four),
    )
    mixed = restored.evolve(mixed_event)
    assert mixed.status is EvolutionStatus.UNRESOLVED
    assert restored.snapshot_encoded() == encoded

    correct = restored.evolve(
        restored.create_causal_event(upstream_receipts=(sequence_two,))
    )
    assert correct.status is EvolutionStatus.EVOLVED
    assert dict(
        correct.state.last_accepted_sequence_by_issuer
    )["issuer:action"] == 2


def test_temporal_authority_cannot_cross_an_unmounted_driver_route():
    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(initial_enabled_transport_ids=()),
    )
    before = authority.snapshot_encoded()
    wrong_lane = CLOCK_ISSUER.sign_temporal(
        chemistry_sequence=1,
        event_id="event:wrong-temporal-lane",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        driver_kind=TemporalDriverKind.CIRCADIAN,
        lane_id="lane:a:source-release",
        lane_enabled=True,
        physical_parameter_path="lane_state/lane:a:source-release/enabled",
    )
    with pytest.raises(ValueError, match="not permitted by manifest"):
        authority.create_causal_event(upstream_receipts=(wrong_lane,))

    wrong_driver = CLOCK_ISSUER.sign_temporal(
        chemistry_sequence=1,
        event_id="event:wrong-temporal-driver",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        driver_kind=TemporalDriverKind.TONIC,
        lane_id="drift:a:circulatory",
        lane_enabled=True,
        physical_parameter_path="lane_state/drift:a:circulatory/enabled",
    )
    with pytest.raises(ValueError, match="not permitted by manifest"):
        authority.create_causal_event(upstream_receipts=(wrong_driver,))

    wrong_path = CLOCK_ISSUER.sign_temporal(
        chemistry_sequence=1,
        event_id="event:wrong-temporal-path",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        driver_kind=TemporalDriverKind.CIRCADIAN,
        lane_id="drift:a:circulatory",
        lane_enabled=True,
        physical_parameter_path="meaning/select-word",
    )
    with pytest.raises(ValueError, match="not permitted by manifest"):
        authority.create_causal_event(upstream_receipts=(wrong_path,))
    assert authority.snapshot_encoded() == before


def test_upstream_exact_numbers_are_admitted_before_json_allocation(
    monkeypatch,
):
    with pytest.raises(ValueError, match="sequence must be a positive"):
        ACTION_ISSUER.sign_physical(
            chemistry_sequence=1 << 128,
            event_id="event:oversize-sequence",
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
            source_component_id="component:a:source",
            lane_id="lane:a:source-release",
            destination_component_id="component:a:circulation",
            amount=Fraction(1),
            amount_unit="molecule-a",
        )
    with pytest.raises(ValueError, match="rational bit capacity"):
        ACTION_ISSUER.sign_physical(
            chemistry_sequence=1,
            event_id="event:oversize-rational",
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
            source_component_id="component:a:source",
            lane_id="lane:a:source-release",
            destination_component_id="component:a:circulation",
            amount=Fraction(1 << 4096),
            amount_unit="molecule-a",
        )

    authority = NeurochemicalFlowFieldAuthority(
        authority_key=AUTHORITY_KEY,
        manifest=_manifest(),
    )
    valid = ACTION_ISSUER.sign_physical(
        chemistry_sequence=1,
        event_id="event:direct-oversize",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        source_component_id="component:a:source",
        lane_id="lane:a:source-release",
        destination_component_id="component:a:circulation",
        amount=Fraction(1),
        amount_unit="molecule-a",
    )
    before = authority.snapshot_encoded()

    def forbidden_canonicalization(_value):
        raise AssertionError("oversize receipt reached canonical JSON")

    monkeypatch.setattr(
        neurochemical_upstream_receipt,
        "_canonical",
        forbidden_canonicalization,
    )
    with pytest.raises(ValueError, match="sequence must be a positive"):
        authority.create_causal_event(
            upstream_receipts=(
                replace(valid, chemistry_sequence=1 << 128),
            ),
        )
    with pytest.raises(ValueError, match="rational bit capacity"):
        authority.create_causal_event(
            upstream_receipts=(
                replace(valid, amount=Fraction(1 << 4096)),
            ),
        )
    assert authority.snapshot_encoded() == before


def test_signed_physical_quantity_rejects_oversize_before_json(
    monkeypatch,
):
    manifest = _manifest()
    oversized = replace(
        manifest,
        structural_time_unit=replace(
            manifest.structural_time_unit,
            value=Fraction(1 << 4096),
        ),
    )

    def forbidden_quantity_canonicalization(_value):
        raise AssertionError("oversize physical quantity reached JSON")

    monkeypatch.setattr(
        neurochemical_physical_quantity,
        "_canonical",
        forbidden_quantity_canonicalization,
    )
    with pytest.raises(ValueError, match="rational bit capacity"):
        NeurochemicalFlowFieldAuthority(
            authority_key=AUTHORITY_KEY,
            manifest=oversized,
        )
