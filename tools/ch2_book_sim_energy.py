"""CH2 book with the stock's own ENERGY as the pick — declared 2026-10-08 before running.
Days: CH2's field gate (gate1, as tools/ch2_book_sim_gated.py). Names: tradeable, in pool.
PICK (ENERGY): names whose latest known structure reading D_k = +1 first (energy building,
the one stock-level reading that rose before large moves in both halves), then the rest;
random order within each group. Compared with ANY_NAME (random) and the LIVE rules
(filing filter, random order), 40 slots x $2,500, hold 10, 0.20 % cost, 8 seeds each.
Per year vs SPY. OUTPUT artifacts/ch4_uf/ch2_book_sim_energy.json"""
import sys, json, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, "tools")
import ch2_book_sim as B
ev = B.load()
en = pd.read_parquet("artifacts/ch4_uf/ch2_energy_daily.parquet")
ev = ev.merge(en, on=["symbol", "date"], how="left")
st = pd.read_csv("artifacts/ch2_life/field_state_daily.csv", index_col=0); st.index = pd.to_datetime(st.index)
day = pd.DataFrame({"slow120": st.rel_up_val.rolling(120, min_periods=80).mean()}); day.index.name = "date_dt"
ev = ev.merge(day.reset_index(), on="date_dt", how="left")
ch = (ev.phase == "CHARGING").values; rl = (ev.releasing == "LO").values; rh = (ev.releasing == "HI").values
daydn = (ev.rel_up == "LO").values; rpu = (ev.release_polarity == "UP").values
c_epic = ev.epic_window.values & ~rpu; c_d2 = rh & daydn & ~rpu; c_p8 = ch & rl & ~rpu
s120dn = (ev.slow120 < 0.5).values
gate1 = (s120dn & c_epic) | (~s120dn & (c_epic | c_d2 | c_p8))
base = (ev.tradeable.values.astype(bool) & ev.in_pool.values.astype(bool) & gate1.astype(bool))
filing = (ev.pre.values.astype(bool) & ~ev.late.values.astype(bool) & ~ev.post.values.astype(bool))
up = (ev.D_k_live == 1).values
print("gate days with an energy reading:", round(float(ev.D_k_live[base].notna().mean()) * 100, 1), "% | share D_k=+1:", round(float(up[base].mean()) * 100, 1), "%")
spy = ev.groupby("date").spy.first().sort_index()
spy_year = {y: round(float(spy[[d for d in spy.index if d.startswith(y)]].iloc[-1] / spy[[d for d in spy.index if d.startswith(y)]].iloc[0] - 1) * 100, 2) for y in sorted(set(d[:4] for d in spy.index))}
B.SLOTS = 40; B.SLOT_USD = 2500.0
out = {"declared": __doc__, "spy": spy_year}
def arm(name, elig, prefer=None):
    runs = []
    for s in range(8):
        rnd = np.random.default_rng(100 + s).random(len(ev))
        ev["_rank"] = rnd + (0 if prefer is None else np.where(prefer, 0.0, 1.0))
        runs.append(B.summarize(B.run_book(ev, elig, "_rank", None), spy_year))
    ys = [y for y in sorted(runs[0]) if y >= "2022"]
    per = {y: float(np.mean([r[y]["return_on_100k_pct"] for r in runs])) for y in ys}
    tots = [sum(r[y]["return_on_100k_pct"] for y in ys) for r in runs]
    beat = sum(per[y] > spy_year[y] for y in ys)
    out[name] = {"per_year_mean": per, "totals_by_seed": tots}
    print(f"{name:10} " + " ".join(f"{y}:{per[y]:+6.1f}" for y in ys) + f" | total {np.mean(tots):+6.1f} (seeds {min(tots):+.1f}..{max(tots):+.1f}) beat SPY {beat}/{len(ys)}")
arm("ANY_NAME", base)
arm("LIVE", base & filing)
arm("ENERGY", base, prefer=up)
arm("ENERGY+LIVE", base & filing, prefer=up)
print("SPY        " + " ".join(f"{y}:{spy_year[y]:+6.1f}" for y in sorted(spy_year) if y >= "2022") + f" | total {sum(v for y, v in spy_year.items() if y >= '2022'):+6.1f}")
json.dump(out, open("artifacts/ch4_uf/ch2_book_sim_energy.json", "w"), indent=1)
