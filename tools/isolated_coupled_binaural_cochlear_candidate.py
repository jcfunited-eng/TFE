"""Isolated bounded coupled-binaural cochlear receptor candidate.

This module is an audit candidate, not a production auditory provider.  It
receives only physical mono PCM.  Because the Speech Commands corpus contains
no measured interaural delay or gain, both calibrated ears receive the same
pressure; no synthetic spatial cue is invented.

Each ear contains the canonical sixteen ERB resonators.  Immediate cochlear
neighbors are coupled synchronously through a passive convex recurrence:
one source/stage input plus every adjacent prior resonator state, divided by
the exact number of contributors.  The denominator is therefore derived from
topology degree, not fitted.

Four receptor streams are retained for every ear and cochlear place:

* RMS pressure envelope;
* carrier phase-lock orientation;
* exact positive envelope displacement (onset);
* exact negative envelope displacement (offset).

All streams are mounted independently into the existing native L0--L4
boundary.  No label, transcript, filename, word window, q identity, Krimelack
state, score, tolerance, or learned parameter is accepted.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    PAIRED_SOURCE_RELEVANCE_RULE,
    SIGNED_UNIT_KERNEL_INPUT_MAP,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
)
from dsf_ai_service.substrate.auditory_pressure_kernel_input import (
    AUDITORY_PRESSURE_KERNEL_INPUT_MAP,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    COCHLEAR_ORDER,
    MAX_CAPTURE_SECONDS,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)


CANDIDATE_SCHEMA = "guala.audit.coupled_binaural_cochlea.capture.v1"
TOPOLOGY_SCHEMA = "guala.audit.coupled_binaural_cochlea.topology.v1"
MOUNT_SCHEMA = "guala.audit.coupled_binaural_cochlea.mount.v1"
EAR_IDS = ("left", "right")
RECEPTOR_KINDS = ("envelope", "phase_lock", "onset", "offset")
COMPONENT_COUNT = (
    len(EAR_IDS) * COCHLEAR_CHANNEL_COUNT * len(RECEPTOR_KINDS)
)
COMPONENTS_PER_EAR = COCHLEAR_CHANNEL_COUNT * len(RECEPTOR_KINDS)
MAX_FRAME_COUNT = (
    MAX_CAPTURE_SECONDS
    * REQUIRED_SAMPLE_RATE_HZ
    // OBSERVATION_HOP_SAMPLES
)
_CAPTURE_DOMAIN = b"guala-isolated-coupled-binaural-capture-v1\0"
_TOPOLOGY_DOMAIN = b"guala-isolated-coupled-binaural-topology-v1\0"
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    result = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(result, bytes) or not 32 <= len(result) <= 4_096:
        raise ValueError("coupled binaural candidate key boundary changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _float_hex(values: tuple[float, ...]) -> list[str]:
    return [value.hex() for value in values]


def _finite_unit(value: object, name: str, *, signed: bool) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} is not finite binary64")
    result = float(value)
    lower = -1.0 if signed else 0.0
    if not math.isfinite(result) or not lower <= result <= 1.0:
        raise ValueError(f"{name} left its analytic unit bound")
    return result


@dataclass(frozen=True, slots=True)
class CoupledBinauralTopology:
    vertex_ids: tuple[str, ...]
    neighbor_edges: tuple[tuple[str, str], ...]
    interaural_edges: tuple[tuple[str, str], ...]
    calibration_receipt_sha256s: tuple[str, str]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "calibration_receipt_sha256s": list(
                self.calibration_receipt_sha256s
            ),
            "interaural_edges": [
                list(value) for value in self.interaural_edges
            ],
            "neighbor_edges": [
                list(value) for value in self.neighbor_edges
            ],
            "schema": TOPOLOGY_SCHEMA,
            "vertex_ids": list(self.vertex_ids),
        }


@dataclass(frozen=True, slots=True)
class CoupledCochlearReceptorField:
    ear_id: str
    cochlear_index: int
    centre_hz: float
    erb_width_hz: float
    causal_offsets_samples: tuple[int, ...]
    envelope: tuple[float, ...]
    phase_lock: tuple[float, ...]
    onset: tuple[float, ...]
    offset: tuple[float, ...]
    cumulative_phase_turns: tuple[float, ...]

    def verify(self) -> None:
        count = len(self.causal_offsets_samples)
        if (
            self.ear_id not in EAR_IDS
            or isinstance(self.cochlear_index, bool)
            or not 0 <= self.cochlear_index < COCHLEAR_CHANNEL_COUNT
            or not 1 <= count <= MAX_FRAME_COUNT
            or any(
                right <= left
                for left, right in zip(
                    self.causal_offsets_samples,
                    self.causal_offsets_samples[1:],
                )
            )
            or not (
                count
                == len(self.envelope)
                == len(self.phase_lock)
                == len(self.onset)
                == len(self.offset)
                == len(self.cumulative_phase_turns)
            )
        ):
            raise ValueError("coupled cochlear receptor topology changed")
        expected = AUDITORY_CHANNELS[self.cochlear_index]
        if (
            self.centre_hz != expected.centre_hz
            or self.erb_width_hz != expected.erb_width_hz
        ):
            raise ValueError("coupled cochlear ERB calibration changed")
        for index in range(count):
            envelope = _finite_unit(
                self.envelope[index],
                "coupled cochlear envelope",
                signed=False,
            )
            onset = _finite_unit(
                self.onset[index],
                "coupled cochlear onset",
                signed=False,
            )
            offset = _finite_unit(
                self.offset[index],
                "coupled cochlear offset",
                signed=False,
            )
            _finite_unit(
                self.phase_lock[index],
                "coupled cochlear phase lock",
                signed=True,
            )
            if index == 0:
                if onset != envelope or offset != 0.0:
                    raise ValueError(
                        "coupled cochlear genesis displacement changed"
                    )
            else:
                displacement = envelope - self.envelope[index - 1]
                if (
                    onset != max(displacement, 0.0)
                    or offset != max(-displacement, 0.0)
                ):
                    raise ValueError(
                        "coupled cochlear onset/offset changed"
                    )
            if not math.isfinite(self.cumulative_phase_turns[index]):
                raise ValueError(
                    "coupled cochlear cumulative phase is not finite"
                )


@dataclass(frozen=True, slots=True)
class CoupledBinauralCapture:
    source_sample_rate_hz: int
    input_sample_count: int
    observation_hop_samples: int
    fields: tuple[CoupledCochlearReceptorField, ...]
    topology_receipt_sha256: str
    pcm_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def frame_count(self) -> int:
        return len(self.fields[0].causal_offsets_samples)

    def payload(self) -> dict[str, object]:
        return {
            "fields": [
                {
                    "causal_offsets_samples": list(
                        value.causal_offsets_samples
                    ),
                    "centre_hz": value.centre_hz.hex(),
                    "cochlear_index": value.cochlear_index,
                    "cumulative_phase_turns": _float_hex(
                        value.cumulative_phase_turns
                    ),
                    "ear_id": value.ear_id,
                    "envelope": _float_hex(value.envelope),
                    "erb_width_hz": value.erb_width_hz.hex(),
                    "offset": _float_hex(value.offset),
                    "onset": _float_hex(value.onset),
                    "phase_lock": _float_hex(value.phase_lock),
                }
                for value in self.fields
            ],
            "input_sample_count": self.input_sample_count,
            "observation_hop_samples": self.observation_hop_samples,
            "pcm_sha256": self.pcm_sha256,
            "schema": CANDIDATE_SCHEMA,
            "source_sample_rate_hz": self.source_sample_rate_hz,
            "topology_receipt_sha256": self.topology_receipt_sha256,
        }


class CoupledBinauralCochlearAuthority:
    """Stateless bounded authority for isolated candidate captures."""

    def __init__(self, *, authority_key: bytes | str) -> None:
        root = hashlib.sha256(_key(authority_key)).digest()
        self._capture_key = hashlib.sha256(
            _CAPTURE_DOMAIN + root
        ).digest()
        self._topology_key = hashlib.sha256(
            _TOPOLOGY_DOMAIN + root
        ).digest()
        self._topology = self._build_topology()

    @property
    def topology(self) -> CoupledBinauralTopology:
        return self._topology

    @staticmethod
    def _vertex(ear_id: str, cochlear_index: int) -> str:
        return f"{ear_id}:erb_{cochlear_index:02d}"

    def _build_topology(self) -> CoupledBinauralTopology:
        vertices = tuple(
            self._vertex(ear_id, index)
            for ear_id in EAR_IDS
            for index in range(COCHLEAR_CHANNEL_COUNT)
        )
        neighbors = tuple(
            (
                self._vertex(ear_id, index),
                self._vertex(ear_id, index + 1),
            )
            for ear_id in EAR_IDS
            for index in range(COCHLEAR_CHANNEL_COUNT - 1)
        )
        interaural = tuple(
            (
                self._vertex(EAR_IDS[0], index),
                self._vertex(EAR_IDS[1], index),
            )
            for index in range(COCHLEAR_CHANNEL_COUNT)
        )
        calibrations = tuple(
            _digest({
                "ear_id": ear_id,
                "gain": "1/1",
                "sample_delay": "0/1",
                "schema": (
                    "guala.audit.coupled_binaural_ear_calibration.v1"
                ),
            })
            for ear_id in EAR_IDS
        )
        provisional = CoupledBinauralTopology(
            vertex_ids=vertices,
            neighbor_edges=neighbors,
            interaural_edges=interaural,
            calibration_receipt_sha256s=calibrations,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._topology_key,
            _TOPOLOGY_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = CoupledBinauralTopology(
            vertex_ids=vertices,
            neighbor_edges=neighbors,
            interaural_edges=interaural,
            calibration_receipt_sha256s=calibrations,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify_topology(result)
        return result

    def verify_topology(self, topology: CoupledBinauralTopology) -> None:
        if (
            not isinstance(topology, CoupledBinauralTopology)
            or len(topology.vertex_ids)
            != len(EAR_IDS) * COCHLEAR_CHANNEL_COUNT
            or len(set(topology.vertex_ids)) != len(topology.vertex_ids)
            or len(topology.neighbor_edges)
            != len(EAR_IDS) * (COCHLEAR_CHANNEL_COUNT - 1)
            or len(topology.interaural_edges) != COCHLEAR_CHANNEL_COUNT
            or any(
                endpoint not in topology.vertex_ids
                for edge in (
                    *topology.neighbor_edges,
                    *topology.interaural_edges,
                )
                for endpoint in edge
            )
        ):
            raise ValueError("coupled binaural topology changed")
        for value in (
            *topology.calibration_receipt_sha256s,
            topology.authority_hmac_sha256,
            topology.authority_receipt_sha256,
        ):
            _sha256(value, "coupled binaural topology authority")
        payload = topology.payload()
        signature = hmac.new(
            self._topology_key,
            _TOPOLOGY_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature, topology.authority_hmac_sha256
            )
            or topology.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("coupled binaural topology authority changed")

    @staticmethod
    def _coefficients() -> tuple[np.ndarray, np.ndarray]:
        centres = np.asarray(
            [value.centre_hz for value in AUDITORY_CHANNELS],
            dtype=np.float64,
        )
        widths = np.asarray(
            [value.erb_width_hz for value in AUDITORY_CHANNELS],
            dtype=np.float64,
        )
        radius = np.exp(
            -2.0
            * math.pi
            * 1.019
            * widths
            / REQUIRED_SAMPLE_RATE_HZ
        )
        poles = radius * np.exp(
            2.0j * math.pi * centres / REQUIRED_SAMPLE_RATE_HZ
        )
        return poles, 1.0 - radius

    @staticmethod
    def _neighbor_average(
        stage_input: np.ndarray,
        prior_state: np.ndarray,
    ) -> np.ndarray:
        result = np.empty_like(stage_input)
        result[:, 0] = (
            stage_input[:, 0] + prior_state[:, 1]
        ) / 2.0
        result[:, -1] = (
            stage_input[:, -1] + prior_state[:, -2]
        ) / 2.0
        result[:, 1:-1] = (
            stage_input[:, 1:-1]
            + prior_state[:, :-2]
            + prior_state[:, 2:]
        ) / 3.0
        return result

    def transduce(
        self,
        signal: np.ndarray,
        *,
        sample_rate_hz: int,
    ) -> CoupledBinauralCapture:
        if isinstance(sample_rate_hz, bool) or (
            sample_rate_hz != REQUIRED_SAMPLE_RATE_HZ
        ):
            raise ValueError("coupled binaural input must be physical 16 kHz")
        values = np.asarray(signal, dtype=np.float64)
        if (
            values.ndim != 1
            or len(values) < OBSERVATION_HOP_SAMPLES
            or len(values)
            > REQUIRED_SAMPLE_RATE_HZ * MAX_CAPTURE_SECONDS
            or not np.all(np.isfinite(values))
            or np.any(values < -1.0)
            or np.any(values > 1.0)
        ):
            raise ValueError("coupled binaural PCM left bounded custody")
        poles, injections = self._coefficients()
        state = np.zeros(
            (
                len(EAR_IDS),
                COCHLEAR_ORDER,
                COCHLEAR_CHANNEL_COUNT,
            ),
            dtype=np.complex128,
        )
        previous = np.zeros(
            (len(EAR_IDS), COCHLEAR_CHANNEL_COUNT),
            dtype=np.complex128,
        )
        cumulative_phase = np.zeros_like(previous.real)
        energy = np.zeros_like(previous.real)
        phase_lock_sum = np.zeros_like(previous.real)
        frame_count = len(values) // OBSERVATION_HOP_SAMPLES
        envelopes = np.empty(
            (frame_count, len(EAR_IDS), COCHLEAR_CHANNEL_COUNT),
            dtype=np.float64,
        )
        phase_locks = np.empty_like(envelopes)
        phases = np.empty_like(envelopes)
        frame_index = 0
        for source_index, sample in enumerate(values):
            stage_input = np.full(
                (len(EAR_IDS), COCHLEAR_CHANNEL_COUNT),
                float(sample),
                dtype=np.complex128,
            )
            for order_index in range(COCHLEAR_ORDER):
                prior = state[:, order_index].copy()
                coupled = self._neighbor_average(stage_input, prior)
                state[:, order_index] = (
                    poles * prior + injections * coupled
                )
                stage_input = state[:, order_index]
            output = state[:, -1]
            active = (np.abs(output) > 0.0) & (np.abs(previous) > 0.0)
            if np.any(active):
                cumulative_phase[active] += np.angle(
                    output[active] * np.conjugate(previous[active])
                ) / (2.0 * math.pi)
            first = (np.abs(output) > 0.0) & (np.abs(previous) == 0.0)
            if np.any(first):
                cumulative_phase[first] = (
                    np.angle(output[first]) / (2.0 * math.pi)
                )
            magnitude = np.abs(output)
            energy += magnitude ** 2
            phase_lock_sum += np.divide(
                output.real,
                magnitude,
                out=np.zeros_like(magnitude),
                where=magnitude > 0.0,
            )
            previous = output.copy()
            if (source_index + 1) % OBSERVATION_HOP_SAMPLES == 0:
                envelope = np.sqrt(
                    energy / OBSERVATION_HOP_SAMPLES
                )
                if np.any(envelope > 1.0):
                    raise RuntimeError(
                        "passive coupled resonator exceeded unit pressure"
                    )
                envelopes[frame_index] = envelope
                phase_locks[frame_index] = (
                    phase_lock_sum / OBSERVATION_HOP_SAMPLES
                )
                phases[frame_index] = cumulative_phase
                frame_index += 1
                energy.fill(0.0)
                phase_lock_sum.fill(0.0)
        onsets = np.empty_like(envelopes)
        offsets = np.empty_like(envelopes)
        onsets[0] = envelopes[0]
        offsets[0].fill(0.0)
        displacement = envelopes[1:] - envelopes[:-1]
        onsets[1:] = np.maximum(displacement, 0.0)
        offsets[1:] = np.maximum(-displacement, 0.0)
        offsets_samples = tuple(
            (index + 1) * OBSERVATION_HOP_SAMPLES
            for index in range(frame_count)
        )
        fields = tuple(
            CoupledCochlearReceptorField(
                ear_id=ear_id,
                cochlear_index=channel_index,
                centre_hz=AUDITORY_CHANNELS[channel_index].centre_hz,
                erb_width_hz=(
                    AUDITORY_CHANNELS[channel_index].erb_width_hz
                ),
                causal_offsets_samples=offsets_samples,
                envelope=tuple(
                    float(value)
                    for value in envelopes[:, ear_index, channel_index]
                ),
                phase_lock=tuple(
                    float(value)
                    for value in phase_locks[:, ear_index, channel_index]
                ),
                onset=tuple(
                    float(value)
                    for value in onsets[:, ear_index, channel_index]
                ),
                offset=tuple(
                    float(value)
                    for value in offsets[:, ear_index, channel_index]
                ),
                cumulative_phase_turns=tuple(
                    float(value)
                    for value in phases[:, ear_index, channel_index]
                ),
            )
            for ear_index, ear_id in enumerate(EAR_IDS)
            for channel_index in range(COCHLEAR_CHANNEL_COUNT)
        )
        for field in fields:
            field.verify()
        pcm = values.astype("<f8", copy=False).tobytes()
        provisional = CoupledBinauralCapture(
            source_sample_rate_hz=sample_rate_hz,
            input_sample_count=len(values),
            observation_hop_samples=OBSERVATION_HOP_SAMPLES,
            fields=fields,
            topology_receipt_sha256=(
                self._topology.authority_receipt_sha256
            ),
            pcm_sha256=hashlib.sha256(pcm).hexdigest(),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._capture_key,
            _CAPTURE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = CoupledBinauralCapture(
            source_sample_rate_hz=provisional.source_sample_rate_hz,
            input_sample_count=provisional.input_sample_count,
            observation_hop_samples=(
                provisional.observation_hop_samples
            ),
            fields=provisional.fields,
            topology_receipt_sha256=(
                provisional.topology_receipt_sha256
            ),
            pcm_sha256=provisional.pcm_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify_capture(result)
        return result

    def verify_capture(self, capture: CoupledBinauralCapture) -> None:
        if (
            not isinstance(capture, CoupledBinauralCapture)
            or capture.source_sample_rate_hz != REQUIRED_SAMPLE_RATE_HZ
            or capture.observation_hop_samples
            != OBSERVATION_HOP_SAMPLES
            or len(capture.fields)
            != len(EAR_IDS) * COCHLEAR_CHANNEL_COUNT
            or capture.topology_receipt_sha256
            != self._topology.authority_receipt_sha256
            or tuple(
                (value.ear_id, value.cochlear_index)
                for value in capture.fields
            )
            != tuple(
                (ear_id, channel_index)
                for ear_id in EAR_IDS
                for channel_index in range(COCHLEAR_CHANNEL_COUNT)
            )
        ):
            raise ValueError("coupled binaural capture topology changed")
        for field in capture.fields:
            field.verify()
        for value in (
            capture.pcm_sha256,
            capture.authority_hmac_sha256,
            capture.authority_receipt_sha256,
        ):
            _sha256(value, "coupled binaural capture authority")
        payload = capture.payload()
        signature = hmac.new(
            self._capture_key,
            _CAPTURE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature, capture.authority_hmac_sha256
            )
            or capture.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("coupled binaural capture authority changed")

    def mount_l0_l4_inputs(
        self,
        capture: CoupledBinauralCapture,
        *,
        source_anchor: Fraction,
    ) -> tuple[NativeSensorySubstreamInput, ...]:
        self.verify_capture(capture)
        if not isinstance(source_anchor, Fraction):
            raise TypeError(
                "coupled binaural source anchor must be exact Fraction"
            )
        mounted = []
        topology_index = 0
        for field in capture.fields:
            times = tuple(
                source_anchor + Fraction(
                    value, REQUIRED_SAMPLE_RATE_HZ
                )
                for value in field.causal_offsets_samples
            )
            phase = tuple(
                Fraction.from_float(value)
                for value in field.cumulative_phase_turns
            )
            values_by_kind = {
                "envelope": field.envelope,
                "phase_lock": field.phase_lock,
                "onset": field.onset,
                "offset": field.offset,
            }
            envelope_id = (
                f"{field.ear_id}_erb_{field.cochlear_index:02d}_envelope"
            )
            envelope_relevance = tuple(
                Fraction.from_float(value) ** 2
                for value in field.envelope
            )
            for kind in RECEPTOR_KINDS:
                values = values_by_kind[kind]
                substream_id = (
                    f"{field.ear_id}_erb_"
                    f"{field.cochlear_index:02d}_{kind}"
                )
                own_relevance = tuple(
                    Fraction.from_float(abs(value)) ** 2
                    for value in values
                )
                is_phase = kind == "phase_lock"
                mounted.append(NativeSensorySubstreamInput(
                    sense=PhysicalSense.SOUND,
                    sensor_id=(
                        "isolated-coupled-binaural-cochlear-candidate"
                    ),
                    substream_id=substream_id,
                    topology_index=topology_index,
                    coordinates=(
                        NativeAxisCoordinate("ear", field.ear_id),
                        NativeAxisCoordinate(
                            "cochlear-channel",
                            f"erb_{field.cochlear_index:02d}",
                        ),
                        NativeAxisCoordinate("receptor-kind", kind),
                        NativeAxisCoordinate(
                            "centre-hz", str(field.centre_hz)
                        ),
                        NativeAxisCoordinate(
                            "erb-width-hz", str(field.erb_width_hz)
                        ),
                        NativeAxisCoordinate(
                            "neighbor-coupling",
                            "degree-derived-passive-convex",
                        ),
                    ),
                    physical_quantity=(
                        "cochlear-carrier-phase-lock"
                        if is_phase
                        else f"cochlear-pressure-{kind}"
                    ),
                    physical_unit=(
                        "signed-unit-orientation"
                        if is_phase
                        else "full-scale-pressure"
                    ),
                    source_times=times,
                    normalized_signal=values,
                    phase_turns=phase if is_phase else (Fraction(0),) * len(
                        times
                    ),
                    source_relevance=(
                        envelope_relevance if is_phase else own_relevance
                    ),
                    source_relevance_rule=(
                        PAIRED_SOURCE_RELEVANCE_RULE
                    ),
                    source_relevance_origin_substream_id=(
                        envelope_id if is_phase else substream_id
                    ),
                    kernel_input_map=(
                        SIGNED_UNIT_KERNEL_INPUT_MAP
                        if is_phase
                        else AUDITORY_PRESSURE_KERNEL_INPUT_MAP
                    ),
                ))
                topology_index += 1
        if (
            len(mounted) != COMPONENT_COUNT
            or tuple(value.topology_index for value in mounted)
            != tuple(range(COMPONENT_COUNT))
        ):
            raise RuntimeError(
                "coupled binaural mount lost joint topology"
            )
        return tuple(mounted)

    def mount_ear_l0_l4_inputs(
        self,
        capture: CoupledBinauralCapture,
        *,
        ear_id: str,
        source_anchor: Fraction,
    ) -> tuple[NativeSensorySubstreamInput, ...]:
        """Mount one complete ear inside the unchanged 64-port boundary."""

        if ear_id not in EAR_IDS:
            raise ValueError("coupled binaural ear identity changed")
        joint = self.mount_l0_l4_inputs(
            capture,
            source_anchor=source_anchor,
        )
        start = EAR_IDS.index(ear_id) * COMPONENTS_PER_EAR
        selected = joint[start : start + COMPONENTS_PER_EAR]
        result = tuple(
            NativeSensorySubstreamInput(
                sense=value.sense,
                sensor_id=value.sensor_id,
                substream_id=value.substream_id,
                topology_index=index,
                coordinates=value.coordinates,
                physical_quantity=value.physical_quantity,
                physical_unit=value.physical_unit,
                source_times=value.source_times,
                normalized_signal=value.normalized_signal,
                phase_turns=value.phase_turns,
                source_relevance=value.source_relevance,
                source_relevance_rule=value.source_relevance_rule,
                source_relevance_origin_substream_id=(
                    value.source_relevance_origin_substream_id
                ),
                kernel_input_map=value.kernel_input_map,
            )
            for index, value in enumerate(selected)
        )
        if len(result) != COMPONENTS_PER_EAR:
            raise RuntimeError("coupled binaural ear mount is incomplete")
        return result


__all__ = (
    "CANDIDATE_SCHEMA",
    "COMPONENT_COUNT",
    "COMPONENTS_PER_EAR",
    "CoupledBinauralCapture",
    "CoupledBinauralCochlearAuthority",
    "CoupledBinauralTopology",
    "CoupledCochlearReceptorField",
    "EAR_IDS",
    "MAX_FRAME_COUNT",
    "MOUNT_SCHEMA",
    "RECEPTOR_KINDS",
    "TOPOLOGY_SCHEMA",
)
