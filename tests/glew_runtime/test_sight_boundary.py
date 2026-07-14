from __future__ import annotations

import copy
from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.sight_boundary import (
    VisionBoundaryTranslationStatus,
    production_sight_port_id,
    translate_visual_fragment_to_boundary_observation,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    mount_packaged_production_story_chemistry,
)
from dsf_ai_service.visual_krimelack import view_picture, visual_fragment_receipt


RUNTIME_KEY = b"test process only: sight boundary translator runtime secret"
RUNTIME_KEY_ID = "test-sight-boundary-runtime-key"


def _mounted_manifest():
    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=RUNTIME_KEY,
        runtime_key_id=RUNTIME_KEY_ID,
    )
    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    return mounted.runtime.manifest


def _real_fragment_receipt(
    *, fill_value: float, ticks_per_fixation: int = 500, seed: int = 7,
    born_tick: int = 0,
):
    """Run the real saccade/fovea-krimelack pipeline over a real (synthetic
    but genuine) image and seal the result the same way production does.

    This is the exact production entry point
    (``dsf_ai_service.v4.gualaloom_v5_engine.Guala.process_sight_frame``
    calls the same ``view_picture`` + ``visual_fragment_receipt`` pair) --
    nothing here is a stand-in fixture for the pipeline.
    """

    image = np.full((16, 16), fill_value, dtype=np.float64)
    fragments = view_picture(
        image,
        source_id="test-camera",
        born_tick=born_tick,
        seed=seed,
        n_fixations=1,
        ticks_per_fixation=ticks_per_fixation,
    )
    assert fragments, "view_picture produced no fragments for a real image"
    return visual_fragment_receipt(fragments[0])


def test_real_valid_fragment_translates_to_a_verifiable_boundary_observation():
    manifest = _mounted_manifest()
    receipt = _real_fragment_receipt(fill_value=0.8)
    assert receipt["events"], "fixture must exercise a real nonempty fixation"

    result = translate_visual_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="live-event-1",
        observation_id="live-event-1:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is VisionBoundaryTranslationStatus.OBSERVED
    assert result.observation is not None
    observation = result.observation
    observation.verify()  # must not raise -- the observation is self-consistent

    assert observation.port_id == production_sight_port_id()
    assert observation.native_flux_unit == manifest.port(
        production_sight_port_id()
    ).native_signal_unit
    assert isinstance(observation.signed_native_flux, Fraction)

    # Exact hand cross-check against the real recorded (t, dw, s) events:
    # net winding direction weighted by real signal magnitude, averaged
    # over every real crossing -- independent of the declared window.
    expected = sum(
        (
            Fraction(int(event["dw"])) * Fraction(event["s"])
            for event in receipt["events"]
        ),
        Fraction(0),
    ) / len(receipt["events"])
    assert observation.signed_native_flux == expected
    assert observation.signed_native_flux != 0
    assert -1 <= observation.signed_native_flux <= 1


def test_tampered_fragment_receipt_is_explicit_unknown_not_a_fabricated_flux():
    manifest = _mounted_manifest()
    receipt = _real_fragment_receipt(fill_value=0.8)
    assert receipt["events"]

    tampered = copy.deepcopy(receipt)
    tampered["events"][0]["s"] = tampered["events"][0]["s"] + 0.5
    # receipt_sha256 is now stale relative to the mutated events.

    result = translate_visual_fragment_to_boundary_observation(
        tampered,
        manifest=manifest,
        event_id="live-event-2",
        observation_id="live-event-2:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is VisionBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None
    assert "tamper" in result.reason or "shape check" in result.reason


def test_corrupted_receipt_digest_is_also_explicit_unknown():
    manifest = _mounted_manifest()
    receipt = _real_fragment_receipt(fill_value=0.6)
    assert receipt["events"]

    corrupted = copy.deepcopy(receipt)
    corrupted["receipt_sha256"] = "0" * 64

    result = translate_visual_fragment_to_boundary_observation(
        corrupted,
        manifest=manifest,
        event_id="live-event-2b",
        observation_id="live-event-2b:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is VisionBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None


def test_zero_event_fragment_is_explicit_unknown_never_a_fabricated_zero_flux():
    manifest = _mounted_manifest()
    # A real, entirely dark frame: omega stays at its floor (omega_0) for
    # the whole fixation and the chosen tick budget never accumulates a
    # full 2*pi phase winding -- a genuine zero-event fixation produced by
    # the real physics, not a synthesized empty list.
    receipt = _real_fragment_receipt(fill_value=0.0, ticks_per_fixation=50)
    assert receipt["events"] == []

    result = translate_visual_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="live-event-3",
        observation_id="live-event-3:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is VisionBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None
    assert "zero events" in result.reason


def test_missing_or_malformed_fragment_receipt_is_explicit_unknown():
    manifest = _mounted_manifest()
    for bad in (None, {}, {"schema": "wrong"}, "not-a-dict", 42, []):
        result = translate_visual_fragment_to_boundary_observation(
            bad,
            manifest=manifest,
            event_id="live-event-4",
            observation_id="live-event-4:sight:boundary",
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
        )
        assert result.status is VisionBoundaryTranslationStatus.UNKNOWN
        assert result.observation is None


def test_missing_manifest_is_explicit_unknown_not_a_crash():
    receipt = _real_fragment_receipt(fill_value=0.5)

    result = translate_visual_fragment_to_boundary_observation(
        receipt,
        manifest=None,
        event_id="live-event-4b",
        observation_id="live-event-4b:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is VisionBoundaryTranslationStatus.UNKNOWN
    assert result.observation is None


def test_nonpositive_window_duration_is_explicit_unknown():
    manifest = _mounted_manifest()
    receipt = _real_fragment_receipt(fill_value=0.5)

    equal = translate_visual_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="live-event-4c",
        observation_id="live-event-4c:sight:boundary",
        source_time_start=Fraction(1),
        source_time_end=Fraction(1),
    )
    reversed_ = translate_visual_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="live-event-4d",
        observation_id="live-event-4d:sight:boundary",
        source_time_start=Fraction(2),
        source_time_end=Fraction(1),
    )
    not_a_fraction = translate_visual_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="live-event-4e",
        observation_id="live-event-4e:sight:boundary",
        source_time_start=0,
        source_time_end=Fraction(1),
    )

    for result in (equal, reversed_, not_a_fraction):
        assert result.status is VisionBoundaryTranslationStatus.UNKNOWN
        assert result.observation is None


def test_derived_flux_genuinely_varies_with_different_real_signal_data():
    manifest = _mounted_manifest()
    dim_receipt = _real_fragment_receipt(fill_value=0.2, seed=11)
    bright_receipt = _real_fragment_receipt(fill_value=0.95, seed=11)
    assert dim_receipt["events"] and bright_receipt["events"]
    # Confirm the two real fixtures actually recorded different signal data
    # (not an accidental duplicate) before trusting the derived comparison.
    assert dim_receipt["events"] != bright_receipt["events"]

    dim_result = translate_visual_fragment_to_boundary_observation(
        dim_receipt,
        manifest=manifest,
        event_id="live-event-5a",
        observation_id="live-event-5a:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )
    bright_result = translate_visual_fragment_to_boundary_observation(
        bright_receipt,
        manifest=manifest,
        event_id="live-event-5b",
        observation_id="live-event-5b:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert dim_result.status is VisionBoundaryTranslationStatus.OBSERVED
    assert bright_result.status is VisionBoundaryTranslationStatus.OBSERVED
    dim_flux = dim_result.observation.signed_native_flux
    bright_flux = bright_result.observation.signed_native_flux
    assert dim_flux != bright_flux
    # The brighter, more-active real fixation should carry a strictly
    # larger net directed weighted winding (more real events, each
    # weighted by a larger real intensity).
    assert bright_flux > dim_flux > 0


def test_flux_is_invariant_to_the_caller_declared_window_duration():
    """Same real (t, dw, s) events, different declared boundary-event
    windows -> the identical signed_native_flux.

    This is deliberate, not an oversight: story_chemistry's own profile
    defines susceptibility as unit propensity "per structural-time unit"
    per flux unit, and chemical_receiver.py multiplies that propensity by
    the interval's real elapsed duration exactly once, at
    ``(generator_matrix * delta).exp()``. If this translator pre-divided
    the flux by the same declared duration, that duration would cancel
    out of the eventual transition matrix and become physically inert.
    It also means the same real sensor evidence must not silently change
    its reported flux merely because a caller declared a different
    bookkeeping window around it.
    """

    manifest = _mounted_manifest()
    receipt = _real_fragment_receipt(fill_value=0.7)

    unit_window = translate_visual_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="live-event-6a",
        observation_id="live-event-6a:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )
    scaled_window = translate_visual_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="live-event-6b",
        observation_id="live-event-6b:sight:boundary",
        source_time_start=Fraction(3),
        source_time_end=Fraction(97, 10),
    )

    assert unit_window.status is VisionBoundaryTranslationStatus.OBSERVED
    assert scaled_window.status is VisionBoundaryTranslationStatus.OBSERVED
    assert (
        unit_window.observation.signed_native_flux
        == scaled_window.observation.signed_native_flux
    )
    assert -1 <= unit_window.observation.signed_native_flux <= 1


def test_provenance_receipt_traces_back_to_the_native_fragment_digest():
    import json as _json

    manifest = _mounted_manifest()
    receipt = _real_fragment_receipt(fill_value=0.4)

    result = translate_visual_fragment_to_boundary_observation(
        receipt,
        manifest=manifest,
        event_id="live-event-7",
        observation_id="live-event-7:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is VisionBoundaryTranslationStatus.OBSERVED
    observation = result.observation
    provenance = _json.loads(observation.provenance_receipt_payload.decode("utf-8"))
    assert (
        provenance["source_visual_fragment"]["receipt_sha256"]
        == receipt["receipt_sha256"]
    )
    assert provenance["source_visual_fragment"]["source_id"] == receipt["source_id"]
    assert (
        provenance["source_visual_fragment"]["winding_count"]
        == receipt["winding_count"]
    )
    assert provenance["event_id"] == "live-event-7"
    assert provenance["port_id"] == production_sight_port_id()


def test_never_derives_flux_from_a_word_label_only_from_real_events():
    """Two fragments with identical (t, dw, s) events but different
    ``source_id`` labels must translate to the identical flux -- proving
    the label plays no role in the derivation."""

    manifest = _mounted_manifest()
    receipt_a = _real_fragment_receipt(fill_value=0.55, seed=3)
    receipt_b = copy.deepcopy(receipt_a)
    # Re-point source_id only, then reseal so the receipt stays authentic.
    receipt_b["source_id"] = "a-completely-different-caption-like-label"
    from dsf_ai_service.visual_krimelack import _receipt_digest

    payload = {k: v for k, v in receipt_b.items() if k != "receipt_sha256"}
    receipt_b["receipt_sha256"] = _receipt_digest(payload)

    result_a = translate_visual_fragment_to_boundary_observation(
        receipt_a,
        manifest=manifest,
        event_id="live-event-8a",
        observation_id="live-event-8a:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )
    result_b = translate_visual_fragment_to_boundary_observation(
        receipt_b,
        manifest=manifest,
        event_id="live-event-8b",
        observation_id="live-event-8b:sight:boundary",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result_a.status is VisionBoundaryTranslationStatus.OBSERVED
    assert result_b.status is VisionBoundaryTranslationStatus.OBSERVED
    assert (
        result_a.observation.signed_native_flux
        == result_b.observation.signed_native_flux
    )
