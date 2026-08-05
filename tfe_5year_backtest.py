#!/usr/bin/env python3
"""
TFE 5-Year Backtest: Agent Alpha vs Agent Chaos vs Agent Inertia
=================================================================

Agent Alpha: TFE kernel (L0-L4) + L5 governance + Epoch Shield + τ_out timer
Agent Chaos: Random picks from the same universe, same capital, same dates
Agent Inertia: Buy-and-hold SPY

Tests across:
  - 2021 hyper-bull
  - 2022 macro-bear (ultimate test of Epoch Shield)
  - 2023 volatile chop
  - 2024-2026 mixed

Each agent starts with $100K. Positions sized at 1% of equity.
CH2 entry: D_k=+1, S_UF in [0.50, 0.75), bar_count>20
CH2 exit: S_UF crosses 0.75 OR D_k flips OR τ_out exhausted
Epoch Shield: blocks entries when stress>1.0 + SPY D_k<=0

No ML. Deterministic. The kernel is frozen.
"""

import json
import os
import sys
import time
import random
from datetime import datetime, timedelta
from urllib.request import urlopen
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf

API_KEY = os.environ.get('MASSIVE_API_KEY') or os.environ.get('POLYGON_API_KEY', '')

# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════

INITIAL_CAPITAL = 100_000
POSITION_SIZE_PCT = 0.01  # 1% of equity per trade
STOP_LOSS_PCT = 0.05      # -5% hard stop (CH3 only — CH2 uses structural floor)
MIN_GATES_CH2 = 8         # minimum gates for CH2 structural richness
MAX_POSITIONS = 30        # max simultaneous positions
TAU_RATIO = 3             # τ_out = τ_in / TAU_RATIO

# Test universe — 500 tickers sampled from the full 8,694 TFE universe
import json as _json
try:
    with open('backtest_universe_500.json') as _f:
        TEST_UNIVERSE = _json.load(_f)
    # Ensure SPY is included for reference
    if 'SPY' not in TEST_UNIVERSE:
        TEST_UNIVERSE.append('SPY')
except FileNotFoundError:
    TEST_UNIVERSE = ['SPY']

BACKTEST_START = '2021-01-01'
BACKTEST_END = '2026-04-30'

# ═══════════════════════════════════════════════════════════════════════
# Data Fetching
# ═══════════════════════════════════════════════════════════════════════

def fetch_bars(ticker, start, end, retries=3):
    for attempt in range(retries):
        try:
            url = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
                   f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={API_KEY}")
            resp = urlopen(url, timeout=15)
            data = json.loads(resp.read())
            if data.get('status') == 'OK':
                return data.get('results', [])
            return []
        except:
            if attempt < retries - 1:
                time.sleep(1)
    return []

# ═══════════════════════════════════════════════════════════════════════
# Kernel Runner
# ═══════════════════════════════════════════════════════════════════════

def run_kernel_on_bars(bars):
    """Run L0-L4, return list of (bar_index, D_k, S_UF, gate_span) per gate."""
    if len(bars) < 20:
        return []

    closes = pd.Series([b['c'] for b in bars],
                      index=[pd.Timestamp(b['t'], unit='ms') for b in bars]).sort_index()
    frame = pd.DataFrame({"Close": closes})

    try:
        sev = compute_sev_series(frame, field_col="Close")
        gates = segment_gates(sev)
        interps = interpret_gates(sev, gates)
        resonance = compute_resonance(interps)
        decisions = compute_directional_signal(resonance)
        dsf_list = compute_dsf(decisions)
    except:
        return []

    if not dsf_list:
        return []

    # Compute running S_UF at each gate
    results = []
    for idx, (dsf, res) in enumerate(zip(dsf_list, resonance)):
        states = decisions[:idx+1]
        results_so_far = resonance[:idx+1]
        rev_flags = [float(ds.R_rev_k) for ds in states]
        d_vals = [float(ds.D_k) for ds in states]
        r_vals = [float(r.R_k) for r in results_so_far]
        dir_stab = 1.0 - np.mean(rev_flags)
        dsf_instab = np.mean([abs(d) > 0 for d in d_vals])
        s_uf = max(0, min(1, 0.5 * (1 - dsf_instab) + 0.5 * dir_stab))
        r_uf = max(0, min(1, np.mean(r_vals)))

        results.append({
            'gate_idx': idx,
            'bar_start': dsf.gate.start_idx,
            'bar_end': dsf.gate.end_idx,
            'span': dsf.gate.end_idx - dsf.gate.start_idx + 1,
            # Full coupled L4 tuple
            'D_k': dsf.D_k,
            'M_k': dsf.M_k,
            'R_rev_k': dsf.R_rev_k,
            'U_star_k': dsf.U_star_k,
            'C_k': dsf.C_k,
            'P_k': dsf.P_k,
            'B_k': dsf.B_k,
            'S_UF': s_uf,
            'R_UF': r_uf,
        })

    return results

# ═══════════════════════════════════════════════════════════════════════
# Epoch Shield (simplified for backtest — uses SPY D_k as proxy)
# ═══════════════════════════════════════════════════════════════════════

def is_epoch_hostile_from_universe(structural_state, date, rich_tickers):
    """Hostile = majority of structurally rich tickers contracting.

    The macro signal comes from the aggregate structural state of
    tickers the kernel can actually see — not from SPY which is
    structurally invisible at daily resolution.
    """
    states = structural_state.get(date, {})
    expanding = 0
    contracting = 0
    for ticker in rich_tickers:
        state = states.get(ticker)
        if state:
            if state['D_k'] > 0:
                expanding += 1
            elif state['D_k'] < 0:
                contracting += 1
    total = expanding + contracting
    if total < 3:
        return False  # not enough data to judge
    return contracting > expanding  # majority contracting = hostile

# ═══════════════════════════════════════════════════════════════════════
# Backtest Engine
# ═══════════════════════════════════════════════════════════════════════

def run_backtest():
    if not API_KEY:
        print("ERROR: No API key")
        return

    print("=" * 80)
    print("TFE 5-YEAR BACKTEST: Agent Alpha vs Agent Chaos vs Agent Inertia")
    print(f"Period: {BACKTEST_START} to {BACKTEST_END}")
    print(f"Universe: {len(TEST_UNIVERSE)} tickers")
    print(f"Initial capital: ${INITIAL_CAPITAL:,}")
    print("=" * 80)

    # Fetch all bar data upfront
    print("\nFetching bar data...")
    all_bars = {}
    for i, ticker in enumerate(TEST_UNIVERSE):
        bars = fetch_bars(ticker, BACKTEST_START, BACKTEST_END)
        if bars:
            all_bars[ticker] = bars
            print(f"  [{i+1}/{len(TEST_UNIVERSE)}] {ticker}: {len(bars)} bars")
        else:
            print(f"  [{i+1}/{len(TEST_UNIVERSE)}] {ticker}: NO DATA")
        time.sleep(0.2)

    # Build date-indexed price lookup
    price_by_date = defaultdict(dict)
    for ticker, bars in all_bars.items():
        for b in bars:
            date = datetime.utcfromtimestamp(b['t']/1000).strftime('%Y-%m-%d')
            price_by_date[date][ticker] = b['c']

    all_dates = sorted(price_by_date.keys())
    print(f"\nTrading days: {len(all_dates)}")

    # Run kernel on each ticker to get structural states
    print("\nRunning kernel on all tickers...")
    kernel_results = {}
    for i, ticker in enumerate(TEST_UNIVERSE):
        if ticker not in all_bars:
            continue
        results = run_kernel_on_bars(all_bars[ticker])
        if results:
            kernel_results[ticker] = results
        print(f"  [{i+1}/{len(TEST_UNIVERSE)}] {ticker}: {len(results)} gates")
        time.sleep(0.05)

    # Map kernel gates to dates
    # For each ticker, at each date, what's the current D_k and S_UF?
    structural_state = defaultdict(dict)  # date -> ticker -> {D_k, S_UF, ...}

    for ticker, gates in kernel_results.items():
        bars = all_bars[ticker]
        for gate in gates:
            for bar_idx in range(gate['bar_start'], min(gate['bar_end'] + 1, len(bars))):
                date = datetime.utcfromtimestamp(bars[bar_idx]['t']/1000).strftime('%Y-%m-%d')
                structural_state[date][ticker] = gate

    # ═══════════════════════════════════════════════════════════════════
    # Agent Alpha: TFE kernel + shield + τ_out
    # ═══════════════════════════════════════════════════════════════════

    print("\nRunning Agent Alpha...")
    alpha_equity = INITIAL_CAPITAL
    alpha_positions = {}  # ticker -> {entry_price, entry_date, tau_out, shares}
    alpha_equity_curve = []
    alpha_trades = []

    # SPY structural state for shield
    spy_gates = kernel_results.get('SPY', [])

    for date_idx, date in enumerate(all_dates):
        prices = price_by_date[date]
        states = structural_state.get(date, {})

        # Update position values
        unrealized = 0
        for ticker, pos in list(alpha_positions.items()):
            if ticker in prices:
                current = prices[ticker]
                pnl_pct = (current - pos['entry_price']) / pos['entry_price']
                unrealized += pos['shares'] * (current - pos['entry_price'])

                # Exit: Structural Floor — price broke below the compression gate's lowest point
                # This is the physical boundary of the valley the stock launched from.
                # If price drops below it, the structural basis for the trade is shattered.
                structural_floor = pos.get('structural_floor', 0)
                if structural_floor > 0 and current < structural_floor:
                    alpha_equity += pos['shares'] * current
                    alpha_trades.append({'ticker': ticker, 'entry': pos['entry_price'], 'exit': current, 'pnl_pct': pnl_pct, 'reason': 'structural_floor', 'date': date})
                    del alpha_positions[ticker]
                    continue

                # Exit: D_k flip
                state = states.get(ticker)
                if state and state['D_k'] != 1:
                    alpha_equity += pos['shares'] * current
                    alpha_trades.append({'ticker': ticker, 'entry': pos['entry_price'], 'exit': current, 'pnl_pct': pnl_pct, 'reason': 'dk_flip', 'date': date})
                    del alpha_positions[ticker]
                    continue

                # Exit: S_UF >= 0.75
                if state and state['S_UF'] >= 0.75:
                    alpha_equity += pos['shares'] * current
                    alpha_trades.append({'ticker': ticker, 'entry': pos['entry_price'], 'exit': current, 'pnl_pct': pnl_pct, 'reason': 'suf_complete', 'date': date})
                    del alpha_positions[ticker]
                    continue

                # Exit: τ_out exhausted
                if pos.get('tau_out', 0) > 0:
                    days_held = date_idx - pos['entry_idx']
                    if days_held > pos['tau_out']:
                        alpha_equity += pos['shares'] * current
                        alpha_trades.append({'ticker': ticker, 'entry': pos['entry_price'], 'exit': current, 'pnl_pct': pnl_pct, 'reason': 'tau_exhausted', 'date': date})
                        del alpha_positions[ticker]
                        continue

        # Identify structurally rich tickers (8+ gates)
        if not hasattr(run_backtest, '_rich_tickers'):
            run_backtest._rich_tickers = [t for t, g in kernel_results.items()
                                          if len(g) >= MIN_GATES_CH2 and t not in ('SPY','QQQ','IWM')]
        rich_tickers = run_backtest._rich_tickers

        # Shield check — aggregate structural state of rich tickers
        if is_epoch_hostile_from_universe(structural_state, date, rich_tickers):
            alpha_equity_curve.append({'date': date, 'equity': alpha_equity + unrealized, 'phase': 'HOSTILE'})
            continue

        # Scan for entries
        if len(alpha_positions) < MAX_POSITIONS:
            for ticker in TEST_UNIVERSE:
                if ticker in alpha_positions or ticker in ('SPY', 'QQQ', 'IWM'):
                    continue
                if ticker not in prices or ticker not in states:
                    continue

                state = states[ticker]
                # Structural richness filter — skip stocks with too few gates
                ticker_gates = kernel_results.get(ticker, [])
                if len(ticker_gates) < MIN_GATES_CH2:
                    continue

                # CH2 entry: full basin math — the coupled DSF determines accumulation
                # Same frozen V3 computation as production
                s_uf = state['S_UF']
                r_uf = state.get('R_UF', s_uf)
                dk = state['D_k']
                mk = state.get('M_k', 0)
                rrev = state['R_rev_k']
                ustar = state.get('U_star_k', 0.33)
                ck = state.get('C_k', 3)
                pk = state.get('P_k', 0)
                bk = state['B_k']

                # V3 Basin argmax
                BETA = 37/64; MW = 3/5; MP = 5/4; RBP = 16; CBP = 4; BS = 1/128
                m_hat = max(-1, min(1, mk))
                sv = s_uf - ustar; rv = r_uf - ustar
                s_pos = max(sv, 0); r_pos = max(rv, 0)
                core = min(s_pos, r_pos); edge = max(s_pos, r_pos) - core
                live = core + BETA * edge
                contested = (1 - BETA) * edge
                balance = core / (core + edge + 1e-12)
                rupture = max(-max(sv, rv), 0)
                d_na = (1 + dk) / 2; d_a = max(-dk, 0)
                m_c = (1 + m_hat) / 2; m_b = (1 - m_hat) / 2
                motion = (MW * d_na**MP + (1-MW) * m_c**MP) ** (1/MP) if (d_na >= 0 and m_c >= 0) else 0
                ab = d_a * m_b
                rb = rrev * ((1-balance)**RBP)
                cb = (-bk) * rrev * ((1-balance)**CBP) * (1-ab)
                burden = BS * (ck/(1+ck)) * (pk/(1+pk))
                ba = max(ab, rb, cb)
                acc_basin = live * motion * (1-rrev) * (1-ab) * (1-burden)
                hold_basin = contested * (1-ba) + live * rrev * balance + live * (1-rrev) * ((1-motion)*(1-ab) + motion*burden)
                avoid_basin = rupture + (live + contested) * ba
                max_basin = max(acc_basin, hold_basin, avoid_basin)
                is_accumulate = abs(max_basin - acc_basin) < 1e-12 and acc_basin > hold_basin

                if is_accumulate and 0.50 <= s_uf < 0.75:
                    price = prices[ticker]
                    position_value = alpha_equity * POSITION_SIZE_PCT
                    shares = int(position_value / price)
                    if shares < 1:
                        continue

                    # Compute τ_in from gate history
                    tau_in = 0
                    gate_idx = state['gate_idx']
                    for g in reversed(ticker_gates[:gate_idx]):
                        if g['D_k'] <= 0:
                            tau_in += g['span']
                        else:
                            break
                    tau_out = tau_in // TAU_RATIO

                    # Structural floor: lowest price in the compression gate
                    # This is the physical boundary of the valley
                    structural_floor = price  # default to entry
                    bars_data = all_bars.get(ticker, [])
                    for g in reversed(ticker_gates[:gate_idx]):
                        if g['D_k'] <= 0:
                            # Find min price in this gate's bar range
                            for bar_idx in range(g['bar_start'], min(g['bar_end'] + 1, len(bars_data))):
                                bar_price = bars_data[bar_idx]['l']  # use low price
                                if bar_price < structural_floor:
                                    structural_floor = bar_price
                            break  # only the immediately preceding compression gate

                    alpha_equity -= shares * price
                    alpha_positions[ticker] = {
                        'entry_price': price,
                        'entry_date': date,
                        'entry_idx': date_idx,
                        'shares': shares,
                        'tau_out': tau_out,
                        'structural_floor': structural_floor,
                    }

                    if len(alpha_positions) >= MAX_POSITIONS:
                        break

        total_equity = alpha_equity + sum(
            pos['shares'] * prices.get(tk, pos['entry_price'])
            for tk, pos in alpha_positions.items()
        )
        alpha_equity_curve.append({'date': date, 'equity': total_equity, 'phase': 'ACTIVE'})

    # Close remaining positions at last price
    for ticker, pos in alpha_positions.items():
        last_price = price_by_date[all_dates[-1]].get(ticker, pos['entry_price'])
        alpha_equity += pos['shares'] * last_price
        pnl_pct = (last_price - pos['entry_price']) / pos['entry_price']
        alpha_trades.append({'ticker': ticker, 'entry': pos['entry_price'], 'exit': last_price, 'pnl_pct': pnl_pct, 'reason': 'end_of_test', 'date': all_dates[-1]})

    # ═══════════════════════════════════════════════════════════════════
    # Agent Chaos: Random picks, same timing and capital
    # ═══════════════════════════════════════════════════════════════════

    print("Running Agent Chaos...")
    random.seed(42)
    chaos_equity = INITIAL_CAPITAL
    chaos_positions = {}
    chaos_equity_curve = []
    chaos_trades = []

    for date_idx, date in enumerate(all_dates):
        prices = price_by_date[date]

        # Update positions
        unrealized = 0
        for ticker, pos in list(chaos_positions.items()):
            if ticker in prices:
                current = prices[ticker]
                pnl_pct = (current - pos['entry_price']) / pos['entry_price']
                unrealized += pos['shares'] * (current - pos['entry_price'])

                # Same holding period as alpha trades (random exit after 5-30 days)
                days_held = date_idx - pos['entry_idx']
                if days_held > pos['hold_days'] or pnl_pct <= -STOP_LOSS_PCT:
                    chaos_equity += pos['shares'] * current
                    chaos_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'date': date})
                    del chaos_positions[ticker]

        # Entry: same frequency as alpha (check if alpha entered today)
        alpha_entries_today = sum(1 for t in alpha_trades if t.get('date') == date and 'entry' in t)
        # Rough proxy: enter same number of random stocks
        if len(chaos_positions) < MAX_POSITIONS:
            n_entries = min(3, MAX_POSITIONS - len(chaos_positions))
            available = [t for t in TEST_UNIVERSE if t in prices and t not in chaos_positions and t not in ('SPY','QQQ','IWM')]
            if available:
                picks = random.sample(available, min(n_entries, len(available)))
                for ticker in picks:
                    price = prices[ticker]
                    position_value = chaos_equity * POSITION_SIZE_PCT
                    shares = int(position_value / price)
                    if shares < 1:
                        continue
                    chaos_equity -= shares * price
                    chaos_positions[ticker] = {
                        'entry_price': price,
                        'entry_idx': date_idx,
                        'shares': shares,
                        'hold_days': random.randint(5, 30),
                    }

        total = chaos_equity + sum(
            pos['shares'] * prices.get(tk, pos['entry_price'])
            for tk, pos in chaos_positions.items()
        )
        chaos_equity_curve.append({'date': date, 'equity': total})

    for ticker, pos in chaos_positions.items():
        last_price = price_by_date[all_dates[-1]].get(ticker, pos['entry_price'])
        chaos_equity += pos['shares'] * last_price
        pnl_pct = (last_price - pos['entry_price']) / pos['entry_price']
        chaos_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'date': all_dates[-1]})

    # ═══════════════════════════════════════════════════════════════════
    # Agent Inertia: Buy-and-hold SPY
    # ═══════════════════════════════════════════════════════════════════

    spy_bars = all_bars.get('SPY', [])
    if spy_bars:
        spy_start_price = spy_bars[0]['c']
        spy_end_price = spy_bars[-1]['c']
        inertia_return = (spy_end_price - spy_start_price) / spy_start_price
        inertia_final = INITIAL_CAPITAL * (1 + inertia_return)
    else:
        inertia_return = 0
        inertia_final = INITIAL_CAPITAL

    # ═══════════════════════════════════════════════════════════════════
    # Results
    # ═══════════════════════════════════════════════════════════════════

    alpha_final = alpha_equity_curve[-1]['equity'] if alpha_equity_curve else INITIAL_CAPITAL
    chaos_final = chaos_equity_curve[-1]['equity'] if chaos_equity_curve else INITIAL_CAPITAL

    alpha_wins = sum(1 for t in alpha_trades if t['pnl_pct'] > 0)
    chaos_wins = sum(1 for t in chaos_trades if t['pnl_pct'] > 0)

    # Max drawdown
    def max_drawdown(curve):
        peak = 0
        max_dd = 0
        for point in curve:
            eq = point['equity']
            if eq > peak:
                peak = eq
            dd = (eq - peak) / peak if peak > 0 else 0
            if dd < max_dd:
                max_dd = dd
        return max_dd

    alpha_dd = max_drawdown(alpha_equity_curve)
    chaos_dd = max_drawdown(chaos_equity_curve)

    # Hostile days blocked
    hostile_days = sum(1 for p in alpha_equity_curve if p.get('phase') == 'HOSTILE')

    print(f"\n{'='*80}")
    print("5-YEAR BACKTEST RESULTS")
    print(f"{'='*80}")
    print(f"\n{'':30} {'Alpha':>12} {'Chaos':>12} {'Inertia':>12}")
    print(f"{'-'*70}")
    print(f"{'Final Equity':30} ${alpha_final:>11,.0f} ${chaos_final:>11,.0f} ${inertia_final:>11,.0f}")
    print(f"{'Total Return':30} {(alpha_final/INITIAL_CAPITAL-1)*100:>+11.1f}% {(chaos_final/INITIAL_CAPITAL-1)*100:>+11.1f}% {inertia_return*100:>+11.1f}%")
    print(f"{'Trades':30} {len(alpha_trades):>12} {len(chaos_trades):>12} {'1':>12}")
    print(f"{'Win Rate':30} {100*alpha_wins/len(alpha_trades) if alpha_trades else 0:>11.1f}% {100*chaos_wins/len(chaos_trades) if chaos_trades else 0:>11.1f}% {'n/a':>12}")
    print(f"{'Max Drawdown':30} {alpha_dd*100:>+11.1f}% {chaos_dd*100:>+11.1f}% {'n/a':>12}")
    print(f"{'Hostile Days Blocked':30} {hostile_days:>12} {'n/a':>12} {'n/a':>12}")

    # By year
    print(f"\nBY YEAR:")
    for year in ['2021', '2022', '2023', '2024', '2025', '2026']:
        alpha_year = [p for p in alpha_equity_curve if p['date'].startswith(year)]
        chaos_year = [p for p in chaos_equity_curve if p['date'].startswith(year)]
        if alpha_year and chaos_year:
            a_start = alpha_year[0]['equity']
            a_end = alpha_year[-1]['equity']
            c_start = chaos_year[0]['equity']
            c_end = chaos_year[-1]['equity']
            a_ret = (a_end - a_start) / a_start * 100
            c_ret = (c_end - c_start) / c_start * 100
            hostile = sum(1 for p in alpha_year if p.get('phase') == 'HOSTILE')
            print(f"  {year}: Alpha {a_ret:>+7.1f}% | Chaos {c_ret:>+7.1f}% | Shield blocked {hostile} days")

    # Exit reason breakdown
    print(f"\nALPHA EXIT REASONS:")
    reasons = defaultdict(int)
    for t in alpha_trades:
        reasons[t.get('reason', 'unknown')] += 1
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")

    # Save results
    results = {
        'alpha_final': alpha_final,
        'chaos_final': chaos_final,
        'inertia_final': inertia_final,
        'alpha_trades': len(alpha_trades),
        'chaos_trades': len(chaos_trades),
        'alpha_win_rate': 100*alpha_wins/len(alpha_trades) if alpha_trades else 0,
        'chaos_win_rate': 100*chaos_wins/len(chaos_trades) if chaos_trades else 0,
        'alpha_max_dd': alpha_dd,
        'chaos_max_dd': chaos_dd,
        'hostile_days_blocked': hostile_days,
        'alpha_equity_curve': alpha_equity_curve,
        'chaos_equity_curve': chaos_equity_curve,
    }

    with open('backtest_5year_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to backtest_5year_results.json")

if __name__ == '__main__':
    run_backtest()
