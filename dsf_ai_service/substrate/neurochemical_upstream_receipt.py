"""Ed25519 custody for physical facts entering neurochemical flow.

The neurochemical field is deliberately verifier-only.  A mounted physical
authority owns an Ed25519 private key and signs one complete chemical fact.
The field receives only the corresponding public-key mount.  It cannot mint,
relabel, or widen upstream truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


PHYSICAL_RECEIPT_SCHEMA = "guala.neurochemical.upstream.physical.v1"
TEMPORAL_RECEIPT_SCHEMA = "guala.neurochemical.upstream.temporal.v1"
_PHYSICAL_DOMAIN = b"guala-neurochemical-upstream-physical-v1\0"
_TEMPORAL_DOMAIN = b"guala-neurochemical-upstream-temporal-v1\0"
_HEX = frozenset("0123456789abcdef")
MAX_UPSTREAM_IDENTIFIER_BYTES = 256
MAX_UPSTREAM_PARAMETER_PATH_BYTES = 1024
MAX_UPSTREAM_SEQUENCE_BITS = 128
MAX_UPSTREAM_FRACTION_BITS = 4096
MAX_UPSTREAM_RECEIPT_BYTES = 64 * 1024


class UpstreamAuthorityKind(str, Enum):
    EXCITATION = "excitation"
    BODY = "body"
    ACTION = "action"
    CLOCK = "clock"


class CausalSourceKind(str, Enum):
    EXCITATION = "excitation"
    BODY = "body"
    ACTION = "action"


class TemporalDriverKind(str, Enum):
    PHASIC = "phasic"
    TONIC = "tonic"
    INTRINSIC = "intrinsic"
    ULTRADIAN = "ultradian"
    CIRCADIAN = "circadian"
    SLEEP_COUPLED = "sleep_coupled"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _identifier(
    value: object,
    label: str,
    maximum: int = MAX_UPSTREAM_IDENTIFIER_BYTES,
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > maximum
    ):
        raise ValueError(f"{label} is not a bounded canonical identifier")
    return value


def _fraction(value: object, label: str) -> Fraction:
    if not isinstance(value, Fraction):
        raise TypeError(f"{label} must be an exact Fraction")
    if (
        abs(value.numerator).bit_length() > MAX_UPSTREAM_FRACTION_BITS
        or value.denominator.bit_length() > MAX_UPSTREAM_FRACTION_BITS
    ):
        raise ValueError(f"{label} exceeds exact rational bit capacity")
    return value


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _hex_bytes(value: object, expected_bytes: int, label: str) -> bytes:
    if (
        not isinstance(value, str)
        or len(value) != expected_bytes * 2
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} is not canonical lowercase hex")
    return bytes.fromhex(value)


def _positive_sequence(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value.bit_length() > MAX_UPSTREAM_SEQUENCE_BITS
    ):
        raise ValueError("upstream chemistry sequence must be a positive integer")
    return value


def expected_authority_kind(source_kind: CausalSourceKind) -> UpstreamAuthorityKind:
    if not isinstance(source_kind, CausalSourceKind):
        raise TypeError("causal source kind is not typed")
    return UpstreamAuthorityKind(source_kind.value)


@dataclass(frozen=True, slots=True)
class UpstreamIssuerVerifierMount:
    issuer_id: str
    authority_kind: UpstreamAuthorityKind
    ed25519_public_key_hex: str

    def verify(self) -> None:
        _identifier(self.issuer_id, "upstream issuer id")
        if not isinstance(self.authority_kind, UpstreamAuthorityKind):
            raise TypeError("upstream authority kind is not typed")
        _hex_bytes(
            self.ed25519_public_key_hex,
            32,
            "upstream Ed25519 public key",
        )

    def record(self) -> dict[str, object]:
        return {
            "authority_kind": self.authority_kind.value,
            "ed25519_public_key_hex": self.ed25519_public_key_hex,
            "issuer_id": self.issuer_id,
        }


@dataclass(frozen=True, slots=True)
class PhysicalNeurochemicalReceipt:
    issuer_id: str
    chemistry_sequence: int
    event_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    source_kind: CausalSourceKind
    source_component_id: str
    lane_id: str
    destination_component_id: str
    amount: Fraction
    amount_unit: str
    ed25519_signature_hex: str

    def payload(self) -> dict[str, object]:
        return {
            "amount": _fraction_text(self.amount),
            "amount_unit": self.amount_unit,
            "chemistry_sequence": self.chemistry_sequence,
            "destination_component_id": self.destination_component_id,
            "event_id": self.event_id,
            "issuer_id": self.issuer_id,
            "lane_id": self.lane_id,
            "schema": PHYSICAL_RECEIPT_SCHEMA,
            "source_component_id": self.source_component_id,
            "source_kind": self.source_kind.value,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "ed25519_signature_hex": self.ed25519_signature_hex,
        }


@dataclass(frozen=True, slots=True)
class TemporalNeurochemicalReceipt:
    issuer_id: str
    chemistry_sequence: int
    event_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    driver_kind: TemporalDriverKind
    lane_id: str
    lane_enabled: bool
    physical_parameter_path: str
    ed25519_signature_hex: str

    def payload(self) -> dict[str, object]:
        return {
            "chemistry_sequence": self.chemistry_sequence,
            "driver_kind": self.driver_kind.value,
            "event_id": self.event_id,
            "issuer_id": self.issuer_id,
            "lane_enabled": self.lane_enabled,
            "lane_id": self.lane_id,
            "physical_parameter_path": self.physical_parameter_path,
            "schema": TEMPORAL_RECEIPT_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "ed25519_signature_hex": self.ed25519_signature_hex,
        }


UpstreamNeurochemicalReceipt = (
    PhysicalNeurochemicalReceipt | TemporalNeurochemicalReceipt
)


def _verify_common(
    receipt: UpstreamNeurochemicalReceipt,
    mount: UpstreamIssuerVerifierMount,
) -> None:
    mount.verify()
    _identifier(receipt.issuer_id, "upstream receipt issuer id")
    if receipt.issuer_id != mount.issuer_id:
        raise ValueError("upstream receipt issuer does not match verifier mount")
    _positive_sequence(receipt.chemistry_sequence)
    _identifier(receipt.event_id, "upstream receipt event id")
    _fraction(receipt.source_time_start, "upstream receipt start")
    _fraction(receipt.source_time_end, "upstream receipt end")
    if receipt.source_time_end <= receipt.source_time_start:
        raise ValueError("upstream receipt requires a positive exact interval")


def verify_upstream_receipt(
    receipt: UpstreamNeurochemicalReceipt,
    mount: UpstreamIssuerVerifierMount,
) -> None:
    if isinstance(receipt, PhysicalNeurochemicalReceipt):
        _verify_common(receipt, mount)
        if (
            not isinstance(receipt.source_kind, CausalSourceKind)
            or mount.authority_kind
            is not expected_authority_kind(receipt.source_kind)
        ):
            raise ValueError("physical receipt source kind changed issuer authority")
        _identifier(receipt.source_component_id, "physical receipt source")
        _identifier(receipt.lane_id, "physical receipt lane")
        _identifier(receipt.destination_component_id, "physical receipt destination")
        _fraction(receipt.amount, "physical receipt amount")
        if receipt.amount <= 0:
            raise ValueError("physical receipt amount must be positive")
        _identifier(receipt.amount_unit, "physical receipt amount unit")
        signature = _hex_bytes(
            receipt.ed25519_signature_hex,
            64,
            "physical Ed25519 signature",
        )
        domain = _PHYSICAL_DOMAIN
    elif isinstance(receipt, TemporalNeurochemicalReceipt):
        _verify_common(receipt, mount)
        if mount.authority_kind is not UpstreamAuthorityKind.CLOCK:
            raise ValueError("temporal receipt requires a clock authority")
        if not isinstance(receipt.driver_kind, TemporalDriverKind):
            raise TypeError("temporal driver kind is not typed")
        _identifier(receipt.lane_id, "temporal receipt lane")
        if not isinstance(receipt.lane_enabled, bool):
            raise TypeError("temporal lane state is not boolean")
        _identifier(
            receipt.physical_parameter_path,
            "temporal physical parameter path",
            MAX_UPSTREAM_PARAMETER_PATH_BYTES,
        )
        signature = _hex_bytes(
            receipt.ed25519_signature_hex,
            64,
            "temporal Ed25519 signature",
        )
        domain = _TEMPORAL_DOMAIN
    else:
        raise TypeError("upstream neurochemical receipt is not typed")
    signed_payload = domain + _canonical(receipt.payload())
    if len(_canonical(receipt.record())) > MAX_UPSTREAM_RECEIPT_BYTES:
        raise ValueError("upstream neurochemical receipt exceeds byte capacity")
    try:
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(mount.ed25519_public_key_hex)
        ).verify(signature, signed_payload)
    except InvalidSignature as error:
        raise ValueError("upstream neurochemical Ed25519 signature changed") from error


class NeurochemicalUpstreamIssuerAuthority:
    """Private-key authority owned by one physical subsystem, never by flow."""

    def __init__(
        self,
        *,
        issuer_id: str,
        authority_kind: UpstreamAuthorityKind,
        private_key: Ed25519PrivateKey,
    ) -> None:
        _identifier(issuer_id, "upstream issuer id")
        if not isinstance(authority_kind, UpstreamAuthorityKind):
            raise TypeError("upstream authority kind is not typed")
        if not isinstance(private_key, Ed25519PrivateKey):
            raise TypeError("upstream issuer private key is not Ed25519")
        self._issuer_id = issuer_id
        self._authority_kind = authority_kind
        self._private_key = private_key

    @classmethod
    def from_private_key_bytes(
        cls,
        *,
        issuer_id: str,
        authority_kind: UpstreamAuthorityKind,
        private_key_bytes: bytes,
    ) -> "NeurochemicalUpstreamIssuerAuthority":
        if not isinstance(private_key_bytes, bytes) or len(private_key_bytes) != 32:
            raise ValueError("Ed25519 private key seed must be exactly 32 bytes")
        return cls(
            issuer_id=issuer_id,
            authority_kind=authority_kind,
            private_key=Ed25519PrivateKey.from_private_bytes(private_key_bytes),
        )

    @property
    def verifier_mount(self) -> UpstreamIssuerVerifierMount:
        public_bytes = self._private_key.public_key().public_bytes_raw()
        return UpstreamIssuerVerifierMount(
            issuer_id=self._issuer_id,
            authority_kind=self._authority_kind,
            ed25519_public_key_hex=public_bytes.hex(),
        )

    def sign_physical(
        self,
        *,
        chemistry_sequence: int,
        event_id: str,
        source_time_start: Fraction,
        source_time_end: Fraction,
        source_component_id: str,
        lane_id: str,
        destination_component_id: str,
        amount: Fraction,
        amount_unit: str,
    ) -> PhysicalNeurochemicalReceipt:
        if self._authority_kind is UpstreamAuthorityKind.CLOCK:
            raise ValueError("clock authority cannot sign physical chemical release")
        source_kind = CausalSourceKind(self._authority_kind.value)
        provisional = PhysicalNeurochemicalReceipt(
            issuer_id=self._issuer_id,
            chemistry_sequence=chemistry_sequence,
            event_id=event_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            source_kind=source_kind,
            source_component_id=source_component_id,
            lane_id=lane_id,
            destination_component_id=destination_component_id,
            amount=amount,
            amount_unit=amount_unit,
            ed25519_signature_hex="0" * 128,
        )
        _verify_common(provisional, self.verifier_mount)
        _identifier(source_component_id, "physical receipt source")
        _identifier(lane_id, "physical receipt lane")
        _identifier(destination_component_id, "physical receipt destination")
        _fraction(amount, "physical receipt amount")
        if amount <= 0:
            raise ValueError("physical receipt amount must be positive")
        _identifier(amount_unit, "physical receipt amount unit")
        signed_payload = _PHYSICAL_DOMAIN + _canonical(provisional.payload())
        if len(signed_payload) + 128 > MAX_UPSTREAM_RECEIPT_BYTES:
            raise ValueError("upstream neurochemical receipt exceeds byte capacity")
        signature = self._private_key.sign(signed_payload)
        result = PhysicalNeurochemicalReceipt(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name != "ed25519_signature_hex"
            },
            ed25519_signature_hex=signature.hex(),
        )
        verify_upstream_receipt(result, self.verifier_mount)
        return result

    def sign_temporal(
        self,
        *,
        chemistry_sequence: int,
        event_id: str,
        source_time_start: Fraction,
        source_time_end: Fraction,
        driver_kind: TemporalDriverKind,
        lane_id: str,
        lane_enabled: bool,
        physical_parameter_path: str,
    ) -> TemporalNeurochemicalReceipt:
        if self._authority_kind is not UpstreamAuthorityKind.CLOCK:
            raise ValueError("only a clock authority can sign temporal chemistry")
        provisional = TemporalNeurochemicalReceipt(
            issuer_id=self._issuer_id,
            chemistry_sequence=chemistry_sequence,
            event_id=event_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            driver_kind=driver_kind,
            lane_id=lane_id,
            lane_enabled=lane_enabled,
            physical_parameter_path=physical_parameter_path,
            ed25519_signature_hex="0" * 128,
        )
        _verify_common(provisional, self.verifier_mount)
        if not isinstance(driver_kind, TemporalDriverKind):
            raise TypeError("temporal driver kind is not typed")
        _identifier(lane_id, "temporal receipt lane")
        if not isinstance(lane_enabled, bool):
            raise TypeError("temporal lane state is not boolean")
        _identifier(
            physical_parameter_path,
            "temporal physical parameter path",
            MAX_UPSTREAM_PARAMETER_PATH_BYTES,
        )
        signed_payload = _TEMPORAL_DOMAIN + _canonical(provisional.payload())
        if len(signed_payload) + 128 > MAX_UPSTREAM_RECEIPT_BYTES:
            raise ValueError("upstream neurochemical receipt exceeds byte capacity")
        signature = self._private_key.sign(signed_payload)
        result = TemporalNeurochemicalReceipt(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name != "ed25519_signature_hex"
            },
            ed25519_signature_hex=signature.hex(),
        )
        verify_upstream_receipt(result, self.verifier_mount)
        return result


__all__ = (
    "CausalSourceKind",
    "MAX_UPSTREAM_SEQUENCE_BITS",
    "NeurochemicalUpstreamIssuerAuthority",
    "PhysicalNeurochemicalReceipt",
    "TemporalDriverKind",
    "TemporalNeurochemicalReceipt",
    "UpstreamAuthorityKind",
    "UpstreamIssuerVerifierMount",
    "UpstreamNeurochemicalReceipt",
    "expected_authority_kind",
    "verify_upstream_receipt",
)
