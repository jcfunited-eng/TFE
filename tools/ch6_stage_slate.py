"""ch6_stage_slate.py — nightly staging under the complete rulebook
(docs/CH6_RULEBOOK_20260821.md).

Takes tonight's filed readings (plus yesterday's under the one-day
carry), keeps RELAX claims only, applies Joseph's rising-stock rule
(no pick that closed up on its decision day — the purchase-side half
lives in the fill path), re-runs every law fresh (read_symbol), and
stages by reading confidence until cash is spoken for. No readings
=> nothing stages, and the custody note says so.

Usage: python tools/ch6_stage_slate.py [--dry]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from multiprocessing import Pool

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DOOR = os.path.join(ROOT, "artifacts", "ch6_harvest", "door")


def _verdict(sym):
    from tools.ch_entry_reading import read_symbol
    return sym, read_symbol(sym)


def main() -> None:
    dry = "--dry" in sys.argv
    from tools.ch_entry_reading import LAWS_VERSION
    from tools.ch6_fast_harvest import (
        load_book, save_book, positions, STORE,
        SLICE_TARGET_USD, SLICE_FLOOR_USD)

    store = pd.read_parquet(STORE)
    latest = str(store["Date"].max())[:10]
    days = sorted(str(d)[:10] for d in store["Date"].unique())
    prev = days[-2] if len(days) > 1 else latest
    dmax = store["Date"].max()
    c_now = {str(r["Symbol"]): float(r["Close"])
             for _, r in store[store["Date"] == dmax].iterrows()}
    prev_rows = store[store["Date"].astype(str).str[:10] == prev]
    c_prev = {str(r["Symbol"]): float(r["Close"])
              for _, r in prev_rows.iterrows()}

    readings = {}
    for day, carry in ((prev, True), (latest, False)):
        rdir = os.path.join(DOOR, "readings", day)
        if not os.path.isdir(rdir):
            continue
        for f in sorted(os.listdir(rdir)):
            if not f.endswith(".json"):
                continue
            try:
                r = json.load(open(os.path.join(rdir, f)))
                sym = r["symbol"]
                if carry:
                    cn, cp = c_now.get(sym, 0.0), c_prev.get(sym, 0.0)
                    if not (cp > 0 and cn <= cp * 1.02):
                        continue  # carried reading died (staleness rule)
                readings[sym] = r  # tonight's overwrites a carry
            except Exception:  # noqa: BLE001 — fail closed
                continue

    book = load_book()
    if book.get("staged_entries") and not dry:
        print("[ch6 stage] staged entries already present — restating")
    held = set(positions(book))
    cands = []
    for sym, r in readings.items():
        if r["prediction"] != "RELAX" or sym in held or sym not in c_now:
            continue
        cn, cp = c_now[sym], c_prev.get(sym, 0.0)
        if cp > 0 and cn > cp:
            continue  # Joseph 2026-08-21: closed up on decision day
        cands.append((sym, float(r["confidence"]), r["family"]))
    cands.sort(key=lambda x: -x[1])
    cash = float(book["cash"])
    target = int(cash // SLICE_TARGET_USD)
    print(f"[ch6 stage] {latest}: readings {len(readings)}, candidates "
          f"{len(cands)}, cash ${cash:,.0f} -> up to {target} stages")

    now = datetime.now(timezone.utc).isoformat()
    staged, refused = [], {}
    batch = [s for s, _, _ in cands[:target * 3]]
    if batch:
        with Pool(8) as p:
            verdicts = dict(p.imap_unordered(_verdict, batch, chunksize=1))
    else:
        verdicts = {}
    for sym, conf, fam in cands:
        if len(staged) >= target:
            break
        v = verdicts.get(sym)
        if v is None:
            continue
        if v["verdict"] != "ALLOW":
            refused[v.get("law")] = refused.get(v.get("law"), 0) + 1
            print(f"  REFUSED {sym}: {v.get('law')}")
            continue
        nd = float(v["facts"]["normal_day_dollars"])
        if 0.01 * nd < SLICE_FLOOR_USD:
            refused["fillability-floor"] = \
                refused.get("fillability-floor", 0) + 1
            continue
        staged.append({"symbol": sym, "decided_date": latest,
                       "decided_close": round(c_now[sym], 4),
                       "decided_at": now, "normal_day_dollars": nd})
        print(f"  STAGED {sym} @ {c_now[sym]:.2f} ({fam} conf {conf})")

    if dry:
        print(f"[ch6 stage] DRY: would stage {len(staged)}")
        return
    book["staged_entries"] = staged
    cust = dict(book.get("last_hunt_custody") or {})
    cust["readings_door"] = {
        "decided_close": latest, "readings": len(readings),
        "candidates": len(cands), "staged": len(staged),
        "law_refused": refused, "laws_version": LAWS_VERSION,
        "rulebook": "docs/CH6_RULEBOOK_20260821.md"}
    book["last_hunt_custody"] = cust
    save_book(book)
    print(f"[ch6 stage] staged {len(staged)}; book saved")


if __name__ == "__main__":
    main()
