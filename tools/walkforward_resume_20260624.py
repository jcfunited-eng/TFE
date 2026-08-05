#!/usr/bin/env python3
"""
Resume-only script: loads kernel cache + bars from DB, re-runs replay + output.
Skips bar backfill and kernel precompute (already done, cache at 467MB).
Fixes: SPY included in bars_db, so benchmark works.
"""
import json, pickle, sys, time
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tfe_l5_baseline import L5BaselineFilter

CACHE_FILE = Path("/workspaces/Tao_Financial_Engine/backups/walkforward_kernel_cache_20260624.pkl")
LOCAL_DSN = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
UNIVERSE_CSV = Path("/workspaces/Tao_Financial_Engine/quarantine_12k_l5_trades.csv")
OUTPUT_DIR = Path("/workspaces/Tao_Financial_Engine/tools")

REPLAY_START = "2021-04-01"
REPLAY_END   = "2026-03-24"
WARM_UP_BARS = 252
MAX_POSITIONS = 30
EXIT_F_THRESHOLD = -0.10
MIN_HOLD_DAYS = 7
N_NEIGHBORS = 30
FWD_DAYS = 20
WR_THRESHOLD = 0.65
STARTING_EQUITY = 100_000.0
MIN_PRICE = 5.0
TUPLE_FIELDS = ["D_k", "M_k", "B_k", "R_rev_k", "U_star_k", "C_k", "P_k"]


def log(m):
    print(f"[WF {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def load_bars_from_db(tickers):
    """Load bars for given tickers (always uppercase). Returns {TICKER: DataFrame}."""
    log(f"Loading bars for {len(tickers)} tickers...")
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
        df = df.set_index("bar_date").sort_index()
        result[sym] = df
    log(f"  Loaded {len(result)} tickers")
    return result


def _extract_tuple(snap):
    vals = []
    for f in TUPLE_FIELDS:
        v = snap.get(f)
        if v is None or not np.isfinite(float(v)):
            return None
        vals.append(float(v))
    return vals


def compute_neighbor_wr(current_tuple, hist_tuples, hist_returns):
    if len(hist_tuples) <= N_NEIGHBORS:
        return None
    hist = np.array(hist_tuples, dtype=float)
    curr = np.array(current_tuple, dtype=float)
    rets = np.array(hist_returns, dtype=float)
    ranges = hist.max(axis=0) - hist.min(axis=0)
    ranges = np.where(ranges < 1e-10, 1.0, ranges)
    diffs = (hist - curr) / ranges
    dists = np.sqrt((diffs ** 2).sum(axis=1))
    idx = np.argpartition(dists, N_NEIGHBORS)[:N_NEIGHBORS]
    return float((rets[idx] > 0).sum()) / N_NEIGHBORS


_l5 = L5BaselineFilter()

def is_accumulate(snap, ticker):
    row = {
        "ticker": ticker, "asset_type": "stock",
        "bar_count": snap.get("bar_count", 0),
        **{f: snap.get(f, 0) for f in
           ["S_UF","R_UF","D_k","M_k","R_rev_k","U_star_k","C_k","P_k","B_k","price"]},
    }
    return len(_l5.apply_canonical_filter(pd.DataFrame([row]))) > 0


def run_walkforward(universe, kernel_db, bars_db, trading_days):
    spy_bars = bars_db.get("SPY")
    if spy_bars is None:
        log("WARNING: SPY not in bars_db — benchmark null")

    history_db = {t: {"tuples": [], "returns": []} for t in universe}
    portfolio = {}
    equity = STARTING_EQUITY
    cash = STARTING_EQUITY
    trades = []
    equity_curve = []
    spy_start = None

    log(f"Replay: {len(trading_days)} days, {len(universe)} tickers")

    for day_idx, day in enumerate(trading_days):
        day_dt = pd.Timestamp(day)

        # Update history: add snapshots whose FWD_DAYS forward is now known
        fwd_idx = day_idx - FWD_DAYS
        if fwd_idx >= 0:
            prior_day = trading_days[fwd_idx]
            prior_dt = pd.Timestamp(prior_day)
            for ticker in universe:
                snap = kernel_db.get(ticker, {}).get(prior_day)
                if snap is None:
                    continue
                t_vals = _extract_tuple(snap)
                if t_vals is None:
                    continue
                tb = bars_db.get(ticker.upper())
                if tb is None:
                    continue
                try:
                    pc = float(tb.loc[prior_dt, "close"])
                    tc = float(tb.loc[day_dt, "close"])
                    if pc > 0 and tc > 0:
                        history_db[ticker]["tuples"].append(t_vals)
                        history_db[ticker]["returns"].append((tc - pc) / pc)
                except (KeyError, TypeError):
                    pass

        # Exit checks
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

            # EXIT-F: always fires
            if pnl_pct <= EXIT_F_THRESHOLD:
                to_exit.append((ticker, cur_close, "exit_f_catastrophic", pnl_pct))
                continue

            # EXIT-A: L5 no longer Accumulate
            snap = kernel_db.get(ticker, {}).get(day)
            if snap is not None and not is_accumulate(snap, ticker):
                if age < MIN_HOLD_DAYS and pnl_pct < 0:
                    pass  # EXIT-R9: hold
                else:
                    to_exit.append((ticker, cur_close, "exit_a_not_accumulate", pnl_pct))

        for ticker, exit_px, reason, pnl_pct in to_exit:
            pos = portfolio.pop(ticker)
            cash += pos["entry_alloc"] * (1 + pnl_pct)
            trades.append({
                "entry_date": pos["entry_date"],
                "exit_date": day,
                "ticker": ticker,
                "entry_px": pos["entry_price"],
                "exit_px": exit_px,
                "days_held": (day_dt - pd.Timestamp(pos["entry_date"])).days,
                "pnl_pct": round(pnl_pct, 6),
                "exit_reason": reason,
            })

        # Signal detection
        slots = MAX_POSITIONS - len(portfolio)
        candidates = []
        if slots > 0:
            for ticker in universe:
                if ticker in portfolio:
                    continue
                snap = kernel_db.get(ticker, {}).get(day)
                if snap is None or snap.get("price", 0) < MIN_PRICE:
                    continue
                if not is_accumulate(snap, ticker):
                    continue
                t_vals = _extract_tuple(snap)
                if t_vals is None:
                    continue
                hist = history_db[ticker]
                wr = compute_neighbor_wr(t_vals, hist["tuples"], hist["returns"])
                if wr is not None and wr >= WR_THRESHOLD:
                    candidates.append((ticker, wr, snap))

        # Enter t+1 open
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
                    "entry_date": day,
                    "entry_price": entry_px,
                    "entry_alloc": alloc,
                }

        # Mark equity
        pos_val = 0.0
        for ticker, pos in portfolio.items():
            tb = bars_db.get(ticker.upper())
            if tb is None:
                pos_val += pos["entry_alloc"]
                continue
            try:
                cur_close = float(tb.loc[day_dt, "close"])
                pos_val += pos["entry_alloc"] * (cur_close / pos["entry_price"])
            except (KeyError, TypeError):
                pos_val += pos["entry_alloc"]
        equity = cash + pos_val

        # SPY benchmark
        spy_equity = None
        if spy_bars is not None:
            try:
                spy_close = float(spy_bars.loc[day_dt, "close"])
                if spy_start is None:
                    spy_start = spy_close
                spy_equity = round(STARTING_EQUITY * spy_close / spy_start, 2)
            except (KeyError, TypeError):
                pass

        equity_curve.append({
            "date": day,
            "equity": round(equity, 2),
            "spy_equity": spy_equity,
            "n_positions": len(portfolio),
        })

        if day_idx % 50 == 0:
            log(f"  {day} | equity=${equity:,.0f} | pos={len(portfolio)} | trades={len(trades)}")

    # Force-close at end
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
    ann_return = (end_equity / STARTING_EQUITY) ** (1 / years) - 1 if years > 0 else 0.0

    running_max = ec["equity"].cummax()
    max_dd = float(((ec["equity"] - running_max) / running_max).min())

    daily_rets = ec["equity"].pct_change().dropna()
    sharpe = (daily_rets.mean() / daily_rets.std()) * np.sqrt(252) if daily_rets.std() > 0 else 0.0

    td = pd.DataFrame(trades)
    win_rate = float((td["pnl_pct"] > 0).mean()) if len(td) > 0 else 0.0
    avg_days = float(td["days_held"].mean()) if len(td) > 0 else 0.0

    spy_eq = ec["spy_equity"].dropna()
    spy_ann = spy_dd = 0.0
    if len(spy_eq) >= 2:
        spy_yrs = (spy_eq.index[-1] - spy_eq.index[0]).days / 365.25
        spy_ann = (spy_eq.iloc[-1] / spy_eq.iloc[0]) ** (1 / spy_yrs) - 1 if spy_yrs > 0 else 0.0
        spy_rm = spy_eq.cummax()
        spy_dd = float(((spy_eq - spy_rm) / spy_rm).min())

    summary = {
        "command": "TFE-CMD-WALKFORWARD-BET-WC-20260624 + AMEND-1",
        "replay_start": ec.index[0].strftime("%Y-%m-%d"),
        "replay_end":   ec.index[-1].strftime("%Y-%m-%d"),
        "starting_equity": STARTING_EQUITY,
        "ending_equity":   round(end_equity, 2),
        "annualized_return_gross": round(ann_return, 6),
        "max_drawdown":    round(max_dd, 6),
        "sharpe":          round(sharpe, 4),
        "win_rate":        round(win_rate, 4),
        "avg_days_held":   round(avg_days, 2),
        "n_trades":        len(trades),
        "n_unique_tickers": len(set(t["ticker"] for t in trades)),
        "spy_annualized_return": round(spy_ann, 6),
        "spy_max_drawdown":      round(spy_dd, 6),
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
            "bars: adjusted throughout (Polygon adjusted=true)",
            "EXIT-A: L5 Layer 1 no longer Accumulate on daily recompute",
            "allocation: equity/30 at signal day (not fixed $100k/30)",
        ],
    }
    return summary


def main():
    t0 = time.time()

    log("Loading kernel cache...")
    with open(CACHE_FILE, "rb") as f:
        kernel_db = pickle.load(f)
    universe = [t for t in kernel_db if kernel_db[t]]
    log(f"  {len(universe)} tickers with kernel data")

    # Load bars: universe tickers + SPY
    bars_db = load_bars_from_db(universe + ["SPY"])

    # Universe filtering (rebuild from kernel_db — already filtered during precompute)
    univ_df = pd.read_csv(UNIVERSE_CSV)
    universe_orig = sorted(univ_df["Symbol"].unique())
    n_orig = len(universe_orig)
    n_kept = len(universe)
    dropped = {"prefiltered_by_kernel_precompute": n_orig - n_kept}

    # Trading days from SPY
    spy_bars = bars_db.get("SPY")
    if spy_bars is None:
        log("STOP: SPY not found in bars_db")
        sys.exit(1)
    trading_days = [
        d.strftime("%Y-%m-%d")
        for d in spy_bars.index
        if REPLAY_START <= d.strftime("%Y-%m-%d") <= REPLAY_END
    ]
    log(f"Trading days: {len(trading_days)} ({trading_days[0]} → {trading_days[-1]})")

    trades, equity_curve = run_walkforward(universe, kernel_db, bars_db, trading_days)

    log("Writing output...")
    pd.DataFrame(trades).to_csv(OUTPUT_DIR / "walkforward_bet_20260624.csv", index=False)
    pd.DataFrame(equity_curve).to_csv(OUTPUT_DIR / "walkforward_bet_20260624_equity_curve.csv", index=False)

    summary = compute_summary(trades, equity_curve, n_orig, n_kept, dropped)
    summary["wall_time_seconds"] = round(time.time() - t0, 1)
    with open(OUTPUT_DIR / "walkforward_bet_20260624_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    log("")
    log("=== BET RESULT ===")
    log(f"  Start:     ${STARTING_EQUITY:,.0f}")
    log(f"  End:       ${summary['ending_equity']:,.0f}")
    log(f"  Ann rtn:   {summary['annualized_return_gross']*100:.2f}%  [target ≥12%: {summary['bet_outcome']['ann_return']}]")
    log(f"  Max DD:    {summary['max_drawdown']*100:.2f}%  [target ≥-15%: {summary['bet_outcome']['max_dd']}]")
    log(f"  Sharpe:    {summary['sharpe']:.3f}  [target ≥0.8:  {summary['bet_outcome']['sharpe']}]")
    log(f"  Win rate:  {summary['win_rate']*100:.1f}%")
    log(f"  N trades:  {summary['n_trades']}")
    log(f"  SPY ann:   {summary['spy_annualized_return']*100:.2f}%")
    log(f"  Wall time: {summary['wall_time_seconds']:.0f}s")


if __name__ == "__main__":
    main()
