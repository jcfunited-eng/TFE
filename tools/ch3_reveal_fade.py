"""
ch3_reveal_fade.py — CH3: the reveal-fade channel (owner's construction)
========================================================================

ENGINE: ch3_reveal_fade_v1 (2026-08-04). SHADOW — simulated fills only.

THE THESIS (mine, from my own measurements): the market pays out at
information reveals and then punishes the crowd that chases them.
Measured on 61,405 reveal events, 12k stocks, 2016-2026, honest fills:
continuation after a violent up-move LOSES; fading it earns +1.33%/5d
on average, positive EVERY year since 2021 (n 3,600-6,200/yr).
Buying crashes loses — so only the up-spike side is traded.

THE CONSTRUCTION (declared):
  EVENT   at today's close: day gain >= +8%, volume >= 3x trailing
          20-day average, close >= $5 (all knowable at that close).
  ENTRY   simulated SHORT at today's close, $2,000 per position,
          at most 10 new per day (largest dollar-volume first),
          one position per symbol at a time.
  EXIT    at the close of the 5th session after entry. Time exit only
          (matches the measured object). No stop: squeeze risk is real
          and is part of what live-forward must measure.
  STATED  no borrow costs or fees modeled; hot names are expensive to
          short in reality. The shadow book exists to measure whether
          the paper edge survives honest accounting later.

V2 (2026-08-13) — FORCE-PROPORTIONAL SIZING, created from the field:
the relaxation-field pass (ch3_relaxation_field.py, filed) measured
the pull monotone in z = |day log-move| / own trailing 20-day noise
(+1.1%/ev at 3-4 sigma rising to +7.5%/ev beyond 12), and the sizing
pass (ch3_force_sizing.py, filed) measured the dollar value of
following it: same events, same exits, same capital per day, split
by z instead of flat = 2.33% vs 1.79% per deployed dollar per entry
day on the decade, with the worst day smaller (-358 vs -610).
  SIZING  the day's capital stays SLICE_USD x (events taken); the
          split across them is proportional to z. No onset, no cap,
          no new constant. An allocation under one whole share stays
          cash. Names need 22 bars now (z needs 20 moves through
          yesterday); zero-noise names (sd=0) are skipped as data
          artifacts.
  ALSO MEASURED AND REFUSED tonight (filed, do not re-derive):
          crater-side longs even in calm herds (-0.82%/ev, 8/11 years
          negative — the field has an arrow); z>=3 as the event law
          (+1.75 vs +2.51 — dilutes); decay-break and above-entry
          refutation exits (pass 1/2 of ch3_fade_exit_law*.py).

V3 (2026-08-13, same night) — THE DOLLAR-TARGET CONSTRUCTION. Joe's
question: can this channel target ~$1,000/day. The honest arithmetic
from the filed objects: harvest exits (ch3_fade_exit_law2 R2: exit at
the first close giving the short >= +5%, else the 5-session clock)
earn 0.685%/deployed-dollar/session vs the clock's 0.501%. Velocity
loses per event and wins per book ONCE CAPITAL BINDS — v1's 10/day
cap and flat $2k slices were the underived constants that kept
capital from ever binding. v3 makes it bind:
  SUPPLY  every qualifying event is taken (no daily count cap; the
          field's supply is the limit, ~9.7/day decade average).
  ENVELOPE declared margin like any real short desk: gross exposure
          to GROSS_MULT (2.0) x capital; the cash ledger may borrow
          to -(GROSS_MULT-1) x CASH0. Borrow costs remain unmodeled
          and STATED, as since v1.
  SIZING  the day's remaining envelope is the budget, split by pull
          z (v2's force law), with no single event above
          MAX_EVENT_FRAC (10%) of capital — a ruin cap, declared as
          survival not alpha (the decade's worst force-day cohort
          lost 3.6x its own deployed dollars; at 2x gross that tail
          can end a book without this cap).
  EXIT    HARVEST at the first close <= 0.95 x entry (R2, measured
          +2.161%/ev at 3.16-session holds, wr 69); TIME backstop at
          the 5th session close, unchanged.
  EXPECTED (decade object, stated before live): ~$200k deployed x
          0.685%/session ~= $1,370/event-day, ~= $1,040/day averaged
          over the decade's droughts. Price tag stated with it:
          droughts pay ZERO for weeks (green tape = no supply, the
          filter working); 2020-style melt-up regimes LOSE at any
          size; the squeeze tail doubles with gross. The kill test
          (ch3_kill_test.py) now watches v3 closures against the R2
          object; below its declared 5th percentile the channel
          halts itself.
  CORRECTED same day (Joe called "bullshit" on the drought story —
          he was right about the dollars): the expectation above
          assumed the object's supply, but 75% of object supply and
          the rich edge (+2.66%/ev) live in UNCOVERED names the
          roster store never refreshes. The live pipe alone reaches
          ~2 events/day on 39% of days at +0.73%/ev — roughly
          $150/day, a seventh of the number above. FIX:
          ch3_supply_tail.py restores the whole market to the scan
          (CH3-only store; the shared CH4 store is untouched).
          Whether the uncovered edge holds on TODAY'S young names —
          not only the decade's dead ones — is a pre-registered
          live hypothesis; the tripwire halts the channel below p5.

Runs nightly after the store refresh (ch4_spring_daily_runner.sh).
State: artifacts/vtvr_observer/ch3_shadow_log.json (same book/page).
Usage: python tools/ch3_reveal_fade.py [DRY]
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
LOG_PATH = os.path.join(ROOT, "artifacts", "vtvr_observer",
                        "ch3_shadow_log.json")
ENGINE = "ch3_reveal_fade_v3"
ENGINE_FAMILY = "ch3_reveal_fade"   # older opens settle under v3 too
EVENT_GAIN = 8.0
VOL_MULT = 3.0
PRICE_FLOOR = 5.0
HOLD_SESSIONS = 5
CASH0 = 100_000.0
GROSS_MULT = 2.0          # declared margin envelope: gross <= 2x capital
HARVEST_X = 0.95          # R2: exit at first close <= 0.95 x entry
MAX_EVENT_FRAC = 0.10     # ruin cap per event (survival, not alpha)
ANOMALY_STOP_PCT = 20.0   # Joe's rule 2026-08-17: cut shorts 20%+ underwater
UNCOVERED_CAP = 2500.0    # 2026-08-17, after WETO: uncovered names (no herd
                          # row — the blind-spot class where gaps jump any
                          # stop) never carry more than this per slice.
                          # Survival sizing: worst gap-through is bounded by
                          # slice x gap, so the slice is the true protection.


def load_log():
    if os.path.exists(LOG_PATH):
        log = json.load(open(LOG_PATH))
    else:
        log = {"finds": [], "days": {}}
    log.setdefault("book", {"cash": CASH0, "start": CASH0})
    log["engine"] = ENGINE
    return log


def main():
    dry = "DRY" in [a.upper() for a in sys.argv[1:]]
    now = datetime.now(timezone.utc).isoformat()
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    days = np.array(sorted(df["Date"].unique()))
    latest = days[-1]
    latest_s = pd.Timestamp(latest).strftime("%Y-%m-%d")
    day_index = {pd.Timestamp(d).strftime("%Y-%m-%d"): i
                 for i, d in enumerate(days)}
    # v3 supply tail (ch3_supply_tail.py): the whole market's rows for
    # names the roster store is NOT currently refreshing — the decade
    # object's "none" stratum, restored. Single-source per name: any
    # symbol with a bar at the roster store's latest day stays roster-
    # only; everything else scans from the tail (no cross-source seams).
    tail_path = os.path.join(ROOT, "ch3_supply_tail.parquet")
    if os.path.exists(tail_path):
        tail = pd.read_parquet(tail_path)
        tail["Date"] = pd.to_datetime(tail["Date"])
        refreshed = set(df[df["Date"] == latest]["Symbol"])
        tail = tail[~tail["Symbol"].isin(refreshed)
                    & (tail["Date"] <= latest)]
        df = pd.concat([df[df["Symbol"].isin(refreshed)], tail],
                       ignore_index=True)
    log = load_log()

    # settle: HARVEST at the first close <= 0.95 x entry (checked every
    # nightly pass = every close), TIME backstop at the 5th session close
    px_latest = dict(df[df["Date"] == latest][["Symbol", "Close"]].values)
    settled = 0
    for f in log["finds"]:
        if (f["status"] != "OPEN"
                or not str(f.get("engine", "")).startswith(ENGINE_FAMILY)):
            continue
        ei = day_index.get(f["date"])
        li = day_index.get(latest_s)
        if ei is None or li is None or li - ei < 1:
            continue
        px = px_latest.get(f["symbol"])
        if px is None:
            continue
        harvest = float(px) <= HARVEST_X * f["entry_px"]
        # ANOMALY STOP (Joe's rule 2026-08-17, after WETO): a short 20%+
        # underwater at a close is cut there — visible blow-ups get
        # cancelled, not ridden to the backstop. Survival constant.
        anomaly = float(px) >= (1 + ANOMALY_STOP_PCT / 100) * f["entry_px"]
        if not harvest and not anomaly and li - ei < HOLD_SESSIONS:
            continue
        ret = 100 * (1 - float(px) / f["entry_px"])          # short
        pnl = round(f["notional"] * ret / 100, 2)
        log["book"]["cash"] = round(log["book"]["cash"] + f["notional"] + pnl, 2)
        f.update(status=("HARVEST" if harvest else
                         ("ANOMALY-CUT" if anomaly else "TIME")), resolved=now,
                 ret_pct=round(ret, 2), pnl=pnl, exit_px=float(px))
        settled += 1

    # herd greed at the latest day (exported by the same nightly pass,
    # knowable at this close): fade ONLY spikes the herd is not backing
    herd = pd.read_parquet(os.path.join(
        ROOT, "artifacts", "ch4_uf", "herd_state_live.parquet"))
    hday = int(pd.Timestamp(latest).strftime("%Y%m%d"))
    gband = {s: int(g) for s, d, g in zip(
        herd["sym"], herd["date"].astype(int), herd["gband"]) if int(d) == hday}
    if not gband:
        # herd state for this close not published (export late/failed).
        # Without it every spike reads "crowd-less" and the engine would
        # enter UNFILTERED — fail-open. Same guard CH6 has: settles above
        # already ran; entries wait for the next pass.
        print(f"[reveal-fade] {latest_s}: herd state missing — settles "
              f"done ({settled}), entries refused (fail-closed)")
        if not dry:
            json.dump(log, open(LOG_PATH, "w"), indent=1)
        return

    # today's reveal events
    sub = df[df["Date"].isin(days[-25:])]
    events = []
    for sym, s in sub.groupby("Symbol"):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy()
        v = s["Volume"].to_numpy()
        if len(c) < 22 or s["Date"].iloc[-1] != latest:
            continue                    # v2: z needs 20 moves through yesterday
        if c[-1] < PRICE_FLOOR or c[-2] <= 0:
            continue
        gain = 100 * (c[-1] / c[-2] - 1)
        vavg = float(np.mean(v[-21:-1]))
        if gain >= EVENT_GAIN and vavg > 0 and v[-1] >= VOL_MULT * vavg:
            g = gband.get(sym)          # None = no herd; 0 = low greed
            if g is not None and g >= 1:
                continue                # herd is backing it: a birth, not a collapse
            with np.errstate(divide="ignore", invalid="ignore"):
                lr = np.diff(np.log(np.maximum(c.astype(float), 1e-12)))
            sd = float(np.std(lr[-21:-1]))          # own 20-day noise
            if sd <= 1e-9 or not np.isfinite(lr[-1]):
                continue                # zero-noise name: data artifact
            z = float(abs(lr[-1]) / sd)             # displacement in own units
            run20 = 100 * (c[-2] / c[-22] - 1) if c[-22] > 0 else 0.0
            events.append({"symbol": sym, "gain": round(gain, 1),
                           "close": float(c[-1]), "z": round(z, 2),
                           "herd": "none" if g is None else "low",
                           "prerun": round(run20, 1),
                           "dollar_vol": float(v[-1] * c[-1])})
    events.sort(key=lambda e: -e["dollar_vol"])
    held = {f["symbol"] for f in log["finds"] if f["status"] == "OPEN"}
    # v3: every qualifying event is taken (supply is the only count
    # limit); the day's budget is the remaining margin envelope (gross
    # to GROSS_MULT x capital, so cash may borrow to the floor), split
    # by pull z, no single event above MAX_EVENT_FRAC of capital
    take = []
    for e in events:
        if e["symbol"] in held or any(t["symbol"] == e["symbol"] for t in take):
            continue
        take.append(e)
    floor_cash = -(GROSS_MULT - 1.0) * CASH0
    budget = max(0.0, log["book"]["cash"] - floor_cash)
    zsum = sum(t["z"] for t in take) or 1.0
    opened = 0
    for e in take:
        alloc = min(budget * e["z"] / zsum, MAX_EVENT_FRAC * CASH0)
        if e["herd"] == "none":
            alloc = min(alloc, UNCOVERED_CAP)
        # whole shares only — a real short cannot be fractional; an
        # allocation under one share stays cash (pull too weak)
        shares = int(alloc // e["close"])
        if shares < 1:
            continue
        notional = round(shares * round(e["close"], 4), 2)
        if log["book"]["cash"] - notional < floor_cash and not dry:
            continue
        if dry:
            print(f"  WOULD SHORT {shares} {e['symbol']} @ {e['close']} "
                  f"(+{e['gain']}% day, z {e['z']}, alloc ${alloc:,.0f}, "
                  f"${e['dollar_vol']/1e6:.0f}M traded)")
            opened += 1
            continue
        log["book"]["cash"] = round(log["book"]["cash"] - notional, 2)
        log["finds"].append({
            "engine": ENGINE, "date": latest_s, "found_at": now,
            "symbol": e["symbol"], "side": -1,
            "entry_px": round(e["close"], 4), "shares": shares,
            "target_pct": None, "target_px": None, "bound_pct": None,
            "notional": notional, "day_chg_pct": e["gain"], "z": e["z"],
            "catalyst": f"REVEAL/herd-{e['herd']}", "status": "OPEN"})
        held.add(e["symbol"])
        opened += 1

    if not dry:
        day = [f for f in log["finds"] if f.get("resolved", "")[:10] == now[:10]
               and f["status"] in ("TIME", "HARVEST")]
        wins = sum(1 for f in day if f["pnl"] > 0)
        log["days"][latest_s] = {
            "finds": opened, "hits": wins,
            "hit_rate_pct": round(100 * wins / len(day), 1) if day else None,
            "mean_ret_pct": round(float(np.mean([f["ret_pct"] for f in day])), 2)
            if day else None,
            "pnl_usd": round(sum(f["pnl"] for f in day), 2),
            "book_value": log["book"]["cash"] + sum(
                f["notional"] for f in log["finds"] if f["status"] == "OPEN")}
        json.dump(log, open(LOG_PATH, "w"), indent=1)
    print(f"[reveal-fade] {latest_s}: events {len(events)}, opened {opened}, "
          f"settled {settled}, cash ${log['book']['cash']:,.2f}"
          + (" (DRY)" if dry else ""))


if __name__ == "__main__":
    main()
