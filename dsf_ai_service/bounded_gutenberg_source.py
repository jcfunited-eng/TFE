"""Bounded explicit Project Gutenberg acquisition for later in-world books.

This module only acquires and preserves one guide-named public-domain source.
It does not select a book, render pages, present a lesson, or enter cognition.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request

from dsf_ai_service.bounded_source_media_store import (
    BoundedSourceMediaStore,
    SourceMediaRecord,
)


GUTENBERG_MAX_SOURCE_BYTES = 2 * 1024 * 1024
GUTENBERG_SOURCE_HOST = "www.gutenberg.org"
GUTENBERG_ATTRIBUTION = "Project Gutenberg"
GUTENBERG_RIGHTS_STATEMENT = (
    "Project Gutenberg public-domain edition; source terms preserved."
)
_GUTENBERG_PATH = re.compile(r"/files/[1-9][0-9]*/[A-Za-z0-9._-]+\.txt")


def _validated_source_url(value: object) -> tuple[str, str]:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("Project Gutenberg source URL changed")
    parsed = urllib.parse.urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("Project Gutenberg source URL changed") from error
    if (
        parsed.scheme != "https"
        or parsed.hostname != GUTENBERG_SOURCE_HOST
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or not _GUTENBERG_PATH.fullmatch(parsed.path)
    ):
        raise ValueError("Project Gutenberg source URL changed")
    return value, parsed.path.rsplit("/", 1)[-1]


def acquire_project_gutenberg_source(
    store: BoundedSourceMediaStore,
    *,
    source_url: str,
    language_tag: str,
    opener=urllib.request.urlopen,
) -> SourceMediaRecord:
    """Fetch one exact named edition into bounded immutable source custody."""

    source_url, edition = _validated_source_url(source_url)
    request = urllib.request.Request(
        source_url,
        headers={
            "Accept": "text/plain",
            "Accept-Encoding": "identity",
            "User-Agent": "guala-bounded-source/1",
        },
    )
    try:
        response_context = opener(request, timeout=25)
        with response_context as response:
            final_url, final_edition = _validated_source_url(response.geturl())
            if final_url != source_url or final_edition != edition:
                raise ValueError("Project Gutenberg source redirected")
            media_type = response.headers.get("Content-Type", "").strip()
            if media_type.split(";", 1)[0].strip().lower() != "text/plain":
                raise ValueError("Project Gutenberg source is not plain text")
            length_header = response.headers.get("Content-Length")
            if length_header is not None:
                try:
                    declared_length = int(length_header)
                except ValueError as error:
                    raise ValueError(
                        "Project Gutenberg byte extent changed"
                    ) from error
                if not 0 < declared_length <= GUTENBERG_MAX_SOURCE_BYTES:
                    raise ValueError("Project Gutenberg bytes exceed their bound")
            source_bytes = response.read(GUTENBERG_MAX_SOURCE_BYTES + 1)
    except ValueError:
        raise
    except (OSError, TimeoutError) as error:
        raise ValueError(
            f"Project Gutenberg acquisition failed: {type(error).__name__}"
        ) from error
    if not source_bytes or len(source_bytes) > GUTENBERG_MAX_SOURCE_BYTES:
        raise ValueError("Project Gutenberg bytes exceed their bound")
    if length_header is not None and len(source_bytes) != declared_length:
        raise ValueError("Project Gutenberg byte extent changed")
    return store.admit(
        attribution=GUTENBERG_ATTRIBUTION,
        edition=edition,
        language_tag=language_tag,
        material_kind="gutenberg_text",
        media_type=media_type,
        origin_kind="project_gutenberg",
        origin_locator=source_url,
        rights_basis="public_domain",
        rights_statement=GUTENBERG_RIGHTS_STATEMENT,
        source_bytes=source_bytes,
    )
