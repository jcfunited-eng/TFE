"""Approved physical teaching surfaces placed in the W1 environment.

This module is external-world configuration, not cognition.  It retains only
neutral physical object identities, placement, paper material, and exact
palette-indexed reflectance.  The visual receptor boundary strips object
identity and transduces only light from the surface.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dsf_ai_service.substrate.embodiment_world import (
    ODORANT_CHANNELS,
    TASTANT_CHANNELS,
    EmbodiedObject,
    ObjectMaterialState,
    PositionMM,
)
from dsf_ai_service.substrate.physical_optical_surface_asset import (
    physical_optical_surface_from_png,
)


_ASSET_ROOT = Path(__file__).resolve().parents[2] / "guala_curriculum/cards"
_APPROVED_ALPHABET_ASSET_NAMES = (
    "alphabet-a-apple-v1.png",
    "alphabet-b-bee-v1.png",
    "C-is-for-Cat.png",
    "D-is-for-Dolphin.png",
    "E-is-for-Elephant.png",
    "F-is-for-Fox.png",
    "G-is-for-Giraffe.png",
    "H-is-for-House.png",
    "I-is-for-Ice-Cream.png",
    "J-is-for-Jellyfish.png",
    "K-is-for-Kite.png",
    "L-is-for-Lion.png",
    "M-is-for-Mushroom.png",
    "N-is-for-Nest.png",
    "O-is-for-Owl.png",
    "P-is-for-Penguin.png",
    "Q-is-for-Queen.png",
    "R-is-for-Rabbit.png",
    "S-is-for-Snail.png",
    "T-is-for-Turtle.png",
    "U-is-for-Umbrella.png",
    "V-is-for-Violin.png",
    "W-is-for-Whale.png",
    "X-is-for-Xylophone.png",
    "Y-is-for-Yak.png",
    "Z-is-for-Zebra.png",
)

# These reviewed surfaces contain exactly N countable objects, one numeral,
# and one written number word on plain cream.  Their file names remain only at
# the external-world construction boundary and never enter a receptor field.
_APPROVED_NUMBER_ASSET_NAMES = (
    "number-01-one-v1.png",
    "number-02-two-v1.png",
    "number-03-three-v1.png",
    "number-04-four-v1.png",
    "number-05-five-v1.png",
    "number-06-six-v1.png",
    "number-07-seven-v1.png",
    "number-08-eight-v1.png",
    "number-09-nine-v1.png",
    "number-10-ten-v1.png",
)

# Zero was approved after the original 60 surface identities were already
# persistent.  It therefore keeps a new object identity and placement instead
# of renumbering or reinterpreting any lived surface.
_APPROVED_ZERO_ASSET_NAMES = (
    "number-00-zero-v1.png",
)

# THE FIRST WORDS SHE IS TAUGHT. Each reviewed surface carries one word
# in plain letters on cream, and its picture, exactly as the alphabet and
# number surfaces do. They were added to her curriculum and NEVER added
# here, so they were never approved and never shipped — every one of these
# lessons refused in production with a missing file. Approval is the gate
# on what may physically reach her eyes; a surface that is not on this
# list must not reach her, and a surface she is offered must be on it.
_APPROVED_WORD_ASSET_NAMES = (
    "word-mama-v1.png",
    "word-dada-v1.png",
    "word-ball-v1.png",
    "word-cup-v1.png",
    "word-dog-v1.png",
    "word-cat-v1.png",
    "word-sun-v1.png",
    "word-moon-v1.png",
    "word-tree-v1.png",
    "word-water-v1.png",
    "word-milk-v1.png",
    "word-shoe-v1.png",
    "word-hand-v1.png",
    "word-eye-v1.png",
    "word-book-v1.png",
    "word-car-v1.png",
    "word-bed-v1.png",
    "word-door-v1.png",
    "word-apple-v1.png",
    "word-banana-v1.png",
    "word-chair-v1.png",
    "word-hat-v1.png",
    "word-fish-v1.png",
    "word-bird-v1.png",
)

_APPROVED_SURFACE_PLACEMENTS = tuple(
    (
        f"W1-optical-surface-{index:02d}",
        _ASSET_ROOT / asset_name,
        PositionMM(
            (
                5_300 + 700 * (index - 47)
                if index > 46
                else 6_200 + 700 * (index - 27)
                if index > 26
                else 5_500 + 700 * (index - 1)
                if index <= 14
                else (
                    15_500 + 700 * (index - 15)
                    if index <= 21
                    else 500 + 700 * (index - 22)
                )
            ),
            1_800 if index > 46 else 2_500 if index > 26 else 4_500,
            0,
        ),
    )
    for index, asset_name in enumerate(
        _APPROVED_ALPHABET_ASSET_NAMES
        + _APPROVED_NUMBER_ASSET_NAMES
        + _APPROVED_WORD_ASSET_NAMES,
        1,
    )
) + (
    (
        "W1-optical-surface-61",
        _ASSET_ROOT / _APPROVED_ZERO_ASSET_NAMES[0],
        PositionMM(15_700, 1_800, 0),
    ),
)


def _paper_material() -> ObjectMaterialState:
    return ObjectMaterialState(
        odorant_reservoir_nanograms=(0,) * ODORANT_CHANNELS,
        odorant_release_nanograms_per_second=(0,) * ODORANT_CHANNELS,
        tastant_mass_micrograms=(0,) * TASTANT_CHANNELS,
        surface_temperature_millikelvin=295_000,
        compliance_ppm=80_000,
        roughness_micrometers=35,
        moisture_ppm=35_000,
    )


@lru_cache(maxsize=1)
def approved_curriculum_physical_surfaces() -> tuple[EmbodiedObject, ...]:
    """Return the exact reviewed surfaces without semantic receptor fields."""

    result = []
    for object_id, path, position in _APPROVED_SURFACE_PLACEMENTS:
        try:
            png_bytes = path.read_bytes()
        except OSError as error:
            raise RuntimeError(
                "approved physical curriculum surface is unavailable"
            ) from error
        asset = physical_optical_surface_from_png(
            png_bytes,
            columns=56,
            rows=70,
        )
        result.append(
            EmbodiedObject(
                object_id=object_id,
                radius_mm=300,
                mass_grams=20,
                position=position,
                reflectance_ppm=(
                    asset.surface.palette_reflectance_ppm[0]
                ),
                material=_paper_material(),
                optical_surface=asset.surface,
            )
        )
    surfaces = tuple(result)
    if (
        len(surfaces) != len(_APPROVED_SURFACE_PLACEMENTS)
        or len({surface.object_id for surface in surfaces}) != len(surfaces)
    ):
        raise RuntimeError("approved physical surface inventory changed")
    for surface in surfaces:
        surface.verify()
    return surfaces


__all__ = ("approved_curriculum_physical_surfaces",)
