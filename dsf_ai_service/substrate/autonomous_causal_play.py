"""Bounded deterministic ownership for autonomous embodied play.

Play is admitted only when the current authenticated full-field world
structure has one exact, closed, tutor-grounded embodiment relation.  The
owner does not score activities, use time, invent an action, or reduce the
field.  It issues one authenticated opportunity for an exact
``(relation-state, world-structure)`` pair and will not issue that
opportunity again until the verified relation state itself changes.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import threading
from typing import Mapping

from dsf_ai_service.substrate.causal_action_cycle import (
    VerifiedActionRelationEvidence,
)


STATE_SCHEMA = "guala.autonomous_causal_play.state.v1"
OPPORTUNITY_SCHEMA = "guala.autonomous_causal_play.opportunity.v1"
COMPLETION_SCHEMA = "guala.autonomous_causal_play.completion.v1"
MAX_RELATIONS = 64
DEFAULT_ENCODED_STATE_BYTES = 128 * 1024


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
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} is not a SHA-256 digest")
    return value


def _authority_key(value: object) -> bytes:
    if isinstance(value, str):
        value = value.encode("utf-8")
    if not isinstance(value, bytes) or not value:
        raise ValueError("autonomous play authority key is required")
    return value


def _relation_record(
    value: VerifiedActionRelationEvidence,
) -> dict[str, object]:
    if not isinstance(value, VerifiedActionRelationEvidence):
        raise TypeError("autonomous play requires verified relation evidence")
    _sha256(value.binding_id, "relation binding")
    _sha256(
        value.trigger_witness.structural_fingerprint,
        "relation trigger structure",
    )
    value.action.verify(max_command_bytes=4096)
    if value.status not in {"provisional", "confirmed", "revoked"}:
        raise ValueError("relation status changed")
    if value.latest_closure_receipt_sha256 is not None:
        _sha256(value.latest_closure_receipt_sha256, "relation closure")
    if value.teaching_evidence_receipt_sha256 is not None:
        _sha256(
            value.teaching_evidence_receipt_sha256,
            "relation teaching evidence",
        )
    if value.outcome_witness is not None:
        _sha256(
            value.outcome_witness.structural_fingerprint,
            "relation outcome structure",
        )
    return {
        "action_receipt_sha256": value.action.authority_receipt_sha256,
        "admitted": value.status != "revoked",
        "binding_id": value.binding_id,
        "closed": value.latest_closure_receipt_sha256 is not None,
        "outcome_structural_fingerprint": (
            value.outcome_witness.structural_fingerprint
            if value.outcome_witness is not None
            else None
        ),
        "teacher_nonce": value.teacher_nonce,
        "teacher_schema": value.teacher_schema,
        "teacher_source": value.teacher_source,
        "teaching_evidence_receipt_sha256": (
            value.teaching_evidence_receipt_sha256
        ),
        "trigger_structural_fingerprint": (
            value.trigger_witness.structural_fingerprint
        ),
    }


@dataclass(frozen=True, slots=True)
class AutonomousPlayOpportunity:
    opportunity_id: str
    relation_state_sha256: str
    trigger_structural_fingerprint: str
    world_observation_receipt_sha256: str
    binding_id: str
    action_receipt_sha256: str
    authority_hmac_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action_receipt_sha256": self.action_receipt_sha256,
            "binding_id": self.binding_id,
            "opportunity_id": self.opportunity_id,
            "relation_state_sha256": self.relation_state_sha256,
            "schema": OPPORTUNITY_SCHEMA,
            "trigger_structural_fingerprint": (
                self.trigger_structural_fingerprint
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
        }


@dataclass(frozen=True, slots=True)
class AutonomousPlayCompletion:
    opportunity_id: str
    causal_play_receipt_sha256: str

    def as_record(self) -> dict[str, object]:
        return {
            "causal_play_receipt_sha256": self.causal_play_receipt_sha256,
            "opportunity_id": self.opportunity_id,
            "schema": COMPLETION_SCHEMA,
        }


def _opportunity_from(value: object) -> AutonomousPlayOpportunity:
    expected = {
        "action_receipt_sha256",
        "authority_hmac_sha256",
        "binding_id",
        "opportunity_id",
        "relation_state_sha256",
        "schema",
        "trigger_structural_fingerprint",
        "world_observation_receipt_sha256",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != OPPORTUNITY_SCHEMA
    ):
        raise ValueError("autonomous play opportunity fields changed")
    return AutonomousPlayOpportunity(
        opportunity_id=_sha256(value.get("opportunity_id"), "opportunity"),
        relation_state_sha256=_sha256(
            value.get("relation_state_sha256"), "opportunity relation state"
        ),
        trigger_structural_fingerprint=_sha256(
            value.get("trigger_structural_fingerprint"),
            "opportunity trigger structure",
        ),
        world_observation_receipt_sha256=_sha256(
            value.get("world_observation_receipt_sha256"),
            "opportunity world observation",
        ),
        binding_id=_sha256(value.get("binding_id"), "opportunity binding"),
        action_receipt_sha256=_sha256(
            value.get("action_receipt_sha256"), "opportunity action"
        ),
        authority_hmac_sha256=_sha256(
            value.get("authority_hmac_sha256"), "opportunity authority"
        ),
    )


class AutonomousCausalPlayOwner:
    """Own one-use autonomous play opportunities without a clock or score."""

    def __init__(
        self,
        *,
        authority_key: object,
        relation_capacity: int = MAX_RELATIONS,
        encoded_state_capacity: int = DEFAULT_ENCODED_STATE_BYTES,
    ) -> None:
        if (
            isinstance(relation_capacity, bool)
            or not isinstance(relation_capacity, int)
            or relation_capacity <= 0
            or relation_capacity > MAX_RELATIONS
            or isinstance(encoded_state_capacity, bool)
            or not isinstance(encoded_state_capacity, int)
            or encoded_state_capacity <= 0
        ):
            raise ValueError("autonomous play capacities are invalid")
        self._key = _authority_key(authority_key)
        self._relation_capacity = relation_capacity
        self._encoded_state_capacity = encoded_state_capacity
        self._relation_state_sha256: str | None = None
        self._consumed: dict[str, str] = {}
        self._active: AutonomousPlayOpportunity | None = None
        self._lock = threading.RLock()

    def _sign(self, value: object) -> str:
        return hmac.new(self._key, _canonical(value), hashlib.sha256).hexdigest()

    def verify_opportunity(
        self, value: AutonomousPlayOpportunity | Mapping[str, object]
    ) -> AutonomousPlayOpportunity:
        opportunity = (
            value
            if isinstance(value, AutonomousPlayOpportunity)
            else _opportunity_from(value)
        )
        for name, digest in (
            ("opportunity", opportunity.opportunity_id),
            ("opportunity relation state", opportunity.relation_state_sha256),
            (
                "opportunity trigger structure",
                opportunity.trigger_structural_fingerprint,
            ),
            (
                "opportunity world observation",
                opportunity.world_observation_receipt_sha256,
            ),
            ("opportunity binding", opportunity.binding_id),
            ("opportunity action", opportunity.action_receipt_sha256),
            ("opportunity authority", opportunity.authority_hmac_sha256),
        ):
            _sha256(digest, name)
        expected_id = _digest({
            "action_receipt_sha256": opportunity.action_receipt_sha256,
            "binding_id": opportunity.binding_id,
            "relation_state_sha256": opportunity.relation_state_sha256,
            "schema": "guala.autonomous_causal_play.identity.v1",
            "trigger_structural_fingerprint": (
                opportunity.trigger_structural_fingerprint
            ),
        })
        if (
            opportunity.opportunity_id != expected_id
            or not hmac.compare_digest(
                opportunity.authority_hmac_sha256,
                self._sign(opportunity.unsigned_record()),
            )
        ):
            raise ValueError("autonomous play opportunity authority changed")
        return opportunity

    @staticmethod
    def _verified_relation_state(
        evidence: tuple[VerifiedActionRelationEvidence, ...],
        *,
        relation_capacity: int,
    ) -> tuple[str, tuple[dict[str, object], ...]]:
        if (
            not isinstance(evidence, tuple)
            or len(evidence) > relation_capacity
        ):
            raise ValueError("autonomous play relation evidence exceeds capacity")
        records = tuple(
            sorted(
                (_relation_record(item) for item in evidence),
                key=lambda item: (
                    item["binding_id"],
                    item["action_receipt_sha256"],
                ),
            )
        )
        if len({item["binding_id"] for item in records}) != len(records):
            raise ValueError("autonomous play relation evidence repeats a binding")
        return _digest({
            "relations": records,
            "schema": "guala.autonomous_causal_play.relation_state.v1",
        }), records

    def prepare(
        self,
        *,
        evidence: tuple[VerifiedActionRelationEvidence, ...],
        world_structural_fingerprint: str,
        world_observation_receipt_sha256: str,
    ) -> AutonomousPlayOpportunity | None:
        """Reserve the one exact action available for the present structure."""

        _sha256(world_structural_fingerprint, "play world structure")
        _sha256(world_observation_receipt_sha256, "play world observation")
        relation_state_sha256, records = self._verified_relation_state(
            evidence,
            relation_capacity=self._relation_capacity,
        )
        candidates = tuple(
            item
            for item in records
            if (
                item["trigger_structural_fingerprint"]
                == world_structural_fingerprint
                and item["admitted"]
                and item["closed"]
                and item["outcome_structural_fingerprint"] is not None
            )
        )
        with self._lock:
            if self._relation_state_sha256 != relation_state_sha256:
                if self._active is not None:
                    return None
                self._relation_state_sha256 = relation_state_sha256
                self._consumed = {}
            if len(candidates) != 1:
                return None
            candidate = candidates[0]
            opportunity_id = _digest({
                "action_receipt_sha256": candidate["action_receipt_sha256"],
                "binding_id": candidate["binding_id"],
                "relation_state_sha256": relation_state_sha256,
                "schema": "guala.autonomous_causal_play.identity.v1",
                "trigger_structural_fingerprint": world_structural_fingerprint,
            })
            if opportunity_id in self._consumed:
                return None
            if self._active is not None:
                if (
                    self._active.opportunity_id == opportunity_id
                    and self._active.world_observation_receipt_sha256
                    == world_observation_receipt_sha256
                ):
                    return self._active
                return None
            unsigned = {
                "action_receipt_sha256": candidate["action_receipt_sha256"],
                "binding_id": candidate["binding_id"],
                "opportunity_id": opportunity_id,
                "relation_state_sha256": relation_state_sha256,
                "schema": OPPORTUNITY_SCHEMA,
                "trigger_structural_fingerprint": world_structural_fingerprint,
                "world_observation_receipt_sha256": (
                    world_observation_receipt_sha256
                ),
            }
            self._active = AutonomousPlayOpportunity(
                opportunity_id=opportunity_id,
                relation_state_sha256=relation_state_sha256,
                trigger_structural_fingerprint=world_structural_fingerprint,
                world_observation_receipt_sha256=(
                    world_observation_receipt_sha256
                ),
                binding_id=candidate["binding_id"],
                action_receipt_sha256=candidate["action_receipt_sha256"],
                authority_hmac_sha256=self._sign(unsigned),
            )
            self._encoded_locked()
            return self._active

    def cancel(
        self,
        value: AutonomousPlayOpportunity | Mapping[str, object],
    ) -> None:
        opportunity = self.verify_opportunity(value)
        with self._lock:
            if (
                self._active is None
                or self._active.opportunity_id != opportunity.opportunity_id
                or self._active != opportunity
            ):
                raise ValueError("autonomous play opportunity is not active")
            self._active = None

    def complete(
        self,
        value: AutonomousPlayOpportunity | Mapping[str, object],
        *,
        causal_play_record: Mapping[str, object],
    ) -> AutonomousPlayCompletion:
        """Consume an opportunity only after at least one physical action."""

        opportunity = self.verify_opportunity(value)
        if (
            not isinstance(causal_play_record, Mapping)
            or causal_play_record.get("trigger") != "autonomous_play"
            or causal_play_record.get("dispatch_status") != "completed"
            or causal_play_record.get("world_observation_receipt_sha256")
            != opportunity.world_observation_receipt_sha256
            or not isinstance(causal_play_record.get("steps"), list)
            or not causal_play_record["steps"]
        ):
            raise ValueError(
                "autonomous play completion lacks a physical causal action"
            )
        play_receipt = _digest({
            "causal_play_record": causal_play_record,
            "opportunity_id": opportunity.opportunity_id,
            "schema": "guala.autonomous_causal_play.completed_record.v1",
        })
        with self._lock:
            if (
                self._active is None
                or self._active != opportunity
                or self._relation_state_sha256
                != opportunity.relation_state_sha256
            ):
                raise ValueError("autonomous play opportunity is not active")
            if len(self._consumed) >= self._relation_capacity:
                raise RuntimeError("autonomous play consumption capacity is full")
            self._consumed[opportunity.opportunity_id] = play_receipt
            self._active = None
            self._encoded_locked()
        return AutonomousPlayCompletion(
            opportunity_id=opportunity.opportunity_id,
            causal_play_receipt_sha256=play_receipt,
        )

    def _unsigned_state(self) -> dict[str, object]:
        return {
            "active": self._active.as_record() if self._active else None,
            "capacities": {
                "encoded_state_capacity": self._encoded_state_capacity,
                "relation_capacity": self._relation_capacity,
            },
            "consumed": [
                {
                    "causal_play_receipt_sha256": self._consumed[key],
                    "opportunity_id": key,
                }
                for key in sorted(self._consumed)
            ],
            "relation_state_sha256": self._relation_state_sha256,
            "schema": STATE_SCHEMA,
        }

    def _encoded_locked(self) -> bytes:
        unsigned = self._unsigned_state()
        payload = _canonical({
            **unsigned,
            "authority_hmac_sha256": self._sign(unsigned),
        })
        if len(payload) > self._encoded_state_capacity:
            raise RuntimeError("autonomous play state capacity is full")
        return payload

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            return self._encoded_locked()

    def restore_encoded(self, payload: object) -> None:
        if not isinstance(payload, bytes) or len(payload) > self._encoded_state_capacity:
            raise ValueError("autonomous play state bytes are invalid")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("autonomous play state is not canonical JSON") from error
        expected = {
            "active",
            "authority_hmac_sha256",
            "capacities",
            "consumed",
            "relation_state_sha256",
            "schema",
        }
        if (
            not isinstance(decoded, dict)
            or set(decoded) != expected
            or decoded.get("schema") != STATE_SCHEMA
            or decoded.get("capacities") != {
                "encoded_state_capacity": self._encoded_state_capacity,
                "relation_capacity": self._relation_capacity,
            }
            or not isinstance(decoded.get("consumed"), list)
            or len(decoded["consumed"]) > self._relation_capacity
        ):
            raise ValueError("autonomous play state fields changed")
        authority = _sha256(
            decoded["authority_hmac_sha256"], "autonomous play state authority"
        )
        unsigned = {key: decoded[key] for key in expected if key != "authority_hmac_sha256"}
        if not hmac.compare_digest(authority, self._sign(unsigned)):
            raise ValueError("autonomous play state authority changed")
        relation_state = decoded["relation_state_sha256"]
        if relation_state is not None:
            _sha256(relation_state, "autonomous play relation state")
        consumed: dict[str, str] = {}
        for item in decoded["consumed"]:
            if not isinstance(item, dict) or set(item) != {
                "causal_play_receipt_sha256",
                "opportunity_id",
            }:
                raise ValueError("autonomous play consumption fields changed")
            opportunity_id = _sha256(
                item["opportunity_id"], "consumed opportunity"
            )
            if opportunity_id in consumed:
                raise ValueError("autonomous play repeats consumed opportunity")
            consumed[opportunity_id] = _sha256(
                item["causal_play_receipt_sha256"], "consumed causal play"
            )
        active = (
            self.verify_opportunity(decoded["active"])
            if decoded["active"] is not None
            else None
        )
        if (
            active is not None
            and (
                relation_state != active.relation_state_sha256
                or active.opportunity_id in consumed
            )
        ):
            raise ValueError("autonomous play active opportunity changed state")
        with self._lock:
            prior = (
                self._relation_state_sha256,
                dict(self._consumed),
                self._active,
            )
            self._relation_state_sha256 = relation_state
            self._consumed = consumed
            self._active = active
            try:
                if self._encoded_locked() != payload:
                    raise ValueError("autonomous play state is not canonical")
            except BaseException:
                (
                    self._relation_state_sha256,
                    self._consumed,
                    self._active,
                ) = prior
                raise

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "active": self._active is not None,
                "consumed": len(self._consumed),
                "encoded_state_bytes": len(self._encoded_locked()),
                "relation_capacity": self._relation_capacity,
                "relation_state_sha256": self._relation_state_sha256,
            }


__all__ = (
    "AutonomousCausalPlayOwner",
    "AutonomousPlayCompletion",
    "AutonomousPlayOpportunity",
    "COMPLETION_SCHEMA",
    "OPPORTUNITY_SCHEMA",
    "STATE_SCHEMA",
)
