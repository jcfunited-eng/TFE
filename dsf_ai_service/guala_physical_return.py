"""One unconsumed physical consequence, carried by the existing world store.

No action, lesson, cognition, acoustic history or body anatomy lives here.
The three sampled frames are the existing world's 0/1/250 ms boundary values.
They reproduce its step and inclusive displacement pulse without interpolation.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from fractions import Fraction
import math
import struct
import uuid

from dsf_ai_service.guala_physical_sensorium import (
    ARTICULATORY_PORTS, COCHLEAR_PORTS, DISPLACEMENT_PORTS, LEGACY_EAR_PORTS,
    RETINAL_PORTS, SMELL_PORTS, TASTE_PORTS, THERMAL_PORTS, TOUCH_PORTS,
    PhysicalSensorium, compact_signal_body,
)


RETURN_TIMES = (Fraction(0), Fraction(1, 1000), Fraction(1, 4))
_PORTS = (
    ("retina", RETINAL_PORTS), ("legacy_ears", LEGACY_EAR_PORTS),
    ("cochleae", COCHLEAR_PORTS), ("touch", TOUCH_PORTS),
    ("smell", SMELL_PORTS), ("taste", TASTE_PORTS),
    ("displacement", DISPLACEMENT_PORTS),
    ("articulation", ARTICULATORY_PORTS), ("thermal", THERMAL_PORTS),
)
RETURN_SAMPLE_BYTES = sum(count for _, count in _PORTS) * 3 * 8
# One native interval emits at most one sparse body episode and the two
# existing root-motion episodes. The body has 45 axes, four endings each.
MAX_RETURN_SOURCES = 3
MAX_BODY_AXES = 45


def _integer(value: object, maximum: int, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError("physical return integer left its representation")
    return value


def _receipt(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("physical return receipt is not canonical")
    return value


def _body(value: object) -> bytes:
    if not isinstance(value, str):
        raise ValueError("physical return byte body is not base64 text")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("physical return byte body is invalid") from error
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError("physical return byte body is not canonical")
    return decoded


@dataclass(frozen=True, slots=True)
class PhysicalReturnSource:
    payload: bytes
    extents: tuple[int, int, int, int]
    admissions: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.payload, bytes) or not self.payload:
            raise ValueError("physical return source is empty")
        if not isinstance(self.extents, tuple) or len(self.extents) != 4:
            raise ValueError("physical return source extent changed")
        ports, samples, occurrences, frames = self.extents
        for value, maximum in zip(self.extents, (4 * MAX_BODY_AXES, 8 * MAX_BODY_AXES, MAX_BODY_AXES, 2 * MAX_BODY_AXES), strict=True):
            _integer(value, maximum, minimum=1)
        if samples != 2 * ports or frames != 2 * occurrences:
            raise ValueError("physical return source lost its two endpoints")
        if not isinstance(self.admissions, tuple) or any(
            not isinstance(interval, tuple) or len(interval) != 2
            or any(isinstance(value, bool) or not isinstance(value, int) for value in interval)
            for interval in self.admissions
        ) or self.admissions != ((1, 1000),) * occurrences:
            raise ValueError("physical return source changed its physical duration")

    @classmethod
    def capture(cls, source: object, admissions: list[tuple[int, int]]) -> PhysicalReturnSource:
        return cls(
            bytes(source.as_bytes()),
            (source.port_count, source.source_sample_count,
             source.occurrence_count, source.occurrence_frame_count),
            tuple(admissions),
        )

    def restore(self) -> object:
        import guala_core
        source = guala_core.settle_native_joint_source_episode(self.payload, *self.extents)
        if bytes(source.as_bytes()) != self.payload:
            raise RuntimeError("physical return source changed on restore")
        return source

    def record(self) -> dict[str, object]:
        return {
            "payload_base64": base64.b64encode(self.payload).decode("ascii"),
            "extents": list(self.extents),
            "admissions": [list(interval) for interval in self.admissions],
        }

    @classmethod
    def from_record(cls, value: object) -> PhysicalReturnSource:
        if not isinstance(value, dict) or set(value) != {"payload_base64", "extents", "admissions"}:
            raise ValueError("physical return source fields changed")
        extents, admissions = value["extents"], value["admissions"]
        if not isinstance(extents, list) or not isinstance(admissions, list) or any(not isinstance(item, list) for item in admissions):
            raise ValueError("physical return source dimensions changed")
        return cls(_body(value["payload_base64"]), tuple(extents), tuple(tuple(item) for item in admissions))


@dataclass(frozen=True, slots=True)
class PendingPhysicalReturn:
    identity: str
    producer_tick: int
    causal_transition_sha256: str
    world_revision: int
    world_observation_receipt_sha256: str
    sampled_sensorium: bytes
    sources: tuple[PhysicalReturnSource, ...]
    vestibular: tuple[int, int] | None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str) or str(uuid.UUID(self.identity)) != self.identity:
            raise ValueError("physical return identity is not canonical")
        _integer(self.producer_tick, (1 << 64) - 1)
        _integer(self.world_revision, (1 << 64) - 1)
        _receipt(self.causal_transition_sha256)
        _receipt(self.world_observation_receipt_sha256)
        if not isinstance(self.sampled_sensorium, bytes) or len(self.sampled_sensorium) != RETURN_SAMPLE_BYTES:
            raise ValueError("physical return lost its exact three sampled frames")
        if any(not math.isfinite(value[0]) for value in struct.iter_unpack("<d", self.sampled_sensorium)):
            raise ValueError("physical return contains a non-finite boundary value")
        if not isinstance(self.sources, tuple) or len(self.sources) > MAX_RETURN_SOURCES or any(not isinstance(source, PhysicalReturnSource) for source in self.sources):
            raise ValueError("physical return exceeded one interval's source anatomy")
        if self.vestibular is not None:
            if not isinstance(self.vestibular, tuple) or len(self.vestibular) != 2:
                raise ValueError("physical return yaw changed shape")
            _integer(self.vestibular[0], 359999)
            _integer(self.vestibular[1], (1 << 31) - 1, minimum=-(1 << 31))

    @classmethod
    def capture(cls, *, identity: str, producer_tick: int,
                causal_transition_sha256: str, world_revision: int,
                world_observation_receipt_sha256: str,
                sensorium: PhysicalSensorium,
                sources: tuple[PhysicalReturnSource, ...],
                vestibular: tuple[int, int] | None) -> PendingPhysicalReturn:
        return cls(identity, producer_tick, causal_transition_sha256,
                   world_revision, world_observation_receipt_sha256,
                   compact_signal_body(sensorium, frame_count=3), sources, vestibular)

    def validate_binding(self, *, identity: str, producer_tick: int,
                         world_revision: int, world_receipt: str) -> None:
        if (identity, producer_tick, world_revision, world_receipt) != (
            self.identity, self.producer_tick, self.world_revision,
            self.world_observation_receipt_sha256,
        ):
            raise RuntimeError("pending physical return does not belong to the current body/world")

    def sensorium(self, source_times: tuple[Fraction, ...]) -> PhysicalSensorium:
        if not source_times or source_times[0] != RETURN_TIMES[0] or source_times[-1] != RETURN_TIMES[-1] or RETURN_TIMES[1] not in source_times:
            raise ValueError("physical return source clock lost its endpoints")
        if any(not isinstance(time, Fraction) for time in source_times) or any(left >= right for left, right in zip(source_times, source_times[1:])):
            raise ValueError("physical return source clock is not exact and ordered")
        indices = tuple(0 if time < RETURN_TIMES[1] else 1 if time == RETURN_TIMES[1] else 2 for time in source_times)
        frames = struct.iter_unpack("<ddd", self.sampled_sensorium)
        values = {
            name: tuple(tuple(frame[index] for index in indices) for frame in (next(frames) for _ in range(count)))
            for name, count in _PORTS
        }
        return PhysicalSensorium(**values)

    def record(self) -> dict[str, object]:
        return {
            "identity": self.identity, "producer_tick": self.producer_tick,
            "causal_transition_sha256": self.causal_transition_sha256,
            "world_revision": self.world_revision,
            "world_observation_receipt_sha256": self.world_observation_receipt_sha256,
            "sampled_sensorium_base64": base64.b64encode(self.sampled_sensorium).decode("ascii"),
            "sources": [source.record() for source in self.sources],
            "vestibular": None if self.vestibular is None else list(self.vestibular),
        }

    @classmethod
    def from_record(cls, value: object) -> PendingPhysicalReturn:
        expected = {"identity", "producer_tick", "causal_transition_sha256", "world_revision", "world_observation_receipt_sha256", "sampled_sensorium_base64", "sources", "vestibular"}
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError("pending physical return fields changed")
        sources, vestibular = value["sources"], value["vestibular"]
        if not isinstance(sources, list) or len(sources) > MAX_RETURN_SOURCES:
            raise ValueError("pending physical return source count changed")
        if vestibular is not None and not isinstance(vestibular, list):
            raise ValueError("pending physical return yaw is not a pair")
        return cls(value["identity"], value["producer_tick"],
                   value["causal_transition_sha256"], value["world_revision"],
                   value["world_observation_receipt_sha256"],
                   _body(value["sampled_sensorium_base64"]),
                   tuple(PhysicalReturnSource.from_record(source) for source in sources),
                   None if vestibular is None else tuple(vestibular))
