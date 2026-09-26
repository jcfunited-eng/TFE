"""Direct planar visibility constraints under approved numerical optics.

World-only, transient geometry. No reconstructed clipping vertices, material
identity in cognition, scene retention, state mutation or complete-renderer claim.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .functional_body_optics import _unit_rows, aperture_solid_angles


def _finite(a, shape):
    return (isinstance(a, np.ndarray) and a.dtype == np.dtype(np.float64)
            and a.shape == shape and np.isfinite(a).all())


def _uv_planes(boundary, max_corners):
    if (type(max_corners) is not int or max_corners < 3
            or not isinstance(boundary, np.ndarray) or boundary.ndim != 2
            or boundary.shape[1] != 2 or not 3 <= len(boundary) <= max_corners
            or not _finite(boundary, boundary.shape)):
        raise ValueError("finite convex UV boundary required")
    shifted = boundary - boundary[0]
    edges = np.roll(shifted, -1, axis=0) - shifted
    area = float(np.sum(shifted[:, 0] * edges[:, 1] - shifted[:, 1] * edges[:, 0]))
    if not np.isfinite(area) or area == 0 or not np.isfinite(edges).all():
        raise ValueError("nonfinite or degenerate UV area")
    winding = np.sign(area)
    planes = []
    for point, edge in zip(boundary, edges):
        if not np.any(edge):
            raise ValueError("duplicate UV corner")
        a, b = -edge[1] * winding, edge[0] * winding
        sides = (boundary - point) @ np.array((a, b))
        if not np.isfinite(sides).all() or np.any(sides < 0):
            raise ValueError("UV boundary must be ordered convex")
        planes.append((a, b, -a * point[0] - b * point[1]))
    result = np.array(planes)
    if not np.isfinite(result).all():
        raise ValueError("UV coefficients exceed numerical domain")
    return result


@dataclass(frozen=True)
class PlanarSurface:
    """Original physical surface chart, prepared once by the optics caller.

    Inverse rows map an eye direction to (1/t,u/t,v/t). Boundary planes include
    positive t. Neither array contains a fitted/recognized object descriptor.
    """
    inverse: np.ndarray
    halfspaces: np.ndarray

    @classmethod
    def from_chart(cls, origin, axes, boundary_uv, *, max_corners):
        if not _finite(origin, (3,)) or not _finite(axes, (2, 3)):
            raise ValueError("finite physical planar chart required")
        uv = _uv_planes(boundary_uv, max_corners)
        matrix = np.column_stack((origin, axes.T))
        try:
            inverse = np.linalg.inv(matrix)
        except np.linalg.LinAlgError as error:
            raise ValueError("singular optical plane/chart") from error
        if not np.isfinite(inverse).all():
            raise ValueError("nonfinite optical inverse")
        planes = uv[:, 0, None] * inverse[1] + uv[:, 1, None] * inverse[2] + uv[:, 2, None] * inverse[0]
        halfspaces = _unit_rows(np.vstack((inverse[0], planes)), "surface boundaries")
        inverse.setflags(write=False)
        halfspaces.setflags(write=False)
        return cls(inverse, halfspaces)

    def material_halfspaces(self, boundary_uv, *, max_corners):
        """Map an attached material cell; it is NOT a second occluding surface."""
        uv = _uv_planes(boundary_uv, max_corners)
        planes = (uv[:, 0, None] * self.inverse[1] + uv[:, 1, None] * self.inverse[2]
                  + uv[:, 2, None] * self.inverse[0])
        return _unit_rows(planes, "material boundaries")


@dataclass(frozen=True)
class VisibleRegion:
    surface_index: int
    halfspaces: np.ndarray


def subtract_convex(region, clip, area, *, max_halfspaces):
    """One convex difference law for depth occlusion and ordered surface paint.

    area is the caller's charged analytic solid-angle evaluator. Returned
    pieces are disjoint up to zero-area boundaries; no clipping vertices.
    """
    overlap = np.vstack((region, clip))
    if area(overlap) == 0:
        return None, (region,)
    remaining, pieces, rows = region, [], 0
    for plane in clip:
        outside = np.vstack((remaining, -plane))
        if area(outside) > 0:
            rows += len(outside)
            if rows > max_halfspaces:
                raise ValueError("convex difference residency exceeded")
            pieces.append(outside)
        remaining = np.vstack((remaining, plane))
        if area(remaining) == 0:
            break
    return overlap, tuple(pieces)


def visible_planar_regions(surfaces, domain, *, max_halfspaces, max_work, max_cells):
    """Partition visible directions within one declared enclosing aperture.

    domain is a (1,4) array of (h_lo,h_hi,sin(v_lo),sin(v_hi)). Callers must not
    use the result outside that domain. Work counts event-cell upper bounds and
    pair/preparation scalar-vector rows. Storage bounds each input/output/active
    pool; total residency is O(max_halfspaces), not lifetime history.
    """
    if (not isinstance(surfaces, tuple) or not _finite(domain, (1, 4))
            or any(type(n) is not int or n <= 0 for n in (max_halfspaces, max_work, max_cells))):
        raise ValueError("bounded surfaces, domain and work required")
    work = 0

    def charge(amount):
        nonlocal work
        work += amount
        if work > max_work:
            raise ValueError("visibility work exhausted")

    def area(planes):
        k = len(planes)
        if k > max_halfspaces:
            raise ValueError("visibility halfspace residency exceeded")
        charge(k * (k - 1) + 6 * k + 2)
        return float(aperture_solid_angles(planes, domain, max_cells=max_cells)[0])

    total = 0
    for surface in surfaces:
        if (not isinstance(surface, PlanarSurface) or not _finite(surface.inverse, (3, 3))
                or not isinstance(surface.halfspaces, np.ndarray) or surface.halfspaces.ndim != 2
                or surface.halfspaces.shape[1] != 3 or not len(surface.halfspaces)
                or not _finite(surface.halfspaces, surface.halfspaces.shape)):
            raise ValueError("prepared finite planar surface required")
        total += len(surface.halfspaces)
        if total > max_halfspaces:
            raise ValueError("input halfspace residency exceeded")
        charge(len(surface.halfspaces))
    # Validate the angular domain even for an empty input.
    area(np.array(((1., 0., 0.),)))
    answer, retained = [], 0
    for index, source in enumerate(surfaces):
        if area(source.halfspaces) == 0:
            continue
        regions = [source.halfspaces]
        for other_index, blocker in enumerate(surfaces):
            if other_index == index:
                continue
            charge(1)
            depth = blocker.inverse[0] - source.inverse[0]
            if not np.isfinite(depth).all():
                raise ValueError("nonfinite physical depth order")
            coincident = not np.any(depth)
            occlusion = (blocker.halfspaces if coincident else
                         np.vstack((blocker.halfspaces, _unit_rows(depth[None, :], "depth boundary"))))
            successor, resident = [], retained + sum(len(r) for r in regions)
            for region in regions:
                if coincident:
                    if area(np.vstack((region, occlusion))) > 0:
                        raise ValueError("overlapping coplanar surfaces have ambiguous material")
                    pieces = (region,)
                else:
                    _, pieces = subtract_convex(region, occlusion, area,
                        max_halfspaces=max_halfspaces-resident+len(region))
                resident += sum(len(piece) for piece in pieces) - len(region)
                successor.extend(pieces)
            regions = successor
            if not regions:
                break
        for region in regions:
            retained += len(region)
            if retained > max_halfspaces:
                raise ValueError("visible output residency exceeded")
            owned = region.copy()
            owned.setflags(write=False)
            answer.append(VisibleRegion(index, owned))
    return tuple(answer)
