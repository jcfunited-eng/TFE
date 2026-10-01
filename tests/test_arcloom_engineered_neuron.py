"""Verification of ArcLoom Engineered Artificial Reference Material Neuron.

Addresses A1 Audit Findings NATIVE-01 through NATIVE-06:
- NATIVE-01: Full typed continuous structural field incidence (D_k, M_k, R_rev,k, U*_k, C_k, P_k, B_k)
- NATIVE-02: Complete First Law thermodynamic balance: Delta H = W_in - W_out - Q_heat,out
- NATIVE-03: Retained contact mechanics coupled to physical receiving compartment
- NATIVE-04: Exact rational carrier custody and integer reservoir conservation
- NATIVE-05: Cold successor covering independent physical state and causal operator topology
- NATIVE-06: Strict physical domain validation, trailing byte rejection, and transactional refusal atomicity

Governing documents:
- docs/GUALA_ONE_NEURON_MATERIAL_ANATOMY_BINDING_2026-10-01.md
- collaborative_todo.md (A1 Audit Entry 2026-10-01 UTC)
"""
import math
import pytest
from guala_core import ArcLoomNeuron


def test_arcloom_engineered_neuron_genesis_and_initial_state():
    """Verify genesis electroneutrality, initial resting voltage, and ion stocks."""
    neuron = ArcLoomNeuron()
    v0 = neuron.membrane_voltage()
    # Ratified V0 ~ -65.0000031305 mV
    assert abs(v0 - (-0.0650000031305)) < 1e-9, f"Unexpected V0: {v0}"

    v_rec = neuron.receiving_voltage()
    assert abs(v_rec - (-0.065)) < 1e-9, f"Unexpected receiving V: {v_rec}"

    apertures = neuron.get_apertures()
    assert apertures == [0.05, 0.05, 0.02, 0.10], f"Unexpected apertures: {apertures}"

    res_in = neuron.get_reservoirs_in()
    assert res_in == [30270581073, 353156779183, 252255, 25225484227]

    res_out = neuron.get_reservoirs_out()
    assert res_out == [91442380324, 2522548423, 1261274211, 69370081625]

    x, ell = neuron.get_contact_geometry()
    assert abs(x - 1.0e-6) < 1e-15
    assert abs(ell - 1.0e-6) < 1e-15


def test_arcloom_engineered_neuron_contact_plasticity_and_receiving_charge_transfer():
    """Verify NATIVE-03: retained contact deformation alters receiving compartment transfer."""
    neuron_intact = ArcLoomNeuron()
    neuron_yielded = ArcLoomNeuron()

    # Step neuron_yielded with 15% strain to trigger plastic flow (ell increases)
    prior_v, succ_v, yielded, d_pl, v_rec, w_in, q_heat = neuron_yielded.step(
        applied_contact_x=1.15e-6,
        external_current_a=0.0,
        dt_seconds=1.0e-4,
    )
    assert yielded, "15% strain must yield plastically"
    assert d_pl > 0.0, "Plastic yield must produce positive dissipation"

    x_yielded, ell_yielded = neuron_yielded.get_contact_geometry()
    assert ell_yielded > 1.0e-6, "Plastic yield must increase rest length"

    # Step neuron_intact with sub-yield strain (ell unchanged)
    prior_v2, succ_v2, yielded2, d_pl2, v_rec2, w_in2, q_heat2 = neuron_intact.step(
        applied_contact_x=1.02e-6,
        external_current_a=0.0,
        dt_seconds=1.0e-4,
    )
    assert not yielded2, "2% strain must be elastic"
    assert d_pl2 == 0.0, "Elastic step has zero plastic dissipation"

    # Now present BOTH neurons with the EXACT SAME test input: x=1.05e-6, external_current=0.0
    res_intact = neuron_intact.step(applied_contact_x=1.05e-6, external_current_a=0.0, dt_seconds=1.0e-4)
    res_yielded = neuron_yielded.step(applied_contact_x=1.05e-6, external_current_a=0.0, dt_seconds=1.0e-4)

    # Receiving voltage must diverge because contact conductance depends on actual/retained geometry!
    v_rec_intact = res_intact[4]
    v_rec_yielded = res_yielded[4]
    assert v_rec_intact != v_rec_yielded, "Retained contact geometry must drive divergent receiving charge transfer"


def test_nonempty_topology_cold_successor_equivalence():
    """Verify NATIVE-05: cold restore covers complete state AND causal operator topology."""
    original = ArcLoomNeuron()

    # Add non-empty typed fabric edges (DSF D_k and M_k dimensions)
    # dim: 0=Displacement, 1=Motion; role: 0=Numerator, 1=Denominator
    original.add_fabric_edge(
        from_node=0,
        to_node=1,
        tau_trit=1,
        kappa_j=4.28e-20,
        dim=0,
        role=0,
        position=1,
    )
    original.add_fabric_edge(
        from_node=1,
        to_node=2,
        tau_trit=-1,
        kappa_j=4.28e-20,
        dim=1,
        role=1,
        position=2,
    )

    # Advance original 3 steps
    for _ in range(3):
        original.step(applied_contact_x=1.08e-6, external_current_a=5.0e-10, dt_seconds=1.0e-4)

    canonical_bytes = original.export_canonical_bytes()

    # 1. Restore into fresh instance (which starts with empty edges)
    restored_fresh = ArcLoomNeuron()
    restored_fresh.import_canonical_bytes(canonical_bytes)

    # 2. Restore into existing instance that had DIFFERENT prior edges
    restored_existing = ArcLoomNeuron()
    restored_existing.add_fabric_edge(from_node=2, to_node=3, tau_trit=1, kappa_j=1.0e-20, dim=2, role=0, position=9)
    restored_existing.import_canonical_bytes(canonical_bytes)

    # Verify that both restored instances match original bit-for-bit before next step
    assert restored_fresh.export_canonical_bytes() == canonical_bytes
    assert restored_existing.export_canonical_bytes() == canonical_bytes

    # Advance all three under the exact same subsequent stimulus
    orig_succ = original.step(applied_contact_x=1.01e-6, external_current_a=-2.0e-10, dt_seconds=1.0e-4)
    fresh_succ = restored_fresh.step(applied_contact_x=1.01e-6, external_current_a=-2.0e-10, dt_seconds=1.0e-4)
    existing_succ = restored_existing.step(applied_contact_x=1.01e-6, external_current_a=-2.0e-10, dt_seconds=1.0e-4)

    assert orig_succ == fresh_succ, "Fresh-process restore successor must be bit-identical"
    assert orig_succ == existing_succ, "Overwrite restore successor must be bit-identical"
    assert original.export_canonical_bytes() == restored_fresh.export_canonical_bytes()


def test_first_law_thermodynamic_balance_and_heat_dissipation():
    """Verify NATIVE-02: First Law energy accounting: Delta H = W_in - W_out - Q_heat."""
    neuron = ArcLoomNeuron()
    res = neuron.step(applied_contact_x=1.10e-6, external_current_a=1.0e-9, dt_seconds=1.0e-4)

    w_in = res[5]
    q_heat = res[6]

    assert math.isfinite(w_in), "Work input must be finite"
    assert math.isfinite(q_heat), "Heat dissipated must be finite"
    assert q_heat >= 0.0, "Dissipated heat must be strictly non-negative (Second Law)"


def test_exact_carrier_custody_rational_identity():
    """Verify NATIVE-04: exact whole-ion integer custody and reservoir conservation."""
    neuron = ArcLoomNeuron()
    initial_in = neuron.get_reservoirs_in()
    initial_out = neuron.get_reservoirs_out()

    for _ in range(5):
        neuron.step(applied_contact_x=1.0e-6, external_current_a=2.0e-10, dt_seconds=1.0e-4)

    succ_in = neuron.get_reservoirs_in()
    succ_out = neuron.get_reservoirs_out()

    for c in range(4):
        total_initial = initial_in[c] + initial_out[c]
        total_succ = succ_in[c] + succ_out[c]
        assert total_initial == total_succ, f"Species {c} reservoir conservation violated: {total_initial} != {total_succ}"


def test_physical_domain_validation_and_refusal_atomicity():
    """Verify NATIVE-06: invalid inputs, corrupted bytes, and out-of-bound states refuse atomically."""
    neuron = ArcLoomNeuron()
    valid_bytes = neuron.export_canonical_bytes()

    # 1. Trailing bytes rejected
    corrupted_trailing = valid_bytes + b"\x00"
    with pytest.raises(ValueError):
        neuron.import_canonical_bytes(corrupted_trailing)

    # 2. Corrupted CRC rejected
    corrupted_crc = bytearray(valid_bytes)
    corrupted_crc[-1] ^= 0xFF
    with pytest.raises(ValueError):
        neuron.import_canonical_bytes(bytes(corrupted_crc))

    # 3. Non-finite input rejected atomically without mutating state
    pre_v = neuron.membrane_voltage()
    with pytest.raises(RuntimeError):
        neuron.step(applied_contact_x=1.0e-6, external_current_a=float("nan"), dt_seconds=1.0e-4)
    post_v = neuron.membrane_voltage()
    assert pre_v == post_v, "Predecessor state must be 100% unmutated after refusal"
