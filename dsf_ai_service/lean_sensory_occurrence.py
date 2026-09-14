"""One bounded external light/pressure occurrence for the lean owner."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib

from dsf_ai_service.lean_actor import MAX_PRESSURE_BYTES


RETINAL_SITE_COUNT = 135
EXTERNAL_RGB_VALUE_COUNT = RETINAL_SITE_COUNT * 3
# Vision upgrade (real-time or nothing, 2026-09-13): the legacy 405 values
# first, unchanged order, then a 32x24 FOCAL central field (the base already calls the 18x6 center "fine"), row-major RGB.
EXTERNAL_RGB_FOCAL_VALUE_COUNT = EXTERNAL_RGB_VALUE_COUNT + 32 * 24 * 3
SOURCES = frozenset({
    "camera",
    "camera-microphone",
    "card-microphone",
    "caretaker-food",
    "guided-body-microphone",
    "guided-vocal-microphone",
    "media",
    "microphone",
    "text-light",
    "text-microphone",
})
# Hand-over-hand teaching (drive organ, 2026-09-13): the axes a caregiver can
# physically move — trunk 0-1, head 2-3, jaw 14, limbs 19-36 — by the body's
# own axis ordinals. Eyes, eyelids, brows, cheeks, lips and the airway are not
# hand-guidable (the airway has its own guided-vocal source). Native refuses
# the same set (BodyAxis::is_caregiver_guidable).
CAREGIVER_GUIDABLE_BODY_AXES = frozenset({0, 1, 2, 3, 14, *range(19, 37)})
MAX_GUIDED_BODY_DRIVES = 8  # two hands on at most eight axes in one quarter second
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
        or len(values) not in (EXTERNAL_RGB_VALUE_COUNT, EXTERNAL_RGB_FOCAL_VALUE_COUNT)
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 255
            for value in values
        )
    ):
        raise ValueError("sensory light changed the 135-site or 903-site RGB retina")


def legacy_retina_rgb_u8(values: tuple[int, ...]) -> tuple[int, ...]:
    """The established 405-value field: the first 405 values of either shape."""

    _validate_retina_rgb(values)
    return tuple(values[:EXTERNAL_RGB_VALUE_COUNT])


def focal_retina_rgb_u8(values: tuple[int, ...]) -> tuple[int, ...]:
    """The 32x24 focal field (768 sites RGB), or () when the legacy shape arrived."""

    _validate_retina_rgb(values)
    return tuple(values[EXTERNAL_RGB_VALUE_COUNT:])


def focal_retina_luminance_u8(values: tuple[int, ...]) -> tuple[int, ...]:
    """Project the focal RGB sites onto 768 achromatic receptors, () if absent."""

    focal = focal_retina_rgb_u8(values)
    return tuple(
        (focal[i] * 299 + focal[i + 1] * 587 + focal[i + 2] * 114 + 500) // 1_000
        for i in range(0, len(focal), 3)
    )


def rgb_retina_luminance_u8(values: tuple[int, ...]) -> tuple[int, ...]:
    """Project browser RGB onto the established 135 achromatic receptors."""

    _validate_retina_rgb(values)
    values = values[:EXTERNAL_RGB_VALUE_COUNT]
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
    # The caregiver's hand (drive organ, 2026-09-14): the one thing the
    # person body presents at her mouth's reach this interval. Present only;
    # nothing moves her.
    present_food: str | None = None
    # Camera foveal crop parameters: frame-relative origin (horizontal, vertical
    # fractions in [0, 1]), angular pitch in millidegrees, and crop pixel dimensions.
    focal_origin: tuple[float, float] | None = None
    focal_pitch_millidegrees: tuple[int, int] | None = None
    focal_crop_dimensions: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError("sensory source is not mounted")
        retina = self.retina_rgb_u8
        pressure = self.pressure_s16le
        guided = self.guided_vocal_drives
        if (self.source == "caretaker-food") != (self.present_food is not None):
            raise ValueError("caretaker food source and presented object disagree")
        if self.present_food is not None and (
            not isinstance(self.present_food, str)
            or not 1 <= len(self.present_food) <= 64
            or not self.present_food.replace("-", "").isalnum()
        ):
            raise ValueError("presented food identity left its bounded form")
        if self.source == "caretaker-food" and (retina is not None or pressure is not None or guided is not None):
            raise ValueError("caretaker food source carries no light, pressure or body work")
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
            if len(guided) > 9:
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
                    not (axis == 18 or 37 <= axis <= 44)
                    or direction not in (0, 1)
                    or not 1 <= carriers <= (1 << 32) - 1
                    or axis in axes
                ):
                    raise ValueError("guided vocal drive left bounded unique anatomy")
                axes.add(axis)
        elif self.source == "guided-body-microphone":
            # Hand-over-hand teaching: a caregiver moves her trunk, head, jaw or
            # limbs while speaking; the drive is the caregiver's hand on the
            # exact axis, the same body-effector work the guided-vocal lesson
            # applies to the airway. Light (a card, the room) may accompany it.
            if pressure is None or not guided:
                raise ValueError("guided body source lost pressure or body work")
            if len(guided) > MAX_GUIDED_BODY_DRIVES:
                raise ValueError("guided body source exceeded one caregiver's hands")
            axes = set()
            for drive in guided:
                if (
                    not isinstance(drive, tuple)
                    or len(drive) != 3
                    or any(isinstance(value, bool) or not isinstance(value, int) for value in drive)
                ):
                    raise ValueError("guided body drive changed exact shape")
                axis, direction, carriers = drive
                if (
                    axis not in CAREGIVER_GUIDABLE_BODY_AXES
                    or direction not in (0, 1)
                    or not 1 <= carriers <= (1 << 32) - 1
                    or axis in axes
                ):
                    raise ValueError("guided body drive left caregiver-guidable unique anatomy")
                axes.add(axis)
        elif guided is not None:
            raise ValueError("ordinary sensory source carried vocal body work")
        if self.focal_origin is not None and (
            not isinstance(self.focal_origin, tuple)
            or len(self.focal_origin) != 2
            or not all(isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0 for v in self.focal_origin)
        ):
            raise ValueError("focal origin left frame bounds")
        if self.focal_pitch_millidegrees is not None and (
            not isinstance(self.focal_pitch_millidegrees, tuple)
            or len(self.focal_pitch_millidegrees) != 2
            or not all(isinstance(v, int) and 1 <= v <= 180_000 for v in self.focal_pitch_millidegrees)
        ):
            raise ValueError("focal pitch left physical bounds")
        if self.focal_crop_dimensions is not None and (
            not isinstance(self.focal_crop_dimensions, tuple)
            or len(self.focal_crop_dimensions) != 2
            or not all(isinstance(v, int) and v >= 24 for v in self.focal_crop_dimensions)
        ):
            raise ValueError("focal crop dimensions left bounded size")

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
        if self.present_food is not None:
            body += b"\0present:" + self.present_food.encode("ascii")
        if self.focal_origin is not None:
            body += f"\0focal_origin:{self.focal_origin[0]:.4f},{self.focal_origin[1]:.4f}".encode("ascii")
        if self.focal_pitch_millidegrees is not None:
            body += f"\0focal_pitch:{self.focal_pitch_millidegrees[0]},{self.focal_pitch_millidegrees[1]}".encode("ascii")
        if self.focal_crop_dimensions is not None:
            body += f"\0focal_dims:{self.focal_crop_dimensions[0]},{self.focal_crop_dimensions[1]}".encode("ascii")
        return hashlib.sha256(body).hexdigest()


__all__ = (
    "EXTERNAL_RGB_VALUE_COUNT",
    "EXTERNAL_RGB_FOCAL_VALUE_COUNT",
    "LeanSensoryOccurrence",
    "RETINAL_SITE_COUNT",
    "SOURCES",
    "focal_retina_luminance_u8",
    "focal_retina_rgb_u8",
    "legacy_retina_rgb_u8",
    "rgb_retina_luminance_u8",
    "transmitted_rgb_retina_u8",
)
