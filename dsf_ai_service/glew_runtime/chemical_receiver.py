"""Certified flux-coupled synthetic chemical receiver for clean GLEW senses.

One independently retained native port carries the conservative topology

    R --native activation--> A
    A --deactivation-------> R
    A --desensitization----> D
    D --recovery-----------> R

The R-to-A authority is a susceptibility, not a free-standing transition
rate.  Its dimension is inverse native-signal-unit per mounted local-time
unit.  For one physical boundary interval the exact activation propensity is

    alpha = susceptibility * abs(signed_native_boundary_flux)

The signed flux remains a separate receipted quantity for L0.  Chemistry uses
only its exact nonnegative magnitude, so equal positive and negative
magnitudes have equal activation while their signs remain distinct.  Exact
zero flux produces exact zero R-to-A activation without a branch, threshold,
clamp, or fallback.

Deactivation, desensitization, and recovery remain independently mounted
inverse-local-time rates.  For the column state ``x = (R, A, D)`` the receiver
evolves by

    x(t + dt) = exp(G(alpha) * dt) x(t)

where ``G`` is a Metzler matrix with exact zero column sums.  Pinned Arb
arithmetic produces outward component enclosures.  Those enclosures retain
the exact affine constraint ``R + A + D = R_total``.  No midpoint is selected,
no enclosure is clamped or renormalized, and no production coefficient is
chosen by this execution engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Sequence

from .certified_backend import (
    FLINT_VERSION,
    PYTHON_FLINT_VERSION,
    PYTHON_FLINT_WHEEL_SHA256,
    CertifiedBall,
    arb_fraction,
    canonical_ball,
    load_pinned_flint,
)
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)


CHEMICAL_RECEIVER_OPERATOR_ID = (
    "glew.synthetic_post_native_flux_coupled_receiver_exponential.v2"
)
CHEMICAL_AFFINE_CONSTRAINT_ID = "R_plus_A_plus_D_equals_R_total.v1"
CHEMICAL_BACKEND_SOLVER_ID = "pinned_arb_exact_time_matrix_exponential.v1"


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "chemical receipt value")
    return f"{value.numerator}/{value.denominator}"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _ball_payload(value: CertifiedBall) -> dict[str, object]:
    if not isinstance(value, CertifiedBall):
        raise ReceiptError("chemical state contains a non-certified component")
    return {
        "flint_version": value.flint_version,
        "lower_exponent": value.lower_exponent,
        "lower_mantissa": value.lower_mantissa,
        "python_flint_version": value.python_flint_version,
        "upper_exponent": value.upper_exponent,
        "upper_mantissa": value.upper_mantissa,
        "wheel_sha256": value.wheel_sha256,
        "working_precision_bits": value.working_precision_bits,
    }


def _ball_bounds(value: CertifiedBall) -> tuple[Fraction, Fraction]:
    if not isinstance(value, CertifiedBall):
        raise ReceiptError("chemical state contains a non-certified component")
    if (
        value.python_flint_version != PYTHON_FLINT_VERSION
        or value.flint_version != FLINT_VERSION
        or value.wheel_sha256 != PYTHON_FLINT_WHEEL_SHA256
    ):
        raise ReceiptError("chemical state carries a different backend authority")
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


def _dyadic_pair(value: Fraction) -> tuple[int, int]:
    denominator = value.denominator
    if denominator & (denominator - 1):
        raise ReceiptError("certified chemical endpoint is not dyadic")
    return value.numerator, -(denominator.bit_length() - 1)


def _arb_from_ball(flint, value: CertifiedBall):
    """Reconstruct the complete closed interval, never a selected midpoint."""

    lower, upper = _ball_bounds(value)
    center = (lower + upper) / 2
    radius = (upper - lower) / 2
    return flint.arb(_dyadic_pair(center), _dyadic_pair(radius))


def _verify_local_receipt(
    *,
    receipt_registry: ReceiptRegistry,
    digest: str,
    payload: bytes,
    expected: bytes,
    field_name: str,
) -> None:
    sha256_digest(digest, field_name)
    if not isinstance(payload, bytes) or not payload:
        raise ReceiptError(f"{field_name} requires nonempty canonical bytes")
    if receipt_sha256(payload) != digest:
        raise ReceiptError(f"{field_name} payload does not match its digest")
    mounted = receipt_registry.resolve(digest, field_name)
    if mounted != payload or payload != expected:
        raise ReceiptError(f"{field_name} differs from its mounted receipt")


class ReceiverTransition(str, Enum):
    NATIVE_ACTIVATION = "R_to_A_native_activation"
    DEACTIVATION = "A_to_R_deactivation"
    DESENSITIZATION = "A_to_D_desensitization"
    RECOVERY = "D_to_R_recovery"


TRANSITION_ORDER = (
    ReceiverTransition.NATIVE_ACTIVATION,
    ReceiverTransition.DEACTIVATION,
    ReceiverTransition.DESENSITIZATION,
    ReceiverTransition.RECOVERY,
)
KINETIC_RATE_TRANSITIONS = TRANSITION_ORDER[1:]


def chemical_time_unit_authority_receipt_payload(
    *,
    authority_id: str,
    time_unit_id: str,
    seconds_per_unit: Fraction,
    derivation_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "derivation_receipt_sha256": derivation_receipt_sha256,
            "dimension": "physical_time",
            "schema": "glew.chemical_receiver.time_unit_authority.v1",
            "seconds_per_unit": _fraction_text(seconds_per_unit),
            "time_unit_id": time_unit_id,
        }
    )


@dataclass(frozen=True, slots=True)
class ChemicalTimeUnitAuthority:
    authority_id: str
    time_unit_id: str
    seconds_per_unit: Fraction
    derivation_receipt_sha256: str
    authority_receipt_sha256: str

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        require_identifier(self.authority_id, "chemical time authority_id")
        require_identifier(self.time_unit_id, "chemical time_unit_id")
        require_fraction(self.seconds_per_unit, "chemical seconds_per_unit")
        if self.seconds_per_unit <= 0:
            raise ReceiptError("chemical time unit must have positive physical duration")
        receipt_registry.resolve(
            self.derivation_receipt_sha256,
            "chemical time-unit derivation receipt",
        )
        expected = chemical_time_unit_authority_receipt_payload(
            authority_id=self.authority_id,
            time_unit_id=self.time_unit_id,
            seconds_per_unit=self.seconds_per_unit,
            derivation_receipt_sha256=self.derivation_receipt_sha256,
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "chemical time-unit authority receipt",
        )
        if mounted != expected:
            raise ReceiptError("chemical time unit differs from its mounted receipt")


def chemical_backend_authority_receipt_payload(
    *, authority_id: str, working_precision_bits: int
) -> bytes:
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "backend": {
                "flint": FLINT_VERSION,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
                "working_precision_bits": working_precision_bits,
            },
            "operator": CHEMICAL_RECEIVER_OPERATOR_ID,
            "schema": "glew.chemical_receiver.backend_authority.v2",
            "solver": CHEMICAL_BACKEND_SOLVER_ID,
        }
    )


@dataclass(frozen=True, slots=True)
class ChemicalBackendAuthority:
    authority_id: str
    working_precision_bits: int
    authority_receipt_sha256: str

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        require_identifier(self.authority_id, "chemical backend authority_id")
        if (
            isinstance(self.working_precision_bits, bool)
            or not isinstance(self.working_precision_bits, int)
            or self.working_precision_bits <= 0
        ):
            raise ReceiptError(
                "chemical backend working precision must be an explicit positive integer"
            )
        expected = chemical_backend_authority_receipt_payload(
            authority_id=self.authority_id,
            working_precision_bits=self.working_precision_bits,
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "chemical backend authority receipt",
        )
        if mounted != expected:
            raise ReceiptError("chemical backend differs from its mounted receipt")


def activation_susceptibility_authority_receipt_payload(
    *,
    susceptibility_id: str,
    port_id: str,
    susceptibility_per_native_signal_unit_per_time_unit: Fraction,
    native_signal_unit: str,
    native_signal_unit_authority_receipt_sha256: str,
    time_unit_authority_receipt_sha256: str,
    derivation_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "derivation_receipt_sha256": derivation_receipt_sha256,
            "dimension": {
                "mounted_time_unit_exponent": -1,
                "native_signal_unit_exponent": -1,
                "result_after_native_signal_multiplication": (
                    "inverse_mounted_time_unit"
                ),
            },
            "native_signal_unit": native_signal_unit,
            "native_signal_unit_authority_receipt_sha256": (
                native_signal_unit_authority_receipt_sha256
            ),
            "port_id": port_id,
            "schema": (
                "glew.chemical_receiver.activation_susceptibility_authority.v1"
            ),
            "susceptibility_id": susceptibility_id,
            "susceptibility_per_native_signal_unit_per_time_unit": _fraction_text(
                susceptibility_per_native_signal_unit_per_time_unit
            ),
            "time_unit_authority_receipt_sha256": (
                time_unit_authority_receipt_sha256
            ),
            "transition": ReceiverTransition.NATIVE_ACTIVATION.value,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedActivationSusceptibility:
    susceptibility_id: str
    port_id: str
    susceptibility_per_native_signal_unit_per_time_unit: Fraction
    native_signal_unit: str
    native_signal_unit_authority_receipt_sha256: str
    time_unit_authority_receipt_sha256: str
    derivation_receipt_sha256: str
    authority_receipt_sha256: str

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        require_identifier(
            self.susceptibility_id,
            "chemical activation susceptibility_id",
        )
        require_identifier(self.port_id, "chemical susceptibility port_id")
        require_fraction(
            self.susceptibility_per_native_signal_unit_per_time_unit,
            "chemical activation susceptibility",
        )
        if self.susceptibility_per_native_signal_unit_per_time_unit < 0:
            raise ReceiptError("chemical activation susceptibility cannot be negative")
        require_identifier(self.native_signal_unit, "chemical native signal unit")
        receipt_registry.resolve(
            self.native_signal_unit_authority_receipt_sha256,
            "chemical susceptibility native signal-unit authority receipt",
        )
        sha256_digest(
            self.time_unit_authority_receipt_sha256,
            "chemical susceptibility time-unit authority receipt",
        )
        receipt_registry.resolve(
            self.derivation_receipt_sha256,
            "chemical activation susceptibility derivation receipt",
        )
        expected = activation_susceptibility_authority_receipt_payload(
            susceptibility_id=self.susceptibility_id,
            port_id=self.port_id,
            susceptibility_per_native_signal_unit_per_time_unit=(
                self.susceptibility_per_native_signal_unit_per_time_unit
            ),
            native_signal_unit=self.native_signal_unit,
            native_signal_unit_authority_receipt_sha256=(
                self.native_signal_unit_authority_receipt_sha256
            ),
            time_unit_authority_receipt_sha256=(
                self.time_unit_authority_receipt_sha256
            ),
            derivation_receipt_sha256=self.derivation_receipt_sha256,
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "chemical activation susceptibility authority receipt",
        )
        if mounted != expected:
            raise ReceiptError(
                "chemical activation susceptibility differs from its mounted receipt"
            )


def chemical_rate_authority_receipt_payload(
    *,
    rate_id: str,
    port_id: str,
    transition: ReceiverTransition,
    rate_per_time_unit: Fraction,
    time_unit_authority_receipt_sha256: str,
    derivation_receipt_sha256: str,
) -> bytes:
    transition_value = (
        transition.value if isinstance(transition, ReceiverTransition) else str(transition)
    )
    return _canonical_bytes(
        {
            "derivation_receipt_sha256": derivation_receipt_sha256,
            "dimension": "inverse_mounted_time_unit",
            "port_id": port_id,
            "rate_id": rate_id,
            "rate_per_time_unit": _fraction_text(rate_per_time_unit),
            "schema": "glew.chemical_receiver.transition_rate_authority.v2",
            "time_unit_authority_receipt_sha256": (
                time_unit_authority_receipt_sha256
            ),
            "transition": transition_value,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedChemicalRate:
    rate_id: str
    port_id: str
    transition: ReceiverTransition
    rate_per_time_unit: Fraction
    time_unit_authority_receipt_sha256: str
    derivation_receipt_sha256: str
    authority_receipt_sha256: str

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        require_identifier(self.rate_id, "chemical rate_id")
        require_identifier(self.port_id, "chemical rate port_id")
        if self.transition not in KINETIC_RATE_TRANSITIONS:
            raise ReceiptError(
                "R-to-A requires susceptibility; it cannot be mounted as a rate"
            )
        require_fraction(self.rate_per_time_unit, "chemical transition rate")
        if self.rate_per_time_unit < 0:
            raise ReceiptError("chemical transition rate cannot be negative")
        sha256_digest(
            self.time_unit_authority_receipt_sha256,
            "chemical rate time-unit authority receipt",
        )
        receipt_registry.resolve(
            self.derivation_receipt_sha256,
            "chemical rate derivation receipt",
        )
        expected = chemical_rate_authority_receipt_payload(
            rate_id=self.rate_id,
            port_id=self.port_id,
            transition=self.transition,
            rate_per_time_unit=self.rate_per_time_unit,
            time_unit_authority_receipt_sha256=(
                self.time_unit_authority_receipt_sha256
            ),
            derivation_receipt_sha256=self.derivation_receipt_sha256,
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "chemical rate authority receipt",
        )
        if mounted != expected:
            raise ReceiptError("chemical rate differs from its mounted receipt")


def native_activation_interval_receipt_payload(
    *,
    interval_id: str,
    port_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    time_unit_authority_receipt_sha256: str,
    activation_susceptibility_receipt_sha256: str,
    signed_native_signal: Fraction,
    native_signal_unit: str,
    native_signal_unit_authority_receipt_sha256: str,
    native_observation_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "activation_susceptibility_receipt_sha256": (
                activation_susceptibility_receipt_sha256
            ),
            "interval_id": interval_id,
            "native_observation_receipt_sha256": native_observation_receipt_sha256,
            "native_signal": {
                "exact_nonnegative_magnitude": _fraction_text(abs(signed_native_signal)),
                "signed_value": _fraction_text(signed_native_signal),
                "unit": native_signal_unit,
                "unit_authority_receipt_sha256": (
                    native_signal_unit_authority_receipt_sha256
                ),
            },
            "port_id": port_id,
            "schema": "glew.chemical_receiver.native_activation_interval.v2",
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "time_unit_authority_receipt_sha256": (
                time_unit_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class NativeActivationInterval:
    interval_id: str
    port_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    time_unit_authority_receipt_sha256: str
    activation_susceptibility_receipt_sha256: str
    signed_native_signal: Fraction
    native_signal_unit: str
    native_signal_unit_authority_receipt_sha256: str
    native_observation_receipt_sha256: str
    interval_receipt_sha256: str

    @property
    def delta(self) -> Fraction:
        return self.source_time_end - self.source_time_start

    @property
    def native_signal_magnitude(self) -> Fraction:
        return abs(self.signed_native_signal)

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        require_identifier(self.interval_id, "chemical activation interval_id")
        require_identifier(self.port_id, "chemical activation port_id")
        require_fraction(self.source_time_start, "chemical interval start")
        require_fraction(self.source_time_end, "chemical interval end")
        if self.source_time_end <= self.source_time_start:
            raise ReceiptError("chemical activation interval must have positive duration")
        require_fraction(self.signed_native_signal, "signed native signal")
        require_identifier(self.native_signal_unit, "native signal unit")
        for digest, name in (
            (
                self.time_unit_authority_receipt_sha256,
                "chemical interval time-unit authority receipt",
            ),
            (
                self.activation_susceptibility_receipt_sha256,
                "chemical interval activation-susceptibility receipt",
            ),
            (
                self.native_signal_unit_authority_receipt_sha256,
                "native signal-unit authority receipt",
            ),
            (
                self.native_observation_receipt_sha256,
                "native observation receipt",
            ),
        ):
            receipt_registry.resolve(digest, name)
        expected = native_activation_interval_receipt_payload(
            interval_id=self.interval_id,
            port_id=self.port_id,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            time_unit_authority_receipt_sha256=(
                self.time_unit_authority_receipt_sha256
            ),
            activation_susceptibility_receipt_sha256=(
                self.activation_susceptibility_receipt_sha256
            ),
            signed_native_signal=self.signed_native_signal,
            native_signal_unit=self.native_signal_unit,
            native_signal_unit_authority_receipt_sha256=(
                self.native_signal_unit_authority_receipt_sha256
            ),
            native_observation_receipt_sha256=self.native_observation_receipt_sha256,
        )
        mounted = receipt_registry.resolve(
            self.interval_receipt_sha256,
            "chemical activation interval receipt",
        )
        if mounted != expected:
            raise ReceiptError(
                "chemical activation interval differs from its mounted receipt"
            )


def initial_receiver_authority_receipt_payload(
    *,
    initial_condition_id: str,
    port_id: str,
    source_time: Fraction,
    time_unit_authority_receipt_sha256: str,
    total_receptor_mass: Fraction,
    resting_mass: Fraction,
    active_mass: Fraction,
    desensitized_mass: Fraction,
    derivation_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "affine_constraint": CHEMICAL_AFFINE_CONSTRAINT_ID,
            "components": {
                "A": _fraction_text(active_mass),
                "D": _fraction_text(desensitized_mass),
                "R": _fraction_text(resting_mass),
            },
            "derivation_receipt_sha256": derivation_receipt_sha256,
            "initial_condition_id": initial_condition_id,
            "port_id": port_id,
            "schema": "glew.chemical_receiver.initial_condition_authority.v2",
            "source_time": _fraction_text(source_time),
            "time_unit_authority_receipt_sha256": (
                time_unit_authority_receipt_sha256
            ),
            "total_receptor_mass": _fraction_text(total_receptor_mass),
        }
    )


def exact_receiver_state_receipt_payload(
    *,
    port_id: str,
    source_time: Fraction,
    time_unit_id: str,
    time_unit_authority_receipt_sha256: str,
    total_receptor_mass: Fraction,
    resting_mass: Fraction,
    active_mass: Fraction,
    desensitized_mass: Fraction,
    initial_authority_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "affine_constraint": {
                "equation": "R+A+D=R_total",
                "id": CHEMICAL_AFFINE_CONSTRAINT_ID,
                "nonnegative_domain": True,
            },
            "components": {
                "A": _fraction_text(active_mass),
                "D": _fraction_text(desensitized_mass),
                "R": _fraction_text(resting_mass),
            },
            "initial_authority_receipt_sha256": initial_authority_receipt_sha256,
            "port_id": port_id,
            "schema": "glew.chemical_receiver.exact_correlated_state.v2",
            "source_time": _fraction_text(source_time),
            "time_unit_authority_receipt_sha256": (
                time_unit_authority_receipt_sha256
            ),
            "time_unit_id": time_unit_id,
            "total_receptor_mass": _fraction_text(total_receptor_mass),
        }
    )


@dataclass(frozen=True, slots=True)
class ExactReceiverState:
    port_id: str
    source_time: Fraction
    time_unit_id: str
    time_unit_authority_receipt_sha256: str
    total_receptor_mass: Fraction
    resting_mass: Fraction
    active_mass: Fraction
    desensitized_mass: Fraction
    initial_condition_id: str
    initial_derivation_receipt_sha256: str
    initial_authority_receipt_sha256: str
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def components(self) -> tuple[Fraction, Fraction, Fraction]:
        return self.resting_mass, self.active_mass, self.desensitized_mass

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        require_identifier(self.port_id, "chemical state port_id")
        require_fraction(self.source_time, "chemical state source_time")
        require_identifier(self.time_unit_id, "chemical state time_unit_id")
        receipt_registry.resolve(
            self.time_unit_authority_receipt_sha256,
            "chemical state time-unit authority receipt",
        )
        require_fraction(self.total_receptor_mass, "total receptor mass")
        for value in self.components:
            require_fraction(value, "exact receptor component")
        if self.total_receptor_mass <= 0:
            raise ReceiptError("total receptor mass must be strictly positive")
        if any(value < 0 for value in self.components):
            raise ReceiptError("exact receptor component cannot be negative")
        if sum(self.components, Fraction(0)) != self.total_receptor_mass:
            raise ReceiptError("exact receptor state violates R+A+D=R_total")
        require_identifier(self.initial_condition_id, "chemical initial_condition_id")
        receipt_registry.resolve(
            self.initial_derivation_receipt_sha256,
            "chemical initial-condition derivation receipt",
        )
        initial_expected = initial_receiver_authority_receipt_payload(
            initial_condition_id=self.initial_condition_id,
            port_id=self.port_id,
            source_time=self.source_time,
            time_unit_authority_receipt_sha256=(
                self.time_unit_authority_receipt_sha256
            ),
            total_receptor_mass=self.total_receptor_mass,
            resting_mass=self.resting_mass,
            active_mass=self.active_mass,
            desensitized_mass=self.desensitized_mass,
            derivation_receipt_sha256=self.initial_derivation_receipt_sha256,
        )
        mounted_initial = receipt_registry.resolve(
            self.initial_authority_receipt_sha256,
            "chemical initial-condition authority receipt",
        )
        if mounted_initial != initial_expected:
            raise ReceiptError(
                "chemical initial condition differs from its mounted receipt"
            )
        expected = exact_receiver_state_receipt_payload(
            port_id=self.port_id,
            source_time=self.source_time,
            time_unit_id=self.time_unit_id,
            time_unit_authority_receipt_sha256=(
                self.time_unit_authority_receipt_sha256
            ),
            total_receptor_mass=self.total_receptor_mass,
            resting_mass=self.resting_mass,
            active_mass=self.active_mass,
            desensitized_mass=self.desensitized_mass,
            initial_authority_receipt_sha256=self.initial_authority_receipt_sha256,
        )
        _verify_local_receipt(
            receipt_registry=receipt_registry,
            digest=self.receipt_sha256,
            payload=self.receipt_payload,
            expected=expected,
            field_name="exact chemical state receipt",
        )


def certified_receiver_state_receipt_payload(
    *,
    port_id: str,
    source_time: Fraction,
    time_unit_id: str,
    time_unit_authority_receipt_sha256: str,
    total_receptor_mass: Fraction,
    resting_mass: CertifiedBall,
    active_mass: CertifiedBall,
    desensitized_mass: CertifiedBall,
    prior_state_receipt_sha256: str,
    evolution_authority_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "affine_constraint": {
                "equation": "R+A+D=R_total",
                "id": CHEMICAL_AFFINE_CONSTRAINT_ID,
                "nonnegative_domain": True,
            },
            "component_enclosures": {
                "A": _ball_payload(active_mass),
                "D": _ball_payload(desensitized_mass),
                "R": _ball_payload(resting_mass),
            },
            "evolution_authority_receipt_sha256": (
                evolution_authority_receipt_sha256
            ),
            "port_id": port_id,
            "prior_state_receipt_sha256": prior_state_receipt_sha256,
            "schema": "glew.chemical_receiver.certified_correlated_state.v2",
            "source_time": _fraction_text(source_time),
            "time_unit_authority_receipt_sha256": (
                time_unit_authority_receipt_sha256
            ),
            "time_unit_id": time_unit_id,
            "total_receptor_mass": _fraction_text(total_receptor_mass),
        }
    )


@dataclass(frozen=True, slots=True)
class CertifiedReceiverState:
    port_id: str
    source_time: Fraction
    time_unit_id: str
    time_unit_authority_receipt_sha256: str
    total_receptor_mass: Fraction
    resting_mass: CertifiedBall
    active_mass: CertifiedBall
    desensitized_mass: CertifiedBall
    exact_affine_constraint_id: str
    prior_state_receipt_sha256: str
    evolution_authority_receipt_sha256: str
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def components(self) -> tuple[CertifiedBall, CertifiedBall, CertifiedBall]:
        return self.resting_mass, self.active_mass, self.desensitized_mass

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        require_identifier(self.port_id, "chemical state port_id")
        require_fraction(self.source_time, "chemical state source_time")
        require_identifier(self.time_unit_id, "chemical state time_unit_id")
        receipt_registry.resolve(
            self.time_unit_authority_receipt_sha256,
            "chemical state time-unit authority receipt",
        )
        require_fraction(self.total_receptor_mass, "total receptor mass")
        if self.total_receptor_mass <= 0:
            raise ReceiptError("total receptor mass must be strictly positive")
        if self.exact_affine_constraint_id != CHEMICAL_AFFINE_CONSTRAINT_ID:
            raise ReceiptError("certified chemical state lost its affine constraint")
        bounds = tuple(_ball_bounds(value) for value in self.components)
        if any(
            upper < 0 or lower > self.total_receptor_mass
            for lower, upper in bounds
        ):
            raise ReceiptError(
                "a chemical enclosure excludes the nonnegative affine state"
            )
        if (
            sum((lower for lower, _ in bounds), Fraction(0))
            > self.total_receptor_mass
            or sum((upper for _, upper in bounds), Fraction(0))
            < self.total_receptor_mass
        ):
            raise ReceiptError(
                "chemical component enclosures exclude exact mass conservation"
            )
        receipt_registry.resolve(
            self.prior_state_receipt_sha256,
            "prior chemical state receipt",
        )
        receipt_registry.resolve(
            self.evolution_authority_receipt_sha256,
            "chemical state evolution-authority receipt",
        )
        expected = certified_receiver_state_receipt_payload(
            port_id=self.port_id,
            source_time=self.source_time,
            time_unit_id=self.time_unit_id,
            time_unit_authority_receipt_sha256=(
                self.time_unit_authority_receipt_sha256
            ),
            total_receptor_mass=self.total_receptor_mass,
            resting_mass=self.resting_mass,
            active_mass=self.active_mass,
            desensitized_mass=self.desensitized_mass,
            prior_state_receipt_sha256=self.prior_state_receipt_sha256,
            evolution_authority_receipt_sha256=(
                self.evolution_authority_receipt_sha256
            ),
        )
        _verify_local_receipt(
            receipt_registry=receipt_registry,
            digest=self.receipt_sha256,
            payload=self.receipt_payload,
            expected=expected,
            field_name="certified chemical state receipt",
        )


ReceiverState = ExactReceiverState | CertifiedReceiverState


def receiver_evolution_authority_receipt_payload(
    *,
    authority_id: str,
    port_id: str,
    prior_state_receipt_sha256: str,
    activation_interval_receipt_sha256: str,
    activation_susceptibility_receipt_sha256: str,
    ordered_rate_receipt_sha256s: Sequence[str],
    time_unit_authority_receipt_sha256: str,
    backend_authority_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "activation_interval_receipt_sha256": (
                activation_interval_receipt_sha256
            ),
            "activation_susceptibility_receipt_sha256": (
                activation_susceptibility_receipt_sha256
            ),
            "authority_id": authority_id,
            "backend_authority_receipt_sha256": (
                backend_authority_receipt_sha256
            ),
            "equations": [
                "alpha=susceptibility*abs(signed_native_boundary_flux)",
                "x_next=exp(G(alpha)*delta_time)*x",
            ],
            "operator": CHEMICAL_RECEIVER_OPERATOR_ID,
            "ordered_inverse_time_rate_receipt_sha256s": list(
                ordered_rate_receipt_sha256s
            ),
            "port_id": port_id,
            "prior_state_receipt_sha256": prior_state_receipt_sha256,
            "schema": "glew.chemical_receiver.evolution_authority.v2",
            "time_unit_authority_receipt_sha256": (
                time_unit_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class ReceiverEvolutionAuthority:
    authority_id: str
    port_id: str
    prior_state_receipt_sha256: str
    activation_interval: NativeActivationInterval | None
    activation_susceptibility: MountedActivationSusceptibility | None
    rates: tuple[MountedChemicalRate, ...]
    time_unit: ChemicalTimeUnitAuthority | None
    backend: ChemicalBackendAuthority | None
    authority_receipt_sha256: str

    def verify(
        self,
        state: ReceiverState,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        require_identifier(self.authority_id, "chemical evolution authority_id")
        require_identifier(self.port_id, "chemical evolution port_id")
        if self.port_id != state.port_id:
            raise ReceiptError("chemical evolution authority names another port")
        if self.prior_state_receipt_sha256 != state.receipt_sha256:
            raise ReceiptError("chemical evolution authority names another prior state")
        if not isinstance(self.activation_interval, NativeActivationInterval):
            raise ReceiptError("chemical activation interval authority is missing")
        if not isinstance(
            self.activation_susceptibility,
            MountedActivationSusceptibility,
        ):
            raise ReceiptError("chemical activation susceptibility authority is missing")
        if not isinstance(self.time_unit, ChemicalTimeUnitAuthority):
            raise ReceiptError("chemical time-unit authority is missing")
        if not isinstance(self.backend, ChemicalBackendAuthority):
            raise ReceiptError("chemical backend authority is missing")
        if not isinstance(self.rates, tuple) or not all(
            isinstance(value, MountedChemicalRate) for value in self.rates
        ):
            raise ReceiptError("chemical inverse-time rate authority is missing")
        if tuple(value.transition for value in self.rates) != KINETIC_RATE_TRANSITIONS:
            raise ReceiptError(
                "chemical evolution requires canonically ordered deactivation, "
                "desensitization, and recovery rates"
            )
        if len({value.transition for value in self.rates}) != len(
            KINETIC_RATE_TRANSITIONS
        ):
            raise ReceiptError("chemical inverse-time rates are not unique")
        self.time_unit.verify(receipt_registry)
        self.backend.verify(receipt_registry)
        interval = self.activation_interval
        susceptibility = self.activation_susceptibility
        interval.verify(receipt_registry)
        susceptibility.verify(receipt_registry)
        for rate in self.rates:
            rate.verify(receipt_registry)
        if state.time_unit_id != self.time_unit.time_unit_id:
            raise ReceiptError("chemical state and mounted time unit differ")
        if (
            state.time_unit_authority_receipt_sha256
            != self.time_unit.authority_receipt_sha256
            or interval.time_unit_authority_receipt_sha256
            != self.time_unit.authority_receipt_sha256
            or susceptibility.time_unit_authority_receipt_sha256
            != self.time_unit.authority_receipt_sha256
            or any(
                rate.time_unit_authority_receipt_sha256
                != self.time_unit.authority_receipt_sha256
                for rate in self.rates
            )
        ):
            raise ReceiptError("chemical inputs do not share one mounted time unit")
        if interval.port_id != self.port_id or susceptibility.port_id != self.port_id:
            raise ReceiptError("chemical activation inputs cross native port boundaries")
        if any(rate.port_id != self.port_id for rate in self.rates):
            raise ReceiptError("chemical rates cross native port boundaries")
        if interval.source_time_start != state.source_time:
            raise ReceiptError("chemical interval does not begin at the prior state")
        if (
            interval.activation_susceptibility_receipt_sha256
            != susceptibility.authority_receipt_sha256
        ):
            raise ReceiptError(
                "chemical interval names another activation susceptibility"
            )
        if (
            interval.native_signal_unit != susceptibility.native_signal_unit
            or interval.native_signal_unit_authority_receipt_sha256
            != susceptibility.native_signal_unit_authority_receipt_sha256
        ):
            raise ReceiptError(
                "chemical boundary flux and susceptibility use different native units"
            )
        ordered_rate_receipts = tuple(
            value.authority_receipt_sha256 for value in self.rates
        )
        expected = receiver_evolution_authority_receipt_payload(
            authority_id=self.authority_id,
            port_id=self.port_id,
            prior_state_receipt_sha256=self.prior_state_receipt_sha256,
            activation_interval_receipt_sha256=interval.interval_receipt_sha256,
            activation_susceptibility_receipt_sha256=(
                susceptibility.authority_receipt_sha256
            ),
            ordered_rate_receipt_sha256s=ordered_rate_receipts,
            time_unit_authority_receipt_sha256=(
                self.time_unit.authority_receipt_sha256
            ),
            backend_authority_receipt_sha256=self.backend.authority_receipt_sha256,
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "chemical evolution authority receipt",
        )
        if mounted != expected:
            raise ReceiptError(
                "chemical evolution authority differs from its mounted receipt"
            )


def effective_activation_propensity_receipt_payload(
    *,
    port_id: str,
    activation_interval_receipt_sha256: str,
    activation_susceptibility_receipt_sha256: str,
    time_unit_authority_receipt_sha256: str,
    native_signal_unit: str,
    native_signal_unit_authority_receipt_sha256: str,
    signed_native_signal: Fraction,
    native_signal_magnitude: Fraction,
    susceptibility_per_native_signal_unit_per_time_unit: Fraction,
    effective_propensity_per_time_unit: Fraction,
) -> bytes:
    return _canonical_bytes(
        {
            "activation_interval_receipt_sha256": (
                activation_interval_receipt_sha256
            ),
            "activation_susceptibility_receipt_sha256": (
                activation_susceptibility_receipt_sha256
            ),
            "dimension": "inverse_mounted_time_unit",
            "equation": "alpha=susceptibility*abs(signed_native_boundary_flux)",
            "exact_nonnegative_native_signal_magnitude": _fraction_text(
                native_signal_magnitude
            ),
            "native_signal_unit": native_signal_unit,
            "native_signal_unit_authority_receipt_sha256": (
                native_signal_unit_authority_receipt_sha256
            ),
            "port_id": port_id,
            "propensity_per_time_unit": _fraction_text(
                effective_propensity_per_time_unit
            ),
            "schema": "glew.chemical_receiver.effective_activation_propensity.v1",
            "signed_native_signal": _fraction_text(signed_native_signal),
            "susceptibility_per_native_signal_unit_per_time_unit": _fraction_text(
                susceptibility_per_native_signal_unit_per_time_unit
            ),
            "time_unit_authority_receipt_sha256": (
                time_unit_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class EffectiveActivationPropensity:
    port_id: str
    activation_interval_receipt_sha256: str
    activation_susceptibility_receipt_sha256: str
    time_unit_authority_receipt_sha256: str
    native_signal_unit: str
    native_signal_unit_authority_receipt_sha256: str
    signed_native_signal: Fraction
    native_signal_magnitude: Fraction
    susceptibility_per_native_signal_unit_per_time_unit: Fraction
    propensity_per_time_unit: Fraction
    receipt_sha256: str
    receipt_payload: bytes


def _effective_activation(
    authority: ReceiverEvolutionAuthority,
) -> EffectiveActivationPropensity:
    interval = authority.activation_interval
    susceptibility = authority.activation_susceptibility
    if not isinstance(interval, NativeActivationInterval) or not isinstance(
        susceptibility,
        MountedActivationSusceptibility,
    ):
        raise ReceiptError("chemical activation authority is incomplete")
    magnitude = interval.native_signal_magnitude
    propensity = (
        susceptibility.susceptibility_per_native_signal_unit_per_time_unit
        * magnitude
    )
    if magnitude < 0 or propensity < 0:
        raise ReceiptError("chemical activation propensity left nonnegative domain")
    payload = effective_activation_propensity_receipt_payload(
        port_id=authority.port_id,
        activation_interval_receipt_sha256=interval.interval_receipt_sha256,
        activation_susceptibility_receipt_sha256=(
            susceptibility.authority_receipt_sha256
        ),
        time_unit_authority_receipt_sha256=(
            susceptibility.time_unit_authority_receipt_sha256
        ),
        native_signal_unit=interval.native_signal_unit,
        native_signal_unit_authority_receipt_sha256=(
            interval.native_signal_unit_authority_receipt_sha256
        ),
        signed_native_signal=interval.signed_native_signal,
        native_signal_magnitude=magnitude,
        susceptibility_per_native_signal_unit_per_time_unit=(
            susceptibility.susceptibility_per_native_signal_unit_per_time_unit
        ),
        effective_propensity_per_time_unit=propensity,
    )
    return EffectiveActivationPropensity(
        authority.port_id,
        interval.interval_receipt_sha256,
        susceptibility.authority_receipt_sha256,
        susceptibility.time_unit_authority_receipt_sha256,
        interval.native_signal_unit,
        interval.native_signal_unit_authority_receipt_sha256,
        interval.signed_native_signal,
        magnitude,
        susceptibility.susceptibility_per_native_signal_unit_per_time_unit,
        propensity,
        receipt_sha256(payload),
        payload,
    )


@dataclass(frozen=True, slots=True)
class ChemicalGeneratorEntry:
    row: int
    column: int
    value: Fraction


def _chemical_generator_entries(
    activation: EffectiveActivationPropensity,
    rates: Sequence[MountedChemicalRate],
) -> tuple[ChemicalGeneratorEntry, ...]:
    if len(rates) != len(KINETIC_RATE_TRANSITIONS):
        raise ReceiptError("chemical generator requires three inverse-time rates")
    alpha = activation.propensity_per_time_unit
    beta, gamma, recovery = (value.rate_per_time_unit for value in rates)
    entries = (
        ChemicalGeneratorEntry(0, 0, -alpha),
        ChemicalGeneratorEntry(1, 0, alpha),
        ChemicalGeneratorEntry(0, 1, beta),
        ChemicalGeneratorEntry(1, 1, -(beta + gamma)),
        ChemicalGeneratorEntry(2, 1, gamma),
        ChemicalGeneratorEntry(0, 2, recovery),
        ChemicalGeneratorEntry(2, 2, -recovery),
    )
    result = tuple(value for value in entries if value.value != 0)
    for column in range(3):
        column_sum = sum(
            (value.value for value in result if value.column == column),
            Fraction(0),
        )
        if column_sum != 0:
            raise ReceiptError("chemical generator lost exact mass conservation")
        if any(
            value.row != value.column and value.value < 0
            for value in result
            if value.column == column
        ):
            raise ReceiptError("chemical generator has a negative transfer propensity")
    return result


def chemical_generator_receipt_payload(
    *,
    authority_receipt_sha256: str,
    effective_activation_propensity_receipt_sha256: str,
    ordered_rate_receipt_sha256s: Sequence[str],
    generator_entries: Sequence[ChemicalGeneratorEntry],
) -> bytes:
    return _canonical_bytes(
        {
            "affine_conservation": "exact_zero_column_sums",
            "authority_receipt_sha256": authority_receipt_sha256,
            "effective_activation_propensity_receipt_sha256": (
                effective_activation_propensity_receipt_sha256
            ),
            "entries": [
                {
                    "column": value.column,
                    "row": value.row,
                    "value_per_time_unit": _fraction_text(value.value),
                }
                for value in generator_entries
            ],
            "matrix_dimension": "inverse_mounted_time_unit",
            "ordered_inverse_time_rate_receipt_sha256s": list(
                ordered_rate_receipt_sha256s
            ),
            "schema": "glew.chemical_receiver.generator.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class ChemicalGeneratorReceipt:
    authority_receipt_sha256: str
    effective_activation_propensity_receipt_sha256: str
    ordered_rate_receipt_sha256s: tuple[str, ...]
    entries: tuple[ChemicalGeneratorEntry, ...]
    receipt_sha256: str
    receipt_payload: bytes


def _chemical_generator(
    authority: ReceiverEvolutionAuthority,
    activation: EffectiveActivationPropensity,
) -> ChemicalGeneratorReceipt:
    entries = _chemical_generator_entries(activation, authority.rates)
    rate_receipts = tuple(
        value.authority_receipt_sha256 for value in authority.rates
    )
    payload = chemical_generator_receipt_payload(
        authority_receipt_sha256=authority.authority_receipt_sha256,
        effective_activation_propensity_receipt_sha256=activation.receipt_sha256,
        ordered_rate_receipt_sha256s=rate_receipts,
        generator_entries=entries,
    )
    return ChemicalGeneratorReceipt(
        authority.authority_receipt_sha256,
        activation.receipt_sha256,
        rate_receipts,
        entries,
        receipt_sha256(payload),
        payload,
    )


def certified_chemical_relevance_receipt_payload(
    *,
    port_id: str,
    state_receipt_sha256: str,
    active_mass: CertifiedBall,
    total_receptor_mass: Fraction,
    relevance: CertifiedBall,
) -> bytes:
    return _canonical_bytes(
        {
            "active_mass_enclosure": _ball_payload(active_mass),
            "denominator": _fraction_text(total_receptor_mass),
            "equation": "relevance=A/R_total",
            "native_signal_replaced": False,
            "port_id": port_id,
            "relevance_enclosure": _ball_payload(relevance),
            "schema": "glew.chemical_receiver.certified_relevance.v2",
            "state_receipt_sha256": state_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class CertifiedChemicalRelevance:
    port_id: str
    state_receipt_sha256: str
    active_mass: CertifiedBall
    total_receptor_mass: Fraction
    value: CertifiedBall
    receipt_sha256: str
    receipt_payload: bytes


def chemical_evolution_result_receipt_payload(
    *,
    authority: ReceiverEvolutionAuthority,
    activation: EffectiveActivationPropensity,
    generator: ChemicalGeneratorReceipt,
    result_state_receipt_sha256: str,
    relevance_receipt_sha256: str,
) -> bytes:
    if not isinstance(authority.backend, ChemicalBackendAuthority):
        raise ReceiptError("chemical result requires backend authority")
    if not isinstance(authority.activation_interval, NativeActivationInterval):
        raise ReceiptError("chemical result requires activation interval")
    if not isinstance(
        authority.activation_susceptibility,
        MountedActivationSusceptibility,
    ):
        raise ReceiptError("chemical result requires activation susceptibility")
    interval = authority.activation_interval
    susceptibility = authority.activation_susceptibility
    return _canonical_bytes(
        {
            "activation_susceptibility": {
                "authority_receipt_sha256": susceptibility.authority_receipt_sha256,
                "value_per_native_signal_unit_per_time_unit": _fraction_text(
                    susceptibility.susceptibility_per_native_signal_unit_per_time_unit
                ),
            },
            "authority_receipt_sha256": authority.authority_receipt_sha256,
            "backend": {
                "authority_receipt_sha256": (
                    authority.backend.authority_receipt_sha256
                ),
                "flint": FLINT_VERSION,
                "precision_bits": authority.backend.working_precision_bits,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "effective_activation": {
                "propensity_per_time_unit": _fraction_text(
                    activation.propensity_per_time_unit
                ),
                "receipt_sha256": activation.receipt_sha256,
            },
            "generator_receipt_sha256": generator.receipt_sha256,
            "native_boundary_flux": {
                "exact_nonnegative_magnitude": _fraction_text(
                    interval.native_signal_magnitude
                ),
                "observation_receipt_sha256": (
                    interval.native_observation_receipt_sha256
                ),
                "signed_value": _fraction_text(interval.signed_native_signal),
                "unit": interval.native_signal_unit,
                "unit_authority_receipt_sha256": (
                    interval.native_signal_unit_authority_receipt_sha256
                ),
            },
            "nonnegative_proof": "Metzler_generator_matrix_exponential",
            "operator": CHEMICAL_RECEIVER_OPERATOR_ID,
            "relevance_receipt_sha256": relevance_receipt_sha256,
            "result_state_receipt_sha256": result_state_receipt_sha256,
            "schema": "glew.chemical_receiver.evolution_result.v2",
        }
    )


@dataclass(frozen=True, slots=True)
class ChemicalEvolutionReceipt:
    authority_receipt_sha256: str
    prior_state_receipt_sha256: str
    result_state_receipt_sha256: str
    effective_activation: EffectiveActivationPropensity
    generator: ChemicalGeneratorReceipt
    backend_authority_receipt_sha256: str
    precision_bits: int
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def generator_entries(self) -> tuple[ChemicalGeneratorEntry, ...]:
        return self.generator.entries


class ReceiverEvolutionStatus(str, Enum):
    EVOLVED = "evolved"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ReceiverEvolutionResult:
    status: ReceiverEvolutionStatus
    state: ReceiverState | None
    relevance: CertifiedChemicalRelevance | None
    signed_native_signal: Fraction | None
    native_signal_unit: str | None
    native_observation_receipt_sha256: str | None
    receipt: ChemicalEvolutionReceipt | None
    reason: str


def _unknown(
    state: ReceiverState | None,
    reason: str,
) -> ReceiverEvolutionResult:
    return ReceiverEvolutionResult(
        status=ReceiverEvolutionStatus.UNKNOWN,
        state=state,
        relevance=None,
        signed_native_signal=None,
        native_signal_unit=None,
        native_observation_receipt_sha256=None,
        receipt=None,
        reason=reason,
    )


def evolve_chemical_receiver(
    *,
    state: ReceiverState | None,
    authority: ReceiverEvolutionAuthority | None,
    receipt_registry: ReceiptRegistry | None,
) -> ReceiverEvolutionResult:
    """Evolve one independent receiver or return typed UNKNOWN unchanged."""

    retained_state = state if isinstance(
        state, (ExactReceiverState, CertifiedReceiverState)
    ) else None
    try:
        if retained_state is None:
            raise ReceiptError("typed chemical receiver state is missing")
        if not isinstance(authority, ReceiverEvolutionAuthority):
            raise ReceiptError("chemical evolution authority is missing")
        if not isinstance(receipt_registry, ReceiptRegistry):
            raise ReceiptError("mounted chemical receipt registry is missing")
        retained_state.verify(receipt_registry)
        authority.verify(retained_state, receipt_registry)
        if not isinstance(authority.activation_interval, NativeActivationInterval):
            raise ReceiptError("chemical activation interval authority is missing")
        if not isinstance(authority.backend, ChemicalBackendAuthority):
            raise ReceiptError("chemical backend authority is missing")
        activation = _effective_activation(authority)
        generator = _chemical_generator(authority, activation)
        flint = load_pinned_flint()
    except ReceiptError as exc:
        return _unknown(retained_state, str(exc))

    interval = authority.activation_interval
    backend = authority.backend
    with flint.ctx.workprec(backend.working_precision_bits):
        matrix = flint.arb_mat(3, 3)
        for entry in generator.entries:
            matrix[entry.row, entry.column] = arb_fraction(flint, entry.value)
        transition = (matrix * arb_fraction(flint, interval.delta)).exp()
        if not all(
            transition[row, column].is_finite()
            for row in range(3)
            for column in range(3)
        ):
            raise ReceiptError("chemical matrix exponential is nonfinite")
        if isinstance(retained_state, ExactReceiverState):
            initial_values = tuple(
                arb_fraction(flint, value) for value in retained_state.components
            )
        else:
            initial_values = tuple(
                _arb_from_ball(flint, value) for value in retained_state.components
            )
        initial = flint.arb_mat(3, 1, list(initial_values))
        evolved = transition * initial
        values = tuple(evolved[index, 0] for index in range(3))
        if not all(value.is_finite() for value in values):
            raise ReceiptError("chemical receiver result is nonfinite")
        balls = tuple(
            canonical_ball(value, backend.working_precision_bits) for value in values
        )
        relevance_ball = canonical_ball(
            values[1] / arb_fraction(flint, retained_state.total_receptor_mass),
            backend.working_precision_bits,
        )

    state_payload = certified_receiver_state_receipt_payload(
        port_id=retained_state.port_id,
        source_time=interval.source_time_end,
        time_unit_id=retained_state.time_unit_id,
        time_unit_authority_receipt_sha256=(
            retained_state.time_unit_authority_receipt_sha256
        ),
        total_receptor_mass=retained_state.total_receptor_mass,
        resting_mass=balls[0],
        active_mass=balls[1],
        desensitized_mass=balls[2],
        prior_state_receipt_sha256=retained_state.receipt_sha256,
        evolution_authority_receipt_sha256=authority.authority_receipt_sha256,
    )
    result_state = CertifiedReceiverState(
        port_id=retained_state.port_id,
        source_time=interval.source_time_end,
        time_unit_id=retained_state.time_unit_id,
        time_unit_authority_receipt_sha256=(
            retained_state.time_unit_authority_receipt_sha256
        ),
        total_receptor_mass=retained_state.total_receptor_mass,
        resting_mass=balls[0],
        active_mass=balls[1],
        desensitized_mass=balls[2],
        exact_affine_constraint_id=CHEMICAL_AFFINE_CONSTRAINT_ID,
        prior_state_receipt_sha256=retained_state.receipt_sha256,
        evolution_authority_receipt_sha256=authority.authority_receipt_sha256,
        receipt_sha256=receipt_sha256(state_payload),
        receipt_payload=state_payload,
    )
    relevance_payload = certified_chemical_relevance_receipt_payload(
        port_id=result_state.port_id,
        state_receipt_sha256=result_state.receipt_sha256,
        active_mass=result_state.active_mass,
        total_receptor_mass=result_state.total_receptor_mass,
        relevance=relevance_ball,
    )
    relevance = CertifiedChemicalRelevance(
        port_id=result_state.port_id,
        state_receipt_sha256=result_state.receipt_sha256,
        active_mass=result_state.active_mass,
        total_receptor_mass=result_state.total_receptor_mass,
        value=relevance_ball,
        receipt_sha256=receipt_sha256(relevance_payload),
        receipt_payload=relevance_payload,
    )
    result_payload = chemical_evolution_result_receipt_payload(
        authority=authority,
        activation=activation,
        generator=generator,
        result_state_receipt_sha256=result_state.receipt_sha256,
        relevance_receipt_sha256=relevance.receipt_sha256,
    )
    evolution_receipt = ChemicalEvolutionReceipt(
        authority_receipt_sha256=authority.authority_receipt_sha256,
        prior_state_receipt_sha256=retained_state.receipt_sha256,
        result_state_receipt_sha256=result_state.receipt_sha256,
        effective_activation=activation,
        generator=generator,
        backend_authority_receipt_sha256=backend.authority_receipt_sha256,
        precision_bits=backend.working_precision_bits,
        receipt_sha256=receipt_sha256(result_payload),
        receipt_payload=result_payload,
    )
    return ReceiverEvolutionResult(
        status=ReceiverEvolutionStatus.EVOLVED,
        state=result_state,
        relevance=relevance,
        signed_native_signal=interval.signed_native_signal,
        native_signal_unit=interval.native_signal_unit,
        native_observation_receipt_sha256=(
            interval.native_observation_receipt_sha256
        ),
        receipt=evolution_receipt,
        reason=(
            "exact boundary-flux magnitude drove the conservative chemical interval"
        ),
    )


__all__ = (
    "CHEMICAL_AFFINE_CONSTRAINT_ID",
    "CHEMICAL_BACKEND_SOLVER_ID",
    "CHEMICAL_RECEIVER_OPERATOR_ID",
    "KINETIC_RATE_TRANSITIONS",
    "ChemicalBackendAuthority",
    "ChemicalEvolutionReceipt",
    "ChemicalGeneratorEntry",
    "ChemicalGeneratorReceipt",
    "ChemicalTimeUnitAuthority",
    "CertifiedChemicalRelevance",
    "CertifiedReceiverState",
    "EffectiveActivationPropensity",
    "ExactReceiverState",
    "MountedActivationSusceptibility",
    "MountedChemicalRate",
    "NativeActivationInterval",
    "ReceiverEvolutionAuthority",
    "ReceiverEvolutionResult",
    "ReceiverEvolutionStatus",
    "ReceiverState",
    "ReceiverTransition",
    "TRANSITION_ORDER",
    "activation_susceptibility_authority_receipt_payload",
    "certified_chemical_relevance_receipt_payload",
    "certified_receiver_state_receipt_payload",
    "chemical_backend_authority_receipt_payload",
    "chemical_evolution_result_receipt_payload",
    "chemical_generator_receipt_payload",
    "chemical_rate_authority_receipt_payload",
    "chemical_time_unit_authority_receipt_payload",
    "effective_activation_propensity_receipt_payload",
    "evolve_chemical_receiver",
    "exact_receiver_state_receipt_payload",
    "initial_receiver_authority_receipt_payload",
    "native_activation_interval_receipt_payload",
    "receiver_evolution_authority_receipt_payload",
)
