"""Authenticated authority receipts for auditory tutoring.

This module is a security boundary outside cognition.  It does not interpret
sound, evaluate DSF fields, establish source identity, or decide meaning.  It
only proves that an already-authenticated gateway authorized one exact tutor
binding.  The proof is domain-separated HMAC-SHA256 over the exact auditory
experience id, reciprocity kind, canonical tutor label, nonce, and wall-clock
issuance time.

Receipts remain verifiable after persistence.  Their signed time is audit
evidence, not a heuristic expiry rule.  Replay is prevented by the owner that
persists and rejects previously admitted nonces.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Mapping


AUDITORY_TUTOR_AUTHORITY_SCHEMA = "guala.auditory.tutor_authority.v1"
AUDITORY_TUTOR_ADMISSION_SCHEMA = "guala.auditory.tutor_admission.v1"
AUDITORY_TUTOR_AUTHORITY_KEY_DOMAIN = b"guala-auditory-tutor-authority-v1\0"
AUDITORY_TUTOR_ADMISSION_KEY_DOMAIN = b"guala-auditory-tutor-admission-v1\0"
AUDITORY_TUTOR_AUTHORITY_SIGNATURE_FIELD = "authority_hmac_sha256"
_RECEIPT_FIELDS = frozenset({
    "authority_hmac_sha256",
    "experience_id",
    "issued_at_unix_ns",
    "kind",
    "nonce",
    "schema",
    "tutor_label",
})
_ADMISSION_FIELDS = frozenset({
    "admission_hmac_sha256",
    "event_boundary",
    "experience_id",
    "gateway_authority_hmac_sha256",
    "kind",
    "l5_authority_payload_base64",
    "l5_authority_receipt_sha256",
    "schema",
    "tutor_label",
})
_AUDITORY_TUTOR_KINDS = frozenset({"source_continuity", "spoken_form"})


def canonical_tutor_label(value: object) -> str:
    """Return the one label representation admitted to a tutor receipt."""
    if not isinstance(value, str):
        raise ValueError("auditory tutor label must be text")
    canonical = " ".join(value.split())
    if not canonical:
        raise ValueError("auditory tutor label cannot be empty")
    if len(canonical) > 512:
        raise ValueError("auditory tutor label exceeds the bounded interface")
    return canonical


def _sha256_hex(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} must be a SHA-256 hex digest")
    try:
        decoded = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a SHA-256 hex digest") from exc
    if len(decoded) != 32 or value != decoded.hex():
        raise ValueError(f"{name} must use canonical lowercase hex")
    return value


def _kind(value: object) -> str:
    raw = value.value if hasattr(value, "value") else value
    if not isinstance(raw, str) or raw not in _AUDITORY_TUTOR_KINDS:
        raise ValueError("auditory tutor authority kind is invalid")
    return raw


def _nonce(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError("auditory tutor authority nonce must be 32-byte hex")
    try:
        decoded = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(
            "auditory tutor authority nonce must be 32-byte hex"
        ) from exc
    if len(decoded) != 32 or value != decoded.hex():
        raise ValueError(
            "auditory tutor authority nonce must use canonical lowercase hex"
        )
    return value


def _canonical_base64(value: object, name: str) -> tuple[str, bytes]:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be nonempty canonical base64")
    try:
        decoded = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError(f"{name} must be nonempty canonical base64") from exc
    if not decoded or base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{name} must be nonempty canonical base64")
    return value, decoded


def _issued_at(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("auditory tutor authority time must be positive unix ns")
    return value


def _secret_bytes(value: object) -> bytes:
    if isinstance(value, str):
        encoded = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        encoded = bytes(value)
    else:
        raise ValueError("auditory tutor authority key must be bytes or text")
    if not encoded:
        raise ValueError("auditory tutor authority key cannot be empty")
    return encoded


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _unsigned_payload(
    *,
    experience_id: str,
    kind: str,
    tutor_label: str,
    nonce: str,
    issued_at_unix_ns: int,
) -> dict[str, object]:
    return {
        "experience_id": experience_id,
        "issued_at_unix_ns": issued_at_unix_ns,
        "kind": kind,
        "nonce": nonce,
        "schema": AUDITORY_TUTOR_AUTHORITY_SCHEMA,
        "tutor_label": tutor_label,
    }


@dataclass(frozen=True, slots=True)
class AuditoryTutorAuthorityReceipt:
    experience_id: str
    kind: str
    tutor_label: str
    nonce: str
    issued_at_unix_ns: int
    authority_hmac_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            **_unsigned_payload(
                experience_id=self.experience_id,
                kind=self.kind,
                tutor_label=self.tutor_label,
                nonce=self.nonce,
                issued_at_unix_ns=self.issued_at_unix_ns,
            ),
            AUDITORY_TUTOR_AUTHORITY_SIGNATURE_FIELD: (
                self.authority_hmac_sha256
            ),
        }

    @classmethod
    def from_payload(
        cls, value: object
    ) -> "AuditoryTutorAuthorityReceipt":
        if not isinstance(value, Mapping) or set(value) != _RECEIPT_FIELDS:
            raise ValueError("auditory tutor authority receipt is malformed")
        if value.get("schema") != AUDITORY_TUTOR_AUTHORITY_SCHEMA:
            raise ValueError("auditory tutor authority receipt schema is invalid")
        return cls(
            experience_id=_sha256_hex(
                value.get("experience_id"), "auditory tutor experience id"
            ),
            kind=_kind(value.get("kind")),
            tutor_label=canonical_tutor_label(value.get("tutor_label")),
            nonce=_nonce(value.get("nonce")),
            issued_at_unix_ns=_issued_at(value.get("issued_at_unix_ns")),
            authority_hmac_sha256=_sha256_hex(
                value.get(AUDITORY_TUTOR_AUTHORITY_SIGNATURE_FIELD),
                "auditory tutor authority HMAC",
            ),
        )


@dataclass(frozen=True, slots=True)
class AuditoryTutorAdmissionReceipt:
    experience_id: str
    kind: str
    tutor_label: str
    event_boundary: str
    gateway_authority_hmac_sha256: str
    l5_authority_receipt_sha256: str
    l5_authority_payload: bytes
    admission_hmac_sha256: str

    def _unsigned(self) -> dict[str, object]:
        return {
            "event_boundary": self.event_boundary,
            "experience_id": self.experience_id,
            "gateway_authority_hmac_sha256": (
                self.gateway_authority_hmac_sha256
            ),
            "kind": self.kind,
            "l5_authority_payload_base64": base64.b64encode(
                self.l5_authority_payload
            ).decode("ascii"),
            "l5_authority_receipt_sha256": (
                self.l5_authority_receipt_sha256
            ),
            "schema": AUDITORY_TUTOR_ADMISSION_SCHEMA,
            "tutor_label": self.tutor_label,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            **self._unsigned(),
            "admission_hmac_sha256": self.admission_hmac_sha256,
        }

    @classmethod
    def from_payload(
        cls, value: object
    ) -> "AuditoryTutorAdmissionReceipt":
        if not isinstance(value, Mapping) or set(value) != _ADMISSION_FIELDS:
            raise ValueError("auditory tutor admission receipt is malformed")
        if value.get("schema") != AUDITORY_TUTOR_ADMISSION_SCHEMA:
            raise ValueError("auditory tutor admission receipt schema is invalid")
        event_boundary = value.get("event_boundary")
        if event_boundary != "utterance":
            raise ValueError(
                "auditory tutor admission is not an utterance boundary"
            )
        _, l5_payload = _canonical_base64(
            value.get("l5_authority_payload_base64"),
            "auditory L5 authority payload",
        )
        return cls(
            experience_id=_sha256_hex(
                value.get("experience_id"), "auditory tutor experience id"
            ),
            kind=_kind(value.get("kind")),
            tutor_label=canonical_tutor_label(value.get("tutor_label")),
            event_boundary=event_boundary,
            gateway_authority_hmac_sha256=_sha256_hex(
                value.get("gateway_authority_hmac_sha256"),
                "gateway auditory tutor HMAC",
            ),
            l5_authority_receipt_sha256=_sha256_hex(
                value.get("l5_authority_receipt_sha256"),
                "auditory L5 authority receipt",
            ),
            l5_authority_payload=l5_payload,
            admission_hmac_sha256=_sha256_hex(
                value.get("admission_hmac_sha256"),
                "auditory tutor admission HMAC",
            ),
        )


class AuditoryTutorAuthority:
    """Issue and verify domain-separated auditory tutor authority receipts."""

    def __init__(self, *, api_key: object | None, required: bool) -> None:
        if not isinstance(required, bool):
            raise TypeError("auditory tutor authority requirement must be boolean")
        if required and api_key is None:
            raise RuntimeError(
                "required auditory tutor authority has no GUALALOOM_API_KEY"
            )
        self._required = required
        secret = _secret_bytes(api_key) if api_key is not None else None
        self._hmac_key = (
            hashlib.sha256(
                AUDITORY_TUTOR_AUTHORITY_KEY_DOMAIN + secret
            ).digest()
            if secret is not None
            else None
        )
        self._admission_hmac_key = (
            hashlib.sha256(
                AUDITORY_TUTOR_ADMISSION_KEY_DOMAIN + secret
            ).digest()
            if secret is not None
            else None
        )

    @classmethod
    def from_environment(
        cls, *, required: bool | None = None
    ) -> "AuditoryTutorAuthority":
        api_key = os.environ.get("GUALALOOM_API_KEY") or None
        actual_required = bool(api_key) if required is None else required
        return cls(api_key=api_key, required=actual_required)

    @classmethod
    def unrequired(cls) -> "AuditoryTutorAuthority":
        """Explicit non-production authority used by isolated development tests."""
        return cls(api_key=None, required=False)

    @property
    def required(self) -> bool:
        return self._required

    @property
    def can_verify(self) -> bool:
        return self._hmac_key is not None

    def issue(
        self,
        *,
        experience_id: str,
        kind: object,
        tutor_label: object,
        nonce: str | None = None,
        issued_at_unix_ns: int | None = None,
    ) -> AuditoryTutorAuthorityReceipt:
        if self._hmac_key is None:
            raise RuntimeError("auditory tutor authority has no signing key")
        payload = _unsigned_payload(
            experience_id=_sha256_hex(
                experience_id, "auditory tutor experience id"
            ),
            kind=_kind(kind),
            tutor_label=canonical_tutor_label(tutor_label),
            nonce=_nonce(nonce if nonce is not None else secrets.token_hex(32)),
            issued_at_unix_ns=_issued_at(
                issued_at_unix_ns
                if issued_at_unix_ns is not None
                else time.time_ns()
            ),
        )
        signature = hmac.new(
            self._hmac_key, _canonical_bytes(payload), hashlib.sha256
        ).hexdigest()
        return AuditoryTutorAuthorityReceipt.from_payload({
            **payload,
            AUDITORY_TUTOR_AUTHORITY_SIGNATURE_FIELD: signature,
        })

    def seal_admission(
        self,
        gateway_receipt: object,
        *,
        experience_id: str,
        kind: object,
        tutor_label: object,
        event_boundary: object,
        l5_authority_receipt_sha256: str,
        l5_authority_payload: bytes,
    ) -> AuditoryTutorAdmissionReceipt:
        if self._admission_hmac_key is None:
            raise RuntimeError("auditory tutor authority has no admission key")
        gateway = self.verify(
            gateway_receipt,
            experience_id=experience_id,
            kind=kind,
            tutor_label=tutor_label,
        )
        if event_boundary != "utterance":
            raise ValueError(
                "auditory tutoring requires verified utterance boundary"
            )
        if (
            not isinstance(l5_authority_payload, bytes)
            or not l5_authority_payload
        ):
            raise ValueError("auditory L5 authority payload is absent")
        l5_digest = _sha256_hex(
            l5_authority_receipt_sha256,
            "auditory L5 authority receipt",
        )
        if hashlib.sha256(l5_authority_payload).hexdigest() != l5_digest:
            raise ValueError("auditory L5 authority payload digest changed")
        unsigned = AuditoryTutorAdmissionReceipt(
            experience_id=gateway.experience_id,
            kind=gateway.kind,
            tutor_label=gateway.tutor_label,
            event_boundary="utterance",
            gateway_authority_hmac_sha256=(
                gateway.authority_hmac_sha256
            ),
            l5_authority_receipt_sha256=l5_digest,
            l5_authority_payload=l5_authority_payload,
            admission_hmac_sha256="0" * 64,
        )._unsigned()
        signature = hmac.new(
            self._admission_hmac_key,
            _canonical_bytes(unsigned),
            hashlib.sha256,
        ).hexdigest()
        return AuditoryTutorAdmissionReceipt.from_payload({
            **unsigned,
            "admission_hmac_sha256": signature,
        })

    def verify_admission(
        self,
        admission_receipt: object,
        gateway_receipt: object,
        *,
        experience_id: str,
        kind: object,
        tutor_label: object,
    ) -> AuditoryTutorAdmissionReceipt:
        if self._admission_hmac_key is None:
            raise RuntimeError("auditory tutor authority has no admission key")
        gateway = self.verify(
            gateway_receipt,
            experience_id=experience_id,
            kind=kind,
            tutor_label=tutor_label,
        )
        admission = (
            admission_receipt
            if isinstance(admission_receipt, AuditoryTutorAdmissionReceipt)
            else AuditoryTutorAdmissionReceipt.from_payload(admission_receipt)
        )
        if (
            admission.experience_id != gateway.experience_id
            or admission.kind != gateway.kind
            or admission.tutor_label != gateway.tutor_label
            or admission.gateway_authority_hmac_sha256
            != gateway.authority_hmac_sha256
        ):
            raise ValueError(
                "auditory tutor admission changed gateway authorization"
            )
        if (
            hashlib.sha256(admission.l5_authority_payload).hexdigest()
            != admission.l5_authority_receipt_sha256
        ):
            raise ValueError("auditory L5 authority payload digest changed")
        expected = hmac.new(
            self._admission_hmac_key,
            _canonical_bytes(admission._unsigned()),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(admission.admission_hmac_sha256, expected):
            raise ValueError("auditory tutor admission HMAC is invalid")
        return admission

    def verify(
        self,
        receipt: object,
        *,
        experience_id: str,
        kind: object,
        tutor_label: object,
    ) -> AuditoryTutorAuthorityReceipt:
        if self._hmac_key is None:
            raise RuntimeError("auditory tutor authority has no verification key")
        mounted = (
            receipt
            if isinstance(receipt, AuditoryTutorAuthorityReceipt)
            else AuditoryTutorAuthorityReceipt.from_payload(receipt)
        )
        expected_experience = _sha256_hex(
            experience_id, "auditory tutor experience id"
        )
        expected_kind = _kind(kind)
        expected_label = canonical_tutor_label(tutor_label)
        if mounted.experience_id != expected_experience:
            raise ValueError("auditory tutor authority experience changed")
        if mounted.kind != expected_kind:
            raise ValueError("auditory tutor authority kind changed")
        if mounted.tutor_label != expected_label:
            raise ValueError("auditory tutor authority label changed")
        unsigned = _unsigned_payload(
            experience_id=mounted.experience_id,
            kind=mounted.kind,
            tutor_label=mounted.tutor_label,
            nonce=mounted.nonce,
            issued_at_unix_ns=mounted.issued_at_unix_ns,
        )
        expected_hmac = hmac.new(
            self._hmac_key, _canonical_bytes(unsigned), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(
            mounted.authority_hmac_sha256, expected_hmac
        ):
            raise ValueError("auditory tutor authority HMAC is invalid")
        return mounted


__all__ = (
    "AUDITORY_TUTOR_ADMISSION_SCHEMA",
    "AUDITORY_TUTOR_AUTHORITY_SCHEMA",
    "AuditoryTutorAdmissionReceipt",
    "AuditoryTutorAuthority",
    "AuditoryTutorAuthorityReceipt",
    "canonical_tutor_label",
)
