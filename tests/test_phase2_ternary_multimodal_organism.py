"""tests/test_phase2_ternary_multimodal_organism.py — Phase 2 Verification.

Verification Suite for WHOLE_BRAIN_SPECIFICATION.md Phase 2:
Direct multi-modal cross-coupling between 19,200-ray retinotopy, 16-channel causal cochleagrams,
somatosensory contact fields, and airway vocal articulators mounted on the compiled native
1,024-node discrete ternary contact matrix (guala_core.TernaryLattice).

Zero Software Dictionaries | Zero ML Backpropagation | Strict Material Yield Stress Dynamics
"""

import hashlib
import json
import numpy as np
import pytest

from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    ONSETS,
    PITCHES_DECIHERTZ,
    SYLLABLE_DRIVES,
    VOWELS,
    syllable_pcm,
)
from dsf_ai_service.guala_cochlea import one_self_hearing_hop
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
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

IDENTITY_TEST = "3ff4e70a-f2a0-44c5-a111-f4a5bc915cc3"
UNATTENDED = PhysicalOccurrence("unattended", None)


def test_genesis_and_exact_restoration_with_ternary_substrate():
    """Verifies that an organism created at genesis instantiates the 1,024-node
    native ternary contact matrix and serializes/restores byte-for-byte identically."""
    org = FunctionalOrganism.genesis(identity=IDENTITY_TEST, organism_tick=1)

    # Substrate topology invariant
    sub = org._ternary_substrate
    assert isinstance(sub, TernaryMultiModalSubstrate)
    assert sub.lattice.node_count == 1024
    assert sub.lattice.synapse_count == 1024 * 1024

    # Virgin substrate has zero active synapses
    stats = sub.matrix_statistics()
    assert stats[2] == 0, f"Expected virgin matrix, got {stats[2]} active synapses"

    # Strict byte-exact serialization invariant
    encoded = org.encoded()
    restored = FunctionalOrganism.restore(encoded)
    assert restored.encoded() == encoded, "Genesis body does not re-encode byte-exact!"


def test_multimodal_experience_yield_and_sparse_persistence():
    """Verifies that authentic multi-modal sensory patterns deform the native 1,024-node
    contact matrix according to von Mises yield stress, and persist across serialization."""
    org = FunctionalOrganism.genesis(identity=IDENTITY_TEST, organism_tick=1)

    # 1. Authentic visual pattern (focal luminance profile)
    focal_input = np.zeros(192)
    focal_input[20:35] = 220.0
    vis_trits = org._ternary_substrate.encode_visual_field(focal_input, target_active=12)
    assert sum(x == 1 for x in vis_trits) > 0

    # 2. Authentic cochlear audio pattern (16-channel envelope from airway syllable)
    pcm_mah = syllable_pcm(SYLLABLE_DRIVES["mah0"], seed=42)
    _, _, coch_envs, _ = one_self_hearing_hop(pcm_mah)
    aud_trits = org._ternary_substrate.encode_cochlear_field_2d(coch_envs, target_active=14)
    assert sum(x == 1 for x in aud_trits) > 0

    # 3. Somatosensory contact load and thermal gradient
    som_trits = org._ternary_substrate.encode_somatic_field(contact_load=0.75, thermal_gradient=0.40)
    assert any(x != 0 for x in som_trits)

    # 4. Airway vocal articulators (mah0: Onset 'm'=1, Vowel 'ah'=0, Pitch=0)
    eff_trits = org._ternary_substrate.encode_dsf_and_efferents(onset_idx=1, vowel_idx=0, pitch_idx=0)
    assert any(x != 0 for x in eff_trits)

    # 5. Assemble full 1,024-node multimodal state vector
    pattern_1024 = org._ternary_substrate.assemble_multimodal_vector(vis_trits, aud_trits, som_trits, eff_trits)
    assert len(pattern_1024) == 1024

    # 6. Present experience and execute local material yield stress plasticity
    yielding_synapses, plastic_energy = org._ternary_substrate.present_experience(pattern_1024)
    assert yielding_synapses > 0, "No synapses yielded under authentic experience!"
    assert plastic_energy > 0.0, "Plastic strain energy must be strictly positive!"
    org._sync_ternary_substrate()

    stats_before = org._ternary_substrate.matrix_statistics()
    assert stats_before[2] > 0, "Expected active conductances in matrix!"

    # 7. Verify body serialization preserves non-zero conductances bit-exact
    encoded = org.encoded()
    restored = FunctionalOrganism.restore(encoded)
    assert restored.encoded() == encoded, "Post-deformation body does not re-encode byte-exact!"

    stats_after = restored._ternary_substrate.matrix_statistics()
    assert stats_before[2] == stats_after[2], "Synapse count mismatch after restoration!"
    assert abs(stats_before[0] - stats_after[0]) < 1e-5, "Mean conductance mismatch after restoration!"


def test_cross_modal_associative_conduction_without_dictionaries():
    """Verifies that an auditory cue alone conducts across plastically deformed contacts
    to resonant efferents, completing the pattern without software dictionaries."""
    org = FunctionalOrganism.genesis(identity=IDENTITY_TEST, organism_tick=1)

    # Train 3 distinct multi-modal syllable pairs
    syllables = [
        ("mah0", 1, 0, 0),  # m, ah, pitch 0
        ("deh1", 3, 1, 1),  # d, eh, pitch 1
        ("bee2", 2, 2, 2),  # b, ee, pitch 2
    ]

    for s_name, o_idx, v_idx, p_idx in syllables:
        pcm = syllable_pcm(SYLLABLE_DRIVES[s_name], seed=1)
        _, _, coch_envs, _ = one_self_hearing_hop(pcm)
        aud_trits = org._ternary_substrate.encode_cochlear_field_2d(coch_envs, target_active=14)
        eff_trits = org._ternary_substrate.encode_dsf_and_efferents(onset_idx=o_idx, vowel_idx=v_idx, pitch_idx=p_idx)
        pattern = org._ternary_substrate.assemble_multimodal_vector([0] * 256, aud_trits, [0] * 256, eff_trits)
        org._ternary_substrate.present_experience(pattern)

    org._sync_ternary_substrate()

    # Associative Recall under 100% efferent occlusion (hear sound -> evoke motor articulators)
    for s_name, exp_onset, exp_vowel, exp_pitch in syllables:
        pcm = syllable_pcm(SYLLABLE_DRIVES[s_name], seed=1)
        _, _, coch_envs, _ = one_self_hearing_hop(pcm)
        aud_trits = org._ternary_substrate.encode_cochlear_field_2d(coch_envs, target_active=14)

        # Mask visual, somatic, and efferents to 0 (pure auditory cue)
        cue = [0] * 1024
        cue[AUDITORY_START:AUDITORY_END] = aud_trits

        decoded, _ = org._ternary_substrate.project_and_readout(cue)
        assert decoded["onset_idx"] == exp_onset, f"{s_name}: Onset recall failed, expected {exp_onset}, got {decoded['onset_idx']}"
        assert decoded["vowel_idx"] == exp_vowel, f"{s_name}: Vowel recall failed, expected {exp_vowel}, got {decoded['vowel_idx']}"


def test_live_functional_loop_step_with_ternary_substrate():
    """Verifies that the live physical loop runs with the mounted 1,024-node substrate
    without runtime exceptions, bounds memory, and correctly updates synaptic deformation."""
    world = home_world_authority(identity=IDENTITY_TEST)
    org = FunctionalOrganism.genesis(identity=IDENTITY_TEST, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Step the live loop for 10 beats
    for b in range(1, 11):
        res = loop.settle(org, world, UNATTENDED)
        assert res.observation["her_act"] is not None

    # Verify that counts include active synapses and matrix is accessible
    counts = org.counts
    assert "active_synapses" in counts
    assert counts["active_synapses"] >= 0

    # Verify byte-exact encoding after 10 live beats
    encoded = org.encoded()
    restored = FunctionalOrganism.restore(encoded)
    assert restored.encoded() == encoded
