"""caretaker.py — Guala's tireless lesson-presenter. Charter: shared
ledger 2026-09-12 (C1 caretaker charter v1, Sol's boundary binding).

WHAT IT IS: environment, never mind. It PRESENTS lawful experiences
(alphabet/number cards with their spoken tutor sound) through the five
public lean routes, paced by HER measured state. It decides nothing
about cognition, meaning, rewards, actions, lesson success, or
recovery; it grades nothing; no lesson timers — every wait reads the
organism's own published state. Wall-clock appears only as polling
politeness (like the page's own cadence), never as a recovery rule.

INTERFACES (read+present only): GET /api/v1/guala/observation,
POST /api/v1/guala/occurrence (kind=sensory, card-microphone).
STOP: touch guala_caretaker/STOP (halts between requests) or kill the
process — nothing persists in her. Single instance via flock. Log is
bounded. An accepted occurrence is NEVER retried; a refused one is
never re-sent — the lesson re-presents from its start at the next
clear window.
"""
from __future__ import annotations

import base64
import fcntl
import json
import os
import sys
import time
import urllib.request
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://dsf-ai.com/api/v1/guala"
CUR = os.path.join(HERE, "curriculum")
STOP = os.path.join(HERE, "STOP")
LOG = os.path.join(HERE, "caretaker.log")
STATE = os.path.join(HERE, "state.json")
POLL_S = 20          # polite observation cadence (transport, not recovery)
QUIET_TICKS = 8      # her own clocks between lessons, read from live_tick
MAX_LOG = 1_000_000


def log(msg: str) -> None:
    if os.path.exists(LOG) and os.path.getsize(LOG) > MAX_LOG:
        os.replace(LOG, LOG + ".1")
    with open(LOG, "a") as fh:
        fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")


def obs() -> dict | None:
    try:
        with urllib.request.urlopen(f"{BASE}/observation", timeout=25) as r:
            return json.load(r)
    except Exception as err:  # noqa: BLE001
        log(f"observation failed: {err}")
        return None


def gates_clear(o: dict) -> bool:
    lo = o.get("last_occurrence") or {}
    return bool(
        o.get("available")
        and not o.get("checkpoint_outstanding")
        and not o.get("durability_blocked")
        and not o.get("checkpoint_error")
        and not o.get("cleanup_error")
        and (o.get("pending_interval_count") or 0) <= 2
        and not lo.get("self_pressure_pending")
        # acoustic-tail guard (Sol's C109 control finding): her own echo
        # can outlive pending-pressure; never present into a self-hearing
        and not lo.get("self_heard_sample_count")
    )


def card_retina(png_path: str) -> tuple:
    """135-site RGB retina (405 u8): sites 0-26 coarse 9x3, 27-134
    central 18x6 — the page's own layout, sampled from the card."""
    from PIL import Image
    img = Image.open(png_path).convert("RGB")
    vals = []
    for w, h in ((9, 3), (18, 6)):
        small = img.resize((w, h))
        px = small.load()
        for y in range(h):
            for x in range(w):
                vals.extend(px[x, y])
    assert len(vals) == 405
    return tuple(int(v) for v in vals)


def wav_blocks(path: str) -> list[bytes]:
    w = wave.open(path)
    if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (16000, 1, 2):
        raise ValueError(f"{path}: not 16kHz mono s16")
    raw = w.readframes(w.getnframes())
    blocks = []
    for i in range(0, len(raw) - 7999, 8000):
        blocks.append(raw[i:i + 8000])
    return blocks or [raw.ljust(8000, b"\0")]


def lessons() -> list[dict]:
    """Pair each card PNG with its letter/number tutor WAV by name."""
    cards = sorted(f for f in os.listdir(os.path.join(CUR, "cards"))
                   if f.endswith(".png") and "preview" not in f)
    auds = {f.split("-")[0]: f for f in os.listdir(os.path.join(CUR, "audio"))
            if f.endswith(".wav")}
    out = []
    for c in cards:
        key = c.split("-")[1] if c.startswith(("alphabet-", "number-")) else c.split("-")[0]
        if key in auds:
            out.append({"name": c[:-4],
                        "card": os.path.join(CUR, "cards", c),
                        "wav": os.path.join(CUR, "audio", auds[key])})
    return out


def present_block(retina: tuple, pcm: bytes) -> dict | None:
    body = json.dumps({"kind": "sensory", "payload": {
        "source": "card-microphone",
        "retina_rgb_u8": list(retina),
        "pcm_s16le_base64": base64.b64encode(pcm).decode(),
    }}).encode()
    req = urllib.request.Request(
        f"{BASE}/occurrence", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except Exception as err:  # noqa: BLE001
        log(f"present refused: {err}")
        return None


def wait_clear(min_tick: int | None = None) -> dict | None:
    """Wait on HER state: gates clear and (optionally) her clock past
    min_tick. Returns the clear observation, or None on STOP."""
    while True:
        if os.path.exists(STOP):
            return None
        o = obs()
        if o and gates_clear(o) and (min_tick is None
                                     or (o.get("live_tick") or 0) >= min_tick):
            return o
        time.sleep(POLL_S)


def main() -> None:
    lockf = open(os.path.join(HERE, ".lock"), "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("caretaker already running")
        return
    plan = lessons()
    if not plan:
        log("no lessons found — exiting")
        return
    st = {"next": 0, "presented": 0}
    if os.path.exists(STATE):
        try:
            st.update(json.load(open(STATE)))
        except Exception:  # noqa: BLE001
            pass
    log(f"caretaker started pid {os.getpid()} lessons={len(plan)} next={st['next']}")
    while not os.path.exists(STOP):
        lesson = plan[st["next"] % len(plan)]
        retina = card_retina(lesson["card"])
        blocks = wav_blocks(lesson["wav"])
        o = wait_clear()
        if o is None:
            break
        ok = True
        for i, pcm in enumerate(blocks):
            res = present_block(retina, pcm)
            if res is None:
                ok = False
                break  # never retried; lesson re-presents next window
            tick = (res.get("observation") or {}).get("live_tick") or 0
            log(f"{lesson['name']} block {i+1}/{len(blocks)} accepted tick {tick}")
            if i + 1 < len(blocks):
                if wait_clear(min_tick=tick + 1) is None:
                    ok = False
                    break
        if ok:
            st["presented"] += 1
            st["next"] += 1
            json.dump(st, open(STATE, "w"))
            end = obs()
            end_tick = (end or {}).get("live_tick") or 0
            log(f"lesson {lesson['name']} complete; quiet until her tick {end_tick + QUIET_TICKS}")
            if wait_clear(min_tick=end_tick + QUIET_TICKS) is None:
                break
        else:
            log(f"lesson {lesson['name']} interrupted; will re-present")
            time.sleep(POLL_S)
    log("caretaker stopped (STOP or signal)")


if __name__ == "__main__":
    main()
