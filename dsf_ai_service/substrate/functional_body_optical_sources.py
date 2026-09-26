"""World-only optical source binding. No lighting solver or sensory identities.

Mount addresses name physical material custody, never recognition. Immutable
compiled addresses contain no paint, light or dynamic world state. Queries
resolve the current published sources without retaining a second scene.
"""
from __future__ import annotations

from dataclasses import dataclass

from .embodiment_world import _identifier, _physical_bands


@dataclass(frozen=True)
class NativeOpticalBinding:
    geom_name: str
    source_kind: str
    source_id: str
    part_index: int | None = None

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

    def as_record(self):
        return dict(geom_name=self.geom_name, source_kind=self.source_kind,
                    source_id=self.source_id, part_index=self.part_index)

    @classmethod
    def from_record(cls, value):
        if type(value) is not dict or set(value) != {
                "geom_name", "source_kind", "source_id", "part_index"}:
            raise ValueError("native optical source fields changed")
        return cls(**value)


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
    they are NOT unit-face patterns. Their lighting/chart integration is not
    supplied by this source resolver.
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
    # "unretained" is NOT night/zero light. No available sample exists yet.
    solar_evidence: str


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
    materials, patterns, admitted_regions, cells = [], set(), set(), 0

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
                if region.region_id not in admitted_regions:
                    for index, look in enumerate(region.looks):
                        account(look.surface, ("region", region.region_id, index))
                    admitted_regions.add(region.region_id)
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
    emitters = tuple(o for o in world.objects if any(o.emission_ppm))
    return tuple(materials), emitters
