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
* the channel centre frequency and ERB bandwidth as explicit coordinates.

This is a sensory transduction, not a claim that the original waveform is
losslessly preserved.  Monaural spatial information and structure finer than
the sixteen-channel cochlear topology are not present.  No per-capture
normalization, strongest-bin selection, fitted threshold, learned parameter,
chi identity, scalar recognition score, or ML operation occurs here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

try:
    from guala_core import auditory_gammatone_field as _native_gammatone_field
except ImportError:
    _native_gammatone_field = None


REQUIRED_SAMPLE_RATE_HZ = 16_000
COCHLEAR_CHANNEL_COUNT = 16
COCHLEAR_ORDER = 4
OBSERVATION_HOP_SAMPLES = 160
MAX_CAPTURE_SECONDS = 8
LOWEST_CENTRE_FREQUENCY_HZ = 80.0
HIGHEST_CENTRE_FREQUENCY_HZ = 7_500.0


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

    def __post_init__(self) -> None:
        cardinality = len(self.causal_offsets_ns)
        if cardinality == 0:
            raise ValueError("auditory channel field cannot be empty")
        if not (
            cardinality
            == len(self.pressure_envelope_full_scale)
            == len(self.carrier_phase_turns)
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


@dataclass(frozen=True, slots=True)
class AuditoryFullFieldCapture:
    source_sample_rate_hz: int
    input_sample_count: int
    observation_hop_samples: int
    channels: tuple[AuditoryChannelField, ...]

    def __post_init__(self) -> None:
        if self.source_sample_rate_hz != REQUIRED_SAMPLE_RATE_HZ:
            raise ValueError("auditory field requires 16 kHz physical samples")
        if self.input_sample_count < self.observation_hop_samples:
            raise ValueError("auditory capture is shorter than one observation interval")
        if self.observation_hop_samples != OBSERVATION_HOP_SAMPLES:
            raise ValueError("auditory causal grid changed")
        if tuple(item.definition for item in self.channels) != AUDITORY_CHANNELS:
            raise ValueError("auditory topology changed")
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


def _cochlear_state_python(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Reference recurrence; authoritative fallback and differential oracle."""
    pole, injection = _cochlear_coefficients()
    state = np.zeros(
        (COCHLEAR_ORDER, COCHLEAR_CHANNEL_COUNT), dtype=np.complex128
    )
    previous = np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.complex128)
    phase_turns = np.zeros(COCHLEAR_CHANNEL_COUNT, dtype=np.float64)
    observation_count = len(values) // OBSERVATION_HOP_SAMPLES
    envelopes = np.empty(
        (observation_count, COCHLEAR_CHANNEL_COUNT), dtype=np.float64
    )
    phases = np.empty_like(envelopes)
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
            phase_turns[active] += np.angle(
                output[active] * np.conjugate(previous[active])
            ) / (2.0 * math.pi)
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
            observation_index += 1
            block_energy.fill(0.0)

    return envelopes, phases


def _cochlear_state_native(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Run the operation-ordered recurrence in the GIL-released Rust core."""
    if _native_gammatone_field is None:
        raise RuntimeError("native auditory gammatone kernel is unavailable")
    pole, injection = _cochlear_coefficients()
    envelopes_raw, phases_raw = _native_gammatone_field(
        values.tolist(),
        pole.real.tolist(),
        pole.imag.tolist(),
        injection.tolist(),
    )
    envelopes = np.asarray(envelopes_raw, dtype=np.float64)
    phases = np.asarray(phases_raw, dtype=np.float64)
    expected_shape = (
        len(values) // OBSERVATION_HOP_SAMPLES,
        COCHLEAR_CHANNEL_COUNT,
    )
    if envelopes.shape != expected_shape or phases.shape != expected_shape:
        raise RuntimeError("native auditory gammatone kernel changed field shape")
    return envelopes, phases


def _cochlear_state(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Advance the field natively when present, otherwise use the exact oracle."""
    if _native_gammatone_field is None:
        return _cochlear_state_python(values)
    return _cochlear_state_native(values)


def transduce_auditory_full_field(
    signal: np.ndarray,
    *,
    sample_rate_hz: int,
) -> AuditoryFullFieldCapture:
    """Map native PCM pressure into one bounded causal cochlear field."""
    values = _validated_samples(signal, sample_rate_hz)
    envelopes, phases = _cochlear_state(values)
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
    "AUDITORY_CHANNELS",
    "AuditoryChannelDefinition",
    "AuditoryChannelField",
    "AuditoryFullFieldCapture",
    "COCHLEAR_CHANNEL_COUNT",
    "COCHLEAR_ORDER",
    "HIGHEST_CENTRE_FREQUENCY_HZ",
    "LOWEST_CENTRE_FREQUENCY_HZ",
    "MAX_CAPTURE_SECONDS",
    "OBSERVATION_HOP_SAMPLES",
    "REQUIRED_SAMPLE_RATE_HZ",
    "transduce_auditory_full_field",
)
