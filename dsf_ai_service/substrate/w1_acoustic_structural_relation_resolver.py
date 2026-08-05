"""Bounded acoustic-cue to full W1 structural-relation learning.

This authority replaces the former challenge binder that accepted one
arbitrarily selected root and could bind a prompt cue as its own response.
One admitted lesson instead has two independently authenticated sides:

* one exact binaural recurrent-q acoustic episode, retaining every
  D/M/R/U/C/P/B occurrence behind every active neuron; and
* one complete, authority-owned :class:`W1GroundedStructuralRelationProof`.

The cue and relation must share a verified causal junction.  For referent and
action relations that junction is already present in both upstream receipts.
Emitter continuity uses one verified W1 audiovisual mount to prove that the
cue settlement carries an emission retained by the relation proof.

At least two source-disjoint lessons per relation are contrasted with every
other relation and with independently observed background acoustics.  A
learned feature is an exact recurrent-q neuron present in every positive
lesson and absent from every relation/background contrast.  Each such
causally diagnostic neuron is a sufficient exact witness; there is no count
or score.  Zero matched relations is ``unknown``, one is ``resolved``, and
more than one is ``ambiguous``.  Unknown and ambiguous results authorize no
action and mutate nothing.  A resolved response is the complete set of
retained typed relation proofs, not a copy of the acoustic prompt.

No transcript, word label, score, threshold, rank, probability, reduced DSF
vector, or scripted response participates.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
    W1PhysicalEvidenceMount,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralActivationEvidence,
    W1BinauralGroundingEvidence,
    W1BinauralGroundingEvidenceAuthority,
)
from dsf_ai_service.substrate.w1_grounded_structural_relations import (
    W1GroundedStructuralRelationKind,
    W1GroundedStructuralRelationOwner,
    W1GroundedStructuralRelationProof,
)


ACOUSTIC_RELATION_PROFILE_SCHEMA = (
    "guala.w1.acoustic_structural_relation.profile.v1"
)
ACOUSTIC_RELATION_LESSON_SCHEMA = (
    "guala.w1.acoustic_structural_relation.lesson.v1"
)
ACOUSTIC_RELATION_DISTINCTION_SCHEMA = (
    "guala.w1.acoustic_structural_relation.distinction.v1"
)
ACOUSTIC_RELATION_STATE_SCHEMA = (
    "guala.w1.acoustic_structural_relation.state.v1"
)
ACOUSTIC_RELATION_ENVELOPE_SCHEMA = (
    "guala.w1.acoustic_structural_relation.state_hmac.v1"
)
ACOUSTIC_RELATION_RESOLUTION_SCHEMA = (
    "guala.w1.acoustic_structural_relation.resolution.v1"
)
_LESSON_DOMAIN = b"guala-w1-acoustic-structural-relation-lesson-v1\0"
_DISTINCTION_DOMAIN = (
    b"guala-w1-acoustic-structural-relation-distinction-v1\0"
)
_STATE_DOMAIN = b"guala-w1-acoustic-structural-relation-state-v1\0"
_RESOLUTION_DOMAIN = (
    b"guala-w1-acoustic-structural-relation-resolution-v1\0"
)
_HEX = frozenset("0123456789abcdef")
_REQUIRED_INDEPENDENT_LESSONS = 2


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
        raise TypeError("acoustic structural relation key is not typed")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("acoustic structural relation key boundary changed")
    return result


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _activation_key(
    value: W1BinauralActivationEvidence,
) -> tuple[str, str]:
    value.verify()
    return value.ear_id, value.neuron_id


def _relation_structure_id(
    proof: W1GroundedStructuralRelationProof,
) -> str:
    """Exact nuisance-free identity of one typed physical relation."""

    proof_roots = [
        [value.root_id, value.value_sha256]
        for value in proof.root_witnesses
    ]
    if proof.relation is (
        W1GroundedStructuralRelationKind.REFERENT_CONTINUITY
    ):
        structure = {
            "relation": proof.relation.value,
            "root": proof_roots[0],
        }
    elif proof.relation is (
        W1GroundedStructuralRelationKind.EMITTER_BODY_CONTINUITY
    ):
        structure = {
            "anonymous_body_continuity_sha256": (
                proof.anonymous_body_continuity_sha256
            ),
            "poses": [value.as_record() for value in proof.poses],
            "relation": proof.relation.value,
        }
    else:
        structure = {
            "full_dynamic_roots": proof_roots,
            "poses": [value.as_record() for value in proof.poses],
            "relation": proof.relation.value,
            "revision_deltas": [
                right - left
                for left, right in zip(
                    proof.revisions,
                    proof.revisions[1:],
                )
            ],
            "signed_displacement": list(proof.signed_displacement),
        }
    return _digest({
        "schema": "guala.w1.grounded_relation_structure.v1",
        "structure": structure,
    })


def _evidence_record(
    value: W1BinauralGroundingEvidence,
) -> dict[str, object]:
    return {
        **value.payload(),
        "authority_hmac_sha256": value.authority_hmac_sha256,
        "authority_receipt_sha256": value.authority_receipt_sha256,
        "episode_id": value.episode_id,
    }


def _root(raw: object) -> GroundingRoot:
    if not isinstance(raw, Mapping) or set(raw) != {
        "root_id",
        "value_json",
        "value_sha256",
    }:
        raise ValueError("acoustic relation grounding root changed")
    result = GroundingRoot(
        root_id=raw.get("root_id"),
        value_sha256=raw.get("value_sha256"),
        value_json=raw.get("value_json"),
    )
    result.verify()
    return result


def _activation(raw: object) -> W1BinauralActivationEvidence:
    if not isinstance(raw, Mapping) or set(raw) != {
        "activation_json",
        "authority_receipt_sha256",
        "ear_id",
        "neuron_id",
    }:
        raise ValueError("acoustic relation activation changed")
    result = W1BinauralActivationEvidence(
        ear_id=raw.get("ear_id"),
        neuron_id=raw.get("neuron_id"),
        activation_json=raw.get("activation_json"),
        authority_receipt_sha256=raw.get(
            "authority_receipt_sha256"
        ),
    )
    result.verify()
    return result


def _evidence(raw: object) -> W1BinauralGroundingEvidence:
    expected = {
        "activations",
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "binaural_firing_receipt_sha256",
        "causal_settlement_receipt_sha256",
        "episode_id",
        "receptor_settlement_receipt_sha256",
        "roots",
        "schema",
    }
    if (
        not isinstance(raw, Mapping)
        or set(raw) != expected
        or not isinstance(raw.get("activations"), list)
        or not isinstance(raw.get("roots"), list)
    ):
        raise ValueError("acoustic relation evidence record changed")
    return W1BinauralGroundingEvidence(
        episode_id=raw.get("episode_id"),
        causal_settlement_receipt_sha256=raw.get(
            "causal_settlement_receipt_sha256"
        ),
        receptor_settlement_receipt_sha256=raw.get(
            "receptor_settlement_receipt_sha256"
        ),
        binaural_firing_receipt_sha256=raw.get(
            "binaural_firing_receipt_sha256"
        ),
        activations=tuple(
            _activation(value) for value in raw["activations"]
        ),
        roots=tuple(_root(value) for value in raw["roots"]),
        authority_hmac_sha256=raw.get("authority_hmac_sha256"),
        authority_receipt_sha256=raw.get(
            "authority_receipt_sha256"
        ),
    )


@dataclass(frozen=True, slots=True)
class W1AcousticStructuralRelationResourceProfile:
    profile_id: str
    max_lessons: int
    max_distinctions: int
    max_lessons_per_distinction: int
    max_background_evidences_per_distinction: int
    max_features_per_relation: int
    max_activations_per_lesson: int
    max_lesson_bytes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_lessons: int,
        max_distinctions: int,
        max_lessons_per_distinction: int,
        max_background_evidences_per_distinction: int,
        max_features_per_relation: int,
        max_activations_per_lesson: int,
        max_lesson_bytes: int,
        max_state_bytes: int,
    ) -> "W1AcousticStructuralRelationResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
            or len(profile_id.encode("utf-8")) > 512
        ):
            raise ValueError(
                "acoustic structural relation profile changed"
            )
        provisional = cls(
            profile_id=profile_id,
            max_lessons=_positive(
                max_lessons, "acoustic relation lesson capacity"
            ),
            max_distinctions=_positive(
                max_distinctions, "acoustic relation distinction capacity"
            ),
            max_lessons_per_distinction=_positive(
                max_lessons_per_distinction,
                "acoustic relation lessons per distinction",
            ),
            max_background_evidences_per_distinction=_positive(
                max_background_evidences_per_distinction,
                "acoustic relation background evidence capacity",
            ),
            max_features_per_relation=_positive(
                max_features_per_relation,
                "acoustic relation feature capacity",
            ),
            max_activations_per_lesson=_positive(
                max_activations_per_lesson,
                "acoustic relation activation capacity",
            ),
            max_lesson_bytes=_positive(
                max_lesson_bytes, "acoustic relation lesson bytes"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "acoustic relation state bytes"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name != "authority_receipt_sha256"
            },
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_activations_per_lesson": (
                self.max_activations_per_lesson
            ),
            "max_distinctions": self.max_distinctions,
            "max_background_evidences_per_distinction": (
                self.max_background_evidences_per_distinction
            ),
            "max_features_per_relation": (
                self.max_features_per_relation
            ),
            "max_lesson_bytes": self.max_lesson_bytes,
            "max_lessons": self.max_lessons,
            "max_lessons_per_distinction": (
                self.max_lessons_per_distinction
            ),
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": ACOUSTIC_RELATION_PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        for value, name in (
            (self.max_lessons, "acoustic relation lesson capacity"),
            (
                self.max_distinctions,
                "acoustic relation distinction capacity",
            ),
            (
                self.max_lessons_per_distinction,
                "acoustic relation lessons per distinction",
            ),
            (
                self.max_background_evidences_per_distinction,
                "acoustic relation background evidence capacity",
            ),
            (
                self.max_features_per_relation,
                "acoustic relation feature capacity",
            ),
            (
                self.max_activations_per_lesson,
                "acoustic relation activation capacity",
            ),
            (self.max_lesson_bytes, "acoustic relation lesson bytes"),
            (self.max_state_bytes, "acoustic relation state bytes"),
        ):
            _positive(value, name)
        if (
            self.max_lessons_per_distinction > self.max_lessons
            or self.authority_receipt_sha256 != _digest(self.payload())
        ):
            raise ValueError(
                "acoustic structural relation profile authority changed"
            )


@dataclass(frozen=True, slots=True)
class W1AcousticStructuralRelationLesson:
    lesson_id: str
    relation_proof: W1GroundedStructuralRelationProof
    cue_evidence: W1BinauralGroundingEvidence
    causal_junction_receipt_sha256s: tuple[str, ...]
    source_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def relation(self) -> W1GroundedStructuralRelationKind:
        return self.relation_proof.relation

    def payload(self) -> dict[str, object]:
        return {
            "causal_junction_receipt_sha256s": list(
                self.causal_junction_receipt_sha256s
            ),
            "cue_evidence": _evidence_record(self.cue_evidence),
            "relation_proof": self.relation_proof.record(),
            "schema": ACOUSTIC_RELATION_LESSON_SCHEMA,
            "source_receipt_sha256s": list(
                self.source_receipt_sha256s
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "lesson_id": self.lesson_id,
        }


@dataclass(frozen=True, slots=True)
class W1AcousticRelationFeature:
    ear_id: str
    neuron_id: str
    positive_activation_receipt_sha256s: tuple[
        tuple[str, ...], ...
    ]

    @property
    def key(self) -> tuple[str, str]:
        return self.ear_id, self.neuron_id

    def record(self) -> dict[str, object]:
        return {
            "ear_id": self.ear_id,
            "neuron_id": self.neuron_id,
            "positive_activation_receipt_sha256s": [
                list(value)
                for value in self.positive_activation_receipt_sha256s
            ],
        }


@dataclass(frozen=True, slots=True)
class W1AcousticStructuralPattern:
    relation: W1GroundedStructuralRelationKind
    relation_structure_id: str
    features: tuple[W1AcousticRelationFeature, ...]
    positive_lesson_receipt_sha256s: tuple[str, ...]
    contrast_lesson_receipt_sha256s: tuple[str, ...]

    def record(self) -> dict[str, object]:
        return {
            "contrast_lesson_receipt_sha256s": list(
                self.contrast_lesson_receipt_sha256s
            ),
            "features": [value.record() for value in self.features],
            "positive_lesson_receipt_sha256s": list(
                self.positive_lesson_receipt_sha256s
            ),
            "relation": self.relation.value,
            "relation_structure_id": self.relation_structure_id,
        }


@dataclass(frozen=True, slots=True)
class W1AcousticStructuralDistinction:
    distinction_id: str
    patterns: tuple[W1AcousticStructuralPattern, ...]
    background_evidences: tuple[W1BinauralGroundingEvidence, ...]
    source_lesson_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "background_evidences": [
                _evidence_record(value)
                for value in self.background_evidences
            ],
            "patterns": [value.record() for value in self.patterns],
            "schema": ACOUSTIC_RELATION_DISTINCTION_SCHEMA,
            "source_lesson_receipt_sha256s": list(
                self.source_lesson_receipt_sha256s
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "distinction_id": self.distinction_id,
        }


class W1AcousticStructuralResolutionState(str, Enum):
    UNKNOWN = "unknown"
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class W1ResolvedGroundedStructuralRelation:
    relation: W1GroundedStructuralRelationKind
    relation_structure_id: str
    positive_relation_proofs: tuple[
        W1GroundedStructuralRelationProof, ...
    ]
    matched_challenge_activations: tuple[
        W1BinauralActivationEvidence, ...
    ]

    def record(self) -> dict[str, object]:
        return {
            "matched_challenge_activations": [
                value.record()
                for value in self.matched_challenge_activations
            ],
            "positive_relation_proofs": [
                value.record() for value in self.positive_relation_proofs
            ],
            "relation": self.relation.value,
            "relation_structure_id": self.relation_structure_id,
        }


@dataclass(frozen=True, slots=True)
class W1AcousticStructuralResolution:
    state: W1AcousticStructuralResolutionState
    reason: str
    challenge_evidence_receipt_sha256: str
    matches: tuple[W1ResolvedGroundedStructuralRelation, ...]
    relation_release_authorized: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "relation_release_authorized": (
                self.relation_release_authorized
            ),
            "challenge_evidence_receipt_sha256": (
                self.challenge_evidence_receipt_sha256
            ),
            "matches": [value.record() for value in self.matches],
            "reason": self.reason,
            "schema": ACOUSTIC_RELATION_RESOLUTION_SCHEMA,
            "state": self.state.value,
        }


class W1AcousticStructuralRelationOwner:
    """Live-owned, bounded exact relation lesson and resolver authority."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1AcousticStructuralRelationResourceProfile,
        relation_owner: W1GroundedStructuralRelationOwner,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
        motif_owner: AuditoryRecurrentMotifOwner,
    ) -> None:
        resource_profile.verify()
        if not isinstance(
            relation_owner, W1GroundedStructuralRelationOwner
        ):
            raise TypeError("acoustic resolver requires relation authority")
        if not isinstance(
            grounding_authority, W1BinauralGroundingEvidenceAuthority
        ):
            raise TypeError("acoustic resolver requires grounding authority")
        if not isinstance(motif_owner, AuditoryRecurrentMotifOwner):
            raise TypeError("acoustic resolver requires recurrent-q authority")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._lesson_key = hashlib.sha256(
            _LESSON_DOMAIN + root
        ).digest()
        self._distinction_key = hashlib.sha256(
            _DISTINCTION_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + root
        ).digest()
        self._resolution_key = hashlib.sha256(
            _RESOLUTION_DOMAIN + root
        ).digest()
        self._profile = resource_profile
        self._relations = relation_owner
        self._grounding = grounding_authority
        self._motifs = motif_owner
        self._lessons: dict[
            str, W1AcousticStructuralRelationLesson
        ] = {}
        self._distinctions: dict[
            str, W1AcousticStructuralDistinction
        ] = {}
        self._lock = threading.RLock()

    @property
    def lessons(
        self,
    ) -> tuple[W1AcousticStructuralRelationLesson, ...]:
        with self._lock:
            return tuple(
                self._lessons[key] for key in sorted(self._lessons)
            )

    @property
    def distinctions(
        self,
    ) -> tuple[W1AcousticStructuralDistinction, ...]:
        with self._lock:
            return tuple(
                self._distinctions[key]
                for key in sorted(self._distinctions)
            )

    def _owned_proof(
        self, receipt: str
    ) -> W1GroundedStructuralRelationProof:
        matches = tuple(
            value
            for value in self._relations.proofs
            if value.authority_receipt_sha256 == receipt
        )
        if len(matches) != 1:
            raise ValueError(
                "acoustic relation lost full relation authority"
            )
        return matches[0]

    def _verify_activation_field(
        self,
        values: tuple[W1BinauralActivationEvidence, ...],
    ) -> None:
        if (
            not values
            or len(values) > self._profile.max_activations_per_lesson
            or len({
                value.authority_receipt_sha256 for value in values
            }) != len(values)
        ):
            raise ValueError("acoustic relation activation field changed")
        neurons = {
            value.neuron_id: value
            for value in self._motifs.motif_neurons
        }
        for activation in values:
            activation.verify()
            neuron = neurons.get(activation.neuron_id)
            if (
                neuron is None
                or neuron.lane.ear_id != activation.ear_id
            ):
                raise ValueError(
                    "acoustic relation activation lost its q neuron"
                )
            neuron.verify()

    def verify_lesson(
        self, lesson: W1AcousticStructuralRelationLesson
    ) -> None:
        for value, name in (
            (lesson.lesson_id, "acoustic relation lesson"),
            (
                lesson.authority_hmac_sha256,
                "acoustic relation lesson HMAC",
            ),
            (
                lesson.authority_receipt_sha256,
                "acoustic relation lesson authority",
            ),
            *(
                (value, "acoustic relation causal junction")
                for value in lesson.causal_junction_receipt_sha256s
            ),
            *(
                (value, "acoustic relation physical source")
                for value in lesson.source_receipt_sha256s
            ),
        ):
            _sha256(value, name)
        proof = self._owned_proof(
            lesson.relation_proof.authority_receipt_sha256
        )
        self._relations.verify(proof)
        self._grounding.verify(lesson.cue_evidence)
        self._verify_activation_field(lesson.cue_evidence.activations)
        cue_sources = {
            lesson.cue_evidence.authority_receipt_sha256,
            lesson.cue_evidence.binaural_firing_receipt_sha256,
            lesson.cue_evidence.causal_settlement_receipt_sha256,
            lesson.cue_evidence.receptor_settlement_receipt_sha256,
        }
        expected_sources = tuple(sorted({
            *proof.source_receipt_sha256s,
            *proof.upstream_authority_receipt_sha256s,
            *cue_sources,
            *lesson.causal_junction_receipt_sha256s,
        }))
        if (
            proof != lesson.relation_proof
            or not lesson.causal_junction_receipt_sha256s
            or lesson.causal_junction_receipt_sha256s
            != tuple(sorted(set(
                lesson.causal_junction_receipt_sha256s
            )))
            or lesson.source_receipt_sha256s != expected_sources
            or len(_canonical(lesson.payload()))
            > self._profile.max_lesson_bytes
        ):
            raise ValueError("acoustic relation lesson changed")
        payload = lesson.payload()
        signature = hmac.new(
            self._lesson_key,
            _LESSON_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            lesson.lesson_id != _digest(payload)
            or not hmac.compare_digest(
                signature, lesson.authority_hmac_sha256
            )
            or lesson.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("acoustic relation lesson authority changed")

    def _admit(
        self,
        *,
        relation_proof: W1GroundedStructuralRelationProof,
        cue_evidence: W1BinauralGroundingEvidence,
        causal_junction_receipts: tuple[str, ...],
    ) -> W1AcousticStructuralRelationLesson:
        owned = self._owned_proof(
            relation_proof.authority_receipt_sha256
        )
        self._relations.verify(relation_proof)
        self._grounding.verify(cue_evidence)
        if owned != relation_proof:
            raise ValueError(
                "acoustic relation proof is not authority-owned"
            )
        junctions = tuple(sorted(set(causal_junction_receipts)))
        if len(junctions) != len(causal_junction_receipts):
            raise ValueError("acoustic relation junction repeated")
        sources = tuple(sorted({
            *relation_proof.source_receipt_sha256s,
            *relation_proof.upstream_authority_receipt_sha256s,
            cue_evidence.authority_receipt_sha256,
            cue_evidence.binaural_firing_receipt_sha256,
            cue_evidence.causal_settlement_receipt_sha256,
            cue_evidence.receptor_settlement_receipt_sha256,
            *junctions,
        }))
        provisional = W1AcousticStructuralRelationLesson(
            lesson_id="0" * 64,
            relation_proof=relation_proof,
            cue_evidence=cue_evidence,
            causal_junction_receipt_sha256s=junctions,
            source_receipt_sha256s=sources,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._lesson_key,
            _LESSON_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1AcousticStructuralRelationLesson(
            lesson_id=_digest(payload),
            relation_proof=relation_proof,
            cue_evidence=cue_evidence,
            causal_junction_receipt_sha256s=junctions,
            source_receipt_sha256s=sources,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify_lesson(result)
        with self._lock:
            if result.lesson_id in self._lessons:
                return result
            if any(
                set(value.source_receipt_sha256s).intersection(
                    result.source_receipt_sha256s
                )
                for value in self._lessons.values()
            ):
                raise ValueError(
                    "acoustic relation lessons reuse a physical source"
                )
            if len(self._lessons) >= self._profile.max_lessons:
                raise RuntimeError(
                    "acoustic relation lesson capacity exhausted"
                )
            staged = dict(self._lessons)
            staged[result.lesson_id] = result
            self._encoded(staged, self._distinctions)
            self._lessons = staged
        return result

    def admit_causally_joined(
        self,
        *,
        relation_proof: W1GroundedStructuralRelationProof,
        cue_evidence: W1BinauralGroundingEvidence,
    ) -> W1AcousticStructuralRelationLesson:
        """Admit a cue whose authenticated receipt is already in the proof."""

        cue_receipts = {
            cue_evidence.authority_receipt_sha256,
            cue_evidence.binaural_firing_receipt_sha256,
            cue_evidence.causal_settlement_receipt_sha256,
            cue_evidence.receptor_settlement_receipt_sha256,
        }
        junctions = tuple(sorted(
            cue_receipts.intersection({
                *relation_proof.source_receipt_sha256s,
                *relation_proof.upstream_authority_receipt_sha256s,
            })
        ))
        if (
            relation_proof.relation
            is W1GroundedStructuralRelationKind.EMITTER_BODY_CONTINUITY
            or not junctions
        ):
            raise ValueError(
                "acoustic cue and structural relation lack a causal junction"
            )
        return self._admit(
            relation_proof=relation_proof,
            cue_evidence=cue_evidence,
            causal_junction_receipts=junctions,
        )

    def admit_emitter_joined(
        self,
        *,
        relation_proof: W1GroundedStructuralRelationProof,
        cue_evidence: W1BinauralGroundingEvidence,
        cue_mount: W1PhysicalEvidenceMount,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
    ) -> W1AcousticStructuralRelationLesson:
        """Bridge one verified acoustic mount into emitter continuity."""

        if (
            relation_proof.relation
            is not W1GroundedStructuralRelationKind.EMITTER_BODY_CONTINUITY
            or not isinstance(
                physical_authority,
                W1AudiovisualPhysicalEvidenceAuthority,
            )
        ):
            raise ValueError(
                "emitter acoustic lesson requires emitter relation authority"
            )
        physical_authority.verify_mount(cue_mount)
        evidence = cue_mount.evidence_receipt
        settlement = cue_mount.causal_settlement
        if (
            cue_mount.state is not W1EvidenceState.OBSERVED
            or evidence is None
            or settlement is None
            or evidence.causal_settlement_receipt_sha256
            != cue_evidence.causal_settlement_receipt_sha256
            or not set(
                evidence.acoustic_emission_receipt_sha256s
            ).intersection(relation_proof.source_receipt_sha256s)
        ):
            raise ValueError(
                "emitter acoustic cue lost its physical emission junction"
            )
        junctions = tuple(sorted({
            evidence.authority_receipt_sha256,
            evidence.causal_settlement_receipt_sha256,
            *evidence.acoustic_emission_receipt_sha256s,
        }))
        return self._admit(
            relation_proof=relation_proof,
            cue_evidence=cue_evidence,
            causal_junction_receipts=junctions,
        )

    def _verify_feature(
        self, feature: W1AcousticRelationFeature
    ) -> None:
        if (
            feature.ear_id not in {"left", "right"}
            or len(
                feature.positive_activation_receipt_sha256s
            ) < _REQUIRED_INDEPENDENT_LESSONS
        ):
            raise ValueError("acoustic relation feature changed")
        _sha256(feature.neuron_id, "acoustic relation q neuron")
        neurons = {
            value.neuron_id: value
            for value in self._motifs.motif_neurons
        }
        neuron = neurons.get(feature.neuron_id)
        if neuron is None or neuron.lane.ear_id != feature.ear_id:
            raise ValueError("acoustic relation q neuron is not retained")
        neuron.verify()
        for receipts in feature.positive_activation_receipt_sha256s:
            if (
                not receipts
                or receipts != tuple(sorted(set(receipts)))
            ):
                raise ValueError(
                    "acoustic relation feature witnesses changed"
                )
            for receipt in receipts:
                _sha256(receipt, "acoustic relation feature witness")

    def verify_distinction(
        self, distinction: W1AcousticStructuralDistinction
    ) -> None:
        for value in (
            distinction.distinction_id,
            distinction.authority_hmac_sha256,
            distinction.authority_receipt_sha256,
            *distinction.source_lesson_receipt_sha256s,
        ):
            _sha256(value, "acoustic relation distinction authority")
        retained = {
            value.authority_receipt_sha256: value
            for value in self._lessons.values()
        }
        if (
            len(distinction.background_evidences)
            < _REQUIRED_INDEPENDENT_LESSONS
            or len(distinction.background_evidences)
            > self._profile.max_background_evidences_per_distinction
        ):
            raise ValueError(
                "acoustic relation background evidence boundary changed"
            )
        background_sources: set[str] = set()
        for evidence in distinction.background_evidences:
            self._grounding.verify(evidence)
            self._verify_activation_field(evidence.activations)
            sources = {
                evidence.authority_receipt_sha256,
                evidence.binaural_firing_receipt_sha256,
                evidence.causal_settlement_receipt_sha256,
                evidence.receptor_settlement_receipt_sha256,
            }
            if background_sources.intersection(sources):
                raise ValueError(
                    "acoustic relation background sources repeat"
                )
            background_sources.update(sources)
        used_lessons: set[str] = set()
        used_features: set[tuple[str, str]] = set()
        relation_structures: set[str] = set()
        if not distinction.patterns:
            raise ValueError("acoustic relation distinction has no patterns")
        for pattern in distinction.patterns:
            if (
                pattern.relation_structure_id in relation_structures
                or len(pattern.positive_lesson_receipt_sha256s)
                < _REQUIRED_INDEPENDENT_LESSONS
                or not pattern.contrast_lesson_receipt_sha256s
                or not pattern.features
                or len(pattern.features)
                > self._profile.max_features_per_relation
                or set(
                    pattern.positive_lesson_receipt_sha256s
                ).intersection(
                    pattern.contrast_lesson_receipt_sha256s
                )
            ):
                raise ValueError("acoustic structural pattern changed")
            _sha256(
                pattern.relation_structure_id,
                "acoustic relation structure",
            )
            try:
                positives = tuple(
                    retained[value]
                    for value
                    in pattern.positive_lesson_receipt_sha256s
                )
                contrasts = tuple(
                    retained[value]
                    for value
                    in pattern.contrast_lesson_receipt_sha256s
                )
            except KeyError as error:
                raise ValueError(
                    "acoustic relation distinction lost a lesson"
                ) from error
            if any(
                value.relation is not pattern.relation
                or _relation_structure_id(value.relation_proof)
                != pattern.relation_structure_id
                for value in positives
            ) or any(
                _relation_structure_id(value.relation_proof)
                == pattern.relation_structure_id
                for value in contrasts
            ):
                raise ValueError(
                    "acoustic relation lesson grouping changed"
                )
            positive_keys = tuple(
                {
                    _activation_key(value)
                    for value in lesson.cue_evidence.activations
                }
                for lesson in positives
            )
            contrast_keys = {
                _activation_key(value)
                for lesson in contrasts
                for value in lesson.cue_evidence.activations
            }
            contrast_keys.update(
                _activation_key(value)
                for evidence in distinction.background_evidences
                for value in evidence.activations
            )
            expected_feature_keys = set.intersection(
                *positive_keys
            ) - contrast_keys
            if {
                value.key for value in pattern.features
            } != expected_feature_keys:
                raise ValueError(
                    "acoustic relation exact contrast changed"
                )
            for feature in pattern.features:
                self._verify_feature(feature)
                if feature.key in used_features:
                    raise ValueError(
                        "acoustic relation feature reused across patterns"
                    )
                expected_witnesses = tuple(
                    tuple(sorted(
                        activation.authority_receipt_sha256
                        for activation
                        in lesson.cue_evidence.activations
                        if _activation_key(activation) == feature.key
                    ))
                    for lesson in positives
                )
                if (
                    feature.positive_activation_receipt_sha256s
                    != expected_witnesses
                ):
                    raise ValueError(
                        "acoustic relation feature witness changed"
                    )
                used_features.add(feature.key)
            relation_structures.add(pattern.relation_structure_id)
            used_lessons.update(
                pattern.positive_lesson_receipt_sha256s
            )
            used_lessons.update(
                pattern.contrast_lesson_receipt_sha256s
            )
        if used_lessons != set(
            distinction.source_lesson_receipt_sha256s
        ):
            raise ValueError("acoustic relation distinction lost sources")
        lesson_sources = {
            source
            for receipt in distinction.source_lesson_receipt_sha256s
            for lesson in self._lessons.values()
            if lesson.authority_receipt_sha256 == receipt
            for source in lesson.source_receipt_sha256s
        }
        if lesson_sources.intersection(background_sources):
            raise ValueError(
                "acoustic relation background reuses a lesson source"
            )
        payload = distinction.payload()
        signature = hmac.new(
            self._distinction_key,
            _DISTINCTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            distinction.distinction_id != _digest(payload)
            or not hmac.compare_digest(
                signature, distinction.authority_hmac_sha256
            )
            or distinction.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError(
                "acoustic relation distinction authority changed"
            )

    def learn(
        self,
        lessons: tuple[W1AcousticStructuralRelationLesson, ...],
        *,
        background_evidences: tuple[
            W1BinauralGroundingEvidence, ...
        ],
    ) -> W1AcousticStructuralDistinction:
        if (
            not isinstance(lessons, tuple)
            or not lessons
            or len(lessons)
            > self._profile.max_lessons_per_distinction
        ):
            raise ValueError(
                "acoustic relation distinction lesson boundary changed"
            )
        if (
            not isinstance(background_evidences, tuple)
            or len(background_evidences)
            < _REQUIRED_INDEPENDENT_LESSONS
            or len(background_evidences)
            > self._profile.max_background_evidences_per_distinction
        ):
            raise ValueError(
                "acoustic relation background evidence boundary changed"
            )
        for lesson in lessons:
            self.verify_lesson(lesson)
        background_sources: set[str] = set()
        for evidence in background_evidences:
            self._grounding.verify(evidence)
            self._verify_activation_field(evidence.activations)
            sources = {
                evidence.authority_receipt_sha256,
                evidence.binaural_firing_receipt_sha256,
                evidence.causal_settlement_receipt_sha256,
                evidence.receptor_settlement_receipt_sha256,
            }
            if background_sources.intersection(sources):
                raise ValueError(
                    "acoustic relation background sources repeat"
                )
            background_sources.update(sources)
        lesson_sources = {
            source for lesson in lessons
            for source in lesson.source_receipt_sha256s
        }
        if lesson_sources.intersection(background_sources):
            raise ValueError(
                "acoustic relation background reuses a lesson source"
            )
        receipts = tuple(sorted(
            value.authority_receipt_sha256 for value in lessons
        ))
        if len(receipts) != len(set(receipts)):
            raise ValueError(
                "acoustic relation distinction repeats a lesson"
            )
        groups: dict[
            tuple[W1GroundedStructuralRelationKind, str],
            list[W1AcousticStructuralRelationLesson],
        ] = {}
        for lesson in lessons:
            groups.setdefault((
                lesson.relation,
                _relation_structure_id(lesson.relation_proof),
            ), []).append(lesson)
        if (
            len(groups) < 2
            or any(
                len(values) < _REQUIRED_INDEPENDENT_LESSONS
                for values in groups.values()
            )
        ):
            raise ValueError(
                "acoustic relation distinction needs two independent "
                "lessons per contrasted relation"
            )
        patterns = []
        for relation_key in sorted(
            groups,
            key=lambda value: (value[0].value, value[1]),
        ):
            relation, relation_structure_id = relation_key
            positives = tuple(sorted(
                groups[relation_key],
                key=lambda value: value.authority_receipt_sha256,
            ))
            contrasts = tuple(sorted((
                lesson
                for other, group in groups.items()
                if other != relation_key
                for lesson in group
            ), key=lambda value: value.authority_receipt_sha256))
            positive_keys = tuple(
                {
                    _activation_key(value)
                    for value in lesson.cue_evidence.activations
                }
                for lesson in positives
            )
            contrast_keys = {
                _activation_key(value)
                for lesson in contrasts
                for value in lesson.cue_evidence.activations
            }
            contrast_keys.update(
                _activation_key(value)
                for evidence in background_evidences
                for value in evidence.activations
            )
            feature_keys = tuple(sorted(
                set.intersection(*positive_keys) - contrast_keys
            ))
            if (
                not feature_keys
                or len(feature_keys)
                > self._profile.max_features_per_relation
            ):
                raise ValueError(
                    "acoustic structural relation is unresolved"
                )
            features = []
            for ear_id, neuron_id in feature_keys:
                features.append(W1AcousticRelationFeature(
                    ear_id=ear_id,
                    neuron_id=neuron_id,
                    positive_activation_receipt_sha256s=tuple(
                        tuple(sorted(
                            activation.authority_receipt_sha256
                            for activation
                            in lesson.cue_evidence.activations
                            if _activation_key(activation)
                            == (ear_id, neuron_id)
                        ))
                        for lesson in positives
                    ),
                ))
            patterns.append(W1AcousticStructuralPattern(
                relation=relation,
                relation_structure_id=relation_structure_id,
                features=tuple(features),
                positive_lesson_receipt_sha256s=tuple(
                    value.authority_receipt_sha256
                    for value in positives
                ),
                contrast_lesson_receipt_sha256s=tuple(sorted(
                    value.authority_receipt_sha256
                    for value in contrasts
                )),
            ))
        provisional = W1AcousticStructuralDistinction(
            distinction_id="0" * 64,
            patterns=tuple(patterns),
            background_evidences=background_evidences,
            source_lesson_receipt_sha256s=receipts,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._distinction_key,
            _DISTINCTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1AcousticStructuralDistinction(
            distinction_id=_digest(payload),
            patterns=provisional.patterns,
            background_evidences=background_evidences,
            source_lesson_receipt_sha256s=receipts,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify_distinction(result)
        with self._lock:
            if result.distinction_id in self._distinctions:
                return result
            if len(self._distinctions) >= self._profile.max_distinctions:
                raise RuntimeError(
                    "acoustic relation distinction capacity exhausted"
                )
            staged = dict(self._distinctions)
            staged[result.distinction_id] = result
            self._encoded(self._lessons, staged)
            self._distinctions = staged
        return result

    def resolve(
        self,
        *,
        distinction: W1AcousticStructuralDistinction,
        challenge_evidence: W1BinauralGroundingEvidence,
    ) -> W1AcousticStructuralResolution:
        """Resolve one fresh physical cue without mutating owner or W1."""

        self.verify_distinction(distinction)
        self._grounding.verify(challenge_evidence)
        self._verify_activation_field(challenge_evidence.activations)
        challenge_sources = {
            challenge_evidence.authority_receipt_sha256,
            challenge_evidence.binaural_firing_receipt_sha256,
            challenge_evidence.causal_settlement_receipt_sha256,
            challenge_evidence.receptor_settlement_receipt_sha256,
        }
        lesson_sources = {
            source
            for receipt in distinction.source_lesson_receipt_sha256s
            for lesson in self._lessons.values()
            if lesson.authority_receipt_sha256 == receipt
            for source in lesson.source_receipt_sha256s
        }
        lesson_sources |= {
            source
            for evidence in distinction.background_evidences
            for source in (
                evidence.authority_receipt_sha256,
                evidence.binaural_firing_receipt_sha256,
                evidence.causal_settlement_receipt_sha256,
                evidence.receptor_settlement_receipt_sha256,
            )
        }
        if challenge_sources.intersection(lesson_sources):
            raise ValueError(
                "acoustic relation challenge reuses a training source"
            )
        active = {
            _activation_key(value): value
            for value in challenge_evidence.activations
        }
        retained = {
            value.authority_receipt_sha256: value
            for value in self._lessons.values()
        }
        matches = []
        for pattern in distinction.patterns:
            if not any(value.key in active for value in pattern.features):
                continue
            proofs = tuple(
                retained[receipt].relation_proof
                for receipt in pattern.positive_lesson_receipt_sha256s
            )
            activations = tuple(
                active[value.key]
                for value in pattern.features
                if value.key in active
            )
            matches.append(W1ResolvedGroundedStructuralRelation(
                relation=pattern.relation,
                relation_structure_id=pattern.relation_structure_id,
                positive_relation_proofs=proofs,
                matched_challenge_activations=activations,
            ))
        if not matches:
            state = W1AcousticStructuralResolutionState.UNKNOWN
            reason = "no_complete_learned_acoustic_relation_active"
        elif len(matches) == 1:
            state = W1AcousticStructuralResolutionState.RESOLVED
            reason = "one_complete_learned_acoustic_relation_active"
        else:
            state = W1AcousticStructuralResolutionState.AMBIGUOUS
            reason = "multiple_complete_learned_acoustic_relations_active"
        provisional = W1AcousticStructuralResolution(
            state=state,
            reason=reason,
            challenge_evidence_receipt_sha256=(
                challenge_evidence.authority_receipt_sha256
            ),
            matches=tuple(matches),
            relation_release_authorized=state is (
                W1AcousticStructuralResolutionState.RESOLVED
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._resolution_key,
            _RESOLUTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        return W1AcousticStructuralResolution(
            state=state,
            reason=reason,
            challenge_evidence_receipt_sha256=(
                challenge_evidence.authority_receipt_sha256
            ),
            matches=tuple(matches),
            relation_release_authorized=(
                provisional.relation_release_authorized
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )

    def verify_resolution(
        self, value: W1AcousticStructuralResolution
    ) -> None:
        _sha256(
            value.challenge_evidence_receipt_sha256,
            "acoustic relation challenge",
        )
        _sha256(
            value.authority_hmac_sha256,
            "acoustic relation resolution HMAC",
        )
        _sha256(
            value.authority_receipt_sha256,
            "acoustic relation resolution authority",
        )
        expected_release = (
            value.state is W1AcousticStructuralResolutionState.RESOLVED
            and len(value.matches) == 1
        )
        if (
            value.relation_release_authorized is not expected_release
            or (
                value.state is W1AcousticStructuralResolutionState.UNKNOWN
                and value.matches
            )
            or (
                value.state
                is W1AcousticStructuralResolutionState.AMBIGUOUS
                and len(value.matches) < 2
            )
        ):
            raise ValueError("acoustic relation resolution state changed")
        for match in value.matches:
            if (
                not match.positive_relation_proofs
                or not match.matched_challenge_activations
                or any(
                    _relation_structure_id(proof)
                    != match.relation_structure_id
                    for proof in match.positive_relation_proofs
                )
                or any(
                    proof.relation is not match.relation
                    for proof in match.positive_relation_proofs
                )
            ):
                raise ValueError(
                    "acoustic relation full response changed"
                )
            _sha256(
                match.relation_structure_id,
                "resolved acoustic relation structure",
            )
            for proof in match.positive_relation_proofs:
                self._relations.verify(proof)
            for activation in match.matched_challenge_activations:
                activation.verify()
        payload = value.payload()
        signature = hmac.new(
            self._resolution_key,
            _RESOLUTION_DOMAIN + _canonical(payload),
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
            raise ValueError(
                "acoustic relation resolution authority changed"
            )

    def _body(
        self,
        lessons: Mapping[str, W1AcousticStructuralRelationLesson],
        distinctions: Mapping[
            str, W1AcousticStructuralDistinction
        ],
    ) -> dict[str, object]:
        return {
            "distinctions": [
                distinctions[key].record()
                for key in sorted(distinctions)
            ],
            "lessons": [
                lessons[key].record() for key in sorted(lessons)
            ],
            "resource_profile": self._profile.record(),
            "schema": ACOUSTIC_RELATION_STATE_SCHEMA,
        }

    def _encoded(
        self,
        lessons: Mapping[str, W1AcousticStructuralRelationLesson],
        distinctions: Mapping[
            str, W1AcousticStructuralDistinction
        ],
    ) -> bytes:
        body = self._body(lessons, distinctions)
        encoded = _canonical({
            "body": body,
            "schema": ACOUSTIC_RELATION_ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError(
                "acoustic relation state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(
                self._lessons, self._distinctions
            )

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
        relation_owner: W1GroundedStructuralRelationOwner,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
        motif_owner: AuditoryRecurrentMotifOwner,
    ) -> "W1AcousticStructuralRelationOwner":
        if not isinstance(encoded, bytes):
            raise TypeError(
                "acoustic relation state must be immutable bytes"
            )
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "acoustic relation state is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema")
            != ACOUSTIC_RELATION_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
            or not isinstance(envelope.get("body"), Mapping)
        ):
            raise ValueError("acoustic relation state envelope changed")
        body = envelope["body"]
        if (
            set(body) != {
                "distinctions",
                "lessons",
                "resource_profile",
                "schema",
            }
            or body.get("schema") != ACOUSTIC_RELATION_STATE_SCHEMA
            or not isinstance(body.get("distinctions"), list)
            or not isinstance(body.get("lessons"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("acoustic relation state body changed")
        raw_profile = body["resource_profile"]
        expected_profile = {
            "authority_receipt_sha256",
            "max_activations_per_lesson",
            "max_background_evidences_per_distinction",
            "max_distinctions",
            "max_features_per_relation",
            "max_lesson_bytes",
            "max_lessons",
            "max_lessons_per_distinction",
            "max_state_bytes",
            "profile_id",
            "schema",
        }
        if set(raw_profile) != expected_profile:
            raise ValueError("acoustic relation profile record changed")
        profile = W1AcousticStructuralRelationResourceProfile(
            profile_id=raw_profile.get("profile_id"),
            max_lessons=raw_profile.get("max_lessons"),
            max_distinctions=raw_profile.get("max_distinctions"),
            max_lessons_per_distinction=raw_profile.get(
                "max_lessons_per_distinction"
            ),
            max_background_evidences_per_distinction=raw_profile.get(
                "max_background_evidences_per_distinction"
            ),
            max_features_per_relation=raw_profile.get(
                "max_features_per_relation"
            ),
            max_activations_per_lesson=raw_profile.get(
                "max_activations_per_lesson"
            ),
            max_lesson_bytes=raw_profile.get("max_lesson_bytes"),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
            relation_owner=relation_owner,
            grounding_authority=grounding_authority,
            motif_owner=motif_owner,
        )
        expected_hmac = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected_hmac,
        ):
            raise ValueError("acoustic relation state HMAC changed")
        proofs = {
            value.authority_receipt_sha256: value
            for value in relation_owner.proofs
        }
        used_sources: set[str] = set()
        for raw in body["lessons"]:
            if not isinstance(raw, Mapping):
                raise ValueError("acoustic relation lesson record changed")
            proof_raw = raw.get("relation_proof")
            if not isinstance(proof_raw, Mapping):
                raise ValueError("acoustic relation proof record changed")
            proof = proofs.get(
                proof_raw.get("authority_receipt_sha256")
            )
            if proof is None or proof.record() != dict(proof_raw):
                raise ValueError(
                    "acoustic relation proof lost live ownership"
                )
            lesson = W1AcousticStructuralRelationLesson(
                lesson_id=raw.get("lesson_id"),
                relation_proof=proof,
                cue_evidence=_evidence(raw.get("cue_evidence")),
                causal_junction_receipt_sha256s=tuple(
                    raw.get("causal_junction_receipt_sha256s", ())
                ),
                source_receipt_sha256s=tuple(
                    raw.get("source_receipt_sha256s", ())
                ),
                authority_hmac_sha256=raw.get(
                    "authority_hmac_sha256"
                ),
                authority_receipt_sha256=raw.get(
                    "authority_receipt_sha256"
                ),
            )
            owner.verify_lesson(lesson)
            if (
                lesson.lesson_id in owner._lessons
                or used_sources.intersection(
                    lesson.source_receipt_sha256s
                )
            ):
                raise ValueError(
                    "restored acoustic relation sources repeat"
                )
            owner._lessons[lesson.lesson_id] = lesson
            used_sources.update(lesson.source_receipt_sha256s)
        for raw in body["distinctions"]:
            if not isinstance(raw, Mapping):
                raise ValueError(
                    "acoustic relation distinction record changed"
                )
            patterns = []
            for pattern_raw in raw.get("patterns", ()):
                features = tuple(
                    W1AcousticRelationFeature(
                        ear_id=value.get("ear_id"),
                        neuron_id=value.get("neuron_id"),
                        positive_activation_receipt_sha256s=tuple(
                            tuple(receipts)
                            for receipts in value.get(
                                "positive_activation_receipt_sha256s",
                                (),
                            )
                        ),
                    )
                    for value in pattern_raw.get("features", ())
                )
                patterns.append(W1AcousticStructuralPattern(
                    relation=W1GroundedStructuralRelationKind(
                        pattern_raw.get("relation")
                    ),
                    relation_structure_id=pattern_raw.get(
                        "relation_structure_id"
                    ),
                    features=features,
                    positive_lesson_receipt_sha256s=tuple(
                        pattern_raw.get(
                            "positive_lesson_receipt_sha256s", ()
                        )
                    ),
                    contrast_lesson_receipt_sha256s=tuple(
                        pattern_raw.get(
                            "contrast_lesson_receipt_sha256s", ()
                        )
                    ),
                ))
            distinction = W1AcousticStructuralDistinction(
                distinction_id=raw.get("distinction_id"),
                patterns=tuple(patterns),
                background_evidences=tuple(
                    _evidence(value)
                    for value in raw.get("background_evidences", ())
                ),
                source_lesson_receipt_sha256s=tuple(
                    raw.get("source_lesson_receipt_sha256s", ())
                ),
                authority_hmac_sha256=raw.get(
                    "authority_hmac_sha256"
                ),
                authority_receipt_sha256=raw.get(
                    "authority_receipt_sha256"
                ),
            )
            owner.verify_distinction(distinction)
            if distinction.distinction_id in owner._distinctions:
                raise ValueError(
                    "restored acoustic relation distinction repeats"
                )
            owner._distinctions[distinction.distinction_id] = (
                distinction
            )
        if owner.snapshot_encoded() != encoded:
            raise ValueError(
                "acoustic relation restored state is not canonical"
            )
        return owner

    def status(self) -> dict[str, object]:
        with self._lock:
            learned = {
                pattern.relation.value
                for distinction in self._distinctions.values()
                for pattern in distinction.patterns
            }
            required = {
                value.value
                for value in W1GroundedStructuralRelationKind
            }
            return {
                "all_relation_kinds_learned": learned == required,
                "capacity_exhausted": (
                    len(self._lessons) >= self._profile.max_lessons
                    or len(self._distinctions)
                    >= self._profile.max_distinctions
                ),
                "distinction_count": len(self._distinctions),
                "learned_relation_kinds": sorted(learned),
                "lesson_count": len(self._lessons),
                "missing_relation_kinds": sorted(required - learned),
                "state_bytes": len(self._encoded(
                    self._lessons, self._distinctions
                )),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }


__all__ = [
    "ACOUSTIC_RELATION_DISTINCTION_SCHEMA",
    "ACOUSTIC_RELATION_ENVELOPE_SCHEMA",
    "ACOUSTIC_RELATION_LESSON_SCHEMA",
    "ACOUSTIC_RELATION_PROFILE_SCHEMA",
    "ACOUSTIC_RELATION_RESOLUTION_SCHEMA",
    "ACOUSTIC_RELATION_STATE_SCHEMA",
    "W1AcousticRelationFeature",
    "W1AcousticStructuralDistinction",
    "W1AcousticStructuralPattern",
    "W1AcousticStructuralRelationLesson",
    "W1AcousticStructuralRelationOwner",
    "W1AcousticStructuralRelationResourceProfile",
    "W1AcousticStructuralResolution",
    "W1AcousticStructuralResolutionState",
    "W1ResolvedGroundedStructuralRelation",
]
