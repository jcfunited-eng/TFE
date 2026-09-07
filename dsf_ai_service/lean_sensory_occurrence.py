"""One bounded external light/pressure occurrence for the lean owner."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from dsf_ai_service.guala_physical_sensorium import RETINAL_PORTS
from dsf_ai_service.lean_actor import MAX_PRESSURE_BYTES


RETINAL_SITE_COUNT = RETINAL_PORTS
SOURCES = frozenset({
    "camera",
    "camera-microphone",
    "card-microphone",
    "media",
    "microphone",
    "text-light",
    "text-microphone",
})
LIGHT_ONLY_SOURCES = frozenset({"camera", "media", "text-light"})
PRESSURE_ONLY_SOURCES = frozenset({"microphone"})
CO_SENSORY_SOURCES = frozenset({
    "camera-microphone",
    "card-microphone",
    "text-microphone",
})


@dataclass(frozen=True, slots=True)
class LeanSensoryOccurrence:
    source: str
    retina_u8: tuple[int, ...] | None
    pressure_s16le: bytes | None

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError("sensory source is not mounted")
        retina = self.retina_u8
        pressure = self.pressure_s16le
        if retina is not None and (
            len(retina) != RETINAL_SITE_COUNT
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 255
                for value in retina
            )
        ):
            raise ValueError("sensory light changed the 135-site u8 retina")
        if pressure is not None and (
            not isinstance(pressure, bytes)
            or not pressure
            or len(pressure) > MAX_PRESSURE_BYTES
            or len(pressure) % 2
        ):
            raise ValueError("sensory pressure changed its bounded s16le body")
        if self.source in LIGHT_ONLY_SOURCES and (
            retina is None or pressure is not None
        ):
            raise ValueError("light-only sensory source changed modality")
        if self.source in PRESSURE_ONLY_SOURCES and (
            pressure is None or retina is not None
        ):
            raise ValueError("pressure-only sensory source changed modality")
        if self.source in CO_SENSORY_SOURCES and (
            retina is None or pressure is None
        ):
            raise ValueError("co-sensory source lost light or pressure")

    @property
    def source_receipt_sha256(self) -> str:
        retina = b"" if self.retina_u8 is None else bytes(self.retina_u8)
        pressure = b"" if self.pressure_s16le is None else self.pressure_s16le
        body = (
            b"guala.lean_sensory_occurrence.v1\0"
            + self.source.encode("ascii")
            + len(retina).to_bytes(2, "little")
            + retina
            + len(pressure).to_bytes(2, "little")
            + pressure
        )
        return hashlib.sha256(body).hexdigest()


__all__ = (
    "LeanSensoryOccurrence",
    "RETINAL_SITE_COUNT",
    "SOURCES",
)
