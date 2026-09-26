"""FB-01z standalone source-custody proof. Never imports pytest/conftest.

Declares an isolated mechanical bench, not a copied production organism or
complete home renderer. Uniform illumination in render() is explicit test
illumination, NOT a replacement for lamp/window/sun transport. Controlled
solar clock input is used only to exercise the existing timed world transition.
"""
from dataclasses import replace
import math
import os
import resource
import time
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from dsf_ai_service.substrate.embodiment_world import (
    AdvancePhysicalTimeCommand, AnatomicalEffortCommand, EmbodiedObject,
    EmbodimentWorldAuthority, NativeWorldMount, ObjectOpticalSurface, ObjectPart,
    PositionMM, ScreenBroadcast, SolarCoupling, SurfaceLookMM, PORT_ID,
    _default_regions, encode_command,
)
from dsf_ai_service.substrate.functional_body_anatomy import append_reference_biped
from dsf_ai_service.substrate.functional_body_native import MechanicalLimits
from dsf_ai_service.substrate.functional_body_optical_sources import (
    NativeOpticalBinding, resolve_materials,
)
from dsf_ai_service.substrate.functional_body_materials import PlanarMaterial
from dsf_ai_service.substrate.functional_body_renderer import integrate_materials


KEY = b"offline-functional-body-optical-source-proof"
INTENT = "b" * 64
WHITE, BLACK = (1000000,) * 6, (0,) * 6
PATTERN = ObjectOpticalSurface(2, 2, (WHITE, BLACK), (0, 1, 1, 0))
LIMITS = MechanicalLimits(1000, 250, .008, .03, .005, .015)


def declaration():
    root = ET.fromstring("""<mujoco model="optical-source-bench">
      <compiler angle="radian" inertiafromgeom="true"/><size memory="8M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 0"/>
      <worldbody>
        <geom name="wall" type="box" pos="-.005 2.5 1.5" size=".005 2.5 1.5"/>
        <body name="other" pos="4.75 4.75 0" quat="0 0 0 1">
          <geom name="other/surface" type="sphere" pos="0 0 .25" size=".25"/>
        </body>
        <body name="card" pos="1.5 1 0">
          <geom name="card/surface" type="box" pos="0 0 1" size=".01 .1 .1"/>
        </body>
        <body name="lamp" pos="3 3 0">
          <geom name="lamp/a" type="sphere" pos="-.1 0 .1" size=".1"/>
          <geom name="lamp/b" type="sphere" pos=".1 0 .1" size=".1"/>
        </body>
      </worldbody><actuator/><sensor/>
    </mujoco>""")
    append_reference_biped(root.find("worldbody"), root.find("actuator"),
                           root.find("sensor"), root_position_m=(1., 1., .54))
    # Traverse this declared subtree, not a semantic name heuristic.
    guala = next(b for b in root.find("worldbody").findall("body") if b.get("name") == "guala/pelvis")
    bindings = [NativeOpticalBinding(g.get("name"), "body", "guala-body-1")
                for g in guala.iter("geom")]
    bindings.extend((
        NativeOpticalBinding("wall", "region", "W1-region-A"),
        NativeOpticalBinding("other/surface", "body", "w1-body-2"),
        NativeOpticalBinding("card/surface", "object", "card"),
        NativeOpticalBinding("lamp/a", "part", "lamp", 0),
        NativeOpticalBinding("lamp/b", "part", "lamp", 1),
    ))
    return NativeWorldMount(
        ET.tostring(root, encoding="unicode"), LIMITS, "guala/pelvis",
        (("guala-body-1", "guala/pelvis"), ("w1-body-2", "other")),
        (("card", "card"), ("lamp", "lamp")),
        tuple(sorted((m.get("name"), "guala-body-1") for m in root.find("actuator"))),
        tuple(sorted(bindings, key=lambda b: b.geom_name)),
        (("guala-body-1", (400000,) * 6), ("w1-body-2", (300000,) * 6)),
    )


def world(*, solar=False, looks=False):
    objects = (
        EmbodiedObject("card", 150, 100, PositionMM(1500, 1000, 0),
            reflectance_ppm=(600000,) * 6, optical_surface=PATTERN,
            shape="box", size_mm=(20, 200, 200), elevation_mm=900),
        EmbodiedObject("lamp", 250, 500, PositionMM(3000, 3000, 0),
            reflectance_ppm=(200000,) * 6, emission_ppm=(100000,) * 6,
            shape="parts", parts=(
                ObjectPart("sphere", (-100, 0, 100), (200, 200, 200), WHITE),
                ObjectPart("sphere", (100, 0, 100), (200, 200, 200)),
            )),
    )
    regions = _default_regions()
    if looks:
        regions = (replace(regions[0], looks=(
            SurfaceLookMM("x-min", 200, 400, 500, 700, PATTERN),
            SurfaceLookMM("x-min", 300, 500, 600, 800, PATTERN),
        )), *regions[1:])
    return EmbodimentWorldAuthority(authority_key=KEY, receipt_capacity=2,
        initial_objects=objects, regions=regions,
        solar_coupling=SolarCoupling(("W1-region-B",), ()) if solar else None,
        screen_broadcasts=(ScreenBroadcast("card", (BLACK, (250000,) * 6), 1),))


def mount(authority, declared=None):
    prior = authority.encoded_snapshot()
    prepared = authority.prepare_native_mount(declared or declaration(),
        expected_revision=0, causal_intent_receipt_sha256=INTENT)
    if authority.encoded_snapshot() != prior:
        raise AssertionError("mount preparation mutated current state")
    authority.commit_prepared_action(prepared)


def query(authority, **changes):
    args = dict(expected_revision=authority._state.world.revision,
                frame_name="guala/head", origin_local_m=(.08, 0., .03),
                max_geoms=256, max_material_cells=4)
    args.update(changes)
    return authority.native_optical_sources(**args)


def advance(authority, *, motor=False):
    command = (AnatomicalEffortCommand(
        (("guala/left/digit-1/distal/flexion/effort", .0002),), 1000)
        if motor else AdvancePhysicalTimeCommand(1000))
    return authority.prepare_port_command(port_id=PORT_ID,
        command_payload=encode_command(command), expected_revision=authority._state.world.revision,
        causal_intent_receipt_sha256=INTENT, available_motor_work_j=1.)


def render(sources):
    """Only the explicit uniform-light bench consumer; no full-light claim."""
    if any(m.region_looks for m in sources.materials):
        raise ValueError("bench consumer has no region-look chart integration")
    incident = (.75,) * 6
    base, faces = [], []
    for index, material in enumerate(sources.materials):
        base.append(PlanarMaterial(material.reflectance_ppm, material.emission_ppm, incident))
        if material.box_pattern is not None:
            painted = PlanarMaterial(material.reflectance_ppm, material.emission_ppm,
                                     incident, material.box_pattern)
            faces.extend((index, axis, side, painted) for axis in range(3) for side in (-1, 1))
    # Independent physically addressed pencil of rays to the declared card.
    # The fixture card centre is declared world geometry, not a cognitive oracle.
    target = np.array((1.5, 1., 1.)) - sources.geometry.origin_world_m
    direction = np.asarray(sources.geometry.rotation_world).reshape(3, 3).T @ target
    h = math.atan2(direction[1], direction[0])
    mu = direction[2] / np.linalg.norm(direction)
    sites = np.array(((h-.02, h+.02, mu-.02, mu+.02),))
    return integrate_materials(sources.geometry, sites, tuple(base), 1/510,
        face_materials=tuple(faces), max_material_cells=24)


class SourceCustodyTests(unittest.TestCase):
    def test_fresh_sources_reference_all_current_materials_and_fixed_charts(self):
        authority = world(looks=True)
        mount(authority)
        before = authority.encoded_snapshot()
        started = time.perf_counter()
        sources = query(authority, max_material_cells=12)
        elapsed = time.perf_counter() - started
        current, engine = authority._state.world, authority._native_scratch
        self.assertIs(sources.native_state, current.native)
        self.assertIs(sources.regions, current.regions)
        self.assertEqual(len(sources.materials), engine._model.ngeom)
        rows = dict(zip(engine.geom_names, sources.materials))
        card, lamp = current.objects
        self.assertIs(rows["card/surface"].box_pattern, card.optical_surface)
        self.assertIs(rows["card/surface"].reflectance_ppm, card.reflectance_ppm)
        self.assertIs(rows["lamp/a"].reflectance_ppm, lamp.parts[0].reflectance_ppm)
        self.assertIs(rows["lamp/b"].reflectance_ppm, lamp.reflectance_ppm)
        self.assertIs(rows["wall"].region_looks, current.regions[0].looks)
        self.assertEqual([look.from_mm for look in rows["wall"].region_looks], [200, 300])
        self.assertEqual(sources.emitters, (lamp,))  # not duplicated for its two parts
        self.assertIs(sources.emitters[0], lamp)
        self.assertEqual(sources.solar_evidence, "absent")
        self.assertEqual(authority.encoded_snapshot(), before)
        print(f"source_query geoms={len(rows)} seconds={elapsed:.6f} "
              f"encoded_bytes={len(before)}", flush=True)

    def test_real_emission_successor_cold_query_and_next_motor_are_exact(self):
        authority = world()
        mount(authority)
        prior = query(authority)
        initial = render(prior)
        old_clock = os.environ.get("GUALA_SOLAR_UTC_OVERRIDE")
        try:
            os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "1"
            prepared = advance(authority)
            authority.commit_prepared_action(prepared)
            successor = query(authority)
            image = render(successor)
            self.assertTrue(np.any(image[0] > initial[0] + initial[1] + image[1]))
            self.assertEqual(len(prior.emitters), 1)
            self.assertEqual(len(successor.emitters), 2)
            encoded = authority.encoded_snapshot()
            fresh = world()
            fresh.restore_encoded(encoded)
            os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "0"
            restored = query(fresh)  # must NOT sample this new clock
            self.assertEqual(restored.materials, successor.materials)
            self.assertEqual(restored.emitters, successor.emitters)
            for field in ("kinds", "sizes_m", "positions_eye_m", "rotations_eye"):
                np.testing.assert_array_equal(getattr(restored.geometry, field),
                                              getattr(successor.geometry, field))
            cold_image = render(restored)
            for a, b in zip(image, cold_image):
                np.testing.assert_array_equal(a, b)
            self.assertEqual(fresh.encoded_snapshot(), encoded)
            a, b = advance(authority, motor=True), advance(fresh, motor=True)
            self.assertEqual(a.execution_receipt, b.execution_receipt)
            authority.commit_prepared_action(a)
            fresh.commit_prepared_action(b)
            self.assertEqual(authority.encoded_snapshot(), fresh.encoded_snapshot())
        finally:
            if old_clock is None:
                os.environ.pop("GUALA_SOLAR_UTC_OVERRIDE", None)
            else:
                os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = old_clock

    def test_successor_paint_and_palette_are_resolved_without_a_color_cache(self):
        authority = world()
        mount(authority)
        before = authority.encoded_snapshot()
        current = authority._state.world
        replacement = ObjectOpticalSurface(2, 2, (WHITE, BLACK), (1, 0, 0, 1))
        # Controlled pure source-resolver test, not a fabricated world action.
        next_card = replace(current.objects[0], reflectance_ppm=(100000,) * 6,
                            optical_surface=replacement)
        next_world = replace(current, objects=(next_card, current.objects[1]))
        rows, _ = resolve_materials(next_world, authority._native_scratch.optical_source_bindings,
                                    max_material_cells=4)
        row = rows[authority._native_scratch.geom_names.index("card/surface")]
        self.assertIs(row.reflectance_ppm, next_card.reflectance_ppm)
        self.assertIs(row.box_pattern, replacement)
        self.assertEqual(authority.encoded_snapshot(), before)

    def test_missing_duplicate_and_wrong_owner_bindings_refuse_without_publication(self):
        original = declaration()
        for modified in (
            replace(original, optical_bindings=original.optical_bindings[:-1]),
            replace(original, optical_bindings=tuple(
                replace(b, source_id="lamp") if b.geom_name == "card/surface" else b
                for b in original.optical_bindings)),
        ):
            authority = world()
            before = authority.encoded_snapshot()
            with self.assertRaises(ValueError):
                mount(authority, modified)
            self.assertEqual(authority.encoded_snapshot(), before)
        with self.assertRaises(ValueError):
            replace(original, optical_bindings=(original.optical_bindings[0],
                                                *original.optical_bindings))
        with self.assertRaises(ValueError):
            replace(original, body_reflectance=())

    def test_hidden_unsupported_sources_and_query_bounds_fail_closed(self):
        authority = world()
        mount(authority)
        before = authority.encoded_snapshot()
        for args in (dict(expected_revision=0), dict(max_geoms=1),
                     dict(max_material_cells=3), dict(max_material_cells=-1)):
            with self.assertRaises(ValueError):
                query(authority, **args)
            self.assertEqual(authority.encoded_snapshot(), before)
        current = authority._state.world
        invalids = (
            (replace(current.objects[0], shape="sphere", size_mm=(), optical_surface=None),
             current.objects[1]),
            (current.objects[0], replace(current.objects[1], optical_surface=PATTERN)),
        )
        for objects in invalids:
            with self.assertRaises(ValueError):
                resolve_materials(replace(current, objects=objects),
                    authority._native_scratch.optical_source_bindings, max_material_cells=4)
        # Source still missing even when the native geometry would be invisible.
        compiled = tuple((replace(b, source_id="absent") if b.source_kind == "region" else b, kind)
                         for b, kind in authority._native_scratch.optical_source_bindings)
        with self.assertRaises(ValueError):
            resolve_materials(current, compiled, max_material_cells=4)
        self.assertEqual(authority.encoded_snapshot(), before)

    def test_source_admission_work_is_bounded_before_resolution_and_shared_per_region(self):
        authority = world(looks=True)
        mount(authority)
        before = authority.encoded_snapshot()
        # Both inputs are invalid; primitive admission must run FIRST.
        with self.assertRaisesRegex(ValueError, "primitive bound"):
            query(authority, max_geoms=1, max_material_cells=-1)

        class CountedLooks(tuple):
            iterations = 0
            def __iter__(self):
                self.iterations += 1
                return super().__iter__()

        # Instrument only this pure resolver's read work. These unchanged
        # physical looks are not published; no behavioral outcome is mocked.
        current = authority._state.world
        looks = CountedLooks(current.regions[0].looks)
        region = replace(current.regions[0], looks=looks)
        probe = replace(current, regions=(region, *current.regions[1:]))
        compiled = authority._native_scratch.optical_source_bindings
        wall = next(pair for pair in compiled if pair[0].source_kind == "region")
        # Multiple static wall geometries can share one room's paint/look law.
        resolve_materials(probe, (*compiled, wall, wall), max_material_cells=12)
        self.assertEqual(looks.iterations, 1)
        self.assertEqual(authority.encoded_snapshot(), before)

    def test_sun_evidence_never_reads_clock_or_turns_unknown_into_night(self):
        authority = world(solar=True)
        mount(authority)
        before = authority.encoded_snapshot()
        old_clock = os.environ.get("GUALA_SOLAR_UTC_OVERRIDE")
        try:
            os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "not-a-clock"
            source = query(authority)  # existing solar_sun() would raise here
            self.assertEqual(source.solar_evidence, "unretained")
            self.assertIs(source.regions, authority._state.world.regions)
            self.assertEqual(authority.encoded_snapshot(), before)
        finally:
            if old_clock is None:
                os.environ.pop("GUALA_SOLAR_UTC_OVERRIDE", None)
            else:
                os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = old_clock

    def test_old_mount_bytes_and_current_mount_codec_are_unambiguous(self):
        current = declaration()
        old = replace(current, optical_bindings=(), body_reflectance=())
        record = old.as_record()
        self.assertEqual(record["schema"], "guala.native.world-mount.v1")
        self.assertNotIn("optical_bindings", record)
        self.assertEqual(NativeWorldMount.from_record(record).as_record(), record)
        self.assertEqual(NativeWorldMount.from_record(current.as_record()), current)
        authority = world()
        mount(authority, old)
        before = authority.encoded_snapshot()
        with self.assertRaises(ValueError):
            query(authority)
        self.assertEqual(authority.encoded_snapshot(), before)
        bad = current.as_record()
        bad["optical_bindings"] = []
        with self.assertRaises(ValueError):
            NativeWorldMount.from_record(bad)


if __name__ == "__main__":
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SourceCustodyTests))
    print(f"source_proof elapsed_s={time.perf_counter()-started:.6f} "
          f"peak_rss_kib={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}", flush=True)
    raise SystemExit(not result.wasSuccessful())
