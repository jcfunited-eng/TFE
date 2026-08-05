from pathlib import Path
import asyncio
import json
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate.grounded_vocab import (
    OBJECT_NAME_RECOGNITION,
    SPOKEN_WORD_RECOGNITION,
    recognition_unavailable,
)
from dsf_ai_service.substrate.grounded_vocab_integration import (
    object_name_recognition_unavailable,
    spoken_word_recognition_unavailable,
)


class _EventOnlyGuala:
    def __init__(self):
        self.events = []

    def _log_substrate_event(self, kind, **detail):
        self.events.append((kind, detail))

    def read_sentence(self, *_args, **_kwargs):
        raise AssertionError("unavailable recognition must never write language")


@pytest.mark.parametrize(
    ("capability", "mechanism"),
    [
        (OBJECT_NAME_RECOGNITION, "sight_krimelack"),
        (SPOKEN_WORD_RECOGNITION, "sound_krimelack"),
    ],
)
def test_unavailable_status_preserves_raw_sensing(capability, mechanism):
    status = recognition_unavailable(capability)

    assert status["capability"] == capability
    assert status["available"] is False
    assert status["status"] == "unavailable"
    assert "unavailable" in status["reason"]
    assert status["raw_sensing"] == {
        "available": True,
        "mechanism": mechanism,
        "semantic_recognition": False,
    }


def test_unknown_capability_fails_loudly():
    with pytest.raises(ValueError, match="unknown recognition capability"):
        recognition_unavailable("invented_recognizer")


def test_integration_only_reports_unavailable_events():
    guala = _EventOnlyGuala()

    object_status = object_name_recognition_unavailable(
        guala, source="camera_stream")
    word_status = spoken_word_recognition_unavailable(
        guala, source="joe_voice")

    assert object_status["status"] == "unavailable"
    assert word_status["status"] == "unavailable"
    assert [kind for kind, _detail in guala.events] == [
        "object_name_recognition_unavailable",
        "spoken_word_recognition_unavailable",
    ]
    assert guala.events[0][1]["raw_sensing"] == "sight_krimelack"
    assert guala.events[1][1]["raw_sensing"] == "sound_krimelack"


def test_retired_runner_stream_handlers_are_absent():
    from dsf_ai_service import substrate_runner

    assert not hasattr(substrate_runner, "handle_sight_frame")
    assert not hasattr(substrate_runner, "handle_sound_frame")
    assert "sight_frame" not in substrate_runner.OP_HANDLERS
    assert "sound_frame" not in substrate_runner.OP_HANDLERS


def test_http_stream_paths_report_unavailable_when_substrate_is_not_ready(
        monkeypatch):
    from dsf_ai_service import app as app_module

    monkeypatch.setattr(app_module, "_guala", None)
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)

    sight_response = asyncio.run(app_module.sight_frame(
        app_module.GLMessage(text="encoded-frame")))
    sound_response = asyncio.run(app_module.sound_frame(
        app_module.GLMessage(text="encoded-audio", source="joe_voice")))
    sight = json.loads(sight_response.body)
    sound = json.loads(sound_response.body)

    assert sight_response.status_code == 503
    assert sight["object_name_recognition"]["status"] == "unavailable"
    assert sound_response.status_code == 503
    assert sound["spoken_word_recognition"]["status"] == "unavailable"


def test_raw_audio_krimelack_transduction_remains_available():
    from dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01 import (
        COCHLEAR_BANDS,
        cochlear_transduce,
    )

    t = np.arange(400, dtype=np.float64) / 200.0
    signal = np.sin(2.0 * np.pi * 18.0 * t)
    result = cochlear_transduce(signal, sample_rate=200)

    assert set(result) == {band["name"] for band in COCHLEAR_BANDS}
    assert all("events" in band and "winding" in band for band in result.values())


def test_production_surfaces_contain_no_pretrained_recognition_authority():
    """Production contains no pretrained recognition or synthesis path."""
    cognition_paths = [
        "dsf_ai_service/substrate/grounded_vocab.py",
        "dsf_ai_service/substrate/grounded_vocab_integration.py",
        "dsf_ai_service/substrate_runner.py",
        "dsf_ai_service/substrate/language_fact_strand.py",
    ]
    forbidden_model_tokens = [
        "faster_whisper",
        "faster-whisper",
        "WhisperModel",
        "VOICE_WHISPER",
        "WHISPER_MODEL_PATH",
        "speech_transducer",
        "transcribe_sound",
        "SpeechRecognition",
        "CTranslate2",
        "ctranslate2",
        "espeak-ng",
        "speechSynthesis",
        "SpeechSynthesisUtterance",
    ]
    all_paths = cognition_paths + [
        "dsf_ai_service/app.py",
        "dsf_ai_service/static/gualaloom.html",
        "dsf_ai_service/static/loomscan.html",
        "dsf_ai_service/Dockerfile",
        "dsf_ai_service/Dockerfile.nogil",
        "tools/deploy_dsf_ai.sh",
    ]
    combined = "\n".join((ROOT / path).read_text() for path in all_paths)
    for token in forbidden_model_tokens:
        assert token not in combined

    forbidden_everywhere = [
        "onnxruntime",
        "yolov8n.onnx",
        "webkitSpeechRecognition",
        "YOLO_MODEL_PATH",
        "process_sight_with_recognition",
        "process_sound_with_recognition",
        "bind_transcribed_speech",
    ]
    for token in forbidden_everywhere:
        assert token not in combined

    assert not (ROOT / "dsf_ai_service/speech_transducer.py").exists()
    assert not (ROOT / "dsf_ai_service/observational_transcription.py").exists()

    html = (ROOT / "dsf_ai_service/static/gualaloom.html").read_text()
    assert "physical auditory L5 experience" in html
    assert "no transcript, word, or recognition" in html
    assert '<input id="msg" type="text"' not in html
    assert "/api/v1/auditory/observations" not in html

    dockerignore = (ROOT / ".dockerignore").read_text()
    assert "!yolov8n.onnx" not in dockerignore
    assert "dsf_ai_service/models/**" in dockerignore
    assert "yolov8n.onnx" in dockerignore
