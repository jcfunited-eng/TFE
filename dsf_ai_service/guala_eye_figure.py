"""The eye's Level 1: the figure under her gaze (docs/GL-SPC-EYE-FIGURE-C1-20260915-v1.md, §7 as built).

A thing seen as one discrete structure. On her world eye the thing's silhouette is the
world's own geometry (the disc of its angular radius at the place her gaze law projects),
and its identity is its look read as a radial profile: the light in three rings from the
disc's centre to its rim, each in quarters of the disc's own range. Level-free (its own
range), size-free (rings scale with the disc), and rotation-free (rings do not turn as she
walks round a thing). Measured 2026-09-15: the same thing at two distances gives one key
(4 of 4 things), four things give four keys, the dominant key holds on 79 to 100 percent of
the beats a thing is under her gaze; sectors and finer grids were measured unstable at her
retina's three quarters of a degree a site. Pure functions; nothing named, matched or
learned. The declared numbers are stated once below. Supports both 3-channel RGB and
achromatic single-channel focal fields.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

FOCAL_COLUMNS = 160
FOCAL_ROWS = 120
LOOK_RINGS = 3         # centre, middle, rim (declared once)
LOOK_LEVELS = 4        # each ring's light in quarters of the disc's own range (level-free)
MIN_RADIUS_SITES = 4   # scaled with 2x finer pitch (375 mdeg, was 2 at 750 mdeg)


@dataclass(frozen=True, slots=True)
class Figure:
    key: str                          # sha-256 (16 hex) of the look
    look: tuple[int, ...]             # the rings' light in quarters, centre to rim (3 quarters for mono, 9 for RGB)
    sites: int                        # how many sites the disc holds in the field
    centre: tuple[float, float]       # the disc's centre as fractions of the field
    radius_sites: float               # its angular radius in sites

    @property
    def extent(self) -> float:
        return self.sites / float(FOCAL_COLUMNS * FOCAL_ROWS)


def figure_of_disc(focal: Sequence[int], centre: tuple[float, float], radius_sites: float) -> Figure | None:
    """The figure of the thing under her gaze: its disc at the projected centre (fractions
    of the field) with its angular radius in sites; None when the disc is too small or lies
    outside the field."""

    is_rgb = len(focal) == FOCAL_COLUMNS * FOCAL_ROWS * 3
    if not is_rgb and len(focal) != FOCAL_COLUMNS * FOCAL_ROWS:
        return None
    if radius_sites < MIN_RADIUS_SITES:
        return None
    cx = float(centre[0]) * (FOCAL_COLUMNS - 1)
    cy = float(centre[1]) * (FOCAL_ROWS - 1)
    r2 = radius_sites * radius_sites
    # A look needs the whole disc in the field: a thing cut by the field's edge has no complete look.
    if cx - radius_sites < 0 or cx + radius_sites > FOCAL_COLUMNS - 1 or cy - radius_sites < 0 or cy + radius_sites > FOCAL_ROWS - 1:
        return None
    x0, x1 = int(cx - radius_sites), int(cx + radius_sites) + 1
    y0, y1 = int(cy - radius_sites), int(cy + radius_sites) + 1
    if is_rgb:
        sums_r = [0] * LOOK_RINGS
        sums_g = [0] * LOOK_RINGS
        sums_b = [0] * LOOK_RINGS
        counts = [0] * LOOK_RINGS
        for row in range(y0, y1 + 1):
            dy = row - cy
            for column in range(x0, x1 + 1):
                dx = column - cx
                d2 = dx * dx + dy * dy
                if d2 > r2:
                    continue
                ring = min(LOOK_RINGS - 1, int((d2 ** 0.5) / radius_sites * LOOK_RINGS))
                idx = (row * FOCAL_COLUMNS + column) * 3
                sums_r[ring] += int(focal[idx])
                sums_g[ring] += int(focal[idx + 1])
                sums_b[ring] += int(focal[idx + 2])
                counts[ring] += 1
        if not all(counts):
            return None
        look_vals: list[float] = []
        for r_s, g_s, b_s, c in zip(sums_r, sums_g, sums_b, counts):
            look_vals.extend([r_s / c, g_s / c, b_s / c])
        low, high = min(look_vals), max(look_vals)
        span = high - low
        look = tuple(min(LOOK_LEVELS - 1, int((m - low) * LOOK_LEVELS / span)) if span > 0 else 0 for m in look_vals)
    else:
        sums = [0] * LOOK_RINGS
        counts = [0] * LOOK_RINGS
        for row in range(y0, y1 + 1):
            dy = row - cy
            for column in range(x0, x1 + 1):
                dx = column - cx
                d2 = dx * dx + dy * dy
                if d2 > r2:
                    continue
                ring = min(LOOK_RINGS - 1, int((d2 ** 0.5) / radius_sites * LOOK_RINGS))
                sums[ring] += int(focal[row * FOCAL_COLUMNS + column])
                counts[ring] += 1
        if not all(counts):
            return None
        means = [sums[i] / counts[i] for i in range(LOOK_RINGS)]
        low, high = min(means), max(means)
        span = high - low
        look = tuple(min(LOOK_LEVELS - 1, int((mean - low) * LOOK_LEVELS / span)) if span > 0 else 0 for mean in means)
    key = hashlib.sha256(bytes(look)).hexdigest()[:16]
    return Figure(key, look, sum(counts), (round(cx / (FOCAL_COLUMNS - 1), 6), round(cy / (FOCAL_ROWS - 1), 6)), round(radius_sites, 3))


__all__ = ("Figure", "FOCAL_COLUMNS", "FOCAL_ROWS", "LOOK_RINGS", "LOOK_LEVELS", "figure_of_disc")
