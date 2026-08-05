"""Headless proof of the lean production surface: genesis, teaching, custody.

Drives ``dsf_ai_service.native_production_app`` through its own functions
only (no network, no other runtime): seeded growth-DNA genesis on an empty
state directory, one approved curriculum card taught as admitted native hop
episodes, durable publication of every committed successor, restart from
disk, and recurrence without unbounded growth.  Every asserted number is what
the native observation actually reports.
"""

from __future__ import annotations

import base64
import io
import json
import math
import struct
import wave

import pytest

from dsf_ai_service import native_production_app as production


CARD_ID = "alphabet-a"
SURFACE_PORTS = production.CARD_SURFACE_PORT_COUNT
LESSON_PORTS = production.LESSON_PORT_COUNT


@pytest.fixture()
def lean_app(monkeypatch, tmp_path):
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    yield tmp_path
    production._restored = None
    production._admission = None
    production._boot_error = None
    production._public_observation_body = None
    production._public_observation_etag = None
    production._last_transition_evidence = None
    production._pcm_sessions.clear()


def _teach(card_id: str) -> tuple[int, dict]:
    response = production.teach_card({"card_id": card_id})
    return response.status_code, json.loads(response.body)


def _tone_wav(seconds: float = 0.5, sample_rate: int = 16_000) -> bytes:
    count = int(seconds * sample_rate)
    samples = tuple(
        int(6_000 * math.sin(2.0 * math.pi * 300.0 * index / sample_rate))
        for index in range(count)
    )
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(struct.pack(f"<{count}h", *samples))
    return output.getvalue()


class _Request:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    async def body(self) -> bytes:
        return self._payload


def test_genesis_teach_persist_restart_and_recurrence(lean_app) -> None:
    # Genesis with authored growth DNA on an empty directory.
    production._startup()
    assert (lean_app / "CURRENT").is_file()
    newborn = production._restored.organism.readiness()
    assert newborn.organism_tick == 0
    assert newborn.complete_neuron_count == 0
    assert newborn.joint_neuron_count == 0
    genesis_sha = production._restored.pointer.state_sha256

    # A card outside the signed manifest is refused without a transition.
    refused_status, refused = _teach("not-an-approved-card")
    assert refused_status == 404
    assert refused["accepted"] is False
    assert production._restored.pointer.state_sha256 == genesis_sha

    # First lesson: the 27 retinal card-surface sites transition and become
    # the grown cohort; both ear sites join it in the following hops.
    first_status, first = _teach(CARD_ID)
    assert first_status == 200
    assert first["accepted"] is True and first["ok"] is True
    assert first["hop_count"] >= 3
    assert (
        first["totals"]["physically_transitioned_neuron_count"]
        == SURFACE_PORTS
    )
    assert first["observation"]["complete_neuron_count"] == LESSON_PORTS
    assert first["observation"]["cognitive_mosaic_count"] == 0
    assert first["persisted"]["state_sha256"] != genesis_sha
    assert (
        production._restored.pointer.state_sha256
        == first["persisted"]["state_sha256"]
    )

    # Restart from disk: the taught body restores exactly.
    production._startup()
    restored = production._restored.organism.readiness()
    assert restored.complete_neuron_count == LESSON_PORTS
    assert (
        production._restored.pointer.state_sha256
        == first["persisted"]["state_sha256"]
    )

    # Second pass of the same lesson: the exact recurrence of the settled
    # experience emits genuine nonzero post-quiescence neuron fractals and
    # grows no new neurons.
    second_status, second = _teach(CARD_ID)
    assert second_status == 200
    assert second["totals"]["physically_transitioned_neuron_count"] == 0
    assert (
        second["totals"]["complete_neuron_fractal_count"] == SURFACE_PORTS
    )
    assert second["observation"]["complete_neuron_count"] == LESSON_PORTS

    # Third pass: recurrence, not growth; the persisted body is byte-bounded.
    third_status, third = _teach(CARD_ID)
    assert third_status == 200
    assert third["totals"]["physically_transitioned_neuron_count"] == 0
    assert (
        third["persisted"]["state_bytes"] == second["persisted"]["state_bytes"]
    )
    assert third["observation"]["complete_neuron_count"] == LESSON_PORTS

    # The public observation cache reflects the committed generations.
    body = json.loads(production._public_observation_body)
    assert body["generation"] == third["observation"]["organism_tick"]
    assert (
        body["generation_state"]["state_sha256"]
        == third["persisted"]["state_sha256"]
    )
    assert body["neuron_activity"]["retained_count"] == LESSON_PORTS
    assert body["curriculum"]["tutoring_transition_available"] is True


@pytest.mark.asyncio
async def test_sound_frame_and_pcm_session_transition_and_persist(
    lean_app,
) -> None:
    production._startup()
    before_tick = production._restored.organism.readiness().organism_tick

    # A malformed body is refused before the organism is reached.
    refused = await production.sound_frame(_Request(b"not-a-wav"))
    assert refused.status_code == 422
    assert (
        production._restored.organism.readiness().organism_tick == before_tick
    )

    accepted = await production.sound_frame(_Request(_tone_wav()))
    assert accepted.status_code == 200
    result = json.loads(accepted.body)
    assert result["accepted"] is True
    assert result["hop_count"] == 2
    assert (
        result["totals"]["dsf_delivery_count"]
        == production.EAR_PORT_COUNT * result["hop_count"]
    )
    after_tick = production._restored.organism.readiness().organism_tick
    assert after_tick == before_tick + result["hop_count"]
    assert (
        production._restored.pointer.state_sha256
        == result["persisted"]["state_sha256"]
    )

    # The mono PCM session delivers the same admitted intake.
    opened = json.loads(production.pcm_open({"sample_rate_hz": 16_000}).body)
    assert opened["accepted"] is True
    session_id = opened["session_id"]
    chunk = struct.pack(
        "<8000h",
        *(
            int(4_000 * math.sin(2.0 * math.pi * 220.0 * index / 16_000))
            for index in range(8_000)
        ),
    )
    chunked = json.loads(
        production.pcm_chunk({
            "session_id": session_id,
            "pcm_s16le_base64": base64.b64encode(chunk).decode("ascii"),
        }).body
    )
    assert chunked["accepted"] is True
    assert chunked["retained_sample_count"] == 8_000
    closed_response = production.pcm_close({"session_id": session_id})
    assert closed_response.status_code == 200
    closed = json.loads(closed_response.body)
    assert closed["accepted"] is True
    assert closed["hop_count"] == 2
    assert (
        production._restored.organism.readiness().organism_tick
        == after_tick + closed["hop_count"]
    )

    # A closed session cannot be replayed.
    replay = production.pcm_close({"session_id": session_id})
    assert replay.status_code == 404
