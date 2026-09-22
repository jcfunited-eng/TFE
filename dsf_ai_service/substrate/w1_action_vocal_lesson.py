"""Exact ordered W1 action-outcome to external-vocal lesson episodes.

One lesson is a temporal composition of two independently settled physical
events:

1. a dynamic W1 action outcome carrying complete non-auditory L0--L4 fields;
2. the immediately subsequent authenticated external binaural vocal episode.

The authenticated world revision chain is the ordering authority: the action
after-observation must be byte-identical to the vocal before-observation.
The action settlement supplies the physical roots.  The vocal episode supplies
only left/right recurrent q cells.  Static co-presence, coordinates, provider
labels, action names, transcripts, and scalar reductions never enter the
lesson identity.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
    grounding_roots_from_settlement,
)
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


W1_ACTION_VOCAL_LESSON_PROFILE_SCHEMA = (
    "guala.w1.action_vocal_lesson.profile.v1"
)
W1_ACTION_VOCAL_LESSON_SCHEMA = (
    "guala.w1.action_vocal_lesson.v1"
)
_LESSON_DOMAIN = b"guala-w1-action-vocal-lesson-v1\0"
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
        raise TypeError("W1 action-vocal lesson key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 action-vocal lesson key boundary changed")
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
        raise TypeError("W1 lesson time must be exact")
    return f"{value.numerator}/{value.denominator}"


def is_dynamic_grounding_root(root: GroundingRoot) -> bool:
    root.verify()
    value = json.loads(root.value_json)
    field_tuples = value.get("field_tuples")
    if not isinstance(field_tuples, list):
        return False
    return any(
        Fraction(field_value) != 0
        for field_tuple in field_tuples
        for _field_name, field_value in field_tuple["fields"]
    )


@dataclass(frozen=True, slots=True)
class W1ActionVocalLessonResourceProfile:
    profile_id: str
    max_lessons: int
    max_action_roots_per_lesson: int
    max_vocal_activations_per_lesson: int
    max_lesson_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_lessons: int,
        max_action_roots_per_lesson: int,
        max_vocal_activations_per_lesson: int,
        max_lesson_bytes: int,
    ) -> "W1ActionVocalLessonResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
            or len(profile_id.encode("utf-8")) > 512
        ):
            raise ValueError("W1 lesson profile identifier changed")
        provisional = cls(
            profile_id=profile_id,
            max_lessons=_positive(
                max_lessons, "W1 lesson capacity"
            ),
            max_action_roots_per_lesson=_positive(
                max_action_roots_per_lesson,
                "W1 lesson action-root capacity",
            ),
            max_vocal_activations_per_lesson=_positive(
                max_vocal_activations_per_lesson,
                "W1 lesson vocal-activation capacity",
            ),
            max_lesson_bytes=_positive(
                max_lesson_bytes, "W1 lesson byte capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_lessons=provisional.max_lessons,
            max_action_roots_per_lesson=(
                provisional.max_action_roots_per_lesson
            ),
            max_vocal_activations_per_lesson=(
                provisional.max_vocal_activations_per_lesson
            ),
            max_lesson_bytes=provisional.max_lesson_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_action_roots_per_lesson": (
                self.max_action_roots_per_lesson
            ),
            "max_lesson_bytes": self.max_lesson_bytes,
            "max_lessons": self.max_lessons,
            "max_vocal_activations_per_lesson": (
                self.max_vocal_activations_per_lesson
            ),
            "profile_id": self.profile_id,
            "schema": W1_ACTION_VOCAL_LESSON_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        for value, name in (
            (self.max_lessons, "W1 lesson capacity"),
            (
                self.max_action_roots_per_lesson,
                "W1 lesson action-root capacity",
            ),
            (
                self.max_vocal_activations_per_lesson,
                "W1 lesson vocal-activation capacity",
            ),
            (self.max_lesson_bytes, "W1 lesson byte capacity"),
        ):
            _positive(value, name)
        _sha256(
            self.authority_receipt_sha256,
            "W1 lesson profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 action-vocal lesson profile changed")


@dataclass(frozen=True, slots=True)
class W1ActionVocalLesson:
    lesson_id: str
    action_execution_receipt_sha256: str
    action_before_world_state_sha256: str
    action_evidence_receipt_sha256: str
    action_settlement_receipt_sha256: str
    vocal_execution_receipt_sha256: str
    vocal_evidence_receipt_sha256: str
    vocal_grounding_receipt_sha256: str
    action_before_revision: int
    junction_revision: int
    vocal_after_revision: int
    action_source_time_start: Fraction
    action_source_time_end: Fraction
    vocal_source_time_start: Fraction
    vocal_source_time_end: Fraction
    action_roots: tuple[GroundingRoot, ...]
    vocal_activations: tuple[W1BinauralActivationEvidence, ...]
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
            "action_before_revision": self.action_before_revision,
            "action_before_world_state_sha256": (
                self.action_before_world_state_sha256
            ),
            "action_evidence_receipt_sha256": (
                self.action_evidence_receipt_sha256
            ),
            "action_execution_receipt_sha256": (
                self.action_execution_receipt_sha256
            ),
            "action_roots": [
                value.as_record() for value in self.action_roots
            ],
            "action_settlement_receipt_sha256": (
                self.action_settlement_receipt_sha256
            ),
            "action_source_time_end": _fraction_text(
                self.action_source_time_end
            ),
            "action_source_time_start": _fraction_text(
                self.action_source_time_start
            ),
            "junction_revision": self.junction_revision,
            "schema": W1_ACTION_VOCAL_LESSON_SCHEMA,
            "vocal_activations": [
                value.record() for value in self.vocal_activations
            ],
            "vocal_after_revision": self.vocal_after_revision,
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


class W1ActionVocalLessonAuthority:
    """Bounded in-memory owner of source-disjoint temporal lessons."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1ActionVocalLessonResourceProfile,
        world_authority: EmbodimentWorldAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
    ) -> None:
        resource_profile.verify()
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 lesson requires its world authority")
        if not isinstance(
            physical_authority,
            W1AudiovisualPhysicalEvidenceAuthority,
        ):
            raise TypeError("W1 lesson requires physical evidence authority")
        if not isinstance(
            grounding_authority,
            W1BinauralGroundingEvidenceAuthority,
        ):
            raise TypeError("W1 lesson requires binaural grounding authority")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._lesson_key = hashlib.sha256(
            _LESSON_DOMAIN + root
        ).digest()
        self._profile = resource_profile
        self._world = world_authority
        self._physical = physical_authority
        self._grounding = grounding_authority
        self._lessons: dict[str, W1ActionVocalLesson] = {}
        self._used_source_receipts: set[str] = set()
        self._lock = threading.RLock()

    @property
    def lessons(self) -> tuple[W1ActionVocalLesson, ...]:
        with self._lock:
            return tuple(
                self._lessons[key] for key in sorted(self._lessons)
            )

    def _verify_lesson(self, lesson: W1ActionVocalLesson) -> None:
        for value, name in (
            (lesson.lesson_id, "W1 lesson"),
            (
                lesson.action_execution_receipt_sha256,
                "W1 lesson action execution",
            ),
            (
                lesson.action_before_world_state_sha256,
                "W1 lesson controlled world before",
            ),
            (
                lesson.action_evidence_receipt_sha256,
                "W1 lesson action evidence",
            ),
            (
                lesson.action_settlement_receipt_sha256,
                "W1 lesson action settlement",
            ),
            (
                lesson.vocal_execution_receipt_sha256,
                "W1 lesson vocal execution",
            ),
            (
                lesson.vocal_evidence_receipt_sha256,
                "W1 lesson vocal evidence",
            ),
            (
                lesson.vocal_grounding_receipt_sha256,
                "W1 lesson vocal grounding",
            ),
            (
                lesson.authority_hmac_sha256,
                "W1 lesson HMAC",
            ),
            (
                lesson.authority_receipt_sha256,
                "W1 lesson authority",
            ),
        ):
            _sha256(value, name)
        if (
            lesson.action_before_revision < 0
            or lesson.junction_revision
            != lesson.action_before_revision + 1
            or lesson.vocal_after_revision
            != lesson.junction_revision + 1
            or lesson.action_source_time_end
            <= lesson.action_source_time_start
            or lesson.vocal_source_time_end
            <= lesson.vocal_source_time_start
            or not lesson.action_roots
            or len(lesson.action_roots)
            > self._profile.max_action_roots_per_lesson
            or not lesson.vocal_activations
            or len(lesson.vocal_activations)
            > self._profile.max_vocal_activations_per_lesson
        ):
            raise ValueError("W1 action-vocal lesson boundary changed")
        for root in lesson.action_roots:
            root.verify()
            if not is_dynamic_grounding_root(root):
                raise ValueError(
                    "W1 lesson retained a static action root"
                )
        for activation in lesson.vocal_activations:
            activation.verify()
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
            raise ValueError("W1 action-vocal lesson authority changed")

    def compose(
        self,
        *,
        action_execution: ActionExecutionReceipt,
        action_mount: W1PhysicalEvidenceMount,
        vocal_execution: ActionExecutionReceipt,
        vocal_mount: W1PhysicalEvidenceMount,
        vocal_grounding: W1BinauralGroundingEvidence,
    ) -> W1ActionVocalLesson:
        self._world.verify_execution_receipt(action_execution)
        self._world.verify_execution_receipt(vocal_execution)
        self._physical.verify_mount(action_mount)
        self._physical.verify_mount(vocal_mount)
        self._grounding.verify(vocal_grounding)
        action_receipt = action_mount.evidence_receipt
        vocal_receipt = vocal_mount.evidence_receipt
        if (
            action_mount.state is not W1EvidenceState.OBSERVED
            or vocal_mount.state is not W1EvidenceState.OBSERVED
            or action_receipt is None
            or vocal_receipt is None
            or action_mount.causal_settlement is None
            or vocal_mount.causal_settlement is None
            or vocal_mount.binaural_receptor_settlement is None
        ):
            raise ValueError("W1 lesson requires two settled physical events")
        if (
            action_receipt.acoustic_emission_receipt_sha256s
            or not vocal_receipt.acoustic_emission_receipt_sha256s
            or action_receipt.world_execution_receipt_sha256
            != action_execution.authority_receipt_sha256
            or vocal_receipt.world_execution_receipt_sha256
            != vocal_execution.authority_receipt_sha256
            or action_execution.after != vocal_execution.before
            or action_execution.after.revision
            != vocal_execution.before.revision
            or action_execution.after.revision
            != action_execution.before.revision + 1
            or vocal_execution.after.revision
            != vocal_execution.before.revision + 1
            or vocal_execution.actor_body_id
            == vocal_execution.after.self_body_id
            or vocal_grounding.causal_settlement_receipt_sha256
            != vocal_mount.causal_settlement.authority_receipt_sha256
            or vocal_grounding.receptor_settlement_receipt_sha256
            != vocal_mount.binaural_receptor_settlement
            .authority_receipt_sha256
        ):
            raise ValueError(
                "W1 lesson world revision or physical source chain changed"
            )
        action_roots = tuple(
            root
            for root in grounding_roots_from_settlement(
                action_mount.causal_settlement
            )
            if is_dynamic_grounding_root(root)
        )
        if not action_roots:
            raise ValueError(
                "W1 lesson action outcome has no dynamic full-field root"
            )
        if (
            len(action_roots)
            > self._profile.max_action_roots_per_lesson
            or len(vocal_grounding.activations)
            > self._profile.max_vocal_activations_per_lesson
        ):
            raise RuntimeError("W1 lesson resource capacity exhausted")
        source_receipts = {
            action_execution.authority_receipt_sha256,
            action_receipt.authority_receipt_sha256,
            action_mount.causal_settlement.authority_receipt_sha256,
            vocal_execution.authority_receipt_sha256,
            vocal_receipt.authority_receipt_sha256,
            vocal_grounding.authority_receipt_sha256,
        }
        if len(source_receipts) != 6:
            raise ValueError("W1 lesson source identities overlap")
        provisional = W1ActionVocalLesson(
            lesson_id="0" * 64,
            action_execution_receipt_sha256=(
                action_execution.authority_receipt_sha256
            ),
            action_before_world_state_sha256=(
                action_execution.before.state_sha256
            ),
            action_evidence_receipt_sha256=(
                action_receipt.authority_receipt_sha256
            ),
            action_settlement_receipt_sha256=(
                action_mount.causal_settlement
                .authority_receipt_sha256
            ),
            vocal_execution_receipt_sha256=(
                vocal_execution.authority_receipt_sha256
            ),
            vocal_evidence_receipt_sha256=(
                vocal_receipt.authority_receipt_sha256
            ),
            vocal_grounding_receipt_sha256=(
                vocal_grounding.authority_receipt_sha256
            ),
            action_before_revision=action_execution.before.revision,
            junction_revision=action_execution.after.revision,
            vocal_after_revision=vocal_execution.after.revision,
            action_source_time_start=action_receipt.source_time_start,
            action_source_time_end=action_receipt.source_time_end,
            vocal_source_time_start=vocal_receipt.source_time_start,
            vocal_source_time_end=vocal_receipt.source_time_end,
            action_roots=action_roots,
            vocal_activations=vocal_grounding.activations,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._lesson_key,
            _LESSON_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        lesson = W1ActionVocalLesson(
            lesson_id=_digest(payload),
            action_execution_receipt_sha256=(
                provisional.action_execution_receipt_sha256
            ),
            action_before_world_state_sha256=(
                provisional.action_before_world_state_sha256
            ),
            action_evidence_receipt_sha256=(
                provisional.action_evidence_receipt_sha256
            ),
            action_settlement_receipt_sha256=(
                provisional.action_settlement_receipt_sha256
            ),
            vocal_execution_receipt_sha256=(
                provisional.vocal_execution_receipt_sha256
            ),
            vocal_evidence_receipt_sha256=(
                provisional.vocal_evidence_receipt_sha256
            ),
            vocal_grounding_receipt_sha256=(
                provisional.vocal_grounding_receipt_sha256
            ),
            action_before_revision=provisional.action_before_revision,
            junction_revision=provisional.junction_revision,
            vocal_after_revision=provisional.vocal_after_revision,
            action_source_time_start=provisional.action_source_time_start,
            action_source_time_end=provisional.action_source_time_end,
            vocal_source_time_start=provisional.vocal_source_time_start,
            vocal_source_time_end=provisional.vocal_source_time_end,
            action_roots=provisional.action_roots,
            vocal_activations=provisional.vocal_activations,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self._verify_lesson(lesson)
        with self._lock:
            if self._used_source_receipts.intersection(source_receipts):
                raise ValueError("W1 lesson reuses a physical source")
            if len(self._lessons) >= self._profile.max_lessons:
                raise RuntimeError("W1 lesson capacity exhausted")
            self._lessons[lesson.lesson_id] = lesson
            self._used_source_receipts.update(source_receipts)
        return lesson

    def verify(self, lesson: W1ActionVocalLesson) -> None:
        if not isinstance(lesson, W1ActionVocalLesson):
            raise TypeError("W1 action-vocal lesson is not typed")
        self._verify_lesson(lesson)

    def status(self) -> dict[str, int | bool]:
        with self._lock:
            return {
                "capacity": self._profile.max_lessons,
                "capacity_exhausted": (
                    len(self._lessons) >= self._profile.max_lessons
                ),
                "count": len(self._lessons),
                "used_source_receipts": len(
                    self._used_source_receipts
                ),
            }


__all__ = [
    "W1ActionVocalLesson",
    "W1ActionVocalLessonAuthority",
    "W1ActionVocalLessonResourceProfile",
    "is_dynamic_grounding_root",
]
