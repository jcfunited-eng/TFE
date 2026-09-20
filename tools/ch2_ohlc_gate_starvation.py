"""Is the entry physics starved by the input? — the decisive test.

Established (docs/CH2_RECOVERY_POINT_20260919.md §16-17):

  - L1's binding clause is B_k > prev_B_k.
  - B_k == prev_B_k on 95.63% of rows: it only updates when a gate closes,
    roughly 13 times per symbol in five years.
  - So L1 fires on 0.14% of post-warm-up rows -> 161 usable signals in five
    years across 11,882 symbols.
  - Those 161 still work: WR 54.66% against a rejected pool at 48.67%.

So the rule is not wrong, it is starved. This tests whether feeding the kernel
the full bar instead of the close alone produces more gates -> more B_k
updates -> more signals, and whether the edge survives at that scale.

Two arms, identical kernel, identical rules, same symbols:
  CLOSE  : close series           (production)
  OHLC   : O,H,L,C path per day   (Joseph: "one stream all data")

A day is four points in the OHLC arm, so every signal is taken at that day's
CLOSE point and forward returns are measured in DAYS in both arms. Nothing
else differs.

Provenance: the rules are Joseph's (L1 + L2 + L3, as recorded in
web/scripts/execution/financial_rules.mjs). The 4-point-per-day path is MINE
and is the form TFE_Specification_v2_5 line 525 calls a heuristic branch --
flagged, not hidden.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_ohlc_gate_starvation.py [N_SYMBOLS]
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_ohlc_gate_starvation_20260919.json"
H = 20
WARMUP_POS = 18          # signals at or below this are the initialization transient

spec = importlib.util.spec_from_file_location("qhk", ROOT / "quarantine_historical_kernel.py")
qhk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qhk)


def states(close_like: np.ndarray, dates: np.ndarray, sym: str, params) -> pd.DataFrame:
    g = pd.DataFrame({"Date": dates, "Symbol": sym, "Close": close_like})
    return qhk.build_state_rows(sym, g, params)


def main() -> int:
    n_sym = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    u = pd.read_parquet(ROOT / "quarantine_12k_universe.parquet")
    u["Date"] = pd.to_datetime(u.Date)
    syms = sorted(u.Symbol.unique())
    rng = np.random.default_rng(int.from_bytes(
        hashlib.blake2b(b"ohlc-starvation-20260919", digest_size=8).digest(), "big") % (2**63))
    samp = sorted(rng.choice(syms, size=min(n_sym, len(syms)), replace=False).tolist())
    print(f"[st] {len(samp)} symbols (blake2b-seeded)", flush=True)

    params = qhk.KernelParameters()
    res = {"CLOSE": [], "OHLC": []}
    gate_stats = {"CLOSE": [], "OHLC": []}

    for n, s in enumerate(samp):
        g = u[u.Symbol == s].sort_values("Date")
        if len(g) < 250:
            continue
        d = g.Date.values
        o, h, l, c = (g[k].values.astype(float) for k in ("Open", "High", "Low", "Close"))
        nd = len(c)
        fwd = np.full(nd, np.nan)
        fwd[: nd - H] = c[H:] / c[: nd - H] - 1.0

        for arm in ("CLOSE", "OHLC"):
            if arm == "CLOSE":
                ser, dts, day_of = c, d, np.arange(nd)
            else:
                ser = np.empty(nd * 4)
                ser[0::4], ser[1::4], ser[2::4], ser[3::4] = o, h, l, c
                dts = np.repeat(d, 4)
                day_of = np.repeat(np.arange(nd), 4)
            try:
                st = states(ser, dts, s, params)
            except Exception:
                continue
            if st is None or not len(st):
                continue
            for col in ("D_k", "M_k", "Rev_k", "B_k", "prev_B_k", "F_n", "x_m", "Close"):
                st[col] = pd.to_numeric(st[col], errors="coerce")
            st = st.dropna(subset=["D_k", "M_k", "Rev_k", "B_k", "prev_B_k", "F_n", "x_m"])
            if not len(st):
                continue
            # map each state row back to its day; keep the last state per day
            bi = st.bar_idx.values if "bar_idx" in st.columns else np.arange(len(st))
            dayi = np.clip(day_of[np.clip(bi, 0, len(day_of) - 1)], 0, nd - 1)
            st = st.assign(_day=dayi).groupby("_day", as_index=False).last()
            dday = st._day.values
            bk, pbk = st.B_k.values, st.prev_B_k.values
            gate_stats[arm].append((len(st), float(np.mean(bk != pbk) * 100)))
            L1 = ((st.D_k.values >= 0) & (st.Rev_k.values == 0) & (bk > pbk) & (st.M_k.values >= 0))
            L2 = c[dday] >= 5.0
            L3 = (st.x_m.values <= 0.50) & (st.F_n.values <= 1.65)
            pos = np.arange(len(st))
            late = pos > WARMUP_POS
            f = fwd[dday]
            ok = np.isfinite(f)
            for tag, m in (("pass", L1 & L2 & L3 & late & ok), ("rej", L1 & L2 & ~L3 & late & ok)):
                for x in f[m]:
                    res[arm].append((tag, float(x)))
        if (n + 1) % 200 == 0:
            print(f"[st] {n+1}/{len(samp)}", flush=True)

    out = {"symbols": len(samp), "warmup_pos": WARMUP_POS, "horizon_days": H, "arms": {}}
    print(f"\n{'arm':7s} {'rows/sym':>9s} {'B_k moves':>10s} {'signals':>8s} {'passWR':>8s} "
          f"{'rejected':>9s} {'rejWR':>7s} {'lift':>8s}")
    for arm in ("CLOSE", "OHLC"):
        gs = np.array(gate_stats[arm]) if gate_stats[arm] else np.zeros((1, 2))
        r = pd.DataFrame(res[arm], columns=["tag", "fwd"])
        p = r[r.tag == "pass"].fwd.values
        q = r[r.tag == "rej"].fwd.values
        pw = float(np.mean(p > 0) * 100) if len(p) else float("nan")
        rw = float(np.mean(q > 0) * 100) if len(q) else float("nan")
        out["arms"][arm] = {"rows_per_symbol": float(gs[:, 0].mean()),
                            "bk_move_pct": float(gs[:, 1].mean()),
                            "signals": int(len(p)), "pass_wr": pw,
                            "rejected": int(len(q)), "rej_wr": rw,
                            "pass_avg20d": float(np.mean(p) * 100) if len(p) else None,
                            "lift_pp": pw - rw}
        print(f"{arm:7s} {gs[:,0].mean():9.0f} {gs[:,1].mean():9.2f}% {len(p):8d} {pw:7.2f}% "
              f"{len(q):9d} {rw:6.2f}% {pw-rw:+7.2f}pp", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n[st] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
