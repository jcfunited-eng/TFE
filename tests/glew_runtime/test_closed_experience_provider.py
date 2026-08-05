"""Vertical and tamper tests for the two-phase closed-experience provider."""

from __future__ import annotations

from dataclasses import replace
import json
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.closed_experience import (
    ClosedExperienceEvidenceEvent,
    ClosedExperienceEvidencePreparation,
    ClosedExperienceProviderBundle,
    ClosedExperienceProviderUnknown,
    KernelNativeInputSample,
    KernelNativeInputStream,
    L5ApplicabilityRule,
    MISSING_KERNEL_ADAPTER,
    NONPOSITIVE_NATIVE_GATE_DURATION,
    MountedL5GovernanceProfile,
    ProviderStatus,
    SealedClosedExperience,
    assemble_closed_experience_provider_bundle,
    kernel_native_input_receipt_payload,
    l5_governance_profile_receipt_payload,
    prepare_closed_experience_evidence,
    run_ratified_native_l0_l4_trace,
    run_ratified_native_l0_l4_trace_typed,
    seal_closed_experience,
    source_evidence_stream_receipt_payload,
)
from dsf_ai_service.glew_runtime.commit import (
    ApplicabilityState,
    CommitStatus,
    EventSupportState,
    GovernedFact,
    L6ScopeAuthority,
    evaluate_commit_boundary,
    evaluate_pending_global_uf_conjunction,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.event_support import (
    EventSupportEvaluationStatus,
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
    ExpressionModeBoundaryResult,
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
)
from dsf_ai_service.glew_runtime.expressions import (
    ClosedExperienceFieldExpression,
    FieldExpressionStep,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
    precision_schedule_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.field import (
    ExactComplex,
    FieldEvolutionAuthority,
    PortFiber,
    canonical_component_partition,
    evolution_authority_receipt_payload,
    source_coefficients_for_injection,
    sparse_map_inject,
)
from dsf_ai_service.glew_runtime.global_uf import (
    MountedPreWindowState,
    MountedRawObservationWindow,
    MountedSensorResolutionProfile,
    ObservationCoordinate,
    SensorCodeResolution,
    SensorIntegerObservation,
    TypedUnicodeObservation,
    evaluate_global_uf_validation,
    pre_window_state_receipt_payload,
    raw_observation_window_receipt_payload,
    sensor_resolution_profile_receipt_payload,
)
from dsf_ai_service.glew_runtime.l6 import (
    ActiveLaneState,
    L6EvaluationStatus,
    L6Lane,
    L6PredicateInputs,
    evaluate_l6,
)
from dsf_ai_service.glew_runtime.model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.structural_port_basin import (
    port_kernel_basin_from_trace_record,
    port_kernel_basin_from_typed_trace,
)
from dsf_ai_service.glew_runtime.safe_mode import (
    IntegrityFact,
    IntegrityFactState,
    MountedSafeModeScope,
    evaluate_safe_mode,
    integrity_fact_receipt_payload,
    safe_mode_scope_receipt_payload,
)
from dsf_ai_service.glew_runtime.physical_l6_tangents import (
    ExactL4Response,
    LanguageTritCoordinate,
    MountedNativePerturbationProfile,
    MountedNativeResponseSet,
    MountedSameBranchCellProof,
    NativeL4ReplayResponse,
    NativePortReplayBundle,
    PhysicalTangentProductionStatus,
    SensorNativeCoordinate,
    TypedTrit,
    enumerate_native_replay_cases,
    native_l4_replay_response_receipt_payload,
    native_perturbation_profile_receipt_payload,
    native_response_set_receipt_payload,
    produce_physical_l6_tangents,
    same_branch_cell_proof_receipt_payload,
)
from dsf_ai_service.glew_runtime.operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    RequiredEdge,
    ResonanceOperatorAuthority,
    causal_grid_receipt_payload,
    resonance_graph_receipt_payload,
    resonance_operator_receipt_payload,
    support_domain_receipt_payload,
)
from tests.glew_runtime.test_field import (
    COMMON_AUTHORITIES,
    PHYSICAL_PROFILE_AUTHORITY,
    PROFILE,
    exact_state,
    registry,
    topology as make_topology,
)
from tests.glew_runtime.test_global_uf import Provider as ExactReplayProvider


CALIBRATION = b"provider-test-calibration"
NATIVE_RELEVANCE = b"provider-test-native-relevance"
TRANSDUCTION_PROFILE = b"signed native calibration and relevance profile"
TIMESTAMPS = (Fraction(5), Fraction(6))
WEIGHTS = (Fraction(1), Fraction(1))
FIBERS = (PortFiber("language", "typed"), PortFiber("sight", "retina"))


def _payloads(value: ReceiptRegistry) -> tuple[bytes, ...]:
    common = {*COMMON_AUTHORITIES, PROFILE}
    return tuple(
        record.payload for record in value.records if record.payload not in common
    )


def _unique(values) -> tuple[bytes, ...]:
    return tuple(dict.fromkeys(values))


def _streams(
    profile_digest: str,
    signals: tuple[tuple[Fraction, ...], ...],
    timestamps: tuple[Fraction, ...],
) -> tuple[EvidenceStream, ...]:
    return tuple(
        EvidenceStream(
            lane_id=fiber.lane_id,
            port_id=fiber.port_id,
            evidence_id=f"native-{fiber.lane_id}",
            source_epoch="epoch-1",
            port_kind="independent-native-port",
            physical_unit="native-unit",
            profile_binding_sha256=profile_digest,
            calibration_receipt_sha256=receipt_sha256(CALIBRATION),
            relevance_receipt_sha256=receipt_sha256(NATIVE_RELEVANCE),
            samples=tuple(
                EvidenceSample(
                    source_index=index,
                    timestamp=timestamp,
                    signal=signal,
                    relevance=Fraction(1),
                    phase_turns=Fraction(0),
                )
                for index, (timestamp, signal) in enumerate(
                    zip(timestamps, port_signals, strict=True)
                )
            ),
        )
        for fiber, port_signals in zip(FIBERS, signals, strict=True)
    )


def _adapters(
    streams: tuple[EvidenceStream, ...],
) -> tuple[tuple[KernelNativeInputStream, ...], tuple[bytes, ...]]:
    values = []
    payloads = []
    for stream in streams:
        samples = tuple(
            KernelNativeInputSample(
                source_index=source.source_index,
                timestamp=source.timestamp,
                dimensionless_field=Fraction(1) + source.signal / 2,
                l0_relevance=source.relevance,
            )
            for source in stream.samples
        )
        source_digest = receipt_sha256(
            source_evidence_stream_receipt_payload(stream)
        )
        payload = kernel_native_input_receipt_payload(
            adapter_id=f"signed-transduction-{stream.lane_id}",
            adapter_profile_receipt_sha256=receipt_sha256(
                TRANSDUCTION_PROFILE
            ),
            lane_id=stream.lane_id,
            port_id=stream.port_id,
            source_stream_receipt_sha256=source_digest,
            samples=samples,
        )
        values.append(
            KernelNativeInputStream(
                adapter_id=f"signed-transduction-{stream.lane_id}",
                adapter_profile_receipt_sha256=receipt_sha256(
                    TRANSDUCTION_PROFILE
                ),
                lane_id=stream.lane_id,
                port_id=stream.port_id,
                source_stream_receipt_sha256=source_digest,
                samples=samples,
                authority_receipt_sha256=receipt_sha256(payload),
            )
        )
        payloads.append(payload)
    return tuple(values), tuple(payloads)


def _environment(
    signals: tuple[tuple[Fraction, ...], ...] = (
        (Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0)),
    ),
    timestamps: tuple[Fraction, ...] = TIMESTAMPS,
):
    weights = tuple(Fraction(1) for _ in timestamps)
    topology, topology_payload = make_topology(*FIBERS)
    seed_registry = registry(topology_payload)
    streams = _streams(
        seed_registry.profile_binding_sha256,
        signals,
        timestamps,
    )
    adapters, adapter_payloads = _adapters(streams)
    grid_payload = causal_grid_receipt_payload(
        "provider-grid",
        timestamps,
        weights,
    )
    grid = CausalGrid(
        "provider-grid",
        timestamps,
        weights,
        receipt_sha256(grid_payload),
    )
    support_payload = support_domain_receipt_payload(
        "provider-support",
        tuple(value.key for value in streams),
    )
    support = MountedSupportDomain(
        "provider-support",
        tuple(value.key for value in streams),
        receipt_sha256(support_payload),
    )
    edge = RequiredEdge(streams[0].key, streams[1].key)
    graph_payload = resonance_graph_receipt_payload(
        "provider-graph",
        (edge,),
    )
    graph = MountedResonanceGraph(
        "provider-graph",
        (edge,),
        receipt_sha256(graph_payload),
    )
    operator_payload = resonance_operator_receipt_payload(
        "provider-resonance",
        256,
    )
    operator = ResonanceOperatorAuthority(
        "provider-resonance",
        256,
        receipt_sha256(operator_payload),
    )
    rules = tuple(
        L5ApplicabilityRule(
            fiber.lane_id,
            fiber.port_id,
            fact,
            ApplicabilityState.REQUIRED,
        )
        for fiber in topology.ordered_port_fibers
        for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
    )
    l5_payload = l5_governance_profile_receipt_payload(
        profile_id="provider-L5",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        rules=rules,
    )
    l5 = MountedL5GovernanceProfile(
        "provider-L5",
        topology.authority_receipt_sha256,
        rules,
        receipt_sha256(l5_payload),
    )
    base_payloads = _unique(
        (
            topology_payload,
            grid_payload,
            CALIBRATION,
            NATIVE_RELEVANCE,
            TRANSDUCTION_PROFILE,
            *adapter_payloads,
            support_payload,
            graph_payload,
            operator_payload,
            l5_payload,
        )
    )
    receipts = registry(*base_payloads)
    return {
        "topology": topology,
        "l5": l5,
        "streams": streams,
        "adapters": adapters,
        "base_payloads": base_payloads,
        "prepare": {
            "streams": streams,
            "kernel_inputs": adapters,
            "source_time_start": timestamps[0],
            "grid": grid,
            "support_domain": support,
            "resonance_graph": graph,
            "resonance_operator": operator,
            "topology": topology,
            "receipt_registry": receipts,
        },
    }


def _evolution_authority(
    *,
    topology,
    event: ClosedExperienceEvidenceEvent,
    authority_id: str,
) -> tuple[FieldEvolutionAuthority, bytes]:
    source = source_coefficients_for_injection(
        event.injection,
        event.source_time_end - event.source_time_start,
    )
    components = canonical_component_partition(topology.dimension, ())
    payload = evolution_authority_receipt_payload(
        authority_id=authority_id,
        physical_profile_receipt_sha256=receipt_sha256(
            PHYSICAL_PROFILE_AUTHORITY
        ),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        map_injection_receipt_sha256=event.injection.receipt_sha256,
        source_time_start=event.source_time_start,
        source_time_end=event.source_time_end,
        source_time_unit="structural_second",
        hbar=Fraction(1),
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
            topology_authority_receipt_sha256=(
                topology.authority_receipt_sha256
            ),
            map_injection_receipt_sha256=event.injection.receipt_sha256,
            source_time_start=event.source_time_start,
            source_time_end=event.source_time_end,
            source_time_unit="structural_second",
            hbar=Fraction(1),
            hamiltonian=(),
            local_rates=(),
            source=source,
            max_connected_component_dimension=1,
            precision_bits=256,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def _expression(
    *,
    topology,
    events,
    base_registry,
) -> tuple[ClosedExperienceFieldExpression, ReceiptRegistry]:
    payloads = list(_payloads(base_registry))
    authorities = []
    for index, event in enumerate(events):
        authority, authority_payload = _evolution_authority(
            topology=topology,
            event=event,
            authority_id=f"provider-field-event-{index}",
        )
        authorities.append(authority)
        payloads.extend(
            (event.injection.receipt_payload, authority_payload)
        )

    initial, initial_payload = exact_state(
        topology,
        events[0].source_time_start,
        (ExactComplex(Fraction(0)),) * topology.dimension,
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="provider-expression-precision",
        maximum_precision_bits=4096,
    )
    precision = PrecisionScheduleAuthority(
        "provider-expression-precision",
        4096,
        receipt_sha256(precision_payload),
    )
    payloads.extend((initial_payload, precision_payload))
    receipts = registry(*payloads)
    result = create_closed_experience_expression(
        topology=topology,
        initial_state=initial,
        steps=tuple(
            FieldExpressionStep(event.injection, authority)
            for event, authority in zip(
                events,
                authorities,
                strict=True,
            )
        ),
        precision_authority=precision,
        receipt_registry=receipts,
    )
    return result, registry(*payloads, result.receipt_payload)


def _mode_payloads(
    result: ExpressionModeBoundaryResult,
) -> tuple[bytes, ...]:
    values = [
        result.receipt_payload,
        result.pre_growth_bank.receipt_payload,
        result.post_growth_bank.receipt_payload,
    ]
    for bank in (result.pre_growth_bank, result.post_growth_bank):
        for mode in bank.modes:
            values.extend(
                (
                    mode.receipt_payload,
                    mode.growth_proof_receipt_payload,
                    mode.source_expression.receipt_payload,
                )
            )
    return _unique(values)


def _recognized(
    expression: ClosedExperienceFieldExpression,
    receipts: ReceiptRegistry,
) -> tuple[ExpressionModeBoundaryResult, ReceiptRegistry]:
    topology = expression.topology
    empty = create_empty_expression_mode_bank(
        topology=topology,
        precision_authority=expression.precision_authority,
        receipt_registry=receipts,
    )
    first = evaluate_expression_mode_boundary(
        topology=topology,
        bank=empty,
        input_expression=expression,
        receipt_registry=receipts,
    )
    first_registry = registry(
        *_payloads(receipts),
        empty.receipt_payload,
        *_mode_payloads(first),
    )
    second = evaluate_expression_mode_boundary(
        topology=topology,
        bank=first.post_growth_bank,
        input_expression=expression,
        receipt_registry=first_registry,
    )
    final_registry = registry(
        *_payloads(first_registry),
        *_mode_payloads(second),
    )
    return second, final_registry


def _prepare_ready(environment) -> ClosedExperienceEvidencePreparation:
    result = prepare_closed_experience_evidence(**environment["prepare"])
    assert isinstance(result, ClosedExperienceEvidencePreparation)
    return result


def _registry_with(
    base: ReceiptRegistry,
    *payloads: bytes,
) -> ReceiptRegistry:
    return registry(*_payloads(base), *payloads)


def _sealed_environment():
    environment = _environment()
    preparation = _prepare_ready(environment)
    expression, expression_registry = _expression(
        topology=environment["topology"],
        events=preparation.events,
        base_registry=preparation.receipt_registry,
    )
    recognition, recognition_registry = _recognized(
        expression,
        expression_registry,
    )
    sealed = seal_closed_experience(
        experience_id="vertical-lived-experience",
        structural_time_unit="structural_second",
        preparation=preparation,
        topology=environment["topology"],
        l5_governance=environment["l5"],
        expression=expression,
        recognition=recognition,
        receipt_registry=recognition_registry,
    )
    return environment, preparation, expression, recognition, sealed


def _physical_replay_bundle(
    *,
    lane: L6Lane,
    native_port_id: str,
    pre_window: MountedPreWindowState,
    payloads: list[bytes],
) -> NativePortReplayBundle:
    provider_id = f"closed-experience-{lane.value}-native-provider"
    profile_id = f"closed-experience-{lane.value}-native-profile"
    if lane is L6Lane.LANGUAGE:
        coordinate_source = b"closed-experience-typed-trit-authority"
        sensor_coordinates = ()
        language_coordinates = (
            LanguageTritCoordinate(
                "typed-utterance-trit",
                TypedTrit.QUIESCENT,
                receipt_sha256(coordinate_source),
            ),
        )
    else:
        coordinate_source = b"closed-experience-retina-code-authority"
        sensor_coordinates = (
            SensorNativeCoordinate(
                "retina-native-code",
                1,
                0,
                2,
                Fraction(1),
                receipt_sha256(coordinate_source),
            ),
        )
        language_coordinates = ()
    profile_payload = native_perturbation_profile_receipt_payload(
        profile_id=profile_id,
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        sensor_coordinates=sensor_coordinates,
        language_trit_coordinates=language_coordinates,
    )
    profile = MountedNativePerturbationProfile(
        profile_id,
        lane,
        provider_id,
        native_port_id,
        sensor_coordinates,
        language_coordinates,
        receipt_sha256(profile_payload),
    )
    payloads.extend((coordinate_source, profile_payload))

    cases = enumerate_native_replay_cases(profile, pre_window)
    branch_id = f"closed-experience-{lane.value}-replay-branch"
    cell_id = f"closed-experience-{lane.value}-replay-cell"
    base = tuple(Fraction(10 + index, 3) for index in range(7))
    response_gradient = tuple(Fraction(index + 1) for index in range(7))
    responses = []
    for case in cases:
        response_id = f"{profile_id}:response:{case.case_index}"
        source = f"{response_id}:exact-L4-replay-source".encode()
        values = tuple(
            value + case.native_delta * gradient
            for value, gradient in zip(base, response_gradient, strict=True)
        )
        l4_response = ExactL4Response(*values)
        response_payload = native_l4_replay_response_receipt_payload(
            response_id=response_id,
            lane=lane,
            provider_id=provider_id,
            native_port_id=native_port_id,
            case_receipt_sha256=case.receipt_sha256,
            profile_receipt_sha256=profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=(
                pre_window.authority_receipt_sha256
            ),
            branch_id=branch_id,
            cell_id=cell_id,
            l4_response=l4_response,
            source_operator_receipt_sha256=receipt_sha256(source),
        )
        payloads.extend((source, response_payload))
        responses.append(
            NativeL4ReplayResponse(
                response_id,
                lane,
                provider_id,
                native_port_id,
                case.receipt_sha256,
                profile.authority_receipt_sha256,
                pre_window.authority_receipt_sha256,
                branch_id,
                cell_id,
                l4_response,
                receipt_sha256(source),
                receipt_sha256(response_payload),
            )
        )
    response_tuple = tuple(responses)
    completeness_source = f"{profile_id}:complete-native-replay-source".encode()
    response_set_payload = native_response_set_receipt_payload(
        response_set_id=f"{profile_id}:response-set",
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window.authority_receipt_sha256,
        responses=response_tuple,
        source_completeness_receipt_sha256=receipt_sha256(
            completeness_source
        ),
    )
    response_set = MountedNativeResponseSet(
        f"{profile_id}:response-set",
        lane,
        provider_id,
        native_port_id,
        profile.authority_receipt_sha256,
        pre_window.authority_receipt_sha256,
        response_tuple,
        receipt_sha256(completeness_source),
        receipt_sha256(response_set_payload),
    )
    branch_source = f"{profile_id}:same-branch-cell-source".encode()
    branch_payload = same_branch_cell_proof_receipt_payload(
        proof_id=f"{profile_id}:same-branch-cell",
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window.authority_receipt_sha256,
        branch_id=branch_id,
        cell_id=cell_id,
        response_receipt_sha256s=tuple(
            value.receipt_sha256 for value in response_tuple
        ),
        source_operator_receipt_sha256=receipt_sha256(branch_source),
    )
    branch_proof = MountedSameBranchCellProof(
        f"{profile_id}:same-branch-cell",
        lane,
        provider_id,
        native_port_id,
        profile.authority_receipt_sha256,
        pre_window.authority_receipt_sha256,
        branch_id,
        cell_id,
        tuple(value.receipt_sha256 for value in response_tuple),
        receipt_sha256(branch_source),
        receipt_sha256(branch_payload),
    )
    payloads.extend(
        (
            completeness_source,
            response_set_payload,
            branch_source,
            branch_payload,
        )
    )
    return NativePortReplayBundle(profile, response_set, branch_proof)


def _actual_authorities(
    *,
    topology,
    sealed: SealedClosedExperience,
    origin_kind: ExperienceOriginKind = ExperienceOriginKind.FRESH_EXTERNAL,
):
    topology_receipt = topology.authority_receipt_sha256
    experience_receipt = sealed.closed_experience.authority_receipt_sha256

    safe_profile = b"closed-experience-required-integrity-profile"
    fact_ids = ("chemistry", "field", "persistence")
    safe_scope_payload = safe_mode_scope_receipt_payload(
        scope_id="closed-experience-integrity-scope",
        topology_authority_receipt_sha256=topology_receipt,
        required_fact_ids=fact_ids,
        source_profile_receipt_sha256=receipt_sha256(safe_profile),
    )
    safe_scope = MountedSafeModeScope(
        "closed-experience-integrity-scope",
        topology_receipt,
        fact_ids,
        receipt_sha256(safe_profile),
        receipt_sha256(safe_scope_payload),
    )
    safe_payloads = [safe_profile, safe_scope_payload]
    facts = []
    for fact_id in fact_ids:
        source = f"exact-integrity-source:{fact_id}".encode()
        fact_payload = integrity_fact_receipt_payload(
            fact_id=fact_id,
            state=IntegrityFactState.CLEAR,
            topology_authority_receipt_sha256=topology_receipt,
            closed_experience_receipt_sha256=experience_receipt,
            source_operator_receipt_sha256=receipt_sha256(source),
        )
        safe_payloads.extend((source, fact_payload))
        facts.append(
            IntegrityFact(
                fact_id,
                IntegrityFactState.CLEAR,
                topology_receipt,
                experience_receipt,
                receipt_sha256(source),
                receipt_sha256(fact_payload),
            )
        )
    working = _registry_with(sealed.receipt_registry, *safe_payloads)
    safe_evaluation = evaluate_safe_mode(
        authority_id="closed-experience-safe-mode",
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        scope=safe_scope,
        facts=tuple(facts),
        receipt_registry=working,
    )

    origin_source = (
        f"closed-experience-origin-source:{origin_kind.value}".encode()
    )
    origin_payload = experience_origin_authority_receipt_payload(
        origin_id=f"closed-experience-{origin_kind.value}",
        kind=origin_kind,
        profile_binding_sha256=working.profile_binding_sha256,
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        source_authority_receipt_sha256=receipt_sha256(origin_source),
    )
    experience_origin = ExperienceOriginAuthority(
        f"closed-experience-{origin_kind.value}",
        origin_kind,
        working.profile_binding_sha256,
        topology_receipt,
        experience_receipt,
        receipt_sha256(origin_source),
        receipt_sha256(origin_payload),
    )
    working = _registry_with(working, origin_source, origin_payload)

    energy_derivation = b"exact-reference-memory-energy-derivation"
    physical_profile = (
        sealed.expression.steps[0].authority.physical_profile_receipt_sha256
    )
    energy_payload = memory_energy_authority_receipt_payload(
        authority_id="closed-experience-memory-energy",
        energy_unit_id="closed-experience-energy-unit",
        exact_memory_energy=Fraction(1),
        derivation_receipt_sha256=receipt_sha256(energy_derivation),
        physical_profile_receipt_sha256=physical_profile,
    )
    energy = MemoryEnergyAuthority(
        "closed-experience-memory-energy",
        "closed-experience-energy-unit",
        Fraction(1),
        receipt_sha256(energy_derivation),
        physical_profile,
        receipt_sha256(energy_payload),
    )
    working = _registry_with(working, energy_derivation, energy_payload)
    event_evaluation = evaluate_event_support(
        authority_id="closed-experience-R-event",
        origin=experience_origin,
        topology=topology,
        closed_experience_receipt_sha256=experience_receipt,
        expression=sealed.expression,
        memory_energy=(
            None
            if origin_kind is ExperienceOriginKind.SELF_GENERATED_RECALL
            else energy
        ),
        receipt_registry=working,
    )

    sensor_coordinate = ObservationCoordinate(
        "sight", "retina", 0, "retina-boundary-code"
    )
    typed_coordinate = ObservationCoordinate(
        "language", "typed", 0, "typed-unicode"
    )
    sensor_observations = (SensorIntegerObservation(sensor_coordinate, 0),)
    typed_observations = (
        TypedUnicodeObservation(typed_coordinate, "sealed lived expression"),
    )
    window_payload = raw_observation_window_receipt_payload(
        window_id="closed-experience-window",
        sensor_observations=sensor_observations,
        typed_unicode_observations=typed_observations,
    )
    window = MountedRawObservationWindow(
        "closed-experience-window",
        sensor_observations,
        typed_observations,
        receipt_sha256(window_payload),
    )
    resolution_source = b"exact-retina-code-resolution-authority"
    resolutions = (
        SensorCodeResolution(
            sensor_coordinate,
            0,
            1,
            Fraction(1),
            receipt_sha256(resolution_source),
        ),
    )
    resolution_payload = sensor_resolution_profile_receipt_payload(
        profile_id="closed-experience-sensor-resolution",
        observation_window_receipt_sha256=receipt_sha256(window_payload),
        resolutions=resolutions,
    )
    resolution_profile = MountedSensorResolutionProfile(
        "closed-experience-sensor-resolution",
        receipt_sha256(window_payload),
        resolutions,
        receipt_sha256(resolution_payload),
    )
    state_payloads = {
        "chemistry": b"closed-experience-pre-window-chemistry",
        "field": b"closed-experience-pre-window-field",
        "mode": b"closed-experience-pre-window-mode",
        "memory": b"closed-experience-pre-window-memory",
        "l6": b"closed-experience-pre-window-l6",
    }
    state_payload = pre_window_state_receipt_payload(
        state_id="closed-experience-pre-window",
        chemistry_state_receipt_sha256=receipt_sha256(state_payloads["chemistry"]),
        field_state_receipt_sha256=receipt_sha256(state_payloads["field"]),
        mode_state_receipt_sha256=receipt_sha256(state_payloads["mode"]),
        memory_state_receipt_sha256=receipt_sha256(state_payloads["memory"]),
        l6_state_receipt_sha256=receipt_sha256(state_payloads["l6"]),
    )
    pre_window = MountedPreWindowState(
        "closed-experience-pre-window",
        receipt_sha256(state_payloads["chemistry"]),
        receipt_sha256(state_payloads["field"]),
        receipt_sha256(state_payloads["mode"]),
        receipt_sha256(state_payloads["memory"]),
        receipt_sha256(state_payloads["l6"]),
        receipt_sha256(state_payload),
    )
    working = _registry_with(
        working,
        window_payload,
        resolution_source,
        resolution_payload,
        *state_payloads.values(),
        state_payload,
    )
    physical_payloads = []
    bundles = tuple(
        _physical_replay_bundle(
            lane=L6Lane(fiber.lane_id),
            native_port_id=fiber.port_id,
            pre_window=pre_window,
            payloads=physical_payloads,
        )
        for fiber in topology.ordered_port_fibers
    )
    working = _registry_with(working, *physical_payloads)
    production = produce_physical_l6_tangents(
        bundles=bundles,
        pre_window_state=pre_window,
        receipt_registry=working,
    )
    assert production.status is PhysicalTangentProductionStatus.KNOWN
    assert production.candidate_constraints is not None
    assert production.candidate_constraints.stack is not None
    completeness = {
        value.lane: value.receipt_sha256
        for value in production.lane_completeness_receipts
    }
    base_u_star = {
        value.profile.lane: value.response_set.responses[0].l4_response.U_star_k
        for value in production.derived_ports
    }
    active_lanes = tuple(
        ActiveLaneState(lane, base_u_star[lane], True, digest)
        for lane, digest in completeness.items()
    )
    predicates = L6PredicateInputs(active_lanes, True)
    working = production.receipt_registry
    l6_evaluation = evaluate_l6(
        production.candidate_constraints.stack,
        predicates,
        working,
    )
    evaluation_payload = l6_evaluation_receipt_payload(l6_evaluation)
    scope_payload = l6_scope_authority_receipt_payload(
        authority_id="closed-experience-fixed42-scope",
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        l6_evaluation_receipt_sha256=receipt_sha256(evaluation_payload),
    )
    l6_scope = L6ScopeAuthority(
        "closed-experience-fixed42-scope",
        topology_receipt,
        experience_receipt,
        receipt_sha256(evaluation_payload),
        receipt_sha256(scope_payload),
    )
    working = _registry_with(
        working,
        *safe_evaluation.generated_receipt_payloads,
        *event_evaluation.generated_receipt_payloads,
        evaluation_payload,
        scope_payload,
    )
    pending_global_uf = evaluate_pending_global_uf_conjunction(
        topology=topology,
        recognition=sealed.recognition,
        l6_evaluation=l6_evaluation,
        l6_scope=l6_scope,
        closed_experience=sealed.closed_experience,
        safe_mode=safe_evaluation.authority,
        event_support=event_evaluation.authority,
        evidence=sealed.evidence,
        l5_applicability=sealed.l5_applicability,
        receipt_registry=working,
    )
    working = _registry_with(working, pending_global_uf.receipt_payload)
    global_result = evaluate_global_uf_validation(
        authority_id="closed-experience-global-UF",
        topology=topology,
        closed_experience_receipt_sha256=experience_receipt,
        observation_window=window,
        sensor_resolution_profile=resolution_profile,
        pre_window_state=pre_window,
        replay_provider=ExactReplayProvider(topology, pending_global_uf),
        receipt_registry=working,
    )
    working = global_result.receipt_registry
    return {
        "experience_origin": experience_origin,
        "safe_mode_evaluation": safe_evaluation,
        "event_support_evaluation": event_evaluation,
        "global_uf_validation": global_result,
        "l6_production": production,
        "l6_predicates": predicates,
        "l6_evaluation": l6_evaluation,
        "l6_scope": l6_scope,
        "receipt_registry": working,
    }


def test_typed_l0_l4_trace_is_byte_and_field_exact_to_receipt_path():
    environment = _environment(
        signals=(
            tuple(Fraction(index % 3 - 1, 1) for index in range(12)),
            tuple(Fraction((index + 1) % 3 - 1, 1) for index in range(12)),
        ),
        timestamps=tuple(Fraction(index) for index in range(12)),
    )
    stream = environment["streams"][0]
    adapter = environment["adapters"][0]
    receipts = environment["prepare"]["receipt_registry"]
    typed = run_ratified_native_l0_l4_trace_typed(
        stream=stream,
        adapter=adapter,
        receipt_registry=receipts,
    )
    receipt = run_ratified_native_l0_l4_trace(
        stream=stream,
        adapter=adapter,
        receipt_registry=receipts,
    )
    assert typed.raw_payload == receipt.payload
    assert receipt_sha256(typed.raw_payload) == receipt.digest
    receipt_basin, receipt_payloads = port_kernel_basin_from_trace_record(
        lane_id=stream.lane_id,
        port_id=stream.port_id,
        trace_record=receipt,
    )
    typed_basin, typed_payloads = port_kernel_basin_from_typed_trace(
        lane_id=stream.lane_id,
        port_id=stream.port_id,
        trace=typed,
    )
    assert typed_basin == receipt_basin
    assert typed_payloads == receipt_payloads
    raw = json.loads(receipt.payload)
    assert tuple(
        (value.gate.start_idx, value.gate.end_idx)
        for value in typed.l1
    ) == tuple(
        (value["start_idx"], value["end_idx"])
        for value in raw["L1_GateL1State"]
    )
    assert tuple(
        tuple(
            Fraction(row[name])
            for name in (
                "D_k", "M_k", "R_rev_k", "U_star_k",
                "C_k", "P_k", "B_k",
            )
        )
        for row in raw["L4_DSF"]
    ) == tuple(
        tuple(
            Fraction.from_float(getattr(value, name))
            for name in (
                "D_k", "M_k", "R_rev_k", "U_star_k",
                "C_k", "P_k", "B_k",
            )
        )
        for value in typed.l4
    )


def test_missing_transduction_returns_typed_unknown_without_evidence():
    environment = _environment()
    environment["prepare"]["kernel_inputs"] = None

    result = prepare_closed_experience_evidence(**environment["prepare"])

    assert isinstance(result, ClosedExperienceProviderUnknown)
    assert result.status is ProviderStatus.UNKNOWN
    assert result.reason == MISSING_KERNEL_ADAPTER
    assert not hasattr(result, "evidence")


@pytest.mark.parametrize(
    ("field_delta", "relevance", "reason"),
    (
        (
            Fraction(1, 10),
            Fraction(1),
            "ratified exact F=1\\+s/2",
        ),
        (
            Fraction(0),
            Fraction(1, 2),
            "differs from the native source relevance",
        ),
    ),
)
def test_transduction_cannot_fork_kernel_field_or_relevance(
    field_delta,
    relevance,
    reason,
):
    environment = _environment()
    original = environment["adapters"][0]
    first = original.samples[0]
    changed_sample = replace(
        first,
        dimensionless_field=first.dimensionless_field + field_delta,
        l0_relevance=relevance,
    )
    changed_samples = (changed_sample, *original.samples[1:])
    changed_payload = kernel_native_input_receipt_payload(
        adapter_id=original.adapter_id,
        adapter_profile_receipt_sha256=(
            original.adapter_profile_receipt_sha256
        ),
        lane_id=original.lane_id,
        port_id=original.port_id,
        source_stream_receipt_sha256=(
            original.source_stream_receipt_sha256
        ),
        samples=changed_samples,
    )
    changed = replace(
        original,
        samples=changed_samples,
        authority_receipt_sha256=receipt_sha256(changed_payload),
    )
    environment["prepare"]["kernel_inputs"] = (
        changed,
        environment["adapters"][1],
    )
    environment["prepare"]["receipt_registry"] = registry(
        *environment["base_payloads"],
        changed_payload,
    )

    with pytest.raises(ReceiptError, match=reason):
        prepare_closed_experience_evidence(**environment["prepare"])


def test_gate_at_initial_boundary_is_unknown_not_dropped_or_retimed():
    environment = _environment(
        signals=(
            (Fraction(0), Fraction(0)),
            (Fraction(-1), Fraction(1)),
        )
    )

    result = prepare_closed_experience_evidence(**environment["prepare"])

    assert isinstance(result, ClosedExperienceProviderUnknown)
    assert result.missing_authority == "positive_native_gate_duration"
    assert result.reason == NONPOSITIVE_NATIVE_GATE_DURATION


def test_unequal_native_gate_times_form_canonical_sparse_events_and_expression():
    timestamps = tuple(Fraction(value) for value in (5, 6, 7, 8, 9))
    environment = _environment(
        signals=(
            tuple(Fraction(0) for _ in timestamps),
            tuple(Fraction(value) for value in (-1, -1, -1, -1, 0)),
        ),
        timestamps=timestamps,
    )

    preparation = _prepare_ready(environment)

    assert tuple(
        (event.source_time_start, event.source_time_end)
        for event in preparation.events
    ) == (
        (Fraction(5), Fraction(7)),
        (Fraction(7), Fraction(8)),
        (Fraction(8), Fraction(9)),
    )
    assert tuple(
        tuple(value.key for value in event.evidence)
        for event in preparation.events
    ) == (
        (("sight", "retina"),),
        (("sight", "retina"),),
        (("language", "typed"), ("sight", "retina")),
    )
    assert preparation.events[0].injection.absent_fibers == (
        PortFiber("language", "typed"),
    )
    assert preparation.events[1].injection.absent_fibers == (
        PortFiber("language", "typed"),
    )
    assert preparation.events[2].injection.absent_fibers == ()
    assert all(
        not hasattr(event.injection, "vector")
        for event in preparation.events
    )
    assert b"no_new_source_event;no_evidence" in (
        preparation.events[0].injection.receipt_payload
    )

    expression, expression_registry = _expression(
        topology=environment["topology"],
        events=preparation.events,
        base_registry=preparation.receipt_registry,
    )

    expression.verify(expression_registry)
    assert len(expression.steps) == 3

    with pytest.raises(
        ReceiptError,
        match="differs from canonical receipt",
    ):
        replace(
            preparation,
            receipt_payload=b"forged asynchronous preparation",
        ).verify(environment["topology"], preparation.receipt_registry)

    first = preparation.events[0]
    with pytest.raises(
        ReceiptError,
        match="canonical topology complement",
    ):
        replace(
            first.injection,
            absent_fibers=(),
        ).verify(environment["topology"], preparation.receipt_registry)


def test_seal_exists_before_any_downstream_authority_is_assembled():
    environment, preparation, expression, recognition, sealed = _sealed_environment()

    assert isinstance(sealed, SealedClosedExperience)
    assert sealed.status is ProviderStatus.READY
    assert sealed.closed_experience.input_expression_receipt_sha256 == (
        expression.receipt_sha256
    )
    assert sealed.closed_experience.recognition_receipt_sha256 == (
        recognition.receipt_sha256
    )
    assert sealed.closed_experience.ordered_evidence_receipt_sha256s == tuple(
        value.evidence_receipt_sha256 for value in preparation.evidence
    )
    assert b"F=1+s/2" in sealed.evidence[0].raw_record.payload
    assert all(
        b"explicit_missing_physical_law" not in record.payload
        for record in sealed.receipt_registry.records
    )
    sealed.verify(
        topology=environment["topology"],
        receipt_registry=sealed.receipt_registry,
    )


def test_missing_real_producer_is_typed_unknown_and_never_returns_a_bundle():
    environment, _preparation, _expression_value, _recognition, sealed = (
        _sealed_environment()
    )
    authorities = _actual_authorities(
        topology=environment["topology"],
        sealed=sealed,
    )
    for missing_name in tuple(authorities):
        supplied = dict(authorities)
        supplied[missing_name] = None
        result = assemble_closed_experience_provider_bundle(
            sealed=sealed,
            topology=environment["topology"],
            **supplied,
        )
        assert isinstance(result, ClosedExperienceProviderUnknown)
        assert result.status is ProviderStatus.UNKNOWN
        expected_name = (
            "physical_l6_production"
            if missing_name == "l6_production"
            else (
                "physical_l6_predicates"
                if missing_name == "l6_predicates"
                else (
                    "physical_l6_evaluation"
                    if missing_name == "l6_evaluation"
                    else (
                        "physical_l6_scope"
                        if missing_name == "l6_scope"
                        else (
                            "authority_receipt_registry"
                            if missing_name == "receipt_registry"
                            else missing_name
                        )
                    )
                )
            )
        )
        assert result.missing_authority == expected_name
        assert not isinstance(result, ClosedExperienceProviderBundle)


def test_actual_producers_assemble_only_for_the_exact_seal_and_topology():
    environment, _preparation, _expression_value, recognition, sealed = (
        _sealed_environment()
    )
    authorities = _actual_authorities(
        topology=environment["topology"],
        sealed=sealed,
    )

    result = assemble_closed_experience_provider_bundle(
        sealed=sealed,
        topology=environment["topology"],
        **authorities,
    )

    assert isinstance(result, ClosedExperienceProviderBundle)
    assert result.status is ProviderStatus.READY
    assert result.safe_mode_evaluation.authority.disposition.value == "pass"
    assert result.event_support_evaluation.status is (
        EventSupportEvaluationStatus.RESOLVED
    )
    assert result.event_support.state is EventSupportState.ZERO
    assert result.global_uf_result.authority.disposition.value == "pass"
    assert result.l6_production.status is PhysicalTangentProductionStatus.KNOWN
    assert result.l6_evaluation.status is L6EvaluationStatus.NO_LOCK

    decision = evaluate_commit_boundary(
        topology=environment["topology"],
        recognition=recognition,
        l6_evaluation=result.l6_evaluation,
        l6_scope=result.l6_scope,
        closed_experience=result.closed_experience,
        safe_mode=result.safe_mode,
        event_support=result.event_support,
        evidence=result.evidence,
        l5_applicability=result.l5_applicability,
        global_uf_validation=result.global_uf_validation,
        receipt_registry=result.receipt_registry,
    )
    assert decision.status is CommitStatus.NO_COMMIT
    assert "fixed42_L6_no_lock" in decision.findings


def test_cross_seal_safe_mode_authority_is_rejected_loudly():
    environment, _preparation, _expression_value, _recognition, sealed = (
        _sealed_environment()
    )
    authorities = _actual_authorities(
        topology=environment["topology"],
        sealed=sealed,
    )
    safe = authorities["safe_mode_evaluation"]
    crossed_authority = replace(
        safe.authority,
        closed_experience_receipt_sha256="0" * 64,
    )
    authorities["safe_mode_evaluation"] = replace(
        safe,
        authority=crossed_authority,
    )

    with pytest.raises(ReceiptError, match="SafeMode"):
        assemble_closed_experience_provider_bundle(
            sealed=sealed,
            topology=environment["topology"],
            **authorities,
        )


def test_unrelated_precomputed_expression_cannot_seal_prepared_evidence():
    environment = _environment()
    preparation = _prepare_ready(environment)
    prepared_event = preparation.events[0]
    changed_evidence = []
    extra_payloads = []
    for index, original in enumerate(prepared_event.evidence):
        changed_values = list(original.coordinates.as_tuple())
        changed_values[index] += Fraction(index + 1)
        changed = replace(
            original,
            evidence_id=f"{original.evidence_id}:unrelated",
            coordinates=type(original.coordinates)(*changed_values),
            evidence_receipt_sha256="0" * 64,
        )
        changed_payload = changed.canonical_receipt_payload()
        changed = replace(
            changed,
            evidence_receipt_sha256=receipt_sha256(changed_payload),
        )
        changed_evidence.append(changed)
        extra_payloads.append(changed_payload)

    unrelated_base = registry(
        *_payloads(preparation.receipt_registry),
        *extra_payloads,
    )
    unrelated_injection = sparse_map_inject(
        environment["topology"],
        tuple(changed_evidence),
        prepared_event.source_time_end,
        unrelated_base,
    )
    unrelated_event = ClosedExperienceEvidenceEvent(
        source_time_start=prepared_event.source_time_start,
        source_time_end=prepared_event.source_time_end,
        evidence=tuple(changed_evidence),
        injection=unrelated_injection,
    )
    unrelated_expression, expression_registry = _expression(
        topology=environment["topology"],
        events=(unrelated_event,),
        base_registry=registry(
            *_payloads(unrelated_base),
            unrelated_injection.receipt_payload,
        ),
    )
    unrelated_recognition, recognition_registry = _recognized(
        unrelated_expression,
        expression_registry,
    )

    with pytest.raises(
        ReceiptError,
        match="does not bind prepared injection",
    ):
        seal_closed_experience(
            experience_id="unrelated-expression",
            structural_time_unit="structural_second",
            preparation=preparation,
            topology=environment["topology"],
            l5_governance=environment["l5"],
            expression=unrelated_expression,
            recognition=unrelated_recognition,
            receipt_registry=recognition_registry,
        )

def test_self_generated_recall_assembles_at_zero_without_erasing_cited_senses_after_restart():
    environment, preparation, _expression_value, _recognition, sealed = (
        _sealed_environment()
    )
    authorities = _actual_authorities(
        topology=environment["topology"],
        sealed=sealed,
        origin_kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
    )
    restarted = ReceiptRegistry(
        authorities["receipt_registry"].profile_binding_sha256,
        tuple(authorities["receipt_registry"].records),
    )
    authorities["receipt_registry"] = restarted

    result = assemble_closed_experience_provider_bundle(
        sealed=sealed,
        topology=environment["topology"],
        **authorities,
    )

    assert isinstance(result, ClosedExperienceProviderBundle)
    assert (
        result.experience_origin.kind
        is ExperienceOriginKind.SELF_GENERATED_RECALL
    )
    assert result.event_support.state is EventSupportState.ZERO
    assert result.event_support.exact_r_event == Fraction(0)
    assert result.evidence == preparation.evidence
    assert result.event_support_evaluation.intervals
    interval = result.event_support_evaluation.intervals[-1]
    assert interval.current_port_evidence_receipt_sha256s
    assert interval.exact_fresh_source_energy == Fraction(0)
    assert interval.exact_p_joint == Fraction(0)


def test_recall_origin_kind_tamper_is_rejected_by_closed_experience_assembly():
    environment, _preparation, _expression_value, _recognition, sealed = (
        _sealed_environment()
    )
    authorities = _actual_authorities(
        topology=environment["topology"],
        sealed=sealed,
        origin_kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
    )
    authorities["experience_origin"] = replace(
        authorities["experience_origin"],
        kind=ExperienceOriginKind.FRESH_EXTERNAL,
    )

    with pytest.raises(ReceiptError, match="origin authority receipt"):
        assemble_closed_experience_provider_bundle(
            sealed=sealed,
            topology=environment["topology"],
            **authorities,
        )

