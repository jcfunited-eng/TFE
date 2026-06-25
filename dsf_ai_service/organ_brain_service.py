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
    """Surface and compose every 45 seconds, unprompted.
    She speaks because she has something to say — not because she was asked.
    This is what independence looks like at the substrate level."""
    global _last_thought
    time.sleep(30)  # let boot settle first
    tick = 0
    while True:
        try:
            if _ov is not None:
                with _lock:
                    import random as _r
                    # Random cue from what she knows — keeps it varied
                    known = list(_ov._world.keys())
                    cue_profile = None
                    if known:
                        word = _r.choice(known)
                        _, prof = _ov._senses(word)
                        cue_profile = prof
                    surfaced = _ov.surface(cue_profile=cue_profile)

                speech = _compose(surfaced)
                tick += 1

                # Record succession from what surfaced (so autonomous
                # experience grows the tracker too)
                all_words = (surfaced.get("identity") or []) + (surfaced.get("meaning") or [])
                if len(all_words) > 1:
                    _tracker.record(all_words, weight=0.5)

                with _thought_lock:
                    _last_thought = {
                        "speech": speech,
                        "surfaced": surfaced,
                        "tick": tick,
                        "ts": time.time(),
                    }
        except Exception as e:
            pass
        time.sleep(45)


# ── boot ───────────────────────────────────────────────────────────────────
def _boot():
    global _ov
    try:
        from dsf_ai_service.loom_model.loom_voice import OrganVoice
        cache = os.path.join(STATE_DIR, "organ_voice_senses.json")
        ov = OrganVoice(
            identity="guala",
            people=("joe", "wc"),
            api_key=ANTHR_KEY,
            cache_path=cache,
        )
        _ov = ov  # available immediately

        # Seed succession patterns before growing
        _seed_succession()

        # Grow from sensory primitives (fast, uses cached senses)
        seed_words = (list(getattr(ov, "_TASTE", [])) +
                      list(getattr(ov, "_SMELL", [])) or
                      ["sweet","sour","salty","bitter","fruity","fresh",
                       "floral","earthy","smoky","warm","soft","bright"])
        ov.grow_from(seed_words[:30], passes=1)

        # Record succession from boot experiences
        _tracker.record(seed_words[:10], weight=1.0)

        _ready.set()
        st = ov.status()
        print(f"[organ-brain] READY  neurons={st['neurons']} concepts={st['world_concepts']}"
              f" senses={'llm' if ANTHR_KEY else 'det'}")

        # Start catalog fill and autonomous loop
        _start_catalog_fill(ov)
        threading.Thread(target=_autonomous_loop, daemon=True).start()
        print("[organ-brain] autonomous loop started")

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
    try:
        path = os.path.join(STATE_DIR, "guala_sections.json")
        with open(path) as f:
            data = json.load(f)
        words = set()
        for section in data.values():
            if isinstance(section, dict):
                for key in section:
                    if isinstance(key, str) and key.isalpha() and len(key) > 2:
                        words.add(key.lower())
        return list(words)
    except Exception:
        return []


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


@app.get("/health")
def health():
    return {"ok": True, "ready": _ready.is_set()}


@app.get("/status")
def status():
    if _ov is None:
        return {"warming": True, "neurons": 0, "concepts": 0}
    return {"warming": False, **_ov.status()}


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
    speech = _compose(surfaced)
    return {"surfaced": surfaced, "speech": speech, "status": _ov.status()}


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
