"""Standalone FB-01aa retention proof; no pytest, network or live organism.

Clock overrides are controlled external environmental inputs. Codec probes are
explicit integrity falsifiers, not learned behavior or physical observations.
Reuses the accepted FB-01z isolated material bench; no complete-home claim.
"""
from dataclasses import replace
import json
import os
import resource
import time
import unittest

from dsf_ai_service.substrate.embodiment_world import (
    AdvancePhysicalTimeCommand, AnatomicalEffortCommand, NativeSolarSample, NativeWorldObservation,
    NativeWorldState, PORT_ID, encode_command,
)
from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
    ThermallyCoupledEmbodimentWorldAuthority,
)
from test_functional_body_optical_sources import KEY, INTENT, advance, mount, query, world
from test_functional_body_world import world as thermal_bench


def coupled_world():
    # Reuse explicit bench declarations, not a live checkpoint or fabricated outcome.
    optical = world(solar=True)
    thermal = thermal_bench(thermal=True, measured_core=True)
    return ThermallyCoupledEmbodimentWorldAuthority(
        authority_key=KEY, receipt_capacity=2,
        initial_objects=optical._state.world.objects,
        regions=optical._state.world.regions,
        solar_coupling=optical._solar_coupling,
        screen_broadcasts=optical._screen_broadcasts,
        thermal_anatomy=thermal._thermal_anatomy)


def prepare(authority, *, motor=False):
    if not isinstance(authority, ThermallyCoupledEmbodimentWorldAuthority):
        return advance(authority, motor=motor)
    # Same mechanical command/work as the optical bench. This retention-only
    # experiment declares zero basal input, NOT measured organism metabolism.
    command = (AnatomicalEffortCommand(
        (("guala/left/digit-1/distal/flexion/effort", .0002),), 1000)
        if motor else AdvancePhysicalTimeCommand(1000))
    return authority.prepare_port_command(port_id=PORT_ID,
        command_payload=encode_command(command), expected_revision=authority._state.world.revision,
        causal_intent_receipt_sha256=INTENT, available_motor_work_j=1.,
        basal_heat_nanojoules=0)


class SolarCustodyTests(unittest.TestCase):
    def setUp(self):
        self.prior_clock = os.environ.get("GUALA_SOLAR_UTC_OVERRIDE")

    def tearDown(self):
        if self.prior_clock is None:
            os.environ.pop("GUALA_SOLAR_UTC_OVERRIDE", None)
        else:
            os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = self.prior_clock

    def settle(self, authority, second, *, motor=False):
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = str(second)
        prepared = prepare(authority, motor=motor)
        authority.commit_prepared_action(prepared)
        return query(authority)

    def test_zero_time_mount_preserves_unknown_absent_and_v1_codecs(self):
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "invalid-clock"
        authority = world(solar=True)
        mount(authority)
        before = authority.encoded_snapshot()
        source = query(authority)
        self.assertEqual(source.solar_evidence, "unretained")
        self.assertIsNone(source.solar_sample)
        with self.assertRaisesRegex(ValueError, "has not been sampled"):
            authority.solar_sun()
        for obj, codec, schema in (
            (source.native_state, NativeWorldState, "guala.native.world-state.v1"),
            (authority.observation_snapshot().native, NativeWorldObservation,
             "guala.native.world-observation.v1"),
        ):
            record = obj.as_record()
            self.assertEqual(record["schema"], schema)
            self.assertNotIn("solar_sample", record)
            self.assertEqual(codec.from_record(record), obj)
        self.assertEqual(authority.encoded_snapshot(), before)
        absent = world()
        mount(absent)
        self.assertEqual(query(absent).solar_evidence, "absent")
        self.assertIsNone(absent.solar_sun())
        # Unmounted legacy reader and cold state are untouched by native retention.
        legacy = world(solar=True)
        encoded = legacy.encoded_snapshot()
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "46800"
        self.assertEqual(legacy.solar_sun(), legacy._solar_coupling.sun_vector(46800))
        fresh = world(solar=True)
        fresh.restore_encoded(encoded)
        self.assertEqual(fresh.encoded_snapshot(), encoded)
        pending = legacy.prepare_port_command(port_id=PORT_ID,
            command_payload=encode_command(AdvancePhysicalTimeCommand(1000)),
            expected_revision=0, causal_intent_receipt_sha256="b" * 64)
        with legacy.prepared_action_visibility_transaction(pending):
            self.assertEqual(legacy.solar_sun(), legacy._solar_coupling.sun_vector(46800))
        legacy.discard_prepared_action(pending)
        self.assertEqual(legacy.encoded_snapshot(), encoded)

    def test_real_successor_aligns_sun_sky_screen_and_changes_below_sky_quantization(self):
        authority = world(solar=True)
        mount(authority)
        a = self.settle(authority, 46799)
        b = self.settle(authority, 46801)
        self.assertEqual(a.solar_sample.sky_ppm, b.solar_sample.sky_ppm)
        self.assertEqual(a.regions, b.regions)
        self.assertEqual(a.materials, b.materials)
        self.assertNotEqual(a.solar_sample.direction_to_sun, b.solar_sample.direction_to_sun)
        for source in (a, b):
            sample = source.solar_sample
            self.assertEqual(source.solar_evidence, "retained")
            self.assertIs(sample, source.native_state.solar_sample)
            self.assertEqual(sample, NativeSolarSample.from_coupling(
                authority._solar_coupling, sample.second_of_day))
            region = next(r for r in source.regions if r.region_id == "W1-region-B")
            self.assertEqual(region.illumination_ppm, (sample.sky_ppm,) * 6)
            card = next(o for o in source.emitters if o.object_id == "card")
            self.assertEqual(card.emission_ppm, authority._screen_broadcasts[0].emission_at(sample.second_of_day))
            self.assertLess(len(json.dumps(sample.as_record())), 256)
        observed = authority.observation_snapshot()
        self.assertIs(observed.native.solar_sample, b.solar_sample)
        encoded = authority.encoded_snapshot()
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "invalid-clock"
        self.assertEqual(authority.solar_sun(), (*b.solar_sample.direction_to_sun, b.solar_sample.sky_ppm))
        self.assertIs(query(authority).solar_sample, b.solar_sample)
        self.assertEqual(authority.encoded_snapshot(), encoded)

    def test_prepared_discard_hidden_publication_rollback_and_failure_preserve_sample(self):
        authority = world(solar=True)
        mount(authority)
        initial = self.settle(authority, 46799)
        before = authority.encoded_snapshot()
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "0"
        pending = advance(authority)
        self.assertIs(query(authority).solar_sample, initial.solar_sample)
        self.assertIsNone(pending.execution_receipt.after.native.solar_sample.direction_to_sun)
        authority.discard_prepared_action(pending)
        self.assertEqual(authority.encoded_snapshot(), before)
        pending = advance(authority)
        with authority.prepared_action_visibility_transaction(pending):
            authority.commit_prepared_action(pending)
            with self.assertRaises(RuntimeError):
                authority.solar_sun()
            with self.assertRaises(RuntimeError):
                query(authority)
        night = query(authority)
        self.assertEqual(night.solar_evidence, "retained")
        self.assertEqual(night.solar_sample.sky_ppm, authority._solar_coupling.night_ppm)
        self.assertIsNone(night.solar_sample.direction_to_sun)
        self.assertIsNone(authority.solar_sun())
        with authority.committed_prepared_action_rollback_transaction(pending) as rollback:
            rollback()
        self.assertEqual(authority.encoded_snapshot(), before)
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "invalid-clock"
        with self.assertRaises(ValueError):
            advance(authority)
        self.assertEqual(authority.encoded_snapshot(), before)
        self.assertIs(query(authority).solar_sample, initial.solar_sample)

    def test_cold_restore_retains_light_and_continues_same_motor_under_same_external_time(self):
        for factory in (lambda: world(solar=True), coupled_world):
            with self.subTest(factory=factory):
                authority = factory()
                mount(authority)
                before = self.settle(authority, 46801, motor=True)
                encoded = authority.encoded_snapshot()
                fresh = factory()
                os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "invalid-clock"
                fresh.restore_encoded(encoded)
                self.assertEqual(fresh.encoded_snapshot(), encoded)
                self.assertEqual(fresh.observation_snapshot(), authority.observation_snapshot())
                self.assertEqual(query(fresh).solar_sample, before.solar_sample)
                self.assertEqual(fresh.solar_sun(), authority.solar_sun())
                os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "46803"
                a, b = prepare(authority, motor=True), prepare(fresh, motor=True)
                self.assertEqual(a.execution_receipt, b.execution_receipt)
                authority.commit_prepared_action(a)
                fresh.commit_prepared_action(b)
                self.assertEqual(authority.encoded_snapshot(), fresh.encoded_snapshot())
                self.assertEqual(query(fresh).solar_sample.second_of_day, 46803)
                if isinstance(fresh, ThermallyCoupledEmbodimentWorldAuthority):
                    self.assertEqual(fresh.thermal_observation(), authority.thermal_observation())

    def test_sample_codec_law_mismatch_and_observation_tamper_fail_closed(self):
        authority = world(solar=True)
        mount(authority)
        source = self.settle(authority, 46801)
        sample = source.solar_sample
        for change in ({"second_of_day": True}, {"second_of_day": 86400},
                       {"sky_ppm": -1}, {"sky_ppm": 1000001},
                       {"direction_to_sun": [float("nan"), 0, 1]},
                       {"direction_to_sun": [2, 0, 0]}, {"direction_to_sun": [0, 0, 0]},
                       {"direction_to_sun": [0, 1]}, {"extra": 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                NativeSolarSample.from_record({**sample.as_record(), **change})
        observed = authority.observation_snapshot()
        other = NativeSolarSample.from_coupling(authority._solar_coupling, 46799)
        forged = replace(observed, native=replace(observed.native, solar_sample=other))
        with self.assertRaises(ValueError):
            authority._verify_observation(forged)
        for obj, codec in ((source.native_state, NativeWorldState),
                           (observed.native, NativeWorldObservation)):
            record = obj.as_record()
            self.assertEqual(codec.from_record(record), obj)
            with self.assertRaises(ValueError):
                codec.from_record({**record, "solar_sample": None})
            with self.assertRaises(ValueError):
                codec.from_record({**record, "schema": record["schema"][:-1] + "1"})
        encoded = authority.encoded_snapshot()
        no_sun = world()
        before = no_sun.encoded_snapshot()
        with self.assertRaisesRegex(ValueError, "declared environmental law"):
            no_sun.restore_encoded(encoded)
        self.assertEqual(no_sun.encoded_snapshot(), before)
        # Explicit integrity probe: validly typed direction with wrong law output.
        bad = replace(source.native_state, solar_sample=replace(sample, direction_to_sun=(1., 1., 1.)))
        with self.assertRaisesRegex(ValueError, "declared environmental law"):
            authority._validate_native_world(replace(authority._state.world, native=bad))
        self.assertEqual(authority.encoded_snapshot(), encoded)


if __name__ == "__main__":
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SolarCustodyTests))
    print(f"solar_custody elapsed_s={time.perf_counter()-started:.6f} "
          f"peak_rss_kib={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}", flush=True)
    raise SystemExit(not result.wasSuccessful())
