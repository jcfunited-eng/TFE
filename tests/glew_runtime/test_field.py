import sys
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.glew_runtime.certified_backend import (
    CertifiedBackendUnavailable,
    CertifiedBall,
)
from dsf_ai_service.glew_runtime.field import (
    FIBER_DIMENSION,
    TRANSPORT_COORDINATE_ORDER,
    EvidenceProvenance,
    EvidenceValidity,
    EvidenceValidityState,
    CertifiedComplexBall,
    ExactComplex,
    ExactFieldState,
    FieldEvolutionAuthority,
    HamiltonianEntry,
    LocalRate,
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
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
    field_conformance,
    map_inject,
    transport_evidence_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)


PROFILE = b"glew-field-profile-v1"
REGIME_AUTHORITY = b"exact categorical Reg_k provider"
SUPPORT_AUTHORITY = b"exact S_UF provider"
RESONANCE_AUTHORITY = b"certified R_UF provider"
VALIDITY_AUTHORITY = b"typed validity provider"
PROVENANCE_AUTHORITY = b"exact source provenance provider"
PHYSICAL_PROFILE_AUTHORITY = (
    b"measured H hbar local-rate and structural-time dimensional authority"
)
COMMON_AUTHORITIES = (
    REGIME_AUTHORITY,
    SUPPORT_AUTHORITY,
    RESONANCE_AUTHORITY,
    VALIDITY_AUTHORITY,
    PROVENANCE_AUTHORITY,
    PHYSICAL_PROFILE_AUTHORITY,
)


def registry(*payloads: bytes) -> ReceiptRegistry:
    unique = tuple(dict.fromkeys((*COMMON_AUTHORITIES, *payloads)))
    return ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=unique,
    )


def exact_ball(value: F = F(1)) -> CertifiedBall:
    return CertifiedBall(
        lower_mantissa=value.numerator,
        lower_exponent=-(value.denominator.bit_length() - 1),
        upper_mantissa=value.numerator,
        upper_exponent=-(value.denominator.bit_length() - 1),
        working_precision_bits=256,
    )


def evidence(
    lane: str,
    port: str,
    values: tuple[F, ...],
    *,
    validity_state: EvidenceValidityState = EvidenceValidityState.VALID,
) -> tuple[PortTransportEvidence, bytes, bytes]:
    coordinates = TransportCoordinates19(*values)
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
        validity_state,
        receipt_sha256(VALIDITY_AUTHORITY),
        None if validity_state is EvidenceValidityState.VALID else "native_fault",
    )
    provenance = EvidenceProvenance(
        provider_id=f"{lane}.{port}.provider",
        source_epoch="epoch-1",
        source_index=0,
        source_timestamp=F(5),
        authority_receipt_sha256=receipt_sha256(PROVENANCE_AUTHORITY),
    )
    raw_payload = f"raw:{lane}:{port}".encode()
    raw = ReceiptRecord(receipt_sha256(raw_payload), raw_payload)
    receipt_payload = transport_evidence_receipt_payload(
        lane_id=lane,
        port_id=port,
        evidence_id=f"{lane}.{port}.gate-1",
        coordinates=coordinates,
        regime=regime,
        support_floor=support,
        resonance=resonance,
        validity=validity,
        provenance=provenance,
        raw_record_sha256=raw.digest,
    )
    record = PortTransportEvidence(
        lane_id=lane,
        port_id=port,
        evidence_id=f"{lane}.{port}.gate-1",
        coordinates=coordinates,
        regime=regime,
        support_floor=support,
        resonance=resonance,
        validity=validity,
        provenance=provenance,
        raw_record=raw,
        evidence_receipt_sha256=receipt_sha256(receipt_payload),
    )
    return record, raw_payload, receipt_payload


def topology(*fibers: PortFiber) -> tuple[MountedFieldTopology, bytes]:
    payload = field_topology_receipt_payload("mounted-field-1", fibers)
    return (
        MountedFieldTopology(
            topology_id="mounted-field-1",
            ordered_port_fibers=fibers,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def make_injection(
    fibers: tuple[PortFiber, ...],
    records: tuple[tuple[PortTransportEvidence, bytes, bytes], ...],
):
    mounted, topology_payload = topology(*fibers)
    payloads = [topology_payload]
    for _, raw_payload, evidence_payload in records:
        payloads.extend((raw_payload, evidence_payload))
    receipts = registry(*payloads)
    injection = map_inject(
        mounted,
        tuple(record for record, _, _ in records),
        receipts,
    )
    return mounted, injection, tuple(payloads)


def source_for(values: tuple[F, ...], delta: F) -> tuple[SourceCoefficient, ...]:
    return tuple(
        SourceCoefficient(index, ExactComplex(value / delta))
        for index, value in enumerate(values)
        if value != 0
    )


def evolution_authority(
    mounted: MountedFieldTopology,
    injection,
    *,
    hamiltonian: tuple[HamiltonianEntry, ...] = (),
    local_rates: tuple[LocalRate, ...] = (),
    source_time_start: F = F(5),
    source_time_end: F = F(6),
    max_component: int = 19,
):
    source = source_for(injection.vector, source_time_end - source_time_start)
    components = canonical_component_partition(mounted.dimension, hamiltonian)
    payload = evolution_authority_receipt_payload(
        authority_id="field-step-1",
        physical_profile_receipt_sha256=receipt_sha256(PHYSICAL_PROFILE_AUTHORITY),
        topology_authority_receipt_sha256=mounted.authority_receipt_sha256,
        map_injection_receipt_sha256=injection.receipt_sha256,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        source_time_unit="structural_second",
        hbar=F(1),
        hamiltonian=hamiltonian,
        local_rates=local_rates,
        source=source,
        component_partition=components,
        max_connected_component_dimension=max_component,
        precision_bits=256,
    )
    return (
        FieldEvolutionAuthority(
            authority_id="field-step-1",
            physical_profile_receipt_sha256=receipt_sha256(
                PHYSICAL_PROFILE_AUTHORITY
            ),
            topology_authority_receipt_sha256=mounted.authority_receipt_sha256,
            map_injection_receipt_sha256=injection.receipt_sha256,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            source_time_unit="structural_second",
            hbar=F(1),
            hamiltonian=hamiltonian,
            local_rates=local_rates,
            source=source,
            max_connected_component_dimension=max_component,
            precision_bits=256,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def ball_bounds(ball: CertifiedBall) -> tuple[F, F]:
    return (
        F(ball.lower_mantissa) * F(2) ** ball.lower_exponent,
        F(ball.upper_mantissa) * F(2) ** ball.upper_exponent,
    )


def contains(ball: CertifiedBall, expected: F) -> bool:
    lower, upper = ball_bounds(ball)
    return lower <= expected <= upper


def exact_state(
    mounted: MountedFieldTopology,
    source_time: F,
    amplitudes: tuple[ExactComplex, ...],
) -> tuple[ExactFieldState, bytes]:
    payload = exact_field_state_receipt_payload(
        mounted.authority_receipt_sha256,
        source_time,
        amplitudes,
    )
    return (
        ExactFieldState(
            mounted.authority_receipt_sha256,
            source_time,
            amplitudes,
            receipt_sha256(payload),
        ),
        payload,
    )


def test_empty_genesis_topology_is_zero_dimensional_and_unavailable():
    mounted, payload = topology()
    assert mounted.dimension == 0
    assert mounted.available is False
    with pytest.raises(ReceiptError, match="dimension zero"):
        map_inject(mounted, (), registry(payload))


def test_dimension_is_exact_sum_of_ordered_port_fibers():
    one, _ = topology(PortFiber("sight", "ribbon_release"))
    three, _ = topology(
        PortFiber("sight", "photocurrent"),
        PortFiber("sight", "ribbon_release"),
        PortFiber("touch", "dynamic_afferent"),
    )
    assert FIBER_DIMENSION == 19
    assert len(TRANSPORT_COORDINATE_ORDER) == 19
    assert one.dimension == 19
    assert three.dimension == 57


def test_two_ports_remain_independent_and_direct_inclusion_is_exact():
    first_values = tuple(F(index, 7) for index in range(1, 20))
    second_values = tuple(F(-index, 11) for index in range(1, 20))
    records = (
        evidence("sight", "photocurrent", first_values),
        evidence("sight", "ribbon_release", second_values),
    )
    mounted, injection, _ = make_injection(
        (
            PortFiber("sight", "photocurrent"),
            PortFiber("sight", "ribbon_release"),
        ),
        records,
    )

    assert mounted.dimension == 38
    assert injection.vector == first_values + second_values
    assert injection.mapped_fibers[0].offset == 0
    assert injection.mapped_fibers[1].offset == 19
    assert injection.mapped_fibers[0].evidence.raw_record.payload == records[0][1]
    assert injection.mapped_fibers[1].evidence.raw_record.payload == records[1][1]


def test_invalid_mask_does_not_shrink_or_zero_the_declared_fiber():
    valid_values = tuple(F(index) for index in range(19))
    invalid_values = tuple(F(index + 100) for index in range(19))
    records = (
        evidence("touch", "dynamic", valid_values),
        evidence(
            "touch",
            "static_merkel",
            invalid_values,
            validity_state=EvidenceValidityState.INVALID,
        ),
    )
    mounted, topology_payload = topology(
        PortFiber("touch", "dynamic"), PortFiber("touch", "static_merkel")
    )
    payloads = [topology_payload]
    for _, raw_payload, evidence_payload in records:
        payloads.extend((raw_payload, evidence_payload))
    assert mounted.dimension == 38
    with pytest.raises(ReceiptError, match="preserves its topology fiber"):
        map_inject(
            mounted,
            tuple(record for record, _, _ in records),
            registry(*payloads),
        )
    assert mounted.dimension == 38


def test_zero_generator_affine_integration_is_certified_exact_identity_source():
    values = (F(3, 2),) + (F(0),) * 18
    record = evidence("language", "typed", values)
    mounted, injection, payloads = make_injection(
        (PortFiber("language", "typed"),), (record,)
    )
    authority, authority_payload = evolution_authority(
        mounted,
        injection,
        source_time_start=F(5),
        source_time_end=F(7),
    )
    initial, initial_payload = exact_state(
        mounted,
        F(5),
        (ExactComplex(F(0)),) * mounted.dimension,
    )
    result = evolve_field(
        topology=mounted,
        injection=injection,
        authority=authority,
        initial_state=initial,
        receipt_registry=registry(*payloads, authority_payload, initial_payload),
    )

    assert contains(result.state.amplitudes[0].real, F(3, 2))
    assert contains(result.state.amplitudes[0].imag, F(0))
    for amplitude in result.state.amplitudes[1:]:
        assert contains(amplitude.real, F(0))
        assert contains(amplitude.imag, F(0))
    assert result.receipt.component_partition == tuple((index,) for index in range(19))
    assert result.receipt.source_time_end - result.receipt.source_time_start == F(2)
    assert result.receipt.result_state_receipt_sha256 == result.state.receipt_sha256


def test_hermitian_unforced_evolution_certifies_conserved_norm():
    zero_record = evidence("sound", "ribbon_release", (F(0),) * 19)
    mounted, injection, payloads = make_injection(
        (PortFiber("sound", "ribbon_release"),), (zero_record,)
    )
    hamiltonian = (HamiltonianEntry(0, 0, ExactComplex(F(1))),)
    authority, authority_payload = evolution_authority(
        mounted,
        injection,
        hamiltonian=hamiltonian,
    )
    initial = (ExactComplex(F(1)),) + (ExactComplex(F(0)),) * 18
    initial_state, initial_payload = exact_state(mounted, F(5), initial)
    result = evolve_field(
        topology=mounted,
        injection=injection,
        authority=authority,
        initial_state=initial_state,
        receipt_registry=registry(*payloads, authority_payload, initial_payload),
    )
    assert contains(result.receipt.norm_before_squared, F(1))
    assert contains(result.receipt.norm_after_squared, F(1))


def test_nonhermitian_hamiltonian_is_rejected_before_backend_execution():
    record = evidence("smell", "release", (F(0),) * 19)
    mounted, injection, payloads = make_injection(
        (PortFiber("smell", "release"),), (record,)
    )
    hamiltonian = (HamiltonianEntry(0, 1, ExactComplex(F(1))),)
    authority, authority_payload = evolution_authority(
        mounted,
        injection,
        hamiltonian=hamiltonian,
    )
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(0)),) * 19
    )
    with pytest.raises(ReceiptError, match="Hermitian"):
        evolve_field(
            topology=mounted,
            injection=injection,
            authority=authority,
            initial_state=initial,
            receipt_registry=registry(*payloads, authority_payload, initial_payload),
        )


def test_receipt_tamper_fails_closed():
    values = (F(1),) + (F(0),) * 18
    record = evidence("taste", "atp_release", values)
    mounted, injection, payloads = make_injection(
        (PortFiber("taste", "atp_release"),), (record,)
    )
    authority, authority_payload = evolution_authority(mounted, injection)
    tampered = replace(authority, local_rates=(LocalRate(0, F(1), F(0)),))
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(0)),) * 19
    )
    with pytest.raises(ReceiptError, match="differ from mounted authority"):
        evolve_field(
            topology=mounted,
            injection=injection,
            authority=tampered,
            initial_state=initial,
            receipt_registry=registry(*payloads, authority_payload, initial_payload),
        )


def test_unmounted_physical_profile_receipt_fails_closed():
    record = evidence("taste", "atp_release", (F(0),) * 19)
    mounted, injection, payloads = make_injection(
        (PortFiber("taste", "atp_release"),), (record,)
    )
    authority, authority_payload = evolution_authority(mounted, injection)
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(0)),) * 19
    )
    receipts_without_physical_profile = ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=(
            REGIME_AUTHORITY,
            SUPPORT_AUTHORITY,
            RESONANCE_AUTHORITY,
            VALIDITY_AUTHORITY,
            PROVENANCE_AUTHORITY,
            *payloads,
            authority_payload,
            initial_payload,
        ),
    )
    with pytest.raises(ReceiptError, match="physical profile receipt is not mounted"):
        evolve_field(
            topology=mounted,
            injection=injection,
            authority=authority,
            initial_state=initial,
            receipt_registry=receipts_without_physical_profile,
        )


def test_changed_physical_profile_receipt_fails_authority_binding():
    record = evidence("smell", "release", (F(0),) * 19)
    mounted, injection, payloads = make_injection(
        (PortFiber("smell", "release"),), (record,)
    )
    authority, authority_payload = evolution_authority(mounted, injection)
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(0)),) * 19
    )
    changed = replace(
        authority,
        physical_profile_receipt_sha256=receipt_sha256(REGIME_AUTHORITY),
    )
    with pytest.raises(ReceiptError, match="differ from mounted authority"):
        evolve_field(
            topology=mounted,
            injection=injection,
            authority=changed,
            initial_state=initial,
            receipt_registry=registry(*payloads, authority_payload, initial_payload),
        )


def test_connected_component_resource_admission_fails_before_solve():
    record = evidence("sight", "release", (F(0),) * 19)
    mounted, injection, payloads = make_injection(
        (PortFiber("sight", "release"),), (record,)
    )
    hamiltonian = (
        HamiltonianEntry(0, 1, ExactComplex(F(1))),
        HamiltonianEntry(1, 0, ExactComplex(F(1))),
    )
    authority, authority_payload = evolution_authority(
        mounted,
        injection,
        hamiltonian=hamiltonian,
        max_component=1,
    )
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(0)),) * 19
    )
    with pytest.raises(ReceiptError, match="resource authority"):
        evolve_field(
            topology=mounted,
            injection=injection,
            authority=authority,
            initial_state=initial,
            receipt_registry=registry(*payloads, authority_payload, initial_payload),
        )


def test_backend_mismatch_fails_closed(monkeypatch):
    record = evidence("language", "typed", (F(0),) * 19)
    mounted, injection, payloads = make_injection(
        (PortFiber("language", "typed"),), (record,)
    )
    authority, authority_payload = evolution_authority(mounted, injection)
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(0)),) * 19
    )

    def fail_backend():
        raise CertifiedBackendUnavailable("backend mismatch fixture")

    monkeypatch.setattr(
        "dsf_ai_service.glew_runtime.field.load_pinned_flint", fail_backend
    )
    with pytest.raises(CertifiedBackendUnavailable, match="backend mismatch"):
        evolve_field(
            topology=mounted,
            injection=injection,
            authority=authority,
            initial_state=initial,
            receipt_registry=registry(*payloads, authority_payload, initial_payload),
        )


def test_forged_public_map_injection_is_reverified_before_evolution():
    record = evidence("language", "typed", (F(1),) + (F(0),) * 18)
    mounted, injection, payloads = make_injection(
        (PortFiber("language", "typed"),), (record,)
    )
    authority, authority_payload = evolution_authority(mounted, injection)
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(0)),) * 19
    )
    forged = replace(injection, vector=(F(9),) + injection.vector[1:])
    with pytest.raises(ReceiptError, match="exact topology identity inclusion"):
        evolve_field(
            topology=mounted,
            injection=forged,
            authority=authority,
            initial_state=initial,
            receipt_registry=registry(*payloads, authority_payload, initial_payload),
        )


def test_forged_exact_initial_state_is_rejected_before_evolution():
    record = evidence("language", "typed", (F(0),) * 19)
    mounted, injection, payloads = make_injection(
        (PortFiber("language", "typed"),), (record,)
    )
    authority, authority_payload = evolution_authority(mounted, injection)
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(0)),) * 19
    )
    forged = replace(
        initial,
        amplitudes=(ExactComplex(F(7)),) + initial.amplitudes[1:],
    )
    with pytest.raises(ReceiptError, match="differs from its mounted authority"):
        evolve_field(
            topology=mounted,
            injection=injection,
            authority=authority,
            initial_state=forged,
            receipt_registry=registry(*payloads, authority_payload, initial_payload),
        )


def test_forged_certified_initial_state_is_rejected_before_next_evolution():
    record = evidence("sound", "release", (F(0),) * 19)
    mounted, injection, payloads = make_injection(
        (PortFiber("sound", "release"),), (record,)
    )
    first_authority, first_authority_payload = evolution_authority(mounted, injection)
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(1)),) + (ExactComplex(F(0)),) * 18
    )
    first = evolve_field(
        topology=mounted,
        injection=injection,
        authority=first_authority,
        initial_state=initial,
        receipt_registry=registry(
            *payloads, first_authority_payload, initial_payload
        ),
    )
    second_authority, second_authority_payload = evolution_authority(
        mounted,
        injection,
        source_time_start=F(6),
        source_time_end=F(7),
    )
    forged = replace(
        first.state,
        amplitudes=(
            CertifiedComplexBall(exact_ball(F(7)), exact_ball(F(0))),
            *first.state.amplitudes[1:],
        ),
    )
    with pytest.raises(ReceiptError, match="differs from its canonical receipt"):
        evolve_field(
            topology=mounted,
            injection=injection,
            authority=second_authority,
            initial_state=forged,
            receipt_registry=registry(
                *payloads,
                first_authority_payload,
                second_authority_payload,
                initial_payload,
            ),
        )


def test_field_conformance_is_deterministic_and_explicitly_not_a_live_mount():
    first = field_conformance()
    second = field_conformance()
    assert first == second
    assert first["status"] == "operator_conformant_no_live_mounted_topology"
    assert first["live_mounted_topology"] is False
    assert first["empty_genesis"]["dimension"] == 0
    assert first["empty_genesis"]["available"] is False
    assert first["one_port_vector"]["dimension"] == 19
    assert first["one_port_vector"]["expected_integrated_charge"] == "3/2"
