"""
ch4_herd_kgate_live.py — CH4 live paper engine: herd_kgate_v1
=============================================================

ENGINE VERSION: herd_kgate_v1 (2026-08-01). Stamped on every trade.
Decision record: docs/CH4_LIVE_TIMING_AUDIT_20260731.md Addendum 5;
build plan: docs/CH4_HERD_KGATE_V1_BUILD_PLAN.md. Declared expectation
in advance: low-single-digit percent per year — live-forward divergence
from that range is itself information.

THE CONSTRUCTION (exactly as measured, nothing re-tuned):
  ENTRY  a symbol's daily gate reveal is the LATEST store close AND the
         herd-conditioned species record (bigram gate classes x herd
         energy x greed band at issue day; strict as-of-issue; n>=20)
         reads band >= 0.75. Fill at that close, long/short by
         majority. 10% slices, max 10 open, one per symbol.
         Friday rule: no new entries at a Friday close.
  EXIT   at the symbol's 3rd subsequent gate reveal, at that close.
  DATA   ch4_live_store.parquet (research store + same-source daily
         appends, seam-checked) + herd_state_live.parquet (exported
         nightly by the same machinery that measured the construction).

Nightly sequence (ch4_spring_daily_runner.sh):
  refresh store -> herd export -> this engine -> page.

Determinism: full-history replay each night; blake2b ids; no RNG.
Usage: python tools/ch4_herd_kgate_live.py            # apply to book
       python tools/ch4_herd_kgate_live.py DRY        # print decisions
       CH4_ASOF=2026-07-30 ... DRY                    # frozen-date test
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_spectrum import gate_stream, life_fraction  # noqa: E402

ENGINE_VERSION = "herd_kgate_v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_live.parquet")
BOOK_PATH = os.path.join(ROOT, "artifacts", "vtvr_observer",
                         "ch4_spring_book.json")
W = 20
BAND = 0.75
K_EXIT = 3
SLICE_PCT = 10.0
MAX_OPEN = 10
PRICE_FLOOR = 5.0
MIN_BARS = 1200
LIFE_MIN = 0.90
CASH0 = 100_000.0


def hid(*parts) -> int:
    h = hashlib.blake2b("|".join(str(p) for p in parts).encode(),
                        digest_size=8)
    return int.from_bytes(h.digest(), "big") >> 1


def build_event_stream(asof: str | None):
    """Full deterministic replay: every gate-reveal event with its HG
    species id, in strict global time order."""
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    if asof:
        df = df[df["Date"] <= pd.Timestamp(asof)]
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = set(stats[(stats["bars"] >= MIN_BARS)
                    & (stats["med"] >= PRICE_FLOOR)].index)
    herd = pd.read_parquet(HERD)
    hmap = {(s, int(d)): (int(c), int(e), int(gb)) for s, d, c, e, gb in zip(
        herd["sym"], herd["date"].astype(int), herd["cell"],
        herd["eband"], herd["gband"])}
    events = []          # (day_int, sym, sp_hg, close)
    last_day = None
    for sym, sub in df.groupby("Symbol", sort=True):
        if sym not in uni:
            continue
        sub = sub.sort_values("Date")
        dates = sub["Date"].dt.strftime("%Y%m%d").tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        vols = sub["Volume"].to_numpy(dtype=float)
        if life_fraction(closes)[-1] < LIFE_MIN:
            continue
        try:
            gs = gate_stream(dates, closes, vols)
        except Exception:
            continue
        for k in range(1, len(gs)):
            _, cls_prev, _, _, _ = gs[k - 1]
            _, cls_cur, _, _, tb_cur = gs[k]
            # reveal slip: the gate ending at tb-1 is knowable at bar tb
            if tb_cur >= len(closes) or closes[tb_cur] < PRICE_FLOOR:
                continue
            day = int(dates[tb_cur])
            st = hmap.get((sym, day))
            if st is None:
                continue
            c, e, gb = st
            sp_hg = hid(hid("bigram", ((cls_prev, cls_cur))), "HG", e, gb)
            events.append((day, sym, sp_hg, float(closes[tb_cur])))
        if dates:
            last_day = max(last_day or "0", dates[-1])
    events.sort(key=lambda x: (x[0], x[1]))
    return events, (int(last_day) if last_day else None)


def replay(events, last_day):
    """Chronological HG ledger + virtual position walk. Returns the
    virtual open-position table and today's decisions."""
    pos, neg = defaultdict(int), defaultdict(int)
    pending = defaultdict(list)      # sym -> [(entry_day, sp, entry_px, side, events_since)]
    vopen = {}                       # sym -> dict (virtual position)
    decisions = {"entries": [], "exits": []}
    for day, sym, sp, px in events:
        # settle completions: this event completes any K_EXIT-old entry
        # candidates' displacement for the ledger (the K=3 completion
        # object), knowable now
        lst = pending[sym]
        for rec in lst:
            rec[4] += 1
        while lst and lst[0][4] >= K_EXIT:
            e_day, e_sp, e_px, _side, _n = lst.pop(0)
            d = px / e_px - 1.0
            if d > 0:
                pos[e_sp] += 1
            elif d < 0:
                neg[e_sp] += 1
        # virtual position exit
        h = vopen.get(sym)
        if h is not None:
            h["events"] += 1
            if h["events"] >= K_EXIT:
                h["exit_day"], h["exit_px"] = day, px
                if day == last_day:
                    decisions["exits"].append(dict(h, sym=sym))
                vopen.pop(sym)
        # candidate entry (every event is a ledger candidate; the
        # BOOK entry additionally needs the band)
        p, q = pos[sp], neg[sp]
        n = p + q
        band_ok = n >= W and max(p, q) / n >= BAND
        side = 1 if p >= q else -1
        if band_ok and sym not in vopen:
            vopen[sym] = {"entry_day": day, "entry_px": px, "side": side,
                          "events": 0, "band": round(max(p, q) / n, 3),
                          "n": n}
            if day == last_day:
                decisions["entries"].append(
                    {"sym": sym, "side": side, "px": px,
                     "band": round(max(p, q) / n, 3), "n": n})
        pending[sym].append([day, sp, px, side, 0])
    return vopen, decisions


def main():
    dry = "DRY" in [a.upper() for a in sys.argv[1:]]
    asof = os.environ.get("CH4_ASOF")
    events, last_day = build_event_stream(asof)
    print(f"events: {len(events)} | latest store day: {last_day}")
    vopen, decisions = replay(events, last_day)
    print(f"latest-day decisions: {len(decisions['entries'])} entries, "
          f"{len(decisions['exits'])} exits | virtual open: {len(vopen)}")
    for d in decisions["entries"]:
        print(f"  ENTER {'LONG' if d['side'] == 1 else 'SHORT'} {d['sym']} "
              f"@{d['px']} band={d['band']} n={d['n']}")
    for d in decisions["exits"]:
        print(f"  EXIT {d['sym']} @{d['exit_px']} (entered {d['entry_day']})")
    if dry:
        print("DRY run - no book changes")
        return 0

    bar_date = f"{str(last_day)[:4]}-{str(last_day)[4:6]}-{str(last_day)[6:]}"
    book = json.load(open(BOOK_PATH)) if os.path.exists(BOOK_PATH) else {
        "engine": ENGINE_VERSION, "cash": CASH0, "positions": {},
        "closed": [], "last_processed": None}
    if book.get("last_processed") == bar_date:
        print("bar already processed; no-op")
        return 0
    # exits first: positions whose symbol had its K_EXIT-th reveal today
    exit_syms = {d["sym"]: d for d in decisions["exits"]}
    for sym in sorted(list(book["positions"].keys())):
        p = book["positions"][sym]
        d = exit_syms.get(sym)
        if d is None:
            continue
        px = d["exit_px"]
        ret = 100 * (px / p["entry_px"] - 1.0) * p["side"]
        pnl = p["notional"] * ret / 100.0
        book["cash"] += p["notional"] + pnl
        book["closed"].append({
            "sym": sym, "side": p["side"], "entry_date": p["entry_date"],
            "exit_date": bar_date, "entry_px": p["entry_px"], "exit_px": px,
            "ret_pct": round(ret, 2), "pnl": round(pnl, 2),
            "engine": p.get("engine", ENGINE_VERSION), "reason": "K3"})
        del book["positions"][sym]
    # entries — never on a Friday close
    if datetime.strptime(bar_date, "%Y-%m-%d").weekday() == 4:
        print("Friday close: entries skipped (weekend rule)")
    else:
        for d in sorted(decisions["entries"], key=lambda x: x["sym"]):
            if d["sym"] in book["positions"] \
                    or len(book["positions"]) >= MAX_OPEN:
                continue
            equity = book["cash"] + sum(p["notional"]
                                        for p in book["positions"].values())
            notional = min(equity * SLICE_PCT / 100.0, book["cash"])
            if notional <= 0:
                continue
            book["positions"][d["sym"]] = {
                "side": d["side"], "entry_px": d["px"],
                "entry_date": bar_date, "notional": round(notional, 2),
                "bound_pct": 0.0, "engine": ENGINE_VERSION}
            book["cash"] -= notional
    book["engine"] = ENGINE_VERSION
    book["last_processed"] = bar_date
    book["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    book["equity_mark"] = round(book["cash"] + sum(
        p["notional"] for p in book["positions"].values()), 2)
    os.makedirs(os.path.dirname(BOOK_PATH), exist_ok=True)
    with open(BOOK_PATH, "w") as f:
        json.dump(book, f, indent=1)
    print(f"book: open={len(book['positions'])} closed={len(book['closed'])} "
          f"cash=${book['cash']:,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
