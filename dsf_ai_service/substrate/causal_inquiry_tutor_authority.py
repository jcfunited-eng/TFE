"""External authorization for one exact causal-inquiry articulation.

The issuer belongs at an authenticated gateway.  Cognition receives only a
verifier and a receipt binding one inquiry need, one authenticated W1 world
observation, one already-owned articulatory program, and one opaque nonce.
No tutor name, label, text, word, meaning, chi, or recognition enters this
boundary.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Mapping


TUTOR_AUTHORIZATION_SCHEMA = (
    "guala.causal_inquiry.external_tutor_authorization.v1"
)
TUTOR_CONSEQUENCE_AUTHORIZATION_SCHEMA = (
    "guala.causal_inquiry.external_tutor_consequence_authorization.v1"
)
_AUTHORIZATION_DOMAIN = (
    b"guala-causal-inquiry-external-tutor-authorization-v1\0"
)
_AUTHORIZATION_ID_SCHEMA = (
    "guala.causal_inquiry.external_tutor_authorization_identity.v1"
)
_CONSEQUENCE_AUTHORIZATION_DOMAIN = (
    b"guala-causal-inquiry-tutor-consequence-authorization-v1\0"
)
_CONSEQUENCE_AUTHORIZATION_ID_SCHEMA = (
    "guala.causal_inquiry.tutor_consequence_authorization_identity.v1"
)
_MIN_KEY_BYTES = 32
_MAX_KEY_BYTES = 4_096
_NONCE_BYTES = 32
_HEX = frozenset("0123456789abcdef")
_VERIFIER_CONSTRUCTION_AUTHORITY = object()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("inquiry tutor authority key changed type")
    if not _MIN_KEY_BYTES <= len(result) <= _MAX_KEY_BYTES:
        raise ValueError("inquiry tutor authority key changed extent")
    return hashlib.sha256(_AUTHORIZATION_DOMAIN + result).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"inquiry tutor {label} changed")
    return value


def _nonce_sha256(value: object) -> str:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError("inquiry tutor nonce is not opaque bytes")
    nonce = bytes(value)
    if len(nonce) != _NONCE_BYTES:
        raise ValueError("inquiry tutor nonce must be exactly 32 bytes")
    return hashlib.sha256(nonce).hexdigest()


@dataclass(frozen=True, slots=True)
class CausalInquiryTutorAuthorizationReceipt:
    authorization_id: str
    need_receipt_sha256: str
    world_observation_receipt_sha256: str
    program_id: str
    nonce_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "authorization_id": self.authorization_id,
            "need_receipt_sha256": self.need_receipt_sha256,
            "nonce_sha256": self.nonce_sha256,
            "program_id": self.program_id,
            "schema": TUTOR_AUTHORIZATION_SCHEMA,
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }

    @classmethod
    def from_record(
        cls,
        value: object,
    ) -> "CausalInquiryTutorAuthorizationReceipt":
        expected = {
            "authorization_id",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "need_receipt_sha256",
            "nonce_sha256",
            "program_id",
            "schema",
            "world_observation_receipt_sha256",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != TUTOR_AUTHORIZATION_SCHEMA
        ):
            raise ValueError(
                "inquiry tutor authorization record changed"
            )
        result = cls(
            authorization_id=value["authorization_id"],
            need_receipt_sha256=value["need_receipt_sha256"],
            world_observation_receipt_sha256=(
                value["world_observation_receipt_sha256"]
            ),
            program_id=value["program_id"],
            nonce_sha256=value["nonce_sha256"],
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=(
                value["authority_receipt_sha256"]
            ),
        )
        for digest, label in (
            (result.authorization_id, "authorization identity"),
            (result.need_receipt_sha256, "need"),
            (
                result.world_observation_receipt_sha256,
                "world observation",
            ),
            (result.program_id, "program"),
            (result.nonce_sha256, "nonce"),
            (result.authority_hmac_sha256, "HMAC"),
            (result.authority_receipt_sha256, "authority receipt"),
        ):
            _sha(digest, label)
        if result.record() != dict(value):
            raise ValueError(
                "inquiry tutor authorization record is noncanonical"
            )
        return result


@dataclass(frozen=True, slots=True)
class CausalInquiryTutorConsequenceAuthorizationReceipt:
    authorization_id: str
    need_receipt_sha256: str
    witness_receipt_sha256: str
    candidate_receipt_sha256: str
    candidate_world_after_receipt_sha256: str
    companion_pcm_sha256: str
    nonce_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "authorization_id": self.authorization_id,
            "candidate_receipt_sha256": (
                self.candidate_receipt_sha256
            ),
            "candidate_world_after_receipt_sha256": (
                self.candidate_world_after_receipt_sha256
            ),
            "companion_pcm_sha256": self.companion_pcm_sha256,
            "need_receipt_sha256": self.need_receipt_sha256,
            "nonce_sha256": self.nonce_sha256,
            "schema": TUTOR_CONSEQUENCE_AUTHORIZATION_SCHEMA,
            "witness_receipt_sha256": self.witness_receipt_sha256,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    @classmethod
    def from_record(
        cls,
        value: object,
    ) -> "CausalInquiryTutorConsequenceAuthorizationReceipt":
        expected = {
            *cls.__dataclass_fields__,
            "schema",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema")
            != TUTOR_CONSEQUENCE_AUTHORIZATION_SCHEMA
        ):
            raise ValueError(
                "inquiry tutor consequence authorization changed"
            )
        result = cls(
            authorization_id=value["authorization_id"],
            need_receipt_sha256=value["need_receipt_sha256"],
            witness_receipt_sha256=value[
                "witness_receipt_sha256"
            ],
            candidate_receipt_sha256=value[
                "candidate_receipt_sha256"
            ],
            candidate_world_after_receipt_sha256=value[
                "candidate_world_after_receipt_sha256"
            ],
            companion_pcm_sha256=value["companion_pcm_sha256"],
            nonce_sha256=value["nonce_sha256"],
            authority_hmac_sha256=value[
                "authority_hmac_sha256"
            ],
            authority_receipt_sha256=value[
                "authority_receipt_sha256"
            ],
        )
        for digest, label in (
            (result.authorization_id, "consequence authorization"),
            (result.need_receipt_sha256, "consequence need"),
            (result.witness_receipt_sha256, "consequence witness"),
            (result.candidate_receipt_sha256, "consequence candidate"),
            (
                result.candidate_world_after_receipt_sha256,
                "consequence world after",
            ),
            (result.companion_pcm_sha256, "consequence PCM"),
            (result.nonce_sha256, "consequence nonce"),
            (result.authority_hmac_sha256, "consequence HMAC"),
            (
                result.authority_receipt_sha256,
                "consequence authority receipt",
            ),
        ):
            _sha(digest, label)
        if result.record() != dict(value):
            raise ValueError(
                "inquiry tutor consequence authorization is noncanonical"
            )
        return result


class CausalInquiryTutorAuthorizationVerifier:
    """Verify receipts without exposing an issuance method."""

    def __init__(
        self,
        verification_key: bytes,
        *,
        _construction_authority: object,
    ) -> None:
        if (
            _construction_authority
            is not _VERIFIER_CONSTRUCTION_AUTHORITY
            or not isinstance(verification_key, bytes)
            or len(verification_key) != 32
        ):
            raise ValueError(
                "inquiry tutor verifier lacks issuer authority"
            )
        self.__verification_key = verification_key

    def verify(
        self,
        value: CausalInquiryTutorAuthorizationReceipt,
    ) -> None:
        if not isinstance(
            value,
            CausalInquiryTutorAuthorizationReceipt,
        ):
            raise TypeError(
                "inquiry tutor authorization is not typed"
            )
        mounted = (
            CausalInquiryTutorAuthorizationReceipt.from_record(
                value.record()
            )
        )
        expected_id = _digest({
            "need_receipt_sha256": mounted.need_receipt_sha256,
            "nonce_sha256": mounted.nonce_sha256,
            "program_id": mounted.program_id,
            "schema": _AUTHORIZATION_ID_SCHEMA,
            "world_observation_receipt_sha256": (
                mounted.world_observation_receipt_sha256
            ),
        })
        expected_hmac = hmac.new(
            self.__verification_key,
            _AUTHORIZATION_DOMAIN + _canonical(mounted.payload()),
            hashlib.sha256,
        ).hexdigest()
        expected_receipt = _digest({
            "authority_hmac_sha256": expected_hmac,
            "payload": mounted.payload(),
        })
        if (
            mounted.authorization_id != expected_id
            or not hmac.compare_digest(
                mounted.authority_hmac_sha256,
                expected_hmac,
            )
            or mounted.authority_receipt_sha256 != expected_receipt
        ):
            raise ValueError(
                "inquiry tutor authorization authority changed"
            )

    def verify_consequence(
        self,
        value: CausalInquiryTutorConsequenceAuthorizationReceipt,
    ) -> None:
        if not isinstance(
            value,
            CausalInquiryTutorConsequenceAuthorizationReceipt,
        ):
            raise TypeError(
                "inquiry tutor consequence authorization is not typed"
            )
        mounted = (
            CausalInquiryTutorConsequenceAuthorizationReceipt
            .from_record(value.record())
        )
        expected_id = _digest({
            "candidate_receipt_sha256": (
                mounted.candidate_receipt_sha256
            ),
            "candidate_world_after_receipt_sha256": (
                mounted.candidate_world_after_receipt_sha256
            ),
            "companion_pcm_sha256": mounted.companion_pcm_sha256,
            "need_receipt_sha256": mounted.need_receipt_sha256,
            "nonce_sha256": mounted.nonce_sha256,
            "schema": _CONSEQUENCE_AUTHORIZATION_ID_SCHEMA,
            "witness_receipt_sha256": (
                mounted.witness_receipt_sha256
            ),
        })
        expected_hmac = hmac.new(
            self.__verification_key,
            _CONSEQUENCE_AUTHORIZATION_DOMAIN
            + _canonical(mounted.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            mounted.authorization_id != expected_id
            or not hmac.compare_digest(
                mounted.authority_hmac_sha256,
                expected_hmac,
            )
            or mounted.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": mounted.payload(),
            })
        ):
            raise ValueError(
                "inquiry tutor consequence authorization authority changed"
            )


class CausalInquiryTutorAuthorizationAuthority:
    """Issue exact receipts and provide a verification-only capability."""

    def __init__(self, *, authority_key: bytes | str) -> None:
        self.__authority_key = _key(authority_key)

    def verifier(self) -> CausalInquiryTutorAuthorizationVerifier:
        return CausalInquiryTutorAuthorizationVerifier(
            self.__authority_key,
            _construction_authority=(
                _VERIFIER_CONSTRUCTION_AUTHORITY
            ),
        )

    def issue(
        self,
        *,
        need_receipt_sha256: str,
        world_observation_receipt_sha256: str,
        program_id: str,
        nonce: bytes,
    ) -> CausalInquiryTutorAuthorizationReceipt:
        need = _sha(need_receipt_sha256, "need")
        observation = _sha(
            world_observation_receipt_sha256,
            "world observation",
        )
        program = _sha(program_id, "program")
        nonce_digest = _nonce_sha256(nonce)
        authorization_id = _digest({
            "need_receipt_sha256": need,
            "nonce_sha256": nonce_digest,
            "program_id": program,
            "schema": _AUTHORIZATION_ID_SCHEMA,
            "world_observation_receipt_sha256": observation,
        })
        provisional = CausalInquiryTutorAuthorizationReceipt(
            authorization_id=authorization_id,
            need_receipt_sha256=need,
            world_observation_receipt_sha256=observation,
            program_id=program,
            nonce_sha256=nonce_digest,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self.__authority_key,
            _AUTHORIZATION_DOMAIN + _canonical(
                provisional.payload()
            ),
            hashlib.sha256,
        ).hexdigest()
        result = CausalInquiryTutorAuthorizationReceipt(
            authorization_id=provisional.authorization_id,
            need_receipt_sha256=provisional.need_receipt_sha256,
            world_observation_receipt_sha256=(
                provisional.world_observation_receipt_sha256
            ),
            program_id=provisional.program_id,
            nonce_sha256=provisional.nonce_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verifier().verify(result)
        return result

    def issue_consequence(
        self,
        *,
        need_receipt_sha256: str,
        witness_receipt_sha256: str,
        candidate_receipt_sha256: str,
        candidate_world_after_receipt_sha256: str,
        companion_pcm_sha256: str,
        nonce: bytes,
    ) -> CausalInquiryTutorConsequenceAuthorizationReceipt:
        need = _sha(need_receipt_sha256, "consequence need")
        witness = _sha(
            witness_receipt_sha256,
            "consequence witness",
        )
        candidate = _sha(
            candidate_receipt_sha256,
            "consequence candidate",
        )
        world_after = _sha(
            candidate_world_after_receipt_sha256,
            "consequence world after",
        )
        pcm = _sha(companion_pcm_sha256, "consequence PCM")
        nonce_digest = _nonce_sha256(nonce)
        identity_payload = {
            "candidate_receipt_sha256": candidate,
            "candidate_world_after_receipt_sha256": world_after,
            "companion_pcm_sha256": pcm,
            "need_receipt_sha256": need,
            "nonce_sha256": nonce_digest,
            "schema": _CONSEQUENCE_AUTHORIZATION_ID_SCHEMA,
            "witness_receipt_sha256": witness,
        }
        provisional = (
            CausalInquiryTutorConsequenceAuthorizationReceipt(
                authorization_id=_digest(identity_payload),
                need_receipt_sha256=need,
                witness_receipt_sha256=witness,
                candidate_receipt_sha256=candidate,
                candidate_world_after_receipt_sha256=world_after,
                companion_pcm_sha256=pcm,
                nonce_sha256=nonce_digest,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
        )
        signature = hmac.new(
            self.__authority_key,
            _CONSEQUENCE_AUTHORIZATION_DOMAIN
            + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = CausalInquiryTutorConsequenceAuthorizationReceipt(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name not in {
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verifier().verify_consequence(result)
        return result


__all__ = (
    "CausalInquiryTutorAuthorizationAuthority",
    "CausalInquiryTutorAuthorizationReceipt",
    "CausalInquiryTutorConsequenceAuthorizationReceipt",
    "CausalInquiryTutorAuthorizationVerifier",
    "TUTOR_AUTHORIZATION_SCHEMA",
    "TUTOR_CONSEQUENCE_AUTHORIZATION_SCHEMA",
)
