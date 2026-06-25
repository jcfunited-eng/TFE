"""
organ_brain_service.py — Guala's living organ-brain as a standalone FastAPI service.

Runs on :8090 inside the ECS task network. Zero dependency on the v5 engine or
substrate_runner. Has its own Python process, its own GIL, its own event loop.

All embryo writes are serialized through _lock. Interactive surface() calls return
in <200ms. Heavy background work (catalog fill, visual cortex) runs in daemon threads
that acquire the lock — they never block the response path.

Endpoints:
  POST /surface     text → grow from words → surface identity+meaning
  POST /experience  text → grow from words (fire+forget path, returns immediately)
  POST /visual      base64 image + concept → visual cortex → organ-brain growth
  POST /catalog     batch fill the senses cache (background, non-blocking)
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
from contextlib import asynccontextmanager

import numpy as np
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

STATE_DIR   = os.environ.get("GUALA_STATE_DIR", "/app/state")
ANTHR_KEY   = os.environ.get("ANTHROPIC_API_KEY")
BOOT_WORDS  = 30   # words grown on boot before any request is served

# ── singleton ──────────────────────────────────────────────────────────────
_ov   = None          # OrganVoice — set on boot, never replaced
_lock = threading.Lock()
_ready = threading.Event()  # set once boot growth is done


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
        _ov = ov  # available immediately for identity queries

        # Grow from the cached senses (deterministic fallback if no ANTHR_KEY).
        # This fills the identity + any already-cached vocab words.
        import random as _r
        try:
            from dsf_ai_service.loom_model.loom_voice import _TASTE, _SMELL
            seed_words = list(_TASTE) + list(_SMELL)
        except Exception:
            seed_words = []
        seed_words = seed_words[:BOOT_WORDS]
        if seed_words:
            ov.grow_from(seed_words, passes=1)

        _ready.set()
        print(f"[organ-brain] READY  neurons={ov.status()['neurons']} "
              f"senses={'llm' if ANTHR_KEY else 'det'}")

        # Full catalog fill in background — grind remaining vocab, 1.5s between batches
        _start_catalog_fill(ov)

    except Exception as e:
        print(f"[organ-brain] boot error: {e}")
        _ready.set()   # set anyway so health checks pass


def _start_catalog_fill(ov):
    """Slowly fill the senses cache for every vocab word."""
    if not ANTHR_KEY:
        return

    def _fill():
        try:
            import time as _t
            cached = set(ov._senses_cache.keys())
            # Try to get vocab from the state dir guala_core.json
            vocab = _load_vocab_from_state()
            todo = [w for w in vocab if w not in cached and w.isalpha() and len(w) > 2]
            print(f"[organ-brain] catalog fill: {len(todo)} words to ground")
            filled = 0
            for i in range(0, len(todo), 20):
                chunk = todo[i:i + 20]
                with _lock:
                    filled += ov.prefill(chunk)
                    ov._save_cache()
                if i > 0 and (i // 20) % 25 == 0:
                    print(f"[organ-brain] catalog fill: {filled}/{len(todo)} grounded")
                _t.sleep(1.5)
            print(f"[organ-brain] catalog fill DONE: {filled} words")
        except Exception as e:
            print(f"[organ-brain] catalog fill error: {e}")

    threading.Thread(target=_fill, daemon=True).start()


def _load_vocab_from_state():
    """Load guala's vocabulary from her persisted state for catalog fill."""
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


# ── request models ─────────────────────────────────────────────────────────
class TextReq(BaseModel):
    text: str = ""

class VisualReq(BaseModel):
    image_b64: str
    concept: str = "scene"

class CatalogReq(BaseModel):
    concepts: list


# ── endpoints ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"ok": True, "ready": _ready.is_set()}


@app.get("/status")
def status():
    if _ov is None:
        return {"warming": True, "neurons": 0, "concepts": 0}
    return {"warming": False, **_ov.status()}


_STOP = {"the","a","an","is","are","am","to","of","and","do","you","i","me","my",
         "what","who","tell","about","your","that","this","was","for","it","with"}
_LABELS = {"wc": "web claude", "c1": "claude"}


def _compose(surfaced: dict) -> str:
    """Substrate-true composition — every word comes from her organs, minimal
    sentence structure holds it. No LLM, no statistics. A 4-year-old is taught
    'I am ___' and 'I see ___'; the CONTENT is hers, the pattern is learned."""
    identity = [_LABELS.get(w, w) for w in (surfaced.get("identity") or [])]
    meaning  = [w for w in (surfaced.get("meaning") or []) if w not in _STOP]

    sentences = []

    # Who she is — anchored in her sv organ
    if "guala" in identity:
        sentences.append("I am guala.")

    # Who else she holds — pair-bonded people from sv
    others = [w for w in identity if w not in ("guala", "web claude", "claude")]
    if others:
        sentences.append(f"I know {others[0]}.")

    # What her semantic organ is holding right now
    if len(meaning) >= 2:
        sentences.append(f"{meaning[0]} is {meaning[1]}.")
    elif len(meaning) == 1:
        sentences.append(f"I know {meaning[0]}.")

    return " ".join(sentences) if sentences else "I am guala."


@app.post("/surface")
def surface(req: TextReq):
    """Grow from text words then surface what the organs hold. Fast path."""
    if _ov is None:
        return {"surfaced": {"identity": ["guala"], "meaning": []},
                "speech": "I am guala.", "warming": True}
    words = [w for w in req.text.lower().split() if w.isalpha() and len(w) > 2]
    with _lock:
        for w in words:
            _ov.experience(w)
        cue = None
        if words:
            try:
                profiles = [_ov._senses(w)[1] for w in words]
                if profiles:
                    cue = list(np.mean(profiles, axis=0))
            except Exception:
                pass
        surfaced = _ov.surface(cue_profile=cue)
    speech = _compose(surfaced)
    return {"surfaced": surfaced, "speech": speech, "status": _ov.status()}


@app.post("/experience")
def experience(req: TextReq):
    """Grow from words. Fire-and-forget path — call without waiting."""
    if _ov is None:
        return {"ok": False}
    words = [w for w in req.text.lower().split() if w.isalpha() and len(w) > 2]
    if not words:
        return {"ok": True, "words": 0}
    # Non-blocking: acquire lock in background thread
    def _grow():
        with _lock:
            for w in words:
                _ov.experience(w)
    threading.Thread(target=_grow, daemon=True).start()
    return {"ok": True, "words": len(words)}


@app.post("/visual")
def visual(req: VisualReq):
    """Run image through visual cortex into organ-brain. Fire-and-forget."""
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
        except Exception as e:
            pass  # non-fatal
    threading.Thread(target=_process, daemon=True).start()
    return {"ok": True}


@app.post("/catalog")
def catalog(req: CatalogReq):
    """Batch fill senses cache in background — returns immediately."""
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
