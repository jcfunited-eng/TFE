"""Ed25519 custody for exact per-boundary AE local-receptor activation."""

from __future__ import annotations

import json
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


SCHEMA = "guala.ae_local_receptor.activation.v1"
_DOMAIN = b"guala-ae-local-receptor-activation-v1\0"
_HEX = frozenset("0123456789abcdef")
SENSE_IDS = ("body", "sight", "smell", "sound", "taste", "touch")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{label} changed")
    return value


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} is not a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class AELocalReceptorVerifierMount:
    issuer_id: str
    ed25519_public_key_hex: str

    def verify(self) -> None:
        _identifier(self.issuer_id, "local receptor issuer")
        if (
            not isinstance(self.ed25519_public_key_hex, str)
            or len(self.ed25519_public_key_hex) != 64
            or any(
                character not in _HEX
                for character in self.ed25519_public_key_hex
            )
        ):
            raise ValueError("local receptor public key changed")


@dataclass(frozen=True, slots=True)
class AELocalReceptorActivation:
    issuer_id: str
    sense: str
    activation_state: int
    settlement_receipt_sha256: str
    chemical_boundary_receipt_sha256: str
    flow_event_receipt_sha256: str
    flow_transition_receipt_sha256: str
    target_id: str | None
    component_id: str | None
    carrier_passoff_receipt_sha256: str | None
    local_target_exposure_receipt_sha256: str | None
    ed25519_signature_hex: str

    def payload(self) -> dict[str, object]:
        return {
            "activation_state": self.activation_state,
            "carrier_passoff_receipt_sha256": (
                self.carrier_passoff_receipt_sha256
            ),
            "chemical_boundary_receipt_sha256": (
                self.chemical_boundary_receipt_sha256
            ),
            "component_id": self.component_id,
            "flow_event_receipt_sha256": self.flow_event_receipt_sha256,
            "flow_transition_receipt_sha256": (
                self.flow_transition_receipt_sha256
            ),
            "issuer_id": self.issuer_id,
            "local_target_exposure_receipt_sha256": (
                self.local_target_exposure_receipt_sha256
            ),
            "schema": SCHEMA,
            "sense": self.sense,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "target_id": self.target_id,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "ed25519_signature_hex": self.ed25519_signature_hex
        }


def verify_ae_local_receptor_activation(
    value: AELocalReceptorActivation,
    verifier: AELocalReceptorVerifierMount,
) -> None:
    if not isinstance(value, AELocalReceptorActivation):
        raise TypeError("AE local receptor activation is not typed")
    verifier.verify()
    if value.issuer_id != verifier.issuer_id:
        raise ValueError("AE local receptor issuer changed")
    if value.sense not in SENSE_IDS:
        raise ValueError("AE local receptor sense changed")
    if value.activation_state not in {0, 1}:
        raise ValueError("AE local receptor state is not ternary zero/one")
    for receipt, label in (
        (value.settlement_receipt_sha256, "receptor settlement"),
        (
            value.chemical_boundary_receipt_sha256,
            "receptor chemical boundary",
        ),
        (value.flow_event_receipt_sha256, "receptor flow event"),
        (
            value.flow_transition_receipt_sha256,
            "receptor flow transition",
        ),
    ):
        _sha(receipt, label)
    activated_fields = (
        value.target_id,
        value.component_id,
        value.carrier_passoff_receipt_sha256,
        value.local_target_exposure_receipt_sha256,
    )
    if value.activation_state == 0:
        if any(item is not None for item in activated_fields):
            raise ValueError("quiescent receptor carries a fabricated pass-off")
    else:
        if any(item is None for item in activated_fields):
            raise ValueError("activated receptor lacks exact pass-off custody")
        _identifier(value.target_id, "receptor target")
        _identifier(value.component_id, "receptor component")
        if (
            value.target_id
            not in {
                f"target:ae-excitation:{value.sense}:a",
                f"target:ae-excitation:{value.sense}:b",
            }
            or value.component_id
            not in {
                f"component:ae-excitation:{value.sense}:a",
                f"component:ae-excitation:{value.sense}:b",
            }
            or value.target_id.rsplit(":", 1)[-1]
            != value.component_id.rsplit(":", 1)[-1]
        ):
            raise ValueError("activated receptor crossed its local target")
        _sha(
            value.carrier_passoff_receipt_sha256,
            "receptor carrier pass-off",
        )
        _sha(
            value.local_target_exposure_receipt_sha256,
            "receptor local target exposure",
        )
    if (
        not isinstance(value.ed25519_signature_hex, str)
        or len(value.ed25519_signature_hex) != 128
        or any(
            character not in _HEX
            for character in value.ed25519_signature_hex
        )
    ):
        raise ValueError("AE local receptor signature changed")
    try:
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(verifier.ed25519_public_key_hex)
        ).verify(
            bytes.fromhex(value.ed25519_signature_hex),
            _DOMAIN + _canonical(value.payload()),
        )
    except InvalidSignature as error:
        raise ValueError(
            "AE local receptor activation signature changed"
        ) from error


class AELocalReceptorAuthority:
    def __init__(
        self,
        *,
        issuer_id: str,
        private_key_bytes: bytes,
    ) -> None:
        _identifier(issuer_id, "local receptor issuer")
        if not isinstance(private_key_bytes, bytes) or len(
            private_key_bytes
        ) != 32:
            raise ValueError("local receptor private key changed")
        self._issuer_id = issuer_id
        self._private = Ed25519PrivateKey.from_private_bytes(
            private_key_bytes
        )

    @property
    def verifier_mount(self) -> AELocalReceptorVerifierMount:
        return AELocalReceptorVerifierMount(
            issuer_id=self._issuer_id,
            ed25519_public_key_hex=(
                self._private.public_key().public_bytes_raw().hex()
            ),
        )

    def sign(
        self,
        *,
        sense: str,
        activation_state: int,
        settlement_receipt_sha256: str,
        chemical_boundary_receipt_sha256: str,
        flow_event_receipt_sha256: str,
        flow_transition_receipt_sha256: str,
        target_id: str | None,
        component_id: str | None,
        carrier_passoff_receipt_sha256: str | None,
        local_target_exposure_receipt_sha256: str | None,
    ) -> AELocalReceptorActivation:
        provisional = AELocalReceptorActivation(
            issuer_id=self._issuer_id,
            sense=sense,
            activation_state=activation_state,
            settlement_receipt_sha256=settlement_receipt_sha256,
            chemical_boundary_receipt_sha256=(
                chemical_boundary_receipt_sha256
            ),
            flow_event_receipt_sha256=flow_event_receipt_sha256,
            flow_transition_receipt_sha256=(
                flow_transition_receipt_sha256
            ),
            target_id=target_id,
            component_id=component_id,
            carrier_passoff_receipt_sha256=(
                carrier_passoff_receipt_sha256
            ),
            local_target_exposure_receipt_sha256=(
                local_target_exposure_receipt_sha256
            ),
            ed25519_signature_hex="0" * 128,
        )
        signed = AELocalReceptorActivation(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name != "ed25519_signature_hex"
            },
            ed25519_signature_hex=self._private.sign(
                _DOMAIN + _canonical(provisional.payload())
            ).hex(),
        )
        verify_ae_local_receptor_activation(
            signed, self.verifier_mount
        )
        return signed


__all__ = (
    "AELocalReceptorActivation",
    "AELocalReceptorAuthority",
    "AELocalReceptorVerifierMount",
    "SCHEMA",
    "SENSE_IDS",
    "verify_ae_local_receptor_activation",
)
