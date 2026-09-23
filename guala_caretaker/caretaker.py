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

try:
    from dsf_ai_service.guala_caretaker_hand import material_impact_pcm
except ImportError:
    def material_impact_pcm(material: str, intensity: float = 1.0) -> bytes:  # type: ignore
        import struct
        return struct.pack("<4000h", *([0] * 4000))

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
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
REACH_MM = 800  # her declared reach (guala_home_world)
FOOD_PREFIXES = ("apple", "bread", "milk", "bottle-milk", "cheese", "berries", "carrot")
FOOD_PREFIX = FOOD_PREFIXES[0]
MEAL_DELIVERY_CYCLE = ("apple-delivery", "bread-delivery", "milk-delivery")
DIURNAL_CYCLE_TICKS = 113_600
PLAYPEN_CHALLENGE_TICKS = 14_200
LADDER_CHALLENGE_TICKS = 14_200
CORE_MICROGRAMS = 2_000


def record_story_moment(st: dict, *modalities: str) -> None:
    """Record an episodic multi-modal story moment delivered to Guala.
    Grounded in external physics; prepares memory traces for nocturnal consolidation."""
    st["daily_moments_presented"] = int(st.get("daily_moments_presented") or 0) + 1
    active = st.setdefault("active_modalities_stimulated", {
        "visual": 0, "tactile": 0, "olfactory": 0, "auditory": 0, "proprioceptive": 0, "thermal": 0,
    })
    for m in modalities:
        if m in active:
            active[m] = int(active.get(m) or 0) + 1


def circadian_epoch(tick: int) -> tuple[str, int]:
    """Partition the 113,600-tick diurnal cycle into 6 distinct epochs:
    - DAWN_AWAKENING: ticks 0 - 14,200
    - MORNING_FOCUS: ticks 14,200 - 37,867
    - MIDDAY_STROLL: ticks 37,867 - 56,800
    - AFTERNOON_CHALLENGE: ticks 56,800 - 75,733
    - EVENING_CULTURE: ticks 75,733 - 94,667
    - NIGHT_CONSOLIDATION: ticks 94,667 - 113,600
    Returns (epoch_name, day_number)."""
    day = tick // DIURNAL_CYCLE_TICKS
    phase = tick % DIURNAL_CYCLE_TICKS
    if phase < 14_200:
        epoch = "DAWN_AWAKENING"
    elif phase < 37_867:
        epoch = "MORNING_FOCUS"
    elif phase < 56_800:
        epoch = "MIDDAY_STROLL"
    elif phase < 75_733:
        epoch = "AFTERNOON_CHALLENGE"
    elif phase < 94_667:
        epoch = "EVENING_CULTURE"
    else:
        epoch = "NIGHT_CONSOLIDATION"
    return epoch, day


AUTH_TOKEN = os.environ.get("GUALA_OCCURRENCE_AUTH_TOKEN") or os.environ.get("GUALA_API_TOKEN")


def _occurrence_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("GUALA_OCCURRENCE_AUTH_TOKEN") or os.environ.get("GUALA_API_TOKEN") or AUTH_TOKEN
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-Guala-Token"] = token
    return headers


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
        and not lo.get("self_pressure_pending")
        and not lo.get("self_heard_sample_count")
    )


def someone_else_present(o: dict) -> int | None:
    """Her last interval was actively fed or taught by a human (not unattended, and
    not passive room sound from an open browser microphone) at a tick this caretaker
    did not produce: a person is with her. Returns that tick, else None."""
    lo = o.get("last_occurrence") or {}
    if lo.get("kind") == "unattended":
        return None
    # Active human interventions: direct food presentation or explicit card/word presentation:
    src = lo.get("external_sensory_source")
    pres = lo.get("caregiver_presentation")
    is_active = (pres is not None) or (src in ("card-microphone", "text-microphone", "guided-vocal-microphone", "caretaker-food"))
    if not is_active:
        return None
    tick = lo.get("native_tick")
    return None if tick is None or tick in MINE else tick


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


def card_focal_base64(png_path: str) -> str | None:
    """The card as the 80x60 focal field, RGB row-major, base64 (the page's
    own form; a plain list of 14,400 values exceeds the occurrence body
    bound). None until the focal eye is live."""
    if not FOCAL_EYE_LIVE:
        return None
    from PIL import Image
    small = Image.open(png_path).convert("RGB").resize((80, 60))
    return base64.b64encode(small.tobytes()).decode()


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


def present_block(retina: tuple, pcm: bytes, focal_b64: str | None = None) -> dict | None:
    payload = {
        "source": "card-microphone",
        "retina_rgb_u8": list(retina),
        "pcm_s16le_base64": base64.b64encode(pcm).decode(),
    }
    if focal_b64 is not None:
        payload.update({"focal_rgb_base64": focal_b64, "focal_origin": [0.5, 0.5],
                        "focal_pitch_millidegrees": [60000, 45000], "focal_crop_dimensions": [80, 60]})
    body = json.dumps({"kind": "sensory", "payload": payload}).encode()
    req = urllib.request.Request(
        f"{BASE}/occurrence", data=body,
        headers=_occurrence_headers(), method="POST")
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
        headers=_occurrence_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except Exception as err:  # noqa: BLE001
        log(f"food presentation refused: {err}")
        return None


def _extract_presentation(res: dict | None) -> dict:
    """Extract caregiver presentation payload from API occurrence response or direct presentation dict."""
    if not res or not isinstance(res, dict):
        return {}
    # Real production API envelope: {"observation": {"last_occurrence": {"caregiver_presentation": {...}}}}
    obs = res.get("observation")
    if isinstance(obs, dict):
        lo = obs.get("last_occurrence")
        if isinstance(lo, dict):
            pres = lo.get("caregiver_presentation")
            if isinstance(pres, dict):
                return pres
    # Direct dictionary fallback (mock or internal return)
    if "presented" in res or "steps" in res or "channel" in res or "schema" in res or "touched" in res:
        return res
    return {}


def food_state(o: dict, skip: set[str]) -> tuple[bool, list[str]]:
    """(something edible is already at her mouth, the apples on the floor
    fullest first) from her published world: the apple in her own hand or in
    the caregiver's hand counts as at her mouth while it still has matter.
    Apples the caregiver could not reach last time come last."""
    emb = ((o.get("last_occurrence") or {}).get("embodiment") or {})
    bodies = emb.get("bodies") or []
    objects = emb.get("objects") or []
    remaining = {ob.get("object_id"): ob.get("tastant_remaining_micrograms") for ob in objects}
    self_id = emb.get("self_body_id")
    her = next((b for b in bodies if b.get("body_id") == self_id), None)
    others = [b for b in bodies if b.get("body_id") != self_id]

    def within_reach(b: dict) -> bool:
        if her is None:
            return False
        her_pos = ((her.get("pose") or {}).get("position") or {})
        b_pos = ((b.get("pose") or {}).get("position") or {})
        if "x_mm" not in her_pos or "y_mm" not in her_pos or "x_mm" not in b_pos or "y_mm" not in b_pos:
            return False
        return ((her_pos["x_mm"] - b_pos["x_mm"]) ** 2 + (her_pos["y_mm"] - b_pos["y_mm"]) ** 2) <= REACH_MM ** 2

    at_mouth = False
    carried = []
    for b in bodies:
        held = b.get("held_object_id")
        if not held or (remaining.get(held) or 0) <= CORE_MICROGRAMS:
            continue
        if b.get("body_id") == self_id or within_reach(b):
            at_mouth = True
        else:
            carried.append(held)
    floor = [
        ob for ob in objects
        if any(str(ob.get("object_id", "")).startswith(p) for p in FOOD_PREFIXES)
        and ob.get("held_by_body_id") is None and ob.get("position") is not None
        and (ob.get("tastant_remaining_micrograms") or 0) > CORE_MICROGRAMS
    ]
    floor.sort(key=lambda ob: (ob["object_id"] in skip, -int(ob.get("tastant_remaining_micrograms") or 0)))
    return at_mouth, carried + [ob["object_id"] for ob in floor]


PLAY_TICKS = 240  # about a minute of her clock between offers of a toy
TOYS = ("toy-bear", "stacking-rings", "play-ball", "book", "cup", "glow-stars")
WORD_FOR = {
    "apple": "apple", "toy-bear": "bear", "glow-stars": "star", "book": "book", "cup": "cup",
    "stacking-rings": "ring", "play-ball": "ball", "high-chair": "chair", "playpen": "playpen",
    "bread": "bread", "milk": "milk", "cheese": "cheese", "berries": "berries", "carrot": "carrot",
    "bowl": "bowl", "plate": "plate", "pot": "pot", "pan": "pan", "table": "table", "table-chair": "chair",
    "bed": "bed", "pillow": "pillow", "blanket": "blanket", "lamp": "lamp", "radio": "radio",
    "television": "television", "book-peter-rabbit": "book", "book-wind-willows": "book", "book-aesops-fables": "book", "book-mother-goose": "book", "slide": "slide", "swing": "swing", "sandbox": "sandbox",
}
NAME_ATTENDED_TICKS = 80  # about 20 seconds of debounce between namings of the same attended item


BEDTIME_FRACTION = 0.9   # of her sleep-pressure ceiling: the caretaker makes her bed
BEDDING = frozenset({"pillow", "blanket"})
READ_EVERY_TICKS = 12_000     # about an hour of her beats between readings
READ_KEEP_EVERY_BLOCKS = 96   # the book is shown beside her again this often, so the caregiver stays through the chapter
READ_BLOCK_RETRIES = 40       # a block her service refused is tried again this many times, three seconds apart: longer than a cutover's blip
READ_BLOCK_RETRY_S = 3
READ_BOOK = "Alice's Adventures in Wonderland"   # the first book; the next titles follow when this one is read through
MUSIC_EVERY_TICKS = 12_000    # about an hour of her beats between pieces of music on the radio
MUSIC_MAX_BLOCKS = 2_400      # ten minutes of a piece at most in one sitting
BEDTIME_RETRY_BEATS = 10_000   # about an hour of her beats between tries until both are on the bed
LULLABY_HZ = (330, 330, 392, 330, 330, 392, 330, 392, 523, 494, 440, 440, 392, 294, 330, 349, 294, 294, 330, 349, 294, 349, 494, 440, 392, 494, 523)
LULLABY_BEATS = (1, 1, 2, 1, 1, 2, 1, 1, 2, 2, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 3)  # quarter-second blocks per note


def birdsong_blocks() -> list[bytes]:
    """Outdoor nature birdsong synthesis as 8,000-byte blocks (0.25 s at 16 kHz):
    Frequency-modulated avian calls between 2.2 kHz and 4.2 kHz with bell-like harmonics."""
    import math, struct
    blocks = []
    chirp_configs = [
        (2200.0, 3600.0, 16.0, 5000.0),
        (3600.0, 2600.0, 24.0, 4500.0),
        (1800.0, 2400.0, 8.0, 2000.0),
        (2600.0, 4200.0, 20.0, 5500.0),
    ]
    for f_start, f_end, mod_rate, amp in chirp_configs:
        samples = []
        for i in range(4000):
            t = i / 16000.0
            f_inst = f_start + (f_end - f_start) * (i / 4000.0)
            env = math.sin(math.pi * (i / 4000.0)) ** 1.5
            vibrato = 80.0 * math.sin(2 * math.pi * mod_rate * t)
            phase = 2 * math.pi * (f_inst + vibrato) * t
            v = amp * env * (0.8 * math.sin(phase) + 0.2 * math.sin(2 * phase))
            samples.append(int(max(-32767, min(32767, v))))
        pcm = struct.pack("<4000h", *samples)
        blocks.append(pcm)
    return blocks


def lullaby_blocks() -> list[bytes]:
    """A soft lullaby as 8,000-byte blocks (0.25 s at 16 kHz): a sine with a
    warm second harmonic and a gentle rise and fall on every note."""
    import math, struct
    blocks = []
    for hz, beats in zip(LULLABY_HZ, LULLABY_BEATS):
        n = 4000 * beats
        samples = []
        for i in range(n):
            t = i / 16000.0
            env = min(1.0, i / 800.0, (n - i) / 1600.0)
            v = 4500 * env * (math.sin(2 * math.pi * hz * t) + 0.35 * math.sin(4 * math.pi * hz * t))
            samples.append(int(max(-32767, min(32767, v))))
        pcm = struct.pack(f"<{n}h", *samples)
        blocks.extend(pcm[k:k + 8000] for k in range(0, len(pcm), 8000))
    return blocks


def sing_block(pcm: bytes) -> dict | None:
    """One block of the caretaker's voice at her ears, nothing shown."""
    body = json.dumps({"kind": "sensory", "payload": {"source": "microphone", "pcm_s16le_base64": base64.b64encode(pcm).decode()}}).encode()
    req = urllib.request.Request(f"{BASE}/occurrence", data=body, headers=_occurrence_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except Exception as err:  # noqa: BLE001
        log(f"sing block refused: {err}")
        return None


def her_sleep(o: dict) -> dict:
    return ((o.get("last_occurrence") or {}).get("her_sleep")) or {}


def maybe_bedtime(o: dict, st: dict) -> None:
    """Her pressure near its ceiling and she is awake: the caretaker sets her
    pillow and blanket on her bed. Tried again every BEDTIME_RETRY_BEATS of her
    beats until both are on it (she carries them about by day); the hand skips
    what is already on the bed. Once the bed is made, gentle tuck-in contact
    (forehead kiss, crown pat, and shoulder hold) is delivered. Presenting only."""
    sleep = her_sleep(o)
    pressure = sleep.get("pressure") or [0, 0]
    nights = int(sleep.get("nights") or 0)
    if sleep.get("asleep") or not pressure[1] or pressure[0] / pressure[1] < BEDTIME_FRACTION:
        return
    night = nights + 1
    tick = int(o.get("live_tick") or 0)
    if st.get("bed_made_for_night") != night:
        st["bed_made_for_night"] = night
        st["bed_made"] = []
        st["bedtime_tick"] = None
    if set(st.get("bed_made") or []) >= BEDDING:
        if st.get("bedtime_hug_given_for_night") != night:
            hold = present_food("touch-bedtime-hold")
            if hold is not None:
                pres = ((hold.get("observation") or {}).get("last_occurrence") or {}).get("caregiver_presentation") or {}
                if pres.get("touched"):
                    st["bedtime_hug_given_for_night"] = night
                    contacts = pres.get("contacts") or []
                    log(f"bedtime: gentle tuck-in contact delivered for Night {night} ({pres.get('touched')}) — contacts={len(contacts)}")
                    record_story_moment(st, "tactile", "thermal")
                    with open(STATE, "w") as f:
                        json.dump(st, f)
        return
    if st.get("bedtime_tick") is not None and tick - int(st["bedtime_tick"]) < BEDTIME_RETRY_BEATS:
        return
    st["bedtime_tick"] = tick
    res = present_food("bedtime")
    made = (((res or {}).get("observation") or {}).get("last_occurrence") or {}).get("caregiver_presentation") or {}
    st["bed_made"] = sorted(set(st.get("bed_made") or []) | set(made.get("made") or []))
    log(f"bedtime: pillow and blanket to her bed — made={made.get('made')} so far={st['bed_made']} steps={len(made.get('steps') or [])} last={(made.get('steps') or [None])[-1]}")
    if set(st.get("bed_made") or []) >= BEDDING and st.get("bedtime_hug_given_for_night") != night:
        hold = present_food("touch-bedtime-hold")
        if hold is not None:
            pres = ((hold.get("observation") or {}).get("last_occurrence") or {}).get("caregiver_presentation") or {}
            if pres.get("touched"):
                st["bedtime_hug_given_for_night"] = night
                contacts = pres.get("contacts") or []
                log(f"bedtime: gentle tuck-in contact delivered for Night {night} ({pres.get('touched')}) — contacts={len(contacts)}")
                record_story_moment(st, "tactile", "thermal")
    with open(STATE, "w") as f:
        json.dump(st, f)


def maybe_housekeeping(o: dict, st: dict) -> None:
    """During EVENING_CULTURE, runs joint clean-up with deictic pointing.
    While she sleeps: her bedding returned to the bed and discarded stray apples collected."""
    sleep = her_sleep(o)
    epoch, _ = circadian_epoch(int(o.get("live_tick") or 0))
    tick = int(o.get("live_tick") or 0)
    if not sleep.get("asleep") and epoch == "EVENING_CULTURE":
        if st.get("last_joint_cleanup_tick") is None or tick - int(st["last_joint_cleanup_tick"]) >= 4800:
            st["last_joint_cleanup_tick"] = tick
            res = present_food("joint-clean-up")
            log(f"housekeeping: evening joint clean-up performed — res={bool(res)}")
            with open(STATE, "w") as f:
                json.dump(st, f)
    sleep = her_sleep(o)
    if not sleep.get("asleep"):
        return
    nights = int(sleep.get("nights") or 0)
    if st.get("nocturnal_bed_made_night") != nights:
        res = present_food("bedtime")
        if res is not None:
            st["nocturnal_bed_made_night"] = nights
            log(f"housekeeping: nocturnal bed reset for Night {nights}")
            with open(STATE, "w") as f:
                json.dump(st, f)

    if st.get("nocturnal_tidy_night") != nights:
        res = present_food("clean-up")
        if res is not None:
            st["nocturnal_tidy_night"] = nights
            log(f"housekeeping: nocturnal house tidying performed for Night {nights} (books reshelved, TV reset to boring channel 0, apples cleared) — res={bool(res)}")
            with open(STATE, "w") as f:
                json.dump(st, f)

    emb = (o.get("last_occurrence") or {}).get("embodiment") or {}
    stray_apples = [
        ob for ob in emb.get("objects") or []
        if ob.get("object_id", "").startswith("apple")
        and ob.get("position") is not None
        and ob.get("held_by_body_id") is None
    ]
    if stray_apples:
        tick = int(o.get("live_tick") or 0)
        if st.get("last_apple_tidy_tick") is None or tick - int(st["last_apple_tidy_tick"]) >= 100:
            st["last_apple_tidy_tick"] = tick
            log(f"housekeeping: auditing {len(stray_apples)} stray floor apple(s) for domestic clean-up")
            res = present_food("clean-up")
            log(f"housekeeping: clean-up routine finished — res={bool(res)}")


def maybe_name_attended(o: dict, st: dict) -> None:
    """When she attends to a physical thing — either holding it in her hands
    or focusing her gaze on it — the caregiver names it aloud in a human voice.
    Paced and debounced; never interrupts feeding or bedtime."""
    if asleep(o):
        return
    tick = int(o.get("live_tick") or 0)
    lo = o.get("last_occurrence") or {}
    her_eye = lo.get("her_eye") or {}
    target_id = her_eye.get("target")

    emb = lo.get("embodiment") or {}
    self_id = emb.get("self_body_id")
    her = next((b for b in (emb.get("bodies") or []) if b.get("body_id") == self_id), None)
    held_id = her.get("held_object_id") if her else None

    attended = held_id or target_id
    if not attended or not isinstance(attended, str):
        return

    base_thing = attended.split("-")[0] if attended.startswith("apple") else attended
    if base_thing not in WORD_FOR:
        return

    last_thing = st.get("last_named_thing")
    last_tick = int(st.get("last_named_tick") or 0)
    if attended == last_thing and tick < last_tick + NAME_ATTENDED_TICKS:
        return

    heard = say_word(base_thing)
    if heard > 0:
        st["last_named_thing"] = attended
        st["last_named_tick"] = tick
        log(f"attention: named '{attended}' ({WORD_FOR[base_thing]}) at her tick {tick} ({heard} beats)")
        record_story_moment(st, "auditory", "visual")


def maybe_echo_syllable(o: dict, st: dict) -> None:
    """When she speaks a syllable, the caregiver echoes her syllable in its own
    airway voice (from person-body-1) with the room's geometry at her ears.
    Echoed once per utterance; encourages causal vocal reciprocity."""
    lo = o.get("last_occurrence") or {}
    drive = lo.get("said_drive")
    if not drive or not isinstance(drive, (list, tuple)) or len(drive) < 3:
        return
    tick = int(o.get("live_tick") or 0)
    if tick == st.get("last_echoed_tick"):
        return

    try:
        import voice
        caregiver_drive = (voice.PITCHES_DECIHERTZ[0], int(drive[1]), int(drive[2]))
        pcm = voice.syllable_pcm(caregiver_drive, seed=tick)
        res = play_block(pcm, from_object="person-body-1")
        if res is not None:
            st["last_echoed_tick"] = tick
            MINE.append(tick)
            log(f"echo: echoed her syllable drive={drive} from person-body-1 at tick {tick}")
            record_story_moment(st, "auditory", "proprioceptive")
    except Exception as err:  # noqa: BLE001
        log(f"echo refused or failed: {err}")


TOUCH_EVERY_TICKS = 600   # about 2.5 minutes between spontaneous somatic affection moments
TOUCH_GESTURES = ("touch-hug", "touch-kiss", "touch-hold-hand", "touch-pat", "touch-shoulder", "touch-lap", "touch-bedtime-hold")
TV_EVERY_TICKS = 4_800    # about 20 minutes between TV demonstrations
STROLL_EVERY_TICKS = 7_200  # about 30 minutes between outdoor stroller walks


def maybe_touch(o: dict, st: dict) -> None:
    """Stage 1 Somatic Affection: Physical touch on her skin (short hugs, forehead kisses,
    holding hands, head pats, shoulder touch, lap hold, bedtime hold). Conducts physical
    warmth and provides somatosensory grounding and homeostatic regulation.
    Geometry only; no reward grading."""
    sleep = her_sleep(o)
    if sleep.get("asleep"):
        return
    tick = int(o.get("live_tick") or 0)
    if st.get("touch_next_tick") is not None and tick < int(st["touch_next_tick"]):
        return
    st["touch_next_tick"] = tick + TOUCH_EVERY_TICKS
    idx = int(st.get("touch_index") or 0)
    touch_id = TOUCH_GESTURES[idx % len(TOUCH_GESTURES)]
    st["touch_index"] = idx + 1
    res = present_food(touch_id)
    json.dump(st, open(STATE, "w"))
    if res is not None:
        pres = ((res.get("observation") or {}).get("last_occurrence") or {}).get("caregiver_presentation") or {}
        if pres.get("touched"):
            contacts = pres.get("contacts") or []
            log(f"affection: {pres.get('touched')} delivered — contacts={len(contacts)} steps={len(pres.get('steps') or [])}")
            record_story_moment(st, "tactile", "proprioceptive", "thermal")


def maybe_tv(o: dict, st: dict) -> None:
    """TV demonstration: during AFTERNOON_CHALLENGE, verifies geometric line-of-sight
    alignment with the screen before remote operation, accompanied by acoustic labeling
    'television' (optical/retinal receptor verification left open)."""
    sleep = her_sleep(o)
    if sleep.get("asleep"):
        return
    epoch, _ = circadian_epoch(int(o.get("live_tick") or 0))
    if epoch != "AFTERNOON_CHALLENGE":
        return
    tick = int(o.get("live_tick") or 0)
    if st.get("tv_next_tick") is not None and tick < int(st["tv_next_tick"]):
        return
    st["tv_next_tick"] = tick + TV_EVERY_TICKS

    lo = o.get("last_occurrence") or {}
    seen = lo.get("seen")
    if seen is None:
        log(f"tv: geometric visibility evidence unavailable at tick {tick}; demonstration withheld (retinal certification open)")
        return
    if "television" not in seen:
        say_word("television")
        log(f"tv: screen not in geometric line-of-sight (seen={seen}) at tick {tick}; calling attention (retinal certification open)")
        return

    res1 = present_food("tv-remote")
    res2 = present_food("tv-remote-cycle")
    pres2 = _extract_presentation(res2)
    ch = pres2.get("channel", 0)
    named = say_word("television")
    log(f"tv: demonstrated tv-remote cycle to channel {ch} with verified geometric visibility of screen — named={named} at tick {tick}")
    record_story_moment(st, "auditory", "visual")


def maybe_stroll(o: dict, st: dict) -> None:
    """Outdoor stroll: during MIDDAY_STROLL, the caregiver brings the stroller carriage
    beside her, holds her hand for an excursion along the walkway, plays outdoor
    nature birdsong audio blocks, and animates visual fauna flutter."""
    sleep = her_sleep(o)
    if sleep.get("asleep"):
        return
    epoch, _ = circadian_epoch(int(o.get("live_tick") or 0))
    if epoch != "MIDDAY_STROLL":
        return
    tick = int(o.get("live_tick") or 0)
    if st.get("stroll_next_tick") is not None and tick < int(st["stroll_next_tick"]):
        return
    st["stroll_next_tick"] = tick + STROLL_EVERY_TICKS
    res = present_food("stroller-carriage")
    pres_stroller = _extract_presentation(res)
    stroller_applied = pres_stroller.get("presented", False)
    touch = present_food("touch-hold-hand")
    pres_touch = _extract_presentation(touch)
    hand_held = pres_touch.get("touched") == "hold_hand" or pres_touch.get("presented", False)
    b_blocks = birdsong_blocks()
    sung = 0
    for block in b_blocks[:4]:
        r = sing_block(block)
        if r is not None:
            sung += 1
            ob = r.get("observation") or {}
            MINE.append(ob.get("live_tick") or 0)
            MINE.append((ob.get("last_occurrence") or {}).get("native_tick"))
    log(f"stroll: stroller carriage excursion (stroller_applied={stroller_applied}, hand_held={hand_held}, birdsong={sung}/{len(b_blocks)}) at tick {tick}")
    delivered = ["auditory"]
    if stroller_applied:
        delivered.extend(["visual", "proprioceptive"])
    if hand_held:
        delivered.extend(["tactile", "thermal"])
    record_story_moment(st, *delivered)


def maybe_read(o: dict, st: dict) -> None:
    """Read to her: during EVENING_CULTURE, the caregiver fetches the book, holds Guala
    in their lap (lap holding / torso embrace), reading LibriVox chapters.
    Provides periodic lap-contact stabilization throughout reading engagement."""
    import media
    sleep = her_sleep(o)
    if sleep.get("asleep"):
        return
    epoch, _ = circadian_epoch(int(o.get("live_tick") or 0))
    if epoch != "EVENING_CULTURE":
        return
    tick = int(o.get("live_tick") or 0)
    if st.get("read_next_tick") is not None and tick < int(st["read_next_tick"]):
        return
    st["read_next_tick"] = tick + READ_EVERY_TICKS
    catalog_items = list(media.BOOK_CATALOG.items())
    title_idx = int(st.get("read_title_index") or 0)
    current_key, current_entry = catalog_items[title_idx % len(catalog_items)]
    current_title = current_entry["title"]
    book_pres_id = f"read-{current_key}" if current_key != "book" else "read-book"
    try:
        book = media.librivox_book(current_title)
        st["read_book"] = book
        chapters = media.chapters(book["archive"])
        index = int(st.get("read_chapter") or 0) % max(1, len(chapters))
        chapter = chapters[index]
        pcm_path = media.fetch_chapter(book["archive"], chapter["name"])
        blocks = media.blocks(pcm_path)
    except Exception as err:  # noqa: BLE001
        log(f"reading: the library could not give the chapter for {current_title}: {err}")
        st["read_title_index"] = title_idx + 1
        st["read_chapter"] = 0
        return
    res = present_food(book_pres_id)
    made = (((res or {}).get("observation") or {}).get("last_occurrence") or {}).get("caregiver_presentation") or {}
    if not made.get("reading"):
        log(f"reading: the caregiver could not bring the book beside her — steps={len(made.get('steps') or [])} last={(made.get('steps') or [None])[-1]}")
        return
    lap = present_food("touch-lap")
    lap_presentation = (((lap or {}).get("observation") or {}).get("last_occurrence") or {}).get("caregiver_presentation") or {}
    lap_touched = lap_presentation.get("touched") if isinstance(lap_presentation, dict) else None
    if lap_touched:
        log(f"reading: lap holding established ({lap_touched}) for story time")
    else:
        log("reading: lap holding could not be established; reading beside her")
    log(f"reading: {book['title']}, chapter file {chapter['name']} ({len(blocks)} beats of sound) begins at tick {tick}")
    record_story_moment(st, "auditory", "visual", "tactile")
    heard = 0
    for i, pcm in enumerate(blocks):
        if os.path.exists(STOP) or os.path.exists(TEACHING):
            log("reading: interrupted by caretaker stop or teaching signal")
            break
        r = None
        for attempt in range(READ_BLOCK_RETRIES + 1):
            if os.path.exists(STOP) or os.path.exists(TEACHING):
                break
            r = sing_block(pcm)
            if r is not None:
                break
            for _ in range(int(READ_BLOCK_RETRY_S * 10)):
                if os.path.exists(STOP) or os.path.exists(TEACHING):
                    break
                time.sleep(0.1)
        if os.path.exists(STOP) or os.path.exists(TEACHING):
            log("reading: interrupted by caretaker stop or teaching signal during retries")
            break
        if r is None:
            log("reading: her service refused a block repeatedly; the book closes for now")
            break
        heard += 1
        ob = r.get("observation") or {}
        MINE.append(ob.get("live_tick") or 0)
        MINE.append((ob.get("last_occurrence") or {}).get("native_tick"))
        if asleep(ob):
            log("reading: she fell asleep; the book closes")
            break
        if (i + 1) % READ_KEEP_EVERY_BLOCKS == 0:
            kept = {}
            for attempt in range(3):
                keep = present_food(book_pres_id)
                kept = (((keep or {}).get("observation") or {}).get("last_occurrence") or {}).get("caregiver_presentation") or {}
                if kept.get("reading"):
                    present_food("touch-lap")
                    break
                time.sleep(2)
            if not kept.get("reading"):
                misses = int(st.get("_read_misses", 0)) + 1
                st["_read_misses"] = misses
                tail = (kept.get("steps") or [])[-3:]
                log(f"reading: the caregiver could not bring the book beside her this time (miss {misses}; steps={len(kept.get('steps') or [])} last={tail}); the voice goes on")
                if misses >= 3:
                    log("reading: the book could not be brought to her three times running; the book closes")
                    break
            else:
                st["_read_misses"] = 0
    if heard >= len(blocks):
        st["read_chapter"] = index + 1
        if index + 1 >= len(chapters):
            st["read_title_index"] = title_idx + 1
            st["read_chapter"] = 0
            log(f"reading: finished entire book {book['title']}; cycling to next title")
    else:
        st["read_chapter"] = index
    with open(STATE, "w") as f:
        json.dump(st, f)
    log(f"reading: {heard} of {len(blocks)} beats reached her ears; next chapter index {st['read_chapter']}")


def room_of_point(o: dict, position: dict) -> str | None:
    """Which of her rooms a point lies in, from the regions the observation carries."""
    emb = (o.get("last_occurrence") or {}).get("embodiment") or {}
    x, y = position.get("x_mm"), position.get("y_mm")
    for region in emb.get("regions") or []:
        b = region.get("bounds") or {}
        lo, hi = b.get("minimum") or {}, b.get("maximum") or {}
        if lo and hi and lo["x_mm"] <= x <= hi["x_mm"] and lo["y_mm"] <= y <= hi["y_mm"]:
            return region.get("region_id")
    return None


def say_word(thing: str) -> int:
    """The word for a thing, at her ears, block by block; the beats that reached her."""
    import media
    word = WORD_FOR.get(thing.split("-")[0] if thing.startswith("apple") else thing)
    if word is None:
        return 0
    try:
        pcm_path = media.commons_word(word)
    except Exception as err:  # noqa: BLE001
        log(f"word: the library could not give '{word}': {err}")
        return 0
    if pcm_path is None:
        return 0
    heard = 0
    for pcm in media.blocks(pcm_path):
        r = sing_block(pcm)
        if r is None:
            break
        heard += 1
        ob = r.get("observation") or {}
        MINE.append(ob.get("live_tick") or 0)
        MINE.append((ob.get("last_occurrence") or {}).get("native_tick"))
    return heard


def play_block(pcm: bytes, from_object: str) -> dict | None:
    """One beat of a thing's sound in her world (the radio): her ears get it by
    the room's geometry between her and the thing."""
    body = json.dumps({"kind": "sensory", "payload": {"source": "thing-sound", "from_object": from_object, "pcm_s16le_base64": base64.b64encode(pcm).decode()}}).encode()
    req = urllib.request.Request(f"{BASE}/occurrence", data=body, headers=_occurrence_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except Exception as err:  # noqa: BLE001
        log(f"radio block refused: {err}")
        return None


def maybe_music(o: dict, st: dict) -> None:
    """Music on the radio: once in MUSIC_EVERY_TICKS of her beats while she is
    awake, one public-domain piece (Musopen, from the Internet Archive) sounds
    from the radio in her world, block by block at her beat; her ears hear it by
    the room's geometry, so walking toward it or away changes what she hears.
    The radio is brought into a world that predates it, once."""
    import media
    sleep = her_sleep(o)
    if sleep.get("asleep"):
        return
    tick = int(o.get("live_tick") or 0)
    if st.get("music_next_tick") is not None and tick < int(st["music_next_tick"]):
        return
    st["music_next_tick"] = tick + MUSIC_EVERY_TICKS
    if not st.get("radio_in_world"):
        res = present_food("radio-delivery")
        made = (((res or {}).get("observation") or {}).get("last_occurrence") or {}).get("caregiver_presentation") or {}
        if not made.get("delivered"):
            log(f"radio: the world refused its arrival — {made.get('steps')}")
            return
        st["radio_in_world"] = True
        log(f"radio: brought into her world as {made.get('delivered')}")
    emb = (o.get("last_occurrence") or {}).get("embodiment") or {}
    radio = next((ob for ob in (emb.get("objects") or []) if ob.get("object_id") == "radio"), None)
    her_room = emb.get("room_id")
    if radio is not None and radio.get("position") is not None and her_room and room_of_point(o, radio["position"]) != her_room:
        res = present_food("radio-to-her")
        made = (((res or {}).get("observation") or {}).get("last_occurrence") or {}).get("caregiver_presentation") or {}
        log(f"radio: carried to her — presented={made.get('presented')} set_down={made.get('set_down')} steps={len(made.get('steps') or [])}")
    try:
        index = int(st.get("music_index") or 0)
        archive, licence = media.MUSIC_ITEMS[index % len(media.MUSIC_ITEMS)]
        tracks = media.tracks(archive)
        if not tracks:
            log(f"radio: {archive} has no sound files; skipping")
            st["music_index"] = index + 1
            return
        track_index = int(st.get("music_track") or 0) % len(tracks)
        track = tracks[track_index]
        pcm_path = media.fetch_track(archive, track["name"], licence)
        blocks = media.blocks(pcm_path)[:MUSIC_MAX_BLOCKS]
    except Exception as err:  # noqa: BLE001
        log(f"radio: the library could not give the piece: {err}")
        return
    log(f"radio: {archive} — {track['name']} ({len(blocks)} beats of sound) begins at tick {tick}")
    record_story_moment(st, "auditory")
    heard = 0
    for i, pcm in enumerate(blocks):
        r = None
        for attempt in range(READ_BLOCK_RETRIES + 1):
            if os.path.exists(STOP) or os.path.exists(TEACHING):
                break
            r = play_block(pcm, "radio")
            if r is not None:
                break
            for _ in range(int(READ_BLOCK_RETRY_S * 10)):
                if os.path.exists(STOP) or os.path.exists(TEACHING):
                    break
                time.sleep(0.1)
        if r is None:
            log("radio: her service refused a block repeatedly; the radio goes quiet")
            break
        heard += 1
        ob = r.get("observation") or {}
        MINE.append(ob.get("live_tick") or 0)
        MINE.append((ob.get("last_occurrence") or {}).get("native_tick"))
        if (i + 1) % READ_KEEP_EVERY_BLOCKS == 0 and asleep(ob):
            log("radio: she fell asleep; the radio goes quiet")
            break
    if track_index + 1 >= len(tracks):
        st["music_index"] = index + 1
        st["music_track"] = 0
    else:
        st["music_track"] = track_index + 1
    json.dump(st, open(STATE, "w"))
    log(f"radio: {heard} of {len(blocks)} beats sounded; next {st.get('music_index', index)}/{st.get('music_track', 0)}")


def maybe_lullaby(o: dict, st: dict) -> None:
    """She has fallen asleep: the caretaker sings once, at her ears."""
    sleep = her_sleep(o)
    if not sleep.get("asleep"):
        return
    nights = int(sleep.get("nights") or 0)
    if st.get("lullaby_for_night") == nights:
        return
    st["lullaby_for_night"] = nights
    blocks = lullaby_blocks()
    sung = sum(1 for pcm in blocks if sing_block(pcm) is not None)
    log(f"lullaby: {sung} of {len(blocks)} blocks reached her (night {nights})")
    record_story_moment(st, "auditory")


def asleep(o: dict) -> bool:
    """Her published sleep (her_sleep.asleep, or the act 'sleep')."""
    lo = o.get("last_occurrence") or {}
    sleep = lo.get("her_sleep") or {}
    return bool(sleep.get("asleep")) or lo.get("her_act") == "sleep"


def maybe_play(o: dict, st: dict) -> None:
    """When she is not hungry and her hands are empty, the caregiver fetches a
    toy that lies on the floor and holds it out to her; she takes it, carries
    it, sets it down; next time the caregiver fetches it again. Presents only;
    never moves her."""
    tick = o.get("live_tick") or 0
    if tick < (st.get("play_tick") or 0) + PLAY_TICKS:
        return
    lo = o.get("last_occurrence") or {}
    deficit = lo.get("metabolic_need_reserve_deficit") or [0, 1]
    try:
        hungry = (deficit[0] / deficit[1]) > HUNGRY_DEFICIT if deficit[1] else False
    except (TypeError, ZeroDivisionError, IndexError):
        hungry = False
    if hungry:
        return
    emb = lo.get("embodiment") or {}
    bodies = emb.get("bodies") or []
    if any(b.get("held_object_id") for b in bodies):
        return
    on_floor = {ob.get("object_id") for ob in emb.get("objects") or [] if ob.get("position") is not None}
    choices = [t for t in TOYS if t in on_floor]
    if not choices:
        return
    toy = choices[(st.get("play_index") or 0) % len(choices)]
    st["play_index"] = (st.get("play_index") or 0) + 1
    st["play_tick"] = tick
    res = present_food(toy)
    json.dump(st, open(STATE, "w"))
    if res is None:
        return
    pres = _extract_presentation(res)
    named = say_word(toy) if pres.get("presented") else 0
    if pres.get("presented"):
        impact_pcm = material_impact_pcm("wood", intensity=0.8)
        sing_block(impact_pcm)
        record_story_moment(st, "tactile", "visual", "auditory", "proprioceptive")
    log(f"play: offered {toy} — presented={pres.get('presented', False)} steps={len(pres.get('steps') or [])} named={named}")


def maybe_playpen_challenge(o: dict, st: dict) -> None:
    """During MORNING_FOCUS: Caregiver places Guala inside playpen at (2050, 6700)
    creating physical boundary impedance that drives vocal signaling, followed by release
    and a caregiver affection hug presentation (touch-hug)."""
    if asleep(o):
        return
    epoch, _ = circadian_epoch(int(o.get("live_tick") or 0))
    if epoch != "MORNING_FOCUS":
        return
    tick = int(o.get("live_tick") or 0)
    if st.get("playpen_next_tick") is not None and tick < int(st["playpen_next_tick"]):
        return
    st["playpen_next_tick"] = tick + PLAYPEN_CHALLENGE_TICKS
    res1 = present_food("playpen-containment")
    pres1 = _extract_presentation(res1)
    contained = pres1.get("presented", False)
    impact_pcm = material_impact_pcm("wood", intensity=0.9)
    sing_block(impact_pcm)
    log(f"challenge: playpen containment presentation applied={contained} at tick {tick}")
    res2 = present_food("playpen-release")
    pres2 = _extract_presentation(res2)
    released = pres2.get("presented", False)
    hug_steps = pres2.get("steps") or []
    hug_delivered = any(s.get("operation") == "touch" and s.get("reason") == "applied" for s in hug_steps)
    log(f"challenge: playpen release presentation applied={released}, caregiver hug presentation delivered={hug_delivered} at tick {tick}")
    modalities = ["auditory"]
    if contained or released:
        modalities.extend(["proprioceptive", "visual"])
    if hug_delivered:
        modalities.append("tactile")
    record_story_moment(st, *modalities)
    with open(STATE, "w") as f:
        json.dump(st, f)


def maybe_ladder_challenge(o: dict, st: dict) -> None:
    """During AFTERNOON_CHALLENGE: Caregiver approaches the garden-ladder and garden-apple
    beneath the apple tree at (14000, 11800), demonstrating vertical tool affordance."""
    if asleep(o):
        return
    epoch, _ = circadian_epoch(int(o.get("live_tick") or 0))
    if epoch != "AFTERNOON_CHALLENGE":
        return
    tick = int(o.get("live_tick") or 0)
    if st.get("ladder_next_tick") is not None and tick < int(st["ladder_next_tick"]):
        return
    st["ladder_next_tick"] = tick + LADDER_CHALLENGE_TICKS
    res = present_food("ladder-challenge")
    if res is not None:
        pres = _extract_presentation(res)
        presented = pres.get("presented", False)
        if presented:
            impact_pcm = material_impact_pcm("metal", intensity=0.85)
            sing_block(impact_pcm)
            record_story_moment(st, "visual", "proprioceptive", "auditory")
            log(f"challenge: backyard ladder affordance challenge presented at tick {tick} — steps={len(pres.get('steps') or [])}")
        else:
            log(f"challenge: backyard ladder affordance challenge refused at tick {tick} — steps={len(pres.get('steps') or [])}")
        with open(STATE, "w") as f:
            json.dump(st, f)


def maybe_feed(o: dict, st: dict) -> None:
    """Present a meal when due. Reads her world; decides nothing about her.
    In MORNING_FOCUS/DAWN_AWAKENING, places Guala in the high chair at (3500, 1500)
    when hunger is verified and meal interval has elapsed, rotating diet across bread, milk, and apple.
    Strictly holds meals during NIGHT_CONSOLIDATION."""
    if "tastant_remaining_micrograms" not in json.dumps(o)[:200000]:
        return
    epoch, _ = circadian_epoch(int(o.get("live_tick") or 0))
    if epoch == "NIGHT_CONSOLIDATION":
        return
    tick = o.get("live_tick") or 0
    if tick < (st.get("meal_tick") or 0) + MEAL_TICKS and not st.get("meal_retry"):
        return
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

    # Verified hunger deficit and meal interval: now seat Guala in high chair if not already there
    seated_this_meal = False
    if epoch in ("DAWN_AWAKENING", "MORNING_FOCUS"):
        emb = (o.get("last_occurrence") or {}).get("embodiment") or {}
        her_b = next((b for b in (emb.get("bodies") or []) if b.get("body_id") == emb.get("self_body_id")), None)
        her_pos = ((her_b.get("pose") or {}).get("position") or {}) if her_b else {}
        if her_pos.get("x_mm") != 3500 or her_pos.get("y_mm") != 1500:
            chair_res = present_food("high-chair-meal")
            chair_pres = _extract_presentation(chair_res)
            chair_steps = chair_pres.get("steps") or []
            chair_applied = chair_pres.get("presented", False) or any(s.get("reason") == "applied" for s in chair_steps)
            log(f"meal: Guala placed in high-chair at (3500, 1500) for morning meal — applied={chair_applied}")
            seated_this_meal = chair_applied

    foods = [f for f in foods if f not in skip]
    if not foods:
        cycle_idx = int(st.get("meal_cycle_index") or 0)
        delivery_choice = MEAL_DELIVERY_CYCLE[cycle_idx % len(MEAL_DELIVERY_CYCLE)]
        st["meal_cycle_index"] = cycle_idx + 1
        log(f"no food with matter left within reach; bringing fresh {delivery_choice}")
        foods = [delivery_choice]
    food = foods[0]
    res = present_food(food)
    st["meal_tick"] = tick
    st["meal_retry"] = False
    if res is None:
        json.dump(st, open(STATE, "w"))
        return
    ob = res.get("observation") or {} if isinstance(res, dict) else {}
    MINE.append(ob.get("live_tick") or 0)
    MINE.append((ob.get("last_occurrence") or {}).get("native_tick"))
    pres = _extract_presentation(res)
    steps = pres.get("steps") or []
    named = say_word(food) if pres.get("presented") else 0
    if pres.get("presented"):
        mat = "ceramic" if "milk" in food else "wood"
        impact_pcm = material_impact_pcm(mat, intensity=0.7)
        sing_block(impact_pcm)
        record_story_moment(st, "olfactory", "tactile", "visual", "auditory")
    log(f"meal: named={named} presented {food} — presented={pres.get('presented')} took_away={pres.get('took_away')} "
        f"steps={len(steps)} last={steps[-1] if steps else None}")
    if not pres.get("presented") and food not in MEAL_DELIVERY_CYCLE and food != DELIVERY_ID:
        st["unreachable"] = sorted(skip | {food})
        st["meal_retry"] = len(foods) > 1

    # Meal-complete release lifecycle:
    # Release Guala from high chair back to kitchen floor at (3500, 2200, 0)
    # completing the seated-to-released lifecycle so high-chair boundary does not trap her
    if epoch in ("DAWN_AWAKENING", "MORNING_FOCUS"):
        rel_res = present_food("high-chair-release")
        rel_pres = _extract_presentation(rel_res)
        rel_steps = rel_pres.get("steps") or []
        rel_applied = rel_pres.get("presented", False) or any(s.get("reason") == "applied" for s in rel_steps)
        log(f"meal: Guala released from high-chair to floor at (2700, 1500) — applied={rel_applied}")

    json.dump(st, open(STATE, "w"))


def ready_for_lesson(o: dict, st: dict | None = None) -> bool:
    """A card lesson requires an awake, upright, attentive pupil.
    Lessons hold during bedtime, sleep, meals, or when lying down."""
    if not gates_clear(o):
        return False
    if asleep(o):
        return False
    lo = o.get('last_occurrence') or {}
    sleep = her_sleep(o)
    pressure = sleep.get('pressure') or [0, 0]
    if pressure[1] and (pressure[0] / pressure[1]) > 0.85:
        return False
    emb = lo.get('embodiment') or {}
    her_b = next((b for b in (emb.get('bodies') or []) if b.get('body_id') == emb.get('self_body_id')), None)
    if her_b:
        posture = (her_b.get('pose') or {}).get('posture')
        if posture == 'lying':
            return False
    deficit = lo.get('metabolic_need_reserve_deficit') or [0, 1]
    if deficit and len(deficit) == 2 and deficit[1] and (deficit[0] / deficit[1]) > HUNGRY_DEFICIT:
        return False
    if st is not None and st.get('active_ritual') in ('BEDTIME', 'MEALTIME'):
        return False
    return True


def wait_clear(min_tick: int | None = None, st: dict | None = None) -> dict | None:
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
            if hold is not None and (o.get("live_tick") or 0) < hold:
                time.sleep(POLL_S)
                continue
            if not gates_clear(o):
                time.sleep(POLL_S)
                continue
            if st is not None:
                cur_tick = int(o.get("live_tick") or 0)
                cur_epoch, cur_day = circadian_epoch(cur_tick)
                if st.get("circadian_epoch") != cur_epoch:
                    log(f"circadian transition: Day {cur_day + 1} entering {cur_epoch} at tick {cur_tick}")
                    st["circadian_epoch"] = cur_epoch
                    st["circadian_day"] = cur_day
                    if cur_epoch == "NIGHT_CONSOLIDATION":
                        st["nocturnal_consolidation_cycles"] = int(st.get("nocturnal_consolidation_cycles") or 0) + 1
                        moments = st.get("daily_moments_presented", 0)
                        mods = st.get("active_modalities_stimulated", {})
                        log(f"consolidation: Night consolidation initiated for Day {cur_day + 1}. Daily story moments presented: {moments}, active modalities: {mods}, total consolidation cycles: {st['nocturnal_consolidation_cycles']}")
                    with open(STATE, "w") as f:
                        json.dump(st, f)
                maybe_lullaby(o, st)
            if asleep(o):
                if st is not None and not st.get("asleep_logged"):
                    log(f"she is asleep (tick {o.get('live_tick')}); nocturnal housekeeping active")
                    st["asleep_logged"] = True
                if st is not None:
                    maybe_housekeeping(o, st)
                time.sleep(POLL_S)
                continue
            if st is not None and st.get("asleep_logged"):
                log(f"she is awake (tick {o.get('live_tick')}); the caretaker resumes")
                st["asleep_logged"] = False
            if st is not None:
                lo = o.get("last_occurrence") or {}
                deficit = lo.get("metabolic_need_reserve_deficit") or [0, 1]
                hungry = (deficit[0] / deficit[1]) > HUNGRY_DEFICIT if (deficit and len(deficit) == 2 and deficit[1]) else False
                emb = lo.get("embodiment") or {}
                her_b = next((b for b in (emb.get("bodies") or []) if b.get("body_id") == emb.get("self_body_id")), None)
                her_pos = ((her_b.get("pose") or {}).get("position") or {}) if her_b else {}
                her_room = room_of_point(o, her_pos) if her_pos.get("x_mm") is not None else None

                if asleep(o) or (her_b and (her_b.get("pose") or {}).get("posture") == "lying") or ((her_sleep(o).get("sleep_pressure") or 0) > 0.85):
                    ritual = "BEDTIME"
                elif hungry:
                    ritual = "MEALTIME"
                elif her_room == "backyard":
                    ritual = "YARD_EXPLORATION"
                elif st.get("read_next_tick") is not None and (o.get("live_tick") or 0) < int(st.get("read_next_tick")) and int(st.get("read_chapter") or 0) > 0:
                    ritual = "STORY_AND_SONG"
                else:
                    ritual = "PLAYPEN_NOVELTY"

                if st.get("active_ritual") != ritual:
                    log(f"developmental ritual transition: {ritual} (room={her_room}, hungry={hungry})")
                    st["active_ritual"] = ritual
                    json.dump(st, open(STATE, "w"))

                maybe_feed(o, st)
                maybe_bedtime(o, st)
                maybe_housekeeping(o, st)
                maybe_touch(o, st)
                maybe_name_attended(o, st)
                maybe_echo_syllable(o, st)
                maybe_play(o, st)
                maybe_tactile_curriculum(o, st)
                maybe_tv(o, st)
                maybe_stroll(o, st)
                maybe_playpen_challenge(o, st)
                maybe_ladder_challenge(o, st)
                maybe_read(o, st)
                maybe_music(o, st)

                if not ready_for_lesson(o, st):
                    ritual = st.get('active_ritual', 'UNKNOWN')
                    if not st.get('lesson_hold_logged') or st.get('lesson_hold_ritual') != ritual:
                        log(f'lesson holding: pupil not in attentive learning state (ritual={ritual}, asleep={asleep(o)})')
                        st['lesson_hold_logged'] = True
                        st['lesson_hold_ritual'] = ritual
                    time.sleep(POLL_S)
                    continue
                if st.get('lesson_hold_logged'):
                    log('lesson resumed: pupil alert and ready for learning')
                    st['lesson_hold_logged'] = False
                    st['lesson_hold_ritual'] = None
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
        try:
            lesson = plan[st["next"] % len(plan)]
            retina = card_retina(lesson["card"])
            focal_b64 = card_focal_base64(lesson["card"])
            blocks = wav_blocks(lesson["wav"])
            o = wait_clear(st=st)
            if o is None:
                break
            maybe_feed(o, st)
            maybe_touch(o, st)
            maybe_name_attended(o, st)
            maybe_echo_syllable(o, st)
            maybe_play(o, st)
            maybe_tv(o, st)
            maybe_stroll(o, st)
            maybe_playpen_challenge(o, st)
            maybe_ladder_challenge(o, st)
            ok = True
            for i, pcm in enumerate(blocks):
                res = present_block(retina, pcm, focal_b64)
                if res is None:
                    ok = False
                    break
                ob = res.get("observation") or {}
                tick = ob.get("live_tick") or 0
                MINE.append(tick)
                MINE.append((ob.get("last_occurrence") or {}).get("native_tick"))
                sites = (ob.get("last_occurrence") or {}).get("external_retinal_site_count")
                action = (ob.get("last_occurrence") or {}).get("requested_world_action")
                log(f"{lesson['name']} block {i+1}/{len(blocks)} accepted tick {tick} retinal sites {sites} world action {action}")
                if i + 1 < len(blocks):
                    if wait_clear(min_tick=tick + 1, st=st) is None:
                        ok = False
                        break
            if ok:
                st["presented"] += 1
                st["next"] += 1
                record_story_moment(st, "visual", "auditory")
                json.dump(st, open(STATE, "w"))
                end = obs()
                end_tick = (end or {}).get("live_tick") or 0
                log(f"lesson {lesson['name']} complete; quiet until her tick {end_tick + QUIET_TICKS}")
                if wait_clear(min_tick=end_tick + QUIET_TICKS, st=st) is None:
                    break
            else:
                now = obs()
                now_tick = (now or {}).get("live_tick") or 0
                log(f"lesson {lesson['name']} interrupted; holding until her tick {now_tick + PERSON_HOLD_TICKS}, then re-present")
                if wait_clear(min_tick=now_tick + PERSON_HOLD_TICKS, st=st) is None:
                    break
        except Exception as err:
            log(f"caretaker loop error: {err}")
            time.sleep(POLL_S)
    log("caretaker stopped (STOP or signal)")


TACTILE_OBJECTS = ("cup", "stacking-rings", "play-ball", "toy-bear")


def maybe_tactile_curriculum(o: dict, st: dict) -> None:
    """Tactile object exploration curriculum: alternately explores cups, rings,
    blocks, and toys with material impact dynamics and acoustic naming."""
    if asleep(o):
        return
    epoch, _ = circadian_epoch(int(o.get("live_tick") or 0))
    if epoch not in ("MORNING_FOCUS", "AFTERNOON_CHALLENGE"):
        return
    tick = int(o.get("live_tick") or 0)
    if st.get("tactile_next_tick") is not None and tick < int(st["tactile_next_tick"]):
        return
    st["tactile_next_tick"] = tick + 3600
    idx = int(st.get("tactile_index") or 0)
    toy = TACTILE_OBJECTS[idx % len(TACTILE_OBJECTS)]
    st["tactile_index"] = idx + 1
    res = present_food(toy)
    mat = "wood" if toy == "stacking-rings" else ("ceramic" if toy == "cup" else "fabric")
    impact_pcm = material_impact_pcm(mat, intensity=0.75)
    sing_block(impact_pcm)
    named = say_word(toy)
    log(f"tactile curriculum: presented {toy} ({mat}) — named={named} at tick {tick}")
    record_story_moment(st, "tactile", "visual", "auditory", "proprioceptive")
    with open(STATE, "w") as f:
        json.dump(st, f)


if __name__ == "__main__":
    main()
