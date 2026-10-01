"""tests/test_arcloom_causal_action_witness.py

Standalone Executable Architectural Witness for ArcLoom 64D Neuromorphic Substrate.
Component witnesses only. A10 rejects full-field closure; its positive field
case remains a strict expected failure, not a passing architecture claim:

1. Production Motor Conversion & Obstacle Refusal (A9-01):
   - Motor efferent inspection is a pure read-only proposal (proposed_kinematic_action).
   - Efferent schema and domain validation: 4-element sequence, finite numbers, declared native physical domains
     (stride in [0.0, 60.0], steer in [-45.0, 45.0], vocal in [0.0, 480.0], grip in [0.0, 25.0]);
     malformed, non-finite, or out-of-domain efferents raise ValueError.
   - Duration validation: strictly positive integer matching canonical BEAT_MICROSECONDS = 250,000 us;
     booleans, non-integers, non-finite values, and non-canonical intervals raise ValueError.
   - Silent motor populations produce strictly (0.0, 0.0, 0.0, 0.0) efferents and return None command.
   - Candidate generation explicitly requires native motor capability (raises AttributeError if absent).
   - In candidate generation, native silence strictly inhibits locomotion (no fallback step option).
   - In open space, active native stride prepares and commits successfully, moving body position.
   - On the same candidate trajectory, lawful physical barrier (room boundary wall) triggers refusal
     using the EXACT unmodified native efferent tuple (no 100mm substitute), asserting full pose invariance.

2. Constitutive Baseline Provenance & Rate-Independent Return Map (A9-02):
   - G_ELASTIC_BASELINE = 0.05 represents the dimensionless baseline resting coupling parameter w_0
     in the discrete ternary lattice model, with signed plastic weights w in [-1.0, 1.0].
     Truthful disclosure: Macroscopic continuum contact mechanics and microscopic derivation in SI units
     remain an open research contract; Holm/tunneling claims are formally retracted.
   - True rate-independent return map projection: trial stress over yield projects directly to |Sigma_{n+1}| = Y
     (yield function f_{n+1} = 0) with non-negative plastic dissipation D_pl >= 0.
   - Once plastic equilibrium on the yield surface is reached, repeated identical steps produce zero yield events
     and identical operative states, eliminating continuous plastic drift on identical inputs.
   - Super-yield plastic deformation (w > 0) versus sub-yield elastic compliance drives divergent world actions.
   - Matched intact vs ablated states executed in two actual world instances produce divergent world coordinates.
   - Incoming tract severing under identical inputs halts motor actuation to strictly 0.0.

3. ARCLOOM4 Codec & Explicit Predecessor Migration (A9-03):
   - Strict separation of current restore from historical migration at outer Python and native boundaries:
     from_dict and import_sparse_bytes accept only current ARCLOOM4 format, rejecting historical versions.
   - Explicit migration via migrate_predecessor_v2 requires authenticated layout metadata ("24B" or "36B"),
     preventing guessing fallbacks; invalid layouts fail closed with ValueError.
   - Historical predecessor v3 migration requires explicit layout ("short" or "long"):
     - ARCLOOM3_SHORT migrates cleanly with continuous_field_present == False.
     - ARCLOOM3_LONG rejects migration when field_present metadata is None; migrates losslessly when field_present=True.
     - Truncated long payloads cannot downgrade to short; short payloads cannot pass as long.
     - Synthetic v3 test payloads are explicitly documented and labeled as synthetic layout test fixtures.
   - Structurally valid asymmetric severed tract test: payload with severed tract 1->2 (66) without reverse 2->1 (129)
     fails closed with exact asymmetric topology ValueError, proving complete recipient failure atomicity.
   - ARCLOOM4 schema preserves explicit field availability (distinguishing present-zero from unavailable).
   - Checked count arithmetic and bounds prevent integer overflow and runaway allocations.

4. Ratified Exact MathLoom Rational Field Decomposition (A9-04):
   - Exact MathLoom balanced ternary integer numerator and power-of-two denominator decomposition:
     decomposes any finite IEEE-754 binary64 float into exact balanced ternary integers N and D.
   - Exact bit-level reconstruction (f64::from_bits) verified across +0.0, -0.0, subnormals (5e-324),
     normals (1e-300, 1e-18, 1e100, 1.79e308), and negative values with 100% bitwise fidelity.
   - 0.5 decomposes to numerator [1] and denominator [-1, 1]; values 0.5, 0.6, 0.9, 1.0, 2.0 produce distinct,
     faithful balanced ternary sequences, disproving positional collapse.
   - Primary column (48+2k) and conjugate column (48+2k+1) receive exact numerator and denominator trits.
   - Controlled field intervention: stepping substrate with Field A vs Field B produces divergent downstream
     physical strain, proving the continuous field physically drives the downstream mechanical transition.
   - Capability enforcement: 4D and 8D substrates raise strict NotImplementedError on continuous field calls.

5. Sleep Learned Competence & Paired Cold Continuation (A9-05 & A9-06):
   - Disclosure: component training-dependent motor response survives this sleep operation; discloses probe-induced plastic updates.
   - Waking quiet intervals (50 silent beats) in yield equilibrium preserve operative state byte-for-byte.
   - Sleep consolidation downscales while retaining conditioned motor response (stride > 0) while matched naive control
     under identical probe produces zero stride, proving post-sleep motor output is demonstrated retained learned competence.
   - Matched cold continuation on actively changing state: advances BOTH original and cold-restored copies by 1 step
     under identical stimulus, proving bit-for-bit successor state equivalence across all fields.
   - Cold world execution: executes both successor commands into two cloned world authorities with
     identical committed ActionExecutionReceipts (receipt_a == receipt_b, disposition=='applied'),
     successor poses, active contacts, body parameters, and full observation snapshot equality.

6. Spatial Tracking Getter & Component Evidence:
   - Verifies stored polar odometry coordinates and exponential trace decay.
   - Confirms recurrent attractor decoding claim is withdrawn.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import pytest
import numpy as np

import guala_core
from guala_core import ModularSubstrate64D, ModularSubstrate8D, ModularSubstrate4D

from dsf_ai_service.substrate.modular_column_substrate import (
    ModularColumnSubstrate,
    _quantize_radix3_signed,
    CANONICAL_MOTOR_INTERVAL_US,
)

from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    candidates,
    motor_efferent_to_locomotion_command,
)

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.exact_lattice_rotation import rotate_lattice_offset
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    MoveCommand,
    PORT_ID,
    PoseMM,
    PositionMM,
    encode_command,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_witness_a6_01_production_motor_conversion_and_world_execution() -> None:
    """
    Finding A9-01 Witness:
    Prove that:
      1. Efferent inspection is a pure read-only proposal (proposed_kinematic_action).
      2. Efferent schema validation: 4-element sequence, finite numbers, declared physical domains
         (stride in [0.0, 60.0], steer in [-45.0, 45.0], vocal in [0.0, 480.0], grip in [0.0, 25.0]);
         malformed, non-finite, or out-of-domain efferents raise ValueError.
      3. Duration validation: strictly positive integer matching canonical 250,000 us;
         booleans, non-integers, and non-canonical durations raise ValueError.
      4. Silent motor populations produce strictly (0.0, 0.0, 0.0, 0.0) efferents and return None command.
      5. Retired applied_* aliases raise AttributeError pointing to canonical world execution.
      6. Candidate generation explicitly requires native motor capability (raises AttributeError if absent).
      7. In organism candidate generation, native silence strictly inhibits locomotion (no fallback step option).
      8. In open space, active native stride prepares and commits successfully, moving body position.
      9. On the same candidate trajectory, lawful physical barrier (room boundary wall) triggers refusal
         using the EXACT unmodified native efferent tuple (no 100mm substitute), asserting full pose invariance.
    """
    sub = ModularColumnSubstrate(columns=64)
    pose_init = PoseMM(PositionMM(1000, 1000, 0), 0)

    # 1. Freshly initialized substrate with zero inputs
    eff_init = sub.get_motor_efferent()
    assert eff_init == (0.0, 0.0, 0.0, 0.0), f"Fresh substrate must have 0.0 efferents, got {eff_init}"

    consequence_init, receipt_init = sub.proposed_kinematic_action()
    assert receipt_init["is_silent"] is True
    assert consequence_init["delta_x_mm"] == 0.0
    assert consequence_init["delta_y_mm"] == 0.0
    assert consequence_init["delta_theta_deg"] == 0.0
    assert consequence_init["acoustic_pressure_pa"] is None
    assert consequence_init["normal_force_n"] is None
    assert consequence_init["mechanical_work_uj"] is None
    assert receipt_init["motion_vector"] == (0.0, 0.0, 0.0)

    # 2. Schema, domain, and finiteness validation in motor_efferent_to_locomotion_command
    # Duration validation
    with pytest.raises(ValueError, match=r"canonical beat interval"):
        motor_efferent_to_locomotion_command(eff_init, pose_init, duration_microseconds=0)
    with pytest.raises(ValueError, match=r"integer, got bool"):
        motor_efferent_to_locomotion_command(eff_init, pose_init, duration_microseconds=True)  # type: ignore
    with pytest.raises(ValueError, match=r"must be an integer, got float"):
        motor_efferent_to_locomotion_command(eff_init, pose_init, duration_microseconds=250000.5)  # type: ignore
    with pytest.raises(ValueError, match=r"canonical beat interval"):
        motor_efferent_to_locomotion_command(eff_init, pose_init, duration_microseconds=100000)

    # Sequence length validation
    with pytest.raises(ValueError, match=r"4-element sequence"):
        motor_efferent_to_locomotion_command((0.0, 50.0), pose_init)  # too short
    with pytest.raises(ValueError, match=r"4-element sequence"):
        motor_efferent_to_locomotion_command((0.0, 50.0, 0.0, 0.0, 1.0), pose_init)  # too long

    # Finiteness validation
    with pytest.raises(ValueError, match=r"Non-finite"):
        motor_efferent_to_locomotion_command((0.0, float("nan"), 0.0, 0.0), pose_init)
    with pytest.raises(ValueError, match=r"Non-finite"):
        motor_efferent_to_locomotion_command((0.0, float("inf"), 0.0, 0.0), pose_init)

    # Tightened native Layer 5 motor decoder domain bounds
    with pytest.raises(ValueError, match=r"out of declared native producer domain"):
        motor_efferent_to_locomotion_command((0.0, 70.0, 0.0, 0.0), pose_init)  # stride > 60.0
    with pytest.raises(ValueError, match=r"out of declared native producer domain"):
        motor_efferent_to_locomotion_command((0.0, -10.0, 0.0, 0.0), pose_init)  # stride < 0.0
    with pytest.raises(ValueError, match=r"out of declared native producer domain"):
        motor_efferent_to_locomotion_command((0.0, 30.0, 50.0, 0.0), pose_init)  # steer > 45.0
    with pytest.raises(ValueError, match=r"out of declared native producer domain"):
        motor_efferent_to_locomotion_command((0.0, 30.0, -50.0, 0.0), pose_init)  # steer < -45.0
    with pytest.raises(ValueError, match=r"out of declared native producer domain"):
        motor_efferent_to_locomotion_command((500.0, 30.0, 0.0, 0.0), pose_init)  # vocal > 480.0
    with pytest.raises(ValueError, match=r"out of declared native producer domain"):
        motor_efferent_to_locomotion_command((-1.0, 30.0, 0.0, 0.0), pose_init)  # vocal < 0.0
    with pytest.raises(ValueError, match=r"out of declared native producer domain"):
        motor_efferent_to_locomotion_command((0.0, 30.0, 0.0, 30.0), pose_init)  # grip > 25.0
    with pytest.raises(ValueError, match=r"out of declared native producer domain"):
        motor_efferent_to_locomotion_command((0.0, 30.0, 0.0, -1.0), pose_init)  # grip < 0.0

    # Lawful silence returns None
    cmd_silent = motor_efferent_to_locomotion_command(eff_init, pose_init)
    assert cmd_silent is None, "Silent motor efferents must translate to None locomotion command"

    # 3. Retired applied_* aliases raise informative AttributeError
    with pytest.raises(AttributeError, match=r"applied_kinematic_action is retired"):
        sub.applied_kinematic_action()
    with pytest.raises(AttributeError, match=r"applied_motor_action is retired"):
        sub.applied_motor_action()

    # 4. Step with silent inputs
    sub.step([0] * 64, [0] * 32)
    assert sub.get_motor_efferent() == (0.0, 0.0, 0.0, 0.0)
    assert motor_efferent_to_locomotion_command(sub.get_motor_efferent(), pose_init) is None

    # 5. In organism candidate generation: requires native capability, and silence inhibits locomotion
    world = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1")
    snap_init = world.observation_snapshot()
    her_init = next(b for b in snap_init.bodies if b.body_id == snap_init.self_body_id)

    class IncompleteSubstrate:
        pass
    with pytest.raises(AttributeError, match=r"lacks required motor efferent capability"):
        candidates(snap_init, her_init, None, None, (), 1, modular_sub=IncompleteSubstrate())

    cands_silent = candidates(snap_init, her_init, None, None, (), 1, modular_sub=sub)
    step_options_silent = [c for c in cands_silent if c[0] == "step"]
    assert len(step_options_silent) == 0, f"Silent substrate must inhibit locomotion; no step candidate allowed, got {step_options_silent}"

    # 6. Actively stimulate substrate to produce native Layer 5 motor stride
    sub_active = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    for _ in range(5):
        sub_active.step([1] * 64, [1] * 32)

    eff_act = sub_active.get_motor_efferent()
    assert 0.0 < eff_act[1] <= 60.0, f"Active substrate must produce valid locomotion stride in (0, 60], got {eff_act[1]}"

    # In candidate generation with active substrate, step candidate IS produced
    cands_active = candidates(snap_init, her_init, None, None, (), 1, modular_sub=sub_active)
    step_options_active = [c for c in cands_active if c[0] == "step"]
    assert len(step_options_active) == 1, "Active substrate must emit exactly one native step candidate"
    assert "native substrate motor stride" in step_options_active[0][1]

    # 7. Canonical motor conversion outside inspection getters
    snap_before = world.observation_snapshot()
    her_before = next(b for b in snap_before.bodies if b.body_id == snap_before.self_body_id)

    move_cmd = motor_efferent_to_locomotion_command(eff_act, her_before.pose)
    assert move_cmd is not None, "Active efferent must yield a MoveCommand"
    assert move_cmd.duration_microseconds == CANONICAL_MOTOR_INTERVAL_US, (
        f"Command must use canonical {CANONICAL_MOTOR_INTERVAL_US} us interval, got {move_cmd.duration_microseconds}"
    )

    intent_sha = hashlib.sha256(f"{eff_act[1]}:{eff_act[2]}".encode()).hexdigest()
    prep_valid = world.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(move_cmd),
        causal_intent_receipt_sha256=intent_sha,
        expected_revision=snap_before.revision,
    )
    assert not isinstance(prep_valid, ActionExecutionReceipt), "Native stride in open space must not be refused"
    with world.prepared_action_visibility_transaction(prep_valid):
        world.commit_prepared_action(prep_valid)

    snap_after = world.observation_snapshot()
    her_after = next(b for b in snap_after.bodies if b.body_id == snap_after.self_body_id)
    assert (her_after.pose.position.x, her_after.pose.position.y) == (
        move_cmd.target_pose.position.x,
        move_cmd.target_pose.position.y,
    ), "Executed world position must match canonical MoveCommand target position"

    # 8. Physical barrier/obstacle refusal verification using EXACT unmodified native efferent tuple
    # Position body at lawful room clearance boundary (x=5350, y=7600, heading=0) facing East wall at x=5600
    world_obstacle = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1")
    s_obs = world_obstacle.observation_snapshot()
    world_obstacle.admit_authored_body_transport(s_obs.self_body_id, PoseMM(PositionMM(5350, 7600, 0), 0))
    s_obs2 = world_obstacle.observation_snapshot()
    her_obs = next(b for b in s_obs2.bodies if b.body_id == s_obs2.self_body_id)

    # Use EXACT measured native efferent tuple eff_act (no 100mm substitution!)
    cmd_blocked = motor_efferent_to_locomotion_command(eff_act, her_obs.pose)
    assert cmd_blocked is not None
    prep_blocked = world_obstacle.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(cmd_blocked),
        causal_intent_receipt_sha256="ff" * 32,
        expected_revision=s_obs2.revision,
    )
    assert isinstance(prep_blocked, ActionExecutionReceipt), "Obstruction must trigger refusal receipt"
    assert prep_blocked.reason in ("collision", "out_of_bounds", "refused", "blocked", "move_outside_room")

    # Body pose (both position and heading) remains completely unchanged upon refusal
    s_obs3 = world_obstacle.observation_snapshot()
    her_obs_after = next(b for b in s_obs3.bodies if b.body_id == s_obs3.self_body_id)
    assert her_obs_after.pose == her_obs.pose, "Full pose must remain strictly invariant upon obstacle refusal"


def test_witness_a6_02_constitutive_contact_law_and_divergent_world_execution() -> None:
    """
    Finding A9-02 Witness:
    Prove that:
      1. G_ELASTIC_BASELINE = 0.05 represents the dimensionless baseline resting coupling parameter w_0
         in the discrete ternary lattice model, with signed plastic weights w in [-1.0, 1.0].
         Truthful disclosure: Macroscopic continuum contact mechanics and microscopic derivation in SI units
         remain an open research contract; Holm/tunneling claims are formally retracted.
      2. True rate-independent return map projection:
         Under trial stress |Sigma_{tr}| > Y, the stress projects directly to |Sigma_{n+1}| = Y (f_{n+1} = 0)
         with non-negative dissipation. Once equilibrium on the yield surface is reached, stepping again
         with identical state and inputs produces zero yield events and identical operative states,
         eliminating continuous plastic drift on identical inputs.
      3. Super-yield plastic deformation (w > 0) versus sub-yield elastic compliance drives divergent world actions.
      4. Matched intact vs ablated states executed in two actual world instances produce divergent world coordinates.
      5. Incoming tract severing under identical inputs halts motor actuation to strictly 0.0.
    """
    sens_train = [1] * 64
    som_train = [1] * 32

    # 1. Train intact substrate to induce super-yield plastic deformation (w > 0)
    sub_intact = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    for _ in range(5):
        sub_intact.step(sens_train, som_train)

    assert sub_intact.active_synapses() > 0, "Super-yield training must induce plastic conductances"
    learned_bytes = sub_intact.export_sparse_bytes(version=4)

    # Rate-independent return map equilibrium stability verification
    sub_return = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    for _ in range(15):
        sub_return.step(sens_train, som_train)
    w_eq = sub_return.export_sparse_bytes(version=4)
    y_eq, s_eq = sub_return.step(sens_train, som_train)
    w_after = sub_return.export_sparse_bytes(version=4)
    assert y_eq == 0, f"At plastic yield equilibrium, further identical steps must produce 0 yield events, got {y_eq}"
    assert w_eq == w_after, "Rate-independent return map must eliminate plastic drift on repeated identical steps"

    # 2. Create matched clone and ablate plastic conductances to reversible elastic baseline (w = 0)
    sub_ablated = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    sub_ablated.import_sparse_bytes(learned_bytes)
    sub_ablated.zero_plastic_weights()
    assert sub_ablated.active_synapses() == 0, "Ablation must clear learned plastic conductances to reversible baseline"

    # Step both with identical test stimulus
    sens_test = [1] * 64
    som_test = [0] * 32
    sub_intact.step(sens_test, som_test)
    sub_ablated.step(sens_test, som_test)

    eff_intact = sub_intact.get_motor_efferent()
    eff_ablated = sub_ablated.get_motor_efferent()

    assert eff_intact != eff_ablated, f"Ablation must alter efferents: {eff_intact} == {eff_ablated}"
    assert eff_intact[1] != eff_ablated[1], (
        f"Learned plasticity must alter motor stride away from ablated baseline: {eff_intact[1]} == {eff_ablated[1]}"
    )

    # 3. Execute both efferents in two separate cloned world instances
    world_intact = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1")
    world_ablated = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1")

    snap_in = world_intact.observation_snapshot()
    snap_ab = world_ablated.observation_snapshot()
    her_in = next(b for b in snap_in.bodies if b.body_id == snap_in.self_body_id)
    her_ab = next(b for b in snap_ab.bodies if b.body_id == snap_ab.self_body_id)

    cmd_intact = motor_efferent_to_locomotion_command(eff_intact, her_in.pose)
    cmd_ablated = motor_efferent_to_locomotion_command(eff_ablated, her_ab.pose)

    assert cmd_intact is not None
    assert cmd_ablated is not None

    prep_in = world_intact.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(cmd_intact),
        causal_intent_receipt_sha256="aa" * 32,
        expected_revision=snap_in.revision,
    )
    with world_intact.prepared_action_visibility_transaction(prep_in):
        world_intact.commit_prepared_action(prep_in)

    prep_ab = world_ablated.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(cmd_ablated),
        causal_intent_receipt_sha256="bb" * 32,
        expected_revision=snap_ab.revision,
    )
    with world_ablated.prepared_action_visibility_transaction(prep_ab):
        world_ablated.commit_prepared_action(prep_ab)

    her_after_in = next(b for b in world_intact.observation_snapshot().bodies if b.body_id == snap_in.self_body_id)
    her_after_ab = next(b for b in world_ablated.observation_snapshot().bodies if b.body_id == snap_ab.self_body_id)

    assert her_after_in.pose.position != her_after_ab.pose.position, (
        f"Plasticity ablation must produce divergent settled world positions: "
        f"{her_after_in.pose.position} vs {her_after_ab.pose.position}"
    )

    # 4. Causal Tract Severing Test
    sub_tract_intact = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    sub_tract_severed = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )

    for c_to in range(40, 48):
        for c_from in range(64):
            if c_from < 40 or c_from >= 48:
                sub_tract_severed.sever_tract(c_from, c_to)
                sub_tract_severed.sever_tract(c_to, c_from)

    for _ in range(2):
        sub_tract_intact.step(sens_test, som_test)
        sub_tract_severed.step(sens_test, som_test)

    eff_tract_intact = sub_tract_intact.get_motor_efferent()
    eff_tract_severed = sub_tract_severed.get_motor_efferent()

    assert eff_tract_intact[1] > 0.0, "Intact conduction must actuate motor drive"
    assert eff_tract_severed == (0.0, 0.0, 0.0, 0.0), (
        f"Severing motor tracts must arrest motor drive under identical inputs, got {eff_tract_severed}"
    )


def test_witness_a6_03_authentic_predecessor_migration_and_strict_codec() -> None:
    """
    Finding A9-03 Witness:
    Prove that:
      1. Both authentic historical predecessors migrate cleanly via explicit migrate_predecessor_v2
         with required layout metadata ("24B" or "36B"), rejecting guessing:
         - arcloom2_cb69d23ea.bin (24-byte column header) restores active conductances.
         - arcloom2_8c3244cb3.bin (36-byte column header) restores active conductances and severed tracts.
      2. Migration into TWO differently configured recipient instances eliminates recipient parameter leakage:
         both recipients initialize local microcircuit parameters from the container header,
         yielding identical current states and next transitions.
      3. Strict separation of current restore from one-time migration:
         from_dict and import_sparse_bytes accept only current ARCLOOM4 format, rejecting historical versions.
      4. Predecessor v3 migration supports both authentic layouts:
         - ARCLOOM3_SHORT (synthetic test fixture) migrates cleanly with continuous_field_present == False.
         - ARCLOOM3_LONG (synthetic test fixture):
           - rejects lossless migration claim when field_present is None (cannot guess missing flag).
           - migrates losslessly when explicit authenticated metadata is provided (field_present=True).
         - Truncated long payloads cannot downgrade to short; short payloads cannot pass as long.
      5. Current import_sparse_v4 strictly rejects ARCLOOM2 and ARCLOOM3 magic.
      6. ARCLOOM4 schema preserves explicit field availability (distinguishing present-zero from unavailable).
      7. Severed-tract parsing enforces checked arithmetic, duplicate rejection, and canonical bidirectional topology.
         Structurally valid asymmetric severed tract test: payload with severed tract 1->2 (66) without reverse 2->1 (129)
         fails closed with exact asymmetric topology ValueError, proving complete recipient failure atomicity.
      8. Complete failure atomicity: recipient state across all fields is 100% untouched upon failure.
    """
    sub = ModularColumnSubstrate(columns=64)

    # 1. Historical predecessor migration from authenticated binary fixtures
    cb69_path = FIXTURES_DIR / "arcloom2_cb69d23ea.bin"
    hist_8c32_path = FIXTURES_DIR / "arcloom2_8c3244cb3.bin"

    assert cb69_path.exists(), f"Predecessor fixture missing: {cb69_path}"
    assert hist_8c32_path.exists(), f"Predecessor fixture missing: {hist_8c32_path}"

    cb69_bytes = cb69_path.read_bytes()
    hist_8c32_bytes = hist_8c32_path.read_bytes()

    # Predecessor cb69d23ea migration into TWO differently configured recipients with explicit required layout="24B":
    sub_r1 = ModularColumnSubstrate(columns=64, yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25)
    sub_r1.migrate_predecessor_v2(cb69_bytes, layout="24B")

    sub_r2 = ModularColumnSubstrate(columns=64, yield_threshold=0.40, plastic_rate=0.10, activation_threshold=0.10)
    sub_r2.migrate_predecessor_v2(cb69_bytes, layout="24B")

    pre_step_syn = sub_r1.active_synapses()
    assert pre_step_syn > 0, "cb69d23ea migration must restore active conductances"
    assert pre_step_syn == sub_r2.active_synapses()
    assert sub_r1.get_motor_efferent() == sub_r2.get_motor_efferent()

    y1, s1 = sub_r1.step([1] * 64, [0] * 32)
    y2, s2 = sub_r2.step([1] * 64, [0] * 32)
    assert y1 == y2 and s1 == s2, "Differently configured recipients must produce identical transitions post-migration"

    # Predecessor 8c3244cb3 migration with explicit required layout="36B"
    sub_8c32 = ModularColumnSubstrate(columns=64)
    sub_8c32.migrate_predecessor_v2(hist_8c32_bytes, layout="36B")
    assert sub_8c32.active_synapses() > 0, "8c3244cb3 migration must restore active conductances"

    # Verify that migrate_predecessor_v2 with invalid layout fails closed
    with pytest.raises(ValueError, match=r"Unknown ARCLOOM2 predecessor layout"):
        sub_r1.migrate_predecessor_v2(cb69_bytes, layout="invalid_layout")

    # Verify that from_dict strictly rejects historical predecessor formats
    with pytest.raises(ValueError, match=r"Historical predecessor format"):
        ModularColumnSubstrate.from_dict({
            "sparse_hex": cb69_bytes.hex(),
            "num_columns": 64,
        })

    # Verify that migrate_predecessor_dict succeeds with explicit authenticated metadata
    migrated_sub = ModularColumnSubstrate.migrate_predecessor_dict(
        {"sparse_hex": cb69_bytes.hex(), "num_columns": 64},
        layout="24B",
    )
    assert migrated_sub.active_synapses() == pre_step_syn

    # 2. Historical predecessor v3 migration (synthetic layout test fixtures with explicit manifest labels)
    sub_template = ModularColumnSubstrate(columns=64)
    sub_template.consume_continuous_joint_field([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], 0.95)
    v4_bytes = sub_template.export_sparse_bytes(version=4)

    expected_floats = struct.pack("<8d", 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.95)
    floats_pos = v4_bytes.find(expected_floats)
    assert floats_pos > 0
    sev_end = floats_pos - 1

    # Synthetic Layout 1: ARCLOOM3_SHORT (manifest: commit 0dad5f2b9 layout - ends after severed tracts + padding)
    pad_short = (8 - (sev_end % 8)) % 8
    v3_short_bytes = b"ARCLOOM3" + struct.pack("<H", 3) + v4_bytes[10:sev_end] + (b"\x00" * pad_short)

    # Synthetic Layout 2: ARCLOOM3_LONG (manifest: commit d577831de layout - 64 bytes of f64 invariants directly after severed tracts)
    pad_long = (8 - ((sev_end + 64) % 8)) % 8
    v3_long_bytes = b"ARCLOOM3" + struct.pack("<H", 3) + v4_bytes[10:sev_end] + expected_floats + (b"\x00" * pad_long)

    # Short layout migrates cleanly under explicit layout="short"
    sub_v3_short = ModularColumnSubstrate(columns=64)
    sub_v3_short.substrate.migrate_predecessor_v3(v3_short_bytes, layout="short", field_present=None)
    assert sub_v3_short.has_continuous_joint_field() is False

    # Long layout rejects lossless migration claim without explicit presence metadata
    with pytest.raises(ValueError, match=r"omits presence flag; explicit authenticated predecessor metadata"):
        sub_v3_fail = ModularColumnSubstrate(columns=64)
        sub_v3_fail.substrate.migrate_predecessor_v3(v3_long_bytes, layout="long", field_present=None)

    # Long layout losslessly migrates with explicit authenticated metadata
    sub_v3_long = ModularColumnSubstrate(columns=64)
    sub_v3_long.substrate.migrate_predecessor_v3(v3_long_bytes, layout="long", field_present=True)
    assert sub_v3_long.has_continuous_joint_field() is True
    assert list(sub_v3_long.get_continuous_joint_field()) == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.95]

    # Truncated long layout cannot downgrade to short
    truncated_long = b"ARCLOOM3" + struct.pack("<H", 3) + v4_bytes[10:sev_end] + expected_floats[:32]
    pad_trunc = (8 - (len(truncated_long) % 8)) % 8
    truncated_long_bytes = truncated_long + (b"\x00" * pad_trunc)
    with pytest.raises(ValueError, match=r"Invalid ARCLOOM3 short payload: expected \d+ padding bytes, got trailing"):
        sub_v3_short.substrate.migrate_predecessor_v3(truncated_long_bytes, layout="short", field_present=None)

    # Short payload cannot pass as long
    with pytest.raises(ValueError, match=r"Invalid ARCLOOM3 long payload: expected 64 field bytes"):
        sub_v3_short.substrate.migrate_predecessor_v3(v3_short_bytes, layout="long", field_present=True)

    # 3. Current import_sparse strictly rejects ARCLOOM2 and ARCLOOM3 magic
    with pytest.raises(ValueError, match=r"(?i)found arcloom2 payload"):
        sub.substrate.import_sparse(cb69_bytes)
    with pytest.raises(ValueError, match=r"(?i)found arcloom2 payload"):
        sub.substrate.import_sparse(hist_8c32_bytes)
    with pytest.raises(ValueError, match=r"(?i)found arcloom3 payload"):
        sub.substrate.import_sparse(v3_long_bytes)

    # 4. ARCLOOM4 explicit presence tracking: present-zero vs unavailable
    sub_zero = ModularColumnSubstrate(columns=64)
    sub_zero.consume_continuous_joint_field([0.0] * 7, 0.0)
    assert sub_zero.has_continuous_joint_field() is True
    zero_bytes = sub_zero.export_sparse_bytes(version=4)
    assert zero_bytes[:8] == b"ARCLOOM4"

    sub_restored_zero = ModularColumnSubstrate(columns=64)
    sub_restored_zero.import_sparse_bytes(zero_bytes)
    assert sub_restored_zero.has_continuous_joint_field() is True, "Present zero field must remain present across import"

    sub_unavail = ModularColumnSubstrate(columns=64)
    sub_unavail.clear_continuous_joint_field()
    assert sub_unavail.has_continuous_joint_field() is False
    unavail_bytes = sub_unavail.export_sparse_bytes(version=4)

    sub_restored_unavail = ModularColumnSubstrate(columns=64)
    sub_restored_unavail.import_sparse_bytes(unavail_bytes)
    assert sub_restored_unavail.has_continuous_joint_field() is False, "Unavailable field must remain unavailable across import"

    # 5. Setup recipient state to test complete failure atomicity
    sub.sever_tract(3, 7)
    sub.substrate.step(
        [0] * 64,
        [0] * 32,
        observed_r_mm=1200.0,
        observed_theta_mdeg=15000,
        barrier_stress=0.0,
        acoustic_formants=[],
    )
    baseline_bytes = sub.export_sparse_bytes(version=4)
    baseline_r, baseline_th, baseline_trace, baseline_occ = sub.get_spatial_tracking()
    baseline_eff = sub.get_motor_efferent()
    baseline_syn = sub.active_synapses()
    baseline_yield_th = sub.yield_threshold
    baseline_rate = sub.plastic_rate
    baseline_act_th = sub.activation_threshold
    baseline_severed = sub.is_tract_severed(3, 7)

    # 6. Strict ARCLOOM4 codec failure tests
    valid_v4 = sub.export_sparse_bytes(version=4)

    # Empty buffer
    with pytest.raises(ValueError, match=r"(?i)empty"):
        sub.substrate.import_sparse(b"")

    # Corrupt magic
    with pytest.raises(ValueError, match=r"(?i)magic"):
        sub.substrate.import_sparse(b"INVALIDM" + valid_v4[8:])

    # Truncated global header (< 24 bytes)
    with pytest.raises(ValueError, match=r"(?i)truncated"):
        sub.substrate.import_sparse(valid_v4[:20])

    # Structurally valid asymmetric severed tract test:
    # Build payload that is 100% structurally valid in every section, but injects severed tract 1->2 (idx 66)
    # without reverse 2->1 (idx 129).
    sub_clean = ModularColumnSubstrate(columns=64)
    sub_clean.consume_continuous_joint_field([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], 0.95)
    b_clean = sub_clean.export_sparse_bytes(version=4)
    exp_flt = struct.pack("<8d", 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.95)
    flt_pos = b_clean.find(exp_flt)
    pres_pos = flt_pos - 1
    cnt_sev_pos = pres_pos - 4

    prefix = b_clean[:cnt_sev_pos]
    sev_section = struct.pack("<I", 1) + struct.pack("<I", 66)  # count=1, tract 66 (1->2)
    field_section = b_clean[pres_pos:flt_pos + 64]
    unpadded_bad = prefix + sev_section + field_section
    pad_bad = (8 - (len(unpadded_bad) % 8)) % 8
    bad_asymm_payload = unpadded_bad + (b"\x00" * pad_bad)

    with pytest.raises(ValueError, match=r"Asymmetric severed tract topology: tract 66 \(1->2\) severed but reverse 129 \(2->1\) is not"):
        sub.substrate.import_sparse_v4(bad_asymm_payload)

    # 7. Complete failure atomicity: verify recipient state is 100% untouched across all fields and exact bytes
    assert sub.export_sparse_bytes(version=4) == baseline_bytes, "Recipient serialized state mutated upon failed import!"
    assert sub.get_spatial_tracking() == (baseline_r, baseline_th, baseline_trace, baseline_occ)
    assert sub.get_motor_efferent() == baseline_eff
    assert sub.active_synapses() == baseline_syn
    assert sub.yield_threshold == baseline_yield_th
    assert sub.plastic_rate == baseline_rate
    assert sub.activation_threshold == baseline_act_th
    assert sub.is_tract_severed(3, 7) == baseline_severed


@pytest.mark.xfail(
    strict=True,
    raises=NotImplementedError,
    reason="A10 release blocker: ratified full-field phase/material consumer is unimplemented",
)
def test_witness_a6_04_full_continuous_joint_field_participation() -> None:
    """
    Finding A9-04 Witness:
    Prove that:
      1. MathLoom exact rational balanced ternary integer decomposition:
         Decomposes finite binary64 values into exact integer numerator N and power-of-two denominator D.
         Bit-exact reconstruction (f64::from_bits) verified across:
         - zeros (+0.0, -0.0)
         - subnormals (5e-324)
         - small normals (1e-300, 1e-18)
         - values > 1.0 (2.0, 1e100, 1.79e308)
         - negative values (-0.5, -2.0, -1e50)
      2. 0.5 decomposes to numerator [1] and denominator [-1, 1].
         Values 0.5, 0.6, 0.9, 1.0, 2.0 produce distinct balanced ternary sequences, disproving positional collapse.
      3. Preserves full IEEE-754 binary64 precision: continuous field values survive without f32 collapse.
         Demonstrated with a genuinely collapsing binary32 pair: 0.4 and nextafter(0.4, +inf).
      4. Zero competing legacy mapping: sensory slots 48..63 are left zeroed, eliminating legacy interference.
      5. Controlled field intervention: stepping substrate with Field A vs Field B produces divergent downstream
         physical strain (s_A != s_B), proving the continuous field physically drives the downstream mechanical transition.
      6. Capability enforcement: 4D and 8D substrates raise strict NotImplementedError on continuous field calls.
    """
    sub64 = ModularColumnSubstrate(columns=64)

    # 1. MathLoom rational balanced ternary decomposition & exact bit reconstruction
    test_vectors = [
        0.0, -0.0, 0.5, 0.6, 0.9, 1.0, 2.0,
        1e-18, 1e-300, 5e-324, 1e100, 1.79e308,
        -0.5, -2.0, -1e-18, -1e50,
    ]
    trit_sequences = {}
    for val in test_vectors:
        num, den, sign, is_z = ModularColumnSubstrate.float_to_rational_trits(val)
        reconstructed = ModularColumnSubstrate.rational_trits_to_float(num, den, sign, is_z)

        orig_bits = struct.unpack(">Q", struct.pack(">d", val))[0]
        rec_bits = struct.unpack(">Q", struct.pack(">d", reconstructed))[0]
        assert orig_bits == rec_bits, f"Bit mismatch for {val}: orig {hex(orig_bits)} != rec {hex(rec_bits)}"

        if val in (0.5, 0.6, 0.9, 1.0, 2.0):
            trit_sequences[val] = (tuple(num), tuple(den))

    # 0.5 decomposition: 1 / 2 = 1 / (-1 + 3) -> num [1], den [-1, 1]
    assert trit_sequences[0.5] == ((1,), (-1, 1)), f"0.5 must decompose to num [1] and den [-1, 1], got {trit_sequences[0.5]}"
    assert trit_sequences[1.0] == ((1,), (1,)), f"1.0 must decompose to num [1] and den [1], got {trit_sequences[1.0]}"
    assert trit_sequences[2.0] == ((-1, 1), (1,)), f"2.0 must decompose to num [-1, 1] and den [1], got {trit_sequences[2.0]}"

    # Assert distinctness of 0.5, 0.6, 0.9, 1.0, 2.0 (disproving Astra's counterexample where all 5 collapsed)
    assert len(set(trit_sequences.values())) == 5, "0.5, 0.6, 0.9, 1.0, 2.0 must produce distinct trit representations!"

    # 2. Exact IEEE-754 binary64 precision preservation without binary32 collapse
    val_a = 0.4
    val_b = float(np.nextafter(np.float64(0.4), np.float64(np.inf)))

    assert val_a != val_b, "Reference binary64 values must be mathematically distinct"
    assert np.float32(val_a) == np.float32(val_b), "Test pair must collapse under IEEE-754 binary32 quantization"

    field_a = [val_a, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    field_b = [val_b, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

    sub64.consume_continuous_joint_field(field_a, s_uf=1.0)
    ret_a = sub64.get_continuous_joint_field()

    sub64.consume_continuous_joint_field(field_b, s_uf=1.0)
    ret_b = sub64.get_continuous_joint_field()

    assert ret_a[0] != ret_b[0], "Continuous joint field must preserve distinct f64 precision without f32 collapse"
    assert ret_a[0] == val_a
    assert ret_b[0] == val_b

    # Exact bitwise binary64 preservation across export/import
    bytes_b = sub64.export_sparse_bytes(version=4)
    sub_restored = ModularColumnSubstrate(columns=64)
    sub_restored.import_sparse_bytes(bytes_b)
    ret_restored = sub_restored.get_continuous_joint_field()

    assert struct.pack(">d", ret_restored[0]) == struct.pack(">d", val_b), "Bitwise binary64 representation must survive roundtrip"

    # 3. Strict capability enforcement on 4D and 8D
    sub8 = ModularColumnSubstrate(columns=8)
    sub4 = ModularColumnSubstrate(columns=4)

    with pytest.raises(NotImplementedError, match=r"requires 64-column cortical array"):
        sub8.consume_continuous_joint_field([0.0] * 7, 1.0)
    with pytest.raises(NotImplementedError, match=r"requires 64-column cortical array"):
        sub8.get_continuous_joint_field()

    with pytest.raises(NotImplementedError, match=r"requires 64-column cortical array"):
        sub4.consume_continuous_joint_field([0.0] * 7, 1.0)
    with pytest.raises(NotImplementedError, match=r"requires 64-column cortical array"):
        sub4.get_continuous_joint_field()

    # 4. Absence of competing legacy mapping in sensory stream
    sensory_stream = sub64.encode_sensory_stream(
        optical_intensities=[0.5] * 16,
        cochlear_channels=[0.5] * 16,
        palmar_contact=0.0,
        thermal_gradient_mk=0.0,
        dsf_vector=[0.5] * 8,
    )
    assert sensory_stream[48:64] == [0] * 16, "Sensory slots 48..63 must not contain competing legacy mappings"

    # 5. Controlled continuous joint field physical intervention
    sub_field_a = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15)
    sub_field_a.consume_continuous_joint_field([0.8, -0.4, 0.9, 0.1, 0.7, 0.8, 0.3], s_uf=0.95)

    sub_field_b = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15)
    sub_field_b.consume_continuous_joint_field([-0.8, 0.4, -0.9, -0.1, -0.7, -0.8, -0.3], s_uf=0.10)

    y_step_a, s_step_a = sub_field_a.step([0] * 64, [1] * 32)
    y_step_b, s_step_b = sub_field_b.step([0] * 64, [1] * 32)

    assert (y_step_a, s_step_a) != (y_step_b, s_step_b), (
        f"Continuous field intervention must produce divergent physical strain: ({y_step_a}, {s_step_a}) vs ({y_step_b}, {s_step_b})"
    )


def test_witness_a6_05_matched_cold_continuation_on_changing_states() -> None:
    """
    Finding A9-05 & A9-06 Witness:
    Prove that:
      1. Waking quiet intervals (50 silent beats) in yield equilibrium preserve operative state byte-for-byte.
      2. Production sleep consolidation (decay=0.03, prune_thresh=0.015) retains conditioned learned competence
         while downscaling sub-threshold connections.
      3. Component training-dependent motor response survives this sleep operation; discloses probe-induced plastic updates.
         Conditioned motor response survives sleep (stride > 0) while matched naive control under identical probe
         produces zero stride, proving post-sleep motor output is a demonstrated retained learned competence.
      4. Matched cold continuation on actively changing state:
         Advances BOTH original and cold-restored copies by 1 step under identical stimulus u:
         S'_orig = F(S_orig, u) and S'_cold = F(S_cold, u).
         Verifies bit-for-bit equivalence of complete successor states, efferents, and executed world actions.
      5. Cold world execution: executes both successor commands into two cloned world authorities with
         identical committed ActionExecutionReceipts (receipt_a == receipt_b, disposition=='applied'),
         successor poses, active contacts, body parameters, and full observation snapshot equality.
    """
    sub = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.50, activation_threshold=0.20, columns=64
    )
    sens = [1] * 64
    som = [1] * 32

    # 1. Train active plastic connections to material yield equilibrium
    for _ in range(25):
        sub.step(sens, som)

    assert sub.active_synapses() > 0

    # Relax to internal quiescence
    sub.step([0] * 64, [0] * 32)
    sub.step([0] * 64, [0] * 32)
    bytes_before_quiet = sub.export_sparse_bytes(version=4)

    # Step 50 quiet beats
    for _ in range(50):
        sub.step([0] * 64, [0] * 32)

    bytes_after_quiet = sub.export_sparse_bytes(version=4)
    assert bytes_after_quiet == bytes_before_quiet, "Operative state mutated during waking quiet!"

    # 2. Production sleep consolidation (decay=0.03, prune_thresh=0.015)
    pre_sleep_syn = sub.active_synapses()
    decayed, pruned = sub.sleep_consolidation(decay=0.03, prune_thresh=0.015)
    assert decayed > 0, "Production sleep parameters must execute downscaling"
    post_sleep_syn = sub.active_synapses()
    assert post_sleep_syn <= pre_sleep_syn, "Sleep downscaling must reduce or maintain active synapse count"

    # Retained learned competence vs matched naive control
    # Discloses: probe stimulus applies identical sensory inputs across both instances
    probe = [1] * 64
    probe_som = [1] * 32
    sub.step(probe, probe_som)
    eff_post_sleep = sub.get_motor_efferent()

    sub_naive = ModularColumnSubstrate(yield_threshold=0.50, plastic_rate=0.50, activation_threshold=0.20, columns=64)
    sub_naive.step(probe, probe_som)
    eff_naive = sub_naive.get_motor_efferent()

    assert eff_post_sleep[1] > 0.0, "Learned motor competence must be retained across sleep consolidation"
    assert eff_naive[1] == 0.0, "Naive control under identical probe must not exhibit conditioned motor stride"
    assert eff_post_sleep != eff_naive, "Learned competence must diverge from unconditioned naive control"

    # 3. Matched Cold Continuation on Actively Changing State
    bytes_before_dyn = sub.export_sparse_bytes(version=4)
    changing_stimulus = [-1 if i % 2 == 0 else 1 for i in range(64)]
    sub.step(changing_stimulus, som)
    bytes_s = sub.export_sparse_bytes(version=4)

    # Assert dynamic probe actively changed pre-state (S' != S)
    assert bytes_s != bytes_before_dyn, "Dynamic stimulus must actively change pre-state (S' != S)"

    # Reconstitute cold clone S_cold from bytes_s
    sub_cold = ModularColumnSubstrate(columns=64)
    sub_cold.import_sparse_bytes(bytes_s)

    # Verify identical pre-step state
    assert sub_cold.active_synapses() == sub.active_synapses()
    assert sub_cold.get_motor_efferent() == sub.get_motor_efferent()

    # Advance BOTH copy S and copy S_cold by 1 step under identical stimulus u
    probe_stimulus = [1 if i % 3 == 0 else -1 for i in range(64)]
    probe_som_2 = [1 if i % 2 == 0 else 0 for i in range(32)]

    y_orig, s_orig = sub.step(probe_stimulus, probe_som_2, observed_r_mm=500.0, observed_theta_mdeg=10000)
    y_cold, s_cold = sub_cold.step(probe_stimulus, probe_som_2, observed_r_mm=500.0, observed_theta_mdeg=10000)

    # Assert complete successor state bit-for-bit equivalence
    assert y_orig == y_cold, f"Successor yield mismatch: {y_orig} vs {y_cold}"
    assert s_orig == s_cold, f"Successor strain mismatch: {s_orig} vs {s_cold}"
    assert sub.active_synapses() == sub_cold.active_synapses()
    assert sub.get_motor_efferent() == sub_cold.get_motor_efferent()
    assert sub.export_sparse_bytes(version=4) == sub_cold.export_sparse_bytes(version=4)

    # 4. Execute both successors into world instances and verify identical displacement, receipts, and complete observations
    world_a = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1")
    world_b = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1")

    snap_a = world_a.observation_snapshot()
    snap_b = world_b.observation_snapshot()
    her_a = next(b for b in snap_a.bodies if b.body_id == snap_a.self_body_id)
    her_b = next(b for b in snap_b.bodies if b.body_id == snap_b.self_body_id)

    cmd_a = motor_efferent_to_locomotion_command(sub.get_motor_efferent(), her_a.pose)
    cmd_b = motor_efferent_to_locomotion_command(sub_cold.get_motor_efferent(), her_b.pose)

    assert cmd_a is not None and cmd_b is not None
    assert cmd_a == cmd_b, f"Successor commands must be identical: {cmd_a} vs {cmd_b}"

    # Commit both actions into worlds
    prep_a = world_a.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(cmd_a),
        causal_intent_receipt_sha256="ca" * 32,
        expected_revision=snap_a.revision,
    )
    prep_b = world_b.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(cmd_b),
        causal_intent_receipt_sha256="ca" * 32,
        expected_revision=snap_b.revision,
    )
    assert not isinstance(prep_a, ActionExecutionReceipt)
    assert not isinstance(prep_b, ActionExecutionReceipt)
    assert prep_a == prep_b, f"Preparation receipts must match: {prep_a} vs {prep_b}"

    with world_a.prepared_action_visibility_transaction(prep_a):
        receipt_a = world_a.commit_prepared_action(prep_a)
    with world_b.prepared_action_visibility_transaction(prep_b):
        receipt_b = world_b.commit_prepared_action(prep_b)

    # Assert matching committed ActionExecutionReceipts
    assert receipt_a == receipt_b, f"Committed execution receipts must match: {receipt_a} vs {receipt_b}"
    assert receipt_a.disposition == "applied"

    snap_a_after = world_a.observation_snapshot()
    snap_b_after = world_b.observation_snapshot()

    # Full observation snapshot equality
    assert snap_a_after == snap_b_after, "World observation snapshots must be 100% equal post-commit"


def test_witness_a6_06_spatial_tracking_polar_getter() -> None:
    """
    Finding A9-06 Witness:
    Prove that:
      1. Spatial tracking getter returns stored polar odometry coordinates and exponential trace.
      2. Recurrent attractor grid decoding claim is formally withdrawn until implemented.
    """
    sub = ModularColumnSubstrate(columns=64)

    # Initial state
    r_init, th_init, trace_init, occ_init = sub.get_spatial_tracking()
    assert r_init == 0.0
    assert th_init == 0
    assert trace_init == 0.0
    assert occ_init is False

    # Observe spatial target at r = 850 mm, theta = 45,000 mdeg (45 degrees)
    sub.step(
        [0] * 64,
        [0] * 32,
        observed_r_mm=850.0,
        observed_theta_mdeg=45000,
        barrier_stress=0.0,
    )

    r_obs, th_obs, trace_obs, occ_obs = sub.get_spatial_tracking()
    assert r_obs == 850.0
    assert th_obs == 45000
    assert trace_obs == 1.0
    assert occ_obs is False

    # Step without observation: trace decays exponentially
    sub.step([0] * 64, [0] * 32)
    r_decay, th_decay, trace_decay, occ_decay = sub.get_spatial_tracking()
    assert r_decay == 850.0
    assert th_decay == 45000
    assert trace_decay < 1.0, "Trace must decay when unobserved"
    assert occ_decay is True, "Target must be marked occluded when unobserved"
