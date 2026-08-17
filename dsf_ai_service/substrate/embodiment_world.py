"""Deterministic bounded authority for Guala's first multi-region world.

This module owns opaque physical regions, portals, bodies, and objects. One
body is the substrate's self-body. Every body has a separate physical command
port; those ports are control topology, never names, language meanings, or
sensory identity. The authority does not choose actions or assign meaning to
them. It executes canonical typed commands arriving as opaque bytes on
actor-specific embodiment ports, using exact integer geometry. Each accepted
transition is atomic and produces authenticated before/after observations and
an authenticated execution receipt.

There is deliberately no random movement, script, object-to-verb lookup,
language lookup, chi identity, DSF projection, or dependency on the retired
semantic-environment mechanisms here.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from math import isqrt

from dsf_ai_service.substrate.exact_lattice_rotation import (
    rotate_lattice_offset,
)


PORT_ID = "guala.embodiment.w1"
SECOND_BODY_PORT_ID = "guala.embodiment.w1.body-2"

COMMAND_SCHEMA = "guala.embodiment.command.v6"
OBSERVATION_SCHEMA = "guala.embodiment.observation.v6"
EXECUTION_SCHEMA = "guala.embodiment.execution.v6"
STATE_SCHEMA = "guala.embodiment.state.v7"
ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v7"
MIGRATION_SCHEMA = "guala.embodiment.optical_surface_migration.v6"

V6_STATE_SCHEMA = "guala.embodiment.state.v6"
V6_ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v6"

V5_OBSERVATION_SCHEMA = "guala.embodiment.observation.v5"
V5_EXECUTION_SCHEMA = "guala.embodiment.execution.v5"
V5_STATE_SCHEMA = "guala.embodiment.state.v5"
V5_ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v5"
V5_MIGRATION_SCHEMA = "guala.embodiment.material_state_migration.v5"

V4_COMMAND_SCHEMA = "guala.embodiment.command.v4"
V4_OBSERVATION_SCHEMA = "guala.embodiment.observation.v4"
V4_EXECUTION_SCHEMA = "guala.embodiment.execution.v4"
V4_STATE_SCHEMA = "guala.embodiment.state.v4"
V4_ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v4"
V4_MIGRATION_SCHEMA = "guala.embodiment.topology_migration.v4"

V3_COMMAND_SCHEMA = "guala.embodiment.command.v1"
V3_OBSERVATION_SCHEMA = "guala.embodiment.observation.v3"
V3_EXECUTION_SCHEMA = "guala.embodiment.execution.v3"
V3_STATE_SCHEMA = "guala.embodiment.state.v3"
V3_ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v3"
V3_MIGRATION_SCHEMA = "guala.embodiment.topology_migration.v2"

V2_OBSERVATION_SCHEMA = "guala.embodiment.observation.v2"
V2_EXECUTION_SCHEMA = "guala.embodiment.execution.v2"
V2_STATE_SCHEMA = "guala.embodiment.state.v2"
V2_ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v2"
V2_MIGRATION_SCHEMA = "guala.embodiment.migration.v1"

LEGACY_OBSERVATION_SCHEMA = "guala.embodiment.observation.v1"
LEGACY_STATE_SCHEMA = "guala.embodiment.state.v1"
LEGACY_ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v1"

OBSERVATION_DOMAIN = b"guala-embodiment-observation-v6\0"
EXECUTION_DOMAIN = b"guala-embodiment-execution-v6\0"
STATE_DOMAIN = b"guala-embodiment-state-v7\0"
MIGRATION_DOMAIN = b"guala-embodiment-optical-surface-migration-v6\0"

V6_STATE_DOMAIN = b"guala-embodiment-state-v6\0"

V5_OBSERVATION_DOMAIN = b"guala-embodiment-observation-v5\0"
V5_EXECUTION_DOMAIN = b"guala-embodiment-execution-v5\0"
V5_STATE_DOMAIN = b"guala-embodiment-state-v5\0"
V5_MIGRATION_DOMAIN = b"guala-embodiment-material-state-migration-v5\0"

V4_OBSERVATION_DOMAIN = b"guala-embodiment-observation-v4\0"
V4_EXECUTION_DOMAIN = b"guala-embodiment-execution-v4\0"
V4_STATE_DOMAIN = b"guala-embodiment-state-v4\0"

V3_OBSERVATION_DOMAIN = b"guala-embodiment-observation-v3\0"
V3_EXECUTION_DOMAIN = b"guala-embodiment-execution-v3\0"
V3_STATE_DOMAIN = b"guala-embodiment-state-v3\0"

V2_OBSERVATION_DOMAIN = b"guala-embodiment-observation-v2\0"
V2_EXECUTION_DOMAIN = b"guala-embodiment-execution-v2\0"
V2_STATE_DOMAIN = b"guala-embodiment-state-v2\0"

LEGACY_OBSERVATION_DOMAIN = b"guala-embodiment-observation-v1\0"
LEGACY_STATE_DOMAIN = b"guala-embodiment-state-v1\0"

DEFAULT_MAX_REGIONS = 4
DEFAULT_MAX_PORTALS = 6
DEFAULT_MAX_OBJECTS = 64
DEFAULT_MAX_BODIES = 4
DEFAULT_RECEIPT_CAPACITY = 16
DEFAULT_MAX_COMMAND_BYTES = 4096
DEFAULT_MAX_ENCODED_STATE_BYTES = 2 * 1024 * 1024
LEGACY_MAX_ENCODED_STATE_BYTES = 8 * 1024 * 1024
MAX_IDENTIFIER_BYTES = 256
MAX_REVISION = (1 << 63) - 1
OPTICAL_BANDS = 6
MAX_PHYSICAL_PPM = 1_000_000
MAX_OPTICAL_SURFACE_COLUMNS = 128
MAX_OPTICAL_SURFACE_ROWS = 160
MAX_OPTICAL_SURFACE_PALETTE_ENTRIES = 256
ODORANT_CHANNELS = 8
TASTANT_CHANNELS = 5
MIN_MATERIAL_ACTION_DURATION_US = 1_000
MAX_MATERIAL_ACTION_DURATION_US = 5_000_000
MAX_MATERIAL_MASS = (1 << 63) - 1
VOCAL_SAMPLE_RATE_HZ = 16_000
MIN_VOCAL_SAMPLE_COUNT = 160
# One physical vocal action spans exactly one admitted continuous microphone
# transport window.  The five-second interval is the existing live sample
# clock contract, not a semantic timeout; keeping it whole prevents one
# physical experience from being fragmented into dozens of control actions.
MAX_VOCAL_SAMPLE_COUNT = 5 * VOCAL_SAMPLE_RATE_HZ


@dataclass(frozen=True, slots=True)
class _CanonicalJsonFragment:
    encoded: bytes


def _canonical_skeleton(
    value: object,
) -> tuple[bytes, tuple[tuple[bytes, bytes], ...]]:
    fragments: list[tuple[bytes, bytes]] = []

    def stage(item: object) -> object:
        if isinstance(item, _CanonicalJsonFragment):
            index = len(fragments)
            marker = (
                "__guala_exact_canonical_fragment_"
                + str(index)
                + "_"
                + hashlib.sha256(item.encoded).hexdigest()
                + "__"
            )
            marker_bytes = json.dumps(
                marker,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            fragments.append((marker_bytes, item.encoded))
            return marker
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                raise TypeError("canonical object keys must be text")
            return {key: stage(item[key]) for key in item}
        if isinstance(item, list):
            return [stage(child) for child in item]
        if isinstance(item, tuple):
            return tuple(stage(child) for child in item)
        return item

    encoded = json.dumps(
        stage(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return encoded, tuple(fragments)


def _canonical_fragment_spans(
    encoded: bytes,
    fragments: tuple[tuple[bytes, bytes], ...],
) -> tuple[tuple[int, int, bytes], ...]:
    if not fragments:
        return ()
    replacements = dict(fragments)
    marker_prefix = b'"__guala_exact_canonical_fragment_'
    marker_suffix = b'__"'
    seen: set[bytes] = set()
    spans: list[tuple[int, int, bytes]] = []
    cursor = 0
    while True:
        marker_start = encoded.find(marker_prefix, cursor)
        if marker_start < 0:
            break
        marker_end = encoded.find(
            marker_suffix,
            marker_start + len(marker_prefix),
        )
        if marker_end < 0:
            raise RuntimeError(
                "canonical fragment marker collided with physical state"
            )
        marker_end += len(marker_suffix)
        marker = encoded[marker_start:marker_end]
        fragment = replacements.get(marker)
        if fragment is None or marker in seen:
            raise RuntimeError(
                "canonical fragment marker collided with physical state"
            )
        spans.append((marker_start, marker_end, fragment))
        seen.add(marker)
        cursor = marker_end
    if len(seen) != len(fragments):
        raise RuntimeError(
            "canonical fragment marker collided with physical state"
        )
    return tuple(spans)


def _canonical(value: object) -> bytes:
    encoded, fragments = _canonical_skeleton(value)
    spans = _canonical_fragment_spans(encoded, fragments)
    if not spans:
        return encoded
    assembled: list[bytes] = []
    cursor = 0
    for marker_start, marker_end, fragment in spans:
        assembled.append(encoded[cursor:marker_start])
        assembled.append(fragment)
        cursor = marker_end
    assembled.append(encoded[cursor:])
    return b"".join(assembled)


def _canonical_byte_count(value: object) -> int:
    encoded, fragments = _canonical_skeleton(value)
    spans = _canonical_fragment_spans(encoded, fragments)
    return len(encoded) + sum(
        len(fragment) - (marker_end - marker_start)
        for marker_start, marker_end, fragment in spans
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _authority_key(value: object) -> bytes:
    if isinstance(value, str):
        if len(value) > 4096:
            raise ValueError("embodiment authority key must be bounded and nonempty")
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        if len(value) > 4096:
            raise ValueError("embodiment authority key must be bounded and nonempty")
        result = bytes(value)
    else:
        raise ValueError("embodiment authority key must be bytes or text")
    if not result or len(result) > 4096:
        raise ValueError("embodiment authority key must be bounded and nonempty")
    return result


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES
    ):
        raise ValueError(f"{name} must be a bounded canonical identifier")
    return value


def _bounded_integer(
    value: object,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"{name} is outside its exact integer boundary")
    return value


def _sha256_identity(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(item not in "0123456789abcdef" for item in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _sign(key: bytes, domain: bytes, payload: Mapping[str, object]) -> str:
    return hmac.new(key, domain + _canonical(payload), hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class PositionMM:
    x: int
    y: int
    z: int = 0

    def verify(self) -> None:
        _bounded_integer(self.x, "position x", minimum=-(1 << 31), maximum=(1 << 31) - 1)
        _bounded_integer(self.y, "position y", minimum=-(1 << 31), maximum=(1 << 31) - 1)
        _bounded_integer(self.z, "position z", minimum=-(1 << 31), maximum=(1 << 31) - 1)

    def as_record(self) -> dict[str, int]:
        self.verify()
        return {"x_mm": self.x, "y_mm": self.y, "z_mm": self.z}


@dataclass(frozen=True, slots=True)
class PoseMM:
    position: PositionMM
    heading_millidegrees: int

    def verify(self) -> None:
        self.position.verify()
        _bounded_integer(
            self.heading_millidegrees,
            "body heading",
            minimum=0,
            maximum=359_999,
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "heading_millidegrees": self.heading_millidegrees,
            "position": self.position.as_record(),
        }


@dataclass(frozen=True, slots=True)
class RoomBoundsMM:
    minimum: PositionMM
    maximum: PositionMM

    def verify(self) -> None:
        self.minimum.verify()
        self.maximum.verify()
        if not (
            self.minimum.x < self.maximum.x
            and self.minimum.y < self.maximum.y
            and self.minimum.z <= self.maximum.z
        ):
            raise ValueError("room bounds are not ordered")

    def contains_floor_disc(self, position: PositionMM, radius_mm: int) -> bool:
        return (
            position.z == self.minimum.z
            and self.minimum.x + radius_mm <= position.x <= self.maximum.x - radius_mm
            and self.minimum.y + radius_mm <= position.y <= self.maximum.y - radius_mm
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "maximum": self.maximum.as_record(),
            "minimum": self.minimum.as_record(),
        }


def _physical_bands(value: object, name: str) -> tuple[int, ...]:
    if (
        not isinstance(value, tuple)
        or len(value) != OPTICAL_BANDS
        or any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or not 0 <= item <= MAX_PHYSICAL_PPM
            for item in value
        )
    ):
        raise ValueError(f"{name} must contain six bounded integer bands")
    return value


def _mass_channels(
    value: object,
    *,
    count: int,
    name: str,
) -> tuple[int, ...]:
    if (
        not isinstance(value, tuple)
        or len(value) != count
        or any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or not 0 <= item <= MAX_MATERIAL_MASS
            for item in value
        )
    ):
        raise ValueError(
            f"{name} must contain {count} bounded integer masses"
        )
    return value


def _positive_channels(
    value: object,
    *,
    count: int,
    name: str,
) -> tuple[int, ...]:
    result = _mass_channels(value, count=count, name=name)
    if any(item == 0 for item in result):
        raise ValueError(f"{name} must contain positive receptor capacities")
    return result


@dataclass(frozen=True, slots=True)
class AirVolumeState:
    volume_cubic_mm: int
    odorant_mass_nanograms: tuple[int, ...]

    def verify(self) -> None:
        _bounded_integer(
            self.volume_cubic_mm,
            "air volume",
            minimum=1,
            maximum=MAX_MATERIAL_MASS,
        )
        _mass_channels(
            self.odorant_mass_nanograms,
            count=ODORANT_CHANNELS,
            name="air odorant mass",
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "odorant_mass_nanograms": list(
                self.odorant_mass_nanograms
            ),
            "volume_cubic_mm": self.volume_cubic_mm,
        }


@dataclass(frozen=True, slots=True)
class ObjectMaterialState:
    odorant_reservoir_nanograms: tuple[int, ...]
    odorant_release_nanograms_per_second: tuple[int, ...]
    tastant_mass_micrograms: tuple[int, ...]
    surface_temperature_millikelvin: int
    compliance_ppm: int
    roughness_micrometers: int
    moisture_ppm: int

    def verify(self) -> None:
        _mass_channels(
            self.odorant_reservoir_nanograms,
            count=ODORANT_CHANNELS,
            name="object odorant reservoir",
        )
        _mass_channels(
            self.odorant_release_nanograms_per_second,
            count=ODORANT_CHANNELS,
            name="object odorant release",
        )
        _mass_channels(
            self.tastant_mass_micrograms,
            count=TASTANT_CHANNELS,
            name="object tastant mass",
        )
        _bounded_integer(
            self.surface_temperature_millikelvin,
            "object surface temperature",
            minimum=1,
            maximum=1_000_000,
        )
        _bounded_integer(
            self.compliance_ppm,
            "object compliance",
            minimum=0,
            maximum=MAX_PHYSICAL_PPM,
        )
        _bounded_integer(
            self.roughness_micrometers,
            "object roughness",
            minimum=0,
            maximum=1_000_000,
        )
        _bounded_integer(
            self.moisture_ppm,
            "object moisture",
            minimum=0,
            maximum=MAX_PHYSICAL_PPM,
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "compliance_ppm": self.compliance_ppm,
            "moisture_ppm": self.moisture_ppm,
            "odorant_release_nanograms_per_second": list(
                self.odorant_release_nanograms_per_second
            ),
            "odorant_reservoir_nanograms": list(
                self.odorant_reservoir_nanograms
            ),
            "roughness_micrometers": self.roughness_micrometers,
            "surface_temperature_millikelvin": (
                self.surface_temperature_millikelvin
            ),
            "tastant_mass_micrograms": list(
                self.tastant_mass_micrograms
            ),
        }


@dataclass(frozen=True, slots=True)
class _VerifiedOpticalSurfaceIntegrity:
    columns: int
    rows: int
    palette_reflectance_ppm: tuple[tuple[int, ...], ...]
    cell_palette_indices: tuple[int, ...]
    canonical_fragment: _CanonicalJsonFragment

    def matches(self, surface: "ObjectOpticalSurface") -> bool:
        return (
            surface.columns == self.columns
            and surface.rows == self.rows
            and surface.palette_reflectance_ppm
            is self.palette_reflectance_ppm
            and surface.cell_palette_indices is self.cell_palette_indices
        )


@dataclass(frozen=True, slots=True)
class ObjectOpticalSurface:
    """One exact bounded palette-indexed material reflectance surface."""

    columns: int
    rows: int
    palette_reflectance_ppm: tuple[tuple[int, ...], ...]
    cell_palette_indices: tuple[int, ...]
    _verified_integrity: _VerifiedOpticalSurfaceIntegrity | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        self._verify_unsealed()
        object.__setattr__(
            self,
            "_verified_integrity",
            _VerifiedOpticalSurfaceIntegrity(
                columns=self.columns,
                rows=self.rows,
                palette_reflectance_ppm=self.palette_reflectance_ppm,
                cell_palette_indices=self.cell_palette_indices,
                canonical_fragment=_CanonicalJsonFragment(
                    _canonical(
                        {
                            "cell_palette_indices": (
                                self.cell_palette_indices
                            ),
                            "columns": self.columns,
                            "palette_reflectance_ppm": (
                                self.palette_reflectance_ppm
                            ),
                            "rows": self.rows,
                        }
                    )
                ),
            ),
        )

    def _verify_unsealed(self) -> None:
        _bounded_integer(
            self.columns,
            "optical surface columns",
            minimum=1,
            maximum=MAX_OPTICAL_SURFACE_COLUMNS,
        )
        _bounded_integer(
            self.rows,
            "optical surface rows",
            minimum=1,
            maximum=MAX_OPTICAL_SURFACE_ROWS,
        )
        if (
            not isinstance(self.palette_reflectance_ppm, tuple)
            or not 2 <= len(self.palette_reflectance_ppm) <= (
                MAX_OPTICAL_SURFACE_PALETTE_ENTRIES
            )
            or any(
                not isinstance(reflectance, tuple)
                for reflectance in self.palette_reflectance_ppm
            )
        ):
            raise ValueError(
                "optical surface palette must contain two to 256 "
                "six-band reflectances"
            )
        for reflectance in self.palette_reflectance_ppm:
            _physical_bands(
                reflectance,
                "optical surface palette reflectance",
            )
        if len(set(self.palette_reflectance_ppm)) != len(
            self.palette_reflectance_ppm
        ):
            raise ValueError(
                "optical surface palette reflectances must be unique"
            )
        if (
            not isinstance(self.cell_palette_indices, tuple)
            or len(self.cell_palette_indices) != self.columns * self.rows
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value < len(self.palette_reflectance_ppm)
                for value in self.cell_palette_indices
            )
        ):
            raise ValueError(
                "optical surface cells must be exact bounded palette indices"
            )
        if set(self.cell_palette_indices) != set(
            range(len(self.palette_reflectance_ppm))
        ):
            raise ValueError(
                "optical surface palette contains an unused reflectance"
            )

    def verify(self) -> None:
        verified = self._verified_integrity
        if verified is None or not verified.matches(self):
            raise ValueError(
                "optical surface changed after verified construction"
            )

    def reflectance_at_ppm(
        self,
        *,
        row: int,
        column: int,
    ) -> tuple[int, ...]:
        self.verify()
        return self.reflectance_at_verified_ppm(
            row=row,
            column=column,
        )

    def reflectance_at_verified_ppm(
        self,
        *,
        row: int,
        column: int,
    ) -> tuple[int, ...]:
        """Read one cell after the enclosing trust boundary verified it."""

        _bounded_integer(
            row,
            "optical surface row",
            minimum=0,
            maximum=self.rows - 1,
        )
        _bounded_integer(
            column,
            "optical surface column",
            minimum=0,
            maximum=self.columns - 1,
        )
        palette_index = self.cell_palette_indices[
            row * self.columns + column
        ]
        return self.palette_reflectance_ppm[palette_index]

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "cell_palette_indices": list(self.cell_palette_indices),
            "columns": self.columns,
            "palette_reflectance_ppm": [
                list(reflectance)
                for reflectance in self.palette_reflectance_ppm
            ],
            "rows": self.rows,
        }

    def _canonical_fragment(self) -> _CanonicalJsonFragment:
        self.verify()
        verified = self._verified_integrity
        if verified is None:
            raise RuntimeError(
                "optical surface lost verified construction"
            )
        return verified.canonical_fragment


@dataclass(frozen=True, slots=True)
class BodyReceptorGeometry:
    retinal_offset_mm: PositionMM
    left_ear_offset_mm: PositionMM
    right_ear_offset_mm: PositionMM
    touch_offset_mm: PositionMM
    touch_radius_mm: int
    oral_offset_mm: PositionMM
    oral_radius_mm: int
    olfactory_offset_mm: PositionMM
    odorant_saturation_nanograms_per_cubic_meter: tuple[int, ...]
    tastant_saturation_micrograms: tuple[int, ...]
    touch_mass_span_grams: int
    touch_temperature_min_millikelvin: int
    touch_temperature_max_millikelvin: int
    touch_roughness_span_micrometers: int

    def verify(self) -> None:
        self.retinal_offset_mm.verify()
        self.left_ear_offset_mm.verify()
        self.right_ear_offset_mm.verify()
        self.touch_offset_mm.verify()
        self.oral_offset_mm.verify()
        self.olfactory_offset_mm.verify()
        for value, name in (
            (self.touch_radius_mm, "touch receptor radius"),
            (self.oral_radius_mm, "oral receptor radius"),
            (self.touch_mass_span_grams, "touch mass span"),
            (
                self.touch_roughness_span_micrometers,
                "touch roughness span",
            ),
        ):
            _bounded_integer(
                value,
                name,
                minimum=1,
                maximum=1_000_000_000,
            )
        _bounded_integer(
            self.touch_temperature_min_millikelvin,
            "touch temperature minimum",
            minimum=1,
            maximum=1_000_000,
        )
        _bounded_integer(
            self.touch_temperature_max_millikelvin,
            "touch temperature maximum",
            minimum=1,
            maximum=1_000_000,
        )
        if (
            self.touch_temperature_min_millikelvin
            >= self.touch_temperature_max_millikelvin
        ):
            raise ValueError("touch temperature span is not ordered")
        _positive_channels(
            self.odorant_saturation_nanograms_per_cubic_meter,
            count=ODORANT_CHANNELS,
            name="olfactory receptor saturation",
        )
        _positive_channels(
            self.tastant_saturation_micrograms,
            count=TASTANT_CHANNELS,
            name="gustatory receptor saturation",
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "left_ear_offset_mm": self.left_ear_offset_mm.as_record(),
            "odorant_saturation_nanograms_per_cubic_meter": list(
                self.odorant_saturation_nanograms_per_cubic_meter
            ),
            "olfactory_offset_mm": self.olfactory_offset_mm.as_record(),
            "oral_offset_mm": self.oral_offset_mm.as_record(),
            "oral_radius_mm": self.oral_radius_mm,
            "retinal_offset_mm": self.retinal_offset_mm.as_record(),
            "right_ear_offset_mm": self.right_ear_offset_mm.as_record(),
            "tastant_saturation_micrograms": list(
                self.tastant_saturation_micrograms
            ),
            "touch_mass_span_grams": self.touch_mass_span_grams,
            "touch_offset_mm": self.touch_offset_mm.as_record(),
            "touch_radius_mm": self.touch_radius_mm,
            "touch_roughness_span_micrometers": (
                self.touch_roughness_span_micrometers
            ),
            "touch_temperature_max_millikelvin": (
                self.touch_temperature_max_millikelvin
            ),
            "touch_temperature_min_millikelvin": (
                self.touch_temperature_min_millikelvin
            ),
        }


@dataclass(frozen=True, slots=True)
class BodyContactState:
    kind: str
    object_id: str
    contact_patch_square_mm: int
    duration_microseconds: int

    def verify(self) -> None:
        if self.kind not in {"touch", "oral"}:
            raise ValueError("body contact kind changed")
        _identifier(self.object_id, "body contact object")
        _bounded_integer(
            self.contact_patch_square_mm,
            "body contact patch",
            minimum=1,
            maximum=1_000_000_000,
        )
        _bounded_integer(
            self.duration_microseconds,
            "body contact duration",
            minimum=MIN_MATERIAL_ACTION_DURATION_US,
            maximum=MAX_MATERIAL_ACTION_DURATION_US,
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "contact_patch_square_mm": self.contact_patch_square_mm,
            "duration_microseconds": self.duration_microseconds,
            "kind": self.kind,
            "object_id": self.object_id,
        }


@dataclass(frozen=True, slots=True)
class PhysicalRegion:
    region_id: str
    bounds: RoomBoundsMM
    ceiling_height_mm: int | None
    reflectance_ppm: tuple[int, ...]
    illumination_ppm: tuple[int, ...]
    air: AirVolumeState | None = None

    def verify(self) -> None:
        _identifier(self.region_id, "physical region id")
        self.bounds.verify()
        if self.ceiling_height_mm is not None:
            _bounded_integer(
                self.ceiling_height_mm,
                "physical ceiling height",
                minimum=1,
                maximum=(1 << 31) - 1,
            )
            if self.ceiling_height_mm > self.bounds.maximum.z:
                raise ValueError("physical ceiling exceeds region volume")
        _physical_bands(self.reflectance_ppm, "region reflectance")
        _physical_bands(self.illumination_ppm, "region illumination")
        if self.air is not None:
            self.air.verify()
            expected_volume = (
                (self.bounds.maximum.x - self.bounds.minimum.x)
                * (self.bounds.maximum.y - self.bounds.minimum.y)
                * (self.bounds.maximum.z - self.bounds.minimum.z)
            )
            if self.air.volume_cubic_mm != expected_volume:
                raise ValueError(
                    "signed air volume differs from region geometry"
                )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "bounds": self.bounds.as_record(),
            "ceiling_height_mm": self.ceiling_height_mm,
            "illumination_ppm": list(self.illumination_ppm),
            "reflectance_ppm": list(self.reflectance_ppm),
            "region_id": self.region_id,
            "air": self.air.as_record() if self.air is not None else None,
        }


@dataclass(frozen=True, slots=True)
class PhysicalPortal:
    portal_id: str
    region_ids: tuple[str, str]
    axis: str
    plane_mm: int
    aperture_min_mm: int
    aperture_max_mm: int
    height_mm: int
    air_flow_cubic_mm_per_second: int | None = None

    def verify(self) -> None:
        _identifier(self.portal_id, "physical portal id")
        if (
            not isinstance(self.region_ids, tuple)
            or len(self.region_ids) != 2
            or self.region_ids != tuple(sorted(self.region_ids))
            or len(set(self.region_ids)) != 2
        ):
            raise ValueError("portal region pair is not canonical")
        for value in self.region_ids:
            _identifier(value, "portal region id")
        if self.axis not in {"x", "y"}:
            raise ValueError("portal axis must be x or y")
        for value, name in (
            (self.plane_mm, "portal plane"),
            (self.aperture_min_mm, "portal aperture minimum"),
            (self.aperture_max_mm, "portal aperture maximum"),
            (self.height_mm, "portal height"),
        ):
            _bounded_integer(
                value, name, minimum=-(1 << 31), maximum=(1 << 31) - 1
            )
        if (
            self.aperture_min_mm >= self.aperture_max_mm
            or self.height_mm <= 0
        ):
            raise ValueError("portal aperture is not physically ordered")
        if self.air_flow_cubic_mm_per_second is not None:
            _bounded_integer(
                self.air_flow_cubic_mm_per_second,
                "portal air flow",
                minimum=1,
                maximum=MAX_MATERIAL_MASS,
            )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "aperture_max_mm": self.aperture_max_mm,
            "aperture_min_mm": self.aperture_min_mm,
            "axis": self.axis,
            "height_mm": self.height_mm,
            "plane_mm": self.plane_mm,
            "portal_id": self.portal_id,
            "region_ids": list(self.region_ids),
            "air_flow_cubic_mm_per_second": (
                self.air_flow_cubic_mm_per_second
            ),
        }


@dataclass(frozen=True, slots=True)
class EmbodiedBody:
    body_id: str
    pose: PoseMM
    radius_mm: int
    reach_mm: int
    held_object_id: str | None = None
    receptor_geometry: BodyReceptorGeometry | None = None
    active_contact: BodyContactState | None = None

    def verify(self) -> None:
        _identifier(self.body_id, "body id")
        self.pose.verify()
        _bounded_integer(self.radius_mm, "body radius", minimum=1, maximum=1_000_000)
        _bounded_integer(self.reach_mm, "body reach", minimum=1, maximum=1_000_000)
        if self.held_object_id is not None:
            _identifier(self.held_object_id, "held object id")
        if self.receptor_geometry is not None:
            self.receptor_geometry.verify()
        if self.active_contact is not None:
            self.active_contact.verify()

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "body_id": self.body_id,
            "held_object_id": self.held_object_id,
            "pose": self.pose.as_record(),
            "radius_mm": self.radius_mm,
            "reach_mm": self.reach_mm,
            "active_contact": (
                self.active_contact.as_record()
                if self.active_contact is not None
                else None
            ),
            "receptor_geometry": (
                self.receptor_geometry.as_record()
                if self.receptor_geometry is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class EmbodiedObject:
    object_id: str
    radius_mm: int
    mass_grams: int
    position: PositionMM | None
    held_by_body_id: str | None = None
    reflectance_ppm: tuple[int, ...] = (
        500_000, 500_000, 500_000, 500_000, 500_000, 500_000
    )
    material: ObjectMaterialState | None = None
    optical_surface: ObjectOpticalSurface | None = None

    def verify(self) -> None:
        _identifier(self.object_id, "object id")
        _bounded_integer(self.radius_mm, "object radius", minimum=1, maximum=1_000_000)
        _bounded_integer(self.mass_grams, "object mass", minimum=1, maximum=1_000_000_000)
        if (self.position is None) == (self.held_by_body_id is None):
            raise ValueError("object must be either placed or held")
        if self.position is not None:
            self.position.verify()
        if self.held_by_body_id is not None:
            _identifier(self.held_by_body_id, "holding body id")
        _physical_bands(self.reflectance_ppm, "object reflectance")
        if self.material is not None:
            self.material.verify()
        if self.optical_surface is not None:
            self.optical_surface.verify()

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "held_by_body_id": self.held_by_body_id,
            "mass_grams": self.mass_grams,
            "object_id": self.object_id,
            "position": self.position.as_record() if self.position is not None else None,
            "radius_mm": self.radius_mm,
            "reflectance_ppm": list(self.reflectance_ppm),
            "material": (
                self.material.as_record()
                if self.material is not None
                else None
            ),
            "optical_surface": (
                self.optical_surface.as_record()
                if self.optical_surface is not None
                else None
            ),
        }

    def _canonical_record(self) -> dict[str, object]:
        self.verify()
        return {
            "held_by_body_id": self.held_by_body_id,
            "mass_grams": self.mass_grams,
            "object_id": self.object_id,
            "position": self.position.as_record() if self.position is not None else None,
            "radius_mm": self.radius_mm,
            "reflectance_ppm": list(self.reflectance_ppm),
            "material": (
                self.material.as_record() if self.material is not None else None
            ),
            "optical_surface": (
                self.optical_surface._canonical_fragment()
                if self.optical_surface is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class EmbodimentPort:
    port_id: str
    actor_body_id: str

    def verify(self) -> None:
        _identifier(self.port_id, "embodiment port id")
        _identifier(self.actor_body_id, "embodiment port actor body id")

    def as_record(self) -> dict[str, str]:
        self.verify()
        return {
            "actor_body_id": self.actor_body_id,
            "port_id": self.port_id,
        }


@dataclass(frozen=True, slots=True)
class MoveCommand:
    target_pose: PoseMM
    duration_microseconds: int


@dataclass(frozen=True, slots=True)
class PickCommand:
    object_id: str
    duration_microseconds: int


@dataclass(frozen=True, slots=True)
class PlaceCommand:
    object_id: str
    target_position: PositionMM
    duration_microseconds: int


@dataclass(frozen=True, slots=True)
class VocalizeCommand:
    """One bounded physical pressure actuation by the addressed body."""

    epoch_commitment_sha256: str
    sequence: int
    source_sample_start: int
    pcm_sha256: str
    sample_count: int


@dataclass(frozen=True, slots=True)
class TouchContactCommand:
    object_id: str
    duration_microseconds: int


@dataclass(frozen=True, slots=True)
class OralContactCommand:
    object_id: str
    duration_microseconds: int


@dataclass(frozen=True, slots=True)
class AdvancePhysicalTimeCommand:
    duration_microseconds: int


EmbodimentCommand = (
    MoveCommand
    | PickCommand
    | PlaceCommand
    | VocalizeCommand
    | TouchContactCommand
    | OralContactCommand
    | AdvancePhysicalTimeCommand
)


def command_record(command: EmbodimentCommand) -> dict[str, object]:
    if isinstance(command, MoveCommand):
        command.target_pose.verify()
        return {
            "duration_microseconds": _bounded_integer(
                command.duration_microseconds,
                "physical action duration",
                minimum=MIN_MATERIAL_ACTION_DURATION_US,
                maximum=MAX_MATERIAL_ACTION_DURATION_US,
            ),
            "operation": "move",
            "schema": COMMAND_SCHEMA,
            "target_pose": command.target_pose.as_record(),
        }
    if isinstance(command, PickCommand):
        return {
            "duration_microseconds": _bounded_integer(
                command.duration_microseconds,
                "physical action duration",
                minimum=MIN_MATERIAL_ACTION_DURATION_US,
                maximum=MAX_MATERIAL_ACTION_DURATION_US,
            ),
            "object_id": _identifier(command.object_id, "pick object id"),
            "operation": "pick",
            "schema": COMMAND_SCHEMA,
        }
    if isinstance(command, PlaceCommand):
        command.target_position.verify()
        return {
            "duration_microseconds": _bounded_integer(
                command.duration_microseconds,
                "physical action duration",
                minimum=MIN_MATERIAL_ACTION_DURATION_US,
                maximum=MAX_MATERIAL_ACTION_DURATION_US,
            ),
            "object_id": _identifier(command.object_id, "place object id"),
            "operation": "place",
            "schema": COMMAND_SCHEMA,
            "target_position": command.target_position.as_record(),
        }
    if isinstance(command, VocalizeCommand):
        sample_count = _bounded_integer(
            command.sample_count,
            "vocal sample count",
            minimum=MIN_VOCAL_SAMPLE_COUNT,
            maximum=MAX_VOCAL_SAMPLE_COUNT,
        )
        return {
            "epoch_commitment_sha256": _sha256_identity(
                command.epoch_commitment_sha256,
                "vocal epoch commitment",
            ),
            "operation": "vocalize",
            "pcm_sha256": _sha256_identity(
                command.pcm_sha256, "vocal pressure identity"
            ),
            "sample_count": sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "sequence": _bounded_integer(
                command.sequence,
                "vocal sequence",
                minimum=0,
                maximum=MAX_REVISION,
            ),
            "schema": COMMAND_SCHEMA,
            "source_sample_start": _bounded_integer(
                command.source_sample_start,
                "vocal source sample start",
                minimum=0,
                maximum=MAX_REVISION - sample_count,
            ),
        }
    if isinstance(command, (TouchContactCommand, OralContactCommand)):
        return {
            "duration_microseconds": _bounded_integer(
                command.duration_microseconds,
                "material action duration",
                minimum=MIN_MATERIAL_ACTION_DURATION_US,
                maximum=MAX_MATERIAL_ACTION_DURATION_US,
            ),
            "object_id": _identifier(
                command.object_id,
                "material contact object id",
            ),
            "operation": (
                "oral_contact"
                if isinstance(command, OralContactCommand)
                else "touch_contact"
            ),
            "schema": COMMAND_SCHEMA,
        }
    if isinstance(command, AdvancePhysicalTimeCommand):
        return {
            "duration_microseconds": _bounded_integer(
                command.duration_microseconds,
                "physical time duration",
                minimum=MIN_MATERIAL_ACTION_DURATION_US,
                maximum=MAX_MATERIAL_ACTION_DURATION_US,
            ),
            "operation": "advance_physical_time",
            "schema": COMMAND_SCHEMA,
        }
    raise ValueError("unsupported embodiment command type")


def encode_command(command: EmbodimentCommand) -> bytes:
    """Encode one typed command into the exact opaque port payload."""

    return _canonical(command_record(command))


def _command_elapsed_nanoseconds(
    command: EmbodimentCommand,
) -> int:
    if isinstance(
        command,
        (
            MoveCommand,
            PickCommand,
            PlaceCommand,
            TouchContactCommand,
            OralContactCommand,
            AdvancePhysicalTimeCommand,
        ),
    ):
        return command.duration_microseconds * 1_000
    if isinstance(command, VocalizeCommand):
        return (
            command.sample_count
            * 1_000_000_000
            // VOCAL_SAMPLE_RATE_HZ
        )
    return 0


def _position_from(value: object, name: str) -> PositionMM:
    if not isinstance(value, Mapping) or set(value) != {"x_mm", "y_mm", "z_mm"}:
        raise ValueError(f"{name} fields changed")
    result = PositionMM(x=value.get("x_mm"), y=value.get("y_mm"), z=value.get("z_mm"))
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError(f"{name} is not canonical")
    return result


def _pose_from(value: object, name: str) -> PoseMM:
    if not isinstance(value, Mapping) or set(value) != {"heading_millidegrees", "position"}:
        raise ValueError(f"{name} fields changed")
    result = PoseMM(
        position=_position_from(value.get("position"), f"{name} position"),
        heading_millidegrees=value.get("heading_millidegrees"),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError(f"{name} is not canonical")
    return result


def decode_command(payload: bytes, *, max_command_bytes: int = DEFAULT_MAX_COMMAND_BYTES) -> EmbodimentCommand:
    """Decode only the canonical typed command language owned by this port."""

    if not isinstance(payload, bytes) or not payload or len(payload) > max_command_bytes:
        raise ValueError("embodiment command exceeds its exact byte boundary")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("embodiment command is not canonical JSON") from error
    if not isinstance(decoded, Mapping) or decoded.get("schema") != COMMAND_SCHEMA:
        raise ValueError("embodiment command schema changed")
    operation = decoded.get("operation")
    if operation == "move" and set(decoded) == {
        "duration_microseconds", "operation", "schema", "target_pose"
    }:
        result: EmbodimentCommand = MoveCommand(
            _pose_from(decoded.get("target_pose"), "move target pose"),
            _bounded_integer(
                decoded.get("duration_microseconds"),
                "physical action duration",
                minimum=MIN_MATERIAL_ACTION_DURATION_US,
                maximum=MAX_MATERIAL_ACTION_DURATION_US,
            ),
        )
    elif operation == "pick" and set(decoded) == {
        "duration_microseconds", "object_id", "operation", "schema"
    }:
        result = PickCommand(
            _identifier(decoded.get("object_id"), "pick object id"),
            _bounded_integer(
                decoded.get("duration_microseconds"),
                "physical action duration",
                minimum=MIN_MATERIAL_ACTION_DURATION_US,
                maximum=MAX_MATERIAL_ACTION_DURATION_US,
            ),
        )
    elif operation == "place" and set(decoded) == {
        "duration_microseconds", "object_id", "operation", "schema",
        "target_position"
    }:
        result = PlaceCommand(
            _identifier(decoded.get("object_id"), "place object id"),
            _position_from(decoded.get("target_position"), "place target position"),
            _bounded_integer(
                decoded.get("duration_microseconds"),
                "physical action duration",
                minimum=MIN_MATERIAL_ACTION_DURATION_US,
                maximum=MAX_MATERIAL_ACTION_DURATION_US,
            ),
        )
    elif operation == "vocalize" and set(decoded) == {
        "epoch_commitment_sha256", "operation", "pcm_sha256", "sample_count",
        "sample_rate_hz", "schema", "sequence", "source_sample_start"
    }:
        if decoded.get("sample_rate_hz") != VOCAL_SAMPLE_RATE_HZ:
            raise ValueError("vocal sample rate changed")
        result = VocalizeCommand(
            epoch_commitment_sha256=_sha256_identity(
                decoded.get("epoch_commitment_sha256"),
                "vocal epoch commitment",
            ),
            sequence=_bounded_integer(
                decoded.get("sequence"),
                "vocal sequence",
                minimum=0,
                maximum=MAX_REVISION,
            ),
            source_sample_start=_bounded_integer(
                decoded.get("source_sample_start"),
                "vocal source sample start",
                minimum=0,
                maximum=MAX_REVISION - _bounded_integer(
                    decoded.get("sample_count"),
                    "vocal sample count",
                    minimum=MIN_VOCAL_SAMPLE_COUNT,
                    maximum=MAX_VOCAL_SAMPLE_COUNT,
                ),
            ),
            pcm_sha256=_sha256_identity(
                decoded.get("pcm_sha256"), "vocal pressure identity"
            ),
            sample_count=_bounded_integer(
                decoded.get("sample_count"),
                "vocal sample count",
                minimum=MIN_VOCAL_SAMPLE_COUNT,
                maximum=MAX_VOCAL_SAMPLE_COUNT,
            ),
        )
    elif operation in {"touch_contact", "oral_contact"} and set(
        decoded
    ) == {
        "duration_microseconds",
        "object_id",
        "operation",
        "schema",
    }:
        object_id = _identifier(
            decoded.get("object_id"),
            "material contact object id",
        )
        duration = _bounded_integer(
            decoded.get("duration_microseconds"),
            "material action duration",
            minimum=MIN_MATERIAL_ACTION_DURATION_US,
            maximum=MAX_MATERIAL_ACTION_DURATION_US,
        )
        result = (
            OralContactCommand(object_id, duration)
            if operation == "oral_contact"
            else TouchContactCommand(object_id, duration)
        )
    elif operation == "advance_physical_time" and set(decoded) == {
        "duration_microseconds",
        "operation",
        "schema",
    }:
        result = AdvancePhysicalTimeCommand(
            _bounded_integer(
                decoded.get("duration_microseconds"),
                "physical time duration",
                minimum=MIN_MATERIAL_ACTION_DURATION_US,
                maximum=MAX_MATERIAL_ACTION_DURATION_US,
            )
        )
    else:
        raise ValueError("embodiment command operation or fields changed")
    if encode_command(result) != payload:
        raise ValueError("embodiment command bytes are not canonical")
    return result


@dataclass(frozen=True, slots=True)
class _WorldState:
    revision: int
    room_id: str
    room_bounds: RoomBoundsMM
    regions: tuple[PhysicalRegion, ...]
    portals: tuple[PhysicalPortal, ...]
    self_body_id: str
    bodies: tuple[EmbodiedBody, ...]
    objects: tuple[EmbodiedObject, ...]

    def as_record(self) -> dict[str, object]:
        return {
            "bodies": [item.as_record() for item in self.bodies],
            "objects": [item.as_record() for item in self.objects],
            "revision": self.revision,
            "room_bounds": self.room_bounds.as_record(),
            "room_id": self.room_id,
            "regions": [item.as_record() for item in self.regions],
            "portals": [item.as_record() for item in self.portals],
            "self_body_id": self.self_body_id,
        }

    def _canonical_record(self) -> dict[str, object]:
        return {
            "bodies": [item.as_record() for item in self.bodies],
            "objects": [item._canonical_record() for item in self.objects],
            "revision": self.revision,
            "room_bounds": self.room_bounds.as_record(),
            "room_id": self.room_id,
            "regions": [item.as_record() for item in self.regions],
            "portals": [item.as_record() for item in self.portals],
            "self_body_id": self.self_body_id,
        }


@dataclass(frozen=True, slots=True)
class ObservationSnapshot:
    revision: int
    room_id: str
    room_bounds: RoomBoundsMM
    regions: tuple[PhysicalRegion, ...]
    portals: tuple[PhysicalPortal, ...]
    self_body_id: str
    bodies: tuple[EmbodiedBody, ...]
    objects: tuple[EmbodiedObject, ...]
    state_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "bodies": [item.as_record() for item in self.bodies],
            "objects": [item.as_record() for item in self.objects],
            "revision": self.revision,
            "room_bounds": self.room_bounds.as_record(),
            "room_id": self.room_id,
            "regions": [item.as_record() for item in self.regions],
            "portals": [item.as_record() for item in self.portals],
            "schema": OBSERVATION_SCHEMA,
            "self_body_id": self.self_body_id,
            "state_sha256": self.state_sha256,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def _canonical_unsigned_record(self) -> dict[str, object]:
        return {
            "bodies": [item.as_record() for item in self.bodies],
            "objects": [item._canonical_record() for item in self.objects],
            "revision": self.revision,
            "room_bounds": self.room_bounds.as_record(),
            "room_id": self.room_id,
            "regions": [item.as_record() for item in self.regions],
            "portals": [item.as_record() for item in self.portals],
            "schema": OBSERVATION_SCHEMA,
            "self_body_id": self.self_body_id,
            "state_sha256": self.state_sha256,
        }

    def _canonical_record(self) -> dict[str, object]:
        return {
            **self._canonical_unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class ActionExecutionReceipt:
    port_id: str
    actor_body_id: str | None
    causal_intent_receipt_sha256: str
    command_sha256: str
    expected_revision: int
    observed_revision: int
    disposition: str
    reason: str
    elapsed_nanoseconds: int
    lifecycle: tuple[str, ...]
    before: ObservationSnapshot
    after: ObservationSnapshot
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "actor_body_id": self.actor_body_id,
            "after": self.after.as_record(),
            "before": self.before.as_record(),
            "causal_intent_receipt_sha256": self.causal_intent_receipt_sha256,
            "command_sha256": self.command_sha256,
            "disposition": self.disposition,
            "elapsed_nanoseconds": self.elapsed_nanoseconds,
            "expected_revision": self.expected_revision,
            "lifecycle": list(self.lifecycle),
            "observed_revision": self.observed_revision,
            "port_id": self.port_id,
            "reason": self.reason,
            "schema": EXECUTION_SCHEMA,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def _canonical_unsigned_record(self) -> dict[str, object]:
        return {
            "actor_body_id": self.actor_body_id,
            "after": self.after._canonical_record(),
            "before": self.before._canonical_record(),
            "causal_intent_receipt_sha256": self.causal_intent_receipt_sha256,
            "command_sha256": self.command_sha256,
            "disposition": self.disposition,
            "elapsed_nanoseconds": self.elapsed_nanoseconds,
            "expected_revision": self.expected_revision,
            "lifecycle": list(self.lifecycle),
            "observed_revision": self.observed_revision,
            "port_id": self.port_id,
            "reason": self.reason,
            "schema": EXECUTION_SCHEMA,
        }

    def _canonical_record(self) -> dict[str, object]:
        return {
            **self._canonical_unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class _AuthorityState:
    world: _WorldState
    observation: ObservationSnapshot
    recent_applied_receipts: tuple[ActionExecutionReceipt, ...]
    migration_receipt: "WorldMigrationReceipt | None" = None


_PREPARED_ACTION_EXECUTION_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class PreparedActionExecution:
    """One verified world transition held outside live physical state."""

    execution_receipt: ActionExecutionReceipt
    _prior_state: _AuthorityState = field(repr=False)
    _candidate_state: _AuthorityState = field(repr=False)
    _construction_authority: object = field(repr=False)


@dataclass(frozen=True, slots=True)
class WorldMigrationReceipt:
    prior_envelope_sha256: str
    prior_observation_receipt_sha256: str
    resulting_observation_receipt_sha256: str
    prior_revision: int
    resulting_revision: int
    parent_migration_receipt_sha256: str | None
    manifest_sha256: str
    prior_topology_sha256: str
    resulting_topology_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "manifest_sha256": self.manifest_sha256,
            "parent_migration_receipt_sha256": (
                self.parent_migration_receipt_sha256
            ),
            "prior_envelope_sha256": self.prior_envelope_sha256,
            "prior_observation_receipt_sha256": (
                self.prior_observation_receipt_sha256
            ),
            "prior_revision": self.prior_revision,
            "resulting_observation_receipt_sha256": (
                self.resulting_observation_receipt_sha256
            ),
            "resulting_revision": self.resulting_revision,
            "prior_topology_sha256": self.prior_topology_sha256,
            "resulting_topology_sha256": self.resulting_topology_sha256,
            "schema": MIGRATION_SCHEMA,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


def _distance_squared(left: PositionMM, right: PositionMM) -> int:
    return (left.x - right.x) ** 2 + (left.y - right.y) ** 2 + (left.z - right.z) ** 2


def _receptor_position(
    body: EmbodiedBody,
    offset: PositionMM,
) -> PositionMM:
    dx, dy = rotate_lattice_offset(
        offset.x,
        offset.y,
        body.pose.heading_millidegrees,
    )
    return PositionMM(
        body.pose.position.x + dx,
        body.pose.position.y + dy,
        body.pose.position.z + offset.z,
    )


def _derived_contact_patch_square_mm(
    *,
    receptor_position: PositionMM,
    receptor_radius_mm: int,
    object_position: PositionMM,
    object_radius_mm: int,
) -> int | None:
    distance_squared = _distance_squared(
        receptor_position,
        object_position,
    )
    combined = receptor_radius_mm + object_radius_mm
    if distance_squared > combined * combined:
        return None
    overlap = combined - isqrt(distance_squared)
    patch_radius = min(
        receptor_radius_mm,
        object_radius_mm,
        max(1, overlap),
    )
    return patch_radius * patch_radius


def _floor_discs_overlap(left: PositionMM, left_radius: int, right: PositionMM, right_radius: int) -> bool:
    distance = (left.x - right.x) ** 2 + (left.y - right.y) ** 2
    return distance < (left_radius + right_radius) ** 2


def _straight_path_intersects_disc(
    start: PositionMM,
    finish: PositionMM,
    obstacle: PositionMM,
    combined_radius: int,
) -> bool:
    """Exact line-segment/disc intersection with integer arithmetic."""

    dx = finish.x - start.x
    dy = finish.y - start.y
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return _floor_discs_overlap(start, 0, obstacle, combined_radius)
    ox = obstacle.x - start.x
    oy = obstacle.y - start.y
    projection = ox * dx + oy * dy
    if projection <= 0:
        return ox * ox + oy * oy < combined_radius * combined_radius
    if projection >= length_squared:
        ex = obstacle.x - finish.x
        ey = obstacle.y - finish.y
        return ex * ex + ey * ey < combined_radius * combined_radius
    cross = ox * dy - oy * dx
    return cross * cross < combined_radius * combined_radius * length_squared


def _room_from(value: object) -> RoomBoundsMM:
    if not isinstance(value, Mapping) or set(value) != {"maximum", "minimum"}:
        raise ValueError("room bounds fields changed")
    result = RoomBoundsMM(
        minimum=_position_from(value.get("minimum"), "room minimum"),
        maximum=_position_from(value.get("maximum"), "room maximum"),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("room bounds are not canonical")
    return result


def _air_from(value: object) -> AirVolumeState:
    expected = {"odorant_mass_nanograms", "volume_cubic_mm"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("air volume fields changed")
    raw_mass = value.get("odorant_mass_nanograms")
    result = AirVolumeState(
        volume_cubic_mm=value.get("volume_cubic_mm"),
        odorant_mass_nanograms=_mass_channels(
            tuple(raw_mass) if isinstance(raw_mass, list) else raw_mass,
            count=ODORANT_CHANNELS,
            name="air odorant mass",
        ),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("air volume record is not canonical")
    return result


def _material_from(value: object) -> ObjectMaterialState:
    expected = {
        "compliance_ppm",
        "moisture_ppm",
        "odorant_release_nanograms_per_second",
        "odorant_reservoir_nanograms",
        "roughness_micrometers",
        "surface_temperature_millikelvin",
        "tastant_mass_micrograms",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("object material fields changed")

    def channels(field: str, count: int) -> tuple[int, ...]:
        raw = value.get(field)
        return _mass_channels(
            tuple(raw) if isinstance(raw, list) else raw,
            count=count,
            name=field,
        )

    result = ObjectMaterialState(
        odorant_reservoir_nanograms=channels(
            "odorant_reservoir_nanograms",
            ODORANT_CHANNELS,
        ),
        odorant_release_nanograms_per_second=channels(
            "odorant_release_nanograms_per_second",
            ODORANT_CHANNELS,
        ),
        tastant_mass_micrograms=channels(
            "tastant_mass_micrograms",
            TASTANT_CHANNELS,
        ),
        surface_temperature_millikelvin=value.get(
            "surface_temperature_millikelvin"
        ),
        compliance_ppm=value.get("compliance_ppm"),
        roughness_micrometers=value.get("roughness_micrometers"),
        moisture_ppm=value.get("moisture_ppm"),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("object material record is not canonical")
    return result


def _receptor_geometry_from(value: object) -> BodyReceptorGeometry:
    expected = {
        "left_ear_offset_mm",
        "odorant_saturation_nanograms_per_cubic_meter",
        "olfactory_offset_mm",
        "oral_offset_mm",
        "oral_radius_mm",
        "retinal_offset_mm",
        "right_ear_offset_mm",
        "tastant_saturation_micrograms",
        "touch_mass_span_grams",
        "touch_offset_mm",
        "touch_radius_mm",
        "touch_roughness_span_micrometers",
        "touch_temperature_max_millikelvin",
        "touch_temperature_min_millikelvin",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("body receptor geometry fields changed")
    raw_odor = value.get(
        "odorant_saturation_nanograms_per_cubic_meter"
    )
    raw_taste = value.get("tastant_saturation_micrograms")
    result = BodyReceptorGeometry(
        retinal_offset_mm=_position_from(
            value.get("retinal_offset_mm"),
            "retinal receptor offset",
        ),
        left_ear_offset_mm=_position_from(
            value.get("left_ear_offset_mm"),
            "left ear receptor offset",
        ),
        right_ear_offset_mm=_position_from(
            value.get("right_ear_offset_mm"),
            "right ear receptor offset",
        ),
        touch_offset_mm=_position_from(
            value.get("touch_offset_mm"),
            "touch receptor offset",
        ),
        touch_radius_mm=value.get("touch_radius_mm"),
        oral_offset_mm=_position_from(
            value.get("oral_offset_mm"),
            "oral receptor offset",
        ),
        oral_radius_mm=value.get("oral_radius_mm"),
        olfactory_offset_mm=_position_from(
            value.get("olfactory_offset_mm"),
            "olfactory receptor offset",
        ),
        odorant_saturation_nanograms_per_cubic_meter=(
            _positive_channels(
                tuple(raw_odor)
                if isinstance(raw_odor, list)
                else raw_odor,
                count=ODORANT_CHANNELS,
                name="olfactory receptor saturation",
            )
        ),
        tastant_saturation_micrograms=_positive_channels(
            tuple(raw_taste)
            if isinstance(raw_taste, list)
            else raw_taste,
            count=TASTANT_CHANNELS,
            name="gustatory receptor saturation",
        ),
        touch_mass_span_grams=value.get("touch_mass_span_grams"),
        touch_temperature_min_millikelvin=value.get(
            "touch_temperature_min_millikelvin"
        ),
        touch_temperature_max_millikelvin=value.get(
            "touch_temperature_max_millikelvin"
        ),
        touch_roughness_span_micrometers=value.get(
            "touch_roughness_span_micrometers"
        ),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("body receptor geometry is not canonical")
    return result


def _contact_from(value: object) -> BodyContactState:
    expected = {
        "contact_patch_square_mm",
        "duration_microseconds",
        "kind",
        "object_id",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("body contact fields changed")
    result = BodyContactState(
        kind=value.get("kind"),
        object_id=value.get("object_id"),
        contact_patch_square_mm=value.get(
            "contact_patch_square_mm"
        ),
        duration_microseconds=value.get("duration_microseconds"),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("body contact record is not canonical")
    return result


def _body_from(value: object) -> EmbodiedBody:
    expected = {
        "active_contact",
        "body_id",
        "held_object_id",
        "pose",
        "radius_mm",
        "reach_mm",
        "receptor_geometry",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("body fields changed")
    receptor = value.get("receptor_geometry")
    contact = value.get("active_contact")
    result = EmbodiedBody(
        body_id=value.get("body_id"),
        held_object_id=value.get("held_object_id"),
        pose=_pose_from(value.get("pose"), "body pose"),
        radius_mm=value.get("radius_mm"),
        reach_mm=value.get("reach_mm"),
        receptor_geometry=(
            _receptor_geometry_from(receptor)
            if receptor is not None
            else None
        ),
        active_contact=(
            _contact_from(contact) if contact is not None else None
        ),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("body record is not canonical")
    return result


def _optical_surface_from(value: object) -> ObjectOpticalSurface:
    expected = {
        "cell_palette_indices",
        "columns",
        "palette_reflectance_ppm",
        "rows",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("object optical surface fields changed")
    raw_indices = value.get("cell_palette_indices")
    raw_palette = value.get("palette_reflectance_ppm")
    if (
        not isinstance(raw_palette, list)
        or any(not isinstance(item, list) for item in raw_palette)
    ):
        raise ValueError("object optical surface palette changed")
    result = ObjectOpticalSurface(
        columns=value.get("columns"),
        rows=value.get("rows"),
        palette_reflectance_ppm=tuple(
            _physical_bands(
                tuple(item),
                "optical surface palette reflectance",
            )
            for item in raw_palette
        ),
        cell_palette_indices=(
            tuple(raw_indices)
            if isinstance(raw_indices, list)
            else raw_indices
        ),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("object optical surface record is not canonical")
    return result


def _object_from(value: object) -> EmbodiedObject:
    expected = {
        "held_by_body_id", "mass_grams", "material", "object_id", "position",
        "radius_mm", "reflectance_ppm", "optical_surface"
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("object fields changed")
    raw_position = value.get("position")
    raw_material = value.get("material")
    raw_optical_surface = value.get("optical_surface")
    result = EmbodiedObject(
        object_id=value.get("object_id"),
        radius_mm=value.get("radius_mm"),
        mass_grams=value.get("mass_grams"),
        position=_position_from(raw_position, "object position") if raw_position is not None else None,
        held_by_body_id=value.get("held_by_body_id"),
        reflectance_ppm=_physical_bands(
            tuple(value.get("reflectance_ppm"))
            if isinstance(value.get("reflectance_ppm"), list)
            else value.get("reflectance_ppm"),
            "object reflectance",
        ),
        material=(
            _material_from(raw_material)
            if raw_material is not None
            else None
        ),
        optical_surface=(
            _optical_surface_from(raw_optical_surface)
            if raw_optical_surface is not None
            else None
        ),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("object record is not canonical")
    return result


def _v5_object_from(value: object) -> EmbodiedObject:
    expected = {
        "held_by_body_id",
        "mass_grams",
        "material",
        "object_id",
        "position",
        "radius_mm",
        "reflectance_ppm",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("v5 object fields changed")
    raw_position = value.get("position")
    raw_material = value.get("material")
    result = EmbodiedObject(
        object_id=value.get("object_id"),
        radius_mm=value.get("radius_mm"),
        mass_grams=value.get("mass_grams"),
        position=(
            _position_from(raw_position, "v5 object position")
            if raw_position is not None
            else None
        ),
        held_by_body_id=value.get("held_by_body_id"),
        reflectance_ppm=_physical_bands(
            tuple(value.get("reflectance_ppm"))
            if isinstance(value.get("reflectance_ppm"), list)
            else value.get("reflectance_ppm"),
            "v5 object reflectance",
        ),
        material=(
            _material_from(raw_material)
            if raw_material is not None
            else None
        ),
    )
    result.verify()
    record = result.as_record()
    del record["optical_surface"]
    if record != dict(value):
        raise ValueError("v5 object record is not canonical")
    return result


def _legacy_object_from(value: object) -> EmbodiedObject:
    expected = {
        "held_by_body_id", "mass_grams", "object_id", "position", "radius_mm"
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("legacy object fields changed")
    raw_position = value.get("position")
    result = EmbodiedObject(
        object_id=value.get("object_id"),
        radius_mm=value.get("radius_mm"),
        mass_grams=value.get("mass_grams"),
        position=(
            _position_from(raw_position, "legacy object position")
            if raw_position is not None else None
        ),
        held_by_body_id=value.get("held_by_body_id"),
    )
    result.verify()
    legacy_record = result.as_record()
    del legacy_record["reflectance_ppm"]
    del legacy_record["material"]
    del legacy_record["optical_surface"]
    if legacy_record != dict(value):
        raise ValueError("legacy object record is not canonical")
    return result


def _region_from(value: object) -> PhysicalRegion:
    expected = {
        "air", "bounds", "ceiling_height_mm", "illumination_ppm",
        "reflectance_ppm", "region_id"
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("physical region fields changed")
    result = PhysicalRegion(
        region_id=value.get("region_id"),
        bounds=_room_from(value.get("bounds")),
        ceiling_height_mm=value.get("ceiling_height_mm"),
        reflectance_ppm=_physical_bands(
            tuple(value.get("reflectance_ppm"))
            if isinstance(value.get("reflectance_ppm"), list)
            else value.get("reflectance_ppm"),
            "region reflectance",
        ),
        illumination_ppm=_physical_bands(
            tuple(value.get("illumination_ppm"))
            if isinstance(value.get("illumination_ppm"), list)
            else value.get("illumination_ppm"),
            "region illumination",
        ),
        air=(
            _air_from(value.get("air"))
            if value.get("air") is not None
            else None
        ),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("physical region record is not canonical")
    return result


def _portal_from(value: object) -> PhysicalPortal:
    expected = {
        "air_flow_cubic_mm_per_second",
        "aperture_max_mm", "aperture_min_mm", "axis", "height_mm",
        "plane_mm", "portal_id", "region_ids"
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("physical portal fields changed")
    raw_regions = value.get("region_ids")
    result = PhysicalPortal(
        portal_id=value.get("portal_id"),
        region_ids=tuple(raw_regions) if isinstance(raw_regions, list) else raw_regions,
        axis=value.get("axis"),
        plane_mm=value.get("plane_mm"),
        aperture_min_mm=value.get("aperture_min_mm"),
        aperture_max_mm=value.get("aperture_max_mm"),
        height_mm=value.get("height_mm"),
        air_flow_cubic_mm_per_second=value.get(
            "air_flow_cubic_mm_per_second"
        ),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("physical portal record is not canonical")
    return result


def _v3_body_from(value: object) -> EmbodiedBody:
    expected = {
        "body_id",
        "held_object_id",
        "pose",
        "radius_mm",
        "reach_mm",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("v3 body fields changed")
    result = EmbodiedBody(
        body_id=value.get("body_id"),
        held_object_id=value.get("held_object_id"),
        pose=_pose_from(value.get("pose"), "v3 body pose"),
        radius_mm=value.get("radius_mm"),
        reach_mm=value.get("reach_mm"),
        receptor_geometry=None,
        active_contact=None,
    )
    result.verify()
    record = result.as_record()
    del record["active_contact"]
    del record["receptor_geometry"]
    if record != dict(value):
        raise ValueError("v3 body record is not canonical")
    return result


def _v3_object_from(value: object) -> EmbodiedObject:
    expected = {
        "held_by_body_id",
        "mass_grams",
        "object_id",
        "position",
        "radius_mm",
        "reflectance_ppm",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("v3 object fields changed")
    raw_position = value.get("position")
    raw_reflectance = value.get("reflectance_ppm")
    result = EmbodiedObject(
        object_id=value.get("object_id"),
        radius_mm=value.get("radius_mm"),
        mass_grams=value.get("mass_grams"),
        position=(
            _position_from(raw_position, "v3 object position")
            if raw_position is not None
            else None
        ),
        held_by_body_id=value.get("held_by_body_id"),
        reflectance_ppm=_physical_bands(
            tuple(raw_reflectance)
            if isinstance(raw_reflectance, list)
            else raw_reflectance,
            "v3 object reflectance",
        ),
        material=None,
    )
    result.verify()
    record = result.as_record()
    del record["material"]
    del record["optical_surface"]
    if record != dict(value):
        raise ValueError("v3 object record is not canonical")
    return result


def _v3_region_from(value: object) -> PhysicalRegion:
    expected = {
        "bounds",
        "ceiling_height_mm",
        "illumination_ppm",
        "reflectance_ppm",
        "region_id",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("v3 region fields changed")
    raw_reflectance = value.get("reflectance_ppm")
    raw_illumination = value.get("illumination_ppm")
    result = PhysicalRegion(
        region_id=value.get("region_id"),
        bounds=_room_from(value.get("bounds")),
        ceiling_height_mm=value.get("ceiling_height_mm"),
        reflectance_ppm=_physical_bands(
            tuple(raw_reflectance)
            if isinstance(raw_reflectance, list)
            else raw_reflectance,
            "v3 region reflectance",
        ),
        illumination_ppm=_physical_bands(
            tuple(raw_illumination)
            if isinstance(raw_illumination, list)
            else raw_illumination,
            "v3 region illumination",
        ),
        air=None,
    )
    result.verify()
    record = result.as_record()
    del record["air"]
    if record != dict(value):
        raise ValueError("v3 region record is not canonical")
    return result


def _v3_portal_from(value: object) -> PhysicalPortal:
    expected = {
        "aperture_max_mm",
        "aperture_min_mm",
        "axis",
        "height_mm",
        "plane_mm",
        "portal_id",
        "region_ids",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("v3 portal fields changed")
    raw_regions = value.get("region_ids")
    result = PhysicalPortal(
        portal_id=value.get("portal_id"),
        region_ids=(
            tuple(raw_regions)
            if isinstance(raw_regions, list)
            else raw_regions
        ),
        axis=value.get("axis"),
        plane_mm=value.get("plane_mm"),
        aperture_min_mm=value.get("aperture_min_mm"),
        aperture_max_mm=value.get("aperture_max_mm"),
        height_mm=value.get("height_mm"),
        air_flow_cubic_mm_per_second=None,
    )
    result.verify()
    record = result.as_record()
    del record["air_flow_cubic_mm_per_second"]
    if record != dict(value):
        raise ValueError("v3 portal record is not canonical")
    return result


def _default_regions() -> tuple[PhysicalRegion, ...]:
    return (
        PhysicalRegion(
            "W1-region-A",
            RoomBoundsMM(PositionMM(0, 0, 0), PositionMM(5000, 5000, 3000)),
            3000,
            (620000, 600000, 580000, 560000, 540000, 520000),
            (700000, 680000, 650000, 620000, 590000, 560000),
            AirVolumeState(
                75_000_000_000,
                (0, 0, 0, 0, 0, 0, 0, 0),
            ),
        ),
        PhysicalRegion(
            "W1-region-B",
            RoomBoundsMM(PositionMM(5000, 0, 0), PositionMM(15000, 5000, 3000)),
            None,
            (310000, 360000, 420000, 480000, 540000, 600000),
            (820000, 800000, 770000, 730000, 690000, 650000),
            AirVolumeState(
                150_000_000_000,
                (0, 0, 0, 0, 0, 0, 0, 0),
            ),
        ),
        PhysicalRegion(
            "W1-region-C",
            RoomBoundsMM(PositionMM(15000, 0, 0), PositionMM(20000, 5000, 3000)),
            3000,
            (470000, 500000, 530000, 560000, 590000, 620000),
            (640000, 630000, 620000, 610000, 600000, 590000),
            AirVolumeState(
                75_000_000_000,
                (0, 0, 0, 0, 0, 0, 0, 0),
            ),
        ),
    )


def _default_portals() -> tuple[PhysicalPortal, ...]:
    return (
        PhysicalPortal(
            "W1-portal-1", ("W1-region-A", "W1-region-B"),
            "x", 5000, 2000, 3000, 2200, 1_000_000_000,
        ),
        PhysicalPortal(
            "W1-portal-2", ("W1-region-B", "W1-region-C"),
            "x", 15000, 2000, 3000, 2200, 1_000_000_000,
        ),
    )


def _default_receptor_geometry() -> BodyReceptorGeometry:
    return BodyReceptorGeometry(
        retinal_offset_mm=PositionMM(0, 0, 220),
        left_ear_offset_mm=PositionMM(0, 85, 200),
        right_ear_offset_mm=PositionMM(0, -85, 200),
        touch_offset_mm=PositionMM(0, 0, 0),
        touch_radius_mm=250,
        oral_offset_mm=PositionMM(0, 0, 0),
        oral_radius_mm=250,
        olfactory_offset_mm=PositionMM(0, 0, 200),
        odorant_saturation_nanograms_per_cubic_meter=(
            20_000,
            20_000,
            20_000,
            20_000,
            20_000,
            20_000,
            20_000,
            20_000,
        ),
        tastant_saturation_micrograms=(
            100_000,
            100_000,
            100_000,
            100_000,
            100_000,
        ),
        touch_mass_span_grams=10_000,
        touch_temperature_min_millikelvin=250_000,
        touch_temperature_max_millikelvin=350_000,
        touch_roughness_span_micrometers=100_000,
    )


def _default_material(
    *,
    odorant_base_nanograms: int,
    tastant_base_micrograms: int,
    temperature_millikelvin: int,
    compliance_ppm: int,
    roughness_micrometers: int,
    moisture_ppm: int,
) -> ObjectMaterialState:
    return ObjectMaterialState(
        odorant_reservoir_nanograms=tuple(
            odorant_base_nanograms + channel * 10_000
            for channel in range(ODORANT_CHANNELS)
        ),
        odorant_release_nanograms_per_second=tuple(
            1_000 + channel * 100
            for channel in range(ODORANT_CHANNELS)
        ),
        tastant_mass_micrograms=tuple(
            tastant_base_micrograms + channel * 1_000
            for channel in range(TASTANT_CHANNELS)
        ),
        surface_temperature_millikelvin=temperature_millikelvin,
        compliance_ppm=compliance_ppm,
        roughness_micrometers=roughness_micrometers,
        moisture_ppm=moisture_ppm,
    )


def _base_objects() -> tuple[EmbodiedObject, ...]:
    return (
        EmbodiedObject(
            "W1-object-1",
            100,
            500,
            PositionMM(1500, 1000, 0),
            reflectance_ppm=(
                700000, 300000, 180000, 120000, 90000, 70000
            ),
            material=_default_material(
                odorant_base_nanograms=2_000_000,
                tastant_base_micrograms=80_000,
                temperature_millikelvin=310_000,
                compliance_ppm=250_000,
                roughness_micrometers=12_000,
                moisture_ppm=700_000,
            ),
        ),
        EmbodiedObject(
            "W1-object-2",
            80,
            240,
            PositionMM(2500, 1000, 0),
            reflectance_ppm=(
                150000, 650000, 240000, 120000, 90000, 60000
            ),
            material=_default_material(
                odorant_base_nanograms=1_200_000,
                tastant_base_micrograms=20_000,
                temperature_millikelvin=305_000,
                compliance_ppm=500_000,
                roughness_micrometers=8_000,
                moisture_ppm=400_000,
            ),
        ),
        EmbodiedObject(
            "W1-object-3",
            120,
            900,
            PositionMM(3500, 1000, 0),
            reflectance_ppm=(
                120000, 220000, 720000, 300000, 120000, 80000
            ),
            material=_default_material(
                odorant_base_nanograms=800_000,
                tastant_base_micrograms=10_000,
                temperature_millikelvin=295_000,
                compliance_ppm=100_000,
                roughness_micrometers=40_000,
                moisture_ppm=100_000,
            ),
        ),
        EmbodiedObject(
            "W1-object-4",
            90,
            360,
            PositionMM(8000, 1000, 0),
            reflectance_ppm=(
                680000, 600000, 180000, 100000, 80000, 60000
            ),
            material=_default_material(
                odorant_base_nanograms=500_000,
                tastant_base_micrograms=15_000,
                temperature_millikelvin=315_000,
                compliance_ppm=350_000,
                roughness_micrometers=18_000,
                moisture_ppm=300_000,
            ),
        ),
        EmbodiedObject(
            "W1-object-5",
            140,
            1400,
            PositionMM(12000, 3500, 0),
            reflectance_ppm=(
                240000, 180000, 620000, 520000, 180000, 90000
            ),
            material=_default_material(
                odorant_base_nanograms=400_000,
                tastant_base_micrograms=5_000,
                temperature_millikelvin=300_000,
                compliance_ppm=80_000,
                roughness_micrometers=60_000,
                moisture_ppm=50_000,
            ),
        ),
        EmbodiedObject(
            "W1-object-6",
            110,
            720,
            PositionMM(17500, 1000, 0),
            reflectance_ppm=(
                520000, 200000, 180000, 650000, 300000, 120000
            ),
            material=_default_material(
                odorant_base_nanograms=300_000,
                tastant_base_micrograms=8_000,
                temperature_millikelvin=320_000,
                compliance_ppm=180_000,
                roughness_micrometers=25_000,
                moisture_ppm=200_000,
            ),
        ),
    )


def _default_objects() -> tuple[EmbodiedObject, ...]:
    from dsf_ai_service.substrate.approved_curriculum_physical_surfaces import (
        approved_curriculum_physical_surfaces,
    )

    return _base_objects() + approved_curriculum_physical_surfaces()


class EmbodimentWorldAuthority:
    """Atomic authority for one exact W1 multi-body/object world."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        room_id: str = "W1",
        room_bounds: RoomBoundsMM | None = None,
        self_body_id: str = "guala-body-1",
        bodies: Sequence[EmbodiedBody] | None = None,
        actor_ports: Sequence[EmbodimentPort] | None = None,
        initial_objects: Sequence[EmbodiedObject] | None = None,
        regions: Sequence[PhysicalRegion] | None = None,
        portals: Sequence[PhysicalPortal] | None = None,
        max_regions: int = DEFAULT_MAX_REGIONS,
        max_portals: int = DEFAULT_MAX_PORTALS,
        max_bodies: int = DEFAULT_MAX_BODIES,
        max_objects: int = DEFAULT_MAX_OBJECTS,
        receipt_capacity: int = DEFAULT_RECEIPT_CAPACITY,
        max_command_bytes: int = DEFAULT_MAX_COMMAND_BYTES,
        max_encoded_state_bytes: int = DEFAULT_MAX_ENCODED_STATE_BYTES,
    ) -> None:
        self._key = _authority_key(authority_key)
        self._max_regions = _bounded_integer(
            max_regions, "region capacity", minimum=3, maximum=4
        )
        self._max_portals = _bounded_integer(
            max_portals, "portal capacity", minimum=2, maximum=6
        )
        self._max_bodies = _bounded_integer(
            max_bodies, "body capacity", minimum=2, maximum=DEFAULT_MAX_BODIES
        )
        self._max_objects = _bounded_integer(
            max_objects,
            "object capacity",
            minimum=1,
            maximum=DEFAULT_MAX_OBJECTS,
        )
        self._receipt_capacity = _bounded_integer(
            receipt_capacity,
            "receipt capacity",
            minimum=1,
            maximum=DEFAULT_RECEIPT_CAPACITY,
        )
        self._max_command_bytes = _bounded_integer(
            max_command_bytes,
            "command byte capacity",
            minimum=64,
            maximum=DEFAULT_MAX_COMMAND_BYTES,
        )
        self._max_encoded_state_bytes = _bounded_integer(
            max_encoded_state_bytes,
            "encoded state byte capacity",
            minimum=4096,
            maximum=DEFAULT_MAX_ENCODED_STATE_BYTES,
        )
        if regions is None:
            physical_regions = _default_regions()
        else:
            if (
                not isinstance(regions, Sequence)
                or isinstance(regions, (str, bytes, bytearray))
                or not 3 <= len(regions) <= self._max_regions
                or any(not isinstance(item, PhysicalRegion) for item in regions)
            ):
                raise ValueError("physical region inventory exceeds capacity")
            physical_regions = tuple(regions)
        physical_regions = tuple(
            sorted(physical_regions, key=lambda item: item.region_id)
        )
        if portals is None:
            physical_portals = _default_portals()
        else:
            if (
                not isinstance(portals, Sequence)
                or isinstance(portals, (str, bytes, bytearray))
                or not 2 <= len(portals) <= self._max_portals
                or any(not isinstance(item, PhysicalPortal) for item in portals)
            ):
                raise ValueError("physical portal inventory exceeds capacity")
            physical_portals = tuple(portals)
        physical_portals = tuple(
            sorted(physical_portals, key=lambda item: item.portal_id)
        )
        bounds = physical_regions[0].bounds
        canonical_self_body_id = _identifier(self_body_id, "self body id")
        if bodies is None:
            embodied_bodies = (
                EmbodiedBody(
                    body_id=canonical_self_body_id,
                    pose=PoseMM(PositionMM(1000, 1000, 0), 0),
                    radius_mm=250,
                    reach_mm=800,
                    receptor_geometry=_default_receptor_geometry(),
                ),
                EmbodiedBody(
                    body_id="w1-body-2",
                    pose=PoseMM(
                        PositionMM(
                            bounds.maximum.x - 250,
                            bounds.maximum.y - 250,
                            bounds.minimum.z,
                        ),
                        180_000,
                    ),
                    radius_mm=250,
                    reach_mm=800,
                    receptor_geometry=_default_receptor_geometry(),
                ),
            )
        else:
            if (
                not isinstance(bodies, Sequence)
                or isinstance(bodies, (str, bytes, bytearray))
                or not 2 <= len(bodies) <= self._max_bodies
                or any(not isinstance(item, EmbodiedBody) for item in bodies)
            ):
                raise ValueError("world body inventory exceeds its exact capacity")
            embodied_bodies = tuple(bodies)
        embodied_bodies = tuple(
            sorted(embodied_bodies, key=lambda item: item.body_id)
        )
        if actor_ports is None:
            other_ids = tuple(
                item.body_id
                for item in embodied_bodies
                if item.body_id != canonical_self_body_id
            )
            if len(other_ids) != 1:
                raise ValueError(
                    "custom multi-body worlds require explicit actor ports"
                )
            embodied_ports = (
                EmbodimentPort(PORT_ID, canonical_self_body_id),
                EmbodimentPort(SECOND_BODY_PORT_ID, other_ids[0]),
            )
        else:
            if (
                not isinstance(actor_ports, Sequence)
                or isinstance(actor_ports, (str, bytes, bytearray))
                or len(actor_ports) != len(embodied_bodies)
                or any(not isinstance(item, EmbodimentPort) for item in actor_ports)
            ):
                raise ValueError("actor port topology differs from body topology")
            embodied_ports = tuple(actor_ports)
        self._actor_ports = tuple(
            sorted(embodied_ports, key=lambda item: item.port_id)
        )
        self._validate_port_topology(
            canonical_self_body_id, embodied_bodies, self._actor_ports
        )
        if initial_objects is None:
            objects = _default_objects()
        else:
            if (
                not isinstance(initial_objects, Sequence)
                or isinstance(initial_objects, (str, bytes, bytearray))
                or not 1 <= len(initial_objects) <= self._max_objects
            ):
                raise ValueError("world object inventory exceeds its exact capacity")
            if any(not isinstance(item, EmbodiedObject) for item in initial_objects):
                raise ValueError("world object inventory contains an invalid object")
            objects = tuple(initial_objects)
        world = _WorldState(
            revision=0,
            room_id=physical_regions[0].region_id,
            room_bounds=bounds,
            regions=physical_regions,
            portals=physical_portals,
            self_body_id=canonical_self_body_id,
            bodies=embodied_bodies,
            objects=tuple(sorted(objects, key=lambda item: item.object_id)),
        )
        self._validate_world(world)
        self._physical_body_mount_observation_receipt = (
            self._derive_physical_body_mount_observation_receipt(world)
        )
        self_body = next(
            body for body in world.bodies
            if body.body_id == world.self_body_id
        )
        vocal_anatomy = {
            "body_id": self_body.body_id,
            "radius_mm": self_body.radius_mm,
            "schema": "guala.embodiment.vocal_anatomy_edge.v1",
        }
        vocal_signature = _sign(
            self._key,
            b"guala.embodiment.vocal_anatomy_edge.v1\0",
            vocal_anatomy,
        )
        self._physical_vocal_anatomy_receipt = _digest({
            "authority_hmac_sha256": vocal_signature,
            "payload": vocal_anatomy,
        })
        self._state = _AuthorityState(
            world=world,
            observation=self._observation_for(world),
            recent_applied_receipts=(),
            migration_receipt=None,
        )
        self._prepared_action_execution: PreparedActionExecution | None = None
        self._committing_prepared_action_execution: (
            PreparedActionExecution | None
        ) = None
        self._visibility_prepared_action: (
            PreparedActionExecution | None
        ) = None
        self._lock = threading.RLock()
        self._encoded_state_for(self._state)

    def _derive_physical_body_mount_observation_receipt(
        self,
        world: _WorldState,
    ) -> str:
        """Bind anatomy before external optical curriculum objects exist."""

        world_record = world._canonical_record()
        mounted_objects = []
        for value in world_record["objects"]:
            if value.get("optical_surface") is not None:
                continue
            mounted = dict(value)
            mounted.pop("optical_surface")
            mounted_objects.append(mounted)
        anatomical_world = {
            **world_record,
            "objects": mounted_objects,
        }
        unsigned = {
            **anatomical_world,
            "schema": V5_OBSERVATION_SCHEMA,
            "state_sha256": _digest(anatomical_world),
        }
        signature = _sign(
            self._key,
            V5_OBSERVATION_DOMAIN,
            unsigned,
        )
        return _digest({
            "authority_hmac_sha256": signature,
            "payload": unsigned,
        })

    def physical_body_mount_observation_receipt(self) -> str:
        """Return the immutable body/room mount receipt."""

        return self._physical_body_mount_observation_receipt

    def physical_vocal_anatomy_receipt(self) -> str:
        """Return the immutable authenticated vocal-anatomy body edge."""

        return self._physical_vocal_anatomy_receipt

    def _require_public_visibility_locked(self) -> None:
        if self._visibility_prepared_action is not None:
            raise RuntimeError(
                "embodiment world visibility transaction is in progress"
            )

    @property
    def port_id(self) -> str:
        with self._lock:
            self._require_public_visibility_locked()
            return next(
                item.port_id
                for item in self._actor_ports
                if item.actor_body_id
                == self._state.world.self_body_id
            )

    @property
    def self_body_id(self) -> str:
        with self._lock:
            self._require_public_visibility_locked()
            return self._state.world.self_body_id

    @property
    def actor_ports(self) -> tuple[EmbodimentPort, ...]:
        return self._actor_ports

    def _validate_port_topology(
        self,
        self_body_id: str,
        bodies: tuple[EmbodiedBody, ...],
        ports: tuple[EmbodimentPort, ...],
    ) -> None:
        if len(ports) != len(bodies):
            raise ValueError("every body requires exactly one actor port")
        for item in ports:
            item.verify()
        if tuple(sorted(ports, key=lambda item: item.port_id)) != ports:
            raise ValueError("actor ports are not in canonical port order")
        port_ids = tuple(item.port_id for item in ports)
        actor_ids = tuple(item.actor_body_id for item in ports)
        body_ids = tuple(item.body_id for item in bodies)
        if len(set(port_ids)) != len(port_ids):
            raise ValueError("actor port identities repeat")
        if len(set(actor_ids)) != len(actor_ids) or set(actor_ids) != set(body_ids):
            raise ValueError("actor port/body reciprocity changed")
        self_ports = tuple(
            item for item in ports if item.actor_body_id == self_body_id
        )
        if len(self_ports) != 1 or self_ports[0].port_id != PORT_ID:
            raise ValueError("self body must retain the canonical self port")

    def _validate_physical_topology(
        self,
        regions: tuple[PhysicalRegion, ...],
        portals: tuple[PhysicalPortal, ...],
    ) -> None:
        if (
            not 3 <= len(regions) <= self._max_regions
            or regions != tuple(sorted(regions, key=lambda item: item.region_id))
            or len({item.region_id for item in regions}) != len(regions)
        ):
            raise ValueError("physical region topology is not canonical")
        for item in regions:
            item.verify()
        if (
            not 2 <= len(portals) <= self._max_portals
            or portals != tuple(sorted(portals, key=lambda item: item.portal_id))
            or len({item.portal_id for item in portals}) != len(portals)
        ):
            raise ValueError("physical portal topology is not canonical")
        region_by_id = {item.region_id: item for item in regions}
        connected_pairs = set()
        for portal in portals:
            portal.verify()
            if any(value not in region_by_id for value in portal.region_ids):
                raise ValueError("portal names a region outside topology")
            if portal.region_ids in connected_pairs:
                raise ValueError("physical regions repeat a portal edge")
            connected_pairs.add(portal.region_ids)
            left, right = (region_by_id[value] for value in portal.region_ids)
            if portal.axis == "x":
                shared = {
                    left.bounds.minimum.x, left.bounds.maximum.x
                }.intersection({right.bounds.minimum.x, right.bounds.maximum.x})
                overlap_min = max(left.bounds.minimum.y, right.bounds.minimum.y)
                overlap_max = min(left.bounds.maximum.y, right.bounds.maximum.y)
            else:
                shared = {
                    left.bounds.minimum.y, left.bounds.maximum.y
                }.intersection({right.bounds.minimum.y, right.bounds.maximum.y})
                overlap_min = max(left.bounds.minimum.x, right.bounds.minimum.x)
                overlap_max = min(left.bounds.maximum.x, right.bounds.maximum.x)
            if (
                shared != {portal.plane_mm}
                or not overlap_min <= portal.aperture_min_mm
                < portal.aperture_max_mm <= overlap_max
                or portal.height_mm > min(
                    left.bounds.maximum.z, right.bounds.maximum.z
                )
            ):
                raise ValueError("portal aperture differs from shared boundaries")
            if portal.air_flow_cubic_mm_per_second is not None and (
                left.air is None or right.air is None
            ):
                raise ValueError(
                    "portal air flow requires signed air on both regions"
                )
        for region in regions:
            incident_flow = sum(
                portal.air_flow_cubic_mm_per_second or 0
                for portal in portals
                if region.region_id in portal.region_ids
            )
            if (
                region.air is not None
                and incident_flow * MAX_MATERIAL_ACTION_DURATION_US
                > region.air.volume_cubic_mm * 1_000_000
            ):
                raise ValueError(
                    "portal flow can evacuate more than signed air volume"
                )

    @staticmethod
    def _region_containing(
        regions: tuple[PhysicalRegion, ...],
        position: PositionMM,
        radius_mm: int,
    ) -> PhysicalRegion | None:
        matches = tuple(
            item for item in regions
            if item.bounds.contains_floor_disc(position, radius_mm)
        )
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _portal_between(
        portals: tuple[PhysicalPortal, ...],
        left: str,
        right: str,
    ) -> PhysicalPortal | None:
        pair = tuple(sorted((left, right)))
        return next((item for item in portals if item.region_ids == pair), None)

    @staticmethod
    def _portal_crossing_is_clear(
        portal: PhysicalPortal,
        start: PositionMM,
        finish: PositionMM,
        radius_mm: int,
    ) -> bool:
        if portal.axis == "x":
            delta = finish.x - start.x
            if delta == 0:
                return False
            numerator = (portal.plane_mm - start.x) * (finish.y - start.y)
            crossing_num = start.y * delta + numerator
            denominator = delta
        else:
            delta = finish.y - start.y
            if delta == 0:
                return False
            numerator = (portal.plane_mm - start.y) * (finish.x - start.x)
            crossing_num = start.x * delta + numerator
            denominator = delta
        if denominator < 0:
            crossing_num = -crossing_num
            denominator = -denominator
        return (
            (portal.aperture_min_mm + radius_mm) * denominator
            <= crossing_num
            <= (portal.aperture_max_mm - radius_mm) * denominator
            and start.z + radius_mm <= portal.height_mm
            and finish.z + radius_mm <= portal.height_mm
        )

    @staticmethod
    def _odorant_totals(world: _WorldState) -> tuple[int, ...]:
        totals = [0] * ODORANT_CHANNELS
        for region in world.regions:
            if region.air is not None:
                for index, value in enumerate(
                    region.air.odorant_mass_nanograms
                ):
                    totals[index] += value
        for item in world.objects:
            if item.material is not None:
                for index, value in enumerate(
                    item.material.odorant_reservoir_nanograms
                ):
                    totals[index] += value
        return tuple(totals)

    def _advance_material_time(
        self,
        world: _WorldState,
        duration_nanoseconds: int,
    ) -> _WorldState:
        duration = _bounded_integer(
            duration_nanoseconds,
            "material transport duration",
            minimum=MIN_MATERIAL_ACTION_DURATION_US * 1_000,
            maximum=MAX_MATERIAL_ACTION_DURATION_US * 1_000,
        )
        before_totals = self._odorant_totals(world)
        regions = list(world.regions)
        objects = list(world.objects)
        region_index = {
            region.region_id: index
            for index, region in enumerate(regions)
        }
        air_mass = [
            (
                list(region.air.odorant_mass_nanograms)
                if region.air is not None
                else None
            )
            for region in regions
        ]
        body_by_id = {body.body_id: body for body in world.bodies}

        for object_index, item in enumerate(objects):
            material = item.material
            if material is None:
                continue
            position = item.position
            if position is None and item.held_by_body_id is not None:
                holder = body_by_id.get(item.held_by_body_id)
                position = (
                    holder.pose.position if holder is not None else None
                )
            if position is None:
                raise ValueError(
                    "material object has no physical transport position"
                )
            region = self._region_containing(
                world.regions,
                position,
                0,
            )
            if region is None:
                raise ValueError(
                    "material object left signed air topology"
                )
            target_index = region_index[region.region_id]
            target_air = air_mass[target_index]
            if target_air is None:
                continue
            reservoir = list(material.odorant_reservoir_nanograms)
            for channel, rate in enumerate(
                material.odorant_release_nanograms_per_second
            ):
                released = min(
                    reservoir[channel],
                    rate * duration // 1_000_000_000,
                )
                reservoir[channel] -= released
                target_air[channel] += released
                if target_air[channel] > MAX_MATERIAL_MASS:
                    raise ValueError(
                        "air odorant mass exceeds signed capacity"
                    )
            objects[object_index] = replace(
                item,
                material=replace(
                    material,
                    odorant_reservoir_nanograms=tuple(reservoir),
                ),
            )

        base_air = [
            tuple(values) if values is not None else None
            for values in air_mass
        ]
        deltas = [
            [0] * ODORANT_CHANNELS
            for _region in regions
        ]
        for portal in world.portals:
            flow = portal.air_flow_cubic_mm_per_second
            if flow is None:
                continue
            left_id, right_id = portal.region_ids
            left_index = region_index[left_id]
            right_index = region_index[right_id]
            left_region = regions[left_index]
            right_region = regions[right_index]
            left_air = base_air[left_index]
            right_air = base_air[right_index]
            if (
                left_region.air is None
                or right_region.air is None
                or left_air is None
                or right_air is None
            ):
                raise ValueError(
                    "signed portal flow lost its air volume"
                )
            for channel in range(ODORANT_CHANNELS):
                left_to_right = (
                    left_air[channel] * flow * duration
                    // (
                        left_region.air.volume_cubic_mm
                        * 1_000_000_000
                    )
                )
                right_to_left = (
                    right_air[channel] * flow * duration
                    // (
                        right_region.air.volume_cubic_mm
                        * 1_000_000_000
                    )
                )
                deltas[left_index][channel] += (
                    right_to_left - left_to_right
                )
                deltas[right_index][channel] += (
                    left_to_right - right_to_left
                )

        for index, region in enumerate(regions):
            values = air_mass[index]
            if values is None:
                continue
            settled = tuple(
                values[channel] + deltas[index][channel]
                for channel in range(ODORANT_CHANNELS)
            )
            if any(
                value < 0 or value > MAX_MATERIAL_MASS
                for value in settled
            ):
                raise ValueError(
                    "finite air transport exceeded signed mass bounds"
                )
            regions[index] = replace(
                region,
                air=replace(
                    region.air,
                    odorant_mass_nanograms=settled,
                ),
            )
        result = replace(
            world,
            regions=tuple(regions),
            objects=tuple(objects),
        )
        if self._odorant_totals(result) != before_totals:
            raise AssertionError(
                "odorant transport violated exact mass conservation"
            )
        return result

    def _validate_world(self, world: _WorldState) -> None:
        _bounded_integer(world.revision, "world revision", minimum=0, maximum=MAX_REVISION)
        self._validate_physical_topology(world.regions, world.portals)
        region_by_id = {item.region_id: item for item in world.regions}
        if (
            world.room_id not in region_by_id
            or world.room_bounds != region_by_id[world.room_id].bounds
        ):
            raise ValueError("self region projection differs from topology")
        _identifier(world.self_body_id, "self body id")
        if not 2 <= len(world.bodies) <= self._max_bodies:
            raise ValueError("world body inventory exceeds its exact capacity")
        if tuple(sorted(world.bodies, key=lambda item: item.body_id)) != world.bodies:
            raise ValueError("world bodies are not in canonical identity order")
        body_ids = [item.body_id for item in world.bodies]
        if len(body_ids) != len(set(body_ids)) or world.self_body_id not in body_ids:
            raise ValueError("world body identities or self-body changed")
        for body in world.bodies:
            body.verify()
        self._validate_port_topology(
            world.self_body_id, world.bodies, self._actor_ports
        )
        if not 1 <= len(world.objects) <= self._max_objects:
            raise ValueError("world object inventory exceeds its exact capacity")
        if tuple(sorted(world.objects, key=lambda item: item.object_id)) != world.objects:
            raise ValueError("world objects are not in canonical identity order")
        ids = [item.object_id for item in world.objects]
        if len(ids) != len(set(ids)):
            raise ValueError("world object identities are not unique")
        held_by_body: dict[str, list[str]] = {
            item.body_id: [] for item in world.bodies
        }
        placed = []
        for item in world.objects:
            item.verify()
            if item.held_by_body_id is not None:
                if item.held_by_body_id not in held_by_body:
                    raise ValueError("object is held by a body outside this authority")
                held_by_body[item.held_by_body_id].append(item.object_id)
            else:
                if self._region_containing(
                    world.regions, item.position, item.radius_mm
                ) is None:
                    raise ValueError("object position is outside room geometry")
                placed.append(item)
        object_by_id = {item.object_id: item for item in world.objects}
        occupied: list[tuple[EmbodiedBody, int]] = []
        for body in world.bodies:
            held = held_by_body[body.body_id]
            expected_held = held[0] if len(held) == 1 else None
            if len(held) > 1 or body.held_object_id != expected_held:
                raise ValueError("body/object holding relation is not reciprocal")
            carried_radius = body.radius_mm
            if expected_held is not None:
                carried_radius = max(
                    carried_radius, object_by_id[expected_held].radius_mm
                )
            if self._region_containing(
                world.regions, body.pose.position, carried_radius
            ) is None:
                raise ValueError("body and held object are outside room geometry")
            occupied.append((body, carried_radius))
            contact = body.active_contact
            if contact is not None:
                item = object_by_id.get(contact.object_id)
                geometry = body.receptor_geometry
                if (
                    item is None
                    or item.material is None
                    or geometry is None
                ):
                    raise ValueError(
                        "body contact lacks signed material/receptor state"
                    )
                if (
                    contact.kind == "oral"
                    and (
                        body.held_object_id != item.object_id
                        or item.held_by_body_id != body.body_id
                    )
                ):
                    raise ValueError(
                        "oral contact is not a reciprocal held relation"
                    )
                object_position = (
                    item.position
                    if item.position is not None
                    else body.pose.position
                )
                offset = (
                    geometry.oral_offset_mm
                    if contact.kind == "oral"
                    else geometry.touch_offset_mm
                )
                receptor_radius = (
                    geometry.oral_radius_mm
                    if contact.kind == "oral"
                    else geometry.touch_radius_mm
                )
                receptor_position = _receptor_position(body, offset)
                expected_patch = (
                    _derived_contact_patch_square_mm(
                        receptor_position=receptor_position,
                        receptor_radius_mm=receptor_radius,
                        object_position=object_position,
                        object_radius_mm=item.radius_mm,
                    )
                    if receptor_position is not None
                    else None
                )
                if expected_patch != contact.contact_patch_square_mm:
                    raise ValueError(
                        "body contact differs from signed geometry"
                    )
        self_body = next(
            item for item in world.bodies if item.body_id == world.self_body_id
        )
        self_region = self._region_containing(
            world.regions,
            self_body.pose.position,
            next(
                radius for body, radius in occupied
                if body.body_id == world.self_body_id
            ),
        )
        if self_region is None or self_region.region_id != world.room_id:
            raise ValueError("self body current region changed")
        for index, (left, left_radius) in enumerate(occupied):
            for right, right_radius in occupied[index + 1 :]:
                if (
                    self._region_containing(
                        world.regions, left.pose.position, left_radius
                    )
                    == self._region_containing(
                        world.regions, right.pose.position, right_radius
                    )
                    and _floor_discs_overlap(
                    left.pose.position,
                    left_radius,
                    right.pose.position,
                    right_radius,
                    )
                ):
                    raise ValueError("body geometries intersect")
        for body, carried_radius in occupied:
            for item in placed:
                if (
                    self._region_containing(
                        world.regions, body.pose.position, carried_radius
                    )
                    == self._region_containing(
                        world.regions, item.position, item.radius_mm
                    )
                    and _floor_discs_overlap(
                    body.pose.position,
                    carried_radius,
                    item.position,
                    item.radius_mm,
                    )
                ):
                    raise ValueError("body or held object intersects placed object geometry")
        for index, left in enumerate(placed):
            for right in placed[index + 1 :]:
                if (
                    self._region_containing(
                        world.regions, left.position, left.radius_mm
                    )
                    == self._region_containing(
                        world.regions, right.position, right.radius_mm
                    )
                    and _floor_discs_overlap(
                        left.position, left.radius_mm,
                        right.position, right.radius_mm
                    )
                ):
                    raise ValueError("placed objects intersect each other")

    def _observation_for(self, world: _WorldState) -> ObservationSnapshot:
        state_record = world._canonical_record()
        state_sha = _digest(state_record)
        unsigned = {
            **state_record,
            "schema": OBSERVATION_SCHEMA,
            "state_sha256": state_sha,
        }
        signature = _sign(self._key, OBSERVATION_DOMAIN, unsigned)
        receipt = _digest({"authority_hmac_sha256": signature, "payload": unsigned})
        return ObservationSnapshot(
            revision=world.revision,
            room_id=world.room_id,
            room_bounds=world.room_bounds,
            regions=world.regions,
            portals=world.portals,
            self_body_id=world.self_body_id,
            bodies=world.bodies,
            objects=world.objects,
            state_sha256=state_sha,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=receipt,
        )

    def observation_snapshot(self) -> ObservationSnapshot:
        with self._lock:
            self._require_public_visibility_locked()
            return self._state.observation

    def latest_execution_snapshot(self) -> ActionExecutionReceipt | None:
        """Return the latest immutable completed action, if one exists."""
        with self._lock:
            self._require_public_visibility_locked()
            if not self._state.recent_applied_receipts:
                return None
            return self._state.recent_applied_receipts[-1]

    def applied_execution_for_causal_intent(
        self,
        causal_intent_receipt_sha256: str,
    ) -> ActionExecutionReceipt | None:
        """Resolve one retained applied execution by exact causal intent."""

        intent = _sha256_identity(
            causal_intent_receipt_sha256,
            "causal intent receipt",
        )
        with self._lock:
            self._require_public_visibility_locked()
            matches = tuple(
                value
                for value in self._state.recent_applied_receipts
                if value.causal_intent_receipt_sha256 == intent
            )
            if len(matches) > 1:
                raise RuntimeError(
                    "causal intent resolves multiple applied executions"
                )
            if not matches:
                return None
            return matches[0]

    def _execution_receipt(
        self,
        *,
        port_id: str,
        actor_body_id: str | None,
        causal_intent_receipt_sha256: str,
        command_sha256: str,
        expected_revision: int,
        disposition: str,
        reason: str,
        elapsed_nanoseconds: int,
        lifecycle: tuple[str, ...],
        before: ObservationSnapshot,
        after: ObservationSnapshot,
    ) -> ActionExecutionReceipt:
        elapsed = _bounded_integer(
            elapsed_nanoseconds,
            "execution elapsed time",
            minimum=0,
            maximum=MAX_MATERIAL_ACTION_DURATION_US * 1_000,
        )
        unsigned = {
            "actor_body_id": actor_body_id,
            "after": after._canonical_record(),
            "before": before._canonical_record(),
            "causal_intent_receipt_sha256": causal_intent_receipt_sha256,
            "command_sha256": command_sha256,
            "disposition": disposition,
            "elapsed_nanoseconds": elapsed,
            "expected_revision": expected_revision,
            "lifecycle": list(lifecycle),
            "observed_revision": before.revision,
            "port_id": port_id,
            "reason": reason,
            "schema": EXECUTION_SCHEMA,
        }
        signature = _sign(self._key, EXECUTION_DOMAIN, unsigned)
        receipt = _digest({"authority_hmac_sha256": signature, "payload": unsigned})
        return ActionExecutionReceipt(
            port_id=port_id,
            actor_body_id=actor_body_id,
            causal_intent_receipt_sha256=causal_intent_receipt_sha256,
            command_sha256=command_sha256,
            expected_revision=expected_revision,
            observed_revision=before.revision,
            disposition=disposition,
            reason=reason,
            elapsed_nanoseconds=elapsed,
            lifecycle=lifecycle,
            before=before,
            after=after,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=receipt,
        )

    def _reject(
        self,
        *,
        port_id: str,
        actor_body_id: str | None,
        causal_intent_receipt_sha256: str,
        command_sha256: str,
        expected_revision: int,
        reason: str,
        lifecycle: tuple[str, ...],
        before: ObservationSnapshot,
    ) -> ActionExecutionReceipt:
        return self._execution_receipt(
            port_id=port_id,
            actor_body_id=actor_body_id,
            causal_intent_receipt_sha256=causal_intent_receipt_sha256,
            command_sha256=command_sha256,
            expected_revision=expected_revision,
            disposition="rejected",
            reason=reason,
            elapsed_nanoseconds=0,
            lifecycle=lifecycle + ("rejected",),
            before=before,
            after=before,
        )

    def _transition(
        self,
        world: _WorldState,
        actor_body_id: str,
        command: EmbodimentCommand,
    ) -> tuple[_WorldState | None, str]:
        bodies = list(world.bodies)
        body_index = next(
            index
            for index, item in enumerate(bodies)
            if item.body_id == actor_body_id
        )
        body = replace(bodies[body_index], active_contact=None)
        bodies[body_index] = body
        objects = list(world.objects)
        by_id = {item.object_id: (index, item) for index, item in enumerate(objects)}

        def occupied_radius(value: EmbodiedBody) -> int:
            if value.held_object_id is None:
                return value.radius_mm
            return max(value.radius_mm, by_id[value.held_object_id][1].radius_mm)

        if isinstance(
            command,
            (TouchContactCommand, OralContactCommand),
        ):
            found = by_id.get(command.object_id)
            if found is None:
                return None, "contact_unknown_object"
            _object_index, item = found
            geometry = body.receptor_geometry
            if item.material is None or geometry is None:
                return None, "material_receptors_unavailable"
            if isinstance(command, OralContactCommand) and (
                body.held_object_id != item.object_id
                or item.held_by_body_id != body.body_id
            ):
                return None, "oral_contact_requires_held_object"
            if (
                item.position is None
                and item.held_by_body_id != body.body_id
            ):
                return None, "contact_object_unavailable"
            object_position = (
                item.position
                if item.position is not None
                else body.pose.position
            )
            offset = (
                geometry.oral_offset_mm
                if isinstance(command, OralContactCommand)
                else geometry.touch_offset_mm
            )
            receptor_radius = (
                geometry.oral_radius_mm
                if isinstance(command, OralContactCommand)
                else geometry.touch_radius_mm
            )
            receptor_position = _receptor_position(body, offset)
            if receptor_position is None:
                return None, "contact_heading_geometry_unresolved"
            patch = _derived_contact_patch_square_mm(
                receptor_position=receptor_position,
                receptor_radius_mm=receptor_radius,
                object_position=object_position,
                object_radius_mm=item.radius_mm,
            )
            if patch is None:
                return None, "contact_geometry_separated"
            advanced = self._advance_material_time(
                replace(world, bodies=tuple(bodies)),
                command.duration_microseconds * 1_000,
            )
            advanced_bodies = list(advanced.bodies)
            advanced_body = advanced_bodies[body_index]
            advanced_bodies[body_index] = replace(
                advanced_body,
                active_contact=BodyContactState(
                    kind=(
                        "oral"
                        if isinstance(command, OralContactCommand)
                        else "touch"
                    ),
                    object_id=item.object_id,
                    contact_patch_square_mm=patch,
                    duration_microseconds=(
                        command.duration_microseconds
                    ),
                ),
            )
            return replace(
                advanced,
                bodies=tuple(advanced_bodies),
            ), "applied"

        if isinstance(command, AdvancePhysicalTimeCommand):
            return self._advance_material_time(
                replace(world, bodies=tuple(bodies)),
                command.duration_microseconds * 1_000,
            ), "applied"

        if isinstance(command, MoveCommand):
            target = command.target_pose
            carried_radius = occupied_radius(body)
            start_region = self._region_containing(
                world.regions, body.pose.position, carried_radius
            )
            target_region = self._region_containing(
                world.regions, target.position, carried_radius
            )
            if target_region is None:
                return None, "move_outside_room"
            if start_region is None:
                raise RuntimeError("body lost its physical region")
            if start_region.region_id != target_region.region_id:
                portal = self._portal_between(
                    world.portals,
                    start_region.region_id,
                    target_region.region_id,
                )
                if portal is None:
                    return None, "move_crosses_disconnected_regions"
                if not self._portal_crossing_is_clear(
                    portal, body.pose.position, target.position, carried_radius
                ):
                    return None, "move_misses_portal_aperture"
            for other in bodies:
                if other.body_id == body.body_id:
                    continue
                other_region = self._region_containing(
                    world.regions,
                    other.pose.position,
                    occupied_radius(other),
                )
                if (
                    other_region in {start_region, target_region}
                    and _straight_path_intersects_disc(
                    body.pose.position,
                    target.position,
                    other.pose.position,
                    carried_radius + occupied_radius(other),
                    )
                ):
                    return None, "move_path_intersects_body"
            for item in objects:
                item_region = (
                    self._region_containing(
                        world.regions, item.position, item.radius_mm
                    ) if item.position is not None else None
                )
                if (
                    item.position is not None
                    and item_region in {start_region, target_region}
                    and _straight_path_intersects_disc(
                    body.pose.position,
                    target.position,
                    item.position,
                    carried_radius + item.radius_mm,
                    )
                ):
                    return None, "move_path_intersects_object"
            bodies[body_index] = replace(body, pose=target)
            changed = replace(world, bodies=tuple(bodies))
            if body.body_id == world.self_body_id:
                changed = replace(
                    changed,
                    room_id=target_region.region_id,
                    room_bounds=target_region.bounds,
                )
            return self._advance_material_time(
                changed,
                command.duration_microseconds * 1_000,
            ), "applied"

        if isinstance(command, PickCommand):
            found = by_id.get(command.object_id)
            if found is None:
                return None, "pick_unknown_object"
            if body.held_object_id is not None:
                return None, "pick_body_already_holding"
            index, item = found
            if item.position is None:
                return None, "pick_object_unavailable"
            body_region = self._region_containing(
                world.regions, body.pose.position, body.radius_mm
            )
            object_region = self._region_containing(
                world.regions, item.position, item.radius_mm
            )
            if body_region != object_region:
                return None, "pick_object_outside_region"
            if _distance_squared(body.pose.position, item.position) > body.reach_mm**2:
                return None, "pick_out_of_reach"
            if self._region_containing(
                world.regions,
                body.pose.position,
                max(body.radius_mm, item.radius_mm),
            ) is None:
                return None, "pick_carried_geometry_outside_room"
            for other in bodies:
                if (
                    other.body_id != body.body_id
                    and self._region_containing(
                        world.regions,
                        other.pose.position,
                        occupied_radius(other),
                    ) == body_region
                    and _straight_path_intersects_disc(
                        body.pose.position,
                        item.position,
                        other.pose.position,
                        item.radius_mm + occupied_radius(other),
                    )
                ):
                    return None, "pick_path_intersects_body"
            for other in objects:
                if (
                    other.object_id != item.object_id
                    and other.position is not None
                    and self._region_containing(
                        world.regions,
                        other.position,
                        other.radius_mm,
                    ) == body_region
                    and _straight_path_intersects_disc(
                        body.pose.position,
                        item.position,
                        other.position,
                        item.radius_mm + other.radius_mm,
                    )
                ):
                    return None, "pick_path_intersects_object"
            objects[index] = replace(item, position=None, held_by_body_id=body.body_id)
            bodies[body_index] = replace(
                body, held_object_id=item.object_id
            )
            return self._advance_material_time(
                replace(
                    world,
                    bodies=tuple(bodies),
                    objects=tuple(objects),
                ),
                command.duration_microseconds * 1_000,
            ), "applied"

        if isinstance(command, PlaceCommand):
            found = by_id.get(command.object_id)
            if found is None:
                return None, "place_unknown_object"
            index, item = found
            if body.held_object_id != item.object_id or item.held_by_body_id != body.body_id:
                return None, "place_object_not_held"
            body_region = self._region_containing(
                world.regions, body.pose.position, body.radius_mm
            )
            target_region = self._region_containing(
                world.regions, command.target_position, item.radius_mm
            )
            if target_region is None:
                return None, "place_outside_room"
            if target_region != body_region:
                return None, "place_target_outside_region"
            if _distance_squared(body.pose.position, command.target_position) > body.reach_mm**2:
                return None, "place_out_of_reach"
            for other in bodies:
                other_region = self._region_containing(
                    world.regions,
                    other.pose.position,
                    occupied_radius(other),
                )
                if other_region == target_region and _floor_discs_overlap(
                    other.pose.position,
                    occupied_radius(other),
                    command.target_position,
                    item.radius_mm,
                ):
                    return None, "place_intersects_body"
            for other in objects:
                if (
                    other.object_id != item.object_id
                    and other.position is not None
                    and self._region_containing(
                        world.regions, other.position, other.radius_mm
                    ) == target_region
                    and _floor_discs_overlap(
                    command.target_position,
                    item.radius_mm,
                    other.position,
                    other.radius_mm,
                    )
                ):
                    return None, "place_intersects_object"
            for other in bodies:
                if (
                    other.body_id != body.body_id
                    and self._region_containing(
                        world.regions,
                        other.pose.position,
                        occupied_radius(other),
                    ) == target_region
                    and _straight_path_intersects_disc(
                        body.pose.position,
                        command.target_position,
                        other.pose.position,
                        item.radius_mm + occupied_radius(other),
                    )
                ):
                    return None, "place_path_intersects_body"
            for other in objects:
                if (
                    other.object_id != item.object_id
                    and other.position is not None
                    and self._region_containing(
                        world.regions,
                        other.position,
                        other.radius_mm,
                    ) == target_region
                    and _straight_path_intersects_disc(
                        body.pose.position,
                        command.target_position,
                        other.position,
                        item.radius_mm + other.radius_mm,
                    )
                ):
                    return None, "place_path_intersects_object"
            objects[index] = replace(item, position=command.target_position, held_by_body_id=None)
            bodies[body_index] = replace(body, held_object_id=None)
            return self._advance_material_time(
                replace(
                    world,
                    bodies=tuple(bodies),
                    objects=tuple(objects),
                ),
                command.duration_microseconds * 1_000,
            ), "applied"

        if isinstance(command, VocalizeCommand):
            command_record(command)
            return self._advance_material_time(
                replace(world, bodies=tuple(bodies)),
                command.sample_count
                * 1_000_000_000
                // VOCAL_SAMPLE_RATE_HZ,
            ), "applied"

        raise ValueError("unsupported embodiment command type")

    def _commit_authority_state(self, candidate: _AuthorityState) -> None:
        prepared = self._prepared_action_execution
        if (
            prepared is not None
            and self._committing_prepared_action_execution is not prepared
        ):
            raise RuntimeError(
                "embodiment world has a prepared action execution"
            )
        self._state = candidate

    def prepare_port_command(
        self,
        *,
        port_id: str,
        command_payload: bytes,
        causal_intent_receipt_sha256: str,
        expected_revision: int,
    ) -> PreparedActionExecution | ActionExecutionReceipt:
        """Prepare one opaque command without changing live physical state.

        Structurally rejected commands return their authenticated rejection
        receipt immediately because there is no transition to reserve.
        """

        port = _identifier(port_id, "embodiment port id")
        intent = _sha256_identity(causal_intent_receipt_sha256, "causal intent receipt")
        revision = _bounded_integer(expected_revision, "expected revision", minimum=0, maximum=MAX_REVISION)
        if (
            not isinstance(command_payload, bytes)
            or not command_payload
            or len(command_payload) > self._max_command_bytes
        ):
            raise ValueError("embodiment command payload exceeds its exact byte boundary")
        command_sha = _sha256(command_payload)

        with self._lock:
            self._require_public_visibility_locked()
            if self._prepared_action_execution is not None:
                raise RuntimeError(
                    "embodiment world already has a prepared action execution"
                )
            before_state = self._state
            before = before_state.observation
            lifecycle = ("received",)
            actor_by_port = {
                item.port_id: item.actor_body_id for item in self._actor_ports
            }
            actor_body_id = actor_by_port.get(port)
            if actor_body_id is None:
                return self._reject(
                    port_id=port,
                    actor_body_id=None,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="port_mismatch",
                    lifecycle=lifecycle,
                    before=before,
                )
            lifecycle += ("port_validated",)
            if revision != before.revision:
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="stale_world_revision",
                    lifecycle=lifecycle,
                    before=before,
                )
            if before.revision == MAX_REVISION:
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="world_revision_exhausted",
                    lifecycle=lifecycle,
                    before=before,
                )
            try:
                command = decode_command(command_payload, max_command_bytes=self._max_command_bytes)
            except ValueError:
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="command_not_canonical",
                    lifecycle=lifecycle,
                    before=before,
                )
            lifecycle += ("command_decoded",)
            transitioned, reason = self._transition(
                before_state.world, actor_body_id, command
            )
            if transitioned is None:
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason=reason,
                    lifecycle=lifecycle + ("geometry_rejected",),
                    before=before,
                )
            transitioned = replace(transitioned, revision=before.revision + 1)
            if isinstance(command, VocalizeCommand):
                consequence_lifecycle = "vocal_commitment_validated"
            elif isinstance(
                command,
                (TouchContactCommand, OralContactCommand),
            ):
                consequence_lifecycle = (
                    "material_contact_geometry_validated"
                )
            elif isinstance(command, AdvancePhysicalTimeCommand):
                consequence_lifecycle = (
                    "physical_time_transport_validated"
                )
            else:
                consequence_lifecycle = "geometry_validated"
            self._validate_world(transitioned)
            after = self._observation_for(transitioned)
            receipt = self._execution_receipt(
                port_id=port,
                actor_body_id=actor_body_id,
                causal_intent_receipt_sha256=intent,
                command_sha256=command_sha,
                expected_revision=revision,
                disposition="applied",
                reason="applied",
                elapsed_nanoseconds=_command_elapsed_nanoseconds(
                    command
                ),
                lifecycle=lifecycle + (consequence_lifecycle, "applied"),
                before=before,
                after=after,
            )
            retained = (before_state.recent_applied_receipts + (receipt,))[-self._receipt_capacity :]
            candidate = _AuthorityState(
                world=transitioned,
                observation=after,
                recent_applied_receipts=retained,
                migration_receipt=before_state.migration_receipt,
            )
            try:
                self._verify_state_capacity_for(candidate)
            except ValueError as error:
                if "byte capacity" not in str(error):
                    raise
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="state_capacity_exhausted",
                    lifecycle=lifecycle + (
                        consequence_lifecycle,
                        "state_capacity_rejected",
                    ),
                    before=before,
                )
            prepared = PreparedActionExecution(
                execution_receipt=receipt,
                _prior_state=before_state,
                _candidate_state=candidate,
                _construction_authority=(
                    _PREPARED_ACTION_EXECUTION_AUTHORITY
                ),
            )
            self._require_prepared_action_execution_locked(
                prepared,
                require_live=False,
            )
            self._prepared_action_execution = prepared
            return prepared

    def _require_prepared_action_execution_locked(
        self,
        prepared: PreparedActionExecution,
        *,
        require_live: bool = True,
    ) -> PreparedActionExecution:
        if (
            not isinstance(prepared, PreparedActionExecution)
            or prepared._construction_authority
            is not _PREPARED_ACTION_EXECUTION_AUTHORITY
            or (
                require_live
                and self._prepared_action_execution is not prepared
            )
        ):
            raise ValueError(
                "prepared embodiment action execution changed custody"
            )
        receipt = prepared.execution_receipt
        if (
            receipt.disposition != "applied"
            or receipt.before is not prepared._prior_state.observation
            or receipt.after is not prepared._candidate_state.observation
            or not prepared._candidate_state.recent_applied_receipts
            or prepared._candidate_state.recent_applied_receipts[-1]
            is not receipt
            or prepared._candidate_state.migration_receipt
            != prepared._prior_state.migration_receipt
        ):
            raise ValueError(
                "prepared embodiment action execution changed state"
            )
        return prepared

    def verify_prepared_action(
        self,
        prepared: PreparedActionExecution,
    ) -> None:
        """Verify that one prepared transition is still this world's live one."""

        with self._lock:
            current = self._require_prepared_action_execution_locked(prepared)
            if self._state is not current._prior_state:
                raise RuntimeError(
                    "prepared embodiment action world changed before commit"
                )

    @contextmanager
    def prepared_action_visibility_transaction(
        self,
        prepared: PreparedActionExecution,
    ):
        """Hide the physical commit until dependent sensory state installs."""

        with self._lock:
            current = self._require_prepared_action_execution_locked(
                prepared
            )
            if (
                self._state is not current._prior_state
                or self._visibility_prepared_action is not None
            ):
                raise RuntimeError(
                    "prepared embodiment visibility transaction changed"
                )
            self._visibility_prepared_action = current
            try:
                yield
            finally:
                self._visibility_prepared_action = None

    def commit_prepared_action(
        self,
        prepared: PreparedActionExecution,
    ) -> ActionExecutionReceipt:
        """Commit exactly one live prepared transition."""

        with self._lock:
            current = self._require_prepared_action_execution_locked(
                prepared
            )
            if self._state is not current._prior_state:
                raise RuntimeError(
                    "prepared embodiment action world changed before commit"
                )
            self._committing_prepared_action_execution = current
            try:
                self._commit_authority_state(current._candidate_state)
            except BaseException:
                self._state = current._prior_state
                raise
            finally:
                self._committing_prepared_action_execution = None
            self._prepared_action_execution = None
            return current.execution_receipt

    def encoded_committed_prepared_action(
        self,
        prepared: PreparedActionExecution,
    ) -> bytes:
        """Encode the hidden committed candidate for atomic persistence.

        Public snapshots remain refused while the visibility transaction is
        open.  The holder of the exact prepared capability may nevertheless
        persist that same committed candidate before a dependent organism
        successor becomes public.
        """

        with self._lock:
            current = self._require_prepared_action_execution_locked(
                prepared,
                require_live=False,
            )
            if (
                self._visibility_prepared_action is not current
                or self._state is not current._candidate_state
                or self._prepared_action_execution is not None
                or self._committing_prepared_action_execution is not None
            ):
                raise RuntimeError(
                    "committed prepared action is not the hidden world candidate"
                )
            return self._encoded_state_for(current._candidate_state)

    @contextmanager
    def committed_prepared_action_rollback_transaction(
        self,
        prepared: PreparedActionExecution,
    ):
        """Hold public visibility while one current prepared tail is undone."""

        with self._lock:
            current = self._require_prepared_action_execution_locked(
                prepared,
                require_live=False,
            )
            if (
                self._state is not current._candidate_state
                or self._prepared_action_execution is not None
                or self._committing_prepared_action_execution is not None
                or self._visibility_prepared_action is not None
            ):
                raise ValueError(
                    "committed embodiment action tail changed"
                )
            rolled_back = [False]
            self._visibility_prepared_action = current

            def rollback_now() -> None:
                assert not rolled_back[0]
                self._state = current._prior_state
                rolled_back[0] = True

            try:
                yield rollback_now
            finally:
                self._visibility_prepared_action = None

    def discard_prepared_action(
        self,
        prepared: PreparedActionExecution,
    ) -> None:
        """Release one uncommitted transition without changing the world."""

        with self._lock:
            self._require_prepared_action_execution_locked(prepared)
            self._prepared_action_execution = None

    def execute_port_command(
        self,
        *,
        port_id: str,
        command_payload: bytes,
        causal_intent_receipt_sha256: str,
        expected_revision: int,
    ) -> ActionExecutionReceipt:
        """Execute one command while preserving the historical atomic API."""

        with self._lock:
            prepared = self.prepare_port_command(
                port_id=port_id,
                command_payload=command_payload,
                causal_intent_receipt_sha256=(
                    causal_intent_receipt_sha256
                ),
                expected_revision=expected_revision,
            )
            if isinstance(prepared, ActionExecutionReceipt):
                return prepared
            try:
                return self.commit_prepared_action(prepared)
            except BaseException:
                if self._prepared_action_execution is prepared:
                    self.discard_prepared_action(prepared)
                raise

    def recent_applied_receipts(self) -> tuple[ActionExecutionReceipt, ...]:
        with self._lock:
            self._require_public_visibility_locked()
            return self._state.recent_applied_receipts

    def verify_execution_receipt(self, receipt: ActionExecutionReceipt) -> None:
        """Verify one self-contained applied W1 execution authority.

        Verification authenticates the exact before/after geometry and command
        identity.  It does not require the receipt to remain in the bounded
        recent-receipt window.
        """

        if not isinstance(receipt, ActionExecutionReceipt):
            raise ValueError("execution receipt is not typed")
        with self._lock:
            self._verify_execution(receipt)

    def execution_receipt_from_record(
        self,
        record: object,
    ) -> ActionExecutionReceipt:
        """Decode and authenticate one exact applied execution record.

        This is the public cold-custody counterpart to
        :meth:`verify_execution_receipt`.  It accepts no compatibility
        projection and reconstructs the complete signed before/after world
        geometry before returning the typed receipt.
        """

        with self._lock:
            return self._execution_from_record(record)

    def verify_observation_snapshot(
        self, observation: ObservationSnapshot
    ) -> None:
        """Verify one self-contained authenticated W1 observation."""

        if not isinstance(observation, ObservationSnapshot):
            raise ValueError("observation snapshot is not typed")
        with self._lock:
            self._verify_observation(observation)

    def _verify_observation(self, observation: ObservationSnapshot) -> None:
        world = _WorldState(
            revision=observation.revision,
            room_id=observation.room_id,
            room_bounds=observation.room_bounds,
            regions=observation.regions,
            portals=observation.portals,
            self_body_id=observation.self_body_id,
            bodies=observation.bodies,
            objects=observation.objects,
        )
        self._validate_world(world)
        expected = self._observation_for(world)
        if expected != observation:
            raise ValueError("observation authentication changed")

    def _verify_execution(self, receipt: ActionExecutionReceipt) -> None:
        if receipt.disposition != "applied" or receipt.reason != "applied":
            raise ValueError("retained execution must be applied")
        if receipt.lifecycle[-2:] not in (
            ("geometry_validated", "applied"),
            ("vocal_commitment_validated", "applied"),
            ("material_contact_geometry_validated", "applied"),
            ("physical_time_transport_validated", "applied"),
        ):
            raise ValueError("retained execution lifecycle changed")
        elapsed = _bounded_integer(
            receipt.elapsed_nanoseconds,
            "execution elapsed time",
            minimum=0,
            maximum=MAX_MATERIAL_ACTION_DURATION_US * 1_000,
        )
        timed_lifecycles = {
            ("geometry_validated", "applied"),
            ("vocal_commitment_validated", "applied"),
            ("material_contact_geometry_validated", "applied"),
            ("physical_time_transport_validated", "applied"),
        }
        if (
            receipt.lifecycle[-2:] in timed_lifecycles
            and elapsed == 0
        ):
            raise ValueError(
                "execution elapsed time differs from physical lifecycle"
            )
        port_actor = next(
            (
                item.actor_body_id
                for item in self._actor_ports
                if item.port_id == receipt.port_id
            ),
            None,
        )
        if port_actor is None or receipt.actor_body_id != port_actor:
            raise ValueError("retained execution port changed")
        _sha256_identity(receipt.causal_intent_receipt_sha256, "causal intent receipt")
        _sha256_identity(receipt.command_sha256, "command identity")
        self._verify_observation(receipt.before)
        self._verify_observation(receipt.after)
        if (
            receipt.expected_revision != receipt.before.revision
            or receipt.observed_revision != receipt.before.revision
            or receipt.after.revision != receipt.before.revision + 1
        ):
            raise ValueError("retained execution revision chain changed")
        unsigned = receipt._canonical_unsigned_record()
        expected_hmac = _sign(self._key, EXECUTION_DOMAIN, unsigned)
        if not hmac.compare_digest(expected_hmac, receipt.authority_hmac_sha256):
            raise ValueError("execution HMAC changed")
        expected_receipt = _digest({"authority_hmac_sha256": expected_hmac, "payload": unsigned})
        if expected_receipt != receipt.authority_receipt_sha256:
            raise ValueError("execution receipt identity changed")

    @staticmethod
    def _optical_surface_content_sha(
        surface: ObjectOpticalSurface,
    ) -> str:
        surface.verify()
        return _sha256(surface._canonical_fragment().encoded)

    def _optical_surface_catalog_for(
        self,
        state: _AuthorityState,
    ) -> dict[str, ObjectOpticalSurface]:
        objects: list[EmbodiedObject] = list(state.world.objects)
        for receipt in state.recent_applied_receipts:
            objects.extend(receipt.before.objects)
            objects.extend(receipt.after.objects)
        catalog: dict[str, ObjectOpticalSurface] = {}
        for item in objects:
            surface = item.optical_surface
            if surface is None:
                continue
            content_sha = self._optical_surface_content_sha(surface)
            prior = catalog.get(content_sha)
            if prior is not None and prior != surface:
                raise ValueError("optical surface content identity collided")
            catalog[content_sha] = surface
        return dict(sorted(catalog.items()))

    def _compact_object_record(
        self,
        item: EmbodiedObject,
        catalog: Mapping[str, ObjectOpticalSurface],
    ) -> dict[str, object]:
        item.verify()
        record = item._canonical_record()
        surface = item.optical_surface
        if surface is None:
            return record
        content_sha = self._optical_surface_content_sha(surface)
        if catalog.get(content_sha) != surface:
            raise ValueError("optical surface is absent from exact catalog")
        record["optical_surface"] = {"content_sha256": content_sha}
        return record

    def _compact_world_record(
        self,
        world: _WorldState,
        catalog: Mapping[str, ObjectOpticalSurface],
    ) -> dict[str, object]:
        return {
            "bodies": [item.as_record() for item in world.bodies],
            "objects": [
                self._compact_object_record(item, catalog)
                for item in world.objects
            ],
            "revision": world.revision,
            "room_bounds": world.room_bounds.as_record(),
            "room_id": world.room_id,
            "regions": [item.as_record() for item in world.regions],
            "portals": [item.as_record() for item in world.portals],
            "self_body_id": world.self_body_id,
        }

    def _compact_observation_record(
        self,
        observation: ObservationSnapshot,
        catalog: Mapping[str, ObjectOpticalSurface],
    ) -> dict[str, object]:
        record = observation._canonical_record()
        record["objects"] = [
            self._compact_object_record(item, catalog)
            for item in observation.objects
        ]
        return record
    def _compact_execution_record(
        self,
        receipt: ActionExecutionReceipt,
        catalog: Mapping[str, ObjectOpticalSurface],
    ) -> dict[str, object]:
        record = receipt._canonical_record()
        record["before"] = self._compact_observation_record(receipt.before, catalog)
        record["after"] = self._compact_observation_record(receipt.after, catalog)
        return record

    def _state_payload_for(self, state: _AuthorityState) -> dict[str, object]:
        catalog = self._optical_surface_catalog_for(state)
        return {
            "actor_ports": [item.as_record() for item in self._actor_ports],
            "limits": {
                "max_regions": self._max_regions,
                "max_portals": self._max_portals,
                "max_bodies": self._max_bodies,
                "max_command_bytes": self._max_command_bytes,
                "max_encoded_state_bytes": self._max_encoded_state_bytes,
                "max_objects": self._max_objects,
                "receipt_capacity": self._receipt_capacity,
            },
            "migration_receipt": (
                state.migration_receipt.as_record()
                if state.migration_receipt is not None
                else None
            ),
            "optical_surface_catalog": [
                {"content_sha256": content_sha,
                 "surface": surface._canonical_fragment()}
                for content_sha, surface in catalog.items()
            ],

            "recent_applied_receipts": [
                self._compact_execution_record(item, catalog)
                for item in state.recent_applied_receipts
            ],
            "schema": STATE_SCHEMA,
            "world": self._compact_world_record(state.world, catalog),
        }

    def _v6_state_payload_for(self, state: _AuthorityState) -> dict[str, object]:
        return {
            "actor_ports": [item.as_record() for item in self._actor_ports],
            "limits": {
                "max_regions": self._max_regions,
                "max_portals": self._max_portals,
                "max_bodies": self._max_bodies,
                "max_command_bytes": self._max_command_bytes,
                "max_encoded_state_bytes": self._max_encoded_state_bytes,
                "max_objects": self._max_objects,
                "receipt_capacity": self._receipt_capacity,
            },
            "migration_receipt": (
                state.migration_receipt.as_record()
                if state.migration_receipt is not None
                else None
            ),
            "recent_applied_receipts": [
                item._canonical_record()
                for item in state.recent_applied_receipts
            ],
            "schema": V6_STATE_SCHEMA,
            "world": state.world._canonical_record(),
        }

    def _encoded_state_for(self, state: _AuthorityState) -> bytes:
        payload = _canonical(self._state_payload_for(state))
        if len(payload) > self._max_encoded_state_bytes:
            raise ValueError("embodiment state exceeds its exact byte capacity")
        signature = hmac.new(self._key, STATE_DOMAIN + payload, hashlib.sha256).hexdigest()
        envelope = {
            "authority_hmac_sha256": signature,
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
        }
        encoded = _canonical(envelope)
        if len(encoded) > self._max_encoded_state_bytes:
            raise ValueError("encoded embodiment state exceeds its exact byte capacity")
        return encoded

    def _verify_state_capacity_for(self, state: _AuthorityState) -> None:
        """Prove persistence extent without constructing a persistence image."""

        payload_byte_count = _canonical_byte_count(
            self._state_payload_for(state)
        )
        if payload_byte_count > self._max_encoded_state_bytes:
            raise ValueError(
                "embodiment state exceeds its exact byte capacity"
            )
        payload_base64_byte_count = 4 * (
            (payload_byte_count + 2) // 3
        )
        empty_envelope_byte_count = _canonical_byte_count(
            {
                "authority_hmac_sha256": "0" * 64,
                "payload_base64": "",
                "schema": ENVELOPE_SCHEMA,
            }
        )
        encoded_byte_count = (
            empty_envelope_byte_count + payload_base64_byte_count
        )
        if encoded_byte_count > self._max_encoded_state_bytes:
            raise ValueError(
                "encoded embodiment state exceeds its exact byte capacity"
            )

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            self._require_public_visibility_locked()
            return self._encoded_state_for(self._state)

    def _observation_from_record(self, value: object) -> ObservationSnapshot:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "bodies",
            "objects",
            "portals",
            "regions",
            "revision",
            "room_bounds",
            "room_id",
            "schema",
            "self_body_id",
            "state_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected or value.get("schema") != OBSERVATION_SCHEMA:
            raise ValueError("observation record fields changed")
        raw_objects = value.get("objects")
        raw_bodies = value.get("bodies")
        raw_regions = value.get("regions")
        raw_portals = value.get("portals")
        if not isinstance(raw_bodies, list) or not 2 <= len(raw_bodies) <= self._max_bodies:
            raise ValueError("observation bodies changed")
        if not isinstance(raw_objects, list) or not 1 <= len(raw_objects) <= self._max_objects:
            raise ValueError("observation objects changed")
        result = ObservationSnapshot(
            revision=value.get("revision"),
            room_id=value.get("room_id"),
            room_bounds=_room_from(value.get("room_bounds")),
            regions=tuple(_region_from(item) for item in raw_regions)
            if isinstance(raw_regions, list) else (),
            portals=tuple(_portal_from(item) for item in raw_portals)
            if isinstance(raw_portals, list) else (),
            self_body_id=_identifier(value.get("self_body_id"), "self body id"),
            bodies=tuple(_body_from(item) for item in raw_bodies),
            objects=tuple(_object_from(item) for item in raw_objects),
            state_sha256=_sha256_identity(value.get("state_sha256"), "observation state identity"),
            authority_hmac_sha256=_sha256_identity(value.get("authority_hmac_sha256"), "observation HMAC"),
            authority_receipt_sha256=_sha256_identity(value.get("authority_receipt_sha256"), "observation receipt"),
        )
        if result.as_record() != dict(value):
            raise ValueError("observation record is not canonical")
        self._verify_observation(result)
        return result

    def _execution_from_record(self, value: object) -> ActionExecutionReceipt:
        expected = {
            "actor_body_id",
            "after",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "before",
            "causal_intent_receipt_sha256",
            "command_sha256",
            "disposition",
            "elapsed_nanoseconds",
            "expected_revision",
            "lifecycle",
            "observed_revision",
            "port_id",
            "reason",
            "schema",
        }
        if not isinstance(value, Mapping) or set(value) != expected or value.get("schema") != EXECUTION_SCHEMA:
            raise ValueError("execution record fields changed")
        lifecycle = value.get("lifecycle")
        if not isinstance(lifecycle, list) or not lifecycle or any(not isinstance(item, str) for item in lifecycle):
            raise ValueError("execution lifecycle changed")
        result = ActionExecutionReceipt(
            port_id=_identifier(value.get("port_id"), "execution port id"),
            actor_body_id=_identifier(
                value.get("actor_body_id"), "execution actor body id"
            ),
            causal_intent_receipt_sha256=_sha256_identity(value.get("causal_intent_receipt_sha256"), "causal intent receipt"),
            command_sha256=_sha256_identity(value.get("command_sha256"), "command identity"),
            expected_revision=_bounded_integer(value.get("expected_revision"), "expected revision", minimum=0, maximum=MAX_REVISION),
            observed_revision=_bounded_integer(value.get("observed_revision"), "observed revision", minimum=0, maximum=MAX_REVISION),
            disposition=value.get("disposition"),
            reason=value.get("reason"),
            elapsed_nanoseconds=_bounded_integer(
                value.get("elapsed_nanoseconds"),
                "execution elapsed time",
                minimum=0,
                maximum=MAX_MATERIAL_ACTION_DURATION_US * 1_000,
            ),
            lifecycle=tuple(lifecycle),
            before=self._observation_from_record(value.get("before")),
            after=self._observation_from_record(value.get("after")),
            authority_hmac_sha256=_sha256_identity(value.get("authority_hmac_sha256"), "execution HMAC"),
            authority_receipt_sha256=_sha256_identity(value.get("authority_receipt_sha256"), "execution receipt"),
        )
        if result.as_record() != dict(value):
            raise ValueError("execution record is not canonical")
        self._verify_execution(result)
        return result

    def _optical_surface_catalog_from_record(
        self,
        value: object,
    ) -> dict[str, ObjectOpticalSurface]:
        if (
            not isinstance(value, list)
            or len(value) > self._max_objects
        ):
            raise ValueError("optical surface catalog exceeds capacity")
        catalog: dict[str, ObjectOpticalSurface] = {}
        prior_sha: str | None = None
        for entry in value:
            if (
                not isinstance(entry, Mapping)
                or set(entry) != {"content_sha256", "surface"}
            ):
                raise ValueError("optical surface catalog fields changed")
            content_sha = _sha256_identity(entry.get("content_sha256"), "optical surface content")
            if prior_sha is not None and content_sha <= prior_sha:
                raise ValueError("optical surface catalog order changed")
            surface = _optical_surface_from(entry.get("surface"))
            if self._optical_surface_content_sha(surface) != content_sha:
                raise ValueError("optical surface catalog content changed")
            catalog[content_sha] = surface
            prior_sha = content_sha
        return catalog

    def _object_from_compact_record(
        self,
        value: object,
        catalog: Mapping[str, ObjectOpticalSurface],
    ) -> EmbodiedObject:
        expected = {
            "held_by_body_id", "mass_grams", "material", "object_id",
            "position", "radius_mm", "reflectance_ppm", "optical_surface",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("compact physical object record changed")
        raw_position = value.get("position")
        raw_material = value.get("material")
        raw_surface = value.get("optical_surface")
        surface = None
        if raw_surface is not None:
            if (
                not isinstance(raw_surface, Mapping)
                or set(raw_surface) != {"content_sha256"}
            ):
                raise ValueError("optical surface reference fields changed")
            content_sha = _sha256_identity(raw_surface.get("content_sha256"), "optical surface reference")
            surface = catalog.get(content_sha)
            if surface is None:
                raise ValueError("optical surface reference is unresolved")
        result = EmbodiedObject(
            object_id=value.get("object_id"),
            radius_mm=value.get("radius_mm"),
            mass_grams=value.get("mass_grams"),
            position=_position_from(raw_position, "object position") if raw_position is not None else None,
            held_by_body_id=value.get("held_by_body_id"),
            reflectance_ppm=_physical_bands(
                tuple(value.get("reflectance_ppm"))
                if isinstance(value.get("reflectance_ppm"), list)
                else value.get("reflectance_ppm"),
                "object reflectance",
            ),
            material=(
                _material_from(raw_material)
                if raw_material is not None
                else None
            ),
            optical_surface=surface,
        )
        result.verify()
        if self._compact_object_record(result, catalog) != dict(value):
            raise ValueError("compact physical object is not canonical")

        return result
    def _observation_from_compact_record(
        self,
        value: object,
        catalog: Mapping[str, ObjectOpticalSurface],
    ) -> ObservationSnapshot:
        expected = {
            "authority_hmac_sha256", "authority_receipt_sha256", "bodies", "objects",
            "portals", "regions", "revision", "room_bounds", "room_id",
            "schema", "self_body_id", "state_sha256",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != OBSERVATION_SCHEMA
        ):
            raise ValueError("compact observation record changed")
        raw_objects = value.get("objects")
        raw_bodies = value.get("bodies")
        raw_regions = value.get("regions")
        raw_portals = value.get("portals")
        if not isinstance(raw_bodies, list) or not 2 <= len(raw_bodies) <= self._max_bodies:
            raise ValueError("compact observation bodies changed")
        if not isinstance(raw_objects, list) or not 1 <= len(raw_objects) <= self._max_objects:
            raise ValueError("compact observation objects changed")
        objects = tuple(
            self._object_from_compact_record(item, catalog)
            for item in raw_objects
        )
        result = ObservationSnapshot(
            revision=_bounded_integer(value.get("revision"), "observation revision", minimum=0, maximum=MAX_REVISION),
            room_id=_identifier(value.get("room_id"), "observation room id"),
            room_bounds=_room_from(value.get("room_bounds")),
            regions=tuple(_region_from(item) for item in raw_regions)
            if isinstance(raw_regions, list) else (),
            portals=tuple(_portal_from(item) for item in raw_portals)
            if isinstance(raw_portals, list) else (),
            self_body_id=_identifier(value.get("self_body_id"), "self body id"),
            bodies=tuple(_body_from(item) for item in raw_bodies),
            objects=objects,
            state_sha256=_sha256_identity(value.get("state_sha256"), "observation state identity"),
            authority_hmac_sha256=_sha256_identity(value.get("authority_hmac_sha256"), "observation HMAC"),
            authority_receipt_sha256=_sha256_identity(value.get("authority_receipt_sha256"), "observation receipt"),
        )
        self._verify_observation(result)
        if self._compact_observation_record(result, catalog) != dict(value):
            raise ValueError("compact observation is not canonical")
        return result

    def _execution_from_compact_record(
        self,
        value: object,
        catalog: Mapping[str, ObjectOpticalSurface],
    ) -> ActionExecutionReceipt:
        expected = {
            "actor_body_id", "after", "authority_hmac_sha256", "authority_receipt_sha256",
            "before", "causal_intent_receipt_sha256", "command_sha256", "disposition",
            "elapsed_nanoseconds", "expected_revision", "lifecycle", "observed_revision",
            "port_id", "reason", "schema",
        }
        if not isinstance(value, Mapping) or set(value) != expected or value.get("schema") != EXECUTION_SCHEMA:
            raise ValueError("compact execution record changed")
        lifecycle = value.get("lifecycle")
        if not isinstance(lifecycle, list) or not lifecycle or any(not isinstance(item, str) for item in lifecycle):
            raise ValueError("compact execution lifecycle changed")
        before = self._observation_from_compact_record(value.get("before"), catalog)
        after = self._observation_from_compact_record(value.get("after"), catalog)
        result = ActionExecutionReceipt(
            port_id=_identifier(value.get("port_id"), "execution port id"),
            actor_body_id=_identifier(value.get("actor_body_id"), "execution actor body id"),
            causal_intent_receipt_sha256=_sha256_identity(value.get("causal_intent_receipt_sha256"), "causal intent receipt"),
            command_sha256=_sha256_identity(value.get("command_sha256"), "command identity"),
            expected_revision=_bounded_integer(value.get("expected_revision"), "expected revision", minimum=0, maximum=MAX_REVISION),
            observed_revision=_bounded_integer(value.get("observed_revision"), "observed revision", minimum=0, maximum=MAX_REVISION),
            disposition=value.get("disposition"),
            reason=value.get("reason"),
            elapsed_nanoseconds=_bounded_integer(
                value.get("elapsed_nanoseconds"),
                "execution elapsed time",
                minimum=0,
                maximum=MAX_MATERIAL_ACTION_DURATION_US * 1_000,
            ),
            lifecycle=tuple(lifecycle),
            before=before,
            after=after,
            authority_hmac_sha256=_sha256_identity(value.get("authority_hmac_sha256"), "execution HMAC"),
            authority_receipt_sha256=_sha256_identity(value.get("authority_receipt_sha256"), "execution receipt"),
        )
        self._verify_execution(result)
        if self._compact_execution_record(result, catalog) != dict(value):
            raise ValueError("compact execution is not canonical")
        return result

    def _world_from_compact_record(
        self,
        value: object,
        catalog: Mapping[str, ObjectOpticalSurface],
    ) -> _WorldState:
        expected = {
            "bodies", "objects", "portals", "regions", "revision",
            "room_bounds", "room_id", "self_body_id"
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("compact world state fields changed")
        raw_objects = value.get("objects")
        raw_bodies = value.get("bodies")
        raw_regions = value.get("regions")
        raw_portals = value.get("portals")
        if not isinstance(raw_bodies, list) or not 2 <= len(raw_bodies) <= self._max_bodies:
            raise ValueError("compact world body inventory changed")
        if not isinstance(raw_objects, list) or not 1 <= len(raw_objects) <= self._max_objects:
            raise ValueError("compact world object inventory changed")
        objects = tuple(
            self._object_from_compact_record(item, catalog)
            for item in raw_objects
        )
        world = _WorldState(
            revision=_bounded_integer(value.get("revision"), "world revision", minimum=0, maximum=MAX_REVISION),
            room_id=_identifier(value.get("room_id"), "room id"),
            room_bounds=_room_from(value.get("room_bounds")),
            regions=tuple(_region_from(item) for item in raw_regions)
            if isinstance(raw_regions, list) else (),
            portals=tuple(_portal_from(item) for item in raw_portals)
            if isinstance(raw_portals, list) else (),
            self_body_id=_identifier(value.get("self_body_id"), "self body id"),
            bodies=tuple(_body_from(item) for item in raw_bodies),
            objects=objects,
        )
        self._validate_world(world)
        if self._compact_world_record(world, catalog) != dict(value):
            raise ValueError("compact world state is not canonical")
        return world

    def _world_from_record(self, value: object) -> _WorldState:
        expected = {
            "bodies", "objects", "portals", "regions", "revision",
            "room_bounds", "room_id", "self_body_id"
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ValueError("world state fields changed")
        raw_objects = value.get("objects")
        raw_bodies = value.get("bodies")
        raw_regions = value.get("regions")
        raw_portals = value.get("portals")
        if not isinstance(raw_bodies, list) or not 2 <= len(raw_bodies) <= self._max_bodies:
            raise ValueError("world body inventory changed")
        if not isinstance(raw_objects, list) or not 1 <= len(raw_objects) <= self._max_objects:
            raise ValueError("world object inventory changed")
        world = _WorldState(
            revision=_bounded_integer(value.get("revision"), "world revision", minimum=0, maximum=MAX_REVISION),
            room_id=_identifier(value.get("room_id"), "room id"),
            room_bounds=_room_from(value.get("room_bounds")),
            regions=tuple(_region_from(item) for item in raw_regions)
            if isinstance(raw_regions, list) else (),
            portals=tuple(_portal_from(item) for item in raw_portals)
            if isinstance(raw_portals, list) else (),
            self_body_id=_identifier(value.get("self_body_id"), "self body id"),
            bodies=tuple(_body_from(item) for item in raw_bodies),
            objects=tuple(_object_from(item) for item in raw_objects),
        )
        self._validate_world(world)
        if world.as_record() != dict(value):
            raise ValueError("world state is not canonical")
        return world

    def _migration_receipt_for(
        self,
        *,
        prior_envelope_sha256: str,
        prior_observation_receipt_sha256: str,
        resulting_observation_receipt_sha256: str,
        prior_revision: int,
        resulting_revision: int,
        parent_migration_receipt_sha256: str | None,
        manifest_sha256: str,
        prior_topology_sha256: str,
        resulting_topology_sha256: str,
    ) -> WorldMigrationReceipt:
        unsigned = {
            "manifest_sha256": manifest_sha256,
            "parent_migration_receipt_sha256": parent_migration_receipt_sha256,
            "prior_envelope_sha256": prior_envelope_sha256,
            "prior_observation_receipt_sha256": prior_observation_receipt_sha256,
            "prior_revision": prior_revision,
            "resulting_observation_receipt_sha256": resulting_observation_receipt_sha256,
            "resulting_revision": resulting_revision,
            "prior_topology_sha256": prior_topology_sha256,
            "resulting_topology_sha256": resulting_topology_sha256,
            "schema": MIGRATION_SCHEMA,
        }
        signature = _sign(self._key, MIGRATION_DOMAIN, unsigned)
        return WorldMigrationReceipt(
            prior_envelope_sha256=prior_envelope_sha256,
            prior_observation_receipt_sha256=prior_observation_receipt_sha256,
            resulting_observation_receipt_sha256=resulting_observation_receipt_sha256,
            prior_revision=prior_revision,
            resulting_revision=resulting_revision,
            parent_migration_receipt_sha256=parent_migration_receipt_sha256,
            manifest_sha256=manifest_sha256,
            prior_topology_sha256=prior_topology_sha256,
            resulting_topology_sha256=resulting_topology_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest(
                {"authority_hmac_sha256": signature, "payload": unsigned}
            ),
        )

    def _verify_migration_receipt(
        self,
        receipt: WorldMigrationReceipt,
        world: _WorldState,
        *,
        require_current_manifest: bool = True,
    ) -> None:
        if not isinstance(receipt, WorldMigrationReceipt):
            raise ValueError("world migration receipt is not typed")
        for value, name in (
            (receipt.prior_envelope_sha256, "prior envelope"),
            (receipt.prior_observation_receipt_sha256, "prior observation"),
            (receipt.resulting_observation_receipt_sha256, "resulting observation"),
            (receipt.manifest_sha256, "migration manifest"),
            (receipt.prior_topology_sha256, "prior topology"),
            (receipt.resulting_topology_sha256, "resulting topology"),
        ):
            _sha256_identity(value, name)
        if receipt.parent_migration_receipt_sha256 is not None:
            _sha256_identity(
                receipt.parent_migration_receipt_sha256,
                "parent migration receipt",
            )
        _bounded_integer(
            receipt.prior_revision,
            "migration prior revision",
            minimum=0,
            maximum=MAX_REVISION,
        )
        _bounded_integer(
            receipt.resulting_revision,
            "migration resulting revision",
            minimum=1,
            maximum=MAX_REVISION,
        )
        if (
            receipt.resulting_revision != receipt.prior_revision + 1
            or receipt.resulting_revision > world.revision
            or (
                require_current_manifest
                and receipt.manifest_sha256
                != self._physical_manifest_sha256()
            )
            or receipt.resulting_topology_sha256
            != self._topology_sha256(world.regions, world.portals)
        ):
            raise ValueError("world migration causal chain changed")
        unsigned = receipt.unsigned_record()
        expected_hmac = _sign(self._key, MIGRATION_DOMAIN, unsigned)
        if not hmac.compare_digest(
            expected_hmac, receipt.authority_hmac_sha256
        ):
            raise ValueError("world migration HMAC changed")
        if receipt.authority_receipt_sha256 != _digest(
            {"authority_hmac_sha256": expected_hmac, "payload": unsigned}
        ):
            raise ValueError("world migration identity changed")

    def _migration_from_record(
        self,
        value: object,
        world: _WorldState,
        *,
        require_current_manifest: bool = True,
    ) -> WorldMigrationReceipt:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "manifest_sha256",
            "parent_migration_receipt_sha256",
            "prior_envelope_sha256",
            "prior_observation_receipt_sha256",
            "prior_revision",
            "prior_topology_sha256",
            "resulting_observation_receipt_sha256",
            "resulting_revision",
            "resulting_topology_sha256",
            "schema",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != MIGRATION_SCHEMA
        ):
            raise ValueError("world migration fields changed")
        result = WorldMigrationReceipt(
            prior_envelope_sha256=_sha256_identity(
                value.get("prior_envelope_sha256"), "prior envelope"
            ),
            prior_observation_receipt_sha256=_sha256_identity(
                value.get("prior_observation_receipt_sha256"),
                "prior observation",
            ),
            resulting_observation_receipt_sha256=_sha256_identity(
                value.get("resulting_observation_receipt_sha256"),
                "resulting observation",
            ),
            prior_revision=_bounded_integer(
                value.get("prior_revision"),
                "migration prior revision",
                minimum=0,
                maximum=MAX_REVISION,
            ),
            resulting_revision=_bounded_integer(
                value.get("resulting_revision"),
                "migration resulting revision",
                minimum=1,
                maximum=MAX_REVISION,
            ),
            parent_migration_receipt_sha256=(
                _sha256_identity(
                    value.get("parent_migration_receipt_sha256"),
                    "parent migration receipt",
                )
                if value.get("parent_migration_receipt_sha256") is not None
                else None
            ),
            manifest_sha256=_sha256_identity(
                value.get("manifest_sha256"), "migration manifest"
            ),
            prior_topology_sha256=_sha256_identity(
                value.get("prior_topology_sha256"), "prior topology"
            ),
            resulting_topology_sha256=_sha256_identity(
                value.get("resulting_topology_sha256"), "resulting topology"
            ),
            authority_hmac_sha256=_sha256_identity(
                value.get("authority_hmac_sha256"), "migration HMAC"
            ),
            authority_receipt_sha256=_sha256_identity(
                value.get("authority_receipt_sha256"), "migration receipt"
            ),
        )
        if result.as_record() != dict(value):
            raise ValueError("world migration record is not canonical")
        self._verify_migration_receipt(
            result,
            world,
            require_current_manifest=require_current_manifest,
        )
        return result

    def _topology_sha256(
        self,
        regions: tuple[PhysicalRegion, ...],
        portals: tuple[PhysicalPortal, ...],
    ) -> str:
        return _digest(
            {
                "portals": [item.as_record() for item in portals],
                "regions": [item.as_record() for item in regions],
            }
        )

    def _physical_manifest_sha256(self) -> str:
        return _digest(
            {
                "object_physics": [
                    item.as_record()
                    for item in _default_objects()
                ],
                "portals": [item.as_record() for item in _default_portals()],
                "regions": [item.as_record() for item in _default_regions()],
            }
        )

    def _decode_authenticated_envelope(
        self, encoded: bytes, *, envelope_schema: str, domain: bytes, limit: int
    ) -> tuple[Mapping[str, object], bytes]:
        if not isinstance(encoded, bytes) or not encoded or len(encoded) > limit:
            raise ValueError("encoded embodiment state exceeds its exact byte capacity")
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("embodiment state envelope is not canonical JSON") from error
        expected_envelope = {"authority_hmac_sha256", "payload_base64", "schema"}
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != expected_envelope
            or envelope.get("schema") != envelope_schema
        ):
            raise ValueError("embodiment state envelope fields changed")
        if _canonical(envelope) != encoded:
            raise ValueError("embodiment state envelope is not canonical")
        try:
            payload = base64.b64decode(
                envelope.get("payload_base64"), validate=True
            )
        except Exception as error:
            raise ValueError("embodiment state payload is not canonical base64") from error
        if not payload or len(payload) > limit:
            raise ValueError("embodiment state payload exceeds its exact byte capacity")
        provided_hmac = _sha256_identity(
            envelope.get("authority_hmac_sha256"), "state HMAC"
        )
        expected_hmac = hmac.new(
            self._key, domain + payload, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_hmac, provided_hmac):
            raise ValueError("embodiment state HMAC changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("embodiment state payload is not canonical JSON") from error
        if not isinstance(decoded, Mapping) or _canonical(decoded) != payload:
            raise ValueError("embodiment state payload is not canonical")
        return decoded, payload

    def _migrated_objects(
        self,
        prior_objects: tuple[EmbodiedObject, ...],
        *,
        preserve_material: bool = False,
    ) -> tuple[EmbodiedObject, ...]:
        migrated: list[EmbodiedObject] = []
        present: set[str] = set()
        for item in prior_objects:
            if item.object_id in present:
                raise ValueError("prior world object identities repeat")
            present.add(item.object_id)
            migrated.append(
                item
                if preserve_material
                else replace(
                    item,
                    material=None,
                    optical_surface=None,
                )
            )
        from dsf_ai_service.substrate.approved_curriculum_physical_surfaces import (
            approved_curriculum_physical_surfaces,
        )
        for item in approved_curriculum_physical_surfaces():
            if item.object_id not in present:
                migrated.append(item)
                present.add(item.object_id)
        if len(migrated) > self._max_objects:
            raise ValueError("migrated world object inventory exceeds capacity")
        return tuple(sorted(migrated, key=lambda item: item.object_id))

    def _commit_migrated_world(
        self,
        *,
        encoded: bytes,
        prior_revision: int,
        prior_room_id: str,
        prior_room_bounds: RoomBoundsMM,
        prior_bodies: tuple[EmbodiedBody, ...],
        prior_objects: tuple[EmbodiedObject, ...],
        prior_observation_unsigned: Mapping[str, object],
        prior_observation_domain: bytes,
        parent_migration_receipt_sha256: str | None,
        preserve_material: bool = False,
    ) -> None:
        regions = _default_regions()
        portals = _default_portals()
        self_body_id = self._state.world.self_body_id
        bodies = prior_bodies
        if {item.body_id for item in bodies} != {
            item.actor_body_id for item in self._actor_ports
        }:
            raise ValueError("prior physical bodies differ from actor port topology")
        if self_body_id not in {item.body_id for item in bodies}:
            raise ValueError("prior world self body changed")
        self_body = next(item for item in bodies if item.body_id == self_body_id)
        current_region = self._region_containing(
            regions, self_body.pose.position, self_body.radius_mm
        )
        if current_region is None:
            raise ValueError("prior self body is outside the v3 physical topology")
        migrated_world = _WorldState(
            revision=prior_revision + 1,
            room_id=current_region.region_id,
            room_bounds=current_region.bounds,
            regions=regions,
            portals=portals,
            self_body_id=self_body_id,
            bodies=tuple(sorted(bodies, key=lambda item: item.body_id)),
            objects=self._migrated_objects(
                prior_objects,
                preserve_material=preserve_material,
            ),
        )
        try:
            self._validate_world(migrated_world)
        except ValueError as error:
            raise ValueError(
                "prior physical state cannot settle into the current topology"
            ) from error
        prior_hmac = _sign(
            self._key, prior_observation_domain, prior_observation_unsigned
        )
        prior_observation_receipt = _digest(
            {
                "authority_hmac_sha256": prior_hmac,
                "payload": prior_observation_unsigned,
            }
        )
        resulting_observation = self._observation_for(migrated_world)
        migration = self._migration_receipt_for(
            prior_envelope_sha256=hashlib.sha256(encoded).hexdigest(),
            prior_observation_receipt_sha256=prior_observation_receipt,
            resulting_observation_receipt_sha256=(
                resulting_observation.authority_receipt_sha256
            ),
            prior_revision=prior_revision,
            resulting_revision=migrated_world.revision,
            parent_migration_receipt_sha256=parent_migration_receipt_sha256,
            manifest_sha256=self._physical_manifest_sha256(),
            prior_topology_sha256=_digest(
                {
                    "room_bounds": prior_room_bounds.as_record(),
                    "room_id": prior_room_id,
                }
            ),
            resulting_topology_sha256=self._topology_sha256(regions, portals),
        )
        candidate = _AuthorityState(
            world=migrated_world,
            observation=resulting_observation,
            recent_applied_receipts=(),
            migration_receipt=migration,
        )
        self._encoded_state_for(candidate)
        with self._lock:
            before_state = self._state
            try:
                self._commit_authority_state(candidate)
            except BaseException:
                self._state = before_state
                raise

    def _restore_pre_material_encoded(
        self,
        encoded: bytes,
        *,
        envelope_schema: str,
        state_schema: str,
        observation_schema: str,
        state_domain: bytes,
        observation_domain: bytes,
        version_name: str,
    ) -> None:
        decoded, _payload = self._decode_authenticated_envelope(
            encoded,
            envelope_schema=envelope_schema,
            domain=state_domain,
            limit=self._max_encoded_state_bytes,
        )
        expected_state = {
            "actor_ports",
            "limits",
            "migration_receipt",
            "recent_applied_receipts",
            "schema",
            "world",
        }
        if (
            set(decoded) != expected_state
            or decoded.get("schema") != state_schema
        ):
            raise ValueError(
                f"{version_name} embodiment state fields changed"
            )
        limits = decoded.get("limits")
        expected_limit_fields = {
            "max_regions",
            "max_portals",
            "max_bodies",
            "max_command_bytes",
            "max_encoded_state_bytes",
            "max_objects",
            "receipt_capacity",
        }
        if (
            not isinstance(limits, Mapping)
            or set(limits) != expected_limit_fields
            or limits.get("max_regions") != self._max_regions
            or limits.get("max_portals") != self._max_portals
            or limits.get("max_bodies") != self._max_bodies
            or limits.get("max_command_bytes") != self._max_command_bytes
            or limits.get("max_encoded_state_bytes")
            != self._max_encoded_state_bytes
            or limits.get("receipt_capacity") != self._receipt_capacity
        ):
            raise ValueError(
                f"{version_name} embodiment limits changed"
            )
        prior_object_capacity = _bounded_integer(
            limits.get("max_objects"),
            f"{version_name} object capacity",
            minimum=1,
            maximum=self._max_objects,
        )
        if decoded.get("actor_ports") != [
            item.as_record() for item in self._actor_ports
        ]:
            raise ValueError(
                f"{version_name} actor port topology changed"
            )
        raw_receipts = decoded.get("recent_applied_receipts")
        if (
            not isinstance(raw_receipts, list)
            or len(raw_receipts) > self._receipt_capacity
            or any(not isinstance(item, Mapping) for item in raw_receipts)
        ):
            raise ValueError(
                f"{version_name} execution custody changed"
            )
        world_value = decoded.get("world")
        world_expected = {
            "bodies",
            "objects",
            "portals",
            "regions",
            "revision",
            "room_bounds",
            "room_id",
            "self_body_id",
        }
        if (
            not isinstance(world_value, Mapping)
            or set(world_value) != world_expected
        ):
            raise ValueError(
                f"{version_name} world state fields changed"
            )
        raw_bodies = world_value.get("bodies")
        raw_objects = world_value.get("objects")
        raw_regions = world_value.get("regions")
        raw_portals = world_value.get("portals")
        if (
            not isinstance(raw_bodies, list)
            or not 2 <= len(raw_bodies) <= self._max_bodies
            or not isinstance(raw_objects, list)
            or not 1 <= len(raw_objects) <= prior_object_capacity
            or not isinstance(raw_regions, list)
            or not isinstance(raw_portals, list)
        ):
            raise ValueError(
                f"{version_name} physical inventory changed"
            )
        prior_revision = _bounded_integer(
            world_value.get("revision"),
            f"{version_name} world revision",
            minimum=0,
            maximum=MAX_REVISION - 1,
        )
        room_id = _identifier(
            world_value.get("room_id"),
            f"{version_name} room id",
        )
        room_bounds = _room_from(world_value.get("room_bounds"))
        self_body_id = _identifier(
            world_value.get("self_body_id"),
            f"{version_name} self body id",
        )
        bodies = tuple(_v3_body_from(item) for item in raw_bodies)
        objects = tuple(_v3_object_from(item) for item in raw_objects)
        regions = tuple(_v3_region_from(item) for item in raw_regions)
        portals = tuple(_v3_portal_from(item) for item in raw_portals)
        if (
            self_body_id != self._state.world.self_body_id
            or {item.body_id for item in bodies}
            != {item.actor_body_id for item in self._actor_ports}
        ):
            raise ValueError(
                f"{version_name} body identity changed"
            )
        prior_world_record = dict(world_value)
        prior_observation_unsigned = {
            **prior_world_record,
            "schema": observation_schema,
            "state_sha256": _digest(prior_world_record),
        }
        prior_hmac = _sign(
            self._key,
            observation_domain,
            prior_observation_unsigned,
        )
        prior_observation_receipt = _digest({
            "authority_hmac_sha256": prior_hmac,
            "payload": prior_observation_unsigned,
        })
        self_body = next(
            item for item in bodies
            if item.body_id == self_body_id
        )
        current_region = self._region_containing(
            regions,
            self_body.pose.position,
            self_body.radius_mm,
        )
        if (
            current_region is None
            or current_region.region_id != room_id
            or current_region.bounds != room_bounds
        ):
            raise ValueError(
                f"{version_name} self-region projection changed"
            )
        migrated_world = _WorldState(
            revision=prior_revision + 1,
            room_id=room_id,
            room_bounds=room_bounds,
            regions=regions,
            portals=portals,
            self_body_id=self_body_id,
            bodies=bodies,
            objects=self._migrated_objects(objects),
        )
        self._validate_world(migrated_world)
        resulting_observation = self._observation_for(
            migrated_world
        )
        parent_receipt = decoded.get("migration_receipt")
        parent_identity = None
        if parent_receipt is not None:
            if not isinstance(parent_receipt, Mapping):
                raise ValueError(
                    f"{version_name} migration custody changed"
                )
            parent_identity = _sha256_identity(
                parent_receipt.get("authority_receipt_sha256"),
                f"{version_name} migration receipt",
            )
        migration = self._migration_receipt_for(
            prior_envelope_sha256=hashlib.sha256(encoded).hexdigest(),
            prior_observation_receipt_sha256=(
                prior_observation_receipt
            ),
            resulting_observation_receipt_sha256=(
                resulting_observation.authority_receipt_sha256
            ),
            prior_revision=prior_revision,
            resulting_revision=migrated_world.revision,
            parent_migration_receipt_sha256=parent_identity,
            manifest_sha256=self._physical_manifest_sha256(),
            prior_topology_sha256=_digest({
                "portals": list(raw_portals),
                "regions": list(raw_regions),
            }),
            resulting_topology_sha256=self._topology_sha256(
                regions,
                portals,
            ),
        )
        candidate = _AuthorityState(
            world=migrated_world,
            observation=resulting_observation,
            recent_applied_receipts=(),
            migration_receipt=migration,
        )
        self._encoded_state_for(candidate)
        with self._lock:
            before_state = self._state
            try:
                self._commit_authority_state(candidate)
            except BaseException:
                self._state = before_state
                raise

    def _restore_legacy_encoded(self, encoded: bytes) -> None:
        decoded, _payload = self._decode_authenticated_envelope(
            encoded,
            envelope_schema=LEGACY_ENVELOPE_SCHEMA,
            domain=LEGACY_STATE_DOMAIN,
            limit=LEGACY_MAX_ENCODED_STATE_BYTES,
        )
        expected_state = {
            "limits", "port_id", "recent_applied_receipts", "schema", "world"
        }
        if set(decoded) != expected_state or decoded.get("schema") != LEGACY_STATE_SCHEMA:
            raise ValueError("legacy embodiment state fields changed")
        limits = decoded.get("limits")
        expected_limit_fields = {
            "max_command_bytes",
            "max_encoded_state_bytes",
            "max_objects",
            "receipt_capacity",
        }
        if not isinstance(limits, Mapping) or set(limits) != expected_limit_fields:
            raise ValueError("legacy embodiment authority limits changed")
        _bounded_integer(
            limits.get("max_command_bytes"),
            "legacy command capacity",
            minimum=64,
            maximum=self._max_command_bytes,
        )
        prior_state_capacity = _bounded_integer(
            limits.get("max_encoded_state_bytes"),
            "legacy encoded state capacity",
            minimum=4096,
            maximum=LEGACY_MAX_ENCODED_STATE_BYTES,
        )
        prior_object_capacity = _bounded_integer(
            limits.get("max_objects"),
            "legacy object capacity",
            minimum=1,
            maximum=self._max_objects,
        )
        prior_receipt_capacity = _bounded_integer(
            limits.get("receipt_capacity"),
            "legacy receipt capacity",
            minimum=1,
            maximum=4096,
        )
        if decoded.get("port_id") != PORT_ID or len(encoded) > prior_state_capacity:
            raise ValueError("legacy embodiment authority port or capacity changed")
        raw_receipts = decoded.get("recent_applied_receipts")
        if (
            not isinstance(raw_receipts, list)
            or len(raw_receipts) > prior_receipt_capacity
            or any(not isinstance(item, Mapping) for item in raw_receipts)
        ):
            raise ValueError("legacy retained execution receipts changed")
        world_value = decoded.get("world")
        expected_world = {"body", "objects", "revision", "room_bounds", "room_id"}
        if not isinstance(world_value, Mapping) or set(world_value) != expected_world:
            raise ValueError("legacy world state fields changed")
        raw_objects = world_value.get("objects")
        if (
            not isinstance(raw_objects, list)
            or not 1 <= len(raw_objects) <= prior_object_capacity
        ):
            raise ValueError("legacy world object inventory changed")
        prior_revision = _bounded_integer(
            world_value.get("revision"),
            "legacy world revision",
            minimum=0,
            maximum=MAX_REVISION - 1,
        )
        room_id = _identifier(world_value.get("room_id"), "legacy room id")
        room_bounds = _room_from(world_value.get("room_bounds"))
        legacy_body = _v3_body_from(world_value.get("body"))
        legacy_objects = tuple(_legacy_object_from(item) for item in raw_objects)
        legacy_world_record = {
            "body": {
                key: value
                for key, value in legacy_body.as_record().items()
                if key not in {"active_contact", "receptor_geometry"}
            },
            "objects": [],
            "revision": prior_revision,
            "room_bounds": room_bounds.as_record(),
            "room_id": room_id,
        }
        for item in legacy_objects:
            record = item.as_record()
            del record["reflectance_ppm"]
            del record["material"]
            del record["optical_surface"]
            legacy_world_record["objects"].append(record)
        if legacy_world_record != dict(world_value):
            raise ValueError("legacy world state is not canonical")
        other_bodies = tuple(
            item
            for item in self._state.world.bodies
            if item.body_id != legacy_body.body_id
        )
        if len(other_bodies) != 1:
            raise ValueError("legacy migration requires one added physical body")
        bodies = tuple(
            sorted((legacy_body, other_bodies[0]), key=lambda item: item.body_id)
        )
        prior_observation_unsigned = {
            **legacy_world_record,
            "schema": LEGACY_OBSERVATION_SCHEMA,
            "state_sha256": _digest(legacy_world_record),
        }
        self._commit_migrated_world(
            encoded=encoded,
            prior_revision=prior_revision,
            prior_room_id=room_id,
            prior_room_bounds=room_bounds,
            prior_bodies=bodies,
            prior_objects=legacy_objects,
            prior_observation_unsigned=prior_observation_unsigned,
            prior_observation_domain=LEGACY_OBSERVATION_DOMAIN,
            parent_migration_receipt_sha256=None,
        )

    def _restore_v2_encoded(self, encoded: bytes) -> None:
        decoded, _payload = self._decode_authenticated_envelope(
            encoded,
            envelope_schema=V2_ENVELOPE_SCHEMA,
            domain=V2_STATE_DOMAIN,
            limit=self._max_encoded_state_bytes,
        )
        expected_state = {
            "actor_ports", "limits", "migration_receipt",
            "recent_applied_receipts", "schema", "world"
        }
        if set(decoded) != expected_state or decoded.get("schema") != V2_STATE_SCHEMA:
            raise ValueError("v2 embodiment state fields changed")
        limits = decoded.get("limits")
        expected_limit_fields = {
            "max_bodies",
            "max_command_bytes",
            "max_encoded_state_bytes",
            "max_objects",
            "receipt_capacity",
        }
        if not isinstance(limits, Mapping) or set(limits) != expected_limit_fields:
            raise ValueError("v2 embodiment authority limits changed")
        _bounded_integer(
            limits.get("max_bodies"),
            "v2 body capacity",
            minimum=2,
            maximum=self._max_bodies,
        )
        _bounded_integer(
            limits.get("max_command_bytes"),
            "v2 command capacity",
            minimum=64,
            maximum=self._max_command_bytes,
        )
        prior_state_capacity = _bounded_integer(
            limits.get("max_encoded_state_bytes"),
            "v2 encoded state capacity",
            minimum=4096,
            maximum=self._max_encoded_state_bytes,
        )
        prior_object_capacity = _bounded_integer(
            limits.get("max_objects"),
            "v2 object capacity",
            minimum=1,
            maximum=self._max_objects,
        )
        prior_receipt_capacity = _bounded_integer(
            limits.get("receipt_capacity"),
            "v2 receipt capacity",
            minimum=1,
            maximum=4096,
        )
        if len(encoded) > prior_state_capacity:
            raise ValueError("v2 embodiment state exceeded its own byte capacity")
        if decoded.get("actor_ports") != [
            item.as_record() for item in self._actor_ports
        ]:
            raise ValueError("v2 actor port topology changed")
        raw_receipts = decoded.get("recent_applied_receipts")
        if (
            not isinstance(raw_receipts, list)
            or len(raw_receipts) > prior_receipt_capacity
            or any(not isinstance(item, Mapping) for item in raw_receipts)
        ):
            raise ValueError("v2 retained execution receipts changed")
        world_value = decoded.get("world")
        expected_world = {
            "bodies", "objects", "revision", "room_bounds", "room_id",
            "self_body_id"
        }
        if not isinstance(world_value, Mapping) or set(world_value) != expected_world:
            raise ValueError("v2 world state fields changed")
        raw_bodies = world_value.get("bodies")
        raw_objects = world_value.get("objects")
        if (
            not isinstance(raw_bodies, list)
            or not 2 <= len(raw_bodies) <= limits["max_bodies"]
            or not isinstance(raw_objects, list)
            or not 1 <= len(raw_objects) <= prior_object_capacity
        ):
            raise ValueError("v2 physical inventory changed")
        prior_revision = _bounded_integer(
            world_value.get("revision"),
            "v2 world revision",
            minimum=0,
            maximum=MAX_REVISION - 1,
        )
        room_id = _identifier(world_value.get("room_id"), "v2 room id")
        room_bounds = _room_from(world_value.get("room_bounds"))
        self_body_id = _identifier(
            world_value.get("self_body_id"), "v2 self body id"
        )
        if self_body_id != self._state.world.self_body_id:
            raise ValueError("v2 self body identity changed")
        bodies = tuple(_v3_body_from(item) for item in raw_bodies)
        objects = tuple(_legacy_object_from(item) for item in raw_objects)
        v2_world_record = {
            "bodies": [
                {
                    key: value
                    for key, value in item.as_record().items()
                    if key
                    not in {"active_contact", "receptor_geometry"}
                }
                for item in bodies
            ],
            "objects": [],
            "revision": prior_revision,
            "room_bounds": room_bounds.as_record(),
            "room_id": room_id,
            "self_body_id": self_body_id,
        }
        for item in objects:
            record = item.as_record()
            del record["reflectance_ppm"]
            del record["material"]
            del record["optical_surface"]
            v2_world_record["objects"].append(record)
        if v2_world_record != dict(world_value):
            raise ValueError("v2 world state is not canonical")
        parent_migration_receipt_sha256 = None
        parent = decoded.get("migration_receipt")
        if parent is not None:
            if (
                not isinstance(parent, Mapping)
                or parent.get("schema") != V2_MIGRATION_SCHEMA
            ):
                raise ValueError("v2 migration receipt changed")
            parent_migration_receipt_sha256 = _sha256_identity(
                parent.get("authority_receipt_sha256"),
                "v2 migration receipt",
            )
        prior_observation_unsigned = {
            **v2_world_record,
            "schema": V2_OBSERVATION_SCHEMA,
            "state_sha256": _digest(v2_world_record),
        }
        self._commit_migrated_world(
            encoded=encoded,
            prior_revision=prior_revision,
            prior_room_id=room_id,
            prior_room_bounds=room_bounds,
            prior_bodies=bodies,
            prior_objects=objects,
            prior_observation_unsigned=prior_observation_unsigned,
            prior_observation_domain=V2_OBSERVATION_DOMAIN,
            parent_migration_receipt_sha256=parent_migration_receipt_sha256,
        )

    def _restore_v5_encoded(self, encoded: bytes) -> None:
        decoded, _payload = self._decode_authenticated_envelope(
            encoded,
            envelope_schema=V5_ENVELOPE_SCHEMA,
            domain=V5_STATE_DOMAIN,
            limit=self._max_encoded_state_bytes,
        )
        expected_state = {
            "actor_ports",
            "limits",
            "migration_receipt",
            "recent_applied_receipts",
            "schema",
            "world",
        }
        if (
            not isinstance(decoded, Mapping)
            or set(decoded) != expected_state
            or decoded.get("schema") != V5_STATE_SCHEMA
        ):
            raise ValueError("v5 embodiment state fields changed")
        limits = decoded.get("limits")
        expected_limit_fields = {
            "max_regions",
            "max_portals",
            "max_bodies",
            "max_command_bytes",
            "max_encoded_state_bytes",
            "max_objects",
            "receipt_capacity",
        }
        if (
            not isinstance(limits, Mapping)
            or set(limits) != expected_limit_fields
            or limits.get("max_regions") != self._max_regions
            or limits.get("max_portals") != self._max_portals
            or limits.get("max_bodies") != self._max_bodies
            or limits.get("max_command_bytes") != self._max_command_bytes
            or limits.get("max_encoded_state_bytes")
            != self._max_encoded_state_bytes
            or limits.get("receipt_capacity") != self._receipt_capacity
        ):
            raise ValueError("v5 embodiment authority limits changed")
        prior_object_capacity = _bounded_integer(
            limits.get("max_objects"),
            "v5 object capacity",
            minimum=1,
            maximum=self._max_objects,
        )
        if decoded.get("actor_ports") != [
            item.as_record() for item in self._actor_ports
        ]:
            raise ValueError("v5 actor port topology changed")
        raw_receipts = decoded.get("recent_applied_receipts")
        if (
            not isinstance(raw_receipts, list)
            or len(raw_receipts) > self._receipt_capacity
            or any(not isinstance(item, Mapping) for item in raw_receipts)
        ):
            raise ValueError("v5 execution custody changed")
        world_value = decoded.get("world")
        world_expected = {
            "bodies",
            "objects",
            "portals",
            "regions",
            "revision",
            "room_bounds",
            "room_id",
            "self_body_id",
        }
        if (
            not isinstance(world_value, Mapping)
            or set(world_value) != world_expected
        ):
            raise ValueError("v5 world state fields changed")
        raw_bodies = world_value.get("bodies")
        raw_objects = world_value.get("objects")
        raw_regions = world_value.get("regions")
        raw_portals = world_value.get("portals")
        if (
            not isinstance(raw_bodies, list)
            or not 2 <= len(raw_bodies) <= self._max_bodies
            or not isinstance(raw_objects, list)
            or not 1 <= len(raw_objects) <= prior_object_capacity
            or not isinstance(raw_regions, list)
            or not isinstance(raw_portals, list)
        ):
            raise ValueError("v5 physical inventory changed")
        bodies = tuple(_body_from(item) for item in raw_bodies)
        objects = tuple(_v5_object_from(item) for item in raw_objects)
        regions = tuple(_region_from(item) for item in raw_regions)
        portals = tuple(_portal_from(item) for item in raw_portals)
        prior_revision = _bounded_integer(
            world_value.get("revision"),
            "v5 world revision",
            minimum=0,
            maximum=MAX_REVISION - 1,
        )
        prior_room_id = _identifier(
            world_value.get("room_id"),
            "v5 room id",
        )
        prior_room_bounds = _room_from(world_value.get("room_bounds"))
        prior_self_body_id = _identifier(
            world_value.get("self_body_id"),
            "v5 self body id",
        )
        if (
            tuple(sorted(bodies, key=lambda item: item.body_id)) != bodies
            or tuple(sorted(objects, key=lambda item: item.object_id))
            != objects
            or prior_self_body_id
            != self._state.world.self_body_id
        ):
            raise ValueError("v5 physical identity order changed")
        migration_value = decoded.get("migration_receipt")
        parent_migration_receipt_sha256 = None
        if migration_value is not None:
            if (
                not isinstance(migration_value, Mapping)
                or migration_value.get("schema") != V5_MIGRATION_SCHEMA
            ):
                raise ValueError("v5 migration receipt changed")
            parent_migration_receipt_sha256 = _sha256_identity(
                migration_value.get("authority_receipt_sha256"),
                "v5 migration receipt identity",
            )
        prior_world_record = dict(world_value)
        prior_observation_unsigned = {
            **prior_world_record,
            "schema": V5_OBSERVATION_SCHEMA,
            "state_sha256": _digest(prior_world_record),
        }
        self._commit_migrated_world(
            encoded=encoded,
            prior_revision=prior_revision,
            prior_room_id=prior_room_id,
            prior_room_bounds=prior_room_bounds,
            prior_bodies=bodies,
            prior_objects=objects,
            prior_observation_unsigned=prior_observation_unsigned,
            prior_observation_domain=V5_OBSERVATION_DOMAIN,
            parent_migration_receipt_sha256=(
                parent_migration_receipt_sha256
            ),
            preserve_material=True,
        )

    def _restore_v6_encoded(self, encoded: bytes) -> None:
        decoded, payload = self._decode_authenticated_envelope(
            encoded,
            envelope_schema=V6_ENVELOPE_SCHEMA,
            domain=V6_STATE_DOMAIN,
            limit=self._max_encoded_state_bytes,
        )
        expected_state = {
            "actor_ports", "limits", "migration_receipt",
            "recent_applied_receipts", "schema", "world"
        }
        if (
            not isinstance(decoded, Mapping)
            or set(decoded) != expected_state
            or decoded.get("schema") != V6_STATE_SCHEMA
        ):
            raise ValueError("v6 embodiment state fields changed")
        expected_limits = {
            "max_regions": self._max_regions,
            "max_portals": self._max_portals,
            "max_bodies": self._max_bodies,
            "max_command_bytes": self._max_command_bytes,
            "max_encoded_state_bytes": self._max_encoded_state_bytes,
            "max_objects": self._max_objects,
            "receipt_capacity": self._receipt_capacity,
        }
        if decoded.get("limits") != expected_limits:
            raise ValueError("v6 embodiment state limits changed")
        if decoded.get("actor_ports") != [item.as_record() for item in self._actor_ports]:
            raise ValueError("v6 embodiment actor port topology changed")
        world = self._world_from_record(decoded.get("world"))
        raw_receipts = decoded.get("recent_applied_receipts")
        if not isinstance(raw_receipts, list) or len(raw_receipts) > self._receipt_capacity:
            raise ValueError("v6 retained execution receipts exceed capacity")
        receipts = tuple(self._execution_from_record(item) for item in raw_receipts)
        for left, right in zip(receipts, receipts[1:]):
            if left.after != right.before:
                raise ValueError("v6 retained execution chain changed")
        current_observation = self._observation_for(world)
        if receipts and receipts[-1].after != current_observation:
            raise ValueError("v6 execution chain does not end at current world")
        migration_value = decoded.get("migration_receipt")
        prior_migration = (
            self._migration_from_record(
                migration_value,
                world,
                require_current_manifest=False,
            )
            if migration_value is not None
            else None
        )
        prior_candidate = _AuthorityState(
            world=world,
            observation=current_observation,
            recent_applied_receipts=receipts,
            migration_receipt=prior_migration,
        )
        if _canonical(self._v6_state_payload_for(prior_candidate)) != payload:
            raise ValueError("v6 embodiment state is not canonical")
        self._commit_migrated_world(
            encoded=encoded,
            prior_revision=world.revision,
            prior_room_id=world.room_id,
            prior_room_bounds=world.room_bounds,
            prior_bodies=world.bodies,
            prior_objects=world.objects,
            prior_observation_unsigned=current_observation.unsigned_record(),
            prior_observation_domain=OBSERVATION_DOMAIN,
            parent_migration_receipt_sha256=(
                None
                if prior_migration is None
                else prior_migration.authority_receipt_sha256
            ),
            preserve_material=True,
        )

    def restore_encoded(
        self,
        encoded: bytes,
        *,
        allow_authenticated_physical_manifest_migration: bool = False,
    ) -> None:
        """Atomically restore one exact authenticated authority snapshot."""
        if not isinstance(encoded, bytes) or not encoded or len(encoded) > LEGACY_MAX_ENCODED_STATE_BYTES:
            raise ValueError("encoded embodiment state exceeds its exact byte capacity")
        try:
            envelope_probe = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("embodiment state envelope is not canonical JSON") from error
        if isinstance(envelope_probe, Mapping) and envelope_probe.get("schema") == LEGACY_ENVELOPE_SCHEMA:
            self._restore_legacy_encoded(encoded)
            return
        if isinstance(envelope_probe, Mapping) and envelope_probe.get("schema") == V2_ENVELOPE_SCHEMA:
            self._restore_v2_encoded(encoded)
            return
        if (
            isinstance(envelope_probe, Mapping)
            and envelope_probe.get("schema") == V3_ENVELOPE_SCHEMA
        ):
            self._restore_pre_material_encoded(
                encoded,
                envelope_schema=V3_ENVELOPE_SCHEMA,
                state_schema=V3_STATE_SCHEMA,
                observation_schema=V3_OBSERVATION_SCHEMA,
                state_domain=V3_STATE_DOMAIN,
                observation_domain=V3_OBSERVATION_DOMAIN,
                version_name="v3",
            )
            return
        if (
            isinstance(envelope_probe, Mapping)
            and envelope_probe.get("schema") == V4_ENVELOPE_SCHEMA
        ):
            self._restore_pre_material_encoded(
                encoded,
                envelope_schema=V4_ENVELOPE_SCHEMA,
                state_schema=V4_STATE_SCHEMA,
                observation_schema=V4_OBSERVATION_SCHEMA,
                state_domain=V4_STATE_DOMAIN,
                observation_domain=V4_OBSERVATION_DOMAIN,
                version_name="v4",
            )
            return
        if (
            isinstance(envelope_probe, Mapping)
            and envelope_probe.get("schema") == V5_ENVELOPE_SCHEMA
        ):
            self._restore_v5_encoded(encoded)
            return
        if (
            isinstance(envelope_probe, Mapping)
            and envelope_probe.get("schema") == V6_ENVELOPE_SCHEMA
        ):
            self._restore_v6_encoded(encoded)
            return
        decoded, _payload = self._decode_authenticated_envelope(
            encoded,
            envelope_schema=ENVELOPE_SCHEMA,
            domain=STATE_DOMAIN,
            limit=self._max_encoded_state_bytes,
        )
        expected_state = {
            "actor_ports", "limits", "migration_receipt", "optical_surface_catalog",
            "recent_applied_receipts", "schema", "world"
        }
        if not isinstance(decoded, Mapping) or set(decoded) != expected_state or decoded.get("schema") != STATE_SCHEMA:
            raise ValueError("embodiment state fields changed")
        expected_limits = {
            "max_regions": self._max_regions,
            "max_portals": self._max_portals,
            "max_bodies": self._max_bodies,
            "max_command_bytes": self._max_command_bytes,
            "max_encoded_state_bytes": self._max_encoded_state_bytes,
            "max_objects": self._max_objects,
            "receipt_capacity": self._receipt_capacity,
        }
        if decoded.get("limits") != expected_limits:
            raise ValueError("embodiment state limits changed")
        if decoded.get("actor_ports") != [item.as_record() for item in self._actor_ports]:
            raise ValueError("embodiment actor port topology changed")
        catalog = self._optical_surface_catalog_from_record(decoded.get("optical_surface_catalog"))
        world = self._world_from_compact_record(decoded.get("world"), catalog)
        raw_receipts = decoded.get("recent_applied_receipts")
        if not isinstance(raw_receipts, list) or len(raw_receipts) > self._receipt_capacity:
            raise ValueError("retained execution receipts exceed capacity")
        receipts = tuple(self._execution_from_compact_record(item, catalog) for item in raw_receipts)
        for left, right in zip(receipts, receipts[1:]):
            if left.after != right.before:
                raise ValueError("retained execution chain changed")
        current_observation = self._observation_for(world)
        if receipts and receipts[-1].after != current_observation:
            raise ValueError("retained execution chain does not end at current world")
        migration_value = decoded.get("migration_receipt")
        migration = (
            self._migration_from_record(
                migration_value,
                world,
                require_current_manifest=(
                    not allow_authenticated_physical_manifest_migration
                ),
            )
            if migration_value is not None
            else None
        )
        candidate = _AuthorityState(
            world=world,
            observation=current_observation,
            recent_applied_receipts=receipts,
            migration_receipt=migration,
        )
        if self._encoded_state_for(candidate) != encoded:
            raise ValueError("embodiment state is not canonical")
        if (
            allow_authenticated_physical_manifest_migration
            and migration is not None
            and migration.manifest_sha256
            != self._physical_manifest_sha256()
        ):
            self._commit_migrated_world(
                encoded=encoded,
                prior_revision=world.revision,
                prior_room_id=world.room_id,
                prior_room_bounds=world.room_bounds,
                prior_bodies=world.bodies,
                prior_objects=world.objects,
                prior_observation_unsigned=(
                    current_observation.unsigned_record()
                ),
                prior_observation_domain=OBSERVATION_DOMAIN,
                parent_migration_receipt_sha256=(
                    migration.authority_receipt_sha256
                ),
                preserve_material=True,
            )
            return
        with self._lock:
            before_state = self._state
            try:
                self._commit_authority_state(candidate)
            except BaseException:
                self._state = before_state
                raise

    def status(self) -> dict[str, object]:
        with self._lock:
            self._require_public_visibility_locked()
            world = self._state.world
            self_body = next(
                item for item in world.bodies
                if item.body_id == world.self_body_id
            )
            return {
                "body_capacity": self._max_bodies,
                "body_count": len(world.bodies),
                "body_ids": [item.body_id for item in world.bodies],
                "self_body_id": world.self_body_id,
                "held_object_id": self_body.held_object_id,
                "object_capacity": self._max_objects,
                "object_count": len(world.objects),
                "portal_capacity": self._max_portals,
                "portal_count": len(world.portals),
                "portal_ids": [item.portal_id for item in world.portals],
                "port_id": self.port_id,
                "region_capacity": self._max_regions,
                "region_count": len(world.regions),
                "region_ids": [item.region_id for item in world.regions],
                "actor_ports": [item.as_record() for item in self._actor_ports],
                "migration_receipt_sha256": (
                    self._state.migration_receipt.authority_receipt_sha256
                    if self._state.migration_receipt is not None
                    else None
                ),
                "prepared_action_execution": int(
                    self._prepared_action_execution is not None
                ),
                "receipt_capacity": self._receipt_capacity,
                "retained_applied_receipts": len(self._state.recent_applied_receipts),
                "revision": world.revision,
                "room_id": world.room_id,
            }


__all__ = [
    "ActionExecutionReceipt",
    "AdvancePhysicalTimeCommand",
    "AirVolumeState",
    "BodyContactState",
    "BodyReceptorGeometry",
    "EmbodiedBody",
    "EmbodiedObject",
    "EmbodimentPort",
    "EmbodimentWorldAuthority",
    "MoveCommand",
    "ObjectMaterialState",
    "ObjectOpticalSurface",
    "MAX_OPTICAL_SURFACE_COLUMNS",
    "MAX_OPTICAL_SURFACE_PALETTE_ENTRIES",
    "MAX_OPTICAL_SURFACE_ROWS",
    "MAX_VOCAL_SAMPLE_COUNT",
    "MIN_VOCAL_SAMPLE_COUNT",
    "ObservationSnapshot",
    "OralContactCommand",
    "PORT_ID",
    "PreparedActionExecution",
    "SECOND_BODY_PORT_ID",
    "PickCommand",
    "PlaceCommand",
    "VocalizeCommand",
    "VOCAL_SAMPLE_RATE_HZ",
    "PoseMM",
    "PositionMM",
    "PhysicalPortal",
    "PhysicalRegion",
    "RoomBoundsMM",
    "TouchContactCommand",
    "V5_ENVELOPE_SCHEMA",
    "V5_STATE_SCHEMA",
    "WorldMigrationReceipt",
    "decode_command",
    "encode_command",
]
