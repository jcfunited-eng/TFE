"""
allowlist.py — Canonical allowlist for curriculum corpus sources.

GL-CMD-CURRICULUM-GUTENBERG-EVE-20260620-92

All 6 future adapters use this module for source validation.
"""

from urllib.parse import urlparse


ALLOWED_CORPUS_SOURCES = {
    "gutenberg.org",
    "khanacademykids.com",
    "pbskids.org",
    "archive.org",
    "spotify.com",
    "youtube.com",
}


class CorpusSourceNotAllowed(Exception):
    """Raised when a corpus source URL is not in the allowlist."""
    pass


def validate_source_url(url: str) -> bool:
    """Validate that a URL's domain is in the allowlist.

    Returns True if allowed. Raises CorpusSourceNotAllowed otherwise.
    Matches on domain suffix (e.g. www.gutenberg.org matches gutenberg.org).
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    for allowed in ALLOWED_CORPUS_SOURCES:
        if host == allowed or host.endswith("." + allowed):
            return True

    raise CorpusSourceNotAllowed(
        f"Source '{host}' is not in the allowed corpus sources: "
        f"{sorted(ALLOWED_CORPUS_SOURCES)}"
    )
