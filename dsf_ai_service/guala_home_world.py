"""Canonical physical home authority for the lean Guala runtime.

This module is environment anatomy only. It owns no organism, scheduler,
observer, persistence, lesson, action choice, or cognition.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
from typing import Any, Iterable
import uuid


TOUCH_RECEPTORS_AUTHORIZED = True
HOME_BOOK_OBJECT_ID = "book"

HOME_ROOM_SPAN_MM = 4_000
HOME_CEILING_MM = 2_600
# The backyard has no ceiling but the sky; this is the honest
# bound of the modelled air column above it, not a room lid.
BACKYARD_SKY_MM = 8_000



def _home_optical_surface_for(
    name: str,
    base_ref: tuple[int, int, int, int, int, int],
) -> Any:
    """Generate a deterministic, content-addressed optical surface for an object.

    Each surface is a 32x32 grid with 4 reflectance spectrum shades derived from
    the object's base spectral reflectance, giving the world-eye raycaster
    fine structural contrast.
    """
    from dsf_ai_service.substrate.embodiment_world import ObjectOpticalSurface

    def scale_spec(scale: float) -> tuple[int, int, int, int, int, int]:
        return tuple(
            max(10_000, min(1_000_000, int(round(c * scale))))
            for c in base_ref
        )

    palette_list = [
        scale_spec(0.65),
        scale_spec(0.85),
        scale_spec(1.10),
        scale_spec(1.35),
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
            if any(k in name for k in ("table", "chair", "desk", "shelf", "chest", "counter", "cabinet", "pantry")):
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
            elif any(k in name for k in ("blanket", "curtains")):
                if "curtains" in name:
                    val = (c % 4) % num_p
                else:
                    val = (((r // 4) % 2) ^ ((c // 4) % 2) + ((r + c) % 3)) % num_p
            elif "rug" in name:
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
            elif any(k in name for k in ("bowl", "cup", "apple", "pot", "pan", "plate", "milk", "bread", "cheese", "berries", "carrot")):
                d2 = (r - 16) ** 2 + (c - 16) ** 2
                if "apple" in name or "berries" in name:
                    if r < 6 and 14 <= c <= 17:
                        val = 0
                    elif d2 > 200:
                        val = 1
                    elif (r * 11 + c * 7) % 5 == 0:
                        val = 3
                    else:
                        val = 2
                elif "milk" in name or "cheese" in name:
                    val = 0 if (r in (0, rows - 1) or c in (0, cols - 1)) else (3 if (r + c) % 8 == 0 else 1)
                elif "bread" in name:
                    val = 2 if d2 <= 180 else (1 if d2 <= 240 else 0)
                elif "carrot" in name:
                    val = 2 if abs(r - c) <= 4 and 6 <= r <= 26 else (0 if r < 6 else 1)
                elif "pot" in name or "pan" in name:
                    val = 3 if 64 <= d2 <= 144 else (2 if d2 <= 64 else 0)
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
            elif "art" in name:
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
    """Her home, delivered from Eve's map (docs/GUALA_WORLD_EXPANSION_
    BLUEPRINT_20260831.md): a 20m x 16m lot — nine places including a
    full-width backyard under a high sky, a hallway spine wide enough
    for three bodies abreast, her own room with window wall, curtains,
    wall art and a toy chest, a library, a television room, a dining
    room, and the two absence rooms with an address. Every corridor
    keeps the five-body law (>= 1500mm clear); every thing is declared
    physically in all of her senses; nothing is mimed."""

    from dsf_ai_service.substrate.embodiment_world import (
        AirVolumeState,
        EmbodiedObject,
        ObjectMaterialState,
        PhysicalPortal,
        PhysicalRegion,
        PositionMM,
        RoomBoundsMM,
    )

    # (id, min_x, min_y, max_x, max_y, ceiling, light)
    plan = (
        ("kitchen",       0,      0,  7_000,  5_000, HOME_CEILING_MM, 900_000),
        ("dining",        7_000,  0, 12_000,  5_000, HOME_CEILING_MM, 820_000),
        ("daddys-room",  12_000,  0, 16_000,  5_000, HOME_CEILING_MM, 700_000),
        ("wcs-room",     16_000,  0, 20_000,  5_000, HOME_CEILING_MM, 700_000),
        ("her-room",      0,  5_000,  5_600, 10_000, HOME_CEILING_MM, 780_000),
        ("hallway",       5_600, 5_000, 9_000, 10_000, HOME_CEILING_MM, 760_000),
        ("library",       9_000, 5_000, 14_000, 10_000, HOME_CEILING_MM, 800_000),
        ("tv-room",      14_000, 5_000, 20_000, 10_000, HOME_CEILING_MM, 740_000),
        # The backyard's ceiling is the sky: tall, bright, outdoors.
        ("backyard",      0, 10_000, 20_000, 16_000, BACKYARD_SKY_MM, 950_000),
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
                (480_000,) * 6 if name == "backyard" else (620_000,) * 6
            ),
            illumination_ppm=(light,) * 6,
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
    furniture = (
        # kitchen: authentic domestic layout with counters, appliances, cookware, and food variety
        ("pantry",            700,    600, 350, 25_000, (580_000, 520_000, 460_000, 420_000, 380_000, 350_000)),
        ("cheese",            600,  1_300,  80,    250, (880_000, 780_000, 350_000, 220_000, 180_000, 150_000)),
        ("refrigerator",      700,  2_000, 450, 60_000, (880_000, 890_000, 900_000, 910_000, 920_000, 920_000)),
        ("milk",              600,  2_800,  80,  1_000, (850_000, 850_000, 860_000, 850_000, 840_000, 830_000)),
        ("kitchen-counter", 1_000,  4_500, 500, 40_000, (620_000, 580_000, 520_000, 480_000, 440_000, 400_000)),
        ("pan",             1_800,  4_600, 130,    900, (280_000, 270_000, 260_000, 250_000, 240_000, 230_000)),
        ("pot",             2_200,  4_600, 140,  1_200, (820_000, 840_000, 850_000, 860_000, 870_000, 880_000)),
        ("carrot",          2_600,  4_600,  60,    120, (850_000, 420_000, 120_000,  80_000,  60_000,  50_000)),
        ("stove",           1_600,    600, 400, 45_000, (250_000, 240_000, 230_000, 220_000, 210_000, 200_000)),
        ("bowl",            2_400,    600, 150,    700, (920_000, 910_000, 900_000, 880_000, 860_000, 840_000)),
        ("berries",         3_000,    600,  80,    200, (650_000, 150_000, 350_000, 400_000, 420_000, 450_000)),
        ("kitchen-cabinet", 4_000,    600, 400, 30_000, (650_000, 600_000, 540_000, 480_000, 440_000, 400_000)),
        ("cup",             4_800,    600, 100,    300, (880_000, 870_000, 860_000, 840_000, 820_000, 800_000)),
        ("apple",           5_650,    900,  90,    180, (820_000, 260_000, 190_000, 170_000, 160_000, 150_000)),
        ("table",           3_500,  2_500, 600, 28_000, (700_000, 620_000, 520_000, 450_000, 410_000, 390_000)),
        ("table-chair",     3_500,  1_500, 280,  6_000, (300_000, 260_000, 240_000, 220_000, 210_000, 200_000)),
        ("bread",           2_500,  2_500, 100,    450, (750_000, 580_000, 420_000, 320_000, 260_000, 220_000)),
        ("plate",           4_500,  2_500, 120,    350, (940_000, 940_000, 930_000, 920_000, 910_000, 900_000)),
        # her room: bed wall, soft things, desk corner, art at eye height.
        ("bed",             1_200,  8_800, 900, 40_000, (760_000, 720_000, 690_000, 640_000, 600_000, 560_000)),
        ("pillow",          1_200,  7_600, 260,  1_200, (900_000, 890_000, 880_000, 860_000, 840_000, 820_000)),
        ("blanket",         3_400,  9_300, 300,    900, (860_000, 620_000, 540_000, 500_000, 470_000, 450_000)),
        ("toy-bear",        4_800,  9_200, 180,    400, (520_000, 380_000, 300_000, 260_000, 240_000, 220_000)),
        ("toy-chest",       1_000,  5_600, 500,  8_000, (560_000, 430_000, 340_000, 300_000, 280_000, 260_000)),
        ("desk",            4_000,  6_400, 800, 32_000, (430_000, 330_000, 260_000, 220_000, 200_000, 190_000)),
        ("desk-chair",      5_150,  6_400, 320,  6_000, (300_000, 260_000, 240_000, 220_000, 210_000, 200_000)),
        ("curtains",        2_800,  9_700, 250,  1_500, (930_000, 760_000, 620_000, 540_000, 500_000, 470_000)),
        ("wall-art-shapes", 300,    7_000, 150,    600, (950_000, 300_000, 850_000, 200_000, 750_000, 250_000)),
        ("wall-art-weather", 300,   6_100, 150,    600, (350_000, 550_000, 900_000, 400_000, 650_000, 300_000)),
        ("glow-stars",      2_200,  9_700, 120,    300, (940_000, 930_000, 700_000, 400_000, 300_000, 260_000)),
        # library: shelves on the north wall, the reading lamp, a book home.
        ("shelf-a",        10_000,  9_500, 400, 30_000, (500_000, 400_000, 330_000, 290_000, 270_000, 250_000)),
        ("shelf-b",        12_500,  9_500, 400, 30_000, (500_000, 400_000, 330_000, 290_000, 270_000, 250_000)),
        ("book",           12_000,  7_500, 140,    900, (640_000, 520_000, 420_000, 360_000, 330_000, 310_000)),
        ("lamp",           13_500,  5_400, 180,  2_200, (880_000, 850_000, 780_000, 700_000, 650_000, 620_000)),
        # tv room: the watching place.
        ("television",     17_000,  9_200, 700, 12_000, (140_000, 140_000, 150_000, 160_000, 170_000, 180_000)),
        ("radio",          15_400,  9_400, 150,  1_200, (250_000, 240_000, 230_000, 220_000, 210_000, 200_000)),
        ("sofa",           17_000,  6_800, 950, 45_000, (360_000, 330_000, 380_000, 420_000, 430_000, 420_000)),
        ("rug",            15_000,  6_000, 600,  5_000, (540_000, 420_000, 360_000, 330_000, 320_000, 310_000)),
        # dining room.
        ("dining-table",    9_500,  2_500, 900, 30_000, (700_000, 620_000, 520_000, 450_000, 410_000, 390_000)),
        ("dining-chair",    9_500,  4_200, 320,  6_000, (300_000, 260_000, 240_000, 220_000, 210_000, 200_000)),
        # backyard: slide, swing, sandbox, garden patch under the sky.
        ("slide",           3_000, 13_500, 900, 25_000, (700_000, 720_000, 740_000, 700_000, 650_000, 600_000)),
        ("swing",           7_000, 14_000, 700, 15_000, (480_000, 430_000, 380_000, 340_000, 320_000, 300_000)),
        ("sandbox",        11_500, 13_500, 1_100, 60_000, (820_000, 780_000, 700_000, 620_000, 560_000, 520_000)),
        ("garden-patch",   16_500, 13_500, 1_200, 80_000, (300_000, 380_000, 300_000, 260_000, 240_000, 220_000)),
    )
    # (release ng/s per odour channel, tastants ug, surface mK, compliance
    #  ppm, roughness um, moisture ppm) — same channel meanings as before:
    #  0 fruit ester - 1 cooked savoury - 2 dairy fat - 3 wood/earth
    #  4 fabric dust - 5 paper ink - 6 warm electronics - 7 soap
    material_of = {
        "kitchen-counter": ((0, 0, 0, 600, 50, 0, 0, 100), (0, 0, 0, 1_500, 0),        294_000, 40_000, 30, 20_000),
        "refrigerator":    ((0, 0, 0, 0, 10, 0, 100, 200), (0, 0, 0, 500, 0),          277_000, 20_000, 10, 5_000),
        "stove":           ((0, 400, 0, 0, 0, 0, 200, 0),   (0, 0, 0, 200, 0),          330_000, 15_000, 15, 2_000),
        "kitchen-cabinet": ((0, 0, 0, 700, 60, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "pantry":          ((0, 0, 0, 800, 100, 0, 0, 0),  (0, 0, 0, 1_200, 0),        294_000, 40_000, 45, 15_000),
        "pot":             ((0, 100, 0, 0, 0, 0, 0, 100),   (0, 0, 0, 100, 0),          320_000, 10_000, 5, 2_000),
        "pan":             ((0, 150, 0, 0, 0, 0, 0, 50),    (0, 0, 0, 100, 0),          295_000, 10_000, 20, 2_000),
        "plate":           ((0, 0, 0, 0, 0, 0, 0, 200),     (0, 0, 0, 50, 0),           293_000, 15_000, 4, 1_000),
        "milk":            ((0, 0, 3_000, 0, 0, 0, 0, 0),   (50_000, 0, 20_000, 0, 0),   277_000, 800_000, 5, 950_000),
        "bread":           ((0, 2_000, 0, 200, 0, 0, 0, 0), (30_000, 10_000, 5_000, 800, 0), 294_000, 400_000, 120, 350_000),
        "cheese":          ((0, 1_200, 2_500, 0, 0, 0, 0, 0), (5_000, 40_000, 35_000, 500, 0), 277_000, 250_000, 30, 400_000),
        "berries":         ((3_800, 0, 0, 0, 0, 0, 0, 0),   (120_000, 100, 15_000, 600, 15_000), 290_000, 200_000, 25, 880_000),
        "carrot":          ((800, 0, 0, 1_200, 0, 0, 0, 0), (60_000, 200, 5_000, 1_500, 500), 291_000, 150_000, 40, 820_000),
        "bed":             ((0, 0, 0, 0, 900, 0, 0, 120),   (0, 300, 0, 800, 0),        294_000, 600_000, 200, 55_000),
        "pillow":          ((0, 0, 0, 0, 600, 0, 0, 300),   (0, 300, 0, 800, 0),        294_000, 900_000, 120, 48_000),
        "blanket":         ((0, 0, 0, 0, 1_000, 0, 0, 150), (0, 300, 0, 800, 0),        294_000, 850_000, 150, 50_000),
        "toy-bear":        ((0, 0, 0, 0, 1_200, 0, 0, 60),  (0, 300, 0, 900, 0),        294_000, 800_000, 300, 42_000),
        "toy-chest":       ((0, 0, 0, 600, 80, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 50_000, 60, 20_000),
        "desk":            ((0, 0, 0, 700, 60, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "desk-chair":      ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "curtains":        ((0, 0, 0, 0, 700, 0, 0, 100),   (0, 0, 0, 600, 0),          293_000, 800_000, 120, 45_000),
        "wall-art-shapes": ((0, 0, 0, 30, 20, 700, 0, 0),   (0, 0, 0, 1_800, 0),        294_000, 60_000, 50, 18_000),
        "wall-art-weather": ((0, 0, 0, 30, 20, 700, 0, 0),  (0, 0, 0, 1_800, 0),        294_000, 60_000, 50, 18_000),
        "glow-stars":      ((0, 0, 0, 0, 10, 0, 120, 0),    (0, 0, 0, 900, 0),          294_000, 30_000, 10, 3_000),
        "book":            ((0, 0, 0, 40, 30, 900, 0, 0),   (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "shelf-a":         ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "shelf-b":         ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "lamp":            ((0, 0, 0, 0, 20, 0, 260, 0),    (0, 0, 0, 400, 0),          310_000, 20_000, 10, 2_000),
        "television":      ((0, 0, 0, 0, 40, 0, 700, 0),    (0, 0, 0, 400, 0),          306_000, 20_000, 5, 1_000),
        "radio":           ((0, 0, 0, 0, 40, 0, 300, 0),    (0, 0, 0, 400, 0),          296_000, 20_000, 8, 1_000),
        "sofa":            ((0, 0, 0, 120, 1_500, 0, 0, 90), (0, 300, 0, 800, 0),       294_000, 700_000, 400, 52_000),
        "rug":             ((0, 0, 0, 0, 2_200, 0, 0, 40),  (0, 300, 0, 900, 0),        294_000, 500_000, 800, 46_000),
        "table":           ((0, 0, 0, 800, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "table-chair":     ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "dining-table":    ((0, 0, 0, 800, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "dining-chair":    ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "bowl":            ((0, 300, 120, 0, 0, 0, 0, 200), (400, 900, 100, 200, 1_200), 294_000, 30_000, 8, 90_000),
        "apple":           ((4_200, 0, 0, 0, 0, 0, 0, 0),   (140_000, 200, 26_000, 900, 300), 292_000, 120_000, 15, 850_000),
        "cup":             ((0, 60, 40, 0, 0, 0, 0, 400),   (0, 0, 0, 0, 0),            291_000, 25_000, 6, 900_000),
        "slide":           ((0, 0, 0, 0, 30, 0, 80, 0),     (0, 0, 0, 300, 0),          288_000, 15_000, 8, 10_000),
        "swing":           ((0, 0, 0, 300, 400, 0, 0, 0),   (0, 200, 0, 900, 0),        288_000, 250_000, 300, 30_000),
        "sandbox":         ((0, 0, 0, 100, 600, 0, 0, 0),   (0, 100, 0, 400, 0),        290_000, 40_000, 900, 25_000),
        "garden-patch":    ((0, 0, 0, 1_600, 300, 0, 0, 0), (0, 100, 200, 700, 100),    289_000, 450_000, 700, 320_000),
    }
    reservoir_seconds = 864_000
    # Things that give off their own light (the emitter law): the lamp
    # shines warm, the glow stars glow softly — visible when her room
    # goes dark because emission does not fade with the room's light.
    emission_of = {
        "lamp": (620_000, 540_000, 380_000, 220_000, 160_000, 120_000),
        "glow-stars": (30_000, 90_000, 120_000, 60_000, 20_000, 10_000),
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
    return regions, portals, objects


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
    authority.restore_encoded(
        encoded_world,
        allow_physical_return_migration=migrate_physical_return,
    )
    if not migrate_physical_return and bytes(authority.encoded_snapshot()) != encoded_world:
        raise RuntimeError("ordinary home-world restore changed canonical bytes")
    if not any(
        item.object_id == HOME_BOOK_OBJECT_ID
        for item in authority.observation_snapshot().objects
    ):
        raise RuntimeError("the persistent home lost its physical book")
    return authority
