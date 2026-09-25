"""Offline world-custody bench, not a home conversion or learned motor proof.

Uses the actual reference anatomy and existing world/thermal authority. No
pytest fixtures, processes, network transport or production body is imported.
External entities are explicitly fixed bench bodies, not simulated caretaking.
Timed thermal dissipation remains unavailable in this mount candidate.
"""
import base64
import json
import unittest
import xml.etree.ElementTree as ET

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


def world(*, thermal=False):
    parameters = dict(authority_key=KEY, receipt_capacity=2,
                      initial_objects=(EmbodiedObject("bench-object", 100, 500,
                                                     PositionMM(1500, 1000, 0)),))
    if not thermal:
        return EmbodimentWorldAuthority(**parameters)
    anatomy = CoupledThermalAnatomy(
        node_ids=("air:A", "air:B", "air:C", "skin", "core"),
        initial_temperatures_millikelvin=(290000, 291000, 292000, 305000, 310000),
        capacities_microjoules_per_millikelvin=(1000,) * 5,
        fixed_conductive_edges=(),
        room_air_node_by_region_id=(("W1-region-A", 0), ("W1-region-B", 1), ("W1-region-C", 2)),
        skin_node_index=3, core_node_index=4,
        skin_air_conductance_microwatts_per_kelvin=1,
        bath_edges=(), power_sources=(),
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
        with self.assertRaisesRegex(RuntimeError, "native thermal dissipation"):
            prepare_effort(fresh)
        self.assertEqual(fresh.encoded_snapshot(), mounted)


if __name__ == "__main__":
    unittest.main()
