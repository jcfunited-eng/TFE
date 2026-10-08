"""Energy pick on the BLIND 1,500 — declared 2026-10-08 before running. Same field gate
(market-wide daily state from the studied run), the blind names as the tradeable universe:
tradeable_flags on the day, >= 252 bars, r10 = close t+10 / close t - 1. Arms: random vs
energy (D_k = +1 first), 8 seeds, 40 x $2,500, hold 10, 0.20 % cost. PASS (declared): energy
beats random in total AND in >= 4 of 5 years (2022-2026).
OUTPUT artifacts/ch4_uf/ch2_book_sim_blind.json"""
import sys, json, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, "tools")
import ch2_book_sim as B
from ch2_canon_census import tradeable_flags
ev0 = B.load()
st = pd.read_csv("artifacts/ch2_life/field_state_daily.csv", index_col=0); st.index = pd.to_datetime(st.index)
ev0 = ev0.merge(pd.DataFrame({"slow120": st.rel_up_val.rolling(120, min_periods=80).mean()}).rename_axis("date_dt").reset_index(), on="date_dt", how="left")
ch = (ev0.phase == "CHARGING").values; rl = (ev0.releasing == "LO").values; rh = (ev0.releasing == "HI").values
daydn = (ev0.rel_up == "LO").values; rpu = (ev0.release_polarity == "UP").values
c_epic = ev0.epic_window.values & ~rpu; c_d2 = rh & daydn & ~rpu; c_p8 = ch & rl & ~rpu
s120dn = (ev0.slow120 < 0.5).values
ev0["gate"] = ((s120dn & c_epic) | (~s120dn & (c_epic | c_d2 | c_p8))).astype(bool)
gate_day = ev0.groupby("date").gate.first().to_dict(); spy = ev0.groupby("date").spy.first().sort_index()
spy_year = {y: round(float(spy[[d for d in spy.index if d.startswith(y)]].iloc[-1] / spy[[d for d in spy.index if d.startswith(y)]].iloc[0] - 1) * 100, 2) for y in sorted(set(d[:4] for d in spy.index))}
rows = []
for s, d in pd.read_parquet("artifacts/ch2_life/ohlcv_blind.parquet").groupby("Symbol"):
    d = d.sort_values("Date").reset_index(drop=True); tf = tradeable_flags(d)
    c = d.Close.values; r10 = np.r_[c[10:] / c[:-10] - 1, np.full(10, np.nan)]
    rows.append(pd.DataFrame({"symbol": s, "date": d.Date.astype(str).str[:10], "tradeable": tf.tradeable.values, "r10": r10}))
bl = pd.concat(rows); bl = bl[bl.r10.notna() & bl.tradeable]
bl["gate"] = bl.date.map(gate_day).fillna(False).astype(bool); bl = bl[bl.gate]
bl = bl.merge(pd.read_parquet("artifacts/ch4_uf/ch2_energy_daily_blind.parquet")[["symbol", "date", "D_k_live"]], on=["symbol", "date"], how="left")
bl["year"] = bl.date.str[:4]; bl = bl[bl.year >= "2022"].reset_index(drop=True)
print("blind gate-day rows", len(bl), "names", bl.symbol.nunique(), "| with energy reading", round(float(bl.D_k_live.notna().mean()) * 100, 1), "%")
B.SLOTS = 40; B.SLOT_USD = 2500.0
up = (bl.D_k_live == 1).values; out = {"declared": __doc__, "spy": spy_year}
res = {}
for pick in ("random", "energy"):
    runs = []
    for s in range(8):
        bl["_rank"] = np.random.default_rng(300 + s).random(len(bl)) + (np.where(up, 0.0, 1.0) if pick == "energy" else 0.0)
        runs.append(B.summarize(B.run_book(bl, np.ones(len(bl), bool), "_rank", None), spy_year))
    ys = [y for y in sorted(runs[0]) if y >= "2022"]
    per = {y: float(np.mean([r[y]["return_on_100k_pct"] for r in runs if y in r])) for y in ys}; tots = [sum(r[y]["return_on_100k_pct"] for y in ys if y in r) for r in runs]
    res[pick] = per; out[pick] = {"per_year_mean": per, "totals_by_seed": tots}
    print(f"{pick:7} " + " ".join(f"{y}:{per[y]:+6.1f}" for y in ys) + f" | total {np.mean(tots):+6.1f} (seeds {min(tots):+.1f}..{max(tots):+.1f})")
ys = sorted(res["random"]); wins = sum(res["energy"][y] > res["random"][y] for y in ys)
tot_e, tot_r = sum(res["energy"].values()), sum(res["random"].values())
out["verdict"] = {"energy_beats_random_years": f"{wins}/{len(ys)}", "total_energy": tot_e, "total_random": tot_r, "pass": bool(tot_e > tot_r and wins >= 4)}
print("energy beats random in", f"{wins}/{len(ys)}", "years; totals", round(tot_e, 1), "vs", round(tot_r, 1), "| PASS" if out["verdict"]["pass"] else "| FAIL")
print("SPY     " + " ".join(f"{y}:{spy_year[y]:+6.1f}" for y in ys))
json.dump(out, open("artifacts/ch4_uf/ch2_book_sim_blind.json", "w"), indent=1)
