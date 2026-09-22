"""Deterministic physical raster import for embodied optical surfaces.

This boundary turns a bounded RGB PNG into the virtual room's explicit
six-band material reflectance field.  It carries no text, object identity,
card identity, OCR, pronunciation, or meaning.  Spatial reduction is an
exact sensor-aperture box integration; color reduction is a fixed uniform
physical quantization, not a learned or content-dependent palette.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass

from PIL import Image

from dsf_ai_service.substrate.embodiment_world import (
    MAX_OPTICAL_SURFACE_COLUMNS,
    MAX_OPTICAL_SURFACE_PALETTE_ENTRIES,
    MAX_OPTICAL_SURFACE_ROWS,
    ObjectOpticalSurface,
)


ASSET_SCHEMA = "guala.physical_optical_surface_asset.v1"
DEFAULT_SURFACE_COLUMNS = MAX_OPTICAL_SURFACE_COLUMNS
DEFAULT_SURFACE_ROWS = MAX_OPTICAL_SURFACE_ROWS
MAX_SOURCE_PNG_BYTES = 16 * 1024 * 1024
MAX_SOURCE_PIXELS = 16_000_000
RGB_QUANTIZATION_LEVELS = 6


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _bounded_dimension(value: object, name: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise ValueError(f"{name} is outside the physical surface boundary")
    return value


def _uniform_channel_level(value: int) -> int:
    """Return the center of one of six exact uniform 8-bit intervals."""

    interval = value * RGB_QUANTIZATION_LEVELS // 256
    return (
        (2 * interval + 1) * 256
        // (2 * RGB_QUANTIZATION_LEVELS)
    )


def _ppm(value: int) -> int:
    return value * 1_000_000 // 255


def rgb8_to_six_band_reflectance_ppm(
    red: int,
    green: int,
    blue: int,
) -> tuple[int, ...]:
    """Define one exact virtual-material spectrum from bounded RGB energy.

    The six bands run from the blue end toward the red end.  Intermediate
    bands are fixed integer linear mixtures of neighboring RGB primaries.
    This defines the virtual material; it does not claim to reconstruct an
    unknown real-world spectrum from RGB.
    """

    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= 255
        for value in (red, green, blue)
    ):
        raise ValueError("optical source channel is outside eight-bit energy")
    values = (
        blue,
        (2 * blue + green) // 3,
        (blue + 2 * green) // 3,
        (2 * green + red) // 3,
        (green + 2 * red) // 3,
        red,
    )
    return tuple(_ppm(value) for value in values)


@dataclass(frozen=True, slots=True)
class PhysicalOpticalSurfaceAsset:
    """Authenticated import result; only ``surface`` enters the room."""

    source_png_sha256: str
    source_width: int
    source_height: int
    surface: ObjectOpticalSurface
    surface_sha256: str
    schema: str = ASSET_SCHEMA

    def verify(self) -> None:
        self.surface.verify()
        if (
            self.schema != ASSET_SCHEMA
            or len(self.source_png_sha256) != 64
            or len(self.surface_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in (
                    self.source_png_sha256 + self.surface_sha256
                )
            )
            or self.source_width <= 0
            or self.source_height <= 0
            or self.source_width * self.source_height > MAX_SOURCE_PIXELS
            or self.surface_sha256
            != hashlib.sha256(
                _canonical(self.surface.as_record())
            ).hexdigest()
        ):
            raise ValueError("physical optical surface asset changed")


def physical_optical_surface_from_png(
    png_bytes: bytes,
    *,
    columns: int = DEFAULT_SURFACE_COLUMNS,
    rows: int = DEFAULT_SURFACE_ROWS,
) -> PhysicalOpticalSurfaceAsset:
    """Import one bounded RGB PNG as an exact palette-indexed surface."""

    columns = _bounded_dimension(
        columns,
        "optical surface columns",
        MAX_OPTICAL_SURFACE_COLUMNS,
    )
    rows = _bounded_dimension(
        rows,
        "optical surface rows",
        MAX_OPTICAL_SURFACE_ROWS,
    )
    if (
        not isinstance(png_bytes, bytes)
        or not png_bytes
        or len(png_bytes) > MAX_SOURCE_PNG_BYTES
    ):
        raise ValueError("physical optical source exceeds its PNG boundary")
    try:
        with Image.open(io.BytesIO(png_bytes)) as source:
            if (
                source.format != "PNG"
                or getattr(source, "n_frames", 1) != 1
                or source.width <= 0
                or source.height <= 0
                or source.width * source.height > MAX_SOURCE_PIXELS
            ):
                raise ValueError(
                    "physical optical source is not one bounded PNG frame"
                )
            source_width = source.width
            source_height = source.height
            rgb = source.convert("RGB")
            sampled = rgb.resize(
                (columns, rows),
                resample=Image.Resampling.BOX,
                reducing_gap=None,
            )
            pixels = tuple(sampled.get_flattened_data())
    except (OSError, SyntaxError) as error:
        raise ValueError("physical optical source PNG is unreadable") from error

    palette: list[tuple[int, ...]] = []
    palette_index: dict[tuple[int, ...], int] = {}
    cells: list[int] = []
    for red, green, blue in pixels:
        reflectance = rgb8_to_six_band_reflectance_ppm(
            _uniform_channel_level(red),
            _uniform_channel_level(green),
            _uniform_channel_level(blue),
        )
        index = palette_index.get(reflectance)
        if index is None:
            index = len(palette)
            if index >= MAX_OPTICAL_SURFACE_PALETTE_ENTRIES:
                raise RuntimeError(
                    "physical optical palette exceeded its exact boundary"
                )
            palette_index[reflectance] = index
            palette.append(reflectance)
        cells.append(index)
    surface = ObjectOpticalSurface(
        columns=columns,
        rows=rows,
        palette_reflectance_ppm=tuple(palette),
        cell_palette_indices=tuple(cells),
    )
    surface.verify()
    result = PhysicalOpticalSurfaceAsset(
        source_png_sha256=hashlib.sha256(png_bytes).hexdigest(),
        source_width=source_width,
        source_height=source_height,
        surface=surface,
        surface_sha256=hashlib.sha256(
            _canonical(surface.as_record())
        ).hexdigest(),
    )
    result.verify()
    return result


__all__ = (
    "ASSET_SCHEMA",
    "DEFAULT_SURFACE_COLUMNS",
    "DEFAULT_SURFACE_ROWS",
    "MAX_SOURCE_PIXELS",
    "MAX_SOURCE_PNG_BYTES",
    "PhysicalOpticalSurfaceAsset",
    "RGB_QUANTIZATION_LEVELS",
    "physical_optical_surface_from_png",
    "rgb8_to_six_band_reflectance_ppm",
)
