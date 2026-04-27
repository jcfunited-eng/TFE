#!/usr/bin/env python3
"""
tfe_epoch_auto_severity.py
Auto-severity scoring for TFE epoch library.

Fetches live market indicators via yfinance and computes severity scores
for each named epoch channel. Caches results to JSON with 6-hour TTL.

8 Active Channels (of 32 in spec):
─────────────────────────────────
RATES_PRESSURE      — 10yr yield, 2s10s spread, credit stress (HYG/LQD)
CONSUMER_STRESS     — XLY/XLP rotation, VIX
WAR_GEOPOLITICS     — VIX, crude oil, defense sector (ITA) outperformance
ENERGY_COMMODITY    — crude oil vs MA, natural gas vs MA, XLE vs SPY
TECH_CYCLE          — semiconductor (SOXX) vs SPY, QQQ vs SPY
CURRENCY_FX         — dollar index (UUP), emerging markets (EEM) vs SPY
FISCAL_INFRA        — infrastructure ETF (PAVE) vs SPY, industrials (XLI)
VOLATILITY_REGIME   — VIX level, VIX term structure (VIX vs VIX3M proxy)

All scores normalized 0.0–1.0. No ML. Deterministic from market data.
Fallback to defaults if fetch fails.
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
    "RATES_PRESSURE":    0.5,
    "CONSUMER_STRESS":   0.3,
    "WAR_GEOPOLITICS":   0.3,
    "ENERGY_COMMODITY":  0.3,
    "TECH_CYCLE":        0.3,
    "CURRENCY_FX":       0.3,
    "FISCAL_INFRA":      0.3,
    "VOLATILITY_REGIME": 0.3,
}

# ── Market data fetch ─────────────────────────────────────────────────────────
_TICKERS = [
    # Original 3 channels
    "^VIX", "CL=F", "^TNX", "^IRX", "HYG", "LQD", "XLY", "XLP", "ITA", "SPY",
    # New channels
    "NG=F",     # natural gas futures
    "XLE",      # energy sector ETF
    "SOXX",     # semiconductor index
    "QQQ",      # tech-heavy Nasdaq
    "UUP",      # dollar index ETF
    "EEM",      # emerging markets ETF
    "PAVE",     # infrastructure ETF
    "XLI",      # industrials ETF
]


def _fetch_closes(period: str = "3mo") -> Dict[str, "np.ndarray"]:
    """Download closing prices for all indicators. Returns {ticker: array}."""
    raw = yf.download(
        _TICKERS,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    closes: Dict[str, np.ndarray] = {}
    if hasattr(raw.columns, "levels"):
        price_df = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
        for ticker in _TICKERS:
            if ticker in price_df.columns:
                arr = price_df[ticker].dropna().values
                if len(arr) > 0:
                    closes[ticker] = arr.astype(float)
    else:
        closes["^VIX"] = raw["Close"].dropna().values.astype(float)
    return closes


def _relative_return(closes, ticker_a, ticker_b, days=20):
    """Compute relative return of A vs B over N days."""
    if ticker_a not in closes or ticker_b not in closes:
        return None
    a, b = closes[ticker_a], closes[ticker_b]
    if len(a) <= days or len(b) <= days:
        return None
    a_ret = float(a[-1]) / float(a[-days]) - 1.0
    b_ret = float(b[-1]) / float(b[-days]) - 1.0
    return a_ret - b_ret


def _pct_above_ma(closes, ticker, ma_days=60):
    """Compute how far price is above its moving average."""
    if ticker not in closes:
        return None
    arr = closes[ticker]
    if len(arr) < ma_days:
        return None
    ma = float(np.mean(arr[-ma_days:]))
    if ma <= 0:
        return None
    return (float(arr[-1]) - ma) / ma


# ── Per-epoch scoring ─────────────────────────────────────────────────────────

def _score_war_geopolitics(closes: Dict[str, np.ndarray]) -> float:
    scores = []
    if "^VIX" in closes and len(closes["^VIX"]) > 0:
        vix = float(closes["^VIX"][-1])
        scores.append(float(np.clip((vix - 15.0) / 35.0, 0.0, 1.0)))
    pct = _pct_above_ma(closes, "CL=F", 60)
    if pct is not None:
        scores.append(float(np.clip(pct / 0.30, 0.0, 1.0)))
    rel = _relative_return(closes, "ITA", "SPY", 20)
    if rel is not None:
        scores.append(float(np.clip(rel / 0.15, 0.0, 1.0)))
    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["WAR_GEOPOLITICS"]


def _score_rates_pressure(closes: Dict[str, np.ndarray]) -> float:
    scores = []
    if "^TNX" in closes and len(closes["^TNX"]) > 0:
        tnx = float(closes["^TNX"][-1])
        scores.append(float(np.clip((tnx - 2.0) / 3.0, 0.0, 1.0)))
    if "^IRX" in closes and "^TNX" in closes:
        irx = float(closes["^IRX"][-1])
        tnx = float(closes["^TNX"][-1])
        spread = tnx - irx
        scores.append(float(np.clip(-spread / 2.0, 0.0, 1.0)))
    if "HYG" in closes and "LQD" in closes:
        hyg, lqd = closes["HYG"], closes["LQD"]
        if len(hyg) > 20 and len(lqd) > 20:
            hyg_ret = float(hyg[-1]) / float(hyg[-20]) - 1.0
            lqd_ret = float(lqd[-1]) / float(lqd[-20]) - 1.0
            scores.append(float(np.clip((lqd_ret - hyg_ret) / 0.05, 0.0, 1.0)))
    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["RATES_PRESSURE"]


def _score_consumer_stress(closes: Dict[str, np.ndarray]) -> float:
    scores = []
    if "XLY" in closes and "XLP" in closes:
        xly, xlp = closes["XLY"], closes["XLP"]
        if len(xly) > 20 and len(xlp) > 20:
            ratio_now = float(xly[-1]) / float(xlp[-1])
            ratio_20d = float(xly[-20]) / float(xlp[-20])
            ratio_chg = ratio_now / ratio_20d - 1.0
            scores.append(float(np.clip(-ratio_chg / 0.10, 0.0, 1.0)))
    if "^VIX" in closes and len(closes["^VIX"]) > 0:
        vix = float(closes["^VIX"][-1])
        scores.append(float(np.clip((vix - 15.0) / 25.0, 0.0, 1.0)))
    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["CONSUMER_STRESS"]


def _score_energy_commodity(closes: Dict[str, np.ndarray]) -> float:
    """Energy/commodity input cost pressure.
    High crude + high nat gas + energy sector outperforming = commodity stress for consumers.
    """
    scores = []
    # Crude oil vs 60d MA
    pct = _pct_above_ma(closes, "CL=F", 60)
    if pct is not None:
        scores.append(float(np.clip(pct / 0.25, 0.0, 1.0)))
    # Natural gas vs 60d MA
    pct_ng = _pct_above_ma(closes, "NG=F", 60)
    if pct_ng is not None:
        scores.append(float(np.clip(pct_ng / 0.40, 0.0, 1.0)))
    # XLE (energy) vs SPY — energy outperformance = commodity pressure
    rel = _relative_return(closes, "XLE", "SPY", 20)
    if rel is not None:
        scores.append(float(np.clip(rel / 0.10, 0.0, 1.0)))
    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["ENERGY_COMMODITY"]


def _score_tech_cycle(closes: Dict[str, np.ndarray]) -> float:
    """Tech sector cycle stress.
    Semiconductors underperforming + QQQ underperforming SPY = tech rotation out.
    Inverted: SOXX outperforming = tech strength (low stress).
    """
    scores = []
    # SOXX vs SPY — semiconductor underperformance = tech stress
    rel_soxx = _relative_return(closes, "SOXX", "SPY", 20)
    if rel_soxx is not None:
        # Negative relative = stress (tech falling behind)
        scores.append(float(np.clip(-rel_soxx / 0.15, 0.0, 1.0)))
    # QQQ vs SPY — tech-heavy underperformance
    rel_qqq = _relative_return(closes, "QQQ", "SPY", 20)
    if rel_qqq is not None:
        scores.append(float(np.clip(-rel_qqq / 0.10, 0.0, 1.0)))
    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["TECH_CYCLE"]


def _score_currency_fx(closes: Dict[str, np.ndarray]) -> float:
    """Currency/FX stress.
    Strong dollar (UUP rising) = pressure on multinationals, EM stress.
    EEM underperforming SPY = emerging market stress from dollar/rates.
    """
    scores = []
    # Dollar strength: UUP 20d return
    if "UUP" in closes and len(closes["UUP"]) > 20:
        uup = closes["UUP"]
        uup_ret = float(uup[-1]) / float(uup[-20]) - 1.0
        # 5% dollar appreciation in 20d = max stress
        scores.append(float(np.clip(uup_ret / 0.05, 0.0, 1.0)))
    # EM underperformance
    rel_eem = _relative_return(closes, "EEM", "SPY", 20)
    if rel_eem is not None:
        # EM underperforming SPY = FX stress
        scores.append(float(np.clip(-rel_eem / 0.10, 0.0, 1.0)))
    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["CURRENCY_FX"]


def _score_fiscal_infra(closes: Dict[str, np.ndarray]) -> float:
    """Fiscal/infrastructure spending signal.
    PAVE (infrastructure) and XLI (industrials) outperforming = fiscal tailwind.
    This is a POSITIVE epoch — high severity means infrastructure is hot.
    """
    scores = []
    rel_pave = _relative_return(closes, "PAVE", "SPY", 20)
    if rel_pave is not None:
        # Infrastructure outperforming = fiscal support active
        scores.append(float(np.clip(rel_pave / 0.10, 0.0, 1.0)))
    rel_xli = _relative_return(closes, "XLI", "SPY", 20)
    if rel_xli is not None:
        scores.append(float(np.clip(rel_xli / 0.08, 0.0, 1.0)))
    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["FISCAL_INFRA"]


def _score_volatility_regime(closes: Dict[str, np.ndarray]) -> float:
    """Volatility regime.
    VIX level + VIX acceleration (is fear increasing?).
    High and rising VIX = stressed volatility regime.
    """
    scores = []
    if "^VIX" in closes and len(closes["^VIX"]) > 20:
        vix_arr = closes["^VIX"]
        vix_now = float(vix_arr[-1])
        vix_20d = float(np.mean(vix_arr[-20:]))
        # Absolute level: 15 = calm, 40 = panic
        scores.append(float(np.clip((vix_now - 15.0) / 25.0, 0.0, 1.0)))
        # Acceleration: VIX rising above its own 20d average
        vix_accel = (vix_now - vix_20d) / max(vix_20d, 1.0)
        scores.append(float(np.clip(vix_accel / 0.30, 0.0, 1.0)))
    return round(float(np.mean(scores)), 3) if scores else _FALLBACK_SEVERITIES["VOLATILITY_REGIME"]


# ── Public API ────────────────────────────────────────────────────────────────

def compute_live_severities() -> Dict[str, float]:
    """Fetch market data and return computed epoch severity dict."""
    try:
        closes = _fetch_closes(period="3mo")
        severities = {
            "RATES_PRESSURE":    _score_rates_pressure(closes),
            "CONSUMER_STRESS":   _score_consumer_stress(closes),
            "WAR_GEOPOLITICS":   _score_war_geopolitics(closes),
            "ENERGY_COMMODITY":  _score_energy_commodity(closes),
            "TECH_CYCLE":        _score_tech_cycle(closes),
            "CURRENCY_FX":       _score_currency_fx(closes),
            "FISCAL_INFRA":      _score_fiscal_infra(closes),
            "VOLATILITY_REGIME": _score_volatility_regime(closes),
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
