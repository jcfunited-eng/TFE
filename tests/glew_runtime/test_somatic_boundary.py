from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from dsf_ai_service.glew_runtime.somatic_boundary import (
    CANONICAL_ACTIVE_EVENT_FLUX,
    ChemistryPortBoundaryStatus,
    SomaticBoundaryEventKind,
    observe_chemistry_port_boundary,
    observe_smell_port_boundary,
    observe_taste_port_boundary,
    observe_touch_port_boundary,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    StoryPhysicalBoundaryEvent,
    evolve_story_chemistry_event,
    mount_story_chemistry,
)


FIXTURE = (
    Path(__file__).parent / "fixtures" / "candidate_story_chemistry_manifest.json"
)
CANDIDATE_KEY = b"transparent candidate test key; never production authority"
CANDIDATE_KEY_ID = "candidate-test-hmac-key-not-production"

TOUCH_PORT = "story-touch.native-port-0"
SMELL_PORT = "story-smell.native-port-0"
TASTE_PORT = "story-taste.native-port-0"
VISION_PORT = "story-vision.native-port-0"


def _mount():
    mounted = mount_story_chemistry(
        manifest_envelope_payload=FIXTURE.read_bytes(),
        trusted_authentication_key=CANDIDATE_KEY,
        expected_key_id=CANDIDATE_KEY_ID,
    )
    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    return mounted.runtime


def test_real_active_descriptor_produces_a_correct_nonzero_flux_observation():
    runtime = _mount()

    result = observe_smell_port_boundary(
        runtime,
        event_id="event-active-smell",
        observation_id="event-active-smell:smell",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        active_descriptor="floral",
    )

    assert result.status is ChemistryPortBoundaryStatus.OBSERVED
    assert result.event_kind is SomaticBoundaryEventKind.ACTIVE_DESCRIPTOR_EVENT
    assert result.lane_id == "smell"
    assert result.observation is not None
    assert result.observation.signed_native_flux == CANONICAL_ACTIVE_EVENT_FLUX
    assert result.observation.signed_native_flux != 0
    assert result.observation.native_flux_unit == (
        "virtual-normalized-olfactory-boundary-flux"
    )
    result.observation.verify()  # must not raise


def test_no_descriptor_produces_a_correct_zero_flux_natural_decay_observation():
    runtime = _mount()

    result = observe_touch_port_boundary(
        runtime,
        event_id="event-quiescent-touch",
        observation_id="event-quiescent-touch:touch",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        active_descriptor=None,
    )

    assert result.status is ChemistryPortBoundaryStatus.OBSERVED
    assert result.event_kind is SomaticBoundaryEventKind.QUIESCENT_NATURAL_DECAY
    assert result.observation is not None
    assert result.observation.signed_native_flux == Fraction(0)
    result.observation.verify()  # zero flux is a real, valid observation


def test_active_and_quiescent_observations_are_genuinely_distinct_in_the_receipt():
    runtime = _mount()

    active = observe_touch_port_boundary(
        runtime,
        event_id="event-compare-touch",
        observation_id="event-compare-touch:touch",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        active_descriptor="warm",
    )
    quiescent = observe_touch_port_boundary(
        runtime,
        event_id="event-compare-touch",
        observation_id="event-compare-touch:touch",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        active_descriptor=None,
    )

    assert active.status is ChemistryPortBoundaryStatus.OBSERVED
    assert quiescent.status is ChemistryPortBoundaryStatus.OBSERVED
    # Same event_id/observation_id/port/time window on both sides -- the ONLY
    # real difference is whether a real active event was reported. The
    # receipts must not collapse the two into the same evidence.
    assert (
        active.observation.provenance_receipt_sha256
        != quiescent.observation.provenance_receipt_sha256
    )
    assert (
        active.observation.observation_receipt_sha256
        != quiescent.observation.observation_receipt_sha256
    )
    assert active.observation.signed_native_flux != quiescent.observation.signed_native_flux


def test_never_mounted_runtime_is_explicit_unknown():
    result = observe_chemistry_port_boundary(
        None,
        TOUCH_PORT,
        event_id="event-unmounted",
        observation_id="event-unmounted:touch",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is ChemistryPortBoundaryStatus.UNKNOWN
    assert result.observation is None
    assert "never been mounted" in result.reason


def test_port_absent_from_this_boundary_owner_is_explicit_unknown():
    runtime = _mount()

    # story-vision.native-port-0 IS mounted (it's a real port in the
    # manifest) but sight/sound are not owned by this somatic boundary
    # module; it must fail closed rather than silently observe it.
    result = observe_chemistry_port_boundary(
        runtime,
        VISION_PORT,
        event_id="event-wrong-sense",
        observation_id="event-wrong-sense:vision",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is ChemistryPortBoundaryStatus.UNKNOWN
    assert result.observation is None
    assert "touch/smell/taste" in result.reason


def test_port_not_in_manifest_is_explicit_unknown():
    runtime = _mount()

    result = observe_chemistry_port_boundary(
        runtime,
        "story-not-a-real-port.native-port-0",
        event_id="event-fake-port",
        observation_id="event-fake-port:fake",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )

    assert result.status is ChemistryPortBoundaryStatus.UNKNOWN
    assert result.observation is None


def test_illegitimate_descriptor_is_explicit_unknown_never_fabricated():
    runtime = _mount()

    nonsense = observe_taste_port_boundary(
        runtime,
        event_id="event-nonsense-taste",
        observation_id="event-nonsense-taste:taste",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        active_descriptor="glorbnax",
    )
    assert nonsense.status is ChemistryPortBoundaryStatus.UNKNOWN
    assert nonsense.observation is None
    assert "not a real legitimate" in nonsense.reason

    # A real word, but for the wrong sense's vocabulary, must not be coerced
    # into a touch event just because it is "a real word somewhere".
    wrong_lane = observe_touch_port_boundary(
        runtime,
        event_id="event-wrong-lane-touch",
        observation_id="event-wrong-lane-touch:touch",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        active_descriptor="floral",  # a real smell word, not a touch word
    )
    assert wrong_lane.status is ChemistryPortBoundaryStatus.UNKNOWN
    assert wrong_lane.observation is None


def test_source_time_start_must_match_the_ports_real_current_state():
    runtime = _mount()

    result = observe_touch_port_boundary(
        runtime,
        event_id="event-bad-start-time",
        observation_id="event-bad-start-time:touch",
        source_time_start=Fraction(5),  # port is actually at source_time 0
        source_time_end=Fraction(6),
        active_descriptor=None,
    )

    assert result.status is ChemistryPortBoundaryStatus.UNKNOWN
    assert result.observation is None
    assert "current mounted source_time" in result.reason


def test_repeated_zero_flux_observations_prove_real_relaxation_toward_rest():
    """Not a static passthrough: inject one real active event, then evolve
    through successive genuine zero-flux natural-decay observations and
    confirm the certified active-mass relevance actually, monotonically
    relaxes toward rest through the real matrix-exponential chemistry."""

    runtime = _mount()

    active = observe_touch_port_boundary(
        runtime,
        event_id="decay-proof:active",
        observation_id="decay-proof:active:touch",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        active_descriptor="hot",
    )
    assert active.status is ChemistryPortBoundaryStatus.OBSERVED
    evolved = evolve_story_chemistry_event(
        runtime=runtime,
        event=StoryPhysicalBoundaryEvent(
            event_id="decay-proof:active",
            observations=(active.observation,),
        ),
    )
    assert evolved.status is StoryChemistryStatus.EVOLVED
    relevances = [evolved.outputs[0].kernel_binary64_relevance.binary64_value]
    runtime = evolved.runtime

    # A real active event drove real activation.
    assert relevances[0] is not None
    assert relevances[0] > 0

    for step in range(1, 5):
        start = Fraction(step)
        end = Fraction(step + 1)
        quiescent = observe_touch_port_boundary(
            runtime,
            event_id=f"decay-proof:quiet-{step}",
            observation_id=f"decay-proof:quiet-{step}:touch",
            source_time_start=start,
            source_time_end=end,
            active_descriptor=None,
        )
        assert quiescent.status is ChemistryPortBoundaryStatus.OBSERVED
        assert quiescent.observation.signed_native_flux == Fraction(0)
        evolved = evolve_story_chemistry_event(
            runtime=runtime,
            event=StoryPhysicalBoundaryEvent(
                event_id=f"decay-proof:quiet-{step}",
                observations=(quiescent.observation,),
            ),
        )
        assert evolved.status is StoryChemistryStatus.EVOLVED
        relevance = evolved.outputs[0].kernel_binary64_relevance.binary64_value
        assert relevance is not None
        relevances.append(relevance)
        runtime = evolved.runtime

    # Strictly decreasing at every genuinely quiescent step: real relaxation,
    # not a value that merely gets copied forward unchanged.
    for earlier, later in zip(relevances, relevances[1:]):
        assert later < earlier
    # Approaching rest (active mass -> 0) but a finite number of finite-time
    # steps never fabricates an exact reach of the limit.
    assert relevances[-1] > 0
