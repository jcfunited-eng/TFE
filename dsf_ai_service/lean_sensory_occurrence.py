"""One bounded external light/pressure occurrence for the lean owner."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib

from dsf_ai_service.lean_actor import MAX_PRESSURE_BYTES


RETINAL_SITE_COUNT = 135
EXTERNAL_RGB_VALUE_COUNT = RETINAL_SITE_COUNT * 3
SOURCES = frozenset({
    "camera",
    "camera-microphone",
    "card-microphone",
    "guided-vocal-microphone",
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


def _validate_retina_rgb(values: tuple[int, ...]) -> None:
    if (
        not isinstance(values, tuple)
        or len(values) != EXTERNAL_RGB_VALUE_COUNT
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 255
            for value in values
        )
    ):
        raise ValueError("sensory light changed the 135-site RGB retina")


def rgb_retina_luminance_u8(values: tuple[int, ...]) -> tuple[int, ...]:
    """Project browser RGB onto the established 135 achromatic receptors."""

    _validate_retina_rgb(values)
    return tuple(
        (
            values[index] * 299
            + values[index + 1] * 587
            + values[index + 2] * 114
            + 500
        )
        // 1_000
        for index in range(0, len(values), 3)
    )


def transmitted_rgb_retina_u8(
    values: tuple[int, ...], transmission: Fraction
) -> tuple[int, ...]:
    """Expose the exact browser RGB field after body-owned eyelid transmission."""

    _validate_retina_rgb(values)
    if not isinstance(transmission, Fraction) or not 0 <= transmission <= 1:
        raise ValueError("external retinal transmission left physical bounds")
    return tuple(round(Fraction(value) * transmission) for value in values)


@dataclass(frozen=True, slots=True)
class LeanSensoryOccurrence:
    source: str
    retina_rgb_u8: tuple[int, ...] | None
    pressure_s16le: bytes | None
    guided_vocal_drives: tuple[tuple[int, int, int], ...] | None = None

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError("sensory source is not mounted")
        retina = self.retina_rgb_u8
        pressure = self.pressure_s16le
        guided = self.guided_vocal_drives
        if retina is not None:
            _validate_retina_rgb(retina)
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
        if self.source == "guided-vocal-microphone":
            if retina is not None or pressure is None or not guided:
                raise ValueError("guided vocal source lost pressure or body work")
            if len(guided) > 13:
                raise ValueError("guided vocal source exceeded fixed vocal anatomy")
            axes: set[int] = set()
            for drive in guided:
                if (
                    not isinstance(drive, tuple)
                    or len(drive) != 3
                    or any(isinstance(value, bool) or not isinstance(value, int) for value in drive)
                ):
                    raise ValueError("guided vocal drive changed exact shape")
                axis, direction, carriers = drive
                if (
                    not 0 <= axis <= 44
                    or direction not in (0, 1)
                    or not 1 <= carriers <= (1 << 32) - 1
                    or axis in axes
                ):
                    raise ValueError("guided vocal drive left bounded unique anatomy")
                axes.add(axis)
        elif guided is not None:
            raise ValueError("ordinary sensory source carried vocal body work")

    @property
    def source_receipt_sha256(self) -> str:
        retina = b"" if self.retina_rgb_u8 is None else bytes(self.retina_rgb_u8)
        pressure = b"" if self.pressure_s16le is None else self.pressure_s16le
        body = (
            (
                b"guala.lean_sensory_occurrence.v3\0"
                if self.guided_vocal_drives is None
                else b"guala.lean_sensory_occurrence.v4\0"
            )
            + self.source.encode("ascii")
            + len(retina).to_bytes(2, "little")
            + retina
            + len(pressure).to_bytes(2, "little")
            + pressure
        )
        if self.guided_vocal_drives is not None:
            body += len(self.guided_vocal_drives).to_bytes(1, "little")
            for axis, direction, carriers in self.guided_vocal_drives:
                body += (
                    axis.to_bytes(1, "little")
                    + direction.to_bytes(1, "little")
                    + carriers.to_bytes(4, "little")
                )
        return hashlib.sha256(body).hexdigest()


__all__ = (
    "EXTERNAL_RGB_VALUE_COUNT",
    "LeanSensoryOccurrence",
    "RETINAL_SITE_COUNT",
    "SOURCES",
    "rgb_retina_luminance_u8",
    "transmitted_rgb_retina_u8",
)
