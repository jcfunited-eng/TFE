"""tests/test_sensorimotor_contact_learning.py — Constitutive Electromechanical Contact Learning Verification.

Validates the experience-caused auditory-vocal sensorimotor learning mechanism:
1. End-to-End Loop Contact Plasticity Practice & Post-Expiration Recall:
   - Guala naturally progresses through infant motor exploration up to beat 54.
   - Caregiver presents authentic PCM audio of 'mah0' via microphone on beat 55.
   - Guala naturally executes vocal practice with 'mah0' through the live functional loop.
   - Measured self-hearing frames return to her ear on beat 56 and deform contact geometry via radial return plastic yield.
   - Material volume conservation (A * ell == Omega_0) and yield consistency (f <= 0) hold strictly.
   - Plastic work dissipation is accounted in strict SI Joules (W_p > 0).
   - 20 beats of silence elapse (beats 57..77), cleanly expiring recent-cue target windows and decaying polarization traces.
   - Both practiced and unpracticed control organisms are reconstituted as matched restored bodies from canonical encoding.
   - Later cue presentation at beat 78: caregiver presents 'mah0' to BOTH restored bodies through the ordinary loop.
   - The practiced organism conducts acoustic energy across the permanently modified contacts and unassistedly speaks
     'mah at 345 Hz' under 'sensorimotor conduction: mah0'.
   - The unpracticed control organism never underwent paired practice, its contacts remain at virgin resting gap (ell_0 = 10 um),
     and it does NOT emit 'mah0' under sensorimotor conduction.
2. Constitutive Radial Return and Volume Conservation Invariant Gate:
   - Verifies that every yielded junction satisfies coupled mechanical-electrostatic equilibrium (residual <= 1e-6).
   - Verifies material volume conservation (A * ell == Omega_0 everywhere).
   - Verifies plastic work dissipation accounting (Delta_W > 0 in Joules).
   - Verifies conductance formula g == sigma_mat * Omega_0 / ell^2 with sigma_mat = 0.05 mS*um/um^2.
3. Authentic Rest State Invariant:
   - Verifies that undeformed virgin contacts stay strictly below activation threshold (~0.015 V << 0.22 V),
     guaranteeing silence/rest without argmax heuristics.
4. Negative Cue Discrimination:
   - Verifies that presenting an alternative acoustic cue ('ah0') does not trigger the learned /m/ onset.
"""
from __future__ import annotations

import os
import time
import pytest
import numpy as np

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
from dsf_ai_service.substrate.guala_sensorimotor_mesh import (
    GualaSensorimotorMesh,
    ELL_0,
    ELL_MIN,
    OMEGA_0,
    SIGMA_MAT,
    V_THRESHOLD,
    YIELD_STRESS,
    HARDENING,
)

IDENTITY_PR = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
IDENTITY_CTL = "2dd4e70a-f2a0-44c5-a111-f4a5bc915cc2"
UNATTENDED = PhysicalOccurrence("unattended", None)


def test_end_to_end_sensorimotor_contact_plasticity_learning() -> None:
    """Verifies end-to-end auditory-vocal practice and unassisted recall through the live physical loop."""
    world_pr = home_world_authority(identity=IDENTITY_PR)
    org_pr = FunctionalOrganism.genesis(identity=IDENTITY_PR, organism_tick=1)
    loop_pr = FunctionalPhysicalLoop()

    world_ctl = home_world_authority(identity=IDENTITY_CTL)
    org_ctl = FunctionalOrganism.genesis(identity=IDENTITY_CTL, organism_tick=1)
    loop_ctl = FunctionalPhysicalLoop()

    # Practice Phase for Practiced Organism:
    # Guala naturally progresses through infant motor exploration up to beat 54
    for b in range(1, 55):
        loop_pr.settle(org_pr, world_pr, UNATTENDED)
        loop_ctl.settle(org_ctl, world_ctl, UNATTENDED)

    # Caregiver presents authentic PCM audio of 'mah0' via microphone on beat 55
    pcm_mah = syllable_pcm(SYLLABLE_DRIVES["mah0"], seed=1)
    sensory_mah = LeanSensoryOccurrence(source="microphone", retina_rgb_u8=None, pressure_s16le=pcm_mah)

    # Beat 55: Practiced organism receives paired presentation of mah0 while naturally babbling
    res55_pr = loop_pr.settle(org_pr, world_pr, PhysicalOccurrence("sensory", sensory_mah))
    assert res55_pr.observation["her_act"] == "say"
    assert res55_pr.observation["said"] == "mah at 345 Hz"

    # Control organism continues unattended without paired presentation
    res55_ctl = loop_ctl.settle(org_ctl, world_ctl, UNATTENDED)

    # Beat 56: Self-hearing reafference returns and settles
    # Drives radial return plastic yield on contact junctions
    loop_pr.settle(org_pr, world_pr, UNATTENDED)
    loop_ctl.settle(org_ctl, world_ctl, UNATTENDED)

    mesh_pr = org_pr._sensorimotor_mesh
    mesh_ctl = org_ctl._sensorimotor_mesh

    # Verify plastic work is positive and contacts have deformed in practiced body
    assert mesh_pr.total_plastic_work > 0.0
    assert mesh_pr.total_plastic_work_joules > 0.0
    assert mesh_pr.ell.min() < ELL_0
    assert mesh_pr.ell.min() >= ELL_MIN

    # Control organism never underwent paired practice; its contacts remain undeformed
    assert mesh_ctl.total_plastic_work == 0.0
    assert mesh_ctl.ell.min() == ELL_0

    # Advance loop 20 beats past target expiration (> 6 beats) in silence (beats 57..77)
    for b in range(57, 78):
        loop_pr.settle(org_pr, world_pr, UNATTENDED)
        loop_ctl.settle(org_ctl, world_ctl, UNATTENDED)

    # Reconstitute matched bodies from canonical encoding
    restored_pr = FunctionalOrganism.restore(org_pr.encoded())
    restored_ctl = FunctionalOrganism.restore(org_ctl.encoded())

    # Later Recall Phase at beat 78:
    # Caregiver presents 'mah0' to BOTH practiced and unpracticed control restored bodies
    loop_pr.settle(restored_pr, world_pr, PhysicalOccurrence("sensory", sensory_mah))
    res_pr_silence = loop_pr.settle(restored_pr, world_pr, UNATTENDED)

    loop_ctl.settle(restored_ctl, world_ctl, PhysicalOccurrence("sensory", sensory_mah))
    res_ctl_silence = loop_ctl.settle(restored_ctl, world_ctl, UNATTENDED)

    # Practiced organism unassistedly recalls mah0 via sensorimotor contact conduction in ordinary loop
    assert res_pr_silence.observation["her_act"] == "say"
    assert res_pr_silence.observation["said"] == "mah at 345 Hz"
    assert "sensorimotor conduction: mah0" in str(res_pr_silence.observation.get("act_reason", ""))

    # Control organism never underwent practice; its contacts remain undeformed and it does NOT fire sensorimotor mah0
    assert "sensorimotor conduction: mah0" not in str(res_ctl_silence.observation.get("act_reason", ""))
    assert res_ctl_silence.observation.get("said") != "mah at 345 Hz"


def test_constitutive_radial_return_and_volume_conservation() -> None:
    """Verifies that all contact junctions strictly conserve volume and satisfy the yield criterion."""
    mesh = GualaSensorimotorMesh()
    assert np.all(mesh.ell == ELL_0)
    assert np.allclose(mesh.area * mesh.ell, OMEGA_0)

    # Stimulation that triggers plastic yield
    mesh.theta = np.array([0.1, 0.9, 0.7, 0.1, 0.05, 0.01])
    self_frames = [((0.008, 0.05, 0.85, 0.08, 0.01, 0.005, 0.005))] * 25

    yielded_count = mesh.plastic_settle((3450, 0, 1), self_frames)
    assert yielded_count > 0

    # Volume conservation invariant: A * ell == Omega_0 everywhere
    assert np.allclose(mesh.area * mesh.ell, OMEGA_0)

    # Gap bounds invariant: ELL_MIN <= ell <= ELL_0
    assert np.all(mesh.ell >= ELL_MIN)
    assert np.all(mesh.ell <= ELL_0)

    # Conductance formula invariant: g == sigma_mat * Omega_0 / ell^2
    expected_g = SIGMA_MAT * OMEGA_0 / (mesh.ell ** 2)
    assert np.allclose(mesh.conductance, expected_g)

    # Recompute exact causal coactivity and verify coupled equilibrium residual
    p_idx = 0
    onset_frames = 4
    coactivity = np.zeros((6, 20), dtype=np.float64)
    for tau, f in enumerate(self_frames):
        band_frac = np.array(f[1:], dtype=np.float64)
        m_eff = np.zeros(20, dtype=np.float64)
        if tau < onset_frames:
            m_eff[1] = 1.0
        else:
            m_eff[11 + 0] = 1.0
        m_eff[11 + 5 + p_idx] = 1.0
        coactivity += np.outer(mesh.theta * band_frac, m_eff)

    residual = mesh.equilibrium_residual(coactivity)
    assert residual <= 1e-6, f"Coupled equilibrium residual violated: max residual = {residual}"
    assert mesh.total_plastic_work > 0.0
    assert mesh.total_plastic_work_joules > 0.0


def test_unpracticed_control_silence_and_rest_invariance() -> None:
    """Verifies that unpracticed virgin contacts dissipate acoustic energy and return None (Rest State)."""
    mesh = GualaSensorimotorMesh()
    # Feed authentic mah0 frames into undeformed mesh
    pcm_mah = syllable_pcm(SYLLABLE_DRIVES["mah0"], seed=42)
    from dsf_ai_service.guala_cochlea import one_self_hearing_hop
    from dsf_ai_service.guala_acoustic_gate import frames_of_cochleae
    _t, _l, coch, _c = one_self_hearing_hop(pcm_mah)
    frames_mah = frames_of_cochleae(coch)

    drive, name, info = mesh.readout(frames_mah)
    assert drive is None
    assert name is None
    assert info["max_onset_v"] < V_THRESHOLD
    assert info["max_vowel_v"] < V_THRESHOLD
    assert info["max_pitch_v"] < V_THRESHOLD


def test_negative_cue_discrimination() -> None:
    """Verifies that presenting 'ah0' to a 'mah0'-practiced organism does not actuate the /m/ onset."""
    mesh = GualaSensorimotorMesh()
    mesh.theta = np.array([0.01, 0.90, 0.40, 0.05, 0.02, 0.005])

    # Practice mah0
    pcm_mah = syllable_pcm(SYLLABLE_DRIVES["mah0"], seed=42)
    from dsf_ai_service.guala_cochlea import one_self_hearing_hop
    from dsf_ai_service.guala_acoustic_gate import frames_of_cochleae
    _t, _l, coch_mah, _c = one_self_hearing_hop(pcm_mah)
    frames_mah = frames_of_cochleae(coch_mah)
    mesh.plastic_settle((3450, 0, 1), frames_mah)

    # Present ah0 cue
    pcm_ah = syllable_pcm(SYLLABLE_DRIVES["ah0"], seed=42)
    _t, _l, coch_ah, _c = one_self_hearing_hop(pcm_ah)
    frames_ah = frames_of_cochleae(coch_ah)

    drive_ah, name_ah, info_ah = mesh.readout(frames_ah)
    # Onset 1 ('m') must not fire for ah0 cue
    assert info_ah["v_onset"][1] < V_THRESHOLD or (drive_ah is not None and drive_ah[2] != 1)
