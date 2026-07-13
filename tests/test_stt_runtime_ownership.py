"""Regression proofs for the owned production speech-recognition lifecycle."""

from concurrent.futures import ThreadPoolExecutor
import inspect
import threading

import pytest

from dsf_ai_service.substrate import grounded_vocab
from dsf_ai_service.substrate import grounded_vocab_integration as integration


def test_speech_singleton_is_constructed_once_with_configured_model(monkeypatch):
    calls = []

    class FakeRecognizer:
        available = True

        def __init__(self, model_path):
            calls.append(model_path)

    monkeypatch.setattr(integration, "SpeechRecognizer", FakeRecognizer)
    monkeypatch.setattr(integration, "WHISPER_MODEL_PATH", "mounted-model")
    monkeypatch.setattr(integration, "_speech_recognizer", None)

    barrier = threading.Barrier(8)

    def obtain():
        barrier.wait()
        return integration.get_speech_recognizer()

    with ThreadPoolExecutor(max_workers=8) as executor:
        recognizers = list(executor.map(lambda _: obtain(), range(8)))

    assert calls == ["mounted-model"]
    assert len({id(recognizer) for recognizer in recognizers}) == 1


def test_transcription_failure_is_not_collapsed_to_empty_text():
    recognizer = grounded_vocab.SpeechRecognizer.__new__(
        grounded_vocab.SpeechRecognizer
    )
    recognizer.available = True
    recognizer._model = object()
    recognizer._initialization_error = None
    recognizer._transcribe_lock = threading.Lock()

    def fail(_audio, _sample_rate):
        raise RuntimeError("inference failure")

    recognizer._run_transcription = fail

    with pytest.raises(grounded_vocab.SpeechTranscriptionError):
        recognizer.transcribe(b"audio")


def test_live_sound_route_owns_one_recognizer_and_starts_it_before_raw_sense():
    from dsf_ai_service import app as app_module

    source = inspect.getsource(app_module.sound_frame)
    module_source = inspect.getsource(app_module)

    assert "_th.Thread(target=_whisper_bg" not in source
    assert "_speech_recognition_executor.submit" in source
    assert source.index("_speech_recognition_executor.submit") < source.index(
        "_guala.process_sound_frame"
    )
    assert "recognition_future.result()" in source
    assert '"speech_recognition": recognition_status' in source
    assert "max_workers=1" in module_source
