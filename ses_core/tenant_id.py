from __future__ import annotations

import json
import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class TenantIdentity:
    """
    Canonical SES-Core tenant identity representation.

    Fields are intentionally minimal. Extended attributes should be carried in
    the 'attributes' mapping while keeping the core identifiers stable.
    """

    tenant_id: str
    display_name: str
    environment: str
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "display_name": self.display_name,
            "environment": self.environment,
            "attributes": dict(self.attributes),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "TenantIdentity":
        tenant_id = str(data.get("tenant_id", "")).strip()
        display_name = str(data.get("display_name", "")).strip()
        environment = str(data.get("environment", "")).strip()
        attributes_raw = data.get("attributes") or {}
        if not isinstance(attributes_raw, Mapping):
            raise ValueError("attributes must be a mapping")

        if not tenant_id:
            raise ValueError("tenant_id must be non-empty")
        if not environment:
            raise ValueError("environment must be non-empty")

        return TenantIdentity(
            tenant_id=tenant_id,
            display_name=display_name,
            environment=environment,
            attributes=dict(attributes_raw),
        )

    def hkdf_salt(self) -> bytes:
        """
        Derive a stable HKDF salt from the canonical tenant identity.

        This salt is deterministic for a given logical tenant and environment
        and suitable as a salt input to HKDF-based key derivation.
        """
        canonical = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(canonical).digest()


@dataclass(frozen=True)
class UserIdentity:
    """
    Canonical SES-Core user identity representation linked to a tenant.
    """

    user_id: str
    tenant_id: str
    display_name: str
    roles: Mapping[str, Any] = field(default_factory=dict)
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "display_name": self.display_name,
            "roles": dict(self.roles),
            "attributes": dict(self.attributes),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "UserIdentity":
        user_id = str(data.get("user_id", "")).strip()
        tenant_id = str(data.get("tenant_id", "")).strip()
        display_name = str(data.get("display_name", "")).strip()
        roles_raw = data.get("roles") or {}
        attributes_raw = data.get("attributes") or {}

        if not isinstance(roles_raw, Mapping):
            raise ValueError("roles must be a mapping")
        if not isinstance(attributes_raw, Mapping):
            raise ValueError("attributes must be a mapping")

        if not user_id:
            raise ValueError("user_id must be non-empty")
        if not tenant_id:
            raise ValueError("tenant_id must be non-empty")

        return UserIdentity(
            user_id=user_id,
            tenant_id=tenant_id,
            display_name=display_name,
            roles=dict(roles_raw),
            attributes=dict(attributes_raw),
        )


class TenantIdentityService:
    """
    Service for creating and validating tenant and user identities in a manner
    consistent with SES-Core TIRM.

    This implementation is deterministic and pure with respect to identity
    structure. Persistence, directory lookups, and external identity providers
    are intentionally out of scope for Phase 1.
    """

    @staticmethod
    def create_tenant(
        display_name: str,
        environment: str,
        attributes: Optional[Mapping[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> TenantIdentity:
        env = environment.strip()
        if not env:
            raise ValueError("environment must be non-empty")

        if tenant_id:
            tid = tenant_id.strip()
        else:
            tid = f"t-{uuid.uuid4().hex}"

        return TenantIdentity(
            tenant_id=tid,
            display_name=display_name.strip(),
            environment=env,
            attributes=dict(attributes or {}),
        )

    @staticmethod
    def create_user(
        tenant: TenantIdentity,
        display_name: str,
        roles: Optional[Mapping[str, Any]] = None,
        attributes: Optional[Mapping[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> UserIdentity:
        if user_id:
            uid = user_id.strip()
        else:
            uid = f"u-{uuid.uuid4().hex}"

        return UserIdentity(
            user_id=uid,
            tenant_id=tenant.tenant_id,
            display_name=display_name.strip(),
            roles=dict(roles or {}),
            attributes=dict(attributes or {}),
        )

    @staticmethod
    def validate_tenant(tenant: TenantIdentity) -> None:
        _ = TenantIdentity.from_dict(asdict(tenant))

    @staticmethod
    def validate_user(user: UserIdentity) -> None:
        _ = UserIdentity.from_dict(asdict(user))
