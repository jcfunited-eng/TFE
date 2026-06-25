#!/usr/bin/env python3
"""
tools/walkforward_bet_20260624.py

Walk-forward backtest: TFE production stack vs SPY.
Command: TFE-CMD-WALKFORWARD-BET-WC-20260624 + AMEND-1

Bar window:   2020-04-01 → 2026-03-24 (252 warm-up + 5-yr replay + 20d tail)
Universe:     quarantine_12k_l5_trades.csv → 5,768 tickers, filtered to full coverage
Replay start: first trading day where ticker has ≥252 bars (approx 2021-04-01)
Replay end:   2026-03-24

Closed-loop protocol per day t:
  1. Kernel L0-L4 on bars[t-252:t] (precomputed)
  2. L5 baseline Layer 1 (V3 basin + Stable Titan, price≥5)
  3. Tuple proximity: 30-NN WR ≥ 0.65 from history[0:t-21]
  4. Enter t+1 open, equal weight, max 30 concurrent
  5. EXIT-A (L5 no longer Accumulate, subject to EXIT-R9 7-day guard),
     EXIT-F (-10% catastrophic floor, always fires)

Deviation notes:
  - bars: adjusted (Polygon adjusted=true); raw vs adj not segregated
    (adjusted prevents spurious kernel discontinuities from splits)
  - EXIT-A interpreted as "L5 Layer 1 no longer Accumulate on daily recompute"
    (original EXIT-A S_UF≥0.75 was removed from production)

No parameter search. No optimization. Bug-fix-only with logged diff.
"""

import json
import multiprocessing
import os
import pickle
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from tfe_l5_baseline import L5BaselineFilter, apply_canonical_filter
from uf_core.uf_structural_engine import compute_uf_structural_state

# ── Constants ────────────────────────────────────────────────────────────────
KEY = os.environ.get("MASSIVE_API_KEY", "")
LOCAL_DSN = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
REPO_ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_CSV = REPO_ROOT / "quarantine_12k_l5_trades.csv"
OUTPUT_DIR = REPO_ROOT / "tools"
CACHE_FILE = REPO_ROOT / "backups" / "walkforward_kernel_cache_20260624.pkl"

BAR_START = "2020-04-01"        # bar fetch start (warm-up begin)
REPLAY_START = "2021-04-01"     # nominal replay start (after 252d warm-up)
REPLAY_END = "2026-03-24"       # replay end / bet measurement date
WARM_UP_BARS = 252              # minimum bars before kernel is valid
MIN_PRICE = 5.0                 # L5 Layer 1 price gate
MAX_POSITIONS = 30              # portfolio capacity
EXIT_F_THRESHOLD = -0.10        # EXIT-F catastrophic floor (CH2)
MIN_HOLD_DAYS = 7               # EXIT-R9 minimum hold (calendar days)
N_NEIGHBORS = 30                # tuple proximity neighbors
FWD_DAYS = 20                   # forward return window for TP win labeling
WR_THRESHOLD = 0.65             # tuple proximity entry threshold

STARTING_EQUITY = 100_000.0     # $100k as stated in bet

TUPLE_FIELDS = ["D_k", "M_k", "B_k", "R_rev_k", "U_star_k", "C_k", "P_k"]  # 7-dim

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_BUGS = []  # bug fix log

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[WF {ts}] {msg}", flush=True)


# ── Phase 1: Bar fetch from Polygon ─────────────────────────────────────────

def fetch_bars_polygon(ticker, start=BAR_START, end="2021-04-11", retries=3):
    """Fetch daily bars from Polygon (adjusted=true). Returns list of bar dicts."""
    url = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
           f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={KEY}")
    for attempt in range(retries):
        try:
            resp = urllib.request.urlopen(url, timeout=30)
            data = json.loads(resp.read())
            if data.get("status") in ("OK", "DELAYED"):
                return data.get("results", [])
            return []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 + attempt * 5)
                continue
            return []
        except Exception:
            if attempt < retries - 1:
                time.sleep(2)
    return []


def backfill_universe(universe, start=BAR_START, end="2021-04-11", workers=20):
    """
    Fetch and insert bars for all universe tickers in the missing window.
    Uses a thread-pool approach with rate limiting.
    Returns: {ticker: bar_count}
    """
    log(f"Backfill: {len(universe)} tickers, {start} → {end}")

    conn = psycopg2.connect(LOCAL_DSN)
    conn.autocommit = True
    cur = conn.cursor()

    # Find which tickers already have bars in this window
    cur.execute("""
        SELECT UPPER(symbol), COUNT(*)
        FROM daily_bars
        WHERE bar_date >= %s AND bar_date <= %s
        GROUP BY UPPER(symbol)
    """, (start, end))
    existing = {r[0]: r[1] for r in cur.fetchall()}
    conn.close()

    # Tickers that need fetching (not already present)
    to_fetch = [t for t in universe if t.upper() not in existing or existing[t.upper()] < 100]
    already = len(universe) - len(to_fetch)
    log(f"  {already} tickers already have bars in window, fetching {len(to_fetch)}")

    results = {}
    batch_size = 50
    total = len(to_fetch)

    for i in range(0, total, batch_size):
        batch = to_fetch[i:i + batch_size]
        batch_results = {}

        for ticker in batch:
            bars = fetch_bars_polygon(ticker, start, end)
            batch_results[ticker] = bars
            time.sleep(0.05)  # ~20 req/s

        # Insert batch into DB
        conn = psycopg2.connect(LOCAL_DSN)
        conn.autocommit = True
        cur = conn.cursor()

        for ticker, bars in batch_results.items():
            n_inserted = 0
            for b in bars:
                try:
                    bar_date = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                    cur.execute("""
                        INSERT INTO daily_bars (symbol, bar_date, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, bar_date) DO NOTHING
                    """, (ticker, bar_date, b["o"], b["h"], b["l"], b["c"], b.get("v", 0)))
                    n_inserted += 1
                except Exception:
                    pass
            results[ticker] = n_inserted

        conn.close()

        done = min(i + batch_size, total)
        log(f"  backfill {done}/{total} tickers ({100*done//total}%)")

    return results


# ── Phase 2: Load all bars from DB ──────────────────────────────────────────

def load_all_bars(universe):
    """Load all daily bars for universe from DB into memory.
    Returns: {ticker: DataFrame(bar_date[date], open, close)} indexed by bar_date.
    """
    log(f"Loading bars from DB for {len(universe)} tickers...")
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()

    tickers_str = ",".join(f"'{t}'" for t in universe)
    cur.execute(f"""
        SELECT UPPER(symbol), bar_date, open, close
        FROM daily_bars
        WHERE UPPER(symbol) IN ({tickers_str})
          AND bar_date >= '2020-01-01'
          AND bar_date <= '2026-04-30'
        ORDER BY symbol, bar_date
    """)
    rows = cur.fetchall()
    conn.close()

    bars_db = {}
    for sym, bar_date, o, c in rows:
        if sym not in bars_db:
            bars_db[sym] = []
        bars_db[sym].append((bar_date, float(o or 0), float(c or 0)))

    # Convert to DataFrames indexed by date
    result = {}
    for sym, row_list in bars_db.items():
        df = pd.DataFrame(row_list, columns=["bar_date", "open", "close"])
        df["bar_date"] = pd.to_datetime(df["bar_date"])
        df = df.set_index("bar_date").sort_index()
        result[sym] = df

    log(f"  Loaded {len(result)} tickers with bar data")
    return result


# ── Phase 3: Filter universe to full coverage ────────────────────────────────

def filter_universe(universe, bars_db, bar_start=BAR_START, replay_end=REPLAY_END):
    """Keep only tickers with bars spanning bar_start → replay_end + 20d tail.
    Returns filtered list + drop histogram.
    """
    import pandas as pd
    replay_end_dt = pd.Timestamp(replay_end)
    bar_start_dt = pd.Timestamp(bar_start)
    min_replay_end = replay_end_dt + pd.Timedelta(days=30)  # 20d tail buffer

    kept = []
    dropped = {"listed_after_bar_start": 0, "delisted_before_replay_end": 0,
               "non_contiguous_bars": 0, "partial_window": 0, "no_bars": 0}

    for ticker in universe:
        df = bars_db.get(ticker.upper(), bars_db.get(ticker))
        if df is None or len(df) == 0:
            dropped["no_bars"] += 1
            continue

        first_bar = df.index[0]
        last_bar = df.index[-1]

        if first_bar > bar_start_dt + pd.Timedelta(days=90):
            dropped["listed_after_bar_start"] += 1
            continue
        if last_bar < min_replay_end:
            dropped["delisted_before_replay_end"] += 1
            continue

        # Check for major gaps (> 7 calendar days between consecutive bars)
        diffs = df.index.to_series().diff().dt.days.dropna()
        if (diffs > 7).any():
            dropped["non_contiguous_bars"] += 1
            continue

        # Must have at least WARM_UP_BARS + replay days worth of bars
        if len(df) < WARM_UP_BARS + 200:
            dropped["partial_window"] += 1
            continue

        kept.append(ticker)

    log(f"Universe filter: {len(kept)}/{len(universe)} tickers kept")
    log(f"  Dropped: {dropped}")
    return kept, dropped


# ── Phase 4: Kernel precomputation (per-ticker worker) ──────────────────────

def _precompute_ticker_kernel(args):
    """Multiprocessing worker: compute kernel for one ticker on all replay days."""
    ticker, bar_rows, trading_days_set = args

    if len(bar_rows) < WARM_UP_BARS + 10:
        return ticker, {}

    # Build indexed series
    df = pd.DataFrame(bar_rows, columns=["bar_date", "open", "close"])
    df["bar_date"] = pd.to_datetime(df["bar_date"])
    df = df.set_index("bar_date").sort_index()

    closes = df["close"]
    opens = df["open"]
    all_dates = closes.index.to_list()
    date_to_idx = {d: i for i, d in enumerate(all_dates)}

    snapshots = {}
    for i, date in enumerate(all_dates):
        date_str = date.strftime("%Y-%m-%d")
        if date_str not in trading_days_set:
            continue
        if i < WARM_UP_BARS:
            continue  # Not enough history yet

        window = closes.iloc[i - WARM_UP_BARS:i + 1]  # [t-252, t] inclusive
        if len(window) < WARM_UP_BARS:
            continue

        try:
            state = compute_uf_structural_state(window)
            l5 = state.level5
            l4 = state.level4
            snap = {
                "D_k":      float(l5.get("D_k", 0) or 0),
                "M_k":      float(l5.get("M_k", 0) or 0),
                "R_rev_k":  float(l5.get("R_rev_k", 0) or 0),
                "U_star_k": float(l5.get("U_star_k", 0) or 0),
                "C_k":      float(l5.get("C_k", 0) or 0),
                "P_k":      float(l5.get("P_k", 0) or 0),
                "B_k":      float(l5.get("B_k", 0) or 0),
                "S_UF":     float(l4.get("S_UF", 0) or 0),
                "R_UF":     float(l4.get("R_UF", 0) or 0),
                "price":    float(closes.iloc[i]),
                "open_next": float(opens.iloc[i + 1]) if i + 1 < len(opens) else float(closes.iloc[i]),
                "bar_count": i + 1,
            }
            snapshots[date_str] = snap
        except Exception:
            pass

    return ticker, snapshots


def precompute_kernels(universe, bars_db, trading_days):
    """Precompute kernel states for all tickers. Returns kernel_db dict."""
    if CACHE_FILE.exists():
        log(f"Loading kernel cache from {CACHE_FILE}")
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)

    log(f"Precomputing kernels: {len(universe)} tickers on {len(trading_days)} days ({multiprocessing.cpu_count()} workers)")
    trading_days_set = set(trading_days)

    args = []
    for ticker in universe:
        sym = ticker.upper()
        df = bars_db.get(sym, bars_db.get(ticker))
        if df is None:
            continue
        bar_rows = [(d.to_pydatetime(), o, c) for d, (o, c) in
                    zip(df.index, zip(df["open"], df["close"]))]
        args.append((ticker, bar_rows, trading_days_set))

    kernel_db = {}
    n_workers = multiprocessing.cpu_count()

    with multiprocessing.Pool(n_workers) as pool:
        for i, (ticker, snaps) in enumerate(pool.imap_unordered(_precompute_ticker_kernel, args, chunksize=5)):
            kernel_db[ticker] = snaps
            if (i + 1) % 200 == 0:
                log(f"  kernel precompute {i+1}/{len(args)}")

    log(f"Precompute complete. {sum(len(v) for v in kernel_db.values())} total snapshots")

    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(kernel_db, f)
    log(f"Cache saved to {CACHE_FILE}")

    return kernel_db


# ── Tuple proximity (Python port of tuple_proximity_engine.mjs) ──────────────

def _extract_tuple(snap):
    """Extract 7-dim tuple from a kernel snapshot. Returns None if any field missing."""
    vals = []
    for f in TUPLE_FIELDS:
        v = snap.get(f)
        if v is None or not np.isfinite(v):
            return None
        vals.append(float(v))
    return vals


def compute_neighbor_wr(current_tuple, history_tuples, history_returns):
    """
    Python port of tuple_proximity_engine.mjs computeNeighborWR.
    Per-stock normalization: range of each field across history.
    Returns neighbor WR (float) or None if insufficient history.
    """
    if len(history_tuples) <= N_NEIGHBORS:
        return None

    hist = np.array(history_tuples, dtype=float)   # (N, 7)
    curr = np.array(current_tuple, dtype=float)     # (7,)
    rets = np.array(history_returns, dtype=float)   # (N,)

    # Per-stock normalization: range of each dimension
    ranges = hist.max(axis=0) - hist.min(axis=0)
    ranges = np.where(ranges < 1e-10, 1.0, ranges)

    # Euclidean distance in normalized space
    diffs = (hist - curr) / ranges                  # (N, 7)
    dists = np.sqrt((diffs ** 2).sum(axis=1))       # (N,)

    # Partial sort: N_NEIGHBORS closest
    if len(dists) <= N_NEIGHBORS:
        neighbor_rets = rets
    else:
        idx = np.argpartition(dists, N_NEIGHBORS)[:N_NEIGHBORS]
        neighbor_rets = rets[idx]

    # Win rate = fraction with positive forward return
    return float((neighbor_rets > 0).sum()) / len(neighbor_rets)


# ── L5 filter helper ─────────────────────────────────────────────────────────

_l5_filter = L5BaselineFilter()

def is_accumulate(snap, ticker):
    """Apply L5 Layer 1 to a kernel snapshot. Returns True if Accumulate."""
    row = {
        "ticker": ticker,
        "asset_type": "stock",
        "S_UF": snap.get("S_UF", 0),
        "R_UF": snap.get("R_UF", 0),
        "D_k": snap.get("D_k", 0),
        "M_k": snap.get("M_k", 0),
        "R_rev_k": snap.get("R_rev_k", 0),
        "U_star_k": snap.get("U_star_k", 0),
        "C_k": snap.get("C_k", 0),
        "P_k": snap.get("P_k", 0),
        "B_k": snap.get("B_k", 0),
        "price": snap.get("price", 0),
        "bar_count": snap.get("bar_count", 0),
    }
    df = pd.DataFrame([row])
    result = _l5_filter.apply_canonical_filter(df)
    return len(result) > 0


# ── Phase 5: Walk-forward replay ─────────────────────────────────────────────

def run_walkforward(universe, kernel_db, bars_db, trading_days):
    """
    Execute the closed-loop walk-forward simulation.
    Returns: (trades_list, equity_curve_list)
    """
    log(f"Walk-forward: {len(trading_days)} trading days, {len(universe)} tickers, "
        f"max {MAX_POSITIONS} concurrent positions")

    # SPY bars for benchmark
    spy_bars = bars_db.get("SPY", bars_db.get("spy"))
    if spy_bars is None:
        log("WARNING: SPY bars not in DB — benchmark will be null")

    # Per-ticker history: list of (tuple, fwd_return) pairs accumulated over replay
    history_db = {t: {"tuples": [], "returns": []} for t in universe}

    # Portfolio state
    portfolio = {}  # {ticker: {entry_date, entry_price, entry_alloc, signal_date}}
    equity = STARTING_EQUITY
    cash = STARTING_EQUITY

    trades = []
    equity_curve = []
    spy_start = None

    for day_idx, day in enumerate(trading_days):
        day_dt = pd.Timestamp(day)

        # ── Step 1: Update history with snapshots whose FWD_DAYS + 1 is today ──
        # A snapshot from FWD_DAYS ago now has its forward return known (today's close)
        fwd_date_idx = day_idx - FWD_DAYS
        if fwd_date_idx >= 0:
            prior_day = trading_days[fwd_date_idx]
            prior_dt = pd.Timestamp(prior_day)
            for ticker in universe:
                snap = kernel_db.get(ticker, {}).get(prior_day)
                if snap is None:
                    continue
                t_vals = _extract_tuple(snap)
                if t_vals is None:
                    continue
                # Forward return: close[today] / close[prior_day] - 1
                ticker_bars = bars_db.get(ticker.upper(), bars_db.get(ticker))
                if ticker_bars is None:
                    continue
                try:
                    prior_close = float(ticker_bars.loc[prior_dt, "close"])
                    today_close = float(ticker_bars.loc[day_dt, "close"])
                    if prior_close > 0 and today_close > 0:
                        fwd_ret = (today_close - prior_close) / prior_close
                        history_db[ticker]["tuples"].append(t_vals)
                        history_db[ticker]["returns"].append(fwd_ret)
                except (KeyError, TypeError):
                    pass

        # ── Step 2: Exit checks on open positions ───────────────────────────
        to_exit = []
        for ticker, pos in portfolio.items():
            ticker_bars = bars_db.get(ticker.upper(), bars_db.get(ticker))
            if ticker_bars is None:
                continue
            try:
                current_close = float(ticker_bars.loc[day_dt, "close"])
            except (KeyError, TypeError):
                continue

            entry_price = pos["entry_price"]
            pnl_pct = (current_close - entry_price) / entry_price

            entry_date_dt = pd.Timestamp(pos["entry_date"])
            age_days = (day_dt - entry_date_dt).days

            # EXIT-F: catastrophic floor, always fires
            if pnl_pct <= EXIT_F_THRESHOLD:
                to_exit.append((ticker, current_close, "exit_f_catastrophic", pnl_pct))
                continue

            # EXIT-A: L5 no longer Accumulate
            snap = kernel_db.get(ticker, {}).get(day)
            if snap is not None:
                not_accumulate = not is_accumulate(snap, ticker)
                if not_accumulate:
                    # EXIT-R9: suppress if young AND losing
                    if age_days < MIN_HOLD_DAYS and pnl_pct < 0:
                        pass  # hold — EXIT-R9 guard
                    else:
                        to_exit.append((ticker, current_close, "exit_a_not_accumulate", pnl_pct))

        for ticker, exit_price, reason, pnl_pct in to_exit:
            pos = portfolio.pop(ticker)
            pnl_dollar = pos["entry_alloc"] * pnl_pct
            cash += pos["entry_alloc"] + pnl_dollar
            entry_dt = pd.Timestamp(pos["entry_date"])
            days_held = (day_dt - entry_dt).days
            trades.append({
                "entry_date": pos["entry_date"],
                "exit_date": day,
                "ticker": ticker,
                "entry_px": pos["entry_price"],
                "exit_px": exit_price,
                "days_held": days_held,
                "pnl_pct": pnl_pct,
                "exit_reason": reason,
            })

        # ── Step 3: Signal detection — find new Accumulate candidates ───────
        slots_available = MAX_POSITIONS - len(portfolio)
        candidates = []

        if slots_available > 0:
            for ticker in universe:
                if ticker in portfolio:
                    continue
                snap = kernel_db.get(ticker, {}).get(day)
                if snap is None:
                    continue
                if snap.get("price", 0) < MIN_PRICE:
                    continue
                if not is_accumulate(snap, ticker):
                    continue

                # Tuple proximity
                t_vals = _extract_tuple(snap)
                if t_vals is None:
                    continue
                hist = history_db[ticker]
                wr = compute_neighbor_wr(t_vals, hist["tuples"], hist["returns"])
                if wr is None:
                    continue
                if wr >= WR_THRESHOLD:
                    candidates.append((ticker, wr, snap))

        # ── Step 4: Enter at t+1 open ────────────────────────────────────────
        if candidates and slots_available > 0:
            # Sort by neighbor WR (highest first)
            candidates.sort(key=lambda x: -x[1])
            for ticker, wr, snap in candidates[:slots_available]:
                # Entry price = t+1 open
                entry_price = snap.get("open_next", snap.get("price", 0))
                if entry_price <= 0:
                    continue
                # Equal weight allocation
                alloc = equity / MAX_POSITIONS
                if alloc > cash:
                    continue  # not enough cash
                cash -= alloc
                portfolio[ticker] = {
                    "entry_date": day,
                    "entry_price": entry_price,
                    "entry_alloc": alloc,
                }

        # ── Step 5: Mark equity ──────────────────────────────────────────────
        position_value = 0.0
        for ticker, pos in portfolio.items():
            ticker_bars = bars_db.get(ticker.upper(), bars_db.get(ticker))
            if ticker_bars is None:
                position_value += pos["entry_alloc"]
                continue
            try:
                current_close = float(ticker_bars.loc[day_dt, "close"])
                entry_price = pos["entry_price"]
                if entry_price > 0:
                    position_value += pos["entry_alloc"] * (current_close / entry_price)
                else:
                    position_value += pos["entry_alloc"]
            except (KeyError, TypeError):
                position_value += pos["entry_alloc"]

        equity = cash + position_value

        # SPY benchmark
        spy_close = None
        if spy_bars is not None:
            try:
                spy_close = float(spy_bars.loc[day_dt, "close"])
            except (KeyError, TypeError):
                pass

        if spy_close is not None and spy_start is None:
            spy_start = spy_close
        spy_equity = (STARTING_EQUITY * spy_close / spy_start) if (spy_close and spy_start) else None

        # Equal-weight basket benchmark (SPY proxy for now; see summary note)
        equity_curve.append({
            "date": day,
            "equity": round(equity, 2),
            "spy_equity": round(spy_equity, 2) if spy_equity else None,
            "n_positions": len(portfolio),
        })

        if day_idx % 50 == 0:
            log(f"  replay {day} | equity=${equity:,.0f} | positions={len(portfolio)} | trades={len(trades)}")

    # Force-close any open positions at replay end
    last_day = trading_days[-1]
    last_day_dt = pd.Timestamp(last_day)
    for ticker, pos in list(portfolio.items()):
        ticker_bars = bars_db.get(ticker.upper(), bars_db.get(ticker))
        exit_price = pos["entry_price"]  # default fallback
        if ticker_bars is not None:
            try:
                exit_price = float(ticker_bars.loc[last_day_dt, "close"])
            except (KeyError, TypeError):
                pass
        pnl_pct = (exit_price - pos["entry_price"]) / pos["entry_price"]
        entry_dt = pd.Timestamp(pos["entry_date"])
        trades.append({
            "entry_date": pos["entry_date"],
            "exit_date": last_day,
            "ticker": ticker,
            "entry_px": pos["entry_price"],
            "exit_px": exit_price,
            "days_held": (last_day_dt - entry_dt).days,
            "pnl_pct": pnl_pct,
            "exit_reason": "replay_end_close",
        })

    log(f"Walk-forward complete: {len(trades)} trades, final equity=${equity:,.0f}")
    return trades, equity_curve


# ── Phase 6: Stats ────────────────────────────────────────────────────────────

def compute_summary(trades, equity_curve, universe_orig, universe_kept, dropped):
    """Compute summary statistics."""
    ec = pd.DataFrame(equity_curve)
    ec["date"] = pd.to_datetime(ec["date"])
    ec = ec.set_index("date")

    if len(ec) < 2:
        return {"error": "insufficient equity curve data"}

    # Annualized return
    start_equity = STARTING_EQUITY
    end_equity = ec["equity"].iloc[-1]
    n_days = (ec.index[-1] - ec.index[0]).days
    years = n_days / 365.25
    ann_return = (end_equity / start_equity) ** (1 / years) - 1 if years > 0 else 0.0

    # Max drawdown
    running_max = ec["equity"].cummax()
    drawdowns = (ec["equity"] - running_max) / running_max
    max_dd = float(drawdowns.min())

    # Daily returns for Sharpe
    daily_rets = ec["equity"].pct_change().dropna()
    sharpe = (daily_rets.mean() / daily_rets.std()) * np.sqrt(252) if daily_rets.std() > 0 else 0.0

    # Trade stats
    td = pd.DataFrame(trades)
    win_rate = float((td["pnl_pct"] > 0).mean()) if len(td) > 0 else 0.0
    avg_days_held = float(td["days_held"].mean()) if len(td) > 0 else 0.0

    # SPY stats
    spy_eq = ec["spy_equity"].dropna()
    spy_ann = 0.0
    spy_dd = 0.0
    if len(spy_eq) >= 2:
        spy_years = (spy_eq.index[-1] - spy_eq.index[0]).days / 365.25
        spy_ann = (spy_eq.iloc[-1] / spy_eq.iloc[0]) ** (1 / spy_years) - 1 if spy_years > 0 else 0.0
        spy_running_max = spy_eq.cummax()
        spy_dd = float(((spy_eq - spy_running_max) / spy_running_max).min())

    return {
        "command": "TFE-CMD-WALKFORWARD-BET-WC-20260624 + AMEND-1",
        "replay_start": ec.index[0].strftime("%Y-%m-%d"),
        "replay_end": ec.index[-1].strftime("%Y-%m-%d"),
        "starting_equity": STARTING_EQUITY,
        "ending_equity": round(end_equity, 2),
        "annualized_return_gross": round(ann_return, 6),
        "max_drawdown": round(max_dd, 6),
        "sharpe": round(sharpe, 4),
        "win_rate": round(win_rate, 4),
        "avg_days_held": round(avg_days_held, 2),
        "n_trades": len(trades),
        "n_unique_tickers": len(set(t["ticker"] for t in trades)),
        "spy_annualized_return": round(spy_ann, 6),
        "spy_max_drawdown": round(spy_dd, 6),
        "eq_basket_annualized_return": "N/A — SPY used as eq basket proxy",
        "universe_original": len(universe_orig),
        "universe_kept": len(universe_kept),
        "universe_dropped": sum(dropped.values()),
        "dropped_reasons": dropped,
        "bet_target": {"ann_return": 0.12, "max_dd": -0.15, "sharpe": 0.8},
        "bet_outcome": {
            "ann_return": "PASS" if ann_return >= 0.12 else "FAIL",
            "max_dd": "PASS" if max_dd >= -0.15 else "FAIL",
            "sharpe": "PASS" if sharpe >= 0.8 else "FAIL",
        },
        "deviation_notes": [
            "bars: adjusted throughout (Polygon adjusted=true; raw not fetched separately)",
            "EXIT-A: interpreted as L5 Layer 1 no longer signals Accumulate on daily recompute",
            "entry allocation: equity/30 at signal day equity level (not fixed $100k/30)",
            "eq_basket_annualized_return: SPY used as proxy (full equal-weight basket not computed)",
        ],
        "bug_fixes": LOG_BUGS,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not KEY:
        log("STOP: MASSIVE_API_KEY not set in .env")
        sys.exit(1)

    t_start = time.time()

    # Load universe
    univ_df = pd.read_csv(UNIVERSE_CSV)
    universe_orig = sorted(univ_df["Symbol"].unique())
    log(f"Universe: {len(universe_orig)} tickers from {UNIVERSE_CSV.name}")

    # Ensure SPY is always in the load set (for benchmark)
    load_set = list(set(universe_orig) | {"SPY"})

    # ── Phase 1: Backfill missing bars (2020-04-01 → 2021-04-11) ────────────
    log("=== Phase 1: Bar backfill ===")
    backfill_results = backfill_universe(load_set, BAR_START, "2021-04-11")
    n_fetched = sum(1 for v in backfill_results.values() if v > 0)
    log(f"Backfill: {n_fetched} tickers had new bars inserted")

    # ── Phase 2: Load all bars ────────────────────────────────────────────────
    log("=== Phase 2: Load bars ===")
    bars_db = load_all_bars(load_set)

    # Normalize keys to uppercase
    bars_db = {k.upper(): v for k, v in bars_db.items()}

    # ── Phase 3: Filter universe ──────────────────────────────────────────────
    log("=== Phase 3: Filter universe ===")
    # Remap lookup to uppercase
    bars_db_lookup = bars_db
    universe_kept, dropped = filter_universe(universe_orig, bars_db_lookup)
    n_backfill_attempted = len(load_set)
    n_tickers_full_history = len(universe_kept)

    # ── Phase 4: Build trading days list ────────────────────────────────────
    # Get all trading days in the replay window from SPY bars
    spy_bars = bars_db.get("SPY")
    if spy_bars is None:
        log("STOP: SPY bars not found — cannot build trading calendar")
        sys.exit(1)

    trading_days = [
        d.strftime("%Y-%m-%d")
        for d in spy_bars.index
        if REPLAY_START <= d.strftime("%Y-%m-%d") <= REPLAY_END
    ]
    log(f"Replay calendar: {len(trading_days)} trading days ({trading_days[0]} → {trading_days[-1]})")

    # ── Phase 5: Precompute kernels ──────────────────────────────────────────
    log("=== Phase 5: Kernel precomputation ===")
    # Build bars_db in format expected by worker: list of (date, open, close) tuples
    bars_for_workers = {}
    for ticker in universe_kept + ["SPY"]:
        sym = ticker.upper()
        df = bars_db.get(sym)
        if df is not None:
            bars_for_workers[ticker] = [(d.to_pydatetime(), o, c)
                                         for d, o, c in zip(df.index, df["open"], df["close"])]

    # Temporarily store bars_db in correct format for kernel worker
    bars_db_worker = {}
    for ticker in universe_kept:
        sym = ticker.upper()
        df = bars_db.get(sym)
        if df is not None:
            bars_db_worker[ticker] = df

    kernel_db = precompute_kernels(universe_kept, bars_db_worker, trading_days)

    # ── Phase 6: Walk-forward replay ─────────────────────────────────────────
    log("=== Phase 6: Walk-forward replay ===")
    trades, equity_curve = run_walkforward(universe_kept, kernel_db, bars_db_worker, trading_days)

    # ── Phase 7: Output ───────────────────────────────────────────────────────
    log("=== Phase 7: Output ===")

    # Per-trade log
    trades_path = OUTPUT_DIR / "walkforward_bet_20260624.csv"
    pd.DataFrame(trades).to_csv(trades_path, index=False)
    log(f"  trades → {trades_path}")

    # Equity curve
    ec_path = OUTPUT_DIR / "walkforward_bet_20260624_equity_curve.csv"
    pd.DataFrame(equity_curve).to_csv(ec_path, index=False)
    log(f"  equity curve → {ec_path}")

    # Summary
    summary = compute_summary(trades, equity_curve, universe_orig, universe_kept, dropped)
    summary["n_tickers_attempted"] = n_backfill_attempted
    summary["n_tickers_with_full_history"] = n_tickers_full_history
    summary["n_tickers_dropped"] = n_backfill_attempted - n_tickers_full_history
    summary["wall_time_seconds"] = round(time.time() - t_start, 1)

    summary_path = OUTPUT_DIR / "walkforward_bet_20260624_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log(f"  summary → {summary_path}")

    log("")
    log("=== RESULT ===")
    log(f"  Annualized return: {summary['annualized_return_gross']*100:.2f}%  (target ≥12%: {summary['bet_outcome']['ann_return']})")
    log(f"  Max drawdown:      {summary['max_drawdown']*100:.2f}%  (target ≥-15%: {summary['bet_outcome']['max_dd']})")
    log(f"  Sharpe:            {summary['sharpe']:.3f}  (target ≥0.8: {summary['bet_outcome']['sharpe']})")
    log(f"  Win rate:          {summary['win_rate']*100:.1f}%")
    log(f"  N trades:          {summary['n_trades']}")
    log(f"  SPY annualized:    {summary['spy_annualized_return']*100:.2f}%")
    log(f"  Wall time:         {summary['wall_time_seconds']:.0f}s")


if __name__ == "__main__":
    main()
