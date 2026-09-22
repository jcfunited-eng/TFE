"""One-record persistence boundary for the active native resident organism.

The record contains one canonical ``GLORUN01`` body.  Python performs only
bounded transport encoding and exact receipt verification; it does not decode,
select, score, or duplicate cognitive state as another authority.
"""

from __future__ import annotations

import base64
import binascii
import hashlib

from dsf_ai_service.glew_runtime.native_resident_organism import (
    NativeResidentOrganism,
    restore_native_resident_organism,
)


PERSISTENCE_SCHEMA = "guala.native.resident_organism.persistence.v1"
PERSISTENCE_KEYS = frozenset({
    "byte_count",
    "schema",
    "state_base64",
    "state_sha256",
})
STATE_MAGIC = b"GLORUN01"


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"resident persistence {label} must be positive")
    return value


def _canonical_sha256(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("resident persistence receipt is not canonical SHA-256")
    return value


def encode_native_resident_organism(
    organism: NativeResidentOrganism,
    *,
    max_envelope_bytes: int,
) -> dict[str, object]:
    """Encode one immutable observation of the active resident state."""

    if not isinstance(organism, NativeResidentOrganism):
        raise TypeError("resident persistence requires the concrete organism")
    maximum = _positive_integer(max_envelope_bytes, "envelope boundary")
    before = organism.readiness()
    state = organism.save()
    after = organism.readiness()
    if (
        before.state_sha256 != after.state_sha256
        or before.state_bytes != after.state_bytes
        or not state.startswith(STATE_MAGIC)
        or len(state) > maximum
        or len(state) != before.state_bytes
        or hashlib.sha256(state).hexdigest() != before.state_sha256
    ):
        raise RuntimeError("resident persistence active state changed while encoding")
    return {
        "byte_count": len(state),
        "schema": PERSISTENCE_SCHEMA,
        "state_base64": base64.b64encode(state).decode("ascii"),
        "state_sha256": before.state_sha256,
    }


def restore_native_resident_organism_record(
    record: object,
    *,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> NativeResidentOrganism:
    """Restore the exact current state; no predecessor or fallback is read."""

    envelope_limit = _positive_integer(
        max_envelope_bytes, "envelope boundary"
    )
    fabric_limit = _positive_integer(max_fabric_bytes, "fabric boundary")
    logical_limit = _positive_integer(
        max_logical_peak_bytes, "logical peak boundary"
    )
    if fabric_limit >= envelope_limit or logical_limit <= 2 * envelope_limit:
        raise ValueError("resident persistence budgets are structurally invalid")
    if (
        not isinstance(record, dict)
        or set(record) != PERSISTENCE_KEYS
        or record.get("schema") != PERSISTENCE_SCHEMA
    ):
        raise ValueError("resident persistence record shape changed")
    byte_count = _positive_integer(record.get("byte_count"), "byte count")
    if byte_count > envelope_limit:
        raise ValueError("resident persistence state exceeds its envelope boundary")
    expected_sha256 = _canonical_sha256(record.get("state_sha256"))
    encoded = record.get("state_base64")
    canonical_character_count = 4 * ((byte_count + 2) // 3)
    if (
        not isinstance(encoded, str)
        or not encoded.isascii()
        or len(encoded) != canonical_character_count
    ):
        raise ValueError("resident persistence base64 width changed")
    encoded_copy_bytes = len(encoded)
    decoded_copy_bytes = byte_count
    native_transfer_bytes = byte_count
    native_logical_peak = logical_limit - (
        encoded_copy_bytes + decoded_copy_bytes + native_transfer_bytes
    )
    if native_logical_peak <= 2 * envelope_limit:
        raise ValueError("resident persistence copies exceed the logical peak")
    try:
        state = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("resident persistence base64 is invalid") from error
    if (
        base64.b64encode(state).decode("ascii") != encoded
        or len(state) != byte_count
        or not state.startswith(STATE_MAGIC)
        or hashlib.sha256(state).hexdigest() != expected_sha256
    ):
        raise ValueError("resident persistence body or receipt changed")
    organism = restore_native_resident_organism(
        current_envelope=state,
        max_envelope_bytes=envelope_limit,
        max_fabric_bytes=fabric_limit,
        max_logical_peak_bytes=native_logical_peak,
    )
    observation = organism.readiness()
    if (
        observation.state_bytes != byte_count
        or observation.state_sha256 != expected_sha256
        or organism.save() != state
    ):
        raise RuntimeError("resident persistence restore changed current state")
    return organism


__all__ = (
    "PERSISTENCE_SCHEMA",
    "encode_native_resident_organism",
    "restore_native_resident_organism_record",
)
