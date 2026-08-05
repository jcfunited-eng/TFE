"""Fresh unlabeled external-pressure challenge causing exact self motion."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
    SettledExperienceSourceKind,
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
    W1PhysicalEvidenceReceipt,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidence,
    W1BinauralGroundingEvidenceAuthority,
)
from dsf_ai_service.substrate.w1_signed_spatial_action_settlement import (
    W1_SIGNED_SPATIAL_ACTION_CONSUMER_ID,
    W1SignedSpatialActionSettlementAuthority,
)
from dsf_ai_service.substrate.w1_speech_commands_tutor_plan import (
    W1TutoredSpeechPressure,
)


W1_FRESH_SPATIAL_VOCAL_CHALLENGE_SCHEMA = (
    "guala.w1.fresh_spatial_vocal_challenge.v1"
)
_DOMAIN = b"guala-w1-fresh-spatial-vocal-challenge-v1\0"
_PREPARED_DOMAIN = (
    b"guala-w1-fresh-spatial-vocal-challenge-prepared-v1\0"
)
W1_FRESH_SPATIAL_VOCAL_CONSUMER_ID = (
    "w1-fresh-spatial-vocal-challenge.vocal"
)
W1_FRESH_SPATIAL_ACTION_CONSUMER_ID = (
    "w1-fresh-spatial-vocal-challenge.action"
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _self_pose(execution: ActionExecutionReceipt) -> PoseMM:
    matches = tuple(
        body.pose for body in execution.after.bodies
        if body.body_id == execution.after.self_body_id
    )
    if len(matches) != 1:
        raise ValueError("W1 challenge self body is not unique")
    return matches[0]


@dataclass(frozen=True, slots=True)
class W1FreshSpatialVocalChallenge:
    state: str
    reason: str
    distinction_receipt_sha256: str
    challenge_pressure_receipt_sha256: str
    challenge_pressure_source_file_sha256: str
    challenge_emission_receipt_sha256: str
    challenge_vocal_execution_receipt_sha256: str
    challenge_vocal_evidence_receipt_sha256: str
    challenge_vocal_grounding_receipt_sha256: str
    resolved_displacement: tuple[int, int, int, int] | None
    action_execution_receipt_sha256: str | None
    spatial_settlement_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_execution_receipt_sha256": (
                self.action_execution_receipt_sha256
            ),
            "challenge_emission_receipt_sha256": (
                self.challenge_emission_receipt_sha256
            ),
            "challenge_pressure_receipt_sha256": (
                self.challenge_pressure_receipt_sha256
            ),
            "challenge_pressure_source_file_sha256": (
                self.challenge_pressure_source_file_sha256
            ),
            "challenge_vocal_evidence_receipt_sha256": (
                self.challenge_vocal_evidence_receipt_sha256
            ),
            "challenge_vocal_execution_receipt_sha256": (
                self.challenge_vocal_execution_receipt_sha256
            ),
            "challenge_vocal_grounding_receipt_sha256": (
                self.challenge_vocal_grounding_receipt_sha256
            ),
            "distinction_receipt_sha256": self.distinction_receipt_sha256,
            "reason": self.reason,
            "resolved_displacement": (
                list(self.resolved_displacement)
                if self.resolved_displacement is not None else None
            ),
            "schema": W1_FRESH_SPATIAL_VOCAL_CHALLENGE_SCHEMA,
            "spatial_settlement_receipt_sha256": (
                self.spatial_settlement_receipt_sha256
            ),
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class W1PreparedFreshSpatialVocalAction:
    distinction: W1AnonymousSpatialVocalDistinction
    pressure: W1TutoredSpeechPressure
    emission: AuthenticatedW1AcousticEmission
    vocal_execution: ActionExecutionReceipt
    vocal_evidence: W1PhysicalEvidenceReceipt
    vocal_grounding: W1BinauralGroundingEvidence
    vocal_parent_custody_receipt_sha256: str
    vocal_custody_capability_receipt_sha256: str
    resolved_displacement: tuple[int, int, int, int]
    action_execution: ActionExecutionReceipt
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_execution_receipt_sha256": (
                self.action_execution.authority_receipt_sha256
            ),
            "distinction_receipt_sha256": (
                self.distinction.authority_receipt_sha256
            ),
            "pressure_receipt_sha256": (
                self.pressure.authority_receipt_sha256
            ),
            "resolved_displacement": list(self.resolved_displacement),
            "schema": (
                "guala.w1.fresh_spatial_vocal_challenge.prepared.v1"
            ),
            "vocal_custody_capability_receipt_sha256": (
                self.vocal_custody_capability_receipt_sha256
            ),
            "vocal_emission_receipt_sha256": (
                self.emission.receipt.authority_receipt_sha256
            ),
            "vocal_execution_receipt_sha256": (
                self.vocal_execution.authority_receipt_sha256
            ),
            "vocal_grounding_receipt_sha256": (
                self.vocal_grounding.authority_receipt_sha256
            ),
            "vocal_parent_custody_receipt_sha256": (
                self.vocal_parent_custody_receipt_sha256
            ),
        }


class W1FreshSpatialVocalChallengeExecutor:
    """Resolve one fresh q field and enact its anonymous signed relation."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        tutor_pressure_key: bytes | str,
        max_challenges: int,
        self_port_id: str,
        world_authority: EmbodimentWorldAuthority,
        emitter_authority: W1AcousticEmitterAuthority,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
        spatial_authority: W1SignedSpatialActionSettlementAuthority,
        relation_authority: W1AnonymousSpatialVocalRelationOwner,
        provenance_authority: (
            W1AnonymousSpatialVocalProvenanceAuthority
        ),
    ) -> None:
        key = authority_key.encode() if isinstance(authority_key, str) else bytes(
            authority_key
        )
        if (
            not 32 <= len(key) <= 4_096
            or isinstance(max_challenges, bool)
            or not isinstance(max_challenges, int)
            or max_challenges <= 0
            or not isinstance(self_port_id, str)
            or not self_port_id
        ):
            raise ValueError("W1 fresh spatial challenge boundary changed")
        self._key = hashlib.sha256(_DOMAIN + hashlib.sha256(key).digest()).digest()
        self._tutor_key = tutor_pressure_key
        self._max = max_challenges
        self._self_port = self_port_id
        self._world = world_authority
        self._emitter = emitter_authority
        self._grounding = grounding_authority
        self._spatial = spatial_authority
        self._relations = relation_authority
        self._provenance = provenance_authority
        self._challenges: dict[str, W1FreshSpatialVocalChallenge] = {}
        self._lock = threading.RLock()

    def _result(
        self,
        *,
        state: str,
        reason: str,
        distinction: W1AnonymousSpatialVocalDistinction,
        pressure: W1TutoredSpeechPressure,
        emission: AuthenticatedW1AcousticEmission,
        vocal_execution: ActionExecutionReceipt,
        vocal_evidence: W1PhysicalEvidenceReceipt,
        vocal_grounding: W1BinauralGroundingEvidence,
        displacement: tuple[int, int, int, int] | None,
        action_execution_sha256: str | None,
        spatial_settlement_sha256: str | None,
    ) -> W1FreshSpatialVocalChallenge:
        provisional = W1FreshSpatialVocalChallenge(
            state=state,
            reason=reason,
            distinction_receipt_sha256=(
                distinction.authority_receipt_sha256
            ),
            challenge_pressure_receipt_sha256=(
                pressure.authority_receipt_sha256
            ),
            challenge_pressure_source_file_sha256=(
                pressure.source_file_sha256
            ),
            challenge_emission_receipt_sha256=(
                emission.receipt.authority_receipt_sha256
            ),
            challenge_vocal_execution_receipt_sha256=(
                vocal_execution.authority_receipt_sha256
            ),
            challenge_vocal_evidence_receipt_sha256=(
                vocal_evidence.authority_receipt_sha256
            ),
            challenge_vocal_grounding_receipt_sha256=(
                vocal_grounding.authority_receipt_sha256
            ),
            resolved_displacement=displacement,
            action_execution_receipt_sha256=action_execution_sha256,
            spatial_settlement_receipt_sha256=spatial_settlement_sha256,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._key, _DOMAIN + _canonical(payload), hashlib.sha256
        ).hexdigest()
        result = W1FreshSpatialVocalChallenge(
            state=provisional.state,
            reason=provisional.reason,
            distinction_receipt_sha256=(
                provisional.distinction_receipt_sha256
            ),
            challenge_pressure_receipt_sha256=(
                provisional.challenge_pressure_receipt_sha256
            ),
            challenge_pressure_source_file_sha256=(
                provisional.challenge_pressure_source_file_sha256
            ),
            challenge_emission_receipt_sha256=(
                provisional.challenge_emission_receipt_sha256
            ),
            challenge_vocal_execution_receipt_sha256=(
                provisional.challenge_vocal_execution_receipt_sha256
            ),
            challenge_vocal_evidence_receipt_sha256=(
                provisional.challenge_vocal_evidence_receipt_sha256
            ),
            challenge_vocal_grounding_receipt_sha256=(
                provisional.challenge_vocal_grounding_receipt_sha256
            ),
            resolved_displacement=provisional.resolved_displacement,
            action_execution_receipt_sha256=(
                provisional.action_execution_receipt_sha256
            ),
            spatial_settlement_receipt_sha256=(
                provisional.spatial_settlement_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature, "payload": payload
            }),
        )
        with self._lock:
            if len(self._challenges) >= self._max:
                raise RuntimeError("W1 fresh spatial challenge capacity exhausted")
            self._challenges[result.authority_receipt_sha256] = result
        return result

    def prepare(
        self,
        *,
        distinction: W1AnonymousSpatialVocalDistinction,
        training_lessons: tuple[W1AnonymousSpatialVocalLesson, ...],
        training_provenances: tuple[
            W1AnonymousSpatialVocalProvenance, ...
        ],
        pressure: W1TutoredSpeechPressure,
        emission: AuthenticatedW1AcousticEmission,
        vocal_custody_authority: SettledExperienceCustodyAuthority,
        vocal_custody_capability: SettledExperienceConsumerCapability,
        vocal_grounding: W1BinauralGroundingEvidence,
        action_duration_microseconds: int,
    ) -> (
        W1PreparedFreshSpatialVocalAction
        | W1FreshSpatialVocalChallenge
    ):
        self._relations.verify_distinction(distinction)
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
        source_files = {
            value.pressure_source_file_sha256
            for value in training_provenances
        }
        if (
            lesson_receipts
            != set(distinction.source_lesson_receipt_sha256s)
            or provenance_lessons != lesson_receipts
            or len(source_files) != len(training_provenances)
        ):
            raise ValueError("W1 challenge training provenance changed")
        pressure.verify(self._tutor_key)
        if pressure.source_file_sha256 in source_files:
            raise ValueError("W1 challenge reused a training recording")
        if (
            not isinstance(
                vocal_custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                vocal_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or vocal_custody_capability.consumer_id
            != W1_FRESH_SPATIAL_VOCAL_CONSUMER_ID
        ):
            raise ValueError(
                "W1 challenge requires its purpose-bound vocal custody"
            )
        vocal_view = vocal_custody_authority.open_child(
            vocal_custody_capability
        )
        vocal_execution = vocal_view.world_execution
        evidence = vocal_view.physical_evidence_receipt
        if (
            vocal_view.source_kind
            is not SettledExperienceSourceKind.PHYSICAL_EVIDENCE
            or vocal_execution is None
            or evidence is None
        ):
            raise ValueError(
                "W1 challenge requires applied physical vocal custody"
            )
        self._emitter.verify_emission(
            emission,
            observation_snapshot=vocal_execution.after,
            execution_receipt=vocal_execution,
        )
        self._grounding.verify(vocal_grounding)
        if (
            pressure.pcm_s16le != emission.pcm_s16le
            or evidence.world_execution_receipt_sha256
            != vocal_execution.authority_receipt_sha256
            or evidence.acoustic_emission_receipt_sha256s
            != (emission.receipt.authority_receipt_sha256,)
            or vocal_grounding.causal_settlement_receipt_sha256
            != vocal_view.causal_settlement.authority_receipt_sha256
            or vocal_view.binaural_receptor_settlement is None
            or vocal_grounding.receptor_settlement_receipt_sha256
            != vocal_view.binaural_receptor_settlement
            .authority_receipt_sha256
            or self._world.observation_snapshot() != vocal_execution.after
        ):
            raise ValueError("W1 challenge vocal physical source chain changed")
        resolved = self._relations.resolve(
            distinction, vocal_grounding.activations
        )
        if len(resolved) != 1:
            return self._result(
                state="unknown" if not resolved else "ambiguous",
                reason=(
                    "no_exact_spatial_relation"
                    if not resolved else "multiple_exact_spatial_relations"
                ),
                distinction=distinction,
                pressure=pressure,
                emission=emission,
                vocal_execution=vocal_execution,
                vocal_evidence=evidence,
                vocal_grounding=vocal_grounding,
                displacement=None,
                action_execution_sha256=None,
                spatial_settlement_sha256=None,
            )
        relation = resolved[0]
        before_pose = _self_pose(vocal_execution)
        if _digest(before_pose.as_record()) != relation.before_pose_sha256:
            raise ValueError("W1 challenge before pose changed")
        dx, dy, dz, dyaw = relation.signed_displacement
        heading = before_pose.heading_millidegrees + dyaw
        if not 0 <= heading <= 359_999:
            raise ValueError("W1 challenge target heading escaped its boundary")
        target = PoseMM(
            PositionMM(
                before_pose.position.x + dx,
                before_pose.position.y + dy,
                before_pose.position.z + dz,
            ),
            heading,
        )
        action = self._world.execute_port_command(
            port_id=self._self_port,
            command_payload=encode_command(MoveCommand(
                target_pose=target,
                duration_microseconds=action_duration_microseconds,
            )),
            causal_intent_receipt_sha256=_digest({
                "distinction_receipt_sha256": (
                    distinction.authority_receipt_sha256
                ),
                "resolved_displacement": list(relation.signed_displacement),
                "vocal_grounding_receipt_sha256": (
                    vocal_grounding.authority_receipt_sha256
                ),
            }),
            expected_revision=vocal_execution.after.revision,
        )
        if action.disposition != "applied":
            raise RuntimeError(
                f"W1 resolved spatial action was rejected: {action.reason}"
            )
        provisional = W1PreparedFreshSpatialVocalAction(
            distinction=distinction,
            pressure=pressure,
            emission=emission,
            vocal_execution=vocal_execution,
            vocal_evidence=evidence,
            vocal_grounding=vocal_grounding,
            vocal_parent_custody_receipt_sha256=(
                vocal_view.parent_custody_receipt_sha256
            ),
            vocal_custody_capability_receipt_sha256=(
                vocal_custody_capability.authority_receipt_sha256
            ),
            resolved_displacement=relation.signed_displacement,
            action_execution=action,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _PREPARED_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return W1PreparedFreshSpatialVocalAction(
            distinction=provisional.distinction,
            pressure=provisional.pressure,
            emission=provisional.emission,
            vocal_execution=provisional.vocal_execution,
            vocal_evidence=provisional.vocal_evidence,
            vocal_grounding=provisional.vocal_grounding,
            vocal_parent_custody_receipt_sha256=(
                provisional.vocal_parent_custody_receipt_sha256
            ),
            vocal_custody_capability_receipt_sha256=(
                provisional.vocal_custody_capability_receipt_sha256
            ),
            resolved_displacement=provisional.resolved_displacement,
            action_execution=provisional.action_execution,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def commit(
        self,
        *,
        prepared: W1PreparedFreshSpatialVocalAction,
        action_custody_authority: SettledExperienceCustodyAuthority,
        action_custody_capability: SettledExperienceConsumerCapability,
        spatial_custody_capability: SettledExperienceConsumerCapability,
    ) -> W1FreshSpatialVocalChallenge:
        if not isinstance(prepared, W1PreparedFreshSpatialVocalAction):
            raise TypeError("W1 challenge prepared action is not typed")
        payload = prepared.payload()
        expected_hmac = hmac.new(
            self._key,
            _PREPARED_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                prepared.authority_hmac_sha256,
            )
            or prepared.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
            or not isinstance(
                action_custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                action_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or action_custody_capability.consumer_id
            != W1_FRESH_SPATIAL_ACTION_CONSUMER_ID
            or not isinstance(
                spatial_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or spatial_custody_capability.consumer_id
            != W1_SIGNED_SPATIAL_ACTION_CONSUMER_ID
        ):
            raise ValueError(
                "W1 challenge action lacks purpose-bound custody"
            )
        action_view = action_custody_authority.open_child(
            action_custody_capability
        )
        if (
            action_view.source_kind
            is not SettledExperienceSourceKind.PHYSICAL_EVIDENCE
            or action_view.world_execution
            != prepared.action_execution
            or action_view.physical_evidence_receipt is None
            or action_view.physical_evidence_receipt
            .acoustic_emission_receipt_sha256s
        ):
            raise ValueError(
                "W1 challenge action custody names another outcome"
            )
        self._relations.verify_distinction(prepared.distinction)
        self._grounding.verify(prepared.vocal_grounding)
        resolved = self._relations.resolve(
            prepared.distinction,
            prepared.vocal_grounding.activations,
        )
        if (
            len(resolved) != 1
            or resolved[0].signed_displacement
            != prepared.resolved_displacement
        ):
            raise ValueError(
                "W1 challenge prepared relation changed before custody"
            )
        spatial = self._spatial.settle_custodied(
            custody_authority=action_custody_authority,
            custody_capability=spatial_custody_capability,
        )
        if (
            spatial.signed_displacement != prepared.resolved_displacement
            or spatial.full_dynamic_roots
            not in self._relations.relation_action_fields(resolved[0])
        ):
            raise ValueError("W1 challenge action outcome changed")
        return self._result(
            state="executed",
            reason="fresh_q_relation_enacted",
            distinction=prepared.distinction,
            pressure=prepared.pressure,
            emission=prepared.emission,
            vocal_execution=prepared.vocal_execution,
            vocal_evidence=prepared.vocal_evidence,
            vocal_grounding=prepared.vocal_grounding,
            displacement=prepared.resolved_displacement,
            action_execution_sha256=(
                prepared.action_execution.authority_receipt_sha256
            ),
            spatial_settlement_sha256=spatial.authority_receipt_sha256,
        )


__all__ = [
    "W1_FRESH_SPATIAL_ACTION_CONSUMER_ID",
    "W1_FRESH_SPATIAL_VOCAL_CONSUMER_ID",
    "W1FreshSpatialVocalChallenge",
    "W1FreshSpatialVocalChallengeExecutor",
    "W1PreparedFreshSpatialVocalAction",
]
