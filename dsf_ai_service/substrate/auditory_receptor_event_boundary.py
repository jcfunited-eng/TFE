"""Exact cochlear receptor-event boundary for full-field neuron intake.

This boundary never decides that two sounds are the same.  It mounts the
physical event that an individual auditory neuron may receive:

* one of the sixteen retained gammatone channels;
* measured pressure amplitude and its exact energy relevance ``r = p^2``;
* cumulative carrier phase and integer winding since the prior observation;
* the complete paired pressure and phase ``D/M/R/U/C/P/B`` field tuples.

The relevance law follows the already-mounted GLEW coherence operator.  That
operator constructs a phasor as ``sqrt(relevance) * exp(i*phase)``; setting
``relevance = pressure_amplitude**2`` therefore makes its phasor amplitude
exactly the measured pressure amplitude.  No threshold, selected band,
normalized co-firing score, chi, text, or identity is introduced.

Publication is fail closed.  In particular, the event is typed UNRESOLVED
unless both members of every pressure/phase pair reached frozen L0 with that
exact per-frame relevance and every source frame is covered by one complete
L4 tuple.  An unresolved result carries ``event=None``; it is never converted
to a zero-valued event.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    sha256_digest,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5Experience,
    AuditoryL5FieldTuple,
    AuditoryL5KernelComponent,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryVerifiedSettlementCapability,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactSubstreamInterpretation,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    AUDITORY_FULL_FIELD_PROVIDER_SCHEMA,
    COCHLEAR_CHANNEL_COUNT,
    MAX_CAPTURE_SECONDS,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    AuditoryFullFieldCapture,
)


AUDITORY_RECEPTOR_EVENT_PROFILE = (
    b"guala.auditory_receptor_event.full_field.v1"
)
AUDITORY_RECEPTOR_CAPTURE_SCHEMA = (
    "guala.auditory_receptor_event.capture.v1"
)
AUDITORY_RECEPTOR_CHANNEL_SCHEMA = (
    "guala.auditory_receptor_event.channel.v1"
)
AUDITORY_RECEPTOR_EVENT_SCHEMA = (
    "guala.auditory_receptor_event.full_field.v1"
)
MAX_AUDITORY_RECEPTOR_FRAMES = (
    MAX_CAPTURE_SECONDS
    * REQUIRED_SAMPLE_RATE_HZ
    // OBSERVATION_HOP_SAMPLES
)
_VERIFIED_RECEPTOR_EVENT_AUTHORITY = object()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or "/" not in value:
        raise ReceiptError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as exc:
        raise ReceiptError(f"{name} is not an exact fraction") from exc
    if f"{result.numerator}/{result.denominator}" != value:
        raise ReceiptError(f"{name} is not canonically encoded")
    return result


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "auditory receptor exact value")
    return f"{value.numerator}/{value.denominator}"


def _binary64(value: object, name: str) -> Fraction:
    if isinstance(value, bool):
        raise ReceiptError(f"{name} is not finite binary64")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ReceiptError(f"{name} is not finite binary64") from exc
    if not math.isfinite(number):
        raise ReceiptError(f"{name} is not finite binary64")
    return Fraction.from_float(number)


def auditory_pressure_energy_relevance(
    pressure_amplitude: object,
) -> Fraction:
    """Return the exact physical relevance ``r=p^2`` for one sample."""

    pressure = _binary64(
        pressure_amplitude,
        "auditory receptor pressure amplitude",
    )
    if not 0 <= pressure <= 1:
        raise ReceiptError(
            "auditory receptor pressure left full-scale calibration"
        )
    return pressure * pressure


class AuditoryReceptorEventState(str, Enum):
    OBSERVED = "observed"
    UNRESOLVED = "unresolved"


class AuditoryWindingState(str, Enum):
    SETTLED = "settled"
    PRIOR_PHASE_UNRESOLVED = "prior_phase_unresolved"


@dataclass(frozen=True, slots=True)
class AuditoryReceptorFieldTuple:
    tuple_index: int
    fields: tuple[tuple[str, Fraction], ...]
    source_l0_l4_trace_receipt_sha256: str
    authority_receipt_sha256: str

    def verify(self, expected_index: int, trace_digest: str) -> None:
        if self.tuple_index != expected_index:
            raise ReceiptError(
                "auditory receptor full-field sequence is incomplete"
            )
        if tuple(name for name, _ in self.fields) != DSF_FIELD_ORDER:
            raise ReceiptError(
                "auditory receptor event flattened the DSF field"
            )
        for name, value in self.fields:
            require_fraction(value, f"auditory receptor {name}")
        if self.source_l0_l4_trace_receipt_sha256 != trace_digest:
            raise ReceiptError(
                "auditory receptor field belongs to another L0-L4 trace"
            )
        sha256_digest(
            self.authority_receipt_sha256,
            "auditory receptor L4 tuple receipt",
        )


@dataclass(frozen=True, slots=True)
class AuditoryReceptorFrame:
    source_index: int
    source_time: Fraction
    causal_offset: Fraction
    pressure_amplitude: Fraction
    relevance: Fraction
    cumulative_phase_turns: Fraction
    phase_advance_turns: Fraction
    winding_state: AuditoryWindingState
    winding_delta: int | None
    pressure_field_tuple_index: int
    phase_field_tuple_index: int

    def verify(
        self,
        *,
        expected_index: int,
        prior_phase: Fraction | None,
        pressure_field_count: int,
        phase_field_count: int,
    ) -> None:
        if self.source_index != expected_index:
            raise ReceiptError(
                "auditory receptor source sequence is incomplete"
            )
        for name, value in (
            ("source time", self.source_time),
            ("causal offset", self.causal_offset),
            ("pressure", self.pressure_amplitude),
            ("relevance", self.relevance),
            ("cumulative phase", self.cumulative_phase_turns),
            ("phase advance", self.phase_advance_turns),
        ):
            require_fraction(value, f"auditory receptor {name}")
        if not 0 <= self.pressure_amplitude <= 1:
            raise ReceiptError(
                "auditory receptor pressure left full-scale calibration"
            )
        if self.relevance != self.pressure_amplitude ** 2:
            raise ReceiptError(
                "auditory receptor relevance is not exact pressure energy"
            )
        if not (
            0 <= self.pressure_field_tuple_index < pressure_field_count
            and 0 <= self.phase_field_tuple_index < phase_field_count
        ):
            raise ReceiptError(
                "auditory receptor frame lost its paired full field"
            )
        if prior_phase is None:
            if (
                self.winding_state
                is not AuditoryWindingState.PRIOR_PHASE_UNRESOLVED
                or self.winding_delta is not None
            ):
                raise ReceiptError(
                    "auditory receptor unresolved winding was converted to zero"
                )
        else:
            expected = (
                math.floor(self.cumulative_phase_turns)
                - math.floor(prior_phase)
            )
            if (
                self.winding_state is not AuditoryWindingState.SETTLED
                or isinstance(self.winding_delta, bool)
                or self.winding_delta != expected
            ):
                raise ReceiptError(
                    "auditory receptor winding differs from cumulative phase"
                )


def _field_payload(value: AuditoryReceptorFieldTuple) -> dict[str, object]:
    return {
        "authority_receipt_sha256": value.authority_receipt_sha256,
        "fields": [
            [name, _fraction_text(field)]
            for name, field in value.fields
        ],
        "source_l0_l4_trace_receipt_sha256": (
            value.source_l0_l4_trace_receipt_sha256
        ),
        "tuple_index": value.tuple_index,
    }


def _frame_payload(value: AuditoryReceptorFrame) -> dict[str, object]:
    return {
        "causal_offset": _fraction_text(value.causal_offset),
        "cumulative_phase_turns": _fraction_text(
            value.cumulative_phase_turns
        ),
        "phase_advance_turns": _fraction_text(
            value.phase_advance_turns
        ),
        "phase_field_tuple_index": value.phase_field_tuple_index,
        "pressure_amplitude": _fraction_text(value.pressure_amplitude),
        "pressure_field_tuple_index": value.pressure_field_tuple_index,
        "relevance": _fraction_text(value.relevance),
        "source_index": value.source_index,
        "source_time": _fraction_text(value.source_time),
        "winding_delta": value.winding_delta,
        "winding_state": value.winding_state.value,
    }


def _channel_payload(
    *,
    cochlear_index: int,
    channel_id: str,
    pressure_trace_receipt_sha256: str,
    phase_trace_receipt_sha256: str,
    pressure_fields: tuple[AuditoryReceptorFieldTuple, ...],
    phase_fields: tuple[AuditoryReceptorFieldTuple, ...],
    frames: tuple[AuditoryReceptorFrame, ...],
    prior_cumulative_phase_turns: Fraction | None,
) -> bytes:
    return _canonical_bytes({
        "channel_id": channel_id,
        "cochlear_index": cochlear_index,
        "frames": [_frame_payload(value) for value in frames],
        "phase_fields": [_field_payload(value) for value in phase_fields],
        "phase_trace_receipt_sha256": phase_trace_receipt_sha256,
        "pressure_fields": [
            _field_payload(value) for value in pressure_fields
        ],
        "pressure_trace_receipt_sha256": (
            pressure_trace_receipt_sha256
        ),
        "prior_cumulative_phase_turns": (
            _fraction_text(prior_cumulative_phase_turns)
            if prior_cumulative_phase_turns is not None
            else None
        ),
        "schema": AUDITORY_RECEPTOR_CHANNEL_SCHEMA,
    })


@dataclass(frozen=True, slots=True)
class AuditoryReceptorChannelEvent:
    cochlear_index: int
    channel_id: str
    pressure_trace_receipt_sha256: str
    phase_trace_receipt_sha256: str
    pressure_fields: tuple[AuditoryReceptorFieldTuple, ...]
    phase_fields: tuple[AuditoryReceptorFieldTuple, ...]
    frames: tuple[AuditoryReceptorFrame, ...]
    prior_cumulative_phase_turns: Fraction | None
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return _channel_payload(
            cochlear_index=self.cochlear_index,
            channel_id=self.channel_id,
            pressure_trace_receipt_sha256=(
                self.pressure_trace_receipt_sha256
            ),
            phase_trace_receipt_sha256=self.phase_trace_receipt_sha256,
            pressure_fields=self.pressure_fields,
            phase_fields=self.phase_fields,
            frames=self.frames,
            prior_cumulative_phase_turns=(
                self.prior_cumulative_phase_turns
            ),
        )

    def verify(self, registry: ReceiptRegistry) -> None:
        if (
            self.cochlear_index < 0
            or self.cochlear_index >= COCHLEAR_CHANNEL_COUNT
            or self.channel_id
            != AUDITORY_CHANNELS[self.cochlear_index].name
            or not self.frames
            or len(self.frames) > MAX_AUDITORY_RECEPTOR_FRAMES
        ):
            raise ReceiptError(
                "auditory receptor channel topology changed"
            )
        for value, name in (
            (
                self.pressure_trace_receipt_sha256,
                "auditory receptor pressure trace receipt",
            ),
            (
                self.phase_trace_receipt_sha256,
                "auditory receptor phase trace receipt",
            ),
        ):
            sha256_digest(value, name)
        if not self.pressure_fields or not self.phase_fields:
            raise ReceiptError(
                "auditory receptor channel lacks a paired full field"
            )
        for index, value in enumerate(self.pressure_fields):
            value.verify(index, self.pressure_trace_receipt_sha256)
        for index, value in enumerate(self.phase_fields):
            value.verify(index, self.phase_trace_receipt_sha256)
        prior_phase = self.prior_cumulative_phase_turns
        if prior_phase is not None:
            require_fraction(
                prior_phase,
                "auditory receptor prior cumulative phase",
            )
        for index, frame in enumerate(self.frames):
            frame.verify(
                expected_index=index,
                prior_phase=prior_phase,
                pressure_field_count=len(self.pressure_fields),
                phase_field_count=len(self.phase_fields),
            )
            prior_phase = frame.cumulative_phase_turns
        expected = self.payload()
        mounted = registry.resolve(
            self.authority_receipt_sha256,
            "auditory receptor channel authority",
        )
        if (
            mounted != expected
            or receipt_sha256(expected)
            != self.authority_receipt_sha256
        ):
            raise ReceiptError(
                "auditory receptor channel authority changed"
            )


def _capture_payload(capture: AuditoryFullFieldCapture) -> bytes:
    return _canonical_bytes({
        "channels": [
            {
                "carrier_phase_advance_turns": [
                    value.hex()
                    for value in channel.carrier_phase_advance_turns
                ],
                "carrier_phase_turns": [
                    value.hex() for value in channel.carrier_phase_turns
                ],
                "channel_id": channel.definition.name,
                "pressure_envelope_full_scale": [
                    value.hex()
                    for value in channel.pressure_envelope_full_scale
                ],
            }
            for channel in capture.channels
        ],
        "continuation_receipt_sha256": (
            capture.continuation_receipt_sha256
        ),
        "frame_count": capture.frame_count,
        "input_sample_count": capture.input_sample_count,
        "observation_hop_samples": capture.observation_hop_samples,
        "provider_schema": capture.provider_schema,
        "schema": AUDITORY_RECEPTOR_CAPTURE_SCHEMA,
        "source_first_sample_index": capture.source_first_sample_index,
        "source_sample_rate_hz": capture.source_sample_rate_hz,
    })


def _event_payload(
    *,
    capture_receipt_sha256: str,
    auditory_l5_authority_receipt_sha256: str,
    auditory_l5_experience_id: str,
    channel_receipt_sha256s: tuple[str, ...],
    frame_count: int,
) -> bytes:
    return _canonical_bytes({
        "auditory_l5_authority_receipt_sha256": (
            auditory_l5_authority_receipt_sha256
        ),
        "auditory_l5_experience_id": auditory_l5_experience_id,
        "capture_receipt_sha256": capture_receipt_sha256,
        "channel_receipt_sha256s": list(channel_receipt_sha256s),
        "cochlear_channel_count": COCHLEAR_CHANNEL_COUNT,
        "field_order": list(DSF_FIELD_ORDER),
        "frame_count": frame_count,
        "relevance_law": (
            "r=pressure_amplitude^2;"
            "sqrt(relevance)=pressure_amplitude"
        ),
        "schema": AUDITORY_RECEPTOR_EVENT_SCHEMA,
    })


@dataclass(frozen=True, slots=True)
class AuditoryReceptorFullFieldEvent:
    capture_receipt_sha256: str
    auditory_l5_authority_receipt_sha256: str
    auditory_l5_experience_id: str
    channels: tuple[AuditoryReceptorChannelEvent, ...]
    frame_count: int
    authority_receipt_sha256: str
    receipt_registry: ReceiptRegistry

    def verify(self) -> None:
        if (
            self.receipt_registry.profile_binding_sha256
            != receipt_sha256(AUDITORY_RECEPTOR_EVENT_PROFILE)
            or len(self.channels) != COCHLEAR_CHANNEL_COUNT
            or tuple(value.cochlear_index for value in self.channels)
            != tuple(range(COCHLEAR_CHANNEL_COUNT))
            or not 0 < self.frame_count <= MAX_AUDITORY_RECEPTOR_FRAMES
            or any(
                len(value.frames) != self.frame_count
                for value in self.channels
            )
        ):
            raise ReceiptError(
                "auditory receptor full-field boundary changed"
            )
        self.receipt_registry.resolve(
            self.capture_receipt_sha256,
            "auditory receptor capture receipt",
        )
        sha256_digest(
            self.auditory_l5_authority_receipt_sha256,
            "auditory receptor upstream L5 receipt",
        )
        sha256_digest(
            self.auditory_l5_experience_id,
            "auditory receptor upstream experience id",
        )
        for channel in self.channels:
            channel.verify(self.receipt_registry)
        payload = _event_payload(
            capture_receipt_sha256=self.capture_receipt_sha256,
            auditory_l5_authority_receipt_sha256=(
                self.auditory_l5_authority_receipt_sha256
            ),
            auditory_l5_experience_id=self.auditory_l5_experience_id,
            channel_receipt_sha256s=tuple(
                value.authority_receipt_sha256
                for value in self.channels
            ),
            frame_count=self.frame_count,
        )
        mounted = self.receipt_registry.resolve(
            self.authority_receipt_sha256,
            "auditory receptor full-field authority",
        )
        if (
            mounted != payload
            or receipt_sha256(payload) != self.authority_receipt_sha256
        ):
            raise ReceiptError(
                "auditory receptor full-field authority changed"
            )


@dataclass(frozen=True, slots=True)
class AuditoryVerifiedReceptorEventCapability:
    """Unforgeable request-local custody for one deeply verified event."""

    event: AuditoryReceptorFullFieldEvent = field(
        compare=False,
        repr=False,
    )
    _construction_authority: object = field(compare=False, repr=False)

    def verify_identity(
        self,
        event: AuditoryReceptorFullFieldEvent,
    ) -> None:
        if (
            self._construction_authority
            is not _VERIFIED_RECEPTOR_EVENT_AUTHORITY
            or event is not self.event
        ):
            raise ValueError(
                "auditory receptor event left verified custody"
            )


@dataclass(frozen=True, slots=True)
class AuditoryReceptorEventResult:
    state: AuditoryReceptorEventState
    event: AuditoryReceptorFullFieldEvent | None
    reason: str
    verified_capability: AuditoryVerifiedReceptorEventCapability | None


def _unresolved(reason: str) -> AuditoryReceptorEventResult:
    return AuditoryReceptorEventResult(
        state=AuditoryReceptorEventState.UNRESOLVED,
        event=None,
        reason=reason,
        verified_capability=None,
    )


def _trace(
    experience: AuditoryL5Experience,
    component: AuditoryL5KernelComponent,
) -> dict[str, object]:
    raw = json.loads(
        experience.upstream_receipt_registry.resolve(
            component.l0_l4_trace_receipt_sha256,
            "auditory receptor source L0-L4 trace",
        )
    )
    if (
        not isinstance(raw, dict)
        or raw.get("port_id") != component.substream_id
        or raw.get("source_stream_receipt_sha256")
        != component.source_stream_receipt_sha256
    ):
        raise ReceiptError(
            "auditory receptor source trace belongs to another component"
        )
    return raw


def _field_authority(
    component: AuditoryL5KernelComponent,
    raw: dict[str, object],
) -> tuple[
    tuple[AuditoryReceptorFieldTuple, ...],
    tuple[int, ...],
    tuple[Fraction, ...],
]:
    l0 = raw.get("L0_SEV")
    l1 = raw.get("L1_GateL1State")
    l4 = raw.get("L4_DSF")
    if (
        not isinstance(l0, list)
        or len(l0) != len(component.samples)
        or not isinstance(l1, list)
        or not isinstance(l4, list)
        or len(l1) != len(l4)
        or len(l4) != len(component.l4_field_tuples)
        or not l4
    ):
        raise ReceiptError(
            "auditory receptor source trace is incomplete"
        )
    relevances = tuple(
        _fraction(row.get("relevance"), "auditory receptor L0 relevance")
        if isinstance(row, dict)
        else (_ for _ in ()).throw(
            ReceiptError("auditory receptor L0 row is malformed")
        )
        for row in l0
    )
    fields = []
    support = [-1] * len(component.samples)
    for index, (gate, row, authority) in enumerate(
        zip(l1, l4, component.l4_field_tuples, strict=True)
    ):
        if not isinstance(gate, dict) or not isinstance(row, dict):
            raise ReceiptError(
                "auditory receptor source gate is malformed"
            )
        start = gate.get("start_idx")
        end = gate.get("end_idx")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or not 0 <= start <= end < len(support)
        ):
            raise ReceiptError(
                "auditory receptor source support is invalid"
            )
        exact_fields = tuple(
            (
                name,
                _fraction(
                    row.get(name),
                    f"auditory receptor L4 {name}",
                ),
            )
            for name in DSF_FIELD_ORDER
        )
        if exact_fields != authority.fields:
            raise ReceiptError(
                "auditory receptor L4 fields differ from L5 authority"
            )
        for source_index in range(start, end + 1):
            if support[source_index] != -1:
                raise ReceiptError(
                    "auditory receptor source supports overlap"
                )
            support[source_index] = index
        fields.append(AuditoryReceptorFieldTuple(
            tuple_index=index,
            fields=exact_fields,
            source_l0_l4_trace_receipt_sha256=(
                component.l0_l4_trace_receipt_sha256
            ),
            authority_receipt_sha256=(
                authority.authority_receipt_sha256
            ),
        ))
    if any(value < 0 for value in support):
        raise ReceiptError(
            "auditory receptor source support has a causal gap"
        )
    return tuple(fields), tuple(support), relevances


def _channel_event(
    *,
    capture: AuditoryFullFieldCapture,
    experience: AuditoryL5Experience,
    cochlear_index: int,
) -> tuple[AuditoryReceptorChannelEvent, bytes]:
    capture_channel = capture.channels[cochlear_index]
    l5_channel = experience.channels[cochlear_index]
    pressure = l5_channel.pressure
    phase = l5_channel.carrier_phase_advance
    pressure_raw = _trace(experience, pressure)
    phase_raw = _trace(experience, phase)
    pressure_fields, pressure_support, pressure_relevance = (
        _field_authority(pressure, pressure_raw)
    )
    phase_fields, phase_support, phase_relevance = _field_authority(
        phase, phase_raw
    )
    if not (
        len(pressure.samples)
        == len(phase.samples)
        == capture.frame_count
    ):
        raise ReceiptError(
            "auditory receptor paired source cardinality changed"
        )
    frames = []
    prior_phase = None
    if (
        capture.rephase_seed is not None
        and not capture.rephase_seed.is_genesis
    ):
        prior_phase = _binary64(
            capture.rephase_seed.phase_turns[cochlear_index],
            "auditory receptor prior cumulative phase",
        )
    for index, (pressure_sample, phase_sample) in enumerate(
        zip(pressure.samples, phase.samples, strict=True)
    ):
        pressure_value = _binary64(
            capture_channel.pressure_envelope_full_scale[index],
            "auditory receptor pressure",
        )
        relevance = pressure_value ** 2
        kernel_relevance = Fraction.from_float(float(relevance))
        phase_signal = _binary64(
            capture_channel.carrier_phase_advance_nyquist_fraction[
                index
            ],
            "auditory receptor normalized phase advance",
        )
        phase_advance = _binary64(
            capture_channel.carrier_phase_advance_turns[index],
            "auditory receptor phase advance",
        )
        cumulative_phase = _binary64(
            capture_channel.carrier_phase_turns[index],
            "auditory receptor cumulative phase",
        )
        if (
            pressure_sample.source_index != index
            or phase_sample.source_index != index
            or pressure_sample.source_time != phase_sample.source_time
            or pressure_sample.causal_offset != phase_sample.causal_offset
            or pressure_sample.signal != pressure_value
            or pressure_sample.relevance != relevance
            or phase_sample.signal != phase_signal
            or phase_sample.relevance != relevance
            or phase_sample.phase_turns != cumulative_phase
            or pressure_relevance[index] != kernel_relevance
            or phase_relevance[index] != kernel_relevance
        ):
            raise ReceiptError(
                "auditory receptor pressure-energy relevance is not "
                "mounted on the complete pressure/phase pair"
            )
        winding_state = (
            AuditoryWindingState.PRIOR_PHASE_UNRESOLVED
            if prior_phase is None
            else AuditoryWindingState.SETTLED
        )
        winding_delta = (
            None
            if prior_phase is None
            else math.floor(cumulative_phase) - math.floor(prior_phase)
        )
        frames.append(AuditoryReceptorFrame(
            source_index=index,
            source_time=pressure_sample.source_time,
            causal_offset=pressure_sample.causal_offset,
            pressure_amplitude=pressure_value,
            relevance=relevance,
            cumulative_phase_turns=cumulative_phase,
            phase_advance_turns=phase_advance,
            winding_state=winding_state,
            winding_delta=winding_delta,
            pressure_field_tuple_index=pressure_support[index],
            phase_field_tuple_index=phase_support[index],
        ))
        prior_phase = cumulative_phase
    provisional = AuditoryReceptorChannelEvent(
        cochlear_index=cochlear_index,
        channel_id=capture_channel.definition.name,
        pressure_trace_receipt_sha256=(
            pressure.l0_l4_trace_receipt_sha256
        ),
        phase_trace_receipt_sha256=(
            phase.l0_l4_trace_receipt_sha256
        ),
        pressure_fields=pressure_fields,
        phase_fields=phase_fields,
        frames=tuple(frames),
        prior_cumulative_phase_turns=(
            None
            if capture.rephase_seed is None
            or capture.rephase_seed.is_genesis
            else _binary64(
                capture.rephase_seed.phase_turns[cochlear_index],
                "auditory receptor prior cumulative phase",
            )
        ),
        authority_receipt_sha256="0" * 64,
    )
    payload = provisional.payload()
    return (
        AuditoryReceptorChannelEvent(
            cochlear_index=provisional.cochlear_index,
            channel_id=provisional.channel_id,
            pressure_trace_receipt_sha256=(
                provisional.pressure_trace_receipt_sha256
            ),
            phase_trace_receipt_sha256=(
                provisional.phase_trace_receipt_sha256
            ),
            pressure_fields=provisional.pressure_fields,
            phase_fields=provisional.phase_fields,
            frames=provisional.frames,
            prior_cumulative_phase_turns=(
                provisional.prior_cumulative_phase_turns
            ),
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def settle_auditory_receptor_event(
    *,
    capture: AuditoryFullFieldCapture | None,
    auditory_l5: AuditoryL5Experience | None,
    verified_settlement_capability: (
        AuditoryVerifiedSettlementCapability | None
    ) = None,
) -> AuditoryReceptorEventResult:
    """Publish one complete receptor event or typed UNRESOLVED/null."""

    try:
        if not isinstance(capture, AuditoryFullFieldCapture):
            raise ReceiptError(
                "typed auditory full-field capture is unavailable"
            )
        if verified_settlement_capability is None:
            capture.__post_init__()
        else:
            if not isinstance(
                verified_settlement_capability,
                AuditoryVerifiedSettlementCapability,
            ):
                raise TypeError(
                    "auditory receptor verified settlement is not typed"
                )
            verified_settlement_capability.verify_linkage(
                pcm_s16le=verified_settlement_capability.pcm_s16le,
                capture=capture,
                auditory_l5=auditory_l5,
                transport=verified_settlement_capability.transport,
                cochlear=verified_settlement_capability.cochlear,
                causal_settlement=(
                    verified_settlement_capability.causal_settlement
                ),
                joint_settlement=(
                    verified_settlement_capability.joint_settlement
                ),
            )
        if (
            capture.provider_schema
            != AUDITORY_FULL_FIELD_PROVIDER_SCHEMA
            or capture.frame_count <= 0
            or capture.frame_count > MAX_AUDITORY_RECEPTOR_FRAMES
        ):
            raise ReceiptError(
                "auditory receptor capture boundary changed"
            )
        if not isinstance(auditory_l5, AuditoryL5Experience):
            raise ReceiptError(
                "typed complete auditory L5 experience is unavailable"
            )
        if verified_settlement_capability is None:
            auditory_l5.verify()
        if len(auditory_l5.channels) != COCHLEAR_CHANNEL_COUNT:
            raise ReceiptError(
                "auditory receptor L5 topology changed"
            )
        channel_results = tuple(
            _channel_event(
                capture=capture,
                experience=auditory_l5,
                cochlear_index=index,
            )
            for index in range(COCHLEAR_CHANNEL_COUNT)
        )
        channels = tuple(value for value, _ in channel_results)
        channel_payloads = tuple(payload for _, payload in channel_results)
        capture_payload = _capture_payload(capture)
        capture_digest = receipt_sha256(capture_payload)
        event_payload = _event_payload(
            capture_receipt_sha256=capture_digest,
            auditory_l5_authority_receipt_sha256=(
                auditory_l5.authority_receipt_sha256
            ),
            auditory_l5_experience_id=auditory_l5.experience_id,
            channel_receipt_sha256s=tuple(
                value.authority_receipt_sha256 for value in channels
            ),
            frame_count=capture.frame_count,
        )
        registry = ReceiptRegistry.from_payloads(
            profile_payload=AUDITORY_RECEPTOR_EVENT_PROFILE,
            receipt_payloads=(
                capture_payload,
                *channel_payloads,
                event_payload,
            ),
        )
        event = AuditoryReceptorFullFieldEvent(
            capture_receipt_sha256=capture_digest,
            auditory_l5_authority_receipt_sha256=(
                auditory_l5.authority_receipt_sha256
            ),
            auditory_l5_experience_id=auditory_l5.experience_id,
            channels=channels,
            frame_count=capture.frame_count,
            authority_receipt_sha256=receipt_sha256(event_payload),
            receipt_registry=registry,
        )
        event.verify()
        return AuditoryReceptorEventResult(
            state=AuditoryReceptorEventState.OBSERVED,
            event=event,
            reason=(
                "complete paired pressure-energy, cumulative winding, "
                "and full D/M/R/U/C/P/B receptor event observed"
            ),
            verified_capability=AuditoryVerifiedReceptorEventCapability(
                event=event,
                _construction_authority=(
                    _VERIFIED_RECEPTOR_EVENT_AUTHORITY
                ),
            ),
        )
    except (
        IndexError,
        KeyError,
        ReceiptError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        return _unresolved(str(exc))


def settle_w1_ear_receptor_event(
    *,
    capture: AuditoryFullFieldCapture,
    mounted_component_inputs: tuple[
        NativeSensorySubstreamInput, ...
    ],
    ear_id: str,
    source_time_start: Fraction,
    pressure_components: tuple[ExactSubstreamInterpretation, ...],
    phase_components: tuple[ExactSubstreamInterpretation, ...],
    w1_l5_authority_receipt_sha256: str,
    w1_l5_experience_id: str,
) -> AuditoryReceptorEventResult:
    """Publish one W1 ear event from retained transduction custody."""

    try:
        capture.__post_init__()
        if (
            ear_id not in {"left", "right"}
            or len(pressure_components) != COCHLEAR_CHANNEL_COUNT
            or len(phase_components) != COCHLEAR_CHANNEL_COUNT
        ):
            raise ReceiptError("W1 ear receptor topology changed")
        if (
            not isinstance(mounted_component_inputs, tuple)
            or len(mounted_component_inputs)
            != 2 * COCHLEAR_CHANNEL_COUNT
            or any(
                not isinstance(value, NativeSensorySubstreamInput)
                for value in mounted_component_inputs
            )
        ):
            raise ReceiptError(
                "W1 ear retained component custody changed"
            )
        mounted_pressure = mounted_component_inputs[0::2]
        mounted_phase = mounted_component_inputs[1::2]
        channels = []
        channel_payloads = []
        prior_phases = [None] * COCHLEAR_CHANNEL_COUNT
        if (
            capture.rephase_seed is not None
            and not capture.rephase_seed.is_genesis
        ):
            prior_phases = [
                _binary64(value, "W1 ear prior phase")
                for value in capture.rephase_seed.phase_turns
            ]
        for index in range(COCHLEAR_CHANNEL_COUNT):
            pressure = pressure_components[index]
            phase = phase_components[index]
            pressure_native = mounted_pressure[index]
            phase_native = mounted_phase[index]
            for component, native in (
                (pressure, pressure_native),
                (phase, phase_native),
            ):
                samples = tuple(
                    (
                        source_index,
                        native.source_times[source_index],
                        Fraction.from_float(
                            native.normalized_signal[source_index]
                        ),
                        (
                            native.source_relevance[source_index]
                            if native.source_relevance is not None
                            else Fraction(1)
                        ),
                        native.phase_turns[source_index],
                    )
                    for source_index in range(
                        len(native.normalized_signal)
                    )
                )
                if not component.matches_source_claim(
                    source_evidence_stream_receipt_sha256=(
                        component.source_evidence_stream_receipt_sha256
                    ),
                    samples=samples,
                ):
                    raise ReceiptError(
                        "W1 ear raw pressure differs from mounted field"
                    )

            def fields_and_support(component):
                support = [-1] * component.source_sample_count
                fields = []
                for field_tuple in component.field_tuples:
                    fields.append(AuditoryReceptorFieldTuple(
                        tuple_index=field_tuple.tuple_index,
                        fields=field_tuple.fields,
                        source_l0_l4_trace_receipt_sha256=(
                            field_tuple
                            .source_l0_l4_trace_receipt_sha256
                        ),
                        authority_receipt_sha256=(
                            field_tuple.authority_receipt_sha256
                        ),
                    ))
                    for source_index in range(
                        field_tuple.source_index_start,
                        field_tuple.source_index_end + 1,
                    ):
                        if support[source_index] != -1:
                            raise ReceiptError(
                                "W1 ear field supports overlap"
                            )
                        support[source_index] = field_tuple.tuple_index
                if any(value < 0 for value in support):
                    raise ReceiptError(
                        "W1 ear field support is incomplete"
                    )
                return tuple(fields), tuple(support)

            pressure_fields, pressure_support = fields_and_support(
                pressure
            )
            phase_fields, phase_support = fields_and_support(phase)
            frames = []
            prior_phase = prior_phases[index]
            capture_channel = capture.channels[index]
            for source_index in range(capture.frame_count):
                pressure_value = _binary64(
                    capture_channel.pressure_envelope_full_scale[
                        source_index
                    ],
                    "W1 ear pressure",
                )
                cumulative_phase = _binary64(
                    capture_channel.carrier_phase_turns[source_index],
                    "W1 ear cumulative phase",
                )
                frames.append(AuditoryReceptorFrame(
                    source_index=source_index,
                    source_time=pressure_native.source_times[
                        source_index
                    ],
                    causal_offset=(
                        pressure_native.source_times[source_index]
                        - source_time_start
                    ),
                    pressure_amplitude=pressure_value,
                    relevance=pressure_value ** 2,
                    cumulative_phase_turns=cumulative_phase,
                    phase_advance_turns=_binary64(
                        capture_channel.carrier_phase_advance_turns[
                            source_index
                        ],
                        "W1 ear phase advance",
                    ),
                    winding_state=(
                        AuditoryWindingState.PRIOR_PHASE_UNRESOLVED
                        if prior_phase is None
                        else AuditoryWindingState.SETTLED
                    ),
                    winding_delta=(
                        None
                        if prior_phase is None
                        else math.floor(cumulative_phase)
                        - math.floor(prior_phase)
                    ),
                    pressure_field_tuple_index=(
                        pressure_support[source_index]
                    ),
                    phase_field_tuple_index=phase_support[source_index],
                ))
                prior_phase = cumulative_phase
            provisional = AuditoryReceptorChannelEvent(
                cochlear_index=index,
                channel_id=AUDITORY_CHANNELS[index].name,
                pressure_trace_receipt_sha256=(
                    pressure.field_tuples[0]
                    .source_l0_l4_trace_receipt_sha256
                ),
                phase_trace_receipt_sha256=(
                    phase.field_tuples[0]
                    .source_l0_l4_trace_receipt_sha256
                ),
                pressure_fields=pressure_fields,
                phase_fields=phase_fields,
                frames=tuple(frames),
                prior_cumulative_phase_turns=prior_phases[index],
                authority_receipt_sha256="0" * 64,
            )
            payload = provisional.payload()
            channel = AuditoryReceptorChannelEvent(
                cochlear_index=provisional.cochlear_index,
                channel_id=provisional.channel_id,
                pressure_trace_receipt_sha256=(
                    provisional.pressure_trace_receipt_sha256
                ),
                phase_trace_receipt_sha256=(
                    provisional.phase_trace_receipt_sha256
                ),
                pressure_fields=provisional.pressure_fields,
                phase_fields=provisional.phase_fields,
                frames=provisional.frames,
                prior_cumulative_phase_turns=(
                    provisional.prior_cumulative_phase_turns
                ),
                authority_receipt_sha256=receipt_sha256(payload),
            )
            channels.append(channel)
            channel_payloads.append(payload)
        capture_payload = _capture_payload(capture)
        capture_receipt = receipt_sha256(capture_payload)
        event_payload = _event_payload(
            capture_receipt_sha256=capture_receipt,
            auditory_l5_authority_receipt_sha256=(
                w1_l5_authority_receipt_sha256
            ),
            auditory_l5_experience_id=w1_l5_experience_id,
            channel_receipt_sha256s=tuple(
                value.authority_receipt_sha256 for value in channels
            ),
            frame_count=capture.frame_count,
        )
        registry = ReceiptRegistry.from_payloads(
            profile_payload=AUDITORY_RECEPTOR_EVENT_PROFILE,
            receipt_payloads=(
                capture_payload,
                *channel_payloads,
                event_payload,
            ),
        )
        event = AuditoryReceptorFullFieldEvent(
            capture_receipt_sha256=capture_receipt,
            auditory_l5_authority_receipt_sha256=(
                w1_l5_authority_receipt_sha256
            ),
            auditory_l5_experience_id=w1_l5_experience_id,
            channels=tuple(channels),
            frame_count=capture.frame_count,
            authority_receipt_sha256=receipt_sha256(event_payload),
            receipt_registry=registry,
        )
        event.verify()
        return AuditoryReceptorEventResult(
            state=AuditoryReceptorEventState.OBSERVED,
            event=event,
            reason="W1 ear raw pressure and mounted full field observed",
            verified_capability=AuditoryVerifiedReceptorEventCapability(
                event=event,
                _construction_authority=(
                    _VERIFIED_RECEPTOR_EVENT_AUTHORITY
                ),
            ),
        )
    except (
        IndexError,
        KeyError,
        ReceiptError,
        TypeError,
        ValueError,
    ) as exc:
        return _unresolved(str(exc))


__all__ = (
    "AUDITORY_RECEPTOR_CAPTURE_SCHEMA",
    "AUDITORY_RECEPTOR_CHANNEL_SCHEMA",
    "AUDITORY_RECEPTOR_EVENT_PROFILE",
    "AUDITORY_RECEPTOR_EVENT_SCHEMA",
    "AuditoryReceptorChannelEvent",
    "AuditoryReceptorEventResult",
    "AuditoryReceptorEventState",
    "AuditoryReceptorFieldTuple",
    "AuditoryReceptorFrame",
    "AuditoryReceptorFullFieldEvent",
    "AuditoryVerifiedReceptorEventCapability",
    "AuditoryWindingState",
    "auditory_pressure_energy_relevance",
    "settle_auditory_receptor_event",
    "settle_w1_ear_receptor_event",
)
