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


def _teach(card_id: str) -> tuple[int, dict]:
    invitation = {
        "schema": production.CURRICULUM_INVITATION_SCHEMA,
        "card_id": card_id,
        "outcome": "presentable",
        "presentation_eligible": True,
        "participant_action_causal_intent_receipt_sha256": "11" * 32,
        "reason": "test fixture physical invitation reached retina",
        "status": "participant_invitation_reached_retina",
    }
    invitation["invitation_receipt_sha256"] = production._receipt(invitation)
    production._curriculum_invitation = invitation
    response = production.teach_card(
        {
            "card_id": card_id,
            "invitation_receipt_sha256": invitation[
                "invitation_receipt_sha256"
            ],
        }
    )
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

    # First lesson: one joint whole-sensorium occurrence per hop reaches the
    # current retina, cochleae, body, and metabolic receptor roster. Exact
    # per-neuron counts are intentionally not pinned here: they changed when
    # the complete mounted anatomy replaced the historical 29-port lean body.
    # This test owns the behavioral contract: physical transitions, fractal
    # change, bounded recovery, persistence, and no exhaustion.
    first_status, first = _teach(CARD_ID)
    assert first_status == 200
    assert first["accepted"] is True and first["ok"] is True
    assert first["hop_count"] >= 3
    assert first["totals"]["physically_transitioned_neuron_count"] > 0
    assert first["totals"]["complete_neuron_fractal_count"] > 0
    assert first["totals"]["partial_cue_reassembly_count"] > 0
    assert first["totals"]["rest_recovered_neuron_count"] > 0
    assert first["totals"]["energy_exhausted_interval_count"] == 0
    retained_neurons = first["observation"]["complete_neuron_count"]
    assert retained_neurons >= SURFACE_PORTS
    assert first["persisted"]["state_sha256"] != genesis_sha
    assert (
        production._restored.pointer.state_sha256
        == first["persisted"]["state_sha256"]
    )

    # Restart from disk: the taught body restores exactly.
    production._startup()
    restored = production._restored.organism.readiness()
    assert restored.complete_neuron_count == retained_neurons
    assert (
        production._restored.pointer.state_sha256
        == first["persisted"]["state_sha256"]
    )

    # Repeated physical presentations retain the learned body, continue
    # partial-cue activity and recovery, and do not append neurons or exhaust
    # the organism. This does not relabel the activity as recognition.
    second_status, second = _teach(CARD_ID)
    assert second_status == 200
    assert second["totals"]["physically_transitioned_neuron_count"] > 0
    assert second["totals"]["partial_cue_reassembly_count"] > 0
    assert second["totals"]["rest_recovered_neuron_count"] > 0
    assert second["totals"]["energy_exhausted_interval_count"] == 0
    assert second["observation"]["complete_neuron_count"] == retained_neurons

    # Two further passes prove bounded, non-append-only state behavior.
    third_status, third = _teach(CARD_ID)
    assert third_status == 200
    assert third["observation"]["complete_neuron_count"] == retained_neurons
    fourth_status, fourth = _teach(CARD_ID)
    assert fourth_status == 200
    assert fourth["observation"]["complete_neuron_count"] == retained_neurons
    assert fourth["totals"]["energy_exhausted_interval_count"] == 0
    assert fourth["persisted"]["state_bytes"] <= max(
        first["persisted"]["state_bytes"],
        second["persisted"]["state_bytes"],
        third["persisted"]["state_bytes"],
    )

    # The public observation cache reflects the committed generations.
    body = json.loads(production._public_observation_body)
    assert body["generation"] == fourth["observation"]["organism_tick"]
    assert (
        body["generation_state"]["state_sha256"]
        == fourth["persisted"]["state_sha256"]
    )
    assert body["neuron_activity"]["retained_count"] == retained_neurons
    assert body["curriculum"]["tutoring_transition_available"] is True


@pytest.mark.asyncio
async def test_standalone_sound_intake_is_suspended_by_doctrine(
    lean_app,
) -> None:
    """Standalone sound refuses without cochlear anatomy and cannot mutate."""

    production._startup()
    before = production._restored.organism.readiness()
    sound = await production.sound_frame(_Request(_tone_wav()))
    assert sound.status_code == 503
    assert b"cochlear ear anatomy is not authorized" in sound.body
    assert production.pcm_open({"sample_rate_hz": 16_000}).status_code == 503
    assert production.pcm_close({"session_id": "any"}).status_code == 503
    after = production._restored.organism.readiness()
    assert after.organism_tick == before.organism_tick
    assert after.state_sha256 == before.state_sha256
    # There is no dormant audio-only implementation to reactivate from an
    # earlier camera receipt; live microphone pressure is accepted only by
    # the co-captured audiovisual route.
    assert production.LIVE_AUDIOVISUAL_INTAKE_ENDPOINT in {
        route.path for route in production.app.routes
    }


@pytest.mark.asyncio
async def test_sound_intake_carries_the_whole_sensorium(lean_app) -> None:
    """Ratified doctrine (2026-08-05): NO single-sense experiences.

    Every sound-intake hop episode must declare the full mounted sensorium
    with TRUE samples: cochlear pressure, the 27 retinal sites carrying true
    dark 0.0 luminance, and lawful body state on one shared clock, as one
    joint occurrence. The declared receptor groups preserve anatomy without
    repeating unchanged L0-L4 once per sense.
    """

    # The built episodes declare the current full mounted sensorium, never an
    # ear-only projection, and exactly one joint occurrence per hop.
    episodes = production._mono_pcm_hop_episodes(
        assembly_prefix="two-sense-proof",
        samples=tuple(
            int(5_000 * math.sin(2.0 * math.pi * 260.0 * index / 16_000))
            for index in range(8_000)
        ),
        sample_rate_hz=16_000,
    )
    assert len(episodes) == 2
    for episode, intervals in episodes:
        assert episode.port_count == LESSON_PORTS
        assert episode.occurrence_count == production.LESSON_OCCURRENCE_COUNT
        # One caller-authored maximum causal interval per occurrence.
        assert intervals == [(production.AMBIENT_INTAKE_MAX_SECONDS, 1)]
        # Every declared port carries one true sample per retained frame:
        # total samples are the whole sensorium, not an ear-only stream.
        frame_count = episode.occurrence_frame_count
        assert episode.source_sample_count == LESSON_PORTS * frame_count

    # The live route refuses by doctrine (standalone hearing suspended)
    # and the organism stays untouched; the whole-sensorium construction
    # above is what reactivation will serve when the camera mounts.
    production._startup()
    before = production._restored.organism.readiness()
    refused = await production.sound_frame(_Request(_tone_wav()))
    assert refused.status_code == 503
    after = production._restored.organism.readiness()
    assert after.organism_tick == before.organism_tick
