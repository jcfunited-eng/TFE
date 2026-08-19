"""
ch_premarket_cut.py — desk floor #10: a position already beyond its cut
line before the open is cut at the first available price, never held
for a scheduled check. Runs 13:00-13:30 UTC via the CH6 loop; covers
BOTH books. Joseph 2026-08-19: "who in their right mind would shoot
themselves."
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

CUT_PCT = 20.0


def _keys():
    import subprocess
    raw = subprocess.run(
        ["aws", "secretsmanager", "get-secret-value", "--secret-id",
         "tfe/market-data/prod", "--query", "SecretString", "--output", "text"],
        capture_output=True, text=True).stdout
    return json.loads(raw)


def _mark(sym, sec):
    r = urllib.request.Request(
        f"https://data.alpaca.markets/v2/stocks/{sym}/trades/latest?feed=iex",
        headers={"APCA-API-KEY-ID": sec["APCA_API_KEY_ID"],
                 "APCA-API-SECRET-KEY": sec["APCA_API_SECRET_KEY"]})
    return float(json.load(urllib.request.urlopen(r, timeout=15))["trade"]["p"])


def main():
    sec = _keys()
    now = datetime.now(timezone.utc).isoformat()
    cut = 0
    from ch6_fast_harvest import close_position, positions
    b6p = ROOT / "artifacts" / "vtvr_observer" / "ch6_book.json"
    b6 = json.load(open(b6p))
    for sym, p in list(positions(b6).items()):
        try:
            px = _mark(sym, sec)
        except Exception:  # noqa: BLE001
            continue
        entry = float(p["entry_px"])
        if 100 * (px / entry - 1) >= CUT_PCT:      # short 20% underwater
            close_position(b6, sym, p, px, "ANOMALY-CUT premarket", now)
            cut += 1
    if cut:
        json.dump(b6, open(b6p, "w"), indent=1)

    lp = ROOT / "artifacts" / "vtvr_observer" / "ch3_shadow_log.json"
    log = json.load(open(lp))
    book = log["book"]
    changed = 0
    for f in log["finds"]:
        if f.get("status") != "OPEN":
            continue
        try:
            px = _mark(f["symbol"], sec)
        except Exception:  # noqa: BLE001
            continue
        entry = float(f["entry_px"])
        if 100 * (px / entry - 1) >= CUT_PCT:
            notional = float(f["notional"])
            sr = 100 * (1 - px / entry)
            pnl = round(notional * sr / 100, 2)
            book["cash"] = round(float(book["cash"]) + notional + pnl, 2)
            f.update(status="ANOMALY-CUT", resolved=now,
                     ret_pct=round(sr, 2), pnl=pnl, exit_px=px,
                     note="premarket cut, desk floor #10")
            changed += 1
            print(f"  CH3 premarket ANOMALY-CUT {f['symbol']} @{px} "
                  f"pnl ${pnl:+,.2f}")
    if changed:
        json.dump(log, open(lp, "w"), indent=1)
    print(f"[premarket-cut] ch6 cut {cut}, ch3 cut {changed}")


if __name__ == "__main__":
    main()
