"""Exact native story-sensor replay through the frozen L0--L4 kernel.

This module closes one deliberately narrow runtime gap.  A mounted story
boundary contains the base physical observation for every native story port.
One selected port exposes one integer scene parameter.  The executor restores
the same immutable pre-window chemistry and sensor state for the base and for
every admissible adjacent integer code, evolves the authenticated story
chemistry, generates the causal native samples from the mounted physical
growth/decay law, and runs the existing frozen L0--L4 provider.

The result is a real ``NativePortReplayBundle``.  No response callback, test
law, desired rank, threshold, manual branch label, L5 disposition, language
commit, or output surface exists here.  The branch and cell identifiers are a
lossless encoding of the actual frozen-kernel categorical trajectory and
seven-field sign/zero geometry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from typing import Iterable, Sequence

from .closed_experience import (
    ClosedExperienceEvidencePreparation,
    ClosedExperienceProviderUnknown,
    KernelNativeInputSample,
    KernelNativeInputStream,
    ProviderStatus,
    kernel_native_input_receipt_payload,
    prepare_closed_experience_evidence,
    source_evidence_stream_receipt_payload,
)
from .field import MountedFieldTopology, PortFiber
from .global_uf import MountedPreWindowState
from .l6 import FIELD_ORDER, L6Lane
from .model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from .operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    ResonanceOperatorAuthority,
)
from .physical_l6_tangents import (
    ExactL4Response,
    MountedNativePerturbationProfile,
    MountedNativeResponseSet,
    MountedSameBranchCellProof,
    NativeL4ReplayResponse,
    NativePortReplayBundle,
    NativeReplayCase,
    SensorNativeCoordinate,
    enumerate_native_replay_cases,
    native_l4_replay_response_receipt_payload,
    native_perturbation_profile_receipt_payload,
    native_response_set_receipt_payload,
    same_branch_cell_proof_receipt_payload,
)
from .story_chemistry import (
    Binary64RoundingStatus,
    StoryChemistryRuntime,
    StoryChemistryStatus,
    StoryPhysicalBoundaryEvent,
    StoryPhysicalBoundaryObservation,
    evolve_story_chemistry_event,
    story_boundary_observation_receipt_payload,
)


STORY_NATIVE_REPLAY_OPERATOR_ID = "glew.story_native_replay.frozen_l0_l4.v1"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "exact fraction")
    return f"{value.numerator}/{value.denominator}"


def _integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReceiptError(f"{field_name} must be an exact integer")
    return value


def _mounted_exact(
    registry: ReceiptRegistry,
    digest: str,
    expected: bytes,
    field_name: str,
) -> None:
    mounted = registry.resolve(digest, field_name)
    if mounted != expected or receipt_sha256(expected) != digest:
        raise ReceiptError(f"{field_name} differs from mounted authority bytes")


def _extend_records(
    registry: ReceiptRegistry,
    records: Iterable[ReceiptRecord],
) -> ReceiptRegistry:
    mounted = {value.digest: value.payload for value in registry.records}
    additions: dict[str, bytes] = {}
    for record in records:
        if not isinstance(record, ReceiptRecord):
            raise ReceiptError("story replay registry received a non-receipt record")
        prior = mounted.get(record.digest)
        if prior is not None and prior != record.payload:
            raise ReceiptError("story replay receipt digest collision")
        added = additions.get(record.digest)
        if added is not None and added != record.payload:
            raise ReceiptError("story replay repeated a digest with different bytes")
        additions[record.digest] = record.payload
    new_records = tuple(
        ReceiptRecord(digest, additions[digest])
        for digest in sorted(additions)
        if digest not in mounted
    )
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        (*registry.records, *new_records),
    )


def _extend_payloads(
    registry: ReceiptRegistry,
    payloads: Iterable[bytes],
) -> ReceiptRegistry:
    records = []
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("story replay generated an empty receipt payload")
        records.append(ReceiptRecord(receipt_sha256(payload), payload))
    return _extend_records(registry, records)


@dataclass(frozen=True, slots=True)
class StorySensorPortAuthority:
    """One physical story port and its one native scene coordinate."""

    lane: L6Lane
    story_port_id: str
    field_port_id: str
    scene_coordinate_id: str
    base_raw_code: int
    minimum_raw_code: int
    maximum_raw_code: int
    flux_at_code_zero: Fraction
    physical_quantum: Fraction
    native_flux_unit: str
    signal_offset: Fraction
    signal_per_native_flux: Fraction
    response_growth: Fraction
    natural_decay: Fraction
    phase_kappa: Fraction
    source_epoch: str
    port_kind: str
    signal_physical_unit: str
    boundary_source_authority_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.lane, L6Lane) or self.lane is L6Lane.LANGUAGE:
            raise ReceiptError("story sensor port requires a non-language L6 lane")
        for value, field_name in (
            (self.story_port_id, "story port id"),
            (self.field_port_id, "field port id"),
            (self.scene_coordinate_id, "scene coordinate id"),
            (self.native_flux_unit, "native flux unit"),
            (self.source_epoch, "source epoch"),
            (self.port_kind, "port kind"),
            (self.signal_physical_unit, "signal physical unit"),
        ):
            require_identifier(value, field_name)
        for value, field_name in (
            (self.base_raw_code, "base raw code"),
            (self.minimum_raw_code, "minimum raw code"),
            (self.maximum_raw_code, "maximum raw code"),
        ):
            _integer(value, field_name)
        if self.minimum_raw_code > self.maximum_raw_code:
            raise ReceiptError("story sensor raw-code bounds are inverted")
        if not self.minimum_raw_code <= self.base_raw_code <= self.maximum_raw_code:
            raise ReceiptError("story sensor base code lies outside mounted bounds")
        for value, field_name in (
            (self.flux_at_code_zero, "flux at code zero"),
            (self.physical_quantum, "physical quantum"),
            (self.signal_offset, "signal offset"),
            (self.signal_per_native_flux, "signal per native flux"),
            (self.response_growth, "response growth"),
            (self.natural_decay, "natural decay"),
            (self.phase_kappa, "phase kappa"),
        ):
            require_fraction(value, field_name)
        if self.physical_quantum <= 0:
            raise ReceiptError("story sensor physical quantum must be positive")
        if self.response_growth < 0 or self.natural_decay < 0:
            raise ReceiptError("story response growth and decay cannot be negative")
        sha256_digest(
            self.boundary_source_authority_receipt_sha256,
            "boundary source authority receipt",
        )
        sha256_digest(self.authority_receipt_sha256, "story port authority receipt")

    @property
    def field_key(self) -> tuple[str, str]:
        return (self.lane.value, self.field_port_id)

    def flux_for_code(self, raw_code: int) -> Fraction:
        _integer(raw_code, "story replay raw code")
        if not self.minimum_raw_code <= raw_code <= self.maximum_raw_code:
            raise ReceiptError("story replay raw code lies outside mounted bounds")
        return self.flux_at_code_zero + self.physical_quantum * raw_code

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.boundary_source_authority_receipt_sha256,
            "boundary source authority receipt",
        )
        expected = story_sensor_port_authority_receipt_payload(
            lane=self.lane,
            story_port_id=self.story_port_id,
            field_port_id=self.field_port_id,
            scene_coordinate_id=self.scene_coordinate_id,
            base_raw_code=self.base_raw_code,
            minimum_raw_code=self.minimum_raw_code,
            maximum_raw_code=self.maximum_raw_code,
            flux_at_code_zero=self.flux_at_code_zero,
            physical_quantum=self.physical_quantum,
            native_flux_unit=self.native_flux_unit,
            signal_offset=self.signal_offset,
            signal_per_native_flux=self.signal_per_native_flux,
            response_growth=self.response_growth,
            natural_decay=self.natural_decay,
            phase_kappa=self.phase_kappa,
            source_epoch=self.source_epoch,
            port_kind=self.port_kind,
            signal_physical_unit=self.signal_physical_unit,
            boundary_source_authority_receipt_sha256=(
                self.boundary_source_authority_receipt_sha256
            ),
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "story port authority receipt",
        )


def story_sensor_port_authority_receipt_payload(
    *,
    lane: L6Lane,
    story_port_id: str,
    field_port_id: str,
    scene_coordinate_id: str,
    base_raw_code: int,
    minimum_raw_code: int,
    maximum_raw_code: int,
    flux_at_code_zero: Fraction,
    physical_quantum: Fraction,
    native_flux_unit: str,
    signal_offset: Fraction,
    signal_per_native_flux: Fraction,
    response_growth: Fraction,
    natural_decay: Fraction,
    phase_kappa: Fraction,
    source_epoch: str,
    port_kind: str,
    signal_physical_unit: str,
    boundary_source_authority_receipt_sha256: str,
) -> bytes:
    if not isinstance(lane, L6Lane) or lane is L6Lane.LANGUAGE:
        raise ReceiptError("story sensor receipt requires a non-language lane")
    return _canonical_bytes(
        {
            "boundary_source_authority_receipt_sha256": sha256_digest(
                boundary_source_authority_receipt_sha256,
                "boundary source authority receipt",
            ),
            "field_port_id": require_identifier(field_port_id, "field port id"),
            "lane": lane.value,
            "native_parameter": {
                "base_raw_code": _integer(base_raw_code, "base raw code"),
                "coordinate_id": require_identifier(
                    scene_coordinate_id, "scene coordinate id"
                ),
                "flux_at_code_zero": _fraction_text(flux_at_code_zero),
                "maximum_raw_code": _integer(maximum_raw_code, "maximum raw code"),
                "minimum_raw_code": _integer(minimum_raw_code, "minimum raw code"),
                "physical_quantum": _fraction_text(physical_quantum),
            },
            "native_flux_unit": require_identifier(
                native_flux_unit, "native flux unit"
            ),
            "native_response": {
                "equation": (
                    "s_next=s_prev+growth*(signal_offset+signal_per_native_flux*"
                    "signed_flux-s_prev)-natural_decay*s_prev"
                ),
                "natural_decay": _fraction_text(natural_decay),
                "phase_equation": "phase_next=phase_prev+phase_kappa*s_next*delta_t",
                "phase_kappa": _fraction_text(phase_kappa),
                "response_growth": _fraction_text(response_growth),
                "signal_offset": _fraction_text(signal_offset),
                "signal_per_native_flux": _fraction_text(signal_per_native_flux),
            },
            "port_kind": require_identifier(port_kind, "port kind"),
            "schema": "glew.story_native_replay.sensor_port_authority.v1",
            "signal_physical_unit": require_identifier(
                signal_physical_unit, "signal physical unit"
            ),
            "source_epoch": require_identifier(source_epoch, "source epoch"),
            "story_port_id": require_identifier(story_port_id, "story port id"),
        }
    )


def story_native_replay_profile_receipt_payload(
    *,
    profile_id: str,
    provider_id: str,
    topology_authority_receipt_sha256: str,
    grid_receipt_sha256: str,
    support_domain_receipt_sha256: str,
    resonance_graph_receipt_sha256: str,
    resonance_operator_receipt_sha256: str,
    kernel_adapter_id: str,
    kernel_adapter_profile_receipt_sha256: str,
    ports: tuple[StorySensorPortAuthority, ...],
) -> bytes:
    require_identifier(profile_id, "story replay profile id")
    require_identifier(provider_id, "story replay provider id")
    require_identifier(kernel_adapter_id, "kernel adapter id")
    for digest, field_name in (
        (topology_authority_receipt_sha256, "topology receipt"),
        (grid_receipt_sha256, "grid receipt"),
        (support_domain_receipt_sha256, "support-domain receipt"),
        (resonance_graph_receipt_sha256, "resonance-graph receipt"),
        (resonance_operator_receipt_sha256, "resonance-operator receipt"),
        (kernel_adapter_profile_receipt_sha256, "kernel-adapter profile receipt"),
    ):
        sha256_digest(digest, field_name)
    if not isinstance(ports, tuple) or not ports:
        raise ReceiptError("story replay profile requires native ports")
    return _canonical_bytes(
        {
            "grid_receipt_sha256": grid_receipt_sha256,
            "kernel_adapter": {
                "adapter_id": kernel_adapter_id,
                "profile_receipt_sha256": kernel_adapter_profile_receipt_sha256,
            },
            "operator": STORY_NATIVE_REPLAY_OPERATOR_ID,
            "ports": [
                {
                    "authority_receipt_sha256": value.authority_receipt_sha256,
                    "field_port_id": value.field_port_id,
                    "lane": value.lane.value,
                    "story_port_id": value.story_port_id,
                }
                for value in ports
            ],
            "profile_id": profile_id,
            "provider_id": provider_id,
            "resonance_graph_receipt_sha256": resonance_graph_receipt_sha256,
            "resonance_operator_receipt_sha256": (
                resonance_operator_receipt_sha256
            ),
            "schema": "glew.story_native_replay.runtime_profile.v1",
            "support_domain_receipt_sha256": support_domain_receipt_sha256,
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedStoryNativeReplayProfile:
    profile_id: str
    provider_id: str
    topology: MountedFieldTopology
    grid: CausalGrid
    support_domain: MountedSupportDomain
    resonance_graph: MountedResonanceGraph
    resonance_operator: ResonanceOperatorAuthority
    kernel_adapter_id: str
    kernel_adapter_profile_receipt_sha256: str
    ports: tuple[StorySensorPortAuthority, ...]
    authority_receipt_sha256: str
    authority_receipt_payload: bytes

    def __post_init__(self) -> None:
        require_identifier(self.profile_id, "story replay profile id")
        require_identifier(self.provider_id, "story replay provider id")
        require_identifier(self.kernel_adapter_id, "kernel adapter id")
        sha256_digest(
            self.kernel_adapter_profile_receipt_sha256,
            "kernel-adapter profile receipt",
        )
        sha256_digest(self.authority_receipt_sha256, "story replay profile receipt")
        if not isinstance(self.ports, tuple) or not all(
            isinstance(value, StorySensorPortAuthority) for value in self.ports
        ):
            raise ReceiptError("story replay ports must be typed and immutable")
        story_ids = tuple(value.story_port_id for value in self.ports)
        field_keys = tuple(value.field_key for value in self.ports)
        if story_ids != tuple(sorted(story_ids)) or len(set(story_ids)) != len(story_ids):
            raise ReceiptError("story replay ports are not canonical and unique")
        if len(set(field_keys)) != len(field_keys):
            raise ReceiptError("story replay profile repeats a field port")

    def port_for_story(self, story_port_id: str) -> StorySensorPortAuthority:
        for value in self.ports:
            if value.story_port_id == story_port_id:
                return value
        raise ReceiptError("story boundary names an unmounted story port")

    def port_for_field(self, lane: L6Lane, field_port_id: str) -> StorySensorPortAuthority:
        for value in self.ports:
            if value.lane is lane and value.field_port_id == field_port_id:
                return value
        raise ReceiptError("requested native replay port is not mounted")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        if receipt_registry.profile_binding_sha256 != self.authority_receipt_sha256:
            raise ReceiptError("story replay registry belongs to another runtime profile")
        self.topology.verify(receipt_registry)
        self.grid.verify(receipt_registry)
        self.support_domain.verify(receipt_registry)
        self.resonance_graph.verify(receipt_registry)
        self.resonance_operator.verify(receipt_registry)
        receipt_registry.resolve(
            self.kernel_adapter_profile_receipt_sha256,
            "kernel-adapter profile receipt",
        )
        for value in self.ports:
            value.verify(receipt_registry)
        if tuple(value.field_key for value in self.ports) != tuple(
            value.key for value in self.topology.ordered_port_fibers
        ):
            raise ReceiptError("story replay ports do not exactly cover field topology")
        expected = story_native_replay_profile_receipt_payload(
            profile_id=self.profile_id,
            provider_id=self.provider_id,
            topology_authority_receipt_sha256=self.topology.authority_receipt_sha256,
            grid_receipt_sha256=self.grid.grid_receipt_sha256,
            support_domain_receipt_sha256=self.support_domain.authority_receipt_sha256,
            resonance_graph_receipt_sha256=self.resonance_graph.authority_receipt_sha256,
            resonance_operator_receipt_sha256=(
                self.resonance_operator.authority_receipt_sha256
            ),
            kernel_adapter_id=self.kernel_adapter_id,
            kernel_adapter_profile_receipt_sha256=(
                self.kernel_adapter_profile_receipt_sha256
            ),
            ports=self.ports,
        )
        if self.authority_receipt_payload != expected:
            raise ReceiptError("story replay profile object differs from canonical bytes")
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "story replay profile receipt",
        )


def authenticated_closed_story_boundary_receipt_payload(
    *,
    boundary_id: str,
    event: StoryPhysicalBoundaryEvent,
    profile: MountedStoryNativeReplayProfile,
) -> bytes:
    require_identifier(boundary_id, "authenticated story boundary id")
    event.verify()
    return _canonical_bytes(
        {
            "boundary_id": boundary_id,
            "event_id": event.event_id,
            "observations": [
                {
                    "boundary_source_authority_receipt_sha256": (
                        profile.port_for_story(
                            value.port_id
                        ).boundary_source_authority_receipt_sha256
                    ),
                    "observation_receipt_sha256": value.observation_receipt_sha256,
                    "port_id": value.port_id,
                    "provenance_receipt_sha256": value.provenance_receipt_sha256,
                }
                for value in event.observations
            ],
            "profile_receipt_sha256": profile.authority_receipt_sha256,
            "schema": "glew.story_native_replay.authenticated_closed_boundary.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class MountedAuthenticatedClosedStoryBoundary:
    boundary_id: str
    event: StoryPhysicalBoundaryEvent
    profile_receipt_sha256: str
    authority_receipt_sha256: str
    authority_receipt_payload: bytes

    def verify(
        self,
        *,
        profile: MountedStoryNativeReplayProfile,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        require_identifier(self.boundary_id, "authenticated story boundary id")
        if self.profile_receipt_sha256 != profile.authority_receipt_sha256:
            raise ReceiptError("story boundary belongs to another runtime profile")
        self.event.verify()
        if tuple(value.port_id for value in self.event.observations) != tuple(
            value.story_port_id for value in profile.ports
        ):
            raise ReceiptError("story boundary does not exactly cover mounted story ports")
        for observation, port in zip(
            self.event.observations, profile.ports, strict=True
        ):
            if observation.native_flux_unit != port.native_flux_unit:
                raise ReceiptError("story boundary unit differs from mounted port authority")
            if observation.signed_native_flux != port.flux_for_code(port.base_raw_code):
                raise ReceiptError("story boundary flux differs from mounted base raw code")
            receipt_registry.resolve(
                port.boundary_source_authority_receipt_sha256,
                "boundary source authority receipt",
            )
            _mounted_exact(
                receipt_registry,
                observation.provenance_receipt_sha256,
                observation.provenance_receipt_payload,
                "story observation provenance receipt",
            )
            _mounted_exact(
                receipt_registry,
                observation.observation_receipt_sha256,
                observation.observation_receipt_payload,
                "story observation receipt",
            )
        expected = authenticated_closed_story_boundary_receipt_payload(
            boundary_id=self.boundary_id,
            event=self.event,
            profile=profile,
        )
        if self.authority_receipt_payload != expected:
            raise ReceiptError("authenticated story boundary object was altered")
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "authenticated story boundary receipt",
        )


def story_sensor_state_receipt_payload(
    *,
    field_port_id: str,
    source_epoch: str,
    last_source_index: int,
    last_timestamp: Fraction,
    retained_signal: Fraction,
    phase_turns: Fraction,
    port_authority_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "field_port_id": require_identifier(field_port_id, "field port id"),
            "last_source_index": _integer(last_source_index, "last source index"),
            "last_timestamp": _fraction_text(last_timestamp),
            "phase_turns": _fraction_text(phase_turns),
            "port_authority_receipt_sha256": sha256_digest(
                port_authority_receipt_sha256, "story port authority receipt"
            ),
            "retained_signal": _fraction_text(retained_signal),
            "schema": "glew.story_native_replay.sensor_state.v1",
            "source_epoch": require_identifier(source_epoch, "source epoch"),
        }
    )


@dataclass(frozen=True, slots=True)
class MountedStorySensorState:
    field_port_id: str
    source_epoch: str
    last_source_index: int
    last_timestamp: Fraction
    retained_signal: Fraction
    phase_turns: Fraction
    port_authority_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.field_port_id, "field port id")
        require_identifier(self.source_epoch, "source epoch")
        _integer(self.last_source_index, "last source index")
        if self.last_source_index < -1:
            raise ReceiptError("last source index cannot be less than -1")
        require_fraction(self.last_timestamp, "last timestamp")
        require_fraction(self.retained_signal, "retained signal")
        require_fraction(self.phase_turns, "phase turns")
        if not -1 <= self.retained_signal <= 1:
            raise ReceiptError("retained story signal lies outside [-1,1]")
        sha256_digest(self.port_authority_receipt_sha256, "story port receipt")
        sha256_digest(self.authority_receipt_sha256, "story sensor state receipt")

    def verify(
        self,
        *,
        port: StorySensorPortAuthority,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if (
            self.field_port_id != port.field_port_id
            or self.source_epoch != port.source_epoch
            or self.port_authority_receipt_sha256 != port.authority_receipt_sha256
        ):
            raise ReceiptError("story sensor state belongs to another mounted port")
        expected = story_sensor_state_receipt_payload(
            field_port_id=self.field_port_id,
            source_epoch=self.source_epoch,
            last_source_index=self.last_source_index,
            last_timestamp=self.last_timestamp,
            retained_signal=self.retained_signal,
            phase_turns=self.phase_turns,
            port_authority_receipt_sha256=self.port_authority_receipt_sha256,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "story sensor state receipt",
        )


def story_replay_chemistry_state_receipt_payload(
    *,
    story_runtime: StoryChemistryRuntime,
    sensor_states: tuple[MountedStorySensorState, ...],
) -> bytes:
    if not isinstance(story_runtime, StoryChemistryRuntime):
        raise ReceiptError("story chemistry runtime is missing")
    return _canonical_bytes(
        {
            "manifest_receipt_sha256": story_runtime.manifest.receipt_sha256,
            "receiver_state_receipt_sha256s": [
                value.receipt_sha256 for value in story_runtime.states
            ],
            "schema": "glew.story_native_replay.pre_window_chemistry_state.v1",
            "sensor_state_receipt_sha256s": [
                value.authority_receipt_sha256 for value in sensor_states
            ],
        }
    )


class StoryNativeReplayStatus(str, Enum):
    READY = "ready"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class StoryKernelReplayExecution:
    case: NativeReplayCase
    streams: tuple[EvidenceStream, ...]
    kernel_inputs: tuple[KernelNativeInputStream, ...]
    preparation: ClosedExperienceEvidencePreparation
    final_story_runtime: StoryChemistryRuntime
    final_sensor_states: tuple[MountedStorySensorState, ...]
    target_l4_response: ExactL4Response
    target_source_stream_receipt_sha256: str
    target_l0_l4_trace_receipt_sha256: str
    target_branch_id: str
    target_cell_id: str
    source_operator_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class StoryNativeReplayResult:
    status: StoryNativeReplayStatus
    reason: str
    bundle: NativePortReplayBundle | None
    replay_cases: tuple[NativeReplayCase, ...]
    executions: tuple[StoryKernelReplayExecution, ...]
    receipt_registry: ReceiptRegistry


def _verify_pre_window(
    *,
    profile: MountedStoryNativeReplayProfile,
    pre_window_state: MountedPreWindowState,
    story_runtime: StoryChemistryRuntime,
    sensor_states: tuple[MountedStorySensorState, ...],
    receipt_registry: ReceiptRegistry,
) -> None:
    pre_window_state.verify(receipt_registry)
    if tuple(value.field_port_id for value in sensor_states) != tuple(
        value.field_port_id for value in profile.ports
    ):
        raise ReceiptError("pre-window sensor state does not exactly cover story ports")
    story_state_ids = tuple(value.port_id for value in story_runtime.states)
    for port, sensor_state in zip(profile.ports, sensor_states, strict=True):
        sensor_state.verify(port=port, receipt_registry=receipt_registry)
        if port.story_port_id not in story_state_ids:
            raise ReceiptError("pre-window chemistry lacks a mounted story port")
        if story_runtime.state(port.story_port_id).source_time != sensor_state.last_timestamp:
            raise ReceiptError("chemistry and native sensor state are at different times")
        if sensor_state.last_timestamp >= profile.grid.timestamps[0]:
            raise ReceiptError("pre-window sensor state does not precede causal samples")
    expected_chemistry = story_replay_chemistry_state_receipt_payload(
        story_runtime=story_runtime,
        sensor_states=sensor_states,
    )
    if receipt_sha256(expected_chemistry) != pre_window_state.chemistry_state_receipt_sha256:
        raise ReceiptError("pre-window chemistry receipt names different native state")
    _mounted_exact(
        receipt_registry,
        pre_window_state.chemistry_state_receipt_sha256,
        expected_chemistry,
        "pre-window chemistry state receipt",
    )


def _verify_boundary_times(
    *,
    boundary: MountedAuthenticatedClosedStoryBoundary,
    profile: MountedStoryNativeReplayProfile,
    story_runtime: StoryChemistryRuntime,
) -> None:
    for observation in boundary.event.observations:
        if observation.source_time_start != story_runtime.state(
            observation.port_id
        ).source_time:
            raise ReceiptError("closed story boundary does not start at pre-window state")
        if observation.source_time_end != profile.grid.timestamps[-1]:
            raise ReceiptError("closed story boundary does not end at causal-grid boundary")


def _derived_story_observation(
    *,
    execution_id: str,
    interval_index: int,
    source_time_start: Fraction,
    source_time_end: Fraction,
    raw_code: int,
    base_observation: StoryPhysicalBoundaryObservation,
    port: StorySensorPortAuthority,
) -> StoryPhysicalBoundaryObservation:
    event_id = f"{execution_id}:chemistry:{interval_index:08d}"
    observation_id = f"{event_id}:{port.story_port_id}"
    flux = port.flux_for_code(raw_code)
    provenance_payload = _canonical_bytes(
        {
            "authenticated_closed_observation_receipt_sha256": (
                base_observation.observation_receipt_sha256
            ),
            "execution_id": execution_id,
            "interval_index": interval_index,
            "native_parameter": {
                "coordinate_id": port.scene_coordinate_id,
                "raw_code": raw_code,
                "signed_flux": _fraction_text(flux),
            },
            "operator": STORY_NATIVE_REPLAY_OPERATOR_ID,
            "port_authority_receipt_sha256": port.authority_receipt_sha256,
            "schema": "glew.story_native_replay.derived_interval_provenance.v1",
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
        }
    )
    observation_payload = story_boundary_observation_receipt_payload(
        event_id=event_id,
        observation_id=observation_id,
        port_id=port.story_port_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        signed_native_flux=flux,
        native_flux_unit=port.native_flux_unit,
        provenance_receipt_sha256=receipt_sha256(provenance_payload),
    )
    return StoryPhysicalBoundaryObservation(
        event_id=event_id,
        observation_id=observation_id,
        port_id=port.story_port_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        signed_native_flux=flux,
        native_flux_unit=port.native_flux_unit,
        provenance_receipt_sha256=receipt_sha256(provenance_payload),
        provenance_receipt_payload=provenance_payload,
        observation_receipt_sha256=receipt_sha256(observation_payload),
        observation_receipt_payload=observation_payload,
    )


def _relevance_receipt_payload(
    *,
    execution_id: str,
    port: StorySensorPortAuthority,
    chemical_receipt_sha256s: Sequence[str],
    rounding_receipt_sha256s: Sequence[str],
) -> bytes:
    return _canonical_bytes(
        {
            "chemical_evolution_receipt_sha256s": list(
                chemical_receipt_sha256s
            ),
            "execution_id": execution_id,
            "field_port_id": port.field_port_id,
            "lane": port.lane.value,
            "rounding_receipt_sha256s": list(rounding_receipt_sha256s),
            "schema": "glew.story_native_replay.causal_relevance_sequence.v1",
        }
    )


def _execute_streams(
    *,
    execution_id: str,
    profile: MountedStoryNativeReplayProfile,
    boundary: MountedAuthenticatedClosedStoryBoundary,
    story_runtime: StoryChemistryRuntime,
    sensor_states: tuple[MountedStorySensorState, ...],
    raw_codes: dict[str, int],
    receipt_registry: ReceiptRegistry,
) -> tuple[
    tuple[EvidenceStream, ...],
    tuple[KernelNativeInputStream, ...],
    StoryChemistryRuntime,
    tuple[MountedStorySensorState, ...],
    ReceiptRegistry,
]:
    runtime = story_runtime
    states = {value.field_port_id: value for value in sensor_states}
    samples: dict[str, list[EvidenceSample]] = {
        value.field_port_id: [] for value in profile.ports
    }
    chemical_receipts: dict[str, list[str]] = {
        value.field_port_id: [] for value in profile.ports
    }
    rounding_receipts: dict[str, list[str]] = {
        value.field_port_id: [] for value in profile.ports
    }
    base_observations = {
        value.port_id: value for value in boundary.event.observations
    }

    for interval_index, timestamp in enumerate(profile.grid.timestamps):
        observations = tuple(
            _derived_story_observation(
                execution_id=execution_id,
                interval_index=interval_index,
                source_time_start=runtime.state(port.story_port_id).source_time,
                source_time_end=timestamp,
                raw_code=raw_codes[port.scene_coordinate_id],
                base_observation=base_observations[port.story_port_id],
                port=port,
            )
            for port in profile.ports
        )
        event = StoryPhysicalBoundaryEvent(
            event_id=observations[0].event_id,
            observations=observations,
        )
        evolved = evolve_story_chemistry_event(runtime=runtime, event=event)
        if evolved.status is not StoryChemistryStatus.EVOLVED:
            raise ReceiptError(f"story chemistry replay unresolved: {evolved.reason}")
        output_by_story_port = {value.port_id: value for value in evolved.outputs}
        if tuple(output_by_story_port) != tuple(
            value.story_port_id for value in profile.ports
        ):
            raise ReceiptError("story chemistry replay did not preserve every native port")

        for port in profile.ports:
            output = output_by_story_port[port.story_port_id]
            rounding = output.kernel_binary64_relevance
            if (
                rounding.status is not Binary64RoundingStatus.CERTIFIED
                or rounding.exact_binary64 is None
                or rounding.receipt_sha256 is None
            ):
                raise ReceiptError("story chemistry lacks uniquely certified relevance")
            state = states[port.field_port_id]
            delta = timestamp - state.last_timestamp
            if delta <= 0:
                raise ReceiptError("story replay causal interval is not positive")
            flux = port.flux_for_code(raw_codes[port.scene_coordinate_id])
            drive = port.signal_offset + port.signal_per_native_flux * flux
            signal = (
                state.retained_signal
                + port.response_growth * (drive - state.retained_signal)
                - port.natural_decay * state.retained_signal
            )
            if not -1 <= signal <= 1:
                raise ReceiptError("mounted story response leaves calibrated signal domain")
            phase = state.phase_turns + port.phase_kappa * signal * delta
            sample = EvidenceSample(
                source_index=state.last_source_index + 1,
                timestamp=timestamp,
                signal=signal,
                relevance=rounding.exact_binary64,
                phase_turns=phase,
            )
            samples[port.field_port_id].append(sample)
            next_state_payload = story_sensor_state_receipt_payload(
                field_port_id=state.field_port_id,
                source_epoch=state.source_epoch,
                last_source_index=sample.source_index,
                last_timestamp=timestamp,
                retained_signal=signal,
                phase_turns=phase,
                port_authority_receipt_sha256=state.port_authority_receipt_sha256,
            )
            states[port.field_port_id] = MountedStorySensorState(
                field_port_id=state.field_port_id,
                source_epoch=state.source_epoch,
                last_source_index=sample.source_index,
                last_timestamp=timestamp,
                retained_signal=signal,
                phase_turns=phase,
                port_authority_receipt_sha256=state.port_authority_receipt_sha256,
                authority_receipt_sha256=receipt_sha256(next_state_payload),
            )
            chemical_receipts[port.field_port_id].append(
                output.chemical_evolution_receipt.receipt_sha256
            )
            rounding_receipts[port.field_port_id].append(rounding.receipt_sha256)
        runtime = evolved.runtime

    registry = _extend_records(receipt_registry, runtime.receipt_registry.records)
    registry = _extend_payloads(
        registry,
        (
            story_sensor_state_receipt_payload(
                field_port_id=value.field_port_id,
                source_epoch=value.source_epoch,
                last_source_index=value.last_source_index,
                last_timestamp=value.last_timestamp,
                retained_signal=value.retained_signal,
                phase_turns=value.phase_turns,
                port_authority_receipt_sha256=value.port_authority_receipt_sha256,
            )
            for value in states.values()
        ),
    )

    streams: list[EvidenceStream] = []
    stream_payloads: list[bytes] = []
    relevance_payloads: list[bytes] = []
    for port in profile.ports:
        relevance_payload = _relevance_receipt_payload(
            execution_id=execution_id,
            port=port,
            chemical_receipt_sha256s=chemical_receipts[port.field_port_id],
            rounding_receipt_sha256s=rounding_receipts[port.field_port_id],
        )
        stream = EvidenceStream(
            lane_id=port.lane.value,
            port_id=port.field_port_id,
            evidence_id=f"{execution_id}:{port.field_port_id}",
            source_epoch=port.source_epoch,
            port_kind=port.port_kind,
            physical_unit=port.signal_physical_unit,
            profile_binding_sha256=profile.authority_receipt_sha256,
            calibration_receipt_sha256=port.authority_receipt_sha256,
            relevance_receipt_sha256=receipt_sha256(relevance_payload),
            samples=tuple(samples[port.field_port_id]),
        )
        streams.append(stream)
        relevance_payloads.append(relevance_payload)
        stream_payloads.append(source_evidence_stream_receipt_payload(stream))
    registry = _extend_payloads(registry, (*relevance_payloads, *stream_payloads))

    kernel_inputs: list[KernelNativeInputStream] = []
    kernel_payloads: list[bytes] = []
    for stream, stream_payload in zip(streams, stream_payloads, strict=True):
        adapted_samples = tuple(
            KernelNativeInputSample(
                source_index=value.source_index,
                timestamp=value.timestamp,
                dimensionless_field=Fraction(1) + value.signal / 2,
                l0_relevance=value.relevance,
            )
            for value in stream.samples
        )
        payload = kernel_native_input_receipt_payload(
            adapter_id=profile.kernel_adapter_id,
            adapter_profile_receipt_sha256=(
                profile.kernel_adapter_profile_receipt_sha256
            ),
            lane_id=stream.lane_id,
            port_id=stream.port_id,
            source_stream_receipt_sha256=receipt_sha256(stream_payload),
            samples=adapted_samples,
        )
        kernel_inputs.append(
            KernelNativeInputStream(
                adapter_id=profile.kernel_adapter_id,
                adapter_profile_receipt_sha256=(
                    profile.kernel_adapter_profile_receipt_sha256
                ),
                lane_id=stream.lane_id,
                port_id=stream.port_id,
                source_stream_receipt_sha256=receipt_sha256(stream_payload),
                samples=adapted_samples,
                authority_receipt_sha256=receipt_sha256(payload),
            )
        )
        kernel_payloads.append(payload)
    registry = _extend_payloads(registry, kernel_payloads)
    return (
        tuple(streams),
        tuple(kernel_inputs),
        runtime,
        tuple(states[value.field_port_id] for value in profile.ports),
        registry,
    )


def _sign_class(value: str) -> str:
    parsed = Fraction(value)
    if parsed < 0:
        return "negative"
    if parsed > 0:
        return "positive"
    return "exact_zero"


def _actual_branch_and_cell(raw_payload: bytes) -> tuple[str, str]:
    try:
        raw = json.loads(raw_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError("frozen L0-L4 trace is not canonical JSON") from exc
    branch_payload = _canonical_bytes(
        {
            "L1": [
                {
                    "C_k": value["C_k"],
                    "N_gate": value["N_gate"],
                    "end_idx": value["end_idx"],
                    "projections": value["projections"],
                    "start_idx": value["start_idx"],
                }
                for value in raw["L1_GateL1State"]
            ],
            "L2": [
                {
                    "IAS_k": value["IAS_k"],
                    "end_idx": value["end_idx"],
                    "regime": value["regime"],
                    "start_idx": value["start_idx"],
                }
                for value in raw["L2_GateInterpretation"]
            ],
            "L3": [
                {
                    "Hyst_k": value["Hyst_k"],
                    "end_idx": value["end_idx"],
                    "g_k": value["g_k"],
                    "start_idx": value["start_idx"],
                }
                for value in raw["L3_ResonanceResult"]
            ],
            "schema": "glew.story_native_replay.actual_branch.v1",
        }
    )
    cell_payload = _canonical_bytes(
        {
            "L4_sign_zero_cells": [
                {
                    field.value: _sign_class(value[field.value])
                    for field in FIELD_ORDER
                }
                for value in raw["L4_DSF"]
            ],
            "schema": "glew.story_native_replay.actual_cell.v1",
        }
    )
    return (f"branch-{branch_payload.hex()}", f"cell-{cell_payload.hex()}")


def _source_operator_receipt_payload(
    *,
    case: NativeReplayCase,
    boundary: MountedAuthenticatedClosedStoryBoundary,
    preparation: ClosedExperienceEvidencePreparation,
    source_stream_receipt_sha256: str,
    l0_l4_trace_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "authenticated_boundary_receipt_sha256": boundary.authority_receipt_sha256,
            "case_receipt_sha256": case.receipt_sha256,
            "l0_l4_preparation_receipt_sha256": preparation.receipt_sha256,
            "l0_l4_trace_receipt_sha256": l0_l4_trace_receipt_sha256,
            "operator": STORY_NATIVE_REPLAY_OPERATOR_ID,
            "schema": "glew.story_native_replay.source_operator.v1",
            "source_stream_receipt_sha256": source_stream_receipt_sha256,
        }
    )


def _execute_case(
    *,
    case: NativeReplayCase,
    target_port: StorySensorPortAuthority,
    profile: MountedStoryNativeReplayProfile,
    boundary: MountedAuthenticatedClosedStoryBoundary,
    story_runtime: StoryChemistryRuntime,
    sensor_states: tuple[MountedStorySensorState, ...],
    receipt_registry: ReceiptRegistry,
) -> tuple[StoryKernelReplayExecution, ReceiptRegistry]:
    raw_codes = {value.scene_coordinate_id: value.base_raw_code for value in profile.ports}
    case_codes = {value.coordinate_id: value.raw_code for value in case.sensor_codes}
    if set(case_codes) != {target_port.scene_coordinate_id}:
        raise ReceiptError("native replay case changed an unmounted scene coordinate")
    raw_codes[target_port.scene_coordinate_id] = case_codes[target_port.scene_coordinate_id]
    streams, inputs, final_runtime, final_states, registry = _execute_streams(
        execution_id=case.case_id,
        profile=profile,
        boundary=boundary,
        story_runtime=story_runtime,
        sensor_states=sensor_states,
        raw_codes=raw_codes,
        receipt_registry=receipt_registry,
    )
    prepared = prepare_closed_experience_evidence(
        streams=streams,
        kernel_inputs=inputs,
        source_time_start=story_runtime.states[0].source_time,
        grid=profile.grid,
        support_domain=profile.support_domain,
        resonance_graph=profile.resonance_graph,
        resonance_operator=profile.resonance_operator,
        topology=profile.topology,
        receipt_registry=registry,
    )
    if isinstance(prepared, ClosedExperienceProviderUnknown):
        raise ReceiptError(
            f"frozen L0-L4 preparation unresolved: {prepared.missing_authority}"
        )
    if prepared.status is not ProviderStatus.READY:
        raise ReceiptError("frozen L0-L4 preparation did not become READY")
    registry = prepared.receipt_registry
    target_evidence = tuple(
        value for value in prepared.evidence if value.key == target_port.field_key
    )
    if not target_evidence:
        raise ReceiptError("frozen L0-L4 emitted no target-port evidence")
    final = max(
        target_evidence,
        key=lambda value: (
            value.provenance.source_timestamp,
            value.provenance.source_index,
        ),
    )
    l4 = ExactL4Response(
        D_k=final.coordinates.D_k,
        M_k=final.coordinates.M_k,
        R_rev_k=final.coordinates.R_rev_k,
        U_star_k=final.coordinates.U_star_k,
        C_k=final.coordinates.C_k,
        P_k=final.coordinates.P_k,
        B_k=final.coordinates.B_k,
    )
    branch_id, cell_id = _actual_branch_and_cell(final.raw_record.payload)
    source_stream = next(value for value in streams if value.key == target_port.field_key)
    source_stream_payload = source_evidence_stream_receipt_payload(source_stream)
    source_operator_payload = _source_operator_receipt_payload(
        case=case,
        boundary=boundary,
        preparation=prepared,
        source_stream_receipt_sha256=receipt_sha256(source_stream_payload),
        l0_l4_trace_receipt_sha256=final.raw_record.digest,
    )
    registry = _extend_payloads(registry, (source_operator_payload,))
    return (
        StoryKernelReplayExecution(
            case=case,
            streams=streams,
            kernel_inputs=inputs,
            preparation=prepared,
            final_story_runtime=final_runtime,
            final_sensor_states=final_states,
            target_l4_response=l4,
            target_source_stream_receipt_sha256=receipt_sha256(source_stream_payload),
            target_l0_l4_trace_receipt_sha256=final.raw_record.digest,
            target_branch_id=branch_id,
            target_cell_id=cell_id,
            source_operator_receipt_sha256=receipt_sha256(source_operator_payload),
        ),
        registry,
    )


def execute_story_native_replay(
    *,
    target_lane: L6Lane,
    target_field_port_id: str,
    profile: MountedStoryNativeReplayProfile,
    boundary: MountedAuthenticatedClosedStoryBoundary,
    pre_window_state: MountedPreWindowState,
    story_runtime: StoryChemistryRuntime,
    sensor_states: tuple[MountedStorySensorState, ...],
    receipt_registry: ReceiptRegistry,
) -> StoryNativeReplayResult:
    """Execute base and every admissible adjacent sensor code from one state."""

    base_registry = receipt_registry
    try:
        if not isinstance(target_lane, L6Lane) or target_lane is L6Lane.LANGUAGE:
            raise ReceiptError("story native replay target must be a sensor lane")
        require_identifier(target_field_port_id, "target field port id")
        profile.verify(base_registry)
        boundary.verify(profile=profile, receipt_registry=base_registry)
        base_registry = _extend_records(
            base_registry, story_runtime.receipt_registry.records
        )
        _verify_pre_window(
            profile=profile,
            pre_window_state=pre_window_state,
            story_runtime=story_runtime,
            sensor_states=sensor_states,
            receipt_registry=base_registry,
        )
        _verify_boundary_times(
            boundary=boundary,
            profile=profile,
            story_runtime=story_runtime,
        )
        target = profile.port_for_field(target_lane, target_field_port_id)
        perturbation_payload = native_perturbation_profile_receipt_payload(
            profile_id=f"{profile.profile_id}:{target.field_port_id}:native",
            lane=target.lane,
            provider_id=profile.provider_id,
            native_port_id=target.field_port_id,
            sensor_coordinates=(
                SensorNativeCoordinate(
                    coordinate_id=target.scene_coordinate_id,
                    base_code=target.base_raw_code,
                    minimum_code=target.minimum_raw_code,
                    maximum_code=target.maximum_raw_code,
                    physical_quantum=target.physical_quantum,
                    source_authority_receipt_sha256=target.authority_receipt_sha256,
                ),
            ),
            language_trit_coordinates=(),
        )
        perturbation_profile = MountedNativePerturbationProfile(
            profile_id=f"{profile.profile_id}:{target.field_port_id}:native",
            lane=target.lane,
            provider_id=profile.provider_id,
            native_port_id=target.field_port_id,
            sensor_coordinates=(
                SensorNativeCoordinate(
                    coordinate_id=target.scene_coordinate_id,
                    base_code=target.base_raw_code,
                    minimum_code=target.minimum_raw_code,
                    maximum_code=target.maximum_raw_code,
                    physical_quantum=target.physical_quantum,
                    source_authority_receipt_sha256=target.authority_receipt_sha256,
                ),
            ),
            language_trit_coordinates=(),
            authority_receipt_sha256=receipt_sha256(perturbation_payload),
        )
        base_registry = _extend_payloads(base_registry, (perturbation_payload,))
        perturbation_profile.verify(base_registry)
        cases = enumerate_native_replay_cases(perturbation_profile, pre_window_state)
        base_registry = _extend_payloads(
            base_registry, (value.receipt_payload for value in cases)
        )

        executions: list[StoryKernelReplayExecution] = []
        registry = base_registry
        for case in cases:
            execution, generated_registry = _execute_case(
                case=case,
                target_port=target,
                profile=profile,
                boundary=boundary,
                story_runtime=story_runtime,
                sensor_states=sensor_states,
                receipt_registry=base_registry,
            )
            registry = _extend_records(registry, generated_registry.records)
            executions.append(execution)

        responses: list[NativeL4ReplayResponse] = []
        response_payloads: list[bytes] = []
        for execution in executions:
            response_payload = native_l4_replay_response_receipt_payload(
                response_id=f"{execution.case.case_id}:frozen-l0-l4",
                lane=target.lane,
                provider_id=profile.provider_id,
                native_port_id=target.field_port_id,
                case_receipt_sha256=execution.case.receipt_sha256,
                profile_receipt_sha256=perturbation_profile.authority_receipt_sha256,
                pre_window_state_receipt_sha256=(
                    pre_window_state.authority_receipt_sha256
                ),
                branch_id=execution.target_branch_id,
                cell_id=execution.target_cell_id,
                l4_response=execution.target_l4_response,
                source_operator_receipt_sha256=(
                    execution.source_operator_receipt_sha256
                ),
            )
            responses.append(
                NativeL4ReplayResponse(
                    response_id=f"{execution.case.case_id}:frozen-l0-l4",
                    lane=target.lane,
                    provider_id=profile.provider_id,
                    native_port_id=target.field_port_id,
                    case_receipt_sha256=execution.case.receipt_sha256,
                    profile_receipt_sha256=(
                        perturbation_profile.authority_receipt_sha256
                    ),
                    pre_window_state_receipt_sha256=(
                        pre_window_state.authority_receipt_sha256
                    ),
                    branch_id=execution.target_branch_id,
                    cell_id=execution.target_cell_id,
                    l4_response=execution.target_l4_response,
                    source_operator_receipt_sha256=(
                        execution.source_operator_receipt_sha256
                    ),
                    receipt_sha256=receipt_sha256(response_payload),
                )
            )
            response_payloads.append(response_payload)
        registry = _extend_payloads(registry, response_payloads)

        completeness_payload = _canonical_bytes(
            {
                "case_receipt_sha256s": [value.receipt_sha256 for value in cases],
                "execution_preparation_receipt_sha256s": [
                    value.preparation.receipt_sha256 for value in executions
                ],
                "operator": STORY_NATIVE_REPLAY_OPERATOR_ID,
                "profile_receipt_sha256": (
                    perturbation_profile.authority_receipt_sha256
                ),
                "schema": "glew.story_native_replay.response_completeness.v1",
            }
        )
        registry = _extend_payloads(registry, (completeness_payload,))
        response_set_payload = native_response_set_receipt_payload(
            response_set_id=f"{perturbation_profile.profile_id}:responses",
            lane=target.lane,
            provider_id=profile.provider_id,
            native_port_id=target.field_port_id,
            profile_receipt_sha256=perturbation_profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
            responses=tuple(responses),
            source_completeness_receipt_sha256=receipt_sha256(
                completeness_payload
            ),
        )
        response_set = MountedNativeResponseSet(
            response_set_id=f"{perturbation_profile.profile_id}:responses",
            lane=target.lane,
            provider_id=profile.provider_id,
            native_port_id=target.field_port_id,
            profile_receipt_sha256=perturbation_profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
            responses=tuple(responses),
            source_completeness_receipt_sha256=receipt_sha256(
                completeness_payload
            ),
            authority_receipt_sha256=receipt_sha256(response_set_payload),
        )
        registry = _extend_payloads(registry, (response_set_payload,))
        response_set.verify(
            profile=perturbation_profile,
            pre_window_state=pre_window_state,
            expected_cases=cases,
            receipt_registry=registry,
        )

        proof: MountedSameBranchCellProof | None = None
        identities = {
            (value.target_branch_id, value.target_cell_id) for value in executions
        }
        if len(identities) == 1:
            branch_id, cell_id = next(iter(identities))
            proof_source_payload = _canonical_bytes(
                {
                    "branch_id": branch_id,
                    "cell_id": cell_id,
                    "response_receipt_sha256s": [
                        value.receipt_sha256 for value in responses
                    ],
                    "schema": "glew.story_native_replay.actual_same_branch_cell_source.v1",
                }
            )
            registry = _extend_payloads(registry, (proof_source_payload,))
            proof_payload = same_branch_cell_proof_receipt_payload(
                proof_id=f"{perturbation_profile.profile_id}:same-branch-cell",
                lane=target.lane,
                provider_id=profile.provider_id,
                native_port_id=target.field_port_id,
                profile_receipt_sha256=perturbation_profile.authority_receipt_sha256,
                pre_window_state_receipt_sha256=(
                    pre_window_state.authority_receipt_sha256
                ),
                branch_id=branch_id,
                cell_id=cell_id,
                response_receipt_sha256s=tuple(
                    value.receipt_sha256 for value in responses
                ),
                source_operator_receipt_sha256=receipt_sha256(
                    proof_source_payload
                ),
            )
            proof = MountedSameBranchCellProof(
                proof_id=f"{perturbation_profile.profile_id}:same-branch-cell",
                lane=target.lane,
                provider_id=profile.provider_id,
                native_port_id=target.field_port_id,
                profile_receipt_sha256=perturbation_profile.authority_receipt_sha256,
                pre_window_state_receipt_sha256=(
                    pre_window_state.authority_receipt_sha256
                ),
                branch_id=branch_id,
                cell_id=cell_id,
                response_receipt_sha256s=tuple(
                    value.receipt_sha256 for value in responses
                ),
                source_operator_receipt_sha256=receipt_sha256(
                    proof_source_payload
                ),
                authority_receipt_sha256=receipt_sha256(proof_payload),
            )
            registry = _extend_payloads(registry, (proof_payload,))
            proof.verify(
                profile=perturbation_profile,
                pre_window_state=pre_window_state,
                responses=tuple(responses),
                receipt_registry=registry,
            )
        bundle = NativePortReplayBundle(
            profile=perturbation_profile,
            response_set=response_set,
            branch_cell_proof=proof,
        )
        return StoryNativeReplayResult(
            status=StoryNativeReplayStatus.READY,
            reason="base and every admissible adjacent native code ran through frozen L0-L4",
            bundle=bundle,
            replay_cases=cases,
            executions=tuple(executions),
            receipt_registry=registry,
        )
    except ReceiptError as exc:
        return StoryNativeReplayResult(
            status=StoryNativeReplayStatus.UNKNOWN,
            reason=str(exc),
            bundle=None,
            replay_cases=(),
            executions=(),
            receipt_registry=base_registry,
        )


__all__ = [
    "MountedAuthenticatedClosedStoryBoundary",
    "MountedStoryNativeReplayProfile",
    "MountedStorySensorState",
    "STORY_NATIVE_REPLAY_OPERATOR_ID",
    "StoryKernelReplayExecution",
    "StoryNativeReplayResult",
    "StoryNativeReplayStatus",
    "StorySensorPortAuthority",
    "authenticated_closed_story_boundary_receipt_payload",
    "execute_story_native_replay",
    "story_native_replay_profile_receipt_payload",
    "story_replay_chemistry_state_receipt_payload",
    "story_sensor_port_authority_receipt_payload",
    "story_sensor_state_receipt_payload",
]
