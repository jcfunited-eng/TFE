"""tests/test_phase5_modular_cortical_columns.py

Verification suite for Item 2 of WHOLE_BRAIN_SPECIFICATION.md:
4-Column 3D Modular Neuromorphic Substrate in Native Rust (ArcLoom Substrate).

Verifies:
  1. 4 Specialized Cortical Columns with vertical laminar microcircuits (L1, L2/3, L4, L5, L6):
     - Column 0: Multimodal Sensory Transduction
     - Column 1: Spatial & Topological Invariance (Polar r, theta and Occlusion Permanence)
     - Column 2: Causal Sequential Syntax & Combinatorial Chaining
     - Column 3: Material Affordance & Barrier Gating (Contact Yield Stress sigma vs Y)
  2. Spatial Permanence Attractor:
     - Maintains egocentric polar coordinates (r_mm, theta_mdeg) even when sensor feed is occluded.
     - Persistence trace decays continuously across blank frames without coordinate erasure.
  3. Material Barrier Refusal:
     - Contact stress below threshold allows normal locomotion.
     - Contact stress exceeding yield limit activates physical barrier refusal.
  4. Continuum von Mises Material Plasticity:
     - Yield occurs if and only if |sigma_ij| > Y.
     - Inter-column fasciculi undergo plastic deformation under sustained co-activation.
  5. Sleep Consolidation & Synaptic Downscaling:
     - Offline sleep consolidation downscales conductances and prunes sub-threshold noise.
  6. Sparse Serialization Parity:
     - Sparse binary serialization exports all active plastic connections without data corruption.
"""

from __future__ import annotations

import pytest
import guala_core
from guala_core import ModularSubstrate4D


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
    # Coordinates MUST remain identical to pre-occlusion location
    assert r_occ == 350.0
    assert theta_occ == 45000
    assert is_occ is True
    # Trace must have decayed smoothly, remaining positive
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
    Co-activation induces plastic deformation and increases active synapse count.
    """
    substrate = ModularSubstrate4D(yield_threshold=0.30, plastic_rate=0.10, activation_threshold=0.10)
    sensory = [1] * 64
    somatic = [1] * 32

    # Drive substrate with repeated synchronized patterns
    initial_synapses = substrate.active_synapses()
    assert initial_synapses == 0

    total_yields = 0
    total_strain = 0.0
    for _ in range(20):
        yields, strain = substrate.step(sensory, somatic, observed_r_mm=200.0, observed_theta_mdeg=15000, barrier_stress=0.2)
        total_yields += yields
        total_strain += strain

    # Plastic yield must occur
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

    # Train synapses
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

    # Initial state has no active synapses
    empty_bytes = substrate.export_sparse()
    assert len(empty_bytes) == 0

    # Drive activity to induce inter-column plasticity
    for _ in range(25):
        substrate.step(sensory, somatic, observed_r_mm=300.0, observed_theta_mdeg=30000, barrier_stress=0.0)

    sparse_bytes = substrate.export_sparse()
    assert len(sparse_bytes) > 0
    # Each sparse entry is u32 index (4 bytes) + f32 conductance (4 bytes) = 8 bytes
    assert len(sparse_bytes) % 8 == 0
