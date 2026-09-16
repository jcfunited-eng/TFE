"""Canonical physical home authority for the lean Guala runtime.

This module is environment anatomy only. It owns no organism, scheduler,
observer, persistence, lesson, action choice, or cognition.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
from typing import Any, Iterable
import uuid

TOUCH_RECEPTORS_AUTHORIZED = True
HOME_BOOK_OBJECT_ID = "book"

# Windows, declared content like a thing's material: which wall of the room, from
# where to where along it, sill and top. The sun's direct light enters through them;
# the sky's share (the solar coupling) is the room's ambient.
from dsf_ai_service.substrate.embodiment_world import (  # noqa: E402
    ObjectOpticalSurface,
    SurfaceLookMM,
    WindowMM,
)

HOME_WINDOWS = {
    "her-room":    (WindowMM("y-max", 1_800, 3_800, 900, 2_100),),    # the north wall, where the curtains hang
    "library":     (WindowMM("y-max", 10_500, 12_500, 900, 2_100),),
    "tv-room":     (WindowMM("y-max", 16_000, 18_000, 900, 2_100),),
    "kitchen":     (WindowMM("x-min", 1_500, 3_500, 1_000, 2_000),),   # the west wall: afternoon sun
    "dining":      (WindowMM("y-min", 8_500, 10_500, 900, 2_100),),    # south wall
    "daddys-room": (WindowMM("y-min", 13_000, 15_000, 900, 2_100),),   # south wall
    "wcs-room":    (WindowMM("y-min", 17_500, 19_000, 1_400, 2_100),), # south high clerestory
}


def _planks(base: tuple[int, ...], columns: int = 32, rows: int = 32) -> ObjectOpticalSurface:
    """Floor planks running along the face: each row of planks a shade of the base paint,
    a dark joint between planks and a staggered dark end joint."""
    palette = tuple(tuple(max(10_000, min(1_000_000, int(c * s))) for c in base) for s in (1.00, 0.86, 0.72, 0.40))
    cells = []
    for r in range(rows):
        for c in range(columns):
            plank = r // 4
            if r % 4 == 3 or (c + 5 * plank) % 16 == 15:
                cells.append(3)                       # the joint
            else:
                cells.append((plank * 7 + (c + 5 * plank) // 16) % 3)   # this plank's shade
    surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
    surface.verify()
    return surface


def _panels(base: tuple[int, ...], columns: int = 32, rows: int = 32) -> ObjectOpticalSurface:
    """Wall panels: a lighter field framed by a darker rail and stile, a dado line."""
    palette = tuple(tuple(max(10_000, min(1_000_000, int(c * s))) for c in base) for s in (1.00, 0.80, 0.55))
    cells = []
    for r in range(rows):
        for c in range(columns):
            frame = r % 11 in (0, 10) or c % 8 in (0, 7)
            cells.append(2 if r == 20 else 1 if frame else 0)
    surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
    surface.verify()
    return surface


def _framed_art(name: str, art_type: str, frame_ppm: tuple[int, ...] = (30_000,) * 6, mat_ppm: tuple[int, ...] = (960_000,) * 6) -> ObjectOpticalSurface:
    """Generate high-contrast architectural gallery art with thin black frame and white mat."""
    cols, rows = 32, 32
    palette = (
        frame_ppm,                             # 0: deep matte black frame / ink
        tuple(int(c * 0.45) for c in mat_ppm), # 1: middle architectural charcoal/grey
        tuple(int(c * 0.78) for c in mat_ppm), # 2: soft light grey tone
        mat_ppm,                               # 3: stark crisp white mat / canvas
    )
    cells = [3] * (cols * rows)
    # Outer Frame (border thickness = 2)
    for r in range(rows):
        for c in range(cols):
            if r < 2 or r >= rows - 2 or c < 2 or c >= cols - 2:
                cells[r * cols + c] = 0

    # Artwork in Center (r in 5..26, c in 5..26)
    for r in range(5, 27):
        for c in range(5, 27):
            idx = r * cols + c
            dr = r - 16
            dc = c - 16
            if art_type == "arch":
                # Solid black arch: semicircular top, vertical straight legs down
                if r <= 15:
                    if dr * dr + dc * dc <= 42:
                        cells[idx] = 0
                else:
                    if abs(dc) <= 6 and r <= 24:
                        cells[idx] = 0
            elif art_type == "circle":
                # Solid black circle
                if dr * dr + dc * dc <= 40:
                    cells[idx] = 0
            elif art_type == "mountain":
                # Sharp geometric diagonal / mountain silhouette
                if r >= 14 and (r + c >= 30 or (r >= 20 and c >= 10)):
                    cells[idx] = 0 if c >= 16 else 1
            elif art_type == "slash":
                # Dynamic expressive diagonal ink gesture
                diff = (r - 7) - (c - 8)
                if abs(diff) <= 3 and 7 <= r <= 24 and 7 <= c <= 24:
                    cells[idx] = 0 if abs(diff) <= 1 else 1
            elif art_type == "archway":
                # Architectural corridor / nested perspective arches
                d2 = dr * dr + dc * dc
                if 45 <= d2 <= 70 or 15 <= d2 <= 28 or d2 <= 6:
                    cells[idx] = 0 if d2 <= 6 else 1
                elif r > 16 and (abs(dc) in (2, 5, 8)):
                    cells[idx] = 0
            elif art_type == "horizontal":
                # Clean horizontal minimalist landscape
                if 15 <= r <= 17:
                    cells[idx] = 0
                elif 18 <= r <= 23 and 10 <= c <= 22:
                    cells[idx] = 1
            elif art_type == "minimal_arch":
                # Subtle light-grey architectural arch
                if r <= 16:
                    if dr * dr + dc * dc <= 45:
                        cells[idx] = 2
                else:
                    if abs(dc) <= 6 and r <= 23:
                        cells[idx] = 2

    used = set(cells)
    for p_i in range(4):
        if p_i not in used:
            cells[p_i] = p_i

    surface = ObjectOpticalSurface(cols, rows, palette, tuple(cells))
    surface.verify()
    return surface


def _textured_rug(base: tuple[int, ...], cols: int = 32, rows: int = 32) -> ObjectOpticalSurface:
    """Rich woven area rug with crisp charcoal border and textured weave."""
    palette = (
        (50_000,) * 6,                          # 0: deep charcoal border band
        tuple(max(10_000, int(c * 0.75)) for c in base), # 1: darker woven weft
        tuple(max(10_000, int(c * 0.90)) for c in base), # 2: textured body weave
        base,                                   # 3: bright crisp weave highlight
    )
    cells = []
    for r in range(rows):
        for c in range(cols):
            if r < 2 or r >= rows - 2 or c < 2 or c >= cols - 2:
                cells.append(0)
            elif r in (3, rows - 4) or c in (3, cols - 4):
                cells.append(2)
            else:
                cells.append(1 if (r + c) % 3 == 0 else (3 if (r - c) % 4 == 0 else 2))
    surface = ObjectOpticalSurface(cols, rows, palette, tuple(cells))
    surface.verify()
    return surface


def _stone_tiles(base: tuple[int, ...], columns: int = 32, rows: int = 32) -> ObjectOpticalSurface:
    """Large-format stone/slate floor tiles with clean dark joints."""
    palette = (
        (30_000,) * 6,                          # dark grout joint
        tuple(max(10_000, int(c * 0.85)) for c in base), # stone shadow
        base,                                   # stone body
        tuple(min(1_000_000, int(c * 1.15)) for c in base), # stone highlight
    )
    cells = []
    for r in range(rows):
        for c in range(columns):
            if r % 8 == 7 or c % 8 == 7:
                cells.append(0)
            else:
                cells.append(1 if (r * 7 + c * 13) % 5 == 0 else (3 if (r + c) % 4 == 0 else 2))
    surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
    surface.verify()
    return surface


def _subway_tiles(base: tuple[int, ...], columns: int = 32, rows: int = 32) -> ObjectOpticalSurface:
    """Staggered ceramic subway tiles with crisp grout lines."""
    palette = (
        (40_000,) * 6,                          # dark grout
        tuple(max(10_000, int(c * 0.90)) for c in base), # tile bevel
        base,                                   # clean ceramic tile
        (980_000,) * 6,                         # bright glaze pop
    )
    cells = []
    for r in range(rows):
        for c in range(columns):
            row_idx = r // 4
            offset = 8 if row_idx % 2 == 1 else 0
            if r % 4 == 3 or (c + offset) % 16 == 15:
                cells.append(0)
            elif r % 4 == 0 or (c + offset) % 16 == 0:
                cells.append(1)
            elif r % 4 == 1 and (c + offset) % 16 == 4:
                cells.append(3)
            else:
                cells.append(2)
    surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
    surface.verify()
    return surface


def _vanity_mirror(base: tuple[int, ...], columns: int = 32, rows: int = 32) -> ObjectOpticalSurface:
    """Circular vanity mirror with metallic frame and backlit halo."""
    palette = (
        (20_000,) * 6,   # matte black frame
        (150_000,) * 6,  # dark mirror glass
        (650_000,) * 6,  # glowing halo
        (950_000,) * 6,  # bright backlit rim
    )
    cells = []
    for r in range(rows):
        for c in range(columns):
            d2 = (r - 16)**2 + (c - 16)**2
            if 196 <= d2 <= 225:
                cells.append(0)
            elif 144 <= d2 < 196:
                cells.append(3)
            elif 100 <= d2 < 144:
                cells.append(2)
            else:
                cells.append(1)
    surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
    surface.verify()
    return surface


_arch_art = _framed_art("arch", "arch")
_circle_art = _framed_art("circle", "circle")
_mountain_art = _framed_art("mountain", "mountain")
_slash_art = _framed_art("slash", "slash")
_archway_art = _framed_art("archway", "archway")
_horizontal_art = _framed_art("horizontal", "horizontal")
_min_arch_art = _framed_art("min_arch", "minimal_arch")
_living_rug = _textured_rug((850_000,) * 6)
_planks_380 = _planks((380_000,) * 6)
_panels_380 = _panels((380_000,) * 6)
_stone_280 = _stone_tiles((280_000,) * 6)
_stone_320 = _stone_tiles((320_000,) * 6)
_subway_920 = _subway_tiles((920_000,) * 6)
_mirror = _vanity_mirror((900_000,) * 6)


HOME_LOOKS = {
    "her-room": (
        SurfaceLookMM("floor", 0, 5_600, 5_000, 10_000, _planks_380),
        SurfaceLookMM("y-min", 0, 5_600, 0, 2_600, _panels_380),      # the south wall she faces from her bed
    ),
    "tv-room": (
        # 1. Gallery Wall: 7 framed prints exactly matching the reference architectural photograph
        SurfaceLookMM("y-min", 14_800, 15_400, 1_650, 2_250, _archway_art),    # Frame 1: Archway photo (upper left)
        SurfaceLookMM("y-min", 14_800, 15_400,   950, 1_550, _circle_art),     # Frame 2: Black circle (lower left)
        SurfaceLookMM("y-min", 15_600, 16_400, 1_350, 2_250, _arch_art),       # Frame 3: Tall black arch (center top)
        SurfaceLookMM("y-min", 15_600, 16_400,   450, 1_250, _slash_art),      # Frame 4: Ink slash (center bottom)
        SurfaceLookMM("y-min", 16_600, 17_300, 1_750, 2_250, _min_arch_art),   # Frame 5: Minimal arch relief (center-right top)
        SurfaceLookMM("y-min", 16_600, 17_300, 1_200, 1_650, _horizontal_art), # Frame 6: Horizontal canvas (center-right mid)
        SurfaceLookMM("y-min", 17_500, 18_300, 1_100, 2_250, _mountain_art),   # Frame 7: Geometric mountain (far right)
        # 2. Floor: Living room area rug + hardwood planks
        SurfaceLookMM("floor", 15_000, 19_000, 5_800, 8_600, _living_rug),
        SurfaceLookMM("floor", 14_000, 20_000, 5_000, 10_000, _planks_380),
    ),
    "dining": (
        SurfaceLookMM("y-max", 9_200, 10_200, 1_200, 2_100, _arch_art),
        SurfaceLookMM("y-max", 10_500, 11_500, 1_200, 2_100, _mountain_art),
        SurfaceLookMM("floor", 7_000, 12_000, 0, 5_000, _planks_380),
    ),
    "daddys-room": (
        SurfaceLookMM("y-max", 12_800, 13_800, 1_200, 2_100, _archway_art),
        SurfaceLookMM("y-max", 14_200, 15_200, 1_200, 2_100, _horizontal_art),
        SurfaceLookMM("floor", 12_500, 15_500, 1_200, 4_200, _living_rug),
        SurfaceLookMM("floor", 12_000, 16_000, 0, 5_000, _planks_380),
    ),
    "wcs-room": (
        SurfaceLookMM("y-max", 16_500, 17_500, 1_200, 1_900, _mirror),
        SurfaceLookMM("floor", 16_000, 20_000, 0, 5_000, _stone_280),
    ),
    "kitchen": (
        SurfaceLookMM("y-max", 800, 4_800, 900, 1_600, _subway_920),
        SurfaceLookMM("floor", 0, 7_000, 0, 5_000, _stone_320),
    ),
    "library": (
        SurfaceLookMM("floor", 10_500, 13_500, 5_500, 8_500, _living_rug),
        SurfaceLookMM("floor", 9_000, 14_000, 5_000, 10_000, _planks_380),
    ),
}


# Shapes: what her eye meets. A thing is a sphere unless declared here as a box:
# (extents x, y, z in its own frame, heading about the vertical, height of its bottom
# above the floor). Below the walking layer the footprint disc every planar law uses
# must cover the box's plan, so such a box's radius is raised to that when needed; a
# framed picture above it keeps its own footprint and hangs flat. First ones (C1):
# her room's bed, chest, desk and chair, the two framed pictures on the west wall,
# the library's shelves and the dining table. A1 extends as the home's content owner.
HOME_SHAPES = {
    # her room
    "bed":              ((1_500,   950,   500),      0,     0),
    "pillow":           ((  350,   250,   120),      0,     0),
    "blanket":          ((  380,   380,   150),      0,     0),
    "curtains":         ((  480,    40, 2_000),      0,   300),   # a hanging panel by the north window
    "toy-chest":        ((  800,   450,   450),      0,     0),
    "desk":             ((1_200,   600,   750),      0,     0),
    "desk-chair":       ((  400,   400,   850),      0,     0),
    "wall-art-shapes":  ((   40,   560,   760),      0, 1_300),   # framed pictures flat on the west wall
    "wall-art-weather": ((   40,   560,   760),      0, 1_300),
    # kitchen
    "kitchen-counter":  ((  700,   700,   900),      0,     0),
    "pantry":           ((  490,   490, 1_800),      0,     0),
    "refrigerator":     ((  630,   630, 1_800),      0,     0),
    "stove":            ((  560,   560,   900),      0,     0),
    "table":            ((  840,   840,   750),      0,     0),
    # dining
    "dining-table":     ((1_200,   700,   750),      0,     0),
    "dining-chair":     ((  360,   360,   850),      0,     0),
    "dining-chair-south": ((360,   360,   850),      0,     0),
    "sideboard":        ((  800,   400,   850),      0,     0),
    # daddy's room
    "daddys-armchair":  ((  630,   630,   800),      0,     0),
    "daddys-desk":      ((  560,   560,   750),      0,     0),
    "daddys-chair":     ((  360,   360,   850),      0,     0),
    "daddys-book":      ((  160,   120,    40),      0,     0),
    # library
    "shelf-a":          ((  700,   300, 1_800),      0,     0),
    "shelf-b":          ((  700,   300, 1_800),      0,     0),
    "book":             ((  190,   140,    40),      0,     0),
    # tv room
    "sofa":             ((1_700,   800,   800),      0,     0),
    "television":       ((1_000,   400,   700),      0,     0),
    "rug":              ((  840,   840,    20),      0,     0),
    "radio":            ((  200,   120,   150),      0,     0),
    # the wc's room
    "bath-tub":         ((1_000,   600,   550),      0,     0),
    "wash-basin":       ((  420,   420,   850),      0,     0),
    "bath-mat":         ((  490,   490,    20),      0,     0),
    "bath-towel":       ((  280,   280,    40),      0,     0),
    # backyard
    "sandbox":          ((1_550, 1_550,   200),      0,     0),
    "slide":            ((1_200,   600, 1_500),      0,     0),
    "swing":            ((  980,   400, 2_000),      0,     0),
    "garden-patch":     ((1_690, 1_690,   150),      0,     0),
}

# Boxes wear their paint flat (a sofa, a table, a tub: one material, its faces told
# apart by the light) except the things whose declared pattern is the point of them.
PATTERNED_BOXES = ("wall-art-shapes", "wall-art-weather", "television", "book", "daddys-book")

# Lamps at their heights: a shade on a stand, a pendant over a table, a light on a
# vanity. The thing keeps its footprint disc on the floor; its shade (and so its
# light) sits this far above the floor. First heights (C1); A1 corrects as content owner.
HOME_LAMP_HEIGHTS = {
    "kitchen-lamp": 1_500,     # a pendant over the counter
    "dining-lamp":  1_600,     # a pendant by the table
    "daddys-lamp":    750,     # the reading lamp on the desk
    "bath-lamp":    1_400,     # the vanity light
    "lamp":         1_300,     # the library's floor lamp
    "glow-stars":   2_300,     # on the ceiling above her bed
}

# Her room's nightlight (A1 listed it; declared here so her nights are not black).
NIGHT_LIGHT = ("night-light", 4_600, 8_600, 80, 300, 250, (900_000,) * 6, (300_000,) * 6)


def _shaped(things: list[Any]) -> list[Any]:
    """Apply the declared shapes to the things that have one."""
    import math
    from dataclasses import replace

    from dsf_ai_service.substrate.embodiment_world import WALKING_LAYER_MM

    shaped = []
    for item in things:
        declared = HOME_SHAPES.get(item.object_id)
        if declared is None:
            shaped.append(item)
            continue
        size, heading, elevation = declared
        needed = math.ceil(math.hypot(size[0], size[1]) / 2) if elevation < WALKING_LAYER_MM else 0
        shaped.append(replace(item, shape="box", size_mm=tuple(size), heading_millidegrees=heading, elevation_mm=elevation,
                              radius_mm=max(item.radius_mm, needed),
                              optical_surface=item.optical_surface if item.object_id in PATTERNED_BOXES else None))
    shaped = [replace(item, elevation_mm=HOME_LAMP_HEIGHTS[item.object_id]) if item.object_id in HOME_LAMP_HEIGHTS else item for item in shaped]
    from dsf_ai_service.substrate.embodiment_world import EmbodiedObject, PositionMM
    name, x, y, radius, mass, height, reflectance, emission = NIGHT_LIGHT
    if all(item.object_id != name for item in shaped):
        shaped.append(EmbodiedObject(name, radius, mass, PositionMM(x, y, 0), reflectance_ppm=reflectance, emission_ppm=emission, elevation_mm=height))
    return shaped


def _home_optical_surface_for(
    name: str,
    base_ref: tuple[int, int, int, int, int, int],
) -> Any:
    """Generate a deterministic, content-addressed optical surface for an object.

    Each surface is a 32x32 grid with 4 reflectance spectrum shades derived from
    the object's base spectral reflectance, giving the world-eye raycaster
    fine structural contrast.
    """
    def scale_spec(scale: float) -> tuple[int, int, int, int, int, int]:
        return tuple(
            max(10_000, min(1_000_000, int(round(c * scale))))
            for c in base_ref
        )

    # Wide dynamic-range span (0.08, 0.35, 0.70, 1.00) ensures clear foveal step
    # functions across all surfaces, preventing radial ring collapse in Level 1 eye.
    palette_list = [
        scale_spec(0.08),
        scale_spec(0.35),
        scale_spec(0.70),
        scale_spec(1.00),
    ]
    seen = set()
    for i, p in enumerate(palette_list):
        curr = list(p)
        while tuple(curr) in seen:
            if curr[0] >= 1_000_000:
                curr = [max(10_000, c - 10_000 * (i + 1)) for c in curr]
            else:
                curr = [min(1_000_000, c + 10_000 * (i + 1)) for c in curr]
        seen.add(tuple(curr))
        palette_list[i] = tuple(curr)
    palette = tuple(palette_list)

    cols, rows = 32, 32
    cells = [0] * (cols * rows)
    num_p = 4

    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            if any(k in name for k in ("table", "chair", "desk", "shelf", "chest", "counter", "cabinet", "pantry", "sideboard", "dresser", "bench")):
                val = (
                    1
                    if (r in (0, rows - 1) or c in (0, cols - 1) or r == 16 or c == 16)
                    else (0 if ((r // 4) + (c // 4)) % 2 == 0 else 2)
                )
            elif "refrigerator" in name:
                val = 0 if (r in (0, rows - 1) or c in (0, cols - 1)) else (2 if c == cols // 2 else 1)
            elif "stove" in name:
                d_b1 = (r - 8) ** 2 + (c - 8) ** 2
                d_b2 = (r - 8) ** 2 + (c - 24) ** 2
                d_b3 = (r - 24) ** 2 + (c - 8) ** 2
                d_b4 = (r - 24) ** 2 + (c - 24) ** 2
                val = 3 if min(d_b1, d_b2, d_b3, d_b4) <= 16 else (1 if (r % 4 == 0 or c % 4 == 0) else 0)
            elif any(k in name for k in ("blanket", "curtains", "towel")):
                if "curtains" in name:
                    val = (c % 4) % num_p
                else:
                    val = (((r // 4) % 2) ^ ((c // 4) % 2) + ((r + c) % 3)) % num_p
            elif any(k in name for k in ("rug", "mat")):
                if r < 3 or r >= rows - 3 or c < 3 or c >= cols - 3:
                    val = 0
                elif r in (4, rows - 5) or c in (4, cols - 5):
                    val = 3
                elif abs(r - 16) + abs(c - 16) <= 8:
                    val = 2
                else:
                    val = 1
            elif "book" in name:
                if c < 6:
                    val = 0
                elif (c in (8, cols - 3) and 3 <= r <= rows - 4) or (
                    r in (3, rows - 4) and 8 <= c <= cols - 3
                ):
                    val = 3
                elif 12 <= r <= 20 and 14 <= c <= 22:
                    val = 2
                else:
                    val = 1
            elif "television" in name:
                if r < 3 or r >= rows - 3 or c < 3 or c >= cols - 3:
                    val = 0 if not (r >= rows - 2 and c >= cols - 4) else 3
                else:
                    val = 1 if r % 2 == 0 else 2
            elif any(k in name for k in ("bowl", "cup", "apple", "pot", "pan", "plate", "tub", "basin", "soap")):
                d2 = (r - 16) ** 2 + (c - 16) ** 2
                if "apple" in name:
                    if r < 6 and 14 <= c <= 17:
                        val = 0
                    elif d2 > 200:
                        val = 1
                    elif (r * 11 + c * 7) % 5 == 0:
                        val = 3
                    else:
                        val = 2
                elif any(k in name for k in ("pot", "pan")):
                    val = 3 if 64 <= d2 <= 144 else (2 if d2 <= 64 else 0)
                elif any(k in name for k in ("bowl", "tub", "basin")):
                    if d2 <= 36:
                        val = 3
                    elif d2 <= 144:
                        val = 1
                    elif d2 <= 225:
                        val = 2
                    else:
                        val = 0
                elif "plate" in name:
                    val = 1 if 100 <= d2 <= 196 else (2 if d2 < 100 else 0)
                else:
                    if d2 <= 36:
                        val = 3
                    elif d2 <= 144:
                        val = 1
                    elif d2 <= 225:
                        val = 2
                    else:
                        val = 0
            elif "toy-bear" in name:
                d_ear1 = (r - 7) ** 2 + (c - 8) ** 2
                d_ear2 = (r - 7) ** 2 + (c - 23) ** 2
                d_head = (r - 16) ** 2 + (c - 16) ** 2
                d_muzzle = (r - 18) ** 2 + (c - 16) ** 2
                if d_ear1 <= 16 or d_ear2 <= 16:
                    val = 0
                elif (r in (13, 14) and c in (11, 20)) or (r == 17 and c == 16):
                    val = 0
                elif d_muzzle <= 20:
                    val = 2
                elif d_head <= 144:
                    val = 1
                else:
                    val = 3
            elif "glow-stars" in name:
                d = abs(r - 16) + abs(c - 16)
                if d <= 3:
                    val = 3
                elif (r == 16 and abs(c - 16) <= 12) or (c == 16 and abs(r - 16) <= 12):
                    val = 2
                elif d <= 10:
                    val = 1
                else:
                    val = 0
            elif "lamp" in name:
                if r < 18:
                    val = 2 if c % 4 < 2 else 3
                elif 18 <= r <= 25 and 14 <= c <= 17:
                    val = 0
                else:
                    val = 1
            elif any(k in name for k in ("sofa", "armchair")):
                if r < 3 or r >= rows - 3 or c < 3 or c >= cols - 3:
                    val = 0
                else:
                    val = 1 if (r + c) % 2 == 0 else 2
            elif "radio" in name:
                val = 3 if (r in (6, 7) and 8 <= c <= 24) else (2 if (r >= 12 and (r + c) % 3 == 0) else 1)
            elif "tree" in name:
                d2 = (r - 16) ** 2 + (c - 16) ** 2
                if d2 <= 25:
                    val = 0
                elif d2 <= 100:
                    val = 2
                elif d2 <= 225:
                    val = 1
                else:
                    val = 3
            elif "wall-art" in name or "art" in name:
                if r < 16 and c < 16:
                    val = 0 if (r - 8) ** 2 + (c - 8) ** 2 <= 25 else 1
                elif r < 16:
                    val = 2 if (r + c) % 4 < 2 else 3
                elif c < 16:
                    val = 3 if ((r // 4) + (c // 4)) % 2 == 0 else 0
                else:
                    val = 1 if (r == 24 or c == 24) else 2
            elif any(k in name for k in ("slide", "swing", "sandbox", "garden")):
                if "slide" in name:
                    val = (
                        0
                        if c in (0, 1, cols - 2, cols - 1)
                        else (1 if (r - c) % 6 < 3 else 2)
                    )
                elif "swing" in name:
                    val = (
                        0
                        if c in (6, 25)
                        else (1 if 12 <= r <= 19 else (2 if r % 4 == 0 else 3))
                    )
                elif "sandbox" in name:
                    val = (
                        0
                        if (r < 3 or r >= rows - 3 or c < 3 or c >= cols - 3)
                        else (((r * 17 + c * 31) % 3) + 1)
                    )
                else:
                    val = 0 if (r // 4) % 2 == 0 else (((c // 4) % 3) + 1)
            else:
                val = ((r // 4) + (c // 4)) % num_p
            cells[idx] = val % num_p

    used = set(cells)
    for p_i in range(num_p):
        if p_i not in used:
            cells[p_i] = p_i

    surf = ObjectOpticalSurface(cols, rows, palette, tuple(cells))
    surf.verify()
    return surf


def _home_rooms_and_things() -> tuple[list[Any], list[Any], list[Any]]:
    """Declare the rooms and things of Guala's home.

    Phase-1 sensory geometry: each room is a signed rectilinear box on
    the floor; each door is a signed portal connecting two rooms; each
    thing is a bounded cylinder. Clearance between any two things, and
    between every thing and every wall, is at least one body diameter so
    a body can walk anywhere.
    """

    from dataclasses import replace
    from dsf_ai_service.substrate.embodiment_world import (
        AirVolumeState,
        EmbodiedObject,
        ObjectMaterialState,
        PhysicalPortal,
        PhysicalRegion,
        PositionMM,
        RoomBoundsMM,
    )

    HOME_CEILING_MM = 2_600
    BACKYARD_SKY_MM = 8_000
    # The home plan: 8 indoor rooms + 1 backyard. Hallway connects all.
    # Night floor ambient illumination (45,000 to 55,000 ppm) provides genuine
    # photographic contrast: dark night house where lamps and windows cast sharp
    # directional shadows, rather than a perpetual flat 24/7 noon-flood.
    plan = (
        ("kitchen",       0,      0,  7_000,  5_000, HOME_CEILING_MM, 55_000),
        ("dining",        7_000,  0, 12_000,  5_000, HOME_CEILING_MM, 45_000),
        ("daddys-room",  12_000,  0, 16_000,  5_000, HOME_CEILING_MM, 45_000),
        ("wcs-room",     16_000,  0, 20_000,  5_000, HOME_CEILING_MM, 45_000),
        ("her-room",      0,  5_000,  5_600, 10_000, HOME_CEILING_MM, 45_000),
        ("hallway",       5_600, 5_000, 9_000, 10_000, HOME_CEILING_MM, 65_000),
        ("library",       9_000, 5_000, 14_000, 10_000, HOME_CEILING_MM, 45_000),
        ("tv-room",      14_000, 5_000, 20_000, 10_000, HOME_CEILING_MM, 45_000),
        # The backyard's ceiling is the sky: tall, bright, outdoors.
        ("backyard",      0, 10_000, 20_000, 16_000, BACKYARD_SKY_MM, 950_000),
    )
    # Architectural Zone V floor/wall baseline (380,000 ppm) provides high contrast
    # in both directions: bright whites pop (+115 to +130 pts), matte blacks sink (-40 to -75 pts).
    regions = [
        PhysicalRegion(
            region_id=name,
            bounds=RoomBoundsMM(
                minimum=PositionMM(min_x, min_y, 0),
                maximum=PositionMM(max_x, max_y, ceiling),
            ),
            ceiling_height_mm=ceiling,
            reflectance_ppm=(
                (180_000, 260_000, 140_000, 110_000, 90_000, 80_000)
                if name == "backyard"
                else (380_000,) * 6
            ),
            illumination_ppm=(light,) * 6,
            windows=HOME_WINDOWS.get(name, ()),
            looks=HOME_LOOKS.get(name, ()),
        )
        for name, min_x, min_y, max_x, max_y, ceiling, light in plan
    ]
    # Doors 1.4m wide minimum; the hallway connects everything and the
    # backyard opens from the hallway, exactly as the blueprint says.
    portals = [
        PhysicalPortal(
            portal_id=f"door-{index}",
            region_ids=tuple(sorted(pair)),
            axis=axis,
            plane_mm=plane,
            aperture_min_mm=ap_min,
            aperture_max_mm=ap_max,
            height_mm=2_050,
        )
        for index, (pair, axis, plane, ap_min, ap_max) in enumerate((
            (("kitchen", "dining"),        "x",  7_000, 1_800, 3_200),
            (("dining", "daddys-room"),    "x", 12_000, 1_800, 3_200),
            (("daddys-room", "wcs-room"),  "x", 16_000, 1_800, 3_200),
            (("her-room", "hallway"),      "x",  5_600, 6_900, 8_300),
            (("hallway", "library"),       "x",  9_000, 6_900, 8_300),
            (("library", "tv-room"),       "x", 14_000, 6_900, 8_300),
            (("kitchen", "hallway"),       "y",  5_000, 5_600, 7_000),
            (("dining", "hallway"),        "y",  5_000, 7_300, 8_700),
            (("hallway", "backyard"),      "y", 10_000, 6_000, 7_400),
        ))
    ]
    # (id, absolute x, y, radius, mass, reflectance) — clearances are
    # pre-checked against every neighbouring radius and wall.
    # Exactly 51 items total: guarantees 13 slots of headroom below 64 ceiling.
    # Floor-standing lamps declared in every room provide authentic directional light.
    furniture = (
        # --- 1. KITCHEN (11 items: domestic hub, counters, appliances, cookware, task lamp) ---
        ("pantry",            700,    600, 350, 25_000, (320_000, 280_000, 250_000, 220_000, 200_000, 180_000)),
        ("refrigerator",      700,  2_000, 450, 60_000, (900_000, 900_000, 900_000, 900_000, 900_000, 900_000)),
        ("kitchen-counter", 1_000,  4_500, 500, 40_000, (180_000, 180_000, 180_000, 180_000, 180_000, 180_000)),
        ("pan",             1_800,  4_600, 130,    900, (50_000,   50_000,  50_000,  50_000,  50_000,  50_000)),
        ("pot",             2_200,  4_600, 140,  1_200, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("stove",           1_600,    600, 400, 45_000, (50_000,   50_000,  50_000,  50_000,  50_000,  50_000)),
        ("bowl",            2_400,    600, 150,    700, (920_000, 920_000, 920_000, 920_000, 920_000, 920_000)),
        ("cup",             4_800,    600, 100,    300, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("apple",           5_650,    900,  90,    180, (720_000, 220_000, 160_000, 140_000, 130_000, 120_000)),
        ("table",           3_500,  2_500, 600, 28_000, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("kitchen-lamp",    1_000,  3_500, 180,  2_500, (900_000, 850_000, 750_000, 600_000, 500_000, 450_000)),

        # --- 2. DINING ROOM (5 items: white dining table, black chairs, credenza, dining lamp) ---
        ("dining-table",       9_500, 2_500, 700, 35_000, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("dining-chair",       9_500, 3_600, 260,  6_000, (50_000,   50_000,  50_000,  50_000,  50_000,  50_000)),
        ("dining-chair-south", 9_500, 1_400, 260,  6_000, (50_000,   50_000,  50_000,  50_000,  50_000,  50_000)),
        ("sideboard",         11_300, 4_200, 450, 38_000, (220_000, 180_000, 150_000, 130_000, 120_000, 110_000)),
        ("dining-lamp",       11_400,   800, 220,  4_000, (900_000, 850_000, 750_000, 600_000, 500_000, 450_000)),

        # --- 3. DADDY'S ROOM (5 items: mahogany study, desk, leather chair, book, brass reading lamp, armchair) ---
        ("daddys-desk",       13_800, 4_300, 400, 36_000, (160_000, 120_000, 100_000,  80_000,  70_000,  60_000)),
        ("daddys-chair",      13_800, 3_400, 260,  8_000, (80_000,   60_000,  50_000,  50_000,  50_000,  50_000)),
        ("daddys-book",       14_600, 4_300, 120,    900, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000)),
        ("daddys-lamp",       15_300, 3_500, 160,  2_500, (880_000, 850_000, 780_000, 700_000, 650_000, 620_000)),
        ("daddys-armchair",   13_000, 1_000, 450, 22_000, (120_000,  90_000,  80_000,  70_000,  60_000,  50_000)),

        # --- 4. WC'S ROOM (5 items: white porcelain soaking tub, wash basin, bath lamp, towel, mat) ---
        ("bath-tub",          18_600, 4_100, 600, 55_000, (950_000, 950_000, 950_000, 950_000, 950_000, 950_000)),
        ("wash-basin",        17_000, 4_400, 300, 22_000, (920_000, 920_000, 920_000, 920_000, 920_000, 920_000)),
        ("bath-lamp",         17_000, 3_200, 150,  1_800, (850_000, 800_000, 700_000, 550_000, 450_000, 400_000)),
        ("bath-towel",        17_000, 3_700, 200,    800, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("bath-mat",          18_600, 3_000, 350,  1_500, (80_000,   80_000,  80_000,  80_000,  80_000,  80_000)),

        # --- 5. HER ROOM (11 items: bed, pillow, blanket, bear, toy chest, desk, chair, curtains, art, stars) ---
        ("bed",                1_200, 8_800, 900, 40_000, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000)),
        ("pillow",             1_200, 7_600, 260,  1_200, (920_000, 920_000, 920_000, 920_000, 920_000, 920_000)),
        ("blanket",            3_400, 9_300, 300,    900, (120_000, 120_000, 120_000, 120_000, 120_000, 120_000)),
        ("toy-bear",           4_800, 9_200, 180,    400, (480_000, 340_000, 260_000, 220_000, 200_000, 180_000)),
        ("toy-chest",          1_000, 5_600, 500,  8_000, (450_000, 350_000, 280_000, 240_000, 220_000, 200_000)),
        ("desk",               4_000, 6_400, 800, 32_000, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("desk-chair",         5_150, 6_400, 320,  6_000, (50_000,   50_000,  50_000,  50_000,  50_000,  50_000)),
        ("curtains",           2_800, 9_700, 250,  1_500, (920_000, 880_000, 820_000, 780_000, 740_000, 700_000)),
        ("wall-art-shapes",      320, 7_000, 310,    600, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("wall-art-weather",     320, 7_800, 310,    600, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("glow-stars",         2_200, 9_700, 120,    300, (940_000, 930_000, 700_000, 400_000, 300_000, 260_000)),

        # --- 6. LIBRARY (4 items: reading shelves, reading desk, canonical book, reading lamp) ---
        ("shelf-a",           10_000, 9_500, 400, 30_000, (180_000, 180_000, 180_000, 180_000, 180_000, 180_000)),
        ("shelf-b",           12_500, 9_500, 400, 30_000, (180_000, 180_000, 180_000, 180_000, 180_000, 180_000)),
        ("book",              12_000, 7_500, 140,    900, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000)),
        ("lamp",              13_500, 5_400, 180,  2_200, (880_000, 850_000, 780_000, 700_000, 650_000, 620_000)),

        # --- 7. TV ROOM (4 items: modern lounge, widescreen television, radio, charcoal sofa, rug) ---
        ("television",        17_000, 9_200, 700, 12_000, (50_000,   50_000,  50_000,  50_000,  50_000,  50_000)),
        ("radio",             15_400, 9_400, 150,  1_200, (180_000, 180_000, 180_000, 180_000, 180_000, 180_000)),
        ("sofa",              17_000, 6_800, 950, 45_000, (80_000,   80_000,  80_000,  80_000,  80_000,  80_000)),
        ("rug",               15_000, 6_000, 600,  5_000, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000)),

        # --- 8. BACKYARD (6 items: playground, slide, swing, sandbox, garden patch, oak, pine) ---
        ("slide",              3_000, 13_500, 900, 25_000, (700_000, 720_000, 740_000, 700_000, 650_000, 600_000)),
        ("swing",              7_000, 14_000, 700, 15_000, (480_000, 430_000, 380_000, 340_000, 320_000, 300_000)),
        ("sandbox",           11_500, 13_500, 1_100, 60_000, (820_000, 780_000, 700_000, 620_000, 560_000, 520_000)),
        ("garden-patch",      16_500, 13_500, 1_200, 80_000, (300_000, 380_000, 300_000, 260_000, 240_000, 220_000)),
        ("tree-oak",           1_500, 14_500, 600, 120_000, (120_000, 280_000, 150_000, 100_000,  80_000,  70_000)),
        ("tree-pine",         19_000, 14_500, 600, 110_000, (80_000,  220_000, 120_000,  90_000,  70_000,  60_000)),
    )
    # (release ng/s per odour channel, tastants ug, surface mK, compliance
    #  ppm, roughness um, moisture ppm) — same channel meanings as before:
    #  0 fruit ester - 1 cooked savoury - 2 dairy fat - 3 wood/earth
    #  4 fabric dust - 5 paper ink - 6 warm electronics - 7 soap
    material_of = {
        # Kitchen
        "kitchen-counter":   ((0, 0, 0, 600, 50, 0, 0, 100), (0, 0, 0, 1_500, 0),        294_000, 40_000, 30, 20_000),
        "refrigerator":      ((0, 0, 0, 0, 10, 0, 100, 200), (0, 0, 0, 500, 0),          277_000, 20_000, 10, 5_000),
        "stove":             ((0, 400, 0, 0, 0, 0, 200, 0),   (0, 0, 0, 200, 0),          330_000, 15_000, 15, 2_000),
        "pantry":            ((0, 0, 0, 800, 100, 0, 0, 0),  (0, 0, 0, 1_200, 0),        294_000, 40_000, 45, 15_000),
        "pot":               ((0, 100, 0, 0, 0, 0, 0, 100),   (0, 0, 0, 100, 0),          320_000, 10_000, 5, 2_000),
        "pan":               ((0, 150, 0, 0, 0, 0, 0, 50),    (0, 0, 0, 100, 0),          295_000, 10_000, 20, 2_000),
        "bowl":              ((0, 300, 120, 0, 0, 0, 0, 200), (400, 900, 100, 200, 1_200), 294_000, 30_000, 8, 90_000),
        "table":             ((0, 0, 0, 800, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "kitchen-lamp":      ((0, 0, 0, 0, 20, 0, 260, 0),    (0, 0, 0, 400, 0),          310_000, 20_000, 10, 2_000),
        "apple":             ((4_200, 0, 0, 0, 0, 0, 0, 0),   (140_000, 200, 26_000, 900, 300), 292_000, 120_000, 15, 850_000),
        "cup":               ((0, 60, 40, 0, 0, 0, 0, 400),   (0, 0, 0, 0, 0),            291_000, 25_000, 6, 900_000),

        # Dining Room
        "dining-table":       ((0, 0, 0, 800, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "dining-chair":       ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "dining-chair-south": ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "sideboard":          ((0, 0, 0, 750, 50, 0, 0, 0),    (0, 0, 0, 1_400, 0),        294_000, 35_000, 30, 18_000),
        "dining-lamp":        ((0, 0, 0, 0, 20, 0, 260, 0),    (0, 0, 0, 400, 0),          310_000, 20_000, 10, 2_000),

        # Daddy's Room
        "daddys-desk":        ((0, 0, 0, 900, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 30_000, 25, 15_000),
        "daddys-chair":       ((0, 0, 0, 100, 600, 0, 0, 0),   (0, 0, 0, 1_000, 0),        294_000, 550_000, 50, 25_000),
        "daddys-book":        ((0, 0, 0, 60, 40, 1_200, 0, 0), (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "daddys-lamp":        ((0, 0, 0, 0, 10, 0, 200, 0),    (0, 0, 0, 300, 0),          312_000, 15_000, 8, 2_000),
        "daddys-armchair":    ((0, 0, 0, 80, 1_400, 0, 0, 0),  (0, 200, 0, 700, 0),        294_000, 720_000, 380, 45_000),

        # WC's Room
        "bath-tub":           ((0, 0, 0, 0, 0, 0, 0, 150),     (0, 0, 0, 100, 0),          291_000, 5_000, 2, 15_000),
        "wash-basin":         ((0, 0, 0, 0, 0, 0, 0, 150),     (0, 0, 0, 100, 0),          291_000, 5_000, 2, 20_000),
        "bath-lamp":          ((0, 0, 0, 0, 20, 0, 260, 0),    (0, 0, 0, 400, 0),          310_000, 20_000, 10, 2_000),
        "bath-towel":         ((0, 0, 0, 0, 800, 0, 0, 400),   (0, 0, 0, 500, 0),          294_000, 850_000, 350, 45_000),
        "bath-mat":           ((0, 0, 0, 0, 1_200, 0, 0, 100), (0, 0, 0, 500, 0),          294_000, 750_000, 500, 60_000),

        # Her Room
        "bed":                ((0, 0, 0, 0, 900, 0, 0, 120),   (0, 300, 0, 800, 0),        294_000, 600_000, 200, 55_000),
        "pillow":             ((0, 0, 0, 0, 600, 0, 0, 300),   (0, 300, 0, 800, 0),        294_000, 900_000, 120, 48_000),
        "blanket":            ((0, 0, 0, 0, 1_000, 0, 0, 150), (0, 300, 0, 800, 0),        294_000, 850_000, 150, 50_000),
        "toy-bear":           ((0, 0, 0, 0, 1_200, 0, 0, 60),  (0, 300, 0, 900, 0),        294_000, 800_000, 300, 42_000),
        "toy-chest":          ((0, 0, 0, 600, 80, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 50_000, 60, 20_000),
        "desk":               ((0, 0, 0, 700, 60, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "desk-chair":         ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "curtains":           ((0, 0, 0, 0, 700, 0, 0, 100),   (0, 0, 0, 600, 0),          293_000, 800_000, 120, 45_000),
        "wall-art-shapes":    ((0, 0, 0, 30, 20, 700, 0, 0),   (0, 0, 0, 1_800, 0),        294_000, 60_000, 50, 18_000),
        "wall-art-weather":   ((0, 0, 0, 30, 20, 700, 0, 0),   (0, 0, 0, 1_800, 0),        294_000, 60_000, 50, 18_000),
        "glow-stars":         ((0, 0, 0, 0, 10, 0, 120, 0),    (0, 0, 0, 900, 0),          294_000, 30_000, 10, 3_000),

        # Library
        "shelf-a":            ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "shelf-b":            ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "book":               ((0, 0, 0, 40, 30, 900, 0, 0),   (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "lamp":               ((0, 0, 0, 0, 20, 0, 260, 0),    (0, 0, 0, 400, 0),          310_000, 20_000, 10, 2_000),

        # TV Room
        "television":         ((0, 0, 0, 0, 40, 0, 700, 0),    (0, 0, 0, 400, 0),          306_000, 20_000, 5, 1_000),
        "radio":              ((0, 0, 0, 0, 40, 0, 300, 0),    (0, 0, 0, 400, 0),          296_000, 20_000, 8, 1_000),
        "sofa":               ((0, 0, 0, 120, 1_500, 0, 0, 90), (0, 300, 0, 800, 0),       294_000, 700_000, 400, 52_000),
        "rug":                ((0, 0, 0, 0, 2_200, 0, 0, 40),  (0, 300, 0, 900, 0),        294_000, 500_000, 800, 46_000),

        # Backyard
        "slide":              ((0, 0, 0, 0, 30, 0, 80, 0),     (0, 0, 0, 300, 0),          288_000, 15_000, 8, 10_000),
        "swing":              ((0, 0, 0, 300, 400, 0, 0, 0),   (0, 200, 0, 900, 0),        288_000, 250_000, 300, 30_000),
        "sandbox":            ((0, 0, 0, 100, 600, 0, 0, 0),   (0, 100, 0, 400, 0),        290_000, 40_000, 900, 25_000),
        "garden-patch":       ((0, 0, 0, 1_600, 300, 0, 0, 0), (0, 100, 200, 700, 100),    289_000, 450_000, 700, 320_000),
        "tree-oak":           ((0, 0, 0, 2_500, 0, 0, 0, 0),    (0, 0, 0, 2_000, 0),        288_000, 30_000, 800, 150_000),
        "tree-pine":          ((0, 0, 0, 3_200, 0, 0, 0, 0),    (0, 0, 0, 2_000, 0),        288_000, 30_000, 600, 120_000),
    }
    reservoir_seconds = 864_000
    # Things that give off their own light (the emitter law):
    # Floor-standing lamps provide active directional illumination.
    emission_of = {
        "lamp":            (900_000, 850_000, 750_000, 600_000, 500_000, 450_000),
        "glow-stars":      (120_000, 120_000, 100_000, 50_000, 20_000, 10_000),
        "daddys-lamp":     (900_000, 850_000, 750_000, 600_000, 500_000, 450_000),
        "dining-lamp":     (900_000, 850_000, 750_000, 600_000, 500_000, 450_000),
        "kitchen-lamp":    (900_000, 850_000, 750_000, 600_000, 500_000, 450_000),
        "bath-lamp":       (850_000, 800_000, 700_000, 550_000, 450_000, 400_000),
    }
    shapes_of = {
        "desk": ("box", (1_200, 600, 750), 0, 0),
        "wall-art-shapes": ("box", (50, 600, 760), 0, 1_300),
        "wall-art-weather": ("box", (50, 600, 760), 0, 1_300),
    }
    objects = [
        EmbodiedObject(
            name,
            radius,
            mass,
            PositionMM(x, y, 0),
            emission_ppm=emission_of.get(name, ()),
            reflectance_ppm=reflectance,
            optical_surface=_home_optical_surface_for(name, reflectance),
            material=ObjectMaterialState(
                odorant_reservoir_nanograms=tuple(
                    rate * reservoir_seconds for rate in material_of[name][0]
                ),
                odorant_release_nanograms_per_second=material_of[name][0],
                tastant_mass_micrograms=material_of[name][1],
                surface_temperature_millikelvin=material_of[name][2],
                compliance_ppm=material_of[name][3],
                roughness_micrometers=material_of[name][4],
                moisture_ppm=material_of[name][5],
            ),
            shape=shapes_of[name][0] if name in shapes_of else "sphere",
            size_mm=shapes_of[name][1] if name in shapes_of else (),
            heading_millidegrees=shapes_of[name][2] if name in shapes_of else 0,
            elevation_mm=shapes_of[name][3] if name in shapes_of else 0,
        )
        for name, x, y, radius, mass, reflectance in furniture
    ]
    # Each room's air is derived from what stands in it, exactly as before,
    # with room membership resolved from each thing's authored position.
    def room_of(x: int, y: int) -> str:
        for name, min_x, min_y, max_x, max_y, _c, _l in plan:
            if min_x <= x < max_x and min_y <= y < max_y:
                return name
        raise RuntimeError(f"authored thing stands outside every room ({x},{y})")

    settled_seconds = 3_600
    channel_count = len(material_of["apple"][0])
    room_air = {name: [0] * channel_count for name, *_rest in plan}
    for name, x, y, *_rest in furniture:
        for channel, rate in enumerate(material_of[name][0]):
            room_air[room_of(x, y)][channel] += rate * settled_seconds
    bounds_of = {name: (min_x, min_y, max_x, max_y, ceiling)
                 for name, min_x, min_y, max_x, max_y, ceiling, _l in plan}
    regions = [
        replace(
            region,
            air=AirVolumeState(
                volume_cubic_mm=(
                    (bounds_of[region.region_id][2] - bounds_of[region.region_id][0])
                    * (bounds_of[region.region_id][3] - bounds_of[region.region_id][1])
                    * bounds_of[region.region_id][4]
                ),
                odorant_mass_nanograms=tuple(room_air[region.region_id]),
            ),
        )
        for region in regions
    ]
    portals = [
        replace(portal, air_flow_cubic_mm_per_second=2_000_000)
        for portal in portals
    ]
    return regions, portals, _shaped(objects)


def _home_thermal_anatomy(
    regions: Iterable[Any], portals: Iterable[Any]
) -> Any:
    """Derive one bounded core/skin/home heat circuit from signed geometry.

    This is Phase-1 virtual anatomy, not a claim about a later manufactured
    body. The child mass is the CDC female 48.5-month median rounded to one
    gram; the two-node capacity uses the published 2.98 kJ/(kg K) whole-body
    specific heat and a declared 90/10 core/skin partition. Air capacity and
    portal conductance derive from each room volume and doorway flow. The only
    authored building value is a finite HVAC boundary conductance at 23 C.
    """

    from dsf_ai_service.substrate.bounded_home_thermal_physics import (
        ConductiveThermalEdge,
        ThermalBathEdge,
        ThermalPowerSource,
    )
    from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
        CoupledThermalAnatomy,
    )

    ordered_regions = tuple(sorted(regions, key=lambda item: item.region_id))
    ordered_portals = tuple(sorted(portals, key=lambda item: item.portal_id))
    if not ordered_regions or any(item.air is None for item in ordered_regions):
        raise ValueError("the thermal home requires finite signed air volumes")
    room_index = {
        region.region_id: index for index, region in enumerate(ordered_regions)
    }
    # 1210.120 J/(m3 K), represented as uJ/(m3 mK).
    air_capacity_per_cubic_meter = 1_210_120
    room_capacities = tuple(
        region.air.volume_cubic_mm * air_capacity_per_cubic_meter
        // 1_000_000_000
        for region in ordered_regions
    )
    # 15.878 kg * 2.98 kJ/(kg K) = 47,316.44 J/K. On the module's
    # uJ/mK lattice that is 47,316,440, split without losing one quantum.
    whole_body_capacity = 15_878 * 2_980
    skin_capacity = whole_body_capacity // 10
    core_capacity = whole_body_capacity - skin_capacity
    skin_index = len(ordered_regions)
    core_index = skin_index + 1
    portal_edges = []
    for portal in ordered_portals:
        flow = portal.air_flow_cubic_mm_per_second
        if flow is None:
            raise ValueError("the thermal home requires signed portal air flow")
        left, right = portal.region_ids
        portal_edges.append(
            ConductiveThermalEdge(
                room_index[left],
                room_index[right],
                flow * air_capacity_per_cubic_meter // 1_000_000,
            )
        )
    metabolic_power = 41_500_000
    return CoupledThermalAnatomy(
        node_ids=(
            *(f"air:{region.region_id}" for region in ordered_regions),
            "body:cutaneous-shell",
            "body:core",
        ),
        initial_temperatures_millikelvin=(
            *(
                (293_150 if region.region_id == "backyard" else 296_150)
                for region in ordered_regions
            ),
            303_150,
            309_950,
        ),
        capacities_microjoules_per_millikelvin=(
            *room_capacities,
            skin_capacity,
            core_capacity,
        ),
        fixed_conductive_edges=(
            *portal_edges,
            ConductiveThermalEdge(core_index, skin_index, 6_102_941),
        ),
        room_air_node_by_region_id=tuple(
            (region.region_id, room_index[region.region_id])
            for region in ordered_regions
        ),
        skin_node_index=skin_index,
        core_node_index=core_index,
        skin_air_conductance_microwatts_per_kelvin=5_928_571,
        # Indoor rooms couple to the authored HVAC boundary; the backyard
        # is outdoors and couples hard to the open sky's own ambient.
        bath_edges=tuple(
            (
                ThermalBathEdge(index, 293_150, 2_500_000_000)
                if region.region_id == "backyard"
                else ThermalBathEdge(index, 296_150, 250_000_000)
            )
            for index, region in enumerate(ordered_regions)
        ),
        power_sources=(ThermalPowerSource(core_index, metabolic_power),),
        parameter_provenance=(
            "CDC female 48.5-month median body mass rounded to 15.878 kilograms",
            "measured whole-body specific heat 2.98 kilojoules per kilogram-kelvin",
            "FAO-WHO-UNU girls age 3-to-10 basal metabolic equation at declared mass",
            "published passive two-node core-skin heat-balance structure",
            "authored Phase-1 virtual-home 296150-millikelvin HVAC boundary",
        ),
    )


def _companion_body_surface_sites() -> tuple[Any, ...]:
    """Declare the bounded skin sites used by exact reciprocal contact.

    These are morphology, not gesture meanings.  Their material coefficients
    are pinned by three explicit substrate-scale reference responses:

    * a fully covered 60 x 80 mm palm compressed by 1 mm carries 9.6 N;
    * the same palm sliding 10 mm over one second carries 0.96 N tangentially;
    * the same palm held across a 1 K difference for one second transfers
      0.48 J.

    The coefficients are therefore derived once from those declarations and
    are never tuned by a lesson, behavior, or observer.  Guala's temperature
    is read from her live cutaneous thermal node; 310.15 K is the participant
    surface's declared finite reservoir boundary until that body gains its own
    thermal circulation.
    """

    if not TOUCH_RECEPTORS_AUTHORIZED:
        return ()
    from dsf_ai_service.substrate.body_surface_contact import (
        BodySurfaceMaterial,
        ExactVector3,
    )
    from dsf_ai_service.substrate.embodiment_world import (
        MountedBodySurfaceSite,
    )

    exact = Fraction
    x = ExactVector3(exact(1), exact(0), exact(0))
    y = ExactVector3(exact(0), exact(1), exact(0))
    z = ExactVector3(exact(0), exact(0), exact(1))
    skin = BodySurfaceMaterial(
        normal_stiffness_millinewtons_per_micrometre_per_square_micrometre=(
            exact(1, 500_000_000)
        ),
        tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre=(
            exact(1, 50_000)
        ),
        thermal_conductance_nanowatts_per_square_micrometre_millikelvin=(
            exact(1, 10_000)
        ),
    )

    def site(
        body_id: str,
        site_id: str,
        centre: tuple[int, int, int],
        normal: Any,
        tangent_u: Any,
        tangent_v: Any,
        half_extents: tuple[int, int],
        cutaneous_topology_index: int | None,
    ) -> Any:
        return MountedBodySurfaceSite(
            body_id=body_id,
            site_id=site_id,
            local_centre_micrometres=ExactVector3(
                *(exact(value) for value in centre)
            ),
            outward_normal=normal,
            tangent_u=tangent_u,
            tangent_v=tangent_v,
            half_extent_u_micrometres=exact(half_extents[0]),
            half_extent_v_micrometres=exact(half_extents[1]),
            material=skin,
            reference_temperature_millikelvin=310_150,
            cutaneous_topology_index=cutaneous_topology_index,
        )

    # The existing 3 x 9 contact sheet is Guala's declared body-surface
    # lattice.  These sparse morphology sites bind seven previously unnamed
    # locations without changing their native topology or receptor law.
    guala = (
        site("guala-body-1", "forehead", (230_000, 0, 1_100_000), x, y, z, (70_000, 55_000), 4),
        site("guala-body-1", "crown", (0, 0, 1_250_000), z, x, y, (75_000, 65_000), 3),
        site("guala-body-1", "left-shoulder", (180_000, 170_000, 900_000), x, y, z, (80_000, 75_000), 9),
        site("guala-body-1", "front-torso", (240_000, 0, 700_000), x, y, z, (150_000, 190_000), 13),
        site("guala-body-1", "right-shoulder", (180_000, -170_000, 900_000), x, y, z, (80_000, 75_000), 17),
        site("guala-body-1", "left-palm", (300_000, 150_000, 500_000), x, y, z, (30_000, 40_000), 18),
        site("guala-body-1", "right-palm", (300_000, -150_000, 500_000), x, y, z, (30_000, 40_000), 26),
    )
    # A facing participant has the opposite heading.  Its local lateral
    # tangents are therefore reversed so the two world-space contact bases
    # become exactly aligned when the surfaces oppose each other.
    participant = (
        site("person-body-1", "left-palm", (300_000, 200_000, 800_000), x, y.scaled(exact(-1)), z, (30_000, 40_000), None),
        site("person-body-1", "right-palm", (300_000, -200_000, 800_000), x, y.scaled(exact(-1)), z, (30_000, 40_000), None),
        site("person-body-1", "front-torso", (250_000, 0, 1_000_000), x, y.scaled(exact(-1)), z, (180_000, 260_000), None),
        site("person-body-1", "perioral", (260_000, 0, 1_450_000), x, y.scaled(exact(-1)), z, (25_000, 20_000), None),
        site("person-body-1", "downward-palm", (250_000, -180_000, 1_050_000), z.scaled(exact(-1)), x.scaled(exact(-1)), y.scaled(exact(-1)), (30_000, 40_000), None),
    )
    return guala + participant


def world_authority_key(identity: str) -> str:
    """Derive the stable authentication key for this organism's one world."""

    if not isinstance(identity, str):
        raise TypeError("organism identity is not text")
    try:
        parsed = uuid.UUID(identity)
    except ValueError as error:
        raise ValueError("organism identity is not canonical UUID text") from error
    if str(parsed) != identity:
        raise ValueError("organism identity is not canonical UUID text")
    return hashlib.sha256(
        f"guala.embodiment.world.v1:{identity}".encode("utf-8")
    ).hexdigest()


def home_world_authority(
    *,
    identity: str,
    encoded_world: bytes | None = None,
    migrate_physical_return: bool = False,
) -> Any:
    """Build the declared home and optionally cold-restore its exact state."""

    from dsf_ai_service.substrate.embodiment_world import (
        BodyReceptorGeometry,
        EmbodiedBody,
        EmbodimentPort,
        PORT_ID,
        SECOND_BODY_PORT_ID,
        PoseMM,
        PositionMM,
        ScreenBroadcast,
        SolarCoupling,
    )
    from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
        ThermallyCoupledEmbodimentWorldAuthority,
    )

    receptors = BodyReceptorGeometry(
        retinal_offset_mm=PositionMM(200, 0, 1_100),
        left_ear_offset_mm=PositionMM(0, 0, 1_050),
        right_ear_offset_mm=PositionMM(0, 180, 1_050),
        touch_offset_mm=PositionMM(200, 0, 150),
        touch_radius_mm=300,
        oral_offset_mm=PositionMM(200, 0, 1_020),
        oral_radius_mm=60,
        olfactory_offset_mm=PositionMM(210, 0, 1_060),
        odorant_saturation_nanograms_per_cubic_meter=(1_000_000,) * 8,
        tastant_saturation_micrograms=(200_000,) * 5,
        touch_mass_span_grams=45_000,
        touch_temperature_min_millikelvin=273_000,
        touch_temperature_max_millikelvin=323_000,
        touch_roughness_span_micrometers=1_000,
    )
    regions, portals, objects = _home_rooms_and_things()
    authority = ThermallyCoupledEmbodimentWorldAuthority(
        authority_key=world_authority_key(identity),
        thermal_anatomy=_home_thermal_anatomy(regions, portals),
        self_body_id="guala-body-1",
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(2_600, 7_600, 0), 0),
                radius_mm=250,
                reach_mm=800,
                receptor_geometry=receptors,
            ),
            EmbodiedBody(
                "person-body-1",
                PoseMM(PositionMM(7_300, 7_500, 0), 180_000),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(SECOND_BODY_PORT_ID, "person-body-1"),
        ),
        regions=regions,
        portals=portals,
        initial_objects=objects,
        contact_optical_surface_sequences=(),
        body_surface_sites=_companion_body_surface_sites(),
        max_regions=12,
        max_portals=16,
        solar_coupling=SolarCoupling(
            outdoor_region_ids=("backyard",),
            window_share_ppm_by_region_id=(
                ("her-room", 250_000),
                ("kitchen", 300_000),
                ("dining", 300_000),
                ("library", 250_000),
                ("tv-room", 200_000),
                ("daddys-room", 250_000),
                ("wcs-room", 150_000),
            ),
        ),
        screen_broadcasts=(
            ScreenBroadcast(
                object_id="television",
                seconds_per_frame=5,
                frames=(
                    (900_000, 800_000, 300_000, 150_000, 100_000, 80_000),
                    (750_000, 850_000, 400_000, 200_000, 120_000, 90_000),
                    (300_000, 600_000, 850_000, 400_000, 180_000, 100_000),
                    (150_000, 300_000, 700_000, 850_000, 300_000, 120_000),
                    (100_000, 150_000, 400_000, 800_000, 700_000, 300_000),
                    (80_000, 100_000, 200_000, 400_000, 850_000, 600_000),
                    (120_000, 200_000, 500_000, 750_000, 400_000, 200_000),
                    (300_000, 700_000, 850_000, 500_000, 250_000, 150_000),
                    (850_000, 850_000, 600_000, 300_000, 180_000, 120_000),
                    (950_000, 700_000, 300_000, 150_000, 100_000, 80_000),
                    (600_000, 400_000, 200_000, 100_000, 80_000, 60_000),
                    (200_000, 300_000, 600_000, 900_000, 500_000, 200_000),
                ),
            ),
        ),
    )
    if encoded_world is None:
        return authority
    if not isinstance(encoded_world, bytes) or not encoded_world:
        raise ValueError("persisted world is not a nonempty byte body")
    # Production restores under the authenticated renovation: when the declared
    # home differs from the lived one (rooms, doors, paint, windows, things),
    # the lived state is carried into the declaration with a receipt; when
    # they agree, nothing happens. An ordinary restore must be byte-exact.
    authority.restore_encoded(
        encoded_world,
        allow_physical_return_migration=migrate_physical_return,
        allow_authenticated_physical_manifest_migration=migrate_physical_return,
    )
    if not migrate_physical_return and bytes(authority.encoded_snapshot()) != encoded_world:
        raise RuntimeError("ordinary home-world restore changed canonical bytes")
    if not any(
        item.object_id == HOME_BOOK_OBJECT_ID
        for item in authority.observation_snapshot().objects
    ):
        raise RuntimeError("the persistent home lost its physical book")
    return authority
