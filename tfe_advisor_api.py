#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from tfe_epoch_library import EpochCorpora
from tfe_fundamental_fetcher import FundamentalCorpora
from tfe_l5_baseline import apply_canonical_filter


STRUCTURAL_PROXY_THRESHOLD = 0.6466
SIC_TO_MACRO_MAP = {
    "SERVICES-BUSINESS SERVICES, NEC": "Information Technology",
}


def _is_structural_proxy(df_history: pd.DataFrame) -> bool:
    return len(df_history) == 1 and "S_UF" in df_history.columns


def _normalize_epoch_sector(sector: str) -> str:
    normalized = str(sector or "Unknown").strip() or "Unknown"
    return SIC_TO_MACRO_MAP.get(normalized, normalized)


def get_tfe_recommendation(ticker: str, sector: str, df_history: pd.DataFrame) -> Dict[str, Any]:
    if df_history.empty:
        return {"action": "Hold", "reason": "Empty history provided."}

    if _is_structural_proxy(df_history):
        s_uf = float(df_history.iloc[0]["S_UF"])
        is_current_breakout = s_uf >= STRUCTURAL_PROXY_THRESHOLD
    else:
        try:
            surviving_rows = apply_canonical_filter(df_history)
        except Exception as exc:
            return {"action": "Hold", "reason": f"Structural baseline unavailable: {exc}"}
        latest_index = df_history.index[-1]
        is_current_breakout = (not surviving_rows.empty) and (latest_index in surviving_rows.index)

    if not is_current_breakout:
        return {"action": "Hold", "reason": "No structurally coherent geometric breakout detected."}

    try:
        fundamental_result = FundamentalCorpora().evaluate_ticker(ticker, sector_hint=sector)
    except Exception as exc:
        return {"action": "Hold", "reason": f"Fundamental evaluation unavailable: {exc}"}

    resolved_sector = str(fundamental_result.get("sector") or sector or "Unknown")
    epoch_sector = _normalize_epoch_sector(resolved_sector)

    if fundamental_result.get("status") == "FAIL":
        return {
            "action": "Avoid",
            "reason": str(fundamental_result.get("reason")),
            "sector": epoch_sector,
        }

    try:
        epoch_result = EpochCorpora().evaluate_sector_epoch(epoch_sector)
    except Exception as exc:
        return {"action": "Avoid", "reason": f"Epoch evaluation unavailable: {exc}", "sector": epoch_sector}

    if epoch_result.get("status") == "FAIL":
        return {"action": "Avoid", "reason": str(epoch_result.get("reason")), "sector": epoch_sector}

    return {
        "action": "Accumulate",
        "reason": "Passed Geometric Baseline, Fundamental Triad, and Epoch Constraints.",
        "sector": epoch_sector,
    }
