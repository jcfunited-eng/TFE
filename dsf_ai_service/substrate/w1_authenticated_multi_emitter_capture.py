"""Authenticated bounded two-emitter pressure coexistence in W1.

W1 vocal actions are executed serially by the world authority, but each action
contains an exact acoustic sample interval.  Two distinct external actors may
therefore commit pressure to the same interval.  This owner verifies each
emission while its world observation is current, derives only an anonymous
two-ear path that is also present in the anonymous visual geometry, and then
closes the interval as one physical binaural mixture.

Control port ids and body ids are used only to verify emission authority and
locate the physical emitter during transient rendering.  They do not enter the
structural capture payload, separated-source ordinal, DSF field, or perceptual
identity.  Anonymous spatial order and exact acoustic paths remain.

The admitted mixture is intentionally narrow:

* exactly two authenticated external emissions;
* one shared epoch, source interval, sample rate, and stable visual geometry;
* two genuine calibrated ears and two unique anonymous visual path matches;
* exact rational attenuation and integer-sample propagation delay;
* no clipping, rounding, saturation, tolerance, blind inference, or ML.

If the exact analog mixture is not integral PCM16, or exceeds PCM16 pressure,
the owner returns a typed indeterminate capture and releases no pressure.  A
captured mixture can be mounted through the complete binaural L0--L4 field and
passed to the exact path-conditioned separator.  Neither operation replaces
or compresses the explicit D_k, M_k, R_rev_k, U_star_k, C_k, P_k, and B_k
fields.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
import threading
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    MAX_EMITTED_PCM_SAMPLES,
    MIN_EMITTED_PCM_SAMPLES,
    PCM_SAMPLE_RATE_HZ,
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1BinauralCalibration,
    _anonymous_path_for_position,
    _public_visual_candidates,
    _visual_inputs,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_sound_field_inputs as _sound_inputs,
    body_from_snapshot as _body,
    calibrated_ear_positions as _ear_positions,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Experience,
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
    settle_w1_binaural_receptors,
)
from dsf_ai_service.substrate.w1_exact_binaural_source_separation import (
    ExactBinauralSourceSeparation,
    ExactBinauralTransferPath,
    MAX_PATH_DELAY_SAMPLES,
    separate_exact_binaural_sources,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
)


MULTI_EMITTER_CAPTURE_SCHEMA = (
    "guala.w1.authenticated_multi_emitter_binaural_capture.v1"
)
MULTI_EMITTER_CAPTURE_AUTHORITY_SCHEMA = (
    "guala.w1.authenticated_multi_emitter_binaural_capture.authority.v1"
)
MULTI_EMITTER_CAPTURE_DOMAIN = (
    b"guala-w1-authenticated-multi-emitter-binaural-capture-v1\0"
)
MULTI_EMITTER_COUNT = 2
PCM_MIN = -(1 << 15)
PCM_MAX = (1 << 15) - 1
MAX_MULTI_EMITTER_RETAINED_RAW_BYTES = (
    MULTI_EMITTER_COUNT * MAX_EMITTED_PCM_SAMPLES * 2
)


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
        raise ValueError(
            "multi-emitter capture key must be bytes or text"
        )
    if not 32 <= len(result) <= 4_096:
        raise ValueError(
            "multi-emitter capture key is outside its exact boundary"
        )
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _pcm_samples(value: bytes, name: str) -> tuple[int, ...]:
    if not isinstance(value, bytes) or len(value) % 2:
        raise ValueError(f"{name} must be signed little-endian PCM16")
    return tuple(item[0] for item in struct.iter_unpack("<h", value))


def _pcm_bytes(values: tuple[int, ...]) -> bytes:
    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or not PCM_MIN <= value <= PCM_MAX
        for value in values
    ):
        raise ValueError("multi-emitter pressure left calibrated PCM16")
    return struct.pack(f"<{len(values)}h", *values)


class W1MultiEmitterCaptureState(str, Enum):
    CAPTURED = "captured"
    INDETERMINATE_ADC_QUANTIZATION = (
        "indeterminate_adc_quantization"
    )
    INDETERMINATE_PRESSURE_RANGE = (
        "indeterminate_pressure_range"
    )


_STATE_REASON = {
    W1MultiEmitterCaptureState.CAPTURED: (
        "two_authenticated_anonymous_paths_coexisted_at_two_ears"
    ),
    W1MultiEmitterCaptureState.INDETERMINATE_ADC_QUANTIZATION: (
        "exact_analog_mixture_is_not_integral_pcm16"
    ),
    W1MultiEmitterCaptureState.INDETERMINATE_PRESSURE_RANGE: (
        "exact_binaural_mixture_exceeds_calibrated_pcm16"
    ),
}


@dataclass(frozen=True, slots=True)
class W1AuthenticatedMultiEmitterBinauralCapture:
    state: W1MultiEmitterCaptureState
    reason: str
    capture_id: str
    structural_fingerprint: str
    epoch_commitment_sha256: str
    source_sample_start: int
    source_sample_count: int
    capture_sample_count: int
    anonymous_visual_ordinals: tuple[int, ...]
    paths: tuple[ExactBinauralTransferPath, ...]
    visual_series_sha256: str
    upstream_emission_receipt_sha256s: tuple[str, ...]
    left_pcm_s16le: bytes
    right_pcm_s16le: bytes
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def structural_payload(self) -> dict[str, object]:
        return {
            "anonymous_visual_ordinals": list(
                self.anonymous_visual_ordinals
            ),
            "capture_sample_count": self.capture_sample_count,
            "left_pcm_sha256": (
                hashlib.sha256(self.left_pcm_s16le).hexdigest()
                if self.left_pcm_s16le else None
            ),
            "paths": [value.payload() for value in self.paths],
            "reason": self.reason,
            "right_pcm_sha256": (
                hashlib.sha256(self.right_pcm_s16le).hexdigest()
                if self.right_pcm_s16le else None
            ),
            "schema": MULTI_EMITTER_CAPTURE_SCHEMA,
            "source_sample_count": self.source_sample_count,
            "state": self.state.value,
            "visual_series_sha256": self.visual_series_sha256,
        }

    def authority_payload(self) -> dict[str, object]:
        return {
            "capture_id": self.capture_id,
            "epoch_commitment_sha256": self.epoch_commitment_sha256,
            "schema": MULTI_EMITTER_CAPTURE_AUTHORITY_SCHEMA,
            "source_sample_start": self.source_sample_start,
            "structural_fingerprint": self.structural_fingerprint,
            "upstream_emission_receipt_sha256s": list(
                self.upstream_emission_receipt_sha256s
            ),
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        if (
            not isinstance(self.state, W1MultiEmitterCaptureState)
            or self.reason != _STATE_REASON[self.state]
            or isinstance(self.source_sample_start, bool)
            or not isinstance(self.source_sample_start, int)
            or self.source_sample_start < 0
            or isinstance(self.source_sample_count, bool)
            or not isinstance(self.source_sample_count, int)
            or not MIN_EMITTED_PCM_SAMPLES
            <= self.source_sample_count
            <= MAX_EMITTED_PCM_SAMPLES
            or len(self.paths) != MULTI_EMITTER_COUNT
            or len(self.anonymous_visual_ordinals)
            != MULTI_EMITTER_COUNT
            or self.anonymous_visual_ordinals
            != tuple(sorted(set(self.anonymous_visual_ordinals)))
            or len(self.upstream_emission_receipt_sha256s)
            != MULTI_EMITTER_COUNT
            or len(set(self.upstream_emission_receipt_sha256s))
            != MULTI_EMITTER_COUNT
        ):
            raise ValueError("multi-emitter capture boundary changed")
        _sha256(
            self.epoch_commitment_sha256,
            "multi-emitter epoch",
        )
        _sha256(
            self.visual_series_sha256,
            "multi-emitter visual series",
        )
        for value in self.upstream_emission_receipt_sha256s:
            _sha256(value, "multi-emitter upstream emission")
        for value in self.paths:
            value.verify()
        expected_capture_count = self.source_sample_count + max(
            max(
                value.left_delay_samples,
                value.right_delay_samples,
            )
            for value in self.paths
        )
        if self.capture_sample_count != expected_capture_count:
            raise ValueError(
                "multi-emitter capture propagation tail changed"
            )
        if self.state is W1MultiEmitterCaptureState.CAPTURED:
            if (
                len(self.left_pcm_s16le) != self.capture_sample_count * 2
                or len(self.right_pcm_s16le)
                != self.capture_sample_count * 2
            ):
                raise ValueError(
                    "multi-emitter binaural pressure is incomplete"
                )
            _pcm_samples(self.left_pcm_s16le, "left multi-emitter pressure")
            _pcm_samples(
                self.right_pcm_s16le,
                "right multi-emitter pressure",
            )
        elif self.left_pcm_s16le or self.right_pcm_s16le:
            raise ValueError(
                "indeterminate multi-emitter capture released pressure"
            )
        structural = _digest(self.structural_payload())
        expected_capture_id = _digest({
            "multi_emitter_binaural_structure": structural,
        })
        if (
            self.structural_fingerprint != structural
            or self.capture_id != expected_capture_id
        ):
            raise ValueError(
                "multi-emitter structural authority changed"
            )
        authority_payload = self.authority_payload()
        expected_hmac = hmac.new(
            key,
            MULTI_EMITTER_CAPTURE_DOMAIN + _canonical(authority_payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": authority_payload,
            })
        ):
            raise ValueError(
                "multi-emitter capture authority changed"
            )

    def persistence_record(
        self,
        authority_key: bytes | str,
    ) -> dict[str, object]:
        """Return bounded authority without transient PCM."""

        self.verify(authority_key)
        return {
            **self.authority_payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "structural_payload": self.structural_payload(),
        }


@dataclass(frozen=True, slots=True)
class _VerifiedEmitterCause:
    anonymous_visual_ordinal: int
    path: ExactBinauralTransferPath
    visual_series_sha256: str
    emission_receipt_sha256: str
    emitter_port_id: str
    pcm_s16le: bytes


@dataclass(slots=True)
class _ActiveCapture:
    epoch_commitment_sha256: str
    source_sample_start: int
    source_sample_count: int
    causes: list[_VerifiedEmitterCause]


class W1AuthenticatedMultiEmitterCaptureOwner:
    """Serial owner of one bounded two-emitter W1 capture interval."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        acoustic_emitter: W1AcousticEmitterAuthority,
        calibration: W1BinauralCalibration | None = None,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "multi-emitter capture requires the W1 world authority"
            )
        if (
            not isinstance(acoustic_emitter, W1AcousticEmitterAuthority)
            or not acoustic_emitter.owns_world(world_authority)
        ):
            raise TypeError(
                "multi-emitter capture requires the world's acoustic emitter"
            )
        mounted_calibration = calibration or W1BinauralCalibration()
        mounted_calibration.verify()
        self._key = _key(authority_key)
        self._world = world_authority
        self._emitter = acoustic_emitter
        self._calibration = mounted_calibration
        self._lock = threading.RLock()
        self._active: _ActiveCapture | None = None
        self._captured = 0
        self._indeterminate = 0

    def open(
        self,
        *,
        epoch_token: str,
        source_sample_start: int,
        source_sample_count: int,
    ) -> None:
        if (
            not isinstance(epoch_token, str)
            or not epoch_token
            or len(epoch_token.encode("utf-8")) > 256
        ):
            raise ValueError(
                "multi-emitter capture epoch token is invalid"
            )
        if (
            isinstance(source_sample_start, bool)
            or not isinstance(source_sample_start, int)
            or source_sample_start < 0
            or isinstance(source_sample_count, bool)
            or not isinstance(source_sample_count, int)
            or not MIN_EMITTED_PCM_SAMPLES
            <= source_sample_count
            <= MAX_EMITTED_PCM_SAMPLES
        ):
            raise ValueError(
                "multi-emitter capture source interval is invalid"
            )
        epoch_commitment = hashlib.sha256(
            epoch_token.encode("utf-8")
        ).hexdigest()
        with self._lock:
            if self._active is not None:
                raise RuntimeError(
                    "multi-emitter capture requires close or abort"
                )
            self._active = _ActiveCapture(
                epoch_commitment_sha256=epoch_commitment,
                source_sample_start=source_sample_start,
                source_sample_count=source_sample_count,
                causes=[],
            )

    def admit(
        self,
        *,
        emission: AuthenticatedW1AcousticEmission,
        observation_snapshot: ObservationSnapshot,
        execution_receipt: ActionExecutionReceipt,
    ) -> None:
        """Verify one current emission before retaining its transient PCM."""

        self._emitter.verify_emission(
            emission,
            observation_snapshot=observation_snapshot,
            execution_receipt=execution_receipt,
        )
        with self._lock:
            active = self._active
            if active is None:
                raise RuntimeError(
                    "multi-emitter capture epoch is not open"
                )
            receipt = emission.receipt
            if (
                receipt.epoch_commitment_sha256
                != active.epoch_commitment_sha256
                or receipt.source_sample_start
                != active.source_sample_start
                or receipt.sample_count != active.source_sample_count
                or receipt.source_sample_end
                != active.source_sample_start + active.source_sample_count
            ):
                raise ValueError(
                    "multi-emitter cause left the shared source interval"
                )
            if len(active.causes) >= MULTI_EMITTER_COUNT:
                raise RuntimeError(
                    "multi-emitter capture cause capacity is full"
                )
            if any(
                value.emission_receipt_sha256
                == receipt.authority_receipt_sha256
                or value.emitter_port_id == receipt.emitter_port_id
                for value in active.causes
            ):
                raise ValueError(
                    "multi-emitter capture requires distinct causes"
                )
            self_body = _body(
                observation_snapshot,
                observation_snapshot.self_body_id,
            )
            ears = _ear_positions(
                self_body,
                self._calibration.ear_separation_mm,
            )
            if ears is None:
                raise ValueError(
                    "multi-emitter capture requires cardinal two-ear geometry"
                )
            emitter_body_id = execution_receipt.actor_body_id
            if (
                emitter_body_id is None
                or emitter_body_id == observation_snapshot.self_body_id
            ):
                raise ValueError(
                    "multi-emitter capture requires an external cause"
                )
            emitter_body = _body(
                observation_snapshot,
                emitter_body_id,
            )
            anonymous_path = _anonymous_path_for_position(
                emitter_body.pose.position,
                left_ear=ears[0],
                right_ear=ears[1],
                reference_distance_mm=(
                    self._calibration.reference_distance_mm
                ),
            )
            path = ExactBinauralTransferPath(
                left_delay_samples=anonymous_path.left_delay_samples,
                right_delay_samples=anonymous_path.right_delay_samples,
                left_attenuation=anonymous_path.left_attenuation,
                right_attenuation=anonymous_path.right_attenuation,
            )
            path.verify()
            if (
                path.left_delay_samples > MAX_PATH_DELAY_SAMPLES
                or path.right_delay_samples > MAX_PATH_DELAY_SAMPLES
            ):
                raise ValueError(
                    "multi-emitter acoustic path exceeds separator delay"
                )
            start = Fraction(
                active.source_sample_start,
                PCM_SAMPLE_RATE_HZ,
            )
            end = start + Fraction(
                active.source_sample_count,
                PCM_SAMPLE_RATE_HZ,
            )
            (
                _visual_substreams,
                visual_series_sha256,
                order_crossed,
                visual_candidates,
            ) = _visual_inputs(
                execution_receipt.before,
                execution_receipt.after,
                source_time_start=start,
                source_time_end=end,
            )
            public_candidates = _public_visual_candidates(
                visual_candidates,
                left_ear=ears[0],
                right_ear=ears[1],
                reference_distance_mm=(
                    self._calibration.reference_distance_mm
                ),
            )
            matches = tuple(
                value.ordinal
                for value in public_candidates
                if value.predicted_acoustic_path == anonymous_path
            )
            if order_crossed or len(matches) != 1:
                raise ValueError(
                    "multi-emitter cause has no unique anonymous visual path"
                )
            if active.causes and (
                active.causes[0].visual_series_sha256
                != visual_series_sha256
            ):
                raise ValueError(
                    "multi-emitter visual geometry changed inside interval"
                )
            if any(
                value.anonymous_visual_ordinal == matches[0]
                for value in active.causes
            ):
                raise ValueError(
                    "multi-emitter causes share one anonymous visual path"
                )
            prospective_raw = sum(
                len(value.pcm_s16le) for value in active.causes
            ) + len(emission.pcm_s16le)
            if prospective_raw > MAX_MULTI_EMITTER_RETAINED_RAW_BYTES:
                raise RuntimeError(
                    "multi-emitter raw pressure capacity is full"
                )
            active.causes.append(_VerifiedEmitterCause(
                anonymous_visual_ordinal=matches[0],
                path=path,
                visual_series_sha256=visual_series_sha256,
                emission_receipt_sha256=(
                    receipt.authority_receipt_sha256
                ),
                emitter_port_id=receipt.emitter_port_id,
                pcm_s16le=emission.pcm_s16le,
            ))

    def _capture_for(
        self,
        active: _ActiveCapture,
    ) -> W1AuthenticatedMultiEmitterBinauralCapture:
        if len(active.causes) != MULTI_EMITTER_COUNT:
            raise RuntimeError(
                "multi-emitter capture requires exactly two causes"
            )
        ordered = tuple(sorted(
            active.causes,
            key=lambda value: value.anonymous_visual_ordinal,
        ))
        paths = tuple(value.path for value in ordered)
        maximum_delay = max(
            max(
                value.left_delay_samples,
                value.right_delay_samples,
            )
            for value in paths
        )
        capture_sample_count = (
            active.source_sample_count + maximum_delay
        )
        sources = tuple(
            _pcm_samples(value.pcm_s16le, "multi-emitter cause")
            for value in ordered
        )
        analog_ears: list[tuple[Fraction, ...]] = []
        for ear_index in range(2):
            values: list[Fraction] = []
            for capture_index in range(capture_sample_count):
                pressure = Fraction(0)
                for source, path in zip(sources, paths, strict=True):
                    delay = (
                        path.left_delay_samples
                        if ear_index == 0 else path.right_delay_samples
                    )
                    attenuation = (
                        path.left_attenuation
                        if ear_index == 0 else path.right_attenuation
                    )
                    source_index = capture_index - delay
                    if 0 <= source_index < active.source_sample_count:
                        pressure += attenuation * source[source_index]
                values.append(pressure)
            analog_ears.append(tuple(values))
        if any(
            value.denominator != 1
            for ear in analog_ears
            for value in ear
        ):
            state = (
                W1MultiEmitterCaptureState
                .INDETERMINATE_ADC_QUANTIZATION
            )
            left_pcm = b""
            right_pcm = b""
        elif any(
            not PCM_MIN <= value.numerator <= PCM_MAX
            for ear in analog_ears
            for value in ear
        ):
            state = (
                W1MultiEmitterCaptureState
                .INDETERMINATE_PRESSURE_RANGE
            )
            left_pcm = b""
            right_pcm = b""
        else:
            state = W1MultiEmitterCaptureState.CAPTURED
            left_pcm = _pcm_bytes(tuple(
                value.numerator for value in analog_ears[0]
            ))
            right_pcm = _pcm_bytes(tuple(
                value.numerator for value in analog_ears[1]
            ))
        structural_payload = {
            "anonymous_visual_ordinals": [
                value.anonymous_visual_ordinal for value in ordered
            ],
            "capture_sample_count": capture_sample_count,
            "left_pcm_sha256": (
                hashlib.sha256(left_pcm).hexdigest()
                if left_pcm else None
            ),
            "paths": [value.payload() for value in paths],
            "reason": _STATE_REASON[state],
            "right_pcm_sha256": (
                hashlib.sha256(right_pcm).hexdigest()
                if right_pcm else None
            ),
            "schema": MULTI_EMITTER_CAPTURE_SCHEMA,
            "source_sample_count": active.source_sample_count,
            "state": state.value,
            "visual_series_sha256": ordered[0].visual_series_sha256,
        }
        structural_fingerprint = _digest(structural_payload)
        capture_id = _digest({
            "multi_emitter_binaural_structure": (
                structural_fingerprint
            ),
        })
        authority_payload = {
            "capture_id": capture_id,
            "epoch_commitment_sha256": (
                active.epoch_commitment_sha256
            ),
            "schema": MULTI_EMITTER_CAPTURE_AUTHORITY_SCHEMA,
            "source_sample_start": active.source_sample_start,
            "structural_fingerprint": structural_fingerprint,
            "upstream_emission_receipt_sha256s": [
                value.emission_receipt_sha256 for value in ordered
            ],
        }
        authority_hmac = hmac.new(
            self._key,
            MULTI_EMITTER_CAPTURE_DOMAIN + _canonical(authority_payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1AuthenticatedMultiEmitterBinauralCapture(
            state=state,
            reason=_STATE_REASON[state],
            capture_id=capture_id,
            structural_fingerprint=structural_fingerprint,
            epoch_commitment_sha256=active.epoch_commitment_sha256,
            source_sample_start=active.source_sample_start,
            source_sample_count=active.source_sample_count,
            capture_sample_count=capture_sample_count,
            anonymous_visual_ordinals=tuple(
                value.anonymous_visual_ordinal for value in ordered
            ),
            paths=paths,
            visual_series_sha256=ordered[0].visual_series_sha256,
            upstream_emission_receipt_sha256s=tuple(
                value.emission_receipt_sha256 for value in ordered
            ),
            left_pcm_s16le=left_pcm,
            right_pcm_s16le=right_pcm,
            authority_hmac_sha256=authority_hmac,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": authority_hmac,
                "payload": authority_payload,
            }),
        )
        result.verify(self._key)
        return result

    def close(self) -> W1AuthenticatedMultiEmitterBinauralCapture:
        with self._lock:
            active = self._active
            if active is None:
                raise RuntimeError(
                    "multi-emitter capture epoch is not open"
                )
            try:
                result = self._capture_for(active)
            finally:
                self._active = None
            if result.state is W1MultiEmitterCaptureState.CAPTURED:
                self._captured += 1
            else:
                self._indeterminate += 1
            return result

    def abort(self) -> bool:
        with self._lock:
            existed = self._active is not None
            self._active = None
            return existed

    def status(self) -> dict[str, object]:
        with self._lock:
            retained = (
                sum(
                    len(value.pcm_s16le)
                    for value in self._active.causes
                )
                if self._active is not None else 0
            )
            return {
                "active": self._active is not None,
                "admitted_causes": (
                    len(self._active.causes)
                    if self._active is not None else 0
                ),
                "captured": self._captured,
                "indeterminate": self._indeterminate,
                "max_causes": MULTI_EMITTER_COUNT,
                "max_retained_raw_media_bytes": (
                    MAX_MULTI_EMITTER_RETAINED_RAW_BYTES
                ),
                "retained_raw_media_bytes": retained,
                "schema": (
                    "guala.w1.authenticated_multi_emitter_capture_status.v1"
                ),
            }


def separate_authenticated_multi_emitter_capture(
    capture: W1AuthenticatedMultiEmitterBinauralCapture,
    *,
    authority_key: bytes | str,
) -> ExactBinauralSourceSeparation:
    capture.verify(authority_key)
    if capture.state is not W1MultiEmitterCaptureState.CAPTURED:
        raise ValueError(
            "indeterminate multi-emitter pressure cannot be separated"
        )
    return separate_exact_binaural_sources(
        left_pcm_s16le=capture.left_pcm_s16le,
        right_pcm_s16le=capture.right_pcm_s16le,
        paths=capture.paths,
        source_sample_count=capture.source_sample_count,
    )


def mount_authenticated_multi_emitter_binaural_hearing(
    capture: W1AuthenticatedMultiEmitterBinauralCapture,
    *,
    authority_key: bytes | str,
) -> W1BinauralReceptorSettlement:
    """Mount two-ear L0--L4, L5, and raw-pressure receptor settlement."""

    capture.verify(authority_key)
    if capture.state is not W1MultiEmitterCaptureState.CAPTURED:
        raise ValueError(
            "indeterminate multi-emitter pressure cannot enter auditory L5"
        )
    source_time_start = Fraction(
        capture.source_sample_start,
        PCM_SAMPLE_RATE_HZ,
    )
    padded_sample_count = (
        (
            capture.capture_sample_count
            + OBSERVATION_HOP_SAMPLES
            - 1
        )
        // OBSERVATION_HOP_SAMPLES
        * OBSERVATION_HOP_SAMPLES
    )
    padding_bytes = b"\0\0" * (
        padded_sample_count - capture.capture_sample_count
    )
    source_time_end = source_time_start + Fraction(
        padded_sample_count,
        PCM_SAMPLE_RATE_HZ,
    )
    left = _sound_inputs(
        ear="left",
        topology_index=0,
        pcm=capture.left_pcm_s16le + padding_bytes,
        source_time_start=source_time_start,
    )
    right = _sound_inputs(
        ear="right",
        topology_index=len(left),
        pcm=capture.right_pcm_s16le + padding_bytes,
        source_time_start=source_time_start,
    )
    built = build_six_sense_full_field(
        assembly_id=f"w1-multi-{capture.capture_id[:32]}",
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        observed_substreams={
            PhysicalSense.SOUND: (*left, *right),
        },
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    causal = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )
    owner = W1BinauralAuditoryL5Owner(max_transitions=1)
    experience = owner.prepare(causal)
    owner.commit_prepared(experience)
    experience.verify()
    return settle_w1_binaural_receptors(
        left_custody=left,
        right_custody=right,
        causal_settlement=causal,
        w1_l5=experience,
    )


def mount_authenticated_multi_emitter_binaural_l5(
    capture: W1AuthenticatedMultiEmitterBinauralCapture,
    *,
    authority_key: bytes | str,
) -> W1BinauralAuditoryL5Experience:
    """Compatibility surface returning the full-field W1 L5 authority."""

    return mount_authenticated_multi_emitter_binaural_hearing(
        capture,
        authority_key=authority_key,
    ).upstream_w1_l5


__all__ = [
    "MAX_MULTI_EMITTER_RETAINED_RAW_BYTES",
    "MULTI_EMITTER_CAPTURE_SCHEMA",
    "MULTI_EMITTER_COUNT",
    "W1AuthenticatedMultiEmitterBinauralCapture",
    "W1AuthenticatedMultiEmitterCaptureOwner",
    "W1MultiEmitterCaptureState",
    "mount_authenticated_multi_emitter_binaural_l5",
    "mount_authenticated_multi_emitter_binaural_hearing",
    "separate_authenticated_multi_emitter_capture",
]
