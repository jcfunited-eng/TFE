"""Offline world-custody bench, not a home conversion or learned motor proof.

Uses the actual reference anatomy and existing world/thermal authority. No
pytest fixtures, processes, network transport or production body is imported.
External entities are explicitly fixed bench bodies, not simulated caretaking.
Measured internal heat is tested through existing core storage; contact heat,
ordinary learner integration, home conversion and live delivery remain open.
"""
from fractions import Fraction
import base64
import json
import math
import time
import numpy as np
import unittest
import xml.etree.ElementTree as ET

from dsf_ai_service.guala_functional_organism import FunctionalOrganism, Decision, STREAMS
from dsf_ai_service.substrate.bounded_home_thermal_physics import (
    BoundedThermalState, ThermalNodeState, ThermalPowerSource,
    advance_bounded_thermal_state,
)
from dsf_ai_service.substrate.functional_body_anatomy import append_reference_biped
from dsf_ai_service.substrate.functional_body_native import MechanicalLimits
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt, AdvancePhysicalTimeCommand, AnatomicalEffortCommand,
    EmbodiedObject, EmbodimentWorldAuthority, MoveCommand, NativeWorldMount,
    PORT_ID, ENVIRONMENT_PORT_ID, PoseMM, PositionMM, PreparedActionExecution,
    encode_command,
)
from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
    CoupledThermalAnatomy, ThermallyCoupledEmbodimentWorldAuthority,
)


KEY = b"functional-body-offline-custody-bench"
LIMITS = MechanicalLimits(1000, 250, .008, .03, .005, .015)
EFFORT = "guala/left/digit-1/distal/flexion/effort"
INTENT = "a" * 64


def declaration(*, shifted_x=0.):
    root = ET.fromstring('''<mujoco model="body-world-custody-bench">
      <compiler angle="radian" inertiafromgeom="true"/>
      <size memory="8M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 0"/>
      <default><geom friction="0.6 0.002 0.0001" solref="0.01 1"
        solimp="0.95 0.99 0.001"/></default>
      <worldbody>
        <body name="bench-other" pos="4.75 4.75 0" quat="0 0 0 1">
          <geom name="bench-other-surface" type="sphere" pos="0 0 .25" size=".25" mass="1"/>
        </body>
        <body name="bench-object" pos="1.5 1 0">
          <geom name="bench-object-surface" type="sphere" pos="0 0 .1" size=".1" mass=".5"/>
        </body>
      </worldbody><actuator/><sensor/>
    </mujoco>''')
    append_reference_biped(root.find("worldbody"), root.find("actuator"),
                           root.find("sensor"), root_position_m=(1. + shifted_x, 1., .54))
    return NativeWorldMount(
        xml=ET.tostring(root, encoding="unicode"), limits=LIMITS,
        sensory_root="guala/pelvis",
        body_frames=(("guala-body-1", "guala/pelvis"), ("w1-body-2", "bench-other")),
        object_frames=(("bench-object", "bench-object"),),
        actuator_owners=tuple(sorted((e.get("name"), "guala-body-1")
                                    for e in root.find("actuator"))),
    )


def world(*, thermal=False, measured_core=False, core_temperature=310000):
    parameters = dict(authority_key=KEY, receipt_capacity=2,
                      initial_objects=(EmbodiedObject("bench-object", 100, 500,
                                                     PositionMM(1500, 1000, 0)),))
    if not thermal:
        return EmbodimentWorldAuthority(**parameters)
    anatomy = CoupledThermalAnatomy(
        node_ids=("air:A", "air:B", "air:C", "skin", "core"),
        initial_temperatures_millikelvin=(290000, 291000, 292000, 305000, core_temperature),
        capacities_microjoules_per_millikelvin=(1000,) * 5,
        fixed_conductive_edges=(),
        room_air_node_by_region_id=(("W1-region-A", 0), ("W1-region-B", 1), ("W1-region-C", 2)),
        skin_node_index=3, core_node_index=4,
        skin_air_conductance_microwatts_per_kelvin=1,
        bath_edges=(), power_sources=(ThermalPowerSource(4, 41500000),) if measured_core else (),
        parameter_provenance=("declared-offline-thermal-bench",),
    )
    return ThermallyCoupledEmbodimentWorldAuthority(thermal_anatomy=anatomy, **parameters)


def mount(authority):
    prepared = authority.prepare_native_mount(
        declaration(), expected_revision=authority.observation_snapshot().revision,
        causal_intent_receipt_sha256=INTENT,
    )
    authority.commit_prepared_action(prepared)
    return prepared


def prepare_effort(authority, *, work=1.):
    return authority.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(AnatomicalEffortCommand(((EFFORT, .0002),), 10000)),
        causal_intent_receipt_sha256=INTENT,
        expected_revision=authority.observation_snapshot().revision,
        available_motor_work_j=work,
    )


class NativeWorldCustodyTests(unittest.TestCase):
    def test_mount_is_prepared_then_published_without_time_or_hidden_body_copy(self):
        authority = world()
        before = authority.encoded_snapshot()
        prepared = authority.prepare_native_mount(
            declaration(), expected_revision=0, causal_intent_receipt_sha256=INTENT,
        )
        self.assertIsInstance(prepared, PreparedActionExecution)
        self.assertEqual(authority.encoded_snapshot(), before)
        self.assertEqual(prepared.execution_receipt.elapsed_nanoseconds, 0)
        authority.commit_prepared_action(prepared)
        observed = authority.observation_snapshot()
        self.assertEqual(observed.revision, 1)
        self.assertIsNotNone(observed.native)
        frames = {frame.name: frame for frame in observed.native.world_frames}
        self.assertEqual(frames["guala/pelvis"].position_m, (1., 1., .54))
        integration = authority._state.world.native.integration_state
        public = json.dumps(observed.as_record(), sort_keys=True)
        self.assertNotIn(base64.b64encode(integration).decode(), public)
        self.assertFalse(hasattr(observed.native.self_feedback, "world_frames"))
        fresh = world()
        fresh.restore_encoded(authority.encoded_snapshot())
        self.assertEqual(fresh.encoded_snapshot(), authority.encoded_snapshot())
        self.assertEqual(fresh.observation_snapshot(), observed)

    def test_actual_anatomical_effort_commits_and_cold_continues(self):
        authority = world()
        mount(authority)
        before = authority.encoded_snapshot()
        prior_state = authority._state.world.native.integration_state
        prepared = prepare_effort(authority)
        self.assertIsInstance(prepared, PreparedActionExecution)
        self.assertEqual(authority.encoded_snapshot(), before)
        self.assertIsNotNone(prepared.native_work)
        self.assertEqual(prepared.execution_receipt.elapsed_nanoseconds, 10000000)
        authority.commit_prepared_action(prepared)
        after_state = authority._state.world.native.integration_state
        self.assertNotEqual(after_state, prior_state)
        self.assertEqual(len(after_state), len(prior_state))
        feedback = authority.observation_snapshot().native.self_feedback
        readings = dict(feedback.sensors)
        self.assertGreater(readings["guala/left/digit-1/distal/flexion/angle"][0], 0)
        self.assertAlmostEqual(readings["guala/left/digit-1/distal/flexion/effort-return"][0], .0002)
        fresh = world()
        fresh.restore_encoded(authority.encoded_snapshot())
        a, b = prepare_effort(authority), prepare_effort(fresh)
        self.assertEqual(a.execution_receipt, b.execution_receipt)
        self.assertEqual(a.native_work, b.native_work)
        authority.commit_prepared_action(a)
        fresh.commit_prepared_action(b)
        self.assertEqual(authority.encoded_snapshot(), fresh.encoded_snapshot())

    def test_discard_and_committed_rollback_preserve_exact_predecessor(self):
        authority = world()
        mount(authority)
        before = authority.encoded_snapshot()
        prepared = prepare_effort(authority)
        authority.discard_prepared_action(prepared)
        self.assertEqual(authority.encoded_snapshot(), before)
        prepared = prepare_effort(authority)
        with authority.prepared_action_visibility_transaction(prepared):
            authority.commit_prepared_action(prepared)
            hidden = authority.encoded_committed_prepared_action(prepared)
            with self.assertRaises(RuntimeError):
                authority.observation_snapshot()
        self.assertNotEqual(hidden, before)
        with authority.committed_prepared_action_rollback_transaction(prepared) as rollback:
            rollback()
        self.assertEqual(authority.encoded_snapshot(), before)
        fresh = world()
        fresh.restore_encoded(before)
        self.assertEqual(prepare_effort(authority).execution_receipt,
                         prepare_effort(fresh).execution_receipt)

    def test_insufficient_work_and_legacy_transport_leave_world_unchanged(self):
        authority = world()
        mount(authority)
        before = authority.encoded_snapshot()
        with self.assertRaises(ValueError):
            prepare_effort(authority, work=0.)
        self.assertEqual(authority.encoded_snapshot(), before)
        move = authority.prepare_port_command(
            port_id=PORT_ID,
            command_payload=encode_command(MoveCommand(PoseMM(PositionMM(1100, 1000, 0), 0), 10000)),
            causal_intent_receipt_sha256=INTENT,
            expected_revision=authority.observation_snapshot().revision,
            available_motor_work_j=1.,
        )
        self.assertIsInstance(move, ActionExecutionReceipt)
        self.assertNotEqual(move.disposition, "applied")
        with self.assertRaises((ValueError, RuntimeError)):
            authority.admit_authored_body_transport("guala-body-1", PoseMM(PositionMM(2000, 1000, 0), 0))
        self.assertEqual(authority.encoded_snapshot(), before)

    def test_mount_cannot_relocate_horizontal_body_placement(self):
        authority = world()
        before = authority.encoded_snapshot()
        with self.assertRaises(ValueError):
            authority.prepare_native_mount(declaration(shifted_x=.1), expected_revision=0,
                                           causal_intent_receipt_sha256=INTENT)
        self.assertEqual(authority.encoded_snapshot(), before)

    def test_unmounted_world_still_roundtrips_and_executes_its_existing_law(self):
        authority = world()
        before = authority.encoded_snapshot()
        fresh = world()
        fresh.restore_encoded(before)
        self.assertEqual(fresh.encoded_snapshot(), before)
        command = dict(port_id=PORT_ID,
                       command_payload=encode_command(MoveCommand(PoseMM(PositionMM(1100, 1000, 0), 0), 10000)),
                       causal_intent_receipt_sha256=INTENT, expected_revision=0)
        a, b = authority.prepare_port_command(**command), fresh.prepare_port_command(**command)
        self.assertIsInstance(a, PreparedActionExecution)
        self.assertEqual(a.execution_receipt, b.execution_receipt)
        authority.commit_prepared_action(a)
        fresh.commit_prepared_action(b)
        self.assertEqual(authority.encoded_snapshot(), fresh.encoded_snapshot())

    def test_failed_coupled_restore_reinstates_exact_unmounted_predecessor(self):
        mounted = world(thermal=True)
        mount(mounted)
        # Signed but internally inconsistent custody simulates a torn pair.
        # The inner native world is authentic; the thermal revision is not its
        # successor. No sensory, learning or physical outcome is manufactured.
        bad = mounted._coupled_encoded(
            EmbodimentWorldAuthority.encoded_snapshot(mounted),
            mounted._thermal_state,
            mounted._body_surface_heat_residue_nanojoules,
            mounted._thermal_world_revision + 1,
            mounted._thermal_world_observation_receipt_sha256,
            None, None,
        )
        fresh = world(thermal=True)
        before = fresh.encoded_snapshot()
        with self.assertRaisesRegex(ValueError, "thermal state does not bind"):
            fresh.restore_encoded(bad)
        self.assertEqual(fresh.encoded_snapshot(), before)
        self.assertIsNone(fresh.observation_snapshot().native)
        command = dict(
            port_id=ENVIRONMENT_PORT_ID,
            command_payload=encode_command(AdvancePhysicalTimeCommand(1000)),
            causal_intent_receipt_sha256=INTENT, expected_revision=0,
        )
        untouched = world(thermal=True)
        a = fresh.prepare_port_command(**command)
        b = untouched.prepare_port_command(**command)
        self.assertEqual(a.execution_receipt, b.execution_receipt)
        fresh.commit_prepared_action(a)
        untouched.commit_prepared_action(b)
        self.assertEqual(fresh.encoded_snapshot(), untouched.encoded_snapshot())

    def test_coupled_mount_preserves_heat_and_rollback_then_fresh_restore(self):
        authority = world(thermal=True)
        prior_interval = authority.prepare_port_command(
            port_id=ENVIRONMENT_PORT_ID,
            command_payload=encode_command(AdvancePhysicalTimeCommand(1000)),
            causal_intent_receipt_sha256=INTENT, expected_revision=0,
        )
        authority.commit_prepared_action(prior_interval)
        before = authority.encoded_snapshot()
        before_heat = authority.thermal_observation()
        self.assertIsNotNone(before_heat.latest_transition_receipt_sha256)
        prepared = mount(authority)
        after_heat = authority.thermal_observation()
        self.assertEqual(after_heat.temperatures_millikelvin, before_heat.temperatures_millikelvin)
        self.assertIsNone(after_heat.latest_transition_receipt_sha256)
        with self.assertRaises(ValueError):
            authority.thermal_endpoints_for_execution(prepared.execution_receipt)
        with authority.committed_prepared_action_rollback_transaction(prepared) as rollback:
            rollback()
        self.assertEqual(authority.encoded_snapshot(), before)
        self.assertEqual(authority.thermal_observation(), before_heat)
        mount(authority)
        fresh = world(thermal=True)
        fresh.restore_encoded(authority.encoded_snapshot())
        self.assertEqual(fresh.encoded_snapshot(), authority.encoded_snapshot())
        self.assertEqual(fresh.thermal_observation(), authority.thermal_observation())
        mounted = fresh.encoded_snapshot()
        with self.assertRaisesRegex(ValueError, "measured basal heat"):
            prepare_effort(fresh)
        self.assertEqual(fresh.encoded_snapshot(), mounted)

def prepare_heated_effort(authority, org, *, effort=.0002, duration=10000):
    # Basal debit is independent of mechanical work; prepare it from actual
    # reserve, then finalize with the world's measured work before publication.
    basal = org.prepare_body_energy(positive_motor_work_j=0., intake_micrograms=0)
    prepared = authority.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(AnatomicalEffortCommand(((EFFORT, effort),), duration)),
        causal_intent_receipt_sha256=INTENT,
        expected_revision=authority.observation_snapshot().revision,
        available_motor_work_j=org.available_motor_work_j,
        basal_heat_nanojoules=basal.basal_nanojoules,
    )
    energy = org.prepare_body_energy(
        positive_motor_work_j=prepared.native_work.positive_motor_work_j,
        intake_micrograms=0,
    )
    assert energy.basal_nanojoules == basal.basal_nanojoules
    return prepared, energy


def commit_energy(org, energy):
    decision = Decision("joint-effort", "controlled thermal bench input", (), None, None,
                        " ".join("________" for _ in STREAMS), False, 0, ())
    org.commit(decision, applied_action="joint-effort", refusal=None,
               intake_micrograms=0, spoke=None, heard_profile=None,
               self_profile=None, tick_now=org.live_organism_tick, body_energy=energy)


class NativeInternalHeatTests(unittest.TestCase):
    def test_actual_work_reserve_heat_and_cold_next_interval(self):
        authority = world(thermal=True, measured_core=True)
        mount(authority)
        org = FunctionalOrganism.genesis(identity="offline-heat-bench", organism_tick=0)
        reserve_before = org.reserve_energy_nanojoules
        heat_before = authority._thermal_state.nodes[4].energy_microjoules
        prepared, energy = prepare_heated_effort(authority, org)
        work = prepared.native_work
        self.assertGreater(work.positive_motor_work_j, 0)
        self.assertGreater(work.self_bearing_dissipation_j, 0)
        self.assertEqual(authority._thermal_state.nodes[4].energy_microjoules, heat_before)
        authority.commit_prepared_action(prepared)
        commit_energy(org, energy)
        receipt = authority._latest_thermal_transition
        loss = round((Fraction.from_float(work.self_bearing_dissipation_j)
                      + Fraction.from_float(work.motor_braking_work_j)) * 10**9)
        supplied = energy.basal_nanojoules + loss
        self.assertEqual(receipt.native_basal_heat_nanojoules, energy.basal_nanojoules)
        self.assertEqual(receipt.native_dissipation_heat_nanojoules, loss)
        self.assertEqual(receipt.powered_into_nodes_microjoules, (supplied // 1000,))
        self.assertEqual(authority._thermal_state.nodes[4].energy_microjoules - heat_before,
                         supplied // 1000)
        self.assertEqual(authority._thermal_state.power_residue_numerators,
                         ((supplied % 1000) * 1000,))
        self.assertEqual(org.reserve_energy_nanojoules,
                         reserve_before - energy.basal_nanojoules - energy.work_nanojoules)
        # Neither fixed 41.5W nor positive motor work is extra deposited heat.
        self.assertNotEqual(receipt.powered_into_nodes_microjoules, (415000,))
        self.assertNotEqual(loss, energy.work_nanojoules)
        restored = world(thermal=True, measured_core=True)
        restored.restore_encoded(authority.encoded_snapshot())
        other = FunctionalOrganism.restore(org.encoded())
        self.assertEqual(restored.encoded_snapshot(), authority.encoded_snapshot())
        self.assertEqual(other.encoded(), org.encoded())
        a, ea = prepare_heated_effort(authority, org, effort=-.0002, duration=1000)
        b, eb = prepare_heated_effort(restored, other, effort=-.0002, duration=1000)
        self.assertGreater(a.native_work.motor_braking_work_j, 0)
        self.assertEqual(a.execution_receipt, b.execution_receipt)
        self.assertEqual(ea, eb)
        self.assertEqual(authority._pending_thermal.receipt, restored._pending_thermal.receipt)
        for auth, body, command, debit in ((authority, org, a, ea), (restored, other, b, eb)):
            auth.commit_prepared_action(command)
            commit_energy(body, debit)
        self.assertEqual(authority.encoded_snapshot(), restored.encoded_snapshot())
        self.assertEqual(org.encoded(), other.encoded())

    def test_heat_discard_and_committed_rollback_preserve_cold_successor(self):
        authority = world(thermal=True, measured_core=True)
        mount(authority)
        org = FunctionalOrganism.genesis(identity="offline-heat-bench", organism_tick=0)
        before = authority.encoded_snapshot()
        prepared, _ = prepare_heated_effort(authority, org)
        authority.discard_prepared_action(prepared)
        self.assertEqual(authority.encoded_snapshot(), before)
        prepared, _ = prepare_heated_effort(authority, org)
        with authority.prepared_action_visibility_transaction(prepared):
            authority.commit_prepared_action(prepared)
            candidate = authority.encoded_committed_prepared_action(prepared)
        self.assertNotEqual(candidate, before)
        with authority.committed_prepared_action_rollback_transaction(prepared) as rollback:
            rollback()
        self.assertEqual(authority.encoded_snapshot(), before)
        fresh = world(thermal=True, measured_core=True)
        fresh.restore_encoded(before)
        a, _ = prepare_heated_effort(authority, org)
        b, _ = prepare_heated_effort(fresh, org)
        self.assertEqual(a.execution_receipt, b.execution_receipt)
        self.assertEqual(authority._pending_thermal.receipt, fresh._pending_thermal.receipt)
        authority.discard_prepared_action(a)
        fresh.discard_prepared_action(b)

    def test_missing_supply_bad_anatomy_and_overflow_do_not_publish(self):
        org = FunctionalOrganism.genesis(identity="offline-heat-bench", organism_tick=0)
        for supplied, temperature, reason in (
            (False, 310000, "one declared core source"),
            (True, 1000000, "temperature exceeds"),
        ):
            authority = world(thermal=True, measured_core=supplied,
                              core_temperature=temperature)
            mount(authority)
            before = authority.encoded_snapshot()
            with self.assertRaisesRegex(ValueError, "measured basal heat"):
                prepare_effort(authority)
            self.assertEqual(authority.encoded_snapshot(), before)
            with self.assertRaisesRegex(ValueError, reason):
                prepare_heated_effort(authority, org)
            self.assertEqual(authority.encoded_snapshot(), before)
            self.assertIsNone(authority._pending_thermal)
        unmounted = world(thermal=True, measured_core=True)
        before = unmounted.encoded_snapshot()
        with self.assertRaisesRegex(ValueError, "unmounted body"):
            prepare_heated_effort(unmounted, org)
        self.assertEqual(unmounted.encoded_snapshot(), before)

    def test_subquantum_source_energy_retains_exact_residue_and_default_law(self):
        state = BoundedThermalState((ThermalNodeState(300000000, 1000),), (), (), (0,))
        source = (ThermalPowerSource(0, 1000000),)
        kwargs = dict(conductive_edges=(), bath_edges=(), power_sources=source,
                      duration_microseconds=1000)
        ordinary = advance_bounded_thermal_state(state, **kwargs)
        explicit = advance_bounded_thermal_state(state, **kwargs, source_energy_nanojoules=(None,))
        self.assertEqual(ordinary, explicit)
        self.assertEqual(ordinary.powered_into_nodes_microjoules, (1000,))
        start = state.nodes[0].energy_microjoules
        for _ in range(4):
            state = advance_bounded_thermal_state(
                state, **kwargs, source_energy_nanojoules=(301,)).successor
        self.assertEqual(state.nodes[0].energy_microjoules - start, 1)
        self.assertEqual(state.power_residue_numerators, (204000,))
        for invalid in ((True,), (-1,), (1.5,), (), [0], (10**100,)):
            with self.assertRaises(ValueError):
                advance_bounded_thermal_state(state, **kwargs, source_energy_nanojoules=invalid)




class NativeOpticalGeometryTests(unittest.TestCase):
    # A declared test optical point 1 cm in front of this bench's spherical
    # head. NOT a mounted production eye, biological receptor or radiance law.
    ORIGIN = (.08, 0., .03)

    def query(self, authority, directions, **overrides):
        parameters = dict(
            expected_revision=authority.observation_snapshot().revision,
            frame_name="guala/head", origin_local_m=self.ORIGIN,
            directions_local=np.asarray(directions, dtype=np.float64),
            max_rays=19335,  # existing 160x120 focal + 135 surround sites
        )
        parameters.update(overrides)
        return authority.native_ray_geometry(**parameters)

    def test_native_occlusion_self_visibility_and_misses(self):
        authority = world()
        mount(authority)
        before = authority.encoded_snapshot()
        origin = np.array((1.08, 1., .96))
        target = np.array((1.5, 1., .1))
        result = self.query(authority, ((1., 0., 0.), (-1., 0., 0.),
                                        tuple(target - origin)))
        engine = authority._native_scratch
        self.assertEqual(result.geom_indices[0], -1)
        self.assertEqual(result.distances_m[0], -1)
        # Looking back hits actual own head: no invisible-self exclusion.
        self.assertEqual(engine.geom_names[result.geom_indices[1]], "guala/head/surface")
        self.assertAlmostEqual(result.distances_m[1], .01, places=12)
        self.assertEqual(engine.geom_names[result.geom_indices[2]], "bench-object-surface")
        self.assertAlmostEqual(result.distances_m[2], np.linalg.norm(target - origin) - .1,
                               places=12)
        np.testing.assert_allclose(result.origin_world_m, origin, atol=1e-15, rtol=0)
        self.assertEqual(authority.encoded_snapshot(), before)
        self.assertFalse(result.distances_m.flags.writeable)
        self.assertFalse(result.directions_world.flags.writeable)
        held = result.distances_m.copy()
        self.query(authority, ((0., 0., 1.),))
        np.testing.assert_array_equal(result.distances_m, held)

    def test_real_head_effort_full_frame_restore_and_next_successor(self):
        authority = world()
        mount(authority)
        directions = np.array(((1., .2, .3), (1., -.2, -.3), (1., 0., 0.)))
        initial = self.query(authority, directions)
        command = AnatomicalEffortCommand((
            ("guala/head/pitch/effort", .015),
            ("guala/head/roll/effort", .02),
            ("guala/head/yaw/effort", -.01),
        ), 50000)
        prepared = authority.prepare_port_command(
            port_id=PORT_ID, command_payload=encode_command(command),
            causal_intent_receipt_sha256=INTENT,
            expected_revision=authority.observation_snapshot().revision,
            available_motor_work_j=1.,
        )
        authority.commit_prepared_action(prepared)
        encoded = authority.encoded_snapshot()
        observed = authority.observation_snapshot()
        frame = next(f for f in observed.native.world_frames if f.name == "guala/head")
        rotation = np.array(frame.rotation_world).reshape(3, 3)
        result = self.query(authority, directions)
        np.testing.assert_allclose(result.origin_world_m,
                                   np.array(frame.position_m) + rotation @ self.ORIGIN,
                                   atol=1e-15, rtol=0)
        expected = (directions / np.linalg.norm(directions, axis=1)[:, None]) @ rotation.T
        np.testing.assert_allclose(result.directions_world, expected, atol=1e-15, rtol=0)
        self.assertGreater(np.max(np.abs(result.directions_world - initial.directions_world)), 1e-6)
        self.assertGreater(abs(rotation[2, 1]), 1e-6)  # real roll, not yaw-only
        self.assertEqual(authority.encoded_snapshot(), encoded)
        restored = world()
        restored.restore_encoded(encoded)
        cold = self.query(restored, directions)
        self.assertEqual(cold.origin_world_m, result.origin_world_m)
        np.testing.assert_array_equal(cold.directions_world, result.directions_world)
        np.testing.assert_array_equal(cold.geom_indices, result.geom_indices)
        np.testing.assert_array_equal(cold.distances_m, result.distances_m)
        # Additional observations cannot change a subsequent actual interval.
        self.query(authority, ((-1., 0., 0.),))
        for item in (authority, restored):
            item.commit_prepared_action(prepare_effort(item))
        self.assertEqual(authority.encoded_snapshot(), restored.encoded_snapshot())

    def test_failures_preserve_world_and_normalization_handles_extremes(self):
        authority = world()
        before = authority.encoded_snapshot()
        with self.assertRaisesRegex(ValueError, "not mounted"):
            self.query(authority, ((1., 0., 0.),))
        self.assertEqual(authority.encoded_snapshot(), before)
        mount(authority)
        before = authority.encoded_snapshot()
        cases = (
            {"expected_revision": 0},
            {"frame_name": "bench-other"},
            {"frame_name": "missing"},
            {"origin_local_m": (math.inf, 0., 0.)},
            {"origin_local_m": (1e11, 0., 0.)},
            {"directions_local": np.zeros((1, 3))},
            {"directions_local": np.full((1, 3), math.nan)},
            {"directions_local": np.ones((2, 3)), "max_rays": 1},
            {"directions_local": np.ones((1, 2))},
            {"directions_local": np.ones((1, 3), dtype=np.float32)},
            {"max_rays": True},
        )
        for override in cases:
            with self.subTest(override=tuple(override)):
                with self.assertRaises(ValueError):
                    self.query(authority, ((1., 0., 0.),), **override)
                self.assertEqual(authority.encoded_snapshot(), before)
        result = self.query(authority, ((1e308, 0., 0.), (5e-324, 0., 0.)))
        np.testing.assert_array_equal(result.directions_world, ((1., 0., 0.), (1., 0., 0.)))
        self.assertEqual(authority.encoded_snapshot(), before)

    def test_hidden_committed_geometry_is_not_observable(self):
        authority = world()
        mount(authority)
        before = authority.encoded_snapshot()
        prepared = prepare_effort(authority)
        with authority.prepared_action_visibility_transaction(prepared):
            authority.commit_prepared_action(prepared)
            with self.assertRaisesRegex(RuntimeError, "visibility transaction"):
                # Use the actual candidate revision: this must refuse on
                # publication, not pass merely because revision matches.
                authority.native_ray_geometry(
                    expected_revision=prepared.execution_receipt.after.revision,
                    frame_name="guala/head", origin_local_m=self.ORIGIN,
                    directions_local=np.array(((1., 0., 0.),)), max_rays=1,
                )
        with authority.committed_prepared_action_rollback_transaction(prepared) as rollback:
            rollback()
        self.assertEqual(authority.encoded_snapshot(), before)
        self.query(authority, ((1., 0., 0.),))

    def test_full_existing_ray_count_is_batched_current_only(self):
        authority = world()
        mount(authority)
        before = authority.encoded_snapshot()
        # Deterministic grid sampling an empty forward hemisphere; this is a
        # geometric throughput test, not a retina/radiance equivalence claim.
        rays = np.ones((19335, 3), dtype=np.float64)
        rays[:, 1] = np.linspace(-.5, .5, len(rays))
        rays[:, 2] = .2
        times = []
        for _ in range(3):
            started = time.perf_counter()
            result = self.query(authority, rays)
            times.append(time.perf_counter() - started)
            self.assertEqual(len(result.geom_indices), len(rays))
            self.assertEqual(authority.encoded_snapshot(), before)
        size = sum(a.nbytes for a in (result.directions_world, result.geom_indices,
                                     result.distances_m))
        self.assertEqual(size, 19335 * (3 * 8 + 4 + 8))
        print(f"native_optical_batch rays={len(rays)} output_bytes={size} "
              f"query_seconds={times}", flush=True)


if __name__ == "__main__":
    unittest.main()
