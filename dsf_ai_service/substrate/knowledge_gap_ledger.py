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

import copy
import json
import os
import threading
import time

from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)

LEDGER_FILE = "knowledge_gaps.json"
ENTRY_CAP = 400                    # exact live-memory and persisted entry cap
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

    def __init__(
            self, state_dir, *, physical_byte_authority=None,
            max_encoded_bytes=None):
        self.path = os.path.join(state_dir, LEDGER_FILE)
        self._lock = threading.Lock()
        self._entries = {}     # word -> dict
        self._tutor_days = {}  # "YYYY-MM-DD" -> teach count
        self._last_persist = 0.0
        self._dirty = False
        self._failure = None
        if physical_byte_authority is not None and not isinstance(
                physical_byte_authority, PhysicalByteCeilingAuthority):
            raise TypeError(
                "physical_byte_authority must be a "
                "PhysicalByteCeilingAuthority")
        if max_encoded_bytes is not None and (
                isinstance(max_encoded_bytes, bool)
                or not isinstance(max_encoded_bytes, int)
                or max_encoded_bytes <= 0):
            raise ValueError(
                "knowledge-gap ledger capacity must be a positive integer")
        if physical_byte_authority is not None and max_encoded_bytes is None:
            raise ValueError(
                "bounded knowledge-gap persistence requires an encoded-byte "
                "capacity")
        self._physical_byte_authority = physical_byte_authority
        self._max_encoded_bytes = max_encoded_bytes
        self._load()

    # ── persistence ────────────────────────────────────────────────
    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    data = json.load(f)
                self._entries = dict(data.get("entries", {}))
                self._tutor_days = dict(data.get("tutor_days", {}))
                if self._bound_entries_locked(time.time()):
                    self._dirty = True
        except Exception:
            self._entries, self._tutor_days = {}, {}

    def _bound_entries_locked(self, now):
        changed = False
        for word in [
            word
            for word, entry in self._entries.items()
            if (
                entry.get("addressed_ts")
                and now - entry["addressed_ts"] > ADDRESSED_EXPIRY_S
            )
        ]:
            del self._entries[word]
            changed = True
        if len(self._entries) > ENTRY_CAP:
            keep = sorted(
                self._entries.items(),
                key=lambda item: (
                    item[1].get("count", 0),
                    item[1].get("last_ts", item[1].get("first_ts", 0)),
                    item[0],
                ),
                reverse=True,
            )[:ENTRY_CAP]
            self._entries = dict(keep)
            changed = True
        return changed

    def _persist_locked(self, force=False):
        now = time.time()
        if not self._dirty:
            return
        self._bound_entries_locked(now)
        # Bound tutor-day history to the last 14 days seen.
        if len(self._tutor_days) > 14:
            self._tutor_days = dict(sorted(
                self._tutor_days.items())[-14:])
        encoded = json.dumps(
            {"entries": self._entries, "tutor_days": self._tutor_days},
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if (
            self._max_encoded_bytes is not None
            and len(encoded) > self._max_encoded_bytes
        ):
            raise RuntimeError(
                "knowledge-gap ledger exceeds its configured byte capacity")
        if not force and now - self._last_persist < PERSIST_DEBOUNCE_S:
            return
        authority = self._physical_byte_authority
        if authority is None:
            tmp = self.path + ".tmp"
            try:
                with open(tmp, "wb") as f:
                    f.write(encoded)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        else:
            authority.atomic_replace_bytes(
                self.path,
                encoded,
                operation="publish_knowledge_gap_ledger",
            )
        self._last_persist = now
        self._dirty = False
        self._failure = None

    # ── recording (called from engine hot paths — must stay cheap) ─
    def record(self, word, kind):
        w = _normalize(word)
        if len(w) < 2:
            return
        with self._lock:
            prior_entries = copy.deepcopy(self._entries)
            prior_dirty = self._dirty
            e = self._entries.get(w)
            if e is None:
                e = {"count": 0, "kind": kind, "first_ts": time.time(),
                     "addressed_ts": 0}
                self._entries[w] = e
            e["count"] = e.get("count", 0) + 1
            e["last_ts"] = time.time()
            self._dirty = True
            self._bound_entries_locked(e["last_ts"])
            try:
                self._persist_locked()
            except BaseException as error:
                self._entries = prior_entries
                self._dirty = prior_dirty
                self._failure = str(error)
                raise

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
                prior_entries = copy.deepcopy(self._entries)
                prior_dirty = self._dirty
                self._entries[w]["addressed_ts"] = time.time()
                self._dirty = True
                try:
                    self._persist_locked(force=True)
                except BaseException as error:
                    self._entries = prior_entries
                    self._dirty = prior_dirty
                    self._failure = str(error)
                    raise

    # ── tutor daily-cap bookkeeping ────────────────────────────────
    def _today(self):
        return time.strftime("%Y-%m-%d", time.gmtime())

    def tutor_teaches_today(self):
        with self._lock:
            return int(self._tutor_days.get(self._today(), 0))

    def record_tutor_teach(self):
        with self._lock:
            prior_days = dict(self._tutor_days)
            prior_dirty = self._dirty
            day = self._today()
            self._tutor_days[day] = int(self._tutor_days.get(day, 0)) + 1
            self._dirty = True
            try:
                self._persist_locked(force=True)
            except BaseException as error:
                self._tutor_days = prior_days
                self._dirty = prior_dirty
                self._failure = str(error)
                raise

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
                "persistence_failure": self._failure,
            }


# ── module singleton + engine-facing record helpers ────────────────
_ledger = None
_ledger_lock = threading.Lock()


def get_ledger(
        state_dir=None, *, physical_byte_authority=None,
        max_encoded_bytes=None):
    global _ledger
    if _ledger is None:
        with _ledger_lock:
            if _ledger is None:
                _ledger = GapLedger(
                    state_dir
                    or os.environ.get("STATE_DIR", "/mnt/efs/guala"),
                    physical_byte_authority=physical_byte_authority,
                    max_encoded_bytes=max_encoded_bytes,
                )
    if physical_byte_authority is not None and (
        _ledger._physical_byte_authority is not physical_byte_authority
        or _ledger._max_encoded_bytes != max_encoded_bytes
    ):
        raise RuntimeError(
            "knowledge-gap ledger was initialized outside the configured "
            "production storage authority")
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
