"""curriculum_scheduler.py — Guala studies on her own, on a schedule.

A background study loop that, while she is awake and not in a bulk pause, pulls the
next chunk from a children's curriculum (public-domain Project Gutenberg) and hands
it to the substrate to feed through her normal corpus path — which now also grows
her organ-brain (GL-CMD-NEXT Increment 1). This is the "she autonomously learns per
a curriculum and schedule" piece.

Design rules:
  - ADDITIVE + KILLABLE. Gated by env CURRICULUM_AUTONOMOUS (default on); a single
    flag or stop() halts it. It never touches her engine directly.
  - DECOUPLED. Network IO (fetching books) lives HERE; feeding the substrate stays
    in the caller via injected callbacks (feed_chunk / is_busy / log). No import of
    substrate_runner, so no circular import and no risk to her boot.
  - GENTLE. She reads a CHUNK (a few "pages") per cycle, not a whole book at once,
    advancing through each book then moving to the next; when the curriculum is
    finished she loops (re-reading reinforces).
  - REVERSIBLE + RESUMABLE. Progress persists to STATE_DIR/curriculum_progress.json,
    so a redeploy resumes where she left off.
  - EXCEPTION-WALLED. Any failure (network, parse, feed) is caught and logged; the
    loop survives and moves on. A study hiccup can never disturb her.
"""

import json
import os
import threading
import time
import urllib.request

_GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"

# Children's public-domain curriculum (Project Gutenberg). Order = study order.
# Every id below was fetched and title-verified as English children's literature.
DEFAULT_CURRICULUM = [
    {"book_id": 11,    "title": "Alice's Adventures in Wonderland"},
    {"book_id": 12,    "title": "Through the Looking-Glass"},
    {"book_id": 11339, "title": "Aesop's Fables"},
    {"book_id": 289,   "title": "The Wind in the Willows"},
    {"book_id": 271,   "title": "Black Beauty"},
    {"book_id": 2591,  "title": "Grimms' Fairy Tales"},
    {"book_id": 16,    "title": "Peter Pan"},
    {"book_id": 113,   "title": "The Secret Garden"},
    {"book_id": 45,    "title": "Anne of Green Gables"},
    {"book_id": 514,   "title": "Little Women"},
]

PROGRESS_FILE = "curriculum_progress.json"
CURRICULUM_FILE = "curriculum.json"  # optional STATE_DIR override of the book list


def _env_int(name, default):
    try:
        return int(os.environ.get(name, "").strip() or default)
    except Exception:
        return default


class CurriculumScheduler:
    """Drives autonomous study. The substrate injects how to feed/observe her."""

    def __init__(self, state_dir, feed_chunk, is_busy, log=None,
                 fetch_fn=None, now_fn=None, interleave_fns=None,
                 interleave_every=3):
        # feed_chunk(sentences) -> (n_fed, organ_tokens_learned); owns pause/resume.
        # is_busy() -> True if she is asleep or in a bulk pause (skip this cycle).
        # log(event, **kw) -> optional event logger (her substrate event stream).
        self.state_dir = state_dir
        self._feed_chunk = feed_chunk
        self._is_busy = is_busy
        self._log = log or (lambda *a, **k: None)
        self._fetch = fetch_fn or self._default_fetch
        self._now = now_fn or time.time

        self.enabled = (os.environ.get("CURRICULUM_AUTONOMOUS", "1").strip() != "0")
        self.chunk_size = _env_int("CURRICULUM_CHUNK_SIZE", 120)
        self.interval_sec = _env_int("CURRICULUM_INTERVAL_SEC", 180)
        self.poll_sec = _env_int("CURRICULUM_POLL_SEC", 30)

        self.curriculum = self._load_curriculum()
        self.progress = self._load_progress()
        self._book_cache = {}          # book_id -> list[str] (fetched lines)
        self._stop = threading.Event()
        self._thread = None
        self._last_status = {"state": "init"}
        # Interleaved alternative study actions (Khan/YouTube feeds, lookup grounding)
        # share the SAME reliable study windows as books — every Nth action runs one,
        # round-robin — instead of competing as starved background loops.
        self.interleave_fns = list(interleave_fns or [])  # [(name, fn), ...]
        self.interleave_every = max(2, interleave_every)
        self._tick_count = 0

    # ── curriculum + progress persistence ──────────────────────────
    def _load_curriculum(self):
        path = os.path.join(self.state_dir, CURRICULUM_FILE)
        try:
            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    return data
        except Exception as e:
            self._log("curriculum_error", where="load_curriculum", error=str(e))
        return list(DEFAULT_CURRICULUM)

    def _load_progress(self):
        path = os.path.join(self.state_dir, PROGRESS_FILE)
        try:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        except Exception as e:
            self._log("curriculum_error", where="load_progress", error=str(e))
        return {"book_index": 0, "offset": 0, "cycles": 0,
                "studied_book_ids": [], "last_ts": 0.0,
                "total_sentences": 0, "total_organ_tokens": 0}

    def _persist_progress(self):
        path = os.path.join(self.state_dir, PROGRESS_FILE)
        try:
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.progress, f, indent=1)
            os.replace(tmp, path)
        except Exception as e:
            self._log("curriculum_error", where="persist_progress", error=str(e))

    # ── fetching ───────────────────────────────────────────────────
    def _default_fetch(self, book_id):
        """Fetch + parse a Gutenberg book into sentence lines (allowlisted)."""
        from dsf_ai_service.curriculum.gutenberg_adapter import fetch_and_parse
        from dsf_ai_service.curriculum.allowlist import validate_source_url
        url = _GUTENBERG_URL.format(id=book_id)
        validate_source_url(url)
        lines, _meta = fetch_and_parse(url)
        return lines

    def _book_lines(self, book_id):
        if book_id not in self._book_cache:
            self._book_cache = {book_id: self._fetch(book_id)}  # keep only current
        return self._book_cache[book_id]

    # ── one study step ─────────────────────────────────────────────
    def study_once(self):
        """Fetch+feed the next chunk. Returns a status dict. Never raises."""
        try:
            if not self.curriculum:
                return {"state": "empty_curriculum"}
            bi = self.progress["book_index"] % len(self.curriculum)
            book = self.curriculum[bi]
            book_id, title = book["book_id"], book.get("title", str(book["book_id"]))

            try:
                lines = self._book_lines(book_id)
            except Exception as e:
                # Skip a bad/unreachable book; advance to the next one.
                self._log("curriculum_error", where="fetch",
                          book_id=book_id, error=str(e))
                self.progress["book_index"] = (bi + 1) % len(self.curriculum)
                self.progress["offset"] = 0
                self._persist_progress()
                return {"state": "fetch_failed", "book_id": book_id}

            off = self.progress["offset"]
            chunk = lines[off:off + self.chunk_size]
            if not chunk:  # book finished -> next book
                self._advance_book(bi, book_id)
                return {"state": "book_complete", "book_id": book_id, "title": title}

            n_fed, organ_learned = self._feed_chunk(chunk)

            # The injected admission owner may stop before the end of this
            # chunk when the previous sentence still has unsettled organism
            # work or a live sensory interaction owns attention.  Advance by
            # what was actually admitted so every deferred sentence remains
            # the next curriculum input instead of being silently skipped.
            self.progress["offset"] = off + n_fed
            self.progress["last_ts"] = self._now()
            self.progress["total_sentences"] = self.progress.get("total_sentences", 0) + n_fed
            self.progress["total_organ_tokens"] = (
                self.progress.get("total_organ_tokens", 0) + organ_learned)
            book_done = self.progress["offset"] >= len(lines)
            if book_done:
                self._advance_book(bi, book_id)
            else:
                self._persist_progress()

            self._log("curriculum_studied", book_id=book_id, title=title,
                      offset=self.progress["offset"], n_book_sentences=len(lines),
                      n_fed=n_fed, organ_tokens=organ_learned,
                      book_complete=book_done)
            st = {"state": "studied", "book_id": book_id, "title": title,
                  "offset": self.progress["offset"], "book_sentences": len(lines),
                  "n_fed": n_fed, "organ_tokens": organ_learned,
                  "book_complete": book_done}
            self._last_status = st
            return st
        except Exception as e:
            self._log("curriculum_error", where="study_once", error=str(e))
            return {"state": "error", "error": str(e)}

    def _advance_book(self, bi, book_id):
        if book_id not in self.progress["studied_book_ids"]:
            self.progress["studied_book_ids"].append(book_id)
        nxt = (bi + 1) % len(self.curriculum)
        if nxt == 0:
            self.progress["cycles"] = self.progress.get("cycles", 0) + 1
        self.progress["book_index"] = nxt
        self.progress["offset"] = 0
        self._book_cache = {}
        self._persist_progress()

    # ── background loop ────────────────────────────────────────────
    def _loop(self):
        self._log("curriculum_started", enabled=self.enabled,
                  n_books=len(self.curriculum), chunk_size=self.chunk_size,
                  interval_sec=self.interval_sec)
        while not self._stop.is_set():
            self._stop.wait(self.poll_sec)
            if self._stop.is_set():
                break
            try:
                if not self.enabled:
                    continue
                if self._now() - self.progress.get("last_ts", 0) < self.interval_sec:
                    continue
                if self._is_busy():
                    self._last_status = {"state": "busy_skip"}
                    continue
                self._study_action()
            except Exception as e:
                self._log("curriculum_error", where="loop", error=str(e))

    def _study_action(self):
        """One study action: usually a book chunk; every Nth, an interleaved feed
        (Khan/YouTube/lookup) so those share the same windows instead of starving."""
        self._tick_count += 1
        if self.interleave_fns and self._tick_count % self.interleave_every == 0:
            slot = (self._tick_count // self.interleave_every - 1) % len(self.interleave_fns)
            name, fn = self.interleave_fns[slot]
            try:
                st = fn()
                self.progress["last_ts"] = self._now()   # pace like a study action
                self._persist_progress()
                self._last_status = {"state": "interleaved", "feed": name, "result": st}
                return
            except Exception as e:
                self._log("curriculum_error", where="interleave", feed=name, error=str(e))
                # fall through to a book chunk on failure
        self.study_once()

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="curriculum-scheduler")
        self._thread.start()

    def stop(self, timeout=120.0):
        self._stop.set()
        if (self._thread is not None
                and self._thread is not threading.current_thread()):
            self._thread.join(timeout=float(timeout))
            if self._thread.is_alive():
                raise RuntimeError("curriculum scheduler did not stop")
            self._thread = None

    def status(self):
        bi = self.progress.get("book_index", 0)
        cur = self.curriculum[bi % len(self.curriculum)] if self.curriculum else {}
        return {
            "enabled": self.enabled,
            "n_books": len(self.curriculum),
            "current_book": cur.get("title"),
            "current_book_id": cur.get("book_id"),
            "offset": self.progress.get("offset", 0),
            "cycles": self.progress.get("cycles", 0),
            "studied_book_ids": self.progress.get("studied_book_ids", []),
            "total_sentences": self.progress.get("total_sentences", 0),
            "total_organ_tokens": self.progress.get("total_organ_tokens", 0),
            "chunk_size": self.chunk_size,
            "interval_sec": self.interval_sec,
            "last_status": self._last_status,
        }
