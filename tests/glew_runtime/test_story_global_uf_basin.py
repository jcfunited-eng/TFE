from __future__ import annotations

from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.closed_experience import (
    L5ApplicabilityRule,
    MountedL5GovernanceProfile,
    l5_governance_profile_receipt_payload,
)
from dsf_ai_service.glew_runtime.commit import (
    ApplicabilityState,
    GovernedFact,
    L6ScopeAuthority,
    evaluate_pending_global_uf_conjunction,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
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
from dsf_ai_service.glew_runtime.expression_modes import create_empty_expression_mode_bank
from dsf_ai_service.glew_runtime.expressions import (
    PrecisionScheduleAuthority,
    precision_schedule_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.field import (
    ExactComplex,
    ExactFieldState,
    MountedFieldTopology,
    PortFiber,
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
)
from dsf_ai_service.glew_runtime.global_uf import (
    MountedPreWindowState,
    pre_window_state_receipt_payload,
)
from dsf_ai_service.glew_runtime.l6 import (
    ActiveLaneState,
    L6Lane,
    L6PredicateInputs,
    evaluate_l6,
)
from dsf_ai_service.glew_runtime.language import (
    MountedTypedLanguageKernelBinding,
    TypedLanguageEvent,
    TypedLanguageState,
    build_typed_language_frozen_kernel_input,
    typed_interface_receipt_payload,
    typed_language_event_receipt_payload,
    typed_language_kernel_binding_receipt_payload,
    typed_phase_calibration_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import ReceiptError, ReceiptRecord, ReceiptRegistry, receipt_sha256
from dsf_ai_service.glew_runtime.operators import (
    MountedResonanceGraph,
    MountedSupportDomain,
    RequiredEdge,
    resonance_graph_receipt_payload,
    support_domain_receipt_payload,
)
from dsf_ai_service.glew_runtime.safe_mode import (
    IntegrityFact,
    IntegrityFactState,
    MountedSafeModeScope,
    evaluate_safe_mode,
    integrity_fact_receipt_payload,
    safe_mode_scope_receipt_payload,
)
from dsf_ai_service.glew_runtime.story_global_uf_basin import (
    MountedStoryGlobalUFBasinProfile,
    MountedStoryReplayAuthorities,
    StoryGlobalUFPreparation,
    evaluate_story_global_uf,
    prepare_story_global_uf,
    story_global_uf_basin_profile_receipt_payload,
)
from tests.glew_runtime.test_story_native_replay import _mounted_five_sense_runtime


def _extend(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    values = {item.digest: item.payload for item in registry.records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        assert values.get(digest, payload) == payload
        values[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, values[key]) for key in sorted(values)),
    )


def _mounted_six_lane_preparation():
    story_profile, boundary, old_pre, story_runtime, sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    interface_id = "story-six-lane-typed-interface"
    interface_payload = typed_interface_receipt_payload(interface_id)
    phase_id = "story-six-lane-typed-phase"
    phase_kappa = Fraction(1, 7)
    phase_payload = typed_phase_calibration_receipt_payload(phase_id, phase_kappa)
    genesis_payload = b'{"schema":"glew.test.story_six_lane_typed_genesis.v1"}'
    derivation_payload = b'{"equation":"F=1+s/2","schema":"glew.test.story_six_lane_kernel_derivation.v1"}'
    binding_payload = typed_language_kernel_binding_receipt_payload(
        adapter_id="story-six-lane-typed-adapter",
        interface_id=interface_id,
        interface_receipt_sha256=receipt_sha256(interface_payload),
        phase_calibration_receipt_sha256=receipt_sha256(phase_payload),
        derivation_receipt_sha256=receipt_sha256(derivation_payload),
    )
    binding = MountedTypedLanguageKernelBinding(
        "story-six-lane-typed-adapter",
        interface_id,
        receipt_sha256(interface_payload),
        receipt_sha256(phase_payload),
        receipt_sha256(derivation_payload),
        receipt_sha256(binding_payload),
    )
    event_payload = typed_language_event_receipt_payload(
        text="\n",
        event_id="story-six-lane-newline",
        interface_id=interface_id,
        source_epoch="story-six-lane-language-epoch",
        valid_sample_times=story_profile.grid.timestamps,
    )
    event = TypedLanguageEvent.from_text(
        text="\n",
        event_id="story-six-lane-newline",
        interface_id=interface_id,
        source_epoch="story-six-lane-language-epoch",
        valid_sample_times=story_profile.grid.timestamps,
        interface_receipt_sha256=receipt_sha256(interface_payload),
        event_receipt_sha256=receipt_sha256(event_payload),
        phase_calibration_id=phase_id,
        phase_kappa=phase_kappa,
        phase_calibration_receipt_sha256=receipt_sha256(phase_payload),
    )
    state = TypedLanguageState(
        phase_id,
        "story-six-lane-language-epoch",
        -1,
        sensor_states[0].last_timestamp,
        Fraction(0),
        receipt_sha256(genesis_payload),
    )
    registry = _extend(
        registry,
        interface_payload,
        phase_payload,
        genesis_payload,
        derivation_payload,
        binding_payload,
        event_payload,
    )
    typed = build_typed_language_frozen_kernel_input(
        event=event,
        initial_state=state,
        kernel_binding=binding,
        receipt_registry=registry,
    )
    registry = typed.receipt_registry
    fibers = (
        PortFiber(L6Lane.LANGUAGE.value, typed.stream.port_id),
        *story_profile.topology.ordered_port_fibers,
    )
    topology_payload = field_topology_receipt_payload("story-six-lane-topology", fibers)
    topology = MountedFieldTopology(
        "story-six-lane-topology", fibers, receipt_sha256(topology_payload)
    )
    keys = tuple(item.key for item in fibers)
    support_payload = support_domain_receipt_payload("story-six-lane-support", keys)
    support = MountedSupportDomain(
        "story-six-lane-support", keys, receipt_sha256(support_payload)
    )
    edges = tuple(
        RequiredEdge(left, right) for left, right in zip(keys[:-1], keys[1:], strict=True)
    )
    graph_payload = resonance_graph_receipt_payload("story-six-lane-resonance", edges)
    graph = MountedResonanceGraph(
        "story-six-lane-resonance", edges, receipt_sha256(graph_payload)
    )
    initial_payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256,
        sensor_states[0].last_timestamp,
        tuple(ExactComplex(Fraction(0)) for _ in range(topology.dimension)),
    )
    initial = ExactFieldState(
        topology.authority_receipt_sha256,
        sensor_states[0].last_timestamp,
        tuple(ExactComplex(Fraction(0)) for _ in range(topology.dimension)),
        receipt_sha256(initial_payload),
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="story-six-lane-expression-precision",
        maximum_precision_bits=2048,
    )
    precision = PrecisionScheduleAuthority(
        "story-six-lane-expression-precision", 2048, receipt_sha256(precision_payload)
    )
    physical_payload = b'{"schema":"glew.test.story_six_lane_exact_field_physics.v1"}'
    rules = tuple(
        L5ApplicabilityRule(fiber.lane_id, fiber.port_id, fact, ApplicabilityState.REQUIRED)
        for fiber in fibers
        for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
    )
    l5_payload = l5_governance_profile_receipt_payload(
        profile_id="story-six-lane-L5",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        rules=rules,
    )
    l5 = MountedL5GovernanceProfile(
        "story-six-lane-L5", topology.authority_receipt_sha256, rules, receipt_sha256(l5_payload)
    )
    registry = _extend(
        registry,
        topology_payload,
        support_payload,
        graph_payload,
        initial_payload,
        precision_payload,
        physical_payload,
        l5_payload,
    )
    mode_bank = create_empty_expression_mode_bank(
        topology=topology, precision_authority=precision, receipt_registry=registry
    )
    registry = _extend(registry, mode_bank.receipt_payload)
    pre_payload = pre_window_state_receipt_payload(
        state_id="story-six-lane-pre-window",
        chemistry_state_receipt_sha256=old_pre.chemistry_state_receipt_sha256,
        field_state_receipt_sha256=initial.authority_receipt_sha256,
        mode_state_receipt_sha256=mode_bank.receipt_sha256,
        memory_state_receipt_sha256=old_pre.memory_state_receipt_sha256,
        l6_state_receipt_sha256=old_pre.l6_state_receipt_sha256,
    )
    pre_window = MountedPreWindowState(
        "story-six-lane-pre-window",
        old_pre.chemistry_state_receipt_sha256,
        initial.authority_receipt_sha256,
        mode_bank.receipt_sha256,
        old_pre.memory_state_receipt_sha256,
        old_pre.l6_state_receipt_sha256,
        receipt_sha256(pre_payload),
    )
    registry = _extend(registry, pre_payload)
    profile_payload = story_global_uf_basin_profile_receipt_payload(
        profile_id="story-six-lane-global-uf-profile",
        story_replay_profile_receipt_sha256=story_profile.authority_receipt_sha256,
        physical_profile_receipt_sha256=receipt_sha256(physical_payload),
        initial_field_state_receipt_sha256=initial.authority_receipt_sha256,
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source_time_unit="story-structural-time",
        max_connected_component_dimension=1,
        field_precision_bits=128,
        precision_authority_receipt_sha256=precision.authority_receipt_sha256,
        mode_bank_receipt_sha256=mode_bank.receipt_sha256,
        l5_governance_receipt_sha256=l5.authority_receipt_sha256,
    )
    profile = MountedStoryGlobalUFBasinProfile(
        "story-six-lane-global-uf-profile",
        story_profile.authority_receipt_sha256,
        receipt_sha256(physical_payload),
        initial,
        Fraction(1),
        (),
        (),
        "story-structural-time",
        1,
        128,
        precision,
        mode_bank,
        l5,
        receipt_sha256(profile_payload),
        profile_payload,
    )
    registry = _extend(registry, profile_payload)
    preparation = prepare_story_global_uf(
        story_profile=story_profile,
        basin_profile=profile,
        boundary=boundary,
        pre_window_state=pre_window,
        story_runtime=story_runtime,
        sensor_states=sensor_states,
        typed_input=typed,
        topology=topology,
        grid=story_profile.grid,
        support_domain=support,
        resonance_graph=graph,
        resonance_operator=story_profile.resonance_operator,
        receipt_registry=registry,
    )
    return (
        preparation,
        topology,
        pre_window,
        profile,
        boundary,
        typed,
        preparation.receipt_registry,
    )


def _mount_authorities(
    *,
    preparation: StoryGlobalUFPreparation,
    topology: MountedFieldTopology,
    profile: MountedStoryGlobalUFBasinProfile,
    boundary,
    origin_kind: ExperienceOriginKind,
    registry: ReceiptRegistry,
):
    scope_source = profile.authority_receipt_sha256
    fact_id = "authenticated-complete-six-lane-context"
    scope_payload = safe_mode_scope_receipt_payload(
        scope_id="story-six-lane-safe-mode-scope",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        required_fact_ids=(fact_id,),
        source_profile_receipt_sha256=scope_source,
    )
    scope = MountedSafeModeScope(
        "story-six-lane-safe-mode-scope",
        topology.authority_receipt_sha256,
        (fact_id,),
        scope_source,
        receipt_sha256(scope_payload),
    )
    memory = None
    payloads = [scope_payload]
    if origin_kind is ExperienceOriginKind.EXPLICIT_STORY_EMULATOR:
        derivation = b'{"schema":"glew.test.story_six_lane_memory_energy_derivation.v1"}'
        memory_payload = memory_energy_authority_receipt_payload(
            authority_id="story-six-lane-memory-energy",
            energy_unit_id="story-memory-energy-unit",
            exact_memory_energy=Fraction(1),
            derivation_receipt_sha256=receipt_sha256(derivation),
            physical_profile_receipt_sha256=profile.physical_profile_receipt_sha256,
        )
        memory = MemoryEnergyAuthority(
            "story-six-lane-memory-energy",
            "story-memory-energy-unit",
            Fraction(1),
            receipt_sha256(derivation),
            profile.physical_profile_receipt_sha256,
            receipt_sha256(memory_payload),
        )
        payloads.extend((derivation, memory_payload))
        origin_source = boundary.authority_receipt_sha256
    else:
        archive = b'{"schema":"glew.test.story_six_lane_recall_archive.v1"}'
        payloads.append(archive)
        origin_source = receipt_sha256(archive)
    registry = _extend(registry, *payloads)
    mounted = []
    completeness = {item.lane: item.receipt_sha256 for item in preparation.lane_completeness_receipts}
    for context in preparation.contexts:
        seal_digest = context.sealed.closed_experience.authority_receipt_sha256
        origin_payload = experience_origin_authority_receipt_payload(
            origin_id=f"{context.request.request_id}:origin",
            kind=origin_kind,
            profile_binding_sha256=registry.profile_binding_sha256,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            closed_experience_receipt_sha256=seal_digest,
            source_authority_receipt_sha256=origin_source,
        )
        origin = ExperienceOriginAuthority(
            f"{context.request.request_id}:origin",
            origin_kind,
            registry.profile_binding_sha256,
            topology.authority_receipt_sha256,
            seal_digest,
            origin_source,
            receipt_sha256(origin_payload),
        )
        fact_payload = integrity_fact_receipt_payload(
            fact_id=fact_id,
            state=IntegrityFactState.CLEAR,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            closed_experience_receipt_sha256=seal_digest,
            source_operator_receipt_sha256=context.preparation.receipt_sha256,
        )
        fact = IntegrityFact(
            fact_id,
            IntegrityFactState.CLEAR,
            topology.authority_receipt_sha256,
            seal_digest,
            context.preparation.receipt_sha256,
            receipt_sha256(fact_payload),
        )
        registry = _extend(registry, origin_payload, fact_payload)
        safe = evaluate_safe_mode(
            authority_id=f"{context.request.request_id}:safe-mode",
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            closed_experience_receipt_sha256=seal_digest,
            scope=scope,
            facts=(fact,),
            receipt_registry=registry,
        )
        registry = _extend(registry, *safe.generated_receipt_payloads)
        event = evaluate_event_support(
            authority_id=f"{context.request.request_id}:R-event",
            origin=origin,
            topology=topology,
            closed_experience_receipt_sha256=seal_digest,
            expression=context.expression_facts.expression,
            memory_energy=memory,
            receipt_registry=registry,
        )
        registry = _extend(registry, *event.generated_receipt_payloads)
        evidence = {item.lane_id: item for item in context.preparation.evidence}
        predicates = L6PredicateInputs(
            tuple(
                ActiveLaneState(
                    lane,
                    evidence[lane.value].coordinates.U_star_k,
                    True,
                    completeness[lane],
                )
                for lane in L6Lane
            ),
            True,
        )
        l6 = evaluate_l6(preparation.fixed42_stack, predicates, registry)
        l6_payload = l6_evaluation_receipt_payload(l6)
        l6_scope_payload = l6_scope_authority_receipt_payload(
            authority_id=f"{context.request.request_id}:L6-scope",
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            closed_experience_receipt_sha256=seal_digest,
            l6_evaluation_receipt_sha256=receipt_sha256(l6_payload),
        )
        l6_scope = L6ScopeAuthority(
            f"{context.request.request_id}:L6-scope",
            topology.authority_receipt_sha256,
            seal_digest,
            receipt_sha256(l6_payload),
            receipt_sha256(l6_scope_payload),
        )
        registry = _extend(registry, l6_payload, l6_scope_payload)
        pending = evaluate_pending_global_uf_conjunction(
            topology=topology,
            recognition=context.expression_facts.recognition,
            l6_evaluation=l6,
            l6_scope=l6_scope,
            closed_experience=context.sealed.closed_experience,
            safe_mode=safe.authority,
            event_support=event.authority,
            evidence=context.sealed.evidence,
            l5_applicability=context.sealed.l5_applicability,
            receipt_registry=registry,
        )
        registry = _extend(registry, pending.receipt_payload)
        mounted.append(
            MountedStoryReplayAuthorities(
                context.request.receipt_sha256,
                origin,
                scope,
                (fact,),
                safe,
                memory,
                event,
                predicates,
                l6,
                l6_scope,
                pending,
            )
        )
    return tuple(mounted), registry


def test_two_stage_story_preparation_keeps_all_six_lanes_and_unique_seals():
    preparation, topology, *_ = _mounted_six_lane_preparation()

    assert len(topology.ordered_port_fibers) == 6
    assert len(preparation.contexts) == 11
    assert tuple(item.lane for item in preparation.lane_completeness_receipts) == tuple(L6Lane)
    assert preparation.language_replay.contingent_cone.fixed42_stack.rows
    expected_keys = {fiber.key for fiber in topology.ordered_port_fibers}
    assert all(
        {item.key for item in context.preparation.evidence} == expected_keys
        for context in preparation.contexts
    )
    assert len(
        {
            context.sealed.closed_experience.authority_receipt_sha256
            for context in preparation.contexts
        }
    ) == len(preparation.contexts)


def test_fresh_story_fails_closed_when_exact_event_geometry_is_zero():
    preparation, topology, pre_window, profile, boundary, _, registry = (
        _mounted_six_lane_preparation()
    )
    mounted, registry = _mount_authorities(
        preparation=preparation,
        topology=topology,
        profile=profile,
        boundary=boundary,
        origin_kind=ExperienceOriginKind.EXPLICIT_STORY_EMULATOR,
        registry=registry,
    )
    assert mounted[0].event_support_evaluation.exact_r_event == 0
    with pytest.raises(ReceiptError, match="fresh story base lacks positive exact R_event"):
        evaluate_story_global_uf(
            authority_id="story-six-lane-fresh-global-uf",
            preparation=preparation,
            mounted_authorities=mounted,
            topology=topology,
            pre_window_state=pre_window,
            receipt_registry=registry,
        )


