"""Attempted real, end-to-end proof of Step 5 (spec section 12, Step 5).

``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
section 12, Step 5's proof requirement is: *"every emitted scalar has a
fresh full-field expression and commit receipt."* This module attempts that
proof literally: (a) really learn one multimodal expression through Step 4's
already-committed ``real_experience_learning_pipeline.learn_one_real_multimodal_
expression`` (unmodified), (b) really stage the learned scalar through
``output.RememberedExpressionActuator`` (the same real actuator production
conversation code will use), (c) construct the two real Step-5 providers this
effort just built (``recall_story_runtime_resolver
.ProductionRecallStoryRuntimeResolver``, ``recall_replay_integrity_provider
.ProductionRecallReplayIntegrityProvider``) plus a real, independently
verifying ``recall_story_episode_archive.RecallStoryEpisode``/
``RecallStoryEpisodeArchive`` and ``recall_story_runtime_resolver
.MountedRecallStoryRuntimeCheckpoint``, wires all of it into a real
``fresh_recall_executor.FreshRecallClosedExperienceExecutor`` and
``fresh_recall_provider.FullFieldFreshRecallProvider``, and (d) attempts to
drive the Step-4-learned scalar through that real Step-5 stack.

The honest result: (a), (b), and the standalone construction of (c) all
succeed for real -- every assertion below is against genuine, independently
re-verified digests, never merely "no exception was raised". Step (d) does
NOT succeed, and it cannot with the code that exists in this repository
today. The reason is precise and reproducible, not a vague "doesn't fit":

Two disjoint, non-interoperable five-sense sensory subsystems
---------------------------------------------------------------
Step 4's real learning pipeline senses its two lived scenes through
``six_sense_boundary_owner.observe_six_sense_boundary`` (real emulated sight
via ``visual_krimelack``, real emulated sound via
``auditory_fragment_receipt``, real touch/smell/taste descriptors) and mounts
its own field topology directly via
``six_lane_runtime_mount.mount_support_domain``/
``mount_resonance_graph_and_operator`` (see
``real_experience_learning_pipeline.py``'s own docstring, chain steps 1-7).

Every real construction path for ``recall_story_episode_archive
.RecallStoryEpisode`` anywhere in this repository -- confirmed by
``recall_story_runtime_resolver.py``'s own module docstring investigation,
and independently re-confirmed here by direct inspection of
``story_native_replay.py`` -- instead senses its five lived instants through
``story_native_replay.execute_story_native_replay``'s own native-code/flux
model (``StorySensorPortAuthority.flux_for_code``, ``_derived_story_
observation``, schema ``glew.story_native_replay.derived_interval_
provenance.v1``), a completely different formula and provenance schema
from ``six_sense_boundary_owner.py``'s.

Every receipt in this codebase is content-addressed (SHA-256 of canonical
bytes): two evidence records only ever share a digest if they were built by
literally the same code from literally the same bytes. Since
``six_sense_boundary_owner.py`` and ``story_native_replay.py`` are two
independent code paths with different schemas, a
``output.MotifOutputBinding`` learned through Step 4's real pipeline can
NEVER carry the same ``sensory_evidence_receipt_sha256s`` (or even the same
``profile_binding_sha256`` -- Step 4 mounts its own topology directly, never
a ``story_native_replay.MountedStoryNativeReplayProfile``) as any
``RecallStoryEpisode`` ever admitted through ``story_native_replay.py``. No
coincidental collision is possible, and none should be forced.

Concretely, this means ``fresh_recall_executor.FreshRecallClosedExperienceExecutor
.execute``'s very first cross-universe step --
``self.archive.resolve(profile_binding_sha256=source_binding.profile_binding_sha256,
sensory_evidence_receipt_sha256s=source_binding.sensory_evidence_receipt_sha256s)``
-- genuinely, deterministically raises
``ReceiptError("no episode has this exact profile and complete sensory
receipt set")`` for a Step-4-learned binding, every time, by construction.
:func:`drive_fresh_recall_attempt` performs this exact call for real and lets
that real exception propagate; it does not swallow, retry, or paper over it.
The accompanying test module proves this precisely (asserting the exact
message and the exact call site), not merely "the pipeline doesn't work".

What a real fix would require (out of scope here, reported honestly)
------------------------------------------------------------------------
Closing this gap for real needs one of: (1) a shared five-sense
evidence-generation subsystem so live intake and archived recall speak the
same sensory schema, or (2) an explicit adapter that re-derives one
pipeline's evidence into the other's receipted shape without inventing
sensory content. Both are task-sized undertakings of their own -- exactly
the same honest category of gap ``real_experience_learning_pipeline.py``'s
own docstring already names for the missing production
``GlobalUFReplayProvider``, and that ``recall_story_runtime_resolver.py``'s
docstring already names for episodes needing to be "sealed against real
basin authorities from the start". This module does not attempt either
fix; it exists to make the gap between Step 4 and Step 5 concrete,
reproducible, and precisely located, per the governing spec's own demand for
honest reporting over forced shortcuts.

What IS proved real and working by this module
--------------------------------------------------
* Step 4's real learning pipeline runs unmodified and produces a genuine
  ``expression_learning.LearnedBindingState`` with a real learned
  ``output.MotifOutputBinding`` (see :func:`build_real_end_to_end_recall_attempt`).
* That learned binding is genuinely staged ``STAGED_PRIVATE`` by a real
  ``output.RememberedExpressionActuator.process`` call -- not a hand-built
  settlement -- exercising this task's own Part A fix
  (``fresh_recall_executor._verify_staged_source``) end to end for the
  first time against a production learning pipeline's real output.
* A complete, real, independently ``.verify()``-able Step-5 recall stack
  (episode, archive, checkpoint, resolver, integrity provider, language
  interface, executor, provider) is constructed from real production mount
  functions only -- mirroring
  ``tests/glew_runtime/test_recall_story_runtime_resolver.py``'s own proven
  construction recipe, reimplemented here with production-only imports (the
  same reason ``real_experience_learning_pipeline.py`` reimplements
  ``_physical_replay_bundle`` instead of importing it from ``tests/``).
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from .expression_learning import LearnedBindingState
from .field import (
    ExactComplex,
    ExactFieldState,
    MountedFieldTopology,
    PortFiber,
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
)
from .fresh_recall_executor import (
    FreshRecallClosedExperienceExecutor,
    MountedRecallLanguageInterface,
)
from .fresh_recall_provider import FullFieldFreshRecallProvider
from .global_uf import MountedPreWindowState, pre_window_state_receipt_payload
from .l6 import L6Lane
from .model import ReceiptError, ReceiptRegistry, receipt_sha256
from .operators import (
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
from .output import (
    CommittedMotifEvent,
    MotifBindingBank,
    MotifEventKind,
    MotifOutputBinding,
    OutputActuation,
    OutputStatus,
    RememberedExpressionActuator,
    committed_motif_event_receipt_payload,
)
from .real_experience_learning_pipeline import (
    RealMultimodalLearningResult,
    learn_one_real_multimodal_expression,
)
from .recall_reentry import fresh_recall_provider_authority_receipt_payload
from .recall_replay_integrity_provider import ProductionRecallReplayIntegrityProvider
from .recall_story_episode_archive import (
    RecallStoryEpisode,
    RecallStoryEpisodeArchive,
    create_recall_story_episode,
)
from .recall_story_runtime_resolver import (
    MountedRecallStoryRuntimeCheckpoint,
    ProductionRecallStoryRuntimeResolver,
    mount_recall_story_runtime_checkpoint,
)
from .six_lane_runtime_mount import (
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
from .story_chemistry import (
    StoryChemistryRuntime,
    StoryChemistryStatus,
    StoryPhysicalBoundaryEvent,
    StoryPhysicalBoundaryObservation,
    mount_packaged_production_story_chemistry,
    story_boundary_observation_receipt_payload,
)
from .story_native_replay import (
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


def _canonical_bytes(value: object) -> bytes:
    import json

    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _extend(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    return extend_receipt_registry(registry, *payloads)


def _unique_payloads(payloads: Sequence[bytes]) -> tuple[bytes, ...]:
    seen: dict[str, bytes] = {}
    ordered: list[bytes] = []
    for payload in payloads:
        digest = receipt_sha256(payload)
        prior = seen.get(digest)
        if prior is not None:
            if prior != payload:
                raise ReceiptError(
                    "real end-to-end recall pipeline receipt collision"
                )
            continue
        seen[digest] = payload
        ordered.append(payload)
    return tuple(ordered)


# ---------------------------------------------------------------------------
# The Step-5 "recall side": a real, self-consistent five-sense
# story-native-replay context, reimplemented here (production-only imports)
# from the exact recipe
# ``tests/glew_runtime/test_story_native_replay.py::_mounted_five_sense_runtime``
# and ``tests/glew_runtime/test_recall_story_runtime_resolver.py::_Scenario``
# already prove real, using ``story_chemistry.mount_packaged_production_
# story_chemistry`` -- the SAME real packaged production profile Step 4's own
# pipeline mounts -- rather than a test-only candidate manifest fixture.
# ---------------------------------------------------------------------------

_BASE_FLUX = {
    "sound": Fraction(1, 5),
    "smell": Fraction(1, 6),
    "taste": Fraction(-1, 7),
    "touch": Fraction(2, 9),
    "sight": Fraction(1, 4),
}
_QUANTUM = {
    "sound": Fraction(1, 20),
    "smell": Fraction(1, 24),
    "taste": Fraction(1, 28),
    "touch": Fraction(1, 18),
    "sight": Fraction(1, 16),
}


def _mount_real_sensor_port(
    port, *, scenario_id: str
) -> tuple[StorySensorPortAuthority, tuple[bytes, ...]]:
    lane = L6Lane(port.kernel_binding.lane_id)
    source_payload = _canonical_bytes(
        {
            "port_id": port.port_id,
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.story_port_source_authority.v1",
        }
    )
    values = dict(
        lane=lane,
        story_port_id=port.port_id,
        field_port_id=port.port_id,
        scene_coordinate_id=f"{scenario_id}-scene-{port.port_id}",
        base_raw_code=0,
        minimum_raw_code=-1,
        maximum_raw_code=1,
        flux_at_code_zero=_BASE_FLUX[lane.value],
        physical_quantum=_QUANTUM[lane.value],
        native_flux_unit=port.native_signal_unit,
        signal_offset=Fraction(0),
        signal_per_native_flux=Fraction(1),
        response_growth=Fraction(1, 2),
        natural_decay=Fraction(1, 8),
        phase_kappa=Fraction(1, 3),
        source_epoch=f"{scenario_id}-story-epoch",
        port_kind="authenticated_virtual_story_boundary",
        signal_physical_unit="dimensionless_story_response",
        boundary_source_authority_receipt_sha256=receipt_sha256(source_payload),
    )
    payload = story_sensor_port_authority_receipt_payload(**values)
    authority = StorySensorPortAuthority(
        **values, authority_receipt_sha256=receipt_sha256(payload)
    )
    return authority, (source_payload, payload)


def _boundary_observation_for_port(
    port: StorySensorPortAuthority, *, event_id: str
) -> tuple[StoryPhysicalBoundaryObservation, tuple[bytes, ...]]:
    provenance_payload = _canonical_bytes(
        {
            "event_id": event_id,
            "port_id": port.story_port_id,
            "schema": "glew.real_end_to_end_recall.boundary_observation_provenance.v1",
        }
    )
    observation_id = f"{event_id}:{port.story_port_id}"
    observation_payload = story_boundary_observation_receipt_payload(
        event_id=event_id,
        observation_id=observation_id,
        port_id=port.story_port_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(3),
        signed_native_flux=port.flux_for_code(port.base_raw_code),
        native_flux_unit=port.native_flux_unit,
        provenance_receipt_sha256=receipt_sha256(provenance_payload),
    )
    observation = StoryPhysicalBoundaryObservation(
        event_id=event_id,
        observation_id=observation_id,
        port_id=port.story_port_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(3),
        signed_native_flux=port.flux_for_code(port.base_raw_code),
        native_flux_unit=port.native_flux_unit,
        provenance_receipt_sha256=receipt_sha256(provenance_payload),
        provenance_receipt_payload=provenance_payload,
        observation_receipt_sha256=receipt_sha256(observation_payload),
        observation_receipt_payload=observation_payload,
    )
    return observation, (provenance_payload, observation_payload)


def _mount_real_five_sense_story_native_replay_context(
    *,
    scenario_id: str,
    chemistry_authentication_key: bytes,
    chemistry_authentication_key_id: str,
) -> tuple[
    MountedStoryNativeReplayProfile,
    MountedAuthenticatedClosedStoryBoundary,
    MountedPreWindowState,
    StoryChemistryRuntime,
    tuple[MountedStorySensorState, ...],
    ReceiptRegistry,
]:
    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=chemistry_authentication_key,
        runtime_key_id=chemistry_authentication_key_id,
    )
    if mounted.status is not StoryChemistryStatus.MOUNTED or mounted.runtime is None:
        raise ReceiptError(
            f"real production story chemistry failed to mount: {mounted.reason}"
        )
    story_runtime = mounted.runtime

    port_results = tuple(
        _mount_real_sensor_port(value, scenario_id=scenario_id)
        for value in story_runtime.manifest.ports
    )
    ports = tuple(value[0] for value in port_results)
    port_payloads = tuple(payload for value in port_results for payload in value[1])

    fibers = tuple(PortFiber(value.lane.value, value.field_port_id) for value in ports)
    topology_payload = field_topology_receipt_payload(
        f"{scenario_id}-five-sense-topology", fibers
    )
    topology = MountedFieldTopology(
        f"{scenario_id}-five-sense-topology",
        fibers,
        receipt_sha256(topology_payload),
    )

    grid_timestamps = (Fraction(1), Fraction(2), Fraction(3))
    grid_weights = (Fraction(1), Fraction(1), Fraction(1))
    grid_payload = causal_grid_receipt_payload(
        f"{scenario_id}-five-sense-grid", grid_timestamps, grid_weights
    )
    grid = CausalGrid(
        f"{scenario_id}-five-sense-grid",
        grid_timestamps,
        grid_weights,
        receipt_sha256(grid_payload),
    )

    topology_keys = tuple(value.field_key for value in ports)
    support_payload = support_domain_receipt_payload(
        f"{scenario_id}-five-sense-support", topology_keys
    )
    support = MountedSupportDomain(
        f"{scenario_id}-five-sense-support",
        topology_keys,
        receipt_sha256(support_payload),
    )

    edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(topology_keys[:-1], topology_keys[1:], strict=True)
    )
    graph_payload = resonance_graph_receipt_payload(
        f"{scenario_id}-five-sense-resonance", edges
    )
    graph = MountedResonanceGraph(
        f"{scenario_id}-five-sense-resonance", edges, receipt_sha256(graph_payload)
    )
    resonance_payload = resonance_operator_receipt_payload(
        f"{scenario_id}-five-sense-gamma-squared", 128
    )
    resonance = ResonanceOperatorAuthority(
        f"{scenario_id}-five-sense-gamma-squared", 128, receipt_sha256(resonance_payload)
    )

    adapter_payload = _canonical_bytes(
        {
            "adapter": "F=1+s/2; relevance identity",
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.kernel_adapter.v1",
        }
    )
    profile_payload = story_native_replay_profile_receipt_payload(
        profile_id=f"{scenario_id}-five-sense-native-replay",
        provider_id=f"{scenario_id}-frozen-kernel-provider",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        grid_receipt_sha256=grid.grid_receipt_sha256,
        support_domain_receipt_sha256=support.authority_receipt_sha256,
        resonance_graph_receipt_sha256=graph.authority_receipt_sha256,
        resonance_operator_receipt_sha256=resonance.authority_receipt_sha256,
        kernel_adapter_id=f"{scenario_id}-kernel-adapter",
        kernel_adapter_profile_receipt_sha256=receipt_sha256(adapter_payload),
        ports=ports,
    )
    profile = MountedStoryNativeReplayProfile(
        profile_id=f"{scenario_id}-five-sense-native-replay",
        provider_id=f"{scenario_id}-frozen-kernel-provider",
        topology=topology,
        grid=grid,
        support_domain=support,
        resonance_graph=graph,
        resonance_operator=resonance,
        kernel_adapter_id=f"{scenario_id}-kernel-adapter",
        kernel_adapter_profile_receipt_sha256=receipt_sha256(adapter_payload),
        ports=ports,
        authority_receipt_sha256=receipt_sha256(profile_payload),
        authority_receipt_payload=profile_payload,
    )

    sensor_states_list: list[MountedStorySensorState] = []
    sensor_payloads: list[bytes] = []
    for port in ports:
        state_payload = story_sensor_state_receipt_payload(
            field_port_id=port.field_port_id,
            source_epoch=port.source_epoch,
            last_source_index=-1,
            last_timestamp=Fraction(0),
            retained_signal=Fraction(0),
            phase_turns=Fraction(0),
            port_authority_receipt_sha256=port.authority_receipt_sha256,
        )
        sensor_states_list.append(
            MountedStorySensorState(
                field_port_id=port.field_port_id,
                source_epoch=port.source_epoch,
                last_source_index=-1,
                last_timestamp=Fraction(0),
                retained_signal=Fraction(0),
                phase_turns=Fraction(0),
                port_authority_receipt_sha256=port.authority_receipt_sha256,
                authority_receipt_sha256=receipt_sha256(state_payload),
            )
        )
        sensor_payloads.append(state_payload)
    sensor_states = tuple(sensor_states_list)

    chemistry_payload = story_replay_chemistry_state_receipt_payload(
        story_runtime=story_runtime, sensor_states=sensor_states
    )
    field_state_payload = _canonical_bytes(
        {
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.pre_window_field_state.v1",
        }
    )
    mode_state_payload = _canonical_bytes(
        {
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.pre_window_mode_state.v1",
        }
    )
    memory_state_payload = _canonical_bytes(
        {
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.pre_window_memory_state.v1",
        }
    )
    l6_state_payload = _canonical_bytes(
        {
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.pre_window_l6_state.v1",
        }
    )
    prewindow_payload = pre_window_state_receipt_payload(
        state_id=f"{scenario_id}-five-sense-pre-window",
        chemistry_state_receipt_sha256=receipt_sha256(chemistry_payload),
        field_state_receipt_sha256=receipt_sha256(field_state_payload),
        mode_state_receipt_sha256=receipt_sha256(mode_state_payload),
        memory_state_receipt_sha256=receipt_sha256(memory_state_payload),
        l6_state_receipt_sha256=receipt_sha256(l6_state_payload),
    )
    prewindow = MountedPreWindowState(
        f"{scenario_id}-five-sense-pre-window",
        receipt_sha256(chemistry_payload),
        receipt_sha256(field_state_payload),
        receipt_sha256(mode_state_payload),
        receipt_sha256(memory_state_payload),
        receipt_sha256(l6_state_payload),
        receipt_sha256(prewindow_payload),
    )

    boundary_event_id = f"{scenario_id}-five-sense-boundary"
    observation_results = tuple(
        _boundary_observation_for_port(value, event_id=boundary_event_id)
        for value in ports
    )
    boundary_event = StoryPhysicalBoundaryEvent(
        boundary_event_id, tuple(value[0] for value in observation_results)
    )
    boundary_payload = authenticated_closed_story_boundary_receipt_payload(
        boundary_id=f"{scenario_id}-five-sense-boundary-authority",
        event=boundary_event,
        profile=profile,
    )
    boundary = MountedAuthenticatedClosedStoryBoundary(
        f"{scenario_id}-five-sense-boundary-authority",
        boundary_event,
        profile.authority_receipt_sha256,
        receipt_sha256(boundary_payload),
        boundary_payload,
    )
    observation_payloads = tuple(
        payload for value in observation_results for payload in value[1]
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
                *sensor_payloads,
                chemistry_payload,
                field_state_payload,
                mode_state_payload,
                memory_state_payload,
                l6_state_payload,
                prewindow_payload,
                *observation_payloads,
                boundary_payload,
                *(value.payload for value in story_runtime.receipt_registry.records),
            )
        ),
    )
    profile.verify(registry)
    boundary.verify(profile=profile, receipt_registry=registry)
    return profile, boundary, prewindow, story_runtime, sensor_states, registry


@dataclass(frozen=True, slots=True)
class RealRecallSideContext:
    """Every real, mutually-consistent piece of one Step-5 recall side.

    Mirrors ``tests/glew_runtime/test_recall_story_runtime_resolver.py
    ::_Scenario`` exactly (production-only imports): the five-sense side
    from :func:`_mount_real_five_sense_story_native_replay_context`, plus a
    six-lane (language-fiber-extended) topology/support/resonance/precision/
    mode-bank/basin-profile/typed-language-kernel-binding, plus one
    ``MountedPreWindowState`` rebuilt so its ``field_state_receipt_sha256``/
    ``mode_state_receipt_sha256`` genuinely correspond to a real
    ``ExactFieldState``/``ExpressionModeBank`` -- the real, load-bearing
    requirement ``recall_story_runtime_resolver.py``'s own docstring
    documents for any episode meant to be resolved for real recall.
    """

    profile: MountedStoryNativeReplayProfile
    boundary: MountedAuthenticatedClosedStoryBoundary
    story_runtime: StoryChemistryRuntime
    sensor_states: tuple[MountedStorySensorState, ...]
    topology: MountedFieldTopology
    support_domain: MountedSupportDomain
    resonance_graph: MountedResonanceGraph
    resonance_operator: ResonanceOperatorAuthority
    precision_authority: object
    mode_bank: object
    pre_window_state: MountedPreWindowState
    basin_profile: object
    kernel_binding: object
    phase_calibration_id: str
    phase_kappa: Fraction
    source_epoch: str
    registry: ReceiptRegistry


def mount_real_recall_side_context(
    *,
    scenario_id: str,
    chemistry_authentication_key: bytes = (
        b"real end-to-end recall pipeline chemistry runtime secret"
    ),
    chemistry_authentication_key_id: str = (
        "real-end-to-end-recall-chemistry-runtime-key"
    ),
) -> RealRecallSideContext:
    (
        profile,
        boundary,
        old_pre_window_state,
        story_runtime,
        sensor_states,
        registry,
    ) = _mount_real_five_sense_story_native_replay_context(
        scenario_id=scenario_id,
        chemistry_authentication_key=chemistry_authentication_key,
        chemistry_authentication_key_id=chemistry_authentication_key_id,
    )

    language_port_id = f"{scenario_id}-recall-language-port"
    fibers = (
        PortFiber(L6Lane.LANGUAGE.value, language_port_id),
        *profile.topology.ordered_port_fibers,
    )
    topology_payload = field_topology_receipt_payload(
        f"{scenario_id}-recall-six-lane-topology", fibers
    )
    registry = extend_receipt_registry(registry, topology_payload)
    topology = MountedFieldTopology(
        f"{scenario_id}-recall-six-lane-topology",
        fibers,
        receipt_sha256(topology_payload),
    )
    topology.verify(registry)

    support_domain, registry = mount_support_domain(
        domain_id=f"{scenario_id}-recall-six-lane-support",
        topology=topology,
        receipt_registry=registry,
    )

    keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    edges = tuple(
        RequiredEdge(left, right) for left, right in zip(keys[:-1], keys[1:], strict=True)
    )
    resonance_graph, resonance_operator, registry = mount_resonance_graph_and_operator(
        graph_id=f"{scenario_id}-recall-six-lane-resonance",
        required_edges=edges,
        operator_id=profile.resonance_operator.operator_id,
        precision_bits=profile.resonance_operator.precision_bits,
        receipt_registry=registry,
        topology=topology,
    )

    precision_authority, registry = mount_precision_schedule_authority(
        authority_id=f"{scenario_id}-recall-precision",
        maximum_precision_bits=2048,
        receipt_registry=registry,
    )
    mode_bank, registry = mount_expression_mode_bank(
        topology=topology,
        precision_authority=precision_authority,
        receipt_registry=registry,
    )

    genesis_time = sensor_states[0].last_timestamp
    amplitudes = tuple(ExactComplex(Fraction(0)) for _ in range(topology.dimension))
    field_payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256, genesis_time, amplitudes
    )
    registry = extend_receipt_registry(registry, field_payload)
    initial_field_state = ExactFieldState(
        topology.authority_receipt_sha256,
        genesis_time,
        amplitudes,
        receipt_sha256(field_payload),
    )
    initial_field_state.verify(registry)

    chemistry_payload = story_replay_chemistry_state_receipt_payload(
        story_runtime=story_runtime, sensor_states=sensor_states
    )
    # Already mounted above (the five-sense context built this exact payload
    # for its own placeholder-paired pre-window state).
    registry.resolve(
        receipt_sha256(chemistry_payload), "recall six-lane chemistry state receipt"
    )

    pre_window_state, registry = mount_pre_window_state(
        state_id=f"{scenario_id}-recall-pre-window",
        chemistry_state_receipt_sha256=receipt_sha256(chemistry_payload),
        field_state=initial_field_state,
        mode_bank=mode_bank,
        memory_state_receipt_sha256=old_pre_window_state.memory_state_receipt_sha256,
        l6_state_receipt_sha256=old_pre_window_state.l6_state_receipt_sha256,
        topology=topology,
        receipt_registry=registry,
    )

    l5_profile, registry = mount_l5_governance_profile(
        profile_id=f"{scenario_id}-recall-l5",
        topology=topology,
        receipt_registry=registry,
    )

    physical_profile_payload = _canonical_bytes(
        {
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.basin_physical_profile.v1",
        }
    )
    basin_profile, registry = mount_story_global_uf_basin_profile(
        profile_id=f"{scenario_id}-recall-basin",
        story_profile=profile,
        physical_profile_payload=physical_profile_payload,
        initial_field_state=initial_field_state,
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source_time_unit="real-end-to-end-recall-structural-time",
        max_connected_component_dimension=1,
        field_precision_bits=128,
        precision_authority=precision_authority,
        mode_bank=mode_bank,
        l5_governance=l5_profile,
        pre_window_state=pre_window_state,
        topology=topology,
        receipt_registry=registry,
    )

    phase_calibration_id = f"{scenario_id}-recall-typed-phase"
    phase_kappa = Fraction(1, 7)
    source_epoch = f"{scenario_id}-recall-language-epoch"
    kernel_binding, registry = mount_typed_language_kernel_binding(
        adapter_id=f"{scenario_id}-recall-typed-adapter",
        interface_id=f"{scenario_id}-recall-typed-interface",
        phase_calibration_id=phase_calibration_id,
        phase_kappa=phase_kappa,
        derivation_payload=_canonical_bytes(
            {
                "scenario_id": scenario_id,
                "schema": "glew.real_end_to_end_recall.typed_derivation.v1",
            }
        ),
        receipt_registry=registry,
    )

    return RealRecallSideContext(
        profile=profile,
        boundary=boundary,
        story_runtime=story_runtime,
        sensor_states=sensor_states,
        topology=topology,
        support_domain=support_domain,
        resonance_graph=resonance_graph,
        resonance_operator=resonance_operator,
        precision_authority=precision_authority,
        mode_bank=mode_bank,
        pre_window_state=pre_window_state,
        basin_profile=basin_profile,
        kernel_binding=kernel_binding,
        phase_calibration_id=phase_calibration_id,
        phase_kappa=phase_kappa,
        source_epoch=source_epoch,
        registry=registry,
    )


def seal_real_recall_episode(context: RealRecallSideContext) -> RecallStoryEpisode:
    """Admit one real BASE episode over the recall side's first native port."""

    result = execute_story_native_replay(
        target_lane=context.profile.ports[0].lane,
        target_field_port_id=context.profile.ports[0].field_port_id,
        profile=context.profile,
        boundary=context.boundary,
        pre_window_state=context.pre_window_state,
        story_runtime=context.story_runtime,
        sensor_states=context.sensor_states,
        receipt_registry=context.registry,
    )
    if result.status is not StoryNativeReplayStatus.READY:
        raise ReceiptError(
            f"real story-native replay was not READY: {result.reason}"
        )
    episode = create_recall_story_episode(
        profile=context.profile,
        boundary=context.boundary,
        pre_window_state=context.pre_window_state,
        pre_window_story_runtime=context.story_runtime,
        pre_window_sensor_states=context.sensor_states,
        execution=result.executions[0],
    )
    episode.verify()
    return episode


@dataclass(frozen=True, slots=True)
class RealRecallStack:
    """Every real, wired Step-5 provider this effort built, plus the
    executor/provider that consume them -- ``FullFieldFreshRecallProvider``
    (already code-complete, never before constructed anywhere) included."""

    episode: RecallStoryEpisode
    archive: RecallStoryEpisodeArchive
    checkpoint: MountedRecallStoryRuntimeCheckpoint
    resolver: ProductionRecallStoryRuntimeResolver
    integrity_provider: ProductionRecallReplayIntegrityProvider
    language_interface: MountedRecallLanguageInterface
    executor: FreshRecallClosedExperienceExecutor
    checkpoint_registry: ReceiptRegistry


def build_real_recall_stack(
    *, scenario_id: str, context: RealRecallSideContext
) -> RealRecallStack:
    episode = seal_real_recall_episode(context)
    archive = RecallStoryEpisodeArchive().with_episode(episode)

    checkpoint = mount_recall_story_runtime_checkpoint(
        checkpoint_id=f"{scenario_id}-recall-checkpoint",
        story_profile=context.profile,
        boundary=context.boundary,
        pre_window_state=context.pre_window_state,
        story_runtime=context.story_runtime,
        sensor_states=context.sensor_states,
        topology=context.topology,
        support_domain=context.support_domain,
        resonance_graph=context.resonance_graph,
        resonance_operator=context.resonance_operator,
        basin_profile=context.basin_profile,
        typed_language_kernel_binding=context.kernel_binding,
        typed_language_phase_calibration_id=context.phase_calibration_id,
        typed_language_phase_kappa=context.phase_kappa,
        typed_language_source_epoch=context.source_epoch,
        receipt_registry=context.registry,
    )
    checkpoint.verify()

    resolver = ProductionRecallStoryRuntimeResolver(checkpoint=checkpoint)
    integrity_provider = ProductionRecallReplayIntegrityProvider()
    language_interface, checkpoint_registry = resolver.mount_language_interface(
        genesis_marker=f"{scenario_id}-recall-genesis-turn",
        receipt_registry=checkpoint.receipt_registry,
    )

    executor = FreshRecallClosedExperienceExecutor(
        executor_id=f"{scenario_id}-fresh-recall-executor",
        archive=archive,
        runtime_resolver=resolver,
        language_interface=language_interface,
        integrity_provider=integrity_provider,
    )

    return RealRecallStack(
        episode=episode,
        archive=archive,
        checkpoint=checkpoint,
        resolver=resolver,
        integrity_provider=integrity_provider,
        language_interface=language_interface,
        executor=executor,
        checkpoint_registry=checkpoint_registry,
    )


# ---------------------------------------------------------------------------
# Step 4's real learned content, genuinely staged through the real actuator.
# ---------------------------------------------------------------------------


def stage_learned_content_second_occurrence(
    *, state: LearnedBindingState, scenario_id: str
) -> tuple[
    CommittedMotifEvent,
    OutputActuation,
    MotifOutputBinding,
    MotifBindingBank,
    ReceiptRegistry,
]:
    """Genuinely stage the learned content scalar a second physical time.

    ``state.initial_event`` (built by ``expression_learning._make_initial_event``)
    is keyed to the STATE's ``initial_relation`` (the root scene) throughout,
    while the one binding in ``state.output_bank`` was learned from the
    CONTENT scene's own relation -- two genuinely different closed
    experiences with different sensory evidence. Pairing them would fail
    ``fresh_recall_executor._verify_staged_source``'s existing (unchanged by
    this task's Part A fix) motif/sensory-evidence cross-check for a reason
    that has nothing to do with fresh recall: they are honestly not the same
    coexperience. What this function builds instead -- exactly mirroring
    ``expression_learning._make_initial_event``'s own pattern, but
    self-consistently keyed to CONTENT's own relation (``state.pending_relation``,
    which after one non-closing ``learn_committed_binding_transaction`` call
    is exactly the content scene's ``CommittedModeRelation``) -- is a second,
    genuinely real ``CommittedMotifEvent`` representing the content scene's
    exact five-sense episode being lived and recognized a second physical
    time. Every digest used is a real, already-computed authority's own
    digest (the relation's expression/commit/L6/fact-strand/sensory receipts,
    the binding's own motif and binding receipts); only the source-state/
    transition-edge/result-state bookkeeping triple is freshly minted, the
    same way ``_make_initial_event`` mints its own.
    """

    current_relation = state.pending_relation
    if current_relation is None:
        raise ReceiptError(
            "learned binding state has no pending relation to stage a second "
            "real occurrence from"
        )
    output_bank = state.output_bank
    if len(output_bank.bindings) != 1:
        raise ReceiptError(
            "this pipeline expects the learning result to carry exactly one "
            "learned output binding"
        )
    source_binding = output_bank.bindings[0]

    registry = state.receipt_registry
    source_state_payload = _canonical_bytes(
        {
            "relation_receipt_sha256": current_relation.authority_receipt_sha256,
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.second_occurrence_source_state.v1",
        }
    )
    result_state_payload = _canonical_bytes(
        {
            "binding_receipt_sha256": source_binding.binding_receipt_sha256,
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.second_occurrence_result_state.v1",
        }
    )
    edge_payload = _canonical_bytes(
        {
            "result_state_receipt_sha256": receipt_sha256(result_state_payload),
            "scenario_id": scenario_id,
            "schema": "glew.real_end_to_end_recall.second_occurrence_transition_edge.v1",
            "source_state_receipt_sha256": receipt_sha256(source_state_payload),
        }
    )
    registry = _extend(registry, source_state_payload, result_state_payload, edge_payload)

    event_kwargs = dict(
        expression_id=state.expression_id,
        event_id=f"{scenario_id}-content-second-occurrence",
        event_kind=MotifEventKind.CONTENT,
        profile_binding_sha256=registry.profile_binding_sha256,
        motif_receipt_sha256=source_binding.motif_receipt_sha256,
        closed_experience_receipt_sha256=(
            current_relation.closed_experience_receipt_sha256
        ),
        fact_strand_receipt_sha256=current_relation.fact_strand_receipt_sha256,
        sensory_evidence_receipt_sha256s=(
            current_relation.sensory_evidence_receipt_sha256s
        ),
        full_field_state_receipt_sha256=current_relation.expression_receipt_sha256,
        field_commit_receipt_sha256=current_relation.commit_receipt_sha256,
        dominant_motif_commit_receipt_sha256=source_binding.binding_receipt_sha256,
        corrected_l6_lock_receipt_sha256=current_relation.l6_evaluation_receipt_sha256,
        output_binding_bank_receipt_sha256=output_bank.bank_receipt_sha256,
        source_state_receipt_sha256=receipt_sha256(source_state_payload),
        transition_edge_receipt_sha256=receipt_sha256(edge_payload),
        result_state_receipt_sha256=receipt_sha256(result_state_payload),
        expression_close_authority_receipt_sha256=None,
    )
    event_payload = committed_motif_event_receipt_payload(**event_kwargs)
    registry = _extend(registry, event_payload)
    event = CommittedMotifEvent(
        **event_kwargs, event_receipt_sha256=receipt_sha256(event_payload)
    )
    event.verify(registry)

    actuator = RememberedExpressionActuator(
        expression_id=state.expression_id,
        profile_binding_sha256=registry.profile_binding_sha256,
        initial_state_receipt_sha256=event.source_state_receipt_sha256,
    )
    staged = actuator.process(
        event=event, binding_bank=output_bank, receipt_registry=registry
    )
    if staged.receipt.status is not OutputStatus.STAGED_PRIVATE:
        raise ReceiptError(
            "second real occurrence of the learned content scalar did not "
            f"stage privately: {staged.receipt.status}/{staged.receipt.reason}/"
            f"{staged.receipt.failure_detail}"
        )
    return event, staged, source_binding, output_bank, registry


# ---------------------------------------------------------------------------
# Full attempt: real learning + real staging + real Step-5 stack, wired
# together as far as the two disjoint sensory subsystems allow.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RealEndToEndRecallAttempt:
    learning_result: RealMultimodalLearningResult
    source_event: CommittedMotifEvent
    staged_output: OutputActuation
    source_binding: MotifOutputBinding
    output_bank: MotifBindingBank
    learning_registry: ReceiptRegistry
    recall_context: RealRecallSideContext
    recall_stack: RealRecallStack
    provider: FullFieldFreshRecallProvider


def build_real_end_to_end_recall_attempt(
    *, scenario_id: str = "real-end-to-end-recall"
) -> RealEndToEndRecallAttempt:
    """Perform every leg of the Step-5 proof that genuinely succeeds today.

    Real Step-4 learning, real staging, and a real, independently-verifying
    Step-5 recall stack are all constructed for real here. See the module
    docstring for the one leg (bridging the two) that this function
    deliberately does NOT attempt -- that is :func:`drive_fresh_recall_attempt`'s
    job, and it is expected to fail closed.
    """

    learning_result = learn_one_real_multimodal_expression(
        scenario_id=f"{scenario_id}-learning"
    )
    state = learning_result.learned
    state.verify()

    (
        source_event,
        staged_output,
        source_binding,
        output_bank,
        learning_registry,
    ) = stage_learned_content_second_occurrence(state=state, scenario_id=scenario_id)

    recall_context = mount_real_recall_side_context(scenario_id=scenario_id)
    recall_stack = build_real_recall_stack(
        scenario_id=scenario_id, context=recall_context
    )

    provider_id = f"{scenario_id}-fresh-recall-provider"
    provider_authority_payload = fresh_recall_provider_authority_receipt_payload(
        provider_id=provider_id,
        profile_binding_sha256=learning_registry.profile_binding_sha256,
    )
    learning_registry = _extend(learning_registry, provider_authority_payload)
    provider = FullFieldFreshRecallProvider(
        provider_id=provider_id,
        profile_binding_sha256=learning_registry.profile_binding_sha256,
        executor=recall_stack.executor,
        motif_kinds=state.motif_kinds,
        authority_receipt_sha256=receipt_sha256(provider_authority_payload),
    )

    return RealEndToEndRecallAttempt(
        learning_result=learning_result,
        source_event=source_event,
        staged_output=staged_output,
        source_binding=source_binding,
        output_bank=output_bank,
        learning_registry=learning_registry,
        recall_context=recall_context,
        recall_stack=recall_stack,
        provider=provider,
    )


def drive_fresh_recall_attempt(attempt: RealEndToEndRecallAttempt):
    """Attempt Step (d): drive the learned scalar through real fresh recall.

    This makes the exact real production call
    (``FullFieldFreshRecallProvider.settle`` -> ``FreshRecallClosedExperienceExecutor
    .execute`` -> ``RecallStoryEpisodeArchive.resolve``) with Step 4's real
    learned binding as ``source_binding``. Per the module docstring, this is
    expected to raise a real, precise ``model.ReceiptError`` -- this
    function does not catch it; the caller (the accompanying test) asserts
    the exact message.
    """

    return attempt.provider.settle(
        source_event=attempt.source_event,
        staged_output=attempt.staged_output,
        source_binding=attempt.source_binding,
        output_binding_bank=attempt.output_bank,
        stable_mode_motif_bank=attempt.learning_result.learned.stable_bank,
        receipt_registry=attempt.learning_registry,
    )


__all__ = (
    "RealEndToEndRecallAttempt",
    "RealRecallSideContext",
    "RealRecallStack",
    "build_real_end_to_end_recall_attempt",
    "build_real_recall_stack",
    "drive_fresh_recall_attempt",
    "mount_real_recall_side_context",
    "seal_real_recall_episode",
    "stage_learned_content_second_occurrence",
)
