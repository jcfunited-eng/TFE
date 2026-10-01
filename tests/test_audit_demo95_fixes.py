import pytest
from guala_core import ModularSubstrate64D
from arcloom_demonstrator.substrate.modular_column_substrate import ModularColumnSubstrate

def test_signed_field_transduction_preserves_sign_at_consumer():
    """DEMO95-A1-01: Ensure +1.0 and -1.0 do not produce identical neural inputs."""
    # 1. Inspect codec output
    num_pos, den_pos, sign_pos, zero_pos = ModularSubstrate64D.float_to_rational_trits(1.0)
    num_neg, den_neg, sign_neg, zero_neg = ModularSubstrate64D.float_to_rational_trits(-1.0)

    assert not zero_pos and not zero_neg
    assert sign_pos == 1 and sign_neg == -1
    assert num_pos == [1]
    assert num_neg == [-1]  # Already negated in mathloom

    # 2. Feed positive and negative values into two substrates
    sub_pos = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08)
    sub_neg = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08)

    # Use D_k = +1.0 vs -1.0 (with safe S_UF = 1.0, R_rev = 0.0)
    sub_pos.consume_continuous_joint_field([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], s_uf=1.0)
    sub_neg.consume_continuous_joint_field([-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], s_uf=1.0)

    # Step both
    y_pos, s_pos = sub_pos.step([0] * 64, [1] * 32)
    y_neg, s_neg = sub_neg.step([0] * 64, [1] * 32)

    bytes_pos = sub_pos.export_sparse_bytes(version=4)
    bytes_neg = sub_neg.export_sparse_bytes(version=4)

    # In the buggy implementation, +1 and -1 both yielded the exact same +1 afferent,
    # making bytes_pos and bytes_neg identical!
    assert bytes_pos != bytes_neg, "+1.0 and -1.0 must produce distinct substrate states"


def test_high_ternary_positions_are_not_modulo_folded():
    """DEMO95-A1-01: Ensure high ternary positions p >= 64 do not fold into p % 64 slots."""
    sub_low = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08)
    sub_high = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08)

    # Position 0: 3^0 = 1.0
    # Position 64: 3^64
    val_low = 1.0
    val_high = float(3**64)

    sub_low.consume_continuous_joint_field([val_low, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], s_uf=1.0)
    sub_high.consume_continuous_joint_field([val_high, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], s_uf=1.0)

    sub_low.step([0] * 64, [1] * 32)
    sub_high.step([0] * 64, [1] * 32)

    bytes_low = sub_low.export_sparse_bytes(version=4)
    bytes_high = sub_high.export_sparse_bytes(version=4)

    # Under modulo-folding (p % 64), 3^64 would fold into node 0 (64 % 64 == 0),
    # colliding with 3^0. With distinct positional assignment without folding,
    # node 0 in sub_high does not receive the trit of 3^64.
    assert bytes_low != bytes_high, "High ternary power 3^64 must not modulo-fold into node 0"


def test_field_refusal_kill_switch_interlock():
    """DEMO95-A1-02: S_UF <= 0 or R_rev > 0 locks refusal_active and clamps stride to 0.0."""
    sub = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08)

    # First, stimulate substrate to verify that normal stride is positive
    for _ in range(5):
        sub.step([1] * 64, [1] * 32, barrier_stress=0.0)
    eff = sub.get_motor_efferent()
    assert eff[1] > 0.0, f"Normal active substrate must produce positive stride, got {eff[1]}"
    assert not sub.is_barrier_refusal_active()

    # Case A: R_rev > 0 (structural reversal kill switch)
    sub.consume_continuous_joint_field([0.5, 0.2, 0.5, 0.1, 0.2, 0.3, 0.4], s_uf=1.0)
    sub.step([1] * 64, [1] * 32, barrier_stress=0.0)
    assert sub.is_barrier_refusal_active(), "R_rev > 0 must trigger refusal even with barrier_stress=0"
    vocal, stride, steer, grip = sub.get_motor_efferent()
    assert stride == 0.0, f"Refusal must clamp locomotion stride to 0.0, got {stride}"

    # Case B: S_UF <= 0 (viability gate kill switch)
    sub2 = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08)
    for _ in range(5):
        sub2.step([1] * 64, [1] * 32, barrier_stress=0.0)
    assert sub2.get_motor_efferent()[1] > 0.0

    sub2.consume_continuous_joint_field([0.5, 0.2, 0.0, 0.1, 0.2, 0.3, 0.4], s_uf=-0.5)
    sub2.step([1] * 64, [1] * 32, barrier_stress=0.0)
    assert sub2.is_barrier_refusal_active(), "S_UF <= 0 must trigger refusal even with barrier_stress=0"
    vocal2, stride2, steer2, grip2 = sub2.get_motor_efferent()
    assert stride2 == 0.0, f"Refusal must clamp locomotion stride to 0.0, got {stride2}"

    # Case C: Nominal field (S_UF > 0, R_rev <= 0, barrier_stress=0)
    sub3 = ModularColumnSubstrate(columns=64, yield_threshold=0.50, plastic_rate=0.08)
    for _ in range(5):
        sub3.step([1] * 64, [1] * 32, barrier_stress=0.0)

    sub3.consume_continuous_joint_field([0.5, 0.2, 0.0, 0.1, 0.2, 0.3, 0.4], s_uf=1.0)
    sub3.step([1] * 64, [1] * 32, barrier_stress=0.0)
    assert not sub3.is_barrier_refusal_active(), "Nominal field must NOT trigger refusal"
    assert sub3.get_motor_efferent()[1] > 0.0, "Nominal field must permit locomotion stride"
