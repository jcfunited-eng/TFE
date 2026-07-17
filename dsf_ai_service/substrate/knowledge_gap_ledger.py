"""knowledge_gap_ledger.py — words she reached for and didn't have.

GL-CMD-AUTOMATED-TEACHING-20260717 (Joe: "there is supposed to be automated
teaching and it should study gaps").  The substrate already PRODUCES honest
gap signals at two real reach-points, and until now nothing consumed them:

  1. Certified-composer refusals (ContinuationStopReason) — she tried to
     speak and a specific word or successor path was missing.  Recorded at
     the engine's existing fact_compose event site.
  2. Recognition misses — a freshly-measured organism recognition surprise
     at read time high enough to mean "no real record of this word."

This ledger is the consumer seam: it accumulates those words with counts,
persists across restarts, and hands the top gaps to the curriculum's
gap-study and tutor interleave slots (substrate_runner).  It is a study
TARGET list — environment bookkeeping, like the curriculum progress file.
It is NOT her memory and never feeds emission; nothing here can speak.

Design rules (same house rules as curriculum_scheduler):
  - Never raises into a caller: every public entry is exception-walled.
  - Off the engine object entirely (module singleton) — pickled saves can
    never trip on this (threading.Lock is unpicklable; lesson of the
    2026-07-08 restore incident).
  - Bounded: entry cap + addressed-entry expiry; counts, not transcripts.
  - Atomic, fsynced persistence (EFS torn-write lesson, GL 2026-07-02).
"""

from __future__ import annotations

import json
import os
import threading
import time

LEDGER_FILE = "knowledge_gaps.json"
ENTRY_CAP = 400                    # keep top-N by count at persist time
ADDRESSED_EXPIRY_S = 7 * 86400     # drop addressed entries after a week
ADDRESSED_COOLDOWN_S = 6 * 3600    # don't re-serve a word just studied
PERSIST_DEBOUNCE_S = 60.0

# Function words are never a *recognition* gap worth studying on their own
# (they only matter inside real sentences, which concordance study already
# provides around content words).  Compose refusals may still record them:
# a missing successor after "the" is a real compositional gap.
_STOPWORDS = frozenset(
    "a an the and or but if of to in on at by for with from as is am are was"
    " were be been being it its this that these those i you he she we they"
    " me him her us them my your his our their so no not do does did have"
    " has had will would can could".split())

_SURPRISE_MIN = float(os.environ.get("GAP_SURPRISE_MIN", "0.8") or 0.8)

_REFUSAL_KINDS_LAST_WORD = {
    "no_cited_occurrence", "no_successor", "successor_unknown",
    "mixed_terminal_and_successor", "ambiguous_successor_classes",
}


def _normalize(word):
    w = str(word or "").strip().lower()
    return w if w.isalpha() else "".join(c for c in w if c.isalpha())


class GapLedger:
    """Thread-safe, persisted map of gap-word -> {count, kind, timestamps}."""

    def __init__(self, state_dir):
        self.path = os.path.join(state_dir, LEDGER_FILE)
        self._lock = threading.Lock()
        self._entries = {}     # word -> dict
        self._tutor_days = {}  # "YYYY-MM-DD" -> teach count
        self._last_persist = 0.0
        self._dirty = False
        self._load()

    # ── persistence ────────────────────────────────────────────────
    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    data = json.load(f)
                self._entries = dict(data.get("entries", {}))
                self._tutor_days = dict(data.get("tutor_days", {}))
        except Exception:
            self._entries, self._tutor_days = {}, {}

    def _persist_locked(self, force=False):
        now = time.time()
        if not force and now - self._last_persist < PERSIST_DEBOUNCE_S:
            return
        if not self._dirty:
            return
        try:
            # Bound: expire old addressed entries, then keep top ENTRY_CAP.
            for w in [w for w, e in self._entries.items()
                      if e.get("addressed_ts")
                      and now - e["addressed_ts"] > ADDRESSED_EXPIRY_S]:
                del self._entries[w]
            if len(self._entries) > ENTRY_CAP:
                keep = sorted(self._entries.items(),
                              key=lambda kv: kv[1].get("count", 0),
                              reverse=True)[:ENTRY_CAP]
                self._entries = dict(keep)
            # Bound tutor-day history to the last 14 days seen.
            if len(self._tutor_days) > 14:
                self._tutor_days = dict(sorted(
                    self._tutor_days.items())[-14:])
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"entries": self._entries,
                           "tutor_days": self._tutor_days}, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
            self._last_persist = now
            self._dirty = False
        except Exception:
            pass  # a bookkeeping write must never disturb her

    # ── recording (called from engine hot paths — must stay cheap) ─
    def record(self, word, kind):
        w = _normalize(word)
        if len(w) < 2:
            return
        with self._lock:
            e = self._entries.get(w)
            if e is None:
                e = {"count": 0, "kind": kind, "first_ts": time.time(),
                     "addressed_ts": 0}
                self._entries[w] = e
            e["count"] = e.get("count", 0) + 1
            e["last_ts"] = time.time()
            self._dirty = True
            self._persist_locked()

    # ── consuming (called from the study slots) ────────────────────
    def top_gaps(self, n=8):
        """Highest-count gap words not addressed within the cooldown."""
        now = time.time()
        with self._lock:
            fresh = [(w, e) for w, e in self._entries.items()
                     if now - e.get("addressed_ts", 0) > ADDRESSED_COOLDOWN_S]
            fresh.sort(key=lambda kv: kv[1].get("count", 0), reverse=True)
            return [w for w, _ in fresh[:n]]

    def mark_addressed(self, word):
        w = _normalize(word)
        with self._lock:
            if w in self._entries:
                self._entries[w]["addressed_ts"] = time.time()
                self._dirty = True
                self._persist_locked(force=True)

    # ── tutor daily-cap bookkeeping ────────────────────────────────
    def _today(self):
        return time.strftime("%Y-%m-%d", time.gmtime())

    def tutor_teaches_today(self):
        with self._lock:
            return int(self._tutor_days.get(self._today(), 0))

    def record_tutor_teach(self):
        with self._lock:
            day = self._today()
            self._tutor_days[day] = int(self._tutor_days.get(day, 0)) + 1
            self._dirty = True
            self._persist_locked(force=True)

    def status(self):
        with self._lock:
            top = sorted(self._entries.items(),
                         key=lambda kv: kv[1].get("count", 0),
                         reverse=True)[:10]
            return {
                "n_gaps": len(self._entries),
                "top": [{"word": w, "count": e.get("count", 0),
                         "kind": e.get("kind"),
                         "addressed": bool(e.get("addressed_ts"))}
                        for w, e in top],
                "tutor_teaches_today": int(
                    self._tutor_days.get(self._today(), 0)),
            }


# ── module singleton + engine-facing record helpers ────────────────
_ledger = None
_ledger_lock = threading.Lock()


def get_ledger(state_dir=None):
    global _ledger
    if _ledger is None:
        with _ledger_lock:
            if _ledger is None:
                _ledger = GapLedger(
                    state_dir
                    or os.environ.get("STATE_DIR", "/mnt/efs/guala"))
    return _ledger


def record_compose_refusal(stop_reason, words):
    """Engine hook: a certified-composer refusal at the fact_compose site.

    input_unknown → every content word of the query is a citation gap.
    successor-class refusals → the LAST word is the boundary she could
    not continue past.  empty_query records nothing.
    """
    try:
        if not stop_reason or not words:
            return
        led = get_ledger()
        if stop_reason == "input_unknown":
            for w in list(words)[:4]:
                nw = _normalize(w)
                if nw and nw not in _STOPWORDS:
                    led.record(nw, "compose_refusal")
        elif stop_reason in _REFUSAL_KINDS_LAST_WORD:
            led.record(list(words)[-1], "compose_refusal")
    except Exception:
        pass


def record_recognition_miss(word, surprise):
    """Engine hook: freshly-measured organism recognition surprise at read.

    Only FRESH measurements reach this (the engine's every-Nth-word real
    recall), never carried-over values — so every record here is a real
    measurement, not an assumption.
    """
    try:
        if surprise is None or float(surprise) < _SURPRISE_MIN:
            return
        w = _normalize(word)
        if w and w not in _STOPWORDS:
            get_ledger().record(w, "recognition_miss")
    except Exception:
        pass
