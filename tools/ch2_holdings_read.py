"""ch2_holdings_read.py — nightly long-view readings of CH2 holdings.

Joseph's exit law 2026-08-25: sells exist to keep profits. Winners
hold while the energy that carried them is alive (judged on the arc,
weeks not days); they sell when the fueling structure fails. Losers
hold while recovery is structurally alive; they sell when repair has
stopped (the measured floor: no healing 16+ sessions past the last
damage — beyond the 99th percentile of 53,890 healed wounds) or at
the 90-day wall. One reader per held stock, long protocol, strict
JSON, fail closed: an unreadable holding files UNREADABLE and keeps
its current protections.

Output: artifacts/ch6_harvest/ch2_readings/<SYM>.json plus a sealed
verdict sheet published to the channel-book S3 path for the
production engine to consume.
Usage: python tools/ch2_holdings_read.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
RDIR = os.path.join(ROOT, "artifacts", "ch6_harvest", "ch2_readings")
PROTOCOL = os.path.join(ROOT, "artifacts", "ch6_harvest",
                        "ch2_holdings_protocol.md")
READER_MODEL = os.environ.get("READER_MODEL", "sonnet")
VERDICTS = {"DRIVE_ALIVE", "DRIVE_DYING", "RECOVERY_ALIVE", "DEAD"}
S3_KEY = ("s3://tfe-codebuild-src-418384447921-us-east-1/"
          "runtime-refresh-checkpoints/channel-books/ch2-verdicts.json")


def _binary() -> str:
    p = os.environ.get("CLAUDE_CODE_EXECPATH")
    if p and os.path.exists(p):
        return p
    base = os.path.expanduser("~/.vscode-server/extensions")
    if os.path.isdir(base):
        for d in sorted(os.listdir(base), reverse=True):
            if d.startswith("anthropic.claude-code-"):
                p2 = os.path.join(base, d, "resources", "native-binary",
                                  "claude")
                if os.path.exists(p2):
                    return p2
    raise RuntimeError("no claude binary for the CH2 reading pass")


def _positions() -> list:
    sec = json.loads(subprocess.run(
        ["aws", "secretsmanager", "get-secret-value", "--secret-id",
         "tfe/market-data/prod", "--query", "SecretString",
         "--output", "text"], capture_output=True, text=True).stdout)
    req = urllib.request.Request(
        "https://paper-api.alpaca.markets/v2/positions",
        headers={"APCA-API-KEY-ID": sec["APCA_API_KEY_ID"],
                 "APCA-API-SECRET-KEY": sec["APCA_API_SECRET_KEY"]})
    return json.load(urllib.request.urlopen(req, timeout=30))


def _read_one(args) -> tuple:
    sym, above_entry, bin_path = args
    dossier = os.path.join(ROOT, "artifacts", "ch6_harvest", "dossiers",
                           f"{sym}.txt")
    out_path = os.path.join(RDIR, f"{sym}.json")
    stance = ("This position is ABOVE its entry (a winner): judge "
              "DRIVE_ALIVE vs DRIVE_DYING." if above_entry else
              "This position is BELOW its entry (a loser): judge "
              "RECOVERY_ALIVE vs DEAD.")
    prompt = (f"Follow {PROTOCOL} exactly, with SYM={sym}. {stance} "
              f"The dossier is at {dossier}. Write the strict JSON to "
              f"{out_path} BEFORE replying; reply exactly one line.")
    try:
        subprocess.run([bin_path, "-p", prompt, "--model", READER_MODEL,
                        "--allowedTools", "Read,Write"],
                       env=dict(os.environ, IS_SANDBOX="1"), cwd=ROOT,
                       capture_output=True, timeout=300)
        r = json.load(open(out_path))
        assert r["symbol"] == sym and r["verdict"] in VERDICTS
        assert isinstance(r["mechanism"], str) and len(r["mechanism"]) > 40
        float(r["confidence"])
        return sym, r["verdict"]
    except Exception as err:  # noqa: BLE001 — fail closed
        if os.path.exists(out_path):
            os.replace(out_path, out_path + ".invalid")
        return sym, f"UNREADABLE ({type(err).__name__})"


def main() -> None:
    os.makedirs(RDIR, exist_ok=True)
    from tools.ch6_dossier import build
    positions = [p for p in _positions() if p["side"] == "long"]
    if not positions:
        print("[ch2 read] no holdings")
        return
    jobs, skipped = [], []
    for p in positions:
        sym = p["symbol"]
        try:
            open(os.path.join(ROOT, "artifacts", "ch6_harvest",
                              "dossiers", f"{sym}.txt"), "w").write(
                build(sym))
            jobs.append((sym, float(p["unrealized_plpc"]) >= 0,
                         _binary()))
        except Exception as err:  # noqa: BLE001
            skipped.append(sym)
            print(f"  DOSSIER FAILED {sym}: {type(err).__name__} — "
                  "files UNREADABLE, current protections stay")
    results = {}
    with ThreadPoolExecutor(6) as ex:
        for sym, verdict in ex.map(_read_one, jobs):
            results[sym] = verdict
            print(f"  {sym}: {verdict}")
    for sym in skipped:
        results[sym] = "UNREADABLE (no dossier)"

    now = datetime.now(timezone.utc).isoformat()
    sheet = {"schema": "tfe.ch2-verdicts.v1", "read_at": now,
             "protocol": "ch2_holdings_protocol.md",
             "reader_model": READER_MODEL,
             "verdicts": results}
    body = json.dumps(sheet, indent=1, sort_keys=True)
    sheet_path = os.path.join(ROOT, "artifacts", "ch6_harvest",
                              "ch2_verdicts.json")
    tmp = sheet_path + f".tmp{os.getpid()}"
    open(tmp, "w").write(body)
    os.replace(tmp, sheet_path)
    digest = sha256(body.encode()).hexdigest()
    subprocess.run(["aws", "s3", "cp", sheet_path, S3_KEY],
                   capture_output=True, check=True)
    print(f"[ch2 read] {len(results)} verdicts published "
          f"sha256={digest[:16]}")


if __name__ == "__main__":
    main()
