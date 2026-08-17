from __future__ import annotations

import json
from pathlib import Path

import pytest

from dsf_ai_service.bounded_source_media_store import (
    BoundedSourceMediaStore,
    BoundedSourceMediaStoreError,
)


def _local_source(**overrides):
    arguments = {
        "attribution": "Joseph Forrester",
        "material_kind": "picture",
        "media_type": "image/png",
        "origin_kind": "local_offer",
        "origin_locator": "family-photo.png",
        "rights_basis": "owned_by_offeror",
        "rights_statement": (
            "Offered by its owner for Guala's bounded private experience."
        ),
        "source_bytes": b"exact-local-source",
    }
    arguments.update(overrides)
    return arguments


def _gutenberg_source(**overrides):
    arguments = {
        "attribution": "Project Gutenberg",
        "edition": "11-0.txt",
        "language_tag": "en",
        "material_kind": "gutenberg_text",
        "media_type": "text/plain; charset=utf-8",
        "origin_kind": "project_gutenberg",
        "origin_locator": "https://www.gutenberg.org/files/11/11-0.txt",
        "rights_basis": "public_domain",
        "rights_statement": (
            "Project Gutenberg public-domain edition; source terms preserved."
        ),
        "source_bytes": b"Project Gutenberg exact returned bytes",
    }
    arguments.update(overrides)
    return arguments


def test_exact_source_bytes_and_provenance_survive_restore(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    source = b"\x89PNG\r\n\x1a\nexact-local-picture"
    admitted = store.admit(**_local_source(source_bytes=source))

    restored = BoundedSourceMediaStore(tmp_path / "source-media")
    assert restored.inventory() == (admitted,)
    assert restored.source_bytes(admitted.receipt_sha256) == source
    projection = admitted.public_projection()
    assert projection["retained_source_bytes"] == len(source)
    assert projection["media_type"] == "image/png"
    assert projection["rights_basis"] == "owned_by_offeror"
    assert projection["attribution"] == "Joseph Forrester"
    assert projection["cognition_authority"] is False
    assert projection["semantic_authority"] is False
    assert "source.bin" not in repr(projection)


def test_identical_admission_is_idempotent_and_does_not_grow(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    arguments = _gutenberg_source()
    first = store.admit(**arguments)
    second = store.admit(**arguments)

    assert second == first
    assert store.inventory() == (first,)
    assert len(tuple((store.entries).iterdir())) == 1


def test_identical_bytes_cannot_grow_under_different_provenance(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    source = b"one physical source"
    first = store.admit(**_local_source(source_bytes=source))

    with pytest.raises(
        BoundedSourceMediaStoreError,
        match="already have different immutable provenance",
    ):
        store.admit(
            **_local_source(
                origin_locator="renamed-copy.png",
                source_bytes=source,
            )
        )

    assert store.inventory() == (first,)
    assert len(tuple(store.entries.iterdir())) == 1


def test_admission_does_not_reread_prior_source_bytes(
    tmp_path,
    monkeypatch,
) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    first = store.admit(**_local_source(source_bytes=b"first source"))
    first_path = store.entries / first.receipt_sha256 / "source.bin"
    read_bytes = Path.read_bytes

    def refuse_prior_source(path):
        if path == first_path:
            raise AssertionError("prior source bytes were redundantly read")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", refuse_prior_source)
    second = store.admit(
        **_local_source(
            origin_locator="second.png",
            source_bytes=b"second source",
        )
    )

    assert second.source_byte_count == len(b"second source")


def test_source_access_reads_only_the_requested_source(
    tmp_path,
    monkeypatch,
) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    first = store.admit(**_local_source(source_bytes=b"first source"))
    second = store.admit(
        **_local_source(
            origin_locator="second.png",
            source_bytes=b"second source",
        )
    )
    second_path = store.entries / second.receipt_sha256 / "source.bin"
    read_bytes = Path.read_bytes

    def refuse_other_source(path):
        if path == second_path:
            raise AssertionError("unrequested source bytes were read")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", refuse_other_source)

    assert store.source_bytes(first.receipt_sha256) == b"first source"


def test_count_and_total_byte_bounds_refuse_before_writing(tmp_path) -> None:
    count_store = BoundedSourceMediaStore(
        tmp_path / "count",
        max_source_bytes=8,
        max_source_count=1,
        max_total_bytes=8,
    )
    count_store.admit(
        **_local_source(
            material_kind="audio",
            media_type="audio/wav",
            origin_locator="first.wav",
            source_bytes=b"1234",
        )
    )
    with pytest.raises(BoundedSourceMediaStoreError, match="count boundary"):
        count_store.admit(
            **_local_source(
                material_kind="song",
                media_type="audio/wav",
                origin_locator="second.wav",
                source_bytes=b"5678",
            )
        )
    assert len(count_store.inventory()) == 1
    assert not count_store.stage.exists()

    byte_store = BoundedSourceMediaStore(
        tmp_path / "bytes",
        max_source_bytes=8,
        max_source_count=3,
        max_total_bytes=8,
    )
    byte_store.admit(
        **_local_source(
            material_kind="pdf",
            media_type="application/pdf",
            origin_locator="first.pdf",
            source_bytes=b"12345",
        )
    )
    with pytest.raises(BoundedSourceMediaStoreError, match="byte boundary"):
        byte_store.admit(
            **_local_source(
                material_kind="book",
                media_type="application/pdf",
                origin_locator="second.pdf",
                source_bytes=b"6789",
            )
        )
    assert len(byte_store.inventory()) == 1


def test_tampered_source_or_record_fails_closed(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    record = store.admit(
        **_local_source(
            material_kind="video",
            media_type="video/mp4",
            origin_locator="short-video.mp4",
            source_bytes=b"exact-video-source",
        )
    )
    source_path = store.entries / record.receipt_sha256 / "source.bin"
    source_path.write_bytes(b"crossed-video-source")
    with pytest.raises(BoundedSourceMediaStoreError, match="receipt mismatch"):
        store.inventory()

    source_path.write_bytes(b"exact-video-source")
    record_path = store.entries / record.receipt_sha256 / "record.json"
    value = json.loads(record_path.read_bytes())
    value["source_byte_count"] = True
    record_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(BoundedSourceMediaStoreError, match="receipt mismatch"):
        store.inventory()

    value["source_byte_count"] = len(b"exact-video-source")
    value["origin_locator"] = "different.mp4"
    record_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(BoundedSourceMediaStoreError, match="receipt mismatch"):
        store.inventory()


def test_interrupted_stage_is_never_mistaken_for_committed_media(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    store.root.mkdir(parents=True)
    store.stage.mkdir()
    (store.stage / "source.bin").write_bytes(b"unfinished")

    with pytest.raises(BoundedSourceMediaStoreError, match="requires recovery"):
        store.inventory()


def test_gutenberg_provenance_must_be_complete_and_public_domain(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")

    with pytest.raises(ValueError, match="provenance is incomplete"):
        store.admit(**_gutenberg_source(edition=None))
    with pytest.raises(ValueError, match="provenance is incomplete"):
        store.admit(**_gutenberg_source(language_tag=None))
    with pytest.raises(ValueError, match="provenance is incomplete"):
        store.admit(**_gutenberg_source(rights_basis="licensed"))
    assert store.inventory() == ()


def test_unadmitted_rights_basis_is_refused_before_writing(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")

    with pytest.raises(ValueError, match="rights basis is not admitted"):
        store.admit(**_local_source(rights_basis="unknown"))
    assert store.inventory() == ()
