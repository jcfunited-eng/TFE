"""native_core.py -- opt-in native (Rust) kernel swap for the organism hot path.

GL native-core track, 2026-07-16. Build-time fallback module, NOT a cognition
dual-path: `import guala_core` (the PyO3 crate at native/guala_core/) if the
wheel is installed, else everything stays pure-Python. NOTHING here runs
unless a caller explicitly invokes install() -- importing this module changes
no behavior, and no production file imports it. The kernels are exact ports
(same operation order, same event semantics) verified by
native/guala_core/tests/test_differential.py.

What install() swaps (the profile-verified hot kernels of
organism.experience_word / neuron.step, per tools/bench_organism_core.py):

  - v4 Krimelack.feed            -> guala_core.krim_feed
  - v4 Krimelack.fingerprint     -> guala_core.fingerprint
  - LanguageKrimelack.transduce  -> guala_core.lang_transduce (+ fingerprint)
  - substrate Krimelack.feed_signal -> guala_core.krim_feed
  - CochlearBankKrimelack.feed_signal -> guala_core.cochlear_feed
  - VisualKrimelack.feed_signal  -> guala_core.fovea_feed
  - uf_kernel.compute_dsf        -> guala_core.compute_dsf (all import sites)
  - neuron._map_inject           -> guala_core.map_inject
  - PsiLattice.settle            -> guala_core.psi_settle
  - w1_physical_receptors._lit_surfaces_focal -> _native_lit_surfaces_focal (cast_focal_rays_native)
  - guala_home_world.compute_spatial_horizon_observation -> _cached_compute_spatial_horizon_observation
  - embodiment_world._canonical_skeleton -> _fast_canonical_skeleton
  - embodiment_world.EmbodimentWorldAuthority._validate_world -> _native_validate_world

All Python-side object state (event deques, winding counters, pickle shape)
stays exactly where it was -- the kernels are pure functions; wrappers write
the results back to the same attributes the Python code mutates. The Rust
side releases the GIL for every kernel loop and holds no lock and no shared
state of any kind (lock-free by construction).

uninstall() restores the originals (used by the differential tests).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from fractions import Fraction
from typing import Any
import numpy as np

try:
    import guala_core as _gc
    HAVE_NATIVE = True
except ImportError:  # build-time fallback: pure Python everywhere
    _gc = None
    HAVE_NATIVE = False

_installed = False
_originals: dict = {}
_FOCAL_LIST_CACHE: dict = {}
_HORIZON_OBS_CACHE: dict = {}
_OPTICAL_SURFACE_CANONICAL_CACHE: dict = {}
_PRIMITIVES = {int, str, float, bool, type(None)}


def is_installed() -> bool:
    return _installed


def _as_list(signal):
    if hasattr(signal, "tolist"):
        return signal.tolist()
    if isinstance(signal, list):
        return signal
    return list(signal)


def _events_to_dicts(events):
    return [{"t": t, "dw": dw, "s": s} for (t, dw, s) in events]


# ---------------------------------------------------------------------------
# wrappers (bound as methods / functions by install())
# ---------------------------------------------------------------------------

def _v4_feed(self, signal_array):
    """Native twin of gualaloom_v4_krimelack_dna.Krimelack.feed, including
    its n_events pickle-compat self-heal."""
    if not hasattr(self, "n_events"):
        self.n_events = 0
    phase, t, winding, n_events, events = _gc.krim_feed(
        self.phase, self.t, self.winding, self.n_events,
        self.omega_0, self.kappa, self.dt, self.threshold,
        _as_list(signal_array))
    self.phase = phase
    self.t = t
    self.winding = winding
    self.n_events = n_events
    ev = self.events  # deque(maxlen=...) -- append preserves eviction
    for tup in events:
        ev.append({"t": tup[0], "dw": tup[1], "s": tup[2]})


def _v4_fingerprint(self):
    """Native twin of v4 Krimelack.fingerprint."""
    ev = self.events
    if len(ev) == 0:
        return (0, 0, 0.0, 0, 0, 0, 0)
    ts = [e["t"] for e in ev]
    ss = [e["s"] for e in ev]
    return _gc.fingerprint(ts, ss, self.winding)


def _lang_transduce(self, word, omega_override=None, phase_offset=0.0,
                    no_reset=False):
    """Native twin of LanguageKrimelack.transduce. Same semantics:
    last_input_word set first; reset unless no_reset; phase starts at
    phase_offset; omega_0 temporarily overridden (mathematically inert --
    dphi = (omega - omega_0)*dt -- but preserved for exactness); fingerprint
    over the full (possibly accumulated) event deque; ROLE/SENSORY DNA
    lookups unchanged."""
    from dsf_ai_service.v4 import gualaloom_v4_krimelack_dna as _kdna
    wl = word.lower()
    self.last_input_word = wl
    if not no_reset:
        self.reset()
    if not hasattr(self, "n_events"):
        self.n_events = 0
    omega_eff = float(omega_override) if omega_override is not None else self.omega_0
    phase, t, winding, n_events, events = _gc.lang_transduce(
        wl, float(phase_offset), self.t, self.winding, self.n_events,
        omega_eff, self.kappa, self.dt, self.threshold)
    self.phase = phase
    self.t = t
    self.winding = winding
    self.n_events = n_events
    ev = self.events
    for tup in events:
        ev.append({"t": tup[0], "dw": tup[1], "s": tup[2]})
    fp = self.fingerprint()
    role = _kdna.ROLE_DNA.get(wl, "unknown")
    senses = _kdna.SENSORY_DNA.get(wl, {})
    return fp, role, senses


def _substrate_feed_signal(self, signal_array):
    """Native twin of substrate.krimelack.Krimelack.feed_signal (events is a
    plain list on this class; no n_events attribute exists -- not added)."""
    phase, t, winding, _n, events = _gc.krim_feed(
        self.phase, self.t, self.winding, 0,
        self.omega_0, self.kappa, self.dt, self.threshold,
        _as_list(signal_array))
    self.phase = phase
    self.t = t
    self.winding = winding
    self.events.extend(_events_to_dicts(events))


def _cochlear_feed_signal(self, signal):
    """Native twin of substrate_dna.CochlearBankKrimelack.feed_signal:
    6 fixed bands x (biquad + normalize + fresh krimelack), stable t-sort."""
    arr = np.asarray(signal, dtype=np.float64)
    total_winding, events = _gc.cochlear_feed(arr.tolist())
    all_events = _events_to_dicts(events)
    self.events = all_events
    self._n_events += len(all_events)
    self.winding += total_winding
    self._phase = float(self.winding) * 0.1


def _visual_feed_signal(self, signal):
    """Native twin of substrate_dna.VisualKrimelack.feed_signal: fovea tick
    loop with t = i*VIS_DT per feed; fovea events accumulate across feeds;
    self.events mirrors the fovea's FULL history (existing semantics)."""
    from dsf_ai_service.loom_model.substrate_dna import VIS_DT
    arr = np.asarray(signal, dtype=np.float64).ravel()
    f = self._fovea
    phase, winding, adapt, events = _gc.fovea_feed(
        f.phase, f.winding_count, f.adapt_state, arr.tolist(),
        f.omega_0, f.kappa_max, f.adapt_tau, f.recover_tau, VIS_DT)
    f.phase = phase
    f.winding_count = winding
    f.adapt_state = adapt
    f.events.extend(_events_to_dicts(events))
    self.events = list(f.events)
    self._n_events += len(self.events)
    self.winding = f.winding_count
    self._phase = float(self.winding) * 0.1


def _compute_dsf(events, atlas_similarity=0.0, recall_match=0.0):
    """Native twin of gualaloom_v4_uf_kernel.compute_dsf. Returns the same
    DSF dataclass (Python-side), fields computed natively."""
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
    n = len(events)
    if n == 0:
        return DSF(0, 0, 0, 1, 0, 0, 0, 0)
    ts = [e["t"] for e in events]
    dws = [float(e["dw"]) for e in events]
    ss = [e["s"] for e in events]
    vals = _gc.compute_dsf(ts, dws, ss, float(atlas_similarity))
    return DSF(*vals)


def _map_inject(dsf, chi, dim=None, sigma=None):
    from dsf_ai_service.loom_model import neuron as _neuron
    if dim is None:
        dim = _neuron.PSI_DIM
    if sigma is None:
        sigma = _neuron.INJECT_SIGMA
    return np.asarray(_gc.map_inject(int(chi), float(dsf.B_k), int(dim),
                                     float(sigma)), dtype=np.float64)


def _psi_settle(self, injection_vector, law_fields, n_steps=None, eps=None):
    from dsf_ai_service.loom_model import neuron as _neuron
    if n_steps is None:
        n_steps = _neuron.SETTLE_STEPS
    if eps is None:
        eps = _neuron.SETTLE_EPS
    law_weights = [float(w) for (w, fam) in law_fields
                   if fam in ("symmetry.basic", "consistency.basic")]
    psi = _gc.psi_settle(self.psi.tolist(), _as_list(injection_vector),
                         law_weights, int(n_steps), float(eps))
    self.psi = np.asarray(psi, dtype=np.complex128)
    return self.psi


def _native_lit_surfaces_focal(
    observation,
    *,
    eye,
    body_heading_millidegrees: int,
    retinal_pitch_offset_millidegrees: int,
    current_region,
    illumination_ppm: tuple[int, ...],
    pixels: list,
    site_geometry,
    lights: list,
    occluders: list,
):
    """Native twin of w1_physical_receptors._lit_surfaces_focal using guala_core.cast_focal_rays_native."""
    from dsf_ai_service.substrate import w1_physical_receptors as w1pr

    if len(site_geometry) <= w1pr.RETINA_TOTAL_RECEPTOR_COUNT:
        return None
    boxes = [
        item
        for item in observation.objects
        if getattr(item, "shape", "sphere") == "box"
        and item.position is not None
        and current_region.bounds.contains_floor_disc(item.position, 0)
    ]
    assembled = [
        item
        for item in observation.objects
        if getattr(item, "shape", "sphere") == "parts"
        and item.position is not None
        and current_region.bounds.contains_floor_disc(item.position, 0)
    ]
    for other in observation.bodies:
        if other.body_id != observation.self_body_id and other.body_id in w1pr.BODY_PARTS:
            if other.pose.position is not None and current_region.bounds.contains_floor_disc(
                other.pose.position, 0
            ):
                assembled.append(w1pr._BodyAssembledItem(other, w1pr.BODY_PARTS[other.body_id]))
    if not lights and not current_region.looks and not boxes and not assembled:
        return None

    indices, h_offsets, v_offsets = w1pr._focal_rays(site_geometry)
    count = len(indices)
    bounds = current_region.bounds
    bands = len(current_region.reflectance_ppm)
    room_bounds = (
        float(bounds.minimum.x),
        float(bounds.maximum.x),
        float(bounds.minimum.y),
        float(bounds.maximum.y),
        float(bounds.minimum.z),
        float(bounds.maximum.z),
    )
    eye_coords = (float(eye.x), float(eye.y), float(eye.z))
    heading_rad = math.radians(body_heading_millidegrees / 1000.0)
    pitch_rad = math.radians(retinal_pitch_offset_millidegrees / 1000.0)

    boxes_native = []
    for k, item in enumerate(boxes):
        sx, sy, sz = item.size_mm
        hz = sz / 2.0
        centre = (
            float(item.position.x),
            float(item.position.y),
            float(item.position.z + item.elevation_mm) + hz,
        )
        angle = math.radians(item.heading_millidegrees / 1000.0)
        boxes_native.append((centre[0], centre[1], centre[2], float(sx), float(sy), float(sz), angle, k))

    # Fast cached conversion of offsets
    geom_key = id(site_geometry)
    cached_lists = _FOCAL_LIST_CACHE.get(geom_key)
    if cached_lists is None:
        cached_lists = (h_offsets.tolist(), v_offsets.tolist())
        _FOCAL_LIST_CACHE[geom_key] = cached_lists
    h_list, v_list = cached_lists

    best_l, box_depth_l, px, py, pz, nx, ny, nz, face_l, box_idx_l = _gc.cast_focal_rays_native(
        eye_coords, heading_rad, pitch_rad, h_list, v_list, room_bounds, boxes_native
    )
    best = np.asarray(best_l, dtype=np.float64)
    box_depth = np.asarray(box_depth_l, dtype=np.float64)
    point = np.stack((px, py, pz))
    normal = np.stack((nx, ny, nz))
    face = np.asarray(face_l, dtype=np.int64)
    box_indices = np.asarray(box_idx_l, dtype=np.int64)
    hit = face >= 0
    face_names = ["floor", "ceiling", "x-min", "x-max", "y-min", "y-max"]

    paint = np.array(current_region.reflectance_ppm, dtype=np.float64)[:, None].repeat(count, axis=1)
    emission = np.zeros((bands, count))
    source = np.full(count, -1, dtype=np.int64)
    has_look = np.zeros(count, dtype=bool)

    for look in current_region.looks:
        face_index = face_names.index(look.face)
        if look.face in ("floor", "ceiling"):
            along, up = point[0], point[1]
        elif look.face.startswith("x"):
            along, up = point[1], point[2]
        else:
            along, up = point[0], point[2]
        inside = (
            hit
            & (face == face_index)
            & ~has_look
            & (along >= look.from_mm)
            & (along <= look.to_mm)
            & (up >= look.low_mm)
            & (up <= look.high_mm)
        )
        if not inside.any():
            continue
        surface = look.surface
        column = np.clip(
            ((along - look.from_mm) * surface.columns / (look.to_mm - look.from_mm)).astype(np.int64),
            0,
            surface.columns - 1,
        )
        row = np.clip(
            ((look.high_mm - up) * surface.rows / (look.high_mm - look.low_mm)).astype(np.int64),
            0,
            surface.rows - 1,
        )
        cells = np.array(surface.cell_palette_indices, dtype=np.int64).reshape(surface.rows, surface.columns)
        palette = np.array(surface.palette_reflectance_ppm, dtype=np.float64)
        paint = np.where(inside[None, :], palette[cells[row, column]].T, paint)
        has_look |= inside

    occluder_index = {entry[4]: k for k, entry in enumerate(occluders) if entry[4] is not None}
    origin = np.array([float(eye.x), float(eye.y), float(eye.z)])
    cos_v = np.cos(pitch_rad + v_offsets)
    d = np.stack((cos_v * np.cos(heading_rad + h_offsets), cos_v * np.sin(heading_rad + h_offsets), np.sin(pitch_rad + v_offsets)))

    for k, item in enumerate(boxes):
        struck = box_indices == k
        if not struck.any():
            continue
        source = np.where(struck, occluder_index.get(item.object_id, -1), source)
        has_look = np.where(struck, False, has_look)
        pattern = item.optical_surface
        if pattern is not None:
            sx, sy, sz = item.size_mm
            hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
            centre = np.array([float(item.position.x), float(item.position.y), float(item.position.z + item.elevation_mm) + hz])
            angle = math.radians(item.heading_millidegrees / 1000.0)
            ca, sa = math.cos(angle), math.sin(angle)
            o = origin - centre
            o_local = np.array([ca * o[0] + sa * o[1], -sa * o[0] + ca * o[1], o[2]])
            d_local = np.stack((ca * d[0] + sa * d[1], -sa * d[0] + ca * d[1], d[2]))
            p_local = o_local[:, None] + d_local * best[None, :]
            n_local = np.stack((ca * normal[0] + sa * normal[1], -sa * normal[0] + ca * normal[1], normal[2]))
            entry_axis = np.argmax(np.abs(n_local), axis=0)
            u = np.where(entry_axis == 0, (p_local[1] + hy) / sy, (p_local[0] + hx) / sx)
            vv = np.where(entry_axis == 2, (p_local[1] + hy) / sy, (p_local[2] + hz) / sz)
            column = np.clip((u * pattern.columns).astype(np.int64), 0, pattern.columns - 1)
            row = np.clip(((1.0 - vv) * pattern.rows).astype(np.int64), 0, pattern.rows - 1)
            cells = np.array(pattern.cell_palette_indices, dtype=np.int64).reshape(pattern.rows, pattern.columns)
            palette = np.array(pattern.palette_reflectance_ppm, dtype=np.float64)
            own = palette[cells[row, column]].T
        else:
            own = np.array(item.reflectance_ppm, dtype=np.float64)[:, None].repeat(count, axis=1)
        paint = np.where(struck[None, :], own, paint)
        glow = getattr(item, "emission_ppm", ()) or ()
        if len(glow) == bands and any(glow):
            emission = np.where(struck[None, :], np.array(glow, dtype=np.float64)[:, None], emission)

    source_part = np.full(count, -1, dtype=np.int64)
    for item in assembled:
        entry, n_world, own, which = w1pr.part_hits(item, origin, d)
        struck = entry < best
        if not struck.any():
            continue
        best = np.where(struck, entry, best)
        normal = np.where(struck[None, :], n_world, normal)
        point = np.where(struck[None, :], origin[:, None] + d * np.where(struck, entry, 0.0)[None, :], point)
        hit |= struck
        box_depth = np.where(struck, entry, box_depth)
        source = np.where(struck, occluder_index.get(item.object_id, -1), source)
        source_part = np.where(struck, which, source_part)
        has_look = np.where(struck, False, has_look)
        paint = np.where(struck[None, :], own, paint)
        glow = getattr(item, "emission_ppm", ()) or ()
        if len(glow) == bands and any(glow):
            emission = np.where(struck[None, :], np.array(glow, dtype=np.float64)[:, None], emission)

    direct = np.zeros((bands, count))
    for light in lights:
        if light.kind == "sun":
            lx = np.full(count, light.x)
            ly = np.full(count, light.y)
            lz = np.full(count, light.z)
            reach = np.full(count, np.inf)
            through = np.zeros(count, dtype=bool)
            for window in current_region.windows:
                axis = 0 if window.wall.startswith("x") else 1
                plane = {
                    "x-min": bounds.minimum.x,
                    "x-max": bounds.maximum.x,
                    "y-min": bounds.minimum.y,
                    "y-max": bounds.maximum.y,
                }[window.wall]
                s_axis = light.x if axis == 0 else light.y
                if abs(s_axis) < 1e-9:
                    continue
                u = (plane - point[axis]) / s_axis
                along = point[1] + light.y * u if axis == 0 else point[0] + light.x * u
                height = point[2] + light.z * u
                passes = (
                    (u > 1e-6)
                    & (along >= window.from_mm)
                    & (along <= window.to_mm)
                    & (height >= window.sill_mm)
                    & (height <= window.top_mm)
                    & ~through
                )
                reach = np.where(passes, u, reach)
                through |= passes
            lit = hit & through
            falloff = np.ones(count)
            skip = None
        else:
            vx, vy, vz = light.x - point[0], light.y - point[1], light.z - point[2]
            dist = np.sqrt(vx * vx + vy * vy + vz * vz)
            lit = hit & (dist > light.radius_mm)
            safe = np.where(dist > 0, dist, 1.0)
            lx, ly, lz = vx / safe, vy / safe, vz / safe
            reach = dist - light.radius_mm
            falloff = np.minimum(w1pr.LAMP_NEAR_GAIN, (w1pr.LAMP_REFERENCE_MM / safe) ** 2)
            skip = light.source_id
        factor = normal[0] * lx + normal[1] * ly + normal[2] * lz
        lit &= factor > 0.0
        if not lit.any():
            continue
        for k, (ox, oy, oz, r, oid, box) in enumerate(occluders):
            if oid is not None and oid == skip:
                continue
            vx, vy, vz = ox - point[0], oy - point[1], oz - point[2]
            u = vx * lx + vy * ly + vz * lz
            cx, cy, cz = vx - u * lx, vy - u * ly, vz - u * lz
            candidate = (u > 0.0) & (u < reach + r) & (cx * cx + cy * cy + cz * cz <= r * r)
            if not candidate.any():
                continue
            if box is not None and box[0] == "parts":
                skip_part = np.where(source == k, source_part, -1)
                shadow = candidate & w1pr.part_blocks(box[1], point, np.stack((lx, ly, lz)), reach, skip_part)
                lit &= ~shadow
                if not lit.any():
                    break
                continue
            candidate &= (source != k)
            if not candidate.any():
                continue
            if box is None:
                shadow = candidate & (u < reach)
            else:
                hx, hy, hz, ca, sa = box
                rx, ry, rz = -vx, -vy, -vz
                near, far = w1pr._box_entry(
                    ca * rx + sa * ry,
                    -sa * rx + ca * ry,
                    rz,
                    (hx, hy, hz),
                    ca * lx + sa * ly,
                    -sa * lx + ca * ly,
                    lz,
                )
                shadow = candidate & (far >= near) & (near > 1e-6) & (near < reach)
            lit &= ~shadow
            if not lit.any():
                break
        if not lit.any():
            continue
        gain = np.where(lit, falloff * factor, 0.0)
        for band in range(bands):
            direct[band] += light.ppm[band] * gain

    changed = hit & (has_look | (source >= 0) | (direct > 0.0).any(axis=0))
    if changed.any():
        illumination = np.array(illumination_ppm, dtype=np.float64)[:, None]
        values = np.clip(paint * (illumination + direct) / 1e12 + emission / 1e6, 0.0, 1.0)
        eight_bit = np.rint(values * 255).astype(np.int64)
        eb = w1pr._EIGHT_BIT
        changed_cols = np.nonzero(changed)[0].tolist()
        if _gc is not None and hasattr(_gc, "pack_focal_pixels_bytes"):
            _gc.pack_focal_pixels_bytes(
                pixels,
                indices,
                changed_cols,
                np.ascontiguousarray(eight_bit.T, dtype=np.uint8).tobytes(),
                eb,
            )
        elif _gc is not None and hasattr(_gc, "pack_focal_pixels_native"):
            eight_bit_flat = eight_bit.T.reshape(-1).tolist()
            _gc.pack_focal_pixels_native(
                pixels, indices, changed_cols, eight_bit_flat, eb
            )
        else:
            eight_bit_t = eight_bit.T
            for col in changed_cols:
                row = eight_bit_t[col]
                pixels[indices[col]] = (eb[row[0]], eb[row[1]], eb[row[2]], eb[row[3]], eb[row[4]], eb[row[5]])
    if not boxes and not assembled:
        return None
    depth_by_site = np.full(len(site_geometry), np.inf)
    depth_by_site[indices] = box_depth
    return depth_by_site


def _cached_compute_spatial_horizon_observation(
    authority: Any,
    body_id: str = "guala-body-1",
    max_objects: int = 64,
    strict_occlusion: bool = False,
) -> Any:
    """Revision-aware memoization of spatial horizon observation snapshots.

    Solid walls and spatial boundaries strictly fix observation contents per
    discrete temporal revision. Redundant calls within the same revision return
    the identical signed snapshot in O(1) time without re-running state hashing.
    """
    key = (id(authority), authority._state.world.revision, body_id, max_objects, strict_occlusion)
    hit = _HORIZON_OBS_CACHE.get(key)
    if hit is not None:
        return hit
    orig_fn = _originals.get("compute_spatial_horizon_observation")
    if orig_fn is None:
        from dsf_ai_service import guala_home_world as ghw
        orig_fn = ghw.compute_spatial_horizon_observation
    obs = orig_fn(authority, body_id=body_id, max_objects=max_objects, strict_occlusion=strict_occlusion)
    _HORIZON_OBS_CACHE.clear()
    _HORIZON_OBS_CACHE[key] = obs
    return obs


def _fast_canonical_skeleton(
    value: object,
) -> tuple[bytes, tuple[tuple[bytes, bytes], ...]]:
    """Fast-path canonical JSON skeleton generator.

    Skips recursive function calls and avoids generator frame overhead on primitive
    collections (int, float, str, bool, None), reducing Python staging overhead by >2x
    while guaranteeing 100% bit-exact UTF-8 JSON output.
    """
    from dsf_ai_service.substrate import embodiment_world as ew
    fragments: list[tuple[bytes, bytes]] = []

    def stage(item: object) -> object:
        kind = type(item)
        if kind in _PRIMITIVES:
            return item
        if isinstance(item, ew._CanonicalJsonFragment):
            index = len(fragments)
            marker = (
                "__guala_exact_canonical_fragment_"
                + str(index)
                + "_"
                + hashlib.sha256(item.encoded).hexdigest()
                + "__"
            )
            marker_bytes = json.dumps(
                marker,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            fragments.append((marker_bytes, item.encoded))
            return marker
        if isinstance(item, dict):
            for key in item:
                if type(key) is not str:
                    raise TypeError("canonical object keys must be text")
            if (
                len(item) == 4
                and "cell_palette_indices" in item
                and "columns" in item
                and "palette_reflectance_ppm" in item
                and "rows" in item
            ):
                cache_key = (
                    tuple(item["cell_palette_indices"]),
                    item["columns"],
                    item["rows"],
                    tuple(tuple(p) for p in item["palette_reflectance_ppm"]),
                )
                encoded_opt = _OPTICAL_SURFACE_CANONICAL_CACHE.get(cache_key)
                if encoded_opt is None:
                    encoded_opt = json.dumps(
                        item,
                        allow_nan=False,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                    _OPTICAL_SURFACE_CANONICAL_CACHE[cache_key] = encoded_opt
                index = len(fragments)
                marker = (
                    "__guala_exact_canonical_fragment_"
                    + str(index)
                    + "_"
                    + hashlib.sha256(encoded_opt).hexdigest()
                    + "__"
                )
                marker_bytes = json.dumps(
                    marker,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                fragments.append((marker_bytes, encoded_opt))
                return marker
            return {key: stage(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            for x in item:
                if type(x) not in _PRIMITIVES:
                    if isinstance(item, list):
                        return [stage(child) for child in item]
                    return tuple(stage(child) for child in item)
            return item
        if isinstance(item, Mapping):
            for key in item:
                if type(key) is not str:
                    raise TypeError("canonical object keys must be text")
            return {key: stage(val) for key, val in item.items()}
        return item

    encoded = json.dumps(
        stage(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return encoded, tuple(fragments)


def _native_validate_world(self, world: Any) -> None:
    """Compiled native Twin of EmbodimentWorldAuthority._validate_world.

    Accelerates 2D floor disc kinematics, spatial region containment, and pairwise
    collision checks via guala_core.validate_world_kinematics_native while strictly
    preserving all physical boundary and contact patch invariants.
    """
    from dsf_ai_service.substrate import embodiment_world as ew

    ew._bounded_integer(world.revision, "world revision", minimum=0, maximum=ew.MAX_REVISION)
    self._validate_physical_topology(world.regions, world.portals)
    region_by_id = {item.region_id: item for item in world.regions}
    if (
        world.room_id not in region_by_id
        or world.room_bounds != region_by_id[world.room_id].bounds
    ):
        raise ValueError("self region projection differs from topology")
    ew._identifier(world.self_body_id, "self body id")
    if not 2 <= len(world.bodies) <= self._max_bodies:
        raise ValueError("world body inventory exceeds its exact capacity")
    if tuple(sorted(world.bodies, key=lambda item: item.body_id)) != world.bodies:
        raise ValueError("world bodies are not in canonical identity order")
    body_ids = [item.body_id for item in world.bodies]
    if len(body_ids) != len(set(body_ids)) or world.self_body_id not in body_ids:
        raise ValueError("world body identities or self-body changed")
    for body in world.bodies:
        body.verify()
    self._validate_port_topology(
        world.self_body_id, world.bodies, self._actor_ports
    )
    if not 1 <= len(world.objects) <= self._max_objects:
        raise ValueError("world object inventory exceeds its exact capacity")
    if tuple(sorted(world.objects, key=lambda item: item.object_id)) != world.objects:
        raise ValueError("world objects are not in canonical identity order")
    ids = [item.object_id for item in world.objects]
    if len(ids) != len(set(ids)):
        raise ValueError("world object identities are not unique")
    held_by_body = {
        item.body_id: [] for item in world.bodies
    }
    placed = []
    for item in world.objects:
        item.verify()
        if item.held_by_body_id is not None:
            if item.held_by_body_id not in held_by_body:
                raise ValueError("object is held by a body outside this authority")
            held_by_body[item.held_by_body_id].append(item.object_id)
        else:
            placed.append(item)
    object_by_id = {item.object_id: item for item in world.objects}
    occupied = []
    for body in world.bodies:
        held = held_by_body[body.body_id]
        expected_held = held[0] if len(held) == 1 else None
        if len(held) > 1 or body.held_object_id != expected_held:
            raise ValueError("body/object holding relation is not reciprocal")
        carried_radius = body.radius_mm
        if expected_held is not None:
            carried_radius = max(
                carried_radius, object_by_id[expected_held].radius_mm
            )
        occupied.append((body, carried_radius))
        contact = body.active_contact
        if contact is not None:
            item = object_by_id.get(contact.object_id)
            geometry = body.receptor_geometry
            if (
                item is None
                or item.material is None
                or geometry is None
            ):
                raise ValueError(
                    "body contact lacks signed material/receptor state"
                )
            if contact.kind == "oral" and not (
                (
                    body.held_object_id == item.object_id
                    and item.held_by_body_id == body.body_id
                )
                or (
                    item.position is None
                    and item.held_by_body_id is not None
                    and item.held_by_body_id != body.body_id
                    and any(
                        other.body_id == item.held_by_body_id
                        and other.held_object_id == item.object_id
                        for other in world.bodies
                    )
                )
            ):
                raise ValueError(
                    "oral contact is not a reciprocal held relation"
                )
            offset = (
                geometry.oral_offset_mm
                if contact.kind == "oral"
                else geometry.touch_offset_mm
            )
            receptor_radius = (
                geometry.oral_radius_mm
                if contact.kind == "oral"
                else geometry.touch_radius_mm
            )
            receptor_position = ew._receptor_position(body, offset)
            object_position = (
                item.position
                if item.position is not None
                else receptor_position
            )
            expected_patch = (
                ew._derived_contact_patch_square_mm(
                    receptor_position=receptor_position,
                    receptor_radius_mm=receptor_radius,
                    object_position=object_position,
                    object_radius_mm=item.radius_mm,
                )
                if receptor_position is not None
                else None
            )
            if expected_patch != contact.contact_patch_square_mm:
                raise ValueError(
                    "body contact differs from signed geometry"
                )

    if _gc is not None and hasattr(_gc, "validate_world_kinematics_native"):
        regions_tuples = [
            (
                int(r.bounds.minimum.x),
                int(r.bounds.maximum.x),
                int(r.bounds.minimum.y),
                int(r.bounds.maximum.y),
                int(r.bounds.minimum.z),
                str(r.region_id),
            )
            for r in world.regions
        ]
        placed_tuples = [
            (
                int(item.position.x),
                int(item.position.y),
                int(item.position.z),
                int(item.radius_mm),
                bool(ew._is_bed(item)),
            )
            for item in placed
        ]
        occupied_tuples = [
            (
                int(body.pose.position.x),
                int(body.pose.position.y),
                int(body.pose.position.z),
                int(carried_radius),
                bool(body.body_id == world.self_body_id),
            )
            for body, carried_radius in occupied
        ]
        _gc.validate_world_kinematics_native(
            regions_tuples, placed_tuples, occupied_tuples, str(world.room_id)
        )
    else:
        orig = _originals.get("_validate_world")
        if orig is not None:
            orig(self, world)
            return

    self._validate_contact_optical_surface_sequences(world)


# ---------------------------------------------------------------------------
# install / uninstall
# ---------------------------------------------------------------------------

def install() -> bool:
    """Swap the native kernels in. Returns True if active. Explicit opt-in:
    nothing anywhere calls this by default."""
    global _installed
    if not HAVE_NATIVE:
        return False
    if _installed:
        return True

    from dsf_ai_service.v4 import gualaloom_v4_krimelack_dna as kdna
    from dsf_ai_service.v4 import gualaloom_v4_uf_kernel as ufk
    from dsf_ai_service.substrate import krimelack as skrim
    from dsf_ai_service.loom_model import substrate_dna as sdna
    from dsf_ai_service.loom_model import neuron as neuron_mod
    from dsf_ai_service.substrate import language_fact_strand as lfs
    from dsf_ai_service.substrate import w1_physical_receptors as w1pr
    from dsf_ai_service.substrate import embodiment_world as ew
    from dsf_ai_service import guala_home_world as ghw

    _originals["v4_feed"] = kdna.Krimelack.feed
    _originals["v4_fingerprint"] = kdna.Krimelack.fingerprint
    _originals["lang_transduce"] = kdna.LanguageKrimelack.transduce
    _originals["substrate_feed_signal"] = skrim.Krimelack.feed_signal
    _originals["cochlear_feed_signal"] = sdna.CochlearBankKrimelack.feed_signal
    _originals["visual_feed_signal"] = sdna.VisualKrimelack.feed_signal
    _originals["ufk_compute_dsf"] = ufk.compute_dsf
    _originals["neuron_compute_dsf"] = neuron_mod.compute_dsf
    _originals["sdna_compute_dsf"] = sdna.compute_dsf
    _originals["lfs_compute_dsf"] = lfs.compute_dsf
    _originals["map_inject"] = neuron_mod._map_inject
    _originals["psi_settle"] = neuron_mod.PsiLattice.settle
    _originals["_lit_surfaces_focal"] = w1pr._lit_surfaces_focal
    _originals["compute_spatial_horizon_observation"] = ghw.compute_spatial_horizon_observation
    _originals["_canonical_skeleton"] = ew._canonical_skeleton
    _originals["_validate_world"] = ew.EmbodimentWorldAuthority._validate_world

    kdna.Krimelack.feed = _v4_feed
    kdna.Krimelack.fingerprint = _v4_fingerprint
    kdna.LanguageKrimelack.transduce = _lang_transduce
    skrim.Krimelack.feed_signal = _substrate_feed_signal
    sdna.CochlearBankKrimelack.feed_signal = _cochlear_feed_signal
    sdna.VisualKrimelack.feed_signal = _visual_feed_signal
    ufk.compute_dsf = _compute_dsf
    neuron_mod.compute_dsf = _compute_dsf
    sdna.compute_dsf = _compute_dsf
    lfs.compute_dsf = _compute_dsf
    neuron_mod._map_inject = _map_inject
    neuron_mod.PsiLattice.settle = _psi_settle
    w1pr._lit_surfaces_focal = _native_lit_surfaces_focal
    ghw.compute_spatial_horizon_observation = _cached_compute_spatial_horizon_observation
    ew._canonical_skeleton = _fast_canonical_skeleton
    ew.EmbodimentWorldAuthority._validate_world = _native_validate_world

    _installed = True
    return True


def uninstall() -> None:
    """Restore the pure-Python originals (differential-test helper)."""
    global _installed
    if not _installed:
        return

    from dsf_ai_service.v4 import gualaloom_v4_krimelack_dna as kdna
    from dsf_ai_service.v4 import gualaloom_v4_uf_kernel as ufk
    from dsf_ai_service.substrate import krimelack as skrim
    from dsf_ai_service.loom_model import substrate_dna as sdna
    from dsf_ai_service.loom_model import neuron as neuron_mod
    from dsf_ai_service.substrate import language_fact_strand as lfs
    from dsf_ai_service.substrate import w1_physical_receptors as w1pr
    from dsf_ai_service.substrate import embodiment_world as ew
    from dsf_ai_service import guala_home_world as ghw

    kdna.Krimelack.feed = _originals["v4_feed"]
    kdna.Krimelack.fingerprint = _originals["v4_fingerprint"]
    kdna.LanguageKrimelack.transduce = _originals["lang_transduce"]
    skrim.Krimelack.feed_signal = _originals["substrate_feed_signal"]
    sdna.CochlearBankKrimelack.feed_signal = _originals["cochlear_feed_signal"]
    sdna.VisualKrimelack.feed_signal = _originals["visual_feed_signal"]
    ufk.compute_dsf = _originals["ufk_compute_dsf"]
    neuron_mod.compute_dsf = _originals["neuron_compute_dsf"]
    sdna.compute_dsf = _originals["sdna_compute_dsf"]
    lfs.compute_dsf = _originals["lfs_compute_dsf"]
    neuron_mod._map_inject = _originals["map_inject"]
    neuron_mod.PsiLattice.settle = _originals["psi_settle"]
    w1pr._lit_surfaces_focal = _originals["_lit_surfaces_focal"]
    ghw.compute_spatial_horizon_observation = _originals["compute_spatial_horizon_observation"]
    ew._canonical_skeleton = _originals["_canonical_skeleton"]
    ew.EmbodimentWorldAuthority._validate_world = _originals["_validate_world"]
    _HORIZON_OBS_CACHE.clear()
    _FOCAL_LIST_CACHE.clear()
    _OPTICAL_SURFACE_CANONICAL_CACHE.clear()

    _installed = False
