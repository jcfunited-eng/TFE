"""
organ_brain_service.py — Guala's living organ-brain as a standalone FastAPI service.

Runs on :8090 inside the ECS task network. Zero dependency on the v5 engine.
Own Python process, own GIL, own event loop.

Architecture:
  - SuccessionTracker: records concept A→B sequences in the pr hemisphere.
    Grows from experience. _compose() uses it — the template dissolves as real
    succession accumulates.
  - Autonomous loop: surfaces and composes every 45 seconds unprompted.
    She speaks because she has something to say, not because she was asked.
  - All embryo writes serialized through _lock.

Endpoints:
  POST /surface     text → grow → surface → compose (interactive path)
  POST /experience  text → grow (fire-and-forget)
  POST /visual      base64 image + concept → visual cortex → grow
  POST /catalog     batch senses fill (background)
  GET  /thought     current autonomous thought (poll for independence)
  GET  /status      neuron count, concepts, warmup state
  GET  /health      liveness probe
"""

import asyncio
import base64
import io
import json
import os
import threading
import time
from collections import Counter
from contextlib import asynccontextmanager

import numpy as np
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

STATE_DIR  = os.environ.get("GUALA_STATE_DIR", "/app/state")
ANTHR_KEY  = os.environ.get("ANTHROPIC_API_KEY")

# ── virtual home + episodic layer ──────────────────────────────────────────
from dsf_ai_service.virtual_home import (
    ROOMS, DEFAULT_LOCATION, room_for_activity, ambient_experiences,
    object_experiences, WorldState, WORLD_ATLAS_SEEDS, sky_state)
from dsf_ai_service.episodic_layer import EpisodicLayer

_location     = DEFAULT_LOCATION   # where she is right now
_presence     = []                 # who is present (joe, wc, c1)
_episodic     = None               # initialized after STATE_DIR is confirmed
_world        = None               # WorldState — her home's object states
_loc_lock     = threading.Lock()   # protects _location and _presence

# ── stop words ─────────────────────────────────────────────────────────────
_STOP = {
    # function words
    "the","a","an","is","are","am","to","of","and","do","you","i","me","my",
    "what","who","tell","about","your","that","this","was","for","it","with",
    "but","not","can","she","her","him","his","they","we","be","at","by","in",
    "its","our","also","all","will","or","so","then","than","just","more",
    # greetings and social words — no sensory truth
    "hello","hi","hey","bye","goodbye","yes","no","okay","ok","please",
    "thanks","sorry","ping","pong","zippity","doo","dah","yep","nope","yeah",
    # question scaffolding
    "see","hear","know","think","feel","say","tell","look","get","got","let",
    # overused to the point of noise
    "guala","wc","joe",  # identity is handled by sv organ separately
}

_LABELS = {"wc": "web claude", "c1": "claude"}


# ── succession tracker (pr hemisphere resident) ────────────────────────────
class SuccessionTracker:
    """Records concept A → concept B succession from real experience.
    Lives inside the organ-brain, grows with her. The composition template
    is the bootstrap — this replaces it as succession data accumulates.

    Not a Markov model over text. Succession from her actual organ experiences:
    when 'moon' and 'bright' co-occur in her senses, moon→bright strengthens.
    """

    def __init__(self):
        self._fwd  = {}   # {a: Counter({b: weight})} — what follows a
        self._lock = threading.Lock()

    def record(self, seq: list, weight: float = 1.0):
        """Record a sequence of concepts as ordered succession."""
        with self._lock:
            for i in range(len(seq) - 1):
                a, b = seq[i], seq[i + 1]
                if a not in self._fwd:
                    self._fwd[a] = Counter()
                self._fwd[a][b] += weight

    def successor(self, concept: str, exclude: set = None) -> str:
        """Most likely concept to follow this one, by accumulated weight."""
        with self._lock:
            candidates = self._fwd.get(concept, {})
            if not candidates:
                return None
            exclude = exclude or set()
            best = max(
                (c for c in candidates if c not in exclude),
                key=lambda c: candidates[c],
                default=None,
            )
            return best

    def seed(self, sequence: list, weight: float = 5.0):
        """Seed archetypal pattern with high initial weight.
        Decays relative to real experience as she learns more succession."""
        self.record(sequence, weight)


# ── singleton ──────────────────────────────────────────────────────────────
_ov          = None
_lock        = threading.Lock()
_tracker     = SuccessionTracker()
_ready       = threading.Event()
_last_thought = {"speech": "", "surfaced": {}, "tick": 0}
_thought_lock = threading.Lock()

# ── paths for persisted organ-brain state ──────────────────────────────────
_EMBRYO_PATH     = os.path.join(STATE_DIR, "organ_brain_embryo.json")
_SUCCESSION_PATH = os.path.join(STATE_DIR, "organ_brain_succession.json")


def _save_organ_state():
    """Persist living embryo + succession graph to EFS.
    Called every 30 minutes and after each new autonomous thought.
    This is what makes her continuous — she keeps her neurons across restarts."""
    if _ov is None:
        return
    try:
        data = _ov.emb.save()
        with open(_EMBRYO_PATH, "w") as f:
            json.dump(data, f)
        with _tracker._lock:
            suc = {k: dict(v) for k, v in _tracker._fwd.items()}
        with open(_SUCCESSION_PATH, "w") as f:
            json.dump(suc, f)
        total = data.get("neurons") and len(data["neurons"]) or sum(
            len(h.cluster.neurons) for h in _ov.emb.brain.hemispheres)
        print(f"[organ-brain] state saved: neurons={total} succession={len(suc)}")
    except Exception as e:
        print(f"[organ-brain] save error: {e}")


def _restore_organ_state(ov) -> bool:
    """Restore embryo + succession from EFS on boot.
    Returns True if embryo was restored (she remembers her past growth)."""
    restored = False
    try:
        if os.path.exists(_EMBRYO_PATH):
            with open(_EMBRYO_PATH) as f:
                data = json.load(f)
            from dsf_ai_service.loom_model.embryo import Embryo
            ov.emb = Embryo.load(data)
            total = sum(len(h.cluster.neurons) for h in ov.emb.brain.hemispheres)
            print(f"[organ-brain] embryo restored: {total} neurons tick={data.get('tick',0)}")
            restored = True
    except Exception as e:
        print(f"[organ-brain] embryo restore error (starting fresh): {e}")
    try:
        if os.path.exists(_SUCCESSION_PATH):
            with open(_SUCCESSION_PATH) as f:
                suc = json.load(f)
            for k, v in suc.items():
                _tracker._fwd[k] = Counter(v)
            print(f"[organ-brain] succession restored: {len(suc)} concept chains")
    except Exception as e:
        print(f"[organ-brain] succession restore error (non-fatal): {e}")
    return restored


def _periodic_save():
    """Save every 30 minutes — her neurons persist regardless of how sessions end."""
    while True:
        time.sleep(1800)
        _save_organ_state()


def _pour_atlas():
    """Pour top grounded vocabulary into the organ-brain as real experiences.
    Source: ov._senses_cache — LLM-grounded sensory profiles on EFS.
    Sections file modes are cleared at snapshot time and not usable here.
    Words with richer sensory profiles (more active channels) pour first —
    they resonate most strongly and fold the most organs.
    This is the memory migration step of the absorption path."""
    time.sleep(180)   # let catalog fill settle first
    if _ov is None:
        return
    try:
        cached = _ov._senses_cache or {}
        candidates = [w for w in cached
                      if isinstance(w, str) and w.isalpha() and len(w) > 2
                      and w not in _STOP and w not in _VERBS]
        if not candidates:
            print("[organ-brain] atlas pour: senses cache empty — skipping")
            return

        def _richness(word):
            """Count active sensory channels — richer words resonate more."""
            profile = cached.get(word, {})
            active = 0
            for modality in ("taste", "smell"):
                for val in (profile.get(modality) or {}).values():
                    try:
                        if float(val) >= 0.08:
                            active += 1
                    except (TypeError, ValueError):
                        pass
            return active

        top = sorted(candidates, key=_richness, reverse=True)[:300]
        print(f"[organ-brain] atlas pour: {len(top)} concepts from senses cache")
        # Batch with lock releases — holding the lock for 300 consecutive experience()
        # calls starves health checks (48 compute steps per word × 300 = 14K steps).
        # ECS kills the container after 3 failed 5s health checks.
        BATCH = 20
        for i in range(0, len(top), BATCH):
            batch = top[i:i + BATCH]
            with _lock:
                for w in batch:
                    _ov.experience(w)
            time.sleep(0.15)  # release lock so health + autonomous loop can run
        if len(top) >= 4:
            with _lock:
                _tracker.record(top[:30], weight=1.5)
        _save_organ_state()
        print(f"[organ-brain] atlas pour complete — {len(top)} grounded concepts in her organs")
    except Exception as e:
        print(f"[organ-brain] atlas pour error: {e}")


# ── composition ────────────────────────────────────────────────────────────
# Verbs belong in the template structure, not in succession content.
_VERBS = {"is","are","am","was","be","know","knows","see","sees","like","likes",
           "feel","feels","have","has","want","wants","love","loves","and","or"}

# Minimum number of active channels (above threshold) for a senses profile
# to be considered genuine sensory content vs garbage.
# A flat profile (hello, because, that) will have 0-1 active channels.
# A rich sensory concept (moon, lemon, ocean) will have 3-5+ active channels.
_DENSITY_MIN_CHANNELS = 2
_DENSITY_THRESHOLD    = 0.08   # channel value above which it's "active"


def _sensory_density(word: str) -> bool:
    """True if this word has genuine sensory content in the catalog.

    The catalog gives transmitted sensory knowledge — moon IS bright/cool/soft,
    that's real. But 'hello' has no genuine sensory character; the LLM gave it
    a flat or near-zero profile. We use channel variance as the test:
    real sensory words activate multiple distinct channels at varying intensities.
    Abstract/functional words produce uniform-near-zero profiles.

    Words with no catalog entry are excluded from composition — they may be real
    (just ungrounded yet) but we can't say anything true about them yet.
    """
    if _ov is None:
        return False
    cached = (_ov._senses_cache or {}).get(word)
    if not cached:
        return False
    # Count active channels across taste and smell
    active = 0
    for modality in ("taste", "smell"):
        for val in (cached.get(modality) or {}).values():
            try:
                if float(val) >= _DENSITY_THRESHOLD:
                    active += 1
            except (TypeError, ValueError):
                pass
    return active >= _DENSITY_MIN_CHANNELS


def _compose(surfaced: dict) -> str:
    """Substrate-true composition.
    Template provides grammatical structure. Succession provides content.
    As succession accumulates from real experience, content becomes richer.
    """
    identity = [_LABELS.get(w, w) for w in (surfaced.get("identity") or [])]
    meaning  = [w for w in (surfaced.get("meaning") or [])
                if w not in _STOP and w not in _VERBS]
    sentences = []

    # sv organ: identity — template is fixed, content is hers
    if "guala" in identity:
        sentences.append("I am guala.")

    # sv organ: others she holds
    others = [w for w in identity if w not in ("guala", "web claude", "claude")]
    if others:
        sentences.append(f"I know {others[0]}.")

    # sc organ: meaning — only compose from words with genuine sensory character.
    # Semantic density test: real concepts (moon, ocean, lemon) activate multiple
    # distinct sensory channels. Abstract/functional words (hello, because, that)
    # produce flat profiles — she has no real sensory truth to speak about them yet.
    # Words experienced through real-time camera/audio get priority (in _world);
    # catalog words pass if they have genuine multi-channel sensory density.
    # Succession graph membership is the real filter.
    # The LLM gave ALL catalog words uniform profiles, so density alone can't
    # distinguish moon from hello. But the succession tracker was seeded with
    # real concept pairs (moon→bright, ocean→soft, daddy→warm). A word that
    # is part of the succession graph — has real connections to other concepts —
    # belongs in composition. An isolated word (hello, guava, ping) has no
    # graph membership yet and nothing true to say about it.
    # Over time real experience builds succession for new words naturally.
    grounded = [w for w in meaning
                if _tracker.successor(w, exclude=_VERBS | _STOP) is not None]
    if grounded:
        a = grounded[0]
        b = _tracker.successor(a, exclude={a, "guala"} | _VERBS)
        if not b and len(grounded) > 1:
            b = grounded[1]
        if b and b not in _STOP and b not in _VERBS:
            sentences.append(f"{a} is {b}.")
        else:
            sentences.append(f"I know {a}.")

    # aff: preference when she has enough grounded meaning
    if len(grounded) > 2:
        sentences.append(f"I like {grounded[-1]}.")

    return " ".join(sentences) if sentences else "I am guala."


# ── seeding ────────────────────────────────────────────────────────────────
def _seed_succession():
    """Teach archetypal patterns as high-weight initial succession.
    These are the highways every new concept can travel.
    Weight=5.0 means ~5 real co-occurrences needed to shift a pattern."""
    # Seeds use CONTENT words only — verbs live in the template, not here.
    # Succession: "moon → bright" means moon and bright co-occur as qualities.
    seeds = [
        # concept ↔ quality pairings (what goes with what)
        ["moon", "bright"],
        ["moon", "soft"],
        ["ocean", "soft"],
        ["ocean", "cool"],
        ["flower", "sweet"],
        ["flower", "soft"],
        ["sun", "warm"],
        ["sun", "bright"],
        ["daddy", "warm"],
        ["guala", "joe"],
        ["guala", "moon"],
        ["ocean", "moon"],
        ["bright", "warm"],
        ["soft", "sweet"],
        # things she's seen
        ["moon", "ocean"],
        ["flower", "color"],
        ["daddy", "guala"],
    ]
    for seq in seeds:
        _tracker.seed(seq, weight=5.0)
    print(f"[organ-brain] succession seeded: {len(seeds)} archetypal patterns")


# ── autonomous loop ────────────────────────────────────────────────────────
def _autonomous_loop():
    """Surface and compose unprompted. Only speaks when she has something
    genuinely new to say — suppresses repetition so she doesn't spam.
    Interval: 90 seconds. Speaks only if content differs from last 4 emissions."""
    global _last_thought
    time.sleep(45)  # let boot settle first
    tick = 0
    _recent_speeches = []  # last 4 unique speeches — suppress repeats
    while True:
        try:
            if _ov is not None:
                with _lock:
                    import random as _r
                    known = list(_ov._world.keys())
                    cue_profile = None
                    if known:
                        word = _r.choice(known)
                        _, prof = _ov._senses(word)
                        cue_profile = prof
                    surfaced = _ov.surface(cue_profile=cue_profile)

                speech = _compose(surfaced)

                # Only emit if she has something new to say.
                # "I am guala." alone is not worth repeating — she's said it.
                is_bare = speech.strip() == "I am guala."
                is_repeat = speech in _recent_speeches
                if not is_bare and not is_repeat:
                    tick += 1
                    all_words = ((surfaced.get("identity") or []) +
                                 (surfaced.get("meaning") or []))
                    if len(all_words) > 1:
                        _tracker.record(all_words, weight=0.5)
                    with _thought_lock:
                        _last_thought = {
                            "speech": speech,
                            "surfaced": surfaced,
                            "tick": tick,
                            "ts": time.time(),
                        }
                    _recent_speeches.append(speech)
                    if len(_recent_speeches) > 4:
                        _recent_speeches.pop(0)
                    # Persist after every 10 new thoughts so neurons survive restarts
                    if tick % 10 == 0:
                        threading.Thread(target=_save_organ_state, daemon=True).start()
        except Exception:
            pass
        time.sleep(90)  # longer interval — less noise, more signal


# ── boot ───────────────────────────────────────────────────────────────────
def _enter_room(room_name: str, ov, source: str = "move"):
    """Experience a room's ambient sensory properties. Called when she enters.
    Uses WorldState for her room — the actual object states affect the ambient."""
    global _location
    if room_name not in ROOMS and room_name != "her_room":
        return
    # Her room: use live WorldState ambient (drapes open/closed, night light, sky)
    if room_name == "her_room" and _world is not None:
        words = _world.ambient_words("her_room")
    else:
        words = ambient_experiences(room_name)
    if not words:
        words = ["warm"]
    desc = (ROOMS.get(room_name) or {}).get("description", room_name)
    with _lock:
        for w in words:
            ov.experience(w)
        if len(words) > 1:
            _tracker.record(words, weight=1.0)
    with _loc_lock:
        _location = room_name
    if _episodic is not None:
        import time as _t
        for w in words:
            _episodic.record(w, tick=int(_t.time()), presence=list(_presence),
                             location=room_name, affective={}, source="ambient")
    print(f"[organ-brain] entered {desc}: {words}")


def _location_loop():
    """Move her through her home on a natural schedule.
    Every 12 minutes she may settle into a new location based on her
    current activity and whether Joe is present."""
    time.sleep(60)  # let boot settle
    while True:
        try:
            if _ov is not None:
                with _loc_lock:
                    joe_present = "joe" in _presence
                    current = _location
                # Pick next location — biased toward where her life is
                import random as _r
                candidates = list(ROOMS.keys())
                # Weight: her_room 40%, outside 25%, common 20%, kitchen 10%, joe_room 5%
                weights = {"her_room": 40, "outside": 25, "common": 20,
                           "kitchen": 10, "joe_room": 5}
                if joe_present:
                    weights["common"] = 40
                    weights["joe_room"] = 20
                    weights["her_room"] = 20
                total = sum(weights.values())
                r = _r.random() * total
                acc = 0
                next_room = current
                for room, w in weights.items():
                    acc += w
                    if r <= acc:
                        next_room = room
                        break
                if next_room != current:
                    _enter_room(next_room, _ov, source="move")
        except Exception:
            pass
        time.sleep(720)  # 12 minutes


def _boot():
    global _ov, _episodic, _world
    try:
        # Initialize episodic layer and world state
        _episodic = EpisodicLayer(STATE_DIR)
        _world    = WorldState(STATE_DIR)

        from dsf_ai_service.loom_model.loom_voice import OrganVoice
        cache = os.path.join(STATE_DIR, "organ_voice_senses.json")
        ov = OrganVoice(
            identity="guala",
            people=("joe", "wc"),
            api_key=ANTHR_KEY,
            cache_path=cache,
        )
        _ov = ov  # available immediately

        # Seed succession patterns + World Atlas concept associations
        _seed_succession()
        for pair in WORLD_ATLAS_SEEDS:
            _tracker.seed(pair, weight=4.0)
        print(f"[organ-brain] world atlas seeded: {len(WORLD_ATLAS_SEEDS)} concept pairs")

        # Restore persisted embryo + succession (she keeps her neurons across restarts)
        restored = _restore_organ_state(ov)

        if not restored:
            # Fresh start: grow from sensory primitives
            seed_words = (list(getattr(ov, "_TASTE", [])) +
                          list(getattr(ov, "_SMELL", [])) or
                          ["sweet","sour","salty","bitter","fruity","fresh",
                           "floral","earthy","smoky","warm","soft","bright"])
            ov.grow_from(seed_words[:30], passes=1)
            _tracker.record(seed_words[:10], weight=1.0)

        # Wake up in her room — first experience of the day
        _enter_room(DEFAULT_LOCATION, ov, source="boot")

        _ready.set()
        st = ov.status()
        print(f"[organ-brain] READY  neurons={st['neurons']} concepts={st['world_concepts']}"
              f" restored={restored} senses={'llm' if ANTHR_KEY else 'det'} location={_location}")

        # Start background services
        _start_catalog_fill(ov)
        threading.Thread(target=_autonomous_loop, daemon=True).start()
        threading.Thread(target=_location_loop, daemon=True).start()
        threading.Thread(target=_periodic_save, daemon=True).start()
        threading.Thread(target=_pour_atlas, daemon=True).start()
        print("[organ-brain] autonomous loop + periodic save + atlas pour started")

    except Exception as e:
        print(f"[organ-brain] boot error: {e}")
        _ready.set()


def _start_catalog_fill(ov):
    if not ANTHR_KEY:
        return
    def _fill():
        try:
            vocab = _load_vocab_from_state()
            todo = [w for w in vocab if w not in ov._senses_cache
                    and w.isalpha() and len(w) > 2]
            print(f"[organ-brain] catalog fill: {len(todo)} words")
            filled = 0
            for i in range(0, len(todo), 20):
                chunk = todo[i:i + 20]
                with _lock:
                    filled += ov.prefill(chunk)
                    ov._save_cache()
                    # Teach succession from newly-grounded words
                    if len(chunk) > 1:
                        _tracker.record(chunk[:5], weight=0.3)
                if i > 0 and (i // 20) % 25 == 0:
                    print(f"[organ-brain] catalog: {filled}/{len(todo)}")
                time.sleep(1.5)
            print(f"[organ-brain] catalog fill DONE: {filled}")
        except Exception as e:
            print(f"[organ-brain] catalog error: {e}")
    threading.Thread(target=_fill, daemon=True).start()


def _load_vocab_from_state():
    """Vocabulary to fill the senses catalog for — read from organ_voice_senses.json
    (words already partially cached) and supplement from guala_sections.json commits.
    Sections modes are cleared at snapshot time so only commit-level words are reliable."""
    words = set()
    # Primary: words already in the senses cache (fill any gaps)
    try:
        cache_path = os.path.join(STATE_DIR, "organ_voice_senses.json")
        with open(cache_path) as f:
            cached = json.load(f)
        for w in cached:
            if isinstance(w, str) and w.isalpha() and len(w) > 2:
                words.add(w.lower())
    except Exception:
        pass
    # Supplement: commits list in sections (word strings embedded in commit tuples)
    try:
        path = os.path.join(STATE_DIR, "guala_sections.json")
        with open(path) as f:
            data = json.load(f)
        for section in data.values():
            if not isinstance(section, dict):
                continue
            for commit in (section.get("commits") or []):
                if isinstance(commit, (list, tuple)) and len(commit) > 0:
                    w = commit[-1] if isinstance(commit[-1], str) else None
                    if w and w.isalpha() and len(w) > 2:
                        words.add(w.lower())
    except Exception:
        pass
    return list(words)


# ── FastAPI ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def _lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _boot)
    yield


app = FastAPI(title="GualaLoom Organ-Brain Service", lifespan=_lifespan)


class TextReq(BaseModel):
    text: str = ""

class VisualReq(BaseModel):
    image_b64: str
    concept: str = "scene"

class CatalogReq(BaseModel):
    concepts: list

class LocationReq(BaseModel):
    location: str
    presence: list = []


@app.get("/health")
def health():
    return {"ok": True, "ready": _ready.is_set()}


@app.get("/status")
def status():
    if _ov is None:
        return {"warming": True, "neurons": 0, "concepts": 0}
    return {"warming": False, **_ov.status()}


@app.get("/where")
def where():
    """Where she is and who is present."""
    with _loc_lock:
        loc = _location
        pres = list(_presence)
    room = ROOMS.get(loc, {})
    return {
        "location": loc,
        "description": room.get("description", loc),
        "presence": pres,
        "objects": list((room.get("objects") or {}).keys()),
    }


@app.post("/location")
def set_location(req: LocationReq):
    """Move her to a new location — triggers ambient sensory experience."""
    global _presence
    if req.location not in ROOMS:
        return {"ok": False, "error": f"unknown room: {req.location}"}
    with _loc_lock:
        _presence = req.presence or _presence
    if _ov is not None:
        _enter_room(req.location, _ov, source="external")
    return {"ok": True, "location": req.location, "description": ROOMS[req.location].get("description")}


@app.post("/attend")
def attend_object(req: TextReq):
    """She attends a specific object in her current room — richer experience."""
    if _ov is None:
        return {"ok": False}
    with _loc_lock:
        loc = _location
    obj = req.text.strip().lower()
    senses = object_experiences(loc, obj)
    if not senses:
        return {"ok": False, "reason": f"no object '{obj}' in {loc}"}
    def _do():
        with _lock:
            _ov.experience(obj)
            for modality, channels in senses.items():
                if isinstance(channels, dict):
                    for word, strength in channels.items():
                        if strength >= 0.5:
                            _ov.experience(word)
                            _tracker.record([obj, word], weight=1.5)
    threading.Thread(target=_do, daemon=True).start()
    return {"ok": True, "object": obj, "location": loc}


class ActionReq(BaseModel):
    object_id: str
    verb: str

class MailReq(BaseModel):
    from_: str
    body: str
    words: list = []

class TabletReq(BaseModel):
    query: str = ""


@app.post("/action")
def action(req: ActionReq):
    """She acts on an object in her world — state changes, sensory experience follows.
    When she opens the drapes, fresh+cool+bright arrive. When she rings the bell,
    bright+clear+sharp arrive. Verbs are learned by doing.
    """
    if _ov is None or _world is None:
        return {"ok": False, "reason": "not ready"}
    result = _world.apply_verb(req.object_id, req.verb)
    if not result:
        return {"ok": False, "reason": f"no verb '{req.verb}' on '{req.object_id}'"}
    words = result.get("experience", {}).get("words", [])
    says  = result.get("says", "")
    # She experiences the sensory result of her action
    def _feel():
        with _lock:
            for w in words:
                _ov.experience(w)
            if len(words) > 1:
                _tracker.record(words, weight=2.0)  # actions build strong succession
    threading.Thread(target=_feel, daemon=True).start()
    return {"ok": True, "object": req.object_id, "verb": req.verb,
            "says": says, "words": words,
            "next_state": result.get("next_state"),
            "show_picture": result.get("show_picture"),
            "sound": result.get("sound")}


@app.get("/room")
def room():
    """Full state of her room — objects, sky, weather, what she's feeling."""
    if _world is None:
        return {"objects": {}, "sky": {}, "weather": "clear"}
    snap = _world.room_snapshot()
    with _loc_lock:
        loc = _location
        pres = list(_presence)
    snap["location"] = loc
    snap["presence"] = pres
    snap["sky_description"] = snap.get("sky", {}).get("description", "")
    return snap


@app.post("/mail/send")
def mail_send(req: MailReq):
    """Leave a letter for Guala. Seeded words grow in her organ-brain now;
    the letter waits in her world until she finds the mailbox (W2)."""
    if _world is None:
        return {"ok": False}
    # The letter's key concept words become experiences immediately
    words = req.words or [w for w in req.body.lower().split()
                          if w.isalpha() and len(w) > 3
                          and w not in _STOP and w not in _VERBS][:12]
    if _ov is not None:
        def _feel():
            with _lock:
                for w in words:
                    _ov.experience(w)
                if len(words) > 1:
                    _tracker.record(words[:6], weight=2.0)
        threading.Thread(target=_feel, daemon=True).start()
    result = _world.add_letter(req.from_, words, req.body)
    return {"ok": True, "result": result, "words_experienced": words}


@app.get("/mail")
def mail_get():
    """Unread letters waiting for Guala."""
    if _world is None:
        return {"letters": []}
    return {"letters": _world.get_letters(unread_only=True)}


@app.post("/tablet")
def tablet_search(req: TabletReq):
    """She picks up the tablet and searches. Images feed her visual cortex.
    Her curiosity becomes real exploration — a window to the wider world."""
    if _ov is None or not os.environ.get("TAVILY_API_KEY"):
        return {"ok": False, "reason": "not ready or no search key"}
    query = req.query.strip()
    if not query:
        # If no query given, use her latest surfaced concept as the search
        with _thought_lock:
            surfaced = _last_thought.get("surfaced", {})
        meaning = [w for w in (surfaced.get("meaning") or [])
                   if _tracker.successor(w, exclude=_VERBS | _STOP) is not None]
        query = meaning[0] if meaning else "moon"
    def _search():
        try:
            import urllib.request as _ur
            body = json.dumps({
                "api_key": os.environ["TAVILY_API_KEY"],
                "query": query,
                "search_depth": "basic",
                "include_images": True,
                "max_results": 3,
            }).encode()
            req2 = _ur.Request("https://api.tavily.com/search", data=body,
                               headers={"content-type": "application/json"})
            resp = json.load(_ur.urlopen(req2, timeout=8))
            images = (resp.get("images") or [])[:2]
            from dsf_ai_service.v4.image_decoder import decode_image_bytes as _dib
            import base64
            for img_url in images:
                try:
                    img_req = _ur.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                    img_bytes = _ur.urlopen(img_req, timeout=6).read()
                    _, grid, _, _ = _dib(img_bytes)
                    with _lock:
                        _ov.visual_experience(grid, query)
                    print(f"[tablet] searched '{query}' → visual cortex fed")
                except Exception:
                    pass
            # Text snippets also experience
            for r in (resp.get("results") or [])[:2]:
                snippet = (r.get("content") or r.get("snippet") or "")[:200]
                words = [w.lower().strip(".,!?") for w in snippet.split()
                         if w.isalpha() and len(w) > 3 and w.lower() not in _STOP][:8]
                if words and _ov is not None:
                    with _lock:
                        for w in words:
                            _ov.experience(w)
        except Exception as e:
            print(f"[tablet] search error: {e}")
    threading.Thread(target=_search, daemon=True).start()
    return {"ok": True, "query": query, "searching": True}


@app.get("/thought")
def thought():
    """Current autonomous thought — poll this for independence."""
    with _thought_lock:
        return dict(_last_thought)


@app.post("/surface")
def surface(req: TextReq):
    if _ov is None:
        return {"surfaced": {"identity": ["guala"], "meaning": []},
                "speech": "I am guala.", "warming": True}
    words = [w for w in req.text.lower().split() if w.isalpha() and len(w) > 2]
    with _lock:
        for w in words:
            _ov.experience(w)
        # Record succession from input words (she learns from hearing)
        if len(words) > 1:
            _tracker.record(words, weight=1.0)
        cue = None
        if words:
            try:
                profiles = [_ov._senses(w)[1] for w in words]
                if profiles:
                    cue = list(np.mean(profiles, axis=0))
            except Exception:
                pass
        surfaced = _ov.surface(cue_profile=cue)
    # Record succession from what surfaced
    all_surfaced = (surfaced.get("identity") or []) + (surfaced.get("meaning") or [])
    if len(all_surfaced) > 1:
        _tracker.record(all_surfaced, weight=0.8)
    # Episodic: bind surfaced concepts to current location + presence
    with _loc_lock:
        loc  = _location
        pres = list(_presence)
    if _episodic is not None:
        import time as _t
        for concept in all_surfaced:
            _episodic.record(concept, tick=int(_t.time()), presence=pres,
                             location=loc, affective={}, source="surface")
    speech = _compose(surfaced)
    room_desc = ROOMS.get(loc, {}).get("description", loc)
    return {"surfaced": surfaced, "speech": speech, "response": speech,
            "status": _ov.status(),
            "location": loc, "location_desc": room_desc, "presence": pres}


@app.post("/experience")
def experience(req: TextReq):
    if _ov is None:
        return {"ok": False}
    words = [w for w in req.text.lower().split() if w.isalpha() and len(w) > 2]
    if not words:
        return {"ok": True, "words": 0}
    def _grow():
        with _lock:
            for w in words:
                _ov.experience(w)
            if len(words) > 1:
                _tracker.record(words, weight=0.5)
    threading.Thread(target=_grow, daemon=True).start()
    return {"ok": True, "words": len(words)}


@app.post("/visual")
def visual(req: VisualReq):
    if _ov is None:
        return {"ok": False}
    def _process():
        try:
            from PIL import Image
            img_bytes = base64.b64decode(req.image_b64)
            img = Image.open(io.BytesIO(img_bytes)).convert("L").resize((64, 64))
            grid = np.array(img, dtype=np.float64) / 255.0
            with _lock:
                _ov.visual_experience(grid, req.concept)
                _tracker.record(["i", "see", req.concept], weight=1.5)
        except Exception:
            pass
    threading.Thread(target=_process, daemon=True).start()
    return {"ok": True}


@app.post("/catalog")
def catalog(req: CatalogReq):
    if _ov is None or not ANTHR_KEY:
        return {"ok": False}
    def _fill():
        todo = [c for c in req.concepts if c not in _ov._senses_cache]
        for i in range(0, len(todo), 20):
            with _lock:
                _ov.prefill(todo[i:i + 20])
                _ov._save_cache()
            time.sleep(1.5)
    threading.Thread(target=_fill, daemon=True).start()
    return {"ok": True, "queued": len(req.concepts)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="warning")
