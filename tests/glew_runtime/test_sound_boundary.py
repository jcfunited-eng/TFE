from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.auditory_fragment_receipt import (
    AUDITORY_BAND_ORDER,
    AuditoryFragmentReceipt,
    AuditoryPerceptFragment,
    auditory_fragment_receipt,
    auditory_fragment_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.sound_boundary import (
    AUDITORY_PORT_ID,
    AuditoryBoundaryTranslationStatus,
    translate_auditory_fragment_to_boundary_observation,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    mount_packaged_production_story_chemistry,
)


RUNTIME_KEY = b"test process only: injected production-profile runtime secret"
RUNTIME_KEY_ID = "test-production-story-runtime-key"


def _silent_bands() -> dict:
    return {
        band_name: {"winding": 0, "n_events": 0, "events": []}
        for band_name in AUDITORY_BAND_ORDER
    }


def _bands_from(winding_and_events: dict) -> dict:
    """Build a full six-band mapping; bands not named in
    winding_and_events default to a real, silent (zero-event) band."""
    bands = _silent_bands()
    bands.update(winding_and_events)
    return bands


def _events_for(directions: list[int], start_t: float = 0.04, dt: float = 0.04) -> list[dict]:
    events = []
    t = start_t
    for i, dw in enumerate(directions):
        events.append({"t": round(t, 6), "dw": dw, "s": 0.5 if dw > 0 else -0.5})
        t += dt
    return events


def _fragment(
    *,
    source_id: str = "mic:live",
    born_tick: int = 100,
    sample_rate_hz: int = 200,
    input_sample_count: int = 128,
    bands: dict | None = None,
) -> AuditoryPerceptFragment:
    return AuditoryPerceptFragment(
        source_id=source_id,
        born_tick=born_tick,
        sample_rate_hz=sample_rate_hz,
        input_sample_count=input_sample_count,
        bands=bands if bands is not None else _silent_bands(),
    )


def _mounted_manifest():
    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=RUNTIME_KEY,
        runtime_key_id=RUNTIME_KEY_ID,
    )
    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    return mounted.runtime.manifest


# --------------------------------------------------------------------------
# AuditoryFragmentReceipt: construction, round-trip, and tamper detection
# --------------------------------------------------------------------------


def test_receipt_construction_round_trips_and_verifies():
    bands = _bands_from(
        {
            "mid": {
                "winding": 3,
                "n_events": 5,
                "events": _events_for([1, 1, 1, -1, 1]),
            },
            "high": {
                "winding": -1,
                "n_events": 1,
                "events": _events_for([-1]),
            },
        }
    )
    fragment = _fragment(bands=bands)
    receipt = auditory_fragment_receipt(fragment)

    assert isinstance(receipt, AuditoryFragmentReceipt)
    assert receipt.fragment is fragment
    assert receipt.receipt_payload == auditory_fragment_receipt_payload(fragment)
    # Self-labeling: this receipt claims no DSF/GLEW semantic authority,
    # mirroring the sight fragment receipt's honest "unknown" self-label.
    decoded = json.loads(receipt.receipt_payload)
    assert decoded["dsf"] == {
        "status": "unknown",
        "reason": "native_auditory_fragment_has_no_ratified_full_field_operator",
    }
    receipt.verify()  # must not raise


def test_receipt_construction_rejects_a_winding_events_mismatch():
    bands = _bands_from(
        {
            "mid": {
                # winding says +3 but the real events only sum to +1 --
                # the two must be internally consistent at construction.
                "winding": 3,
                "n_events": 3,
                "events": _events_for([1, -1, 1]),
            },
        }
    )
    fragment = _fragment(bands=bands)
    with pytest.raises(ReceiptError):
        auditory_fragment_receipt(fragment)


def test_receipt_construction_rejects_n_events_count_mismatch():
    bands = _bands_from(
        {
            "mid": {
                "winding": 2,
                "n_events": 5,  # declared 5 but only 2 real events supplied
                "events": _events_for([1, 1]),
            },
        }
    )
    fragment = _fragment(bands=bands)
    with pytest.raises(ReceiptError):
        auditory_fragment_receipt(fragment)


def test_receipt_construction_rejects_missing_band():
    incomplete_bands = _silent_bands()
    del incomplete_bands["high"]
    fragment = _fragment(bands=incomplete_bands)
    with pytest.raises(ReceiptError):
        auditory_fragment_receipt(fragment)


def test_receipt_tamper_on_payload_bytes_is_detected():
    fragment = _fragment()
    receipt = auditory_fragment_receipt(fragment)
    tampered = replace(receipt, receipt_payload=receipt.receipt_payload + b" ")
    with pytest.raises(ReceiptError):
        tampered.verify()


def test_receipt_tamper_on_digest_is_detected():
    fragment = _fragment()
    receipt = auditory_fragment_receipt(fragment)
    flipped = ("0" if receipt.receipt_sha256[0] != "0" else "1") + receipt.receipt_sha256[1:]
    tampered = replace(receipt, receipt_sha256=flipped)
    with pytest.raises(ReceiptError):
        tampered.verify()


# --------------------------------------------------------------------------
# Translation: a real, valid capture produces a verifying observation
# --------------------------------------------------------------------------


def test_valid_capture_translates_to_a_self_verifying_boundary_observation():
    manifest = _mounted_manifest()
    bands = _bands_from(
        {
            "mid": {
                "winding": 3,
                "n_events": 5,
                "events": _events_for([1, 1, 1, -1, 1]),
            },
            "high": {
                "winding": -1,
                "n_events": 1,
                "events": _events_for([-1]),
            },
        }
    )
    fragment = _fragment(bands=bands)
    receipt = auditory_fragment_receipt(fragment)

    result = translate_auditory_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="sound-event-1",
        observation_id="sound-event-1:story-auditory.native-port-0:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is AuditoryBoundaryTranslationStatus.OBSERVED
    assert result.observation is not None
    observation = result.observation
    observation.verify()  # must not raise

    port = manifest.port(AUDITORY_PORT_ID)
    assert observation.port_id == AUDITORY_PORT_ID
    assert observation.native_flux_unit == port.native_signal_unit

    # total winding = 3 + (-1) = 2; total events = 5 + 1 = 6
    assert observation.signed_native_flux == Fraction(2, 6)
    assert Fraction(-1) <= observation.signed_native_flux <= Fraction(1)

    # Provenance traces back to this exact auditory fragment receipt.
    assert observation.provenance_receipt_sha256 == receipt.receipt_sha256
    assert observation.provenance_receipt_payload == receipt.receipt_payload


def test_flux_never_derived_from_language_only_from_band_counts():
    """Two fragments with identical bands but wildly different, irrelevant
    metadata (source_id standing in for anything a word/transcription path
    might vary) must produce the identical flux -- proving the value comes
    only from the per-band winding/n_events data."""
    manifest = _mounted_manifest()
    bands = _bands_from(
        {
            "low": {"winding": 2, "n_events": 4, "events": _events_for([1, 1, -1, 1])},
        }
    )
    receipt_a = auditory_fragment_receipt(_fragment(source_id="mic:live", bands=bands))
    receipt_b = auditory_fragment_receipt(
        _fragment(source_id="voice:self", born_tick=999999, bands=bands)
    )

    result_a = translate_auditory_fragment_to_boundary_observation(
        receipt_a,
        manifest=manifest,
        event_id="event-a",
        observation_id="event-a:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )
    result_b = translate_auditory_fragment_to_boundary_observation(
        receipt_b,
        manifest=manifest,
        event_id="event-b",
        observation_id="event-b:boundary",
        source_time_start=Fraction(5),
        source_time_end=Fraction(6),
    )

    assert result_a.status is AuditoryBoundaryTranslationStatus.OBSERVED
    assert result_b.status is AuditoryBoundaryTranslationStatus.OBSERVED
    assert result_a.observation.signed_native_flux == result_b.observation.signed_native_flux


# --------------------------------------------------------------------------
# Tamper / unauthenticated evidence -> UNKNOWN
# --------------------------------------------------------------------------


def test_tampered_fragment_receipt_is_unknown_not_raised():
    manifest = _mounted_manifest()
    bands = _bands_from(
        {"low": {"winding": 1, "n_events": 1, "events": _events_for([1])}}
    )
    receipt = auditory_fragment_receipt(_fragment(bands=bands))
    tampered = replace(receipt, receipt_payload=receipt.receipt_payload + b" ")

    result = translate_auditory_fragment_to_boundary_observation(
        tampered,
        manifest=manifest,
        event_id="tampered-event",
        observation_id="tampered-event:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is AuditoryBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None
    assert "authentication" in result.reason


def test_missing_receipt_is_unknown():
    manifest = _mounted_manifest()
    result = translate_auditory_fragment_to_boundary_observation(
        None,
        manifest=manifest,
        event_id="missing-event",
        observation_id="missing-event:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )
    assert result.status is AuditoryBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None


def test_missing_manifest_is_unknown():
    bands = _bands_from(
        {"low": {"winding": 1, "n_events": 1, "events": _events_for([1])}}
    )
    receipt = auditory_fragment_receipt(_fragment(bands=bands))
    result = translate_auditory_fragment_to_boundary_observation(
        receipt,
        manifest=None,
        event_id="no-manifest-event",
        observation_id="no-manifest-event:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )
    assert result.status is AuditoryBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None


def test_unmounted_auditory_port_is_unknown():
    manifest = _mounted_manifest()
    manifest_without_sound = replace(
        manifest,
        ports=tuple(
            port for port in manifest.ports if port.kernel_binding.lane_id != "sound"
        ),
    )
    bands = _bands_from(
        {"low": {"winding": 1, "n_events": 1, "events": _events_for([1])}}
    )
    receipt = auditory_fragment_receipt(_fragment(bands=bands))

    result = translate_auditory_fragment_to_boundary_observation(
        receipt,
        manifest=manifest_without_sound,
        event_id="no-port-event",
        observation_id="no-port-event:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is AuditoryBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None
    assert "not mounted" in result.reason


# --------------------------------------------------------------------------
# The core distinction: no capture (UNKNOWN) vs. real quiet capture (real 0)
# --------------------------------------------------------------------------


def test_zero_samples_captured_is_unknown():
    """No real audio samples were ever fed into cochlear_transduce --
    this must be UNKNOWN, never a fabricated flux value."""
    manifest = _mounted_manifest()
    fragment = _fragment(input_sample_count=0, bands=_silent_bands())
    receipt = auditory_fragment_receipt(fragment)

    result = translate_auditory_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="no-capture-event",
        observation_id="no-capture-event:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is AuditoryBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None
    assert "zero real audio samples" in result.reason


def test_real_quiet_capture_is_a_real_zero_flux_not_unknown():
    """Real audio samples WERE captured (input_sample_count > 0) but every
    band genuinely produced zero winding events -- this is real signal
    (silence), and must produce an OBSERVED result with flux exactly 0,
    distinct from the no-capture case above."""
    manifest = _mounted_manifest()
    fragment = _fragment(input_sample_count=128, bands=_silent_bands())
    receipt = auditory_fragment_receipt(fragment)

    result = translate_auditory_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="quiet-capture-event",
        observation_id="quiet-capture-event:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is AuditoryBoundaryTranslationStatus.OBSERVED
    assert result.observation is not None
    assert result.observation.signed_native_flux == Fraction(0)
    result.observation.verify()


def test_no_capture_and_quiet_capture_are_genuinely_distinguishable():
    manifest = _mounted_manifest()
    no_capture = auditory_fragment_receipt(
        _fragment(input_sample_count=0, bands=_silent_bands())
    )
    quiet_capture = auditory_fragment_receipt(
        _fragment(input_sample_count=128, bands=_silent_bands())
    )

    no_capture_result = translate_auditory_fragment_to_boundary_observation(
        no_capture,
        manifest=manifest,
        event_id="event-none",
        observation_id="event-none:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )
    quiet_result = translate_auditory_fragment_to_boundary_observation(
        quiet_capture,
        manifest=manifest,
        event_id="event-quiet",
        observation_id="event-quiet:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert no_capture_result.status is AuditoryBoundaryTranslationStatus.UNKNOWN
    assert quiet_result.status is AuditoryBoundaryTranslationStatus.OBSERVED
    assert quiet_result.observation.signed_native_flux == Fraction(0)


# --------------------------------------------------------------------------
# Flux genuinely varies with different real per-band inputs
# --------------------------------------------------------------------------


def test_flux_varies_with_different_real_band_data():
    manifest = _mounted_manifest()

    mostly_positive = _bands_from(
        {
            "very_low": {"winding": 4, "n_events": 4, "events": _events_for([1, 1, 1, 1])},
            "low": {"winding": 1, "n_events": 3, "events": _events_for([1, -1, 1])},
        }
    )
    mostly_negative = _bands_from(
        {
            "mid_high": {"winding": -5, "n_events": 5, "events": _events_for([-1, -1, -1, -1, -1])},
        }
    )
    balanced = _bands_from(
        {
            "high": {"winding": 0, "n_events": 4, "events": _events_for([1, -1, 1, -1])},
        }
    )

    def _observed_flux(bands):
        receipt = auditory_fragment_receipt(_fragment(bands=bands))
        result = translate_auditory_fragment_to_boundary_observation(
            receipt,
            manifest=manifest,
            event_id=f"vary-event-{id(bands)}",
            observation_id=f"vary-event-{id(bands)}:boundary",
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
        )
        assert result.status is AuditoryBoundaryTranslationStatus.OBSERVED
        return result.observation.signed_native_flux

    flux_positive = _observed_flux(mostly_positive)
    flux_negative = _observed_flux(mostly_negative)
    flux_balanced = _observed_flux(balanced)

    assert flux_positive == Fraction(5, 7)
    assert flux_negative == Fraction(-1)
    assert flux_balanced == Fraction(0)

    # All three genuinely differ from each other -- the derivation tracks
    # the real per-band data, it is not a constant.
    assert len({flux_positive, flux_negative, flux_balanced}) == 3
    for flux in (flux_positive, flux_negative, flux_balanced):
        assert Fraction(-1) <= flux <= Fraction(1)


def test_bad_time_window_is_unknown_not_raised():
    manifest = _mounted_manifest()
    bands = _bands_from(
        {"low": {"winding": 1, "n_events": 1, "events": _events_for([1])}}
    )
    receipt = auditory_fragment_receipt(_fragment(bands=bands))

    result = translate_auditory_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="bad-window-event",
        observation_id="bad-window-event:boundary",
        source_time_start=Fraction(1),
        source_time_end=Fraction(1),  # not a positive duration
    )

    assert result.status is AuditoryBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None
