#!/usr/bin/env python3
"""
tfe_epoch_auto_severity.py
Auto-severity scoring for TFE epoch library.

Fetches live market indicators via yfinance and computes severity scores
for each named epoch. Caches results to a JSON file with a 6-hour TTL so
individual ticker evaluations don't make repeated network calls.

Epoch → Indicator mapping
─────────────────────────
WAR_GEOPOLITICS
  • VIX level            (fear/uncertainty proxy; >15 = elevated)
  • Crude oil vs 60d MA  (energy shock proxy; >20% above MA = high)
  • ITA vs SPY 20d rel.  (defense sector outperformance proxy)

RATES_PRESSURE
  • 10yr yield (^TNX)    (absolute rate level; 2%=low, 5%=high)
  • 2s10s spread inversion (^IRX vs ^TNX; inversion = pressure)
  • HYG vs LQD 20d rel.  (credit stress; HYG underperf = widening spreads)

CONSUMER_STRESS
  • XLY/XLP ratio 20d change (discretionary vs staples flight)
  • VIX (consumer fear component)

All scores are normalized 0.0–1.0 and blended to a single severity per epoch.
Fallback to hardcoded values if market data fetch fails.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict

import numpy as np
import yfinance as yf

# ── Cache ────────────────────────────────────────────────────────────────────
_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "epoch_live_severities.json")
_CACHE_TTL_HOURS = 6

# Hardcoded fallback — used if network unavailable
_FALLBACK_SEVERITIES: Dict[str, float] = {
    "WAR_GEOPOLITICS":  0.7,
    "RATES_PRESSURE":   0.8,
    "CONSUMER_STRESS":  0.6,
}

# ── Market data fetch ─────────────────────────────────────────────────────────
_TICKERS = ["^VIX", "CL=F", "^TNX", "^IRX", "HYG", "LQD", "XLY", "XLP", "ITA", "SPY"]


def _fetch_closes(period: str = "3mo") -> Dict[str, "np.ndarray"]:
    """Download closing prices for all indicators. Returns {ticker: array}."""
    raw = yf.download(
        _TICKERS,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    # yfinance returns MultiIndex columns when multiple tickers requested
    closes: Dict[str, np.ndarray] = {}
    if hasattr(raw.columns, "levels"):
        price_df = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
        for ticker in _TICKERS:
            if ticker in price_df.columns:
                arr = price_df[ticker].dropna().values
                if len(arr) > 0:
                    closes[ticker] = arr.astype(float)
    else:
        # Single ticker fallback (should not happen here)
        closes["^VIX"] = raw["Close"].dropna().values.astype(float)
    return closes


# ── Per-epoch scoring ─────────────────────────────────────────────────────────

def _score_war_geopolitics(closes: Dict[str, np.ndarray]) -> float:
    scores = []

    # VIX: 15 = baseline calm, 50 = extreme fear
    if "^VIX" in closes and len(closes["^VIX"]) > 0:
        vix = float(closes["^VIX"][-1])
        scores.append(float(np.clip((vix - 15.0) / 35.0, 0.0, 1.0)))

    # Crude oil: % above 60-day moving average
    if "CL=F" in closes and len(closes["CL=F"]) > 20:
        oil = closes["CL=F"]
        ma60 = float(np.mean(oil[-60:])) if len(oil) >= 60 else float(np.mean(oil))
        pct_above = (float(oil[-1]) - ma60) / max(ma60, 1.0)
        # 30% above 60d MA = severity 1.0; below MA = 0
        scores.append(float(np.clip(pct_above / 0.30, 0.0, 1.0)))

    # Defense sector (ITA) vs SPY 20-day relative return
    if "ITA" in closes and "SPY" in closes:
        ita, spy = closes["ITA"], closes["SPY"]
        if len(ita) > 20 and len(spy) > 20:
            ita_ret = float(ita[-1]) / float(ita[-20]) - 1.0
            spy_ret = float(spy[-1]) / float(spy[-20]) - 1.0
            rel = ita_ret - spy_ret
            # 15% outperformance = severity 1.0
            scores.append(float(np.clip(rel / 0.15, 0.0, 1.0)))

    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["WAR_GEOPOLITICS"]


def _score_rates_pressure(closes: Dict[str, np.ndarray]) -> float:
    scores = []

    # 10yr yield: 2% = low, 5% = high
    if "^TNX" in closes and len(closes["^TNX"]) > 0:
        tnx = float(closes["^TNX"][-1])
        scores.append(float(np.clip((tnx - 2.0) / 3.0, 0.0, 1.0)))

    # Yield curve: 2s10s spread — inversion = max pressure
    # ^IRX is the 3-month T-bill rate (quoted as annualised %)
    if "^IRX" in closes and "^TNX" in closes:
        irx = float(closes["^IRX"][-1])
        tnx = float(closes["^TNX"][-1])
        spread = tnx - irx  # negative = inverted
        # Inversion of -2pp = severity 1.0; positive spread = 0
        scores.append(float(np.clip(-spread / 2.0, 0.0, 1.0)))

    # HYG vs LQD 20-day relative return (credit stress)
    if "HYG" in closes and "LQD" in closes:
        hyg, lqd = closes["HYG"], closes["LQD"]
        if len(hyg) > 20 and len(lqd) > 20:
            hyg_ret = float(hyg[-1]) / float(hyg[-20]) - 1.0
            lqd_ret = float(lqd[-1]) / float(lqd[-20]) - 1.0
            # HYG underperforming LQD = credit widening
            spread_move = lqd_ret - hyg_ret
            # 5% spread widening = severity 1.0
            scores.append(float(np.clip(spread_move / 0.05, 0.0, 1.0)))

    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["RATES_PRESSURE"]


def _score_consumer_stress(closes: Dict[str, np.ndarray]) -> float:
    scores = []

    # XLY/XLP ratio 20-day change — declining = flight to staples = stress
    if "XLY" in closes and "XLP" in closes:
        xly, xlp = closes["XLY"], closes["XLP"]
        if len(xly) > 20 and len(xlp) > 20:
            ratio_now   = float(xly[-1])  / float(xlp[-1])
            ratio_20d   = float(xly[-20]) / float(xlp[-20])
            ratio_chg   = ratio_now / ratio_20d - 1.0
            # 10% decline in ratio = severity 1.0
            scores.append(float(np.clip(-ratio_chg / 0.10, 0.0, 1.0)))

    # VIX component (broad fear = consumer fear)
    if "^VIX" in closes and len(closes["^VIX"]) > 0:
        vix = float(closes["^VIX"][-1])
        scores.append(float(np.clip((vix - 15.0) / 25.0, 0.0, 1.0)))

    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["CONSUMER_STRESS"]


# ── Public API ────────────────────────────────────────────────────────────────

def compute_live_severities() -> Dict[str, float]:
    """Fetch market data and return computed epoch severity dict."""
    try:
        closes = _fetch_closes(period="3mo")
        severities = {
            "WAR_GEOPOLITICS":  _score_war_geopolitics(closes),
            "RATES_PRESSURE":   _score_rates_pressure(closes),
            "CONSUMER_STRESS":  _score_consumer_stress(closes),
        }
        print(f"[EPOCH-AUTO] Live severities computed: {severities}")
        return severities
    except Exception as exc:
        print(f"[EPOCH-AUTO] Market fetch failed ({exc}) — using fallback severities")
        return dict(_FALLBACK_SEVERITIES)


def refresh_and_cache() -> Dict[str, float]:
    """Compute severities and write to cache file. Returns severity dict."""
    severities = compute_live_severities()
    try:
        with open(_CACHE_PATH, "w") as fh:
            json.dump({"computed_at": datetime.utcnow().isoformat(), "severities": severities}, fh, indent=2)
    except Exception as exc:
        print(f"[EPOCH-AUTO] Cache write failed: {exc}")
    return severities


def load_live_epochs() -> Dict[str, float]:
    """
    Return live epoch severities.
    Reads from cache file if age < TTL, otherwise recomputes and caches.
    Falls back to hardcoded values if everything fails.
    """
    try:
        with open(_CACHE_PATH) as fh:
            cached = json.load(fh)
        computed_at = datetime.fromisoformat(cached["computed_at"])
        age_hours = (datetime.utcnow() - computed_at).total_seconds() / 3600.0
        if age_hours < _CACHE_TTL_HOURS:
            sevs = cached["severities"]
            print(f"[EPOCH-AUTO] Using cached severities (age={age_hours:.1f}h): {sevs}")
            return sevs
    except (FileNotFoundError, KeyError, ValueError):
        pass
    # Cache missing or stale — recompute
    return refresh_and_cache()


if __name__ == "__main__":
    result = refresh_and_cache()
    print("Epoch severities:", result)
