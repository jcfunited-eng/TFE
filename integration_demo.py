from __future__ import annotations

import json
import os

from ses_core import (
    TenantIdentityService,
    DomainParameters,
    StaticRootKeyProvider,
    KeyDerivationService,
    EnvelopeService,
    FileChainOfCustodySink,
    ChainOfCustodyService,
)
from ses_core.aead_backend import AESGCMBackend


def main() -> None:
    # 1. Root key and key derivation
    root_key = os.urandom(32)
    root_provider = StaticRootKeyProvider(key=root_key)
    kdf_service = KeyDerivationService(root_key_provider=root_provider)

    # 2. AEAD backend and envelope service
    aead_backend = AESGCMBackend()
    envelope_service = EnvelopeService(
        key_derivation=kdf_service,
        aead_backend=aead_backend,
    )

    # 3. Tenant identity (TIRM binding)
    tenant_service = TenantIdentityService()
    tenant = tenant_service.create_tenant(
        display_name="Demo Tenant",
        environment="dev",
    )
    tenant_service.validate_tenant(tenant)

    # 4. Domain parameters (SES-Core domain binding)
    domain = DomainParameters(
        environment="dev",
        region="local",
        purpose="tfe-demo-payload",
        version="v1",
    )

    # 5. Sample payload and associated metadata
    payload_obj = {
        "portfolio_id": "demo-123",
        "balance": 12345.67,
        "currency": "USD",
    }
    plaintext = json.dumps(payload_obj, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    associated_metadata = {
        "actor_id": "u-demo",
        "source": "integration_demo",
    }

    # 6. Encrypt to SES-Core envelope
    envelope = envelope_service.encrypt(
        tenant=tenant,
        domain=domain,
        plaintext=plaintext,
        associated_metadata=associated_metadata,
    )

    # 7. Decrypt from SES-Core envelope
    recovered = envelope_service.decrypt(
        tenant=tenant,
        domain=domain,
        envelope=envelope,
        associated_metadata=associated_metadata,
    )
    if recovered != plaintext:
        raise RuntimeError("Decrypted payload does not match original plaintext")

    # 8. Chain-of-custody event logging
    coc_sink = FileChainOfCustodySink(path="coc_events.log")
    coc_service = ChainOfCustodyService(sink=coc_sink)

    event_payload = {
        "portfolio_id": payload_obj["portfolio_id"],
        "operation": "encrypt_roundtrip",
        "envelope_key_id": envelope.key_id,
        "environment": domain.environment,
        "region": domain.region,
        "purpose": domain.purpose,
        "version": domain.version,
    }

    event = coc_service.record_event(
        tenant_id=tenant.tenant_id,
        actor_id=associated_metadata["actor_id"],
        asset_id=f"portfolio:{payload_obj['portfolio_id']}",
        action="demo.encrypt_roundtrip",
        payload=event_payload,
    )

    print("=== SES-Core → TFE Phase 1 Integration Demo ===")
    print("Tenant ID:", tenant.tenant_id)
    print("Envelope JSON:", envelope.to_json())
    print("Recovered payload:", recovered.decode("utf-8"))
    print("Chain-of-custody event ID:", event.event_id)
    print("Chain-of-custody log written to: coc_events.log")


if __name__ == "__main__":
    main()
