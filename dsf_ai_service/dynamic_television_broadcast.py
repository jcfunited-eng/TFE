"""Dynamic Multi-Channel Television Broadcast System.

Provides 3 distinct environmental broadcast channels for the TV Room television:
- Channel 0: Boring (monotone 60 Hz hum, low-contrast static noise, inducing habituation and negative space avoidance).
- Channel 1: Fun / Cartoon (high-contrast vibrant bouncing geometric shapes, rhythmic pentatonic melodic chime, driving visual tracking).
- Channel 2: Educational (Symbolic orthographic letter/word glyphs with synchronized spoken phonetic formants, stimulating Asset 6 cortex).

Includes caretaker and remote-control channel switching dynamics, nocturnal reset, and authentic physical field generation:
- Optical: 32x32 ObjectOpticalSurface screen projection.
- Acoustic: 16 kHz signed 16-bit PCM audio waves for room sound propagation.
"""

from __future__ import annotations

import enum
import math
import struct
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from dsf_ai_service.guala_voice import PITCHES_DECIHERTZ, VOWELS, syllable_pcm
from dsf_ai_service.orthographic_sensory_transducer import (
    GLYPH_STROKES,
    OrthographicSensoryTransducer,
    _point_to_arc_distance,
    _point_to_segment_distance,
)
from dsf_ai_service.substrate.embodiment_world import ObjectOpticalSurface


class TVChannel(enum.IntEnum):
    BORING = 0
    CARTOON = 1
    EDUCATIONAL = 2


CHANNEL_NAMES: dict[int, str] = {
    TVChannel.BORING: "Boring Static / Monotone Hum",
    TVChannel.CARTOON: "Fun Cartoon / Melodic Rhythm",
    TVChannel.EDUCATIONAL: "Educational Phonetics / Asset 6",
}

# ---------------------------------------------------------------------------
# Channel Color Palettes (6-band Spectral Reflectance PPM)
# ---------------------------------------------------------------------------

# Channel 0: Low-contrast neutral gray shades
PALETTE_BORING = (
    (120_000, 120_000, 120_000, 120_000, 120_000, 120_000),
    (140_000, 140_000, 140_000, 140_000, 140_000, 140_000),
    (160_000, 160_000, 160_000, 160_000, 160_000, 160_000),
    (180_000, 180_000, 180_000, 180_000, 180_000, 180_000),
)

# Channel 1: High-contrast primary cartoon colors
PALETTE_CARTOON = (
    (30_000, 40_000, 200_000, 300_000, 600_000, 800_000),    # 0: Deep navy blue
    (950_000, 900_000, 200_000, 120_000, 90_000, 70_000),    # 1: Bright sunshine yellow
    (850_000, 120_000, 90_000, 70_000, 60_000, 50_000),      # 2: Vivid crimson red
    (80_000, 750_000, 650_000, 200_000, 120_000, 90_000),    # 3: Vibrant emerald/cyan
)

# Channel 2: Educational high-contrast reading screen
PALETTE_EDUCATIONAL = (
    (40_000, 40_000, 80_000, 100_000, 120_000, 140_000),     # 0: Dark slate background
    (80_000, 80_000, 150_000, 180_000, 200_000, 220_000),    # 1: Subtle frame boundary
    (200_000, 350_000, 600_000, 750_000, 850_000, 900_000),   # 2: Educational blue highlight
    (950_000, 950_000, 950_000, 950_000, 950_000, 950_000),   # 3: Crisp high-luminance white text
)

# Educational vocabulary sequence
EDUCATIONAL_CURRICULUM_WORDS = ("A", "APPLE", "B", "BELL", "C", "BED", "D", "BOOK")

# Cartoon melodic scale (frequencies in Hz: G4, A4, C5, D5, E5)
CARTOON_MELODY_HZ = (392.0, 440.0, 523.25, 587.33, 659.25, 587.33, 523.25, 440.0)


# ---------------------------------------------------------------------------
# TelevisionBroadcast Class
# ---------------------------------------------------------------------------

@dataclass
class TelevisionBroadcast:
    """Dynamic television broadcast generator for the TV room."""

    channel: TVChannel = TVChannel.CARTOON
    frame_index: int = 0
    is_powered: bool = True
    _transducer: OrthographicSensoryTransducer = field(default_factory=OrthographicSensoryTransducer)

    def switch_channel(self, target: int | None = None) -> int:
        """Switch TV channels: cycles 0 -> 1 -> 2 -> 0 or sets specific channel."""
        if target is not None:
            self.channel = TVChannel(target % 3)
        else:
            self.channel = TVChannel((int(self.channel) + 1) % 3)
        return int(self.channel)

    def toggle_channel(self) -> int:
        """Cycle to next channel (0 -> 1 -> 2 -> 0) via remote control."""
        return self.switch_channel()

    def reset_to_boring(self) -> None:
        """Reset TV back to Channel 0 (Boring static) during nocturnal house cleaning."""
        self.channel = TVChannel.BORING

    def step(self) -> None:
        """Advance broadcast by one 250 ms beat."""
        self.frame_index += 1

    def render_screen_surface(self, columns: int = 32, rows: int = 32) -> ObjectOpticalSurface:
        """Render the 32x32 optical surface for the active broadcast channel."""
        if not self.is_powered:
            # Powered off: dark matte glass with subtle border
            palette = ((20_000,) * 6, (30_000,) * 6)
            cells = [0] * (columns * rows)
            for c in range(columns):
                cells[c] = 1
                cells[(rows - 1) * columns + c] = 1
            for r in range(rows):
                cells[r * columns] = 1
                cells[r * columns + (columns - 1)] = 1
            surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
            surface.verify()
            return surface

        if self.channel == TVChannel.BORING:
            palette = PALETTE_BORING
            cells = []
            # Low-contrast deterministic static noise
            for r in range(rows):
                for c in range(columns):
                    val = (r * 7 + c * 13 + self.frame_index * 3) % 4
                    cells.append(val)

        elif self.channel == TVChannel.CARTOON:
            palette = PALETTE_CARTOON
            cells = [0] * (columns * rows)
            # Ground bar at bottom
            for c in range(columns):
                cells[(rows - 1) * columns + c] = 3
                cells[(rows - 2) * columns + c] = 3

            # Animated bouncing circular character
            time_rad = self.frame_index * 0.35
            center_x = 16.0 + 9.0 * math.sin(time_rad)
            center_y = 14.0 + 7.0 * math.cos(time_rad * 1.5)
            radius = 5.0

            for r in range(rows - 2):
                for c in range(columns):
                    d2 = (c - center_x) ** 2 + (r - center_y) ** 2
                    if d2 <= radius ** 2:
                        # Ball body (yellow)
                        cells[r * columns + c] = 1
                    elif d2 <= (radius + 2.0) ** 2:
                        # Outer halo/outline (red)
                        cells[r * columns + c] = 2

        elif self.channel == TVChannel.EDUCATIONAL:
            palette = PALETTE_EDUCATIONAL
            cells = [0] * (columns * rows)
            # Border frame
            for r in range(rows):
                for c in range(columns):
                    if r in (0, rows - 1) or c in (0, columns - 1):
                        cells[r * columns + c] = 1

            # Render current lesson glyph
            word_idx = (self.frame_index // 8) % len(EDUCATIONAL_CURRICULUM_WORDS)
            word = EDUCATIONAL_CURRICULUM_WORDS[word_idx]
            display_char = word[0]

            # Rasterize glyph onto 32x32 surface
            glyph_bitmap_64 = self._transducer.rasterize_glyph_bitmap(display_char)
            # Downsample 64x64 to 32x32
            for r in range(1, rows - 1):
                r64 = r * 2
                for c in range(1, columns - 1):
                    c64 = c * 2
                    patch = glyph_bitmap_64[r64:r64 + 2, c64:c64 + 2]
                    if patch.mean() > 0.4:
                        cells[r * columns + c] = 3
                    elif patch.mean() > 0.1:
                        cells[r * columns + c] = 2

        # Ensure all palette indices are present to satisfy physical optical verification
        used = set(cells)
        for p_i in range(len(palette)):
            if p_i not in used:
                cells[p_i] = p_i

        surface = ObjectOpticalSurface(columns, rows, palette, tuple(cells))
        surface.verify()
        return surface

    def generate_audio_pcm(self, samples: int = 4000) -> bytes:
        """Generate 16 kHz signed 16-bit PCM audio for one 250 ms beat."""
        if not self.is_powered:
            return b"\x00\x00" * samples

        rate = 16_000

        if self.channel == TVChannel.BORING:
            # Low monotone 60 Hz hum + 120 Hz soft harmonic at low volume
            raw = []
            amp = 700.0  # gentle low-level ambient drone (~ -33 dB)
            for i in range(samples):
                t = i / rate
                val = amp * (math.sin(2.0 * math.pi * 60.0 * t) + 0.35 * math.sin(2.0 * math.pi * 120.0 * t))
                raw.append(int(round(val)))
            return struct.pack(f"<{samples}h", *raw)

        elif self.channel == TVChannel.CARTOON:
            # Upbeat musical chime from pentatonic melody
            melody_idx = self.frame_index % len(CARTOON_MELODY_HZ)
            freq = CARTOON_MELODY_HZ[melody_idx]
            amp = 5_000.0
            raw = []
            for i in range(samples):
                t = i / rate
                # Envelope: quick attack, natural exponential decay
                env = math.exp(-3.5 * (i / samples))
                val = amp * env * (
                    math.sin(2.0 * math.pi * freq * t)
                    + 0.4 * math.sin(2.0 * math.pi * 2.0 * freq * t)
                    + 0.15 * math.sin(2.0 * math.pi * 3.0 * freq * t)
                )
                clamped = max(-32768, min(32767, int(round(val))))
                raw.append(clamped)
            return struct.pack(f"<{samples}h", *raw)

        elif self.channel == TVChannel.EDUCATIONAL:
            # Pronounce lesson word using Asset 6 phonetic speech synthesis
            word_idx = (self.frame_index // 8) % len(EDUCATIONAL_CURRICULUM_WORDS)
            word = EDUCATIONAL_CURRICULUM_WORDS[word_idx]
            pcm = self._transducer.synthesize_word_pcm(word, seed=self.frame_index)
            if len(pcm) >= samples * 2:
                return pcm[:samples * 2]
            return pcm + b"\x00\x00" * (samples - len(pcm) // 2)

        return b"\x00\x00" * samples

    def get_emission_ppm(self) -> tuple[int, int, int, int, int, int]:
        """Emission spectrum in PPM for screen lighting."""
        if not self.is_powered:
            return (0, 0, 0, 0, 0, 0)
        if self.channel == TVChannel.BORING:
            return (150_000, 150_000, 150_000, 150_000, 150_000, 150_000)
        if self.channel == TVChannel.CARTOON:
            return (480_000, 420_000, 500_000, 480_000, 450_000, 400_000)
        # Educational
        return (420_000, 420_000, 450_000, 480_000, 500_000, 520_000)


__all__ = (
    "CHANNEL_NAMES",
    "PALETTE_BORING",
    "PALETTE_CARTOON",
    "PALETTE_EDUCATIONAL",
    "TVChannel",
    "TelevisionBroadcast",
)
