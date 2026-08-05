"""Isolated exact W1 stereo renderer and auditory-brainstem topology.

This audit-only authority reuses W1's public ear geometry, propagation delay,
inverse-square attenuation, and exact binaural transfer types.  It does not
modify the live auditory provider or kernel.

The controlled chamber has no pinna, head shadow, diffraction, reflection,
reverberation, or sensor noise.  Those absences are explicit losses, not
implicit approximations.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedBody,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    calibrated_ear_positions,
    distance_squared_mm,
    pcm16_bytes,
    propagation_delay_samples,
    scaled_pcm16_sample,
    signed_pcm16_samples,
)
from dsf_ai_service.substrate.w1_exact_binaural_source_separation import (
    ExactBinauralTransferPath,
)


STEREO_CAPTURE_SCHEMA = "guala.audit.w1.physical_stereo_capture.v1"
BRAINSTEM_TOPOLOGY_SCHEMA = (
    "guala.audit.w1.auditory_brainstem_topology.v1"
)
BRAINSTEM_RELATION_SCHEMA = (
    "guala.audit.w1.auditory_brainstem_relation.v1"
)
BILATERAL_ASSEMBLY_SCHEMA = (
    "guala.audit.w1.mirrored_bilateral_assembly.v1"
)
EAR_SEPARATION_MM = 200
REFERENCE_DISTANCE_MM = 300
_CAPTURE_DOMAIN = b"guala-audit-w1-physical-stereo-capture-v1\0"
_BRAINSTEM_DOMAIN = b"guala-audit-w1-brainstem-v1\0"
_ASSEMBLY_DOMAIN = b"guala-audit-w1-bilateral-assembly-v1\0"
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
        raise ValueError("physical stereo authority key changed")
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


def _fraction(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("physical stereo relation is not exact")
    return f"{value.numerator}/{value.denominator}"


def controlled_chamber_geometry() -> tuple[
    tuple[PositionMM, PositionMM],
    tuple[PositionMM, PositionMM],
]:
    body = EmbodiedBody(
        "audit-listener",
        PoseMM(PositionMM(0, 0, 0), 0),
        radius_mm=100,
        reach_mm=300,
    )
    ears = calibrated_ear_positions(body, EAR_SEPARATION_MM)
    if ears is None:
        raise RuntimeError("controlled chamber ear geometry unresolved")
    sources = (
        PositionMM(200, 100, 0),
        PositionMM(200, -100, 0),
    )
    return ears, sources


def transfer_path(
    source: PositionMM,
    *,
    ears: tuple[PositionMM, PositionMM],
) -> ExactBinauralTransferPath:
    distances = tuple(
        distance_squared_mm(source, ear) for ear in ears
    )
    reference_squared = REFERENCE_DISTANCE_MM**2
    result = ExactBinauralTransferPath(
        left_delay_samples=propagation_delay_samples(distances[0]),
        right_delay_samples=propagation_delay_samples(distances[1]),
        left_attenuation=Fraction(
            reference_squared,
            max(reference_squared, distances[0]),
        ),
        right_attenuation=Fraction(
            reference_squared,
            max(reference_squared, distances[1]),
        ),
    )
    result.verify()
    return result


@dataclass(frozen=True, slots=True)
class PhysicalStereoCapture:
    source_receipt_sha256s: tuple[str, ...]
    paths: tuple[ExactBinauralTransferPath, ...]
    source_sample_count: int
    capture_sample_count: int
    left_pcm_s16le: bytes
    right_pcm_s16le: bytes
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "capture_sample_count": self.capture_sample_count,
            "left_pcm_sha256": hashlib.sha256(
                self.left_pcm_s16le
            ).hexdigest(),
            "paths": [value.payload() for value in self.paths],
            "right_pcm_sha256": hashlib.sha256(
                self.right_pcm_s16le
            ).hexdigest(),
            "schema": STEREO_CAPTURE_SCHEMA,
            "source_receipt_sha256s": list(
                self.source_receipt_sha256s
            ),
            "source_sample_count": self.source_sample_count,
        }


@dataclass(frozen=True, slots=True)
class BrainstemRelationFrame:
    channel_index: int
    frame_index: int
    path_delay_difference_samples: int
    envelope_level_difference: Fraction
    cumulative_phase_difference_turns: Fraction
    phase_advance_difference_turns: Fraction
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "channel_index": self.channel_index,
            "cumulative_phase_difference_turns": _fraction(
                self.cumulative_phase_difference_turns
            ),
            "envelope_level_difference": _fraction(
                self.envelope_level_difference
            ),
            "frame_index": self.frame_index,
            "path_delay_difference_samples": (
                self.path_delay_difference_samples
            ),
            "phase_advance_difference_turns": _fraction(
                self.phase_advance_difference_turns
            ),
            "schema": BRAINSTEM_RELATION_SCHEMA,
        }


@dataclass(frozen=True, slots=True)
class BrainstemComparison:
    topology_receipt_sha256: str
    stereo_capture_receipt_sha256: str
    frames: tuple[BrainstemRelationFrame, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "frame_receipt_sha256s": [
                value.authority_receipt_sha256
                for value in self.frames
            ],
            "schema": "guala.audit.w1.brainstem_comparison.v1",
            "stereo_capture_receipt_sha256": (
                self.stereo_capture_receipt_sha256
            ),
            "topology_receipt_sha256": self.topology_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class MirroredBilateralAssembly:
    left_hemisphere_port_receipt_sha256s: tuple[str, ...]
    right_hemisphere_port_receipt_sha256s: tuple[str, ...]
    brainstem_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "brainstem_receipt_sha256": self.brainstem_receipt_sha256,
            "left_hemisphere_port_receipt_sha256s": list(
                self.left_hemisphere_port_receipt_sha256s
            ),
            "right_hemisphere_port_receipt_sha256s": list(
                self.right_hemisphere_port_receipt_sha256s
            ),
            "schema": BILATERAL_ASSEMBLY_SCHEMA,
        }


class PhysicalStereoAuditAuthority:
    def __init__(self, *, authority_key: bytes | str) -> None:
        root = hashlib.sha256(_key(authority_key)).digest()
        self._capture_key = hashlib.sha256(
            _CAPTURE_DOMAIN + root
        ).digest()
        self._brainstem_key = hashlib.sha256(
            _BRAINSTEM_DOMAIN + root
        ).digest()
        self._assembly_key = hashlib.sha256(
            _ASSEMBLY_DOMAIN + root
        ).digest()
        ears, sources = controlled_chamber_geometry()
        self.ears = ears
        self.sources = sources
        self.paths = tuple(
            transfer_path(source, ears=ears) for source in sources
        )
        topology_payload = {
            "edges": [
                [f"left:erb_{index:02d}", f"right:erb_{index:02d}"]
                for index in range(len(AUDITORY_CHANNELS))
            ],
            "relation_fields": [
                "path_delay_difference_samples",
                "envelope_level_difference",
                "cumulative_phase_difference_turns",
                "phase_advance_difference_turns",
            ],
            "schema": BRAINSTEM_TOPOLOGY_SCHEMA,
        }
        signature = hmac.new(
            self._brainstem_key,
            _BRAINSTEM_DOMAIN + _canonical(topology_payload),
            hashlib.sha256,
        ).hexdigest()
        self.topology_receipt_sha256 = _digest({
            "authority_hmac_sha256": signature,
            "payload": topology_payload,
        })

    def render(
        self,
        sources_pcm_s16le: tuple[bytes, ...],
        *,
        source_ordinals: tuple[int, ...],
    ) -> PhysicalStereoCapture:
        if (
            not sources_pcm_s16le
            or len(sources_pcm_s16le) != len(source_ordinals)
            or any(
                isinstance(value, bool)
                or not 0 <= value < len(self.paths)
                for value in source_ordinals
            )
            or len(set(source_ordinals)) != len(source_ordinals)
        ):
            raise ValueError("physical stereo source topology changed")
        sources = tuple(
            signed_pcm16_samples(value) for value in sources_pcm_s16le
        )
        if len({len(value) for value in sources}) != 1:
            raise ValueError(
                "overlapping physical sources need one closed interval"
            )
        source_count = len(sources[0])
        paths = tuple(self.paths[value] for value in source_ordinals)
        maximum_delay = max(
            max(path.left_delay_samples, path.right_delay_samples)
            for path in paths
        )
        capture_count = source_count + maximum_delay
        ears = []
        for ear_index in range(2):
            rendered = []
            for capture_index in range(capture_count):
                pressure = 0
                for source, path in zip(sources, paths, strict=True):
                    delay = (
                        path.left_delay_samples
                        if ear_index == 0
                        else path.right_delay_samples
                    )
                    source_index = capture_index - delay
                    if 0 <= source_index < source_count:
                        attenuation = (
                            path.left_attenuation
                            if ear_index == 0
                            else path.right_attenuation
                        )
                        pressure += scaled_pcm16_sample(
                            source[source_index], attenuation
                        )
                if not -(1 << 15) <= pressure < (1 << 15):
                    raise ValueError(
                        "overlapping physical pressure exceeds PCM16"
                    )
                rendered.append(pressure)
            ears.append(pcm16_bytes(tuple(rendered)))
        provisional = PhysicalStereoCapture(
            source_receipt_sha256s=tuple(
                hashlib.sha256(value).hexdigest()
                for value in sources_pcm_s16le
            ),
            paths=paths,
            source_sample_count=source_count,
            capture_sample_count=capture_count,
            left_pcm_s16le=ears[0],
            right_pcm_s16le=ears[1],
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._capture_key,
            _CAPTURE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = PhysicalStereoCapture(
            source_receipt_sha256s=provisional.source_receipt_sha256s,
            paths=provisional.paths,
            source_sample_count=provisional.source_sample_count,
            capture_sample_count=provisional.capture_sample_count,
            left_pcm_s16le=provisional.left_pcm_s16le,
            right_pcm_s16le=provisional.right_pcm_s16le,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify_capture(result)
        return result

    def verify_capture(self, capture: PhysicalStereoCapture) -> None:
        if (
            not isinstance(capture, PhysicalStereoCapture)
            or not 1 <= len(capture.paths) <= 2
            or capture.capture_sample_count
            != capture.source_sample_count
            + max(
                max(value.left_delay_samples, value.right_delay_samples)
                for value in capture.paths
            )
            or len(capture.left_pcm_s16le)
            != capture.capture_sample_count * 2
            or len(capture.right_pcm_s16le)
            != capture.capture_sample_count * 2
        ):
            raise ValueError("physical stereo capture boundary changed")
        for path in capture.paths:
            path.verify()
        for value in (
            *capture.source_receipt_sha256s,
            capture.authority_hmac_sha256,
            capture.authority_receipt_sha256,
        ):
            _sha256(value, "physical stereo authority")
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
            raise ValueError("physical stereo capture authority changed")

    def compare_brainstem(
        self,
        capture: PhysicalStereoCapture,
    ) -> BrainstemComparison:
        self.verify_capture(capture)
        if len(capture.paths) != 1:
            raise ValueError(
                "word brainstem comparison requires one physical source"
            )
        ears = tuple(
            transduce_auditory_full_field(
                np.asarray(
                    signed_pcm16_samples(value), dtype=np.float64
                )
                / 32_768.0,
                sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
            )
            for value in (
                capture.left_pcm_s16le,
                capture.right_pcm_s16le,
            )
        )
        frame_count = min(value.frame_count for value in ears)
        delay_difference = (
            capture.paths[0].right_delay_samples
            - capture.paths[0].left_delay_samples
        )
        frames = []
        for channel_index in range(len(AUDITORY_CHANNELS)):
            left = ears[0].channels[channel_index]
            right = ears[1].channels[channel_index]
            for frame_index in range(frame_count):
                provisional = BrainstemRelationFrame(
                    channel_index=channel_index,
                    frame_index=frame_index,
                    path_delay_difference_samples=delay_difference,
                    envelope_level_difference=(
                        Fraction.from_float(
                            left.pressure_envelope_full_scale[frame_index]
                        )
                        - Fraction.from_float(
                            right.pressure_envelope_full_scale[frame_index]
                        )
                    ),
                    cumulative_phase_difference_turns=(
                        Fraction.from_float(
                            left.carrier_phase_turns[frame_index]
                        )
                        - Fraction.from_float(
                            right.carrier_phase_turns[frame_index]
                        )
                    ),
                    phase_advance_difference_turns=(
                        Fraction.from_float(
                            left.carrier_phase_advance_turns[frame_index]
                        )
                        - Fraction.from_float(
                            right.carrier_phase_advance_turns[frame_index]
                        )
                    ),
                    authority_receipt_sha256="0" * 64,
                )
                frames.append(BrainstemRelationFrame(
                    channel_index=provisional.channel_index,
                    frame_index=provisional.frame_index,
                    path_delay_difference_samples=(
                        provisional.path_delay_difference_samples
                    ),
                    envelope_level_difference=(
                        provisional.envelope_level_difference
                    ),
                    cumulative_phase_difference_turns=(
                        provisional.cumulative_phase_difference_turns
                    ),
                    phase_advance_difference_turns=(
                        provisional.phase_advance_difference_turns
                    ),
                    authority_receipt_sha256=_digest(
                        provisional.payload()
                    ),
                ))
        provisional_comparison = BrainstemComparison(
            topology_receipt_sha256=self.topology_receipt_sha256,
            stereo_capture_receipt_sha256=(
                capture.authority_receipt_sha256
            ),
            frames=tuple(frames),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional_comparison.payload()
        signature = hmac.new(
            self._brainstem_key,
            _BRAINSTEM_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = BrainstemComparison(
            topology_receipt_sha256=(
                provisional_comparison.topology_receipt_sha256
            ),
            stereo_capture_receipt_sha256=(
                provisional_comparison.stereo_capture_receipt_sha256
            ),
            frames=provisional_comparison.frames,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify_brainstem(result)
        return result

    def verify_brainstem(self, value: BrainstemComparison) -> None:
        if (
            not isinstance(value, BrainstemComparison)
            or value.topology_receipt_sha256
            != self.topology_receipt_sha256
            or not value.frames
        ):
            raise ValueError("brainstem comparison topology changed")
        for index, frame in enumerate(value.frames):
            if (
                frame.channel_index
                != index // (len(value.frames) // len(AUDITORY_CHANNELS))
                or frame.authority_receipt_sha256
                != _digest(frame.payload())
            ):
                raise ValueError("brainstem relation frame changed")
        payload = value.payload()
        signature = hmac.new(
            self._brainstem_key,
            _BRAINSTEM_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(signature, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("brainstem authority changed")

    def assemble_bilateral(
        self,
        *,
        left_ear_port_receipt_sha256s: tuple[str, ...],
        right_ear_port_receipt_sha256s: tuple[str, ...],
        brainstem: BrainstemComparison,
    ) -> MirroredBilateralAssembly:
        self.verify_brainstem(brainstem)
        if (
            len(left_ear_port_receipt_sha256s) != 32
            or len(right_ear_port_receipt_sha256s) != 32
            or set(left_ear_port_receipt_sha256s).intersection(
                right_ear_port_receipt_sha256s
            )
        ):
            raise ValueError("bilateral auditory port topology changed")
        for value in (
            *left_ear_port_receipt_sha256s,
            *right_ear_port_receipt_sha256s,
        ):
            _sha256(value, "bilateral auditory port")
        provisional = MirroredBilateralAssembly(
            left_hemisphere_port_receipt_sha256s=(
                left_ear_port_receipt_sha256s
                + right_ear_port_receipt_sha256s
            ),
            right_hemisphere_port_receipt_sha256s=(
                right_ear_port_receipt_sha256s
                + left_ear_port_receipt_sha256s
            ),
            brainstem_receipt_sha256=brainstem.authority_receipt_sha256,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._assembly_key,
            _ASSEMBLY_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        return MirroredBilateralAssembly(
            left_hemisphere_port_receipt_sha256s=(
                provisional.left_hemisphere_port_receipt_sha256s
            ),
            right_hemisphere_port_receipt_sha256s=(
                provisional.right_hemisphere_port_receipt_sha256s
            ),
            brainstem_receipt_sha256=provisional.brainstem_receipt_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )


__all__ = (
    "BILATERAL_ASSEMBLY_SCHEMA",
    "BRAINSTEM_RELATION_SCHEMA",
    "BRAINSTEM_TOPOLOGY_SCHEMA",
    "BrainstemComparison",
    "BrainstemRelationFrame",
    "EAR_SEPARATION_MM",
    "MirroredBilateralAssembly",
    "PhysicalStereoAuditAuthority",
    "PhysicalStereoCapture",
    "REFERENCE_DISTANCE_MM",
    "STEREO_CAPTURE_SCHEMA",
    "controlled_chamber_geometry",
    "transfer_path",
)
