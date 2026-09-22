"""Production AE-native conservative neurochemical-flow authority.

The mounted field contains two explicitly artificial carrier species.  They
are not assertions about dopamine, serotonin, human concentrations, mood, or
reward:

* one indivisible excitation carrier is mounted for every sensory receptor
  family and passes between two physical nodal compartments whenever that
  receptor is authentically observed;
* a recovery carrier moves through a closed source/body/sink circulation.

All units are substrate-native defined units.  Every defining quantity is
Ed25519 signed, every sensory pass-off is signed by the excitation authority,
and every causal boundary is also signed by the clock authority.  The field
is finite, exactly mass-conservative, analytically advanced, and cold-exact.

Sensor clocks are not assumed to share one absolute epoch.  Their exact
durations are concatenated into the field's own monotonic structural time.
No duration is scaled, smoothed, thresholded, or discarded.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from fractions import Fraction

from dsf_ai_service.substrate.ae_local_receptor import (
    AELocalReceptorAuthority,
    AELocalReceptorVerifierMount,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.neurochemical_flow import (
    CausalSourceKind,
    DirectedLaneKind,
    ExtracellularDiffusionInterface,
    LocalNeurochemicalTarget,
    LocalTargetKind,
    MechanismAvailability,
    NeurochemicalBackendMount,
    NeurochemicalCapacity,
    NeurochemicalCompartmentMount,
    NeurochemicalDriftLane,
    NeurochemicalFlowManifest,
    NeurochemicalImpulseRoute,
    NeurochemicalNodeMount,
    NeurochemicalSpeciesMount,
    NodeKind,
    NonlinearMechanismKind,
    PhysicalReceiptRoutePermission,
    TemporalDriverKind,
    TemporalReceiptRoutePermission,
    UnavailableNonlinearMechanism,
    create_neurochemical_flow_manifest,
)
from dsf_ai_service.substrate.neurochemical_physical_quantity import (
    PhysicalQuantityIssuerAuthority,
    SignedPhysicalQuantity,
)
from dsf_ai_service.substrate.neurochemical_upstream_receipt import (
    NeurochemicalUpstreamIssuerAuthority,
    UpstreamAuthorityKind,
)
from dsf_ai_service.substrate.physical_internal_body_state import (
    NeurochemicalCompartmentReference,
    PhysicalInternalBodyStateAuthority,
)
from dsf_ai_service.substrate.whole_organism_neurochemical_mount import (
    UnavailableChemicalReaction,
    WholeOrganismNeurochemicalMountOwner,
    WholeOrganismNeurochemicalMountProfile,
)
from dsf_ai_service.substrate.whole_organism_recovery_state import (
    ExactWholeOrganismRecoveryOwner,
)


SENSE_IDS = ("body", "sight", "smell", "sound", "taste", "touch")
EXCITATION_SPECIES_ID = "species:ae-excitation-carrier"
RECOVERY_SPECIES_ID = "species:ae-recovery-carrier"
EXCITATION_UNIT = "ae-excitation-quantum"
RECOVERY_UNIT = "ae-recovery-quantum"
STATUS_SCHEMA = "guala.live_ae_neurochemical_flow.status.v1"

_QUANTITY_ISSUER_ID = "issuer:guala-ae-neurochemical-quantity"
_EXCITATION_ISSUER_ID = "issuer:guala-ae-sensory-excitation"
_CLOCK_ISSUER_ID = "issuer:guala-ae-structural-clock"


def _key(root_key: bytes | str, label: bytes) -> bytes:
    raw = root_key.encode("utf-8") if isinstance(root_key, str) else root_key
    if not isinstance(raw, bytes) or len(raw) < 32:
        raise ValueError("live AE neurochemical root authority changed")
    return hmac.new(raw, label, hashlib.sha256).digest()


def _evidence(fact_id: str, derivation: str) -> bytes:
    return json.dumps(
        {
            "derivation": derivation,
            "fact_id": fact_id,
            "numeric_authority": "exact-defined-AE-substrate-unit",
            "schema": "guala.live_ae_neurochemical_flow.derivation.v1",
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class _Authorities:
    def __init__(self, root_key: bytes | str) -> None:
        self.manifest_key = _key(
            root_key, b"guala-live-ae-neurochemical-manifest-v1"
        )
        self.flow_key = self.manifest_key
        self.mount_key = _key(
            root_key, b"guala-live-ae-neurochemical-mount-v1"
        )
        self.quantity = PhysicalQuantityIssuerAuthority.from_private_key_bytes(
            issuer_id=_QUANTITY_ISSUER_ID,
            private_key_bytes=_key(
                root_key, b"guala-live-ae-neurochemical-quantity-ed25519-v1"
            ),
        )
        self.excitation = (
            NeurochemicalUpstreamIssuerAuthority.from_private_key_bytes(
                issuer_id=_EXCITATION_ISSUER_ID,
                authority_kind=UpstreamAuthorityKind.EXCITATION,
                private_key_bytes=_key(
                    root_key,
                    b"guala-live-ae-neurochemical-excitation-ed25519-v1",
                ),
            )
        )
        self.clock = NeurochemicalUpstreamIssuerAuthority.from_private_key_bytes(
            issuer_id=_CLOCK_ISSUER_ID,
            authority_kind=UpstreamAuthorityKind.CLOCK,
            private_key_bytes=_key(
                root_key, b"guala-live-ae-neurochemical-clock-ed25519-v1"
            ),
        )
        self.receptor = AELocalReceptorAuthority(
            issuer_id="issuer:guala-ae-local-receptor",
            private_key_bytes=_key(
                root_key, b"guala-live-ae-local-receptor-ed25519-v1"
            ),
        )


def _signed(
    authority: PhysicalQuantityIssuerAuthority,
    *,
    quantity_id: str,
    role: str,
    value: Fraction,
    unit: str,
    derivation: str,
) -> SignedPhysicalQuantity:
    return authority.sign(
        quantity_id=quantity_id,
        quantity_role=role,
        value=value,
        unit=unit,
        provenance_id=hashlib.sha256(
            _evidence(quantity_id, derivation)
        ).hexdigest(),
    )


def build_live_ae_neurochemical_manifest(
    root_key: bytes | str,
) -> NeurochemicalFlowManifest:
    """Build the one deterministic production topology and its signed facts."""

    authorities = _Authorities(root_key)
    quantity = authorities.quantity
    structural_time = _signed(
        quantity,
        quantity_id="quantity:ae-neurochemical:structural-time",
        role="manifest/structural_time_unit",
        value=Fraction(1),
        unit="time",
        derivation="one exact causal duration unit",
    )
    backend_evidence = _evidence(
        "backend:pinned-arb-128",
        "pinned single-thread Arb matrix exponential at 128 bits",
    )
    backend = NeurochemicalBackendMount(
        authority_id="backend:guala-pinned-arb-128",
        working_precision_bits=128,
        derivation_receipt_payload=backend_evidence,
        derivation_receipt_sha256=hashlib.sha256(
            backend_evidence
        ).hexdigest(),
    )
    species = tuple(
        NeurochemicalSpeciesMount(
            species_id=species_id,
            quantity_unit=unit,
            conserved_mass_per_quantity=_signed(
                quantity,
                quantity_id=f"quantity:mass:{species_id}",
                role=(
                    f"species/{species_id}/conserved_mass_per_quantity"
                ),
                value=Fraction(1),
                unit=f"mass-per-{unit}",
                derivation=(
                    "one carrier quantum defines one conserved AE mass unit"
                ),
            ),
        )
        for species_id, unit in (
            (EXCITATION_SPECIES_ID, EXCITATION_UNIT),
            (RECOVERY_SPECIES_ID, RECOVERY_UNIT),
        )
    )
    node_facts = [
        ("node:ae-recovery-body", NodeKind.PHYSICAL),
        ("node:ae-recovery-sink", NodeKind.EXTERNAL_SINK_RESERVOIR),
        ("node:ae-recovery-source", NodeKind.EXTERNAL_SOURCE_RESERVOIR),
    ]
    for sense in SENSE_IDS:
        node_facts.extend((
            (f"node:ae-excitation:{sense}:a", NodeKind.PHYSICAL),
            (f"node:ae-excitation:{sense}:b", NodeKind.PHYSICAL),
        ))
    nodes = tuple(
        NeurochemicalNodeMount(
            node_id=node_id,
            kind=kind,
            volume=_signed(
                quantity,
                quantity_id=f"quantity:volume:{node_id}",
                role=f"node/{node_id}/volume",
                value=Fraction(1),
                unit="volume",
                derivation="one bounded AE nodal compartment volume",
            ),
        )
        for node_id, kind in sorted(node_facts)
    )
    component_facts = [
        (
            "component:ae-recovery:body",
            RECOVERY_SPECIES_ID,
            "node:ae-recovery-body",
            RECOVERY_UNIT,
            Fraction(0),
        ),
        (
            "component:ae-recovery:sink",
            RECOVERY_SPECIES_ID,
            "node:ae-recovery-sink",
            RECOVERY_UNIT,
            Fraction(0),
        ),
        (
            "component:ae-recovery:source",
            RECOVERY_SPECIES_ID,
            "node:ae-recovery-source",
            RECOVERY_UNIT,
            Fraction(1),
        ),
    ]
    for sense in SENSE_IDS:
        component_facts.extend((
            (
                f"component:ae-excitation:{sense}:a",
                EXCITATION_SPECIES_ID,
                f"node:ae-excitation:{sense}:a",
                EXCITATION_UNIT,
                Fraction(1),
            ),
            (
                f"component:ae-excitation:{sense}:b",
                EXCITATION_SPECIES_ID,
                f"node:ae-excitation:{sense}:b",
                EXCITATION_UNIT,
                Fraction(0),
            ),
        ))
    components = tuple(
        NeurochemicalCompartmentMount(
            component_id=component_id,
            species_id=species_id,
            node_id=node_id,
            initial_quantity=_signed(
                quantity,
                quantity_id=f"quantity:initial:{component_id}",
                role=f"component/{component_id}/initial_quantity",
                value=initial,
                unit=unit,
                derivation=(
                    "one conserved token per sensory toggle; one recovery "
                    "token in the closed circulation"
                ),
            ),
        )
        for component_id, species_id, node_id, unit, initial
        in sorted(component_facts)
    )
    impulse_routes = tuple(
        NeurochemicalImpulseRoute(
            lane_id=f"lane:ae-excitation:{sense}:{source}-{target}",
            kind=DirectedLaneKind.SYNAPTIC,
            species_id=EXCITATION_SPECIES_ID,
            source_component_id=(
                f"component:ae-excitation:{sense}:{source}"
            ),
            target_component_id=(
                f"component:ae-excitation:{sense}:{target}"
            ),
        )
        for sense in SENSE_IDS
        for source, target in (("a", "b"), ("b", "a"))
    )

    def drift(
        lane_id: str,
        kind: DirectedLaneKind,
        source: str,
        target: str,
    ) -> NeurochemicalDriftLane:
        return NeurochemicalDriftLane(
            lane_id=lane_id,
            kind=kind,
            species_id=RECOVERY_SPECIES_ID,
            source_component_id=source,
            target_component_id=target,
            velocity=_signed(
                quantity,
                quantity_id=f"quantity:velocity:{lane_id}",
                role=f"drift/{lane_id}/velocity",
                value=Fraction(1),
                unit="length-per-time",
                derivation="one nodal lane length per causal duration unit",
            ),
            interface_area=_signed(
                quantity,
                quantity_id=f"quantity:area:{lane_id}",
                role=f"drift/{lane_id}/interface_area",
                value=Fraction(1),
                unit="area",
                derivation="one bounded nodal interface area",
            ),
        )

    drift_lanes = (
        drift(
            "drift:ae-recovery:body-to-sink",
            DirectedLaneKind.CSF_CLEARANCE,
            "component:ae-recovery:body",
            "component:ae-recovery:sink",
        ),
        drift(
            "drift:ae-recovery:sink-to-source",
            DirectedLaneKind.CIRCULATORY,
            "component:ae-recovery:sink",
            "component:ae-recovery:source",
        ),
        drift(
            "drift:ae-recovery:source-to-body",
            DirectedLaneKind.CIRCULATORY,
            "component:ae-recovery:source",
            "component:ae-recovery:body",
        ),
    )
    target_evidence = _evidence(
        "targets:ae-sensory-excitation",
        "each target exposes its complete local carrier compartment",
    )
    local_targets = tuple(
        LocalNeurochemicalTarget(
            target_id=f"target:ae-excitation:{sense}:{position}",
            component_id=(
                f"component:ae-excitation:{sense}:{position}"
            ),
            kind=LocalTargetKind.MEMBRANE_CONDUCTANCE,
            receptor_activation_availability=(
                MechanismAvailability.AVAILABLE
            ),
            derivation_receipt_payload=target_evidence,
            derivation_receipt_sha256=hashlib.sha256(
                target_evidence
            ).hexdigest(),
        )
        for sense in SENSE_IDS
        for position in ("a", "b")
    )
    nonlinear_evidence = _evidence(
        "mechanism:ae-receptor-binding",
        "no exact local receptor activation kinetics are yet mounted",
    )
    unavailable_nonlinear = (
        UnavailableNonlinearMechanism(
            mechanism_id="mechanism:ae-receptor-binding-activation",
            kind=NonlinearMechanismKind.RECEPTOR_BINDING_ACTIVATION,
            availability=MechanismAvailability.UNAVAILABLE,
            reason="exact local receptor activation kinetics are not mounted",
            derivation_receipt_payload=nonlinear_evidence,
            derivation_receipt_sha256=hashlib.sha256(
                nonlinear_evidence
            ).hexdigest(),
        ),
    )
    physical_permissions = tuple(
        PhysicalReceiptRoutePermission(
            route_id=f"route:ae-excitation:{sense}:{source}-{target}",
            issuer_id=_EXCITATION_ISSUER_ID,
            source_kind=CausalSourceKind.EXCITATION,
            source_component_id=(
                f"component:ae-excitation:{sense}:{source}"
            ),
            lane_id=f"lane:ae-excitation:{sense}:{source}-{target}",
            destination_component_id=(
                f"component:ae-excitation:{sense}:{target}"
            ),
            amount_unit=EXCITATION_UNIT,
        )
        for sense in SENSE_IDS
        for source, target in (("a", "b"), ("b", "a"))
    )
    temporal_permissions = tuple(
        TemporalReceiptRoutePermission(
            route_id=f"route:ae-temporal-clock:{lane.lane_id}:enable",
            issuer_id=_CLOCK_ISSUER_ID,
            driver_kind=TemporalDriverKind.INTRINSIC,
            lane_id=lane.lane_id,
            lane_enabled=True,
            physical_parameter_path=(
                f"lane_state/{lane.lane_id}/enabled"
            ),
        )
        for lane in drift_lanes
    )
    return create_neurochemical_flow_manifest(
        authority_key=authorities.manifest_key,
        manifest_id="manifest:guala-live-ae-neurochemical-flow-v1",
        structural_time_unit=structural_time,
        backend=backend,
        physical_quantity_issuers=(quantity.verifier_mount,),
        species=species,
        nodes=nodes,
        components=components,
        impulse_routes=impulse_routes,
        drift_lanes=drift_lanes,
        diffusion_interfaces=(),
        conversions=(),
        upstream_issuers=(
            authorities.excitation.verifier_mount,
            authorities.clock.verifier_mount,
        ),
        physical_route_permissions=physical_permissions,
        temporal_route_permissions=temporal_permissions,
        local_targets=local_targets,
        unavailable_nonlinear_mechanisms=unavailable_nonlinear,
        initial_enabled_transport_ids=tuple(
            lane.lane_id for lane in drift_lanes
        ),
        capacity=NeurochemicalCapacity(
            max_components=32,
            max_lanes=32,
            max_reactions=4,
            max_targets=16,
            max_events_per_boundary=8,
            max_active_block_components=4,
            max_derivation_receipt_bytes=4_096,
            max_causal_receipt_bytes=65_536,
            max_event_bytes=1_048_576,
            max_state_bytes=8 * 1024 * 1024,
        ),
    )


def live_ae_neurochemical_compartment_references(
    root_key: bytes | str,
) -> tuple[NeurochemicalCompartmentReference, ...]:
    """Bind the internal body to every live carrier compartment."""

    manifest = build_live_ae_neurochemical_manifest(root_key)
    unit_by_species = {
        value.species_id: value.quantity_unit
        for value in manifest.species
    }
    return tuple(
        NeurochemicalCompartmentReference(
            reference_id=f"reference:{component.component_id}",
            species_id=component.species_id,
            node_id=component.node_id,
            quantity_unit=unit_by_species[component.species_id],
            manifest_receipt_sha256=manifest.authority_receipt_sha256,
            compartment_receipt_sha256=hashlib.sha256(
                _canonical(component.record())
            ).hexdigest(),
        )
        for component in manifest.components
    )


class LiveAENeurochemicalFlowOwner:
    """Production custody, event issuance, advancement, and cold restore."""

    def __init__(
        self,
        *,
        root_key: bytes | str,
        body_authority: PhysicalInternalBodyStateAuthority,
        recovery_owner: ExactWholeOrganismRecoveryOwner,
        max_state_bytes: int,
    ) -> None:
        self._root_key = root_key
        self._authorities = _Authorities(root_key)
        self._manifest = build_live_ae_neurochemical_manifest(root_key)
        self._profile = WholeOrganismNeurochemicalMountProfile.create(
            profile_id="guala-live-ae-neurochemical-mount-v1",
            max_upstream_receipts_per_boundary=8,
            max_state_bytes=max_state_bytes,
        )
        unavailable = (
            UnavailableChemicalReaction.create(
                reaction_id="reaction:biological-neurotransmitter-kinetics",
                reason="no authenticated biological species quantities",
                derivation_evidence={
                    "available": (
                        "AE-native conservative carrier transport"
                    ),
                    "unavailable": (
                        "dopamine serotonin and other biological kinetics"
                    ),
                },
            ),
        )
        self._unavailable = unavailable
        self._body = body_authority
        self._recovery = recovery_owner
        self._owner = WholeOrganismNeurochemicalMountOwner(
            authority_key=self._authorities.mount_key,
            profile=self._profile,
            flow_authority_key=self._authorities.flow_key,
            flow_manifest=self._manifest,
            body_authority=body_authority,
            recovery_owner=recovery_owner,
            unavailable_reactions=unavailable,
        )

    @property
    def flow_state(self):
        return self._owner.flow_state

    @property
    def boundary(self):
        return self._owner.boundary

    @property
    def local_receptor_verifier(
        self,
    ) -> AELocalReceptorVerifierMount:
        return self._authorities.receptor.verifier_mount

    def _next_sequence(self, issuer_id: str) -> int:
        return dict(
            self.flow_state.last_accepted_sequence_by_issuer
        )[issuer_id] + 1

    def advance(
        self,
        settlement: CausalExperienceSettlement,
    ):
        settlement.verify()
        if (
            self.boundary is not None
            and self.boundary.settlement_receipt_sha256
            == settlement.authority_receipt_sha256
        ):
            return self.boundary
        duration = settlement.source_time_end - settlement.source_time_start
        if duration <= 0:
            raise ValueError(
                "AE neurochemical boundary requires positive lived duration"
            )
        chemical_start = self.flow_state.source_time
        chemical_end = chemical_start + duration
        values = dict(self.flow_state.component_values)
        receipts = []
        event_id = (
            "event:ae-neurochemical-boundary:"
            f"{settlement.authority_receipt_sha256}"
        )
        sequence = self._next_sequence(_EXCITATION_ISSUER_ID)
        observed = tuple(sorted(
            value.sense
            for value in settlement.interpretations
            if value.state == "observed"
        ))
        for sense in observed:
            if sense not in SENSE_IDS:
                raise ValueError(
                    "AE neurochemical excitation left mounted senses"
                )
            component_a = f"component:ae-excitation:{sense}:a"
            component_b = f"component:ae-excitation:{sense}:b"
            if values[component_a] == 1 and values[component_b] == 0:
                source, target = "a", "b"
            elif values[component_a] == 0 and values[component_b] == 1:
                source, target = "b", "a"
            else:
                raise ValueError(
                    "AE sensory excitation token lost exact nodal position"
                )
            lane_id = f"lane:ae-excitation:{sense}:{source}-{target}"
            receipts.append(self._authorities.excitation.sign_physical(
                chemistry_sequence=sequence,
                event_id=event_id,
                source_time_start=chemical_start,
                source_time_end=chemical_end,
                source_component_id=(
                    f"component:ae-excitation:{sense}:{source}"
                ),
                lane_id=lane_id,
                destination_component_id=(
                    f"component:ae-excitation:{sense}:{target}"
                ),
                amount=Fraction(1),
                amount_unit=EXCITATION_UNIT,
            ))
            sequence += 1
        if not receipts:
            clock_sequence = self._next_sequence(_CLOCK_ISSUER_ID)
            receipts.append(self._authorities.clock.sign_temporal(
                chemistry_sequence=clock_sequence,
                event_id=event_id,
                source_time_start=chemical_start,
                source_time_end=chemical_end,
                driver_kind=TemporalDriverKind.INTRINSIC,
                lane_id="drift:ae-recovery:source-to-body",
                lane_enabled=True,
                physical_parameter_path=(
                    "lane_state/drift:ae-recovery:source-to-body/enabled"
                ),
            ))
        prepared = self._owner.prepare(
            settlement=settlement,
            upstream_receipts=tuple(receipts),
            flow_source_time_start=chemical_start,
            flow_source_time_end=chemical_end,
        )
        self._owner.commit(prepared)
        return self._owner.boundary

    def local_receptor_activations(
        self,
        settlement: CausalExperienceSettlement,
    ):
        """Issue six exact activation/zero receipts from the current pass-off."""

        settlement.verify()
        boundary = self.boundary
        transition = self._owner.last_transition
        if (
            boundary is None
            or transition is None
            or boundary.settlement_receipt_sha256
            != settlement.authority_receipt_sha256
            or boundary.flow_event_receipt_sha256
            != transition.event.authority_receipt_sha256
            or boundary.flow_transition_receipt_sha256
            != transition.receipt_sha256
        ):
            raise ValueError(
                "local receptor activation lacks the current chemical boundary"
            )
        exposure_by_component = {
            value.component_id: value
            for value in transition.local_target_exposures
            if (
                value.receptor_activation_availability
                is MechanismAvailability.AVAILABLE
            )
        }
        passoff_by_sense = {}
        for passoff in transition.event.physical_receipts:
            prefix = "component:ae-excitation:"
            if not passoff.destination_component_id.startswith(prefix):
                continue
            suffix = passoff.destination_component_id.removeprefix(prefix)
            sense, separator, position = suffix.partition(":")
            if (
                not separator
                or sense not in SENSE_IDS
                or position not in {"a", "b"}
                or sense in passoff_by_sense
            ):
                raise ValueError(
                    "local receptor pass-off left one-sense destination"
                )
            exposure = exposure_by_component.get(
                passoff.destination_component_id
            )
            target_id = f"target:ae-excitation:{sense}:{position}"
            if (
                exposure is None
                or exposure.target_id != target_id
                or exposure.component_id
                != passoff.destination_component_id
            ):
                raise ValueError(
                    "local receptor pass-off lacks its available target"
                )
            passoff_by_sense[sense] = (passoff, exposure)
        result = []
        for sense in SENSE_IDS:
            pair = passoff_by_sense.get(sense)
            if pair is None:
                target_id = None
                component_id = None
                passoff_receipt = None
                exposure_receipt = None
                state = 0
            else:
                passoff, exposure = pair
                target_id = exposure.target_id
                component_id = exposure.component_id
                passoff_receipt = hashlib.sha256(
                    _canonical(passoff.record())
                ).hexdigest()
                exposure_receipt = hashlib.sha256(
                    _canonical(exposure.record())
                ).hexdigest()
                state = 1
            result.append(self._authorities.receptor.sign(
                sense=sense,
                activation_state=state,
                settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                chemical_boundary_receipt_sha256=(
                    boundary.authority_receipt_sha256
                ),
                flow_event_receipt_sha256=(
                    transition.event.authority_receipt_sha256
                ),
                flow_transition_receipt_sha256=(
                    transition.receipt_sha256
                ),
                target_id=target_id,
                component_id=component_id,
                carrier_passoff_receipt_sha256=passoff_receipt,
                local_target_exposure_receipt_sha256=exposure_receipt,
            ))
        return tuple(result)

    def snapshot_encoded(self) -> bytes:
        return self._owner.snapshot_encoded()

    def status(self) -> dict[str, object]:
        state = self._owner.status()
        return {
            **state,
            "available": True,
            "chemistry_authority": True,
            "cold_restorable": True,
            "conservative": True,
            "field_source_time": (
                f"{self.flow_state.source_time.numerator}/"
                f"{self.flow_state.source_time.denominator}"
            ),
            "local_receptor_coupling": "available_exact_event_state",
            "mounted_sensory_carriers": len(SENSE_IDS),
            "schema": STATUS_SCHEMA,
        }

    @classmethod
    def restore_encoded(
        cls,
        *,
        root_key: bytes | str,
        body_authority: PhysicalInternalBodyStateAuthority,
        recovery_owner: ExactWholeOrganismRecoveryOwner,
        max_state_bytes: int,
        encoded: bytes,
    ) -> "LiveAENeurochemicalFlowOwner":
        result = cls(
            root_key=root_key,
            body_authority=body_authority,
            recovery_owner=recovery_owner,
            max_state_bytes=max_state_bytes,
        )
        result._owner = WholeOrganismNeurochemicalMountOwner.restore_encoded(
            authority_key=result._authorities.mount_key,
            profile=result._profile,
            flow_authority_key=result._authorities.flow_key,
            flow_manifest=result._manifest,
            body_authority=body_authority,
            recovery_owner=recovery_owner,
            unavailable_reactions=result._unavailable,
            encoded=encoded,
        )
        if result.snapshot_encoded() != encoded:
            raise ValueError(
                "live AE neurochemical cold round-trip changed bytes"
            )
        return result


__all__ = (
    "EXCITATION_SPECIES_ID",
    "EXCITATION_UNIT",
    "LiveAENeurochemicalFlowOwner",
    "RECOVERY_SPECIES_ID",
    "RECOVERY_UNIT",
    "SENSE_IDS",
    "STATUS_SCHEMA",
    "build_live_ae_neurochemical_manifest",
    "live_ae_neurochemical_compartment_references",
)
