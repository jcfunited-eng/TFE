"""What the whole kernel does before a rise — declared in
docs/CH2_RUNUP_PATTERN_DECLARATION_20260919.md.

Joseph's instruction: find the price peaks, look at what the WHOLE kernel was
doing leading up to them, read the pattern off that, do the same on the down
slopes for the exit, and apply the common-sense filters.

Every previous measurement declared a rule and tested it. This one looks first,
then freezes what it found, then checks it on bodies and years it never saw.

Labels may use the future -- that is what a label is. The rule sees only the
causal tuple.

Single process. Uses the kernel readings already on disk; computes no new ones.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_runup_pattern.py \
      artifacts/ch4_uf/ch2_lanes_20260919.csv.gz ch4_live_store.parquet
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_runup_pattern_20260919.json"

FIELDS = ["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"]
ZIGZAG_PCT = 0.15          # declared
ADVANCE_MIN = 0.25         # declared
DECLINE_MIN = 0.15         # declared
BUY_REMAIN = 0.15          # declared
SELL_REMAIN = 0.10         # declared
MIN_SUPPORT = 200          # a transition must be seen this often in discovery
SPLIT_YEAR = np.datetime64("2023-01-01", "D")
BAR_MIN = 250              # Joseph's zombie rule
LIQ_WINDOW = 20
LIQ_FLOOR_USD = 5_000_000.0
PUMP_RISE = 0.50           # Joseph's pump-and-dump rule
SEEDS = 200


def body_cell(ticker: str) -> int:
    """Discovery/validation split by ticker. blake2b, never builtin hash."""
    return hashlib.blake2b(ticker.encode(), digest_size=2).digest()[0] & 1


def zigzag(close: np.ndarray, pct: float) -> list[tuple[int, int]]:
    """Alternating pivots: (index, +1 peak / -1 trough)."""
    piv: list[tuple[int, int]] = []
    if len(close) < 3:
        return piv
    lo_i = hi_i = 0
    direction = 0
    for i in range(1, len(close)):
        c = close[i]
        if direction >= 0 and c > close[hi_i]:
            hi_i = i
        if direction <= 0 and c < close[lo_i]:
            lo_i = i
        if direction >= 0 and close[hi_i] > 0 and c <= close[hi_i] * (1 - pct):
            piv.append((hi_i, 1)); direction = -1; lo_i = i
        elif direction <= 0 and close[lo_i] > 0 and c >= close[lo_i] * (1 + pct):
            piv.append((lo_i, -1)); direction = 1; hi_i = i
    return piv


def label_body(close: np.ndarray) -> np.ndarray:
    """0 ordinary, 1 BUY session, 2 SELL session."""
    lab = np.zeros(len(close), dtype=np.int8)
    piv = zigzag(close, ZIGZAG_PCT)
    for (a, ta), (b, tb) in zip(piv, piv[1:]):
        if ta == -1 and tb == 1:                      # advance: trough -> peak
            if close[b] / close[a] - 1.0 >= ADVANCE_MIN:
                seg = np.arange(a, b)
                rem = close[b] / close[seg] - 1.0
                lab[seg[rem >= BUY_REMAIN]] = 1
        elif ta == 1 and tb == -1:                    # decline: peak -> trough
            if close[b] / close[a] - 1.0 <= -DECLINE_MIN:
                seg = np.arange(a, b)
                rem = close[b] / close[seg] - 1.0
                lab[seg[rem <= -SELL_REMAIN]] = 2
    return lab


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=FIELDS).sort_values(["ticker", "d"]).reset_index(drop=True)
    print(f"[run] lane rows={len(lanes)} tickers={lanes.ticker.nunique()}", flush=True)

    s_uf = lanes.s_uf.values; r_uf = lanes.r_uf.values; ustar = lanes.u_star_k.values
    d_k = lanes.d_k.values; m_k = lanes.m_k.values; r_rev = lanes.r_rev_k.values
    c_k = lanes.c_k.values.astype(int); p_k = lanes.p_k.values.astype(int)
    b_k = lanes.b_k.values

    # The whole kernel, jointly, at native levels. No field left out, none scored.
    carry = np.where(b_k == 0.0, 0, np.where(b_k > -1.0, 1, 2))
    cfg = ((((((((s_uf > ustar).astype(int) * 2 + (r_uf > ustar).astype(int)) * 3
                + (d_k.astype(int) + 1)) * 3 + (np.sign(m_k).astype(int) + 1)) * 2
              + r_rev.astype(int)) * 3 + carry) * 4 + c_k) * 3 + p_k)
    lanes["cfg"] = cfg
    print(f"[run] distinct configurations present: {len(np.unique(cfg))}", flush=True)

    bars_df = pd.read_parquet(sys.argv[2], columns=["Date", "Symbol", "Close", "Volume"]).dropna()
    bars_df = bars_df.sort_values(["Symbol", "Date"])
    bars = {}
    for sym, g in bars_df.groupby("Symbol", sort=False):
        close = g.Close.values.astype(float)
        d = g.Date.values.astype("datetime64[D]")
        liq = pd.Series(close * g.Volume.values.astype(float)).rolling(
            LIQ_WINDOW, min_periods=LIQ_WINDOW).median().values
        pump = pd.Series(close).pct_change(LIQ_WINDOW).values
        # No dollar-volume floor. The $5M floor was mine, not Joseph's, and is
        # removed on his correction. Joseph's rules only: no zombies (bar_count)
        # and no pump-and-dumps.
        ok = ~np.nan_to_num(pump > PUMP_RISE, nan=False)
        bars[sym] = (d, close, ok, label_body(close))
    del bars_df
    print(f"[run] bodies with bars: {len(bars)}", flush=True)

    bar_ok = lanes.bar_count.fillna(0).values >= BAR_MIN
    lane_dates = lanes.d.values.astype("datetime64[D]")

    # Per lane row: the transition (previous distinct cfg -> this cfg), the bar
    # the order would fill on, that bar's label, and which split cell it is in.
    A: dict[str, list] = {k: [] for k in
                          ["tk", "prev", "cur", "j", "lab", "cell", "day", "okmask"]}
    bodies: dict[str, tuple] = {}
    for ticker, idx in lanes.groupby("ticker", sort=False).indices.items():
        grp = bars.get(ticker)
        if grp is None:
            continue
        d, close, ok, lab = grp
        idx = idx[bar_ok[idx]]
        if not len(idx):
            continue
        cur = cfg[idx]
        # The previous DISTINCT configuration: the kernel's own previous step,
        # not a calendar lookback. A run of identical tuples is one step.
        pd_arr = np.empty(len(cur), dtype=np.int64)
        lastc = -1
        for t in range(len(cur)):
            if t and cur[t] != cur[t - 1]:
                lastc = cur[t - 1]
            pd_arr[t] = lastc
        j = np.searchsorted(d, lane_dates[idx], side="right")
        keep = j < len(d)
        idx, cur, pd_arr, j = idx[keep], cur[keep], pd_arr[keep], j[keep]
        if not len(idx):
            continue
        bodies[ticker] = grp
        A["tk"].append(np.full(len(idx), ticker))
        A["prev"].append(pd_arr); A["cur"].append(cur); A["j"].append(j)
        A["lab"].append(lab[j]); A["okmask"].append(ok[j])
        A["day"].append(d[j])
        A["cell"].append(np.full(len(idx), body_cell(ticker)))

    tk = np.concatenate(A["tk"]); prev = np.concatenate(A["prev"])
    cur = np.concatenate(A["cur"]); jj = np.concatenate(A["j"])
    lab = np.concatenate(A["lab"]); okm = np.concatenate(A["okmask"])
    day = np.concatenate(A["day"]); cellv = np.concatenate(A["cell"])
    del A
    valid = okm
    print(f"[run] rows mapped={len(tk)} passing filters={int(valid.sum())} "
          f"BUY={int((lab[valid]==1).sum())} SELL={int((lab[valid]==2).sum())}", flush=True)

    disc = valid & (cellv == 0) & (day < SPLIT_YEAR)
    print(f"[run] discovery rows={int(disc.sum())} "
          f"({(lab[disc]==1).mean()*100:.1f}% BUY, {(lab[disc]==2).mean()*100:.1f}% SELL)", flush=True)

    # ── FIND the pattern, discovery only ────────────────────────────────
    def enrich(unit: np.ndarray, target: int):
        m = disc
        base = float((lab[m] == target).mean())
        u = unit[m]; l = lab[m]
        uu, inv = np.unique(u, return_inverse=True)
        cnt = np.bincount(inv)
        hit = np.bincount(inv, weights=(l == target).astype(float))
        keep = cnt >= MIN_SUPPORT
        e = np.divide(hit, np.maximum(cnt, 1)) / max(base, 1e-12)
        return uu[keep], e[keep], cnt[keep], base

    trans = prev.astype(np.int64) * 100000 + cur.astype(np.int64)
    out = {"declaration": "docs/CH2_RUNUP_PATTERN_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.now("UTC").isoformat(),
           "note": "production lanes cover a median 13% of sessions; unit is the tuple, not the day",
           "rows_mapped": int(len(tk)), "rows_passing_filters": int(valid.sum()),
           "discovery_rows": int(disc.sum()), "patterns": {}}

    frozen = {}
    for pname, unit in (("configuration", cur.astype(np.int64)), ("transition", trans)):
        for tname, tgt in (("BUY", 1), ("SELL", 2)):
            u, e, c, base = enrich(unit, tgt)
            sel = u[e > 1.0]
            frozen[f"{pname}_{tname}"] = set(sel.tolist())
            top = np.argsort(-e)[:10]
            out["patterns"][f"{pname}_{tname}"] = {
                "base_rate_pct": base * 100, "units_with_support": int(len(u)),
                "units_selected": int(len(sel)),
                "top10": [{"unit": int(u[i]), "enrichment": float(e[i]), "n": int(c[i])}
                          for i in top]}
            print(f"[run] {pname:13s} {tname}: base {base*100:.1f}%  units w/ support {len(u)}  "
                  f"selected {len(sel)}  best enrichment {e.max():.2f}x" if len(u) else
                  f"[run] {pname:13s} {tname}: no unit reached support {MIN_SUPPORT}", flush=True)

    # ── FREEZE, then run once on each held-out cell ─────────────────────
    cells = {"discovery(in-sample)": disc,
             "held_out_bodies_same_years": valid & (cellv == 1) & (day < SPLIT_YEAR),
             "held_out_years_same_bodies": valid & (cellv == 0) & (day >= SPLIT_YEAR),
             "held_out_both": valid & (cellv == 1) & (day >= SPLIT_YEAR)}

    close_of = {t: bars[t][1] for t in bodies}
    valid_starts = {}
    for t, (d, close, ok, _l) in bodies.items():
        valid_starts[t] = np.flatnonzero(ok)

    for pname, unit in (("configuration", cur.astype(np.int64)), ("transition", trans)):
        buys = frozen[f"{pname}_BUY"]; sells = frozen[f"{pname}_SELL"]
        if not buys or not sells:
            out["patterns"][f"{pname}_result"] = {"note": "empty pattern, not run"}
            continue
        isbuy = np.fromiter((x in buys for x in unit), dtype=bool, count=len(unit))
        issell = np.fromiter((x in sells for x in unit), dtype=bool, count=len(unit))
        res = {}
        for cname, cmask in cells.items():
            rets, lens, tks = [], [], []
            ordr = np.argsort(tk, kind="stable")
            tsorted = tk[ordr]
            ut, st = np.unique(tsorted, return_index=True)
            en = np.append(st[1:], len(ordr))
            for t, a, b in zip(ut, st, en):
                rows = ordr[a:b]
                rows = rows[np.argsort(jj[rows], kind="stable")]
                cl = close_of[t]
                i = 0
                n = len(rows)
                while i < n:
                    ri = rows[i]
                    if not (cmask[ri] and isbuy[ri]):
                        i += 1
                        continue
                    ej = jj[ri]
                    x = i + 1
                    while x < n and not issell[rows[x]]:
                        x += 1
                    xj = jj[rows[x]] if x < n else len(cl) - 1
                    xj = min(xj, len(cl) - 1)
                    if xj <= ej:
                        i = x + 1
                        continue
                    rets.append(cl[xj] / cl[ej] - 1.0); lens.append(xj - ej); tks.append(t)
                    i = x + 1
            if not rets:
                res[cname] = {"positions": 0}
                continue
            R = np.array(rets); L = np.array(lens); T = np.array(tks)
            null = np.full((SEEDS, len(R)), np.nan)
            for t in np.unique(T):
                sel = np.flatnonzero(T == t)
                cl = close_of[t]; vs = valid_starts[t]
                if not len(vs):
                    continue
                cut = np.searchsorted(vs, len(cl) - L[sel] - 1, side="right")
                g = cut > 0
                if not g.any():
                    continue
                sg = sel[g]; Lg = L[sel][g]; cg = cut[g]
                # blake2b, never the builtin hash(): it is salted per process.
                rng = np.random.default_rng(int.from_bytes(
                    hashlib.blake2b(str(t).encode(), digest_size=4).digest(), "big"))
                starts = vs[(rng.random((SEEDS, len(sg))) * cg).astype(np.int64)]
                null[:, sg] = cl[starts + Lg] / cl[starts] - 1.0
            nm = np.nanmean(null, axis=1) * 100
            res[cname] = {"positions": int(len(R)), "mean_pct": float(R.mean() * 100),
                          "median_pct": float(np.median(R) * 100),
                          "win_rate_pct": float((R > 0).mean() * 100),
                          "mean_hold_sessions": float(L.mean()),
                          "null_mean_pct": float(np.nanmean(nm)),
                          "null_p95": float(np.nanpercentile(nm, 95)),
                          "beats_null": bool(R.mean() * 100 > np.nanpercentile(nm, 95))}
            print(f"[run] {pname:13s} {cname:28s} n={res[cname]['positions']:5d} "
                  f"mean={res[cname]['mean_pct']:+6.2f}% win={res[cname]['win_rate_pct']:.1f}% "
                  f"hold={res[cname]['mean_hold_sessions']:.0f} | null {res[cname]['null_mean_pct']:+.2f}% "
                  f"p95 {res[cname]['null_p95']:+.2f}% beats={res[cname]['beats_null']}", flush=True)
        out["patterns"][f"{pname}_result"] = res

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[run] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
