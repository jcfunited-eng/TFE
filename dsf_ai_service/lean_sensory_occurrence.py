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


def _validate_retina_rgb(
    values: tuple[int, ...], retinal_site_indices: tuple[int, ...] | None = None,
) -> None:
    if retinal_site_indices is not None and (
        not isinstance(retinal_site_indices, tuple)
        or not retinal_site_indices
        or len(retinal_site_indices) > EXTERNAL_RGB_FOCAL_VALUE_COUNT // 3
        or any(type(site) is not int or not 0 <= site < EXTERNAL_RGB_FOCAL_VALUE_COUNT // 3
               for site in retinal_site_indices)
        or any(left >= right for left, right in
               zip(retinal_site_indices, retinal_site_indices[1:]))
    ):
        raise ValueError("sampled retinal sites are not bounded canonical anatomy")
    if (
        not isinstance(values, tuple)
        or (
            len(values) not in (EXTERNAL_RGB_VALUE_COUNT, EXTERNAL_RGB_FOCAL_VALUE_COUNT)
            if retinal_site_indices is None else len(values) != 3 * len(retinal_site_indices)
        )
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
    values: tuple[int, ...], transmission: Fraction,
    *, retinal_site_indices: tuple[int, ...] | None = None,
) -> tuple[int, ...]:
    """Expose only supplied RGB sites after body-owned eyelid transmission."""

    _validate_retina_rgb(values, retinal_site_indices)
    if not isinstance(transmission, Fraction) or not 0 <= transmission <= 1:
        raise ValueError("external retinal transmission left physical bounds")
    return tuple(round(Fraction(value) * transmission) for value in values)


def sampled_retina_luminance_u8(
    values: tuple[int, ...], retinal_site_indices: tuple[int, ...],
) -> tuple[int, ...]:
    """The existing achromatic law, once for each explicitly sampled site."""

    _validate_retina_rgb(values, retinal_site_indices)
    return tuple(
        (values[i] * 299 + values[i + 1] * 587 + values[i + 2] * 114 + 500) // 1_000
        for i in range(0, len(values), 3)
    )


@dataclass(frozen=True, slots=True)
class LeanSensoryOccurrence:
    source: str
    retina_rgb_u8: tuple[int, ...] | None
    pressure_s16le: bytes | None
    guided_vocal_drives: tuple[tuple[int, int, int], ...] | None = None
    retinal_site_indices: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError("sensory source is not mounted")
        retina = self.retina_rgb_u8
        pressure = self.pressure_s16le
        guided = self.guided_vocal_drives
        if retina is not None:
            _validate_retina_rgb(retina, self.retinal_site_indices)
        elif self.retinal_site_indices is not None:
            raise ValueError("sampled retinal sites have no captured light")
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

    @property
    def source_receipt_sha256(self) -> str:
        retina = b"" if self.retina_rgb_u8 is None else bytes(self.retina_rgb_u8)
        pressure = b"" if self.pressure_s16le is None else self.pressure_s16le
        body = (
            (
                b"guala.lean_sensory_occurrence.v5\0"
                if self.retinal_site_indices is not None else (
                    b"guala.lean_sensory_occurrence.v3\0"
                    if self.guided_vocal_drives is None
                    else b"guala.lean_sensory_occurrence.v4\0"
                )
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
        if self.retinal_site_indices is not None:
            body += len(self.retinal_site_indices).to_bytes(2, "little")
            body += b"".join(site.to_bytes(2, "little") for site in self.retinal_site_indices)
        return hashlib.sha256(body).hexdigest()


__all__ = (
    "EXTERNAL_RGB_VALUE_COUNT",
    "LeanSensoryOccurrence",
    "RETINAL_SITE_COUNT",
    "SOURCES",
    "rgb_retina_luminance_u8",
    "transmitted_rgb_retina_u8",
)
