#!/usr/bin/env python3
"""
Fast replay: vectorized L5 filter across all tickers per day.
Identical math to walkforward_resume_20260624.py; eliminates the
per-ticker DataFrame construction (2.74M calls → 1 per day per day).

Optimization log (per command: bug-fix-only with logged diff):
  - PERF: batch all tickers for a day into one DataFrame, run L5 filter
    once per day instead of once per ticker per day. Math unchanged.
    Original: ~3.3h for 1250 days. New: estimated ~8-12 min.
"""
import json, pickle, sys, time
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tfe_l5_baseline import L5BaselineFilter

CACHE_FILE  = Path("/workspaces/Tao_Financial_Engine/backups/walkforward_kernel_cache_20260624.pkl")
LOCAL_DSN   = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
UNIVERSE_CSV = Path("/workspaces/Tao_Financial_Engine/quarantine_12k_l5_trades.csv")
OUTPUT_DIR  = Path("/workspaces/Tao_Financial_Engine/tools")

REPLAY_START    = "2021-04-01"
REPLAY_END      = "2026-03-24"
MAX_POSITIONS   = 30
EXIT_F_THRESHOLD = -0.10
MIN_HOLD_DAYS   = 7
N_NEIGHBORS     = 30
FWD_DAYS        = 20
WR_THRESHOLD    = 0.65
STARTING_EQUITY = 100_000.0
MIN_PRICE       = 5.0
TUPLE_FIELDS    = ["D_k","M_k","B_k","R_rev_k","U_star_k","C_k","P_k"]

_l5 = L5BaselineFilter()


def log(m):
    print(f"[WF {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def load_bars(tickers):
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()
    tstr = ",".join(f"'{t.upper()}'" for t in tickers)
    cur.execute(f"""
        SELECT UPPER(symbol), bar_date, open, close
        FROM daily_bars
        WHERE UPPER(symbol) IN ({tstr})
          AND bar_date >= '2020-01-01' AND bar_date <= '2026-06-30'
        ORDER BY symbol, bar_date
    """)
    rows = cur.fetchall()
    conn.close()
    raw = {}
    for sym, bd, o, c in rows:
        raw.setdefault(sym, []).append((bd, float(o or 0), float(c or 0)))
    result = {}
    for sym, rl in raw.items():
        df = pd.DataFrame(rl, columns=["bar_date","open","close"])
        df["bar_date"] = pd.to_datetime(df["bar_date"])
        result[sym] = df.set_index("bar_date").sort_index()
    return result


def build_day_snapshots(kernel_db, trading_days):
    """
    Pre-index kernel_db by (day → {ticker: snap}) for O(1) day lookups.
    Also pre-build a DataFrame per day for the L5 filter.
    Returns: day_snap_index[day] = {ticker: snap}
    """
    log("Building day-indexed snapshot lookup...")
    day_snap = {d: {} for d in trading_days}
    for ticker, snaps in kernel_db.items():
        for day, snap in snaps.items():
            if day in day_snap:
                day_snap[day][ticker] = snap
    return day_snap


def compute_neighbor_wr(current_tuple, hist_tuples, hist_returns):
    if len(hist_tuples) <= N_NEIGHBORS:
        return None
    hist = np.array(hist_tuples, dtype=float)
    curr = np.array(current_tuple, dtype=float)
    rets = np.array(hist_returns, dtype=float)
    ranges = hist.max(axis=0) - hist.min(axis=0)
    ranges = np.where(ranges < 1e-10, 1.0, ranges)
    diffs = (hist - curr) / ranges
    dists = np.sqrt((diffs**2).sum(axis=1))
    if len(dists) <= N_NEIGHBORS:
        neighbor_rets = rets
    else:
        idx = np.argpartition(dists, N_NEIGHBORS)[:N_NEIGHBORS]
        neighbor_rets = rets[idx]
    return float((neighbor_rets > 0).sum()) / len(neighbor_rets)


def extract_tuple(snap):
    vals = []
    for f in TUPLE_FIELDS:
        v = snap.get(f)
        if v is None or not np.isfinite(float(v)):
            return None
        vals.append(float(v))
    return vals


def l5_batch(day_tickers_snaps):
    """
    Vectorized L5 filter: one DataFrame for all tickers on this day.
    Returns set of tickers that pass L5 (Accumulate).
    Identical math to calling is_accumulate() per-ticker.
    """
    if not day_tickers_snaps:
        return set()
    rows = []
    tickers = []
    for ticker, snap in day_tickers_snaps.items():
        rows.append({
            "ticker": ticker, "asset_type": "stock",
            "bar_count": snap.get("bar_count", 0),
            "S_UF": snap.get("S_UF", 0),
            "R_UF": snap.get("R_UF", 0),
            "D_k":  snap.get("D_k",  0),
            "M_k":  snap.get("M_k",  0),
            "R_rev_k": snap.get("R_rev_k", 0),
            "U_star_k": snap.get("U_star_k", 0),
            "C_k":  snap.get("C_k",  0),
            "P_k":  snap.get("P_k",  0),
            "B_k":  snap.get("B_k",  0),
            "price": snap.get("price", 0),
        })
        tickers.append(ticker)
    df = pd.DataFrame(rows, index=tickers)
    result = _l5.apply_canonical_filter(df)
    return set(result.index.tolist())


def run_walkforward(universe, kernel_db, bars_db, trading_days):
    spy_bars = bars_db.get("SPY")
    if spy_bars is None:
        log("WARNING: SPY not found — no benchmark")

    # Pre-index by day for fast lookup
    day_snap = build_day_snapshots(kernel_db, trading_days)

    # Pre-run L5 filter for ALL days at once (1 DataFrame per day instead of per ticker)
    log("Pre-computing L5 filter for all days...")
    t_l5 = time.time()
    day_accumulate = {}  # {day: set(tickers that pass L5)}
    for di, day in enumerate(trading_days):
        day_snaps = day_snap.get(day, {})
        # Only tickers with price >= MIN_PRICE
        filtered = {t: s for t, s in day_snaps.items() if s.get("price", 0) >= MIN_PRICE}
        day_accumulate[day] = l5_batch(filtered)
        if (di + 1) % 250 == 0:
            log(f"  L5 precompute {di+1}/{len(trading_days)}")
    log(f"L5 precompute done in {time.time()-t_l5:.1f}s")

    # History per ticker for tuple proximity
    history_db = {t: {"tuples": [], "returns": []} for t in universe}
    portfolio = {}   # {ticker: {entry_date, entry_price, entry_alloc}}
    equity = STARTING_EQUITY
    cash = STARTING_EQUITY
    trades = []
    equity_curve = []
    spy_start = None

    log(f"Replay: {len(trading_days)} days, {len(universe)} tickers")

    for day_idx, day in enumerate(trading_days):
        day_dt = pd.Timestamp(day)

        # Update history: snapshots from FWD_DAYS ago now have known forward returns
        fwd_idx = day_idx - FWD_DAYS
        if fwd_idx >= 0:
            prior_day = trading_days[fwd_idx]
            prior_dt = pd.Timestamp(prior_day)
            for ticker in universe:
                snap = day_snap.get(prior_day, {}).get(ticker)
                if snap is None:
                    continue
                t_vals = extract_tuple(snap)
                if t_vals is None:
                    continue
                tb = bars_db.get(ticker.upper())
                if tb is None:
                    continue
                try:
                    pc = float(tb.loc[prior_dt, "close"])
                    tc = float(tb.loc[day_dt,   "close"])
                    if pc > 0 and tc > 0:
                        history_db[ticker]["tuples"].append(t_vals)
                        history_db[ticker]["returns"].append((tc - pc) / pc)
                except (KeyError, TypeError):
                    pass

        # Today's Accumulate set (already computed above)
        today_acc = day_accumulate.get(day, set())

        # Exit checks (max 30 positions)
        to_exit = []
        for ticker, pos in portfolio.items():
            tb = bars_db.get(ticker.upper())
            if tb is None:
                continue
            try:
                cur_close = float(tb.loc[day_dt, "close"])
            except (KeyError, TypeError):
                continue
            entry_px = pos["entry_price"]
            pnl_pct = (cur_close - entry_px) / entry_px
            age = (day_dt - pd.Timestamp(pos["entry_date"])).days

            # EXIT-F: catastrophic floor, always fires
            if pnl_pct <= EXIT_F_THRESHOLD:
                to_exit.append((ticker, cur_close, "exit_f_catastrophic", pnl_pct))
                continue

            # EXIT-A: L5 no longer Accumulate (uses pre-computed day_accumulate)
            if ticker not in today_acc:
                # EXIT-R9: suppress if young and losing
                if age < MIN_HOLD_DAYS and pnl_pct < 0:
                    pass  # hold
                else:
                    to_exit.append((ticker, cur_close, "exit_a_not_accumulate", pnl_pct))

        for ticker, exit_px, reason, pnl_pct in to_exit:
            pos = portfolio.pop(ticker)
            cash += pos["entry_alloc"] * (1 + pnl_pct)
            trades.append({
                "entry_date": pos["entry_date"], "exit_date": day,
                "ticker": ticker, "entry_px": pos["entry_price"], "exit_px": exit_px,
                "days_held": (day_dt - pd.Timestamp(pos["entry_date"])).days,
                "pnl_pct": round(pnl_pct, 6), "exit_reason": reason,
            })

        # Signal detection using pre-computed L5 results + tuple proximity
        slots = MAX_POSITIONS - len(portfolio)
        candidates = []
        if slots > 0:
            for ticker in (today_acc - set(portfolio.keys())):
                snap = day_snap.get(day, {}).get(ticker)
                if snap is None:
                    continue
                t_vals = extract_tuple(snap)
                if t_vals is None:
                    continue
                hist = history_db[ticker]
                wr = compute_neighbor_wr(t_vals, hist["tuples"], hist["returns"])
                if wr is not None and wr >= WR_THRESHOLD:
                    candidates.append((ticker, wr, snap))

        # Enter at t+1 open (equal weight)
        if candidates and slots > 0:
            candidates.sort(key=lambda x: -x[1])
            for ticker, wr, snap in candidates[:slots]:
                entry_px = snap.get("open_next", snap.get("price", 0))
                if entry_px <= 0:
                    continue
                alloc = equity / MAX_POSITIONS
                if alloc > cash:
                    continue
                cash -= alloc
                portfolio[ticker] = {
                    "entry_date": day, "entry_price": entry_px, "entry_alloc": alloc,
                }

        # Mark equity
        pos_val = 0.0
        for ticker, pos in portfolio.items():
            tb = bars_db.get(ticker.upper())
            if tb is None:
                pos_val += pos["entry_alloc"]
                continue
            try:
                pos_val += pos["entry_alloc"] * (
                    float(tb.loc[day_dt, "close"]) / pos["entry_price"])
            except (KeyError, TypeError):
                pos_val += pos["entry_alloc"]
        equity = cash + pos_val

        # SPY
        spy_equity = None
        if spy_bars is not None:
            try:
                sc = float(spy_bars.loc[day_dt, "close"])
                if spy_start is None:
                    spy_start = sc
                spy_equity = round(STARTING_EQUITY * sc / spy_start, 2)
            except (KeyError, TypeError):
                pass

        equity_curve.append({
            "date": day, "equity": round(equity, 2),
            "spy_equity": spy_equity, "n_positions": len(portfolio),
        })

        if day_idx % 50 == 0:
            log(f"  {day} | equity=${equity:,.0f} | pos={len(portfolio)} | trades={len(trades)}")

    # Force-close at replay end
    last_day = trading_days[-1]
    last_dt = pd.Timestamp(last_day)
    for ticker, pos in list(portfolio.items()):
        tb = bars_db.get(ticker.upper())
        exit_px = pos["entry_price"]
        if tb is not None:
            try:
                exit_px = float(tb.loc[last_dt, "close"])
            except (KeyError, TypeError):
                pass
        pnl_pct = (exit_px - pos["entry_price"]) / pos["entry_price"]
        trades.append({
            "entry_date": pos["entry_date"], "exit_date": last_day,
            "ticker": ticker, "entry_px": pos["entry_price"], "exit_px": exit_px,
            "days_held": (last_dt - pd.Timestamp(pos["entry_date"])).days,
            "pnl_pct": round(pnl_pct, 6), "exit_reason": "replay_end_close",
        })

    log(f"Replay complete: {len(trades)} trades, final equity=${equity:,.0f}")
    return trades, equity_curve


def compute_summary(trades, equity_curve, n_orig, n_kept, dropped):
    ec = pd.DataFrame(equity_curve)
    ec["date"] = pd.to_datetime(ec["date"])
    ec = ec.set_index("date")

    end_equity = ec["equity"].iloc[-1]
    years = (ec.index[-1] - ec.index[0]).days / 365.25
    ann_return = (end_equity / STARTING_EQUITY) ** (1/years) - 1 if years > 0 else 0.0
    max_dd = float(((ec["equity"] - ec["equity"].cummax()) / ec["equity"].cummax()).min())
    dr = ec["equity"].pct_change().dropna()
    sharpe = (dr.mean() / dr.std()) * np.sqrt(252) if dr.std() > 0 else 0.0

    td = pd.DataFrame(trades)
    win_rate = float((td["pnl_pct"] > 0).mean()) if len(td) > 0 else 0.0
    avg_days = float(td["days_held"].mean()) if len(td) > 0 else 0.0

    spy_eq = ec["spy_equity"].dropna()
    spy_ann = spy_dd = 0.0
    if len(spy_eq) >= 2:
        sy = (spy_eq.index[-1] - spy_eq.index[0]).days / 365.25
        spy_ann = (spy_eq.iloc[-1] / spy_eq.iloc[0]) ** (1/sy) - 1 if sy > 0 else 0.0
        spy_dd = float(((spy_eq - spy_eq.cummax()) / spy_eq.cummax()).min())

    return {
        "command": "TFE-CMD-WALKFORWARD-BET-WC-20260624 + AMEND-1",
        "replay_start": ec.index[0].strftime("%Y-%m-%d"),
        "replay_end":   ec.index[-1].strftime("%Y-%m-%d"),
        "starting_equity":        STARTING_EQUITY,
        "ending_equity":          round(end_equity, 2),
        "annualized_return_gross": round(ann_return, 6),
        "max_drawdown":           round(max_dd, 6),
        "sharpe":                 round(sharpe, 4),
        "win_rate":               round(win_rate, 4),
        "avg_days_held":          round(avg_days, 2),
        "n_trades":               len(trades),
        "n_unique_tickers":       len(set(t["ticker"] for t in trades)),
        "spy_annualized_return":  round(spy_ann, 6),
        "spy_max_drawdown":       round(spy_dd, 6),
        "eq_basket_annualized_return": "SPY used as proxy",
        "universe_original":  n_orig,
        "universe_kept":      n_kept,
        "universe_dropped":   n_orig - n_kept,
        "dropped_reasons":    dropped,
        "bet_target": {"ann_return": 0.12, "max_dd": -0.15, "sharpe": 0.8},
        "bet_outcome": {
            "ann_return": "PASS" if ann_return >= 0.12 else "FAIL",
            "max_dd":     "PASS" if max_dd >= -0.15 else "FAIL",
            "sharpe":     "PASS" if sharpe >= 0.8 else "FAIL",
        },
        "deviation_notes": [
            "bars: adjusted (Polygon adjusted=true; raw not fetched separately)",
            "EXIT-A: L5 Layer 1 no longer Accumulate on daily recompute",
            "allocation: equity/30 at signal day",
            "perf optimization: L5 filter vectorized per-day (identical math)",
        ],
    }


def main():
    t0 = time.time()
    log("Loading kernel cache (467MB)...")
    with open(CACHE_FILE, "rb") as f:
        kernel_db = pickle.load(f)
    universe = [t for t in kernel_db if kernel_db[t]]
    log(f"  {len(universe)} tickers with kernel data")

    bars_db = load_bars(universe + ["SPY"])
    bars_db = {k.upper(): v for k, v in bars_db.items()}  # ensure uppercase keys

    univ_orig = sorted(pd.read_csv(UNIVERSE_CSV)["Symbol"].unique())
    n_orig = len(univ_orig)
    dropped = {"dropped_in_kernel_precompute": n_orig - len(universe)}

    spy_bars = bars_db.get("SPY")
    if spy_bars is None:
        log("STOP: SPY bars missing")
        sys.exit(1)

    trading_days = [
        d.strftime("%Y-%m-%d") for d in spy_bars.index
        if REPLAY_START <= d.strftime("%Y-%m-%d") <= REPLAY_END
    ]
    log(f"Trading days: {len(trading_days)} ({trading_days[0]} → {trading_days[-1]})")

    trades, equity_curve = run_walkforward(universe, kernel_db, bars_db, trading_days)

    log("Writing output...")
    pd.DataFrame(trades).to_csv(OUTPUT_DIR / "walkforward_bet_20260624.csv", index=False)
    pd.DataFrame(equity_curve).to_csv(
        OUTPUT_DIR / "walkforward_bet_20260624_equity_curve.csv", index=False)

    summary = compute_summary(trades, equity_curve, n_orig, len(universe), dropped)
    summary["wall_time_seconds"] = round(time.time() - t0, 1)
    with open(OUTPUT_DIR / "walkforward_bet_20260624_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    log("")
    log("=== BET RESULT ===")
    log(f"  $100k → ${summary['ending_equity']:,.0f}  ({summary['annualized_return_gross']*100:.2f}%/yr)")
    log(f"  Max DD:  {summary['max_drawdown']*100:.2f}%  [≥-15%: {summary['bet_outcome']['max_dd']}]")
    log(f"  Sharpe:  {summary['sharpe']:.3f}  [≥0.8:  {summary['bet_outcome']['sharpe']}]")
    log(f"  Ann rtn: {summary['annualized_return_gross']*100:.2f}%  [≥12%:  {summary['bet_outcome']['ann_return']}]")
    log(f"  Win rt:  {summary['win_rate']*100:.1f}%  |  Trades: {summary['n_trades']}")
    log(f"  SPY:     {summary['spy_annualized_return']*100:.2f}%/yr  ({summary['spy_max_drawdown']*100:.2f}% DD)")
    log(f"  Time:    {summary['wall_time_seconds']:.0f}s")


if __name__ == "__main__":
    main()
