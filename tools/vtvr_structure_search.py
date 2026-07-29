"""
vtvr_structure_search.py
=========================

NON-CANONICAL — exhaustive structure search over the joint field's outputs.

Mandate (Joe, 2026-07-28): the side kernel is FROZEN — play with its
OUTPUTS as thoroughly as possible to tease out high-win-rate structural
states, in case the un-flattened physics holds something wonderful the
first simple studies missed. 120 bars of history is the minimum bar to
entry (an eligibility filter); structure may be evaluated at any scale at
or inside that window.

METHOD
  Field      30 declared tickers, joint daily field, as much simultaneous
             history as the data source provides (kernel bound M ≤ 2048).
  Eligibility a stock-date enters evaluation only with 120 trailing bars.
  Descriptors per stock-date, from the joint field only, at TWO scales
             (W=120 structure, W=30 recent structure):
               LEAD   window-integrated signed wedge vs the field
               COH    mean co-movement intensity with the field
               BRTH   swept-volume share of the window
               REV    displacement sign-flip rate (choppiness)
               PRES   mean |acceleration| of structural share
               LTRND  leadership trend (2nd half − 1st half of window)
               BTRND  breathing trend (expansion vs contraction)
               PTRND  pressure trend (building vs calming)
  Herd context two field-level descriptors per date (same for all stocks):
               FCOH   field coherence (mean pairwise |r_delta|)
               FBRTH  field total swept volume
  Atoms      cross-sectional thirds (LO/MID/HI) of each stock descriptor;
             temporal thirds of each field descriptor. 8×2×3 + 2×3 = 54.
  States     all single atoms, all pairs, all triples (compatible only).
  Outcomes   forward 20-bar and 60-bar simple returns; WIN = return > 0.
  Split      first 70% of eval dates = SEARCH; last 30% = HOLDOUT, used
             only to verify the top states after ranking is frozen.
  Support    a state must cover ≥ 400 stock-dates in SEARCH.

Kernel untouched. Read-only. No production import. No trading claim.
Usage: python tools/vtvr_structure_search.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.isolated_market_vtvr_side_kernel import dimensionalize  # noqa: E402
from tools.run_market_vtvr_capture import (  # noqa: E402
    fetch_exact_bars,
    iso_to_rational_seconds,
)
from tools.vtvr_leadlag_walkforward import UNIVERSE  # noqa: E402

W_LONG, W_SHORT = 120, 30
HORIZONS = (20, 60)
HISTORY_DAYS = 2600
BAR_LIMIT = 1700
MIN_SUPPORT = 400
SEARCH_FRACTION = 0.7
TOP_K_VERIFY = 25


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def build_field(universe=None):
    # Explicit parameter: callers MUST pass their universe. Reassigning
    # another module's UNIVERSE global does NOT reach this function (that
    # bug silently re-ran cohort A for every "different" universe on
    # 2026-07-29 — replication and full-scale runs before the fix are void).
    roster = list(universe) if universe is not None else list(UNIVERSE)
    from datetime import datetime, timedelta, timezone
    start_iso = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    per_symbol = {}
    for s in roster:
        try:
            per_symbol[s] = fetch_exact_bars(s, "1Day", BAR_LIMIT, start_iso)
        except Exception as e:
            print(f"  {s}: fetch failed ({e}) — dropped")
    symbols = [s for s in roster if per_symbol.get(s)]
    common = sorted(set.intersection(*(set(per_symbol[s].keys()) for s in symbols)))
    if len(common) > 2048:
        common = common[-2048:]  # kernel bound; keep the most recent
    print(f"Symbols: {len(symbols)} | simultaneous days: {len(common)} "
          f"({common[0][:10]} .. {common[-1][:10]})")
    times = [iso_to_rational_seconds(t) for t in common]
    observations = [[per_symbol[s][t] for s in symbols] for t in common]
    field = dimensionalize(symbols, times, observations)
    px = [[float(v) for v in row] for row in observations]
    return symbols, common, field, px


def per_step_arrays(symbols, field):
    m_total, n = len(field.times), len(symbols)
    edges = [(r.i, r.j) for r in field.relations[0]]

    lead = [[0.0] * n for _ in range(m_total)]
    coh = [[0.0] * n for _ in range(m_total)]
    fcoh = [0.0] * m_total
    for k in range(m_total):
        row = field.relations[k]
        tot = 0.0
        for e, (i, j) in enumerate(edges):
            w = float(row[e].r_wedge)
            rd = abs(float(row[e].r_delta))
            lead[k][j] += w
            lead[k][i] -= w
            coh[k][i] += rd
            coh[k][j] += rd
            tot += rd
        fcoh[k] = tot / len(edges)

    vol = [[float(v) for v in row] for row in field.volume]
    fbrth = [sum(row) for row in vol]
    dx = [[float(v) for v in row] for row in field.dxhat]
    dts = [float(t) for t in field.dts]

    acc = [[0.0] * n for _ in range(m_total)]
    for k in range(2, m_total):
        for i in range(n):
            u1 = dx[k][i] / dts[k] if dts[k] else 0.0
            u0 = dx[k - 1][i] / dts[k - 1] if dts[k - 1] else 0.0
            acc[k][i] = abs((u1 - u0) / dts[k]) if dts[k] else 0.0

    flip = [[0.0] * n for _ in range(m_total)]
    for k in range(1, m_total):
        for i in range(n):
            flip[k][i] = 1.0 if dx[k - 1][i] * dx[k][i] < 0 else 0.0

    def prefix(a):
        n_inner = len(a[0])
        out = [[0.0] * n_inner]
        for k in range(len(a)):
            out.append([out[-1][i] + a[k][i] for i in range(n_inner)])
        return out

    return {
        "lead_p": prefix(lead), "coh_p": prefix(coh), "vol_p": prefix(vol),
        "acc_p": prefix(acc), "flip_p": prefix(flip),
        "fcoh": fcoh, "fbrth": fbrth, "n": n, "m": m_total,
    }


def window_desc(arrs, m, w):
    """Descriptors over bars (m-w, m], per stock. Prefix arrays are 1-based."""
    n = arrs["n"]
    lo, hi = m - w + 1, m + 1
    mid = lo + (hi - lo) // 2

    def rng(p, a, b, i):
        return p[b][i] - p[a][i]

    out = []
    for i in range(n):
        lead_full = rng(arrs["lead_p"], lo, hi, i)
        out.append({
            "LEAD": lead_full,
            "COH": rng(arrs["coh_p"], lo, hi, i) / w,
            "BRTH": rng(arrs["vol_p"], lo, hi, i),
            "REV": rng(arrs["flip_p"], lo + 1, hi, i) / (w - 1),
            "PRES": rng(arrs["acc_p"], lo, hi, i) / w,
            "LTRND": rng(arrs["lead_p"], mid, hi, i) - rng(arrs["lead_p"], lo, mid, i),
            "BTRND": rng(arrs["vol_p"], mid, hi, i) - rng(arrs["vol_p"], lo, mid, i),
            "PTRND": rng(arrs["acc_p"], mid, hi, i) - rng(arrs["acc_p"], lo, mid, i),
        })
    return out


DESCS = ("LEAD", "COH", "BRTH", "REV", "PRES", "LTRND", "BTRND", "PTRND")
BANDS = ("LO", "MID", "HI")


def main():
    symbols, common, field, px = build_field()
    arrs = per_step_arrays(symbols, field)
    n, m_total = arrs["n"], arrs["m"]

    max_h = max(HORIZONS)
    eval_dates = list(range(W_LONG, m_total - max_h))
    print(f"Eligible evaluation dates: {len(eval_dates)}")
    n_search = int(len(eval_dates) * SEARCH_FRACTION)
    search_dates = eval_dates[:n_search]
    holdout_dates = eval_dates[n_search:]
    print(f"Search {common[search_dates[0]][:10]}..{common[search_dates[-1]][:10]} "
          f"| Holdout {common[holdout_dates[0]][:10]}..{common[holdout_dates[-1]][:10]}")

    # Field-level temporal thirds (computed causally over all eval dates would
    # peek; use expanding rank within search for atoms, fixed cuts thereafter)
    fcoh_cut = sorted(arrs["fcoh"][d] for d in search_dates)
    fbrth_cut = sorted(arrs["fbrth"][d] for d in search_dates)

    def field_band(val, cuts):
        t1 = cuts[len(cuts) // 3]
        t2 = cuts[2 * len(cuts) // 3]
        return "LO" if val <= t1 else ("MID" if val <= t2 else "HI")

    # Atom bitmasks over flattened (date_idx, stock) universe
    atoms: dict = {}

    def set_bit(key, flat):
        atoms[key] = atoms.get(key, 0) | (1 << flat)

    win = {h: 0 for h in HORIZONS}
    fwd_store = {h: [] for h in HORIZONS}

    all_dates = eval_dates
    for di, m in enumerate(all_dates):
        base = di * n
        for h in HORIZONS:
            row = [(px[m + h][i] - px[m][i]) / px[m][i] for i in range(n)]
            fwd_store[h].extend(row)
            for i in range(n):
                if row[i] > 0:
                    win[h] |= 1 << (base + i)

        fb_coh = field_band(arrs["fcoh"][m], fcoh_cut)
        fb_brth = field_band(arrs["fbrth"][m], fbrth_cut)
        for i in range(n):
            set_bit(("FCOH", fb_coh), base + i)
            set_bit(("FBRTH", fb_brth), base + i)

        for w, tag in ((W_LONG, "L"), (W_SHORT, "S")):
            descs = window_desc(arrs, m, w)
            for d in DESCS:
                order = sorted(range(n), key=lambda i: descs[i][d])
                for pos, i in enumerate(order):
                    band = BANDS[min(2, (pos * 3) // n)]
                    set_bit((f"{d}.{tag}", band), base + i)

    total_flat = len(all_dates) * n
    search_mask = 0
    holdout_mask = 0
    for di, m in enumerate(all_dates):
        block = ((1 << n) - 1) << (di * n)
        if m in set(search_dates):
            search_mask |= block
        else:
            holdout_mask |= block

    atom_keys = sorted(atoms.keys())
    print(f"Atoms: {len(atom_keys)} | flattened universe: {total_flat}")

    def stats(mask, h, subset_mask):
        sel = mask & subset_mask
        n_sel = bin(sel).count("1")
        if n_sel == 0:
            return 0, 0.0, 0.0
        wins = bin(sel & win[h]).count("1")
        # mean forward return needs indices — only for reported states
        return n_sel, wins / n_sel, None

    def mean_fwd(mask, h, subset_mask):
        sel = mask & subset_mask
        vals = []
        f = fwd_store[h]
        idx = 0
        while sel:
            lsb = sel & -sel
            i = lsb.bit_length() - 1
            vals.append(f[i])
            sel ^= lsb
        return _mean(vals)

    # ── Search: singles, pairs, triples ─────────────────────────────────
    print("Searching states (singles, pairs, triples)...")
    candidates = []
    keys = atom_keys
    masks = {k: atoms[k] for k in keys}

    def consider(name, mask):
        n_sel, wr, _ = stats(mask, 60, search_mask)
        if n_sel >= MIN_SUPPORT:
            candidates.append((wr, n_sel, name, mask))

    for a in range(len(keys)):
        consider(str(keys[a]), masks[keys[a]])
    for a in range(len(keys)):
        ka = keys[a]
        for b in range(a + 1, len(keys)):
            kb = keys[b]
            if ka[0] == kb[0]:
                continue
            consider(f"{ka}&{kb}", masks[ka] & masks[kb])
    pair_top = sorted(candidates, key=lambda c: c[0], reverse=True)[:120]
    for wr_p, ns_p, name_p, mask_p in pair_top:
        parts = name_p.split("&")
        for c in range(len(keys)):
            kc = keys[c]
            if any(str(kc[0]) in p for p in parts):
                continue
            consider(f"{name_p}&{kc}", mask_p & masks[kc])

    candidates.sort(key=lambda c: c[0], reverse=True)
    top = candidates[:TOP_K_VERIFY]

    print()
    print("=" * 78)
    print(f"TOP STATES — ranked by SEARCH win rate @60 bars (support ≥ {MIN_SUPPORT})")
    print("then VERIFIED on untouched holdout")
    print("=" * 78)
    print(f"{'SEARCH':>28}  {'HOLDOUT':>20}")
    print(f"{'state':<40}{'N':>6}{'WR%':>7}  {'N':>6}{'WR%':>7}{'fwd60%':>8}")
    for wr, ns, name, mask in top:
        nh, wrh, _ = stats(mask, 60, holdout_mask)
        f60 = mean_fwd(mask, 60, holdout_mask) * 100 if nh else 0.0
        label = name.replace("('", "").replace("', '", ":").replace("')", "")
        print(f"{label[:40]:<40}{ns:>6}{wr*100:>7.1f}  {nh:>6}{wrh*100:>7.1f}{f60:>8.2f}")

    # Baselines
    nb, wrb, _ = stats((1 << total_flat) - 1, 60, search_mask)
    nbh, wrbh, _ = stats((1 << total_flat) - 1, 60, holdout_mask)
    print("-" * 78)
    print(f"{'UNIVERSE BASELINE':<40}{nb:>6}{wrb*100:>7.1f}  {nbh:>6}{wrbh*100:>7.1f}")
    print()
    print("Reading: a state is real if its holdout WR holds near its search WR.")
    print("A big search-to-holdout drop = that state was luck, not physics.")


if __name__ == "__main__":
    main()
