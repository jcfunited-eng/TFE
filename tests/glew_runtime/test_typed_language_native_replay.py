from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.field import (
    MountedFieldTopology,
    PortFiber,
    field_topology_receipt_payload,
)
from dsf_ai_service.glew_runtime.l6 import LANE_ORDER, exact_rank_receipt
from dsf_ai_service.glew_runtime.language import (
    MountedTypedLanguageKernelBinding,
    TypedLanguageEvent,
    TypedLanguageState,
    build_typed_language_frozen_kernel_input,
    encode_balanced_ternary_scalar,
    typed_interface_receipt_payload,
    typed_language_event_receipt_payload,
    typed_language_kernel_binding_receipt_payload,
    typed_phase_calibration_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    RequiredEdge,
    causal_grid_receipt_payload,
    resonance_graph_receipt_payload,
    support_domain_receipt_payload,
)
from dsf_ai_service.glew_runtime.physical_l6_tangents import ExactL4Response
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryPhysicalBoundaryEvent,
    StoryPhysicalBoundaryObservation,
    story_boundary_observation_receipt_payload,
)
from dsf_ai_service.glew_runtime.story_native_replay import (
    MountedAuthenticatedClosedStoryBoundary,
    MountedStoryNativeReplayProfile,
    StoryNativeReplayStatus,
    authenticated_closed_story_boundary_receipt_payload,
    execute_story_native_replay,
    story_native_replay_profile_receipt_payload,
)
from dsf_ai_service.glew_runtime.typed_language_native_replay import (
    TYPED_LANGUAGE_DIRECTION_ROW_OPERATOR_ID,
    TypedLanguageNativeReplayResult,
    execute_typed_language_native_replay,
)
from tests.glew_runtime.test_story_native_replay import (
    _canonical,
    _mounted_five_sense_runtime,
)


def _registry_with_payloads(
    *,
    profile_payload: bytes,
    registry: ReceiptRegistry,
    payloads: tuple[bytes, ...],
) -> ReceiptRegistry:
    """Mount exact bytes once; profile binding is never duplicated."""

    mounted = {record.digest: record.payload for record in registry.records}
    for payload in (profile_payload, *payloads):
        digest = receipt_sha256(payload)
        if digest in mounted and mounted[digest] != payload:
            raise AssertionError("test fixture receipt digest collision")
        mounted[digest] = payload
    return ReceiptRegistry(
        receipt_sha256(profile_payload),
        tuple(
            ReceiptRecord(digest, mounted[digest]) for digest in sorted(mounted)
        ),
    )


def _merge_registry(
    registry: ReceiptRegistry,
    addition: ReceiptRegistry,
) -> ReceiptRegistry:
    assert registry.profile_binding_sha256 == addition.profile_binding_sha256
    mounted = {record.digest: record.payload for record in registry.records}
    for record in addition.records:
        assert mounted.get(record.digest, record.payload) == record.payload
        mounted[record.digest] = record.payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(
            ReceiptRecord(digest, mounted[digest]) for digest in sorted(mounted)
        ),
    )


def _fourteen_step_story():
    (
        old_profile,
        _old_boundary,
        pre_window,
        story_runtime,
        sensor_states,
        old_registry,
    ) = _mounted_five_sense_runtime()
    timestamps = tuple(Fraction(index + 1) for index in range(14))
    weights = tuple(Fraction(1) for _ in timestamps)
    grid_payload = causal_grid_receipt_payload(
        "typed-cone-fourteen-grid",
        timestamps,
        weights,
    )
    grid = CausalGrid(
        "typed-cone-fourteen-grid",
        timestamps,
        weights,
        receipt_sha256(grid_payload),
    )
    profile_payload = story_native_replay_profile_receipt_payload(
        profile_id="typed-cone-five-sense-native-replay",
        provider_id=old_profile.provider_id,
        topology_authority_receipt_sha256=(
            old_profile.topology.authority_receipt_sha256
        ),
        grid_receipt_sha256=grid.grid_receipt_sha256,
        support_domain_receipt_sha256=(
            old_profile.support_domain.authority_receipt_sha256
        ),
        resonance_graph_receipt_sha256=(
            old_profile.resonance_graph.authority_receipt_sha256
        ),
        resonance_operator_receipt_sha256=(
            old_profile.resonance_operator.authority_receipt_sha256
        ),
        kernel_adapter_id=old_profile.kernel_adapter_id,
        kernel_adapter_profile_receipt_sha256=(
            old_profile.kernel_adapter_profile_receipt_sha256
        ),
        ports=old_profile.ports,
    )
    profile = MountedStoryNativeReplayProfile(
        profile_id="typed-cone-five-sense-native-replay",
        provider_id=old_profile.provider_id,
        topology=old_profile.topology,
        grid=grid,
        support_domain=old_profile.support_domain,
        resonance_graph=old_profile.resonance_graph,
        resonance_operator=old_profile.resonance_operator,
        kernel_adapter_id=old_profile.kernel_adapter_id,
        kernel_adapter_profile_receipt_sha256=(
            old_profile.kernel_adapter_profile_receipt_sha256
        ),
        ports=old_profile.ports,
        authority_receipt_sha256=receipt_sha256(profile_payload),
        authority_receipt_payload=profile_payload,
    )
    event_id = "typed-cone-authenticated-five-sense-boundary"
    observations = []
    boundary_payloads = []
    for port in profile.ports:
        provenance = _canonical(
            {
                "event_id": event_id,
                "port_id": port.story_port_id,
                "schema": "glew.test.typed_cone_boundary_provenance.v1",
            }
        )
        observation_id = f"{event_id}:{port.story_port_id}"
        payload = story_boundary_observation_receipt_payload(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port.story_port_id,
            source_time_start=Fraction(0),
            source_time_end=Fraction(14),
            signed_native_flux=port.flux_for_code(port.base_raw_code),
            native_flux_unit=port.native_flux_unit,
            provenance_receipt_sha256=receipt_sha256(provenance),
        )
        observations.append(
            StoryPhysicalBoundaryObservation(
                event_id=event_id,
                observation_id=observation_id,
                port_id=port.story_port_id,
                source_time_start=Fraction(0),
                source_time_end=Fraction(14),
                signed_native_flux=port.flux_for_code(port.base_raw_code),
                native_flux_unit=port.native_flux_unit,
                provenance_receipt_sha256=receipt_sha256(provenance),
                provenance_receipt_payload=provenance,
                observation_receipt_sha256=receipt_sha256(payload),
                observation_receipt_payload=payload,
            )
        )
        boundary_payloads.extend((provenance, payload))
    event = StoryPhysicalBoundaryEvent(event_id, tuple(observations))
    boundary_payload = authenticated_closed_story_boundary_receipt_payload(
        boundary_id="typed-cone-mounted-five-sense-boundary",
        event=event,
        profile=profile,
    )
    boundary = MountedAuthenticatedClosedStoryBoundary(
        "typed-cone-mounted-five-sense-boundary",
        event,
        profile.authority_receipt_sha256,
        receipt_sha256(boundary_payload),
        boundary_payload,
    )
    registry = _registry_with_payloads(
        profile_payload=profile_payload,
        registry=old_registry,
        payloads=(
            grid_payload,
            profile_payload,
            *boundary_payloads,
            boundary_payload,
        ),
    )
    results = tuple(
        execute_story_native_replay(
            target_lane=port.lane,
            target_field_port_id=port.field_port_id,
            profile=profile,
            boundary=boundary,
            pre_window_state=pre_window,
            story_runtime=story_runtime,
            sensor_states=sensor_states,
            receipt_registry=registry,
        )
        for port in profile.ports
    )
    assert all(value.status is StoryNativeReplayStatus.READY for value in results), [
        value.reason for value in results
    ]
    for result in results:
        registry = _merge_registry(registry, result.receipt_registry)
    return profile, pre_window, results, registry


def _typed_character(
    *,
    text: str,
    registry: ReceiptRegistry,
    timestamps: tuple[Fraction, ...],
):
    assert len(text) == 1
    slug = f"u{ord(text):06x}"
    interface_id = f"typed-cone-{slug}-interface"
    interface_payload = typed_interface_receipt_payload(interface_id)
    phase_id = f"typed-cone-{slug}-phase"
    phase_kappa = Fraction(1, 7)
    phase_payload = typed_phase_calibration_receipt_payload(
        phase_id,
        phase_kappa,
    )
    genesis_payload = _canonical(
        {"schema": "glew.test.typed_cone_genesis.v1", "slug": slug}
    )
    derivation_payload = _canonical(
        {
            "equation": "F=1+s/2",
            "schema": "glew.test.typed_cone_kernel_derivation.v1",
            "slug": slug,
        }
    )
    binding_payload = typed_language_kernel_binding_receipt_payload(
        adapter_id=f"typed-cone-{slug}-adapter",
        interface_id=interface_id,
        interface_receipt_sha256=receipt_sha256(interface_payload),
        phase_calibration_receipt_sha256=receipt_sha256(phase_payload),
        derivation_receipt_sha256=receipt_sha256(derivation_payload),
    )
    binding = MountedTypedLanguageKernelBinding(
        f"typed-cone-{slug}-adapter",
        interface_id,
        receipt_sha256(interface_payload),
        receipt_sha256(phase_payload),
        receipt_sha256(derivation_payload),
        receipt_sha256(binding_payload),
    )
    trits = encode_balanced_ternary_scalar(ord(text))
    valid_times = tuple(
        timestamp
        for trit, timestamp in zip(trits, timestamps, strict=True)
        if trit.valid
    )
    event_id = f"typed-cone-{slug}-event"
    source_epoch = f"typed-cone-{slug}-epoch"
    event_payload = typed_language_event_receipt_payload(
        text=text,
        event_id=event_id,
        interface_id=interface_id,
        source_epoch=source_epoch,
        valid_sample_times=valid_times,
    )
    event = TypedLanguageEvent.from_text(
        text=text,
        event_id=event_id,
        interface_id=interface_id,
        source_epoch=source_epoch,
        valid_sample_times=valid_times,
        interface_receipt_sha256=receipt_sha256(interface_payload),
        event_receipt_sha256=receipt_sha256(event_payload),
        phase_calibration_id=phase_id,
        phase_kappa=phase_kappa,
        phase_calibration_receipt_sha256=receipt_sha256(phase_payload),
    )
    state = TypedLanguageState(
        phase_id,
        source_epoch,
        -1,
        Fraction(0),
        Fraction(0),
        receipt_sha256(genesis_payload),
    )
    profile_payload = registry.resolve(
        registry.profile_binding_sha256,
        "test profile binding",
    )
    mounted = _registry_with_payloads(
        profile_payload=profile_payload,
        registry=registry,
        payloads=(
            interface_payload,
            phase_payload,
            genesis_payload,
            derivation_payload,
            binding_payload,
            event_payload,
        ),
    )
    language = build_typed_language_frozen_kernel_input(
        event=event,
        initial_state=state,
        kernel_binding=binding,
        receipt_registry=mounted,
        complete_grid_times=timestamps,
    )
    return language, language.receipt_registry


@dataclass(frozen=True, slots=True)
class MountedReplay:
    profile: MountedStoryNativeReplayProfile
    pre_window: object
    sensor_results: tuple
    language: object
    topology: MountedFieldTopology
    support: MountedSupportDomain
    graph: MountedResonanceGraph
    replay: TypedLanguageNativeReplayResult
    registry: ReceiptRegistry


def _mounted_replay(text: str) -> MountedReplay:
    profile, pre_window, sensor_results, registry = _fourteen_step_story()
    language, registry = _typed_character(
        text=text,
        registry=registry,
        timestamps=profile.grid.timestamps,
    )
    slug = f"u{ord(text):06x}"
    fibers = (
        PortFiber("language", language.stream.port_id),
        *profile.topology.ordered_port_fibers,
    )
    topology_payload = field_topology_receipt_payload(
        f"typed-cone-{slug}-six-lane-topology",
        fibers,
    )
    topology = MountedFieldTopology(
        f"typed-cone-{slug}-six-lane-topology",
        fibers,
        receipt_sha256(topology_payload),
    )
    keys = tuple(value.key for value in fibers)
    support_payload = support_domain_receipt_payload(
        f"typed-cone-{slug}-six-lane-support",
        keys,
    )
    support = MountedSupportDomain(
        f"typed-cone-{slug}-six-lane-support",
        keys,
        receipt_sha256(support_payload),
    )
    edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(keys[:-1], keys[1:], strict=True)
    )
    graph_payload = resonance_graph_receipt_payload(
        f"typed-cone-{slug}-six-lane-resonance",
        edges,
    )
    graph = MountedResonanceGraph(
        f"typed-cone-{slug}-six-lane-resonance",
        edges,
        receipt_sha256(graph_payload),
    )
    profile_payload = registry.resolve(
        registry.profile_binding_sha256,
        "test profile binding",
    )
    registry = _registry_with_payloads(
        profile_payload=profile_payload,
        registry=registry,
        payloads=(topology_payload, support_payload, graph_payload),
    )
    base = sensor_results[0].executions[0]
    replay = execute_typed_language_native_replay(
        provider_id=profile.provider_id,
        typed_input=language,
        pre_window_state=pre_window,
        nonlanguage_streams=base.streams,
        nonlanguage_kernel_inputs=base.kernel_inputs,
        source_time_start=Fraction(0),
        topology=topology,
        grid=profile.grid,
        support_domain=support,
        resonance_graph=graph,
        resonance_operator=profile.resonance_operator,
        receipt_registry=registry,
    )
    return MountedReplay(
        profile,
        pre_window,
        sensor_results,
        language,
        topology,
        support,
        graph,
        replay,
        replay.receipt_registry,
    )


@pytest.fixture(scope="module")
def b_replay() -> MountedReplay:
    return _mounted_replay("b")


@pytest.fixture(scope="module")
def newline_replay() -> MountedReplay:
    return _mounted_replay("\n")


def _expected_adjacent_count(language) -> int:
    return sum(
        int(value.value > -1) + int(value.value < 1)
        for value in language.event.trits
        if value.valid
    )


def _assert_complete_exact_cone(mounted: MountedReplay) -> None:
    replay = mounted.replay
    cone = replay.contingent_cone
    expected_adjacent = _expected_adjacent_count(mounted.language)
    assert len(replay.executions) == 1 + expected_adjacent
    assert len(cone.directions) == expected_adjacent
    assert len(cone.rows) + len(cone.zero_directions) == expected_adjacent
    assert replay.bundle.branch_cell_proof is None
    assert tuple(value.case.receipt_sha256 for value in replay.executions[1:]) == tuple(
        value.case_receipt_sha256 for value in cone.directions
    )
    base = replay.executions[0].l4_response.as_tuple()
    for execution, direction in zip(
        replay.executions[1:],
        cone.directions,
        strict=True,
    ):
        expected = ExactL4Response(
            *tuple(
                (target - source) / execution.case.native_delta
                for source, target in zip(
                    base,
                    execution.l4_response.as_tuple(),
                    strict=True,
                )
            )
        )
        assert direction.secant == expected
        assert direction.source_branch_id == replay.executions[0].branch_id
        assert direction.source_cell_id == replay.executions[0].cell_id
        assert direction.target_branch_id == execution.branch_id
        assert direction.target_cell_id == execution.cell_id
        mounted.registry.resolve(
            direction.reversal_receipt_sha256,
            "test reversal receipt",
        )
        if any(expected.as_tuple()):
            assert direction.row is not None
            assert direction.zero_response_receipt_sha256 is None
            assert direction.row.native_coefficients == expected.as_tuple()
            assert len(direction.row.coefficients) == 42
            assert direction.row.coefficients[:7] == expected.as_tuple()
            assert not any(direction.row.coefficients[7:])
            assert (
                direction.row.provenance.operator_id
                == TYPED_LANGUAGE_DIRECTION_ROW_OPERATOR_ID
            )
        else:
            assert direction.row is None
            assert direction.zero_response_receipt_sha256 is not None
            mounted.registry.resolve(
                direction.zero_response_receipt_sha256,
                "test zero-response receipt",
            )
    assert cone.rank_receipt == exact_rank_receipt(cone.fixed42_stack)
    assert cone.rank_receipt.row_count == len(cone.rows)
    cone.verify(
        profile=replay.bundle.profile,
        pre_window_state=mounted.pre_window,
        cases=tuple(value.case for value in replay.executions),
        response_set=replay.bundle.response_set,
        receipt_registry=mounted.registry,
    )


def test_b_mounts_every_directed_trit_as_exact_contingent_geometry(
    b_replay: MountedReplay,
):
    assert b_replay.language.event.normalized_text == "b"
    assert len(b_replay.language.stream.samples) == 14
    assert sum(value.valid for value in b_replay.language.event.trits) == 5
    _assert_complete_exact_cone(b_replay)
    base_identity = (
        b_replay.replay.executions[0].branch_id,
        b_replay.replay.executions[0].cell_id,
    )
    assert any(
        (value.target_branch_id, value.target_cell_id) != base_identity
        for value in b_replay.replay.contingent_cone.directions
    )


def test_newline_preserves_padding_and_mounts_every_admissible_direction(
    newline_replay: MountedReplay,
):
    assert newline_replay.language.event.normalized_text == "\n"
    assert len(newline_replay.language.stream.samples) == 14
    assert sum(value.valid for value in newline_replay.language.event.trits) == 3
    assert tuple(
        value.relevance for value in newline_replay.language.stream.samples
    ).count(Fraction(0)) == 11
    _assert_complete_exact_cone(newline_replay)


def test_language_cone_preserves_the_complete_six_lane_field_without_fabrication(
    b_replay: MountedReplay,
):
    expected_keys = tuple(
        value.key for value in b_replay.topology.ordered_port_fibers
    )
    mounted_lanes = tuple(
        value.lane_id for value in b_replay.topology.ordered_port_fibers
    )
    assert len(mounted_lanes) == len(LANE_ORDER)
    assert set(mounted_lanes) == {value.value for value in LANE_ORDER}
    assert all(
        execution.preparation.topology_authority_receipt_sha256
        == b_replay.topology.authority_receipt_sha256
        for execution in b_replay.replay.executions
    )
    assert all(
        {value.key for value in execution.preparation.evidence}
        == set(expected_keys)
        for execution in b_replay.replay.executions
    )
    assert all(
        row.provenance.lane.value == "language"
        for row in b_replay.replay.contingent_cone.rows
    )
    assert all(
        result.bundle is not None
        and result.bundle.branch_cell_proof is None
        for result in b_replay.sensor_results
    )


def test_contingent_cone_is_bit_identical_after_restart(
    b_replay: MountedReplay,
):
    base = b_replay.sensor_results[0].executions[0]
    restarted_registry = ReceiptRegistry(
        b_replay.registry.profile_binding_sha256,
        tuple(b_replay.registry.records),
    )
    restarted = execute_typed_language_native_replay(
        provider_id=b_replay.profile.provider_id,
        typed_input=b_replay.language,
        pre_window_state=b_replay.pre_window,
        nonlanguage_streams=base.streams,
        nonlanguage_kernel_inputs=base.kernel_inputs,
        source_time_start=Fraction(0),
        topology=b_replay.topology,
        grid=b_replay.profile.grid,
        support_domain=b_replay.support,
        resonance_graph=b_replay.graph,
        resonance_operator=b_replay.profile.resonance_operator,
        receipt_registry=restarted_registry,
    )
    first = b_replay.replay
    assert first.contingent_cone == restarted.contingent_cone
    assert tuple(
        value.l0_l4_trace_receipt_sha256 for value in first.executions
    ) == tuple(
        value.l0_l4_trace_receipt_sha256 for value in restarted.executions
    )
    assert (
        first.contingent_cone.authority_receipt_sha256
        == restarted.contingent_cone.authority_receipt_sha256
    )


def test_direction_tamper_and_direction_omission_fail_closed(
    b_replay: MountedReplay,
):
    cone = b_replay.replay.contingent_cone
    first = cone.directions[0]
    altered_secant = replace(first.secant, D_k=first.secant.D_k + 1)
    altered_direction = replace(first, secant=altered_secant)
    altered = replace(
        cone,
        directions=(altered_direction, *cone.directions[1:]),
    )
    verification = dict(
        profile=b_replay.replay.bundle.profile,
        pre_window_state=b_replay.pre_window,
        cases=tuple(value.case for value in b_replay.replay.executions),
        response_set=b_replay.replay.bundle.response_set,
        receipt_registry=b_replay.registry,
    )
    with pytest.raises(ReceiptError):
        altered.verify(**verification)
    with pytest.raises(ReceiptError):
        replace(cone, directions=cone.directions[:-1]).verify(**verification)


def test_mismatched_capture_and_incomplete_six_lane_field_fail_closed(
    b_replay: MountedReplay,
):
    base = b_replay.sensor_results[0].executions[0]
    first = b_replay.language.stream.samples[0]
    altered_stream = replace(
        b_replay.language.stream,
        samples=(
            replace(first, signal=-first.signal),
            *b_replay.language.stream.samples[1:],
        ),
    )
    common = dict(
        provider_id=b_replay.profile.provider_id,
        pre_window_state=b_replay.pre_window,
        source_time_start=Fraction(0),
        topology=b_replay.topology,
        grid=b_replay.profile.grid,
        support_domain=b_replay.support,
        resonance_graph=b_replay.graph,
        resonance_operator=b_replay.profile.resonance_operator,
        receipt_registry=b_replay.registry,
    )
    with pytest.raises(ReceiptError):
        execute_typed_language_native_replay(
            typed_input=replace(b_replay.language, stream=altered_stream),
            nonlanguage_streams=base.streams,
            nonlanguage_kernel_inputs=base.kernel_inputs,
            **common,
        )
    with pytest.raises(ReceiptError):
        execute_typed_language_native_replay(
            typed_input=b_replay.language,
            nonlanguage_streams=base.streams[:-1],
            nonlanguage_kernel_inputs=base.kernel_inputs[:-1],
            **common,
        )



