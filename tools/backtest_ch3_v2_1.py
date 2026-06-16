#!/usr/bin/env python3
"""
CH3 v2.1 Backtest — Corrected apparatus
========================================

Fixes from addendum:
1. Computes per-bar kernel state by running L0-L4 on daily_bars (not sparse snapshots).
2. Splits v2 baseline into resolved vs unresolved trades.
3. Then runs Variant A (top decile) and Variant B (self-relative 2x stdev).

Usage:
  python3 tools/backtest_ch3_v2_1.py
"""

import sys
import os
import math
import time
from collections import defaultdict
from datetime import datetime, date
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import psycopg2
    import pandas as pd
except ImportError:
    print("psycopg2 and pandas required.")
    sys.exit(1)

from uf_core.uf_structural_engine import compute_structural_state

DB_CONFIG = {"host": "/var/run/postgresql", "dbname": "tfe_validation", "user": "postgres"}
WINDOW_START = date(2026, 4, 7)
WINDOW_END = date(2026, 5, 5)
POSITION_SIZE = 2500.0
MIN_PRICE = 5.0
MIN_BAR_COUNT = 21

CH2_TICKERS = {
    "ASR","BDX","BELFA","BELFB","BIRK","BOH","CARL","CHIQ","CMDB","COPP",
    "CRTO","DORM","KBA","KSPI","LPLA","MED","NBIX","PODD","PWR","REGN",
    "RRX","SMHX","SOHU","SONO","SXC","TSMZ","TXBC","UNHG","WCC","WOR",
}


def load_daily_bars(conn):
    """Load daily bars for all tickers, Mar 1 - May 5 (need history for kernel)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, bar_date, open, high, low, close, volume
        FROM daily_bars
        WHERE bar_date >= '2026-01-01' AND bar_date < '2026-05-06'
          AND symbol NOT LIKE 'I:%%' AND symbol NOT LIKE 'X:%%'
        ORDER BY symbol, bar_date
    """)
    by_ticker = defaultdict(list)
    for symbol, bar_date, o, h, l, c, v in cur.fetchall():
        by_ticker[symbol].append((bar_date, o, h, l, c, v))
    cur.close()
    return by_ticker


def compute_kernel_series(bars_by_ticker, target_dates):
    """Run kernel at each target date, return per-ticker per-day kernel state."""
    kernel_states = {}  # {ticker: {date: {M_k, D_k, ...}}}
    total = len(bars_by_ticker)
    done = 0
    t0 = time.time()

    for ticker, bars in bars_by_ticker.items():
        done += 1
        if done % 500 == 0:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0
            print(f"  [{done}/{total}] {rate:.0f} tickers/s, ETA {eta:.0f}s", flush=True)

        if len(bars) < 60:  # need enough history for kernel
            continue

        ticker_states = {}
        for target_date in target_dates:
            # Truncate bars to this date
            truncated = [(d, o, h, l, c, v) for d, o, h, l, c, v in bars if d <= target_date]
            if len(truncated) < 30:
                continue

            bar_objs = [SimpleNamespace(
                close=r[4], open=r[1], high=r[2], low=r[3], volume=r[5],
                timestamp=pd.Timestamp(r[0])
            ) for r in truncated]

            try:
                result = compute_structural_state(ticker, bar_objs)
                ticker_states[target_date] = {
                    "M_k": result.get("M_k"),
                    "D_k": result.get("D_k"),
                    "S_UF": result.get("S_UF"),
                    "B_k": result.get("B_k"),
                    "bar_count": result.get("bar_count") or len(truncated),
                    "price": truncated[-1][4],  # close price
                }
            except Exception:
                pass

        if ticker_states:
            kernel_states[ticker] = ticker_states

    elapsed = time.time() - t0
    print(f"  Kernel computation: {done} tickers in {elapsed:.0f}s ({done/elapsed:.0f}/s)")
    return kernel_states


def compute_atr(bars, target_date):
    """ATR-14 from bars up to target_date."""
    truncated = [(d, o, h, l, c, v) for d, o, h, l, c, v in bars if d <= target_date]
    if len(truncated) < 15:
        return None
    trs = []
    for i in range(1, len(truncated)):
        h, l, c = truncated[i][2], truncated[i][3], truncated[i][4]
        prev_c = truncated[i-1][4]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    if len(trs) < 14:
        return None
    return sum(trs[-14:]) / 14


def v2_entry(state, prev1, prev2, spy_dk):
    m = state.get("M_k"); m1 = prev1.get("M_k"); m2 = prev2.get("M_k")
    d = state.get("D_k"); bc = state.get("bar_count"); p = state.get("price")
    if any(v is None for v in [m, m1, m2, d, bc, p]):
        return False
    return m > 0 and m > m1 > m2 and d == 1 and spy_dk == 1 and bc >= MIN_BAR_COUNT and p >= MIN_PRICE


def orig_ch3_entry(state, prev1, prev2, spy_dk):
    s = state.get("S_UF"); d = state.get("D_k"); bc = state.get("bar_count"); p = state.get("price")
    if any(v is None for v in [s, d, bc, p]):
        return False
    return s >= 0.70 and d == 1 and spy_dk == 1 and bc > 20 and p >= MIN_PRICE


def simulate_trade(ticker, entry_idx, sorted_days, states, bars_by_ticker):
    entry_state = states[sorted_days[entry_idx]]
    entry_price = entry_state["price"]
    atr = compute_atr(bars_by_ticker.get(ticker, []), sorted_days[entry_idx])
    if atr is None or atr <= 0:
        return None

    tp = entry_price + 1.5 * atr
    sl = entry_price - 1.0 * atr
    cat = entry_price * 0.90
    prev_m = entry_state["M_k"]
    m_decline = 0

    for j in range(entry_idx + 1, min(entry_idx + 6, len(sorted_days))):
        fs = states[sorted_days[j]]
        fp = fs["price"]; fm = fs["M_k"]
        bars = j - entry_idx
        if fp is None:
            continue
        if fm is not None and prev_m is not None:
            if fm < prev_m: m_decline += 1
            else: m_decline = 0
            if m_decline >= 2:
                return {"exit_price": fp, "reason": "m_k_rollover", "bars": bars, "day": sorted_days[j]}
        if fp <= cat:
            return {"exit_price": cat, "reason": "catastrophic_floor", "bars": bars, "day": sorted_days[j]}
        if fp >= tp:
            return {"exit_price": tp, "reason": "take_profit", "bars": bars, "day": sorted_days[j]}
        if fp <= sl:
            return {"exit_price": sl, "reason": "stop_loss", "bars": bars, "day": sorted_days[j]}
        if bars >= 5:
            return {"exit_price": fp, "reason": "max_hold", "bars": bars, "day": sorted_days[j]}
        prev_m = fm
    return None  # no exit found = unresolvable in data


def run_backtest(kernel_states, spy_dk, bars_by_ticker, entry_fn, extra_filter=None, m_k_hist=None):
    admissible_by_day = defaultdict(list)
    for ticker, states in kernel_states.items():
        days = sorted(states.keys())
        if len(days) < 3:
            continue
        for i in range(2, len(days)):
            d = days[i]
            sd = spy_dk.get(d, None)
            if sd is None:
                continue
            if entry_fn(states[d], states[days[i-1]], states[days[i-2]], sd):
                admissible_by_day[d].append({
                    "ticker": ticker, "idx": i, "days": days, "states": states,
                    "m_k": states[d]["M_k"], "price": states[d]["price"],
                })

    if extra_filter:
        for d in admissible_by_day:
            admissible_by_day[d] = extra_filter(admissible_by_day[d], d, m_k_hist)

    trades = []
    signals_by_day = defaultdict(list)
    tickers_set = set()
    for d in sorted(admissible_by_day):
        for c in admissible_by_day[d]:
            ticker = c["ticker"]
            signals_by_day[d].append(ticker)
            tickers_set.add(ticker)
            result = simulate_trade(ticker, c["idx"], c["days"], c["states"], bars_by_ticker)
            entry_price = c["price"]
            if result is None:
                # Unresolved — mark with last available price
                last_idx = min(c["idx"] + 1, len(c["days"]) - 1)
                last_price = c["states"][c["days"][last_idx]]["price"] if last_idx < len(c["days"]) else entry_price
                pl_pct = (last_price - entry_price) / entry_price * 100 if entry_price > 0 else 0
                shares = max(1, int(POSITION_SIZE / entry_price))
                trades.append({
                    "ticker": ticker, "entry_day": str(d), "exit_day": "unresolved",
                    "entry_price": round(entry_price, 2), "exit_price": round(last_price, 2),
                    "exit_reason": "data_end", "pl_pct": round(pl_pct, 2),
                    "pl_dollar": round((last_price - entry_price) * shares, 2),
                    "bars_held": 1, "m_k": round(c["m_k"], 4) if c["m_k"] else 0,
                    "resolved": False,
                })
            else:
                pl_pct = (result["exit_price"] - entry_price) / entry_price * 100
                shares = max(1, int(POSITION_SIZE / entry_price))
                trades.append({
                    "ticker": ticker, "entry_day": str(d), "exit_day": str(result["day"]),
                    "entry_price": round(entry_price, 2), "exit_price": round(result["exit_price"], 2),
                    "exit_reason": result["reason"], "pl_pct": round(pl_pct, 2),
                    "pl_dollar": round((result["exit_price"] - entry_price) * shares, 2),
                    "bars_held": result["bars"], "m_k": round(c["m_k"], 4) if c["m_k"] else 0,
                    "resolved": True,
                })
    return trades, signals_by_day, tickers_set


def variant_a_filter(candidates, day, m_k_hist):
    if not candidates: return []
    vals = sorted([c["m_k"] for c in candidates if c["m_k"] is not None], reverse=True)
    if not vals: return []
    cutoff = vals[max(0, len(vals) // 10 - 1)]
    return [c for c in candidates if c["m_k"] is not None and c["m_k"] >= cutoff]


def variant_b_filter(candidates, day, m_k_hist):
    selected = []
    for c in candidates:
        hist = m_k_hist.get(c["ticker"], [])
        vals = [m for d, m in hist if d < day][-20:]
        if len(vals) < 3: continue
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        sd = math.sqrt(var) if var > 0 else None
        if sd and c["m_k"] is not None and c["m_k"] >= 2.0 * sd:
            selected.append(c)
    return selected


def report_section(trades, label, signals_by_day, tickers_set, ch2_tickers, orig_tickers):
    lines = [f"\n### {label}", ""]
    resolved = [t for t in trades if t["resolved"]]
    unresolved = [t for t in trades if not t["resolved"]]

    for subset_label, subset in [("ALL", trades), ("RESOLVED ONLY", resolved), ("UNRESOLVED (data_end)", unresolved)]:
        lines.append(f"\n**{subset_label}:** {len(subset)} trades")
        if not subset:
            lines.append("  (none)")
            continue
        wins = [t for t in subset if t["pl_pct"] > 0]
        losses = [t for t in subset if t["pl_pct"] <= 0]
        aw = sum(t["pl_pct"] for t in wins) / len(wins) if wins else 0
        al = sum(t["pl_pct"] for t in losses) / len(losses) if losses else 0
        wr = len(wins) / len(subset) * 100
        ratio = abs(aw / al) if al != 0 else float("inf")
        tpl = sum(t["pl_dollar"] for t in subset)
        lines.append(f"  WR: {len(wins)}/{len(subset)} = {wr:.1f}% | Avg win: +{aw:.2f}% | Avg loss: {al:.2f}% | **Ratio: {ratio:.2f}x** | P&L: ${tpl:,.0f}")

    # Exit distribution (resolved only)
    if resolved:
        reasons = defaultdict(int)
        for t in resolved: reasons[t["exit_reason"]] += 1
        lines.append("\n**Exit reasons (resolved):**")
        for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
            lines.append(f"  {r}: {c} ({c/len(resolved)*100:.0f}%)")

    mc = max(len(v) for v in signals_by_day.values()) if signals_by_day else 0
    lines.append(f"\n**Max concurrent:** {mc} | **Unique tickers:** {len(tickers_set)}")

    if tickers_set:
        ch2_ol = tickers_set & ch2_tickers
        orig_ol = tickers_set & orig_tickers
        lines.append(f"**CH2 overlap:** {len(ch2_ol)}/{len(tickers_set)} = {len(ch2_ol)/len(tickers_set)*100:.0f}%")
        lines.append(f"**Orig CH3 overlap:** {len(orig_ol)}/{len(tickers_set)} = {len(orig_ol)/len(tickers_set)*100:.0f}%")

        # Acceptance criteria (on resolved trades only)
        r_wins = [t for t in resolved if t["pl_pct"] > 0]
        r_losses = [t for t in resolved if t["pl_pct"] <= 0]
        r_aw = sum(t["pl_pct"] for t in r_wins) / len(r_wins) if r_wins else 0
        r_al = sum(t["pl_pct"] for t in r_losses) / len(r_losses) if r_losses else 0
        r_ratio = abs(r_aw / r_al) if r_al != 0 else float("inf")

        lines.append("\n**Acceptance (on resolved trades):**")
        lines.append(f"| Criterion | Value | Pass? |")
        lines.append(f"|-----------|-------|-------|")
        lines.append(f"| Max concurrent <= 20 | {mc} | {'YES' if mc <= 20 else 'NO'} |")
        lines.append(f"| Asymmetry >= 1.5x | {r_ratio:.2f}x | {'YES' if r_ratio >= 1.5 else 'NO'} |")
        ch2_pct = len(ch2_ol) / max(len(tickers_set), 1) * 100
        orig_pct = len(orig_ol) / max(len(tickers_set), 1) * 100
        lines.append(f"| CH2 overlap <= 30% | {ch2_pct:.0f}% | {'YES' if ch2_pct <= 30 else 'NO'} |")
        lines.append(f"| Orig CH3 overlap <= 10% | {orig_pct:.0f}% | {'YES' if orig_pct <= 10 else 'NO'} |")
        all_pass = mc <= 20 and r_ratio >= 1.5 and ch2_pct <= 30 and orig_pct <= 10
        lines.append(f"\n**{'ALL CRITERIA MET' if all_pass else 'CRITERIA NOT MET'}**")

    return "\n".join(lines)


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    print("Loading daily bars...")
    bars_by_ticker = load_daily_bars(conn)
    print(f"  {len(bars_by_ticker)} tickers loaded.")

    # Get SPY D_k from kernel
    spy_bars = bars_by_ticker.get("SPY", [])
    target_dates = sorted({d for d, _, _, _, _, _ in spy_bars if WINDOW_START <= d < WINDOW_END})
    print(f"  {len(target_dates)} trading days in window.")

    print("Computing SPY D_k per day...")
    spy_dk = {}
    for td in target_dates:
        trunc = [(d, o, h, l, c, v) for d, o, h, l, c, v in spy_bars if d <= td]
        if len(trunc) < 30: continue
        bar_objs = [SimpleNamespace(close=r[4], open=r[1], high=r[2], low=r[3], volume=r[5],
                                   timestamp=pd.Timestamp(r[0])) for r in trunc]
        try:
            result = compute_structural_state("SPY", bar_objs)
            spy_dk[td] = result.get("D_k")
        except:
            pass
    print(f"  SPY D_k: {dict(list(spy_dk.items())[:3])}...")
    conn.close()

    print(f"\nComputing kernel states for {len(bars_by_ticker)} tickers x {len(target_dates)} days...")
    kernel_states = compute_kernel_series(bars_by_ticker, target_dates)
    print(f"  {len(kernel_states)} tickers with kernel states.")

    # Build M_k history for variant B
    m_k_hist = {}
    for ticker, states in kernel_states.items():
        m_k_hist[ticker] = [(d, s["M_k"]) for d, s in sorted(states.items()) if s["M_k"] is not None]

    # Compute orig CH3 tickers
    orig_tickers = set()
    for ticker, states in kernel_states.items():
        days = sorted(states.keys())
        if len(days) < 3: continue
        for i in range(2, len(days)):
            if orig_ch3_entry(states[days[i]], states[days[i-1]], states[days[i-2]], spy_dk.get(days[i], 0)):
                orig_tickers.add(ticker)
    print(f"  Original CH3 tickers: {len(orig_tickers)}")

    # V2 baseline
    print("\nRunning v2 baseline...")
    v2_trades, v2_sig, v2_tick = run_backtest(kernel_states, spy_dk, bars_by_ticker, v2_entry)
    print(f"  {len(v2_trades)} trades ({sum(1 for t in v2_trades if t['resolved'])} resolved)")

    # Variant A
    print("Running Variant A (top decile)...")
    a_trades, a_sig, a_tick = run_backtest(kernel_states, spy_dk, bars_by_ticker, v2_entry, variant_a_filter, m_k_hist)
    print(f"  {len(a_trades)} trades ({sum(1 for t in a_trades if t['resolved'])} resolved)")

    # Variant B
    print("Running Variant B (2x stdev)...")
    b_trades, b_sig, b_tick = run_backtest(kernel_states, spy_dk, bars_by_ticker, v2_entry, variant_b_filter, m_k_hist)
    print(f"  {len(b_trades)} trades ({sum(1 for t in b_trades if t['resolved'])} resolved)")

    # Report
    md = [
        "# CH3 v2.1 Backtest — Corrected Apparatus",
        f"**Window:** {WINDOW_START} to {WINDOW_END}",
        f"**Data:** Per-bar kernel via L0-L4 on daily_bars ({len(target_dates)} trading days, {len(kernel_states)} tickers)",
        f"**SPY D_k:** Computed by kernel (not price proxy)",
        f"**Generated:** {datetime.utcnow().isoformat()[:19]}Z",
        "",
    ]

    md.append(report_section(v2_trades, "V2 Baseline (no selectivity)", v2_sig, v2_tick, CH2_TICKERS, orig_tickers))
    md.append(report_section(a_trades, "Variant A: Top Decile M_k", a_sig, a_tick, CH2_TICKERS, orig_tickers))
    md.append(report_section(b_trades, "Variant B: Self-relative 2x stdev", b_sig, b_tick, CH2_TICKERS, orig_tickers))

    report_text = "\n".join(md)
    with open("docs/backtests/ch3_v2_1_april.md", "w") as f:
        f.write(report_text)
    print(f"\nReport written.")
    print(report_text)


if __name__ == "__main__":
    main()
