"""
gutenberg_source.py — TextSource wrapper around existing GutenbergAdapter.

GL-CMD-112 Phase D.
"""

from typing import List, Optional
import numpy as np

from dsf_ai_service.curriculum.adapters.gutenberg import GutenbergAdapter


class GutenbergSource:
    """TextSource conformant wrapper around the -92 Gutenberg adapter."""

    def __init__(self, book_id: int):
        self._adapter = GutenbergAdapter(book_id=book_id)
        self._sentences = None

    @property
    def source_id(self) -> str:
        return f"gutenberg-{self._adapter.book_id}"

    @property
    def title(self) -> str:
        if self._adapter.metadata:
            return self._adapter.metadata.get("title", self.source_id)
        return self.source_id

    def get_sentences(self) -> List[str]:
        if self._sentences is None:
            self._sentences = self._adapter.fetch_normalized()
        return self._sentences

    def get_audio(self) -> Optional[List[np.ndarray]]:
        return None

    def get_images(self) -> Optional[List[np.ndarray]]:
        return None
