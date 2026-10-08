"""CH2 gated book — the 09-30 result (+68% 2022-26) recovered from the session that ran
it inline (never filed), plus the EXACT LIVE LAW beside it (added 10-08, declared before
running). Same book machinery as tools/ch2_book_sim.py (hold 10 sessions, 0.20% cost).
ARMS:
  G1P   gate1 with slot priority (the 09-30 +68% arm): field rules epic | down-release |
        charging&quiet, not polarity UP; slow120 < 0.5 -> epics only; ANY tradeable name;
        slot priority epic > down-release > charging&quiet. 50 slots x $2,000.
  LIVE  what CH2 runs (tools/ch2_field_nightly_db.py + strategist): same gate, PLUS the
        filing filter (61-95 days since last filing, not late 96-130, not 0-3 post),
        names taken closest-to-report first (dsl descending); 40 slots x $2,500 (~2.5%).
  LIVE_NOFILE  LIVE without the filing filter (G1P's set, live's slot size).
Exits NOT modelled: live's -20% brake and +20%->+15% profit lock (both only trim tails).
OUTPUT artifacts/ch4_uf/ch2_book_sim_gated_live.json"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "tools")
import ch2_book_sim as B
ev = B.load()
st = pd.read_csv("artifacts/ch2_life/field_state_daily.csv", index_col=0); st.index = pd.to_datetime(st.index)
day = pd.DataFrame({"slow120": st.rel_up_val.rolling(120, min_periods=80).mean()}); day.index.name = "date_dt"
ev = ev.merge(day.reset_index(), on="date_dt", how="left")
ch = (ev.phase == "CHARGING").values; rl = (ev.releasing == "LO").values; rh = (ev.releasing == "HI").values
daydn = (ev.rel_up == "LO").values; rpu = (ev.release_polarity == "UP").values
c_epic = ev.epic_window.values & ~rpu; c_d2 = rh & daydn & ~rpu; c_p8 = ch & rl & ~rpu
ev["prio"] = np.where(c_epic, 0, np.where(c_d2, 1, np.where(c_p8, 2, 9)))
ev["neg_dsl"] = -ev.dsl.fillna(-1)
base = ev.tradeable.values & ev.in_pool.values
s120dn = (ev.slow120 < 0.5).values
gate1 = (s120dn & c_epic) | (~s120dn & (c_epic | c_d2 | c_p8))
filing = ev.pre.values & ~ev.late.values & ~ev.post.values
spy = ev.groupby("date").spy.first().sort_index()
spy_year = {y: round(float(spy[[d for d in spy.index if d.startswith(y)]].iloc[-1] / spy[[d for d in spy.index if d.startswith(y)]].iloc[0] - 1) * 100, 2) for y in sorted(set(d[:4] for d in spy.index))}
out = {"declared": __doc__, "spy": spy_year}
def book(name, elig, rank, slots):
    B.SLOTS = slots; B.SLOT_USD = 100000.0 / slots
    t = B.summarize(B.run_book(ev, elig, rank, None if rank else 0), spy_year)
    out[name] = t
    ys = [y for y in sorted(t) if y >= "2022"]
    tot = sum(t[y]["return_on_100k_pct"] for y in ys); beat = sum(t[y]["return_on_100k_pct"] > spy_year[y] for y in ys)
    print(f"{name:12} " + " ".join(f"{y}:{t[y]['return_on_100k_pct']:+6.1f}" for y in ys) + f" | total {tot:+6.1f} beat SPY {beat}/{len(ys)} worst dd ${min(t[y]['max_drawdown_usd'] for y in ys):,.0f}")
ev["prio_then_dsl"] = ev.prio * 1000 + ev.neg_dsl     # live sorts by dsl; priority is the day's, same for all names
book("G1P", base & gate1, "prio", 50)
book("LIVE", base & gate1 & filing, "neg_dsl", 40)
book("LIVE_NOFILE", base & gate1, "prio", 40)
print("SPY         " + " ".join(f"{y}:{spy_year[y]:+6.1f}" for y in sorted(spy_year) if y >= "2022") + f" | total {sum(v for y, v in spy_year.items() if y >= '2022'):+6.1f}")
json.dump(out, open("artifacts/ch4_uf/ch2_book_sim_gated_live.json", "w"), indent=1)

# ---- added 10-08: order check. G1P / LIVE_NOFILE took same-priority names in file order
# (~alphabetical). Average over 8 random orders is the honest expectation.
def avg_book(name, elig, slots, seeds=range(8)):
    B.SLOTS = slots; B.SLOT_USD = 100000.0 / slots
    runs = [B.summarize(B.run_book(ev, elig, None, s), spy_year) for s in seeds]
    ys = [y for y in sorted(runs[0]) if y >= "2022"]
    per = {y: float(np.mean([r[y]["return_on_100k_pct"] for r in runs])) for y in ys}
    tots = [sum(r[y]["return_on_100k_pct"] for y in ys) for r in runs]
    out[name] = {"per_year_mean": per, "totals_by_seed": tots}
    print(f"{name:22} " + " ".join(f"{y}:{per[y]:+6.1f}" for y in ys) + f" | total mean {np.mean(tots):+6.1f} (seeds {min(tots):+.1f}..{max(tots):+.1f})")
avg_book("ANY_NAME random 50", base & gate1, 50)
avg_book("ANY_NAME random 40", base & gate1, 40)
avg_book("LIVE_FILING random 40", base & gate1 & filing, 40)
json.dump(out, open("artifacts/ch4_uf/ch2_book_sim_gated_live.json", "w"), indent=1)
