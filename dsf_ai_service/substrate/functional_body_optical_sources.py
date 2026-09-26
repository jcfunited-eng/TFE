"""World-only optical source binding. No lighting solver or sensory identities.

Mount addresses name physical material custody, never recognition. Immutable
compiled addresses contain no paint, light or dynamic world state. Queries
resolve the current published sources without retaining a second scene.
"""
from __future__ import annotations

from dataclasses import dataclass

from .embodiment_world import LOOK_FACES, _identifier, _physical_bands


@dataclass(frozen=True)
class NativeOpticalBinding:
    geom_name: str
    source_kind: str
    source_id: str
    part_index: int | None = None
    # Explicit environmental paint registration, never an inferred object ID.
    region_faces: tuple[tuple[int, int, str], ...] = ()

    def __post_init__(self):
        _identifier(self.geom_name, "native optical geometry")
        _identifier(self.source_id, "native optical source")
        if self.source_kind not in ("object", "part", "region", "body"):
            raise ValueError("unknown physical material source kind")
        if self.source_kind == "part":
            if type(self.part_index) is not int or self.part_index < 0:
                raise ValueError("object part requires its physical index")
        elif self.part_index is not None:
            raise ValueError("only a part source has a part index")
        if (type(self.region_faces) is not tuple or len(self.region_faces) > 6
                or (self.region_faces and self.source_kind != "region")):
            raise ValueError("bounded region-only native face registration required")
        for face in self.region_faces:
            if (type(face) is not tuple or len(face) != 3
                    or type(face[0]) is not int or face[0] not in (0, 1, 2)
                    or type(face[1]) is not int or face[1] not in (-1, 1)
                    or type(face[2]) is not str or face[2] not in LOOK_FACES):
                raise ValueError("native axis, signed face and physical room face required")
        addresses = tuple((axis, side) for axis, side, _ in self.region_faces)
        if addresses != tuple(sorted(set(addresses))):
            raise ValueError("unique canonical native region faces required")

    def as_record(self):
        return dict(geom_name=self.geom_name, source_kind=self.source_kind,
                    source_id=self.source_id, part_index=self.part_index,
                    **({"region_faces": [list(face) for face in self.region_faces]}
                       if self.region_faces else {}))

    @classmethod
    def from_record(cls, value):
        base = {"geom_name", "source_kind", "source_id", "part_index"}
        if type(value) is not dict or set(value) not in (base, base | {"region_faces"}):
            raise ValueError("native optical source fields changed")
        if "region_faces" not in value:
            return cls(**value)
        raw = value["region_faces"]
        if (type(raw) is not list or not raw or len(raw) > 6
                or any(type(face) is not list or len(face) != 3 for face in raw)):
            raise ValueError("nonempty canonical region-face record required")
        return cls(value["geom_name"], value["source_kind"], value["source_id"],
                   value["part_index"], tuple(tuple(face) for face in raw))


def _look_axes(face):
    """Existing room-surface coordinate convention, not a face detector."""
    if face in ("floor", "ceiling"):
        return 0, 1, 2, (1 if face == "floor" else -1)
    normal = 0 if face[0] == "x" else 1
    return 1-normal, 2, normal, (1 if face.endswith("min") else -1)


def validate_declaration(bindings, body_reflectance):
    if type(bindings) is not tuple or any(type(b) is not NativeOpticalBinding for b in bindings):
        raise ValueError("immutable typed native optical bindings required")
    names = tuple(b.geom_name for b in bindings)
    if names != tuple(sorted(set(names))):
        raise ValueError("unique canonical native geometry bindings required")
    if type(body_reflectance) is not tuple:
        raise ValueError("immutable declared body coatings required")
    ids = []
    for item in body_reflectance:
        if type(item) is not tuple or len(item) != 2:
            raise ValueError("body coating requires body address and six bands")
        ids.append(_identifier(item[0], "body coating owner"))
        _physical_bands(item[1], "body coating reflectance")
    if tuple(ids) != tuple(sorted(set(ids))):
        raise ValueError("unique canonical body coatings required")
    if bool(bindings) != bool(body_reflectance):
        raise ValueError("optical binding and explicit body coatings must be declared together")


def compile_bindings(mount, engine):
    """One immutable anatomical index, rebuilt only when the mount changes.

    Nothing is inferred from geometry names. Native parentage proves the
    addressed surface belongs to the declared physical object/body. Static
    room surfaces must belong to worldbody, not a moving entity.
    """
    import mujoco as mj
    import numpy as np

    bindings = mount.optical_bindings
    if not bindings:
        return ()
    model = engine._model
    names = engine.geom_names
    if (any(name is None for name in names) or len(set(names)) != len(names)
            or set(names) != {b.geom_name for b in bindings}):
        raise ValueError("every native surface requires exactly one material source")
    body_map, object_map = dict(mount.body_frames), dict(mount.object_frames)
    if set(dict(mount.body_reflectance)) != set(body_map):
        raise ValueError("every physical body requires an explicit coating")
    roots = {}
    for kind, pairs in (("body", body_map), ("object", object_map)):
        for source_id, frame in pairs.items():
            node = int(mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, frame))
            if node <= 0 or node in roots:
                raise ValueError("material source requires a unique native entity frame")
            roots[node] = (kind, source_id)
    # Native anatomy is parent-before-child. This is not a dynamic scene cache.
    owners = [None] * model.nbody
    for node in range(1, model.nbody):
        owners[node] = roots.get(node, owners[int(model.body_parentid[node])])
    by_name = {b.geom_name: b for b in bindings}
    result, material_primitives = [], set()
    for index, name in enumerate(names):
        binding = by_name[name]
        node = int(model.geom_bodyid[index])
        kind = int(model.geom_type[index])
        expected = ("object" if binding.source_kind == "part" else binding.source_kind,
                    binding.source_id)
        if binding.source_kind == "region":
            if node != 0 or kind not in (int(mj.mjtGeom.mjGEOM_PLANE), int(mj.mjtGeom.mjGEOM_BOX)):
                raise ValueError("region material requires a static native plane or box")
            if binding.region_faces:
                if kind != int(mj.mjtGeom.mjGEOM_BOX):
                    raise ValueError("region paint registration requires original BOX faces")
                # Fixed world-body anatomy: use native quaternion conversion once,
                # not eye-frame reconstruction or a guessed normal threshold.
                matrix = np.empty(9)
                mj.mju_quat2Mat(matrix, model.geom_quat[index])
                rotation = matrix.reshape(3, 3)
                for axis, side, face in binding.region_faces:
                    _, _, normal_axis, inward = _look_axes(face)
                    if side*rotation[normal_axis, axis]*inward <= 0:
                        raise ValueError("region chart is singular or faces away from the room")
        elif owners[node] != expected:
            raise ValueError("native material source differs from physical subtree owner")
        if binding.source_kind in ("object", "part"):
            address = (binding.source_id, binding.part_index)
            if address in material_primitives:
                raise ValueError("one physical object primitive cannot be painted onto two geometries")
            material_primitives.add(address)
        result.append((binding, kind))
    return tuple(result)


@dataclass(frozen=True)
class NativeMaterialSource:
    """Transient references; no duplicate persisted paint/texture custody.

    box_pattern belongs to EVERY original local box face (existing box law).
    Region looks keep physical world subrectangles and first-match ordering;
    they are NOT unit-face patterns. Native face registration is in the same
    binding; chart clipping and spatial-light integration remain downstream.
    """
    reflectance_ppm: tuple[int, ...]
    emission_ppm: tuple[int, ...]
    box_pattern: object | None = None
    region_looks: tuple = ()


@dataclass(frozen=True)
class NativeOpticalSources:
    revision: int
    native_state: object
    geometry: object
    materials: tuple[NativeMaterialSource, ...]
    regions: tuple
    emitters: tuple
    # "unretained" is NOT night/zero light; "retained" may include sampled night.
    solar_evidence: str
    # Borrow the same published transforms and immutable compiled addresses.
    world_frames: tuple
    bindings: tuple

    @property
    def solar_sample(self):
        """The same world's retained producer sample, not duplicated custody."""
        return self.native_state.solar_sample


def resolve_materials(world, compiled, *, max_material_cells):
    """Resolve authoritative current material refs, once per physical surface.

    The world's authenticated decoder/transition already validates material
    values. This boundary validates source completeness and supported charts.
    It never reconstructs full palettes or hashes physical sources per pixel.
    """
    import mujoco as mj

    if type(max_material_cells) is not int or max_material_cells < 0:
        raise ValueError("nonnegative material-cell work bound required")
    if not compiled:
        raise ValueError("native optical material sources are not mounted")
    objects = {o.object_id: o for o in world.objects}
    regions = {r.region_id: r for r in world.regions}
    coatings = dict(world.native.mount.body_reflectance)
    primitive = {"sphere": int(mj.mjtGeom.mjGEOM_SPHERE),
                 "box": int(mj.mjtGeom.mjGEOM_BOX),
                 "cylinder": int(mj.mjtGeom.mjGEOM_CYLINDER)}
    materials, patterns, cells = [], set(), 0
    registered_faces, required_faces = {}, {}

    def account(pattern, address):
        nonlocal cells
        if pattern is not None and address not in patterns:
            # Count physical chart addresses, not Python object identity (which
            # can change after cold catalog interning). No palette copies.
            patterns.add(address)
            cells += pattern.rows * pattern.columns
            if cells > max_material_cells:
                raise ValueError("native material source cell bound exceeded")

    try:
        for binding, kind in compiled:
            if binding.source_kind == "body":
                source = NativeMaterialSource(coatings[binding.source_id], (0,) * 6)
            elif binding.source_kind == "region":
                region = regions[binding.source_id]
                registered_faces.setdefault(region.region_id, set()).update(
                    face for _, _, face in binding.region_faces)
                if region.region_id not in required_faces:
                    required_faces[region.region_id] = set()
                    for index, look in enumerate(region.looks):
                        required_faces[region.region_id].add(look.face)
                        account(look.surface, ("region", region.region_id, index))
                source = NativeMaterialSource(region.reflectance_ppm, (0,) * 6,
                                              region_looks=region.looks)
            else:
                item = objects[binding.source_id]
                if binding.source_kind == "part":
                    if item.shape != "parts" or binding.part_index >= len(item.parts):
                        raise ValueError("native material part is absent")
                    part = item.parts[binding.part_index]
                    expected_kind = part.kind
                    reflectance = part.reflectance_ppm or item.reflectance_ppm
                else:
                    if item.shape == "parts":
                        raise ValueError("assembled material requires a physical part address")
                    expected_kind, reflectance = item.shape, item.reflectance_ppm
                if primitive.get(expected_kind) != kind:
                    raise ValueError("native primitive differs from physical material source")
                pattern = item.optical_surface
                if pattern is not None:
                    if binding.source_kind != "object" or expected_kind != "box":
                        raise ValueError("curved/assembled material has no fixed physical chart")
                    account(pattern, ("object", item.object_id))
                source = NativeMaterialSource(reflectance, item.emission_ppm or (0,) * 6,
                                              box_pattern=pattern)
            materials.append(source)
    except KeyError as error:
        raise ValueError("native material source is absent from current world") from error
    if (any(region.looks and region.region_id not in required_faces for region in regions.values())
            or any(not needed <= registered_faces[region]
                   for region, needed in required_faces.items())):
        raise ValueError("room pattern has no declared native surface registration")
    emitters = tuple(o for o in world.objects if any(o.emission_ppm))
    return tuple(materials), emitters


def region_face_charts(sources, receiver_row, axis, side, *, max_charts):
    """Attach ordered room looks to one explicitly registered native BOX face.

    This prepares physical paint coordinates only. The caller must clip to the
    actual panel and preserve first-match order; these charts never occlude.
    The source view was admitted by the existing world query. No state changes.
    """
    import numpy as np
    from .functional_body_renderer import BOX
    from .functional_body_visibility import PlanarSurface

    geometry = sources.geometry
    if (type(max_charts) is not int or max_charts < 0
            or type(receiver_row) is not int or not 0 <= receiver_row < len(sources.bindings)
            or type(axis) is not int or axis not in (0, 1, 2)
            or type(side) is not int or side not in (-1, 1)):
        raise ValueError("bounded original native face request required")
    binding, kind = sources.bindings[receiver_row]
    if binding.source_kind != "region" or kind != BOX or geometry.kinds[receiver_row] != BOX:
        raise ValueError("registered native region BOX face required")
    looks = sources.materials[receiver_row].region_looks
    if len(looks) > max_charts:
        raise ValueError("region chart input exceeds declared bound")
    face = next((face for a, b, face in binding.region_faces
                 if (a, b) == (axis, side)), None)
    if face is None:
        return ()  # this physical face carries only its base coating
    selected = tuple(look for look in looks if look.face == face)
    if not selected:
        return ()
    along, up, _, _ = _look_axes(face)
    rotation = np.asarray(geometry.rotation_world).reshape(3, 3)
    origin = np.asarray(geometry.origin_world_m)
    normal = side*geometry.rotations_eye[receiver_row, :, axis]
    centre = (geometry.positions_eye_m[receiver_row] +
              normal*geometry.sizes_m[receiver_row, axis])
    matrix = np.stack((normal, rotation[along], rotation[up]))
    try:
        inverse = np.linalg.inv(matrix)
    except np.linalg.LinAlgError as error:
        raise ValueError("singular registered room-pattern chart") from error
    fixed = inverse @ np.array((normal @ centre, -origin[along], -origin[up]))
    u, v = inverse[:, 1], inverse[:, 2]
    if not np.isfinite(inverse).all() or not np.isfinite(fixed).all():
        raise ValueError("registered chart exceeds numerical domain")
    quad = np.array(((0., 0.), (1., 0.), (1., 1.), (0., 1.)))
    result = []
    for look in selected:
        point = fixed + u*(look.from_mm/1000) + v*(look.low_mm/1000)
        axes = np.array((u*((look.to_mm-look.from_mm)/1000),
                         v*((look.high_mm-look.low_mm)/1000)))
        chart = PlanarSurface.from_chart(point, axes, quad, max_corners=4)
        result.append((chart, look.surface))
    return tuple(result)
