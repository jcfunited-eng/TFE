"""CH2 book with the RELEASE EXIT — declared 2026-10-08 before running.
Days: CH2's field gate (gate1). Names: tradeable, in pool. Pick: random (8 seeds) and the
energy pick (D_k = +1 first). EXITS: FIXED10 (CH2 today: 10 sessions); REL10 = sell at the
close where the stock's next structure boundary is known (its release), cap 10 sessions;
REL30 = same, cap 30 (the measured structure scale). Slots free when a trade exits.
40 slots x $2,500, 0.20 % cost. Per year vs SPY. OUTPUT artifacts/ch4_uf/ch2_book_sim_release.json"""
import sys, json, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, "tools")
import ch2_book_sim as B
ev = B.load()
en = pd.read_parquet("artifacts/ch4_uf/ch2_energy_daily.parquet"); ev = ev.merge(en, on=["symbol", "date"], how="left")
st = pd.read_csv("artifacts/ch2_life/field_state_daily.csv", index_col=0); st.index = pd.to_datetime(st.index)
day = pd.DataFrame({"slow120": st.rel_up_val.rolling(120, min_periods=80).mean()}); day.index.name = "date_dt"
ev = ev.merge(day.reset_index(), on="date_dt", how="left")
ch = (ev.phase == "CHARGING").values; rl = (ev.releasing == "LO").values; rh = (ev.releasing == "HI").values
daydn = (ev.rel_up == "LO").values; rpu = (ev.release_polarity == "UP").values
c_epic = ev.epic_window.values & ~rpu; c_d2 = rh & daydn & ~rpu; c_p8 = ch & rl & ~rpu
s120dn = (ev.slow120 < 0.5).values
gate1 = (s120dn & c_epic) | (~s120dn & (c_epic | c_d2 | c_p8))
base = ev.tradeable.values.astype(bool) & ev.in_pool.values.astype(bool) & gate1.astype(bool)
up = (ev.D_k_live == 1).values
spy = ev.groupby("date").spy.first().sort_index()
spy_year = {y: round(float(spy[[d for d in spy.index if d.startswith(y)]].iloc[-1] / spy[[d for d in spy.index if d.startswith(y)]].iloc[0] - 1) * 100, 2) for y in sorted(set(d[:4] for d in spy.index))}
SLOTS, USD = 40, 2500.0
dates = sorted(ev.date.unique()); di = {d: i for i, d in enumerate(dates)}

def book(elig, rcol, hcol, rank):
    e = ev[elig & ev[rcol].notna().values].copy(); e["di"] = e.date.map(di); e["_rank"] = rank[elig & ev[rcol].notna().values]
    byd = {d: g.sort_values("_rank") for d, g in e.groupby("di")}
    open_until = {}; trades = []
    for i in range(len(dates)):
        open_until = {s: x for s, x in open_until.items() if x > i}
        free = SLOTS - len(open_until)
        if free <= 0 or i not in byd: continue
        g = byd[i]; g = g[~g.symbol.isin(open_until)]
        for _, row in g.head(free).iterrows():
            open_until[row.symbol] = i + int(row[hcol]); trades.append((row.year, float(row[rcol]) - 0.002))
    t = pd.DataFrame(trades, columns=["year", "net"])
    return {y: float(g.net.sum() * USD / 1000.0) for y, g in t.groupby("year")}

out = {"declared": __doc__, "spy": spy_year}
ev["r10x"] = ev.r10; ev["h10x"] = 10
for exit_name, rcol, hcol in (("FIXED10", "r10x", "h10x"), ("REL10", "r_rel10", "h_rel10"), ("REL30", "r_rel30", "h_rel30")):
    for pick in ("random", "energy"):
        runs = []
        for s in range(8):
            rnd = np.random.default_rng(200 + s).random(len(ev)); rank = rnd + (np.where(up, 0.0, 1.0) if pick == "energy" else 0.0)
            runs.append(book(base, rcol, hcol, rank))
        ys = [y for y in sorted(runs[0]) if y >= "2022"]
        per = {y: float(np.mean([r.get(y, 0.0) for r in runs])) for y in ys}; tots = [sum(r.get(y, 0.0) for y in ys) for r in runs]
        beat = sum(per[y] > spy_year[y] for y in ys); name = f"{exit_name}/{pick}"
        out[name] = {"per_year_mean": per, "totals_by_seed": tots}
        print(f"{name:15} " + " ".join(f"{y}:{per[y]:+6.1f}" for y in ys) + f" | total {np.mean(tots):+6.1f} (seeds {min(tots):+.1f}..{max(tots):+.1f}) beat SPY {beat}/{len(ys)}", flush=True)
print("SPY             " + " ".join(f"{y}:{spy_year[y]:+6.1f}" for y in sorted(spy_year) if y >= "2022") + f" | total {sum(v for y, v in spy_year.items() if y >= '2022'):+6.1f}")
json.dump(out, open("artifacts/ch4_uf/ch2_book_sim_release.json", "w"), indent=1)
