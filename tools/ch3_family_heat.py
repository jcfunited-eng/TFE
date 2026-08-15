"""
ch3_family_heat.py — a crowd-check for names the herd frame can't see
=====================================================================

DECLARED 2026-08-15 BEFORE THE RUN (Joe's order after EXOD: "in the
world of short strategies we cannot afford that blind spot"). One
pass, no scans, filed as-is.

THE BLIND SPOT: uncovered names (no herd row — young/small, outside
the 5,016 roster) are treated as "not crowd-backed" because the
instrument returns no data. EXOD proved a young name can have a
roaring crowd OUTSIDE the frame: its family is crypto, the family
was stampeding, and the fade shorted a sector-backed move at -23%.
The same blind stratum also produced the day's four winners, so the
fix must be a scalpel: see the family, not block the stratum.

THE INSTRUMENT (pre-registered, physics-native — no external labels;
SIC codes would file a Bitcoin-wallet company under generic finance
and miss its real kin):
  FAMILY  the 20 covered names (herd rows exist) whose daily log
          returns correlate highest with the event name over the
          trailing 60 sessions, positive correlation, minimum 40
          overlapping sessions. Knowable at the event close.
  HEAT    the fraction of that family sitting in hot greed
          (gband >= 1, the same declared herd instrument the
          covered law already uses) on the event day.
  GATE    refuse the uncovered spike when heat > 0.5 — the family
          MAJORITY is hot. Majority is the a-priori line; no
          threshold is fitted anywhere.

VALIDATION on the decade uncovered stratum (R2 harvest returns, the
exit law both books run): split events by heat > 0.5 and compare.
The gate validates iff the hot-family stratum loses its edge (the
way covered-backed spikes measured ~0) while the cool-family
stratum keeps it. ACCEPTANCE CASE, declared: on the 2026-08-13
scan the gate must refuse EXOD and pass UPLD, AEBI, FGI, AIRO —
if it fails that, it does not ship regardless of the decade split.

Usage:  python tools/ch3_family_heat.py
Output: artifacts/ch4_uf/ch3_family_heat.json
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
TAIL = os.path.join(ROOT, "ch3_supply_tail.parquet")
HERD_DAILY = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
HERD_LIVE = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_live.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_family_heat.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD = 8.0, 3.0, 5.0, 5
HARVEST_X = 0.95
HERD_END = 20260324
FAM_K = 20
FAM_WIN = 60
FAM_MIN_OVERLAP = 40
HEAT_GATE = 0.5


def build_matrices(df):
    """Per-symbol aligned daily log-return matrix over the store's calendar."""
    days = np.array(sorted(df["day"].unique()))
    d_ix = {d: i for i, d in enumerate(days)}
    syms = sorted(df["Symbol"].unique())
    s_ix = {s: i for i, s in enumerate(syms)}
    px = np.full((len(syms), len(days)), np.nan, dtype=np.float32)
    for sym, g in df.groupby("Symbol", sort=False):
        si = s_ix[sym]
        px[si, [d_ix[d] for d in g["day"]]] = g["Close"].to_numpy(dtype=np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        lr = np.diff(np.log(px), axis=1)
    return days, d_ix, syms, s_ix, lr


def family_heat_for(events, lr, d_ix, s_ix, herd, syms):
    """events: list of (sym, day). Returns dict (sym,day)->(heat, n_family)."""
    herd_g = {}
    for d, g in herd.groupby("date"):
        herd_g[int(d)] = dict(zip(g["sym"], g["gband"]))
    by_day = {}
    for sym, day in events:
        by_day.setdefault(int(day), []).append(sym)
    out = {}
    sym_arr = np.array(syms)
    for day, evs in sorted(by_day.items()):
        di = d_ix.get(day)
        gmap = herd_g.get(day)
        if di is None or not gmap or di < 2:
            continue
        w0 = max(0, di - FAM_WIN)
        win = lr[:, w0:di]                      # returns THROUGH yesterday
        covered_mask = np.isin(sym_arr, list(gmap.keys()))
        finite = np.isfinite(win)
        n_ok = finite.sum(axis=1)
        for sym in evs:
            si = s_ix.get(sym)
            if si is None:
                continue
            ev = win[si]
            ev_f = np.isfinite(ev)
            if ev_f.sum() < FAM_MIN_OVERLAP:
                out[(sym, day)] = (None, 0)     # too young to correlate
                continue
            both = finite & ev_f[None, :]
            n = both.sum(axis=1)
            evm = np.where(ev_f, ev, 0.0)
            wm = np.where(finite, win, 0.0)
            sx = (wm * ev_f[None, :]).sum(axis=1)
            sy = np.where(both, evm[None, :], 0.0).sum(axis=1)
            sxx = (wm * wm * ev_f[None, :]).sum(axis=1)
            syy = np.where(both, (evm * evm)[None, :], 0.0).sum(axis=1)
            sxy = (wm * evm[None, :]).sum(axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                cov = sxy - sx * sy / np.maximum(n, 1)
                vx = sxx - sx * sx / np.maximum(n, 1)
                vy = syy - sy * sy / np.maximum(n, 1)
                corr = cov / np.sqrt(vx * vy)
            corr[~covered_mask] = -np.inf
            corr[n < FAM_MIN_OVERLAP] = -np.inf
            corr[si] = -np.inf
            top = np.argsort(corr)[-FAM_K:]
            top = top[np.isfinite(corr[top]) & (corr[top] > 0)]
            if len(top) == 0:
                out[(sym, day)] = (None, 0)
                continue
            fam = sym_arr[top]
            heat = float(np.mean([1.0 if gmap.get(s, 0) >= 1 else 0.0
                                  for s in fam]))
            out[(sym, day)] = (heat, int(len(fam)))
    return out


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD_DAILY, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)

    # ---- decade uncovered ("none") events with R2 returns ----
    rows = []
    for sym, s in df.groupby("Symbol", sort=False):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        v = s["Volume"].to_numpy(dtype=float)
        d = s["day"].to_numpy()
        if len(c) < 26:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        for t in range(20, len(c) - HOLD):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or v[t] < VOL_MULT * va:
                continue
            k = HOLD
            for j in range(1, HOLD + 1):
                if c[t + j] <= HARVEST_X * c[t]:
                    k = j
                    break
            rows.append((sym, int(d[t]), 100 * (1 - c[t + k] / c[t])))
    ev = pd.DataFrame(rows, columns=["sym", "date", "r2"])
    ev = ev.merge(herd, on=["sym", "date"], how="left")
    none_ev = ev[ev["gband"].isna()][["sym", "date", "r2"]]
    print(f"uncovered (none) events: {len(none_ev)}")

    days, d_ix, syms, s_ix, lr = build_matrices(df)
    heats = family_heat_for(
        list(zip(none_ev["sym"], none_ev["date"])), lr, d_ix, s_ix, herd, syms)
    none_ev = none_ev.assign(
        heat=[heats.get((s, int(dd)), (None, 0))[0]
              for s, dd in zip(none_ev["sym"], none_ev["date"])])

    def stats(x):
        x = np.asarray(x, dtype=float)
        if len(x) == 0:
            return {"n": 0}
        return {"n": int(len(x)), "mean_pct": round(float(x.mean()), 3),
                "median_pct": round(float(np.median(x)), 3),
                "wr_pct": round(100 * float((x > 0).mean()), 1),
                "p1_pct": round(float(np.percentile(x, 1)), 2)}

    known = none_ev[none_ev["heat"].notna()]
    hot = known[known["heat"] > HEAT_GATE]
    cool = known[known["heat"] <= HEAT_GATE]
    unknown = none_ev[none_ev["heat"].isna()]

    # ---- acceptance case: the 2026-08-13 five ----
    tail = pd.read_parquet(TAIL)
    tail["Date"] = pd.to_datetime(tail["Date"])
    tail["day"] = tail["Date"].dt.strftime("%Y%m%d").astype(int)
    live_herd = pd.read_parquet(HERD_LIVE, columns=["sym", "date", "gband"])
    live_herd["date"] = live_herd["date"].astype(int)
    comb = pd.concat([df[["Symbol", "day", "Close"]],
                      tail[~tail["Symbol"].isin(set(df["Symbol"].unique()))]
                      [["Symbol", "day", "Close"]]], ignore_index=True)
    _cdays, cd_ix, csyms, cs_ix, clr = build_matrices(comb)
    FIVE = ["EXOD", "UPLD", "AEBI", "FGI", "AIRO"]
    acc = family_heat_for([(s, 20260813) for s in FIVE],
                          clr, cd_ix, cs_ix, live_herd, csyms)
    acceptance = {}
    for s in FIVE:
        h, nf = acc.get((s, 20260813), (None, 0))
        verdict = ("REFUSE" if (h is not None and h > HEAT_GATE)
                   else ("no family data — passes" if h is None else "PASS"))
        acceptance[s] = {"heat": None if h is None else round(h, 3),
                         "family_n": nf, "gate": verdict}

    result = {
        "declared": "family=top-20 positively-correlated covered names, "
                    "trailing 60 sessions; heat=share with gband>=1; gate "
                    "refuses heat>0.5; all pre-registered in the docstring",
        "decade_uncovered_split": {
            "hot_family (gate would refuse)": stats(hot["r2"]),
            "cool_family (gate passes)": stats(cool["r2"]),
            "no_family_computable (too young — passes)": stats(unknown["r2"]),
        },
        "share_refused_pct": round(100 * len(hot) / max(len(none_ev), 1), 1),
        "acceptance_2026_08_13": acceptance,
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
