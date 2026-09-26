"""Canonical physical home authority for the lean Guala runtime.

This module is environment anatomy only. It owns no organism, scheduler,
observer, persistence, lesson, action choice, or cognition.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import inspect
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
from dsf_ai_service.substrate.w1_parts import BODY_PARTS, CARETAKER_PARTS  # noqa: E402

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


def _grass_surface(columns: int = 32, rows: int = 32) -> ObjectOpticalSurface:
    """Lawn grass: rich chlorophyll green palette with texture variations."""
    palette = (
        (60_000, 110_000, 360_000, 300_000, 70_000, 50_000),
        (80_000, 140_000, 440_000, 380_000, 90_000, 70_000),
        (100_000, 170_000, 500_000, 420_000, 100_000, 80_000),
        (50_000, 90_000, 280_000, 240_000, 60_000, 40_000),
    )
    cells = []
    for r in range(rows):
        for c in range(columns):
            h = (r * 5 + c * 3 + (r * c)) % 4
            cells.append(h)
    surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
    surface.verify()
    return surface


def _sky_surface(columns: int = 32, rows: int = 32) -> ObjectOpticalSurface:
    """Atmospheric sky ceiling: Rayleigh scattering blue gradient."""
    palette = (
        (60_000, 90_000, 180_000, 320_000, 560_000, 720_000),
        (70_000, 100_000, 200_000, 340_000, 580_000, 740_000),
        (80_000, 120_000, 230_000, 380_000, 620_000, 760_000),
        (90_000, 130_000, 250_000, 400_000, 640_000, 780_000),
    )
    cells = []
    for r in range(rows):
        for c in range(columns):
            idx = min(3, r // 8)
            cells.append(idx)
    surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
    surface.verify()
    return surface


def _fence_surface(columns: int = 32, rows: int = 32) -> ObjectOpticalSurface:
    """Cedar perimeter fence: vertical wooden slats."""
    palette = (
        (260_000, 210_000, 140_000, 100_000, 70_000, 60_000),
        (220_000, 170_000, 110_000, 80_000, 60_000, 50_000),
        (160_000, 120_000, 80_000, 60_000, 40_000, 30_000),
        (280_000, 230_000, 160_000, 110_000, 80_000, 70_000),
    )
    cells = []
    for r in range(rows):
        for c in range(columns):
            if c % 4 == 3:
                cells.append(2)
            elif r % 16 in (2, 14):
                cells.append(3)
            elif (c // 4) % 2 == 0:
                cells.append(0)
            else:
                cells.append(1)
    surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
    surface.verify()
    return surface


_grass_lawn = _grass_surface()
_blue_sky = _sky_surface()
_fence_wood = _fence_surface()


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
    "hallway": (
        SurfaceLookMM("floor", 5_600, 9_000, 5_000, 10_000, _planks_380),
        SurfaceLookMM("floor", 6_800, 7_800, 5_500, 9_500, _living_rug),
    ),
    "backyard": (
        SurfaceLookMM("floor", 0, 20_000, 10_000, 16_000, _grass_lawn),
        SurfaceLookMM("ceiling", 0, 20_000, 10_000, 16_000, _blue_sky),
        SurfaceLookMM("y-max", 0, 20_000, 0, 2_400, _fence_wood),
        SurfaceLookMM("x-min", 10_000, 16_000, 0, 2_400, _fence_wood),
        SurfaceLookMM("x-max", 10_000, 16_000, 0, 2_400, _fence_wood),
    ),
}


# Shapes: what her eye meets. A thing is a sphere unless declared here as a box:
# (extents x, y, z in its own frame, heading about the vertical, height of its bottom
# above the floor).
HOME_SHAPES = {
    # her room
    "bed":              ((1_500,   950,   500),      0,     0),
    "pillow":           ((  350,   250,   120),      0,   350),   # resting on the bed mattress
    "blanket":          ((  380,   380,   150),      0,   350),   # resting on the bed mattress
    "curtains":         ((  480,    40, 2_000),      0,   300),   # a hanging panel by the north window
    "toy-chest":        ((  800,   450,   450),      0,     0),
    "toy-blocks":       ((  160,   160,    80),      0,   450),   # resting in toy chest
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
    "book-peter-rabbit": ((  190,   140,    40),      0,     0),
    "book-wind-willows": ((  190,   140,    40),      0,     0),
    "book-aesops-fables": (( 190,   140,    40),      0,     0),
    "book-mother-goose": ((  190,   140,    40),      0,     0),
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
    "garden-ladder":    ((  450,   400,   550),      0,     0),
    "tv-remote":        ((  140,    50,    20),      0,     0),
    "bottle-milk":      ((   80,    80,   160),      0,     0),
    "bread-slice":      ((  100,    80,    25),      0,     0),
    "stroller-carriage": ((  850,   550,   750),      0,     0),
    "garden-flowers":   ((  160,   160,   200),      0,     0),
    "garden-butterfly": ((   80,    80,    20),      0,     0),
    "garden-bird":      ((  120,    80,    90),      0,     0),
    "walkway-bench":    ((1_200,   450,   450),      0,     0),
    "walkway-lantern":  ((  300,   300,   400),      0, 1_200),
}

# Boxes wear their paint flat (a sofa, a table, a tub: one material, its faces told
# apart by the light) except the things whose declared pattern is the point of them.
PATTERNED_BOXES = ("wall-art-shapes", "wall-art-weather", "television", "book", "daddys-book", "book-peter-rabbit", "book-wind-willows", "book-aesops-fables", "book-mother-goose")


# Things built of parts:
def _P(kind, x, y, z, a, b=None, c=None, paint=None):
    from dsf_ai_service.substrate.embodiment_world import ObjectPart
    b = a if b is None else b
    c = (a if kind == "sphere" else b) if c is None else c
    return ObjectPart(kind, (x, y, z), (a, b, c), tuple(paint) if paint else ())


_DARK = (80_000,) * 6
_WOOD = (320_000, 260_000, 180_000, 120_000, 90_000, 80_000)
_STEM = (140_000, 160_000, 90_000, 60_000, 50_000, 40_000)
_FOLIAGE_OAK = (80_000, 130_000, 420_000, 360_000, 90_000, 70_000)
_FOLIAGE_PINE = (60_000, 100_000, 320_000, 260_000, 70_000, 50_000)
_FOLIAGE_APPLE = (90_000, 160_000, 440_000, 340_000, 100_000, 80_000)
_APPLE_RED = (850_000, 120_000, 90_000, 70_000, 60_000, 50_000)


def _chair(seat=360, height=850, leg=40):
    half = seat // 2 - leg
    return (_P("box", 0, 0, 430, seat, seat, 40), _P("box", 0, -(seat // 2 - 20), 640, seat, 40, 420),
            *(_P("cylinder", sx, sy, 205, leg, leg, 410) for sx in (-half, half) for sy in (-half, half)))


def _table(width, depth, height=750, leg=50):
    hx, hy = width // 2 - leg, depth // 2 - leg
    return (_P("box", 0, 0, height - 20, width, depth, 40),
            *(_P("cylinder", sx, sy, (height - 40) // 2, leg, leg, height - 40, _WOOD) for sx in (-hx, hx) for sy in (-hy, hy)))


def _high_chair():
    return (
        _P("box", 0, 0, 650, 360, 360, 40),
        _P("box", 0, -160, 800, 360, 40, 300),
        _P("box", 0, 180, 700, 420, 200, 30, _WOOD),
        *(_P("cylinder", sx, sy, 325, 30, 30, 650, _WOOD) for sx in (-150, 150) for sy in (-150, 150)),
    )


def _playpen():
    return (
        _P("box", 0, 0, 20, 600, 600, 20),
        _P("box", 0, -290, 250, 600, 20, 460, _WOOD),
        _P("box", 0, 290, 250, 600, 20, 460, _WOOD),
        _P("box", -290, 0, 250, 20, 600, 460, _WOOD),
        _P("box", 290, 0, 250, 20, 600, 460, _WOOD),
    )


def _stacking_rings():
    _RED_RING = (900_000, 200_000, 150_000, 120_000, 100_000, 80_000)
    _AMBER_RING = (950_000, 800_000, 200_000, 120_000, 100_000, 80_000)
    _BLUE_RING = (100_000, 250_000, 500_000, 750_000, 850_000, 900_000)
    return (
        _P("cylinder", 0, 0, 15, 240, 240, 30, _WOOD),
        _P("cylinder", 0, 0, 120, 35, 35, 210, _WOOD),
        _P("cylinder", 0, 0, 50, 200, 200, 40, _RED_RING),
        _P("cylinder", 0, 0, 90, 150, 150, 40, _AMBER_RING),
        _P("cylinder", 0, 0, 130, 100, 100, 40, _BLUE_RING),
    )


def _play_ball():
    _BALL_YELLOW = (960_000, 900_000, 150_000, 100_000, 80_000, 60_000)
    return (
        _P("sphere", 0, 0, 90, 180, paint=_BALL_YELLOW),
    )


def _toy_blocks():
    # Set of 4 alphabet & number blocks arranged in a neat 2x2 cluster
    # Natural wood painted with child-safe primary and pastel finishes
    _BLOCK_RED = (900_000, 200_000, 150_000, 120_000, 100_000, 80_000)
    _BLOCK_BLUE = (100_000, 250_000, 500_000, 750_000, 850_000, 900_000)
    _BLOCK_YELLOW = (950_000, 850_000, 150_000, 100_000, 80_000, 60_000)
    _BLOCK_GREEN = (150_000, 750_000, 250_000, 150_000, 100_000, 80_000)
    return (
        _P("box", -40, -40, 40, 75, 75, 75, _BLOCK_RED),
        _P("box",  40, -40, 40, 75, 75, 75, _BLOCK_BLUE),
        _P("box", -40,  40, 40, 75, 75, 75, _BLOCK_YELLOW),
        _P("box",  40,  40, 40, 75, 75, 75, _BLOCK_GREEN),
    )



HOME_PARTS = {
    "high-chair": _high_chair(),
    "playpen": _playpen(),
    "stacking-rings": _stacking_rings(),
    "toy-blocks": _toy_blocks(),
    "play-ball": _play_ball(),
    "toy-bear": (_P("sphere", 0, 0, 150, 300), _P("sphere", 0, 0, 380, 220), _P("sphere", -80, 0, 470, 90), _P("sphere", 80, 0, 470, 90),
                 _P("sphere", 0, -95, 390, 60, paint=_DARK),                                                    # the muzzle
                 *(_P("cylinder", sx, sy, 75, 70, 70, 150) for sx in (-110, 110) for sy in (-60, 60))),
    "apple":    (_P("sphere", 0, 0, 90, 180), _P("cylinder", 0, 0, 195, 12, 12, 30, _STEM)),
    "cup":      (_P("cylinder", 0, 0, 55, 100, 100, 110), _P("box", 65, 0, 60, 20, 30, 60)),                    # a handle
    "bowl":     (_P("cylinder", 0, 0, 45, 280, 280, 90),),
    "pot":      (_P("cylinder", 0, 0, 80, 240, 240, 160), _P("box", 110, 0, 120, 40, 30, 20, _DARK), _P("box", -110, 0, 120, 40, 30, 20, _DARK)),
    "pan":      (_P("cylinder", 0, 0, 25, 200, 200, 50), _P("box", 105, 0, 30, 30, 24, 20, _DARK)),
    "desk-chair": _chair(), "dining-chair": _chair(), "dining-chair-south": _chair(), "daddys-chair": _chair(),
    "desk": _table(1_200, 600), "dining-table": _table(1_200, 700), "table": _table(840, 840), "daddys-desk": _table(560, 560),
    "bed":      (_P("box", 0, 0, 350, 1_500, 950, 300), _P("box", -730, 0, 500, 40, 950, 600, _WOOD),           # mattress, headboard
                 *(_P("cylinder", sx, sy, 100, 60, 60, 200, _WOOD) for sx in (-700, 700) for sy in (-420, 420))),
    "sofa":     (_P("box", 0, 0, 250, 1_700, 800, 500), _P("box", 0, -300, 650, 1_700, 200, 300),
                 _P("box", -800, 0, 350, 100, 800, 700), _P("box", 800, 0, 350, 100, 800, 700)),
    "daddys-armchair": (_P("box", 0, 0, 250, 630, 630, 500), _P("box", 0, -240, 600, 630, 150, 300),
                        _P("box", -270, 0, 350, 90, 630, 700), _P("box", 270, 0, 350, 90, 630, 700)),
    "television": (_P("box", 0, 0, 550, 1_000, 60, 600, _DARK), _P("box", 0, 0, 125, 400, 400, 250, _WOOD)),   # screen on a stand
    "shelf-a":  (_P("box", -330, 0, 900, 40, 300, 1_800), _P("box", 330, 0, 900, 40, 300, 1_800),
                 *(_P("box", 0, 0, z, 700, 300, 30) for z in (300, 750, 1_200, 1_650))),
    "shelf-b":  (_P("box", -330, 0, 900, 40, 300, 1_800), _P("box", 330, 0, 900, 40, 300, 1_800),
                 *(_P("box", 0, 0, z, 700, 300, 30) for z in (300, 750, 1_200, 1_650))),
    "refrigerator": (_P("box", 0, 0, 900, 630, 630, 1_800), _P("box", 0, -330, 1_000, 30, 30, 500, _DARK)),   # a handle
    "stove":    (_P("box", 0, 0, 450, 560, 560, 900), *(_P("cylinder", sx, sy, 905, 160, 160, 10, _DARK) for sx in (-140, 140) for sy in (-140, 140))),
    "kitchen-counter": (_P("box", 0, 0, 450, 700, 700, 900),),
    "pantry":   (_P("box", 0, 0, 900, 490, 490, 1_800), _P("box", 0, -250, 1_000, 20, 20, 300, _DARK)),
    "bath-tub": (_P("box", 0, 0, 275, 1_000, 600, 550), _P("box", 0, 0, 560, 800, 400, 20, _DARK)),          # the water's dark top
    "wash-basin": (_P("cylinder", 0, 0, 350, 120, 120, 700), _P("cylinder", 0, 0, 800, 420, 420, 100)),
    "tree-oak": (_P("cylinder", 0, 0, 900, 240, 240, 1_800, _WOOD), _P("sphere", 0, 0, 2_400, 1_200, paint=_FOLIAGE_OAK)),
    "tree-pine": (_P("cylinder", 0, 0, 800, 200, 200, 1_600, _WOOD), _P("sphere", 0, 0, 2_000, 900, paint=_FOLIAGE_PINE), _P("sphere", 0, 0, 2_700, 600, paint=_FOLIAGE_PINE)),
    "tree-apple": (_P("cylinder", 0, 0, 700, 200, 200, 1_400, _WOOD), _P("sphere", 0, 0, 1_800, 1_000, paint=_FOLIAGE_APPLE),
                   _P("sphere", -200, -150, 1_500, 120, paint=_APPLE_RED), _P("sphere", 180, -100, 1_600, 120, paint=_APPLE_RED),
                   _P("sphere", 50, 200, 1_450, 120, paint=_APPLE_RED)),
    "garden-apple": (_P("sphere", 0, 0, 90, 180, paint=_APPLE_RED), _P("cylinder", 0, 0, 195, 12, 12, 30, _STEM)),
    "garden-ladder": (_P("cylinder", -180, 0, 275, 35, 35, 550, _WOOD), _P("cylinder", 180, 0, 275, 35, 35, 550, _WOOD),
                      _P("box", 0, 0, 180, 360, 60, 25, _WOOD), _P("box", 0, 0, 360, 360, 60, 25, _WOOD),
                      _P("box", 0, 0, 535, 420, 200, 30, _WOOD)),
    "swing":    (_P("cylinder", -450, 0, 1_000, 80, 80, 2_000, _WOOD), _P("cylinder", 450, 0, 1_000, 80, 80, 2_000, _WOOD),
                 _P("box", 0, 0, 1_990, 980, 80, 60, _WOOD), _P("box", 0, 0, 450, 400, 200, 40)),
    "slide":    (_P("box", 0, 0, 750, 1_200, 600, 1_500), _P("box", -700, 0, 700, 200, 400, 1_400, _WOOD)),
    "radio":    (_P("box", 0, 0, 75, 200, 120, 150), _P("cylinder", 60, 0, 170, 8, 8, 40, _DARK)),         # an aerial
    "lamp":     (_P("cylinder", 0, 0, 10, 180, 180, 20, _DARK), _P("cylinder", 0, 0, 650, 30, 30, 1_260, _DARK)),   # the floor lamp's base and stand; its shade is the sphere
}

HOME_LAMP_HEIGHTS = {
    "kitchen-lamp": 1_500,     # a pendant over the counter
    "dining-lamp":  1_600,     # a pendant by the table
    "daddys-lamp":    750,     # the reading lamp on the desk
    "bath-lamp":    1_400,     # the vanity light
    "lamp":         1_300,     # the library's floor lamp
    "glow-stars":   2_300,     # on the ceiling above her bed
}

HOME_DEPARTED = ("art-arch", "art-circle", "berries", "bread", "carrot", "cheese", "kitchen-cabinet", "milk", "plate")

# Her room's nightlight.
NIGHT_LIGHT = ("night-light",   300, 8_000, 80, 300, 250, (900_000,) * 6, (300_000,) * 6)


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
    # Parts replace a box shape where declared. Patterned things (like television) keep their optical surface.
    shaped = [
        replace(item, shape="parts", size_mm=(), parts=tuple(HOME_PARTS[item.object_id]),
                optical_surface=item.optical_surface if item.object_id in PATTERNED_BOXES else None)
        if item.object_id in HOME_PARTS and item.object_id not in HOME_LAMP_HEIGHTS else item
        for item in shaped
    ]
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
            elif "butterfly" in name:
                dc = abs(c - 16)
                dr = abs(r - 16)
                if dc <= 2:
                    val = 0
                elif dr + dc <= 14:
                    val = 3 if (r + c) % 3 == 0 else 2
                else:
                    val = 1
            elif "bird" in name:
                d_head = (r - 12) ** 2 + (c - 16) ** 2
                d_body = (r - 20) ** 2 + (c - 16) ** 2
                if r == 10 and c in (15, 17):
                    val = 0
                elif r == 12 and c == 16:
                    val = 3
                elif d_head <= 25:
                    val = 2
                elif d_body <= 49:
                    val = 1
                else:
                    val = 0
            elif "flower" in name:
                d = (r - 16) ** 2 + (c - 16) ** 2
                if d <= 16:
                    val = 3
                elif d <= 100 and (abs(r - 16) * abs(c - 16)) % 4 != 0:
                    val = 2
                else:
                    val = 1
            elif "lantern" in name:
                d = (r - 16) ** 2 + (c - 16) ** 2
                if r < 3 or r >= rows - 3 or c < 3 or c >= cols - 3:
                    val = 0  # dark bronze frame
                elif d <= 25:
                    val = 3  # glowing central light
                elif d <= 100:
                    val = 2  # amber glass pane
                else:
                    val = 1
            elif "ladder" in name:
                if c in (4, 5, cols - 6, cols - 5):
                    val = 0
                elif r in (8, 16, 24):
                    val = 1
                elif r < 6:
                    val = 3
                else:
                    val = 2
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
            elif "mailbox" in name:
                if r < 2 or r >= rows - 2 or c < 2 or c >= cols - 2:
                    val = 0
                elif 14 <= r <= 18 and 13 <= c <= 18:
                    val = 1
                else:
                    val = 2 if (r // 3) % 2 == 0 else 3
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
    plan = (
        ("kitchen",       0,      0,  7_000,  5_000, HOME_CEILING_MM, 55_000),
        ("dining",        7_000,  0, 12_000,  5_000, HOME_CEILING_MM, 45_000),
        ("daddys-room",  12_000,  0, 16_000,  5_000, HOME_CEILING_MM, 45_000),
        ("wcs-room",     16_000,  0, 20_000,  5_000, HOME_CEILING_MM, 45_000),
        ("her-room",      0,  5_000,  5_600, 10_000, HOME_CEILING_MM, 45_000),
        ("hallway",       5_600, 5_000, 9_000, 10_000, HOME_CEILING_MM, 240_000),
        ("library",       9_000, 5_000, 14_000, 10_000, HOME_CEILING_MM, 45_000),
        ("tv-room",      14_000, 5_000, 20_000, 10_000, HOME_CEILING_MM, 45_000),
        ("backyard",      0, 10_000, 20_000, 16_000, BACKYARD_SKY_MM, 280_000),
    )
    regions = [
        PhysicalRegion(
            region_id=name,
            bounds=RoomBoundsMM(
                minimum=PositionMM(min_x, min_y, 0),
                maximum=PositionMM(max_x, max_y, ceiling),
            ),
            ceiling_height_mm=ceiling,
            reflectance_ppm=(
                (70_000, 100_000, 200_000, 340_000, 580_000, 740_000)
                if name == "backyard"
                else (380_000,) * 6
            ),
            illumination_ppm=(light,) * 6,
            windows=HOME_WINDOWS.get(name, ()),
            looks=HOME_LOOKS.get(name, ()),
        )
        for name, min_x, min_y, max_x, max_y, ceiling, light in plan
    ]
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
    # Exactly 59 items total: guarantees 4 slots of headroom below 64 ceiling.
    furniture = (
        # --- 1. KITCHEN (12 items) ---
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
        ("high-chair",       3_500,  1_500, 350,  8_000, (820_000, 780_000, 700_000, 620_000, 560_000, 520_000)),
        ("bread-slice",      4_800,  3_800,  60,     60, (750_000, 550_000, 350_000, 220_000, 150_000, 100_000)),

        # --- 2. DINING ROOM (5 items) ---
        ("dining-table",       9_500, 2_500, 700, 35_000, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("dining-chair",       9_500, 3_600, 260,  6_000, (50_000,   50_000,  50_000,  50_000,  50_000,  50_000)),
        ("sideboard",         11_300, 4_200, 450, 38_000, (220_000, 180_000, 150_000, 130_000, 120_000, 110_000)),
        ("dining-lamp",       11_400,   800, 220,  4_000, (900_000, 850_000, 750_000, 600_000, 500_000, 450_000)),
        ("bottle-milk",       8_000,  3_500,  50,    250, (920_000, 920_000, 920_000, 900_000, 880_000, 850_000)),

        # --- 3. DADDY'S ROOM (5 items) ---
        ("daddys-desk",       13_800, 4_300, 400, 36_000, (160_000, 120_000, 100_000,  80_000,  70_000,  60_000)),
        ("daddys-chair",      13_800, 3_400, 260,  8_000, (80_000,   60_000,  50_000,  50_000,  50_000,  50_000)),
        ("daddys-book",       14_600, 4_300, 120,    900, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000)),
        ("daddys-lamp",       15_300, 3_500, 160,  2_500, (880_000, 850_000, 780_000, 700_000, 650_000, 620_000)),
        ("daddys-armchair",   13_000, 1_000, 450, 22_000, (120_000,  90_000,  80_000,  70_000,  60_000,  50_000)),

        # --- 4. WC'S ROOM (5 items) ---
        ("bath-tub",          18_600, 4_100, 600, 55_000, (950_000, 950_000, 950_000, 950_000, 950_000, 950_000)),
        ("wash-basin",        17_000, 4_400, 300, 22_000, (920_000, 920_000, 920_000, 920_000, 920_000, 920_000)),
        ("bath-lamp",         17_000, 3_200, 150,  1_800, (850_000, 800_000, 700_000, 550_000, 450_000, 400_000)),
        ("bath-towel",        17_000, 3_700, 200,    800, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("bath-mat",          18_600, 3_000, 350,  1_500, (80_000,   80_000,  80_000,  80_000,  80_000,  80_000)),

        # --- 5. HER ROOM (15 items) ---
        ("bed",                  900, 9_100, 900, 40_000, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000)),
        ("pillow",               900, 9_100, 260,  1_200, (920_000, 920_000, 920_000, 920_000, 920_000, 920_000)),
        ("blanket",              900, 8_500, 300,    900, (120_000, 120_000, 120_000, 120_000, 120_000, 120_000)),
        ("toy-bear",           4_800, 9_200, 180,    400, (480_000, 340_000, 260_000, 220_000, 200_000, 180_000)),
        ("toy-chest",          1_000, 5_600, 500,  8_000, (450_000, 350_000, 280_000, 240_000, 220_000, 200_000)),
        ("desk",               4_900, 5_700, 700, 32_000, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("desk-chair",         3_800, 5_700, 320,  6_000, (50_000,   50_000,  50_000,  50_000,  50_000,  50_000)),
        ("curtains",           2_800, 9_750, 250, 15_000, (920_000, 880_000, 820_000, 780_000, 740_000, 700_000)),
        ("wall-art-shapes",      320, 6_500, 310, 10_000, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("wall-art-weather",     320, 7_500, 310, 10_000, (880_000, 880_000, 880_000, 880_000, 880_000, 880_000)),
        ("glow-stars",         2_200, 9_700, 120,    300, (940_000, 930_000, 700_000, 400_000, 300_000, 260_000)),
        ("playpen",            4_200, 8_800, 450, 15_000, (840_000, 800_000, 720_000, 640_000, 580_000, 540_000)),
        ("stacking-rings",       750, 5_600, 140,    600, (920_000, 300_000, 150_000, 650_000, 800_000, 850_000)),
        ("toy-blocks",         1_020, 5_600, 120,    480, (880_000, 820_000, 400_000, 250_000, 200_000, 180_000)),
        ("play-ball",          1_250, 5_600,  90,    200, (950_000, 920_000, 200_000, 120_000, 100_000,  80_000)),

        # --- 6. LIBRARY (4 items) ---
        ("shelf-a",           10_000, 9_500, 400, 30_000, (180_000, 180_000, 180_000, 180_000, 180_000, 180_000)),
        ("shelf-b",           12_500, 9_500, 400, 30_000, (180_000, 180_000, 180_000, 180_000, 180_000, 180_000)),
        ("book",              12_000, 7_500, 140,    900, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000)),
        ("lamp",              13_500, 5_400, 180,  2_200, (880_000, 850_000, 780_000, 700_000, 650_000, 620_000)),

        # --- 7. TV ROOM (4 items) ---
        ("television",        17_000, 9_200, 700, 12_000, (50_000,   50_000,  50_000,  50_000,  50_000,  50_000)),
        ("radio",             15_400, 9_400, 150,  1_200, (180_000, 180_000, 180_000, 180_000, 180_000, 180_000)),
        ("sofa",              17_000, 6_800, 950, 45_000, (80_000,   80_000,  80_000,  80_000,  80_000,  80_000)),
        ("rug",               15_000, 6_000, 600,  5_000, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000)),
        ("tv-remote",         15_600, 7_600,  50,    120, ( 60_000,  60_000,  60_000,  60_000,  60_000,  60_000)),

        # --- 9. HALLWAY (1 item) ---
        ("mailbox",            8_200,  9_200, 220, 12_000, (220_000, 180_000, 150_000, 130_000, 120_000, 110_000)),
        ("stroller-carriage",  6_500,  6_000, 350,  8_500, (140_000, 180_000, 320_000, 260_000, 180_000, 140_000)),

        # --- 8. BACKYARD (9 items: slide, swing, sandbox, garden-patch, oak, pine, apple tree, hanging apple, ladder) ---
        ("slide",              3_000, 13_500,   900,  25_000, (700_000, 720_000, 740_000, 700_000, 650_000, 600_000)),
        ("swing",              7_000, 14_000,   700,  15_000, (480_000, 430_000, 380_000, 340_000, 320_000, 300_000)),
        ("sandbox",           11_500, 13_500, 1_100,  60_000, (820_000, 780_000, 700_000, 620_000, 560_000, 520_000)),
        ("garden-patch",      16_500, 13_500, 1_200,  80_000, (300_000, 380_000, 300_000, 260_000, 240_000, 220_000)),
        ("tree-oak",           1_500, 14_500,   600, 120_000, ( 80_000, 130_000, 420_000, 360_000,  90_000,  70_000)),
        ("tree-pine",         19_000, 14_500,   600, 110_000, ( 60_000, 100_000, 320_000, 260_000,  70_000,  50_000)),
        ("tree-apple",        14_000, 14_800,   500, 100_000, ( 80_000, 160_000, 380_000, 300_000, 100_000,  80_000)),
        ("garden-apple",      14_000, 14_100,    90,     180, (850_000, 120_000,  90_000,  70_000,  60_000,  50_000)),
        ("garden-ladder",     14_000, 11_800,   250,   4_000, (320_000, 260_000, 180_000, 120_000,  90_000,  80_000)),
    )
    digestible_mass_of = {
        "apple": 140_000,
        "garden-apple": 140_000,
        "bread-slice": 50_000,
        "bottle-milk": 20_000,
        "bowl": 30_000,
    }
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
        "high-chair":        ((0, 0, 0, 400, 200, 0, 0, 50),   (0, 0, 0, 1_200, 0),        294_000, 120_000, 30, 20_000),
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
        "playpen":            ((0, 0, 0, 500, 300, 0, 0, 0),   (0, 0, 0, 1_200, 0),        294_000, 180_000, 35, 20_000),
        "stacking-rings":     ((0, 0, 0, 0, 100, 0, 0, 0),     (0, 0, 0, 500, 0),          294_000, 250_000, 15, 10_000),
        "toy-blocks":         ((0, 0, 0, 800, 100, 0, 0, 0),   (0, 0, 0, 800, 0),          294_000, 200_000, 20, 12_000),
        "play-ball":          ((0, 0, 0, 0, 50, 0, 80, 0),      (0, 0, 0, 300, 0),          294_000, 850_000, 10, 5_000),

        # Library
        "shelf-a":            ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "shelf-b":            ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "book":               ((0, 0, 0, 40, 30, 900, 0, 0),   (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "book-peter-rabbit":  ((0, 0, 0, 40, 30, 900, 0, 0),   (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "book-wind-willows":  ((0, 0, 0, 40, 30, 900, 0, 0),   (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "book-aesops-fables": ((0, 0, 0, 40, 30, 900, 0, 0),   (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "book-mother-goose":  ((0, 0, 0, 40, 30, 900, 0, 0),   (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "lamp":               ((0, 0, 0, 0, 20, 0, 260, 0),    (0, 0, 0, 400, 0),          310_000, 20_000, 10, 2_000),

        # TV Room
        "television":         ((0, 0, 0, 0, 40, 0, 700, 0),    (0, 0, 0, 400, 0),          306_000, 20_000, 5, 1_000),
        "radio":              ((0, 0, 0, 0, 40, 0, 300, 0),    (0, 0, 0, 400, 0),          296_000, 20_000, 8, 1_000),
        "sofa":               ((0, 0, 0, 120, 1_500, 0, 0, 90), (0, 300, 0, 800, 0),       294_000, 700_000, 400, 52_000),
        "rug":                ((0, 0, 0, 0, 2_200, 0, 0, 40),  (0, 300, 0, 900, 0),        294_000, 500_000, 800, 46_000),

        # Hallway
        "mailbox":            ((0, 0, 0, 600, 50, 800, 0, 0),  (0, 0, 0, 1_000, 0),        294_000, 30_000, 40, 10_000),

        # Backyard
        "slide":              ((0, 0, 0, 0, 30, 0, 80, 0),     (0, 0, 0, 300, 0),          288_000, 15_000, 8, 10_000),
        "swing":              ((0, 0, 0, 300, 400, 0, 0, 0),   (0, 200, 0, 900, 0),        288_000, 250_000, 300, 30_000),
        "sandbox":            ((0, 0, 0, 100, 600, 0, 0, 0),   (0, 100, 0, 400, 0),        290_000, 40_000, 900, 25_000),
        "garden-patch":       ((0, 0, 0, 1_600, 300, 0, 0, 0), (0, 100, 200, 700, 100),    289_000, 450_000, 700, 320_000),
        "tree-oak":           ((0, 0, 0, 2_500, 0, 0, 0, 0),    (0, 0, 0, 2_000, 0),        288_000, 30_000, 800, 150_000),
        "tree-pine":          ((0, 0, 0, 3_200, 0, 0, 0, 0),    (0, 0, 0, 2_000, 0),        288_000, 30_000, 600, 120_000),
        "tree-apple":         ((0, 0, 0, 2_200, 0, 0, 0, 0),    (0, 0, 0, 1_800, 0),        288_000, 30_000, 700, 140_000),
        "garden-apple":       ((4_200, 0, 0, 0, 0, 0, 0, 0),   (140_000, 200, 26_000, 900, 300), 292_000, 120_000, 15, 850_000),
        "garden-ladder":      ((0, 0, 0, 800, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 15_000),
        "bread-slice":        ((1_200, 100, 100, 0, 0, 0, 0, 800), (200, 800, 100, 0, 500), 294_000, 350_000, 40, 400_000),
        "bottle-milk":        ((0, 200, 500, 0, 0, 0, 0, 100), (0, 0, 200, 0, 3_000), 288_000, 80_000, 10, 850_000),
        "tv-remote":          ((0, 0, 0, 0, 50, 0, 250, 0),    (0, 0, 0, 200, 0),          294_000, 60_000, 120, 2_000),
        "stroller-carriage":  ((0, 0, 0, 0, 0, 0, 0, 50),     (0, 0, 0, 300, 0),          294_000, 150_000, 25, 25_000),
        "garden-flowers":     ((0, 0, 0, 100, 150, 0, 0, 0),    (0, 0, 0, 1_500, 0),        291_000, 180_000, 30, 200_000),
        "garden-butterfly":   ((0, 0, 0, 0, 10, 0, 0, 0),       (0, 0, 0, 100, 0),          294_000, 50_000, 10, 5_000),
        "garden-bird":        ((0, 0, 0, 0, 300, 0, 0, 0),      (0, 0, 0, 600, 0),          312_000, 600_000, 150, 40_000),
        "walkway-bench":      ((0, 0, 0, 800, 50, 0, 0, 0),     (0, 0, 0, 1_500, 0),        294_000, 40_000, 60, 15_000),
        "walkway-lantern":    ((0, 0, 0, 0, 20, 0, 260, 0),     (0, 0, 0, 400, 0),          315_000, 20_000, 10, 2_000),
    }
    reservoir_seconds = 864_000
    emission_of = {
        "lamp":            (900_000, 850_000, 750_000, 600_000, 500_000, 450_000),
        "glow-stars":      (120_000, 120_000, 100_000, 50_000, 20_000, 10_000),
        "daddys-lamp":     (900_000, 850_000, 750_000, 600_000, 500_000, 450_000),
        "dining-lamp":     (900_000, 850_000, 750_000, 600_000, 500_000, 450_000),
        "kitchen-lamp":    (900_000, 850_000, 750_000, 600_000, 500_000, 450_000),
        "bath-lamp":       (850_000, 800_000, 700_000, 550_000, 450_000, 400_000),
        "walkway-lantern": (800_000, 750_000, 650_000, 500_000, 400_000, 350_000),
    }
    shapes_of = {
        "desk": ("box", (1_200, 600, 750), 0, 0),
        "wall-art-shapes": ("box", (50, 600, 760), 0, 1_300),
        "wall-art-weather": ("box", (50, 600, 760), 0, 1_300),
        "curtains": ("sphere", (), 0, 1_200),
        "pillow": ("sphere", (), 0, 350),
        "blanket": ("sphere", (), 0, 350),
        "mailbox": ("box", (200, 300, 450), 0, 800),
        "garden-ladder": ("box", (450, 400, 550), 0, 0),
        "garden-apple": ("sphere", (), 0, 850),
        "tv-remote": ("box", (140, 50, 20), 0, 0),
        "bottle-milk": ("box", (80, 80, 160), 0, 0),
        "bread-slice": ("box", (100, 80, 25), 0, 0),
        "stroller-carriage": ("box", (850, 550, 750), 0, 0),
        "book-peter-rabbit": ("box", (190, 140, 40), 0, 450),
        "book-wind-willows": ("box", (190, 140, 40), 0, 450),
        "book-aesops-fables": ("box", (190, 140, 40), 0, 450),
        "book-mother-goose": ("box", (190, 140, 40), 0, 450),
        "garden-flowers": ("sphere", (), 0, 100),
        "garden-butterfly": ("sphere", (), 0, 450),
        "garden-bird": ("sphere", (), 0, 1_800),
        "walkway-bench": ("box", (1_200, 450, 450), 0, 0),
        "walkway-lantern": ("sphere", (), 0, 1_200),
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
                digestible_mass_micrograms=digestible_mass_of.get(name, 0),
            ),
            shape=shapes_of[name][0] if name in shapes_of else "sphere",
            size_mm=shapes_of[name][1] if name in shapes_of else (),
            heading_millidegrees=shapes_of[name][2] if name in shapes_of else 0,
            elevation_mm=shapes_of[name][3] if name in shapes_of else 0,
        )
        for name, x, y, radius, mass, reflectance in furniture
    ]

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
    """Derive one bounded core/skin/home heat circuit from signed geometry."""
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
    air_capacity_per_cubic_meter = 1_210_120
    room_capacities = tuple(
        region.air.volume_cubic_mm * air_capacity_per_cubic_meter
        // 1_000_000_000
        for region in ordered_regions
    )
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
    """Declare the bounded skin sites used by exact reciprocal contact."""
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

    guala = (
        site("guala-body-1", "forehead", (230_000, 0, 1_100_000), x, y, z, (70_000, 55_000), 4),
        site("guala-body-1", "crown", (0, 0, 1_250_000), z, x, y, (75_000, 65_000), 3),
        site("guala-body-1", "left-shoulder", (180_000, 170_000, 900_000), x, y, z, (80_000, 75_000), 9),
        site("guala-body-1", "front-torso", (240_000, 0, 700_000), x, y, z, (150_000, 190_000), 13),
        site("guala-body-1", "right-shoulder", (180_000, -170_000, 900_000), x, y, z, (80_000, 75_000), 17),
        site("guala-body-1", "left-palm", (300_000, 150_000, 500_000), x, y, z, (30_000, 40_000), 18),
        site("guala-body-1", "right-palm", (300_000, -150_000, 500_000), x, y, z, (30_000, 40_000), 26),
    )
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
    tv_broadcast: Any = None,
    expand_garden: bool = False,
    expand_walkway: bool = False,
    expand_library: bool = False,
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
        departed_object_ids=HOME_DEPARTED,
    )

    if tv_broadcast is None:
        from dsf_ai_service.dynamic_television_broadcast import TelevisionBroadcast
        tv_broadcast = TelevisionBroadcast()
    authority.television_broadcast = tv_broadcast

    # Attach spatial horizon streaming methods and bound sensory aperture to <= 64 objects
    _orig_obs = authority.observation_snapshot
    authority.canonical_observation_snapshot = _orig_obs
    def _horizon_aware_obs(body_id="guala-body-1", max_objects=64, strict_occlusion=False):
        max_objects = min(max(int(max_objects), 1), 64)
        if len(authority._state.world.objects) > 64:
            return compute_spatial_horizon_observation(authority, body_id=body_id, max_objects=max_objects, strict_occlusion=strict_occlusion)
        return _orig_obs()
    authority.observation_snapshot = _horizon_aware_obs
    authority.spatial_horizon_snapshot = lambda body_id="guala-body-1", max_objects=64, strict_occlusion=False: compute_spatial_horizon_observation(
        authority, body_id=body_id, max_objects=min(max(int(max_objects), 1), 64), strict_occlusion=strict_occlusion
    )
    authority.global_objects = lambda: authority._state.world.objects
    if expand_garden:
        expand_garden_fauna_and_flora(authority)
    if expand_walkway:
        expand_exterior_walkway(authority)

    if encoded_world is None:
        if expand_library:
            expand_library_books(authority)
        return authority
    if not isinstance(encoded_world, bytes) or not encoded_world:
        raise ValueError("persisted world is not a nonempty byte body")
    authority.restore_encoded(
        encoded_world,
        allow_physical_return_migration=migrate_physical_return,
        allow_authenticated_physical_manifest_migration=migrate_physical_return,
    )
    if not migrate_physical_return and bytes(authority.encoded_snapshot()) != encoded_world:
        raise RuntimeError("ordinary home-world restore changed canonical bytes")
    if not any(
        item.object_id == HOME_BOOK_OBJECT_ID
        for item in authority.global_objects()
    ):
        raise RuntimeError("the persistent home lost its physical book")
    cur_w = authority._state.world
    held_by_body = {
        obj.held_by_body_id: obj.object_id
        for obj in cur_w.objects
        if obj.held_by_body_id is not None
    }
    def _body_needs_reconciliation(b):
        if b.held_object_id != held_by_body.get(b.body_id):
            return True
        if b.active_contact is not None:
            target_obj = next((o for o in cur_w.objects if o.object_id == b.active_contact.object_id), None)
            if target_obj is None:
                return True
            if b.active_contact.kind == "oral" and not (
                (b.held_object_id == target_obj.object_id and target_obj.held_by_body_id == b.body_id)
                or (
                    target_obj.position is None
                    and target_obj.held_by_body_id is not None
                    and target_obj.held_by_body_id != b.body_id
                    and any(
                        other.body_id == target_obj.held_by_body_id
                        and other.held_object_id == target_obj.object_id
                        for other in cur_w.bodies
                    )
                )
            ):
                return True
        return False

    if any(_body_needs_reconciliation(b) for b in cur_w.bodies):
        _commit_world_successor(authority, cur_w)
    if expand_library:
        expand_library_books(authority)
    return authority


from contextlib import contextmanager

@contextmanager
def _world_thermal_transaction(authority: Any):
    """Transactional context manager enforcing the canonical lock hierarchy (_thermal_lock -> _lock)
    and providing all-or-nothing rollback for any world mutation."""
    thermal_lock = getattr(authority, "_thermal_lock", None)
    world_lock = getattr(authority, "_lock", None)

    # Acquire in canonical hierarchy: _thermal_lock FIRST, then _lock SECOND
    if thermal_lock is not None:
        thermal_lock.acquire()
    try:
        if world_lock is not None:
            world_lock.acquire()
        try:
            # Snapshot prior states for atomic rollback on failure
            prior_state = getattr(authority, "_state", None)
            prior_thermal_rev = getattr(authority, "_thermal_world_revision", None)
            prior_thermal_receipt = getattr(authority, "_thermal_world_observation_receipt_sha256", None)
            prior_physical_return = getattr(authority, "_physical_return", None)
            prior_thermal_state = getattr(authority, "_thermal_state", None)
            prior_thermal_anatomy = getattr(authority, "_thermal_anatomy", None)
            prior_latest_thermal = getattr(authority, "_latest_thermal_transition", None)
            prior_pending_thermal = getattr(authority, "_pending_thermal", None)
            prior_committed_thermal_tail = getattr(authority, "_committed_thermal_tail", None)

            yield

        except BaseException:
            # Complete atomic rollback of all authority states (including restoring originally None fields)
            if hasattr(authority, "_state"):
                authority._state = prior_state
            if hasattr(authority, "_thermal_world_revision"):
                authority._thermal_world_revision = prior_thermal_rev
            if hasattr(authority, "_thermal_world_observation_receipt_sha256"):
                authority._thermal_world_observation_receipt_sha256 = prior_thermal_receipt
            if hasattr(authority, "_physical_return"):
                authority._physical_return = prior_physical_return
            if hasattr(authority, "_thermal_state"):
                authority._thermal_state = prior_thermal_state
            if hasattr(authority, "_thermal_anatomy"):
                authority._thermal_anatomy = prior_thermal_anatomy
            if hasattr(authority, "_latest_thermal_transition"):
                authority._latest_thermal_transition = prior_latest_thermal
            if hasattr(authority, "_pending_thermal"):
                authority._pending_thermal = prior_pending_thermal
            if hasattr(authority, "_committed_thermal_tail"):
                authority._committed_thermal_tail = prior_committed_thermal_tail
            raise
        finally:
            if world_lock is not None:
                world_lock.release()
    finally:
        if thermal_lock is not None:
            thermal_lock.release()


def _commit_world_successor(
    authority: Any,
    new_world: Any,
    *,
    new_anatomy: Any = None,
) -> Any:
    """Commit a new world successor into authority, synchronously updating thermal custody,
    expanding thermal anatomy if applicable, and rebinding pending physical return."""
    from dataclasses import replace
    # Enforce canonical reciprocal custody between bodies and objects
    remaining_ids = {obj.object_id for obj in new_world.objects}
    held_by_body = {
        obj.held_by_body_id: obj.object_id
        for obj in new_world.objects
        if obj.held_by_body_id is not None
    }
    corrected_bodies = []
    bodies_changed = False
    for b in new_world.bodies:
        actual_held = held_by_body.get(b.body_id)
        actual_contact = b.active_contact
        if actual_contact is not None:
            target_obj = next((o for o in new_world.objects if o.object_id == actual_contact.object_id), None)
            if target_obj is None:
                actual_contact = None
            elif actual_contact.kind == "oral" and not (
                (b.held_object_id == target_obj.object_id and target_obj.held_by_body_id == b.body_id)
                or (
                    target_obj.position is None
                    and target_obj.held_by_body_id is not None
                    and target_obj.held_by_body_id != b.body_id
                    and any(
                        other.body_id == target_obj.held_by_body_id
                        and other.held_object_id == target_obj.object_id
                        for other in new_world.bodies
                    )
                )
            ):
                actual_contact = None
        if b.held_object_id != actual_held or b.active_contact != actual_contact:
            corrected_bodies.append(replace(b, held_object_id=actual_held, active_contact=actual_contact))
            bodies_changed = True
        else:
            corrected_bodies.append(b)
    if bodies_changed:
        new_world = replace(new_world, bodies=tuple(corrected_bodies))
    # Enforce canonical identity ordering for regions, portals, and objects
    ordered_regions = tuple(sorted(new_world.regions, key=lambda item: item.region_id))
    ordered_portals = tuple(sorted(new_world.portals, key=lambda item: item.portal_id))
    ordered_objects = tuple(sorted(new_world.objects, key=lambda item: item.object_id))
    if (
        ordered_regions != new_world.regions
        or ordered_portals != new_world.portals
        or ordered_objects != new_world.objects
    ):
        new_world = replace(
            new_world,
            regions=ordered_regions,
            portals=ordered_portals,
            objects=ordered_objects,
        )
    if hasattr(authority, "_validate_world"):
        authority._validate_world(new_world)
    if hasattr(authority, "_observation_for"):
        new_obs = authority._observation_for(new_world)
        authority._state = replace(authority._state, world=new_world, observation=new_obs)
        receipt_sha = new_obs.authority_receipt_sha256
    else:
        authority._state = replace(authority._state, world=new_world)
        receipt_sha = ""

    # Synchronously update thermal custody to match new world revision & receipt
    if hasattr(authority, "_thermal_world_revision"):
        authority._thermal_world_revision = new_world.revision
    if hasattr(authority, "_thermal_world_observation_receipt_sha256"):
        authority._thermal_world_observation_receipt_sha256 = receipt_sha

    # Expand thermal anatomy and carry forward lived thermal nodes if new anatomy provided
    if new_anatomy is not None and hasattr(authority, "_thermal_anatomy"):
        prior_nodes = dict(zip(authority._thermal_anatomy.node_ids, authority._thermal_state.nodes))
        genesis = new_anatomy.genesis_state()
        carried_nodes = []
        for node_id, node in zip(new_anatomy.node_ids, genesis.nodes):
            lived = prior_nodes.get(node_id)
            if lived is not None and lived.capacity_microjoules_per_millikelvin == node.capacity_microjoules_per_millikelvin:
                carried_nodes.append(lived)
            else:
                carried_nodes.append(node)
        authority._thermal_anatomy = new_anatomy
        authority._thermal_state = replace(genesis, nodes=tuple(carried_nodes))

    # Rebind pending physical return to successor world revision & observation receipt
    cur_ret = getattr(authority, "_physical_return", None)
    if cur_ret is not None:
        authority._physical_return = replace(
            cur_ret,
            world_revision=new_world.revision,
            world_observation_receipt_sha256=receipt_sha,
        )

    # Retire retained latest transition tail on world successor mutations (no elapsed time)
    if hasattr(authority, "_latest_thermal_transition"):
        authority._latest_thermal_transition = None
    if hasattr(authority, "_pending_thermal"):
        authority._pending_thermal = None
    if hasattr(authority, "_committed_thermal_tail"):
        authority._committed_thermal_tail = None

    return authority


def get_tv_broadcast(authority: Any) -> Any:
    """Retrieve the dynamic television broadcast generator from a world authority."""
    if not hasattr(authority, "television_broadcast") or authority.television_broadcast is None:
        from dsf_ai_service.dynamic_television_broadcast import TelevisionBroadcast
        authority.television_broadcast = TelevisionBroadcast()
    return authority.television_broadcast


def switch_tv_channel(authority: Any, channel: int | None = None) -> int:
    """Switch the TV room broadcast channel and return the new active channel under coupled transaction.
    Enforces canonical lock hierarchy (_thermal_lock -> _lock), updates thermal custody,
    and rolls back atomically on exception."""
    with _world_thermal_transaction(authority):
        broadcast = get_tv_broadcast(authority)
        old_ch = broadcast.channel
        new_ch = broadcast.switch_channel(channel)
        try:
            new_surface = broadcast.render_screen_surface()
            new_emission = broadcast.get_emission_ppm()
            if hasattr(authority, "_state") and hasattr(authority._state, "world"):
                from dataclasses import replace
                cur_world = authority._state.world
                updated = []
                for obj in cur_world.objects:
                    if obj.object_id == "television":
                        updated.append(replace(obj, optical_surface=new_surface, emission_ppm=new_emission))
                    else:
                        updated.append(obj)
                new_world = replace(cur_world, revision=cur_world.revision + 1, objects=tuple(updated))
                _commit_world_successor(authority, new_world)
        except Exception:
            broadcast.channel = old_ch
            raise
    return new_ch


def operate_tv_remote(authority: Any) -> int:
    """Operate the TV remote to cycle the TV broadcast channel."""
    return switch_tv_channel(authority)


LIBRARY_BOOK_SHELVES = {
    "book-peter-rabbit": (9_800, 8_900, 0, 330),
    "book-wind-willows": (10_200, 8_900, 0, 330),
    "book": (12_100, 8_900, 0, 330),
    "book-aesops-fables": (12_500, 8_900, 0, 330),
    "book-mother-goose": (12_900, 8_900, 0, 330),
}


def nocturnal_house_tidying(authority: Any) -> None:
    """Perform caretaker nocturnal house-cleaning and state reset during sleep cycles under coupled transaction.

    1. Resets the television broadcast back to Channel 0 (Boring static & 60 Hz hum).
    2. Tidies tv-remote, stroller-carriage, and garden fauna perches.
    3. Reshelves unheld library books to shelf-a and shelf-b within child reach for wakeful selection.
    4. Clears stray floor apples and preserves objects currently held by Guala or caretaker.
    """
    with _world_thermal_transaction(authority):
        broadcast = get_tv_broadcast(authority)
        old_ch = broadcast.channel
        broadcast.reset_to_boring()
        try:
            new_surface = broadcast.render_screen_surface()
            new_emission = broadcast.get_emission_ppm()
            if hasattr(authority, "_state") and hasattr(authority._state, "world"):
                from dataclasses import replace
                from dsf_ai_service.substrate.embodiment_world import PositionMM
                cur_world = authority._state.world
                updated = []
                for obj in cur_world.objects:
                    if getattr(obj, "held_by_body_id", None) is not None:
                        updated.append(obj)
                        continue
                    if obj.object_id == "television":
                        updated.append(replace(obj, optical_surface=new_surface, emission_ppm=new_emission))
                    elif obj.object_id == "tv-remote":
                        updated.append(replace(obj, position=PositionMM(15_600, 7_600, 0)))
                    elif obj.object_id == "stroller-carriage":
                        updated.append(replace(obj, position=PositionMM(6_500, 6_000, 0)))
                    elif obj.object_id == "garden-bird":
                        updated.append(replace(obj, position=PositionMM(14_000, 15_500, 0), elevation_mm=1_800))
                    elif obj.object_id == "garden-butterfly":
                        updated.append(replace(obj, position=PositionMM(16_500, 11_000, 0), elevation_mm=450))
                    elif obj.object_id in LIBRARY_BOOK_SHELVES and obj.position is not None:
                        bx, by, bz, target_elev = LIBRARY_BOOK_SHELVES[obj.object_id]
                        updated.append(replace(obj, position=PositionMM(bx, by, bz), elevation_mm=target_elev))
                    elif obj.object_id == "stacking-rings" and obj.position is not None:
                        updated.append(replace(obj, position=PositionMM(750, 5_600, 0), elevation_mm=450))
                    elif obj.object_id == "toy-blocks" and obj.position is not None:
                        updated.append(replace(obj, position=PositionMM(1_020, 5_600, 0), elevation_mm=450))
                    elif obj.object_id == "play-ball" and obj.position is not None:
                        updated.append(replace(obj, position=PositionMM(1_250, 5_600, 0), elevation_mm=450))
                    elif obj.object_id == "toy-bear" and obj.position is not None:
                        if obj.position.x > 5600 or obj.position.y < 5000:
                            updated.append(replace(obj, position=PositionMM(4_800, 9_200, 0), elevation_mm=0))
                        else:
                            updated.append(obj)
                    elif obj.object_id.startswith("apple") and obj.position is not None:
                        # Clear stray abandoned floor apples during nocturnal house tidying so Guala wakes to a clean home
                        if obj.held_by_body_id is not None:
                            updated.append(obj)
                        else:
                            continue
                    else:
                        updated.append(obj)
                remaining_ids = {obj.object_id for obj in updated}
                updated_bodies = tuple(
                    replace(b, held_object_id=None)
                    if b.held_object_id is not None and b.held_object_id not in remaining_ids
                    else b
                    for b in cur_world.bodies
                )
                new_world = replace(cur_world, revision=cur_world.revision + 1, objects=tuple(updated), bodies=updated_bodies)
                _commit_world_successor(authority, new_world)
        except Exception:
            broadcast.channel = old_ch
            raise


def flutter_garden_fauna(authority: Any) -> bool:
    """Animate outdoor garden fauna (butterfly flutter / bird perch shift)
    during daylight stroller excursions under coupled thermal transaction,
    strictly bounded within the physical garden/backyard area."""
    with _world_thermal_transaction(authority):
        if not hasattr(authority, "_state") or not hasattr(authority._state, "world"):
            return False
        from dataclasses import replace
        from dsf_ai_service.substrate.embodiment_world import PositionMM
        cur_world = authority._state.world
        updated = []
        shifted = False
        rev = cur_world.revision
        delta = 100 if (rev % 2 == 0) else -100
        for obj in cur_world.objects:
            if obj.object_id == "garden-butterfly" and obj.position is not None:
                # Strictly clamp butterfly within garden flora bounds: x in [11_000, 18_000], y in [10_500, 15_500], z in [100, 1_200]
                target_x = max(11_000, min(18_000, obj.position.x + delta))
                target_y = max(10_500, min(15_500, obj.position.y + (50 if rev % 3 == 0 else -50)))
                if abs(target_x - 16_500) < 200 and abs(target_y - 11_500) < 200:
                    target_y = 11_000
                target_elev = max(100, min(1_200, 450 + (50 if rev % 2 == 0 else -50)))
                new_pos = PositionMM(target_x, target_y, 0)
                updated.append(replace(obj, position=new_pos, elevation_mm=target_elev))
                shifted = True
            elif obj.object_id == "garden-bird" and obj.position is not None:
                # Strictly clamp bird within tree perch bounds: x in [11_000, 18_000], y in [10_500, 15_500], z in [1_000, 2_200]
                target_x = max(11_000, min(18_000, obj.position.x + (50 if rev % 3 == 1 else -50)))
                target_y = max(10_500, min(15_500, obj.position.y + delta))
                target_elev = max(1_000, min(2_200, 1_800 + (100 if rev % 2 == 0 else -100)))
                new_pos = PositionMM(target_x, target_y, 0)
                updated.append(replace(obj, position=new_pos, elevation_mm=target_elev))
                shifted = True
            else:
                updated.append(obj)
        if shifted:
            new_world = replace(cur_world, revision=cur_world.revision + 1, objects=tuple(updated))
            _commit_world_successor(authority, new_world)
            return True
        return False


def compute_spatial_horizon_observation(
    authority: Any,
    body_id: str = "guala-body-1",
    max_objects: int = 64,
    strict_occlusion: bool = False,
) -> Any:
    """Compute an optically and acoustically occluded spatial horizon ObservationSnapshot.

    Physics Principle:
    Solid walls attenuate optical rays and acoustic transmissions. An embodied sensor
    (retinal CORDIC ray-tracer and binaural cochlea) receives signals from the local topological
    manifold:
      1. Immediate Room (R_current) containing the body.
      2. Adjacent Rooms (R_adjacent) connecting via open portals with verified line-of-sight.

    Entities are ranked by optical solid angle metric Omega = (pi * r^2) / (d^2 + 1),
    placing proximate, held, and physically large entities within the receptor aperture while
    distant occluded items fall outside the horizon.
    """
    from dataclasses import replace
    import math

    # Strictly clamp max_objects to physical sensory receptor aperture bound <= 64
    max_objects = min(max(int(max_objects), 1), 64)

    cur_world = authority._state.world

    body = next((b for b in cur_world.bodies if b.body_id == body_id), None)
    if not body:
        body = next((b for b in cur_world.bodies if b.body_id == getattr(authority, "self_body_id", "")), None)
        if not body and cur_world.bodies:
            body = cur_world.bodies[0]

    if not body:
        horizon_world = replace(cur_world, objects=tuple(cur_world.objects[:max_objects]))
        return authority._observation_for(horizon_world)

    b_pos = body.pose.position
    b_r = body.radius_mm

    curr_r = None
    for r in cur_world.regions:
        b = getattr(r, "bounds", None)
        if b is not None and b.contains_floor_disc(b_pos, b_r):
            curr_r = r
            break
    if curr_r is None:
        for r in cur_world.regions:
            b = getattr(r, "bounds", None)
            if b is not None:
                if b.minimum.x <= b_pos.x <= b.maximum.x and b.minimum.y <= b_pos.y <= b.maximum.y:
                    curr_r = r
                    break

    body_positions = {b.body_id: b.pose.position for b in cur_world.bodies}

    def _get_effective_pos(obj: Any) -> Any:
        if obj.position is not None:
            return obj.position
        if obj.held_by_body_id:
            return body_positions.get(obj.held_by_body_id, b_pos)
        return b_pos

    def _solid_angle(obj: Any) -> float:
        r_mm = getattr(obj, "radius_mm", 100)
        if obj.position is None and obj.held_by_body_id == body_id:
            # Held by self against body at arm distance ~250 mm: finite physical solid angle
            d2 = 250.0 ** 2
            return (math.pi * (r_mm ** 2)) / (d2 + 1)
        pos = _get_effective_pos(obj)
        d2 = (pos.x - b_pos.x) ** 2 + (pos.y - b_pos.y) ** 2
        return (math.pi * (r_mm ** 2)) / (d2 + 1)

    def _get_region_id(pos: Any) -> str | None:
        if pos is None:
            return None
        for r in cur_world.regions:
            b = getattr(r, "bounds", None)
            if b is not None:
                if b.minimum.x <= pos.x <= b.maximum.x and b.minimum.y <= pos.y <= b.maximum.y:
                    return r.region_id
        return None

    def _has_portal_line_of_sight(p: Any, p1: Any, p2: Any) -> bool:
        axis = getattr(p, "axis", "x")
        plane = getattr(p, "plane_mm", 0)
        ap_min = getattr(p, "aperture_min_mm", 0)
        ap_max = getattr(p, "aperture_max_mm", 0)

        if axis == "x":
            denom = p2.x - p1.x
            if denom == 0:
                return False
            t = (plane - p1.x) / denom
            if not (0.0 <= t <= 1.0):
                return False
            y_cross = p1.y + t * (p2.y - p1.y)
            return ap_min <= y_cross <= ap_max
        elif axis == "y":
            denom = p2.y - p1.y
            if denom == 0:
                return False
            t = (plane - p1.y) / denom
            if not (0.0 <= t <= 1.0):
                return False
            x_cross = p1.x + t * (p2.x - p1.x)
            return ap_min <= x_cross <= ap_max
        return False

    tier1 = []
    tier2 = []

    for obj in cur_world.objects:
        if obj.position is None and obj.held_by_body_id == body_id:
            tier1.append(obj)
            continue

        eff_pos = _get_effective_pos(obj)
        obj_r_id = _get_region_id(eff_pos)

        if curr_r and obj_r_id == curr_r.region_id:
            tier1.append(obj)
        elif curr_r and obj_r_id:
            has_los = False
            for p in cur_world.portals:
                p_regs = getattr(p, "region_ids", ())
                if curr_r.region_id in p_regs and obj_r_id in p_regs:
                    if _has_portal_line_of_sight(p, b_pos, eff_pos):
                        has_los = True
                        break
            if has_los:
                tier1.append(obj)
            else:
                tier2.append(obj)
        else:
            tier2.append(obj)

    tier1.sort(key=_solid_angle, reverse=True)
    tier2.sort(key=_solid_angle, reverse=True)

    if strict_occlusion:
        selected = tier1[:max_objects]
    else:
        selected = tier1[:max_objects]
        if len(selected) < max_objects:
            selected.extend(tier2[: max_objects - len(selected)])

    horizon_world = replace(cur_world, objects=tuple(selected))
    return authority._observation_for(horizon_world)


def generate_birdsong_chirp(
    frequency_hz: float = 4200.0,
    duration_seconds: float = 0.15,
    sample_rate_hz: int = 16_000,
    amplitude: int = 8000,
) -> bytes:
    """Generate deterministic canonical 16 kHz S16LE PCM birdsong acoustic chirp waveform.

    Physics model: frequency modulated high-frequency acoustic burst (Robin / Finch song).
    """
    import math
    import struct
    total_samples = int(duration_seconds * sample_rate_hz)
    frames = bytearray()
    for n in range(total_samples):
        t = n / sample_rate_hz
        f_instant = frequency_hz + 800.0 * (t / duration_seconds)
        phase = 2.0 * math.pi * f_instant * t
        envelope = math.exp(-0.5 * (((t - duration_seconds / 2.0) / (duration_seconds / 4.0)) ** 2))
        sample_val = int(amplitude * envelope * math.sin(phase))
        clamped = max(-32768, min(32767, sample_val))
        frames.extend(struct.pack("<h", clamped))
    return bytes(frames)


GARDEN_FAUNA_FLORA_ITEMS = (
    ("garden-flowers",   16_500, 11_500, 120,    250, (880_000, 200_000, 750_000, 600_000, 200_000, 150_000), 100),
    ("garden-butterfly", 16_500, 11_000,  40,      1, (150_000, 350_000, 850_000, 750_000, 400_000, 200_000), 450),
    ("garden-bird",      14_000, 15_500,  65,     35, (600_000, 450_000, 180_000, 120_000, 100_000,  80_000), 1_800),
)



LIBRARY_EXPANSION_BOOKS = (
    ("book-peter-rabbit",  10_000, 6_000, 140, 800, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000), 450),
    ("book-wind-willows", 10_500, 6_000, 140, 800, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000), 450),
    ("book-aesops-fables", 11_000, 6_000, 140, 800, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000), 450),
    ("book-mother-goose",  11_500, 6_000, 140, 800, (850_000, 850_000, 850_000, 850_000, 850_000, 850_000), 450),
)


def expand_library_books(authority: Any) -> Any:
    """Expand the world authority with 4 distinct children's literature books under coupled transaction."""
    with _world_thermal_transaction(authority):
        if hasattr(authority, "_state") and hasattr(authority._state, "world"):
            from dataclasses import replace
            from dsf_ai_service.substrate.embodiment_world import EmbodiedObject, PositionMM, ObjectMaterialState
            cur_w = authority._state.world
            existing_ids = {o.object_id for o in cur_w.objects}
            res_sec = 864_000
            new_items = []
            for name, x, y, radius, mass, refl, elev in LIBRARY_EXPANSION_BOOKS:
                if name not in existing_ids:
                    new_items.append(
                        EmbodiedObject(
                            name,
                            radius,
                            mass,
                            PositionMM(x, y, 0),
                            reflectance_ppm=refl,
                            optical_surface=_home_optical_surface_for(name, refl),
                            material=ObjectMaterialState(
                                odorant_reservoir_nanograms=tuple(rate * res_sec for rate in (0, 0, 0, 40, 30, 900, 0, 0)),
                                odorant_release_nanograms_per_second=(0, 0, 0, 40, 30, 900, 0, 0),
                                tastant_mass_micrograms=(0, 0, 0, 2_000, 0),
                                surface_temperature_millikelvin=294_000,
                                compliance_ppm=60_000,
                                roughness_micrometers=60,
                                moisture_ppm=18_000,
                            ),
                            shape="box",
                            size_mm=(190, 140, 40),
                            elevation_mm=elev,
                        )
                    )
            if new_items:
                expanded_w = replace(cur_w, revision=cur_w.revision + 1, objects=cur_w.objects + tuple(new_items))
                _commit_world_successor(authority, expanded_w)
    return authority


def expand_garden_fauna_and_flora(authority: Any) -> Any:
    """Expand the world authority with garden fauna and flora under coupled transaction."""
    with _world_thermal_transaction(authority):
        if hasattr(authority, "_state") and hasattr(authority._state, "world"):
            from dataclasses import replace
            from dsf_ai_service.substrate.embodiment_world import EmbodiedObject, PositionMM, ObjectMaterialState
            cur_w = authority._state.world
            existing_ids = {o.object_id for o in cur_w.objects}
            res_sec = 864_000
            new_items = []
            if "garden-flowers" not in existing_ids:
                refl = (880_000, 200_000, 750_000, 600_000, 200_000, 150_000)
                new_items.append(
                    EmbodiedObject(
                        "garden-flowers",
                        120,
                        250,
                        PositionMM(16_500, 11_500, 0),
                        reflectance_ppm=refl,
                        optical_surface=_home_optical_surface_for("garden-flowers", refl),
                        material=ObjectMaterialState(
                            odorant_reservoir_nanograms=tuple(rate * res_sec for rate in (0, 0, 0, 100, 150, 0, 0, 0)),
                            odorant_release_nanograms_per_second=(0, 0, 0, 100, 150, 0, 0, 0),
                            tastant_mass_micrograms=(0, 0, 0, 1_500, 0),
                            surface_temperature_millikelvin=291_000,
                            compliance_ppm=180_000,
                            roughness_micrometers=30,
                            moisture_ppm=200_000,
                        ),
                        shape="sphere",
                        elevation_mm=100,
                    )
                )
            if "garden-butterfly" not in existing_ids:
                refl = (150_000, 350_000, 850_000, 750_000, 400_000, 200_000)
                new_items.append(
                    EmbodiedObject(
                        "garden-butterfly",
                        40,
                        1,
                        PositionMM(16_500, 11_000, 0),
                        reflectance_ppm=refl,
                        optical_surface=_home_optical_surface_for("garden-butterfly", refl),
                        material=ObjectMaterialState(
                            odorant_reservoir_nanograms=tuple(rate * res_sec for rate in (0, 0, 0, 0, 10, 0, 0, 0)),
                            odorant_release_nanograms_per_second=(0, 0, 0, 0, 10, 0, 0, 0),
                            tastant_mass_micrograms=(0, 0, 0, 100, 0),
                            surface_temperature_millikelvin=294_000,
                            compliance_ppm=50_000,
                            roughness_micrometers=10,
                            moisture_ppm=5_000,
                        ),
                        shape="sphere",
                        elevation_mm=450,
                    )
                )
            if "garden-bird" not in existing_ids:
                refl = (600_000, 450_000, 180_000, 120_000, 100_000, 80_000)
                new_items.append(
                    EmbodiedObject(
                        "garden-bird",
                        65,
                        35,
                        PositionMM(14_000, 15_500, 0),
                        reflectance_ppm=refl,
                        optical_surface=_home_optical_surface_for("garden-bird", refl),
                        material=ObjectMaterialState(
                            odorant_reservoir_nanograms=tuple(rate * res_sec for rate in (0, 0, 0, 0, 300, 0, 0, 0)),
                            odorant_release_nanograms_per_second=(0, 0, 0, 0, 300, 0, 0, 0),
                            tastant_mass_micrograms=(0, 0, 0, 600, 0),
                            surface_temperature_millikelvin=312_000,
                            compliance_ppm=600_000,
                            roughness_micrometers=150,
                            moisture_ppm=40_000,
                        ),
                        shape="sphere",
                        elevation_mm=1_800,
                    )
                )
            if new_items:
                expanded_w = replace(cur_w, revision=cur_w.revision + 1, objects=cur_w.objects + tuple(new_items))
                _commit_world_successor(authority, expanded_w)
    return authority


def expand_exterior_walkway(authority: Any) -> Any:
    """Expand the world authority with an exterior walkway and perimeter garden gate under coupled transaction.
    Integrates walkway region, door-gate portal, and expanded thermal anatomy with air volume and flows."""
    with _world_thermal_transaction(authority):
        if hasattr(authority, "_state") and hasattr(authority._state, "world"):
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
            cur_w = authority._state.world
            reg_ids = {r.region_id for r in cur_w.regions}
            portal_ids = {p.portal_id for p in cur_w.portals}
            obj_ids = {o.object_id for o in cur_w.objects}

            new_regions = list(cur_w.regions)
            new_portals = list(cur_w.portals)
            new_objects = list(cur_w.objects)

            if "walkway" not in reg_ids:
                walkway = PhysicalRegion(
                    region_id="walkway",
                    bounds=RoomBoundsMM(PositionMM(0, 16_000, 0), PositionMM(20_000, 22_000, 8_000)),
                    ceiling_height_mm=8_000,
                    reflectance_ppm=(70_000, 100_000, 200_000, 340_000, 580_000, 740_000),
                    illumination_ppm=(280_000,) * 6,
                    air=AirVolumeState(
                        volume_cubic_mm=20_000 * 6_000 * 8_000,
                        odorant_mass_nanograms=(15_120_000, 0, 0, 38_520_000, 4_968_000, 0, 288_000, 0),
                    ),
                )
                new_regions.append(walkway)

            if "door-gate" not in portal_ids:
                gate = PhysicalPortal(
                    portal_id="door-gate",
                    region_ids=("backyard", "walkway"),
                    axis="y",
                    plane_mm=16_000,
                    aperture_min_mm=9_000,
                    aperture_max_mm=11_000,
                    height_mm=2_050,
                    air_flow_cubic_mm_per_second=2_000_000,
                )
                new_portals.append(gate)

            res_sec = 864_000
            if "walkway-bench" not in obj_ids:
                refl = (320_000, 260_000, 180_000, 120_000, 90_000, 80_000)
                bench = EmbodiedObject(
                    "walkway-bench",
                    650,
                    35_000,
                    PositionMM(10_000, 19_000, 0),
                    reflectance_ppm=refl,
                    optical_surface=_home_optical_surface_for("walkway-bench", refl),
                    material=ObjectMaterialState(
                        odorant_reservoir_nanograms=tuple(rate * res_sec for rate in (0, 0, 0, 800, 50, 0, 0, 0)),
                        odorant_release_nanograms_per_second=(0, 0, 0, 800, 50, 0, 0, 0),
                        tastant_mass_micrograms=(0, 0, 0, 1_500, 0),
                        surface_temperature_millikelvin=294_000,
                        compliance_ppm=40_000,
                        roughness_micrometers=60,
                        moisture_ppm=15_000,
                    ),
                    shape="box",
                    size_mm=(1_200, 450, 450),
                    elevation_mm=0,
                )
                new_objects.append(bench)

            if "walkway-lantern" not in obj_ids:
                refl = (850_000, 800_000, 700_000, 550_000, 450_000, 400_000)
                emission = (800_000, 750_000, 650_000, 500_000, 400_000, 350_000)
                lantern = EmbodiedObject(
                    "walkway-lantern",
                    150,
                    4_500,
                    PositionMM(8_500, 17_000, 0),
                    reflectance_ppm=refl,
                    emission_ppm=emission,
                    optical_surface=_home_optical_surface_for("walkway-lantern", refl),
                    material=ObjectMaterialState(
                        odorant_reservoir_nanograms=tuple(rate * res_sec for rate in (0, 0, 0, 0, 20, 0, 260, 0)),
                        odorant_release_nanograms_per_second=(0, 0, 0, 0, 20, 0, 260, 0),
                        tastant_mass_micrograms=(0, 0, 0, 400, 0),
                        surface_temperature_millikelvin=315_000,
                        compliance_ppm=20_000,
                        roughness_micrometers=10,
                        moisture_ppm=2_000,
                    ),
                    shape="sphere",
                    elevation_mm=1_200,
                )
                new_objects.append(lantern)

            new_world = replace(
                cur_w,
                revision=cur_w.revision + 1,
                regions=tuple(new_regions),
                portals=tuple(new_portals),
                objects=tuple(new_objects),
            )
            # Derive expanded coupled thermal anatomy if regions/portals changed
            new_anatomy = None
            if hasattr(authority, "_thermal_anatomy") and ("walkway" not in reg_ids or "door-gate" not in portal_ids):
                new_anatomy = _home_thermal_anatomy(new_regions, new_portals)
            _commit_world_successor(authority, new_world, new_anatomy=new_anatomy)
    return authority


from dsf_ai_service.substrate.embodiment_world import PositionMM

HER_ROOM_LAYOUT = {
    "bed": PositionMM(900, 9100, 0),
    "pillow": PositionMM(900, 9100, 0),
    "blanket": PositionMM(900, 8500, 0),
    "desk": PositionMM(4900, 5700, 0),
    "desk-chair": PositionMM(3800, 5700, 0),
    "curtains": PositionMM(2800, 9750, 0),
    "wall-art-shapes": PositionMM(320, 6500, 0),
    "wall-art-weather": PositionMM(320, 7500, 0),
    "playpen": PositionMM(4200, 8800, 0),
    "night-light": PositionMM(500, 8600, 0),
    "toy-chest": PositionMM(1000, 5600, 0),
    "stacking-rings": PositionMM(750, 5600, 0),
    "toy-blocks": PositionMM(1020, 5600, 0),
    "play-ball": PositionMM(1250, 5600, 0),
}
HER_ROOM_RADII = {
    "desk": 700,
    "curtains": 250,
    "playpen": 450,
    "bed": 900,
    "toy-chest": 500,
    "stacking-rings": 140,
    "toy-blocks": 120,
    "play-ball": 90,
}
HER_ROOM_ELEVATIONS = {
    "pillow": 350,
    "blanket": 350,
    "curtains": 1200,
    "wall-art-shapes": 1300,
    "wall-art-weather": 1300,
    "stacking-rings": 450,
    "toy-blocks": 450,
    "play-ball": 450,
}
HER_ROOM_MASSES = {
    "curtains": 15_000,
    "wall-art-shapes": 10_000,
    "wall-art-weather": 10_000,
    "playpen": 15_000,
    "toy-chest": 8_000,
    "toy-blocks": 480,
}


def renovate_her_room_layout(authority: Any) -> bool:
    """Reposition and renovate Her-Room furniture, fixtures, toy-chest inventory, and place sleeping Guala on her bed."""
    with _world_thermal_transaction(authority):
        if not hasattr(authority, "_state") or not hasattr(authority._state, "world"):
            return False
        cur_world = authority._state.world
        needs_update = False
        obj_ids = {obj.object_id for obj in cur_world.objects}
        if "toy-blocks" not in obj_ids:
            needs_update = True
        for obj in cur_world.objects:
            if obj.object_id in HER_ROOM_LAYOUT and obj.position != HER_ROOM_LAYOUT[obj.object_id]:
                needs_update = True
                break
            if obj.object_id in HER_ROOM_RADII and obj.radius_mm != HER_ROOM_RADII[obj.object_id]:
                needs_update = True
                break
            if obj.object_id in HER_ROOM_ELEVATIONS and obj.elevation_mm != HER_ROOM_ELEVATIONS[obj.object_id]:
                needs_update = True
                break
            if obj.object_id in HER_ROOM_MASSES and obj.mass_grams != HER_ROOM_MASSES[obj.object_id]:
                needs_update = True
                break
        bed_pos = HER_ROOM_LAYOUT["bed"]
        for body in cur_world.bodies:
            if body.body_id == cur_world.self_body_id and body.pose.position != bed_pos:
                needs_update = True
                break
        if not needs_update:
            return False
        from dataclasses import replace
        from dsf_ai_service.substrate.embodiment_world import PositionMM, PoseMM, EmbodiedObject, ObjectMaterialState
        updated = []
        for obj in cur_world.objects:
            pos = HER_ROOM_LAYOUT.get(obj.object_id, obj.position)
            radius = HER_ROOM_RADII.get(obj.object_id, obj.radius_mm)
            elev = HER_ROOM_ELEVATIONS.get(obj.object_id, obj.elevation_mm)
            mass = HER_ROOM_MASSES.get(obj.object_id, obj.mass_grams)
            if obj.object_id == "toy-bear" and (obj.position.x > 5600 or obj.position.y < 5000):
                pos = PositionMM(4800, 9200, 0)
                elev = 0
            updated.append(replace(obj, position=pos, radius_mm=radius, elevation_mm=elev, mass_grams=mass))
        if "toy-blocks" not in obj_ids:
            res_sec = 864_000
            refl = (880_000, 820_000, 400_000, 250_000, 200_000, 180_000)
            blocks = EmbodiedObject(
                "toy-blocks",
                HER_ROOM_RADII["toy-blocks"],
                HER_ROOM_MASSES["toy-blocks"],
                HER_ROOM_LAYOUT["toy-blocks"],
                reflectance_ppm=refl,
                material=ObjectMaterialState(
                    odorant_reservoir_nanograms=tuple(rate * res_sec for rate in (0, 0, 0, 800, 100, 0, 0, 0)),
                    odorant_release_nanograms_per_second=(0, 0, 0, 800, 100, 0, 0, 0),
                    tastant_mass_micrograms=(0, 0, 0, 800, 0),
                    surface_temperature_millikelvin=294_000,
                    compliance_ppm=200_000,
                    roughness_micrometers=20,
                    moisture_ppm=12_000,
                ),
                shape="parts",
                elevation_mm=HER_ROOM_ELEVATIONS["toy-blocks"],
                parts=tuple(HOME_PARTS["toy-blocks"]),
            )
            updated.append(blocks)
        updated_bodies = []
        for body in cur_world.bodies:
            if body.body_id == cur_world.self_body_id and body.pose.position != bed_pos:
                updated_bodies.append(replace(body, pose=PoseMM(bed_pos, body.pose.heading_millidegrees)))
            else:
                updated_bodies.append(body)
        new_world = replace(cur_world, revision=cur_world.revision + 1, bodies=tuple(updated_bodies), objects=tuple(updated))
        _commit_world_successor(authority, new_world)
        return True
