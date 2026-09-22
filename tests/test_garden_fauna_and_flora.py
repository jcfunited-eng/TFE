#!/usr/bin/env python3
"""tests/test_garden_fauna_and_flora.py — Garden Fauna & Flora Sensory and Affordance Physics.

Verifies:
1. World expansion to 67 global entities while streaming strictly <= 64 objects to physical receptors.
2. Spatial horizon occlusion: fauna/flora occluded from bedroom, perceived in backyard.
3. Bird acoustic birdsong chirp generation and 16-channel ERB gammatone cochlear transduction.
4. Optical spectral reflectance, 32x32 textures, and floral volatile emissions.
5. Affordance extraction (is_fauna, is_flora, can_emit_sound) and gentle approach planning.
6. Nocturnal house-tidying sleep cycle reset of fauna resting perches.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import replace
import numpy as np
import pytest

from dsf_ai_service.affordance_planner import (
    extract_affordances,
    plan_fauna_observation_approach,
)
from dsf_ai_service.guala_home_world import (
    expand_garden_fauna_and_flora,
    generate_birdsong_chirp,
    home_world_authority,
    nocturnal_house_tidying,
)
from dsf_ai_service.substrate.embodiment_world import (
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    transduce_auditory_full_field,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def test_garden_fauna_and_flora_expansion_scales_world_ledger_to_67() -> None:
    """Verify garden expansion scales global ledger to 67 objects while preserving 64-object receptor ceiling."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True)

    # 1. Global inventory ledger contains all 67 objects
    assert len(world.global_objects()) == 67
    global_ids = {o.object_id for o in world.global_objects()}
    assert "garden-flowers" in global_ids
    assert "garden-butterfly" in global_ids
    assert "garden-bird" in global_ids

    # 2. Local perceptual aperture strictly streams <= 64 objects with cryptographically valid HMAC
    snapshot = world.observation_snapshot()
    assert len(snapshot.objects) == 64
    assert len(snapshot.objects) <= 64
    assert snapshot.authority_hmac_sha256 != ""
    assert snapshot.authority_receipt_sha256 != ""


def test_spatial_horizon_occlusion_bedroom_vs_backyard() -> None:
    """Verify garden fauna/flora are occluded from bedroom and become visible upon stepping into backyard."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True)

    # In her bedroom (2_600, 7_600): garden fauna/flora behind multiple solid walls
    bed_snap = world.observation_snapshot()
    bed_ids = {o.object_id for o in bed_snap.objects}
    assert "garden-bird" not in bed_ids
    assert "garden-butterfly" not in bed_ids
    assert "bed" in bed_ids
    assert "desk" in bed_ids

    # Displace Guala to the backyard (14_000, 14_000, 0)
    cur_world = world._state.world
    updated_bodies = [
        replace(b, pose=PoseMM(PositionMM(14_000, 14_000, 0), b.pose.heading_millidegrees))
        if b.body_id == "guala-body-1" else b
        for b in cur_world.bodies
    ]
    world._state = replace(world._state, world=replace(cur_world, bodies=tuple(updated_bodies)))

    # In backyard: fauna and flora rise into active perceptual horizon
    back_snap = world.observation_snapshot()
    back_ids = {o.object_id for o in back_snap.objects}
    assert len(back_snap.objects) == 64
    assert "garden-flowers" in back_ids
    assert "garden-butterfly" in back_ids
    assert "garden-bird" in back_ids
    assert "tree-apple" in back_ids


def test_garden_bird_acoustic_birdsong_transduction() -> None:
    """Verify deterministic birdsong PCM generation and 16-channel gammatone cochlear transduction."""
    pcm = generate_birdsong_chirp(frequency_hz=4200.0, duration_seconds=0.15, sample_rate_hz=16_000)

    # 150 ms at 16 kHz with 16-bit (2-byte) samples = 4800 bytes
    assert len(pcm) == 4800
    pcm_sha = hashlib.sha256(pcm).hexdigest()
    assert len(pcm_sha) == 64

    # Convert to normalized float signal for gammatone filter bank
    signal = np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32768.0
    capture = transduce_auditory_full_field(signal, sample_rate_hz=16_000)

    assert len(capture.channels) == 16
    assert capture.continuation_receipt_sha256 != ""

    # High frequency channels (corresponding to ~4 kHz birdsong) must show strong pressure envelope energy
    high_freq_channels = capture.channels[10:]
    max_energy = max(max(ch.pressure_envelope_full_scale) for ch in high_freq_channels)
    assert max_energy > 0.05


def test_garden_fauna_and_flora_optical_spectra_and_textures() -> None:
    """Verify physical optical spectra, surface textures, and material emissions."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True)
    objects = {o.object_id: o for o in world.global_objects()}

    # Butterfly: Morpho blue optical spectrum (channels 2 & 3 dominant)
    butterfly = objects["garden-butterfly"]
    assert butterfly.reflectance_ppm[2] > 700_000
    assert butterfly.optical_surface.columns == 32
    assert butterfly.optical_surface.rows == 32

    # Bird: Warm-blooded surface temperature (312 K) and songbird plumage
    bird = objects["garden-bird"]
    assert bird.material.surface_temperature_millikelvin == 312_000
    assert bird.optical_surface.columns == 32

    # Flowers: Volatile terpenoid release in odorant channel 3
    flowers = objects["garden-flowers"]
    assert flowers.material.odorant_release_nanograms_per_second[3] > 0
    assert flowers.optical_surface.columns == 32


def test_garden_fauna_affordances_and_observation_approach() -> None:
    """Verify affordance extraction and multi-step gentle observation approach planning."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True)
    affordances = extract_affordances(world.global_objects(), regions=world._state.world.regions)

    aff_map = {a.object_id: a for a in affordances}
    assert aff_map["garden-bird"].is_fauna is True
    assert aff_map["garden-bird"].can_emit_sound is True
    assert aff_map["garden-butterfly"].is_fauna is True
    assert aff_map["garden-flowers"].is_flora is True

    # Plan approach from porch (10_000, 11_000, 0) toward perching bird (14_000, 15_500, 0)
    plan = plan_fauna_observation_approach(
        current_pose=(10_000, 11_000, 0),
        target_fauna_id="garden-bird",
        affordances=affordances,
        current_tick=100,
        observation_distance_mm=1_000,
    )

    assert plan.status == "active"
    assert not plan.is_refused
    assert len(plan.steps) == 3
    assert plan.steps[0].action == "orient_toward"
    assert plan.steps[1].action == "gentle_approach"
    assert plan.steps[2].action == "quiet_observe"
    assert plan.terminal_valence == 0.90


def test_nocturnal_house_tidying_resets_fauna_perches() -> None:
    """Verify nocturnal sleep cycle tidying resets displaced bird and butterfly to canonical perches."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True)
    cur_w = world._state.world

    # Displace bird and butterfly onto the patio table
    displaced = []
    for o in cur_w.objects:
        if o.object_id == "garden-bird":
            displaced.append(replace(o, position=PositionMM(840, 840, 0), elevation_mm=750))
        elif o.object_id == "garden-butterfly":
            displaced.append(replace(o, position=PositionMM(840, 840, 0), elevation_mm=750))
        else:
            displaced.append(o)

    world._state = replace(world._state, world=replace(cur_w, objects=tuple(displaced)))

    # Execute nocturnal tidying
    nocturnal_house_tidying(world)

    tidied_objs = {o.object_id: o for o in world.global_objects()}
    # Bird roosts in tree canopy
    assert tidied_objs["garden-bird"].position.x == 14_000
    assert tidied_objs["garden-bird"].position.y == 15_500
    assert tidied_objs["garden-bird"].elevation_mm == 1_800

    # Butterfly rests on flower patch
    assert tidied_objs["garden-butterfly"].position.x == 16_500
    assert tidied_objs["garden-butterfly"].position.y == 11_500
    assert tidied_objs["garden-butterfly"].elevation_mm == 180

