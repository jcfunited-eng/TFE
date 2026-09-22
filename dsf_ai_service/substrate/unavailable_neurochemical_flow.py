"""Truthful typed custody for an unavailable neurochemical flow mechanism.

This owner asserts no species, concentration, quantity, transport, reaction,
reward, mood, salience, or quiescent chemical state.  It binds the exact
current internal-body snapshot to one authenticated reason explaining why
neurochemical flow is unavailable in this release.
"""

from __future__ import annotations

import hashlib
import hmac
import json

from dsf_ai_service.substrate.physical_internal_body_state import (
    COLD_SCHEMA as INTERNAL_BODY_COLD_SCHEMA,
    PhysicalInternalBodyStateAuthority,
)


UNAVAILABLE_REASON = (
    "no_ratified_exact_species_quantities_or_kinetics"
)
STATE_SCHEMA = "guala.unavailable_neurochemical_flow.state.v1"
STATUS_SCHEMA = "guala.unavailable_neurochemical_flow.status.v1"
_STATE_DOMAIN = b"guala-unavailable-neurochemical-flow-state-v1\0"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class UnavailableNeurochemicalFlowOwner:
    """Cold-exact unavailable chemistry bound to the real internal body."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        internal_body_owner: PhysicalInternalBodyStateAuthority,
        max_state_bytes: int = 32 * 1024 * 1024,
    ) -> None:
        raw_key = (
            authority_key.encode("utf-8")
            if isinstance(authority_key, str)
            else authority_key
        )
        if not isinstance(raw_key, bytes) or len(raw_key) < 32:
            raise ValueError(
                "unavailable chemistry authority key is invalid"
            )
        if type(internal_body_owner) is not (
            PhysicalInternalBodyStateAuthority
        ):
            raise TypeError(
                "unavailable chemistry requires the exact internal-body "
                "owner"
            )
        if (
            isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or not 2_048 <= max_state_bytes <= 128 * 1024 * 1024
        ):
            raise ValueError(
                "unavailable chemistry state capacity is invalid"
            )
        self._key = hashlib.sha256(
            _STATE_DOMAIN + raw_key
        ).digest()
        self._internal_body_owner = internal_body_owner
        self._max_state_bytes = max_state_bytes
        self.snapshot_encoded()

    def _body(self) -> dict[str, object]:
        snapshot = self._internal_body_owner.snapshot_encoded()
        if not isinstance(snapshot, bytes) or not snapshot:
            raise ValueError(
                "unavailable chemistry lost internal-body custody"
            )
        try:
            body_envelope = json.loads(snapshot)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "unavailable chemistry internal-body state is unreadable"
            ) from error
        if (
            not isinstance(body_envelope, dict)
            or body_envelope.get("schema")
            != INTERNAL_BODY_COLD_SCHEMA
            or _canonical(body_envelope) != snapshot
        ):
            raise ValueError(
                "unavailable chemistry internal-body authority changed"
            )
        return {
            "chemical_state": {
                "available": False,
                "mechanism_state": "unavailable",
                "quiescent_claim": False,
                "reason": UNAVAILABLE_REASON,
            },
            "internal_body_snapshot_bytes": len(snapshot),
            "internal_body_snapshot_sha256": (
                hashlib.sha256(snapshot).hexdigest()
            ),
            "schema": STATE_SCHEMA,
        }

    def snapshot_encoded(self) -> bytes:
        body = self._body()
        encoded = _canonical({
            "body": body,
            "schema": STATE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._max_state_bytes:
            raise RuntimeError(
                "unavailable chemistry state capacity exhausted"
            )
        return encoded

    def status(self) -> dict[str, object]:
        encoded = self.snapshot_encoded()
        return {
            "available": False,
            "chemistry_authority": False,
            "mechanism_state": "unavailable",
            "quiescent_claim": False,
            "reason": UNAVAILABLE_REASON,
            "schema": STATUS_SCHEMA,
            "state_bytes": len(encoded),
            "state_capacity_bytes": self._max_state_bytes,
        }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        internal_body_owner: PhysicalInternalBodyStateAuthority,
        encoded: bytes,
        max_state_bytes: int = 32 * 1024 * 1024,
    ) -> "UnavailableNeurochemicalFlowOwner":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError(
                "unavailable chemistry cold state is absent"
            )
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "unavailable chemistry cold state is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != STATE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError(
                "unavailable chemistry cold envelope changed"
            )
        body = envelope.get("body")
        if (
            not isinstance(body, dict)
            or set(body)
            != {
                "chemical_state",
                "internal_body_snapshot_bytes",
                "internal_body_snapshot_sha256",
                "schema",
            }
            or body.get("schema") != STATE_SCHEMA
            or body.get("chemical_state")
            != {
                "available": False,
                "mechanism_state": "unavailable",
                "quiescent_claim": False,
                "reason": UNAVAILABLE_REASON,
            }
        ):
            raise ValueError(
                "unavailable chemistry cold payload changed"
            )
        current_body = internal_body_owner.snapshot_encoded()
        if (
            isinstance(body.get("internal_body_snapshot_bytes"), bool)
            or not isinstance(body.get("internal_body_snapshot_bytes"), int)
            or body["internal_body_snapshot_bytes"] != len(current_body)
            or hashlib.sha256(current_body).hexdigest()
            != body.get("internal_body_snapshot_sha256")
        ):
            raise ValueError(
                "unavailable chemistry restored internal body changed"
            )
        owner = cls(
            authority_key=authority_key,
            internal_body_owner=internal_body_owner,
            max_state_bytes=max_state_bytes,
        )
        expected_hmac = hmac.new(
            owner._key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected_hmac,
        ):
            raise ValueError(
                "unavailable chemistry cold authority changed"
            )
        if owner.snapshot_encoded() != encoded:
            raise ValueError(
                "unavailable chemistry cold round-trip changed"
            )
        return owner


__all__ = (
    "STATE_SCHEMA",
    "STATUS_SCHEMA",
    "UNAVAILABLE_REASON",
    "UnavailableNeurochemicalFlowOwner",
)
