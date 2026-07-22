"""Bounded learned causal-action ownership for verified sensory settlements.

This owner never derives an answer from text, chi, Atlas proximity, a score,
or a fixed response scaffold.  A learned action requires two independently
verified full-field causal experiences: the triggering perceived occurrence
and a separately perceived spoken action.  An authenticated teacher relation
joins those experiences.  Formation is then routed by the stable learned
auditory-class authority while the current complete settlement remains the
mandatory release authority.

The learned spoken-form class routes this conversational action, while every
contemporaneous sense interpretation remains inside the mandatory current
settlement and the released action authority.  No unselected sense is reduced
or discarded.  The owner keeps no raw sensor stream, no lifetime experience
index, no background queue, and no immutable generation tree.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.model import receipt_sha256, sha256_digest
from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryRecognitionState,
    AuditoryReciprocityKind,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


CAUSAL_ACTION_STATE_SCHEMA = "guala.causal_action.state.v1"
CAUSAL_ACTION_ENVELOPE_SCHEMA = "guala.causal_action.hmac.v1"
CAUSAL_ACTION_TEACHER_RELATION_SCHEMA = (
    "guala.causal_action.teacher_relation.v1"
)
CAUSAL_ACTION_SETTLEMENT_SCHEMA = "guala.causal_action.settlement.v1"
CAUSAL_ACTION_EXACT_CLOSE_SCHEMA = "guala.causal_action.exact_close.v1"
CAUSAL_ACTION_HMAC_DOMAIN = b"guala-causal-action-state-v1\0"
CAUSAL_ACTION_TEACHER_HMAC_DOMAIN = b"guala-causal-action-teacher-v1\0"

DEFAULT_TRANSIENT_CAPACITY = 4
DEFAULT_ACTION_CAPACITY = 64
DEFAULT_WITNESS_CAPACITY = 128
DEFAULT_SCALAR_CAPACITY = 512
DEFAULT_ENCODED_BYTE_CAPACITY = 16 * 1024 * 1024


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _key_bytes(value: object | None) -> bytes | None:
    if value is None or value == "" or value == b"":
        return None
    if isinstance(value, str):
        encoded = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        encoded = bytes(value)
    else:
        raise ValueError("causal action authority key must be bytes or text")
    if not encoded:
        return None
    return encoded


def _signature(key: bytes, domain: bytes, payload: bytes) -> str:
    return hmac.new(key, domain + payload, hashlib.sha256).hexdigest()


def _canonical_scalars(value: object, name: str) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{name} must be a nonempty scalar sequence")
    scalars = tuple(value)
    if any(
        isinstance(item, bool)
        or not isinstance(item, int)
        or item < 0
        or item > 0x10FFFF
        or 0xD800 <= item <= 0xDFFF
        for item in scalars
    ):
        raise ValueError(f"{name} contains an invalid Unicode scalar")
    return scalars


@dataclass(frozen=True, slots=True)
class CausalActionWitness:
    settlement_receipt_sha256: str
    settlement_payload_base64: str
    event_id: str
    structural_fingerprint: str
    recognition_class_authority_receipt_sha256: str
    recognition_occurrence_authority_receipt_sha256: str
    unicode_scalars: tuple[int, ...]

    def as_record(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "recognition_class_authority_receipt_sha256": (
                self.recognition_class_authority_receipt_sha256
            ),
            "recognition_occurrence_authority_receipt_sha256": (
                self.recognition_occurrence_authority_receipt_sha256
            ),
            "settlement_payload_base64": self.settlement_payload_base64,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "structural_fingerprint": self.structural_fingerprint,
            "unicode_scalars": list(self.unicode_scalars),
        }

    def verify(self) -> None:
        sha256_digest(
            self.settlement_receipt_sha256,
            "causal action witness settlement receipt",
        )
        sha256_digest(self.event_id, "causal action witness event")
        sha256_digest(
            self.structural_fingerprint,
            "causal action witness structural fingerprint",
        )
        sha256_digest(
            self.recognition_class_authority_receipt_sha256,
            "causal action witness learned class",
        )
        sha256_digest(
            self.recognition_occurrence_authority_receipt_sha256,
            "causal action witness recognition occurrence",
        )
        scalars = _canonical_scalars(
            self.unicode_scalars, "causal action witness"
        )
        try:
            payload = base64.b64decode(
                self.settlement_payload_base64, validate=True
            )
        except Exception as error:
            raise ValueError(
                "causal action witness payload is not canonical base64"
            ) from error
        if (
            not payload
            or base64.b64encode(payload).decode("ascii")
            != self.settlement_payload_base64
            or receipt_sha256(payload) != self.settlement_receipt_sha256
        ):
            raise ValueError("causal action witness payload receipt changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "causal action witness settlement is not canonical JSON"
            ) from error
        if _canonical_bytes(decoded) != payload:
            raise ValueError(
                "causal action witness settlement bytes are not canonical"
            )
        interpretations = decoded.get("interpretations")
        language_events = decoded.get("language_events")
        if (
            decoded.get("event_id") != self.event_id
            or decoded.get("structural_fingerprint")
            != self.structural_fingerprint
            or not isinstance(interpretations, list)
            or len(interpretations) != 6
            or not isinstance(language_events, list)
            or len(language_events) != 1
        ):
            raise ValueError("causal action witness settlement identity changed")
        sense_states = {
            item.get("sense"): item.get("state")
            for item in interpretations
            if isinstance(item, dict)
        }
        if (
            set(sense_states) != {
                "sight", "sound", "touch", "smell", "taste", "body"
            }
            or sense_states["sound"] != "observed"
            or any(
                state not in {"observed", "sensor_unavailable", "unknown"}
                for state in sense_states.values()
            )
        ):
            raise ValueError(
                "causal action witness requires complete six-sense authority"
            )
        language = language_events[0]
        occurrence = language.get("recognition_occurrence")
        if (
            not isinstance(occurrence, dict)
            or occurrence.get("state") != AuditoryRecognitionState.UNIQUE.value
            or occurrence.get("kind")
            != AuditoryReciprocityKind.SPOKEN_FORM.value
            or occurrence.get("authority_receipt_sha256")
            != self.recognition_occurrence_authority_receipt_sha256
            or occurrence.get("selected_class_authority_receipt_sha256")
            != self.recognition_class_authority_receipt_sha256
            or tuple(language.get("unicode_scalars") or ()) != scalars
            or "".join(chr(value) for value in scalars)
            != language.get("form")
        ):
            raise ValueError(
                "causal action witness recognition authority changed"
            )

    @classmethod
    def from_record(cls, value: object) -> "CausalActionWitness":
        if not isinstance(value, Mapping) or set(value) != {
            "event_id",
            "recognition_class_authority_receipt_sha256",
            "recognition_occurrence_authority_receipt_sha256",
            "settlement_payload_base64",
            "settlement_receipt_sha256",
            "structural_fingerprint",
            "unicode_scalars",
        }:
            raise ValueError("causal action witness record fields changed")
        witness = cls(
            settlement_receipt_sha256=value.get(
                "settlement_receipt_sha256"
            ),
            settlement_payload_base64=value.get(
                "settlement_payload_base64"
            ),
            event_id=value.get("event_id"),
            structural_fingerprint=value.get("structural_fingerprint"),
            recognition_class_authority_receipt_sha256=value.get(
                "recognition_class_authority_receipt_sha256"
            ),
            recognition_occurrence_authority_receipt_sha256=value.get(
                "recognition_occurrence_authority_receipt_sha256"
            ),
            unicode_scalars=_canonical_scalars(
                value.get("unicode_scalars"), "causal action witness"
            ),
        )
        witness.verify()
        if witness.as_record() != dict(value):
            raise ValueError("causal action witness record is not canonical")
        return witness


@dataclass(frozen=True, slots=True)
class CausalActionTeacherRelation:
    trigger_settlement_receipt_sha256: str
    trigger_class_authority_receipt_sha256: str
    action_settlement_receipt_sha256: str
    action_class_authority_receipt_sha256: str
    source: str
    issued_at_unix_ns: int
    nonce: str
    authority_hmac_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action_class_authority_receipt_sha256": (
                self.action_class_authority_receipt_sha256
            ),
            "action_settlement_receipt_sha256": (
                self.action_settlement_receipt_sha256
            ),
            "issued_at_unix_ns": self.issued_at_unix_ns,
            "nonce": self.nonce,
            "schema": CAUSAL_ACTION_TEACHER_RELATION_SCHEMA,
            "source": self.source,
            "trigger_class_authority_receipt_sha256": (
                self.trigger_class_authority_receipt_sha256
            ),
            "trigger_settlement_receipt_sha256": (
                self.trigger_settlement_receipt_sha256
            ),
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
        }

    def verify(self, key: bytes) -> None:
        for value, name in (
            (self.trigger_settlement_receipt_sha256, "trigger settlement"),
            (self.trigger_class_authority_receipt_sha256, "trigger class"),
            (self.action_settlement_receipt_sha256, "action settlement"),
            (self.action_class_authority_receipt_sha256, "action class"),
            (self.authority_hmac_sha256, "teacher relation HMAC"),
        ):
            sha256_digest(value, f"causal action {name}")
        if (
            self.source not in {"joe", "wc"}
            or isinstance(self.issued_at_unix_ns, bool)
            or not isinstance(self.issued_at_unix_ns, int)
            or self.issued_at_unix_ns <= 0
            or not isinstance(self.nonce, str)
            or len(self.nonce) != 64
        ):
            raise ValueError("causal action teacher relation is malformed")
        try:
            nonce = bytes.fromhex(self.nonce)
        except ValueError as error:
            raise ValueError(
                "causal action teacher relation nonce is malformed"
            ) from error
        if len(nonce) != 32 or nonce.hex() != self.nonce:
            raise ValueError("causal action teacher relation nonce is malformed")
        expected = _signature(
            key,
            CAUSAL_ACTION_TEACHER_HMAC_DOMAIN,
            _canonical_bytes(self.unsigned_record()),
        )
        if not hmac.compare_digest(expected, self.authority_hmac_sha256):
            raise ValueError("causal action teacher relation HMAC changed")

    @classmethod
    def from_record(
        cls, value: object, *, key: bytes
    ) -> "CausalActionTeacherRelation":
        if not isinstance(value, Mapping) or set(value) != {
            "action_class_authority_receipt_sha256",
            "action_settlement_receipt_sha256",
            "authority_hmac_sha256",
            "issued_at_unix_ns",
            "nonce",
            "schema",
            "source",
            "trigger_class_authority_receipt_sha256",
            "trigger_settlement_receipt_sha256",
        } or value.get("schema") != CAUSAL_ACTION_TEACHER_RELATION_SCHEMA:
            raise ValueError("causal action teacher relation fields changed")
        relation = cls(
            trigger_settlement_receipt_sha256=value.get(
                "trigger_settlement_receipt_sha256"
            ),
            trigger_class_authority_receipt_sha256=value.get(
                "trigger_class_authority_receipt_sha256"
            ),
            action_settlement_receipt_sha256=value.get(
                "action_settlement_receipt_sha256"
            ),
            action_class_authority_receipt_sha256=value.get(
                "action_class_authority_receipt_sha256"
            ),
            source=value.get("source"),
            issued_at_unix_ns=value.get("issued_at_unix_ns"),
            nonce=value.get("nonce"),
            authority_hmac_sha256=value.get("authority_hmac_sha256"),
        )
        relation.verify(key)
        if relation.as_record() != dict(value):
            raise ValueError(
                "causal action teacher relation is not canonical"
            )
        return relation


@dataclass(frozen=True, slots=True)
class CausalActionBinding:
    binding_id: str
    trigger_witness_receipt_sha256: str
    trigger_class_authority_receipt_sha256: str
    action_witness_receipt_sha256: str
    action_class_authority_receipt_sha256: str
    unicode_scalars: tuple[int, ...]
    teacher_relation: CausalActionTeacherRelation
    binding_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_class_authority_receipt_sha256": (
                self.action_class_authority_receipt_sha256
            ),
            "action_witness_receipt_sha256": (
                self.action_witness_receipt_sha256
            ),
            "binding_id": self.binding_id,
            "schema": "guala.causal_action.binding.v1",
            "teacher_relation": self.teacher_relation.as_record(),
            "trigger_class_authority_receipt_sha256": (
                self.trigger_class_authority_receipt_sha256
            ),
            "trigger_witness_receipt_sha256": (
                self.trigger_witness_receipt_sha256
            ),
            "unicode_scalars": list(self.unicode_scalars),
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "binding_receipt_sha256": self.binding_receipt_sha256,
        }

    def verify(self, key: bytes) -> None:
        self.teacher_relation.verify(key)
        scalars = _canonical_scalars(
            self.unicode_scalars, "causal action binding"
        )
        semantic_id = _digest({
            "action_class_authority_receipt_sha256": (
                self.action_class_authority_receipt_sha256
            ),
            "schema": "guala.causal_action.semantic_relation.v1",
            "trigger_class_authority_receipt_sha256": (
                self.trigger_class_authority_receipt_sha256
            ),
            "unicode_scalars": list(scalars),
        })
        if self.binding_id != semantic_id:
            raise ValueError("causal action binding identity changed")
        if _digest(self.payload()) != self.binding_receipt_sha256:
            raise ValueError("causal action binding receipt changed")
        for value, name in (
            (self.binding_id, "binding id"),
            (self.binding_receipt_sha256, "binding receipt"),
            (self.trigger_witness_receipt_sha256, "trigger witness"),
            (self.trigger_class_authority_receipt_sha256, "trigger class"),
            (self.action_witness_receipt_sha256, "action witness"),
            (self.action_class_authority_receipt_sha256, "action class"),
        ):
            sha256_digest(value, f"causal action {name}")

    @classmethod
    def from_record(
        cls, value: object, *, key: bytes
    ) -> "CausalActionBinding":
        if not isinstance(value, Mapping) or set(value) != {
            "action_class_authority_receipt_sha256",
            "action_witness_receipt_sha256",
            "binding_id",
            "binding_receipt_sha256",
            "schema",
            "teacher_relation",
            "trigger_class_authority_receipt_sha256",
            "trigger_witness_receipt_sha256",
            "unicode_scalars",
        } or value.get("schema") != "guala.causal_action.binding.v1":
            raise ValueError("causal action binding fields changed")
        binding = cls(
            binding_id=value.get("binding_id"),
            trigger_witness_receipt_sha256=value.get(
                "trigger_witness_receipt_sha256"
            ),
            trigger_class_authority_receipt_sha256=value.get(
                "trigger_class_authority_receipt_sha256"
            ),
            action_witness_receipt_sha256=value.get(
                "action_witness_receipt_sha256"
            ),
            action_class_authority_receipt_sha256=value.get(
                "action_class_authority_receipt_sha256"
            ),
            unicode_scalars=_canonical_scalars(
                value.get("unicode_scalars"), "causal action binding"
            ),
            teacher_relation=CausalActionTeacherRelation.from_record(
                value.get("teacher_relation"), key=key
            ),
            binding_receipt_sha256=value.get("binding_receipt_sha256"),
        )
        binding.verify(key)
        if binding.as_record() != dict(value):
            raise ValueError("causal action binding is not canonical")
        return binding


@dataclass(frozen=True, slots=True)
class CausalActionProvenance:
    current_settlement_receipt_sha256: str
    current_recognition_occurrence_receipt_sha256: str
    trigger_class_authority_receipt_sha256: str
    binding_id: str
    binding_receipt_sha256: str
    action_witness_receipt_sha256: str
    teacher_relation_authority_hmac_sha256: str
    exact_close_receipt_sha256: str
    action_authority_receipt_sha256: str

    def as_record(self) -> dict[str, object]:
        return {
            "action_authority_receipt_sha256": (
                self.action_authority_receipt_sha256
            ),
            "action_witness_receipt_sha256": (
                self.action_witness_receipt_sha256
            ),
            "authority": "causal_action_v1",
            "binding_id": self.binding_id,
            "binding_receipt_sha256": self.binding_receipt_sha256,
            "current_recognition_occurrence_receipt_sha256": (
                self.current_recognition_occurrence_receipt_sha256
            ),
            "current_settlement_receipt_sha256": (
                self.current_settlement_receipt_sha256
            ),
            "exact_close_receipt_sha256": (
                self.exact_close_receipt_sha256
            ),
            "teacher_relation_authority_hmac_sha256": (
                self.teacher_relation_authority_hmac_sha256
            ),
            "trigger_class_authority_receipt_sha256": (
                self.trigger_class_authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class CausalActionSettlement:
    status: str
    content: str = ""
    unicode_scalars: tuple[int, ...] = ()
    n_commits: int = 0
    committed_sections: tuple[str, ...] = ()
    commit_provenance: tuple[CausalActionProvenance, ...] = ()
    stop_reason: str | None = None
    tick: int = 0
    exact_close_receipt_sha256: str | None = None
    authority_receipt_sha256: str | None = None
    authority_payload: bytes | None = field(
        default=None, repr=False
    )
    _owner_token: object | None = field(
        default=None, repr=False, compare=False
    )

    def verify_receipts(self) -> None:
        if (
            self.status not in {"committed", "unknown", "ambiguous"}
            or isinstance(self.tick, bool)
            or not isinstance(self.tick, int)
            or self.tick < 0
        ):
            raise ValueError("causal action settlement state is malformed")
        if self.status != "committed":
            expected_reason = f"causal_action_{self.status}"
            if self.stop_reason != expected_reason:
                raise ValueError("causal action silent reason changed")
            if any((
                self.content,
                self.unicode_scalars,
                self.n_commits,
                self.committed_sections,
                self.commit_provenance,
                self.exact_close_receipt_sha256,
                self.authority_receipt_sha256,
                self.authority_payload,
            )):
                raise ValueError("silent causal action exposed staged output")
            return
        scalars = _canonical_scalars(
            self.unicode_scalars, "causal action settlement"
        )
        if (
            self.stop_reason is not None
            or self.content != "".join(chr(value) for value in scalars)
            or self.n_commits != len(scalars)
            or self.committed_sections != ("causal_action",)
            or len(self.commit_provenance) != 1
            or not isinstance(self.authority_payload, bytes)
        ):
            raise ValueError("causal action settlement is not exact-closed")
        sha256_digest(
            self.exact_close_receipt_sha256,
            "causal action exact-close receipt",
        )
        if receipt_sha256(self.authority_payload) != sha256_digest(
            self.authority_receipt_sha256,
            "causal action authority receipt",
        ):
            raise ValueError("causal action settlement authority changed")
        payload = json.loads(self.authority_payload.decode("utf-8"))
        if (
            _canonical_bytes(payload) != self.authority_payload
            or payload.get("schema") != CAUSAL_ACTION_SETTLEMENT_SCHEMA
            or tuple(payload.get("unicode_scalars") or ()) != scalars
            or payload.get("exact_close_receipt_sha256")
            != self.exact_close_receipt_sha256
        ):
            raise ValueError("causal action settlement payload changed")


class CausalActionOwner:
    """Single serial owner of bounded learned causal action relations."""

    def __init__(
        self,
        *,
        log_event: Callable[..., None],
        authority_key: object | None,
        transient_capacity: int = DEFAULT_TRANSIENT_CAPACITY,
        action_capacity: int = DEFAULT_ACTION_CAPACITY,
        witness_capacity: int = DEFAULT_WITNESS_CAPACITY,
        scalar_capacity: int = DEFAULT_SCALAR_CAPACITY,
        encoded_byte_capacity: int = DEFAULT_ENCODED_BYTE_CAPACITY,
    ) -> None:
        capacities = (
            transient_capacity,
            action_capacity,
            witness_capacity,
            scalar_capacity,
            encoded_byte_capacity,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
            for value in capacities
        ):
            raise ValueError("causal action capacities must be positive")
        self._log_event = log_event
        self._key = _key_bytes(authority_key)
        self._transient_capacity = transient_capacity
        self._action_capacity = action_capacity
        self._witness_capacity = witness_capacity
        self._scalar_capacity = scalar_capacity
        self._encoded_byte_capacity = encoded_byte_capacity
        self._lock = threading.RLock()
        self._owner_token = object()
        self._transient: OrderedDict[
            str, CausalExperienceSettlement
        ] = OrderedDict()
        self._transient_by_source_event: dict[str, str] = {}
        self._witnesses: dict[str, CausalActionWitness] = {}
        self._bindings: dict[str, CausalActionBinding] = {}
        self._binding_ids_by_trigger: dict[str, set[str]] = {}
        self._accepted_teacher_nonces: set[str] = set()
        self._issued_actions: OrderedDict[
            str, CausalActionSettlement
        ] = OrderedDict()
        self._issued_action_capacity = 8
        self._formed = 0
        self._unknown = 0
        self._ambiguous = 0

    @property
    def persistence_available(self) -> bool:
        return self._key is not None

    @staticmethod
    def _witness(settlement: CausalExperienceSettlement) -> CausalActionWitness:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("causal action requires a causal experience settlement")
        settlement.verify()
        if len(settlement.language_events) != 1:
            raise ValueError(
                "causal action requires one recognized language occurrence"
            )
        language = settlement.language_events[0]
        occurrence = language.recognition_occurrence
        if occurrence is None:
            raise ValueError(
                "causal action requires learned-class recognition authority"
            )
        occurrence.verify()
        selected = occurrence.selected_class_authority_receipt_sha256
        if selected is None:
            raise ValueError("causal action recognition is not unique")
        payload = settlement.receipt_registry.resolve(
            settlement.authority_receipt_sha256,
            "causal action settlement witness",
        )
        witness = CausalActionWitness(
            settlement_receipt_sha256=settlement.authority_receipt_sha256,
            settlement_payload_base64=base64.b64encode(payload).decode("ascii"),
            event_id=settlement.event_id,
            structural_fingerprint=settlement.structural_fingerprint,
            recognition_class_authority_receipt_sha256=selected,
            recognition_occurrence_authority_receipt_sha256=(
                occurrence.authority_receipt_sha256
            ),
            unicode_scalars=language.unicode_scalars,
        )
        witness.verify()
        return witness

    @staticmethod
    def _verify_binding_evidence(
        binding: CausalActionBinding,
        witnesses: Mapping[str, CausalActionWitness],
        key: bytes,
    ) -> None:
        """Prove every persisted relation still names its exact witnesses."""
        binding.verify(key)
        trigger = witnesses.get(binding.trigger_witness_receipt_sha256)
        action = witnesses.get(binding.action_witness_receipt_sha256)
        if trigger is None or action is None:
            raise ValueError("causal action binding evidence is missing")
        trigger.verify()
        action.verify()
        relation = binding.teacher_relation
        if (
            binding.trigger_class_authority_receipt_sha256
            != trigger.recognition_class_authority_receipt_sha256
            or binding.action_class_authority_receipt_sha256
            != action.recognition_class_authority_receipt_sha256
            or binding.unicode_scalars != action.unicode_scalars
            or relation.trigger_settlement_receipt_sha256
            != trigger.settlement_receipt_sha256
            or relation.trigger_class_authority_receipt_sha256
            != trigger.recognition_class_authority_receipt_sha256
            or relation.action_settlement_receipt_sha256
            != action.settlement_receipt_sha256
            or relation.action_class_authority_receipt_sha256
            != action.recognition_class_authority_receipt_sha256
        ):
            raise ValueError("causal action binding evidence changed")

    def offer_teaching_experience(
        self, settlement: CausalExperienceSettlement
    ) -> dict[str, object]:
        """Retain only a bounded working set; expiry is explicit telemetry."""
        witness = self._witness(settlement)
        source_event_id = settlement.language_events[0].source_event_id
        expired = None
        with self._lock:
            existing = self._transient.get(witness.event_id)
            if existing is not None:
                if existing.authority_receipt_sha256 != (
                    settlement.authority_receipt_sha256
                ):
                    raise ValueError(
                        "causal action event identity was offered differently"
                    )
                if self._transient_by_source_event.get(source_event_id) != (
                    witness.event_id
                ):
                    raise ValueError(
                        "causal action source event identity changed"
                    )
                self._transient.move_to_end(witness.event_id)
                return {"accepted": True, "repeated": True, "expired": None}
            source_owner = self._transient_by_source_event.get(source_event_id)
            if source_owner is not None:
                raise ValueError(
                    "causal action source event was offered differently"
                )
            if len(self._transient) >= self._transient_capacity:
                expired, expired_settlement = self._transient.popitem(
                    last=False
                )
                del self._transient_by_source_event[
                    expired_settlement.language_events[0].source_event_id
                ]
            self._transient[witness.event_id] = settlement
            self._transient_by_source_event[source_event_id] = witness.event_id
        if expired is not None:
            try:
                self._log_event(
                    "causal_action_teaching_experience_expired",
                    causal_experience_id=expired,
                )
            except Exception:
                # Capacity settlement is complete; telemetry cannot undo it.
                pass
        return {"accepted": True, "repeated": False, "expired": expired}

    def resolve_teaching_experience_id(self, reference_id: str) -> str:
        """Resolve one bounded terminal ID to its exact causal settlement."""
        sha256_digest(reference_id, "causal action teaching reference")
        with self._lock:
            if reference_id in self._transient:
                return reference_id
            resolved = self._transient_by_source_event.get(reference_id)
            if resolved is None:
                raise ValueError(
                    "causal action teaching experience is no longer in working memory"
                )
            return resolved

    def issue_teacher_relation(
        self,
        *,
        trigger_experience_id: str,
        action_experience_id: str,
        source: str,
    ) -> CausalActionTeacherRelation:
        if self._key is None:
            raise RuntimeError(
                "causal action teaching authority key is unavailable"
            )
        trigger_experience_id = self.resolve_teaching_experience_id(
            trigger_experience_id
        )
        action_experience_id = self.resolve_teaching_experience_id(
            action_experience_id
        )
        if trigger_experience_id == action_experience_id:
            raise ValueError(
                "causal action requires separate trigger and action experiences"
            )
        with self._lock:
            trigger = self._transient.get(trigger_experience_id)
            action = self._transient.get(action_experience_id)
        if trigger is None or action is None:
            raise ValueError(
                "causal action teaching experience is no longer in working memory"
            )
        trigger_witness = self._witness(trigger)
        action_witness = self._witness(action)
        unsigned = {
            "action_class_authority_receipt_sha256": (
                action_witness.recognition_class_authority_receipt_sha256
            ),
            "action_settlement_receipt_sha256": (
                action_witness.settlement_receipt_sha256
            ),
            "issued_at_unix_ns": time.time_ns(),
            "nonce": secrets.token_hex(32),
            "schema": CAUSAL_ACTION_TEACHER_RELATION_SCHEMA,
            "source": source,
            "trigger_class_authority_receipt_sha256": (
                trigger_witness.recognition_class_authority_receipt_sha256
            ),
            "trigger_settlement_receipt_sha256": (
                trigger_witness.settlement_receipt_sha256
            ),
        }
        relation = CausalActionTeacherRelation(
            trigger_settlement_receipt_sha256=(
                unsigned["trigger_settlement_receipt_sha256"]
            ),
            trigger_class_authority_receipt_sha256=(
                unsigned["trigger_class_authority_receipt_sha256"]
            ),
            action_settlement_receipt_sha256=(
                unsigned["action_settlement_receipt_sha256"]
            ),
            action_class_authority_receipt_sha256=(
                unsigned["action_class_authority_receipt_sha256"]
            ),
            source=source,
            issued_at_unix_ns=unsigned["issued_at_unix_ns"],
            nonce=unsigned["nonce"],
            authority_hmac_sha256=_signature(
                self._key,
                CAUSAL_ACTION_TEACHER_HMAC_DOMAIN,
                _canonical_bytes(unsigned),
            ),
        )
        relation.verify(self._key)
        return relation

    def _state_record(
        self,
        witnesses: Mapping[str, CausalActionWitness],
        bindings: Mapping[str, CausalActionBinding],
    ) -> dict[str, object]:
        return {
            "action_capacity": self._action_capacity,
            "bindings": [
                bindings[key].as_record() for key in sorted(bindings)
            ],
            "encoded_byte_capacity": self._encoded_byte_capacity,
            "scalar_capacity": self._scalar_capacity,
            "schema": CAUSAL_ACTION_STATE_SCHEMA,
            "transient_capacity": self._transient_capacity,
            "witness_capacity": self._witness_capacity,
            "witnesses": [
                witnesses[key].as_record() for key in sorted(witnesses)
            ],
        }

    def _prospective_payload(
        self,
        witnesses: Mapping[str, CausalActionWitness],
        bindings: Mapping[str, CausalActionBinding],
    ) -> bytes:
        if len(witnesses) > self._witness_capacity:
            raise RuntimeError("causal action witness capacity is full")
        if len(bindings) > self._action_capacity:
            raise RuntimeError("causal action binding capacity is full")
        if bindings:
            if self._key is None:
                raise RuntimeError(
                    "causal action binding authority key is unavailable"
                )
            for binding in bindings.values():
                self._verify_binding_evidence(
                    binding,
                    witnesses,
                    self._key,
                )
        payload = _canonical_bytes(self._state_record(witnesses, bindings))
        if len(payload) > self._encoded_byte_capacity:
            raise RuntimeError("causal action encoded state capacity is full")
        return payload

    def learn(
        self,
        *,
        trigger_experience_id: str,
        action_experience_id: str,
        teacher_relation: CausalActionTeacherRelation,
    ) -> CausalActionBinding:
        if self._key is None:
            raise RuntimeError(
                "causal action teaching authority key is unavailable"
            )
        trigger_experience_id = self.resolve_teaching_experience_id(
            trigger_experience_id
        )
        action_experience_id = self.resolve_teaching_experience_id(
            action_experience_id
        )
        if trigger_experience_id == action_experience_id:
            raise ValueError(
                "causal action requires separate trigger and action experiences"
            )
        teacher_relation.verify(self._key)
        with self._lock:
            trigger = self._transient.get(trigger_experience_id)
            action = self._transient.get(action_experience_id)
            if trigger is None or action is None:
                raise ValueError(
                    "causal action teaching experience is no longer in working memory"
                )
            trigger_witness = self._witness(trigger)
            action_witness = self._witness(action)
            if (
                teacher_relation.trigger_settlement_receipt_sha256
                != trigger_witness.settlement_receipt_sha256
                or teacher_relation.trigger_class_authority_receipt_sha256
                != trigger_witness.recognition_class_authority_receipt_sha256
                or teacher_relation.action_settlement_receipt_sha256
                != action_witness.settlement_receipt_sha256
                or teacher_relation.action_class_authority_receipt_sha256
                != action_witness.recognition_class_authority_receipt_sha256
            ):
                raise ValueError(
                    "causal action teacher relation names different experiences"
                )
            scalars = action_witness.unicode_scalars
            if len(scalars) > self._scalar_capacity:
                raise RuntimeError(
                    "causal action expression scalar capacity is full"
                )
            binding_id = _digest({
                "action_class_authority_receipt_sha256": (
                    action_witness.recognition_class_authority_receipt_sha256
                ),
                "schema": "guala.causal_action.semantic_relation.v1",
                "trigger_class_authority_receipt_sha256": (
                    trigger_witness.recognition_class_authority_receipt_sha256
                ),
                "unicode_scalars": list(scalars),
            })
            existing = self._bindings.get(binding_id)
            if existing is not None:
                existing.verify(self._key)
                return existing
            if teacher_relation.nonce in self._accepted_teacher_nonces:
                raise ValueError(
                    "causal action teacher relation nonce was already used"
                )
            provisional = CausalActionBinding(
                binding_id=binding_id,
                trigger_witness_receipt_sha256=(
                    trigger_witness.settlement_receipt_sha256
                ),
                trigger_class_authority_receipt_sha256=(
                    trigger_witness.recognition_class_authority_receipt_sha256
                ),
                action_witness_receipt_sha256=(
                    action_witness.settlement_receipt_sha256
                ),
                action_class_authority_receipt_sha256=(
                    action_witness.recognition_class_authority_receipt_sha256
                ),
                unicode_scalars=scalars,
                teacher_relation=teacher_relation,
                binding_receipt_sha256="0" * 64,
            )
            binding = CausalActionBinding(
                binding_id=provisional.binding_id,
                trigger_witness_receipt_sha256=(
                    provisional.trigger_witness_receipt_sha256
                ),
                trigger_class_authority_receipt_sha256=(
                    provisional.trigger_class_authority_receipt_sha256
                ),
                action_witness_receipt_sha256=(
                    provisional.action_witness_receipt_sha256
                ),
                action_class_authority_receipt_sha256=(
                    provisional.action_class_authority_receipt_sha256
                ),
                unicode_scalars=provisional.unicode_scalars,
                teacher_relation=provisional.teacher_relation,
                binding_receipt_sha256=_digest(provisional.payload()),
            )
            binding.verify(self._key)
            prospective_witnesses = dict(self._witnesses)
            prospective_witnesses[
                trigger_witness.settlement_receipt_sha256
            ] = trigger_witness
            prospective_witnesses[
                action_witness.settlement_receipt_sha256
            ] = action_witness
            prospective_bindings = dict(self._bindings)
            prospective_bindings[binding.binding_id] = binding
            self._prospective_payload(
                prospective_witnesses, prospective_bindings
            )
            self._witnesses = prospective_witnesses
            self._bindings = prospective_bindings
            self._binding_ids_by_trigger.setdefault(
                binding.trigger_class_authority_receipt_sha256, set()
            ).add(binding.binding_id)
            self._accepted_teacher_nonces.add(teacher_relation.nonce)
        self._log_event(
            "causal_action_learned",
            action_witness_receipt_sha256=(
                binding.action_witness_receipt_sha256
            ),
            binding_id=binding.binding_id,
            trigger_class_authority_receipt_sha256=(
                binding.trigger_class_authority_receipt_sha256
            ),
        )
        return binding

    def teach(
        self,
        *,
        trigger_experience_id: str,
        action_experience_id: str,
        source: str,
    ) -> CausalActionBinding:
        relation = self.issue_teacher_relation(
            trigger_experience_id=trigger_experience_id,
            action_experience_id=action_experience_id,
            source=source,
        )
        return self.learn(
            trigger_experience_id=trigger_experience_id,
            action_experience_id=action_experience_id,
            teacher_relation=relation,
        )

    def form(
        self,
        settlement: CausalExperienceSettlement,
        *,
        tick: int,
    ) -> CausalActionSettlement:
        witness = self._witness(settlement)
        trigger_class = witness.recognition_class_authority_receipt_sha256
        with self._lock:
            binding_ids = tuple(sorted(
                self._binding_ids_by_trigger.get(trigger_class, ())
            ))
            if not binding_ids:
                self._unknown += 1
                return CausalActionSettlement(
                    status="unknown",
                    stop_reason="causal_action_unknown",
                    tick=tick,
                )
            if len(binding_ids) != 1:
                self._ambiguous += 1
                return CausalActionSettlement(
                    status="ambiguous",
                    stop_reason="causal_action_ambiguous",
                    tick=tick,
                )
            binding = self._bindings[binding_ids[0]]
            if self._key is None:
                raise RuntimeError(
                    "causal action persistence authority is unavailable"
                )
            self._verify_binding_evidence(
                binding,
                self._witnesses,
                self._key,
            )
            action_witness = self._witnesses.get(
                binding.action_witness_receipt_sha256
            )
            if action_witness is None:
                raise RuntimeError("causal action lost its action witness")
            scalars = binding.unicode_scalars
            exact_close_payload = {
                "binding_id": binding.binding_id,
                "current_settlement_receipt_sha256": (
                    witness.settlement_receipt_sha256
                ),
                "schema": CAUSAL_ACTION_EXACT_CLOSE_SCHEMA,
                "unicode_scalars": list(scalars),
            }
            exact_close = _digest(exact_close_payload)
            action_payload_value = {
                "action_witness_receipt_sha256": (
                    binding.action_witness_receipt_sha256
                ),
                "binding_id": binding.binding_id,
                "binding_receipt_sha256": binding.binding_receipt_sha256,
                "current_recognition_occurrence_receipt_sha256": (
                    witness.recognition_occurrence_authority_receipt_sha256
                ),
                "current_settlement_receipt_sha256": (
                    witness.settlement_receipt_sha256
                ),
                "exact_close_receipt_sha256": exact_close,
                "schema": CAUSAL_ACTION_SETTLEMENT_SCHEMA,
                "teacher_relation_authority_hmac_sha256": (
                    binding.teacher_relation.authority_hmac_sha256
                ),
                "trigger_class_authority_receipt_sha256": trigger_class,
                "unicode_scalars": list(scalars),
            }
            action_payload = _canonical_bytes(action_payload_value)
            action_authority = receipt_sha256(action_payload)
            provenance = CausalActionProvenance(
                current_settlement_receipt_sha256=(
                    witness.settlement_receipt_sha256
                ),
                current_recognition_occurrence_receipt_sha256=(
                    witness.recognition_occurrence_authority_receipt_sha256
                ),
                trigger_class_authority_receipt_sha256=trigger_class,
                binding_id=binding.binding_id,
                binding_receipt_sha256=binding.binding_receipt_sha256,
                action_witness_receipt_sha256=(
                    binding.action_witness_receipt_sha256
                ),
                teacher_relation_authority_hmac_sha256=(
                    binding.teacher_relation.authority_hmac_sha256
                ),
                exact_close_receipt_sha256=exact_close,
                action_authority_receipt_sha256=action_authority,
            )
            result = CausalActionSettlement(
                status="committed",
                content="".join(chr(value) for value in scalars),
                unicode_scalars=scalars,
                n_commits=len(scalars),
                committed_sections=("causal_action",),
                commit_provenance=(provenance,),
                tick=tick,
                exact_close_receipt_sha256=exact_close,
                authority_receipt_sha256=action_authority,
                authority_payload=action_payload,
                _owner_token=self._owner_token,
            )
            result.verify_receipts()
            prior_issued = self._issued_actions.get(action_authority)
            if prior_issued is not None:
                prior_issued.verify_receipts()
                if (
                    prior_issued._owner_token is not self._owner_token
                    or prior_issued.authority_payload != action_payload
                ):
                    raise RuntimeError(
                        "causal action authority was issued twice differently"
                    )
                result = prior_issued
            else:
                self._issued_actions[action_authority] = result
            self._issued_actions.move_to_end(action_authority)
            while len(self._issued_actions) > self._issued_action_capacity:
                self._issued_actions.popitem(last=False)
            self._formed += 1
        self._log_event(
            "causal_action_formed",
            action_authority_receipt_sha256=action_authority,
            binding_id=binding.binding_id,
            current_settlement_receipt_sha256=(
                witness.settlement_receipt_sha256
            ),
        )
        return result

    def verify_issued(self, value: CausalActionSettlement) -> bool:
        if not isinstance(value, CausalActionSettlement):
            return False
        value.verify_receipts()
        if value.status != "committed" or value._owner_token is not self._owner_token:
            return False
        with self._lock:
            return self._issued_actions.get(
                value.authority_receipt_sha256
            ) == value

    def encoded_snapshot(self) -> dict[str, object]:
        if self._key is None:
            raise RuntimeError(
                "causal action persistence authority key is unavailable"
            )
        with self._lock:
            payload = self._prospective_payload(
                self._witnesses, self._bindings
            )
        return {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": CAUSAL_ACTION_ENVELOPE_SCHEMA,
            "state_hmac_sha256": _signature(
                self._key, CAUSAL_ACTION_HMAC_DOMAIN, payload
            ),
        }

    def working_settlements(self) -> tuple[CausalExperienceSettlement, ...]:
        with self._lock:
            return tuple(self._transient.values())

    def restore_working_settlements(
        self, values: tuple[CausalExperienceSettlement, ...]
    ) -> None:
        if (
            not isinstance(values, tuple)
            or len(values) > self._transient_capacity
        ):
            raise ValueError("causal action working-set restore is invalid")
        restored: OrderedDict[str, CausalExperienceSettlement] = OrderedDict()
        restored_sources: dict[str, str] = {}
        for settlement in values:
            witness = self._witness(settlement)
            if witness.event_id in restored:
                raise ValueError(
                    "causal action working-set repeats an experience"
                )
            source_event_id = settlement.language_events[0].source_event_id
            if source_event_id in restored_sources:
                raise ValueError(
                    "causal action working-set repeats a source event"
                )
            restored[witness.event_id] = settlement
            restored_sources[source_event_id] = witness.event_id
        with self._lock:
            self._transient = restored
            self._transient_by_source_event = restored_sources

    def restore_encoded(self, value: object) -> None:
        if self._key is None:
            raise RuntimeError(
                "causal action persistence authority key is unavailable"
            )
        if not isinstance(value, Mapping) or set(value) != {
            "payload_base64", "schema", "state_hmac_sha256"
        } or value.get("schema") != CAUSAL_ACTION_ENVELOPE_SCHEMA:
            raise ValueError("causal action state envelope is malformed")
        try:
            payload = base64.b64decode(
                value.get("payload_base64"), validate=True
            )
        except Exception as error:
            raise ValueError(
                "causal action state payload is not canonical base64"
            ) from error
        if (
            base64.b64encode(payload).decode("ascii")
            != value.get("payload_base64")
            or len(payload) > self._encoded_byte_capacity
        ):
            raise ValueError("causal action state payload boundary changed")
        expected_hmac = _signature(
            self._key, CAUSAL_ACTION_HMAC_DOMAIN, payload
        )
        if not hmac.compare_digest(
            expected_hmac, value.get("state_hmac_sha256", "")
        ):
            raise ValueError("causal action state HMAC changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("causal action state payload is invalid") from error
        if _canonical_bytes(decoded) != payload or set(decoded) != {
            "action_capacity",
            "bindings",
            "encoded_byte_capacity",
            "scalar_capacity",
            "schema",
            "transient_capacity",
            "witness_capacity",
            "witnesses",
        } or decoded.get("schema") != CAUSAL_ACTION_STATE_SCHEMA:
            raise ValueError("causal action state fields changed")
        if (
            decoded.get("action_capacity") != self._action_capacity
            or decoded.get("witness_capacity") != self._witness_capacity
            or decoded.get("transient_capacity") != self._transient_capacity
            or decoded.get("scalar_capacity") != self._scalar_capacity
            or decoded.get("encoded_byte_capacity")
            != self._encoded_byte_capacity
            or not isinstance(decoded.get("witnesses"), list)
            or not isinstance(decoded.get("bindings"), list)
        ):
            raise ValueError("causal action state capacities changed")
        witnesses: dict[str, CausalActionWitness] = {}
        for record in decoded["witnesses"]:
            witness = CausalActionWitness.from_record(record)
            if witness.settlement_receipt_sha256 in witnesses:
                raise ValueError("causal action state repeats a witness")
            witnesses[witness.settlement_receipt_sha256] = witness
        bindings: dict[str, CausalActionBinding] = {}
        trigger_index: dict[str, set[str]] = {}
        nonces = set()
        for record in decoded["bindings"]:
            binding = CausalActionBinding.from_record(record, key=self._key)
            if binding.binding_id in bindings:
                raise ValueError("causal action state repeats a binding")
            if (
                binding.trigger_witness_receipt_sha256 not in witnesses
                or binding.action_witness_receipt_sha256 not in witnesses
                or binding.teacher_relation.nonce in nonces
                or len(binding.unicode_scalars) > self._scalar_capacity
            ):
                raise ValueError("causal action state lost binding evidence")
            bindings[binding.binding_id] = binding
            trigger_index.setdefault(
                binding.trigger_class_authority_receipt_sha256, set()
            ).add(binding.binding_id)
            nonces.add(binding.teacher_relation.nonce)
        if self._prospective_payload(witnesses, bindings) != payload:
            raise ValueError("causal action state is not canonical")
        with self._lock:
            self._witnesses = witnesses
            self._bindings = bindings
            self._binding_ids_by_trigger = trigger_index
            self._accepted_teacher_nonces = nonces
            self._transient.clear()
            self._transient_by_source_event.clear()
            self._issued_actions.clear()

    def status(self) -> dict[str, object]:
        with self._lock:
            state_bytes = len(_canonical_bytes(
                self._state_record(self._witnesses, self._bindings)
            ))
            return {
                "actions": len(self._bindings),
                "action_capacity": self._action_capacity,
                "witnesses": len(self._witnesses),
                "witness_capacity": self._witness_capacity,
                "working_experiences": len(self._transient),
                "working_experience_capacity": self._transient_capacity,
                "encoded_state_bytes": state_bytes,
                "encoded_state_capacity": self._encoded_byte_capacity,
                "persistence_authority_available": self._key is not None,
                "formed": self._formed,
                "unknown": self._unknown,
                "ambiguous": self._ambiguous,
                "issued_actions": len(self._issued_actions),
                "issued_action_capacity": self._issued_action_capacity,
            }


__all__ = (
    "CausalActionBinding",
    "CausalActionOwner",
    "CausalActionProvenance",
    "CausalActionSettlement",
    "CausalActionTeacherRelation",
    "CausalActionWitness",
)
