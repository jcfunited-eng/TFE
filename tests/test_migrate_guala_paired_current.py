from __future__ import annotations

import hashlib
import lzma
from pathlib import Path
import struct

import pytest

from tools.migrate_guala_paired_current import read_retired_current_pair


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
_CURRENT = struct.Struct("<8sH36sQQ32s32s")
_COMPACT = struct.Struct("<8sHBBQ32sQ")
_WORLD = struct.Struct("<8sH32s32sQ")


def _checked(record: bytes) -> bytes:
    return record + hashlib.sha256(record).digest()


def _retired_root(root: Path) -> tuple[bytes, bytes]:
    body = b"GLORUN01" + bytes(range(256)) * 8
    body_digest = hashlib.sha256(body).digest()
    world = b"one exact world"
    world_digest = hashlib.sha256(world).digest()
    (root / "generations").mkdir(parents=True)
    (root / "world-associations").mkdir()
    (root / "world-generations").mkdir()
    pointer = _CURRENT.pack(
        b"GLCUR001",
        1,
        IDENTITY.encode("ascii"),
        41,
        len(body),
        body_digest,
        bytes(32),
    )
    (root / "CURRENT").write_bytes(_checked(pointer))
    payload = lzma.compress(
        body,
        format=lzma.FORMAT_RAW,
        filters=[{"id": lzma.FILTER_LZMA2, "preset": 0}],
    )
    compact = _COMPACT.pack(
        b"GLCMP001",
        1,
        1,
        0,
        len(body),
        body_digest,
        len(payload),
    ) + payload
    (root / "generations" / f"{body_digest.hex()}.glorun").write_bytes(compact)
    (root / "WORLD_RECOVERY_V1").write_bytes(b"GLWRCV01\n")
    association = _WORLD.pack(
        b"GLWREF01",
        1,
        body_digest,
        world_digest,
        len(world),
    )
    (root / "world-associations" / f"{body_digest.hex()}.worldref").write_bytes(
        _checked(association)
    )
    (root / "world-generations" / f"{world_digest.hex()}.glworld").write_bytes(
        world
    )
    return body, world


def test_reads_only_exact_retired_current_pair(tmp_path: Path) -> None:
    body, world = _retired_root(tmp_path)
    restored = read_retired_current_pair(
        tmp_path,
        max_body_bytes=4096,
        max_world_bytes=4096,
    )
    assert restored.identity == IDENTITY
    assert restored.organism_tick == 41
    assert restored.body == body
    assert restored.body_sha256 == hashlib.sha256(body).hexdigest()
    assert restored.world == world
    assert restored.world_sha256 == hashlib.sha256(world).hexdigest()


def test_refuses_world_association_corruption(tmp_path: Path) -> None:
    body, _world = _retired_root(tmp_path)
    association = (
        tmp_path
        / "world-associations"
        / f"{hashlib.sha256(body).hexdigest()}.worldref"
    )
    changed = bytearray(association.read_bytes())
    changed[-1] ^= 1
    association.write_bytes(changed)
    with pytest.raises(RuntimeError, match="association checksum changed"):
        read_retired_current_pair(
            tmp_path,
            max_body_bytes=4096,
            max_world_bytes=4096,
        )
