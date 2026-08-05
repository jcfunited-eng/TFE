# reflective_memory.py
# v4.7 — dialogue memory with lightweight reflection & summarization

from __future__ import annotations
import json, time, re
from pathlib import Path
from typing import List, Dict, Any

SAFE_LEN = 240  # cap for stored snippets

def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s[:SAFE_LEN]

def _keywords(s: str, k: int = 6) -> List[str]:
    # very small, stopword-ish filter
    stop = set("""
        the a an and or of to in for on with by from at as is are was were be been being that this
        those these it its into about over under after before more most less least very much many
        i you he she we they them us our your their my
    """.split())
    words = re.findall(r"[A-Za-z][A-Za-z\-']{1,}", s.lower())
    freq: Dict[str, int] = {}
    for w in words:
        if w in stop or len(w) < 3: continue
        freq[w] = freq.get(w, 0) + 1
    return [p[0] for p in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:k]]

class ReflectiveMemory:
    """
    Stores conversational turns and periodic reflections.
    Structure:
      self.turns = [{"t":epoch, "user":str, "bot":str, "phi":float}]
      self.reflections = [{"t":epoch, "summary":str, "open_qs":[str,...]}]
    """
    def __init__(self, path: str = "dialogue_memory.json"):
        self.path = Path(path)
        self.turns: List[Dict[str, Any]] = []
        self.reflections: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.turns = data.get("turns", [])
                self.reflections = data.get("reflections", [])
            except Exception:
                self.turns, self.reflections = [], []

    def save(self):
        data = {"turns": self.turns, "reflections": self.reflections}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_turn(self, user: str, bot: str, phi: float | None = None):
        self.turns.append({"t": time.time(), "user": _clean(user), "bot": _clean(bot), "phi": float(phi or 0.0)})

    # ----- reflection -----
    def synthesize(self, window: int = 6) -> Dict[str, Any]:
        """
        Summarize last N turns; produce open questions (knowledge gaps).
        """
        buf = self.turns[-window:] if window > 0 else self.turns[:]
        if not buf:
            return {"summary": "", "open_qs": []}

        # crude extractive summary: collect keywords from user + bot lines
        joined = " ".join([f'U:{r.get("user","")} B:{r.get("bot","")}' for r in buf])
        keys = _keywords(joined, k=10)

        # heuristics for open questions
        open_qs: List[str] = []
        if any(w in joined.lower() for w in ("confuse", "uncertain", "not sure", "why", "how")):
            open_qs.append("What point remains unclear to you from the last exchange?")
        # ask about top entity if seen but weakly elaborated
        if keys:
            open_qs.append(f"What aspect of “{keys[0]}” should we clarify or exemplify?")
        if len(keys) > 3:
            open_qs.append(f"Should we relate “{keys[1]}” and “{keys[2]}” to “{keys[3]}”?")

        summary = " • ".join(keys) if keys else "recent chat; no dominant themes"
        ref = {"t": time.time(), "summary": summary, "open_qs": open_qs}
        self.reflections.append(ref)
        return ref

    def last_user(self) -> str | None:
        for r in reversed(self.turns):
            u = r.get("user")
            if u: return u
        return None

    def last_phi(self) -> float:
        return float(self.turns[-1]["phi"]) if self.turns else 0.0
