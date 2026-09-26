"""Six-band material integration on physical planar charts.

Approved numerical optics. Uniform incident irradiance is an explicit input,
not a claim of spatially varying illumination or complete world mounting.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .embodiment_world import ObjectOpticalSurface, _physical_bands
from .functional_body_optics import _validate_apertures, disjoint_surface_radiance
from .functional_body_visibility import PlanarSurface, visible_planar_regions


_UNIT_RECTANGLE = np.array(((0., 0.), (1., 0.), (1., 1.), (0., 1.)))
_UNIT_RECTANGLE.setflags(write=False)


@dataclass(frozen=True)
class PlanarMaterial:
    """World-owned physical material inputs, never a recognition identity.

    Six exact ppm reflectance/emission bands and declared incident irradiance.
    Pattern columns run toward +u and rows toward -v on the original [0,1]
    physical rectangular surface chart. References are transient, not custody.
    """
    reflectance_ppm: tuple[int, ...]
    emission_ppm: tuple[int, ...]
    incident_irradiance: tuple[float, ...]
    pattern: ObjectOpticalSurface | None = None

    def verify(self):
        _physical_bands(self.reflectance_ppm, "planar material reflectance")
        _physical_bands(self.emission_ppm, "planar material emission")
        light = self.incident_irradiance
        if (type(light) is not tuple or len(light) != 6
                or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
                       for v in light)):
            raise ValueError("six finite nonnegative incident irradiances required")
        if self.pattern is not None:
            if not isinstance(self.pattern, ObjectOpticalSurface):
                raise ValueError("existing physical optical surface required")
            self.pattern.verify()


def _prepare_material(material):
    """Single physical radiance law, after one material trust-boundary check."""
    if not isinstance(material, PlanarMaterial):
        raise ValueError("typed physical material required")
    material.verify()
    pattern = material.pattern
    paint = ((material.reflectance_ppm,) if pattern is None
             else pattern.palette_reflectance_ppm)
    values = (np.asarray(paint, dtype=np.float64) / 1_000_000
              * np.asarray(material.incident_irradiance, dtype=np.float64)
              + np.asarray(material.emission_ppm, dtype=np.float64) / 1_000_000)
    if not np.isfinite(values).all():
        raise ValueError("derived material radiance exceeds numerical domain")
    return pattern, values


def _material_regions(surfaces, prepared, visible, *, max_halfspaces):
    """One post-visibility composer shared by planar and native geometry.

    Inputs were admitted by the caller; prepared entries are (physical pattern
    or None, six-band radiances). Material cells never become occluding solids.
    """
    planes, radiances, rows = [], [], 0

    def append(region, cell_planes, value):
        nonlocal rows
        count = len(region) + (0 if cell_planes is None else len(cell_planes))
        if rows + count > max_halfspaces:
            raise ValueError("material intersection halfspace bound exceeded")
        rows += count
        planes.append(region if cell_planes is None else np.vstack((region, cell_planes)))
        radiances.append(value)

    for index, (surface, (pattern, values)) in enumerate(zip(surfaces, prepared)):
        if pattern is not None:
            rectangle = surface.material_halfspaces(_UNIT_RECTANGLE, max_corners=4)
            if (surface.halfspaces.shape != (5, 3)
                    or not np.array_equal(surface.halfspaces[1:], rectangle)):
                raise ValueError("pattern requires the original unit rectangular chart")
        regions = tuple(r.halfspaces for r in visible if r.surface_index == index)
        if not regions:
            continue
        if pattern is None:
            for region in regions:
                append(region, None, values[0])
            continue
        for row in range(pattern.rows):
            start = row * pattern.columns
            column = 0
            while column < pattern.columns:
                selected = pattern.cell_palette_indices[start + column]
                end = column + 1
                while (end < pattern.columns
                       and pattern.cell_palette_indices[start + end] == selected):
                    end += 1
                u0, u1 = column / pattern.columns, end / pattern.columns
                v0, v1 = 1 - (row + 1) / pattern.rows, 1 - row / pattern.rows
                cell = np.array(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
                boundaries = surface.material_halfspaces(cell, max_corners=4)
                for region in regions:
                    append(region, boundaries, values[selected])
                column = end
    return tuple(planes), np.asarray(radiances, dtype=np.float64).reshape(-1, 6)


def planar_material_radiance(surfaces, materials, apertures, *, max_sites,
                             max_material_cells, max_halfspaces, max_work,
                             max_cells):
    """Integrate actual attached paint AFTER complete planar depth ordering."""
    if any(type(n) is not int or n <= 0 for n in (
            max_sites, max_material_cells, max_halfspaces, max_work, max_cells)):
        raise ValueError("positive optical resource bounds required")
    if (type(surfaces) is not tuple or type(materials) is not tuple
            or len(surfaces) != len(materials) or len(surfaces) > max_halfspaces):
        raise ValueError("one material per bounded physical surface required")
    if (not isinstance(apertures, np.ndarray) or apertures.ndim != 2
            or not 0 < len(apertures) <= max_sites):
        raise ValueError("retinal site bound exceeded")
    _validate_apertures(apertures)
    prepared, cell_count = [], 0
    for surface, material in zip(surfaces, materials):
        if not isinstance(surface, PlanarSurface):
            raise ValueError("typed physical planar surface required")
        value = _prepare_material(material)
        pattern = value[0]
        if pattern is not None:
            cell_count += pattern.rows * pattern.columns
            if cell_count > max_material_cells:
                raise ValueError("declared material cell bound exceeded")
        prepared.append(value)
    domain = np.array(((apertures[:, 0].min(), apertures[:, 1].max(),
                        apertures[:, 2].min(), apertures[:, 3].max()),))
    visible = visible_planar_regions(surfaces, domain, max_halfspaces=max_halfspaces,
                                     max_work=max_work, max_cells=max_cells)
    planes, values = _material_regions(surfaces, prepared, visible,
                                       max_halfspaces=max_halfspaces)
    return disjoint_surface_radiance(planes, values, apertures,
                                     max_cells=max_cells, max_halfspaces=max_halfspaces)
