"""The nine-field reading — declared in
docs/CH2_NINE_FIELD_READING_DECLARATION_20260919.md.

All nine kernel fields, each read at the levels the kernel itself produces and
in the role Joseph stated for it. No trailing window, no lookback difference,
no median, no count threshold, no percentile: the only constants are 0, +/-1
and comparisons between two kernel fields.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_nine_field_reading.py \
      artifacts/ch4_uf/ch2_lanes_20260919.csv.gz ch4_live_store.parquet
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_nine_field_reading_20260919.json"

FIELDS = ["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"]
BAR_MIN = 250                    # Joseph's, agreed
LIQ_WINDOW = 20                  # mine, on trial: order has to fill
LIQ_FLOOR_USD = 5_000_000.0      # mine, on trial
HOLDS = [30, 60]
SEEDS = 200
SPLIT = np.datetime64("2024-03-15", "D")


def assert_native_levels(lanes: pd.DataFrame) -> dict:
    """The declaration stands on these ranges. If they do not hold, stop."""
    seen = {
        "d_k": sorted(np.unique(lanes.d_k.values).tolist()),
        "r_rev_k": sorted(np.unique(lanes.r_rev_k.values).tolist()),
        "c_k": sorted(np.unique(lanes.c_k.values).tolist()),
        "p_k": sorted(np.unique(lanes.p_k.values).tolist()),
        "b_k_range": [float(lanes.b_k.min()), float(lanes.b_k.max())],
        "s_uf_range": [float(lanes.s_uf.min()), float(lanes.s_uf.max())],
        "r_uf_range": [float(lanes.r_uf.min()), float(lanes.r_uf.max())],
        "u_star_k_range": [float(lanes.u_star_k.min()), float(lanes.u_star_k.max())],
        "m_k_range": [float(lanes.m_k.min()), float(lanes.m_k.max())],
    }
    bad = []
    if set(seen["d_k"]) - {-1.0, 0.0, 1.0}:
        bad.append("D_k is not {-1,0,+1}")
    if set(seen["r_rev_k"]) - {0.0, 1.0}:
        bad.append("R_rev_k is not binary")
    if set(seen["c_k"]) - {0.0, 1.0, 2.0, 3.0}:
        bad.append("C_k is not {0,1,2,3}")
    if set(seen["p_k"]) - {0.0, 1.0, 2.0}:
        bad.append("P_k is not {0,1,2}")
    if seen["b_k_range"][0] < -1.0 - 1e-9 or seen["b_k_range"][1] > 1e-9:
        bad.append("B_k is not within [-1,0]")
    seen["violations"] = bad
    return seen


def blk(r: np.ndarray) -> dict:
    if not len(r):
        return {"positions": 0}
    return {"positions": int(len(r)), "mean_pct": float(r.mean() * 100),
            "median_pct": float(np.median(r) * 100),
            "win_rate_pct": float((r > 0).mean() * 100)}


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=FIELDS)
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    print(f"[9f] rows={len(lanes)} tickers={lanes.ticker.nunique()}", flush=True)

    native = assert_native_levels(lanes)
    for k, v in native.items():
        print(f"[9f] native {k}: {v}", flush=True)
    if native["violations"]:
        print("[9f] STOP — the declared native levels do not hold", flush=True)
        return 1

    # ── The reading. Four groups, all nine fields, native levels only. ──
    s_uf = lanes.s_uf.values; r_uf = lanes.r_uf.values; ustar = lanes.u_star_k.values
    d_k = lanes.d_k.values; m_k = lanes.m_k.values
    r_rev = lanes.r_rev_k.values; b_k = lanes.b_k.values
    c_k = lanes.c_k.values.astype(int); p_k = lanes.p_k.values.astype(int)

    g_viab = (s_uf > ustar) & (r_uf > ustar)      # U* read against S_UF and R_UF
    g_motion = (d_k == 1.0) & (m_k >= 0.0)        # direction with bend, never alone
    g_geom = r_rev == 0.0                         # first-class state, not a penalty
    g_carry = b_k > -1.0                          # potential not exhausted
    # Burden: neither C_k nor P_k acts alone; only their joint extreme acts.
    g_burden = ~((c_k == 3) & (p_k == 2))
    reading = g_viab & g_motion & g_geom & g_carry & g_burden

    for nm, gcond in [("viability", g_viab), ("motion", g_motion),
                      ("geometry", g_geom), ("carry", g_carry),
                      ("burden", g_burden), ("READING", reading)]:
        print(f"[9f] group {nm:10s} true on {gcond.mean()*100:5.2f}% of sessions", flush=True)

    # census cell: viability x motion x geometry x carry x burden corner, all native
    viab_c = (s_uf > ustar).astype(int) * 2 + (r_uf > ustar).astype(int)
    motion_c = (d_k.astype(int) + 1) * 3 + (np.sign(m_k).astype(int) + 1)
    carry_c = np.where(b_k == 0.0, 0, np.where(b_k > -1.0, 1, 2))
    cell = ((((viab_c * 9 + motion_c) * 2 + r_rev.astype(int)) * 3 + carry_c) * 2
            + (~g_burden).astype(int))

    # ── Population and fills ────────────────────────────────────────────
    bars_df = pd.read_parquet(sys.argv[2], columns=["Date", "Symbol", "Close", "Volume"]).dropna()
    bars_df = bars_df.sort_values(["Symbol", "Date"])
    lo = lanes.d.min().to_datetime64().astype("datetime64[D]")
    hi = lanes.d.max().to_datetime64().astype("datetime64[D]")
    bars = {}
    for sym, gg in bars_df.groupby("Symbol", sort=False):
        close = gg.Close.values.astype(float)
        d = gg.Date.values.astype("datetime64[D]")
        liq = pd.Series(close * gg.Volume.values.astype(float)).rolling(
            LIQ_WINDOW, min_periods=LIQ_WINDOW).median().values
        # No price floor: removed on Joseph's correction.
        ok = np.nan_to_num(liq >= LIQ_FLOOR_USD, nan=0).astype(bool)
        bars[sym] = (d, close, ok, np.nan_to_num(liq, nan=0.0))
    del bars_df

    bar_ok = lanes.bar_count.fillna(0).values >= BAR_MIN
    lane_dates = lanes.d.values.astype("datetime64[D]")
    acc: dict[str, list] = {k: [] for k in
                            ["day", "read", "pk", "ck", "cell", "liq", "r30", "r60"]}
    for ticker, idx in lanes.groupby("ticker", sort=False).indices.items():
        grp = bars.get(ticker)
        if grp is None:
            continue
        d, close, ok, liq = grp
        idx = idx[bar_ok[idx]]
        if not len(idx):
            continue
        j = np.searchsorted(d, lane_dates[idx], side="right")
        keep = j < len(d)
        idx, j = idx[keep], j[keep]
        if not len(idx):
            continue
        keep = ok[j] & (d[j] >= lo) & (d[j] <= hi)
        idx, j = idx[keep], j[keep]
        if not len(idx):
            continue
        n = len(close)
        for hold, key in ((30, "r30"), (60, "r60")):
            fwd = np.full(len(j), np.nan)
            m = j + hold < n
            fwd[m] = close[j[m] + hold] / close[j[m]] - 1.0
            acc[key].append(fwd)
        acc["day"].append(d[j])
        acc["read"].append(reading[idx])
        acc["pk"].append(p_k[idx])
        acc["ck"].append(c_k[idx])
        acc["cell"].append(cell[idx])
        acc["liq"].append(liq[j])

    day = np.concatenate(acc["day"]); read = np.concatenate(acc["read"])
    pk = np.concatenate(acc["pk"]); ck = np.concatenate(acc["ck"])
    cel = np.concatenate(acc["cell"]); liqv = np.concatenate(acc["liq"])
    rets = {30: np.concatenate(acc["r30"]), 60: np.concatenate(acc["r60"])}
    del acc
    order = np.argsort(day, kind="stable")
    day, read, pk, ck, cel, liqv = day[order], read[order], pk[order], ck[order], cel[order], liqv[order]
    rets = {h: v[order] for h, v in rets.items()}
    udays, starts = np.unique(day, return_index=True)
    ends = np.append(starts[1:], len(day))
    print(f"[9f] eligible rows={len(day)} days={len(udays)} reading rows={int(read.sum())}", flush=True)

    out = {"declaration": "docs/CH2_NINE_FIELD_READING_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
           "native_levels": native,
           "group_rates_pct": {nm: float(g.mean() * 100) for nm, g in
                               [("viability", g_viab), ("motion", g_motion),
                                ("geometry", g_geom), ("carry", g_carry),
                                ("burden", g_burden), ("reading", reading)]},
           "eligible_rows": int(len(day)), "days": int(len(udays)),
           "reading_rows": int(read.sum()), "holds": {}}

    # ── Cross-sectional test, both holds ────────────────────────────────
    for hold in HOLDS:
        r = rets[hold]
        fin = np.isfinite(r)
        sel = read & fin
        rec = {"reading": blk(r[sel]), "all_eligible": blk(r[fin]),
               "reading_first_half": blk(r[sel & (day < SPLIT)]),
               "reading_second_half": blk(r[sel & (day >= SPLIT)])}

        # random same-count from the same day's eligible names
        slices = []
        for a, b in zip(starts, ends):
            f = np.flatnonzero(fin[a:b]) + a
            k = int(read[a:b][fin[a:b]].sum())
            if k and len(f):
                slices.append((f, min(k, len(f)), day[a] < SPLIT))
        means, m1, m2 = [], [], []
        for seed in range(SEEDS):
            rng = np.random.default_rng(9100 + seed * 3 + hold)
            p1, p2 = [], []
            for f, k, is_h1 in slices:
                pick = r[rng.choice(f, size=k, replace=False)]
                (p1 if is_h1 else p2).append(pick)
            a1 = np.concatenate(p1) if p1 else np.array([])
            a2 = np.concatenate(p2) if p2 else np.array([])
            allp = np.concatenate([a1, a2]) if len(a1) or len(a2) else np.array([])
            means.append(float(allp.mean() * 100))
            if len(a1):
                m1.append(float(a1.mean() * 100))
            if len(a2):
                m2.append(float(a2.mean() * 100))
        nm_ = np.array(means)
        rec["random_same_count"] = {
            "seeds": SEEDS, "mean_pct": float(nm_.mean()),
            "p05": float(np.percentile(nm_, 5)), "p95": float(np.percentile(nm_, 95)),
            "h1_mean_pct": float(np.mean(m1)) if m1 else None,
            "h1_p95": float(np.percentile(m1, 95)) if m1 else None,
            "h2_mean_pct": float(np.mean(m2)) if m2 else None,
            "h2_p95": float(np.percentile(m2, 95)) if m2 else None}
        rec["beats_random"] = bool(rec["reading"].get("mean_pct", -1e9) > rec["random_same_count"]["p95"])
        rec["beats_random_h1"] = bool(rec["random_same_count"]["h1_p95"] is not None and
                                      rec["reading_first_half"].get("mean_pct", -1e9) > rec["random_same_count"]["h1_p95"])
        rec["beats_random_h2"] = bool(rec["random_same_count"]["h2_p95"] is not None and
                                      rec["reading_second_half"].get("mean_pct", -1e9) > rec["random_same_count"]["h2_p95"])

        # C_k and P_k GRADE the reading; they never filtered it.
        rec["graded_by_p_k"] = {str(lv): blk(r[sel & (pk == lv)]) for lv in (0, 1, 2)}
        rec["graded_by_c_k"] = {str(lv): blk(r[sel & (ck == lv)]) for lv in (0, 1, 2, 3)}

        # epsilon_D resolution: the same reading inside each size band.
        bands = np.full(len(day), -1)
        for a, b in zip(starts, ends):
            v = liqv[a:b]
            if len(v) >= 3:
                q = np.percentile(v, [33.333, 66.667])
                bands[a:b] = np.digitize(v, q)
        rec["size_bands"] = {}
        for bnd, label in ((0, "small"), (1, "mid"), (2, "large")):
            bm = bands == bnd
            bsel = sel & bm
            bslices = []
            for a, b in zip(starts, ends):
                f = np.flatnonzero(fin[a:b] & bm[a:b]) + a
                k = int((read[a:b] & fin[a:b] & bm[a:b]).sum())
                if k and len(f):
                    bslices.append((f, min(k, len(f))))
            bmeans = []
            for seed in range(50):
                rng = np.random.default_rng(9700 + seed * 3 + hold + bnd)
                pk_ = [r[rng.choice(f, size=k, replace=False)] for f, k in bslices]
                if pk_:
                    bmeans.append(float(np.concatenate(pk_).mean() * 100))
            ba = np.array(bmeans) if bmeans else np.array([np.nan])
            rec["size_bands"][label] = {
                "reading": blk(r[bsel]), "all_eligible": blk(r[fin & bm]),
                "random_same_count_mean_pct": float(np.nanmean(ba)),
                "random_same_count_p95": float(np.nanpercentile(ba, 95)),
                "beats_random": bool(blk(r[bsel]).get("mean_pct", -1e9) > np.nanpercentile(ba, 95))}

        out["holds"][str(hold)] = rec
        print(f"[9f] hold={hold}: reading n={rec['reading'].get('positions')} "
              f"mean={rec['reading'].get('mean_pct', 0):+.2f}% "
              f"(h1 {rec['reading_first_half'].get('mean_pct', 0):+.2f}, "
              f"h2 {rec['reading_second_half'].get('mean_pct', 0):+.2f}) | "
              f"all eligible {rec['all_eligible'].get('mean_pct', 0):+.2f}% | "
              f"random mean {rec['random_same_count']['mean_pct']:+.2f}% "
              f"p95 {rec['random_same_count']['p95']:+.2f}% | "
              f"beats={rec['beats_random']} h1={rec['beats_random_h1']} h2={rec['beats_random_h2']}", flush=True)
        for lv in (0, 1, 2):
            print(f"[9f]   P_k={lv} ({['quiet','stressed','sharply adverse'][lv]}): "
                  f"{rec['graded_by_p_k'][str(lv)]}", flush=True)
        for lv in (0, 1, 2, 3):
            print(f"[9f]   C_k={lv}: {rec['graded_by_c_k'][str(lv)]}", flush=True)
        for label in ("small", "mid", "large"):
            sb = rec["size_bands"][label]
            print(f"[9f]   size {label:6s}: reading {sb['reading'].get('mean_pct', 0):+.2f}% "
                  f"(n {sb['reading'].get('positions')}) vs random {sb['random_same_count_mean_pct']:+.2f}% "
                  f"p95 {sb['random_same_count_p95']:+.2f}% beats={sb['beats_random']}", flush=True)

    # ── Census: description only, nothing is selected on it ─────────────
    r30 = rets[30]; fin30 = np.isfinite(r30)
    census = []
    for cv in np.unique(cel):
        m = (cel == cv) & fin30
        n = int(m.sum())
        if n < 500:
            continue
        corner = cv % 2; base = cv // 2
        viab = base // 54; rest = base % 54
        mot = rest // 6; rest2 = rest % 6
        geo = rest2 // 3; car = rest2 % 3
        census.append({"cell": int(cv), "positions": n,
                       "s_gt_u": bool(viab & 2), "r_gt_u": bool(viab & 1),
                       "d_k": int(mot // 3) - 1, "m_sign": int(mot % 3) - 1,
                       "r_rev_k": int(geo), "carry": ["intact", "spending", "exhausted"][car],
                       "burden_corner": bool(corner),
                       "mean_pct_30": float(r30[m].mean() * 100),
                       "win_rate_pct": float((r30[m] > 0).mean() * 100)})
    census.sort(key=lambda x: -x["positions"])
    out["census_hold30"] = census
    print(f"[9f] census cells (n>=500): {len(census)}", flush=True)
    for c in census[:15]:
        print(f"[9f]   n={c['positions']:7d} S>U*={int(c['s_gt_u'])} R>U*={int(c['r_gt_u'])} "
              f"D={c['d_k']:+d} M={c['m_sign']:+d} Rrev={c['r_rev_k']} carry={c['carry']:9s} "
              f"corner={int(c['burden_corner'])} "
              f"mean30={c['mean_pct_30']:+6.2f}% win={c['win_rate_pct']:.1f}%", flush=True)

    passes = all(out["holds"][str(h)]["beats_random"] and out["holds"][str(h)]["beats_random_h1"]
                 and out["holds"][str(h)]["beats_random_h2"] for h in HOLDS)
    out["passes_declared_bar"] = bool(passes)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[9f] passes declared bar: {passes}", flush=True)
    print(f"[9f] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
