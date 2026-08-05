"""Fresh real acoustic blend challenge that releases no spatial action."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_spatial_vocal_provenance import (
    W1AnonymousSpatialVocalProvenance,
    W1AnonymousSpatialVocalProvenanceAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_spatial_vocal_relation import (
    W1AnonymousSpatialVocalDistinction,
    W1AnonymousSpatialVocalLesson,
    W1AnonymousSpatialVocalRelationOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
    W1PhysicalEvidenceMount,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidence,
    W1BinauralGroundingEvidenceAuthority,
)
from dsf_ai_service.substrate.w1_fresh_acoustic_blend import (
    W1FreshAcousticBlend,
    W1FreshAcousticBlendAuthority,
)


W1_FRESH_SPATIAL_VOCAL_BLEND_CHALLENGE_SCHEMA = (
    "guala.w1.fresh_spatial_vocal_blend_challenge.v1"
)
_DOMAIN = b"guala-w1-fresh-spatial-vocal-blend-challenge-v1\0"


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
        raise TypeError("W1 blend challenge key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 blend challenge key boundary changed")
    return result


@dataclass(frozen=True, slots=True)
class W1FreshSpatialVocalBlendChallenge:
    state: str
    reason: str
    distinction_receipt_sha256: str
    blend_receipt_sha256: str
    blend_pcm_sha256: str
    source_pcm_sha256s: tuple[str, str]
    source_file_sha256s: tuple[str, str]
    emission_receipt_sha256: str
    vocal_execution_receipt_sha256: str
    vocal_evidence_receipt_sha256: str
    vocal_grounding_receipt_sha256: str
    resolved_relation_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "blend_pcm_sha256": self.blend_pcm_sha256,
            "blend_receipt_sha256": self.blend_receipt_sha256,
            "distinction_receipt_sha256": self.distinction_receipt_sha256,
            "emission_receipt_sha256": self.emission_receipt_sha256,
            "reason": self.reason,
            "resolved_relation_sha256s": list(
                self.resolved_relation_sha256s
            ),
            "schema": W1_FRESH_SPATIAL_VOCAL_BLEND_CHALLENGE_SCHEMA,
            "source_file_sha256s": list(self.source_file_sha256s),
            "source_pcm_sha256s": list(self.source_pcm_sha256s),
            "state": self.state,
            "vocal_evidence_receipt_sha256": (
                self.vocal_evidence_receipt_sha256
            ),
            "vocal_execution_receipt_sha256": (
                self.vocal_execution_receipt_sha256
            ),
            "vocal_grounding_receipt_sha256": (
                self.vocal_grounding_receipt_sha256
            ),
        }


class W1FreshSpatialVocalBlendChallengeAuthority:
    """Classify one fresh mixed field while remaining motor-inert."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        max_challenges: int,
        world_authority: EmbodimentWorldAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
        emitter_authority: W1AcousticEmitterAuthority,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
        blend_authority: W1FreshAcousticBlendAuthority,
        relation_authority: W1AnonymousSpatialVocalRelationOwner,
        provenance_authority: W1AnonymousSpatialVocalProvenanceAuthority,
    ) -> None:
        if (
            isinstance(max_challenges, bool)
            or not isinstance(max_challenges, int)
            or max_challenges <= 0
        ):
            raise ValueError("W1 blend challenge capacity changed")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._key = hashlib.sha256(_DOMAIN + root).digest()
        self._max = max_challenges
        self._world = world_authority
        self._physical = physical_authority
        self._emitter = emitter_authority
        self._grounding = grounding_authority
        self._blend = blend_authority
        self._relations = relation_authority
        self._provenance = provenance_authority
        self._challenges: dict[
            str, W1FreshSpatialVocalBlendChallenge
        ] = {}
        self._lock = threading.RLock()

    def execute(
        self,
        *,
        distinction: W1AnonymousSpatialVocalDistinction,
        training_lessons: tuple[W1AnonymousSpatialVocalLesson, ...],
        training_provenances: tuple[
            W1AnonymousSpatialVocalProvenance, ...
        ],
        blend: W1FreshAcousticBlend,
        emission: AuthenticatedW1AcousticEmission,
        vocal_execution: ActionExecutionReceipt,
        vocal_mount: W1PhysicalEvidenceMount,
        vocal_grounding: W1BinauralGroundingEvidence,
    ) -> W1FreshSpatialVocalBlendChallenge:
        self._relations.verify_distinction(distinction)
        self._blend.verify(blend)
        for lesson in training_lessons:
            self._relations.verify_lesson(lesson)
        for provenance in training_provenances:
            self._provenance.verify(provenance)
        lesson_receipts = {
            value.authority_receipt_sha256 for value in training_lessons
        }
        provenance_lessons = {
            value.spatial_vocal_lesson_receipt_sha256
            for value in training_provenances
        }
        training_source_files = {
            value.pressure_source_file_sha256
            for value in training_provenances
        }
        if (
            lesson_receipts
            != set(distinction.source_lesson_receipt_sha256s)
            or provenance_lessons != lesson_receipts
            or training_source_files.intersection(
                blend.source_file_sha256s
            )
        ):
            raise ValueError(
                "W1 blend challenge training provenance changed"
            )
        self._world.verify_execution_receipt(vocal_execution)
        self._physical.verify_mount(vocal_mount)
        self._emitter.verify_emission(
            emission,
            observation_snapshot=vocal_execution.after,
            execution_receipt=vocal_execution,
        )
        self._grounding.verify(vocal_grounding)
        evidence = vocal_mount.evidence_receipt
        if (
            vocal_mount.state is not W1EvidenceState.OBSERVED
            or evidence is None
            or emission.pcm_s16le != blend.pcm_s16le
            or evidence.world_execution_receipt_sha256
            != vocal_execution.authority_receipt_sha256
            or evidence.acoustic_emission_receipt_sha256s
            != (emission.receipt.authority_receipt_sha256,)
            or vocal_grounding.causal_settlement_receipt_sha256
            != vocal_mount.causal_settlement.authority_receipt_sha256
            or vocal_grounding.receptor_settlement_receipt_sha256
            != (
                vocal_mount.binaural_receptor_settlement
                .authority_receipt_sha256
            )
            or self._world.observation_snapshot() != vocal_execution.after
            or vocal_execution.actor_body_id
            == vocal_execution.after.self_body_id
        ):
            raise ValueError(
                "W1 blend challenge physical source chain changed"
            )
        resolved = self._relations.resolve(
            distinction, vocal_grounding.activations
        )
        state = (
            "unknown"
            if not resolved
            else "ambiguous"
            if len(resolved) > 1
            else "unexpected_unique"
        )
        reason = {
            "unknown": "no_exact_spatial_relation",
            "ambiguous": "multiple_exact_spatial_relations",
            "unexpected_unique": "one_exact_spatial_relation",
        }[state]
        relation_ids = tuple(sorted(
            _digest(value.record()) for value in resolved
        ))
        provisional = W1FreshSpatialVocalBlendChallenge(
            state=state,
            reason=reason,
            distinction_receipt_sha256=(
                distinction.authority_receipt_sha256
            ),
            blend_receipt_sha256=blend.authority_receipt_sha256,
            blend_pcm_sha256=blend.blend_pcm_sha256,
            source_pcm_sha256s=blend.source_pcm_sha256s,
            source_file_sha256s=blend.source_file_sha256s,
            emission_receipt_sha256=(
                emission.receipt.authority_receipt_sha256
            ),
            vocal_execution_receipt_sha256=(
                vocal_execution.authority_receipt_sha256
            ),
            vocal_evidence_receipt_sha256=(
                evidence.authority_receipt_sha256
            ),
            vocal_grounding_receipt_sha256=(
                vocal_grounding.authority_receipt_sha256
            ),
            resolved_relation_sha256s=relation_ids,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._key,
            _DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1FreshSpatialVocalBlendChallenge(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name not in {
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        with self._lock:
            if len(self._challenges) >= self._max:
                raise RuntimeError(
                    "W1 blend challenge capacity exhausted"
                )
            self._challenges[result.authority_receipt_sha256] = result
        return result


__all__ = [
    "W1FreshSpatialVocalBlendChallenge",
    "W1FreshSpatialVocalBlendChallengeAuthority",
]
