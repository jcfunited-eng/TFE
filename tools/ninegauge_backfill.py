"""ninegauge_backfill.py — the full nine-gauge field, computed locally.

Production's own engine (uf_core.uf_structural_engine.compute_structural_state
— the code that fills runtime snapshots) walked causally over every operating
life: for each session d, the engine reads the trailing bars up to and
including d (window capped at 1260 bars, production's own five-year
reconstruction convention) and reports that day's nine gauges:
D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, S_UF, R_UF.

Declared constants (before running, per the timing discipline):
  START = 2021-06-01  (first walked session; 90 sessions of approach
                       history before the first cataloged rises of Sept 2021)
  MIN_BARS = 30       (engine's own minimum from production's walker;
                       bar_count recorded so young lives are distinguishable)
  WINDOW = 1260       (trailing bar cap, production convention)

Output: artifacts/ninegauge/lanes/<SYM>.parquet with
  date, close, volume, bar_count, D_k, M_k, R_rev_k, U_star_k, C_k, P_k,
  B_k, S_UF, R_UF
Resumable: a symbol whose file already reaches its last eligible session
is skipped. One life failing never kills the pass.
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from multiprocessing import Pool
from types import SimpleNamespace

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "artifacts", "ninegauge", "lanes")
START = "2021-06-01"
MIN_BARS = 30
WINDOW = 1260
GAUGES = ("D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k",
          "S_UF", "R_UF")


def walk_life(args) -> str:
    sym, dates, closes, volumes = args
    import pandas as pd
    out_path = os.path.join(OUT, f"{sym}.parquet")
    try:
        n = len(closes)
        idx0 = None
        for i in range(n):
            if dates[i] >= START and i + 1 >= MIN_BARS:
                idx0 = i
                break
        if idx0 is None:
            return f"{sym}: too short"
        last_date = dates[n - 1]
        if os.path.exists(out_path):
            prior = pd.read_parquet(out_path, columns=["date"])
            if len(prior) and str(prior["date"].iloc[-1]) == last_date:
                return f"{sym}: current"
        from uf_core.uf_structural_engine import compute_structural_state
        ts = [pd.Timestamp(d) for d in dates]
        rows = []
        for i in range(idx0, n):
            lo = max(0, i + 1 - WINDOW)
            bars = [SimpleNamespace(close=float(c), timestamp=t)
                    for c, t in zip(closes[lo:i + 1], ts[lo:i + 1])]
            try:
                st = compute_structural_state(sym, bars)
            except Exception:  # noqa: BLE001
                continue
            row = {"date": dates[i], "close": float(closes[i]),
                   "volume": float(volumes[i]), "bar_count": i + 1 - lo}
            ok = True
            for g in GAUGES:
                v = st.get(g)
                if v is None:
                    ok = False
                    break
                row[g] = float(v)
            if ok:
                rows.append(row)
        if not rows:
            return f"{sym}: EMPTY"
        tmp = out_path + f".tmp{os.getpid()}"
        pd.DataFrame(rows).to_parquet(tmp)
        os.replace(tmp, out_path)
        return f"{sym}: {len(rows)} readings"
    except Exception as err:  # noqa: BLE001 — one life never kills the pass
        return f"{sym}: FAILED {type(err).__name__}: {err}"


def main() -> None:
    import pandas as pd
    os.makedirs(OUT, exist_ok=True)
    tt = json.load(open(os.path.join(ROOT, "artifacts", "ch6_harvest",
                                     "ticker_types.json")))
    op = {s for s, t in tt.items() if t in ("CS", "ADRC")}
    store = pd.read_parquet(os.path.join(ROOT, "ch4_live_store.parquet"),
                            columns=["Date", "Symbol", "Close", "Volume"])
    store["d"] = store["Date"].astype(str).str[:10]
    jobs = []
    for sym, g in store.groupby("Symbol"):
        if sym not in op:
            continue
        g = g.sort_values("d")
        jobs.append((sym, g["d"].tolist(),
                     g["Close"].to_numpy(float), g["Volume"].to_numpy(float)))
    del store
    jobs.sort(key=lambda j: j[0])
    total = len(jobs)
    print(f"[ninegauge] {total} operating lives to walk", flush=True)
    t0 = time.time()
    done = 0
    with Pool(processes=14, maxtasksperchild=20) as pool:
        for msg in pool.imap_unordered(walk_life, jobs, chunksize=4):
            done += 1
            if done % 100 == 0 or "FAILED" in msg:
                el = time.time() - t0
                print(f"[ninegauge] {done}/{total} ({el/60:.0f}m) last: {msg}",
                      flush=True)
    print(f"[ninegauge] DONE {done}/{total} in {(time.time()-t0)/60:.0f}m",
          flush=True)


if __name__ == "__main__":
    main()
