"""
tfe_app_integration.py
-----------------------------------------
SES-Core → TFE Integration Layer

This module glues together:
  - TFECryptoManager (encryption + custody)
  - TFEPortfolioService (encrypted portfolio storage)
and exposes a simple interface for the Tao Financial Engine (TFE)
application code to use.

Design goals:
  - TFE never talks to SES-Core primitives directly.
  - TFE uses a small, stable set of functions.
  - Multi-tenant usage is supported via tenant_display_name.
  - Users are identified by user_display_name.
  - Portfolios are identified by a string portfolio_id.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from tfe_crypto_manager import TFECryptoManager
from tfe_portfolio_service import TFEPortfolioService, PortfolioSummary


# ------------------------------------------------------------
# App-level SES-Core / TFE context
# ------------------------------------------------------------

@dataclass
class TFEAppContext:
    """
    Holds the initialized SES-Core crypto stack and portfolio service.

    environment: logical environment name (e.g. "dev", "prod")
    region: logical region (e.g. "local", "us-east-1")
    """
    environment: str
    region: str
    crypto_manager: TFECryptoManager
    portfolio_service: TFEPortfolioService


def init_tfe_app_context(
    environment: str = "dev",
    region: str = "local",
    purpose_prefix: str = "tfe",
) -> TFEAppContext:
    """
    Initialize the SES-Core → TFE integration stack.

    This function SHOULD be called once at application startup.
    """
    # Crypto manager: wraps SES-Core adapter and keys
    crypto_manager = TFECryptoManager.from_environment(
        environment=environment,
        region=region,
        purpose_prefix=purpose_prefix,
    )

    # Portfolio service: wraps crypto manager + index + storage
    portfolio_service = TFEPortfolioService.from_environment(
        environment=environment,
        region=region,
        purpose_prefix=purpose_prefix,
    )

    ctx = TFEAppContext(
        environment=environment,
        region=region,
        crypto_manager=crypto_manager,
        portfolio_service=portfolio_service,
    )

    return ctx


# ------------------------------------------------------------
# Portfolio Operations – App-Facing API
# ------------------------------------------------------------

def save_portfolio(
    ctx: TFEAppContext,
    tenant_display_name: str,
    user_display_name: str,
    portfolio_id: str,
    portfolio_data: Mapping[str, Any],
    label: str = "",
) -> PortfolioSummary:
    """
    Encrypt and store a portfolio under the given tenant and user.

    This is the function the TFE app should call whenever a portfolio is
    created or updated.

    Parameters:
      ctx:                TFEAppContext from init_tfe_app_context()
      tenant_display_name: human-readable tenant label (e.g. "Tao")
      user_display_name:   human-readable user label (e.g. "Tao Primary")
      portfolio_id:        stable ID for this portfolio (string)
      portfolio_data:      arbitrary mapping representing the portfolio
      label:               optional UI label for the portfolio

    Returns:
      PortfolioSummary object describing the stored portfolio.
    """
    summary = ctx.portfolio_service.create_or_update_portfolio(
        tenant_display_name=tenant_display_name,
        user_display_name=user_display_name,
        portfolio_id=portfolio_id,
        portfolio_data=portfolio_data,
        label=label,
    )
    return summary


def load_portfolio(
    ctx: TFEAppContext,
    tenant_display_name: str,
    user_display_name: str,
    portfolio_id: str,
) -> Mapping[str, Any]:
    """
    Load and decrypt a portfolio.

    Parameters:
      ctx:                TFEAppContext
      tenant_display_name: must match the name used when saving
      user_display_name:   must match the name used when saving
      portfolio_id:        ID of the portfolio

    Returns:
      A mapping (dict-like) representing the decrypted portfolio data.
    """
    return ctx.portfolio_service.load_portfolio(
        tenant_display_name=tenant_display_name,
        user_display_name=user_display_name,
        portfolio_id=portfolio_id,
    )


def list_portfolios_for_tenant(
    ctx: TFEAppContext,
    tenant_display_name: str,
) -> List[PortfolioSummary]:
    """
    Return a list of PortfolioSummary objects for the given tenant.

    Useful for populating UI lists and dashboards.
    """
    return ctx.portfolio_service.list_portfolios_for_tenant(
        tenant_display_name=tenant_display_name,
    )


def list_portfolios_for_tenant_as_dicts(
    ctx: TFEAppContext,
    tenant_display_name: str,
) -> List[Dict[str, Any]]:
    """
    Convenience wrapper returning portfolio summaries as plain dicts,
    easier to consume from UI code.
    """
    summaries = list_portfolios_for_tenant(ctx, tenant_display_name)
    return [s.to_dict() for s in summaries]


# ------------------------------------------------------------
# Example CLI Demo – Optional Smoke Test
# ------------------------------------------------------------

def _demo() -> None:
    """
    Optional command-line demo for manual testing.

    Run from the TFE project root:

        python tfe_app_integration.py

    This will:
      - Initialize SES-Core → TFE context (dev/local)
      - Save an example portfolio
      - List portfolios for the tenant
      - Load and print the decrypted portfolio
    """
    ctx = init_tfe_app_context(environment="dev", region="local")

    tenant_name = "Demo Tenant"
    user_name = "Demo User"
    portfolio_id = "demo-portfolio-001"

    # Example portfolio structure – TFE UI would provide this in reality
    portfolio_data = {
        "portfolio_id": portfolio_id,
        "owner": user_name,
        "positions": [
            {"symbol": "VTI", "shares": 50},
            {"symbol": "VXUS", "shares": 25},
            {"symbol": "BND", "shares": 10},
        ],
        "value": 12345.67,
        "currency": "USD",
        "risk_profile": "balanced",
    }

    print("\n=== TFE App Integration Demo ===\n")
    print("Initializing SES-Core → TFE context...")
    print(f"Environment: {ctx.environment}")
    print(f"Region:      {ctx.region}")
    print()

    print("Saving encrypted portfolio...")
    summary = save_portfolio(
        ctx=ctx,
        tenant_display_name=tenant_name,
        user_display_name=user_name,
        portfolio_id=portfolio_id,
        portfolio_data=portfolio_data,
        label="Demo Balanced Portfolio",
    )
    print("PortfolioSummary:")
    print(summary)
    print()

    print("Listing portfolios for tenant:", tenant_name)
    summaries = list_portfolios_for_tenant_as_dicts(ctx, tenant_name)
    print(json.dumps(summaries, indent=2))
    print()

    print("Loading and decrypting portfolio...")
    recovered = load_portfolio(
        ctx=ctx,
        tenant_display_name=tenant_name,
        user_display_name=user_name,
        portfolio_id=portfolio_id,
    )
    print("Recovered portfolio JSON:")
    print(json.dumps(recovered, indent=2))
    print()

    print("=== Demo Complete ===\n")


if __name__ == "__main__":
    _demo()
