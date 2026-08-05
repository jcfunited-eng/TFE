"""Tests for the production ``RecallStoryRuntimeResolver`` (spec section 9.6).

Seals one real archived episode using ONLY real production mount functions
(``story_native_replay.execute_story_native_replay`` /
``recall_story_episode_archive.create_recall_story_episode`` /
``six_lane_runtime_mount``'s ``mount_*`` functions), builds one real
:class:`~dsf_ai_service.glew_runtime.recall_story_runtime_resolver.MountedRecallStoryRuntimeCheckpoint`,
resolves the episode back through :class:`ProductionRecallStoryRuntimeResolver`,
and asserts the resolved runtime's receipts genuinely match the episode's own
recorded receipts byte-for-byte -- never merely "no exception was raised".

No receipt is hand-synthesized: every payload here is produced by calling the
real ``*_receipt_payload`` functions the production modules themselves
already export, exactly as every other test in this package does.
"""

from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.field import (
    ExactComplex,
    ExactFieldState,
    MountedFieldTopology,
    PortFiber,
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
)
from dsf_ai_service.glew_runtime.fresh_recall_executor import (
    MountedRecallLanguageInterface,
    MountedRecallStoryRuntime,
)
from dsf_ai_service.glew_runtime.l6 import L6Lane
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.operators import RequiredEdge
from dsf_ai_service.glew_runtime.recall_story_episode_archive import (
    RecallStoryEpisode,
    create_recall_story_episode,
)
from dsf_ai_service.glew_runtime.recall_story_runtime_resolver import (
    MountedRecallStoryRuntimeCheckpoint,
    ProductionRecallStoryRuntimeResolver,
    mount_recall_story_runtime_checkpoint,
)
from dsf_ai_service.glew_runtime.six_lane_runtime_mount import (
    extend_receipt_registry,
    mount_expression_mode_bank,
    mount_l5_governance_profile,
    mount_precision_schedule_authority,
    mount_pre_window_state,
    mount_resonance_graph_and_operator,
    mount_story_global_uf_basin_profile,
    mount_support_domain,
    mount_typed_language_kernel_binding,
)
from dsf_ai_service.glew_runtime.story_chemistry import StoryPhysicalBoundaryEvent
from dsf_ai_service.glew_runtime.story_native_replay import (
    MountedAuthenticatedClosedStoryBoundary,
    StoryNativeReplayStatus,
    authenticated_closed_story_boundary_receipt_payload,
    execute_story_native_replay,
    story_replay_chemistry_state_receipt_payload,
)

from tests.glew_runtime.test_story_native_replay import (
    _boundary_observation,
    _mounted_five_sense_runtime,
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _merge(registry: ReceiptRegistry, other: ReceiptRegistry) -> ReceiptRegistry:
    assert registry.profile_binding_sha256 == other.profile_binding_sha256
    mounted = {value.digest: value.payload for value in registry.records}
    for record in other.records:
        assert mounted.get(record.digest, record.payload) == record.payload
        mounted[record.digest] = record.payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, mounted[key]) for key in sorted(mounted)),
    )


class _Scenario:
    """Every real piece needed to build and later re-derive one episode.

    Building a ``MountedRecallStoryRuntimeCheckpoint`` requires a
    ``MountedPreWindowState`` whose field/mode digests genuinely correspond
    to a real six-lane ``ExactFieldState``/``ExpressionModeBank`` (see the
    resolver module's own docstring for why this is a genuine, load-bearing
    upstream requirement, not a test convenience) -- so this scenario builds
    that consistent pre-window state itself, mirroring
    ``tests/glew_runtime/test_six_lane_runtime_mount.py::_six_lane_basin_context``,
    rather than reusing ``_mounted_five_sense_runtime``'s own placeholder-based
    one, which structurally cannot pass ``MountedStoryGlobalUFBasinProfile.verify``.
    """

    def __init__(self, *, suffix: str) -> None:
        (
            self.profile,
            self.boundary,
            self.old_pre_window_state,
            self.story_runtime,
            self.sensor_states,
            registry,
        ) = _mounted_five_sense_runtime()

        language_port_id = f"recall-resolver-language-port{suffix}"
        fibers = (
            PortFiber(L6Lane.LANGUAGE.value, language_port_id),
            *self.profile.topology.ordered_port_fibers,
        )
        topology_payload = field_topology_receipt_payload(
            f"recall-resolver-six-lane-topology{suffix}", fibers
        )
        registry = extend_receipt_registry(registry, topology_payload)
        self.topology = MountedFieldTopology(
            f"recall-resolver-six-lane-topology{suffix}",
            fibers,
            receipt_sha256(topology_payload),
        )
        self.topology.verify(registry)

        self.support_domain, registry = mount_support_domain(
            domain_id=f"recall-resolver-six-lane-support{suffix}",
            topology=self.topology,
            receipt_registry=registry,
        )

        keys = tuple(fiber.key for fiber in self.topology.ordered_port_fibers)
        edges = tuple(
            RequiredEdge(left, right)
            for left, right in zip(keys[:-1], keys[1:], strict=True)
        )
        self.resonance_graph, self.resonance_operator, registry = (
            mount_resonance_graph_and_operator(
                graph_id=f"recall-resolver-six-lane-resonance{suffix}",
                required_edges=edges,
                operator_id=self.profile.resonance_operator.operator_id,
                precision_bits=self.profile.resonance_operator.precision_bits,
                receipt_registry=registry,
                topology=self.topology,
            )
        )
        # Reused unchanged, exactly mirroring mount_six_lane_runtime's own
        # "same operator_id/precision_bits => identical operator" pattern.
        assert self.resonance_operator == self.profile.resonance_operator

        self.precision_authority, registry = mount_precision_schedule_authority(
            authority_id=f"recall-resolver-precision{suffix}",
            maximum_precision_bits=2048,
            receipt_registry=registry,
        )
        self.mode_bank, registry = mount_expression_mode_bank(
            topology=self.topology,
            precision_authority=self.precision_authority,
            receipt_registry=registry,
        )

        genesis_time = self.sensor_states[0].last_timestamp
        amplitudes = tuple(
            ExactComplex(Fraction(0)) for _ in range(self.topology.dimension)
        )
        field_payload = exact_field_state_receipt_payload(
            self.topology.authority_receipt_sha256, genesis_time, amplitudes
        )
        registry = extend_receipt_registry(registry, field_payload)
        self.initial_field_state = ExactFieldState(
            self.topology.authority_receipt_sha256,
            genesis_time,
            amplitudes,
            receipt_sha256(field_payload),
        )
        self.initial_field_state.verify(registry)

        chemistry_payload = story_replay_chemistry_state_receipt_payload(
            story_runtime=self.story_runtime, sensor_states=self.sensor_states
        )
        # Already mounted: _mounted_five_sense_runtime built this exact
        # payload for its own (placeholder-paired) pre-window state.
        assert registry.resolve(receipt_sha256(chemistry_payload)) == chemistry_payload

        self.pre_window_state, registry = mount_pre_window_state(
            state_id=f"recall-resolver-pre-window{suffix}",
            chemistry_state_receipt_sha256=receipt_sha256(chemistry_payload),
            field_state=self.initial_field_state,
            mode_bank=self.mode_bank,
            memory_state_receipt_sha256=self.old_pre_window_state.memory_state_receipt_sha256,
            l6_state_receipt_sha256=self.old_pre_window_state.l6_state_receipt_sha256,
            topology=self.topology,
            receipt_registry=registry,
        )

        self.l5_profile, registry = mount_l5_governance_profile(
            profile_id=f"recall-resolver-l5{suffix}",
            topology=self.topology,
            receipt_registry=registry,
        )

        physical_profile_payload = _canonical(
            {
                "schema": "test.recall_story_runtime_resolver.basin_physical_profile.v1",
                "suffix": suffix,
            }
        )
        self.basin_profile, registry = mount_story_global_uf_basin_profile(
            profile_id=f"recall-resolver-basin{suffix}",
            story_profile=self.profile,
            physical_profile_payload=physical_profile_payload,
            initial_field_state=self.initial_field_state,
            hbar=Fraction(1),
            hamiltonian=(),
            local_rates=(),
            source_time_unit="recall-resolver-structural-time",
            max_connected_component_dimension=1,
            field_precision_bits=128,
            precision_authority=self.precision_authority,
            mode_bank=self.mode_bank,
            l5_governance=self.l5_profile,
            pre_window_state=self.pre_window_state,
            topology=self.topology,
            receipt_registry=registry,
        )

        self.kernel_binding, registry = mount_typed_language_kernel_binding(
            adapter_id=f"recall-resolver-typed-adapter{suffix}",
            interface_id=f"recall-resolver-typed-interface{suffix}",
            phase_calibration_id=f"recall-resolver-typed-phase{suffix}",
            phase_kappa=Fraction(1, 7),
            derivation_payload=_canonical(
                {
                    "schema": "test.recall_story_runtime_resolver.typed_derivation.v1",
                    "suffix": suffix,
                }
            ),
            receipt_registry=registry,
        )
        self.phase_calibration_id = f"recall-resolver-typed-phase{suffix}"
        self.phase_kappa = Fraction(1, 7)
        self.source_epoch = f"recall-resolver-language-epoch{suffix}"

        self.registry = registry
        self.suffix = suffix

    def replay(
        self, *, boundary: MountedAuthenticatedClosedStoryBoundary, registry: ReceiptRegistry
    ):
        result = execute_story_native_replay(
            target_lane=self.profile.ports[0].lane,
            target_field_port_id=self.profile.ports[0].field_port_id,
            profile=self.profile,
            boundary=boundary,
            pre_window_state=self.pre_window_state,
            story_runtime=self.story_runtime,
            sensor_states=self.sensor_states,
            receipt_registry=registry,
        )
        assert result.status is StoryNativeReplayStatus.READY, result.reason
        return result

    def seal_episode(
        self, *, boundary: MountedAuthenticatedClosedStoryBoundary, registry: ReceiptRegistry
    ) -> RecallStoryEpisode:
        result = self.replay(boundary=boundary, registry=registry)
        return create_recall_story_episode(
            profile=self.profile,
            boundary=boundary,
            pre_window_state=self.pre_window_state,
            pre_window_story_runtime=self.story_runtime,
            pre_window_sensor_states=self.sensor_states,
            execution=result.executions[0],
        )

    def checkpoint(self) -> MountedRecallStoryRuntimeCheckpoint:
        return mount_recall_story_runtime_checkpoint(
            checkpoint_id=f"recall-resolver-checkpoint{self.suffix}",
            story_profile=self.profile,
            boundary=self.boundary,
            pre_window_state=self.pre_window_state,
            story_runtime=self.story_runtime,
            sensor_states=self.sensor_states,
            topology=self.topology,
            support_domain=self.support_domain,
            resonance_graph=self.resonance_graph,
            resonance_operator=self.resonance_operator,
            basin_profile=self.basin_profile,
            typed_language_kernel_binding=self.kernel_binding,
            typed_language_phase_calibration_id=self.phase_calibration_id,
            typed_language_phase_kappa=self.phase_kappa,
            typed_language_source_epoch=self.source_epoch,
            receipt_registry=self.registry,
        )

    def alternate_boundary(self) -> tuple[MountedAuthenticatedClosedStoryBoundary, ReceiptRegistry]:
        """One different, independently-valid boundary over the SAME profile."""

        event_id = f"recall-resolver-alt-boundary-event{self.suffix}"
        mounted_observations = tuple(
            _boundary_observation(event_id=event_id, port=value) for value in self.profile.ports
        )
        event = StoryPhysicalBoundaryEvent(
            event_id, tuple(value[0] for value in mounted_observations)
        )
        boundary_payload = authenticated_closed_story_boundary_receipt_payload(
            boundary_id=f"recall-resolver-alt-boundary{self.suffix}",
            event=event,
            profile=self.profile,
        )
        boundary = MountedAuthenticatedClosedStoryBoundary(
            f"recall-resolver-alt-boundary{self.suffix}",
            event,
            self.profile.authority_receipt_sha256,
            receipt_sha256(boundary_payload),
            boundary_payload,
        )
        extra_payloads = tuple(
            payload for value in mounted_observations for payload in (value[1], value[2])
        ) + (boundary_payload,)
        registry = extend_receipt_registry(self.registry, *extra_payloads)
        boundary.verify(profile=self.profile, receipt_registry=registry)
        assert boundary.authority_receipt_sha256 != self.boundary.authority_receipt_sha256
        return boundary, registry


@pytest.fixture(scope="module")
def real_scenario() -> _Scenario:
    return _Scenario(suffix="")


@pytest.fixture(scope="module")
def real_episode(real_scenario: _Scenario) -> RecallStoryEpisode:
    return real_scenario.seal_episode(
        boundary=real_scenario.boundary, registry=real_scenario.registry
    )


@pytest.fixture(scope="module")
def real_checkpoint(real_scenario: _Scenario) -> MountedRecallStoryRuntimeCheckpoint:
    return real_scenario.checkpoint()


# ---------------------------------------------------------------------------
# MountedRecallStoryRuntimeCheckpoint
# ---------------------------------------------------------------------------


def test_checkpoint_mounts_and_verifies_from_real_authorities(real_checkpoint):
    real_checkpoint.verify()  # independent re-verification, not just construction


def test_checkpoint_tamper_fails_closed(real_scenario, real_checkpoint):
    alt_boundary, alt_registry = real_scenario.alternate_boundary()
    tampered = replace(real_checkpoint, boundary=alt_boundary, receipt_registry=alt_registry)
    # The swapped boundary's own receipt digest differs from what the
    # checkpoint's envelope receipt was originally bound to -- verify()
    # must fail closed rather than silently accept the substitution.
    with pytest.raises(ReceiptError, match="differs from its own receipt"):
        tampered.verify()


def test_checkpoint_rejects_untyped_authority():
    with pytest.raises(ReceiptError, match="mounted story native-replay profile"):
        mount_recall_story_runtime_checkpoint(
            checkpoint_id="bad-checkpoint",
            story_profile=object(),  # type: ignore[arg-type]
            boundary=object(),  # type: ignore[arg-type]
            pre_window_state=object(),  # type: ignore[arg-type]
            story_runtime=object(),  # type: ignore[arg-type]
            sensor_states=(),
            topology=object(),  # type: ignore[arg-type]
            support_domain=object(),  # type: ignore[arg-type]
            resonance_graph=object(),  # type: ignore[arg-type]
            resonance_operator=object(),  # type: ignore[arg-type]
            basin_profile=object(),  # type: ignore[arg-type]
            typed_language_kernel_binding=object(),  # type: ignore[arg-type]
            typed_language_phase_calibration_id="x",
            typed_language_phase_kappa=Fraction(1, 7),
            typed_language_source_epoch="x",
            receipt_registry=ReceiptRegistry.from_payloads(
                profile_payload=b'{"schema":"unrelated.v1"}', receipt_payloads=()
            ),
        )


# ---------------------------------------------------------------------------
# ProductionRecallStoryRuntimeResolver.resolve_runtime
# ---------------------------------------------------------------------------


def test_resolver_resolves_the_real_episode_byte_identically(
    real_scenario, real_episode, real_checkpoint
):
    resolver = ProductionRecallStoryRuntimeResolver(checkpoint=real_checkpoint)
    incoming_registry = ReceiptRegistry(
        real_scenario.profile.authority_receipt_sha256, real_episode.receipt_records
    )

    runtime = resolver.resolve_runtime(
        episode=real_episode, receipt_registry=incoming_registry
    )

    assert isinstance(runtime, MountedRecallStoryRuntime)

    # Not "no exception raised" -- assert the actual digests match, byte for
    # byte, against exactly what the episode itself recorded at seal time.
    assert runtime.episode_receipt_sha256 == real_episode.episode_receipt_sha256
    assert (
        runtime.story_profile.authority_receipt_sha256
        == real_episode.profile_binding_sha256
    )
    assert runtime.boundary.authority_receipt_sha256 == real_episode.boundary_receipt_sha256
    assert (
        runtime.pre_window_state.authority_receipt_sha256
        == real_episode.pre_window_state_receipt_sha256
    )
    assert tuple(
        value.receipt_sha256 for value in runtime.story_runtime.states
    ) == real_episode.pre_window_receiver_state_receipt_sha256s
    assert tuple(
        value.authority_receipt_sha256 for value in runtime.sensor_states
    ) == real_episode.pre_window_sensor_state_receipt_sha256s
    assert (
        runtime.basin_profile.authority_receipt_sha256
        == real_checkpoint.basin_profile.authority_receipt_sha256
    )
    assert runtime.topology.authority_receipt_sha256 == real_checkpoint.topology.authority_receipt_sha256

    # Full independent re-verification against the fully merged registry --
    # exercising MountedRecallStoryRuntime.verify's own real production path.
    merged = _merge(
        incoming_registry,
        ReceiptRegistry(
            incoming_registry.profile_binding_sha256, runtime.receipt_registry.records
        ),
    )
    runtime.verify(episode=real_episode, receipt_registry=merged)


def test_resolver_resolves_two_independent_ports_of_the_same_episode_family(
    real_scenario, real_checkpoint
):
    """A second, genuinely different (different target port -> different
    evidence-preparation receipt) but still real BASE episode, sharing the
    same profile/boundary/pre-window, resolves through the SAME checkpoint."""

    other_port = real_scenario.profile.ports[1]
    result = execute_story_native_replay(
        target_lane=other_port.lane,
        target_field_port_id=other_port.field_port_id,
        profile=real_scenario.profile,
        boundary=real_scenario.boundary,
        pre_window_state=real_scenario.pre_window_state,
        story_runtime=real_scenario.story_runtime,
        sensor_states=real_scenario.sensor_states,
        receipt_registry=real_scenario.registry,
    )
    assert result.status is StoryNativeReplayStatus.READY, result.reason
    other_episode = create_recall_story_episode(
        profile=real_scenario.profile,
        boundary=real_scenario.boundary,
        pre_window_state=real_scenario.pre_window_state,
        pre_window_story_runtime=real_scenario.story_runtime,
        pre_window_sensor_states=real_scenario.sensor_states,
        execution=result.executions[0],
    )

    resolver = ProductionRecallStoryRuntimeResolver(checkpoint=real_checkpoint)
    incoming_registry = ReceiptRegistry(
        real_scenario.profile.authority_receipt_sha256, other_episode.receipt_records
    )
    runtime = resolver.resolve_runtime(
        episode=other_episode, receipt_registry=incoming_registry
    )
    assert runtime.episode_receipt_sha256 == other_episode.episode_receipt_sha256
    merged = _merge(
        incoming_registry,
        ReceiptRegistry(
            incoming_registry.profile_binding_sha256, runtime.receipt_registry.records
        ),
    )
    runtime.verify(episode=other_episode, receipt_registry=merged)


def test_resolver_rejects_a_real_episode_sealed_against_a_different_boundary(
    real_scenario, real_checkpoint
):
    """Fail closed: a genuinely real, self-consistent episode (verifies fine
    on its own) that was archived against a DIFFERENT (but equally real)
    boundary than the one this resolver's checkpoint carries must never
    silently resolve -- it must be rejected before a wrong runtime is ever
    handed back."""

    alt_boundary, alt_registry = real_scenario.alternate_boundary()
    mismatched_episode = real_scenario.seal_episode(
        boundary=alt_boundary, registry=alt_registry
    )
    mismatched_episode.verify()  # the episode itself is genuinely valid
    assert (
        mismatched_episode.boundary_receipt_sha256
        != real_checkpoint.boundary.authority_receipt_sha256
    )

    resolver = ProductionRecallStoryRuntimeResolver(checkpoint=real_checkpoint)
    incoming_registry = ReceiptRegistry(
        real_scenario.profile.authority_receipt_sha256,
        mismatched_episode.receipt_records,
    )
    with pytest.raises(ReceiptError, match="boundary differs"):
        resolver.resolve_runtime(
            episode=mismatched_episode, receipt_registry=incoming_registry
        )


def test_resolver_rejects_a_tampered_episode(real_scenario, real_episode, real_checkpoint):
    tampered = replace(
        real_episode, boundary_receipt_sha256="a" * 64
    )
    resolver = ProductionRecallStoryRuntimeResolver(checkpoint=real_checkpoint)
    incoming_registry = ReceiptRegistry(
        real_scenario.profile.authority_receipt_sha256, tampered.receipt_records
    )
    with pytest.raises(ReceiptError):
        resolver.resolve_runtime(episode=tampered, receipt_registry=incoming_registry)


def test_resolver_rejects_a_non_registry_receipt_registry(real_episode, real_checkpoint):
    resolver = ProductionRecallStoryRuntimeResolver(checkpoint=real_checkpoint)
    with pytest.raises(ReceiptError):
        resolver.resolve_runtime(episode=real_episode, receipt_registry=object())  # type: ignore[arg-type]


def test_resolver_rejects_a_non_episode():
    checkpoint_stub = object()
    with pytest.raises(ReceiptError):
        ProductionRecallStoryRuntimeResolver(checkpoint=checkpoint_stub)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# MountedRecallLanguageInterface production construction path
# ---------------------------------------------------------------------------


def test_resolver_mounts_a_verifying_language_interface_synced_to_basin_genesis(
    real_checkpoint,
):
    resolver = ProductionRecallStoryRuntimeResolver(checkpoint=real_checkpoint)
    interface, registry = resolver.mount_language_interface(
        genesis_marker="recall-resolver-test-turn-1",
        receipt_registry=real_checkpoint.receipt_registry,
    )
    assert isinstance(interface, MountedRecallLanguageInterface)
    interface.verify(registry)  # independent re-verification
    assert (
        interface.initial_state.last_timestamp
        == real_checkpoint.basin_profile.initial_field_state.source_time
    )
    assert interface.initial_state.last_source_index == -1
    assert interface.initial_state.disrupted is False
    assert interface.phase_kappa == real_checkpoint.typed_language_phase_kappa
    assert interface.kernel_binding == real_checkpoint.typed_language_kernel_binding


def test_language_interface_mount_fails_closed_on_a_foreign_kernel_binding(
    real_checkpoint,
):
    from dsf_ai_service.glew_runtime.recall_story_runtime_resolver import (
        mount_recall_language_interface_genesis,
    )
    from dsf_ai_service.glew_runtime.language import MountedTypedLanguageKernelBinding

    foreign = replace(
        real_checkpoint.typed_language_kernel_binding,
        adapter_id="a-different-unmounted-adapter-id",
    )
    assert isinstance(foreign, MountedTypedLanguageKernelBinding)
    with pytest.raises(ReceiptError, match="differs from receipt"):
        mount_recall_language_interface_genesis(
            kernel_binding=foreign,
            phase_calibration_id=real_checkpoint.typed_language_phase_calibration_id,
            phase_kappa=real_checkpoint.typed_language_phase_kappa,
            source_epoch=real_checkpoint.typed_language_source_epoch,
            source_time=real_checkpoint.basin_profile.initial_field_state.source_time,
            genesis_marker="foreign-binding-marker",
            receipt_registry=real_checkpoint.receipt_registry,
        )
