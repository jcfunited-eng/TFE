from __future__ import annotations

import json

import pytest

from dsf_ai_service.bounded_source_media_store import (
    BoundedSourceMediaStore,
    BoundedSourceMediaStoreError,
)


def test_exact_source_bytes_and_provenance_survive_restore(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    source = b"\x89PNG\r\n\x1a\nexact-local-picture"
    admitted = store.admit(
        material_kind="picture",
        origin_kind="local_offer",
        origin_locator="family-photo.png",
        source_bytes=source,
    )

    restored = BoundedSourceMediaStore(tmp_path / "source-media")
    assert restored.inventory() == (admitted,)
    assert restored.source_bytes(admitted.receipt_sha256) == source
    projection = admitted.public_projection()
    assert projection["retained_source_bytes"] == len(source)
    assert projection["cognition_authority"] is False
    assert projection["semantic_authority"] is False
    assert "source.bin" not in repr(projection)


def test_identical_admission_is_idempotent_and_does_not_grow(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    arguments = {
        "material_kind": "gutenberg_text",
        "origin_kind": "project_gutenberg",
        "origin_locator": "https://www.gutenberg.org/files/11/11-0.txt",
        "source_bytes": b"Project Gutenberg exact returned bytes",
    }
    first = store.admit(**arguments)
    second = store.admit(**arguments)

    assert second == first
    assert store.inventory() == (first,)
    assert len(tuple((store.entries).iterdir())) == 1


def test_count_and_total_byte_bounds_refuse_before_writing(tmp_path) -> None:
    count_store = BoundedSourceMediaStore(
        tmp_path / "count",
        max_source_bytes=8,
        max_source_count=1,
        max_total_bytes=8,
    )
    count_store.admit(
        material_kind="audio",
        origin_kind="local_offer",
        origin_locator="first.wav",
        source_bytes=b"1234",
    )
    with pytest.raises(BoundedSourceMediaStoreError, match="count boundary"):
        count_store.admit(
            material_kind="song",
            origin_kind="local_offer",
            origin_locator="second.wav",
            source_bytes=b"5678",
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
        material_kind="pdf",
        origin_kind="local_offer",
        origin_locator="first.pdf",
        source_bytes=b"12345",
    )
    with pytest.raises(BoundedSourceMediaStoreError, match="byte boundary"):
        byte_store.admit(
            material_kind="book",
            origin_kind="local_offer",
            origin_locator="second.pdf",
            source_bytes=b"6789",
        )
    assert len(byte_store.inventory()) == 1


def test_tampered_source_or_record_fails_closed(tmp_path) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    record = store.admit(
        material_kind="video",
        origin_kind="local_offer",
        origin_locator="short-video.mp4",
        source_bytes=b"exact-video-source",
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
