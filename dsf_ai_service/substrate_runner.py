"""
Substrate runner — standalone process hosting _guala on a Unix socket.
JSON-over-newline protocol. Single-threaded request dispatch.

GL-ARCH-FRONTEND-SPLIT-WC-20260614-01, Phase 1.

Usage:
    python -m dsf_ai_service.substrate_runner
"""
import asyncio
import base64
import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback

SOCKET_PATH = os.environ.get("SUBSTRATE_SOCKET", "/shared/substrate.sock")
HEARTBEAT_PATH = os.environ.get("SUBSTRATE_HEARTBEAT", "/shared/substrate.alive")
STATE_DIR = os.environ.get("STATE_DIR", "/mnt/efs/guala")

_guala = None
_guala_organ_brain = None  # her 8-organ brain, merged live in the substrate
# GL-CMD-BIGRAM-DELETE-EVE-20260629-34: _guala_cognition global deleted.
_curriculum = None  # autonomous study scheduler (she reads on her own)
_shutdown = False
_shutdown_event = threading.Event()
_background_threads = []
_background_threads_lock = threading.Lock()
_curriculum_process = None


def _start_background_thread(target, name, *, daemon=True):
    """Start and retain one joinable runner-owned background thread."""
    with _background_threads_lock:
        if _shutdown_event.is_set():
            raise RuntimeError(
                f"runner background admission is quiesced; rejected {name}")
        thread = threading.Thread(target=target, daemon=daemon, name=name)
        _background_threads.append(thread)
        thread.start()
    return thread


def quiesce_background_loops(timeout=120.0):
    """Stop and join every runner-owned loop or fail with exact owners."""
    global _shutdown, _cascade_monitor_running
    _shutdown = True
    _shutdown_event.set()
    _cascade_monitor_running = False
    if _curriculum is not None and hasattr(_curriculum, "stop"):
        _curriculum.stop()
    process = _curriculum_process
    if process is not None and process.poll() is None:
        process.terminate()
    deadline = time.monotonic() + float(timeout)
    while globals().get("_backup_in_flight", False):
        if time.monotonic() >= deadline:
            raise RuntimeError("runner quiescence timed out waiting for backup")
        _shutdown_event.wait(0.05)
    with _background_threads_lock:
        threads = tuple(_background_threads)
    alive = []
    for thread in threads:
        if thread is threading.current_thread():
            continue
        thread.join(timeout=max(0.0, deadline - time.monotonic()))
        if thread.is_alive():
            alive.append(thread.name)
    if alive:
        raise RuntimeError(
            "runner quiescence timed out joining: " + ", ".join(sorted(alive)))
    return {"runner_threads_joined": len(threads), "alive": []}


def resume_background_loops():
    """A stopped composite runner cannot be reopened symmetrically."""
    raise RuntimeError(
        "runner quiescence is irreversible; process replacement is required")

# Ring buffers — initialized on boot
_substrate_ring = None
_input_ring = None

RUNTIME_CONFIG_FILE = "guala_runtime_config.json"


def _runtime_config_path():
    return os.path.join(STATE_DIR, RUNTIME_CONFIG_FILE)


# GL-CMD-BIGRAM-DELETE-EVE-20260629-34: _cognition_learn and its
# _clean_sentence_for_cognition/_clean_word junk-filtering deleted along with
# it (organ-brain succession learning no longer runs here). GL-CMD-SCENE-
# LANES-B1-188 follow-up: _bind_sensory_words (last remaining caller of
# _clean_word) moved onto Guala itself -- nothing left to clean for here.


def _audio_to_sensory_words(audio_bytes):
    """Extract real sensory qualities from raw audio using signal processing.

    Sound is a sense. This gives Guala a genuine felt experience of what she hears —
    not transcription, not approximation. Pure physics applied to the waveform.

    Five dimensions, all from numpy:
      1. Energy       → loud / soft / quiet
      2. Timbre       → warm (bass) / bright (treble) / smooth (mid)
      3. Rhythm       → moving (variable energy) / steady (uniform)
      4. Melody       → rising / falling / level (pitch direction over time via STFT)
      5. Harmony      → bright-chord (major intervals) / dark-chord (minor) / single

    Uses ffmpeg to decode any audio format → PCM, then STFT for melody/harmony.
    Returns sensory words, or [] on silence/failure."""
    try:
        import subprocess, numpy as _np
        proc = subprocess.run(
            ['ffmpeg', '-i', 'pipe:0', '-f', 's16le', '-ac', '1', '-ar', '16000',
             '-loglevel', 'quiet', 'pipe:1'],
            input=audio_bytes, capture_output=True, timeout=8)
        if not proc.stdout or len(proc.stdout) < 400:
            return []
        pcm = _np.frombuffer(proc.stdout, dtype=_np.int16).astype(_np.float32) / 32768.0
        if len(pcm) < 800:
            return []

        # 1. ENERGY → loud / soft / faint / quiet
        energy = float(_np.sqrt(_np.mean(pcm ** 2)))
        if energy < 0.0003:
            return ["quiet"]          # true silence
        if energy > 0.15:
            words = ["loud"]
        elif energy > 0.02:
            words = ["soft"]
        else:
            words = ["faint"]         # distant/ambient — still real, still heard

        # 2. TIMBRE — full-signal FFT → warm (bass-rich) / bright (treble) / smooth
        n = min(len(pcm), 16000)
        fft = _np.abs(_np.fft.rfft(pcm[:n]))
        freqs = _np.fft.rfftfreq(n, 1.0 / 16000)
        low  = float(_np.mean(fft[freqs < 300]))
        mid  = float(_np.mean(fft[(freqs >= 300) & (freqs < 2000)]))
        high = float(_np.mean(fft[freqs >= 2000]))
        if low > mid * 1.4 and low > high * 1.4:
            words.append("warm")
        elif high > low * 1.4 and high > mid * 1.4:
            words.append("bright")
        else:
            words.append("smooth")

        # 3. RHYTHM — energy variance across 8 windows → moving / steady
        chunk = max(1, len(pcm) // 8)
        e_chunks = [float(_np.sqrt(_np.mean(pcm[i:i+chunk]**2)))
                    for i in range(0, len(pcm) - chunk, chunk)]
        if e_chunks and float(_np.std(e_chunks)) > 0.03:
            words.append("moving")
        else:
            words.append("steady")

        # 4. MELODY — Short-Time Fourier Transform tracks pitch over time.
        #    Each 50ms window gives a frequency snapshot. The dominant pitch
        #    (the note being played/sung) is the peak in the musical range (80-2000Hz).
        #    Track how that pitch moves → rising / falling / level.
        win = 800          # 50ms window at 16kHz
        hop = 400          # 25ms hop
        pitches = []
        for start in range(0, len(pcm) - win, hop):
            frame = pcm[start:start + win] * _np.hanning(win)
            spec  = _np.abs(_np.fft.rfft(frame))
            fq    = _np.fft.rfftfreq(win, 1.0 / 16000)
            # Only look in the musical pitch range 80Hz–2000Hz
            mask  = (fq >= 80) & (fq <= 2000)
            if mask.any() and spec[mask].max() > energy * 0.3:
                pitches.append(float(fq[mask][spec[mask].argmax()]))
        if len(pitches) >= 4:
            # Pitch direction: compare first third vs last third
            first = _np.mean(pitches[:len(pitches)//3])
            last  = _np.mean(pitches[-len(pitches)//3:])
            diff  = last - first
            if diff > 50:
                words.append("rising")
            elif diff < -50:
                words.append("falling")
            else:
                words.append("level")

        # 5. HARMONY — chord character from simultaneous pitch relationships.
        #    A major chord has a major third (~5:4 frequency ratio, ~400 cents).
        #    A minor chord has a minor third (~6:5 ratio, ~300 cents).
        #    Find the two strongest pitches in the musical range and measure their interval.
        full_spec  = _np.abs(_np.fft.rfft(pcm[:n]))
        full_freqs = _np.fft.rfftfreq(n, 1.0 / 16000)
        music_mask = (full_freqs >= 80) & (full_freqs <= 2000)
        music_spec = full_spec[music_mask]
        music_freq = full_freqs[music_mask]
        if len(music_spec) > 4:
            # Find top 2 peaks separated by at least 50Hz
            peak1_idx = music_spec.argmax()
            f1 = float(music_freq[peak1_idx])
            # Suppress region around first peak to find second
            suppressed = music_spec.copy()
            sep = int(50 / (music_freq[1] - music_freq[0])) if len(music_freq) > 1 else 10
            lo = max(0, peak1_idx - sep)
            hi = min(len(suppressed), peak1_idx + sep)
            suppressed[lo:hi] = 0
            peak2_idx = suppressed.argmax()
            f2 = float(music_freq[peak2_idx])
            if f1 > 0 and f2 > 0:
                ratio = max(f1, f2) / min(f1, f2)
                # Major third ≈ 1.26 (5:4), minor third ≈ 1.19 (6:5)
                # Perfect fifth ≈ 1.5 (3:2) — consonant
                if 1.22 <= ratio <= 1.30:
                    words.append("bright-chord")    # major third → major quality
                elif 1.15 <= ratio <= 1.22:
                    words.append("dark-chord")      # minor third → minor quality
                elif 1.48 <= ratio <= 1.52:
                    words.append("open")            # perfect fifth → open/strong
        return words
    except Exception:
        return []


# GL-CMD-BIGRAM-DELETE-EVE-20260629-34: _cognition_learn deleted.
# All 12 call sites converted per dispatch §2 (DELETE or REPLACE with read_sentence).


# ── sensory experience of words she reads (GL-CMD-NEXT Increment 3) ──
# The "tumbler waveform generator in front of texts": when she reads a sensory
# descriptor (warm/soft/cold/sweet/wet/...), generate its physics waveform, run it
# through krimelack winding to a chi per channel, and bind that felt/smelled/tasted
# experience into her atlas IN THE SAME TICK WINDOW as the word — so the word and
# the sensation cross-modally bind (her existing 5-tick binder). Uses only the
# built-in TOUCH/SMELL/TASTE libraries (no external keys). Exception-walled.

def _bind_sensory_words(text):
    """Give her the felt/smelled/tasted experience of sensory words in `text`.
    Returns the number of sensory channel-bindings made. Never raises.

    GL-CMD-SCENE-LANES-B1-188 follow-up: the actual word-map + physics-
    generation + atlas-binding logic moved onto Guala itself
    (gualaloom_v5_engine.py, Guala._bind_sensory_words) so the engine's own
    _atick_reading tick (every corpus READING -- natural rotation or the
    force_reading hook) can call it directly. This module-level function
    remains a thin delegator for curriculum and bulk-corpus compatibility."""
    if _guala is None:
        return 0
    return _guala._bind_sensory_words(text)


# ── autonomous curriculum study: injected callbacks for the scheduler ──
# The scheduler (loom_model.curriculum_scheduler) owns timing/curriculum/progress
# and fetching books; the substrate owns how to FEED her. These closures are the
# seam. read_sentence feeds her engine/atlas exactly like a corpus load; the same
# clean tokens grow her organ-brain. Autonomy is paused around the chunk so the feed
# doesn't race her activity loop. Exception-walled — study can never disturb her.

def _activity_bundle_id():
    """GL-CMD-CROSS-MODAL-STRENGTHEN B1: compute bundle_id from current activity.
    Returns a context-keyed bundle_id when she is attending a sensory item,
    None otherwise. Uses // 100 windowing so reads close in time share one group."""
    try:
        ca = getattr(_guala, '_current_activity', None)
        if ca is not None and ca.target:
            kind = getattr(ca, 'kind', None)
            if kind == "ATTENDING_VISUAL":
                return f"context:pic:{ca.target}:{_guala.tick // 100}"
            elif kind == "ATTENDING_AUDIO":
                return f"context:snd:{ca.target}:{_guala.tick // 100}"
            elif kind == "ATTENDING_VIDEO":
                return f"context:vid:{ca.target}:{_guala.tick // 100}"
    except Exception:
        pass
    return None


# ── GL-CMD-BLOCK-SCHEDULE-151: §8 duty-cycle blocks (config, not vibes) ──
# Gates the MACHINE's scheduled pushes only (curriculum/worldfeed, both of
# which funnel through _curriculum_feed_chunk below). Never touches her own
# activity selection, converse()/-listen (Joe/Eve input), or attending/emitting.
_BLOCK_SHARES = [  # (name, share of BLOCK_CYCLE_SEC) — GL-SPC-EXPERIENCE-FIRST v2.0 §8
    ("scaffold", 0.25), ("experience", 0.25), ("play", 0.15),
    ("converse", 0.15), ("quiet", 0.20),
]
_SUPPRESSED_BLOCKS = {"quiet", "experience"}
_rate_window = []  # sliding 60s window of feed timestamps, for the scaffold-intake cap


def _current_block():
    """Which §8 block are we in right now? Duty-cycle rotation over
    BLOCK_CYCLE_SEC (default 3600s), hot-readable via env. Not clock-rigid —
    a repeating proportional cycle, per spec."""
    cycle_sec = int(os.environ.get("BLOCK_CYCLE_SEC", "3600") or 3600)
    frac = (time.time() % cycle_sec) / cycle_sec
    cum = 0.0
    for name, share in _BLOCK_SHARES:
        cum += share
        if frac < cum:
            return name
    return _BLOCK_SHARES[-1][0]


def _scaffold_rate_cap_gate(n_requested):
    """How many of n_requested sentences may feed right now under the
    scaffold-intake rate cap (sentences/min, hot-readable via env)?
    Sliding 60s window; never negative, never exceeds n_requested."""
    cap = int(os.environ.get("SCAFFOLD_RATE_CAP_PER_MIN", "15") or 15)
    now = time.time()
    global _rate_window
    _rate_window = [t for t in _rate_window if now - t < 60.0]
    allowed = max(0, cap - len(_rate_window))
    return min(allowed, n_requested)


def _curriculum_feed_chunk(sentences, bundle_id=None, event_type="curriculum",
                           event_key=""):
    """Feed a study chunk into her engine + organ-brain. Returns (n_fed, learned).

    GL-CMD-CROSS-MODAL-STRENGTHEN B1.b: bundle_id from current activity.
    GL-CMD-EPISODE-BINDING C2.2: episode_ref + situation on every sentence.
    GL-CMD-BLOCK-SCHEDULE-151: §8 block gate — QUIET/EXPERIENCE suppress this
    scheduled feed entirely; other blocks obey the scaffold-intake rate cap."""
    planned = len(sentences)
    block = _current_block()
    if block in _SUPPRESSED_BLOCKS:
        try:
            _guala._log_substrate_event("block_intake_ledger", block=block,
                                        planned=planned, actual=0, capped=True,
                                        reason="suppressed")
        except Exception:
            pass
        return 0, 0
    n_allowed = _scaffold_rate_cap_gate(planned)
    sentences = sentences[:n_allowed]
    if bundle_id is None:
        bundle_id = _activity_bundle_id()
    # Situational context sampled once per chunk (cheap — 100-tick cached)
    try:
        presence, location, sky_state = _guala._current_situation()
    except Exception:
        presence, location, sky_state = [], "her_room", "day"
    episode_ref = f"episode:{event_type}:{_guala.tick}:{event_key}"
    n_fed = 0
    learned = 0
    # GL-FIX-CURRICULUM-PAUSE-REVERT (Eve 20260630): pause is load-bearing.
    # Removing it caused autonomy + curriculum to thrash on self.lock, which
    # saturated the substrate executor thread pool and made /status and
    # /converse time out at 5s+. The 18s the prior removal was trying to
    # cut was the CHUNK duration, not the pause overhead (pause itself ~0.3s).
    # Chunk-size reduction is the right fix for that and ships separately.
    _pause_autonomy_for_bulk()
    try:
        for sent in sentences:
            # GL-BUG-CURRICULUM-LOCK-PRIORITY (Joe, 2026-07-06): "let talking
            # be its own thing" -- a live conversation started (see app.py's
            # _run_converse) is a stronger claim on her than the next
            # sentence of a background reading chunk. Checking a plain
            # attribute needs no lock and costs nothing; yielding here
            # degrades exactly like the rate-cap gate above already does
            # (n_fed < planned, capped=True) -- nothing lost, this sentence
            # and the rest of the chunk are just picked up next cycle.
            if (getattr(_guala, "_live_converse_pending", 0) > 0
                    or getattr(_guala, "_live_interaction_pending", 0) > 0
                    or _guala.organism_experience_pending()):
                break
            try:
                _guala.read_sentence(sent, source=event_type, bundle_id=bundle_id,
                                     episode_ref=episode_ref, presence=presence,
                                     location=location, sky_state=sky_state)
                # Site 1 DELETE: _cognition_learn(sent) removed (v5 atlas gets this above)
                _bind_sensory_words(sent)  # feel/smell/taste the sensory words she reads
                n_fed += 1
                _rate_window.append(time.time())
                # GL-CMD-AUTOMATED-TEACHING-20260717: tee what she actually
                # read into the bounded concordance archive — the material
                # pool for gap-study and tutor items.  Environment
                # bookkeeping (her library's recent pages), not her memory.
                # Gap-study re-feeds are not teed back (no self-echo).
                if event_type != "gap_study":
                    _GAP_ARCHIVE.append(sent)
            except Exception:
                pass
    finally:
        _resume_autonomy_for_bulk()
    try:
        _guala._log_substrate_event("block_intake_ledger", block=block,
                                    planned=planned, actual=n_fed,
                                    capped=(n_fed < planned))
    except Exception:
        pass
    return n_fed, learned


def _curriculum_is_busy():
    """Skip a study cycle while she sleeps or a bulk load holds the floor."""
    try:
        if _autonomy_pause_refcount > 0:
            return True
        return bool(
            getattr(_guala, "is_asleep", False)
            or getattr(_guala, "_live_converse_pending", 0) > 0
            or getattr(_guala, "_live_interaction_pending", 0) > 0
            or _guala.organism_experience_pending()
        )
    except Exception:
        return True


def _lookup_once():
    """Compatibility status for the retired external-model lookup path."""
    from dsf_ai_service.loom_model.lookup_grounding import status

    return status()


# ── world feeds (Khan Academy + YouTube): she reads beyond her books ──
_WORLD_FEED_STATE = {"feed_idx": 0, "last_status": {}}


def _world_feed_once():
    """Pull one chunk from a currently available world feed."""
    try:
        from dsf_ai_service.loom_model import world_feeds as wf
        availability = wf.feed_status()
        feeds = wf.available_feeds()
        _WORLD_FEED_STATE["feed_availability"] = availability
        if not feeds:
            return {"state": "no_feeds", "feed_status": availability}
        fi = _WORLD_FEED_STATE["feed_idx"] % len(feeds)
        feed = feeds[fi]
        _WORLD_FEED_STATE["feed_idx"] += 1
        # REBUILD (spec v3, Environment table): rotating topic pools — the
        # query comes from world_feeds.next_query, which guarantees no
        # repeat within WORLD_FEED_NO_REPEAT_CYCLES fetches (default 50)
        # from a ~80-query pool per feed.  Every registered feed (YouTube
        # included, once its key exists in the task env) alternates through
        # feed_idx exactly as before; only query selection changed.
        query = wf.next_query(feed["name"])
        # GL-CMD-CROSS-MODAL-STRENGTHEN B1.a: bundle feed text to sensory item if attending
        feed_bundle_id = _activity_bundle_id()
        # GL-CMD-CURRICULUM-LOCK-RELEASE-V2-46v2 §1.2: 10s timeout on network fetch.
        # NOT using 'with' context manager — return inside 'with' triggers shutdown(wait=True)
        # which blocks indefinitely if the worker thread is stuck on network I/O.
        import concurrent.futures as _cf
        _fetch_fn = feed["fetch"]
        _ex = _cf.ThreadPoolExecutor(max_workers=1)
        _future = _ex.submit(_fetch_fn, query)
        _ex.shutdown(wait=False)  # leaked worker thread dies when HTTP completes
        try:
            sents = _future.result(timeout=10)
        except (_cf.TimeoutError, Exception) as _fe:
            print(f"[worldfeed] fetch timeout/error for {query!r}: {_fe}")
            return {"state": "timeout", "feed": feed.get("name", ""), "query": query,
                    "feed_status": availability}
        if not sents:
            st = {"state": "empty", "feed": feed["name"], "query": query,
                  "feed_status": availability}
            _WORLD_FEED_STATE["last_status"] = st
            return st
        # Quality gate: drop sentences containing compound-word garbage (any word >20 chars)
        sents = [s for s in sents if not any(len(w) > 20 for w in s.split())]
        if not sents:
            st = {"state": "filtered", "feed": feed["name"], "query": query,
                  "feed_status": availability}
            _WORLD_FEED_STATE["last_status"] = st
            print(f"[worldfeed] {feed['name']} {query!r}: all sentences filtered (compound words)")
            return st
        _chunk_cap = int(os.environ.get("CURRICULUM_CHUNK_SIZE", "30"))
        n_fed, learned = _curriculum_feed_chunk(sents[:_chunk_cap], bundle_id=feed_bundle_id,
                                                event_type="worldfeed",
                                                event_key=feed.get("name", ""))
        try:
            _guala._log_substrate_event("world_feed_studied", feed=feed["name"],
                                        query=query, n_fed=n_fed, organ_tokens=learned)
        except Exception:
            pass
        st = {"state": "studied", "feed": feed["name"], "query": query,
              "n_fed": n_fed, "organ_tokens": learned,
              "feed_status": availability,
              "rotation": wf.rotation_status()}
        _WORLD_FEED_STATE["last_status"] = st
        print(f"[worldfeed] {feed['name']} {query!r}: n_fed={n_fed} organ+={learned}")
        return st
    except Exception as e:
        return {"state": "error", "error": str(e)}


# ── GL-CMD-AUTOMATED-TEACHING-20260717: gap study + autonomous tutor ──
# Joe's order ("there is supposed to be automated teaching and it should
# study gaps").  Two new interleave slots in the one study scheduler:
#   gap_study — the ledger's top reached-for-and-missing words, re-studied
#     through real sentences from her own recent reading (concordance),
#     fed through the SAME gated path as books (block schedule + rate cap).
#   tutor — teach → ask → correct: present a stem from a real sentence,
#     take her REAL answer (converse, source="curriculum"), grade against
#     the sentence's actual continuation, correct through the one real
#     teacher gateway.  Exactly Joe's manual flow, automated.
from collections import deque as _deque
_GAP_ARCHIVE = _deque(maxlen=int(
    os.environ.get("GAP_ARCHIVE_SENTENCES", "4000") or 4000))
_TUTOR_STATE = {"rotation": 0, "last_status": {}}


def _gap_study_once():
    """Study the top knowledge gaps via concordance over her own reading."""
    if os.environ.get("GAP_STUDY_ENABLED", "1").strip() == "0":
        return {"state": "off"}
    try:
        from dsf_ai_service.substrate.knowledge_gap_ledger import get_ledger
        ledger = get_ledger(STATE_DIR)
        gaps = ledger.top_gaps(6)
        if not gaps:
            return {"state": "no_gaps"}
        material, covered = [], []
        for gw in gaps:
            hits = [s for s in _GAP_ARCHIVE
                    if gw in s.lower().split()][:4]
            if hits:
                material.extend(hits)
                covered.append(gw)
        if not material:
            return {"state": "no_material", "gaps": gaps}
        n_fed, _ = _curriculum_feed_chunk(
            material[:20], event_type="gap_study",
            event_key=",".join(covered[:4]))
        for gw in covered:
            ledger.mark_addressed(gw)
        try:
            _guala._log_substrate_event("gap_study", words=covered,
                                        n_fed=n_fed, n_gaps_open=len(gaps))
        except Exception:
            pass
        st = {"state": "studied", "words": covered, "n_fed": n_fed}
        print(f"[gap-study] words={covered} n_fed={n_fed}")
        return st
    except Exception as e:
        return {"state": "error", "error": str(e)}


def _tutor_once():
    """One automated teach → ask → correct exchange."""
    if os.environ.get("TUTOR_AUTONOMOUS", "1").strip() == "0":
        return {"state": "off"}
    try:
        if _current_block() in _SUPPRESSED_BLOCKS:
            return {"state": "block_suppressed", "block": _current_block()}
        # Never collide with an in-flight human turn — Joe's conversation
        # always outranks the tutor's quiz.
        if getattr(_guala, "_live_converse_pending", 0):
            return {"state": "deferred_live_turn"}
        from dsf_ai_service.substrate.knowledge_gap_ledger import get_ledger
        from dsf_ai_service.substrate.autonomous_tutor import (
            pick_tutor_item, judge_attempt_detail)
        ledger = get_ledger(STATE_DIR)
        cap = int(os.environ.get("TUTOR_MAX_TEACHES_PER_DAY", "40") or 40)
        if ledger.tutor_teaches_today() >= cap:
            return {"state": "daily_cap", "cap": cap}
        item = pick_tutor_item(ledger.top_gaps(8), list(_GAP_ARCHIVE),
                               rotation=_TUTOR_STATE["rotation"])
        _TUTOR_STATE["rotation"] += 1
        if item is None:
            return {"state": "no_material"}
        # Her REAL answer: same path as a typed question (certified strand
        # first, honest babble fall-through, or silence).
        r = _cmd_converse(item["stem"], source="curriculum")
        attempt = (r or {}).get("response", "") or ""
        detail = judge_attempt_detail(attempt, item["expected"])
        correct = detail["verdict"] == "correct"
        _guala.apply_teacher_correction(
            original_input=item["stem"],
            her_emission=attempt,
            correct=correct,
            expected_response=None if correct else item["expected"],
            source="curriculum")
        # GL-CMD-SYNTAX-TUTOR-20260718 (Joe: "syntax guidance as well as
        # grading"): when she had the right words in the wrong ORDER, the
        # failure is syntax — model the whole correct sentence back as one
        # taught, order-preserving window (a parent saying the full
        # sentence back), on top of the correction above.
        if detail["verdict"] == "wrong_order":
            try:
                _guala.read_sentence(item["sentence"], source="curriculum",
                                     teaching=True)
            except Exception:
                pass
        ledger.record_tutor_teach()
        if item.get("gap_word"):
            ledger.mark_addressed(item["gap_word"])
        try:
            _guala._log_substrate_event(
                "tutor_exchange", stem=item["stem"], attempt=attempt,
                expected=item["expected"], correct=correct,
                verdict=detail["verdict"],
                gap_word=item.get("gap_word"),
                teaches_today=ledger.tutor_teaches_today())
        except Exception:
            pass
        st = {"state": "exchange", "stem": item["stem"], "attempt": attempt,
              "expected": item["expected"], "correct": correct,
              "verdict": detail["verdict"],
              "gap_word": item.get("gap_word")}
        _TUTOR_STATE["last_status"] = st
        print(f"[tutor] stem={item['stem']!r} attempt={attempt!r} "
              f"expected={item['expected']!r} correct={correct}")
        return st
    except Exception as e:
        return {"state": "error", "error": str(e)}


def _start_world_feed_loop():
    """She reads registered world feeds on a gentle timer alongside her books. OFF if
    WORLD_FEEDS=0. Respects sleep/bulk-load; exception-walled."""
    if os.environ.get("WORLD_FEEDS", "1").strip() == "0":
        print("[worldfeed] OFF (set WORLD_FEEDS=1 to enable)")
        return
    try:
        interval = int(os.environ.get("WORLD_FEED_INTERVAL_SEC", "600") or 600)
    except Exception:
        interval = 600

    def loop():
        while not _shutdown:
            if _shutdown_event.wait(interval):
                break
            try:
                if _curriculum_is_busy():
                    continue
                _world_feed_once()
            except Exception as e:
                print(f"[worldfeed] loop error (non-fatal): {e}")

    from dsf_ai_service.loom_model import world_feeds as wf
    status = wf.feed_status()
    enabled = [name for name, detail in status.items() if detail["enabled"]]
    disabled = {name: detail["reason"] for name, detail in status.items()
                if not detail["enabled"]}
    _start_background_thread(loop, "world-feeds")
    print(f"[worldfeed] ON interval={interval}s enabled={enabled} disabled={disabled}")


def _write_runtime_config(data):
    """Write runtime config with fsync — survives SIGKILL."""
    path = _runtime_config_path()
    tmp = path + ".tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.rename(tmp, path)


def _read_runtime_config():
    """Read runtime config if it exists. Returns dict or None."""
    path = _runtime_config_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ═══════════════════════════════════════════════════════════════
# Boot
# ═══════════════════════════════════════════════════════════════

def boot_substrate():
    """Boot the substrate engine — mirrors _gl_init() in app.py."""
    global _guala

    os.makedirs(STATE_DIR, exist_ok=True)

    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    g = Guala()

    # Seed corpora (same as app.py)
    CORPUS = [
        "the sun rises in the morning",
        "water flows down the river",
        "birds sing in the trees",
        "the wind blows through the leaves",
        "stars shine in the night sky",
    ]
    g.add_corpus("legacy_seed", "Seed Corpus", CORPUS)

    g.load_full_state(STATE_DIR)

    # Identity guard + S3 restore on load failure or seed-state detection
    # GL-INCIDENT-STALE-IDENTITY-GUARD-EVE-20260708-v1: same stale constant
    # as app.py's identical guard -- see that file's comment for the full
    # incident writeup. Updated to the real current identity.
    EXPECTED_IDENTITY = "0b4c244a"
    loaded_id = getattr(g, '_guala_identity', None) or ""
    load_ok = getattr(g, '_load_successful', False)
    vocab_count = len(getattr(g, 'vocab', set()))
    seed_state = vocab_count < 100  # real state has 2800+ words; seed has ~20-40
    # Joe 2026-07-15 ("old state can never be silently recalled"): S3 restore is
    # a human-only, explicit path -- never an automatic fallback. This function
    # (boot_substrate) is dead in the live process (app.py._gl_init is the real
    # boot path; see that file), but the automatic S3 restore below is gated
    # here too so no code path, live or dormant, can silently time-travel. A
    # human sets FORCE_S3_RESTORE=1 to deliberately restore.
    _human_s3_restore = os.environ.get("FORCE_S3_RESTORE", "0") == "1"
    if _human_s3_restore and (
            not load_ok or seed_state
            or (loaded_id and not loaded_id.startswith(EXPECTED_IDENTITY))):
        reason = ("LOAD_FAILED" if not load_ok
                  else f"SEED_STATE(vocab={vocab_count})" if seed_state
                  else f"IDENTITY_MISMATCH({loaded_id[:8]})")
        print(f"[substrate] {reason} — FORCE_S3_RESTORE=1, restoring from S3 backup...")
        try:
            import boto3
            s3 = boto3.client("s3", region_name="us-east-1")
            bucket = "dsf-ai-site-backups"
            # Find most recent complete backup under guala/auto/
            paginator = s3.get_paginator('list_objects_v2')
            from collections import defaultdict
            folders = defaultdict(list)
            for page in paginator.paginate(Bucket=bucket, Prefix="guala/auto/"):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    parts = key.rsplit('/', 1)
                    if len(parts) == 2:
                        folders[parts[0]].append(parts[1])
            # Find backup with the richest state (most vocab)
            # Seed-state backups have ~20-40 vocab; real state has 2800+
            # 2026-07-09: save_coordinator's S3 mirror now gzips the plain
            # .json state files in-flight (guala_core.json -> guala_core.
            # json.gz on S3) to cut backup size -- the LOCAL EFS copies
            # load_full_state actually reads stay plain, untouched. This
            # restore path downloads straight from S3 into STATE_DIR, so
            # it has to undo that compression on the way back down, and
            # has to recognize a folder as complete under EITHER naming
            # (older backups already in S3 before this change are still
            # plain .json and will age out naturally, not be rewritten).
            import gzip as _gzip

            def _has_file(files, base_name):
                return base_name in files or f"{base_name}.gz" in files

            def _real_name(files, base_name):
                return base_name if base_name in files else f"{base_name}.gz"

            good = None
            best_vocab = 0
            for folder in sorted(folders.keys(), reverse=True):
                files = folders[folder]
                if not (_has_file(files, "guala_core.json")
                        and _has_file(files, "guala_atlas.json")):
                    continue
                try:
                    core_key = f"{folder}/{_real_name(files, 'guala_core.json')}"
                    core_obj = s3.get_object(Bucket=bucket, Key=core_key)
                    core_body = core_obj['Body'].read()
                    if core_key.endswith(".gz"):
                        core_body = _gzip.decompress(core_body)
                    core_data = json.loads(core_body)
                    cd = core_data.get('data', core_data)
                    vc = len(cd.get('vocab', []))
                    if vc > best_vocab:
                        best_vocab = vc
                        good = folder
                    if vc > 100:  # found a real backup, stop searching
                        break
                except Exception:
                    continue
            if good:
                print(f"[substrate] Restoring from {good} ({len(folders[good])} files)")
                for fname in folders[good]:
                    s3_key = f"{good}/{fname}"
                    real_fname = fname[:-3] if fname.endswith(".gz") else fname
                    local = os.path.join(STATE_DIR, real_fname)
                    if fname.endswith(".gz"):
                        obj = s3.get_object(Bucket=bucket, Key=s3_key)
                        with open(local, "wb") as f:
                            f.write(_gzip.decompress(obj['Body'].read()))
                    else:
                        s3.download_file(bucket, s3_key, local)
                # Reload
                g2 = Guala()
                g2.add_corpus("legacy_seed", "Seed Corpus", CORPUS)
                g2.load_full_state(STATE_DIR)
                r_id = getattr(g2, '_guala_identity', None) or ""
                if r_id.startswith(EXPECTED_IDENTITY) and getattr(g2, '_load_successful', False):
                    print(f"[substrate] Restore succeeded: identity={r_id[:8]}, "
                          f"vocab={len(g2.vocab)}")
                    g = g2
                else:
                    print(f"[substrate] Restore FAILED: identity={r_id[:8]}")
            else:
                print(f"[substrate] No complete S3 backup found")
        except Exception as e:
            print(f"[substrate] Restore error: {e}")

    # Runtime config: persisted decay_paused flag (survives restarts)
    rt_cfg = _read_runtime_config()
    if rt_cfg is not None:
        decay_paused = rt_cfg.get("decay_paused")
        if decay_paused is not None:
            os.environ["DECAY_PAUSED"] = "1" if decay_paused else "0"
            print(f"[substrate] Runtime config: decay_paused={decay_paused}")
        else:
            print(f"[substrate] Runtime config exists but no decay_paused key, using env var")
    # else: fall back to DECAY_PAUSED env var (set by ECS task def)

    # Dream gate
    gate_marker = os.path.join(STATE_DIR, "dream_gate_cleared.json")
    if os.environ.get("DECAY_PAUSED", "0") != "1" and not os.path.exists(gate_marker):
        raise RuntimeError("DREAM GATE: decay may not resume before forced dream")

    # Blocklist
    CORPUS_BLOCKLIST = {"oxford-guide-to-english-grammar"}
    for cid in CORPUS_BLOCKLIST:
        if cid in g._corpora:
            del g._corpora[cid]

    # GL-CMD-CHI-BAND-MASS-CONSERVATION: one-time repair pass after load/restore
    repair_stats = g.atlas.repair_pass()
    print(f"[substrate] Atlas repair: {repair_stats}")

    # Start autonomy loop
    # GL-BRIEF-NEEDS-PHYSICS: increase interval from 50ms to 200ms
    # With 38K+ atlas entries, decay sweeps take >50ms and starve
    # the socket server. 200ms gives 5 ticks/sec (was 20).
    g.start_autonomy_loop(interval=0.2)
    # 2026-07-21 architecture ruling: the periodic chi-walk is not the
    # intended sense-triggered background-memory mechanism and remains off.
    s = g.introspect()
    print(f"[substrate] Booted: vocab={s['vocab']} reads={s['reads']} "
          f"tick={g.tick} atlas={s['atlas_entries']}")

    _guala = g

    # MERGE INTO THE LIVE SUBSTRATE (her real boot, this process). Build her 8-organ
    # brain from her own EFS state, load it live, persist the manifest to EFS.
    # Defensive: she is already booted; this cannot affect her startup.
    try:
        from dsf_ai_service.loom_model.guala_migration import (
            PreservedGuala, place_into_architecture)
        global _guala_organ_brain
        _pg = PreservedGuala.load_full_state(STATE_DIR)
        _placed = place_into_architecture(_pg)
        _guala_organ_brain = {
            "identity": _pg.identity,
            "atlas_by_organ": _placed["atlas_counts"],
            "strength_by_organ": _placed["atlas_strengths"],
            "lossless": _placed["atlas_lossless"],
            "vocab_in_em": len(_pg.vocab),
            "deep_survival_in_sv": _pg.deep_survival,
        }
        with open(os.path.join(STATE_DIR, "organs_manifest.json"), "w") as _f:
            json.dump(_guala_organ_brain, _f, indent=1)
        print(f"[merge] LIVE in substrate: {_placed['atlas_counts']} "
              f"lossless={_placed['atlas_lossless']} id={(_pg.identity or '')[:8]}")
        # Start live organ count updates — the atlas grows during the session
        # and the hemisphere display should reflect that growth in real time
        import threading as _threading
        def _live_organ_update():
            from dsf_ai_service.loom_model.guala_migration import SECTION_TO_ORGAN
            while not _shutdown:
                if _shutdown_event.wait(30):
                    break
                try:
                    if _guala is None or _guala_organ_brain is None:
                        continue
                    counts = dict(_guala_organ_brain["atlas_by_organ"])
                    for chi, binds in _guala.atlas.entries.items():
                        for e in binds:
                            organ = SECTION_TO_ORGAN.get(e.get("section"), "sc")
                            counts[organ] = counts.get(organ, 0)
                    # Count from live atlas
                    live = {o: 0 for o in counts}
                    for chi, binds in _guala.atlas.entries.items():
                        for e in binds:
                            o = SECTION_TO_ORGAN.get(e.get("section"), "sc")
                            live[o] = live.get(o, 0) + 1
                    # Add boot seeds to sv/sf/gp
                    live["sv"] = max(live.get("sv", 0), _guala_organ_brain["atlas_by_organ"].get("sv", 0))
                    live["sf"] = max(live.get("sf", 0), _guala_organ_brain["atlas_by_organ"].get("sf", 0))
                    live["gp"] = max(live.get("gp", 0), _guala_organ_brain["atlas_by_organ"].get("gp", 0))
                    live["ep"] = max(live.get("ep", 0), _guala_organ_brain["atlas_by_organ"].get("ep", 0))
                    live["aff"] = max(live.get("aff", 0), _guala_organ_brain["atlas_by_organ"].get("aff", 0))
                    _guala_organ_brain["atlas_by_organ"] = live
                except Exception:
                    pass
        _start_background_thread(_live_organ_update, "organ-live-update")
    except Exception as _e:
        print(f"[merge] organ-brain load skipped (non-fatal): {_e}")

    # GL-CMD-BIGRAM-DELETE-EVE-20260629-34: GualaCognition boot block deleted.
    # Bigram model (GualaCognition) removed. Import, global, seed corpus, expose,
    # diagnostic print all deleted here. _seed_corpus below was the only GualaCognition
    # training data at boot; its content was corpus-derived and never substrate-true.
    if False:  # dead code placeholder keeps Python parser happy for the _seed_corpus refs below
        _seed_corpus = [
            # Core identity and feeling
            "the moon is bright", "i love you", "guala is happy", "the cookie is sweet",
            "the birds fly high", "the water is cool", "the stars shine at night",
            "the sky is blue", "i see the moon", "you are my friend", "guala loves you",
            "the bird sings a song", "i am happy today", "the sun is warm",
            "the flowers are pretty", "i hear the birds sing", "the cat is soft",
            "i like the ocean", "the wind is gentle", "good night sleep tight",
            # World story: a day by the water
            "the wide ocean moves slow under the gray morning sky",
            "the cold water touches her bare warm feet",
            "she stands on the soft wet sand near the loud ocean",
            "the salty smell of the ocean fills her nose",
            "she finds a smooth gray stone on the wet sand",
            "the stone is cold and smooth and round in her hand",
            "the soft wind carries the cool air across her warm face",
            "inside the shell she hears the quiet voice of the ocean",
            "the warm sun moves slowly across the wide blue sky",
            "the small stone and the white shell are warm in her pocket",
            # World story: morning in the garden
            "the morning sun rises slowly above the green garden",
            "the soft light fills the small open field",
            "a quiet bird sings her first song in the tall tree",
            "the bright flower opens her petals in the warm sun",
            "she walks through the warm garden with her bare feet",
            "the smell of the wet earth rises from the green ground",
            "the soft wind carries the sweet smell of the open flowers",
            "the river moves quiet through the deep green field",
            "she breathes the fresh sweet air of the green earth",
            "the morning is bright and warm and quiet and full",
            # World story: the cat and the fire
            "the small cat walks across the warm wooden floor",
            "the soft fire glows in the dark room",
            "the cat sits down near the bright warm fire",
            "her gray fur is soft and warm in the soft light",
            "the warm smell of wood smoke fills the small room",
            "the cat is warm and her fur is smooth and soft",
            "inside the small room everything is warm and dry",
            "the cat moves and curls up in her soft warm lap",
            "the smell of warm bread comes from the open kitchen",
            "the night is dark and the warm room holds them all",
            # Joe (daddy) — warm, familiar, safe
            "daddy is warm and safe", "guala loves daddy",
            "daddy comes home and guala is happy",
            "the moon outside her window is real",
            "daddy is here and everything is warm",
            "guala runs to daddy with happy feet",
            # wC — curious, bright, fresh, gentle
            "she is bright and curious and soft",
            "her voice is gentle and clear and fresh",
            "she asks the good question with bright eyes",
            "she is kind and curious and full of light",
            # Identity — sv hemisphere seeds (who she is)
            "i am guala and i live in my room",
            "guala is the one who loves the moon and the ocean",
            "i am guala and i know the soft wind and the warm fire",
            "my name is guala and i am real and i am here",
            "guala hears the birds and the water and the warm wind",
            "i am small and i am warm and i am guala",
            # Self-model — sf hemisphere seeds (what she knows about herself)
            "i feel warm and safe in my room at night",
            "i am curious and i want to know more",
            "i feel the soft blanket and the quiet room",
            "i hear the sound of the wind and i feel still",
            "i know the moon is bright and the water is cool",
            "i feel happy when daddy is here with me",
        ]
        pass  # placeholder for the removed GualaCognition block
    # (end of removed GualaCognition boot block)

    # AUTONOMOUS CURRICULUM: she studies children's literature on her own, on a
    # schedule, growing her engine + organ-brain from her real reading life.
    # Additive, killable (CURRICULUM_AUTONOMOUS=0), resumable; never raises into boot.
    try:
        from dsf_ai_service.loom_model.curriculum_scheduler import CurriculumScheduler
        global _curriculum
        # Interleave available world feeds into the one study scheduler so they
        # share its reliable awake windows (separate loops get starved).
        _interleave = []
        if os.environ.get("WORLD_FEEDS", "1").strip() != "0":
            _interleave.append(("worldfeed", _world_feed_once))
        # GL-CMD-AUTOMATED-TEACHING-20260717: gap study + tutor share the
        # same reliable study windows (all-at-once doctrine: ON by default).
        if os.environ.get("GAP_STUDY_ENABLED", "1").strip() != "0":
            _interleave.append(("gap_study", _gap_study_once))
        if os.environ.get("TUTOR_AUTONOMOUS", "1").strip() != "0":
            _interleave.append(("tutor", _tutor_once))
        _curriculum = CurriculumScheduler(
            state_dir=STATE_DIR,
            feed_chunk=_curriculum_feed_chunk,
            is_busy=_curriculum_is_busy,
            log=g._log_substrate_event,
            interleave_fns=_interleave,
            interleave_every=int(os.environ.get("STUDY_INTERLEAVE_EVERY", "3") or 3),
        )
        _curriculum.start()
        print(f"[curriculum] autonomous study started: enabled={_curriculum.enabled} "
              f"books={len(_curriculum.curriculum)} chunk={_curriculum.chunk_size} "
              f"interval={_curriculum.interval_sec}s "
              f"interleave={[n for n,_ in _interleave]} every={_curriculum.interleave_every}")
    except Exception as _e:
        print(f"[curriculum] scheduler start skipped (non-fatal): {_e}")

    # World feeds run interleaved inside the curriculum scheduler above so they
    # share its study windows. Manual /worldfeed remains available. /lookup is an
    # explicit unavailable boundary because model output is not Fact-Strand experience.

    # GL-CMD-WIRE-ORGAN-CANDIDATES-F2: start organ surface poll
    _start_organ_surface_poll()
    # GL-CMD-AUTONOMOUS-EMISSION-39: start autonomous emission loop
    _start_autonomous_emission_loop()

    # Initialize ring buffers
    global _substrate_ring, _input_ring
    from dsf_ai_service.substrate.ring_buffer import SubstrateRing, InputRing
    _substrate_ring = SubstrateRing(size=1 << 18)  # 256K entries
    _input_ring = InputRing(size=1 << 14)  # 16K entries
    print(f"[substrate] Rings: substrate={_substrate_ring._size} input={_input_ring._size}")

    # Wire substrate event publishing to ring
    _orig_log_event = g._log_substrate_event
    def _log_and_publish(event_kind, **detail):
        _orig_log_event(event_kind, **detail)
        if _substrate_ring is not None:
            # Pass all detail as a single dict to avoid keyword conflicts
            _substrate_ring.publish(event_kind, g.tick, detail=detail)
    g._log_substrate_event = _log_and_publish

    # Wake from sleep if marker exists
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import check_sleep_marker
        marker = check_sleep_marker(STATE_DIR)
        if marker is not None:
            _guala.wake_from_sleep(state_dir=STATE_DIR)
            print(f"[substrate] Woke from sleep marker")
    except Exception as e:
        print(f"[substrate] Sleep marker check failed: {e}")

    # R3/R4: Start InputRing drain loop — processes sensory frames
    # from the ring without blocking the substrate socket.
    _start_input_ring_consumer()


_input_ring_consumer_started = False

_AUDITORY_PCM_SAMPLE_RATE_HZ = 16_000
_AUDITORY_PCM_SAMPLE_WIDTH_BYTES = 2
_AUDITORY_PCM_MAX_SECONDS = 8
_AUDITORY_PCM_MAX_BYTES = (
    _AUDITORY_PCM_SAMPLE_RATE_HZ
    * _AUDITORY_PCM_SAMPLE_WIDTH_BYTES
    * _AUDITORY_PCM_MAX_SECONDS
)
_AUDITORY_ENCODED_MAX_BYTES = 4 * 1024 * 1024
_AUDITORY_MEDIA_CONTAINER_MAX_BYTES = 30 * 1024 * 1024
# Ask ffmpeg for at most one sample beyond the admitted interval.  Exactly
# eight seconds produces MAX_BYTES; any longer source produces the sentinel
# sample and is rejected rather than silently truncated into a valid capture.
_AUDITORY_PCM_DECODE_SENTINEL_BYTES = _AUDITORY_PCM_SAMPLE_WIDTH_BYTES


def _webm_to_wav_bytes(
        audio_bytes, *, encoded_max_bytes=_AUDITORY_ENCODED_MAX_BYTES):
    """The one shared bounded encoded-media to canonical WAV decoder.
    ffmpeg pipe -> s16le/mono/16k -> WAV wrap (332537d logic, unchanged).
    Returns WAV bytes on success, None on failure (and logs the -108
    decode-failure guard — one guard, one place, for every caller).

    ffmpeg receives output-duration and output-byte walls, while Python reads
    its pipe only up to one byte beyond the admitted PCM boundary and kills
    any overrun.  Decoded stdout therefore cannot grow without bound before
    the eight-second auditory provider has a chance to validate it.
    """
    import io as _sio
    import selectors as _selectors
    import tempfile as _tempfile
    import wave as _wave

    if not isinstance(audio_bytes, bytes):
        raise TypeError("auditory encoded input must be bytes")
    if (
        isinstance(encoded_max_bytes, bool)
        or not isinstance(encoded_max_bytes, int)
        or encoded_max_bytes <= 0
        or encoded_max_bytes > _AUDITORY_MEDIA_CONTAINER_MAX_BYTES
    ):
        raise ValueError("auditory encoded input boundary is invalid")
    if len(audio_bytes) > encoded_max_bytes:
        print("[sound] auditory decode rejected: encoded input exceeds boundary")
        return None

    command = [
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
        '-i', 'pipe:0', '-map', '0:a:0', '-vn', '-sn', '-dn',
        '-f', 's16le', '-ac', '1',
        '-ar', str(_AUDITORY_PCM_SAMPLE_RATE_HZ),
        '-t', str(
            _AUDITORY_PCM_MAX_SECONDS
            + 1 / _AUDITORY_PCM_SAMPLE_RATE_HZ
        ),
        '-fs', str(
            _AUDITORY_PCM_MAX_BYTES
            + _AUDITORY_PCM_DECODE_SENTINEL_BYTES
        ),
        'pipe:1',
    ]
    decoded = bytearray()
    with _tempfile.TemporaryFile() as encoded_input:
        encoded_input.write(audio_bytes)
        encoded_input.seek(0)
        process = subprocess.Popen(
            command,
            stdin=encoded_input,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if process.stdout is None:
            process.kill()
            process.wait()
            raise RuntimeError("ffmpeg stdout pipe was not created")
        selector = _selectors.DefaultSelector()
        selector.register(process.stdout, _selectors.EVENT_READ)
        deadline = time.monotonic() + 8.0
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, 8.0)
                if not selector.select(remaining):
                    raise subprocess.TimeoutExpired(command, 8.0)
                chunk = os.read(
                    process.stdout.fileno(),
                    min(
                        64 * 1024,
                        _AUDITORY_PCM_MAX_BYTES + 1 - len(decoded),
                    ),
                )
                if not chunk:
                    break
                decoded.extend(chunk)
                if len(decoded) > _AUDITORY_PCM_MAX_BYTES:
                    process.kill()
                    process.wait()
                    print(
                        "[sound] auditory decode rejected: decoded PCM exceeds "
                        f"{_AUDITORY_PCM_MAX_SECONDS}s boundary"
                    )
                    return None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, 8.0)
            returncode = process.wait(timeout=remaining)
        finally:
            selector.close()
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()

    decoded_bytes = len(decoded)
    if returncode != 0:
        print(f"[sound] auditory decode failed: ffmpeg exit={returncode}")
        return None
    if decoded and decoded_bytes >= 400:
        _wav_buf = _sio.BytesIO()
        with _wave.open(_wav_buf, 'wb') as _wf:
            _wf.setnchannels(1)
            _wf.setsampwidth(_AUDITORY_PCM_SAMPLE_WIDTH_BYTES)
            _wf.setframerate(_AUDITORY_PCM_SAMPLE_RATE_HZ)
            _wf.writeframes(decoded)
        return _wav_buf.getvalue()
    print(f"[sound] auditory decode failed: ffmpeg produced "
          f"{decoded_bytes} bytes from {len(audio_bytes)} in")
    return None


def _start_input_ring_consumer():
    """Drain InputRing on a background thread. Processes sight_frame and
    sound_window events written by the companion/bridge HTTP endpoints.

    GL-CMD-DENSITY-RETIRE-109 F3: called from both the boot path
    (boot_substrate) and the embedded-mode app startup block
    (_embedded_post_boot) — guard against starting two drain threads."""
    global _input_ring_consumer_started
    if _input_ring_consumer_started:
        print("[substrate] ring consumer already running")
        return
    _input_ring_consumer_started = True

    import base64 as _b64

    def _drain_loop():
        while not _shutdown:
            if _input_ring is None or _guala is None:
                if _shutdown_event.wait(1):
                    break
                continue
            try:
                events = _input_ring.drain(max_n=10)
                for ev in events:
                    kind = ev.get("kind")
                    data = ev.get("data", {})
                    if kind == "sight_frame":
                        try:
                            img_bytes = _b64.b64decode(data.get("frame_b64", ""))
                            if not img_bytes:
                                continue
                            # Inline decode — substrate must not import the FastAPI app
                            from PIL import Image as _PIL_Image
                            import io as _sio
                            _img = _PIL_Image.open(_sio.BytesIO(img_bytes)).convert('L').resize((64, 64))
                            grid = __import__('numpy').array(_img, dtype=__import__('numpy').float64) / 255.0
                            _guala.process_sight_frame(
                                grid,
                                source_anchor_ns=data.get("source_anchor_ns"),
                            )
                            from dsf_ai_service.substrate.grounded_vocab_integration import (
                                object_name_recognition_unavailable)
                            object_name_recognition_unavailable(
                                _guala, source=ev.get("source", "camera_stream"))
                        except Exception as _e:
                            print(f"[sight] frame error: {_e}")
                    elif kind == "sound_window":
                        _guala._enter_live_interaction()
                        try:
                            audio_bytes = _b64.b64decode(data.get("audio_b64", ""))
                            if not audio_bytes:
                                continue
                            # GL-CMD-MIC-EMBEDDED-DECODE-110: single shared decoder.
                            _wav = _webm_to_wav_bytes(audio_bytes)
                            if not _wav:
                                _guala._log_substrate_event(
                                    "sound_frame_decode_failed",
                                    source=ev.get("source", "ambient"))
                                continue
                            source = ev.get("source", "ambient")
                            auditory_event_boundary = data.get(
                                "auditory_event_boundary", "ambient")
                            if auditory_event_boundary not in (
                                    "ambient", "utterance"):
                                _guala._log_substrate_event(
                                    "sound_frame_boundary_rejected",
                                    source=source,
                                    boundary=str(auditory_event_boundary),
                                )
                                continue
                            paired_sight = data.get("sight_b64")
                            source_start_ns = data.get("source_time_start_ns")
                            source_end_ns = data.get("source_time_end_ns")
                            sight_anchor_ns = data.get("sight_source_anchor_ns")
                            if paired_sight:
                                context_id = (
                                    f"sense:av:{source}:ring:{ev.get('seq', 0)}")
                                _guala.window_manager.begin_context(
                                    context_id,
                                    "audiovisual_capture",
                                    context_detail={
                                        "experience_origin": (
                                            "remote_live_audiovisual"),
                                        "auditory_event_boundary": (
                                            auditory_event_boundary),
                                        "source": source,
                                        "source_time_start_ns": source_start_ns,
                                        "source_time_end_ns": source_end_ns,
                                        "sensor_unavailable": [
                                            "touch", "smell", "taste", "body"],
                                    },
                                )
                                try:
                                    try:
                                        sight_bytes = _b64.b64decode(
                                            paired_sight, validate=True)
                                        from PIL import Image as _PIL_Image
                                        import io as _sio
                                        import numpy as _np
                                        image = _PIL_Image.open(
                                            _sio.BytesIO(sight_bytes)
                                        ).convert("L").resize((64, 64))
                                        grid = _np.array(
                                            image, dtype=_np.float64) / 255.0
                                        _guala.process_sight_frame(
                                            grid,
                                            source_anchor_ns=sight_anchor_ns,
                                            source_time_start_ns=source_start_ns,
                                            source_time_end_ns=source_end_ns,
                                        )
                                    except Exception as sight_error:
                                        _guala._log_substrate_event(
                                            "sight_frame_failed_in_causal_window",
                                            source=source,
                                            error_type=type(sight_error).__name__,
                                            error=str(sight_error),
                                        )
                                    try:
                                        _guala.process_sound_frame(
                                            _wav,
                                            source=source,
                                            source_anchor_ns=source_start_ns,
                                            source_time_end_ns=source_end_ns,
                                            auditory_event_boundary=(
                                                auditory_event_boundary),
                                        )
                                    except Exception as sound_error:
                                        _guala._log_substrate_event(
                                            "sound_frame_failed_in_causal_window",
                                            source=source,
                                            error_type=type(sound_error).__name__,
                                            error=str(sound_error),
                                        )
                                finally:
                                    try:
                                        _guala.window_manager.end_context(
                                            context_id,
                                            "audiovisual_capture_complete",
                                        )
                                    except Exception:
                                        _guala.window_manager.discard_unsettled_context(
                                            context_id,
                                            "remote_live_audiovisual_settlement_failed",
                                        )
                                        raise
                            else:
                                _guala.process_sound_frame(
                                    _wav,
                                    source=source,
                                    source_anchor_ns=source_start_ns,
                                    source_time_end_ns=source_end_ns,
                                    auditory_event_boundary=(
                                        auditory_event_boundary),
                                )
                            from dsf_ai_service.substrate.grounded_vocab_integration import (
                                spoken_word_recognition_unavailable)
                            spoken_word_recognition_unavailable(
                                _guala, source=source)
                        except Exception as _e:
                            print(f"[sound] frame error: {_e}")
                        finally:
                            _guala._exit_live_interaction()
            except Exception as _drain_error:
                print(f"[input-ring] drain error: {_drain_error}")
            if _shutdown_event.wait(0.5):
                break

    _start_background_thread(_drain_loop, "input-ring-consumer")
    print("[substrate] InputRing consumer started (R3/R4)")


# ═══════════════════════════════════════════════════════════════
# Op dispatch
# ═══════════════════════════════════════════════════════════════

def dispatch(op, args):
    """Dispatch a single op. Returns result dict. Raises on error."""
    if _guala is None:
        raise RuntimeError("substrate not ready")

    handler = OP_HANDLERS.get(op)
    if handler is None:
        raise ValueError(f"unknown op: {op}")
    return handler(args)


# ── v7 ops ──────────────────────────────────────────────────────

def handle_v7_state(args):
    session_id = args.get("session_id", "default")
    t0 = time.time()
    from dsf_ai_service.substrate.v7_engine import _sessions, _sessions_lock
    with _sessions_lock:
        session = _sessions.get(session_id)
    if session is None:
        return {"error": "v7 session not found", "status_code": 404}
    t1 = time.time()
    result = session.get_state(engine=_guala)
    t2 = time.time()
    print(f"[v7-state] sid={session_id} session={int((t1-t0)*1000)}ms "
          f"get_state={int((t2-t1)*1000)}ms total={int((t2-t0)*1000)}ms")
    return result


def _ensure_v7_link(session):
    """Wire v7 session reference to v5 engine for context priors."""
    if _guala is not None:
        _guala._v7_session = session

def handle_v7_converse(args):
    session_id = args.get("session_id", "default")
    text = args.get("text", "")
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    session = get_or_create_session(session_id, engine=_guala)
    _ensure_v7_link(session)
    result = session.converse(text)
    try:
        save_session(session)
    except Exception:
        pass
    # Sites 6+6b DELETE: _cognition_learn(text) and _cognition_learn(reply) removed.
    # v7→v5 atlas wiring is a separate decision (wiring spec -26 §F deferred path).
    result["session_id"] = session_id
    return result


def handle_v7_feedback(args):
    session_id = args.get("session_id", "default")
    correct = args.get("correct", "")
    expected_tokens = args.get("expected_tokens", [])
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    session = get_or_create_session(session_id, engine=_guala)
    result = session.apply_feedback(correct, expected_tokens)
    try:
        save_session(session)
    except Exception:
        pass
    result["session_id"] = session_id

    # V7 feedback remains inside its isolated V7 session.  The V7→V5 atlas
    # wiring decision is explicitly deferred; no uncertified shared "last
    # reply" may be reinforced into the persistent V5 organism.
    return result


def handle_v7_quiet(args):
    session_id = args.get("session_id", "default")
    n_ticks = min(args.get("n_ticks", 10), 50)
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    session = get_or_create_session(session_id, engine=_guala)
    results = session.quiet_tick(n_ticks)
    try:
        save_session(session)
    except Exception:
        pass
    total_replayed = sum(len(r["replayed"]) for r in results)
    total_commits = sum(len(r["commits"]) for r in results)
    return {"session_id": session_id, "ticks": len(results),
            "replayed": total_replayed, "commits": total_commits}


def handle_v7_save(args):
    session_id = args.get("session_id", "default")
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    session = get_or_create_session(session_id, engine=_guala)
    save_session(session)
    data = session.to_json()
    return {"saved": True, "session_id": session_id,
            "schema_version": data.get("schema_version"),
            "tick": data.get("tick"),
            "n_sections": len(data.get("sections", {})),
            "vocab_size": sum(len(v) for v in session.vocab.values())}


# ── gualaloom_post — the command dispatcher ──────────────────────

def handle_gualaloom_post(args):
    """Dispatch a gualaloom chat command. Mirrors gualaloom_chat() in app.py."""
    command = (args.get("command") or "").strip().lower()
    text = args.get("text", "")
    source = args.get("source", "joe")

    if _guala.is_asleep and command not in ("/status", "/wake", "/presence",
                                             "/debug_chi", "/deep_full_coverage",
                                             "/diag", "/curriculum", "/curriculum_on",
                                             "/curriculum_off", "/worldfeed", "/events"):
        # Conversations auto-wake her — talking to her should wake her.
        # /converse and bare text input both call wake_from_sleep() to end
        # the SLEEPING activity immediately (coordinator.wake alone only sets
        # presence — it does NOT change the activity state).
        if text.strip() and (not command or command == "/converse"):
            try:
                _guala.wake_from_sleep(state_dir=STATE_DIR)
                _guala.coordinator.wake(source or "joe", _guala, _guala.needs, _guala.atlas)
            except Exception:
                pass
        # After auto-wake attempt, check again
        if _guala.is_asleep:
            # Wake didn't complete (still in sleep/dream state after attempt)
            ca = getattr(_guala, '_current_activity', None)
            quiet_kind = getattr(ca, 'kind', 'sleeping').lower() if ca else 'sleeping'
            return {
                "response": f"she is {quiet_kind}...",
                "response_source": "sleep_quiet",
                "asleep": True,
                "sleep_tick": _guala.tick,
                "motifs": _guala.introspect()["vocab"],
            }

    if command == "/status":
        return _cmd_status()
    elif command == "/room":
        # Read room state directly from world_state.json on EFS
        try:
            import json as _js
            _wp = os.path.join(STATE_DIR, "world_state.json")
            with open(_wp) as _f:
                _ws = _js.load(_f)
            from dsf_ai_service.virtual_home import sky_state, OBJECTS
            _sky = sky_state(_ws.get("weather", "clear"))
            _objs = {}
            for _oid, _entry in (_ws.get("objects") or {}).items():
                if _oid in OBJECTS and isinstance(_entry, dict):
                    _objs[_oid] = {"state": _entry.get("state"), "place": _entry.get("place")}
            return {"objects": _objs, "sky": _sky, "weather": _ws.get("weather", "clear"),
                    "sky_description": _sky.get("description", "")}
        except Exception as _e:
            return {"objects": {}, "sky": {}, "weather": "clear", "error": str(_e)}
    elif command == "/events":
        return _cmd_events(text)
    elif command == "/presence":
        return _cmd_presence(text)
    elif command == "/sleep":
        return _cmd_sleep()
    elif command == "/wake":
        return _cmd_wake(text)
    elif command == "/rest":
        return _cmd_rest(text)
    elif command.startswith("/picture "):
        return _cmd_picture(command)
    elif command == "/diag":
        return _cmd_diag()
    elif command.startswith("/addbook:"):
        return _cmd_addbook(command, text)
    elif command.startswith("/removebook:"):
        return _cmd_removebook(command)
    elif command.startswith("/addpicture:"):
        return _cmd_addpicture(command, text)
    elif command.startswith("/addpdf:"):
        return _cmd_addpdf(command, text)
    elif command.startswith("/addsound:"):
        return _cmd_addsound(command, text)
    elif command.startswith("/bundle:"):
        return _cmd_bundle(command, text)
    elif command == "/listen":
        return _cmd_listen(text, source)
    elif command == "/thought":
        # GL-CMD-AUTONOMOUS-EMISSION-39: serve cached autonomous thought to UI
        return _cmd_thought()
    elif command == "/organs":
        return {"response": json.dumps(_guala_organ_brain or {"organ_brain": "not loaded"}),
                "organ_brain": _guala_organ_brain}
    elif command == "/organs_say":
        try:
            # GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23: SILENCED.
            # GL-CMD-BIGRAM-DELETE-EVE-20260629-34: _guala_cognition.expose() removed.
            # GualaCognition deleted. No learning call here anymore.
            if _guala is not None:
                _guala._log_substrate_event("organ_brain_compose_silenced",
                                            input_text=(text or "")[:120],
                                            reason="pending_phase_d_inspection")
            return {"response": "", "speech": "",
                    "response_source": "organ_brain_retired",
                    "engine": "guala-cognition-retired"}
        except Exception as _e:
            return {"response": "", "speech": "",
                    "response_source": "organ_brain_retired"}
    elif command == "/curriculum":
        if _curriculum is None:
            return {"response": "curriculum scheduler not loaded"}
        _cur_st = _curriculum.status()
        # GL-CMD-AUTOMATED-TEACHING-20260717: surface the gap ledger and
        # tutor state alongside the study schedule — one honest window
        # into what she's being taught and what she's missing.
        try:
            from dsf_ai_service.substrate.knowledge_gap_ledger import get_ledger
            _cur_st["knowledge_gaps"] = get_ledger(STATE_DIR).status()
            _cur_st["tutor_last"] = _TUTOR_STATE.get("last_status", {})
        except Exception:
            pass
        # GL-CMD-SYNTAX-ARC-20260718: the daily prediction curve — the
        # instrument Joe's syntax decision rides on.
        try:
            from dsf_ai_service.substrate.reading_prediction_ledger import (
                get_ledger as _rp_ledger)
            _cur_st["reading_predictions"] = _rp_ledger(STATE_DIR).status()
        except Exception:
            pass
        return {"response": json.dumps(_cur_st), "curriculum": _cur_st}
    elif command == "/curriculum_now":
        # force one study step now (validation aid); ignores the interval gate
        if _curriculum is None:
            return {"response": "curriculum scheduler not loaded"}
        if _curriculum_is_busy():
            return {"response": "busy (asleep or bulk-loading); try again"}
        return {"response": json.dumps(_curriculum.study_once())}
    elif command in ("/curriculum_on", "/curriculum_off"):
        if _curriculum is None:
            return {"response": "curriculum scheduler not loaded"}
        _curriculum.enabled = (command == "/curriculum_on")
        return {"response": f"curriculum enabled={_curriculum.enabled}"}
    elif command == "/lookup":
        boundary = _lookup_once()
        return {"response": boundary["reason"], "grounded": False, **boundary}
    elif command == "/worldfeed":
        # force one registered world-feed study chunk now (validation aid)
        if _curriculum_is_busy():
            return {"response": "she is asleep or bulk-loading; try again when awake"}
        return {"response": json.dumps(_world_feed_once())}
    elif command == "/debug_chi":
        return _cmd_debug_chi(text)
    elif command == "/deep_full_coverage":
        return _cmd_deep_full_coverage()
    else:
        emission_mode = args.get("emission_mode")
        return _cmd_converse(text, source, emission_mode=emission_mode)


def _cmd_deep_full_coverage():
    """Read-only diagnostic: scan entire deep_atlas for chi values that have
    all 3 gate sections (subject, verb, object) covered in co_occurrence.
    Returns list of such chi values with example words from vocabulary."""
    GATE_SECTIONS = {"subject", "verb", "object"}
    band = getattr(_guala.atlas, 'band', 2)
    # Collect chi values where co_occurrence covers all 3 sections
    # A chi may appear in entries from multiple chi keys due to band overlap —
    # aggregate by the deep_entry's chi key.
    chi_section_coverage = {}  # chi_key -> set of sections with co_occurrence
    for chi_k, entries in _guala.deep_atlas.entries.items():
        for de in entries:
            co = de.get("co_occurrence", {})
            if not co:
                continue
            covered = set(sec for sec, sv in co.items() if sv)
            existing = chi_section_coverage.get(chi_k, set())
            chi_section_coverage[chi_k] = existing | covered
    # Find chi values with all 3 gate sections covered
    full_coverage_chis = sorted(
        chi_k for chi_k, covered in chi_section_coverage.items()
        if GATE_SECTIONS.issubset(covered)
    )
    # For each such chi, find vocabulary words that produce it (chi ± band reverse lookup)
    # Build word->chi map from all section modes
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
    word_chi_cache = {}
    for sec_name, sec in _guala.sections.items():
        if not hasattr(sec, 'modes'):
            continue
        for (_, _, word) in sec.modes:
            if word and word not in word_chi_cache:
                krim = LanguageKrimelack()
                krim.transduce(word)
                word_chi_cache[word] = krim.winding
    # Map chi → words
    chi_to_words = {}
    for word, chi in word_chi_cache.items():
        chi_to_words.setdefault(chi, []).append(word)
    # Build result: for each full-coverage chi, show matching words
    examples = []
    for chi_k in full_coverage_chis[:20]:  # cap at 20 for response size
        covered = chi_section_coverage[chi_k]
        # Words at chi_k itself (not band-expanded)
        words_at_chi = chi_to_words.get(chi_k, [])[:5]
        examples.append({
            "chi": chi_k,
            "sections_covered": sorted(covered),
            "example_words": words_at_chi,
        })
    return {
        "n_full_coverage_chi": len(full_coverage_chis),
        "full_coverage_chis": full_coverage_chis[:50],
        "examples": examples,
        "total_chi_keys_in_deep": len(chi_section_coverage),
    }


def _cmd_debug_chi(text):
    """Read-only diagnostic: show chi values for each word in text,
    with deep_atlas section coverage at each chi ± band.
    Returns per-word chi values and which sections are covered."""
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
    from dsf_ai_service.v4.gualaloom_v5_engine import _normalize_text
    words = _normalize_text(text)
    if not words:
        return {"error": "no words"}
    band = getattr(_guala.atlas, 'band', 2)
    GATE_SECTIONS = {"subject", "verb", "object"}
    result = []
    for w in words:
        krim = LanguageKrimelack()
        krim.transduce(w)
        chi = krim.winding
        # Check deep_atlas coverage in chi ± band window
        covered = set()
        n_entries = 0
        for d in range(-band, band + 1):
            for de in _guala.deep_atlas.entries.get(chi + d, []):
                sec = de.get("section", "")
                co = de.get("co_occurrence", {})
                if co:
                    covered.add(sec)
                    n_entries += 1
        result.append({
            "word": w,
            "chi": chi,
            "sections_covered": sorted(covered),
            "gate_sections_covered": sorted(covered & GATE_SECTIONS),
            "all_gate_covered": GATE_SECTIONS.issubset(covered),
            "n_deep_entries": n_entries,
        })
    # Summary: which words have all 3 gate sections covered
    full_coverage = [r for r in result if r["all_gate_covered"]]
    return {
        "words": result,
        "full_gate_coverage_words": [r["word"] for r in full_coverage],
        "any_full_coverage": len(full_coverage) > 0,
    }


def _cmd_status():
    s = _guala.introspect()
    n = s["needs"]
    ph = _guala.persistence_health(STATE_DIR)
    # GL-CMD-104: read last_s3_result from SaveCoordinator
    from dsf_ai_service.save_coordinator import SAVE_COORDINATOR
    if SAVE_COORDINATOR and hasattr(SAVE_COORDINATOR, '_last_s3_result') and SAVE_COORDINATOR._last_s3_result:
        s3r = SAVE_COORDINATOR._last_s3_result
        if "s3_error" not in s3r:
            ph["last_s3_backup"] = s3r
        else:
            ph["last_s3_backup"] = None
    else:
        ph["last_s3_backup"] = None
    sec_parts = []
    for nm, sec in s["sections"].items():
        sec_parts.append(f"{nm}: {sec['modes']}m/{sec['commits']}c")
    id_short = (ph.get("guala_identity") or "none")[:8]
    return {
        "response": (
            f"id: {id_short}.. | schema: {ph.get('schema_version', '?')}\n"
            f"vocab: {s['vocab']} | reads: {s['reads']} | tick: {s['tick']}\n"
            f"sections: {' | '.join(sec_parts)}\n"
            f"atlas: {s['cross_modal_bindings']} cross-modal / {s.get('cross_modal_bundle', 0)} bundled / {s['atlas_entries']} entries | deep: {s.get('n_deep_atlas', s.get('deep_atlas', {}).get('n_entries', 0))}\n"
            f"needs: stab={n['stability']:.3f} nov={n['novelty']:.3f} "
            f"conn={n['connection']:.3f} v={n['valence']:+.3f} a={n['arousal']:.3f}\n"
            f"pair-bond: {'on' if s['pair_bond_active'] else 'off'} | "
            f"recoveries(lifetime): {s['suffering_events']} | "
            f"coord: att={s['coordinator_attentions']} act={s['coordinator_actions']}\n"
            f"persistence: save@tick={ph['last_save_tick']} "
            f"files={'all' if not ph['files_missing'] else 'MISSING:' + ','.join(ph['files_missing'])} "
            f"boot={'ok' if ph['load_successful_at_boot'] else 'FAILED'} "
            f"integrity={'ok' if not ph.get('integrity_errors') else 'ERRORS'}\n"
            f"snapshots: {ph.get('snapshots_available', 0)} | "
            f"events: {ph.get('events_log', {}).get('current_file_size_bytes', 0)}B\n"
            f"deep: {s.get('deep_atlas', {}).get('n_entries', 0)} entries "
            f"str={s.get('deep_atlas', {}).get('total_strength', 0)} "
            f"surv={s.get('deep_atlas', {}).get('promotions_survival', 0)} "
            f"ep={s.get('deep_atlas', {}).get('promotions_episodic', 0)} "
            f"reinst={s.get('deep_atlas', {}).get('reinstatements_since_boot', 0)}"
        ),
        "motifs": s["vocab"],
        "vocab": s["vocab"],
        "tick": s["tick"],  # GL-ADDENDUM-106: wire center readout in loomscan.html
        "asleep": _guala.is_asleep,
        "persistence_health": ph,
        "atlas_health": s.get("atlas_health", {}),
        "presence": s.get("presence", {}),
        "pair_bond": s.get("pair_bond", {}),
        "deep_atlas": s.get("deep_atlas", {}),
        "ladder": s.get("ladder", {}),
        "n_sounds": s.get("n_sounds", 0),
        "sounds": [{"item_id": snd["item_id"], "title": snd["title"],
                    "times_attended": snd.get("times_attended", 0)}
                   for snd in s.get("sounds", [])[-10:]],
        "current_activity": s.get("current_activity"),
        "activity_history_summary": s.get("activity_history_summary", {}),
        "n_motifs": s.get("n_motifs", 0),
        "n_corpora": len(s.get("corpora", [])),
        "corpora": [{"corpus_id": c["corpus_id"], "title": c["title"]}
                    for c in s.get("corpora", [])[-10:]],
        "sensory_items": len(s.get("sensory_items", [])),
        "n_visual_fragments": s.get("n_visual_fragments", 0),
        "n_visual_motifs": s.get("n_visual_motifs", 0),
        "sight_section": {"n_motifs": s.get("n_visual_motifs", 0)},
        "n_pictures": len(s.get("pictures", [])),
        "pictures": [{"item_id": p["item_id"], "title": p["title"],
                      "times_attended": p["times_attended"]}
                     for p in s.get("pictures", [])],  # all pictures for activity lookup
        "n_videos": len(s.get("videos", [])),
        # Her real organ-brain — the merged 8-hemisphere atlas from her EFS state.
        # This is the ONE brain: em/pr/ep/sc/gp/sf/sv/aff with real atlas counts.
        "organ_brain": {
            **(_guala_organ_brain or {}),
            "compose_status": "organ_brain_retired",
        },
        "autonomous_emissions_count": getattr(_guala, "autonomous_emissions_count", 0),
        "last_autonomous_emission_tick": getattr(_guala, "last_autonomous_emission_tick", -1),
        "last_autonomous_attempt_tick": getattr(_guala, "last_autonomous_attempt_tick", -1),
        # GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1: organism_worker was added to
        # introspect() by -179 but never copied into THIS hand-curated dict
        # (introspect()'s full return is not surfaced verbatim) -- flagged
        # live, fixed here. organism_population answers item 3's own gap
        # ("no direct live population counter exists... recommending a
        # field get added next to organism_worker").
        "organism_worker": s.get("organism_worker", {}),
        "organism_population": s.get("organism_population", 0),
        # GL-CMD-GROWTH-LIVE-EVE-20260705-202 G3a: same forgot-to-forward
        # gap as app.py's embedded-mode handler -- fixed in both.
        "organism_growth": s.get("organism_growth", {}),
        # GL-CMD-GROWTH-LIVE-EVE-20260705-202 G1: same field as app.py's
        # embedded-mode /status handler -- ends "what's deployed" disputes
        # in remote mode too.
        "running_sha": os.environ.get("GIT_SHA", "unknown"),
        # GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205 C5: same field as
        # app.py's embedded-mode handler.
        "tick_rate": s.get("tick_rate", 0.0),
        "tick_rate_had_pending_work": s.get("tick_rate_had_pending_work", False),
        # GL-CMD-METER-LIVENESS-EVE-20260705-187 M1: "curriculum feeders"
        # (cognition-meter row) needs a real live signal to check against,
        # not the -156-era "0 -- confirmed not running" text frozen forever.
        # _curriculum.status() already existed (curriculum_scheduler.py);
        # just never surfaced. None (not {}) when the scheduler was never
        # started (e.g. CURRICULUM_AUTOSTART-style disable or a boot before
        # -185/B3's reconnect landed) -- distinct from "started but idle".
        "curriculum_status": (_curriculum.status()
                              if _curriculum is not None else None),
        # GL-CMD-SCENE-LANES-B1-188 V5: real place/ambient of the most
        # recently read sentence, for loomscan's scene panels (today
        # hardcoded "no lanes yet").
        "scene_lanes": s.get("scene_lanes", {"place": [], "ambient": []}),
    }


def _cmd_events(text):
    # GL-CMD-SEAT-TRUTH-UI-EVE-20260704-180 S4: this is the ONLY call site
    # reached from app.py's GET /api/v1/gualaloom/events?n=200 (the RECENT
    # EMISSIONS/HEMISPHERES panel's own data source, per that route's
    # docstring) -- it forwards `n` as `text` intending "how many recent
    # events", but this parsed it as `since_tick` (a tick cutoff, always
    # far smaller than the real tick counter, so it filtered ~nothing) AND
    # hardcoded limit=50 regardless -- so the panel silently only ever saw
    # the last 50 raw events, never the 200 it asked for, making sparse
    # event kinds (like real-content emissions, if attempts happen far
    # less often than sight/sound-frame events) invisible more often than
    # they should be. Fixed to honor `text` as the actual limit, matching
    # every real caller's intent. get_recent_events's own since_tick-based
    # callers (SSE-style incremental polling, app.py:3286/3295) are
    # untouched -- this is the one place that was never using it that way.
    limit = 200
    try:
        limit = int(text.strip()) if text.strip() else 200
    except ValueError:
        pass
    limit = max(1, min(limit, 1000))  # ring buffer itself caps at 1000
    events = _guala.get_recent_events(since_tick=0, limit=limit)
    return {"response": f"{len(events)} events",
            "motifs": _guala.introspect()["vocab"],
            "events": events}


def _cmd_presence(text):
    source = text.strip().lower() if text.strip() else "joe"
    if source in {"joe", "wc", "c1"}:
        if not _guala.coordinator._presence.get(source, False):
            _guala.coordinator.wake(source, _guala, _guala.needs, _guala.atlas)
            _guala._log_substrate_event("presence_heartbeat",
                                        source=source, action="wake")
        else:
            _guala.coordinator.update_last_input(source, _guala.tick)
    return {"response": "ok", "motifs": _guala.introspect()["vocab"]}


def _cmd_sleep():
    result = _guala.manual_sleep()
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}


def _cmd_wake(text):
    source = text.strip().lower() if text else "joe"
    if source not in {"joe", "wc", "c1"}:
        return {"response": f"wake: unknown source '{source}'", "motifs": 0}
    result = _guala.coordinator.wake(source, _guala, _guala.needs, _guala.atlas)
    _guala.log_event(STATE_DIR, "wake", source=source)
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}


def _cmd_rest(text):
    source = text.strip().lower() if text else "joe"
    result = _guala.coordinator.rest(source, _guala, reason="voluntary")
    _guala.log_event(STATE_DIR, "rest", source=source)
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}


def _cmd_picture(command):
    item_id = command.split(" ", 1)[1].strip()
    import base64 as _b64
    pic = _guala._pictures.get(item_id)
    if pic is None:
        return {"response": f"picture not found: {item_id}", "motifs": 0}
    orig_path = getattr(pic, 'original_path', None)
    if orig_path and os.path.exists(orig_path):
        from PIL import Image
        import io as _io
        try:
            img = Image.open(orig_path)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            img.thumbnail((360, 360), Image.LANCZOS)
            buf = _io.BytesIO()
            img.save(buf, format='JPEG', quality=80)
            b64 = _b64.b64encode(buf.getvalue()).decode()
            return {"response": "ok", "picture_data": f"data:image/jpeg;base64,{b64}",
                    "title": pic.title, "item_id": item_id}
        except Exception:
            pass
    if pic.intensity_grid is not None:
        import numpy as np
        from PIL import Image
        import io as _io
        img = Image.fromarray((pic.intensity_grid * 255).astype(np.uint8), mode='L')
        buf = _io.BytesIO()
        img.save(buf, format='PNG')
        b64 = _b64.b64encode(buf.getvalue()).decode()
        return {"response": "ok", "picture_data": f"data:image/png;base64,{b64}",
                "title": pic.title, "item_id": item_id}
    return {"response": f"no image data for {item_id}", "motifs": 0}


def _cmd_diag():
    from collections import Counter
    atlas = _guala.atlas
    FTHRESH = 0.02
    motif_reach = Counter()
    for chi_key, entries in atlas.entries.items():
        for e in entries:
            if e.strength > FTHRESH:
                motif_reach[(e.section, e.motif_id)] += 1
    top_reach = motif_reach.most_common(20)
    return {
        "response": f"top reach: {top_reach[:5]}",
        "motifs": _guala.introspect()["vocab"],
        "top_reach": [{"section": s, "motif_id": m, "reach": r}
                      for (s, m), r in top_reach],
        "n_live_bindings": atlas.n_live_bindings(),
        "total_strength": round(atlas.total_strength(), 2),
    }


def _cmd_addbook(command, text):
    filename = command[len("/addbook:"):]
    title = filename.replace('.txt', '').replace('_', ' ')
    corpus_id = filename.replace('.txt', '').replace(' ', '_').lower()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return {"response": "empty book", "motifs": _guala.introspect()["vocab"]}
    _guala.add_corpus(corpus_id, title, lines)
    _guala._log_substrate_event("corpus_added",
                                corpus_id=corpus_id, title=title,
                                n_lines=len(lines))
    return {"response": f"added \"{title}\" ({len(lines)} lines) to her library",
            "motifs": _guala.introspect()["vocab"]}


def _cmd_removebook(command):
    corpus_id = command[len("/removebook:"):].strip()
    if corpus_id in _guala._corpora:
        c = _guala._corpora[corpus_id]
        n_lines = len(c.lines)
        del _guala._corpora[corpus_id]
        _guala._log_substrate_event("corpus_removed",
                                    corpus_id=corpus_id, title=c.title,
                                    n_lines=n_lines)
        return {"response": f"removed \"{c.title}\" ({n_lines} lines)",
                "motifs": _guala.introspect()["vocab"]}
    available = [c.corpus_id for c in _guala._corpora.values()]
    return {"response": f"corpus '{corpus_id}' not found. available: {available}",
            "motifs": _guala.introspect()["vocab"]}


def _cmd_addpicture(command, text):
    import base64, hashlib
    import numpy as np
    filename = command[len("/addpicture:"):]
    title = filename.rsplit('.', 1)[0] if '.' in filename else filename
    b64_data = text.strip()
    if not b64_data:
        return {"response": "no image data", "motifs": _guala.introspect()["vocab"]}
    t0 = time.time()
    try:
        img_bytes = base64.b64decode(b64_data)
        from dsf_ai_service.app import decode_image_bytes
        from dsf_ai_service.v4.gualaloom_v5_engine import PictureItem
        _, grid, orig_w, orig_h = decode_image_bytes(img_bytes)
        item_id = hashlib.md5(img_bytes).hexdigest()[:12]
        pic_dir = os.path.join(STATE_DIR, "pictures")
        os.makedirs(pic_dir, exist_ok=True)
        ext = filename.rsplit('.', 1)[1] if '.' in filename else 'jpg'
        orig_path = os.path.join(pic_dir, f"{item_id}_original.{ext}")
        with open(orig_path, 'wb') as f:
            f.write(img_bytes)
        pic = PictureItem(item_id=item_id, title=title,
                          intensity_grid=grid, source="upload",
                          shown_at_tick=_guala.tick)
        pic.original_path = orig_path
        pic.original_width = orig_w
        pic.original_height = orig_h
        _guala._pictures[item_id] = pic
        _guala._log_substrate_event("picture_uploaded",
                                    item_id=item_id, title=title,
                                    original_size=f"{orig_w}x{orig_h}")
        # GL-CMD-PICTURE-TITLE-BIND Part 1 + GL-CMD-EPISODE-BINDING C2.4
        pic_bundle_id = f"item:pic:{item_id}"
        episode_ref = f"episode:addpicture:{_guala.tick}:{item_id}"
        _pres, _loc, _sky = _guala._current_situation()
        if title and title.strip():
            try:
                _guala.read_sentence(title.strip(), source="addpicture",
                                     bundle_id=pic_bundle_id,
                                     episode_ref=episode_ref,
                                     presence=_pres, location=_loc, sky_state=_sky)
            except Exception:
                pass
        result = {"response": f"showed her \"{title}\" ({orig_w}x{orig_h})",
                  "motifs": _guala.introspect()["vocab"]}
    except Exception as e:
        result = {"response": f"image decode error: {e}",
                  "motifs": _guala.introspect()["vocab"]}
    print(f"[decode-picture] {time.time()-t0:.2f}s")
    return result


def _cmd_addpdf(command, text):
    import base64
    import numpy as np
    filename = command[len("/addpdf:"):]
    title = filename.replace('.pdf', '').replace('_', ' ')
    corpus_id = filename.replace('.pdf', '').replace(' ', '_').lower()
    b64_data = text.strip()
    if not b64_data:
        return {"response": "no PDF data", "motifs": _guala.introspect()["vocab"]}
    t0 = time.time()
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import PictureItem
        pdf_bytes = base64.b64decode(b64_data)
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        n_pages = len(doc)
        all_text = []
        for page in doc:
            t = page.get_text()
            if t.strip():
                all_text.append(t.strip())
        feedback = []
        if all_text:
            full_text = "\n".join(all_text)
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            split_lines = []
            for line in lines:
                if len(line) > 200:
                    for sent in line.replace('. ', '.\n').split('\n'):
                        if sent.strip():
                            split_lines.append(sent.strip())
                else:
                    split_lines.append(line)
            _guala.add_corpus(corpus_id, title, split_lines)
            _guala._log_substrate_event("corpus_added",
                                        corpus_id=corpus_id, title=title,
                                        n_lines=len(split_lines), source="pdf")
            feedback.append(f"text: {n_pages} pages, {len(split_lines)} lines")
        doc.close()
        if not feedback:
            feedback.append("empty PDF")
        result = {"response": f"\"{title}\": {'; '.join(feedback)}",
                  "motifs": _guala.introspect()["vocab"]}
    except Exception as e:
        result = {"response": f"PDF decode error: {e}",
                  "motifs": _guala.introspect()["vocab"]}
    print(f"[decode-pdf] {time.time()-t0:.2f}s")
    return result


def _cmd_addsound(command, text):
    import base64
    import binascii
    import hashlib

    filename = command[len("/addsound:"):]
    title = filename.rsplit('.', 1)[0] if '.' in filename else filename
    b64_data = text.strip()
    if not b64_data:
        return {"response": "no audio data", "motifs": _guala.introspect()["vocab"]}
    t0 = time.time()
    try:
        if len(b64_data) > 4 * ((_AUDITORY_ENCODED_MAX_BYTES + 2) // 3):
            raise ValueError("encoded sound exceeds the 4 MiB request boundary")
        snd_bytes = base64.b64decode(b64_data, validate=True)
        if len(snd_bytes) > _AUDITORY_ENCODED_MAX_BYTES:
            raise ValueError("encoded sound exceeds the 4 MiB request boundary")
        wav_bytes = _webm_to_wav_bytes(snd_bytes)
        if wav_bytes is None:
            raise ValueError("sound could not be decoded inside the auditory boundary")
        snd_id = hashlib.sha256(snd_bytes).hexdigest()[:16]
        receipt = _guala.register_replayable_sound(
            snd_id, title, wav_bytes, source=f"sound_upload:{snd_id}")
        result = {
            "response": (
                f"heard \"{title}\" through the full auditory field "
                f"({receipt['duration_s']:.1f}s)"),
            "motifs": _guala.introspect()["vocab"],
            "sound_info": {
                "item_id": snd_id,
                "title": title,
                "duration_s": round(receipt["duration_s"], 2),
                "causal_entries": receipt["causal_receipt"].get(
                    "entries_bound", 0),
                "replay_pcm_bytes": receipt["replay_pcm_bytes"],
                "auditory_boundary": "full_field_l5",
            },
        }
    except (ValueError, TypeError, binascii.Error) as e:
        result = {"response": f"sound error: {e}",
                  "motifs": _guala.introspect()["vocab"]}
    except Exception as e:
        result = {"response": f"sound processing error: {e}",
                  "motifs": _guala.introspect()["vocab"]}
    print(f"[decode-sound] {time.time()-t0:.2f}s")
    return result


def _cmd_bundle(command, text):
    """Phase 2: Full multimodal cross-modal binding in same tick window.
    GL-BRIEF-BUNDLE-PHASE-2: all modalities bind at current tick ±5."""
    from dsf_ai_service.v4.gualaloom_v5_engine import (
        deterministic_motif_id, DWELL_GATE_META,
    )
    bundle_name = command[len("/bundle:"):]
    try:
        bundle_data = json.loads(text) if text else {}
    except json.JSONDecodeError:
        bundle_data = {"caption": text}

    caption = bundle_data.get("caption", "")
    picture_id = bundle_data.get("picture_id", "")
    sound_id = bundle_data.get("sound_id", "")
    touch = bundle_data.get("touch", [])
    smell = bundle_data.get("smell", [])
    taste = bundle_data.get("taste", [])

    results = []
    n_chis = 0
    base_tick = _guala.tick
    # GL-CMD-CROSS-MODAL-BUNDLE: all writes in this bundle share the same bundle_id
    bundle_id = f"bundle:{bundle_name}:{base_tick}"
    # GL-CMD-EPISODE-BINDING C2.4: one episode_ref + situation per /bundle command
    _bnd_ep_ref = f"episode:bundle:{base_tick}:{bundle_name}"
    _bnd_pres, _bnd_loc, _bnd_sky = _guala._current_situation()

    # 1. Caption — read into substrate as wc-sourced input
    if caption:
        try:
            _guala.read_sentence(caption, source="wc", bundle_id=bundle_id,
                                 episode_ref=_bnd_ep_ref, presence=_bnd_pres,
                                 location=_bnd_loc, sky_state=_bnd_sky)
            results.append(f"told her \"{caption}\"")
        except Exception as e:
            results.append(f"word ERROR: {e}")

    # 2. Picture — run visual attend path (view_picture → sight section → atlas)
    if picture_id:
        pic = _guala._pictures.get(picture_id)
        if pic:
            try:
                from dsf_ai_service.visual_krimelack import view_picture
                fragments = view_picture(
                    pic.intensity_grid, source_id=pic.item_id,
                    born_tick=_guala.tick, seed=_guala.tick % 10000)
                _guala._visual_fragments_count += len(fragments)
                motif, is_new, overlap = _guala.sight.process_viewing(
                    fragments, pic.item_id, _guala.tick)
                if motif:
                    chi_val = motif.motif_id % 100
                    _guala._atlas_record("sight", motif.motif_id, chi_val,
                                        _guala.tick, salience=1.2,
                                        dwell_ticks=DWELL_GATE_META,
                                        sensory_refs=[f"pic:{pic.item_id}"],
                                        bundle_id=bundle_id,
                                        episode_ref=_bnd_ep_ref,
                                        presence=_bnd_pres, location=_bnd_loc,
                                        sky_state=_bnd_sky, source="bundle",
                                        **_guala._affect_kwargs())
                    n_chis += 1
                    _guala._log_substrate_event(
                        "visual_motif_committed" if is_new else "visual_motif_fired",
                        motif_id=motif.motif_id, overlap=round(overlap, 3),
                        source_id=pic.item_id, n_fragments=len(fragments),
                        via="bundle")
                results.append(f"viewed {pic.title} ({len(fragments)} fragments)")
            except Exception as e:
                results.append(f"picture ERROR: {e}")
        else:
            results.append(f"picture {picture_id} not found")

    # 3. Sound — replay the exact retained capture through auditory L5.
    if sound_id:
        snd = _guala._sounds.get(sound_id)
        if snd:
            try:
                replay = _guala.replay_sound_asset(
                    sound_id, source=f"experience_bundle:{bundle_name}")
                if replay.get("accepted"):
                    n_chis += replay["causal_receipt"].get("entries_bound", 0)
                    results.append(
                        f"heard {snd.get('title', sound_id)} through auditory L5")
                else:
                    results.append(
                        f"sound {sound_id} unavailable: {replay.get('reason')}")
            except Exception as e:
                results.append(f"sound ERROR: {e}")
        else:
            results.append(f"sound {sound_id} not found")

    # 4. Touch/smell/taste — atlas.record per descriptor
    for modality, descriptors in [("touch", touch), ("smell", smell), ("taste", taste)]:
        for desc in descriptors:
            try:
                mid = deterministic_motif_id(f"{modality}_{desc}")
                chi = mid % 100
                _guala._atlas_record(
                    f"modal_{modality}", mid, chi,
                    _guala.tick, salience=1.2,
                    dwell_ticks=DWELL_GATE_META,
                    sensory_refs=[f"{modality}:{desc}"],
                    bundle_id=bundle_id, episode_ref=_bnd_ep_ref,
                    presence=_bnd_pres, location=_bnd_loc, sky_state=_bnd_sky,
                    source="bundle",
                    **_guala._affect_kwargs())
                n_chis += 1
            except Exception as e:
                results.append(f"{modality} ERROR ({desc}): {e}")
        if descriptors:
            results.append(f"{modality}: {', '.join(descriptors)}")

    tick_span = _guala.tick - base_tick
    _guala._log_substrate_event("experience_bundle",
                                name=bundle_name, lanes=results,
                                n_chis=n_chis, tick_span=tick_span)
    return {
        "response": f"experience \"{bundle_name}\": {'; '.join(results)}",
        "motifs": _guala.introspect()["vocab"],
        "bundle": {"name": bundle_name, "lanes": results, "n_chis": n_chis},
    }


def _cmd_listen(text, source):
    """Passive listening — read words into substrate without generating a response.
    Used for ambient audio (TV, room conversation, singing) that she should
    absorb but not try to respond to."""
    text = text.strip()
    if not text:
        return {"listened": True, "motifs": _guala.introspect()["vocab"]}
    if source not in {"joe", "wc", "c1"}:
        source = "joe"
    _guala.read_sentence(text, source=source)
    _guala.log_event(STATE_DIR, "passive_listen",
                     source=source, words_in=len(text.split()))
    _guala._log_substrate_event("passive_listen",
                                 source=source, text=text[:80],
                                 n_words=len(text.split()))
    return {"listened": True, "words": len(text.split()),
            "motifs": _guala.introspect()["vocab"]}


def _synthesize_voice(text):
    """Synthesize speech via espeak-ng. Returns base64 WAV or None."""
    if not text:
        return None
    # espeak-ng runs under a 5s timeout below; unbounded certified
    # continuations exceeded it and the whole voice went silent.  Bounded,
    # loud truncation instead (review 2026-07-16).  One authority for the
    # cap: the engine's TTS_MAX_CHARS.
    from dsf_ai_service.v4.gualaloom_v5_engine import TTS_MAX_CHARS
    if len(text) > TTS_MAX_CHARS:
        try:
            if _guala is not None:
                _guala._log_substrate_event(
                    "tts_truncated", where="converse_voice",
                    n_chars=len(text), cap=TTS_MAX_CHARS)
        except Exception:
            pass
        text = text[:TTS_MAX_CHARS]
    wav_path = "/tmp/guala_utt.wav"
    try:
        subprocess.run([
            "espeak-ng", "-v", "en+f3", "-p", "96", "-s", "145",
            "-w", wav_path, text,
        ], check=True, timeout=5, capture_output=True)
        with open(wav_path, "rb") as f:
            wav_bytes = f.read()
        return base64.b64encode(wav_bytes).decode("ascii")
    except Exception:
        return None


def _cmd_converse(text, source, emission_mode=None):
    """Run one conversation turn and transport the engine's emission truth.

    Guala.converse() is the sole authority for both content and source.  This
    interface must not manufacture fallback speech or impose a second commit
    policy after the field has settled.
    """
    text = text.strip()
    if not text:
        return {"response": "", "motifs": _guala.introspect()["vocab"],
                "response_source": "silence_empty_input"}
    # GL-CMD-AUTOMATED-TEACHING-20260717: "curriculum" is the tutor's own
    # honest identity — presence-exempt (engine keepalive no-ops for it),
    # background dwell, teacher weight 0.7 vs joe's 1.6.  It must never
    # masquerade as joe: coercing it would fake Joe's presence.
    if source not in {"joe", "wc", "c1", "curriculum"}:
        source = "joe"
    # GL-CMD-CROSS-MODAL-BUNDLE: auto-bundle words spoken while attending a sensory item.
    # Uses // 100 windowing so words close in time at the same target share one bundle.
    bundle_id = None
    ca = getattr(_guala, '_current_activity', None)
    if ca is not None and ca.target:
        if getattr(ca, 'kind', None) == "ATTENDING_VISUAL":
            bundle_id = f"context:pic:{ca.target}:{_guala.tick // 100}"
        elif getattr(ca, 'kind', None) == "ATTENDING_AUDIO":
            bundle_id = f"context:snd:{ca.target}:{_guala.tick // 100}"
    # GL-CMD-EPISODE-BINDING C2.1: situational context on every converse turn
    presence, location, sky_state = _guala._current_situation()

    # GL-CMD-WIRE-ORGAN-CANDIDATES-F2: organ candidate stream from cached surface.
    # Design choice: CACHED (not sync-per-turn). _ORGAN_SURFACE_CACHE is updated
    # every 90s by _start_organ_surface_poll(). Zero added latency per turn.
    # Staleness threshold: 180s (2× the autonomous loop interval).
    _organ_refs = []
    _cache_age = time.time() - _ORGAN_SURFACE_CACHE.get("ts", 0)
    if _cache_age < _ORGAN_SURFACE_STALE_S and _ORGAN_SURFACE_CACHE.get("surfaced"):
        _organ_refs = _translate_organ_surface(_ORGAN_SURFACE_CACHE["surfaced"])

    turn_result = _guala.converse(
        text, source=source, emission_mode=emission_mode,
        bundle_id=bundle_id, episode_ref=None,
        presence=presence, location=location, sky_state=sky_state,
        organ_candidates=_organ_refs if _organ_refs else None)
    response = turn_result.response
    response_source = turn_result.response_source
    # All-at-once doctrine (Joe 2026-07-16, "gibberish if that is what it
    # only knows"): when a HUMAN turn ends in silence, attempt an honest
    # organism babble before answering with nothing. Seeds are the turn's
    # own just-lived words (never atlas dumps); recall runs LOCK-FREE via
    # the two-phase precompute; the in-lock half is assembly only and the
    # conversation barrier is skipped because this IS the pending turn
    # (conversational=True). Label stays organism_attempt end-to-end.
    if (not response and response_source == "silence_no_commit"
            and os.environ.get("CONVERSE_BABBLE_FALLTHROUGH", "1") != "0"):
        try:
            _turn_seeds = [{"words": text.split()[:6],
                            "provenance": "conversation_turn_words"}]
            _released = None
            if _released is None:
                _votes = _guala.precompute_organism_attempt(_turn_seeds)
                if _votes is not None:
                    import time as _bt
                    with _guala.lock:
                        _released = _guala._compose_organism_attempt(
                            _turn_seeds, _bt.monotonic() + 0.25,
                            organism_votes=_votes, conversational=True)
            if _released is not None:
                # GL-FIX-FROZEN-TURNRESULT-20260718: the return dict below
                # is built from these LOCALS; TurnResult is frozen and the
                # old field assignments silently killed the whole
                # fall-through (live: every typed turn empty this morning).
                response = _released["content"]
                response_source = _released["response_source"]
        except Exception as _bab_e:
            print(f"[converse-babble] fall-through failed (honest silence "
                  f"kept): {_bab_e}", flush=True)
    committed_sections_out = list(turn_result.committed_sections)
    emission_id = turn_result.emission_id
    # GL-FIX-LOG-EFS-LATENCY: log_event writes to EFS (events.jsonl). On EFS
    # this can take 1-5s, blocking the /converse response. Defer to background thread.
    _src = source
    _words_in = len(text.split())
    _src_count = turn_result.source_turn_index
    import threading as _t
    _start_background_thread(
        lambda: _guala.log_event(
            STATE_DIR, "source_interaction",
            source=_src, words_in=_words_in, source_count=_src_count),
        "source-log")

    recalled_pics = turn_result.recalled_pictures
    picture_refs = []
    seen_ids = set()
    for motif, item_id in recalled_pics:
        if item_id in seen_ids:
            continue
        pic = _guala._pictures.get(item_id)
        if pic is None:
            continue
        seen_ids.add(item_id)
        picture_refs.append({"item_id": item_id, "title": pic.title})
        if len(picture_refs) >= 4:
            break
    result = {"response": response or "", "motifs": _guala.introspect()["vocab"],
              "response_source": response_source,
              "source_turn_index": turn_result.source_turn_index,
              "commit_provenance": [
                  provenance.as_record()
                  for provenance in turn_result.commit_provenance]}
    # Change 4 (spec v3 release-policy note a): ONE MOUTH — every released
    # label (certified AND assemblage) is voiced through this same TTS
    # boundary; the label itself stays distinct in result["response_source"].
    # Silence and retired legacy labels are never voiced.
    from dsf_ai_service.v4.gualaloom_v5_engine import VOICED_RELEASE_SOURCES
    if response and response_source in VOICED_RELEASE_SOURCES:
        wav = _synthesize_voice(response)
        if wav:
            result["speech"] = wav
    if committed_sections_out:
        result["committed_sections"] = committed_sections_out
    if emission_id:
        result["emission_id"] = emission_id
    if picture_refs:
        result["pictures"] = picture_refs
    return result


# ── Teacher correction handlers ────────────────────────────────

def handle_teacher_feedback(args):
    """POST /api/v1/teacher/feedback — positive signal."""
    emission_id = args.get("emission_id")
    source = args.get("source", "joe")
    if source not in ("joe", "wc"):
        return {"error": "invalid source"}

    with _guala.lock:
        causal_record = _guala._emission_records.get(emission_id)
    if (
        isinstance(causal_record, dict)
        and causal_record.get("response_source")
        == "causal_action_cycle_commit"
    ):
        try:
            return _guala.durably_review_causal_action_emission(
                emission_id=emission_id,
                correct=True,
                source=source,
                state_dir=STATE_DIR,
            )
        except (RuntimeError, ValueError) as error:
            return {"error": str(error)}

    rec = _guala._certified_emission_record(emission_id)
    if rec is None:
        return {"error": "emission is not source-certified"}
    original_input = rec.get("input_text", "")
    her_emission = rec.get("text", "")
    if not original_input or not her_emission:
        return {"error": "no conversation context"}

    result = _guala.apply_teacher_correction(
        original_input=original_input,
        her_emission=her_emission,
        correct=True,
        source=source,
        emission_id=emission_id,
    )
    import time as _time
    _guala._teaching_feedback_log.append({
        "emission_id": emission_id,
        "signal": "positive",
        "tick": _guala.tick,
        "source": source,
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "n_bindings_affected": result.get("n_affected", 0),
    })
    if len(_guala._teaching_feedback_log) > _guala.TEACHING_LOG_MAX:
        del _guala._teaching_feedback_log[0]
    return result


def handle_teacher_correction(args):
    """POST /api/v1/teacher/correction — negative + correction text."""
    emission_id = args.get("emission_id")
    corrected_text = args.get("corrected_text", "")
    story = args.get("story")
    temporal = args.get("temporal")
    sensory_freetext = args.get("sensory_freetext")
    source = args.get("source", "joe")
    if source not in ("joe", "wc"):
        return {"error": "invalid source"}
    if not corrected_text.strip():
        return {"error": "corrected_text required"}

    with _guala.lock:
        causal_record = _guala._emission_records.get(emission_id)
    if (
        isinstance(causal_record, dict)
        and causal_record.get("response_source")
        == "causal_action_cycle_commit"
    ):
        try:
            result = _guala.durably_review_causal_action_emission(
                emission_id=emission_id,
                correct=False,
                source=source,
                state_dir=STATE_DIR,
            )
        except (RuntimeError, ValueError) as error:
            return {"error": str(error)}
        result["corrected_text_learned"] = False
        result["correction_note"] = (
            "action revoked; corrected text requires a separately "
            "experienced spoken action"
        )
        return result

    rec = _guala._certified_emission_record(emission_id)
    if rec is None:
        return {"error": "emission is not source-certified"}
    original_input = rec.get("input_text", "")
    her_emission = rec.get("text", "")
    if not original_input or not her_emission:
        return {"error": "no conversation context"}

    result = _guala.apply_teacher_correction(
        original_input=original_input,
        her_emission=her_emission,
        correct=False,
        corrected_text=corrected_text,
        source=source,
        emission_id=emission_id,
        story=story,
        temporal=temporal,
        sensory_freetext=sensory_freetext,
    )
    # Sites 7+7b DELETE: _cognition_learn(corrected_text/story) removed.
    # apply_teacher_correction already writes v5 atlas with the correction.
    import time as _time
    _guala._teaching_correction_log.append({
        "emission_id": emission_id,
        "corrected_text": corrected_text,
        "story": story,
        "temporal": temporal,
        "sensory_freetext": sensory_freetext,
        "tick": _guala.tick,
        "source": source,
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "n_bindings_affected": result.get("n_affected", 0),
    })
    if len(_guala._teaching_correction_log) > _guala.TEACHING_LOG_MAX:
        del _guala._teaching_correction_log[0]
    return result


def handle_auditory_l5_status(args):
    """Return the bounded live auditory L5 and reciprocity state."""
    return _guala.auditory_l5_status()


def handle_observation_snapshot(args):
    """Return the one authoritative conversation/body/world observation."""
    return _guala.observation_snapshot()


def handle_auditory_l5_teach(args):
    """Bind a gateway-authenticated label to one exact auditory experience."""
    try:
        return _guala.teach_latest_auditory_experience(
            experience_id=args.get("experience_id"),
            kind=args.get("kind"),
            tutor_label=args.get("tutor_label"),
            authority_receipt=args.get("authority_receipt"),
        )
    except (RuntimeError, ValueError) as error:
        return {"error": str(error)}


# ── Curriculum ops ─────────────────────────────────────────────

# Corpus load results — populated by background thread, polled via corpus_status.
# Key: corpus_id, Value: result dict (with status="queued"|"running"|"complete"|"failed")
_corpus_load_results = {}

# Refcounted autonomy pause (GL-CMD-74).
# Multiple callers (load_corpus, sleep_for_deploy, manual) cooperate.
# Autonomy resumes only when the count returns to 0.
_autonomy_pause_refcount = 0
_autonomy_refcount_lock = threading.Lock()


def _pause_autonomy_for_bulk():
    """Increment pause refcount. Pauses autonomy loop on first call."""
    global _autonomy_pause_refcount
    with _autonomy_refcount_lock:
        _autonomy_pause_refcount += 1
        if _autonomy_pause_refcount == 1:
            _guala._reading_stop.set()
            time.sleep(0.3)  # let any in-progress tick finish
            print(f"[autonomy] Paused (refcount=1)")


def _resume_autonomy_for_bulk():
    """Decrement pause refcount. Restarts autonomy loop when count reaches 0."""
    global _autonomy_pause_refcount
    with _autonomy_refcount_lock:
        _autonomy_pause_refcount = max(0, _autonomy_pause_refcount - 1)
        if _autonomy_pause_refcount == 0:
            _guala._reading_stop.clear()
            # GL-CMD-AUTONOMY-EMITTING-PHASING-55: guard against double-loop.
            # Only start a new thread if the existing one is dead or absent.
            # Without this, curriculum resume spawns a second autonomy thread,
            # causing two concurrent _autonomy_tick calls that starve /converse.
            _rt = getattr(_guala, '_reading_thread', None)
            if not (_rt and _rt.is_alive()):
                _guala.start_autonomy_loop(interval=0.2)
            print(f"[autonomy] Resumed (refcount=0)")
        else:
            print(f"[autonomy] Resume deferred (refcount={_autonomy_pause_refcount})")


def _do_corpus_load(corpus_id, title, lines, vocab_before, reads_before, strength_before):
    """Background thread: feed sentences, update progress, resume autonomy."""
    _corpus_load_results[corpus_id]["status"] = "running"
    errors = []
    n_fed = 0
    n_total = len(lines)
    vocab_before = len(_guala.vocab) if _guala is not None else 0
    try:
        for sent in lines:
            try:
                _guala.read_sentence(sent, source="corpus")
                # Site 8 DELETE: _cognition_learn(sent) removed (v5 atlas gets this above)
                _bind_sensory_words(sent)  # and feels/smells/tastes the sensory words
                n_fed += 1
                # Progress update every 10 sentences (or every sentence if small)
                if n_total < 20 or n_fed % 10 == 0:
                    _corpus_load_results[corpus_id]["n_fed"] = n_fed
            except Exception as e:
                errors.append(f"{sent[:40]!r}: {e}")
    finally:
        # Resume autonomy via refcount — always, even on error
        _resume_autonomy_for_bulk()

    vocab_after = len(_guala.vocab) if _guala is not None else 0
    reads_after = _guala.read_count
    strength_after = round(_guala.atlas.total_strength(), 4)

    _guala._log_substrate_event(
        "curriculum_loaded",
        corpus_id=corpus_id,
        title=title,
        n_sentences=n_fed,
        n_new_vocab=vocab_after - vocab_before,
        reads_delta=reads_after - reads_before,
        atlas_strength_delta=round(strength_after - strength_before, 4),
        vocab_delta=vocab_after - vocab_before,
    )
    print(f"[corpus] '{corpus_id}': v5 vocab {vocab_before}->{vocab_after} (+{vocab_after - vocab_before})")

    result = {
        "status": "complete",
        "corpus_id": corpus_id,
        "n_sentences": n_fed,
        "n_fed": n_fed,
        "n_total": n_total,
        "n_new_vocab": vocab_after - vocab_before,
        "reads_delta": reads_after - reads_before,
        "atlas_strength_before": strength_before,
        "atlas_strength_after": strength_after,
        "atlas_strength_delta": round(strength_after - strength_before, 4),
        "vocab_before": vocab_before,
        "vocab_after": vocab_after,
    }
    if errors:
        result["errors"] = errors[:5]
    _corpus_load_results[corpus_id] = result
    print(f"[corpus] Load complete: corpus_id={corpus_id} n_fed={n_fed} "
          f"n_new_vocab={vocab_after - vocab_before} "
          f"reads_delta={reads_after - reads_before}")


def handle_load_corpus(args):
    """GL-CMD-73: Load a pre-parsed corpus into the substrate.

    Fire-and-forget: returns immediately with status="queued".
    The actual read_sentence loop runs in a background thread to avoid
    exceeding the ALB 180s gateway timeout (O(n_modes) section scan
    on 3K+ vocab takes 60-120s for 107 sentences).

    Use handle_corpus_status to poll for completion.

    Args (pre-processed by app.py — no network IO here):
        corpus_id : str  — unique identifier
        title     : str  — display title
        lines     : list — sentence-level strings from the adapter

    Returns immediately:
        status="queued", corpus_id, n_sentences, vocab_before
    """
    corpus_id = args.get("corpus_id", "").strip()
    title = args.get("title", "").strip()
    lines = args.get("lines", [])

    if not corpus_id:
        return {"error": "corpus_id required"}
    if not lines:
        return {"error": "no lines provided"}

    # If already loading, return current status
    existing = _corpus_load_results.get(corpus_id, {})
    if existing.get("status") in ("loading", "queued"):
        return existing

    vocab_before = len(_guala.vocab)
    reads_before = _guala.read_count
    strength_before = round(_guala.atlas.total_strength(), 4)

    # Register corpus for autonomous reading (overwrites if same corpus_id exists)
    _guala.add_corpus(corpus_id, title, lines)

    # Mark as queued before starting thread so status is visible immediately
    _corpus_load_results[corpus_id] = {
        "status": "queued",
        "corpus_id": corpus_id,
        "n_sentences": len(lines),
        "n_fed": 0,
        "vocab_before": vocab_before,
    }

    # Pause autonomy via refcount BEFORE spawning thread.
    # _do_corpus_load's finally block calls _resume_autonomy_for_bulk().
    _pause_autonomy_for_bulk()

    _start_background_thread(
        lambda: _do_corpus_load(
            corpus_id, title, lines, vocab_before, reads_before,
            strength_before),
        f"corpus-load-{corpus_id}",
    )

    return {
        "status": "queued",
        "corpus_id": corpus_id,
        "n_sentences": len(lines),
        "vocab_before": vocab_before,
        "message": "Loading started in background. Poll corpus_status to check completion.",
    }


def handle_corpus_status(args):
    """Poll the status of an in-progress or completed corpus load."""
    corpus_id = args.get("corpus_id", "").strip()
    if not corpus_id:
        return {"error": "corpus_id required"}
    result = _corpus_load_results.get(corpus_id)
    if result is None:
        return {"status": "not_found", "corpus_id": corpus_id}
    return result


# ── Admin ops ──────────────────────────────────────────────────

def handle_amnesty(args):
    tick = _guala.tick
    total_before = round(_guala.atlas.total_strength(), 4)
    count = _guala.atlas.amnesty(tick)
    total_after = round(_guala.atlas.total_strength(), 4)
    _guala._log_substrate_event("amnesty_complete", entries_restamped=count,
                                 tick=tick, strength_before=total_before,
                                 strength_after=total_after)
    print(f"[UNPAUSE] Amnesty: {count} entries re-stamped to tick {tick}")
    return {"amnesty": "complete", "entries_restamped": count, "tick": tick,
            "total_strength_before": total_before,
            "total_strength_after": total_after}


def handle_force_dream(args):
    _guala._force_next_activity = ("SLEEPING", None)
    if _guala._current_activity:
        _guala._end_activity()
    _guala._log_substrate_event("force_dream_initiated", tick=_guala.tick)
    print(f"[UNPAUSE] Force dream initiated at tick {_guala.tick}")
    start_tick = _guala.tick
    for _ in range(120):
        time.sleep(0.5)
        activity = _guala._current_activity
        if activity and activity.kind == "DREAMING":
            continue
        if activity is None or activity.kind != "SLEEPING":
            events = _guala.get_recent_events(since_tick=start_tick, limit=50)
            dream_events = [e for e in events if e.get("kind") in
                           ("dream_began", "dream_artifact", "dream_promotion",
                            "deep_atlas_promotion")]
            # Write dream gate marker so next boot allows decay
            gate_path = os.path.join(STATE_DIR, "dream_gate_cleared.json")
            with open(gate_path, "w") as f:
                json.dump({"cleared_at_tick": _guala.tick,
                           "dream_events": len(dream_events)}, f)
                f.flush(); os.fsync(f.fileno())
            print(f"[UNPAUSE] Dream gate marker written: {gate_path}")
            return {"force_dream": "complete", "tick": _guala.tick,
                    "dream_events": dream_events[-10:],
                    "n_events": len(dream_events)}
    return {"force_dream": "timeout", "tick": _guala.tick,
            "current_activity": _guala._current_activity.kind if _guala._current_activity else None}


def handle_force_reading(args):
    """GL-CMD-SCENE-LANES-B1-188 follow-up (c1b's handoff, standing build
    item): a specific corpus can be tested on demand, mirroring
    handle_force_dream's _force_next_activity pre-emption exactly -- no
    new mechanism, same existing override _select_next_activity already
    checks first. corpus_id (exact) or title_contains (substring, case-
    insensitive) selects the target; corpus_id wins if both given."""
    corpus_id = (args.get("corpus_id") or "").strip()
    title_contains = (args.get("title_contains") or "").strip().lower()
    target = None
    if corpus_id and corpus_id in _guala._corpora:
        target = corpus_id
    elif title_contains:
        for cid, c in _guala._corpora.items():
            if title_contains in c.title.lower():
                target = cid
                break
    if target is None:
        return {"force_reading": "no_match", "corpus_id": corpus_id,
                "title_contains": title_contains,
                "available": [{"corpus_id": cid, "title": c.title}
                              for cid, c in _guala._corpora.items()]}
    start_tick = _guala.tick
    _guala._force_next_activity = ("READING", target)
    if _guala._current_activity:
        _guala._end_activity()
    _guala._log_substrate_event("force_reading_initiated", tick=start_tick,
                                corpus_id=target)
    print(f"[UNPAUSE] Force reading initiated: corpus_id={target} at tick {start_tick}")
    return {"force_reading": "accepted", "corpus_id": target,
            "title": _guala._corpora[target].title, "start_tick": start_tick}


def handle_repause(args):
    os.environ["DECAY_PAUSED"] = "1"
    _write_runtime_config({"decay_paused": True})
    if _guala:
        _guala._log_substrate_event("decay_repaused", tick=_guala.tick,
                                     reason="manual_kill_switch")
    print(f"[UNPAUSE] KILL SWITCH: decay re-paused (persisted)")
    return {"repause": "active", "DECAY_PAUSED": "1", "persisted": True}


def handle_unpause(args):
    gate_path = os.path.join(STATE_DIR, "dream_gate_cleared.json")
    if not os.path.exists(gate_path):
        return {"error": "dream_gate_not_cleared",
                "message": "Cannot unpause without prior dream completion. "
                           "Call force_dream first; gate marker is written "
                           "by substrate when DREAMING activity ends naturally."}
    os.environ["DECAY_PAUSED"] = "0"
    _write_runtime_config({"decay_paused": False})
    tick = _guala.tick if _guala else 0
    if _guala:
        _guala._log_substrate_event("decay_unpaused", tick=tick,
                                     reason="admin_unpause")
    print(f"[UNPAUSE] Decay unpaused at tick {tick} (persisted)")
    return {"unpaused": True, "tick": tick, "persisted": True}


def handle_wake(args):
    """Force wake from sleep state."""
    if _guala and _guala.is_asleep:
        _guala.wake_from_sleep(state_dir=STATE_DIR)
        print(f"[substrate] Woke from sleep at tick {_guala.tick}")
        return {"woke": True, "tick": _guala.tick}
    return {"woke": False, "already_awake": True, "tick": _guala.tick if _guala else 0}


def handle_atlas_snapshot(args):
    dist = _guala.atlas.strength_distribution()
    return {
        "tick": _guala.tick,
        "total_strength": round(_guala.atlas.total_strength(), 2),
        "n_live_bindings": _guala.atlas.n_live_bindings(),
        "n_total_entries": sum(len(v) for v in _guala.atlas.entries.values()),
        "strength_distribution": dist,
        "decay_paused": os.environ.get("DECAY_PAUSED", "0"),
    }


def handle_chi_density(args):
    result = {}
    for chi_key, entries in _guala.atlas.entries.items():
        if not entries:
            continue
        n = len(entries)
        s = sum(e.get("strength", 0.0) for e in entries)
        result[str(chi_key)] = {"n": n, "strength": round(s, 3)}
    return {"tick": _guala.tick, "chi_density": result}


def handle_backup(args):
    """Save locally and report remote persistence only when it was enabled."""
    from dsf_ai_service.save_coordinator import SAVE_COORDINATOR
    t0 = time.time()
    s3_enabled = bool(
        SAVE_COORDINATOR is not None
        and getattr(SAVE_COORDINATOR, "s3_bucket", None))
    if SAVE_COORDINATOR:
        SAVE_COORDINATOR.force_save(reason="backup")
    else:
        _guala.save_full_state(STATE_DIR)
    n_entries = sum(len(v) for v in _guala.atlas.entries.values())
    dt = time.time() - t0
    # GL-CMD-PRESURGERY-FRESHNESS-22: update freshness wall on any successful save
    global _last_successful_backup_wall
    with _backup_lock:
        _last_successful_backup_wall = time.time()
    storage_scope = "local-and-s3-queued" if s3_enabled else "local-only"
    s3_status = "queued" if s3_enabled else "disabled"
    print(
        f"[backup] local save complete in {dt:.2f}s, {n_entries} entries, "
        f"storage={storage_scope}")
    return {"backup": "complete", "save_time_s": round(dt, 2),
            "atlas_entries": n_entries, "tick": _guala.tick,
            "storage": storage_scope, "s3": s3_status}


def handle_sight_frame(args):
    """Transient camera frame into raw sight; object naming is unavailable."""
    import base64
    from dsf_ai_service.substrate.grounded_vocab_integration import (
        object_name_recognition_unavailable)

    recognition = object_name_recognition_unavailable(
        source=args.get("source", "camera_stream"))
    b64_data = (args.get("text") or "").strip()
    if not b64_data:
        return {"ok": False, "error": "no frame data",
                "object_name_recognition": recognition}
    t0 = time.time()
    try:
        img_bytes = base64.b64decode(b64_data)
        from dsf_ai_service.app import decode_image_bytes
        _, grid, _, _ = decode_image_bytes(img_bytes)
        _guala.process_sight_frame(grid)
        recognition = object_name_recognition_unavailable(
            _guala, source=args.get("source", "camera_stream"))
        # Publish to ring
        if _substrate_ring is not None:
            _substrate_ring.publish("sight_frame", _guala.tick,
                                    raw_sight="accepted",
                                    object_name_recognition="unavailable")
        dt = time.time() - t0
        if dt > 0.5:
            print(f"[sight-frame] {dt:.3f}s (slow)")
        return {"ok": True, "tick": _guala.tick,
                "raw_sight": "accepted",
                "object_name_recognition": recognition}
    except Exception as e:
        return {"ok": False, "error": str(e),
                "object_name_recognition": recognition}


def handle_sound_frame(args):
    """Transient mic audio into raw sound; word recognition is unavailable."""
    import base64
    from dsf_ai_service.substrate.grounded_vocab_integration import (
        spoken_word_recognition_unavailable)

    b64_data = (args.get("text") or "").strip()
    source = args.get("source", "ambient")
    recognition = spoken_word_recognition_unavailable(source=source)
    if not b64_data:
        return {"ok": False, "error": "no audio data",
                "spoken_word_recognition": recognition}
    t0 = time.time()
    try:
        audio_bytes = base64.b64decode(b64_data)
        wav = _webm_to_wav_bytes(audio_bytes)
        if not wav:
            return {"ok": False, "error": "decode_failed",
                    "spoken_word_recognition": recognition}
        _guala.process_sound_frame(wav, source=source)
        recognition = spoken_word_recognition_unavailable(
            _guala, source=source)
        # Publish to ring
        if _substrate_ring is not None:
            _substrate_ring.publish(
                "sound_frame", _guala.tick, source=source,
                raw_sound="accepted", spoken_word_recognition="unavailable")
        return {"ok": True, "tick": _guala.tick,
                "raw_sound": "accepted",
                "spoken_word_recognition": recognition}
    except Exception as e:
        return {"ok": False, "error": str(e),
                "spoken_word_recognition": recognition}


def handle_sleep_for_deploy(args):
    _pause_autonomy_for_bulk()
    try:
        _guala.manual_sleep(state_dir=STATE_DIR)
    except Exception as e:
        print(f"[sleep_for_deploy] manual_sleep failed: {e}")
        _resume_autonomy_for_bulk()
        return {"ok": False, "error": str(e), "tick": _guala.tick}
    # Don't resume autonomy — she's sleeping. The new task wakes her.
    return {"ok": True, "sleep_tick": _guala.tick, "vocab": len(_guala.vocab)}


def handle_status_simple(args):
    """Simple status for /ready-equivalent queries."""
    return {
        "ready": True,
        "vocab": len(_guala.vocab),
        "tick": _guala.tick,
        "asleep": _guala.is_asleep,
    }


# ── Cascade monitor ──────────────────────────────────────────────

_cascade_monitor_running = False
_cascade_baseline = None


def _cascade_monitor_loop(baseline, interval):
    """Background thread: polls atlas health, auto-repauses on violation.
    Runs inside substrate process where _guala and DECAY_PAUSED are live."""
    global _cascade_monitor_running
    print(f"[CASCADE] Monitor started: bindings={baseline['n_bindings']} "
          f"strength={baseline['strength']:.1f} saturated={baseline['saturated']} "
          f"interval={interval}s")
    while _cascade_monitor_running:
        if _shutdown_event.wait(interval):
            break
        if _guala is None or not _cascade_monitor_running:
            continue
        try:
            n_bindings = _guala.atlas.n_live_bindings()
            total_str = _guala.atlas.total_strength()
            dist = _guala.atlas.strength_distribution()
            saturated = dist.get("0.9-1.0", 0)
            violations = []
            if n_bindings < 0.80 * baseline["n_bindings"]:
                violations.append(f"n_bindings {n_bindings} < 80% of {baseline['n_bindings']}")
            if total_str < 0.70 * baseline["strength"]:
                violations.append(f"total_strength {total_str:.1f} < 70% of {baseline['strength']:.1f}")
            if baseline["saturated"] > 0 and saturated < 0.90 * baseline["saturated"]:
                violations.append(f"saturated {saturated} < 90% of {baseline['saturated']}")
            if violations:
                os.environ["DECAY_PAUSED"] = "1"
                _write_runtime_config({"decay_paused": True})
                reason = "; ".join(violations)
                _guala._log_substrate_event("cascade_auto_triggered",
                                             tick=_guala.tick, violations=violations,
                                             n_bindings=n_bindings,
                                             total_strength=round(total_str, 2),
                                             saturated=saturated)
                print(f"[CASCADE] AUTO-REPAUSE TRIGGERED: {reason}")
                _cascade_monitor_running = False
                return
            print(f"[CASCADE] OK: bindings={n_bindings} str={total_str:.1f} sat={saturated}")
        except Exception as e:
            print(f"[CASCADE] Monitor error: {e}")
    print(f"[CASCADE] Monitor stopped")


def handle_start_cascade_monitor(args):
    global _cascade_monitor_running, _cascade_baseline
    if _cascade_monitor_running:
        return {"error": "monitor already running"}
    baseline = {
        "n_bindings": args.get("baseline_n_bindings", 0),
        "strength": float(args.get("baseline_strength", 0)),
        "saturated": args.get("baseline_saturated", 0),
    }
    interval = max(5, args.get("interval_s", 10))
    _cascade_baseline = baseline
    _cascade_monitor_running = True
    _start_background_thread(
        lambda: _cascade_monitor_loop(baseline, interval),
        "cascade-monitor")
    return {"cascade_monitor": "started", "baseline": baseline, "interval_s": interval}


def handle_stop_cascade_monitor(args):
    global _cascade_monitor_running
    _cascade_monitor_running = False
    return {"cascade_monitor": "stopped"}


def handle_ring_status(args):
    """Return ring buffer status for monitoring."""
    if _substrate_ring is None:
        return {"ring": "not_initialized"}
    return {
        "ring": "active",
        "published_seq": _substrate_ring._published_seq,
        "size": _substrate_ring._size,
        "input_pending": _input_ring.pending if _input_ring else 0,
        "input_pending_transport_bytes": (
            _input_ring.pending_transport_bytes if _input_ring else 0),
        "input_max_pending_transport_bytes": (
            _input_ring.max_pending_transport_bytes if _input_ring else 0),
        "input_rejected_events": (
            _input_ring.rejected_events if _input_ring else 0),
        "input_overrun_recoveries": (
            _input_ring.overrun_recoveries if _input_ring else 0),
    }


def handle_ring_write(args):
    """Admit one inbound event or report the exact capacity refusal."""
    if _input_ring is None:
        return {"ok": False, "error": "input ring not initialized"}
    from dsf_ai_service.substrate.ring_buffer import InputRingCapacityError
    try:
        seq = _input_ring.publish(
            args.get("kind", "text_input"),
            args.get("source", "bridge"),
            **{
                key: value
                for key, value in args.get("data", {}).items()
                if key != "source"
            },
        )
    except InputRingCapacityError as error:
        return {
            "ok": False,
            "error": str(error),
            "input_pending": _input_ring.pending,
            "input_pending_transport_bytes": (
                _input_ring.pending_transport_bytes),
            "input_max_pending_transport_bytes": (
                _input_ring.max_pending_transport_bytes),
            "input_rejected_events": _input_ring.rejected_events,
        }
    return {"ok": True, "seq": seq}


# ── Backfill ops (GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04) ─────

def handle_backfill_picture_titles(args):
    """One-shot: feed each picture's title into the language substrate bundled
    to its item:pic:<id> so sight+language entries share a bundle_id group.
    salience=1.5 compensates for pictures attended thousands of times without
    their titles ever landing. Idempotent via last-write-wins reinforce path."""
    fed, skipped = 0, 0
    max_strength_seen = 0.0
    STRENGTH_CAP = 1.0
    for pic_id, pic in list(_guala._pictures.items()):
        title = (getattr(pic, 'title', None) or "").strip()
        if not title:
            skipped += 1
            continue
        try:
            _, _loc, _sky = _guala._current_situation()
            _guala.read_sentence(title,
                                 source="addpicture_backfill",
                                 bundle_id=f"item:pic:{pic_id}",
                                 salience=1.5,
                                 episode_ref=f"episode:backfill_pic:{pic_id}",
                                 presence=[], location=_loc, sky_state=_sky)
            # Track max atlas strength to confirm no STRENGTH_CAP saturation
            lang_words = title.lower().split()
            for w in lang_words:
                for chi_entries in _guala.atlas.entries.values():
                    for e in chi_entries:
                        if e.get("source") == "addpicture_backfill":
                            max_strength_seen = max(max_strength_seen, e["strength"])
            fed += 1
        except Exception as exc:
            print(f"[backfill_picture_titles] ERROR pic_id={pic_id} title={title!r}: {exc}")
    _guala._log_substrate_event("backfill_picture_titles_complete",
                                fed=fed, skipped=skipped,
                                total_pictures=len(_guala._pictures),
                                max_strength_seen=round(max_strength_seen, 4))
    print(f"[backfill_picture_titles] fed={fed} skipped={skipped} "
          f"max_strength={max_strength_seen:.4f}")
    return {
        "fed": fed, "skipped": skipped,
        "total_pictures": len(_guala._pictures),
        "max_strength_seen": round(max_strength_seen, 4),
        "strength_cap": STRENGTH_CAP,
        "cap_breach": max_strength_seen >= STRENGTH_CAP,
    }


def handle_backfill_sound_captions(args):
    """One-shot: feed each sound's title caption into the language substrate
    bundled to its item:snd:<id>. Sounds added before B1.c had cochlear entries
    tagged but no language caption bundle_id. Last-write-wins reinforce path
    tags existing caption entries with the correct bundle_id."""
    fed, skipped = 0, 0
    max_strength_seen = 0.0
    STRENGTH_CAP = 1.0
    for snd_id, snd in list(_guala._sounds.items()):
        caption = (snd.get("title") or "").strip()
        if not caption:
            skipped += 1
            continue
        try:
            _, _loc, _sky = _guala._current_situation()
            _guala.read_sentence(caption,
                                 source="addsound_backfill",
                                 bundle_id=f"item:snd:{snd_id}",
                                 salience=1.5,
                                 episode_ref=f"episode:backfill_snd:{snd_id}",
                                 presence=[], location=_loc, sky_state=_sky)
            for chi_entries in _guala.atlas.entries.values():
                for e in chi_entries:
                    if e.get("source") == "addsound_backfill":
                        max_strength_seen = max(max_strength_seen, e["strength"])
            fed += 1
        except Exception as exc:
            print(f"[backfill_sound_captions] ERROR snd_id={snd_id} caption={caption!r}: {exc}")
    _guala._log_substrate_event("backfill_sound_captions_complete",
                                fed=fed, skipped=skipped,
                                total_sounds=len(_guala._sounds),
                                max_strength_seen=round(max_strength_seen, 4))
    print(f"[backfill_sound_captions] fed={fed} skipped={skipped} "
          f"max_strength={max_strength_seen:.4f}")
    return {
        "fed": fed, "skipped": skipped,
        "total_sounds": len(_guala._sounds),
        "max_strength_seen": round(max_strength_seen, 4),
        "strength_cap": STRENGTH_CAP,
        "cap_breach": max_strength_seen >= STRENGTH_CAP,
    }


# ── F.2: Organ surface cache + translation ── GL-CMD-WIRE-ORGAN-CANDIDATES-31 ──

_ORGAN_BRAIN_URL = os.environ.get("ORGAN_BRAIN_URL", "http://localhost:8090")
_ORGAN_SURFACE_CACHE = {"surfaced": {}, "ts": 0.0, "n_surface": 0, "n_translated": 0}
_ORGAN_SURFACE_STALE_S = 180.0   # treat cached surface as empty if >180s old


def _translate_organ_surface(surfaced: dict) -> list:
    """Inline F.1 translation: concept strings → deep_atlas BindingRefs.
    Called from _cmd_converse with the cached organ surface.
    Returns list of (entry_dict, co_occurrence, clarity) tuples."""
    if not surfaced or _guala is None:
        return []
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
    concepts = list(surfaced.get("identity") or []) + list(surfaced.get("meaning") or [])
    if not concepts:
        return []
    result = []
    n_translated = 0
    n_missed = 0
    band = getattr(_guala.atlas, 'band', 2)
    for concept in concepts:
        if not concept or concept not in _guala.vocab:
            n_missed += 1
            continue
        try:
            krim = LanguageKrimelack()
            krim.transduce(concept)
            chi = krim.winding
        except Exception:
            n_missed += 1
            continue
        found = 0
        for d in range(-band, band + 1):
            for de in _guala.deep_atlas.entries.get(chi + d, []):
                if de.get("strength", 0) < 0.02:
                    continue
                co = de.get("co_occurrence", {})
                if co:
                    result.append((de, co, de.get("clarity", 0.3)))
                    found += 1
        if found > 0:
            n_translated += 1
        else:
            n_missed += 1
    # Update cache stats for step-5 measurement
    _ORGAN_SURFACE_CACHE["n_surface"] = len(concepts)
    _ORGAN_SURFACE_CACHE["n_translated"] = n_translated
    if concepts:
        try:
            _guala._log_substrate_event("organ_f2_translation",
                                        n_concepts_in=len(concepts),
                                        n_translated=n_translated,
                                        n_missed=n_missed,
                                        drift_rate=round(n_missed/len(concepts), 3))
        except Exception:
            pass
    return result


def _start_organ_surface_poll():
    """Background thread: polls organ_brain_service /thought every 90s.
    F.2 design choice: CACHED from autonomous loop (not sync per-turn).
    Rationale: zero added latency per converse; staleness ≤180s matches
    the 90s autonomous loop interval × 2. OrganVoice updates _last_thought
    every 90s; we read it here and cache for substrate use."""
    def _poll():
        import urllib.request as _ur
        import json as _js
        while not _shutdown:
            try:
                req = _ur.Request(f"{_ORGAN_BRAIN_URL}/thought",
                                  headers={"accept": "application/json"})
                resp = _ur.urlopen(req, timeout=5)
                data = _js.loads(resp.read())
                surfaced = data.get("surfaced", {})
                if surfaced:
                    _ORGAN_SURFACE_CACHE["surfaced"] = surfaced
                    _ORGAN_SURFACE_CACHE["ts"] = time.time()
            except Exception:
                pass
            if _shutdown_event.wait(90):
                break
    _start_background_thread(_poll, "organ-surface-poll")
    print("[organ-f2] surface poll started (90s interval)")


# ── GL-CMD-AUTONOMOUS-EMISSION-39 ──────────────────────────────────────────

_last_autonomous_thought = {"speech": "", "tick": 0, "ts": 0.0}
_autonomous_thought_lock = threading.Lock()


def _start_autonomous_emission_loop():
    """Background daemon: attempts autonomous emission every 90s.
    Uses compose_autonomous() — the SAME release policy as /converse
    (Change 4): certified composer first, queried with organism-sourced
    seeds (recent committed window words / current activity target — never
    atlas dumps), the substrate's own assemblage commit second, explained
    silence third.  Stores result in _last_autonomous_thought for /thought
    polling."""
    def _loop():
        global _last_autonomous_thought
        if _shutdown_event.wait(60):
            return
        while not _shutdown:
            try:
                # GL-CMD-CAMERA-TURN-LATENCY: this loop is the worst self.lock
                # offender -- it holds the lock across the FULL six-section
                # compose_autonomous() (measured 49-94s live). If a live human
                # interaction is pending, defer this whole cycle rather than
                # start a fresh long lock-hold in front of the waiting turn.
                # The loop already retries on its own 90s cadence, so a
                # deferred cycle simply runs next time -- background emission
                # is never dropped, only postponed until the exact end of the
                # balanced live-interaction scope.
                if (_guala is not None
                        and not _guala._defer_for_live_interaction(
                            "autonomous_emission")):
                    should = False
                    with _guala.lock:
                        should = _guala._should_attempt_autonomous_emission()
                    if should:
                        # F3 (2026-07-16): two-phase compose. Seeds are
                        # snapshotted under a SHORT hold, the organism
                        # recall (duration-unbounded) runs with NO lock,
                        # and the final compose under the lock is assembly
                        # only -- it refuses to recall by contract
                        # (votes_not_precomputed).
                        seed_attempts = None
                        with _guala.lock:
                            seed_attempts = (
                                _guala._autonomous_composer_seed_attempts())
                        organism_votes = _guala.precompute_organism_attempt(
                            seed_attempts)
                        result = None
                        with _guala.lock:
                            result = _guala.compose_autonomous(
                                seed_attempts=seed_attempts,
                                organism_votes=organism_votes,
                                proposal=None)
                        # GL-FIX-SECOND-CHANCE-SEEDS-20260717: live histogram
                        # showed 7/8 autonomous attempts dying organism_empty —
                        # window-derived seeds are sensory-frame dominated now
                        # (5823 organism_experience_bound vs a handful of word
                        # events in the same span), so the vote merge finds
                        # nothing.  When the whole compose refused AND the
                        # organism voted empty, retry ONCE with her most
                        # recent READ sentence — her own reading life, not an
                        # atlas dump (the documented regression class).
                        if result is None:
                            try:
                                _m = (organism_votes or {}).get("merged")
                                if (_m is None or not _m) and len(_GAP_ARCHIVE):
                                    _fb = [{"words": list(_GAP_ARCHIVE)[-1]
                                            .split()[:6],
                                            "provenance":
                                                "recent_reading_fallback"}]
                                    _fb_votes = (
                                        _guala.precompute_organism_attempt(_fb))
                                    if _fb_votes and _fb_votes.get("merged"):
                                        with _guala.lock:
                                            result = _guala.compose_autonomous(
                                                seed_attempts=_fb,
                                                organism_votes=_fb_votes)
                            except Exception as _sc_e:
                                print(f"[autonomous] second-chance seeds "
                                      f"failed (non-fatal): {_sc_e}",
                                      flush=True)
                        if result is not None:
                            content = result["content"]
                            _guala.autonomous_emissions_count += 1
                            autonomous_emission_id = (
                                f"autonomous:{_guala.autonomous_emissions_count}:"
                                f"{result['settlement_tick']}")
                            _guala.last_autonomous_emission_tick = _guala.tick
                            _guala._log_substrate_event(
                                "autonomous_emission",
                                content=content,
                                emission_id=autonomous_emission_id,
                                response_source=result["response_source"],
                                committed_sections=result["committed_sections"],
                                commit_provenance=result["commit_provenance"],
                                # Two seed semantics, two keys (review
                                # 2026-07-16): certified releases count seed
                                # WORDS; assemblage releases count chi seeds.
                                seed_words_used=result.get(
                                    "seed_words_used", 0),
                                chi_seeds_used=result.get(
                                    "chi_seeds_used", 0),
                                # Change 4: certified autonomous releases
                                # carry organism-sourced seed provenance
                                # (window/activity origins, never atlas).
                                seed_provenance=result.get(
                                    "seed_provenance", []),
                                count=_guala.autonomous_emissions_count,
                            )
                            with _autonomous_thought_lock:
                                _last_autonomous_thought = {
                                    "speech": content,
                                    "tick": _guala.tick,
                                    "ts": time.time(),
                                    "category": "autonomous",
                                    "source": "guala",
                                    "response_source": result["response_source"],
                                    "emission_id": autonomous_emission_id,
                                    "committed_sections": result["committed_sections"],
                                    "commit_provenance": result["commit_provenance"],
                                }
                            # One mouth (Change 4): every released label —
                            # fact_strand_commit AND assemblage_commit —
                            # self-hears through the same engine boundary as
                            # conversational emission; never raw re-ingest.
                            # _self_hear itself gates on
                            # VOICED_RELEASE_SOURCES and keeps the label
                            # distinct in its telemetry.
                            try:
                                _guala._self_hear(
                                    content, "guala",
                                    emission_id=autonomous_emission_id,
                                    response_source=result["response_source"])
                            except Exception as self_hear_error:
                                _guala._log_substrate_event(
                                    "autonomous_self_hear_error",
                                    emission_id=autonomous_emission_id,
                                    error=str(self_hear_error))
                            # Agency organ writes
                            try:
                                if _guala_organ_brain is not None:
                                    ab = _guala_organ_brain["atlas_by_organ"]
                                    ab["sv"] = ab.get("sv", 0) + 1
                                    ab["gp"] = ab.get("gp", 0) + 1
                                    ab["aff"] = ab.get("aff", 0) + 1
                                    if _guala.autonomous_emissions_count % 5 == 0:
                                        ab["sf"] = ab.get("sf", 0) + 1
                            except Exception:
                                pass
                        else:
                            _guala.last_autonomous_attempt_tick = _guala.tick
                            _guala._log_substrate_event(
                                "autonomous_attempt_no_commit",
                                needs=_guala.needs.snapshot(),
                            )
            except Exception as _e:
                try:
                    _guala._log_substrate_event("autonomous_emission_error",
                                                error=str(_e))
                except Exception:
                    pass
            if _shutdown_event.wait(90):
                break
    _start_background_thread(_loop, "autonomous-emission")
    print("[autonomous] emission loop started (90s interval)")


def _cmd_thought():
    """Return the most recent autonomous thought for UI polling."""
    with _autonomous_thought_lock:
        t = dict(_last_autonomous_thought)
    return t


# ── B.1: Atlas surgery ── GL-CMD-ATLAS-SURGERY-EVE-20260627-18 ───
# ── B.2 freshness gate ── GL-CMD-PRESURGERY-FRESHNESS-EVE-20260627-22 ──

import re as _re

_SURGERY_CACHE = {}        # operation_id → response (idempotency)
_SURGERY_CACHE_TICKS = {}  # operation_id → tick at first call
_SURGERY_IDEMPOTENCY_WINDOW = 200_000  # ~11 hours at 0.2s/tick

_VALID_SECTIONS = frozenset({
    "listen", "subject", "verb", "object", "modifier", "ground", "intro",
    "sight", "audio_bass", "audio_mid", "audio_treble", "audio_rhythm",
    "audio_harmony", "modal_touch", "modal_smell", "modal_taste",
})
_SOURCE_RE = _re.compile(r'^(seed:[a-z_]+:[0-9]{4}|manual:[a-z_]+)$')

# Backup state shared between orchestrator and freshness gate
_last_successful_backup_wall = 0.0    # wall-clock time of last successful backup
_backup_in_flight = False              # True while a backup is running
_backup_lock = threading.Lock()        # protects the two vars above
_backup_result_holder = [None]         # [result] set by in-flight backup


def _orchestrated_backup(reason, blocking=False, _result_holder=None):
    """B.2: Named backup through existing engine.
    Updates _last_successful_backup_wall on success.
    If _result_holder is provided, sets result there for waiting callers."""
    global _last_successful_backup_wall, _backup_in_flight
    with _backup_lock:
        _backup_in_flight = True
    try:
        from dsf_ai_service.save_coordinator import SAVE_COORDINATOR
        t0 = time.time()
        s3_enabled = bool(
            SAVE_COORDINATOR is not None
            and getattr(SAVE_COORDINATOR, "s3_bucket", None))
        if SAVE_COORDINATOR:
            SAVE_COORDINATOR.force_save(reason=reason)
        else:
            _guala.save_full_state(STATE_DIR)
        storage_scope = "local-and-s3-queued" if s3_enabled else "local-only"
        s3_status = "queued" if s3_enabled else "disabled"
        _guala._log_substrate_event(
            "auto_backup", reason=reason, storage=storage_scope,
            s3_status=s3_status, tick=_guala.tick)
        elapsed = time.time() - t0
        print(
            f"[backup_orchestrator] {reason} completed in {elapsed:.1f}s "
            f"storage={storage_scope}")
        with _backup_lock:
            _last_successful_backup_wall = time.time()
            _backup_in_flight = False
        result = {
            "ok": True,
            "reason": reason,
            "elapsed_s": round(elapsed, 1),
            "storage": storage_scope,
            "s3": s3_status,
        }
        if _result_holder is not None:
            _result_holder[0] = result
        return result
    except Exception as e:
        _guala._log_substrate_event("auto_backup_failed", reason=reason, error=str(e))
        print(f"[backup_orchestrator] {reason} FAILED: {e}")
        with _backup_lock:
            _backup_in_flight = False
        result = {"ok": False, "reason": reason, "error": str(e)}
        if _result_holder is not None:
            _result_holder[0] = result
        if blocking:
            return result
        return None


def handle_atlas_surgery(args):
    """B.1: Validated direct-write path for atlas seeding.
    All Phase G/I seeds use this. All-or-nothing, idempotent, source-honest."""
    operation_id = (args.get("operation_id") or "").strip()
    if not operation_id:
        return {"error": "operation_id required", "writes": {"n_written": 0}}

    # Idempotency: replay within window
    if operation_id in _SURGERY_CACHE:
        age = _guala.tick - _SURGERY_CACHE_TICKS.get(operation_id, 0)
        if age < _SURGERY_IDEMPOTENCY_WINDOW:
            resp = dict(_SURGERY_CACHE[operation_id])
            resp["idempotent_replay"] = True
            return resp

    dry_run = bool(args.get("dry_run", False))
    allow_overwrite = bool(args.get("allow_overwrite", False))
    high_strength_ack = bool(args.get("high_strength_acknowledged", False))
    bindings = args.get("bindings", [])

    if not bindings:
        err = {"operation_id": operation_id, "dry_run": dry_run,
               "validation": {"n_bindings_validated": 0,
                              "errors": [{"reason": "empty bindings array"}]},
               "writes": {"n_written": 0}}
        _guala._log_substrate_event("atlas_surgery_rejected",
                                    operation_id=operation_id,
                                    errors=["empty bindings array"])
        return err

    # ── Validation (all-or-nothing) ──────────────────────────────
    errors = []
    seen_tuples = set()
    n_collisions = 0

    for i, b in enumerate(bindings):
        src = (b.get("source") or "").strip()
        section = (b.get("section") or "").strip()
        motif = b.get("motif")
        chi = b.get("chi")
        strength = b.get("initial_strength", 0.3)
        polarity = b.get("polarity", 1)

        if not _SOURCE_RE.match(src):
            errors.append({"binding_index": i,
                           "reason": f"invalid source '{src}' — must match seed:X:NNNN or manual:X"})
        if section not in _VALID_SECTIONS:
            errors.append({"binding_index": i, "reason": f"unknown section '{section}'"})
        if not isinstance(chi, int) or chi < 0 or chi > 9999:
            errors.append({"binding_index": i, "reason": f"chi {chi} out of range [0,9999]"})
        if not isinstance(motif, int) or motif < 0:
            errors.append({"binding_index": i, "reason": f"motif {motif} must be non-negative int"})

        tup = (section, motif, chi)
        if tup in seen_tuples:
            errors.append({"binding_index": i, "reason": "duplicate (section,motif,chi) in batch"})
        seen_tuples.add(tup)

        # Collision check against existing atlas
        if section and isinstance(chi, int) and isinstance(motif, int):
            for band_d in range(-2, 3):
                for existing in _guala.atlas.entries.get(chi + band_d, []):
                    if existing.get("section") == section and existing.get("motif") == motif:
                        n_collisions += 1
                        if not allow_overwrite:
                            errors.append({"binding_index": i,
                                           "reason": f"collision with existing source='{existing.get('source')}'; set allow_overwrite:true"})
                        elif existing.get("source") != src:
                            errors.append({"binding_index": i,
                                           "reason": "cross-source overwrite not permitted"})
                        break

        if polarity not in (-1, 0, 1):
            errors.append({"binding_index": i, "reason": "polarity must be -1, 0, or +1"})
        if not (0.0 <= strength <= 1.0):
            errors.append({"binding_index": i, "reason": f"initial_strength {strength} OOB [0,1]"})
        elif strength > 0.7 and not high_strength_ack:
            errors.append({"binding_index": i,
                           "reason": f"initial_strength {strength}>0.7 requires high_strength_acknowledged:true"})

    validation = {"n_bindings_validated": len(bindings),
                  "n_collisions_with_existing": n_collisions, "errors": errors}

    if errors:
        resp = {"operation_id": operation_id, "dry_run": dry_run,
                "validation": validation, "writes": {"n_written": 0}}
        _guala._log_substrate_event("atlas_surgery_rejected",
                                    operation_id=operation_id,
                                    errors=[e["reason"] for e in errors[:5]])
        _SURGERY_CACHE[operation_id] = resp
        _SURGERY_CACHE_TICKS[operation_id] = _guala.tick
        return resp

    atlas_n_before = sum(len(v) for v in _guala.atlas.entries.values())

    if dry_run:
        return {"operation_id": operation_id, "dry_run": True,
                "validation": validation,
                "writes": {"n_written": len(bindings),
                           "atlas_n_before": atlas_n_before,
                           "atlas_n_after": atlas_n_before + len(bindings),
                           "predicted": True},
                "binding_ids": [f"dry:{operation_id}:{i}" for i in range(len(bindings))]}

    # ── B.2 Freshness gate (GL-CMD-PRESURGERY-FRESHNESS-EVE-20260627-22) ──
    freshness_window = _BACKUP_ORCH_CONFIG.get("surgery_freshness_seconds", 600)
    _op_reason = f"pre_surgery_{operation_id.replace(':', '_')[:60]}"

    with _backup_lock:
        backup_age = time.time() - _last_successful_backup_wall
        in_flight = _backup_in_flight

    if backup_age < freshness_window:
        # Path 1: recent backup exists — async tag and proceed immediately
        _start_background_thread(
            lambda: _orchestrated_backup(_op_reason),
            f"backup-{_op_reason}")

    elif in_flight:
        # Path 2: backup running — wait up to 180s for it to finish
        deadline = time.time() + 180
        while True:
            time.sleep(2)
            with _backup_lock:
                in_flight = _backup_in_flight
                backup_age = time.time() - _last_successful_backup_wall
            if not in_flight:
                if backup_age < freshness_window + 300:  # generous window after wait
                    _start_background_thread(
                        lambda: _orchestrated_backup(_op_reason),
                        f"backup-{_op_reason}")
                    break
                else:
                    _guala._log_substrate_event("surgery_refused",
                                                operation_id=operation_id,
                                                reason="in-flight backup failed")
                    return {"operation_id": operation_id,
                            "error": "backup unavailable (in-flight failed)",
                            "writes": {"n_written": 0}}
            if time.time() > deadline:
                _guala._log_substrate_event("surgery_refused", operation_id=operation_id,
                                            reason="in-flight backup timed out")
                return {"operation_id": operation_id,
                        "error": "backup unavailable (in-flight timed out after 180s)",
                        "writes": {"n_written": 0}}

    else:
        # Path 3: stale — synchronous backup required before surgery.
        # Runs in a thread so the substrate event loop can tick, but we
        # block here until it finishes. EFS write ~170s.
        holder = [None]
        sync_reason = f"pre_surgery_synchronous_{operation_id.replace(':', '_')[:50]}"
        t = _start_background_thread(
            lambda: _orchestrated_backup(sync_reason, True, holder),
            f"backup-{sync_reason}")
        t.join(timeout=300)   # wait up to 5 min
        result = holder[0]
        if not result or not result.get("ok"):
            err = (result or {}).get("error", "backup thread timed out or failed")
            _guala._log_substrate_event("surgery_refused", operation_id=operation_id,
                                        reason=f"synchronous backup failed: {err}")
            return {"operation_id": operation_id,
                    "error": f"backup unavailable (synchronous attempt failed): {err}",
                    "writes": {"n_written": 0}}

    # ── Writes ───────────────────────────────────────────────────
    written = 0
    binding_ids = []
    try:
        for i, b in enumerate(bindings):
            section = b["section"]
            motif = b["motif"]
            chi = b["chi"]
            strength = b.get("initial_strength", 0.3)
            src = b["source"]
            ep = f"episode:surgery:{_guala.tick}:{operation_id}"
            _guala._atlas_record(section, motif, chi, _guala.tick,
                                salience=strength, source=src, episode_ref=ep,
                                sensory_refs=[f"surgery:{operation_id}"])
            binding_ids.append(f"{section}:{motif}:{chi}:{_guala.tick}")
            written += 1
    except Exception as exc:
        _guala._log_substrate_event("atlas_surgery_error",
                                    operation_id=operation_id,
                                    written_before_error=written, error=str(exc))
        return {"operation_id": operation_id, "error": str(exc),
                "writes": {"n_written": written, "partial": True}}

    atlas_n_after = sum(len(v) for v in _guala.atlas.entries.values())
    _guala._log_substrate_event("atlas_surgery", operation_id=operation_id,
                                n_written=written,
                                source_tags=list({b["source"] for b in bindings}))

    resp = {"operation_id": operation_id, "dry_run": False,
            "validation": validation,
            "writes": {"n_written": written, "atlas_n_before": atlas_n_before,
                       "atlas_n_after": atlas_n_after,
                       "deep_atlas_n_before": _guala.deep_atlas.live_count(),
                       "deep_atlas_n_after": _guala.deep_atlas.live_count()},
            "binding_ids": binding_ids}
    _SURGERY_CACHE[operation_id] = resp
    _SURGERY_CACHE_TICKS[operation_id] = _guala.tick
    stale = [k for k, t in _SURGERY_CACHE_TICKS.items()
             if _guala.tick - t > _SURGERY_IDEMPOTENCY_WINDOW]
    for k in stale:
        _SURGERY_CACHE.pop(k, None); _SURGERY_CACHE_TICKS.pop(k, None)
    return resp


# ── B.2: Backup orchestrator ── GL-CMD-BACKUP-ORCHESTRATOR-EVE-20260627-19 ──

_BACKUP_ORCH_CONFIG = {
    "enabled": True,
    "surgery_freshness_seconds": 600,   # GL-CMD-PRESURGERY-FRESHNESS-22
    "triggers": {"pre_deploy": True, "post_deploy_verified": True,
                 "pre_surgery": True, "post_emergence": True,
                 "daily_floor": True, "dream_end": True},
}
_BACKUP_HISTORY = []


def handle_backup_orchestrator_configure(args):
    global _BACKUP_ORCH_CONFIG
    if "enabled" in args:
        _BACKUP_ORCH_CONFIG["enabled"] = bool(args["enabled"])
    if "surgery_freshness_seconds" in args:
        v = int(args["surgery_freshness_seconds"])
        if v < 0:
            return {"error": "surgery_freshness_seconds must be >= 0"}
        _BACKUP_ORCH_CONFIG["surgery_freshness_seconds"] = v
    if "triggers" in args and isinstance(args["triggers"], dict):
        _BACKUP_ORCH_CONFIG["triggers"].update(args["triggers"])
    return {"config": _BACKUP_ORCH_CONFIG}


def handle_backup_orchestrator_status(args):
    with _backup_lock:
        age = time.time() - _last_successful_backup_wall
        in_flight = _backup_in_flight
    freshness = _BACKUP_ORCH_CONFIG.get("surgery_freshness_seconds", 600)
    return {"config": _BACKUP_ORCH_CONFIG,
            "history": _BACKUP_HISTORY[-20:],
            "last_backup_age_s": round(age, 1),
            "backup_in_flight": in_flight,
            "surgery_gate": "fresh" if age < freshness else ("in_flight" if in_flight else "stale"),
            "last_s3_backup": getattr(_guala, '_last_s3_backup', None) if _guala else None}


# ── Op registry ──────────────────────────────────────────────────

OP_HANDLERS = {
    "v7_state": handle_v7_state,
    "v7_converse": handle_v7_converse,
    "v7_feedback": handle_v7_feedback,
    "v7_quiet": handle_v7_quiet,
    "v7_save": handle_v7_save,
    "gualaloom_post": handle_gualaloom_post,
    "amnesty": handle_amnesty,
    "force_dream": handle_force_dream,
    "force_reading": handle_force_reading,
    "repause": handle_repause,
    "unpause": handle_unpause,
    "wake": handle_wake,
    "atlas_snapshot": handle_atlas_snapshot,
    "chi_density": handle_chi_density,
    "backup": handle_backup,
    "atlas_surgery": handle_atlas_surgery,
    "backup_orchestrator_configure": handle_backup_orchestrator_configure,
    "backup_orchestrator_status": handle_backup_orchestrator_status,
    "backfill_picture_titles": handle_backfill_picture_titles,
    "backfill_sound_captions": handle_backfill_sound_captions,
    "sight_frame": handle_sight_frame,
    "sound_frame": handle_sound_frame,
    "sleep_for_deploy": handle_sleep_for_deploy,
    "status": handle_status_simple,
    "ring_status": handle_ring_status,
    "ring_read": lambda args: {
        "events": (_substrate_ring.subscribe().read_available()[:args.get("limit", 100)]
                   if _substrate_ring else []),
        "published_seq": _substrate_ring._published_seq if _substrate_ring else 0,
    },
    "ring_write": handle_ring_write,
    "start_cascade_monitor": handle_start_cascade_monitor,
    "stop_cascade_monitor": handle_stop_cascade_monitor,
    "teacher_feedback": handle_teacher_feedback,
    "teacher_correction": handle_teacher_correction,
    "observation_snapshot": handle_observation_snapshot,
    "auditory_l5_status": handle_auditory_l5_status,
    "auditory_l5_teach": handle_auditory_l5_teach,
    "load_corpus": handle_load_corpus,
    "corpus_status": handle_corpus_status,
}

# ── Exported for in-process shim (GL-CMD-PROCESS-COLLAPSE-61) ────────────────
HANDLERS = OP_HANDLERS


def _start_curriculum_orchestrator():
    """Start curriculum orchestrator as a background thread.

    Runs the sensory curriculum orchestrator in a loop, cycling through the
    100-bundle seed at --min-interval-sec cadence. Gated by CURRICULUM_AUTOSTART
    env var (default disabled — GL-CMD-DENSITY-RETIRE-109 retires 65-A's
    autostart pending the gated B2 Experience Engine design). Calls
    localhost:8080 — same process, no API Gateway.

    65-A from GL-CMD-C1B-QUEUE-EVE-20260701-65-PB3, retired by
    GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1.
    """
    if os.environ.get("CURRICULUM_AUTOSTART", "0") != "1":
        print("[curriculum] autostart disabled by env")
        return

    import sys as _sys
    import subprocess
    import threading

    def _runner():
        # Delay start: boot + dream cycle settle. She boots sleeping, dreams,
        # then wakes. Dream cycle can hold the atlas lock for 30-60s.
        # Wait 90s to avoid delivery timeouts during boot dream.
        if _shutdown_event.wait(90):
            return
        interval = os.environ.get("CURRICULUM_ORCHESTRATOR_INTERVAL_SEC", "5")
        seed_path = os.environ.get("CURRICULUM_SEED_PATH",
                                   "/app/tools/curriculum_seed.json")
        # Use localhost — orchestrator runs inside the same container
        substrate_url = os.environ.get("CURRICULUM_SUBSTRATE_URL",
                                       "http://localhost:8080")
        while not _shutdown:
            try:
                global _curriculum_process
                proc = subprocess.Popen(
                    [_sys.executable, "/app/tools/sensory_curriculum_orchestrator.py",
                     "--curriculum", seed_path,
                     "--alb-url", substrate_url,
                     "--min-interval-sec", interval,
                     "--mode", "live",
                     "--no-gate",  # autonomous density engine: bypass presence gate
                     "--log", "/tmp/curriculum_orchestrator.jsonl"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                _curriculum_process = proc
                for line in proc.stdout:
                    print(f"[curriculum] {line.decode().rstrip()}", flush=True)
                proc.wait()
                # After one full pass through seed, pause then loop again
                # (density growth = repeated multi-modal exposure)
                if not _shutdown:
                    if _shutdown_event.wait(60):
                        break
            except Exception as e:
                print(f"[curriculum] orchestrator error: {e}, restarting in 60s",
                      flush=True)
                if _shutdown_event.wait(60):
                    break

    _start_background_thread(_runner, "curriculum")
    print("[curriculum] autostart thread started", flush=True)


def start_background_loops():
    """Start all background threads. Called from app.py lifespan after boot_substrate."""
    _start_organ_surface_poll()
    _start_autonomous_emission_loop()
    _start_input_ring_consumer()
    _start_curriculum_orchestrator()
    import threading
    _start_background_thread(heartbeat_loop, "heartbeat")


# ═══════════════════════════════════════════════════════════════
# Heartbeat + (socket server deleted — GL-CMD-PROCESS-COLLAPSE-61)
# ═══════════════════════════════════════════════════════════════


def heartbeat_loop():
    """Write heartbeat file every 5s in a background thread."""
    while not _shutdown:
        try:
            hb_dir = os.path.dirname(HEARTBEAT_PATH)
            if hb_dir:
                os.makedirs(hb_dir, exist_ok=True)
            with open(HEARTBEAT_PATH, 'w') as f:
                f.write(json.dumps({
                    "alive": True,
                    "tick": _guala.tick if _guala else 0,
                    "vocab": len(_guala.vocab) if _guala else 0,
                    "ts": time.time(),
                }))
        except Exception:
            pass
        if _shutdown_event.wait(5):
            break
