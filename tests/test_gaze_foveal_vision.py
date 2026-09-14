"""Tests for 20/20 foveal vision crop, exact rational resampling, and saccadic gaze tracking."""

from __future__ import annotations

import base64
import json
import math

import pytest

from dsf_ai_service.guala_vision_fovea import (
    FOCAL_COLUMNS,
    FOCAL_ROWS,
    FOCAL_RGB_COUNT,
    FOCAL_SITE_COUNT,
    compute_saccadic_gaze,
    focal_rgb_to_luminance,
    resample_focal_crop_rgb,
)
from dsf_ai_service.lean_production_app import (
    MAX_OCCURRENCE_BODY_BYTES,
    OccurrenceBody,
    _physical_occurrence,
)
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence


def test_exact_rational_box_filter_preserves_uniform_color() -> None:
    """Every output site must receive the exact uniform value under area weighting."""
    for (w, h) in ((80, 60), (64, 48), (32, 24)):
        data = bytes([177, 88, 42] * (w * h))
        res = resample_focal_crop_rgb(data, w, h)
        assert len(res) == FOCAL_RGB_COUNT
        for i in range(0, len(res), 3):
            assert res[i] == 177
            assert res[i + 1] == 88
            assert res[i + 2] == 42


def test_box_filter_channel_isolation() -> None:
    """R, G, B channels must not cross-bleed during resampling."""
    data = bytearray(80 * 60 * 3)
    for i in range(80 * 60):
        data[i * 3] = 255  # only red
    res = resample_focal_crop_rgb(data, 80, 60)
    for i in range(0, len(res), 3):
        assert res[i] == 255
        assert res[i + 1] == 0
        assert res[i + 2] == 0


def test_focal_luminance_projection() -> None:
    """768 RGB sites project onto 768 achromatic luminance receptors."""
    rgb = tuple([255, 255, 255] * FOCAL_SITE_COUNT)
    lum = focal_rgb_to_luminance(rgb)
    assert len(lum) == FOCAL_SITE_COUNT
    assert all(v == 255 for v in lum)


def test_saccadic_gaze_smooth_tracking() -> None:
    """Gaze tracking within crop must move smoothly in frame coordinates without jumping."""
    origin = (0.5, 0.5)
    # Bright feature on the far right of the crop patch (gx = 0.95)
    gaze_focal = (0.95, 0.5)
    crop_fraction = (80 / 640, 60 / 480)  # 0.125, 0.125
    next_gaze = compute_saccadic_gaze(origin, gaze_focal, crop_fraction, max_saccade=0.08)

    # Must move rightwards, but strictly bounded (no jump to 0.95!)
    assert next_gaze[0] > 0.5
    assert next_gaze[0] <= 0.5 + 0.08
    assert next_gaze[1] == 0.5  # no vertical displacement
    # Exact shift: (0.95 - 0.5) * 0.125 = 0.05625
    assert math.isclose(next_gaze[0], 0.5562, abs_tol=1e-3)


def test_occurrence_payload_with_focal_base64_crop_fits_byte_bound() -> None:
    """80x60 base64 crop + 8000 B audio + legacy retina must strictly obey 34,816 bytes."""
    pcm = bytes([0] * 8000)
    crop_rgb = bytes([128] * (80 * 60 * 3))
    legacy_retina = tuple([128] * 405)

    payload_dict = {
        "kind": "sensory",
        "payload": {
            "source": "camera-microphone",
            "retina_rgb_u8": legacy_retina,
            "pcm_s16le_base64": base64.b64encode(pcm).decode("ascii"),
            "focal_rgb_base64": base64.b64encode(crop_rgb).decode("ascii"),
            "focal_origin": [0.5, 0.5],
            "focal_pitch_millidegrees": [94, 94],
            "focal_crop_dimensions": [80, 60],
        },
    }
    raw_json = json.dumps(payload_dict).encode("utf-8")
    assert len(raw_json) < MAX_OCCURRENCE_BODY_BYTES, f"payload size {len(raw_json)} exceeded {MAX_OCCURRENCE_BODY_BYTES}"

    body = OccurrenceBody.model_validate_json(raw_json)
    occurrence = _physical_occurrence(body)
    assert occurrence.kind == "sensory"
    sensory = occurrence.payload
    assert isinstance(sensory, LeanSensoryOccurrence)
    assert sensory.focal_origin == (0.5, 0.5)
    assert sensory.focal_pitch_millidegrees == (94, 94)
    assert sensory.focal_crop_dimensions == (80, 60)
    assert len(sensory.retina_rgb_u8) == 405 + FOCAL_RGB_COUNT
    assert len(sensory.pressure_s16le) == 8000


def test_optical_resolution_covers_card_and_letters() -> None:
    """At 500 mm distance, 80x60 native crop covers ~72x54 mm, containing flashcard glyphs."""
    fov_horizontal_deg = 60.0
    distance_mm = 500.0
    full_frame_width_mm = 2.0 * distance_mm * math.tan(math.radians(fov_horizontal_deg / 2.0))
    mm_per_pixel = full_frame_width_mm / 640.0  # ~0.902 mm/px

    crop_width_mm = 80 * mm_per_pixel
    crop_height_mm = 60 * mm_per_pixel
    assert 65.0 < crop_width_mm < 80.0
    assert 48.0 < crop_height_mm < 60.0

    # A 12 mm letter spans ~13 native sensor pixels
    letter_height_mm = 12.0
    letter_pixels = letter_height_mm / mm_per_pixel
    assert 12.0 < letter_pixels < 15.0

