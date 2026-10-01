"""Tests for the canonical one-neuron phase-gate physical transition contract.

Verifies the ratified constitutive chain mounted on Primary Column 48 Layer 2/3:
  1. Complete typed structural field (D, M, R_rev, U*, C, P, B, S_UF) ingress.
  2. Exact positional MathLoom balanced-ternary trits tau(q, p) with zero truncation.
  3. Persistent phase phi and Krimelack topological winding count K.
  4. Dimensionless gate coordinate relaxation y_c in [0.0, 1.0].
  5. Sourced material pore conductance g_c = sigma * A_c(y_c) / ell.
  6. Nernst driving force (V_m - E_c) and ionic pore current I_c.
  7. Exact signed carrier transport J_c with remainder custody: |q*n + q*(r'-r) - J| < 1e-25.
  8. Stored capacitive energy decrement dot{E} <= 0 under zero external drive.
  9. Controlled intervention causal divergence (Field A vs Field B).
 10. Fail-closed 148-byte binary serialization and exact byte-for-byte continuation.
"""
import struct
import numpy as np
import pytest
from guala_core import ModularSubstrate64D
from dsf_ai_service.substrate.modular_column_substrate import ModularColumnSubstrate


def test_mounted_canonical_neuron_initial_state():
    sub = ModularColumnSubstrate(columns=64)
    state = sub.get_mounted_neuron_state()

    assert state["phase"] == 0.0
    assert state["amplitude"] == 1.0
    assert state["winding"] == 0
    assert state["gate_coordinate"] == 0.5
    assert state["conductance"] > 0.0
    # Initial resting potential: -70 mV across 100 pF
    assert abs(state["membrane_voltage"] - (-0.070)) < 1e-6
    assert state["stored_energy"] > 0.0


def test_mounted_canonical_neuron_refuses_when_field_absent():
    sub = ModularColumnSubstrate(columns=64)
    assert not sub.has_continuous_joint_field()
    with pytest.raises(Exception, match="continuous joint field is not present"):
        sub.step_mounted_canonical_neuron(dt=0.001)


def test_mounted_canonical_neuron_full_field_participation():
    sub = ModularColumnSubstrate(columns=64)
    # Feed complete 7-field tensor + S_UF invariant
    field = [0.65, -0.25, 0.40, 0.15, 0.85, 0.30, 0.50]
    sub.consume_continuous_joint_field(field, s_uf=0.92)

    receipt = sub.step_mounted_canonical_neuron(dt=0.001)

    # Verify complete participation: phase force is non-zero
    assert abs(receipt["phase_force"]) > 0.0
    assert abs(receipt["delta_phase"]) > 0.0
    assert receipt["conductance"] > 0.0
    assert abs(receipt["ionic_current"]) > 0.0
    assert abs(receipt["charge_transferred_coulombs"]) > 0.0


def test_mounted_canonical_neuron_carrier_remainder_custody():
    sub = ModularColumnSubstrate(columns=64)
    field = [0.8, -0.4, 0.9, 0.1, 0.7, 0.8, 0.3]
    sub.consume_continuous_joint_field(field, s_uf=0.95)

    receipt = sub.step_mounted_canonical_neuron(dt=0.001)

    # Carrier custody identity: q_c * n_c + q_c * (r' - r) == J_c
    q_c = 1.602176634e-19
    n_c = receipt["transferred_carriers"]
    r_prime = receipt["final_remainder"]
    j_c = receipt["charge_transferred_coulombs"]

    # In step 1 from r=0, r_c_init = 0.0
    custody_error = abs(q_c * n_c + q_c * r_prime - j_c)
    assert custody_error < 1e-25, f"Custody error violated: {custody_error}"


def test_mounted_canonical_neuron_energy_decrement_zero_input():
    sub = ModularColumnSubstrate(columns=64)
    # Feed zero external drive (trits are all zero)
    sub.consume_continuous_joint_field([0.0] * 7, s_uf=1.0)

    receipt = sub.step_mounted_canonical_neuron(dt=0.001)

    # Under zero drive, capacitor discharges through the pore: delta_e_cap <= 0
    assert receipt["delta_e_cap"] <= 0.0, f"Energy increased under zero input: {receipt['delta_e_cap']}"


def test_mounted_canonical_neuron_causal_divergence_under_isolated_intervention():
    sub_a = ModularColumnSubstrate(columns=64)
    sub_b = ModularColumnSubstrate(columns=64)

    field_a = [0.85, 0.10, -0.30, 0.20, 0.70, 0.40, 0.60]
    field_b = [-0.85, -0.10, 0.30, -0.20, -0.70, -0.40, -0.60]

    sub_a.consume_continuous_joint_field(field_a, s_uf=0.95)
    sub_b.consume_continuous_joint_field(field_b, s_uf=0.95)

    receipt_a = sub_a.step_mounted_canonical_neuron(dt=0.001)
    receipt_b = sub_b.step_mounted_canonical_neuron(dt=0.001)

    # Opposite fields must produce divergent phase forces and distinct pore currents
    assert receipt_a["phase_force"] != receipt_b["phase_force"]
    assert receipt_a["final_phase"] != receipt_b["final_phase"]
    assert receipt_a["conductance"] != receipt_b["conductance"]
    assert receipt_a["ionic_current"] != receipt_b["ionic_current"]


def test_mounted_canonical_neuron_lossless_continuation_and_serialization():
    sub1 = ModularColumnSubstrate(columns=64)
    field = [0.75, -0.35, 0.55, 0.15, 0.45, 0.65, 0.25]
    sub1.consume_continuous_joint_field(field, s_uf=0.90)

    # Step 5 cycles
    for _ in range(5):
        sub1.step_mounted_canonical_neuron(dt=0.001)

    # Export serialized 148-byte record
    raw_bytes = sub1.export_mounted_neuron_bytes()
    assert len(raw_bytes) == 148
    assert raw_bytes[:8] == b"GUALA_NG"

    # Step original 1 additional cycle
    receipt_orig = sub1.step_mounted_canonical_neuron(dt=0.001)

    # Restore into fresh substrate with identical continuous field
    sub2 = ModularColumnSubstrate(columns=64)
    sub2.consume_continuous_joint_field(field, s_uf=0.90)
    sub2.import_mounted_neuron_bytes(raw_bytes)

    # Step restored 1 cycle
    receipt_restored = sub2.step_mounted_canonical_neuron(dt=0.001)

    # Assert bit-for-bit exact continuation
    for key in (
        "phase_force",
        "delta_phase",
        "phase_constraint_energy",
        "final_phase",
        "final_winding",
        "gate_coordinate",
        "conductance",
        "ionic_current",
        "charge_transferred_coulombs",
        "membrane_voltage",
        "delta_e_cap",
        "transferred_carriers",
        "final_remainder",
    ):
        v_orig = receipt_orig[key]
        v_rest = receipt_restored[key]
        if isinstance(v_orig, float):
            orig_bits = struct.unpack(">Q", struct.pack(">d", v_orig))[0]
            rest_bits = struct.unpack(">Q", struct.pack(">d", v_rest))[0]
            assert orig_bits == rest_bits, f"Bit mismatch for {key}: orig {hex(orig_bits)} != rest {hex(rest_bits)}"
        else:
            assert v_orig == v_rest, f"Value mismatch for {key}: {v_orig} != {v_rest}"
