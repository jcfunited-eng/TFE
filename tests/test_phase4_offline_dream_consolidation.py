"""tests/test_phase4_offline_dream_consolidation.py

Verification suite for Phase 4 of WHOLE_BRAIN_SPECIFICATION.md:
Offline Dream Replay & Synaptic Consolidation in the ArcLoom Neuromorphic Substrate.

Verifies:
  1. Native Rust `TernaryLattice.decay_and_prune` executes continuum synaptic downscaling
     (Synaptic Homeostasis Hypothesis) and prunes weak conductances below threshold.
  2. `TernaryLattice.replay_pattern` reinforces salient multi-modal Krimelack pathways during offline sleep.
  3. `FunctionalOrganism._dream` executes offline dream replay of salient waking Krimelacks
     when Guala is asleep (quiescence M_k ≈ 0), consolidating long-term pathways and pruning noise.
  4. Synaptic downscaling and pruning restore matrix capacity and prevent catastrophic cross-talk saturation.
  5. Persistent body serialization preserves consolidated ternary conductances across sleep cycles bit-exact.
"""

from __future__ import annotations

import pytest
import numpy as np

import guala_core
from guala_core import TernaryLattice
from dsf_ai_service.substrate.ternary_multimodal_substrate import (
    TernaryMultiModalSubstrate,
    VISUAL_START,
    VISUAL_END,
    AUDITORY_START,
    AUDITORY_END,
    SOMATIC_START,
    SOMATIC_END,
    EFFERENT_START,
    EFFERENT_END,
)
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence, LeanSensoryOccurrence

IDENTITY_TEST = "3ff4e70a-f2a0-44c5-a111-f4a5bc915cc4"
UNATTENDED = PhysicalOccurrence("unattended", None)


def _present(food: str) -> PhysicalOccurrence:
    return PhysicalOccurrence(
        "sensory",
        LeanSensoryOccurrence(
            source="caretaker-food",
            retina_rgb_u8=None,
            pressure_s16le=None,
            present_food=food,
        ),
    )


def test_rust_lattice_decay_and_prune() -> None:
    """
    1. Verify native Rust TernaryLattice downscaling and pruning mechanics.
    """
    lattice = TernaryLattice(yield_threshold=0.30, plastic_rate=0.40, activation_threshold=1.0)

    # Present a strong pattern across nodes 0, 1, 2
    pat1 = [0] * 1024
    pat1[0] = 1
    pat1[1] = 1
    pat1[2] = 1
    y1, s1 = lattice.present_and_yield(pat1)
    assert y1 == 3
    assert s1 > 0.0

    g_init = lattice.get_conductance(0, 1)
    assert g_init > 0.20

    # Replay pattern with plastic boost
    y_rep, s_rep = lattice.replay_pattern(pat1, plastic_boost=1.5)
    g_replayed = lattice.get_conductance(0, 1)
    assert g_replayed > g_init, f"Replay should reinforce conductance: {g_replayed} > {g_init}"

    # Downscale conductances: decay_factor=0.20, min_conductance=0.10
    decayed, pruned = lattice.decay_and_prune(decay_factor=0.20, min_conductance=0.10)
    assert decayed > 0
    assert pruned == 0
    g_decayed = lattice.get_conductance(0, 1)
    assert abs(g_decayed - (g_replayed * 0.80)) < 1e-4

    # Strong prune: prune everything below 0.50
    decayed2, pruned2 = lattice.decay_and_prune(decay_factor=0.0, min_conductance=0.50)
    assert pruned2 > 0
    assert lattice.get_conductance(0, 1) == 0.0


def test_krimelack_multimodal_replay_and_pruning() -> None:
    """
    2. Verify multi-modal Krimelack replay and noise elimination on TernaryMultiModalSubstrate.
    """
    substrate = TernaryMultiModalSubstrate(yield_threshold=0.30, plastic_rate=0.35, activation_threshold=0.30)

    # Construct a salient multi-modal Krimelack (caregiver acoustic pattern + vocal response)
    audio_trits = [0] * 256
    audio_trits[10] = 1
    audio_trits[25] = 1

    efferent_trits = [0] * 256
    efferent_trits[128] = 1  # onset 'm' node 0
    efferent_trits[129] = 1  # onset 'm' node 1
    efferent_trits[172] = 1  # vowel 'ah'

    krimelack_salient = substrate.assemble_multimodal_vector(
        [0] * 256, audio_trits, [0] * 256, efferent_trits
    )

    # Present waking experience
    substrate.present_experience(krimelack_salient)
    initial_conductance = substrate.lattice.get_conductance(AUDITORY_START + 10, EFFERENT_START + 128)
    assert initial_conductance > 0.0

    # Inject weak random sensory noise
    noise_pat = [0] * 1024
    noise_pat[50] = 1
    noise_pat[700] = 1
    substrate.present_experience(noise_pat)
    noise_g = substrate.lattice.get_conductance(50, 700)
    assert noise_g > 0.0

    # Offline sleep: replay the salient Krimelack
    y_rep, s_rep = substrate.replay_krimelack(krimelack_salient, factor=1.5)
    boosted_g = substrate.lattice.get_conductance(AUDITORY_START + 10, EFFERENT_START + 128)
    assert boosted_g > initial_conductance

    # Sleep downscaling and pruning:
    # Set min_conductance higher than the noise conductance but lower than the boosted salient conductance
    decayed, pruned = substrate.sleep_decay_and_prune(decay_factor=0.15, min_conductance=noise_g * 0.90)
    assert pruned >= 1
    assert substrate.lattice.get_conductance(50, 700) == 0.0  # Noise pruned to zero
    assert substrate.lattice.get_conductance(AUDITORY_START + 10, EFFERENT_START + 128) > 0.0  # Salient memory survives


def test_organism_dream_consolidation_lifecycle() -> None:
    """
    3. Verify closed-loop offline dream replay and synaptic consolidation within FunctionalOrganism.
    """
    world = home_world_authority(identity=IDENTITY_TEST)
    organism = FunctionalOrganism.genesis(identity=IDENTITY_TEST, organism_tick=1)

    # 1. Experience awake events that form moments with Krimelacks (e.g. caretaker apple presentation)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, UNATTENDED)
    loop.settle(organism, world, _present("apple"))
    for _ in range(6):
        loop.settle(organism, world, UNATTENDED)

    moments = organism._state.get("moments", {})
    assert len(moments) > 0, "Awake processing must form moments"

    # Verify that moments contain multi-modal Krimelack signatures
    has_krimelack = any("krimelack" in m for m in moments.values())
    assert has_krimelack, "Formed moments must contain multi-modal Krimelacks"

    # Record active synapses before sleep
    synapses_before_sleep = organism.counts["active_synapses"]
    assert synapses_before_sleep > 0

    # 2. Put organism to sleep
    organism._state["asleep"] = True
    organism._state["sleep_pressure"] = 500

    # Settle sleep beat to trigger _dream()
    sleep_res = loop.settle(organism, world, UNATTENDED)
    assert sleep_res.observation["her_act"] == "sleep"

    # Verify that sleep consolidation occurred:
    assert "ternary_substrate" in organism._state
    stored_sub = organism._state["ternary_substrate"]
    assert "sparse_conductances" in stored_sub

    # 3. Verify persistence across serialization after sleep consolidation
    encoded_state = organism.encoded()
    restored_organism = FunctionalOrganism.restore(encoded_state)

    orig_stats = organism._ternary_substrate.matrix_statistics()
    restored_stats = restored_organism._ternary_substrate.matrix_statistics()

    assert orig_stats[2] == restored_stats[2], f"Active synapse count must match exactly: {orig_stats[2]} vs {restored_stats[2]}"
    assert abs(orig_stats[0] - restored_stats[0]) < 1e-5, f"Mean conductance mismatch: {orig_stats[0]} vs {restored_stats[0]}"
    assert abs(orig_stats[1] - restored_stats[1]) < 1e-5, f"Max conductance mismatch: {orig_stats[1]} vs {restored_stats[1]}"
    assert restored_organism.encoded() == encoded_state, "Body state must serialize byte-for-byte identical after sleep consolidation"


def test_pruning_restores_matrix_capacity_and_prevents_saturation() -> None:
    """
    4. Verify that offline sleep consolidation prevents catastrophic cross-talk saturation.
    """
    substrate = TernaryMultiModalSubstrate(yield_threshold=0.30, plastic_rate=0.35, activation_threshold=0.30)

    # Learn 3 structured multi-modal memories
    memories = []
    for m_idx in range(3):
        pat = [0] * 1024
        # Orthogonal visual cues
        pat[m_idx * 20] = 1
        pat[m_idx * 20 + 1] = 1
        # Associated vocal efferent onset column
        pat[EFFERENT_START + 128 + m_idx * 4] = 1
        pat[EFFERENT_START + 128 + m_idx * 4 + 1] = 1
        substrate.present_experience(pat)
        memories.append(pat)

    # Test baseline associative recall: visual cue recalls associated vocal onset
    for m_idx, mem in enumerate(memories):
        cue = [0] * 1024
        cue[m_idx * 20] = 1
        cue[m_idx * 20 + 1] = 1
        decoded, _ = substrate.project_and_readout(cue)
        assert decoded["onset_idx"] == m_idx, f"Memory {m_idx} must be recalled before noise"

    # Inject waking non-orthogonal background noise across 25 presentations
    rng = np.random.RandomState(42)
    for _ in range(25):
        noise = [0] * 1024
        active_nodes = rng.choice(1024, size=6, replace=False)
        for an in active_nodes:
            noise[an] = 1 if rng.rand() > 0.5 else -1
        substrate.present_experience(noise)

    noisy_stats = substrate.matrix_statistics()
    noisy_synapse_count = noisy_stats[2]

    # Offline sleep: replay core memories with plastic boost and execute downscaling/pruning
    for mem in memories:
        substrate.replay_krimelack(mem, factor=1.5)

    decayed, pruned = substrate.sleep_decay_and_prune(decay_factor=0.25, min_conductance=0.20)
    assert pruned > 0, "Synaptic pruning must eliminate weak noise conductances"

    clean_stats = substrate.matrix_statistics()
    clean_synapse_count = clean_stats[2]
    assert clean_synapse_count < noisy_synapse_count, "Pruning must reduce active synapse count"

    # Verify that core memories still achieve 100% accurate associative recall after sleep consolidation
    for m_idx, mem in enumerate(memories):
        cue = [0] * 1024
        cue[m_idx * 20] = 1
        cue[m_idx * 20 + 1] = 1
        decoded, _ = substrate.project_and_readout(cue)
        assert decoded["onset_idx"] == m_idx, f"Core memory {m_idx} must survive sleep consolidation with 100% recall"
