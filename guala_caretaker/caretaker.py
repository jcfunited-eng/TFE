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
DECK: the approved manifest (curriculum/card_experience_manifest-v1.json):
every experience that names a card surface AND a tutor recording, both
files verified against the manifest's sha256. Nothing is paired by
filename guessing (Joe, 2026-09-13: the old name-guess deck reached 5 of
37 recorded lessons and looped on "A").
YIELD (Sol's recommendation 2026-09-13, explicit coordination first):
while guala_caretaker/TEACHING exists a person is teaching and lessons
hold; remove it and lessons resume at the saved place. Safety net only,
for when nobody set the marker: an interval fed by anyone other than
this caretaker, or a refused presentation, holds lessons for
PERSON_HOLD_TICKS of her clock — a politeness constant like POLL_S,
not a law. The caretaker never competes with a person for her one mouth.
"""
from __future__ import annotations

import base64
import collections
import fcntl
import hashlib
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
FOCAL_EYE_LIVE = os.path.exists(os.path.join(HERE, "FOCAL_EYE_LIVE"))  # touch this file after the 903-site cutover
QUIET_TICKS = 32     # Sol's measured recovery law 2026-09-11: 32 physical settlements between lessons
MAX_LOG = 1_000_000
MANIFEST = os.path.join(CUR, "card_experience_manifest-v1.json")
TEACHING = os.path.join(HERE, "TEACHING")  # explicit teaching-session control: exists while a person teaches (touched/removed on Joe's word)
PERSON_HOLD_TICKS = 32  # safety-net hold after an unannounced feed or a refusal; politeness, not a recovery law
MINE = collections.deque(maxlen=256)  # her ticks this caretaker produced; any other fed tick = a person is with her
# MEALS (2026-09-14): the caretaker presents food — the person body in her
# world fetches a fresh apple and holds it out within her reach. Whether she
# bites is her own reflex; the caretaker never moves her. A meal is offered
# when nothing is at her mouth that a bite can still take from, and not more
# often than MEAL_TICKS of her clock — politeness, not a hunger rule.
MEAL_TICKS = 400
HUNGRY_DEFICIT = 0.40  # her feeding law starts below 60 percent of capacity
DELIVERY_ID = "apple-delivery"  # asks the caregiver to bring a fresh apple from outside
FOOD_PREFIX = "apple"
CORE_MICROGRAMS = 2_000  # below this an apple is a core: a bite takes a geometric share of what is left, and under two milligrams that is nothing worth a walk


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
        # pending_interval_count is completed work awaiting SAVE, not queued
        # attention (Sol, 2026-09-13) — save pressure is already covered by
        # checkpoint_outstanding/durability_blocked; a full mailbox shows as a
        # refused POST, which is never retried. Do not gate on it.
        and not lo.get("self_pressure_pending")
        # acoustic-tail guard (Sol's C109 control finding): her own echo
        # can outlive pending-pressure; never present into a self-hearing
        and not lo.get("self_heard_sample_count")
    )


def someone_else_present(o: dict) -> int | None:
    """Her last interval was fed (not unattended) at a tick this caretaker
    did not produce: a person is with her. Returns that tick, else None."""
    lo = o.get("last_occurrence") or {}
    if lo.get("kind") == "unattended":
        return None
    tick = lo.get("native_tick")
    return None if tick is None or tick in MINE else tick


def card_retina(png_path: str) -> tuple:
    """135-site RGB retina (405 u8): sites 0-26 coarse 9x3, 27-134
    central 18x6 — the page's own layout, sampled from the card."""
    from PIL import Image
    img = Image.open(png_path).convert("RGB")
    vals = []
    # legacy 405 first (27 coarse 9x3, 108 center 18x6), then — once the
    # 903-site eye is live — the 32x24 focal field (768 sites), row-major,
    # per the filed transport contract. FOCAL_EYE_LIVE gates the shape so
    # a pre-upgrade production (405 only) is never sent a refused payload.
    tiers = ((9, 3), (18, 6)) + (((32, 24),) if FOCAL_EYE_LIVE else ())
    for w, h in tiers:
        small = img.resize((w, h))
        px = small.load()
        for y in range(h):
            for x in range(w):
                vals.extend(px[x, y])
    assert len(vals) in (405, 2709)
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


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lessons() -> list[dict]:
    """The deck is the approved manifest, in manifest order: every
    experience naming a card surface AND a tutor recording, both files
    present and matching the manifest's sha256. A card without a tutor
    voice is not a lesson. Nothing is paired by filename guessing."""
    manifest = json.load(open(MANIFEST))
    out, skipped = [], []
    for e in manifest.get("experiences", []):
        surface = e.get("surface") or {}
        audio = e.get("tutor_audio") or {}
        if not surface.get("path") or not audio.get("path"):
            continue
        card = os.path.join(CUR, "cards", os.path.basename(surface["path"]))
        wav = os.path.join(CUR, "audio", os.path.basename(audio["path"]))
        if not (os.path.exists(card) and os.path.exists(wav)) \
                or _sha256(card) != surface.get("sha256") \
                or _sha256(wav) != audio.get("sha256"):
            skipped.append(e.get("experience_id"))
            continue
        out.append({"name": e.get("experience_id"), "card": card, "wav": wav})
    if skipped:
        log(f"manifest experiences skipped (file missing or sha256 mismatch): {skipped}")
    return out


def present_block(retina: tuple, pcm: bytes) -> dict | None:
    # The caretaker presents and encourages only: a card's light and a tutor
    # voice. It never moves her body (Joe, 2026-09-14): exploring, moving and
    # learning are hers alone.
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


def present_food(object_id: str) -> dict | None:
    body = json.dumps({"kind": "sensory", "payload": {
        "source": "caretaker-food",
        "present_food": object_id,
    }}).encode()
    req = urllib.request.Request(
        f"{BASE}/occurrence", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except Exception as err:  # noqa: BLE001
        log(f"food presentation refused: {err}")
        return None


def food_state(o: dict, skip: set[str]) -> tuple[bool, list[str]]:
    """(something edible is already at her mouth, the apples on the floor
    fullest first) from her published world: the apple in her own hand or in
    the caregiver's hand counts as at her mouth while it still has matter.
    Apples the caregiver could not reach last time come last."""
    emb = ((o.get("last_occurrence") or {}).get("embodiment") or {})
    bodies = emb.get("bodies") or []
    objects = emb.get("objects") or []
    remaining = {ob.get("object_id"): ob.get("tastant_remaining_micrograms") for ob in objects}
    held_ids = {b.get("held_object_id") for b in bodies if b.get("held_object_id")}
    # The world's bite takes floor(mass × 3600 / 8100) per channel: a channel of
    # 2 µg or less can never come off, so an eaten core (five channels of 2,
    # 10 µg in all) is not food; anything above that still has a mouthful.
    at_mouth = any((remaining.get(i) or 0) > CORE_MICROGRAMS for i in held_ids)
    floor = [
        ob for ob in objects
        if str(ob.get("object_id", "")).startswith(FOOD_PREFIX)
        and ob.get("held_by_body_id") is None and ob.get("position") is not None
        and (ob.get("tastant_remaining_micrograms") or 0) > CORE_MICROGRAMS
    ]
    floor.sort(key=lambda ob: (ob["object_id"] in skip, -int(ob.get("tastant_remaining_micrograms") or 0)))
    return at_mouth, [ob["object_id"] for ob in floor]


def maybe_feed(o: dict, st: dict) -> None:
    """Present a meal when due. Reads her world; decides nothing about her.
    A presentation the world did not allow (a thing boxed in by furniture)
    is remembered so the next candidate is tried at the next clear window."""
    if "tastant_remaining_micrograms" not in json.dumps(o)[:200000]:
        return  # the feeding route is not live yet; nothing to present
    tick = o.get("live_tick") or 0
    if tick < (st.get("meal_tick") or 0) + MEAL_TICKS and not st.get("meal_retry"):
        return
    # Food is offered when she is hungry (her own published reserve deficit
    # above HUNGRY_DEFICIT); otherwise the caregiver stays home. Presenting
    # only, never deciding for her.
    deficit = ((o.get("last_occurrence") or {}).get("metabolic_need_reserve_deficit") or [0, 1])
    try:
        hungry = (deficit[0] / deficit[1]) > HUNGRY_DEFICIT if deficit[1] else False
    except (TypeError, ZeroDivisionError, IndexError):
        hungry = False
    if not hungry:
        if st.get("not_hungry_logged") != tick // 2000:
            log(f"not hungry (deficit {deficit[0]}/{deficit[1]}); no meal offered")
            st["not_hungry_logged"] = tick // 2000
        return
    skip = set(st.get("unreachable") or [])
    at_mouth, foods = food_state(o, skip)
    if at_mouth:
        st["meal_retry"] = False
        return
    foods = [f for f in foods if f not in skip]  # an unreachable apple is not retried; a fresh one is brought instead
    if not foods:
        # Nothing edible within reach: the caregiver brings a fresh apple
        # from outside (the world's grocery boundary) and presents it.
        log("no apple with matter left within reach; bringing a fresh one")
        foods = [DELIVERY_ID]
    food = foods[0]
    res = present_food(food)
    st["meal_tick"] = tick
    st["meal_retry"] = False
    if res is None:
        json.dump(st, open(STATE, "w"))
        return
    ob = res.get("observation") or {}
    MINE.append(ob.get("live_tick") or 0)
    MINE.append((ob.get("last_occurrence") or {}).get("native_tick"))
    pres = (ob.get("last_occurrence") or {}).get("caregiver_presentation") or {}
    steps = pres.get("steps") or []
    log(f"meal: presented {food} — presented={pres.get('presented')} took_away={pres.get('took_away')} "
        f"steps={len(steps)} last={steps[-1] if steps else None}")
    if not pres.get("presented") and food != DELIVERY_ID:
        st["unreachable"] = sorted(skip | {food})
        st["meal_retry"] = len(foods) > 1
    else:
        st["unreachable"] = []
    json.dump(st, open(STATE, "w"))


def wait_clear(min_tick: int | None = None) -> dict | None:
    """Wait on HER state: gates clear, her clock past min_tick, no
    TEACHING marker, and no one else feeding her. Explicit control first:
    the TEACHING marker holds until it is removed. Safety net: a tick fed
    by someone else pushes the hold to that tick + PERSON_HOLD_TICKS.
    Returns the clear observation, or None on STOP."""
    hold = min_tick
    teaching_logged = False
    while True:
        if os.path.exists(STOP):
            return None
        if os.path.exists(TEACHING):
            if not teaching_logged:
                log("TEACHING marker present: a person is teaching; lessons hold until it is removed")
                teaching_logged = True
            time.sleep(POLL_S)
            continue
        if teaching_logged:
            log("TEACHING marker removed; lessons resume at the saved place")
            teaching_logged = False
        o = obs()
        if o:
            other = someone_else_present(o)
            if other is not None and (hold is None or other + PERSON_HOLD_TICKS > hold):
                hold = other + PERSON_HOLD_TICKS
                log(f"unannounced feed by someone else (tick {other}); safety hold until her tick {hold}")
            if gates_clear(o) and (hold is None or (o.get("live_tick") or 0) >= hold):
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
        maybe_feed(o, st)
        ok = True
        for i, pcm in enumerate(blocks):
            res = present_block(retina, pcm)
            if res is None:
                ok = False
                break  # never retried; lesson re-presents next window
            ob = res.get("observation") or {}
            tick = ob.get("live_tick") or 0
            MINE.append(tick)
            MINE.append((ob.get("last_occurrence") or {}).get("native_tick"))
            sites = (ob.get("last_occurrence") or {}).get("external_retinal_site_count")
            action = (ob.get("last_occurrence") or {}).get("requested_world_action")
            log(f"{lesson['name']} block {i+1}/{len(blocks)} accepted tick {tick} retinal sites {sites} world action {action}")
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
            # a refusal means her one mouth is in someone else's use:
            # hold the recovery window before re-presenting, never fight
            now = obs()
            now_tick = (now or {}).get("live_tick") or 0
            log(f"lesson {lesson['name']} interrupted; holding until her tick {now_tick + PERSON_HOLD_TICKS}, then re-present")
            if wait_clear(min_tick=now_tick + PERSON_HOLD_TICKS) is None:
                break
    log("caretaker stopped (STOP or signal)")


if __name__ == "__main__":
    main()
