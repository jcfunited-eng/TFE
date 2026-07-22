"""Causal cochlear mounting for Guala's native auditory field.

This provider does not recognize a word, a speaker, or meaning.  It mounts one
mono pressure waveform as sixteen independently evolving cochlear channels.
Each channel is a fourth-order complex gammatone resonator.  The pole spacing
follows the equivalent-rectangular-bandwidth (ERB) relation and every channel
is advanced at the native 16 kHz sample rate.  Its complete within-hop energy
is settled as a 10 ms RMS observation rather than sampled at one endpoint.

The mounted field retains, for every channel and observation time:

* the channel's calibrated 10 ms pressure-envelope RMS;
* the continuously accumulated carrier phase (advanced at 16 kHz, so phase
  winding is not aliased by the 10 ms observation grid);
* the carrier-phase advance across each completed observation hop and that
  advance divided by the hop's analytic Nyquist limit;
* the channel centre frequency and ERB bandwidth as explicit coordinates.

This is a sensory transduction, not a claim that the original waveform is
losslessly preserved.  Monaural spatial information and structure finer than
the sixteen-channel cochlear topology are not present.  No per-capture
normalization, strongest-bin selection, fitted threshold, learned parameter,
chi identity, scalar recognition score, or ML operation occurs here.
"""

from __future__ import annotations

import math
import hashlib
import json
import struct
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np

try:
    from guala_core import auditory_gammatone_field as _native_gammatone_field
except ImportError:
    _native_gammatone_field = None

try:
    from guala_core import auditory_gammatone_stream as _native_gammatone_stream
except ImportError:
    _native_gammatone_stream = None

from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMContinuityReceipt,
    PCM_STREAM_CAPACITY,
    PCM_STREAM_IDLE_SECONDS,
)


REQUIRED_SAMPLE_RATE_HZ = 16_000
COCHLEAR_CHANNEL_COUNT = 16
COCHLEAR_ORDER = 4
OBSERVATION_HOP_SAMPLES = 160
PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP = OBSERVATION_HOP_SAMPLES / 2.0
MAX_CAPTURE_SECONDS = 8
LOWEST_CENTRE_FREQUENCY_HZ = 80.0
HIGHEST_CENTRE_FREQUENCY_HZ = 7_500.0
AUDITORY_GAMMATONE_CONTINUATION_SCHEMA = (
    "guala.auditory_gammatone_continuation.v3"
)
AUDITORY_FULL_FIELD_PROVIDER_SCHEMA = "guala.auditory_full_field_provider.v3"


def _erb_width_hz(frequency_hz: float) -> float:
    """Glasberg--Moore equivalent rectangular bandwidth in hertz."""
    return 24.7 * (1.0 + 4.37e-3 * frequency_hz)


def _erb_rate(frequency_hz: float) -> float:
    return 21.4 * math.log10(1.0 + 4.37e-3 * frequency_hz)


def _frequency_from_erb_rate(rate: float) -> float:
    return (10.0 ** (rate / 21.4) - 1.0) / 4.37e-3


@dataclass(frozen=True, slots=True)
class AuditoryChannelDefinition:
    name: str
    centre_hz: float
    erb_width_hz: float


def _channel_definitions() -> tuple[AuditoryChannelDefinition, ...]:
    lower = _erb_rate(LOWEST_CENTRE_FREQUENCY_HZ)
    upper = _erb_rate(HIGHEST_CENTRE_FREQUENCY_HZ)
    rates = np.linspace(lower, upper, COCHLEAR_CHANNEL_COUNT)
    return tuple(
        AuditoryChannelDefinition(
            name=f"erb_{index:02d}",
            centre_hz=float(_frequency_from_erb_rate(float(rate))),
            erb_width_hz=float(_erb_width_hz(
                _frequency_from_erb_rate(float(rate)))),
        )
        for index, rate in enumerate(rates)
    )


AUDITORY_CHANNELS = _channel_definitions()


@dataclass(frozen=True, slots=True)
class AuditoryChannelField:
    definition: AuditoryChannelDefinition
    causal_offsets_ns: tuple[int, ...]
    pressure_envelope_full_scale: tuple[float, ...]
    carrier_phase_turns: tuple[float, ...]
    carrier_phase_advance_turns: tuple[float, ...]
    carrier_phase_advance_nyquist_fraction: tuple[float, ...]

    def __post_init__(self) -> None:
        cardinality = len(self.causal_offsets_ns)
        if cardinality == 0:
            raise ValueError("auditory channel field cannot be empty")
        if not (
            cardinality
            == len(self.pressure_envelope_full_scale)
            == len(self.carrier_phase_turns)
            == len(self.carrier_phase_advance_turns)
            == len(self.carrier_phase_advance_nyquist_fraction)
        ):
            raise ValueError("auditory channel field lost synchronized samples")
        if self.causal_offsets_ns[0] < 0 or any(
            right <= left
            for left, right in zip(
                self.causal_offsets_ns, self.causal_offsets_ns[1:]
            )
        ):
            raise ValueError("auditory field time grid is not causal")
        for value in self.pressure_envelope_full_scale:
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("auditory pressure left full-scale calibration")
        for value in self.carrier_phase_turns:
            if not math.isfinite(value):
                raise ValueError("auditory carrier phase is not finite")
        for value in self.carrier_phase_advance_turns:
            if (
                not math.isfinite(value)
                or not -PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
                <= value
                <= PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
            ):
                raise ValueError("auditory carrier phase advance exceeded Nyquist")
        for value in self.carrier_phase_advance_nyquist_fraction:
            if not math.isfinite(value) or not -1.0 <= value <= 1.0:
                raise ValueError(
                    "auditory normalized carrier phase advance exceeded Nyquist"
                )
        expected_normalized = tuple(
            value / PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
            for value in self.carrier_phase_advance_turns
        )
        if self.carrier_phase_advance_nyquist_fraction != expected_normalized:
            raise ValueError("auditory carrier phase normalization changed")


@dataclass(frozen=True, slots=True)
class AuditoryFullFieldCapture:
    source_sample_rate_hz: int
    input_sample_count: int
    observation_hop_samples: int
    channels: tuple[AuditoryChannelField, ...]
    source_first_sample_index: int = 0
    continuation_receipt_sha256: str | None = None
    provider_schema: str = AUDITORY_FULL_FIELD_PROVIDER_SCHEMA

    def __post_init__(self) -> None:
        if self.source_sample_rate_hz != REQUIRED_SAMPLE_RATE_HZ:
            raise ValueError("auditory field requires 16 kHz physical samples")
        if self.provider_schema != AUDITORY_FULL_FIELD_PROVIDER_SCHEMA:
            raise ValueError("auditory full-field provider schema changed")
        if self.input_sample_count < self.observation_hop_samples:
            raise ValueError("auditory capture is shorter than one observation interval")
        if self.observation_hop_samples != OBSERVATION_HOP_SAMPLES:
            raise ValueError("auditory causal grid changed")
        if tuple(item.definition for item in self.channels) != AUDITORY_CHANNELS:
            raise ValueError("auditory topology changed")
        if self.source_first_sample_index < 0:
            raise ValueError("auditory source sample index is invalid")
        if (
            self.continuation_receipt_sha256 is not None
            and (
                not isinstance(self.continuation_receipt_sha256, str)
                or len(self.continuation_receipt_sha256) != 64
                or any(value not in "0123456789abcdef"
                       for value in self.continuation_receipt_sha256)
            )
        ):
            raise ValueError("auditory continuation receipt digest is invalid")
        reference_offsets = self.channels[0].causal_offsets_ns
        if any(
            item.causal_offsets_ns != reference_offsets
            for item in self.channels
        ):
            raise ValueError("auditory channels are not synchronized")

    @property
    def frame_count(self) -> int:
        return len(self.channels[0].causal_offsets_ns)

    @property
    def bands(self) -> tuple[AuditoryChannelField, ...]:
        """Compatibility name for the engine's neutral channel iterator."""
        return self.channels


@dataclass(frozen=True, slots=True)
class AuditoryGammatoneContinuationReceipt:
    stream_id: str
    sequence: int
    first_sample_index: int
    sample_count: int
    prior_state_receipt_sha256: str | None
    transport_receipt_sha256: str
    state_sha256: str
    receipt_sha256: str

    def payload(self) -> dict:
        return {
            "first_sample_index": self.first_sample_index,
            "prior_state_receipt_sha256": self.prior_state_receipt_sha256,
            "sample_count": self.sample_count,
            "schema": AUDITORY_GAMMATONE_CONTINUATION_SCHEMA,
            "sequence": self.sequence,
            "state_sha256": self.state_sha256,
            "stream_id": self.stream_id,
            "transport_receipt_sha256": self.transport_receipt_sha256,
        }

    def verify(self) -> None:
        encoded = json.dumps(
            self.payload(), allow_nan=False, ensure_ascii=False,
            separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")
        if hashlib.sha256(encoded).hexdigest() != self.receipt_sha256:
            raise ValueError("auditory gammatone continuation receipt was altered")


def _validated_samples(signal: np.ndarray, sample_rate_hz: int) -> np.ndarray:
    if isinstance(sample_rate_hz, bool) or sample_rate_hz != REQUIRED_SAMPLE_RATE_HZ:
        raise ValueError("production auditory input must be 16 kHz")
    values = np.asarray(signal, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("production auditory input must be mono")
    if len(values) < OBSERVATION_HOP_SAMPLES:
        raise ValueError("auditory capture is shorter than 10 ms")
    if len(values) > REQUIRED_SAMPLE_RATE_HZ * MAX_CAPTURE_SECONDS:
        raise ValueError("auditory capture exceeds the eight-second boundary")
    if not np.all(np.isfinite(values)):
        raise ValueError("auditory input contains non-finite pressure")
    if np.any(values < -1.0) or np.any(values > 1.0):
        raise ValueError("auditory input exceeds normalized full scale")
    return values


def _cochlear_coefficients() -> tuple[np.ndarray, np.ndarray]:
    """Return the production poles and injections for all physical channels."""
    centres = np.asarray(
        [channel.centre_hz for channel in AUDITORY_CHANNELS],
        dtype=np.float64,
    )
    widths = np.asarray(
        [channel.erb_width_hz for channel in AUDITORY_CHANNELS],
        dtype=np.float64,
    )
    # A fourth-order gammatone is a cascade of four identical complex poles.
    # The 1.019 multiplier is the standard fourth-order ERB correction.
    radius = np.exp(
        -2.0 * math.pi * 1.019 * widths / REQUIRED_SAMPLE_RATE_HZ
    )
    pole = radius * np.exp(
        2.0j * math.pi * centres / REQUIRED_SAMPLE_RATE_HZ
    )
    injection = 1.0 - radius
    return pole, injection


def _cochlear_state_python(
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reference recurrence; authoritative fallback and differential oracle."""
    pole, injection = _cochlear_coefficients()
    state = np.zeros(
        (COCHLEAR_ORDER, COCHLEAR_CHANNEL_COUNT), dtype=np.complex128
    )
    previous = np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.complex128)
    phase_turns = np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.float64)
    hop_phase_turns = np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.float64)
    observation_count = len(values) // OBSERVATION_HOP_SAMPLES
    envelopes = np.empty(
        (observation_count, COCHLEAR_CHANNEL_COUNT), dtype=np.float64
    )
    phases = np.empty_like(envelopes)
    phase_advances = np.empty_like(envelopes)
    observation_index = 0
    block_energy = np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.float64)

    for source_index, sample in enumerate(values):
        stage_input = np.full(
            COCHLEAR_CHANNEL_COUNT, float(sample), dtype=np.complex128
        )
        for order_index in range(COCHLEAR_ORDER):
            state[order_index] = (
                pole * state[order_index] + injection * stage_input
            )
            stage_input = state[order_index]
        output = state[-1]
        active = (np.abs(output) > 0.0) & (np.abs(previous) > 0.0)
        if np.any(active):
            phase_delta = np.angle(
                output[active] * np.conjugate(previous[active])
            ) / (2.0 * math.pi)
            phase_turns[active] += phase_delta
            hop_phase_turns[active] += phase_delta
        first_active = (np.abs(output) > 0.0) & (np.abs(previous) == 0.0)
        if np.any(first_active):
            phase_turns[first_active] = (
                np.angle(output[first_active]) / (2.0 * math.pi)
            )
        previous = output.copy()
        block_energy += np.abs(output) ** 2

        if (source_index + 1) % OBSERVATION_HOP_SAMPLES == 0:
            magnitude = np.sqrt(block_energy / OBSERVATION_HOP_SAMPLES)
            # Each first-order section has impulse-response L1 norm one;
            # their cascade therefore cannot exceed a unit-bounded input.
            if np.any(magnitude > 1.0 + 1e-12):
                raise RuntimeError("cochlear pressure exceeded its analytic bound")
            envelopes[observation_index] = np.minimum(magnitude, 1.0)
            phases[observation_index] = phase_turns
            phase_advances[observation_index] = hop_phase_turns
            observation_index += 1
            block_energy.fill(0.0)
            hop_phase_turns.fill(0.0)

    return envelopes, phases, phase_advances


def _cochlear_state_native(
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run the operation-ordered recurrence in the GIL-released Rust core."""
    if _native_gammatone_field is None:
        raise RuntimeError("native auditory gammatone kernel is unavailable")
    pole, injection = _cochlear_coefficients()
    envelopes_raw, phases_raw, phase_advances_raw = _native_gammatone_field(
        values.tolist(),
        pole.real.tolist(),
        pole.imag.tolist(),
        injection.tolist(),
    )
    envelopes = np.asarray(envelopes_raw, dtype=np.float64)
    phases = np.asarray(phases_raw, dtype=np.float64)
    phase_advances = np.asarray(phase_advances_raw, dtype=np.float64)
    expected_shape = (
        len(values) // OBSERVATION_HOP_SAMPLES,
        COCHLEAR_CHANNEL_COUNT,
    )
    if (
        envelopes.shape != expected_shape
        or phases.shape != expected_shape
        or phase_advances.shape != expected_shape
    ):
        raise RuntimeError("native auditory gammatone kernel changed field shape")
    return envelopes, phases, phase_advances


def _cochlear_state(
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Advance the field natively when present, otherwise use the exact oracle."""
    if _native_gammatone_field is None:
        return _cochlear_state_python(values)
    return _cochlear_state_native(values)


def _phase_advance_components(
    phase_advances: np.ndarray,
    *,
    completed_observation_count: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Settle phase motion accumulated directly inside each physical hop."""
    advances = np.asarray(phase_advances, dtype=np.float64).copy()
    expected_shape = (len(advances), COCHLEAR_CHANNEL_COUNT)
    if advances.shape != expected_shape:
        raise RuntimeError("auditory carrier phase advance changed field shape")
    if (
        isinstance(completed_observation_count, bool)
        or not isinstance(completed_observation_count, int)
        or completed_observation_count < 0
    ):
        raise RuntimeError("auditory completed observation count is invalid")

    if len(advances) and completed_observation_count == 0:
        # The first completed observation establishes phase origin. There is
        # no earlier completed observation, so genesis is exactly zero once.
        advances[0].fill(0.0)

    normalized = advances / PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
    if (
        not np.all(np.isfinite(advances))
        or np.any(
            np.abs(advances) > PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
        )
        or np.any(np.abs(normalized) > 1.0)
    ):
        raise RuntimeError("auditory carrier phase advance exceeded Nyquist")
    return (
        advances,
        normalized,
        completed_observation_count + len(advances),
    )


def _zero_continuation_state() -> tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, int, int,
]:
    state_shape = (COCHLEAR_ORDER, COCHLEAR_CHANNEL_COUNT)
    return (
        np.zeros(state_shape, dtype=np.float64),
        np.zeros(state_shape, dtype=np.float64),
        np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.float64),
        np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.float64),
        np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.float64),
        np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.float64),
        np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.float64),
        0,
        0,
    )


def _cochlear_stream_python(
    values: np.ndarray,
    state_real: np.ndarray,
    state_imag: np.ndarray,
    previous_real: np.ndarray,
    previous_imag: np.ndarray,
    phase_turns: np.ndarray,
    block_energy: np.ndarray,
    partial_hop_phase_turns: np.ndarray,
    partial_hop_samples: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray,
           np.ndarray, np.ndarray, np.ndarray, np.ndarray,
           np.ndarray, np.ndarray, int]:
    pole, injection = _cochlear_coefficients()
    state = state_real.astype(np.complex128) + 1j * state_imag
    previous = previous_real.astype(np.complex128) + 1j * previous_imag
    phases_state = phase_turns.copy()
    energy_state = block_energy.copy()
    hop_phase_state = partial_hop_phase_turns.copy()
    envelopes = []
    phases = []
    phase_advances = []
    partial = int(partial_hop_samples)
    for sample in values:
        stage_input = np.full(
            COCHLEAR_CHANNEL_COUNT, float(sample), dtype=np.complex128
        )
        for order_index in range(COCHLEAR_ORDER):
            state[order_index] = (
                pole * state[order_index] + injection * stage_input
            )
            stage_input = state[order_index]
        output = state[-1]
        active = (np.abs(output) > 0.0) & (np.abs(previous) > 0.0)
        if np.any(active):
            phase_delta = np.angle(
                output[active] * np.conjugate(previous[active])
            ) / (2.0 * math.pi)
            phases_state[active] += phase_delta
            hop_phase_state[active] += phase_delta
        first_active = (np.abs(output) > 0.0) & (np.abs(previous) == 0.0)
        if np.any(first_active):
            phases_state[first_active] = (
                np.angle(output[first_active]) / (2.0 * math.pi)
            )
        previous = output.copy()
        energy_state += np.abs(output) ** 2
        partial += 1
        if partial == OBSERVATION_HOP_SAMPLES:
            magnitude = np.sqrt(energy_state / OBSERVATION_HOP_SAMPLES)
            if np.any(magnitude > 1.0 + 1e-12):
                raise RuntimeError("cochlear pressure exceeded its analytic bound")
            envelopes.append(np.minimum(magnitude, 1.0))
            phases.append(phases_state.copy())
            phase_advances.append(hop_phase_state.copy())
            energy_state.fill(0.0)
            hop_phase_state.fill(0.0)
            partial = 0
    shape = (0, COCHLEAR_CHANNEL_COUNT)
    return (
        np.asarray(envelopes, dtype=np.float64).reshape(
            (-1, COCHLEAR_CHANNEL_COUNT)) if envelopes
        else np.empty(shape, dtype=np.float64),
        np.asarray(phases, dtype=np.float64).reshape(
            (-1, COCHLEAR_CHANNEL_COUNT)) if phases
        else np.empty(shape, dtype=np.float64),
        np.asarray(phase_advances, dtype=np.float64).reshape(
            (-1, COCHLEAR_CHANNEL_COUNT)) if phase_advances
        else np.empty(shape, dtype=np.float64),
        state.real.copy(),
        state.imag.copy(),
        previous.real.copy(),
        previous.imag.copy(),
        phases_state,
        energy_state,
        hop_phase_state,
        partial,
    )


def _cochlear_stream_native(
    values: np.ndarray,
    state_real: np.ndarray,
    state_imag: np.ndarray,
    previous_real: np.ndarray,
    previous_imag: np.ndarray,
    phase_turns: np.ndarray,
    block_energy: np.ndarray,
    partial_hop_phase_turns: np.ndarray,
    partial_hop_samples: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray,
           np.ndarray, np.ndarray, np.ndarray, np.ndarray,
           np.ndarray, np.ndarray, int]:
    if _native_gammatone_stream is None:
        raise RuntimeError("native auditory gammatone stream kernel is unavailable")
    pole, injection = _cochlear_coefficients()
    result = _native_gammatone_stream(
        values.tolist(), pole.real.tolist(), pole.imag.tolist(),
        injection.tolist(), state_real.reshape(-1).tolist(),
        state_imag.reshape(-1).tolist(), previous_real.tolist(),
        previous_imag.tolist(), phase_turns.tolist(), block_energy.tolist(),
        partial_hop_phase_turns.tolist(),
        int(partial_hop_samples),
    )
    envelopes = np.asarray(result[0], dtype=np.float64).reshape(
        (-1, COCHLEAR_CHANNEL_COUNT))
    phases = np.asarray(result[1], dtype=np.float64).reshape(
        (-1, COCHLEAR_CHANNEL_COUNT))
    phase_advances = np.asarray(result[2], dtype=np.float64).reshape(
        (-1, COCHLEAR_CHANNEL_COUNT))
    return (
        envelopes,
        phases,
        phase_advances,
        np.asarray(result[3], dtype=np.float64).reshape(
            (COCHLEAR_ORDER, COCHLEAR_CHANNEL_COUNT)),
        np.asarray(result[4], dtype=np.float64).reshape(
            (COCHLEAR_ORDER, COCHLEAR_CHANNEL_COUNT)),
        np.asarray(result[5], dtype=np.float64),
        np.asarray(result[6], dtype=np.float64),
        np.asarray(result[7], dtype=np.float64),
        np.asarray(result[8], dtype=np.float64),
        np.asarray(result[9], dtype=np.float64),
        int(result[10]),
    )


def _state_sha256(state: tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, int, int,
]) -> str:
    encoded = bytearray()
    for values in state[:-2]:
        for value in np.asarray(values, dtype=np.float64).reshape(-1):
            encoded.extend(struct.pack("<d", float(value)))
    encoded.extend(struct.pack("<Q", int(state[-2])))
    encoded.extend(struct.pack("<Q", int(state[-1])))
    return hashlib.sha256(encoded).hexdigest()


class AuditoryFullFieldStream:
    """Transient owner of one exact, gap-free cochlear recurrence."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stream_id: str | None = None
        self._last_transport_receipt_sha256: str | None = None
        self._last_state_receipt_sha256: str | None = None
        self._expected_first_sample_index = 0
        self._state = _zero_continuation_state()

    def _reset(self, stream_id: str) -> None:
        self._stream_id = stream_id
        self._last_transport_receipt_sha256 = None
        self._last_state_receipt_sha256 = None
        self._expected_first_sample_index = 0
        self._state = _zero_continuation_state()

    def advance(
        self,
        pcm_s16le: bytes,
        continuity: AuditoryPCMContinuityReceipt,
    ) -> tuple[AuditoryFullFieldCapture, AuditoryGammatoneContinuationReceipt]:
        if not isinstance(continuity, AuditoryPCMContinuityReceipt):
            raise TypeError("auditory stream requires a typed PCM continuity receipt")
        continuity.verify()
        if not isinstance(pcm_s16le, bytes) or len(pcm_s16le) % 2:
            raise ValueError("auditory stream requires signed 16-bit mono PCM")
        if hashlib.sha256(pcm_s16le).hexdigest() != continuity.pcm_sha256:
            raise ValueError("auditory PCM differs from its continuity receipt")
        if len(pcm_s16le) // 2 != continuity.sample_count:
            raise ValueError("auditory PCM sample count differs from its receipt")
        values = (
            np.frombuffer(pcm_s16le, dtype="<i2").astype(np.float64)
            / 32768.0
        )
        _validated_samples(values, REQUIRED_SAMPLE_RATE_HZ)
        with self._lock:
            if continuity.sequence == 0:
                if (
                    continuity.first_sample_index != 0
                    or continuity.prior_receipt_sha256 is not None
                ):
                    raise ValueError("auditory PCM epoch does not begin at sample zero")
                self._reset(continuity.stream_id)
            elif (
                continuity.stream_id != self._stream_id
                or continuity.first_sample_index
                != self._expected_first_sample_index
                or continuity.prior_receipt_sha256
                != self._last_transport_receipt_sha256
            ):
                raise ValueError("auditory cochlear continuation is discontinuous")
            prior_partial = int(self._state[-1])
            operation = (
                _cochlear_stream_native
                if _native_gammatone_stream is not None
                else _cochlear_stream_python
            )
            result = operation(values, *self._state[:7], self._state[-1])
            envelopes, phases, direct_phase_advances = result[:3]
            (
                phase_advances,
                normalized_phase_advances,
                next_completed_observation_count,
            ) = _phase_advance_components(
                direct_phase_advances,
                completed_observation_count=self._state[7],
            )
            next_state = (
                *result[3:10],
                next_completed_observation_count,
                result[10],
            )
            state_digest = _state_sha256(next_state)
            receipt_payload = {
                "first_sample_index": continuity.first_sample_index,
                "prior_state_receipt_sha256": self._last_state_receipt_sha256,
                "sample_count": continuity.sample_count,
                "schema": AUDITORY_GAMMATONE_CONTINUATION_SCHEMA,
                "sequence": continuity.sequence,
                "state_sha256": state_digest,
                "stream_id": continuity.stream_id,
                "transport_receipt_sha256": continuity.receipt_sha256,
            }
            receipt_bytes = json.dumps(
                receipt_payload, allow_nan=False, ensure_ascii=False,
                separators=(",", ":"), sort_keys=True,
            ).encode("utf-8")
            state_receipt = AuditoryGammatoneContinuationReceipt(
                stream_id=continuity.stream_id,
                sequence=continuity.sequence,
                first_sample_index=continuity.first_sample_index,
                sample_count=continuity.sample_count,
                prior_state_receipt_sha256=self._last_state_receipt_sha256,
                transport_receipt_sha256=continuity.receipt_sha256,
                state_sha256=state_digest,
                receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
            )
            state_receipt.verify()
            if not len(envelopes):
                raise ValueError(
                    "auditory stream chunk is shorter than one completed observation"
                )
            first_completion = (
                continuity.first_sample_index
                + OBSERVATION_HOP_SAMPLES - prior_partial
            )
            offsets_ns = tuple(
                (first_completion + index * OBSERVATION_HOP_SAMPLES)
                * 1_000_000_000 // REQUIRED_SAMPLE_RATE_HZ
                for index in range(len(envelopes))
            )
            channels = tuple(
                AuditoryChannelField(
                    definition=definition,
                    causal_offsets_ns=offsets_ns,
                    pressure_envelope_full_scale=tuple(
                        float(value) for value in envelopes[:, index]
                    ),
                    carrier_phase_turns=tuple(
                        float(value) for value in phases[:, index]
                    ),
                    carrier_phase_advance_turns=tuple(
                        float(value) for value in phase_advances[:, index]
                    ),
                    carrier_phase_advance_nyquist_fraction=tuple(
                        float(value)
                        for value in normalized_phase_advances[:, index]
                    ),
                )
                for index, definition in enumerate(AUDITORY_CHANNELS)
            )
            capture = AuditoryFullFieldCapture(
                source_sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
                input_sample_count=len(values),
                observation_hop_samples=OBSERVATION_HOP_SAMPLES,
                channels=channels,
                source_first_sample_index=continuity.first_sample_index,
                continuation_receipt_sha256=state_receipt.receipt_sha256,
            )
            self._state = next_state
            self._stream_id = continuity.stream_id
            self._expected_first_sample_index = continuity.last_sample_index_exclusive
            self._last_transport_receipt_sha256 = continuity.receipt_sha256
            self._last_state_receipt_sha256 = state_receipt.receipt_sha256
            return capture, state_receipt


@dataclass(slots=True)
class _OwnedAuditoryFullFieldStream:
    owner: AuditoryFullFieldStream
    last_activity: float


class AuditoryFullFieldStreamRegistry:
    """Bounded per-epoch ownership for uninterrupted cochlear recurrence.

    Each browser stream advances one and only one filter state. Interleaving
    independently valid microphone epochs therefore cannot reset, borrow, or
    corrupt another epoch's physical history. The registry has the same
    capacity and idle lifetime as the PCM continuity authority; a process
    restart intentionally restores no active auditory stream.
    """

    def __init__(
        self,
        *,
        clock=time.monotonic,
        stream_capacity: int = PCM_STREAM_CAPACITY,
        idle_seconds: int = PCM_STREAM_IDLE_SECONDS,
    ) -> None:
        if stream_capacity <= 0 or idle_seconds <= 0:
            raise ValueError("auditory full-field registry bounds must be positive")
        self._clock = clock
        self._stream_capacity = int(stream_capacity)
        self._idle_seconds = int(idle_seconds)
        self._lock = threading.RLock()
        self._streams: OrderedDict[
            str, _OwnedAuditoryFullFieldStream
        ] = OrderedDict()

    def _expire_locked(self, now: float) -> None:
        for stream_id in tuple(self._streams):
            if now - self._streams[stream_id].last_activity > self._idle_seconds:
                del self._streams[stream_id]

    def advance(
        self,
        pcm_s16le: bytes,
        continuity: AuditoryPCMContinuityReceipt,
    ) -> tuple[AuditoryFullFieldCapture, AuditoryGammatoneContinuationReceipt]:
        if not isinstance(continuity, AuditoryPCMContinuityReceipt):
            raise TypeError("auditory stream requires a typed PCM continuity receipt")
        continuity.verify()
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            mounted = self._streams.get(continuity.stream_id)
            if continuity.sequence == 0:
                if mounted is not None:
                    raise ValueError("auditory full-field stream epoch already exists")
                if len(self._streams) >= self._stream_capacity:
                    raise RuntimeError("auditory full-field stream capacity is full")
                mounted = _OwnedAuditoryFullFieldStream(
                    owner=AuditoryFullFieldStream(),
                    last_activity=now,
                )
                self._streams[continuity.stream_id] = mounted
            elif mounted is None:
                raise ValueError("auditory full-field stream epoch is unknown or expired")
            try:
                capture, receipt = mounted.owner.advance(pcm_s16le, continuity)
            except Exception:
                self._streams.pop(continuity.stream_id, None)
                raise
            mounted.last_activity = now
            self._streams.move_to_end(continuity.stream_id)
            return capture, receipt

    def close(self, stream_id: str) -> bool:
        with self._lock:
            return self._streams.pop(stream_id, None) is not None

    def status(self) -> dict:
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            return {
                "active_streams": len(self._streams),
                "stream_capacity": self._stream_capacity,
            }


def transduce_auditory_full_field(
    signal: np.ndarray,
    *,
    sample_rate_hz: int,
) -> AuditoryFullFieldCapture:
    """Map native PCM pressure into one bounded causal cochlear field."""
    values = _validated_samples(signal, sample_rate_hz)
    envelopes, phases, direct_phase_advances = _cochlear_state(values)
    phase_advances, normalized_phase_advances, _ = (
        _phase_advance_components(
            direct_phase_advances,
            completed_observation_count=0,
        )
    )
    offsets_ns = tuple(
        (index + 1)
        * OBSERVATION_HOP_SAMPLES
        * 1_000_000_000
        // REQUIRED_SAMPLE_RATE_HZ
        for index in range(len(envelopes))
    )
    channels = tuple(
        AuditoryChannelField(
            definition=definition,
            causal_offsets_ns=offsets_ns,
            pressure_envelope_full_scale=tuple(
                float(value) for value in envelopes[:, index]
            ),
            carrier_phase_turns=tuple(
                float(value) for value in phases[:, index]
            ),
            carrier_phase_advance_turns=tuple(
                float(value) for value in phase_advances[:, index]
            ),
            carrier_phase_advance_nyquist_fraction=tuple(
                float(value)
                for value in normalized_phase_advances[:, index]
            ),
        )
        for index, definition in enumerate(AUDITORY_CHANNELS)
    )
    return AuditoryFullFieldCapture(
        source_sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
        input_sample_count=len(values),
        observation_hop_samples=OBSERVATION_HOP_SAMPLES,
        channels=channels,
    )


__all__ = (
    "AUDITORY_FULL_FIELD_PROVIDER_SCHEMA",
    "AUDITORY_GAMMATONE_CONTINUATION_SCHEMA",
    "AUDITORY_CHANNELS",
    "AuditoryChannelDefinition",
    "AuditoryChannelField",
    "AuditoryFullFieldCapture",
    "AuditoryFullFieldStream",
    "AuditoryFullFieldStreamRegistry",
    "AuditoryGammatoneContinuationReceipt",
    "COCHLEAR_CHANNEL_COUNT",
    "COCHLEAR_ORDER",
    "HIGHEST_CENTRE_FREQUENCY_HZ",
    "LOWEST_CENTRE_FREQUENCY_HZ",
    "MAX_CAPTURE_SECONDS",
    "OBSERVATION_HOP_SAMPLES",
    "PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP",
    "REQUIRED_SAMPLE_RATE_HZ",
    "transduce_auditory_full_field",
)
