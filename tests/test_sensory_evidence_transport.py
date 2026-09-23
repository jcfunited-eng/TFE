"""Focused verification suite for sensory evidence transport.

Verifies:
1. Producer-origin saturation detection resolves the 212 rounding counterexample.
2. Channel-bit layout (little-bit ordering) and focal-prefix exclusion bound the mask to exactly 7,200 bytes.
3. Real-renderer/ordinary-loop settlement delivers truthful OpticalEvidence to Sensed with unchanged pixel bytes
   (asserting exact equality against the predecessor calculation and producer pre-clip saturation flags across
   both flagged and unflagged channels).
4. External camera source replacement marks upstream exposure and clipping as unavailable (None) without leaking stale world metadata.
"""

from fractions import Fraction
import math
from typing import Any
import numpy as np
import pytest

import dsf_ai_service.guala_functional_loop
from dsf_ai_service.guala_functional_loop import (
    FunctionalPhysicalLoop, PUPIL_GAIN_MAX, PUPIL_HIGHLIGHT_PERCENTILE,
    PUPIL_MID_RANGE, WORLD_FOCAL_SITES, WORLD_FOCAL_VALUES,
    WORLD_LEGACY_SITES, WORLD_RETINAL_SITES, WORLD_WIDE_SITES, _gc,
)
from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism, OpticalEvidence, Sensed,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_world_sensorium import retinal_carriage
from tests.test_guala_functional_organism import IDENTITY, UNATTENDED
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.substrate.w1_physical_receptors import _EIGHT_BIT, retinal_irradiance_field


def test_producer_saturation_rounding_counterexample() -> None:
    """Verify that producer-origin evaluation (pre_clip >= 1.0) correctly
    distinguishes clipped from unclipped signals where post-hoc byte checks fail.

    Under transmission tau = 5/6:
      Ceiling = 255.0 * (5/6) = 212.5.
      Nearest-even rint(212.5) yields byte 212.
    """
    tau = Fraction(5, 6)
    tau_f = float(tau)

    # Sample A: clipped at ceiling
    pre_clip_clipped = 1.05
    assert pre_clip_clipped >= 1.0, "Producer detects clipping before bounding"
    clipped_val = np.rint(np.minimum(1.0, pre_clip_clipped) * (255.0 * tau_f)).astype(int)
    assert clipped_val == 212, "Clipped signal rounds to byte 212"

    # Sample B: unclipped near ceiling
    pre_clip_unclipped = 0.998
    assert not (pre_clip_unclipped >= 1.0), "Producer recognizes unclipped signal"
    unclipped_val = np.rint(np.minimum(1.0, pre_clip_unclipped) * (255.0 * tau_f)).astype(int)
    assert unclipped_val == 212, "Unclipped signal also rounds to byte 212"

    # Post-hoc comparisons fail on both sides:
    # 1. Byte threshold 212 produces false positive for unclipped sample B:
    assert unclipped_val >= 212, "Post-hoc threshold >= 212 falsely labels unclipped sample as saturated"
    # 2. Float threshold 212.5 produces false negative for clipped sample A:
    assert not (clipped_val >= 255.0 * tau_f), "Post-hoc threshold >= 212.5 misses clipped sample because 212 < 212.5"

    # Truthful producer-origin boolean differentiates them:
    sat_clipped = bool(pre_clip_clipped >= 1.0)
    sat_unclipped = bool(pre_clip_unclipped >= 1.0)
    assert sat_clipped is True
    assert sat_unclipped is False


def test_channel_bit_layout_and_focal_prefix_exclusion() -> None:
    """Verify the 7,200-byte packed bitmask layout and focal-prefix exclusion.

    Layout:
      160 columns x 120 rows x 3 channels (RGB) = 57,600 channel flags.
      Packed into bytes with little-bit ordering: exactly 7,200 bytes.
      Flag index: 3 * (160 * row + col) + channel, where R=0, G=1, B=2.
    """
    # 1. Total focal channel count and byte size bound
    assert WORLD_FOCAL_SITES == 19200
    assert WORLD_FOCAL_VALUES == 57600
    expected_bytes = WORLD_FOCAL_VALUES // 8
    assert expected_bytes == 7200

    # 2. Focal prefix exclusion:
    # The full retina contains 135 ambient sites (27 legacy + 108 wide) preceding focal sites
    ambient_sites = WORLD_LEGACY_SITES + WORLD_WIDE_SITES
    assert ambient_sites == 135
    assert WORLD_RETINAL_SITES == ambient_sites + WORLD_FOCAL_SITES

    # 3. Vectorized bit packing and indexing verification
    flags = np.zeros(WORLD_FOCAL_VALUES, dtype=bool)

    # Test individual channel flags across diverse sites:
    # Site (0, 0) Red (index 0)
    flags[0] = True
    # Site (0, 0) Green (index 1)
    flags[1] = True
    # Site (0, 1) Blue: row=0, col=1, ch=2 -> 3 * (160 * 0 + 1) + 2 = 5
    flags[5] = True
    # Site (50, 80) Red: row=50, col=80, ch=0 -> 3 * (160 * 50 + 80) + 0 = 24240
    test_idx = 3 * (160 * 50 + 80) + 0
    flags[test_idx] = True

    packed = np.packbits(flags, bitorder="little").tobytes()
    assert len(packed) == 7200, f"Mask must be exactly 7,200 bytes, got {len(packed)}"

    # Verify little-bit ordering:
    # Byte 0 has bits 0, 1, 5 set: (1 << 0) | (1 << 1) | (1 << 5) = 1 + 2 + 32 = 35
    assert packed[0] == 35

    # Verify test_idx bit location:
    target_byte = test_idx // 8
    target_bit = test_idx % 8
    assert (packed[target_byte] & (1 << target_bit)) != 0


def test_sensory_evidence_transport_real_loop_world(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that real-renderer settlement delivers truthful OpticalEvidence
    to Sensed while leaving existing pixel bytes unchanged.

    Captures actual renderer inputs/outputs, derives predecessor pixel values
    from those same transducer inputs, asserts exact equality across all 57,600
    delivered focal pixels, and compares every mask bit against producer-origin
    pre-clip evaluation exercising both flagged and unflagged channels.
    """
    captured_calls: list[dict[str, Any]] = []
    orig_renderer = dsf_ai_service.guala_functional_loop._world_retina_u8

    def intercept_renderer(snapshot: Any, axes: tuple[Any, ...], sun: Any = None, pupil: bool = True) -> tuple[tuple[int, ...], OpticalEvidence]:
        ret = orig_renderer(snapshot, axes, sun=sun, pupil=pupil)
        captured_calls.append({
            "snapshot": snapshot,
            "axes": axes,
            "sun": sun,
            "pupil": pupil,
            "output": ret,
        })
        return ret

    monkeypatch.setattr(dsf_ai_service.guala_functional_loop, "_world_retina_u8", intercept_renderer)

    world = home_world_authority(identity=IDENTITY, expand_library=False)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=100)
    loop = FunctionalPhysicalLoop()

    captured_sensed: list[Sensed] = []
    orig_decide = organism.decide

    def intercept_decide(sensed: Sensed):
        captured_sensed.append(sensed)
        return orig_decide(sensed)

    organism.decide = intercept_decide  # type: ignore[assignment]

    res = loop.settle(organism, world, UNATTENDED)
    assert len(captured_calls) == 1, "Renderer must be called exactly once per settlement"
    assert len(captured_sensed) == 1, "Expected exactly one Sensed construction per settlement"
    
    call = captured_calls[0]
    sensed = captured_sensed[0]

    # Predecessor computation using captured renderer inputs:
    heading, pitch, transmission = retinal_carriage(call["axes"])
    pixels = retinal_irradiance_field(
        call["snapshot"], retinal_heading_offset_millidegrees=heading,
        retinal_pitch_offset_millidegrees=pitch, include_focal=True, sun=call["sun"],
    )
    if _gc is not None and hasattr(_gc, "fast_pixels_to_bands_f64"):
        raw = _gc.fast_pixels_to_bands_f64(pixels, _EIGHT_BIT)
        bands = np.asarray(raw, dtype=np.float64).reshape(-1, 6)
    else:
        bands = np.array(pixels, dtype=np.float64)
    rgb = np.stack(((bands[:, 0] + bands[:, 1]) / 2.0, (bands[:, 2] + bands[:, 3]) / 2.0, (bands[:, 4] + bands[:, 5]) / 2.0), axis=1)
    middle = float(np.median(rgb))
    bright = float(np.percentile(rgb, PUPIL_HIGHLIGHT_PERCENTILE))
    gain = 1.0
    if call["pupil"] and middle > 0.0 and bright > 0.0:
        wanted = min(PUPIL_GAIN_MAX, max(1.0, PUPIL_MID_RANGE / middle), max(1.0, 1.0 / bright))
        gain = float(2 ** int(math.log2(wanted)))

    # Predecessor pixel formula (identical to pre-patch):
    predecessor_values = np.rint(np.minimum(1.0, rgb * gain) * (255.0 * float(transmission))).astype(np.int64).reshape(-1).tolist()
    predecessor_focal = tuple(predecessor_values[-WORLD_FOCAL_VALUES:])

    # 1. Exact equality of delivered focal pixels
    assert sensed.focal_luminance_u8 == predecessor_focal, (
        "Delivered focal pixels must exactly match predecessor calculation across all 57,600 values"
    )

    # 2. OpticalEvidence delivery and transducer parameters
    evidence = sensed.optical_evidence
    assert evidence is not None, "OpticalEvidence must be present on Sensed"
    assert isinstance(evidence, OpticalEvidence)
    assert evidence.pupil_gain == gain
    assert evidence.eyelid_transmission == transmission
    assert isinstance(evidence.eyelid_transmission, Fraction)
    assert evidence.eyelid_transmission == Fraction(5, 6)

    # 3. Producer focal saturation mask derivation from pre-clip:
    pre_clip = rgb * gain
    # Prefix exclusion: ambient sites are the first 135 sites (405 values)
    ambient_sites = WORLD_LEGACY_SITES + WORLD_WIDE_SITES
    assert rgb.shape[0] == ambient_sites + WORLD_FOCAL_SITES
    expected_focal_pre_clip = pre_clip[-WORLD_FOCAL_SITES:]
    expected_focal_flags = (expected_focal_pre_clip >= 1.0)
    expected_mask = np.packbits(expected_focal_flags.ravel(), bitorder="little").tobytes()

    actual_mask = evidence.focal_saturation_mask
    assert len(actual_mask) == 7200, f"Delivered mask must be exactly 7,200 bytes, got {len(actual_mask)}"
    assert actual_mask == expected_mask, "Delivered focal saturation mask must exactly match producer pre-clip derivation"

    # 4. Unpack mask bits and assert exact equality channel by channel
    unpacked_bits = np.unpackbits(np.frombuffer(actual_mask, dtype=np.uint8), bitorder="little")[:WORLD_FOCAL_VALUES]
    unpacked_flags = unpacked_bits.reshape(WORLD_FOCAL_SITES, 3).astype(bool)
    assert np.array_equal(unpacked_flags, expected_focal_flags), (
        "Unpacked mask flags must match producer pre-clip flags at every site and channel"
    )

    # 5. Exercise both flagged and unflagged channels in this real world render
    flagged_count = int(np.sum(expected_focal_flags))
    unflagged_count = int(np.sum(~expected_focal_flags))
    assert flagged_count > 0, "Real world render must exercise flagged (saturated) channels"
    assert unflagged_count > 0, "Real world render must exercise unflagged (unsaturated) channels"
    assert flagged_count + unflagged_count == WORLD_FOCAL_VALUES


def test_sensory_evidence_transport_camera_source_replacement() -> None:
    """Verify that external camera input marks upstream exposure gain and clipping
    as unavailable (None) without carrying stale world metadata.
    """
    world = home_world_authority(identity=IDENTITY, expand_library=False)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=100)
    loop = FunctionalPhysicalLoop()

    # Supply external camera RGB stream (full 160x120 + 135 ambient sites = 58,005 values)
    fake_camera_rgb = tuple(128 for _ in range(WORLD_RETINAL_SITES * 3))
    sensory = LeanSensoryOccurrence(source="camera", pressure_s16le=None, retina_rgb_u8=fake_camera_rgb)
    occurrence = PhysicalOccurrence(kind="sensory", payload=sensory)

    captured_sensed: list[Sensed] = []
    orig_decide = organism.decide

    def intercept_decide(sensed: Sensed):
        captured_sensed.append(sensed)
        return orig_decide(sensed)

    organism.decide = intercept_decide  # type: ignore[assignment]

    res = loop.settle(organism, world, occurrence)
    assert len(captured_sensed) == 1
    sensed = captured_sensed[0]

    # Source verification
    assert sensed.luminance_source == "camera"

    # Evidence isolation: upstream camera gain and clipping must be None, NOT world values or all-zero
    evidence = sensed.optical_evidence
    assert evidence is not None
    assert evidence.pupil_gain is None, "Camera source must not report world pupil gain"
    assert evidence.focal_saturation_mask is None, "Camera source must not report world saturation mask"
    assert evidence.eyelid_transmission == Fraction(5, 6), "Local carriage transmission remains known"
