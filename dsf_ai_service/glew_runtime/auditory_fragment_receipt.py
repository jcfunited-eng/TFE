"""Receipted authentication wrapper for real, already-produced native
cochlear-transduction output.

Source of the raw numbers this authenticates:
dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01
.cochlear_transduce() -- called from process_sound_frame()
(dsf_ai_service/v4/gualaloom_v5_engine.py) on real, already-decoded audio
samples. cochlear_transduce() splits the signal into six fixed tonotopic
bands (COCHLEAR_BANDS) and runs a Krimelack oscillator per band, returning
for each band an exact signed cumulative winding number and the exact list
of winding-transition events (time, direction, signal-at-transition) that
produced it.

This module authenticates that real result -- so a later boundary
translator can trust the numbers came from genuine transduction of
captured audio at a specific process tick -- without inventing any of the
missing full-field (DSF/GLEW) semantic authority that native sound does not
have yet. It mirrors the honest self-labeling used by the sight fragment
receipt (dsf_ai_service/visual_krimelack.py's visual_fragment_receipt,
commit 341103a): this receipt's payload carries
"dsf": {"status": "unknown", ...} -- it authenticates real transduction
numbers, it does not claim they already mean anything to GLEW.

No language, transcription, or word-derived value is ever accepted here --
only the raw per-band {winding, n_events, events} that cochlear_transduce()
itself produced from real audio samples, plus the real capture metadata
(source id, process tick, sample rate, and how many real samples were fed
into the transduction) needed to tell a genuine capture apart from no
capture at all.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from .model import ReceiptError, receipt_sha256, require_identifier


AUDITORY_FRAGMENT_RECEIPT_SCHEMA = "guala.native_sound_fragment.v1"

# Honest self-labeling, matching visual_fragment_receipt's
# "dsf": {"status": "unknown", ...} -- this receipt authenticates real
# transduction numbers, it does not claim any ratified DSF/GLEW full-field
# semantic authority over them.
AUDITORY_DSF_UNKNOWN_REASON = (
    "native_auditory_fragment_has_no_ratified_full_field_operator"
)

# Canonical cochlear tonotopic band order -- fixed here (matches
# GL_MDL_AUDITORY_CORTEX_WC_20260608_01.COCHLEAR_BANDS exactly: very_low,
# low, low_mid, mid, mid_high, high) so a missing, renamed, or reordered
# band fails closed instead of silently narrowing which real bands get
# authenticated.
AUDITORY_BAND_ORDER: tuple[str, ...] = (
    "very_low",
    "low",
    "low_mid",
    "mid",
    "mid_high",
    "high",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class AuditoryPerceptFragment:
    """One real cochlear_transduce() result plus the real capture metadata
    needed to authenticate it. Carries no derived DSF field -- only what the
    DSP stage of process_sound_frame actually produced.

    input_sample_count is the real number of (already downsampled) audio
    samples that were fed into cochlear_transduce for this fragment. It is
    the one field that distinguishes "no real audio was ever captured" (0)
    from "real audio was captured and every band happened to stay quiet"
    (>0, with every band at n_events==0) -- the two must never be
    conflated by anything downstream of this receipt.

    bands maps each of AUDITORY_BAND_ORDER's six names to
    {"winding": int, "n_events": int, "events": [{"t": real, "dw": +-1,
    "s": real}, ...]} -- the exact shape cochlear_transduce() returns per
    band (its "filtered" array is intentionally not carried here, for the
    same reason the sight fragment receipt does not carry raw pixels: only
    the derived event stream and winding count are the physical evidence
    that matters past this boundary).
    """

    source_id: str
    born_tick: int
    sample_rate_hz: int
    input_sample_count: int
    bands: Mapping[str, Mapping[str, object]]


def _band_payload(
    band_name: str, band: object, field_name: str
) -> dict[str, object]:
    if not isinstance(band, Mapping) or set(band) != {"winding", "n_events", "events"}:
        raise ReceiptError(f"{field_name} is not a native cochlear band result")
    winding = band["winding"]
    n_events = band["n_events"]
    events = band["events"]
    if isinstance(winding, bool) or not isinstance(winding, int):
        raise ReceiptError(f"{field_name} winding is not an integer")
    if isinstance(n_events, bool) or not isinstance(n_events, int) or n_events < 0:
        raise ReceiptError(f"{field_name} n_events is not a non-negative integer")
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        raise ReceiptError(f"{field_name} events is not a real event sequence")

    encoded_events: list[dict[str, object]] = []
    previous_t: float | None = None
    running_winding = 0
    for event in events:
        if not isinstance(event, Mapping) or set(event) != {"t", "dw", "s"}:
            raise ReceiptError(f"{field_name} event is malformed")
        t, dw, s = event["t"], event["dw"], event["s"]
        if (
            isinstance(t, bool)
            or not isinstance(t, (int, float))
            or not math.isfinite(float(t))
        ):
            raise ReceiptError(f"{field_name} event time is not a real number")
        if dw not in (-1, 1) or isinstance(dw, bool):
            raise ReceiptError(f"{field_name} event winding direction is invalid")
        if (
            isinstance(s, bool)
            or not isinstance(s, (int, float))
            or not math.isfinite(float(s))
        ):
            raise ReceiptError(f"{field_name} event signal is not a real number")
        if previous_t is not None and float(t) < previous_t:
            raise ReceiptError(f"{field_name} events are not time-ordered")
        previous_t = float(t)
        running_winding += int(dw)
        encoded_events.append({"t": float(t), "dw": int(dw), "s": float(s)})

    if len(encoded_events) != n_events:
        raise ReceiptError(
            f"{field_name} n_events does not match its own event records"
        )
    # Real physical invariant of Krimelack.step(): winding is exactly the
    # running sum of that band's own +-1 event directions. Checking it
    # catches a band whose winding and events were tampered independently.
    if running_winding != winding:
        raise ReceiptError(
            f"{field_name} winding does not match the sum of its own event directions"
        )
    return {
        "band": band_name,
        "winding": winding,
        "n_events": n_events,
        "events": encoded_events,
    }


def auditory_fragment_receipt_payload(fragment: AuditoryPerceptFragment) -> bytes:
    """Canonical payload for one authenticated native cochlear-transduction
    fragment. Preserves the exact per-band winding/event counts that
    cochlear_transduce() produced; invents nothing, claims no DSF
    authority."""
    if not isinstance(fragment, AuditoryPerceptFragment):
        raise ReceiptError("auditory fragment is not a typed native percept")
    source_id = require_identifier(fragment.source_id, "auditory fragment source_id")
    if isinstance(fragment.born_tick, bool) or not isinstance(fragment.born_tick, int):
        raise ReceiptError("auditory fragment born_tick is not an integer")
    if (
        isinstance(fragment.sample_rate_hz, bool)
        or not isinstance(fragment.sample_rate_hz, int)
        or fragment.sample_rate_hz <= 0
    ):
        raise ReceiptError(
            "auditory fragment sample_rate_hz is not a positive integer"
        )
    if (
        isinstance(fragment.input_sample_count, bool)
        or not isinstance(fragment.input_sample_count, int)
        or fragment.input_sample_count < 0
    ):
        raise ReceiptError(
            "auditory fragment input_sample_count is not a non-negative integer"
        )
    if not isinstance(fragment.bands, Mapping) or set(fragment.bands) != set(
        AUDITORY_BAND_ORDER
    ):
        raise ReceiptError(
            "auditory fragment does not carry the exact mounted cochlear band set"
        )

    bands_payload = [
        _band_payload(
            band_name,
            fragment.bands[band_name],
            f"auditory fragment band {band_name}",
        )
        for band_name in AUDITORY_BAND_ORDER
    ]
    return _canonical_bytes(
        {
            "schema": AUDITORY_FRAGMENT_RECEIPT_SCHEMA,
            "source_id": source_id,
            "born_tick": fragment.born_tick,
            "sample_rate_hz": fragment.sample_rate_hz,
            "input_sample_count": fragment.input_sample_count,
            "bands": bands_payload,
            "dsf": {
                "status": "unknown",
                "reason": AUDITORY_DSF_UNKNOWN_REASON,
            },
        }
    )


@dataclass(frozen=True, slots=True)
class AuditoryFragmentReceipt:
    fragment: AuditoryPerceptFragment
    receipt_payload: bytes
    receipt_sha256: str

    def verify(self) -> None:
        """Fail closed unless this receipt's bytes are complete, exactly
        reproduce the fragment they claim to authenticate, and are
        untampered."""
        expected_payload = auditory_fragment_receipt_payload(self.fragment)
        if (
            not isinstance(self.receipt_payload, bytes)
            or not self.receipt_payload
            or self.receipt_payload != expected_payload
            or receipt_sha256(expected_payload) != self.receipt_sha256
        ):
            raise ReceiptError("native auditory fragment receipt was tampered")


def auditory_fragment_receipt(
    fragment: AuditoryPerceptFragment,
) -> AuditoryFragmentReceipt:
    """Authenticate one real cochlear_transduce() result plus its capture
    metadata. Raises ReceiptError if the fragment itself is malformed --
    fails closed at construction rather than minting a receipt that would
    only fail verification later."""
    payload = auditory_fragment_receipt_payload(fragment)
    return AuditoryFragmentReceipt(
        fragment=fragment,
        receipt_payload=payload,
        receipt_sha256=receipt_sha256(payload),
    )
