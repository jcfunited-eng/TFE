"""Deterministic, non-statistical silence/presence and voiced/unvoiced
discrimination from real cochlear transduction, decided by the existing
certified interval-dominance recognizer.

SCOPE (read this first -- it is deliberately narrow and honest)
================================================================
This module builds ONE, and only one, honestly-achievable first milestone
toward real speech-to-text:

  1. silence vs. speech-presence, and
  2. (when present) voiced vs. unvoiced sound.

It is NOT phoneme recognition, NOT word recognition, and NOT a step that
trivially extends to either. A prior honest investigation concluded that
full word/phoneme-level recognition fundamentally requires statistical
acoustic-phonetic modeling: the category boundaries between phonemes
genuinely overlap in continuous acoustic space, so no amount of exact
arithmetic can separate them without a learned/statistical model. That is
true of every real speech recognizer, not a limitation peculiar to this
codebase. This module makes NO progress on that hard problem and must not be
represented as if it does. What it does do is establish the two coarse,
physically-exact distinctions that a real system computes FIRST, using zero
pretrained models, zero heuristic thresholds, and zero statistical modeling
-- every decision here is an exact integer/Fraction comparison or the
codebase's own certified-ball interval dominance, never a tuned magic number.

Everything downstream of presence+voicing (segmenting the speech stream into
phones, mapping acoustic frames to phoneme categories, mapping phones to
words, a language model) is out of scope and, per the investigation, cannot
be built to this same zero-statistics standard at all. Closing that gap is a
separate, much larger effort.

WHERE THE REAL EVIDENCE COMES FROM
==================================
The only physical evidence this module ever reads is the exact per-band
``{winding, n_events}`` that
``dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01
.cochlear_transduce()`` actually produced from real audio samples --
authenticated by ``auditory_fragment_receipt.AuditoryFragmentReceipt``,
exactly as ``sound_boundary.py`` requires. ``cochlear_transduce`` splits the
signal into six fixed tonotopic bands (``COCHLEAR_BANDS``) and runs one
Krimelack oscillator per band, returning per band an exact signed cumulative
winding number and the exact list of +-1 winding-transition events that
produced it. No word label, transcription, or language-derived value is ever
read here; this is a raw-sound path only.

DISCRIMINATION 1 -- silence vs. speech-presence (an exact zero boundary)
========================================================================
``total_events = sum(n_events over all six bands)``. Exactly zero events
means SILENCE (literally: not one cochlear band registered a single winding
transition). Greater than zero means SPEECH_PRESENT. This is a real physical
boundary, not a threshold: there is no tunable cutoff, only the exact
integer question "did ANY band register ANY event".

This one distinction is NOT routed through the certified recognizer, on
purpose. The recognizer decides which of several competing stored categories
an input's field most resembles, and it fundamentally requires the input's
field energy to be certified strictly positive. A truly silent capture has
an all-zero feature vector and hence exactly zero field energy, so feeding
it to the recognizer would only ever yield the recognizer's own UNKNOWN --
never a clean SILENCE. "Did any event occur" is already an exact, definitive
boundary that needs no interval-dominance machinery, so we answer it
directly and honestly rather than dressing it up in recognizer scaffolding.

DISCRIMINATION 2 -- voiced vs. unvoiced (certified interval dominance)
======================================================================
Physical basis: voicing is periodic phonation with a strong low-frequency
fundamental; voicelessness (frication/aspiration) is broadband, high-
frequency, aperiodic energy without that low-frequency periodicity. In this
substrate the genuine, exact correlate of periodicity is each band's net
signed winding magnitude ``|winding|``: a coherent, periodic signal drives
its matched band's Krimelack in a consistent direction, so its +-1 events do
NOT cancel and ``|winding|`` accumulates; an aperiodic/noisy signal produces
+-1 transitions that largely cancel, leaving ``|winding|`` near zero. We use
``|winding|`` and NOT the raw spike count ``n_events`` for voicing because
``n_events`` was empirically confirmed to be dominated by the per-band
``kappa`` sensitivity gradient (``cochlear_transduce`` gives higher bands a
larger ``kappa``, so they register more events regardless of where the
signal's energy actually lies); ``|winding|`` isolates coherent periodicity,
which is the real voiced/unvoiced physical distinction, while ``n_events``
does not.

Low vs. high split: the six band centre frequencies are 8, 18, 35, 55, 75,
92 Hz (within the substrate's Nyquist for sample_rate=200). Their range
midpoint is (8+92)/2 = 50 Hz, so the three bands below 50 Hz
(``very_low`` 8, ``low`` 18, ``low_mid`` 35) are the LOW/periodicity half and
the three at or above 50 Hz (``mid`` 55, ``mid_high`` 75, ``high`` 92) are
the HIGH half. This is an even 3/3 split at the arithmetic midpoint of the
band definitions themselves -- not a tuned boundary.

Rather than invent a bespoke if/else, the voiced/unvoiced decision is made
by the SAME certified mechanism the rest of this session's GLEW work uses:
``expression_modes.evaluate_expression_mode_boundary``. We build a real
19-coordinate field feature vector holding the six exact per-band
``|winding|`` values (coordinates 0..5, the remaining 13 fibre coordinates
zero), following ``field.py``'s exact identity-inclusion contract, and a
real minimal two-mode reference bank: a VOICED reference concentrating unit
weight across the three LOW-band coordinates ``(1,1,1,0,0,0,...)`` and an
UNVOICED reference across the three HIGH-band coordinates
``(0,0,0,1,1,1,...)``. The recognizer, using exact-rational FLINT/Arb
``CertifiedBall`` interval dominance (decision rule
``one_lower_bound_strictly_exceeds_every_other_upper_bound``, with
precision doubling when indeterminate), decides which reference the input's
exact winding vector certainly dominates:

  * RECOGNIZED, winner = the voiced reference   -> VOICED
  * RECOGNIZED, winner = the unvoiced reference -> UNVOICED
  * any non-committal recognizer outcome
    (AMBIGUOUS_SILENCE / NOVEL_SILENCE / BOOTSTRAP_SILENCE / UNKNOWN)
    -> AMBIGUOUS (an honest "the exact evidence does not cleanly favour
       either category", never a forced guess)
  * present but every band's ``|winding|`` is exactly zero (a real capture
    with events but no coherent periodicity anywhere) -> AMBIGUOUS, decided
    directly, because an all-zero feature vector again has no certified-
    positive energy for the recognizer to compare.

The field/transport scaffolding around that winding vector (the mounted
topology, the transport-evidence regime/support/resonance/validity/
provenance authorities, the evolution authority, the precision authority)
carries no acoustic meaning of its own here: it is the structural carrier
that ``field.py``'s contract requires, exactly as the existing
``tests/glew_runtime/test_field.py`` / ``real_experience_learning_pipeline``
scaffolding is. The ONLY acoustically-meaningful content is the exact
per-band winding vector; those carrier authorities are opaque structural
receipts, and this is stated plainly rather than implied to be measured.

PROVENANCE
==========
Every result carries a BindingWindow-style receipt: a canonical
SHA-256-bound payload (the codebase's universal ``receipt_sha256``
convention) that cites the exact authenticated cochlear-transduction
fragment (by its receipt digest) and the exact per-band numbers the decision
was derived from, so any later reader can re-derive and re-check the
discrimination. ``verify()`` fails closed if the cited fragment receipt is
tampered, if the stored per-band numbers do not match the fragment, or if
the result payload itself was altered.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping

from .auditory_fragment_receipt import (
    AUDITORY_BAND_ORDER,
    AuditoryFragmentReceipt,
    AuditoryPerceptFragment,
    auditory_fragment_receipt,
)
from .certified_backend import CertifiedBall
from .expression_modes import (
    EXPRESSION_RECOGNITION_OPERATOR_ID,
    ExpressionModeBank,
    ExpressionRecognitionStatus,
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
)
from .expressions import (
    FieldExpressionStep,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
    precision_schedule_authority_receipt_payload,
)
from .field import (
    ExactComplex,
    ExactFieldState,
    EvidenceProvenance,
    EvidenceValidity,
    EvidenceValidityState,
    FIBER_DIMENSION,
    FieldEvolutionAuthority,
    MountedFieldTopology,
    PortFiber,
    PortTransportEvidence,
    RegimeFact,
    ResonanceFact,
    StructuralFactState,
    SupportFloorFact,
    TransportCoordinates19,
    canonical_component_partition,
    evolution_authority_receipt_payload,
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
    map_inject,
    source_coefficients_for_injection,
    transport_evidence_receipt_payload,
)
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    sha256_digest,
)


# ---------------------------------------------------------------------------
# Fixed band partition (from GL_MDL_AUDITORY_CORTEX_WC_20260608_01.COCHLEAR_
# BANDS centre frequencies 8/18/35/55/75/92 Hz, split at their range midpoint
# 50 Hz). AUDITORY_BAND_ORDER is imported and re-checked so a renamed or
# reordered mounted band set fails closed instead of silently mis-splitting.
# ---------------------------------------------------------------------------

LOW_BANDS: tuple[str, ...] = ("very_low", "low", "low_mid")
HIGH_BANDS: tuple[str, ...] = ("mid", "mid_high", "high")
BAND_SPLIT_MIDPOINT_HZ = Fraction(50)

if LOW_BANDS + HIGH_BANDS != AUDITORY_BAND_ORDER:  # pragma: no cover - invariant
    raise ReceiptError(
        "deterministic sound discrimination low/high split does not cover the "
        "exact mounted cochlear band order"
    )

_PRESENCE_SCHEMA = "guala.deterministic_sound_discrimination.presence.v1"
_VOICING_SCHEMA = "guala.deterministic_sound_discrimination.voicing.v1"
_RESULT_SCHEMA = "guala.deterministic_sound_discrimination.result.v1"

# The two reference categories, as exact 6-band |winding| feature templates.
_VOICED_REFERENCE_BANDS: tuple[int, ...] = (1, 1, 1, 0, 0, 0)
_UNVOICED_REFERENCE_BANDS: tuple[int, ...] = (0, 0, 0, 1, 1, 1)
_VOICED_MODE_INDEX = 0
_UNVOICED_MODE_INDEX = 1

_RECOGNIZER_DECISION_RULE = (
    "one_lower_bound_strictly_exceeds_every_other_upper_bound"
)


class SoundPresence(str, Enum):
    SILENCE = "silence"
    SPEECH_PRESENT = "speech_present"


class Voicing(str, Enum):
    VOICED = "voiced"
    UNVOICED = "unvoiced"
    AMBIGUOUS = "ambiguous"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Exact per-band extraction from an authenticated fragment.
# ---------------------------------------------------------------------------


def _require_fragment_receipt(
    fragment_receipt: AuditoryFragmentReceipt | None,
) -> AuditoryFragmentReceipt:
    if fragment_receipt is None or not isinstance(
        fragment_receipt, AuditoryFragmentReceipt
    ):
        raise ReceiptError(
            "sound discrimination requires a typed AuditoryFragmentReceipt"
        )
    # Fails closed if the authenticated per-band numbers were tampered.
    fragment_receipt.verify()
    return fragment_receipt


def _per_band_n_events(fragment: AuditoryPerceptFragment) -> tuple[int, ...]:
    return tuple(
        int(fragment.bands[band]["n_events"]) for band in AUDITORY_BAND_ORDER
    )


def _per_band_winding_magnitude(
    fragment: AuditoryPerceptFragment,
) -> tuple[int, ...]:
    return tuple(
        abs(int(fragment.bands[band]["winding"])) for band in AUDITORY_BAND_ORDER
    )


# ---------------------------------------------------------------------------
# Real closed-experience field expression carrier for one exact 19-vector.
#
# Mirrors exactly the real construction chain proven by
# tests/glew_runtime/test_field.py and used by
# real_experience_learning_pipeline._build_expression: evidence ->
# map_inject -> evolution authority -> zero initial state ->
# create_closed_experience_expression. A single zero-Hamiltonian gate over a
# unit source interval with a zero initial state evaluates the field to
# exactly the injected vector, so the recognizer compares the exact winding
# feature vectors directly. The regime/support/resonance/validity/provenance/
# physical-profile authorities are structural carrier receipts (see module
# docstring): they carry no acoustic claim.
# ---------------------------------------------------------------------------

_CARRIER_PROFILE = b"guala-deterministic-sound-discrimination-profile-v1"
_CARRIER_AUTHORITIES: Mapping[str, bytes] = {
    "regime": b"deterministic-sound-discrimination:carrier:regime",
    "support": b"deterministic-sound-discrimination:carrier:support",
    "resonance": b"deterministic-sound-discrimination:carrier:resonance",
    "validity": b"deterministic-sound-discrimination:carrier:validity",
    "provenance": b"deterministic-sound-discrimination:carrier:provenance",
    "physical": b"deterministic-sound-discrimination:carrier:physical-profile",
}
_CARRIER_TOPOLOGY_ID = "deterministic-sound-discrimination-topology"
_CARRIER_LANE = "sound"
_CARRIER_PORT = "native"
_CARRIER_SOURCE_TIME_START = Fraction(5)
_CARRIER_SOURCE_TIME_END = Fraction(6)
_CARRIER_PRECISION_BITS = 4096
_CARRIER_FIELD_PRECISION_BITS = 256


def _carrier_registry(*payloads: bytes) -> ReceiptRegistry:
    unique = tuple(
        dict.fromkeys((*_CARRIER_AUTHORITIES.values(), *payloads))
    )
    return ReceiptRegistry.from_payloads(
        profile_payload=_CARRIER_PROFILE,
        receipt_payloads=unique,
    )


def _exact_carrier_ball(value: Fraction = Fraction(1)) -> CertifiedBall:
    return CertifiedBall(
        lower_mantissa=value.numerator,
        lower_exponent=-(value.denominator.bit_length() - 1),
        upper_mantissa=value.numerator,
        upper_exponent=-(value.denominator.bit_length() - 1),
        working_precision_bits=_CARRIER_FIELD_PRECISION_BITS,
    )


def _carrier_evidence(
    values: tuple[Fraction, ...],
) -> tuple[PortTransportEvidence, bytes, bytes]:
    coordinates = TransportCoordinates19(*values)
    regime = RegimeFact("stable", receipt_sha256(_CARRIER_AUTHORITIES["regime"]))
    support = SupportFloorFact(
        StructuralFactState.AVAILABLE,
        Fraction(1),
        receipt_sha256(_CARRIER_AUTHORITIES["support"]),
    )
    resonance = ResonanceFact(
        StructuralFactState.AVAILABLE,
        _exact_carrier_ball(),
        receipt_sha256(_CARRIER_AUTHORITIES["resonance"]),
    )
    validity = EvidenceValidity(
        EvidenceValidityState.VALID,
        receipt_sha256(_CARRIER_AUTHORITIES["validity"]),
        None,
    )
    provenance = EvidenceProvenance(
        provider_id=f"{_CARRIER_LANE}.{_CARRIER_PORT}.provider",
        source_epoch="deterministic-sound-discrimination-epoch",
        source_index=0,
        source_timestamp=_CARRIER_SOURCE_TIME_START,
        authority_receipt_sha256=receipt_sha256(
            _CARRIER_AUTHORITIES["provenance"]
        ),
    )
    raw_payload = f"raw:{_CARRIER_LANE}:{_CARRIER_PORT}".encode()
    raw = ReceiptRecord(receipt_sha256(raw_payload), raw_payload)
    receipt_payload = transport_evidence_receipt_payload(
        lane_id=_CARRIER_LANE,
        port_id=_CARRIER_PORT,
        evidence_id=f"{_CARRIER_LANE}.{_CARRIER_PORT}.gate-1",
        coordinates=coordinates,
        regime=regime,
        support_floor=support,
        resonance=resonance,
        validity=validity,
        provenance=provenance,
        raw_record_sha256=raw.digest,
    )
    record = PortTransportEvidence(
        lane_id=_CARRIER_LANE,
        port_id=_CARRIER_PORT,
        evidence_id=f"{_CARRIER_LANE}.{_CARRIER_PORT}.gate-1",
        coordinates=coordinates,
        regime=regime,
        support_floor=support,
        resonance=resonance,
        validity=validity,
        provenance=provenance,
        raw_record=raw,
        evidence_receipt_sha256=receipt_sha256(receipt_payload),
    )
    return record, raw_payload, receipt_payload


def _carrier_topology() -> tuple[MountedFieldTopology, bytes]:
    fibers = (PortFiber(_CARRIER_LANE, _CARRIER_PORT),)
    payload = field_topology_receipt_payload(_CARRIER_TOPOLOGY_ID, fibers)
    return (
        MountedFieldTopology(
            topology_id=_CARRIER_TOPOLOGY_ID,
            ordered_port_fibers=fibers,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def _carrier_precision() -> tuple[PrecisionScheduleAuthority, bytes]:
    payload = precision_schedule_authority_receipt_payload(
        authority_id="deterministic-sound-discrimination-precision",
        maximum_precision_bits=_CARRIER_PRECISION_BITS,
    )
    return (
        PrecisionScheduleAuthority(
            "deterministic-sound-discrimination-precision",
            _CARRIER_PRECISION_BITS,
            receipt_sha256(payload),
        ),
        payload,
    )


def _feature_vector(band_values: tuple[int, ...]) -> tuple[Fraction, ...]:
    if len(band_values) != len(AUDITORY_BAND_ORDER):
        raise ReceiptError("feature vector requires one value per cochlear band")
    tail = FIBER_DIMENSION - len(band_values)
    return tuple(Fraction(int(v)) for v in band_values) + (Fraction(0),) * tail


def _build_feature_expression(
    *,
    topology: MountedFieldTopology,
    topology_payload: bytes,
    precision: PrecisionScheduleAuthority,
    precision_payload: bytes,
    band_values: tuple[int, ...],
):
    """Return (expression, payloads) for one exact 6-band |winding| vector."""

    values = _feature_vector(band_values)
    record, raw_payload, evidence_payload = _carrier_evidence(values)
    injection = map_inject(
        topology,
        (record,),
        _carrier_registry(topology_payload, raw_payload, evidence_payload),
    )
    delta = _CARRIER_SOURCE_TIME_END - _CARRIER_SOURCE_TIME_START
    source = source_coefficients_for_injection(injection, delta)
    components = canonical_component_partition(topology.dimension, ())
    authority_payload = evolution_authority_receipt_payload(
        authority_id="deterministic-sound-discrimination-gate",
        physical_profile_receipt_sha256=receipt_sha256(
            _CARRIER_AUTHORITIES["physical"]
        ),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        map_injection_receipt_sha256=injection.receipt_sha256,
        source_time_start=_CARRIER_SOURCE_TIME_START,
        source_time_end=_CARRIER_SOURCE_TIME_END,
        source_time_unit="deterministic-sound-discrimination-structural-time",
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source=source,
        component_partition=components,
        max_connected_component_dimension=FIBER_DIMENSION,
        precision_bits=_CARRIER_FIELD_PRECISION_BITS,
    )
    authority = FieldEvolutionAuthority(
        authority_id="deterministic-sound-discrimination-gate",
        physical_profile_receipt_sha256=receipt_sha256(
            _CARRIER_AUTHORITIES["physical"]
        ),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        map_injection_receipt_sha256=injection.receipt_sha256,
        source_time_start=_CARRIER_SOURCE_TIME_START,
        source_time_end=_CARRIER_SOURCE_TIME_END,
        source_time_unit="deterministic-sound-discrimination-structural-time",
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source=source,
        max_connected_component_dimension=FIBER_DIMENSION,
        precision_bits=_CARRIER_FIELD_PRECISION_BITS,
        authority_receipt_sha256=receipt_sha256(authority_payload),
    )
    zero_amplitudes = tuple(
        ExactComplex(Fraction(0)) for _ in range(topology.dimension)
    )
    initial_payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256,
        _CARRIER_SOURCE_TIME_START,
        zero_amplitudes,
    )
    initial = ExactFieldState(
        topology.authority_receipt_sha256,
        _CARRIER_SOURCE_TIME_START,
        zero_amplitudes,
        receipt_sha256(initial_payload),
    )
    payloads = (
        topology_payload,
        raw_payload,
        evidence_payload,
        authority_payload,
        initial_payload,
        precision_payload,
    )
    expression = create_closed_experience_expression(
        topology=topology,
        initial_state=initial,
        steps=(FieldExpressionStep(injection, authority),),
        precision_authority=precision,
        receipt_registry=_carrier_registry(*payloads),
    )
    return expression, (*payloads, expression.receipt_payload)


def _mode_bank_payloads(result) -> tuple[bytes, ...]:
    payloads = [
        result.pre_growth_bank.receipt_payload,
        result.post_growth_bank.receipt_payload,
        result.receipt_payload,
    ]
    for bank in (result.pre_growth_bank, result.post_growth_bank):
        for mode in bank.modes:
            payloads.extend(
                (
                    mode.source_expression.receipt_payload,
                    mode.growth_proof_receipt_payload,
                    mode.receipt_payload,
                )
            )
    return tuple(payloads)


# Cached bootstrapped rank-two reference bank (voiced then unvoiced). The
# recognizer never mutates the input bank, so this pure, deterministic
# reference is safe to reuse across every discrimination.
_REFERENCE_CACHE: dict[str, object] | None = None


def _reference_voicing_recognizer() -> dict[str, object]:
    global _REFERENCE_CACHE
    if _REFERENCE_CACHE is not None:
        return _REFERENCE_CACHE

    topology, topology_payload = _carrier_topology()
    precision, precision_payload = _carrier_precision()

    voiced_expr, voiced_payloads = _build_feature_expression(
        topology=topology,
        topology_payload=topology_payload,
        precision=precision,
        precision_payload=precision_payload,
        band_values=_VOICED_REFERENCE_BANDS,
    )
    unvoiced_expr, unvoiced_payloads = _build_feature_expression(
        topology=topology,
        topology_payload=topology_payload,
        precision=precision,
        precision_payload=precision_payload,
        band_values=_UNVOICED_REFERENCE_BANDS,
    )

    base_payloads = tuple(dict.fromkeys((*voiced_payloads, *unvoiced_payloads)))
    registry = _carrier_registry(*base_payloads)
    empty_bank = create_empty_expression_mode_bank(
        topology=topology,
        precision_authority=precision,
        receipt_registry=registry,
    )
    accumulated = list(base_payloads) + [empty_bank.receipt_payload]
    registry = _carrier_registry(*accumulated)

    first = evaluate_expression_mode_boundary(
        topology=topology,
        bank=empty_bank,
        input_expression=voiced_expr,
        receipt_registry=registry,
    )
    if (
        first.status is not ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
        or first.post_growth_bank.rank != 1
    ):
        raise ReceiptError(
            "voiced reference did not bootstrap the voicing mode bank: "
            f"{first.status}/{first.reason}"
        )
    accumulated.extend(_mode_bank_payloads(first))
    registry = _carrier_registry(*dict.fromkeys(accumulated))

    second = evaluate_expression_mode_boundary(
        topology=topology,
        bank=first.post_growth_bank,
        input_expression=unvoiced_expr,
        receipt_registry=registry,
    )
    if (
        second.status is not ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
        or second.post_growth_bank.rank != 2
    ):
        raise ReceiptError(
            "unvoiced reference did not bootstrap the voicing mode bank to "
            f"rank two: {second.status}/{second.reason}"
        )
    accumulated.extend(_mode_bank_payloads(second))

    reference_bank = second.post_growth_bank
    _REFERENCE_CACHE = {
        "topology": topology,
        "topology_payload": topology_payload,
        "precision": precision,
        "precision_payload": precision_payload,
        "bank": reference_bank,
        "base_payloads": tuple(dict.fromkeys(accumulated)),
    }
    return _REFERENCE_CACHE


def _recognize_voicing(band_magnitudes: tuple[int, ...]):
    """Route one exact 6-band |winding| vector through the real certified
    interval-dominance recognizer against the voiced/unvoiced reference bank.

    Returns (recognition_status_value, winner_mode_index, recognition_receipt
    _sha256). Never mutates the cached reference bank.
    """

    reference = _reference_voicing_recognizer()
    topology: MountedFieldTopology = reference["topology"]  # type: ignore[assignment]
    precision: PrecisionScheduleAuthority = reference["precision"]  # type: ignore[assignment]
    bank: ExpressionModeBank = reference["bank"]  # type: ignore[assignment]

    input_expr, input_payloads = _build_feature_expression(
        topology=topology,
        topology_payload=reference["topology_payload"],  # type: ignore[arg-type]
        precision=precision,
        precision_payload=reference["precision_payload"],  # type: ignore[arg-type]
        band_values=band_magnitudes,
    )
    registry = _carrier_registry(
        *reference["base_payloads"],  # type: ignore[misc]
        *input_payloads,
    )
    result = evaluate_expression_mode_boundary(
        topology=topology,
        bank=bank,
        input_expression=input_expr,
        receipt_registry=registry,
    )
    return result.status.value, result.winner_mode_index, result.receipt_sha256


# ---------------------------------------------------------------------------
# Public receipted results.
# ---------------------------------------------------------------------------


def _presence_payload(
    *,
    fragment_receipt_sha256: str,
    per_band_n_events: tuple[int, ...],
    total_n_events: int,
    status: SoundPresence,
) -> bytes:
    return _canonical_bytes(
        {
            "boundary_rule": (
                "total_winding_event_count_exactly_zero_is_silence_"
                "else_speech_present"
            ),
            "fragment_receipt_sha256": fragment_receipt_sha256,
            "per_band_n_events": [
                [band, count]
                for band, count in zip(AUDITORY_BAND_ORDER, per_band_n_events)
            ],
            "schema": _PRESENCE_SCHEMA,
            "status": status.value,
            "total_n_events": total_n_events,
        }
    )


@dataclass(frozen=True, slots=True)
class SoundPresenceDiscrimination:
    """Exact silence-vs-presence result plus its provenance receipt."""

    status: SoundPresence
    total_n_events: int
    per_band_n_events: tuple[int, ...]
    fragment_receipt_sha256: str
    receipt_sha256: str
    receipt_payload: bytes

    def verify(self, fragment_receipt: AuditoryFragmentReceipt) -> None:
        fragment_receipt = _require_fragment_receipt(fragment_receipt)
        if fragment_receipt.receipt_sha256 != self.fragment_receipt_sha256:
            raise ReceiptError(
                "presence result cites a different auditory fragment receipt"
            )
        per_band = _per_band_n_events(fragment_receipt.fragment)
        total = sum(per_band)
        expected_status = (
            SoundPresence.SILENCE if total == 0 else SoundPresence.SPEECH_PRESENT
        )
        if (
            per_band != self.per_band_n_events
            or total != self.total_n_events
            or expected_status is not self.status
        ):
            raise ReceiptError(
                "presence result does not match the cited fragment's exact "
                "per-band winding-event counts"
            )
        expected = _presence_payload(
            fragment_receipt_sha256=self.fragment_receipt_sha256,
            per_band_n_events=self.per_band_n_events,
            total_n_events=self.total_n_events,
            status=self.status,
        )
        if (
            self.receipt_payload != expected
            or receipt_sha256(expected) != self.receipt_sha256
        ):
            raise ReceiptError("presence result differs from its canonical receipt")


def _voicing_payload(
    *,
    fragment_receipt_sha256: str,
    per_band_winding_magnitude: tuple[int, ...],
    low_band_winding_magnitude_sum: int,
    high_band_winding_magnitude_sum: int,
    recognition_status: str,
    winner_mode_index: int | None,
    recognition_receipt_sha256: str | None,
    status: Voicing,
) -> bytes:
    return _canonical_bytes(
        {
            "band_split_midpoint_hz": (
                f"{BAND_SPLIT_MIDPOINT_HZ.numerator}/"
                f"{BAND_SPLIT_MIDPOINT_HZ.denominator}"
            ),
            "fragment_receipt_sha256": fragment_receipt_sha256,
            "high_band_winding_magnitude_sum": high_band_winding_magnitude_sum,
            "high_bands": list(HIGH_BANDS),
            "low_band_winding_magnitude_sum": low_band_winding_magnitude_sum,
            "low_bands": list(LOW_BANDS),
            "per_band_winding_magnitude": [
                [band, magnitude]
                for band, magnitude in zip(
                    AUDITORY_BAND_ORDER, per_band_winding_magnitude
                )
            ],
            "recognizer": {
                "decision_rule": _RECOGNIZER_DECISION_RULE,
                "operator_id": EXPRESSION_RECOGNITION_OPERATOR_ID,
                "recognition_receipt_sha256": recognition_receipt_sha256,
                "recognition_status": recognition_status,
                "unvoiced_reference_bands": list(_UNVOICED_REFERENCE_BANDS),
                "voiced_reference_bands": list(_VOICED_REFERENCE_BANDS),
                "winner_mode_index": winner_mode_index,
            },
            "schema": _VOICING_SCHEMA,
            "status": status.value,
        }
    )


# Recognizer statuses that are honestly non-committal for voicing.
_AMBIGUOUS_RECOGNIZER_STATUSES = frozenset(
    value.value
    for value in (
        ExpressionRecognitionStatus.AMBIGUOUS_SILENCE,
        ExpressionRecognitionStatus.NOVEL_SILENCE,
        ExpressionRecognitionStatus.BOOTSTRAP_SILENCE,
        ExpressionRecognitionStatus.UNKNOWN,
    )
)
# Sentinel recognition status used when presence holds but every band's
# coherent winding is exactly zero: the feature vector is all zero, so it has
# no certified-positive field energy and the recognizer is not run.
_ZERO_WINDING_RECOGNITION_STATUS = "not_evaluated_zero_coherent_winding"


def _voicing_status_from_recognition(
    recognition_status: str, winner_mode_index: int | None
) -> Voicing:
    if recognition_status == ExpressionRecognitionStatus.RECOGNIZED.value:
        if winner_mode_index == _VOICED_MODE_INDEX:
            return Voicing.VOICED
        if winner_mode_index == _UNVOICED_MODE_INDEX:
            return Voicing.UNVOICED
        # Recognized as a later-grown mode (not one of the two references):
        # honest AMBIGUOUS rather than forcing voiced/unvoiced.
        return Voicing.AMBIGUOUS
    return Voicing.AMBIGUOUS


@dataclass(frozen=True, slots=True)
class VoicingDiscrimination:
    """Voiced/unvoiced/ambiguous result decided by the certified recognizer,
    plus its provenance receipt."""

    status: Voicing
    per_band_winding_magnitude: tuple[int, ...]
    low_band_winding_magnitude_sum: int
    high_band_winding_magnitude_sum: int
    recognition_status: str
    winner_mode_index: int | None
    recognition_receipt_sha256: str | None
    fragment_receipt_sha256: str
    receipt_sha256: str
    receipt_payload: bytes

    def verify(self, fragment_receipt: AuditoryFragmentReceipt) -> None:
        fragment_receipt = _require_fragment_receipt(fragment_receipt)
        if fragment_receipt.receipt_sha256 != self.fragment_receipt_sha256:
            raise ReceiptError(
                "voicing result cites a different auditory fragment receipt"
            )
        per_band = _per_band_winding_magnitude(fragment_receipt.fragment)
        low = sum(
            per_band[AUDITORY_BAND_ORDER.index(band)] for band in LOW_BANDS
        )
        high = sum(
            per_band[AUDITORY_BAND_ORDER.index(band)] for band in HIGH_BANDS
        )
        if (
            per_band != self.per_band_winding_magnitude
            or low != self.low_band_winding_magnitude_sum
            or high != self.high_band_winding_magnitude_sum
        ):
            raise ReceiptError(
                "voicing result does not match the cited fragment's exact "
                "per-band winding magnitudes"
            )
        expected_status = _voicing_status_from_recognition(
            self.recognition_status, self.winner_mode_index
        )
        if self.recognition_status == _ZERO_WINDING_RECOGNITION_STATUS:
            expected_status = Voicing.AMBIGUOUS
        if expected_status is not self.status:
            raise ReceiptError(
                "voicing status is not the honest mapping of its recognizer "
                "outcome"
            )
        if self.recognition_receipt_sha256 is not None:
            sha256_digest(
                self.recognition_receipt_sha256, "voicing recognition receipt"
            )
        expected = _voicing_payload(
            fragment_receipt_sha256=self.fragment_receipt_sha256,
            per_band_winding_magnitude=self.per_band_winding_magnitude,
            low_band_winding_magnitude_sum=self.low_band_winding_magnitude_sum,
            high_band_winding_magnitude_sum=self.high_band_winding_magnitude_sum,
            recognition_status=self.recognition_status,
            winner_mode_index=self.winner_mode_index,
            recognition_receipt_sha256=self.recognition_receipt_sha256,
            status=self.status,
        )
        if (
            self.receipt_payload != expected
            or receipt_sha256(expected) != self.receipt_sha256
        ):
            raise ReceiptError("voicing result differs from its canonical receipt")


@dataclass(frozen=True, slots=True)
class SoundDiscrimination:
    """Combined presence + (when present) voicing discrimination for one
    authenticated cochlear-transduction fragment, with a receipt binding both
    sub-results to the exact cited fragment."""

    fragment_receipt_sha256: str
    presence: SoundPresenceDiscrimination
    voicing: VoicingDiscrimination | None
    receipt_sha256: str
    receipt_payload: bytes

    def verify(self, fragment_receipt: AuditoryFragmentReceipt) -> None:
        fragment_receipt = _require_fragment_receipt(fragment_receipt)
        if fragment_receipt.receipt_sha256 != self.fragment_receipt_sha256:
            raise ReceiptError(
                "sound discrimination cites a different auditory fragment receipt"
            )
        self.presence.verify(fragment_receipt)
        if self.presence.status is SoundPresence.SILENCE:
            if self.voicing is not None:
                raise ReceiptError(
                    "silent capture must not carry a voicing sub-result"
                )
        else:
            if self.voicing is None:
                raise ReceiptError(
                    "present capture must carry a voicing sub-result"
                )
            self.voicing.verify(fragment_receipt)
        expected = _result_payload(
            fragment_receipt_sha256=self.fragment_receipt_sha256,
            presence_receipt_sha256=self.presence.receipt_sha256,
            voicing_receipt_sha256=(
                None if self.voicing is None else self.voicing.receipt_sha256
            ),
        )
        if (
            self.receipt_payload != expected
            or receipt_sha256(expected) != self.receipt_sha256
        ):
            raise ReceiptError(
                "sound discrimination differs from its canonical receipt"
            )


def _result_payload(
    *,
    fragment_receipt_sha256: str,
    presence_receipt_sha256: str,
    voicing_receipt_sha256: str | None,
) -> bytes:
    return _canonical_bytes(
        {
            "fragment_receipt_sha256": fragment_receipt_sha256,
            "presence_receipt_sha256": presence_receipt_sha256,
            "schema": _RESULT_SCHEMA,
            "voicing_receipt_sha256": voicing_receipt_sha256,
        }
    )


# ---------------------------------------------------------------------------
# Public entry points.
# ---------------------------------------------------------------------------


def discriminate_sound_presence(
    fragment_receipt: AuditoryFragmentReceipt,
) -> SoundPresenceDiscrimination:
    """Exact silence vs. speech-presence from an authenticated fragment.

    SILENCE iff not one cochlear band registered a single winding-transition
    event (total n_events exactly zero); SPEECH_PRESENT otherwise. Fails
    closed (ReceiptError) if the fragment receipt is tampered or missing.
    """

    fragment_receipt = _require_fragment_receipt(fragment_receipt)
    per_band = _per_band_n_events(fragment_receipt.fragment)
    total = sum(per_band)
    status = (
        SoundPresence.SILENCE if total == 0 else SoundPresence.SPEECH_PRESENT
    )
    payload = _presence_payload(
        fragment_receipt_sha256=fragment_receipt.receipt_sha256,
        per_band_n_events=per_band,
        total_n_events=total,
        status=status,
    )
    return SoundPresenceDiscrimination(
        status=status,
        total_n_events=total,
        per_band_n_events=per_band,
        fragment_receipt_sha256=fragment_receipt.receipt_sha256,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def discriminate_voicing(
    fragment_receipt: AuditoryFragmentReceipt,
) -> VoicingDiscrimination:
    """Voiced / unvoiced / ambiguous from an authenticated fragment, decided
    by the real certified interval-dominance recognizer over the exact
    per-band winding magnitudes.

    Intended for a present capture. A silent (all-zero) capture, or a present
    capture with no coherent winding anywhere, has no certified-positive
    field energy for the recognizer to compare and therefore honestly returns
    AMBIGUOUS (never a forced voiced/unvoiced guess). Fails closed if the
    fragment receipt is tampered or missing.
    """

    fragment_receipt = _require_fragment_receipt(fragment_receipt)
    per_band = _per_band_winding_magnitude(fragment_receipt.fragment)
    low = sum(per_band[AUDITORY_BAND_ORDER.index(band)] for band in LOW_BANDS)
    high = sum(per_band[AUDITORY_BAND_ORDER.index(band)] for band in HIGH_BANDS)

    if sum(per_band) == 0:
        recognition_status = _ZERO_WINDING_RECOGNITION_STATUS
        winner_mode_index: int | None = None
        recognition_receipt_sha256: str | None = None
        status = Voicing.AMBIGUOUS
    else:
        recognition_status, winner_mode_index, recognition_receipt_sha256 = (
            _recognize_voicing(per_band)
        )
        status = _voicing_status_from_recognition(
            recognition_status, winner_mode_index
        )

    payload = _voicing_payload(
        fragment_receipt_sha256=fragment_receipt.receipt_sha256,
        per_band_winding_magnitude=per_band,
        low_band_winding_magnitude_sum=low,
        high_band_winding_magnitude_sum=high,
        recognition_status=recognition_status,
        winner_mode_index=winner_mode_index,
        recognition_receipt_sha256=recognition_receipt_sha256,
        status=status,
    )
    return VoicingDiscrimination(
        status=status,
        per_band_winding_magnitude=per_band,
        low_band_winding_magnitude_sum=low,
        high_band_winding_magnitude_sum=high,
        recognition_status=recognition_status,
        winner_mode_index=winner_mode_index,
        recognition_receipt_sha256=recognition_receipt_sha256,
        fragment_receipt_sha256=fragment_receipt.receipt_sha256,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def discriminate_sound(
    fragment_receipt: AuditoryFragmentReceipt,
) -> SoundDiscrimination:
    """Full first-milestone discrimination for one authenticated fragment:
    exact presence, and -- only when present -- recognizer-decided voicing.

    Silence carries no voicing sub-result (there is nothing to voice). Fails
    closed if the fragment receipt is tampered or missing.
    """

    fragment_receipt = _require_fragment_receipt(fragment_receipt)
    presence = discriminate_sound_presence(fragment_receipt)
    voicing = (
        None
        if presence.status is SoundPresence.SILENCE
        else discriminate_voicing(fragment_receipt)
    )
    payload = _result_payload(
        fragment_receipt_sha256=fragment_receipt.receipt_sha256,
        presence_receipt_sha256=presence.receipt_sha256,
        voicing_receipt_sha256=(
            None if voicing is None else voicing.receipt_sha256
        ),
    )
    return SoundDiscrimination(
        fragment_receipt_sha256=fragment_receipt.receipt_sha256,
        presence=presence,
        voicing=voicing,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


# ---------------------------------------------------------------------------
# Convenience: authenticate raw cochlear_transduce() output into the fragment
# receipt this module consumes. Provided so real callers/tests can go from a
# real cochlear_transduce() result to a discrimination without hand-building
# the receipt; it only drops the per-band "filtered" ndarray (not physical
# evidence past the boundary, exactly as auditory_fragment_receipt documents)
# and keeps the exact winding/n_events/events.
# ---------------------------------------------------------------------------


def build_auditory_fragment_receipt_from_cochlear(
    cochlear_output: Mapping[str, Mapping[str, object]],
    *,
    source_id: str,
    born_tick: int,
    sample_rate_hz: int,
    input_sample_count: int,
) -> AuditoryFragmentReceipt:
    """Authenticate a real ``cochlear_transduce()`` result as an
    ``AuditoryFragmentReceipt``. Raises ReceiptError (fails closed) if the
    cochlear output is not the exact mounted six-band shape."""

    if set(cochlear_output) != set(AUDITORY_BAND_ORDER):
        raise ReceiptError(
            "cochlear output does not carry the exact mounted six-band set"
        )
    bands = {
        band: {
            "winding": int(cochlear_output[band]["winding"]),
            "n_events": int(cochlear_output[band]["n_events"]),
            "events": [
                {"t": float(e["t"]), "dw": int(e["dw"]), "s": float(e["s"])}
                for e in cochlear_output[band]["events"]  # type: ignore[index]
            ],
        }
        for band in AUDITORY_BAND_ORDER
    }
    fragment = AuditoryPerceptFragment(
        source_id=source_id,
        born_tick=born_tick,
        sample_rate_hz=sample_rate_hz,
        input_sample_count=input_sample_count,
        bands=bands,
    )
    return auditory_fragment_receipt(fragment)


__all__ = (
    "LOW_BANDS",
    "HIGH_BANDS",
    "BAND_SPLIT_MIDPOINT_HZ",
    "SoundPresence",
    "Voicing",
    "SoundPresenceDiscrimination",
    "VoicingDiscrimination",
    "SoundDiscrimination",
    "discriminate_sound_presence",
    "discriminate_voicing",
    "discriminate_sound",
    "build_auditory_fragment_receipt_from_cochlear",
)
