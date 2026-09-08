from __future__ import annotations

from fractions import Fraction

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_spectral_retina import (
    SPECTRAL_RETINAL_PORTS,
    settle_spectral_retina,
    spectral_retina_admissions,
    spectral_retina_u8_observation,
)
from dsf_ai_service.guala_world_sensorium import passive_receptor_capture
from dsf_ai_service.substrate.w1_physical_receptors import (
    RETINAL_SITE_GEOMETRY,
    RETINA_COLUMNS,
    RETINA_FINE_COLUMNS,
    RETINA_FINE_RECEPTOR_COUNT,
    RETINA_RECEPTOR_COUNT,
)


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
BODY_AXES = (
    (0, "neck_yaw", "millidegree", 0, -75_000, 0, 75_000),
    (1, "left_eyelid_aperture", "micrometre", 10_000, 0, 10_000, 12_000),
    (2, "right_eyelid_aperture", "micrometre", 10_000, 0, 10_000, 12_000),
)
SOURCE_TIMES = tuple(
    Fraction(index, 16_000) for index in range(0, 4_001, 160)
)


def test_world_retina_retains_every_spectral_band_as_an_independent_port() -> None:
    world = home_world_authority(identity=IDENTITY)
    capture = passive_receptor_capture(
        snapshot=world.observation_snapshot(),
        body_axes=BODY_AXES,
    )
    episode = settle_spectral_retina(
        assembly_id="test-lean-six-band-retina",
        streams=capture[0][PhysicalSense.SIGHT],
        source_times=SOURCE_TIMES,
        before_transmission=capture[1],
    )

    assert episode.port_count == SPECTRAL_RETINAL_PORTS == 810
    assert episode.source_sample_count == 810 * len(SOURCE_TIMES)
    assert episode.occurrence_count == 135
    assert episode.occurrence_frame_count == 135 * len(SOURCE_TIMES)
    assert episode.python_callback_count == 0
    assert len(spectral_retina_admissions(Fraction(1, 4))) == 135
    observation = spectral_retina_u8_observation(
        streams=capture[0][PhysicalSense.SIGHT],
        transmission=capture[1],
    )
    assert len(observation) == 810
    assert all(0 <= value <= 255 for value in observation)


def test_coarse_and_fine_retinal_fields_are_centered_and_cover_180_degrees() -> None:
    coarse = RETINAL_SITE_GEOMETRY[:RETINA_RECEPTOR_COUNT]
    fine = RETINAL_SITE_GEOMETRY[
        RETINA_RECEPTOR_COUNT:
        RETINA_RECEPTOR_COUNT + RETINA_FINE_RECEPTOR_COUNT
    ]

    for field, columns in ((coarse, RETINA_COLUMNS), (fine, RETINA_FINE_COLUMNS)):
        first_row = field[:columns]
        centers = tuple(site[1] for site in first_row)
        half_widths = tuple(site[3] for site in first_row)
        assert len(set(half_widths)) == 1
        half_width = half_widths[0]
        assert centers[0] - half_width == -90_000
        assert centers[-1] + half_width == 90_000
        assert tuple(reversed(tuple(-value for value in centers))) == centers
        assert all(
            right - left == 2 * half_width
            for left, right in zip(centers, centers[1:])
        )
