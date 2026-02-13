"""
tfe_ses_core_adapter.py
------------------------------------
SES-Core → TFE Integration Adapter (Phase 1)

This module provides a stable interface for TFE code to access SES-Core
functionality without depending on internal SES-Core structures.

All SES-Core objects remain internal to this adapter.
TFE code calls only these adapter functions.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

# SES-Core imports
from ses_core import (
    TenantIdentity,
    UserIdentity,
    TenantIdentityService,
    DomainParameters,
    StaticRootKeyProvider,
    KeyDerivationService,
    Envelope,
    EnvelopeService,
    FileChainOfCustodySink,
    ChainOfCustodyService,
)
from ses_core.aead_backend import AESGCMBackend


# ------------------------------------------------------------
# Adapter Context — Holds active SES-Core components
# ------------------------------------------------------------

@dataclass
class SESCoreContext:
    """
    Holds initialized SES-Core services for a single TFE environment.
    """

    environment: str
    region: str
    purpose_prefix: str
    root_key_provider: StaticRootKeyProvider
    kdf: KeyDerivationService
    envelope_service: EnvelopeService
    coc_service: ChainOfCustodyService
    tenant_service: TenantIdentityService


# ------------------------------------------------------------
# Initialization  (STABLE ROOT KEY)
# ------------------------------------------------------------

def initialize_ses_core_for_env(
    environment: str,
    region: str = "local",
    purpose_prefix: str = "tfe",
    root_key: Optional[bytes] = None,
) -> SESCoreContext:
    """
    Initialize AES-GCM envelope service, HKDF, and chain-of-custody logging
    for the given TFE runtime environment.

    CRITICAL CHANGE:
      - The root key is now loaded from 'tfe_root_key.bin'.
      - If the file does not exist, a new 32-byte key is generated ONCE
        and persisted to that file.
      - This guarantees that encryption and decryption use the same root
        key across restarts, preventing InvalidTag errors.
    """

    root_key_path = "tfe_root_key.bin"

    if root_key is None:
        if os.path.exists(root_key_path):
            with open(root_key_path, "rb") as f:
                root_key = f.read()
        else:
            root_key = os.urandom(32)
            with open(root_key_path, "wb") as f:
                f.write(root_key)

    root_provider = StaticRootKeyProvider(key=root_key)
    kdf = KeyDerivationService(root_key_provider=root_provider)

    envelope_service = EnvelopeService(
        key_derivation=kdf,
        aead_backend=AESGCMBackend(),
    )

    coc_sink = FileChainOfCustodySink(path=f"coc_events_{environment}.log")
    coc_service = ChainOfCustodyService(sink=coc_sink)

    return SESCoreContext(
        environment=environment,
        region=region,
        purpose_prefix=purpose_prefix,
        root_key_provider=root_provider,
        kdf=kdf,
        envelope_service=envelope_service,
        coc_service=coc_service,
        tenant_service=TenantIdentityService(),
    )


# ------------------------------------------------------------
# Tenant & User Identity (TIRM)
# ------------------------------------------------------------

def create_tenant(
    ctx: SESCoreContext,
    display_name: str,
    attributes: Optional[Mapping[str, Any]] = None,
) -> TenantIdentity:
    """
    Create a canonical SES-Core tenant identity for TFE.

    NOTE:
      In our current design we now prefer to use raw, stable TenantIdentity
      objects directly in TFECryptoManager, rather than calling this for the
      main TFE tenant. This function remains available for future provisioning
      flows (e.g. creating new tenants).
    """
    tenant = ctx.tenant_service.create_tenant(
        display_name=display_name,
        environment=ctx.environment,
        attributes=attributes,
    )
    ctx.tenant_service.validate_tenant(tenant)
    return tenant


def create_user(
    ctx: SESCoreContext,
    tenant: TenantIdentity,
    display_name: str,
    roles: Optional[Mapping[str, Any]] = None,
    attributes: Optional[Mapping[str, Any]] = None,
) -> UserIdentity:
    """
    Create a canonical SES-Core user identity for TFE.

    As with create_tenant, for the primary TFE tenant/user we now construct
    raw stable identities directly in TFECryptoManager, but this function
    remains useful for future multi-tenant provisioning flows.
    """
    user = ctx.tenant_service.create_user(
        tenant=tenant,
        display_name=display_name,
        roles=roles,
        attributes=attributes,
    )
    ctx.tenant_service.validate_user(user)
    return user


# ------------------------------------------------------------
# Domain Parameters
# ------------------------------------------------------------

def make_domain(
    ctx: SESCoreContext,
    purpose_suffix: str,
    version: str = "v1",
) -> DomainParameters:
    """
    Construct SES-Core domain parameters using TFE's prefix + suffix model.
    """
    purpose = f"{ctx.purpose_prefix}-{purpose_suffix}"
    return DomainParameters(
        environment=ctx.environment,
        region=ctx.region,
        purpose=purpose,
        version=version,
    )


# ------------------------------------------------------------
# Encryption / Decryption
# ------------------------------------------------------------

def encrypt_blob(
    ctx: SESCoreContext,
    tenant: TenantIdentity,
    domain: DomainParameters,
    payload: Mapping[str, Any],
    actor_id: str,
) -> Envelope:
    """
    Encrypt a portfolio / account / settings blob into an SES-Core envelope.
    """

    plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    metadata = {
        "actor_id": actor_id,
        "source": "tfe-adapter",
    }

    return ctx.envelope_service.encrypt(
        tenant=tenant,
        domain=domain,
        plaintext=plaintext,
        associated_metadata=metadata,
    )


def decrypt_blob(
    ctx: SESCoreContext,
    tenant: TenantIdentity,
    domain: DomainParameters,
    envelope: Envelope,
    actor_id: str,
) -> Dict[str, Any]:
    """
    Decrypt an SES-Core envelope back into a Python dict for TFE.
    """

    metadata = {
        "actor_id": actor_id,
        "source": "tfe-adapter",
    }

    plaintext = ctx.envelope_service.decrypt(
        tenant=tenant,
        domain=domain,
        envelope=envelope,
        associated_metadata=metadata,
    )

    return json.loads(plaintext.decode("utf-8"))


# ------------------------------------------------------------
# Chain of Custody
# ------------------------------------------------------------

def record_custody_event(
    ctx: SESCoreContext,
    tenant_id: str,
    actor_id: str,
    asset_id: str,
    action: str,
    payload: Mapping[str, Any],
):
    """
    Record a TFE action into SES-Core's chain-of-custody log.
    """
    return ctx.coc_service.record_event(
        tenant_id=tenant_id,
        actor_id=actor_id,
        asset_id=asset_id,
        action=action,
        payload=payload,
    )


# ------------------------------------------------------------
# High-level combined operation: Encrypt + Log
# ------------------------------------------------------------

def encrypt_and_log(
    ctx: SESCoreContext,
    tenant: TenantIdentity,
    user: UserIdentity,
    domain: DomainParameters,
    payload: Mapping[str, Any],
    asset_id: str,
    action_suffix: str,
) -> Envelope:
    """
    Encrypt a blob AND create a chain-of-custody event in one operation.
    """

    envelope = encrypt_blob(
        ctx=ctx,
        tenant=tenant,
        domain=domain,
        payload=payload,
        actor_id=user.user_id,
    )

    event_payload = {
        "asset_id": asset_id,
        "purpose": domain.purpose,
        "version": domain.version,
        "envelope_key_id": envelope.key_id,
    }

    record_custody_event(
        ctx=ctx,
        tenant_id=tenant.tenant_id,
        actor_id=user.user_id,
        asset_id=asset_id,
        action=f"tfe.{action_suffix}.encrypt",
        payload=event_payload,
    )

    return envelope
