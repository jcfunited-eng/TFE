"""CH2 book simulation — the edge after capital, costs and a slot rule. Declared before running.

BOOK: $100,000; 20 slots of $5,000; a slot holds one name for 10 sessions
(enter at the close of the signal day, exit at the close 10 sessions
later). Cost: 0.20 % round trip per trade (declared; spread + commission).
Slot size fixed (no compounding); yearly P&L on $100k.

ELIGIBLE (from the field + particle results, unchanged):
  F2  the field is long (epic window OR field-wide down-release OR
      charging & quiet; and NOT polarity UP), the particle is tradeable,
      61–95 days into its reporting cycle, not a late filer, not 0–3 days
      after a report.
SLOT RULE (declared): when eligible names exceed free slots, take the
  ones that fell the most over the last 10 sessions (the particle's own
  signed displacement, L0), most fallen first.
ARMS: B0 random tradeable names every day (the null book, 20 seeds);
      B1 field-long only, random particle (20 seeds); B2 = F2 with the slot rule;
      B3 = F2 with random slot fill (20 seeds) — to separate the rule from the set.
ELIGIBILITY AS OF THE YEAR: a name is in the pool for year Y only if it
  had >= 252 bars before Jan 1 of Y and was tradeable on its last day of
  Y−1. Names that died before today are still missing (survivorship —
  stated, not fixed here).
REPORT per year: trades, WR, gross and net P&L, return on $100k, days
  with any position, max drawdown of the yearly equity path; SPY
  buy-and-hold the same year. Filed either way.
OUTPUT: artifacts/ch4_uf/ch2_book_sim.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SLOTS, SLOT_USD, HOLD, COST = 20, 5000.0, 10, 0.002
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_book_sim.json"


def load():
    f = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "filings_pool.parquet"); f["last_filing"] = pd.to_datetime(f.filing_date).astype("datetime64[ns]")
    f = f[f.timeframe.isin(["quarterly", "annual"])].sort_values("last_filing").drop_duplicates(["Symbol", "last_filing"])
    bars = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet", columns=["Date", "Symbol", "Close", "Volume"]).sort_values(["Symbol", "Date"])
    bars["Date"] = bars.Date.astype("datetime64[ns]")
    bars["r10"] = bars.groupby("Symbol").Close.shift(-HOLD) / bars.Close - 1
    bars["own_10"] = bars.Close / bars.groupby("Symbol").Close.shift(10) - 1
    bars["nbar"] = bars.groupby("Symbol").cumcount()
    bars = bars.sort_values("Date")
    m = pd.merge_asof(bars, f[["Symbol", "last_filing"]], left_on="Date", right_on="last_filing", by="Symbol", direction="backward")
    m["dsl"] = (m.Date - m.last_filing).dt.days; m["date"] = m.Date.astype(str).str[:10]
    ev = pd.read_parquet(ROOT / "artifacts" / "ch4_uf" / "ch2_particle_days_B.parquet").merge(m[["Symbol", "date", "r10", "own_10", "dsl", "nbar"]].rename(columns={"Symbol": "symbol"}), on=["symbol", "date"], how="inner")
    day = pd.read_csv(ROOT / "artifacts" / "ch2_life" / "field_temperature_daily.csv", index_col=0); day.index = pd.to_datetime(day.index)
    st = pd.read_csv(ROOT / "artifacts" / "ch2_life" / "field_state_daily.csv", index_col=0); st.index = pd.to_datetime(st.index)
    day = day.join(st[["rel_up"]]); day.index.name = "date_dt"; ev["date_dt"] = pd.to_datetime(ev.date)
    ev = ev.merge(day[["epic_window", "phase", "releasing", "release_polarity", "rel_up", "spy"]].reset_index(), on="date_dt", how="inner")
    ev = ev[ev.r10.notna()].copy()
    ch = (ev.phase == "CHARGING").values; rl = (ev.releasing == "LO").values; rh = (ev.releasing == "HI").values; daydn = (ev.rel_up == "LO").values; rpu = (ev.release_polarity == "UP").values
    ev["field_long"] = ((ev.epic_window.values) | (rh & daydn) | (ch & rl)) & ~rpu
    d = ev.dsl.values; has = ~np.isnan(d)
    ev["pre"] = has & (d >= 61) & (d <= 95); ev["late"] = has & (d >= 96) & (d <= 130); ev["post"] = has & (d <= 3)
    ev["year"] = ev.date.str[:4]
    # eligibility as of the year: >= 252 bars before the year and tradeable on the last day of the prior year
    last_prev = ev.sort_values("date").groupby(["symbol", "year"]).tail(1)[["symbol", "year", "tradeable", "nbar"]]
    last_prev["year"] = (last_prev.year.astype(int) + 1).astype(str)
    ok = last_prev[(last_prev.tradeable) & (last_prev.nbar >= 252)][["symbol", "year"]].assign(in_pool=True)
    ev = ev.merge(ok, on=["symbol", "year"], how="left"); ev["in_pool"] = ev.in_pool.fillna(False)
    return ev


def run_book(ev: pd.DataFrame, elig: np.ndarray, rank_col: str | None, seed: int | None):
    rng = np.random.default_rng(seed)
    dates = sorted(ev.date.unique()); di = {d: i for i, d in enumerate(dates)}
    e = ev[elig].copy(); e["di"] = e.date.map(di)
    by_day = {d: g for d, g in e.groupby("di")}
    open_until = {}          # symbol -> exit day index
    trades = []
    for i, d in enumerate(dates):
        open_until = {s: x for s, x in open_until.items() if x > i}
        free = SLOTS - len(open_until)
        if free <= 0 or i not in by_day:
            continue
        g = by_day[i]; g = g[~g.symbol.isin(open_until)]
        if len(g) == 0:
            continue
        if rank_col is None:
            g = g.iloc[rng.permutation(len(g))]
        else:
            g = g.sort_values(rank_col)          # most fallen first
        for _, row in g.head(free).iterrows():
            open_until[row.symbol] = i + HOLD
            trades.append((row.year, d, row.symbol, float(row.r10), float(row.r10) - COST))
    tr = pd.DataFrame(trades, columns=["year", "date", "symbol", "gross", "net"])
    return tr


def summarize(tr: pd.DataFrame, spy_year: dict):
    out = {}
    for y, g in tr.groupby("year"):
        pnl = (g.net * SLOT_USD)
        eq = pnl.cumsum(); dd = float((eq - eq.cummax()).min()) if len(eq) else 0.0
        out[y] = {"trades": int(len(g)), "win_rate": round(float((g.net > 0).mean()), 4), "gross_pnl": round(float((g.gross * SLOT_USD).sum()), 0),
                  "net_pnl": round(float(pnl.sum()), 0), "return_on_100k_pct": round(float(pnl.sum()) / 1000.0, 2), "max_drawdown_usd": round(dd, 0),
                  "spy_buy_hold_pct": spy_year.get(y)}
    return out


def main():
    ev = load()
    spy = ev.groupby("date").spy.first().sort_index()
    spy_year = {}
    for y in sorted(set(d[:4] for d in spy.index)):
        s = spy[[d for d in spy.index if d.startswith(y)]]
        spy_year[y] = round(float(s.iloc[-1] / s.iloc[0] - 1) * 100, 2)
    base = ev.tradeable.values & ev.in_pool.values
    F2 = base & ev.field_long.values & ev.pre.values & ~ev.late.values & ~ev.post.values
    F = base & ev.field_long.values
    res = {"declared": "book, eligibility, slot rule, arms, costs and per-year report in the docstring before results",
           "spy_buy_hold_pct": spy_year, "arms": {}}
    pd.set_option("display.width", 220)
    def show(name, tables):
        # average over seeds when several
        keys = sorted(set(k for t in tables for k in t))
        agg = {y: {c: round(float(np.mean([t[y][c] for t in tables if y in t and t[y][c] is not None])), 2) for c in ["trades", "win_rate", "gross_pnl", "net_pnl", "return_on_100k_pct", "max_drawdown_usd"]} for y in keys}
        for y in keys: agg[y]["spy_buy_hold_pct"] = spy_year.get(y)
        res["arms"][name] = agg
        t = pd.DataFrame(agg).T
        print(f"\n== {name} ({len(tables)} run{'s' if len(tables) > 1 else ''}):"); print(t.to_string())
        tot = sum(v["net_pnl"] for v in agg.values()); print(f"   total net P&L over the years: ${tot:,.0f} on $100k")
    show("B0 random tradeable names, every day (null book)", [summarize(run_book(ev, base, None, s), spy_year) for s in range(20)])
    show("B1 field-long days, random particle", [summarize(run_book(ev, F, None, s), spy_year) for s in range(20)])
    show("B3 F2 set, random slot fill", [summarize(run_book(ev, F2, None, s), spy_year) for s in range(20)])
    show("B2 F2 set, slot rule: most fallen first", [summarize(run_book(ev, F2, "own_10", None), spy_year)])
    json.dump(res, open(OUT, "w"), indent=1); print("filed:", OUT)


if __name__ == "__main__":
    main()
