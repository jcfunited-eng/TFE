from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from dsf_ai_service.substrate.immutable_generation_store import (
    MANIFEST_NAME,
    ImmutableGenerationStore,
    LoadedGeneration,
)
from tools.retired_legacy_s3_archive import (
    ARCHIVE_RECEIPT_NAME,
    ARCHIVE_ROOT_PREFIX,
    CONTENT_ADDRESSED_MODE,
    MAX_RETIRED_LEGACY_ARCHIVE_BYTES,
    STORED_OBJECT_MODE,
    RetiredLegacyArchiveError,
    archive_retired_legacy_generation,
    verify_retired_legacy_archive_receipt,
)


IDENTITY = "retired-legacy-archive-test-identity"
CONTENT_UUID = "00000000-0000-4000-8000-000000000731"
STORED_UUID = "00000000-0000-4000-8000-000000000732"
AUTHORITY_KEY = b"retired-legacy-archive-test-key-32-bytes"


class TrackingRemoteBody(io.BytesIO):
    def __init__(self, value: bytes, owner: "MemoryImmutableS3") -> None:
        super().__init__(value)
        self._owner = owner

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            raise AssertionError("archive attempted an unbounded S3 read")
        self._owner.maximum_remote_read = max(
            self._owner.maximum_remote_read,
            size,
        )
        return super().read(size)


class MemoryImmutableS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.put_count = 0
        self.put_attempt_count = 0
        self.get_count: dict[str, int] = {}
        self.fail_after_puts: int | None = None
        self.corrupt_after_put_key: str | None = None
        self.maximum_remote_read = 0
        self.streamed_put_keys: set[str] = set()
        self.maximum_put_read = 0

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body,
        ContentLength: int,
        IfNoneMatch: str,
    ) -> dict[str, object]:
        assert IfNoneMatch == "*"
        self.put_attempt_count += 1
        target = (Bucket, Key)
        if target in self.objects:
            raise RuntimeError("PreconditionFailed")
        if (
            self.fail_after_puts is not None
            and self.put_count >= self.fail_after_puts
        ):
            raise RuntimeError("injected immutable put failure")
        if isinstance(Body, bytes):
            data = Body
        else:
            self.streamed_put_keys.add(Key)
            parts: list[bytes] = []
            while True:
                request_bytes = 64 * 1024
                self.maximum_put_read = max(
                    self.maximum_put_read,
                    request_bytes,
                )
                block = Body.read(request_bytes)
                if not block:
                    break
                parts.append(block)
            data = b"".join(parts)
        assert len(data) == ContentLength
        self.objects[target] = data
        self.put_count += 1
        return {"ETag": "immutable-test-etag"}

    def get_object(self, *, Bucket: str, Key: str):
        target = (Bucket, Key)
        self.get_count[Key] = self.get_count.get(Key, 0) + 1
        body = self.objects[target]
        if (
            Key == self.corrupt_after_put_key
            and self.get_count[Key] >= 1
        ):
            body = body + b"corrupt"
        return {"Body": TrackingRemoteBody(body, self)}

    def list_objects_v2(
        self,
        *,
        Bucket: str,
        Prefix: str,
        ContinuationToken: str | None = None,
    ) -> dict[str, object]:
        assert ContinuationToken is None
        return {
            "Contents": [
                {"Key": key}
                for bucket, key in sorted(self.objects)
                if bucket == Bucket and key.startswith(Prefix)
            ],
            "IsTruncated": False,
        }


def _content_generation(root: Path) -> LoadedGeneration:
    store = ImmutableGenerationStore(
        root / "content-store",
        identity=IDENTITY,
        required_files=("brain.json", "shared-a.bin", "shared-b.bin"),
        content_addressed=True,
        max_encoded_generation_bytes=1024 * 1024,
    )
    shared = b"same exact learned neural state"
    return store.commit(
        tick=731,
        generation_uuid=CONTENT_UUID,
        files={
            "brain.json": (
                b'{"D_k":"1/2","M_k":"2/3","learned":"retained"}'
            ),
            "shared-a.bin": shared,
            "shared-b.bin": shared,
        },
    )


def _stored_generation(
    root: Path,
    *,
    object_count: int = 91,
    large_bytes: int = 5 * 1024 * 1024,
) -> LoadedGeneration:
    root.mkdir(parents=True, exist_ok=True)
    relative_paths = tuple(
        f"owner_state/owner-{index:03d}.bin"
        for index in range(object_count - 1)
    ) + ("guala_organism.sgr",)
    large = root / "large-source.sgr"
    with large.open("wb") as handle:
        handle.truncate(large_bytes)
    files: dict[str, object] = {
        path: f"owner-{index}".encode("utf-8")
        for index, path in enumerate(relative_paths[:-1])
    }
    files["guala_organism.sgr"] = large
    store = ImmutableGenerationStore(
        root / "stored-store",
        identity=IDENTITY,
        required_files=relative_paths,
        max_encoded_generation_bytes=(
            large_bytes + object_count * 4096
        ),
    )
    return store.commit(
        tick=732,
        generation_uuid=STORED_UUID,
        files=files,
    )


def _archive_keys(remote: MemoryImmutableS3) -> set[str]:
    return {
        key
        for bucket, key in remote.objects
        if bucket == "archive-bucket"
    }


def _archive_bytes(remote: MemoryImmutableS3, root: str) -> int:
    return sum(
        len(body)
        for (bucket, key), body in remote.objects.items()
        if bucket == "archive-bucket" and key.startswith(f"{root}/")
    )


def test_content_archive_binds_manifest_unique_chunks_and_read_back(
    tmp_path: Path,
) -> None:
    generation = _content_generation(tmp_path)
    remote = MemoryImmutableS3()

    result = archive_retired_legacy_generation(
        generation,
        s3_client=remote,
        bucket="archive-bucket",
        authority_key=AUTHORITY_KEY,
    )

    root = f"{ARCHIVE_ROOT_PREFIX}/{CONTENT_UUID}"
    receipt_key = f"{root}/{ARCHIVE_RECEIPT_NAME}"
    keys = _archive_keys(remote)
    assert f"{root}/{MANIFEST_NAME}" in keys
    assert receipt_key in keys
    assert result.source_storage_mode == CONTENT_ADDRESSED_MODE
    assert result.content_chunk_count == 2
    assert result.stored_generation_object_count == 0
    assert len(keys) == result.source_object_count + 2
    receipt = verify_retired_legacy_archive_receipt(
        remote.objects[("archive-bucket", receipt_key)],
        authority_key=AUTHORITY_KEY,
    )
    assert receipt["identity"] == IDENTITY
    assert receipt["tick"] == 731
    assert receipt["source_generation_uuid"] == CONTENT_UUID
    assert receipt["manifest"]["sha256"] == generation.manifest_sha256
    assert receipt["source_tree_sha256"] == result.source_tree_sha256
    assert receipt["source_storage_mode"] == CONTENT_ADDRESSED_MODE
    assert receipt["runtime_restore_available"] is False
    assert receipt["total_archive_bytes"] == _archive_bytes(remote, root)
    assert all(remote.get_count[key] >= 2 for key in keys)


def test_verified_91_object_stored_generation_is_streamed_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation = _stored_generation(tmp_path)
    remote = MemoryImmutableS3()

    def forbidden_stored_bytes(*_args, **_kwargs):
        raise AssertionError("large stored generation object entered RAM")

    monkeypatch.setattr(
        LoadedGeneration,
        "stored_bytes",
        forbidden_stored_bytes,
    )
    result = archive_retired_legacy_generation(
        generation,
        s3_client=remote,
        bucket="archive-bucket",
        authority_key=AUTHORITY_KEY,
    )

    root = f"{ARCHIVE_ROOT_PREFIX}/{STORED_UUID}"
    receipt_key = f"{root}/{ARCHIVE_RECEIPT_NAME}"
    keys = _archive_keys(remote)
    assert result.source_storage_mode == STORED_OBJECT_MODE
    assert result.content_chunk_count == 0
    assert result.stored_generation_object_count == 91
    assert result.source_object_count == 91
    assert len(keys) == 93
    assert f"{root}/guala_organism.sgr" in keys
    assert f"{root}/{MANIFEST_NAME}" in keys
    assert receipt_key in keys
    assert f"{root}/guala_organism.sgr" in remote.streamed_put_keys
    assert remote.maximum_put_read <= 64 * 1024
    assert remote.maximum_remote_read <= 1024 * 1024
    receipt = verify_retired_legacy_archive_receipt(
        remote.objects[("archive-bucket", receipt_key)],
        authority_key=AUTHORITY_KEY,
    )
    assert receipt["source_storage_mode"] == STORED_OBJECT_MODE
    assert receipt["source_object_count"] == 91
    assert receipt["total_archive_bytes"] == _archive_bytes(remote, root)
    assert all(
        record["role"] == "stored_generation_object"
        for record in receipt["source_objects"]
    )


@pytest.mark.parametrize(
    "factory",
    (_content_generation, _stored_generation),
)
def test_completed_archive_is_exact_idempotent_without_any_put_attempt(
    tmp_path: Path,
    factory,
) -> None:
    generation = factory(tmp_path)
    remote = MemoryImmutableS3()
    first = archive_retired_legacy_generation(
        generation,
        s3_client=remote,
        bucket="archive-bucket",
        authority_key=AUTHORITY_KEY,
    )
    before = dict(remote.objects)
    put_count = remote.put_count
    put_attempt_count = remote.put_attempt_count

    second = archive_retired_legacy_generation(
        generation,
        s3_client=remote,
        bucket="archive-bucket",
        authority_key=AUTHORITY_KEY,
    )

    assert second == first
    assert remote.objects == before
    assert remote.put_count == put_count
    assert remote.put_attempt_count == put_attempt_count


def test_interrupted_exact_prefix_resumes_without_rewriting_prior_objects(
    tmp_path: Path,
) -> None:
    generation = _stored_generation(
        tmp_path,
        object_count=3,
        large_bytes=1024,
    )
    remote = MemoryImmutableS3()
    remote.fail_after_puts = 1
    with pytest.raises(
        RetiredLegacyArchiveError,
        match="immutable streamed S3 creation failed",
    ):
        archive_retired_legacy_generation(
            generation,
            s3_client=remote,
            bucket="archive-bucket",
            authority_key=AUTHORITY_KEY,
        )
    retained = dict(remote.objects)
    assert len(retained) == 1

    remote.fail_after_puts = None
    archive_retired_legacy_generation(
        generation,
        s3_client=remote,
        bucket="archive-bucket",
        authority_key=AUTHORITY_KEY,
    )
    assert all(
        remote.objects[key] == body
        for key, body in retained.items()
    )


def test_stored_object_collision_and_unexpected_object_do_not_overwrite(
    tmp_path: Path,
) -> None:
    generation = _stored_generation(
        tmp_path,
        object_count=3,
        large_bytes=1024,
    )
    root = f"{ARCHIVE_ROOT_PREFIX}/{STORED_UUID}"
    remote = MemoryImmutableS3()
    remote.objects[
        ("archive-bucket", f"{root}/guala_organism.sgr")
    ] = b"different"
    before = dict(remote.objects)
    with pytest.raises(
        RetiredLegacyArchiveError,
        match="collision",
    ):
        archive_retired_legacy_generation(
            generation,
            s3_client=remote,
            bucket="archive-bucket",
            authority_key=AUTHORITY_KEY,
        )
    assert remote.objects == before
    assert remote.put_attempt_count == 0

    remote = MemoryImmutableS3()
    remote.objects[
        ("archive-bucket", f"{root}/unowned.bin")
    ] = b"unowned"
    before = dict(remote.objects)
    with pytest.raises(
        RetiredLegacyArchiveError,
        match="unexpected objects",
    ):
        archive_retired_legacy_generation(
            generation,
            s3_client=remote,
            bucket="archive-bucket",
            authority_key=AUTHORITY_KEY,
        )
    assert remote.objects == before


def test_streamed_read_back_corruption_fails_closed(
    tmp_path: Path,
) -> None:
    generation = _stored_generation(
        tmp_path,
        object_count=3,
        large_bytes=1024,
    )
    remote = MemoryImmutableS3()
    root = f"{ARCHIVE_ROOT_PREFIX}/{STORED_UUID}"
    remote.corrupt_after_put_key = f"{root}/guala_organism.sgr"
    with pytest.raises(
        RetiredLegacyArchiveError,
        match="streamed read-back differs",
    ):
        archive_retired_legacy_generation(
            generation,
            s3_client=remote,
            bucket="archive-bucket",
            authority_key=AUTHORITY_KEY,
        )


def test_capacity_is_preflighted_and_cannot_exceed_two_gib(
    tmp_path: Path,
) -> None:
    generation = _stored_generation(
        tmp_path,
        object_count=3,
        large_bytes=1024,
    )
    remote = MemoryImmutableS3()
    with pytest.raises(
        RetiredLegacyArchiveError,
        match="capacity",
    ):
        archive_retired_legacy_generation(
            generation,
            s3_client=remote,
            bucket="archive-bucket",
            authority_key=AUTHORITY_KEY,
            max_total_archive_bytes=64,
        )
    assert remote.objects == {}
    with pytest.raises(
        RetiredLegacyArchiveError,
        match="no greater than 2 GiB",
    ):
        archive_retired_legacy_generation(
            generation,
            s3_client=remote,
            bucket="archive-bucket",
            authority_key=AUTHORITY_KEY,
            max_total_archive_bytes=(
                MAX_RETIRED_LEGACY_ARCHIVE_BYTES + 1
            ),
        )


def test_receipt_tamper_and_verified_source_mutation_are_rejected(
    tmp_path: Path,
) -> None:
    generation = _content_generation(tmp_path)
    remote = MemoryImmutableS3()
    result = archive_retired_legacy_generation(
        generation,
        s3_client=remote,
        bucket="archive-bucket",
        authority_key=AUTHORITY_KEY,
    )
    changed = json.loads(result.receipt_bytes)
    changed["tick"] += 1
    with pytest.raises(
        RetiredLegacyArchiveError,
        match="authentication failed",
    ):
        verify_retired_legacy_archive_receipt(
            (
                json.dumps(
                    changed,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8"),
            authority_key=AUTHORITY_KEY,
        )

    stored = _stored_generation(
        tmp_path / "mutation",
        object_count=3,
        large_bytes=1024,
    )
    target = stored.directory / "guala_organism.sgr"
    target.chmod(0o644)
    target.write_bytes(b"changed")
    with pytest.raises(
        RetiredLegacyArchiveError,
        match="mutable or special|size changed",
    ):
        archive_retired_legacy_generation(
            stored,
            s3_client=MemoryImmutableS3(),
            bucket="archive-bucket",
            authority_key=AUTHORITY_KEY,
        )


def test_public_surface_contains_no_restore_or_activation_path() -> None:
    from tools import retired_legacy_s3_archive as archive_module

    assert all(
        forbidden not in name
        for name in archive_module.__all__
        for forbidden in ("restore", "materialize", "activate", "runtime")
    )
