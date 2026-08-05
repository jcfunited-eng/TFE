"""Unlabeled real-pressure provenance for cue-to-spatial-action lessons."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

from dsf_ai_service.substrate.embodiment_world import ActionExecutionReceipt
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_spatial_vocal_relation import (
    W1AnonymousSpatialVocalLesson,
    W1AnonymousSpatialVocalRelationOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1PhysicalEvidenceMount,
)
from dsf_ai_service.substrate.w1_speech_commands_tutor_plan import (
    W1TutoredSpeechPressure,
)
from dsf_ai_service.substrate.w1_vocal_spatial_action_lesson import (
    W1VocalSpatialActionLesson,
    W1VocalSpatialActionLessonAuthority,
)


W1_ANONYMOUS_SPATIAL_VOCAL_PROVENANCE_SCHEMA = (
    "guala.w1.anonymous_spatial_vocal.provenance.v2"
)
_DOMAIN = b"guala-w1-anonymous-spatial-vocal-provenance-v2\0"
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


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


@dataclass(frozen=True, slots=True)
class W1AnonymousSpatialVocalProvenance:
    spatial_vocal_lesson_receipt_sha256: str
    vocal_spatial_action_lesson_receipt_sha256: str
    pressure_authority_receipt_sha256: str
    pressure_source_file_sha256: str
    emission_receipt_sha256: str
    vocal_execution_receipt_sha256: str
    vocal_evidence_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "emission_receipt_sha256": self.emission_receipt_sha256,
            "pressure_authority_receipt_sha256": (
                self.pressure_authority_receipt_sha256
            ),
            "pressure_source_file_sha256": self.pressure_source_file_sha256,
            "schema": W1_ANONYMOUS_SPATIAL_VOCAL_PROVENANCE_SCHEMA,
            "spatial_vocal_lesson_receipt_sha256": (
                self.spatial_vocal_lesson_receipt_sha256
            ),
            "vocal_evidence_receipt_sha256": (
                self.vocal_evidence_receipt_sha256
            ),
            "vocal_execution_receipt_sha256": (
                self.vocal_execution_receipt_sha256
            ),
            "vocal_spatial_action_lesson_receipt_sha256": (
                self.vocal_spatial_action_lesson_receipt_sha256
            ),
        }


class W1AnonymousSpatialVocalProvenanceAuthority:
    """Authenticate exact pressure origin without tutor metadata in cognition."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        tutor_pressure_key: bytes | str,
        relation_owner: W1AnonymousSpatialVocalRelationOwner,
        lesson_authority: W1VocalSpatialActionLessonAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
        emitter_authority: W1AcousticEmitterAuthority,
        max_bindings: int,
    ) -> None:
        key = (
            authority_key.encode("utf-8")
            if isinstance(authority_key, str)
            else bytes(authority_key)
        )
        if not 32 <= len(key) <= 4_096:
            raise ValueError("W1 spatial-vocal provenance key changed")
        if (
            isinstance(max_bindings, bool)
            or not isinstance(max_bindings, int)
            or max_bindings <= 0
        ):
            raise ValueError("W1 spatial-vocal provenance capacity changed")
        if not isinstance(
            relation_owner, W1AnonymousSpatialVocalRelationOwner
        ):
            raise TypeError(
                "W1 spatial-vocal provenance requires relation authority"
            )
        if not isinstance(
            lesson_authority, W1VocalSpatialActionLessonAuthority
        ):
            raise TypeError(
                "W1 spatial-vocal provenance requires cue-action authority"
            )
        self._key = hashlib.sha256(
            _DOMAIN + hashlib.sha256(key).digest()
        ).digest()
        self._tutor_key = tutor_pressure_key
        self._relations = relation_owner
        self._lessons = lesson_authority
        self._physical = physical_authority
        self._emitter = emitter_authority
        self._max_bindings = max_bindings
        self._bindings: dict[
            str, W1AnonymousSpatialVocalProvenance
        ] = {}

    def verify(self, value: W1AnonymousSpatialVocalProvenance) -> None:
        if not isinstance(value, W1AnonymousSpatialVocalProvenance):
            raise TypeError("W1 spatial-vocal provenance is not typed")
        for item, name in (
            (
                value.spatial_vocal_lesson_receipt_sha256,
                "spatial-vocal lesson",
            ),
            (
                value.vocal_spatial_action_lesson_receipt_sha256,
                "vocal-spatial lesson",
            ),
            (value.pressure_authority_receipt_sha256, "pressure authority"),
            (value.pressure_source_file_sha256, "pressure source file"),
            (value.emission_receipt_sha256, "acoustic emission"),
            (value.vocal_execution_receipt_sha256, "vocal execution"),
            (value.vocal_evidence_receipt_sha256, "vocal evidence"),
            (value.authority_hmac_sha256, "provenance HMAC"),
            (value.authority_receipt_sha256, "provenance authority"),
        ):
            _sha256(item, name)
        payload = value.payload()
        signature = hmac.new(
            self._key,
            _DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature, value.authority_hmac_sha256
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("W1 spatial-vocal provenance changed")

    def bind(
        self,
        *,
        spatial_vocal_lesson: W1AnonymousSpatialVocalLesson,
        vocal_spatial_action_lesson: W1VocalSpatialActionLesson,
        pressure: W1TutoredSpeechPressure,
        emission: AuthenticatedW1AcousticEmission,
        vocal_execution: ActionExecutionReceipt,
        vocal_mount: W1PhysicalEvidenceMount,
    ) -> W1AnonymousSpatialVocalProvenance:
        self._relations.verify_lesson(spatial_vocal_lesson)
        self._lessons.verify(vocal_spatial_action_lesson)
        pressure.verify(self._tutor_key)
        self._physical.verify_mount(vocal_mount)
        self._emitter.verify_retained_emission(
            emission,
            observation_snapshot=vocal_execution.after,
            execution_receipt=vocal_execution,
        )
        evidence = vocal_mount.evidence_receipt
        if (
            evidence is None
            or pressure.pcm_s16le != emission.pcm_s16le
            or (
                spatial_vocal_lesson
                .vocal_spatial_action_lesson_receipt_sha256
                != vocal_spatial_action_lesson.authority_receipt_sha256
            )
            or (
                vocal_spatial_action_lesson
                .vocal_execution_receipt_sha256
                != vocal_execution.authority_receipt_sha256
            )
            or (
                vocal_spatial_action_lesson
                .vocal_evidence_receipt_sha256
                != evidence.authority_receipt_sha256
            )
            or evidence.acoustic_emission_receipt_sha256s
            != (emission.receipt.authority_receipt_sha256,)
        ):
            raise ValueError(
                "W1 spatial-vocal pressure source chain changed"
            )
        payload = {
            "emission_receipt_sha256": (
                emission.receipt.authority_receipt_sha256
            ),
            "pressure_authority_receipt_sha256": (
                pressure.authority_receipt_sha256
            ),
            "pressure_source_file_sha256": pressure.source_file_sha256,
            "schema": W1_ANONYMOUS_SPATIAL_VOCAL_PROVENANCE_SCHEMA,
            "spatial_vocal_lesson_receipt_sha256": (
                spatial_vocal_lesson.authority_receipt_sha256
            ),
            "vocal_evidence_receipt_sha256": (
                evidence.authority_receipt_sha256
            ),
            "vocal_execution_receipt_sha256": (
                vocal_execution.authority_receipt_sha256
            ),
            "vocal_spatial_action_lesson_receipt_sha256": (
                vocal_spatial_action_lesson.authority_receipt_sha256
            ),
        }
        signature = hmac.new(
            self._key,
            _DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1AnonymousSpatialVocalProvenance(
            spatial_vocal_lesson_receipt_sha256=(
                payload["spatial_vocal_lesson_receipt_sha256"]
            ),
            vocal_spatial_action_lesson_receipt_sha256=(
                payload[
                    "vocal_spatial_action_lesson_receipt_sha256"
                ]
            ),
            pressure_authority_receipt_sha256=(
                payload["pressure_authority_receipt_sha256"]
            ),
            pressure_source_file_sha256=(
                payload["pressure_source_file_sha256"]
            ),
            emission_receipt_sha256=payload["emission_receipt_sha256"],
            vocal_execution_receipt_sha256=(
                payload["vocal_execution_receipt_sha256"]
            ),
            vocal_evidence_receipt_sha256=(
                payload["vocal_evidence_receipt_sha256"]
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify(result)
        if any(
            item.pressure_source_file_sha256
            == result.pressure_source_file_sha256
            for item in self._bindings.values()
        ):
            raise ValueError("W1 spatial-vocal pressure source is reused")
        if len(self._bindings) >= self._max_bindings:
            raise RuntimeError(
                "W1 spatial-vocal provenance capacity exhausted"
            )
        self._bindings[result.authority_receipt_sha256] = result
        return result


__all__ = [
    "W1AnonymousSpatialVocalProvenance",
    "W1AnonymousSpatialVocalProvenanceAuthority",
]
