"""Boundary speech-to-text transducer (Whisper-tiny via faster-whisper).

Port of the stranded recognizer-lifecycle repair a8277fa ("fix(stt): own
recognizer lifecycle and fail visibly", branch hotfix/stt-reinstatement-
20260713) onto the live lineage.  a8277fa patched grounded_vocab.py /
grounded_vocab_integration.py, but 8835cfc (the Fact-Strand cutover, 2.5h
later on the live lineage) rewrote both files and deleted the recognizer
entirely, so the repair could not cherry-pick — this module re-implements
its substance against the current code.

Boundary discipline (why this file lives at the service edge, NOT under
substrate/):

- This is a SENSE TRANSDUCER at the process boundary, exactly like the
  ffmpeg WebM->WAV decode that precedes it in /sound_frame: it converts one
  physical signal (audio) into another (text) BEFORE anything enters the
  substrate.  It is never part of cognition.
- It is NOT a semantic-recognition authority.  Language Fact-Strand
  reciprocity remains the sole semantic authority inside the substrate
  (8835cfc's ruling stands).  The CALLER (app.py /sound_frame) feeds the
  transcript through the engine's one sentence-intake door, tagged
  source="joe" — the same real path typed text and heard speech already
  use, which also establishes presence (GL-FIX-VOICE-PRESENCE-20260712:
  she is not a chatbot gated on being directly addressed).  This module
  itself never touches the substrate: audio bytes in, text out.
- Failure is loud: construction and inference failures raise typed
  exceptions the caller must surface; no path fabricates words or collapses
  an error into silent empty text.  An empty string has exactly one
  meaning: valid audio that contained no speech.

Lifecycle (a8277fa's core repair): one CTranslate2 model is one physical
recognition resource.  Exactly one SpeechRecognizer exists per process
(double-checked-locked singleton), inference is serialized on it, and the
caller runs it on a dedicated single-worker executor — which also keeps STT
decode trivially movable to its own process later (the GIL story).
"""

from __future__ import annotations

import os
import threading


class SpeechRecognitionUnavailable(RuntimeError):
    """The configured speech recognizer could not be constructed."""


class SpeechTranscriptionError(RuntimeError):
    """A configured recognizer failed while processing an audio event."""


class SpeechRecognizer:
    """Whisper-tiny speech-to-text via faster-whisper (CTranslate2).

    Uses faster-whisper which is CPU-optimized and doesn't require torch.
    Construction and inference are serialized because one CTranslate2 model
    is one physical recognition resource.  Configuration or inference
    failures are raised explicitly; valid audio containing no speech still
    returns an empty string.
    """

    def __init__(self, model_path=None):
        self.available = False
        self._model = None
        self._initialization_error = None
        self._transcribe_lock = threading.Lock()
        try:
            from faster_whisper import WhisperModel
            model_size = model_path or "tiny"
            self._model = WhisperModel(model_size, device="cpu",
                                       compute_type="int8")
            self.available = True
        except Exception as error:
            self._initialization_error = error

    def transcribe(self, audio_bytes, sample_rate=16000):
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: raw PCM int16 mono audio, or WAV bytes.
            sample_rate: sample rate of the audio (default 16000).

        Returns:
            str: transcribed text, or "" when the audio contains no speech.

        Raises:
            SpeechRecognitionUnavailable: model construction failed.
            SpeechTranscriptionError: inference failed.
        """
        if not self.available or self._model is None:
            detail = (type(self._initialization_error).__name__
                      if self._initialization_error else "unknown")
            raise SpeechRecognitionUnavailable(
                f"speech recognizer unavailable ({detail})"
            ) from self._initialization_error
        with self._transcribe_lock:
            try:
                return self._run_transcription(audio_bytes, sample_rate)
            except Exception as error:
                raise SpeechTranscriptionError(
                    f"speech transcription failed ({type(error).__name__})"
                ) from error

    def _run_transcription(self, audio_bytes, sample_rate):
        """Internal: decode audio and run faster-whisper."""
        import io
        import struct
        import wave

        import numpy as np

        # Try WAV decode
        try:
            wf = wave.open(io.BytesIO(audio_bytes), 'rb')
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
            sr = wf.getframerate()
            if wf.getsampwidth() == 2:
                samples = np.array(struct.unpack(f'<{n_frames}h', raw),
                                   dtype=np.float32) / 32768.0
            else:
                samples = np.frombuffer(raw, dtype=np.uint8).astype(
                    np.float32) / 128.0 - 1.0
            wf.close()
        except Exception:
            samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(
                np.float32) / 32768.0
            sr = sample_rate

        if len(samples) < 100:
            return ""

        # Resample to 16kHz if needed
        if sr != 16000:
            step = max(1, sr // 16000)
            samples = samples[::step]

        # faster-whisper takes float32 numpy array directly
        segments, _ = self._model.transcribe(samples, language="en",
                                             vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()


# ---------------------------------------------------------------------------
# Owned lifecycle: exactly one recognizer per process
# ---------------------------------------------------------------------------

_speech_recognizer = None
_speech_recognizer_lock = threading.Lock()


def get_speech_recognizer():
    """Return exactly one configured SpeechRecognizer per process."""
    global _speech_recognizer
    if _speech_recognizer is None:
        with _speech_recognizer_lock:
            if _speech_recognizer is None:
                _speech_recognizer = SpeechRecognizer(
                    model_path=os.environ.get("WHISPER_MODEL_PATH", "tiny"))
    return _speech_recognizer


def _speech_worker_enabled():
    """True when whisper inference must run in its own OS process.

    Off by default so the embedded (in-process) path — and every existing
    caller and test — is byte-for-byte unchanged.  Turned on in production by
    setting VOICE_WHISPER_WORKER=1 alongside VOICE_WHISPER=1 once the worker
    code is in the image, moving whisper's GIL-heavy CTranslate2 inference out
    of the shared uvicorn process (the tick-starvation / health-probe story).
    Read live (never cached) so config changes take effect without a restart.
    """
    return os.environ.get("VOICE_WHISPER_WORKER", "0") == "1"


def require_speech_recognizer():
    """Ensure the configured recognizer is ready, failing loudly if it is not.

    Worker mode (VOICE_WHISPER_WORKER=1): spawn the out-of-process whisper
    worker and wait for its model to construct — the boot pre-warm path —
    raising SpeechRecognitionUnavailable if it cannot start.  Embedded mode:
    construct the in-process recognizer singleton, unchanged.  Both return a
    handle exposing .available and .transcribe.
    """
    if _speech_worker_enabled():
        return _get_speech_worker().ensure_ready()
    recognizer = get_speech_recognizer()
    if not recognizer.available:
        error = getattr(recognizer, "_initialization_error", None)
        detail = type(error).__name__ if error else "unknown"
        raise SpeechRecognitionUnavailable(
            f"configured speech recognizer unavailable ({detail})"
        ) from error
    return recognizer


def transcribe_sound(audio_bytes):
    """Transcribe one decoded audio event without mutating substrate state.

    Routes to the out-of-process worker when VOICE_WHISPER_WORKER=1, else runs
    the in-process recognizer.  Both paths return the transcript string and
    raise the same typed exceptions; neither ever fabricates words.
    """
    if _speech_worker_enabled():
        return _get_speech_worker().transcribe(audio_bytes)
    return require_speech_recognizer().transcribe(audio_bytes)


# ---------------------------------------------------------------------------
# Honest public status for the boundary transducer
# ---------------------------------------------------------------------------

_TRANSDUCTION_STATUSES = {"not_attempted", "recognized", "no_speech", "error"}


def spoken_word_transduction_status(status, *, transcript=None):
    """Canonical public status when the boundary transducer is configured.

    Mirrors the shape of grounded_vocab.recognition_unavailable() so callers
    and the UI see one consistent contract.  semantic_recognition stays
    False deliberately: Fact-Strand reciprocity remains the only semantic
    authority inside the substrate — this transducer only carries words to
    the same door typed text enters.

    Unknown statuses are programming errors and raise, never fold into a
    generic result (same fail-visible rule as recognition_unavailable()).
    """
    if status not in _TRANSDUCTION_STATUSES:
        raise ValueError(f"unknown transduction status: {status}")
    payload = {
        "capability": "spoken_word_recognition",
        "available": status != "error",
        "status": status,
        "mechanism": "boundary_stt_transducer",
        "raw_sensing": {
            "available": True,
            "mechanism": "sound_krimelack",
            "semantic_recognition": False,
        },
    }
    if transcript:
        payload["transcript"] = transcript
    return payload


# ---------------------------------------------------------------------------
# Out-of-process whisper worker (stage-1 parallel lane)
# ---------------------------------------------------------------------------
#
# Whisper's CTranslate2 inference is a heavy, always-runnable GIL competitor:
# run inside the shared uvicorn process it starves the substrate tick loop and
# the async /ready health probe (measured live: a single converse turn on the
# restored state saturated the process enough that the 5 s container health
# check timed out and ECS killed the task).  Stage 1 moves inference into its
# OWN OS process so the parent never contends for the GIL against it.
#
# Design:
#   - multiprocessing SPAWN, never fork: the parent is a multi-GB, multi-
#     threaded process; fork would copy that whole address space and inherit
#     locks other threads hold.  Spawn starts a fresh minimal interpreter that
#     imports only this module + faster-whisper and loads whisper-tiny
#     (~tens of MB).  The worker target lives here (not in __main__), so the
#     spawned child never re-imports app.py or restarts uvicorn.
#   - The worker owns the one model singleton (a SpeechRecognizer built inside
#     the child) and serves audio-bytes-in / transcript-out over two queues.
#   - Parent-side public surface is unchanged: transcribe_sound /
#     require_speech_recognizer route here transparently, so app.py wiring is
#     untouched.
#   - Fail loud: a worker that cannot build its model, dies mid-request, or
#     times out raises a typed exception the caller surfaces per frame
#     (status="error"/"unavailable").  No path ever fabricates a transcript.
#     A dead worker is respawned automatically on the next demand, once per
#     backoff window, so a crash-looping worker backs off instead of hammering.
#   - Lifecycle: shutdown_speech_worker() terminates and joins the child on
#     deploy seal, following the _curriculum_process terminate/join precedent.

import multiprocessing as _multiprocessing
import queue as _queue
import time as _time

_WORKER_STARTUP_TAG = "__startup__"
_WORKER_SHUTDOWN = "__shutdown__"


def _speech_worker_main(request_q, response_q, model_path):
    """Child entry point: own one recognizer, serve transcription requests.

    Runs in a spawned process.  Announces readiness once (or an unavailable
    model, then exits), then serves (req_id, audio_bytes) requests until asked
    to stop.  A per-request inference failure is reported back and never
    crashes the worker or fabricates words.
    """
    try:
        recognizer = SpeechRecognizer(model_path=model_path)
    except Exception as error:  # pragma: no cover - defensive
        response_q.put((_WORKER_STARTUP_TAG, "unavailable",
                        f"{type(error).__name__}: {error}"))
        return
    if not recognizer.available:
        error = getattr(recognizer, "_initialization_error", None)
        detail = type(error).__name__ if error else "unknown"
        response_q.put((_WORKER_STARTUP_TAG, "unavailable", detail))
        return
    response_q.put((_WORKER_STARTUP_TAG, "ready", ""))
    while True:
        try:
            item = request_q.get()
        except (EOFError, OSError):  # pragma: no cover - parent gone
            return
        if item == _WORKER_SHUTDOWN:
            return
        req_id, audio_bytes = item
        try:
            text = recognizer.transcribe(audio_bytes)
            response_q.put((req_id, "ok", text))
        except SpeechRecognitionUnavailable as error:
            response_q.put((req_id, "unavailable", str(error)))
        except Exception as error:
            response_q.put((req_id, "error",
                            f"{type(error).__name__}: {error}"))


class _SpeechWorkerManager:
    """Parent-side owner of the single out-of-process whisper worker.

    Serializes access under one lock (the caller — app.py's single-worker
    speech-recognition executor — already serializes, this guards spawn /
    respawn / shutdown races).  A dead worker is respawned on the next demand,
    bounded by a backoff window so a crash loop cannot hammer.
    """

    def __init__(self, model_path="tiny", *, worker_target=_speech_worker_main,
                 mp_context=None, startup_timeout=None, request_timeout=None,
                 respawn_backoff=None):
        self._model_path = model_path
        self._worker_target = worker_target
        # Spawn, never fork — see module header.
        self._ctx = mp_context or _multiprocessing.get_context("spawn")
        self._startup_timeout = float(
            startup_timeout if startup_timeout is not None
            else os.environ.get("SPEECH_WORKER_STARTUP_TIMEOUT_S", "60"))
        self._request_timeout = float(
            request_timeout if request_timeout is not None
            else os.environ.get("SPEECH_WORKER_REQUEST_TIMEOUT_S", "30"))
        self._respawn_backoff = float(
            respawn_backoff if respawn_backoff is not None
            else os.environ.get("SPEECH_WORKER_RESPAWN_BACKOFF_S", "5"))
        self._lock = threading.Lock()
        self._proc = None
        self._request_q = None
        self._response_q = None
        self._req_counter = 0
        self._last_spawn_at = None
        self._starts = 0

    # -- lifecycle -----------------------------------------------------------
    @property
    def available(self):
        return self._proc is not None and self._proc.is_alive()

    @property
    def starts(self):
        """How many times a worker process was successfully started (respawns)."""
        return self._starts

    def ensure_ready(self):
        """Start the worker (respecting backoff) and wait for model readiness."""
        with self._lock:
            self._ensure_started_locked()
        return self

    def _ensure_started_locked(self):
        if self._proc is not None and self._proc.is_alive():
            return
        now = _time.monotonic()
        if self._last_spawn_at is not None:
            elapsed = now - self._last_spawn_at
            if elapsed < self._respawn_backoff:
                raise SpeechRecognitionUnavailable(
                    "speech worker respawn backing off "
                    f"({self._respawn_backoff - elapsed:.1f}s remaining)")
        self._reap_locked()
        self._last_spawn_at = now
        self._spawn_locked()

    def _spawn_locked(self):
        request_q = self._ctx.Queue()
        response_q = self._ctx.Queue()
        proc = self._ctx.Process(
            target=self._worker_target,
            args=(request_q, response_q, self._model_path),
            name="speech-whisper-worker",
            daemon=True,
        )
        proc.start()
        try:
            tag, status, detail = response_q.get(timeout=self._startup_timeout)
        except _queue.Empty as error:
            self._force_kill(proc)
            raise SpeechRecognitionUnavailable(
                "speech worker did not report readiness before timeout"
            ) from error
        if tag != _WORKER_STARTUP_TAG or status != "ready":
            self._force_kill(proc)
            raise SpeechRecognitionUnavailable(
                f"speech worker unavailable ({detail or status})")
        self._proc = proc
        self._request_q = request_q
        self._response_q = response_q
        self._starts += 1

    def _reap_locked(self):
        proc = self._proc
        self._proc = None
        self._request_q = None
        self._response_q = None
        if proc is not None and proc.is_alive():
            self._force_kill(proc)

    @staticmethod
    def _force_kill(proc):
        try:
            proc.terminate()
            proc.join(timeout=5)
        except Exception:  # pragma: no cover - best effort
            pass

    # -- request / response --------------------------------------------------
    def transcribe(self, audio_bytes):
        """Round-trip audio to the worker; raise (never fabricate) on failure."""
        with self._lock:
            self._ensure_started_locked()
            self._req_counter += 1
            req_id = self._req_counter
            proc = self._proc
            request_q = self._request_q
            response_q = self._response_q
            try:
                request_q.put((req_id, audio_bytes))
            except Exception as error:
                raise SpeechTranscriptionError(
                    f"speech worker send failed ({type(error).__name__})"
                ) from error
            deadline = _time.monotonic() + self._request_timeout
            while True:
                try:
                    tag, status, payload = response_q.get(timeout=0.1)
                except _queue.Empty:
                    if not proc.is_alive():
                        self._reap_locked()
                        raise SpeechTranscriptionError(
                            "speech worker process died before responding")
                    if _time.monotonic() > deadline:
                        raise SpeechTranscriptionError(
                            "speech worker timed out")
                    continue
                if tag != req_id:
                    continue  # stale startup / prior-request leftover
                if status == "ok":
                    return payload
                if status == "unavailable":
                    raise SpeechRecognitionUnavailable(payload)
                raise SpeechTranscriptionError(
                    payload or "speech transcription failed")

    # -- teardown (deploy seal) ----------------------------------------------
    def shutdown(self, timeout=10.0):
        """Terminate and join the worker (curriculum-process precedent)."""
        with self._lock:
            proc = self._proc
            request_q = self._request_q
            self._proc = None
            self._request_q = None
            self._response_q = None
        if proc is None:
            return {"speech_worker": "not_running"}
        if proc.is_alive():
            try:
                if request_q is not None:
                    request_q.put_nowait(_WORKER_SHUTDOWN)
            except Exception:
                pass
            proc.join(timeout=min(2.0, float(timeout)))
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=float(timeout))
        return {"speech_worker": "stopped", "exitcode": proc.exitcode}


_speech_worker = None
_speech_worker_singleton_lock = threading.Lock()


def _get_speech_worker():
    """Return exactly one worker manager per process (lazily constructed)."""
    global _speech_worker
    if _speech_worker is None:
        with _speech_worker_singleton_lock:
            if _speech_worker is None:
                _speech_worker = _SpeechWorkerManager(
                    model_path=os.environ.get("WHISPER_MODEL_PATH", "tiny"))
    return _speech_worker


def shutdown_speech_worker(timeout=10.0):
    """Terminate and join the out-of-process whisper worker for deploy seal.

    A no-op when no worker was ever started.  Never raises into the seal path:
    the process is being torn down regardless, so a teardown error is reported
    in the return value, not propagated.
    """
    manager = _speech_worker
    if manager is None:
        return {"speech_worker": "not_running"}
    try:
        return manager.shutdown(timeout)
    except Exception as error:  # pragma: no cover - teardown is best-effort
        return {"speech_worker": "shutdown_error",
                "detail": f"{type(error).__name__}: {error}"}
