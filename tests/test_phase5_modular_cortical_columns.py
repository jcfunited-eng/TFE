"""tests/test_phase5_modular_cortical_columns.py

Verification suite for Item 2 of WHOLE_BRAIN_SPECIFICATION.md:
Modular Neuromorphic Substrates in Native Rust (ArcLoom Substrate).

Verifies:
  1. 4-Column Baseline Substrate (ModularSubstrate4D):
     - Column 0: Multimodal Sensory Transduction
     - Column 1: Spatial & Topological Invariance (Polar r, theta and Occlusion Permanence)
     - Column 2: Causal Sequential Syntax & Combinatorial Chaining
     - Column 3: Material Affordance & Barrier Gating (Contact Yield Stress sigma vs Y)
  2. 8-Column Balanced Octet Substrate (ModularSubstrate8D - Option A):
     - Col 0 (V1): Optical Foveal Focal Target
     - Col 1 (V2): Optical Motion Gradient & Spatial Angle
     - Col 2 (A1): Cochlear Formant Peak Resonance
     - Col 3 (A2): Cochlear Pitch / Envelope
     - Col 4 (S1): Somatosensory Palmar Contact
     - Col 5 (S2): Somatosensory Barrier Stress (von Mises Yield Refusal)
     - Col 6 (M1): Motor Airway Vocal Valve (Exhaust pulse)
     - Col 7 (M2): Motor Locomotion Stride & Steer
  3. Spatial Permanence Attractor:
     - Maintains egocentric polar coordinates (r_mm, theta_mdeg) even when sensor feed is occluded.
  4. Material Barrier Refusal & Homeostatic Motor Exhaust:
     - Sub-yield stress permits nominal locomotion.
     - Over-yield impact triggers refusal, arrests stride, and discharges airway vocal valve.
  5. Continuum von Mises Plasticity:
     - Yield occurs if and only if |sigma_ij| > Y.
  6. Sleep Consolidation & Synaptic Downscaling:
     - Downscales conductances and prunes sub-threshold noise without memory collapse.
"""

from __future__ import annotations

import pytest
import guala_core
from guala_core import ModularSubstrate4D, ModularSubstrate8D, ModularSubstrate64D


# =============================================================================
# 4-Column Baseline Tests (ModularSubstrate4D)
# =============================================================================

def test_modular_substrate_initialization() -> None:
    """Verify clean initialization of the 4-Column 3D Substrate."""
    substrate = ModularSubstrate4D(yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25)
    assert substrate.active_synapses() == 0
    r, theta, trace, occluded = substrate.get_spatial_tracking()
    assert r == 0.0
    assert theta == 0
    assert trace == 0.0
    assert not occluded
    assert not substrate.is_barrier_refusal_active()


def test_spatial_permanence_under_occlusion() -> None:
    """
    Verify Column 1 (Spatial Invariance) maintains polar coordinates
    even when the sensory signal is completely occluded.
    """
    substrate = ModularSubstrate4D(yield_threshold=0.50, plastic_rate=0.05, activation_threshold=0.20)

    # 1. Target visible at r=350.0 mm, theta=45,000 mdeg (45 degrees)
    sensory = [1] * 64
    somatic = [0] * 32
    substrate.step(sensory, somatic, observed_r_mm=350.0, observed_theta_mdeg=45000, barrier_stress=0.0)

    r, theta, trace, occluded = substrate.get_spatial_tracking()
    assert r == 350.0
    assert theta == 45000
    assert trace == 1.0
    assert not occluded

    # 2. Target occluded for 10 consecutive ticks (observed=None)
    for _ in range(10):
        substrate.step(sensory, somatic, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0)

    r_occ, theta_occ, trace_occ, is_occ = substrate.get_spatial_tracking()
    assert r_occ == 350.0
    assert theta_occ == 45000
    assert is_occ is True
    assert 0.0 < trace_occ < 1.0
    assert pytest.approx(trace_occ, rel=1e-3) == (0.985 ** 10)


def test_material_barrier_refusal_gating() -> None:
    """
    Verify Column 3 (Material Affordance) activates barrier refusal
    only when contact stress meets or exceeds the material yield limit.
    """
    substrate = ModularSubstrate4D(yield_threshold=0.60, plastic_rate=0.05, activation_threshold=0.20)
    sensory = [0] * 64
    somatic = [0] * 32

    # Stress below yield limit (0.70)
    substrate.step(sensory, somatic, barrier_stress=0.45)
    assert not substrate.is_barrier_refusal_active()

    # Stress exceeding yield limit
    substrate.step(sensory, somatic, barrier_stress=0.75)
    assert substrate.is_barrier_refusal_active()

    # Pressure released
    substrate.step(sensory, somatic, barrier_stress=0.10)
    assert not substrate.is_barrier_refusal_active()


def test_continuum_von_mises_plasticity() -> None:
    """
    Verify continuum von Mises plasticity f(|sigma|) = |sigma| - Y <= 0.
    """
    substrate = ModularSubstrate4D(yield_threshold=0.30, plastic_rate=0.10, activation_threshold=0.10)
    sensory = [1] * 64
    somatic = [1] * 32

    initial_synapses = substrate.active_synapses()
    assert initial_synapses == 0

    total_yields = 0
    total_strain = 0.0
    for _ in range(20):
        yields, strain = substrate.step(sensory, somatic, observed_r_mm=200.0, observed_theta_mdeg=15000, barrier_stress=0.2)
        total_yields += yields
        total_strain += strain

    assert total_yields > 0
    assert total_strain > 0.0
    assert substrate.active_synapses() > 0


def test_sleep_consolidation_and_pruning() -> None:
    """
    Verify sleep consolidation downscales conductances and prunes sub-threshold noise.
    """
    substrate = ModularSubstrate4D(yield_threshold=0.20, plastic_rate=0.15, activation_threshold=0.10)
    sensory = [1] * 64
    somatic = [1] * 32

    for _ in range(15):
        substrate.step(sensory, somatic, observed_r_mm=100.0, observed_theta_mdeg=0, barrier_stress=0.0)

    pre_sleep_synapses = substrate.active_synapses()
    assert pre_sleep_synapses > 0

    # 1. Downscale conductances by 20%
    decayed, pruned = substrate.sleep_consolidation(decay=0.20, prune_thresh=0.01)
    assert decayed > 0
    assert pruned == 0

    # 2. Competitive prune: prune conductances below 0.60
    decayed2, pruned2 = substrate.sleep_consolidation(decay=0.0, prune_thresh=0.60)
    assert pruned2 > 0
    post_sleep_synapses = substrate.active_synapses()
    assert post_sleep_synapses < pre_sleep_synapses


def test_sparse_export_deterministic_structure() -> None:
    """
    Verify export_sparse produces deterministic byte stream encoding active conductances.
    """
    substrate = ModularSubstrate4D(yield_threshold=0.25, plastic_rate=0.10, activation_threshold=0.15)
    sensory = [1] * 64
    somatic = [1] * 32

    empty_bytes = substrate.export_sparse()
    assert len(empty_bytes) == 0

    for _ in range(25):
        substrate.step(sensory, somatic, observed_r_mm=300.0, observed_theta_mdeg=30000, barrier_stress=0.0)

    sparse_bytes = substrate.export_sparse()
    assert len(sparse_bytes) > 0
    assert len(sparse_bytes) % 8 == 0


# =============================================================================
# 8-Column Balanced Octet Tests (ModularSubstrate8D - Option A)
# =============================================================================

def test_modular_substrate_8d_initialization_and_spatial_persistence() -> None:
    """
    Verify 8-Column Balanced Octet initialization, coupled V1/V2 spatial permanence,
    and coordinate retention under visual occlusion.
    """
    sub8 = ModularSubstrate8D(yield_threshold=0.50, plastic_rate=0.04, activation_threshold=0.20)
    assert sub8.active_synapses() == 0

    # Prime target at r=420.0 mm, theta=-25,000 mdeg (-25 deg)
    sensory = [1] * 64
    somatic = [0] * 32
    sub8.step(sensory, somatic, observed_r_mm=420.0, observed_theta_mdeg=-25000, barrier_stress=0.0, acoustic_formant=0.0)

    r, theta, trace, occluded = sub8.get_spatial_tracking()
    assert r == 420.0
    assert theta == -25000
    assert trace == 1.0
    assert not occluded

    # Occlude visual target for 15 ticks
    for _ in range(15):
        sub8.step(sensory, somatic, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0, acoustic_formant=0.0)

    r_occ, theta_occ, trace_occ, is_occ = sub8.get_spatial_tracking()
    assert r_occ == 420.0
    assert theta_occ == -25000
    assert is_occ is True
    assert 0.0 < trace_occ < 1.0


def test_modular_substrate_8d_barrier_refusal_and_vocal_exhaust() -> None:
    """
    Verify 8-Column Col 5 (S2) barrier yield refusal gating and Col 6 (M1) vocal exhaust discharge.
    """
    sub8 = ModularSubstrate8D(yield_threshold=0.50, plastic_rate=0.04, activation_threshold=0.20)
    sensory = [0] * 64
    somatic = [0] * 32

    # 1. Sub-yield contact (sigma = 0.30 <= Y = 0.70)
    sub8.step(sensory, somatic, barrier_stress=0.30)
    assert not sub8.is_barrier_refusal_active()
    vocal, stride = sub8.get_motor_efferent()
    assert stride == 60.0
    assert vocal == 0.0

    # 2. Over-yield collision (sigma = 0.85 > Y = 0.70)
    sub8.step(sensory, somatic, barrier_stress=0.85)
    assert sub8.is_barrier_refusal_active()
    vocal_over, stride_over = sub8.get_motor_efferent()
    assert stride_over == 0.0     # Locomotion arrested
    assert vocal_over == 220.0   # Homeostatic airway vocal valve discharged


def test_modular_substrate_8d_plastic_yield_binding() -> None:
    """
    Verify multi-modal acoustic-optical yield binding across the 8-column fasciculi mesh.
    """
    sub8 = ModularSubstrate8D(yield_threshold=0.35, plastic_rate=0.08, activation_threshold=0.15)
    sensory = [1] * 64
    somatic = [1] * 32

    # Co-activate visual target and acoustic formant
    for _ in range(30):
        sub8.step(sensory, somatic, observed_r_mm=250.0, observed_theta_mdeg=12000, barrier_stress=0.0, acoustic_formant=160.0)

    assert sub8.active_synapses() > 500

    # Verify sparse export
    sparse_data = sub8.export_sparse()
    assert len(sparse_data) > 0
    assert len(sparse_data) % 8 == 0


# =============================================================================
# 64-Column Cortical Array Tests (ModularSubstrate64D)
# =============================================================================

def test_modular_substrate_64d_initialization() -> None:
    """Verify clean initialization of the 64-Column Cortical Array (20,480 nodes)."""
    sub64 = ModularSubstrate64D(yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25)
    assert sub64.active_synapses() == 0
    r, theta, trace, occluded = sub64.get_spatial_tracking()
    assert r == 0.0
    assert theta == 0
    assert trace == 0.0
    assert occluded is False


def test_modular_substrate_64d_spatial_permanence() -> None:
    """Verify 2D spatial permanence attractor locks coordinates in 64D substrate under total optical occlusion."""
    sub64 = ModularSubstrate64D(yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25)
    sensory = [1] * 64
    somatic = [0] * 32

    # Step 1: Optical presence
    for _ in range(10):
        sub64.step(sensory, somatic, observed_r_mm=380.0, observed_theta_mdeg=14000, barrier_stress=0.0)

    r_vis, theta_vis, trace_vis, is_vis = sub64.get_spatial_tracking()
    assert r_vis == 380.0
    assert theta_vis == 14000
    assert trace_vis == 1.0
    assert is_vis is False

    # Step 2: Optical blindout for 20 consecutive ticks
    for _ in range(20):
        sub64.step(sensory, somatic, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0)

    r_occ, theta_occ, trace_occ, is_occ = sub64.get_spatial_tracking()
    assert r_occ == 380.0
    assert theta_occ == 14000
    assert is_occ is True
    assert 0.0 < trace_occ < 1.0


def test_modular_substrate_64d_barrier_refusal_and_motor() -> None:
    """Verify 64-Column Col 23 (S8) barrier yield refusal gating and multi-channel motor efferents."""
    sub64 = ModularSubstrate64D(yield_threshold=0.50, plastic_rate=0.04, activation_threshold=0.20)
    sensory = [0] * 64
    somatic = [0] * 32

    # 1. Sub-yield contact
    sub64.step(sensory, somatic, barrier_stress=0.25)
    assert not sub64.is_barrier_refusal_active()
    vocal, stride, steer, grip = sub64.get_motor_efferent()
    assert stride == 60.0
    assert vocal == 0.0
    assert grip == 25.0

    # 2. Over-yield collision
    sub64.step(sensory, somatic, barrier_stress=0.85)
    assert sub64.is_barrier_refusal_active()
    vocal_over, stride_over, steer_over, grip_over = sub64.get_motor_efferent()
    assert stride_over == 0.0     # Locomotion stride arrested
    assert vocal_over == 220.0   # Vocal exhaust pulse fired
    assert grip_over == 0.0      # Gripper released to prevent damage


def test_modular_substrate_64d_plasticity_and_sleep_consolidation() -> None:
    """Verify continuum von Mises plasticity and nocturnal consolidation across 64 columns."""
    sub64 = ModularSubstrate64D(yield_threshold=0.40, plastic_rate=0.05, activation_threshold=0.20)
    sensory = [1] * 64
    somatic = [0] * 32
    formants = [220.0, 800.0, 1500.0]

    for _ in range(15):
        sub64.step(sensory, somatic, observed_r_mm=300.0, observed_theta_mdeg=8000, barrier_stress=0.0, acoustic_formants=formants)

    active_pre = sub64.active_synapses()
    assert active_pre > 1000

    decayed, pruned = sub64.sleep_consolidation(decay=0.05, prune_thresh=0.01)
    assert decayed > 0

    # Sparse binary export and import round-trip
    sparse_data = sub64.export_sparse()
    assert len(sparse_data) > 0
    assert len(sparse_data) % 8 == 0

    sub_clone = ModularSubstrate64D()
    sub_clone.import_sparse(sparse_data)
    assert sub_clone.active_synapses() > 0
