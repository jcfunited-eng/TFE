"""What a successful structure looks like to the kernel — Joseph's idea.

"you not only know how the S&P performed in the same period you also have the
data from the kernel for the S&P so you literally can evaluate that too to
understand what the patterns of successful physics structure look like since
that is the to-be comparison"

SPY is the structure everything in this chain has failed to beat. So run the
kernel on SPY itself and describe what it reads. Then ask how a typical
individual body differs from it.

This is DESCRIPTION. No rule is proposed here and nothing is selected on the
output. Provenance: the question is Joseph's; the way it is tabulated is MINE.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_benchmark_signature.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
LANES = ROOT / "artifacts" / "ch4_uf" / "dense_lanes_20260919"
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_benchmark_signature_20260919.json"
BENCH = ["SPY", "QQQ", "DIA", "IWM"]

from ch2_runup_pattern import label_body  # noqa: E402  (zigzag labels, declared there)


def fields(df: pd.DataFrame) -> dict:
    s, r, u = df.s_uf.values, df.r_uf.values, df.u_star_k.values
    b = df.b_k.values
    return {
        "sessions": int(len(df)),
        "S_gt_Ustar_pct": float((s > u).mean() * 100),
        "R_gt_Ustar_pct": float((r > u).mean() * 100),
        "both_gt_Ustar_pct": float(((s > u) & (r > u)).mean() * 100),
        "neither_gt_Ustar_pct": float(((s <= u) & (r <= u)).mean() * 100),
        "D_neg_pct": float((df.d_k == -1).mean() * 100),
        "D_zero_pct": float((df.d_k == 0).mean() * 100),
        "D_pos_pct": float((df.d_k == 1).mean() * 100),
        "M_bend_back_pct": float((df.m_k < 0).mean() * 100),
        "R_rev_pct": float((df.r_rev_k == 1).mean() * 100),
        "carry_intact_pct": float((b == 0).mean() * 100),
        "carry_spending_pct": float(((b > -1) & (b < 0)).mean() * 100),
        "carry_exhausted_pct": float((b == -1).mean() * 100),
        "B_mean": float(b.mean()),
        "P0_quiet_pct": float((df.p_k == 0).mean() * 100),
        "P1_stressed_pct": float((df.p_k == 1).mean() * 100),
        "P2_adverse_pct": float((df.p_k == 2).mean() * 100),
        "S_mean": float(s.mean()), "R_mean": float(r.mean()), "Ustar_mean": float(u.mean()),
    }


def main() -> int:
    files = sorted(LANES.glob("*.parquet"))
    print(f"[bench] dense lanes available: {len(files)}", flush=True)
    bench, others, per_body = {}, [], {}
    for f in files:
        df = pd.read_parquet(f)
        if len(df) < 100:
            continue
        sym = f.stem
        per_body[sym] = fields(df)
        if sym in BENCH:
            bench[sym] = (df, per_body[sym])
        else:
            others.append(df)
    if not bench:
        print("[bench] no benchmark lane yet", flush=True)
        return 1
    pool = pd.concat(others, ignore_index=True) if others else None
    print(f"[bench] benchmarks: {sorted(bench)} | individual bodies pooled: "
          f"{len(others)} ({0 if pool is None else len(pool)} sessions)", flush=True)

    out = {"generated_at_utc": pd.Timestamp.now("UTC").isoformat(),
           "note": "description only; the question is Joseph's, the tabulation is MINE",
           "benchmarks": {k: v[1] for k, v in bench.items()},
           "individual_bodies_pooled": fields(pool) if pool is not None else None,
           "per_body": per_body}

    keys = ["both_gt_Ustar_pct", "neither_gt_Ustar_pct", "D_pos_pct", "D_zero_pct",
            "D_neg_pct", "M_bend_back_pct", "R_rev_pct", "carry_intact_pct",
            "carry_spending_pct", "carry_exhausted_pct", "P0_quiet_pct",
            "P2_adverse_pct", "S_mean", "R_mean", "Ustar_mean"]
    print(f"\n{'reading':26s} " + " ".join(f"{b:>8s}" for b in sorted(bench)) + f" {'stocks':>9s}")
    for k in keys:
        row = " ".join(f"{bench[b][1][k]:8.2f}" for b in sorted(bench))
        pv = out["individual_bodies_pooled"][k] if pool is not None else float("nan")
        print(f"{k:26s} {row} {pv:9.2f}")

    # SPY's own rises and falls, in the kernel's terms
    for sym in sorted(bench):
        df = bench[sym][0].reset_index(drop=True)
        lab = label_body(df.close.values)
        out.setdefault("benchmark_by_phase", {})[sym] = {
            "rising": fields(df[lab == 1]) if (lab == 1).any() else None,
            "falling": fields(df[lab == 2]) if (lab == 2).any() else None,
            "other": fields(df[lab == 0]) if (lab == 0).any() else None}
        r, fl = out["benchmark_by_phase"][sym]["rising"], out["benchmark_by_phase"][sym]["falling"]
        if r and fl:
            print(f"\n{sym} in its own advances vs declines:")
            for k in ["both_gt_Ustar_pct", "D_pos_pct", "carry_spending_pct",
                      "carry_exhausted_pct", "R_rev_pct", "P0_quiet_pct"]:
                print(f"   {k:26s} rising {r[k]:7.2f}   falling {fl[k]:7.2f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n[bench] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
