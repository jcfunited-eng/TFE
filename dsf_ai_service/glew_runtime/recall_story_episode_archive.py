"""Immutable content-addressed archive of admitted five-sense story episodes.

This module is storage, not cognition.  It accepts only a receipt-verified BASE
story execution and preserves the exact sensory authority that already exists.
It does not index text, construct a response, infer a profile, or create field
authority.  Resolution is an exact equality test over the complete sensory
receipt set and the mounted story profile.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Sequence

from .field import PortTransportEvidence
from .global_uf import MountedPreWindowState
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)
from .physical_l6_tangents import NativeReplayCaseKind
from .story_chemistry import StoryChemistryRuntime
from .story_native_replay import (
    MountedAuthenticatedClosedStoryBoundary,
    MountedStoryNativeReplayProfile,
    MountedStorySensorState,
    StoryKernelReplayExecution,
    story_replay_chemistry_state_receipt_payload,
)


ARCHIVE_CHECKPOINT_ALGORITHM = "HMAC-SHA256"
ARCHIVE_CHECKPOINT_SCHEMA = "glew.recall.story_episode_archive_checkpoint.v1"
ARCHIVE_EPISODE_SCHEMA = "glew.recall.story_episode.v1"
ARCHIVE_ROOT_SCHEMA = "glew.recall.story_episode_archive.v1"
SENSORY_LANES = frozenset(("sight", "sound", "smell", "taste", "touch"))
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _strict_object_pairs(
    pairs: Sequence[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ReceiptError("archive checkpoint contains a duplicate JSON field")
        result[key] = value
    return result


def _strict_json_object(payload: bytes, field_name: str) -> dict[str, object]:
    if not isinstance(payload, bytes) or not payload:
        raise ReceiptError(f"{field_name} bytes are absent")
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_strict_object_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ReceiptError(f"{field_name} contains a non-finite number")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{field_name} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise ReceiptError(f"{field_name} must be a JSON object")
    if _canonical_bytes(value) != payload:
        raise ReceiptError(f"{field_name} is not canonical JSON bytes")
    return value


def _expect_exact_keys(
    value: Mapping[str, object], expected: frozenset[str], field_name: str
) -> None:
    if frozenset(value) != expected:
        raise ReceiptError(f"{field_name} fields changed")


def _expect_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise ReceiptError(f"{field_name} must be a list")
    return value


def _hex_bytes(value: object, field_name: str) -> bytes:
    if not isinstance(value, str) or not value or value.lower() != value:
        raise ReceiptError(f"{field_name} must be nonempty lowercase hexadecimal")
    try:
        payload = bytes.fromhex(value)
    except ValueError as exc:
        raise ReceiptError(f"{field_name} is not hexadecimal") from exc
    if not payload or payload.hex() != value:
        raise ReceiptError(f"{field_name} is not canonical hexadecimal")
    return payload


def _digest_tuple(values: object, field_name: str) -> tuple[str, ...]:
    result: list[str] = []
    for index, value in enumerate(_expect_list(values, field_name)):
        if not isinstance(value, str):
            raise ReceiptError(f"{field_name}[{index}] is not a digest")
        result.append(sha256_digest(value, f"{field_name}[{index}]"))
    return tuple(result)


def _mounted_exact(
    registry: ReceiptRegistry,
    digest: str,
    field_name: str,
) -> bytes:
    payload = registry.resolve(digest, field_name)
    if receipt_sha256(payload) != digest:
        raise ReceiptError(f"{field_name} differs from its digest")
    return payload


@dataclass(frozen=True, slots=True)
class ArchivedSensoryEvidenceBinding:
    """Identity of one exact raw L0-L4 sensory record in an episode."""

    lane_id: str
    port_id: str
    evidence_id: str
    evidence_receipt_sha256: str
    raw_record_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, "archived sensory lane_id")
        require_identifier(self.port_id, "archived sensory port_id")
        require_identifier(self.evidence_id, "archived sensory evidence_id")
        sha256_digest(
            self.evidence_receipt_sha256,
            "archived sensory evidence receipt",
        )
        sha256_digest(self.raw_record_sha256, "archived raw sensory record")
        if self.lane_id not in SENSORY_LANES:
            raise ReceiptError("archive evidence is not one of the five sensory lanes")

    @classmethod
    def from_evidence(
        cls, value: PortTransportEvidence
    ) -> "ArchivedSensoryEvidenceBinding":
        if not isinstance(value, PortTransportEvidence):
            raise ReceiptError("archive admission contains untyped sensory evidence")
        return cls(
            lane_id=value.lane_id,
            port_id=value.port_id,
            evidence_id=value.evidence_id,
            evidence_receipt_sha256=value.evidence_receipt_sha256,
            raw_record_sha256=value.raw_record.digest,
        )

    def verify(self, registry: ReceiptRegistry) -> None:
        payload = _mounted_exact(
            registry,
            self.evidence_receipt_sha256,
            "archived sensory evidence receipt",
        )
        value = _strict_json_object(payload, "archived sensory evidence receipt")
        if (
            value.get("schema") != "glew.field.transport_evidence.v1"
            or value.get("lane_id") != self.lane_id
            or value.get("port_id") != self.port_id
            or value.get("evidence_id") != self.evidence_id
            or value.get("raw_record_sha256") != self.raw_record_sha256
        ):
            raise ReceiptError("archived sensory binding differs from exact evidence")
        _mounted_exact(registry, self.raw_record_sha256, "archived raw sensory record")
        for object_name, field_name in (
            ("Reg_k", "archived Reg_k authority receipt"),
            ("R_UF", "archived R_UF authority receipt"),
            ("S_UF", "archived S_UF authority receipt"),
            ("validity", "archived validity authority receipt"),
            ("provenance", "archived provenance authority receipt"),
        ):
            fact = value.get(object_name)
            if not isinstance(fact, dict):
                raise ReceiptError(f"archived sensory {object_name} binding is malformed")
            digest = fact.get("authority_receipt_sha256")
            if not isinstance(digest, str):
                raise ReceiptError(f"archived sensory {object_name} authority is absent")
            _mounted_exact(registry, digest, field_name)


def recall_story_episode_receipt_payload(
    *,
    profile_binding_sha256: str,
    profile_receipt_sha256s: tuple[str, ...],
    boundary_receipt_sha256: str,
    boundary_observation_receipt_sha256s: tuple[str, ...],
    pre_window_state_receipt_sha256: str,
    pre_window_receiver_state_receipt_sha256s: tuple[str, ...],
    post_window_receiver_state_receipt_sha256s: tuple[str, ...],
    pre_window_sensor_state_receipt_sha256s: tuple[str, ...],
    post_window_sensor_state_receipt_sha256s: tuple[str, ...],
    evidence_preparation_receipt_sha256: str,
    sensory_evidence_bindings: tuple[ArchivedSensoryEvidenceBinding, ...],
    mounted_receipt_sha256s: tuple[str, ...],
) -> bytes:
    return _canonical_bytes(
        {
            "boundary_observation_receipt_sha256s": list(
                boundary_observation_receipt_sha256s
            ),
            "boundary_receipt_sha256": boundary_receipt_sha256,
            "evidence_preparation_receipt_sha256": (
                evidence_preparation_receipt_sha256
            ),
            "mounted_receipt_sha256s": list(mounted_receipt_sha256s),
            "post_window_receiver_state_receipt_sha256s": list(
                post_window_receiver_state_receipt_sha256s
            ),
            "post_window_sensor_state_receipt_sha256s": list(
                post_window_sensor_state_receipt_sha256s
            ),
            "pre_window_receiver_state_receipt_sha256s": list(
                pre_window_receiver_state_receipt_sha256s
            ),
            "pre_window_sensor_state_receipt_sha256s": list(
                pre_window_sensor_state_receipt_sha256s
            ),
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "profile_binding_sha256": profile_binding_sha256,
            "profile_receipt_sha256s": list(profile_receipt_sha256s),
            "schema": ARCHIVE_EPISODE_SCHEMA,
            "sensory_evidence_bindings": [
                {
                    "evidence_id": value.evidence_id,
                    "evidence_receipt_sha256": value.evidence_receipt_sha256,
                    "lane_id": value.lane_id,
                    "port_id": value.port_id,
                    "raw_record_sha256": value.raw_record_sha256,
                }
                for value in sensory_evidence_bindings
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class RecallStoryEpisode:
    """Bit-exact receipt closure of one admitted five-sense episode."""

    profile_binding_sha256: str
    profile_receipt_sha256s: tuple[str, ...]
    boundary_receipt_sha256: str
    boundary_observation_receipt_sha256s: tuple[str, ...]
    pre_window_state_receipt_sha256: str
    pre_window_receiver_state_receipt_sha256s: tuple[str, ...]
    post_window_receiver_state_receipt_sha256s: tuple[str, ...]
    pre_window_sensor_state_receipt_sha256s: tuple[str, ...]
    post_window_sensor_state_receipt_sha256s: tuple[str, ...]
    evidence_preparation_receipt_sha256: str
    sensory_evidence_bindings: tuple[ArchivedSensoryEvidenceBinding, ...]
    receipt_records: tuple[ReceiptRecord, ...]
    episode_receipt_sha256: str
    episode_receipt_payload: bytes

    @property
    def sensory_evidence_receipt_sha256s(self) -> tuple[str, ...]:
        return tuple(
            value.evidence_receipt_sha256
            for value in self.sensory_evidence_bindings
        )

    @property
    def sensory_receipt_set_key(self) -> tuple[str, ...]:
        return tuple(sorted(self.sensory_evidence_receipt_sha256s))

    def verify(self) -> None:
        sha256_digest(self.profile_binding_sha256, "archive profile binding")
        sha256_digest(self.episode_receipt_sha256, "archive episode receipt")
        if not isinstance(self.receipt_records, tuple) or not self.receipt_records:
            raise ReceiptError("archive episode has no exact receipt records")
        record_digests = tuple(value.digest for value in self.receipt_records)
        if record_digests != tuple(sorted(record_digests)):
            raise ReceiptError("archive receipt records are not canonical")
        registry = ReceiptRegistry(self.profile_binding_sha256, self.receipt_records)

        if (
            not self.profile_receipt_sha256s
            or self.profile_receipt_sha256s
            != tuple(sorted(set(self.profile_receipt_sha256s)))
        ):
            raise ReceiptError("archive profile receipts are not canonical and complete")
        if self.profile_binding_sha256 not in self.profile_receipt_sha256s:
            raise ReceiptError("archive profile binding is absent from profile receipts")
        for digest in self.profile_receipt_sha256s:
            _mounted_exact(registry, digest, "archive profile receipt")

        for digest, field_name in (
            (self.boundary_receipt_sha256, "archive boundary receipt"),
            (self.pre_window_state_receipt_sha256, "archive pre-window state receipt"),
            (
                self.evidence_preparation_receipt_sha256,
                "archive evidence-preparation receipt",
            ),
        ):
            _mounted_exact(registry, digest, field_name)
        for values, field_name in (
            (
                self.boundary_observation_receipt_sha256s,
                "archive boundary observation receipt",
            ),
            (
                self.pre_window_receiver_state_receipt_sha256s,
                "archive pre-window receiver-state receipt",
            ),
            (
                self.post_window_receiver_state_receipt_sha256s,
                "archive post-window receiver-state receipt",
            ),
            (
                self.pre_window_sensor_state_receipt_sha256s,
                "archive pre-window sensor-state receipt",
            ),
            (
                self.post_window_sensor_state_receipt_sha256s,
                "archive post-window sensor-state receipt",
            ),
        ):
            if len(values) != 5 or len(set(values)) != 5:
                raise ReceiptError(f"{field_name} does not exactly cover five senses")
            for digest in values:
                _mounted_exact(registry, digest, field_name)

        if not self.sensory_evidence_bindings:
            raise ReceiptError("archive episode has no sensory evidence")
        if len(set(self.sensory_evidence_receipt_sha256s)) != len(
            self.sensory_evidence_receipt_sha256s
        ):
            raise ReceiptError("archive episode repeats sensory evidence")
        if {
            (value.lane_id, value.port_id)
            for value in self.sensory_evidence_bindings
        } != {
            (value.lane_id, value.port_id)
            for value in self.sensory_evidence_bindings
            if value.lane_id in SENSORY_LANES
        } or {
            value.lane_id for value in self.sensory_evidence_bindings
        } != SENSORY_LANES:
            raise ReceiptError("archive episode does not cover the exact five senses")
        for value in self.sensory_evidence_bindings:
            value.verify(registry)

        boundary_payload = _strict_json_object(
            registry.resolve(self.boundary_receipt_sha256, "archive boundary receipt"),
            "archive boundary receipt",
        )
        observations = _expect_list(
            boundary_payload.get("observations"),
            "archive boundary observations",
        )
        mounted_observations = tuple(
            value.get("observation_receipt_sha256")
            for value in observations
            if isinstance(value, dict)
        )
        if (
            len(mounted_observations) != len(observations)
            or boundary_payload.get("profile_receipt_sha256")
            != self.profile_binding_sha256
            or mounted_observations
            != self.boundary_observation_receipt_sha256s
        ):
            raise ReceiptError("archive boundary binding changed")

        expected = recall_story_episode_receipt_payload(
            profile_binding_sha256=self.profile_binding_sha256,
            profile_receipt_sha256s=self.profile_receipt_sha256s,
            boundary_receipt_sha256=self.boundary_receipt_sha256,
            boundary_observation_receipt_sha256s=(
                self.boundary_observation_receipt_sha256s
            ),
            pre_window_state_receipt_sha256=(
                self.pre_window_state_receipt_sha256
            ),
            pre_window_receiver_state_receipt_sha256s=(
                self.pre_window_receiver_state_receipt_sha256s
            ),
            post_window_receiver_state_receipt_sha256s=(
                self.post_window_receiver_state_receipt_sha256s
            ),
            pre_window_sensor_state_receipt_sha256s=(
                self.pre_window_sensor_state_receipt_sha256s
            ),
            post_window_sensor_state_receipt_sha256s=(
                self.post_window_sensor_state_receipt_sha256s
            ),
            evidence_preparation_receipt_sha256=(
                self.evidence_preparation_receipt_sha256
            ),
            sensory_evidence_bindings=self.sensory_evidence_bindings,
            mounted_receipt_sha256s=record_digests,
        )
        if (
            self.episode_receipt_payload != expected
            or receipt_sha256(expected) != self.episode_receipt_sha256
        ):
            raise ReceiptError("archive episode differs from its content address")


def _profile_receipts(
    profile: MountedStoryNativeReplayProfile,
    story_runtime: StoryChemistryRuntime,
) -> tuple[str, ...]:
    values = {
        profile.authority_receipt_sha256,
        profile.topology.authority_receipt_sha256,
        profile.grid.grid_receipt_sha256,
        profile.support_domain.authority_receipt_sha256,
        profile.resonance_graph.authority_receipt_sha256,
        profile.resonance_operator.authority_receipt_sha256,
        profile.kernel_adapter_profile_receipt_sha256,
        story_runtime.manifest.receipt_sha256,
        *(receipt_sha256(value) for value in story_runtime.manifest.static_receipt_payloads),
        *(value.authority_receipt_sha256 for value in profile.ports),
        *(
            value.boundary_source_authority_receipt_sha256
            for value in profile.ports
        ),
    }
    return tuple(sorted(values))


def _verify_story_runtime(
    *,
    runtime: StoryChemistryRuntime,
    registry: ReceiptRegistry,
    expected_port_ids: tuple[str, ...],
    field_name: str,
) -> None:
    if not isinstance(runtime, StoryChemistryRuntime):
        raise ReceiptError(f"{field_name} is not a story chemistry runtime")
    if tuple(value.port_id for value in runtime.states) != expected_port_ids:
        raise ReceiptError(f"{field_name} does not exactly cover the five story ports")
    if registry.resolve(
        runtime.manifest.receipt_sha256,
        f"{field_name} manifest receipt",
    ) != runtime.manifest.canonical_payload:
        raise ReceiptError(f"{field_name} manifest receipt changed")
    for value in runtime.states:
        value.verify(registry)


def _verify_sensor_states(
    *,
    states: tuple[MountedStorySensorState, ...],
    profile: MountedStoryNativeReplayProfile,
    registry: ReceiptRegistry,
    field_name: str,
) -> None:
    if not isinstance(states, tuple) or tuple(
        value.field_port_id for value in states
    ) != tuple(value.field_port_id for value in profile.ports):
        raise ReceiptError(f"{field_name} does not exactly cover five native ports")
    for port, state in zip(profile.ports, states, strict=True):
        state.verify(port=port, receipt_registry=registry)


def create_recall_story_episode(
    *,
    profile: MountedStoryNativeReplayProfile,
    boundary: MountedAuthenticatedClosedStoryBoundary,
    pre_window_state: MountedPreWindowState,
    pre_window_story_runtime: StoryChemistryRuntime,
    pre_window_sensor_states: tuple[MountedStorySensorState, ...],
    execution: StoryKernelReplayExecution,
) -> RecallStoryEpisode:
    """Admit one exact lived BASE execution; reject counterfactual replays."""

    if not isinstance(profile, MountedStoryNativeReplayProfile):
        raise ReceiptError("archive admission lacks a mounted story profile")
    if not isinstance(boundary, MountedAuthenticatedClosedStoryBoundary):
        raise ReceiptError("archive admission lacks an authenticated boundary")
    if not isinstance(pre_window_state, MountedPreWindowState):
        raise ReceiptError("archive admission lacks a pre-window state")
    if not isinstance(execution, StoryKernelReplayExecution):
        raise ReceiptError("archive admission lacks a real story execution")
    if execution.case.kind is not NativeReplayCaseKind.BASE:
        raise ReceiptError("counterfactual replay cannot enter lived episode memory")
    if execution.case.pre_window_state_receipt_sha256 != (
        pre_window_state.authority_receipt_sha256
    ):
        raise ReceiptError("admitted BASE execution belongs to another pre-window state")

    registry = execution.preparation.receipt_registry
    if registry.profile_binding_sha256 != profile.authority_receipt_sha256:
        raise ReceiptError("admitted episode belongs to another story profile")
    profile.verify(registry)
    boundary.verify(profile=profile, receipt_registry=registry)
    pre_window_state.verify(registry)
    execution.preparation.verify(profile.topology, registry)

    profile_lanes = {value.lane.value for value in profile.ports}
    if len(profile.ports) != 5 or profile_lanes != SENSORY_LANES:
        raise ReceiptError("archive admission requires the exact five sensory lanes")
    expected_story_ports = tuple(value.story_port_id for value in profile.ports)
    if tuple(
        value.port_id for value in pre_window_story_runtime.manifest.ports
    ) != expected_story_ports:
        raise ReceiptError("story chemistry manifest differs from story replay profile")
    if (
        execution.final_story_runtime.manifest.receipt_sha256
        != pre_window_story_runtime.manifest.receipt_sha256
    ):
        raise ReceiptError("story chemistry profile changed during admitted experience")
    _verify_story_runtime(
        runtime=pre_window_story_runtime,
        registry=registry,
        expected_port_ids=expected_story_ports,
        field_name="pre-window receiver state",
    )
    _verify_story_runtime(
        runtime=execution.final_story_runtime,
        registry=registry,
        expected_port_ids=expected_story_ports,
        field_name="post-window receiver state",
    )
    _verify_sensor_states(
        states=pre_window_sensor_states,
        profile=profile,
        registry=registry,
        field_name="pre-window native sensor state",
    )
    _verify_sensor_states(
        states=execution.final_sensor_states,
        profile=profile,
        registry=registry,
        field_name="post-window native sensor state",
    )

    expected_chemistry = story_replay_chemistry_state_receipt_payload(
        story_runtime=pre_window_story_runtime,
        sensor_states=pre_window_sensor_states,
    )
    if (
        receipt_sha256(expected_chemistry)
        != pre_window_state.chemistry_state_receipt_sha256
        or registry.resolve(
            pre_window_state.chemistry_state_receipt_sha256,
            "archive pre-window chemistry state receipt",
        )
        != expected_chemistry
    ):
        raise ReceiptError("pre-window state does not bind the archived receiver states")

    starts = {value.source_time_start for value in boundary.event.observations}
    ends = {value.source_time_end for value in boundary.event.observations}
    if len(starts) != 1 or len(ends) != 1:
        raise ReceiptError("authenticated boundary senses do not share one time window")
    source_start = next(iter(starts))
    source_end = next(iter(ends))
    if (
        execution.preparation.source_time_start != source_start
        or execution.preparation.source_time_end != source_end
        or any(value.source_time != source_start for value in pre_window_story_runtime.states)
        or any(
            value.last_timestamp != source_start
            for value in pre_window_sensor_states
        )
        or any(
            value.source_time != source_end
            for value in execution.final_story_runtime.states
        )
        or any(
            value.last_timestamp != source_end
            for value in execution.final_sensor_states
        )
    ):
        raise ReceiptError("archived chemistry, evidence, and boundary times differ")

    expected_fibers = {value.field_key for value in profile.ports}
    actual_fibers = {value.key for value in execution.preparation.evidence}
    if actual_fibers != expected_fibers:
        raise ReceiptError("admitted evidence does not cover every five-sense fiber")
    sensory_bindings = tuple(
        ArchivedSensoryEvidenceBinding.from_evidence(value)
        for value in execution.preparation.evidence
    )
    for value in execution.preparation.evidence:
        value.verify(registry)

    profile_receipts = _profile_receipts(profile, pre_window_story_runtime)
    for digest in profile_receipts:
        _mounted_exact(registry, digest, "archive admitted profile receipt")
    records = tuple(sorted(registry.records, key=lambda value: value.digest))
    boundary_observations = tuple(
        value.observation_receipt_sha256 for value in boundary.event.observations
    )
    episode_payload = recall_story_episode_receipt_payload(
        profile_binding_sha256=profile.authority_receipt_sha256,
        profile_receipt_sha256s=profile_receipts,
        boundary_receipt_sha256=boundary.authority_receipt_sha256,
        boundary_observation_receipt_sha256s=boundary_observations,
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        pre_window_receiver_state_receipt_sha256s=tuple(
            value.receipt_sha256 for value in pre_window_story_runtime.states
        ),
        post_window_receiver_state_receipt_sha256s=tuple(
            value.receipt_sha256 for value in execution.final_story_runtime.states
        ),
        pre_window_sensor_state_receipt_sha256s=tuple(
            value.authority_receipt_sha256 for value in pre_window_sensor_states
        ),
        post_window_sensor_state_receipt_sha256s=tuple(
            value.authority_receipt_sha256 for value in execution.final_sensor_states
        ),
        evidence_preparation_receipt_sha256=execution.preparation.receipt_sha256,
        sensory_evidence_bindings=sensory_bindings,
        mounted_receipt_sha256s=tuple(value.digest for value in records),
    )
    episode = RecallStoryEpisode(
        profile_binding_sha256=profile.authority_receipt_sha256,
        profile_receipt_sha256s=profile_receipts,
        boundary_receipt_sha256=boundary.authority_receipt_sha256,
        boundary_observation_receipt_sha256s=boundary_observations,
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        pre_window_receiver_state_receipt_sha256s=tuple(
            value.receipt_sha256 for value in pre_window_story_runtime.states
        ),
        post_window_receiver_state_receipt_sha256s=tuple(
            value.receipt_sha256 for value in execution.final_story_runtime.states
        ),
        pre_window_sensor_state_receipt_sha256s=tuple(
            value.authority_receipt_sha256 for value in pre_window_sensor_states
        ),
        post_window_sensor_state_receipt_sha256s=tuple(
            value.authority_receipt_sha256 for value in execution.final_sensor_states
        ),
        evidence_preparation_receipt_sha256=execution.preparation.receipt_sha256,
        sensory_evidence_bindings=sensory_bindings,
        receipt_records=records,
        episode_receipt_sha256=receipt_sha256(episode_payload),
        episode_receipt_payload=episode_payload,
    )
    episode.verify()
    return episode


def recall_story_archive_receipt_payload(
    episodes: tuple[RecallStoryEpisode, ...],
) -> bytes:
    return _canonical_bytes(
        {
            "episode_receipt_sha256s": [
                value.episode_receipt_sha256 for value in episodes
            ],
            "schema": ARCHIVE_ROOT_SCHEMA,
        }
    )


@dataclass(frozen=True, slots=True)
class RecallStoryEpisodeArchive:
    """Immutable archive indexed only by exact profile and sensory receipts."""

    episodes: tuple[RecallStoryEpisode, ...] = ()
    _by_receipts: Mapping[
        tuple[str, tuple[str, ...]], RecallStoryEpisode
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.episodes, tuple) or not all(
            isinstance(value, RecallStoryEpisode) for value in self.episodes
        ):
            raise ReceiptError("story episode archive must be typed and immutable")
        digests = tuple(value.episode_receipt_sha256 for value in self.episodes)
        if digests != tuple(sorted(digests)) or len(set(digests)) != len(digests):
            raise ReceiptError("story episode archive is not canonical and unique")
        index: dict[tuple[str, tuple[str, ...]], RecallStoryEpisode] = {}
        for value in self.episodes:
            value.verify()
            key = (value.profile_binding_sha256, value.sensory_receipt_set_key)
            if key in index:
                raise ReceiptError(
                    "two episodes claim the same complete sensory receipt set"
                )
            index[key] = value
        object.__setattr__(self, "_by_receipts", MappingProxyType(index))

    @property
    def receipt_payload(self) -> bytes:
        return recall_story_archive_receipt_payload(self.episodes)

    @property
    def receipt_sha256(self) -> str:
        return receipt_sha256(self.receipt_payload)

    def with_episode(self, episode: RecallStoryEpisode) -> "RecallStoryEpisodeArchive":
        if not isinstance(episode, RecallStoryEpisode):
            raise ReceiptError("archive admission is not a typed story episode")
        episode.verify()
        key = (episode.profile_binding_sha256, episode.sensory_receipt_set_key)
        if key in self._by_receipts:
            current = self._by_receipts[key]
            if current == episode:
                return self
            raise ReceiptError("complete sensory receipt set is already bound")
        return RecallStoryEpisodeArchive(
            tuple(
                sorted(
                    (*self.episodes, episode),
                    key=lambda value: value.episode_receipt_sha256,
                )
            )
        )

    def resolve(
        self,
        *,
        profile_binding_sha256: str,
        sensory_evidence_receipt_sha256s: tuple[str, ...],
    ) -> RecallStoryEpisode:
        sha256_digest(profile_binding_sha256, "recall archive profile binding")
        if not isinstance(sensory_evidence_receipt_sha256s, tuple) or not (
            sensory_evidence_receipt_sha256s
        ):
            raise ReceiptError("recall requires an immutable complete sensory receipt set")
        for index, value in enumerate(sensory_evidence_receipt_sha256s):
            sha256_digest(value, f"recall sensory receipt[{index}]")
        if len(set(sensory_evidence_receipt_sha256s)) != len(
            sensory_evidence_receipt_sha256s
        ):
            raise ReceiptError("recall sensory receipt set contains a duplicate")
        key = (
            profile_binding_sha256,
            tuple(sorted(sensory_evidence_receipt_sha256s)),
        )
        try:
            return self._by_receipts[key]
        except KeyError as exc:
            raise ReceiptError(
                "no episode has this exact profile and complete sensory receipt set"
            ) from exc


def _binding_body(value: ArchivedSensoryEvidenceBinding) -> dict[str, object]:
    return {
        "evidence_id": value.evidence_id,
        "evidence_receipt_sha256": value.evidence_receipt_sha256,
        "lane_id": value.lane_id,
        "port_id": value.port_id,
        "raw_record_sha256": value.raw_record_sha256,
    }


def _episode_body(value: RecallStoryEpisode) -> dict[str, object]:
    return {
        "boundary_observation_receipt_sha256s": list(
            value.boundary_observation_receipt_sha256s
        ),
        "boundary_receipt_sha256": value.boundary_receipt_sha256,
        "episode_receipt_payload_hex": value.episode_receipt_payload.hex(),
        "episode_receipt_sha256": value.episode_receipt_sha256,
        "evidence_preparation_receipt_sha256": (
            value.evidence_preparation_receipt_sha256
        ),
        "post_window_receiver_state_receipt_sha256s": list(
            value.post_window_receiver_state_receipt_sha256s
        ),
        "post_window_sensor_state_receipt_sha256s": list(
            value.post_window_sensor_state_receipt_sha256s
        ),
        "pre_window_receiver_state_receipt_sha256s": list(
            value.pre_window_receiver_state_receipt_sha256s
        ),
        "pre_window_sensor_state_receipt_sha256s": list(
            value.pre_window_sensor_state_receipt_sha256s
        ),
        "pre_window_state_receipt_sha256": value.pre_window_state_receipt_sha256,
        "profile_binding_sha256": value.profile_binding_sha256,
        "profile_receipt_sha256s": list(value.profile_receipt_sha256s),
        "receipt_records": [
            {"payload_hex": record.payload.hex(), "sha256": record.digest}
            for record in value.receipt_records
        ],
        "sensory_evidence_bindings": [
            _binding_body(binding) for binding in value.sensory_evidence_bindings
        ],
    }


def recall_story_archive_checkpoint_payload(
    *,
    archive: RecallStoryEpisodeArchive,
    checkpoint_id: str,
    authentication_key: bytes,
    key_id: str,
) -> bytes:
    if not isinstance(archive, RecallStoryEpisodeArchive):
        raise ReceiptError("story archive checkpoint lacks an archive")
    require_identifier(checkpoint_id, "story archive checkpoint id")
    require_identifier(key_id, "story archive checkpoint key id")
    if not isinstance(authentication_key, bytes) or not authentication_key:
        raise ReceiptError("story archive checkpoint authentication key is absent")
    body = {
        "archive_receipt_sha256": archive.receipt_sha256,
        "checkpoint_id": checkpoint_id,
        "episodes": [_episode_body(value) for value in archive.episodes],
        "schema": ARCHIVE_CHECKPOINT_SCHEMA,
    }
    signature = hmac.new(
        authentication_key,
        _canonical_bytes(body),
        hashlib.sha256,
    ).hexdigest()
    return _canonical_bytes(
        {
            "authentication": {
                "algorithm": ARCHIVE_CHECKPOINT_ALGORITHM,
                "key_id": key_id,
                "signature_sha256": signature,
            },
            "body": body,
        }
    )


_EPISODE_BODY_KEYS = frozenset(
    (
        "boundary_observation_receipt_sha256s",
        "boundary_receipt_sha256",
        "episode_receipt_payload_hex",
        "episode_receipt_sha256",
        "evidence_preparation_receipt_sha256",
        "post_window_receiver_state_receipt_sha256s",
        "post_window_sensor_state_receipt_sha256s",
        "pre_window_receiver_state_receipt_sha256s",
        "pre_window_sensor_state_receipt_sha256s",
        "pre_window_state_receipt_sha256",
        "profile_binding_sha256",
        "profile_receipt_sha256s",
        "receipt_records",
        "sensory_evidence_bindings",
    )
)


def _restore_binding(value: object) -> ArchivedSensoryEvidenceBinding:
    if not isinstance(value, dict):
        raise ReceiptError("archive checkpoint sensory binding is malformed")
    _expect_exact_keys(
        value,
        frozenset(
            (
                "evidence_id",
                "evidence_receipt_sha256",
                "lane_id",
                "port_id",
                "raw_record_sha256",
            )
        ),
        "archive checkpoint sensory binding",
    )
    if not all(
        isinstance(value.get(key), str)
        for key in (
            "evidence_id",
            "evidence_receipt_sha256",
            "lane_id",
            "port_id",
            "raw_record_sha256",
        )
    ):
        raise ReceiptError("archive checkpoint sensory binding fields are malformed")
    return ArchivedSensoryEvidenceBinding(
        lane_id=value["lane_id"],  # type: ignore[arg-type]
        port_id=value["port_id"],  # type: ignore[arg-type]
        evidence_id=value["evidence_id"],  # type: ignore[arg-type]
        evidence_receipt_sha256=value["evidence_receipt_sha256"],  # type: ignore[arg-type]
        raw_record_sha256=value["raw_record_sha256"],  # type: ignore[arg-type]
    )


def _restore_episode(value: object) -> RecallStoryEpisode:
    if not isinstance(value, dict):
        raise ReceiptError("archive checkpoint episode is malformed")
    _expect_exact_keys(value, _EPISODE_BODY_KEYS, "archive checkpoint episode")
    records: list[ReceiptRecord] = []
    for index, raw in enumerate(
        _expect_list(value["receipt_records"], "archive checkpoint receipt records")
    ):
        if not isinstance(raw, dict) or frozenset(raw) != frozenset(
            ("payload_hex", "sha256")
        ):
            raise ReceiptError(
                f"archive checkpoint receipt record[{index}] is malformed"
            )
        digest = raw.get("sha256")
        if not isinstance(digest, str):
            raise ReceiptError("archive checkpoint receipt digest is malformed")
        payload = _hex_bytes(
            raw.get("payload_hex"),
            f"archive checkpoint receipt record[{index}] payload",
        )
        records.append(ReceiptRecord(digest=digest, payload=payload))
    bindings = tuple(
        _restore_binding(raw)
        for raw in _expect_list(
            value["sensory_evidence_bindings"],
            "archive checkpoint sensory bindings",
        )
    )
    string_fields = (
        "profile_binding_sha256",
        "boundary_receipt_sha256",
        "pre_window_state_receipt_sha256",
        "evidence_preparation_receipt_sha256",
        "episode_receipt_sha256",
    )
    if not all(isinstance(value.get(key), str) for key in string_fields):
        raise ReceiptError("archive checkpoint episode receipt fields are malformed")
    return RecallStoryEpisode(
        profile_binding_sha256=value["profile_binding_sha256"],  # type: ignore[arg-type]
        profile_receipt_sha256s=_digest_tuple(
            value["profile_receipt_sha256s"], "archive checkpoint profile receipts"
        ),
        boundary_receipt_sha256=value["boundary_receipt_sha256"],  # type: ignore[arg-type]
        boundary_observation_receipt_sha256s=_digest_tuple(
            value["boundary_observation_receipt_sha256s"],
            "archive checkpoint boundary observation receipts",
        ),
        pre_window_state_receipt_sha256=value["pre_window_state_receipt_sha256"],  # type: ignore[arg-type]
        pre_window_receiver_state_receipt_sha256s=_digest_tuple(
            value["pre_window_receiver_state_receipt_sha256s"],
            "archive checkpoint pre-window receiver receipts",
        ),
        post_window_receiver_state_receipt_sha256s=_digest_tuple(
            value["post_window_receiver_state_receipt_sha256s"],
            "archive checkpoint post-window receiver receipts",
        ),
        pre_window_sensor_state_receipt_sha256s=_digest_tuple(
            value["pre_window_sensor_state_receipt_sha256s"],
            "archive checkpoint pre-window sensor receipts",
        ),
        post_window_sensor_state_receipt_sha256s=_digest_tuple(
            value["post_window_sensor_state_receipt_sha256s"],
            "archive checkpoint post-window sensor receipts",
        ),
        evidence_preparation_receipt_sha256=value[
            "evidence_preparation_receipt_sha256"
        ],  # type: ignore[arg-type]
        sensory_evidence_bindings=bindings,
        receipt_records=tuple(records),
        episode_receipt_sha256=value["episode_receipt_sha256"],  # type: ignore[arg-type]
        episode_receipt_payload=_hex_bytes(
            value["episode_receipt_payload_hex"],
            "archive checkpoint episode receipt payload",
        ),
    )


def restore_recall_story_archive_checkpoint(
    *,
    checkpoint_payload: bytes,
    authentication_key: bytes,
    expected_key_id: str,
) -> RecallStoryEpisodeArchive:
    if not isinstance(authentication_key, bytes) or not authentication_key:
        raise ReceiptError("story archive checkpoint authentication key is absent")
    require_identifier(expected_key_id, "story archive checkpoint expected key id")
    envelope = _strict_json_object(
        checkpoint_payload,
        "story archive checkpoint envelope",
    )
    _expect_exact_keys(
        envelope,
        frozenset(("authentication", "body")),
        "story archive checkpoint envelope",
    )
    authentication = envelope["authentication"]
    body = envelope["body"]
    if not isinstance(authentication, dict) or not isinstance(body, dict):
        raise ReceiptError("story archive checkpoint envelope is malformed")
    _expect_exact_keys(
        authentication,
        frozenset(("algorithm", "key_id", "signature_sha256")),
        "story archive checkpoint authentication",
    )
    _expect_exact_keys(
        body,
        frozenset(("archive_receipt_sha256", "checkpoint_id", "episodes", "schema")),
        "story archive checkpoint body",
    )
    if (
        authentication.get("algorithm") != ARCHIVE_CHECKPOINT_ALGORITHM
        or authentication.get("key_id") != expected_key_id
    ):
        raise ReceiptError("story archive checkpoint authentication authority changed")
    signature = authentication.get("signature_sha256")
    if not isinstance(signature, str) or _SHA256_RE.fullmatch(signature) is None:
        raise ReceiptError("story archive checkpoint signature is malformed")
    expected_signature = hmac.new(
        authentication_key,
        _canonical_bytes(body),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ReceiptError("story archive checkpoint authentication failed")
    if body.get("schema") != ARCHIVE_CHECKPOINT_SCHEMA:
        raise ReceiptError("story archive checkpoint schema changed")
    checkpoint_id = body.get("checkpoint_id")
    if not isinstance(checkpoint_id, str):
        raise ReceiptError("story archive checkpoint id is malformed")
    require_identifier(checkpoint_id, "story archive checkpoint id")
    archive = RecallStoryEpisodeArchive(
        tuple(
            _restore_episode(value)
            for value in _expect_list(
                body["episodes"], "story archive checkpoint episodes"
            )
        )
    )
    archive_digest = body.get("archive_receipt_sha256")
    if not isinstance(archive_digest, str):
        raise ReceiptError("story archive checkpoint root receipt is malformed")
    if sha256_digest(
        archive_digest, "story archive checkpoint root receipt"
    ) != archive.receipt_sha256:
        raise ReceiptError("story archive checkpoint root changed")
    return archive


__all__ = [
    "ArchivedSensoryEvidenceBinding",
    "RecallStoryEpisode",
    "RecallStoryEpisodeArchive",
    "create_recall_story_episode",
    "recall_story_archive_checkpoint_payload",
    "restore_recall_story_archive_checkpoint",
]
