"""
ch4_month_scan.py — the month scan at five readings per session
================================================================

Joseph 2026-08-20: "Do the 1 month scan with the 5 per day daily
reads — make sure your resolution for the kernel allows the values
to be visually expressive, make sure the tuples are arranged
correctly so the shorts on the 3D topology can be seen — then look
for the patterns — stocks are always in a state of decline or gain."

Per validated life: 78-minute bars (exactly 5 per session), ~4 months
fetched so the chain has its run-up (warmup 60 readings), the last 22
sessions kept for reading. Files one parquet per life with the chain
outputs at this resolution: artifacts/ch6_harvest/month_lanes/<SYM>.parquet

Usage: python tools/ch4_month_scan.py [workers]
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
UNIVERSE = os.path.join(ROOT, "artifacts", "ch4_uf",
                        "population_universe_20260819.csv")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch6_harvest", "month_lanes")
FIELDS = ("D_k", "B_k", "Rev_k", "U_star_k", "URF", "R_res", "S_UF",
          "F_n", "regime", "ignition", "extinction", "gate_count")


def _key() -> str:
    for ln in open(os.path.join(ROOT, ".env")):
        if ln.startswith("MASSIVE_API_KEY"):
            return ln.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("MASSIVE_API_KEY missing")


KEY = None


def fetch_78m(symbol: str, start: str, end: str) -> list:
    url = (f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/78/minute/"
           f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={KEY}")
    bars = []
    while url:
        d = json.load(urllib.request.urlopen(url, timeout=45))
        bars.extend(d.get("results", []))
        nxt = d.get("next_url")
        url = f"{nxt}&apiKey={KEY}" if nxt else None
        time.sleep(0.05)
    return bars


def one_life(symbol: str) -> str:
    try:
        from tools.ch4_uf_kernel_v2 import replay_symbol_v2
        today = datetime.now(timezone.utc)
        start = (today - timedelta(days=int(os.environ.get("SCAN_DAYS","130")))).strftime("%Y-%m-%d")
        bars = fetch_78m(symbol, start, today.strftime("%Y-%m-%d"))
        rows = []
        for b in bars:
            dt = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc)
            off = 4 if 3 < dt.month < 11 else 5
            et = dt - timedelta(hours=off)
            hm = et.hour * 60 + et.minute
            if 9 * 60 + 30 <= hm < 16 * 60 and et.weekday() < 5:
                rows.append((dt, float(b["c"]), float(b["v"]),
                             et.strftime("%Y-%m-%d"), et.strftime("%H:%M")))
        if len(rows) < 120:
            return f"{symbol}: thin ({len(rows)})"
        states = replay_symbol_v2(np.array([r[0] for r in rows]),
                                  np.array([r[1] for r in rows]),
                                  np.array([r[2] for r in rows]), warmup=60)
        recs = []
        for r, s in zip(rows, states):
            if s is None:
                continue
            rec = {"date": r[3], "time": r[4], "close": r[1], "volume": r[2]}
            for f in FIELDS:
                rec[f] = getattr(s, f)
            recs.append(rec)
        sessions = sorted({r["date"] for r in recs})[-int(os.environ.get("SCAN_KEEP","22")):]
        recs = [r for r in recs if r["date"] in sessions]
        if len(recs) < 60:
            return f"{symbol}: short window ({len(recs)})"
        tmp = os.path.join(OUT_DIR, f"{symbol}.parquet.tmp{os.getpid()}")
        pd.DataFrame(recs).to_parquet(tmp)
        os.replace(tmp, os.path.join(OUT_DIR, f"{symbol}.parquet"))
        return f"{symbol}: {len(recs)} readings"
    except Exception as err:  # noqa: BLE001
        return f"{symbol}: FAILED {type(err).__name__}: {err}"


def init():
    global KEY
    KEY = _key()


def main() -> None:
    global KEY
    KEY = _key()
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    os.makedirs(OUT_DIR, exist_ok=True)
    symbols = pd.read_csv(UNIVERSE)["Symbol"].astype(str).tolist()
    t0 = time.time()
    done = failed = 0
    with Pool(workers, initializer=init) as pool:
        for msg in pool.imap_unordered(one_life, symbols, chunksize=8):
            done += 1
            if "FAILED" in msg or "thin" in msg or "short window" in msg:
                failed += 1
            if done % 250 == 0:
                rate = done / (time.time() - t0)
                print(f"[{done}/{len(symbols)}] {rate:.1f}/s "
                      f"eta {(len(symbols) - done) / max(rate, .01) / 60:.0f}m "
                      f"skips {failed}", flush=True)
    print(f"DONE {done}, skips/failures {failed}, "
          f"{(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
