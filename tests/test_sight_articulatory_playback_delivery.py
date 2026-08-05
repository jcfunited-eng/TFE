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


