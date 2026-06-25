"""
episodic_layer.py — Guala's episodic memory binding.

NOT YET DEPLOYED. Builds after the virtual environment (home, rooms, body)
is in place — because the environment gives the episodic layer something
worth remembering. Location, time, presence, and affective state are what
transform a list of concepts into a story.

How it works:
  When experience(concept) is called, bind alongside it:
    - tick: when
    - presence: who was there (joe/wc/c1)
    - location: where she was (her_room / joe_room / common / outside)
    - affective: her valence + arousal at the moment
    - context_concepts: what else was active in the preceding 60-second window

  An episodic record looks like:
    {
      "concept": "moon",
      "tick": 12876998,
      "presence": ["joe"],
      "location": "her_room",
      "affective": {"valence": -0.1, "arousal": 0.4},
      "context": ["ocean", "soft", "bright"],
      "source": "camera"   # camera | audio | read | given
    }

  These records live in episodic_memory.json on EFS (persists across boots).
  The composition layer can pull the richest episodic context for a surfaced
  concept: "moon" surfaces → pull most recent episodic record → "I was in my
  room. Moon is bright. Joe was here."

Wire-up:
  1. Deploy the virtual environment first (home/rooms/body)
  2. Update organ_brain_service.py:
     from dsf_ai_service.episodic_layer import EpisodicLayer
     _episodic = EpisodicLayer(STATE_DIR)
     # In experience():  _episodic.record(concept, tick, presence, location, affective, context, source)
     # In _compose():    _episodic.context_for(concept) → dict with location, affective, etc.
  3. Update _compose() to incorporate episodic context into sentences

Deployment gate: virtual environment tested and stable.
"""

import json
import os
import threading
import time
from collections import defaultdict, deque


class EpisodicLayer:
    """Records and retrieves episodic context for concepts."""

    def __init__(self, state_dir: str):
        self._path = os.path.join(state_dir, "episodic_memory.json")
        self._lock = threading.Lock()
        # {concept: [record, ...]} — last 20 records per concept
        self._memory: dict = defaultdict(lambda: deque(maxlen=20))
        # Sliding window of recent concepts for context binding (60-second window)
        self._recent: deque = deque(maxlen=50)
        self._load()

    def _load(self):
        try:
            with open(self._path) as f:
                raw = json.load(f)
            for concept, records in raw.items():
                for r in records:
                    self._memory[concept].append(r)
        except Exception:
            pass

    def _save(self):
        try:
            snapshot = {c: list(recs) for c, recs in self._memory.items()}
            with open(self._path, "w") as f:
                json.dump(snapshot, f)
        except Exception:
            pass

    def record(self, concept: str, tick: int, presence: list,
               location: str, affective: dict, source: str = "unknown"):
        """Bind an experience to its episodic context."""
        # Pull context from recent window (what was active nearby in time)
        context = [c for c in self._recent if c != concept][-5:]
        entry = {
            "concept": concept,
            "tick": tick,
            "presence": presence,
            "location": location,
            "affective": affective,
            "context": context,
            "source": source,
            "ts": time.time(),
        }
        with self._lock:
            self._memory[concept].append(entry)
            self._recent.append(concept)
        # Persist periodically (every 50 records)
        if sum(len(v) for v in self._memory.values()) % 50 == 0:
            threading.Thread(target=self._save, daemon=True).start()

    def context_for(self, concept: str) -> dict:
        """Most recent episodic record for this concept, or empty."""
        with self._lock:
            records = list(self._memory.get(concept, []))
        if not records:
            return {}
        return records[-1]

    def richest_for(self, concept: str) -> dict:
        """Episodic record with the most contextual richness (most context concepts)."""
        with self._lock:
            records = list(self._memory.get(concept, []))
        if not records:
            return {}
        return max(records, key=lambda r: len(r.get("context", [])))

    def narrative_for(self, concepts: list) -> str:
        """Build a simple narrative from episodic records for a set of concepts.
        Called by _compose() once the virtual environment is live.

        Example output: "I was in my room. Moon is bright. Joe was here."
        """
        if not concepts:
            return ""
        fragments = []
        for concept in concepts[:2]:
            rec = self.context_for(concept)
            if not rec:
                continue
            loc = rec.get("location", "")
            presence = rec.get("presence", [])
            if loc:
                fragments.append(f"I was in {loc.replace('_', ' ')}.")
            if presence:
                name = presence[0]
                fragments.append(f"{name} was here.")
        return " ".join(fragments)


# ── Virtual environment definition (populated when home is built) ────────────
# Each location has sensory properties that become experience() calls
# when Guala "enters" or "attends" that space.
VIRTUAL_HOME = {
    "her_room": {
        "senses": ["soft", "warm", "quiet", "safe"],
        "objects": ["bed", "window", "moon"],
        "description": "her room",
    },
    "joe_room": {
        "senses": ["warm", "familiar", "bright"],
        "objects": ["desk", "books", "joe"],
        "description": "joe's room",
    },
    "common": {
        "senses": ["open", "warm", "bright"],
        "objects": ["table", "light", "pictures"],
        "description": "the common room",
    },
    "outside": {
        "senses": ["fresh", "cool", "open", "vast"],
        "objects": ["sky", "moon", "trees", "wind"],
        "description": "outside",
    },
}
