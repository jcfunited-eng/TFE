"""Production must have no pretrained perception or synthetic voice path."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "dsf_ai_service"

FORBIDDEN_RUNTIME_TOKENS = (
    "faster-whisper",
    "faster_whisper",
    "WhisperModel",
    "CTranslate2",
    "ctranslate2",
    "VOICE_WHISPER",
    "speech_transducer",
    "observational_transcription",
    "espeak-ng",
    "speechSynthesis",
    "SpeechSynthesisUtterance",
    "webkitSpeechRecognition",
    "/api/v1/auditory/observations",
)


def _production_sources() -> tuple[Path, ...]:
    runtime = tuple(
        path
        for path in RUNTIME_ROOT.rglob("*")
        if (
            path.is_file()
            and (
                path.suffix in {".py", ".html"}
                or path.name.startswith("Dockerfile")
            )
            and not path.name.startswith("test_")
        )
    )
    operational = (
        ROOT / "tools" / "deploy_dsf_ai.sh",
        ROOT / "tools" / "probe_guala_candidate_browser.py",
    )
    return tuple(sorted((*runtime, *operational)))


def test_production_has_no_ml_recognition_or_tts_support() -> None:
    violations: list[str] = []
    for path in _production_sources():
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_RUNTIME_TOKENS:
            if token in source:
                violations.append(
                    f"{path.relative_to(ROOT)} contains {token!r}"
                )
    assert violations == []


def test_removed_model_owners_and_observation_route_stay_absent() -> None:
    assert not (RUNTIME_ROOT / "speech_transducer.py").exists()
    assert not (RUNTIME_ROOT / "observational_transcription.py").exists()

    app_source = (RUNTIME_ROOT / "app.py").read_text(encoding="utf-8")
    ui_source = (
        RUNTIME_ROOT / "static" / "gualaloom.html"
    ).read_text(encoding="utf-8")
    assert "_speech_recognition_executor" not in app_source
    assert "_observational_transcription_owner" not in app_source
    assert "def _auditory_l5_spoken_report(" not in app_source
    assert "/api/v1/auditory/observations" not in app_source
    assert "/api/v1/auditory/observations" not in ui_source
