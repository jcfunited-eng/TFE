"""
tfe_ses_core_adapter.py
------------------------------------
SES-Core -> TFE Integration Adapter (Phase 1)

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
    RootKeyProvider,
    StaticRootKeyProvider,
    KeyDerivationService,
    Envelope,
    EnvelopeService,
    FileChainOfCustodySink,
    ChainOfCustodyService,
)
from ses_core.aead_backend import SCESIVBackend


# ------------------------------------------------------------
# Canonical Domain Tuple Constants (deterministic)
# ------------------------------------------------------------

# Domain classes routed to canonical tuple binding.
UF_SNAPSHOT_PURPOSE_SUFFIX = "uf-snapshot"
WATCHLIST_PURPOSE_SUFFIX = "watchlist"
WATCHLIST_USER_PREFIX = "watchlist-"
PORTFOLIO_MANUAL_PURPOSE_SUFFIX = "portfolio-manual"
PORTFOLIO_MANUAL_USER_PREFIX = "portfolio-manual-"
GENERIC_PURPOSE_PROFILE = "generic"

# Deterministic defaults for all canonical tuple fields.
DEFAULT_CANONICAL_WINDOW_START = "2000-01-01T00:00:00Z"
DEFAULT_CANONICAL_WINDOW_END = "2099-12-31T00:00:00Z"
DEFAULT_CANONICAL_TIMEFRAME = "1D"
DEFAULT_CANONICAL_UF_VERSION = "v1.4.0"
DEFAULT_CANONICAL_SES_VERSION = "v2.0"
DEFAULT_CANONICAL_TENANT_ID = "tenant-tao"

# Profile-specific defaults.
DEFAULT_SYMBOL_BY_PROFILE: Dict[str, str] = {
    UF_SNAPSHOT_PURPOSE_SUFFIX: "UF_SNAPSHOT_UNIVERSE",
    WATCHLIST_PURPOSE_SUFFIX: "TFE_WATCHLIST_BLOB",
    PORTFOLIO_MANUAL_PURPOSE_SUFFIX: "TFE_PORTFOLIO_MANUAL_BLOB",
    GENERIC_PURPOSE_PROFILE: "TFE_GENERIC_BLOB",
}

DEFAULT_ENGINE_VARIANT_BY_PROFILE: Dict[str, str] = {
    UF_SNAPSHOT_PURPOSE_SUFFIX: "tfe-web-snapshot",
    WATCHLIST_PURPOSE_SUFFIX: "tfe-web-watchlist",
    PORTFOLIO_MANUAL_PURPOSE_SUFFIX: "tfe-web-portfolio-manual",
    GENERIC_PURPOSE_PROFILE: "tfe-generic",
}


def _normalize_env_suffix_token(value: str) -> str:
    token = "".join(ch if ch.isalnum() else "_" for ch in str(value).upper())
    token = token.strip("_")
    return token or "GENERIC"


def _normalize_variant_suffix_token(value: str) -> str:
    token = "".join(ch if ch.isalnum() else "-" for ch in str(value).lower())
    token = token.strip("-")
    return token or "generic"


def _canonical_profile_for_suffix(purpose_suffix: str) -> str:
    suffix = str(purpose_suffix).strip().lower()
    if suffix == UF_SNAPSHOT_PURPOSE_SUFFIX:
        return UF_SNAPSHOT_PURPOSE_SUFFIX
    if suffix == WATCHLIST_PURPOSE_SUFFIX or suffix.startswith(WATCHLIST_USER_PREFIX):
        return WATCHLIST_PURPOSE_SUFFIX
    if suffix == PORTFOLIO_MANUAL_PURPOSE_SUFFIX or suffix.startswith(PORTFOLIO_MANUAL_USER_PREFIX):
        return PORTFOLIO_MANUAL_PURPOSE_SUFFIX
    return GENERIC_PURPOSE_PROFILE


def _canonical_tuple_for_profile(
    ctx: "SESCoreContext",
    profile: str,
    purpose_suffix: str,
) -> Dict[str, str]:
    profile_upper = profile.upper().replace("-", "_")
    suffix_upper = _normalize_env_suffix_token(purpose_suffix)

    symbol_default = DEFAULT_SYMBOL_BY_PROFILE.get(profile, f"TFE_{suffix_upper}_BLOB")
    engine_variant_default = DEFAULT_ENGINE_VARIANT_BY_PROFILE.get(
        profile,
        f"tfe-{_normalize_variant_suffix_token(purpose_suffix)}",
    )

    symbol = str(
        os.environ.get(
            f"TFE_DOMAIN_SYMBOL_SUFFIX_{suffix_upper}",
            os.environ.get(
                f"TFE_DOMAIN_SYMBOL_{profile_upper}",
            os.environ.get("TFE_DOMAIN_SYMBOL", symbol_default),
            ),
        )
    ).strip()

    engine_variant = str(
        os.environ.get(
            f"TFE_ENGINE_VARIANT_SUFFIX_{suffix_upper}",
            os.environ.get(
                f"TFE_ENGINE_VARIANT_{profile_upper}",
            os.environ.get("TFE_ENGINE_VARIANT", engine_variant_default),
            ),
        )
    ).strip()

    return {
        "symbol": symbol,
        "window_start": str(
            os.environ.get("TFE_DOMAIN_WINDOW_START", DEFAULT_CANONICAL_WINDOW_START)
        ).strip(),
        "window_end": str(
            os.environ.get("TFE_DOMAIN_WINDOW_END", DEFAULT_CANONICAL_WINDOW_END)
        ).strip(),
        "timeframe": str(
            os.environ.get("TFE_DOMAIN_TIMEFRAME", DEFAULT_CANONICAL_TIMEFRAME)
        ).strip(),
        "uf_version": str(os.environ.get("TFE_UF_VERSION", DEFAULT_CANONICAL_UF_VERSION)).strip(),
        "ses_version": str(os.environ.get("TFE_SES_VERSION", DEFAULT_CANONICAL_SES_VERSION)).strip(),
        "tenant_id": str(
            os.environ.get("TFE_DOMAIN_TENANT_ID", DEFAULT_CANONICAL_TENANT_ID)
        ).strip(),
        "engine_variant": engine_variant,
        "environment": str(ctx.environment).strip(),
    }


# ------------------------------------------------------------
# Adapter Context - Holds active SES-Core components
# ------------------------------------------------------------


@dataclass
class SESCoreContext:
    """
    Holds initialized SES-Core services for a single TFE environment.
    """

    environment: str
    region: str
    purpose_prefix: str
    root_key_provider: RootKeyProvider
    kdf: KeyDerivationService
    envelope_service: EnvelopeService
    coc_service: ChainOfCustodyService
    tenant_service: TenantIdentityService


def _load_or_create_private_root_key(path: str) -> bytes:
    """
    Load an existing root-key file or create a new one with private mode (0600).
    """
    if os.path.exists(path):
        with open(path, "rb") as f:
            key = f.read()
        if len(key) < 32:
            raise ValueError("Existing root key file is invalid (must be at least 32 bytes).")
        try:
            os.chmod(path, 0o600)
        except Exception:
            # Best-effort on platforms/filesystems that restrict chmod behavior.
            pass
        return key

    key = os.urandom(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    return key


# ------------------------------------------------------------
# Initialization  (STABLE ROOT KEY)
# ------------------------------------------------------------


def initialize_ses_core_for_env(
    environment: str,
    region: str = "local",
    purpose_prefix: str = "tfe",
    root_key: Optional[bytes] = None,
    root_key_provider: Optional[RootKeyProvider] = None,
) -> SESCoreContext:
    """
    Initialize SES envelope service, HKDF, and chain-of-custody logging
    for the given TFE runtime environment.

    CRITICAL CHANGE:
      - The root key is loaded from 'tfe_root_key.bin'.
      - If the file does not exist, a new 32-byte key is generated ONCE
        and persisted to that file.
      - This guarantees that encryption and decryption use the same root
        key across restarts.
      - Encryption/decryption uses only SCE-SIV (`sce-siv-v1`).
      - Legacy AES-GCM compatibility paths are removed.
      - If root_key_provider is supplied, raw key bytes are never requested
        by application code outside SES-Core key derivation boundary.
    """

    root_key_path = "tfe_root_key.bin"

    if root_key_provider is not None and root_key is not None:
        raise ValueError("Provide either root_key_provider or root_key, not both.")

    if root_key_provider is not None:
        active_root_provider: RootKeyProvider = root_key_provider
    else:
        key_material = root_key
        if key_material is None:
            key_material = _load_or_create_private_root_key(root_key_path)
        active_root_provider = StaticRootKeyProvider(key=key_material)

    kdf = KeyDerivationService(root_key_provider=active_root_provider)

    sce_backend = SCESIVBackend()
    algorithm_backends: Dict[str, Any] = {"sce-siv-v1": sce_backend}

    envelope_service = EnvelopeService(
        key_derivation=kdf,
        aead_backend=sce_backend,
        algorithm_id="sce-siv-v1",
        algorithm_backends=algorithm_backends,
    )

    coc_sink = FileChainOfCustodySink(path=f"coc_events_{environment}.log")
    coc_service = ChainOfCustodyService(sink=coc_sink)

    return SESCoreContext(
        environment=environment,
        region=region,
        purpose_prefix=purpose_prefix,
        root_key_provider=active_root_provider,
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

    Canonical tuple wiring behavior:
    - Always canonical for all suffixes.
    - Known profiles use fixed deterministic symbols/variants.
    - Unknown suffixes use deterministic generic canonical defaults.
    """
    purpose = f"{ctx.purpose_prefix}-{purpose_suffix}"
    suffix_norm = str(purpose_suffix).strip().lower()

    profile = _canonical_profile_for_suffix(suffix_norm)
    tuple_values = _canonical_tuple_for_profile(ctx, profile, suffix_norm)
    return DomainParameters(
        environment=ctx.environment,
        region=ctx.region,
        purpose=purpose,
        version=version,
        symbol=tuple_values["symbol"],
        window_start=tuple_values["window_start"],
        window_end=tuple_values["window_end"],
        timeframe=tuple_values["timeframe"],
        uf_version=tuple_values["uf_version"],
        ses_version=tuple_values["ses_version"],
        tenant_id=tuple_values["tenant_id"],
        engine_variant=tuple_values["engine_variant"],
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
    Legacy migration fallback paths are intentionally removed.
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
