#!/usr/bin/env python3
"""Automated Associative Grounding Benchmark (Option 1).

Measures quantitative stability, noise tolerance, and physical invariance of Guala's
multi-modal sensorimotor grounding:
1. Clean Grounding & Causal Credit: Caloric drive relief, oral reflex, moment binding,
   and somatic credit assignment (fed).
2. Acoustic Noise & Spectral Resilience: 16-channel cochlear ERB filter resilience
   and acoustic gate event closure across domestic noise perturbations.
3. Visual Invariant Stability: Level-free chromatic annular disc invariance across
   diurnal solar illumination variations (morning, noon, afternoon, dusk).
4. Temporal Binding Coincidence Window: Within-window causal linkage vs. post-window
   decay across the 16-beat temporal boundary law.

Emits structured JSON benchmark metrics and enforces the canonical 85% physics floor.
"""

from __future__ import annotations

import json
import math
import os
import random
import struct
import sys
import time
from typing import Any

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop, _hearing
from dsf_ai_service.guala_functional_organism import (
    FOLLOW_WINDOW_BEATS,
    FunctionalOrganism,
    syllable_pcm,
    SYLLABLE_DRIVES,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def _microphone_sound(pcm: bytes) -> PhysicalOccurrence:
    return PhysicalOccurrence(
        "sensory",
        LeanSensoryOccurrence(
            source="microphone",
            retina_rgb_u8=None,
            pressure_s16le=pcm,
        ),
    )


def _present_food(food: str) -> PhysicalOccurrence:
    return PhysicalOccurrence(
        "sensory",
        LeanSensoryOccurrence(
            source="caretaker-food",
            retina_rgb_u8=None,
            pressure_s16le=None,
            present_food=food,
        ),
    )


def _add_pcm_noise(pcm: bytes, noise_fraction: float) -> bytes:
    samples = struct.unpack(f"<{len(pcm)//2}h", pcm)
    noisy = []
    for s in samples:
        n = int((random.random() * 2.0 - 1.0) * 32767 * noise_fraction)
        val = max(-32768, min(32767, s + n))
        noisy.append(val)
    return struct.pack(f"<{len(noisy)}h", *noisy)


def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na * nb > 0.0 else 0.0


def run_benchmark() -> dict[str, Any]:
    loop = FunctionalPhysicalLoop()
    results: dict[str, Any] = {
        "benchmark": "Option 1 - Automated Associative Grounding Benchmark",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "physics_floor": 0.85,
        "tests": {},
        "scores": {},
    }

    # -------------------------------------------------------------------------
    # Test 1: Clean Baseline Grounding & Causal Credit (Caloric Drive Relief)
    # -------------------------------------------------------------------------
    world1 = home_world_authority(identity=IDENTITY)
    org1 = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    before_reserve = org1.reserve_micrograms

    clean_pcm_dah = syllable_pcm(SYLLABLE_DRIVES["dah0"], seed=42)

    # Hop 1: Caregiver speaks "dah0"
    loop.settle(org1, world1, _microphone_sound(clean_pcm_dah))
    # Hop 2: Caregiver offers apple
    loop.settle(org1, world1, _present_food("apple"))
    # Hops 3..7: Allow oral reflex bites, digestion, and event closure
    for _ in range(5):
        loop.settle(org1, world1, UNATTENDED)

    after_reserve = org1.reserve_micrograms
    intake = after_reserve - before_reserve
    bites = int(org1._state.get("bites", 0))
    moments = org1._state.get("moments", {})
    fed_credits = sum(m.get("fed", 0) for m in moments.values())

    test1_pass = intake > 0 and bites >= 1 and len(moments) >= 1 and fed_credits >= 1
    test1_score = 1.0 if test1_pass else 0.0
    results["tests"]["test1_clean_grounding"] = {
        "intake_micrograms": intake,
        "bites": bites,
        "moments_formed": len(moments),
        "fed_causal_credits": fed_credits,
        "passed": test1_pass,
    }
    results["scores"]["clean_grounding_score"] = test1_score

    # -------------------------------------------------------------------------
    # Test 2: Acoustic Noise Resilience (16 ERB Channels & Gate Closure)
    # -------------------------------------------------------------------------
    clean_prof, _, _ = _hearing(clean_pcm_dah)
    noise_levels = [0.02, 0.05, 0.10, 0.15]  # Whisper to active domestic ambient
    noise_details = []
    level_scores = []

    for nl in noise_levels:
        noisy_pcm = _add_pcm_noise(clean_pcm_dah, nl)
        noisy_prof, _, _ = _hearing(noisy_pcm)
        sim = _cosine_similarity(clean_prof, noisy_prof)

        org2 = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=100)
        w2 = home_world_authority(identity=IDENTITY)
        loop.settle(org2, w2, _microphone_sound(noisy_pcm))
        loop.settle(org2, w2, UNATTENDED)

        gate_closed = bool(org2._state.get("sound_event"))
        score = sim if gate_closed else 0.0
        level_scores.append(score)
        noise_details.append({
            "noise_amplitude_fraction": nl,
            "gate_event_closed": gate_closed,
            "cochlear_cosine_similarity": round(sim, 4),
            "effective_score": round(score, 4),
        })

    mean_acoustic_score = sum(level_scores) / len(level_scores)
    test2_pass = mean_acoustic_score >= 0.85
    results["tests"]["test2_acoustic_noise"] = {
        "target_syllable": "dah0",
        "levels_tested": len(noise_levels),
        "mean_spectral_fidelity": round(mean_acoustic_score, 4),
        "details": noise_details,
        "passed": test2_pass,
    }
    results["scores"]["acoustic_resilience_score"] = round(mean_acoustic_score, 4)

    # -------------------------------------------------------------------------
    # Test 3: Visual Invariant Stability Across Diurnal Solar Illumination
    # -------------------------------------------------------------------------
    solar_hours = [9, 12, 15, 17]  # Morning, Noon, Afternoon, Dusk
    base_time = int(time.time()) - (int(time.time()) % 86_400)
    figure_keys = []

    for hour in solar_hours:
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = str(base_time + hour * 3600)
        w3 = home_world_authority(identity=IDENTITY)
        org3 = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=200)
        org3._state["gaze_target"] = "sofa"  # Large prominent object (radius > 10 sites)
        loop.settle(org3, w3, UNATTENDED)
        figure_keys.append(org3._state.get("sight_figure"))

    # True level-free invariance means the figure hash is identical across all illuminations
    unique_figures = set(figure_keys)
    test3_pass = len(unique_figures) == 1 and None not in unique_figures
    test3_score = 1.0 if test3_pass else 0.0
    results["tests"]["test3_visual_lighting"] = {
        "solar_hours_tested": solar_hours,
        "figure_keys_observed": figure_keys,
        "unique_keys_count": len(unique_figures),
        "passed": test3_pass,
    }
    results["scores"]["visual_invariant_score"] = test3_score

    # -------------------------------------------------------------------------
    # Test 4: Temporal Binding Coincidence Window & Causal Decay
    # -------------------------------------------------------------------------
    org4 = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=300)
    w4 = home_world_authority(identity=IDENTITY)

    # Event A: Caregiver speaks "dah0"
    loop.settle(org4, w4, _microphone_sound(clean_pcm_dah))
    loop.settle(org4, w4, UNATTENDED)
    m_heard_key = org4._state.get("last_moment")[0]

    # Guala responds with vocalization within 6 beats
    for _ in range(6):
        loop.settle(org4, w4, UNATTENDED)

    within_window_bound = len(org4._state["moments"][m_heard_key].get("next", {})) > 0
    m_voice_key = org4._state.get("last_moment")[0]

    # Advance 20 beats (exceeds FOLLOW_WINDOW_BEATS = 16)
    for _ in range(20):
        loop.settle(org4, w4, UNATTENDED)

    # Event B: Caregiver speaks "dee0" after the window has decayed
    clean_pcm_dee = syllable_pcm(SYLLABLE_DRIVES["dee0"], seed=43)
    loop.settle(org4, w4, _microphone_sound(clean_pcm_dee))
    loop.settle(org4, w4, UNATTENDED)

    m_decayed_key = org4._state.get("last_moment")[0]
    # Check that m_voice_key did NOT link to m_decayed_key across the gap
    outside_window_decayed = m_decayed_key not in org4._state["moments"][m_voice_key].get("next", {})

    test4_pass = within_window_bound and outside_window_decayed
    test4_score = 1.0 if test4_pass else 0.0
    results["tests"]["test4_temporal_binding"] = {
        "follow_window_beats": FOLLOW_WINDOW_BEATS,
        "within_window_bound": within_window_bound,
        "outside_window_decayed": outside_window_decayed,
        "passed": test4_pass,
    }
    results["scores"]["temporal_binding_score"] = test4_score

    # -------------------------------------------------------------------------
    # Composite Overall Robustness Score (Canonical 85% Physics Floor)
    # -------------------------------------------------------------------------
    weights = {
        "clean_grounding_score": 0.30,
        "acoustic_resilience_score": 0.25,
        "visual_invariant_score": 0.25,
        "temporal_binding_score": 0.20,
    }
    overall = sum(results["scores"][k] * weights[k] for k in weights)
    results["overall_robustness_score"] = round(overall, 4)
    results["verdict"] = "PASS" if overall >= 0.85 else "FAIL"

    return results


def main() -> None:
    report = run_benchmark()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
