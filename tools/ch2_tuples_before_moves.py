"""One ticker as a single blob stretched through time: the kernel's tuple on
every day, and what the price did after. Then: the tuples before rises, and
the tuples before falls. All fields. All of them. Nothing chosen.

Joe, 2026-09-30: "if you look at a ticker as a single blob that stretched
through time — what were the tuples at before rises and what were they at
falls — ALL of them."

Day t's tuple = the production chain run on closes through t (the reading
the system has on that day), last gate's fields. Own resolution per ticker
(tools/ch2_tuples_over_time.py). Rise: close 20 sessions later >= +8%.
Fall: <= -8%. Else flat.

Usage: python3 tools/ch2_tuples_before_moves.py SYMBOL [--years 5] [--move 0.08]
Writes artifacts/ch2_life/<SYMBOL>_daily_tuples.csv and prints the rows.
"""
import argparse, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))

FIELDS = ["age", "D", "M", "Rev", "Ustar", "C", "P", "B", "S_UF", "R_UF", "R", "URF", "g", "Hy", "IAS", "U", "w", "psi", "S", "regime"]
_close = None
_tau = None


def _init(close, tau):
    global _close, _tau
    _close, _tau = close, tau


def _day(t):
    import uf_core.config as cfg
    from tools.ch2_draw_life import chain
    cfg.KERNEL_THRESHOLDS.tau_D = float(_tau)
    sev, gates, interps, res, dsf = chain(_close.iloc[: t + 1])
    from uf_core.uf_structural_engine import _compute_stability_from_l4
    from uf_core.layer4 import compute_directional_signal
    gt, it, rs, d = gates[-1], interps[-1], res[-1], dsf[-1]
    stab = _compute_stability_from_l4(res, compute_directional_signal(res))
    s_uf = max(0.0, min(1.0, 0.5 * stab["dsf"] + 0.5 * stab["directional"]))
    r_uf = max(0.0, min(1.0, stab["R_mean"]))
    return (t, t - gt.start_idx + 1, int(d.D_k), round(d.M_k, 3), int(d.R_rev_k), round(d.U_star_k, 3), int(d.C_k), int(d.P_k),
            round(d.B_k, 3), round(s_uf, 3), round(r_uf, 3), round(rs.R_k, 3), round(rs.URF_k, 3), int(rs.g_k), int(rs.Hyst_k), int(rs.IAS_k), round(rs.U_k, 3),
            round(it.w_k, 3), round(it.psi_k, 3), round(it.S_k, 3), it.regime)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("symbol"); ap.add_argument("--years", type=float, default=5.0)
    ap.add_argument("--move", type=float, default=0.08); ap.add_argument("--hold", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6); a = ap.parse_args()
    from tools.ch2_tuples_over_time import own_resolution
    store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol", "Close"])
    g = store[store.Symbol == a.symbol].sort_values("Date")
    close = pd.Series(g.Close.values.astype(float), index=pd.to_datetime(g.Date.values))
    tau, typical = own_resolution(close.values)
    n = len(close); start = max(252, n - int(a.years * 252))
    with Pool(a.workers, initializer=_init, initargs=(close, tau)) as pool:
        rows = pool.map(_day, range(start, n), chunksize=8)
    df = pd.DataFrame(rows, columns=["t"] + FIELDS)
    df.insert(0, "date", [str(close.index[t].date()) for t in df.t])
    df["close"] = close.values[df.t]
    fwd = np.full(len(df), np.nan)
    ok = df.t.values + a.hold < n
    fwd[ok] = close.values[df.t.values[ok] + a.hold] / close.values[df.t.values[ok]] - 1
    df["fwd%"] = np.round(100 * fwd, 1)
    df["after"] = np.where(fwd >= a.move, "RISE", np.where(fwd <= -a.move, "FALL", np.where(np.isnan(fwd), "?", "flat")))
    out = ROOT / "artifacts" / "ch2_life" / f"{a.symbol}_daily_tuples.csv"
    df.drop(columns=["t"]).to_csv(out, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 5000)
    print(f"{a.symbol}  tau_D={tau:.4f} (3.77 x typical day {typical:.4f})  days {len(df)}  "
          f"RISE(+{a.move*100:.0f}% in {a.hold}) {int((df.after=='RISE').sum())}  FALL {int((df.after=='FALL').sum())}  flat {int((df.after=='flat').sum())}")
    cols = ["date", "close", "fwd%"] + FIELDS
    for label in ("RISE", "FALL"):
        print(f"\n===== tuples on days BEFORE a {label} =====")
        print(df[df.after == label][cols].to_string(index=False))
    print(f"\n===== every field, its values before RISE vs before FALL vs flat (min / 25% / 50% / 75% / max) =====")
    for f in FIELDS[:-1]:
        line = f"{f:>6}"
        for label in ("RISE", "FALL", "flat"):
            v = df[df.after == label][f].astype(float)
            q = v.quantile([0, .25, .5, .75, 1]).values
            line += f" | {label:4} {q[0]:>6.2f} {q[1]:>6.2f} {q[2]:>6.2f} {q[3]:>6.2f} {q[4]:>6.2f}"
        print(line)
    for label in ("RISE", "FALL", "flat"):
        print(f"regime before {label}:", df[df.after == label].regime.value_counts().to_dict())
    print("wrote", out)


if __name__ == "__main__":
    main()
