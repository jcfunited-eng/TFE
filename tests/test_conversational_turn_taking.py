"""tests/test_conversational_turn_taking.py — Stage 4 Turn-Taking Flow Verification.

Empirically validates:
1. Acoustic Pressure Clamping (No Talking Over Speaker):
   - When external acoustic energy is present (sound_heard == True), vocal motor actuation
     is clamped and 'say' is withheld from motor execution.
   - Non-say motor actions (step, turn) do not inject vocal drive during speech.
2. Calibrated 250 ms Quiet-Gap Conversational Response:
   - On the very first beat following acoustic pressure cessation (quiet_gap == 1 beat == 250 ms),
     the vocal motor pathway is released.
   - Guala unassistedly releases 'say' as her conversational turn response.
   - The reason strictly records 'conversational turn release after 250ms quiet gap'.
3. Conversational Floor Hand-Off:
   - Delivering the response consumes the acoustic speech target.
   - On subsequent silence beats (quiet_gap > 1), Guala yields the conversational floor
     and does not loop or repeat unprompted.
"""
from __future__ import annotations

import os
import time
import pytest

# Daylight override so world illumination is invariant
os.environ.setdefault("GUALA_SOLAR_UTC_OVERRIDE", str(int(time.time()) - int(time.time()) % 86_400 + 13 * 3_600))

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    SYLLABLE_DRIVES,
    syllable_pcm,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def test_conversational_turn_taking_quiet_gap_flow() -> None:
    """Verifies that Guala listens during active caregiver speech, responds at 250ms quiet gap,
    and cleanly yields the floor on subsequent beats."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Initial settling beats
    for _ in range(5):
        loop.settle(organism, world, UNATTENDED)

    # 1. Caregiver speaks 'mah0' via microphone
    pcm_mah = syllable_pcm(SYLLABLE_DRIVES["mah0"], seed=42)
    sensory_speech = LeanSensoryOccurrence(source="microphone", retina_rgb_u8=None, pressure_s16le=pcm_mah)

    # Beat of active acoustic pressure: Guala hears sound
    res_speech = loop.settle(organism, world, PhysicalOccurrence("sensory", sensory_speech))

    # Invariant 1: No talking over the speaker
    assert res_speech.observation["her_act"] != "say", (
        f"Guala erroneously talked over the speaker: {res_speech.observation['her_act']}"
    )
    assert res_speech.observation["said"] is None, (
        f"Vocal drive was erroneously emitted during active speaker speech: {res_speech.observation['said']}"
    )

    # 2. Next Beat: Speaker has finished; 250 ms quiet gap arrives (1 beat of silence)
    res_turn = loop.settle(organism, world, UNATTENDED)

    # Invariant 2: Vocal motor release at 250 ms quiet gap
    assert res_turn.observation["her_act"] == "say", (
        f"Guala failed to take her conversational turn at 250ms quiet gap: act={res_turn.observation['her_act']}"
    )
    assert res_turn.observation["said"] is not None, "Guala took turn but said nothing"
    assert "conversational turn release after 250ms quiet gap" in str(res_turn.observation.get("act_reason", "")), (
        f"Reason did not record turn-taking release: {res_turn.observation.get('act_reason')}"
    )

    # Invariant 3: Acoustic target was consumed by the response
    target = organism._state.get("heard_speech_target")
    assert target is not None and target.get("consumed") is True, "Target was not consumed by turn response"

    # 3. Subsequent Beat: Quiet continues (quiet gap = 500 ms)
    res_yield = loop.settle(organism, world, UNATTENDED)

    # Invariant 4: Guala yields the floor and does not repeatedly speak
    assert "conversational turn release after 250ms quiet gap" not in str(res_yield.observation.get("act_reason", "")), (
        "Guala failed to yield the conversational floor on subsequent beat"
    )


def test_acoustic_pressure_clamp_during_multi_beat_speech() -> None:
    """Verifies that while acoustic pressure is sustained over multiple beats,
    vocal motor actuation remains strictly clamped throughout."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    pcm_phrase = syllable_pcm(SYLLABLE_DRIVES["bah0"], seed=7)
    sensory_phrase = LeanSensoryOccurrence(source="microphone", retina_rgb_u8=None, pressure_s16le=pcm_phrase)

    # Three consecutive beats of incoming speech
    for beat_idx in range(3):
        res = loop.settle(organism, world, PhysicalOccurrence("sensory", sensory_phrase))
        assert res.observation["her_act"] != "say", f"Vocal release during speech beat {beat_idx}"
        assert res.observation["said"] is None, f"Vocal emission during speech beat {beat_idx}"

    # First beat of silence (250 ms quiet gap)
    res_response = loop.settle(organism, world, UNATTENDED)
    assert res_response.observation["her_act"] == "say", "Did not respond at 250ms quiet gap after multi-beat speech"
    assert "conversational turn release after 250ms quiet gap" in str(res_response.observation.get("act_reason", ""))
