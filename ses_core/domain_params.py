from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class DomainParameters:
    """
    Domain parameters bind keys and envelopes to a specific logical context.

    Examples of fields:
    - environment: "prod", "staging"
    - region: "us-east-1", "eu-central-1"
    - purpose: "tfe-portfolio-encrypt", "tfe-session-token"
    - version: monotonic schema or algorithm version
    """

    environment: str
    region: str
    purpose: str
    version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment": self.environment,
            "region": self.region,
            "purpose": self.purpose,
            "version": self.version,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "DomainParameters":
        environment = str(data.get("environment", "")).strip()
        region = str(data.get("region", "")).strip()
        purpose = str(data.get("purpose", "")).strip()
        version = str(data.get("version", "")).strip()

        if not environment:
            raise ValueError("environment must be non-empty")
        if not region:
            raise ValueError("region must be non-empty")
        if not purpose:
            raise ValueError("purpose must be non-empty")
        if not version:
            raise ValueError("version must be non-empty")

        return DomainParameters(
            environment=environment,
            region=region,
            purpose=purpose,
            version=version,
        )

    def kdf_context(self) -> bytes:
        """
        Returns a canonical byte string used as HKDF 'info' input for key
        derivation, ensuring that keys are tightly bound to the domain.
        """
        canonical = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return canonical
