"""
text_source.py — TextSource Protocol for curriculum ingestion.

GL-CMD-112 Phase D, per GL-SPC-SENSORY-CATALOG-EVE-20260621-111 §3.

Source-agnostic interface: any content provider (Gutenberg, direct text,
future PDF/TTS/video) implements this Protocol to feed the curriculum loader.
"""

from typing import List, Optional, Protocol
import numpy as np


class TextSource(Protocol):
    """Source-agnostic content provider for curriculum ingestion.

    Implementors provide sentences (always), and optionally audio/image data.
    The curriculum loader iterates get_sentences(), then checks get_audio()
    and get_images() for multi-modal content.
    """

    @property
    def source_id(self) -> str:
        """Unique identifier for this source (e.g., 'gutenberg-14838')."""
        ...

    @property
    def title(self) -> str:
        """Human-readable title."""
        ...

    def get_sentences(self) -> List[str]:
        """Return all sentences from this source.

        Sentences are substrate-ready: normalized, stripped, non-empty.
        """
        ...

    def get_audio(self) -> Optional[List[np.ndarray]]:
        """Return audio waveforms associated with this source, or None.

        Each array is a 1D float64 waveform at substrate sample rate.
        """
        ...

    def get_images(self) -> Optional[List[np.ndarray]]:
        """Return images associated with this source, or None.

        Each array is a 2D float64 intensity grid (grayscale, 0-1).
        """
        ...
