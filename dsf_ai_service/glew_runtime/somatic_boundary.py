"""Live boundary owner for the touch, smell, and taste chemistry ports.

This module is the first small slice of the "Live six-sense boundary owner"
required by section 9.1 of
``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``,
scoped narrowly to the three somatic/chemical senses named there:

    "Touch, smell, and taste use the robust emulator's actual states; quiet
    input must evolve through natural decay rather than becoming an invented
    descriptor."

The "robust emulator" is ``chemical_receiver.py`` / ``story_chemistry.py``
themselves -- already real, already tested, already mounted from
``profiles/production_virtual_story_chemistry_profile_v1.json``.  This module
does not add a second emulator.  It reads a touch/smell/taste port's CURRENT
mounted ``ReceiverState`` from a live ``StoryChemistryRuntime`` and produces a
receipted ``StoryPhysicalBoundaryObservation`` for exactly that port, for one
of two genuinely real situations:

    1. a real active touch/smell/taste event was reported for this port
       (``active_descriptor`` names a real, legitimate word for that sense),
       producing a real nonzero signed native flux; or
    2. no active input was reported (``active_descriptor`` is ``None``),
       producing a real, valid, exact-zero flux observation -- this is NOT a
       missing-evidence case.  Chemistry's own math
       (``chemical_receiver.evolve_chemical_receiver``) still relaxes any
       existing active/desensitized mass toward rest through the mounted
       deactivation/desensitization/recovery rates even when the boundary
       flux driving new activation is exactly zero; feeding this module's
       zero-flux observations through ``evolve_story_chemistry_event`` over
       successive intervals is what makes that natural decay real (see
       ``tests/glew_runtime/test_somatic_boundary.py`` for a directly
       measured proof).

Neither case is ever fabricated.  A port that has never been mounted at all,
a ``port_id`` absent from the mounted manifest, or an ``active_descriptor``
that is not a real recognized word for that sense, each returns the explicit
``ChemistryPortBoundaryStatus.UNKNOWN`` -- never a coerced or invented flux.

Judgment call requiring review -- the descriptor/flux-magnitude boundary
----------------------------------------------------------------------
There is no existing GLEW-native "descriptor -> flux magnitude" derivation
anywhere in ``glew_runtime``.  ``story_chemistry.py`` says so explicitly in
its own module docstring ("It does not turn words, descriptors, hashes, or
vocabulary entries into sensory values"), and the ratified
``GLEW_LANGUAGE_WEAVE_PROFILE_v1.json`` records this as a verified,
already-confirmed anti-pattern absence ("no port derived from a word label or
hash (confirmed zero derivation logic in story_chemistry.py /
story_native_replay.py)").

The only descriptor -> numeric-value mapping that exists anywhere in this
repository for touch/smell/taste is the legacy v5 Atlas mechanism in
``dsf_ai_service/substrate/sensory_generators.py``
(``TOUCH_LIBRARY`` / ``SMELL_LIBRARY`` / ``TASTE_LIBRARY`` ->
``generate_*_waveform`` -> ``Krimelack`` winding -> ``chi``).  That pipeline
is float-based, seeds numpy noise from a hash of the descriptor's characters,
and produces the legacy chi/motif representation -- it is exactly the
"word-derived procedural sensory placeholder" mechanism the governing
handoff doc's mandatory architecture-honesty gate lists as a mechanism that
"must not be extended" into this rearchitecture, and reusing it here would
directly recreate the prohibited patterns "generating sight, sound, touch,
smell, or taste from a word hash" and "treating static descriptor
dictionaries as lived sensory truth" from the ratified profile's
``prohibitions`` list -- just under a new file name.

Given that, this module reuses ONLY the *word legitimacy* fact from those
libraries (``frozenset(TOUCH_LIBRARY)`` etc. -- i.e. "is 'warm' a real,
already-recognized touch word in this codebase," a plain vocabulary-membership
check) and never their per-word numeric intensity profiles or their
waveform/hash/Krimelack machinery. For the actual flux MAGNITUDE of a real
reported active event, this module uses ``CANONICAL_ACTIVE_EVENT_FLUX``
(exactly ``Fraction(1)``) uniformly for every legitimate descriptor on a
port. That value is not invented here: every port's own mounted
``native_signal_unit_authority`` in the production profile defines its unit
this way verbatim ("one boundary-flux unit is defined as the flux producing
unit R-to-A propensity in a fully available virtual receiver"). Because no
ratified GLEW authority assigns a *different* magnitude to *specific*
legitimate words (e.g. "warm" vs "hot"), doing so here would itself be an
invented per-word intensity map -- exactly what this module exists to avoid.
A future session may ratify a real per-descriptor magnitude authority; until
then, "one real reported active event of a legitimate kind" maps to exactly
one canonical unit of flux, and "no reported event" maps to exactly zero.
This is the one design decision in this module that most needs an explicit
human sign-off; everything else here is direct reuse of already-ratified
mechanisms.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from dsf_ai_service.substrate.sensory_generators import (
    SMELL_LIBRARY,
    TASTE_LIBRARY,
    TOUCH_LIBRARY,
)

from .chemical_receiver import CertifiedReceiverState, ExactReceiverState, ReceiverState
from .model import ReceiptError, receipt_sha256, require_fraction, require_identifier
from .story_chemistry import (
    StoryChemistryRuntime,
    StoryPhysicalBoundaryObservation,
    StoryPortChemicalAuthority,
    story_boundary_observation_receipt_payload,
)


SOMATIC_BOUNDARY_PROVENANCE_SCHEMA = "glew.somatic_boundary.provenance.v1"

# The three somatic/chemical senses this module owns, and their exact
# mounted port ids (PRODUCTION_STORY_PORT_LANES in story_chemistry.py).
# Sight and sound are deliberately excluded: per the governing spec they use
# their actual observed/emulated activity through a different transport
# (an external legacy sensor path translation), not this module.
SOMATIC_LANE_TO_PORT_ID: dict[str, str] = {
    "smell": "story-smell.native-port-0",
    "taste": "story-taste.native-port-0",
    "touch": "story-touch.native-port-0",
}
PORT_ID_TO_SOMATIC_LANE: dict[str, str] = {
    port_id: lane for lane, port_id in SOMATIC_LANE_TO_PORT_ID.items()
}

# Real, already-existing legitimate touch/smell/taste vocabulary, reused as a
# membership check only.  See "Judgment call" in the module docstring for why
# only the key sets -- never the numeric profiles or generator machinery --
# are reused from dsf_ai_service/substrate/sensory_generators.py.
_LEGITIMATE_DESCRIPTORS_BY_LANE: dict[str, frozenset[str]] = {
    "touch": frozenset(TOUCH_LIBRARY),
    "smell": frozenset(SMELL_LIBRARY),
    "taste": frozenset(TASTE_LIBRARY),
}

# "One boundary-flux unit" exactly as each somatic port's own mounted
# native_signal_unit_authority already defines it (see module docstring).
# Not a per-descriptor intensity; the same canonical magnitude applies to
# every real legitimate active-event report on a given port.
CANONICAL_ACTIVE_EVENT_FLUX = Fraction(1)


class ChemistryPortBoundaryStatus(str, Enum):
    OBSERVED = "observed"
    UNKNOWN = "unknown"


class SomaticBoundaryEventKind(str, Enum):
    """Which of the two genuinely real situations this observation reports."""

    ACTIVE_DESCRIPTOR_EVENT = "active_descriptor_event"
    QUIESCENT_NATURAL_DECAY = "quiescent_natural_decay"


@dataclass(frozen=True, slots=True)
class ChemistryPortBoundaryResult:
    """Explicit-unknown result shape for one somatic boundary observation.

    ``observation`` is populated only when ``status`` is ``OBSERVED``.  When
    ``status`` is ``UNKNOWN`` every other payload field is ``None`` except
    ``port_id`` and ``active_descriptor``, which are retained verbatim from
    the request for diagnosis -- they are the caller's inputs, not fabricated
    evidence.
    """

    status: ChemistryPortBoundaryStatus
    port_id: str
    active_descriptor: str | None
    lane_id: str | None
    event_kind: SomaticBoundaryEventKind | None
    observation: StoryPhysicalBoundaryObservation | None
    reason: str


def _unknown(
    *,
    port_id: str,
    active_descriptor: str | None,
    reason: str,
) -> ChemistryPortBoundaryResult:
    return ChemistryPortBoundaryResult(
        status=ChemistryPortBoundaryStatus.UNKNOWN,
        port_id=port_id,
        active_descriptor=active_descriptor,
        lane_id=None,
        event_kind=None,
        observation=None,
        reason=reason,
    )


def _somatic_boundary_provenance_payload(
    *,
    event_id: str,
    observation_id: str,
    port_id: str,
    lane_id: str,
    event_kind: SomaticBoundaryEventKind,
    active_descriptor: str | None,
) -> bytes:
    return json.dumps(
        {
            "active_descriptor": active_descriptor,
            "event_id": require_identifier(event_id, "somatic boundary event_id"),
            "event_kind": event_kind.value,
            "lane_id": require_identifier(lane_id, "somatic boundary lane_id"),
            "observation_id": require_identifier(
                observation_id, "somatic boundary observation_id"
            ),
            "port_id": require_identifier(port_id, "somatic boundary port_id"),
            "schema": SOMATIC_BOUNDARY_PROVENANCE_SCHEMA,
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _mounted_somatic_port(
    *,
    runtime: StoryChemistryRuntime | None,
    port_id: str,
    active_descriptor: str | None,
) -> tuple[StoryPortChemicalAuthority, ReceiverState, str] | ChemistryPortBoundaryResult:
    """Resolve the real mounted port authority, its lane, and its current
    state, or return the explicit-unknown result for every way that can
    genuinely fail closed."""

    if not isinstance(runtime, StoryChemistryRuntime):
        return _unknown(
            port_id=port_id,
            active_descriptor=active_descriptor,
            reason="chemistry runtime has never been mounted; no state exists yet",
        )
    if not isinstance(port_id, str) or not port_id:
        return _unknown(
            port_id=port_id if isinstance(port_id, str) else "",
            active_descriptor=active_descriptor,
            reason="port_id must be a nonempty string",
        )
    lane_id = PORT_ID_TO_SOMATIC_LANE.get(port_id)
    if lane_id is None:
        return _unknown(
            port_id=port_id,
            active_descriptor=active_descriptor,
            reason=(
                "port_id is not one of the mounted touch/smell/taste ports "
                "this boundary owner covers"
            ),
        )
    try:
        port = runtime.manifest.port(port_id)
    except ReceiptError as exc:
        return _unknown(
            port_id=port_id,
            active_descriptor=active_descriptor,
            reason=f"port not present in the mounted manifest: {exc}",
        )
    try:
        state = runtime.state(port_id)
    except ReceiptError as exc:
        return _unknown(
            port_id=port_id,
            active_descriptor=active_descriptor,
            reason=f"port has no mounted state: {exc}",
        )
    if not isinstance(state, (ExactReceiverState, CertifiedReceiverState)):
        return _unknown(
            port_id=port_id,
            active_descriptor=active_descriptor,
            reason="mounted port state is not a typed receiver state",
        )
    return port, state, lane_id


def observe_chemistry_port_boundary(
    runtime: StoryChemistryRuntime | None,
    port_id: str,
    *,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    active_descriptor: str | None = None,
) -> ChemistryPortBoundaryResult:
    """Build one real ``StoryPhysicalBoundaryObservation`` for a somatic port.

    ``runtime`` must be an already-mounted ``StoryChemistryRuntime`` (see
    ``mount_story_chemistry`` / ``mount_packaged_production_story_chemistry``
    in ``story_chemistry.py``).  ``port_id`` must name one of the three
    mounted touch/smell/taste ports.  ``source_time_start`` must equal the
    port's CURRENT mounted ``source_time`` -- an observation can only begin
    where the port's real evolving state actually is, never at an invented
    instant.  ``source_time_end`` must be strictly later.

    When ``active_descriptor`` is a real, legitimate word for this port's
    sense (checked against the real vocabulary in
    ``dsf_ai_service/substrate/sensory_generators.py``), the observation
    carries a real nonzero ``signed_native_flux`` (see
    ``CANONICAL_ACTIVE_EVENT_FLUX`` and the module docstring's judgment-call
    note). When it is ``None``, the observation carries exact zero flux:
    real evidence that no active input was reported, letting the mounted
    chemistry's own deactivation/desensitization/recovery rates continue
    relaxing any existing active/desensitized mass toward rest. When
    ``active_descriptor`` is given but is not a real legitimate word for this
    port, the result is UNKNOWN -- it is never silently coerced into zero or
    into a fabricated flux.
    """

    resolved = _mounted_somatic_port(
        runtime=runtime, port_id=port_id, active_descriptor=active_descriptor
    )
    if isinstance(resolved, ChemistryPortBoundaryResult):
        return resolved
    port, state, lane_id = resolved

    try:
        require_fraction(source_time_start, "somatic boundary source_time_start")
        require_fraction(source_time_end, "somatic boundary source_time_end")
    except ReceiptError as exc:
        return _unknown(port_id=port_id, active_descriptor=active_descriptor, reason=str(exc))

    if source_time_start != state.source_time:
        return _unknown(
            port_id=port_id,
            active_descriptor=active_descriptor,
            reason=(
                "source_time_start does not match the port's current mounted "
                f"source_time ({state.source_time}); an observation can only "
                "begin where the port's real evolving state currently is"
            ),
        )
    if source_time_end <= source_time_start:
        return _unknown(
            port_id=port_id,
            active_descriptor=active_descriptor,
            reason="source_time_end must be strictly later than source_time_start",
        )

    if active_descriptor is None:
        event_kind = SomaticBoundaryEventKind.QUIESCENT_NATURAL_DECAY
        signed_native_flux = Fraction(0)
    else:
        if not isinstance(active_descriptor, str) or not active_descriptor:
            return _unknown(
                port_id=port_id,
                active_descriptor=active_descriptor,
                reason="active_descriptor must be a nonempty string or None",
            )
        legitimate_words = _LEGITIMATE_DESCRIPTORS_BY_LANE[lane_id]
        if active_descriptor not in legitimate_words:
            return _unknown(
                port_id=port_id,
                active_descriptor=active_descriptor,
                reason=(
                    f"{active_descriptor!r} is not a real legitimate {lane_id} "
                    "word for this port; refusing to fabricate a flux value"
                ),
            )
        event_kind = SomaticBoundaryEventKind.ACTIVE_DESCRIPTOR_EVENT
        signed_native_flux = CANONICAL_ACTIVE_EVENT_FLUX

    try:
        provenance_payload = _somatic_boundary_provenance_payload(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port_id,
            lane_id=lane_id,
            event_kind=event_kind,
            active_descriptor=active_descriptor,
        )
        provenance_receipt_sha256 = receipt_sha256(provenance_payload)
        observation_payload = story_boundary_observation_receipt_payload(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            signed_native_flux=signed_native_flux,
            native_flux_unit=port.native_signal_unit,
            provenance_receipt_sha256=provenance_receipt_sha256,
        )
        observation = StoryPhysicalBoundaryObservation(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            signed_native_flux=signed_native_flux,
            native_flux_unit=port.native_signal_unit,
            provenance_receipt_sha256=provenance_receipt_sha256,
            provenance_receipt_payload=provenance_payload,
            observation_receipt_sha256=receipt_sha256(observation_payload),
            observation_receipt_payload=observation_payload,
        )
        observation.verify()
    except ReceiptError as exc:
        return _unknown(port_id=port_id, active_descriptor=active_descriptor, reason=str(exc))

    return ChemistryPortBoundaryResult(
        status=ChemistryPortBoundaryStatus.OBSERVED,
        port_id=port_id,
        active_descriptor=active_descriptor,
        lane_id=lane_id,
        event_kind=event_kind,
        observation=observation,
        reason=(
            "real active descriptor event observed"
            if event_kind is SomaticBoundaryEventKind.ACTIVE_DESCRIPTOR_EVENT
            else "no active input reported; genuine zero-flux natural-decay observation"
        ),
    )


def observe_touch_port_boundary(
    runtime: StoryChemistryRuntime | None,
    *,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    active_descriptor: str | None = None,
) -> ChemistryPortBoundaryResult:
    """``observe_chemistry_port_boundary`` fixed to the mounted touch port."""

    return observe_chemistry_port_boundary(
        runtime,
        SOMATIC_LANE_TO_PORT_ID["touch"],
        event_id=event_id,
        observation_id=observation_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        active_descriptor=active_descriptor,
    )


def observe_smell_port_boundary(
    runtime: StoryChemistryRuntime | None,
    *,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    active_descriptor: str | None = None,
) -> ChemistryPortBoundaryResult:
    """``observe_chemistry_port_boundary`` fixed to the mounted smell port."""

    return observe_chemistry_port_boundary(
        runtime,
        SOMATIC_LANE_TO_PORT_ID["smell"],
        event_id=event_id,
        observation_id=observation_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        active_descriptor=active_descriptor,
    )


def observe_taste_port_boundary(
    runtime: StoryChemistryRuntime | None,
    *,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    active_descriptor: str | None = None,
) -> ChemistryPortBoundaryResult:
    """``observe_chemistry_port_boundary`` fixed to the mounted taste port."""

    return observe_chemistry_port_boundary(
        runtime,
        SOMATIC_LANE_TO_PORT_ID["taste"],
        event_id=event_id,
        observation_id=observation_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        active_descriptor=active_descriptor,
    )


__all__ = (
    "CANONICAL_ACTIVE_EVENT_FLUX",
    "PORT_ID_TO_SOMATIC_LANE",
    "SOMATIC_BOUNDARY_PROVENANCE_SCHEMA",
    "SOMATIC_LANE_TO_PORT_ID",
    "ChemistryPortBoundaryResult",
    "ChemistryPortBoundaryStatus",
    "SomaticBoundaryEventKind",
    "observe_chemistry_port_boundary",
    "observe_smell_port_boundary",
    "observe_taste_port_boundary",
    "observe_touch_port_boundary",
)
