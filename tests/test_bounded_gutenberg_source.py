from __future__ import annotations

import pytest

from dsf_ai_service.bounded_gutenberg_source import (
    GUTENBERG_MAX_SOURCE_BYTES,
    acquire_project_gutenberg_source,
)
from dsf_ai_service.bounded_source_media_store import BoundedSourceMediaStore


SOURCE_URL = "https://www.gutenberg.org/files/11/11-0.txt"


class _Response:
    def __init__(
        self,
        body: bytes,
        *,
        final_url: str = SOURCE_URL,
        media_type: str = "text/plain; charset=utf-8",
        declared_length: int | None = None,
    ) -> None:
        self.body = body
        self.final_url = final_url
        self.headers = {"Content-Type": media_type}
        if declared_length is not None:
            self.headers["Content-Length"] = str(declared_length)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def geturl(self) -> str:
        return self.final_url

    def read(self, maximum: int) -> bytes:
        return self.body[:maximum]


def _opener(response: _Response):
    def open_source(request, *, timeout):
        assert request.full_url == SOURCE_URL
        assert request.get_header("Accept") == "text/plain"
        assert request.get_header("Accept-encoding") == "identity"
        assert timeout == 25
        return response

    return open_source


def test_named_gutenberg_response_enters_exact_immutable_custody(tmp_path) -> None:
    body = b"Project Gutenberg exact response bytes"
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    record = acquire_project_gutenberg_source(
        store,
        source_url=SOURCE_URL,
        language_tag="en",
        opener=_opener(_Response(body, declared_length=len(body))),
    )

    assert record.edition == "11-0.txt"
    assert record.language_tag == "en"
    assert record.rights_basis == "public_domain"
    assert record.origin_locator == SOURCE_URL
    assert record.media_type == "text/plain; charset=utf-8"
    assert store.source_bytes(record.receipt_sha256) == body


@pytest.mark.parametrize(
    "source_url",
    (
        "http://www.gutenberg.org/files/11/11-0.txt",
        "https://example.com/files/11/11-0.txt",
        "https://www.gutenberg.org/files/11/11-0.txt?choice=next",
        "https://www.gutenberg.org/cache/epub/11/pg11.txt",
    ),
)
def test_non_exact_gutenberg_source_is_refused_before_fetch(
    tmp_path,
    source_url,
) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")

    with pytest.raises(ValueError, match="source URL changed"):
        acquire_project_gutenberg_source(
            store,
            source_url=source_url,
            language_tag="en",
            opener=lambda *args, **kwargs: pytest.fail("fetch was attempted"),
        )


def test_redirect_or_non_text_response_is_refused(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")

    with pytest.raises(ValueError, match="redirected"):
        acquire_project_gutenberg_source(
            store,
            source_url=SOURCE_URL,
            language_tag="en",
            opener=_opener(
                _Response(
                    b"redirected",
                    final_url="https://www.gutenberg.org/files/12/12-0.txt",
                )
            ),
        )
    with pytest.raises(ValueError, match="not plain text"):
        acquire_project_gutenberg_source(
            store,
            source_url=SOURCE_URL,
            language_tag="en",
            opener=_opener(_Response(b"html", media_type="text/html")),
        )
    assert store.inventory() == ()


def test_declared_or_actual_oversize_is_refused_without_custody(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")

    with pytest.raises(ValueError, match="bytes exceed their bound"):
        acquire_project_gutenberg_source(
            store,
            source_url=SOURCE_URL,
            language_tag="en",
            opener=_opener(
                _Response(
                    b"small",
                    declared_length=GUTENBERG_MAX_SOURCE_BYTES + 1,
                )
            ),
        )
    with pytest.raises(ValueError, match="bytes exceed their bound"):
        acquire_project_gutenberg_source(
            store,
            source_url=SOURCE_URL,
            language_tag="en",
            opener=_opener(_Response(b"x" * (GUTENBERG_MAX_SOURCE_BYTES + 1))),
        )
    assert store.inventory() == ()
