"""Bounded receipt-level demonstrations for grounded W1 behavior.

This owner does not assign milestone names or word meanings.  It retains two
substrate facts only: a grounded vocal response to a grounded challenge, or an
authenticated W1 action outcome after a grounded challenge.  Vocal responses
retain their ordered grounded cue structure after self-hearing.  Lived scene
citations retain complete non-auditory roots from exact settlements.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    AuditoryMotifCausalGroundingOwner,
    GroundingRoot,
    grounding_roots_from_settlement,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.grounded_turn_conversation import (
    GroundedTurnCue,
    cue_from_record,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalHearingReceipt,
    SelfVocalPCMMotorOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1PhysicalEvidenceReceipt,
    W1AudiovisualPhysicalEvidenceAuthority,
)


DEMONSTRATION_PROFILE_SCHEMA = "guala.w1.grounded_demo.profile.v1"
DEMONSTRATION_SCHEMA = "guala.w1.grounded_demo.v1"
DEMONSTRATION_STATE_SCHEMA = "guala.w1.grounded_demo.state.v1"
DEMONSTRATION_ENVELOPE_SCHEMA = "guala.w1.grounded_demo.state_hmac.v1"
_DEMO_DOMAIN = b"guala-w1-grounded-demonstration-v1\0"
_STATE_DOMAIN = b"guala-w1-grounded-demonstration-state-v1\0"


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
    result = value.encode() if isinstance(value, str) else value
    if not isinstance(result, bytes) or not 32 <= len(result) <= 4096:
        raise ValueError("W1 demonstration key boundary changed")
    return result


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{name} is invalid")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} is invalid")
    return value


@dataclass(frozen=True, slots=True)
class W1GroundedDemonstrationProfile:
    profile_id: str
    max_demonstrations: int
    max_scenes_per_demonstration: int
    max_roots_per_scene: int
    max_cue_elements: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(cls, *, profile_id: str, max_demonstrations: int,
               max_scenes_per_demonstration: int, max_roots_per_scene: int,
               max_cue_elements: int, max_state_bytes: int):
        profile_id = _identifier(profile_id, "W1 demonstration profile")
        values = {
            "max_cue_elements": _positive(
                max_cue_elements, "demo cue elements"),
            "max_demonstrations": _positive(
                max_demonstrations, "demo count"),
            "max_roots_per_scene": _positive(
                max_roots_per_scene, "demo scene roots"),
            "max_scenes_per_demonstration": _positive(
                max_scenes_per_demonstration, "demo scenes"),
            "max_state_bytes": _positive(max_state_bytes, "demo state"),
            "profile_id": profile_id,
            "schema": DEMONSTRATION_PROFILE_SCHEMA,
        }
        return cls(
            profile_id=profile_id,
            max_demonstrations=max_demonstrations,
            max_scenes_per_demonstration=max_scenes_per_demonstration,
            max_roots_per_scene=max_roots_per_scene,
            max_cue_elements=max_cue_elements,
            max_state_bytes=max_state_bytes,
            authority_receipt_sha256=_digest(values),
        )

    def record(self) -> dict[str, object]:
        return {
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "max_cue_elements": self.max_cue_elements,
            "max_demonstrations": self.max_demonstrations,
            "max_roots_per_scene": self.max_roots_per_scene,
            "max_scenes_per_demonstration": (
                self.max_scenes_per_demonstration),
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": DEMONSTRATION_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _identifier(self.profile_id, "W1 demonstration profile")
        _positive(self.max_demonstrations, "demo count")
        _positive(self.max_scenes_per_demonstration, "demo scenes")
        _positive(self.max_roots_per_scene, "demo scene roots")
        _positive(self.max_cue_elements, "demo cue elements")
        _positive(self.max_state_bytes, "demo state")
        _sha256(
            self.authority_receipt_sha256,
            "W1 demonstration profile authority",
        )
        expected = dict(self.record())
        expected.pop("authority_receipt_sha256")
        if self.authority_receipt_sha256 != _digest(expected):
            raise ValueError("W1 demonstration profile changed")


@dataclass(frozen=True, slots=True)
class W1GroundedScene:
    settlement_receipt_sha256: str
    roots: tuple[GroundingRoot, ...]

    def record(self) -> dict[str, object]:
        return {
            "roots": [value.as_record() for value in self.roots],
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
        }

    def verify(self, maximum: int) -> None:
        _sha256(
            self.settlement_receipt_sha256,
            "W1 grounded scene settlement",
        )
        if (
            not self.roots
            or len(self.roots) > maximum
            or tuple(sorted(self.roots, key=lambda value: value.root_id))
            != self.roots
        ):
            raise ValueError("W1 grounded scene changed")
        for value in self.roots:
            value.verify()


@dataclass(frozen=True, slots=True)
class W1GroundedDemonstration:
    demonstration_id: str
    kind: str
    challenge_cue: GroundedTurnCue
    response_cue: GroundedTurnCue | None
    scenes: tuple[W1GroundedScene, ...]
    motor_id: str | None
    self_hearing_receipt_sha256: str | None
    action_execution_receipt_sha256: str | None
    action_outcome_evidence_receipt_sha256: str | None
    source_episode_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_execution_receipt_sha256": (
                self.action_execution_receipt_sha256),
            "action_outcome_evidence_receipt_sha256": (
                self.action_outcome_evidence_receipt_sha256),
            "challenge_cue": self.challenge_cue.as_record(),
            "kind": self.kind,
            "motor_id": self.motor_id,
            "response_cue": (
                self.response_cue.as_record()
                if self.response_cue is not None else None),
            "scenes": [value.record() for value in self.scenes],
            "schema": DEMONSTRATION_SCHEMA,
            "self_hearing_receipt_sha256": (
                self.self_hearing_receipt_sha256),
            "source_episode_receipt_sha256s": list(
                self.source_episode_receipt_sha256s),
        }


class W1GroundedDemonstrationOwner:
    def __init__(self, *, authority_key: bytes | str,
                 resource_profile: W1GroundedDemonstrationProfile):
        resource_profile.verify()
        root = hashlib.sha256(_key(authority_key)).digest()
        self._demo_key = hashlib.sha256(_DEMO_DOMAIN + root).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = resource_profile
        self._demonstrations: dict[str, W1GroundedDemonstration] = {}
        self._lock = threading.RLock()

    @property
    def demonstrations(self):
        with self._lock:
            return tuple(
                self._demonstrations[key]
                for key in sorted(self._demonstrations))

    def _verify_demo(self, value: W1GroundedDemonstration) -> None:
        _sha256(value.demonstration_id, "W1 demonstration")
        _sha256(
            value.authority_hmac_sha256,
            "W1 demonstration authority",
        )
        value.challenge_cue.verify(self._profile.max_cue_elements)
        if value.response_cue is not None:
            value.response_cue.verify(self._profile.max_cue_elements)
        for scene in value.scenes:
            scene.verify(self._profile.max_roots_per_scene)
        for receipt in value.source_episode_receipt_sha256s:
            _sha256(receipt, "W1 demonstration physical source")
        vocal_shape = (
            value.kind in {
                "cited_lived_sequence_response",
                "grounded_exchange",
            }
            and value.response_cue is not None
            and value.motor_id is not None
            and value.self_hearing_receipt_sha256 is not None
            and value.action_execution_receipt_sha256 is None
            and value.action_outcome_evidence_receipt_sha256 is None
        )
        action_shape = (
            value.kind == "authenticated_action_outcome"
            and value.response_cue is None
            and value.motor_id is None
            and value.self_hearing_receipt_sha256 is None
            and value.action_execution_receipt_sha256 is not None
            and value.action_outcome_evidence_receipt_sha256 is not None
        )
        if value.motor_id is not None:
            _sha256(value.motor_id, "W1 demonstration motor")
        if value.self_hearing_receipt_sha256 is not None:
            _sha256(
                value.self_hearing_receipt_sha256,
                "W1 demonstration self-hearing",
            )
        if value.action_execution_receipt_sha256 is not None:
            _sha256(
                value.action_execution_receipt_sha256,
                "W1 demonstration action execution",
            )
        if value.action_outcome_evidence_receipt_sha256 is not None:
            _sha256(
                value.action_outcome_evidence_receipt_sha256,
                "W1 demonstration action outcome",
            )
        if (
            not (vocal_shape or action_shape)
            or not value.scenes
            or len(value.scenes)
            > self._profile.max_scenes_per_demonstration
            or tuple(sorted(set(
                value.source_episode_receipt_sha256s
            ))) != value.source_episode_receipt_sha256s
            or len(value.source_episode_receipt_sha256s) < 2
        ):
            raise ValueError("W1 grounded demonstration changed")
        payload = value.payload()
        expected_hmac = hmac.new(
            self._demo_key,
            _DEMO_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            value.demonstration_id != _digest(payload)
            or not hmac.compare_digest(
                value.authority_hmac_sha256, expected_hmac
            )
        ):
            raise ValueError("W1 demonstration authority changed")

    def _admit(self, provisional: W1GroundedDemonstration):
        payload = provisional.payload()
        identity = _digest(payload)
        signature = hmac.new(
            self._demo_key,
            _DEMO_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1GroundedDemonstration(
            demonstration_id=identity,
            kind=provisional.kind,
            challenge_cue=provisional.challenge_cue,
            response_cue=provisional.response_cue,
            scenes=provisional.scenes,
            motor_id=provisional.motor_id,
            self_hearing_receipt_sha256=(
                provisional.self_hearing_receipt_sha256),
            action_execution_receipt_sha256=(
                provisional.action_execution_receipt_sha256),
            action_outcome_evidence_receipt_sha256=(
                provisional.action_outcome_evidence_receipt_sha256),
            source_episode_receipt_sha256s=(
                provisional.source_episode_receipt_sha256s),
            authority_hmac_sha256=signature,
        )
        self._verify_demo(result)
        with self._lock:
            used = {
                receipt
                for value in self._demonstrations.values()
                for receipt in value.source_episode_receipt_sha256s
            }
            if used.intersection(result.source_episode_receipt_sha256s):
                raise ValueError(
                    "W1 demonstrations reuse a physical source episode")
            if len(self._demonstrations) >= self._profile.max_demonstrations:
                raise RuntimeError("W1 demonstration capacity exhausted")
            staged = dict(self._demonstrations)
            staged[result.demonstration_id] = result
            self._encoded(staged)
            self._demonstrations = staged
        return result

    def admit_vocal(
        self, *, challenge_cue: GroundedTurnCue,
        response_cue: GroundedTurnCue,
        lived_settlements: tuple[CausalExperienceSettlement, ...],
        self_hearing: SelfVocalHearingReceipt,
        motor_owner: SelfVocalPCMMotorOwner,
    ):
        challenge_cue.verify(self._profile.max_cue_elements)
        response_cue.verify(self._profile.max_cue_elements)
        motor_owner.verify_hearing(self_hearing)
        scenes = tuple(
            W1GroundedScene(
                value.authority_receipt_sha256,
                grounding_roots_from_settlement(value),
            )
            for value in lived_settlements
        )
        if not scenes or len(scenes) > (
            self._profile.max_scenes_per_demonstration
        ):
            raise ValueError("W1 vocal demonstration scene boundary changed")
        for value in scenes:
            value.verify(self._profile.max_roots_per_scene)
        scene_roots = {
            (root.root_id, root.value_sha256)
            for scene in scenes for root in scene.roots
        }
        response_roots = {
            (value.root.root_id, value.root.value_sha256)
            for value in response_cue.elements
        }
        kind = (
            "cited_lived_sequence_response"
            if response_roots.issubset(scene_roots)
            else "grounded_exchange"
        )
        physical_source_receipts = tuple(
            value.authority_receipt_sha256
            for value in lived_settlements
        ) + (self_hearing.receptor_event_receipt_sha256,)
        sources = tuple(sorted(set(physical_source_receipts)))
        if (
            len(sources) != len(physical_source_receipts)
            or len(sources) < 2
        ):
            raise ValueError("W1 vocal source episodes are not disjoint")
        return self._admit(W1GroundedDemonstration(
            demonstration_id="",
            kind=kind,
            challenge_cue=challenge_cue,
            response_cue=response_cue,
            scenes=scenes,
            motor_id=self_hearing.motor_id,
            self_hearing_receipt_sha256=(
                self_hearing.authority_receipt_sha256),
            action_execution_receipt_sha256=None,
            action_outcome_evidence_receipt_sha256=None,
            source_episode_receipt_sha256s=sources,
            authority_hmac_sha256="",
        ))

    def admit_action(
        self, *, challenge_cue: GroundedTurnCue,
        lived_settlements: tuple[CausalExperienceSettlement, ...],
        execution: ActionExecutionReceipt,
        outcome: W1PhysicalEvidenceReceipt,
        world_owner: EmbodimentWorldAuthority,
        physical_owner: W1AudiovisualPhysicalEvidenceAuthority,
    ):
        challenge_cue.verify(self._profile.max_cue_elements)
        world_owner.verify_execution_receipt(execution)
        physical_owner.verify_evidence_receipt(outcome)
        if (
            execution.disposition != "applied"
            or outcome.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
        ):
            raise ValueError("W1 action demonstration lacks applied outcome")
        scenes = tuple(
            W1GroundedScene(
                value.authority_receipt_sha256,
                grounding_roots_from_settlement(value),
            )
            for value in lived_settlements
        )
        for value in scenes:
            value.verify(self._profile.max_roots_per_scene)
        physical_source_receipts = tuple(
            value.authority_receipt_sha256
            for value in lived_settlements
        ) + (outcome.causal_settlement_receipt_sha256,)
        sources = tuple(sorted(set(physical_source_receipts)))
        if (
            len(sources) != len(physical_source_receipts)
            or len(sources) < 2
        ):
            raise ValueError("W1 action source episodes are not disjoint")
        return self._admit(W1GroundedDemonstration(
            demonstration_id="",
            kind="authenticated_action_outcome",
            challenge_cue=challenge_cue,
            response_cue=None,
            scenes=scenes,
            motor_id=None,
            self_hearing_receipt_sha256=None,
            action_execution_receipt_sha256=(
                execution.authority_receipt_sha256),
            action_outcome_evidence_receipt_sha256=(
                outcome.authority_receipt_sha256),
            source_episode_receipt_sha256s=sources,
            authority_hmac_sha256="",
        ))

    def _encoded(self, values):
        body = {
            "demonstrations": [
                values[key].payload() | {
                    "authority_hmac_sha256": values[key].authority_hmac_sha256,
                    "demonstration_id": values[key].demonstration_id,
                } for key in sorted(values)
            ],
            "resource_profile": self._profile.record(),
            "schema": DEMONSTRATION_STATE_SCHEMA,
        }
        envelope = {
            "body": body,
            "schema": DEMONSTRATION_ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        }
        encoded = _canonical(envelope)
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("W1 demonstration state capacity exhausted")
        return encoded

    def snapshot_encoded(self):
        with self._lock:
            return self._encoded(self._demonstrations)

    @classmethod
    def restore_encoded(cls, *, authority_key: bytes | str, encoded: bytes):
        if not isinstance(encoded, bytes):
            raise TypeError("W1 demonstration state must be bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("W1 demonstration state is unreadable") from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != DEMONSTRATION_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("W1 demonstration envelope changed")
        body = envelope["body"]
        if (
            not isinstance(body, Mapping)
            or set(body)
            != {"demonstrations", "resource_profile", "schema"}
            or body.get("schema") != DEMONSTRATION_STATE_SCHEMA
            or not isinstance(body.get("demonstrations"), list)
        ):
            raise ValueError("W1 demonstration body changed")
        profile_record = body.get("resource_profile")
        if not isinstance(profile_record, Mapping):
            raise ValueError("W1 demonstration profile record changed")
        profile = W1GroundedDemonstrationProfile(
            profile_id=profile_record.get("profile_id"),
            max_demonstrations=profile_record.get("max_demonstrations"),
            max_scenes_per_demonstration=profile_record.get(
                "max_scenes_per_demonstration"),
            max_roots_per_scene=profile_record.get("max_roots_per_scene"),
            max_cue_elements=profile_record.get("max_cue_elements"),
            max_state_bytes=profile_record.get("max_state_bytes"),
            authority_receipt_sha256=profile_record.get(
                "authority_receipt_sha256"),
        )
        profile.verify()
        owner = cls(authority_key=authority_key, resource_profile=profile)
        expected_state_hmac = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected_state_hmac,
        ):
            raise ValueError("W1 demonstration state HMAC changed")
        restored = {}
        used_sources = set()
        for raw in body["demonstrations"]:
            if not isinstance(raw, Mapping):
                raise ValueError("W1 demonstration record changed")
            challenge = cue_from_record(
                raw.get("challenge_cue"),
                max_elements=profile.max_cue_elements,
            )
            response_raw = raw.get("response_cue")
            response = (
                cue_from_record(
                    response_raw,
                    max_elements=profile.max_cue_elements,
                )
                if response_raw is not None else None
            )
            scenes = []
            for scene_raw in raw.get("scenes", ()):
                roots = tuple(
                    GroundingRoot(
                        root_id=root_raw.get("root_id"),
                        value_sha256=root_raw.get("value_sha256"),
                        value_json=root_raw.get("value_json"),
                    )
                    for root_raw in scene_raw.get("roots", ())
                )
                scenes.append(W1GroundedScene(
                    settlement_receipt_sha256=scene_raw.get(
                        "settlement_receipt_sha256"),
                    roots=roots,
                ))
            demo = W1GroundedDemonstration(
                demonstration_id=raw.get("demonstration_id"),
                kind=raw.get("kind"),
                challenge_cue=challenge,
                response_cue=response,
                scenes=tuple(scenes),
                motor_id=raw.get("motor_id"),
                self_hearing_receipt_sha256=raw.get(
                    "self_hearing_receipt_sha256"),
                action_execution_receipt_sha256=raw.get(
                    "action_execution_receipt_sha256"),
                action_outcome_evidence_receipt_sha256=raw.get(
                    "action_outcome_evidence_receipt_sha256"),
                source_episode_receipt_sha256s=tuple(
                    raw.get("source_episode_receipt_sha256s", ())),
                authority_hmac_sha256=raw.get("authority_hmac_sha256"),
            )
            owner._verify_demo(demo)
            if (
                demo.demonstration_id in restored
                or used_sources.intersection(
                    demo.source_episode_receipt_sha256s)
            ):
                raise ValueError("W1 demonstration sources repeat")
            restored[demo.demonstration_id] = demo
            used_sources.update(demo.source_episode_receipt_sha256s)
        owner._demonstrations = restored
        if owner.snapshot_encoded() != encoded:
            raise ValueError("W1 demonstration state is not canonical")
        return owner

    def cross_validate_restored(
        self,
        *,
        grounding_owner: AuditoryMotifCausalGroundingOwner,
        motor_owner: SelfVocalPCMMotorOwner,
    ) -> None:
        """Prove restored cue and vocal references against live owners."""

        if not isinstance(
            grounding_owner, AuditoryMotifCausalGroundingOwner
        ):
            raise TypeError(
                "W1 demonstration restore requires grounding owner"
            )
        if not isinstance(motor_owner, SelfVocalPCMMotorOwner):
            raise TypeError(
                "W1 demonstration restore requires self-vocal motor owner"
            )
        grounded_roots = {
            (
                alternative.root.root_id,
                alternative.root.value_sha256,
            )
            for distinction in grounding_owner.distinctions
            for alternative in distinction.alternatives
            if alternative.diagnostic_motif_neuron_ids
        }
        motor_ids = {
            exemplar.motor_id for exemplar in motor_owner.exemplars
        }
        for demonstration in self.demonstrations:
            self._verify_demo(demonstration)
            cues = (demonstration.challenge_cue,) + (
                (demonstration.response_cue,)
                if demonstration.response_cue is not None
                else ()
            )
            for cue in cues:
                for element in cue.elements:
                    if (
                        element.root.root_id,
                        element.root.value_sha256,
                    ) not in grounded_roots:
                        raise ValueError(
                            "W1 demonstration cue lacks grounded distinction"
                        )
            if (
                demonstration.motor_id is not None
                and demonstration.motor_id not in motor_ids
            ):
                raise ValueError(
                    "W1 demonstration motor is not retained"
                )

    def status(self):
        with self._lock:
            kinds = {}
            for value in self._demonstrations.values():
                kinds[value.kind] = kinds.get(value.kind, 0) + 1
            return {
                "capacity": self._profile.max_demonstrations,
                "capacity_exhausted": (
                    len(self._demonstrations)
                    >= self._profile.max_demonstrations),
                "count": len(self._demonstrations),
                "kind_counts": kinds,
                "state_bytes": len(self._encoded(self._demonstrations)),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }


__all__ = [
    "DEMONSTRATION_ENVELOPE_SCHEMA",
    "DEMONSTRATION_PROFILE_SCHEMA",
    "DEMONSTRATION_SCHEMA",
    "DEMONSTRATION_STATE_SCHEMA",
    "W1GroundedDemonstration",
    "W1GroundedDemonstrationOwner",
    "W1GroundedDemonstrationProfile",
    "W1GroundedScene",
]
