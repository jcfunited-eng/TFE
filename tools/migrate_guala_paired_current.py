#!/usr/bin/env python3
"""One-time exact migration from the retired body/world stores to one pair."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import lzma
from pathlib import Path
import struct
import uuid

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.glew_runtime.native_resident_organism import (
    restore_native_resident_organism,
)
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import (
    derive_native_resident_resource_admission,
)


_OLD_CURRENT = struct.Struct("<8sH36sQQ32s32s")
_OLD_COMPACT = struct.Struct("<8sHBBQ32sQ")
_OLD_WORLD_ASSOCIATION = struct.Struct("<8sH32s32sQ")
_SHA256_BYTES = hashlib.sha256().digest_size
_OLD_CURRENT_BYTES = _OLD_CURRENT.size + _SHA256_BYTES
_OLD_WORLD_ASSOCIATION_BYTES = _OLD_WORLD_ASSOCIATION.size + _SHA256_BYTES
_OLD_CURRENT_MAGIC = b"GLCUR001"
_OLD_CURRENT_VERSION = 1
_OLD_RAW_MAGIC = b"GLORUN01"
_OLD_COMPACT_MAGIC = b"GLCMP001"
_OLD_COMPACT_VERSION = 1
_OLD_COMPACT_CODEC_LZMA2 = 1
_OLD_COMPACT_PRESET = 0
_OLD_WORLD_MARKER = b"GLWRCV01\n"
_OLD_WORLD_ASSOCIATION_MAGIC = b"GLWREF01"
_OLD_WORLD_ASSOCIATION_VERSION = 1


@dataclass(frozen=True, slots=True)
class RetiredCurrentPair:
    identity: str
    organism_tick: int
    body_sha256: str
    body: bytes
    world_sha256: str
    world: bytes


def _real_file(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label} is not a real file")
    return path.read_bytes()


def _verified_record(body: bytes, expected_bytes: int, label: str) -> bytes:
    if len(body) != expected_bytes:
        raise RuntimeError(f"{label} changed byte count")
    record, receipt = body[:-_SHA256_BYTES], body[-_SHA256_BYTES:]
    if hashlib.sha256(record).digest() != receipt:
        raise RuntimeError(f"{label} checksum changed")
    return record


def _identity(raw: bytes) -> str:
    try:
        value = raw.decode("ascii")
        parsed = uuid.UUID(value)
    except (UnicodeDecodeError, ValueError, AttributeError) as error:
        raise RuntimeError("retired CURRENT identity is invalid") from error
    if str(parsed) != value:
        raise RuntimeError("retired CURRENT identity is not canonical")
    return value


def _positive_bound(value: object, maximum: int, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > maximum
    ):
        raise RuntimeError(f"{label} is outside its byte bound")
    return value


def _decode_retired_body(
    stored: bytes,
    *,
    expected_bytes: int,
    expected_sha256: str,
    max_body_bytes: int,
) -> bytes:
    expected_bytes = _positive_bound(
        expected_bytes, max_body_bytes, "retired body"
    )
    if stored.startswith(_OLD_RAW_MAGIC):
        body = stored
    else:
        if len(stored) < _OLD_COMPACT.size:
            raise RuntimeError("retired compact body ended before its header")
        (
            magic,
            version,
            codec,
            preset,
            raw_bytes,
            raw_sha256,
            payload_bytes,
        ) = _OLD_COMPACT.unpack_from(stored)
        payload = stored[_OLD_COMPACT.size :]
        if (
            magic != _OLD_COMPACT_MAGIC
            or version != _OLD_COMPACT_VERSION
            or codec != _OLD_COMPACT_CODEC_LZMA2
            or preset != _OLD_COMPACT_PRESET
            or raw_bytes != expected_bytes
            or raw_sha256.hex() != expected_sha256
            or payload_bytes != len(payload)
        ):
            raise RuntimeError("retired compact body header changed")
        try:
            decoder = lzma.LZMADecompressor(
                format=lzma.FORMAT_RAW,
                filters=[{"id": lzma.FILTER_LZMA2, "preset": preset}],
            )
            body = decoder.decompress(payload, max_length=expected_bytes + 1)
        except lzma.LZMAError as error:
            raise RuntimeError("retired compact body could not decode") from error
        if not decoder.eof or decoder.unused_data:
            raise RuntimeError("retired compact body did not end exactly")
    if (
        len(body) != expected_bytes
        or not body.startswith(_OLD_RAW_MAGIC)
        or hashlib.sha256(body).hexdigest() != expected_sha256
    ):
        raise RuntimeError("retired body differs from CURRENT")
    return body


def read_retired_current_pair(
    root: Path,
    *,
    max_body_bytes: int,
    max_world_bytes: int,
) -> RetiredCurrentPair:
    """Read and authenticate only the exact retired CURRENT-selected pair."""

    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("retired state root is not a real directory")
    pointer_body = _real_file(root / "CURRENT", "retired CURRENT")
    pointer_record = _verified_record(
        pointer_body, _OLD_CURRENT_BYTES, "retired CURRENT"
    )
    (
        magic,
        version,
        raw_identity,
        organism_tick,
        body_bytes,
        body_digest,
        predecessor_digest,
    ) = _OLD_CURRENT.unpack(pointer_record)
    if magic != _OLD_CURRENT_MAGIC or version != _OLD_CURRENT_VERSION:
        raise RuntimeError("retired CURRENT schema changed")
    if organism_tick < 0:
        raise RuntimeError("retired CURRENT tick is invalid")
    if predecessor_digest == body_digest:
        raise RuntimeError("retired CURRENT predecessor equals current")
    identity = _identity(raw_identity)
    body_sha256 = body_digest.hex()
    stored_body = _real_file(
        root / "generations" / f"{body_sha256}.glorun",
        "retired current generation",
    )
    body = _decode_retired_body(
        stored_body,
        expected_bytes=body_bytes,
        expected_sha256=body_sha256,
        max_body_bytes=max_body_bytes,
    )

    marker = _real_file(root / "WORLD_RECOVERY_V1", "world recovery marker")
    if marker != _OLD_WORLD_MARKER:
        raise RuntimeError("world recovery marker changed")
    association_body = _real_file(
        root / "world-associations" / f"{body_sha256}.worldref",
        "current world association",
    )
    association_record = _verified_record(
        association_body,
        _OLD_WORLD_ASSOCIATION_BYTES,
        "current world association",
    )
    (
        association_magic,
        association_version,
        associated_body_digest,
        world_digest,
        world_bytes,
    ) = _OLD_WORLD_ASSOCIATION.unpack(association_record)
    if (
        association_magic != _OLD_WORLD_ASSOCIATION_MAGIC
        or association_version != _OLD_WORLD_ASSOCIATION_VERSION
        or associated_body_digest != body_digest
    ):
        raise RuntimeError("current world association changed")
    world_bytes = _positive_bound(
        world_bytes, max_world_bytes, "retired world"
    )
    world_sha256 = world_digest.hex()
    world = _real_file(
        root / "world-generations" / f"{world_sha256}.glworld",
        "retired current world",
    )
    if len(world) != world_bytes or hashlib.sha256(world).hexdigest() != world_sha256:
        raise RuntimeError("retired world differs from its association")
    return RetiredCurrentPair(
        identity=identity,
        organism_tick=organism_tick,
        body_sha256=body_sha256,
        body=body,
        world_sha256=world_sha256,
        world=world,
    )


def migrate(
    old_root: Path,
    new_root: Path,
    *,
    max_body_bytes: int,
    max_world_bytes: int,
) -> dict[str, object]:
    if old_root.resolve() == new_root.resolve():
        raise RuntimeError("migration roots are identical")
    source = read_retired_current_pair(
        old_root,
        max_body_bytes=max_body_bytes,
        max_world_bytes=max_world_bytes,
    )
    admission = derive_native_resident_resource_admission(new_root)
    if len(source.body) > admission.max_envelope_bytes:
        raise RuntimeError("retired body exceeds live runtime admission")
    runtime = restore_native_resident_organism(
        current_envelope=source.body,
        max_envelope_bytes=admission.max_envelope_bytes,
        max_fabric_bytes=admission.max_fabric_bytes,
        max_logical_peak_bytes=admission.max_logical_peak_bytes,
    )
    readiness = runtime.readiness()
    if (
        readiness.identity != source.identity
        or readiness.organism_tick != source.organism_tick
        or readiness.state_bytes != len(source.body)
        or readiness.state_sha256 != source.body_sha256
        or readiness.python_callback_count != 0
        or runtime.live_organism_tick != source.organism_tick
        or runtime.save() != source.body
    ):
        raise RuntimeError("retired body failed exact native cold verification")
    world = home_world_authority(
        identity=source.identity,
        encoded_world=source.world,
    )
    if bytes(world.encoded_snapshot()) != source.world:
        raise RuntimeError("retired world changed during cold verification")

    store = PairedCurrentStore(
        new_root,
        max_body_bytes=admission.max_envelope_bytes,
        max_world_bytes=max_world_bytes,
    )
    pointer = store.publish(
        identity=source.identity,
        organism_tick=source.organism_tick,
        body=source.body,
        world=source.world,
        expected_current_body_sha256=None,
    )
    store.reconcile(pointer)
    restored = store.restore()
    if restored.body != source.body or restored.world != source.world:
        raise RuntimeError("paired CURRENT changed migrated bytes")
    return {
        "body_bytes": pointer.current.body_bytes,
        "body_sha256": pointer.current.body_sha256,
        "file_count": sum(1 for path in new_root.rglob("*") if path.is_file()),
        "identity": pointer.current.identity,
        "organism_tick": pointer.current.organism_tick,
        "schema": "guala.paired_current_migration.v1",
        "world_bytes": pointer.current.world_bytes,
        "world_sha256": pointer.current.world_sha256,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--new-root", type=Path, required=True)
    parser.add_argument("--max-body-bytes", type=int, required=True)
    parser.add_argument("--max-world-bytes", type=int, required=True)
    arguments = parser.parse_args()
    print(json.dumps(migrate(
        arguments.old_root,
        arguments.new_root,
        max_body_bytes=arguments.max_body_bytes,
        max_world_bytes=arguments.max_world_bytes,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
