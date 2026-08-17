from dataclasses import fields, replace
from fractions import Fraction

import pytest

from dsf_ai_service.substrate.body_surface_contact import (
    BodySurfaceMaterial,
    BodySurfaceState,
    BodySurfaceTrajectory,
    ContactDisposition,
    ExactVector3,
    RectangularBodySurfaceSite,
    admit_body_surface_pair,
    settle_admitted_body_surface_contact,
)


F = Fraction
X = ExactVector3(F(1), F(0), F(0))
Y = ExactVector3(F(0), F(1), F(0))
Z = ExactVector3(F(0), F(0), F(1))


def _material(
    *,
    stiffness: Fraction = F(2),
    damping: Fraction = F(2),
    conductance: Fraction = F(2),
) -> BodySurfaceMaterial:
    return BodySurfaceMaterial(
        normal_stiffness_millinewtons_per_micrometre_per_square_micrometre=(
            stiffness
        ),
        tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre=(
            damping
        ),
        thermal_conductance_nanowatts_per_square_micrometre_millikelvin=(
            conductance
        ),
    )


def _site(
    body_id: str,
    site_id: str,
    *,
    normal: ExactVector3,
    half_u: Fraction,
    half_v: Fraction,
    material: BodySurfaceMaterial | None = None,
) -> RectangularBodySurfaceSite:
    return RectangularBodySurfaceSite(
        body_id=body_id,
        site_id=site_id,
        outward_normal=normal,
        tangent_u=Y,
        tangent_v=Z,
        half_extent_u_micrometres=half_u,
        half_extent_v_micrometres=half_v,
        material=material if material is not None else _material(),
    )


def _trajectory(
    site: RectangularBodySurfaceSite,
    predecessor: tuple[int, int, int],
    successor: tuple[int, int, int],
    *,
    predecessor_temperature: int = 300_000,
    successor_temperature: int | None = None,
) -> BodySurfaceTrajectory:
    final_temperature = (
        predecessor_temperature
        if successor_temperature is None
        else successor_temperature
    )
    return BodySurfaceTrajectory(
        site=site,
        predecessor=BodySurfaceState(
            centre_micrometres=ExactVector3(*(F(value) for value in predecessor)),
            temperature_millikelvin=F(predecessor_temperature),
        ),
        successor=BodySurfaceState(
            centre_micrometres=ExactVector3(*(F(value) for value in successor)),
            temperature_millikelvin=F(final_temperature),
        ),
    )


def _pair(
    *,
    predecessor_a: tuple[int, int, int] = (0, 0, 0),
    successor_a: tuple[int, int, int] = (0, 0, 0),
    predecessor_b: tuple[int, int, int] = (0, 0, 0),
    successor_b: tuple[int, int, int] = (-2, 0, 0),
    temperature_a: int = 300_000,
    temperature_b: int = 310_000,
) -> tuple[BodySurfaceTrajectory, BodySurfaceTrajectory]:
    site_a = _site("body-a", "surface-a", normal=X, half_u=F(10), half_v=F(10))
    site_b = _site(
        "body-b",
        "surface-b",
        normal=X.scaled(F(-1)),
        half_u=F(5),
        half_v=F(5),
    )
    return (
        _trajectory(
            site_a,
            predecessor_a,
            successor_a,
            predecessor_temperature=temperature_a,
        ),
        _trajectory(
            site_b,
            predecessor_b,
            successor_b,
            predecessor_temperature=temperature_b,
        ),
    )


def test_exact_reciprocal_normal_contact_work_and_heat() -> None:
    a, b = _pair()
    admitted = admit_body_surface_pair(a, b, duration_microseconds=F(100))
    result = settle_admitted_body_surface_contact(admitted)

    assert result.disposition is ContactDisposition.CONTACT
    assert result.contact_area_square_micrometres == 100
    assert result.predecessor_compression_micrometres == 0
    assert result.successor_compression_micrometres == 2
    assert result.predecessor_normal_load_millinewtons == 0
    assert result.successor_normal_load_millinewtons == 200
    assert result.normal_work_into_interface_nanojoules == 200
    assert result.successor_normal_force_on_a_millinewtons == (
        ExactVector3(F(-200), F(0), F(0))
    )
    assert result.successor_normal_force_on_b_millinewtons == (
        ExactVector3(F(200), F(0), F(0))
    )
    assert (
        result.successor_normal_force_on_a_millinewtons
        + result.successor_normal_force_on_b_millinewtons
        == ExactVector3(F(0), F(0), F(0))
    )
    assert result.constant_tangential_force_on_a_millinewtons == (
        ExactVector3(F(0), F(0), F(0))
    )
    assert result.constant_tangential_force_on_b_millinewtons == (
        ExactVector3(F(0), F(0), F(0))
    )
    assert result.conductive_heat_to_a_nanojoules == 100
    assert result.conductive_heat_to_b_nanojoules == -100
    assert (
        result.conductive_heat_to_a_nanojoules
        + result.conductive_heat_to_b_nanojoules
        == 0
    )


def test_exact_tangential_slip_dissipates_work_and_preserves_force_reciprocity() -> None:
    a, b = _pair(
        predecessor_b=(-1, 0, 0),
        successor_b=(-1, 3, 4),
        temperature_a=300_000,
        temperature_b=300_000,
    )
    result = settle_admitted_body_surface_contact(
        admit_body_surface_pair(a, b, duration_microseconds=F(100))
    )

    assert result.disposition is ContactDisposition.CONTACT
    assert result.predecessor_normal_load_millinewtons == 100
    assert result.successor_normal_load_millinewtons == 100
    assert result.normal_work_into_interface_nanojoules == 0
    assert result.tangential_relative_displacement_u_micrometres == 3
    assert result.tangential_relative_displacement_v_micrometres == 4
    assert result.tangential_slip_occurred is True
    assert result.tangential_dissipated_work_nanojoules == 25
    assert result.successor_normal_force_on_b_millinewtons == (
        ExactVector3(F(100), F(0), F(0))
    )
    assert result.successor_normal_force_on_a_millinewtons == (
        ExactVector3(F(-100), F(0), F(0))
    )
    assert result.constant_tangential_force_on_b_millinewtons == (
        ExactVector3(F(0), F(-3), F(-4))
    )
    assert result.constant_tangential_force_on_a_millinewtons == (
        ExactVector3(F(0), F(3), F(4))
    )
    assert result.conductive_heat_to_a_nanojoules == 0
    assert result.conductive_heat_to_b_nanojoules == 0


def test_boundary_to_separation_reports_each_body_physical_contribution() -> None:
    a, b = _pair(
        predecessor_a=(0, 0, 0),
        successor_a=(-3, 0, 0),
        predecessor_b=(0, 0, 0),
        successor_b=(2, 0, 0),
    )
    result = settle_admitted_body_surface_contact(
        admit_body_surface_pair(a, b, duration_microseconds=F(100))
    )

    assert result.disposition is ContactDisposition.SEPARATED
    assert result.predecessor_signed_gap_micrometres == 0
    assert result.successor_signed_gap_micrometres == 5
    assert result.separating_motion_a_micrometres == 3
    assert result.separating_motion_b_micrometres == 2
    assert result.contact_area_square_micrometres == 0
    assert result.successor_normal_force_on_a_millinewtons == (
        ExactVector3(F(0), F(0), F(0))
    )
    assert result.successor_normal_force_on_b_millinewtons == (
        ExactVector3(F(0), F(0), F(0))
    )
    assert result.constant_tangential_force_on_a_millinewtons == (
        ExactVector3(F(0), F(0), F(0))
    )
    assert result.constant_tangential_force_on_b_millinewtons == (
        ExactVector3(F(0), F(0), F(0))
    )
    assert result.normal_work_into_interface_nanojoules == 0
    assert result.tangential_dissipated_work_nanojoules == 0
    assert result.tangential_slip_occurred is False

    field_names = {field.name for field in fields(result)}
    assert "consent" not in field_names
    assert "meaning" not in field_names
    assert "action_name" not in field_names


def test_same_exact_input_repeats_byte_for_byte_equivalent_facts() -> None:
    a, b = _pair(
        predecessor_b=(-1, 0, 0),
        successor_b=(-1, 2, 0),
    )
    admitted = admit_body_surface_pair(a, b, duration_microseconds=F(125))

    assert settle_admitted_body_surface_contact(admitted) == (
        settle_admitted_body_surface_contact(admitted)
    )


def test_swapping_surface_order_preserves_the_same_reciprocal_physics() -> None:
    a, b = _pair(
        predecessor_b=(-1, 0, 0),
        successor_b=(-1, 2, 0),
    )
    forward = settle_admitted_body_surface_contact(
        admit_body_surface_pair(a, b, duration_microseconds=F(100))
    )
    reverse = settle_admitted_body_surface_contact(
        admit_body_surface_pair(b, a, duration_microseconds=F(100))
    )

    assert reverse.contact_area_square_micrometres == (
        forward.contact_area_square_micrometres
    )
    assert reverse.successor_normal_load_millinewtons == (
        forward.successor_normal_load_millinewtons
    )
    assert reverse.successor_normal_force_on_a_millinewtons == (
        forward.successor_normal_force_on_b_millinewtons
    )
    assert reverse.successor_normal_force_on_b_millinewtons == (
        forward.successor_normal_force_on_a_millinewtons
    )
    assert reverse.constant_tangential_force_on_a_millinewtons == (
        forward.constant_tangential_force_on_b_millinewtons
    )
    assert reverse.constant_tangential_force_on_b_millinewtons == (
        forward.constant_tangential_force_on_a_millinewtons
    )
    assert reverse.conductive_heat_to_a_nanojoules == (
        forward.conductive_heat_to_b_nanojoules
    )
    assert reverse.conductive_heat_to_b_nanojoules == (
        forward.conductive_heat_to_a_nanojoules
    )
    assert reverse.tangential_dissipated_work_nanojoules == (
        forward.tangential_dissipated_work_nanojoules
    )


def test_contact_crossing_must_be_segmented_at_zero_gap() -> None:
    a, b = _pair(predecessor_b=(1, 0, 0), successor_b=(-1, 0, 0))

    with pytest.raises(ValueError, match="split at zero gap"):
        admit_body_surface_pair(a, b, duration_microseconds=F(100))


def test_changing_partial_patch_must_be_segmented() -> None:
    a, b = _pair(
        predecessor_b=(-1, 0, 0),
        successor_b=(-1, 8, 0),
    )

    with pytest.raises(ValueError, match="contact-patch boundary"):
        admit_body_surface_pair(a, b, duration_microseconds=F(100))


@pytest.mark.parametrize(
    "change, message",
    (
        ("same_body", "distinct bodies"),
        ("same_normal", "exactly opposed"),
        ("non_unit_basis", "exact unit vector"),
        ("zero_coefficient", "must be positive"),
    ),
)
def test_admission_rejects_missing_physical_anatomy(
    change: str,
    message: str,
) -> None:
    a, b = _pair()
    if change == "same_body":
        b = BodySurfaceTrajectory(
            site=RectangularBodySurfaceSite(
                body_id=a.site.body_id,
                site_id=b.site.site_id,
                outward_normal=b.site.outward_normal,
                tangent_u=b.site.tangent_u,
                tangent_v=b.site.tangent_v,
                half_extent_u_micrometres=b.site.half_extent_u_micrometres,
                half_extent_v_micrometres=b.site.half_extent_v_micrometres,
                material=b.site.material,
            ),
            predecessor=b.predecessor,
            successor=b.successor,
        )
    elif change == "same_normal":
        b = BodySurfaceTrajectory(
            site=RectangularBodySurfaceSite(
                body_id=b.site.body_id,
                site_id=b.site.site_id,
                outward_normal=a.site.outward_normal,
                tangent_u=b.site.tangent_u,
                tangent_v=b.site.tangent_v,
                half_extent_u_micrometres=b.site.half_extent_u_micrometres,
                half_extent_v_micrometres=b.site.half_extent_v_micrometres,
                material=b.site.material,
            ),
            predecessor=b.predecessor,
            successor=b.successor,
        )
    elif change == "non_unit_basis":
        a = BodySurfaceTrajectory(
            site=RectangularBodySurfaceSite(
                body_id=a.site.body_id,
                site_id=a.site.site_id,
                outward_normal=ExactVector3(F(2), F(0), F(0)),
                tangent_u=a.site.tangent_u,
                tangent_v=a.site.tangent_v,
                half_extent_u_micrometres=a.site.half_extent_u_micrometres,
                half_extent_v_micrometres=a.site.half_extent_v_micrometres,
                material=a.site.material,
            ),
            predecessor=a.predecessor,
            successor=a.successor,
        )
    else:
        a = BodySurfaceTrajectory(
            site=RectangularBodySurfaceSite(
                body_id=a.site.body_id,
                site_id=a.site.site_id,
                outward_normal=a.site.outward_normal,
                tangent_u=a.site.tangent_u,
                tangent_v=a.site.tangent_v,
                half_extent_u_micrometres=a.site.half_extent_u_micrometres,
                half_extent_v_micrometres=a.site.half_extent_v_micrometres,
                material=_material(stiffness=F(0)),
            ),
            predecessor=a.predecessor,
            successor=a.successor,
        )

    with pytest.raises((TypeError, ValueError), match=message):
        admit_body_surface_pair(a, b, duration_microseconds=F(100))


def test_duration_and_coefficients_are_required_exact_fractions() -> None:
    a, b = _pair()
    with pytest.raises(TypeError, match="exact Fraction"):
        admit_body_surface_pair(a, b, duration_microseconds=100)  # type: ignore[arg-type]

    invalid_site = _site(
        "body-c",
        "surface-c",
        normal=X,
        half_u=F(1),
        half_v=F(1),
        material=BodySurfaceMaterial(
            normal_stiffness_millinewtons_per_micrometre_per_square_micrometre=F(1),
            tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre=F(1),
            thermal_conductance_nanowatts_per_square_micrometre_millikelvin=(
                1  # type: ignore[arg-type]
            ),
        ),
    )
    invalid = _trajectory(invalid_site, (0, 0, 0), (0, 0, 0))
    with pytest.raises(TypeError, match="exact Fraction"):
        admit_body_surface_pair(invalid, b, duration_microseconds=F(100))


def test_admission_custody_and_exact_width_are_bounded() -> None:
    a, b = _pair()
    admitted = admit_body_surface_pair(a, b, duration_microseconds=F(100))
    with pytest.raises(ValueError, match="admission custody"):
        settle_admitted_body_surface_contact(
            replace(admitted, _construction_authority=object())
        )

    overwide = F(1 << 256)
    with pytest.raises(ValueError, match="rational bit boundary"):
        admit_body_surface_pair(a, b, duration_microseconds=overwide)


def test_explicit_zero_damping_and_conductance_are_physical_not_missing() -> None:
    material = _material(damping=F(0), conductance=F(0))
    site_a = _site(
        "body-a",
        "surface-a",
        normal=X,
        half_u=F(10),
        half_v=F(10),
        material=material,
    )
    site_b = _site(
        "body-b",
        "surface-b",
        normal=X.scaled(F(-1)),
        half_u=F(5),
        half_v=F(5),
        material=material,
    )
    a = _trajectory(site_a, (0, 0, 0), (0, 0, 0), predecessor_temperature=300_000)
    b = _trajectory(site_b, (-1, 0, 0), (-1, 2, 0), predecessor_temperature=310_000)

    result = settle_admitted_body_surface_contact(
        admit_body_surface_pair(a, b, duration_microseconds=F(100))
    )

    assert result.tangential_slip_occurred is True
    assert result.tangential_dissipated_work_nanojoules == 0
    assert result.conductive_heat_to_a_nanojoules == 0
    assert result.conductive_heat_to_b_nanojoules == 0
