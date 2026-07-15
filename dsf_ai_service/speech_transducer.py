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


def require_speech_recognizer():
    """Construct the recognizer and fail loudly if it is unavailable."""
    recognizer = get_speech_recognizer()
    if not recognizer.available:
        error = getattr(recognizer, "_initialization_error", None)
        detail = type(error).__name__ if error else "unknown"
        raise SpeechRecognitionUnavailable(
            f"configured speech recognizer unavailable ({detail})"
        ) from error
    return recognizer


def transcribe_sound(audio_bytes):
    """Transcribe one decoded audio event without mutating substrate state."""
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
