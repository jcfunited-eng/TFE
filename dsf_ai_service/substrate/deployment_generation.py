"""Deployment integration for immutable local persistence generations.

The helper in this module is deliberately separate from the engine, web
application, and deployment scripts.  It accepts an injected save callback and
an injected S3-compatible client.  No network client is constructed here.

The deployment sequence is:

1. save into a private staging directory;
2. require every staged regular file and reject every unsafe filesystem node;
3. commit through :class:`ImmutableGenerationStore`;
4. run any caller-supplied cold-restore validator while still unpublished;
5. upload the exact immutable generation tree to a UUID-versioned prefix;
6. list and read every remote object back, verifying exact keys and bytes;
7. publish CURRENT and return a caller-nonce-bound HMAC-SHA256 certificate.

Materialization performs the reverse boundary.  It discovers ``CURRENT`` from
only its pointer and manifest, invokes full immutable-store verification, then
unwraps JSON and copies binary payloads into a fresh sibling directory.  An
existing active directory is exchanged atomically with Linux ``renameat2``;
any post-swap verification failure exchanges it back before raising.
"""

from __future__ import annotations

import base64
import contextlib
import copy
import ctypes
import errno
import fcntl
import hashlib
import hmac
import json
import os
import shutil
import stat
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator, Mapping, Optional

from dsf_ai_service.substrate.immutable_generation_store import (
    CURRENT_NAME,
    CURRENT_SCHEMA,
    FILE_RECORD_SCHEMA,
    GENERATIONS_DIRECTORY,
    MANIFEST_NAME,
    MANIFEST_SCHEMA,
    CurrentPointerError,
    GenerationValidationError,
    ImmutableGenerationStore,
    LoadedGeneration,
)


DEPLOYMENT_SEAL_SCHEMA = "deployment_generation_seal_v1"
MATERIALIZATION_SCHEMA = "deployment_generation_materialization_v1"
OWNER_LOCK_SCHEMA = "deployment_generation_efs_owner_v1"
DEPLOYMENT_SEAL_NAME = "DEPLOYMENT_SEAL.json"

_CURRENT_KEYS = {
    "schema", "generation_uuid", "identity", "tick", "generation_path",
    "manifest_sha256",
}
_MANIFEST_KEYS = {
    "schema", "generation_uuid", "identity", "tick", "required_files",
}
_FILE_RECORD_KEYS = {
    "schema", "generation_uuid", "identity", "tick", "relative_path",
    "sha256", "size_bytes",
}
_SEAL_KEYS = {
    "schema", "algorithm", "generation_uuid", "identity", "tick",
    "manifest_sha256", "recovery_certificate_sha256", "bucket",
    "versioned_prefix", "nonce_base64", "objects", "seal_hmac_sha256",
}
_OBJECT_RECORD_KEYS = {"key", "sha256", "size_bytes"}

_TEMPORARY_SUFFIXES = (".tmp", ".temp", ".part", ".swp")
_TEMPORARY_PREFIXES = (".tmp-", ".temp-", ".partial-")
_AT_FDCWD = -100
_RENAME_EXCHANGE = 2


class DeploymentGenerationError(RuntimeError):
    """Base failure for deployment staging, upload, or activation."""


class StageValidationError(DeploymentGenerationError):
    """The caller-produced save tree contains an unsafe or incomplete node."""


class RemoteGenerationVerificationError(DeploymentGenerationError):
    """The uploaded object set or read-back bytes do not match the generation."""


class SealValidationError(DeploymentGenerationError):
    """A deployment seal is malformed, mismatched, or cryptographically invalid."""


class MaterializationError(DeploymentGenerationError):
    """A verified generation could not be safely activated."""


class AtomicDirectorySwapUnsupported(MaterializationError):
    """The filesystem cannot atomically exchange two existing directories."""


class EFSOwnerLockUnavailable(DeploymentGenerationError):
    """Another process already owns the nonblocking persistence lock."""


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value!r} is forbidden")


def _strict_json_bytes(data: bytes, description: str) -> Any:
    try:
        return json.loads(
            data.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DeploymentGenerationError(
            f"{description} is not strict UTF-8 JSON: {error}") from error


def _canonical_json(value: Any) -> bytes:
    try:
        return (json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise DeploymentGenerationError(
            f"value is not deterministic JSON: {error}") from error


def _canonical_uuid(value: Any, description: str) -> str:
    if not isinstance(value, str):
        raise DeploymentGenerationError(f"{description} must be a UUID string")
    try:
        canonical = str(uuid.UUID(value))
    except (ValueError, AttributeError) as error:
        raise DeploymentGenerationError(f"{description} is not a valid UUID") from error
    if value != canonical:
        raise DeploymentGenerationError(f"{description} is not in canonical UUID form")
    return canonical


def _identity(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise DeploymentGenerationError(
            "generation identity must be a non-empty trimmed string")
    return value


def _tick(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DeploymentGenerationError(
            "generation tick must be a non-negative integer")
    return value


def _relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeploymentGenerationError("generation path is not canonical POSIX syntax")
    path = PurePosixPath(value)
    if (path.is_absolute() or path.as_posix() != value
            or any(part in ("", ".", "..") for part in path.parts)):
        raise DeploymentGenerationError(
            f"generation path {value!r} is unsafe or noncanonical")
    if value in {CURRENT_NAME, MANIFEST_NAME, GENERATIONS_DIRECTORY}:
        raise DeploymentGenerationError(
            f"generation path {value!r} is reserved")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        count = os.write(fd, view[offset:])
        if count <= 0:
            raise OSError("file write made no forward progress")
        offset += count


def _write_materialized_file(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        _write_all(fd, data)
        os.fchmod(fd, 0o644)
        os.fsync(fd)
    finally:
        os.close(fd)


def _is_temporary_name(name: str) -> bool:
    lower = name.lower()
    return (lower.startswith(_TEMPORARY_PREFIXES) or name.endswith("~")
            or lower.endswith(_TEMPORARY_SUFFIXES))


def _remove_private_tree(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode):
        path.unlink()
        return
    if not stat.S_ISDIR(info.st_mode):
        raise DeploymentGenerationError(
            f"refusing to remove non-directory private path {path}")
    shutil.rmtree(path)


def _read_immutable_json(path: Path, description: str) -> tuple[dict, bytes]:
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise CurrentPointerError(f"{description} is missing") from error
    if (not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o444
            or info.st_nlink != 1):
        raise CurrentPointerError(
            f"{description} is not an immutable unique regular file")
    data = path.read_bytes()
    value = _strict_json_bytes(data, description)
    if not isinstance(value, dict):
        raise CurrentPointerError(f"{description} must be a JSON object")
    return value, data


def _validated_digest(value: Any, description: str) -> str:
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise DeploymentGenerationError(f"{description} is not a SHA-256 hex digest")
    return value


@dataclass(frozen=True)
class DiscoveredCurrent:
    store: ImmutableGenerationStore
    generation: LoadedGeneration


@dataclass(frozen=True)
class DeploymentGenerationResult:
    generation: LoadedGeneration
    _seal_json: bytes

    def seal_certificate(self) -> dict:
        return copy.deepcopy(_strict_json_bytes(
            self._seal_json, "deployment seal certificate"))

    def seal_certificate_bytes(self) -> bytes:
        return bytes(self._seal_json)


@dataclass(frozen=True)
class MaterializedGeneration:
    schema: str
    generation_uuid: str
    identity: str
    tick: int
    manifest_sha256: str
    active_directory: Path
    materialized_files: tuple[str, ...]


def discover_and_load_current(
        store_root: str | os.PathLike[str]) -> DiscoveredCurrent:
    """Discover identity/file contract from pointer+manifest, then fully verify.

    The pointer path is never trusted as a filesystem path.  Its UUID is parsed
    canonically and the only accepted location is ``generations/<UUID>``.
    Required paths are learned only from the hash-bound manifest.  The newly
    constructed store then performs its full tree, mode, envelope, size, and
    hash verification before any payload is returned.
    """
    root = Path(store_root)
    if root.is_symlink() or not root.is_dir():
        raise CurrentPointerError("generation-store root is not a real directory")
    pointer, _pointer_bytes = _read_immutable_json(
        root / CURRENT_NAME, "CURRENT pointer")
    if set(pointer) != _CURRENT_KEYS or pointer.get("schema") != CURRENT_SCHEMA:
        raise CurrentPointerError("CURRENT pointer field set or schema is invalid")

    generation_uuid = _canonical_uuid(
        pointer.get("generation_uuid"), "CURRENT generation UUID")
    identity = _identity(pointer.get("identity"))
    tick = _tick(pointer.get("tick"))
    expected_generation_path = f"{GENERATIONS_DIRECTORY}/{generation_uuid}"
    if pointer.get("generation_path") != expected_generation_path:
        raise CurrentPointerError("CURRENT generation path is not UUID-derived")
    manifest_digest = _validated_digest(
        pointer.get("manifest_sha256"), "CURRENT manifest hash")

    manifest_path = root / GENERATIONS_DIRECTORY / generation_uuid / MANIFEST_NAME
    manifest, manifest_bytes = _read_immutable_json(
        manifest_path, "CURRENT generation manifest")
    if _sha256(manifest_bytes) != manifest_digest:
        raise CurrentPointerError("CURRENT manifest bytes do not match the pointer hash")
    if set(manifest) != _MANIFEST_KEYS or manifest.get("schema") != MANIFEST_SCHEMA:
        raise CurrentPointerError("CURRENT manifest field set or schema is invalid")
    if (manifest.get("generation_uuid") != generation_uuid
            or manifest.get("identity") != identity
            or manifest.get("tick") != tick):
        raise CurrentPointerError("CURRENT manifest generation metadata mismatch")

    records = manifest.get("required_files")
    if not isinstance(records, list) or not records:
        raise CurrentPointerError("CURRENT manifest has no required-file records")
    required_files = []
    for record in records:
        if (not isinstance(record, dict)
                or set(record) != _FILE_RECORD_KEYS
                or record.get("schema") != FILE_RECORD_SCHEMA):
            raise CurrentPointerError("CURRENT manifest has an invalid file record")
        relative_path = _relative_path(record.get("relative_path"))
        if (record.get("generation_uuid") != generation_uuid
                or record.get("identity") != identity
                or record.get("tick") != tick):
            raise CurrentPointerError(
                f"CURRENT file record {relative_path!r} metadata mismatch")
        _validated_digest(record.get("sha256"), f"record {relative_path!r} hash")
        size = record.get("size_bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise CurrentPointerError(
                f"CURRENT file record {relative_path!r} size is invalid")
        required_files.append(relative_path)
    if tuple(required_files) != tuple(sorted(set(required_files))):
        raise CurrentPointerError(
            "CURRENT required-file records are duplicated or noncanonical")

    try:
        store = ImmutableGenerationStore(
            root, identity=identity, required_files=required_files)
        generation = store.load_current()
    except (GenerationValidationError, CurrentPointerError) as error:
        raise CurrentPointerError(
            f"CURRENT failed full immutable-store verification: {error}") from error
    return DiscoveredCurrent(store=store, generation=generation)


def _discover_staged_files(stage_directory: Path) -> dict[str, Path]:
    try:
        root_info = stage_directory.lstat()
    except FileNotFoundError as error:
        raise StageValidationError("save callback removed its staging directory") from error
    if not stat.S_ISDIR(root_info.st_mode) or stage_directory.is_symlink():
        raise StageValidationError("save callback replaced its staging directory")

    files: dict[str, Path] = {}
    for current_root, directory_names, file_names in os.walk(
            stage_directory, topdown=True, followlinks=False):
        current = Path(current_root)
        for name in directory_names:
            path = current / name
            relative = path.relative_to(stage_directory).as_posix()
            info = path.lstat()
            if _is_temporary_name(name):
                raise StageValidationError(
                    f"staged tree contains temporary directory {relative!r}")
            if not stat.S_ISDIR(info.st_mode) or path.is_symlink():
                raise StageValidationError(
                    f"staged tree contains special directory node {relative!r}")
        for name in file_names:
            path = current / name
            relative = path.relative_to(stage_directory).as_posix()
            info = path.lstat()
            if _is_temporary_name(name):
                raise StageValidationError(
                    f"staged tree contains temporary file {relative!r}")
            if not stat.S_ISREG(info.st_mode) or path.is_symlink():
                raise StageValidationError(
                    f"staged tree contains special file node {relative!r}")
            if info.st_nlink != 1:
                raise StageValidationError(
                    f"staged file {relative!r} has hard links")
            canonical = _relative_path(relative)
            files[canonical] = path
    if not files:
        raise StageValidationError("save callback produced no regular files")
    return files


def _normalized_s3_prefix(prefix: str) -> str:
    if not isinstance(prefix, str) or not prefix.strip("/"):
        raise DeploymentGenerationError("S3 prefix must be a non-empty string")
    normalized = prefix.strip("/")
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise DeploymentGenerationError("S3 prefix is noncanonical")
    return normalized


def _s3_body_bytes(response: Mapping[str, Any], key: str) -> bytes:
    if not isinstance(response, Mapping) or "Body" not in response:
        raise RemoteGenerationVerificationError(
            f"S3 get_object for {key!r} returned no Body")
    body = response["Body"]
    if isinstance(body, bytes):
        return body
    read = getattr(body, "read", None)
    if not callable(read):
        raise RemoteGenerationVerificationError(
            f"S3 Body for {key!r} is not readable")
    try:
        data = read()
    finally:
        close = getattr(body, "close", None)
        if callable(close):
            close()
    if not isinstance(data, bytes):
        raise RemoteGenerationVerificationError(
            f"S3 Body for {key!r} did not return bytes")
    return data


def _list_s3_keys(client: Any, bucket: str, prefix: str) -> set[str]:
    keys: set[str] = set()
    continuation: Optional[str] = None
    seen_tokens: set[str] = set()
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if continuation is not None:
            kwargs["ContinuationToken"] = continuation
        response = client.list_objects_v2(**kwargs)
        if not isinstance(response, Mapping):
            raise RemoteGenerationVerificationError(
                "S3 list_objects_v2 returned a non-object response")
        for item in response.get("Contents") or []:
            if not isinstance(item, Mapping) or not isinstance(item.get("Key"), str):
                raise RemoteGenerationVerificationError(
                    "S3 listing contains an invalid object record")
            keys.add(item["Key"])
        if not response.get("IsTruncated", False):
            return keys
        next_token = response.get("NextContinuationToken")
        if not isinstance(next_token, str) or not next_token or next_token in seen_tokens:
            raise RemoteGenerationVerificationError(
                "S3 listing continuation token is absent or cyclic")
        seen_tokens.add(next_token)
        continuation = next_token


def _nonce_bytes(nonce: bytes | bytearray | memoryview | str) -> bytes:
    if isinstance(nonce, str):
        value = nonce.encode("utf-8")
    elif isinstance(nonce, (bytes, bytearray, memoryview)):
        value = bytes(nonce)
    else:
        raise SealValidationError("seal nonce must be bytes or a string")
    if len(value) < 16:
        raise SealValidationError("seal nonce must contain at least 16 bytes")
    return value


def _hmac_key(value: bytes | bytearray | memoryview) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise SealValidationError("HMAC key must be bytes")
    key = bytes(value)
    if len(key) < 32:
        raise SealValidationError("HMAC-SHA256 key must contain at least 32 bytes")
    return key


def _generation_tree_bytes(generation: LoadedGeneration) -> dict[str, bytes]:
    """Revalidate the exact immutable tree at the moment it is uploaded."""
    expected_files = set(generation.required_files) | {MANIFEST_NAME}
    expected_directories = _expected_parent_directories(
        tuple(generation.required_files))
    actual_files = set()
    actual_directories = set()
    for current_root, directory_names, file_names in os.walk(
            generation.directory, topdown=True, followlinks=False):
        current = Path(current_root)
        relative_root = current.relative_to(generation.directory)
        if relative_root != Path("."):
            actual_directories.add(relative_root.as_posix())
        directory_info = current.lstat()
        if (not stat.S_ISDIR(directory_info.st_mode)
                or stat.S_IMODE(directory_info.st_mode) != 0o555
                or current.is_symlink()):
            raise RemoteGenerationVerificationError(
                "local generation contains a mutable or special directory")
        for name in directory_names:
            if (current / name).is_symlink():
                raise RemoteGenerationVerificationError(
                    "local generation contains a directory symlink")
        for name in file_names:
            path = current / name
            relative = path.relative_to(generation.directory).as_posix()
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode)
                    or stat.S_IMODE(info.st_mode) != 0o444
                    or info.st_nlink != 1
                    or path.is_symlink()):
                raise RemoteGenerationVerificationError(
                    f"local generation file {relative!r} is mutable or special")
            actual_files.add(relative)
    if actual_files != expected_files or actual_directories != expected_directories:
        raise RemoteGenerationVerificationError(
            "local generation tree no longer has its exact verified file set")

    certificate = generation.recovery_certificate()
    record_by_path = {
        record["relative_path"]: record
        for record in certificate["required_files"]
    }
    tree = {}
    for relative_path in sorted(expected_files):
        data = (generation.directory / Path(relative_path)).read_bytes()
        expected_digest = (
            generation.manifest_sha256
            if relative_path == MANIFEST_NAME
            else record_by_path[relative_path]["sha256"])
        if _sha256(data) != expected_digest:
            raise RemoteGenerationVerificationError(
                f"local generation file {relative_path!r} changed before upload")
        tree[relative_path] = data
    return tree


def upload_verified_generation(
        generation: LoadedGeneration, *, s3_client: Any, bucket: str,
        prefix: str, hmac_key: bytes, nonce: bytes | str) -> bytes:
    """Upload, read back, verify, and seal one immutable generation tree."""
    if not isinstance(generation, LoadedGeneration):
        raise TypeError("generation must be a fully verified LoadedGeneration")
    if not isinstance(bucket, str) or not bucket.strip():
        raise DeploymentGenerationError("S3 bucket must be a non-empty string")
    normalized_prefix = _normalized_s3_prefix(prefix)
    versioned_prefix = f"{normalized_prefix}/{generation.generation_uuid}"
    key_bytes = _hmac_key(hmac_key)
    actual_nonce = _nonce_bytes(nonce)

    generation_tree = _generation_tree_bytes(generation)
    local_objects: dict[str, bytes] = {}
    for relative_path, data in generation_tree.items():
        key = f"{versioned_prefix}/{relative_path}"
        local_objects[key] = data
        s3_client.put_object(Bucket=bucket, Key=key, Body=data)

    listing_prefix = f"{versioned_prefix}/"
    remote_keys = _list_s3_keys(s3_client, bucket, listing_prefix)
    expected_keys = set(local_objects)
    if remote_keys != expected_keys:
        missing = sorted(expected_keys - remote_keys)
        extra = sorted(remote_keys - expected_keys)
        raise RemoteGenerationVerificationError(
            f"remote generation key set mismatch: missing={missing}, extra={extra}")

    certificate = generation.recovery_certificate()
    required_records = {
        record["relative_path"]: record
        for record in certificate["required_files"]
    }
    object_records = []
    for key in sorted(expected_keys):
        response = s3_client.get_object(Bucket=bucket, Key=key)
        remote = _s3_body_bytes(response, key)
        local = local_objects[key]
        if remote != local:
            raise RemoteGenerationVerificationError(
                f"remote object {key!r} bytes differ from the local generation")
        relative = key[len(listing_prefix):]
        digest = _sha256(remote)
        if relative == MANIFEST_NAME:
            expected_digest = generation.manifest_sha256
        else:
            expected_digest = required_records[relative]["sha256"]
        if digest != expected_digest:
            raise RemoteGenerationVerificationError(
                f"remote object {key!r} failed its generation hash")
        object_records.append({
            "key": key,
            "sha256": digest,
            "size_bytes": len(remote),
        })

    unsigned = {
        "schema": DEPLOYMENT_SEAL_SCHEMA,
        "algorithm": "HMAC-SHA256",
        "generation_uuid": generation.generation_uuid,
        "identity": generation.identity,
        "tick": generation.tick,
        "manifest_sha256": generation.manifest_sha256,
        "recovery_certificate_sha256": _sha256(
            generation.recovery_certificate_bytes()),
        "bucket": bucket,
        "versioned_prefix": versioned_prefix,
        "nonce_base64": base64.b64encode(actual_nonce).decode("ascii"),
        "objects": object_records,
    }
    seal = hmac.new(key_bytes, _canonical_json(unsigned), hashlib.sha256).hexdigest()
    return _canonical_json({**unsigned, "seal_hmac_sha256": seal})


def verify_deployment_seal(
        certificate: bytes | Mapping[str, Any], *, hmac_key: bytes,
        expected_nonce: bytes | str) -> dict:
    """Verify the exact seal field set, nonce, object records, and HMAC."""
    if isinstance(certificate, bytes):
        value = _strict_json_bytes(certificate, "deployment seal")
    elif isinstance(certificate, Mapping):
        value = copy.deepcopy(dict(certificate))
    else:
        raise SealValidationError("deployment seal must be bytes or a mapping")
    if not isinstance(value, dict) or set(value) != _SEAL_KEYS:
        raise SealValidationError("deployment seal has an invalid field set")
    if (value.get("schema") != DEPLOYMENT_SEAL_SCHEMA
            or value.get("algorithm") != "HMAC-SHA256"):
        raise SealValidationError("deployment seal schema or algorithm is invalid")
    _canonical_uuid(value.get("generation_uuid"), "seal generation UUID")
    _identity(value.get("identity"))
    _tick(value.get("tick"))
    _validated_digest(value.get("manifest_sha256"), "seal manifest hash")
    _validated_digest(
        value.get("recovery_certificate_sha256"), "seal recovery-certificate hash")
    bucket = value.get("bucket")
    if not isinstance(bucket, str) or not bucket.strip():
        raise SealValidationError("deployment seal bucket is invalid")
    versioned_prefix = value.get("versioned_prefix")
    if (not isinstance(versioned_prefix, str)
            or versioned_prefix.rsplit("/", 1)[-1] != value["generation_uuid"]):
        raise SealValidationError(
            "deployment seal versioned prefix is not generation-bound")
    objects = value.get("objects")
    if not isinstance(objects, list) or not objects:
        raise SealValidationError("deployment seal has no object records")
    prior_key = None
    for record in objects:
        if not isinstance(record, dict) or set(record) != _OBJECT_RECORD_KEYS:
            raise SealValidationError("deployment seal has an invalid object record")
        key = record.get("key")
        if (not isinstance(key, str)
                or not key.startswith(versioned_prefix + "/")
                or (prior_key is not None and key <= prior_key)):
            raise SealValidationError(
                "deployment seal object keys must be unique and strictly ordered")
        prior_key = key
        _validated_digest(record.get("sha256"), f"seal object {key!r} hash")
        size = record.get("size_bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise SealValidationError(f"seal object {key!r} size is invalid")

    nonce = _nonce_bytes(expected_nonce)
    expected_nonce_base64 = base64.b64encode(nonce).decode("ascii")
    if value.get("nonce_base64") != expected_nonce_base64:
        raise SealValidationError("deployment seal nonce mismatch")
    supplied_seal = _validated_digest(
        value.get("seal_hmac_sha256"), "deployment HMAC")
    unsigned = {key: item for key, item in value.items()
                if key != "seal_hmac_sha256"}
    expected_seal = hmac.new(
        _hmac_key(hmac_key), _canonical_json(unsigned), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_seal, expected_seal):
        raise SealValidationError("deployment seal HMAC mismatch")
    return value


def persist_deployment_seal(
        store_root: str | os.PathLike[str], certificate: bytes, *,
        hmac_key: bytes, expected_nonce: bytes | str) -> Path:
    """Atomically publish an already verified seal for the next process.

    The HMAC certificate is immutable once published.  A later deployment
    replaces the named pointer atomically with a new immutable inode.
    """
    if not isinstance(certificate, bytes):
        raise TypeError("deployment seal certificate must be bytes")
    verify_deployment_seal(
        certificate, hmac_key=hmac_key, expected_nonce=expected_nonce)
    root = Path(store_root)
    if root.is_symlink() or not root.is_dir():
        raise SealValidationError("generation-store root is not a real directory")
    destination = root / DEPLOYMENT_SEAL_NAME
    candidate = root / f".{DEPLOYMENT_SEAL_NAME}.{uuid.uuid4()}.tmp"
    try:
        file_descriptor = os.open(
            candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            _write_all(file_descriptor, certificate)
            os.fchmod(file_descriptor, 0o444)
            os.fsync(file_descriptor)
        finally:
            os.close(file_descriptor)
        os.replace(candidate, destination)
        _fsync_directory(root)
    finally:
        with contextlib.suppress(FileNotFoundError):
            candidate.unlink()
    return destination


def load_and_verify_deployment_seal(
        store_root: str | os.PathLike[str], *, hmac_key: bytes,
        expected_nonce: bytes | str | None = None) -> dict:
    """Load the immutable cross-process seal and verify its nonce and HMAC."""
    path = Path(store_root) / DEPLOYMENT_SEAL_NAME
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise SealValidationError("deployment seal pointer is missing") from error
    if (not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o444
            or info.st_nlink != 1
            or path.is_symlink()):
        raise SealValidationError(
            "deployment seal pointer is not an immutable unique regular file")
    certificate = path.read_bytes()
    if expected_nonce is None:
        value = _strict_json_bytes(certificate, "deployment seal")
        encoded = value.get("nonce_base64") if isinstance(value, dict) else None
        if not isinstance(encoded, str):
            raise SealValidationError("deployment seal nonce is missing")
        try:
            expected_nonce = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as error:
            raise SealValidationError(
                "deployment seal nonce is not canonical base64") from error
    return verify_deployment_seal(
        certificate, hmac_key=hmac_key, expected_nonce=expected_nonce)


def stage_commit_upload(
        *, store_root: str | os.PathLike[str], identity: str, tick: int,
        save_callback: Callable[[Path], Any], s3_client: Any, bucket: str,
        prefix: str, hmac_key: bytes, nonce: bytes | str,
        pre_publish_validator: Optional[Callable[[LoadedGeneration], Any]] = None,
        ) -> DeploymentGenerationResult:
    """Run the complete stage -> local commit -> remote proof transaction.

    ``pre_publish_validator`` receives the fully verified but unpublished
    immutable generation.  It runs before any S3 object is written and before
    ``CURRENT`` is created or replaced.  This is the fail-closed boundary for
    callers that must prove a cold restore before making a recovery generation
    discoverable.
    """
    if not callable(save_callback):
        raise TypeError("save_callback must be callable")
    if pre_publish_validator is not None and not callable(pre_publish_validator):
        raise TypeError("pre_publish_validator must be callable")
    root = Path(store_root)
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".deployment-stage-", dir=root))
    os.chmod(stage, 0o700)
    try:
        save_callback(stage)
        staged_files = _discover_staged_files(stage)
        store = ImmutableGenerationStore(
            root,
            identity=_identity(identity),
            required_files=tuple(staged_files),
        )
        generation = store.commit(
            tick=_tick(tick), files=staged_files, publish_current=False)
        if pre_publish_validator is not None:
            pre_publish_validator(generation)
        seal_json = upload_verified_generation(
            generation,
            s3_client=s3_client,
            bucket=bucket,
            prefix=prefix,
            hmac_key=hmac_key,
            nonce=nonce,
        )
        generation = store.publish(generation)
        return DeploymentGenerationResult(
            generation=generation,
            _seal_json=seal_json,
        )
    finally:
        if stage.exists():
            _remove_private_tree(stage)


def _materialized_expected_bytes(generation: LoadedGeneration) -> dict[str, bytes]:
    expected = {}
    for relative_path in generation.required_files:
        payload = generation.payload(relative_path)
        if relative_path.endswith(".json"):
            expected[relative_path] = _canonical_json(payload)
        else:
            if not isinstance(payload, bytes):
                raise MaterializationError(
                    f"binary generation payload {relative_path!r} is not bytes")
            expected[relative_path] = payload
    return expected


def _expected_parent_directories(relative_files: tuple[str, ...]) -> set[str]:
    directories = set()
    for relative_path in relative_files:
        parent = PurePosixPath(relative_path).parent
        while parent.as_posix() != ".":
            directories.add(parent.as_posix())
            parent = parent.parent
    return directories


def _write_materialization(candidate: Path, expected: Mapping[str, bytes]) -> None:
    candidate.mkdir(mode=0o700)
    directories = _expected_parent_directories(tuple(expected))
    for relative in sorted(
            directories, key=lambda item: (len(PurePosixPath(item).parts), item)):
        (candidate / Path(relative)).mkdir(mode=0o700)
    for relative_path in sorted(expected):
        _write_materialized_file(
            candidate / Path(relative_path), expected[relative_path])
    all_directories = [candidate]
    all_directories.extend(candidate / Path(item) for item in directories)
    for directory in sorted(
            all_directories, key=lambda item: len(item.parts), reverse=True):
        os.chmod(directory, 0o755)
        _fsync_directory(directory)


def _verify_materialization(directory: Path, expected: Mapping[str, bytes]) -> None:
    expected_files = set(expected)
    expected_directories = _expected_parent_directories(tuple(expected))
    actual_files = set()
    actual_directories = set()
    for current_root, directory_names, file_names in os.walk(
            directory, topdown=True, followlinks=False):
        current = Path(current_root)
        relative_root = current.relative_to(directory)
        if relative_root != Path("."):
            actual_directories.add(relative_root.as_posix())
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode) or current.is_symlink():
            raise MaterializationError("materialized tree contains a special directory")
        for name in directory_names:
            if (current / name).is_symlink():
                raise MaterializationError("materialized tree contains a directory symlink")
        for name in file_names:
            path = current / name
            relative = path.relative_to(directory).as_posix()
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or path.is_symlink()
                    or info.st_nlink != 1):
                raise MaterializationError(
                    f"materialized file {relative!r} is not a unique regular file")
            actual_files.add(relative)
    if actual_files != expected_files or actual_directories != expected_directories:
        raise MaterializationError(
            "materialized tree has a missing or extra file/directory")
    for relative_path, expected_bytes in expected.items():
        if (directory / Path(relative_path)).read_bytes() != expected_bytes:
            raise MaterializationError(
                f"materialized file {relative_path!r} differs from verified payload")


def _rename_exchange(first: Path, second: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise AtomicDirectorySwapUnsupported(
            "libc does not expose renameat2 atomic directory exchange")
    renameat2.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        _AT_FDCWD, os.fsencode(first),
        _AT_FDCWD, os.fsencode(second),
        _RENAME_EXCHANGE,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in (errno.ENOSYS, errno.EINVAL, errno.ENOTSUP):
            raise AtomicDirectorySwapUnsupported(
                f"filesystem does not support atomic directory exchange: "
                f"{os.strerror(error_number)}")
        raise OSError(error_number, os.strerror(error_number))


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def materialize_verified_generation(
        *, generation: LoadedGeneration,
        active_directory: str | os.PathLike[str]) -> MaterializedGeneration:
    """Materialize one already verified immutable generation.

    This does not discover or publish ``CURRENT``.  It exists so a caller can
    exercise an unpublished generation through the exact production
    materialization path before admitting that generation as current.
    """
    if not isinstance(generation, LoadedGeneration):
        raise TypeError("generation must be a fully verified LoadedGeneration")
    generation_path = generation.directory.resolve(strict=True)
    active = Path(active_directory)
    active_parent = active.parent
    resolved_active = active.resolve(strict=False)
    if (_path_is_within(resolved_active, generation_path)
            or _path_is_within(generation_path, resolved_active)):
        raise MaterializationError(
            "active directory and immutable generation cannot contain one another")
    active_parent.mkdir(parents=True, exist_ok=True)
    if active.exists() and (active.is_symlink() or not active.is_dir()):
        raise MaterializationError(
            "existing active path must be a real directory")

    expected = _materialized_expected_bytes(generation)
    candidate = active_parent / (
        f".{active.name}.materializing-{generation.generation_uuid}-{uuid.uuid4()}")
    if candidate.exists():
        raise MaterializationError("materialization candidate unexpectedly exists")

    exchanged = False
    moved_into_empty = False
    try:
        _write_materialization(candidate, expected)
        _verify_materialization(candidate, expected)
        if active.exists():
            _rename_exchange(candidate, active)
            exchanged = True
        else:
            os.rename(candidate, active)
            moved_into_empty = True
        _fsync_directory(active_parent)
        _verify_materialization(active, expected)
    except Exception as activation_error:
        try:
            if exchanged:
                _rename_exchange(candidate, active)
                _fsync_directory(active_parent)
            elif moved_into_empty and active.exists() and not candidate.exists():
                os.rename(active, candidate)
                _fsync_directory(active_parent)
        except Exception as rollback_error:
            raise MaterializationError(
                f"activation failed and rollback also failed: "
                f"activation={activation_error}; rollback={rollback_error}") from rollback_error
        raise
    finally:
        if candidate.exists():
            _remove_private_tree(candidate)
            _fsync_directory(active_parent)

    return MaterializedGeneration(
        schema=MATERIALIZATION_SCHEMA,
        generation_uuid=generation.generation_uuid,
        identity=generation.identity,
        tick=generation.tick,
        manifest_sha256=generation.manifest_sha256,
        active_directory=active,
        materialized_files=tuple(sorted(expected)),
    )


def materialize_current(
        *, store_root: str | os.PathLike[str],
        active_directory: str | os.PathLike[str]) -> MaterializedGeneration:
    """Fully verify CURRENT, materialize it, and atomically activate it."""
    discovered = discover_and_load_current(store_root)
    store_path = Path(store_root).resolve(strict=True)
    resolved_active = Path(active_directory).resolve(strict=False)
    if _path_is_within(resolved_active, store_path):
        raise MaterializationError(
            "active directory cannot be inside the immutable generation store")
    return materialize_verified_generation(
        generation=discovered.generation,
        active_directory=active_directory,
    )


class ProcessLifetimeEFSOwnerLock:
    """One nonblocking advisory owner lock held for this object's lifetime.

    The lock file is never unlinked.  Removing a live flock path can create a
    second inode and therefore two apparent owners on EFS.  Ownership ends only
    by explicit ``release()``, context exit, or process/file-descriptor exit.
    """

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self._fd: Optional[int] = None

    @property
    def acquired(self) -> bool:
        return self._fd is not None

    def acquire(self) -> "ProcessLifetimeEFSOwnerLock":
        if self._fd is not None:
            raise DeploymentGenerationError("EFS owner lock is already acquired")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(self.path, flags, 0o600)
        except OSError as error:
            raise DeploymentGenerationError(
                f"EFS owner lock cannot be opened: {error}") from error
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise DeploymentGenerationError(
                    "EFS owner lock path is not a regular file")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise EFSOwnerLockUnavailable(
                    f"EFS state is already owned at {self.path}") from error
            owner = _canonical_json({
                "schema": OWNER_LOCK_SCHEMA,
                "pid": os.getpid(),
                "hostname": os.uname().nodename,
            })
            os.ftruncate(fd, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            _write_all(fd, owner)
            os.fchmod(fd, 0o600)
            os.fsync(fd)
            _fsync_directory(self.path.parent)
            self._fd = fd
            return self
        except Exception:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            raise

    def release(self) -> None:
        fd = self._fd
        if fd is None:
            return
        self._fd = None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def __enter__(self) -> "ProcessLifetimeEFSOwnerLock":
        return self.acquire()

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.release()

    def __del__(self):
        with contextlib.suppress(Exception):
            self.release()


__all__ = [
    "AtomicDirectorySwapUnsupported",
    "DeploymentGenerationError",
    "DeploymentGenerationResult",
    "DiscoveredCurrent",
    "EFSOwnerLockUnavailable",
    "MaterializationError",
    "MaterializedGeneration",
    "ProcessLifetimeEFSOwnerLock",
    "RemoteGenerationVerificationError",
    "SealValidationError",
    "StageValidationError",
    "discover_and_load_current",
    "load_and_verify_deployment_seal",
    "materialize_current",
    "persist_deployment_seal",
    "stage_commit_upload",
    "upload_verified_generation",
    "verify_deployment_seal",
]
