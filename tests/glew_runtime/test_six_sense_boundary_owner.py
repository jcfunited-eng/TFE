from __future__ import annotations

import copy
from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.auditory_fragment_receipt import (
    AUDITORY_BAND_ORDER,
    AuditoryPerceptFragment,
    auditory_fragment_receipt,
)
from dsf_ai_service.glew_runtime.six_sense_boundary_owner import (
    CausalWindowCandidateStatus,
    SixSenseBoundaryStatus,
    confirm_causal_window_candidate,
    observe_six_sense_boundary,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    PRODUCTION_STORY_PORT_LANES,
    StoryChemistryStatus,
    StoryKernelBridgeStatus,
    build_story_frozen_kernel_inputs,
    evolve_story_chemistry_event,
    mount_packaged_production_story_chemistry,
)
from dsf_ai_service.visual_krimelack import view_picture, visual_fragment_receipt


RUNTIME_KEY = b"test process only: six sense boundary owner runtime secret"
RUNTIME_KEY_ID = "test-six-sense-boundary-owner-runtime-key"

# PRODUCTION_STORY_PORT_LANES is alphabetic by port_id (confirmed in
# story_chemistry.py and GLEW_LANGUAGE_WEAVE_PROFILE_v1.json's
# "verified_anti_patterns_absent"); the same alphabetic order is what
# StoryPhysicalBoundaryEvent.verify() requires observations to be sorted
# into, so both these tuples name the identical canonical order.
ALL_FIVE_PORT_IDS = tuple(sorted(port_id for port_id, _lane in PRODUCTION_STORY_PORT_LANES))
SOMATIC_ONLY_PORT_IDS = tuple(
    sorted(
        port_id
        for port_id, lane in PRODUCTION_STORY_PORT_LANES
        if lane in ("touch", "smell", "taste")
    )
)


def _mounted_runtime():
    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=RUNTIME_KEY,
        runtime_key_id=RUNTIME_KEY_ID,
    )
    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    return mounted.runtime


def _real_visual_fragment_receipt(
    *, fill_value: float, ticks_per_fixation: int = 500, seed: int = 7, born_tick: int = 0
):
    """Same real saccade/fovea-krimelack pipeline used by
    tests/glew_runtime/test_sight_boundary.py -- a genuine (synthetic but
    real) captured image, not a stand-in fixture."""

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


def _silent_bands() -> dict:
    return {
        band_name: {"winding": 0, "n_events": 0, "events": []}
        for band_name in AUDITORY_BAND_ORDER
    }


def _real_auditory_fragment_receipt(
    *, born_tick: int = 100, source_id: str = "mic:live"
):
    """Same real cochlear-band capture shape used by
    tests/glew_runtime/test_sound_boundary.py -- one real nonzero band plus
    five genuinely silent bands, authenticated the same way production
    does."""

    bands = _silent_bands()
    bands["mid"] = {
        "winding": 3,
        "n_events": 5,
        "events": [
            {"t": 0.04 * (i + 1), "dw": (1 if i != 3 else -1), "s": 0.5}
            for i in range(5)
        ],
    }
    fragment = AuditoryPerceptFragment(
        source_id=source_id,
        born_tick=born_tick,
        sample_rate_hz=200,
        input_sample_count=128,
        bands=bands,
    )
    return auditory_fragment_receipt(fragment)


def _build_two_evolved_five_port_events():
    """Build two real, full five-port StoryPhysicalBoundaryEvents at
    strictly increasing source_time, evolving the real mounted chemistry
    runtime between them (this is test-only chemistry evolution -- the
    production six_sense_boundary_owner module itself never calls
    evolve_story_chemistry_event)."""

    runtime = _mounted_runtime()

    first = observe_six_sense_boundary(
        runtime,
        event_id="two-frame-instant-1",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        visual_fragment_receipt=_real_visual_fragment_receipt(fill_value=0.8, seed=1),
        auditory_fragment_receipt=_real_auditory_fragment_receipt(born_tick=0),
        touch_descriptor="warm",
        smell_descriptor=None,
        taste_descriptor=None,
    )
    assert first.status is SixSenseBoundaryStatus.OBSERVED

    evolved_1 = evolve_story_chemistry_event(runtime=runtime, event=first.event)
    assert evolved_1.status is StoryChemistryStatus.EVOLVED

    second = observe_six_sense_boundary(
        evolved_1.runtime,
        event_id="two-frame-instant-2",
        source_time_start=Fraction(1),
        source_time_end=Fraction(2),
        visual_fragment_receipt=_real_visual_fragment_receipt(fill_value=0.5, seed=2),
        auditory_fragment_receipt=_real_auditory_fragment_receipt(born_tick=100),
        touch_descriptor=None,
        smell_descriptor="floral",
        taste_descriptor=None,
    )
    assert second.status is SixSenseBoundaryStatus.OBSERVED

    evolved_2 = evolve_story_chemistry_event(runtime=evolved_1.runtime, event=second.event)
    assert evolved_2.status is StoryChemistryStatus.EVOLVED

    return first.event, second.event, evolved_1, evolved_2


# --------------------------------------------------------------------------
# observe_six_sense_boundary: real multi-sense instant assembly
# --------------------------------------------------------------------------


def test_real_multisense_instant_assembles_one_valid_five_port_event():
    runtime = _mounted_runtime()

    result = observe_six_sense_boundary(
        runtime,
        event_id="full-instant-1",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        visual_fragment_receipt=_real_visual_fragment_receipt(fill_value=0.8),
        auditory_fragment_receipt=_real_auditory_fragment_receipt(),
        touch_descriptor="warm",
        smell_descriptor=None,
        taste_descriptor=None,
    )

    assert result.status is SixSenseBoundaryStatus.OBSERVED
    assert result.event is not None
    result.event.verify()  # must not raise: real, self-consistent, canonically sorted
    assert result.active_port_ids == ALL_FIVE_PORT_IDS
    assert tuple(o.port_id for o in result.event.observations) == ALL_FIVE_PORT_IDS
    # Canonical sort-by-port_id, exactly as StoryPhysicalBoundaryEvent requires.
    assert tuple(sorted(o.port_id for o in result.event.observations)) == tuple(
        o.port_id for o in result.event.observations
    )


def test_somatic_only_instant_no_captured_sight_or_sound_is_still_observed():
    """Sight and sound genuinely were not captured this instant (no fragment
    supplied for either). Per section 9.1 of the governing spec and this
    owner's own documented reasoning (see six_sense_boundary_owner.py's
    module docstring, "Which layer owns..."), this is a legitimate,
    OBSERVED instant at THIS layer: the profile's "at least four lived
    lanes" language belongs to event_support.py's downstream Gram-rank
    computation over already-field-mapped evidence (event_support.py line
    ~986, and GLEW_LANGUAGE_WEAVE_PROFILE_v1.json's
    event_support.full_rank_rule), not to this raw boundary-assembly layer.
    A 3-port instant is real and must not be rejected here."""

    runtime = _mounted_runtime()

    result = observe_six_sense_boundary(
        runtime,
        event_id="somatic-only-instant",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        visual_fragment_receipt=None,
        auditory_fragment_receipt=None,
        touch_descriptor="warm",
        smell_descriptor=None,
        taste_descriptor=None,
    )

    assert result.status is SixSenseBoundaryStatus.OBSERVED
    assert result.event is not None
    result.event.verify()
    assert result.active_port_ids == SOMATIC_ONLY_PORT_IDS
    assert len(result.event.observations) == 3


def test_failed_sight_capture_propagates_explicit_unknown_not_silently_dropped():
    """A genuinely tampered/empty visual fragment -- real evidence WAS
    expected because the caller supplied a fragment -- must fail the whole
    instant closed, not silently omit the sight port from an otherwise-
    OBSERVED event."""

    runtime = _mounted_runtime()

    # A real, entirely dark frame: a genuine zero-event fixation (matches
    # tests/glew_runtime/test_sight_boundary.py's own zero-event case), so
    # sight_boundary.py returns UNKNOWN ("zero events") rather than a
    # fabricated flux.
    empty_receipt = _real_visual_fragment_receipt(fill_value=0.0, ticks_per_fixation=50)
    assert empty_receipt["events"] == []

    result = observe_six_sense_boundary(
        runtime,
        event_id="failed-sight-instant",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        visual_fragment_receipt=empty_receipt,
        auditory_fragment_receipt=None,
        touch_descriptor=None,
        smell_descriptor=None,
        taste_descriptor=None,
    )

    assert result.status is SixSenseBoundaryStatus.UNKNOWN
    assert result.event is None
    assert result.active_port_ids == ()
    assert "sight" in result.reason
    assert "zero events" in result.reason


def test_tampered_sight_receipt_digest_also_propagates_unknown():
    runtime = _mounted_runtime()
    receipt = _real_visual_fragment_receipt(fill_value=0.6)
    tampered = copy.deepcopy(receipt)
    tampered["events"][0]["s"] = tampered["events"][0]["s"] + 0.5  # stale digest now

    result = observe_six_sense_boundary(
        runtime,
        event_id="tampered-sight-instant",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        visual_fragment_receipt=tampered,
        auditory_fragment_receipt=None,
    )

    assert result.status is SixSenseBoundaryStatus.UNKNOWN
    assert result.event is None


def test_failed_sound_capture_propagates_explicit_unknown():
    """A real auditory fragment receipt was tampered after sealing -- real
    evidence was expected (a fragment was supplied) and must fail the
    instant closed."""

    from dataclasses import replace

    runtime = _mounted_runtime()
    receipt = _real_auditory_fragment_receipt()
    tampered = replace(receipt, receipt_payload=receipt.receipt_payload + b" ")

    result = observe_six_sense_boundary(
        runtime,
        event_id="failed-sound-instant",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        visual_fragment_receipt=None,
        auditory_fragment_receipt=tampered,
    )

    assert result.status is SixSenseBoundaryStatus.UNKNOWN
    assert result.event is None
    assert "sound" in result.reason


def test_illegitimate_somatic_descriptor_propagates_explicit_unknown():
    """Touch/smell/taste always carry real emulator state; an illegitimate
    descriptor is a real failure of that expectation, not a silently
    dropped port."""

    runtime = _mounted_runtime()

    result = observe_six_sense_boundary(
        runtime,
        event_id="bad-descriptor-instant",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        touch_descriptor="glorbnax-not-a-real-word",
    )

    assert result.status is SixSenseBoundaryStatus.UNKNOWN
    assert result.event is None
    assert "touch" in result.reason


def test_unmounted_runtime_propagates_explicit_unknown():
    result = observe_six_sense_boundary(
        None,
        event_id="unmounted-instant",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is SixSenseBoundaryStatus.UNKNOWN
    assert result.event is None


# --------------------------------------------------------------------------
# confirm_causal_window_candidate
# --------------------------------------------------------------------------


def test_real_increasing_time_sequence_is_a_causal_window_candidate():
    event_1, event_2, _evolved_1, _evolved_2 = _build_two_evolved_five_port_events()

    result = confirm_causal_window_candidate((event_1, event_2))

    assert result.status is CausalWindowCandidateStatus.CANDIDATE
    assert result.events == (event_1, event_2)
    assert result.source_time_starts == (Fraction(0), Fraction(1))


def test_out_of_order_sequence_fails_closed():
    event_1, event_2, _evolved_1, _evolved_2 = _build_two_evolved_five_port_events()

    result = confirm_causal_window_candidate((event_2, event_1))

    assert result.status is CausalWindowCandidateStatus.UNKNOWN
    assert result.events == ()
    assert "strictly increasing" in result.reason


def test_duplicate_timestamp_sequence_fails_closed():
    event_1, _event_2, _evolved_1, _evolved_2 = _build_two_evolved_five_port_events()

    result = confirm_causal_window_candidate((event_1, event_1))

    assert result.status is CausalWindowCandidateStatus.UNKNOWN
    assert result.events == ()


def test_single_event_is_not_a_causal_window_candidate():
    event_1, _event_2, _evolved_1, _evolved_2 = _build_two_evolved_five_port_events()

    result = confirm_causal_window_candidate((event_1,))

    assert result.status is CausalWindowCandidateStatus.UNKNOWN
    assert "at least two" in result.reason


def test_empty_sequence_fails_closed():
    result = confirm_causal_window_candidate(())

    assert result.status is CausalWindowCandidateStatus.UNKNOWN


# --------------------------------------------------------------------------
# The real acceptance test: the assembled, evolved sequence is genuinely
# consumable by the existing, untouched build_story_frozen_kernel_inputs.
# --------------------------------------------------------------------------


def test_assembled_evolved_sequence_is_accepted_by_the_real_frozen_kernel_bridge():
    event_1, event_2, evolved_1, evolved_2 = _build_two_evolved_five_port_events()

    candidate = confirm_causal_window_candidate((event_1, event_2))
    assert candidate.status is CausalWindowCandidateStatus.CANDIDATE

    # This module never calls evolve_story_chemistry_event or
    # build_story_frozen_kernel_inputs itself; this test calls the REAL,
    # already-tested machinery directly to prove the sequence this module
    # assembled and validated is genuinely usable downstream, not merely
    # shaped like it should be.
    bridge = build_story_frozen_kernel_inputs(
        runtime=evolved_2.runtime,
        output_frames=(evolved_1.outputs, evolved_2.outputs),
        source_epoch="six-sense-boundary-owner-test-epoch",
    )

    assert bridge.status is StoryKernelBridgeStatus.READY
    assert len(bridge.streams) == 5
    assert len(bridge.kernel_inputs) == 5
    assert tuple(stream.lane_id for stream in bridge.streams) == (
        "sound",
        "smell",
        "taste",
        "touch",
        "sight",
    )
    for stream in bridge.streams:
        assert len(stream.samples) == 2  # two real evolved frames per port
