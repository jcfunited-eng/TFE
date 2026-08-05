from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_microphone_ingress_is_capability_gated_and_same_origin() -> None:
    page = _page()
    assert 'const cap=capability("microphone");if(!cap.available)return' in page
    assert 'safeEndpoint(value?.endpoint)' in page
    assert 'new URL(value,location.origin)' in page
    assert 'parsed.origin===location.origin' in page
    assert 'credentials:"same-origin"' in page
    assert "/api/v1/auditory/binaural-pcm/" not in page
    assert "/sound_frame" not in page


def test_microphone_is_a_true_toggle_with_track_cleanup() -> None:
    page = _page()
    assert "async function toggleMicrophone(){if(microphoneStream||microphoneStarting)stopMicrophone();else await startMicrophone()}" in page
    assert "microphoneStream.getTracks().forEach" not in page
    assert "if(stream)stream.getTracks().forEach(track=>track.stop())" in page
    assert "microphoneRecorder=null;microphoneStream=null" in page
    assert "microphoneStarting" in page
    assert "microphoneStream!==acquired" in page
    assert "microphoneStream===acquired" in page
    assert 'if(!microphone.available&&(microphoneStream!==null||microphoneStarting)){stopMicrophone("Microphone stopped · native capability withdrawn");return}' in page
    assert "if(token!==microphoneStartToken){acquired.getTracks().forEach(track=>track.stop());return}" in page
    assert 'if(!capability("microphone").available){acquired.getTracks().forEach(track=>track.stop());stopMicrophone("Microphone stopped · native capability withdrawn");return}' in page
    assert "Local microphone off · organism ingress not established" in page


def test_microphone_capture_is_bounded_and_fail_closed() -> None:
    page = _page()
    assert "if(microphoneInFlight)" in page
    assert "native processing fell behind the bounded stream" in page
    assert "microphoneInFlight=true" in page
    assert "finally{microphoneInFlight=false}" in page
    assert "Math.max(500,Math.min(5000" in page
    assert "native acceptance failed" in page
    assert "if(!response.ok||result.accepted!==true)" in page


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


def test_camera_capture_has_one_bounded_inflight_request() -> None:
    page = _page()
    assert "if(!cameraStream||cameraInFlight)return" in page
    assert "cameraInFlight=true" in page
    assert "finally{cameraInFlight=false}" in page
    assert "Math.max(1000,Math.min(15000" in page
    assert "Camera stopped · native acceptance failed" in page


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
