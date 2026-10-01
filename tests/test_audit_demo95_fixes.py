import pytest
from guala_core import ModularSubstrate64D
from arcloom_demonstrator.substrate.modular_column_substrate import ModularColumnSubstrate


def test_signed_field_transduction_preserves_sign_at_consumer():
    """DEMO95-A1-01: Ensure +1.0 and -1.0 produce distinct signed neural and material observables at the consumer."""
    # 1. Inspect codec output
    num_pos, den_pos, sign_pos, zero_pos = ModularSubstrate64D.float_to_rational_trits(1.0)
    num_neg, den_neg, sign_neg, zero_neg = ModularSubstrate64D.float_to_rational_trits(-1.0)

    assert not zero_pos and not zero_neg
    assert sign_pos == 1 and sign_neg == -1
    assert num_pos == [1]
    assert num_neg == [-1]  # Exact signed numerator applied once

    # 2. Feed positive and negative values into two substrates
    sub_pos = ModularSubstrate64D(0.50, 0.08, 0.15)
    sub_neg = ModularSubstrate64D(0.50, 0.08, 0.15)

    sub_pos.consume_continuous_joint_field([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 1.0)
    sub_neg.consume_continuous_joint_field([-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 1.0)

    sub_pos.step([0] * 64, [0] * 32)
    sub_neg.step([0] * 64, [0] * 32)

    # 3. Assert reached neural and material state directly (excluding raw input retention bytes)
    pos_l4 = sub_pos.get_column_l4_nodes(48)
    neg_l4 = sub_neg.get_column_l4_nodes(48)
    assert pos_l4[0] == 1, f"Positive field must transduce +1 to primary column L4 node 0, got {pos_l4[0]}"
    assert neg_l4[0] == -1, f"Negative field must transduce -1 to primary column L4 node 0, got {neg_l4[0]}"

    pos_v_mem = sub_pos.material_membrane_voltage()
    neg_v_mem = sub_neg.material_membrane_voltage()
    assert pos_v_mem != neg_v_mem, "Opposite field orientations must produce distinct material membrane potentials"


def test_unmounted_high_ternary_positions_refuse_atomically():
    """DEMO95-A1-01: Values whose rational trits exceed mounted Layer 4 capacity refuse fail-closed before mutation."""
    sub = ModularSubstrate64D(0.50, 0.08, 0.15)

    # Subnormal v = 2^-200 = 6.223015277861142e-61 has 127 denominator trits (39 nonzero trits at p >= 64).
    # Discarding positions >= 64 would silently alter the rational value n/d.
    val_200 = 6.223015277861142e-61
    sub.consume_continuous_joint_field([val_200, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 1.0)

    with pytest.raises(NotImplementedError, match=r"unmounted incidence refused"):
        sub.step([0] * 64, [0] * 32)

    # Atomic state preservation: no mutation occurred upon refusal
    assert sub.get_column_l4_nodes(48)[0] == 0

    # Minimum subnormal 5e-324 (2^-1074) also has trits far exceeding 64 and must refuse
    val_submin = 5e-324
    sub.consume_continuous_joint_field([val_submin, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 1.0)
    with pytest.raises(NotImplementedError, match=r"unmounted incidence refused"):
        sub.step([0] * 64, [0] * 32)

    # 3^63 fits entirely within the 64 mounted positions (indices 0..63) without unmounted digits
    sub_63 = ModularSubstrate64D(0.50, 0.08, 0.15)
    val_63 = float(3**63)
    sub_63.consume_continuous_joint_field([val_63, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 1.0)
    sub_63.step([0] * 64, [0] * 32)
    assert sub_63.get_column_l4_nodes(48)[63] == 1, "Position 63 must mount exact power 3^63 at node 63"


def test_barrier_refusal_causally_emerges_from_contact_mechanics():
    """DEMO95-A1-02: Barrier refusal is governed strictly by contact yield stress mechanics, not software bypasses."""
    sub = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08)

    # 1. Drive substrate to positive active locomotion stride
    for _ in range(5):
        sub.step([1] * 64, [1] * 32, barrier_stress=0.0)
    assert sub.get_motor_efferent()[1] > 0.0
    assert not sub.is_barrier_refusal_active()

    # 2. Structural field presence with zero mechanical stress must NOT trigger barrier refusal
    # (Removes the artificial software bypass where zero mechanical stress reported barrier refusal)
    sub.consume_continuous_joint_field([0.5, 0.2, 0.5, 0.1, 0.2, 0.3, 0.4], s_uf=1.0)
    sub.step([1] * 64, [1] * 32, barrier_stress=0.0)
    assert not sub.is_barrier_refusal_active(), "Zero mechanical stress must never trigger barrier refusal"
    assert sub.get_motor_efferent()[1] > 0.0, "Nominal locomotion stride must continue when barrier stress is zero"

    # 3. Mechanical over-yield collision (barrier_stress = 0.85 > yield_threshold = 0.50)
    # Physical contact yields: refusal becomes active and arrests locomotion stride
    sub.step([1] * 64, [1] * 32, barrier_stress=0.85)
    assert sub.is_barrier_refusal_active(), "Over-yield barrier stress must activate physical barrier refusal"
    vocal, stride, steer, grip = sub.get_motor_efferent()
    assert stride == 0.0, f"Over-yield barrier refusal must clamp locomotion stride to 0.0, got {stride}"
