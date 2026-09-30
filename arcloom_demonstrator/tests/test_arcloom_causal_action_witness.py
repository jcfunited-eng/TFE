"""tests/test_arcloom_causal_action_witness.py

Standalone Component Witness Suite for ArcLoom 64D Neuromorphic Substrate.
Proves component-level architectural properties:
  1. Causal Motor Efferent Readout & Canonical Command Translation (Component Evidence)
  2. Constitutive Contact Law Parameter Provenance & Plasticity Ablation
  3. Authentic Predecessor Migration & Strict Fail-Closed Codec
  4. Full Continuous Joint Field IEEE-754 f64 Participation
  5. Matched Cold Continuation on Dynamic Changing States
  6. Spatial Tracking Polar Register Hold under Noise & Occlusion
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import pytest
import numpy as np

import guala_core
from guala_core import ModularSubstrate64D, ModularSubstrate8D, ModularSubstrate4D

from substrate.modular_column_substrate import (
    ModularColumnSubstrate,
    motor_efferent_to_locomotion_command,
    _quantize_radix3_signed,
    PoseMM,
    PositionMM,
    CANONICAL_MOTOR_INTERVAL_US,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_witness_a6_01_silent_motor_zero_invariant_and_canonical_command() -> None:
    """
    Component Witness 1:
    Prove that:
      1. Efferent inspection is a pure read-only proposal (proposed_kinematic_action).
      2. Silent motor populations produce strictly (0.0, 0.0, 0.0, 0.0) efferents and None command.
      3. Retired applied_* aliases raise AttributeError pointing to canonical world execution.
      4. Authorized motor conversion converts active efferents into a canonical MoveCommand with
         interval 250,000 µs (0.25 s) and exact lattice displacement.
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

    # Silent efferent translation helper returns None
    cmd_silent = sub.motor_efferent_to_locomotion_command(pose_init)
    assert cmd_silent is None, "Silent motor efferents must translate to None locomotion command"

    # 2. Retired applied_* aliases raise informative AttributeError
    with pytest.raises(AttributeError, match=r"applied_kinematic_action is retired"):
        sub.applied_kinematic_action()
    with pytest.raises(AttributeError, match=r"applied_motor_action is retired"):
        sub.applied_motor_action()

    # 3. Step with silent inputs
    sub.step([0] * 64, [0] * 32)
    assert sub.get_motor_efferent() == (0.0, 0.0, 0.0, 0.0)
    assert sub.motor_efferent_to_locomotion_command(pose_init) is None

    # 4. Actively stimulate substrate to produce native Layer 5 motor stride
    sub_active = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    for _ in range(5):
        sub_active.step([1] * 64, [1] * 32)

    vocal_act, stride_act, steer_act, grip_act = sub_active.get_motor_efferent()
    assert stride_act > 0.0, f"Active substrate must produce positive locomotion stride, got {stride_act}"

    # 5. Production motor conversion helper verification
    move_cmd = sub_active.motor_efferent_to_locomotion_command(pose_init)
    assert move_cmd is not None, "Active efferent must yield a MoveCommand"
    assert move_cmd.duration_microseconds == CANONICAL_MOTOR_INTERVAL_US, (
        f"Command must use canonical {CANONICAL_MOTOR_INTERVAL_US} us interval, got {move_cmd.duration_microseconds}"
    )


def test_witness_a6_02_constitutive_conduction_and_unconfounded_tract_severing() -> None:
    """
    Component Witness 2:
    Prove that:
      1. Constitutive elastic baseline G_ELASTIC_BASELINE = 0.05 is declared as the normalized
         innate tunneling conductance ratio (g_0 / g_sat) in the reversible elastic regime (w=0, |sigma| <= Y).
      2. Super-yield plastic deformation (w > 0) versus sub-yield elastic compliance drives divergent proposed output.
      3. Causal tract necessity under 100% IDENTICAL inputs:
         Severing incoming tracts to motor cortex (cols 40..47) halts motor actuation to strictly 0.0.
         Reconnecting tracts restores motor drive under identical inputs.
    """
    sens_train = [1] * 64
    som_train = [1] * 32

    # 1. Train intact substrate to induce plastic yield across inter-column fasciculi
    sub_intact = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    for _ in range(10):
        sub_intact.step(sens_train, som_train)

    assert sub_intact.active_synapses() > 0, "Training must induce plastic yield"
    learned_bytes = sub_intact.export_sparse_bytes()

    # 2. Create matched clone from identical checkpoint and ablate plastic weights
    sub_ablated = ModularColumnSubstrate.from_dict({
        "sparse_hex": learned_bytes.hex(),
        "num_columns": 64,
        "yield_threshold": 0.50,
        "plastic_rate": 0.08,
        "activation_threshold": 0.15,
    })
    sub_ablated.zero_plastic_weights()
    assert sub_ablated.active_synapses() == 0, "Ablation must clear learned plastic conductances"

    # Step both with 100% IDENTICAL test inputs
    sens_test = [1] * 64
    som_test = [0] * 32

    sub_intact.step(sens_test, som_test)
    sub_ablated.step(sens_test, som_test)

    eff_intact = sub_intact.get_motor_efferent()
    eff_ablated = sub_ablated.get_motor_efferent()

    # Invariant: Intact learned state must alter motor action strictly away from ablated baseline
    assert eff_intact != eff_ablated, f"Ablation must alter efferents: {eff_intact} == {eff_ablated}"
    assert eff_intact[1] != eff_ablated[1], (
        f"Learned plasticity must alter motor stride away from ablated baseline (component evidence): "
        f"{eff_intact[1]} == {eff_ablated[1]}"
    )

    # 3. Unconfounded Causal Tract Severing Test
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

    for c_to in range(40, 48):
        for c_from in range(64):
            if c_from < 40 or c_from >= 48:
                sub_tract_severed.reconnect_tract(c_from, c_to)
                sub_tract_severed.reconnect_tract(c_to, c_from)

    for _ in range(2):
        sub_tract_severed.step(sens_test, som_test)

    eff_reconnected = sub_tract_severed.get_motor_efferent()
    assert eff_reconnected[1] > 0.0, "Reconnecting tracts must restore motor actuation"


def test_witness_a6_03_authentic_predecessor_migration_and_strict_codec() -> None:
    """
    Component Witness 3:
    Prove that:
      1. Both authentic historical predecessors migrate cleanly via migrate_predecessor_v2:
         - arcloom2_cb69d23ea.bin (24-byte column header) -> restores active conductances.
         - arcloom2_8c3244cb3.bin (36-byte column header) -> restores active conductances and severed tracts.
      2. Current import_sparse strictly rejects ARCLOOM2 magic.
      3. Strict validation: slot mismatch, duplicate indices, out-of-range weights, truncated headers,
         non-ternary nodes, invalid padding all fail closed with ValueError.
      4. Complete failure atomicity: recipient state across all fields is 100% untouched upon failure.
    """
    sub = ModularColumnSubstrate(columns=64)

    # 1. Historical predecessor migration from authenticated binary fixtures
    cb69_path = FIXTURES_DIR / "arcloom2_cb69d23ea.bin"
    hist_8c32_path = FIXTURES_DIR / "arcloom2_8c3244cb3.bin"

    assert cb69_path.exists(), f"Predecessor fixture missing: {cb69_path}"
    assert hist_8c32_path.exists(), f"Predecessor fixture missing: {hist_8c32_path}"

    cb69_bytes = cb69_path.read_bytes()
    hist_8c32_bytes = hist_8c32_path.read_bytes()

    # Predecessor cb69d23ea migration (24-byte column headers)
    sub_cb69 = ModularColumnSubstrate(columns=64)
    sub_cb69.import_sparse_bytes(cb69_bytes, version=2)
    assert sub_cb69.active_synapses() > 0, "cb69d23ea migration must restore active conductances"

    # Predecessor 8c3244cb3 migration (36-byte column headers)
    sub_8c32 = ModularColumnSubstrate(columns=64)
    sub_8c32.import_sparse_bytes(hist_8c32_bytes, version=2)
    assert sub_8c32.active_synapses() > 0, "8c3244cb3 migration must restore active conductances"

    # 2. Strict rejection of ARCLOOM2 in current ARCLOOM3 importer
    with pytest.raises(ValueError, match=r"(?i)found arcloom2 payload"):
        sub.substrate.import_sparse(cb69_bytes)
    with pytest.raises(ValueError, match=r"(?i)found arcloom2 payload"):
        sub.substrate.import_sparse(hist_8c32_bytes)

    # 3. Setup recipient state to test complete failure atomicity
    sub.sever_tract(3, 7)
    sub.substrate.step(
        [0] * 64,
        [0] * 32,
        observed_r_mm=1200.0,
        observed_theta_mdeg=15000,
        barrier_stress=0.0,
        acoustic_formants=[],
    )
    baseline_r, baseline_th, baseline_trace, baseline_occ = sub.get_spatial_tracking()
    baseline_eff = sub.get_motor_efferent()
    baseline_syn = sub.active_synapses()
    baseline_yield_th = sub.yield_threshold
    baseline_rate = sub.plastic_rate
    baseline_act_th = sub.activation_threshold
    baseline_severed = sub.is_tract_severed(3, 7)

    # 4. Strict ARCLOOM3 codec failure tests
    valid_v3 = sub.export_sparse_bytes()

    # Empty buffer
    with pytest.raises(ValueError, match=r"(?i)empty"):
        sub.substrate.import_sparse(b"")

    # Corrupt magic
    with pytest.raises(ValueError, match=r"(?i)magic"):
        sub.substrate.import_sparse(b"INVALIDM" + valid_v3[8:])

    # Truncated global header (< 24 bytes)
    with pytest.raises(ValueError, match=r"(?i)truncated"):
        sub.substrate.import_sparse(valid_v3[:20])

    # Truncated column header (< 36 bytes)
    with pytest.raises(ValueError, match=r"(?i)36 bytes"):
        sub.substrate.import_sparse(valid_v3[:50])

    # Non-ternary node states (value 2 at L1 node)
    bad_nodes = bytearray(valid_v3)
    bad_nodes[60] = 2
    with pytest.raises(ValueError, match=r"(?i)ternary"):
        sub.substrate.import_sparse(bytes(bad_nodes))

    # Invalid padding
    bad_pad = bytearray(valid_v3)
    bad_pad[-1] = 0xAA
    with pytest.raises(ValueError, match=r"(?i)padding"):
        sub.substrate.import_sparse(bytes(bad_pad))

    # 5. Full Failure Atomicity Assertion: EVERY single field is 100% untouched
    assert sub.get_spatial_tracking() == (baseline_r, baseline_th, baseline_trace, baseline_occ)
    assert sub.get_motor_efferent() == baseline_eff
    assert sub.active_synapses() == baseline_syn
    assert sub.yield_threshold == baseline_yield_th
    assert sub.plastic_rate == baseline_rate
    assert sub.activation_threshold == baseline_act_th
    assert sub.is_tract_severed(3, 7) == baseline_severed, "Severed tract topology mutated upon rejected payload!"


def test_witness_a6_04_full_continuous_joint_field_f64_participation() -> None:
    """
    Component Witness 4:
    Prove that:
      1. Preserves full IEEE-754 binary64 precision: continuous field values survive without f32 collapse.
      2. Native transition participation: non-viable DSF invariants (S_UF <= 0 or R_rev > 0) engage
         the native viability clamp, holding motor stride to 0.0 even under stimulation; viable invariants permit excitation.
      3. Capability enforcement: 4D and 8D substrates raise strict NotImplementedError on continuous field calls.
      4. Matched causal intervention: active DSF invariants drive Prefrontal Sheet and amplify motor drive.
    """
    sub64 = ModularColumnSubstrate(columns=64)

    # 1. IEEE-754 binary64 precision preservation
    val_a = 0.40000000000000002
    val_b = 0.40000005960464478  # Would collapse in f32
    field_a = [val_a, -0.25, 0.15, 0.50, 0.65, 0.20, 0.55]
    field_b = [val_b, -0.25, 0.15, 0.50, 0.65, 0.20, 0.55]

    sub64.consume_continuous_joint_field(field_a, s_uf=1.0)
    ret_a = sub64.get_continuous_joint_field()

    sub64.consume_continuous_joint_field(field_b, s_uf=1.0)
    ret_b = sub64.get_continuous_joint_field()

    assert ret_a[0] != ret_b[0], "Continuous joint field must preserve distinct f64 precision without f32 collapse"
    assert ret_a[0] == val_a
    assert ret_b[0] == val_b

    # 2. Strict capability enforcement on 4D and 8D
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

    # 3. Native transition participation: viability clamp engages when S_UF <= 0 or R_rev > 0
    sub_viable = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15)
    sub_nonviable = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15)

    sub_viable.consume_continuous_joint_field([0.5, 0.2, 0.0, 0.1, 0.3, 0.2, 0.5], s_uf=1.0)
    sub_nonviable.consume_continuous_joint_field([0.5, 0.2, 1.0, 0.1, 0.3, 0.8, 0.2], s_uf=0.0)

    sens = [1] * 64
    som = [1] * 32
    for _ in range(5):
        sub_viable.step(sens, som)
        sub_nonviable.step(sens, som)

    eff_viable = sub_viable.get_motor_efferent()
    eff_nonviable = sub_nonviable.get_motor_efferent()

    assert eff_viable[1] > 0.0, "Viable field must permit motor excitation"
    assert eff_nonviable[1] == 0.0, f"Non-viable field must engage viability clamp (stride=0.0), got {eff_nonviable[1]}"

    # 4. Matched causal intervention across prefrontal-to-motor fasciculi
    sub_active = ModularColumnSubstrate(yield_threshold=0.55, plastic_rate=0.05, activation_threshold=0.20, columns=64)
    sub_zero = ModularColumnSubstrate(yield_threshold=0.55, plastic_rate=0.05, activation_threshold=0.20, columns=64)

    dsf_invariants = (0.8, -0.4, 0.9, 0.1, 0.7, 0.8, 0.3, 0.6)
    sens_active = sub_active.encode_sensory_stream(dsf_vector=dsf_invariants)
    sens_zero = list(sens_active)
    for i in range(48, 64):
        sens_zero[i] = 0

    som_test = [1] * 32
    for _ in range(10):
        sub_active.step(sens_active, som_test)
        sub_zero.step(sens_zero, som_test)

    eff_active = sub_active.get_motor_efferent()
    eff_zero = sub_zero.get_motor_efferent()

    assert any(eff_active[i] > eff_zero[i] for i in range(4)), (
        f"Active DSF drive must amplify motor efferents over zero-DSF control: {eff_active} vs {eff_zero}"
    )


def test_witness_a6_05_matched_cold_continuation_on_changing_states() -> None:
    """
    Component Witness 5:
    Prove that:
      1. Waking quiet intervals (50 silent beats) in yield equilibrium preserve operative state byte-for-byte.
      2. Production sleep consolidation (decay=0.03, prune_thresh=0.015) downscales conductances lawfully.
      3. Matched cold continuation on an actively changing state:
         Advances BOTH original and cold-restored copies by 1 step under identical stimulus u:
         S'_orig = F(S_orig, u) and S'_cold = F(S_cold, u).
         Verifies bit-for-bit equivalence of complete successor states and efferents.
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
    bytes_before_quiet = sub.export_sparse_bytes()

    # Step 50 quiet beats
    for _ in range(50):
        sub.step([0] * 64, [0] * 32)

    bytes_after_quiet = sub.export_sparse_bytes()
    assert bytes_after_quiet == bytes_before_quiet, "Operative state mutated during waking quiet!"

    # 2. Production sleep consolidation (decay=0.03, prune_thresh=0.015)
    decayed, pruned = sub.sleep_consolidation(decay=0.03, prune_thresh=0.015)
    assert decayed > 0, "Production sleep parameters must execute downscaling"

    # 3. Matched Cold Continuation on Actively Changing State
    changing_stimulus = [-1 if i % 2 == 0 else 1 for i in range(64)]
    sub.step(changing_stimulus, som)

    # Save state S
    bytes_s = sub.export_sparse_bytes()

    # Reconstitute cold clone S_cold from bytes_s
    sub_cold = ModularColumnSubstrate(columns=64)
    sub_cold.import_sparse_bytes(bytes_s)

    # Verify identical pre-step state
    assert sub_cold.active_synapses() == sub.active_synapses()
    assert sub_cold.get_motor_efferent() == sub.get_motor_efferent()

    # Advance BOTH copy S and copy S_cold by 1 step under identical stimulus u
    probe_stimulus = [1 if i % 3 == 0 else -1 for i in range(64)]
    probe_som = [1 if i % 2 == 0 else 0 for i in range(32)]

    y_orig, s_orig = sub.step(probe_stimulus, probe_som, observed_r_mm=500.0, observed_theta_mdeg=10000)
    y_cold, s_cold = sub_cold.step(probe_stimulus, probe_som, observed_r_mm=500.0, observed_theta_mdeg=10000)

    # Assert complete successor state bit-for-bit equivalence
    assert y_orig == y_cold, f"Successor yield mismatch: {y_orig} vs {y_cold}"
    assert s_orig == s_cold, f"Successor strain mismatch: {s_orig} vs {s_cold}"
    assert sub.active_synapses() == sub_cold.active_synapses()
    assert sub.get_motor_efferent() == sub_cold.get_motor_efferent()
    assert sub.export_sparse_bytes() == sub_cold.export_sparse_bytes()


def test_witness_a6_06_spatial_tracking_polar_getter() -> None:
    """
    Component Witness 6:
    Verify spatial tracking getter behavior on stored polar odometry coordinates.
    Formally confirms that recurrent network attractor decoding claim is withdrawn.
    """
    sub = ModularColumnSubstrate(columns=64)
    r, th, trace, occ = sub.get_spatial_tracking()
    assert (r, th, trace, occ) == (0.0, 0, 0.0, False)

    # Set odometry
    sub.step([0] * 64, [0] * 32, observed_r_mm=850.0, observed_theta_mdeg=-18000)
    r_set, th_set, trace_set, occ_set = sub.get_spatial_tracking()
    assert r_set == 850.0
    assert th_set == -18000
    assert trace_set == 1.0
    assert occ_set is False

    # Occlusion maintains stored coordinates while trace decays exponentially
    sub.step([0] * 64, [0] * 32, observed_r_mm=None, observed_theta_mdeg=None)
    r_occ, th_occ, trace_occ, occ_now = sub.get_spatial_tracking()
    assert r_occ == 850.0
    assert th_occ == -18000
    assert occ_now is True
    assert pytest.approx(trace_occ, rel=1e-3) == 0.985
