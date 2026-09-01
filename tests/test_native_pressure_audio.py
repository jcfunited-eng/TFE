from __future__ import annotations

import hashlib
import io
from pathlib import Path
import struct
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
        "_native_pressure_audio_cache",
        ({
            "pcm_s16le": b"\x01\x00\xff\xff",
            "pressure_sha256": PRESSURE_SHA256,
            "sample_count": 2,
            "sample_rate_hz": 16_000,
        },),
    )

    observation = production._articulation_record()
    playback = observation["native_pressure_playback"]
    response = production.native_pressure_audio(PRESSURE_SHA256)

    assert playback["available"] is True
    assert playback["endpoint"] == (
        production.NATIVE_PRESSURE_AUDIO_ENDPOINT
        + f"?pressure_sha256={PRESSURE_SHA256}"
    )
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
        "_native_pressure_audio_cache",
        ({
            "pcm_s16le": b"\x01\x00\xff\xff",
            "pressure_sha256": "b" * 64,
            "sample_count": 2,
            "sample_rate_hz": 16_000,
        },),
    )

    playback = production._articulation_record()["native_pressure_playback"]

    assert playback["available"] is False
    assert playback["endpoint"] is None


def test_native_pressure_cache_is_bounded_by_count_and_exact_pcm_bytes() -> None:
    extent = production.NATIVE_PRESSURE_AUDIO_CACHE_MAX_ENTRY_BYTES
    candidates = tuple(
        {"ordinal": ordinal, "pcm_s16le": bytes([ordinal]) * extent}
        for ordinal in range(6)
    )

    retained = production._bounded_native_pressure_audio_cache(candidates)

    assert [entry["ordinal"] for entry in retained] == [2, 3, 4, 5]
    assert sum(len(entry["pcm_s16le"]) for entry in retained) == (
        production.NATIVE_PRESSURE_AUDIO_CACHE_MAX_BYTES
    )
    assert production._bounded_native_pressure_audio_cache(
        ({"pcm_s16le": b"x" * (extent + 1)},)
    ) == ()


def test_gualaloom_plays_only_the_exact_native_pressure_endpoint() -> None:
    page = PAGE.read_text(encoding="utf-8")

    assert "Hear raw native pressure" in page
    assert "Hear Guala" in page
    assert "X-Guala-Pressure-SHA256" in page
    assert "new Audio(nativePressureUrl)" in page
    assert "speechSynthesis" not in page


def _articulatory_interval(pressure: tuple[int, ...]) -> tuple[object, ...]:
    body = struct.pack(
        f"<{production.ARTICULATORY_BODY_PORT_COUNT * len(pressure)}h",
        *(pressure + pressure + pressure + ((0,) * len(pressure))),
    )
    return (
        (),
        pressure,
        body,
        b"body-state",
        max(pressure),
        len(pressure),
        20,
        7,
        3,
        0,
    )


def _consumed(candidate: dict[str, object]) -> dict[str, object]:
    return {
        "coexisting_emitted_neuron_fractal_count": 2,
        "coexisting_transitioned_neuron_count": 19,
        "pressure_sha256": candidate["pressure_sha256"],
        "receptor_ingress_sound_count": production.EAR_PORT_COUNT,
        "remaining_sample_count": 0,
        "sample_count": candidate["pressure_sample_count"],
    }


def test_multi_hop_observer_selects_newest_exact_all_ear_return() -> None:
    first = production._articulation_candidate_from_hop(
        (_articulatory_interval((11, 13)),),
        (),
    )
    second = production._articulation_candidate_from_hop(
        (_articulatory_interval((17, 19)),),
        (),
    )
    assert first is not None and second is not None

    selected = production._newest_exact_self_heard_articulation(
        (first, second),
        (_consumed(first[0]), _consumed(second[0])),
    )

    assert selected is not None
    evidence, pressure = selected
    assert evidence["pressure_sha256"] == second[0]["pressure_sha256"]
    assert pressure == second[1]
    assert evidence["pressure_sample_count"] == 2
    assert evidence["self_hearing_hop_count"] == 1
    assert evidence["self_hearing_receptor_ingress_count"] == (
        production.EAR_PORT_COUNT
    )
    assert evidence["self_hearing_transitioned_neuron_count"] == 19
    assert evidence["articulatory_body_receptor_ingress_count"] == 4


def test_multi_hop_observer_never_matches_a_concatenated_pressure() -> None:
    first = production._articulation_candidate_from_hop(
        (_articulatory_interval((11, 13)),),
        (),
    )
    second = production._articulation_candidate_from_hop(
        (_articulatory_interval((17, 19)),),
        (),
    )
    assert first is not None and second is not None
    concatenated = {
        **_consumed(first[0]),
        "pressure_sha256": hashlib.sha256(first[1] + second[1]).hexdigest(),
        "sample_count": 4,
    }

    selected = production._newest_exact_self_heard_articulation(
        (first, second),
        (concatenated,),
    )

    assert selected is not None
    evidence, pressure = selected
    assert evidence["pressure_sha256"] == second[0]["pressure_sha256"]
    assert pressure == second[1]
    assert evidence["self_hearing_hop_count"] == 0
    assert evidence["self_hearing_pressure_sha256"] is None
