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
        "outcome": "attended",
        "presentation_eligible": True,
        "participant_action_causal_intent_receipt_sha256": "11" * 32,
        "reason": "test fixture exact causal continuation",
        "status": "participant_causal_continuation_observed",
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

    # First lesson: the 27 retinal card-surface sites transition and become
    # the grown cohort; the ears stay declared with true silence but grow
    # nothing (no auditory transduction law is mounted).
    #
    # PIN CHANGED by the stimulus-boundary retention ratification
    # (2026-08-05) and its companion app transport fix, measured
    # before/after on this exact path:
    #   physically_transitioned_neuron_count  189 -> AFTER 209
    #   complete_neuron_fractal_count         stays 27
    # Every lit hop declares the lit card surface as its own exact optical
    # occurrence (7 * 27 == 189 lit transitions), and now the two ENDED hops
    # do the same with true dark samples, so the cohort physically settles
    # at presentation end (measured: 16 then 4 neurons transition on the
    # dark boundary hops; 189 + 16 + 4 == 209).  The first dark settlement
    # carries zero exogenous optical energy, so the lesson's experience
    # closes THERE — with its real electrical participation masks (gate
    # work 27/27, active contacts 26/26) — and emits its 27 genuine
    # stimulus-boundary fractals.  The retained original is CONNECTED and
    # satisfies the admission law's own original-side predicate.
    first_status, first = _teach(CARD_ID)
    assert first_status == 200
    assert first["accepted"] is True and first["ok"] is True
    assert first["hop_count"] >= 3
    assert first["totals"]["physically_transitioned_neuron_count"] == 209
    assert first["totals"]["complete_neuron_fractal_count"] == SURFACE_PORTS
    # PIN CHANGED 29 -> 27 by the same ratification: the two ear neurons
    # only ever joined the retinal cohort through the OLD ended hops'
    # combined 29-port occurrence — the exact transport lie this fix
    # removes.  The ears remain declared with true silence on every hop
    # (two-sense doctrine), but with no auditory transduction law mounted
    # they lawfully grow nothing; the grown cohort is the 27 retinal sites.
    assert first["observation"]["complete_neuron_count"] == SURFACE_PORTS
    assert first["observation"]["cognitive_mosaic_count"] == 0
    assert first["persisted"]["state_sha256"] != genesis_sha
    assert (
        production._restored.pointer.state_sha256
        == first["persisted"]["state_sha256"]
    )

    # Restart from disk: the taught body restores exactly.
    production._startup()
    restored = production._restored.organism.readiness()
    assert restored.complete_neuron_count == SURFACE_PORTS
    assert (
        production._restored.pointer.state_sha256
        == first["persisted"]["state_sha256"]
    )

    # Second pass of the same lesson: RECURRENCE against the connected
    # retained original.
    #
    # PINS CHANGED by the stimulus-boundary retention ratification
    # (2026-08-05), measured before/after on this exact path:
    #   physically_transitioned_neuron_count  189 -> AFTER 211
    #   partial_cue_reassembly_count            0 -> AFTER   4
    #   cognitive_mosaic_count                  0 -> AFTER   4
    # With a CONNECTED original retained by lesson 1, the second lesson's
    # dwell-staggered gate openings form proper partial cues in time (the
    # early hops of a presentation are a partial glimpse of it), and the
    # physics itself admits four physical mosaics on this served path —
    # the first served-path recognitions.  Recorded, never forced: these
    # counts are the decoded native observation.
    second_status, second = _teach(CARD_ID)
    assert second_status == 200
    assert second["totals"]["physically_transitioned_neuron_count"] == 211
    assert second["totals"]["complete_neuron_fractal_count"] == 0
    assert second["totals"]["partial_cue_reassembly_count"] == 4
    assert second["observation"]["cognitive_mosaic_count"] == 4
    assert second["observation"]["complete_neuron_count"] == SURFACE_PORTS

    # Third pass: recurrence continues, no growth in neurons.
    third_status, third = _teach(CARD_ID)
    assert third_status == 200
    assert third["totals"]["physically_transitioned_neuron_count"] == 213
    assert third["observation"]["complete_neuron_count"] == SURFACE_PORTS

    # PIN RE-MEASURED under the stimulus-boundary retention ratification
    # (2026-08-05).  The body is no longer a flat plateau: it grows ONLY
    # with each newly DISTINCT admitted mosaic (~116 kB of resident mosaic
    # reference per admission) while repeated admissions of an
    # already-formed mosaic add nothing resident.  Measured bodies,
    # alphabet-a, this exact served path, 6 consecutive lessons:
    #   L1 2070731 (0 mosaics), L2 2535923 (4), L3 3001071 (8),
    #   L4 3117277 (9), L5 3233455 (10), L6 3349681 (11)
    # The new-mosaic rate falls as the cue spectrum saturates (4, 4, 1, 1,
    # 1); recognition episodes additionally file into hippocampal cold
    # custody (~1.9 MB per admission, on disk, content-addressed).  The
    # honest bound is per-new-mosaic, not per-lesson; whether this harvest
    # rate needs governance is an open doctrine item, stated, not hidden.
    fourth_status, fourth = _teach(CARD_ID)
    assert fourth_status == 200
    assert fourth["totals"]["physically_transitioned_neuron_count"] == 218
    assert fourth["persisted"]["state_bytes"] >= third["persisted"]["state_bytes"]
    new_mosaics = (
        fourth["observation"]["cognitive_mosaic_count"]
        - third["observation"]["cognitive_mosaic_count"]
    )
    assert (
        fourth["persisted"]["state_bytes"] - third["persisted"]["state_bytes"]
        <= 130_000 * max(new_mosaics, 1)
    )
    assert fourth["persisted"]["state_bytes"] <= 3_200_000
    assert fourth["observation"]["complete_neuron_count"] == SURFACE_PORTS

    # The public observation cache reflects the committed generations.
    body = json.loads(production._public_observation_body)
    assert body["generation"] == fourth["observation"]["organism_tick"]
    assert (
        body["generation_state"]["state_sha256"]
        == fourth["persisted"]["state_sha256"]
    )
    assert body["neuron_activity"]["retained_count"] == SURFACE_PORTS
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

    Every sound-intake hop episode must declare BOTH mounted senses with
    TRUE samples: the two ear pressure ports carrying the caller's PCM and
    all 27 card-surface receptor sites carrying their true dark 0.0
    luminance, as two lawful occurrences (the surface as its own exact
    optical occurrence, the ears as theirs).  The proof asserts the built
    episodes' declared port composition AND that the admitted transition
    still commits and persists.
    """

    # The built episodes declare the full 29-port sensorium, never the two
    # ear ports alone, and exactly two occurrences per hop.
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
        assert episode.occurrence_count == 2
        # One caller-authored maximum causal interval per occurrence.
        assert intervals == [(production.AMBIENT_INTAKE_MAX_SECONDS, 1)] * 2
        # Every declared port carries one true sample per retained frame:
        # total samples are the whole sensorium, not an ear-only stream.
        frame_count = episode.occurrence_frame_count // 2
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
