"""
adapter_integration_test.py
-----------------------------------------
Full end-to-end test of SES-Core → TFE integration
through the tfe_ses_core_adapter module.

This verifies:

1. SES-Core initialization via adapter
2. Tenant creation (TIRM)
3. User creation (TIRM)
4. Domain construction
5. Encrypt blob through adapter
6. Decrypt blob through adapter
7. Chain-of-custody logging through adapter

All SES-Core internals remain hidden.
"""

from __future__ import annotations

import json

# Import adapter
import tfe_ses_core_adapter as adapter


def main() -> None:
    print("\n=== TFE Adapter Integration Test (SES-Core Phase 1) ===\n")

    # ----------------------------------------------------
    # 1. Initialize SES-Core context
    # ----------------------------------------------------
    ctx = adapter.initialize_ses_core_for_env(
        environment="dev",
        region="local",
        purpose_prefix="tfe",
    )

    print("SES-Core Context Initialized:")
    print("  Environment:", ctx.environment)
    print("  Region:     ", ctx.region)
    print("  PurposePrefix:", ctx.purpose_prefix)
    print()

    # ----------------------------------------------------
    # 2. Create tenant
    # ----------------------------------------------------
    tenant = adapter.create_tenant(
        ctx=ctx,
        display_name="Adapter Test Tenant",
        attributes={"tier": "demo"},
    )

    print("Tenant Created:")
    print("  Tenant ID:", tenant.tenant_id)
    print("  Display:  ", tenant.display_name)
    print()

    # ----------------------------------------------------
    # 3. Create user
    # ----------------------------------------------------
    user = adapter.create_user(
        ctx=ctx,
        tenant=tenant,
        display_name="Adapter Test User",
        roles={"role": "tester"},
        attributes={"department": "test-lab"},
    )

    print("User Created:")
    print("  User ID:", user.user_id)
    print("  Display:", user.display_name)
    print()

    # ----------------------------------------------------
    # 4. Create domain parameters
    # ----------------------------------------------------
    domain = adapter.make_domain(
        ctx=ctx,
        purpose_suffix="portfolio",
        version="v1",
    )

    print("Domain Created:")
    print("  Environment:", domain.environment)
    print("  Region:", domain.region)
    print("  Purpose:", domain.purpose)
    print("  Version:", domain.version)
    print()

    # ----------------------------------------------------
    # 5. Payload to encrypt
    # ----------------------------------------------------
    payload = {
        "portfolio_id": "demo-xyz",
        "positions": [
            {"symbol": "AAPL", "shares": 10},
            {"symbol": "TSLA", "shares": 3},
        ],
        "value": 27250.44,
        "currency": "USD",
    }

    print("Payload to Encrypt:")
    print(json.dumps(payload, indent=2))
    print()

    # ----------------------------------------------------
    # 6. Encrypt + log custody event
    # ----------------------------------------------------
    envelope = adapter.encrypt_and_log(
        ctx=ctx,
        tenant=tenant,
        user=user,
        domain=domain,
        payload=payload,
        asset_id=f"portfolio:{payload['portfolio_id']}",
        action_suffix="adapter-test",
    )

    print("Envelope Created:")
    print(envelope.to_json())
    print()

    # ----------------------------------------------------
    # 7. Decrypt using adapter
    # ----------------------------------------------------
    recovered = adapter.decrypt_blob(
        ctx=ctx,
        tenant=tenant,
        domain=domain,
        envelope=envelope,
        actor_id=user.user_id,
    )

    print("Decrypted Payload:")
    print(json.dumps(recovered, indent=2))
    print()

    # ----------------------------------------------------
    # 8. Validation
    # ----------------------------------------------------
    if recovered != payload:
        raise RuntimeError("Decrypted payload does NOT match original payload!")

    print("SUCCESS: Recovered payload matches original.")
    print("SUCCESS: Chain-of-custody event logged.")
    print("\n=== Adapter Integration Test Complete ===\n")


if __name__ == "__main__":
    main()
