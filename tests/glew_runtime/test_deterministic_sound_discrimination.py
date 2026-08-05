"""Real-audio conformance tests for deterministic sound discrimination.

Every fixture here drives the REAL cochlear filterbank
(GL_MDL_AUDITORY_CORTEX_WC_20260608_01.cochlear_transduce) against a real
synthetic audio buffer -- a pure low-frequency tone / low harmonic stack for
voiced-like input, a high-frequency tone for unvoiced-like input, scattered
high-band noise for a genuinely ambiguous input, and a zero buffer for
silence. No fabricated feature vector ever bypasses the real transduction.

The discriminations are then decided by the real certified interval-dominance
recognizer (expression_modes.evaluate_expression_mode_boundary), never a
bespoke if/else, and every result's provenance receipt is checked to fail
closed when the cited real band data is tampered.
"""

from __future__ import annotations

import math
from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01 import (
    cochlear_transduce,
)
from dsf_ai_service.glew_runtime.auditory_fragment_receipt import (
    AUDITORY_BAND_ORDER,
    auditory_fragment_receipt,
)
from dsf_ai_service.glew_runtime.deterministic_sound_discrimination import (
    EXPRESSION_RECOGNITION_OPERATOR_ID,
    HIGH_BANDS,
    LOW_BANDS,
    SoundPresence,
    Voicing,
    build_auditory_fragment_receipt_from_cochlear,
    discriminate_sound,
    discriminate_sound_presence,
    discriminate_voicing,
)
from dsf_ai_service.glew_runtime.expression_modes import (
    ExpressionRecognitionStatus,
)
from dsf_ai_service.glew_runtime.model import ReceiptError


SR = 200


def _t(duration_s: float) -> np.ndarray:
    return np.arange(int(duration_s * SR)) / SR


def _harmonic(f0: float, amps: list[float], duration_s: float = 2.0) -> np.ndarray:
    t = _t(duration_s)
    signal = np.zeros_like(t)
    for harmonic_index, amp in enumerate(amps, 1):
        signal += amp * np.sin(2 * math.pi * f0 * harmonic_index * t)
    return signal


def _sine(freq: float, duration_s: float = 2.0) -> np.ndarray:
    return np.sin(2 * math.pi * freq * _t(duration_s))


def _hp_noise(
    center: float, bandwidth: float, seed: int, n: int = 12, duration_s: float = 2.0
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = _t(duration_s)
    signal = np.zeros_like(t)
    for _ in range(n):
        freq = center + rng.standard_normal() * bandwidth
        phase = rng.uniform(0, 2 * math.pi)
        signal += np.sin(2 * math.pi * freq * t + phase)
    return signal


def _receipt_from_buffer(buffer: np.ndarray, *, source_id: str = "test-mic"):
    cochlear = cochlear_transduce(buffer, SR)
    return build_auditory_fragment_receipt_from_cochlear(
        cochlear,
        source_id=source_id,
        born_tick=0,
        sample_rate_hz=SR,
        input_sample_count=len(buffer),
    )


# Real synthetic audio buffers (deterministic; validated against the real
# transducer). Voiced-like inputs concentrate coherent winding in the low
# bands; the high tone concentrates it high; the scattered / all-quiet noise
# buffers are honestly ambiguous.
SILENCE = np.zeros(400)
VOICED_HARMONIC = _harmonic(8, [0.8, 0.4, 0.2])
VOICED_SINE = _sine(10)
UNVOICED_SINE = _sine(88)
SCATTERED_NOISE = _hp_noise(80, 25, seed=9)
PRESENT_ZERO_WINDING_NOISE = _hp_noise(85, 18, seed=2)


# ---------------------------------------------------------------------------
# Discrimination 1: silence vs. presence (exact zero-event boundary).
# ---------------------------------------------------------------------------


def test_silence_is_detected_as_exactly_zero_events():
    receipt = _receipt_from_buffer(SILENCE)
    presence = discriminate_sound_presence(receipt)

    assert presence.status is SoundPresence.SILENCE
    assert presence.total_n_events == 0
    assert presence.per_band_n_events == (0,) * len(AUDITORY_BAND_ORDER)
    presence.verify(receipt)


def test_silence_carries_no_voicing_subresult():
    receipt = _receipt_from_buffer(SILENCE)
    result = discriminate_sound(receipt)

    assert result.presence.status is SoundPresence.SILENCE
    assert result.voicing is None
    result.verify(receipt)


def test_real_speech_like_buffer_is_present():
    receipt = _receipt_from_buffer(VOICED_HARMONIC)
    presence = discriminate_sound_presence(receipt)

    assert presence.status is SoundPresence.SPEECH_PRESENT
    assert presence.total_n_events > 0
    presence.verify(receipt)


# ---------------------------------------------------------------------------
# Discrimination 2: voiced vs. unvoiced (certified recognizer).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("buffer", [VOICED_HARMONIC, VOICED_SINE])
def test_low_frequency_periodic_input_is_voiced(buffer):
    receipt = _receipt_from_buffer(buffer)
    voicing = discriminate_voicing(receipt)

    assert voicing.status is Voicing.VOICED
    assert voicing.recognition_status == ExpressionRecognitionStatus.RECOGNIZED.value
    assert voicing.winner_mode_index == 0
    # Coherent low-band periodicity genuinely exceeds high-band winding.
    assert voicing.low_band_winding_magnitude_sum > voicing.high_band_winding_magnitude_sum
    voicing.verify(receipt)


def test_high_frequency_input_is_unvoiced():
    receipt = _receipt_from_buffer(UNVOICED_SINE)
    voicing = discriminate_voicing(receipt)

    assert voicing.status is Voicing.UNVOICED
    assert voicing.recognition_status == ExpressionRecognitionStatus.RECOGNIZED.value
    assert voicing.winner_mode_index == 1
    assert voicing.high_band_winding_magnitude_sum > voicing.low_band_winding_magnitude_sum
    voicing.verify(receipt)


def test_scattered_noise_is_honestly_ambiguous_not_forced():
    receipt = _receipt_from_buffer(SCATTERED_NOISE)
    voicing = discriminate_voicing(receipt)

    assert voicing.status is Voicing.AMBIGUOUS
    # A real, non-committal recognizer outcome, never RECOGNIZED.
    assert voicing.recognition_status != ExpressionRecognitionStatus.RECOGNIZED.value
    assert voicing.recognition_status in {
        ExpressionRecognitionStatus.NOVEL_SILENCE.value,
        ExpressionRecognitionStatus.AMBIGUOUS_SILENCE.value,
        ExpressionRecognitionStatus.BOOTSTRAP_SILENCE.value,
        ExpressionRecognitionStatus.UNKNOWN.value,
    }
    assert voicing.winner_mode_index is None
    voicing.verify(receipt)


def test_present_but_zero_coherent_winding_is_ambiguous_without_running_recognizer():
    receipt = _receipt_from_buffer(PRESENT_ZERO_WINDING_NOISE)
    presence = discriminate_sound_presence(receipt)
    voicing = discriminate_voicing(receipt)

    # Real capture: events present (so not silence) but every band's net
    # winding is exactly zero -> no certified-positive field energy -> the
    # recognizer is honestly not run, and the result is AMBIGUOUS.
    assert presence.status is SoundPresence.SPEECH_PRESENT
    assert sum(voicing.per_band_winding_magnitude) == 0
    assert voicing.status is Voicing.AMBIGUOUS
    assert voicing.recognition_status == "not_evaluated_zero_coherent_winding"
    assert voicing.winner_mode_index is None
    assert voicing.recognition_receipt_sha256 is None
    voicing.verify(receipt)


# ---------------------------------------------------------------------------
# The decision really is the shared certified mechanism.
# ---------------------------------------------------------------------------


def test_voicing_is_decided_by_the_real_certified_recognizer():
    receipt = _receipt_from_buffer(VOICED_HARMONIC)
    voicing = discriminate_voicing(receipt)

    payload = voicing.receipt_payload.decode()
    assert EXPRESSION_RECOGNITION_OPERATOR_ID in payload
    assert (
        "one_lower_bound_strictly_exceeds_every_other_upper_bound" in payload
    )
    # A recognized case cites the recognizer's own certified result receipt.
    assert voicing.recognition_receipt_sha256 is not None
    assert len(voicing.recognition_receipt_sha256) == 64


def test_low_high_split_covers_the_exact_mounted_band_order():
    assert LOW_BANDS + HIGH_BANDS == AUDITORY_BAND_ORDER
    assert LOW_BANDS == ("very_low", "low", "low_mid")
    assert HIGH_BANDS == ("mid", "mid_high", "high")


# ---------------------------------------------------------------------------
# Provenance: receipts verify, and fail closed on tamper.
# ---------------------------------------------------------------------------


def test_full_result_receipt_verifies_and_binds_the_cited_fragment():
    receipt = _receipt_from_buffer(VOICED_HARMONIC)
    result = discriminate_sound(receipt)

    result.verify(receipt)
    assert result.fragment_receipt_sha256 == receipt.receipt_sha256
    assert result.presence.fragment_receipt_sha256 == receipt.receipt_sha256
    assert result.voicing is not None
    assert result.voicing.fragment_receipt_sha256 == receipt.receipt_sha256


def _tamper_one_band(receipt):
    """Return a genuinely different, still self-consistent fragment receipt by
    adding one real winding-transition event to the 'mid' band."""

    bands = {
        band: {
            "winding": receipt.fragment.bands[band]["winding"],
            "n_events": receipt.fragment.bands[band]["n_events"],
            "events": list(receipt.fragment.bands[band]["events"]),
        }
        for band in AUDITORY_BAND_ORDER
    }
    events = bands["mid"]["events"]
    last_t = events[-1]["t"] if events else 0.0
    events.append({"t": last_t + 0.04, "dw": 1, "s": 0.5})
    bands["mid"]["winding"] = int(bands["mid"]["winding"]) + 1
    bands["mid"]["n_events"] = int(bands["mid"]["n_events"]) + 1
    tampered_fragment = replace(receipt.fragment, bands=bands)
    return auditory_fragment_receipt(tampered_fragment)


def test_tampered_band_data_fails_closed():
    receipt = _receipt_from_buffer(VOICED_HARMONIC)
    result = discriminate_sound(receipt)

    tampered = _tamper_one_band(receipt)
    # The tampered receipt is itself internally valid but is a different
    # fragment; the result is bound to the exact original it cited.
    assert tampered.receipt_sha256 != receipt.receipt_sha256
    tampered.verify()  # internally consistent -> valid on its own
    with pytest.raises(ReceiptError, match="different auditory fragment receipt"):
        result.verify(tampered)
    with pytest.raises(ReceiptError, match="different auditory fragment receipt"):
        result.presence.verify(tampered)
    with pytest.raises(ReceiptError, match="different auditory fragment receipt"):
        result.voicing.verify(tampered)


def test_tampered_fragment_receipt_digest_fails_closed():
    receipt = _receipt_from_buffer(VOICED_HARMONIC)
    forged = replace(receipt, receipt_sha256="0" * 64)

    # Any entry point re-authenticates the fragment and fails closed.
    with pytest.raises(ReceiptError, match="tampered"):
        discriminate_sound_presence(forged)
    with pytest.raises(ReceiptError, match="tampered"):
        discriminate_voicing(forged)
    with pytest.raises(ReceiptError, match="tampered"):
        discriminate_sound(forged)


def test_tampered_result_payload_fails_closed():
    receipt = _receipt_from_buffer(UNVOICED_SINE)
    voicing = discriminate_voicing(receipt)

    # Flip the stored verdict without recomputing the bound payload digest.
    forged = replace(voicing, status=Voicing.VOICED)
    with pytest.raises(ReceiptError):
        forged.verify(receipt)

    presence = discriminate_sound_presence(receipt)
    forged_presence = replace(presence, total_n_events=presence.total_n_events + 1)
    with pytest.raises(ReceiptError):
        forged_presence.verify(receipt)


def test_non_receipt_input_fails_closed():
    with pytest.raises(ReceiptError, match="typed AuditoryFragmentReceipt"):
        discriminate_sound(None)  # type: ignore[arg-type]
    with pytest.raises(ReceiptError, match="typed AuditoryFragmentReceipt"):
        discriminate_voicing(object())  # type: ignore[arg-type]


def test_convenience_builder_rejects_wrong_band_set():
    with pytest.raises(ReceiptError, match="exact mounted six-band set"):
        build_auditory_fragment_receipt_from_cochlear(
            {"only_one_band": {"winding": 0, "n_events": 0, "events": []}},
            source_id="x",
            born_tick=0,
            sample_rate_hz=SR,
            input_sample_count=10,
        )
