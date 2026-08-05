"""Exact D3 model of typed sparse Krimelack phase/winding coupling.

This model implements the phase/winding-first law approved for falsification.
It leaves frozen L0--L4 unchanged.  A local D1 sign/null coordinate and typed
winding events reach a matching Krimelack component after L4.  The component
has a centered balanced-ternary phase residue and an integer winding count.
Crossing its exact ``3**width`` boundary emits a signed event on each declared
sparse route for delivery at the next organism generation.

The model contains no float, learned weight, threshold, score, similarity,
semantic label, dense matrix, or cross-coordinate addition.  Full DSF and
perspective authority remain explicit by receipt on every local drive.  A
passing model is architecture evidence only; native implementation and live
deployment require separate gates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


SCHEMA = "guala.research.typed_krimelack_phase_coupling.v1"
FIELD_FAMILIES = frozenset({
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
})
FACT_KINDS = frozenset({
    "vertex_value",
    "availability",
    "reversal",
    "prior_product",
    "current_product",
    "displacement_product",
    "oriented_area",
})


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _digest_value(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{name} is invalid")
    return value


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


@dataclass(frozen=True, slots=True, order=True)
class CoordinateType:
    field_family: str
    fact_kind: str

    def verify(self) -> None:
        if self.field_family not in FIELD_FAMILIES:
            raise ValueError("Krimelack coordinate field family is unknown")
        if self.fact_kind not in FACT_KINDS:
            raise ValueError("Krimelack coordinate fact kind is unknown")
        compatible = {
            "D_k": {"vertex_value"},
            "M_k": {"vertex_value"},
            "R_rev_k": {"reversal"},
            "U_star_k": {"availability"},
            "C_k": {
                "prior_product",
                "current_product",
                "displacement_product",
                "oriented_area",
            },
            "P_k": {"vertex_value"},
            "B_k": {"vertex_value"},
        }
        if self.fact_kind not in compatible[self.field_family]:
            raise ValueError("Krimelack coordinate family and fact differ")

    def as_record(self) -> dict[str, str]:
        return {
            "fact_kind": self.fact_kind,
            "field_family": self.field_family,
        }


@dataclass(frozen=True, slots=True, order=True)
class ComponentAddress:
    neuron_lineage: str
    component_id: str

    def verify(self) -> None:
        _identifier(self.neuron_lineage, "neuron lineage")
        _identifier(self.component_id, "Krimelack component id")

    def as_record(self) -> dict[str, str]:
        return {
            "component_id": self.component_id,
            "neuron_lineage": self.neuron_lineage,
        }


@dataclass(frozen=True, slots=True)
class PhaseComponent:
    address: ComponentAddress
    coordinate_type: CoordinateType
    ternary_width: int
    phase_residue: int
    winding: int
    last_transition_generation: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        address: ComponentAddress,
        coordinate_type: CoordinateType,
        ternary_width: int,
        phase_residue: int,
        winding: int,
        last_transition_generation: int,
        max_working_trits: int,
    ) -> "PhaseComponent":
        address.verify()
        coordinate_type.verify()
        width = _integer(ternary_width, "ternary width")
        if width <= 0 or width > max_working_trits:
            raise ValueError("phase width exceeds admitted working trits")
        residue = _integer(phase_residue, "phase residue")
        exact_winding = _integer(winding, "winding")
        generation = _integer(
            last_transition_generation,
            "component transition generation",
        )
        if generation < 0:
            raise ValueError("component transition generation is negative")
        modulus = 3**width
        half = (modulus - 1) // 2
        if not -half <= residue <= half:
            raise ValueError("phase residue is outside its centered word")
        unsigned = {
            "address": address.as_record(),
            "coordinate_type": coordinate_type.as_record(),
            "last_transition_generation": generation,
            "phase_residue": residue,
            "ternary_width": width,
            "type": "phase_component",
            "winding": exact_winding,
        }
        return cls(
            address=address,
            coordinate_type=coordinate_type,
            ternary_width=width,
            phase_residue=residue,
            winding=exact_winding,
            last_transition_generation=generation,
            authority_receipt_sha256=_digest(unsigned),
        )

    def as_record(self) -> dict[str, object]:
        return {
            "address": self.address.as_record(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "coordinate_type": self.coordinate_type.as_record(),
            "last_transition_generation": self.last_transition_generation,
            "phase_residue": self.phase_residue,
            "ternary_width": self.ternary_width,
            "winding": self.winding,
        }

    def verify(self, *, max_working_trits: int) -> None:
        expected = PhaseComponent.create(
            address=self.address,
            coordinate_type=self.coordinate_type,
            ternary_width=self.ternary_width,
            phase_residue=self.phase_residue,
            winding=self.winding,
            last_transition_generation=self.last_transition_generation,
            max_working_trits=max_working_trits,
        )
        if expected != self:
            raise ValueError("phase component authority changed")


@dataclass(frozen=True, slots=True, order=True)
class SparsePhaseRoute:
    source: ComponentAddress
    target: ComponentAddress
    coordinate_type: CoordinateType
    topology_generation: int
    topology_authority_receipt_sha256: str
    edge_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        source: ComponentAddress,
        target: ComponentAddress,
        coordinate_type: CoordinateType,
        topology_generation: int,
        topology_authority_receipt_sha256: str,
    ) -> "SparsePhaseRoute":
        source.verify()
        target.verify()
        coordinate_type.verify()
        if source == target:
            raise ValueError("sparse phase route cannot be a self-edge")
        generation = _integer(topology_generation, "topology generation")
        if generation <= 0:
            raise ValueError("topology generation must be positive")
        authority = _digest_value(
            topology_authority_receipt_sha256,
            "topology authority",
        )
        unsigned = {
            "coordinate_type": coordinate_type.as_record(),
            "source": source.as_record(),
            "target": target.as_record(),
            "topology_authority_receipt_sha256": authority,
            "topology_generation": generation,
            "type": "sparse_phase_route",
        }
        return cls(
            source=source,
            target=target,
            coordinate_type=coordinate_type,
            topology_generation=generation,
            topology_authority_receipt_sha256=authority,
            edge_receipt_sha256=_digest(unsigned),
        )

    def as_record(self) -> dict[str, object]:
        return {
            "coordinate_type": self.coordinate_type.as_record(),
            "edge_receipt_sha256": self.edge_receipt_sha256,
            "source": self.source.as_record(),
            "target": self.target.as_record(),
            "topology_authority_receipt_sha256": (
                self.topology_authority_receipt_sha256
            ),
            "topology_generation": self.topology_generation,
        }

    def verify(self) -> None:
        expected = SparsePhaseRoute.create(
            source=self.source,
            target=self.target,
            coordinate_type=self.coordinate_type,
            topology_generation=self.topology_generation,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
        )
        if expected != self:
            raise ValueError("sparse phase route authority changed")


@dataclass(frozen=True, slots=True)
class LocalPhaseDrive:
    target: ComponentAddress
    coordinate_type: CoordinateType
    structural_trit: int
    complete_field_receipt_sha256: str
    perspective_receipt_sha256: str
    local_fractal_receipt_sha256: str
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        target: ComponentAddress,
        coordinate_type: CoordinateType,
        structural_trit: int,
        complete_field_receipt_sha256: str,
        perspective_receipt_sha256: str,
        local_fractal_receipt_sha256: str,
    ) -> "LocalPhaseDrive":
        target.verify()
        coordinate_type.verify()
        trit = _integer(structural_trit, "local structural trit")
        if trit not in (-1, 0, 1):
            raise ValueError("local structural drive must be a trit")
        field = _digest_value(
            complete_field_receipt_sha256,
            "complete field authority",
        )
        perspective = _digest_value(
            perspective_receipt_sha256,
            "local perspective authority",
        )
        fractal = _digest_value(
            local_fractal_receipt_sha256,
            "local fractal authority",
        )
        unsigned = {
            "complete_field_receipt_sha256": field,
            "coordinate_type": coordinate_type.as_record(),
            "local_fractal_receipt_sha256": fractal,
            "perspective_receipt_sha256": perspective,
            "structural_trit": trit,
            "target": target.as_record(),
            "type": "local_phase_drive",
        }
        return cls(
            target=target,
            coordinate_type=coordinate_type,
            structural_trit=trit,
            complete_field_receipt_sha256=field,
            perspective_receipt_sha256=perspective,
            local_fractal_receipt_sha256=fractal,
            authority_receipt_sha256=_digest(unsigned),
        )

    def as_record(self) -> dict[str, object]:
        return {
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "complete_field_receipt_sha256": (
                self.complete_field_receipt_sha256
            ),
            "coordinate_type": self.coordinate_type.as_record(),
            "local_fractal_receipt_sha256": (
                self.local_fractal_receipt_sha256
            ),
            "perspective_receipt_sha256": (
                self.perspective_receipt_sha256
            ),
            "structural_trit": self.structural_trit,
            "target": self.target.as_record(),
        }

    def verify(self) -> None:
        expected = LocalPhaseDrive.create(
            target=self.target,
            coordinate_type=self.coordinate_type,
            structural_trit=self.structural_trit,
            complete_field_receipt_sha256=(
                self.complete_field_receipt_sha256
            ),
            perspective_receipt_sha256=self.perspective_receipt_sha256,
            local_fractal_receipt_sha256=(
                self.local_fractal_receipt_sha256
            ),
        )
        if expected != self:
            raise ValueError("local phase drive authority changed")


@dataclass(frozen=True, slots=True, order=True)
class WindingEvent:
    route_receipt_sha256: str
    source: ComponentAddress
    target: ComponentAddress
    coordinate_type: CoordinateType
    source_generation: int
    delivery_generation: int
    signed_crossing_count: int
    source_settlement_receipt_sha256: str
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        route: SparsePhaseRoute,
        source_generation: int,
        signed_crossing_count: int,
        source_settlement_receipt_sha256: str,
    ) -> "WindingEvent":
        route.verify()
        generation = _integer(source_generation, "event source generation")
        crossing = _integer(signed_crossing_count, "winding crossing count")
        if generation <= 0 or crossing == 0:
            raise ValueError("winding event generation or crossing is invalid")
        settlement = _digest_value(
            source_settlement_receipt_sha256,
            "source settlement authority",
        )
        unsigned = {
            "coordinate_type": route.coordinate_type.as_record(),
            "delivery_generation": generation + 1,
            "route_receipt_sha256": route.edge_receipt_sha256,
            "signed_crossing_count": crossing,
            "source": route.source.as_record(),
            "source_generation": generation,
            "source_settlement_receipt_sha256": settlement,
            "target": route.target.as_record(),
            "type": "winding_event",
        }
        return cls(
            route_receipt_sha256=route.edge_receipt_sha256,
            source=route.source,
            target=route.target,
            coordinate_type=route.coordinate_type,
            source_generation=generation,
            delivery_generation=generation + 1,
            signed_crossing_count=crossing,
            source_settlement_receipt_sha256=settlement,
            authority_receipt_sha256=_digest(unsigned),
        )

    def as_record(self) -> dict[str, object]:
        return {
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "coordinate_type": self.coordinate_type.as_record(),
            "delivery_generation": self.delivery_generation,
            "route_receipt_sha256": self.route_receipt_sha256,
            "signed_crossing_count": self.signed_crossing_count,
            "source": self.source.as_record(),
            "source_generation": self.source_generation,
            "source_settlement_receipt_sha256": (
                self.source_settlement_receipt_sha256
            ),
            "target": self.target.as_record(),
        }


@dataclass(frozen=True, slots=True)
class PhaseSettlement:
    target: ComponentAddress
    generation: int
    predecessor_component_receipt_sha256: str
    local_drive_receipt_sha256: str | None
    consumed_event_receipts: tuple[str, ...]
    net_drive: int
    phase_residue: int
    winding: int
    winding_delta: int
    successor_component_receipt_sha256: str
    authority_receipt_sha256: str

    def as_record(self) -> dict[str, object]:
        return {
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "consumed_event_receipts": list(self.consumed_event_receipts),
            "generation": self.generation,
            "local_drive_receipt_sha256": self.local_drive_receipt_sha256,
            "net_drive": self.net_drive,
            "phase_residue": self.phase_residue,
            "predecessor_component_receipt_sha256": (
                self.predecessor_component_receipt_sha256
            ),
            "successor_component_receipt_sha256": (
                self.successor_component_receipt_sha256
            ),
            "target": self.target.as_record(),
            "winding": self.winding,
            "winding_delta": self.winding_delta,
        }


@dataclass(frozen=True, slots=True)
class PhaseFabric:
    generation: int
    components: tuple[PhaseComponent, ...]
    routes: tuple[SparsePhaseRoute, ...]
    pending_events: tuple[WindingEvent, ...]
    settlements: tuple[PhaseSettlement, ...]
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "components": [value.as_record() for value in self.components],
            "generation": self.generation,
            "pending_events": [
                value.as_record() for value in self.pending_events
            ],
            "routes": [value.as_record() for value in self.routes],
            "schema": SCHEMA,
            "settlements": [
                value.as_record() for value in self.settlements
            ],
        }

    def encode(self, *, max_state_bytes: int) -> bytes:
        if (
            isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or max_state_bytes <= 0
        ):
            raise ValueError("phase fabric state boundary must be positive")
        encoded = _canonical_bytes({
            **self.unsigned_record(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        })
        if len(encoded) > max_state_bytes:
            raise ValueError(
                f"phase fabric requires {len(encoded)} state bytes, "
                f"admitted {max_state_bytes}"
            )
        return encoded


def _settlement(
    *,
    predecessor: PhaseComponent,
    generation: int,
    local_drive: LocalPhaseDrive | None,
    events: tuple[WindingEvent, ...],
    max_working_trits: int,
) -> tuple[PhaseComponent, PhaseSettlement]:
    net_drive = (
        0 if local_drive is None else local_drive.structural_trit
    ) + sum(value.signed_crossing_count for value in events)
    modulus = 3**predecessor.ternary_width
    half = (modulus - 1) // 2
    raw = predecessor.phase_residue + net_drive
    winding_delta, shifted = divmod(raw + half, modulus)
    phase_residue = shifted - half
    if raw != phase_residue + modulus * winding_delta:
        raise AssertionError("centered ternary phase division changed value")
    successor = PhaseComponent.create(
        address=predecessor.address,
        coordinate_type=predecessor.coordinate_type,
        ternary_width=predecessor.ternary_width,
        phase_residue=phase_residue,
        winding=predecessor.winding + winding_delta,
        last_transition_generation=generation,
        max_working_trits=max_working_trits,
    )
    event_receipts = tuple(
        value.authority_receipt_sha256 for value in events
    )
    local_receipt = (
        None if local_drive is None else local_drive.authority_receipt_sha256
    )
    unsigned = {
        "consumed_event_receipts": list(event_receipts),
        "generation": generation,
        "local_drive_receipt_sha256": local_receipt,
        "net_drive": net_drive,
        "phase_residue": successor.phase_residue,
        "predecessor_component_receipt_sha256": (
            predecessor.authority_receipt_sha256
        ),
        "successor_component_receipt_sha256": (
            successor.authority_receipt_sha256
        ),
        "target": predecessor.address.as_record(),
        "type": "phase_settlement",
        "winding": successor.winding,
        "winding_delta": winding_delta,
    }
    settlement = PhaseSettlement(
        target=predecessor.address,
        generation=generation,
        predecessor_component_receipt_sha256=(
            predecessor.authority_receipt_sha256
        ),
        local_drive_receipt_sha256=local_receipt,
        consumed_event_receipts=event_receipts,
        net_drive=net_drive,
        phase_residue=successor.phase_residue,
        winding=successor.winding,
        winding_delta=winding_delta,
        successor_component_receipt_sha256=(
            successor.authority_receipt_sha256
        ),
        authority_receipt_sha256=_digest(unsigned),
    )
    return successor, settlement


def create_phase_fabric(
    *,
    components: tuple[PhaseComponent, ...],
    routes: tuple[SparsePhaseRoute, ...],
    max_state_bytes: int,
    max_working_trits: int,
) -> PhaseFabric:
    if not components:
        raise ValueError("phase fabric has no components")
    ordered_components = tuple(sorted(
        components,
        key=lambda value: value.address,
    ))
    component_by_address = {
        value.address: value for value in ordered_components
    }
    if len(component_by_address) != len(ordered_components):
        raise ValueError("phase component address is duplicated")
    for component in ordered_components:
        component.verify(max_working_trits=max_working_trits)
        if component.last_transition_generation != 0:
            raise ValueError("genesis phase component already transitioned")
    ordered_routes = tuple(sorted(routes))
    if len(set(ordered_routes)) != len(ordered_routes):
        raise ValueError("sparse phase route is duplicated")
    edge_receipts = set()
    for route in ordered_routes:
        route.verify()
        if route.edge_receipt_sha256 in edge_receipts:
            raise ValueError("sparse phase edge receipt is duplicated")
        edge_receipts.add(route.edge_receipt_sha256)
        source = component_by_address.get(route.source)
        target = component_by_address.get(route.target)
        if source is None or target is None:
            raise ValueError("sparse phase route endpoint is absent")
        if (
            source.coordinate_type != route.coordinate_type
            or target.coordinate_type != route.coordinate_type
        ):
            raise ValueError("sparse phase route crosses coordinate types")
    provisional = PhaseFabric(
        generation=0,
        components=ordered_components,
        routes=ordered_routes,
        pending_events=(),
        settlements=(),
        authority_receipt_sha256="",
    )
    result = PhaseFabric(
        generation=0,
        components=ordered_components,
        routes=ordered_routes,
        pending_events=(),
        settlements=(),
        authority_receipt_sha256=_digest(provisional.unsigned_record()),
    )
    result.encode(max_state_bytes=max_state_bytes)
    return result


def transition_phase_fabric(
    *,
    prior: PhaseFabric,
    local_drives: tuple[LocalPhaseDrive, ...],
    max_state_bytes: int,
    max_working_trits: int,
) -> PhaseFabric:
    """Execute one synchronous whole-fabric phase/winding transition."""

    generation = prior.generation + 1
    components = {value.address: value for value in prior.components}
    if len(components) != len(prior.components):
        raise ValueError("prior phase component address is duplicated")
    for component in prior.components:
        component.verify(max_working_trits=max_working_trits)
        if component.last_transition_generation != prior.generation:
            raise ValueError("phase component generation is discontinuous")
    routes_by_receipt = {}
    for route in prior.routes:
        route.verify()
        if route.edge_receipt_sha256 in routes_by_receipt:
            raise ValueError("prior sparse phase route is duplicated")
        routes_by_receipt[route.edge_receipt_sha256] = route

    drive_by_target = {}
    for drive in local_drives:
        drive.verify()
        if drive.target in drive_by_target:
            raise ValueError("phase component repeats a local drive")
        target = components.get(drive.target)
        if target is None or target.coordinate_type != drive.coordinate_type:
            raise ValueError("local drive target or coordinate type differs")
        drive_by_target[drive.target] = drive

    events_by_target: dict[ComponentAddress, list[WindingEvent]] = {}
    seen_event_routes = set()
    for event in prior.pending_events:
        if event.delivery_generation != generation:
            raise ValueError("pending winding event delivery is discontinuous")
        route = routes_by_receipt.get(event.route_receipt_sha256)
        if route is None:
            raise ValueError("pending winding event route is absent")
        expected = WindingEvent.create(
            route=route,
            source_generation=event.source_generation,
            signed_crossing_count=event.signed_crossing_count,
            source_settlement_receipt_sha256=(
                event.source_settlement_receipt_sha256
            ),
        )
        if expected != event:
            raise ValueError("pending winding event authority changed")
        if event.route_receipt_sha256 in seen_event_routes:
            raise ValueError("pending winding event repeats one edge")
        seen_event_routes.add(event.route_receipt_sha256)
        events_by_target.setdefault(event.target, []).append(event)

    successor_components = []
    settlements = []
    settlement_by_source = {}
    for address, predecessor in sorted(components.items()):
        events = tuple(sorted(
            events_by_target.get(address, ()),
            key=lambda value: value.route_receipt_sha256,
        ))
        successor, settlement = _settlement(
            predecessor=predecessor,
            generation=generation,
            local_drive=drive_by_target.get(address),
            events=events,
            max_working_trits=max_working_trits,
        )
        successor_components.append(successor)
        settlements.append(settlement)
        settlement_by_source[address] = settlement

    next_events = []
    for route in prior.routes:
        source_settlement = settlement_by_source[route.source]
        if source_settlement.winding_delta == 0:
            continue
        next_events.append(WindingEvent.create(
            route=route,
            source_generation=generation,
            signed_crossing_count=source_settlement.winding_delta,
            source_settlement_receipt_sha256=(
                source_settlement.authority_receipt_sha256
            ),
        ))

    provisional = PhaseFabric(
        generation=generation,
        components=tuple(successor_components),
        routes=prior.routes,
        pending_events=tuple(sorted(next_events)),
        settlements=tuple(settlements),
        authority_receipt_sha256="",
    )
    result = PhaseFabric(
        generation=provisional.generation,
        components=provisional.components,
        routes=provisional.routes,
        pending_events=provisional.pending_events,
        settlements=provisional.settlements,
        authority_receipt_sha256=_digest(provisional.unsigned_record()),
    )
    result.encode(max_state_bytes=max_state_bytes)
    return result


def decode_phase_fabric(
    payload: bytes,
    *,
    max_state_bytes: int,
    max_working_trits: int,
) -> PhaseFabric:
    if (
        not isinstance(payload, bytes)
        or not payload
        or len(payload) > max_state_bytes
    ):
        raise ValueError("phase fabric cold payload exceeds admitted bytes")
    try:
        record = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("phase fabric cold payload is not JSON") from error
    if _canonical_bytes(record) != payload:
        raise ValueError("phase fabric cold payload is not canonical")
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise ValueError("phase fabric cold schema differs")

    def address(value: object) -> ComponentAddress:
        if not isinstance(value, dict) or set(value) != {
            "component_id", "neuron_lineage"
        }:
            raise ValueError("cold component address changed shape")
        return ComponentAddress(
            neuron_lineage=value["neuron_lineage"],
            component_id=value["component_id"],
        )

    def coordinate(value: object) -> CoordinateType:
        if not isinstance(value, dict) or set(value) != {
            "fact_kind", "field_family"
        }:
            raise ValueError("cold coordinate type changed shape")
        return CoordinateType(
            field_family=value["field_family"],
            fact_kind=value["fact_kind"],
        )

    components = []
    for value in record.get("components", ()):
        component = PhaseComponent.create(
            address=address(value["address"]),
            coordinate_type=coordinate(value["coordinate_type"]),
            ternary_width=value["ternary_width"],
            phase_residue=value["phase_residue"],
            winding=value["winding"],
            last_transition_generation=value["last_transition_generation"],
            max_working_trits=max_working_trits,
        )
        if component.authority_receipt_sha256 != value.get(
            "authority_receipt_sha256"
        ):
            raise ValueError("cold phase component receipt differs")
        components.append(component)

    routes = []
    for value in record.get("routes", ()):
        route = SparsePhaseRoute.create(
            source=address(value["source"]),
            target=address(value["target"]),
            coordinate_type=coordinate(value["coordinate_type"]),
            topology_generation=value["topology_generation"],
            topology_authority_receipt_sha256=(
                value["topology_authority_receipt_sha256"]
            ),
        )
        if route.edge_receipt_sha256 != value.get("edge_receipt_sha256"):
            raise ValueError("cold sparse phase edge receipt differs")
        routes.append(route)

    route_by_receipt = {value.edge_receipt_sha256: value for value in routes}
    events = []
    for value in record.get("pending_events", ()):
        route = route_by_receipt.get(value.get("route_receipt_sha256"))
        if route is None:
            raise ValueError("cold winding event route is absent")
        event = WindingEvent.create(
            route=route,
            source_generation=value["source_generation"],
            signed_crossing_count=value["signed_crossing_count"],
            source_settlement_receipt_sha256=(
                value["source_settlement_receipt_sha256"]
            ),
        )
        if event.as_record() != value:
            raise ValueError("cold winding event differs")
        events.append(event)

    settlements = []
    for value in record.get("settlements", ()):
        unsigned = {
            **value,
            "type": "phase_settlement",
        }
        authority = unsigned.pop("authority_receipt_sha256")
        if _digest(unsigned) != authority:
            raise ValueError("cold phase settlement receipt differs")
        settlements.append(PhaseSettlement(
            target=address(value["target"]),
            generation=value["generation"],
            predecessor_component_receipt_sha256=(
                value["predecessor_component_receipt_sha256"]
            ),
            local_drive_receipt_sha256=value["local_drive_receipt_sha256"],
            consumed_event_receipts=tuple(value["consumed_event_receipts"]),
            net_drive=value["net_drive"],
            phase_residue=value["phase_residue"],
            winding=value["winding"],
            winding_delta=value["winding_delta"],
            successor_component_receipt_sha256=(
                value["successor_component_receipt_sha256"]
            ),
            authority_receipt_sha256=authority,
        ))

    fabric = PhaseFabric(
        generation=record["generation"],
        components=tuple(components),
        routes=tuple(routes),
        pending_events=tuple(events),
        settlements=tuple(settlements),
        authority_receipt_sha256=record["authority_receipt_sha256"],
    )
    if _digest(fabric.unsigned_record()) != fabric.authority_receipt_sha256:
        raise ValueError("cold phase fabric authority differs")
    if fabric.encode(max_state_bytes=max_state_bytes) != payload:
        raise ValueError("cold phase fabric round trip differs")
    return fabric


__all__ = [
    "ComponentAddress",
    "CoordinateType",
    "LocalPhaseDrive",
    "PhaseComponent",
    "PhaseFabric",
    "PhaseSettlement",
    "SparsePhaseRoute",
    "WindingEvent",
    "create_phase_fabric",
    "decode_phase_fabric",
    "transition_phase_fabric",
]
