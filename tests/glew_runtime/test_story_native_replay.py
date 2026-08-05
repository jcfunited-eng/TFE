from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from dsf_ai_service.glew_runtime.field import (
    MountedFieldTopology,
    PortFiber,
    field_topology_receipt_payload,
)
from dsf_ai_service.glew_runtime.global_uf import (
    MountedPreWindowState,
    pre_window_state_receipt_payload,
)
from dsf_ai_service.glew_runtime.l6 import (
    ActiveLaneState,
    L6EvaluationStatus,
    L6Lane,
    L6PredicateInputs,
    evaluate_l6,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
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
from dsf_ai_service.glew_runtime.physical_l6_tangents import (
    PhysicalTangentProductionStatus,
    produce_physical_l6_tangents,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    StoryPhysicalBoundaryEvent,
    StoryPhysicalBoundaryObservation,
    mount_story_chemistry,
    story_boundary_observation_receipt_payload,
)
from dsf_ai_service.glew_runtime.story_native_replay import (
    MountedAuthenticatedClosedStoryBoundary,
    MountedStoryNativeReplayProfile,
    MountedStorySensorState,
    StoryNativeReplayStatus,
    StorySensorPortAuthority,
    authenticated_closed_story_boundary_receipt_payload,
    execute_story_native_replay,
    story_native_replay_profile_receipt_payload,
    story_replay_chemistry_state_receipt_payload,
    story_sensor_port_authority_receipt_payload,
    story_sensor_state_receipt_payload,
)


FIXTURE = Path(__file__).parent / "fixtures" / "candidate_story_chemistry_manifest.json"
CANDIDATE_KEY = b"transparent candidate test key; never production authority"
CANDIDATE_KEY_ID = "candidate-test-hmac-key-not-production"

BASE_FLUX = {
    "sound": Fraction(1, 5),
    "smell": Fraction(1, 6),
    "taste": Fraction(-1, 7),
    "touch": Fraction(2, 9),
    "sight": Fraction(1, 4),
}
QUANTUM = {
    "sound": Fraction(1, 20),
    "smell": Fraction(1, 24),
    "taste": Fraction(1, 28),
    "touch": Fraction(1, 18),
    "sight": Fraction(1, 16),
}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _unique_payloads(payloads) -> tuple[bytes, ...]:
    values = {receipt_sha256(value): value for value in payloads}
    return tuple(values[digest] for digest in sorted(values))


def _merge_registries(*registries: ReceiptRegistry) -> ReceiptRegistry:
    profile_binding = registries[0].profile_binding_sha256
    records: dict[str, bytes] = {}
    for registry in registries:
        assert registry.profile_binding_sha256 == profile_binding
        for record in registry.records:
            assert records.get(record.digest, record.payload) == record.payload
            records[record.digest] = record.payload
    return ReceiptRegistry(
        profile_binding,
        tuple(ReceiptRecord(digest, records[digest]) for digest in sorted(records)),
    )


def _sensor_port(port) -> tuple[StorySensorPortAuthority, bytes, bytes]:
    lane = L6Lane(port.kernel_binding.lane_id)
    source = _canonical(
        {
            "port_id": port.port_id,
            "schema": "glew.story_native_replay.test_source_authority.v1",
        }
    )
    values = dict(
        lane=lane,
        story_port_id=port.port_id,
        field_port_id=port.port_id,
        scene_coordinate_id=f"scene-{port.port_id}",
        base_raw_code=0,
        minimum_raw_code=-1,
        maximum_raw_code=1,
        flux_at_code_zero=BASE_FLUX[lane.value],
        physical_quantum=QUANTUM[lane.value],
        native_flux_unit=port.native_signal_unit,
        signal_offset=Fraction(0),
        signal_per_native_flux=Fraction(1),
        response_growth=Fraction(1, 2),
        natural_decay=Fraction(1, 8),
        phase_kappa=Fraction(1, 3),
        source_epoch="candidate-five-sense-story-epoch-0",
        port_kind="authenticated_virtual_story_boundary",
        signal_physical_unit="dimensionless_story_response",
        boundary_source_authority_receipt_sha256=receipt_sha256(source),
    )
    payload = story_sensor_port_authority_receipt_payload(**values)
    return (
        StorySensorPortAuthority(
            **values,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
        source,
    )


def _boundary_observation(
    *, event_id: str, port: StorySensorPortAuthority
) -> tuple[StoryPhysicalBoundaryObservation, bytes, bytes]:
    provenance = _canonical(
        {
            "event_id": event_id,
            "port_id": port.story_port_id,
            "schema": "glew.story_native_replay.test_boundary_provenance.v1",
        }
    )
    observation_id = f"{event_id}:{port.story_port_id}"
    payload = story_boundary_observation_receipt_payload(
        event_id=event_id,
        observation_id=observation_id,
        port_id=port.story_port_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(3),
        signed_native_flux=port.flux_for_code(port.base_raw_code),
        native_flux_unit=port.native_flux_unit,
        provenance_receipt_sha256=receipt_sha256(provenance),
    )
    return (
        StoryPhysicalBoundaryObservation(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port.story_port_id,
            source_time_start=Fraction(0),
            source_time_end=Fraction(3),
            signed_native_flux=port.flux_for_code(port.base_raw_code),
            native_flux_unit=port.native_flux_unit,
            provenance_receipt_sha256=receipt_sha256(provenance),
            provenance_receipt_payload=provenance,
            observation_receipt_sha256=receipt_sha256(payload),
            observation_receipt_payload=payload,
        ),
        provenance,
        payload,
    )


def _mounted_five_sense_runtime():
    mounted = mount_story_chemistry(
        manifest_envelope_payload=FIXTURE.read_bytes(),
        trusted_authentication_key=CANDIDATE_KEY,
        expected_key_id=CANDIDATE_KEY_ID,
    )
    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    story_runtime = mounted.runtime
    assert tuple(port.kernel_binding.lane_id for port in story_runtime.manifest.ports) == (
        "sound",
        "smell",
        "taste",
        "touch",
        "sight",
    )

    mounted_ports = tuple(_sensor_port(value) for value in story_runtime.manifest.ports)
    ports = tuple(value[0] for value in mounted_ports)
    port_payloads = tuple(value[1] for value in mounted_ports)
    source_payloads = tuple(value[2] for value in mounted_ports)
    fibers = tuple(PortFiber(value.lane.value, value.field_port_id) for value in ports)
    topology_payload = field_topology_receipt_payload(
        "candidate-five-sense-story-topology", fibers
    )
    topology = MountedFieldTopology(
        "candidate-five-sense-story-topology",
        fibers,
        receipt_sha256(topology_payload),
    )
    grid_payload = causal_grid_receipt_payload(
        "candidate-five-sense-story-grid",
        (Fraction(1), Fraction(2), Fraction(3)),
        (Fraction(1), Fraction(1), Fraction(1)),
    )
    grid = CausalGrid(
        "candidate-five-sense-story-grid",
        (Fraction(1), Fraction(2), Fraction(3)),
        (Fraction(1), Fraction(1), Fraction(1)),
        receipt_sha256(grid_payload),
    )
    topology_keys = tuple(value.field_key for value in ports)
    support_payload = support_domain_receipt_payload(
        "candidate-five-sense-story-support", topology_keys
    )
    support = MountedSupportDomain(
        "candidate-five-sense-story-support",
        topology_keys,
        receipt_sha256(support_payload),
    )
    edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(topology_keys[:-1], topology_keys[1:], strict=True)
    )
    graph_payload = resonance_graph_receipt_payload(
        "candidate-five-sense-story-resonance", edges
    )
    graph = MountedResonanceGraph(
        "candidate-five-sense-story-resonance",
        edges,
        receipt_sha256(graph_payload),
    )
    resonance_payload = resonance_operator_receipt_payload(
        "candidate-five-sense-story-gamma-squared", 128
    )
    resonance = ResonanceOperatorAuthority(
        "candidate-five-sense-story-gamma-squared",
        128,
        receipt_sha256(resonance_payload),
    )
    adapter_payload = _canonical(
        {
            "adapter": "F=1+s/2; relevance identity",
            "schema": "glew.story_native_replay.test_kernel_adapter.v1",
        }
    )
    profile_payload = story_native_replay_profile_receipt_payload(
        profile_id="candidate-five-sense-story-native-replay",
        provider_id="candidate-five-sense-frozen-kernel-provider",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        grid_receipt_sha256=grid.grid_receipt_sha256,
        support_domain_receipt_sha256=support.authority_receipt_sha256,
        resonance_graph_receipt_sha256=graph.authority_receipt_sha256,
        resonance_operator_receipt_sha256=resonance.authority_receipt_sha256,
        kernel_adapter_id="candidate-exact-story-kernel-adapter",
        kernel_adapter_profile_receipt_sha256=receipt_sha256(adapter_payload),
        ports=ports,
    )
    profile = MountedStoryNativeReplayProfile(
        profile_id="candidate-five-sense-story-native-replay",
        provider_id="candidate-five-sense-frozen-kernel-provider",
        topology=topology,
        grid=grid,
        support_domain=support,
        resonance_graph=graph,
        resonance_operator=resonance,
        kernel_adapter_id="candidate-exact-story-kernel-adapter",
        kernel_adapter_profile_receipt_sha256=receipt_sha256(adapter_payload),
        ports=ports,
        authority_receipt_sha256=receipt_sha256(profile_payload),
        authority_receipt_payload=profile_payload,
    )

    sensor_states = []
    sensor_payloads = []
    for port in ports:
        payload = story_sensor_state_receipt_payload(
            field_port_id=port.field_port_id,
            source_epoch=port.source_epoch,
            last_source_index=-1,
            last_timestamp=Fraction(0),
            retained_signal=Fraction(0),
            phase_turns=Fraction(0),
            port_authority_receipt_sha256=port.authority_receipt_sha256,
        )
        sensor_states.append(
            MountedStorySensorState(
                field_port_id=port.field_port_id,
                source_epoch=port.source_epoch,
                last_source_index=-1,
                last_timestamp=Fraction(0),
                retained_signal=Fraction(0),
                phase_turns=Fraction(0),
                port_authority_receipt_sha256=port.authority_receipt_sha256,
                authority_receipt_sha256=receipt_sha256(payload),
            )
        )
        sensor_payloads.append(payload)
    sensor_states = tuple(sensor_states)
    chemistry_payload = story_replay_chemistry_state_receipt_payload(
        story_runtime=story_runtime, sensor_states=sensor_states
    )
    field_payload = _canonical({"schema": "test.pre_window_field_state.v1"})
    mode_payload = _canonical({"schema": "test.pre_window_mode_state.v1"})
    memory_payload = _canonical({"schema": "test.pre_window_memory_state.v1"})
    l6_payload = _canonical({"schema": "test.pre_window_l6_state.v1"})
    prewindow_payload = pre_window_state_receipt_payload(
        state_id="candidate-five-sense-pre-window",
        chemistry_state_receipt_sha256=receipt_sha256(chemistry_payload),
        field_state_receipt_sha256=receipt_sha256(field_payload),
        mode_state_receipt_sha256=receipt_sha256(mode_payload),
        memory_state_receipt_sha256=receipt_sha256(memory_payload),
        l6_state_receipt_sha256=receipt_sha256(l6_payload),
    )
    prewindow = MountedPreWindowState(
        "candidate-five-sense-pre-window",
        receipt_sha256(chemistry_payload),
        receipt_sha256(field_payload),
        receipt_sha256(mode_payload),
        receipt_sha256(memory_payload),
        receipt_sha256(l6_payload),
        receipt_sha256(prewindow_payload),
    )

    event_id = "candidate-authenticated-five-sense-boundary"
    mounted_observations = tuple(
        _boundary_observation(event_id=event_id, port=value) for value in ports
    )
    event = StoryPhysicalBoundaryEvent(
        event_id,
        tuple(value[0] for value in mounted_observations),
    )
    boundary_payload = authenticated_closed_story_boundary_receipt_payload(
        boundary_id="candidate-mounted-five-sense-boundary",
        event=event,
        profile=profile,
    )
    boundary = MountedAuthenticatedClosedStoryBoundary(
        "candidate-mounted-five-sense-boundary",
        event,
        profile.authority_receipt_sha256,
        receipt_sha256(boundary_payload),
        boundary_payload,
    )

    story_payloads = tuple(
        value.payload for value in story_runtime.receipt_registry.records
    )
    observation_payloads = tuple(
        payload
        for value in mounted_observations
        for payload in (value[1], value[2])
    )
    registry = ReceiptRegistry.from_payloads(
        profile_payload=profile_payload,
        receipt_payloads=_unique_payloads(
            (
                topology_payload,
                grid_payload,
                support_payload,
                graph_payload,
                resonance_payload,
                adapter_payload,
                *port_payloads,
                *source_payloads,
                *sensor_payloads,
                chemistry_payload,
                field_payload,
                mode_payload,
                memory_payload,
                l6_payload,
                prewindow_payload,
                *observation_payloads,
                boundary_payload,
                *story_payloads,
            )
        ),
    )
    return profile, boundary, prewindow, story_runtime, sensor_states, registry


def test_all_five_story_senses_replay_real_frozen_kernel_and_lock_fixed42():
    profile, boundary, prewindow, story_runtime, sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    results = tuple(
        execute_story_native_replay(
            target_lane=port.lane,
            target_field_port_id=port.field_port_id,
            profile=profile,
            boundary=boundary,
            pre_window_state=prewindow,
            story_runtime=story_runtime,
            sensor_states=sensor_states,
            receipt_registry=registry,
        )
        for port in profile.ports
    )

    assert all(value.status is StoryNativeReplayStatus.READY for value in results), [
        value.reason for value in results
    ]
    assert all(value.bundle is not None for value in results)
    assert all(value.bundle.branch_cell_proof is not None for value in results)
    assert all(len(value.executions) == 3 for value in results)
    assert tuple(value.bundle.profile.lane for value in results) == (
        L6Lane.SOUND,
        L6Lane.SMELL,
        L6Lane.TASTE,
        L6Lane.TOUCH,
        L6Lane.SIGHT,
    )

    combined = _merge_registries(*(value.receipt_registry for value in results))
    production = produce_physical_l6_tangents(
        bundles=tuple(value.bundle for value in results if value.bundle is not None),
        pre_window_state=prewindow,
        receipt_registry=combined,
    )
    assert production.status is PhysicalTangentProductionStatus.KNOWN, production.reason
    assert production.candidate_constraints is not None
    assert production.candidate_constraints.stack is not None
    completeness = {
        value.lane: value.receipt_sha256
        for value in production.lane_completeness_receipts
    }
    base_u_star = {
        value.bundle.profile.lane: value.executions[0].target_l4_response.U_star_k
        for value in results
        if value.bundle is not None
    }
    active_lanes = tuple(
        ActiveLaneState(lane, base_u_star[lane], True, completeness[lane])
        for lane in L6Lane
        if lane in completeness
    )
    evaluation = evaluate_l6(
        production.candidate_constraints.stack,
        L6PredicateInputs(active_lanes=active_lanes, disruption_clear=True),
        production.receipt_registry,
    )
    assert evaluation.status is L6EvaluationStatus.LOCK, evaluation.reason
    assert evaluation.rank_receipt.n_start == 42
    assert evaluation.rank_receipt.n_effective < 16

    restarted = execute_story_native_replay(
        target_lane=profile.ports[0].lane,
        target_field_port_id=profile.ports[0].field_port_id,
        profile=profile,
        boundary=boundary,
        pre_window_state=prewindow,
        story_runtime=story_runtime,
        sensor_states=sensor_states,
        receipt_registry=registry,
    )
    assert restarted.status is StoryNativeReplayStatus.READY, restarted.reason
    assert [
        value.target_l0_l4_trace_receipt_sha256
        for value in restarted.executions
    ] == [
        value.target_l0_l4_trace_receipt_sha256
        for value in results[0].executions
    ]
    assert story_runtime.states == mounted_states_at_zero(story_runtime)


def mounted_states_at_zero(story_runtime):
    assert all(value.source_time == 0 for value in story_runtime.states)
    return story_runtime.states
