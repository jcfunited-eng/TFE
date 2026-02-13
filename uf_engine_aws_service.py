"""
uf_engine_aws_service.py
-----------------------------------------
UF-Engine AWS Service Skeleton (v1.0)

This module exposes a minimal "service layer" for the UF Engine that:

  - Uses uf_kernel_engine to compute UF structural state for a symbol.
  - Uses UFEngineSESContext (SES-Core adapter) to:
        * encrypt the UF structural payload ("UF-SP")
        * record a chain-of-custody event
  - Returns a JSON-serializable response payload suitable for:
        * local CLI testing
        * future wrapping in AWS Lambda / API Gateway

IMPORTANT:
  - This file does NOT talk directly to AWS SDKs.
  - All crypto is delegated to SES-Core via uf_engine_ses_adapter.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any, Dict

from uf_engine_ses_adapter import UFEngineSESContext

# NOTE: We assume uf_kernel_engine.py provides evaluate_symbol_snapshot.
# This matches how you run it via:
#   python uf_kernel_engine.py AAPL
try:
    from uf_kernel_engine import evaluate_symbol_snapshot
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "uf_engine_aws_service.py requires uf_kernel_engine.py with "
        "an evaluate_symbol_snapshot(symbol, asset_type='stock') function."
    ) from exc


# -------------------------------------------------------------------
# Version / environment constants
# -------------------------------------------------------------------

ENGINE_VERSION = "uf-engine-aws-v1.0"
UF_CORE_SPEC_VERSION = "uf-core-spec-v1.4.0"

DEFAULT_ENVIRONMENT = os.getenv("UF_ENGINE_ENV", "dev")
DEFAULT_REGION = os.getenv("UF_ENGINE_REGION", "local")
DEFAULT_TENANT_ID = os.getenv("UF_ENGINE_TENANT_ID", "tenant-tao")


# -------------------------------------------------------------------
# UF-Engine AWS Service
# -------------------------------------------------------------------


class UFEngineAwsService:
    """
    Minimal service wrapper around:
      - UF Kernel Engine evaluation
      - SES-Core encryption / custody for UF-SP
    """

    def __init__(
        self,
        environment: str = DEFAULT_ENVIRONMENT,
        region: str = DEFAULT_REGION,
        purpose_prefix: str = "uf-engine",
    ) -> None:
        self.environment = environment
        self.region = region

        # Initialize SES-Core context for UF Engine
        self.ses_ctx = UFEngineSESContext.from_environment(
            environment=environment,
            region=region,
            purpose_prefix=purpose_prefix,
        )

    # -----------------------------------
    # Health Check
    # -----------------------------------

    def health_check(self) -> Dict[str, Any]:
        """
        Return a simple health/status payload.

        In a real AWS deployment this would be the payload behind a
        /health or similar endpoint.
        """
        return {
            "status": "OK",
            "operation": "HealthCheck",
            "uf_engine_version": ENGINE_VERSION,
            "uf_core_spec_version": UF_CORE_SPEC_VERSION,
            "environment": self.environment,
            "region": self.region,
            # Future: wire real integrity checks here.
            "integrity_status": "NOT_CHECKED_STUB",
        }

    # -----------------------------------
    # Evaluate Symbol
    # -----------------------------------

    def evaluate_symbol(
        self,
        tenant_id: str,
        asset_id: str,
        asset_type: str = "stock",
        uf_domain_version: str = "v1",
    ) -> Dict[str, Any]:
        """
        Evaluate a single symbol via UF Kernel Engine and wrap the result in
        an SES-Core envelope.

        Parameters:
          tenant_id:  logical tenant identifier (for the caller)
          asset_id:   symbol/ticker identifier (e.g. "AAPL")
          asset_type: domain type ("stock", "etf", "crypto", "index", ...)
        """

        # 1) Run the UF Kernel Engine to get structural state
        uf_state: Dict[str, Any] = evaluate_symbol_snapshot(
            symbol=asset_id,
            asset_type=asset_type,
        )

        # 2) Encrypt the UF state as UF-SP envelope
        envelope = self.ses_ctx.encrypt_uf_state(
            asset_id=asset_id,
            payload=uf_state,
            version=uf_domain_version,
        )

        # 3) Convert envelope to plain dict for JSON (handles SES-Core Envelope)
        if hasattr(envelope, "to_dict") and callable(getattr(envelope, "to_dict")):
            envelope_dict = envelope.to_dict()
        elif is_dataclass(envelope):
            envelope_dict = asdict(envelope)
        else:
            # assume it's already a mapping
            envelope_dict = dict(envelope)

        # 4) Record chain-of-custody event
        self.ses_ctx.record_uf_custody_event(
            asset_id=asset_id,
            action_suffix="evaluate_symbol",
            payload={
                "environment": self.environment,
                "region": self.region,
                "uf_engine_version": ENGINE_VERSION,
                "uf_core_spec_version": UF_CORE_SPEC_VERSION,
                "tenant_id": tenant_id,
            },
        )

        # 5) Assemble response payload
        response: Dict[str, Any] = {
            "status": "OK",
            "operation": "EvaluateSymbol",
            "tenant_id": tenant_id,
            "asset_id": asset_id,
            "asset_type": asset_type,
            "uf_engine_version": ENGINE_VERSION,
            "uf_core_spec_version": UF_CORE_SPEC_VERSION,
            "environment": self.environment,
            "region": self.region,
            "envelope": envelope_dict,
        }
        return response


# -------------------------------------------------------------------
# Local test harness
# -------------------------------------------------------------------


def _local_test() -> None:
    """
    Simple local smoke test.

    This is what you already ran as:
        python uf_engine_aws_service.py

    It will:
      - build a UFEngineAwsService with dev/local
      - run a HealthCheck
      - run EvaluateSymbol on AAPL with tenant-tao
    """
    service = UFEngineAwsService(
        environment=DEFAULT_ENVIRONMENT,
        region=DEFAULT_REGION,
    )

    print("=== UF-Engine AWS Service Skeleton Local Test ===\n")

    health = service.health_check()
    print("[HealthCheck response]")
    print(json.dumps(health, indent=2))
    print()

    eval_resp = service.evaluate_symbol(
        tenant_id=DEFAULT_TENANT_ID,
        asset_id="AAPL",
        asset_type="stock",
    )
    print("[EvaluateSymbol response]")
    print(json.dumps(eval_resp, indent=2))

    print("\n=== End Test ===")


if __name__ == "__main__":
    _local_test()
