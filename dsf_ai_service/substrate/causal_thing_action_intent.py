"""Bounded action intents authorized by current causal THING evidence.

This owner is the action boundary downstream of
``CausalThingActionDeliberationOwner``.  It does not extend or mutate the
legacy exact-snapshot action-cycle schema.  Instead it issues a distinct typed
intent whose authority simultaneously retains:

* the current complete six-sense perception witness;
* the unique current reciprocal THING evocation;
* the original complete learned trigger/action/outcome relation; and
* the exact embodied action command selected by that relation;
* the current recognition-attention and whole-organism context receipts; and
* the current self-world and other-perspective boundary receipts.

The current field and learned field remain different witnesses.  Physical
THING continuity is the explicit reason the learned relation may apply; the
implementation never claims that the two fields are equal.

Only a fresh ``ready`` resolution can issue an intent.  Unknown, ambiguous,
stale, changed, or unclosed evidence produces no intent.  State is bounded,
authenticated, canonical, and fail-closed without eviction.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Mapping

from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    PerceptionWitness,
    _action_from,
    _witness_from,
)
from dsf_ai_service.substrate.causal_recognition_attention import (
    CausalRecognitionAttentionOwner,
    CausalRecognitionAttentionState,
)
from dsf_ai_service.substrate.causal_thing_action_deliberation import (
    CausalThingActionDeliberationOwner,
    CausalThingActionResolution,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.embodied_other_perspective import (
    EmbodiedOtherPerspectiveOwner,
    OtherBodyPerspectiveModel,
    SelfWorldState,
)


PROFILE_SCHEMA = "guala.causal_thing.action_intent.profile.v1"
INTENT_SCHEMA = "guala.causal_thing.action_intent.v2"
STATE_SCHEMA = "guala.causal_thing.action_intent.state.v2"
ENVELOPE_SCHEMA = "guala.causal_thing.action_intent.state_hmac.v2"

_INTENT_DOMAIN = b"guala-causal-thing-action-intent-v2\0"
_STATE_DOMAIN = b"guala-causal-thing-action-intent-state-v2\0"
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
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("THING action intent key changed")
    return hashlib.sha256(
        b"guala-causal-thing-action-intent-owner-v1\0" + raw
    ).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


@dataclass(frozen=True, slots=True)
class CausalThingActionIntentProfile:
    profile_id: str
    max_live_intents: int
    max_witness_bytes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_live_intents: int,
        max_witness_bytes: int,
        max_state_bytes: int,
    ) -> "CausalThingActionIntentProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
            or len(profile_id.encode("utf-8")) > 256
        ):
            raise ValueError("THING action intent profile id changed")
        provisional = cls(
            profile_id=profile_id,
            max_live_intents=_positive(
                max_live_intents,
                "THING action live intent capacity",
            ),
            max_witness_bytes=_positive(
                max_witness_bytes,
                "THING action witness capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes,
                "THING action state capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        if provisional.max_state_bytes <= provisional.max_witness_bytes:
            raise ValueError(
                "THING action state must exceed one witness boundary"
            )
        return cls(
            profile_id=provisional.profile_id,
            max_live_intents=provisional.max_live_intents,
            max_witness_bytes=provisional.max_witness_bytes,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_live_intents": self.max_live_intents,
            "max_state_bytes": self.max_state_bytes,
            "max_witness_bytes": self.max_witness_bytes,
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
            max_live_intents=self.max_live_intents,
            max_witness_bytes=self.max_witness_bytes,
            max_state_bytes=self.max_state_bytes,
        )
        if self != expected:
            raise ValueError("THING action intent profile changed")


@dataclass(frozen=True, slots=True)
class CausalThingActionIntent:
    current_witness: PerceptionWitness
    resolution_record: Mapping[str, object]
    recognition_attention_receipt_sha256: str
    attention_context_receipt_sha256: str
    focused_relation_receipt_sha256: str
    self_world_state_receipt_sha256: str
    world_observation_receipt_sha256: str
    perspective_model_receipt_sha256s: tuple[str, ...]
    thing_id: str
    source_binding_id: str
    action: ActionCommand
    learned_trigger_witness: PerceptionWitness
    expected_outcome_witness: PerceptionWitness
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action": self.action.as_record(),
            "current_witness": self.current_witness.as_record(),
            "expected_outcome_witness": (
                self.expected_outcome_witness.as_record()
            ),
            "learned_trigger_witness": (
                self.learned_trigger_witness.as_record()
            ),
            "recognition_attention_receipt_sha256": (
                self.recognition_attention_receipt_sha256
            ),
            "attention_context_receipt_sha256": (
                self.attention_context_receipt_sha256
            ),
            "focused_relation_receipt_sha256": (
                self.focused_relation_receipt_sha256
            ),
            "self_world_state_receipt_sha256": (
                self.self_world_state_receipt_sha256
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "perspective_model_receipt_sha256s": list(
                self.perspective_model_receipt_sha256s
            ),
            "resolution_record": dict(self.resolution_record),
            "schema": INTENT_SCHEMA,
            "source_binding_id": self.source_binding_id,
            "thing_id": self.thing_id,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class CausalThingActionIntentOwner:
    """Own live action intents without changing the source action memory."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: CausalThingActionIntentProfile,
        deliberation_owner: CausalThingActionDeliberationOwner,
    ) -> None:
        profile.verify()
        if not isinstance(
            deliberation_owner,
            CausalThingActionDeliberationOwner,
        ):
            raise TypeError(
                "THING action intent requires its deliberation authority"
            )
        root = _key(authority_key)
        self._intent_key = hashlib.sha256(
            _INTENT_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._deliberation = deliberation_owner
        self._live: dict[str, CausalThingActionIntent] = {}
        self._lock = threading.RLock()

    def _verify_intent(
        self,
        value: CausalThingActionIntent,
    ) -> None:
        if not isinstance(value, CausalThingActionIntent):
            raise TypeError("THING action intent is not typed")
        for digest, label in (
            (value.thing_id, "THING action intent THING"),
            (
                value.source_binding_id,
                "THING action intent source binding",
            ),
            (
                value.authority_hmac_sha256,
                "THING action intent HMAC",
            ),
            (
                value.authority_receipt_sha256,
                "THING action intent authority",
            ),
            (
                value.recognition_attention_receipt_sha256,
                "THING action intent recognition attention",
            ),
            (
                value.attention_context_receipt_sha256,
                "THING action intent attention context",
            ),
            (
                value.focused_relation_receipt_sha256,
                "THING action intent focused relation",
            ),
            (
                value.self_world_state_receipt_sha256,
                "THING action intent self-world state",
            ),
            (
                value.world_observation_receipt_sha256,
                "THING action intent world observation",
            ),
        ):
            _sha(digest, label)
        if value.perspective_model_receipt_sha256s != tuple(sorted(
            set(value.perspective_model_receipt_sha256s)
        )):
            raise ValueError(
                "THING action intent perspective custody changed"
            )
        for receipt in value.perspective_model_receipt_sha256s:
            _sha(receipt, "THING action intent perspective model")
        value.current_witness.verify(
            max_bytes=self._profile.max_witness_bytes
        )
        value.learned_trigger_witness.verify(
            max_bytes=self._profile.max_witness_bytes
        )
        value.expected_outcome_witness.verify(
            max_bytes=self._profile.max_witness_bytes
        )
        value.action.verify(
            max_command_bytes=4_096,
        )
        resolution = value.resolution_record
        if (
            not isinstance(resolution, Mapping)
            or resolution.get("schema")
            != "guala.causal_thing.action_resolution.v2"
            or resolution.get("state") != "ready"
            or resolution.get("selected_binding_id")
            != value.source_binding_id
            or resolution.get(
                "recognition_attention_receipt_sha256"
            ) != value.recognition_attention_receipt_sha256
            or resolution.get(
                "attention_context_receipt_sha256"
            ) != value.attention_context_receipt_sha256
            or resolution.get(
                "focused_relation_receipt_sha256"
            ) != value.focused_relation_receipt_sha256
            or resolution.get(
                "self_world_state_receipt_sha256"
            ) != value.self_world_state_receipt_sha256
            or resolution.get(
                "world_observation_receipt_sha256"
            ) != value.world_observation_receipt_sha256
            or resolution.get(
                "perspective_model_receipt_sha256s"
            ) != list(value.perspective_model_receipt_sha256s)
            or not isinstance(
                resolution.get("authority_receipt_sha256"),
                str,
            )
        ):
            raise ValueError(
                "THING action intent resolution record changed"
            )
        expected = hmac.new(
            self._intent_key,
            _INTENT_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("THING action intent authority changed")

    def issue(
        self,
        *,
        settlement: CausalExperienceSettlement,
        resolution: CausalThingActionResolution,
        recognition_attention_owner: CausalRecognitionAttentionOwner,
        attention_state: CausalRecognitionAttentionState,
        perspective_owner: EmbodiedOtherPerspectiveOwner,
        self_world_state: SelfWorldState,
        perspective_models: tuple[OtherBodyPerspectiveModel, ...],
    ) -> CausalThingActionIntent:
        self._deliberation.verify_current_resolution(
            settlement,
            resolution,
            recognition_attention_owner=recognition_attention_owner,
            attention_state=attention_state,
            perspective_owner=perspective_owner,
            self_world_state=self_world_state,
            perspective_models=perspective_models,
        )
        selected = resolution.selected
        if resolution.state != "ready" or selected is None:
            raise ValueError(
                "THING action intent requires one ready relation"
            )
        current = PerceptionWitness.from_settlement(
            settlement,
            max_bytes=self._profile.max_witness_bytes,
        )
        provisional = CausalThingActionIntent(
            current_witness=current,
            resolution_record=resolution.record(),
            recognition_attention_receipt_sha256=(
                resolution.recognition_attention_receipt_sha256
            ),
            attention_context_receipt_sha256=(
                resolution.attention_context_receipt_sha256
            ),
            focused_relation_receipt_sha256=(
                resolution.focused_relation_receipt_sha256
            ),
            self_world_state_receipt_sha256=(
                resolution.self_world_state_receipt_sha256
            ),
            world_observation_receipt_sha256=(
                resolution.world_observation_receipt_sha256
            ),
            perspective_model_receipt_sha256s=(
                resolution.perspective_model_receipt_sha256s
            ),
            thing_id=selected.thing_id,
            source_binding_id=selected.binding_id,
            action=selected.action,
            learned_trigger_witness=selected.trigger_witness,
            expected_outcome_witness=selected.outcome_witness,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._intent_key,
            _INTENT_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        intent = CausalThingActionIntent(
            current_witness=provisional.current_witness,
            resolution_record=provisional.resolution_record,
            recognition_attention_receipt_sha256=(
                provisional.recognition_attention_receipt_sha256
            ),
            attention_context_receipt_sha256=(
                provisional.attention_context_receipt_sha256
            ),
            focused_relation_receipt_sha256=(
                provisional.focused_relation_receipt_sha256
            ),
            self_world_state_receipt_sha256=(
                provisional.self_world_state_receipt_sha256
            ),
            world_observation_receipt_sha256=(
                provisional.world_observation_receipt_sha256
            ),
            perspective_model_receipt_sha256s=(
                provisional.perspective_model_receipt_sha256s
            ),
            thing_id=provisional.thing_id,
            source_binding_id=provisional.source_binding_id,
            action=provisional.action,
            learned_trigger_witness=(
                provisional.learned_trigger_witness
            ),
            expected_outcome_witness=(
                provisional.expected_outcome_witness
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self._verify_intent(intent)
        receipt = intent.authority_receipt_sha256
        with self._lock:
            existing = self._live.get(receipt)
            if existing is not None:
                if existing != intent:
                    raise ValueError(
                        "THING action intent receipt changed"
                    )
                return existing
            if len(self._live) >= self._profile.max_live_intents:
                raise RuntimeError(
                    "THING action live intent capacity exhausted"
                )
            staged = dict(self._live)
            staged[receipt] = intent
            self._encoded(staged)
            self._live = staged
        return intent

    def verify_live(self, value: CausalThingActionIntent) -> bool:
        try:
            self._verify_intent(value)
        except (TypeError, ValueError):
            return False
        with self._lock:
            return (
                self._live.get(value.authority_receipt_sha256) == value
            )

    def resolve_live(
        self,
        intent_receipt_sha256: str,
    ) -> CausalThingActionIntent:
        """Resolve one exact live intent by its authenticated receipt."""

        _sha(intent_receipt_sha256, "resolved THING action intent")
        with self._lock:
            value = self._live.get(intent_receipt_sha256)
            if value is None:
                raise ValueError("THING action intent is not live")
            self._verify_intent(value)
            return value

    def consume(
        self,
        *,
        intent_receipt_sha256: str,
    ) -> CausalThingActionIntent:
        _sha(intent_receipt_sha256, "consumed THING action intent")
        with self._lock:
            value = self._live.get(intent_receipt_sha256)
            if value is None:
                raise ValueError("THING action intent is not live")
            self._verify_intent(value)
            staged = dict(self._live)
            del staged[intent_receipt_sha256]
            self._encoded(staged)
            self._live = staged
            return value

    @contextmanager
    def executing(
        self,
        value: CausalThingActionIntent,
    ) -> Iterator[None]:
        """Hold one live intent until a physical outcome commits."""

        self._verify_intent(value)
        receipt = value.authority_receipt_sha256
        with self._lock:
            if self._live.get(receipt) != value:
                raise ValueError("THING action intent is not live")
            staged = dict(self._live)
            del staged[receipt]
            self._encoded(staged)
            yield
            self._live = staged

    def _body(
        self,
        live: Mapping[str, CausalThingActionIntent],
    ) -> dict[str, object]:
        return {
            "intents": [
                live[key].record() for key in sorted(live)
            ],
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        live: Mapping[str, CausalThingActionIntent],
    ) -> bytes:
        body = self._body(live)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError(
                "THING action intent state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._live)

    def _intent_from_record(
        self,
        value: object,
    ) -> CausalThingActionIntent:
        expected = {
            "action",
            "attention_context_receipt_sha256",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "current_witness",
            "expected_outcome_witness",
            "focused_relation_receipt_sha256",
            "learned_trigger_witness",
            "perspective_model_receipt_sha256s",
            "recognition_attention_receipt_sha256",
            "resolution_record",
            "schema",
            "self_world_state_receipt_sha256",
            "source_binding_id",
            "thing_id",
            "world_observation_receipt_sha256",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != INTENT_SCHEMA
            or not isinstance(value.get("resolution_record"), Mapping)
        ):
            raise ValueError(
                "THING action intent record is malformed"
            )
        intent = CausalThingActionIntent(
            current_witness=_witness_from(
                value.get("current_witness"),
                max_bytes=self._profile.max_witness_bytes,
            ),
            resolution_record=dict(value["resolution_record"]),
            recognition_attention_receipt_sha256=value.get(
                "recognition_attention_receipt_sha256"
            ),
            attention_context_receipt_sha256=value.get(
                "attention_context_receipt_sha256"
            ),
            focused_relation_receipt_sha256=value.get(
                "focused_relation_receipt_sha256"
            ),
            self_world_state_receipt_sha256=value.get(
                "self_world_state_receipt_sha256"
            ),
            world_observation_receipt_sha256=value.get(
                "world_observation_receipt_sha256"
            ),
            perspective_model_receipt_sha256s=tuple(
                value.get("perspective_model_receipt_sha256s", ())
            ),
            thing_id=value.get("thing_id"),
            source_binding_id=value.get("source_binding_id"),
            action=_action_from(
                value.get("action"),
                max_command_bytes=4_096,
            ),
            learned_trigger_witness=_witness_from(
                value.get("learned_trigger_witness"),
                max_bytes=self._profile.max_witness_bytes,
            ),
            expected_outcome_witness=_witness_from(
                value.get("expected_outcome_witness"),
                max_bytes=self._profile.max_witness_bytes,
            ),
            authority_hmac_sha256=value.get(
                "authority_hmac_sha256"
            ),
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        self._verify_intent(intent)
        if intent.record() != dict(value):
            raise ValueError(
                "THING action intent record is not canonical"
            )
        return intent

    def restore_encoded(self, encoded: bytes) -> None:
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > self._profile.max_state_bytes
        ):
            raise ValueError(
                "THING action intent state boundary changed"
            )
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "THING action intent state is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or _canonical(envelope) != encoded
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
        ):
            raise ValueError(
                "THING action intent state envelope changed"
            )
        body = envelope["body"]
        expected_hmac = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected_hmac,
            envelope.get("state_hmac_sha256", ""),
        ):
            raise ValueError(
                "THING action intent state authority changed"
            )
        if (
            set(body) != {"intents", "profile", "schema"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != self._profile.record()
            or not isinstance(body.get("intents"), list)
            or len(body["intents"])
            > self._profile.max_live_intents
        ):
            raise ValueError(
                "THING action intent state body changed"
            )
        restored = tuple(
            self._intent_from_record(item)
            for item in body["intents"]
        )
        staged = {
            item.authority_receipt_sha256: item
            for item in restored
        }
        if (
            len(staged) != len(restored)
            or [item.authority_receipt_sha256 for item in restored]
            != sorted(staged)
            or self._encoded(staged) != encoded
        ):
            raise ValueError(
                "THING action intent state is not canonical"
            )
        with self._lock:
            self._live = staged

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self._encoded(self._live)
            return {
                "full_field": True,
                "live_intents": len(self._live),
                "max_live_intents": (
                    self._profile.max_live_intents
                ),
                "reduced_approximation": False,
                "schema": (
                    "guala.causal_thing.action_intent.status.v1"
                ),
                "state_bytes": len(encoded),
                "state_capacity_bytes": (
                    self._profile.max_state_bytes
                ),
            }


__all__ = (
    "CausalThingActionIntent",
    "CausalThingActionIntentOwner",
    "CausalThingActionIntentProfile",
)
