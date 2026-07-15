"""Regression proofs for the out-of-process whisper worker (stage-1 lane).

Stage 1 of the ratified continuous-existence build moves whisper's GIL-heavy
CTranslate2 inference out of the shared uvicorn process into its OWN OS
process (multiprocessing spawn), so a converse turn plus continuous sound
frames can no longer starve the substrate tick loop / the container /ready
health probe.  These tests exercise the REAL mechanism — real spawned
processes, real queues, real death and respawn — never a mocked process:

  - round-trip: audio bytes in, transcript out, over a spawned worker;
  - the REAL whisper model in the child (espeak audio, like the existing
    zero-stub e2e test), silence -> "" and speech -> non-empty, never
    fabricated;
  - worker death is visible per-request (a typed error, never a fabricated
    transcript) and the worker respawns automatically on the next demand;
  - startup failure (unbuildable model) is surfaced loudly, not as silence;
  - a per-request inference error is reported without crashing the worker;
  - seal teardown terminates and joins the child (deploy-seal lifecycle);
  - the public surface (transcribe_sound / require_speech_recognizer) routes
    to the worker only when VOICE_WHISPER_WORKER=1, and is otherwise the
    unchanged in-process path.

Fake worker targets are module-level (picklable across spawn); the tests dir
is placed on sys.path so the spawned child can import this module to resolve
them, independent of pytest's import mode.
"""

import importlib.util
import io
import os
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
for _p in (str(_ROOT), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dsf_ai_service.speech_transducer as transducer  # noqa: E402
from dsf_ai_service.speech_transducer import (  # noqa: E402
    _SpeechWorkerManager,
    _WORKER_SHUTDOWN,
    _WORKER_STARTUP_TAG,
)

_HAVE_WHISPER = importlib.util.find_spec("faster_whisper") is not None


# ── module-level fake worker targets (spawn-picklable) ──────────────────────

def _fake_worker_echo_crash(request_q, response_q, model_path):
    """Ready worker that echoes audio, but exits hard on a b"__die__" frame."""
    response_q.put((_WORKER_STARTUP_TAG, "ready", ""))
    while True:
        item = request_q.get()
        if item == _WORKER_SHUTDOWN:
            return
        req_id, audio = item
        if audio == b"__die__":
            os._exit(7)  # simulate a crash mid-request (no response sent)
        response_q.put((req_id, "ok", "heard:" + audio.decode("utf-8", "ignore")))


def _fake_worker_unavailable(request_q, response_q, model_path):
    """Worker whose model cannot be built: reports unavailable, then exits."""
    response_q.put((_WORKER_STARTUP_TAG, "unavailable", "faster_whisper missing"))


def _fake_worker_inference_error(request_q, response_q, model_path):
    """Ready worker that reports a per-request inference error and stays up."""
    response_q.put((_WORKER_STARTUP_TAG, "ready", ""))
    while True:
        item = request_q.get()
        if item == _WORKER_SHUTDOWN:
            return
        req_id, _audio = item
        response_q.put((req_id, "error", "RuntimeError: inference exploded"))


# ── helpers ─────────────────────────────────────────────────────────────────

def _fake_manager(target, **kwargs):
    kwargs.setdefault("startup_timeout", 20.0)
    kwargs.setdefault("request_timeout", 10.0)
    kwargs.setdefault("respawn_backoff", 0.0)
    return _SpeechWorkerManager("tiny", worker_target=target, **kwargs)


def _wav_bytes(samples_int16, sample_rate=16000):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples_int16)}h", *samples_int16))
    return buffer.getvalue()


def _espeak_wav(text):
    """Real spoken audio via espeak-ng, or None when espeak is absent."""
    if not (subprocess.run(["which", "espeak-ng"],
                           capture_output=True).returncode == 0):
        return None
    out = _HERE / "_stt_worker_espeak.wav"
    subprocess.run(["espeak-ng", "-w", str(out), "-s", "130", text], check=True)
    data = out.read_bytes()
    try:
        out.unlink()
    except OSError:
        pass
    return data


# ── round-trip over a real spawned process ──────────────────────────────────

def test_worker_round_trip_over_real_process():
    manager = _fake_manager(_fake_worker_echo_crash)
    try:
        assert manager.transcribe(b"hello") == "heard:hello"
        assert manager.transcribe(b"again") == "heard:again"
        assert manager.starts == 1, "one worker, reused across requests"
        assert manager.available
    finally:
        manager.shutdown(5.0)


# ── the REAL whisper model, in the child process ────────────────────────────

@pytest.mark.skipif(not _HAVE_WHISPER,
                    reason="faster-whisper not installed (it IS in the image)")
def test_real_model_round_trip_silence_empty_speech_nonempty():
    manager = _SpeechWorkerManager(
        "tiny", startup_timeout=120.0, request_timeout=60.0)
    try:
        # Real silence transcribes to honest empty — the model actually ran in
        # the child and did not fabricate a word.
        assert manager.transcribe(_wav_bytes([0] * 16000)) == ""
        # Real spoken audio round-trips to a non-empty transcript through the
        # process boundary (whisper-tiny garbles espeak, but never returns
        # empty for clear speech — we assert presence, not exact words).
        speech = _espeak_wav("hello hello hello there guala")
        if speech is not None:
            out = manager.transcribe(speech)
            assert isinstance(out, str)
            assert out.strip() != "", "clear speech must not vanish to empty"
    finally:
        manager.shutdown(10.0)


# ── worker death: visible, never fabricated, auto-respawn ────────────────────

def test_worker_death_is_visible_and_never_fabricates_and_respawns():
    manager = _fake_manager(_fake_worker_echo_crash)
    try:
        assert manager.transcribe(b"one") == "heard:one"
        assert manager.starts == 1
        first_pid = manager._proc.pid

        # A worker that dies mid-request raises a typed error — never a
        # fabricated or silently-empty transcript.
        with pytest.raises(transducer.SpeechTranscriptionError):
            manager.transcribe(b"__die__")
        assert not manager.available, "the death is observed, not hidden"

        # The next demand respawns the worker automatically (single respawn,
        # backoff=0) and the round-trip works again on a NEW process.
        assert manager.transcribe(b"two") == "heard:two"
        assert manager.starts == 2, "worker respawned exactly once"
        assert manager._proc.pid != first_pid, "a genuinely new process"
    finally:
        manager.shutdown(5.0)


def test_respawn_backoff_blocks_immediate_hammering():
    manager = _fake_manager(_fake_worker_echo_crash, respawn_backoff=30.0)
    try:
        assert manager.transcribe(b"one") == "heard:one"
        with pytest.raises(transducer.SpeechTranscriptionError):
            manager.transcribe(b"__die__")
        # Within the backoff window the next demand refuses to respawn and
        # says so honestly instead of crash-looping.
        with pytest.raises(transducer.SpeechRecognitionUnavailable,
                           match="backing off"):
            manager.transcribe(b"two")
    finally:
        manager.shutdown(5.0)


# ── startup failure and inference error are loud, never silent ──────────────

def test_worker_startup_failure_is_visible():
    manager = _fake_manager(_fake_worker_unavailable)
    with pytest.raises(transducer.SpeechRecognitionUnavailable):
        manager.ensure_ready()
    assert not manager.available


def test_worker_inference_error_is_loud_and_worker_survives():
    manager = _fake_manager(_fake_worker_inference_error)
    try:
        with pytest.raises(transducer.SpeechTranscriptionError):
            manager.transcribe(b"whatever")
        # A handled inference error does not kill the worker.
        assert manager.available
    finally:
        manager.shutdown(5.0)


# ── seal teardown terminates and joins the child ────────────────────────────

def test_seal_teardown_terminates_and_joins_the_worker():
    manager = _fake_manager(_fake_worker_echo_crash)
    manager.ensure_ready()
    proc = manager._proc
    assert proc.is_alive()

    proof = manager.shutdown(10.0)

    assert proof["speech_worker"] == "stopped"
    assert not proc.is_alive(), "the child is really gone after seal"
    assert not manager.available


def test_module_shutdown_helper_stops_the_singleton(monkeypatch):
    manager = _fake_manager(_fake_worker_echo_crash)
    manager.ensure_ready()
    monkeypatch.setattr(transducer, "_speech_worker", manager)
    proof = transducer.shutdown_speech_worker(10.0)
    assert proof["speech_worker"] == "stopped"
    assert not manager.available


def test_module_shutdown_helper_is_noop_when_never_started(monkeypatch):
    monkeypatch.setattr(transducer, "_speech_worker", None)
    assert transducer.shutdown_speech_worker()["speech_worker"] == "not_running"


# ── public-surface routing: worker only when explicitly enabled ─────────────

def test_transcribe_sound_routes_to_worker_when_enabled(monkeypatch):
    monkeypatch.setenv("VOICE_WHISPER_WORKER", "1")
    seen = []

    class _StubManager:
        def transcribe(self, audio):
            seen.append(audio)
            return "from-worker"

    monkeypatch.setattr(transducer, "_get_speech_worker", lambda: _StubManager())
    assert transducer.transcribe_sound(b"aud") == "from-worker"
    assert seen == [b"aud"]


def test_require_speech_recognizer_readies_worker_when_enabled(monkeypatch):
    monkeypatch.setenv("VOICE_WHISPER_WORKER", "1")
    readied = []

    class _StubManager:
        available = True

        def ensure_ready(self):
            readied.append(True)
            return self

    monkeypatch.setattr(transducer, "_get_speech_worker", lambda: _StubManager())
    handle = transducer.require_speech_recognizer()
    assert readied == [True]
    assert handle.available is True


def test_disabled_worker_flag_keeps_the_in_process_path(monkeypatch):
    monkeypatch.delenv("VOICE_WHISPER_WORKER", raising=False)

    class _FakeRecognizer:
        available = True

        def __init__(self, model_path):
            pass

        def transcribe(self, _audio):
            return "in-process"

    monkeypatch.setattr(transducer, "SpeechRecognizer", _FakeRecognizer)
    monkeypatch.setattr(transducer, "_speech_recognizer", None)

    def _boom():
        raise AssertionError("worker must not be used when the flag is off")

    monkeypatch.setattr(transducer, "_get_speech_worker", _boom)
    assert transducer.transcribe_sound(b"aud") == "in-process"


def test_worker_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv("VOICE_WHISPER_WORKER", raising=False)
    assert transducer._speech_worker_enabled() is False
    monkeypatch.setenv("VOICE_WHISPER_WORKER", "1")
    assert transducer._speech_worker_enabled() is True
