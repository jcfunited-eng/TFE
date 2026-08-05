from __future__ import annotations

from fractions import Fraction as F

import pytest

from dsf_ai_service.glew_runtime.causal_relation_episode import (
    CausalDirectionSourceKind,
    cause_consequence_source_receipt_payload,
    create_causal_direction_authority,
    create_causal_relation_recovery_episode,
    create_causal_relation_support_episode,
    extend_relation_domain_with_zero_mass,
)
from dsf_ai_service.glew_runtime.closed_experience import (
    ClosedExperienceEvidenceEvent,
    ClosedExperienceEvidencePreparation,
    ProviderStatus,
    _preparation_receipt_payload,
    _resonance_payload,
    _support_payload,
)
from dsf_ai_service.glew_runtime.event_support import (
    MemoryEnergyAuthority,
    evaluate_event_support,
    memory_energy_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.experience_origin import (
    ExperienceOriginAuthority,
    ExperienceOriginKind,
    experience_origin_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.expression_modes import (
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
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
    sparse_map_inject,
)
from dsf_ai_service.glew_runtime.memory import (
    DirectedRelation,
    MemoryElementCalibration,
    create_quiescent_memory_state,
    memory_element_calibration_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.operators import (
    PortSupportFact,
    ResonanceConfirmation,
    SupportFloor,
)
from tests.glew_runtime.test_closed_experience_provider import (
    _evolution_authority,
)
from tests.glew_runtime.test_field import (
    COMMON_AUTHORITIES,
    PHYSICAL_PROFILE_AUTHORITY,
    PROFILE,
    evidence,
    exact_ball,
    exact_state,
    topology as make_topology,
)


def _registry(*payloads: bytes) -> ReceiptRegistry:
    return ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=tuple(dict.fromkeys((*COMMON_AUTHORITIES, *payloads))),
    )


def _merge(
    *registries: ReceiptRegistry, payloads: tuple[bytes, ...] = ()
) -> ReceiptRegistry:
    by_digest: dict[str, bytes] = {}
    for registry in registries:
        assert registry.profile_binding_sha256 == receipt_sha256(PROFILE)
        for record in registry.records:
            previous = by_digest.setdefault(record.digest, record.payload)
            assert previous == record.payload
    for payload in payloads:
        digest = receipt_sha256(payload)
        previous = by_digest.setdefault(digest, payload)
        assert previous == payload
    records = tuple(
        ReceiptRecord(digest=digest, payload=payload)
        for digest, payload in by_digest.items()
    )
    return ReceiptRegistry(receipt_sha256(PROFILE), records)


def _mode_payloads(result) -> tuple[bytes, ...]:
    values = [
        result.receipt_payload,
        result.pre_growth_bank.receipt_payload,
        result.post_growth_bank.receipt_payload,
    ]
    for bank in (result.pre_growth_bank, result.post_growth_bank):
        for mode in bank.modes:
            values.extend(
                (
                    mode.growth_proof_receipt_payload,
                    mode.receipt_payload,
                    mode.source_expression.receipt_payload,
                )
            )
    return tuple(dict.fromkeys(values))


def _prepared_axis(
    coordinate: int,
    *,
    r_uf=F(1),
):
    lane_ports = (
        ("sight", "retina"),
        ("smell", "olfactory"),
        ("taste", "tongue"),
        ("touch", "skin"),
    )
    records = []
    raw_payloads = []
    evidence_payloads = []
    for lane_index, (lane_id, port_id) in enumerate(lane_ports):
        values = [F(0)] * 19
        values[(4 if coordinate == 0 else 0) + lane_index] = F(1)
        values[18] = F(1) if coordinate == 18 else F(0)
        record, raw_payload, evidence_payload = evidence(
            lane_id, port_id, tuple(values)
        )
        records.append(record)
        raw_payloads.append(raw_payload)
        evidence_payloads.append(evidence_payload)
    fibers = tuple(PortFiber(*value) for value in lane_ports)
    mounted, topology_payload = make_topology(*fibers)
    domain_payload = b"semantic support-domain authority"
    graph_payload = b"semantic resonance-graph authority"
    operator_payload = b"semantic resonance-operator authority"
    base = _registry(
        topology_payload,
        *raw_payloads,
        *evidence_payloads,
        domain_payload,
        graph_payload,
        operator_payload,
    )
    injection = sparse_map_inject(mounted, tuple(records), F(5), base)
    event = ClosedExperienceEvidenceEvent(
        F(4), F(5), tuple(records), injection
    )
    authority, authority_payload = _evolution_authority(
        topology=mounted,
        event=event,
        authority_id=f"semantic-axis-{coordinate}",
    )
    initial, initial_payload = exact_state(
        mounted, F(4), (ExactComplex(F(0)),) * mounted.dimension
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="causal-relation-precision",
        maximum_precision_bits=4096,
    )
    precision = PrecisionScheduleAuthority(
        "causal-relation-precision",
        4096,
        receipt_sha256(precision_payload),
    )
    expression_payloads = (
        injection.receipt_payload,
        authority_payload,
        initial_payload,
        precision_payload,
    )
    expression_registry = _merge(base, payloads=expression_payloads)
    expression = create_closed_experience_expression(
        topology=mounted,
        initial_state=initial,
        steps=(FieldExpressionStep(injection, authority),),
        precision_authority=precision,
        receipt_registry=expression_registry,
    )

    support = SupportFloor(
        value=F(1),
        port_facts=tuple(
            PortSupportFact(value, F(1), True) for value in lane_ports
        ),
        required_port_keys=lane_ports,
        domain_authority_receipt_sha256=receipt_sha256(domain_payload),
        grid_id="causal-grid",
    )
    resonance = ResonanceConfirmation(
        value=exact_ball(r_uf),
        edge_facts=(),
        required_edges=(),
        graph_authority_receipt_sha256=receipt_sha256(graph_payload),
        operator_authority_receipt_sha256=receipt_sha256(operator_payload),
        working_precision_bits=256,
        grid_id="causal-grid",
    )
    support_payload = _support_payload(support)
    resonance_payload = _resonance_payload(resonance)
    preparation_payload = _preparation_receipt_payload(
        topology_authority_receipt_sha256=mounted.authority_receipt_sha256,
        events=(event,),
        source_time_start=F(4),
        source_time_end=F(5),
        support_floor_receipt_sha256=receipt_sha256(support_payload),
        resonance_confirmation_receipt_sha256=(
            receipt_sha256(resonance_payload)
        ),
    )
    prepared_registry = _merge(
        expression_registry,
        payloads=(
            expression.receipt_payload,
            support_payload,
            resonance_payload,
            preparation_payload,
        ),
    )
    preparation = ClosedExperienceEvidencePreparation(
        status=ProviderStatus.READY,
        topology_authority_receipt_sha256=mounted.authority_receipt_sha256,
        events=(event,),
        source_time_start=F(4),
        source_time_end=F(5),
        support_floor=support,
        resonance_confirmation=resonance,
        receipt_sha256=receipt_sha256(preparation_payload),
        receipt_payload=preparation_payload,
        receipt_registry=prepared_registry,
    )
    preparation.verify(mounted, prepared_registry)
    expression.verify(prepared_registry)
    return mounted, preparation, expression, prepared_registry


def _two_mode_context(*, target_r_uf=F(1)):
    topology, first_preparation, first, first_registry = _prepared_axis(0)
    _, target_preparation, target, target_registry = _prepared_axis(
        18, r_uf=target_r_uf
    )
    registry = _merge(first_registry, target_registry)
    empty = create_empty_expression_mode_bank(
        topology=topology,
        precision_authority=first.precision_authority,
        receipt_registry=registry,
    )
    registry = _merge(registry, payloads=(empty.receipt_payload,))
    first_growth = evaluate_expression_mode_boundary(
        topology=topology,
        bank=empty,
        input_expression=first,
        receipt_registry=registry,
    )
    registry = _merge(registry, payloads=_mode_payloads(first_growth))
    second_growth = evaluate_expression_mode_boundary(
        topology=topology,
        bank=first_growth.post_growth_bank,
        input_expression=target,
        receipt_registry=registry,
    )
    registry = _merge(registry, payloads=_mode_payloads(second_growth))
    bank = second_growth.post_growth_bank
    assert bank.rank == 2
    bank.verify(topology=topology, receipt_registry=registry)
    relation = DirectedRelation(
        source_mode_index=0,
        target_mode_index=1,
        source_mode_receipt_sha256=bank.modes[0].receipt_sha256,
        target_mode_receipt_sha256=bank.modes[1].receipt_sha256,
    )
    return (
        topology,
        first_preparation,
        first,
        target_preparation,
        target,
        bank,
        relation,
        registry,
    )


def _episode_context(*, target_r_uf=F(1)):
    (
        topology,
        _first_preparation,
        first,
        target_preparation,
        target,
        bank,
        relation,
        registry,
    ) = _two_mode_context(target_r_uf=target_r_uf)
    closed_payload = b"closed consequence occurrence: target axis"
    origin_source = b"fresh external causal episode origin"
    origin_payload = experience_origin_authority_receipt_payload(
        origin_id="causal-episode-origin",
        kind=ExperienceOriginKind.FRESH_EXTERNAL,
        profile_binding_sha256=registry.profile_binding_sha256,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=receipt_sha256(closed_payload),
        source_authority_receipt_sha256=receipt_sha256(origin_source),
    )
    origin = ExperienceOriginAuthority(
        origin_id="causal-episode-origin",
        kind=ExperienceOriginKind.FRESH_EXTERNAL,
        profile_binding_sha256=registry.profile_binding_sha256,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=receipt_sha256(closed_payload),
        source_authority_receipt_sha256=receipt_sha256(origin_source),
        authority_receipt_sha256=receipt_sha256(origin_payload),
    )
    energy_derivation = b"exact causal episode energy derivation"
    energy_payload = memory_energy_authority_receipt_payload(
        authority_id="causal-episode-energy",
        energy_unit_id="causal-energy-unit",
        exact_memory_energy=F(1),
        derivation_receipt_sha256=receipt_sha256(energy_derivation),
        physical_profile_receipt_sha256=receipt_sha256(
            PHYSICAL_PROFILE_AUTHORITY
        ),
    )
    energy = MemoryEnergyAuthority(
        authority_id="causal-episode-energy",
        energy_unit_id="causal-energy-unit",
        exact_memory_energy=F(1),
        derivation_receipt_sha256=receipt_sha256(energy_derivation),
        physical_profile_receipt_sha256=receipt_sha256(
            PHYSICAL_PROFILE_AUTHORITY
        ),
        authority_receipt_sha256=receipt_sha256(energy_payload),
    )
    registry = _merge(
        registry,
        payloads=(
            closed_payload,
            origin_source,
            origin_payload,
            energy_derivation,
            energy_payload,
        ),
    )
    event_support = evaluate_event_support(
        authority_id="causal-episode-R-event",
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=receipt_sha256(closed_payload),
        expression=target,
        memory_energy=energy,
        receipt_registry=registry,
    )
    assert event_support.exact_r_event is not None
    assert event_support.exact_r_event > 0
    registry = _merge(
        registry, payloads=event_support.generated_receipt_payloads
    )

    derivation = b"mounted local k and gamma derivation"
    calibration_payload = memory_element_calibration_receipt_payload(
        element_id="causal-relation-element",
        relation=relation,
        stiffness=F(3),
        damping=F(2),
        structural_time_unit="structural_second",
        derivation_receipt_sha256=receipt_sha256(derivation),
    )
    calibration = MemoryElementCalibration(
        element_id="causal-relation-element",
        relation=relation,
        stiffness=F(3),
        damping=F(2),
        structural_time_unit="structural_second",
        derivation_receipt_sha256=receipt_sha256(derivation),
        calibration_receipt_sha256=receipt_sha256(calibration_payload),
    )
    source_occurrence = b"authenticated source occurrence"
    causal_mechanism = (
        b"embodied intervention authority proved this cause-consequence pair"
    )
    causal_source = cause_consequence_source_receipt_payload(
        source_kind=CausalDirectionSourceKind.EMBODIED_INTERVENTION,
        relation=relation,
        source_occurrence_receipt_sha256=receipt_sha256(source_occurrence),
        consequence_occurrence_receipt_sha256=receipt_sha256(closed_payload),
        source_time_start=F(2),
        source_time_end=F(3),
        consequence_time_start=target_preparation.source_time_start,
        consequence_time_end=target_preparation.source_time_end,
        structural_time_unit="structural_second",
        causal_mechanism_authority_receipt_sha256=(
            receipt_sha256(causal_mechanism)
        ),
    )
    registry = _merge(
        registry,
        payloads=(
            derivation,
            calibration_payload,
            source_occurrence,
            causal_mechanism,
            causal_source,
        ),
    )
    direction, registry = create_causal_direction_authority(
        authority_id="cause-axis-zero-to-axis-negative-space",
        relation=relation,
        bank=bank,
        topology=topology,
        source_occurrence_receipt_sha256=receipt_sha256(source_occurrence),
        consequence_occurrence_receipt_sha256=receipt_sha256(closed_payload),
        cause_consequence_source_receipt_sha256=receipt_sha256(causal_source),
        source_time_start=F(2),
        source_time_end=F(3),
        consequence_time_start=target_preparation.source_time_start,
        consequence_time_end=target_preparation.source_time_end,
        structural_time_unit="structural_second",
        receipt_registry=registry,
    )
    return {
        "topology": topology,
        "source_expression": first,
        "preparation": target_preparation,
        "expression": target,
        "bank": bank,
        "relation": relation,
        "origin": origin,
        "event_support": event_support,
        "calibration": calibration,
        "direction": direction,
        "registry": registry,
    }


def test_supported_episode_creates_exact_conservative_existing_drive():
    context = _episode_context()
    material = create_causal_relation_support_episode(
        episode_id="supported-causal-relation",
        direction=context["direction"],
        topology=context["topology"],
        bank=context["bank"],
        preparation=context["preparation"],
        expression=context["expression"],
        origin=context["origin"],
        event_support=context["event_support"],
        calibration=context["calibration"],
        receipt_registry=context["registry"],
    )

    assert material.drive.relation == context["relation"]
    assert material.drive.relation_support == F(1)
    assert (
        material.drive.excitation_rate * material.authority.delta
        == material.authority.exact_r_event
    )
    assert material.authority.resonance_value == exact_ball(F(1))
    assert b"field_evaluation_identity" in material.authority.payload()
    assert b"centroid" in material.authority.payload()


def test_recovery_semantically_reads_actual_n_gate_and_creates_no_drive():
    context = _episode_context()
    material = create_causal_relation_recovery_episode(
        episode_id="quiet-causal-relation-recovery",
        direction=context["direction"],
        topology=context["topology"],
        bank=context["bank"],
        preparation=context["preparation"],
        expression=context["expression"],
        origin=context["origin"],
        event_support=context["event_support"],
        calibration=context["calibration"],
        receipt_registry=context["registry"],
    )

    assert material.negative_space_proof.active_lane_ids == (
        "sight",
        "smell",
        "taste",
        "touch",
    )
    lane_payload = material.receipt_registry.resolve(
        material.negative_space_proof.lane_l1_proof_receipt_sha256s[0]
    )
    assert b"every_actual_native_L1_closure_has_exact_N_gate=1" in lane_payload
    assert not hasattr(material, "drive")


def test_recovery_rejects_actual_lane_n_gate_zero():
    context = _episode_context()
    zero_preparation = _prepared_axis(0)[1]

    with pytest.raises(ReceiptError, match="actual L1 N_gate != 1"):
        create_causal_relation_recovery_episode(
            episode_id="forbidden-opaque-negative-space",
            direction=context["direction"],
            topology=context["topology"],
            bank=context["bank"],
            preparation=zero_preparation,
            expression=context["expression"],
            origin=context["origin"],
            event_support=context["event_support"],
            calibration=context["calibration"],
            receipt_registry=context["registry"],
        )


def test_supported_episode_authorizes_zero_mass_domain_extension_only():
    context = _episode_context()
    material = create_causal_relation_support_episode(
        episode_id="domain-extension-causal-relation",
        direction=context["direction"],
        topology=context["topology"],
        bank=context["bank"],
        preparation=context["preparation"],
        expression=context["expression"],
        origin=context["origin"],
        event_support=context["event_support"],
        calibration=context["calibration"],
        receipt_registry=context["registry"],
    )
    prior = create_quiescent_memory_state(
        source_time=F(5),
        structural_time_unit="structural_second",
        topology_authority_receipt_sha256=(
            context["topology"].authority_receipt_sha256
        ),
    )
    extension = extend_relation_domain_with_zero_mass(
        state=prior,
        episode=material.authority,
        receipt_registry=material.receipt_registry,
    )

    assert extension.state.relation_order == (context["relation"],)
    assert extension.state.active_masses == (F(0),)
    assert extension.state.quiescent_mass == F(1)
    assert sum(
        (extension.state.quiescent_mass, *extension.state.active_masses), F(0)
    ) == F(1)

    with pytest.raises(ReceiptError, match="already exists"):
        extend_relation_domain_with_zero_mass(
            state=extension.state,
            episode=material.authority,
            receipt_registry=extension.receipt_registry,
        )


def test_timing_without_mounted_causal_source_is_not_direction():
    context = _episode_context()
    missing = b"unmounted causal assertion"

    with pytest.raises(
        ReceiptError, match="authenticated cause-consequence source is not mounted"
    ):
        create_causal_direction_authority(
            authority_id="timing-alone-is-not-causation",
            relation=context["relation"],
            bank=context["bank"],
            topology=context["topology"],
            source_occurrence_receipt_sha256=(
                context["direction"].source_occurrence_receipt_sha256
            ),
            consequence_occurrence_receipt_sha256=(
                context["direction"].consequence_occurrence_receipt_sha256
            ),
            cause_consequence_source_receipt_sha256=receipt_sha256(missing),
            source_time_start=F(2),
            source_time_end=F(3),
            consequence_time_start=F(4),
            consequence_time_end=F(5),
            structural_time_unit="structural_second",
            receipt_registry=context["registry"],
        )


def test_support_rejects_r_uf_that_does_not_certify_positive():
    context = _episode_context(target_r_uf=F(0))

    with pytest.raises(
        ReceiptError, match="R_UF does not certify strictly positive"
    ):
        create_causal_relation_support_episode(
            episode_id="zero-resonance-cannot-fund-relation",
            direction=context["direction"],
            topology=context["topology"],
            bank=context["bank"],
            preparation=context["preparation"],
            expression=context["expression"],
            origin=context["origin"],
            event_support=context["event_support"],
            calibration=context["calibration"],
            receipt_registry=context["registry"],
        )
