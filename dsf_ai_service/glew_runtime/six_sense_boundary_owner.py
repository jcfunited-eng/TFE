"""Live six-sense boundary owner.

This module is the production owner required by
``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
section 9.1, "Live six-sense boundary owner". It is the first place any
caller combines the three already-built, already-committed per-sense
translators --

* ``sight_boundary.translate_visual_fragment_to_boundary_observation``
* ``sound_boundary.translate_auditory_fragment_to_boundary_observation``
* ``somatic_boundary.observe_touch_port_boundary`` /
  ``observe_smell_port_boundary`` / ``observe_taste_port_boundary``

-- into one real
:class:`~dsf_ai_service.glew_runtime.story_chemistry.StoryPhysicalBoundaryEvent`
for one instant, and then confirms a real ordered sequence of those events is
a genuine causal-window candidate.

This module does not run the chemistry itself. It never calls
``story_chemistry.evolve_story_chemistry_event`` or
``story_chemistry.build_story_frozen_kernel_inputs`` -- that machinery is
already built and already tested; this module's job stops at producing
real, receipted, correctly time-ordered ``StoryPhysicalBoundaryEvent``
objects that those functions can consume unmodified.

Which senses are attempted, and why
------------------------------------
Per the governing spec's section 9.1:

    "Sight and sound use their actual observed/emulated activity. Touch,
    smell, and taste use the robust emulator's actual states; quiet input
    must evolve through natural decay rather than becoming an invented
    descriptor."

Sight and sound therefore participate in an instant's event ONLY when the
caller actually supplies real captured evidence for that instant (a visual
fragment receipt / an auditory fragment receipt). No sight or sound port may
ever be conjured from a word label or from "the lane must be active" --
if no real capture happened this instant, that port is simply absent from
the assembled event, exactly as ``StoryPhysicalBoundaryEvent`` already
permits ("Ports absent from an event are not sampled and retain their
state", ``story_chemistry.py`` module docstring).

Touch, smell, and taste are attempted on every single call, whether or not
an active descriptor is supplied, because ``somatic_boundary.py`` already
proved (module docstring, and ``tests/glew_runtime/test_somatic_boundary.py``
::test_repeated_zero_flux_observations_prove_real_relaxation_toward_rest)
that "no active input" is a real zero-flux natural-decay observation, not a
missing-evidence case. These three lanes are therefore expected to succeed
on every call as long as the runtime is genuinely mounted; any ``UNKNOWN``
from one of them is a real failure of the mounted runtime/state/descriptor
(never "the sense was legitimately absent"), and is propagated as an
explicit top-level unknown rather than silently dropping that port.

Which layer owns "how many senses must be real this instant"
--------------------------------------------------------------
This module does **not** apply the profile's "at least four active/lived
lanes" language as a gate on its own OBSERVED/UNKNOWN outcome. That
requirement belongs to a different, later layer, and conflating the two
would silently reject perfectly legitimate assembled instants. The evidence
for this, read directly rather than assumed:

1. ``dsf_ai_service/glew_runtime/event_support.py`` (module docstring,
   line 9, and ``evaluate_event_support``, around line 986) computes
   ``R_geometry`` from the exact Gram determinant of the currently-mapped
   ``PortTransportEvidence`` objects and explicitly writes:
   ``if complete and len(lived_lanes) >= 4: geometry = exact_port_gram_geometry(...)
   else: geometry = Fraction(0)``. Two things follow from reading this
   code directly: (a) the four-lane test is evaluated over
   ``current`` -- a dict of already-mapped ``PortTransportEvidence`` keyed
   by ``MountedFieldTopology`` fiber key, i.e. state that only exists after
   a ``MapInject`` field-evolution step has run (``field.py``'s
   ``PortFiber``/``MountedFieldTopology``/``PortTransportEvidence``), which
   is a structurally different, later object than this module's
   ``StoryPhysicalBoundaryObservation``/``StoryPhysicalBoundaryEvent``; and
   (b) a lane-count shortfall there does not fail closed -- it zeroes one
   interval's geometry term and the computation continues. That is a
   downstream field-support computation's own internal accounting rule, not
   an admission gate on a raw sensory instant.
2. The ratified ``GLEW_LANGUAGE_WEAVE_PROFILE_v1.json``'s own
   ``event_support.full_rank_rule`` names this exact rule verbatim
   ("requires complete interval + at least 4 lived lanes; rank/lane
   shortfall zeroes geometry rather than fabricating a value") as belonging
   to operator id ``glew.exact_full_port_gram_event_support.v1`` --
   ``event_support.py``, confirmed above -- not to any boundary-observation
   operator.
3. ``GLEW_UPSTREAM_PROFILE_v1.json``'s ``fixed42_l6.lock`` names the
   "at_least_four_canonical_active_lanes..." wording as part of the Fixed-42
   L6 lock condition -- again a later full-field evaluation stage, not the
   boundary translation stage.
4. Section 9.4 of the governing spec itself distinguishes the two: "The
   current hardcoded 'at least four active lanes' language in the upstream
   profile must not be casually changed... L5 applicability still needs a
   ratified rule for genuinely inapplicable or unavailable ports." That is
   about L5 applicability and Fixed-42/event-support -- explicitly named as
   still-open, separately-ratified concerns -- not about this boundary
   owner's own admission decision.

This owner's own job, per section 9.1's actual requirements list, is
narrower and simpler: assemble whichever ports are genuinely real this
instant (touch/smell/taste always; sight/sound only with real captured
evidence) into one valid ``StoryPhysicalBoundaryEvent``, and return an
explicit unknown only when a port that was *expected* to produce real
evidence (touch/smell/taste always; sight/sound whenever the caller supplied
a fragment for them) instead failed. An instant with only touch/smell/taste
observed (sight and sound genuinely not captured this moment) is a valid
OBSERVED assembled event at this layer: "Sight and sound might genuinely be
absent this instant" (this module's own charge, per the task that produced
it) is exactly the case ``StoryPhysicalBoundaryEvent`` already tolerates,
and rejecting it here would be this module inventing a lane-count gate that
no ratified authority assigns to it. Whether such a 3-port instant later
contributes zero geometry inside ``event_support.py``, or is judged
NOT_APPLICABLE by a future L5 rule, is that later layer's own concern, not
this one's -- both of those remain explicitly open ratification gaps
(``l5_applicability.requires_explicit_ratification`` in the language weave
profile), and this module must not preempt them by fabricating its own
stricter threshold.

Causal window candidates
-------------------------
Section 9.1 also requires: "A complete causal window needs at least two
evolved frames because frozen L0-L4 evaluates change." This module's
``confirm_causal_window_candidate`` checks that an ordered sequence of at
least two already-assembled, already-verified ``StoryPhysicalBoundaryEvent``
objects carries strictly increasing, non-duplicate declared boundary times
-- the structural precondition for later feeding them, one at a time,
through the untouched ``evolve_story_chemistry_event`` /
``build_story_frozen_kernel_inputs`` pipeline. It does not itself evolve
anything.

One further real constraint worth recording precisely (found while reading
``build_story_frozen_kernel_inputs``, not guessed): that function requires
every output frame it is given to cover *every* port named in the mounted
manifest (``expected_ports = tuple(port.port_id for port in
runtime.manifest.ports)``, and ``tuple(output.port_id for output in frame)
!= expected_ports`` fails closed). So while THIS module's per-instant
event may legitimately carry only 3 or 4 of the 5 senses (sight/sound
genuinely absent), only a sequence of *five-port* instants can ever be
successfully evolved into frames that ``build_story_frozen_kernel_inputs``
will accept. That full-coverage requirement belongs to that existing,
tested function and to whatever future caller chooses to invoke it -- it is
not re-implemented or pre-checked here, per this module's explicit scope
limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping, Sequence

from .auditory_fragment_receipt import AuditoryFragmentReceipt
from .model import ReceiptError
from .sight_boundary import (
    VisionBoundaryTranslationStatus,
    translate_visual_fragment_to_boundary_observation,
)
from .somatic_boundary import (
    ChemistryPortBoundaryStatus,
    observe_smell_port_boundary,
    observe_taste_port_boundary,
    observe_touch_port_boundary,
)
from .sound_boundary import (
    AuditoryBoundaryTranslationStatus,
    translate_auditory_fragment_to_boundary_observation,
)
from .story_chemistry import (
    StoryChemistryRuntime,
    StoryPhysicalBoundaryEvent,
    StoryPhysicalBoundaryObservation,
)


class SixSenseBoundaryStatus(str, Enum):
    OBSERVED = "observed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SixSenseBoundaryResult:
    """Explicit result of assembling one instant's real per-sense evidence.

    ``event`` is populated only when ``status`` is ``OBSERVED``.
    ``active_port_ids`` names, in canonical sorted order, exactly the ports
    that contributed a real observation to ``event`` (always includes the
    touch/smell/taste ports when ``OBSERVED``; includes sight/sound only
    when a real fragment for that sense was actually supplied and
    translated).
    """

    status: SixSenseBoundaryStatus
    event: StoryPhysicalBoundaryEvent | None
    active_port_ids: tuple[str, ...]
    reason: str


def _unknown(reason: str) -> SixSenseBoundaryResult:
    return SixSenseBoundaryResult(
        status=SixSenseBoundaryStatus.UNKNOWN,
        event=None,
        active_port_ids=(),
        reason=reason,
    )


def observe_six_sense_boundary(
    runtime: StoryChemistryRuntime | None,
    *,
    event_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    visual_fragment_receipt: Mapping[str, object] | None = None,
    auditory_fragment_receipt: AuditoryFragmentReceipt | None = None,
    touch_descriptor: str | None = None,
    smell_descriptor: str | None = None,
    taste_descriptor: str | None = None,
) -> SixSenseBoundaryResult:
    """Assemble one real ``StoryPhysicalBoundaryEvent`` for one instant.

    ``runtime`` must be an already-mounted ``StoryChemistryRuntime`` (see
    ``story_chemistry.mount_story_chemistry`` /
    ``mount_packaged_production_story_chemistry``). Its ``.manifest`` is
    passed to the sight/sound translators; the runtime itself is passed to
    the touch/smell/taste translators.

    ``visual_fragment_receipt`` / ``auditory_fragment_receipt`` are ``None``
    when no real capture happened for that sense this instant -- a
    legitimate absence, not an error; that port is simply left out of the
    assembled event. When one IS supplied, real evidence was expected, and
    a translation failure (tamper, zero events, wrong manifest, ...)
    propagates as an explicit top-level ``UNKNOWN`` rather than being
    silently dropped.

    ``touch_descriptor`` / ``smell_descriptor`` / ``taste_descriptor`` are
    always translated (``None`` means "no active event", which
    ``somatic_boundary.py`` already turns into a real zero-flux
    natural-decay observation -- not a missing-evidence case). Because
    these three lanes are expected to produce real evidence on every call,
    any ``UNKNOWN`` from one of them is a genuine failure and propagates as
    an explicit top-level ``UNKNOWN``.

    Returns ``OBSERVED`` with a real, self-verifying, canonically sorted
    ``StoryPhysicalBoundaryEvent`` (3, 4, or 5 observations, touch/smell/
    taste always present, sight/sound present only when real evidence was
    supplied and translated) once every attempted port succeeds. Never
    raises past this boundary.
    """

    manifest = runtime.manifest if isinstance(runtime, StoryChemistryRuntime) else None
    observations: list[StoryPhysicalBoundaryObservation] = []

    if visual_fragment_receipt is not None:
        sight_result = translate_visual_fragment_to_boundary_observation(
            visual_fragment_receipt,
            manifest=manifest,
            event_id=event_id,
            observation_id=f"{event_id}:sight",
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
        if sight_result.status is not VisionBoundaryTranslationStatus.OBSERVED:
            return _unknown(
                "a visual fragment was supplied for this instant but sight "
                f"boundary translation failed: {sight_result.reason}"
            )
        observations.append(sight_result.observation)

    if auditory_fragment_receipt is not None:
        sound_result = translate_auditory_fragment_to_boundary_observation(
            auditory_fragment_receipt,
            manifest=manifest,
            event_id=event_id,
            observation_id=f"{event_id}:sound",
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
        if sound_result.status is not AuditoryBoundaryTranslationStatus.OBSERVED:
            return _unknown(
                "an auditory fragment was supplied for this instant but "
                f"sound boundary translation failed: {sound_result.reason}"
            )
        observations.append(sound_result.observation)

    for lane_name, descriptor, observe in (
        ("touch", touch_descriptor, observe_touch_port_boundary),
        ("smell", smell_descriptor, observe_smell_port_boundary),
        ("taste", taste_descriptor, observe_taste_port_boundary),
    ):
        somatic_result = observe(
            runtime,
            event_id=event_id,
            observation_id=f"{event_id}:{lane_name}",
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            active_descriptor=descriptor,
        )
        if somatic_result.status is not ChemistryPortBoundaryStatus.OBSERVED:
            return _unknown(
                f"{lane_name} boundary observation failed though this lane "
                f"always carries real emulator state: {somatic_result.reason}"
            )
        observations.append(somatic_result.observation)

    ordered_observations = tuple(
        sorted(observations, key=lambda observation: observation.port_id)
    )
    try:
        event = StoryPhysicalBoundaryEvent(
            event_id=event_id,
            observations=ordered_observations,
        )
        event.verify()
    except ReceiptError as exc:
        return _unknown(f"assembled boundary event failed self-verification: {exc}")

    return SixSenseBoundaryResult(
        status=SixSenseBoundaryStatus.OBSERVED,
        event=event,
        active_port_ids=tuple(
            observation.port_id for observation in ordered_observations
        ),
        reason=(
            f"assembled {len(ordered_observations)} real per-instant port "
            "observations into one verified boundary event"
        ),
    )


class CausalWindowCandidateStatus(str, Enum):
    CANDIDATE = "causal_window_candidate"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CausalWindowCandidateResult:
    """Explicit result of confirming an ordered sequence of real per-instant
    boundary events is a genuine causal-window candidate.

    ``events``/``source_time_starts`` are populated (in the caller's given
    order) only when ``status`` is ``CANDIDATE``.
    """

    status: CausalWindowCandidateStatus
    events: tuple[StoryPhysicalBoundaryEvent, ...]
    source_time_starts: tuple[Fraction, ...]
    reason: str


def _causal_unknown(reason: str) -> CausalWindowCandidateResult:
    return CausalWindowCandidateResult(
        status=CausalWindowCandidateStatus.UNKNOWN,
        events=(),
        source_time_starts=(),
        reason=reason,
    )


def confirm_causal_window_candidate(
    events: Sequence[StoryPhysicalBoundaryEvent],
) -> CausalWindowCandidateResult:
    """Confirm a real, strictly time-ordered sequence of at least two
    already-assembled ``StoryPhysicalBoundaryEvent`` objects.

    This performs no chemistry evolution: it does not call
    ``evolve_story_chemistry_event`` or ``build_story_frozen_kernel_inputs``.
    It only confirms the structural precondition those functions require
    before a caller invokes them one event at a time: every event is itself
    a real, self-verifying, canonically-ordered boundary event; every
    observation inside one event shares the same declared boundary window
    (this owner always builds them that way; this checker verifies it
    rather than assuming it); event ids are unique; and the declared
    ``source_time_start`` strictly increases, with no duplicate or
    out-of-order instant, across the sequence exactly as given.

    Fails closed (returns ``UNKNOWN``, never raises) for: fewer than two
    events; an untyped or self-inconsistent event; an event whose own
    observations disagree about their declared boundary window; duplicate
    event ids; or a non-strictly-increasing ``source_time_start`` sequence.
    """

    try:
        if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
            raise ReceiptError(
                "causal window candidate requires a real sequence of boundary events"
            )
        if len(events) < 2:
            raise ReceiptError(
                "a causal window candidate requires at least two per-instant "
                "boundary events -- frozen L0-L4 evaluates change, not one instant"
            )
        event_ids: list[str] = []
        starts: list[Fraction] = []
        for event in events:
            if not isinstance(event, StoryPhysicalBoundaryEvent):
                raise ReceiptError(
                    "causal window candidate sequence contains an untyped event"
                )
            event.verify()
            observation_starts = {
                observation.source_time_start for observation in event.observations
            }
            observation_ends = {
                observation.source_time_end for observation in event.observations
            }
            if len(observation_starts) != 1 or len(observation_ends) != 1:
                raise ReceiptError(
                    "every observation inside one instant must share the same "
                    "declared boundary window; this event's ports disagree"
                )
            event_ids.append(event.event_id)
            starts.append(next(iter(observation_starts)))
        if len(set(event_ids)) != len(event_ids):
            raise ReceiptError(
                "causal window candidate events must have unique event_id values"
            )
        for earlier, later in zip(starts, starts[1:]):
            if later <= earlier:
                raise ReceiptError(
                    "causal window candidate requires strictly increasing "
                    "source_time_start across the sequence; found a duplicate "
                    "or out-of-order instant"
                )
    except ReceiptError as exc:
        return _causal_unknown(str(exc))

    return CausalWindowCandidateResult(
        status=CausalWindowCandidateStatus.CANDIDATE,
        events=tuple(events),
        source_time_starts=tuple(starts),
        reason=(
            f"{len(events)} real per-instant boundary events are strictly "
            "time-ordered and form a genuine causal window candidate"
        ),
    )


__all__ = (
    "CausalWindowCandidateResult",
    "CausalWindowCandidateStatus",
    "SixSenseBoundaryResult",
    "SixSenseBoundaryStatus",
    "confirm_causal_window_candidate",
    "observe_six_sense_boundary",
)
