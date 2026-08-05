from __future__ import annotations

import asyncio
import base64
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dsf_ai_service.app as app_module
from dsf_ai_service.substrate.consequence_evoked_articulatory_response import (
    CommittedConsequenceEvokedArticulatoryAct,
)

class _Verifier:
    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error
        self.values = []

    def verify_committed_act(self, value) -> None:
        self.values.append(value)
        if self.error is not None:
            raise self.error


def _act(pcm: bytes, *, claimed_digest: str | None = None):
    response = SimpleNamespace(
        state="executed",
        synthesis_pcm_sha256=(
            claimed_digest or hashlib.sha256(pcm).hexdigest()
        ),
        authority_receipt_sha256="a" * 64,
    )
    return CommittedConsequenceEvokedArticulatoryAct(
        response=response,
        pcm_s16le=pcm,
    )


def test_server_consumes_only_verified_same_request_typed_act() -> None:
    pcm = b"\x01\x00\xfe\xff" * 80
    act = _act(pcm)
    verifier = _Verifier()
    receipt = {
        "accepted": True,
        "articulatory_act": act,
        "visual_region": {"regions": []},
    }

    projection = (
        app_module._consume_same_request_sight_articulatory_playback(
            receipt,
            response_authority=verifier,
        )
    )

    assert verifier.values == [act]
    assert "articulatory_act" not in receipt
    assert projection == {
        "channel_count": 1,
        "encoding": "pcm_s16le",
        "pcm_s16le_b64": base64.b64encode(pcm).decode("ascii"),
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "sample_count": len(pcm) // 2,
        "sample_rate_hz": 16_000,
        "schema": (
            "guala.loom.same_request_sight_articulatory_playback.v1"
        ),
        "source_response_authority_receipt_sha256": "a" * 64,
    }


def test_server_never_reads_observation_history_or_unverified_pressure() -> None:
    stale = _act(b"\x01\x00" * 80)
    verifier = _Verifier(
        AssertionError("a nullable result must not consult an authority")
    )
    receipt = {
        "accepted": True,
        "latest_observation": stale,
        "historical_articulatory_act": stale,
    }
    assert (
        app_module._consume_same_request_sight_articulatory_playback(
            receipt,
            response_authority=verifier,
        )
        is None
    )
    assert verifier.values == []

    rejected = _Verifier(ValueError("unverified committed act"))
    unverified_receipt = {
        "articulatory_act": _act(b"\x02\x00" * 80),
    }
    try:
        app_module._consume_same_request_sight_articulatory_playback(
            unverified_receipt,
            response_authority=rejected,
        )
    except ValueError as error:
        assert str(error) == "unverified committed act"
    else:
        raise AssertionError("unverified physical pressure was serialized")
    assert "articulatory_act" not in unverified_receipt

    changed_pcm = b"\x03\x00" * 80
    changed_receipt = {
        "articulatory_act": _act(
            changed_pcm,
            claimed_digest=hashlib.sha256(b"different").hexdigest(),
        ),
    }
    try:
        app_module._consume_same_request_sight_articulatory_playback(
            changed_receipt,
            response_authority=_Verifier(),
        )
    except ValueError as error:
        assert "changed physical pressure" in str(error)
    else:
        raise AssertionError("digest-mismatched physical pressure was serialized")


def test_current_camera_result_is_explicitly_null(monkeypatch) -> None:
    class _CameraOnlyGuala:
        tick = 7
        _consequence_evoked_articulatory_response = None

        def process_live_visual_region_sequence(self, *_args, **_kwargs):
            return {
                "accepted": True,
                "visual_region": {"regions": []},
            }

    async def run_inline(function):
        return function()

    monkeypatch.setattr(app_module, "_guala", _CameraOnlyGuala())
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    monkeypatch.setattr(
        app_module,
        "_visual_claim_transport",
        lambda _claims: (True, (object(),), None),
    )
    monkeypatch.setattr(
        app_module,
        "_decode_visual_sequence",
        lambda *_args, **_kwargs: (object(),),
    )
    monkeypatch.setattr(
        app_module,
        "_run_lifecycle_executor",
        run_inline,
    )
    monkeypatch.setattr(
        app_module,
        "_frame_backpressure_acquire",
        lambda _kind: True,
    )
    monkeypatch.setattr(
        app_module,
        "_frame_backpressure_release",
        lambda _kind: None,
    )

    result = asyncio.run(
        app_module.sight_frame(
            app_module.GLMessage(
                text="",
                capture_started_ms=1_000,
                capture_ended_ms=2_000,
                sight_frames=[{"opaque": True}],
            )
        )
    )

    assert result["ok"] is True
    assert result["articulatory_playback"] is None


def test_browser_uses_one_digest_verified_slot_and_releases_pcm() -> None:
    page = (
        ROOT / "dsf_ai_service/static/gualaloom.html"
    ).read_text(encoding="utf-8")
    start = page.index(
        "async function _playSameRequestSightArticulation"
    )
    end = page.index(
        "function _notifyPCMEpochClose",
        start,
    )
    delivery = page[start:end]

    assert "await _sha256Hex(pcm)!==projection.pcm_sha256" in delivery
    assert "projection.sample_count*2>SIGHT_ARTICULATORY_MAX_PCM_BYTES" in delivery
    assert "let sightArticulatoryPlayback=null;" in page
    assert "sightArticulatoryPlayback.push" not in page
    assert "_releaseSightArticulatoryPlayback();" in delivery
    assert "URL.revokeObjectURL(active.url)" in page
    assert "result.articulatory_playback=null;" in page
    assert "if(muted)_releaseSightArticulatoryPlayback();" in page
    assert "window._lastObservation" not in delivery
    assert "/api/v1/gualaloom/observation" not in delivery
    assert "speechSynthesis" not in delivery
    assert "new Audio(" not in delivery
