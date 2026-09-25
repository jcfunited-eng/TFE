"""Six-band material integration on physical planar charts.

Approved numerical optics; no perception/identity, retained scene, curved-shape
substitute or complete lighting claim. Each surface has declared uniform incident
irradiance. Spatially varying illumination needs its own physical integration.
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
    """Transient references/values from world material custody, not a new owner.

    Units: exact integer ppm reflectance/emission, and incident irradiance in
    the world's declared retinal-reference units. Pattern columns run toward
    +u, rows toward -v on a full [0,1] physical rectangle. No material/object
    identifiers are exported to an organism by this type.
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


def planar_material_radiance(surfaces, materials, apertures, *, max_sites,
                             max_material_cells, max_halfspaces, max_work,
                             max_cells):
    """Integrate actual material cells AFTER physical visibility/depth ordering.

    No billboard texture, centre sampling, guessed UV axis or palette reduction.
    Adjacent equal indices within a row become one exact rectangle. The input
    surfaces must represent the complete planar scene; this cannot certify a
    scene with omitted curved or other occluding geometry.
    """
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
    cell_count = 0
    for surface, material in zip(surfaces, materials):
        if not isinstance(surface, PlanarSurface) or not isinstance(material, PlanarMaterial):
            raise ValueError("typed physical planar surface and material required")
        material.verify()
        pattern = material.pattern
        if pattern is not None:
            cell_count += pattern.rows * pattern.columns
            if cell_count > max_material_cells:
                raise ValueError("declared material cell bound exceeded")
            rectangle = surface.material_halfspaces(_UNIT_RECTANGLE, max_corners=4)
            if (surface.halfspaces.shape != (5, 3)
                    or not np.array_equal(surface.halfspaces[1:], rectangle)):
                raise ValueError("pattern requires the original unit rectangular chart")

    domain = np.array(((apertures[:, 0].min(), apertures[:, 1].max(),
                        apertures[:, 2].min(), apertures[:, 3].max()),))
    visible = visible_planar_regions(surfaces, domain, max_halfspaces=max_halfspaces,
                                     max_work=max_work, max_cells=max_cells)
    planes, radiances, rows = [], [], 0

    def append(region, cell_planes, value):
        nonlocal rows
        count = len(region) + (0 if cell_planes is None else len(cell_planes))
        if rows + count > max_halfspaces:
            raise ValueError("material intersection halfspace bound exceeded")
        rows += count
        planes.append(region if cell_planes is None else np.vstack((region, cell_planes)))
        radiances.append(value)

    for index, (surface, material) in enumerate(zip(surfaces, materials)):
        regions = tuple(r.halfspaces for r in visible if r.surface_index == index)
        if not regions:
            continue
        light = np.asarray(material.incident_irradiance, dtype=np.float64)
        emission = np.asarray(material.emission_ppm, dtype=np.float64) / 1_000_000
        pattern = material.pattern
        if pattern is None:
            value = np.asarray(material.reflectance_ppm, dtype=np.float64) / 1_000_000 * light + emission
            for region in regions:
                append(region, None, value)
            continue
        palette = np.asarray(pattern.palette_reflectance_ppm, dtype=np.float64) / 1_000_000
        values = palette * light + emission
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
    return disjoint_surface_radiance(
        tuple(planes), np.asarray(radiances, dtype=np.float64).reshape(-1, 6),
        apertures, max_cells=max_cells, max_halfspaces=max_halfspaces)
