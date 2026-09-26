"""Accepted 5b3900e06 primitive arithmetic, TEST-ONLY differential evidence.

Never imported by runtime, packaging, restore or a fallback. No world writes.
"""
import numpy as np
SPHERE, CAPSULE, ELLIPSOID, CYLINDER, BOX = 2, 3, 4, 5, 6

def quadratic(a, b, c):
    """Real interval where a*t^2+2*b*t+c<=0, for squared-norm a>=0."""
    a, b, c = np.broadcast_arrays(a, b, c)
    det = b*b - a*c
    root = np.sqrt(np.maximum(det, 0))
    q = -b - np.copysign(root, b)
    x = np.divide(q, a, out=np.zeros_like(q), where=a != 0)
    y = np.divide(c, q, out=x.copy(), where=q != 0)
    lo, hi = np.minimum(x, y), np.maximum(x, y)
    constant_inside = (a == 0) & (c <= 0)
    missing = (det < 0) | ((a == 0) & (c > 0))
    return (np.where(missing, np.inf, np.where(constant_inside, -np.inf, lo)),
            np.where(missing, -np.inf, np.where(constant_inside, np.inf, hi)))


def slab(origin, velocity, half):
    origin, velocity, half = np.broadcast_arrays(origin, velocity, half)
    a = np.divide(-half-origin, velocity, out=np.zeros_like(velocity), where=velocity != 0)
    b = np.divide(half-origin, velocity, out=np.zeros_like(velocity), where=velocity != 0)
    parallel = velocity == 0
    outside = parallel & (np.abs(origin) > half)
    return (np.where(outside, np.inf, np.where(parallel, -np.inf, np.minimum(a, b))),
            np.where(outside, -np.inf, np.where(parallel, np.inf, np.maximum(a, b))))


def sphere_interval(origin, velocity, radius):
    return quadratic(np.sum(velocity*velocity, axis=-1),
                     np.sum(origin*velocity, axis=-1), np.sum(origin*origin, axis=-1)-radius*radius)


def _primitive_interval(kind, origin, velocity, radius, half, axes, *, normal=False):
    """One primitive law; optional surface normals reuse the winning roots."""
    if kind == SPHERE:
        lo, hi = sphere_interval(origin, velocity, radius)
    elif kind == ELLIPSOID:
        lo, hi = sphere_interval(origin / axes, velocity / axes, 1.)
    elif kind == BOX:
        axis_entry, axis_exit = slab(origin, velocity, axes)
        lo, hi = np.max(axis_entry, axis=-1), np.min(axis_exit, axis=-1)
    elif kind in (CAPSULE, CYLINDER):
        radial_entry, hi = sphere_interval(origin[..., :2], velocity[..., :2], radius)
        cap_entry, cap_exit = slab(origin[..., 2], velocity[..., 2], half)
        lo, hi = np.maximum(radial_entry, cap_entry), np.minimum(hi, cap_exit)
        valid = lo <= hi
        lo, hi = np.where(valid, lo, np.inf), np.where(valid, hi, -np.inf)
        if kind == CAPSULE:
            for sign in (-1, 1):
                shifted = np.broadcast_to(origin, velocity.shape).copy()
                shifted[..., 2] -= sign*half
                a, b = sphere_interval(shifted, velocity, radius)
                lo, hi = np.minimum(lo, a), np.maximum(hi, b)
    else:
        raise ValueError('finite primitive required; no silent geometry exclusion')
    if not normal:
        return lo, hi
    if not np.isfinite(lo).all() or np.any(lo <= 0) or np.any(hi < lo):
        raise ValueError('finite exterior central surface hit required')
    point = origin + lo[..., None]*velocity
    if kind == SPHERE:
        outward = point/radius[..., None]
    elif kind == ELLIPSOID:
        outward = point/(axes*axes)
    elif kind == CAPSULE:
        outward = point.copy()
        outward[..., 2] -= np.clip(point[..., 2], -half, half)
        outward /= radius[..., None]
    elif kind == CYLINDER:
        outward = np.zeros_like(point)
        outward[..., :2] = point[..., :2]/radius[..., None]
        cap = cap_entry >= radial_entry
        outward[cap] = 0
        outward[..., 2] = np.where(cap, -np.sign(velocity[..., 2]), 0.)
    else:
        # The same winning slab defines the normal; no nearest-face estimate.
        axis = np.argmax(axis_entry, axis=-1)
        outward = np.zeros_like(point)
        sign = -np.sign(np.take_along_axis(velocity, axis[..., None], axis=-1))
        np.put_along_axis(outward, axis[..., None], sign, axis=-1)
    return lo, hi, point, outward


def interval(kind, sizes, origin, velocity):
    """Line interval through the original analytic convex solid, in local axes."""
    return _primitive_interval(kind, origin, velocity, sizes[..., 0], sizes[..., 1], sizes)


def interval_pair(kind, expanded, contracted, origin, velocity):
    """Two independent solid intervals with identical ray terms evaluated once.

    Capsule radial dilation leaves its segment half-length unchanged. Keeping
    that common axis unexpanded avoids recomputing both end translations and
    their dot products. Ellipsoids still have distinct scaled rays.
    """
    radius = (np.stack((expanded[..., 0], contracted[..., 0]))
              if kind in (SPHERE, CAPSULE, CYLINDER) else None)
    axes = np.stack((expanded, contracted)) if kind in (ELLIPSOID, BOX) else None
    half = None
    if kind == CAPSULE:
        if not np.array_equal(expanded[..., 1], contracted[..., 1]):
            raise ValueError('paired capsule radial dilation requires equal half-lengths')
        half = expanded[..., 1]
    elif kind == CYLINDER:
        half = np.stack((expanded[..., 1], contracted[..., 1]))
    return _primitive_interval(kind, origin, velocity, radius, half, axes)
