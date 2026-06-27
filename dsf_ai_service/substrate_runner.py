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
import re
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
_guala_cognition = None  # her organ-brain speech (learns from exposure)
_curriculum = None  # autonomous study scheduler (she reads on her own)
_shutdown = False

# Ring buffers — initialized on boot
_substrate_ring = None
_input_ring = None

RUNTIME_CONFIG_FILE = "guala_runtime_config.json"


def _runtime_config_path():
    return os.path.join(STATE_DIR, RUNTIME_CONFIG_FILE)


# ═══════════════════════════════════════════════════════════════
# Organ-brain learning from real experience (GL-CMD-NEXT Increment 1)
# Her section data carries junk (e.g. 'kbl', leaked quote fragments). Before any
# real word becomes part of her organ-brain's learned succession, it passes this
# gate: a clean word is alphabetic, has a vowel (drops code-junk like 'kbl'/'wc'),
# and is a sane length. Exposure only happens on >=2 clean tokens (succession needs
# a pair). All of this rides ALONGSIDE her engine and never raises into her runtime.
# ═══════════════════════════════════════════════════════════════

_VOWELS = frozenset("aeiouy")  # y counts: keeps real words like sky/my/why/dry/try
# obvious non-words seen in her section data; extend conservatively
_COGNITION_STOP_JUNK = frozenset({
    # code/encoding artifacts
    "kbl", "kb", "wc", "nhs", "xx", "xxx", "hmm",
    # commercial/web boilerplate — these should never enter her succession
    "ads", "ad", "subscribe", "subscribed", "subscribers", "sponsored",
    "advertisement", "click", "download", "signup", "login", "logout",
    "cookies", "privacy", "terms", "copyright", "reserved", "trademark",
    "playlist", "channel", "views", "likes", "dislike", "comment", "share",
    "patreon", "merch", "affiliate", "promo", "discount", "coupon", "deal",
    "checkout", "cart", "purchase", "shipping", "refund", "pricing",
    "netflix", "hulu", "spotify", "amazon", "walmart", "youtube",
})


def _clean_word(raw):
    """Normalize one token to a real word, or '' if it is junk."""
    w = re.sub(r"[^a-z']", "", (raw or "").lower()).strip("'")
    if not w or len(w) > 20:
        return ""
    if w in _COGNITION_STOP_JUNK:
        return ""
    if len(w) == 1 and w not in ("a", "i"):   # stray single letters (g, b, c...)
        return ""
    if not (_VOWELS & set(w)):                 # no vowel (y counts) -> code/junk
        return ""
    return w


def _clean_sentence_for_cognition(text):
    """Real-word sentence for the organ-brain, or '' if too little signal.

    Minimum 4 clean tokens — blocks 'no ads', 'good deal', 'click here'
    while allowing 'the water is cool and soft' and similar real sentences.
    Maximum 20 tokens — blocks run-on web scrape garbage.
    """
    toks = [w for w in (_clean_word(t) for t in (text or "").split()) if w]
    if len(toks) < 4 or len(toks) > 20:
        return ""
    return " ".join(toks)


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


def _cognition_learn(text):
    """Feed CLEAN tokens into GualaCognition.

    Additive and exception-walled. Returns the number of clean tokens learned."""
    try:
        s = _clean_sentence_for_cognition(text)
        if not s:
            return 0
        if _guala_cognition is not None:
            _guala_cognition.expose([s])
        return len(s.split())
    except Exception:
        return 0


# ── sensory experience of words she reads (GL-CMD-NEXT Increment 3) ──
# The "tumbler waveform generator in front of texts": when she reads a sensory
# descriptor (warm/soft/cold/sweet/wet/...), generate its physics waveform, run it
# through krimelack winding to a chi per channel, and bind that felt/smelled/tasted
# experience into her atlas IN THE SAME TICK WINDOW as the word — so the word and
# the sensation cross-modally bind (her existing 5-tick binder). Uses only the
# built-in TOUCH/SMELL/TASTE libraries (no external keys). Exception-walled.

_SENSORY_WORD_MAP = None


def _sensory_word_map():
    """word -> modality, from the built-in physics libraries (built once)."""
    global _SENSORY_WORD_MAP
    if _SENSORY_WORD_MAP is None:
        m = {}
        try:
            from dsf_ai_service.substrate import sensory_generators as sg
            for w in getattr(sg, "TOUCH_LIBRARY", {}):
                m[w] = "touch"
            for w in getattr(sg, "TASTE_LIBRARY", {}):
                m.setdefault(w, "taste")   # taste before smell for sweet/salty
            for w in getattr(sg, "SMELL_LIBRARY", {}):
                m.setdefault(w, "smell")
        except Exception:
            pass
        _SENSORY_WORD_MAP = m
    return _SENSORY_WORD_MAP


def _bind_sensory_words(text):
    """Give her the felt/smelled/tasted experience of sensory words in `text`.
    Returns the number of sensory channel-bindings made. Never raises."""
    try:
        if _guala is None:
            return 0
        mapping = _sensory_word_map()
        if not mapping:
            return 0
        from dsf_ai_service.substrate.sensory_generators import (
            generate_sensory_signals, transduce_sensory_signals)
        from dsf_ai_service.v4.gualaloom_v5_engine import (
            deterministic_motif_id, DWELL_GATE_META)
        seen = set()
        bound = 0
        for raw in (text or "").lower().split():
            w = _clean_word(raw)
            if not w or w in seen:
                continue
            modality = mapping.get(w)
            if not modality:
                continue
            seen.add(w)
            signals = generate_sensory_signals(modality, [w])
            for channel, info in transduce_sensory_signals(signals).items():
                mid = deterministic_motif_id(f"{modality}_{w}_{channel}")
                _guala.atlas.record(
                    f"modal_{modality}", mid, info["chi"], _guala.tick,
                    salience=1.0, dwell_ticks=DWELL_GATE_META,
                    sensory_refs=[f"{modality}:{w}"],
                    **_guala._affect_kwargs())
                bound += 1
        return bound
    except Exception:
        return 0


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


def _curriculum_feed_chunk(sentences, bundle_id=None):
    """Feed a study chunk into her engine + organ-brain. Returns (n_fed, learned).

    GL-CMD-CROSS-MODAL-STRENGTHEN B1.b: if bundle_id not supplied, compute from
    current activity so curriculum words read while she attends a sensory item
    bind into that item's cross-modal group."""
    if bundle_id is None:
        bundle_id = _activity_bundle_id()
    n_fed = 0
    learned = 0
    _pause_autonomy_for_bulk()
    try:
        for sent in sentences:
            try:
                _guala.read_sentence(sent, source="curriculum", bundle_id=bundle_id)
                learned += _cognition_learn(sent)
                _bind_sensory_words(sent)  # feel/smell/taste the sensory words she reads
                n_fed += 1
            except Exception:
                pass
    finally:
        _resume_autonomy_for_bulk()
    return n_fed, learned


def _curriculum_is_busy():
    """Skip a study cycle while she sleeps or a bulk load holds the floor."""
    try:
        if _autonomy_pause_refcount > 0:
            return True
        return bool(getattr(_guala, "is_asleep", False))
    except Exception:
        return True


# ── lookup grounding (GL-CMD-NEXT Increment 4): feed what she focuses on ──
# Look an item up (OpenAI child-safe description — substitute for the absent Google
# key) and feed the description through her senses + organ-brain. Exception-walled.

def _lookup_and_ground(term):
    """Look up `term`, feed the description into her engine + organ-brain + senses.
    Returns the description text, or None. Never raises into her runtime."""
    try:
        from dsf_ai_service.loom_model.lookup_grounding import describe
        desc = describe(term)
        if not desc:
            return None
        _pause_autonomy_for_bulk()
        try:
            _guala.read_sentence(desc, source="lookup")
            _cognition_learn(desc)
            _bind_sensory_words(desc)
        finally:
            _resume_autonomy_for_bulk()
        try:
            _guala._log_substrate_event("lookup_grounded", term=term, text=desc[:120])
        except Exception:
            pass
        return desc
    except Exception:
        return None


_LOOKUP_STATE = {"idx": 0}


def _lookup_once():
    """Ground the next of her pictures (one autonomous lookup). Returns status dict."""
    try:
        titles = [getattr(p, "title", None)
                  for p in (getattr(_guala, "_pictures", {}) or {}).values()]
        titles = [t for t in titles if t]
        if not titles:
            return {"state": "no_pictures"}
        term = titles[_LOOKUP_STATE["idx"] % len(titles)]
        _LOOKUP_STATE["idx"] += 1
        d = _lookup_and_ground(term)
        return {"state": "grounded" if d else "empty", "term": term,
                "text": (d or "")[:80]}
    except Exception as e:
        return {"state": "error", "error": str(e)}


def _start_lookup_loop():
    """Autonomous grounding of the things she looks at — OFF unless LOOKUP_AUTONOMOUS=1.
    When on, periodically grounds one of her pictures so her words mean real things."""
    if os.environ.get("LOOKUP_AUTONOMOUS", "0").strip() == "0":
        print("[lookup] autonomous grounding OFF (set LOOKUP_AUTONOMOUS=1 to enable)")
        return
    try:
        interval = int(os.environ.get("LOOKUP_INTERVAL_SEC", "600") or 600)
    except Exception:
        interval = 600

    def loop():
        idx = 0
        while not _shutdown:
            time.sleep(interval)
            try:
                if _curriculum_is_busy():
                    continue
                titles = [getattr(p, "title", None)
                          for p in (getattr(_guala, "_pictures", {}) or {}).values()]
                titles = [t for t in titles if t]
                if not titles:
                    continue
                term = titles[idx % len(titles)]
                idx += 1
                d = _lookup_and_ground(term)
                if d:
                    print(f"[lookup] grounded {term!r}: {d[:60]}")
            except Exception as e:
                print(f"[lookup] loop error (non-fatal): {e}")

    threading.Thread(target=loop, daemon=True, name="lookup-grounding").start()
    print(f"[lookup] autonomous grounding ON interval={interval}s")


# ── world feeds (Khan Academy + YouTube): she reads beyond her books ──
_WORLD_FEED_STATE = {"feed_idx": 0, "query_idx": 0, "last_status": {}}


def _world_feed_once():
    """Pull one chunk from the next world feed (khan/youtube) and feed it to her."""
    try:
        from dsf_ai_service.loom_model import world_feeds as wf
        if not wf.FEEDS:
            return {"state": "no_feeds"}
        fi = _WORLD_FEED_STATE["feed_idx"] % len(wf.FEEDS)
        feed = wf.FEEDS[fi]
        qi = _WORLD_FEED_STATE["query_idx"] % len(feed["queries"])
        query = feed["queries"][qi]
        _WORLD_FEED_STATE["feed_idx"] += 1
        _WORLD_FEED_STATE["query_idx"] += 1
        # GL-CMD-CROSS-MODAL-STRENGTHEN B1.a: bundle feed text to sensory item if attending
        feed_bundle_id = _activity_bundle_id()
        sents = feed["fetch"](query)
        if not sents:
            st = {"state": "empty", "feed": feed["name"], "query": query}
            _WORLD_FEED_STATE["last_status"] = st
            return st
        n_fed, learned = _curriculum_feed_chunk(sents[:120], bundle_id=feed_bundle_id)
        try:
            _guala._log_substrate_event("world_feed_studied", feed=feed["name"],
                                        query=query, n_fed=n_fed, organ_tokens=learned)
        except Exception:
            pass
        st = {"state": "studied", "feed": feed["name"], "query": query,
              "n_fed": n_fed, "organ_tokens": learned}
        _WORLD_FEED_STATE["last_status"] = st
        print(f"[worldfeed] {feed['name']} {query!r}: n_fed={n_fed} organ+={learned}")
        return st
    except Exception as e:
        return {"state": "error", "error": str(e)}


def _start_world_feed_loop():
    """She reads Khan + YouTube on a gentle timer alongside her books. OFF if
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
            time.sleep(interval)
            try:
                if _curriculum_is_busy():
                    continue
                _world_feed_once()
            except Exception as e:
                print(f"[worldfeed] loop error (non-fatal): {e}")

    threading.Thread(target=loop, daemon=True, name="world-feeds").start()
    print(f"[worldfeed] ON interval={interval}s feeds=khan,youtube")


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

    from dsf_ai_service.v4.gualaloom_v5_engine import Guala, CorpusItem

    g = Guala()

    # Seed corpora (same as app.py)
    CORPUS = [
        "the sun rises in the morning",
        "water flows down the river",
        "birds sing in the trees",
        "the wind blows through the leaves",
        "stars shine in the night sky",
    ]
    g._corpora["legacy_seed"] = CorpusItem(
        corpus_id="legacy_seed", title="Seed Corpus", lines=CORPUS)

    g.load_full_state(STATE_DIR)

    # Identity guard + S3 restore on load failure or seed-state detection
    EXPECTED_IDENTITY = "cdef9bcf"
    loaded_id = getattr(g, '_guala_identity', None) or ""
    load_ok = getattr(g, '_load_successful', False)
    vocab_count = len(getattr(g, 'vocab', set()))
    seed_state = vocab_count < 100  # real state has 2800+ words; seed has ~20-40
    if not load_ok or seed_state or (loaded_id and not loaded_id.startswith(EXPECTED_IDENTITY)):
        reason = ("LOAD_FAILED" if not load_ok
                  else f"SEED_STATE(vocab={vocab_count})" if seed_state
                  else f"IDENTITY_MISMATCH({loaded_id[:8]})")
        print(f"[substrate] {reason} — restoring from S3 backup...")
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
            good = None
            best_vocab = 0
            for folder in sorted(folders.keys(), reverse=True):
                files = folders[folder]
                if "guala_core.json" not in files or "guala_atlas.json" not in files:
                    continue
                try:
                    core_obj = s3.get_object(Bucket=bucket,
                        Key=f"{folder}/guala_core.json")
                    core_data = json.loads(core_obj['Body'].read())
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
                    local = os.path.join(STATE_DIR, fname)
                    s3.download_file(bucket, s3_key, local)
                # Reload
                g2 = Guala()
                g2._corpora["legacy_seed"] = CorpusItem(
                    corpus_id="legacy_seed", title="Seed Corpus", lines=CORPUS)
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
            while True:
                time.sleep(30)
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
        _threading.Thread(target=_live_organ_update, daemon=True, name="organ-live-update").start()
    except Exception as _e:
        print(f"[merge] organ-brain load skipped (non-fatal): {_e}")

    # ORGAN-BRAIN COGNITION: she speaks from exposure. Seed with a clean corpus in
    # her world so she composes coherently; learns continuously from her experience.
    try:
        from dsf_ai_service.loom_model.loom_cognition import GualaCognition
        global _guala_cognition
        _guala_cognition = GualaCognition()
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
        _guala_cognition.expose(_seed_corpus)
        print(f"[cognition] organ-brain SPEAKS: vocab={len(_guala_cognition.vocab)} "
              f"sample='{_guala_cognition.say('the moon')}'")
    except Exception as _e:
        print(f"[cognition] organ-brain speech skipped (non-fatal): {_e}")

    # AUTONOMOUS CURRICULUM: she studies children's literature on her own, on a
    # schedule, growing her engine + organ-brain from her real reading life.
    # Additive, killable (CURRICULUM_AUTONOMOUS=0), resumable; never raises into boot.
    try:
        from dsf_ai_service.loom_model.curriculum_scheduler import CurriculumScheduler
        global _curriculum
        # Interleave the world feeds + lookup INTO the one study scheduler so they
        # share its reliable awake windows (separate loops get starved). Gated by env.
        _interleave = []
        if os.environ.get("WORLD_FEEDS", "1").strip() != "0":
            _interleave.append(("worldfeed", _world_feed_once))
        if os.environ.get("LOOKUP_AUTONOMOUS", "0").strip() != "0":
            _interleave.append(("lookup", _lookup_once))
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

    # NOTE: lookup grounding (Increment 4) and world feeds (Khan/YouTube) now run
    # INTERLEAVED inside the curriculum scheduler above (so they share its reliable
    # study windows instead of starving as separate loops). Manual ops /lookup and
    # /worldfeed remain available. The standalone loops are intentionally NOT started.

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

    print(f"[substrate] Ready on {SOCKET_PATH}")


def _start_input_ring_consumer():
    """Drain InputRing on a background thread. Processes sight_frame and
    sound_window events written by the companion/bridge HTTP endpoints."""
    import base64 as _b64

    def _drain_loop():
        while not _shutdown:
            if _input_ring is None or _guala is None:
                time.sleep(1)
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
                            _guala.process_sight_frame(grid)
                            # YOLO gets raw bytes (full color at original resolution)
                            from dsf_ai_service.substrate.grounded_vocab_integration import (
                                process_sight_with_recognition)
                            bindings = process_sight_with_recognition(_guala, img_bytes)
                            if bindings:
                                _scene = " ".join(b.get("word","") for b in bindings)
                                _cognition_learn(_scene)
                                print(f"[sight] detected: {_scene}")
                        except Exception as _e:
                            print(f"[sight] frame error: {_e}")
                    elif kind == "sound_window":
                        try:
                            audio_bytes = _b64.b64decode(data.get("audio_b64", ""))
                            if not audio_bytes:
                                continue
                            # Raw signal processing — she hears like a child hears.
                            # Decode WebM → PCM via ffmpeg, extract real sensory qualities:
                            # energy (loud/soft), frequency (warm/bright), rhythm (moving/steady).
                            # These are true auditory experiences, not transcription.
                            _guala.process_sound_frame(audio_bytes)
                            _heard = _audio_to_sensory_words(audio_bytes)
                            if _heard:
                                _cognition_learn(" ".join(_heard))
                                print(f"[sound] heard: {_heard}")
                            # Also run whisper for speech/lyrics (bonus — fails gracefully)
                            from dsf_ai_service.substrate.grounded_vocab_integration import (
                                process_sound_with_recognition)
                            _words = process_sound_with_recognition(
                                _guala, audio_bytes, source=data.get("source", "ambient"))
                            if _words:
                                _spoken = " ".join(w.get("word","") for w in _words if w.get("word"))
                                if _spoken.strip():
                                    _cognition_learn(_spoken)
                                    print(f"[sound] heard words: {_spoken}")
                        except Exception as _e:
                            print(f"[sound] frame error: {_e}")
            except Exception:
                pass
            time.sleep(0.5)

    t = threading.Thread(target=_drain_loop, daemon=True, name="input-ring-consumer")
    t.start()
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
    from dsf_ai_service.substrate.v7_engine import get_or_create_session
    session = get_or_create_session(session_id, engine=_guala)
    _ensure_v7_link(session)
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
    # organ-brain learns from the live conversation: what was said to her, and her
    # own reply (whichever reply field the engine populated). Clean-gated, walled.
    _cognition_learn(text)
    if isinstance(result, dict):
        for _k in ("reply", "text", "emission", "utterance", "response"):
            _v = result.get(_k)
            if isinstance(_v, str) and _v:
                _cognition_learn(_v)
                break
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

    # GL-CMD-TEACHER-CORRECTION-BINDING: also apply to v5 Guala
    if _guala and hasattr(_guala, 'apply_teacher_correction'):
        original_input = getattr(_guala, '_last_converse_input', None)
        her_emission = getattr(_guala, '_last_converse_reply', None)
        if original_input and her_emission:
            expected = " ".join(expected_tokens) if expected_tokens else None
            _guala.apply_teacher_correction(
                original_input=original_input,
                her_emission=her_emission,
                correct=bool(correct),
                expected_response=expected,
                source="joe",
            )

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
            return {
                "response": "she is sleeping...",
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
    elif command == "/organs":
        return {"response": json.dumps(_guala_organ_brain or {"organ_brain": "not loaded"}),
                "organ_brain": _guala_organ_brain}
    elif command == "/organs_say":
        try:
            if _guala_cognition is None:
                return {"response": "", "speech": ""}
            # learn from what was said to her, then compose from her succession
            if text:
                _guala_cognition.expose([text])
            said = _guala_cognition.say(text or "")
            # speech field makes the UI treat this as her voice (addEmissionMsg path)
            return {"response": said, "speech": said, "engine": "guala-cognition"}
        except Exception as _e:
            return {"response": "", "speech": ""}
    elif command == "/curriculum":
        if _curriculum is None:
            return {"response": "curriculum scheduler not loaded"}
        return {"response": json.dumps(_curriculum.status()), "curriculum": _curriculum.status()}
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
        # look a thing up and feed the description through her senses + organ-brain
        if not (text or "").strip():
            return {"response": "usage: /lookup <thing>"}
        if _curriculum_is_busy():
            return {"response": "she is asleep or bulk-loading; try again when awake"}
        desc = _lookup_and_ground(text)
        return {"response": desc or "lookup unavailable (no key or no result)",
                "grounded": bool(desc)}
    elif command == "/worldfeed":
        # force one Khan/YouTube study chunk now (validation aid)
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
            f"atlas: {s['cross_modal_bindings']} cross-modal / {s.get('cross_modal_bundle', 0)} bundled / {s['atlas_entries']} entries\n"
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
        "organ_brain": _guala_organ_brain or {},
    }


def _cmd_events(text):
    since_tick = 0
    try:
        since_tick = int(text.strip()) if text.strip() else 0
    except ValueError:
        pass
    events = _guala.get_recent_events(since_tick=since_tick, limit=50)
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
    from dsf_ai_service.v4.gualaloom_v5_engine import CorpusItem
    filename = command[len("/addbook:"):]
    title = filename.replace('.txt', '').replace('_', ' ')
    corpus_id = filename.replace('.txt', '').replace(' ', '_').lower()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return {"response": "empty book", "motifs": _guala.introspect()["vocab"]}
    _guala._corpora[corpus_id] = CorpusItem(
        corpus_id=corpus_id, title=title, lines=lines)
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
        from dsf_ai_service.v4.gualaloom_v5_engine import CorpusItem, PictureItem
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
            _guala._corpora[corpus_id] = CorpusItem(
                corpus_id=corpus_id, title=title, lines=split_lines)
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
    import base64, hashlib, tempfile, subprocess, struct, wave
    import numpy as np
    filename = command[len("/addsound:"):]
    title = filename.rsplit('.', 1)[0] if '.' in filename else filename
    b64_data = text.strip()
    if not b64_data:
        return {"response": "no audio data", "motifs": _guala.introspect()["vocab"]}
    t0 = time.time()
    try:
        snd_bytes = base64.b64decode(b64_data)
        snd_id = hashlib.md5(snd_bytes).hexdigest()[:12]
        tmp_in = tempfile.NamedTemporaryFile(suffix='.audio', delete=False)
        tmp_in.write(snd_bytes)
        tmp_in.close()
        tmp_wav = tmp_in.name + '.wav'
        try:
            subprocess.run(["ffmpeg", "-i", tmp_in.name, "-ar", "200",
                            "-ac", "1", "-f", "wav", tmp_wav, "-y",
                            "-loglevel", "error"], check=True, timeout=30)
            with wave.open(tmp_wav, 'rb') as wf:
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
            samples = np.array(struct.unpack(f'<{n_frames}h', raw),
                               dtype=np.float64) / 32768.0
            from dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01 import (
                cochlear_transduce,)
            cochlear = cochlear_transduce(samples, sample_rate=sr)
            n_events = sum(c["n_events"] for c in cochlear.values())
            dur = len(samples) / max(sr, 1)
            from dsf_ai_service.app import deterministic_motif_id
            snd_bundle_id = f"item:snd:{snd_id}"
            for bn, c in cochlear.items():
                chi = c["winding"] % 100
                _guala.atlas.record(f"audio_{bn}",
                    deterministic_motif_id(snd_id),
                    chi, _guala.tick, salience=1.5, dwell_ticks=8,
                    bundle_id=snd_bundle_id)
            # GL-CMD-CROSS-MODAL-STRENGTHEN B1.c: bind title into same bundle as cochlear
            if title:
                try:
                    _guala.read_sentence(title, source="addsound",
                                         bundle_id=snd_bundle_id)
                except Exception:
                    pass
            _guala._sounds[snd_id] = {
                "item_id": snd_id, "title": title,
                "cochlear": {bn: {"winding": c["winding"],
                                  "n_events": c["n_events"]}
                             for bn, c in cochlear.items()},
                "times_attended": 0, "last_attended_tick": 0,
            }
            result = {"response": f"played her \"{title}\" ({dur:.1f}s, {n_events} events)",
                      "motifs": _guala.introspect()["vocab"]}
        except Exception as e:
            result = {"response": f"sound decode error: {e}",
                      "motifs": _guala.introspect()["vocab"]}
        finally:
            for p in [tmp_in.name, tmp_wav]:
                if os.path.exists(p):
                    os.unlink(p)
    except Exception as e:
        result = {"response": f"sound error: {e}",
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

    # 1. Caption — read into substrate as wc-sourced input
    if caption:
        try:
            _guala.read_sentence(caption, source="wc", bundle_id=bundle_id)
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
                _guala._visual_fragments.extend(fragments)
                motif, is_new, overlap = _guala.sight.process_viewing(
                    fragments, pic.item_id, _guala.tick)
                if motif:
                    chi_val = motif.motif_id % 100
                    _guala.atlas.record("sight", motif.motif_id, chi_val,
                                        _guala.tick, salience=1.2,
                                        dwell_ticks=DWELL_GATE_META,
                                        sensory_refs=[f"pic:{pic.item_id}"],
                                        bundle_id=bundle_id,
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

    # 3. Sound — bind cochlear bands into atlas
    if sound_id:
        snd = _guala._sounds.get(sound_id)
        if snd:
            try:
                cochlear = snd.get("cochlear", {})
                for band_name, c in cochlear.items():
                    chi = c.get("winding", 0) % 100
                    _guala.atlas.record(
                        f"audio_{band_name}", deterministic_motif_id(sound_id),
                        chi, _guala.tick, salience=1.2,
                        dwell_ticks=DWELL_GATE_META,
                        sensory_refs=[f"snd:{sound_id}"],
                        bundle_id=bundle_id,
                        **_guala._affect_kwargs())
                    n_chis += 1
                snd["times_attended"] = snd.get("times_attended", 0) + 1
                snd["last_attended_tick"] = _guala.tick
                results.append(f"heard {snd.get('title', sound_id)} ({len(cochlear)} bands)")
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
                _guala.atlas.record(
                    f"modal_{modality}", mid, chi,
                    _guala.tick, salience=1.2,
                    dwell_ticks=DWELL_GATE_META,
                    sensory_refs=[f"{modality}:{desc}"],
                    bundle_id=bundle_id,
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
    if not text or text == "...":
        return None
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
    text = text.strip()
    if not text:
        return {"response": "...", "motifs": _guala.introspect()["vocab"]}
    if source not in {"joe", "wc", "c1"}:
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
    response = _guala.converse(text, source=source, emission_mode=emission_mode,
                               bundle_id=bundle_id)
    _guala.log_event(STATE_DIR, "source_interaction",
                     source=source, words_in=len(text.split()),
                     source_count=_guala.source_history.get(source, 0))
    recalled_pics = getattr(_guala, '_last_recalled_pictures', [])
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
    result = {"response": response or "...", "motifs": _guala.introspect()["vocab"]}
    # GL-CMD-TEACHER-CORRECTION-UI: surface emission_id
    emission_id = getattr(_guala, '_last_emission_id', None)
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

    # Look up emission record for context
    rec = _guala._emission_records.get(emission_id, {})
    original_input = rec.get("input_text") or getattr(_guala, '_last_converse_input', "")
    her_emission = rec.get("text") or getattr(_guala, '_last_converse_reply', "")

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

    # Look up emission record for context
    rec = _guala._emission_records.get(emission_id, {})
    original_input = rec.get("input_text") or getattr(_guala, '_last_converse_input', "")
    her_emission = rec.get("text") or getattr(_guala, '_last_converse_reply', "")

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
    # organ-brain learns the CORRECT phrasing she was taught (supervised signal)
    _cognition_learn(corrected_text)
    if isinstance(story, str):
        _cognition_learn(story)
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
    return result


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
            _guala.start_autonomy_loop(interval=0.2)
            print(f"[autonomy] Resumed (refcount=0)")
        else:
            print(f"[autonomy] Resume deferred (refcount={_autonomy_pause_refcount})")


def _do_corpus_load(corpus_id, title, lines, vocab_before, reads_before, strength_before):
    """Background thread: feed sentences, update progress, resume autonomy."""
    from dsf_ai_service.v4.gualaloom_v5_engine import CorpusItem
    _corpus_load_results[corpus_id]["status"] = "running"
    errors = []
    n_fed = 0
    n_total = len(lines)
    organ_vocab_before = len(_guala_cognition.vocab) if _guala_cognition is not None else 0
    try:
        for sent in lines:
            try:
                _guala.read_sentence(sent, source="corpus")
                _cognition_learn(sent)  # organ-brain learns from what she studies
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

    vocab_after = len(_guala.vocab)
    reads_after = _guala.read_count
    strength_after = round(_guala.atlas.total_strength(), 4)
    organ_vocab_after = len(_guala_cognition.vocab) if _guala_cognition is not None else 0

    _guala._log_substrate_event(
        "curriculum_loaded",
        corpus_id=corpus_id,
        title=title,
        n_sentences=n_fed,
        n_new_vocab=vocab_after - vocab_before,
        reads_delta=reads_after - reads_before,
        atlas_strength_delta=round(strength_after - strength_before, 4),
        organ_vocab_delta=organ_vocab_after - organ_vocab_before,
    )
    print(f"[cognition] corpus '{corpus_id}': organ-brain vocab "
          f"{organ_vocab_before}->{organ_vocab_after} "
          f"(+{organ_vocab_after - organ_vocab_before})")

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
        "organ_vocab_before": organ_vocab_before,
        "organ_vocab_after": organ_vocab_after,
        "organ_vocab_delta": organ_vocab_after - organ_vocab_before,
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
    from dsf_ai_service.v4.gualaloom_v5_engine import CorpusItem

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

    # Register the corpus (overwrites if same corpus_id already exists)
    _guala._corpora[corpus_id] = CorpusItem(
        corpus_id=corpus_id,
        title=title,
        lines=lines,
    )

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

    t = threading.Thread(
        target=_do_corpus_load,
        args=(corpus_id, title, lines, vocab_before, reads_before, strength_before),
        daemon=True,
    )
    t.start()

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


def handle_backup(args):
    """Save to EFS, queue S3 upload. Returns immediately after EFS save.
    GL-CMD-97/104: API Gateway has 30s timeout — cannot wait for S3 queue.
    S3 upload runs in background thread via SaveCoordinator. Caller polls
    /status for last_s3_backup to confirm completion."""
    from dsf_ai_service.save_coordinator import SAVE_COORDINATOR
    t0 = time.time()
    if SAVE_COORDINATOR:
        SAVE_COORDINATOR.force_save(reason="backup")
    else:
        _guala.save_full_state(STATE_DIR)
    n_entries = sum(len(v) for v in _guala.atlas.entries.values())
    dt = time.time() - t0
    print(f"[backup] EFS saved in {dt:.2f}s, {n_entries} entries, S3 queued")
    return {"backup": "complete", "save_time_s": round(dt, 2),
            "atlas_entries": n_entries, "tick": _guala.tick,
            "s3": "queued"}


def handle_sight_frame(args):
    """Transient camera frame → sight krimelack + object recognition."""
    import base64
    b64_data = (args.get("text") or "").strip()
    if not b64_data:
        return {"ok": False, "error": "no frame data"}
    t0 = time.time()
    try:
        img_bytes = base64.b64decode(b64_data)
        from dsf_ai_service.app import decode_image_bytes
        _, grid, _, _ = decode_image_bytes(img_bytes)
        _guala.process_sight_frame(grid)
        # Grounded vocab: YOLO needs raw bytes (full color), not the 64x64 gray grid
        from dsf_ai_service.substrate.grounded_vocab_integration import (
            process_sight_with_recognition)
        bindings = process_sight_with_recognition(_guala, img_bytes)
        # organ-brain learns the scene it saw (co-seen objects -> succession)
        _scene = " ".join(b.get("word", "") for b in (bindings or []))
        _cognition_learn(_scene)
        # Publish to ring
        if _substrate_ring is not None:
            _substrate_ring.publish("sight_frame", _guala.tick,
                                    n_bindings=len(bindings))
        dt = time.time() - t0
        if dt > 0.5:
            print(f"[sight-frame] {dt:.3f}s (slow)")
        return {"ok": True, "tick": _guala.tick,
                "recognized": [b["word"] for b in bindings]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_sound_frame(args):
    """Transient mic audio → sound krimelack + speech/ambient recognition."""
    import base64
    b64_data = (args.get("text") or "").strip()
    source = args.get("source", "ambient")
    if not b64_data:
        return {"ok": False, "error": "no audio data"}
    t0 = time.time()
    try:
        audio_bytes = base64.b64decode(b64_data)
        _guala.process_sound_frame(audio_bytes)
        # Grounded vocab: speech transcription / ambient classification
        from dsf_ai_service.substrate.grounded_vocab_integration import (
            process_sound_with_recognition)
        _sbind = process_sound_with_recognition(_guala, audio_bytes, source=source)
        # organ-brain learns the words it heard (transcribed speech -> succession)
        if _sbind:
            _cognition_learn(" ".join(b.get("word", "") for b in _sbind))
        # Publish to ring
        if _substrate_ring is not None:
            _substrate_ring.publish("sound_frame", _guala.tick, source=source)
        return {"ok": True, "tick": _guala.tick}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_sleep_for_deploy(args):
    if _guala.is_asleep:
        return {"ok": True, "already_asleep": True, "sleep_tick": _guala.tick}
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
        time.sleep(interval)
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
    t = threading.Thread(target=_cascade_monitor_loop, args=(baseline, interval),
                         daemon=True)
    t.start()
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
    }


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
    "repause": handle_repause,
    "unpause": handle_unpause,
    "wake": handle_wake,
    "atlas_snapshot": handle_atlas_snapshot,
    "backup": handle_backup,
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
    "ring_write": lambda args: {
        "ok": True,
        "seq": _input_ring.publish(
            args.get("kind", "text_input"),
            args.get("source", "bridge"),
            # exclude 'source' from data to avoid duplicate keyword arg crash
            **{k: v for k, v in args.get("data", {}).items() if k != "source"}
        ) if _input_ring else -1,
    },
    "start_cascade_monitor": handle_start_cascade_monitor,
    "stop_cascade_monitor": handle_stop_cascade_monitor,
    "teacher_feedback": handle_teacher_feedback,
    "teacher_correction": handle_teacher_correction,
    "load_corpus": handle_load_corpus,
    "corpus_status": handle_corpus_status,
}


# ═══════════════════════════════════════════════════════════════
# Socket server
# ═══════════════════════════════════════════════════════════════

async def handle_client(reader, writer):
    """Handle one client connection — read JSON lines, dispatch, respond."""
    peer = "client"
    try:
        while not _shutdown:
            line = await reader.readline()
            if not line:
                break
            try:
                req = json.loads(line)
            except json.JSONDecodeError as e:
                resp = {"id": "?", "ok": False, "error": f"bad json: {e}"}
                writer.write(json.dumps(resp, default=str).encode() + b"\n")
                await writer.drain()
                continue

            req_id = req.get("id", "?")
            op = req.get("op", "")
            args = req.get("args", {})

            try:
                # Run dispatch in executor to keep socket server responsive
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, dispatch, op, args)
                resp = {"id": req_id, "ok": True, "result": result}
            except Exception as e:
                resp = {"id": req_id, "ok": False,
                        "error": f"{type(e).__name__}: {e}"}
                traceback.print_exc()

            writer.write(json.dumps(resp, default=str).encode() + b"\n")
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


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
        time.sleep(5)


async def run_server():
    global _shutdown

    # Clean up stale socket
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    sock_dir = os.path.dirname(SOCKET_PATH)
    if sock_dir:
        os.makedirs(sock_dir, exist_ok=True)

    # Boot substrate
    print(f"[substrate] Booting...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, boot_substrate)

    # Start heartbeat
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()

    # Start socket server (64 MB buffer — base64 uploads can be ~13 MB)
    server = await asyncio.start_unix_server(
        handle_client, path=SOCKET_PATH, limit=64 * 1024 * 1024)
    print(f"[substrate] Listening on {SOCKET_PATH}")

    # SaveCoordinator: presence-detected saves with S3 background queue
    from dsf_ai_service.save_coordinator import SaveCoordinator
    import dsf_ai_service.save_coordinator as _sc
    s3_bucket = os.environ.get("GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups")
    save_coord = SaveCoordinator(_guala, STATE_DIR, s3_bucket=s3_bucket)
    _sc.SAVE_COORDINATOR = save_coord

    import concurrent.futures
    _save_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="save")

    # Save hooks consolidated into _end_activity wrap below.
    # The engine ends all activities (including DREAMING) via
    # _end_activity; there is no separate _end_dream_cycle method.
    if hasattr(_guala, '_end_activity'):
        _orig_end_activity = _guala._end_activity
        def _end_activity_with_save(*a, **kw):
            # Capture the ending activity kind BEFORE _end_activity clears it
            ending = getattr(_guala, '_current_activity', None)
            ending_kind = ending.kind if ending else None
            result = _orig_end_activity(*a, **kw)
            if ending_kind == "DREAMING":
                save_coord.maybe_save(reason="dream_end")
            else:
                save_coord.maybe_save(reason="activity_ended")
            return result
        _guala._end_activity = _end_activity_with_save

    # Backstop: 5-minute check (NOT the primary trigger, just safety net)
    async def _save_backstop():
        while not _shutdown:
            await asyncio.sleep(300)
            if _guala is None or _shutdown:
                continue
            try:
                if _guala.is_natural_quiet_point():
                    await loop.run_in_executor(
                        _save_executor,
                        lambda: save_coord.maybe_save("backstop"))
            except Exception as e:
                print(f"[save] backstop error: {e}")
    asyncio.ensure_future(_save_backstop())

    # Start persistence consumer on ring buffer (R2)
    if _substrate_ring is not None:
        from dsf_ai_service.substrate.persistence_consumer import (
            PersistenceConsumer, S3Consumer)
        events_dir = os.path.join(STATE_DIR, "ring_events")
        os.makedirs(events_dir, exist_ok=True)
        _pers_consumer = PersistenceConsumer(
            ring=_substrate_ring,
            state_dir=events_dir,
            build_snapshot_fn=lambda: _guala.introspect())
        _pers_consumer.start()
        _s3_consumer = S3Consumer(
            ring=_substrate_ring,
            state_dir=events_dir,
            bucket=s3_bucket)
        _s3_consumer.start()
        print(f"[substrate] Ring consumers started: persistence + S3")

    # Handle SIGTERM/SIGINT
    def _signal_handler():
        global _shutdown
        _shutdown = True
        print(f"[substrate] Shutting down...")
        if _guala:
            try:
                save_coord.force_save(reason="shutdown")
                print(f"[substrate] Final save complete")
            except Exception as e:
                print(f"[substrate] Final save failed: {e}")
        server.close()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    async with server:
        await server.serve_forever()


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
