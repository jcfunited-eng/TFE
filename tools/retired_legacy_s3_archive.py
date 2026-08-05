"""Immutable S3 custody for one retired verified generation.

This module is migration tooling.  It has no runtime restore, materialization,
or activation surface.  It archives either immutable-generation storage form:

* ``immutable_generation_manifest_v1``: the exact manifest and every exact
  stored generation object beneath that manifest;
* ``immutable_generation_content_manifest_v2``: the exact manifest and every
  unique content chunk referenced by that manifest.

Large non-content-addressed objects are hashed, uploaded, and read back as
streams.  They are never assembled in memory.  Objects are created only with
``IfNoneMatch="*"``.  An exact pre-existing object is accepted, making both
interrupted and completed calls idempotent.  Different or unexpected objects
fail closed and are never overwritten.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping

from dsf_ai_service.substrate.immutable_generation_store import (
    CONTENT_CHUNK_SCHEMA,
    CONTENT_FILE_RECORD_SCHEMA,
    CONTENT_MANIFEST_SCHEMA,
    FILE_RECORD_SCHEMA,
    MANIFEST_NAME,
    MANIFEST_SCHEMA,
    LoadedGeneration,
)


ARCHIVE_ROOT_PREFIX = "retired-legacy-archive"
ARCHIVE_RECEIPT_NAME = "RETIREMENT_RECEIPT.json"
ARCHIVE_RECEIPT_SCHEMA = "guala.retired_legacy_s3_archive.receipt.v2"
MAX_RETIRED_LEGACY_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024

CONTENT_ADDRESSED_MODE = "content_addressed_chunks"
STORED_OBJECT_MODE = "stored_generation_objects"

_STREAM_BYTES = 1024 * 1024
_TREE_DOMAIN = b"guala-retired-legacy-s3-archive-tree-v2\0"
_HMAC_KEY_DOMAIN = b"guala-retired-legacy-s3-archive-key-v1\0"
_HMAC_BODY_DOMAIN = b"guala-retired-legacy-s3-archive-receipt-v2\0"
_HEX = frozenset("0123456789abcdef")
_MANIFEST_KEYS = {
    "schema",
    "generation_uuid",
    "identity",
    "tick",
    "required_files",
}
_CONTENT_FILE_KEYS = {
    "schema",
    "generation_uuid",
    "identity",
    "tick",
    "relative_path",
    "sha256",
    "size_bytes",
    "json_payload",
    "chunks",
}
_STORED_FILE_KEYS = {
    "schema",
    "generation_uuid",
    "identity",
    "tick",
    "relative_path",
    "sha256",
    "size_bytes",
}
_CONTENT_CHUNK_KEYS = {"schema", "sha256", "size_bytes"}
_OBJECT_RECORD_KEYS = {
    "key",
    "role",
    "sha256",
    "size_bytes",
    "source_relative_path",
}
_RECEIPT_KEYS = {
    "algorithm",
    "archive_role",
    "bucket",
    "content_bytes",
    "identity",
    "manifest",
    "max_total_archive_bytes",
    "receipt_hmac_sha256",
    "receipt_key",
    "receipt_size_bytes",
    "runtime_restore_available",
    "schema",
    "source_generation_uuid",
    "source_object_count",
    "source_objects",
    "source_storage_mode",
    "source_tree_sha256",
    "tick",
    "total_archive_bytes",
    "versioned_prefix",
}


class RetiredLegacyArchiveError(RuntimeError):
    """The retired-generation archive could not be proven exact."""


@dataclass(frozen=True, slots=True)
class RetiredLegacyArchiveResult:
    """Authenticated result of one complete immutable archive operation."""

    bucket: str
    versioned_prefix: str
    source_generation_uuid: str
    identity: str
    tick: int
    source_storage_mode: str
    source_tree_sha256: str
    manifest_sha256: str
    content_chunk_count: int
    stored_generation_object_count: int
    source_object_count: int
    total_archive_bytes: int
    receipt_key: str
    receipt_hmac_sha256: str
    receipt_bytes: bytes


@dataclass(frozen=True, slots=True)
class _SourceObject:
    key: str
    role: str
    source_relative_path: str
    sha256: str
    size_bytes: int

    def record(self) -> dict[str, object]:
        return {
            "key": self.key,
            "role": self.role,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "source_relative_path": self.source_relative_path,
        }


@dataclass(frozen=True, slots=True)
class _LocalFileIdentity:
    device: int
    inode: int
    size_bytes: int
    mode: int
    link_count: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> "_LocalFileIdentity":
        return cls(
            device=value.st_dev,
            inode=value.st_ino,
            size_bytes=value.st_size,
            mode=value.st_mode,
            link_count=value.st_nlink,
            modified_ns=value.st_mtime_ns,
            changed_ns=value.st_ctime_ns,
        )


def _canonical(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise RetiredLegacyArchiveError(
            "archive receipt is not canonically serializable"
        ) from error


def _generation_canonical(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise RetiredLegacyArchiveError(
            "source manifest is not canonically serializable"
        ) from error


def _strict_json(data: bytes, description: str) -> object:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite constant {value}")

    try:
        return json.loads(
            data.decode("utf-8"),
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise RetiredLegacyArchiveError(
            f"{description} is not strict UTF-8 JSON"
        ) from error


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validated_digest(value: object, description: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise RetiredLegacyArchiveError(
            f"{description} is not a lowercase SHA-256 digest"
        )
    return value


def _size(value: object, description: str, *, allow_zero: bool) -> int:
    minimum = 0 if allow_zero else 1
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
    ):
        raise RetiredLegacyArchiveError(f"{description} is invalid")
    return value


def _positive_capacity(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > MAX_RETIRED_LEGACY_ARCHIVE_BYTES
    ):
        raise RetiredLegacyArchiveError(
            "archive capacity must be positive and no greater than 2 GiB"
        )
    return value


def _identity(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise RetiredLegacyArchiveError(
            "source generation identity is invalid"
        )
    return value


def _tick(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RetiredLegacyArchiveError(
            "source generation tick is invalid"
        )
    return value


def _authority_key(value: bytes | bytearray | memoryview | str) -> bytes:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
    else:
        raise RetiredLegacyArchiveError(
            "archive HMAC authority key must be bytes or text"
        )
    if not 32 <= len(raw) <= 4096:
        raise RetiredLegacyArchiveError(
            "archive HMAC authority key must contain 32 to 4096 bytes"
        )
    return hmac.new(
        raw,
        _HMAC_KEY_DOMAIN,
        hashlib.sha256,
    ).digest()


def _prefix(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise RetiredLegacyArchiveError(
            "archive root prefix must be a non-empty string"
        )
    if value != value.strip("/"):
        raise RetiredLegacyArchiveError(
            "archive root prefix must not have boundary slashes"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise RetiredLegacyArchiveError(
            "archive root prefix is not canonical"
        )
    return value


def _relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RetiredLegacyArchiveError(
            "source generation object path is invalid"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise RetiredLegacyArchiveError(
            "source generation object path is noncanonical"
        )
    return value


def _bucket(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise RetiredLegacyArchiveError(
            "archive S3 bucket must be a non-empty string"
        )
    return value


def _list_keys(client: Any, bucket: str, prefix: str) -> set[str]:
    keys: set[str] = set()
    continuation: str | None = None
    seen_tokens: set[str] = set()
    while True:
        arguments: dict[str, object] = {
            "Bucket": bucket,
            "Prefix": prefix,
        }
        if continuation is not None:
            arguments["ContinuationToken"] = continuation
        try:
            response = client.list_objects_v2(**arguments)
        except Exception as error:
            raise RetiredLegacyArchiveError(
                "retired archive S3 prefix could not be listed"
            ) from error
        if not isinstance(response, Mapping):
            raise RetiredLegacyArchiveError(
                "S3 list_objects_v2 returned a non-object"
            )
        for record in response.get("Contents") or ():
            if (
                not isinstance(record, Mapping)
                or not isinstance(record.get("Key"), str)
            ):
                raise RetiredLegacyArchiveError(
                    "retired archive S3 listing is malformed"
                )
            keys.add(record["Key"])
        if not response.get("IsTruncated", False):
            return keys
        next_token = response.get("NextContinuationToken")
        if (
            not isinstance(next_token, str)
            or not next_token
            or next_token in seen_tokens
        ):
            raise RetiredLegacyArchiveError(
                "retired archive S3 listing pagination is invalid"
            )
        seen_tokens.add(next_token)
        continuation = next_token


def _remote_measurement(
    client: Any,
    bucket: str,
    key: str,
    *,
    maximum_bytes: int,
) -> tuple[str, int]:
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception as error:
        raise RetiredLegacyArchiveError(
            f"S3 object {key!r} could not be read"
        ) from error
    if not isinstance(response, Mapping) or "Body" not in response:
        raise RetiredLegacyArchiveError(
            f"S3 get_object returned no Body for {key!r}"
        )
    body = response["Body"]
    if isinstance(body, bytes):
        body = __import__("io").BytesIO(body)
    read = getattr(body, "read", None)
    if not callable(read):
        raise RetiredLegacyArchiveError(
            f"S3 object body is not readable for {key!r}"
        )
    digest = hashlib.sha256()
    total = 0
    try:
        while True:
            block = read(_STREAM_BYTES)
            if not isinstance(block, bytes):
                raise RetiredLegacyArchiveError(
                    f"S3 object body returned non-bytes for {key!r}"
                )
            if not block:
                break
            total += len(block)
            if total > maximum_bytes:
                raise RetiredLegacyArchiveError(
                    f"S3 object {key!r} exceeds its receipt size"
                )
            digest.update(block)
    finally:
        close = getattr(body, "close", None)
        if callable(close):
            close()
    return digest.hexdigest(), total


def _assert_remote(
    client: Any,
    bucket: str,
    record: Mapping[str, object],
    *,
    collision_description: str,
) -> None:
    expected_digest = _validated_digest(
        record.get("sha256"),
        f"{collision_description} digest",
    )
    expected_size = _size(
        record.get("size_bytes"),
        f"{collision_description} size",
        allow_zero=True,
    )
    digest, size = _remote_measurement(
        client,
        bucket,
        str(record["key"]),
        maximum_bytes=expected_size,
    )
    if digest != expected_digest or size != expected_size:
        raise RetiredLegacyArchiveError(
            f"{collision_description} collision at {record['key']!r}"
        )


def _put_bytes_once(
    client: Any,
    bucket: str,
    record: Mapping[str, object],
    body: bytes,
) -> None:
    key = str(record["key"])
    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentLength=len(body),
            IfNoneMatch="*",
        )
    except Exception as error:
        try:
            _assert_remote(
                client,
                bucket,
                record,
                collision_description="immutable S3 object",
            )
        except RetiredLegacyArchiveError as collision:
            raise RetiredLegacyArchiveError(
                f"immutable S3 creation failed for {key!r}"
            ) from error
        return
    try:
        _assert_remote(
            client,
            bucket,
            record,
            collision_description="S3 read-back",
        )
    except RetiredLegacyArchiveError as error:
        raise RetiredLegacyArchiveError(
            f"S3 read-back differs after immutable creation of {key!r}"
        ) from error


def _local_identity(
    value: os.stat_result,
    path: Path,
) -> _LocalFileIdentity:
    if (
        not stat.S_ISREG(value.st_mode)
        or stat.S_IMODE(value.st_mode) != 0o444
        or value.st_nlink != 1
        or path.is_symlink()
    ):
        raise RetiredLegacyArchiveError(
            f"source generation object {path} is mutable or special"
        )
    return _LocalFileIdentity.from_stat(value)


def _measure_local_file(
    path: Path,
    *,
    expected_sha256: str,
    expected_size: int,
) -> _LocalFileIdentity:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        first = os.fstat(descriptor)
        identity = _local_identity(first, path)
        if identity.size_bytes != expected_size:
            raise RetiredLegacyArchiveError(
                f"source generation object {path} size changed"
            )
        digest = hashlib.sha256()
        total = 0
        while True:
            block = os.read(descriptor, _STREAM_BYTES)
            if not block:
                break
            total += len(block)
            if total > expected_size:
                raise RetiredLegacyArchiveError(
                    f"source generation object {path} grew while hashed"
                )
            digest.update(block)
        final = _LocalFileIdentity.from_stat(os.fstat(descriptor))
        if (
            final != identity
            or total != expected_size
            or digest.hexdigest() != expected_sha256
        ):
            raise RetiredLegacyArchiveError(
                f"source generation object {path} changed after verification"
            )
        return identity
    except OSError as error:
        raise RetiredLegacyArchiveError(
            f"source generation object {path} cannot be verified"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


@contextlib.contextmanager
def _open_verified_local_file(
    path: Path,
    identity: _LocalFileIdentity,
) -> Iterator[Any]:
    descriptor: int | None = None
    handle = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        if _local_identity(os.fstat(descriptor), path) != identity:
            raise RetiredLegacyArchiveError(
                f"source generation object {path} changed before upload"
            )
        handle = os.fdopen(descriptor, "rb", closefd=True)
        descriptor = None
        yield handle
        if _LocalFileIdentity.from_stat(os.fstat(handle.fileno())) != identity:
            raise RetiredLegacyArchiveError(
                f"source generation object {path} changed during upload"
            )
    except OSError as error:
        raise RetiredLegacyArchiveError(
            f"source generation object {path} cannot be streamed"
        ) from error
    finally:
        if handle is not None:
            handle.close()
        if descriptor is not None:
            os.close(descriptor)


def _put_file_once(
    client: Any,
    bucket: str,
    record: Mapping[str, object],
    path: Path,
    identity: _LocalFileIdentity,
) -> None:
    key = str(record["key"])
    try:
        with _open_verified_local_file(path, identity) as handle:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=handle,
                ContentLength=identity.size_bytes,
                IfNoneMatch="*",
            )
    except RetiredLegacyArchiveError:
        raise
    except Exception as error:
        try:
            _assert_remote(
                client,
                bucket,
                record,
                collision_description="immutable S3 object",
            )
        except RetiredLegacyArchiveError:
            raise RetiredLegacyArchiveError(
                f"immutable streamed S3 creation failed for {key!r}"
            ) from error
        return
    try:
        _assert_remote(
            client,
            bucket,
            record,
            collision_description="S3 streamed read-back",
        )
    except RetiredLegacyArchiveError as error:
        raise RetiredLegacyArchiveError(
            f"S3 streamed read-back differs for {key!r}"
        ) from error


def _assert_local_unchanged(
    path: Path,
    identity: _LocalFileIdentity,
) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        if _local_identity(os.fstat(descriptor), path) != identity:
            raise RetiredLegacyArchiveError(
                f"source generation object {path} changed during archive"
            )
    except OSError as error:
        raise RetiredLegacyArchiveError(
            f"source generation object {path} cannot be reverified"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _read_manifest(
    generation: LoadedGeneration,
    maximum: int,
) -> tuple[bytes, dict[str, object]]:
    if not isinstance(generation, LoadedGeneration):
        raise TypeError(
            "generation must be a fully verified LoadedGeneration"
        )
    manifest_path = generation.directory / MANIFEST_NAME
    try:
        info = manifest_path.lstat()
        manifest_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise RetiredLegacyArchiveError(
            "source generation manifest cannot be read"
        ) from error
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o444
        or info.st_nlink != 1
        or manifest_path.is_symlink()
        or len(manifest_bytes) != info.st_size
        or len(manifest_bytes) > maximum
        or _digest(manifest_bytes) != generation.manifest_sha256
    ):
        raise RetiredLegacyArchiveError(
            "source generation manifest changed or exceeds archive capacity"
        )
    manifest = _strict_json(
        manifest_bytes,
        "source generation manifest",
    )
    if (
        not isinstance(manifest, dict)
        or set(manifest) != _MANIFEST_KEYS
        or manifest.get("schema")
        not in {MANIFEST_SCHEMA, CONTENT_MANIFEST_SCHEMA}
        or manifest.get("generation_uuid") != generation.generation_uuid
        or manifest.get("identity") != generation.identity
        or manifest.get("tick") != generation.tick
        or _generation_canonical(manifest) != manifest_bytes
    ):
        raise RetiredLegacyArchiveError(
            "source generation manifest contract changed"
        )
    return manifest_bytes, manifest


def _content_chunk_sources(
    generation: LoadedGeneration,
    manifest: Mapping[str, object],
    versioned_prefix: str,
) -> tuple[_SourceObject, ...]:
    records = manifest.get("required_files")
    if not isinstance(records, list) or not records:
        raise RetiredLegacyArchiveError(
            "source content manifest has no required files"
        )
    chunks: dict[str, int] = {}
    required_paths: list[str] = []
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != _CONTENT_FILE_KEYS
            or record.get("schema") != CONTENT_FILE_RECORD_SCHEMA
            or record.get("generation_uuid")
            != generation.generation_uuid
            or record.get("identity") != generation.identity
            or record.get("tick") != generation.tick
        ):
            raise RetiredLegacyArchiveError(
                "source content manifest file record changed"
            )
        required_paths.append(
            _relative_path(record.get("relative_path"))
        )
        raw_chunks = record.get("chunks")
        if not isinstance(raw_chunks, list):
            raise RetiredLegacyArchiveError(
                "source content manifest chunk list is invalid"
            )
        for chunk in raw_chunks:
            if (
                not isinstance(chunk, dict)
                or set(chunk) != _CONTENT_CHUNK_KEYS
                or chunk.get("schema") != CONTENT_CHUNK_SCHEMA
            ):
                raise RetiredLegacyArchiveError(
                    "source content manifest chunk record changed"
                )
            digest = _validated_digest(
                chunk.get("sha256"),
                "source content chunk digest",
            )
            size = _size(
                chunk.get("size_bytes"),
                "source content chunk size",
                allow_zero=False,
            )
            prior = chunks.setdefault(digest, size)
            if prior != size:
                raise RetiredLegacyArchiveError(
                    "source content chunk has conflicting sizes"
                )
    if tuple(required_paths) != generation.required_files:
        raise RetiredLegacyArchiveError(
            "source manifest paths differ from verified generation"
        )
    return tuple(
        _SourceObject(
            key=(
                f"{versioned_prefix}/content-chunks/"
                f"{digest[:2]}/{digest}"
            ),
            role="content_chunk",
            source_relative_path=f"content-chunks/{digest[:2]}/{digest}",
            sha256=digest,
            size_bytes=size,
        )
        for digest, size in sorted(chunks.items())
    )


def _stored_object_sources(
    generation: LoadedGeneration,
    manifest: Mapping[str, object],
    versioned_prefix: str,
) -> tuple[_SourceObject, ...]:
    records = manifest.get("required_files")
    if not isinstance(records, list) or not records:
        raise RetiredLegacyArchiveError(
            "source stored-object manifest has no required files"
        )
    result: list[_SourceObject] = []
    paths: list[str] = []
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != _STORED_FILE_KEYS
            or record.get("schema") != FILE_RECORD_SCHEMA
            or record.get("generation_uuid")
            != generation.generation_uuid
            or record.get("identity") != generation.identity
            or record.get("tick") != generation.tick
        ):
            raise RetiredLegacyArchiveError(
                "source stored generation object record changed"
            )
        relative = _relative_path(record.get("relative_path"))
        paths.append(relative)
        result.append(
            _SourceObject(
                key=f"{versioned_prefix}/{relative}",
                role="stored_generation_object",
                source_relative_path=relative,
                sha256=_validated_digest(
                    record.get("sha256"),
                    "source stored generation object digest",
                ),
                size_bytes=_size(
                    record.get("size_bytes"),
                    "source stored generation object size",
                    allow_zero=True,
                ),
            )
        )
    if tuple(paths) != generation.required_files:
        raise RetiredLegacyArchiveError(
            "source manifest paths differ from verified generation"
        )
    return tuple(result)


def _tree_sha256(
    storage_mode: str,
    manifest_record: Mapping[str, object],
    source_records: tuple[dict[str, object], ...],
) -> str:
    tree = {
        "manifest": dict(manifest_record),
        "source_objects": list(source_records),
        "source_storage_mode": storage_mode,
    }
    return hashlib.sha256(_TREE_DOMAIN + _canonical(tree)).hexdigest()


def _signed_receipt(
    body: dict[str, object],
    key: bytes,
    maximum: int,
) -> bytes:
    receipt_size = 0
    total_size = int(body["content_bytes"])
    for _attempt in range(16):
        unsigned = {
            **body,
            "receipt_size_bytes": receipt_size,
            "total_archive_bytes": total_size,
        }
        signature = hmac.new(
            key,
            _HMAC_BODY_DOMAIN + _canonical(unsigned),
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical(
            {
                **unsigned,
                "receipt_hmac_sha256": signature,
            }
        )
        next_receipt_size = len(encoded)
        next_total_size = int(body["content_bytes"]) + next_receipt_size
        if (
            next_receipt_size == receipt_size
            and next_total_size == total_size
        ):
            if next_total_size > maximum:
                raise RetiredLegacyArchiveError(
                    "retired archive exceeds configured byte capacity"
                )
            return encoded
        receipt_size = next_receipt_size
        total_size = next_total_size
    raise RetiredLegacyArchiveError(
        "retired archive receipt size did not settle"
    )


def verify_retired_legacy_archive_receipt(
    receipt_bytes: bytes,
    *,
    authority_key: bytes | bytearray | memoryview | str,
) -> dict[str, object]:
    """Authenticate a receipt without exposing archived state restoration."""

    if not isinstance(receipt_bytes, bytes):
        raise TypeError("archive receipt must be bytes")
    receipt = _strict_json(receipt_bytes, "retired archive receipt")
    if (
        not isinstance(receipt, dict)
        or set(receipt) != _RECEIPT_KEYS
        or receipt.get("schema") != ARCHIVE_RECEIPT_SCHEMA
        or receipt.get("algorithm") != "HMAC-SHA256"
        or receipt.get("archive_role")
        != "retired_nonactive_evidence_only"
        or receipt.get("runtime_restore_available") is not False
        or _canonical(receipt) != receipt_bytes
    ):
        raise RetiredLegacyArchiveError(
            "retired archive receipt contract changed"
        )
    supplied = _validated_digest(
        receipt["receipt_hmac_sha256"],
        "archive receipt HMAC",
    )
    unsigned = dict(receipt)
    del unsigned["receipt_hmac_sha256"]
    expected = hmac.new(
        _authority_key(authority_key),
        _HMAC_BODY_DOMAIN + _canonical(unsigned),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise RetiredLegacyArchiveError(
            "retired archive receipt authentication failed"
        )

    versioned_prefix = _prefix(receipt.get("versioned_prefix"))
    source_generation_uuid = receipt.get("source_generation_uuid")
    if (
        not isinstance(source_generation_uuid, str)
        or not source_generation_uuid
        or versioned_prefix.rsplit("/", 1)[-1]
        != source_generation_uuid
    ):
        raise RetiredLegacyArchiveError(
            "retired archive receipt generation prefix changed"
        )
    _bucket(receipt.get("bucket"))
    _identity(receipt.get("identity"))
    _tick(receipt.get("tick"))
    if (
        receipt.get("receipt_key")
        != f"{versioned_prefix}/{ARCHIVE_RECEIPT_NAME}"
    ):
        raise RetiredLegacyArchiveError(
            "retired archive receipt key changed"
        )
    storage_mode = receipt.get("source_storage_mode")
    if storage_mode not in {CONTENT_ADDRESSED_MODE, STORED_OBJECT_MODE}:
        raise RetiredLegacyArchiveError(
            "retired archive storage mode changed"
        )

    manifest = receipt.get("manifest")
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"key", "sha256", "size_bytes"}
        or manifest.get("key") != f"{versioned_prefix}/{MANIFEST_NAME}"
    ):
        raise RetiredLegacyArchiveError(
            "retired archive receipt manifest record changed"
        )
    _validated_digest(
        manifest.get("sha256"),
        "archive manifest digest",
    )
    manifest_size = _size(
        manifest.get("size_bytes"),
        "retired archive manifest size",
        allow_zero=False,
    )

    raw_objects = receipt.get("source_objects")
    if not isinstance(raw_objects, list):
        raise RetiredLegacyArchiveError(
            "retired archive source object records changed"
        )
    objects: list[dict[str, object]] = []
    sort_keys: list[str] = []
    object_bytes = 0
    expected_role = (
        "content_chunk"
        if storage_mode == CONTENT_ADDRESSED_MODE
        else "stored_generation_object"
    )
    for raw in raw_objects:
        if not isinstance(raw, dict) or set(raw) != _OBJECT_RECORD_KEYS:
            raise RetiredLegacyArchiveError(
                "retired archive source object record changed"
            )
        role = raw.get("role")
        relative = _relative_path(raw.get("source_relative_path"))
        digest = _validated_digest(
            raw.get("sha256"),
            "archive source object digest",
        )
        size = _size(
            raw.get("size_bytes"),
            "archive source object size",
            allow_zero=storage_mode == STORED_OBJECT_MODE,
        )
        if storage_mode == CONTENT_ADDRESSED_MODE:
            expected_relative = (
                f"content-chunks/{digest[:2]}/{digest}"
            )
        else:
            expected_relative = relative
        expected_key = f"{versioned_prefix}/{expected_relative}"
        if (
            role != expected_role
            or relative != expected_relative
            or raw.get("key") != expected_key
        ):
            raise RetiredLegacyArchiveError(
                "retired archive source object location changed"
            )
        objects.append(dict(raw))
        sort_keys.append(relative)
        object_bytes += size
    if sort_keys != sorted(set(sort_keys)):
        raise RetiredLegacyArchiveError(
            "retired archive source objects are duplicated or unordered"
        )
    source_object_count = receipt.get("source_object_count")
    content_bytes = receipt.get("content_bytes")
    if (
        isinstance(source_object_count, bool)
        or not isinstance(source_object_count, int)
        or source_object_count != len(objects)
        or isinstance(content_bytes, bool)
        or not isinstance(content_bytes, int)
        or content_bytes != manifest_size + object_bytes
    ):
        raise RetiredLegacyArchiveError(
            "retired archive content accounting changed"
        )
    tree_sha256 = _validated_digest(
        receipt.get("source_tree_sha256"),
        "archive source tree digest",
    )
    if tree_sha256 != _tree_sha256(
        str(storage_mode),
        manifest,
        tuple(objects),
    ):
        raise RetiredLegacyArchiveError(
            "retired archive source tree binding changed"
        )

    receipt_size = receipt.get("receipt_size_bytes")
    total_bytes = receipt.get("total_archive_bytes")
    maximum = _positive_capacity(receipt.get("max_total_archive_bytes"))
    if (
        isinstance(receipt_size, bool)
        or not isinstance(receipt_size, int)
        or receipt_size != len(receipt_bytes)
        or isinstance(total_bytes, bool)
        or not isinstance(total_bytes, int)
        or total_bytes != content_bytes + receipt_size
        or total_bytes > maximum
    ):
        raise RetiredLegacyArchiveError(
            "retired archive receipt byte accounting changed"
        )
    return dict(receipt)


def archive_retired_legacy_generation(
    generation: LoadedGeneration,
    *,
    s3_client: Any,
    bucket: str,
    authority_key: bytes | bytearray | memoryview | str,
    archive_root_prefix: str = ARCHIVE_ROOT_PREFIX,
    max_total_archive_bytes: int = MAX_RETIRED_LEGACY_ARCHIVE_BYTES,
) -> RetiredLegacyArchiveResult:
    """Copy, stream-read back, and authenticate one retired generation."""

    maximum = _positive_capacity(max_total_archive_bytes)
    actual_bucket = _bucket(bucket)
    root_prefix = _prefix(archive_root_prefix)
    key = _authority_key(authority_key)
    manifest_bytes, manifest = _read_manifest(generation, maximum)
    versioned_prefix = f"{root_prefix}/{generation.generation_uuid}"
    manifest_key = f"{versioned_prefix}/{MANIFEST_NAME}"
    receipt_key = f"{versioned_prefix}/{ARCHIVE_RECEIPT_NAME}"
    manifest_record = {
        "key": manifest_key,
        "sha256": generation.manifest_sha256,
        "size_bytes": len(manifest_bytes),
    }

    if manifest["schema"] == CONTENT_MANIFEST_SCHEMA:
        storage_mode = CONTENT_ADDRESSED_MODE
        sources = _content_chunk_sources(
            generation,
            manifest,
            versioned_prefix,
        )
    else:
        storage_mode = STORED_OBJECT_MODE
        sources = _stored_object_sources(
            generation,
            manifest,
            versioned_prefix,
        )
    source_records = tuple(source.record() for source in sources)
    content_bytes = len(manifest_bytes) + sum(
        source.size_bytes for source in sources
    )
    if content_bytes > maximum:
        raise RetiredLegacyArchiveError(
            "retired archive content exceeds configured byte capacity"
        )

    local_identities: dict[str, _LocalFileIdentity] = {}
    if storage_mode == STORED_OBJECT_MODE:
        for source in sources:
            path = generation.directory / Path(
                source.source_relative_path
            )
            local_identities[source.source_relative_path] = (
                _measure_local_file(
                    path,
                    expected_sha256=source.sha256,
                    expected_size=source.size_bytes,
                )
            )

    tree_sha256 = _tree_sha256(
        storage_mode,
        manifest_record,
        source_records,
    )
    receipt_body = {
        "algorithm": "HMAC-SHA256",
        "archive_role": "retired_nonactive_evidence_only",
        "bucket": actual_bucket,
        "content_bytes": content_bytes,
        "identity": _identity(generation.identity),
        "manifest": manifest_record,
        "max_total_archive_bytes": maximum,
        "receipt_key": receipt_key,
        "runtime_restore_available": False,
        "schema": ARCHIVE_RECEIPT_SCHEMA,
        "source_generation_uuid": generation.generation_uuid,
        "source_object_count": len(sources),
        "source_objects": list(source_records),
        "source_storage_mode": storage_mode,
        "source_tree_sha256": tree_sha256,
        "tick": _tick(generation.tick),
        "versioned_prefix": versioned_prefix,
    }
    receipt_bytes = _signed_receipt(receipt_body, key, maximum)
    receipt = verify_retired_legacy_archive_receipt(
        receipt_bytes,
        authority_key=authority_key,
    )
    receipt_record = {
        "key": receipt_key,
        "sha256": _digest(receipt_bytes),
        "size_bytes": len(receipt_bytes),
    }

    records_by_key: dict[str, Mapping[str, object]] = {
        manifest_key: manifest_record,
        receipt_key: receipt_record,
        **{source.key: source.record() for source in sources},
    }
    expected_keys = set(records_by_key)
    listing_prefix = f"{versioned_prefix}/"
    existing_keys = _list_keys(
        s3_client,
        actual_bucket,
        listing_prefix,
    )
    unexpected = existing_keys - expected_keys
    if unexpected:
        raise RetiredLegacyArchiveError(
            "retired archive prefix contains unexpected objects: "
            + ", ".join(sorted(unexpected))
        )
    for existing_key in sorted(existing_keys):
        _assert_remote(
            s3_client,
            actual_bucket,
            records_by_key[existing_key],
            collision_description="retired archive object",
        )

    if storage_mode == CONTENT_ADDRESSED_MODE:
        sources_by_digest = {
            source.sha256: source for source in sources
        }
        seen: set[str] = set()
        for digest, size, data in generation.content_chunks():
            source = sources_by_digest.get(digest)
            if (
                source is None
                or digest in seen
                or size != source.size_bytes
                or len(data) != size
                or _digest(data) != digest
            ):
                raise RetiredLegacyArchiveError(
                    "verified source content chunk set changed during archive"
                )
            if source.key not in existing_keys:
                _put_bytes_once(
                    s3_client,
                    actual_bucket,
                    source.record(),
                    data,
                )
            seen.add(digest)
        if seen != set(sources_by_digest):
            raise RetiredLegacyArchiveError(
                "verified source omitted a manifest-referenced content chunk"
            )
    else:
        for source in sources:
            if source.key in existing_keys:
                continue
            relative = source.source_relative_path
            _put_file_once(
                s3_client,
                actual_bucket,
                source.record(),
                generation.directory / Path(relative),
                local_identities[relative],
            )

    if manifest_key not in existing_keys:
        _put_bytes_once(
            s3_client,
            actual_bucket,
            manifest_record,
            manifest_bytes,
        )
    if receipt_key not in existing_keys:
        _put_bytes_once(
            s3_client,
            actual_bucket,
            receipt_record,
            receipt_bytes,
        )

    final_keys = _list_keys(
        s3_client,
        actual_bucket,
        listing_prefix,
    )
    if final_keys != expected_keys:
        raise RetiredLegacyArchiveError(
            "retired archive final S3 object set differs from its receipt"
        )
    for archived_key in sorted(final_keys):
        _assert_remote(
            s3_client,
            actual_bucket,
            records_by_key[archived_key],
            collision_description="retired archive final read-back",
        )
    if storage_mode == STORED_OBJECT_MODE:
        for source in sources:
            relative = source.source_relative_path
            _assert_local_unchanged(
                generation.directory / Path(relative),
                local_identities[relative],
            )

    return RetiredLegacyArchiveResult(
        bucket=actual_bucket,
        versioned_prefix=versioned_prefix,
        source_generation_uuid=generation.generation_uuid,
        identity=generation.identity,
        tick=generation.tick,
        source_storage_mode=storage_mode,
        source_tree_sha256=tree_sha256,
        manifest_sha256=generation.manifest_sha256,
        content_chunk_count=(
            len(sources)
            if storage_mode == CONTENT_ADDRESSED_MODE
            else 0
        ),
        stored_generation_object_count=(
            len(sources)
            if storage_mode == STORED_OBJECT_MODE
            else 0
        ),
        source_object_count=len(sources),
        total_archive_bytes=int(receipt["total_archive_bytes"]),
        receipt_key=receipt_key,
        receipt_hmac_sha256=str(receipt["receipt_hmac_sha256"]),
        receipt_bytes=receipt_bytes,
    )


__all__ = [
    "ARCHIVE_RECEIPT_NAME",
    "ARCHIVE_RECEIPT_SCHEMA",
    "ARCHIVE_ROOT_PREFIX",
    "CONTENT_ADDRESSED_MODE",
    "MAX_RETIRED_LEGACY_ARCHIVE_BYTES",
    "STORED_OBJECT_MODE",
    "RetiredLegacyArchiveError",
    "RetiredLegacyArchiveResult",
    "archive_retired_legacy_generation",
    "verify_retired_legacy_archive_receipt",
]
