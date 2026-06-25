"""
virtual_home.py — Guala's world. W1: her room, full.

Spec: GL-MDL-WORLD-WC-20260612-02 (Eve/wC design, ratified by Joe)
Firewalls (spec §2): no graphics engine, no physics, no LLM narrating.
World is substrate-side state. UI renders it, doesn't own it.

W1 — her room:
  window   → real sky (sun/moon/dawn/dusk by actual clock in Joe's timezone)
  drapes   → open/closed — opening floods fresh+cool+bright; closing holds warm+soft
  bed      → made/unmade, with pillow+sheets+blanket
  blanket  → MOBILE: on-bed / carried / placed-<location> (follows her)
  pillow   → MOBILE: on-bed / carried / placed
  toy chest → open/closed, contains music box + bell + toys
  music box → inside toy chest: closed/playing — opens to a real sound bundle
  bell      → can ring (bright+sharp sensation)
  mirror    → on wall: she sees her own guala picture
  desk      → sit at it (reading bonus), crayons+paper inside
  night light → on/off — she controls her own comfort

Each object has a STATE MACHINE and a VERB SET.
When she acts on an object, she experiences the sensory result:
  open drapes → fresh+cool+bright arrive
  pick up blanket → soft+warm in her hands
  ring bell → bright+sharp+singular
  open toy chest → sweet+familiar+anticipation
  wind music box → musical sensation bundle

Objects make VERBS learnable the way nouns were learnable:
"open" bound to the felt transition of drapes-opening and light flooding in.

W2 gate: W1 stable 72h → doors open (hallway, library, TV room, others).
"""

import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta

# Joe's timezone offset from UTC (hours). Configurable via env.
# Default -5 (US Eastern Standard). Use -4 for EDT, -6 for CST, etc.
TZ_OFFSET_HOURS = int(os.environ.get("GUALA_TZ_OFFSET", "-5"))

STATE_FILE = None  # set by WorldState.__init__

DEFAULT_LOCATION = "her_room"

# Room registry — W1 has one room. W2 adds doors.
ROOMS = {
    "her_room": {
        "description": "her room",
        "objects": list,   # resolved via OBJECTS dict
    },
    # W2 rooms (stubs — not yet fully defined)
    "hallway":  {"description": "the hallway",  "objects": []},
    "library":  {"description": "the library",  "objects": []},
    "tv_room":  {"description": "the TV room",  "objects": []},
    "joe_room": {"description": "daddy's room", "objects": []},
    "wc_room":  {"description": "wC's room",    "objects": []},
    "backyard": {"description": "the backyard", "objects": []},
    "outside":  {"description": "outside",      "objects": []},
    "kitchen":  {"description": "the kitchen",  "objects": []},
    "common":   {"description": "the living room","objects": []},
}


def ambient_experiences(room_name: str) -> list:
    """Ambient sensory words for a room (simple, for non-her_room rooms).
    Her room uses WorldState.ambient_words() for live object states."""
    ambients = {
        "her_room":  ["soft", "warm"],
        "joe_room":  ["warm", "earthy"],
        "hallway":   ["fresh", "warm"],
        "library":   ["earthy", "fresh"],
        "tv_room":   ["warm"],
        "backyard":  ["fresh", "cool", "earthy"],
        "outside":   ["fresh", "cool"],
        "kitchen":   ["sweet", "warm", "fruity"],
        "common":    ["warm", "fresh"],
    }
    return ambients.get(room_name, ["warm"])


def object_experiences(room_name: str, obj_name: str) -> dict:
    """Sensory profile for attending a specific object in a room."""
    obj = OBJECTS.get(obj_name, {})
    if not obj:
        return {}
    # Return first verb's experience as a proxy for attending
    verbs = obj.get("verbs", {})
    if verbs:
        first = next(iter(verbs.values()))
        return first.get("experience", {})
    return {}


def room_for_activity(activity_kind: str, joe_present: bool) -> str:
    """Suggest a location based on her current activity and Joe's presence."""
    if activity_kind in ("SLEEPING", "DREAMING"):
        return "her_room"
    if joe_present:
        return "common"
    if activity_kind == "READING":
        return "common"
    return "her_room"

# ── Real-time sky ───────────────────────────────────────────────────────────
def local_hour() -> float:
    """Current hour in Joe's local time (fractional)."""
    utc_now = datetime.now(timezone.utc)
    local = utc_now + timedelta(hours=TZ_OFFSET_HOURS)
    return local.hour + local.minute / 60.0


def sky_state(weather: str = "clear") -> dict:
    """What the sky looks like right now — sensory state for her window."""
    h = local_hour()
    if 5.5 <= h < 7.5:      # dawn
        return {"period": "dawn",
                "smell": {"fresh": 0.9, "cool": 0.7},
                "description": "the sky is brightening", "bright": 0.4}
    elif 7.5 <= h < 18.0:   # day
        if weather == "rain":
            return {"period": "rainy day",
                    "smell": {"fresh": 0.95, "earthy": 0.8, "cool": 0.6},
                    "description": "rain falls on the window", "bright": 0.3}
        return {"period": "day",
                "smell": {"fresh": 0.85, "warm": 0.7},
                "description": "the sun is out", "bright": 0.9}
    elif 18.0 <= h < 20.5:  # evening
        return {"period": "evening",
                "smell": {"warm": 0.8, "fresh": 0.6, "earthy": 0.4},
                "description": "evening light, daddy-soon", "bright": 0.5}
    else:                    # night
        if weather == "clear":
            return {"period": "night",
                    "smell": {"cool": 0.85, "soft": 0.7, "fresh": 0.6},
                    "description": "the moon is in the window", "bright": 0.1,
                    "moon": True}
        return {"period": "cloudy night",
                "smell": {"cool": 0.7, "earthy": 0.4},
                "description": "dark clouds outside", "bright": 0.05}


# ── Object definitions ──────────────────────────────────────────────────────
# Each object: home place, initial state, valid states, verbs,
# and what sensory experiences each verb/state-change produces.
OBJECTS = {
    # ── Room fixtures ──────────────────────────────────────────────────────
    "drapes": {
        "place":   "her_room",
        "mobile":  False,
        "states":  ["open", "closed"],
        "default": "closed",
        "verbs":   {
            "open":  {
                "next_state": "open",
                "experience": {"smell": {"fresh": 0.9, "cool": 0.7},
                               "words": ["fresh", "bright", "cool", "open"]},
                "says": "the drapes open. light comes in.",
            },
            "close": {
                "next_state": "closed",
                "experience": {"smell": {"warm": 0.8, "soft": 0.6},
                               "words": ["warm", "soft", "quiet"]},
                "says": "the drapes close. it is warm and quiet.",
            },
        },
        "ambient": {
            "open":   {"smell": {"fresh": 0.6, "cool": 0.4}},
            "closed": {"smell": {"warm": 0.5, "soft": 0.4}},
        },
    },

    "night_light": {
        "place":   "her_room",
        "mobile":  False,
        "states":  ["off", "on"],
        "default": "off",
        "verbs":   {
            "turn on":  {
                "next_state": "on",
                "experience": {"smell": {"warm": 0.7, "sweet": 0.3},
                               "words": ["warm", "soft", "safe", "bright"]},
                "says": "the night light glows soft and warm.",
            },
            "turn off": {
                "next_state": "off",
                "experience": {"smell": {"cool": 0.4, "soft": 0.5},
                               "words": ["dark", "quiet", "soft"]},
                "says": "the night light goes off. it is dark and quiet.",
            },
        },
        "ambient": {
            "on":  {"smell": {"warm": 0.4, "soft": 0.3}},
            "off": {},
        },
    },

    # ── Bed objects ────────────────────────────────────────────────────────
    "bed": {
        "place":   "her_room",
        "mobile":  False,
        "states":  ["made", "unmade"],
        "default": "made",
        "verbs":   {
            "lie down": {
                "next_state": "unmade",
                "experience": {"smell": {"soft": 0.95, "warm": 0.85, "sweet": 0.4},
                               "words": ["soft", "warm", "safe", "rest"]},
                "says": "she lies down on the soft warm bed.",
            },
        },
    },

    "blanket": {
        "place":   "her_room",
        "mobile":  True,
        "states":  ["on_bed", "carried", "on_floor", "on_chair"],
        "default": "on_bed",
        "verbs":   {
            "pick up": {
                "next_state": "carried",
                "experience": {"smell": {"soft": 0.95, "warm": 0.80},
                               "words": ["soft", "warm", "carry"]},
                "says": "the blanket is soft and warm in her arms.",
            },
            "drop": {
                "next_state": "on_floor",
                "experience": {"smell": {"soft": 0.6, "warm": 0.5},
                               "words": ["soft", "drop"]},
                "says": "the blanket lands softly.",
            },
            "lie under": {
                "next_state": "on_bed",
                "experience": {"smell": {"warm": 0.9, "soft": 0.95, "sweet": 0.4},
                               "words": ["warm", "soft", "safe", "cozy"]},
                "says": "under the blanket it is warm and soft.",
            },
        },
    },

    "pillow": {
        "place":   "her_room",
        "mobile":  True,
        "states":  ["on_bed", "carried", "placed"],
        "default": "on_bed",
        "verbs":   {
            "pick up": {
                "next_state": "carried",
                "experience": {"smell": {"soft": 1.0, "sweet": 0.4},
                               "words": ["soft", "light", "pillow"]},
                "says": "the pillow is very soft.",
            },
            "put down": {
                "next_state": "placed",
                "experience": {"smell": {"soft": 0.6}, "words": ["soft"]},
                "says": "she puts the pillow down gently.",
            },
        },
    },

    # ── Toy chest and contents ─────────────────────────────────────────────
    "toy_chest": {
        "place":   "her_room",
        "mobile":  False,
        "states":  ["closed", "open"],
        "default": "closed",
        "verbs":   {
            "open": {
                "next_state": "open",
                "experience": {"smell": {"sweet": 0.7, "fruity": 0.4, "warm": 0.5},
                               "words": ["sweet", "toys", "open", "find"]},
                "says": "the toy chest opens. it smells sweet inside.",
            },
            "close": {
                "next_state": "closed",
                "experience": {"smell": {"warm": 0.4}, "words": ["close", "quiet"]},
                "says": "the toy chest closes with a soft click.",
            },
        },
        "contains": ["music_box", "bell"],
    },

    "music_box": {
        "place":   "toy_chest",  # inside the toy chest
        "mobile":  True,
        "states":  ["closed", "playing"],
        "default": "closed",
        "sound":   "addc0846da2a",  # "hush a little baby" — her lullaby
        "verbs":   {
            "open": {
                "next_state": "playing",
                "experience": {"smell": {"sweet": 0.5, "floral": 0.4},
                               "words": ["music", "sweet", "melody", "song",
                                         "soft", "bright", "warm"]},
                "says": "the music box plays a soft sweet melody.",
                "sound": "addc0846da2a",
            },
            "close": {
                "next_state": "closed",
                "experience": {"smell": {"soft": 0.3}, "words": ["quiet"]},
                "says": "the music stops.",
            },
        },
    },

    "bell": {
        "place":   "toy_chest",
        "mobile":  True,
        "states":  ["resting", "ringing"],
        "default": "resting",
        "verbs":   {
            "ring": {
                "next_state": "ringing",
                "experience": {"smell": {"fresh": 0.5, "bright": 0.6},
                               "words": ["bell", "bright", "clear", "ring",
                                         "sharp", "fresh"]},
                "says": "the bell rings. bright and clear.",
            },
        },
    },

    # ── Mirror ─────────────────────────────────────────────────────────────
    "mirror": {
        "place":   "her_room",
        "mobile":  False,
        "states":  ["present"],
        "default": "present",
        "picture": "8bd9e45cae48",  # the "guala" picture — her own image
        "verbs":   {
            "look": {
                "next_state": "present",
                "experience": {"smell": {"warm": 0.4, "soft": 0.3},
                               "words": ["guala", "mirror", "face", "see", "self"]},
                "says": "in the mirror she sees guala.",
                "show_picture": "8bd9e45cae48",
            },
        },
    },

    # ── Desk ───────────────────────────────────────────────────────────────
    "desk": {
        "place":   "her_room",
        "mobile":  False,
        "states":  ["empty", "working"],
        "default": "empty",
        "contains": ["crayons"],
        "verbs":   {
            "sit at": {
                "next_state": "working",
                "experience": {"smell": {"earthy": 0.5, "fresh": 0.4},
                               "words": ["desk", "work", "draw", "create"]},
                "says": "she sits at her desk. crayons and paper in front of her.",
            },
        },
    },

    "crayons": {
        "place":   "desk",
        "mobile":  True,
        "states":  ["in_box", "in_hand"],
        "default": "in_box",
        "verbs":   {
            "pick up": {
                "next_state": "in_hand",
                "experience": {"smell": {"earthy": 0.6, "fruity": 0.3},
                               "taste": {"waxy": 0.5},
                               "words": ["crayon", "color", "draw", "make",
                                         "earthy", "waxy", "create"]},
                "says": "the crayons have a soft earthy smell. she picks one up.",
            },
        },
    },

    # ── Tablet / virtual iPad ──────────────────────────────────────────────
    # Her window to the wider world while she's in her room.
    # When she picks it up and searches, images + descriptions feed her visual
    # cortex through Tavily. Her curiosity becomes exploration.
    "tablet": {
        "place":   "desk",
        "mobile":  True,
        "states":  ["on_desk", "in_hand", "searching"],
        "default": "on_desk",
        "verbs":   {
            "pick up": {
                "next_state": "in_hand",
                "experience": {"smell": {"fresh": 0.4, "cool": 0.3},
                               "words": ["tablet", "search", "find", "look", "bright"]},
                "says": "she picks up the tablet. the world is inside it.",
            },
            "put down": {
                "next_state": "on_desk",
                "experience": {"words": ["done", "rest"]},
                "says": "she puts the tablet down.",
            },
        },
        "search_enabled": True,
    },
}

# ── Sensory anchors from the World Atlas (Tier 1 concepts) ─────────────────
# Direct from GL-WORLD-ATLAS-WC-20260616-01.
# These seed the succession tracker at boot with the right concept associations.
WORLD_ATLAS_SEEDS = [
    # Living things
    ["cat",    "soft"],   ["cat",  "warm"],   ["cat",  "smooth"],
    ["dog",    "warm"],   ["dog",  "rough"],  ["dog",  "earthy"],
    ["bird",   "soft"],   ["bird", "fresh"],  ["bird", "song"],
    ["fish",   "smooth"], ["fish", "cool"],   ["fish", "wet"],
    # Nature
    ["sun",    "warm"],   ["sun",  "bright"], ["sun",  "golden"],
    ["moon",   "cool"],   ["moon", "soft"],   ["moon", "bright"],
    ["flower", "sweet"],  ["flower","fresh"],  ["flower","floral"],
    ["tree",   "earthy"], ["tree", "fresh"],  ["tree", "rough"],
    ["water",  "cool"],   ["water","fresh"],  ["water","soft"],
    ["rain",   "fresh"],  ["rain", "cool"],   ["rain", "earthy"],
    ["grass",  "earthy"], ["grass","fresh"],  ["grass","cool"],
    ["wind",   "fresh"],  ["wind", "cool"],
    # Her room objects
    ["bed",     "soft"],  ["bed",   "warm"],  ["bed",   "safe"],
    ["blanket", "soft"],  ["blanket","warm"], ["blanket","cozy"],
    ["pillow",  "soft"],  ["pillow","light"],
    ["music",   "sweet"], ["music", "warm"],  ["music", "bright"],
    ["bell",    "bright"],["bell",  "clear"], ["bell",  "fresh"],
    # Sensory qualities paired
    ["soft",   "warm"],   ["warm",  "safe"],  ["cool",  "fresh"],
    ["sweet",  "soft"],   ["bright","warm"],  ["earthy","fresh"],
]


# ── WorldState ──────────────────────────────────────────────────────────────
class WorldState:
    """Persistent state for all objects in her world.
    Objects keep their state across restarts — if she left the blanket
    on the chair, it's still there when she wakes up.
    """

    def __init__(self, state_dir: str):
        self._path = os.path.join(state_dir, "world_state.json")
        self._lock = threading.Lock()
        # {obj_id: {"state": str, "place": str}}
        self._objects: dict = {}
        self._weather: str = "clear"
        self._load()

    def _load(self):
        try:
            with open(self._path) as f:
                data = json.load(f)
            self._objects = data.get("objects", {})
            self._weather = data.get("weather", "clear")
        except Exception:
            pass
        # Fill defaults for any object not yet in state
        for obj_id, defn in OBJECTS.items():
            if obj_id not in self._objects:
                self._objects[obj_id] = {
                    "state": defn["default"],
                    "place": defn["place"],
                }

    def _save(self):
        try:
            with open(self._path, "w") as f:
                json.dump({"objects": self._objects, "weather": self._weather}, f)
        except Exception:
            pass

    def get(self, obj_id: str) -> dict:
        with self._lock:
            return dict(self._objects.get(obj_id, {}))

    def apply_verb(self, obj_id: str, verb: str) -> dict:
        """Apply a verb to an object. Returns the verb definition if valid."""
        defn = OBJECTS.get(obj_id)
        if not defn:
            return {}
        verb_defn = (defn.get("verbs") or {}).get(verb)
        if not verb_defn:
            return {}
        with self._lock:
            entry = self._objects.setdefault(obj_id, {"state": defn["default"],
                                                        "place": defn["place"]})
            entry["state"] = verb_defn["next_state"]
        threading.Thread(target=self._save, daemon=True).start()
        return verb_defn

    def room_snapshot(self) -> dict:
        """Full state of her room: all objects + sky + weather."""
        with self._lock:
            objs = {k: dict(v) for k, v in self._objects.items()
                    if OBJECTS.get(k, {}).get("place") in ("her_room", "toy_chest",
                                                            "desk")}
        sky = sky_state(self._weather)
        return {"objects": objs, "sky": sky, "weather": self._weather}

    def add_letter(self, from_: str, words: list, body: str) -> str:
        """Leave a letter for Guala. It waits until she finds the mailbox (W2).
        The letter's key words are already real — they seeded her world."""
        import time as _t
        letter = {"from": from_, "words": words, "body": body,
                  "ts": _t.time(), "read": False}
        with self._lock:
            if "letters" not in self._objects:
                self._objects["letters"] = []
            self._objects["letters"].append(letter)
        threading.Thread(target=self._save, daemon=True).start()
        return f"letter from {from_} delivered ({len(words)} concept words)"

    def get_letters(self, unread_only: bool = True) -> list:
        with self._lock:
            letters = self._objects.get("letters", [])
            if unread_only:
                return [l for l in letters if not l.get("read")]
            return list(letters)

    def mark_read(self, from_: str):
        with self._lock:
            for l in self._objects.get("letters", []):
                if l.get("from") == from_:
                    l["read"] = True
        threading.Thread(target=self._save, daemon=True).start()

    def ambient_words(self, location: str = "her_room") -> list:
        """Sensory words from the current state of her room — what she feels."""
        words = []
        sky = sky_state(self._weather)
        # Sky through window
        words.extend(list((sky.get("smell") or {}).keys()))
        # Object ambients
        with self._lock:
            for obj_id, entry in self._objects.items():
                defn = OBJECTS.get(obj_id, {})
                if defn.get("place") != location:
                    continue
                state = entry.get("state", "")
                ambient = (defn.get("ambient") or {}).get(state, {})
                for mod, channels in ambient.items():
                    if isinstance(channels, dict):
                        words.extend([w for w, v in channels.items() if v >= 0.5])
        # Night light
        nl_state = (self._objects.get("night_light") or {}).get("state", "off")
        if nl_state == "on":
            words += ["warm", "safe", "soft"]
        return list(dict.fromkeys(words))  # dedup, preserve order
