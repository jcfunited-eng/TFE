"""FB-01ai standalone native-head -> ordinary retinal producer -> sensory use.

Controlled body/world inputs, not learned gaze or full ordinary motor settlement.
No pytest/conftest/network. Old root-based cognition remains outside this slice.
"""
from dataclasses import replace
import math
import resource
import time
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from dsf_ai_service.guala_functional_loop import (
    _world_retina_u8, PUPIL_GAIN_MAX, PUPIL_MID_RANGE,
    PUPIL_HIGHLIGHT_PERCENTILE, WORLD_FOCAL_VALUES, WORLD_FOCAL_SITES,
)
from dsf_ai_service.guala_functional_organism import FunctionalOrganism, Sensed
from dsf_ai_service.guala_world_sensorium import retinal_carriage
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority, AnatomicalEffortCommand, PORT_ID, encode_command,
)
from dsf_ai_service.substrate.functional_body_retinal import (
    RETINAL_APERTURES, native_retinal_radiance,
)
from dsf_ai_service.substrate.w1_physical_receptors import retinal_irradiance_field
from test_functional_body_optical_sources import (
    KEY, INTENT, declaration, mount, advance, world,
)
from test_functional_body_retinal import bench, retinal_apertures


def eyes(axes, **positions):
    return tuple((a[0], a[1], a[2], positions[a[1]], *a[4:]) if a[1] in positions else a
                 for a in axes)


def source(auth, rotation=(0, 0), **changes):
    args = dict(expected_revision=auth.observation_snapshot().revision,
                retinal_rotation=rotation, max_geoms=256, max_material_cells=32768)
    args.update(changes)
    return auth.native_optical_sources(**args)


def field(auth, rotation=(0, 0)):
    return native_retinal_radiance(source(auth, rotation), RETINAL_APERTURES,
        1/510, max_shadow_tests=20000000, max_nodes=262144)[0]


def prior_transducer(bands, transmission, pupil=True):
    # Independent literal predecessor transduction, not the candidate helper.
    rgb = np.stack(((bands[:, 0]+bands[:, 1])/2, (bands[:, 2]+bands[:, 3])/2,
                    (bands[:, 4]+bands[:, 5])/2), axis=1)
    middle, bright = float(np.median(rgb)), float(np.percentile(rgb, PUPIL_HIGHLIGHT_PERCENTILE))
    gain = 1.
    if pupil and middle > 0 and bright > 0:
        wanted = min(PUPIL_GAIN_MAX, max(1., PUPIL_MID_RANGE/middle), max(1., 1./bright))
        gain = float(2**int(math.log2(wanted)))
    pre = rgb*gain
    return (tuple(np.rint(np.minimum(1., pre)*(255*float(transmission))).astype(np.int64).ravel()),
            gain, np.packbits((pre[-WORLD_FOCAL_SITES:] >= 1).ravel(), bitorder="little").tobytes())


class NativeRetinalConsumptionTests(unittest.TestCase):
    def axes(self):
        return FunctionalOrganism.genesis(identity="offline-native-retinal-consumption",
                                           organism_tick=100).body_axes

    def test_current_head_reaches_existing_transducer_and_real_sensory_consumer(self):
        auth, _, _ = bench()
        axes = self.axes()
        snapshot = auth.observation_snapshot()
        before = auth.encoded_snapshot()
        start = time.perf_counter()
        pixels, evidence = _world_retina_u8(snapshot, axes, world=auth)
        seconds = time.perf_counter()-start
        self.assertEqual(len(pixels), 58005)
        _, _, transmission = retinal_carriage(axes, include_neck=False)
        expected, gain, flags = prior_transducer(field(auth), transmission)
        self.assertEqual(pixels, expected)
        self.assertEqual(evidence.pupil_gain, gain)
        self.assertEqual(evidence.eyelid_transmission, transmission)
        self.assertEqual(evidence.focal_saturation_mask, flags)
        self.assertEqual(len(flags), 7200)
        self.assertEqual(auth.encoded_snapshot(), before)
        wide = pixels[27*3:135*3]
        wide = tuple(sum(wide[i:i+3])//3 for i in range(0, len(wide), 3))
        sensed = Sensed(snapshot, pixels[-WORLD_FOCAL_VALUES:], "world", None, None,
                        wide, optical_evidence=evidence)
        organism = FunctionalOrganism.genesis(identity="offline-native-retinal-consumption",
                                              organism_tick=100)
        decision = organism.decide(sensed)
        self.assertIsNotNone(decision)
        self.assertEqual(organism._state["streams"]["sight_luminance"][-1],
                         round(sum(pixels[-WORLD_FOCAL_VALUES:])/WORLD_FOCAL_VALUES/255, 6))
        self.assertEqual(auth.encoded_snapshot(), before)
        print(dict(native_retinal_producer_s=seconds, u8_values=len(pixels),
                   aperture_bytes=RETINAL_APERTURES.nbytes, consumer="real decide, not full settle"),
              flush=True)

    def test_declared_apertures_and_eye_rotation_have_one_pose_authority(self):
        np.testing.assert_array_equal(RETINAL_APERTURES, retinal_apertures())
        self.assertFalse(RETINAL_APERTURES.flags.writeable)
        auth, _, _ = bench(lamps=False)
        original = source(auth)
        head = next(f for f in auth.observation_snapshot().native.world_frames if f.name == "guala/head")
        r = np.array(head.rotation_world).reshape(3, 3)
        np.testing.assert_allclose(original.geometry.origin_world_m,
                                   np.asarray(head.position_m)+r @ (.08, 0., .03), rtol=0, atol=1e-14)
        np.testing.assert_allclose(np.asarray(original.geometry.rotation_world).reshape(3, 3),
                                   r, rtol=0, atol=1e-14)
        axes = self.axes()
        neutral = _world_retina_u8(auth.observation_snapshot(), axes, world=auth)
        neck_only = eyes(axes, neck_yaw=20000, neck_pitch=10000)
        self.assertEqual(neutral, _world_retina_u8(auth.observation_snapshot(), neck_only, world=auth))
        eye_axes = eyes(axes, left_eye_yaw=12000, left_eye_pitch=7000)
        turned = _world_retina_u8(auth.observation_snapshot(), eye_axes, world=auth)
        self.assertNotEqual(neutral[0], turned[0])
        yaw, pitch = math.radians(12), math.radians(7)
        expected_forward = r @ np.array((math.cos(yaw)*math.cos(pitch),
                                         math.sin(yaw)*math.cos(pitch), math.sin(pitch)))
        view = source(auth, (12000, 7000))
        np.testing.assert_allclose(np.asarray(view.geometry.rotation_world).reshape(3, 3)[:, 0],
                                   expected_forward, rtol=0, atol=1e-14)

    def test_real_head_effort_cold_pixels_and_next_motor(self):
        auth, objects, regions = bench(lamps=False)
        axes = self.axes()
        before = _world_retina_u8(auth.observation_snapshot(), axes, world=auth)
        command = AnatomicalEffortCommand((("guala/head/pitch/effort", .008),
                                           ("guala/head/roll/effort", .015)), 50000)
        prepared = auth.prepare_port_command(port_id=PORT_ID, command_payload=encode_command(command),
            expected_revision=auth.observation_snapshot().revision,
            causal_intent_receipt_sha256=INTENT, available_motor_work_j=1.)
        auth.commit_prepared_action(prepared)
        moved = _world_retina_u8(auth.observation_snapshot(), axes, world=auth)
        self.assertNotEqual(before[0], moved[0])
        encoded = auth.encoded_snapshot()
        fresh = EmbodimentWorldAuthority(authority_key=KEY, receipt_capacity=2,
                                        initial_objects=objects, regions=regions)
        fresh.restore_encoded(encoded)
        self.assertEqual(moved, _world_retina_u8(fresh.observation_snapshot(), axes, world=fresh))
        self.assertEqual(fresh.encoded_snapshot(), encoded)
        a, b = advance(auth, motor=True), advance(fresh, motor=True)
        # The existing object codec omits all-zero emission. Compare the full
        # authenticated record, and prove this specific representation alias
        # is the only warm/cold observation difference.
        self.assertEqual(a.execution_receipt.as_record(), b.execution_receipt.as_record())
        self.assertEqual(a.native_work, b.native_work)
        for warm, cold in ((a.execution_receipt.before, b.execution_receipt.before),
                           (a.execution_receipt.after, b.execution_receipt.after)):
            normalized = tuple(replace(o, emission_ppm=()) if o.emission_ppm == (0,)*6 else o
                               for o in warm.objects)
            self.assertEqual(replace(warm, objects=normalized), cold)
        auth.commit_prepared_action(a)
        fresh.commit_prepared_action(b)
        self.assertEqual(auth.encoded_snapshot(), fresh.encoded_snapshot())

    def test_native_overrange_light_saturates_only_at_existing_transducer(self):
        base, objects, regions = bench(lamps=False, card_pattern=False)
        objects = (replace(objects[0], reflectance_ppm=(1000000,)*6,
                           emission_ppm=(1000000,)*6), objects[1])
        auth = EmbodimentWorldAuthority(authority_key=KEY, receipt_capacity=2,
                                       initial_objects=objects, regions=regions)
        mount(auth, base._state.world.native.mount)
        bands = field(auth)
        self.assertGreater(float(bands.max()), 1.)
        axes = self.axes()
        pixels, evidence = _world_retina_u8(auth.observation_snapshot(), axes, pupil=False, world=auth)
        expected, _, mask = prior_transducer(bands, retinal_carriage(axes, include_neck=False)[2], pupil=False)
        self.assertEqual(pixels, expected)
        self.assertEqual(evidence.focal_saturation_mask, mask)
        self.assertTrue(any(mask))
        self.assertLessEqual(max(pixels), 255)

    def test_missing_ambiguous_tracking_and_stale_camera_paths_refuse(self):
        declared = declaration()
        root = ET.fromstring(declared.xml)
        head = root.find(".//body[@name='guala/head']")
        camera = head.find("camera")
        self.assertIsNotNone(camera)
        head.remove(camera)
        auth = world()
        mount(auth, replace(declared, xml=ET.tostring(root, encoding="unicode")))
        before = auth.encoded_snapshot()
        with self.assertRaisesRegex(ValueError, "retinal camera is not mounted"):
            _world_retina_u8(auth.observation_snapshot(), self.axes(), world=auth)
        self.assertEqual(before, auth.encoded_snapshot())
        for duplicate in (False, True):
            root = ET.fromstring(declared.xml)
            head = root.find(".//body[@name='guala/head']")
            if duplicate:
                ET.SubElement(head, "camera", name="extra", mode="fixed")
                message = "one declared mono"
            else:
                head.find("camera").set("mode", "track")
                message = "fixed"
            fresh = world()
            before = fresh.encoded_snapshot()
            with self.assertRaisesRegex(ValueError, message):
                mount(fresh, replace(declared, xml=ET.tostring(root, encoding="unicode")))
            self.assertEqual(before, fresh.encoded_snapshot())
        auth, _, _ = bench(lamps=False)
        with self.assertRaisesRegex(RuntimeError, "current world"):
            _world_retina_u8(auth.observation_snapshot(), self.axes())
        with self.assertRaisesRegex(ValueError, "revision"):
            source(auth, expected_revision=auth.observation_snapshot().revision-1)
        with self.assertRaisesRegex(ValueError, "exclusive typed"):
            source(auth, frame_name="guala/head", origin_local_m=(.08, 0., .03))
        with self.assertRaisesRegex(ValueError, "exclusive typed"):
            source(auth, rotation=(True, 0))

    def test_legacy_producer_pixels_and_metadata_remain_identical(self):
        auth = world()
        snapshot, axes = auth.observation_snapshot(), self.axes()
        heading, pitch, transmission = retinal_carriage(axes)
        bands = np.array(retinal_irradiance_field(snapshot,
            retinal_heading_offset_millidegrees=heading,
            retinal_pitch_offset_millidegrees=pitch, include_focal=True), dtype=float)
        for pupil in (False, True):
            pixels, evidence = _world_retina_u8(snapshot, axes, pupil=pupil)
            expected, gain, mask = prior_transducer(bands, transmission, pupil)
            self.assertEqual(pixels, expected)
            self.assertEqual((evidence.pupil_gain, evidence.eyelid_transmission,
                              evidence.focal_saturation_mask), (gain, transmission, mask))


if __name__ == "__main__":
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(NativeRetinalConsumptionTests))
    print(dict(native_retinal_consumption_s=time.perf_counter()-started,
               peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss), flush=True)
    raise SystemExit(not result.wasSuccessful())
