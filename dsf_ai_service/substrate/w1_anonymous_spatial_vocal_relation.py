"""Full-field anonymous auditory-q to signed spatial relation authority.

The owner retains complete W1 activation intervals and every underlying
D/M/R/U/C/P/B occurrence. A diagnostic temporal feature is one exact recurrent
q neuron present in every positive lesson and absent from every contrast
lesson. Its neuron is re-resolved against the retained recurrent-q state and
all retained lesson witnesses. Challenge release is conjunctive: every
feature in one causally contrasted relation must be active; no individual
feature is sufficient.
No count, rank, score, threshold, word, speaker, or tutor role is authoritative.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.substrate.auditory_motif_causal_grounding import GroundingRoot
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralActivationEvidence,
)
from dsf_ai_service.substrate.w1_vocal_spatial_action_lesson import (
    W1VocalSpatialActionLesson,
    W1VocalSpatialActionLessonAuthority,
)


W1_ANONYMOUS_SPATIAL_VOCAL_PROFILE_SCHEMA = (
    "guala.w1.anonymous_spatial_vocal.profile.v3"
)
W1_ANONYMOUS_SPATIAL_VOCAL_LESSON_SCHEMA = (
    "guala.w1.anonymous_spatial_vocal.lesson.v3"
)
W1_ANONYMOUS_SPATIAL_VOCAL_DISTINCTION_SCHEMA = (
    "guala.w1.anonymous_spatial_vocal.distinction.v3"
)
_LESSON_DOMAIN = b"guala-w1-anonymous-spatial-vocal-lesson-v3\0"
_DISTINCTION_DOMAIN = b"guala-w1-anonymous-spatial-vocal-distinction-v3\0"
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False,
        separators=(",", ":"), sort_keys=True,
    ).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode()
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("W1 spatial-vocal key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 spatial-vocal key boundary changed")
    return result


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(item not in _HEX for item in value)
    ):
        raise ValueError(f"{name} must be a SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _feature_key(
    activation: W1BinauralActivationEvidence,
) -> tuple[str, str]:
    activation.verify()
    return activation.ear_id, activation.neuron_id


def _activation_order(
    activation: W1BinauralActivationEvidence,
) -> tuple[int, int, str, str]:
    activation.verify()
    record = json.loads(activation.activation_json)
    return (
        record["source_index_start"],
        record["source_index_end"],
        activation.ear_id,
        activation.neuron_id,
    )


@dataclass(frozen=True, slots=True)
class W1AnonymousSpatialVocalResourceProfile:
    profile_id: str
    max_lessons: int
    max_distinctions: int
    max_lessons_per_distinction: int
    max_relations_per_distinction: int
    required_dynamic_root_count: int
    max_features_per_relation: int
    max_activations_per_lesson: int
    max_record_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_lessons: int,
        max_distinctions: int,
        max_lessons_per_distinction: int,
        max_relations_per_distinction: int,
        required_dynamic_root_count: int,
        max_features_per_relation: int,
        max_activations_per_lesson: int,
        max_record_bytes: int,
    ) -> "W1AnonymousSpatialVocalResourceProfile":
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise ValueError("W1 spatial-vocal profile identifier changed")
        values = (
            max_lessons,
            max_distinctions,
            max_lessons_per_distinction,
            max_relations_per_distinction,
            required_dynamic_root_count,
            max_features_per_relation,
            max_activations_per_lesson,
            max_record_bytes,
        )
        for value, name in zip(
            values,
            (
                "lesson capacity", "distinction capacity",
                "lessons per distinction", "relations per distinction",
                "dynamic root count", "feature capacity",
                "activation capacity", "record byte capacity",
            ),
            strict=True,
        ):
            _positive(value, name)
        provisional = cls(
            profile_id=profile_id,
            max_lessons=max_lessons,
            max_distinctions=max_distinctions,
            max_lessons_per_distinction=max_lessons_per_distinction,
            max_relations_per_distinction=max_relations_per_distinction,
            required_dynamic_root_count=required_dynamic_root_count,
            max_features_per_relation=max_features_per_relation,
            max_activations_per_lesson=max_activations_per_lesson,
            max_record_bytes=max_record_bytes,
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=profile_id,
            max_lessons=max_lessons,
            max_distinctions=max_distinctions,
            max_lessons_per_distinction=max_lessons_per_distinction,
            max_relations_per_distinction=max_relations_per_distinction,
            required_dynamic_root_count=required_dynamic_root_count,
            max_features_per_relation=max_features_per_relation,
            max_activations_per_lesson=max_activations_per_lesson,
            max_record_bytes=max_record_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_activations_per_lesson": self.max_activations_per_lesson,
            "max_distinctions": self.max_distinctions,
            "max_features_per_relation": self.max_features_per_relation,
            "max_lessons": self.max_lessons,
            "max_lessons_per_distinction": self.max_lessons_per_distinction,
            "max_record_bytes": self.max_record_bytes,
            "max_relations_per_distinction": self.max_relations_per_distinction,
            "profile_id": self.profile_id,
            "required_dynamic_root_count": self.required_dynamic_root_count,
            "schema": W1_ANONYMOUS_SPATIAL_VOCAL_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _sha(self.authority_receipt_sha256, "spatial-vocal profile")
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 spatial-vocal profile changed")


@dataclass(frozen=True, slots=True)
class W1AnonymousSpatialVocalLesson:
    lesson_id: str
    vocal_spatial_action_lesson_receipt_sha256: str
    spatial_settlement_receipt_sha256: str
    before_pose_sha256: str
    signed_displacement: tuple[int, int, int, int]
    full_dynamic_roots: tuple[GroundingRoot, ...]
    vocal_activations: tuple[W1BinauralActivationEvidence, ...]
    source_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "vocal_spatial_action_lesson_receipt_sha256": (
                self.vocal_spatial_action_lesson_receipt_sha256
            ),
            "before_pose_sha256": self.before_pose_sha256,
            "full_dynamic_roots": [
                root.as_record() for root in self.full_dynamic_roots
            ],
            "schema": W1_ANONYMOUS_SPATIAL_VOCAL_LESSON_SCHEMA,
            "signed_displacement": list(self.signed_displacement),
            "source_receipt_sha256s": list(self.source_receipt_sha256s),
            "spatial_settlement_receipt_sha256": (
                self.spatial_settlement_receipt_sha256
            ),
            "vocal_activations": [
                value.record() for value in self.vocal_activations
            ],
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "lesson_id": self.lesson_id,
        }


@dataclass(frozen=True, slots=True)
class W1RecurrentQTemporalFeature:
    ear_id: str
    neuron_id: str
    positive_activation_witness_receipt_sha256s: tuple[
        tuple[str, ...], ...
    ]

    @property
    def feature_key(self) -> tuple[str, str]:
        return self.ear_id, self.neuron_id

    def record(self) -> dict[str, object]:
        return {
            "ear_id": self.ear_id,
            "neuron_id": self.neuron_id,
            "positive_activation_witness_receipt_sha256s": [
                list(receipts)
                for receipts
                in self.positive_activation_witness_receipt_sha256s
            ],
        }


@dataclass(frozen=True, slots=True)
class W1AnonymousSpatialVocalRelation:
    signed_displacement: tuple[int, int, int, int]
    before_pose_sha256: str
    diagnostic_features: tuple[W1RecurrentQTemporalFeature, ...]
    positive_lesson_receipt_sha256s: tuple[str, ...]
    contrast_lesson_receipt_sha256s: tuple[str, ...]

    def record(self) -> dict[str, object]:
        return {
            "before_pose_sha256": self.before_pose_sha256,
            "contrast_lesson_receipt_sha256s": list(
                self.contrast_lesson_receipt_sha256s
            ),
            "diagnostic_features": [
                value.record() for value in self.diagnostic_features
            ],
            "positive_lesson_receipt_sha256s": list(
                self.positive_lesson_receipt_sha256s
            ),
            "signed_displacement": list(self.signed_displacement),
        }


@dataclass(frozen=True, slots=True)
class W1AnonymousSpatialVocalDistinction:
    distinction_id: str
    q_state_sha256: str
    relations: tuple[W1AnonymousSpatialVocalRelation, ...]
    source_lesson_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "q_state_sha256": self.q_state_sha256,
            "relations": [value.record() for value in self.relations],
            "schema": W1_ANONYMOUS_SPATIAL_VOCAL_DISTINCTION_SCHEMA,
            "source_lesson_receipt_sha256s": list(
                self.source_lesson_receipt_sha256s
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "distinction_id": self.distinction_id,
        }


class W1AnonymousSpatialVocalRelationOwner:
    """Bounded full-field lesson and Boolean feature-relation authority."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1AnonymousSpatialVocalResourceProfile,
        lesson_authority: W1VocalSpatialActionLessonAuthority,
        motif_owner: AuditoryRecurrentMotifOwner,
    ) -> None:
        resource_profile.verify()
        if not isinstance(motif_owner, AuditoryRecurrentMotifOwner):
            raise TypeError("W1 spatial-vocal relation requires q authority")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._lesson_key = hashlib.sha256(_LESSON_DOMAIN + root).digest()
        self._distinction_key = hashlib.sha256(
            _DISTINCTION_DOMAIN + root
        ).digest()
        self._profile = resource_profile
        if not isinstance(
            lesson_authority, W1VocalSpatialActionLessonAuthority
        ):
            raise TypeError(
                "W1 spatial-vocal relation requires cue-action authority"
            )
        self._lessons_source = lesson_authority
        self._motifs = motif_owner
        self._lessons: dict[str, W1AnonymousSpatialVocalLesson] = {}
        self._distinctions: dict[
            str, W1AnonymousSpatialVocalDistinction
        ] = {}
        self._lock = threading.RLock()

    def _q_state_sha256(self) -> str:
        return hashlib.sha256(self._motifs.snapshot_encoded()).hexdigest()

    def _verify_activation_set(
        self, values: tuple[W1BinauralActivationEvidence, ...]
    ) -> None:
        if (
            not values
            or len(values) > self._profile.max_activations_per_lesson
            or values != tuple(sorted(values, key=_activation_order))
        ):
            raise ValueError("W1 spatial-vocal activation field changed")
        neurons = {
            value.neuron_id: value for value in self._motifs.motif_neurons
        }
        for value in values:
            value.verify()
            neuron = neurons.get(value.neuron_id)
            if neuron is None or neuron.lane.ear_id != value.ear_id:
                raise ValueError(
                    "W1 spatial-vocal activation lost its q neuron"
                )
            neuron.verify()

    def verify_lesson(self, lesson: W1AnonymousSpatialVocalLesson) -> None:
        for value in (
            lesson.lesson_id,
            lesson.vocal_spatial_action_lesson_receipt_sha256,
            lesson.spatial_settlement_receipt_sha256,
            lesson.before_pose_sha256,
            lesson.authority_hmac_sha256,
            lesson.authority_receipt_sha256,
            *lesson.source_receipt_sha256s,
        ):
            _sha(value, "spatial-vocal lesson authority")
        if (
            len(lesson.full_dynamic_roots)
            != self._profile.required_dynamic_root_count
            or lesson.source_receipt_sha256s
            != tuple(sorted(set(lesson.source_receipt_sha256s)))
        ):
            raise ValueError("W1 spatial-vocal lesson changed")
        for root in lesson.full_dynamic_roots:
            root.verify()
        self._verify_activation_set(lesson.vocal_activations)
        payload = lesson.payload()
        signature = hmac.new(
            self._lesson_key, _LESSON_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            lesson.lesson_id != _digest(payload)
            or len(_canonical(payload)) > self._profile.max_record_bytes
            or not hmac.compare_digest(signature, lesson.authority_hmac_sha256)
            or lesson.authority_receipt_sha256
            != _digest({"authority_hmac_sha256": signature, "payload": payload})
        ):
            raise ValueError("W1 spatial-vocal lesson authority changed")

    def compose_lesson(
        self,
        *,
        vocal_spatial_action_lesson: W1VocalSpatialActionLesson,
    ) -> W1AnonymousSpatialVocalLesson:
        self._lessons_source.verify(vocal_spatial_action_lesson)
        spatial_settlement = vocal_spatial_action_lesson.spatial_settlement
        activations = tuple(sorted(
            vocal_spatial_action_lesson.vocal_activations,
            key=_activation_order,
        ))
        sources = tuple(sorted({
            spatial_settlement.execution_receipt_sha256,
            spatial_settlement.evidence_receipt_sha256,
            spatial_settlement.causal_settlement_receipt_sha256,
            spatial_settlement.authority_receipt_sha256,
            vocal_spatial_action_lesson.vocal_execution_receipt_sha256,
            vocal_spatial_action_lesson.vocal_evidence_receipt_sha256,
            vocal_spatial_action_lesson.vocal_grounding_receipt_sha256,
        }))
        provisional = W1AnonymousSpatialVocalLesson(
            lesson_id="0" * 64,
            vocal_spatial_action_lesson_receipt_sha256=(
                vocal_spatial_action_lesson.authority_receipt_sha256
            ),
            spatial_settlement_receipt_sha256=(
                spatial_settlement.authority_receipt_sha256
            ),
            before_pose_sha256=_digest(
                spatial_settlement.before_pose.as_record()
            ),
            signed_displacement=spatial_settlement.signed_displacement,
            full_dynamic_roots=spatial_settlement.full_dynamic_roots,
            vocal_activations=activations,
            source_receipt_sha256s=sources,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._lesson_key, _LESSON_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1AnonymousSpatialVocalLesson(
            lesson_id=_digest(payload),
            vocal_spatial_action_lesson_receipt_sha256=(
                provisional.vocal_spatial_action_lesson_receipt_sha256
            ),
            spatial_settlement_receipt_sha256=(
                provisional.spatial_settlement_receipt_sha256
            ),
            before_pose_sha256=provisional.before_pose_sha256,
            signed_displacement=provisional.signed_displacement,
            full_dynamic_roots=provisional.full_dynamic_roots,
            vocal_activations=provisional.vocal_activations,
            source_receipt_sha256s=provisional.source_receipt_sha256s,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature, "payload": payload
            }),
        )
        self.verify_lesson(result)
        self.retain_lesson(result)
        return result

    def retain_lesson(
        self, lesson: W1AnonymousSpatialVocalLesson
    ) -> None:
        """Retain one verified full lesson for receipt-based re-resolution."""

        self.verify_lesson(lesson)
        with self._lock:
            if lesson.lesson_id in self._lessons:
                return
            if any(
                set(item.source_receipt_sha256s).intersection(
                    lesson.source_receipt_sha256s
                )
                for item in self._lessons.values()
            ):
                raise ValueError("W1 spatial-vocal lesson reuses a source")
            if len(self._lessons) >= self._profile.max_lessons:
                raise RuntimeError("W1 spatial-vocal lesson capacity exhausted")
            self._lessons[lesson.lesson_id] = lesson

    def relation_action_fields(
        self, relation: W1AnonymousSpatialVocalRelation
    ) -> tuple[tuple[GroundingRoot, ...], ...]:
        """Resolve complete positive DSF fields from retained lesson receipts."""

        retained = {
            lesson.authority_receipt_sha256: lesson
            for lesson in self._lessons.values()
        }
        try:
            lessons = tuple(
                retained[receipt]
                for receipt in relation.positive_lesson_receipt_sha256s
            )
        except KeyError as error:
            raise ValueError(
                "W1 spatial relation lost its full action field"
            ) from error
        for lesson in lessons:
            self.verify_lesson(lesson)
        return tuple(lesson.full_dynamic_roots for lesson in lessons)

    def _verify_feature(self, feature: W1RecurrentQTemporalFeature) -> None:
        if len(
            feature.positive_activation_witness_receipt_sha256s
        ) < 2:
            raise ValueError("W1 recurrent q feature changed")
        for receipts in (
            feature.positive_activation_witness_receipt_sha256s
        ):
            if not receipts or receipts != tuple(sorted(set(receipts))):
                raise ValueError("W1 recurrent q feature witness changed")
            for receipt in receipts:
                _sha(receipt, "W1 recurrent q feature witness")

    def learn(
        self, lessons: tuple[W1AnonymousSpatialVocalLesson, ...]
    ) -> W1AnonymousSpatialVocalDistinction:
        if (
            not isinstance(lessons, tuple)
            or len(lessons) > self._profile.max_lessons_per_distinction
        ):
            raise ValueError("W1 spatial-vocal lesson boundary changed")
        for lesson in lessons:
            self.verify_lesson(lesson)
        receipts = tuple(sorted(
            lesson.authority_receipt_sha256 for lesson in lessons
        ))
        if len(receipts) != len(set(receipts)):
            raise ValueError("W1 spatial-vocal lessons are not disjoint")
        groups: dict[
            tuple[int, int, int, int],
            list[W1AnonymousSpatialVocalLesson],
        ] = {}
        for lesson in lessons:
            groups.setdefault(lesson.signed_displacement, []).append(lesson)
        if (
            not 2 <= len(groups) <= self._profile.max_relations_per_distinction
            or any(len(group) < 2 for group in groups.values())
            or len({lesson.before_pose_sha256 for lesson in lessons}) != 1
        ):
            raise ValueError(
                "W1 spatial-vocal distinction requires at least two lessons "
                "per relation from one exact before pose"
            )
        relations = []
        for displacement in sorted(groups):
            positive = groups[displacement]
            positive_key_sets = tuple(
                {
                    _feature_key(value)
                    for value in lesson.vocal_activations
                }
                for lesson in positive
            )
            positive_keys = set.intersection(*positive_key_sets)
            contrasts = tuple(
                lesson for other, group in groups.items()
                if other != displacement for lesson in group
            )
            contrast_keys = {
                _feature_key(value) for lesson in contrasts
                for value in lesson.vocal_activations
            }
            feature_keys = tuple(sorted(positive_keys - contrast_keys))
            if (
                not feature_keys
                or len(feature_keys) > self._profile.max_features_per_relation
            ):
                raise ValueError("W1 spatial-vocal relation is unresolved")
            features = []
            for ear_id, neuron_id in feature_keys:
                witnesses = tuple(
                    tuple(
                        value for value in lesson.vocal_activations
                        if _feature_key(value) == (ear_id, neuron_id)
                    )
                    for lesson in positive
                )
                features.append(W1RecurrentQTemporalFeature(
                    ear_id=ear_id,
                    neuron_id=neuron_id,
                    positive_activation_witness_receipt_sha256s=tuple(
                        tuple(sorted(
                            value.authority_receipt_sha256
                            for value in lesson_witnesses
                        ))
                        for lesson_witnesses in witnesses
                    ),
                ))
            relations.append(W1AnonymousSpatialVocalRelation(
                signed_displacement=displacement,
                before_pose_sha256=positive[0].before_pose_sha256,
                diagnostic_features=tuple(features),
                positive_lesson_receipt_sha256s=tuple(
                    lesson.authority_receipt_sha256
                    for lesson in positive
                ),
                contrast_lesson_receipt_sha256s=tuple(sorted(
                    lesson.authority_receipt_sha256
                    for lesson in contrasts
                )),
            ))
        provisional = W1AnonymousSpatialVocalDistinction(
            distinction_id="0" * 64,
            q_state_sha256=self._q_state_sha256(),
            relations=tuple(relations),
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
        result = W1AnonymousSpatialVocalDistinction(
            distinction_id=_digest(payload),
            q_state_sha256=provisional.q_state_sha256,
            relations=provisional.relations,
            source_lesson_receipt_sha256s=receipts,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature, "payload": payload
            }),
        )
        self.verify_distinction(result)
        with self._lock:
            if len(self._distinctions) >= self._profile.max_distinctions:
                raise RuntimeError(
                    "W1 spatial-vocal distinction capacity exhausted"
                )
            self._distinctions[result.distinction_id] = result
        return result

    def verify_distinction(
        self, distinction: W1AnonymousSpatialVocalDistinction
    ) -> None:
        for value in (
            distinction.distinction_id,
            distinction.q_state_sha256,
            distinction.authority_hmac_sha256,
            distinction.authority_receipt_sha256,
            *distinction.source_lesson_receipt_sha256s,
        ):
            _sha(value, "spatial-vocal distinction authority")
        if (
            distinction.q_state_sha256 != self._q_state_sha256()
            or not 2 <= len(distinction.relations)
            <= self._profile.max_relations_per_distinction
        ):
            raise ValueError("W1 spatial-vocal distinction q state changed")
        feature_keys: set[tuple[str, str]] = set()
        used_lessons: set[str] = set()
        retained_lessons = {
            lesson.authority_receipt_sha256: lesson
            for lesson in self._lessons.values()
        }
        for relation in distinction.relations:
            if (
                len(relation.positive_lesson_receipt_sha256s) < 2
                or not relation.contrast_lesson_receipt_sha256s
                or not relation.diagnostic_features
                or set(relation.positive_lesson_receipt_sha256s).intersection(
                    relation.contrast_lesson_receipt_sha256s
                )
            ):
                raise ValueError("W1 spatial-vocal relation changed")
            try:
                positive_lessons = tuple(
                    retained_lessons[receipt]
                    for receipt in relation.positive_lesson_receipt_sha256s
                )
                contrast_lessons = tuple(
                    retained_lessons[receipt]
                    for receipt in relation.contrast_lesson_receipt_sha256s
                )
            except KeyError as error:
                raise ValueError(
                    "W1 spatial-vocal relation lost retained lesson"
                ) from error
            positive_keys = tuple(
                {
                    _feature_key(value)
                    for value in lesson.vocal_activations
                }
                for lesson in positive_lessons
            )
            contrast_keys = {
                _feature_key(value)
                for lesson in contrast_lessons
                for value in lesson.vocal_activations
            }
            for lesson in (*positive_lessons, *contrast_lessons):
                self.verify_lesson(lesson)
            for feature in relation.diagnostic_features:
                self._verify_feature(feature)
                expected_receipts = tuple(
                    tuple(sorted(
                        value.authority_receipt_sha256
                        for value in witnesses
                        if _feature_key(value) == feature.feature_key
                    ))
                    for witnesses in (
                        lesson.vocal_activations
                        for lesson in positive_lessons
                    )
                )
                if (
                    any(
                        feature.feature_key not in keys
                        for keys in positive_keys
                    )
                    or (
                        feature.positive_activation_witness_receipt_sha256s
                        != expected_receipts
                    )
                    or feature.feature_key in contrast_keys
                    or feature.feature_key in feature_keys
                ):
                    raise ValueError("W1 recurrent q feature contrast changed")
                feature_keys.add(feature.feature_key)
            used_lessons.update(relation.positive_lesson_receipt_sha256s)
            used_lessons.update(relation.contrast_lesson_receipt_sha256s)
        if used_lessons != set(distinction.source_lesson_receipt_sha256s):
            raise ValueError("W1 spatial-vocal distinction lost lessons")
        payload = distinction.payload()
        signature = hmac.new(
            self._distinction_key,
            _DISTINCTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            distinction.distinction_id != _digest(payload)
            or len(_canonical(payload)) > self._profile.max_record_bytes
            or not hmac.compare_digest(
                signature, distinction.authority_hmac_sha256
            )
            or distinction.authority_receipt_sha256
            != _digest({"authority_hmac_sha256": signature, "payload": payload})
        ):
            raise ValueError("W1 spatial-vocal distinction authority changed")

    def resolve(
        self,
        distinction: W1AnonymousSpatialVocalDistinction,
        active_vocal_activations: tuple[
            W1BinauralActivationEvidence, ...
        ],
    ) -> tuple[W1AnonymousSpatialVocalRelation, ...]:
        self.verify_distinction(distinction)
        self._verify_activation_set(tuple(sorted(
            active_vocal_activations, key=_activation_order
        )))
        active_keys = {
            _feature_key(value) for value in active_vocal_activations
        }
        return tuple(
            relation for relation in distinction.relations
            if all(
                feature.feature_key in active_keys
                for feature in relation.diagnostic_features
            )
        )


__all__ = [
    "W1AnonymousSpatialVocalDistinction",
    "W1AnonymousSpatialVocalLesson",
    "W1AnonymousSpatialVocalRelation",
    "W1AnonymousSpatialVocalRelationOwner",
    "W1AnonymousSpatialVocalResourceProfile",
    "W1RecurrentQTemporalFeature",
]
