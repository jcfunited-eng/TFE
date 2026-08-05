"""Exact origin-bound full-port R_event conformance."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.commit import EventSupportState
from dsf_ai_service.glew_runtime.event_support import (
    EventSupportEvaluationStatus,
    MemoryEnergyAuthority,
    evaluate_event_support,
    exact_port_gram_geometry,
    memory_energy_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.experience_origin import (
    ExperienceOriginAuthority,
    ExperienceOriginKind,
    experience_origin_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.expressions import (
    FieldExpressionStep,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
    precision_schedule_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.field import (
    ExactComplex,
    PortFiber,
    PortTransportEvidence,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from tests.glew_runtime.test_field import (
    COMMON_AUTHORITIES,
    PROFILE,
    evidence,
    evolution_authority,
    exact_state,
    make_injection,
    registry,
)


def _evidence_tuple(lane: str, port: str, axis: int):
    values = [Fraction(0)] * 19
    values[axis] = Fraction(1)
    return evidence(lane, port, tuple(values))


def _record(lane: str, port: str, axis: int) -> PortTransportEvidence:
    return _evidence_tuple(lane, port, axis)[0]


def _extend(receipts: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    mounted = {record.digest: record.payload for record in receipts.records}
    for payload in payloads:
        mounted[receipt_sha256(payload)] = payload
    profile = receipts.resolve(receipts.profile_binding_sha256, "test profile")
    return ReceiptRegistry.from_payloads(
        profile_payload=profile,
        receipt_payloads=tuple(
            payload
            for digest, payload in mounted.items()
            if digest != receipts.profile_binding_sha256
        ),
    )


def _restart(receipts: ReceiptRegistry) -> ReceiptRegistry:
    profile = receipts.resolve(receipts.profile_binding_sha256, "test profile")
    return ReceiptRegistry.from_payloads(
        profile_payload=profile,
        receipt_payloads=tuple(
            record.payload
            for record in receipts.records
            if record.digest != receipts.profile_binding_sha256
        ),
    )


def _origin(
    *,
    kind: ExperienceOriginKind,
    topology_receipt: str,
    experience_receipt: str,
    receipts: ReceiptRegistry,
    name: str,
) -> tuple[ExperienceOriginAuthority, ReceiptRegistry]:
    source = f"origin-source:{name}".encode()
    payload = experience_origin_authority_receipt_payload(
        origin_id=name,
        kind=kind,
        profile_binding_sha256=receipts.profile_binding_sha256,
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        source_authority_receipt_sha256=receipt_sha256(source),
    )
    origin = ExperienceOriginAuthority(
        name,
        kind,
        receipts.profile_binding_sha256,
        topology_receipt,
        experience_receipt,
        receipt_sha256(source),
        receipt_sha256(payload),
    )
    return origin, _extend(receipts, source, payload)


def test_exact_gram_geometry_preserves_independent_ports() -> None:
    values = tuple(
        sorted(
            (
                _record("sight", "one", 0),
                _record("sight", "two", 1),
                _record("sound", "one", 2),
                _record("touch", "one", 3),
            ),
            key=lambda value: value.key,
        )
    )
    assert exact_port_gram_geometry(values) == 1
    dependent = (*values[:-1], _record("touch", "one", 2))
    assert exact_port_gram_geometry(dependent) == 0


def _experience():
    fibers = (
        PortFiber("language", "typed"),
        PortFiber("sight", "retina"),
        PortFiber("sound", "cochlea"),
        PortFiber("touch", "skin"),
        PortFiber("smell", "receptor"),
    )
    records = tuple(
        _evidence_tuple(fiber.lane_id, fiber.port_id, index)
        for index, fiber in enumerate(fibers)
    )
    topology, injection, injection_payloads = make_injection(fibers, records)
    authority, authority_payload = evolution_authority(
        topology,
        injection,
        max_component=topology.dimension,
    )
    initial, initial_payload = exact_state(
        topology,
        Fraction(5),
        (ExactComplex(Fraction(0)),) * topology.dimension,
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="event-support-precision",
        maximum_precision_bits=4096,
    )
    precision = PrecisionScheduleAuthority(
        "event-support-precision",
        4096,
        receipt_sha256(precision_payload),
    )
    derivation = b"event-support-memory-energy-derivation"
    energy_payload = memory_energy_authority_receipt_payload(
        authority_id="memory-element-energy",
        energy_unit_id="mounted-energy-unit",
        exact_memory_energy=Fraction(1),
        derivation_receipt_sha256=receipt_sha256(derivation),
        physical_profile_receipt_sha256=(
            authority.physical_profile_receipt_sha256
        ),
    )
    energy = MemoryEnergyAuthority(
        "memory-element-energy",
        "mounted-energy-unit",
        Fraction(1),
        receipt_sha256(derivation),
        authority.physical_profile_receipt_sha256,
        receipt_sha256(energy_payload),
    )
    receipts = registry(
        *injection_payloads,
        authority_payload,
        initial_payload,
        precision_payload,
        derivation,
        energy_payload,
    )
    expression = create_closed_experience_expression(
        topology=topology,
        initial_state=initial,
        steps=(FieldExpressionStep(injection, authority),),
        precision_authority=precision,
        receipt_registry=receipts,
    )
    receipts = registry(
        *tuple(
            record.payload
            for record in receipts.records
            if record.payload not in {*COMMON_AUTHORITIES, PROFILE}
        ),
        expression.receipt_payload,
    )
    return topology, expression, energy, receipts


def test_positive_event_support_has_no_positive_threshold() -> None:
    topology, expression, energy, receipts = _experience()
    experience_receipt = receipt_sha256(b"experience")
    origin, receipts = _origin(
        kind=ExperienceOriginKind.FRESH_EXTERNAL,
        topology_receipt=topology.authority_receipt_sha256,
        experience_receipt=experience_receipt,
        receipts=receipts,
        name="fresh-external-event",
    )
    result = evaluate_event_support(
        authority_id="R-event",
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=experience_receipt,
        expression=expression,
        memory_energy=energy,
        receipt_registry=receipts,
    )

    assert result.status is EventSupportEvaluationStatus.RESOLVED
    assert result.authority.state is EventSupportState.POSITIVE
    assert result.exact_r_event is not None and result.exact_r_event > 0
    assert result.intervals[0].exact_r_geometry == 1
    assert (
        result.intervals[0].exact_fresh_source_energy
        == result.intervals[0].exact_source_energy
    )


def test_missing_energy_is_typed_unknown() -> None:
    topology, expression, _energy, receipts = _experience()
    experience_receipt = receipt_sha256(b"experience")
    origin, receipts = _origin(
        kind=ExperienceOriginKind.FRESH_EXTERNAL,
        topology_receipt=topology.authority_receipt_sha256,
        experience_receipt=experience_receipt,
        receipts=receipts,
        name="missing-energy-event",
    )
    result = evaluate_event_support(
        authority_id="R-event",
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=experience_receipt,
        expression=expression,
        memory_energy=None,
        receipt_registry=receipts,
    )

    assert result.status is EventSupportEvaluationStatus.UNKNOWN
    assert result.authority.state is EventSupportState.UNKNOWN
    assert result.exact_r_event is None


def test_recall_keeps_sensory_geometry_but_has_exact_zero_fresh_energy_after_restart() -> None:
    topology, expression, _energy, receipts = _experience()
    experience_receipt = receipt_sha256(b"remembered-experience")
    origin, receipts = _origin(
        kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
        topology_receipt=topology.authority_receipt_sha256,
        experience_receipt=experience_receipt,
        receipts=receipts,
        name="self-generated-recall",
    )
    result = evaluate_event_support(
        authority_id="recall-R-event",
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=experience_receipt,
        expression=expression,
        memory_energy=None,
        receipt_registry=receipts,
    )

    interval = result.intervals[0]
    assert result.status is EventSupportEvaluationStatus.RESOLVED
    assert result.authority.state is EventSupportState.ZERO
    assert result.exact_r_event == Fraction(0)
    assert interval.exact_r_geometry == Fraction(1)
    assert interval.exact_source_energy > 0
    assert interval.exact_fresh_source_energy == Fraction(0)
    assert interval.exact_p_joint == Fraction(0)
    assert interval.exact_interval_support == Fraction(0)
    assert len(interval.current_port_evidence_receipt_sha256s) == 4

    mounted = _extend(receipts, *result.generated_receipt_payloads)
    restarted = _restart(mounted)
    result.verify(
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=experience_receipt,
        expression=expression,
        receipt_registry=restarted,
    )


def test_recall_fresh_energy_tamper_fails_closed() -> None:
    topology, expression, _energy, receipts = _experience()
    experience_receipt = receipt_sha256(b"tampered-recall-experience")
    origin, receipts = _origin(
        kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
        topology_receipt=topology.authority_receipt_sha256,
        experience_receipt=experience_receipt,
        receipts=receipts,
        name="tampered-self-recall",
    )
    result = evaluate_event_support(
        authority_id="tampered-recall-R-event",
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=experience_receipt,
        expression=expression,
        memory_energy=None,
        receipt_registry=receipts,
    )
    mounted = _extend(receipts, *result.generated_receipt_payloads)
    changed_interval = replace(
        result.intervals[0],
        exact_fresh_source_energy=Fraction(1),
    )
    changed = replace(result, intervals=(changed_interval,))

    with pytest.raises(ReceiptError, match="relabelled as fresh energy"):
        changed.verify(
            origin=origin,
            topology=topology,
            closed_experience_receipt_sha256=experience_receipt,
            expression=expression,
            receipt_registry=mounted,
        )
