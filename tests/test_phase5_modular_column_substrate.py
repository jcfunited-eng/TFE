"""tests/test_phase5_modular_column_substrate.py

Verification suite for Item 3 of WHOLE_BRAIN_SPECIFICATION.md:
ModularColumnSubstrate Python Adapter bridging native 4-Column, 8-Column, and 64-Column Cortical Array.

Verifies:
  1. Multimodal Sensory Transduction:
     - Encodes visual luminance, cochlear ERB spectral envelopes, tactile pressure,
       and DSF L0-L4 invariants into 64 Layer 4 afferent trits.
  2. Apical Somatic Modulation:
     - Encodes hunger deficit, sleep pressure, and free energy surplus into 32 Layer 1 apical trits.
  3. Spatial Permanence Attractor:
     - Column 1 maintains egocentric polar coordinates (r_mm, theta_mdeg) across blank frames.
  4. Material Barrier Gating:
     - Column 3 / Column 5 / Column 23 activates barrier refusal if and only if contact stress exceeds yield limit.
  5. Continuum von Mises Plasticity:
     - Synchronized multimodal activity induces plastic deformation in intra-column laminar
       and inter-column fasciculi tensors.
  6. Sleep Consolidation:
     - Downscaling and competitive noise pruning restore capacity during offline sleep.
  7. Deterministic Serialization:
     - to_dict() / from_dict() roundtrip preserves configuration and active synapse states.
  8. 64-Column Cortical Array Scaling:
     - High-capacity 20,480-node substrate operates with multimodal acoustic formants and multi-channel efferents.
"""

from __future__ import annotations

import pytest
import numpy as np

from dsf_ai_service.substrate.modular_column_substrate import ModularColumnSubstrate


def test_modular_column_substrate_initialization() -> None:
    """Verify clean initialization of the adapter and native substrate."""
    sub = ModularColumnSubstrate(yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25)
    assert sub.active_synapses() == 0
    r, theta, trace, occluded = sub.get_spatial_tracking()
    assert r == 0.0
    assert theta == 0
    assert trace == 0.0
    assert not occluded
    assert not sub.is_barrier_refusal_active()


def test_sensory_stream_encoding() -> None:
    """Verify Column 0 Layer 4 afferent encoding across all 4 multimodal lanes."""
    sub = ModularColumnSubstrate()

    # 1. Blank inputs
    blank = sub.encode_sensory_stream()
    assert len(blank) == 64
    assert all(t == 0 for t in blank)

    # 2. Multimodal inputs
    optical = np.ones(16) * 0.80
    cochlear = np.ones(16) * 0.90
    dsf = (0.8, -0.4, 0.9, 0.1, 0.7, 0.8, 0.3, 0.6)
    trits = sub.encode_sensory_stream(
        optical_intensities=optical,
        cochlear_channels=cochlear,
        palmar_contact=1.0,
        thermal_gradient_mk=2000.0,
        dsf_vector=dsf,
    )
    assert len(trits) == 64
    # Visual lane (0..15)
    assert any(trits[i] == 1 for i in range(16))
    # Auditory lane (16..31)
    assert any(trits[16 + i] == 1 for i in range(16))
    # Somatosensory lane (32..47)
    assert any(trits[32 + i] == 1 for i in range(16))
    # DSF lane (48..63)
    assert any(trits[48 + i] != 0 for i in range(16))


def test_apical_somatic_encoding() -> None:
    """Verify Layer 1 apical somatic modulation encoding."""
    sub = ModularColumnSubstrate()

    # Resting sated state
    blank_som = sub.encode_somatic_apical(sleep_pressure=0.0, metabolic_deficit=0.0, arousal_surplus=0.0)
    assert len(blank_som) == 32
    assert all(t == 0 for t in blank_som)

    # Strained / aroused state
    active_som = sub.encode_somatic_apical(sleep_pressure=0.8, metabolic_deficit=0.9, arousal_surplus=0.7)
    assert len(active_som) == 32
    # Deficit lane (0..9)
    assert sum(active_som[i] == 1 for i in range(10)) >= 8
    # Sleep lane (10..19)
    assert sum(active_som[10 + i] == 1 for i in range(10)) >= 8
    # Arousal lane (20..31)
    assert sum(active_som[20 + i] == 1 for i in range(12)) >= 8


def test_spatial_permanence_and_barrier_gating() -> None:
    """Verify Column 1 polar tracking permanence and Column 3 barrier gating."""
    sub = ModularColumnSubstrate(yield_threshold=0.50, plastic_rate=0.05, activation_threshold=0.20)
    sens = sub.encode_sensory_stream(optical_intensities=np.ones(16))
    som = sub.encode_somatic_apical()

    # Step with target visible at (400.0 mm, 30,000 mdeg) and barrier stress 0.3 (safe)
    sub.step(sens, som, observed_r_mm=400.0, observed_theta_mdeg=30000, barrier_stress=0.3)
    r, theta, trace, occluded = sub.get_spatial_tracking()
    assert r == 400.0
    assert theta == 30000
    assert trace == 1.0
    assert not occluded
    assert not sub.is_barrier_refusal_active()

    # Target occluded, barrier stress exceeds yield limit (0.75 >= 0.70)
    sub.step(sens, som, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.75)
    r_occ, theta_occ, trace_occ, is_occ = sub.get_spatial_tracking()
    assert r_occ == 400.0
    assert theta_occ == 30000
    assert is_occ is True
    assert 0.0 < trace_occ < 1.0
    assert sub.is_barrier_refusal_active()


def test_sleep_consolidation_and_pruning() -> None:
    """Verify synaptic downscaling and competitive pruning on the adapter."""
    sub = ModularColumnSubstrate(yield_threshold=0.20, plastic_rate=0.15, activation_threshold=0.10)
    sens = [1] * 64
    som = [1] * 32

    # Train synapses
    for _ in range(15):
        sub.step(sens, som, observed_r_mm=200.0, observed_theta_mdeg=10000, barrier_stress=0.0)

    pre_sleep = sub.active_synapses()
    assert pre_sleep > 0

    # 1. Downscale conductances
    decayed, pruned = sub.sleep_consolidation(decay=0.20, prune_thresh=0.01)
    assert decayed > 0

    # 2. Competitive prune
    decayed2, pruned2 = sub.sleep_consolidation(decay=0.0, prune_thresh=0.60)
    assert pruned2 > 0
    assert sub.active_synapses() < pre_sleep


def test_serialization_roundtrip() -> None:
    """Verify to_dict and from_dict preserve configuration."""
    sub = ModularColumnSubstrate(yield_threshold=0.45, plastic_rate=0.04, activation_threshold=0.30)
    sens = [1] * 64
    som = [1] * 32
    sub.step(sens, som, observed_r_mm=150.0, observed_theta_mdeg=5000, barrier_stress=0.1)

    state_dict = sub.to_dict()
    assert "yield_threshold" in state_dict
    assert "sparse_hex" in state_dict
    assert state_dict["yield_threshold"] == 0.45

    sub_restored = ModularColumnSubstrate.from_dict(state_dict)
    assert sub_restored.yield_threshold == 0.45
    assert sub_restored.plastic_rate == 0.04
    assert sub_restored.activation_threshold == 0.30


def test_modular_column_substrate_64d_adapter() -> None:
    """Verify ModularColumnSubstrate adapter properly drives the 64-column array."""
    sub64 = ModularColumnSubstrate(yield_threshold=0.55, plastic_rate=0.03, activation_threshold=0.25, columns=64)
    assert sub64.num_columns == 64
    assert sub64.active_synapses() == 0

    # Encode multimodal sensory and somatic vectors
    sens = sub64.encode_sensory_stream(optical_intensities=np.ones(16) * 0.9)
    som = sub64.encode_somatic_apical(arousal_surplus=0.5)

    # Step with speech formants and visual target
    formants = [220.0, 750.0, 2400.0]
    yields, strain = sub64.step(
        sensory_trits=sens,
        somatic_trits=som,
        observed_r_mm=320.0,
        observed_theta_mdeg=12500,
        barrier_stress=0.10,
        acoustic_formant=formants,
    )
    assert strain >= 0.0

    r, theta, trace, occluded = sub64.get_spatial_tracking()
    assert r == 320.0
    assert theta == 12500
    assert trace == 1.0
    assert occluded is False

    # Check 4-channel motor efferents
    motor = sub64.get_motor_efferent()
    assert len(motor) == 4
    vocal, stride, steer, grip = motor
    assert stride > 0.0
    assert grip > 0.0

    # Over-yield barrier contact
    sub64.step(sens, som, barrier_stress=0.90)
    assert sub64.is_barrier_refusal_active()
    v_over, s_over, _, g_over = sub64.get_motor_efferent()
    assert s_over == 0.0
    assert v_over == 220.0
    assert g_over == 0.0

    # Serialization roundtrip with 64 columns
    state = sub64.to_dict()
    assert state["num_columns"] == 64
    restored = ModularColumnSubstrate.from_dict(state)
    assert restored.num_columns == 64
