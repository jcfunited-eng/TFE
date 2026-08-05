"""Strict migration-only unwrapping of manifest-authenticated owner state."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from dsf_ai_service.substrate.owner_scoped_persistence import (
    OWNER_STATE_BODY_SCHEMA,
    OWNER_STATE_GROUPS,
    owner_state_body_mutation_root,
)


_HEX = frozenset("0123456789abcdef")


class AuthenticatedOwnerStateUnwrapError(RuntimeError):
    """An authenticated outer state body cannot be derived exactly."""


@dataclass(frozen=True, slots=True)
class AuthenticatedOwnerStatePayload:
    relative_path: str
    owner_id: str
    state_key: str
    outer_file_sha256: str
    derived_inner_sha256: str
    inner_bytes: bytes


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise AuthenticatedOwnerStateUnwrapError(
            "expected outer digest is not a canonical SHA-256"
        )
    return value


def _canonical_inner(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def unwrap_authenticated_owner_state(
    *,
    relative_path: str,
    outer_bytes: bytes,
    expected_outer_sha256: str,
    expected_owner_id: str,
    expected_state_key: str,
) -> AuthenticatedOwnerStatePayload:
    if not isinstance(relative_path, str) or not relative_path:
        raise TypeError("owner state relative path must be a nonempty string")
    if not isinstance(outer_bytes, bytes):
        raise TypeError("owner state outer body must be immutable bytes")
    expected = _sha(expected_outer_sha256)
    if _sha256(outer_bytes) != expected:
        raise AuthenticatedOwnerStateUnwrapError(
            "owner state bytes differ from the authenticated manifest member"
        )
    groups = tuple(
        group
        for group in OWNER_STATE_GROUPS
        if group.owner_id == expected_owner_id
        and group.state_keys == (expected_state_key,)
    )
    if len(groups) != 1:
        raise AuthenticatedOwnerStateUnwrapError(
            "requested owner/state key has no unique frozen outer contract"
        )
    try:
        owner_state_body_mutation_root(groups[0], outer_bytes)
        outer = json.loads(outer_bytes)
    except Exception as error:
        raise AuthenticatedOwnerStateUnwrapError(
            "owner state outer contract changed"
        ) from error
    if (
        not isinstance(outer, dict)
        or set(outer) != {"owner_id", "schema", "state"}
        or outer["schema"] != OWNER_STATE_BODY_SCHEMA
        or outer["owner_id"] != expected_owner_id
        or not isinstance(outer["state"], dict)
        or set(outer["state"]) != {expected_state_key}
    ):
        raise AuthenticatedOwnerStateUnwrapError(
            "owner state identity or state-key surface changed"
        )
    inner_bytes = _canonical_inner(outer["state"][expected_state_key])
    return AuthenticatedOwnerStatePayload(
        relative_path=relative_path,
        owner_id=expected_owner_id,
        state_key=expected_state_key,
        outer_file_sha256=expected,
        derived_inner_sha256=_sha256(inner_bytes),
        inner_bytes=inner_bytes,
    )


__all__ = (
    "AuthenticatedOwnerStatePayload",
    "AuthenticatedOwnerStateUnwrapError",
    "unwrap_authenticated_owner_state",
)
