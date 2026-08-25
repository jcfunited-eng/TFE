"""ch6_read_pool.py — the nightly reading pass, headless.

For every admitted pool name without a fresh reading, builds the
dossier (month lanes at 5 readings/session) and asks one headless
reader (the bundled Claude Code binary, sonnet) to name the
mechanism and claim RELAX or HOLD_OFF, per the filed protocol.
Fresh = filed on this close, or on the prior close and not run
2%+ against (the rulebook's one-day carry).

Spend controls (Joseph 2026-08-25): READ_CAP names per night
(default 120), most recent damage first; the dropped count is
printed, never silent. Every reading validates as strict JSON with
all five fields or is discarded (fail closed).

Output: artifacts/ch6_harvest/door/readings/<date>/<SYM>.json
Usage: python tools/ch6_read_pool.py <pool.json>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DOOR = os.path.join(ROOT, "artifacts", "ch6_harvest", "door")
PROTOCOL = os.path.join(ROOT, "artifacts", "ch6_harvest",
                        "reading_protocol.md")
READ_CAP = int(os.environ.get("READ_CAP", "120"))
READER_MODEL = os.environ.get("READER_MODEL", "sonnet")
FAMILIES = {"LIVE_COLLAPSE", "POST_EVENT_BASE", "BOUNCE_FORMING",
            "CONDUCTION", "PUMP_VEHICLE", "SPENT_PULSE"}


def _binary() -> str:
    p = os.environ.get("CLAUDE_CODE_EXECPATH")
    if p and os.path.exists(p):
        return p
    base = os.path.expanduser("~/.vscode-server/extensions")
    if os.path.isdir(base):
        cands = sorted(d for d in os.listdir(base)
                       if d.startswith("anthropic.claude-code-"))
        for d in reversed(cands):
            p2 = os.path.join(base, d, "resources", "native-binary",
                              "claude")
            if os.path.exists(p2):
                return p2
    raise RuntimeError("no claude binary found for the reading pass")


def _fresh(sym: str, latest: str, prev: str, c_now: float,
           c_prev: float, rdir: str, prev_dir: str) -> bool:
    if os.path.exists(os.path.join(rdir, f"{sym}.json")):
        return True
    prior = os.path.join(prev_dir, f"{sym}.json")
    if os.path.exists(prior) and c_prev > 0 and c_now <= c_prev * 1.02:
        return True    # one-day carry under the staleness rule
    return False


def _read_one(args) -> tuple:
    sym, out_dir, bin_path = args
    dossier = os.path.join(ROOT, "artifacts", "ch6_harvest", "dossiers",
                           f"{sym}.txt")
    out_path = os.path.join(out_dir, f"{sym}.json")
    prompt = (
        f"Follow {PROTOCOL} exactly, with SYM={sym}. The dossier is at "
        f"{dossier}. Write the five-field strict JSON to {out_path} "
        "with the Write tool BEFORE replying; your entire reply is one "
        f"line: `{sym} FILED` or `{sym} ERROR: <reason>`.")
    env = dict(os.environ, IS_SANDBOX="1")
    try:
        subprocess.run(
            [bin_path, "-p", prompt, "--model", READER_MODEL,
             "--allowedTools", "Read,Write"],
            env=env, cwd=ROOT, capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        return sym, "timeout"
    try:
        r = json.load(open(out_path))
        assert r["symbol"] == sym
        assert r["family"] in FAMILIES
        assert r["prediction"] in ("RELAX", "HOLD_OFF")
        assert isinstance(r["mechanism"], str) and len(r["mechanism"]) > 40
        float(r["confidence"])
        return sym, "ok"
    except Exception as err:  # noqa: BLE001 — fail closed: discard
        if os.path.exists(out_path):
            os.replace(out_path, out_path + ".invalid")
        return sym, f"invalid ({type(err).__name__})"


def main() -> None:
    pool = json.load(open(sys.argv[1]))
    latest = pool["decided_close"]
    store = pd.read_parquet(os.path.join(ROOT, "ch4_live_store.parquet"))
    days = sorted(str(d)[:10] for d in store["Date"].unique())
    prev = days[-2] if len(days) > 1 else latest
    dmax = store["Date"].max()
    c_now = {str(r["Symbol"]): float(r["Close"])
             for _, r in store[store["Date"] == dmax].iterrows()}
    prev_day = store[store["Date"].astype(str).str[:10] == prev]
    c_prev = {str(r["Symbol"]): float(r["Close"])
              for _, r in prev_day.iterrows()}

    rdir = os.path.join(DOOR, "readings", latest)
    prev_dir = os.path.join(DOOR, "readings", prev)
    os.makedirs(rdir, exist_ok=True)

    lanes = os.path.join(ROOT, "artifacts", "ch4_uf", "population_lanes")
    need = []
    for sym in pool["admitted"]:
        if _fresh(sym, latest, prev, c_now.get(sym, 0.0),
                  c_prev.get(sym, 0.0), rdir, prev_dir):
            continue
        path = os.path.join(lanes, f"{sym}.parquet")
        recency = 99
        if os.path.exists(path):
            ex = pd.read_parquet(path, columns=["extinction"]).tail(10)
            arr = ex["extinction"].to_numpy()
            hits = [i for i, v in enumerate(reversed(arr)) if v > 0]
            recency = hits[0] if hits else 99
        need.append((recency, sym))
    need.sort()
    dropped = max(0, len(need) - READ_CAP)
    todo = [s for _, s in need[:READ_CAP]]
    print(f"[ch6 read] {latest}: pool {len(pool['admitted'])}, fresh "
          f"{len(pool['admitted']) - len(need)}, to read {len(todo)}"
          + (f", DROPPED {dropped} past READ_CAP={READ_CAP} "
             "(read tomorrow, damage-recency order)" if dropped else ""))
    if not todo:
        return

    from tools.ch6_dossier import build
    built = 0
    for sym in list(todo):
        try:
            open(os.path.join(ROOT, "artifacts", "ch6_harvest", "dossiers",
                              f"{sym}.txt"), "w").write(build(sym))
            built += 1
        except Exception as err:  # noqa: BLE001
            print(f"  DOSSIER FAILED {sym}: {type(err).__name__} — skipped")
            todo.remove(sym)
    print(f"[ch6 read] dossiers built {built}")

    bin_path = _binary()
    ok = bad = 0
    with ThreadPoolExecutor(6) as ex:
        for sym, status in ex.map(_read_one,
                                  [(s, rdir, bin_path) for s in todo]):
            if status == "ok":
                ok += 1
            else:
                bad += 1
                print(f"  READER {sym}: {status}")
    print(f"[ch6 read] filed {ok}, failed {bad} "
          f"(model {READER_MODEL}, failures discarded, fail closed)")


if __name__ == "__main__":
    main()
