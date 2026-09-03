"""ch3_recovery_engine.py — the healed-recovery law, live on paper.

The law EXACTLY as tested (ch2_healed_entry_trial.json, PASS both
halves): a damage cluster healing on the living schedule — within 16
sessions of the last damage, an ignition OR five quiet sessions with
URF back above its own 22-session median — with S_UF at/above its own
22-session median and B_k not draining over five sessions, is bought
at the close after confirmation and sold at the 20th session close.
No stops, no trailing, no management. Frozen per
docs/CH3_RECOVERY_TRIAL_20260902.md until 2026-10-02.

Runs nightly after the store/population refresh:
  python tools/ch3_recovery_engine.py
Entries fill at the NEXT session's close (as tested); exits at the
20th session close after entry. The blindfold control (unconditional
20-session long of the same universe) accrues alongside. The grade
publishes with the channel books.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LANES = os.path.join(ROOT, "artifacts", "ch4_uf", "population_lanes")
BOOK = os.path.join(ROOT, "artifacts", "vtvr_observer",
                    "ch3_recovery_book.json")
TT = json.load(open(os.path.join(ROOT, "artifacts", "ch6_harvest",
                                 "ticker_types.json")))
OP = {s for s, t in TT.items() if t in ("CS", "ADRC")}
SLICE = 2_500.0
CASH0 = 100_000.0
HOLD = 20


def _load() -> dict:
    if os.path.exists(BOOK):
        return json.load(open(BOOK))
    return {"engine": "ch3_recovery_v1", "cash": CASH0, "start": CASH0,
            "positions": {}, "closed": [], "pending": [],
            "control": {"n": 0, "sum_ret": 0.0},
            "trial": "docs/CH3_RECOVERY_TRIAL_20260902.md"}


def _save(book: dict) -> None:
    book["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    tmp = BOOK + f".tmp{os.getpid()}"
    json.dump(book, open(tmp, "w"), indent=1)
    os.replace(tmp, BOOK)


def confirmations_and_control(latest: str) -> tuple[list, list]:
    """Scan every operating life: heal-confirmations AT the latest
    close (the law's entry signal), plus the control sample (every
    10th ordinary session close, as in the trial)."""
    confirms, control = [], []
    for f in os.listdir(LANES):
        if not f.endswith(".parquet"):
            continue
        sym = f[:-8]
        if sym not in OP:
            continue
        try:
            lf = pd.read_parquet(os.path.join(LANES, f),
                                 columns=["date", "close", "URF", "S_UF",
                                          "B_k", "extinction", "ignition"])
        except Exception:  # noqa: BLE001
            continue
        n = len(lf)
        if n < 40 or str(lf["date"].iloc[-1])[:10] != latest:
            continue
        c = lf["close"].to_numpy(float)
        # the CLEAN frame the law passed under (ch3_recovery_clean_retest
        # 2026-09-03): $5 floor, no destroyed shells, no 25%-day pump
        # names in the last 10 sessions. Fillability/ceiling applied
        # below from the store.
        if c[-1] < 5:
            continue
        if float(np.max(c)) / c[-1] >= 1000:
            continue
        w = c[-11:]
        if any(a > 0 and b / a >= 1.25 for a, b in zip(w, w[1:])):
            continue
        urf = lf["URF"].to_numpy(float)
        suf = lf["S_UF"].to_numpy(float)
        bk = lf["B_k"].to_numpy(float)
        ext = lf["extinction"].to_numpy(float)
        ign = lf["ignition"].to_numpy(float)
        h = n - 1
        # control: every ordinary close participates via subsample
        if ext[h] == 0 and h % 10 == 0:
            control.append(sym)
        # find the most recent damage; is TODAY its confirmation?
        if ext[h] > 0:
            continue
        last_dmg = None
        for j in range(h - 1, max(h - 17, 0), -1):
            if ext[j] > 0:
                last_dmg = j
                break
        if last_dmg is None:
            continue
        urf_med = float(np.median(urf[h - 22:h]))
        quiet5 = (h - last_dmg >= 5
                  and ext[last_dmg + 1:h + 1].sum() == 0)
        confirmed_today = (ign[h] > 0
                           or (quiet5 and urf[h] > urf_med))
        # confirmation must be TODAY, not earlier in the window
        if not confirmed_today:
            continue
        already = False
        for j in range(last_dmg + 1, h):
            q5 = (j - last_dmg >= 5
                  and ext[last_dmg + 1:j + 1].sum() == 0)
            um = float(np.median(urf[j - 22:j])) if j >= 22 else np.nan
            if ign[j] > 0 or (q5 and np.isfinite(um) and urf[j] > um):
                already = True
                break
        if already:
            continue
        suf_med = float(np.median(suf[h - 22:h]))
        if suf[h] >= suf_med and bk[h] >= bk[max(0, h - 5)]:
            confirms.append(sym)
    return confirms, control


def main() -> None:
    store = pd.read_parquet(os.path.join(ROOT, "ch4_live_store.parquet"),
                            columns=["Date", "Symbol", "Close", "Volume"])
    store["d"] = store["Date"].astype(str).str[:10]
    days = sorted(store["d"].unique())
    latest = days[-1]
    px = store[store["d"] == latest].set_index("Symbol")["Close"].to_dict()
    med20 = {}
    for sym, g in store.groupby("Symbol"):
        g = g.sort_values("d").tail(21).head(20)
        med20[sym] = float((g["Close"] * g["Volume"]).median())

    book = _load()
    if book.get("last_processed") == latest:
        print(f"[ch3 recovery] {latest} already processed")
        return
    now = datetime.now(timezone.utc).isoformat()

    # 1. fill yesterday's pending confirmations at TODAY's close
    filled = 0
    for sym in book.get("pending", []):
        p = px.get(sym)
        if not p or sym in book["positions"] or book["cash"] < SLICE:
            continue
        nd = med20.get(sym, 0.0)
        if not (200_000 <= nd < 100_000_000):
            continue  # fillability floor and poison ceiling (clean frame)
        shares = int(SLICE // p)
        if shares < 1:
            continue
        book["positions"][sym] = {"entry_px": round(float(p), 4),
                                  "entry_date": latest, "shares": shares,
                                  "sessions_held": 0}
        book["cash"] -= shares * p
        filled += 1

    # 2. age and exit at the 20th session close
    exits = 0
    for sym in list(book["positions"]):
        pos = book["positions"][sym]
        pos["sessions_held"] = int(pos["sessions_held"]) + 1
        if pos["sessions_held"] >= HOLD:
            p = px.get(sym)
            if p:
                pnl = pos["shares"] * (float(p) - pos["entry_px"])
                book["cash"] += pos["shares"] * float(p)
                book["closed"].append({
                    "symbol": sym, "entry_px": pos["entry_px"],
                    "exit_px": round(float(p), 4),
                    "entry_date": pos["entry_date"], "exit_date": latest,
                    "pnl": round(pnl, 2),
                    "ret_pct": round(100 * (float(p) / pos["entry_px"] - 1), 2)})
                del book["positions"][sym]
                exits += 1

    # 3. tonight's confirmations become tomorrow's fills; the control
    #    accrues its 20-session forward return when computable
    confirms, control = confirmations_and_control(latest)
    book["pending"] = confirms
    if len(days) > 21:
        d0, d20 = days[-22], days[-2]
        p0 = store[store["d"] == d0].set_index("Symbol")["Close"]
        p20 = store[store["d"] == d20].set_index("Symbol")["Close"]
        joined = pd.concat([p0, p20], axis=1, keys=["a", "b"]).dropna()
        joined = joined[joined["a"] > 1]
        sample = joined.iloc[::10]
        if len(sample):
            book["control"]["n"] += int(len(sample))
            book["control"]["sum_ret"] += float(
                (100 * (sample["b"] / sample["a"] - 1)).sum())

    book["last_processed"] = latest
    _save(book)
    eq = book["cash"] + sum(p["shares"] * px.get(s, p["entry_px"])
                            for s, p in book["positions"].items())
    ctrl_avg = (book["control"]["sum_ret"] / book["control"]["n"]
                if book["control"]["n"] else 0.0)
    mine = [t["ret_pct"] for t in book["closed"]]
    print(f"[ch3 recovery] {latest}: filled {filled}, exited {exits}, "
          f"pending {len(confirms)}, open {len(book['positions'])}, "
          f"equity ${eq:,.2f} | closed avg "
          f"{np.mean(mine):+.2f}% (n={len(mine)}) vs control "
          f"{ctrl_avg:+.2f}% (n={book['control']['n']})"
          if mine else
          f"[ch3 recovery] {latest}: filled {filled}, exited {exits}, "
          f"pending {len(confirms)}, open {len(book['positions'])}, "
          f"equity ${eq:,.2f} | control {ctrl_avg:+.2f}% "
          f"(n={book['control']['n']})")


if __name__ == "__main__":
    main()
