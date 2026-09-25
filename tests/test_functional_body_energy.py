"""Standalone reserve/motor integration checks; no live world or pytest fixtures.

External bench efforts are controlled test inputs, not autonomous behavior.
These prove native work -> existing organism reserve/record -> cold restore,
not whole-world transaction mounting, learning, gait or production delivery.
"""
from dataclasses import replace
from fractions import Fraction
import math
import unittest

from dsf_ai_service.guala_functional_organism import (
    BASAL_BURN_MICROGRAMS, CAPACITY_MICROGRAMS, STREAMS,
    BodyEnergyTransition, Decision, FunctionalOrganism,
    RESERVE_NANOJOULES_PER_MICROGRAM as UNIT,
)
from dsf_ai_service.substrate.functional_body_native import MechanicalLimits, NativeBody


def bench():
    return NativeBody('''<mujoco><size memory="2M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 0"/>
      <worldbody><body><joint name="joint" type="hinge" damping="0.02"/>
        <geom type="sphere" size=".1" mass="1"/>
      </body></worldbody>
      <actuator><motor joint="joint" forcelimited="true" forcerange="-1 1"/></actuator>
    </mujoco>''', MechanicalLimits(1000, 250, .008, .03, .005, .01))


def organism():
    return FunctionalOrganism.genesis(identity="offline-body-energy-bench", organism_tick=0)


def commit(org, energy=None, *, act="joint-effort", applied=None, intake=0):
    decision = Decision(act, "controlled mechanical bench input", (), None, None,
                        " ".join("________" for _ in STREAMS), False, 0, ())
    org.commit(decision, applied_action=act if applied is None else applied,
               refusal="bench refusal" if applied == "refused" else None,
               intake_micrograms=intake, spoke=None, heard_profile=None,
               self_profile=None, tick_now=org.live_organism_tick, body_energy=energy)


class BodyEnergyTests(unittest.TestCase):
    def test_real_motor_work_debits_existing_reserve_without_charging_heat_twice(self):
        org, native = organism(), bench()
        before = org.reserve_energy_nanojoules
        result = native.advance(native.initial_state(), (.3,), 100000,
                                org.available_motor_work_j)
        self.assertGreater(result.bearing_dissipation_j, 0)
        energy = org.prepare_body_energy(positive_motor_work_j=result.positive_motor_work_j,
                                         intake_micrograms=0)
        exact_work_nj = Fraction.from_float(result.positive_motor_work_j) * 10**9
        self.assertGreaterEqual(energy.work_nanojoules, exact_work_nj)
        self.assertLess(energy.work_nanojoules - exact_work_nj, 1)
        # Same cost/capacity law receives actual work, not a name multiplier.
        org._state["pending_act"] = {"burn": 0}
        commit(org, energy, act="step")
        self.assertEqual(org.reserve_energy_nanojoules,
                         before - energy.work_nanojoules - BASAL_BURN_MICROGRAMS * UNIT)
        self.assertEqual(org._state["pending_act"]["burn_nanojoules"],
                         energy.basal_nanojoules + energy.work_nanojoules)
        self.assertNotIn("burn", org._state["pending_act"])
        self.assertLess(org._state["reserve_spent_nanojoules"], UNIT)

    def test_fractional_debits_survive_cold_restore_and_next_physical_interval(self):
        org, native = organism(), bench()
        result = native.advance(native.initial_state(), (.3,), 1000, org.available_motor_work_j)
        commit(org, org.prepare_body_energy(positive_motor_work_j=result.positive_motor_work_j,
                                           intake_micrograms=0))
        self.assertGreater(org._state["reserve_spent_nanojoules"], 0)
        encoded = org.encoded()
        restored = FunctionalOrganism.restore(encoded)
        self.assertEqual(restored.encoded(), encoded)
        a = native.advance(result.state, None, 1000, org.available_motor_work_j)
        b = bench().advance(result.state, None, 1000, restored.available_motor_work_j)
        self.assertEqual(a, b)
        for instance, successor in ((org, a), (restored, b)):
            commit(instance, instance.prepare_body_energy(
                positive_motor_work_j=successor.positive_motor_work_j, intake_micrograms=0))
        self.assertEqual(org.encoded(), restored.encoded())

    def test_negative_motor_work_is_not_food_or_extra_heat_charge(self):
        org, native = organism(), bench()
        driven = native.advance(native.initial_state(), (.3,), 100000, org.available_motor_work_j)
        commit(org, org.prepare_body_energy(positive_motor_work_j=driven.positive_motor_work_j,
                                           intake_micrograms=0))
        before = org.reserve_energy_nanojoules
        braking = native.advance(driven.state, (-.3,), 1000, org.available_motor_work_j)
        self.assertGreater(braking.motor_braking_work_j, 0)
        self.assertEqual(braking.positive_motor_work_j, 0)
        commit(org, org.prepare_body_energy(positive_motor_work_j=braking.positive_motor_work_j,
                                           intake_micrograms=0))
        self.assertEqual(org.reserve_energy_nanojoules, before - BASAL_BURN_MICROGRAMS * UNIT)

    def test_overspend_and_bad_receipts_refuse_before_any_organism_mutation(self):
        org = organism()
        before = org.encoded()
        for work in (math.nan, math.inf, -.01, org.available_motor_work_j + 1):
            with self.assertRaises(ValueError):
                org.prepare_body_energy(positive_motor_work_j=work, intake_micrograms=0)
            self.assertEqual(org.encoded(), before)
        valid = org.prepare_body_energy(positive_motor_work_j=.001, intake_micrograms=0)
        with self.assertRaises(ValueError):
            replace(valid, after_nanojoules=valid.after_nanojoules + 1)
        with self.assertRaises(RuntimeError):
            commit(org, replace(valid, tick=1))
        self.assertEqual(org.encoded(), before)
        with self.assertRaises(ValueError):
            commit(org, valid, applied="refused")
        self.assertEqual(org.encoded(), before)
        commit(org, valid)
        after = org.encoded()
        with self.assertRaises(RuntimeError):
            commit(org)  # No fallback to legacy fixed-effort costs after mounting.
        self.assertEqual(org.encoded(), after)

    def test_emptying_fractional_reserve_is_exact_and_food_cannot_prefund_motion(self):
        org = organism()
        org._state["reserve_micrograms"] = 2
        org._state["reserve_spent_nanojoules"] = 100
        self.assertEqual(org.available_motor_work_j, 0)
        with self.assertRaises(ValueError):
            org.prepare_body_energy(positive_motor_work_j=.001, intake_micrograms=100)
        energy = org.prepare_body_energy(positive_motor_work_j=0, intake_micrograms=0)
        self.assertEqual(energy.basal_nanojoules, 2 * UNIT - 100)
        commit(org, energy, act="rest")
        self.assertEqual(org.reserve_micrograms, 0)
        self.assertEqual(org.reserve_energy_nanojoules, 0)
        self.assertEqual(org._state["reserve_spent_nanojoules"], 0)
        fed = org.prepare_body_energy(positive_motor_work_j=0, intake_micrograms=100)
        commit(org, fed, act="rest", intake=100)
        self.assertEqual(org.reserve_energy_nanojoules, 100 * UNIT)

    def test_legacy_encoding_cost_and_memory_are_not_migrated_to_joint_experience(self):
        org = organism()
        encoded = org.encoded()
        self.assertEqual(FunctionalOrganism.restore(encoded).encoded(), encoded)
        self.assertNotIn("reserve_spent_nanojoules", org._state)
        before = org.reserve_micrograms
        commit(org, act="step")
        self.assertEqual(org.reserve_micrograms, before - 5 * BASAL_BURN_MICROGRAMS)
        self.assertNotIn("reserve_spent_nanojoules", org._state)
        self.assertEqual(org._state["meanings"], {})

    def test_supply_rounds_conservatively_and_corrupt_fractional_custody_fails(self):
        org = organism()
        org._state["reserve_spent_nanojoules"] = 1
        exact = Fraction(org.reserve_energy_nanojoules - BASAL_BURN_MICROGRAMS * UNIT, 10**9)
        self.assertLessEqual(Fraction.from_float(org.available_motor_work_j), exact)
        self.assertLess(exact - Fraction.from_float(org.available_motor_work_j),
                        Fraction.from_float(math.ulp(org.available_motor_work_j)))
        self.assertEqual(org.deficit, Fraction(CAPACITY_MICROGRAMS * UNIT - org.reserve_energy_nanojoules,
                                               CAPACITY_MICROGRAMS * UNIT))
        for residue in (-1, UNIT, True, .5):
            org._state["reserve_spent_nanojoules"] = residue
            with self.assertRaises(ValueError):
                FunctionalOrganism.restore(org.encoded())


    def test_invalid_retained_cost_cannot_debit_before_failure(self):
        for bad in ("bad", -1, True, .5):
            org = organism()
            org._state["pending_act"] = {"burn_nanojoules": bad}
            before = org.encoded()
            with self.assertRaises(ValueError):
                FunctionalOrganism.restore(before)
            prepared = org.prepare_body_energy(positive_motor_work_j=.001, intake_micrograms=0)
            with self.assertRaises(ValueError):
                commit(org, prepared)
            self.assertEqual(org.encoded(), before)
        org = organism()
        org._state["pending_act"] = {"burn": "bad"}
        before = org.encoded()
        prepared = org.prepare_body_energy(positive_motor_work_j=.001, intake_micrograms=0)
        with self.assertRaises(ValueError):
            commit(org, prepared)
        self.assertEqual(org.encoded(), before)


if __name__ == "__main__":
    unittest.main()
