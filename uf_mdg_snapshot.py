#!/usr/bin/env python3
"""
UF-Core MDG Snapshot Evaluator

Purpose
-------
Single place that turns:
    (symbol, recent market history)
into one UF snapshot row that matches the active snapshot row schema
schema used by TFE pages (Recommendations, etc.).

This module:
    - Uses UF-Core structural engine only (no TA).
    - Uses the same structural adapter as Watchlist / live views.
    - Materializes structural recency fields from published decision lineage.
    - Computes CP-2 cognitive scalars (F_n, raw_x_m) from close bar history
      using the deterministic quarantine kernel physics.
    - Returns a dict with keys:
        ticker, asset_type, price, regime,
        S_UF, R_UF, stability_score, max_dd,
        decision_vector, D_k, M_k, R_rev_k, U_star_k, C_k, prev_C_k, P_k, B_k,
        bar_count, F_n, raw_x_m

Intended usage
--------------
Typical integration point is the snapshot rebuild path (e.g. refresh_snapshot_full):

    from uf_mdg_snapshot import evaluate_symbol_snapshot

    row = evaluate_symbol_snapshot("AAPL", asset_type="stock")
    # collect rows and write snapshot envelope payload rows

This file does NOT know anything about Streamlit or UI.
It is purely a governance-aware structural snapshot builder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ----------------------------------------------------------------------
# Data layer imports
# ----------------------------------------------------------------------
# We follow the same pattern as the other TFE scripts:
# - Prefer tfe_market_data if present.
# - Fallback to unified_market_data_service if this is run standalone.

try:
    # TFE-local wrapper (used by Portfolio, Watchlist, etc.)
    from tfe_market_data import get_unified_market_data  # type: ignore
except ModuleNotFoundError:
    # Direct UF/TFE data service
    from unified_market_data_service import get_unified_market_data  # type: ignore

from structural_recency_snapshot import (
    build_structural_recency_payload,
    history_metadata_from_bars,
)
from tfe_bar_integrity import DEFAULT_MIN_PRICE_FLOOR, sanitize_daily_bars
from tfe_market_data_service import Bar, HistoryRequest, Timespan  # type: ignore

# ----------------------------------------------------------------------
# UF-Core structural engine import
# ----------------------------------------------------------------------
# Same adapter used by Watchlist and other TFE pages.

try:
    # Package-style import
    from uf_core.uf_structural_engine import compute_structural_state  # type: ignore
except ModuleNotFoundError:
    # Flat module-style import
    from uf_structural_engine import compute_structural_state  # type: ignore


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# How much history we give UF-Core for a snapshot evaluation.
YEARS_HISTORY: int = 5

# Production policy evidence floor:
# decision layer requires this many daily bars before allowing Accumulate.
ACCUMULATE_MIN_BARS: int = 514
RECENT_BAR_LOOKBACK_DAYS: int = 10

# Strict OHLC integrity floor used by production ingestion.
MIN_PRICE_FLOOR: float = DEFAULT_MIN_PRICE_FLOOR


# ===========================================================================
# CP-2: Cognitive Kernel — Deterministic physics for F_n and raw_x_m
#
# Ported verbatim from quarantine_historical_kernel.py.
# No pyarrow. No quarantine module imports. Pure numpy/dataclass.
# Constants are frozen from KernelParameters defaults.
# ===========================================================================

# ---------------------------------------------------------------------------
# Frozen kernel constants (KernelParameters defaults)
# ---------------------------------------------------------------------------
_KP_W: int = 20
_KP_W_r: int = 10
_KP_sigma_min: float = 1e-6
_KP_delta_min: float = 1e-6
_KP_kappa_min: float = 1e-6
_KP_tau_D: float = 0.20
_KP_alpha_1: float = 1.0
_KP_alpha_2: float = 1.0
_KP_alpha_3: float = 1.0
_KP_beta_1: float = 1.0
_KP_beta_2: float = 1.0
_KP_beta_3: float = 1.0
_KP_lattices: List[Tuple[float, float, float]] = [(1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (4.0, 4.0, 4.0)]
_KP_lambda_1: float = 1.0
_KP_lambda_2: float = 1.0
_KP_lambda_3: float = 1.0
_KP_lambda_4: float = 1.0
_KP_lambda_5: float = 1.0
_KP_h_max: float = 0.20
_KP_U_max: float = 0.75
_KP_eps_D: float = 0.00073
_KP_eta_H: float = 0.10
_KP_eta_IAS: float = 0.10
_KP_xi: float = 0.10
_KP_chi: float = 0.10
_KP_B_min: float = -1.0
_KP_B_max: float = 1.0
_KP_a_rho: float = 0.4
_KP_b_rho: float = 0.4
_KP_c_rho: float = 0.1
_KP_d_rho: float = 0.1
_KP_a_decay: float = 0.99
_KP_a_nu_weight: float = 0.05
_KP_a_pi_weight: float = 0.05
_KP_A_f: float = 0.90
_KP_A_m: float = 0.98
_KP_A_s: float = 0.995
_KP_B_f: float = 0.1
_KP_B_m: float = 0.1
_KP_B_s: float = 0.1
_KP_H_mf: float = 0.1
_KP_H_sm: float = 0.1
_KP_G_all: float = 0.01
_KP_L_f: float = 0.01
_KP_L_m: float = 0.01
_KP_L_s: float = 0.01
_KP_lambda_s: float = 1.0
_KP_eta_h: float = 2.0
_KP_EPS_TAU_DAYS: float = 1.0
_KP_RHO_ROLLING_WINDOW: int = 5
_KP_R_NORM_MAX: float = 1.0
_KP_Z: float = _KP_lambda_1 + _KP_lambda_2 + _KP_lambda_3 + _KP_lambda_4 + _KP_lambda_5


# ---------------------------------------------------------------------------
# L0 SEV
# ---------------------------------------------------------------------------

@dataclass
class _SEV:
    F: float
    dF: float
    sigma: float
    kappa: float
    r: float
    N: int


def _psi_r(F_window: np.ndarray) -> float:
    return 1.0 if len(F_window) > 0 and F_window[-1] > np.mean(F_window) else 0.5


def _compute_l0_sev(F: np.ndarray) -> List[_SEV]:
    n = len(F)
    sevs: List[_SEV] = []
    for t in range(n):
        dF = F[t] - F[t - 1] if t > 0 else 0.0
        start_w = max(0, t - _KP_W + 1)
        F_window = F[start_w : t + 1]
        F_bar = np.mean(F_window)
        sigma = float(np.mean((F_window - F_bar) ** 2))
        if 0 < t < n - 1:
            kappa = abs(float(F[t + 1]) - 2.0 * float(F[t]) + float(F[t - 1]))
        else:
            kappa = 0.0
        start_r = max(0, t - _KP_W_r + 1)
        r_val = _psi_r(F[start_r : t + 1])
        N = 1 if (sigma < _KP_sigma_min and abs(dF) < _KP_delta_min and kappa < _KP_kappa_min) else 0
        sevs.append(_SEV(float(F[t]), float(dF), sigma, kappa, r_val, N))
    return sevs


# ---------------------------------------------------------------------------
# L1 Gate segmentation
# ---------------------------------------------------------------------------

@dataclass
class _GateL1:
    t_a: int
    t_b: int
    TVR: Tuple[float, float, float]
    P_list: List[Tuple[int, int, int]]
    C: int
    delta_g: float
    mu: np.ndarray
    N_gate: int


def _segment_l1_gates(sevs: List[_SEV]) -> List[_GateL1]:
    D = np.zeros(len(sevs))
    for t, sev in enumerate(sevs):
        D[t] = _KP_alpha_1 * abs(sev.dF) + _KP_alpha_2 * sev.sigma + _KP_alpha_3 * sev.kappa

    gates: List[_GateL1] = []
    t_a = 0
    last_mu = np.zeros(3)
    for t in range(1, len(sevs)):
        if D[t] >= _KP_tau_D or t == len(sevs) - 1:
            t_b = t
            gate_sevs = sevs[t_a:t_b]
            if not gate_sevs:
                t_a = t
                continue
            T = float(t_b - t_a)
            V = sum(_KP_beta_1 * abs(s.dF) + _KP_beta_2 * s.sigma + _KP_beta_3 * s.kappa for s in gate_sevs)
            R = sum(s.r for s in gate_sevs)
            TVR = (T, V, R)
            P_list: List[Tuple[int, int, int]] = []
            for h1, h2, h3 in _KP_lattices:
                P_list.append((int(T // h1), int(V // h2), int(R // h3)))
            C = len(set(P_list))
            mu_k = np.array(
                [
                    np.mean([s.dF for s in gate_sevs]),
                    np.mean([s.sigma for s in gate_sevs]),
                    np.mean([s.kappa for s in gate_sevs]),
                ]
            )
            delta_g = float(np.linalg.norm(mu_k - last_mu))
            N_gate = 1 if all(s.N == 1 for s in gate_sevs) else 0
            gates.append(_GateL1(t_a, t_b, TVR, P_list, C, delta_g, mu_k, N_gate))
            last_mu = mu_k
            t_a = t
    return gates


# ---------------------------------------------------------------------------
# L2 ISF
# ---------------------------------------------------------------------------

@dataclass
class _ISF:
    gate: _GateL1
    w: float
    CV: np.ndarray
    S: float
    U: float
    IAS: int


def _compute_l2_isf(gates: List[_GateL1]) -> List[_ISF]:
    if not gates:
        return []
    V_max = max((g.TVR[1] for g in gates), default=1e-12)
    V_max = V_max if V_max > 0 else 1e-12
    isfs: List[_ISF] = []
    for g in gates:
        w_k = g.TVR[1] / V_max
        CV_k = np.array(g.TVR) - g.mu
        S_k = float(np.clip(1.0 / (1.0 + g.C + g.delta_g), 0.0, 1.0))
        U_k = float(np.clip((g.C * 0.1) + (g.delta_g * 0.1) + (g.N_gate * 0.2), 0.0, 1.0))
        IAS_k = 1 if U_k > 0.8 or g.delta_g > 2.0 else 0
        isfs.append(_ISF(g, w_k, CV_k, S_k, U_k, IAS_k))
    return isfs


# ---------------------------------------------------------------------------
# L3 Resonance
# ---------------------------------------------------------------------------

@dataclass
class _Resonance:
    isf: _ISF
    R: float
    Hyst: int
    g: int
    URF: float


def _compute_l3_resonance(isfs: List[_ISF]) -> List[_Resonance]:
    if not isfs:
        return []
    CV_max = max((np.linalg.norm(isf.CV) for isf in isfs), default=1e-12)
    CV_max = CV_max if CV_max > 0 else 1e-12
    res: List[_Resonance] = []
    last_R = 0.0
    for isf in isfs:
        term1 = _KP_lambda_1 * isf.w
        term2 = _KP_lambda_2 * (float(np.linalg.norm(isf.CV)) / CV_max)
        term3 = _KP_lambda_3 * isf.S
        term4 = _KP_lambda_4 * (1.0 / (1.0 + isf.gate.C))
        term5 = _KP_lambda_5 * (1.0 - isf.U)
        R_k = (1.0 / _KP_Z) * (term1 + term2 + term3 + term4 + term5)
        Hyst_k = 1 if abs(R_k - last_R) > _KP_h_max else 0
        g_k = 1 if (isf.U <= _KP_U_max and isf.IAS == 0 and Hyst_k == 0) else 0
        URF_k = g_k * R_k
        res.append(_Resonance(isf, R_k, Hyst_k, g_k, URF_k))
        last_R = R_k
    return res


# ---------------------------------------------------------------------------
# L4 DSF
# ---------------------------------------------------------------------------

@dataclass
class _DSFState:
    D: int
    M: float
    Rev: int
    U_star: float
    B: float


def _compute_l4_dsf(res: List[_Resonance]) -> List[_DSFState]:
    dsfs: List[_DSFState] = []
    last_URF = 0.0
    last_URF2 = 0.0
    last_D = 0
    last_B = 0.0
    for r in res:
        delta_R = r.URF - last_URF
        if delta_R > _KP_eps_D:
            D_k = 1
        elif delta_R < -_KP_eps_D:
            D_k = -1
        else:
            D_k = 0
        M_k = r.URF - 2.0 * last_URF + last_URF2
        U_star_k = r.isf.U + (_KP_eta_H * r.Hyst) + (_KP_eta_IAS * r.isf.IAS)
        B_k_raw = last_B + _KP_xi * (1.0 - U_star_k) * delta_R - _KP_chi * U_star_k
        B_k = float(np.clip(B_k_raw, _KP_B_min, _KP_B_max))
        dsfs.append(_DSFState(D_k, M_k, 1 if (D_k * last_D < 0) else 0, U_star_k, B_k))
        last_URF2 = last_URF
        last_URF = r.URF
        last_D = D_k
        last_B = B_k
    return dsfs


# ---------------------------------------------------------------------------
# CV-1.0 cognitive scalars — compute the latest F_n and raw_x_m from bars
# ---------------------------------------------------------------------------

def compute_cognitive_scalars(
    close_prices: np.ndarray,
    max_bars: int = 252,
) -> Dict[str, Optional[float]]:
    """
    Run the full L0→L4 + CV-1.0 kernel on close_prices and return the final
    gate's F_n and raw_x_m.

    Returns {"F_n": float, "raw_x_m": float} on success, or
    {"F_n": None, "raw_x_m": None} when insufficient data or any error.

    raw_x_m = Q_20 + 2.0 * F_n  (verified from quarantine_sequential_filter.py)
    Q_20 = x_m - eta_h * F_n  (q_20 = [0, 1, 0] so dot(q_20, z_n) = x_m)
    => raw_x_m = x_m - 2.0 * F_n + 2.0 * F_n = x_m

    max_bars: cap the input to the most recent N bars before running the
    kernel. The CV-1.0 integrators (especially x_m with A_m=0.98) saturate
    at the clip boundary when fed 5-year history, making raw_x_m useless as
    a discriminator. 252 bars (~1 year) is enough warm-up to settle state
    without saturation.
    """
    _null: Dict[str, Optional[float]] = {"F_n": None, "raw_x_m": None, "s_n": None}

    try:
        F = close_prices.astype(float)
        if max_bars > 0 and len(F) > max_bars:
            F = F[-max_bars:]
        if len(F) < 2:
            return _null

        sevs = _compute_l0_sev(F)
        gates = _segment_l1_gates(sevs)
        if not gates:
            return _null

        isfs = _compute_l2_isf(gates)
        resonances = _compute_l3_resonance(isfs)
        dsfs = _compute_l4_dsf(resonances)

        if not resonances or not dsfs:
            return _null

        # CV-1.0 stateful forward pass — accumulate to the last gate
        a_state = np.zeros(3, dtype=float)
        x_f = 0.0
        x_m = 0.0
        x_s = 0.0
        r_history: List[float] = []
        u_history: List[float] = []
        c_history: List[float] = []  # gate complexity history — required for s_n via rho

        F_n_last: Optional[float] = None
        raw_x_m_last: Optional[float] = None
        s_n_last: Optional[float] = None

        for resonance, dsf in zip(resonances, dsfs):
            r_norm = float(np.clip(resonance.R / _KP_R_NORM_MAX, -1.0, 1.0))
            s_value = 1.0  # s_uf_default
            u_value = float(np.clip(dsf.U_star, 0.0, 1.0))
            # c_norm: gate complexity (C_k) normalised to [0, 1].
            # Consumed by C_bar → rho → z_n → s_n.
            # Reference: quarantine_historical_kernel.py line 353:
            #   c_norm = float(np.clip(dsf.C / 4.0, 0.0, 1.0))
            # where dsf.C == gate.C (complexity count from L1 lattice quantization).
            c_norm = float(np.clip(resonance.isf.gate.C / 4.0, 0.0, 1.0))

            r_history.append(r_norm)
            u_history.append(u_value)
            c_history.append(c_norm)

            R_bar = float(np.mean(r_history[-_KP_RHO_ROLLING_WINDOW:]))
            S_bar = s_value
            U_bar = float(np.mean(u_history[-_KP_RHO_ROLLING_WINDOW:]))
            C_bar = float(np.mean(c_history[-_KP_RHO_ROLLING_WINDOW:]))
            rho = float(np.clip(
                (_KP_a_rho * R_bar) + (_KP_b_rho * S_bar) - (_KP_c_rho * U_bar) - (_KP_d_rho * C_bar),
                0.0, 1.0,
            ))

            nu_core = np.clip(
                np.array([float(dsf.D), float(dsf.M), r_norm], dtype=float),
                -1.0, 1.0,
            )
            pi_vec = np.full(3, rho, dtype=float)

            a_state = np.clip(
                (_KP_a_decay * a_state) + (_KP_a_nu_weight * nu_core) + (_KP_a_pi_weight * pi_vec),
                -1.0, 1.0,
            )

            x_f = float(np.clip(
                (_KP_A_f * x_f) + (_KP_B_f * nu_core[0]) + (_KP_G_all * rho) + (_KP_L_f * a_state[0]),
                -1.0, 1.0,
            ))
            x_m = float(np.clip(
                (_KP_A_m * x_m) + (_KP_B_m * nu_core[1]) + (_KP_H_mf * x_f) + (_KP_G_all * rho) + (_KP_L_m * a_state[1]),
                -1.0, 1.0,
            ))
            x_s = float(np.clip(
                (_KP_A_s * x_s) + (_KP_B_s * nu_core[2]) + (_KP_H_sm * x_m) + (_KP_G_all * rho) + (_KP_L_s * a_state[2]),
                -1.0, 1.0,
            ))

            z_n = np.array([x_f, x_m, x_s], dtype=float)
            surprise = float(np.linalg.norm(nu_core - z_n))
            gamma = float(0.5 * (u_value + (1.0 - rho)))
            F_n_val = float(gamma + (_KP_lambda_s * surprise))
            Q_20_val = float(x_m - (_KP_eta_h * F_n_val))
            raw_x_m_val = float(Q_20_val + 2.0 * F_n_val)  # = x_m

            F_n_last = F_n_val
            raw_x_m_last = raw_x_m_val
            s_n_last = surprise  # raw L2 norm — no clip, no norm, no smoothing

        if F_n_last is None:
            return _null

        return {"F_n": F_n_last, "raw_x_m": raw_x_m_last, "s_n": s_n_last}

    except Exception:
        return _null


# ===========================================================================
# End of CP-2 cognitive kernel
# ===========================================================================


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------

def _fetch_history(
    symbol: str,
    years: int = YEARS_HISTORY,
    client: Optional[Any] = None,
    _bar_cache_conn=None,
) -> Tuple[List[Bar], Dict[str, int]]:
    """
    Fetch daily OHLCV bars for `symbol`, using the persistent bar cache.

    Strategy:
    1. Read cached bars from Postgres (daily_bars table).
    2. If cached data exists, fetch only the delta (bars after the latest
       cached date) from the API.
    3. If no cached data, fetch full history from the API (first run only).
    4. Write any new API bars to the cache for next time.
    5. Apply bar integrity filter and return.

    This reduces a typical daily refresh from ~6,000 full-history API calls
    to ~6,000 single-day delta fetches (or zero if bars are already current).
    """
    if client is None:
        client = get_unified_market_data()

    # ── Step 1: Read from bar cache ──────────────────────────────────────
    cached_bars: List[Bar] = []
    cache_available = False
    try:
        from bar_cache import read_cached_bars, get_latest_bar_date, write_bars, ensure_schema
        if _bar_cache_conn is not None:
            ensure_schema(_bar_cache_conn)
        cached_bars = read_cached_bars(symbol, conn=_bar_cache_conn)
        cache_available = True
    except Exception:
        # Cache not available (table doesn't exist yet, DB not reachable, etc.)
        # Fall through to full API fetch
        pass

    # ── Step 2: Determine what to fetch from API ─────────────────────────
    end = datetime.now(timezone.utc)
    if cached_bars:
        # Fetch only bars after the latest cached date (delta)
        latest_cached = max(b.timestamp for b in cached_bars)
        # Start from the day after the latest cached bar
        start = latest_cached + timedelta(days=1)
        if start >= end:
            # Cache is already current — no API call needed
            return _finalize_bars(cached_bars), {}
    else:
        # No cache — full history fetch
        start = end - timedelta(days=years * 365)

    # ── Step 3: Fetch delta (or full) from API ───────────────────────────
    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=True,
        limit=None,
    )

    result = client.get_history(req)
    raw_bars: List[Bar] = getattr(result, "bars", []) or []

    # Fallback: if Polygon returned nothing and we have no cache, try yfinance
    if not raw_bars and not cached_bars:
        try:
            import yfinance as yf
            yf_data = yf.download(
                symbol, start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                auto_adjust=True, progress=False,
            )
            if yf_data is not None and not yf_data.empty:
                for idx_date, row in yf_data.iterrows():
                    try:
                        ts = datetime(idx_date.year, idx_date.month, idx_date.day,
                                      tzinfo=None)
                        raw_bars.append(Bar(
                            timestamp=ts,
                            open=float(row.get("Open", row.get("Close", 0))),
                            high=float(row.get("High", row.get("Close", 0))),
                            low=float(row.get("Low", row.get("Close", 0))),
                            close=float(row["Close"]),
                            volume=float(row.get("Volume", 0)),
                        ))
                    except Exception:
                        continue
                if raw_bars:
                    print(f"[UF-SNAPSHOT] {symbol}: yfinance fallback provided {len(raw_bars)} bars")
        except Exception:
            pass  # yfinance unavailable — continue with empty bars

    cleaned_bars, dropped = sanitize_daily_bars(raw_bars, min_price_floor=MIN_PRICE_FLOOR)

    # ── Step 4: Write new bars to cache ──────────────────────────────────
    if cache_available and cleaned_bars:
        try:
            bar_source = "yfinance" if (not cached_bars and not getattr(result, "bars", None)) else "polygon"
            write_bars(symbol, cleaned_bars, source=bar_source, conn=_bar_cache_conn)
        except Exception as exc:
            # Non-fatal — cache write failure doesn't break the refresh
            print(f"[UF-SNAPSHOT] Bar cache write failed for {symbol}: {exc}")

    # ── Step 5: Merge cached + new bars, finalize ────────────────────────
    all_bars = cached_bars + cleaned_bars
    return _finalize_bars(all_bars), dropped


def _finalize_bars(bars: List[Bar]) -> List[Bar]:
    """Deduplicate by date, filter usable closes, sort by timestamp."""
    seen_dates: Dict[Any, Bar] = {}
    for b in bars:
        ts = b.timestamp
        date_key = ts.date() if hasattr(ts, "date") else ts
        # Later bars (from API) override cached bars for the same date
        seen_dates[date_key] = b

    close_clean: List[Bar] = []
    for b in seen_dates.values():
        try:
            close_value = getattr(b, "close", None)
            if close_value is None:
                continue
            float(close_value)
        except Exception:
            continue
        close_clean.append(b)

    close_clean.sort(key=lambda b: b.timestamp)
    return close_clean


def load_recent_daily_bar_metrics(
    symbol: str,
    client: Optional[Any] = None,
    lookback_days: int = RECENT_BAR_LOOKBACK_DAYS,
) -> Dict[str, Any]:
    if client is None:
        client = get_unified_market_data()

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(2, int(lookback_days)))

    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=True,
        limit=None,
    )

    result = client.get_history(req)
    raw_bars: List[Bar] = getattr(result, "bars", []) or []
    cleaned_bars, dropped = sanitize_daily_bars(raw_bars, min_price_floor=MIN_PRICE_FLOOR)

    close_clean: List[Bar] = []
    for bar in cleaned_bars:
        try:
            close_value = getattr(bar, "close", None)
            if close_value is None:
                continue
            float(close_value)
        except Exception:
            continue
        close_clean.append(bar)

    close_clean.sort(key=lambda bar: bar.timestamp)
    latest = close_clean[-1] if close_clean else None
    previous = close_clean[-2] if len(close_clean) >= 2 else None

    latest_close = _safe_optional_float(getattr(latest, "close", None)) if latest is not None else None
    latest_volume = _safe_optional_float(getattr(latest, "volume", None)) if latest is not None else None
    previous_close = _safe_optional_float(getattr(previous, "close", None)) if previous is not None else None
    previous_volume = _safe_optional_float(getattr(previous, "volume", None)) if previous is not None else None

    latest_timestamp = None
    if latest is not None:
        try:
            latest_timestamp = getattr(latest, "timestamp", None)
            if latest_timestamp is not None:
                latest_timestamp = latest_timestamp.isoformat()
        except Exception:
            latest_timestamp = None

    latest_traded_dollar_volume = None
    if latest_close is not None and latest_volume is not None:
        latest_traded_dollar_volume = float(latest_close) * float(latest_volume)

    return {
        "bar_count": len(close_clean),
        "dropped": dropped,
        "latest_close": latest_close,
        "latest_volume": latest_volume,
        "previous_close": previous_close,
        "previous_volume": previous_volume,
        "latest_traded_dollar_volume": latest_traded_dollar_volume,
        "latest_timestamp": latest_timestamp,
    }


def _pad_decision_vector(raw_dv: Any, length: int = 6) -> List[float]:
    """
    Normalize the decision_vector so that:
        - It is always a list[float] of fixed length (default 6).
        - Missing values are padded with 0.0.
        - Extra values are truncated.
    """
    if raw_dv is None:
        return [0.0] * length

    try:
        dv = list(raw_dv)
    except Exception:
        return [0.0] * length

    if len(dv) < length:
        dv = dv + [0.0] * (length - len(dv))
    elif len(dv) > length:
        dv = dv[:length]

    out: List[float] = []
    for x in dv:
        try:
            out.append(float(x))
        except Exception:
            out.append(0.0)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _safe_vector_value(vector: List[float], index: int, default: float = 0.0) -> float:
    if index < 0 or index >= len(vector):
        return float(default)
    try:
        return float(vector[index])
    except Exception:
        return float(default)


# ----------------------------------------------------------------------
# Public API: single-row UF snapshot evaluator
# ----------------------------------------------------------------------

def evaluate_symbol_snapshot(
    symbol: str,
    asset_type: str = "stock",
    years_history: int = YEARS_HISTORY,
    client: Optional[Any] = None,
    _bar_cache_conn=None,
) -> Dict[str, Any]:
    """
    Compute a UF-Core + MDG snapshot row for one symbol.

    Inputs
    ------
    symbol      : ticker symbol (e.g. "AAPL", "SPY", "BTC-USD")
    asset_type  : semantic label used by TFE snapshot:
                    "stock", "etf", "index", "crypto", ...
                  For now, callers typically pass "stock" for equities/ETFs,
                  "index" for indices, "crypto" for BTC-USD, etc.
    years_history : number of years of daily bars to use.
    client      : optional unified market data client; if None, a new one
                  is obtained via get_unified_market_data().
    _bar_cache_conn : optional psycopg2 connection for the bar cache DB.

    Output
    ------
    A dict with the same row fields used in the snapshot envelope payload, plus bar_count.
    CP-2 additions: F_n (cognitive load scalar), raw_x_m (medium-frequency state).

    Notes
    -----
    - NO TA is computed here; everything comes from UF-Core structural fields.
    - Structural recency fields are materialized from published decision lineage,
      not from request-time heuristics.
    - This function is deliberately small so it can be called from
      refresh_snapshot_full without dragging in any Streamlit / UI code.
    """
    bars, dropped = _fetch_history(symbol, years=years_history, client=client,
                                    _bar_cache_conn=_bar_cache_conn)
    bar_count = len(bars)
    history_meta = history_metadata_from_bars(bars)

    # CP-2: compute cognitive scalars from the close bar array.
    # Fails closed (None, None) if insufficient data or any error.
    close_prices: np.ndarray = np.array(
        [float(b.close) for b in bars], dtype=float
    ) if bars else np.array([], dtype=float)
    cognitive = compute_cognitive_scalars(close_prices)
    f_n: Optional[float] = cognitive["F_n"]
    raw_x_m: Optional[float] = cognitive["raw_x_m"]
    s_n: Optional[float] = cognitive["s_n"]

    # If we truly have no usable data, still return a row so the UI doesn't break.
    if not bars:
        return {
            "ticker": symbol,
            "asset_type": asset_type,
            "price": float("nan"),
            "regime": "NO_DATA",
            "S_UF": 0.0,
            "R_UF": 0.0,
            "stability_score": 0.0,
            "max_dd": 0.0,
            "decision_vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "D_k": 0.0,
            "M_k": 0.0,
            "R_rev_k": 0.0,
            "U_star_k": 0.0,
            "C_k": 0.0,
            "prev_C_k": None,
            "P_k": 0.0,
            "B_k": 0.0,
            "bar_count": 0,
            "gate_count": 0,
            "active_gate_count": 0,
            "decision_guard": {"gate_unlock_transient_neutralized": False},
            "integrity_dropped": dropped,
            "history_available_steps": int(history_meta["history_available_steps"]),
            "ts_gap_days_from_prev": float(history_meta["ts_gap_days_from_prev"]),
            "structural_recency_schema_version": "v1",
            "steps_since_regime_change": 0,
            "steps_since_pattern_change": 0,
            "steps_since_reversal_sign_flip": -1,
            "D_steps_since_sign_flip": -1,
            "M_steps_since_sign_flip": -1,
            "R_rev_steps_since_sign_flip": -1,
            "U_star_steps_since_sign_flip": -1,
            "C_steps_since_sign_flip": -1,
            "P_steps_since_sign_flip": -1,
            "B_steps_since_sign_flip": -1,
            "S_UF_steps_since_sign_flip": -1,
            "R_UF_steps_since_sign_flip": -1,
            "F_n": None,
            "raw_x_m": None,
            "s_n": None,
        }

    # Use the same structural adapter as Watchlist and other TFE pages.
    state = compute_structural_state(symbol, bars)

    # Defensive extraction of fields
    last_close = _safe_float(state.get("last_close"), float("nan"))
    regime = str(state.get("regime", "UNKNOWN"))
    s_uf = _safe_float(state.get("S_UF"), 0.0)
    r_uf = _safe_float(state.get("R_UF"), 0.0)
    stability_score = _safe_float(state.get("stability_score"), 0.0)
    max_dd = _safe_float(state.get("max_drawdown"), 0.0)

    decision_vector = _pad_decision_vector(state.get("decision_vector"))
    d_k = _safe_optional_float(state.get("D_k"))
    m_k = _safe_optional_float(state.get("M_k"))
    r_rev_k = _safe_optional_float(state.get("R_rev_k"))
    u_star_k = _safe_optional_float(state.get("U_star_k"))
    c_k = _safe_optional_float(state.get("C_k"))
    prev_c_k = _safe_optional_float(state.get("prev_C_k"))
    p_k = _safe_optional_float(state.get("P_k"))
    b_k = _safe_optional_float(state.get("B_k"))

    # Keep L4 basis complete for downstream strict checks; low-data rows are
    # decision-gated to Hold by bar-count policy in the recommendation layer.
    if d_k is None:
        d_k = _safe_vector_value(decision_vector, 0, 0.0)
    if m_k is None:
        m_k = _safe_vector_value(decision_vector, 1, 0.0)
    if r_rev_k is None:
        r_rev_k = _safe_vector_value(decision_vector, 2, 0.0)
    if u_star_k is None:
        u_star_k = _safe_vector_value(decision_vector, 3, 0.0)
    if c_k is None:
        c_k = 0.0
    if p_k is None:
        p_k = _safe_vector_value(decision_vector, 4, 0.0)
    if b_k is None:
        b_k = _safe_vector_value(decision_vector, 5, 0.0)

    gate_count = _safe_int(state.get("gate_count"), 0)
    active_gate_count = _safe_int(state.get("active_gate_count"), 0)

    decision_guard_raw = state.get("decision_guard", {})
    decision_guard = decision_guard_raw if isinstance(decision_guard_raw, dict) else {}

    row: Dict[str, Any] = {
        "ticker": symbol,
        "asset_type": asset_type,
        "price": last_close,
        "regime": regime,
        "S_UF": s_uf,
        "R_UF": r_uf,
        "stability_score": stability_score,
        "max_dd": max_dd,
        "decision_vector": decision_vector,
        "D_k": d_k,
        "M_k": m_k,
        "R_rev_k": r_rev_k,
        "U_star_k": u_star_k,
        "C_k": c_k,
        "prev_C_k": prev_c_k,
        "P_k": p_k,
        "B_k": b_k,
        "bar_count": int(bar_count),
        "gate_count": gate_count,
        "active_gate_count": active_gate_count,
        "decision_guard": decision_guard,
        "integrity_dropped": dropped,
        # CP-2: cognitive scalars — None when kernel cannot compute (insufficient bars)
        "F_n": f_n,
        "raw_x_m": raw_x_m,
        "s_n": s_n,
        # Incremental refresh: store the latest bar's timestamp so the next
        # refresh can skip recomputation when no new bars exist.
        "last_bar_timestamp": bars[-1].timestamp.isoformat() if bars and hasattr(bars[-1], 'timestamp') and bars[-1].timestamp else None,
    }
    row.update(
        build_structural_recency_payload(
            symbol=symbol,
            current_state=row,
            history_available_steps=int(history_meta["history_available_steps"]),
            ts_gap_days_from_prev=float(history_meta["ts_gap_days_from_prev"]),
        )
    )

    return row


# ----------------------------------------------------------------------
# Minimal CLI helper (optional)
# ----------------------------------------------------------------------

def _demo_single_ticker() -> None:
    """
    Tiny demo if you run this file directly.

    Example:
        python uf_mdg_snapshot.py AAPL
    """
    import json as _json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python uf_mdg_snapshot.py TICKER [ASSET_TYPE]")
        print("Example: python uf_mdg_snapshot.py AAPL stock")
        return

    ticker = sys.argv[1].upper().strip()
    a_type = sys.argv[2] if len(sys.argv) >= 3 else "stock"

    row = evaluate_symbol_snapshot(ticker, asset_type=a_type)
    print(_json.dumps(row, indent=2, default=str))


if __name__ == "__main__":
    _demo_single_ticker()