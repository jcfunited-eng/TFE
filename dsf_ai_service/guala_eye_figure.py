"""The eye's Level 1: the figure under her gaze (docs/GL-SPC-EYE-FIGURE-C1-20260915-v1.md).

A thing seen as one discrete structure: the connected region of her focal field
under her gaze whose luminance holds together, with its shape kept level-free and
place-free (aspect, fill, contrast against its surround, in eighths) as its key,
and its extent and place as measures beside it. Pure functions of the focal field
and the gaze; nothing is named, matched, or learned. The declared numbers are
stated once below (C1's §2 and A1's §5 resolutions).
"""
from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass
from typing import Sequence

FOCAL_COLUMNS = 80
FOCAL_ROWS = 60
FULL_SCALE = 255
STEP_GRAIN = 16            # a neighbour belongs to the same surface within one sixteenth of full scale of the site it joins from
SEED_DIVERGENCE = 48       # and within three sixteenths of the seed's luminance (a shaded curve holds, a boundary does not)
SURROUND_DEPTH = 2         # the surround is the band two sites deep just outside the region
MIN_SITES = 16             # smaller is noise
MAX_FIELD_FRACTION = 2     # a region over half the field is the wall or the floor: no figure
EIGHTHS = 8
MIN_FILL_EIGHTHS = 2       # thinner than two eighths of its box is a glint or a wire: no figure
ASPECT_CAP = 4             # aspect is kept between one to four and four to one


@dataclass(frozen=True, slots=True)
class Figure:
    key: str                          # sha-256 (16 hex) of (aspect, fill, contrast) in eighths
    aspect_eighths: int               # width over height, times eight (8 = square)
    fill_eighths: int                 # sites over the bounding box's sites, times eight
    contrast_eighths: int             # region mean minus surround mean over full scale, times eight, signed
    sites: int                        # how many sites the region holds
    box: tuple[int, int, int, int]    # column and row bounds, inclusive
    centre: tuple[float, float]       # the region's centre as fractions of the field

    @property
    def extent(self) -> float:
        return self.sites / float(FOCAL_COLUMNS * FOCAL_ROWS)


def _seed_index(gaze: tuple[float, float]) -> int:
    column = min(FOCAL_COLUMNS - 1, max(0, int(round(float(gaze[0]) * (FOCAL_COLUMNS - 1)))))
    row = min(FOCAL_ROWS - 1, max(0, int(round(float(gaze[1]) * (FOCAL_ROWS - 1)))))
    return row * FOCAL_COLUMNS + column


def region_under(focal: Sequence[int], seed: int) -> set[int]:
    """The connected region grown from the seed by the two declared grains."""

    seed_value = int(focal[seed])
    region = {seed}
    queue = deque([seed])
    while queue:
        index = queue.popleft()
        value = int(focal[index])
        column, row = index % FOCAL_COLUMNS, index // FOCAL_COLUMNS
        for neighbour in (index - 1 if column > 0 else -1, index + 1 if column + 1 < FOCAL_COLUMNS else -1,
                          index - FOCAL_COLUMNS if row > 0 else -1, index + FOCAL_COLUMNS if row + 1 < FOCAL_ROWS else -1):
            if neighbour < 0 or neighbour in region:
                continue
            other = int(focal[neighbour])
            if abs(other - value) <= STEP_GRAIN and abs(other - seed_value) <= SEED_DIVERGENCE:
                region.add(neighbour)
                queue.append(neighbour)
    return region


def figure_under_gaze(focal: Sequence[int], gaze: tuple[float, float]) -> Figure | None:
    """The figure under her gaze, or None (no figure: the wall, noise, a glint)."""

    if len(focal) != FOCAL_COLUMNS * FOCAL_ROWS:
        return None
    region = region_under(focal, _seed_index(gaze))
    sites = len(region)
    if sites < MIN_SITES or sites * MAX_FIELD_FRACTION > FOCAL_COLUMNS * FOCAL_ROWS:
        return None
    columns = [index % FOCAL_COLUMNS for index in region]
    rows = [index // FOCAL_COLUMNS for index in region]
    x0, x1, y0, y1 = min(columns), max(columns), min(rows), max(rows)
    width, height = x1 - x0 + 1, y1 - y0 + 1
    fill = int(round(EIGHTHS * sites / float(width * height)))
    if fill < MIN_FILL_EIGHTHS:
        return None
    ratio = min(float(ASPECT_CAP), max(1.0 / ASPECT_CAP, width / float(height)))
    aspect = int(round(EIGHTHS * ratio))
    # The surround: every site within the declared depth of the region, outside it, inside the field.
    surround: set[int] = set()
    for index in region:
        column, row = index % FOCAL_COLUMNS, index // FOCAL_COLUMNS
        for dy in range(-SURROUND_DEPTH, SURROUND_DEPTH + 1):
            for dx in range(-SURROUND_DEPTH, SURROUND_DEPTH + 1):
                c, r = column + dx, row + dy
                if 0 <= c < FOCAL_COLUMNS and 0 <= r < FOCAL_ROWS:
                    other = r * FOCAL_COLUMNS + c
                    if other not in region:
                        surround.add(other)
    region_mean = sum(int(focal[i]) for i in region) / float(sites)
    surround_mean = (sum(int(focal[i]) for i in surround) / float(len(surround))) if surround else region_mean
    contrast = int(round(EIGHTHS * (region_mean - surround_mean) / FULL_SCALE))
    key = hashlib.sha256(f"a{aspect}f{fill}c{contrast}".encode("ascii")).hexdigest()[:16]
    centre = (sum(columns) / float(sites * (FOCAL_COLUMNS - 1)), sum(rows) / float(sites * (FOCAL_ROWS - 1)))
    return Figure(key, aspect, fill, contrast, sites, (x0, y0, x1, y1), centre)


__all__ = ("Figure", "FOCAL_COLUMNS", "FOCAL_ROWS", "figure_under_gaze", "region_under")
