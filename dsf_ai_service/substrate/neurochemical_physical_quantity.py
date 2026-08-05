"""Independent Ed25519 authority for mounted neurochemical quantities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


PHYSICAL_QUANTITY_SCHEMA = "guala.neurochemical.physical_quantity.v1"
_QUANTITY_DOMAIN = b"guala-neurochemical-physical-quantity-v1\0"
_HEX = frozenset("0123456789abcdef")
MAX_QUANTITY_IDENTIFIER_BYTES = 256
MAX_QUANTITY_ROLE_BYTES = 1024
MAX_QUANTITY_PROVENANCE_BYTES = 1024
MAX_QUANTITY_FRACTION_BITS = 4096
MAX_PHYSICAL_QUANTITY_RECEIPT_BYTES = 64 * 1024


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
    maximum_bytes: int = MAX_QUANTITY_IDENTIFIER_BYTES,
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > maximum_bytes
    ):
        raise ValueError(f"{label} is not a bounded canonical identifier")
    return value


def _exact_fraction(value: object, label: str) -> Fraction:
    if not isinstance(value, Fraction):
        raise TypeError(f"{label} must be an exact Fraction")
    if (
        abs(value.numerator).bit_length() > MAX_QUANTITY_FRACTION_BITS
        or value.denominator.bit_length() > MAX_QUANTITY_FRACTION_BITS
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


@dataclass(frozen=True, slots=True)
class PhysicalQuantityVerifierMount:
    issuer_id: str
    ed25519_public_key_hex: str

    def verify(self) -> None:
        _identifier(self.issuer_id, "physical quantity issuer id")
        _hex_bytes(
            self.ed25519_public_key_hex,
            32,
            "physical quantity Ed25519 public key",
        )

    def record(self) -> dict[str, object]:
        return {
            "ed25519_public_key_hex": self.ed25519_public_key_hex,
            "issuer_id": self.issuer_id,
        }


@dataclass(frozen=True, slots=True)
class SignedPhysicalQuantity:
    issuer_id: str
    quantity_id: str
    quantity_role: str
    value: Fraction
    unit: str
    provenance_id: str
    ed25519_signature_hex: str

    def payload(self) -> dict[str, object]:
        return {
            "issuer_id": self.issuer_id,
            "provenance_id": self.provenance_id,
            "quantity_id": self.quantity_id,
            "quantity_role": self.quantity_role,
            "schema": PHYSICAL_QUANTITY_SCHEMA,
            "unit": self.unit,
            "value": _fraction_text(self.value),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "ed25519_signature_hex": self.ed25519_signature_hex,
        }


def verify_signed_physical_quantity(
    receipt: SignedPhysicalQuantity,
    mount: PhysicalQuantityVerifierMount,
) -> None:
    if not isinstance(receipt, SignedPhysicalQuantity):
        raise TypeError("physical quantity receipt is not typed")
    mount.verify()
    _identifier(receipt.issuer_id, "physical quantity issuer id")
    if receipt.issuer_id != mount.issuer_id:
        raise ValueError("physical quantity issuer does not match verifier")
    _identifier(receipt.quantity_id, "physical quantity id")
    _identifier(
        receipt.quantity_role,
        "physical quantity role",
        MAX_QUANTITY_ROLE_BYTES,
    )
    _exact_fraction(receipt.value, "physical quantity value")
    _identifier(receipt.unit, "physical quantity unit")
    _identifier(
        receipt.provenance_id,
        "physical quantity provenance",
        MAX_QUANTITY_PROVENANCE_BYTES,
    )
    signature = _hex_bytes(
        receipt.ed25519_signature_hex,
        64,
        "physical quantity Ed25519 signature",
    )
    signed_payload = _QUANTITY_DOMAIN + _canonical(receipt.payload())
    if len(_canonical(receipt.record())) > MAX_PHYSICAL_QUANTITY_RECEIPT_BYTES:
        raise ValueError("physical quantity receipt exceeds byte capacity")
    try:
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(mount.ed25519_public_key_hex)
        ).verify(signature, signed_payload)
    except InvalidSignature as error:
        raise ValueError("physical quantity Ed25519 signature changed") from error


class PhysicalQuantityIssuerAuthority:
    """Private provenance authority; the flow receives only its public mount."""

    def __init__(
        self,
        *,
        issuer_id: str,
        private_key: Ed25519PrivateKey,
    ) -> None:
        _identifier(issuer_id, "physical quantity issuer id")
        if not isinstance(private_key, Ed25519PrivateKey):
            raise TypeError("physical quantity private key is not Ed25519")
        self._issuer_id = issuer_id
        self._private_key = private_key

    @classmethod
    def from_private_key_bytes(
        cls,
        *,
        issuer_id: str,
        private_key_bytes: bytes,
    ) -> "PhysicalQuantityIssuerAuthority":
        if not isinstance(private_key_bytes, bytes) or len(private_key_bytes) != 32:
            raise ValueError("Ed25519 private key seed must be exactly 32 bytes")
        return cls(
            issuer_id=issuer_id,
            private_key=Ed25519PrivateKey.from_private_bytes(private_key_bytes),
        )

    @property
    def verifier_mount(self) -> PhysicalQuantityVerifierMount:
        return PhysicalQuantityVerifierMount(
            issuer_id=self._issuer_id,
            ed25519_public_key_hex=(
                self._private_key.public_key().public_bytes_raw().hex()
            ),
        )

    def sign(
        self,
        *,
        quantity_id: str,
        quantity_role: str,
        value: Fraction,
        unit: str,
        provenance_id: str,
    ) -> SignedPhysicalQuantity:
        provisional = SignedPhysicalQuantity(
            issuer_id=self._issuer_id,
            quantity_id=quantity_id,
            quantity_role=quantity_role,
            value=value,
            unit=unit,
            provenance_id=provenance_id,
            ed25519_signature_hex="0" * 128,
        )
        _identifier(quantity_id, "physical quantity id")
        _identifier(
            quantity_role,
            "physical quantity role",
            MAX_QUANTITY_ROLE_BYTES,
        )
        _exact_fraction(value, "physical quantity value")
        _identifier(unit, "physical quantity unit")
        _identifier(
            provenance_id,
            "physical quantity provenance",
            MAX_QUANTITY_PROVENANCE_BYTES,
        )
        signed_payload = _QUANTITY_DOMAIN + _canonical(provisional.payload())
        if len(signed_payload) + 128 > MAX_PHYSICAL_QUANTITY_RECEIPT_BYTES:
            raise ValueError("physical quantity receipt exceeds byte capacity")
        result = SignedPhysicalQuantity(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name != "ed25519_signature_hex"
            },
            ed25519_signature_hex=self._private_key.sign(
                signed_payload
            ).hex(),
        )
        verify_signed_physical_quantity(result, self.verifier_mount)
        return result


__all__ = (
    "PhysicalQuantityIssuerAuthority",
    "PhysicalQuantityVerifierMount",
    "SignedPhysicalQuantity",
    "verify_signed_physical_quantity",
)
