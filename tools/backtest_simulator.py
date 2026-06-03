"""
tools/backtest_simulator.py

Full-lifecycle backtest simulator for the current production system (task 522).

Implements:
- Entry: tuple-proximity decision, CH2 strategist gates, 3WA/1+3/standard tagging
- Sizing: computeSizing per signal_class (3WA 3.5%, W1+3 2.5%, TP_HIGH 2.5%, TP_MED 1.5%)
- Exit: EXIT-F (-10%), EXIT-S (-2% to -10% assessment), EXIT-A (S_UF >= 0.75),
        EXIT-B (D_k collapse), EXIT-R9 (7-day minimum hold), EXIT-H (structural harvest),
        EXIT-C (tau exhaustion)
- Market hours: kills deferred when market closed (Part A fix)
- Fill: next-session open price

Data sources:
- backtest_kernel_snapshots (current-kernel daily walkforward, April 7 - May 29 2026)
- runtime_decisions_history backfill (neighbor history, Sep 2025 - April 6 2026)
- daily_bars (prices for fills and returns)
- species_profiles (validation DB, for 3WA tagging)

Usage:
    python3 tools/backtest_simulator.py [--mode comparison1|comparison2]
"""

import sys, os, json, math, time
from collections import defaultdict
from datetime import date, timedelta, datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Constants (matching production l5_unified_shadow.mjs) ─────────────
SIZING_3WA = 0.035
SIZING_W1_W3 = 0.025
SIZING_TP_HIGH = 0.025
SIZING_TP_MED = 0.015
EPOCH_UPHEAVAL_SIZING_MULT = 0.5

ENTRY_TP_THRESHOLD = 0.65
EXIT_THRESHOLD = 0.40

EXIT_LOSS_FLOOR = -0.10
EXIT_ASSESSMENT_LOW = -0.02
EXIT_CUT_WR = 0.50
EXIT_HOLD_WR = 0.55

MIN_HOLD_DAYS = 7
MAX_POSITIONS = 30
REGIME_DEFENSIVE_MULT = 0.5

CH2_S_UF_MIN = 0.50
CH2_S_UF_MAX = 0.75
CH2_BAR_COUNT_MIN = 21
CH2_DK_REQUIRED = 1
NEW_LISTING_BAR_MAX = 20

N_NEIGHBORS = 30
FORWARD_DAYS = 20
TUPLE_FIELDS = ["D_k", "M_k", "B_k", "R_rev_k", "U_star_k", "C_k", "P_k"]

MIN_SHARE_PRICE = 5.0
MIN_SHARES = 1

# ── Data classes ──────────────────────────────────────────────────────
@dataclass
class Position:
    ticker: str
    signal_class: str
    entry_date: date
    entry_price: float
    shares: int
    sizing_pct: float
    neighbor_wr: Optional[float] = None
    spy_dk_at_entry: int = 0
    tau_in: int = 0  # bars since structural quiescence started

    def pnl_pct(self, current_price: float) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (current_price - self.entry_price) / self.entry_price

    def age_days(self, current_date: date) -> int:
        return (current_date - self.entry_date).days

@dataclass
class ClosedTrade:
    ticker: str
    signal_class: str
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    shares: int
    sizing_pct: float
    exit_reason: str
    pnl: float
    pnl_pct: float
    hold_days: int
    neighbor_wr: Optional[float] = None


# ── Tuple-proximity computation ──────────────────────────────────────
def extract_tuple(snap):
    vals = []
    for f in TUPLE_FIELDS:
        v = snap.get(f)
        if v is None:
            return None
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            return None
    return vals


def compute_neighbor_wr(current_tuple, history_tuples, history_returns):
    """Pure Python equivalent of tuple_proximity_engine.mjs computeNeighborWR."""
    if len(history_tuples) <= N_NEIGHBORS:
        return None

    ht = np.array(history_tuples)
    ranges = ht.max(axis=0) - ht.min(axis=0)
    ranges[ranges < 1e-10] = 1.0

    ct = np.array(current_tuple)
    diffs = (ht - ct) / ranges
    dists = np.sqrt((diffs ** 2).sum(axis=1))
    idx = np.argsort(dists)[:N_NEIGHBORS]
    wins = sum(1 for i in idx if history_returns[i] > 0)
    return wins / N_NEIGHBORS


class BacktestSimulator:
    def __init__(self, start_equity=100_000.0):
        self.conn = psycopg2.connect(
            host="/var/run/postgresql", port=5432,
            user="postgres", dbname="tfe_validation",
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        self.start_equity = start_equity
        self.cash = start_equity
        self.positions: List[Position] = []
        self.closed_trades: List[ClosedTrade] = []
        self.equity_curve: List[dict] = []
        self.daily_decisions: List[dict] = []

        # Pre-load data
        self._load_data()

    def _load_data(self):
        cur = self.conn.cursor()
        print("Loading data...")

        # Trading dates
        cur.execute("""
            SELECT DISTINCT bar_date FROM daily_bars
            WHERE bar_date >= '2026-04-07' AND bar_date <= '2026-05-29'
            ORDER BY bar_date
        """)
        all_dates = [r["bar_date"] for r in cur.fetchall()]
        # Filter to weekdays only (actual trading days)
        self.trading_dates = [d for d in all_dates if d.weekday() < 5]
        print(f"  Trading dates: {len(self.trading_dates)}")

        # Daily bars (for fills and current prices)
        cur.execute("SELECT symbol, bar_date, open, close FROM daily_bars ORDER BY symbol, bar_date")
        self.bars = defaultdict(list)
        for r in cur.fetchall():
            self.bars[r["symbol"]].append(r)
        self.bar_close = {}  # (ticker, date) -> close
        self.bar_open = {}   # (ticker, date) -> open
        for ticker, blist in self.bars.items():
            for b in blist:
                self.bar_close[(ticker, b["bar_date"])] = float(b["close"])
                if b["open"]:
                    self.bar_open[(ticker, b["bar_date"])] = float(b["open"])
        print(f"  Bars: {sum(len(v) for v in self.bars.values())} across {len(self.bars)} tickers")

        # Kernel snapshots (from walkforward)
        cur.execute("SELECT ticker, bar_date, snapshot_json FROM backtest_kernel_snapshots")
        self.snapshots = {}  # (ticker, date) -> snapshot
        for r in cur.fetchall():
            snap = r["snapshot_json"] if isinstance(r["snapshot_json"], dict) else json.loads(r["snapshot_json"])
            self.snapshots[(r["ticker"], r["bar_date"])] = snap
        print(f"  Kernel snapshots: {len(self.snapshots)}")

        # Deep neighbor history (daily kernel, Apr 2025 - Mar 2026)
        # with pre-computed forward returns and exit dates for leak-free filtering
        cur.execute("""
            SELECT ticker, bar_date, snapshot_json, fwd_return_20d, fwd_exit_date
            FROM backtest_neighbor_history
            WHERE fwd_return_20d IS NOT NULL AND fwd_exit_date IS NOT NULL
            ORDER BY ticker, bar_date
        """)
        self.neighbor_history = defaultdict(list)
        for r in cur.fetchall():
            snap = r["snapshot_json"] if isinstance(r["snapshot_json"], dict) else json.loads(r["snapshot_json"])
            self.neighbor_history[r["ticker"]].append({
                "date": r["bar_date"],
                "snap": snap,
                "fwd_return": float(r["fwd_return_20d"]),
                "fwd_exit_date": r["fwd_exit_date"],
            })
        print(f"  Deep neighbor history: {sum(len(v) for v in self.neighbor_history.values())} rows, {len(self.neighbor_history)} tickers")

        # Species profiles
        cur.execute("SELECT ticker, classification FROM species_profiles")
        self.species = {r["ticker"]: r["classification"] for r in cur.fetchall()}
        print(f"  Species profiles: {len(self.species)} tickers")

        # SPY snapshots
        self.spy_snapshots = {}
        for (ticker, d), snap in self.snapshots.items():
            if ticker == "SPY":
                self.spy_snapshots[d] = snap
        print(f"  SPY snapshots: {len(self.spy_snapshots)} dates")

        cur.close()

    def _get_spy_dk(self, d: date) -> int:
        snap = self.spy_snapshots.get(d)
        if snap:
            return int(snap.get("D_k", 0))
        # Fallback: find nearest prior date
        for delta in range(1, 5):
            prev = d - timedelta(days=delta)
            snap = self.spy_snapshots.get(prev)
            if snap:
                return int(snap.get("D_k", 0))
        return 0

    def _get_next_open(self, ticker: str, after_date: date) -> Optional[tuple]:
        """Get (date, open_price) for the first trading day after after_date."""
        for delta in range(1, 10):
            d = after_date + timedelta(days=delta)
            price = self.bar_open.get((ticker, d))
            if price and price > 0:
                return (d, price)
        return None

    def _compute_tp_wr(self, ticker: str, decision_date: date, current_snap: dict) -> Optional[float]:
        """Compute tuple-proximity neighbor WR, leak-free, from deep neighbor pool."""
        current_tuple = extract_tuple(current_snap)
        if current_tuple is None:
            return None

        history_tuples = []
        history_returns = []

        # Deep neighbor pool: pre-computed forward returns and exit dates.
        # Leak-free filter: only include neighbors whose forward window
        # fully resolved before the decision date.
        for h in self.neighbor_history.get(ticker, []):
            if h["fwd_exit_date"] >= decision_date:
                continue  # Leak-free: skip neighbors whose outcome extends past decision
            t = extract_tuple(h["snap"])
            if t is None:
                continue
            history_tuples.append(t)
            history_returns.append(h["fwd_return"])

        return compute_neighbor_wr(current_tuple, history_tuples, history_returns)

    def _compute_tau_out(self, ticker: str, entry_date: date) -> int:
        """Compute τ_out from daily D_k snapshots, matching production logic.
        τ_in = consecutive days with D_k != 1 looking backward from entry.
        τ_out = floor(τ_in / 3)."""
        compression_days = 0
        phase = "expansion"
        # Walk backward from entry_date through snapshots
        for delta in range(1, 400):
            d = entry_date - timedelta(days=delta)
            snap = self.snapshots.get((ticker, d))
            if snap is None:
                # Also check neighbor history
                for h in self.neighbor_history.get(ticker, []):
                    if h["date"] == d:
                        snap = h["snap"]
                        break
            if snap is None:
                continue
            dk = int(snap.get("D_k", 0))
            if phase == "expansion":
                if dk != 1:
                    phase = "compression"
                    compression_days += 1
            else:
                if dk != 1:
                    compression_days += 1
                else:
                    break
        return compression_days // 3

    def _compute_sizing_tuple(self, ticker: str, decision_date, current_snap: dict,
                               spy_dk: int = 0) -> tuple:
        """Tuple-sourced sizing from neighbor return distribution.

        For each pick, takes the 30 nearest resolved neighbors and their
        forward returns. Computes distance-weighted central tendency and
        dispersion. Size proportional to (tendency × consistency-weight).

        Returns (raw_score, neighbor_returns) where raw_score is the
        unnormalized conviction. Caller normalizes across all day's picks
        to fit within cash ceiling.
        """
        current_tuple = extract_tuple(current_snap)
        if current_tuple is None:
            return (0.0, [])

        # Get leak-free neighbors with returns
        history_tuples = []
        history_returns = []
        for h in self.neighbor_history.get(ticker, []):
            if h["fwd_exit_date"] >= decision_date:
                continue
            t = extract_tuple(h["snap"])
            if t is None:
                continue
            history_tuples.append(t)
            history_returns.append(h["fwd_return"])

        if len(history_tuples) <= N_NEIGHBORS:
            return (0.0, [])

        # Compute distances and find 30 nearest
        ht = np.array(history_tuples)
        ranges = ht.max(axis=0) - ht.min(axis=0)
        ranges[ranges < 1e-10] = 1.0
        ct = np.array(current_tuple)
        diffs = (ht - ct) / ranges
        dists = np.sqrt((diffs ** 2).sum(axis=1))
        idx = np.argsort(dists)[:N_NEIGHBORS]

        neighbor_dists = dists[idx]
        neighbor_rets = np.array([history_returns[i] for i in idx])

        # Distance weights: inverse distance, normalized
        # Add small epsilon to avoid division by zero on exact matches
        inv_dists = 1.0 / (neighbor_dists + 1e-8)
        weights = inv_dists / inv_dists.sum()

        # Weighted central tendency of neighbor returns
        weighted_mean = np.sum(weights * neighbor_rets)

        # Weighted dispersion (consistency)
        weighted_var = np.sum(weights * (neighbor_rets - weighted_mean) ** 2)
        weighted_std = np.sqrt(weighted_var)

        # Consistency weight: tight distribution → high weight, scattered → low
        # Use 1 / (1 + std) so consistency ranges from ~0.5 (scattered) to ~1.0 (tight)
        consistency = 1.0 / (1.0 + weighted_std)

        # Raw conviction score: central tendency × consistency
        # Only positive tendency contributes to sizing (negative = don't enter, but
        # the entry gate already filtered on WR >= 0.65, so tendency should be positive)
        raw_score = max(0.0, weighted_mean) * consistency

        return (raw_score, neighbor_rets.tolist())

    def _regime_allows_entry(self, spy_dk: int) -> bool:
        """Regime does not veto qualified picks. Bounded by MAX_POSITIONS
        and available cash only. No arbitrary defensive multiplier."""
        return len(self.positions) < MAX_POSITIONS

    def _evaluate_entries(self, d: date) -> List[dict]:
        """Evaluate all tickers for entry on this date."""
        entries = []
        spy_dk = self._get_spy_dk(d)

        # Weekend/holiday block
        if d.weekday() >= 5:
            return []

        # Regime gate
        if not self._regime_allows_entry(spy_dk):
            return []

        # Get all snapshots for this date
        open_tickers = {p.ticker for p in self.positions}

        for (ticker, snap_date), snap in self.snapshots.items():
            if snap_date != d:
                continue
            if ticker == "SPY":
                continue
            if ticker in open_tickers:
                continue

            dk = snap.get("D_k")
            s_uf = snap.get("S_UF")
            bar_count = snap.get("bar_count")
            price = snap.get("price", 0)

            if dk is None or s_uf is None or bar_count is None:
                continue
            if price < MIN_SHARE_PRICE:
                continue

            # CH2 gate: Accumulate-direction, mid S_UF, established
            dk = int(dk)
            s_uf = float(s_uf)
            bar_count = int(bar_count)

            # Compute tuple-proximity WR
            wr = self._compute_tp_wr(ticker, d, snap)

            # Check if this is an Accumulate signal via tuple-proximity
            if wr is None or wr < ENTRY_TP_THRESHOLD:
                continue

            # Tuple-only entry: TP WR >= 0.65 is the entry decision.
            # No S_UF band gate. Per-ticker D_k stays (it's a tuple field).
            # 3WA/1+3 classification still applies for new listings.
            is_new_listing = bar_count <= NEW_LISTING_BAR_MAX
            species = self.species.get(ticker, "unknown")
            is_calm = species == "calm"

            if is_new_listing and s_uf > 0 and spy_dk == 1:
                if is_calm:
                    signal_class = "3WA"
                else:
                    signal_class = "1+3"
            elif bar_count >= CH2_BAR_COUNT_MIN:
                # Tuple-only: any established stock with TP WR >= 0.65 enters.
                # No S_UF band restriction. D_k is read by the tuple, not as
                # a scalar gate — the TP engine already incorporates D_k in
                # the 7-dim distance computation.
                signal_class = "CH2"
            else:
                continue

            # Tuple-sourced sizing: conviction from neighbor return distribution
            raw_score, neighbor_rets = self._compute_sizing_tuple(ticker, d, snap, spy_dk=spy_dk)
            if raw_score <= 0:
                continue  # Negative or zero conviction — skip

            entries.append({
                "ticker": ticker,
                "signal_class": signal_class,
                "neighbor_wr": wr,
                "raw_score": raw_score,
                "neighbor_rets": neighbor_rets,
                "price": price,
                "spy_dk": spy_dk,
                "d_k": dk,
                "s_uf": s_uf,
                "bar_count": bar_count,
            })

        return entries

    def _evaluate_exits(self, d: date) -> List[tuple]:
        """Evaluate all positions for exit. Returns list of (position, exit_reason)."""
        exits = []

        if d.weekday() >= 5:
            return []  # Market closed

        for pos in self.positions:
            current_price = self.bar_close.get((pos.ticker, d))
            if current_price is None or current_price <= 0:
                continue

            pnl_pct = pos.pnl_pct(current_price)
            age = pos.age_days(d)
            is_young = age < MIN_HOLD_DAYS

            # EXIT-F: catastrophic floor
            if pnl_pct <= EXIT_LOSS_FLOOR:
                if is_young and pnl_pct < 0:
                    continue  # R9 blocks losing exits on young positions
                exits.append((pos, "EXIT-F", current_price))
                continue

            # EXIT-S: structural assessment in -2% to -10% zone
            if pnl_pct <= EXIT_ASSESSMENT_LOW:
                # Need current neighbor WR
                snap = self.snapshots.get((pos.ticker, d))
                wr = None
                if snap:
                    wr = self._compute_tp_wr(pos.ticker, d, snap)

                if wr is not None and wr <= EXIT_CUT_WR:
                    if is_young and pnl_pct < 0:
                        continue  # R9
                    exits.append((pos, "EXIT-S_CUT", current_price))
                    continue
                # HOLD_STRUCTURAL or AMBIGUOUS — don't exit

            # Channel-specific exits (CH2)
            if pos.signal_class == "CH2":
                snap = self.snapshots.get((pos.ticker, d))
                if snap:
                    current_suf = float(snap.get("S_UF", 0))
                    current_dk = int(snap.get("D_k", 0))

                    # EXIT-A: acceleration complete
                    if current_suf >= 0.75:
                        exits.append((pos, "EXIT-A", current_price))
                        continue

                    # EXIT-B: D_k collapse
                    if current_dk != 1:
                        if is_young and pnl_pct < 0:
                            continue  # R9
                        exits.append((pos, "EXIT-B", current_price))
                        continue

            # EXIT-C: τ exhaustion — position age exceeds τ_out
            tau_out_c = self._compute_tau_out(pos.ticker, pos.entry_date)
            if tau_out_c > 0 and age > tau_out_c:
                if is_young and pnl_pct < 0:
                    pass  # R9 blocks
                else:
                    exits.append((pos, "EXIT-C", current_price))
                    continue

            # EXIT-H: structural harvest — kernel-sourced exhaustion trigger.
            # Fires when the position is profitable AND the kernel perceives
            # structural exhaustion (the move is rolling over).
            #
            # Structural exhaustion signals (need ≥2 active):
            #   - B_k <= B_k at entry (breathing not expanding beyond entry)
            #   - D_k < D_k at entry (direction weakened)
            #   - M_k < 0 (momentum negative, decelerating)
            #   - neighbor_wr < entry neighbor_wr (coupled state deteriorated)
            #
            # τ_out timer is backstop only: if age > τ_out AND profitable, harvest
            # regardless (energy budget spent even if kernel still reads expansion).
            if pnl_pct > 0:
                snap = self.snapshots.get((pos.ticker, d))
                if snap:
                    # Entry-state comparison
                    entry_snap = self.snapshots.get((pos.ticker, pos.entry_date))
                    entry_bk = float(entry_snap.get("B_k", 0)) if entry_snap else 0
                    entry_dk = int(entry_snap.get("D_k", 0)) if entry_snap else 0
                    entry_wr = pos.neighbor_wr if pos.neighbor_wr else 0.65

                    current_bk = float(snap.get("B_k", 0))
                    current_dk = int(snap.get("D_k", 0))
                    current_mk = float(snap.get("M_k", 0))

                    # Current WR (expensive — only compute if other signals suggest exhaustion)
                    exhaustion_signals = 0
                    if current_bk <= entry_bk:
                        exhaustion_signals += 1  # breathing not expanding
                    if current_dk < entry_dk:
                        exhaustion_signals += 1  # direction weakened
                    if current_mk < 0:
                        exhaustion_signals += 1  # momentum negative

                    # Only compute WR if we need the 4th signal to reach 2
                    if exhaustion_signals < 2:
                        current_wr = self._compute_tp_wr(pos.ticker, d, snap)
                        if current_wr is not None and current_wr < entry_wr:
                            exhaustion_signals += 1

                    if exhaustion_signals >= 2:
                        exits.append((pos, "EXIT-H_STRUCTURAL", current_price))
                        continue

                # τ_out backstop: timer expired + profitable = harvest regardless
                if pnl_pct > 0:
                    tau_out = self._compute_tau_out(pos.ticker, pos.entry_date)
                    if tau_out > 0 and age > tau_out:
                        exits.append((pos, "EXIT-H_TIMER", current_price))
                        continue
                    elif tau_out == 0 and age >= 7 and pnl_pct > 0.05:
                        exits.append((pos, "EXIT-H_FALLBACK", current_price))
                        continue

        return exits

    def run(self):
        """Run the full simulation."""
        print(f"\n{'='*60}")
        print(f"BACKTEST SIMULATION: ${self.start_equity:,.0f}")
        print(f"Period: {self.trading_dates[0]} to {self.trading_dates[-1]}")
        print(f"{'='*60}\n")

        for di, d in enumerate(self.trading_dates):
            if d.weekday() >= 5:
                continue  # Skip weekends

            # 1. Evaluate exits first (before entries)
            exit_list = self._evaluate_exits(d)
            for pos, reason, exit_price in exit_list:
                pnl = (exit_price - pos.entry_price) * pos.shares
                pnl_pct = pos.pnl_pct(exit_price)
                hold_days = pos.age_days(d)

                self.closed_trades.append(ClosedTrade(
                    ticker=pos.ticker, signal_class=pos.signal_class,
                    entry_date=pos.entry_date, entry_price=pos.entry_price,
                    exit_date=d, exit_price=exit_price,
                    shares=pos.shares, sizing_pct=pos.sizing_pct,
                    exit_reason=reason, pnl=pnl, pnl_pct=pnl_pct,
                    hold_days=hold_days, neighbor_wr=pos.neighbor_wr,
                ))
                self.cash += exit_price * pos.shares
                self.positions.remove(pos)

            # 2. Evaluate entries with tuple-sourced sizing
            entry_candidates = self._evaluate_entries(d)

            # Sort by raw conviction score (highest first)
            entry_candidates.sort(key=lambda e: e["raw_score"], reverse=True)

            # Normalize scores across today's picks to allocate within cash
            total_score = sum(e["raw_score"] for e in entry_candidates)

            for entry in entry_candidates:
                if len(self.positions) >= MAX_POSITIONS:
                    break

                fill = self._get_next_open(entry["ticker"], d)
                if fill is None:
                    continue
                fill_date, fill_price = fill

                if fill_price < MIN_SHARE_PRICE:
                    continue

                # Tuple-sourced sizing: this pick's share of available cash
                # proportional to its conviction score relative to all picks
                equity = self.cash + sum(
                    self.bar_close.get((p.ticker, d), p.entry_price) * p.shares
                    for p in self.positions
                )
                if total_score > 0:
                    # Each pick gets a fraction of deployable capital proportional
                    # to its conviction. Cap individual allocation at 5% of equity.
                    score_frac = entry["raw_score"] / total_score
                    # Deployable = available cash (bounded by ceiling)
                    dollar_alloc = min(self.cash * score_frac * len(entry_candidates),
                                       equity * 0.05)  # max 5% per position
                else:
                    dollar_alloc = 0

                shares = int(dollar_alloc / fill_price)
                if shares < MIN_SHARES:
                    continue
                cost = shares * fill_price
                if cost > self.cash:
                    continue

                sizing_pct = cost / equity if equity > 0 else 0

                self.cash -= cost
                self.positions.append(Position(
                    ticker=entry["ticker"],
                    signal_class=entry["signal_class"],
                    entry_date=fill_date,
                    entry_price=fill_price,
                    shares=shares,
                    sizing_pct=sizing_pct,
                    neighbor_wr=entry["neighbor_wr"],
                    spy_dk_at_entry=entry["spy_dk"],
                ))

                # Track sizing distribution
                self.daily_decisions.append({
                    "date": d, "ticker": entry["ticker"],
                    "raw_score": entry["raw_score"], "sizing_pct": sizing_pct,
                    "shares": shares, "cost": cost,
                })

            # 3. Record equity curve
            pos_value = sum(
                self.bar_close.get((p.ticker, d), p.entry_price) * p.shares
                for p in self.positions
            )
            total_equity = self.cash + pos_value
            spy_close = self.bar_close.get(("SPY", d), 0)

            self.equity_curve.append({
                "date": d,
                "equity": total_equity,
                "cash": self.cash,
                "positions": len(self.positions),
                "spy_close": spy_close,
            })

            if di % 5 == 0:
                print(f"  {d}: equity=${total_equity:,.0f} positions={len(self.positions)} closed={len(self.closed_trades)}")

        # Mark open positions to market at last date
        last_date = self.trading_dates[-1]
        open_value = sum(
            self.bar_close.get((p.ticker, last_date), p.entry_price) * p.shares
            for p in self.positions
        )
        final_equity = self.cash + open_value

        self._report(final_equity, last_date)

    def _report(self, final_equity: float, last_date: date):
        """Print the full results report."""
        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")

        # Basic P&L
        total_return = (final_equity - self.start_equity) / self.start_equity
        spy_start = self.equity_curve[0]["spy_close"] if self.equity_curve else 0
        spy_end = self.equity_curve[-1]["spy_close"] if self.equity_curve else 0
        spy_return = (spy_end - spy_start) / spy_start if spy_start > 0 else 0

        print(f"\nFinal equity: ${final_equity:,.2f} (started ${self.start_equity:,.0f})")
        print(f"Total return: {total_return*100:.2f}%")
        print(f"SPY return:   {spy_return*100:.2f}%")
        print(f"Edge vs SPY:  {(total_return - spy_return)*100:.2f}pp")

        # Realized P&L
        realized_pnl = sum(t.pnl for t in self.closed_trades)
        open_pnl = sum(
            (self.bar_close.get((p.ticker, last_date), p.entry_price) - p.entry_price) * p.shares
            for p in self.positions
        )
        print(f"\nRealized P&L: ${realized_pnl:,.2f}")
        print(f"Open P&L:     ${open_pnl:,.2f}")
        print(f"Total P&L:    ${realized_pnl + open_pnl:,.2f}")

        # Win rate
        if self.closed_trades:
            winners = [t for t in self.closed_trades if t.pnl > 0]
            losers = [t for t in self.closed_trades if t.pnl <= 0]
            wr = len(winners) / len(self.closed_trades)
            mean_win = np.mean([t.pnl for t in winners]) if winners else 0
            mean_loss = np.mean([t.pnl for t in losers]) if losers else 0
            wl_ratio = abs(mean_win / mean_loss) if mean_loss != 0 else float('inf')

            print(f"\nClosed trades: {len(self.closed_trades)}")
            print(f"Win rate:      {wr*100:.1f}% ({len(winners)}W / {len(losers)}L)")
            print(f"Mean win:      ${mean_win:,.2f}")
            print(f"Mean loss:     ${mean_loss:,.2f}")
            print(f"Win/loss ratio: {wl_ratio:.2f}")

            # Hold days
            win_days = np.mean([t.hold_days for t in winners]) if winners else 0
            loss_days = np.mean([t.hold_days for t in losers]) if losers else 0
            print(f"Mean hold (winners): {win_days:.1f} days")
            print(f"Mean hold (losers):  {loss_days:.1f} days")

        # Max drawdown
        if self.equity_curve:
            equities = [e["equity"] for e in self.equity_curve]
            peak = equities[0]
            max_dd = 0
            for eq in equities:
                if eq > peak:
                    peak = eq
                dd = (eq - peak) / peak
                if dd < max_dd:
                    max_dd = dd
            print(f"\nMax drawdown: {max_dd*100:.2f}%")

        # Exit reason distribution
        if self.closed_trades:
            exit_dist = defaultdict(int)
            for t in self.closed_trades:
                exit_dist[t.exit_reason] += 1
            print(f"\nExit reason distribution:")
            for reason, count in sorted(exit_dist.items(), key=lambda x: -x[1]):
                print(f"  {reason}: {count}")

        # By signal class
        if self.closed_trades:
            print(f"\nBy signal class:")
            for cls in sorted(set(t.signal_class for t in self.closed_trades)):
                cls_trades = [t for t in self.closed_trades if t.signal_class == cls]
                cls_wins = [t for t in cls_trades if t.pnl > 0]
                cls_wr = len(cls_wins) / len(cls_trades) if cls_trades else 0
                cls_pnl = sum(t.pnl for t in cls_trades)
                print(f"  {cls}: {len(cls_trades)} trades, {cls_wr*100:.1f}% WR, ${cls_pnl:,.2f} P&L")

        # SPY D_k regime days
        dk_days = defaultdict(int)
        for e in self.equity_curve:
            spy_snap = self.spy_snapshots.get(e["date"])
            if spy_snap:
                dk = int(spy_snap.get("D_k", 0))
                dk_days[dk] += 1
        print(f"\nSPY D_k regime days:")
        for dk in sorted(dk_days):
            print(f"  D_k={dk:+d}: {dk_days[dk]} days")

        # Open positions at end
        print(f"\nOpen positions at end: {len(self.positions)}")
        for p in self.positions:
            cp = self.bar_close.get((p.ticker, last_date), p.entry_price)
            print(f"  {p.ticker} | class={p.signal_class} | entry=${p.entry_price:.2f} | current=${cp:.2f} | P&L={p.pnl_pct(cp)*100:.1f}% | age={p.age_days(last_date)}d")

        # Sizing distribution
        if self.daily_decisions:
            sizes = [d["sizing_pct"] for d in self.daily_decisions if d["sizing_pct"] > 0]
            scores = [d["raw_score"] for d in self.daily_decisions if d["raw_score"] > 0]
            if sizes:
                print(f"\nSizing distribution (tuple-sourced):")
                print(f"  Per-position size: min={min(sizes)*100:.2f}% median={np.median(sizes)*100:.2f}% max={max(sizes)*100:.2f}%")
                print(f"  Conviction scores: min={min(scores):.4f} median={np.median(scores):.4f} max={max(scores):.4f}")
                print(f"  Total entries sized: {len(sizes)}")
                # Deployment % of equity
                avg_deployed = np.mean([e["equity"] - e["cash"] for e in self.equity_curve]) / self.start_equity * 100 if self.equity_curve else 0
                print(f"  Avg deployment: {avg_deployed:.1f}% of starting equity")

        # Equity curve summary
        print(f"\nEquity curve (weekly):")
        for i, e in enumerate(self.equity_curve):
            if i % 5 == 0 or i == len(self.equity_curve) - 1:
                print(f"  {e['date']}: ${e['equity']:,.0f} ({len(self.positions)} pos)")


if __name__ == "__main__":
    sim = BacktestSimulator(start_equity=100_000.0)
    sim.run()
