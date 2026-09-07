#!/usr/bin/env python3
"""One-time exact migration from raw paired CURRENT v1 to compressed v2."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import struct
import uuid

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.glew_runtime.native_resident_organism import (
    restore_native_resident_organism,
)
from dsf_ai_service.paired_current_store import (
    BODY_DIRECTORY,
    BODY_SUFFIX,
    PairedCurrentStore,
    WORLD_DIRECTORY,
    WORLD_SUFFIX,
)
from dsf_ai_service.substrate.native_resident_resource_admission import (
    derive_native_resident_resource_admission,
)


_V1_MAGIC = b"GLPAIR01"
_V1_VERSION = 1
_V1_BODY_DIRECTORY = "body-generations"
_V1_WORLD_DIRECTORY = "world-generations"
_V1_BODY_SUFFIX = ".glorun"
_V1_WORLD_SUFFIX = ".glworld"
_V1_RECORD = struct.Struct("<8sH36sQ32sQ32sQBQ32sQ32sQ")
_SHA256_BYTES = hashlib.sha256().digest_size
_V1_RECORD_BYTES = _V1_RECORD.size + _SHA256_BYTES


@dataclass(frozen=True, slots=True)
class V1CurrentPair:
    identity: str
    organism_tick: int
    body_sha256: str
    body: bytes
    world_sha256: str
    world: bytes


def _real_directory(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError(f"{label} is not a real directory")


def _real_file(path: Path, expected_bytes: int, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label} is not a real file")
    if path.stat().st_size != expected_bytes:
        raise RuntimeError(f"{label} changed byte count")
    body = path.read_bytes()
    if len(body) != expected_bytes:
        raise RuntimeError(f"{label} changed while read")
    return body


def _bounded_size(value: int, maximum: int, label: str) -> int:
    if value <= 0 or value > maximum:
        raise RuntimeError(f"{label} is outside its byte bound")
    return value


def _identity(raw: bytes) -> str:
    try:
        value = raw.decode("ascii")
        parsed = uuid.UUID(value)
    except (UnicodeDecodeError, ValueError, AttributeError) as error:
        raise RuntimeError("v1 CURRENT identity is invalid") from error
    if str(parsed) != value:
        raise RuntimeError("v1 CURRENT identity is not canonical")
    return value


def read_v1_current_pair(
    root: Path,
    *,
    max_body_bytes: int,
    max_world_bytes: int,
) -> V1CurrentPair:
    """Authenticate and read only the v1 CURRENT-selected raw pair."""

    _real_directory(root, "v1 paired root")
    pointer = _real_file(root / "CURRENT", _V1_RECORD_BYTES, "v1 CURRENT")
    record, receipt = pointer[:-_SHA256_BYTES], pointer[-_SHA256_BYTES:]
    if not hmac.compare_digest(receipt, hashlib.sha256(record).digest()):
        raise RuntimeError("v1 CURRENT checksum changed")
    (
        magic,
        version,
        raw_identity,
        organism_tick,
        body_digest,
        body_bytes,
        world_digest,
        world_bytes,
        has_predecessor,
        predecessor_tick,
        predecessor_body_digest,
        predecessor_body_bytes,
        predecessor_world_digest,
        predecessor_world_bytes,
    ) = _V1_RECORD.unpack(record)
    if magic != _V1_MAGIC or version != _V1_VERSION:
        raise RuntimeError("v1 CURRENT schema changed")
    identity = _identity(raw_identity)
    body_bytes = _bounded_size(body_bytes, max_body_bytes, "v1 body")
    world_bytes = _bounded_size(world_bytes, max_world_bytes, "v1 world")
    if has_predecessor not in (0, 1):
        raise RuntimeError("v1 CURRENT predecessor flag is invalid")
    if has_predecessor:
        _bounded_size(predecessor_body_bytes, max_body_bytes, "v1 predecessor body")
        _bounded_size(predecessor_world_bytes, max_world_bytes, "v1 predecessor world")
        if predecessor_tick > organism_tick:
            raise RuntimeError("v1 CURRENT predecessor tick is ahead")
        if not any(predecessor_body_digest) or not any(predecessor_world_digest):
            raise RuntimeError("v1 CURRENT predecessor receipt is empty")
    elif (
        predecessor_tick
        or predecessor_body_bytes
        or predecessor_world_bytes
        or any(predecessor_body_digest)
        or any(predecessor_world_digest)
    ):
        raise RuntimeError("v1 CURRENT has hidden predecessor values")

    _real_directory(root / _V1_BODY_DIRECTORY, "v1 body directory")
    _real_directory(root / _V1_WORLD_DIRECTORY, "v1 world directory")
    body_sha256 = body_digest.hex()
    world_sha256 = world_digest.hex()
    body = _real_file(
        root / _V1_BODY_DIRECTORY / f"{body_sha256}{_V1_BODY_SUFFIX}",
        body_bytes,
        "v1 current body",
    )
    world = _real_file(
        root / _V1_WORLD_DIRECTORY / f"{world_sha256}{_V1_WORLD_SUFFIX}",
        world_bytes,
        "v1 current world",
    )
    if not hmac.compare_digest(hashlib.sha256(body).digest(), body_digest):
        raise RuntimeError("v1 current body receipt changed")
    if not hmac.compare_digest(hashlib.sha256(world).digest(), world_digest):
        raise RuntimeError("v1 current world receipt changed")
    return V1CurrentPair(
        identity=identity,
        organism_tick=organism_tick,
        body_sha256=body_sha256,
        body=body,
        world_sha256=world_sha256,
        world=world,
    )


def migrate_v1_to_v2(
    old_root: Path,
    new_root: Path,
    *,
    max_body_bytes: int,
    max_world_bytes: int,
) -> dict[str, object]:
    if old_root.resolve() == new_root.resolve():
        raise RuntimeError("migration roots are identical")
    if new_root.exists() or new_root.is_symlink():
        raise RuntimeError("v2 destination already exists")
    source = read_v1_current_pair(
        old_root,
        max_body_bytes=max_body_bytes,
        max_world_bytes=max_world_bytes,
    )
    admission = derive_native_resident_resource_admission(new_root)
    if len(source.body) > admission.max_envelope_bytes:
        raise RuntimeError("v1 body exceeds live runtime admission")
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
        raise RuntimeError("v1 body failed exact native cold verification")
    world = home_world_authority(
        identity=source.identity,
        encoded_world=source.world,
    )
    if bytes(world.encoded_snapshot()) != source.world:
        raise RuntimeError("v1 world changed during cold verification")

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
        raise RuntimeError("v2 paired CURRENT changed migrated bytes")
    stored_body = (
        new_root
        / BODY_DIRECTORY
        / f"{pointer.current.body_sha256}{BODY_SUFFIX}"
    )
    stored_world = (
        new_root
        / WORLD_DIRECTORY
        / f"{pointer.current.world_sha256}{WORLD_SUFFIX}"
    )
    return {
        "identity": pointer.current.identity,
        "organism_tick": pointer.current.organism_tick,
        "raw_body_bytes": pointer.current.body_bytes,
        "body_sha256": pointer.current.body_sha256,
        "stored_body_bytes": stored_body.stat().st_size,
        "world_bytes": pointer.current.world_bytes,
        "world_sha256": pointer.current.world_sha256,
        "stored_world_bytes": stored_world.stat().st_size,
        "file_count": sum(1 for path in new_root.rglob("*") if path.is_file()),
        "python_callback_count": readiness.python_callback_count,
        "schema": "guala.paired_current_v1_to_v2.v1",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--new-root", type=Path, required=True)
    parser.add_argument("--max-body-bytes", type=int, required=True)
    parser.add_argument("--max-world-bytes", type=int, required=True)
    arguments = parser.parse_args()
    print(json.dumps(migrate_v1_to_v2(
        arguments.old_root,
        arguments.new_root,
        max_body_bytes=arguments.max_body_bytes,
        max_world_bytes=arguments.max_world_bytes,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
