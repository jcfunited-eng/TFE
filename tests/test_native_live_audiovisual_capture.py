from __future__ import annotations

import base64
from fractions import Fraction
from io import BytesIO
import json
import struct
from pathlib import Path

from PIL import Image
import pytest

from dsf_ai_service import native_production_app as production


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"


def _payload(*, frame_count: int = 4, sample_count: int = 16_000) -> dict:
    raster = BytesIO()
    Image.new("L", (9, 3), color=96).save(raster, format="PNG")
    encoded_frame = base64.b64encode(raster.getvalue()).decode("ascii")
    pcm = struct.pack(f"<{sample_count}h", *([1_000] * sample_count))
    return {
        "schema": production.LIVE_AUDIOVISUAL_SCHEMA,
        "source": production.LIVE_AUDIOVISUAL_SOURCE,
        "frames": [
            {
                "captured_at_ms": 1_000 + index * 250,
                "png_base64": encoded_frame,
            }
            for index in range(frame_count)
        ],
        "sample_rate_hz": 16_000,
        "pcm_s16le_base64": base64.b64encode(pcm).decode("ascii"),
    }


def test_capture_requires_one_real_frame_per_pcm_hop() -> None:
    rosters, samples, rate, provenance = (
        production._parse_live_audiovisual_capture(_payload())
    )

    assert len(rosters) == 4
    assert len(samples) == 16_000
    assert rate == 16_000
    assert provenance["source"] == production.LIVE_AUDIOVISUAL_SOURCE
    assert provenance["audio_sample_count"] == 16_000

    with pytest.raises(ValueError, match="exactly one camera frame"):
        production._parse_live_audiovisual_capture(
            _payload(sample_count=12_000)
        )


def test_capture_builder_places_light_and_pressure_in_the_same_hops(
    monkeypatch,
) -> None:
    times = (Fraction(0), Fraction(1, 4))
    pressure_hops = [
        (times, (float(index), float(index + 1))) for index in range(4)
    ]
    cochlear_hops = [(times, ((float(index), float(index)),)) for index in range(4)]
    calls: list[tuple] = []
    monkeypatch.setattr(production, "_pcm_hops", lambda *_args: pressure_hops)
    monkeypatch.setattr(production, "_cochlear_hops", lambda *_args: cochlear_hops)
    monkeypatch.setattr(
        production,
        "_whole_roster_hop_episode",
        lambda *args: calls.append(args) or args[0],
    )
    rosters = [tuple([float(index)] * production.CARD_SURFACE_PORT_COUNT) for index in range(4)]

    episodes = production._live_audiovisual_hop_episodes(
        "capture",
        rosters,
        tuple([0] * 16_000),
        16_000,
    )

    assert len(episodes) == len(calls) == 4
    for index, call in enumerate(calls):
        assert call[1] == times
        assert call[2] == rosters[index]
        assert call[3] == pressure_hops[index][1]
        assert call[4] == cochlear_hops[index]


def test_route_commits_both_witnesses_from_one_native_transaction(
    monkeypatch,
) -> None:
    captured: dict = {}
    monkeypatch.setattr(production, "COCHLEAR_EARS_AUTHORIZED", True)
    monkeypatch.setattr(
        production,
        "_parse_live_audiovisual_capture",
        lambda _payload: (["retina"], (1, 2), 16_000, {"source": "paired"}),
    )
    monkeypatch.setattr(
        production,
        "_live_audiovisual_hop_episodes",
        lambda *_args: ["whole-roster-hop"],
    )

    def perform(episodes, intake, provenance, *, includes_live_hearing=False):
        captured.update(
            episodes=episodes,
            intake=intake,
            provenance=provenance,
            includes_live_hearing=includes_live_hearing,
        )
        return {"accepted": True, "ok": True}

    monkeypatch.setattr(production, "_perform_live_sight_intake", perform)

    response = production.live_audiovisual_capture({})

    assert response.status_code == 200
    assert json.loads(response.body)["accepted"] is True
    assert captured["episodes"] == ["whole-roster-hop"]
    assert captured["includes_live_hearing"] is True
    assert captured["intake"].startswith("live-audiovisual:")


def test_standalone_audio_never_borrows_an_earlier_camera_receipt(
    monkeypatch,
) -> None:
    monkeypatch.setattr(production, "COCHLEAR_EARS_AUTHORIZED", True)
    monkeypatch.setattr(production, "_live_sight_evidence", {"committed": True})

    refusal = production._standalone_hearing_refusal()

    assert refusal is not None
    assert refusal.status_code == 503
    assert b"prior camera receipt does not prove present sight" in refusal.body


def test_browser_uses_one_bounded_audiovisual_request() -> None:
    page = PAGE.read_text(encoding="utf-8")

    assert 'schema:"guala.live_audiovisual_capture.v1"' in page
    assert 'source:"live-camera-microphone"' in page
    assert "hopCount*MIC_SAMPLES_PER_HOP" in page
    assert "pcmS16leBytes(pcm)" in page
    assert "micSamples-=take" in page
    assert "micChunks=[];micFrames=[];micSamples=0;const controller" not in page
    assert "/api/v1/auditory/pcm/" not in page
    assert "if(!cameraStream)return" in page
    assert "if(cameraInFlightEpoch!==null)return" in page
