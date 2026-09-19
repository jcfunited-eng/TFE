"""The nine-field reading in the structure's own frame — declared in
docs/CH2_WITHIN_BODY_READING_DECLARATION_20260919.md.

The kernel is a time-series tool. There is no structure in a calendar day, so
nothing here compares one name against another on a date. Each body is its own
control: does the reading mark the moments in THIS structure's life that
precede its rises?

The field closes the position too. No stop, no target, no time limit: the
position is held until the state that authorized it ends, read at the same
native levels as the entry.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_within_body_reading.py \
      artifacts/ch4_uf/ch2_lanes_20260919.csv.gz ch4_live_store.parquet
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_within_body_reading_20260919.json"

FIELDS = ["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"]
BAR_MIN = 250
LIQ_WINDOW = 20
LIQ_FLOOR_USD = 5_000_000.0
SEEDS = 200
SPLIT = np.datetime64("2024-03-15", "D")
CAUSES = ["geometry_break", "carry_exhausted", "viability_lost", "direction_negative", "end_of_data"]


def blk(r: np.ndarray) -> dict:
    if not len(r):
        return {"positions": 0}
    return {"positions": int(len(r)), "mean_pct": float(r.mean() * 100),
            "median_pct": float(np.median(r) * 100),
            "win_rate_pct": float((r > 0).mean() * 100)}


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=FIELDS).sort_values(["ticker", "d"]).reset_index(drop=True)
    print(f"[wb] rows={len(lanes)} tickers={lanes.ticker.nunique()}", flush=True)

    s_uf = lanes.s_uf.values; r_uf = lanes.r_uf.values; ustar = lanes.u_star_k.values
    d_k = lanes.d_k.values; m_k = lanes.m_k.values
    r_rev = lanes.r_rev_k.values; b_k = lanes.b_k.values
    c_k = lanes.c_k.values.astype(int); p_k = lanes.p_k.values.astype(int)

    # The reading — unchanged from the previous declaration, nothing re-tuned.
    reading = ((s_uf > ustar) & (r_uf > ustar)
               & (d_k == 1.0) & (m_k >= 0.0)
               & (r_rev == 0.0)
               & (b_k > -1.0)
               & ~((c_k == 3) & (p_k == 2)))

    # The state's end, at the same native levels. Order fixes the reported cause.
    end_geom = r_rev == 1.0
    end_carry = b_k == -1.0
    end_viab = (s_uf <= ustar) & (r_uf <= ustar)
    end_dir = d_k == -1.0
    state_end = end_geom | end_carry | end_viab | end_dir
    print(f"[wb] reading {reading.mean()*100:.2f}% of sessions | state-end {state_end.mean()*100:.2f}%", flush=True)
    print(f"[wb] end causes: geom {end_geom.mean()*100:.1f}% carry {end_carry.mean()*100:.1f}% "
          f"viab {end_viab.mean()*100:.1f}% dir {end_dir.mean()*100:.1f}%", flush=True)

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
        bars[sym] = (d, close, np.nan_to_num(liq >= LIQ_FLOOR_USD, nan=0).astype(bool),
                     np.nan_to_num(liq, nan=0.0))
    del bars_df

    bar_ok = lanes.bar_count.fillna(0).values >= BAR_MIN
    lane_dates = lanes.d.values.astype("datetime64[D]")

    t_close: list[np.ndarray] = []          # one close array per body that traded
    t_valid: list[np.ndarray] = []          # bars where a real entry could have started
    t_ret, t_len, t_cause, t_day = [], [], [], []
    t_pk, t_ck, t_liq, t_body = [], [], [], []

    for ticker, idx in lanes.groupby("ticker", sort=False).indices.items():
        grp = bars.get(ticker)
        if grp is None:
            continue
        d, close, ok, liq = grp
        nb = len(close)
        if nb < BAR_MIN:
            continue
        j_all = np.searchsorted(d, lane_dates[idx], side="right")
        n = len(idx)
        body_id = None
        i = 0
        while i < n:
            gi = idx[i]
            if not (reading[gi] and bar_ok[gi]):
                i += 1
                continue
            ej = j_all[i]
            if ej >= nb or not ok[ej] or not (lo <= d[ej] <= hi):
                i += 1
                continue
            # hold until the state ends
            t = i + 1
            while t < n and not state_end[idx[t]]:
                t += 1
            if t < n:
                xj = j_all[t]
                gt = idx[t]
                cause = (0 if end_geom[gt] else 1 if end_carry[gt] else
                         2 if end_viab[gt] else 3)
            else:
                xj, cause = nb - 1, 4
            xj = min(xj, nb - 1)
            if xj <= ej:
                i = t + 1
                continue
            if body_id is None:
                body_id = len(t_close)
                t_close.append(close)
                # A null entry may only start where a real one could: inside the
                # lane window and liquid. Drawing from the whole price history
                # would hand the null five years the reading never had.
                t_valid.append(np.flatnonzero(ok & (d >= lo) & (d <= hi)))
            t_ret.append(close[xj] / close[ej] - 1.0)
            t_len.append(xj - ej)
            t_cause.append(cause)
            t_day.append(d[ej])
            t_pk.append(p_k[gi]); t_ck.append(c_k[gi]); t_liq.append(liq[ej])
            t_body.append(body_id)
            i = t + 1

    ret = np.array(t_ret); ln = np.array(t_len); cause = np.array(t_cause)
    day = np.array(t_day); pk = np.array(t_pk); ck = np.array(t_ck)
    liqv = np.array(t_liq); body = np.array(t_body)
    print(f"[wb] positions={len(ret)} across {len(t_close)} bodies | "
          f"mean hold={ln.mean():.1f} median={np.median(ln):.0f} sessions", flush=True)

    # ── Matched-timing null inside the same body ────────────────────────
    null = np.full((SEEDS, len(ret)), np.nan)
    order = np.argsort(body, kind="stable")
    ub, bstarts = np.unique(body[order], return_index=True)
    bends = np.append(bstarts[1:], len(order))
    for bi, a, bnd in zip(ub, bstarts, bends):
        rows = order[a:bnd]
        close = t_close[bi]; nb = len(close)
        vstarts = t_valid[bi]
        if not len(vstarts):
            continue
        L = ln[rows]
        # per trade, how many valid starts leave room for a hold of that length
        cutoff = np.searchsorted(vstarts, nb - L - 1, side="right")
        good = cutoff > 0
        if not good.any():
            continue
        rows_g = rows[good]; Lg = L[good]; cg = cutoff[good]
        rng = np.random.default_rng(31000 + int(bi))
        starts = vstarts[(rng.random((SEEDS, len(rows_g))) * cg).astype(np.int64)]
        null[:, rows_g] = close[starts + Lg] / close[starts] - 1.0

    nm = np.nanmean(null, axis=1) * 100
    h1, h2 = day < SPLIT, day >= SPLIT
    nm1 = np.nanmean(null[:, h1], axis=1) * 100 if h1.any() else None
    nm2 = np.nanmean(null[:, h2], axis=1) * 100 if h2.any() else None

    out = {"declaration": "docs/CH2_WITHIN_BODY_READING_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.now("UTC").isoformat(),
           "reading_rate_pct": float(reading.mean() * 100),
           "state_end_rate_pct": float(state_end.mean() * 100),
           "positions": int(len(ret)), "bodies": int(len(t_close)),
           "hold_sessions": {"mean": float(ln.mean()), "median": float(np.median(ln)),
                             "p05": float(np.percentile(ln, 5)), "p25": float(np.percentile(ln, 25)),
                             "p75": float(np.percentile(ln, 75)), "p95": float(np.percentile(ln, 95)),
                             "max": int(ln.max())},
           "reading": blk(ret), "reading_first_half": blk(ret[h1]), "reading_second_half": blk(ret[h2]),
           "matched_timing_null": {
               "seeds": SEEDS, "mean_pct": float(nm.mean()),
               "p05": float(np.percentile(nm, 5)), "p95": float(np.percentile(nm, 95)),
               "h1_mean_pct": float(nm1.mean()) if nm1 is not None else None,
               "h1_p95": float(np.percentile(nm1, 95)) if nm1 is not None else None,
               "h2_mean_pct": float(nm2.mean()) if nm2 is not None else None,
               "h2_p95": float(np.percentile(nm2, 95)) if nm2 is not None else None},
           "by_exit_cause": {CAUSES[c]: dict(blk(ret[cause == c]),
                                             mean_hold=float(ln[cause == c].mean()) if (cause == c).any() else None)
                             for c in range(5)},
           "graded_by_p_k": {str(lv): blk(ret[pk == lv]) for lv in (0, 1, 2)},
           "graded_by_c_k": {str(lv): blk(ret[ck == lv]) for lv in (0, 1, 2, 3)}}

    out["beats_null"] = bool(out["reading"]["mean_pct"] > out["matched_timing_null"]["p95"])
    out["beats_null_h1"] = bool(nm1 is not None and out["reading_first_half"].get("mean_pct", -1e9)
                                > np.percentile(nm1, 95))
    out["beats_null_h2"] = bool(nm2 is not None and out["reading_second_half"].get("mean_pct", -1e9)
                                > np.percentile(nm2, 95))
    out["passes_declared_bar"] = bool(out["beats_null"] and out["beats_null_h1"] and out["beats_null_h2"])

    # size bands — the epsilon_D resolution question, kernel untouched
    q = np.percentile(liqv, [33.333, 66.667])
    band = np.digitize(liqv, q)
    out["size_bands"] = {}
    for bnd_i, label in ((0, "small"), (1, "mid"), (2, "large")):
        m = band == bnd_i
        bn = np.nanmean(null[:, m], axis=1) * 100 if m.any() else np.array([np.nan])
        out["size_bands"][label] = {"reading": blk(ret[m]),
                                    "null_mean_pct": float(np.nanmean(bn)),
                                    "null_p95": float(np.nanpercentile(bn, 95)),
                                    "beats_null": bool(blk(ret[m]).get("mean_pct", -1e9) > np.nanpercentile(bn, 95)),
                                    "mean_hold": float(ln[m].mean()) if m.any() else None}

    print(f"[wb] reading {out['reading']['mean_pct']:+.2f}% (h1 {out['reading_first_half'].get('mean_pct',0):+.2f}, "
          f"h2 {out['reading_second_half'].get('mean_pct',0):+.2f}) win {out['reading']['win_rate_pct']:.1f}%", flush=True)
    print(f"[wb] matched-timing null mean {nm.mean():+.2f}% p95 {np.percentile(nm,95):+.2f}% "
          f"| beats={out['beats_null']} h1={out['beats_null_h1']} h2={out['beats_null_h2']}", flush=True)
    print(f"[wb] holds: median {np.median(ln):.0f} p05 {np.percentile(ln,5):.0f} p95 {np.percentile(ln,95):.0f} "
          f"max {ln.max()} sessions", flush=True)
    for c in range(5):
        b = out["by_exit_cause"][CAUSES[c]]
        if b.get("positions"):
            print(f"[wb]   exit {CAUSES[c]:20s} n={b['positions']:6d} mean={b['mean_pct']:+6.2f}% "
                  f"win={b['win_rate_pct']:.1f}% hold={b['mean_hold']:.1f}", flush=True)
    for lv in (0, 1, 2):
        print(f"[wb]   P_k={lv}: {out['graded_by_p_k'][str(lv)]}", flush=True)
    for lv in (0, 1, 2, 3):
        print(f"[wb]   C_k={lv}: {out['graded_by_c_k'][str(lv)]}", flush=True)
    for label in ("small", "mid", "large"):
        sb = out["size_bands"][label]
        print(f"[wb]   size {label:6s}: {sb['reading'].get('mean_pct',0):+.2f}% (n {sb['reading'].get('positions')}) "
              f"vs null {sb['null_mean_pct']:+.2f}% p95 {sb['null_p95']:+.2f}% beats={sb['beats_null']} "
              f"hold {sb['mean_hold']:.1f}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[wb] passes declared bar: {out['passes_declared_bar']}", flush=True)
    print(f"[wb] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
