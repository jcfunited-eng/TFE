"""The signature SPY proves, found where SPY isn't — declared in
docs/CH2_WHAT_SPY_MISSED_DECLARATION_20260919.md.

Joseph's idea. The rule is learned from ONE series (SPY) and tested on three
hundred others. No individual body's return touches the rule, so there is no
fitting to the test set available by construction.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_what_spy_missed.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
LANES = ROOT / "artifacts" / "ch4_uf" / "dense_lanes_20260919"
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_what_spy_missed_20260919.json"

TEACHER = "SPY"
BENCH = {"SPY", "QQQ", "DIA", "IWM"}
MIN_OCCUR = 30          # a configuration must occur this often in SPY's lane
BAR_MIN = 250           # Joseph's zombie rule
PUMP_WINDOW = 20        # rule HIS, numbers MINE
PUMP_RISE = 0.50
SEEDS = 200

from ch2_runup_pattern import label_body  # noqa: E402  (the declared zigzag)


def configs(df: pd.DataFrame) -> np.ndarray:
    """All nine fields, jointly, at native levels. Nothing excluded or scored."""
    s, r, u = df.s_uf.values, df.r_uf.values, df.u_star_k.values
    d, m, rr = df.d_k.values, df.m_k.values, df.r_rev_k.values
    b = df.b_k.values
    c, p = df.c_k.values.astype(int), df.p_k.values.astype(int)
    carry = np.where(b == 0.0, 0, np.where(b > -1.0, 1, 2))
    return ((((((((s > u).astype(int) * 2 + (r > u).astype(int)) * 3
                 + (d.astype(int) + 1)) * 3 + (np.sign(m).astype(int) + 1)) * 2
               + rr.astype(int)) * 3 + carry) * 4 + c) * 3 + p)


def decode(c: int) -> str:
    p = c % 3; c //= 3; ck = c % 4; c //= 4; car = c % 3; c //= 3
    rr = c % 2; c //= 2; ms = c % 3 - 1; c //= 3; d = c % 3 - 1; c //= 3
    r = c % 2; c //= 2; s = c % 2
    return (f"S{'>' if s else '<'}U* R{'>' if r else '<'}U* D={d:+d} "
            f"M={['-','0','+'][ms+1]} Rrev={rr} "
            f"{['intact','spending','exhausted'][car]} C={ck} P={p}")


def main() -> int:
    tf = LANES / f"{TEACHER}.parquet"
    if not tf.exists():
        print(f"[spy] {TEACHER} lane not built yet", flush=True)
        return 1
    spy = pd.read_parquet(tf).reset_index(drop=True)
    spy_cfg = configs(spy)
    lab = label_body(spy.close.values)
    print(f"[spy] {TEACHER}: {len(spy)} sessions, "
          f"{(lab==1).sum()} advancing, {(lab==2).sum()} declining", flush=True)

    # ── Learn the signature from SPY alone ──────────────────────────────
    uu, inv = np.unique(spy_cfg, return_inverse=True)
    cnt = np.bincount(inv, minlength=len(uu))
    adv = np.bincount(inv, weights=(lab == 1).astype(float), minlength=len(uu))
    dec = np.bincount(inv, weights=(lab == 2).astype(float), minlength=len(uu))
    base_a = float((lab == 1).mean()); base_d = float((lab == 2).mean())
    ok = cnt >= MIN_OCCUR
    adv_rate = np.divide(adv, np.maximum(cnt, 1))
    dec_rate = np.divide(dec, np.maximum(cnt, 1))
    ADV = set(uu[ok & (adv_rate > base_a)].tolist())
    DEC = set(uu[ok & (dec_rate > base_d)].tolist())
    print(f"[spy] SPY base: advancing {base_a*100:.1f}%  declining {base_d*100:.1f}%", flush=True)
    print(f"[spy] configurations in SPY's lane: {len(uu)} ({int(ok.sum())} with >= {MIN_OCCUR} occurrences)", flush=True)
    print(f"[spy] ADVANCE signature: {len(ADV)} configurations, covering "
          f"{np.isin(spy_cfg, list(ADV)).mean()*100:.1f}% of SPY's sessions", flush=True)
    print(f"[spy] DECLINE signature: {len(DEC)} configurations, covering "
          f"{np.isin(spy_cfg, list(DEC)).mean()*100:.1f}% of SPY's sessions", flush=True)
    sig_rows = []
    for i in np.argsort(-adv_rate * ok)[:10]:
        if ok[i] and adv_rate[i] > base_a:
            sig_rows.append({"cfg": int(uu[i]), "n_in_spy": int(cnt[i]),
                             "advance_rate_pct": float(adv_rate[i] * 100),
                             "reading": decode(int(uu[i]))})
            print(f"[spy]   ADV {adv_rate[i]*100:5.1f}%  n={int(cnt[i]):4d}  {decode(int(uu[i]))}", flush=True)
    dec_rows = []
    for i in np.argsort(-dec_rate * ok)[:10]:
        if ok[i] and dec_rate[i] > base_d:
            dec_rows.append({"cfg": int(uu[i]), "n_in_spy": int(cnt[i]),
                             "decline_rate_pct": float(dec_rate[i] * 100),
                             "reading": decode(int(uu[i]))})
            print(f"[spy]   DEC {dec_rate[i]*100:5.1f}%  n={int(cnt[i]):4d}  {decode(int(uu[i]))}", flush=True)

    out = {"declaration": "docs/CH2_WHAT_SPY_MISSED_DECLARATION_20260919.md",
           "generated_at_utc": pd.Timestamp.now("UTC").isoformat(),
           "teacher": TEACHER, "spy_sessions": int(len(spy)),
           "spy_advancing_pct": base_a * 100, "spy_declining_pct": base_d * 100,
           "advance_signature_size": len(ADV), "decline_signature_size": len(DEC),
           "advance_signature_coverage_of_spy_pct": float(np.isin(spy_cfg, list(ADV)).mean() * 100),
           "advance_signature_top": sig_rows, "decline_signature_top": dec_rows}

    # ── Apply to the 300 bodies. Nothing of theirs informed the rule. ───
    rets, lens, tks, dvs, days = [], [], [], [], []
    closes, starts_ok = {}, {}
    for f in sorted(LANES.glob("*.parquet")):
        sym = f.stem
        if sym in BENCH:
            continue
        df = pd.read_parquet(f).reset_index(drop=True)
        if len(df) < BAR_MIN:
            continue
        cfg = configs(df)
        cl = df.close.values
        pump = pd.Series(cl).pct_change(PUMP_WINDOW).values
        entry_ok = ~np.nan_to_num(pump > PUMP_RISE, nan=False)
        closes[sym] = cl
        starts_ok[sym] = np.flatnonzero(entry_ok)
        dv = float(np.median(df.close.values * df.volume.values))
        isadv = np.isin(cfg, list(ADV)); isdec = np.isin(cfg, list(DEC))
        n = len(cfg); i = 0
        while i < n:
            if not (isadv[i] and entry_ok[i]):
                i += 1
                continue
            x = i + 1
            while x < n and not isdec[x]:
                x += 1
            xj = min(x, n - 1)
            if xj <= i:
                break
            rets.append(cl[xj] / cl[i] - 1.0); lens.append(xj - i)
            tks.append(sym); dvs.append(dv); days.append(df.d.values[i])
            i = x + 1

    if not rets:
        print("[spy] the signature never fired on any body", flush=True)
        out["result"] = {"positions": 0}
        OUT.write_text(json.dumps(out, indent=2, default=str))
        return 0

    R = np.array(rets); L = np.array(lens); T = np.array(tks); DV = np.array(dvs)
    print(f"\n[spy] positions={len(R)} across {len(set(tks))} bodies | "
          f"mean hold={L.mean():.0f} median={np.median(L):.0f} sessions", flush=True)

    null = np.full((SEEDS, len(R)), np.nan)
    for t in np.unique(T):
        sel = np.flatnonzero(T == t)
        cl = closes[t]; vs = starts_ok[t]
        if not len(vs):
            continue
        cut = np.searchsorted(vs, len(cl) - L[sel] - 1, side="right")
        g = cut > 0
        if not g.any():
            continue
        sg = sel[g]; Lg = L[sel][g]; cg = cut[g]
        rng = np.random.default_rng(int.from_bytes(
            hashlib.blake2b(t.encode(), digest_size=4).digest(), "big"))
        st = vs[(rng.random((SEEDS, len(sg))) * cg).astype(np.int64)]
        null[:, sg] = cl[st + Lg] / cl[st] - 1.0
    nm = np.nanmean(null, axis=1) * 100

    def blk(r, l):
        return {"positions": int(len(r)), "mean_pct": float(r.mean() * 100),
                "median_pct": float(np.median(r) * 100),
                "win_rate_pct": float((r > 0).mean() * 100),
                "mean_hold": float(l.mean())}

    res = {"all": blk(R, L), "null_mean_pct": float(np.nanmean(nm)),
           "null_p95": float(np.nanpercentile(nm, 95)),
           "beats_null": bool(R.mean() * 100 > np.nanpercentile(nm, 95))}
    print(f"[spy] signature {res['all']['mean_pct']:+.2f}% win {res['all']['win_rate_pct']:.1f}% "
          f"| matched-timing null {res['null_mean_pct']:+.2f}% p95 {res['null_p95']:+.2f}% "
          f"| beats={res['beats_null']}", flush=True)

    # size terciles — "what SPY missed" (size as a stand-in for membership: MINE)
    q = np.percentile(DV, [33.333, 66.667])
    band = np.digitize(DV, q)
    res["by_size"] = {}
    for b, name in ((0, "small"), (1, "mid"), (2, "large")):
        m = band == b
        if not m.any():
            continue
        bn = np.nanmean(null[:, m], axis=1) * 100
        res["by_size"][name] = dict(blk(R[m], L[m]),
                                    null_mean_pct=float(np.nanmean(bn)),
                                    null_p95=float(np.nanpercentile(bn, 95)),
                                    beats_null=bool(R[m].mean() * 100 > np.nanpercentile(bn, 95)),
                                    median_dollar_volume=float(np.median(DV[m])))
        s = res["by_size"][name]
        print(f"[spy]   {name:6s} n={s['positions']:5d} {s['mean_pct']:+7.2f}% "
              f"win {s['win_rate_pct']:.1f}% hold {s['mean_hold']:.0f} | null {s['null_mean_pct']:+.2f}% "
              f"p95 {s['null_p95']:+.2f}% beats={s['beats_null']} | ${s['median_dollar_volume']/1e6:.1f}M/day", flush=True)

    # SPY held over the same span
    d0, d1 = spy.d.values[0], spy.d.values[-1]
    spy_ret = float(spy.close.values[-1] / spy.close.values[0] - 1.0) * 100
    res["spy_held_pct"] = spy_ret
    res["spy_span"] = [str(d0), str(d1)]
    print(f"[spy] SPY held over {d0}..{d1}: {spy_ret:+.1f}%", flush=True)

    out["result"] = res
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"[spy] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
