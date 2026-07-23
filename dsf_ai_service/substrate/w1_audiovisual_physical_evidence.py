"""Bounded anonymous multisensory physics for consecutive W1 observations.

This authority turns one authenticated W1 execution boundary into a transient
two-ear acoustic capture and a two-sample anonymous visual field.  The W1
control topology may select the physical emitter, but no body id, port id,
source tag, word, face, object label, chi address, or Atlas address enters the
perceptual evidence or its persisted receipt.

The visual field is an ordered egocentric geometry field at the exact before
and after observations.  Ordering is spatial, not identity.  If control
topology proves that this order crossed between observations, the evidence is
reported as ambiguous; it is never silently used as a continuity claim.

The acoustic field is rendered at two calibrated ears with exact integer
sample delay and exact rational inverse-square attenuation.  Only cardinal
body headings are admitted because those are the headings for which W1's
integer geometry can place both ears without a trigonometric approximation.

Sight, sound, body, and contact enter the canonical native six-sense builder,
so frozen L0--L4
evaluates D_k, M_k, R_rev_k, U_star_k, C_k, P_k, and B_k independently on
every substream.  The returned compact settlement retains those full fields.
Raw PCM and source geometry are transient and are never retained by this
authority's epoch state or persistence record.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
import struct
import threading
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping

import numpy as np

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SOUND_SUBSTREAMS,
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.embodiment_sensory_outcome import _is_visible
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodiedBody,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
    PositionMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    MAX_EMITTED_PCM_SAMPLES,
    MIN_EMITTED_PCM_SAMPLES,
    PCM_SAMPLE_RATE_HZ,
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Experience,
    W1BinauralAuditoryL5Owner,
)


EVIDENCE_SCHEMA = "guala.w1.anonymous_multisensory_evidence.v7"
PERSISTENCE_SCHEMA = "guala.w1.anonymous_multisensory_persistence.v7"
AUTHORITY_DOMAIN = b"guala-w1-anonymous-multisensory-evidence-v7\0"

PCM_SAMPLE_WIDTH_BYTES = 2
SPEED_OF_SOUND_MM_PER_SECOND = 343_000
MAX_PROPAGATION_DELAY_SAMPLES = MAX_EMITTED_PCM_SAMPLES

_VISUAL_AXES = ("relative-x", "relative-y", "relative-z", "apparent-radius")
_BODY_AXES = (
    "position-x",
    "position-y",
    "position-z",
    "heading",
    "body-radius",
    "reach",
    "holding-contact",
)
_TOUCH_AXES = ("contact", "contact-radius", "contact-mass")
_CARDINAL_HEADINGS = (0, 90_000, 180_000, 270_000)
_PHYSICAL_RADIUS_SCALE = 1 << 20
_BODY_REACH_SCALE = 1 << 20
_OBJECT_MASS_SCALE = 1 << 30


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError("W1 audiovisual authority key must be bytes or text")
    if not 32 <= len(result) <= 4096:
        raise ValueError("W1 audiovisual authority key has an invalid boundary")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise ValueError("W1 audiovisual time must be exact")
    return f"{value.numerator}/{value.denominator}"


def _signed_pcm_samples(value: bytes) -> tuple[int, ...]:
    if (
        not isinstance(value, bytes)
        or len(value) % PCM_SAMPLE_WIDTH_BYTES
    ):
        raise ValueError("emitted PCM must be signed little-endian PCM16")
    count = len(value) // PCM_SAMPLE_WIDTH_BYTES
    if not MIN_EMITTED_PCM_SAMPLES <= count <= MAX_EMITTED_PCM_SAMPLES:
        raise ValueError("emitted PCM exceeds its exact sample boundary")
    return tuple(item[0] for item in struct.iter_unpack("<h", value))


def _pcm_bytes(samples: tuple[int, ...]) -> bytes:
    return struct.pack(f"<{len(samples)}h", *samples)


def _distance_squared(left: PositionMM, right: PositionMM) -> int:
    return (
        (left.x - right.x) ** 2
        + (left.y - right.y) ** 2
        + (left.z - right.z) ** 2
    )


def _delay_samples(distance_squared_mm: int) -> int:
    """Exact ceiling of distance * sample_rate / speed_of_sound."""
    if distance_squared_mm < 0:
        raise ValueError("acoustic distance cannot be negative")
    radicand = distance_squared_mm * PCM_SAMPLE_RATE_HZ**2
    root_floor = math.isqrt(radicand)
    root_ceiling = (
        root_floor if root_floor * root_floor == radicand else root_floor + 1
    )
    return (
        root_ceiling + SPEED_OF_SOUND_MM_PER_SECOND - 1
    ) // SPEED_OF_SOUND_MM_PER_SECOND


def _scaled_sample(sample: int, attenuation: Fraction) -> int:
    magnitude = abs(sample) * attenuation.numerator // attenuation.denominator
    return -magnitude if sample < 0 else magnitude


def _render_ear(
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
    distance_squared = _distance_squared(source, ear)
    delay = _delay_samples(distance_squared)
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
        _scaled_sample(sample, attenuation) for sample in samples
    )
    continuous_receipts = pending_receipts + (
        emission_receipt_sha256,
    ) * len(samples)
    rendered = continuous[:len(samples)]
    next_pending = continuous[len(samples):]
    rendered_receipts = continuous_receipts[:len(samples)]
    next_pending_receipts = continuous_receipts[len(samples):]
    if len(next_pending) != delay:
        raise RuntimeError("W1 acoustic delay line cardinality changed")
    if len(next_pending_receipts) != delay:
        raise RuntimeError("W1 acoustic provenance cardinality changed")
    contributing_receipts = tuple(dict.fromkeys(
        receipt for receipt in rendered_receipts if receipt is not None
    ))
    return (
        _pcm_bytes(rendered),
        next_pending,
        next_pending_receipts,
        contributing_receipts,
        delay,
        attenuation,
    )


def _body(snapshot: ObservationSnapshot, body_id: str) -> EmbodiedBody:
    matches = tuple(item for item in snapshot.bodies if item.body_id == body_id)
    if len(matches) != 1:
        raise ValueError("W1 body control topology changed")
    return matches[0]


def _ear_positions(
    body: EmbodiedBody, ear_separation_mm: int
) -> tuple[PositionMM, PositionMM] | None:
    heading = body.pose.heading_millidegrees
    if heading not in _CARDINAL_HEADINGS:
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


def _global_spans(snapshot: ObservationSnapshot) -> tuple[int, int, int, int]:
    minimum_x = min(item.bounds.minimum.x for item in snapshot.regions)
    maximum_x = max(item.bounds.maximum.x for item in snapshot.regions)
    minimum_y = min(item.bounds.minimum.y for item in snapshot.regions)
    maximum_y = max(item.bounds.maximum.y for item in snapshot.regions)
    minimum_z = min(item.bounds.minimum.z for item in snapshot.regions)
    maximum_z = max(item.bounds.maximum.z for item in snapshot.regions)
    span_x = maximum_x - minimum_x
    span_y = maximum_y - minimum_y
    span_z = max(maximum_z - minimum_z, 1)
    return span_x, span_y, span_z, max(span_x, span_y)


def _binary_scale(maximum_magnitude: int) -> int:
    if maximum_magnitude <= 0:
        raise ValueError("W1 physical normalization span is not positive")
    return 1 << (maximum_magnitude - 1).bit_length()


def _exact_binary_float(value: Fraction) -> float:
    result = float(value)
    if Fraction.from_float(result) != value:
        raise ValueError("W1 native signal is not exactly binary representable")
    return result


@dataclass(frozen=True, slots=True)
class _AnonymousDetection:
    control_track_id: str
    values: tuple[Fraction, Fraction, Fraction, Fraction]

    @property
    def anonymous_order_key(self) -> tuple[Fraction, ...]:
        return self.values


def _anonymous_detections(
    snapshot: ObservationSnapshot,
) -> tuple[_AnonymousDetection, ...]:
    self_body = _body(snapshot, snapshot.self_body_id)
    origin = self_body.pose.position
    span_x, span_y, span_z, _planar_span = _global_spans(snapshot)
    scale_x = _binary_scale(span_x)
    scale_y = _binary_scale(span_y)
    scale_z = _binary_scale(span_z)
    values = []
    for body in snapshot.bodies:
        if body.body_id == snapshot.self_body_id:
            continue
        if not _is_visible(
            snapshot,
            origin,
            body.pose.position,
            body.radius_mm,
        ):
            continue
        position = body.pose.position
        values.append(_AnonymousDetection(
            control_track_id=f"body:{body.body_id}",
            values=(
                Fraction(position.x - origin.x, scale_x),
                Fraction(position.y - origin.y, scale_y),
                Fraction(position.z - origin.z, scale_z),
                Fraction(body.radius_mm, _PHYSICAL_RADIUS_SCALE),
            ),
        ))
    body_by_id = {item.body_id: item for item in snapshot.bodies}
    for item in snapshot.objects:
        position = item.position
        if position is None:
            holder = body_by_id.get(item.held_by_body_id)
            if holder is None:
                raise ValueError("W1 held object control topology changed")
            position = holder.pose.position
        if not _is_visible(snapshot, origin, position, item.radius_mm):
            continue
        values.append(_AnonymousDetection(
            control_track_id=f"object:{item.object_id}",
            values=(
                Fraction(position.x - origin.x, scale_x),
                Fraction(position.y - origin.y, scale_y),
                Fraction(position.z - origin.z, scale_z),
                Fraction(item.radius_mm, _PHYSICAL_RADIUS_SCALE),
            ),
        ))
    return tuple(sorted(values, key=lambda item: item.anonymous_order_key))


def _visual_inputs(
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    *,
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> tuple[
    tuple[NativeSensorySubstreamInput, ...],
    str,
    bool,
]:
    first = _anonymous_detections(before)
    second = _anonymous_detections(after)
    if not first and not second:
        return (), _digest({"before": (), "after": ()}), False
    order_ambiguous = (
        len({item.anonymous_order_key for item in first}) != len(first)
        or len({item.anonymous_order_key for item in second}) != len(second)
    )
    first_by_track = {item.control_track_id: item for item in first}
    second_by_track = {item.control_track_id: item for item in second}
    tracks = set(first_by_track) | set(second_by_track)
    edges = {track: set() for track in tracks}
    indegree = {track: 0 for track in tracks}
    for sequence in (first, second):
        for left, right in zip(sequence, sequence[1:]):
            if right.control_track_id not in edges[left.control_track_id]:
                edges[left.control_track_id].add(right.control_track_id)
                indegree[right.control_track_id] += 1
    merged_order = []
    remaining = set(tracks)
    while remaining:
        available = tuple(
            track for track in remaining if indegree[track] == 0
        )
        if len(available) != 1:
            order_ambiguous = True
            break
        track = available[0]
        merged_order.append(track)
        remaining.remove(track)
        for target in edges[track]:
            indegree[target] -= 1
    absent = (Fraction(0), Fraction(0), Fraction(0), Fraction(-1))
    witness = []
    inputs = []
    for ordinal, track in enumerate(merged_order):
        left_values = (
            first_by_track[track].values
            if track in first_by_track else absent
        )
        right_values = (
            second_by_track[track].values
            if track in second_by_track else absent
        )
        for axis_index, axis in enumerate(_VISUAL_AXES):
            exact_values = (
                left_values[axis_index], right_values[axis_index]
            )
            witness.append({
                "axis": axis,
                "ordinal": ordinal,
                "values": [_fraction_text(item) for item in exact_values],
            })
            inputs.append(NativeSensorySubstreamInput(
                sense=PhysicalSense.SIGHT,
                sensor_id="W1-anonymous-egocentric-visual-geometry",
                substream_id=f"visual-order-{ordinal}-{axis}",
                topology_index=len(inputs),
                coordinates=(
                    NativeAxisCoordinate(
                        "anonymous-spatial-order", str(ordinal)
                    ),
                    NativeAxisCoordinate("physical-axis", axis),
                ),
                physical_quantity="normalized-visual-physical-geometry",
                physical_unit="dimensionless",
                source_times=(source_time_start, source_time_end),
                normalized_signal=tuple(
                    _exact_binary_float(item) for item in exact_values
                ),
                phase_turns=(Fraction(0), Fraction(0)),
            ))
    return tuple(inputs), _digest({
        "schema": "guala.w1.anonymous_visual_series.v1",
        "substreams": witness,
    }), order_ambiguous


def _held_physical_values(
    snapshot: ObservationSnapshot,
) -> tuple[Fraction, Fraction, Fraction]:
    held = tuple(
        item for item in snapshot.objects
        if item.held_by_body_id == snapshot.self_body_id
    )
    if len(held) > 1:
        raise ValueError("W1 self contact topology changed")
    if not held:
        return Fraction(-1), Fraction(0), Fraction(0)
    item = held[0]
    return (
        Fraction(1),
        Fraction(item.radius_mm, _PHYSICAL_RADIUS_SCALE),
        Fraction(item.mass_grams, _OBJECT_MASS_SCALE),
    )


def _somatic_inputs(
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    *,
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> tuple[
    dict[PhysicalSense, tuple[NativeSensorySubstreamInput, ...]],
    str,
]:
    before_self = _body(before, before.self_body_id)
    after_self = _body(after, after.self_body_id)
    span_x, span_y, span_z, _planar_span = _global_spans(after)
    scale_x = _binary_scale(span_x)
    scale_y = _binary_scale(span_y)
    scale_z = _binary_scale(span_z)
    heading_scale = 1 << 19
    minimum_x = min(item.bounds.minimum.x for item in after.regions)
    minimum_y = min(item.bounds.minimum.y for item in after.regions)
    minimum_z = min(item.bounds.minimum.z for item in after.regions)
    before_touch = _held_physical_values(before)
    after_touch = _held_physical_values(after)
    before_body = (
        Fraction(before_self.pose.position.x - minimum_x, scale_x),
        Fraction(before_self.pose.position.y - minimum_y, scale_y),
        Fraction(before_self.pose.position.z - minimum_z, scale_z),
        Fraction(before_self.pose.heading_millidegrees, heading_scale),
        Fraction(before_self.radius_mm, _PHYSICAL_RADIUS_SCALE),
        Fraction(before_self.reach_mm, _BODY_REACH_SCALE),
        before_touch[0],
    )
    after_body = (
        Fraction(after_self.pose.position.x - minimum_x, scale_x),
        Fraction(after_self.pose.position.y - minimum_y, scale_y),
        Fraction(after_self.pose.position.z - minimum_z, scale_z),
        Fraction(after_self.pose.heading_millidegrees, heading_scale),
        Fraction(after_self.radius_mm, _PHYSICAL_RADIUS_SCALE),
        Fraction(after_self.reach_mm, _BODY_REACH_SCALE),
        after_touch[0],
    )
    if any(
        not -1 <= value <= 1
        for value in (*before_body, *after_body, *before_touch, *after_touch)
    ):
        raise ValueError("W1 somatic field left its physical boundary")

    witness = []

    def build(
        sense: PhysicalSense,
        sensor_id: str,
        axes: tuple[str, ...],
        left: tuple[Fraction, ...],
        right: tuple[Fraction, ...],
    ) -> tuple[NativeSensorySubstreamInput, ...]:
        inputs = []
        for index, axis in enumerate(axes):
            exact_values = (left[index], right[index])
            witness.append({
                "axis": axis,
                "sense": sense.value,
                "values": [
                    _fraction_text(item) for item in exact_values
                ],
            })
            inputs.append(NativeSensorySubstreamInput(
                sense=sense,
                sensor_id=sensor_id,
                substream_id=f"anonymous-{sense.value}-{axis}",
                topology_index=index,
                coordinates=(
                    NativeAxisCoordinate("physical-axis", axis),
                    NativeAxisCoordinate(
                        "reference-frame",
                        "proprioceptive" if sense is PhysicalSense.BODY
                        else "body-surface",
                    ),
                ),
                physical_quantity=(
                    "normalized-proprioceptive-geometry"
                    if sense is PhysicalSense.BODY
                    else "normalized-contact-state"
                ),
                physical_unit="dimensionless",
                source_times=(source_time_start, source_time_end),
                normalized_signal=tuple(
                    _exact_binary_float(item) for item in exact_values
                ),
                phase_turns=(Fraction(0), Fraction(0)),
            ))
        return tuple(inputs)

    observed = {
        PhysicalSense.BODY: build(
            PhysicalSense.BODY,
            "W1-anonymous-proprioceptive-field",
            _BODY_AXES,
            before_body,
            after_body,
        ),
        PhysicalSense.TOUCH: build(
            PhysicalSense.TOUCH,
            "W1-anonymous-contact-field",
            _TOUCH_AXES,
            before_touch,
            after_touch,
        ),
    }
    return observed, _digest({
        "schema": "guala.w1.anonymous_somatic_series.v1",
        "substreams": witness,
    })


def _sound_inputs(
    *,
    ear: str,
    topology_index: int,
    pcm: bytes,
    source_time_start: Fraction,
) -> tuple[NativeSensorySubstreamInput, ...]:
    samples = _signed_pcm_samples(pcm)
    capture = transduce_auditory_full_field(
        np.asarray(samples, dtype=np.float64) / 32_768.0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
    )
    mounted = auditory_kernel_component_inputs(
        capture,
        source_anchor=source_time_start,
    )
    return tuple(
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
        )
        for item in mounted
    )


class W1EvidenceState(str, Enum):
    OBSERVED = "observed"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class W1BinauralCalibration:
    ear_separation_mm: int = 200
    reference_distance_mm: int = 1_000

    def verify(self) -> None:
        if (
            isinstance(self.ear_separation_mm, bool)
            or not isinstance(self.ear_separation_mm, int)
            or not 2 <= self.ear_separation_mm <= 1_000
            or self.ear_separation_mm % 2
        ):
            raise ValueError(
                "ear separation must be a positive even integer millimetre value"
            )
        if (
            isinstance(self.reference_distance_mm, bool)
            or not isinstance(self.reference_distance_mm, int)
            or not 1 <= self.reference_distance_mm <= 100_000
        ):
            raise ValueError("acoustic reference distance is invalid")


@dataclass(frozen=True, slots=True)
class W1BinauralPCM:
    left_pcm_s16le: bytes
    right_pcm_s16le: bytes
    emitted_sample_count: int
    left_sample_count: int
    right_sample_count: int
    left_delay_samples: int
    right_delay_samples: int
    left_attenuation: Fraction
    right_attenuation: Fraction

    def commitment_record(self) -> dict[str, object]:
        return {
            "left_attenuation": _fraction_text(self.left_attenuation),
            "left_delay_samples": self.left_delay_samples,
            "left_sample_count": self.left_sample_count,
            "left_pcm_sha256": hashlib.sha256(
                self.left_pcm_s16le
            ).hexdigest(),
            "right_attenuation": _fraction_text(self.right_attenuation),
            "right_delay_samples": self.right_delay_samples,
            "right_sample_count": self.right_sample_count,
            "right_pcm_sha256": hashlib.sha256(
                self.right_pcm_s16le
            ).hexdigest(),
            "emitted_sample_count": self.emitted_sample_count,
            "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
        }

    def verify(self) -> None:
        for name, value in (
            ("emitted", self.emitted_sample_count),
            ("left", self.left_sample_count),
            ("right", self.right_sample_count),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not MIN_EMITTED_PCM_SAMPLES
                <= value
                <= MAX_EMITTED_PCM_SAMPLES
            ):
                raise ValueError(f"binaural {name} sample boundary changed")
        if (
            len(self.left_pcm_s16le)
            != self.left_sample_count * PCM_SAMPLE_WIDTH_BYTES
            or len(self.right_pcm_s16le)
            != self.right_sample_count * PCM_SAMPLE_WIDTH_BYTES
            or self.left_sample_count != self.emitted_sample_count
            or self.right_sample_count != self.emitted_sample_count
        ):
            raise ValueError("binaural PCM cardinality changed")
        _signed_pcm_samples(self.left_pcm_s16le)
        _signed_pcm_samples(self.right_pcm_s16le)
        if self.left_delay_samples < 0 or self.right_delay_samples < 0:
            raise ValueError("binaural delay changed")
        for value in (self.left_attenuation, self.right_attenuation):
            if not isinstance(value, Fraction) or not 0 < value <= 1:
                raise ValueError("binaural attenuation changed")


@dataclass(frozen=True, slots=True)
class W1PhysicalEvidenceReceipt:
    state: W1EvidenceState
    reason: str
    sequence: int
    prior_evidence_receipt_sha256: str | None
    world_execution_receipt_sha256: str | None
    world_observation_before_receipt_sha256: str
    world_observation_after_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    visual_series_sha256: str
    somatic_series_sha256: str
    acoustic_emission_receipt_sha256s: tuple[str, ...]
    binaural_commitment: Mapping[str, object]
    binaural_auditory_l5_authority_receipt_sha256: str | None
    causal_settlement_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "acoustic_emission_receipt_sha256s": list(
                self.acoustic_emission_receipt_sha256s
            ),
            "binaural_commitment": dict(self.binaural_commitment),
            "binaural_auditory_l5_authority_receipt_sha256": (
                self.binaural_auditory_l5_authority_receipt_sha256
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "prior_evidence_receipt_sha256": (
                self.prior_evidence_receipt_sha256
            ),
            "reason": self.reason,
            "schema": EVIDENCE_SCHEMA,
            "sequence": self.sequence,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "state": self.state.value,
            "somatic_series_sha256": self.somatic_series_sha256,
            "visual_series_sha256": self.visual_series_sha256,
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
            "world_observation_after_receipt_sha256": (
                self.world_observation_after_receipt_sha256
            ),
            "world_observation_before_receipt_sha256": (
                self.world_observation_before_receipt_sha256
            ),
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        if not isinstance(self.state, W1EvidenceState):
            raise ValueError("W1 evidence state changed")
        if (
            not isinstance(self.reason, str)
            or not self.reason
            or isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
            or self.source_time_end <= self.source_time_start
        ):
            raise ValueError("W1 evidence boundary changed")
        if self.prior_evidence_receipt_sha256 is not None:
            _sha256(
                self.prior_evidence_receipt_sha256,
                "prior W1 evidence receipt",
            )
        if self.world_execution_receipt_sha256 is not None:
            _sha256(
                self.world_execution_receipt_sha256,
                "W1 world execution receipt",
            )
        _sha256(
            self.world_observation_before_receipt_sha256,
            "W1 before observation receipt",
        )
        _sha256(
            self.world_observation_after_receipt_sha256,
            "W1 after observation receipt",
        )
        _sha256(self.visual_series_sha256, "W1 visual series")
        _sha256(self.somatic_series_sha256, "W1 somatic series")
        if not isinstance(
            self.acoustic_emission_receipt_sha256s, tuple
        ) or len(set(self.acoustic_emission_receipt_sha256s)) != len(
            self.acoustic_emission_receipt_sha256s
        ):
            raise ValueError("W1 acoustic contribution boundary changed")
        for receipt in self.acoustic_emission_receipt_sha256s:
            _sha256(receipt, "W1 authenticated acoustic emission")
        if bool(self.acoustic_emission_receipt_sha256s) != bool(
            self.binaural_commitment
        ):
            raise ValueError(
                "W1 acoustic contribution lost its binaural commitment"
            )
        if self.binaural_auditory_l5_authority_receipt_sha256 is not None:
            _sha256(
                self.binaural_auditory_l5_authority_receipt_sha256,
                "W1 binaural auditory L5 authority",
            )
        if bool(self.acoustic_emission_receipt_sha256s) != bool(
            self.binaural_auditory_l5_authority_receipt_sha256
        ):
            raise ValueError(
                "W1 acoustic contribution lost its binaural L5 authority"
            )
        _sha256(
            self.causal_settlement_receipt_sha256,
            "W1 causal settlement",
        )
        expected_hmac = hmac.new(
            key,
            AUTHORITY_DOMAIN + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected_hmac, self.authority_hmac_sha256
        ):
            raise ValueError("W1 evidence HMAC changed")
        expected_receipt = _digest({
            "authority_hmac_sha256": expected_hmac,
            "payload": self.payload(),
        })
        if expected_receipt != self.authority_receipt_sha256:
            raise ValueError("W1 evidence receipt changed")


@dataclass(frozen=True, slots=True)
class W1PhysicalEvidenceMount:
    state: W1EvidenceState
    reason: str
    evidence_receipt: W1PhysicalEvidenceReceipt | None = None
    binaural_pcm: W1BinauralPCM | None = None
    causal_settlement: CausalExperienceSettlement | None = None
    binaural_auditory_l5: W1BinauralAuditoryL5Experience | None = None

    @property
    def observation_receipt(self) -> W1PhysicalEvidenceReceipt | None:
        return self.evidence_receipt

    def persistence_record(self) -> dict[str, object]:
        """Return a raw-media-free record safe for bounded persistence."""
        return {
            "evidence": (
                self.evidence_receipt.as_record()
                if self.evidence_receipt is not None
                else None
            ),
            "reason": self.reason,
            "schema": PERSISTENCE_SCHEMA,
            "state": self.state.value,
        }

    def verify(self, authority_key: bytes | str) -> None:
        if not isinstance(self.state, W1EvidenceState):
            raise ValueError("W1 evidence mount state changed")
        if self.evidence_receipt is None:
            if self.binaural_pcm is not None or self.causal_settlement is not None:
                raise ValueError("unsettled W1 evidence retained physical payload")
            if self.binaural_auditory_l5 is not None:
                raise ValueError("unsettled W1 evidence retained auditory L5")
            return
        self.evidence_receipt.verify(authority_key)
        if (
            self.state is not self.evidence_receipt.state
            or self.reason != self.evidence_receipt.reason
        ):
            raise ValueError("W1 physical mount differs from its receipt")
        if self.causal_settlement is None:
            raise ValueError("settled W1 evidence is incomplete")
        self.causal_settlement.verify()
        acoustic = self.evidence_receipt.acoustic_emission_receipt_sha256s
        if acoustic:
            if self.binaural_pcm is None:
                raise ValueError("settled W1 acoustic evidence is incomplete")
            if self.binaural_auditory_l5 is None:
                raise ValueError("settled W1 acoustic L5 evidence is incomplete")
            self.binaural_pcm.verify()
            self.binaural_auditory_l5.verify()
            if self.binaural_pcm.commitment_record() != dict(
                self.evidence_receipt.binaural_commitment
            ):
                raise ValueError("W1 physical evidence differs from its receipt")
            if (
                self.binaural_auditory_l5.authority_receipt_sha256
                != self.evidence_receipt
                .binaural_auditory_l5_authority_receipt_sha256
                or self.binaural_auditory_l5
                .upstream_causal_settlement_receipt_sha256
                != self.causal_settlement.authority_receipt_sha256
            ):
                raise ValueError("W1 auditory L5 differs from physical evidence")
        elif self.binaural_pcm is not None or dict(
            self.evidence_receipt.binaural_commitment
        ) or self.binaural_auditory_l5 is not None:
            raise ValueError("W1 unavailable sound retained acoustic payload")
        if self.causal_settlement.authority_receipt_sha256 != (
            self.evidence_receipt.causal_settlement_receipt_sha256
        ):
            raise ValueError("W1 physical evidence differs from its receipt")
        for sense in self.causal_settlement.interpretations:
            for substream in sense.substreams:
                for field_tuple in substream.field_tuples:
                    if tuple(name for name, _value in field_tuple.fields) != (
                        DSF_FIELD_ORDER
                    ):
                        raise ValueError(
                            "W1 evidence lost full DSF field order"
                        )


@dataclass(frozen=True, slots=True)
class _BinauralRender:
    binaural: W1BinauralPCM
    left_pending_samples: tuple[int, ...]
    right_pending_samples: tuple[int, ...]
    left_pending_receipt_sha256s: tuple[str | None, ...]
    right_pending_receipt_sha256s: tuple[str | None, ...]
    contributing_receipt_sha256s: tuple[str, ...]
    path_commitment_sha256: str


@dataclass(slots=True)
class _Epoch:
    expected_sequence: int = 0
    next_source_sample_index: int = 0
    prior_evidence_receipt_sha256: str | None = None
    previous_after_observation_receipt_sha256: str | None = None
    left_pending_samples: tuple[int, ...] = ()
    right_pending_samples: tuple[int, ...] = ()
    left_pending_receipt_sha256s: tuple[str | None, ...] = ()
    right_pending_receipt_sha256s: tuple[str | None, ...] = ()
    path_commitment_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class _PreparedAudiovisualMount:
    epoch_token: str
    prior_epoch: _Epoch
    next_epoch: _Epoch
    mount: W1PhysicalEvidenceMount


@dataclass(frozen=True, slots=True)
class _AtomicAudiovisualEpisode:
    epoch_token: str
    causal_sequence_token: str
    binaural_l5_sequence_token: str


class W1AudiovisualPhysicalEvidenceAuthority:
    """Transient bounded owner of anonymous W1 audiovisual captures."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        causal_owner: ExactCausalExperienceOwner,
        acoustic_emitter: W1AcousticEmitterAuthority,
        binaural_auditory_l5_owner: W1BinauralAuditoryL5Owner,
        calibration: W1BinauralCalibration | None = None,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 evidence requires the world authority")
        if not isinstance(causal_owner, ExactCausalExperienceOwner):
            raise TypeError("W1 evidence requires an exact causal owner")
        if not isinstance(acoustic_emitter, W1AcousticEmitterAuthority):
            raise TypeError("W1 evidence requires the acoustic emitter authority")
        if not isinstance(
            binaural_auditory_l5_owner,
            W1BinauralAuditoryL5Owner,
        ):
            raise TypeError("W1 evidence requires the binaural auditory L5 owner")
        if not acoustic_emitter.owns_world(world_authority):
            raise ValueError("W1 acoustic emitter belongs to another world")
        self._key = _key(authority_key)
        self._world = world_authority
        self._causal_owner = causal_owner
        self._acoustic_emitter = acoustic_emitter
        self._binaural_auditory_l5_owner = binaural_auditory_l5_owner
        self._calibration = calibration or W1BinauralCalibration()
        self._calibration.verify()
        self._epoch_capacity = len(world_authority.actor_ports)
        self._epochs: dict[str, _Epoch] = {}
        self._prepared_mount: _PreparedAudiovisualMount | None = None
        self._pending_reservation: tuple[
            str,
            CausalExperienceSettlement,
            W1BinauralAuditoryL5Experience | None,
        ] | None = None
        self._atomic_episode: _AtomicAudiovisualEpisode | None = None
        self._lock = threading.RLock()

    def begin_atomic_episode(self) -> str:
        """Open one rollback-capable, exact multi-mount W1 episode."""
        with self._lock:
            if (
                self._atomic_episode is not None
                or self._prepared_mount is not None
                or self._pending_reservation is not None
            ):
                raise RuntimeError(
                    "W1 audiovisual authority already has an active transaction"
                )
            if len(self._epochs) >= self._epoch_capacity:
                raise RuntimeError("W1 audiovisual epoch capacity is full")
            causal_token = self._causal_owner.begin_atomic_sequence()
            try:
                l5_token = (
                    self._binaural_auditory_l5_owner.begin_atomic_sequence()
                )
            except BaseException:
                self._causal_owner.rollback_atomic_sequence(causal_token)
                raise
            while True:
                epoch_token = secrets.token_urlsafe(24)
                if epoch_token not in self._epochs:
                    break
            self._epochs[epoch_token] = _Epoch()
            self._atomic_episode = _AtomicAudiovisualEpisode(
                epoch_token=epoch_token,
                causal_sequence_token=causal_token,
                binaural_l5_sequence_token=l5_token,
            )
            return epoch_token

    def commit_atomic_episode(self, epoch_token: str) -> None:
        """Publish one fully prepared multi-mount episode and close its epoch."""
        with self._lock:
            transaction = self._atomic_episode
            if (
                transaction is None
                or transaction.epoch_token != epoch_token
                or epoch_token not in self._epochs
                or self._prepared_mount is not None
                or self._pending_reservation is not None
            ):
                raise ValueError("W1 atomic audiovisual episode changed")
            self._causal_owner.verify_atomic_sequence(
                transaction.causal_sequence_token
            )
            self._binaural_auditory_l5_owner.verify_atomic_sequence(
                transaction.binaural_l5_sequence_token
            )
            l5_undo = self._binaural_auditory_l5_owner.commit_atomic_sequence(
                transaction.binaural_l5_sequence_token
            )
            try:
                self._causal_owner.commit_atomic_sequence(
                    transaction.causal_sequence_token
                )
            except BaseException:
                self._binaural_auditory_l5_owner.rollback_committed_atomic_sequence(
                    l5_undo
                )
                raise
            del self._epochs[epoch_token]
            self._atomic_episode = None

    def rollback_atomic_episode(self, epoch_token: str) -> None:
        """Erase all causal/L5 relation changes made by one W1 episode."""
        with self._lock:
            transaction = self._atomic_episode
            if (
                transaction is None
                or transaction.epoch_token != epoch_token
            ):
                raise ValueError("W1 atomic audiovisual episode changed")
            prepared = self._prepared_mount
            if prepared is not None:
                if prepared.epoch_token != epoch_token:
                    raise RuntimeError(
                        "another audiovisual mount entered an atomic episode"
                    )
                self.discard_prepared_multisensory_mount(prepared.mount)
            pending = self._pending_reservation
            if pending is not None:
                if pending[0] != epoch_token:
                    raise RuntimeError(
                        "another causal reservation entered an atomic episode"
                    )
                if pending[2] is not None:
                    self._binaural_auditory_l5_owner.discard_prepared(
                        pending[2]
                    )
                self._causal_owner.discard_prepared(pending[1])
                self._pending_reservation = None
            self._causal_owner.verify_atomic_sequence(
                transaction.causal_sequence_token
            )
            self._binaural_auditory_l5_owner.verify_atomic_sequence(
                transaction.binaural_l5_sequence_token
            )
            self._binaural_auditory_l5_owner.rollback_atomic_sequence(
                transaction.binaural_l5_sequence_token
            )
            self._causal_owner.rollback_atomic_sequence(
                transaction.causal_sequence_token
            )
            self._epochs.pop(epoch_token, None)
            self._atomic_episode = None

    def open_epoch(self) -> str:
        with self._lock:
            if self._atomic_episode is not None:
                raise RuntimeError(
                    "W1 audiovisual atomic episode owns the authority"
                )
            if len(self._epochs) >= self._epoch_capacity:
                raise RuntimeError("W1 audiovisual epoch capacity is full")
            while True:
                token = secrets.token_urlsafe(24)
                if token not in self._epochs:
                    self._epochs[token] = _Epoch()
                    return token

    def close_epoch(self, epoch_token: str) -> bool:
        with self._lock:
            if (
                self._atomic_episode is not None
                and self._atomic_episode.epoch_token == epoch_token
            ):
                raise RuntimeError(
                    "W1 atomic audiovisual episode requires commit or rollback"
                )
            prepared = self._prepared_mount
            if prepared is not None and prepared.epoch_token == epoch_token:
                raise RuntimeError(
                    "W1 audiovisual epoch has a prepared transaction"
                )
            pending = self._pending_reservation
            if pending is not None and pending[0] == epoch_token:
                if pending[2] is not None:
                    self._binaural_auditory_l5_owner.discard_prepared(
                        pending[2]
                    )
                self._causal_owner.discard_prepared(pending[1])
                self._pending_reservation = None
            return self._epochs.pop(epoch_token, None) is not None

    def emit_acoustic_pressure(
        self,
        *,
        epoch_token: str,
        sequence: int,
        source_sample_start: int,
        observation_snapshot: ObservationSnapshot,
        execution_receipt: ActionExecutionReceipt,
        command_payload: bytes,
        emitter_port_id: str,
        pcm_s16le: bytes,
    ) -> AuthenticatedW1AcousticEmission:
        """Execute the authenticated transient W1 emitter transaction."""
        return self._acoustic_emitter.emit(
            epoch_token=epoch_token,
            sequence=sequence,
            source_sample_start=source_sample_start,
            observation_snapshot=observation_snapshot,
            execution_receipt=execution_receipt,
            command_payload=command_payload,
            emitter_port_id=emitter_port_id,
            pcm_s16le=pcm_s16le,
        )

    @staticmethod
    def _unsettled(
        state: W1EvidenceState, reason: str
    ) -> W1PhysicalEvidenceMount:
        result = W1PhysicalEvidenceMount(state=state, reason=reason)
        result.verify(b"x" * 32)
        return result

    def verify_mount(self, mount: W1PhysicalEvidenceMount) -> None:
        if not isinstance(mount, W1PhysicalEvidenceMount):
            raise TypeError("W1 physical evidence mount is required")
        mount.verify(self._key)

    def verify_evidence_receipt(
        self, receipt: W1PhysicalEvidenceReceipt
    ) -> None:
        if not isinstance(receipt, W1PhysicalEvidenceReceipt):
            raise TypeError("W1 physical evidence receipt is required")
        receipt.verify(self._key)

    def _mount_anonymous_physical_boundary(
        self,
        *,
        before: ObservationSnapshot,
        after: ObservationSnapshot,
        execution_receipt_sha256: str | None,
        reason: str,
        commit: bool,
        reserve: bool = False,
    ) -> W1PhysicalEvidenceMount:
        if not isinstance(commit, bool):
            raise TypeError("W1 physical boundary commit flag must be boolean")
        if not isinstance(reserve, bool):
            raise TypeError("W1 physical boundary reserve flag must be boolean")
        if reserve and commit:
            raise ValueError("W1 physical boundary cannot reserve and commit")
        source_time_start = Fraction(0)
        source_time_end = Fraction(1)
        visual_inputs, visual_commitment, visual_order_crossed = _visual_inputs(
            before,
            after,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
        if visual_order_crossed:
            return self._unsettled(
                W1EvidenceState.AMBIGUOUS,
                "anonymous_visual_order_crossed",
            )
        if not visual_inputs:
            return self._unsettled(
                W1EvidenceState.UNKNOWN,
                "anonymous_visual_series_is_incomplete",
            )
        somatic_inputs, somatic_commitment = _somatic_inputs(
            before,
            after,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
        states = {
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in (
                    PhysicalSense.SIGHT,
                    PhysicalSense.TOUCH,
                    PhysicalSense.BODY,
                )
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        }
        assembly_id = "w1-anonymous-physical-boundary-" + _digest({
            "after_observation_receipt_sha256": (
                after.authority_receipt_sha256
            ),
            "before_observation_receipt_sha256": (
                before.authority_receipt_sha256
            ),
            "execution_receipt_sha256": execution_receipt_sha256,
            "somatic_series_sha256": somatic_commitment,
            "visual_series_sha256": visual_commitment,
        })
        built = build_six_sense_full_field(
            assembly_id=assembly_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            observed_substreams={
                PhysicalSense.SIGHT: visual_inputs,
                **somatic_inputs,
            },
            states=states,
        )
        settlement_owner = (
            self._causal_owner
            if commit or reserve
            else ExactCausalExperienceOwner(
                on_settlement=lambda _settlement: None,
                log_event=lambda *_args, **_kwargs: None,
            )
        )
        settlement = settlement_owner.settle(
            built,
            routing_chis=(),
            source_tags=(),
            commit=commit,
            reserve=False,
        )
        payload = {
            "acoustic_emission_receipt_sha256s": [],
            "binaural_commitment": {},
            "binaural_auditory_l5_authority_receipt_sha256": None,
            "causal_settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "prior_evidence_receipt_sha256": None,
            "reason": reason,
            "schema": EVIDENCE_SCHEMA,
            "sequence": 0,
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "state": W1EvidenceState.OBSERVED.value,
            "somatic_series_sha256": somatic_commitment,
            "visual_series_sha256": visual_commitment,
            "world_execution_receipt_sha256": execution_receipt_sha256,
            "world_observation_after_receipt_sha256": (
                after.authority_receipt_sha256
            ),
            "world_observation_before_receipt_sha256": (
                before.authority_receipt_sha256
            ),
        }
        signature = hmac.new(
            self._key,
            AUTHORITY_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        receipt = W1PhysicalEvidenceReceipt(
            state=W1EvidenceState.OBSERVED,
            reason=reason,
            sequence=0,
            prior_evidence_receipt_sha256=None,
            world_execution_receipt_sha256=execution_receipt_sha256,
            world_observation_before_receipt_sha256=(
                before.authority_receipt_sha256
            ),
            world_observation_after_receipt_sha256=(
                after.authority_receipt_sha256
            ),
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            visual_series_sha256=visual_commitment,
            somatic_series_sha256=somatic_commitment,
            acoustic_emission_receipt_sha256s=(),
            binaural_commitment={},
            binaural_auditory_l5_authority_receipt_sha256=None,
            causal_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result = W1PhysicalEvidenceMount(
            state=W1EvidenceState.OBSERVED,
            reason=reason,
            evidence_receipt=receipt,
            causal_settlement=settlement,
        )
        self.verify_mount(result)
        if reserve:
            self._causal_owner.reserve_prepared(settlement)
        return result

    def mount_current_observation(
        self, *, commit: bool = True
    ) -> W1PhysicalEvidenceMount:
        observation = self._world.observation_snapshot()
        return self.mount_authenticated_observation(
            observation, commit=commit
        )

    def mount_authenticated_observation(
        self,
        observation: ObservationSnapshot,
        *,
        commit: bool = False,
    ) -> W1PhysicalEvidenceMount:
        self._world.verify_observation_snapshot(observation)
        return self._mount_anonymous_physical_boundary(
            before=observation,
            after=observation,
            execution_receipt_sha256=None,
            reason="anonymous_current_physical_field_observed",
            commit=commit,
        )

    def mount_action_outcome(
        self,
        execution_receipt: ActionExecutionReceipt,
        *,
        commit: bool = True,
        reserve: bool = False,
    ) -> W1PhysicalEvidenceMount:
        self._world.verify_execution_receipt(execution_receipt)
        current = self._world.observation_snapshot()
        if current != execution_receipt.after:
            raise ValueError("W1 action outcome is not the current world")
        return self.mount_authenticated_action_outcome(
            execution_receipt,
            commit=commit,
            reserve=reserve,
        )

    def mount_authenticated_action_outcome(
        self,
        execution_receipt: ActionExecutionReceipt,
        *,
        commit: bool = False,
        reserve: bool = False,
    ) -> W1PhysicalEvidenceMount:
        """Reproduce one authority-verified historical physical transition."""

        self._world.verify_execution_receipt(execution_receipt)
        if (
            execution_receipt.disposition != "applied"
            or execution_receipt.after.revision
            != execution_receipt.before.revision + 1
            or execution_receipt.observed_revision
            != execution_receipt.before.revision
        ):
            raise ValueError(
                "W1 action outcome requires one applied physical transition"
            )
        return self._mount_anonymous_physical_boundary(
            before=execution_receipt.before,
            after=execution_receipt.after,
            execution_receipt_sha256=(
                execution_receipt.authority_receipt_sha256
            ),
            reason="anonymous_action_outcome_observed",
            commit=commit,
            reserve=reserve,
        )

    def commit_prepared_mount(
        self, mount: W1PhysicalEvidenceMount
    ) -> None:
        self.verify_mount(mount)
        if mount.causal_settlement is None:
            raise ValueError("W1 prepared mount has no causal settlement")
        self._causal_owner.commit_prepared(mount.causal_settlement)

    def discard_prepared_mount(
        self, mount: W1PhysicalEvidenceMount
    ) -> None:
        if not isinstance(mount, W1PhysicalEvidenceMount):
            raise TypeError("W1 physical evidence mount is required")
        if mount.causal_settlement is None:
            raise ValueError("W1 prepared mount has no causal settlement")
        self._causal_owner.discard_prepared(mount.causal_settlement)

    def _binaural(
        self,
        *,
        execution: ActionExecutionReceipt,
        emitter_port_id: str,
        emitted_samples: tuple[int, ...],
        emission_receipt_sha256: str,
        left_pending_samples: tuple[int, ...],
        right_pending_samples: tuple[int, ...],
        left_pending_receipt_sha256s: tuple[str | None, ...],
        right_pending_receipt_sha256s: tuple[str | None, ...],
        prior_path_commitment_sha256: str | None,
    ) -> _BinauralRender | W1PhysicalEvidenceMount:
        actor_by_port = {
            item.port_id: item.actor_body_id
            for item in self._world.actor_ports
        }
        emitter_body_id = actor_by_port.get(emitter_port_id)
        if emitter_body_id is None:
            raise ValueError("W1 acoustic emitter port is not mounted")
        if emitter_body_id == execution.after.self_body_id:
            return self._unsettled(
                W1EvidenceState.UNAVAILABLE,
                "self_emission_is_not_external_source_evidence",
            )
        after_self = _body(execution.after, execution.after.self_body_id)
        after_emitter = _body(execution.after, emitter_body_id)
        if not _is_visible(
            execution.after,
            after_self.pose.position,
            after_emitter.pose.position,
            after_emitter.radius_mm,
        ):
            return self._unsettled(
                W1EvidenceState.UNKNOWN,
                "acoustic_emitter_is_not_visible_at_emission",
            )
        ears = _ear_positions(
            after_self, self._calibration.ear_separation_mm
        )
        if ears is None:
            return self._unsettled(
                W1EvidenceState.UNAVAILABLE,
                "noncardinal_two_ear_calibration_is_unavailable",
            )
        left, right = ears
        left_distance_squared = _distance_squared(
            after_emitter.pose.position, left
        )
        right_distance_squared = _distance_squared(
            after_emitter.pose.position, right
        )
        prospective_left_delay = _delay_samples(left_distance_squared)
        prospective_right_delay = _delay_samples(right_distance_squared)
        if (
            prospective_left_delay > MAX_PROPAGATION_DELAY_SAMPLES
            or prospective_right_delay > MAX_PROPAGATION_DELAY_SAMPLES
        ):
            return self._unsettled(
                W1EvidenceState.UNAVAILABLE,
                "acoustic_path_exceeds_bounded_delay_line",
            )
        reference_squared = self._calibration.reference_distance_mm**2
        prospective_left_attenuation = Fraction(
            reference_squared,
            max(reference_squared, left_distance_squared),
        )
        prospective_right_attenuation = Fraction(
            reference_squared,
            max(reference_squared, right_distance_squared),
        )
        path_commitment = _digest({
            "ear_separation_mm": self._calibration.ear_separation_mm,
            "left_attenuation": _fraction_text(
                prospective_left_attenuation
            ),
            "left_delay_samples": prospective_left_delay,
            "reference_distance_mm": (
                self._calibration.reference_distance_mm
            ),
            "right_attenuation": _fraction_text(
                prospective_right_attenuation
            ),
            "right_delay_samples": prospective_right_delay,
            "schema": "guala.w1.anonymous_acoustic_path.v1",
        })
        if (
            prior_path_commitment_sha256 is not None
            and prior_path_commitment_sha256 != path_commitment
        ):
            return self._unsettled(
                W1EvidenceState.UNKNOWN,
                "acoustic_path_changed_closed_the_epoch",
            )
        (
            left_pcm,
            next_left_pending,
            next_left_pending_receipts,
            left_contributing_receipts,
            left_delay,
            left_attenuation,
        ) = _render_ear(
            emitted_samples,
            source=after_emitter.pose.position,
            ear=left,
            reference_distance_mm=self._calibration.reference_distance_mm,
            pending_samples=left_pending_samples,
            pending_receipt_sha256s=left_pending_receipt_sha256s,
            emission_receipt_sha256=emission_receipt_sha256,
        )
        (
            right_pcm,
            next_right_pending,
            next_right_pending_receipts,
            right_contributing_receipts,
            right_delay,
            right_attenuation,
        ) = _render_ear(
            emitted_samples,
            source=after_emitter.pose.position,
            ear=right,
            reference_distance_mm=self._calibration.reference_distance_mm,
            pending_samples=right_pending_samples,
            pending_receipt_sha256s=right_pending_receipt_sha256s,
            emission_receipt_sha256=emission_receipt_sha256,
        )
        if (
            left_delay != prospective_left_delay
            or right_delay != prospective_right_delay
            or left_attenuation != prospective_left_attenuation
            or right_attenuation != prospective_right_attenuation
        ):
            raise RuntimeError("W1 acoustic path changed during rendering")
        result = W1BinauralPCM(
            left_pcm_s16le=left_pcm,
            right_pcm_s16le=right_pcm,
            emitted_sample_count=len(emitted_samples),
            left_sample_count=len(left_pcm) // PCM_SAMPLE_WIDTH_BYTES,
            right_sample_count=len(right_pcm) // PCM_SAMPLE_WIDTH_BYTES,
            left_delay_samples=left_delay,
            right_delay_samples=right_delay,
            left_attenuation=left_attenuation,
            right_attenuation=right_attenuation,
        )
        result.verify()
        return _BinauralRender(
            binaural=result,
            left_pending_samples=next_left_pending,
            right_pending_samples=next_right_pending,
            left_pending_receipt_sha256s=next_left_pending_receipts,
            right_pending_receipt_sha256s=next_right_pending_receipts,
            contributing_receipt_sha256s=tuple(dict.fromkeys(
                left_contributing_receipts + right_contributing_receipts
            )),
            path_commitment_sha256=path_commitment,
        )

    def mount(
        self,
        *,
        epoch_token: str,
        sequence: int,
        execution_receipt: ActionExecutionReceipt,
        acoustic_emission: AuthenticatedW1AcousticEmission,
        commit: bool = True,
    ) -> W1PhysicalEvidenceMount:
        if not isinstance(commit, bool):
            raise TypeError("W1 audiovisual commit flag must be boolean")
        if (
            not isinstance(epoch_token, str)
            or not epoch_token
            or len(epoch_token.encode("utf-8")) > 256
        ):
            raise ValueError("W1 audiovisual epoch token is required")
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence < 0
        ):
            raise ValueError("W1 audiovisual sequence is invalid")
        self._world.verify_execution_receipt(execution_receipt)
        if not isinstance(
            acoustic_emission, AuthenticatedW1AcousticEmission
        ):
            raise TypeError("W1 authenticated acoustic emission is required")
        self._acoustic_emitter.verify_emission(
            acoustic_emission,
            observation_snapshot=execution_receipt.after,
            execution_receipt=execution_receipt,
        )
        emission_receipt = acoustic_emission.receipt
        if (
            emission_receipt.epoch_commitment_sha256
            != hashlib.sha256(epoch_token.encode("utf-8")).hexdigest()
            or emission_receipt.sequence != sequence
        ):
            raise ValueError("W1 acoustic emission belongs to another epoch")
        emitted_pcm_s16le = acoustic_emission.pcm_s16le
        emitted_samples = _signed_pcm_samples(emitted_pcm_s16le)
        if (
            execution_receipt.disposition != "applied"
            or execution_receipt.after.revision
            != execution_receipt.before.revision + 1
            or execution_receipt.observed_revision
            != execution_receipt.before.revision
        ):
            return self._unsettled(
                W1EvidenceState.UNKNOWN,
                "W1_execution_is_not_one_authenticated_transition",
            )

        with self._lock:
            if (
                self._prepared_mount is not None
                or self._pending_reservation is not None
            ):
                raise RuntimeError(
                    "W1 audiovisual mount already has a prepared transaction"
                )
            atomic_episode = self._atomic_episode
            if (
                atomic_episode is not None
                and atomic_episode.epoch_token != epoch_token
            ):
                raise RuntimeError(
                    "W1 audiovisual atomic episode owns another epoch"
                )
            epoch = self._epochs.get(epoch_token)
            if epoch is None:
                return self._unsettled(
                    W1EvidenceState.UNKNOWN,
                    "audiovisual_epoch_unknown_after_gap_or_restart",
                )
            if sequence != epoch.expected_sequence:
                del self._epochs[epoch_token]
                return self._unsettled(
                    W1EvidenceState.UNKNOWN,
                    "audiovisual_sequence_gap_closed_the_epoch",
                )
            if emission_receipt.source_sample_start != (
                epoch.next_source_sample_index
            ):
                del self._epochs[epoch_token]
                return self._unsettled(
                    W1EvidenceState.UNKNOWN,
                    "acoustic_sample_gap_closed_the_epoch",
                )
            if (
                epoch.previous_after_observation_receipt_sha256 is not None
                and execution_receipt.before.authority_receipt_sha256
                != epoch.previous_after_observation_receipt_sha256
            ):
                del self._epochs[epoch_token]
                return self._unsettled(
                    W1EvidenceState.UNKNOWN,
                    "W1_observation_gap_closed_the_epoch",
                )

            rendered = self._binaural(
                execution=execution_receipt,
                emitter_port_id=emission_receipt.emitter_port_id,
                emitted_samples=emitted_samples,
                emission_receipt_sha256=(
                    emission_receipt.authority_receipt_sha256
                ),
                left_pending_samples=epoch.left_pending_samples,
                right_pending_samples=epoch.right_pending_samples,
                left_pending_receipt_sha256s=(
                    epoch.left_pending_receipt_sha256s
                ),
                right_pending_receipt_sha256s=(
                    epoch.right_pending_receipt_sha256s
                ),
                prior_path_commitment_sha256=(
                    epoch.path_commitment_sha256
                ),
            )
            if isinstance(rendered, W1PhysicalEvidenceMount):
                del self._epochs[epoch_token]
                return rendered
            binaural = rendered.binaural

            source_time_start = Fraction(
                epoch.next_source_sample_index, PCM_SAMPLE_RATE_HZ
            )
            source_time_end = source_time_start + Fraction(
                len(emitted_samples), PCM_SAMPLE_RATE_HZ
            )
            visual_inputs, visual_commitment, visual_order_crossed = (
                _visual_inputs(
                    execution_receipt.before,
                    execution_receipt.after,
                    source_time_start=source_time_start,
                    source_time_end=source_time_end,
                )
            )
            somatic_inputs, somatic_commitment = _somatic_inputs(
                execution_receipt.before,
                execution_receipt.after,
                source_time_start=source_time_start,
                source_time_end=source_time_end,
            )
            if visual_order_crossed:
                del self._epochs[epoch_token]
                return self._unsettled(
                    W1EvidenceState.AMBIGUOUS,
                    "anonymous_visual_order_crossed",
                )
            if not visual_inputs:
                del self._epochs[epoch_token]
                return self._unsettled(
                    W1EvidenceState.UNKNOWN,
                    "anonymous_visual_series_is_incomplete",
                )
            if not (
                any(_signed_pcm_samples(binaural.left_pcm_s16le))
                or any(_signed_pcm_samples(binaural.right_pcm_s16le))
            ):
                epoch.expected_sequence += 1
                epoch.next_source_sample_index = (
                    emission_receipt.source_sample_end
                )
                epoch.previous_after_observation_receipt_sha256 = (
                    execution_receipt.after.authority_receipt_sha256
                )
                epoch.left_pending_samples = rendered.left_pending_samples
                epoch.right_pending_samples = rendered.right_pending_samples
                epoch.left_pending_receipt_sha256s = (
                    rendered.left_pending_receipt_sha256s
                )
                epoch.right_pending_receipt_sha256s = (
                    rendered.right_pending_receipt_sha256s
                )
                epoch.path_commitment_sha256 = (
                    rendered.path_commitment_sha256
                )
                return self._unsettled(
                    W1EvidenceState.UNKNOWN,
                    "received_pressure_is_silent",
                )
            if binaural.left_pcm_s16le == binaural.right_pcm_s16le:
                del self._epochs[epoch_token]
                return self._unsettled(
                    W1EvidenceState.AMBIGUOUS,
                    "two_ear_field_is_spatially_symmetric",
                )
            if not rendered.contributing_receipt_sha256s:
                raise RuntimeError(
                    "received pressure lost authenticated source provenance"
                )
            left_sound = _sound_inputs(
                ear="left",
                topology_index=0,
                pcm=binaural.left_pcm_s16le,
                source_time_start=source_time_start,
            )
            right_sound = _sound_inputs(
                ear="right",
                topology_index=AUDITORY_KERNEL_COMPONENT_COUNT,
                pcm=binaural.right_pcm_s16le,
                source_time_start=source_time_start,
            )
            sound_inputs = (*left_sound, *right_sound)
            if len(sound_inputs) != MAX_NATIVE_SOUND_SUBSTREAMS:
                raise RuntimeError(
                    "W1 binaural cochlear topology lost a native component"
                )
            states = {
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense in (
                        PhysicalSense.SIGHT,
                        PhysicalSense.SOUND,
                        PhysicalSense.TOUCH,
                        PhysicalSense.BODY,
                    )
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            }
            assembly_id = "w1-anonymous-multisensory-" + _digest({
                "acoustic_emission_receipt_sha256s": (
                    rendered.contributing_receipt_sha256s
                ),
                "binaural_commitment": binaural.commitment_record(),
                "execution_receipt_sha256": (
                    execution_receipt.authority_receipt_sha256
                ),
                "prior_evidence_receipt_sha256": (
                    epoch.prior_evidence_receipt_sha256
                ),
                "sequence": sequence,
                "somatic_series_sha256": somatic_commitment,
                "visual_series_sha256": visual_commitment,
                "world_execution_receipt_sha256": (
                    execution_receipt.authority_receipt_sha256
                ),
            })
            built = build_six_sense_full_field(
                assembly_id=assembly_id,
                source_time_start=source_time_start,
                source_time_end=source_time_end,
                observed_substreams={
                    PhysicalSense.SIGHT: visual_inputs,
                    PhysicalSense.SOUND: sound_inputs,
                    **somatic_inputs,
                },
                states=states,
            )
            settlement = self._causal_owner.settle(
                built,
                routing_chis=(),
                source_tags=(),
                commit=False,
                reserve=True,
            )
            self._pending_reservation = (epoch_token, settlement, None)
            try:
                binaural_auditory_l5 = (
                    self._binaural_auditory_l5_owner.prepare(settlement)
                )
            except BaseException:
                self._causal_owner.discard_prepared(settlement)
                self._pending_reservation = None
                raise
            self._pending_reservation = (
                epoch_token,
                settlement,
                binaural_auditory_l5,
            )
            state = W1EvidenceState.OBSERVED
            reason = "anonymous_multisensory_evidence_observed"
            commitment = binaural.commitment_record()
            payload = {
                "acoustic_emission_receipt_sha256s": list(
                    rendered.contributing_receipt_sha256s
                ),
                "binaural_commitment": commitment,
                "binaural_auditory_l5_authority_receipt_sha256": (
                    binaural_auditory_l5.authority_receipt_sha256
                ),
                "causal_settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
                "prior_evidence_receipt_sha256": (
                    epoch.prior_evidence_receipt_sha256
                ),
                "reason": reason,
                "schema": EVIDENCE_SCHEMA,
                "sequence": sequence,
                "source_time_end": _fraction_text(source_time_end),
                "source_time_start": _fraction_text(source_time_start),
                "state": state.value,
                "somatic_series_sha256": somatic_commitment,
                "visual_series_sha256": visual_commitment,
                "world_execution_receipt_sha256": (
                    execution_receipt.authority_receipt_sha256
                ),
                "world_observation_after_receipt_sha256": (
                    execution_receipt.after.authority_receipt_sha256
                ),
                "world_observation_before_receipt_sha256": (
                    execution_receipt.before.authority_receipt_sha256
                ),
            }
            signature = hmac.new(
                self._key,
                AUTHORITY_DOMAIN + _canonical(payload),
                hashlib.sha256,
            ).hexdigest()
            receipt = W1PhysicalEvidenceReceipt(
                state=state,
                reason=reason,
                sequence=sequence,
                prior_evidence_receipt_sha256=(
                    epoch.prior_evidence_receipt_sha256
                ),
                world_execution_receipt_sha256=(
                    execution_receipt.authority_receipt_sha256
                ),
                world_observation_before_receipt_sha256=(
                    execution_receipt.before.authority_receipt_sha256
                ),
                world_observation_after_receipt_sha256=(
                    execution_receipt.after.authority_receipt_sha256
                ),
                source_time_start=source_time_start,
                source_time_end=source_time_end,
                visual_series_sha256=visual_commitment,
                somatic_series_sha256=somatic_commitment,
                acoustic_emission_receipt_sha256s=(
                    rendered.contributing_receipt_sha256s
                ),
                binaural_commitment=commitment,
                binaural_auditory_l5_authority_receipt_sha256=(
                    binaural_auditory_l5.authority_receipt_sha256
                ),
                causal_settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": payload,
                }),
            )
            try:
                receipt.verify(self._key)
            except BaseException:
                self._binaural_auditory_l5_owner.discard_prepared(
                    binaural_auditory_l5
                )
                self._causal_owner.discard_prepared(settlement)
                self._pending_reservation = None
                raise
            prior_epoch = _Epoch(
                expected_sequence=epoch.expected_sequence,
                next_source_sample_index=epoch.next_source_sample_index,
                prior_evidence_receipt_sha256=(
                    epoch.prior_evidence_receipt_sha256
                ),
                previous_after_observation_receipt_sha256=(
                    epoch.previous_after_observation_receipt_sha256
                ),
                left_pending_samples=epoch.left_pending_samples,
                right_pending_samples=epoch.right_pending_samples,
                left_pending_receipt_sha256s=(
                    epoch.left_pending_receipt_sha256s
                ),
                right_pending_receipt_sha256s=(
                    epoch.right_pending_receipt_sha256s
                ),
                path_commitment_sha256=epoch.path_commitment_sha256,
            )
            next_epoch = _Epoch(
                expected_sequence=epoch.expected_sequence + 1,
                next_source_sample_index=emission_receipt.source_sample_end,
                prior_evidence_receipt_sha256=(
                    receipt.authority_receipt_sha256
                ),
                previous_after_observation_receipt_sha256=(
                    execution_receipt.after.authority_receipt_sha256
                ),
                left_pending_samples=rendered.left_pending_samples,
                right_pending_samples=rendered.right_pending_samples,
                left_pending_receipt_sha256s=(
                    rendered.left_pending_receipt_sha256s
                ),
                right_pending_receipt_sha256s=(
                    rendered.right_pending_receipt_sha256s
                ),
                path_commitment_sha256=rendered.path_commitment_sha256,
            )
            result = W1PhysicalEvidenceMount(
                state=state,
                reason=reason,
                evidence_receipt=receipt,
                binaural_pcm=binaural,
                causal_settlement=settlement,
                binaural_auditory_l5=binaural_auditory_l5,
            )
            try:
                result.verify(self._key)
            except BaseException:
                self._binaural_auditory_l5_owner.discard_prepared(
                    binaural_auditory_l5
                )
                self._causal_owner.discard_prepared(settlement)
                self._pending_reservation = None
                raise
            self._prepared_mount = _PreparedAudiovisualMount(
                epoch_token=epoch_token,
                prior_epoch=prior_epoch,
                next_epoch=next_epoch,
                mount=result,
            )
            self._pending_reservation = None
            if commit:
                self._commit_prepared_multisensory_mount(result)
            return result

    def _prepared_for(
        self, mount: W1PhysicalEvidenceMount
    ) -> _PreparedAudiovisualMount:
        self.verify_mount(mount)
        prepared = self._prepared_mount
        if (
            prepared is None
            or mount.causal_settlement is None
            or prepared.mount.causal_settlement is None
            or mount.causal_settlement.authority_receipt_sha256
            != prepared.mount.causal_settlement.authority_receipt_sha256
        ):
            raise ValueError("W1 audiovisual prepared mount changed")
        return prepared

    def _commit_prepared_multisensory_mount(
        self,
        mount: W1PhysicalEvidenceMount,
        *,
        close_epoch: bool = False,
    ) -> None:
        if not isinstance(close_epoch, bool):
            raise TypeError("W1 audiovisual close-epoch flag must be boolean")
        prepared = self._prepared_for(mount)
        current = self._epochs.get(prepared.epoch_token)
        if current != prepared.prior_epoch:
            raise RuntimeError("W1 audiovisual epoch changed before commit")
        auditory_l5 = mount.binaural_auditory_l5
        if auditory_l5 is None:
            raise RuntimeError("W1 audiovisual commit lost binaural L5")
        try:
            undo = self._binaural_auditory_l5_owner.commit_prepared(
                auditory_l5
            )
        except BaseException:
            try:
                self._binaural_auditory_l5_owner.discard_prepared(
                    auditory_l5
                )
            except ValueError:
                pass
            self._causal_owner.discard_prepared(mount.causal_settlement)
            self._prepared_mount = None
            raise
        try:
            self._causal_owner.commit_prepared(mount.causal_settlement)
        except BaseException:
            self._binaural_auditory_l5_owner.rollback_committed(undo)
            try:
                self._causal_owner.discard_prepared(
                    mount.causal_settlement
                )
            except ValueError:
                pass
            self._prepared_mount = None
            raise
        self._epochs[prepared.epoch_token] = prepared.next_epoch
        if close_epoch:
            del self._epochs[prepared.epoch_token]
        self._prepared_mount = None

    def commit_prepared_multisensory_mount(
        self,
        mount: W1PhysicalEvidenceMount,
        *,
        close_epoch: bool = False,
    ) -> None:
        with self._lock:
            self._commit_prepared_multisensory_mount(
                mount,
                close_epoch=close_epoch,
            )

    def discard_prepared_multisensory_mount(
        self,
        mount: W1PhysicalEvidenceMount,
        *,
        close_epoch: bool = False,
    ) -> None:
        with self._lock:
            if not isinstance(close_epoch, bool):
                raise TypeError(
                    "W1 audiovisual close-epoch flag must be boolean"
                )
            prepared = self._prepared_for(mount)
            if self._epochs.get(prepared.epoch_token) != prepared.prior_epoch:
                raise RuntimeError(
                    "W1 audiovisual epoch changed before discard"
            )
            if mount.binaural_auditory_l5 is None:
                raise RuntimeError("W1 audiovisual discard lost binaural L5")
            self._binaural_auditory_l5_owner.discard_prepared(
                mount.binaural_auditory_l5
            )
            self._causal_owner.discard_prepared(mount.causal_settlement)
            if close_epoch:
                del self._epochs[prepared.epoch_token]
            self._prepared_mount = None

    def status(self) -> dict[str, object]:
        with self._lock:
            retained_delay_line_bytes = sum(
                (
                    len(epoch.left_pending_samples)
                    + len(epoch.right_pending_samples)
                ) * PCM_SAMPLE_WIDTH_BYTES
                for epoch in self._epochs.values()
            )
            retained_provenance_bytes = sum(
                64
                for epoch in self._epochs.values()
                for receipt in (
                    epoch.left_pending_receipt_sha256s
                    + epoch.right_pending_receipt_sha256s
                )
                if receipt is not None
            )
            prepared_binaural_bytes = (
                len(self._prepared_mount.mount.binaural_pcm.left_pcm_s16le)
                + len(
                    self._prepared_mount.mount.binaural_pcm.right_pcm_s16le
                )
                if (
                    self._prepared_mount is not None
                    and self._prepared_mount.mount.binaural_pcm is not None
                )
                else 0
            )
            prepared_pending_bytes = (
                (
                    len(self._prepared_mount.next_epoch.left_pending_samples)
                    + len(
                        self._prepared_mount.next_epoch.right_pending_samples
                    )
                ) * PCM_SAMPLE_WIDTH_BYTES
                if self._prepared_mount is not None else 0
            )
            prepared_provenance_bytes = (
                sum(
                    64
                    for receipt in (
                        self._prepared_mount.next_epoch
                        .left_pending_receipt_sha256s
                        + self._prepared_mount.next_epoch
                        .right_pending_receipt_sha256s
                    )
                    if receipt is not None
                )
                if self._prepared_mount is not None else 0
            )
            return {
                "active_epochs": len(self._epochs),
                "prepared_multisensory_mount": int(
                    self._prepared_mount is not None
                ),
                "pending_multisensory_reservation": int(
                    self._pending_reservation is not None
                ),
                "atomic_episode": int(self._atomic_episode is not None),
                "epoch_capacity": self._epoch_capacity,
                "max_pcm_samples_per_capture": MAX_EMITTED_PCM_SAMPLES,
                "max_propagation_delay_samples": (
                    MAX_PROPAGATION_DELAY_SAMPLES
                ),
                "max_retained_raw_media_bytes": (
                    self._epoch_capacity
                    * 2
                    * MAX_PROPAGATION_DELAY_SAMPLES
                    * PCM_SAMPLE_WIDTH_BYTES
                    + 2
                    * MAX_EMITTED_PCM_SAMPLES
                    * PCM_SAMPLE_WIDTH_BYTES
                    + 2
                    * MAX_PROPAGATION_DELAY_SAMPLES
                    * PCM_SAMPLE_WIDTH_BYTES
                ),
                "retained_raw_media_bytes": (
                    retained_delay_line_bytes
                    + prepared_binaural_bytes
                    + prepared_pending_bytes
                ),
                "max_retained_provenance_bytes": (
                    self._epoch_capacity
                    * 2
                    * MAX_PROPAGATION_DELAY_SAMPLES
                    * 64
                    + 2 * MAX_PROPAGATION_DELAY_SAMPLES * 64
                ),
                "retained_provenance_bytes": (
                    retained_provenance_bytes + prepared_provenance_bytes
                ),
                "retained_raw_media_kind": (
                    "bounded_transient_acoustic_delay_lines"
                ),
                "binaural_auditory_l5": (
                    self._binaural_auditory_l5_owner.status()
                ),
                "schema": "guala.w1.anonymous_multisensory_status.v3",
            }


__all__ = (
    "EVIDENCE_SCHEMA",
    "MAX_EMITTED_PCM_SAMPLES",
    "MIN_EMITTED_PCM_SAMPLES",
    "PCM_SAMPLE_RATE_HZ",
    "W1AudiovisualPhysicalEvidenceAuthority",
    "W1BinauralCalibration",
    "W1BinauralPCM",
    "W1EvidenceState",
    "W1PhysicalEvidenceMount",
    "W1PhysicalEvidenceReceipt",
)
