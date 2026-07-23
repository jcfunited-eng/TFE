"""Bounded anonymous audiovisual physics for consecutive W1 observations.

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

Both senses enter the canonical native six-sense builder, so frozen L0--L4
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

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
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
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    MAX_EMITTED_PCM_SAMPLES,
    MIN_EMITTED_PCM_SAMPLES,
    PCM_SAMPLE_RATE_HZ,
    W1AcousticEmitterAuthority,
)


EVIDENCE_SCHEMA = "guala.w1.anonymous_audiovisual_evidence.v2"
PERSISTENCE_SCHEMA = "guala.w1.anonymous_audiovisual_persistence.v2"
AUTHORITY_DOMAIN = b"guala-w1-anonymous-audiovisual-evidence-v2\0"

PCM_SAMPLE_WIDTH_BYTES = 2
SPEED_OF_SOUND_MM_PER_SECOND = 343_000
MAX_PROPAGATION_DELAY_SAMPLES = MAX_EMITTED_PCM_SAMPLES

_VISUAL_AXES = ("relative-x", "relative-y", "relative-z", "apparent-radius")
_CARDINAL_HEADINGS = (0, 90_000, 180_000, 270_000)


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
) -> tuple[bytes, tuple[int, ...], int, Fraction]:
    distance_squared = _distance_squared(source, ear)
    delay = _delay_samples(distance_squared)
    reference_squared = reference_distance_mm**2
    attenuation = Fraction(
        reference_squared,
        max(reference_squared, distance_squared),
    )
    if pending_samples and len(pending_samples) != delay:
        raise ValueError("W1 acoustic propagation path changed inside epoch")
    pending = pending_samples or (0,) * delay
    continuous = pending + tuple(
        _scaled_sample(sample, attenuation) for sample in samples
    )
    rendered = continuous[:len(samples)]
    next_pending = continuous[len(samples):]
    if len(next_pending) != delay:
        raise RuntimeError("W1 acoustic delay line cardinality changed")
    return _pcm_bytes(rendered), next_pending, delay, attenuation


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
    control_body_id: str
    values: tuple[Fraction, Fraction, Fraction, Fraction]

    @property
    def anonymous_order_key(self) -> tuple[Fraction, ...]:
        return self.values


def _anonymous_detections(
    snapshot: ObservationSnapshot,
) -> tuple[_AnonymousDetection, ...]:
    self_body = _body(snapshot, snapshot.self_body_id)
    origin = self_body.pose.position
    span_x, span_y, span_z, planar_span = _global_spans(snapshot)
    scale_x = _binary_scale(span_x)
    scale_y = _binary_scale(span_y)
    scale_z = _binary_scale(span_z)
    planar_scale = _binary_scale(planar_span)
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
            control_body_id=body.body_id,
            values=(
                Fraction(position.x - origin.x, scale_x),
                Fraction(position.y - origin.y, scale_y),
                Fraction(position.z - origin.z, scale_z),
                Fraction(body.radius_mm, planar_scale),
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
    if not first or not second or len(first) != len(second):
        return (), _digest({"before": (), "after": ()}), False
    order_crossed = tuple(
        item.control_body_id for item in first
    ) != tuple(item.control_body_id for item in second)
    witness = []
    inputs = []
    for ordinal, (left, right) in enumerate(
        zip(first, second, strict=True)
    ):
        for axis_index, axis in enumerate(_VISUAL_AXES):
            exact_values = (left.values[axis_index], right.values[axis_index])
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
                physical_quantity="normalized-visual-body-geometry",
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
    }), order_crossed


def _sound_input(
    *,
    ear: str,
    topology_index: int,
    pcm: bytes,
    source_time_start: Fraction,
) -> NativeSensorySubstreamInput:
    samples = _signed_pcm_samples(pcm)
    count = len(samples)
    source_times = tuple(
        source_time_start + Fraction(index + 1, PCM_SAMPLE_RATE_HZ)
        for index in range(count)
    )
    return NativeSensorySubstreamInput(
        sense=PhysicalSense.SOUND,
        sensor_id=f"W1-calibrated-{ear}-ear",
        substream_id=f"binaural-{ear}-pressure",
        topology_index=topology_index,
        coordinates=(
            NativeAxisCoordinate("acoustic-receptor", ear),
            NativeAxisCoordinate("sample-rate-hz", str(PCM_SAMPLE_RATE_HZ)),
        ),
        physical_quantity="acoustic-pressure",
        physical_unit="signed-pcm16-full-scale",
        source_times=source_times,
        normalized_signal=tuple(
            _exact_binary_float(Fraction(item, 32_768)) for item in samples
        ),
        phase_turns=tuple(Fraction(0) for _sample in samples),
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
    source_time_start: Fraction
    source_time_end: Fraction
    visual_series_sha256: str
    acoustic_emission_receipt_sha256: str
    binaural_commitment: Mapping[str, object]
    causal_settlement_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "acoustic_emission_receipt_sha256": (
                self.acoustic_emission_receipt_sha256
            ),
            "binaural_commitment": dict(self.binaural_commitment),
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
            "visual_series_sha256": self.visual_series_sha256,
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
        _sha256(self.visual_series_sha256, "W1 visual series")
        _sha256(
            self.acoustic_emission_receipt_sha256,
            "W1 authenticated acoustic emission",
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
            return
        self.evidence_receipt.verify(authority_key)
        if self.binaural_pcm is None or self.causal_settlement is None:
            raise ValueError("settled W1 evidence is incomplete")
        self.binaural_pcm.verify()
        self.causal_settlement.verify()
        if (
            self.binaural_pcm.commitment_record()
            != dict(self.evidence_receipt.binaural_commitment)
            or self.causal_settlement.authority_receipt_sha256
            != self.evidence_receipt.causal_settlement_receipt_sha256
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


@dataclass(slots=True)
class _Epoch:
    expected_sequence: int = 0
    next_source_sample_index: int = 0
    prior_evidence_receipt_sha256: str | None = None
    previous_after_observation_receipt_sha256: str | None = None
    left_pending_samples: tuple[int, ...] = ()
    right_pending_samples: tuple[int, ...] = ()


class W1AudiovisualPhysicalEvidenceAuthority:
    """Transient bounded owner of anonymous W1 audiovisual captures."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        causal_owner: ExactCausalExperienceOwner,
        acoustic_emitter: W1AcousticEmitterAuthority,
        calibration: W1BinauralCalibration | None = None,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 evidence requires the world authority")
        if not isinstance(causal_owner, ExactCausalExperienceOwner):
            raise TypeError("W1 evidence requires an exact causal owner")
        if not isinstance(acoustic_emitter, W1AcousticEmitterAuthority):
            raise TypeError("W1 evidence requires the acoustic emitter authority")
        if not acoustic_emitter.owns_world(world_authority):
            raise ValueError("W1 acoustic emitter belongs to another world")
        self._key = _key(authority_key)
        self._world = world_authority
        self._causal_owner = causal_owner
        self._acoustic_emitter = acoustic_emitter
        self._calibration = calibration or W1BinauralCalibration()
        self._calibration.verify()
        self._epoch_capacity = len(world_authority.actor_ports)
        self._epochs: dict[str, _Epoch] = {}
        self._lock = threading.RLock()

    def open_epoch(self) -> str:
        with self._lock:
            if len(self._epochs) >= self._epoch_capacity:
                raise RuntimeError("W1 audiovisual epoch capacity is full")
            while True:
                token = secrets.token_urlsafe(24)
                if token not in self._epochs:
                    self._epochs[token] = _Epoch()
                    return token

    def close_epoch(self, epoch_token: str) -> bool:
        with self._lock:
            return self._epochs.pop(epoch_token, None) is not None

    def emit_acoustic_pressure(
        self,
        *,
        epoch_token: str,
        sequence: int,
        source_sample_start: int,
        execution_receipt: ActionExecutionReceipt,
        emitter_port_id: str,
        pcm_s16le: bytes,
    ) -> AuthenticatedW1AcousticEmission:
        """Execute the authenticated transient W1 emitter transaction."""
        return self._acoustic_emitter.emit(
            epoch_token=epoch_token,
            sequence=sequence,
            source_sample_start=source_sample_start,
            execution_receipt=execution_receipt,
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

    def _binaural(
        self,
        *,
        execution: ActionExecutionReceipt,
        emitter_port_id: str,
        emitted_samples: tuple[int, ...],
        left_pending_samples: tuple[int, ...],
        right_pending_samples: tuple[int, ...],
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
        before_self = _body(execution.before, execution.before.self_body_id)
        after_self = _body(execution.after, execution.after.self_body_id)
        before_emitter = _body(execution.before, emitter_body_id)
        after_emitter = _body(execution.after, emitter_body_id)
        if before_self.pose != after_self.pose:
            return self._unsettled(
                W1EvidenceState.UNAVAILABLE,
                "moving_receptor_calibration_is_unavailable",
            )
        if before_emitter.pose.position != after_emitter.pose.position:
            return self._unsettled(
                W1EvidenceState.UNAVAILABLE,
                "timed_moving_emitter_path_is_unavailable",
            )
        if not (
            _is_visible(
                execution.before,
                before_self.pose.position,
                before_emitter.pose.position,
                before_emitter.radius_mm,
            )
            and _is_visible(
                execution.after,
                after_self.pose.position,
                after_emitter.pose.position,
                after_emitter.radius_mm,
            )
        ):
            return self._unsettled(
                W1EvidenceState.UNKNOWN,
                "acoustic_emitter_is_not_contemporaneously_visible",
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
        prospective_left_delay = _delay_samples(
            _distance_squared(after_emitter.pose.position, left)
        )
        prospective_right_delay = _delay_samples(
            _distance_squared(after_emitter.pose.position, right)
        )
        if (
            prospective_left_delay > MAX_PROPAGATION_DELAY_SAMPLES
            or prospective_right_delay > MAX_PROPAGATION_DELAY_SAMPLES
        ):
            return self._unsettled(
                W1EvidenceState.UNAVAILABLE,
                "acoustic_path_exceeds_bounded_delay_line",
            )
        (
            left_pcm,
            next_left_pending,
            left_delay,
            left_attenuation,
        ) = _render_ear(
            emitted_samples,
            source=after_emitter.pose.position,
            ear=left,
            reference_distance_mm=self._calibration.reference_distance_mm,
            pending_samples=left_pending_samples,
        )
        (
            right_pcm,
            next_right_pending,
            right_delay,
            right_attenuation,
        ) = _render_ear(
            emitted_samples,
            source=after_emitter.pose.position,
            ear=right,
            reference_distance_mm=self._calibration.reference_distance_mm,
            pending_samples=right_pending_samples,
        )
        if (
            left_delay != prospective_left_delay
            or right_delay != prospective_right_delay
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
        )

    def mount(
        self,
        *,
        epoch_token: str,
        sequence: int,
        execution_receipt: ActionExecutionReceipt,
        acoustic_emission: AuthenticatedW1AcousticEmission,
    ) -> W1PhysicalEvidenceMount:
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
        emission_sha256 = hashlib.sha256(emitted_pcm_s16le).hexdigest()
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
                left_pending_samples=epoch.left_pending_samples,
                right_pending_samples=epoch.right_pending_samples,
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
            if not visual_inputs:
                del self._epochs[epoch_token]
                return self._unsettled(
                    W1EvidenceState.UNKNOWN,
                    "anonymous_visual_series_is_incomplete",
                )
            left_sound = _sound_input(
                ear="left",
                topology_index=0,
                pcm=binaural.left_pcm_s16le,
                source_time_start=source_time_start,
            )
            right_sound = _sound_input(
                ear="right",
                topology_index=1,
                pcm=binaural.right_pcm_s16le,
                source_time_start=source_time_start,
            )
            sound_inputs = (left_sound, right_sound)
            states = {
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense in (PhysicalSense.SIGHT, PhysicalSense.SOUND)
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            }
            assembly_id = "w1-anonymous-av-" + _digest({
                "acoustic_emission_receipt_sha256": (
                    emission_receipt.authority_receipt_sha256
                ),
                "emission_sha256": emission_sha256,
                "execution_receipt_sha256": (
                    execution_receipt.authority_receipt_sha256
                ),
                "prior_evidence_receipt_sha256": (
                    epoch.prior_evidence_receipt_sha256
                ),
                "sequence": sequence,
                "visual_series_sha256": visual_commitment,
            })
            built = build_six_sense_full_field(
                assembly_id=assembly_id,
                source_time_start=source_time_start,
                source_time_end=source_time_end,
                observed_substreams={
                    PhysicalSense.SIGHT: visual_inputs,
                    PhysicalSense.SOUND: sound_inputs,
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
            state = (
                W1EvidenceState.UNKNOWN
                if not (
                    any(_signed_pcm_samples(binaural.left_pcm_s16le))
                    or any(_signed_pcm_samples(binaural.right_pcm_s16le))
                )
                else W1EvidenceState.AMBIGUOUS
                if (
                    visual_order_crossed
                    or binaural.left_pcm_s16le == binaural.right_pcm_s16le
                )
                else W1EvidenceState.OBSERVED
            )
            reason = {
                W1EvidenceState.UNKNOWN: "received_pressure_is_silent",
                W1EvidenceState.AMBIGUOUS: (
                    "anonymous_visual_order_crossed"
                    if visual_order_crossed
                    else "two_ear_field_is_spatially_symmetric"
                ),
                W1EvidenceState.OBSERVED: (
                    "anonymous_spatial_audiovisual_evidence_observed"
                ),
            }[state]
            commitment = binaural.commitment_record()
            payload = {
                "acoustic_emission_receipt_sha256": (
                    emission_receipt.authority_receipt_sha256
                ),
                "binaural_commitment": commitment,
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
                "visual_series_sha256": visual_commitment,
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
                source_time_start=source_time_start,
                source_time_end=source_time_end,
                visual_series_sha256=visual_commitment,
                acoustic_emission_receipt_sha256=(
                    emission_receipt.authority_receipt_sha256
                ),
                binaural_commitment=commitment,
                causal_settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": payload,
                }),
            )
            receipt.verify(self._key)
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
            )
            epoch.expected_sequence += 1
            epoch.next_source_sample_index = emission_receipt.source_sample_end
            epoch.left_pending_samples = rendered.left_pending_samples
            epoch.right_pending_samples = rendered.right_pending_samples
            epoch.prior_evidence_receipt_sha256 = (
                receipt.authority_receipt_sha256
            )
            epoch.previous_after_observation_receipt_sha256 = (
                execution_receipt.after.authority_receipt_sha256
            )
            try:
                self._causal_owner.commit_prepared(settlement)
            except BaseException:
                self._epochs[epoch_token] = prior_epoch
                try:
                    self._causal_owner.discard_prepared(settlement)
                except ValueError:
                    pass
                raise
            result = W1PhysicalEvidenceMount(
                state=state,
                reason=reason,
                evidence_receipt=receipt,
                binaural_pcm=binaural,
                causal_settlement=settlement,
            )
            result.verify(self._key)
            return result

    def status(self) -> dict[str, object]:
        with self._lock:
            retained_delay_line_bytes = sum(
                (
                    len(epoch.left_pending_samples)
                    + len(epoch.right_pending_samples)
                ) * PCM_SAMPLE_WIDTH_BYTES
                for epoch in self._epochs.values()
            )
            return {
                "active_epochs": len(self._epochs),
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
                ),
                "retained_raw_media_bytes": retained_delay_line_bytes,
                "retained_raw_media_kind": (
                    "bounded_transient_acoustic_delay_lines"
                ),
                "schema": "guala.w1.anonymous_audiovisual_status.v1",
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
