"""Live SIGHT-port boundary translator.

This module is the first concrete instance of the "live six-sense boundary
owner" required by
``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
section 9.1: it converts one already-captured, already-receipted native
visual observation into a GLEW
:class:`~dsf_ai_service.glew_runtime.story_chemistry.StoryPhysicalBoundaryObservation`
for the mounted production vision port.

Real visual evidence enters this module in exactly the shape produced today
by the legacy (non-GLEW) sight path:

* ``dsf_ai_service/visual_krimelack.py``'s ``view_picture()`` runs a real
  saccade/fixation simulation over an actually-captured camera frame and
  returns one ``VisualPerceptFragment`` per fixation, each carrying
  ``event_records``: the fragment's real ``(t, dw, s)`` photoreceptor
  phase-winding crossings (tick, signed winding direction, and the real
  normalized-optical-intensity signal present at that crossing).
* ``visual_krimelack.visual_fragment_receipt()`` seals that fragment into a
  tamper-evident dict receipt (``guala.native_sight_fragment.v1``) with its
  own ``receipt_sha256``. That receipt explicitly self-labels its ``dsf``
  field ``{"status": "unknown", ...}`` -- it carries real sensor evidence,
  not a GLEW flux.

This module is the translation step that closes that gap for the vision
port only: it re-verifies the native receipt's own tamper check, derives a
real, non-fabricated ``signed_native_flux`` Fraction from the receipt's
actual events, and builds a fully self-verifying
``StoryPhysicalBoundaryObservation`` bound to the mounted production
chemistry manifest's real vision port id and native flux unit.

It does not decide when a turn's boundary event closes, does not choose the
observation's declared time window (that is supplied by the caller -- the
still-unbuilt six-sense boundary owner -- from the shared experience
window's own clock), and does not mount or extend any receipt registry.
Those remain out of scope for this translator.

Fail-closed discipline, matching the rest of ``glew_runtime``: missing,
malformed, tamper-failed, or event-empty input never raises past this
module's public entry point and never fabricates a flux value. It returns
the explicit "unknown" result shape instead (mirroring, e.g.,
``chemical_receiver.py``'s ``ReceiverEvolutionResult``/``_unknown()`` and
``event_support.py``'s ``EventSupportEvaluationStatus``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.visual_krimelack import validate_visual_fragment_receipt

from .model import (
    ReceiptError,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from .story_chemistry import (
    PRODUCTION_STORY_PORT_LANES,
    SignedStoryChemistryManifest,
    StoryPhysicalBoundaryObservation,
    story_boundary_observation_receipt_payload,
)

SIGHT_BOUNDARY_PROVENANCE_SCHEMA = (
    "glew.sight_boundary.native_visual_fragment_provenance.v1"
)
_SIGHT_LANE_NAME = "sight"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def production_sight_port_id() -> str:
    """Return the real registered vision port id from the production lane map.

    This reads the same ``PRODUCTION_STORY_PORT_LANES`` tuple that
    ``story_chemistry.py`` itself uses to bind lane names to port ids -- it
    is not a fresh guess at the string, and it stays correct automatically
    if that tuple is ever amended.
    """

    for port_id, lane in PRODUCTION_STORY_PORT_LANES:
        if lane == _SIGHT_LANE_NAME:
            return port_id
    raise ReceiptError(
        "production story port lanes do not name a sight port"
    )


class VisionBoundaryTranslationStatus(str, Enum):
    OBSERVED = "observed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class VisionBoundaryTranslationResult:
    """Explicit result of translating one native visual fragment receipt.

    ``observation`` is populated only when ``status`` is ``OBSERVED``; it
    is always ``None`` under ``UNKNOWN`` -- there is no "last known good"
    boundary observation to retain here (unlike a stateful receiver), because
    each call translates one independent, already-closed fixation.
    """

    status: VisionBoundaryTranslationStatus
    observation: StoryPhysicalBoundaryObservation | None
    reason: str


def _unknown(reason: str) -> VisionBoundaryTranslationResult:
    return VisionBoundaryTranslationResult(
        status=VisionBoundaryTranslationStatus.UNKNOWN,
        observation=None,
        reason=reason,
    )


def native_sight_boundary_provenance_receipt_payload(
    *,
    event_id: str,
    observation_id: str,
    port_id: str,
    visual_fragment_schema: str,
    visual_fragment_receipt_sha256: str,
    source_id: str,
    born_tick: int,
    fixation_coord: tuple[int, int],
    winding_count: int,
    event_count: int,
) -> bytes:
    """Canonical bytes binding one boundary observation to the exact native
    visual fragment receipt it was translated from.

    This is the auditable chain-of-custody artifact: it embeds the native
    receipt's own verified ``receipt_sha256`` plus enough of the receipt's
    identifying, already-validated fields (source, fixation, winding count,
    event count) to bind this specific observation to that specific sealed
    fragment and no other. It is never a synthesized or free-floating claim.
    """

    return _canonical_bytes(
        {
            "event_id": require_identifier(event_id, "sight boundary event_id"),
            "observation_id": require_identifier(
                observation_id, "sight boundary observation_id"
            ),
            "port_id": require_identifier(port_id, "sight boundary port_id"),
            "schema": SIGHT_BOUNDARY_PROVENANCE_SCHEMA,
            "source_visual_fragment": {
                "born_tick": int(born_tick),
                "event_count": int(event_count),
                "fixation_coord": [
                    int(fixation_coord[0]),
                    int(fixation_coord[1]),
                ],
                "receipt_sha256": sha256_digest(
                    visual_fragment_receipt_sha256,
                    "native visual fragment receipt_sha256",
                ),
                "schema": require_identifier(
                    visual_fragment_schema, "native visual fragment schema"
                ),
                "source_id": require_identifier(
                    source_id, "native visual fragment source_id"
                ),
                "winding_count": int(winding_count),
            },
        }
    )


def _derive_signed_native_flux(events: list) -> Fraction:
    """Net winding direction weighted by real signal magnitude, averaged
    over every real crossing this fixation actually produced.

    Each admitted event is one real photoreceptor phase-winding crossing:
    ``dw`` is the exact signed crossing direction actually recorded (+1
    forward wind, -1 reverse wind) and ``s`` is the exact real normalized
    optical intensity (calibrated to [0, 1]) present at that crossing.
    ``Fraction(dw)`` and ``Fraction(s)`` are the exact rational values of
    the real recorded int/float -- Python's ``Fraction(float)`` constructor
    returns the exact binary64 value, never a rounded or nominal stand-in,
    so no precision is fabricated anywhere in this sum.

    ``dw * s`` for one event is already an exact value in the closed
    interval [-1, 1] (dw in {-1, +1}, s in [0, 1]). The arithmetic mean of
    N such bounded values is itself in [-1, 1] by construction -- with no
    clipping, no rescaling, and no reference to anything but the events
    actually present. This matches the vision port's own registered,
    already-"normalized" native flux unit
    (``virtual-normalized-optical-boundary-flux``, read from the mounted
    production chemistry profile, never hardcoded here) and mirrors the
    same bounded-mean shape the sibling auditory-port translator uses for
    its own registered normalized unit.

    This is deliberately NOT divided by the caller-declared observation
    window (``source_time_end - source_time_start``), for two independent
    reasons:

    1. Physical: ``story_chemistry``'s own profile defines susceptibility
       as producing unit propensity "per structural-time unit" from one
       flux unit, and ``chemical_receiver.py`` integrates that propensity
       across the interval's real ``delta`` exactly once, at
       ``(generator_matrix * delta).exp()``. Pre-dividing this flux by the
       same declared ``delta`` would make that ``delta`` algebraically
       cancel out of the eventual transition matrix entirely -- silently
       making the caller's real declared duration physically inert. Flux
       must be a duration-independent intrinsic reading of the sensor;
       the one real multiplication by elapsed time belongs to the chemical
       evolution step, not this translator.
    2. Evidentiary: the same real (t, dw, s) events must translate to the
       same signed_native_flux regardless of what boundary-event window a
       caller later chooses to declare around them. Making the flux a
       function of an arbitrary externally supplied window would let
       unrelated bookkeeping metadata change what is supposed to be a pure
       reading of real sensor evidence -- itself a quiet fabrication
       vector.

    This also never touches the fragment's raw tick coordinates
    (``event["t"]``) at all: those are a dimensionless simulation-tick
    coordinate local to one fixation, not a physical time base, and no
    ratified tick-to-native-time-unit conversion exists for this
    translator to invent one from.

    Caller must already have established ``events`` is nonempty -- the
    zero-event case is a distinct, explicit UNKNOWN outcome handled before
    this function is ever called, since a mean over zero terms is not a
    well-defined value.
    """

    weighted_sum = sum(
        (Fraction(int(event["dw"])) * Fraction(event["s"]) for event in events),
        start=Fraction(0),
    )
    return weighted_sum / len(events)


def translate_visual_fragment_to_boundary_observation(
    fragment_receipt: Mapping[str, object] | None,
    *,
    manifest: SignedStoryChemistryManifest,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> VisionBoundaryTranslationResult:
    """Translate one authenticated native visual fragment receipt into a
    ``StoryPhysicalBoundaryObservation`` for the mounted production sight port.

    ``fragment_receipt`` must be the dict produced by
    ``dsf_ai_service.visual_krimelack.visual_fragment_receipt()`` (or an
    exact copy of one) for a single real fixation. ``manifest`` must be a
    mounted ``SignedStoryChemistryManifest`` that registers the production
    vision port (e.g. from
    ``story_chemistry.mount_packaged_production_story_chemistry()``).
    ``source_time_start``/``source_time_end`` are the real declared
    observation window for this boundary event, in the port's own
    calibrated time unit; this function does not choose or invent that
    window.

    Fails closed -- returns the explicit UNKNOWN result, never raises past
    this boundary, and never fabricates a flux value -- when:

    * ``fragment_receipt`` is missing, malformed, or fails its own
      tamper/shape check (``validate_visual_fragment_receipt``);
    * the fragment receipt has zero real events (no non-fabricated flux
      can be derived from an empty fixation);
    * the declared observation window is not a strictly positive-duration
      ``Fraction``;
    * the mounted manifest does not register the production sight port.
    """

    try:
        if not validate_visual_fragment_receipt(fragment_receipt):
            raise ReceiptError(
                "native visual fragment receipt failed its own tamper/shape check"
            )
        events = fragment_receipt["events"]
        if not events:
            raise ReceiptError(
                "native visual fragment has zero events; refusing to "
                "fabricate a flux for an empty fixation"
            )
        if not isinstance(manifest, SignedStoryChemistryManifest):
            raise ReceiptError("mounted story chemistry manifest is missing")
        port_id = production_sight_port_id()
        port_authority = manifest.port(port_id)
        require_fraction(source_time_start, "sight boundary source_time_start")
        require_fraction(source_time_end, "sight boundary source_time_end")
        if source_time_end - source_time_start <= 0:
            raise ReceiptError(
                "sight boundary observation must have a positive real duration"
            )

        signed_native_flux = _derive_signed_native_flux(events)

        provenance_payload = native_sight_boundary_provenance_receipt_payload(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port_id,
            visual_fragment_schema=str(fragment_receipt["schema"]),
            visual_fragment_receipt_sha256=str(fragment_receipt["receipt_sha256"]),
            source_id=str(fragment_receipt["source_id"]),
            born_tick=int(fragment_receipt["born_tick"]),
            fixation_coord=tuple(fragment_receipt["fixation_coord"]),
            winding_count=int(fragment_receipt["winding_count"]),
            event_count=len(events),
        )
        provenance_receipt_sha256 = receipt_sha256(provenance_payload)

        observation_payload = story_boundary_observation_receipt_payload(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            signed_native_flux=signed_native_flux,
            native_flux_unit=port_authority.native_signal_unit,
            provenance_receipt_sha256=provenance_receipt_sha256,
        )
        observation = StoryPhysicalBoundaryObservation(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            signed_native_flux=signed_native_flux,
            native_flux_unit=port_authority.native_signal_unit,
            provenance_receipt_sha256=provenance_receipt_sha256,
            provenance_receipt_payload=provenance_payload,
            observation_receipt_sha256=receipt_sha256(observation_payload),
            observation_receipt_payload=observation_payload,
        )
        observation.verify()
    except ReceiptError as exc:
        return _unknown(str(exc))

    return VisionBoundaryTranslationResult(
        status=VisionBoundaryTranslationStatus.OBSERVED,
        observation=observation,
        reason=(
            "native visual fragment receipt translated into a sight "
            "boundary observation"
        ),
    )


__all__ = (
    "SIGHT_BOUNDARY_PROVENANCE_SCHEMA",
    "VisionBoundaryTranslationResult",
    "VisionBoundaryTranslationStatus",
    "native_sight_boundary_provenance_receipt_payload",
    "production_sight_port_id",
    "translate_visual_fragment_to_boundary_observation",
)
