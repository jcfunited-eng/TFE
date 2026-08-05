"""Stage 1 of the mounted six-lane runtime (governing spec section 9.2).

Proves the four foundational ``mount_*`` functions in
``dsf_ai_service/glew_runtime/six_lane_runtime_mount.py`` each produce a
real, ``.verify()``-passing authority -- not a fixture double -- and that
invalid or tampered inputs fail closed with ``ReceiptError``. The final
class of tests reuses the real, already-committed five-sense chemistry
fixture (``tests/glew_runtime/test_story_native_replay.py::
_mounted_five_sense_runtime``) to prove the mounted authorities compose with
the existing, already-tested ``compute_support_floor`` /
``compute_resonance_confirmation`` operators over a genuine topology and
genuine evidence -- not merely with each other in isolation.
"""

from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.commit import ApplicabilityState, GovernedFact
from dsf_ai_service.glew_runtime.expression_modes import ExpressionModeBank
from dsf_ai_service.glew_runtime.expressions import PrecisionScheduleAuthority
from dsf_ai_service.glew_runtime.field import (
    FIBER_DIMENSION,
    ExactComplex,
    ExactFieldState,
    MountedFieldTopology,
    PortFiber,
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
)
from dsf_ai_service.glew_runtime.global_uf import MountedPreWindowState
from dsf_ai_service.glew_runtime.l6 import L6Lane
from dsf_ai_service.glew_runtime.language import MountedTypedLanguageKernelBinding
from dsf_ai_service.glew_runtime.model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    RequiredEdge,
    ResonanceOperatorAuthority,
    compute_resonance_confirmation,
    compute_support_floor,
)
from dsf_ai_service.glew_runtime.six_lane_runtime_mount import (
    MountedSixLaneRuntime,
    extend_receipt_registry,
    mount_causal_grid,
    mount_expression_mode_bank,
    mount_field_topology,
    mount_l5_governance_profile,
    mount_precision_schedule_authority,
    mount_pre_window_state,
    mount_resonance_graph_and_operator,
    mount_six_lane_runtime,
    mount_story_global_uf_basin_profile,
    mount_story_sensor_states,
    mount_support_domain,
    mount_typed_language_kernel_binding,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    mount_story_chemistry,
)
from dsf_ai_service.glew_runtime.story_global_uf_basin import (
    MountedStoryGlobalUFBasinProfile,
)
from dsf_ai_service.glew_runtime.story_native_replay import (
    MountedStorySensorState,
    StorySensorPortAuthority,
    story_sensor_port_authority_receipt_payload,
)

from tests.glew_runtime.test_story_native_replay import (
    CANDIDATE_KEY,
    CANDIDATE_KEY_ID,
    FIXTURE,
    _mounted_five_sense_runtime,
    _sensor_port,
)


PROFILE_PAYLOAD = b'{"schema":"test.six_lane_runtime_mount.profile.v1"}'
CALIBRATION_PAYLOAD = b'{"schema":"test.six_lane_runtime_mount.calibration.v1"}'
RELEVANCE_PAYLOAD = b'{"schema":"test.six_lane_runtime_mount.relevance.v1"}'


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _base_registry() -> ReceiptRegistry:
    return ReceiptRegistry.from_payloads(profile_payload=PROFILE_PAYLOAD, receipt_payloads=())


def _small_topology(registry: ReceiptRegistry) -> tuple[MountedFieldTopology, ReceiptRegistry]:
    fibers = (
        PortFiber("touch", "left-hand"),
        PortFiber("sight", "left-eye"),
        PortFiber("sound", "left-ear"),
    )
    payload = field_topology_receipt_payload("six-lane-mount-test-topology", fibers)
    registry = extend_receipt_registry(registry, payload)
    topology = MountedFieldTopology(
        "six-lane-mount-test-topology", fibers, receipt_sha256(payload)
    )
    topology.verify(registry)
    return topology, registry


# ---------------------------------------------------------------------------
# extend_receipt_registry
# ---------------------------------------------------------------------------


def test_extend_receipt_registry_merges_new_payload_and_preserves_profile_binding():
    registry = _base_registry()
    payload = b'{"schema":"test.six_lane_runtime_mount.extend.v1"}'
    merged = extend_receipt_registry(registry, payload)
    assert merged.profile_binding_sha256 == registry.profile_binding_sha256
    assert merged.resolve(receipt_sha256(payload)) == payload
    # original registry is untouched (immutable merge, not in-place mutation)
    with pytest.raises(ReceiptError):
        registry.resolve(receipt_sha256(payload))


def test_extend_receipt_registry_is_idempotent_for_identical_bytes():
    registry = _base_registry()
    payload = b'{"schema":"test.six_lane_runtime_mount.extend.v1"}'
    once = extend_receipt_registry(registry, payload)
    twice = extend_receipt_registry(once, payload)
    assert len(twice.records) == len(once.records)


def test_extend_receipt_registry_rejects_non_registry_input():
    with pytest.raises(ReceiptError, match="mounted immutable receipt registry"):
        extend_receipt_registry(object(), b"irrelevant")  # type: ignore[arg-type]


def test_extend_receipt_registry_rejects_empty_payload():
    with pytest.raises(ReceiptError, match="nonempty exact bytes"):
        extend_receipt_registry(_base_registry(), b"")


# ---------------------------------------------------------------------------
# mount_precision_schedule_authority
# ---------------------------------------------------------------------------


def test_precision_schedule_authority_mounts_and_verifies():
    registry = _base_registry()
    authority, registry = mount_precision_schedule_authority(
        authority_id="test-precision-authority",
        maximum_precision_bits=256,
        receipt_registry=registry,
    )
    assert isinstance(authority, PrecisionScheduleAuthority)
    assert authority.maximum_precision_bits == 256
    authority.verify(registry)  # independent re-verification, not just construction


def test_precision_schedule_authority_rejects_nonpositive_maximum_bits():
    with pytest.raises(ReceiptError, match="positive integer"):
        mount_precision_schedule_authority(
            authority_id="test-precision-authority",
            maximum_precision_bits=0,
            receipt_registry=_base_registry(),
        )


def test_precision_schedule_authority_rejects_boolean_maximum_bits():
    with pytest.raises(ReceiptError, match="positive integer"):
        mount_precision_schedule_authority(
            authority_id="test-precision-authority",
            maximum_precision_bits=True,  # bool is an int subclass; must be explicitly rejected
            receipt_registry=_base_registry(),
        )


def test_precision_schedule_authority_tamper_fails_closed():
    registry = _base_registry()
    authority, registry = mount_precision_schedule_authority(
        authority_id="test-precision-authority",
        maximum_precision_bits=256,
        receipt_registry=registry,
    )
    tampered = PrecisionScheduleAuthority(
        authority_id=authority.authority_id,
        maximum_precision_bits=512,  # different from the mounted receipt bytes
        authority_receipt_sha256=authority.authority_receipt_sha256,
    )
    with pytest.raises(ReceiptError, match="differs from its mounted authority"):
        tampered.verify(registry)


def test_precision_schedule_authority_foreign_registry_fails_closed():
    registry = _base_registry()
    authority, _mounted_registry = mount_precision_schedule_authority(
        authority_id="test-precision-authority",
        maximum_precision_bits=256,
        receipt_registry=registry,
    )
    foreign_registry = _base_registry()
    with pytest.raises(ReceiptError, match="not mounted"):
        authority.verify(foreign_registry)


# ---------------------------------------------------------------------------
# mount_causal_grid
# ---------------------------------------------------------------------------


def test_causal_grid_mounts_and_verifies_with_at_least_two_frames():
    registry = _base_registry()
    grid, registry = mount_causal_grid(
        grid_id="test-causal-grid",
        timestamps=(Fraction(1), Fraction(2), Fraction(3)),
        positive_weights=(Fraction(1), Fraction(1), Fraction(1)),
        receipt_registry=registry,
    )
    assert isinstance(grid, CausalGrid)
    grid.verify(registry)


def test_causal_grid_rejects_a_single_instant():
    with pytest.raises(ReceiptError, match="at least two"):
        mount_causal_grid(
            grid_id="test-causal-grid",
            timestamps=(Fraction(1),),
            positive_weights=(Fraction(1),),
            receipt_registry=_base_registry(),
        )


def test_causal_grid_rejects_nonincreasing_timestamps():
    with pytest.raises(ReceiptError, match="increase strictly"):
        mount_causal_grid(
            grid_id="test-causal-grid",
            timestamps=(Fraction(1), Fraction(1)),
            positive_weights=(Fraction(1), Fraction(1)),
            receipt_registry=_base_registry(),
        )


def test_causal_grid_rejects_nonpositive_weight():
    with pytest.raises(ReceiptError, match="exactly positive"):
        mount_causal_grid(
            grid_id="test-causal-grid",
            timestamps=(Fraction(1), Fraction(2)),
            positive_weights=(Fraction(1), Fraction(0)),
            receipt_registry=_base_registry(),
        )


def test_causal_grid_tamper_fails_closed():
    registry = _base_registry()
    grid, registry = mount_causal_grid(
        grid_id="test-causal-grid",
        timestamps=(Fraction(1), Fraction(2)),
        positive_weights=(Fraction(1), Fraction(1)),
        receipt_registry=registry,
    )
    tampered = CausalGrid(
        grid_id=grid.grid_id,
        timestamps=grid.timestamps,
        positive_weights=(Fraction(2), Fraction(2)),  # different from mounted receipt bytes
        grid_receipt_sha256=grid.grid_receipt_sha256,
    )
    with pytest.raises(ReceiptError, match="do not match"):
        tampered.verify(registry)


# ---------------------------------------------------------------------------
# mount_support_domain
# ---------------------------------------------------------------------------


def test_support_domain_defaults_to_every_mounted_topology_port():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    domain, registry = mount_support_domain(
        domain_id="test-support-domain",
        topology=topology,
        receipt_registry=registry,
    )
    assert isinstance(domain, MountedSupportDomain)
    assert set(domain.required_port_keys) == {fiber.key for fiber in topology.ordered_port_fibers}
    domain.verify(registry)


def test_support_domain_accepts_an_explicit_subset():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    subset = (topology.ordered_port_fibers[0].key,)
    domain, registry = mount_support_domain(
        domain_id="test-support-domain",
        topology=topology,
        receipt_registry=registry,
        required_port_keys=subset,
    )
    assert domain.required_port_keys == subset
    domain.verify(registry)


def test_support_domain_rejects_a_port_key_absent_from_the_topology():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    with pytest.raises(ReceiptError, match="absent from the mounted topology"):
        mount_support_domain(
            domain_id="test-support-domain",
            topology=topology,
            receipt_registry=registry,
            required_port_keys=(("smell", "nonexistent-port"),),
        )


def test_support_domain_rejects_empty_override():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    with pytest.raises(ReceiptError, match="cannot be empty"):
        mount_support_domain(
            domain_id="test-support-domain",
            topology=topology,
            receipt_registry=registry,
            required_port_keys=(),
        )


def test_support_domain_tamper_fails_closed():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    domain, registry = mount_support_domain(
        domain_id="test-support-domain",
        topology=topology,
        receipt_registry=registry,
    )
    tampered = MountedSupportDomain(
        domain_id=domain.domain_id,
        required_port_keys=(domain.required_port_keys[0],),  # narrower than mounted receipt
        authority_receipt_sha256=domain.authority_receipt_sha256,
    )
    with pytest.raises(ReceiptError, match="does not match"):
        tampered.verify(registry)


# ---------------------------------------------------------------------------
# mount_resonance_graph_and_operator
# ---------------------------------------------------------------------------


def test_resonance_graph_and_operator_mount_and_verify_against_topology():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    edges = (RequiredEdge(keys[0], keys[1]), RequiredEdge(keys[1], keys[2]))
    graph, operator, registry = mount_resonance_graph_and_operator(
        graph_id="test-resonance-graph",
        required_edges=edges,
        operator_id="test-resonance-operator",
        precision_bits=128,
        receipt_registry=registry,
        topology=topology,
    )
    assert isinstance(graph, MountedResonanceGraph)
    assert isinstance(operator, ResonanceOperatorAuthority)
    graph.verify(registry)
    operator.verify(registry)


def test_resonance_graph_mounts_without_an_explicit_topology():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    edges = (RequiredEdge(keys[0], keys[1]),)
    graph, operator, registry = mount_resonance_graph_and_operator(
        graph_id="test-resonance-graph",
        required_edges=edges,
        operator_id="test-resonance-operator",
        precision_bits=128,
        receipt_registry=registry,
        topology=None,
    )
    graph.verify(registry)
    operator.verify(registry)


def test_resonance_graph_rejects_an_edge_naming_an_unmounted_port():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    edges = (RequiredEdge(keys[0], ("smell", "nonexistent-port")),)
    with pytest.raises(ReceiptError, match="absent from the mounted topology"):
        mount_resonance_graph_and_operator(
            graph_id="test-resonance-graph",
            required_edges=edges,
            operator_id="test-resonance-operator",
            precision_bits=128,
            receipt_registry=registry,
            topology=topology,
        )


def test_resonance_graph_rejects_empty_edges():
    registry = _base_registry()
    with pytest.raises(ReceiptError, match="cannot be empty"):
        mount_resonance_graph_and_operator(
            graph_id="test-resonance-graph",
            required_edges=(),
            operator_id="test-resonance-operator",
            precision_bits=128,
            receipt_registry=registry,
        )


def test_resonance_operator_tamper_fails_closed():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    edges = (RequiredEdge(keys[0], keys[1]),)
    graph, operator, registry = mount_resonance_graph_and_operator(
        graph_id="test-resonance-graph",
        required_edges=edges,
        operator_id="test-resonance-operator",
        precision_bits=128,
        receipt_registry=registry,
        topology=topology,
    )
    tampered = ResonanceOperatorAuthority(
        operator_id=operator.operator_id,
        precision_bits=256,  # different from the mounted receipt bytes
        authority_receipt_sha256=operator.authority_receipt_sha256,
    )
    with pytest.raises(ReceiptError, match="does not match"):
        tampered.verify(registry)


# ---------------------------------------------------------------------------
# Integration: real five-sense fixture topology + real operators
# ---------------------------------------------------------------------------


def test_mounted_authorities_compose_with_real_support_and_resonance_operators():
    """Prove the mounted authorities are not merely self-consistent toys.

    Reuses the real, already-committed five-sense chemistry fixture to get a
    genuine ``MountedFieldTopology`` and a genuine shared sample-time grid,
    then drives the existing, already-tested ``compute_support_floor`` and
    ``compute_resonance_confirmation`` operators through the newly mounted
    authorities end to end.
    """

    profile, _boundary, _prewindow, _story_runtime, _sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    topology = profile.topology
    real_timestamps = profile.grid.timestamps
    assert len(real_timestamps) >= 2

    registry = extend_receipt_registry(registry, CALIBRATION_PAYLOAD, RELEVANCE_PAYLOAD)
    calibration_receipt_sha256 = receipt_sha256(CALIBRATION_PAYLOAD)
    relevance_receipt_sha256 = receipt_sha256(RELEVANCE_PAYLOAD)

    grid, registry = mount_causal_grid(
        grid_id="six-lane-mount-integration-grid",
        timestamps=real_timestamps,
        positive_weights=tuple(Fraction(1) for _ in real_timestamps),
        receipt_registry=registry,
    )

    support_domain, registry = mount_support_domain(
        domain_id="six-lane-mount-integration-support",
        topology=topology,
        receipt_registry=registry,
    )

    keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    edges = tuple(
        RequiredEdge(left, right) for left, right in zip(keys[:-1], keys[1:], strict=True)
    )
    resonance_graph, resonance_operator, registry = mount_resonance_graph_and_operator(
        graph_id="six-lane-mount-integration-resonance",
        required_edges=edges,
        operator_id="six-lane-mount-integration-gamma-squared",
        precision_bits=128,
        receipt_registry=registry,
        topology=topology,
    )

    precision_authority, registry = mount_precision_schedule_authority(
        authority_id="six-lane-mount-integration-precision",
        maximum_precision_bits=256,
        receipt_registry=registry,
    )
    precision_authority.verify(registry)

    streams = tuple(
        EvidenceStream(
            lane_id=lane_id,
            port_id=port_id,
            evidence_id=f"integration-{lane_id}-{port_id}",
            source_epoch="six-lane-mount-integration-epoch",
            port_kind="test_receipted_port",
            physical_unit="native_unit",
            profile_binding_sha256=registry.profile_binding_sha256,
            calibration_receipt_sha256=calibration_receipt_sha256,
            relevance_receipt_sha256=relevance_receipt_sha256,
            samples=tuple(
                EvidenceSample(
                    source_index=index,
                    timestamp=timestamp,
                    signal=Fraction(0),
                    relevance=Fraction(1, 2) + Fraction(index, 10),
                    phase_turns=Fraction(index, 8),
                )
                for index, timestamp in enumerate(real_timestamps)
            ),
        )
        for lane_id, port_id in keys
    )

    support_floor = compute_support_floor(streams, grid, support_domain, registry)
    assert support_floor.value > 0
    assert set(support_floor.required_port_keys) == set(keys)

    resonance = compute_resonance_confirmation(
        streams, grid, resonance_graph, resonance_operator, registry
    )
    assert resonance.working_precision_bits == 128
    assert len(resonance.edge_facts) == len(edges)


# ---------------------------------------------------------------------------
# mount_field_topology (Stage 3)
# ---------------------------------------------------------------------------


def test_field_topology_mounts_over_the_real_five_sense_manifest_and_verifies():
    _profile, _boundary, _prewindow, story_runtime, _sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    topology, registry = mount_field_topology(
        topology_id="test-field-topology",
        manifest=story_runtime.manifest,
        receipt_registry=registry,
    )
    assert isinstance(topology, MountedFieldTopology)
    # Derived from the real production-shaped manifest port count -- never a
    # hardcoded five- or six-port shape.
    assert len(topology.ordered_port_fibers) == len(story_runtime.manifest.ports)
    assert tuple(fiber.lane_id for fiber in topology.ordered_port_fibers) == (
        "sound",
        "smell",
        "taste",
        "touch",
        "sight",
    )
    assert tuple(fiber.port_id for fiber in topology.ordered_port_fibers) == tuple(
        port.port_id for port in story_runtime.manifest.ports
    )
    assert topology.dimension == FIBER_DIMENSION * len(story_runtime.manifest.ports)
    topology.verify(registry)  # independent re-verification, not just construction


def test_field_topology_rejects_a_non_manifest_input():
    registry = _base_registry()
    with pytest.raises(ReceiptError, match="authenticated story chemistry manifest"):
        mount_field_topology(
            topology_id="test-field-topology",
            manifest=object(),  # type: ignore[arg-type]
            receipt_registry=registry,
        )


def test_field_topology_fails_closed_when_manifest_authorities_are_not_yet_mounted():
    _profile, _boundary, _prewindow, story_runtime, _sensor_states, _registry = (
        _mounted_five_sense_runtime()
    )
    fresh_registry = _base_registry()
    with pytest.raises(ReceiptError, match="not mounted"):
        mount_field_topology(
            topology_id="test-field-topology",
            manifest=story_runtime.manifest,
            receipt_registry=fresh_registry,
        )


def test_field_topology_tamper_fails_closed():
    _profile, _boundary, _prewindow, story_runtime, _sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    topology, registry = mount_field_topology(
        topology_id="test-field-topology-tamper",
        manifest=story_runtime.manifest,
        receipt_registry=registry,
    )
    tampered = MountedFieldTopology(
        topology_id=topology.topology_id,
        ordered_port_fibers=topology.ordered_port_fibers[:-1],  # dropped a fiber
        authority_receipt_sha256=topology.authority_receipt_sha256,
    )
    with pytest.raises(ReceiptError, match="differs from its authority receipt"):
        tampered.verify(registry)


# ---------------------------------------------------------------------------
# mount_typed_language_kernel_binding (Stage 3)
# ---------------------------------------------------------------------------


def test_typed_language_kernel_binding_mounts_and_verifies():
    registry = _base_registry()
    binding, registry = mount_typed_language_kernel_binding(
        adapter_id="test-typed-adapter",
        interface_id="test-typed-interface",
        phase_calibration_id="test-typed-phase",
        phase_kappa=Fraction(1, 7),
        derivation_payload=b'{"schema":"test.six_lane_runtime_mount.typed_derivation.v1"}',
        receipt_registry=registry,
    )
    assert isinstance(binding, MountedTypedLanguageKernelBinding)
    assert binding.adapter_id == "test-typed-adapter"
    assert binding.interface_id == "test-typed-interface"
    binding.verify(registry)  # independent re-verification, not just construction


def test_typed_language_kernel_binding_rejects_empty_derivation_payload():
    with pytest.raises(ReceiptError, match="nonempty exact bytes"):
        mount_typed_language_kernel_binding(
            adapter_id="test-typed-adapter",
            interface_id="test-typed-interface",
            phase_calibration_id="test-typed-phase",
            phase_kappa=Fraction(1, 7),
            derivation_payload=b"",
            receipt_registry=_base_registry(),
        )


def test_typed_language_kernel_binding_rejects_non_fraction_phase_kappa():
    with pytest.raises(ReceiptError, match="fractions.Fraction"):
        mount_typed_language_kernel_binding(
            adapter_id="test-typed-adapter",
            interface_id="test-typed-interface",
            phase_calibration_id="test-typed-phase",
            phase_kappa=0.5,  # type: ignore[arg-type]
            derivation_payload=b'{"schema":"test.six_lane_runtime_mount.typed_derivation.v1"}',
            receipt_registry=_base_registry(),
        )


def test_typed_language_kernel_binding_rejects_blank_identifiers():
    with pytest.raises(ReceiptError, match="canonical identifier"):
        mount_typed_language_kernel_binding(
            adapter_id="",
            interface_id="test-typed-interface",
            phase_calibration_id="test-typed-phase",
            phase_kappa=Fraction(1, 7),
            derivation_payload=b'{"schema":"test.six_lane_runtime_mount.typed_derivation.v1"}',
            receipt_registry=_base_registry(),
        )


def test_typed_language_kernel_binding_tamper_fails_closed():
    registry = _base_registry()
    binding, registry = mount_typed_language_kernel_binding(
        adapter_id="test-typed-adapter",
        interface_id="test-typed-interface",
        phase_calibration_id="test-typed-phase",
        phase_kappa=Fraction(1, 7),
        derivation_payload=b'{"schema":"test.six_lane_runtime_mount.typed_derivation.v1"}',
        receipt_registry=registry,
    )
    tampered = replace(binding, adapter_id="a-different-adapter-id")
    with pytest.raises(ReceiptError, match="differs from receipt"):
        tampered.verify(registry)


def test_typed_language_kernel_binding_foreign_registry_fails_closed():
    registry = _base_registry()
    binding, _mounted_registry = mount_typed_language_kernel_binding(
        adapter_id="test-typed-adapter",
        interface_id="test-typed-interface",
        phase_calibration_id="test-typed-phase",
        phase_kappa=Fraction(1, 7),
        derivation_payload=b'{"schema":"test.six_lane_runtime_mount.typed_derivation.v1"}',
        receipt_registry=registry,
    )
    with pytest.raises(ReceiptError, match="not mounted"):
        binding.verify(_base_registry())


# ---------------------------------------------------------------------------
# mount_story_sensor_states (Stage 3)
# ---------------------------------------------------------------------------


def _foreign_sensor_port(*, story_port_id: str, field_port_id: str) -> StorySensorPortAuthority:
    source = _canonical(
        {
            "port_id": field_port_id,
            "schema": "test.six_lane_runtime_mount.foreign_source_authority.v1",
        }
    )
    values = dict(
        lane=L6Lane.SOUND,
        story_port_id=story_port_id,
        field_port_id=field_port_id,
        scene_coordinate_id=f"scene-{field_port_id}",
        base_raw_code=0,
        minimum_raw_code=-1,
        maximum_raw_code=1,
        flux_at_code_zero=Fraction(1, 5),
        physical_quantum=Fraction(1, 20),
        native_flux_unit="test-native-flux-unit",
        signal_offset=Fraction(0),
        signal_per_native_flux=Fraction(1),
        response_growth=Fraction(1, 2),
        natural_decay=Fraction(1, 8),
        phase_kappa=Fraction(1, 3),
        source_epoch="test-foreign-sensor-epoch-0",
        port_kind="authenticated_virtual_story_boundary",
        signal_physical_unit="dimensionless_story_response",
        boundary_source_authority_receipt_sha256=receipt_sha256(source),
    )
    payload = story_sensor_port_authority_receipt_payload(**values)
    return StorySensorPortAuthority(**values, authority_receipt_sha256=receipt_sha256(payload)), payload, source


def test_story_sensor_states_mount_genesis_for_every_real_five_sense_port_and_verify():
    profile, _boundary, _prewindow, story_runtime, _fixture_sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    sensor_states, registry = mount_story_sensor_states(
        manifest=story_runtime.manifest,
        ports=profile.ports,
        receipt_registry=registry,
    )
    assert len(sensor_states) == len(profile.ports)
    assert all(isinstance(value, MountedStorySensorState) for value in sensor_states)
    assert tuple(value.field_port_id for value in sensor_states) == tuple(
        port.field_port_id for port in profile.ports
    )
    for port, state in zip(profile.ports, sensor_states, strict=True):
        # Genuine genesis: no observations yet, and the exact real chemistry
        # start time -- never an invented or averaged value.
        assert state.last_source_index == -1
        assert state.retained_signal == Fraction(0)
        assert state.phase_turns == Fraction(0)
        assert state.last_timestamp == story_runtime.state(port.story_port_id).source_time
        state.verify(port=port, receipt_registry=registry)  # independent re-verification


def test_story_sensor_states_rejects_a_non_manifest_input():
    profile, _boundary, _prewindow, _story_runtime, _fixture_sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    with pytest.raises(ReceiptError, match="authenticated story chemistry manifest"):
        mount_story_sensor_states(
            manifest=object(),  # type: ignore[arg-type]
            ports=profile.ports,
            receipt_registry=registry,
        )


def test_story_sensor_states_rejects_empty_ports():
    _profile, _boundary, _prewindow, story_runtime, _fixture_sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    with pytest.raises(ReceiptError, match="at least one mounted sensor port"):
        mount_story_sensor_states(
            manifest=story_runtime.manifest,
            ports=(),
            receipt_registry=registry,
        )


def test_story_sensor_states_rejects_an_untyped_port():
    _profile, _boundary, _prewindow, story_runtime, _fixture_sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    with pytest.raises(ReceiptError, match="typed StorySensorPortAuthority"):
        mount_story_sensor_states(
            manifest=story_runtime.manifest,
            ports=(object(),),  # type: ignore[arg-type]
            receipt_registry=registry,
        )


def test_story_sensor_states_rejects_a_repeated_field_port_id():
    profile, _boundary, _prewindow, story_runtime, _fixture_sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    with pytest.raises(ReceiptError, match="cannot repeat a field port id"):
        mount_story_sensor_states(
            manifest=story_runtime.manifest,
            ports=(profile.ports[0], profile.ports[0]),
            receipt_registry=registry,
        )


def test_story_sensor_states_rejects_a_port_that_does_not_resolve_in_the_registry():
    profile, _boundary, _prewindow, story_runtime, _fixture_sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    tampered_port = replace(
        profile.ports[0],
        authority_receipt_sha256=receipt_sha256(b'{"schema":"unrelated.junk.v1"}'),
    )
    with pytest.raises(ReceiptError, match="not mounted"):
        mount_story_sensor_states(
            manifest=story_runtime.manifest,
            ports=(tampered_port,),
            receipt_registry=registry,
        )


def test_story_sensor_states_rejects_a_port_naming_an_unmounted_story_port():
    _profile, _boundary, _prewindow, story_runtime, _fixture_sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    foreign_port, foreign_payload, foreign_source = _foreign_sensor_port(
        story_port_id="foreign-story-port-not-in-manifest",
        field_port_id="foreign-field-port-not-in-manifest",
    )
    registry = extend_receipt_registry(registry, foreign_source, foreign_payload)
    with pytest.raises(ReceiptError, match="unmounted port"):
        mount_story_sensor_states(
            manifest=story_runtime.manifest,
            ports=(foreign_port,),
            receipt_registry=registry,
        )


def test_story_sensor_state_tamper_fails_closed():
    profile, _boundary, _prewindow, story_runtime, _fixture_sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    sensor_states, registry = mount_story_sensor_states(
        manifest=story_runtime.manifest,
        ports=profile.ports,
        receipt_registry=registry,
    )
    tampered = replace(sensor_states[0], retained_signal=Fraction(1, 2))
    with pytest.raises(ReceiptError, match="story sensor state receipt"):
        tampered.verify(port=profile.ports[0], receipt_registry=registry)


# ---------------------------------------------------------------------------
# Integration: the full Stage 1 + Stage 3 mount chain over one registry
# ---------------------------------------------------------------------------


def test_full_stage_one_and_stage_three_chain_mounts_one_coherent_authority_set():
    """Chain every Stage 1 + Stage 3 ``mount_*`` function in the real
    dependency order the governing fixtures prove works: mount chemistry ->
    topology -> typed-language binding -> sensor states -> causal grid ->
    support domain -> resonance graph, all against one continuously-extended
    :class:`ReceiptRegistry`, then independently re-verify every mounted
    authority against that same final registry -- proving one coherent,
    cross-verified authority set, not isolated per-call registries.
    """

    profile, _boundary, _prewindow, story_runtime, _fixture_sensor_states, registry = (
        _mounted_five_sense_runtime()
    )

    topology, registry = mount_field_topology(
        topology_id="chain-field-topology",
        manifest=story_runtime.manifest,
        receipt_registry=registry,
    )

    binding, registry = mount_typed_language_kernel_binding(
        adapter_id="chain-typed-adapter",
        interface_id="chain-typed-interface",
        phase_calibration_id="chain-typed-phase",
        phase_kappa=Fraction(1, 7),
        derivation_payload=b'{"schema":"test.six_lane_runtime_mount.chain_derivation.v1"}',
        receipt_registry=registry,
    )

    sensor_states, registry = mount_story_sensor_states(
        manifest=story_runtime.manifest,
        ports=profile.ports,
        receipt_registry=registry,
    )
    assert len(sensor_states) == len(profile.ports)

    grid, registry = mount_causal_grid(
        grid_id="chain-causal-grid",
        timestamps=profile.grid.timestamps,
        positive_weights=profile.grid.positive_weights,
        receipt_registry=registry,
    )

    support_domain, registry = mount_support_domain(
        domain_id="chain-support-domain",
        topology=topology,
        receipt_registry=registry,
    )
    assert set(support_domain.required_port_keys) == {
        fiber.key for fiber in topology.ordered_port_fibers
    }

    keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    edges = tuple(
        RequiredEdge(left, right) for left, right in zip(keys[:-1], keys[1:], strict=True)
    )
    resonance_graph, resonance_operator, registry = mount_resonance_graph_and_operator(
        graph_id="chain-resonance-graph",
        required_edges=edges,
        operator_id="chain-resonance-operator",
        precision_bits=128,
        receipt_registry=registry,
        topology=topology,
    )

    # Every mounted authority independently re-verifies against the SAME
    # final registry, proving one coherent, continuously-extended chain.
    topology.verify(registry)
    binding.verify(registry)
    for port, state in zip(profile.ports, sensor_states, strict=True):
        state.verify(port=port, receipt_registry=registry)
    grid.verify(registry)
    support_domain.verify(registry)
    resonance_graph.verify(registry)
    resonance_operator.verify(registry)


# ---------------------------------------------------------------------------
# mount_expression_mode_bank (Stage 4)
# ---------------------------------------------------------------------------


def test_expression_mode_bank_mounts_empty_and_verifies():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    precision_authority, registry = mount_precision_schedule_authority(
        authority_id="test-expression-precision",
        maximum_precision_bits=2048,
        receipt_registry=registry,
    )
    bank, registry = mount_expression_mode_bank(
        topology=topology,
        precision_authority=precision_authority,
        receipt_registry=registry,
    )
    assert isinstance(bank, ExpressionModeBank)
    assert bank.rank == 0
    assert bank.dimension == topology.dimension
    # The bank's own receipt must already be mounted -- later authorities
    # (MountedPreWindowState) require mode_state_receipt_sha256 to resolve.
    assert registry.resolve(bank.receipt_sha256) == bank.receipt_payload
    bank.verify(topology=topology, receipt_registry=registry)  # independent re-verification


def test_expression_mode_bank_rejects_an_unavailable_topology():
    registry = _base_registry()
    empty_payload = field_topology_receipt_payload("test-empty-genesis-topology", ())
    registry = extend_receipt_registry(registry, empty_payload)
    empty_topology = MountedFieldTopology(
        "test-empty-genesis-topology", (), receipt_sha256(empty_payload)
    )
    empty_topology.verify(registry)
    precision_authority, registry = mount_precision_schedule_authority(
        authority_id="test-expression-precision",
        maximum_precision_bits=2048,
        receipt_registry=registry,
    )
    with pytest.raises(ReceiptError, match="requires a mounted field"):
        mount_expression_mode_bank(
            topology=empty_topology,
            precision_authority=precision_authority,
            receipt_registry=registry,
        )


# ---------------------------------------------------------------------------
# mount_pre_window_state (Stage 4)
# ---------------------------------------------------------------------------


def _mounted_bank_and_field_state(registry, topology, *, genesis_time=Fraction(0)):
    precision_authority, registry = mount_precision_schedule_authority(
        authority_id="test-pre-window-precision",
        maximum_precision_bits=2048,
        receipt_registry=registry,
    )
    bank, registry = mount_expression_mode_bank(
        topology=topology, precision_authority=precision_authority, receipt_registry=registry
    )
    amplitudes = tuple(ExactComplex(Fraction(0)) for _ in range(topology.dimension))
    field_payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256, genesis_time, amplitudes
    )
    registry = extend_receipt_registry(registry, field_payload)
    field_state = ExactFieldState(
        topology.authority_receipt_sha256, genesis_time, amplitudes, receipt_sha256(field_payload)
    )
    field_state.verify(registry)
    return field_state, bank, registry


def _opaque_state_digest(registry, schema: str) -> tuple[str, ReceiptRegistry]:
    payload = json.dumps({"schema": schema}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    registry = extend_receipt_registry(registry, payload)
    return receipt_sha256(payload), registry


def test_pre_window_state_mounts_and_verifies():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    field_state, bank, registry = _mounted_bank_and_field_state(registry, topology)
    chemistry_digest, registry = _opaque_state_digest(registry, "test.pre_window.chemistry.v1")
    memory_digest, registry = _opaque_state_digest(registry, "test.pre_window.memory.v1")
    l6_digest, registry = _opaque_state_digest(registry, "test.pre_window.l6.v1")

    state, registry = mount_pre_window_state(
        state_id="test-pre-window-state",
        chemistry_state_receipt_sha256=chemistry_digest,
        field_state=field_state,
        mode_bank=bank,
        memory_state_receipt_sha256=memory_digest,
        l6_state_receipt_sha256=l6_digest,
        topology=topology,
        receipt_registry=registry,
    )
    assert isinstance(state, MountedPreWindowState)
    assert state.field_state_receipt_sha256 == field_state.authority_receipt_sha256
    assert state.mode_state_receipt_sha256 == bank.receipt_sha256
    state.verify(registry)  # independent re-verification


def test_pre_window_state_rejects_field_state_from_another_topology():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    other_fibers = (PortFiber("smell", "right-nose"), PortFiber("taste", "right-tongue"))
    other_topology_payload = field_topology_receipt_payload(
        "test-pre-window-other-topology", other_fibers
    )
    registry = extend_receipt_registry(registry, other_topology_payload)
    other_topology = MountedFieldTopology(
        "test-pre-window-other-topology", other_fibers, receipt_sha256(other_topology_payload)
    )
    other_topology.verify(registry)
    field_state, bank, registry = _mounted_bank_and_field_state(registry, topology)
    # Build a field state genuinely bound to a *different* mounted topology.
    other_amplitudes = tuple(ExactComplex(Fraction(0)) for _ in range(other_topology.dimension))
    other_payload = exact_field_state_receipt_payload(
        other_topology.authority_receipt_sha256, Fraction(0), other_amplitudes
    )
    registry = extend_receipt_registry(registry, other_payload)
    other_field_state = ExactFieldState(
        other_topology.authority_receipt_sha256,
        Fraction(0),
        other_amplitudes,
        receipt_sha256(other_payload),
    )
    other_field_state.verify(registry)
    chemistry_digest, registry = _opaque_state_digest(registry, "test.pre_window.chemistry.v2")
    memory_digest, registry = _opaque_state_digest(registry, "test.pre_window.memory.v2")
    l6_digest, registry = _opaque_state_digest(registry, "test.pre_window.l6.v2")

    with pytest.raises(ReceiptError, match="belongs to another topology"):
        mount_pre_window_state(
            state_id="test-pre-window-state",
            chemistry_state_receipt_sha256=chemistry_digest,
            field_state=other_field_state,
            mode_bank=bank,
            memory_state_receipt_sha256=memory_digest,
            l6_state_receipt_sha256=l6_digest,
            topology=topology,
            receipt_registry=registry,
        )


def test_pre_window_state_rejects_a_non_exact_field_state():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    _field_state, bank, registry = _mounted_bank_and_field_state(registry, topology)
    chemistry_digest, registry = _opaque_state_digest(registry, "test.pre_window.chemistry.v3")
    memory_digest, registry = _opaque_state_digest(registry, "test.pre_window.memory.v3")
    l6_digest, registry = _opaque_state_digest(registry, "test.pre_window.l6.v3")

    with pytest.raises(ReceiptError, match="mounted exact field state"):
        mount_pre_window_state(
            state_id="test-pre-window-state",
            chemistry_state_receipt_sha256=chemistry_digest,
            field_state=object(),  # type: ignore[arg-type]
            mode_bank=bank,
            memory_state_receipt_sha256=memory_digest,
            l6_state_receipt_sha256=l6_digest,
            topology=topology,
            receipt_registry=registry,
        )


def test_pre_window_state_rejects_a_non_expression_mode_bank():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    field_state, _bank, registry = _mounted_bank_and_field_state(registry, topology)
    chemistry_digest, registry = _opaque_state_digest(registry, "test.pre_window.chemistry.v4")
    memory_digest, registry = _opaque_state_digest(registry, "test.pre_window.memory.v4")
    l6_digest, registry = _opaque_state_digest(registry, "test.pre_window.l6.v4")

    with pytest.raises(ReceiptError, match="mounted expression mode bank"):
        mount_pre_window_state(
            state_id="test-pre-window-state",
            chemistry_state_receipt_sha256=chemistry_digest,
            field_state=field_state,
            mode_bank=object(),  # type: ignore[arg-type]
            memory_state_receipt_sha256=memory_digest,
            l6_state_receipt_sha256=l6_digest,
            topology=topology,
            receipt_registry=registry,
        )


def test_pre_window_state_rejects_an_unmounted_memory_digest():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    field_state, bank, registry = _mounted_bank_and_field_state(registry, topology)
    chemistry_digest, registry = _opaque_state_digest(registry, "test.pre_window.chemistry.v5")
    l6_digest, registry = _opaque_state_digest(registry, "test.pre_window.l6.v5")
    never_mounted_digest = receipt_sha256(b'{"schema":"never.mounted.v1"}')

    with pytest.raises(ReceiptError, match="not mounted"):
        mount_pre_window_state(
            state_id="test-pre-window-state",
            chemistry_state_receipt_sha256=chemistry_digest,
            field_state=field_state,
            mode_bank=bank,
            memory_state_receipt_sha256=never_mounted_digest,
            l6_state_receipt_sha256=l6_digest,
            topology=topology,
            receipt_registry=registry,
        )


def test_pre_window_state_tamper_fails_closed():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    field_state, bank, registry = _mounted_bank_and_field_state(registry, topology)
    chemistry_digest, registry = _opaque_state_digest(registry, "test.pre_window.chemistry.v6")
    memory_digest, registry = _opaque_state_digest(registry, "test.pre_window.memory.v6")
    l6_digest, registry = _opaque_state_digest(registry, "test.pre_window.l6.v6")
    other_digest, registry = _opaque_state_digest(registry, "test.pre_window.other.v6")

    state, registry = mount_pre_window_state(
        state_id="test-pre-window-state",
        chemistry_state_receipt_sha256=chemistry_digest,
        field_state=field_state,
        mode_bank=bank,
        memory_state_receipt_sha256=memory_digest,
        l6_state_receipt_sha256=l6_digest,
        topology=topology,
        receipt_registry=registry,
    )
    tampered = replace(state, memory_state_receipt_sha256=other_digest)
    with pytest.raises(ReceiptError, match="differs from mounted authority"):
        tampered.verify(registry)


# ---------------------------------------------------------------------------
# mount_l5_governance_profile (Stage 4)
# ---------------------------------------------------------------------------


def test_l5_governance_profile_defaults_every_port_and_fact_to_required():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    profile, registry = mount_l5_governance_profile(
        profile_id="test-l5-profile",
        topology=topology,
        receipt_registry=registry,
    )
    expected_keys = tuple(
        (fiber.lane_id, fiber.port_id, fact)
        for fiber in topology.ordered_port_fibers
        for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
    )
    actual_keys = tuple((rule.lane_id, rule.port_id, rule.fact) for rule in profile.rules)
    assert actual_keys == expected_keys
    assert all(rule.state is ApplicabilityState.REQUIRED for rule in profile.rules)
    profile.verify(topology, registry)  # independent re-verification


def test_l5_governance_profile_tamper_fails_closed():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    profile, registry = mount_l5_governance_profile(
        profile_id="test-l5-profile",
        topology=topology,
        receipt_registry=registry,
    )
    tampered_rules = (
        *profile.rules[:-1],
        replace(profile.rules[-1], state=ApplicabilityState.NOT_APPLICABLE),
    )
    tampered = replace(profile, rules=tampered_rules)
    with pytest.raises(ReceiptError, match="differs from mounted authority"):
        tampered.verify(topology, registry)


def test_l5_governance_profile_foreign_registry_fails_closed():
    registry = _base_registry()
    topology, registry = _small_topology(registry)
    profile, _mounted_registry = mount_l5_governance_profile(
        profile_id="test-l5-profile",
        topology=topology,
        receipt_registry=registry,
    )
    foreign_registry, _foreign_topology = registry, topology
    with pytest.raises(ReceiptError, match="not mounted"):
        profile.verify(topology, _base_registry())


# ---------------------------------------------------------------------------
# mount_story_global_uf_basin_profile (Stage 4)
# ---------------------------------------------------------------------------


def _six_lane_basin_context(language_port_id: str = "six-lane-mount-test-language-port"):
    """Build every already-mounted piece :func:`mount_story_global_uf_basin_profile`
    needs, reusing the real five-sense fixture (never a toy topology) and
    reusing the *old* five-sense pre-window state's chemistry/memory/L6
    receipts unchanged -- exactly mirroring how ``tests/glew_runtime/
    test_story_global_uf_basin.py::_mounted_six_lane_preparation`` continues
    an existing window rather than inventing a fresh chemistry state.
    """

    story_profile, _boundary, old_pre, _story_runtime, sensor_states, registry = (
        _mounted_five_sense_runtime()
    )
    fibers = (
        PortFiber(L6Lane.LANGUAGE.value, language_port_id),
        *story_profile.topology.ordered_port_fibers,
    )
    topology_payload = field_topology_receipt_payload(
        "six-lane-mount-test-basin-topology", fibers
    )
    registry = extend_receipt_registry(registry, topology_payload)
    topology = MountedFieldTopology(
        "six-lane-mount-test-basin-topology", fibers, receipt_sha256(topology_payload)
    )
    topology.verify(registry)

    precision_authority, registry = mount_precision_schedule_authority(
        authority_id="six-lane-mount-test-basin-precision",
        maximum_precision_bits=2048,
        receipt_registry=registry,
    )
    mode_bank, registry = mount_expression_mode_bank(
        topology=topology, precision_authority=precision_authority, receipt_registry=registry
    )

    genesis_time = sensor_states[0].last_timestamp
    amplitudes = tuple(ExactComplex(Fraction(0)) for _ in range(topology.dimension))
    field_payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256, genesis_time, amplitudes
    )
    registry = extend_receipt_registry(registry, field_payload)
    initial_field_state = ExactFieldState(
        topology.authority_receipt_sha256, genesis_time, amplitudes, receipt_sha256(field_payload)
    )
    initial_field_state.verify(registry)

    pre_window_state, registry = mount_pre_window_state(
        state_id="six-lane-mount-test-pre-window",
        chemistry_state_receipt_sha256=old_pre.chemistry_state_receipt_sha256,
        field_state=initial_field_state,
        mode_bank=mode_bank,
        memory_state_receipt_sha256=old_pre.memory_state_receipt_sha256,
        l6_state_receipt_sha256=old_pre.l6_state_receipt_sha256,
        topology=topology,
        receipt_registry=registry,
    )

    l5_profile, registry = mount_l5_governance_profile(
        profile_id="six-lane-mount-test-l5-profile",
        topology=topology,
        receipt_registry=registry,
    )

    return {
        "story_profile": story_profile,
        "topology": topology,
        "precision_authority": precision_authority,
        "mode_bank": mode_bank,
        "initial_field_state": initial_field_state,
        "pre_window_state": pre_window_state,
        "l5_profile": l5_profile,
        "registry": registry,
    }


def test_story_global_uf_basin_profile_mounts_and_verifies():
    ctx = _six_lane_basin_context()
    physical_payload = b'{"schema":"test.six_lane_runtime_mount.basin_physical_profile.v1"}'
    profile, registry = mount_story_global_uf_basin_profile(
        profile_id="six-lane-mount-test-basin-profile",
        story_profile=ctx["story_profile"],
        physical_profile_payload=physical_payload,
        initial_field_state=ctx["initial_field_state"],
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source_time_unit="six-lane-mount-test-structural-time",
        max_connected_component_dimension=1,
        field_precision_bits=128,
        precision_authority=ctx["precision_authority"],
        mode_bank=ctx["mode_bank"],
        l5_governance=ctx["l5_profile"],
        pre_window_state=ctx["pre_window_state"],
        topology=ctx["topology"],
        receipt_registry=ctx["registry"],
    )
    assert isinstance(profile, MountedStoryGlobalUFBasinProfile)
    profile.verify(
        story_profile=ctx["story_profile"],
        pre_window_state=ctx["pre_window_state"],
        topology=ctx["topology"],
        receipt_registry=registry,
    )


def test_story_global_uf_basin_profile_rejects_empty_physical_payload():
    ctx = _six_lane_basin_context()
    with pytest.raises(ReceiptError, match="nonempty exact physical profile payload"):
        mount_story_global_uf_basin_profile(
            profile_id="six-lane-mount-test-basin-profile",
            story_profile=ctx["story_profile"],
            physical_profile_payload=b"",
            initial_field_state=ctx["initial_field_state"],
            hbar=Fraction(1),
            hamiltonian=(),
            local_rates=(),
            source_time_unit="six-lane-mount-test-structural-time",
            max_connected_component_dimension=1,
            field_precision_bits=128,
            precision_authority=ctx["precision_authority"],
            mode_bank=ctx["mode_bank"],
            l5_governance=ctx["l5_profile"],
            pre_window_state=ctx["pre_window_state"],
            topology=ctx["topology"],
            receipt_registry=ctx["registry"],
        )


def test_story_global_uf_basin_profile_requires_exactly_six_native_lanes():
    ctx = _six_lane_basin_context()
    physical_payload = b'{"schema":"test.six_lane_runtime_mount.basin_physical_profile.v2"}'
    profile, registry = mount_story_global_uf_basin_profile(
        profile_id="six-lane-mount-test-basin-profile",
        story_profile=ctx["story_profile"],
        physical_profile_payload=physical_payload,
        initial_field_state=ctx["initial_field_state"],
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source_time_unit="six-lane-mount-test-structural-time",
        max_connected_component_dimension=1,
        field_precision_bits=128,
        precision_authority=ctx["precision_authority"],
        mode_bank=ctx["mode_bank"],
        l5_governance=ctx["l5_profile"],
        pre_window_state=ctx["pre_window_state"],
        topology=ctx["topology"],
        receipt_registry=ctx["registry"],
    )
    # Re-verifying against the five-sense-only topology (the real, unmodified
    # story_profile.topology) confirms MountedStoryGlobalUFBasinProfile's own
    # six-lane invariant is genuinely enforced -- not something this module
    # invented.
    with pytest.raises(ReceiptError, match="exactly all six native lanes"):
        profile.verify(
            story_profile=ctx["story_profile"],
            pre_window_state=ctx["pre_window_state"],
            topology=ctx["story_profile"].topology,
            receipt_registry=registry,
        )


def test_story_global_uf_basin_profile_tamper_fails_closed():
    ctx = _six_lane_basin_context()
    physical_payload = b'{"schema":"test.six_lane_runtime_mount.basin_physical_profile.v3"}'
    profile, registry = mount_story_global_uf_basin_profile(
        profile_id="six-lane-mount-test-basin-profile",
        story_profile=ctx["story_profile"],
        physical_profile_payload=physical_payload,
        initial_field_state=ctx["initial_field_state"],
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source_time_unit="six-lane-mount-test-structural-time",
        max_connected_component_dimension=1,
        field_precision_bits=128,
        precision_authority=ctx["precision_authority"],
        mode_bank=ctx["mode_bank"],
        l5_governance=ctx["l5_profile"],
        pre_window_state=ctx["pre_window_state"],
        topology=ctx["topology"],
        receipt_registry=ctx["registry"],
    )
    tampered = replace(profile, source_time_unit="a-different-structural-time-unit")
    with pytest.raises(ReceiptError, match="differs from canonical bytes"):
        tampered.verify(
            story_profile=ctx["story_profile"],
            pre_window_state=ctx["pre_window_state"],
            topology=ctx["topology"],
            receipt_registry=registry,
        )


# ---------------------------------------------------------------------------
# mount_six_lane_runtime: the top-level orchestrator (Stage 4)
# ---------------------------------------------------------------------------


def _six_lane_runtime_kwargs():
    """Real inputs for :func:`mount_six_lane_runtime`, built from the same
    candidate five-sense production-shaped fixture every other test in this
    module already relies on (``tests/glew_runtime/test_story_native_replay.py``'s
    ``FIXTURE``/``CANDIDATE_KEY``/``CANDIDATE_KEY_ID``/``_sensor_port``).
    """

    profile_bytes = FIXTURE.read_bytes()
    preliminary = mount_story_chemistry(
        manifest_envelope_payload=profile_bytes,
        trusted_authentication_key=CANDIDATE_KEY,
        expected_key_id=CANDIDATE_KEY_ID,
    )
    assert preliminary.status is StoryChemistryStatus.MOUNTED
    mounted_ports = tuple(_sensor_port(value) for value in preliminary.runtime.manifest.ports)
    sensor_ports = tuple(value[0] for value in mounted_ports)
    sensor_port_receipt_payloads = tuple(
        payload for value in mounted_ports for payload in (value[1], value[2])
    )

    five_sense_keys = tuple(value.field_key for value in sensor_ports)
    five_sense_edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(five_sense_keys[:-1], five_sense_keys[1:], strict=True)
    )
    six_lane_keys = (("language", "six-lane-runtime-test-language-port"), *five_sense_keys)
    six_lane_edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(six_lane_keys[:-1], six_lane_keys[1:], strict=True)
    )

    return dict(
        story_chemistry_profile_bytes=profile_bytes,
        story_chemistry_authentication_key=CANDIDATE_KEY,
        story_chemistry_expected_key_id=CANDIDATE_KEY_ID,
        sensor_ports=sensor_ports,
        sensor_port_receipt_payloads=sensor_port_receipt_payloads,
        five_sense_topology_id="six-lane-runtime-test-five-sense-topology",
        causal_grid_id="six-lane-runtime-test-causal-grid",
        causal_timestamps=(Fraction(1), Fraction(2), Fraction(3)),
        causal_positive_weights=(Fraction(1), Fraction(1), Fraction(1)),
        five_sense_support_domain_id="six-lane-runtime-test-five-sense-support",
        five_sense_resonance_graph_id="six-lane-runtime-test-five-sense-resonance",
        five_sense_resonance_required_edges=five_sense_edges,
        resonance_operator_id="six-lane-runtime-test-resonance-operator",
        resonance_precision_bits=128,
        story_replay_profile_id="six-lane-runtime-test-story-replay-profile",
        story_replay_provider_id="six-lane-runtime-test-story-replay-provider",
        story_replay_kernel_adapter_id="six-lane-runtime-test-kernel-adapter",
        story_replay_kernel_adapter_profile_payload=(
            b'{"schema":"test.six_lane_runtime_mount.orchestrator_kernel_adapter.v1"}'
        ),
        typed_language_adapter_id="six-lane-runtime-test-typed-adapter",
        typed_language_interface_id="six-lane-runtime-test-typed-interface",
        typed_language_phase_calibration_id="six-lane-runtime-test-typed-phase",
        typed_language_phase_kappa=Fraction(1, 7),
        typed_language_derivation_payload=(
            b'{"schema":"test.six_lane_runtime_mount.orchestrator_typed_derivation.v1"}'
        ),
        language_port_id="six-lane-runtime-test-language-port",
        six_lane_topology_id="six-lane-runtime-test-six-lane-topology",
        six_lane_support_domain_id="six-lane-runtime-test-six-lane-support",
        six_lane_resonance_graph_id="six-lane-runtime-test-six-lane-resonance",
        six_lane_resonance_required_edges=six_lane_edges,
        expression_precision_authority_id="six-lane-runtime-test-expression-precision",
        expression_maximum_precision_bits=2048,
        pre_window_state_id="six-lane-runtime-test-pre-window",
        pre_window_memory_state_payload=(
            b'{"schema":"test.six_lane_runtime_mount.orchestrator_memory_state.v1"}'
        ),
        pre_window_l6_state_payload=(
            b'{"schema":"test.six_lane_runtime_mount.orchestrator_l6_state.v1"}'
        ),
        l5_governance_profile_id="six-lane-runtime-test-l5-profile",
        basin_profile_id="six-lane-runtime-test-basin-profile",
        basin_physical_profile_payload=(
            b'{"schema":"test.six_lane_runtime_mount.orchestrator_physical_profile.v1"}'
        ),
        basin_hbar=Fraction(1),
        basin_source_time_unit="six-lane-runtime-test-structural-time",
        basin_max_connected_component_dimension=1,
        basin_field_precision_bits=128,
    ), sensor_ports


def test_mount_six_lane_runtime_builds_and_cross_verifies_all_thirteen_authorities():
    kwargs, sensor_ports = _six_lane_runtime_kwargs()
    result = mount_six_lane_runtime(**kwargs)
    assert isinstance(result, MountedSixLaneRuntime)
    registry = result.receipt_registry

    # Every one of the thirteen named authorities independently re-verifies
    # against the SAME final registry -- one coherent, cross-verified
    # authority set, not isolated per-call registries.
    result.story_native_replay_profile.verify(registry)
    result.field_topology.verify(registry)
    assert len(result.field_topology.ordered_port_fibers) == 6
    assert {fiber.lane_id for fiber in result.field_topology.ordered_port_fibers} == {
        item.value for item in L6Lane
    }
    result.causal_grid.verify(registry)
    result.support_domain.verify(registry)
    result.resonance_graph.verify(registry)
    result.resonance_operator.verify(registry)
    assert len(result.sensor_states) == len(sensor_ports)
    for port, state in zip(sensor_ports, result.sensor_states, strict=True):
        state.verify(port=port, receipt_registry=registry)
    result.typed_language_kernel_binding.verify(registry)
    result.precision_authority.verify(registry)
    result.expression_mode_bank.verify(
        topology=result.field_topology, receipt_registry=registry
    )
    result.pre_window_state.verify(registry)
    result.l5_governance_profile.verify(result.field_topology, registry)
    result.story_global_uf_basin_profile.verify(
        story_profile=result.story_native_replay_profile,
        pre_window_state=result.pre_window_state,
        topology=result.field_topology,
        receipt_registry=registry,
    )


def test_mount_six_lane_runtime_rejects_an_unauthenticated_chemistry_manifest():
    kwargs, _sensor_ports = _six_lane_runtime_kwargs()
    kwargs["story_chemistry_authentication_key"] = b"the wrong candidate key entirely"
    with pytest.raises(ReceiptError, match="mounted story chemistry manifest"):
        mount_six_lane_runtime(**kwargs)


def test_mount_six_lane_runtime_construction_is_deterministic_across_cold_start_and_restart():
    """Section 9.2's stated proof requirement: cold start and restart
    construct bit-identical authority state.

    Calling :func:`mount_six_lane_runtime` twice with the identical real
    input bytes/parameters must produce, for every one of the thirteen
    mounted authorities, exactly the same receipt digests -- proving the
    construction itself is deterministic given the same authenticated
    inputs. (The actual checkpoint-to-disk persistence mechanism is
    out of scope for this stage; this is its real prerequisite.)
    """

    kwargs, _sensor_ports = _six_lane_runtime_kwargs()
    cold_start = mount_six_lane_runtime(**kwargs)
    restart = mount_six_lane_runtime(**kwargs)

    # The strongest, most direct proof: the two fully-extended registries
    # (every mounted receipt digest and its exact payload bytes) are
    # bit-identical, not merely equal in size.
    assert cold_start.receipt_registry.profile_binding_sha256 == (
        restart.receipt_registry.profile_binding_sha256
    )
    cold_start_records = tuple(
        sorted((record.digest, record.payload) for record in cold_start.receipt_registry.records)
    )
    restart_records = tuple(
        sorted((record.digest, record.payload) for record in restart.receipt_registry.records)
    )
    assert cold_start_records == restart_records

    # And explicitly, per authority, for the report: every one of the
    # thirteen named authorities' own receipt digest is bit-identical.
    assert cold_start.story_chemistry_runtime.manifest.receipt_sha256 == (
        restart.story_chemistry_runtime.manifest.receipt_sha256
    )
    assert cold_start.story_native_replay_profile.authority_receipt_sha256 == (
        restart.story_native_replay_profile.authority_receipt_sha256
    )
    assert cold_start.field_topology.authority_receipt_sha256 == (
        restart.field_topology.authority_receipt_sha256
    )
    assert cold_start.causal_grid.grid_receipt_sha256 == restart.causal_grid.grid_receipt_sha256
    assert cold_start.support_domain.authority_receipt_sha256 == (
        restart.support_domain.authority_receipt_sha256
    )
    assert cold_start.resonance_graph.authority_receipt_sha256 == (
        restart.resonance_graph.authority_receipt_sha256
    )
    assert cold_start.resonance_operator.authority_receipt_sha256 == (
        restart.resonance_operator.authority_receipt_sha256
    )
    assert tuple(state.authority_receipt_sha256 for state in cold_start.sensor_states) == tuple(
        state.authority_receipt_sha256 for state in restart.sensor_states
    )
    assert cold_start.typed_language_kernel_binding.authority_receipt_sha256 == (
        restart.typed_language_kernel_binding.authority_receipt_sha256
    )
    assert cold_start.precision_authority.authority_receipt_sha256 == (
        restart.precision_authority.authority_receipt_sha256
    )
    assert cold_start.expression_mode_bank.receipt_sha256 == (
        restart.expression_mode_bank.receipt_sha256
    )
    assert cold_start.pre_window_state.authority_receipt_sha256 == (
        restart.pre_window_state.authority_receipt_sha256
    )
    assert cold_start.l5_governance_profile.authority_receipt_sha256 == (
        restart.l5_governance_profile.authority_receipt_sha256
    )
    assert cold_start.story_global_uf_basin_profile.authority_receipt_sha256 == (
        restart.story_global_uf_basin_profile.authority_receipt_sha256
    )
