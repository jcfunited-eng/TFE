"""
direct_text_source.py — TextSource for inline text strings.

GL-CMD-112 Phase D.
"""

from typing import List, Optional
import numpy as np


def _split_to_sentences(text: str) -> List[str]:
    """Split text into sentences (reuses gutenberg_adapter heuristic)."""
    sentences = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) > 200:
            parts = line.replace(". ", ".\n").split("\n")
            sentences.extend(p.strip() for p in parts if p.strip())
        else:
            sentences.append(line)
    return [s for s in sentences if len(s) > 1]


class DirectTextSource:
    """TextSource for inline text passed at construction."""

    def __init__(self, text: str, title: str = "direct"):
        self._text = text
        self._title = title

    @property
    def source_id(self) -> str:
        return f"direct-{hash(self._text) & 0xFFFFFFFF:08x}"

    @property
    def title(self) -> str:
        return self._title

    def get_sentences(self) -> List[str]:
        return _split_to_sentences(self._text)

    def get_audio(self) -> Optional[List[np.ndarray]]:
        return None

    def get_images(self) -> Optional[List[np.ndarray]]:
        return None
