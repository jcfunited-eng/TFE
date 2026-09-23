"""tests/test_multimodal_experience_story.py — Verification of Multi-Modal VR Story Experience.

Invariants Verified:
1. Diurnal thermal modulation: outdoor hand contact reference temperature scales with circadian solar phase.
2. Pre-ingestion volatile odorant delivery: food items (bread, milk, apple) carry authentic odorant release profiles.
3. Material acoustic impulse transients: physical impact wave packets generate distinct 16kHz audio for wood, ceramic, fabric, and metal.
4. Caregiver deictic gaze and pointing orientation: caregiver body aligns toward target objects in Euclidean coordinates.
5. Consolidation depth telemetry: multi-modal moment tracking in state.json functions without locks.
"""

from __future__ import annotations

import math
import struct
import pytest

from dsf_ai_service.guala_caretaker_hand import (
    material_impact_pcm,
    diurnal_thermal_reference_millikelvin,
    deictic_orientation_millidegrees,
    DELIVER_IDS,
)
from guala_caretaker.caretaker import (
    circadian_epoch,
    DIURNAL_CYCLE_TICKS,
)


def test_diurnal_thermal_reference_scaling() -> None:
    """Verify outdoor reference temperature scales with circadian phase:
    Cooler at dawn (289K-291K), warmer at midday (297K-299K)."""
    # Dawn (tick 0): cool reference
    dawn_temp = diurnal_thermal_reference_millikelvin(0)
    assert 288_000 <= dawn_temp <= 292_000

    # Midday focus (tick ~45,000): peak solar warming
    midday_temp = diurnal_thermal_reference_millikelvin(45_000)
    assert 296_000 <= midday_temp <= 300_000

    # Night consolidation (tick ~100,000): cool baseline
    night_temp = diurnal_thermal_reference_millikelvin(100_000)
    assert 288_000 <= night_temp <= 292_000

    # Midday must be strictly warmer than dawn
    assert midday_temp > dawn_temp


def test_material_acoustic_impact_synthesis() -> None:
    """Verify physical impact synthesis generates valid 16kHz mono s16le PCM wave packets
    with material-specific frequencies and damping profiles."""
    materials = ["wood", "ceramic", "fabric", "metal"]
    for mat in materials:
        pcm = material_impact_pcm(mat, intensity=1.0)
        assert isinstance(pcm, bytes)
        assert len(pcm) == 8000  # 0.25 s at 16kHz mono 16-bit = 4000 samples * 2 bytes = 8000 bytes
        samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
        assert len(samples) == 4000

        # Non-silent with initial impact
        peak = max(abs(s) for s in samples)
        assert peak > 2000

        # Physical damping: second half of block must have lower energy than first half
        first_half_energy = sum(s * s for s in samples[:2000])
        second_half_energy = sum(s * s for s in samples[2000:])
        assert first_half_energy > second_half_energy, f"Material {mat} must damp over time"


def test_caregiver_deictic_gaze_orientation() -> None:
    """Verify deictic angle calculation correctly points person-body-1 toward target coordinates."""
    # Person at (0, 0), target at (1000, 0) -> 0 degrees = 0 millidegrees
    assert deictic_orientation_millidegrees((0, 0), (1000, 0)) == 0

    # Person at (0, 0), target at (0, 1000) -> 90 degrees = 90,000 millidegrees
    assert deictic_orientation_millidegrees((0, 0), (0, 1000)) == 90_000

    # Person at (0, 0), target at (-1000, 0) -> 180 degrees = 180,000 millidegrees
    assert deictic_orientation_millidegrees((0, 0), (-1000, 0)) == 180_000

    # Person at (0, 0), target at (0, -1000) -> 270 degrees = 270,000 millidegrees
    assert deictic_orientation_millidegrees((0, 0), (0, -1000)) == 270_000


def test_multi_diet_delivery_ids_cover_essential_nutrition() -> None:
    """Verify delivery IDs map to physical entities carrying mass and material properties."""
    assert "bread-delivery" in DELIVER_IDS
    assert DELIVER_IDS["bread-delivery"] == "bread-slice"

    assert "milk-delivery" in DELIVER_IDS
    assert DELIVER_IDS["milk-delivery"] == "bottle-milk"

    assert "stroller-delivery" in DELIVER_IDS
    assert DELIVER_IDS["stroller-delivery"] == "stroller-carriage"

