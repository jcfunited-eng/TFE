"""Exact bounded physical state for Guala's internal organism.

This authority is deliberately upstream of sensory transduction.  It owns
independent, unit-bearing physical quantities and causal structural time.  It
does not map any quantity into a sensory lane, run L0--L4, choose an action,
assign meaning, or claim cognition.

All numeric state is supplied as exact ``Fraction`` values under an
authenticated manifest.  The manifest supplies bounds, conservation groups,
cyclic extents, anatomy/physical parameters, and explicit unavailable
mechanisms.  No biological coefficient or equilibrium is invented here.
Evolution is admitted only from an identified physical-source receipt.
Conserved groups either balance exactly or carry an explicit external exchange
receipt.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Mapping, Sequence


MANIFEST_SCHEMA = "guala.physical_internal_body.manifest.v1"
STATE_SCHEMA = "guala.physical_internal_body.state.v1"
TRANSITION_SCHEMA = "guala.physical_internal_body.transition.v1"
COLD_SCHEMA = "guala.physical_internal_body.cold.v1"

_MANIFEST_DOMAIN = b"guala-physical-internal-body-manifest-v1\0"
_STATE_DOMAIN = b"guala-physical-internal-body-state-v1\0"
_TRANSITION_DOMAIN = b"guala-physical-internal-body-transition-v1\0"
_COLD_DOMAIN = b"guala-physical-internal-body-cold-v1\0"
_HEX = frozenset("0123456789abcdef")
_PREPARED_AUTHORITY = object()
_UNDO_AUTHORITY = object()

MAX_IDENTIFIER_BYTES = 256
MAX_REASON_BYTES = 2_048
MAX_FRACTION_BITS = 4_096


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("internal-body authority key is invalid")
    return raw


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES
    ):
        raise ValueError(f"{label} is not a bounded canonical identifier")
    return value


def _reason(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > MAX_REASON_BYTES
    ):
        raise ValueError(f"{label} is not bounded explicit text")
    return value


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _nonnegative(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _fraction(value: object, label: str) -> Fraction:
    if not isinstance(value, Fraction):
        raise TypeError(f"{label} must be an exact Fraction")
    if (
        abs(value.numerator).bit_length() > MAX_FRACTION_BITS
        or value.denominator.bit_length() > MAX_FRACTION_BITS
    ):
        raise ValueError(f"{label} exceeds the exact rational boundary")
    return value


def _fraction_text(value: Fraction) -> str:
    _fraction(value, "fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object, label: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{label} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{label} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{label} is not a canonical exact fraction")
    return result


class InternalMechanism(str, Enum):
    PROPRIOCEPTION = "proprioception"
    VESTIBULAR = "vestibular"
    THERMAL = "thermal"
    NOCICEPTION = "nociception"
    ENERGY_WATER = "energy_water"
    RESPIRATION = "respiration"
    CIRCULATION = "circulation"
    VISCERAL = "visceral"
    FATIGUE_RECOVERY = "fatigue_recovery"
    CIRCADIAN = "circadian"
    NEUROCHEMICAL = "neurochemical"


class MechanismAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class QuantityEvolutionKind(str, Enum):
    LINEAR = "linear"
    CYCLIC = "cyclic"
    UNAVAILABLE = "unavailable"


REQUIRED_QUANTITY_ROLES: Mapping[InternalMechanism, tuple[str, ...]] = {
    InternalMechanism.PROPRIOCEPTION: (
        "position_x",
        "position_y",
        "position_z",
        "supported_load",
    ),
    InternalMechanism.VESTIBULAR: (
        "linear_acceleration_x",
        "linear_acceleration_y",
        "linear_acceleration_z",
        "orientation_roll",
        "orientation_pitch",
        "orientation_yaw",
    ),
    InternalMechanism.THERMAL: (
        "core_temperature",
        "compartment_temperature",
    ),
    InternalMechanism.NOCICEPTION: (
        "tissue_integrity",
        "nociceptive_load",
    ),
    InternalMechanism.ENERGY_WATER: (
        "energy_inventory",
        "water_inventory",
    ),
    InternalMechanism.RESPIRATION: (
        "respiratory_volume",
        "respiratory_pressure",
        "oxygen_inventory",
        "carbon_dioxide_inventory",
    ),
    InternalMechanism.CIRCULATION: (
        "pulse_phase",
        "perfusion_rate",
    ),
    InternalMechanism.VISCERAL: ("visceral_load",),
    InternalMechanism.FATIGUE_RECOVERY: (
        "fatigue_load",
        "recovery_reserve",
    ),
    InternalMechanism.CIRCADIAN: ("circadian_phase",),
    InternalMechanism.NEUROCHEMICAL: (),
}


@dataclass(frozen=True, slots=True)
class InternalBodyCapacity:
    max_quantities: int
    max_parameters: int
    max_neurochemical_references: int
    max_changes_per_transition: int
    max_conservation_exchanges_per_transition: int
    max_transitions: int
    max_state_bytes: int

    def verify(self) -> None:
        for value, label in (
            (self.max_quantities, "quantity capacity"),
            (self.max_parameters, "parameter capacity"),
            (
                self.max_neurochemical_references,
                "neurochemical reference capacity",
            ),
            (
                self.max_changes_per_transition,
                "transition change capacity",
            ),
            (
                self.max_conservation_exchanges_per_transition,
                "conservation exchange capacity",
            ),
            (self.max_transitions, "transition history capacity"),
            (self.max_state_bytes, "cold-state byte capacity"),
        ):
            _positive(value, label)

    def record(self) -> dict[str, int]:
        self.verify()
        return {
            "max_changes_per_transition": self.max_changes_per_transition,
            "max_conservation_exchanges_per_transition": (
                self.max_conservation_exchanges_per_transition
            ),
            "max_neurochemical_references": (
                self.max_neurochemical_references
            ),
            "max_parameters": self.max_parameters,
            "max_quantities": self.max_quantities,
            "max_state_bytes": self.max_state_bytes,
            "max_transitions": self.max_transitions,
        }


@dataclass(frozen=True, slots=True)
class InternalPhysicalParameter:
    parameter_id: str
    mechanism: InternalMechanism
    unit: str
    value: Fraction
    derivation_receipt_sha256: str

    def verify(self) -> None:
        _identifier(self.parameter_id, "internal physical parameter id")
        if not isinstance(self.mechanism, InternalMechanism):
            raise TypeError("internal physical parameter mechanism is not typed")
        _identifier(self.unit, "internal physical parameter unit")
        _fraction(self.value, "internal physical parameter value")
        _sha(
            self.derivation_receipt_sha256,
            "internal physical parameter derivation",
        )

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            "derivation_receipt_sha256": self.derivation_receipt_sha256,
            "mechanism": self.mechanism.value,
            "parameter_id": self.parameter_id,
            "unit": self.unit,
            "value": _fraction_text(self.value),
        }


@dataclass(frozen=True, slots=True)
class InternalPhysicalQuantity:
    quantity_id: str
    mechanism: InternalMechanism
    role: str
    unit: str
    evolution_kind: QuantityEvolutionKind
    lower_bound: Fraction | None
    upper_bound: Fraction | None
    initial_value: Fraction | None
    conservation_group_id: str | None = None
    cyclic_modulus: Fraction | None = None

    def verify(self) -> None:
        _identifier(self.quantity_id, "internal physical quantity id")
        if not isinstance(self.mechanism, InternalMechanism):
            raise TypeError("internal physical quantity mechanism is not typed")
        _identifier(self.role, "internal physical quantity role")
        _identifier(self.unit, "internal physical quantity unit")
        if not isinstance(self.evolution_kind, QuantityEvolutionKind):
            raise TypeError("internal physical quantity evolution is not typed")
        if self.conservation_group_id is not None:
            _identifier(
                self.conservation_group_id,
                "internal physical conservation group",
            )
        if self.evolution_kind is QuantityEvolutionKind.UNAVAILABLE:
            if any(
                value is not None
                for value in (
                    self.lower_bound,
                    self.upper_bound,
                    self.initial_value,
                    self.cyclic_modulus,
                )
            ):
                raise ValueError(
                    "unavailable internal quantity fabricated numeric state"
                )
            return
        if (
            self.lower_bound is None
            or self.upper_bound is None
            or self.initial_value is None
        ):
            raise ValueError("modeled internal quantity lacks exact bounds")
        lower = _fraction(self.lower_bound, "internal quantity lower bound")
        upper = _fraction(self.upper_bound, "internal quantity upper bound")
        initial = _fraction(self.initial_value, "internal quantity initial value")
        if lower >= upper or not lower <= initial <= upper:
            raise ValueError("internal physical quantity bounds are invalid")
        if self.evolution_kind is QuantityEvolutionKind.CYCLIC:
            if (
                self.cyclic_modulus is None
                or _fraction(
                    self.cyclic_modulus,
                    "internal quantity cyclic modulus",
                )
                <= 0
                or lower != 0
                or upper != self.cyclic_modulus
                or initial == upper
            ):
                raise ValueError(
                    "cyclic internal quantity requires explicit [0,modulus)"
                )
        elif self.cyclic_modulus is not None:
            raise ValueError("linear internal quantity carries a cyclic modulus")

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            "conservation_group_id": self.conservation_group_id,
            "cyclic_modulus": (
                _fraction_text(self.cyclic_modulus)
                if self.cyclic_modulus is not None
                else None
            ),
            "evolution_kind": self.evolution_kind.value,
            "initial_value": (
                _fraction_text(self.initial_value)
                if self.initial_value is not None
                else None
            ),
            "lower_bound": (
                _fraction_text(self.lower_bound)
                if self.lower_bound is not None
                else None
            ),
            "mechanism": self.mechanism.value,
            "quantity_id": self.quantity_id,
            "role": self.role,
            "unit": self.unit,
            "upper_bound": (
                _fraction_text(self.upper_bound)
                if self.upper_bound is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class InternalMechanismMount:
    mechanism: InternalMechanism
    availability: MechanismAvailability
    quantity_ids: tuple[str, ...]
    required_parameter_ids: tuple[str, ...]
    unavailable_reason: str | None = None

    def verify(self) -> None:
        if not isinstance(self.mechanism, InternalMechanism):
            raise TypeError("internal mechanism mount is not typed")
        if not isinstance(self.availability, MechanismAvailability):
            raise TypeError("internal mechanism availability is not typed")
        for values, label in (
            (self.quantity_ids, "internal mechanism quantity ids"),
            (
                self.required_parameter_ids,
                "internal mechanism parameter ids",
            ),
        ):
            if (
                not isinstance(values, tuple)
                or values != tuple(sorted(set(values)))
            ):
                raise ValueError(f"{label} are not canonical")
            for value in values:
                _identifier(value, label)
        if self.availability is MechanismAvailability.UNAVAILABLE:
            _reason(
                self.unavailable_reason,
                "internal mechanism unavailable reason",
            )
        elif self.unavailable_reason is not None:
            raise ValueError(
                "available internal mechanism carries an unavailable reason"
            )

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            "availability": self.availability.value,
            "mechanism": self.mechanism.value,
            "quantity_ids": list(self.quantity_ids),
            "required_parameter_ids": list(self.required_parameter_ids),
            "unavailable_reason": self.unavailable_reason,
        }


@dataclass(frozen=True, slots=True)
class NeurochemicalCompartmentReference:
    reference_id: str
    species_id: str
    node_id: str
    quantity_unit: str
    manifest_receipt_sha256: str
    compartment_receipt_sha256: str

    def verify(self) -> None:
        for value, label in (
            (self.reference_id, "neurochemical reference id"),
            (self.species_id, "neurochemical reference species"),
            (self.node_id, "neurochemical reference node"),
            (self.quantity_unit, "neurochemical reference unit"),
        ):
            _identifier(value, label)
        _sha(
            self.manifest_receipt_sha256,
            "neurochemical reference manifest",
        )
        _sha(
            self.compartment_receipt_sha256,
            "neurochemical compartment reference",
        )

    def record(self) -> dict[str, str]:
        self.verify()
        return {
            "compartment_receipt_sha256": self.compartment_receipt_sha256,
            "manifest_receipt_sha256": self.manifest_receipt_sha256,
            "node_id": self.node_id,
            "quantity_unit": self.quantity_unit,
            "reference_id": self.reference_id,
            "species_id": self.species_id,
        }


@dataclass(frozen=True, slots=True)
class PhysicalInternalBodyManifest:
    manifest_id: str
    structural_time_unit: str
    capacity: InternalBodyCapacity
    mechanisms: tuple[InternalMechanismMount, ...]
    quantities: tuple[InternalPhysicalQuantity, ...]
    parameters: tuple[InternalPhysicalParameter, ...]
    neurochemical_references: tuple[NeurochemicalCompartmentReference, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "capacity": self.capacity.record(),
            "manifest_id": self.manifest_id,
            "mechanisms": [value.record() for value in self.mechanisms],
            "neurochemical_references": [
                value.record() for value in self.neurochemical_references
            ],
            "parameters": [value.record() for value in self.parameters],
            "quantities": [value.record() for value in self.quantities],
            "schema": MANIFEST_SCHEMA,
            "structural_time_unit": self.structural_time_unit,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self, authority_key: bytes | str) -> None:
        _identifier(self.manifest_id, "internal-body manifest id")
        _identifier(self.structural_time_unit, "structural time unit")
        self.capacity.verify()
        expected_mechanisms = tuple(InternalMechanism)
        if (
            tuple(value.mechanism for value in self.mechanisms)
            != expected_mechanisms
        ):
            raise ValueError(
                "internal-body manifest must cover every mechanism in order"
            )
        quantity_ids = tuple(value.quantity_id for value in self.quantities)
        parameter_ids = tuple(value.parameter_id for value in self.parameters)
        reference_ids = tuple(
            value.reference_id for value in self.neurochemical_references
        )
        for values, label, maximum in (
            (
                quantity_ids,
                "internal-body quantities",
                self.capacity.max_quantities,
            ),
            (
                parameter_ids,
                "internal-body parameters",
                self.capacity.max_parameters,
            ),
            (
                reference_ids,
                "internal-body neurochemical references",
                self.capacity.max_neurochemical_references,
            ),
        ):
            if (
                values != tuple(sorted(set(values)))
                or len(values) > maximum
            ):
                raise ValueError(f"{label} exceed canonical capacity")
        quantity_by_id = {}
        roles_by_mechanism: dict[InternalMechanism, set[str]] = {
            value: set() for value in InternalMechanism
        }
        for quantity in self.quantities:
            quantity.verify()
            quantity_by_id[quantity.quantity_id] = quantity
            if quantity.role in roles_by_mechanism[quantity.mechanism]:
                raise ValueError("internal-body quantity role is duplicated")
            roles_by_mechanism[quantity.mechanism].add(quantity.role)
        parameter_by_id = {}
        for parameter in self.parameters:
            parameter.verify()
            parameter_by_id[parameter.parameter_id] = parameter
        for reference in self.neurochemical_references:
            reference.verify()
        for mount in self.mechanisms:
            mount.verify()
            mounted_quantities = tuple(
                sorted(
                    quantity.quantity_id
                    for quantity in self.quantities
                    if quantity.mechanism is mount.mechanism
                )
            )
            if mount.quantity_ids != mounted_quantities:
                raise ValueError(
                    "internal mechanism quantity membership changed"
                )
            required_roles = frozenset(
                REQUIRED_QUANTITY_ROLES[mount.mechanism]
            )
            if not required_roles.issubset(
                roles_by_mechanism[mount.mechanism]
            ):
                raise ValueError(
                    f"{mount.mechanism.value} lacks required quantity roles"
                )
            supplied_parameters = {
                value.parameter_id
                for value in self.parameters
                if value.mechanism is mount.mechanism
            }
            if mount.availability is MechanismAvailability.AVAILABLE:
                if (
                    not set(mount.required_parameter_ids).issubset(
                        supplied_parameters
                    )
                    or any(
                        quantity_by_id[quantity_id].evolution_kind
                        is QuantityEvolutionKind.UNAVAILABLE
                        for quantity_id in mount.quantity_ids
                    )
                ):
                    raise ValueError(
                        "available mechanism lacks physical parameters "
                        "or modeled quantities"
                    )
            elif any(
                quantity_by_id[quantity_id].evolution_kind
                is not QuantityEvolutionKind.UNAVAILABLE
                for quantity_id in mount.quantity_ids
            ):
                raise ValueError(
                    "unavailable mechanism carries fabricated evolving state"
                )
            if any(
                parameter_by_id[parameter_id].mechanism is not mount.mechanism
                for parameter_id in mount.required_parameter_ids
                if parameter_id in parameter_by_id
            ):
                raise ValueError(
                    "internal mechanism parameter crosses mechanism ownership"
                )
        neurochemical = self.mechanisms[
            expected_mechanisms.index(InternalMechanism.NEUROCHEMICAL)
        ]
        if (
            neurochemical.availability is MechanismAvailability.AVAILABLE
            and not self.neurochemical_references
        ):
            raise ValueError(
                "available neurochemical mechanism lacks exact references"
            )
        payload = self.payload()
        raw_key = _key(authority_key)
        expected_hmac = hmac.new(
            hashlib.sha256(_MANIFEST_DOMAIN + raw_key).digest(),
            _MANIFEST_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            self.authority_hmac_sha256 != expected_hmac
            or self.authority_receipt_sha256
            != _digest(
                {
                    "authority_hmac_sha256": expected_hmac,
                    "payload": payload,
                }
            )
        ):
            raise ValueError("internal-body manifest authority changed")


def create_physical_internal_body_manifest(
    *,
    authority_key: bytes | str,
    manifest_id: str,
    structural_time_unit: str,
    capacity: InternalBodyCapacity,
    mechanisms: Sequence[InternalMechanismMount],
    quantities: Sequence[InternalPhysicalQuantity],
    parameters: Sequence[InternalPhysicalParameter] = (),
    neurochemical_references: Sequence[
        NeurochemicalCompartmentReference
    ] = (),
) -> PhysicalInternalBodyManifest:
    ordered_mechanisms = tuple(
        next(
            value
            for value in mechanisms
            if value.mechanism is mechanism
        )
        for mechanism in InternalMechanism
    )
    if len(tuple(mechanisms)) != len(InternalMechanism):
        raise ValueError("internal-body mechanism manifest is not one-to-one")
    provisional = PhysicalInternalBodyManifest(
        manifest_id=manifest_id,
        structural_time_unit=structural_time_unit,
        capacity=capacity,
        mechanisms=ordered_mechanisms,
        quantities=tuple(
            sorted(quantities, key=lambda value: value.quantity_id)
        ),
        parameters=tuple(
            sorted(parameters, key=lambda value: value.parameter_id)
        ),
        neurochemical_references=tuple(
            sorted(
                neurochemical_references,
                key=lambda value: value.reference_id,
            )
        ),
        authority_hmac_sha256="0" * 64,
        authority_receipt_sha256="0" * 64,
    )
    payload = provisional.payload()
    raw_key = _key(authority_key)
    signature = hmac.new(
        hashlib.sha256(_MANIFEST_DOMAIN + raw_key).digest(),
        _MANIFEST_DOMAIN + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    result = PhysicalInternalBodyManifest(
        **{
            name: getattr(provisional, name)
            for name in provisional.__dataclass_fields__
            if name
            not in {"authority_hmac_sha256", "authority_receipt_sha256"}
        },
        authority_hmac_sha256=signature,
        authority_receipt_sha256=_digest(
            {"authority_hmac_sha256": signature, "payload": payload}
        ),
    )
    result.verify(raw_key)
    return result


def create_embodiment_proprioceptive_internal_body_authority(
    *,
    authority_key: bytes | str,
    world_observation_receipt_sha256: str,
    position_x_mm: Fraction,
    position_y_mm: Fraction,
    position_z_mm: Fraction,
    supported_load_grams: Fraction,
    neurochemical_references: Sequence[
        NeurochemicalCompartmentReference
    ] = (),
) -> "PhysicalInternalBodyStateAuthority":
    """Mount physical quantities and exact external compartment references."""

    _sha(
        world_observation_receipt_sha256,
        "proprioceptive world observation",
    )
    references = tuple(neurochemical_references)
    for reference in references:
        reference.verify()
    initial_by_role = {
        "position_x": _fraction(position_x_mm, "position x"),
        "position_y": _fraction(position_y_mm, "position y"),
        "position_z": _fraction(position_z_mm, "position z"),
        "supported_load": _fraction(
            supported_load_grams,
            "supported load",
        ),
    }
    units = {
        "position_x": "millimetre",
        "position_y": "millimetre",
        "position_z": "millimetre",
        "supported_load": "gram",
    }
    quantities = []
    mechanisms = []
    for mechanism in InternalMechanism:
        available = (
            mechanism is InternalMechanism.PROPRIOCEPTION
            or (
                mechanism is InternalMechanism.NEUROCHEMICAL
                and bool(references)
            )
        )
        quantity_ids = []
        for role in REQUIRED_QUANTITY_ROLES[mechanism]:
            quantity_id = f"quantity:{mechanism.value}:{role}"
            quantity_ids.append(quantity_id)
            if available:
                initial = initial_by_role[role]
                lower = (
                    Fraction(-(1 << 31))
                    if role.startswith("position_")
                    else Fraction(0)
                )
                upper = Fraction(
                    (1 << 31) - 1
                    if role.startswith("position_")
                    else (1 << 63) - 1
                )
                quantities.append(InternalPhysicalQuantity(
                    quantity_id=quantity_id,
                    mechanism=mechanism,
                    role=role,
                    unit=units[role],
                    evolution_kind=QuantityEvolutionKind.LINEAR,
                    lower_bound=lower,
                    upper_bound=upper,
                    initial_value=initial,
                ))
            else:
                quantities.append(InternalPhysicalQuantity(
                    quantity_id=quantity_id,
                    mechanism=mechanism,
                    role=role,
                    unit=f"{mechanism.value}-{role}-unit-unavailable",
                    evolution_kind=QuantityEvolutionKind.UNAVAILABLE,
                    lower_bound=None,
                    upper_bound=None,
                    initial_value=None,
                ))
        mechanisms.append(InternalMechanismMount(
            mechanism=mechanism,
            availability=(
                MechanismAvailability.AVAILABLE
                if available
                else MechanismAvailability.UNAVAILABLE
            ),
            quantity_ids=tuple(sorted(quantity_ids)),
            required_parameter_ids=(),
            unavailable_reason=(
                None
                if available
                else (
                    "current embodiment exposes no authenticated physical "
                    f"{mechanism.value} source"
                )
            ),
        ))
    manifest = create_physical_internal_body_manifest(
        authority_key=authority_key,
        manifest_id="guala-live-physical-internal-body-v1",
        structural_time_unit="exact-causal-interval",
        capacity=InternalBodyCapacity(
            max_quantities=64,
            max_parameters=1,
            max_neurochemical_references=(
                16 if references else 1
            ),
            max_changes_per_transition=4,
            max_conservation_exchanges_per_transition=1,
            max_transitions=1_024,
            max_state_bytes=16 * 1024 * 1024,
        ),
        mechanisms=mechanisms,
        quantities=quantities,
        parameters=(
            InternalPhysicalParameter(
                parameter_id="parameter:proprioception:world-custody",
                mechanism=InternalMechanism.PROPRIOCEPTION,
                unit="authenticated-world-observation",
                value=Fraction(1),
                derivation_receipt_sha256=(
                    world_observation_receipt_sha256
                ),
            ),
        ),
        neurochemical_references=references,
    )
    return PhysicalInternalBodyStateAuthority(
        authority_key=authority_key,
        manifest=manifest,
    )


@dataclass(frozen=True, slots=True)
class InternalQuantityChange:
    quantity_id: str
    delta: Fraction

    def verify(self) -> None:
        _identifier(self.quantity_id, "internal quantity change id")
        _fraction(self.delta, "internal quantity change delta")

    def record(self) -> dict[str, str]:
        self.verify()
        return {
            "delta": _fraction_text(self.delta),
            "quantity_id": self.quantity_id,
        }


@dataclass(frozen=True, slots=True)
class InternalConservationExchange:
    conservation_group_id: str
    net_external_delta: Fraction
    physical_exchange_receipt_sha256: str

    def verify(self) -> None:
        _identifier(
            self.conservation_group_id,
            "internal conservation exchange group",
        )
        _fraction(
            self.net_external_delta,
            "internal conservation external delta",
        )
        _sha(
            self.physical_exchange_receipt_sha256,
            "internal conservation exchange receipt",
        )

    def record(self) -> dict[str, str]:
        self.verify()
        return {
            "conservation_group_id": self.conservation_group_id,
            "net_external_delta": _fraction_text(self.net_external_delta),
            "physical_exchange_receipt_sha256": (
                self.physical_exchange_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class InternalBodyEvolutionRequest:
    source_kind: str
    physical_source_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    expected_state_receipt_sha256: str
    changes: tuple[InternalQuantityChange, ...]
    conservation_exchanges: tuple[InternalConservationExchange, ...] = ()

    def verify(self) -> None:
        _identifier(self.source_kind, "internal-body causal source kind")
        _sha(
            self.physical_source_receipt_sha256,
            "internal-body physical source receipt",
        )
        start = _fraction(
            self.source_time_start,
            "internal-body source time start",
        )
        end = _fraction(
            self.source_time_end,
            "internal-body source time end",
        )
        if end <= start:
            raise ValueError("internal-body causal interval is not positive")
        _sha(
            self.expected_state_receipt_sha256,
            "internal-body expected state receipt",
        )
        if (
            not self.changes
            or self.changes
            != tuple(sorted(self.changes, key=lambda value: value.quantity_id))
            or len({value.quantity_id for value in self.changes})
            != len(self.changes)
        ):
            raise ValueError("internal-body changes are not canonical")
        for change in self.changes:
            change.verify()
        if (
            self.conservation_exchanges
            != tuple(
                sorted(
                    self.conservation_exchanges,
                    key=lambda value: value.conservation_group_id,
                )
            )
            or len(
                {
                    value.conservation_group_id
                    for value in self.conservation_exchanges
                }
            )
            != len(self.conservation_exchanges)
        ):
            raise ValueError(
                "internal-body conservation exchanges are not canonical"
            )
        for exchange in self.conservation_exchanges:
            exchange.verify()


@dataclass(frozen=True, slots=True)
class PhysicalInternalBodyState:
    manifest_receipt_sha256: str
    source_time: Fraction
    sequence: int
    quantity_values: tuple[tuple[str, Fraction | None], ...]
    unavailable_mechanisms: tuple[tuple[str, str], ...]
    neurochemical_reference_receipts: tuple[tuple[str, str], ...]
    prior_state_receipt_sha256: str | None
    causal_source_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "causal_source_receipt_sha256": (
                self.causal_source_receipt_sha256
            ),
            "manifest_receipt_sha256": self.manifest_receipt_sha256,
            "neurochemical_reference_receipts": [
                list(value) for value in self.neurochemical_reference_receipts
            ],
            "prior_state_receipt_sha256": (
                self.prior_state_receipt_sha256
            ),
            "quantity_values": [
                [
                    quantity_id,
                    _fraction_text(value) if value is not None else None,
                ]
                for quantity_id, value in self.quantity_values
            ],
            "schema": STATE_SCHEMA,
            "sequence": self.sequence,
            "source_time": _fraction_text(self.source_time),
            "unavailable_mechanisms": [
                list(value) for value in self.unavailable_mechanisms
            ],
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PhysicalInternalBodyTransition:
    sequence: int
    source_kind: str
    source_time_start: Fraction
    source_time_end: Fraction
    physical_source_receipt_sha256: str
    before_state_receipt_sha256: str
    after_state_receipt_sha256: str
    changes: tuple[InternalQuantityChange, ...]
    conservation_exchanges: tuple[InternalConservationExchange, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "after_state_receipt_sha256": self.after_state_receipt_sha256,
            "before_state_receipt_sha256": self.before_state_receipt_sha256,
            "changes": [value.record() for value in self.changes],
            "conservation_exchanges": [
                value.record() for value in self.conservation_exchanges
            ],
            "physical_source_receipt_sha256": (
                self.physical_source_receipt_sha256
            ),
            "schema": TRANSITION_SCHEMA,
            "sequence": self.sequence,
            "source_kind": self.source_kind,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(slots=True)
class _TransactionPhase:
    value: str


@dataclass(frozen=True, slots=True)
class PreparedInternalBodyEvolution:
    before: PhysicalInternalBodyState
    after: PhysicalInternalBodyState
    transition: PhysicalInternalBodyTransition
    _phase: _TransactionPhase = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class InternalBodyEvolutionUndo:
    _prepared: PreparedInternalBodyEvolution = field(repr=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


class PhysicalInternalBodyStateAuthority:
    """Own exact internal physical state without sensory or cognitive claims."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        manifest: PhysicalInternalBodyManifest,
    ) -> None:
        raw_key = _key(authority_key)
        manifest.verify(raw_key)
        self._manifest = manifest
        self._state_key = hashlib.sha256(_STATE_DOMAIN + raw_key).digest()
        self._transition_key = hashlib.sha256(
            _TRANSITION_DOMAIN + raw_key
        ).digest()
        self._cold_key = hashlib.sha256(_COLD_DOMAIN + raw_key).digest()
        self._lock = threading.RLock()
        self._owner_authority = object()
        self._migration_archive: dict[str, object] | None = None
        self._quantity_by_id = {
            value.quantity_id: value for value in manifest.quantities
        }
        initial_values = tuple(
            (value.quantity_id, value.initial_value)
            for value in manifest.quantities
        )
        self._state = self._build_state(
            source_time=Fraction(0),
            sequence=0,
            quantity_values=initial_values,
            prior_state_receipt_sha256=None,
            causal_source_receipt_sha256=None,
        )
        self._transitions: tuple[PhysicalInternalBodyTransition, ...] = ()
        self.snapshot_encoded()

    @property
    def manifest(self) -> PhysicalInternalBodyManifest:
        return self._manifest

    @property
    def state(self) -> PhysicalInternalBodyState:
        with self._lock:
            return self._state

    @property
    def transitions(self) -> tuple[PhysicalInternalBodyTransition, ...]:
        with self._lock:
            return self._transitions

    def resolve_transition(
        self,
        transition_receipt_sha256: str,
    ) -> PhysicalInternalBodyTransition:
        """Resolve one retained physical evolution by exact receipt."""

        _sha(
            transition_receipt_sha256,
            "resolved internal-body transition",
        )
        with self._lock:
            matches = tuple(
                value
                for value in self._transitions
                if value.authority_receipt_sha256
                == transition_receipt_sha256
            )
            if len(matches) != 1:
                raise ValueError(
                    "internal-body transition is not exactly retained"
                )
            self._verify_transition(matches[0])
            return matches[0]

    def _unavailable_mechanisms(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (value.mechanism.value, value.unavailable_reason)
            for value in self._manifest.mechanisms
            if value.availability is MechanismAvailability.UNAVAILABLE
        )

    def _reference_receipts(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (value.reference_id, value.compartment_receipt_sha256)
            for value in self._manifest.neurochemical_references
        )

    def _build_state(
        self,
        *,
        source_time: Fraction,
        sequence: int,
        quantity_values: tuple[tuple[str, Fraction | None], ...],
        prior_state_receipt_sha256: str | None,
        causal_source_receipt_sha256: str | None,
    ) -> PhysicalInternalBodyState:
        provisional = PhysicalInternalBodyState(
            manifest_receipt_sha256=(
                self._manifest.authority_receipt_sha256
            ),
            source_time=source_time,
            sequence=sequence,
            quantity_values=quantity_values,
            unavailable_mechanisms=self._unavailable_mechanisms(),
            neurochemical_reference_receipts=self._reference_receipts(),
            prior_state_receipt_sha256=prior_state_receipt_sha256,
            causal_source_receipt_sha256=causal_source_receipt_sha256,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = PhysicalInternalBodyState(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name
                not in {"authority_hmac_sha256", "authority_receipt_sha256"}
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest(
                {
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }
            ),
        )
        self._verify_state(result)
        return result

    def _verify_state(self, state: PhysicalInternalBodyState) -> None:
        if not isinstance(state, PhysicalInternalBodyState):
            raise TypeError("internal-body state is not typed")
        if (
            state.manifest_receipt_sha256
            != self._manifest.authority_receipt_sha256
        ):
            raise ValueError("internal-body state changed manifest")
        _fraction(state.source_time, "internal-body state time")
        _nonnegative(state.sequence, "internal-body state sequence")
        expected_ids = tuple(self._quantity_by_id)
        if tuple(value[0] for value in state.quantity_values) != expected_ids:
            raise ValueError("internal-body state quantity topology changed")
        for quantity_id, value in state.quantity_values:
            quantity = self._quantity_by_id[quantity_id]
            if quantity.evolution_kind is QuantityEvolutionKind.UNAVAILABLE:
                if value is not None:
                    raise ValueError(
                        "unavailable internal quantity acquired a value"
                    )
                continue
            if value is None:
                raise ValueError("modeled internal quantity lost its value")
            exact = _fraction(value, "internal-body state quantity")
            assert quantity.lower_bound is not None
            assert quantity.upper_bound is not None
            if quantity.evolution_kind is QuantityEvolutionKind.CYCLIC:
                if not quantity.lower_bound <= exact < quantity.upper_bound:
                    raise ValueError("cyclic internal quantity left its extent")
            elif not quantity.lower_bound <= exact <= quantity.upper_bound:
                raise ValueError("internal quantity left its physical bounds")
        if state.unavailable_mechanisms != self._unavailable_mechanisms():
            raise ValueError("internal-body unavailable mechanisms changed")
        if (
            state.neurochemical_reference_receipts
            != self._reference_receipts()
        ):
            raise ValueError("internal-body neurochemical references changed")
        if state.prior_state_receipt_sha256 is not None:
            _sha(
                state.prior_state_receipt_sha256,
                "internal-body prior state",
            )
        if state.causal_source_receipt_sha256 is not None:
            _sha(
                state.causal_source_receipt_sha256,
                "internal-body causal source",
            )
        expected_hmac = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(state.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            state.authority_hmac_sha256 != expected_hmac
            or state.authority_receipt_sha256
            != _digest(
                {
                    "authority_hmac_sha256": expected_hmac,
                    "payload": state.payload(),
                }
            )
        ):
            raise ValueError("internal-body state authority changed")

    def _build_transition(
        self,
        request: InternalBodyEvolutionRequest,
        after: PhysicalInternalBodyState,
    ) -> PhysicalInternalBodyTransition:
        provisional = PhysicalInternalBodyTransition(
            sequence=after.sequence,
            source_kind=request.source_kind,
            source_time_start=request.source_time_start,
            source_time_end=request.source_time_end,
            physical_source_receipt_sha256=(
                request.physical_source_receipt_sha256
            ),
            before_state_receipt_sha256=(
                request.expected_state_receipt_sha256
            ),
            after_state_receipt_sha256=after.authority_receipt_sha256,
            changes=request.changes,
            conservation_exchanges=request.conservation_exchanges,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._transition_key,
            _TRANSITION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = PhysicalInternalBodyTransition(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name
                not in {"authority_hmac_sha256", "authority_receipt_sha256"}
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest(
                {
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }
            ),
        )
        self._verify_transition(result)
        return result

    def _verify_transition(
        self,
        transition: PhysicalInternalBodyTransition,
    ) -> None:
        if not isinstance(transition, PhysicalInternalBodyTransition):
            raise TypeError("internal-body transition is not typed")
        _positive(transition.sequence, "internal-body transition sequence")
        _identifier(transition.source_kind, "internal-body source kind")
        _fraction(
            transition.source_time_start,
            "internal-body transition start",
        )
        _fraction(
            transition.source_time_end,
            "internal-body transition end",
        )
        if transition.source_time_end <= transition.source_time_start:
            raise ValueError("internal-body transition interval changed")
        for value, label in (
            (
                transition.physical_source_receipt_sha256,
                "internal-body transition source",
            ),
            (
                transition.before_state_receipt_sha256,
                "internal-body transition before state",
            ),
            (
                transition.after_state_receipt_sha256,
                "internal-body transition after state",
            ),
        ):
            _sha(value, label)
        for change in transition.changes:
            change.verify()
        for exchange in transition.conservation_exchanges:
            exchange.verify()
        expected_hmac = hmac.new(
            self._transition_key,
            _TRANSITION_DOMAIN + _canonical(transition.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            transition.authority_hmac_sha256 != expected_hmac
            or transition.authority_receipt_sha256
            != _digest(
                {
                    "authority_hmac_sha256": expected_hmac,
                    "payload": transition.payload(),
                }
            )
        ):
            raise ValueError("internal-body transition authority changed")

    def prepare_evolution(
        self,
        request: InternalBodyEvolutionRequest,
    ) -> PreparedInternalBodyEvolution:
        request.verify()
        with self._lock:
            before = self._state
            capacity = self._manifest.capacity
            if len(self._transitions) >= capacity.max_transitions:
                raise RuntimeError(
                    "internal-body transition capacity is exhausted"
                )
            if len(request.changes) > capacity.max_changes_per_transition:
                raise RuntimeError(
                    "internal-body transition change capacity is exceeded"
                )
            if (
                len(request.conservation_exchanges)
                > capacity.max_conservation_exchanges_per_transition
            ):
                raise RuntimeError(
                    "internal-body conservation exchange capacity is exceeded"
                )
            if (
                request.expected_state_receipt_sha256
                != before.authority_receipt_sha256
                or request.source_time_start != before.source_time
            ):
                raise ValueError(
                    "internal-body evolution crossed current state custody"
                )
            if any(
                value.physical_source_receipt_sha256
                == request.physical_source_receipt_sha256
                for value in self._transitions
            ):
                raise ValueError(
                    "internal-body physical source receipt was replayed"
                )
            values = dict(before.quantity_values)
            deltas: dict[str, Fraction] = {}
            for change in request.changes:
                quantity = self._quantity_by_id.get(change.quantity_id)
                if quantity is None:
                    raise ValueError(
                        "internal-body change names an unmounted quantity"
                    )
                if (
                    quantity.evolution_kind
                    is QuantityEvolutionKind.UNAVAILABLE
                ):
                    raise ValueError(
                        "unavailable internal quantity cannot evolve"
                    )
                current = values[change.quantity_id]
                assert current is not None
                candidate = current + change.delta
                if quantity.evolution_kind is QuantityEvolutionKind.CYCLIC:
                    assert quantity.cyclic_modulus is not None
                    candidate %= quantity.cyclic_modulus
                values[change.quantity_id] = candidate
                deltas[change.quantity_id] = change.delta
            exchanges = {
                value.conservation_group_id: value
                for value in request.conservation_exchanges
            }
            mounted_groups = {
                value.conservation_group_id
                for value in self._manifest.quantities
                if value.conservation_group_id is not None
            }
            if not set(exchanges).issubset(mounted_groups):
                raise ValueError(
                    "internal-body exchange names an unmounted group"
                )
            for group_id in sorted(mounted_groups):
                group_delta = sum(
                    (
                        deltas.get(quantity.quantity_id, Fraction(0))
                        for quantity in self._manifest.quantities
                        if quantity.conservation_group_id == group_id
                    ),
                    Fraction(0),
                )
                external = exchanges.get(group_id)
                expected = (
                    external.net_external_delta
                    if external is not None
                    else Fraction(0)
                )
                if group_delta != expected:
                    raise ValueError(
                        f"internal-body conservation failed for {group_id}"
                    )
            after = self._build_state(
                source_time=request.source_time_end,
                sequence=before.sequence + 1,
                quantity_values=tuple(
                    (quantity_id, values[quantity_id])
                    for quantity_id in self._quantity_by_id
                ),
                prior_state_receipt_sha256=(
                    before.authority_receipt_sha256
                ),
                causal_source_receipt_sha256=(
                    request.physical_source_receipt_sha256
                ),
            )
            transition = self._build_transition(request, after)
            prepared = PreparedInternalBodyEvolution(
                before=before,
                after=after,
                transition=transition,
                _phase=_TransactionPhase("prepared"),
                _owner_authority=self._owner_authority,
                _construction_authority=_PREPARED_AUTHORITY,
            )
            self._encoded(
                after,
                self._transitions + (transition,),
            )
            return prepared

    def _verify_prepared(
        self,
        prepared: PreparedInternalBodyEvolution,
        *,
        phase: str,
    ) -> None:
        if (
            not isinstance(prepared, PreparedInternalBodyEvolution)
            or prepared._construction_authority is not _PREPARED_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
            or prepared._phase.value != phase
        ):
            raise ValueError(
                "internal-body prepared evolution authority changed"
            )
        self._verify_state(prepared.before)
        self._verify_state(prepared.after)
        self._verify_transition(prepared.transition)
        if (
            prepared.after.prior_state_receipt_sha256
            != prepared.before.authority_receipt_sha256
            or prepared.transition.before_state_receipt_sha256
            != prepared.before.authority_receipt_sha256
            or prepared.transition.after_state_receipt_sha256
            != prepared.after.authority_receipt_sha256
        ):
            raise ValueError("internal-body prepared lineage changed")

    def commit_prepared(
        self,
        prepared: PreparedInternalBodyEvolution,
    ) -> InternalBodyEvolutionUndo:
        with self._lock:
            self._verify_prepared(prepared, phase="prepared")
            if self._state != prepared.before:
                raise ValueError(
                    "internal-body prepared evolution is stale"
                )
            if (
                len(self._transitions)
                >= self._manifest.capacity.max_transitions
            ):
                raise RuntimeError(
                    "internal-body transition capacity is exhausted"
                )
            self._state = prepared.after
            self._transitions = self._transitions + (
                prepared.transition,
            )
            try:
                self.snapshot_encoded()
            except BaseException:
                self._transitions = self._transitions[:-1]
                self._state = prepared.before
                raise
            prepared._phase.value = "committed"
            return InternalBodyEvolutionUndo(
                _prepared=prepared,
                _owner_authority=self._owner_authority,
                _construction_authority=_UNDO_AUTHORITY,
            )

    def discard_prepared(
        self,
        prepared: PreparedInternalBodyEvolution,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared, phase="prepared")
            prepared._phase.value = "discarded"

    def rollback_committed(
        self,
        undo: InternalBodyEvolutionUndo,
    ) -> None:
        with self._lock:
            if (
                not isinstance(undo, InternalBodyEvolutionUndo)
                or undo._construction_authority is not _UNDO_AUTHORITY
                or undo._owner_authority is not self._owner_authority
            ):
                raise ValueError("internal-body rollback authority changed")
            prepared = undo._prepared
            self._verify_prepared(prepared, phase="committed")
            if (
                self._state != prepared.after
                or not self._transitions
                or self._transitions[-1] != prepared.transition
            ):
                raise ValueError("internal-body rollback is not the live tail")
            self._state = prepared.before
            self._transitions = self._transitions[:-1]
            prepared._phase.value = "rolled_back"
            self.snapshot_encoded()

    def _encoded(
        self,
        state: PhysicalInternalBodyState,
        transitions: tuple[PhysicalInternalBodyTransition, ...],
    ) -> bytes:
        body = {
            "manifest_receipt_sha256": (
                self._manifest.authority_receipt_sha256
            ),
            "migration_archive": self._migration_archive,
            "schema": COLD_SCHEMA,
            "state": state.record(),
            "transitions": [value.record() for value in transitions],
        }
        encoded = _canonical(
            {
                "body": body,
                "cold_hmac_sha256": hmac.new(
                    self._cold_key,
                    _COLD_DOMAIN + _canonical(body),
                    hashlib.sha256,
                ).hexdigest(),
                "schema": COLD_SCHEMA,
            }
        )
        if len(encoded) > self._manifest.capacity.max_state_bytes:
            raise RuntimeError(
                "internal-body cold state exceeds byte capacity"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._state, self._transitions)

    @staticmethod
    def _state_from_record(value: object) -> PhysicalInternalBodyState:
        if not isinstance(value, dict) or set(value) != {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "causal_source_receipt_sha256",
            "manifest_receipt_sha256",
            "neurochemical_reference_receipts",
            "prior_state_receipt_sha256",
            "quantity_values",
            "schema",
            "sequence",
            "source_time",
            "unavailable_mechanisms",
        }:
            raise ValueError("internal-body cold state shape changed")
        if value["schema"] != STATE_SCHEMA:
            raise ValueError("internal-body state schema changed")
        quantities = value["quantity_values"]
        unavailable = value["unavailable_mechanisms"]
        references = value["neurochemical_reference_receipts"]
        if not all(
            isinstance(collection, list)
            for collection in (quantities, unavailable, references)
        ):
            raise ValueError("internal-body cold state collections changed")
        return PhysicalInternalBodyState(
            manifest_receipt_sha256=value["manifest_receipt_sha256"],
            source_time=_fraction_from_text(
                value["source_time"],
                "internal-body cold state time",
            ),
            sequence=value["sequence"],
            quantity_values=tuple(
                (
                    item[0],
                    _fraction_from_text(
                        item[1],
                        "internal-body cold quantity",
                    )
                    if item[1] is not None
                    else None,
                )
                for item in quantities
                if isinstance(item, list) and len(item) == 2
            ),
            unavailable_mechanisms=tuple(
                tuple(item)
                for item in unavailable
                if isinstance(item, list) and len(item) == 2
            ),
            neurochemical_reference_receipts=tuple(
                tuple(item)
                for item in references
                if isinstance(item, list) and len(item) == 2
            ),
            prior_state_receipt_sha256=(
                value["prior_state_receipt_sha256"]
            ),
            causal_source_receipt_sha256=(
                value["causal_source_receipt_sha256"]
            ),
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=value["authority_receipt_sha256"],
        )

    @staticmethod
    def _transition_from_record(
        value: object,
    ) -> PhysicalInternalBodyTransition:
        if not isinstance(value, dict) or set(value) != {
            "after_state_receipt_sha256",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "before_state_receipt_sha256",
            "changes",
            "conservation_exchanges",
            "physical_source_receipt_sha256",
            "schema",
            "sequence",
            "source_kind",
            "source_time_end",
            "source_time_start",
        }:
            raise ValueError("internal-body cold transition shape changed")
        if value["schema"] != TRANSITION_SCHEMA:
            raise ValueError("internal-body transition schema changed")
        changes = value["changes"]
        exchanges = value["conservation_exchanges"]
        if not isinstance(changes, list) or not isinstance(exchanges, list):
            raise ValueError(
                "internal-body cold transition collections changed"
            )
        return PhysicalInternalBodyTransition(
            sequence=value["sequence"],
            source_kind=value["source_kind"],
            source_time_start=_fraction_from_text(
                value["source_time_start"],
                "internal-body cold transition start",
            ),
            source_time_end=_fraction_from_text(
                value["source_time_end"],
                "internal-body cold transition end",
            ),
            physical_source_receipt_sha256=(
                value["physical_source_receipt_sha256"]
            ),
            before_state_receipt_sha256=(
                value["before_state_receipt_sha256"]
            ),
            after_state_receipt_sha256=(
                value["after_state_receipt_sha256"]
            ),
            changes=tuple(
                InternalQuantityChange(
                    quantity_id=item["quantity_id"],
                    delta=_fraction_from_text(
                        item["delta"],
                        "internal-body cold change",
                    ),
                )
                for item in changes
                if isinstance(item, dict)
                and set(item) == {"delta", "quantity_id"}
            ),
            conservation_exchanges=tuple(
                InternalConservationExchange(
                    conservation_group_id=item[
                        "conservation_group_id"
                    ],
                    net_external_delta=_fraction_from_text(
                        item["net_external_delta"],
                        "internal-body cold exchange",
                    ),
                    physical_exchange_receipt_sha256=item[
                        "physical_exchange_receipt_sha256"
                    ],
                )
                for item in exchanges
                if isinstance(item, dict)
                and set(item)
                == {
                    "conservation_group_id",
                    "net_external_delta",
                    "physical_exchange_receipt_sha256",
                }
            ),
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=value["authority_receipt_sha256"],
        )

    @staticmethod
    def _verify_exact_neurochemical_manifest_superset(
        prior: PhysicalInternalBodyManifest,
        current: PhysicalInternalBodyManifest,
    ) -> None:
        if (
            prior.manifest_id != current.manifest_id
            or prior.structural_time_unit
            != current.structural_time_unit
            or prior.quantities != current.quantities
            or prior.parameters != current.parameters
            or prior.neurochemical_references
        ):
            raise ValueError(
                "internal-body migration changed physical contracts"
            )
        expected_reference_ids = {
            "reference:component:ae-recovery:body",
            "reference:component:ae-recovery:sink",
            "reference:component:ae-recovery:source",
            *{
                f"reference:component:ae-excitation:{sense}:{position}"
                for sense in (
                    "body",
                    "sight",
                    "smell",
                    "sound",
                    "taste",
                    "touch",
                )
                for position in ("a", "b")
            },
        }
        if (
            len(current.neurochemical_references) != 15
            or {
                value.reference_id
                for value in current.neurochemical_references
            }
            != expected_reference_ids
        ):
            raise ValueError(
                "internal-body migration lacks exact carrier references"
            )
        for reference in current.neurochemical_references:
            component_id = reference.reference_id.removeprefix(
                "reference:"
            )
            is_recovery = component_id.startswith(
                "component:ae-recovery:"
            )
            expected_node = (
                "node:ae-recovery-"
                + component_id.rsplit(":", 1)[-1]
                if is_recovery
                else component_id.replace("component:", "node:", 1)
            )
            if (
                reference.node_id != expected_node
                or reference.species_id
                != (
                    "species:ae-recovery-carrier"
                    if is_recovery
                    else "species:ae-excitation-carrier"
                )
                or reference.quantity_unit
                != (
                    "ae-recovery-quantum"
                    if is_recovery
                    else "ae-excitation-quantum"
                )
            ):
                raise ValueError(
                    "internal-body migration crossed a carrier compartment"
                )
        if len({
            value.manifest_receipt_sha256
            for value in current.neurochemical_references
        }) != 1:
            raise ValueError(
                "internal-body migration crossed flow manifests"
            )
        prior_capacity = prior.capacity.record()
        current_capacity = current.capacity.record()
        expected_capacity = dict(prior_capacity)
        expected_capacity["max_neurochemical_references"] = 16
        if (
            prior_capacity["max_neurochemical_references"] != 1
            or current_capacity != expected_capacity
        ):
            raise ValueError(
                "internal-body migration changed bounded capacity"
            )
        prior_by_mechanism = {
            value.mechanism: value for value in prior.mechanisms
        }
        current_by_mechanism = {
            value.mechanism: value for value in current.mechanisms
        }
        for mechanism in InternalMechanism:
            old = prior_by_mechanism[mechanism]
            new = current_by_mechanism[mechanism]
            if mechanism is not InternalMechanism.NEUROCHEMICAL:
                if old != new:
                    raise ValueError(
                        "internal-body migration changed a body mechanism"
                    )
                continue
            expected = InternalMechanismMount(
                mechanism=old.mechanism,
                availability=MechanismAvailability.AVAILABLE,
                quantity_ids=old.quantity_ids,
                required_parameter_ids=old.required_parameter_ids,
                unavailable_reason=None,
            )
            if (
                old.availability is not MechanismAvailability.UNAVAILABLE
                or new != expected
            ):
                raise ValueError(
                    "internal-body migration changed neurochemical law"
                )

    def _verify_migration_archive(self) -> None:
        archive = self._migration_archive
        if archive is None:
            return
        if (
            not isinstance(archive, dict)
            or set(archive)
            != {
                "prior_cold_hmac_sha256",
                "prior_manifest",
                "prior_state",
                "prior_transitions",
                "schema",
            }
            or archive.get("schema")
            != (
                "guala.physical_internal_body."
                "manifest_migration_archive.v1"
            )
            or not isinstance(archive.get("prior_manifest"), dict)
            or not isinstance(archive.get("prior_state"), dict)
            or not isinstance(archive.get("prior_transitions"), list)
        ):
            raise ValueError(
                "internal-body manifest migration archive changed"
            )
        _sha(
            archive["prior_cold_hmac_sha256"],
            "internal-body archived cold authority",
        )
        if (
            archive["prior_manifest"].get(
                "authority_receipt_sha256"
            )
            != archive["prior_state"].get(
                "manifest_receipt_sha256"
            )
        ):
            raise ValueError(
                "internal-body migration archive crossed manifests"
            )

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        manifest: PhysicalInternalBodyManifest,
        encoded: bytes,
        prior_manifest_for_migration: (
            PhysicalInternalBodyManifest | None
        ) = None,
    ) -> "PhysicalInternalBodyStateAuthority":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("internal-body cold state is absent")
        if len(encoded) > manifest.capacity.max_state_bytes:
            raise ValueError("internal-body cold state exceeds byte capacity")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("internal-body cold state is unreadable") from error
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {"body", "cold_hmac_sha256", "schema"}
            or envelope["schema"] != COLD_SCHEMA
            or not isinstance(envelope["body"], dict)
        ):
            raise ValueError("internal-body cold envelope changed")
        raw_key = _key(authority_key)
        cold_key = hashlib.sha256(_COLD_DOMAIN + raw_key).digest()
        expected_hmac = hmac.new(
            cold_key,
            _COLD_DOMAIN + _canonical(envelope["body"]),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope["cold_hmac_sha256"],
            expected_hmac,
        ):
            raise ValueError("internal-body cold state authentication failed")
        body = envelope["body"]
        if (
            frozenset(body)
            not in {
                frozenset({
                    "manifest_receipt_sha256",
                    "schema",
                    "state",
                    "transitions",
                }),
                frozenset({
                    "manifest_receipt_sha256",
                    "migration_archive",
                    "schema",
                    "state",
                    "transitions",
                }),
            }
            or body["schema"] != COLD_SCHEMA
            or not isinstance(body["transitions"], list)
        ):
            raise ValueError("internal-body cold state changed manifest")
        manifest_changed = (
            body["manifest_receipt_sha256"]
            != manifest.authority_receipt_sha256
        )
        if manifest_changed:
            if prior_manifest_for_migration is None:
                raise ValueError(
                    "internal-body migration lacks exact prior manifest"
                )
            prior_manifest_for_migration.verify(raw_key)
            if (
                prior_manifest_for_migration.authority_receipt_sha256
                != body["manifest_receipt_sha256"]
            ):
                raise ValueError(
                    "internal-body prior manifest receipt disagrees"
                )
            cls._verify_exact_neurochemical_manifest_superset(
                prior_manifest_for_migration,
                manifest,
            )
        elif prior_manifest_for_migration is not None:
            raise ValueError(
                "internal-body prior manifest supplied without migration"
            )
        result = cls(authority_key=raw_key, manifest=manifest)
        state = cls._state_from_record(body["state"])
        transitions = tuple(
            cls._transition_from_record(value)
            for value in body["transitions"]
        )
        if manifest_changed:
            expected_state_hmac = hmac.new(
                result._state_key,
                _STATE_DOMAIN + _canonical(state.payload()),
                hashlib.sha256,
            ).hexdigest()
            if (
                state.authority_hmac_sha256 != expected_state_hmac
                or state.authority_receipt_sha256
                != _digest({
                    "authority_hmac_sha256": expected_state_hmac,
                    "payload": state.payload(),
                })
            ):
                raise ValueError(
                    "legacy internal-body state authority changed"
                )
            prior = None
            for index, transition in enumerate(transitions, start=1):
                result._verify_transition(transition)
                if (
                    transition.sequence != index
                    or (
                        prior is not None
                        and transition.before_state_receipt_sha256
                        != prior.after_state_receipt_sha256
                    )
                ):
                    raise ValueError(
                        "legacy internal-body transition lineage changed"
                    )
                prior = transition
            if transitions:
                tail = transitions[-1]
                if (
                    state.sequence != len(transitions)
                    or state.authority_receipt_sha256
                    != tail.after_state_receipt_sha256
                    or state.source_time != tail.source_time_end
                ):
                    raise ValueError(
                        "legacy internal-body state lost history tail"
                    )
            elif state.sequence != 0:
                raise ValueError(
                    "legacy internal-body genesis sequence changed"
                )
            result._migration_archive = {
                "prior_cold_hmac_sha256": envelope[
                    "cold_hmac_sha256"
                ],
                "prior_manifest": (
                    prior_manifest_for_migration.record()
                ),
                "prior_state": state.record(),
                "prior_transitions": [
                    value.record() for value in transitions
                ],
                "schema": (
                    "guala.physical_internal_body."
                    "manifest_migration_archive.v1"
                ),
            }
            result._state = result._build_state(
                source_time=state.source_time,
                sequence=0,
                quantity_values=state.quantity_values,
                prior_state_receipt_sha256=None,
                causal_source_receipt_sha256=(
                    state.authority_receipt_sha256
                ),
            )
            result._transitions = ()
            result.snapshot_encoded()
            return result
        result._migration_archive = body.get("migration_archive")
        result._verify_migration_archive()
        result._verify_state(state)
        if len(transitions) > manifest.capacity.max_transitions:
            raise ValueError("internal-body cold history exceeds capacity")
        prior = None
        for index, transition in enumerate(transitions, start=1):
            result._verify_transition(transition)
            if (
                transition.sequence != index
                or (
                    prior is not None
                    and transition.before_state_receipt_sha256
                    != prior.after_state_receipt_sha256
                )
            ):
                raise ValueError(
                    "internal-body cold transition lineage changed"
                )
            prior = transition
        if transitions:
            tail = transitions[-1]
            if (
                state.sequence != len(transitions)
                or state.authority_receipt_sha256
                != tail.after_state_receipt_sha256
                or state.source_time != tail.source_time_end
            ):
                raise ValueError("internal-body cold state lost history tail")
        elif state.sequence != 0:
            raise ValueError("internal-body cold genesis sequence changed")
        result._state = state
        result._transitions = transitions
        if result.snapshot_encoded() != encoded:
            raise ValueError("internal-body cold state is not canonical")
        return result

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "cold_restorable": True,
                "cognition_authority": False,
                "authenticated_manifest_migration_source_receipt_sha256": (
                    self._state.causal_source_receipt_sha256
                    if (
                        self._state.sequence == 0
                        and self._state.prior_state_receipt_sha256 is None
                    )
                    else None
                ),
                "full_independent_quantities": True,
                "manifest_migration_archive_present": (
                    self._migration_archive is not None
                ),
                "manifest_migration_archived_transitions": (
                    0
                    if self._migration_archive is None
                    else len(
                        self._migration_archive["prior_transitions"]
                    )
                ),
                "manifest_receipt_sha256": (
                    self._manifest.authority_receipt_sha256
                ),
                "modeled_quantities": sum(
                    value is not None
                    for _quantity_id, value in self._state.quantity_values
                ),
                "neurochemical_reference_count": len(
                    self._manifest.neurochemical_references
                ),
                "reduced_body_lane": False,
                "schema": "guala.physical_internal_body.status.v1",
                "sensory_lane_mapping": None,
                "sequence": self._state.sequence,
                "state_bytes": len(self.snapshot_encoded()),
                "state_capacity_bytes": (
                    self._manifest.capacity.max_state_bytes
                ),
                "transition_capacity": (
                    self._manifest.capacity.max_transitions
                ),
                "transitions": len(self._transitions),
                "unavailable_mechanisms": [
                    list(value)
                    for value in self._state.unavailable_mechanisms
                ],
            }


__all__ = (
    "COLD_SCHEMA",
    "InternalBodyCapacity",
    "InternalBodyEvolutionRequest",
    "InternalBodyEvolutionUndo",
    "InternalConservationExchange",
    "InternalMechanism",
    "InternalMechanismMount",
    "InternalPhysicalParameter",
    "InternalPhysicalQuantity",
    "InternalQuantityChange",
    "MechanismAvailability",
    "NeurochemicalCompartmentReference",
    "PhysicalInternalBodyManifest",
    "PhysicalInternalBodyState",
    "PhysicalInternalBodyStateAuthority",
    "PhysicalInternalBodyTransition",
    "PreparedInternalBodyEvolution",
    "QuantityEvolutionKind",
    "REQUIRED_QUANTITY_ROLES",
    "create_physical_internal_body_manifest",
    "create_embodiment_proprioceptive_internal_body_authority",
)
