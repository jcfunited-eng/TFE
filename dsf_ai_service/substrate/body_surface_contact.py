"""Exact bounded contact between two declared virtual body-surface sites.

This module contains no action selection, semantic interaction names, organism
state, authentication, persistence, or observation receipts.  A caller admits
one pair of explicit surface trajectories, settles that one reached contact,
and applies the returned reciprocal physical facts at the organism boundary.

The virtual material is a normal spring, a tangential viscous interface, and a
thermal conductor.  Every coefficient is required as declared morphology
input.  No value is defaulted or inferred from a body or site identifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction


MAX_CONTACT_IDENTIFIER_BYTES = 256
MAX_CONTACT_RATIONAL_BITS = 256
_ADMITTED_BODY_SURFACE_PAIR_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class ExactVector3:
    x: Fraction
    y: Fraction
    z: Fraction

    def __add__(self, other: "ExactVector3") -> "ExactVector3":
        return ExactVector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "ExactVector3") -> "ExactVector3":
        return ExactVector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def scaled(self, scalar: Fraction) -> "ExactVector3":
        return ExactVector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other: "ExactVector3") -> Fraction:
        return self.x * other.x + self.y * other.y + self.z * other.z


ZERO_VECTOR = ExactVector3(Fraction(0), Fraction(0), Fraction(0))


@dataclass(frozen=True, slots=True)
class BodySurfaceMaterial:
    """Declared virtual material coefficients; no coefficient is defaulted."""

    normal_stiffness_millinewtons_per_micrometre_per_square_micrometre: Fraction
    tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre: Fraction
    thermal_conductance_nanowatts_per_square_micrometre_millikelvin: Fraction


@dataclass(frozen=True, slots=True)
class RectangularBodySurfaceSite:
    """One fixed rectangular surface lattice site and exact local basis."""

    body_id: str
    site_id: str
    outward_normal: ExactVector3
    tangent_u: ExactVector3
    tangent_v: ExactVector3
    half_extent_u_micrometres: Fraction
    half_extent_v_micrometres: Fraction
    material: BodySurfaceMaterial


@dataclass(frozen=True, slots=True)
class BodySurfaceState:
    """One boundary state of a surface site's centre and temperature."""

    centre_micrometres: ExactVector3
    temperature_millikelvin: Fraction


@dataclass(frozen=True, slots=True)
class BodySurfaceTrajectory:
    """Exact linear centre and temperature trajectory over one caller clock."""

    site: RectangularBodySurfaceSite
    predecessor: BodySurfaceState
    successor: BodySurfaceState


class ContactDisposition(str, Enum):
    CONTACT = "contact"
    SEPARATED = "separated"


@dataclass(frozen=True, slots=True)
class ReciprocalBodySurfaceContact:
    disposition: ContactDisposition
    body_a_id: str
    site_a_id: str
    body_b_id: str
    site_b_id: str
    duration_microseconds: Fraction
    predecessor_signed_gap_micrometres: Fraction
    successor_signed_gap_micrometres: Fraction
    contact_area_square_micrometres: Fraction
    predecessor_compression_micrometres: Fraction
    successor_compression_micrometres: Fraction
    predecessor_normal_load_millinewtons: Fraction
    successor_normal_load_millinewtons: Fraction
    predecessor_normal_elastic_energy_nanojoules: Fraction
    successor_normal_elastic_energy_nanojoules: Fraction
    normal_work_into_interface_nanojoules: Fraction
    tangential_relative_displacement_u_micrometres: Fraction
    tangential_relative_displacement_v_micrometres: Fraction
    tangential_slip_occurred: bool
    successor_normal_force_on_a_millinewtons: ExactVector3
    successor_normal_force_on_b_millinewtons: ExactVector3
    constant_tangential_force_on_a_millinewtons: ExactVector3
    constant_tangential_force_on_b_millinewtons: ExactVector3
    tangential_dissipated_work_nanojoules: Fraction
    conductive_heat_to_a_nanojoules: Fraction
    conductive_heat_to_b_nanojoules: Fraction
    separating_motion_a_micrometres: Fraction
    separating_motion_b_micrometres: Fraction


@dataclass(frozen=True, slots=True)
class _AdmittedBodySurfacePair:
    a: BodySurfaceTrajectory
    b: BodySurfaceTrajectory
    duration_microseconds: Fraction
    predecessor_gap: Fraction
    successor_gap: Fraction
    predecessor_u: Fraction
    predecessor_v: Fraction
    successor_u: Fraction
    successor_v: Fraction
    contact_area: Fraction
    contact_interval: bool
    _construction_authority: object


def _require_fraction(
    value: object,
    name: str,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Fraction:
    if not isinstance(value, Fraction):
        raise TypeError(f"{name} must be an exact Fraction")
    if (
        value.numerator.bit_length() > MAX_CONTACT_RATIONAL_BITS
        or value.denominator.bit_length() > MAX_CONTACT_RATIONAL_BITS
    ):
        raise ValueError(f"{name} exceeds the exact rational bit boundary")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _validate_vector(value: ExactVector3, name: str) -> None:
    if not isinstance(value, ExactVector3):
        raise TypeError(f"{name} must be an ExactVector3")
    for component_name, component in (
        ("x", value.x),
        ("y", value.y),
        ("z", value.z),
    ):
        _require_fraction(component, f"{name}.{component_name}")


def _validate_material(material: BodySurfaceMaterial, name: str) -> None:
    if not isinstance(material, BodySurfaceMaterial):
        raise TypeError(f"{name} must be a BodySurfaceMaterial")
    _require_fraction(
        material.normal_stiffness_millinewtons_per_micrometre_per_square_micrometre,
        f"{name}.normal_stiffness",
        positive=True,
    )
    _require_fraction(
        material.tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre,
        f"{name}.tangential_damping",
        nonnegative=True,
    )
    _require_fraction(
        material.thermal_conductance_nanowatts_per_square_micrometre_millikelvin,
        f"{name}.thermal_conductance",
        nonnegative=True,
    )


def _validate_site(site: RectangularBodySurfaceSite, name: str) -> None:
    if not isinstance(site, RectangularBodySurfaceSite):
        raise TypeError(f"{name} must be a RectangularBodySurfaceSite")
    for identifier_name, identifier in (
        ("body_id", site.body_id),
        ("site_id", site.site_id),
    ):
        if (
            not isinstance(identifier, str)
            or not identifier
            or "\x00" in identifier
            or len(identifier.encode("utf-8")) > MAX_CONTACT_IDENTIFIER_BYTES
        ):
            raise ValueError(
                f"{name}.{identifier_name} exceeds the identifier boundary"
            )
    for vector_name, vector in (
        ("outward_normal", site.outward_normal),
        ("tangent_u", site.tangent_u),
        ("tangent_v", site.tangent_v),
    ):
        _validate_vector(vector, f"{name}.{vector_name}")
        if vector.dot(vector) != 1:
            raise ValueError(f"{name}.{vector_name} must be an exact unit vector")
    if (
        site.outward_normal.dot(site.tangent_u) != 0
        or site.outward_normal.dot(site.tangent_v) != 0
        or site.tangent_u.dot(site.tangent_v) != 0
    ):
        raise ValueError(f"{name} basis must be exactly orthogonal")
    _require_fraction(
        site.half_extent_u_micrometres,
        f"{name}.half_extent_u_micrometres",
        positive=True,
    )
    _require_fraction(
        site.half_extent_v_micrometres,
        f"{name}.half_extent_v_micrometres",
        positive=True,
    )
    _validate_material(site.material, f"{name}.material")


def _validate_trajectory(trajectory: BodySurfaceTrajectory, name: str) -> None:
    if not isinstance(trajectory, BodySurfaceTrajectory):
        raise TypeError(f"{name} must be a BodySurfaceTrajectory")
    _validate_site(trajectory.site, f"{name}.site")
    for state_name, state in (
        ("predecessor", trajectory.predecessor),
        ("successor", trajectory.successor),
    ):
        if not isinstance(state, BodySurfaceState):
            raise TypeError(f"{name}.{state_name} must be a BodySurfaceState")
        _validate_vector(
            state.centre_micrometres,
            f"{name}.{state_name}.centre_micrometres",
        )
        _require_fraction(
            state.temperature_millikelvin,
            f"{name}.{state_name}.temperature_millikelvin",
            positive=True,
        )


def _harmonic_series(left: Fraction, right: Fraction) -> Fraction:
    if left == 0 or right == 0:
        return Fraction(0)
    return left * right / (left + right)


def _relative_coordinates(
    a: BodySurfaceState,
    b: BodySurfaceState,
    site_a: RectangularBodySurfaceSite,
) -> tuple[Fraction, Fraction, Fraction]:
    relative = b.centre_micrometres - a.centre_micrometres
    return (
        relative.dot(site_a.outward_normal),
        relative.dot(site_a.tangent_u),
        relative.dot(site_a.tangent_v),
    )


def _contained_contact_area(
    site_a: RectangularBodySurfaceSite,
    site_b: RectangularBodySurfaceSite,
    predecessor_u: Fraction,
    predecessor_v: Fraction,
    successor_u: Fraction,
    successor_v: Fraction,
) -> Fraction:
    b_inside_a = all(
        abs(offset) + extent_b <= extent_a
        for offset, extent_a, extent_b in (
            (
                predecessor_u,
                site_a.half_extent_u_micrometres,
                site_b.half_extent_u_micrometres,
            ),
            (
                successor_u,
                site_a.half_extent_u_micrometres,
                site_b.half_extent_u_micrometres,
            ),
            (
                predecessor_v,
                site_a.half_extent_v_micrometres,
                site_b.half_extent_v_micrometres,
            ),
            (
                successor_v,
                site_a.half_extent_v_micrometres,
                site_b.half_extent_v_micrometres,
            ),
        )
    )
    a_inside_b = all(
        abs(offset) + extent_a <= extent_b
        for offset, extent_a, extent_b in (
            (
                predecessor_u,
                site_a.half_extent_u_micrometres,
                site_b.half_extent_u_micrometres,
            ),
            (
                successor_u,
                site_a.half_extent_u_micrometres,
                site_b.half_extent_u_micrometres,
            ),
            (
                predecessor_v,
                site_a.half_extent_v_micrometres,
                site_b.half_extent_v_micrometres,
            ),
            (
                successor_v,
                site_a.half_extent_v_micrometres,
                site_b.half_extent_v_micrometres,
            ),
        )
    )
    if b_inside_a:
        return 4 * site_b.half_extent_u_micrometres * site_b.half_extent_v_micrometres
    if a_inside_b:
        return 4 * site_a.half_extent_u_micrometres * site_a.half_extent_v_micrometres
    raise ValueError(
        "surface trajectory requires exact segmentation at a changing contact-patch boundary"
    )


def admit_body_surface_pair(
    a: BodySurfaceTrajectory,
    b: BodySurfaceTrajectory,
    *,
    duration_microseconds: Fraction,
) -> _AdmittedBodySurfacePair:
    """Validate one explicit reached pair before pure physical settlement."""

    _validate_trajectory(a, "surface_a")
    _validate_trajectory(b, "surface_b")
    duration = _require_fraction(
        duration_microseconds,
        "duration_microseconds",
        positive=True,
    )
    if a.site.body_id == b.site.body_id:
        raise ValueError("body-to-body contact requires two distinct bodies")
    if b.site.outward_normal != a.site.outward_normal.scaled(Fraction(-1)):
        raise ValueError("contact surface normals must be exactly opposed")
    if b.site.tangent_u != a.site.tangent_u or b.site.tangent_v != a.site.tangent_v:
        raise ValueError("contact surface tangent bases must be exactly aligned")

    predecessor_gap, predecessor_u, predecessor_v = _relative_coordinates(
        a.predecessor, b.predecessor, a.site
    )
    successor_gap, successor_u, successor_v = _relative_coordinates(
        a.successor, b.successor, a.site
    )
    if predecessor_gap * successor_gap < 0:
        raise ValueError(
            "trajectory crosses contact onset or release and must be split at zero gap"
        )
    contact_interval = predecessor_gap <= 0 and successor_gap <= 0
    contact_area = (
        _contained_contact_area(
            a.site,
            b.site,
            predecessor_u,
            predecessor_v,
            successor_u,
            successor_v,
        )
        if contact_interval
        else Fraction(0)
    )
    return _AdmittedBodySurfacePair(
        a=a,
        b=b,
        duration_microseconds=duration,
        predecessor_gap=predecessor_gap,
        successor_gap=successor_gap,
        predecessor_u=predecessor_u,
        predecessor_v=predecessor_v,
        successor_u=successor_u,
        successor_v=successor_v,
        contact_area=contact_area,
        contact_interval=contact_interval,
        _construction_authority=_ADMITTED_BODY_SURFACE_PAIR_AUTHORITY,
    )


def settle_admitted_body_surface_contact(
    admitted: _AdmittedBodySurfacePair,
) -> ReciprocalBodySurfaceContact:
    """Settle one already-admitted pair in constant work and current state."""

    if (
        not isinstance(admitted, _AdmittedBodySurfacePair)
        or admitted._construction_authority
        is not _ADMITTED_BODY_SURFACE_PAIR_AUTHORITY
    ):
        raise ValueError("body-surface pair lacks exact admission custody")

    a = admitted.a
    b = admitted.b
    displacement_a = a.successor.centre_micrometres - a.predecessor.centre_micrometres
    displacement_b = b.successor.centre_micrometres - b.predecessor.centre_micrometres
    separating_a = max(Fraction(0), -displacement_a.dot(a.site.outward_normal))
    separating_b = max(Fraction(0), displacement_b.dot(a.site.outward_normal))

    if not admitted.contact_interval:
        return ReciprocalBodySurfaceContact(
            disposition=ContactDisposition.SEPARATED,
            body_a_id=a.site.body_id,
            site_a_id=a.site.site_id,
            body_b_id=b.site.body_id,
            site_b_id=b.site.site_id,
            duration_microseconds=admitted.duration_microseconds,
            predecessor_signed_gap_micrometres=admitted.predecessor_gap,
            successor_signed_gap_micrometres=admitted.successor_gap,
            contact_area_square_micrometres=Fraction(0),
            predecessor_compression_micrometres=Fraction(0),
            successor_compression_micrometres=Fraction(0),
            predecessor_normal_load_millinewtons=Fraction(0),
            successor_normal_load_millinewtons=Fraction(0),
            predecessor_normal_elastic_energy_nanojoules=Fraction(0),
            successor_normal_elastic_energy_nanojoules=Fraction(0),
            normal_work_into_interface_nanojoules=Fraction(0),
            tangential_relative_displacement_u_micrometres=Fraction(0),
            tangential_relative_displacement_v_micrometres=Fraction(0),
            tangential_slip_occurred=False,
            successor_normal_force_on_a_millinewtons=ZERO_VECTOR,
            successor_normal_force_on_b_millinewtons=ZERO_VECTOR,
            constant_tangential_force_on_a_millinewtons=ZERO_VECTOR,
            constant_tangential_force_on_b_millinewtons=ZERO_VECTOR,
            tangential_dissipated_work_nanojoules=Fraction(0),
            conductive_heat_to_a_nanojoules=Fraction(0),
            conductive_heat_to_b_nanojoules=Fraction(0),
            separating_motion_a_micrometres=separating_a,
            separating_motion_b_micrometres=separating_b,
        )

    material_a = a.site.material
    material_b = b.site.material
    stiffness = _harmonic_series(
        material_a.normal_stiffness_millinewtons_per_micrometre_per_square_micrometre,
        material_b.normal_stiffness_millinewtons_per_micrometre_per_square_micrometre,
    )
    damping = _harmonic_series(
        (
            material_a
            .tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre
        ),
        (
            material_b
            .tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre
        ),
    )
    conductance = _harmonic_series(
        material_a.thermal_conductance_nanowatts_per_square_micrometre_millikelvin,
        material_b.thermal_conductance_nanowatts_per_square_micrometre_millikelvin,
    )
    area = admitted.contact_area
    predecessor_compression = -admitted.predecessor_gap
    successor_compression = -admitted.successor_gap
    predecessor_load = stiffness * area * predecessor_compression
    successor_load = stiffness * area * successor_compression
    predecessor_energy = stiffness * area * predecessor_compression**2 / 2
    successor_energy = stiffness * area * successor_compression**2 / 2

    delta_u = admitted.successor_u - admitted.predecessor_u
    delta_v = admitted.successor_v - admitted.predecessor_v
    tangential_force_u_on_b = -damping * area * delta_u / admitted.duration_microseconds
    tangential_force_v_on_b = -damping * area * delta_v / admitted.duration_microseconds
    tangential_force_on_b = (
        a.site.tangent_u.scaled(tangential_force_u_on_b)
        + a.site.tangent_v.scaled(tangential_force_v_on_b)
    )
    normal_force_on_b = a.site.outward_normal.scaled(successor_load)
    normal_force_on_a = normal_force_on_b.scaled(Fraction(-1))
    tangential_force_on_a = tangential_force_on_b.scaled(Fraction(-1))
    tangential_work = (
        damping * area * (delta_u**2 + delta_v**2) / admitted.duration_microseconds
    )

    average_temperature_a = (
        a.predecessor.temperature_millikelvin
        + a.successor.temperature_millikelvin
    ) / 2
    average_temperature_b = (
        b.predecessor.temperature_millikelvin
        + b.successor.temperature_millikelvin
    ) / 2
    heat_to_a = (
        conductance
        * area
        * (average_temperature_b - average_temperature_a)
        * admitted.duration_microseconds
        / 1_000_000
    )

    return ReciprocalBodySurfaceContact(
        disposition=ContactDisposition.CONTACT,
        body_a_id=a.site.body_id,
        site_a_id=a.site.site_id,
        body_b_id=b.site.body_id,
        site_b_id=b.site.site_id,
        duration_microseconds=admitted.duration_microseconds,
        predecessor_signed_gap_micrometres=admitted.predecessor_gap,
        successor_signed_gap_micrometres=admitted.successor_gap,
        contact_area_square_micrometres=area,
        predecessor_compression_micrometres=predecessor_compression,
        successor_compression_micrometres=successor_compression,
        predecessor_normal_load_millinewtons=predecessor_load,
        successor_normal_load_millinewtons=successor_load,
        predecessor_normal_elastic_energy_nanojoules=predecessor_energy,
        successor_normal_elastic_energy_nanojoules=successor_energy,
        normal_work_into_interface_nanojoules=successor_energy - predecessor_energy,
        tangential_relative_displacement_u_micrometres=delta_u,
        tangential_relative_displacement_v_micrometres=delta_v,
        tangential_slip_occurred=delta_u != 0 or delta_v != 0,
        successor_normal_force_on_a_millinewtons=normal_force_on_a,
        successor_normal_force_on_b_millinewtons=normal_force_on_b,
        constant_tangential_force_on_a_millinewtons=tangential_force_on_a,
        constant_tangential_force_on_b_millinewtons=tangential_force_on_b,
        tangential_dissipated_work_nanojoules=tangential_work,
        conductive_heat_to_a_nanojoules=heat_to_a,
        conductive_heat_to_b_nanojoules=-heat_to_a,
        separating_motion_a_micrometres=separating_a,
        separating_motion_b_micrometres=separating_b,
    )


__all__ = [
    "BodySurfaceMaterial",
    "BodySurfaceState",
    "BodySurfaceTrajectory",
    "ContactDisposition",
    "ExactVector3",
    "ReciprocalBodySurfaceContact",
    "RectangularBodySurfaceSite",
    "admit_body_surface_pair",
    "settle_admitted_body_surface_contact",
]
