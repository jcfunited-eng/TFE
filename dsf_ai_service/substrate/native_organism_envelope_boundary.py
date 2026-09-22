"""Isolated current-only persistence custody for one native Guala envelope.

This boundary is limited to the stateless migration rehearsal.  It is not the
resident-organism runtime, live recurrence authority, or a production resource
certificate.  It accepts only one concrete native ``GLORUN01`` result and
reserves the persistence string, decoded state, and native-transfer copies
before decoding a persistence record.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import importlib

from dsf_ai_service.glew_runtime.native_organism_runtime import (
    ImmutableNativeOrganismTransition,
    restore_native_organism,
)


PERSISTENCE_SCHEMA = "guala.native.organism_envelope.persistence.v1"
PERSISTENCE_KEYS = frozenset({
    "byte_count",
    "schema",
    "state_base64",
    "state_sha256",
})

_GLORUN_MAGIC = b"GLORUN01"
_GLORUN_FIXED_BYTES = 8 + 2 + 36 + 8 + 4
_GLMFAB_FIXED_BYTES = 8 + 2 + 8 + 4
_VERIFIED_ENVELOPE_CAPABILITY = object()


def _native_core():
    return importlib.import_module("guala_core")


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _canonical_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} is not canonical SHA-256")
    return value


def _preflight_budget(
    *,
    max_envelope_bytes: object,
    max_fabric_bytes: object,
    max_logical_peak_bytes: object,
) -> tuple[int, int, int]:
    envelope = _positive_integer(
        max_envelope_bytes,
        "native organism envelope byte boundary",
    )
    fabric = _positive_integer(
        max_fabric_bytes,
        "native organism fabric byte boundary",
    )
    logical = _positive_integer(
        max_logical_peak_bytes,
        "native organism logical peak byte boundary",
    )
    if envelope <= _GLORUN_FIXED_BYTES:
        raise ValueError("native organism envelope boundary cannot hold GLORUN01")
    if fabric <= _GLMFAB_FIXED_BYTES:
        raise ValueError("native organism fabric boundary cannot hold GLMFAB04")
    if fabric > envelope - _GLORUN_FIXED_BYTES:
        raise ValueError("native organism fabric boundary cannot fit its envelope")
    if logical <= 2 * envelope:
        raise ValueError(
            "native organism logical peak cannot retain both admitted envelopes"
        )
    return envelope, fabric, logical


def _admit_persistence_copy_peak(
    *,
    encoded_character_count: int,
    decoded_state_bytes: int,
    max_envelope_bytes: int,
    max_logical_peak_bytes: int,
) -> int:
    """Reserve exact payload copies that overlap the native restore call."""

    encoded_string_bytes = encoded_character_count
    decoded_python_bytes = decoded_state_bytes
    native_transfer_bytes = decoded_state_bytes
    infrastructure_copy_bytes = (
        encoded_string_bytes + decoded_python_bytes + native_transfer_bytes
    )
    native_logical_peak_bytes = (
        max_logical_peak_bytes - infrastructure_copy_bytes
    )
    if native_logical_peak_bytes <= 2 * max_envelope_bytes:
        raise ValueError(
            "native organism persistence copies exceed the admitted logical peak"
        )
    return native_logical_peak_bytes


def _require_concrete_native_transition(
    value: object,
) -> ImmutableNativeOrganismTransition:
    native_transition_type = getattr(
        _native_core(),
        "NativeOrganismRuntimeTransition",
        None,
    )
    if not isinstance(native_transition_type, type):
        raise RuntimeError("native organism transition type is unavailable")
    if type(value) is not native_transition_type:
        raise TypeError(
            "native organism persistence requires the concrete native result"
        )
    return value


@dataclass(frozen=True, slots=True, init=False)
class VerifiedNativeOrganismEnvelope:
    """Factory-only custody for an already authenticated current envelope."""

    state_bytes: bytes
    observation: ImmutableNativeOrganismTransition

    def __init__(
        self,
        *,
        state_bytes: bytes,
        observation: ImmutableNativeOrganismTransition,
        _capability: object | None = None,
    ) -> None:
        if _capability is not _VERIFIED_ENVELOPE_CAPABILITY:
            raise TypeError(
                "native organism verified envelope construction is factory-only"
            )
        object.__setattr__(self, "state_bytes", state_bytes)
        object.__setattr__(self, "observation", observation)
        self._verify_current_state()

    def _verify_current_state(self) -> None:
        if (
            not isinstance(self.state_bytes, bytes)
            or not self.state_bytes.startswith(_GLORUN_MAGIC)
        ):
            raise ValueError("native organism persistence is not current GLORUN01")
        state_sha256 = hashlib.sha256(self.state_bytes).hexdigest()
        if (
            self.observation.as_bytes() != self.state_bytes
            or self.observation.state_bytes != len(self.state_bytes)
            or self.observation.state_sha256 != state_sha256
        ):
            raise ValueError("native organism observation differs from its state")

    @classmethod
    def from_native(
        cls,
        value: ImmutableNativeOrganismTransition,
    ) -> "VerifiedNativeOrganismEnvelope":
        """Admit one concrete stateless native result for isolated rehearsal."""

        concrete = _require_concrete_native_transition(value)
        return cls(
            state_bytes=concrete.as_bytes(),
            observation=concrete,
            _capability=_VERIFIED_ENVELOPE_CAPABILITY,
        )

    @classmethod
    def from_persistence_record(
        cls,
        value: object,
        *,
        max_envelope_bytes: int,
        max_fabric_bytes: int,
        max_logical_peak_bytes: int,
    ) -> "VerifiedNativeOrganismEnvelope":
        if (
            not isinstance(value, dict)
            or set(value) != PERSISTENCE_KEYS
            or value.get("schema") != PERSISTENCE_SCHEMA
        ):
            raise ValueError("native organism persistence surface changed")
        envelope_limit, fabric_limit, logical_limit = _preflight_budget(
            max_envelope_bytes=max_envelope_bytes,
            max_fabric_bytes=max_fabric_bytes,
            max_logical_peak_bytes=max_logical_peak_bytes,
        )
        byte_count = value.get("byte_count")
        if (
            isinstance(byte_count, bool)
            or not isinstance(byte_count, int)
            or byte_count <= 0
        ):
            raise ValueError("native organism persistence byte count is invalid")
        if byte_count > envelope_limit:
            raise ValueError(
                "native organism persistence exceeds its envelope boundary"
            )
        state_sha256 = _canonical_sha256(
            value.get("state_sha256"),
            "native organism persistence state",
        )
        encoded = value.get("state_base64")
        if not isinstance(encoded, str) or not encoded:
            raise ValueError("native organism persistence bytes are absent")
        canonical_encoded_characters = 4 * ((byte_count + 2) // 3)
        if not encoded.isascii() or len(encoded) != canonical_encoded_characters:
            raise ValueError(
                "native organism persistence encoded length is not canonical"
            )
        native_logical_limit = _admit_persistence_copy_peak(
            encoded_character_count=len(encoded),
            decoded_state_bytes=byte_count,
            max_envelope_bytes=envelope_limit,
            max_logical_peak_bytes=logical_limit,
        )
        try:
            state_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as error:
            raise ValueError("native organism persistence bytes are invalid") from error
        if (
            base64.b64encode(state_bytes).decode("ascii") != encoded
            or len(state_bytes) != byte_count
            or hashlib.sha256(state_bytes).hexdigest() != state_sha256
        ):
            raise ValueError("native organism persistence custody changed")
        if not state_bytes.startswith(_GLORUN_MAGIC):
            raise ValueError("native organism persistence is not current GLORUN01")
        observation = restore_native_organism(
            current_envelope=state_bytes,
            max_envelope_bytes=envelope_limit,
            max_fabric_bytes=fabric_limit,
            max_logical_peak_bytes=native_logical_limit,
        )
        return cls.from_native(observation)

    def persistence_record(self) -> dict[str, object]:
        return {
            "byte_count": len(self.state_bytes),
            "schema": PERSISTENCE_SCHEMA,
            "state_base64": base64.b64encode(self.state_bytes).decode("ascii"),
            "state_sha256": hashlib.sha256(self.state_bytes).hexdigest(),
        }


__all__ = (
    "PERSISTENCE_SCHEMA",
    "VerifiedNativeOrganismEnvelope",
)
