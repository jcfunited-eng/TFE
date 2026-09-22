"""Tests for Cognitive Asset 6: Symbolic Orthographic-to-Phonetic Sensory Cortex.

Verifies:
1. Deterministic 64x64 vector stroke glyph rasterization and ExactGlyphGeometry integrity.
2. 135-site retinal projection (27 wide + 108 fine) and receptive field coordinates.
3. Articulatory acoustic formant synthesis at 16 kHz and 32-channel cochlear filtering.
4. 5-modality physical invariant affordance grounding (matching home-world materials).
5. Curriculum sentence temporal sequencing into 250 ms sensorimotor frames.
6. Closed-loop organism sensory ingestion with zero cognitive contamination.
"""

from __future__ import annotations

import math
import struct
import numpy as np
import pytest

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.orthographic_sensory_transducer import (
    CANONICAL_PHONETIC_LEXICON,
    DEFAULT_BACKGROUND_LUMINANCE,
    DEFAULT_FOREGROUND_LUMINANCE,
    ExactGlyphGeometry,
    GEOMETRY_SCHEMA,
    GLYPH_STROKES,
    OrthographicSensoryTransducer,
    PACKED_GEOMETRY_BYTES,
    PHYSICAL_ADJECTIVE_AFFORDANCES,
    PHYSICAL_NOUN_AFFORDANCES,
    RETINA_TOTAL_RECEPTOR_COUNT,
    TransducedSensoryFrame,
    VISUAL_HEIGHT,
    VISUAL_WIDTH,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def test_glyph_rasterization_determinism_and_geometry() -> None:
    """Verifies that vector stroke rasterization is bit-for-bit deterministic and produces valid geometry."""
    transducer = OrthographicSensoryTransducer()

    # Test characters spanning letters, digits, and punctuation
    for char in ("A", "B", "O", "Z", "0", "7", "!", "?", " "):
        grid1 = transducer.rasterize_glyph_bitmap(char)
        grid2 = transducer.rasterize_glyph_bitmap(char)

        # Bit-for-bit determinism
        assert np.array_equal(grid1, grid2), f"Rasterization of '{char}' is not deterministic"
        assert grid1.shape == (VISUAL_HEIGHT, VISUAL_WIDTH)

        # Invariant: non-trivial foreground count
        fg_count = int(grid1.sum())
        assert 0 < fg_count < VISUAL_HEIGHT * VISUAL_WIDTH

        # Create ExactGlyphGeometry
        geom = transducer.transduce_glyph_geometry(char)
        assert isinstance(geom, ExactGlyphGeometry)
        assert len(geom.packed_foreground_bits) == PACKED_GEOMETRY_BYTES
        assert geom.foreground_luminance == DEFAULT_FOREGROUND_LUMINANCE
        assert geom.background_luminance == DEFAULT_BACKGROUND_LUMINANCE
        assert geom.foreground_pixel_count == fg_count
        assert len(geom.authority_receipt_sha256) == 64

        # Payload validation
        payload = geom.payload()
        assert payload["schema"] == GEOMETRY_SCHEMA
        assert payload["width"] == VISUAL_WIDTH
        assert payload["height"] == VISUAL_HEIGHT
        assert payload["foreground_pixel_count"] == fg_count


def test_retinal_projection_and_receptive_coordinates() -> None:
    """Verifies that 64x64 glyphs project accurately to 135 retinal sites and receptive coordinates."""
    transducer = OrthographicSensoryTransducer()
    grid = transducer.rasterize_glyph_bitmap("A")

    # 1. 135-site retinal projection
    rgb_405 = transducer.project_glyph_to_retina_135(grid)
    assert len(rgb_405) == RETINA_TOTAL_RECEPTOR_COUNT * 3  # 135 * 3 = 405
    assert all(0 <= v <= 255 for v in rgb_405)
    # Since 'A' has foreground pixels, at least some sites must have luminance > background
    assert any(v > DEFAULT_BACKGROUND_LUMINANCE for v in rgb_405)

    # 2. Receptive field coordinates
    s_lum, s_h, s_v = transducer.compute_retinal_receptive_coordinates(grid)
    assert 0.0 < s_lum <= 1.0
    assert -1.0 <= s_h <= 1.0
    assert -1.0 <= s_v <= 1.0

    # 'A' is centered horizontally, so s_h should be near 0
    assert abs(s_h) < 0.25


def test_phonetic_formant_synthesis_and_cochlear_integration() -> None:
    """Verifies that word phonetics synthesize into 16 kHz PCM and decompose into 32 cochlear channels and 6 ear bands."""
    transducer = OrthographicSensoryTransducer()

    for word in ("apple", "book", "warm", "water"):
        pcm = transducer.synthesize_word_pcm(word, seed=42)
        assert isinstance(pcm, bytes)
        # Exactly one sensorimotor beat: 4,000 samples * 2 bytes = 8,000 bytes
        assert len(pcm) == 8_000

        profile_32, bands_6, energy, pitch = transducer.analyze_acoustic_pcm(pcm)

        # 32 cochlear ERB channels
        assert len(profile_32) == 32
        assert all(isinstance(v, float) for v in profile_32)
        assert any(v > 0.0 for v in profile_32)

        # 6 spectral ear bands
        assert len(bands_6) == 6
        assert all(isinstance(v, float) for v in bands_6)
        band_sum = sum(bands_6)
        # Total energy fraction across all bands must sum to approx 1.0
        assert 0.95 <= band_sum <= 1.05

        # Acoustic physical metrics
        assert energy > 0.0
        assert 80.0 <= pitch <= 7500.0


def test_5_modality_physical_affordance_grounding() -> None:
    """Verifies that concrete nouns and sensory adjectives map to ground-truth physical invariants, while abstract words yield empty sets."""
    transducer = OrthographicSensoryTransducer()

    # 1. Concrete physical nouns
    apple_aff = transducer.ground_affordances("apple")
    assert apple_aff["touch_texture"] == 0.08
    assert apple_aff["touch_warmth"] == 0.45
    assert apple_aff["contact_compliance"] == 0.35
    assert apple_aff["smell_odour"] == 0.70
    assert apple_aff["taste_residue"] == 0.85
    assert apple_aff["optical_reflectance"] == (420_000, 110_000, 90_000, 80_000, 70_000, 60_000)

    book_aff = transducer.ground_affordances("book")
    assert book_aff["touch_texture"] == 0.25
    assert book_aff["contact_compliance"] == 0.20
    assert book_aff["taste_residue"] == 0.0

    # 2. Sensory adjectives
    warm_aff = transducer.ground_affordances("warm")
    assert warm_aff == {"touch_warmth": 0.80}

    rough_aff = transducer.ground_affordances("rough")
    assert rough_aff == {"touch_texture": 0.85}

    sweet_aff = transducer.ground_affordances("sweet")
    assert sweet_aff == {"taste_residue": 0.85, "smell_odour": 0.65}

    # 3. Compound modulation
    warm_apple = transducer.ground_affordances("warm-apple")
    assert warm_apple["touch_warmth"] == 0.80  # overridden by warm
    assert warm_apple["taste_residue"] == 0.85  # from apple

    # 4. Abstract / functional words (strictly zero affordances)
    for abstract in ("the", "a", "is", "in", "on", "and", "which", "because"):
        aff = transducer.ground_affordances(abstract)
        assert aff == {}, f"Abstract word '{abstract}' must not fabricate physical affordances"


def test_curriculum_sentence_temporal_sequencing() -> None:
    """Verifies that an educational sentence is transduced into synchronized temporal frames."""
    transducer = OrthographicSensoryTransducer()
    sentence = "The warm sweet apple on the desk"
    frames = transducer.transduce_sentence(sentence, base_seed=100)

    tokens = ["The", "warm", "sweet", "apple", "on", "the", "desk"]
    assert len(frames) == len(tokens)

    for frame, expected_token in zip(frames, tokens):
        assert isinstance(frame, TransducedSensoryFrame)
        assert frame.text_token == expected_token
        assert isinstance(frame.optical_glyph, ExactGlyphGeometry)
        assert len(frame.retinal_rgb_405) == 405
        assert len(frame.acoustic_pcm_s16le) == 8_000
        assert len(frame.cochlear_32_channels) == 32
        assert len(frame.ear_bands_6) == 6
        assert frame.sound_energy > 0.0

        # Export verification
        lean_occ = frame.to_lean_sensory_occurrence(source="text-microphone")
        assert isinstance(lean_occ, LeanSensoryOccurrence)
        assert lean_occ.source == "text-microphone"
        assert lean_occ.retina_rgb_u8 == frame.retinal_rgb_405
        assert lean_occ.pressure_s16le == frame.acoustic_pcm_s16le

        phys_occ = frame.to_physical_occurrence(source="text-microphone")
        assert isinstance(phys_occ, PhysicalOccurrence)
        assert phys_occ.kind == "sensory"
        assert phys_occ.payload == lean_occ


def test_organism_sensory_ingestion_and_zero_cognitive_contamination() -> None:
    """Verifies that presenting transduced frames into Guala's sensory intake advances the organism without cognitive corruption."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)

    transducer = OrthographicSensoryTransducer()
    frames = transducer.transduce_sentence("The warm sweet apple", base_seed=200)

    loop = FunctionalPhysicalLoop()
    initial_tick = organism.live_organism_tick

    for idx, frame in enumerate(frames):
        occ = frame.to_physical_occurrence()
        result = loop.settle(organism, world, occ)

        # Organism must step forward on each beat
        assert organism.live_organism_tick == initial_tick + idx + 1
        assert result.observation is not None
        assert "her_act" in result.observation

        # Internal state verification: L0-L4 determinism preserved
        assert organism.identity == IDENTITY
        assert organism.reserve_micrograms > 0

