"""Deterministic foveal vision geometry and rational optical resampling.

Maps native camera foveal crops onto Guala's canonical
4800 focal sites (80x60) via exact integer area-weighted box filtering.
Calculates bounded saccadic gaze tracking in camera frame coordinates.
"""

from __future__ import annotations

import math
from typing import Sequence

FOCAL_COLUMNS: int = 80
FOCAL_ROWS: int = 60
FOCAL_SITE_COUNT: int = FOCAL_COLUMNS * FOCAL_ROWS  # 4800 sites
FOCAL_RGB_COUNT: int = FOCAL_SITE_COUNT * 3          # 14400 values
DEFAULT_MAX_SACCADE: float = 0.08                   # max frame fraction shift per beat


def resample_focal_crop_rgb(
    crop_rgb: Sequence[int] | bytes,
    in_w: int,
    in_h: int,
    out_w: int = FOCAL_COLUMNS,
    out_h: int = FOCAL_ROWS,
) -> tuple[int, ...]:
    """Resample an arbitrary native rectangular RGB crop onto out_w x out_h sites
    using exact integer area-weighted box integration. Zero floating point rounding."""

    if in_w < out_w or in_h < out_h:
        raise ValueError(f"crop dimensions ({in_w}x{in_h}) smaller than focal grid ({out_w}x{out_h})")
    expected_bytes = in_w * in_h * 3
    if len(crop_rgb) != expected_bytes:
        raise ValueError(f"expected {expected_bytes} RGB bytes for {in_w}x{in_h}, got {len(crop_rgb)}")

    if in_w == out_w and in_h == out_h:
        return tuple(crop_rgb)

    out: list[int] = []
    total_area = in_w * in_h
    for oy in range(out_h):
        y0 = oy * in_h
        y1 = (oy + 1) * in_h
        iy_min = y0 // out_h
        iy_max = (y1 + out_h - 1) // out_h
        for ox in range(out_w):
            x0 = ox * in_w
            x1 = (ox + 1) * in_w
            ix_min = x0 // out_w
            ix_max = (x1 + out_w - 1) // out_w
            r_sum = 0
            g_sum = 0
            b_sum = 0
            for iy in range(iy_min, iy_max):
                wy = min(y1, (iy + 1) * out_h) - max(y0, iy * out_h)
                for ix in range(ix_min, ix_max):
                    wx = min(x1, (ix + 1) * out_w) - max(x0, ix * out_w)
                    w = wx * wy
                    idx = (iy * in_w + ix) * 3
                    r_sum += crop_rgb[idx] * w
                    g_sum += crop_rgb[idx + 1] * w
                    b_sum += crop_rgb[idx + 2] * w
            out.extend([
                (r_sum + total_area // 2) // total_area,
                (g_sum + total_area // 2) // total_area,
                (b_sum + total_area // 2) // total_area,
            ])
    return tuple(out)


def focal_rgb_to_luminance(focal_rgb: Sequence[int]) -> tuple[int, ...]:
    """Convert 4800 RGB focal sites (14400 values) to 4800 achromatic luminance values."""
    if len(focal_rgb) != FOCAL_RGB_COUNT:
        raise ValueError(f"expected {FOCAL_RGB_COUNT} RGB values, got {len(focal_rgb)}")
    return tuple(
        (focal_rgb[i] * 299 + focal_rgb[i + 1] * 587 + focal_rgb[i + 2] * 114 + 500) // 1000
        for i in range(0, len(focal_rgb), 3)
    )


def compute_saccadic_gaze(
    focal_origin: tuple[float, float],
    gaze_focal: tuple[float, float],
    crop_fraction: tuple[float, float],
    max_saccade: float = DEFAULT_MAX_SACCADE,
) -> tuple[float, float]:
    """Compute frame-relative gaze target from crop origin and focal field centroid,
    bounded by a maximum saccadic displacement to prevent jumps across the frame."""

    fx, fy = focal_origin
    gx, gy = gaze_focal
    cw, ch = crop_fraction

    # Offset within the focal patch relative to patch center (0.5, 0.5)
    dx = (gx - 0.5) * cw
    dy = (gy - 0.5) * ch

    # Target frame coordinate
    tx = max(0.0, min(1.0, fx + dx))
    ty = max(0.0, min(1.0, fy + dy))

    # Bound by maximum saccade from current origin
    step_x = max(-max_saccade, min(max_saccade, tx - fx))
    step_y = max(-max_saccade, min(max_saccade, ty - fy))

    return (
        round(max(0.0, min(1.0, fx + step_x)), 4),
        round(max(0.0, min(1.0, fy + step_y)), 4),
    )


__all__ = (
    "FOCAL_COLUMNS",
    "FOCAL_ROWS",
    "FOCAL_SITE_COUNT",
    "FOCAL_RGB_COUNT",
    "compute_saccadic_gaze",
    "focal_rgb_to_luminance",
    "resample_focal_crop_rgb",
)
