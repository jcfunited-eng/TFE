"""
tfe_portfolio_api.py
-----------------------------------------
SES-Core–backed Portfolio API Layer for TFE
NO CSV FALLBACK (SES-Core is the single source of truth).

This module now does ONLY:

  - Read/write portfolio via SES-Core-backed TFEPortfolioService.
  - Compute valuation via portfolio_valuation_engine.

Behavior:

  - If SES-Core portfolio exists → load and decode it.
  - If SES-Core portfolio does NOT exist → return an EMPTY portfolio DF.
  - CSV is NO LONGER USED AT ALL.

If you still have portfolio.csv, it is now irrelevant and will never
overwrite SES-Core.

Single-tenant identifiers (v1.0):

  TENANT_DISPLAY_NAME = "Tao Tenant"
  USER_DISPLAY_NAME   = "Tao Primary User"
  PORTFOLIO_ID        = "default"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from portfolio_valuation_engine import (
    compute_portfolio_valuation,
    PositionValuation,
    PortfolioValuation,
)
from tfe_app_integration import init_tfe_app_context


# ============================================================
# Constants
# ============================================================

TENANT_DISPLAY_NAME = "Tao Tenant"
USER_DISPLAY_NAME = "Tao Primary User"
PORTFOLIO_ID = "default"

_CTX = None  # cached TFEAppContext


def _get_ctx():
    """
    Lazy-initialize the TFE SES-Core context once per process.
    """
    global _CTX
    if _CTX is None:
        _CTX = init_tfe_app_context(environment="dev", region="local")
    return _CTX


# ============================================================
# DF ↔ payload conversion helpers
# ============================================================

def _df_to_payload(df: pd.DataFrame) -> dict:
    """
    Convert a portfolio DataFrame into a JSON-serializable dict
    for storage via SES-Core.

    Required columns:
      - ticker
      - quantity
      - cost_basis

    Optional:
      - asset_type
    """
    if df.empty:
        return {"rows": []}

    df_norm = df.copy()
    df_norm.columns = [c.lower().strip() for c in df_norm.columns]

    if "asset_type" not in df_norm.columns:
        df_norm["asset_type"] = "equity"

    df_norm["ticker"] = df_norm["ticker"].astype(str).str.upper()
    df_norm["quantity"] = df_norm["quantity"].astype(float)
    df_norm["cost_basis"] = df_norm["cost_basis"].astype(float)

    rows = df_norm[["ticker", "quantity", "cost_basis", "asset_type"]].to_dict(orient="records")
    return {"rows": rows}


def _payload_to_df(payload: dict) -> pd.DataFrame:
    """
    Convert SES-Core payload back into a DataFrame.
    """
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not rows:
        return pd.DataFrame(columns=["ticker", "quantity", "cost_basis", "asset_type"])

    df = pd.DataFrame(rows)
    df.columns = [c.lower().strip() for c in df.columns]
    if "asset_type" not in df.columns:
        df["asset_type"] = "equity"

    df["ticker"] = df["ticker"].astype(str).str.upper()
    df["quantity"] = df["quantity"].astype(float)
    df["cost_basis"] = df["cost_basis"].astype(float)

    return df


# ============================================================
# Portfolio DF API
# ============================================================

def get_portfolio_df() -> pd.DataFrame:
    """
    Load the portfolio from SES-Core via TFEPortfolioService.

    Behavior:
      - If SES-Core portfolio exists → return DF.
      - If NO portfolio exists → return EMPTY DF.
      - CSV is NOT touched.

    Any errors from SES-Core are allowed to propagate; they are
    considered critical configuration failures.
    """
    ctx = _get_ctx()
    try:
        payload = ctx.portfolio_service.load_portfolio(
            tenant_display_name=TENANT_DISPLAY_NAME,
            user_display_name=USER_DISPLAY_NAME,
            portfolio_id=PORTFOLIO_ID,
        )
        df = _payload_to_df(payload)
        return df
    except FileNotFoundError:
        # No SES-Core portfolio yet → start empty
        return pd.DataFrame(columns=["ticker", "quantity", "cost_basis", "asset_type"])
    except Exception as e:
        # Hard failure — better to surface than silently fallback to CSV.
        raise RuntimeError(f"Failed to load SES-Core portfolio: {e}") from e


def save_portfolio_df(df: pd.DataFrame) -> None:
    """
    Save the portfolio DF to SES-Core via TFEPortfolioService.

    This overwrites the existing portfolio for (tenant-tao, user-primary, default).
    """
    ctx = _get_ctx()
    payload = _df_to_payload(df)

    ctx.portfolio_service.create_or_update_portfolio(
        tenant_display_name=TENANT_DISPLAY_NAME,
        user_display_name=USER_DISPLAY_NAME,
        portfolio_id=PORTFOLIO_ID,
        portfolio_data=payload,
        label="Default Portfolio",
    )


# ============================================================
# Valuation API
# ============================================================

def get_portfolio_valuation() -> PortfolioValuation:
    """
    Compute portfolio valuation using live market data, based on
    the SES-Core–backed portfolio.
    """
    df = get_portfolio_df()
    return compute_portfolio_valuation(df)


def get_positions_valuation() -> List[PositionValuation]:
    """
    Return per-position valuations for the SES-Core–backed portfolio.
    """
    pv = get_portfolio_valuation()
    return pv.positions
