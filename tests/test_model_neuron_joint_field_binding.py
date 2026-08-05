from fractions import Fraction

from tools.isolated_vtvr_side_kernel_v2 import (
    JointFieldInput,
    run_side_kernel,
)
from tools.model_neuron_joint_field_binding import (
    ExactTernaryRational,
    bind_neuron_perspective,
    reconstruct_cohesion,
)


def _experience(*, changed_third_vertex: bool = False):
    third = Fraction(4 if changed_third_vertex else 3)
    return run_side_kernel(JointFieldInput.create(
        vertex_ids=("sight:left", "sound:left", "body:hand"),
        groups=((0, 1, 2),),
        times=(Fraction(0), Fraction(1, 3), Fraction(2, 3)),
        vectors=(
            (Fraction(1), Fraction(2), Fraction(3)),
            (Fraction(2), Fraction(1), third),
            (Fraction(-1), Fraction(3), Fraction(2)),
        ),
    ))


def test_exact_ternary_rational_round_trips_without_quantization():
    values = (
        Fraction(0),
        Fraction(1, 2),
        Fraction(-17, 29),
        Fraction(2**53 - 1, 2**52),
    )
    for value in values:
        encoded = ExactTernaryRational.encode(value)
        assert encoded.decode() == value
        assert encoded.trit_count > 0


def test_one_neuron_retains_local_fields_and_every_incident_edge():
    experience = _experience()
    perspective = bind_neuron_perspective(
        experience,
        neuron_id="neuron-0",
        vertex_index=0,
        frame_index=1,
    )
    assert perspective.complete_field_receipt_sha256 == (
        experience.L4.authority_receipt_sha256
    )
    assert perspective.D_k.decode() == experience.L4.D_k[1][0]
    assert perspective.M_k.decode() == experience.L4.M_k[1][0]
    assert perspective.R_rev_k == experience.L4.R_rev_k[1][0]
    assert perspective.U_star_k == experience.L4.U_star_k[1][0]
    assert perspective.P_k.decode() == experience.L4.P_k[1][0]
    assert perspective.B_k.decode() == experience.L4.B_k[1][0]
    assert tuple(edge.decode() for edge in perspective.C_k) == tuple(
        edge
        for edge in experience.L4.C_k[1]
        if 0 in (edge.left, edge.right)
    )
    assert perspective.arithmetic_trit_count > 0


def test_one_neuron_binding_is_byte_deterministic():
    experience = _experience()
    first = bind_neuron_perspective(
        experience,
        neuron_id="neuron-0",
        vertex_index=0,
        frame_index=1,
    )
    second = bind_neuron_perspective(
        experience,
        neuron_id="neuron-0",
        vertex_index=0,
        frame_index=1,
    )
    assert first == second


def test_relational_change_reaches_the_one_neuron_perspective():
    baseline = bind_neuron_perspective(
        _experience(),
        neuron_id="neuron-0",
        vertex_index=0,
        frame_index=1,
    )
    changed = bind_neuron_perspective(
        _experience(changed_third_vertex=True),
        neuron_id="neuron-0",
        vertex_index=0,
        frame_index=1,
    )
    assert baseline.authority_receipt_sha256 != (
        changed.authority_receipt_sha256
    )
    assert baseline.C_k != changed.C_k


def test_three_neurons_reconstruct_complete_cohesion_without_flattening():
    experience = _experience()
    perspectives = tuple(
        bind_neuron_perspective(
            experience,
            neuron_id=f"neuron-{index}",
            vertex_index=index,
            frame_index=1,
        )
        for index in range(3)
    )
    assert reconstruct_cohesion(perspectives) == experience.L4.C_k[1]


def test_three_neuron_closure_rejects_a_missing_perspective():
    experience = _experience()
    perspectives = tuple(
        bind_neuron_perspective(
            experience,
            neuron_id=f"neuron-{index}",
            vertex_index=index,
            frame_index=1,
        )
        for index in range(2)
    )
    try:
        reconstruct_cohesion(perspectives)
    except ValueError as error:
        assert "close the joint field" in str(error)
    else:
        raise AssertionError("incomplete joint field was accepted")
