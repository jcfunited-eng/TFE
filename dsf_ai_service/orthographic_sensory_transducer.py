"""Symbolic Orthographic-to-Phonetic Sensory Cortex (Cognitive Asset 6).

Exogenous sensory transducer converting written educational curricula, books,
and printed materials into continuous physical sensory fields for Guala's
retinal, cochlear, and somatic receptor channels.

Physical and Architectural Invariants:
1. Strict Sensory Containment: Operates strictly at the organism's environmental
   boundary (like the cornea or cochlear basilar membrane). Never dictates motor
   policies or touches internal cognitive state (L0-L4 kernel remains unchanged).
2. Deterministic Multimodal Transduction:
   - Optical: 2D vector stroke rasterization into 64x64 ExactGlyphGeometry and 135-site retina.
   - Auditory: Articulatory acoustic formant synthesis (16 kHz PCM) across 32 cochlear ERB channels.
   - Physical Invariants: 5-modality physical grounding (texture, warmth, compliance, odour, taste, optical reflectance)
     matching home-world physics for concrete nouns and sensory adjectives.
3. Zero statistical ML, neural networks, or heuristics. 100% reproducible physics.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
import math
import struct
from typing import Any, Mapping, Sequence

import numpy as np

from dsf_ai_service.guala_cochlea import (
    CHANNELS_PER_EAR,
    SAMPLE_RATE_HZ,
    one_self_hearing_hop,
)
from dsf_ai_service.guala_functional_organism import (
    EAR_BANDS,
    cochlear_profile,
    ear_bands,
)
from dsf_ai_service.guala_voice import (
    ONSETS,
    PITCHES_DECIHERTZ,
    VOWELS,
    syllable_pcm,
)
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import (
    EXTERNAL_RGB_VALUE_COUNT,
    LeanSensoryOccurrence,
)

# ---------------------------------------------------------------------------
# Physical Constants & Geometrical Parameters
# ---------------------------------------------------------------------------

GEOMETRY_SCHEMA: str = "guala.embodied_glyph.geometry.v1"
VISUAL_WIDTH: int = 64
VISUAL_HEIGHT: int = 64
PACKED_GEOMETRY_BYTES: int = VISUAL_WIDTH * VISUAL_HEIGHT // 8  # 512 bytes

RETINA_ROWS: int = 3
RETINA_COLUMNS: int = 9
RETINA_FINE_ROWS: int = 6
RETINA_FINE_COLUMNS: int = 18
RETINA_RECEPTOR_COUNT: int = RETINA_ROWS * RETINA_COLUMNS  # 27
RETINA_FINE_RECEPTOR_COUNT: int = RETINA_FINE_ROWS * RETINA_FINE_COLUMNS  # 108
RETINA_TOTAL_RECEPTOR_COUNT: int = RETINA_RECEPTOR_COUNT + RETINA_FINE_RECEPTOR_COUNT  # 135

DEFAULT_FOREGROUND_LUMINANCE: int = 240
DEFAULT_BACKGROUND_LUMINANCE: int = 15
GLYPH_STROKE_THICKNESS: float = 4.0
BEAT_SAMPLE_COUNT: int = 4_000  # 250 ms at 16,000 Hz
DEFAULT_VOICE_PITCH_DECIHERTZ: int = 3600  # 360.0 Hz (child vocalization)


# ---------------------------------------------------------------------------
# ExactGlyphGeometry Data Structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ExactGlyphGeometry:
    """Exact binary material geometry; it carries no glyph identity."""

    packed_foreground_bits: bytes = field(repr=False)
    foreground_luminance: int
    background_luminance: int
    foreground_pixel_count: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        packed_foreground_bits: bytes,
        foreground_luminance: int,
        background_luminance: int,
    ) -> "ExactGlyphGeometry":
        if (
            not isinstance(packed_foreground_bits, bytes)
            or len(packed_foreground_bits) != PACKED_GEOMETRY_BYTES
        ):
            raise ValueError("glyph geometry must be one exact 64x64 bit plane")
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 255
            for value in (foreground_luminance, background_luminance)
        ) or foreground_luminance == background_luminance:
            raise ValueError("glyph material luminance boundary changed")
        unpacked = np.unpackbits(
            np.frombuffer(packed_foreground_bits, dtype=np.uint8),
            bitorder="big",
        )
        count = int(unpacked.sum())
        if not 0 < count < VISUAL_WIDTH * VISUAL_HEIGHT:
            raise ValueError("glyph material must contain foreground and background")
        payload = {
            "background_luminance": background_luminance,
            "foreground_luminance": foreground_luminance,
            "foreground_pixel_count": count,
            "height": VISUAL_HEIGHT,
            "packed_foreground_bits_base64": base64.b64encode(
                packed_foreground_bits
            ).decode("ascii"),
            "schema": GEOMETRY_SCHEMA,
            "width": VISUAL_WIDTH,
        }
        body = json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        receipt = hashlib.sha256(body).hexdigest()
        return cls(
            packed_foreground_bits=packed_foreground_bits,
            foreground_luminance=foreground_luminance,
            background_luminance=background_luminance,
            foreground_pixel_count=count,
            authority_receipt_sha256=receipt,
        )

    def payload(self) -> dict[str, object]:
        return {
            "background_luminance": self.background_luminance,
            "foreground_luminance": self.foreground_luminance,
            "foreground_pixel_count": self.foreground_pixel_count,
            "height": VISUAL_HEIGHT,
            "packed_foreground_bits_base64": base64.b64encode(
                self.packed_foreground_bits
            ).decode("ascii"),
            "schema": GEOMETRY_SCHEMA,
            "width": VISUAL_WIDTH,
        }


# ---------------------------------------------------------------------------
# Physical Invariant Tables (Home-World Matching Materials)
# ---------------------------------------------------------------------------

PHYSICAL_NOUN_AFFORDANCES: dict[str, dict[str, Any]] = {
    "apple": {
        "touch_texture": 0.08,
        "touch_warmth": 0.45,
        "contact_compliance": 0.35,
        "smell_odour": 0.70,
        "taste_residue": 0.85,
        "optical_reflectance": (420_000, 110_000, 90_000, 80_000, 70_000, 60_000),
    },
    "book": {
        "touch_texture": 0.25,
        "touch_warmth": 0.45,
        "contact_compliance": 0.20,
        "smell_odour": 0.35,
        "taste_residue": 0.00,
        "optical_reflectance": (220_000, 180_000, 140_000, 110_000, 90_000, 80_000),
    },
    "daddys-book": {
        "touch_texture": 0.28,
        "touch_warmth": 0.45,
        "contact_compliance": 0.20,
        "smell_odour": 0.40,
        "taste_residue": 0.00,
        "optical_reflectance": (240_000, 190_000, 150_000, 120_000, 95_000, 85_000),
    },
    "blanket": {
        "touch_texture": 0.15,
        "touch_warmth": 0.75,
        "contact_compliance": 0.90,
        "smell_odour": 0.20,
        "taste_residue": 0.00,
        "optical_reflectance": (180_000, 220_000, 320_000, 280_000, 150_000, 120_000),
    },
    "pillow": {
        "touch_texture": 0.10,
        "touch_warmth": 0.65,
        "contact_compliance": 0.95,
        "smell_odour": 0.15,
        "taste_residue": 0.00,
        "optical_reflectance": (850_000, 850_000, 850_000, 850_000, 850_000, 850_000),
    },
    "bell": {
        "touch_texture": 0.04,
        "touch_warmth": 0.25,
        "contact_compliance": 0.00,
        "smell_odour": 0.05,
        "taste_residue": 0.10,
        "optical_reflectance": (550_000, 480_000, 200_000, 100_000, 60_000, 50_000),
    },
    "music-box": {
        "touch_texture": 0.18,
        "touch_warmth": 0.35,
        "contact_compliance": 0.05,
        "smell_odour": 0.15,
        "taste_residue": 0.00,
        "optical_reflectance": (380_000, 300_000, 190_000, 130_000, 90_000, 80_000),
    },
    "bed": {
        "touch_texture": 0.22,
        "touch_warmth": 0.55,
        "contact_compliance": 0.80,
        "smell_odour": 0.20,
        "taste_residue": 0.00,
        "optical_reflectance": (350_000, 280_000, 180_000, 120_000, 90_000, 80_000),
    },
    "table": {
        "touch_texture": 0.30,
        "touch_warmth": 0.45,
        "contact_compliance": 0.02,
        "smell_odour": 0.25,
        "taste_residue": 0.00,
        "optical_reflectance": (320_000, 260_000, 180_000, 120_000, 90_000, 80_000),
    },
    "desk": {
        "touch_texture": 0.28,
        "touch_warmth": 0.45,
        "contact_compliance": 0.02,
        "smell_odour": 0.22,
        "taste_residue": 0.00,
        "optical_reflectance": (320_000, 260_000, 180_000, 120_000, 90_000, 80_000),
    },
    "chair": {
        "touch_texture": 0.30,
        "touch_warmth": 0.45,
        "contact_compliance": 0.05,
        "smell_odour": 0.22,
        "taste_residue": 0.00,
        "optical_reflectance": (320_000, 260_000, 180_000, 120_000, 90_000, 80_000),
    },
    "toy-chest": {
        "touch_texture": 0.35,
        "touch_warmth": 0.45,
        "contact_compliance": 0.03,
        "smell_odour": 0.30,
        "taste_residue": 0.00,
        "optical_reflectance": (340_000, 270_000, 190_000, 130_000, 95_000, 85_000),
    },
    "water": {
        "touch_texture": 0.01,
        "touch_warmth": 0.30,
        "contact_compliance": 1.00,
        "smell_odour": 0.05,
        "taste_residue": 0.05,
        "optical_reflectance": (100_000, 200_000, 450_000, 500_000, 400_000, 300_000),
    },
    "milk": {
        "touch_texture": 0.02,
        "touch_warmth": 0.50,
        "contact_compliance": 1.00,
        "smell_odour": 0.45,
        "taste_residue": 0.65,
        "optical_reflectance": (880_000, 880_000, 880_000, 880_000, 880_000, 880_000),
    },
    "bread": {
        "touch_texture": 0.40,
        "touch_warmth": 0.55,
        "contact_compliance": 0.60,
        "smell_odour": 0.80,
        "taste_residue": 0.75,
        "optical_reflectance": (450_000, 350_000, 220_000, 140_000, 90_000, 70_000),
    },
    "cheese": {
        "touch_texture": 0.15,
        "touch_warmth": 0.45,
        "contact_compliance": 0.50,
        "smell_odour": 0.75,
        "taste_residue": 0.80,
        "optical_reflectance": (650_000, 580_000, 220_000, 120_000, 70_000, 60_000),
    },
    "carrot": {
        "touch_texture": 0.20,
        "touch_warmth": 0.40,
        "contact_compliance": 0.25,
        "smell_odour": 0.55,
        "taste_residue": 0.70,
        "optical_reflectance": (550_000, 280_000, 80_000, 60_000, 50_000, 40_000),
    },
}

PHYSICAL_ADJECTIVE_AFFORDANCES: dict[str, dict[str, Any]] = {
    "warm": {"touch_warmth": 0.80},
    "hot": {"touch_warmth": 0.95},
    "cold": {"touch_warmth": 0.15},
    "cool": {"touch_warmth": 0.30},
    "rough": {"touch_texture": 0.85},
    "smooth": {"touch_texture": 0.05},
    "soft": {"contact_compliance": 0.85},
    "hard": {"contact_compliance": 0.05},
    "sweet": {"taste_residue": 0.85, "smell_odour": 0.65},
    "sour": {"taste_residue": 0.70},
    "salty": {"taste_residue": 0.60},
    "bitter": {"taste_residue": 0.50},
    "fresh": {"smell_odour": 0.40},
    "red": {"optical_reflectance": (600_000, 100_000, 80_000, 60_000, 50_000, 40_000)},
    "green": {"optical_reflectance": (80_000, 500_000, 150_000, 100_000, 70_000, 50_000)},
    "blue": {"optical_reflectance": (50_000, 100_000, 350_000, 600_000, 500_000, 400_000)},
    "white": {"optical_reflectance": (900_000, 900_000, 900_000, 900_000, 900_000, 900_000)},
    "dark": {"optical_reflectance": (50_000, 50_000, 50_000, 50_000, 50_000, 50_000)},
    "black": {"optical_reflectance": (30_000, 30_000, 30_000, 30_000, 30_000, 30_000)},
}

# ---------------------------------------------------------------------------
# Canonical Phonetic Lexicon for Common Vocabulary
# ---------------------------------------------------------------------------

CANONICAL_PHONETIC_LEXICON: dict[str, tuple[tuple[str, str, int], ...]] = {
    "apple": (("", "ah", 3600), ("p", "eh", 3600), ("l", "oo", 3600)),
    "book": (("b", "oo", 3600), ("k", "oo", 3600)),
    "daddys-book": (("d", "ah", 3600), ("d", "ee", 3600), ("b", "oo", 3600)),
    "blanket": (("b", "ah", 3600), ("l", "eh", 3600), ("k", "eh", 3600), ("t", "eh", 3600)),
    "pillow": (("p", "ee", 3600), ("l", "oh", 3600)),
    "bell": (("b", "eh", 3600), ("l", "eh", 3600)),
    "music-box": (("m", "oo", 3600), ("b", "oh", 3600), ("k", "eh", 3600)),
    "bed": (("b", "eh", 3600), ("d", "eh", 3600)),
    "table": (("t", "eh", 3600), ("b", "oo", 3600), ("l", "oo", 3600)),
    "desk": (("d", "eh", 3600), ("k", "eh", 3600)),
    "chair": (("t", "eh", 3600), ("ah", "eh", 3600)),
    "toy-chest": (("t", "oh", 3600), ("k", "eh", 3600), ("t", "eh", 3600)),
    "water": (("w", "ah", 3600), ("t", "eh", 3600)),
    "milk": (("m", "ee", 3600), ("l", "oo", 3600), ("k", "oo", 3600)),
    "bread": (("b", "eh", 3600), ("d", "eh", 3600)),
    "cheese": (("t", "ee", 3600), ("d", "ee", 3600)),
    "carrot": (("k", "eh", 3600), ("t", "oh", 3600)),
    "warm": (("w", "oh", 3600), ("m", "ah", 3600)),
    "hot": (("ah", "oh", 3600), ("t", "oh", 3600)),
    "cold": (("k", "oh", 3600), ("l", "oo", 3600), ("d", "oo", 3600)),
    "cool": (("k", "oo", 3600), ("l", "oo", 3600)),
    "rough": (("w", "ah", 3600), ("p", "ah", 3600)),
    "smooth": (("m", "oo", 3600), ("d", "oo", 3600)),
    "soft": (("t", "oh", 3600), ("p", "eh", 3600)),
    "hard": (("ah", "ah", 3600), ("d", "ah", 3600)),
    "sweet": (("w", "ee", 3600), ("t", "ee", 3600)),
    "sour": (("t", "ah", 3600), ("w", "oh", 3600)),
    "salty": (("t", "oh", 3600), ("l", "ee", 3600)),
    "bitter": (("b", "ee", 3600), ("t", "eh", 3600)),
    "fresh": (("p", "eh", 3600), ("t", "eh", 3600)),
    "red": (("w", "eh", 3600), ("d", "eh", 3600)),
    "green": (("g", "ee", 3600), ("n", "ee", 3600)),
    "blue": (("b", "l", 3600), ("l", "oo", 3600)),
    "white": (("w", "ah", 3600), ("t", "ee", 3600)),
    "dark": (("d", "ah", 3600), ("k", "ah", 3600)),
    "black": (("b", "ah", 3600), ("k", "ah", 3600)),
    "the": (("d", "ah", 3600),),
    "a": (("", "ah", 3600),),
    "on": (("", "oh", 3600), ("n", "oh", 3600)),
    "in": (("", "ee", 3600), ("n", "ee", 3600)),
    "is": (("", "ee", 3600), ("d", "ee", 3600)),
    "and": (("", "ah", 3600), ("n", "ah", 3600), ("d", "ah", 3600)),
}


# ---------------------------------------------------------------------------
# Geometric Vector Stroke Primitives for Character Rasterization
# ---------------------------------------------------------------------------

GLYPH_STROKES: dict[str, list[tuple[Any, ...]]] = {
    "A": [("line", (25, 85), (50, 15)), ("line", (50, 15), (75, 85)), ("line", (35, 55), (65, 55))],
    "B": [("line", (25, 15), (25, 85)), ("line", (25, 15), (50, 15)), ("line", (25, 50), (50, 50)),
          ("line", (25, 85), (50, 85)), ("arc", (50, 32), 17, -90, 90), ("arc", (50, 68), 17, -90, 90)],
    "C": [("arc", (50, 50), 32, 45, 315)],
    "D": [("line", (25, 15), (25, 85)), ("line", (25, 15), (45, 15)), ("line", (25, 85), (45, 85)),
          ("arc", (45, 50), 35, -90, 90)],
    "E": [("line", (25, 15), (25, 85)), ("line", (25, 15), (75, 15)), ("line", (25, 50), (65, 50)),
          ("line", (25, 85), (75, 85))],
    "F": [("line", (25, 15), (25, 85)), ("line", (25, 15), (75, 15)), ("line", (25, 50), (65, 50))],
    "G": [("arc", (50, 50), 32, 45, 315), ("line", (50, 50), (75, 50)), ("line", (75, 50), (75, 75))],
    "H": [("line", (25, 15), (25, 85)), ("line", (75, 15), (75, 85)), ("line", (25, 50), (75, 50))],
    "I": [("line", (50, 15), (50, 85)), ("line", (30, 15), (70, 15)), ("line", (30, 85), (70, 85))],
    "J": [("line", (65, 15), (65, 65)), ("arc", (45, 65), 20, 0, 180)],
    "K": [("line", (25, 15), (25, 85)), ("line", (75, 15), (25, 50)), ("line", (25, 50), (75, 85))],
    "L": [("line", (25, 15), (25, 85)), ("line", (25, 85), (75, 85))],
    "M": [("line", (20, 85), (20, 15)), ("line", (20, 15), (50, 55)), ("line", (50, 55), (80, 15)),
          ("line", (80, 15), (80, 85))],
    "N": [("line", (25, 85), (25, 15)), ("line", (25, 15), (75, 85)), ("line", (75, 85), (75, 15))],
    "O": [("arc", (50, 50), 32, 0, 360)],
    "P": [("line", (25, 15), (25, 85)), ("line", (25, 15), (48, 15)), ("line", (25, 50), (48, 50)),
          ("arc", (48, 32), 17, -90, 90)],
    "Q": [("arc", (50, 50), 32, 0, 360), ("line", (55, 65), (80, 85))],
    "R": [("line", (25, 15), (25, 85)), ("line", (25, 15), (48, 15)), ("line", (25, 50), (48, 50)),
          ("arc", (48, 32), 17, -90, 90), ("line", (48, 50), (75, 85))],
    "S": [("arc", (50, 33), 18, 45, 270), ("arc", (50, 67), 18, -135, 90)],
    "T": [("line", (50, 15), (50, 85)), ("line", (20, 15), (80, 15))],
    "U": [("line", (25, 15), (25, 65)), ("line", (75, 15), (75, 65)), ("arc", (50, 65), 25, 0, 180)],
    "V": [("line", (25, 15), (50, 85)), ("line", (50, 85), (75, 15))],
    "W": [("line", (15, 15), (32, 85)), ("line", (32, 85), (50, 45)), ("line", (50, 45), (68, 85)),
          ("line", (68, 85), (85, 15))],
    "X": [("line", (25, 15), (75, 85)), ("line", (25, 85), (75, 15))],
    "Y": [("line", (25, 15), (50, 50)), ("line", (75, 15), (50, 50)), ("line", (50, 50), (50, 85))],
    "Z": [("line", (25, 15), (75, 15)), ("line", (75, 15), (25, 85)), ("line", (25, 85), (75, 85))],
    "0": [("arc", (50, 50), 32, 0, 360), ("line", (32, 68), (68, 32))],
    "1": [("line", (50, 15), (50, 85)), ("line", (35, 30), (50, 15)), ("line", (30, 85), (70, 85))],
    "2": [("arc", (50, 35), 20, -90, 90), ("line", (50, 55), (25, 85)), ("line", (25, 85), (75, 85))],
    "3": [("arc", (48, 33), 18, -90, 90), ("arc", (48, 67), 18, -90, 90), ("line", (25, 15), (48, 15)),
          ("line", (25, 85), (48, 85))],
    "4": [("line", (65, 15), (65, 85)), ("line", (65, 15), (20, 60)), ("line", (20, 60), (80, 60))],
    "5": [("line", (75, 15), (25, 15)), ("line", (25, 15), (25, 45)), ("line", (25, 45), (48, 45)),
          ("arc", (48, 65), 20, -90, 90), ("line", (25, 85), (48, 85))],
    "6": [("arc", (50, 50), 32, 90, 270), ("arc", (50, 65), 20, 0, 360)],
    "7": [("line", (25, 15), (75, 15)), ("line", (75, 15), (35, 85))],
    "8": [("arc", (50, 33), 18, 0, 360), ("arc", (50, 67), 20, 0, 360)],
    "9": [("arc", (50, 35), 20, 0, 360), ("line", (70, 35), (70, 85)), ("arc", (50, 85), 20, 0, 90)],
    ".": [("dot", (50, 82), 4)],
    ",": [("dot", (50, 80), 4), ("line", (50, 80), (45, 90))],
    "!": [("line", (50, 15), (50, 65)), ("dot", (50, 82), 4)],
    "?": [("arc", (50, 35), 18, -180, 45), ("line", (50, 53), (50, 65)), ("dot", (50, 82), 4)],
    "-": [("line", (30, 50), (70, 50))],
    ":": [("dot", (50, 35), 4), ("dot", (50, 65), 4)],
    ";": [("dot", (50, 35), 4), ("dot", (50, 75), 4), ("line", (50, 75), (45, 85))],
    " ": [("dot", (16, 16), 2), ("dot", (48, 16), 2), ("dot", (16, 48), 2), ("dot", (48, 48), 2)],
}


def _point_to_segment_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance from point (px, py) to line segment (x1, y1)-(x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-9:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _point_to_arc_distance(px: float, py: float, cx: float, cy: float, radius: float, start_deg: float, end_deg: float) -> float:
    """Euclidean distance from point (px, py) to a circular arc."""
    dx = px - cx
    dy = py - cy
    dist_to_center = math.hypot(dx, dy)
    angle_deg = math.degrees(math.atan2(dy, dx)) % 360.0

    s = start_deg % 360.0
    e = end_deg % 360.0

    in_arc = False
    if s <= e:
        in_arc = (s <= angle_deg <= e)
    else:
        in_arc = (angle_deg >= s or angle_deg <= e)

    if in_arc:
        return abs(dist_to_center - radius)

    s_rad = math.radians(s)
    e_rad = math.radians(e)
    p1_x = cx + radius * math.cos(s_rad)
    p1_y = cy + radius * math.sin(s_rad)
    p2_x = cx + radius * math.cos(e_rad)
    p2_y = cy + radius * math.sin(e_rad)
    return min(math.hypot(px - p1_x, py - p1_y), math.hypot(px - p2_x, py - p2_y))


# ---------------------------------------------------------------------------
# Transduced Sensory Frame Container
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TransducedSensoryFrame:
    """One multimodal physical sensory frame delivered to Guala's sensorium."""

    text_token: str
    optical_glyph: ExactGlyphGeometry
    sight_luminance: float
    sight_horizontal: float
    sight_vertical: float
    retinal_rgb_405: tuple[int, ...]
    acoustic_pcm_s16le: bytes
    cochlear_32_channels: tuple[float, ...]
    ear_bands_6: tuple[float, ...]
    sound_energy: float
    sound_pitch: float
    physical_affordances: dict[str, Any]

    def to_lean_sensory_occurrence(self, source: str = "text-microphone") -> LeanSensoryOccurrence:
        """Export as an authentic LeanSensoryOccurrence for the organism loop."""
        return LeanSensoryOccurrence(
            source=source,
            retina_rgb_u8=self.retinal_rgb_405,
            pressure_s16le=self.acoustic_pcm_s16le,
        )

    def to_physical_occurrence(self, source: str = "text-microphone") -> PhysicalOccurrence:
        """Export as an authentic PhysicalOccurrence for the functional physical loop."""
        return PhysicalOccurrence(
            kind="sensory",
            payload=self.to_lean_sensory_occurrence(source=source),
        )


# ---------------------------------------------------------------------------
# OrthographicSensoryTransducer Class
# ---------------------------------------------------------------------------

class OrthographicSensoryTransducer:
    """Deterministic sensory transducer converting symbolic text into physical fields."""

    def __init__(
        self,
        foreground_luminance: int = DEFAULT_FOREGROUND_LUMINANCE,
        background_luminance: int = DEFAULT_BACKGROUND_LUMINANCE,
        stroke_thickness: float = GLYPH_STROKE_THICKNESS,
    ) -> None:
        self.foreground_luminance = foreground_luminance
        self.background_luminance = background_luminance
        self.stroke_thickness = stroke_thickness

    def rasterize_glyph_bitmap(self, character: str) -> np.ndarray:
        """Rasterize one character into a 64x64 boolean foreground bitmap."""
        c = character.upper() if character.upper() in GLYPH_STROKES else " "
        strokes = GLYPH_STROKES.get(c, GLYPH_STROKES[" "])

        grid = np.zeros((VISUAL_HEIGHT, VISUAL_WIDTH), dtype=bool)
        half_th = self.stroke_thickness / 2.0

        for r in range(VISUAL_HEIGHT):
            py = (r + 0.5) * (100.0 / VISUAL_HEIGHT)
            for col in range(VISUAL_WIDTH):
                px = (col + 0.5) * (100.0 / VISUAL_WIDTH)

                is_foreground = False
                for stroke in strokes:
                    kind = stroke[0]
                    if kind == "line":
                        _k, (x1, y1), (x2, y2) = stroke
                        dist = _point_to_segment_distance(px, py, x1, y1, x2, y2)
                    elif kind == "arc":
                        _k, (cx, cy), radius, s_deg, e_deg = stroke
                        dist = _point_to_arc_distance(px, py, cx, cy, radius, s_deg, e_deg)
                    elif kind == "dot":
                        _k, (cx, cy), radius = stroke
                        dist = math.hypot(px - cx, py - cy) - radius
                    else:
                        continue

                    if dist <= half_th:
                        is_foreground = True
                        break

                grid[r, col] = is_foreground

        fg_count = int(grid.sum())
        if fg_count == 0:
            grid[16, 16] = True
            grid[48, 48] = True
        elif fg_count >= VISUAL_HEIGHT * VISUAL_WIDTH:
            grid[0, 0] = False
            grid[0, 1] = False

        return grid

    def transduce_glyph_geometry(self, character: str) -> ExactGlyphGeometry:
        """Transduce a character into an authenticated ExactGlyphGeometry."""
        grid = self.rasterize_glyph_bitmap(character)
        packed_bits = np.packbits(grid.astype(np.uint8), bitorder="big").tobytes()
        return ExactGlyphGeometry.create(
            packed_foreground_bits=packed_bits,
            foreground_luminance=self.foreground_luminance,
            background_luminance=self.background_luminance,
        )

    def project_glyph_to_retina_135(self, grid: np.ndarray) -> tuple[int, ...]:
        """Downsample 64x64 glyph grid onto 135 retinal sites (27 wide + 108 fine) and triplicate to 405 RGB."""
        # 1. Wide-field retina: 3 rows x 9 columns = 27 sites
        wide_values = []
        for r_idx in range(RETINA_ROWS):
            r0 = int(r_idx * VISUAL_HEIGHT / RETINA_ROWS)
            r1 = int((r_idx + 1) * VISUAL_HEIGHT / RETINA_ROWS)
            for c_idx in range(RETINA_COLUMNS):
                c0 = int(c_idx * VISUAL_WIDTH / RETINA_COLUMNS)
                c1 = int((c_idx + 1) * VISUAL_WIDTH / RETINA_COLUMNS)
                patch = grid[r0:r1, c0:c1]
                val = int(round(self.background_luminance + (self.foreground_luminance - self.background_luminance) * patch.mean()))
                wide_values.append(max(0, min(255, val)))

        # 2. Fine retina: 6 rows x 18 columns = 108 sites
        fine_values = []
        for r_idx in range(RETINA_FINE_ROWS):
            r0 = int(r_idx * VISUAL_HEIGHT / RETINA_FINE_ROWS)
            r1 = int((r_idx + 1) * VISUAL_HEIGHT / RETINA_FINE_ROWS)
            for c_idx in range(RETINA_FINE_COLUMNS):
                c0 = int(c_idx * VISUAL_WIDTH / RETINA_FINE_COLUMNS)
                c1 = int((c_idx + 1) * VISUAL_WIDTH / RETINA_FINE_COLUMNS)
                patch = grid[r0:r1, c0:c1]
                val = int(round(self.background_luminance + (self.foreground_luminance - self.background_luminance) * patch.mean()))
                fine_values.append(max(0, min(255, val)))

        all_135 = wide_values + fine_values
        rgb_405 = []
        for val in all_135:
            rgb_405.extend((val, val, val))
        return tuple(rgb_405)

    def compute_retinal_receptive_coordinates(self, grid: np.ndarray) -> tuple[float, float, float]:
        """Compute (sight_luminance, sight_horizontal, sight_vertical) from glyph bitmap."""
        fg_indices = np.argwhere(grid)
        if len(fg_indices) == 0:
            return 0.0, 0.0, 0.0

        mean_y, mean_x = fg_indices.mean(axis=0)
        # Normalized coordinates: center is (31.5, 31.5), range [-1.0, 1.0]
        sight_horizontal = float(round((mean_x - 31.5) / 31.5, 4))
        sight_vertical = float(round((mean_y - 31.5) / 31.5, 4))
        fg_fraction = float(len(fg_indices) / (VISUAL_HEIGHT * VISUAL_WIDTH))
        sight_luminance = float(round(fg_fraction * (self.foreground_luminance / 255.0), 4))
        return sight_luminance, sight_horizontal, sight_vertical

    def decompose_word_phonetics(self, word: str) -> tuple[tuple[str, str, int], ...]:
        """Decompose an orthographic word into articulatory syllables (onset, vowel, pitch)."""
        w = word.strip().lower()
        if w in CANONICAL_PHONETIC_LEXICON:
            return CANONICAL_PHONETIC_LEXICON[w]

        syllables: list[tuple[str, str, int]] = []
        current_onset = ""
        vowel_map = {"a": "ah", "e": "eh", "i": "ee", "o": "oh", "u": "oo", "y": "ee"}

        idx = 0
        while idx < len(w):
            char = w[idx]
            if char in vowel_map:
                vowel = vowel_map[char]
                syllables.append((current_onset, vowel, DEFAULT_VOICE_PITCH_DECIHERTZ))
                current_onset = ""
            elif char in ONSETS:
                current_onset = char
            elif char.isalpha():
                if char in ("c", "q", "x"):
                    current_onset = "k"
                elif char in ("f", "v"):
                    current_onset = "p"
                elif char in ("s", "z"):
                    current_onset = "d"
                elif char in ("j", "r"):
                    current_onset = "w"
                elif char == "h":
                    current_onset = ""
            idx += 1

        if not syllables:
            syllables.append(("", "ah", DEFAULT_VOICE_PITCH_DECIHERTZ))

        return tuple(syllables)

    def synthesize_word_pcm(self, word: str, seed: int = 0) -> bytes:
        """Synthesize word phonetics into 16 kHz signed 16-bit PCM audio."""
        syllable_specs = self.decompose_word_phonetics(word)
        pcm_chunks = []

        vowel_names = [v[0] for v in VOWELS]

        for s_idx, (onset, vowel_name, pitch) in enumerate(syllable_specs):
            o_idx = ONSETS.index(onset) if onset in ONSETS else 0
            v_idx = vowel_names.index(vowel_name) if vowel_name in vowel_names else 0
            p_val = pitch if pitch in PITCHES_DECIHERTZ else DEFAULT_VOICE_PITCH_DECIHERTZ

            drive = (p_val, v_idx, o_idx)
            s_seed = (seed * 101 + s_idx * 17) & 0x7FFFFFFF
            chunk = syllable_pcm(drive, s_seed)
            pcm_chunks.append(chunk)

        full_pcm = b"".join(pcm_chunks)
        max_bytes = BEAT_SAMPLE_COUNT * 2
        if len(full_pcm) > max_bytes:
            full_pcm = full_pcm[:max_bytes]
        elif len(full_pcm) < max_bytes:
            full_pcm = full_pcm + (b"\x00\x00" * ((max_bytes - len(full_pcm)) // 2))

        return full_pcm

    def analyze_acoustic_pcm(self, pcm_bytes: bytes) -> tuple[tuple[float, ...], tuple[float, ...], float, float]:
        """Pass PCM through cochlea to compute 32-channel envelope, 6 ear bands, energy, and pitch."""
        times, legacy, cochlea_channels, consumed = one_self_hearing_hop(pcm_bytes)
        profile_32 = cochlear_profile(cochlea_channels)
        bands_6 = ear_bands(profile_32)

        sample_count = len(pcm_bytes) // 2
        samples = struct.unpack(f"<{sample_count}h", pcm_bytes)
        energy_sum = sum(s * s for s in samples)
        rms = math.sqrt(energy_sum / max(1, sample_count)) / 32768.0
        sound_energy = float(round(rms, 4))

        dominant_channel = int(np.argmax(profile_32[:CHANNELS_PER_EAR]))
        approx_pitch = float(round(80.0 + dominant_channel * (7500.0 - 80.0) / (CHANNELS_PER_EAR - 1), 2))

        return profile_32, bands_6, sound_energy, approx_pitch

    def ground_affordances(self, token: str) -> dict[str, Any]:
        """Extract physical invariant affordances for concrete nouns and sensory adjectives."""
        cleaned = token.strip().lower()

        # Direct noun match
        if cleaned in PHYSICAL_NOUN_AFFORDANCES:
            return dict(PHYSICAL_NOUN_AFFORDANCES[cleaned])

        # Direct adjective match
        if cleaned in PHYSICAL_ADJECTIVE_AFFORDANCES:
            return dict(PHYSICAL_ADJECTIVE_AFFORDANCES[cleaned])

        # Multi-word or hyphenated matches: baseline nouns first, then modulated by adjectives
        parts = cleaned.replace("_", "-").split("-")
        nouns = [p for p in parts if p in PHYSICAL_NOUN_AFFORDANCES]
        adjectives = [p for p in parts if p in PHYSICAL_ADJECTIVE_AFFORDANCES]

        combined: dict[str, Any] = {}
        for n in nouns:
            combined.update(PHYSICAL_NOUN_AFFORDANCES[n])
        for a in adjectives:
            combined.update(PHYSICAL_ADJECTIVE_AFFORDANCES[a])

        return combined

    def transduce_token(self, token: str, seed: int = 0) -> TransducedSensoryFrame:
        """Transduce a single token into a complete TransducedSensoryFrame."""
        first_char = token[0] if token else " "
        glyph_grid = self.rasterize_glyph_bitmap(first_char)
        packed_bits = np.packbits(glyph_grid.astype(np.uint8), bitorder="big").tobytes()
        glyph_geom = ExactGlyphGeometry.create(
            packed_foreground_bits=packed_bits,
            foreground_luminance=self.foreground_luminance,
            background_luminance=self.background_luminance,
        )

        rgb_405 = self.project_glyph_to_retina_135(glyph_grid)
        s_lum, s_h, s_v = self.compute_retinal_receptive_coordinates(glyph_grid)

        pcm = self.synthesize_word_pcm(token, seed=seed)
        profile_32, bands_6, energy, pitch = self.analyze_acoustic_pcm(pcm)
        affordances = self.ground_affordances(token)

        return TransducedSensoryFrame(
            text_token=token,
            optical_glyph=glyph_geom,
            sight_luminance=s_lum,
            sight_horizontal=s_h,
            sight_vertical=s_v,
            retinal_rgb_405=rgb_405,
            acoustic_pcm_s16le=pcm,
            cochlear_32_channels=profile_32,
            ear_bands_6=bands_6,
            sound_energy=energy,
            sound_pitch=pitch,
            physical_affordances=affordances,
        )

    def transduce_sentence(self, sentence: str, base_seed: int = 0) -> tuple[TransducedSensoryFrame, ...]:
        """Transduce an educational sentence or book passage into a sequence of sensory frames."""
        tokens = [t.strip(",.!?\"';:()[]{}") for t in sentence.split() if t.strip(",.!?\"';:()[]{}")]
        frames = []
        for idx, token in enumerate(tokens):
            seed = (base_seed * 1009 + idx * 37) & 0x7FFFFFFF
            frames.append(self.transduce_token(token, seed=seed))
        return tuple(frames)


__all__ = (
    "CANONICAL_PHONETIC_LEXICON",
    "DEFAULT_BACKGROUND_LUMINANCE",
    "DEFAULT_FOREGROUND_LUMINANCE",
    "ExactGlyphGeometry",
    "GEOMETRY_SCHEMA",
    "GLYPH_STROKES",
    "OrthographicSensoryTransducer",
    "PACKED_GEOMETRY_BYTES",
    "PHYSICAL_ADJECTIVE_AFFORDANCES",
    "PHYSICAL_NOUN_AFFORDANCES",
    "RETINA_COLUMNS",
    "RETINA_FINE_COLUMNS",
    "RETINA_FINE_RECEPTOR_COUNT",
    "RETINA_FINE_ROWS",
    "RETINA_RECEPTOR_COUNT",
    "RETINA_ROWS",
    "RETINA_TOTAL_RECEPTOR_COUNT",
    "TransducedSensoryFrame",
    "VISUAL_HEIGHT",
    "VISUAL_WIDTH",
)

