#!/usr/bin/env python3
"""
CH3 v2.1 Backtest: Selective M_k-driven energy grabber
======================================================

Two selectivity variants on top of v2 base entry.

Variant A — Universe-relative: M_k(t) in top decile of all admissible
Accumulate tickers on the same bar.

Variant B — Self-relative: M_k(t) >= 2.0 * stdev(M_k over trailing
20 bars for that ticker).

Acceptance criteria:
  - max concurrent signals <= 20
  - asymmetry ratio >= 1.5x
  - ticker overlap with CH2 <= 30%
  - overlap with original CH3 <= 10%

Usage:
  python3 tools/backtest_ch3_v2_1.py
"""

import sys
import math
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

# CH2 tickers from Alpaca fill history (April 7 - May 4)
CH2_TICKERS = {
    "ASR","BDX","BELFA","BELFB","BIRK","BOH","CARL","CHIQ","CMDB","COPP",
    "CRTO","DORM","KBA","KSPI","LPLA","MED","NBIX","PODD","PWR","REGN",
    "RRX","SMHX","SOHU","SONO","SXC","TSMZ","TXBC","UNHG","WCC","WOR",
}

# Original CH3 tickers (from v2 backtest control — S_UF >= 0.70, D_k=1)
# Will be computed dynamically


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
            CAST(NULLIF(snapshot_row_json->>'bar_count', '') AS INTEGER) AS bar_count,
            CAST(NULLIF(snapshot_row_json->>'price', '') AS DOUBLE PRECISION) AS price,
            snapshot_row_json->>'decision_label' AS decision_label
        FROM runtime_decisions_history
        WHERE generated_at_utc >= %s AND generated_at_utc < %s
          AND snapshot_row_json->>'M_k' IS NOT NULL
        ORDER BY ticker, generated_at_utc
    """, (WINDOW_START, WINDOW_END))

    by_ticker = defaultdict(dict)
    for row in cur.fetchall():
        ticker, day, m_k, d_k, s_uf, bar_count, price, dl = row
        by_ticker[ticker][day] = {
            "m_k": m_k, "d_k": d_k, "s_uf": s_uf,
            "bar_count": bar_count, "price": price,
            "decision_label": dl,
        }
    cur.close()
    return by_ticker


def fetch_spy_dk(conn):
    """Get SPY D_k per day from daily_bars proxy."""
    cur = conn.cursor()
    cur.execute("""
        SELECT bar_date, close FROM daily_bars
        WHERE symbol = 'SPY' AND bar_date >= %s AND bar_date < %s
        ORDER BY bar_date
    """, (WINDOW_START, WINDOW_END))
    bars = cur.fetchall()
    spy = {}
    if len(bars) >= 2:
        for i in range(1, len(bars)):
            day, close = bars[i]
            prev_close = bars[i - 1][1]
            spy[day] = 1 if close >= prev_close else -1
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

    atr_map = {}
    for ticker, bars in bars_by_ticker.items():
        if len(bars) < 15:
            continue
        trs = []
        for i in range(1, len(bars)):
            _, h, l, c = bars[i]
            prev_c = bars[i - 1][3]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            trs.append(tr)
        if len(trs) >= 14:
            atr_map[ticker] = sum(trs[-14:]) / 14
    return atr_map


def fetch_m_k_history(conn):
    """Fetch extended M_k history for stdev computation (trailing 20 bars)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            ticker,
            generated_at_utc::date AS day,
            CAST(NULLIF(snapshot_row_json->>'M_k', '') AS DOUBLE PRECISION) AS m_k
        FROM runtime_decisions_history
        WHERE generated_at_utc >= '2026-03-01' AND generated_at_utc < %s
          AND snapshot_row_json->>'M_k' IS NOT NULL
        ORDER BY ticker, generated_at_utc
    """, (WINDOW_END,))

    m_k_hist = defaultdict(list)
    for ticker, day, m_k in cur.fetchall():
        if m_k is not None:
            m_k_hist[ticker].append((day, m_k))
    cur.close()
    return m_k_hist


def compute_m_k_stdev(m_k_hist, ticker, target_day, window=20):
    """Compute stdev of M_k over trailing `window` bars for a ticker."""
    hist = m_k_hist.get(ticker, [])
    # Get values before target_day
    vals = [m for d, m in hist if d < target_day]
    if len(vals) < window:
        vals = vals  # use whatever we have
    else:
        vals = vals[-window:]
    if len(vals) < 3:
        return None
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return math.sqrt(var) if var > 0 else None


def v2_base_check(state, prev1, prev2, spy_dk_day):
    """V2 base entry conditions."""
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
    if spy_dk_day != 1:
        return False
    if bar_count < MIN_BAR_COUNT:
        return False
    if price < MIN_PRICE:
        return False
    return True


def original_ch3_check(state, prev1, prev2, spy_dk_day):
    """Original CH3 entry for overlap computation."""
    s_uf = state.get("s_uf")
    d_k = state.get("d_k")
    bar_count = state.get("bar_count")
    price = state.get("price")
    if any(v is None for v in [s_uf, d_k, bar_count, price]):
        return False
    return s_uf >= 0.70 and d_k == 1 and bar_count > 20 and price >= MIN_PRICE and spy_dk_day == 1


def simulate_trade(ticker, entry_day_idx, sorted_days, days_data, atr):
    """Simulate a single trade from entry to exit."""
    entry_price = days_data[sorted_days[entry_day_idx]]["price"]
    tp_price = entry_price + 1.5 * atr
    sl_price = entry_price - 1.0 * atr
    catastrophic = entry_price * 0.90

    prev_m_k = days_data[sorted_days[entry_day_idx]]["m_k"]
    m_k_decline = 0

    for j in range(entry_day_idx + 1, min(entry_day_idx + 6, len(sorted_days))):
        future = days_data[sorted_days[j]]
        fp = future["price"]
        fm = future["m_k"]
        bars = j - entry_day_idx

        if fp is None:
            continue

        if fm is not None and prev_m_k is not None:
            if fm < prev_m_k:
                m_k_decline += 1
            else:
                m_k_decline = 0
            if m_k_decline >= 2:
                return fp, "m_k_rollover", bars, sorted_days[j]

        if fp <= catastrophic:
            return catastrophic, "catastrophic_floor", bars, sorted_days[j]
        if fp >= tp_price:
            return tp_price, "take_profit", bars, sorted_days[j]
        if fp <= sl_price:
            return sl_price, "stop_loss", bars, sorted_days[j]
        if bars >= 5:
            return fp, "max_hold", bars, sorted_days[j]

        prev_m_k = fm

    # Ran out of data
    if entry_day_idx + 1 < len(sorted_days):
        last = sorted_days[min(entry_day_idx + 1, len(sorted_days) - 1)]
        return days_data[last]["price"], "data_end", 1, last
    return None, None, 0, None


def run_variant(by_ticker, spy_dk, atr_map, m_k_hist, variant_label, extra_filter_fn):
    """Run a backtest variant."""
    # First pass: collect all v2-admissible signals per day
    admissible_by_day = defaultdict(list)

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
            spy_d = spy_dk.get(day, 1)

            if v2_base_check(state, prev1, prev2, spy_d):
                admissible_by_day[day].append({
                    "ticker": ticker, "day_idx": i,
                    "m_k": state["m_k"], "price": state["price"],
                    "sorted_days": sorted_days, "days_data": days,
                    "atr": atr,
                })

    # Second pass: apply selectivity filter
    trades = []
    signals_by_day = defaultdict(list)
    selected_tickers = set()

    for day in sorted(admissible_by_day.keys()):
        candidates = admissible_by_day[day]
        selected = extra_filter_fn(candidates, day, m_k_hist)

        for c in selected:
            ticker = c["ticker"]
            signals_by_day[day].append(ticker)
            selected_tickers.add(ticker)

            exit_price, exit_reason, bars, exit_day = simulate_trade(
                ticker, c["day_idx"], c["sorted_days"], c["days_data"], c["atr"]
            )
            if exit_price is None:
                continue

            entry_price = c["price"]
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
                "bars_held": bars,
                "m_k": round(c["m_k"], 4),
            })

    return trades, signals_by_day, selected_tickers


def variant_a_filter(candidates, day, m_k_hist):
    """Top decile of M_k across all admissible tickers on this day."""
    if not candidates:
        return []
    m_k_values = sorted([c["m_k"] for c in candidates], reverse=True)
    cutoff_idx = max(1, len(m_k_values) // 10)
    cutoff = m_k_values[cutoff_idx - 1]
    return [c for c in candidates if c["m_k"] >= cutoff]


def variant_b_filter(candidates, day, m_k_hist):
    """M_k >= 2.0 * stdev(trailing 20 bars) for that ticker."""
    selected = []
    for c in candidates:
        sd = compute_m_k_stdev(m_k_hist, c["ticker"], day)
        if sd is not None and sd > 0 and c["m_k"] >= 2.0 * sd:
            selected.append(c)
    return selected


def report(trades, label, signals_by_day, selected_tickers, ch2_tickers, orig_ch3_tickers):
    """Generate report section."""
    lines = []
    lines.append(f"\n### {label}")
    lines.append("")
    lines.append(f"**Signals admitted:** {len(trades)}")

    if not trades:
        lines.append("No signals in window.")
        lines.append("")
        lines.append("| Criterion | Value | Pass? |")
        lines.append("|-----------|-------|-------|")
        lines.append("| Max concurrent <= 20 | 0 | YES |")
        lines.append("| Asymmetry >= 1.5x | n/a | NO (no trades) |")
        lines.append("| CH2 overlap <= 30% | 0% | YES |")
        lines.append("| Original CH3 overlap <= 10% | 0% | YES |")
        return "\n".join(lines)

    wins = [t for t in trades if t["pl_pct"] > 0]
    losses = [t for t in trades if t["pl_pct"] <= 0]
    avg_win = sum(t["pl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pl_pct"] for t in losses) / len(losses) if losses else 0
    wr = len(wins) / len(trades) * 100
    ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")
    total_pl = sum(t["pl_dollar"] for t in trades)

    max_concurrent = max(len(v) for v in signals_by_day.values()) if signals_by_day else 0

    ch2_overlap = selected_tickers & ch2_tickers
    ch2_pct = len(ch2_overlap) / max(len(selected_tickers), 1) * 100
    orig_overlap = selected_tickers & orig_ch3_tickers
    orig_pct = len(orig_overlap) / max(len(selected_tickers), 1) * 100

    lines.append(f"**Win rate:** {len(wins)}/{len(trades)} = {wr:.1f}%")
    lines.append(f"**Avg win:** +{avg_win:.2f}%")
    lines.append(f"**Avg loss:** {avg_loss:.2f}%")
    lines.append(f"**Asymmetry ratio:** {ratio:.2f}x")
    lines.append(f"**Total P&L:** ${total_pl:,.0f}")
    lines.append(f"**Max concurrent signals:** {max_concurrent}")
    lines.append(f"**Unique tickers:** {len(selected_tickers)}")
    lines.append("")

    # Exit reasons
    reasons = defaultdict(int)
    for t in trades:
        reasons[t["exit_reason"]] += 1
    lines.append("**Exit reason distribution:**")
    lines.append("")
    lines.append("| Reason | Count | % |")
    lines.append("|--------|-------|---|")
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        lines.append(f"| {reason} | {count} | {count / len(trades) * 100:.0f}% |")

    # Overlap
    lines.append("")
    lines.append(f"**CH2 overlap:** {len(ch2_overlap)}/{len(selected_tickers)} = {ch2_pct:.0f}%")
    if ch2_overlap:
        lines.append(f"  Tickers: {', '.join(sorted(ch2_overlap))}")
    lines.append(f"**Original CH3 overlap:** {len(orig_overlap)}/{len(selected_tickers)} = {orig_pct:.0f}%")
    if orig_overlap:
        lines.append(f"  Tickers: {', '.join(sorted(orig_overlap))}")

    # Acceptance criteria
    lines.append("")
    lines.append("**Acceptance criteria:**")
    lines.append("")
    lines.append("| Criterion | Value | Pass? |")
    lines.append("|-----------|-------|-------|")
    c1 = max_concurrent <= 20
    c2 = ratio >= 1.5
    c3 = ch2_pct <= 30
    c4 = orig_pct <= 10
    lines.append(f"| Max concurrent <= 20 | {max_concurrent} | {'YES' if c1 else 'NO'} |")
    lines.append(f"| Asymmetry >= 1.5x | {ratio:.2f}x | {'YES' if c2 else 'NO'} |")
    lines.append(f"| CH2 overlap <= 30% | {ch2_pct:.0f}% | {'YES' if c3 else 'NO'} |")
    lines.append(f"| Original CH3 overlap <= 10% | {orig_pct:.0f}% | {'YES' if c4 else 'NO'} |")
    all_pass = c1 and c2 and c3 and c4
    lines.append(f"")
    lines.append(f"**Overall: {'ALL CRITERIA MET' if all_pass else 'CRITERIA NOT MET'}**")

    # Top trades
    lines.append("")
    lines.append("**Top 10 trades:**")
    lines.append("")
    lines.append("| Ticker | Entry | Exit | P&L% | M_k | Exit Reason | Bars |")
    lines.append("|--------|-------|------|------|-----|-------------|------|")
    for t in sorted(trades, key=lambda x: -x["pl_pct"])[:10]:
        lines.append(
            f"| {t['ticker']} | ${t['entry_price']} | ${t['exit_price']} "
            f"| {t['pl_pct']:+.2f}% | {t['m_k']} | {t['exit_reason']} | {t['bars_held']} |"
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

    print("Fetching M_k history for stdev...")
    m_k_hist = fetch_m_k_history(conn)
    print(f"  {len(m_k_hist)} tickers with M_k history.")

    conn.close()

    # Compute original CH3 tickers for overlap
    orig_tickers = set()
    for ticker, days in by_ticker.items():
        sorted_days = sorted(days.keys())
        if len(sorted_days) < 3:
            continue
        for i in range(2, len(sorted_days)):
            day = sorted_days[i]
            state = days[day]
            prev1 = days[sorted_days[i - 1]]
            prev2 = days[sorted_days[i - 2]]
            spy_d = spy_dk.get(day, 1)
            if original_ch3_check(state, prev1, prev2, spy_d):
                orig_tickers.add(ticker)

    print(f"\nOriginal CH3 tickers: {len(orig_tickers)}")

    # Run Variant A
    print("Running Variant A (top decile M_k)...")
    a_trades, a_signals, a_tickers = run_variant(
        by_ticker, spy_dk, atr_map, m_k_hist, "Variant A", variant_a_filter
    )
    print(f"  {len(a_trades)} trades, {len(a_tickers)} unique tickers.")

    # Run Variant B
    print("Running Variant B (self-relative 2x stdev)...")
    b_trades, b_signals, b_tickers = run_variant(
        by_ticker, spy_dk, atr_map, m_k_hist, "Variant B", variant_b_filter
    )
    print(f"  {len(b_trades)} trades, {len(b_tickers)} unique tickers.")

    # Generate report
    md = []
    md.append("# CH3 v2.1 Selectivity Backtest Report")
    md.append(f"**Window:** {WINDOW_START} to {WINDOW_END}")
    md.append(f"**Position size:** ${POSITION_SIZE:,.0f}")
    md.append(f"**Data source:** runtime_decisions_history (validation DB)")
    md.append(f"**Generated:** {datetime.utcnow().isoformat()[:19]}Z")
    md.append("")
    md.append("**NOTE:** SPY D_k computed from price proxy. 62% data_end exits due to sparse validation DB.")
    md.append("")
    md.append(f"**CH2 tickers in window:** {len(CH2_TICKERS)}")
    md.append(f"**Original CH3 tickers in window:** {len(orig_tickers)}")

    md.append(report(a_trades, "Variant A: Universe-relative (top decile M_k)", a_signals, a_tickers, CH2_TICKERS, orig_tickers))
    md.append(report(b_trades, "Variant B: Self-relative (M_k >= 2x stdev)", b_signals, b_tickers, CH2_TICKERS, orig_tickers))

    # Cross-variant overlap
    ab_overlap = a_tickers & b_tickers
    md.append("\n### Cross-Variant Overlap")
    md.append(f"")
    md.append(f"- Variant A tickers: {len(a_tickers)}")
    md.append(f"- Variant B tickers: {len(b_tickers)}")
    md.append(f"- A ∩ B overlap: {len(ab_overlap)} ({len(ab_overlap) / max(len(a_tickers | b_tickers), 1) * 100:.0f}%)")

    report_text = "\n".join(md)

    report_path = "docs/backtests/ch3_v2_1_april.md"
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"\nReport written to {report_path}")
    print(report_text)


if __name__ == "__main__":
    main()
