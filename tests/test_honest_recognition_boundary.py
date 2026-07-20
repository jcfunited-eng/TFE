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


def test_stream_handlers_report_unavailable_on_invalid_input(monkeypatch):
    from dsf_ai_service import substrate_runner

    monkeypatch.setattr(substrate_runner, "_guala", None)
    sight = substrate_runner.handle_sight_frame({"text": ""})
    sound = substrate_runner.handle_sound_frame({"text": ""})

    assert sight["ok"] is False
    assert sight["object_name_recognition"]["status"] == "unavailable"
    assert sound["ok"] is False
    assert sound["spoken_word_recognition"]["status"] == "unavailable"


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
    """Semantic recognition inside the substrate stays Fact-Strand-only.

    Amended for the a8277fa STT port (2026-07-15): a boundary speech-to-text
    TRANSDUCER (dsf_ai_service/speech_transducer.py) is permitted at the
    service edge only — it converts audio to words exactly like the ffmpeg
    decode converts WebM to WAV, and the words enter through read_sentence
    like typed text.  It is NOT a semantic authority: no cognition surface
    may import or name it, and nothing anywhere may reinstate object-naming
    classifiers or the legacy vocab-binding path
    (process_*_with_recognition / confidence-tagged atlas writes).
    """
    cognition_paths = [
        "dsf_ai_service/substrate/grounded_vocab.py",
        "dsf_ai_service/substrate/grounded_vocab_integration.py",
        "dsf_ai_service/substrate_runner.py",
        "dsf_ai_service/substrate/language_fact_strand.py",
        "dsf_ai_service/v4/gualaloom_v5_engine.py",
    ]
    stt_tokens = [
        "faster_whisper",
        "WhisperModel",
        "VOICE_WHISPER",
        "WHISPER_MODEL_PATH",
        "speech_transducer",
        "transcribe_sound",
        "SpeechRecognition",
    ]
    cognition_combined = "\n".join(
        (ROOT / path).read_text() for path in cognition_paths)
    for token in stt_tokens:
        assert token not in cognition_combined, (
            f"STT transducer token {token!r} leaked into a cognition surface")

    all_paths = cognition_paths + [
        "dsf_ai_service/app.py",
        "dsf_ai_service/speech_transducer.py",
        "dsf_ai_service/static/gualaloom.html",
        "dsf_ai_service/Dockerfile",
        "dsf_ai_service/Dockerfile.nogil",
        "tools/deploy_dsf_ai.sh",
    ]
    forbidden_everywhere = [
        "onnxruntime",
        "yolov8n.onnx",
        "webkitSpeechRecognition",
        "YOLO_MODEL_PATH",
        "process_sight_with_recognition",
        "process_sound_with_recognition",
        "bind_transcribed_speech",
    ]
    combined = "\n".join((ROOT / path).read_text() for path in all_paths)
    for token in forbidden_everywhere:
        assert token not in combined

    # The transducer itself never reaches INTO the substrate: it imports
    # nothing from this codebase and never touches memory or language.
    transducer = (ROOT / "dsf_ai_service/speech_transducer.py").read_text()
    assert "class SpeechRecognizer" in transducer
    assert "SpeechRecognitionUnavailable" in transducer
    assert "SpeechTranscriptionError" in transducer
    assert "from dsf_ai_service" not in transducer
    assert "import dsf_ai_service" not in transducer
    assert "read_sentence" not in transducer
    assert "_atlas_record" not in transducer

    # app.py owns one recognizer on a dedicated executor and transcripts
    # enter through the one real door (read_sentence), failing loudly.
    app_text = (ROOT / "dsf_ai_service/app.py").read_text()
    assert "_speech_recognition_executor.submit" in app_text
    assert "max_workers=1" in app_text
    assert "speech_recognition_failed" in app_text

    # The image carries the pinned transducer runtime and bakes the model
    # at build time; the nogil experiment image and the deploy script stay
    # transducer-free (task-def env is not the flag authority anymore).
    dockerfile = (ROOT / "dsf_ai_service/Dockerfile").read_text()
    assert "faster-whisper==" in dockerfile
    assert "WhisperModel('tiny'" in dockerfile
    assert "ENV VOICE_WHISPER=1" in dockerfile
    nogil_dockerfile = (ROOT / "dsf_ai_service/Dockerfile.nogil").read_text()
    for token in ["faster_whisper", "faster-whisper", "WhisperModel",
                  "VOICE_WHISPER", "WHISPER_MODEL_PATH"]:
        assert token not in nogil_dockerfile
    # The live acceptance gate has passed: production must explicitly keep
    # the boundary sense enabled.  This remains configuration, not recognition
    # authority; the deploy script still may not name model/library surfaces.
    deploy_script = (ROOT / "tools/deploy_dsf_ai.sh").read_text()
    for token in ["faster_whisper", "faster-whisper", "WhisperModel",
                  "WHISPER_MODEL_PATH"]:
        assert token not in deploy_script
    assert deploy_script.count(
        "{'name': 'VOICE_WHISPER', 'value': '1'}") == 1
    assert "{'name': 'VOICE_WHISPER', 'value': '0'}" not in deploy_script

    html = (ROOT / "dsf_ai_service/static/gualaloom.html").read_text()
    assert "spoken-word recognition unavailable" in html
    assert "object naming unavailable" in html
    assert '<input id="msg" type="text"' in html

    dockerignore = (ROOT / ".dockerignore").read_text()
    assert "!yolov8n.onnx" not in dockerignore
    assert "dsf_ai_service/models/**" in dockerignore
    assert "yolov8n.onnx" in dockerignore
