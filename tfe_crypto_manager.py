"""
tfe_crypto_manager.py
-----------------------------------------
TFECryptoManager with STABLE SES-Core Tenant/User identities.

This module wraps the SES-Core adapter (tfe_ses_core_adapter) and
provides a stable crypto/custody context for the Tao Financial Engine.

Key properties (v1.0 single-tenant mode):
  - tenant_id = "tenant-tao"
  - user_id   = "user-primary"

These IDs are used on EVERY run, so SES-Core always looks up and writes
to the SAME encrypted portfolio envelopes. This fixes the persistence
issue where SES-Core was generating new tenant IDs each run.

AWS integration:
  - When TFE_ENV=aws, we derive the SES-Core root key from AWS Secrets
    Manager via AwsSecretsRootKeyProvider (aws_root_key_provider.py).
  - Otherwise (default), we pass root_key_provider=None and rely on the existing
    local/dev root-key behavior inside SES-Core.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Any

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

from aws_root_key_provider import AwsSecretsRootKeyProvider


# Stable identity constants for v1.0 single-tenant mode
TENANT_ID = "tenant-tao"
TENANT_DISPLAY_NAME = "Tao Tenant"

USER_ID = "user-primary"
USER_DISPLAY_NAME = "Tao Primary User"


@dataclass
class TFECryptoManager:
    """
    High-level SES-Core crypto/custody context for TFE.

    Fields:
      - ctx: SESCoreContext initialized for environment/region/purpose
      - tenant: stable TenantIdentity
      - user:   stable UserIdentity
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
        purpose_prefix: str = "tfe",
    ) -> "TFECryptoManager":
        """
        Construct a TFECryptoManager with STABLE tenant/user IDs.

        This must be called once per process; the resulting instance
        is then reused by TFE.

        Root key behavior:

          - If TFE_ENV=aws (case-insensitive), we:
              * Use AwsSecretsRootKeyProvider.from_env()
              * Pass provider handle into initialize_ses_core_for_env
                (no direct root_key byte fetch in app code)

          - Otherwise, we pass root_key_provider=None, which preserves the
            existing local/dev behavior (static root key handling
            inside SES-Core).
        """

        # Decide whether we are running in AWS mode.
        # Default: use the explicit 'environment' argument, but allow an
        # override via TFE_ENV so deployment can switch behavior without
        # changing code.
        env_flag = os.environ.get("TFE_ENV", environment).lower()

        if env_flag == "aws":
            # AWS mode: pass provider boundary into SES-Core
            root_key_provider = AwsSecretsRootKeyProvider.from_env()
        else:
            # Local/dev mode: keep existing behavior (no explicit provider)
            root_key_provider = None

        ctx = initialize_ses_core_for_env(
            environment=environment,
            region=region,
            purpose_prefix=purpose_prefix,
            root_key_provider=root_key_provider,
        )

        # Raw, stable identities (no tenant_service.create_* used)
        tenant = TenantIdentity(
            tenant_id=TENANT_ID,
            display_name=TENANT_DISPLAY_NAME,
            environment=environment,
            attributes={},
        )

        user = UserIdentity(
            user_id=USER_ID,
            tenant_id=tenant.tenant_id,
            display_name=USER_DISPLAY_NAME,
            roles={},
            attributes={},
        )

        return cls(
            ctx=ctx,
            tenant=tenant,
            user=user,
        )

    # -----------------------------------
    # Encryption / Decryption helpers
    # -----------------------------------

    def encrypt_portfolio(
        self,
        portfolio_id: str,
        payload: Mapping[str, Any],
    ):
        """
        Encrypt a portfolio payload into an SES-Core Envelope,
        using a domain specific to this portfolio.
        """
        domain = make_domain(
            ctx=self.ctx,
            purpose_suffix=f"portfolio-{portfolio_id}",
            version="v1",
        )
        envelope = encrypt_blob(
            ctx=self.ctx,
            tenant=self.tenant,
            domain=domain,
            payload=payload,
            actor_id=self.user.user_id,
        )
        return envelope

    def decrypt_portfolio(
        self,
        portfolio_id: str,
        envelope,
    ) -> Mapping[str, Any]:
        """
        Decrypt an SES-Core Envelope back into a Python mapping using
        the same domain that was used for encryption.
        """
        domain = make_domain(
            ctx=self.ctx,
            purpose_suffix=f"portfolio-{portfolio_id}",
            version="v1",
        )
        payload = decrypt_blob(
            ctx=self.ctx,
            tenant=self.tenant,
            domain=domain,
            envelope=envelope,
            actor_id=self.user.user_id,
        )
        return payload

    def record_custody(
        self,
        asset_id: str,
        action_suffix: str,
        payload: Mapping[str, Any],
    ):
        """
        Record a chain-of-custody event for portfolio-related actions.
        """
        action = f"tfe.{action_suffix}"
        record_custody_event(
            ctx=self.ctx,
            tenant_id=self.tenant.tenant_id,
            actor_id=self.user.user_id,
            asset_id=asset_id,
            payload=payload,
            action=action,
        )
