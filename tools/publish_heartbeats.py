"""publish_heartbeats.py — gather every long-running program's pulse
and publish one sealed sheet beside the channel books.

The site reads this sheet and shows staleness in red; the production
engine emails when a pulse goes stale. The publisher's own generated_at
is its own pulse — if THIS stops, everything reads stale, which is the
correct failure face (2026-08-31: two loops died in a weekend restart
and trading stopped silently for two days).

Runs every cycle of channel_book_publication_loop.sh.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OBS = os.path.join(ROOT, "artifacts", "vtvr_observer")
S3_KEY = ("s3://tfe-codebuild-src-418384447921-us-east-1/"
          "runtime-refresh-checkpoints/channel-books/heartbeats.json")


def _iso_mtime(path: str) -> str | None:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path),
                                      tz=timezone.utc).isoformat()
    except OSError:
        return None


def _file_text(path: str) -> str | None:
    try:
        return open(path).read().strip() or None
    except OSError:
        return None


def main() -> None:
    pulses: dict[str, dict] = {}
    pulses["trading_loop"] = {
        "last": _file_text(os.path.join(OBS, ".hb_ch6_loop")),
        "expect_minutes": 15,
        "label": "CH6 trading pass"}
    pulses["nightly_runner"] = {
        "last": _file_text(os.path.join(OBS, ".hb_spring_runner")),
        "expect_minutes": 15,
        "label": "nightly runner"}
    door_last = None
    try:
        for line in open(os.path.join(OBS, "ch6_door.log")):
            m = re.match(r"\[ch6-door\] done (\S+)", line)
            if m:
                door_last = m.group(1)
    except OSError:
        pass
    pulses["nightly_picking"] = {
        "last": door_last,
        "expect_minutes": 26 * 60,
        "label": "nightly picking"}
    try:
        import pandas as pd
        store = os.path.join(ROOT, "ch4_live_store.parquet")
        latest = str(pd.read_parquet(store, columns=["Date"])
                     ["Date"].max())[:10]
        pulses["data_store"] = {
            "last": _iso_mtime(store), "latest_close": latest,
            "expect_minutes": 26 * 60, "label": "market data"}
    except Exception:  # noqa: BLE001
        pulses["data_store"] = {"last": None, "latest_close": None,
                                "expect_minutes": 26 * 60,
                                "label": "market data"}
    pulses["ch3_shadow"] = {
        "last": _iso_mtime(os.path.join(OBS, "ch3_shadow_log.json")),
        "expect_minutes": 26 * 60,
        "label": "CH3 shadow"}

    sheet = {"schema": "tfe.heartbeats.v1",
             "generated_at": datetime.now(timezone.utc).isoformat(),
             "pulses": pulses}
    out = os.path.join(OBS, "heartbeats.json")
    tmp = out + f".tmp{os.getpid()}"
    json.dump(sheet, open(tmp, "w"), indent=1)
    os.replace(tmp, out)
    subprocess.run(["aws", "s3", "cp", out, S3_KEY],
                   capture_output=True, check=False)


if __name__ == "__main__":
    main()
