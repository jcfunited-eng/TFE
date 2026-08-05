"""Bounded authenticated structural relations over lived W1 evidence.

The five admitted relations are physical, not linguistic labels:

* exact referent continuity across independent causal settlements;
* one external emitter body continuing across independent emissions;
* exact signed pose/region change;
* vocal cue followed by an authenticated action outcome;
* the same exact cue/action revision junction viewed as causal predecessor.

Every action relation retains the complete dynamic D/M/R/U/C/P/B roots.
Nothing here contains question words, answers, names, transcripts, scores,
probabilities, tutor roles, or reduced DSF vectors.
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
    grounding_roots_from_settlement,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_vocal_spatial_action_lesson import (
    W1VocalSpatialActionLesson,
    W1VocalSpatialActionLessonAuthority,
)


STRUCTURAL_RELATION_PROFILE_SCHEMA = (
    "guala.w1.grounded_structural_relation.profile.v1"
)
STRUCTURAL_RELATION_PROOF_SCHEMA = (
    "guala.w1.grounded_structural_relation.proof.v1"
)
STRUCTURAL_RELATION_STATE_SCHEMA = (
    "guala.w1.grounded_structural_relation.state.v1"
)
STRUCTURAL_RELATION_ENVELOPE_SCHEMA = (
    "guala.w1.grounded_structural_relation.state_hmac.v1"
)
_PROOF_DOMAIN = b"guala-w1-grounded-structural-relation-proof-v1\0"
_STATE_DOMAIN = b"guala-w1-grounded-structural-relation-state-v1\0"
_BODY_DOMAIN = b"guala-w1-anonymous-emitter-body-continuity-v1\0"
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
    result = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(result, bytes) or not 32 <= len(result) <= 4_096:
        raise ValueError("structural relation key boundary changed")
    return result


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _body_pose(snapshot: ObservationSnapshot, body_id: str) -> PoseMM:
    matches = tuple(
        value.pose for value in snapshot.bodies
        if value.body_id == body_id
    )
    if len(matches) != 1:
        raise ValueError("structural relation body is not unique")
    return matches[0]


def _displacement(
    before: PoseMM,
    after: PoseMM,
) -> tuple[int, int, int, int]:
    return (
        after.position.x - before.position.x,
        after.position.y - before.position.y,
        after.position.z - before.position.z,
        after.heading_millidegrees - before.heading_millidegrees,
    )


class W1GroundedStructuralRelationKind(str, Enum):
    REFERENT_CONTINUITY = "referent_continuity"
    EMITTER_BODY_CONTINUITY = "emitter_body_continuity"
    POSE_REGION_RELATION = "pose_region_relation"
    ACTION_OUTCOME_AFFORDANCE = "action_outcome_affordance"
    CAUSAL_PREDECESSOR = "causal_predecessor"


@dataclass(frozen=True, slots=True)
class W1GroundedStructuralRelationProfile:
    profile_id: str
    max_proofs: int
    required_dynamic_root_count: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_proofs: int,
        required_dynamic_root_count: int,
        max_state_bytes: int,
    ) -> "W1GroundedStructuralRelationProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("structural relation profile changed")
        provisional = cls(
            profile_id=profile_id,
            max_proofs=_positive(max_proofs, "structural relation proofs"),
            required_dynamic_root_count=_positive(
                required_dynamic_root_count,
                "structural relation dynamic roots",
            ),
            max_state_bytes=_positive(
                max_state_bytes, "structural relation state"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_proofs=provisional.max_proofs,
            required_dynamic_root_count=(
                provisional.required_dynamic_root_count
            ),
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_proofs": self.max_proofs,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "required_dynamic_root_count": (
                self.required_dynamic_root_count
            ),
            "schema": STRUCTURAL_RELATION_PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        _positive(self.max_proofs, "structural relation proofs")
        _positive(
            self.required_dynamic_root_count,
            "structural relation dynamic roots",
        )
        _positive(self.max_state_bytes, "structural relation state")
        _sha256(
            self.authority_receipt_sha256,
            "structural relation profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("structural relation profile authority changed")


@dataclass(frozen=True, slots=True)
class W1GroundedStructuralRelationProof:
    proof_id: str
    relation: W1GroundedStructuralRelationKind
    source_receipt_sha256s: tuple[str, ...]
    upstream_authority_receipt_sha256s: tuple[str, ...]
    root_witnesses: tuple[GroundingRoot, ...]
    anonymous_body_continuity_sha256: str | None
    poses: tuple[PoseMM, ...]
    signed_displacement: tuple[int, int, int, int] | None
    revisions: tuple[int, ...]
    world_state_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "anonymous_body_continuity_sha256": (
                self.anonymous_body_continuity_sha256
            ),
            "poses": [value.as_record() for value in self.poses],
            "relation": self.relation.value,
            "revisions": list(self.revisions),
            "root_witnesses": [
                value.as_record() for value in self.root_witnesses
            ],
            "schema": STRUCTURAL_RELATION_PROOF_SCHEMA,
            "signed_displacement": (
                list(self.signed_displacement)
                if self.signed_displacement is not None
                else None
            ),
            "source_receipt_sha256s": list(
                self.source_receipt_sha256s
            ),
            "upstream_authority_receipt_sha256s": list(
                self.upstream_authority_receipt_sha256s
            ),
            "world_state_sha256s": list(self.world_state_sha256s),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "proof_id": self.proof_id,
        }


@dataclass(frozen=True, slots=True)
class W1RetainedEmitterBodyOccurrence:
    emission: AuthenticatedW1AcousticEmission
    execution: ActionExecutionReceipt
    observation: ObservationSnapshot


class W1GroundedStructuralRelationOwner:
    """One bounded authority for exact lived structural relations."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1GroundedStructuralRelationProfile,
    ) -> None:
        resource_profile.verify()
        root = hashlib.sha256(_key(authority_key)).digest()
        self._proof_key = hashlib.sha256(_PROOF_DOMAIN + root).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = resource_profile
        self._proofs: dict[
            str, W1GroundedStructuralRelationProof
        ] = {}
        self._lock = threading.RLock()

    @property
    def proofs(self) -> tuple[W1GroundedStructuralRelationProof, ...]:
        with self._lock:
            return tuple(self._proofs[key] for key in sorted(self._proofs))

    def verify(self, proof: W1GroundedStructuralRelationProof) -> None:
        if not isinstance(
            proof.relation, W1GroundedStructuralRelationKind
        ):
            raise ValueError("structural relation kind changed")
        for value, name in (
            (proof.proof_id, "structural relation proof"),
            (
                proof.authority_hmac_sha256,
                "structural relation HMAC",
            ),
            (
                proof.authority_receipt_sha256,
                "structural relation authority",
            ),
            *(
                (value, "structural relation physical source")
                for value in proof.source_receipt_sha256s
            ),
            *(
                (value, "structural relation upstream authority")
                for value in proof.upstream_authority_receipt_sha256s
            ),
            *(
                (value, "structural relation world state")
                for value in proof.world_state_sha256s
            ),
        ):
            _sha256(value, name)
        if (
            not proof.source_receipt_sha256s
            or proof.source_receipt_sha256s
            != tuple(sorted(set(proof.source_receipt_sha256s)))
            or not proof.upstream_authority_receipt_sha256s
            or proof.upstream_authority_receipt_sha256s
            != tuple(sorted(set(
                proof.upstream_authority_receipt_sha256s
            )))
        ):
            raise ValueError("structural relation sources changed")
        for root in proof.root_witnesses:
            root.verify()
        for pose in proof.poses:
            pose.verify()
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in proof.revisions
        ):
            raise ValueError("structural relation revisions changed")

        kind = proof.relation
        if kind is W1GroundedStructuralRelationKind.REFERENT_CONTINUITY:
            if (
                len(proof.root_witnesses) != 2
                or proof.root_witnesses[0].root_id
                != proof.root_witnesses[1].root_id
                or proof.root_witnesses[0].value_sha256
                != proof.root_witnesses[1].value_sha256
                or proof.anonymous_body_continuity_sha256 is not None
                or proof.poses
                or proof.signed_displacement is not None
                or proof.revisions
                or proof.world_state_sha256s
                or len(proof.upstream_authority_receipt_sha256s) != 2
            ):
                raise ValueError("referent continuity changed")
        elif kind is (
            W1GroundedStructuralRelationKind.EMITTER_BODY_CONTINUITY
        ):
            if (
                proof.root_witnesses
                or proof.anonymous_body_continuity_sha256 is None
                or len(proof.poses) != 2
                or proof.signed_displacement is not None
                or len(proof.revisions) != 2
                or proof.revisions[1] <= proof.revisions[0]
                or len(proof.world_state_sha256s) != 2
                or len(proof.upstream_authority_receipt_sha256s) != 2
            ):
                raise ValueError("emitter body continuity changed")
            _sha256(
                proof.anonymous_body_continuity_sha256,
                "anonymous emitter body continuity",
            )
        else:
            if (
                proof.anonymous_body_continuity_sha256 is not None
                or len(proof.poses) != 2
                or proof.signed_displacement
                != _displacement(proof.poses[0], proof.poses[1])
                or len(proof.root_witnesses)
                != self._profile.required_dynamic_root_count
                or tuple(
                    value.root_id for value in proof.root_witnesses
                ) != tuple(sorted(
                    value.root_id for value in proof.root_witnesses
                ))
            ):
                raise ValueError("full action structural relation changed")
            if (
                len(proof.revisions) != 3
                or proof.revisions[1] != proof.revisions[0] + 1
                or proof.revisions[2] != proof.revisions[1] + 1
                or len(proof.world_state_sha256s) != 3
                or len(proof.upstream_authority_receipt_sha256s) != 2
            ):
                raise ValueError("temporal action relation changed")

        payload = proof.payload()
        signature = hmac.new(
            self._proof_key,
            _PROOF_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            proof.proof_id != _digest(payload)
            or not hmac.compare_digest(
                proof.authority_hmac_sha256, signature
            )
            or proof.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("structural relation proof authority changed")

    def _admit(
        self,
        *,
        relation: W1GroundedStructuralRelationKind,
        source_receipts: tuple[str, ...],
        upstream_receipts: tuple[str, ...],
        roots: tuple[GroundingRoot, ...] = (),
        body_continuity: str | None = None,
        poses: tuple[PoseMM, ...] = (),
        displacement: tuple[int, int, int, int] | None = None,
        revisions: tuple[int, ...] = (),
        world_states: tuple[str, ...] = (),
    ) -> W1GroundedStructuralRelationProof:
        provisional = W1GroundedStructuralRelationProof(
            proof_id="0" * 64,
            relation=relation,
            source_receipt_sha256s=tuple(sorted(set(source_receipts))),
            upstream_authority_receipt_sha256s=tuple(sorted(set(
                upstream_receipts
            ))),
            root_witnesses=roots,
            anonymous_body_continuity_sha256=body_continuity,
            poses=poses,
            signed_displacement=displacement,
            revisions=revisions,
            world_state_sha256s=world_states,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        if (
            len(provisional.source_receipt_sha256s)
            != len(source_receipts)
            or len(provisional.upstream_authority_receipt_sha256s)
            != len(upstream_receipts)
        ):
            raise ValueError("structural relation reused an internal source")
        payload = provisional.payload()
        signature = hmac.new(
            self._proof_key,
            _PROOF_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1GroundedStructuralRelationProof(
            proof_id=_digest(payload),
            relation=provisional.relation,
            source_receipt_sha256s=provisional.source_receipt_sha256s,
            upstream_authority_receipt_sha256s=(
                provisional.upstream_authority_receipt_sha256s
            ),
            root_witnesses=provisional.root_witnesses,
            anonymous_body_continuity_sha256=(
                provisional.anonymous_body_continuity_sha256
            ),
            poses=provisional.poses,
            signed_displacement=provisional.signed_displacement,
            revisions=provisional.revisions,
            world_state_sha256s=provisional.world_state_sha256s,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify(result)
        with self._lock:
            if result.proof_id in self._proofs:
                return result
            if any(
                set(value.source_receipt_sha256s).intersection(
                    result.source_receipt_sha256s
                )
                for value in self._proofs.values()
            ):
                raise ValueError(
                    "structural relation proofs reuse a physical source"
                )
            if len(self._proofs) >= self._profile.max_proofs:
                raise RuntimeError(
                    "structural relation proof capacity exhausted"
                )
            staged = dict(self._proofs)
            staged[result.proof_id] = result
            self._encoded(staged)
            self._proofs = staged
        return result

    def admit_referent_continuity(
        self,
        *,
        first_settlement: CausalExperienceSettlement,
        first_root: GroundingRoot,
        second_settlement: CausalExperienceSettlement,
        second_root: GroundingRoot,
    ) -> W1GroundedStructuralRelationProof:
        first_settlement.verify()
        second_settlement.verify()
        first_roots = grounding_roots_from_settlement(first_settlement)
        second_roots = grounding_roots_from_settlement(second_settlement)
        if (
            first_root not in first_roots
            or second_root not in second_roots
            or first_settlement.authority_receipt_sha256
            == second_settlement.authority_receipt_sha256
            or first_root.root_id != second_root.root_id
            or first_root.value_sha256 != second_root.value_sha256
        ):
            raise ValueError(
                "referent continuity lacks independent exact roots"
            )
        return self._admit(
            relation=(
                W1GroundedStructuralRelationKind.REFERENT_CONTINUITY
            ),
            source_receipts=(
                first_settlement.authority_receipt_sha256,
                second_settlement.authority_receipt_sha256,
            ),
            upstream_receipts=(
                first_settlement.authority_receipt_sha256,
                second_settlement.authority_receipt_sha256,
            ),
            roots=(first_root, second_root),
        )

    def admit_emitter_body_continuity(
        self,
        *,
        first: W1RetainedEmitterBodyOccurrence,
        second: W1RetainedEmitterBodyOccurrence,
        world_authority: EmbodimentWorldAuthority,
        emitter_authority: W1AcousticEmitterAuthority,
    ) -> W1GroundedStructuralRelationProof:
        if (
            not isinstance(world_authority, EmbodimentWorldAuthority)
            or not isinstance(
                emitter_authority, W1AcousticEmitterAuthority
            )
            or not emitter_authority.owns_world(world_authority)
        ):
            raise TypeError(
                "emitter continuity requires one W1 world/emitter authority"
            )
        for occurrence in (first, second):
            if not isinstance(
                occurrence, W1RetainedEmitterBodyOccurrence
            ):
                raise TypeError("emitter occurrence is not typed")
            emitter_authority.verify_retained_emission(
                occurrence.emission,
                observation_snapshot=occurrence.observation,
                execution_receipt=occurrence.execution,
            )
        if (
            first.execution.actor_body_id
            != second.execution.actor_body_id
            or first.execution.actor_body_id
            == first.observation.self_body_id
            or first.emission.receipt.authority_receipt_sha256
            == second.emission.receipt.authority_receipt_sha256
        ):
            raise ValueError(
                "emitter body continuity lacks one independent external body"
            )
        body_id = first.execution.actor_body_id
        continuity = hashlib.sha256(
            _BODY_DOMAIN + body_id.encode("utf-8")
        ).hexdigest()
        poses = (
            _body_pose(first.observation, body_id),
            _body_pose(second.observation, body_id),
        )
        return self._admit(
            relation=(
                W1GroundedStructuralRelationKind.EMITTER_BODY_CONTINUITY
            ),
            source_receipts=(
                first.emission.receipt.authority_receipt_sha256,
                first.execution.authority_receipt_sha256,
                second.emission.receipt.authority_receipt_sha256,
                second.execution.authority_receipt_sha256,
            ),
            upstream_receipts=(
                first.emission.receipt.authority_receipt_sha256,
                second.emission.receipt.authority_receipt_sha256,
            ),
            body_continuity=continuity,
            poses=poses,
            revisions=(
                first.observation.revision,
                second.observation.revision,
            ),
            world_states=(
                first.observation.state_sha256,
                second.observation.state_sha256,
            ),
        )

    def admit_pose_region_relation(
        self,
        *,
        lesson: W1VocalSpatialActionLesson,
        lesson_authority: W1VocalSpatialActionLessonAuthority,
    ) -> W1GroundedStructuralRelationProof:
        return self._admit_temporal_action(
            relation=(
                W1GroundedStructuralRelationKind.POSE_REGION_RELATION
            ),
            lesson=lesson,
            lesson_authority=lesson_authority,
        )

    def _admit_temporal_action(
        self,
        *,
        relation: W1GroundedStructuralRelationKind,
        lesson: W1VocalSpatialActionLesson,
        lesson_authority: W1VocalSpatialActionLessonAuthority,
    ) -> W1GroundedStructuralRelationProof:
        lesson_authority.verify(lesson)
        settlement = lesson.spatial_settlement
        return self._admit(
            relation=relation,
            source_receipts=(
                lesson.vocal_execution_receipt_sha256,
                lesson.vocal_evidence_receipt_sha256,
                lesson.vocal_grounding_receipt_sha256,
                lesson.spatial_settlement_receipt_sha256,
                lesson.authority_receipt_sha256,
            ),
            upstream_receipts=(
                lesson.authority_receipt_sha256,
                settlement.authority_receipt_sha256,
            ),
            roots=settlement.full_dynamic_roots,
            poses=(settlement.before_pose, settlement.after_pose),
            displacement=settlement.signed_displacement,
            revisions=(
                lesson.vocal_before_revision,
                lesson.junction_revision,
                lesson.action_after_revision,
            ),
            world_states=(
                lesson.vocal_before_world_state_sha256,
                lesson.junction_world_state_sha256,
                lesson.action_after_world_state_sha256,
            ),
        )

    def admit_action_outcome_affordance(
        self,
        *,
        lesson: W1VocalSpatialActionLesson,
        lesson_authority: W1VocalSpatialActionLessonAuthority,
    ) -> W1GroundedStructuralRelationProof:
        return self._admit_temporal_action(
            relation=(
                W1GroundedStructuralRelationKind
                .ACTION_OUTCOME_AFFORDANCE
            ),
            lesson=lesson,
            lesson_authority=lesson_authority,
        )

    def admit_causal_predecessor(
        self,
        *,
        lesson: W1VocalSpatialActionLesson,
        lesson_authority: W1VocalSpatialActionLessonAuthority,
    ) -> W1GroundedStructuralRelationProof:
        return self._admit_temporal_action(
            relation=(
                W1GroundedStructuralRelationKind.CAUSAL_PREDECESSOR
            ),
            lesson=lesson,
            lesson_authority=lesson_authority,
        )

    def _body(
        self,
        values: dict[str, W1GroundedStructuralRelationProof],
    ) -> dict[str, object]:
        return {
            "proofs": [values[key].record() for key in sorted(values)],
            "resource_profile": self._profile.record(),
            "schema": STRUCTURAL_RELATION_STATE_SCHEMA,
        }

    def _encoded(
        self,
        values: dict[str, W1GroundedStructuralRelationProof],
    ) -> bytes:
        body = self._body(values)
        encoded = _canonical({
            "body": body,
            "schema": STRUCTURAL_RELATION_ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("structural relation state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._proofs)

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
    ) -> "W1GroundedStructuralRelationOwner":
        if not isinstance(encoded, bytes):
            raise TypeError("structural relation state must be bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "structural relation state is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema")
            != STRUCTURAL_RELATION_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
            or not isinstance(envelope.get("body"), Mapping)
        ):
            raise ValueError("structural relation envelope changed")
        body = envelope["body"]
        if (
            set(body) != {"proofs", "resource_profile", "schema"}
            or body.get("schema") != STRUCTURAL_RELATION_STATE_SCHEMA
            or not isinstance(body.get("proofs"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("structural relation state changed")
        raw_profile = body["resource_profile"]
        profile = W1GroundedStructuralRelationProfile(
            profile_id=raw_profile.get("profile_id"),
            max_proofs=raw_profile.get("max_proofs"),
            required_dynamic_root_count=raw_profile.get(
                "required_dynamic_root_count"
            ),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
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
            raise ValueError("structural relation state HMAC changed")
        restored: dict[
            str, W1GroundedStructuralRelationProof
        ] = {}
        used_sources: set[str] = set()
        for raw in body["proofs"]:
            if not isinstance(raw, Mapping):
                raise ValueError("structural relation proof record changed")
            roots = tuple(
                GroundingRoot(
                    root_id=value.get("root_id"),
                    value_sha256=value.get("value_sha256"),
                    value_json=value.get("value_json"),
                )
                for value in raw.get("root_witnesses", ())
            )
            poses = tuple(
                PoseMM(
                    PositionMM(
                        value.get("position", {}).get("x_mm"),
                        value.get("position", {}).get("y_mm"),
                        value.get("position", {}).get("z_mm"),
                    ),
                    value.get("heading_millidegrees"),
                )
                for value in raw.get("poses", ())
            )
            raw_displacement = raw.get("signed_displacement")
            proof = W1GroundedStructuralRelationProof(
                proof_id=raw.get("proof_id"),
                relation=W1GroundedStructuralRelationKind(
                    raw.get("relation")
                ),
                source_receipt_sha256s=tuple(
                    raw.get("source_receipt_sha256s", ())
                ),
                upstream_authority_receipt_sha256s=tuple(
                    raw.get(
                        "upstream_authority_receipt_sha256s", ()
                    )
                ),
                root_witnesses=roots,
                anonymous_body_continuity_sha256=raw.get(
                    "anonymous_body_continuity_sha256"
                ),
                poses=poses,
                signed_displacement=(
                    tuple(raw_displacement)
                    if raw_displacement is not None
                    else None
                ),
                revisions=tuple(raw.get("revisions", ())),
                world_state_sha256s=tuple(
                    raw.get("world_state_sha256s", ())
                ),
                authority_hmac_sha256=raw.get(
                    "authority_hmac_sha256"
                ),
                authority_receipt_sha256=raw.get(
                    "authority_receipt_sha256"
                ),
            )
            owner.verify(proof)
            if (
                proof.proof_id in restored
                or used_sources.intersection(
                    proof.source_receipt_sha256s
                )
            ):
                raise ValueError(
                    "restored structural relation sources repeat"
                )
            restored[proof.proof_id] = proof
            used_sources.update(proof.source_receipt_sha256s)
        owner._proofs = restored
        if owner.snapshot_encoded() != encoded:
            raise ValueError(
                "structural relation state is not canonical"
            )
        return owner

    def status(self) -> dict[str, object]:
        with self._lock:
            counts = {
                kind.value: sum(
                    value.relation is kind
                    for value in self._proofs.values()
                )
                for kind in W1GroundedStructuralRelationKind
            }
            return {
                "capacity": self._profile.max_proofs,
                "capacity_exhausted": (
                    len(self._proofs) >= self._profile.max_proofs
                ),
                "count": len(self._proofs),
                "relation_counts": counts,
                "state_bytes": len(self._encoded(self._proofs)),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }


__all__ = [
    "STRUCTURAL_RELATION_ENVELOPE_SCHEMA",
    "STRUCTURAL_RELATION_PROFILE_SCHEMA",
    "STRUCTURAL_RELATION_PROOF_SCHEMA",
    "STRUCTURAL_RELATION_STATE_SCHEMA",
    "W1GroundedStructuralRelationKind",
    "W1GroundedStructuralRelationOwner",
    "W1GroundedStructuralRelationProfile",
    "W1GroundedStructuralRelationProof",
    "W1RetainedEmitterBodyOccurrence",
]
