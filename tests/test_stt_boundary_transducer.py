"""Regression proofs for the owned boundary speech-to-text lifecycle.

Port of tests/test_stt_runtime_ownership.py from stranded commit a8277fa
("fix(stt): own recognizer lifecycle and fail visibly") onto the live
lineage, extended with real functional wiring proofs against the current
/sound_frame handler: the transducer runs at the boundary, the FULL
transcript enters through read_sentence(source="joe") — the same real door
heard/typed speech uses — and every failure is loud, never fabricated or
silently-empty words.

Stubbing discipline: only the model-inference call (transcribe_sound /
_run_transcription) is ever replaced, with a recorded known output; the
plumbing around it — the real sound_frame coroutine, backpressure gates,
executor dispatch, response contract — is real.  The final test runs the
REAL whisper model when faster-whisper is installed (it is in the
production image; skipped where absent).
"""

from concurrent.futures import ThreadPoolExecutor
import asyncio
import base64
import importlib.util
import inspect
import io
import struct
import sys
import threading
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dsf_ai_service.app as appmod  # noqa: E402
import dsf_ai_service.speech_transducer as transducer  # noqa: E402


# ── owned lifecycle: exactly one recognizer per process ─────────────────────

def test_speech_singleton_is_constructed_once_with_configured_model(
        monkeypatch):
    calls = []

    class FakeRecognizer:
        available = True

        def __init__(self, model_path):
            calls.append(model_path)

    monkeypatch.setattr(transducer, "SpeechRecognizer", FakeRecognizer)
    monkeypatch.setenv("WHISPER_MODEL_PATH", "mounted-model")
    monkeypatch.setattr(transducer, "_speech_recognizer", None)

    barrier = threading.Barrier(8)

    def obtain():
        barrier.wait()
        return transducer.get_speech_recognizer()

    with ThreadPoolExecutor(max_workers=8) as executor:
        recognizers = list(executor.map(lambda _: obtain(), range(8)))

    assert calls == ["mounted-model"]
    assert len({id(recognizer) for recognizer in recognizers}) == 1


def test_recognizer_is_reused_across_transcriptions(monkeypatch):
    instances = []

    class FakeRecognizer:
        available = True

        def __init__(self, model_path):
            instances.append(self)
            self.calls = 0

        def transcribe(self, _audio):
            self.calls += 1
            return "recorded words"

    monkeypatch.setattr(transducer, "SpeechRecognizer", FakeRecognizer)
    monkeypatch.setattr(transducer, "_speech_recognizer", None)

    first = transducer.transcribe_sound(b"audio-1")
    second = transducer.transcribe_sound(b"audio-2")

    assert (first, second) == ("recorded words", "recorded words")
    assert len(instances) == 1, "one owned recognizer, reused across calls"
    assert instances[0].calls == 2


# ── visible failure: never collapsed into empty text ────────────────────────

def test_construction_failure_raises_visibly(monkeypatch):
    """A recognizer that cannot be constructed raises, with the cause
    chained — whether faster-whisper is absent (ImportError) or the model
    path is unusable.  Entirely real: no monkeypatched internals."""
    recognizer = transducer.SpeechRecognizer(
        model_path="/nonexistent/whisper-model-dir")

    assert recognizer.available is False
    assert recognizer._initialization_error is not None
    with pytest.raises(transducer.SpeechRecognitionUnavailable):
        recognizer.transcribe(b"audio")

    monkeypatch.setattr(transducer, "_speech_recognizer", recognizer)
    with pytest.raises(transducer.SpeechRecognitionUnavailable):
        transducer.require_speech_recognizer()
    with pytest.raises(transducer.SpeechRecognitionUnavailable):
        transducer.transcribe_sound(b"audio")


def test_transcription_failure_is_not_collapsed_to_empty_text():
    recognizer = transducer.SpeechRecognizer.__new__(
        transducer.SpeechRecognizer)
    recognizer.available = True
    recognizer._model = object()
    recognizer._initialization_error = None
    recognizer._transcribe_lock = threading.Lock()

    def fail(_audio, _sample_rate):
        raise RuntimeError("inference failure")

    recognizer._run_transcription = fail

    with pytest.raises(transducer.SpeechTranscriptionError):
        recognizer.transcribe(b"audio")


def test_unknown_transduction_status_fails_loudly():
    with pytest.raises(ValueError, match="unknown transduction status"):
        transducer.spoken_word_transduction_status("fabricated")


# ── functional wiring: transcription -> read_sentence, through the real
#    /sound_frame handler ────────────────────────────────────────────────────

@pytest.fixture
def clean_frame_state(monkeypatch):
    """Snapshot the app-module state the real handler touches, and stub the
    single unrelated heavy collaborator (the ffmpeg WebM->WAV decode), per
    the convention in tests/test_converse_frame_priority.py."""
    import dsf_ai_service.substrate_runner as sr

    saved_guala = appmod._guala
    saved_inflight = appmod._converse_inflight
    saved_started = appmod._converse_window_started_at
    appmod._converse_inflight = 0
    appmod._converse_window_started_at = 0.0
    monkeypatch.setattr(sr, "_webm_to_wav_bytes", lambda b: b"RIFFwav")
    try:
        yield
    finally:
        appmod._guala = saved_guala
        appmod._converse_inflight = saved_inflight
        appmod._converse_window_started_at = saved_started


def _recording_guala():
    sentences = []
    frames = []
    guala = SimpleNamespace(
        tick=42,
        process_sound_frame=lambda wav, source=None: frames.append(
            (wav, source)),
        read_sentence=lambda text, source=None, bundle_id=None: sentences.append(
            {"text": text, "source": source, "bundle_id": bundle_id}),
    )
    return guala, sentences, frames


def _post_sound_frame(source="joe_voice"):
    return asyncio.run(appmod.sound_frame(
        appmod.GLMessage(text=base64.b64encode(b"webm").decode(),
                         source=source)))


def test_transcribed_speech_enters_through_read_sentence(
        clean_frame_state, monkeypatch):
    monkeypatch.setenv("VOICE_WHISPER", "1")
    guala, sentences, frames = _recording_guala()
    appmod._guala = guala
    # Stub ONLY at the model-inference call, with a recorded known output.
    monkeypatch.setattr(
        transducer, "transcribe_sound", lambda wav: "hello there guala")

    resp = _post_sound_frame()

    assert resp["ok"] is True
    assert resp["raw_sound"] == "accepted"
    assert resp["transcript"] == "hello there guala"
    assert resp["spoken_word_recognition"]["status"] == "recognized"
    assert resp["spoken_word_recognition"]["available"] is True
    # Raw sound STILL reached the substrate (transducer is additive).
    assert frames == [(b"RIFFwav", "joe_voice")]
    # The FULL transcript entered through the one real door heard speech
    # uses, which itself establishes presence (GL-FIX-VOICE-PRESENCE).
    assert sentences == [{
        "text": "hello there guala",
        "source": "joe",
        "bundle_id": "sound_frame:42",
    }]


def test_no_speech_is_honest_and_never_reaches_read_sentence(
        clean_frame_state, monkeypatch):
    monkeypatch.setenv("VOICE_WHISPER", "1")
    guala, sentences, frames = _recording_guala()
    appmod._guala = guala
    monkeypatch.setattr(transducer, "transcribe_sound", lambda wav: "")

    resp = _post_sound_frame()

    assert resp["ok"] is True
    assert resp["spoken_word_recognition"]["status"] == "no_speech"
    assert "transcript" not in resp
    assert sentences == [], "no fabricated words from silent audio"
    assert len(frames) == 1, "raw sound still processed"


def test_transcription_error_is_loud_and_never_fabricates(
        clean_frame_state, monkeypatch):
    monkeypatch.setenv("VOICE_WHISPER", "1")
    guala, sentences, frames = _recording_guala()
    appmod._guala = guala

    def explode(_wav):
        raise transducer.SpeechTranscriptionError(
            "speech transcription failed (RuntimeError)")

    monkeypatch.setattr(transducer, "transcribe_sound", explode)

    resp = _post_sound_frame()

    assert resp["ok"] is False
    assert resp["error"] == "speech_recognition_failed"
    assert resp["spoken_word_recognition"]["status"] == "error"
    assert resp["spoken_word_recognition"]["available"] is False
    assert "transcript" not in resp
    assert sentences == [], "an error NEVER becomes words"
    assert len(frames) == 1, "raw sound experience survives an STT failure"


def test_disabled_flag_keeps_the_honest_unavailable_report(
        clean_frame_state, monkeypatch):
    monkeypatch.delenv("VOICE_WHISPER", raising=False)
    guala, sentences, _frames = _recording_guala()
    guala._log_substrate_event = lambda *a, **k: None
    appmod._guala = guala

    called = []
    monkeypatch.setattr(
        transducer, "transcribe_sound",
        lambda wav: called.append(wav) or "")

    resp = _post_sound_frame()

    assert resp["ok"] is True
    assert resp["spoken_word_recognition"]["status"] == "unavailable"
    assert called == [], "transducer never invoked while disabled"
    assert sentences == []


def test_ambient_sources_are_never_transcribed(clean_frame_state, monkeypatch):
    monkeypatch.setenv("VOICE_WHISPER", "1")
    guala, sentences, _frames = _recording_guala()
    guala._log_substrate_event = lambda *a, **k: None
    appmod._guala = guala

    called = []
    monkeypatch.setattr(
        transducer, "transcribe_sound",
        lambda wav: called.append(wav) or "")

    resp = _post_sound_frame(source="ambient")

    assert resp["ok"] is True
    assert resp["spoken_word_recognition"]["status"] == "unavailable"
    assert called == []
    assert sentences == []


def test_live_sound_route_owns_one_recognizer_and_starts_it_before_raw_sense():
    """a8277fa's structural proof, against the current handler: recognition
    is submitted to the owned single-worker executor BEFORE raw-sense
    processing, its result is awaited, and the honest status is returned."""
    source = inspect.getsource(appmod.sound_frame)
    module_source = inspect.getsource(appmod)

    assert "_th.Thread(target=_whisper_bg" not in module_source
    assert "_speech_recognition_executor.submit" in source
    assert source.index("_speech_recognition_executor.submit") < source.index(
        "_guala.process_sound_frame")
    assert "recognition_future.result()" in source
    assert "spoken_word_transduction_status" in source
    assert 'thread_name_prefix="speech-recognition"' in module_source
    assert "max_workers=1" in module_source


# ── the real model, where installed (always true in the production image) ───

def _wav_bytes(samples_int16, sample_rate=16000):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples_int16)}h",
                                   *samples_int16))
    return buffer.getvalue()


@pytest.mark.skipif(
    importlib.util.find_spec("faster_whisper") is None,
    reason="faster-whisper not installed in this environment "
           "(it IS pinned in the production image)")
def test_real_whisper_transcribes_silence_to_empty_never_fabricates():
    recognizer = transducer.SpeechRecognizer(model_path="tiny")
    assert recognizer.available, recognizer._initialization_error

    silence = _wav_bytes([0] * 16000)  # one second of real silence
    assert recognizer.transcribe(silence) == ""
