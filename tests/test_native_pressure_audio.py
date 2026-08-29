from __future__ import annotations

import io
from pathlib import Path
import wave

from dsf_ai_service import native_production_app as production


PAGE = Path(production.__file__).parent / "static" / "gualaloom.html"
PRESSURE_SHA256 = "a" * 64


def _wav_body() -> bytes:
    body = io.BytesIO()
    with wave.open(body, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16_000)
        output.writeframes(b"\x01\x00\xff\xff")
    return body.getvalue()


def test_latest_native_pressure_is_a_bounded_read_only_audio_surface(
    monkeypatch,
) -> None:
    wav_body = _wav_body()
    monkeypatch.setattr(
        production,
        "_last_tested_articulation_evidence",
        {
            "pressure_sample_count": 2,
            "pressure_sha256": PRESSURE_SHA256,
            "sample_rate_hz": 16_000,
        },
    )
    monkeypatch.setattr(
        production,
        "_latest_native_pressure_audio",
        {
            "pcm_s16le": b"\x01\x00\xff\xff",
            "pressure_sha256": PRESSURE_SHA256,
            "sample_count": 2,
            "sample_rate_hz": 16_000,
        },
    )

    observation = production._articulation_record()
    playback = observation["native_pressure_playback"]
    response = production.native_pressure_audio()

    assert playback["available"] is True
    assert playback["endpoint"] == production.NATIVE_PRESSURE_AUDIO_ENDPOINT
    assert playback["pressure_sha256"] == PRESSURE_SHA256
    assert response.body == wav_body
    assert response.media_type == "audio/wav"
    assert response.headers["x-guala-pressure-sha256"] == PRESSURE_SHA256


def test_articulation_cannot_offer_pressure_from_a_different_event(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        production,
        "_last_tested_articulation_evidence",
        {
            "pressure_sample_count": 2,
            "pressure_sha256": PRESSURE_SHA256,
            "sample_rate_hz": 16_000,
        },
    )
    monkeypatch.setattr(
        production,
        "_latest_native_pressure_audio",
        {
            "pcm_s16le": b"\x01\x00\xff\xff",
            "pressure_sha256": "b" * 64,
            "sample_count": 2,
            "sample_rate_hz": 16_000,
        },
    )

    playback = production._articulation_record()["native_pressure_playback"]

    assert playback["available"] is False
    assert playback["endpoint"] is None


def test_gualaloom_plays_only_the_exact_native_pressure_endpoint() -> None:
    page = PAGE.read_text(encoding="utf-8")

    assert "Hear latest native pressure" in page
    assert "X-Guala-Pressure-SHA256" in page
    assert "new Audio(nativePressureUrl)" in page
    assert "speechSynthesis" not in page
