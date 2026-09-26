"""Offline nutrient custody across physical contact and the existing body mount.

These are externally driven mechanical trials, not autonomous feeding or a
biological digestion model. No pytest fixtures, production state, reserve edits,
memory edits, new native anatomy, or network calls are used. Legacy contact is
exercised before mounting; the native body does not yet support oral commands.
The legacy mouth radius is the home's declared 60 mm, not the generic world's
250 mm receptor that would consume this 100 mm specimen in a single contact.
"""
from dataclasses import replace
import unittest

from dsf_ai_service.guala_functional_loop import _oral_intake_micrograms
from dsf_ai_service.substrate.embodiment_world import (
    BodyContactState, EmbodiedObject, EmbodimentWorldAuthority,
    MAX_MATERIAL_MASS, ObjectMaterialState, OralContactCommand, PickCommand,
    PlaceCommand, PORT_ID, PositionMM, PreparedActionExecution,
    _contact_from, _material_from, encode_command,
)
from test_functional_body_world import (
    KEY, INTENT, mount, prepare_effort, world as bench_world,
)


OBJECT = "bench-object"
POSITION = PositionMM(1500, 1000, 0)
DURATION_US = 10_000


def material(nutrients, *, tastes=(1000, 2000, 3000, 4000, 5000)):
    return ObjectMaterialState(
        odorant_reservoir_nanograms=(0,) * 8,
        odorant_release_nanograms_per_second=(0,) * 8,
        tastant_mass_micrograms=tastes,
        surface_temperature_millikelvin=294000,
        compliance_ppm=100000,
        roughness_micrometers=10,
        moisture_ppm=10000,
        digestible_mass_micrograms=nutrients,
    )


def authority(nutrients, *, tastes=(1000, 2000, 3000, 4000, 5000)):
    declared = bench_world().observation_snapshot()
    bodies = tuple(
        replace(body, receptor_geometry=replace(body.receptor_geometry, oral_radius_mm=60))
        if body.body_id == declared.self_body_id else body
        for body in declared.bodies
    )
    return EmbodimentWorldAuthority(
        authority_key=KEY, receipt_capacity=2, bodies=bodies,
        initial_objects=(EmbodiedObject(
            OBJECT, 100, 500, POSITION, material=material(nutrients, tastes=tastes),
        ),),
    )


def item(world):
    return next(o for o in world.observation_snapshot().objects if o.object_id == OBJECT)


def prepare(world, command):
    return world.prepare_port_command(
        port_id=PORT_ID, command_payload=encode_command(command),
        causal_intent_receipt_sha256=INTENT,
        expected_revision=world.observation_snapshot().revision,
    )


class NutritionCustodyTests(unittest.TestCase):
    def applied(self, world, command):
        before = world.encoded_snapshot()
        candidate = prepare(world, command)
        self.assertIsInstance(candidate, PreparedActionExecution)
        self.assertEqual(candidate.execution_receipt.disposition, "applied")
        self.assertEqual(world.encoded_snapshot(), before)
        return world.commit_prepared_action(candidate)

    def test_canonical_zero_positive_and_malformed_material_and_receipts(self):
        zero = material(0)
        old = zero.as_record()
        self.assertNotIn("digestible_mass_micrograms", old)
        self.assertEqual(_material_from(old), zero)
        self.assertEqual(_material_from(old).as_record(), old)
        contact = BodyContactState("oral", OBJECT, 100, DURATION_US)
        old_contact = contact.as_record()
        self.assertEqual(old_contact, {
            "kind": "oral", "object_id": OBJECT,
            "contact_patch_square_mm": 100, "duration_microseconds": DURATION_US,
        })
        self.assertEqual(_contact_from(old_contact), contact)
        for amount in (1, MAX_MATERIAL_MASS):
            enriched = replace(zero, digestible_mass_micrograms=amount)
            mouthful = replace(contact, transferred_digestible_micrograms=amount)
            self.assertEqual(_material_from(enriched.as_record()), enriched)
            self.assertEqual(_contact_from(mouthful.as_record()), mouthful)
        for invalid in (-1, True, False, 1.0, None, "1", MAX_MATERIAL_MASS + 1):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    replace(zero, digestible_mass_micrograms=invalid).as_record()
                with self.assertRaises(ValueError):
                    replace(contact, transferred_digestible_micrograms=invalid).as_record()
                with self.assertRaises(ValueError):
                    _material_from(dict(old, digestible_mass_micrograms=invalid))
                with self.assertRaises(ValueError):
                    _contact_from(dict(old_contact, transferred_digestible_micrograms=invalid))
        with self.assertRaises(ValueError):
            _material_from(dict(old, digestible_mass_micrograms=0))
        with self.assertRaises(ValueError):
            _contact_from(dict(old_contact, transferred_digestible_micrograms=0))
        with self.assertRaises(ValueError):
            replace(contact, kind="touch", transferred_digestible_micrograms=1).as_record()
        with self.assertRaises(ValueError):
            _contact_from(dict(old_contact, kind="touch", transferred_digestible_micrograms=1))

    def test_actual_bite_debits_only_declared_nutrients_and_cold_continues(self):
        for nutrients, tastes in ((0, (1000,) * 5), (12000, (1000,) * 5),
                                  (12000, (0,) * 5)):
            with self.subTest(nutrients=nutrients, tastes=tastes):
                world = authority(nutrients, tastes=tastes)
                self.applied(world, PickCommand(OBJECT, DURATION_US))
                before = item(world).material
                receipt = self.applied(world, OralContactCommand(OBJECT, DURATION_US))
                mouth = next(b.active_contact for b in receipt.after.bodies
                             if b.body_id == receipt.after.self_body_id)
                expected = min(nutrients, nutrients * mouth.contact_patch_square_mm // 100**2)
                self.assertEqual(mouth.transferred_digestible_micrograms, expected)
                self.assertEqual(_oral_intake_micrograms(receipt), expected)
                self.assertEqual(item(world).material.digestible_mass_micrograms,
                                 nutrients - expected)
                self.assertEqual(bool(expected), bool(nutrients))
                taste_debits = tuple(a - b for a, b in zip(
                    before.tastant_mass_micrograms, item(world).material.tastant_mass_micrograms))
                self.assertEqual(mouth.dissolved_tastant_micrograms,
                                 taste_debits if any(taste_debits) else ())
                self.assertEqual(bool(any(taste_debits)), bool(any(tastes)))
                saved = world.encoded_snapshot()
                fresh = authority(nutrients, tastes=tastes)
                fresh.restore_encoded(saved)
                self.assertFalse(fresh.migrate_declared_material_transport())
                self.assertEqual(fresh.encoded_snapshot(), saved)
                self.assertEqual(fresh.observation_snapshot(), world.observation_snapshot())
                a = self.applied(world, OralContactCommand(OBJECT, DURATION_US))
                b = self.applied(fresh, OralContactCommand(OBJECT, DURATION_US))
                self.assertEqual(a, b)
                self.assertEqual(world.encoded_snapshot(), fresh.encoded_snapshot())
                self.assertEqual(nutrients, expected + _oral_intake_micrograms(a)
                                 + item(world).material.digestible_mass_micrograms)

    def test_native_mount_interval_and_restart_preserve_bitten_material(self):
        world = authority(12000)
        self.applied(world, PickCommand(OBJECT, DURATION_US))
        self.applied(world, OralContactCommand(OBJECT, DURATION_US))
        remaining = item(world).material
        self.assertGreater(remaining.digestible_mass_micrograms, 0)
        self.assertLess(remaining.digestible_mass_micrograms, 12000)
        self.applied(world, PlaceCommand(OBJECT, POSITION, DURATION_US))
        self.assertEqual(item(world).material, remaining)
        mount_receipt = mount(world).execution_receipt
        self.assertEqual(mount_receipt.elapsed_nanoseconds, 0)
        self.assertEqual(item(world).material, remaining)
        prepared = prepare_effort(world)
        self.assertIsInstance(prepared, PreparedActionExecution)
        self.assertEqual(_oral_intake_micrograms(prepared.execution_receipt), 0)
        world.commit_prepared_action(prepared)
        self.assertEqual(item(world).material, remaining)
        saved = world.encoded_snapshot()
        fresh = authority(12000)
        fresh.restore_encoded(saved)
        with self.assertRaisesRegex(ValueError, "mounted native topology"):
            fresh.migrate_declared_material_transport()
        self.assertEqual(fresh.encoded_snapshot(), saved)
        self.assertEqual(fresh.observation_snapshot(), world.observation_snapshot())
        a, b = prepare_effort(world), prepare_effort(fresh)
        self.assertEqual(a.execution_receipt, b.execution_receipt)
        self.assertEqual(a.native_work, b.native_work)
        world.commit_prepared_action(a)
        fresh.commit_prepared_action(b)
        self.assertEqual(world.encoded_snapshot(), fresh.encoded_snapshot())
        self.assertEqual(item(world).material, remaining)

    def test_prepared_bite_discard_and_rollback_cannot_consume_material(self):
        world = authority(12000)
        self.applied(world, PickCommand(OBJECT, DURATION_US))
        before = world.encoded_snapshot()
        candidate = prepare(world, OralContactCommand(OBJECT, DURATION_US))
        self.assertIsInstance(candidate, PreparedActionExecution)
        world.discard_prepared_action(candidate)
        self.assertEqual(world.encoded_snapshot(), before)
        candidate = prepare(world, OralContactCommand(OBJECT, DURATION_US))
        with world.prepared_action_visibility_transaction(candidate):
            world.commit_prepared_action(candidate)
            hidden = world.encoded_committed_prepared_action(candidate)
        self.assertNotEqual(hidden, before)
        with world.committed_prepared_action_rollback_transaction(candidate) as rollback:
            rollback()
        self.assertEqual(world.encoded_snapshot(), before)
        self.assertEqual(item(world).material.digestible_mass_micrograms, 12000)


if __name__ == "__main__":
    unittest.main()
