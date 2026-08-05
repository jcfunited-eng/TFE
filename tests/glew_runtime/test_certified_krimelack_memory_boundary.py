from __future__ import annotations

from dataclasses import replace
from fractions import Fraction as F

import pytest

from dsf_ai_service.glew_runtime.field import (
    ExactComplex,
    ExactFieldState,
    MountedFieldTopology,
    PortFiber,
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
)
from dsf_ai_service.glew_runtime.memory import (
    FIELD_H_MEM_INTEGRATION_REQUIREMENT,
    H_MEM_OPERATOR_ID,
    AllLaneNegativeSpaceProof,
    DirectedRelation,
    HMemOperatorAuthority,
    MemoryElementCalibration,
    MemoryFieldIntegrationRequired,
    MemoryMassFlowAuthority,
    MemoryValidityMask,
    RelationDrive,
    all_lane_negative_space_receipt_payload,
    build_certified_h_mem,
    create_quiescent_memory_state,
    evolve_relation_mass,
    h_mem_authority_receipt_payload,
    mass_flow_authority_receipt_payload,
    memory_element_calibration_receipt_payload,
    relation_drive_receipt_payload,
    validity_mask_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.modes import (
    ModeGrowthAuthority,
    create_empty_mode_bank,
    evaluate_mode_boundary,
    mode_growth_authority_receipt_payload,
)


PROFILE = b"certified-krimelack-memory-test-profile"
DERIVATION = b"measured local virtual memory stiffness and damping derivation"
FULL_FIELD_COMMIT = b"fresh externally lived complete full-field commit"
MASS_TOPOLOGY = b"mounted topology authority for relation-mass tests"
TEST_MODE_RECEIPTS = (
    receipt_sha256(b"test full-field mode zero"),
    receipt_sha256(b"test full-field mode one"),
)


def relation(source: int, target: int) -> DirectedRelation:
    return DirectedRelation(
        source_mode_index=source,
        target_mode_index=target,
        source_mode_receipt_sha256=TEST_MODE_RECEIPTS[source],
        target_mode_receipt_sha256=TEST_MODE_RECEIPTS[target],
    )


def registry(*payloads: bytes) -> ReceiptRegistry:
    return ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=tuple(dict.fromkeys(payloads)),
    )


def bounds(value) -> tuple[F, F]:
    return (
        F(value.lower_mantissa) * F(2) ** value.lower_exponent,
        F(value.upper_mantissa) * F(2) ** value.upper_exponent,
    )


def calibration(relation: DirectedRelation, element_id: str = "element-000"):
    payload = memory_element_calibration_receipt_payload(
        element_id=element_id,
        relation=relation,
        stiffness=F(1),
        damping=F(1),
        structural_time_unit="structural_second",
        derivation_receipt_sha256=receipt_sha256(DERIVATION),
    )
    value = MemoryElementCalibration(
        element_id=element_id,
        relation=relation,
        stiffness=F(1),
        damping=F(1),
        structural_time_unit="structural_second",
        derivation_receipt_sha256=receipt_sha256(DERIVATION),
        calibration_receipt_sha256=receipt_sha256(payload),
    )
    return value, payload


def drive(relation: DirectedRelation):
    payload = relation_drive_receipt_payload(
        relation=relation,
        joint_energy_density=F(1),
        relation_support=F(1),
        experience_origin="fresh_external",
        full_field_commit_receipt_sha256=receipt_sha256(FULL_FIELD_COMMIT),
    )
    value = RelationDrive(
        relation=relation,
        joint_energy_density=F(1),
        relation_support=F(1),
        experience_origin="fresh_external",
        full_field_commit_receipt_sha256=receipt_sha256(FULL_FIELD_COMMIT),
        drive_receipt_sha256=receipt_sha256(payload),
    )
    return value, payload


def flow_authority(
    *,
    state,
    calibration_values,
    drive_values=(),
    negative_space=None,
    authority_id="memory-flow",
    source_time_end=F(1),
):
    payload = mass_flow_authority_receipt_payload(
        authority_id=authority_id,
        prior_state_receipt_sha256=state.receipt_sha256,
        source_time_start=state.source_time,
        source_time_end=source_time_end,
        structural_time_unit="structural_second",
        calibration_receipt_sha256s=tuple(
            value.calibration_receipt_sha256 for value in calibration_values
        ),
        drive_receipt_sha256s=tuple(
            value.drive_receipt_sha256 for value in drive_values
        ),
        negative_space_receipt_sha256=(
            None
            if negative_space is None
            else negative_space.aggregate_receipt_sha256
        ),
    )
    authority = MemoryMassFlowAuthority(
        authority_id=authority_id,
        prior_state_receipt_sha256=state.receipt_sha256,
        source_time_start=state.source_time,
        source_time_end=source_time_end,
        structural_time_unit="structural_second",
        calibrations=tuple(calibration_values),
        drives=tuple(drive_values),
        negative_space_proof=negative_space,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    return authority, payload


def excite(
    relation: DirectedRelation,
    *,
    topology_authority_receipt_sha256: str = receipt_sha256(MASS_TOPOLOGY),
):
    state = create_quiescent_memory_state(
        source_time=F(0),
        structural_time_unit="structural_second",
        topology_authority_receipt_sha256=topology_authority_receipt_sha256,
        relations=(relation,),
    )
    local, local_payload = calibration(relation)
    support, support_payload = drive(relation)
    authority, authority_payload = flow_authority(
        state=state,
        calibration_values=(local,),
        drive_values=(support,),
    )
    receipts = registry(
        DERIVATION,
        FULL_FIELD_COMMIT,
        local_payload,
        support_payload,
        authority_payload,
    )
    result = evolve_relation_mass(
        state=state,
        authority=authority,
        receipt_registry=receipts,
    )
    return result, local, local_payload


def negative_space_proof(*, start: F, end: F):
    topology_payload = MASS_TOPOLOGY
    lane_payloads = (
        b"canonical L1 Negative Space proof for language",
        b"canonical L1 Negative Space proof for sight",
    )
    lanes = ("language", "sight")
    lane_digests = tuple(receipt_sha256(value) for value in lane_payloads)
    aggregate = all_lane_negative_space_receipt_payload(
        topology_authority_receipt_sha256=receipt_sha256(topology_payload),
        source_time_start=start,
        source_time_end=end,
        structural_time_unit="structural_second",
        active_lane_ids=lanes,
        lane_l1_proof_receipt_sha256s=lane_digests,
    )
    proof = AllLaneNegativeSpaceProof(
        topology_authority_receipt_sha256=receipt_sha256(topology_payload),
        source_time_start=start,
        source_time_end=end,
        structural_time_unit="structural_second",
        active_lane_ids=lanes,
        lane_l1_proof_receipt_sha256s=lane_digests,
        aggregate_receipt_sha256=receipt_sha256(aggregate),
    )
    return proof, topology_payload, lane_payloads, aggregate


def exact_field_state(topology: MountedFieldTopology, coordinate: int, source_time: F):
    amplitudes = tuple(
        ExactComplex(F(1) if index == coordinate else F(0))
        for index in range(topology.dimension)
    )
    payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256,
        source_time,
        amplitudes,
    )
    return (
        ExactFieldState(
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            source_time=source_time,
            amplitudes=amplitudes,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def growth_authority(topology, state, closed_payload: bytes, authority_id: str):
    payload = mode_growth_authority_receipt_payload(
        authority_id=authority_id,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        source_state_authority_receipt_sha256=state.authority_receipt_sha256,
        closed_experience_receipt_sha256=receipt_sha256(closed_payload),
    )
    return (
        ModeGrowthAuthority(
            authority_id=authority_id,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            source_state_authority_receipt_sha256=state.authority_receipt_sha256,
            closed_experience_receipt_sha256=receipt_sha256(closed_payload),
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def two_mode_bank():
    fibers = (PortFiber("language", "typed"),)
    topology_payload = field_topology_receipt_payload("memory-topology", fibers)
    topology = MountedFieldTopology(
        topology_id="memory-topology",
        ordered_port_fibers=fibers,
        authority_receipt_sha256=receipt_sha256(topology_payload),
    )
    first, first_payload = exact_field_state(topology, 0, F(0))
    second, second_payload = exact_field_state(topology, 1, F(1))
    first_closed = b"first independent complete closed experience"
    second_closed = b"second independent complete closed experience"
    first_growth, first_growth_payload = growth_authority(
        topology, first, first_closed, "grow-mode-0"
    )
    second_growth, second_growth_payload = growth_authority(
        topology, second, second_closed, "grow-mode-1"
    )
    receipts = registry(
        topology_payload,
        first_payload,
        second_payload,
        first_closed,
        second_closed,
        first_growth_payload,
        second_growth_payload,
    )
    bank = create_empty_mode_bank(topology, working_precision_bits=128)
    first_result = evaluate_mode_boundary(
        topology=topology,
        state=first,
        bank=bank,
        receipt_registry=receipts,
        growth_authority=first_growth,
    )
    second_result = evaluate_mode_boundary(
        topology=topology,
        state=second,
        bank=first_result.post_growth_bank,
        receipt_registry=receipts,
        growth_authority=second_growth,
    )
    return topology, topology_payload, second_result.post_growth_bank


def h_mem_for(source_mode_index: int, target_mode_index: int):
    topology, topology_payload, bank = two_mode_bank()
    bound_relation = DirectedRelation(
        source_mode_index=source_mode_index,
        target_mode_index=target_mode_index,
        source_mode_receipt_sha256=bank.modes[source_mode_index].receipt_sha256,
        target_mode_receipt_sha256=bank.modes[target_mode_index].receipt_sha256,
    )
    excited, _, _ = excite(
        bound_relation,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
    )
    state = excited.state
    mask_payload = validity_mask_receipt_payload(
        mask_id="all-currently-valid-coordinates",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        dimension=topology.dimension,
        active_coordinates=tuple(range(topology.dimension)),
    )
    mask = MemoryValidityMask(
        mask_id="all-currently-valid-coordinates",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        dimension=topology.dimension,
        active_coordinates=tuple(range(topology.dimension)),
        authority_receipt_sha256=receipt_sha256(mask_payload),
    )
    authority_payload = h_mem_authority_receipt_payload(
        operator_id=H_MEM_OPERATOR_ID,
        memory_state_receipt_sha256=state.receipt_sha256,
        mode_bank_receipt_sha256=bank.receipt_sha256,
        validity_mask_receipt_sha256=mask.authority_receipt_sha256,
    )
    authority = HMemOperatorAuthority(
        operator_id=H_MEM_OPERATOR_ID,
        memory_state_receipt_sha256=state.receipt_sha256,
        mode_bank_receipt_sha256=bank.receipt_sha256,
        validity_mask_receipt_sha256=mask.authority_receipt_sha256,
        authority_receipt_sha256=receipt_sha256(authority_payload),
    )
    receipts = registry(topology_payload, mask_payload, authority_payload)
    result = build_certified_h_mem(
        topology=topology,
        bank=bank,
        state=state,
        validity_mask=mask,
        authority=authority,
        receipt_registry=receipts,
    )
    return result


def test_clean_memory_genesis_is_one_quiescent_mass_unit():
    relations = (relation(0, 1), relation(1, 0))
    state = create_quiescent_memory_state(
        source_time=F(0),
        structural_time_unit="structural_second",
        topology_authority_receipt_sha256=receipt_sha256(MASS_TOPOLOGY),
        relations=relations,
    )

    assert state.quiescent_mass == 1
    assert state.active_masses == (0, 0)
    assert state.quiescent_mass + sum(state.active_masses, F(0)) == 1
    state.verify()


def test_fresh_full_field_support_moves_mass_without_increment_or_clamp():
    result, _, _ = excite(relation(0, 1))
    quiescent_lower, quiescent_upper = bounds(result.state.quiescent_mass)
    active_lower, active_upper = bounds(result.state.active_masses[0])

    assert F(1, 3) < quiescent_lower < quiescent_upper < F(1, 2)
    assert F(1, 2) < active_lower < active_upper < F(2, 3)
    assert result.state.exact_total_mass == 1
    assert result.state.constraint_id.endswith("memory_simplex.v1")
    assert tuple(
        (entry.row, entry.column, entry.value)
        for entry in result.receipt.generator_entries
    ) == ((0, 0, F(-1)), (1, 0, F(1)))


def test_active_mass_is_unchanged_when_negative_space_is_not_proved():
    first, local, local_payload = excite(relation(0, 1))
    authority, authority_payload = flow_authority(
        state=first.state,
        calibration_values=(local,),
        source_time_end=F(2),
        authority_id="no-decay-without-proof",
    )
    second = evolve_relation_mass(
        state=first.state,
        authority=authority,
        receipt_registry=registry(DERIVATION, local_payload, authority_payload),
    )

    assert second.receipt.generator_entries == ()
    before_lower, before_upper = bounds(first.state.active_masses[0])
    after_lower, after_upper = bounds(second.state.active_masses[0])
    assert after_lower <= before_lower <= before_upper <= after_upper


def test_proved_all_lane_negative_space_causes_natural_exponential_decay():
    first, local, local_payload = excite(relation(0, 1))
    proof, topology_payload, lane_payloads, proof_payload = negative_space_proof(
        start=F(1), end=F(2)
    )
    authority, authority_payload = flow_authority(
        state=first.state,
        calibration_values=(local,),
        negative_space=proof,
        source_time_end=F(2),
        authority_id="proved-natural-decay",
    )
    second = evolve_relation_mass(
        state=first.state,
        authority=authority,
        receipt_registry=registry(
            DERIVATION,
            local_payload,
            topology_payload,
            *lane_payloads,
            proof_payload,
            authority_payload,
        ),
    )
    before_active_lower, _ = bounds(first.state.active_masses[0])
    _, after_active_upper = bounds(second.state.active_masses[0])
    _, before_quiet_upper = bounds(first.state.quiescent_mass)
    after_quiet_lower, _ = bounds(second.state.quiescent_mass)

    assert after_active_upper < before_active_lower
    assert after_quiet_lower > before_quiet_upper
    assert tuple(
        (entry.row, entry.column, entry.value)
        for entry in second.receipt.generator_entries
    ) == ((0, 1, F(1)), (1, 1, F(-1)))
    assert second.state.exact_total_mass == 1


def test_supported_growth_cannot_coexist_with_all_lane_negative_space():
    relation_value = relation(0, 1)
    state = create_quiescent_memory_state(
        source_time=F(0),
        structural_time_unit="structural_second",
        topology_authority_receipt_sha256=receipt_sha256(MASS_TOPOLOGY),
        relations=(relation_value,),
    )
    local, local_payload = calibration(relation_value)
    support, support_payload = drive(relation_value)
    proof, topology_payload, lane_payloads, proof_payload = negative_space_proof(
        start=F(0), end=F(1)
    )
    authority, authority_payload = flow_authority(
        state=state,
        calibration_values=(local,),
        drive_values=(support,),
        negative_space=proof,
    )
    receipts = registry(
        DERIVATION,
        FULL_FIELD_COMMIT,
        local_payload,
        support_payload,
        topology_payload,
        *lane_payloads,
        proof_payload,
        authority_payload,
    )

    with pytest.raises(ReceiptError, match="cannot coexist"):
        evolve_relation_mass(
            state=state,
            authority=authority,
            receipt_registry=receipts,
        )


def test_unmounted_calibration_derivation_fails_closed():
    relation_value = relation(0, 1)
    state = create_quiescent_memory_state(
        source_time=F(0),
        structural_time_unit="structural_second",
        topology_authority_receipt_sha256=receipt_sha256(MASS_TOPOLOGY),
        relations=(relation_value,),
    )
    local, local_payload = calibration(relation_value)
    authority, authority_payload = flow_authority(
        state=state,
        calibration_values=(local,),
    )

    with pytest.raises(ReceiptError, match="derivation receipt is not mounted"):
        evolve_relation_mass(
            state=state,
            authority=authority,
            receipt_registry=registry(local_payload, authority_payload),
        )


def test_h_mem_is_hermitian_direction_distinct_and_keeps_interval_mass():
    forward = h_mem_for(0, 1)
    reverse = h_mem_for(1, 0)
    forward_real = bounds(forward.entries[0][1].real)
    reverse_real = bounds(reverse.entries[0][1].real)
    forward_imag = bounds(forward.entries[0][1].imag)
    reverse_imag = bounds(reverse.entries[0][1].imag)

    forward.verify()
    reverse.verify()
    assert forward_real == reverse_real
    assert forward_imag[0] > 0
    assert reverse_imag[1] < 0
    assert forward.entries[1][0].real == forward.entries[0][1].real
    assert bounds(forward.entries[1][0].imag) == (
        -forward_imag[1],
        -forward_imag[0],
    )
    assert forward.spectral_norm_bound == 1
    assert b"certified_interval" in forward.expression_receipt_payload
    assert b"midpoint" not in forward.expression_receipt_payload


def test_h_mem_cannot_be_smuggled_into_rational_only_field_authority():
    result = h_mem_for(0, 1)

    with pytest.raises(
        MemoryFieldIntegrationRequired,
        match="CertifiedComplexBall Hermitian entries",
    ):
        result.require_field_integration()
    assert "ExactComplex rational-only" in FIELD_H_MEM_INTEGRATION_REQUIREMENT
    assert "Midpoint selection" in FIELD_H_MEM_INTEGRATION_REQUIREMENT


def test_h_mem_receipt_tamper_fails_closed():
    result = h_mem_for(0, 1)
    forged = replace(result, expression_receipt_payload=b"forged expression")

    with pytest.raises(ReceiptError, match="not content-bound"):
        forged.verify()
