"""Transactional full-field lived-turn learning and motor proposal authority."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingResolution,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.grounded_turn_conversation import (
    GroundedTurnConstruction,
    GroundedTurnConversationOwner,
    GroundedTurnEpisode,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalHearingReceipt,
    SelfVocalPCMExemplar,
    SelfVocalPCMMotorOwner,
)


PROFILE_SCHEMA = "guala.lived_conversation_learning.profile.v1"
PREPARED_SCHEMA = "guala.lived_conversation_learning.prepared.v1"
PROPOSAL_SCHEMA = "guala.lived_conversation_learning.motor_proposal.v1"
STATE_SCHEMA = "guala.lived_conversation_learning.state.v1"
_PREPARED_DOMAIN = b"guala-lived-conversation-prepared-v1\0"
_PROPOSAL_DOMAIN = b"guala-lived-conversation-proposal-v1\0"
_STATE_DOMAIN = b"guala-lived-conversation-state-v1\0"
_HEX = frozenset("0123456789abcdef")


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


def _key(value: bytes | str) -> bytes:
    raw = value.encode() if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4096:
        raise ValueError("lived conversation authority key changed")
    return hashlib.sha256(b"guala-lived-conversation-v1\0" + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(item not in _HEX for item in value)
    ):
        raise ValueError(f"{label} changed")
    return value


@dataclass(frozen=True, slots=True)
class LivedConversationLearningProfile:
    profile_id: str
    max_proposal_witness_bytes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_proposal_witness_bytes: int,
        max_state_bytes: int,
    ) -> "LivedConversationLearningProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or len(profile_id.encode()) > 256
            or isinstance(max_proposal_witness_bytes, bool)
            or not isinstance(max_proposal_witness_bytes, int)
            or max_proposal_witness_bytes <= 0
            or isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or max_state_bytes <= max_proposal_witness_bytes
        ):
            raise ValueError("lived conversation profile boundary changed")
        provisional = cls(
            profile_id,
            max_proposal_witness_bytes,
            max_state_bytes,
            "0" * 64,
        )
        return cls(
            profile_id,
            max_proposal_witness_bytes,
            max_state_bytes,
            _digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_proposal_witness_bytes": self.max_proposal_witness_bytes,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        expected = type(self).create(
            profile_id=self.profile_id,
            max_proposal_witness_bytes=self.max_proposal_witness_bytes,
            max_state_bytes=self.max_state_bytes,
        )
        if self != expected:
            raise ValueError("lived conversation profile changed")


@dataclass(frozen=True, slots=True)
class PreparedLivedConversationLearning:
    request_id: str
    expected_episode_id: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "expected_episode_id": self.expected_episode_id,
            "request_id": self.request_id,
            "schema": PREPARED_SCHEMA,
        }


@dataclass(frozen=True, slots=True)
class LivedConversationLearningResult:
    episode: GroundedTurnEpisode
    construction: GroundedTurnConstruction | None


@dataclass(frozen=True, slots=True)
class ConversationalMotorProposal:
    proposal_id: str
    cue_structure_id: str
    construction_id: str
    motor_id: str
    motor_pcm_sha256: str
    proof_witness_json: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "construction_id": self.construction_id,
            "cue_structure_id": self.cue_structure_id,
            "motor_id": self.motor_id,
            "motor_pcm_sha256": self.motor_pcm_sha256,
            "proof_witness_json": self.proof_witness_json,
            "proposal_id": self.proposal_id,
            "schema": PROPOSAL_SCHEMA,
        }


@dataclass(frozen=True, slots=True)
class _Inputs:
    prompt_resolution: GroundingResolution
    prompt_settlement: CausalExperienceSettlement
    response_exemplar: SelfVocalPCMExemplar
    self_hearing: SelfVocalHearingReceipt
    outcome_settlement: CausalExperienceSettlement


@dataclass(frozen=True, slots=True)
class _Prepared:
    public: PreparedLivedConversationLearning
    inputs: _Inputs
    baseline: bytes
    expected: LivedConversationLearningResult


class LivedConversationLearningCoordinator:
    """Own one active exact learning preparation and authenticated proposals."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: LivedConversationLearningProfile,
        turn_owner: GroundedTurnConversationOwner,
        motor_owner: SelfVocalPCMMotorOwner,
    ) -> None:
        profile.verify()
        if not isinstance(turn_owner, GroundedTurnConversationOwner):
            raise TypeError("lived conversation requires its turn owner")
        if not isinstance(motor_owner, SelfVocalPCMMotorOwner):
            raise TypeError("lived conversation requires its motor owner")
        root = _key(authority_key)
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._proposal_key = hashlib.sha256(
            _PROPOSAL_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._turns = turn_owner
        self._motors = motor_owner
        self._prepared: _Prepared | None = None
        self._lock = threading.RLock()

    @staticmethod
    def _verify_full_field(episode: GroundedTurnEpisode) -> None:
        for element in episode.cue.elements:
            decoded = json.loads(element.root.value_json)
            tuples = decoded.get("field_tuples")
            if not isinstance(tuples, list) or not tuples:
                raise ValueError(
                    "lived conversation cue lost its explicit DSF field"
                )
            if any(
                tuple(name for name, _value in item["fields"])
                != DSF_FIELD_ORDER
                for item in tuples
            ):
                raise ValueError(
                    "lived conversation cue changed D/M/R/U/C/P/B"
                )

    def _admit(self, inputs: _Inputs) -> LivedConversationLearningResult:
        episode = self._turns.admit_turn(
            prompt_resolution=inputs.prompt_resolution,
            prompt_settlement=inputs.prompt_settlement,
            response_exemplar=inputs.response_exemplar,
            self_hearing=inputs.self_hearing,
            outcome_settlement=inputs.outcome_settlement,
            motor_owner=self._motors,
        )
        self._verify_full_field(episode)
        construction = self._turns.settle_construction(
            episode.cue.structure_id
        )
        return LivedConversationLearningResult(episode, construction)

    def _handle(
        self, request_id: str, episode_id: str
    ) -> PreparedLivedConversationLearning:
        provisional = PreparedLivedConversationLearning(
            request_id, episode_id, "0" * 64
        )
        signature = hmac.new(
            self._prepared_key,
            _PREPARED_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return PreparedLivedConversationLearning(
            request_id, episode_id, signature
        )

    def _verify_handle(
        self, value: PreparedLivedConversationLearning
    ) -> None:
        if not isinstance(value, PreparedLivedConversationLearning):
            raise TypeError("lived conversation preparation is not typed")
        _sha(value.request_id, "learning request")
        _sha(value.expected_episode_id, "learning episode")
        expected = self._handle(
            value.request_id, value.expected_episode_id
        )
        if expected != value:
            raise ValueError("lived conversation preparation changed")

    def prepare(
        self,
        *,
        prompt_resolution: GroundingResolution,
        prompt_settlement: CausalExperienceSettlement,
        response_exemplar: SelfVocalPCMExemplar,
        self_hearing: SelfVocalHearingReceipt,
        outcome_settlement: CausalExperienceSettlement,
    ) -> PreparedLivedConversationLearning:
        inputs = _Inputs(
            prompt_resolution,
            prompt_settlement,
            response_exemplar,
            self_hearing,
            outcome_settlement,
        )
        request_id = _digest({
            "motor_id": response_exemplar.motor_id,
            "outcome": outcome_settlement.authority_receipt_sha256,
            "prompt": prompt_settlement.authority_receipt_sha256,
            "self_hearing": self_hearing.authority_receipt_sha256,
        })
        with self._lock, self._turns._lock:
            if self._prepared is not None:
                if self._prepared.public.request_id == request_id:
                    return self._prepared.public
                raise RuntimeError(
                    "lived conversation already has a preparation"
                )
            baseline = self._turns.snapshot_encoded()
            episodes = dict(self._turns._episodes)
            constructions = dict(self._turns._constructions)
            try:
                expected = self._admit(inputs)
            finally:
                self._turns._episodes = episodes
                self._turns._constructions = constructions
                if self._turns.snapshot_encoded() != baseline:
                    raise RuntimeError(
                        "lived conversation prepare rollback changed bytes"
                    )
            public = self._handle(
                request_id, expected.episode.episode_id
            )
            self._prepared = _Prepared(
                public, inputs, baseline, expected
            )
            return public

    def commit(
        self, prepared: PreparedLivedConversationLearning
    ) -> LivedConversationLearningResult:
        self._verify_handle(prepared)
        with self._lock, self._turns._lock:
            active = self._prepared
            if active is None or active.public != prepared:
                existing = next(
                    (
                        value for value in self._turns.episodes
                        if value.episode_id
                        == prepared.expected_episode_id
                    ),
                    None,
                )
                if existing is None:
                    raise ValueError(
                        "lived conversation preparation is not active"
                    )
                construction = next(
                    (
                        value for value in self._turns.constructions
                        if value.cue_structure_id
                        == existing.cue.structure_id
                    ),
                    None,
                )
                return LivedConversationLearningResult(
                    existing, construction
                )
            if self._turns.snapshot_encoded() != active.baseline:
                raise RuntimeError(
                    "lived conversation state changed after prepare"
                )
            episodes = dict(self._turns._episodes)
            constructions = dict(self._turns._constructions)
            try:
                result = self._admit(active.inputs)
                if result != active.expected:
                    raise RuntimeError(
                        "lived conversation commit diverged from prepare"
                    )
                self.encoded_snapshot()
            except BaseException:
                self._turns._episodes = episodes
                self._turns._constructions = constructions
                if self._turns.snapshot_encoded() != active.baseline:
                    raise RuntimeError(
                        "lived conversation commit rollback changed bytes"
                    )
                raise
            self._prepared = None
            return result

    def rollback(
        self, prepared: PreparedLivedConversationLearning
    ) -> bool:
        self._verify_handle(prepared)
        with self._lock:
            if self._prepared is None:
                return False
            if self._prepared.public != prepared:
                raise ValueError(
                    "lived conversation preparation is not active"
                )
            if self._turns.snapshot_encoded() != self._prepared.baseline:
                raise RuntimeError(
                    "lived conversation state changed after prepare"
                )
            self._prepared = None
            return True

    def propose(
        self, prompt_resolution: GroundingResolution
    ) -> ConversationalMotorProposal:
        resolution = self._turns.resolve_reply(prompt_resolution)
        if resolution.state != "resolved" or resolution.motor_id is None:
            raise ValueError("lived conversation cue is not uniquely learned")
        exemplar = next(
            (
                value for value in self._motors.exemplars
                if value.motor_id == resolution.motor_id
            ),
            None,
        )
        if exemplar is None:
            raise ValueError("learned conversational motor is unavailable")
        self._motors.verify_exemplar(exemplar)
        construction = next(
            value for value in self._turns.constructions
            if value.construction_id == resolution.construction_id
        )
        proofs = tuple(
            value for value in self._turns.episodes
            if value.episode_id in construction.proof_episode_ids
        )
        for proof in proofs:
            self._verify_full_field(proof)
        witness = {
            "construction": construction.payload(),
            "proof_episodes": [value.payload() for value in proofs],
            "schema": "guala.lived_conversation_learning.proof.v1",
        }
        encoded = _canonical(witness)
        if len(encoded) > self._profile.max_proposal_witness_bytes:
            raise RuntimeError(
                "conversational motor proposal witness capacity exhausted"
            )
        pcm_sha = hashlib.sha256(exemplar.pcm_s16le).hexdigest()
        identity = {
            "construction_id": construction.construction_id,
            "cue_structure_id": resolution.cue_structure_id,
            "motor_id": exemplar.motor_id,
            "motor_pcm_sha256": pcm_sha,
            "proof_witness_sha256": hashlib.sha256(encoded).hexdigest(),
        }
        proposal_id = _digest(identity)
        provisional = ConversationalMotorProposal(
            proposal_id,
            resolution.cue_structure_id,
            construction.construction_id,
            exemplar.motor_id,
            pcm_sha,
            encoded.decode(),
            "0" * 64,
            "0" * 64,
        )
        signature = hmac.new(
            self._proposal_key,
            _PROPOSAL_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        proposal = ConversationalMotorProposal(
            proposal_id,
            provisional.cue_structure_id,
            provisional.construction_id,
            provisional.motor_id,
            pcm_sha,
            provisional.proof_witness_json,
            signature,
            _digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify_proposal(proposal)
        return proposal

    def verify_proposal(
        self, proposal: ConversationalMotorProposal
    ) -> None:
        if not isinstance(proposal, ConversationalMotorProposal):
            raise TypeError("conversational motor proposal is not typed")
        for value, label in (
            (proposal.proposal_id, "motor proposal"),
            (proposal.cue_structure_id, "proposal cue"),
            (proposal.construction_id, "proposal construction"),
            (proposal.motor_id, "proposal motor"),
            (proposal.motor_pcm_sha256, "proposal PCM"),
            (proposal.authority_hmac_sha256, "proposal HMAC"),
            (proposal.authority_receipt_sha256, "proposal authority"),
        ):
            _sha(value, label)
        try:
            witness = json.loads(proposal.proof_witness_json)
        except json.JSONDecodeError as error:
            raise ValueError("motor proposal proof is unreadable") from error
        encoded = _canonical(witness)
        identity = {
            "construction_id": proposal.construction_id,
            "cue_structure_id": proposal.cue_structure_id,
            "motor_id": proposal.motor_id,
            "motor_pcm_sha256": proposal.motor_pcm_sha256,
            "proof_witness_sha256": hashlib.sha256(encoded).hexdigest(),
        }
        signature = hmac.new(
            self._proposal_key,
            _PROPOSAL_DOMAIN + _canonical(proposal.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            encoded.decode() != proposal.proof_witness_json
            or len(encoded) > self._profile.max_proposal_witness_bytes
            or proposal.proposal_id != _digest(identity)
            or not hmac.compare_digest(
                signature, proposal.authority_hmac_sha256
            )
            or proposal.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": proposal.payload(),
            })
        ):
            raise ValueError("conversational motor proposal changed")

    def encoded_snapshot(self) -> bytes:
        turn_state = self._turns.snapshot_encoded()
        body = {
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
            "turn_state_base64": base64.b64encode(turn_state).decode(),
        }
        encoded = _canonical({
            "body": body,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError(
                "lived conversation coordinator state capacity exhausted"
            )
        return encoded

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
        motor_owner: SelfVocalPCMMotorOwner,
    ) -> "LivedConversationLearningCoordinator":
        envelope = json.loads(encoded)
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {"body", "state_hmac_sha256"}
            or _canonical(envelope) != encoded
        ):
            raise ValueError("lived conversation state changed")
        body = envelope["body"]
        raw = body["profile"]
        profile = LivedConversationLearningProfile(
            raw["profile_id"],
            raw["max_proposal_witness_bytes"],
            raw["max_state_bytes"],
            raw["authority_receipt_sha256"],
        )
        profile.verify()
        turn_state = base64.b64decode(
            body["turn_state_base64"], validate=True
        )
        turns = GroundedTurnConversationOwner.restore_encoded(
            authority_key=authority_key,
            encoded=turn_state,
        )
        result = cls(
            authority_key=authority_key,
            profile=profile,
            turn_owner=turns,
            motor_owner=motor_owner,
        )
        if result.encoded_snapshot() != encoded:
            raise ValueError(
                "lived conversation cold restore changed bytes"
            )
        return result


__all__ = (
    "ConversationalMotorProposal",
    "LivedConversationLearningCoordinator",
    "LivedConversationLearningProfile",
    "LivedConversationLearningResult",
    "PreparedLivedConversationLearning",
)
