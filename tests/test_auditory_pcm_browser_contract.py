from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_browser_audio_is_transport_not_recognition_or_meaning() -> None:
    page = _page()
    assert 'schema:"guala.native.browser_audio_chunk.v1"' in page
    assert "audio_b64:bytesToBase64(bytes)" in page
    assert "recognized_form" not in page
    assert "spoken_word_recognition" not in page
    assert "replying to:" not in page
    assert "meaning authority" not in page.lower()


def test_local_capture_and_organism_acceptance_are_distinct_states() -> None:
    page = _page()
    assert "Local microphone active · no organism acceptance yet" in page
    assert "Local microphone active · organism accepted generation" in page
    assert "microphoneAccepted=true" in page
    assert "microphoneAccepted=false" in page


def test_hidden_document_stops_local_sensory_capture() -> None:
    page = _page()
    assert 'document.addEventListener("visibilitychange"' in page
    assert 'stopCamera("Camera stopped while page is hidden")' in page
    assert 'stopMicrophone("Microphone stopped while page is hidden")' in page
    assert "if(pollAbort)pollAbort.abort()" in page


def test_no_browser_side_audio_queue_or_epoch_authority_remains() -> None:
    page = _page()
    forbidden = (
        "PCM_RING_SAMPLES",
        "PCM_MAX_PENDING_CHUNKS",
        "source_epoch_start_ns",
        "AudioWorklet",
        "auditoryTerminalSeen",
        "W1BinauralAuditoryL5Owner",
    )
    for marker in forbidden:
        assert marker not in page
