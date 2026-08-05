#!/usr/bin/env python3
"""
TFE Epoch Structural History Study
====================================

Runs the L0-L4 kernel on major tickers across historical crisis periods
to build the structural record of how the L4 field evolved during
specific epoch stories.

Crisis periods studied:
  1. 2007-2009: Financial crisis (housing → credit → banks → contagion)
  2. 2020: COVID crash and recovery (pandemic → shutdown → stimulus → V)
  3. 2022: Rate shock (inflation → hikes → tech collapse → energy spike)
  4. 2024-2026: Current period (for comparison)

For each period, we:
  - Fetch daily bars for a broad set of tickers
  - Run the frozen L0-L4 kernel
  - Capture the full DSF evolution at every gate
  - Tag which sectors/stocks were loaded springs
  - Track which fired UP vs DOWN
  - Record the epoch environment at each gate

Output: epoch_structural_history.json — complete structural record
        epoch_structural_analysis.txt — human-readable findings
"""

import json
import os
import sys
import time
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

# Tickers that tell the epoch stories — across sectors
STUDY_TICKERS = {
    # Banks / Financial (2008 story)
    'financials': ['JPM', 'BAC', 'GS', 'WFC', 'C', 'MS'],
    # Housing / Real Estate (2008 story)
    'real_estate': ['VNQ', 'IYR', 'XHB'],
    # Energy (2008 + 2022 + current Iran story)
    'energy': ['XOM', 'CVX', 'OXY', 'COP', 'XLE', 'USO'],
    # Tech (2020 recovery + 2022 crash + current divergence)
    'tech': ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'NVDA', 'QQQ'],
    # Consumer (sensitive to rates + inflation)
    'consumer': ['WMT', 'TGT', 'HD', 'COST', 'XLY', 'XLP'],
    # Broad market
    'market': ['SPY', 'IWM', 'DIA'],
    # Rates / Bonds
    'rates': ['TLT', 'HYG', 'LQD'],
    # Volatility
    'volatility': ['VXX'],
    # Healthcare (defensive)
    'healthcare': ['JNJ', 'UNH', 'PFE', 'XLV'],
    # Industrials
    'industrials': ['CAT', 'DE', 'GE', 'XLI'],
    # Small caps (where CH3 hunts)
    'small_cap': ['IWM', 'SOXS', 'TQQQ', 'SQQQ'],
}

# Flatten to unique list
ALL_TICKERS = sorted(set(t for group in STUDY_TICKERS.values() for t in group))

# Crisis periods with context
CRISIS_PERIODS = {
    '2007-2009_financial_crisis': {
        'start': '2005-01-01',  # 2 years before for context
        'end': '2010-06-30',    # through recovery
        'peak_crisis': ('2008-09-01', '2009-03-31'),
        'narrative': 'Housing bubble → credit freeze → bank failures → contagion → TARP → slow recovery',
        'epoch_type': 'CREDIT_CONTAGION',
    },
    '2020_covid_crash': {
        'start': '2019-01-01',
        'end': '2021-06-30',
        'peak_crisis': ('2020-02-19', '2020-04-30'),
        'narrative': 'Pandemic → global shutdown → stimulus → fastest V-recovery in history',
        'epoch_type': 'EXOGENOUS_SHOCK',
    },
    '2022_rate_shock': {
        'start': '2021-06-01',
        'end': '2023-06-30',
        'peak_crisis': ('2022-01-01', '2022-12-31'),
        'narrative': 'Inflation spike → aggressive Fed hikes → tech collapse → energy surge → bank stress (SVB)',
        'epoch_type': 'MONETARY_TIGHTENING',
    },
    '2024-2026_current': {
        'start': '2024-01-01',
        'end': '2026-04-29',
        'peak_crisis': ('2026-04-01', '2026-04-29'),
        'narrative': 'Iran blockade → oil spike → Fed frozen (4 dissents) → tech earnings divergence → Warsh transition',
        'epoch_type': 'GEOPOLITICAL_MONETARY_SPLIT',
    },
}

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════════
# Data Fetching
# ═══════════════════════════════════════════════════════════════════════

def fetch_bars(ticker, start, end, max_retries=3):
    """Fetch daily bars from Polygon with retry."""
    for attempt in range(max_retries):
        try:
            url = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
                   f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={API_KEY}")
            resp = urlopen(url, timeout=30)
            data = json.loads(resp.read())
            if data.get('status') == 'OK' and data.get('results'):
                return data['results']
            return []
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"    FAILED after {max_retries} attempts: {e}")
                return []
    return []

# ���══════════════════════════════════════════════════════════════════════
# Kernel Runner
# ═���═══════════════════��═════════════════════════════════════════════════

def run_kernel(bars):
    """Run L0-L4 on bar data, return full DSF evolution with gate mapping."""
    if len(bars) < 20:
        return None

    closes = pd.Series(
        [b['c'] for b in bars],
        index=[pd.Timestamp(b['t'], unit='ms') for b in bars]
    ).sort_index().dropna().astype(float)

    if len(closes) < 20:
        return None

    frame = pd.DataFrame({"Close": closes})
    frame.index = closes.index

    try:
        sev_list = compute_sev_series(frame, field_col="Close")
        gates = segment_gates(sev_list)
        interps = interpret_gates(sev_list, gates)
        resonance = compute_resonance(interps)
        decisions = compute_directional_signal(resonance)
        dsf_list = compute_dsf(decisions)
    except Exception as e:
        print(f"    Kernel error: {e}")
        return None

    if not dsf_list:
        return None

    # Build evolution record
    n_bars = len(closes)
    close_values = closes.values
    dates = [str(d.date()) if hasattr(d, 'date') else str(d)[:10] for d in closes.index]

    # Compute stability metrics progressively
    evolution = []
    for idx, (dsf, res) in enumerate(zip(dsf_list, resonance)):
        gate_end = min(dsf.gate.end_idx, n_bars - 1)
        gate_start = dsf.gate.start_idx

        if gate_end >= n_bars:
            continue

        price = float(close_values[gate_end])
        bar_date = dates[gate_end] if gate_end < len(dates) else ''

        # Forward returns
        fwd_5d_max = None
        fwd_5d_min = None
        fwd_5d = None
        if gate_end + 5 < n_bars:
            window = close_values[gate_end + 1:gate_end + 6]
            fwd_5d_max = float(max(window) / price - 1)
            fwd_5d_min = float(min(window) / price - 1)
            fwd_5d = float(close_values[gate_end + 5] / price - 1)

        # Regime from L2
        regime = res.interpretation.regime if hasattr(res, 'interpretation') else 'UNKNOWN'

        # Running S_UF proxy
        states_so_far = decisions[:idx + 1]
        results_so_far = resonance[:idx + 1]
        r_vals = [float(r.R_k) for r in results_so_far]
        r_mean = float(np.mean(r_vals))
        rev_flags = [float(ds.R_rev_k) for ds in states_so_far]
        d_vals = [float(ds.D_k) for ds in states_so_far]
        dir_stab = float(1.0 - np.mean(rev_flags))
        dsf_instab = float(np.mean([(abs(d) > 0) for d in d_vals]))
        s_uf = max(0.0, min(1.0, 0.5 * (1.0 - dsf_instab) + 0.5 * dir_stab))
        r_uf = max(0.0, min(1.0, r_mean))

        evolution.append({
            'gate_index': idx,
            'gate_start': gate_start,
            'gate_end': gate_end,
            'bar_date': bar_date,
            'price': price,
            'D_k': float(dsf.D_k),
            'M_k': float(dsf.M_k),
            'R_rev_k': float(dsf.R_rev_k),
            'U_star_k': float(dsf.U_star_k),
            'C_k': float(dsf.C_k),
            'P_k': float(dsf.P_k),
            'B_k': float(dsf.B_k),
            'S_UF': s_uf,
            'R_UF': r_uf,
            'regime': regime,
            'fwd_5d_max': fwd_5d_max,
            'fwd_5d_min': fwd_5d_min,
            'fwd_5d': fwd_5d,
        })

    return evolution

# ═══════════════════════════════════════════════════════════════════════
# Epoch Environment Computation
# ═══════════════════════════════════════════════════════════════════════

def compute_epoch_env(spy_bars, qqq_bars, uso_bars, tlt_bars, date_str):
    """Compute epoch environment for a specific date from market proxy bars."""
    def get_price(bars, date):
        for b in bars:
            d = datetime.utcfromtimestamp(b['t']/1000).strftime('%Y-%m-%d')
            if d == date:
                return b['c']
        return None

    def get_price_lookback(bars, date, lookback=20):
        dates_prices = [(datetime.utcfromtimestamp(b['t']/1000).strftime('%Y-%m-%d'), b['c']) for b in bars]
        target_idx = None
        for i, (d, _) in enumerate(dates_prices):
            if d >= date:
                target_idx = i
                break
        if target_idx is None or target_idx < lookback:
            return None, None
        return dates_prices[target_idx][1], dates_prices[target_idx - lookback][1]

    env = {}
    for label, proxy_bars in [('spy', spy_bars), ('qqq', qqq_bars), ('uso', uso_bars), ('tlt', tlt_bars)]:
        curr, prev = get_price_lookback(proxy_bars, date_str, 20)
        if curr and prev and prev > 0:
            env[f'{label}_20d'] = (curr / prev - 1)
        else:
            env[f'{label}_20d'] = None

    return env

# ══���═════════════════════════��══════════════════════════════════════════
# Main Study
# ═══════════════════��═══════════════════════════════════════════════════

def run_study():
    if not API_KEY:
        print("ERROR: No API key")
        return

    results = {}
    analysis_lines = []

    analysis_lines.append("=" * 80)
    analysis_lines.append("TFE EPOCH STRUCTURAL HISTORY STUDY")
    analysis_lines.append(f"Generated: {datetime.utcnow().isoformat()}")
    analysis_lines.append("=" * 80)

    for period_name, period_config in CRISIS_PERIODS.items():
        print(f"\n{'='*70}")
        print(f"PERIOD: {period_name}")
        print(f"  {period_config['narrative']}")
        print(f"  Data range: {period_config['start']} to {period_config['end']}")
        print(f"{'='*70}")

        analysis_lines.append(f"\n\n{'='*80}")
        analysis_lines.append(f"PERIOD: {period_name}")
        analysis_lines.append(f"Narrative: {period_config['narrative']}")
        analysis_lines.append(f"Epoch type: {period_config['epoch_type']}")
        analysis_lines.append(f"{'='*80}")

        period_results = {
            'config': period_config,
            'tickers': {},
        }

        # Fetch epoch proxy data for this period
        print("  Fetching epoch proxies (SPY, QQQ, USO, TLT)...")
        spy_bars = fetch_bars('SPY', period_config['start'], period_config['end']); time.sleep(0.25)
        qqq_bars = fetch_bars('QQQ', period_config['start'], period_config['end']); time.sleep(0.25)
        uso_bars = fetch_bars('USO', period_config['start'], period_config['end']); time.sleep(0.25)
        tlt_bars = fetch_bars('TLT', period_config['start'], period_config['end']); time.sleep(0.25)

        # Process each ticker
        for sector, tickers in STUDY_TICKERS.items():
            for ticker in tickers:
                print(f"  [{sector}] {ticker}...", end=" ", flush=True)

                bars = fetch_bars(ticker, period_config['start'], period_config['end'])
                time.sleep(0.25)  # rate limit

                if not bars or len(bars) < 20:
                    print(f"SKIP ({len(bars) if bars else 0} bars)")
                    continue

                evolution = run_kernel(bars)
                if not evolution:
                    print("SKIP (kernel returned nothing)")
                    continue

                # Count loaded springs and their outcomes
                loaded = [g for g in evolution if g['B_k'] <= -0.95 and g['R_rev_k'] == 1.0 and g['fwd_5d_max'] is not None]
                fired_up = [g for g in loaded if g['fwd_5d_max'] > abs(g['fwd_5d_min'])]

                # Find gates during peak crisis
                peak_start, peak_end = period_config['peak_crisis']
                crisis_gates = [g for g in evolution if peak_start <= g['bar_date'] <= peak_end]
                crisis_loaded = [g for g in crisis_gates if g['B_k'] <= -0.95 and g['R_rev_k'] == 1.0]

                print(f"{len(evolution)} gates, {len(loaded)} loaded, {len(fired_up)} UP, {len(crisis_gates)} in crisis")

                period_results['tickers'][ticker] = {
                    'sector': sector,
                    'total_gates': len(evolution),
                    'loaded_springs': len(loaded),
                    'fired_up': len(fired_up),
                    'fired_down': len(loaded) - len(fired_up),
                    'crisis_gates': len(crisis_gates),
                    'crisis_loaded': len(crisis_loaded),
                    'evolution': evolution,  # full record
                }

        # ── Period Analysis ──────────────────────────────────────────────
        # How did each sector's springs behave during this epoch?
        analysis_lines.append(f"\n--- Sector Spring Behavior ---")
        analysis_lines.append(f"{'Sector':<20} {'Ticker':<8} {'Gates':>6} {'Loaded':>7} {'UP':>4} {'DN':>4} {'UP%':>6} {'Crisis':>7}")
        analysis_lines.append("-" * 70)

        sector_summary = defaultdict(lambda: {'loaded': 0, 'up': 0, 'down': 0, 'crisis_loaded': 0})

        for ticker, data in period_results['tickers'].items():
            up_pct = f"{100*data['fired_up']/data['loaded_springs']:.0f}%" if data['loaded_springs'] > 0 else "n/a"
            analysis_lines.append(
                f"{data['sector']:<20} {ticker:<8} {data['total_gates']:>6} {data['loaded_springs']:>7} "
                f"{data['fired_up']:>4} {data['fired_down']:>4} {up_pct:>6} {data['crisis_loaded']:>7}"
            )
            s = data['sector']
            sector_summary[s]['loaded'] += data['loaded_springs']
            sector_summary[s]['up'] += data['fired_up']
            sector_summary[s]['down'] += data['fired_down']
            sector_summary[s]['crisis_loaded'] += data['crisis_loaded']

        analysis_lines.append(f"\n--- Sector Summary ---")
        for sector, stats in sorted(sector_summary.items()):
            total = stats['loaded']
            up_pct = f"{100*stats['up']/total:.1f}%" if total > 0 else "n/a"
            analysis_lines.append(
                f"  {sector:<20} loaded={total:>4} UP={stats['up']:>4} ({up_pct}) "
                f"crisis_loaded={stats['crisis_loaded']:>4}"
            )

        # ── Structural Narrative ─────────────────────────────────────────
        # What did the L4 field look like during the crisis peak?
        analysis_lines.append(f"\n--- Crisis Peak Structural States ---")
        analysis_lines.append(f"Peak: {period_config['peak_crisis'][0]} to {period_config['peak_crisis'][1]}")

        for ticker, data in period_results['tickers'].items():
            crisis = [g for g in data['evolution']
                      if peak_start <= g['bar_date'] <= peak_end]
            if not crisis:
                continue

            analysis_lines.append(f"\n  {ticker} ({data['sector']}) — {len(crisis)} crisis gates:")
            for g in crisis[:10]:  # first 10 crisis gates
                fwd = f"{g['fwd_5d_max']*100:>+6.1f}%" if g['fwd_5d_max'] is not None else "   n/a"
                direction = "UP" if (g['fwd_5d_max'] or 0) > abs(g['fwd_5d_min'] or 0) else "DN"
                analysis_lines.append(
                    f"    {g['bar_date']} | D={g['D_k']:>+3.0f} M={g['M_k']:>+9.5f} "
                    f"Rrev={g['R_rev_k']:.0f} U*={g['U_star_k']:.3f} C={g['C_k']:.0f} "
                    f"P={g['P_k']:.0f} B={g['B_k']:>+7.4f} | ${g['price']:>8.2f} | {fwd} {direction}"
                )

        results[period_name] = period_results

    # ═══════════════════════════════════════════════════════════════════════
    # Cross-Period Comparison
    # ═══════════════════════════════════════════════════════════════════════

    analysis_lines.append(f"\n\n{'='*80}")
    analysis_lines.append("CROSS-PERIOD COMPARISON")
    analysis_lines.append(f"{'='*80}")

    PROFIT_CENTER = np.array([0.2875, 0.0196, 0.6649, 0.2978, 2.2506, 1.3766, -0.9771])
    L4_FIELDS = ['D_k', 'M_k', 'R_rev_k', 'U_star_k', 'C_k', 'P_k', 'B_k']
    NORMS = np.array([2.0, 2.0, 1.0, 1.0, 3.0, 2.0, 2.0])

    analysis_lines.append("\nDo loaded springs in different epoch types fire differently?")
    analysis_lines.append(f"{'Period':<35} {'Loaded':>7} {'UP%':>6} {'Avg Max':>9} {'Avg Worst':>10}")
    analysis_lines.append("-" * 70)

    for period_name, period_data in results.items():
        all_loaded = []
        for ticker, data in period_data['tickers'].items():
            for g in data['evolution']:
                if (g.get('B_k', 0) or 0) <= -0.95 and g.get('R_rev_k') == 1.0 and g.get('fwd_5d_max') is not None:
                    g['_sector'] = data['sector']
                    g['_ticker'] = ticker
                    all_loaded.append(g)

        if not all_loaded:
            continue

        up = sum(1 for g in all_loaded if g['fwd_5d_max'] > abs(g['fwd_5d_min']))
        avg_max = np.mean([g['fwd_5d_max'] for g in all_loaded]) * 100
        avg_min = np.mean([g['fwd_5d_min'] for g in all_loaded]) * 100

        analysis_lines.append(
            f"  {period_name:<35} {len(all_loaded):>5} {100*up/len(all_loaded):>5.1f}% "
            f"{avg_max:>+8.2f}% {avg_min:>+9.2f}%"
        )

        # By sector within this period
        by_sector = defaultdict(list)
        for g in all_loaded:
            by_sector[g['_sector']].append(g)

        for sector, gates in sorted(by_sector.items()):
            up_s = sum(1 for g in gates if g['fwd_5d_max'] > abs(g['fwd_5d_min']))
            avg_max_s = np.mean([g['fwd_5d_max'] for g in gates]) * 100
            analysis_lines.append(
                f"    {sector:<25} n={len(gates):>4} UP={100*up_s/len(gates):>5.1f}% max={avg_max_s:>+7.1f}%"
            )

    # ═══════════════════════════════════════════════════════════════════════
    # The Key Question: Which sectors fire UP during which epoch types?
    # ═════════════════════════════════════════��═════════════════════════════

    analysis_lines.append(f"\n\n{'='*80}")
    analysis_lines.append("THE KEY QUESTION: Sector × Epoch Type → Direction")
    analysis_lines.append("Which sectors' loaded springs fire UP in which epoch environments?")
    analysis_lines.append(f"{'='*80}")

    # Build sector × epoch matrix
    sector_epoch_matrix = {}
    for period_name, period_data in results.items():
        epoch_type = period_data['config']['epoch_type']
        for ticker, data in period_data['tickers'].items():
            sector = data['sector']
            key = (sector, epoch_type)
            if key not in sector_epoch_matrix:
                sector_epoch_matrix[key] = {'up': 0, 'down': 0, 'returns': []}

            for g in data['evolution']:
                if (g.get('B_k', 0) or 0) <= -0.95 and g.get('R_rev_k') == 1.0 and g.get('fwd_5d_max') is not None:
                    fired_up = g['fwd_5d_max'] > abs(g['fwd_5d_min'])
                    sector_epoch_matrix[key]['up' if fired_up else 'down'] += 1
                    sector_epoch_matrix[key]['returns'].append(g['fwd_5d_max'])

    all_sectors = sorted(set(k[0] for k in sector_epoch_matrix.keys()))
    all_epochs = sorted(set(k[1] for k in sector_epoch_matrix.keys()))

    analysis_lines.append(f"\n{'Sector':<20}", )
    for epoch in all_epochs:
        analysis_lines[-1] += f" | {epoch[:15]:<15}"

    analysis_lines.append("-" * (20 + 18 * len(all_epochs)))

    for sector in all_sectors:
        line = f"  {sector:<20}"
        for epoch in all_epochs:
            key = (sector, epoch)
            if key in sector_epoch_matrix:
                stats = sector_epoch_matrix[key]
                total = stats['up'] + stats['down']
                if total > 0:
                    up_pct = 100 * stats['up'] / total
                    avg_ret = np.mean(stats['returns']) * 100
                    line += f" | {up_pct:>4.0f}% n={total:<3} {avg_ret:>+5.1f}%"
                else:
                    line += f" | {'n/a':>15}"
            else:
                line += f" | {'—':>15}"
        analysis_lines.append(line)

    # ═══════════════════════════════════════════════════════════════════════
    # Today's implication
    # ════════════════════════════════════════════��══════════════════════════

    analysis_lines.append(f"\n\n{'='*80}")
    analysis_lines.append("TODAY'S IMPLICATION")
    analysis_lines.append(f"Current epoch type: GEOPOLITICAL_MONETARY_SPLIT")
    analysis_lines.append(f"Iran blockade + oil at $120 + Fed frozen (4 dissents) + tech earnings diverging")
    analysis_lines.append(f"{'='*80}")
    analysis_lines.append(f"\nBased on the sector × epoch matrix above:")
    analysis_lines.append(f"- Which sectors' loaded springs historically fire UP in this kind of environment?")
    analysis_lines.append(f"- Which sectors' springs break DOWN?")
    analysis_lines.append(f"- Use this to rank CH3 candidates by sector-epoch alignment")

    # ═══════════════════════════════════════════════════════════════════════
    # Save
    # ═══════════════════════════════════════════════════════════════════════

    # Save analysis text
    analysis_path = os.path.join(OUTPUT_DIR, 'epoch_structural_analysis.txt')
    with open(analysis_path, 'w') as f:
        f.write('\n'.join(analysis_lines))
    print(f"\nAnalysis saved to {analysis_path}")

    # Save raw data (without full evolution to keep size manageable)
    summary = {}
    for period_name, period_data in results.items():
        summary[period_name] = {
            'config': period_data['config'],
            'tickers': {}
        }
        for ticker, data in period_data['tickers'].items():
            summary[period_name]['tickers'][ticker] = {
                'sector': data['sector'],
                'total_gates': data['total_gates'],
                'loaded_springs': data['loaded_springs'],
                'fired_up': data['fired_up'],
                'fired_down': data['fired_down'],
                'crisis_gates': data['crisis_gates'],
                'crisis_loaded': data['crisis_loaded'],
                # Include crisis peak gates only (not full evolution)
                'crisis_evolution': [g for g in data['evolution']
                                    if period_data['config']['peak_crisis'][0] <= g['bar_date'] <= period_data['config']['peak_crisis'][1]],
            }

    data_path = os.path.join(OUTPUT_DIR, 'epoch_structural_history.json')
    with open(data_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Data saved to {data_path}")

    print(f"\n{'='*70}")
    print("STUDY COMPLETE")
    print(f"{'='*70}")

if __name__ == '__main__':
    run_study()
