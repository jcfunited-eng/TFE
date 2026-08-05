"""Canonical persistent memory for anonymous spatial-vocal relations."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.substrate.w1_anonymous_spatial_vocal_relation import (
    W1AnonymousSpatialVocalDistinction,
    W1AnonymousSpatialVocalLesson,
    W1AnonymousSpatialVocalRelationOwner,
)


W1_SPATIAL_VOCAL_MEMORY_PROFILE_SCHEMA = (
    "guala.w1.anonymous_spatial_vocal.memory.profile.v1"
)
W1_SPATIAL_VOCAL_MEMORY_STATE_SCHEMA = (
    "guala.w1.anonymous_spatial_vocal.memory.state.v1"
)
W1_SPATIAL_VOCAL_MEMORY_ENVELOPE_SCHEMA = (
    "guala.w1.anonymous_spatial_vocal.memory.envelope.v1"
)
_STATE_DOMAIN = b"guala-w1-anonymous-spatial-vocal-memory-v1\0"
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


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(item not in _HEX for item in value)
    ):
        raise ValueError(f"{name} must be a SHA-256 identity")
    return value


@dataclass(frozen=True, slots=True)
class W1AnonymousSpatialVocalMemoryProfile:
    profile_id: str
    max_lessons: int
    max_distinctions: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_lessons: int,
        max_distinctions: int,
        max_state_bytes: int,
    ) -> "W1AnonymousSpatialVocalMemoryProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id.strip()
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
                for value in (
                    max_lessons, max_distinctions, max_state_bytes
                )
            )
        ):
            raise ValueError("W1 spatial-vocal memory profile changed")
        provisional = cls(
            profile_id=profile_id,
            max_lessons=max_lessons,
            max_distinctions=max_distinctions,
            max_state_bytes=max_state_bytes,
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=profile_id,
            max_lessons=max_lessons,
            max_distinctions=max_distinctions,
            max_state_bytes=max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_distinctions": self.max_distinctions,
            "max_lessons": self.max_lessons,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": W1_SPATIAL_VOCAL_MEMORY_PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        _sha(self.authority_receipt_sha256, "spatial-vocal memory profile")
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 spatial-vocal memory profile changed")


class W1AnonymousSpatialVocalRelationMemoryOwner:
    """Bounded HMAC state owner cross-validated by the relation authority."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1AnonymousSpatialVocalMemoryProfile,
        relation_authority: W1AnonymousSpatialVocalRelationOwner,
    ) -> None:
        resource_profile.verify()
        key = authority_key.encode() if isinstance(authority_key, str) else bytes(
            authority_key
        )
        if not 32 <= len(key) <= 4_096:
            raise ValueError("W1 spatial-vocal memory key changed")
        if not isinstance(
            relation_authority, W1AnonymousSpatialVocalRelationOwner
        ):
            raise TypeError("W1 spatial-vocal memory requires relation authority")
        self._key = hashlib.sha256(
            _STATE_DOMAIN + hashlib.sha256(key).digest()
        ).digest()
        self._profile = resource_profile
        self._relations = relation_authority
        self._lessons: dict[str, W1AnonymousSpatialVocalLesson] = {}
        self._distinctions: dict[
            str, W1AnonymousSpatialVocalDistinction
        ] = {}
        self._lock = threading.RLock()

    def _body(self) -> dict[str, object]:
        return {
            "distinctions": [
                {
                    **self._distinctions[key].payload(),
                    "authority_hmac_sha256": (
                        self._distinctions[key].authority_hmac_sha256
                    ),
                    "authority_receipt_sha256": (
                        self._distinctions[key].authority_receipt_sha256
                    ),
                    "distinction_id": self._distinctions[key].distinction_id,
                }
                for key in sorted(self._distinctions)
            ],
            "lessons": [
                {
                    **self._lessons[key].payload(),
                    "authority_hmac_sha256": (
                        self._lessons[key].authority_hmac_sha256
                    ),
                    "authority_receipt_sha256": (
                        self._lessons[key].authority_receipt_sha256
                    ),
                    "lesson_id": self._lessons[key].lesson_id,
                }
                for key in sorted(self._lessons)
            ],
            "resource_profile": self._profile.record(),
            "schema": W1_SPATIAL_VOCAL_MEMORY_STATE_SCHEMA,
        }

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            body = self._body()
            encoded = _canonical({
                "body": body,
                "schema": W1_SPATIAL_VOCAL_MEMORY_ENVELOPE_SCHEMA,
                "state_hmac_sha256": hmac.new(
                    self._key,
                    _STATE_DOMAIN + _canonical(body),
                    hashlib.sha256,
                ).hexdigest(),
            })
            if len(encoded) > self._profile.max_state_bytes:
                raise RuntimeError("W1 spatial-vocal memory capacity exhausted")
            return encoded

    def admit_lesson(self, lesson: W1AnonymousSpatialVocalLesson) -> None:
        self._relations.verify_lesson(lesson)
        self._relations.retain_lesson(lesson)
        with self._lock:
            if lesson.lesson_id in self._lessons:
                return
            if len(self._lessons) >= self._profile.max_lessons:
                raise RuntimeError("W1 spatial-vocal lesson memory is full")
            self._lessons[lesson.lesson_id] = lesson
            try:
                self.snapshot_encoded()
            except Exception:
                self._lessons.pop(lesson.lesson_id, None)
                raise

    def admit_distinction(
        self, distinction: W1AnonymousSpatialVocalDistinction
    ) -> None:
        self._relations.verify_distinction(distinction)
        with self._lock:
            retained = {
                lesson.authority_receipt_sha256
                for lesson in self._lessons.values()
            }
            if set(
                distinction.source_lesson_receipt_sha256s
            ) - retained:
                raise ValueError(
                    "W1 spatial-vocal distinction lost retained lessons"
                )
            if distinction.distinction_id in self._distinctions:
                return
            if len(self._distinctions) >= self._profile.max_distinctions:
                raise RuntimeError("W1 spatial-vocal distinction memory is full")
            self._distinctions[distinction.distinction_id] = distinction
            try:
                self.snapshot_encoded()
            except Exception:
                self._distinctions.pop(distinction.distinction_id, None)
                raise

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
        relation_authority: W1AnonymousSpatialVocalRelationOwner,
        retained_lessons: tuple[W1AnonymousSpatialVocalLesson, ...],
        retained_distinctions: tuple[
            W1AnonymousSpatialVocalDistinction, ...
        ],
    ) -> "W1AnonymousSpatialVocalRelationMemoryOwner":
        if not isinstance(encoded, bytes):
            raise TypeError("W1 spatial-vocal memory must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "W1 spatial-vocal memory is not canonical JSON"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema")
            != W1_SPATIAL_VOCAL_MEMORY_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
            or not isinstance(envelope.get("body"), Mapping)
        ):
            raise ValueError("W1 spatial-vocal memory envelope changed")
        body = envelope["body"]
        if (
            set(body)
            != {"distinctions", "lessons", "resource_profile", "schema"}
            or body.get("schema") != W1_SPATIAL_VOCAL_MEMORY_STATE_SCHEMA
            or not isinstance(body.get("lessons"), list)
            or not isinstance(body.get("distinctions"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("W1 spatial-vocal memory body changed")
        raw_profile = body["resource_profile"]
        if set(raw_profile) != {
            "authority_receipt_sha256",
            "max_distinctions",
            "max_lessons",
            "max_state_bytes",
            "profile_id",
            "schema",
        }:
            raise ValueError("W1 spatial-vocal memory profile changed")
        profile = W1AnonymousSpatialVocalMemoryProfile(
            profile_id=raw_profile.get("profile_id"),
            max_lessons=raw_profile.get("max_lessons"),
            max_distinctions=raw_profile.get("max_distinctions"),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
            relation_authority=relation_authority,
        )
        expected = hmac.new(
            owner._key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""), expected
        ):
            raise ValueError("W1 spatial-vocal memory HMAC changed")
        raw_lessons = {
            raw.get("authority_receipt_sha256"): raw
            for raw in body["lessons"]
            if isinstance(raw, Mapping)
        }
        raw_distinctions = {
            raw.get("authority_receipt_sha256"): raw
            for raw in body["distinctions"]
            if isinstance(raw, Mapping)
        }
        if (
            len(raw_lessons) != len(body["lessons"])
            or len(raw_distinctions) != len(body["distinctions"])
            or len(raw_lessons) != len(retained_lessons)
            or len(raw_distinctions) != len(retained_distinctions)
        ):
            raise ValueError("W1 spatial-vocal retained source set changed")
        for lesson in retained_lessons:
            owner._relations.verify_lesson(lesson)
            raw = raw_lessons.pop(
                lesson.authority_receipt_sha256, None
            )
            owner.admit_lesson(lesson)
            records = {
                item["authority_receipt_sha256"]: item
                for item in owner._body()["lessons"]
            }
            if raw != records[lesson.authority_receipt_sha256]:
                raise ValueError(
                    "W1 spatial-vocal lesson conflicts with retained authority"
                )
        for distinction in retained_distinctions:
            owner._relations.verify_distinction(distinction)
            raw = raw_distinctions.pop(
                distinction.authority_receipt_sha256, None
            )
            owner.admit_distinction(distinction)
            records = {
                item["authority_receipt_sha256"]: item
                for item in owner._body()["distinctions"]
            }
            if raw != records[distinction.authority_receipt_sha256]:
                raise ValueError(
                    "W1 spatial-vocal distinction conflicts with retained authority"
                )
        if (
            raw_lessons
            or raw_distinctions
            or owner.snapshot_encoded() != encoded
        ):
            raise ValueError("W1 spatial-vocal restored state changed")
        return owner


__all__ = [
    "W1AnonymousSpatialVocalMemoryProfile",
    "W1AnonymousSpatialVocalRelationMemoryOwner",
]
