from __future__ import annotations

from fractions import Fraction

import pytest

from dsf_ai_service.guala_external_rgb_retina import (
    EXTERNAL_RGB_RETINAL_PORTS,
    external_rgb_retina_admissions,
    rgb_retina_luminance_u8,
    settle_external_rgb_retina,
    transmitted_rgb_retina_u8,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    RETINA_TOTAL_RECEPTOR_COUNT,
)


SOURCE_TIMES = tuple(
    Fraction(index, 16_000) for index in range(0, 4_001, 160)
)
RGB = tuple(
    value
    for site in range(RETINA_TOTAL_RECEPTOR_COUNT)
    for value in (site % 256, (site * 3) % 256, (site * 7) % 256)
)


def test_external_rgb_retina_preserves_three_channels_per_spatial_site() -> None:
    episode = settle_external_rgb_retina(
        assembly_id="test-external-RGB-retina",
        rgb_u8=RGB,
        source_times=SOURCE_TIMES,
        transmission=Fraction(1),
    )

    assert episode.port_count == EXTERNAL_RGB_RETINAL_PORTS == 810
    assert episode.source_sample_count == 810 * len(SOURCE_TIMES)
    assert episode.occurrence_count == RETINA_TOTAL_RECEPTOR_COUNT == 135
    assert episode.occurrence_frame_count == 135 * len(SOURCE_TIMES)
    assert episode.python_callback_count == 0
    assert len(external_rgb_retina_admissions(Fraction(1, 4))) == 135


def test_external_rgb_retina_retains_luminance_continuity_and_eyelids() -> None:
    primary = (255, 0, 0, 0, 255, 0, 0, 0, 255) * 45
    assert rgb_retina_luminance_u8(primary)[:3] == (76, 150, 29)
    assert transmitted_rgb_retina_u8(primary, Fraction(1, 2))[:3] == (
        128,
        0,
        0,
    )
    assert transmitted_rgb_retina_u8(primary, Fraction(0)) == (0,) * 405

    for invalid in (primary[:-1], primary + (0,), (0,) * 404 + (256,)):
        with pytest.raises(ValueError):
            settle_external_rgb_retina(
                assembly_id="test-invalid-external-RGB-retina",
                rgb_u8=invalid,
                source_times=SOURCE_TIMES,
                transmission=Fraction(1),
            )
