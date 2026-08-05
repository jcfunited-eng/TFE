from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedObject,
    EmbodimentWorldAuthority,
    PositionMM,
)
from dsf_ai_service.substrate.physical_optical_surface_asset import (
    physical_optical_surface_from_png,
)
from dsf_ai_service.substrate.w1_physical_foveal_observation import (
    PhysicalFovealObservationAuthority,
    successive_surface_patch_fixation_sequences,
)


ROOT = Path(__file__).resolve().parents[1]
A_PATH = ROOT / "guala_curriculum/cards/alphabet-a-apple-v1.png"
B_PATH = ROOT / "guala_curriculum/cards/alphabet-b-bee-v1.png"
KEY = b"physical-optical-surface-asset-test-key"


def _fields(result) -> tuple[tuple[tuple[object, ...], ...], ...]:
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=(
            f"test-optical-asset-"
            f"{result.scan_plan.authority_receipt_sha256}"
        ),
        source_time_start=result.scan_plan.source_time_start,
        source_time_end=result.scan_plan.source_time_end,
        observed_substreams={
            PhysicalSense.SIGHT: result.physical_substreams,
        },
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SIGHT
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
        occurrences=result.joint_source_occurrences(),
    )
    sight = next(
        boundary
        for boundary in built.boundary.boundaries
        if boundary.sense is PhysicalSense.SIGHT
    )
    return tuple(
        tuple(
            field_tuple.as_tuple()
            for field_tuple in substream.kernel_basin.exact_dsf_field_tuples
        )
        for substream in sight.substreams
    )


def _first_patch_fields(png_path: Path):
    asset = physical_optical_surface_from_png(png_path.read_bytes())
    world = EmbodimentWorldAuthority(
        authority_key=KEY,
        initial_objects=(
            EmbodiedObject(
                object_id="neutral-physical-surface",
                radius_mm=300,
                mass_grams=20,
                position=PositionMM(5_400, 1_000, 0),
                reflectance_ppm=asset.surface.palette_reflectance_ppm[0],
                optical_surface=asset.surface,
            ),
        ),
    )
    observation = world.observation_snapshot()
    target = observation.objects[0]
    patches = successive_surface_patch_fixation_sequences(
        asset.surface,
        patch_rows=32,
        patch_columns=32,
    )
    authority = PhysicalFovealObservationAuthority(authority_key=KEY)
    plan = authority.authorize_scan(
        observation,
        target_object_id=target.object_id,
        fixations=patches[0],
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, len(patches)),
    )
    observed = authority.observe(observation, scan_plan=plan)
    return asset, observed, _fields(observed)


def test_approved_a_and_b_cards_become_distinct_physical_full_fields():
    a_asset, a_observed, a_fields = _first_patch_fields(A_PATH)
    b_asset, b_observed, b_fields = _first_patch_fields(B_PATH)

    assert a_asset.source_png_sha256 != b_asset.source_png_sha256
    assert a_asset.surface_sha256 != b_asset.surface_sha256
    assert a_fields != b_fields
    assert DSF_FIELD_ORDER == (
        "D_k",
        "M_k",
        "R_rev_k",
        "U_star_k",
        "C_k",
        "P_k",
        "B_k",
    )
    assert len(a_observed.physical_substreams) == 6
    assert len(b_observed.physical_substreams) == 6
    receptor_text = (
        repr(a_observed.physical_substreams)
        + repr(b_observed.physical_substreams)
    ).lower()
    assert "apple" not in receptor_text
    assert "bee" not in receptor_text
    assert "alphabet" not in receptor_text
    assert "png" not in receptor_text


def test_png_import_is_exactly_repeatable_and_cold_restorable():
    png = A_PATH.read_bytes()
    first = physical_optical_surface_from_png(png)
    second = physical_optical_surface_from_png(png)
    assert first == second

    world = EmbodimentWorldAuthority(
        authority_key=KEY,
        initial_objects=(
            EmbodiedObject(
                object_id="neutral-physical-surface",
                radius_mm=300,
                mass_grams=20,
                position=PositionMM(5_400, 1_000, 0),
                reflectance_ppm=first.surface.palette_reflectance_ppm[0],
                optical_surface=first.surface,
            ),
        ),
    )
    encoded = world.encoded_snapshot()
    cold = EmbodimentWorldAuthority(authority_key=KEY)
    cold.restore_encoded(encoded)
    assert cold.encoded_snapshot() == encoded
    assert cold.observation_snapshot().objects[0].optical_surface == (
        first.surface
    )


def test_png_import_rejects_non_png_and_out_of_bounds_dimensions():
    with pytest.raises(ValueError, match="PNG"):
        physical_optical_surface_from_png(b"not a PNG")
    with pytest.raises(ValueError, match="columns"):
        physical_optical_surface_from_png(
            A_PATH.read_bytes(),
            columns=129,
        )


def test_verified_optical_surface_rejects_post_construction_change():
    asset = physical_optical_surface_from_png(A_PATH.read_bytes())
    surface = asset.surface
    object.__setattr__(
        surface,
        "cell_palette_indices",
        tuple(reversed(surface.cell_palette_indices)),
    )

    with pytest.raises(
        ValueError,
        match="changed after verified construction",
    ):
        surface.verify()
