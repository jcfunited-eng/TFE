from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate.deployment_generation import (
    delete_remote_generation_prefix,
    materialize_verified_generation,
    reconcile_remote_generation_prefixes,
    retire_verified_materialization,
    upload_verified_generation,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    CONTENT_CHUNK_BYTES,
    MANIFEST_NAME,
    ImmutableGenerationStore,
)


PAYLOAD_BYTES = 289 * 1024 * 1024
HMAC_KEY = b"content-addressed-test-key-material-32-bytes"
NONCE = b"content-addressed-test-nonce"


class MemoryS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, *, Bucket, Key, Body):
        self.objects[(Bucket, Key)] = bytes(Body)
        return {}

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def list_objects_v2(self, *, Bucket, Prefix, ContinuationToken=None):
        assert ContinuationToken is None
        return {
            "Contents": [
                {"Key": key}
                for bucket, key in sorted(self.objects)
                if bucket == Bucket and key.startswith(Prefix)
            ],
            "IsTruncated": False,
        }

    def delete_objects(self, *, Bucket, Delete):
        for record in Delete["Objects"]:
            self.objects.pop((Bucket, record["Key"]), None)
        return {"Deleted": list(Delete["Objects"])}


def _tree_bytes(path: Path) -> int:
    return sum(
        candidate.stat().st_size
        for candidate in path.rglob("*")
        if candidate.is_file() and not candidate.is_symlink()
    )


def _remote_bytes(client: MemoryS3) -> int:
    return sum(len(data) for data in client.objects.values())


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _generation_sha256(generation) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    for block in generation.iter_stored_chunks("payload.bin"):
        digest.update(block)
        size += len(block)
    return digest.hexdigest(), size


def test_289_mib_unchanged_and_one_chunk_mutation_are_not_rewritten(
        tmp_path: Path) -> None:
    source = tmp_path / "source.sgr"
    with source.open("wb") as handle:
        handle.truncate(PAYLOAD_BYTES)

    root = tmp_path / "cold"
    store = ImmutableGenerationStore(
        root,
        identity="content-addressed-cold-test",
        required_files=("payload.bin",),
        content_addressed=True,
        max_encoded_generation_bytes=PAYLOAD_BYTES + 1024 * 1024,
    )
    remote = MemoryS3()

    first = store.commit(tick=1, files={"payload.bin": source})
    upload_verified_generation(
        first,
        s3_client=remote,
        bucket="bucket",
        prefix="guala/generations",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )
    first_local_bytes = _tree_bytes(root)
    first_remote_bytes = _remote_bytes(remote)

    second = store.commit(tick=2, files={"payload.bin": source})
    upload_verified_generation(
        second,
        s3_client=remote,
        bucket="bucket",
        prefix="guala/generations",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )
    second_manifest_bytes = (
        second.directory / MANIFEST_NAME
    ).stat().st_size
    assert _tree_bytes(root) - first_local_bytes == second_manifest_bytes
    assert _remote_bytes(remote) - first_remote_bytes == second_manifest_bytes

    descriptor = os.open(source, os.O_WRONLY)
    try:
        os.pwrite(descriptor, b"\x01", CONTENT_CHUNK_BYTES + 17)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

    third = store.commit(tick=3, files={"payload.bin": source})
    upload_verified_generation(
        third,
        s3_client=remote,
        bucket="bucket",
        prefix="guala/generations",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )
    third_manifest_bytes = (
        third.directory / MANIFEST_NAME
    ).stat().st_size
    assert (
        _tree_bytes(root) - first_local_bytes - second_manifest_bytes
        == CONTENT_CHUNK_BYTES + third_manifest_bytes
    )
    assert (
        _remote_bytes(remote) - first_remote_bytes - second_manifest_bytes
        == CONTENT_CHUNK_BYTES + third_manifest_bytes
    )
    assert _generation_sha256(third) == (
        _file_sha256(source),
        PAYLOAD_BYTES,
    )
    active = tmp_path / "active"
    materialize_verified_generation(
        generation=third,
        active_directory=active,
    )
    runtime_receipt = active / "runtime-receipt.json"
    runtime_receipt.write_bytes(b'{"runtime":true}\n')
    assert (active / "payload.bin").stat().st_size == PAYLOAD_BYTES
    assert retire_verified_materialization(
        baseline=third,
        active_directory=active,
    ) == ("payload.bin",)
    assert not (active / "payload.bin").exists()
    assert runtime_receipt.read_bytes() == b'{"runtime":true}\n'

    store.prune_generations(retain=2, verified_current=third)
    retained = (second.generation_uuid, third.generation_uuid)
    reconcile_remote_generation_prefixes(
        s3_client=remote,
        bucket="bucket",
        prefix="guala/generations",
        retained_generation_uuids=retained,
        maximum_objects_per_generation=2,
    )
    assert {
        path.name
        for path in store.generations_directory.iterdir()
    } == set(retained)
    assert not tuple(root.rglob("*.tmp"))
    assert not tuple(root.rglob(".building-*"))
    assert not tuple(root.rglob("*.retired-*"))

    baseline_local = _tree_bytes(root)
    baseline_remote = _remote_bytes(remote)
    descriptor = os.open(source, os.O_WRONLY)
    try:
        os.pwrite(descriptor, b"\x02", 2 * CONTENT_CHUNK_BYTES + 19)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    candidate = store.commit(
        tick=4,
        files={"payload.bin": source},
        publish_current=False,
    )
    upload_verified_generation(
        candidate,
        s3_client=remote,
        bucket="bucket",
        prefix="guala/generations",
        hmac_key=HMAC_KEY,
        nonce=NONCE,
    )
    store.discard_unpublished(candidate)
    delete_remote_generation_prefix(
        s3_client=remote,
        bucket="bucket",
        prefix="guala/generations",
        generation_uuid=candidate.generation_uuid,
        maximum_objects=2,
    )
    reconcile_remote_generation_prefixes(
        s3_client=remote,
        bucket="bucket",
        prefix="guala/generations",
        retained_generation_uuids=retained,
        maximum_objects_per_generation=2,
    )
    assert _tree_bytes(root) == baseline_local
    assert _remote_bytes(remote) == baseline_remote
    assert not tuple(root.rglob("*.tmp"))
    assert not tuple(root.rglob(".building-*"))
