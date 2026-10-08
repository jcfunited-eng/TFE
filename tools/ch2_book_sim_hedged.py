"""CH2 book sim, HEDGED arms — declared 2026-10-08 before running (Joe: "is there
anything we could do to fix it"). Same book, eligibility, slot rule and costs as
tools/ch2_book_sim.py (B2: F2 set, most-fallen-first, 20 x $5k, 10 sessions,
0.20% round trip). Hedge cost +0.05% per trade (declared).
  H1  B2 trade return minus SPY's return over the same 10 sessions
  H2  B2 trade return minus the equal-weight average 10-session return of every
      in-pool tradeable name that day (the small-company market CH2 swims in)
Report per year on $100k next to unhedged B2 and SPY buy-and-hold. Filed either way.
OUTPUT: artifacts/ch4_uf/ch2_book_sim_hedged.json"""
import json, numpy as np, pandas as pd, sys
sys.path.insert(0, ".")
from tools.ch2_book_sim import load, run_book, summarize, OUT as _O, SLOT_USD, COST, HOLD
HEDGE_COST = 0.0005
ev = load()
spy = ev.groupby("date").spy.first().sort_index()
spy_r10 = (spy.shift(-HOLD) / spy - 1).to_dict()
base = ev.tradeable.values & ev.in_pool.values
pool_r10 = ev[base].groupby("date").r10.mean().to_dict()
spy_year = {}
for y in sorted(set(d[:4] for d in spy.index)):
    s = spy[[d for d in spy.index if d.startswith(y)]]; spy_year[y] = round(float(s.iloc[-1] / s.iloc[0] - 1) * 100, 2)
F2 = base & ev.field_long.values & ev.pre.values & ~ev.late.values & ~ev.post.values
tr = run_book(ev, F2, "own_10", None)
res = {"declared": __doc__, "spy_buy_hold_pct": spy_year}
res["B2 unhedged"] = summarize(tr, spy_year)
for name, ref in (("H1 minus SPY", spy_r10), ("H2 minus small-company pool", pool_r10)):
    t = tr.copy(); r = t.date.map(ref)
    t = t[r.notna()].copy(); t["gross"] = t.gross - r[r.notna()]; t["net"] = t.gross - COST - HEDGE_COST
    res[name] = summarize(t, spy_year)
for k in ("B2 unhedged", "H1 minus SPY", "H2 minus small-company pool"):
    v = res[k]; print(k.ljust(30), " ".join(f"{y}:{v[y]['return_on_100k_pct']:+6.1f}(dd {v[y]['max_drawdown_usd']/1000:+.1f}k)" for y in sorted(v)))
print("SPY buy-and-hold".ljust(30), " ".join(f"{y}:{spy_year[y]:+6.1f}" for y in sorted(spy_year)))
json.dump(res, open("artifacts/ch4_uf/ch2_book_sim_hedged.json", "w"), indent=1); print("filed")
