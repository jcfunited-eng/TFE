"""Raw GLORUN/CURRENT checkpoint proof with no JSON cognitive copy."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.native_resident_organism import (
    create_native_resident_organism,
)
from dsf_ai_service.substrate import native_organism_binary_store as store


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
MAX_ENVELOPE_BYTES = 67_108_864
MAX_FABRIC_BYTES = 67_108_000
MAX_LOGICAL_PEAK_BYTES = 536_870_912


class _ObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_if_absent(
        self,
        key: str,
        chunks,
        *,
        byte_count: int,
        sha256: str,
    ) -> bool:
        body = b"".join(chunks)
        assert len(body) == byte_count
        assert hashlib.sha256(body).hexdigest() == sha256
        prior = self.objects.setdefault(key, body)
        if prior != body:
            raise RuntimeError("immutable object collision")
        return prior is body

    def iter_bytes(self, key: str):
        yield self.objects[key]

    def delete_if_exact(
        self,
        key: str,
        *,
        byte_count: int,
        sha256: str,
    ) -> None:
        body = self.objects[key]
        assert len(body) == byte_count
        assert hashlib.sha256(body).hexdigest() == sha256
        del self.objects[key]


def _publish(root: Path):
    organism = create_native_resident_organism(
        organism_identity=IDENTITY,
        organism_tick=0,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
        max_fabric_bytes=MAX_FABRIC_BYTES,
        max_logical_peak_bytes=MAX_LOGICAL_PEAK_BYTES,
    )
    staged = store.stage_active_native_organism(
        root,
        organism,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
    )
    remote = _ObjectStore()
    published = store.publish_staged_native_organism(
        staged,
        expected_predecessor_sha256=None,
        object_store=remote,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
        max_fabric_bytes=MAX_FABRIC_BYTES,
        max_logical_peak_bytes=MAX_LOGICAL_PEAK_BYTES,
    )
    return organism, published, remote


def _restore(root: Path):
    return store.restore_current_native_organism(
        root,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
        max_fabric_bytes=MAX_FABRIC_BYTES,
        max_logical_peak_bytes=MAX_LOGICAL_PEAK_BYTES,
    )


def test_checkpoint_is_one_raw_glorun_and_one_fixed_current_pointer(
    tmp_path: Path,
) -> None:
    organism, published, remote = _publish(tmp_path)
    body = organism.save()
    digest = hashlib.sha256(body).hexdigest()
    generation = tmp_path / store.GENERATIONS_DIRECTORY / f"{digest}.glorun"
    current = tmp_path / store.CURRENT_NAME
    restored = _restore(tmp_path)

    assert body.startswith(store.STATE_MAGIC)
    assert generation.read_bytes() == body
    assert current.read_bytes().startswith(store.CURRENT_MAGIC)
    assert current.stat().st_size == store.POINTER_BYTES
    assert published.pointer.state_sha256 == digest
    assert published.pointer.predecessor_state_sha256 is None
    assert restored.organism.save() == body
    assert restored.pointer == published.pointer
    assert remote.objects[published.remote_key] == body
    assert not list(tmp_path.rglob("*.json"))
    assert not any("owner" in path.name.lower() for path in tmp_path.rglob("*"))
    assert not any("lock" in path.name.lower() for path in tmp_path.rglob("*"))


def test_tampered_current_body_halts_without_predecessor_fallback(
    tmp_path: Path,
) -> None:
    _organism, published, _remote = _publish(tmp_path)
    path = (
        tmp_path
        / store.GENERATIONS_DIRECTORY
        / f"{published.pointer.state_sha256}.glorun"
    )
    body = bytearray(path.read_bytes())
    body[-1] ^= 1
    path.write_bytes(body)

    with pytest.raises(
        store.NativeOrganismBinaryStoreError,
        match="not exact current GLORUN",
    ):
        _restore(tmp_path)
