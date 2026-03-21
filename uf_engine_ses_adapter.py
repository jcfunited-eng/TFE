"""
uf_engine_ses_adapter.py
-----------------------------------------
SES-Core adapter for the UF Engine (UF-Core L0–L4).

Purpose:
  - Give the UF Engine its own stable Tenant/User identities.
  - Provide small, focused helpers for:
      * encrypting UF structural payloads ("UF-SP")
      * decrypting them
      * recording chain-of-custody events

This mirrors tfe_crypto_manager.TFECryptoManager but is UF-Engine–specific and
domain-agnostic (no TFE UI assumptions).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from tfe_ses_core_adapter import (
    SESCoreContext,
    initialize_ses_core_for_env,
    TenantIdentity,
    UserIdentity,
    make_domain,
    encrypt_blob,
    decrypt_blob,
    record_custody_event,
)


# -------------------------------------------------------------------
# Stable identity constants for UF Engine v1.0
# -------------------------------------------------------------------

# For now we reuse the same tenant as TFE to keep setup simple.
# If you later want a dedicated UF Engine tenant, you can change
# TENANT_ID / TENANT_DISPLAY_NAME here without touching TFE code.
TENANT_ID = "tenant-tao"
TENANT_DISPLAY_NAME = "Tao Tenant"

# Dedicated UF Engine service identity
USER_ID = "uf-engine-service"
USER_DISPLAY_NAME = "UF Engine Service"


# -------------------------------------------------------------------
# UF Engine SES-Core Context
# -------------------------------------------------------------------


@dataclass
class UFEngineSESContext:
    """
    High-level SES-Core crypto/custody context for the UF Engine.

    Fields:
      - ctx:    SESCoreContext initialized for environment/region/purpose
      - tenant: stable TenantIdentity
      - user:   stable UserIdentity (UF Engine service actor)
    """

    ctx: SESCoreContext
    tenant: TenantIdentity
    user: UserIdentity

    # -----------------------------------
    # Factory
    # -----------------------------------
    @classmethod
    def from_environment(
        cls,
        environment: str = "dev",
        region: str = "local",
        purpose_prefix: str = "uf-engine",
    ) -> "UFEngineSESContext":
        """
        Construct a UFEngineSESContext with STABLE tenant/user IDs.

        This should be called once per process and shared wherever the
        UF Engine needs to encrypt/decrypt UF structural payloads.
        """

        ctx = initialize_ses_core_for_env(
            environment=environment,
            region=region,
            purpose_prefix=purpose_prefix,
        )

        # Stable tenant identity
        tenant = TenantIdentity(
            tenant_id=TENANT_ID,
            display_name=TENANT_DISPLAY_NAME,
            environment=environment,
            attributes={"component": "uf-engine"},
        )

        # Stable UF Engine actor identity
        user = UserIdentity(
            user_id=USER_ID,
            tenant_id=tenant.tenant_id,
            display_name=USER_DISPLAY_NAME,
            roles={},
            attributes={"component": "uf-engine"},
        )

        return cls(
            ctx=ctx,
            tenant=tenant,
            user=user,
        )

    # -----------------------------------
    # UF-SP Encryption / Decryption
    # -----------------------------------

    def encrypt_uf_state(
        self,
        asset_id: str,
        payload: Mapping[str, Any],
        version: str = "v1",
    ):
        """
        Encrypt a UF structural payload ("UF-SP") into an SES-Core Envelope.

        Domain binding:
          purpose_suffix = f"uf-sp-{asset_id}"
          version        = version (default "v1")
        """
        domain = make_domain(
            ctx=self.ctx,
            purpose_suffix=f"uf-sp-{asset_id}",
            version=version,
        )

        envelope = encrypt_blob(
            ctx=self.ctx,
            tenant=self.tenant,
            domain=domain,
            payload=payload,
            actor_id=self.user.user_id,
        )
        return envelope

    def decrypt_uf_state(
        self,
        asset_id: str,
        envelope,
        version: str = "v1",
    ) -> Mapping[str, Any]:
        """
        Decrypt a UF-SP envelope back into a Python mapping using the same
        domain that was used for encryption.
        """
        domain = make_domain(
            ctx=self.ctx,
            purpose_suffix=f"uf-sp-{asset_id}",
            version=version,
        )

        payload = decrypt_blob(
            ctx=self.ctx,
            tenant=self.tenant,
            domain=domain,
            envelope=envelope,
            actor_id=self.user.user_id,
        )
        return payload

    # -----------------------------------
    # Chain-of-Custody for UF Engine
    # -----------------------------------

    def record_uf_custody_event(
        self,
        asset_id: str,
        action_suffix: str,
        payload: Mapping[str, Any],
    ) -> None:
        """
        Record a chain-of-custody event for UF Engine actions.

        action name: "uf-engine.{action_suffix}"
        """
        action = f"uf-engine.{action_suffix}"
        record_custody_event(
            ctx=self.ctx,
            tenant_id=self.tenant.tenant_id,
            actor_id=self.user.user_id,
            asset_id=asset_id,
            payload=payload,
            action=action,
        )
