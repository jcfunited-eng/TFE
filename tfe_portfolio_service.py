"""
tfe_portfolio_service.py
-----------------------------------------
TFEPortfolioService backed by SES-Core with STABLE Tenant/User IDs.

This service:
  - Uses TFECryptoManager to encrypt/decrypt portfolio payloads.
  - Persists SES-Core Envelope objects to disk in a deterministic
    path based on tenant_id and portfolio_id.
  - Provides create/update/load/list operations for TFE.

Storage layout (v1.0):
  - Directory: tfe_encrypted_portfolios/
  - File per portfolio:
        {tenant_id}__{portfolio_id}.json

For now:
  - Single tenant:  tenant-tao
  - Single user:    user-primary

Future:
  - Multi-tenant can be introduced by parameterizing tenant_id and
    user_id, but the on-disk layout remains compatible.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import json

from ses_core import Envelope
from tfe_crypto_manager import TFECryptoManager


PORTFOLIO_DIR = Path("tfe_encrypted_portfolios")
PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PortfolioSummary:
    """
    Lightweight summary of a stored portfolio.
    """

    tenant_id: str
    portfolio_id: str
    label: str
    metadata: Mapping[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "portfolio_id": self.portfolio_id,
            "label": self.label,
            "metadata": dict(self.metadata),
        }


@dataclass
class TFEPortfolioService:
    """
    Portfolio storage service on top of SES-Core.

    Uses:
      - TFECryptoManager (stable tenant/user + SES-Core context)
      - File-based Envelope persistence under tfe_encrypted_portfolios/
    """

    crypto_manager: TFECryptoManager

    # -----------------------------------
    # Factory
    # -----------------------------------
    @classmethod
    def from_environment(
        cls,
        environment: str = "dev",
        region: str = "local",
        purpose_prefix: str = "tfe",
    ) -> "TFEPortfolioService":
        cm = TFECryptoManager.from_environment(
            environment=environment,
            region=region,
            purpose_prefix=purpose_prefix,
        )
        return cls(crypto_manager=cm)

    # -----------------------------------
    # Internal helpers
    # -----------------------------------

    def _portfolio_path(self, portfolio_id: str) -> Path:
        """
        Compute a deterministic path for a given portfolio_id,
        based on the stable tenant_id.
        """
        tenant_id = self.crypto_manager.tenant.tenant_id
        fname = f"{tenant_id}__{portfolio_id}.json"
        return PORTFOLIO_DIR / fname

    # -----------------------------------
    # Public API
    # -----------------------------------

    def create_or_update_portfolio(
        self,
        tenant_display_name: str,
        user_display_name: str,
        portfolio_id: str,
        portfolio_data: Mapping[str, Any],
        label: str = "",
    ) -> PortfolioSummary:
        """
        Encrypt and store a portfolio via SES-Core, then persist Envelope to disk.
        """

        # Encrypt via SES-Core using stable tenant/user
        envelope = self.crypto_manager.encrypt_portfolio(
            portfolio_id=portfolio_id,
            payload=portfolio_data,
        )

        # Persist envelope as JSON
        path = self._portfolio_path(portfolio_id)
        path.write_text(envelope.to_json(), encoding="utf-8")

        # Optional: record custody event
        self.crypto_manager.record_custody(
            asset_id=f"portfolio:{portfolio_id}",
            action_suffix="portfolio.save",
            payload={
                "label": label or portfolio_id,
                "display_tenant": tenant_display_name,
                "display_user": user_display_name,
            },
        )

        return PortfolioSummary(
            tenant_id=self.crypto_manager.tenant.tenant_id,
            portfolio_id=portfolio_id,
            label=label or portfolio_id,
            metadata={
                "display_tenant": tenant_display_name,
                "display_user": user_display_name,
            },
        )

    def load_portfolio(
        self,
        tenant_display_name: str,
        user_display_name: str,
        portfolio_id: str,
    ) -> Mapping[str, Any]:
        """
        Load and decrypt a stored portfolio via SES-Core.
        """
        path = self._portfolio_path(portfolio_id)
        if not path.exists():
            raise FileNotFoundError(f"No portfolio stored for id={portfolio_id}")

        raw = path.read_text(encoding="utf-8")
        envelope = Envelope.from_json(raw)

        payload = self.crypto_manager.decrypt_portfolio(
            portfolio_id=portfolio_id,
            envelope=envelope,
        )
        return payload

    def list_portfolios_for_tenant(
        self,
        tenant_display_name: str,
    ) -> List[PortfolioSummary]:
        """
        List all portfolios for the stable tenant by scanning the portfolio
        directory for files matching {tenant_id}__*.json
        """
        tenant_id = self.crypto_manager.tenant.tenant_id
        summaries: List[PortfolioSummary] = []

        prefix = f"{tenant_id}__"

        for path in PORTFOLIO_DIR.glob("*.json"):
            name = path.name
            if not name.startswith(prefix):
                continue
            portfolio_id = name[len(prefix) : -5]  # strip tenant + ".json"
            summaries.append(
                PortfolioSummary(
                    tenant_id=tenant_id,
                    portfolio_id=portfolio_id,
                    label=portfolio_id,
                    metadata={"display_tenant": tenant_display_name},
                )
            )

        return summaries
