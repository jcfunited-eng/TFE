"""Public exact W1 binaural geometry, propagation, and cochlear mounting.

External emitters and the self-vocal motor share these physical laws.  This
module owns the one authoritative implementation so neither hearing path can
silently diverge in ear geometry, integer propagation delay, rational
inverse-square attenuation, PCM transport, or full-field cochlear topology.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedBody,
    ObservationSnapshot,
    PositionMM,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AuditoryFullFieldCapture,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    MAX_EMITTED_PCM_SAMPLES,
    MIN_EMITTED_PCM_SAMPLES,
    PCM_SAMPLE_RATE_HZ,
)


PCM_SAMPLE_WIDTH_BYTES = 2
SPEED_OF_SOUND_MM_PER_SECOND = 343_000
CARDINAL_HEADINGS_MILLIDEGREES = (
    0,
    90_000,
    180_000,
    270_000,
)


@dataclass(frozen=True, slots=True)
class _VerifiedW1EarAuditoryTransduction:
    ear_id: str
    topology_index: int
    source_time_start: Fraction
    source_pcm_sha256: str
    capture: AuditoryFullFieldCapture
    component_inputs: tuple[NativeSensorySubstreamInput, ...]
    native_inputs: tuple[NativeSensorySubstreamInput, ...]


@dataclass(frozen=True, slots=True)
class W1EarAuditoryTransductionCustody(
    Sequence[NativeSensorySubstreamInput],
):
    """One physical transduction and its exact one-time cochlear mount."""

    ear_id: str
    topology_index: int
    source_time_start: Fraction
    source_pcm_sha256: str
    capture: AuditoryFullFieldCapture
    component_inputs: tuple[NativeSensorySubstreamInput, ...]
    native_inputs: tuple[NativeSensorySubstreamInput, ...]
    transduction_count: int
    component_mount_count: int
    _construction_authority: (
        _VerifiedW1EarAuditoryTransduction | None
    ) = field(
        repr=False,
        compare=False,
    )

    def __len__(self) -> int:
        return len(self.native_inputs)

    def __iter__(self) -> Iterator[NativeSensorySubstreamInput]:
        return iter(self.native_inputs)

    def __getitem__(
        self,
        index: int | slice,
    ) -> NativeSensorySubstreamInput | tuple[
        NativeSensorySubstreamInput, ...
    ]:
        return self.native_inputs[index]

    def verify(self) -> None:
        self.capture.__post_init__()
        authority = self._construction_authority
        if (
            self.ear_id not in ("left", "right")
            or not isinstance(
                authority,
                _VerifiedW1EarAuditoryTransduction,
            )
            or authority.ear_id != self.ear_id
            or authority.topology_index != self.topology_index
            or authority.source_time_start != self.source_time_start
            or authority.source_pcm_sha256 != self.source_pcm_sha256
            or authority.capture is not self.capture
            or authority.component_inputs is not self.component_inputs
            or authority.native_inputs is not self.native_inputs
            or isinstance(self.topology_index, bool)
            or not isinstance(self.topology_index, int)
            or self.topology_index < 0
            or not isinstance(self.source_time_start, Fraction)
            or len(self.source_pcm_sha256) != 64
            or any(
                value not in "0123456789abcdef"
                for value in self.source_pcm_sha256
            )
            or self.transduction_count != 1
            or self.component_mount_count != 1
            or len(self.component_inputs)
            != AUDITORY_KERNEL_COMPONENT_COUNT
            or len(self.native_inputs)
            != AUDITORY_KERNEL_COMPONENT_COUNT
        ):
            raise ValueError("W1 auditory transduction custody changed")
        for component, native in zip(
            self.component_inputs,
            self.native_inputs,
            strict=True,
        ):
            expected_origin = (
                f"{self.ear_id}-"
                f"{component.source_relevance_origin_substream_id}"
                if component.source_relevance_origin_substream_id is not None
                else None
            )
            if (
                native.sense is not PhysicalSense.SOUND
                or native.sensor_id
                != f"W1-calibrated-{self.ear_id}-cochlear-field"
                or native.substream_id
                != f"{self.ear_id}-{component.substream_id}"
                or native.topology_index
                != self.topology_index + component.topology_index
                or native.coordinates
                != (
                    NativeAxisCoordinate(
                        "acoustic-receptor",
                        self.ear_id,
                    ),
                    *component.coordinates,
                )
                or native.physical_quantity
                != component.physical_quantity
                or native.physical_unit != component.physical_unit
                or native.source_times != component.source_times
                or native.normalized_signal
                != component.normalized_signal
                or native.phase_turns != component.phase_turns
                or native.source_relevance
                != component.source_relevance
                or native.source_relevance_rule
                != component.source_relevance_rule
                or native.source_relevance_origin_substream_id
                != expected_origin
                or native.kernel_input_map
                != component.kernel_input_map
            ):
                raise ValueError(
                    "W1 auditory custody differs from its exact mount"
                )


def signed_pcm16_samples(value: bytes) -> tuple[int, ...]:
    """Decode one bounded immutable little-endian PCM16 pressure window."""

    if (
        not isinstance(value, bytes)
        or len(value) % PCM_SAMPLE_WIDTH_BYTES
    ):
        raise ValueError("emitted PCM must be signed little-endian PCM16")
    count = len(value) // PCM_SAMPLE_WIDTH_BYTES
    if not MIN_EMITTED_PCM_SAMPLES <= count <= MAX_EMITTED_PCM_SAMPLES:
        raise ValueError("emitted PCM exceeds its exact sample boundary")
    return tuple(item[0] for item in struct.iter_unpack("<h", value))


def pcm16_bytes(samples: tuple[int, ...]) -> bytes:
    """Encode exact signed PCM16 samples without clipping or saturation."""

    if (
        not isinstance(samples, tuple)
        or any(
            isinstance(sample, bool)
            or not isinstance(sample, int)
            or not -(1 << 15) <= sample < (1 << 15)
            for sample in samples
        )
    ):
        raise ValueError("W1 pressure left signed PCM16")
    return struct.pack(f"<{len(samples)}h", *samples)


def distance_squared_mm(left: PositionMM, right: PositionMM) -> int:
    left.verify()
    right.verify()
    return (
        (left.x - right.x) ** 2
        + (left.y - right.y) ** 2
        + (left.z - right.z) ** 2
    )


def propagation_delay_samples(distance_squared: int) -> int:
    """Exact ceiling of distance times rate divided by sound speed."""

    if (
        isinstance(distance_squared, bool)
        or not isinstance(distance_squared, int)
        or distance_squared < 0
    ):
        raise ValueError("acoustic distance cannot be negative")
    radicand = distance_squared * PCM_SAMPLE_RATE_HZ**2
    root_floor = math.isqrt(radicand)
    root_ceiling = (
        root_floor
        if root_floor * root_floor == radicand
        else root_floor + 1
    )
    return (
        root_ceiling + SPEED_OF_SOUND_MM_PER_SECOND - 1
    ) // SPEED_OF_SOUND_MM_PER_SECOND


def scaled_pcm16_sample(sample: int, attenuation: Fraction) -> int:
    if (
        isinstance(sample, bool)
        or not isinstance(sample, int)
        or not -(1 << 15) <= sample < (1 << 15)
        or not isinstance(attenuation, Fraction)
        or not 0 < attenuation <= 1
    ):
        raise ValueError("W1 acoustic scaling left exact pressure physics")
    magnitude = (
        abs(sample)
        * attenuation.numerator
        // attenuation.denominator
    )
    return -magnitude if sample < 0 else magnitude


def body_from_snapshot(
    snapshot: ObservationSnapshot,
    body_id: str,
) -> EmbodiedBody:
    matches = tuple(
        item for item in snapshot.bodies if item.body_id == body_id
    )
    if len(matches) != 1:
        raise ValueError("W1 body control topology changed")
    return matches[0]


def calibrated_ear_positions(
    body: EmbodiedBody,
    ear_separation_mm: int,
) -> tuple[PositionMM, PositionMM] | None:
    """Return ordered left/right ear positions for exact cardinal headings."""

    if (
        isinstance(ear_separation_mm, bool)
        or not isinstance(ear_separation_mm, int)
        or ear_separation_mm <= 0
        or ear_separation_mm % 2
    ):
        raise ValueError("W1 ear separation must be a positive even integer")
    heading = body.pose.heading_millidegrees
    if heading not in CARDINAL_HEADINGS_MILLIDEGREES:
        return None
    half = ear_separation_mm // 2
    left_offset = {
        0: (0, half),
        90_000: (-half, 0),
        180_000: (0, -half),
        270_000: (half, 0),
    }[heading]
    position = body.pose.position
    left = PositionMM(
        position.x + left_offset[0],
        position.y + left_offset[1],
        position.z,
    )
    right = PositionMM(
        position.x - left_offset[0],
        position.y - left_offset[1],
        position.z,
    )
    return left, right


def render_ear_pressure(
    samples: tuple[int, ...],
    *,
    source: PositionMM,
    ear: PositionMM,
    reference_distance_mm: int,
    pending_samples: tuple[int, ...],
    pending_receipt_sha256s: tuple[str | None, ...],
    emission_receipt_sha256: str,
) -> tuple[
    bytes,
    tuple[int, ...],
    tuple[str | None, ...],
    tuple[str, ...],
    int,
    Fraction,
]:
    """Advance one exact bounded acoustic delay line for one ear."""

    distance_squared = distance_squared_mm(source, ear)
    delay = propagation_delay_samples(distance_squared)
    if (
        isinstance(reference_distance_mm, bool)
        or not isinstance(reference_distance_mm, int)
        or reference_distance_mm <= 0
    ):
        raise ValueError("W1 acoustic reference distance is invalid")
    reference_squared = reference_distance_mm**2
    attenuation = Fraction(
        reference_squared,
        max(reference_squared, distance_squared),
    )
    if (
        bool(pending_samples) != bool(pending_receipt_sha256s)
        or pending_samples
        and (
            len(pending_samples) != delay
            or len(pending_receipt_sha256s) != delay
        )
    ):
        raise ValueError("W1 acoustic propagation path changed inside epoch")
    pending = pending_samples or (0,) * delay
    pending_receipts = pending_receipt_sha256s or (None,) * delay
    continuous = pending + tuple(
        scaled_pcm16_sample(sample, attenuation)
        for sample in samples
    )
    continuous_receipts = pending_receipts + (
        emission_receipt_sha256,
    ) * len(samples)
    rendered = continuous[:len(samples)]
    next_pending = continuous[len(samples):]
    rendered_receipts = continuous_receipts[:len(samples)]
    next_pending_receipts = continuous_receipts[len(samples):]
    if (
        len(next_pending) != delay
        or len(next_pending_receipts) != delay
    ):
        raise RuntimeError(
            "W1 acoustic delay-line cardinality changed"
        )
    contributing_receipts = tuple(dict.fromkeys(
        receipt
        for receipt in rendered_receipts
        if receipt is not None
    ))
    return (
        pcm16_bytes(rendered),
        next_pending,
        next_pending_receipts,
        contributing_receipts,
        delay,
        attenuation,
    )


def binaural_sound_field_inputs(
    *,
    ear: str,
    topology_index: int,
    pcm: bytes,
    source_time_start: Fraction,
) -> W1EarAuditoryTransductionCustody:
    """Mount one ear's pressure through every exact cochlear L0--L4 port."""

    if ear not in ("left", "right"):
        raise ValueError("W1 acoustic receptor must be left or right")
    samples = signed_pcm16_samples(pcm)
    capture = transduce_auditory_full_field(
        np.asarray(samples, dtype=np.float64) / 32_768.0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
    )
    mounted = auditory_kernel_component_inputs(
        capture,
        source_anchor=source_time_start,
    )
    native_inputs = tuple(
        NativeSensorySubstreamInput(
            sense=PhysicalSense.SOUND,
            sensor_id=f"W1-calibrated-{ear}-cochlear-field",
            substream_id=f"{ear}-{item.substream_id}",
            topology_index=topology_index + item.topology_index,
            coordinates=(
                NativeAxisCoordinate("acoustic-receptor", ear),
                *item.coordinates,
            ),
            physical_quantity=item.physical_quantity,
            physical_unit=item.physical_unit,
            source_times=item.source_times,
            normalized_signal=item.normalized_signal,
            phase_turns=item.phase_turns,
            source_relevance=item.source_relevance,
            source_relevance_rule=item.source_relevance_rule,
            source_relevance_origin_substream_id=(
                f"{ear}-{item.source_relevance_origin_substream_id}"
                if item.source_relevance_origin_substream_id is not None
                else None
            ),
            kernel_input_map=item.kernel_input_map,
        )
        for item in mounted
    )
    authority = _VerifiedW1EarAuditoryTransduction(
        ear_id=ear,
        topology_index=topology_index,
        source_time_start=source_time_start,
        source_pcm_sha256=hashlib.sha256(pcm).hexdigest(),
        capture=capture,
        component_inputs=mounted,
        native_inputs=native_inputs,
    )
    custody = W1EarAuditoryTransductionCustody(
        ear_id=authority.ear_id,
        topology_index=authority.topology_index,
        source_time_start=authority.source_time_start,
        source_pcm_sha256=authority.source_pcm_sha256,
        capture=authority.capture,
        component_inputs=authority.component_inputs,
        native_inputs=authority.native_inputs,
        transduction_count=1,
        component_mount_count=1,
        _construction_authority=authority,
    )
    custody.verify()
    return custody


__all__ = [
    "CARDINAL_HEADINGS_MILLIDEGREES",
    "PCM_SAMPLE_WIDTH_BYTES",
    "SPEED_OF_SOUND_MM_PER_SECOND",
    "W1EarAuditoryTransductionCustody",
    "binaural_sound_field_inputs",
    "body_from_snapshot",
    "calibrated_ear_positions",
    "distance_squared_mm",
    "pcm16_bytes",
    "propagation_delay_samples",
    "render_ear_pressure",
    "scaled_pcm16_sample",
    "signed_pcm16_samples",
]
