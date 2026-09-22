"""Authenticated external-vocal cue followed by a signed spatial action.

One lesson preserves the exact causal order required for lived direction
grounding:

1. an external acoustic episode is physically observed and grounded through
   recurrent binaural activations;
2. self immediately enacts one signed spatial displacement from the
   byte-identical world observation produced by that vocal episode.

The lesson retains the complete vocal activations and the complete signed
spatial settlement, including every dynamic D/M/R/U/C/P/B root.  It contains
no transcript, command name, tutor label, score, or reduced decision vector.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
    W1PhysicalEvidenceMount,
)
from dsf_ai_service.substrate.w1_binaural_controlled_distinction import (
    W1DiagnosticCell,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralActivationEvidence,
    W1BinauralGroundingEvidence,
    W1BinauralGroundingEvidenceAuthority,
)
from dsf_ai_service.substrate.w1_signed_spatial_action_settlement import (
    W1SignedSpatialActionSettlement,
    W1SignedSpatialActionSettlementAuthority,
)


W1_VOCAL_SPATIAL_ACTION_PROFILE_SCHEMA = (
    "guala.w1.vocal_spatial_action_lesson.profile.v1"
)
W1_VOCAL_SPATIAL_ACTION_LESSON_SCHEMA = (
    "guala.w1.vocal_spatial_action_lesson.v1"
)
W1_VOCAL_SPATIAL_ACTION_STATE_SCHEMA = (
    "guala.w1.vocal_spatial_action_lesson.state.v1"
)
W1_VOCAL_SPATIAL_ACTION_ENVELOPE_SCHEMA = (
    "guala.w1.vocal_spatial_action_lesson.envelope.v1"
)
_LESSON_DOMAIN = b"guala-w1-vocal-spatial-action-lesson-v1\0"
_STATE_DOMAIN = b"guala-w1-vocal-spatial-action-state-v1\0"
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("W1 vocal-spatial lesson key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 vocal-spatial lesson key boundary changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("W1 vocal-spatial lesson time must be exact")
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class W1VocalSpatialActionLessonResourceProfile:
    profile_id: str
    max_lessons: int
    max_vocal_activations_per_lesson: int
    max_lesson_bytes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_lessons: int,
        max_vocal_activations_per_lesson: int,
        max_lesson_bytes: int,
        max_state_bytes: int,
    ) -> "W1VocalSpatialActionLessonResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
            or len(profile_id.encode("utf-8")) > 512
        ):
            raise ValueError("W1 vocal-spatial profile identifier changed")
        provisional = cls(
            profile_id=profile_id,
            max_lessons=_positive(
                max_lessons, "W1 vocal-spatial lesson capacity"
            ),
            max_vocal_activations_per_lesson=_positive(
                max_vocal_activations_per_lesson,
                "W1 vocal-spatial activation capacity",
            ),
            max_lesson_bytes=_positive(
                max_lesson_bytes, "W1 vocal-spatial lesson byte capacity"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "W1 vocal-spatial state byte capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_lessons=provisional.max_lessons,
            max_vocal_activations_per_lesson=(
                provisional.max_vocal_activations_per_lesson
            ),
            max_lesson_bytes=provisional.max_lesson_bytes,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_lesson_bytes": self.max_lesson_bytes,
            "max_lessons": self.max_lessons,
            "max_state_bytes": self.max_state_bytes,
            "max_vocal_activations_per_lesson": (
                self.max_vocal_activations_per_lesson
            ),
            "profile_id": self.profile_id,
            "schema": W1_VOCAL_SPATIAL_ACTION_PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        for value, name in (
            (self.max_lessons, "W1 vocal-spatial lesson capacity"),
            (
                self.max_vocal_activations_per_lesson,
                "W1 vocal-spatial activation capacity",
            ),
            (self.max_lesson_bytes, "W1 vocal-spatial lesson byte capacity"),
            (self.max_state_bytes, "W1 vocal-spatial state byte capacity"),
        ):
            _positive(value, name)
        _sha256(
            self.authority_receipt_sha256,
            "W1 vocal-spatial profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 vocal-spatial profile changed")


@dataclass(frozen=True, slots=True)
class W1VocalSpatialActionLesson:
    lesson_id: str
    vocal_execution_receipt_sha256: str
    vocal_evidence_receipt_sha256: str
    vocal_grounding_receipt_sha256: str
    spatial_settlement_receipt_sha256: str
    vocal_before_world_state_sha256: str
    junction_world_state_sha256: str
    action_after_world_state_sha256: str
    vocal_before_revision: int
    junction_revision: int
    action_after_revision: int
    vocal_source_time_start: Fraction
    vocal_source_time_end: Fraction
    vocal_activations: tuple[W1BinauralActivationEvidence, ...]
    spatial_settlement: W1SignedSpatialActionSettlement
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def vocal_cells(self) -> frozenset[W1DiagnosticCell]:
        return frozenset(
            W1DiagnosticCell(value.ear_id, value.neuron_id)
            for value in self.vocal_activations
        )

    def payload(self) -> dict[str, object]:
        return {
            "action_after_revision": self.action_after_revision,
            "action_after_world_state_sha256": (
                self.action_after_world_state_sha256
            ),
            "junction_revision": self.junction_revision,
            "junction_world_state_sha256": self.junction_world_state_sha256,
            "schema": W1_VOCAL_SPATIAL_ACTION_LESSON_SCHEMA,
            "spatial_settlement": self.spatial_settlement.record(),
            "spatial_settlement_receipt_sha256": (
                self.spatial_settlement_receipt_sha256
            ),
            "vocal_activations": [
                value.record() for value in self.vocal_activations
            ],
            "vocal_before_revision": self.vocal_before_revision,
            "vocal_before_world_state_sha256": (
                self.vocal_before_world_state_sha256
            ),
            "vocal_evidence_receipt_sha256": (
                self.vocal_evidence_receipt_sha256
            ),
            "vocal_execution_receipt_sha256": (
                self.vocal_execution_receipt_sha256
            ),
            "vocal_grounding_receipt_sha256": (
                self.vocal_grounding_receipt_sha256
            ),
            "vocal_source_time_end": _fraction_text(
                self.vocal_source_time_end
            ),
            "vocal_source_time_start": _fraction_text(
                self.vocal_source_time_start
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "lesson_id": self.lesson_id,
        }


@dataclass(frozen=True, slots=True)
class W1VocalSpatialActionRetainedSource:
    vocal_execution: ActionExecutionReceipt
    vocal_mount: W1PhysicalEvidenceMount
    vocal_grounding: W1BinauralGroundingEvidence
    action_execution: ActionExecutionReceipt
    action_mount: W1PhysicalEvidenceMount
    spatial_settlement: W1SignedSpatialActionSettlement


class W1VocalSpatialActionLessonAuthority:
    """Bounded persistent owner of vocal-cue then signed-action lessons."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1VocalSpatialActionLessonResourceProfile,
        world_authority: EmbodimentWorldAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
        spatial_authority: W1SignedSpatialActionSettlementAuthority,
    ) -> None:
        resource_profile.verify()
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 vocal-spatial lesson requires world authority")
        if not isinstance(
            physical_authority, W1AudiovisualPhysicalEvidenceAuthority
        ):
            raise TypeError(
                "W1 vocal-spatial lesson requires physical evidence authority"
            )
        if not isinstance(
            grounding_authority, W1BinauralGroundingEvidenceAuthority
        ):
            raise TypeError(
                "W1 vocal-spatial lesson requires grounding authority"
            )
        if not isinstance(
            spatial_authority, W1SignedSpatialActionSettlementAuthority
        ):
            raise TypeError(
                "W1 vocal-spatial lesson requires spatial authority"
            )
        root = hashlib.sha256(_key(authority_key)).digest()
        self._lesson_key = hashlib.sha256(
            _LESSON_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = resource_profile
        self._world = world_authority
        self._physical = physical_authority
        self._grounding = grounding_authority
        self._spatial = spatial_authority
        self._lessons: dict[str, W1VocalSpatialActionLesson] = {}
        self._used_source_receipts: set[str] = set()
        self._lock = threading.RLock()

    @property
    def lessons(self) -> tuple[W1VocalSpatialActionLesson, ...]:
        with self._lock:
            return tuple(
                self._lessons[key] for key in sorted(self._lessons)
            )

    def _verify_lesson(self, lesson: W1VocalSpatialActionLesson) -> None:
        for value, name in (
            (lesson.lesson_id, "W1 vocal-spatial lesson"),
            (
                lesson.vocal_execution_receipt_sha256,
                "W1 vocal-spatial vocal execution",
            ),
            (
                lesson.vocal_evidence_receipt_sha256,
                "W1 vocal-spatial vocal evidence",
            ),
            (
                lesson.vocal_grounding_receipt_sha256,
                "W1 vocal-spatial vocal grounding",
            ),
            (
                lesson.spatial_settlement_receipt_sha256,
                "W1 vocal-spatial settlement",
            ),
            (
                lesson.vocal_before_world_state_sha256,
                "W1 vocal-spatial world before",
            ),
            (
                lesson.junction_world_state_sha256,
                "W1 vocal-spatial junction world",
            ),
            (
                lesson.action_after_world_state_sha256,
                "W1 vocal-spatial world after",
            ),
            (lesson.authority_hmac_sha256, "W1 vocal-spatial HMAC"),
            (
                lesson.authority_receipt_sha256,
                "W1 vocal-spatial authority",
            ),
        ):
            _sha256(value, name)
        if (
            lesson.vocal_before_revision < 0
            or lesson.junction_revision != lesson.vocal_before_revision + 1
            or lesson.action_after_revision != lesson.junction_revision + 1
            or lesson.vocal_source_time_end
            <= lesson.vocal_source_time_start
            or not lesson.vocal_activations
            or len(lesson.vocal_activations)
            > self._profile.max_vocal_activations_per_lesson
        ):
            raise ValueError("W1 vocal-spatial lesson boundary changed")
        for activation in lesson.vocal_activations:
            activation.verify()
        self._spatial.verify(lesson.spatial_settlement)
        if (
            lesson.spatial_settlement_receipt_sha256
            != lesson.spatial_settlement.authority_receipt_sha256
            or lesson.junction_revision
            != lesson.spatial_settlement.before_revision
            or lesson.action_after_revision
            != lesson.spatial_settlement.after_revision
            or lesson.junction_world_state_sha256
            != lesson.spatial_settlement.before_world_state_sha256
            or lesson.action_after_world_state_sha256
            != lesson.spatial_settlement.after_world_state_sha256
        ):
            raise ValueError("W1 vocal-spatial signed action chain changed")
        payload = lesson.payload()
        signature = hmac.new(
            self._lesson_key,
            _LESSON_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            lesson.lesson_id != _digest(payload)
            or len(_canonical(payload)) > self._profile.max_lesson_bytes
            or not hmac.compare_digest(
                signature, lesson.authority_hmac_sha256
            )
            or lesson.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("W1 vocal-spatial lesson authority changed")

    def _from_sources(
        self, source: W1VocalSpatialActionRetainedSource
    ) -> tuple[W1VocalSpatialActionLesson, set[str]]:
        if not isinstance(source, W1VocalSpatialActionRetainedSource):
            raise TypeError("W1 vocal-spatial retained source is not typed")
        vocal_execution = source.vocal_execution
        vocal_mount = source.vocal_mount
        vocal_grounding = source.vocal_grounding
        action_execution = source.action_execution
        action_mount = source.action_mount
        spatial_settlement = source.spatial_settlement
        self._world.verify_execution_receipt(vocal_execution)
        self._world.verify_execution_receipt(action_execution)
        self._physical.verify_mount(vocal_mount)
        self._physical.verify_mount(action_mount)
        self._grounding.verify(vocal_grounding)
        self._spatial.verify(spatial_settlement)
        vocal_evidence = vocal_mount.evidence_receipt
        action_evidence = action_mount.evidence_receipt
        vocal_causal = vocal_mount.causal_settlement
        action_causal = action_mount.causal_settlement
        receptor = vocal_mount.binaural_receptor_settlement
        if (
            vocal_mount.state is not W1EvidenceState.OBSERVED
            or action_mount.state is not W1EvidenceState.OBSERVED
            or vocal_evidence is None
            or action_evidence is None
            or vocal_causal is None
            or action_causal is None
            or receptor is None
        ):
            raise ValueError(
                "W1 vocal-spatial lesson requires settled physical events"
            )
        if (
            not vocal_evidence.acoustic_emission_receipt_sha256s
            or action_evidence.acoustic_emission_receipt_sha256s
            or vocal_evidence.world_execution_receipt_sha256
            != vocal_execution.authority_receipt_sha256
            or action_evidence.world_execution_receipt_sha256
            != action_execution.authority_receipt_sha256
            or vocal_execution.actor_body_id
            == vocal_execution.after.self_body_id
            or action_execution.actor_body_id
            != action_execution.after.self_body_id
            or vocal_execution.after != action_execution.before
            or vocal_execution.after.revision
            != action_execution.before.revision
            or vocal_execution.after.revision
            != vocal_execution.before.revision + 1
            or action_execution.after.revision
            != action_execution.before.revision + 1
            or vocal_grounding.causal_settlement_receipt_sha256
            != vocal_causal.authority_receipt_sha256
            or vocal_grounding.receptor_settlement_receipt_sha256
            != receptor.authority_receipt_sha256
            or spatial_settlement.execution_receipt_sha256
            != action_execution.authority_receipt_sha256
            or spatial_settlement.evidence_receipt_sha256
            != action_evidence.authority_receipt_sha256
            or spatial_settlement.causal_settlement_receipt_sha256
            != action_causal.authority_receipt_sha256
        ):
            raise ValueError(
                "W1 vocal-spatial world revision or physical source chain changed"
            )
        if (
            len(vocal_grounding.activations)
            > self._profile.max_vocal_activations_per_lesson
        ):
            raise RuntimeError("W1 vocal-spatial lesson capacity exhausted")
        provisional = W1VocalSpatialActionLesson(
            lesson_id="0" * 64,
            vocal_execution_receipt_sha256=(
                vocal_execution.authority_receipt_sha256
            ),
            vocal_evidence_receipt_sha256=(
                vocal_evidence.authority_receipt_sha256
            ),
            vocal_grounding_receipt_sha256=(
                vocal_grounding.authority_receipt_sha256
            ),
            spatial_settlement_receipt_sha256=(
                spatial_settlement.authority_receipt_sha256
            ),
            vocal_before_world_state_sha256=(
                vocal_execution.before.state_sha256
            ),
            junction_world_state_sha256=(
                vocal_execution.after.state_sha256
            ),
            action_after_world_state_sha256=(
                action_execution.after.state_sha256
            ),
            vocal_before_revision=vocal_execution.before.revision,
            junction_revision=vocal_execution.after.revision,
            action_after_revision=action_execution.after.revision,
            vocal_source_time_start=vocal_evidence.source_time_start,
            vocal_source_time_end=vocal_evidence.source_time_end,
            vocal_activations=vocal_grounding.activations,
            spatial_settlement=spatial_settlement,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._lesson_key,
            _LESSON_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        lesson = W1VocalSpatialActionLesson(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name not in {
                    "lesson_id",
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            lesson_id=_digest(payload),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        source_receipts = {
            vocal_execution.authority_receipt_sha256,
            vocal_evidence.authority_receipt_sha256,
            vocal_grounding.authority_receipt_sha256,
            action_execution.authority_receipt_sha256,
            action_evidence.authority_receipt_sha256,
            action_causal.authority_receipt_sha256,
            spatial_settlement.authority_receipt_sha256,
        }
        if len(source_receipts) != 7:
            raise ValueError("W1 vocal-spatial source identities overlap")
        self._verify_lesson(lesson)
        return lesson, source_receipts

    def _body(
        self, lessons: Mapping[str, W1VocalSpatialActionLesson]
    ) -> dict[str, object]:
        return {
            "lessons": [
                lessons[key].record() for key in sorted(lessons)
            ],
            "resource_profile": self._profile.record(),
            "schema": W1_VOCAL_SPATIAL_ACTION_STATE_SCHEMA,
        }

    def _encoded(
        self, lessons: Mapping[str, W1VocalSpatialActionLesson]
    ) -> bytes:
        body = self._body(lessons)
        encoded = _canonical({
            "body": body,
            "schema": W1_VOCAL_SPATIAL_ACTION_ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("W1 vocal-spatial state capacity exhausted")
        return encoded

    def compose(
        self,
        *,
        vocal_execution: ActionExecutionReceipt,
        vocal_mount: W1PhysicalEvidenceMount,
        vocal_grounding: W1BinauralGroundingEvidence,
        action_execution: ActionExecutionReceipt,
        action_mount: W1PhysicalEvidenceMount,
        spatial_settlement: W1SignedSpatialActionSettlement,
    ) -> W1VocalSpatialActionLesson:
        lesson, source_receipts = self._from_sources(
            W1VocalSpatialActionRetainedSource(
                vocal_execution=vocal_execution,
                vocal_mount=vocal_mount,
                vocal_grounding=vocal_grounding,
                action_execution=action_execution,
                action_mount=action_mount,
                spatial_settlement=spatial_settlement,
            )
        )
        with self._lock:
            if self._used_source_receipts.intersection(source_receipts):
                raise ValueError(
                    "W1 vocal-spatial lesson reuses a physical source"
                )
            if len(self._lessons) >= self._profile.max_lessons:
                raise RuntimeError("W1 vocal-spatial lesson capacity exhausted")
            candidate = dict(self._lessons)
            candidate[lesson.lesson_id] = lesson
            self._encoded(candidate)
            self._lessons = candidate
            self._used_source_receipts.update(source_receipts)
        return lesson

    def verify(self, lesson: W1VocalSpatialActionLesson) -> None:
        if not isinstance(lesson, W1VocalSpatialActionLesson):
            raise TypeError("W1 vocal-spatial lesson is not typed")
        self._verify_lesson(lesson)

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._lessons)

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
        world_authority: EmbodimentWorldAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
        spatial_authority: W1SignedSpatialActionSettlementAuthority,
        retained_sources: tuple[W1VocalSpatialActionRetainedSource, ...],
    ) -> "W1VocalSpatialActionLessonAuthority":
        if not isinstance(encoded, bytes):
            raise TypeError("W1 vocal-spatial state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "W1 vocal-spatial state is not canonical JSON"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema")
            != W1_VOCAL_SPATIAL_ACTION_ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("W1 vocal-spatial state envelope changed")
        body = envelope["body"]
        if (
            set(body) != {"lessons", "resource_profile", "schema"}
            or body.get("schema") != W1_VOCAL_SPATIAL_ACTION_STATE_SCHEMA
            or not isinstance(body.get("lessons"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
            or not isinstance(retained_sources, tuple)
        ):
            raise ValueError("W1 vocal-spatial state body changed")
        raw_profile = body["resource_profile"]
        if set(raw_profile) != {
            "authority_receipt_sha256",
            "max_lesson_bytes",
            "max_lessons",
            "max_state_bytes",
            "max_vocal_activations_per_lesson",
            "profile_id",
            "schema",
        }:
            raise ValueError("W1 vocal-spatial profile record changed")
        profile = W1VocalSpatialActionLessonResourceProfile(
            profile_id=raw_profile.get("profile_id"),
            max_lessons=raw_profile.get("max_lessons"),
            max_vocal_activations_per_lesson=raw_profile.get(
                "max_vocal_activations_per_lesson"
            ),
            max_lesson_bytes=raw_profile.get("max_lesson_bytes"),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        profile.verify()
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
            world_authority=world_authority,
            physical_authority=physical_authority,
            grounding_authority=grounding_authority,
            spatial_authority=spatial_authority,
        )
        expected_hmac = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""), expected_hmac
        ):
            raise ValueError("W1 vocal-spatial state HMAC changed")
        raw_by_id: dict[str, Mapping[str, object]] = {}
        for raw in body["lessons"]:
            if not isinstance(raw, Mapping):
                raise ValueError("W1 vocal-spatial lesson record changed")
            lesson_id = raw.get("lesson_id")
            _sha256(lesson_id, "W1 restored vocal-spatial lesson")
            if lesson_id in raw_by_id:
                raise ValueError("W1 vocal-spatial lesson is duplicated")
            raw_by_id[lesson_id] = raw
        if len(raw_by_id) != len(retained_sources):
            raise ValueError("W1 vocal-spatial retained source set changed")
        for source in retained_sources:
            lesson, source_receipts = owner._from_sources(source)
            raw = raw_by_id.pop(lesson.lesson_id, None)
            if raw is None or lesson.record() != raw:
                raise ValueError(
                    "W1 vocal-spatial state conflicts with retained source"
                )
            if owner._used_source_receipts.intersection(source_receipts):
                raise ValueError(
                    "W1 restored vocal-spatial source is duplicated"
                )
            owner._lessons[lesson.lesson_id] = lesson
            owner._used_source_receipts.update(source_receipts)
        if (
            raw_by_id
            or len(owner._lessons) > profile.max_lessons
            or owner.snapshot_encoded() != encoded
        ):
            raise ValueError("W1 restored vocal-spatial state changed")
        return owner

    def status(self) -> dict[str, int | bool]:
        with self._lock:
            state_bytes = len(self._encoded(self._lessons))
            return {
                "capacity": self._profile.max_lessons,
                "capacity_exhausted": (
                    len(self._lessons) >= self._profile.max_lessons
                ),
                "count": len(self._lessons),
                "state_bytes": state_bytes,
                "state_capacity_bytes": self._profile.max_state_bytes,
                "used_source_receipts": len(
                    self._used_source_receipts
                ),
            }


__all__ = [
    "W1VocalSpatialActionLesson",
    "W1VocalSpatialActionLessonAuthority",
    "W1VocalSpatialActionLessonResourceProfile",
    "W1VocalSpatialActionRetainedSource",
]
