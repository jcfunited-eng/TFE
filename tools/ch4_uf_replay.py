"""
ch4_uf_replay.py — CH4 causal whole-history evaluation over the local store
===========================================================================

Runs the CH4 true-to-original engine (ch4_uf_engine) over the preserved
local 5-year store (quarantine_12k_universe.parquet, 2021-03-26 ..
2026-03-24 — bull, bear, and recovery: all SPY conditions), and files raw
evidence. PAPER ONLY. Never touches production.

DECLARED BEFORE ANY RESULT (no outcome-driven edits):
  Universe rule   — every symbol with >= MIN_BARS bars and median close
                    >= $5 (lineage price floor). No hand-picking.
  Signal          — a day whose governed action is ACCUMULATE and the
                    previous day's action was not ACCUMULATE (fresh
                    entries, not continuations).
  Signal evidence — forward close-to-close returns at +5/+10/+20/+60 bars
                    (lineage horizons + the spec's 60), WR and mean, both
                    for ACCUMULATE and (symmetrically) AVOID.
  Book            — $100,000; 10% equity slices; max 10 concurrent
                    positions; one position per symbol; enter at signal
                    close; exit at the first AVOID event for the symbol or
                    +20 bars, whichever comes first; final bar force-close;
                    ties broken alphabetically; no costs (paper, matching
                    the lineage's frictionless record). Book return
                    reported whole-span and per calendar year.
  Field modes     — RAW primary, LOG variant, both reported raw.

Usage:
  python tools/ch4_uf_replay.py test                # determinism + causality
  python tools/ch4_uf_replay.py run RAW AAPL MSFT   # named symbols
  python tools/ch4_uf_replay.py universe RAW 500    # first N by rule order
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_engine import (  # noqa: E402
    DayState,
    actions_digest,
    assert_causal,
    replay_symbol,
)

PARQUET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "quarantine_12k_universe.parquet")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "artifacts", "ch4_uf")
MIN_BARS = 1250
PRICE_FLOOR = 5.0
WARMUP = 60
HORIZONS = (5, 10, 20, 60)
BOOK_CASH = 100_000.0
BOOK_SLICE = 0.10
BOOK_MAX_POS = 10
BOOK_HORIZON = 20


def load_store(with_volume: bool = False) -> pd.DataFrame:
    cols = ["Date", "Symbol", "Close"] + (["Volume"] if with_volume else [])
    df = pd.read_parquet(PARQUET, columns=cols)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def universe_by_rule(df: pd.DataFrame) -> List[str]:
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    ok = stats[(stats["bars"] >= MIN_BARS) & (stats["med"] >= PRICE_FLOOR)]
    return sorted(ok.index.tolist())


def replay_frame(df: pd.DataFrame, symbol: str, field_mode: str):
    sub = df[df["Symbol"] == symbol].sort_values("Date")
    dates = sub["Date"].dt.date.tolist()
    closes = sub["Close"].to_numpy(dtype=float)
    states = replay_symbol(dates, closes, field_mode=field_mode, warmup=WARMUP)
    return dates, closes, states


def replay_frame_v2(df: pd.DataFrame, symbol: str):
    """Conformant v2 realization (ch4_uf_kernel_v2): normalized field,
    adaptive ‖ΔSEV‖ gating, attention relevance from Volume, coherent CV,
    spec S/w/Reg, de-stubbed S(UF), full Γ, graded χ."""
    from tools.ch4_uf_kernel_v2 import replay_symbol_v2
    sub = df[df["Symbol"] == symbol].sort_values("Date")
    dates = sub["Date"].dt.date.tolist()
    closes = sub["Close"].to_numpy(dtype=float)
    vols = sub["Volume"].to_numpy(dtype=float) if "Volume" in sub.columns else None
    states = replay_symbol_v2(dates, closes, vols, warmup=WARMUP)
    return dates, closes, states


def signal_rows_v2(symbol: str, dates, closes, states):
    """V2 signals: fresh strict-governance transitions; event-resolution
    flag = a new gate verifiably closed this bar (gate_count increased)."""
    rows = []
    n = len(closes)
    prev_action = None
    prev_action_z = None
    prev_diamond = None
    prev_ie = (0, 0)
    prev_k = None
    for t in range(n):
        s = states[t]
        if s is None:
            prev_action = prev_action_z = prev_diamond = None
            prev_ie = (0, 0)
            prev_k = None
            continue
        new_gate = int(prev_k is not None and s.gate_count > prev_k)

        emits = []  # (channel, side)
        if s.action != prev_action and s.action in ("ACCUMULATE", "AVOID"):
            emits.append(("strict", s.action))
        if s.action_z != prev_action_z and s.action_z in ("ACCUMULATE", "AVOID"):
            emits.append(("strict_z", s.action_z))
        if s.ignition == 1 and prev_ie[0] == 0:
            emits.append(("primitive", "ACCUMULATE"))
        if s.extinction == 1 and prev_ie[1] == 0:
            emits.append(("primitive", "AVOID"))
        if s.action_diamond != prev_diamond and s.action_diamond in ("ACCUMULATE", "AVOID"):
            emits.append(("diamond", s.action_diamond))

        if closes[t] >= PRICE_FLOOR:
            for channel, side in emits:
                row = {
                    "symbol": symbol, "date": str(dates[t]), "t": t,
                    "channel": channel, "action": side,
                    "close": float(closes[t]),
                    "Q_20": s.Q_20, "F_n": s.F_n, "F_n_z": s.F_n_z,
                    "x_m": s.x_m, "chi_n": s.chi_n, "S_UF": s.S_UF,
                    "ignition": s.ignition, "extinction": s.extinction,
                    "regime": s.regime, "gate_count": s.gate_count,
                    "event_type": s.event_type, "boundary_today": new_gate,
                }
                for h in HORIZONS:
                    row[f"ret_{h}"] = (
                        float(closes[t + h] / closes[t] - 1.0) if t + h < n else None
                    )
                rows.append(row)
        prev_action = s.action
        prev_action_z = s.action_z
        prev_diamond = s.action_diamond
        prev_ie = (s.ignition, s.extinction)
        prev_k = s.gate_count
    return rows


def boundary_flags(closes: np.ndarray, field_mode: str) -> np.ndarray:
    """Causal same-day gate-close condition: D_end[t] = |dF[t]| + sigma[t]
    (endpoint kappa = 0) >= tau_D. Sufficient for a true boundary since
    kappa >= 0. Splits signals into EVENT-resolution (a gate verifiably
    closed today) vs forming-gate (daily-flicker). Declared decomposition."""
    from quarantine_historical_kernel import KernelParameters as _KP
    p = _KP()
    F = closes.astype(float) if field_mode == "RAW" else np.log(closes.astype(float))
    n = len(F)
    dF = np.zeros(n)
    if n > 1:
        dF[1:] = np.diff(F)
    sig = np.zeros(n)
    for t in range(n):
        w0 = max(0, t - p.W + 1)
        win = F[w0 : t + 1]
        sig[t] = float(np.mean((win - win.mean()) ** 2))
    return (p.alpha_1 * np.abs(dF) + p.alpha_2 * sig) >= p.tau_D


def signal_rows(symbol: str, dates, closes, states: List[Optional[DayState]],
                bflags: Optional[np.ndarray] = None):
    """Fresh CP-2 governed signals (the lineage-realized rule), price floor
    applied at signal time. Strict ch06-mapping actions are tallied by the
    caller for the report but produced no trades in the preserved run."""
    rows = []
    n = len(closes)
    prev_action = None
    for t in range(n):
        s = states[t]
        if s is None:
            prev_action = None
            continue
        fresh = s.action_cp2 if s.action_cp2 != prev_action else None
        if fresh in ("ACCUMULATE", "AVOID") and closes[t] >= PRICE_FLOOR:
            row = {
                "symbol": symbol, "date": str(dates[t]), "t": t,
                "action": fresh, "close": float(closes[t]),
                "Q_20": s.Q_20, "F_n": s.F_n, "x_m": s.x_m, "chi_n": s.chi_n,
                "strict_action": s.action, "ignition": s.ignition,
                "gate_count": s.gate_count, "event_type": s.event_type,
                "boundary_today": int(bool(bflags[t])) if bflags is not None else None,
            }
            for h in HORIZONS:
                row[f"ret_{h}"] = (
                    float(closes[t + h] / closes[t] - 1.0) if t + h < n else None
                )
            rows.append(row)
        prev_action = s.action_cp2
    return rows


def summarize_signals(all_rows: List[dict]) -> dict:
    out = {}
    for side in ("ACCUMULATE", "AVOID"):
        rows = [r for r in all_rows if r["action"] == side]
        side_stats = {"signals": len(rows)}
        for h in HORIZONS:
            vals = [r[f"ret_{h}"] for r in rows if r[f"ret_{h}"] is not None]
            if vals:
                arr = np.array(vals)
                side_stats[f"h{h}"] = {
                    "n": len(vals),
                    "wr_pct": round(100.0 * float((arr > 0).mean()), 2),
                    "mean_pct": round(100.0 * float(arr.mean()), 3),
                }
        out[side] = side_stats
    return out


def run_book(all_rows: List[dict], frames: Dict[str, tuple]) -> dict:
    """Deterministic paper book per the declared mechanics."""
    entries = sorted(
        [r for r in all_rows if r["action"] == "ACCUMULATE"],
        key=lambda r: (r["date"], r["symbol"]),
    )
    avoid_by_symbol: Dict[str, List[str]] = {}
    for r in all_rows:
        if r["action"] == "AVOID":
            avoid_by_symbol.setdefault(r["symbol"], []).append(r["date"])

    all_dates = sorted({r["date"] for r in all_rows} | {
        str(d) for sym in frames for d in frames[sym][0]
    })
    entries_by_date: Dict[str, List[dict]] = {}
    for r in entries:
        entries_by_date.setdefault(r["date"], []).append(r)

    cash = BOOK_CASH
    positions: Dict[str, dict] = {}
    closed_trades: List[dict] = []
    equity_curve: List[tuple] = []

    def close_lookup(sym: str, t: int) -> Optional[float]:
        dts, cls, _ = frames[sym]
        return float(cls[t]) if 0 <= t < len(cls) else None

    for d in all_dates:
        # exits first (deterministic order)
        for sym in sorted(list(positions.keys())):
            pos = positions[sym]
            dts, cls, sts = frames[sym]
            idx = pos["idx_map"].get(d)
            if idx is None:
                continue
            age = idx - pos["t_in"]
            hit_avoid = sts[idx] == "AVOID"
            at_horizon = age >= BOOK_HORIZON
            last_bar = idx == len(cls) - 1
            if hit_avoid or at_horizon or last_bar:
                px = float(cls[idx])
                pnl = pos["shares"] * (px - pos["px_in"])
                cash += pos["shares"] * px
                closed_trades.append({
                    "symbol": sym, "date_in": pos["date_in"], "date_out": d,
                    "px_in": pos["px_in"], "px_out": px, "bars_held": age,
                    "reason": ("AVOID" if hit_avoid else ("HORIZON" if at_horizon else "EOD")),
                    "ret_pct": round(100.0 * (px / pos["px_in"] - 1.0), 3),
                    "pnl": round(pnl, 2),
                })
                del positions[sym]

        # entries
        for r in entries_by_date.get(d, []):
            sym = r["symbol"]
            if sym in positions or len(positions) >= BOOK_MAX_POS:
                continue
            equity = cash + sum(
                p["shares"] * (close_lookup(s, p["idx_map"].get(d, p["t_in"])) or p["px_in"])
                for s, p in positions.items()
            )
            budget = min(cash, BOOK_SLICE * equity)
            if budget <= 0:
                continue
            px = r["close"]
            shares = budget / px
            dts, cls, sts = frames[sym]
            idx_map = {str(dd): i for i, dd in enumerate(dts)}
            positions[sym] = {
                "shares": shares, "px_in": px, "date_in": d,
                "t_in": r["t"], "idx_map": idx_map,
            }
            cash -= shares * px

        equity = cash + sum(
            p["shares"] * (close_lookup(s, p["idx_map"].get(d, p["t_in"])) or p["px_in"])
            for s, p in positions.items()
        )
        equity_curve.append((d, round(equity, 2)))

    rets = [t["ret_pct"] for t in closed_trades]
    wins = sum(1 for x in rets if x > 0)
    final_equity = equity_curve[-1][1] if equity_curve else BOOK_CASH

    by_year: Dict[str, dict] = {}
    prev_eq = BOOK_CASH
    cur_year = None
    year_start_eq = BOOK_CASH
    for d, eq in equity_curve:
        y = d[:4]
        if cur_year is None:
            cur_year = y
        if y != cur_year:
            by_year[cur_year] = {"ret_pct": round(100.0 * (prev_eq / year_start_eq - 1.0), 2)}
            cur_year = y
            year_start_eq = prev_eq
        prev_eq = eq
    if cur_year is not None:
        by_year[cur_year] = {"ret_pct": round(100.0 * (prev_eq / year_start_eq - 1.0), 2)}

    return {
        "closed_trades": len(closed_trades),
        "wr_pct": round(100.0 * wins / len(rets), 2) if rets else None,
        "mean_trade_pct": round(float(np.mean(rets)), 3) if rets else None,
        "final_equity": final_equity,
        "total_return_pct": round(100.0 * (final_equity / BOOK_CASH - 1.0), 2),
        "by_year": by_year,
        "trades": closed_trades,
    }


def cmd_test() -> int:
    df = load_store()
    for mode in ("RAW", "LOG"):
        t0 = time.time()
        dates, closes, states = replay_frame(df, "AAPL", mode)
        dt = time.time() - t0
        d1 = actions_digest("AAPL", dates, states, mode)
        dates2, closes2, states2 = replay_frame(df, "AAPL", mode)
        d2 = actions_digest("AAPL", dates2, states2, mode)
        assert d1 == d2, "determinism failure"
        n = len(closes)
        sample = [WARMUP + 5, n // 3, n // 2, (2 * n) // 3, n - 2]
        assert_causal(dates, closes, states, mode, sample)
        acts = [s.action for s in states if s is not None]
        acts2 = [s.action_cp2 for s in states if s is not None]
        ign = sum(s.ignition for s in states if s is not None)
        from collections import Counter
        print(f"[{mode}] AAPL bars={n} replay={dt:.1f}s digest={d1[:12]} "
              f"strict={dict(Counter(acts))} cp2={dict(Counter(acts2))} "
              f"ignitions={ign} CAUSAL-OK DETERMINISM-OK")
    return 0


def _evaluate(symbols: List[str], mode: str, tag: str) -> None:
    df = load_store(with_volume=(mode == "V2"))
    os.makedirs(OUT_DIR, exist_ok=True)
    frames: Dict[str, tuple] = {}
    all_rows: List[dict] = []
    t0 = time.time()
    for i, sym in enumerate(symbols):
        try:
            if mode == "V2":
                dates, closes, states = replay_frame_v2(df, sym)
            else:
                dates, closes, states = replay_frame(df, sym, mode)
        except Exception as e:
            print(f"  {sym}: FAILED {e}")
            continue
        if mode == "V2":
            rows = signal_rows_v2(sym, dates, closes, states)
            # book exits ride the primitive extinction channel (declared)
            acts = [("AVOID" if (s is not None and s.extinction == 1) else
                     (s.action if s is not None else None)) for s in states]
        else:
            rows = signal_rows(sym, dates, closes, states, boundary_flags(closes, mode))
            acts = [s.action_cp2 if s is not None else None for s in states]
        all_rows.extend(rows)
        frames[sym] = (dates, closes, acts)
        if (i + 1) % 25 == 0 or i == len(symbols) - 1:
            el = time.time() - t0
            print(f"  [{i+1}/{len(symbols)}] {sym} signals_total={len(all_rows)} "
                  f"elapsed={el:.0f}s", flush=True)

    if mode == "V2":
        summary = {ch: summarize_signals([r for r in all_rows if r["channel"] == ch])
                   for ch in ("strict", "strict_z", "primitive", "diamond")}
        event_rows = [r for r in all_rows if r.get("boundary_today") == 1]
        summary_event = {ch: summarize_signals([r for r in event_rows if r["channel"] == ch])
                         for ch in ("strict", "strict_z", "primitive", "diamond")}
        book_rows = [r for r in all_rows if r["channel"] == "primitive"]
    else:
        summary = summarize_signals(all_rows)
        event_rows = [r for r in all_rows if r.get("boundary_today") == 1]
        summary_event = summarize_signals(event_rows)
        book_rows = all_rows
    book = run_book(book_rows, frames)
    result = {
        "engine": "ch4_uf_engine v1 (preserved lineage kernel + full ch06 action mapping)",
        "field_mode": mode,
        "declared": {
            "universe_rule": f">= {MIN_BARS} bars, median close >= ${PRICE_FLOOR}",
            "book": f"${BOOK_CASH:,.0f}, {int(BOOK_SLICE*100)}% slices, max {BOOK_MAX_POS}, "
                    f"exit first AVOID or +{BOOK_HORIZON} bars, no costs",
        },
        "symbols_evaluated": len(frames),
        "signals": summary,
        "signals_event_resolution": summary_event,
        "book": {k: v for k, v in book.items() if k != "trades"},
    }
    out_path = os.path.join(OUT_DIR, f"ch4_uf_{tag}_{mode}.json")
    with open(out_path, "w") as f:
        json.dump({**result, "book_trades": book["trades"],
                   "signal_rows": all_rows}, f, indent=1, default=str)
    print(json.dumps(result, indent=1, default=str))
    print(f"filed: {out_path}")


def cmd_run(mode: str, symbols: List[str]) -> int:
    _evaluate(symbols, mode, "named")
    return 0


def cmd_universe(mode: str, limit: int) -> int:
    df = load_store()
    symbols = universe_by_rule(df)
    print(f"universe by rule: {len(symbols)} symbols; evaluating first {limit}")
    _evaluate(symbols[:limit], mode, f"universe{limit}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "test":
        raise SystemExit(cmd_test())
    if cmd == "run":
        raise SystemExit(cmd_run(sys.argv[2], sys.argv[3:]))
    if cmd == "universe":
        raise SystemExit(cmd_universe(sys.argv[2], int(sys.argv[3])))
    print(__doc__)
    raise SystemExit(2)
