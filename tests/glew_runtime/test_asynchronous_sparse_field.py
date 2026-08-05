from dataclasses import replace
from fractions import Fraction as F

import pytest

from dsf_ai_service.glew_runtime.expressions import (
    ExpressionEvaluationStatus,
    FieldExpressionStep,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
    evaluate_closed_experience_expression,
    precision_schedule_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.field import (
    EvidenceProvenance,
    EvidenceValidity,
    EvidenceValidityState,
    ExactComplex,
    FieldEvolutionAuthority,
    MountedFieldTopology,
    PortFiber,
    PortTransportEvidence,
    RegimeFact,
    ResonanceFact,
    SourceCoefficient,
    StructuralFactState,
    SupportFloorFact,
    TransportCoordinates19,
    canonical_component_partition,
    evolve_field,
    evolution_authority_receipt_payload,
    field_topology_receipt_payload,
    source_coefficients_for_injection,
    sparse_map_inject,
    transport_evidence_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from tests.glew_runtime.test_field import (
    PHYSICAL_PROFILE_AUTHORITY,
    PROVENANCE_AUTHORITY,
    REGIME_AUTHORITY,
    RESONANCE_AUTHORITY,
    SUPPORT_AUTHORITY,
    VALIDITY_AUTHORITY,
    contains,
    exact_ball,
    exact_state,
    registry,
)


TOPOLOGY_ID = "asynchronous-two-port-field"


def _topology() -> tuple[MountedFieldTopology, bytes]:
    fibers = (
        PortFiber("sight", "photocurrent"),
        PortFiber("sound", "cochlear_release"),
    )
    payload = field_topology_receipt_payload(TOPOLOGY_ID, fibers)
    return (
        MountedFieldTopology(TOPOLOGY_ID, fibers, receipt_sha256(payload)),
        payload,
    )


def _evidence(
    *,
    lane: str,
    port: str,
    integrated_charge: F,
    source_time: F,
    source_index: int,
) -> tuple[PortTransportEvidence, bytes, bytes]:
    coordinates = TransportCoordinates19(
        integrated_charge,
        *(F(0) for _ in range(18)),
    )
    regime = RegimeFact("stable", receipt_sha256(REGIME_AUTHORITY))
    support = SupportFloorFact(
        StructuralFactState.AVAILABLE,
        F(1),
        receipt_sha256(SUPPORT_AUTHORITY),
    )
    resonance = ResonanceFact(
        StructuralFactState.AVAILABLE,
        exact_ball(),
        receipt_sha256(RESONANCE_AUTHORITY),
    )
    validity = EvidenceValidity(
        EvidenceValidityState.VALID,
        receipt_sha256(VALIDITY_AUTHORITY),
    )
    provenance = EvidenceProvenance(
        provider_id=f"{lane}.{port}.native-provider",
        source_epoch="native-epoch-1",
        source_index=source_index,
        source_timestamp=source_time,
        authority_receipt_sha256=receipt_sha256(PROVENANCE_AUTHORITY),
    )
    raw_payload = (
        f"raw:{lane}:{port}:{source_index}:"
        f"{source_time.numerator}/{source_time.denominator}"
    ).encode()
    raw = ReceiptRecord(receipt_sha256(raw_payload), raw_payload)
    evidence_id = f"{lane}.{port}.gate-{source_index}"
    payload = transport_evidence_receipt_payload(
        lane_id=lane,
        port_id=port,
        evidence_id=evidence_id,
        coordinates=coordinates,
        regime=regime,
        support_floor=support,
        resonance=resonance,
        validity=validity,
        provenance=provenance,
        raw_record_sha256=raw.digest,
    )
    evidence = PortTransportEvidence(
        lane_id=lane,
        port_id=port,
        evidence_id=evidence_id,
        coordinates=coordinates,
        regime=regime,
        support_floor=support,
        resonance=resonance,
        validity=validity,
        provenance=provenance,
        raw_record=raw,
        evidence_receipt_sha256=receipt_sha256(payload),
    )
    return evidence, raw_payload, payload


def _authority(
    *,
    topology: MountedFieldTopology,
    injection,
    start: F,
    end: F,
    authority_id: str,
) -> tuple[FieldEvolutionAuthority, bytes]:
    source = source_coefficients_for_injection(injection, end - start)
    components = canonical_component_partition(topology.dimension, ())
    payload = evolution_authority_receipt_payload(
        authority_id=authority_id,
        physical_profile_receipt_sha256=receipt_sha256(
            PHYSICAL_PROFILE_AUTHORITY
        ),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        map_injection_receipt_sha256=injection.receipt_sha256,
        source_time_start=start,
        source_time_end=end,
        source_time_unit="structural_second",
        hbar=F(1),
        hamiltonian=(),
        local_rates=(),
        source=source,
        component_partition=components,
        max_connected_component_dimension=1,
        precision_bits=256,
    )
    return (
        FieldEvolutionAuthority(
            authority_id=authority_id,
            physical_profile_receipt_sha256=receipt_sha256(
                PHYSICAL_PROFILE_AUTHORITY
            ),
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            map_injection_receipt_sha256=injection.receipt_sha256,
            source_time_start=start,
            source_time_end=end,
            source_time_unit="structural_second",
            hbar=F(1),
            hamiltonian=(),
            local_rates=(),
            source=source,
            max_connected_component_dimension=1,
            precision_bits=256,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def _registry_with_evidence(
    topology_payload: bytes,
    evidence_values: tuple[tuple[PortTransportEvidence, bytes, bytes], ...],
    *extra_payloads: bytes,
) -> ReceiptRegistry:
    evidence_payloads = tuple(
        payload
        for _, raw_payload, evidence_payload in evidence_values
        for payload in (raw_payload, evidence_payload)
    )
    return registry(topology_payload, *evidence_payloads, *extra_payloads)


def _three_event_expression():
    topology, topology_payload = _topology()
    sight_one = _evidence(
        lane="sight",
        port="photocurrent",
        integrated_charge=F(2),
        source_time=F(1),
        source_index=1,
    )
    sound_one = _evidence(
        lane="sound",
        port="cochlear_release",
        integrated_charge=F(3),
        source_time=F(3, 2),
        source_index=1,
    )
    sight_two = _evidence(
        lane="sight",
        port="photocurrent",
        integrated_charge=F(5),
        source_time=F(2),
        source_index=2,
    )
    evidence_values = (sight_one, sound_one, sight_two)
    base_registry = _registry_with_evidence(topology_payload, evidence_values)
    injections = (
        sparse_map_inject(topology, (sight_one[0],), F(1), base_registry),
        sparse_map_inject(topology, (sound_one[0],), F(3, 2), base_registry),
        sparse_map_inject(topology, (sight_two[0],), F(2), base_registry),
    )
    intervals = ((F(0), F(1)), (F(1), F(3, 2)), (F(3, 2), F(2)))
    authorities_and_payloads = tuple(
        _authority(
            topology=topology,
            injection=injection,
            start=start,
            end=end,
            authority_id=f"asynchronous-step-{index}",
        )
        for index, (injection, (start, end)) in enumerate(
            zip(injections, intervals, strict=True),
            start=1,
        )
    )
    initial, initial_payload = exact_state(
        topology,
        F(0),
        (ExactComplex(F(0)),) * topology.dimension,
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="asynchronous-expression-precision",
        maximum_precision_bits=4096,
    )
    precision = PrecisionScheduleAuthority(
        authority_id="asynchronous-expression-precision",
        maximum_precision_bits=4096,
        authority_receipt_sha256=receipt_sha256(precision_payload),
    )
    receipt_registry = _registry_with_evidence(
        topology_payload,
        evidence_values,
        *(injection.receipt_payload for injection in injections),
        *(payload for _, payload in authorities_and_payloads),
        initial_payload,
        precision_payload,
    )
    expression = create_closed_experience_expression(
        topology=topology,
        initial_state=initial,
        steps=tuple(
            FieldExpressionStep(injection, authority)
            for injection, (authority, _) in zip(
                injections,
                authorities_and_payloads,
                strict=True,
            )
        ),
        precision_authority=precision,
        receipt_registry=receipt_registry,
    )
    return (
        topology,
        evidence_values,
        injections,
        authorities_and_payloads,
        expression,
        receipt_registry,
    )


def test_unequal_native_gate_boundaries_form_one_exact_causal_expression():
    topology, _, injections, authorities, expression, receipts = (
        _three_event_expression()
    )

    result = evaluate_closed_experience_expression(
        expression,
        receipt_registry=receipts,
    )

    assert result.status is ExpressionEvaluationStatus.CERTIFIED
    assert expression.dimension == topology.dimension == 38
    assert tuple(value.source_time for value in injections) == (
        F(1),
        F(3, 2),
        F(2),
    )
    assert tuple(
        value.source for value, _ in authorities
    ) == (
        (SourceCoefficient(0, ExactComplex(F(2))),),
        (SourceCoefficient(19, ExactComplex(F(6))),),
        (SourceCoefficient(0, ExactComplex(F(10))),),
    )
    # Post-event states are (2,0), (2,3), and (7,3) in the first
    # coordinate of each native fiber.  Their exact centroid is (11/3,2).
    assert contains(result.amplitudes[0].real, F(11, 3))
    assert contains(result.amplitudes[19].real, F(2))


def test_absent_port_has_no_evidence_and_its_field_state_persists():
    topology, evidence_values, injections, authorities, _, receipts = (
        _three_event_expression()
    )
    sight_injection, sound_injection, _ = injections
    sight_authority, _ = authorities[0]
    sound_authority, _ = authorities[1]
    initial, initial_payload = exact_state(
        topology,
        F(0),
        (ExactComplex(F(0)),) * topology.dimension,
    )
    direct_receipts = _registry_with_evidence(
        field_topology_receipt_payload(
            topology.topology_id,
            topology.ordered_port_fibers,
        ),
        evidence_values,
        *(injection.receipt_payload for injection in injections),
        *(payload for _, payload in authorities),
        initial_payload,
    )

    after_sight = evolve_field(
        topology=topology,
        injection=sight_injection,
        authority=sight_authority,
        initial_state=initial,
        receipt_registry=direct_receipts,
    )
    after_sound = evolve_field(
        topology=topology,
        injection=sound_injection,
        authority=sound_authority,
        initial_state=after_sight.state,
        receipt_registry=direct_receipts,
    )

    assert sight_injection.absent_fibers == (
        PortFiber("sound", "cochlear_release"),
    )
    assert sound_injection.absent_fibers == (
        PortFiber("sight", "photocurrent"),
    )
    assert not hasattr(sight_injection, "vector")
    assert b"no_new_source_event;no_evidence" in sight_injection.receipt_payload
    assert contains(after_sight.state.amplitudes[0].real, F(2))
    assert contains(after_sight.state.amplitudes[19].real, F(0))
    assert contains(after_sound.state.amplitudes[0].real, F(2))
    assert contains(after_sound.state.amplitudes[19].real, F(3))
    assert receipts is not None


def test_sparse_injection_rejects_duplicate_reordered_and_time_mismatched_evidence():
    topology, topology_payload = _topology()
    sight = _evidence(
        lane="sight",
        port="photocurrent",
        integrated_charge=F(1),
        source_time=F(1),
        source_index=1,
    )
    sound = _evidence(
        lane="sound",
        port="cochlear_release",
        integrated_charge=F(1),
        source_time=F(1),
        source_index=1,
    )
    receipts = _registry_with_evidence(topology_payload, (sight, sound))

    with pytest.raises(ReceiptError, match="duplicate transport evidence"):
        sparse_map_inject(topology, (sight[0], sight[0]), F(1), receipts)
    with pytest.raises(ReceiptError, match="out of canonical"):
        sparse_map_inject(topology, (sound[0], sight[0]), F(1), receipts)
    with pytest.raises(ReceiptError, match="did not close at the declared"):
        sparse_map_inject(topology, (sight[0],), F(2), receipts)


def test_sparse_receipt_offset_absence_and_payload_tampering_fail_closed():
    topology, evidence_values, injections, _, _, receipts = (
        _three_event_expression()
    )
    injection = injections[0]

    with pytest.raises(ReceiptError, match="exact canonical topology complement"):
        replace(injection, absent_fibers=()).verify(topology, receipts)
    with pytest.raises(ReceiptError, match="canonical direct-sum offset"):
        replace(
            injection,
            mapped_fibers=(replace(injection.mapped_fibers[0], offset=19),),
        ).verify(topology, receipts)
    with pytest.raises(ReceiptError, match="payload is not canonical"):
        replace(injection, receipt_payload=b"forged sparse event").verify(
            topology,
            receipts,
        )
    assert evidence_values


def test_sparse_evolution_binds_event_time_and_exact_charge_over_delta():
    topology, evidence_values, injections, authorities, _, receipts = (
        _three_event_expression()
    )
    injection = injections[0]
    authority, _ = authorities[0]
    initial, initial_payload = exact_state(
        topology,
        F(0),
        (ExactComplex(F(0)),) * topology.dimension,
    )

    wrong_source = replace(
        authority,
        source=(SourceCoefficient(0, ExactComplex(F(3))),),
    )
    with pytest.raises(ReceiptError, match="integrated MapInject charge divided by delta"):
        evolve_field(
            topology=topology,
            injection=injection,
            authority=wrong_source,
            initial_state=initial,
            receipt_registry=receipts,
        )

    mismatched_time, mismatched_payload = _authority(
        topology=topology,
        injection=injection,
        start=F(0),
        end=F(2),
        authority_id="mismatched-event-boundary",
    )
    mismatch_receipts = _registry_with_evidence(
        field_topology_receipt_payload(
            topology.topology_id,
            topology.ordered_port_fibers,
        ),
        evidence_values,
        injection.receipt_payload,
        mismatched_payload,
        initial_payload,
    )
    with pytest.raises(ReceiptError, match="source time differs"):
        evolve_field(
            topology=topology,
            injection=injection,
            authority=mismatched_time,
            initial_state=initial,
            receipt_registry=mismatch_receipts,
        )


def test_expression_rejects_native_source_index_regression():
    topology, topology_payload = _topology()
    later_index_first = _evidence(
        lane="sight",
        port="photocurrent",
        integrated_charge=F(1),
        source_time=F(1),
        source_index=2,
    )
    earlier_index_later = _evidence(
        lane="sight",
        port="photocurrent",
        integrated_charge=F(1),
        source_time=F(2),
        source_index=1,
    )
    evidence_values = (later_index_first, earlier_index_later)
    base = _registry_with_evidence(topology_payload, evidence_values)
    injections = (
        sparse_map_inject(topology, (later_index_first[0],), F(1), base),
        sparse_map_inject(topology, (earlier_index_later[0],), F(2), base),
    )
    authorities = (
        _authority(
            topology=topology,
            injection=injections[0],
            start=F(0),
            end=F(1),
            authority_id="regression-step-1",
        ),
        _authority(
            topology=topology,
            injection=injections[1],
            start=F(1),
            end=F(2),
            authority_id="regression-step-2",
        ),
    )
    initial, initial_payload = exact_state(
        topology,
        F(0),
        (ExactComplex(F(0)),) * topology.dimension,
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="regression-precision",
        maximum_precision_bits=4096,
    )
    precision = PrecisionScheduleAuthority(
        "regression-precision",
        4096,
        receipt_sha256(precision_payload),
    )
    receipts = _registry_with_evidence(
        topology_payload,
        evidence_values,
        *(injection.receipt_payload for injection in injections),
        *(payload for _, payload in authorities),
        initial_payload,
        precision_payload,
    )

    with pytest.raises(ReceiptError, match="strict native causal order"):
        create_closed_experience_expression(
            topology=topology,
            initial_state=initial,
            steps=tuple(
                FieldExpressionStep(injection, authority)
                for injection, (authority, _) in zip(
                    injections,
                    authorities,
                    strict=True,
                )
            ),
            precision_authority=precision,
            receipt_registry=receipts,
        )
