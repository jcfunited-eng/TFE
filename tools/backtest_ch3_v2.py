#!/usr/bin/env python3
"""
CH3 v2 Backtest: M_k-driven energy grabber
==========================================

Entry: M_k(t) > 0 AND M_k(t) > M_k(t-1) > M_k(t-2), D_k(t) = 1,
       SPY D_k(t) = 1, bar_count >= 21, price >= $5.

Exit (first of):
  1. M_k rollover: M_k(t) < M_k(t-1) for 2 consecutive bars
  2. -10% from entry (catastrophic floor)
  3. +1.5×ATR from entry (profit target)
  4. -1×ATR from entry (stop loss)
  5. 5 bars elapsed (max hold)

Position size: $2,500.

Also runs a control with original CH3 entry conditions:
  S_UF >= 0.70, D_k = 1, bar_count > 20.

Data source: runtime_decisions_history (validation DB).

Usage:
  python3 tools/backtest_ch3_v2.py
"""

import sys
import json
from collections import defaultdict
from datetime import datetime

try:
    import psycopg2
except ImportError:
    print("psycopg2 required. pip install psycopg2-binary")
    sys.exit(1)


DB_CONFIG = {
    "host": "/var/run/postgresql",
    "dbname": "tfe_validation",
    "user": "postgres",
}

WINDOW_START = "2026-04-07"
WINDOW_END = "2026-05-05"
POSITION_SIZE = 2500.0
MIN_PRICE = 5.0
MIN_BAR_COUNT = 21


def fetch_all_history(conn):
    """Fetch all ticker-day kernel states in the backtest window."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            ticker,
            generated_at_utc::date AS day,
            CAST(NULLIF(snapshot_row_json->>'M_k', '') AS DOUBLE PRECISION) AS m_k,
            CAST(NULLIF(snapshot_row_json->>'D_k', '') AS DOUBLE PRECISION) AS d_k,
            CAST(NULLIF(snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) AS s_uf,
            CAST(NULLIF(snapshot_row_json->>'B_k', '') AS DOUBLE PRECISION) AS b_k,
            CAST(NULLIF(snapshot_row_json->>'bar_count', '') AS INTEGER) AS bar_count,
            CAST(NULLIF(snapshot_row_json->>'price', '') AS DOUBLE PRECISION) AS price
        FROM runtime_decisions_history
        WHERE generated_at_utc >= %s AND generated_at_utc < %s
          AND snapshot_row_json->>'M_k' IS NOT NULL
        ORDER BY ticker, generated_at_utc
    """, (WINDOW_START, WINDOW_END))

    # Group by ticker, deduplicate by day (keep latest per day)
    by_ticker = defaultdict(dict)
    for row in cur.fetchall():
        ticker, day, m_k, d_k, s_uf, b_k, bar_count, price = row
        by_ticker[ticker][day] = {
            "m_k": m_k, "d_k": d_k, "s_uf": s_uf, "b_k": b_k,
            "bar_count": bar_count, "price": price,
        }
    cur.close()
    return by_ticker


def fetch_spy_dk(conn):
    """Get SPY D_k per day. If not in history, try to infer from daily_bars."""
    cur = conn.cursor()
    # First try runtime_decisions_history
    cur.execute("""
        SELECT generated_at_utc::date AS day,
               CAST(NULLIF(snapshot_row_json->>'D_k', '') AS DOUBLE PRECISION) AS d_k
        FROM runtime_decisions_history
        WHERE ticker = 'SPY' AND generated_at_utc >= %s AND generated_at_utc < %s
        ORDER BY generated_at_utc
    """, (WINDOW_START, WINDOW_END))
    spy = {}
    for day, d_k in cur.fetchall():
        spy[day] = d_k

    if not spy:
        # SPY not in history for this window. Check if it's in daily_bars
        # and compute a simple direction proxy (close > prev_close = 1, else -1)
        cur.execute("""
            SELECT bar_date, close FROM daily_bars
            WHERE symbol = 'SPY' AND bar_date >= %s AND bar_date < %s
            ORDER BY bar_date
        """, (WINDOW_START, WINDOW_END))
        bars = cur.fetchall()
        if len(bars) >= 2:
            for i in range(1, len(bars)):
                day, close = bars[i]
                prev_close = bars[i - 1][1]
                # Use a simple heuristic: SPY D_k=1 when SPY is in an uptrend
                # This is an approximation — the real D_k comes from the kernel
                spy[day] = 1 if close >= prev_close else -1
            # Note: this is a PROXY, not the kernel's D_k. Flag in report.
            print(f"[WARN] SPY D_k computed from price proxy, not kernel. {len(spy)} days.")
        else:
            # No SPY data at all — assume D_k=1 for the April window
            # (April 7-May 4 was a generally rising market)
            print("[WARN] No SPY data. Assuming SPY D_k=1 for entire window.")

    cur.close()
    return spy


def fetch_atr(conn):
    """Compute ATR-14 per ticker from daily_bars."""
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, bar_date, high, low, close
        FROM daily_bars
        WHERE bar_date >= '2026-03-15' AND bar_date < %s
        ORDER BY symbol, bar_date
    """, (WINDOW_END,))

    bars_by_ticker = defaultdict(list)
    for symbol, bar_date, high, low, close in cur.fetchall():
        bars_by_ticker[symbol].append((bar_date, high, low, close))
    cur.close()

    atr_by_ticker = {}
    for ticker, bars in bars_by_ticker.items():
        if len(bars) < 15:
            continue
        trs = []
        for i in range(1, len(bars)):
            _, h, l, c = bars[i]
            prev_c = bars[i - 1][3]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            trs.append(tr)
        # ATR-14 from most recent 14 TRs
        if len(trs) >= 14:
            atr_by_ticker[ticker] = sum(trs[-14:]) / 14
    return atr_by_ticker


def run_backtest(by_ticker, spy_dk, atr_map, entry_fn, label):
    """Run a backtest with the given entry function."""
    trades = []
    signals_by_day = defaultdict(list)

    for ticker, days in by_ticker.items():
        sorted_days = sorted(days.keys())
        if len(sorted_days) < 3:
            continue

        atr = atr_map.get(ticker)
        if atr is None or atr <= 0:
            continue

        for i in range(2, len(sorted_days)):
            day = sorted_days[i]
            state = days[day]
            prev1 = days[sorted_days[i - 1]]
            prev2 = days[sorted_days[i - 2]]

            # Check SPY D_k
            spy_d = spy_dk.get(day, 1)  # default 1 if no data
            if spy_d != 1:
                continue

            # Check entry conditions
            if not entry_fn(state, prev1, prev2):
                continue

            # Signal admitted
            entry_price = state["price"]
            if entry_price is None or entry_price < MIN_PRICE:
                continue

            signals_by_day[day].append(ticker)

            # Simulate exit over next bars
            exit_price = None
            exit_reason = None
            exit_day = None
            bars_held = 0

            tp_price = entry_price + 1.5 * atr
            sl_price = entry_price - 1.0 * atr
            catastrophic = entry_price * 0.90

            # Look ahead up to 5 bars
            prev_m_k = state["m_k"]
            m_k_declining_count = 0

            for j in range(i + 1, min(i + 6, len(sorted_days))):
                future_day = sorted_days[j]
                future = days[future_day]
                future_price = future["price"]
                future_m_k = future["m_k"]
                bars_held += 1

                if future_price is None:
                    continue

                # Check exit conditions in order
                # 1. M_k rollover (2 consecutive declines)
                if future_m_k is not None and prev_m_k is not None:
                    if future_m_k < prev_m_k:
                        m_k_declining_count += 1
                    else:
                        m_k_declining_count = 0
                    if m_k_declining_count >= 2:
                        exit_price = future_price
                        exit_reason = "m_k_rollover"
                        exit_day = future_day
                        break

                # 2. Catastrophic floor
                if future_price <= catastrophic:
                    exit_price = catastrophic
                    exit_reason = "catastrophic_floor"
                    exit_day = future_day
                    break

                # 3. TP hit
                if future_price >= tp_price:
                    exit_price = tp_price
                    exit_reason = "take_profit"
                    exit_day = future_day
                    break

                # 4. SL hit
                if future_price <= sl_price:
                    exit_price = sl_price
                    exit_reason = "stop_loss"
                    exit_day = future_day
                    break

                # 5. Max hold
                if bars_held >= 5:
                    exit_price = future_price
                    exit_reason = "max_hold"
                    exit_day = future_day
                    break

                prev_m_k = future_m_k

            if exit_price is None:
                # Ran out of data — exit at last available price
                if i + 1 < len(sorted_days):
                    exit_price = days[sorted_days[min(i + 1, len(sorted_days) - 1)]]["price"]
                    exit_reason = "data_end"
                    exit_day = sorted_days[min(i + 1, len(sorted_days) - 1)]
                else:
                    continue

            pl_pct = (exit_price - entry_price) / entry_price * 100
            shares = max(1, int(POSITION_SIZE / entry_price))
            pl_dollar = (exit_price - entry_price) * shares

            trades.append({
                "ticker": ticker,
                "entry_day": str(day),
                "exit_day": str(exit_day),
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "exit_reason": exit_reason,
                "pl_pct": round(pl_pct, 2),
                "pl_dollar": round(pl_dollar, 2),
                "bars_held": bars_held,
                "atr": round(atr, 4),
            })

    return trades, signals_by_day


def ch3_v2_entry(state, prev1, prev2):
    """CH3 v2: M_k rising 3 bars, D_k=1, bar_count>=21, price>=$5."""
    m_k = state.get("m_k")
    m_k_1 = prev1.get("m_k")
    m_k_2 = prev2.get("m_k")
    d_k = state.get("d_k")
    bar_count = state.get("bar_count")
    price = state.get("price")

    if any(v is None for v in [m_k, m_k_1, m_k_2, d_k, bar_count, price]):
        return False
    if m_k <= 0:
        return False
    if not (m_k > m_k_1 > m_k_2):
        return False
    if d_k != 1:
        return False
    if bar_count < MIN_BAR_COUNT:
        return False
    if price < MIN_PRICE:
        return False
    return True


def ch3_original_entry(state, prev1, prev2):
    """Original CH3: S_UF >= 0.70, D_k=1, bar_count > 20."""
    s_uf = state.get("s_uf")
    d_k = state.get("d_k")
    bar_count = state.get("bar_count")
    price = state.get("price")

    if any(v is None for v in [s_uf, d_k, bar_count, price]):
        return False
    if s_uf < 0.70:
        return False
    if d_k != 1:
        return False
    if bar_count <= 20:
        return False
    if price < MIN_PRICE:
        return False
    return True


def report(trades, label, signals_by_day):
    """Generate report section."""
    lines = []
    lines.append(f"\n### {label}")
    lines.append(f"")
    lines.append(f"**Signals admitted:** {len(trades)}")

    if not trades:
        lines.append("No signals in window.")
        return "\n".join(lines)

    wins = [t for t in trades if t["pl_pct"] > 0]
    losses = [t for t in trades if t["pl_pct"] <= 0]
    avg_win = sum(t["pl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pl_pct"] for t in losses) / len(losses) if losses else 0
    wr = len(wins) / len(trades) * 100
    ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")
    total_pl = sum(t["pl_dollar"] for t in trades)

    lines.append(f"**Win rate:** {len(wins)}/{len(trades)} = {wr:.1f}%")
    lines.append(f"**Avg win:** +{avg_win:.2f}%")
    lines.append(f"**Avg loss:** {avg_loss:.2f}%")
    lines.append(f"**Asymmetry ratio:** {ratio:.2f}x")
    lines.append(f"**Total P&L:** ${total_pl:,.0f}")
    lines.append(f"")

    # Exit reason distribution
    reasons = defaultdict(int)
    for t in trades:
        reasons[t["exit_reason"]] += 1
    lines.append("**Exit reason distribution:**")
    lines.append("")
    lines.append("| Reason | Count | % |")
    lines.append("|--------|-------|---|")
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        lines.append(f"| {reason} | {count} | {count / len(trades) * 100:.0f}% |")

    # Max concurrent positions
    if signals_by_day:
        max_concurrent = max(len(v) for v in signals_by_day.values())
        lines.append(f"")
        lines.append(f"**Max concurrent signals (single day):** {max_concurrent}")

    # Sample trades
    lines.append(f"")
    lines.append("**Sample trades (top 10 by P&L):**")
    lines.append("")
    lines.append("| Ticker | Entry | Exit | P&L% | Exit Reason | Bars |")
    lines.append("|--------|-------|------|------|-------------|------|")
    for t in sorted(trades, key=lambda x: -x["pl_pct"])[:10]:
        lines.append(
            f"| {t['ticker']} | ${t['entry_price']} | ${t['exit_price']} "
            f"| {t['pl_pct']:+.2f}% | {t['exit_reason']} | {t['bars_held']} |"
        )

    return "\n".join(lines)


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    print("Connected to validation DB.")

    print("Fetching kernel history...")
    by_ticker = fetch_all_history(conn)
    print(f"  {len(by_ticker)} tickers loaded.")

    print("Fetching SPY D_k...")
    spy_dk = fetch_spy_dk(conn)
    print(f"  {len(spy_dk)} SPY days.")

    print("Computing ATR-14...")
    atr_map = fetch_atr(conn)
    print(f"  {len(atr_map)} tickers with ATR.")

    # Run CH3 v2 backtest
    print("\nRunning CH3 v2 backtest (M_k rising)...")
    v2_trades, v2_signals = run_backtest(by_ticker, spy_dk, atr_map, ch3_v2_entry, "CH3 v2")
    print(f"  {len(v2_trades)} trades.")

    # Run control (original CH3)
    print("Running control backtest (original CH3: S_UF >= 0.70)...")
    orig_trades, orig_signals = run_backtest(by_ticker, spy_dk, atr_map, ch3_original_entry, "Original CH3")
    print(f"  {len(orig_trades)} trades.")

    conn.close()

    # Generate report
    md = []
    md.append("# CH3 v2 Backtest Report")
    md.append(f"**Window:** {WINDOW_START} to {WINDOW_END}")
    md.append(f"**Position size:** ${POSITION_SIZE:,.0f}")
    md.append(f"**Data source:** runtime_decisions_history (validation DB)")
    md.append(f"**Generated:** {datetime.utcnow().isoformat()[:19]}Z")
    md.append("")
    md.append("**NOTE:** SPY D_k computed from price proxy (close vs prev_close), "
              "not kernel. This is an approximation.")

    md.append(report(v2_trades, "CH3 v2: M_k-driven energy grabber", v2_signals))
    md.append(report(orig_trades, "Control: Original CH3 (S_UF >= 0.70, D_k = 1)", orig_signals))

    # Overlap analysis
    v2_tickers = {t["ticker"] for t in v2_trades}
    orig_tickers = {t["ticker"] for t in orig_trades}
    overlap = v2_tickers & orig_tickers
    md.append(f"\n### Overlap Analysis")
    md.append(f"")
    md.append(f"- CH3 v2 unique tickers: {len(v2_tickers)}")
    md.append(f"- Original CH3 unique tickers: {len(orig_tickers)}")
    md.append(f"- Overlap: {len(overlap)} tickers ({len(overlap) / max(len(v2_tickers), 1) * 100:.0f}% of v2)")
    if overlap:
        md.append(f"- Overlapping: {', '.join(sorted(list(overlap)[:20]))}")

    report_text = "\n".join(md)

    # Write report
    report_path = "docs/backtests/ch3_v2_april.md"
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"\nReport written to {report_path}")
    print(report_text)


if __name__ == "__main__":
    main()
