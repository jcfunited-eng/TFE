from __future__ import annotations

import hashlib
from pathlib import Path
import struct

import pytest

from tools.migrate_guala_paired_v1_to_v2 import read_v1_current_pair


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
_RECORD = struct.Struct("<8sH36sQ32sQ32sQBQ32sQ32sQ")


def _v1_root(root: Path) -> tuple[bytes, bytes]:
    body = b"GLORUN01" + bytes(range(256)) * 8
    world = b"one exact world"
    body_digest = hashlib.sha256(body).digest()
    world_digest = hashlib.sha256(world).digest()
    (root / "body-generations").mkdir(parents=True)
    (root / "world-generations").mkdir()
    record = _RECORD.pack(
        b"GLPAIR01",
        1,
        IDENTITY.encode("ascii"),
        41,
        body_digest,
        len(body),
        world_digest,
        len(world),
        0,
        0,
        bytes(32),
        0,
        bytes(32),
        0,
    )
    (root / "CURRENT").write_bytes(record + hashlib.sha256(record).digest())
    (root / "body-generations" / f"{body_digest.hex()}.glorun").write_bytes(body)
    (root / "world-generations" / f"{world_digest.hex()}.glworld").write_bytes(world)
    return body, world


def test_reads_only_exact_v1_current_pair(tmp_path: Path) -> None:
    body, world = _v1_root(tmp_path)

    source = read_v1_current_pair(
        tmp_path,
        max_body_bytes=4096,
        max_world_bytes=4096,
    )

    assert source.identity == IDENTITY
    assert source.organism_tick == 41
    assert source.body == body
    assert source.body_sha256 == hashlib.sha256(body).hexdigest()
    assert source.world == world
    assert source.world_sha256 == hashlib.sha256(world).hexdigest()


def test_refuses_v1_pointer_or_selected_body_corruption(tmp_path: Path) -> None:
    body, _world = _v1_root(tmp_path)
    pointer = tmp_path / "CURRENT"
    original = pointer.read_bytes()
    pointer.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(RuntimeError, match="CURRENT checksum changed"):
        read_v1_current_pair(
            tmp_path,
            max_body_bytes=4096,
            max_world_bytes=4096,
        )

    pointer.write_bytes(original)
    body_path = (
        tmp_path
        / "body-generations"
        / f"{hashlib.sha256(body).hexdigest()}.glorun"
    )
    body_path.write_bytes(body[:-1] + bytes([body[-1] ^ 1]))
    with pytest.raises(RuntimeError, match="body receipt changed"):
        read_v1_current_pair(
            tmp_path,
            max_body_bytes=4096,
            max_world_bytes=4096,
        )
