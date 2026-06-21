"""
gutenberg.py — GutenbergAdapter: fetch + parse Project Gutenberg texts.

GL-CMD-CURRICULUM-GUTENBERG-EVE-20260620-92

Wraps the existing fetch_and_parse() with a class interface, adds allowlist
validation, and supports book_id-based URL construction.

URL pattern: https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt
"""

from typing import List, Tuple

from dsf_ai_service.curriculum.allowlist import validate_source_url
from dsf_ai_service.curriculum.gutenberg_adapter import fetch_and_parse


class GutenbergAdapter:
    """Fetch and normalize a Project Gutenberg book into sentences.

    Usage:
        adapter = GutenbergAdapter(book_id=14838)
        sentences = adapter.fetch_normalized()
    """

    URL_TEMPLATE = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"

    def __init__(self, book_id):
        self.book_id = int(book_id)
        self.url = self.URL_TEMPLATE.format(id=self.book_id)
        self.metadata = None

    def fetch_normalized(self) -> List[str]:
        """Validate URL, fetch, strip boilerplate, return sentences.

        Raises CorpusSourceNotAllowed if URL is off-list.
        """
        validate_source_url(self.url)
        sentences, metadata = fetch_and_parse(self.url)
        self.metadata = metadata
        return sentences
