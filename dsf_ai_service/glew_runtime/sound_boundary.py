"""SOUND port translator: real, already-captured audio -> a GLEW
StoryPhysicalBoundaryObservation for the mounted auditory port.

Governing spec: docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-
20260713-v1.md section 9.1, "Live six-sense boundary owner" -- this module
is the SOUND half of that owner. Sight has an authentication receipt
(dsf_ai_service/visual_krimelack.py's visual_fragment_receipt, commit
341103a) but, at the time this module was written, no GLEW boundary
translator of its own yet either; this is the first translator of this
kind, built for sound because sound's evidence is simpler to derive a
non-fabricated flux from (bounded winding counts) than sight's saccade
geometry.

Only the real per-band {winding, n_events, events} that
GL_MDL_AUDITORY_CORTEX_WC_20260608_01.cochlear_transduce() actually
produced from real audio samples -- authenticated by
auditory_fragment_receipt.AuditoryFragmentReceipt -- may ever reach
signed_native_flux. No word label, transcription, or language-derived
value is read here: this stays a raw sound signal path, structurally
separate from any speech-recognition or language path.

Missing, unauthenticated, or truly uncaptured audio evidence returns typed
UNKNOWN (AuditoryBoundaryTranslationResult), never a fabricated flux and
never a raised exception past this boundary. A real, quiet capture
(nonzero real samples, zero winding events in every band) is a different,
valid outcome: it produces a real flux of exactly 0, not UNKNOWN, because
"zero real audio samples were ever captured" is not the same evidence as
"real audio was captured and it was near-silent."
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from .auditory_fragment_receipt import AUDITORY_BAND_ORDER, AuditoryFragmentReceipt
from .model import ReceiptError, receipt_sha256, require_fraction, require_identifier
from .story_chemistry import (
    PRODUCTION_STORY_PORT_LANES,
    SignedStoryChemistryManifest,
    StoryPhysicalBoundaryObservation,
    story_boundary_observation_receipt_payload,
)


# Read from the ratified production five-sense chemistry profile's own lane
# table (story_chemistry.PRODUCTION_STORY_PORT_LANES, itself parsed from
# dsf_ai_service/glew_runtime/profiles/production_virtual_story_chemistry_
# profile_v1.json) instead of retyping the port_id string by hand -- the
# mounted port entry with kernel_binding.lane_id == "sound" is
# "story-auditory.native-port-0".
_AUDITORY_PORT_ID_BY_LANE = {
    lane_id: port_id for port_id, lane_id in PRODUCTION_STORY_PORT_LANES
}
try:
    AUDITORY_PORT_ID = _AUDITORY_PORT_ID_BY_LANE["sound"]
except KeyError as exc:  # pragma: no cover - ratified profile invariant
    raise ReceiptError(
        "production story chemistry profile no longer names a sound lane"
    ) from exc


class AuditoryBoundaryTranslationStatus(str, Enum):
    OBSERVED = "observed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AuditoryBoundaryTranslationResult:
    status: AuditoryBoundaryTranslationStatus
    observation: StoryPhysicalBoundaryObservation | None
    reason: str


def _unknown(reason: str) -> AuditoryBoundaryTranslationResult:
    return AuditoryBoundaryTranslationResult(
        status=AuditoryBoundaryTranslationStatus.UNKNOWN,
        observation=None,
        reason=reason,
    )


def _signed_native_flux(fragment) -> Fraction:
    """Net signed winding aggregate across all six tonotopic bands,
    weighted by each band's own real event count:

        signed_flux = (sum of winding_b over bands) / (sum of n_events_b over bands)

    winding_b is the exact signed sum of band b's own +-1 winding
    transitions (real Krimelack output, checked against its own event list
    by auditory_fragment_receipt's construction-time invariant);
    n_events_b == len(band b's own event list). Because every transition
    contributes exactly +-1 to both the numerator and the denominator,
    |winding_b| <= n_events_b for every band, so this aggregate ratio is
    guaranteed to land in the closed interval [-1, 1] -- exactly the
    auditory port's registered physical dimension
    ("dimensionless_signed_boundary_flux_in_closed_interval_minus_one_to_
    one") -- by construction, with no clipping and no rescaling.

    This is equivalently the n_events-weighted mean of each band's own net
    winding fraction (winding_b / n_events_b): weighting by each band's
    real event count means a band that fired often contributes
    proportionally more evidence than a band that barely fired, with no
    per-band threshold, no manual reweighting, and no reference to the
    "s" (signal-at-transition) or "filtered" values -- only the exact
    integer counts cochlear_transduce() produced.

    Must only be called once the caller has already established that
    total_events > 0 -- a real, nonempty capture that produced at least
    one real winding transition somewhere in the spectrum. (The
    total_events == 0 case -- a real capture where every band happened to
    stay silent -- is a distinct, valid outcome handled by the caller as
    an exact 0, not by this function, since 0 winding / 0 events is not a
    well-defined ratio.)
    """
    total_winding = 0
    total_events = 0
    for band_name in AUDITORY_BAND_ORDER:
        band = fragment.bands[band_name]
        total_winding += int(band["winding"])
        total_events += int(band["n_events"])
    return Fraction(total_winding, total_events)


def translate_auditory_fragment_to_boundary_observation(
    fragment_receipt: AuditoryFragmentReceipt | None,
    *,
    manifest: SignedStoryChemistryManifest,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> AuditoryBoundaryTranslationResult:
    """Translate one authenticated real cochlear-transduction fragment into
    a StoryPhysicalBoundaryObservation for the mounted auditory port, or an
    explicit typed UNKNOWN. Never raises past this boundary.

    manifest must be an already-authenticated, already-mounted
    SignedStoryChemistryManifest (see story_chemistry.mount_story_chemistry
    / mount_packaged_production_story_chemistry) -- this function only
    looks up the auditory port that manifest already verified; it does not
    itself authenticate the manifest.
    """

    if not isinstance(manifest, SignedStoryChemistryManifest):
        return _unknown(
            "auditory boundary translation requires an already-mounted "
            "story chemistry manifest"
        )

    if fragment_receipt is None:
        return _unknown(
            "no auditory fragment receipt was supplied -- no audio evidence"
        )
    if not isinstance(fragment_receipt, AuditoryFragmentReceipt):
        return _unknown("auditory fragment receipt is not a typed native receipt")

    try:
        fragment_receipt.verify()
    except ReceiptError as exc:
        return _unknown(f"auditory fragment receipt failed authentication: {exc}")

    fragment = fragment_receipt.fragment
    if fragment.input_sample_count <= 0:
        return _unknown(
            "zero real audio samples were captured -- no evidence to derive "
            "a boundary observation from (distinct from a real, quiet "
            "capture, which produces a real near-zero flux instead)"
        )

    try:
        port = manifest.port(AUDITORY_PORT_ID)
    except ReceiptError as exc:
        return _unknown(f"auditory port is not mounted: {exc}")
    if port.kernel_binding.lane_id != "sound":
        return _unknown(
            "mounted auditory port_id no longer binds to the sound lane -- "
            "refusing to guess"
        )

    try:
        event_id = require_identifier(event_id, "auditory boundary event_id")
        observation_id = require_identifier(
            observation_id, "auditory boundary observation_id"
        )
        require_fraction(source_time_start, "auditory boundary source_time_start")
        require_fraction(source_time_end, "auditory boundary source_time_end")
    except ReceiptError as exc:
        return _unknown(str(exc))
    if source_time_end <= source_time_start:
        return _unknown(
            "auditory boundary observation window is not a positive real duration"
        )

    total_events = sum(
        int(fragment.bands[band_name]["n_events"]) for band_name in AUDITORY_BAND_ORDER
    )
    if total_events == 0:
        # Real, nonempty capture; every tonotopic band stayed below its own
        # winding threshold for the whole window. That is a real near-zero
        # boundary flux, not missing evidence -- reported as exactly 0, the
        # honest value of the weighted-aggregate formula's limit when there
        # is no directional winding evidence anywhere in the spectrum.
        # Never UNKNOWN: real audio was genuinely captured and processed.
        signed_native_flux = Fraction(0)
    else:
        signed_native_flux = _signed_native_flux(fragment)

    if not (Fraction(-1) <= signed_native_flux <= Fraction(1)):
        # Cannot happen given the derivation above (proven bounded by
        # construction); kept as a fail-closed guard rather than trusting
        # the proof silently forever.
        return _unknown(
            "derived auditory boundary flux fell outside the port's "
            "registered physical interval"
        )

    try:
        provenance_receipt_sha256 = fragment_receipt.receipt_sha256
        provenance_receipt_payload = fragment_receipt.receipt_payload
        observation_payload = story_boundary_observation_receipt_payload(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port.port_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            signed_native_flux=signed_native_flux,
            native_flux_unit=port.native_signal_unit,
            provenance_receipt_sha256=provenance_receipt_sha256,
        )
        observation = StoryPhysicalBoundaryObservation(
            event_id=event_id,
            observation_id=observation_id,
            port_id=port.port_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            signed_native_flux=signed_native_flux,
            native_flux_unit=port.native_signal_unit,
            provenance_receipt_sha256=provenance_receipt_sha256,
            provenance_receipt_payload=provenance_receipt_payload,
            observation_receipt_sha256=receipt_sha256(observation_payload),
            observation_receipt_payload=observation_payload,
        )
        observation.verify()
    except ReceiptError as exc:
        return _unknown(
            f"auditory boundary observation failed self-verification: {exc}"
        )

    return AuditoryBoundaryTranslationResult(
        status=AuditoryBoundaryTranslationStatus.OBSERVED,
        observation=observation,
        reason="real native cochlear transduction observed",
    )
