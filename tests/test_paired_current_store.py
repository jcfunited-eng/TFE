from __future__ import annotations

import hashlib
import os
from pathlib import Path
import zlib

import pytest

from dsf_ai_service.paired_current_store import (
    BODY_DIRECTORY,
    BODY_SUFFIX,
    CURRENT_FILE,
    PairedCurrentStore,
    PairedCurrentStoreError,
    WORLD_DIRECTORY,
    WORLD_SUFFIX,
)


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def _store(root: Path) -> PairedCurrentStore:
    return PairedCurrentStore(root, max_body_bytes=4096, max_world_bytes=4096)


def _publish_initial(store: PairedCurrentStore) -> tuple[bytes, bytes]:
    body = b"body-zero"
    world = b"world-zero"
    store.publish(
        identity=IDENTITY,
        organism_tick=41,
        body=body,
        world=world,
        expected_current_body_sha256=None,
    )
    return body, world


def test_one_current_record_restores_exact_pair(tmp_path: Path) -> None:
    store = _store(tmp_path)
    body, world = _publish_initial(store)

    restored = store.restore()

    assert restored.body == body
    assert restored.world == world
    assert restored.pointer.current.identity == IDENTITY
    assert restored.pointer.current.organism_tick == 41
    assert restored.pointer.predecessor is None
    assert {path.name for path in tmp_path.iterdir()} == {
        BODY_DIRECTORY,
        WORLD_DIRECTORY,
        CURRENT_FILE,
    }


def test_body_generation_is_deterministic_gzip_with_raw_receipt(
    tmp_path: Path,
) -> None:
    body = b"GLORUN01" + (b"native-state" * 300)
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    for root in (first_root, second_root):
        _store(root).publish(
            identity=IDENTITY,
            organism_tick=41,
            body=body,
            world=b"world-one",
            expected_current_body_sha256=None,
        )
    body_name = f"{hashlib.sha256(body).hexdigest()}{BODY_SUFFIX}"
    first_stored = (first_root / BODY_DIRECTORY / body_name).read_bytes()
    second_stored = (second_root / BODY_DIRECTORY / body_name).read_bytes()

    assert first_stored == second_stored
    assert first_stored.startswith(b"\x1f\x8b")
    assert len(first_stored) < len(body)
    assert zlib.decompress(first_stored, wbits=31) == body
    pointer = PairedCurrentStore(
        first_root,
        max_body_bytes=4096,
        max_world_bytes=4096,
    ).read_pointer()
    assert pointer.current.body_bytes == len(body)
    assert pointer.current.body_sha256 == hashlib.sha256(body).hexdigest()


def test_incompressible_body_remains_within_stored_bound(tmp_path: Path) -> None:
    body = os.urandom(4096)
    store = _store(tmp_path)
    store.publish(
        identity=IDENTITY,
        organism_tick=41,
        body=body,
        world=b"world-zero",
        expected_current_body_sha256=None,
    )

    assert store.restore().body == body


def test_appended_or_damaged_compressed_body_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    body, _world = _publish_initial(store)
    body_path = (
        tmp_path
        / BODY_DIRECTORY
        / f"{hashlib.sha256(body).hexdigest()}{BODY_SUFFIX}"
    )
    original = body_path.read_bytes()
    body_path.chmod(0o600)
    body_path.write_bytes(original + b"trailing")
    with pytest.raises(PairedCurrentStoreError, match="raw body receipt"):
        store.restore()

    body_path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(PairedCurrentStoreError, match="damaged|raw body receipt"):
        store.restore()


def test_successor_carries_exact_predecessor_pair_and_tick(tmp_path: Path) -> None:
    store = _store(tmp_path)
    body, world = _publish_initial(store)
    predecessor_receipt = hashlib.sha256(body).hexdigest()
    successor_body = b"body-one"
    successor_world = b"world-one"

    published = store.publish(
        identity=IDENTITY,
        organism_tick=57,
        body=successor_body,
        world=successor_world,
        expected_current_body_sha256=predecessor_receipt,
    )

    assert published.current.organism_tick == 57
    assert published.predecessor is not None
    assert published.predecessor.organism_tick == 41
    assert published.predecessor.body_sha256 == predecessor_receipt
    assert published.predecessor.world_sha256 == hashlib.sha256(world).hexdigest()
    restored = store.restore()
    assert restored.body == successor_body
    assert restored.world == successor_world


def test_stale_or_missing_expected_current_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _publish_initial(store)

    with pytest.raises(PairedCurrentStoreError, match="another writer"):
        store.publish(
            identity=IDENTITY,
            organism_tick=42,
            body=b"body-one",
            world=b"world-one",
            expected_current_body_sha256="0" * 64,
        )
    with pytest.raises(PairedCurrentStoreError, match="was not expected"):
        store.publish(
            identity=IDENTITY,
            organism_tick=42,
            body=b"body-one",
            world=b"world-one",
            expected_current_body_sha256=None,
        )


def test_corrupt_pointer_or_generation_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    body, world = _publish_initial(store)
    current = tmp_path / CURRENT_FILE
    original_pointer = current.read_bytes()
    current.write_bytes(original_pointer[:-1] + bytes([original_pointer[-1] ^ 1]))
    with pytest.raises(PairedCurrentStoreError, match="checksum"):
        store.restore()

    current.write_bytes(original_pointer)
    world_path = (
        tmp_path
        / WORLD_DIRECTORY
        / f"{hashlib.sha256(world).hexdigest()}{WORLD_SUFFIX}"
    )
    world_path.chmod(0o600)
    world_path.write_bytes(b"wrong-world")
    with pytest.raises(PairedCurrentStoreError, match="byte count|receipt"):
        store.restore()

    body_path = (
        tmp_path
        / BODY_DIRECTORY
        / f"{hashlib.sha256(body).hexdigest()}{BODY_SUFFIX}"
    )
    assert body_path.is_file()


def test_missing_or_symlinked_generation_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    body, _world = _publish_initial(store)
    body_path = (
        tmp_path
        / BODY_DIRECTORY
        / f"{hashlib.sha256(body).hexdigest()}{BODY_SUFFIX}"
    )
    body_path.unlink()
    body_path.symlink_to(tmp_path / CURRENT_FILE)

    with pytest.raises(PairedCurrentStoreError, match="not a real file"):
        store.restore()


def test_reconcile_retains_only_current_and_exact_predecessor(tmp_path: Path) -> None:
    store = _store(tmp_path)
    body, _world = _publish_initial(store)
    successor = b"body-one"
    pointer = store.publish(
        identity=IDENTITY,
        organism_tick=42,
        body=successor,
        world=b"world-one",
        expected_current_body_sha256=hashlib.sha256(body).hexdigest(),
    )
    orphan = tmp_path / BODY_DIRECTORY / f"{'f' * 64}{BODY_SUFFIX}"
    orphan.write_bytes(b"orphan")

    removed_count, removed_bytes = store.reconcile(pointer)

    assert (removed_count, removed_bytes) == (1, len(b"orphan"))
    assert not orphan.exists()
    retained = {path.name for path in (tmp_path / BODY_DIRECTORY).iterdir()}
    assert retained == {
        f"{hashlib.sha256(body).hexdigest()}{BODY_SUFFIX}",
        f"{hashlib.sha256(successor).hexdigest()}{BODY_SUFFIX}",
    }


def test_identity_tick_and_size_changes_are_refused(tmp_path: Path) -> None:
    store = _store(tmp_path)
    body, _world = _publish_initial(store)
    receipt = hashlib.sha256(body).hexdigest()

    with pytest.raises(PairedCurrentStoreError, match="identity changed"):
        store.publish(
            identity="18fcfe11-315f-428f-84f4-b6515498e06c",
            organism_tick=42,
            body=b"body-one",
            world=b"world-one",
            expected_current_body_sha256=receipt,
        )
    with pytest.raises(PairedCurrentStoreError, match="tick moved backward"):
        store.publish(
            identity=IDENTITY,
            organism_tick=40,
            body=b"body-one",
            world=b"world-one",
            expected_current_body_sha256=receipt,
        )
    with pytest.raises(PairedCurrentStoreError, match="body size"):
        store.publish(
            identity=IDENTITY,
            organism_tick=42,
            body=b"x" * 4097,
            world=b"world-one",
            expected_current_body_sha256=receipt,
        )
