"""The living-drive signature — the measurement declared in
docs/CH2_LIVING_DRIVE_SIGNATURE_DECLARATION_20260919.md.

Joseph's five conditions read on closed sessions, with his exclusions, tested
cross-sectionally: on each day, do the bodies showing the whole signature
outrun the other bodies available that day? Selection only — no exits.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_living_drive_signature.py \
      artifacts/ch4_uf/ch2_lanes_20260919.csv.gz ch4_live_store.parquet
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ch2_winner_exit_measure import verify_vectorised  # noqa: E402
from ch2_holding_length_measure import LIQ_FLOOR_USD, LIQ_WINDOW, PRICE_FLOOR  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_living_drive_signature_20260919.json"

# ── Declared constants (declaration §The signature, §The exclusions) ─────
W = 20              # trailing window
LAG = 10            # fuel comparison lag
RUPTURE_MAX = 5     # at most 5 of the trailing 20 sessions carrying damage
IGNITION_MIN = 10   # D_k == 1 on at least 10 of the trailing 20
ZOMBIE_BARS = 250   # fewer than this many sessions of history is excluded
PUMP_RISE = 0.50    # up more than 50% over the trailing 20 is excluded
HOLDS = [30, 60]
SEEDS = 200
SPLIT = np.datetime64("2024-03-15", "D")


def main() -> int:
    lanes = pd.read_csv(sys.argv[1], parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    port = verify_vectorised(lanes)
    print(f"[sig] port check {port}", flush=True)
    if port["decision_mismatches"]:
        return 1

    g = lanes.groupby("ticker", sort=False)
    roll = lambda s, f: g[s].transform(lambda x: getattr(x.rolling(W, min_periods=W), f)())
    suf_med = roll("s_uf", "median")
    ruf_med = roll("r_uf", "median")
    b_prev = g.b_k.shift(LAG)
    s_term = lanes.s_uf - lanes.u_star_k
    r_term = lanes.r_uf - lanes.u_star_k
    rupture = (-np.maximum(s_term, r_term)).clip(lower=0)
    lanes["rupture"] = rupture
    rupture_days = g.rupture.transform(lambda x: (x > 0).rolling(W, min_periods=W).sum())
    ign = (lanes.d_k == 1).astype(int)
    lanes["_ign"] = ign
    ign_days = g._ign.transform(lambda x: x.rolling(W, min_periods=W).sum())

    c1 = lanes.s_uf >= suf_med
    c2 = lanes.r_uf >= ruf_med
    c3 = lanes.b_k >= b_prev
    c4 = (rupture <= 0) & (rupture_days <= RUPTURE_MAX)
    c5 = (lanes.d_k == 1) & (ign_days >= IGNITION_MIN)
    lanes["signature"] = (c1 & c2 & c3 & c4 & c5).fillna(False)
    lanes["not_zombie"] = lanes.bar_count.fillna(0) >= ZOMBIE_BARS
    for name, c in [("support", c1), ("resonance", c2), ("fuel", c3),
                    ("healed", c4), ("ignition", c5)]:
        print(f"[sig] condition {name:10s} true on {float(c.fillna(False).mean())*100:5.1f}% of sessions", flush=True)
    print(f"[sig] all five: {float(lanes.signature.mean())*100:.2f}% of sessions", flush=True)

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
        ok = np.nan_to_num((liq >= LIQ_FLOOR_USD), nan=0).astype(bool) & (close >= PRICE_FLOOR)
        pump = pd.Series(close).pct_change(W).values
        ok = ok & ~np.nan_to_num(pump > PUMP_RISE, nan=False)
        bars[sym] = (d, close, ok)

    # day -> list of (ticker, fill_idx, is_signature)
    day_rows: dict[np.datetime64, list] = defaultdict(list)
    for ticker, gl in lanes.groupby("ticker", sort=False):
        grp = bars.get(ticker)
        if grp is None:
            continue
        d, close, ok = grp
        keep = gl.not_zombie.values
        if not keep.any():
            continue
        dates = gl.d.values.astype("datetime64[D]")
        sigs = gl.signature.values
        j = np.searchsorted(d, dates, side="right")
        for k in np.flatnonzero(keep):
            jj = j[k]
            if jj < len(d) and ok[jj] and lo <= d[jj] <= hi:
                day_rows[d[jj]].append((ticker, int(jj), bool(sigs[k])))
    days = sorted(day_rows)
    tot_sig = sum(sum(1 for _, _, s in v if s) for v in day_rows.values())
    print(f"[sig] days={len(days)} eligible rows={sum(len(v) for v in day_rows.values())} signature rows={tot_sig}", flush=True)

    out = {"declaration": "docs/CH2_LIVING_DRIVE_SIGNATURE_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.utcnow().isoformat(), "port_check": port,
           "signature_rate_pct": float(lanes.signature.mean() * 100),
           "days": len(days), "holds": {}}

    for hold in HOLDS:
        sig_r, sig_d, all_r = [], [], []
        per_day = []      # (day, [returns of eligible], n_signature)
        for day in days:
            rows = day_rows[day]
            rr, flags = [], []
            for t, jj, is_sig in rows:
                _, close, _ = bars[t]
                if jj + hold < len(close):
                    rr.append(close[jj + hold] / close[jj] - 1.0); flags.append(is_sig)
            if not rr:
                continue
            rr = np.array(rr); flags = np.array(flags)
            all_r.append(rr)
            if flags.any():
                sig_r.append(rr[flags]); sig_d.append(np.full(flags.sum(), day))
                per_day.append((day, rr, int(flags.sum())))
        if not sig_r:
            out["holds"][str(hold)] = {"note": "signature never fired"}
            print(f"[sig] hold={hold}: signature never fired", flush=True)
            continue
        S = np.concatenate(sig_r); SD = np.concatenate(sig_d); A = np.concatenate(all_r)

        means, m_h1, m_h2 = [], [], []
        for seed in range(SEEDS):
            rng = np.random.default_rng(6100 + seed * 3 + hold)
            picks, pd_dates = [], []
            for day, rr, n in per_day:
                idx = rng.choice(len(rr), size=min(n, len(rr)), replace=False)
                picks.append(rr[idx]); pd_dates.append(np.full(len(idx), day))
            p = np.concatenate(picks); pdte = np.concatenate(pd_dates)
            means.append(float(p.mean() * 100))
            if (pdte < SPLIT).any():
                m_h1.append(float(p[pdte < SPLIT].mean() * 100))
            if (pdte >= SPLIT).any():
                m_h2.append(float(p[pdte >= SPLIT].mean() * 100))
        nm = np.array(means)

        def blk(r):
            return {"positions": int(len(r)), "mean_pct": float(r.mean() * 100),
                    "median_pct": float(np.median(r) * 100),
                    "win_rate_pct": float((r > 0).mean() * 100)} if len(r) else {"positions": 0}

        h1m, h2m = SD < SPLIT, SD >= SPLIT
        rec = {"signature": blk(S), "signature_first_half": blk(S[h1m]),
               "signature_second_half": blk(S[h2m]), "all_eligible": blk(A),
               "random_same_count": {"seeds": SEEDS, "mean_pct": float(nm.mean()),
                                     "p05": float(np.percentile(nm, 5)),
                                     "p95": float(np.percentile(nm, 95)),
                                     "h1_mean_pct": float(np.mean(m_h1)) if m_h1 else None,
                                     "h1_p95": float(np.percentile(m_h1, 95)) if m_h1 else None,
                                     "h2_mean_pct": float(np.mean(m_h2)) if m_h2 else None,
                                     "h2_p95": float(np.percentile(m_h2, 95)) if m_h2 else None}}
        rec["beats_random"] = bool(rec["signature"]["mean_pct"] > rec["random_same_count"]["p95"])
        rec["beats_random_h1"] = bool(rec["random_same_count"]["h1_p95"] is not None
                                      and rec["signature_first_half"].get("mean_pct", -1e9) > rec["random_same_count"]["h1_p95"])
        rec["beats_random_h2"] = bool(rec["random_same_count"]["h2_p95"] is not None
                                      and rec["signature_second_half"].get("mean_pct", -1e9) > rec["random_same_count"]["h2_p95"])
        out["holds"][str(hold)] = rec
        print(f"[sig] hold={hold}: signature n={rec['signature']['positions']} "
              f"mean={rec['signature']['mean_pct']:+.2f}% (h1 {rec['signature_first_half'].get('mean_pct', 0):+.2f}, "
              f"h2 {rec['signature_second_half'].get('mean_pct', 0):+.2f}) | all eligible "
              f"{rec['all_eligible']['mean_pct']:+.2f}% | random same-count mean "
              f"{rec['random_same_count']['mean_pct']:+.2f}% p95 {rec['random_same_count']['p95']:+.2f}% "
              f"| beats={rec['beats_random']} h1={rec['beats_random_h1']} h2={rec['beats_random_h2']}", flush=True)

    passes = all(out["holds"][str(h)].get("beats_random") and out["holds"][str(h)].get("beats_random_h1")
                 and out["holds"][str(h)].get("beats_random_h2") for h in HOLDS
                 if "note" not in out["holds"][str(h)])
    out["passes_declared_bar"] = bool(passes and all("note" not in out["holds"][str(h)] for h in HOLDS))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[sig] passes declared bar: {out['passes_declared_bar']}", flush=True)
    print(f"[sig] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
