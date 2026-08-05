"""Immutable, manifest-verified local persistence generations.

This module owns no application state and performs no network I/O.  Callers
provide the complete required file mapping for one generation.  The store
writes those files into a new directory, writes a SHA-256 manifest last,
verifies the completed immutable directory, and only then atomically replaces
the ``CURRENT`` pointer.

JSON inputs are stored inside a generation envelope.  Binary inputs are stored
byte-for-byte.  Both are bound to the same generation UUID, substrate identity,
and tick by the required-file records in the manifest.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import stat
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping, Sequence

import fcntl
import ijson

try:
    from guala_core import (
        ImmutableGenerationContentChunker as _NativeContentDefinedChunker,
    )
except (ImportError, AttributeError):
    _NativeContentDefinedChunker = None

from dsf_ai_service.substrate.physical_byte_ceiling import (
    PHYSICAL_BYTE_CEILING_RECEIPT_NAME,
    PHYSICAL_BYTE_CEILING_SCHEMA,
    PHYSICAL_BYTE_STATUS_SCHEMA,
    PhysicalByteCeilingAuthority,
    PhysicalByteCeilingConfigurationError,
    PhysicalByteCeilingError,
)


ENVELOPE_SCHEMA = "immutable_generation_envelope_v1"
FILE_RECORD_SCHEMA = "immutable_generation_file_record_v1"
MANIFEST_SCHEMA = "immutable_generation_manifest_v1"
CONTENT_FILE_RECORD_SCHEMA = "immutable_generation_content_record_v2"
CONTENT_MANIFEST_SCHEMA = "immutable_generation_content_manifest_v2"
CONTENT_CHUNK_SCHEMA = "immutable_generation_content_chunk_v1"
CURRENT_SCHEMA = "immutable_generation_current_v1"
CERTIFICATE_SCHEMA = "immutable_generation_recovery_certificate_v1"

MANIFEST_NAME = "MANIFEST.json"
CURRENT_NAME = "CURRENT"
GENERATIONS_DIRECTORY = "generations"
CONTENT_CHUNKS_DIRECTORY = "content-chunks"
CONTENT_CHUNK_MIN_BYTES = 1024 * 1024
CONTENT_CHUNK_BYTES = 4 * 1024 * 1024
CONTENT_CHUNK_MAX_BYTES = 8 * 1024 * 1024
_CONTENT_CHUNK_MASK = CONTENT_CHUNK_BYTES - 1
_CONTENT_GEAR_TABLE = tuple(
    int.from_bytes(
        hashlib.sha256(
            b"guala-content-defined-chunk-v1:" + bytes((value,))
        ).digest()[:8],
        "big",
    )
    for value in range(256)
)
LOCK_NAME = ".generation-store.lock"
MINIMUM_RETAINED_GENERATIONS = 2
UINT64_MAX = (1 << 64) - 1
REQUIRE_NATIVE_CONTENT_CHUNKING_ENV = (
    "GUALA_REQUIRE_NATIVE_CONTENT_CHUNKING"
)

_ENVELOPE_KEYS = {
    "schema", "generation_uuid", "identity", "tick", "relative_path",
    "payload",
}
_FILE_RECORD_KEYS = {
    "schema", "generation_uuid", "identity", "tick", "relative_path",
    "sha256", "size_bytes",
}
_MANIFEST_KEYS = {
    "schema", "generation_uuid", "identity", "tick", "required_files",
}
_CURRENT_KEYS = {
    "schema", "generation_uuid", "identity", "tick", "generation_path",
    "manifest_sha256",
}
_CONTENT_FILE_RECORD_KEYS = {
    "schema", "generation_uuid", "identity", "tick", "relative_path",
    "sha256", "size_bytes", "json_payload", "chunks",
}
_CONTENT_CHUNK_KEYS = {"schema", "sha256", "size_bytes"}


class GenerationStoreError(RuntimeError):
    """Base error for generation creation or verification failures."""


class GenerationValidationError(GenerationStoreError):
    """A generation, manifest, payload, or required path is invalid."""


class GenerationCapacityError(GenerationStoreError):
    """A candidate generation exceeds its configured encoded-byte capacity."""


class CurrentPointerError(GenerationStoreError):
    """The CURRENT pointer is absent, torn, corrupt, or inconsistent."""


def _native_content_chunking_required() -> bool:
    sealed_production = os.environ.get(
        "GUALA_REQUIRE_SEALED_STATE", "0"
    ).strip() == "1"
    configured = os.environ.get(REQUIRE_NATIVE_CONTENT_CHUNKING_ENV)
    if configured is None:
        return sealed_production
    configured = configured.strip()
    if configured not in {"0", "1"}:
        raise GenerationValidationError(
            f"{REQUIRE_NATIVE_CONTENT_CHUNKING_ENV} must be 0 or 1"
        )
    return sealed_production or configured == "1"


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value!r} is forbidden")


def _strict_json_loads(data: bytes, description: str) -> Any:
    try:
        text = data.decode("utf-8")
        return json.loads(text, parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise GenerationValidationError(
            f"{description} is not strict UTF-8 JSON: {error}") from error


def _canonical_json(value: Any) -> bytes:
    try:
        return (json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise GenerationValidationError(
            f"JSON payload is not deterministically serializable: {error}") from error


def _canonical_generation_uuid(value: str) -> str:
    if not isinstance(value, str):
        raise GenerationValidationError("generation UUID must be a string")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as error:
        raise GenerationValidationError(
            f"invalid generation UUID {value!r}") from error
    canonical = str(parsed)
    if value != canonical:
        raise GenerationValidationError(
            f"generation UUID must use canonical form {canonical!r}")
    return canonical


def _validated_tick(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GenerationValidationError("generation tick must be a non-negative integer")
    return value


def _validated_identity(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenerationValidationError("generation identity must be a non-empty string")
    if value != value.strip():
        raise GenerationValidationError(
            "generation identity cannot have leading or trailing whitespace")
    return value


def _validated_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise GenerationValidationError("required file paths must be non-empty strings")
    if "\\" in value or "\x00" in value:
        raise GenerationValidationError(
            f"required file path {value!r} is not canonical POSIX syntax")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix():
        raise GenerationValidationError(
            f"required file path {value!r} must be canonical and relative")
    if any(part in ("", ".", "..") for part in path.parts):
        raise GenerationValidationError(
            f"required file path {value!r} contains an unsafe component")
    if value in {
        MANIFEST_NAME,
        CURRENT_NAME,
        GENERATIONS_DIRECTORY,
        CONTENT_CHUNKS_DIRECTORY,
        LOCK_NAME,
    }:
        raise GenerationValidationError(
            f"required file path {value!r} is reserved by the generation store")
    return value


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    written = 0
    while written < len(view):
        count = os.write(fd, view[written:])
        if count <= 0:
            raise OSError("file write made no forward progress")
        written += count


def _write_new_bytes(path: Path, data: bytes) -> tuple[str, int]:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        _write_all(fd, data)
        os.fchmod(fd, 0o444)
        os.fsync(fd)
    finally:
        os.close(fd)
    return _sha256_bytes(data), len(data)


def _copy_new_file(
        source: Path, destination: Path, *,
        max_bytes: int | None = None) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    source_fd = None
    destination_fd = None
    try:
        source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode):
            raise GenerationValidationError(
                f"generation source {source} is not a regular file")
        if max_bytes is not None and source_stat.st_size > max_bytes:
            raise GenerationCapacityError(
                f"binary payload {source} exceeds remaining encoded-byte "
                f"capacity: {source_stat.st_size}>{max_bytes}")
        destination_fd = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            if max_bytes is not None and size + len(chunk) > max_bytes:
                raise GenerationCapacityError(
                    f"binary payload {source} changed beyond remaining "
                    "encoded-byte capacity while copied")
            _write_all(destination_fd, chunk)
            digest.update(chunk)
            size += len(chunk)
        final_source_stat = os.fstat(source_fd)
        if (
            size != source_stat.st_size
            or final_source_stat.st_size != source_stat.st_size
            or final_source_stat.st_mtime_ns != source_stat.st_mtime_ns
            or final_source_stat.st_ctime_ns != source_stat.st_ctime_ns
            or final_source_stat.st_ino != source_stat.st_ino
            or final_source_stat.st_dev != source_stat.st_dev
        ):
            raise GenerationValidationError(
                f"binary payload {source} changed while copied")
        os.fchmod(destination_fd, 0o444)
        os.fsync(destination_fd)
    finally:
        if destination_fd is not None:
            os.close(destination_fd)
        if source_fd is not None:
            os.close(source_fd)
    return digest.hexdigest(), size


def _read_regular_file(
        source: Path, description: str, *,
        max_bytes: int | None = None) -> bytes:
    chunks = []
    size = 0
    source_fd = None
    try:
        source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode):
            raise GenerationValidationError(
                f"{description} source is not a regular file")
        if max_bytes is not None and source_stat.st_size > max_bytes:
            raise GenerationCapacityError(
                f"{description} exceeds remaining encoded-byte capacity: "
                f"{source_stat.st_size}>{max_bytes}")
        while True:
            read_size = 1024 * 1024
            if max_bytes is not None:
                read_size = min(read_size, max_bytes - size + 1)
            chunk = os.read(source_fd, read_size)
            if not chunk:
                break
            size += len(chunk)
            if max_bytes is not None and size > max_bytes:
                raise GenerationCapacityError(
                    f"{description} grew beyond remaining encoded-byte "
                    "capacity while read")
            chunks.append(chunk)
        final_stat = os.fstat(source_fd)
        if (
            size != source_stat.st_size
            or final_stat.st_size != source_stat.st_size
            or final_stat.st_mtime_ns != source_stat.st_mtime_ns
            or final_stat.st_ctime_ns != source_stat.st_ctime_ns
            or final_stat.st_ino != source_stat.st_ino
            or final_stat.st_dev != source_stat.st_dev
        ):
            raise GenerationValidationError(
                f"{description} changed while read")
    except OSError as error:
        raise GenerationValidationError(
            f"{description} source cannot be read: {error}") from error
    finally:
        if source_fd is not None:
            os.close(source_fd)
    return b"".join(chunks)


class _IteratorByteStream(io.RawIOBase):
    def __init__(self, blocks: Iterator[bytes]):
        super().__init__()
        self._blocks = iter(blocks)
        self._pending = memoryview(b"")

    def readable(self) -> bool:
        return True

    def readinto(self, target) -> int:
        output = memoryview(target)
        written = 0
        while written < len(output):
            if not self._pending:
                try:
                    self._pending = memoryview(next(self._blocks))
                except StopIteration:
                    break
            length = min(len(output) - written, len(self._pending))
            output[written:written + length] = self._pending[:length]
            self._pending = self._pending[length:]
            written += length
        return written


def _validate_streaming_json(
        blocks: Iterator[bytes], description: str) -> None:
    stream = io.BufferedReader(_IteratorByteStream(blocks), 1024 * 1024)
    try:
        for _prefix, _event, _value in ijson.parse(stream):
            pass
    except Exception as error:
        raise GenerationValidationError(
            f"{description} is not strict streaming JSON: {error}") from error
    finally:
        stream.close()


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _assert_regular_read_only_file(path: Path, description: str) -> os.stat_result:
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise GenerationValidationError(f"{description} is missing") from error
    if not stat.S_ISREG(info.st_mode):
        raise GenerationValidationError(f"{description} is not a regular file")
    if stat.S_IMODE(info.st_mode) != 0o444:
        raise GenerationValidationError(
            f"{description} is not immutable (mode must be exactly 0444)")
    if info.st_nlink != 1:
        raise GenerationValidationError(
            f"{description} is not immutable (hard-link count must be one)")
    return info


def _assert_content_chunk_file(
        path: Path, description: str) -> os.stat_result:
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise GenerationValidationError(f"{description} is missing") from error
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise GenerationValidationError(
            f"{description} is not a regular non-symlink file")
    if stat.S_IMODE(info.st_mode) != 0o444:
        raise GenerationValidationError(
            f"{description} is not immutable (mode must be exactly 0444)")
    return info


def _read_strict_json_file(path: Path, description: str) -> tuple[Any, bytes]:
    _assert_regular_read_only_file(path, description)
    data = path.read_bytes()
    return _strict_json_loads(data, description), data


def _expected_directories(required_files: Sequence[str]) -> set[str]:
    directories: set[str] = set()
    for relative_path in required_files:
        parent = PurePosixPath(relative_path).parent
        while parent.as_posix() != ".":
            directories.add(parent.as_posix())
            parent = parent.parent
    return directories


@dataclass(frozen=True)
class LoadedGeneration:
    """One completely verified immutable generation."""

    generation_uuid: str
    identity: str
    tick: int
    directory: Path
    manifest_sha256: str
    _certificate_json: bytes
    _required_files: tuple[str, ...]
    _content_chunks_root: Path | None = None
    _content_records: Mapping[str, Mapping[str, Any]] | None = None

    @property
    def required_files(self) -> tuple[str, ...]:
        return self._required_files

    def recovery_certificate(self) -> dict:
        """Return a fresh copy of the deterministic verification certificate."""
        return copy.deepcopy(_strict_json_loads(
            self._certificate_json, "recovery certificate"))

    def recovery_certificate_bytes(self) -> bytes:
        return bytes(self._certificate_json)

    @property
    def content_addressed(self) -> bool:
        return self._content_records is not None

    def iter_stored_chunks(self, relative_path: str) -> Iterator[bytes]:
        relative_path = _validated_relative_path(relative_path)
        if relative_path not in self._required_files:
            raise KeyError(relative_path)
        if self._content_records is None:
            with (
                self.directory / Path(relative_path)
            ).open("rb") as handle:
                while True:
                    block = handle.read(1024 * 1024)
                    if not block:
                        return
                    yield block
        else:
            record = self._content_records[relative_path]
            for chunk in record["chunks"]:
                path = (
                    self._content_chunks_root
                    / chunk["sha256"][:2]
                    / chunk["sha256"]
                )
                with path.open("rb") as handle:
                    while True:
                        block = handle.read(1024 * 1024)
                        if not block:
                            break
                        yield block

    def stored_bytes(self, relative_path: str) -> bytes:
        return b"".join(self.iter_stored_chunks(relative_path))

    def content_chunks(self) -> Iterator[tuple[str, int, bytes]]:
        """Return each unique verified content chunk exactly once."""
        if self._content_records is None or self._content_chunks_root is None:
            return
        chunks: dict[str, int] = {}
        for record in self._content_records.values():
            for chunk in record["chunks"]:
                digest = chunk["sha256"]
                size = int(chunk["size_bytes"])
                prior = chunks.setdefault(digest, size)
                if prior != size:
                    raise GenerationValidationError(
                        f"content chunk {digest} has inconsistent sizes")
        for digest, size in sorted(chunks.items()):
            path = self._content_chunks_root / digest[:2] / digest
            info = _assert_content_chunk_file(
                path, f"content chunk {digest}")
            data = path.read_bytes()
            if (
                info.st_size != size
                or len(data) != size
                or _sha256_bytes(data) != digest
            ):
                raise GenerationValidationError(
                    f"content chunk {digest} changed")
            yield digest, size, data

    def payload(self, relative_path: str) -> Any:
        """Return the caller payload: decoded JSON or immutable binary bytes."""
        data = self.stored_bytes(relative_path)
        if relative_path.endswith(".json"):
            value = _strict_json_loads(
                data, f"JSON payload {relative_path!r}")
            if self._content_records is not None:
                return copy.deepcopy(value)
            return copy.deepcopy(value["payload"])
        return data


class ImmutableGenerationStore:
    """Commits and verifies one fixed required-file set for one identity."""

    def __init__(self, root: str | os.PathLike[str], *, identity: str,
                 required_files: Sequence[str] | None,
                 content_addressed: bool = False,
                 max_encoded_generation_bytes: int | None = None,
                 max_dynamic_required_files: int | None = None,
                 max_dynamic_path_bytes: int | None = None,
                 physical_byte_ceiling: int | None = None,
                 physical_byte_scope: str | os.PathLike[str] | None = None):
        self.root = Path(root)
        self.identity = _validated_identity(identity)
        if not isinstance(content_addressed, bool):
            raise GenerationValidationError(
                "content_addressed must be a boolean")
        self.content_addressed = content_addressed
        if max_encoded_generation_bytes is not None and (
            isinstance(max_encoded_generation_bytes, bool)
            or not isinstance(max_encoded_generation_bytes, int)
            or max_encoded_generation_bytes <= 0
        ):
            raise GenerationValidationError(
                "encoded generation capacity must be a positive integer")
        self.max_encoded_generation_bytes = max_encoded_generation_bytes
        if required_files is None:
            for value, description in (
                (max_dynamic_required_files, "dynamic required-file count"),
                (max_dynamic_path_bytes, "dynamic required-path bytes"),
            ):
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0
                ):
                    raise GenerationValidationError(
                        f"{description} capacity must be a positive integer")
            self.required_files: tuple[str, ...] | None = None
            self._required_set: frozenset[str] | None = None
            self.max_dynamic_required_files = max_dynamic_required_files
            self.max_dynamic_path_bytes = max_dynamic_path_bytes
        else:
            if isinstance(required_files, (str, bytes)):
                raise GenerationValidationError(
                    "required_files must be a sequence of relative paths")
            validated = tuple(
                _validated_relative_path(item)
                for item in required_files
            )
            if not validated:
                raise GenerationValidationError(
                    "at least one required file is mandatory")
            if len(set(validated)) != len(validated):
                raise GenerationValidationError(
                    "required file paths must be unique")
            self.required_files = tuple(sorted(validated))
            self._required_set = frozenset(self.required_files)
            self.max_dynamic_required_files = None
            self.max_dynamic_path_bytes = None

        self.root.mkdir(parents=True, exist_ok=True)
        self.generations_directory = self.root / GENERATIONS_DIRECTORY
        self.generations_directory.mkdir(exist_ok=True)
        self.content_chunks_directory = self.root / CONTENT_CHUNKS_DIRECTORY
        if self.content_addressed:
            self.content_chunks_directory.mkdir(exist_ok=True)
        if self.root.is_symlink() or not self.root.is_dir():
            raise GenerationValidationError("generation-store root must be a real directory")
        if (self.generations_directory.is_symlink()
                or not self.generations_directory.is_dir()):
            raise GenerationValidationError(
                "generation directory must be a real directory")
        if self.content_addressed and (
                self.content_chunks_directory.is_symlink()
                or not self.content_chunks_directory.is_dir()):
            raise GenerationValidationError(
                "content chunk directory must be a real directory")
        _fsync_directory(self.generations_directory)
        _fsync_directory(self.root)
        self._writer_local = threading.local()
        self._physical_writer_local = threading.local()
        self._physical_byte_ceiling: PhysicalByteCeilingAuthority | None = None
        self._last_physical_byte_receipt: dict | None = None
        if physical_byte_ceiling is None:
            if physical_byte_scope is not None:
                raise GenerationValidationError(
                    "physical-byte scope requires a physical-byte ceiling")
        else:
            scope = (
                self.root
                if physical_byte_scope is None
                else Path(physical_byte_scope)
            ).resolve()
            try:
                self.root.resolve().relative_to(scope)
            except ValueError as error:
                raise GenerationValidationError(
                    "generation-store root must be inside the physical-byte "
                    "scope") from error
            try:
                self._physical_byte_ceiling = PhysicalByteCeilingAuthority(
                    scope,
                    physical_byte_ceiling,
                )
            except PhysicalByteCeilingConfigurationError as error:
                raise GenerationValidationError(str(error)) from error

    def physical_byte_status(self) -> dict | None:
        """Return an exact rescan of the configured shared physical scope."""
        if self._physical_byte_ceiling is None:
            return None
        return self._physical_byte_ceiling.status()

    def physical_byte_configuration(self) -> dict | None:
        """Return the immutable shared-scope contract without a byte rescan."""
        if self._physical_byte_ceiling is None:
            return None
        return self._physical_byte_ceiling.configuration()

    def last_physical_byte_receipt(self) -> dict | None:
        """Return the latest admission or refusal issued by this instance."""
        return copy.deepcopy(self._last_physical_byte_receipt)

    def _admit_physical_bytes(
            self, *, operation: str, requested_bytes: int,
            rescan: bool = False, reserve: bool = True) -> dict | None:
        if self._physical_byte_ceiling is None:
            return None
        used_bytes = getattr(
            self._physical_writer_local,
            "projected_used_bytes",
            None,
        )
        if rescan or used_bytes is None:
            used_bytes = self._physical_byte_ceiling.used_bytes()
        try:
            receipt = self._physical_byte_ceiling.admit_at(
                operation=operation,
                used_bytes=used_bytes,
                requested_bytes=requested_bytes,
            )
        except PhysicalByteCeilingError as error:
            self._last_physical_byte_receipt = copy.deepcopy(error.receipt)
            raise
        self._physical_writer_local.projected_used_bytes = (
            used_bytes + requested_bytes
            if reserve
            else used_bytes
        )
        self._last_physical_byte_receipt = copy.deepcopy(receipt)
        return receipt

    @contextlib.contextmanager
    def _exclusive_physical_scope(self) -> Iterator[None]:
        if self._physical_byte_ceiling is None:
            yield
            return
        depth = getattr(self._physical_writer_local, "depth", 0)
        if depth:
            self._physical_writer_local.depth = depth + 1
            try:
                yield
            finally:
                self._physical_writer_local.depth = depth
            return
        with self._physical_byte_ceiling.exclusive_writer():
            self._physical_writer_local.depth = 1
            self._physical_writer_local.projected_used_bytes = (
                self._physical_byte_ceiling.used_bytes())
            try:
                yield
            finally:
                self._physical_writer_local.depth = 0
                self._physical_writer_local.projected_used_bytes = None

    @contextlib.contextmanager
    def _exclusive_writer(self) -> Iterator[None]:
        depth = getattr(self._writer_local, "depth", 0)
        if depth:
            self._writer_local.depth = depth + 1
            try:
                yield
            finally:
                self._writer_local.depth = depth
            return

        lock_path = self.root / LOCK_NAME
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            self._writer_local.depth = 1
            yield
        finally:
            self._writer_local.depth = 0
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    @contextlib.contextmanager
    def exclusive_transaction(self) -> Iterator[None]:
        """Hold the store's inter-process writer lock across one transaction."""
        with self._exclusive_physical_scope():
            with self._exclusive_writer():
                yield

    @staticmethod
    def _source_bytes(
        source: Any,
        description: str,
        *,
        max_bytes: int | None = None,
    ) -> bytes:
        if isinstance(source, bytes):
            if max_bytes is not None and len(source) > max_bytes:
                raise GenerationCapacityError(
                    f"{description} exceeds remaining encoded-byte capacity: "
                    f"{len(source)}>{max_bytes}"
                )
            return source
        if isinstance(source, bytearray):
            if max_bytes is not None and len(source) > max_bytes:
                raise GenerationCapacityError(
                    f"{description} exceeds remaining encoded-byte capacity: "
                    f"{len(source)}>{max_bytes}"
                )
            return bytes(source)
        if isinstance(source, memoryview):
            if max_bytes is not None and source.nbytes > max_bytes:
                raise GenerationCapacityError(
                    f"{description} exceeds remaining encoded-byte capacity: "
                    f"{source.nbytes}>{max_bytes}"
                )
            return source.tobytes()
        if isinstance(source, (str, os.PathLike)):
            source_path = Path(source)
            return _read_regular_file(
                source_path,
                description,
                max_bytes=max_bytes,
            )
        raise GenerationValidationError(
            f"{description} source must be bytes or a filesystem path")

    def _json_envelope(self, relative_path: str, source: Any,
                       generation_uuid: str, tick: int,
                       *, max_source_bytes: int | None = None) -> bytes:
        raw = self._source_bytes(
            source,
            f"JSON payload {relative_path!r}",
            max_bytes=max_source_bytes,
        )
        payload = _strict_json_loads(raw, f"JSON payload {relative_path!r}")
        return _canonical_json({
            "schema": ENVELOPE_SCHEMA,
            "generation_uuid": generation_uuid,
            "identity": self.identity,
            "tick": tick,
            "relative_path": relative_path,
            "payload": payload,
        })

    @staticmethod
    def _create_required_directories(
        building: Path,
        expected_directories: set[str],
    ) -> None:
        for relative_directory in sorted(
                expected_directories,
                key=lambda value: (len(PurePosixPath(value).parts), value)):
            (building / Path(relative_directory)).mkdir(exist_ok=False)

    @staticmethod
    def _freeze_and_sync_directories(
        generation_directory: Path,
        expected_directories: set[str],
    ) -> None:
        directories = [generation_directory]
        directories.extend(
            generation_directory / Path(relative)
            for relative in expected_directories)
        for directory in sorted(
                directories, key=lambda path: len(path.parts), reverse=True):
            os.chmod(directory, 0o555)
            _fsync_directory(directory)

    def _admit_encoded_bytes(
            self, *, accumulated: int, additional: int,
            description: str) -> None:
        if isinstance(additional, bool) or additional < 0:
            raise GenerationValidationError(
                f"{description} encoded size is invalid")
        capacity = self.max_encoded_generation_bytes
        if capacity is not None and accumulated + additional > capacity:
            raise GenerationCapacityError(
                f"candidate generation exceeds encoded-byte capacity: "
                f"{accumulated + additional}>{capacity} while admitting "
                f"{description}")

    @staticmethod
    def _verified_encoded_bytes(generation: LoadedGeneration) -> int:
        certificate = generation.recovery_certificate()
        return sum(
            int(record["size_bytes"])
            for record in certificate["required_files"]
        ) + (generation.directory / MANIFEST_NAME).stat().st_size

    def _enforce_verified_capacity(
            self, generation: LoadedGeneration, *,
            description: str) -> int:
        encoded_bytes = self._verified_encoded_bytes(generation)
        capacity = self.max_encoded_generation_bytes
        if capacity is not None and encoded_bytes > capacity:
            raise GenerationCapacityError(
                f"{description} exceeds encoded-byte capacity: "
                f"{encoded_bytes}>{capacity}")
        return encoded_bytes

    def _content_chunk_path(self, digest: str) -> Path:
        return self.content_chunks_directory / digest[:2] / digest

    def _publish_content_chunk(
            self, data: bytes, *, newly_created: set[Path]) -> dict:
        digest = _sha256_bytes(data)
        destination = self._content_chunk_path(digest)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if destination.exists():
            info = _assert_content_chunk_file(
                destination, f"content chunk {digest}")
            if info.st_size != len(data) or _sha256_file(destination)[0] != digest:
                raise GenerationValidationError(
                    f"content chunk {digest} differs from its address")
        else:
            temporary = destination.with_name(
                f".{digest}.{uuid.uuid4().hex}.tmp")
            try:
                self._admit_physical_bytes(
                    operation=f"allocate_content_chunk:{digest}",
                    requested_bytes=len(data),
                )
                _write_new_bytes(temporary, data)
                os.replace(temporary, destination)
                _fsync_directory(destination.parent)
                newly_created.add(destination)
            finally:
                if temporary.exists():
                    temporary.unlink()
                    _fsync_directory(destination.parent)
        return {
            "schema": CONTENT_CHUNK_SCHEMA,
            "sha256": digest,
            "size_bytes": len(data),
        }

    @staticmethod
    def _iter_source_blocks(
            source: Any, description: str, *,
            max_bytes: int | None) -> Iterator[bytes]:
        if isinstance(source, bytes):
            data = source
        elif isinstance(source, bytearray):
            data = bytes(source)
        elif isinstance(source, memoryview):
            data = source.tobytes()
        else:
            data = None
        if data is not None:
            if max_bytes is not None and len(data) > max_bytes:
                raise GenerationCapacityError(
                    f"{description} exceeds remaining encoded-byte capacity: "
                    f"{len(data)}>{max_bytes}")
            for offset in range(0, len(data), 1024 * 1024):
                yield data[offset:offset + 1024 * 1024]
            return
        if not isinstance(source, (str, os.PathLike)):
            raise GenerationValidationError(
                f"{description} source must be bytes or a filesystem path")
        source_path = Path(source)
        source_fd = None
        size = 0
        try:
            source_fd = os.open(source_path, os.O_RDONLY | os.O_NOFOLLOW)
            source_stat = os.fstat(source_fd)
            if not stat.S_ISREG(source_stat.st_mode):
                raise GenerationValidationError(
                    f"{description} source is not a regular file")
            if max_bytes is not None and source_stat.st_size > max_bytes:
                raise GenerationCapacityError(
                    f"{description} exceeds remaining encoded-byte capacity: "
                    f"{source_stat.st_size}>{max_bytes}")
            while True:
                body = os.read(source_fd, 1024 * 1024)
                if not body:
                    break
                size += len(body)
                if max_bytes is not None and size > max_bytes:
                    raise GenerationCapacityError(
                        f"{description} grew beyond remaining encoded-byte "
                        "capacity while read")
                yield body
            final_stat = os.fstat(source_fd)
            if (
                size != source_stat.st_size
                or final_stat.st_size != source_stat.st_size
                or final_stat.st_mtime_ns != source_stat.st_mtime_ns
                or final_stat.st_ctime_ns != source_stat.st_ctime_ns
                or final_stat.st_ino != source_stat.st_ino
                or final_stat.st_dev != source_stat.st_dev
            ):
                raise GenerationValidationError(
                    f"{description} changed while read")
        except OSError as error:
            raise GenerationValidationError(
                f"{description} source cannot be read: {error}") from error
        finally:
            if source_fd is not None:
                os.close(source_fd)

    @classmethod
    def _iter_content_defined_chunks(
            cls, source: Any, description: str, *,
            max_bytes: int | None) -> Iterator[bytes]:
        native_required = _native_content_chunking_required()
        if _NativeContentDefinedChunker is not None:
            chunker = _NativeContentDefinedChunker()
            for block in cls._iter_source_blocks(
                    source, description, max_bytes=max_bytes):
                for completed in chunker.feed(block):
                    yield bytes(completed)
            final_chunk = chunker.finish()
            if final_chunk is not None:
                yield bytes(final_chunk)
            return
        if native_required:
            raise GenerationValidationError(
                "sealed production requires the native immutable-generation "
                "content chunker; the guala_core wheel is absent or stale"
            )

        pending = bytearray()
        gear = 0
        for block in cls._iter_source_blocks(
                source, description, max_bytes=max_bytes):
            for byte in block:
                pending.append(byte)
                gear = (
                    ((gear << 1) + _CONTENT_GEAR_TABLE[byte])
                    & UINT64_MAX
                )
                length = len(pending)
                if (
                    length >= CONTENT_CHUNK_MIN_BYTES
                    and (
                        (gear & _CONTENT_CHUNK_MASK) == 0
                        or length >= CONTENT_CHUNK_MAX_BYTES
                    )
                ):
                    yield bytes(pending)
                    pending.clear()
                    gear = 0
        if pending:
            yield bytes(pending)

    @classmethod
    def _iter_fixed_content_chunks(
            cls, source: Any, description: str, *,
            max_bytes: int | None,
            chunk_bytes: int = CONTENT_CHUNK_BYTES) -> Iterator[bytes]:
        pending = bytearray()
        for block in cls._iter_source_blocks(
                source, description, max_bytes=max_bytes):
            pending.extend(block)
            while len(pending) >= chunk_bytes:
                yield bytes(pending[:chunk_bytes])
                del pending[:chunk_bytes]
        if pending:
            yield bytes(pending)

    @classmethod
    def _iter_sqlite_page_group_chunks(
            cls, source: Any, description: str, *,
            max_bytes: int | None) -> Iterator[bytes]:
        blocks = cls._iter_source_blocks(
            source, description, max_bytes=max_bytes)
        pending = bytearray()
        try:
            first = next(blocks)
        except StopIteration:
            raise GenerationValidationError(
                f"{description} is an empty structural graph")
        pending.extend(first)
        if (
            len(pending) < 100
            or pending[:16] != b"SQLite format 3\x00"
        ):
            raise GenerationValidationError(
                f"{description} is not a SQLite structural graph")
        page_size = int.from_bytes(pending[16:18], "big")
        if page_size == 1:
            page_size = 65_536
        if page_size != 4_096:
            raise GenerationValidationError(
                f"{description} has an unsupported SQLite page size")
        group_bytes = page_size * 256
        for block in blocks:
            pending.extend(block)
            while len(pending) >= group_bytes:
                yield bytes(pending[:group_bytes])
                del pending[:group_bytes]
        if pending:
            if len(pending) % page_size:
                raise GenerationValidationError(
                    f"{description} ends inside a SQLite page")
            yield bytes(pending)

    @classmethod
    def _iter_storage_chunks(
            cls, relative_path: str, source: Any, description: str, *,
            max_bytes: int | None) -> Iterator[bytes]:
        if relative_path.endswith(".sgr"):
            return cls._iter_sqlite_page_group_chunks(
                source, description, max_bytes=max_bytes)
        if (
            relative_path.endswith(".json")
            and relative_path != "guala_deep_atlas.json"
        ):
            return cls._iter_content_defined_chunks(
                source, description, max_bytes=max_bytes)
        return cls._iter_fixed_content_chunks(
            source, description, max_bytes=max_bytes)

    @classmethod
    def _validated_json_source(
            cls, source: Any, description: str, *,
            max_bytes: int | None) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0

        def observed_blocks() -> Iterator[bytes]:
            nonlocal size
            for block in cls._iter_source_blocks(
                    source, description, max_bytes=max_bytes):
                digest.update(block)
                size += len(block)
                yield block

        _validate_streaming_json(observed_blocks(), description)
        return digest.hexdigest(), size

    def _write_content_generation_directory(
        self,
        building: Path,
        generation_uuid: str,
        tick: int,
        files: Mapping[str, Any],
        required_files: tuple[str, ...],
    ) -> int:
        building.mkdir(mode=0o700)
        records = []
        logical_bytes = 0
        newly_created: set[Path] = set()
        try:
            for relative_path in required_files:
                remaining = (
                    None
                    if self.max_encoded_generation_bytes is None
                    else self.max_encoded_generation_bytes - logical_bytes
                )
                content_digest = hashlib.sha256()
                chunks = []
                content_size = 0
                description = f"content payload {relative_path!r}"
                validated_json = (
                    self._validated_json_source(
                        files[relative_path],
                        description,
                        max_bytes=remaining,
                    )
                    if relative_path.endswith(".json")
                    else None
                )
                bodies = self._iter_storage_chunks(
                    relative_path,
                    files[relative_path],
                    description,
                    max_bytes=remaining,
                )
                for body in bodies:
                    self._admit_encoded_bytes(
                        accumulated=logical_bytes + content_size,
                        additional=len(body),
                        description=relative_path,
                    )
                    content_digest.update(body)
                    content_size += len(body)
                    chunks.append(self._publish_content_chunk(
                        body,
                        newly_created=newly_created,
                    ))
                if (
                    validated_json is not None
                    and validated_json
                    != (content_digest.hexdigest(), content_size)
                ):
                    raise GenerationValidationError(
                        f"{description} changed between validation and chunking")
                logical_bytes += content_size
                records.append({
                    "schema": CONTENT_FILE_RECORD_SCHEMA,
                    "generation_uuid": generation_uuid,
                    "identity": self.identity,
                    "tick": tick,
                    "relative_path": relative_path,
                    "sha256": content_digest.hexdigest(),
                    "size_bytes": content_size,
                    "json_payload": relative_path.endswith(".json"),
                    "chunks": chunks,
                })
            manifest = {
                "schema": CONTENT_MANIFEST_SCHEMA,
                "generation_uuid": generation_uuid,
                "identity": self.identity,
                "tick": tick,
                "required_files": records,
            }
            manifest_bytes = _canonical_json(manifest)
            self._admit_encoded_bytes(
                accumulated=logical_bytes,
                additional=len(manifest_bytes),
                description=MANIFEST_NAME,
            )
            self._admit_physical_bytes(
                operation=f"allocate_prepared_file:{MANIFEST_NAME}",
                requested_bytes=len(manifest_bytes),
            )
            _write_new_bytes(building / MANIFEST_NAME, manifest_bytes)
            logical_bytes += len(manifest_bytes)
            self._freeze_and_sync_directories(building, set())
            return logical_bytes
        except Exception:
            for path in newly_created:
                with contextlib.suppress(FileNotFoundError):
                    path.unlink()
            for parent in {
                    path.parent for path in newly_created
                    if path.parent != self.content_chunks_directory}:
                with contextlib.suppress(OSError):
                    parent.rmdir()
            raise

    def _write_generation_directory(
        self,
        building: Path,
        generation_uuid: str,
        tick: int,
        files: Mapping[str, Any],
        required_files: tuple[str, ...],
    ) -> int:
        if self.content_addressed:
            return self._write_content_generation_directory(
                building,
                generation_uuid,
                tick,
                files,
                required_files,
            )
        expected_directories = _expected_directories(required_files)
        building.mkdir(mode=0o700)
        self._create_required_directories(building, expected_directories)
        records = []
        encoded_bytes = 0

        for relative_path in required_files:
            destination = building / Path(relative_path)
            source = files[relative_path]
            if relative_path.endswith(".json"):
                remaining = (
                    None
                    if self.max_encoded_generation_bytes is None
                    else self.max_encoded_generation_bytes - encoded_bytes
                )
                stored = self._json_envelope(
                    relative_path,
                    source,
                    generation_uuid,
                    tick,
                    max_source_bytes=remaining,
                )
                self._admit_encoded_bytes(
                    accumulated=encoded_bytes,
                    additional=len(stored),
                    description=relative_path,
                )
                self._admit_physical_bytes(
                    operation=f"allocate_prepared_file:{relative_path}",
                    requested_bytes=len(stored),
                )
                digest, size = _write_new_bytes(destination, stored)
            elif isinstance(source, (str, os.PathLike)):
                source_path = Path(source)
                try:
                    source_size = source_path.stat().st_size
                    self._admit_encoded_bytes(
                        accumulated=encoded_bytes,
                        additional=source_size,
                        description=relative_path,
                    )
                    remaining = (
                        None
                        if self.max_encoded_generation_bytes is None
                        else self.max_encoded_generation_bytes - encoded_bytes
                    )
                    physical_receipt = self._admit_physical_bytes(
                        operation=f"allocate_prepared_file:{relative_path}",
                        requested_bytes=source_size,
                    )
                    if physical_receipt is not None:
                        physical_remaining = physical_receipt[
                            "remaining_bytes"]
                        remaining = (
                            physical_remaining
                            if remaining is None
                            else min(remaining, physical_remaining)
                        )
                    if remaining is None:
                        digest, size = _copy_new_file(
                            source_path,
                            destination,
                        )
                    else:
                        digest, size = _copy_new_file(
                            source_path,
                            destination,
                            max_bytes=remaining,
                        )
                except OSError as error:
                    raise GenerationValidationError(
                        f"binary payload {relative_path!r} cannot be copied: {error}") from error
            elif isinstance(source, (bytes, bytearray, memoryview)):
                stored = bytes(source)
                self._admit_encoded_bytes(
                    accumulated=encoded_bytes,
                    additional=len(stored),
                    description=relative_path,
                )
                self._admit_physical_bytes(
                    operation=f"allocate_prepared_file:{relative_path}",
                    requested_bytes=len(stored),
                )
                digest, size = _write_new_bytes(destination, stored)
            else:
                raise GenerationValidationError(
                    f"binary payload {relative_path!r} must be bytes or a filesystem path")
            encoded_bytes += size

            records.append({
                "schema": FILE_RECORD_SCHEMA,
                "generation_uuid": generation_uuid,
                "identity": self.identity,
                "tick": tick,
                "relative_path": relative_path,
                "sha256": digest,
                "size_bytes": size,
            })

        # The manifest is deliberately the final file created in this directory.
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "generation_uuid": generation_uuid,
            "identity": self.identity,
            "tick": tick,
            "required_files": records,
        }
        manifest_bytes = _canonical_json(manifest)
        self._admit_encoded_bytes(
            accumulated=encoded_bytes,
            additional=len(manifest_bytes),
            description=MANIFEST_NAME,
        )
        self._admit_physical_bytes(
            operation=f"allocate_prepared_file:{MANIFEST_NAME}",
            requested_bytes=len(manifest_bytes),
        )
        _, manifest_size = _write_new_bytes(
            building / MANIFEST_NAME, manifest_bytes)
        encoded_bytes += manifest_size
        self._freeze_and_sync_directories(
            building,
            expected_directories,
        )
        return encoded_bytes

    def _actual_tree(self, generation_directory: Path) -> tuple[set[str], set[str]]:
        actual_files: set[str] = set()
        actual_directories: set[str] = set()
        for current_root, directory_names, file_names in os.walk(
                generation_directory, topdown=True, followlinks=False):
            root_path = Path(current_root)
            root_relative = root_path.relative_to(generation_directory)
            if root_relative != Path("."):
                actual_directories.add(root_relative.as_posix())
            root_info = root_path.lstat()
            if (not stat.S_ISDIR(root_info.st_mode)
                    or stat.S_IMODE(root_info.st_mode) != 0o555):
                raise GenerationValidationError(
                    f"generation directory {root_relative.as_posix()!r} is mutable or invalid")
            for name in directory_names:
                candidate = root_path / name
                if candidate.is_symlink():
                    raise GenerationValidationError(
                        f"generation contains symlink directory "
                        f"{candidate.relative_to(generation_directory).as_posix()!r}")
            for name in file_names:
                candidate = root_path / name
                relative = candidate.relative_to(generation_directory).as_posix()
                _assert_regular_read_only_file(
                    candidate, f"generation file {relative!r}")
                actual_files.add(relative)
        return actual_files, actual_directories

    def _verify_content_directory(
            self,
            generation_directory: Path,
            generation_uuid: str,
            manifest: Mapping[str, Any],
            manifest_bytes: bytes,
            manifest_sha256: str,
            *,
            validate_json_payloads: bool,
    ) -> LoadedGeneration:
        tick = _validated_tick(manifest.get("tick"))
        records = manifest.get("required_files")
        if not isinstance(records, list):
            raise GenerationValidationError(
                "content manifest required_files must be a JSON array")
        record_paths = []
        by_path = {}
        for record in records:
            if (
                not isinstance(record, dict)
                or set(record) != _CONTENT_FILE_RECORD_KEYS
                or record.get("schema") != CONTENT_FILE_RECORD_SCHEMA
            ):
                raise GenerationValidationError(
                    "content manifest has an invalid file record")
            relative = _validated_relative_path(record.get("relative_path"))
            if (
                record.get("generation_uuid") != generation_uuid
                or record.get("identity") != self.identity
                or record.get("tick") != tick
            ):
                raise GenerationValidationError(
                    f"content record {relative!r} has generation mismatch")
            if record.get("json_payload") is not relative.endswith(".json"):
                raise GenerationValidationError(
                    f"content record {relative!r} JSON role mismatch")
            digest = record.get("sha256")
            size = record.get("size_bytes")
            chunks = record.get("chunks")
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef"
                       for character in digest)
                or isinstance(size, bool)
                or not isinstance(size, int)
                or size < 0
                or not isinstance(chunks, list)
            ):
                raise GenerationValidationError(
                    f"content record {relative!r} is invalid")
            content_digest = hashlib.sha256()
            content_size = 0
            for chunk in chunks:
                if (
                    not isinstance(chunk, dict)
                    or set(chunk) != _CONTENT_CHUNK_KEYS
                    or chunk.get("schema") != CONTENT_CHUNK_SCHEMA
                ):
                    raise GenerationValidationError(
                        f"content record {relative!r} has invalid chunk")
                chunk_digest = chunk.get("sha256")
                chunk_size = chunk.get("size_bytes")
                if (
                    not isinstance(chunk_digest, str)
                    or len(chunk_digest) != 64
                    or any(character not in "0123456789abcdef"
                           for character in chunk_digest)
                    or isinstance(chunk_size, bool)
                    or not isinstance(chunk_size, int)
                    or not 0 < chunk_size <= CONTENT_CHUNK_MAX_BYTES
                ):
                    raise GenerationValidationError(
                        f"content record {relative!r} chunk is invalid")
                chunk_path = self._content_chunk_path(chunk_digest)
                info = _assert_content_chunk_file(
                    chunk_path, f"content chunk {chunk_digest}")
                actual_digest, actual_size = _sha256_file(chunk_path)
                if (
                    actual_digest != chunk_digest
                    or actual_size != chunk_size
                    or info.st_size != chunk_size
                ):
                    raise GenerationValidationError(
                        f"content chunk {chunk_digest} changed")
                with chunk_path.open("rb") as handle:
                    while True:
                        block = handle.read(1024 * 1024)
                        if not block:
                            break
                        content_digest.update(block)
                content_size += chunk_size
            if content_size != size or content_digest.hexdigest() != digest:
                raise GenerationValidationError(
                    f"content record {relative!r} body mismatch")
            if size == 0 and chunks:
                raise GenerationValidationError(
                    f"empty content record {relative!r} has chunks")
            if size > 0 and not chunks:
                raise GenerationValidationError(
                    f"content record {relative!r} has no chunks")
            record_paths.append(relative)
            by_path[relative] = copy.deepcopy(record)
        required = tuple(record_paths)
        if not required or required != tuple(sorted(set(required))):
            raise GenerationValidationError(
                "content manifest paths are empty, duplicated, or unordered")
        if self.required_files is not None and required != self.required_files:
            raise GenerationValidationError(
                "content manifest differs from the fixed store contract")
        actual_files, actual_directories = self._actual_tree(
            generation_directory)
        if actual_files != {MANIFEST_NAME} or actual_directories:
            raise GenerationValidationError(
                "content generation must contain only its manifest")
        if manifest_bytes != _canonical_json(manifest):
            raise GenerationValidationError(
                "content manifest is not canonical JSON")
        certificate = {
            "schema": CERTIFICATE_SCHEMA,
            "status": "verified",
            "generation_uuid": generation_uuid,
            "identity": self.identity,
            "tick": tick,
            "manifest_sha256": manifest_sha256,
            "required_files": copy.deepcopy(records),
        }
        loaded = LoadedGeneration(
            generation_uuid=generation_uuid,
            identity=self.identity,
            tick=tick,
            directory=generation_directory,
            manifest_sha256=manifest_sha256,
            _certificate_json=_canonical_json(certificate),
            _required_files=required,
            _content_chunks_root=self.content_chunks_directory,
            _content_records=by_path,
        )
        if validate_json_payloads:
            for relative in required:
                if relative.endswith(".json"):
                    _validate_streaming_json(
                        loaded.iter_stored_chunks(relative),
                        f"content JSON {relative!r}",
                    )
        return loaded

    def _verify_directory(
        self,
        generation_directory: Path,
        generation_uuid: str,
        *,
        validate_json_envelopes: bool = True,
    ) -> LoadedGeneration:
        try:
            directory_info = generation_directory.lstat()
        except FileNotFoundError as error:
            raise GenerationValidationError(
                f"generation directory {generation_uuid!r} is missing") from error
        if (not stat.S_ISDIR(directory_info.st_mode)
                or generation_directory.is_symlink()
                or stat.S_IMODE(directory_info.st_mode) != 0o555):
            raise GenerationValidationError(
                f"generation directory {generation_uuid!r} is mutable or invalid")

        manifest_path = generation_directory / MANIFEST_NAME
        manifest, manifest_bytes = _read_strict_json_file(
            manifest_path, "generation manifest")
        manifest_sha256 = _sha256_bytes(manifest_bytes)
        if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS:
            raise GenerationValidationError("generation manifest has an invalid field set")
        manifest_schema = manifest.get("schema")
        if manifest_schema == CONTENT_MANIFEST_SCHEMA:
            if manifest.get("generation_uuid") != generation_uuid:
                raise GenerationValidationError(
                    "content generation manifest UUID mismatch")
            if manifest.get("identity") != self.identity:
                raise GenerationValidationError(
                    "content generation manifest identity mismatch")
            return self._verify_content_directory(
                generation_directory,
                generation_uuid,
                manifest,
                manifest_bytes,
                manifest_sha256,
                validate_json_payloads=validate_json_envelopes,
            )
        if manifest_schema != MANIFEST_SCHEMA:
            raise GenerationValidationError(
                "generation manifest schema is unsupported")
        if manifest.get("generation_uuid") != generation_uuid:
            raise GenerationValidationError("generation manifest UUID mismatch")
        if manifest.get("identity") != self.identity:
            raise GenerationValidationError("generation manifest identity mismatch")
        tick = _validated_tick(manifest.get("tick"))

        records = manifest.get("required_files")
        if not isinstance(records, list):
            raise GenerationValidationError(
                "generation manifest required_files must be a JSON array")
        record_paths = []
        for record in records:
            if not isinstance(record, dict) or set(record) != _FILE_RECORD_KEYS:
                raise GenerationValidationError(
                    "generation manifest contains an invalid required-file record")
            if record.get("schema") != FILE_RECORD_SCHEMA:
                raise GenerationValidationError(
                    "generation manifest file-record schema is unsupported")
            relative_path = _validated_relative_path(record.get("relative_path"))
            record_paths.append(relative_path)
            if (record.get("generation_uuid") != generation_uuid
                    or record.get("identity") != self.identity
                    or record.get("tick") != tick):
                raise GenerationValidationError(
                    f"manifest record {relative_path!r} has generation metadata mismatch")
            digest = record.get("sha256")
            size = record.get("size_bytes")
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(character not in "0123456789abcdef" for character in digest)):
                raise GenerationValidationError(
                    f"manifest record {relative_path!r} has invalid SHA-256")
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise GenerationValidationError(
                    f"manifest record {relative_path!r} has invalid size")

        generation_required_files = tuple(record_paths)
        if not generation_required_files:
            raise GenerationValidationError(
                "generation manifest must contain at least one required file")
        if generation_required_files != tuple(sorted(set(record_paths))):
            raise GenerationValidationError(
                "manifest required-file records are duplicated or unordered")
        if (
            self.required_files is not None
            and generation_required_files != self.required_files
        ):
            raise GenerationValidationError(
                "manifest required-file records differ from the fixed "
                "store contract")
        expected_directories = _expected_directories(
            generation_required_files)
        actual_files, actual_directories = self._actual_tree(
            generation_directory)
        expected_files = set(generation_required_files) | {MANIFEST_NAME}
        if actual_files != expected_files:
            missing = sorted(expected_files - actual_files)
            extra = sorted(actual_files - expected_files)
            raise GenerationValidationError(
                f"generation required-file set mismatch: missing={missing}, "
                f"extra={extra}")
        if actual_directories != expected_directories:
            missing = sorted(expected_directories - actual_directories)
            extra = sorted(actual_directories - expected_directories)
            raise GenerationValidationError(
                f"generation directory set mismatch: missing={missing}, "
                f"extra={extra}")

        for record in records:
            relative_path = record["relative_path"]
            actual_digest, actual_size = _sha256_file(
                generation_directory / Path(relative_path))
            if (
                actual_digest != record["sha256"]
                or actual_size != record["size_bytes"]
            ):
                raise GenerationValidationError(
                    f"required file {relative_path!r} hash or size mismatch")

        if manifest_bytes != _canonical_json(manifest):
            raise GenerationValidationError(
                "generation manifest is not canonical JSON")

        if validate_json_envelopes:
            # Creation and reconciliation interpret every JSON envelope before
            # publication or retirement.  A sealed boot can instead stream
            # the exact manifest hashes here and let the one real engine load
            # perform the sole payload interpretation.
            for relative_path in generation_required_files:
                if not relative_path.endswith(".json"):
                    continue
                envelope, envelope_bytes = _read_strict_json_file(
                    generation_directory / Path(relative_path),
                    f"JSON envelope {relative_path!r}")
                if (
                    not isinstance(envelope, dict)
                    or set(envelope) != _ENVELOPE_KEYS
                ):
                    raise GenerationValidationError(
                        f"JSON envelope {relative_path!r} has an invalid field set")
                expected = {
                    "schema": ENVELOPE_SCHEMA,
                    "generation_uuid": generation_uuid,
                    "identity": self.identity,
                    "tick": tick,
                    "relative_path": relative_path,
                }
                for key, value in expected.items():
                    if envelope.get(key) != value:
                        raise GenerationValidationError(
                            f"JSON envelope {relative_path!r} has mismatched {key}")
                if envelope_bytes != _canonical_json(envelope):
                    raise GenerationValidationError(
                        f"JSON envelope {relative_path!r} is not canonical JSON")

        certificate = {
            "schema": CERTIFICATE_SCHEMA,
            "status": "verified",
            "generation_uuid": generation_uuid,
            "identity": self.identity,
            "tick": tick,
            "manifest_sha256": manifest_sha256,
            "required_files": copy.deepcopy(records),
        }
        certificate_json = _canonical_json(certificate)
        return LoadedGeneration(
            generation_uuid=generation_uuid,
            identity=self.identity,
            tick=tick,
            directory=generation_directory,
            manifest_sha256=manifest_sha256,
            _certificate_json=certificate_json,
            _required_files=generation_required_files,
        )

    @staticmethod
    def _current_pointer_bytes(loaded: LoadedGeneration) -> bytes:
        pointer = {
            "schema": CURRENT_SCHEMA,
            "generation_uuid": loaded.generation_uuid,
            "identity": loaded.identity,
            "tick": loaded.tick,
            "generation_path": (
                f"{GENERATIONS_DIRECTORY}/{loaded.generation_uuid}"),
            "manifest_sha256": loaded.manifest_sha256,
        }
        return _canonical_json(pointer)

    def _write_current(self, loaded: LoadedGeneration) -> None:
        pointer_bytes = self._current_pointer_bytes(loaded)
        temporary = self.root / f".{CURRENT_NAME}.{loaded.generation_uuid}.tmp"
        try:
            self._admit_physical_bytes(
                operation="allocate_current_pointer_temp",
                requested_bytes=len(pointer_bytes),
                rescan=True,
            )
            _write_new_bytes(temporary, pointer_bytes)
            self._admit_physical_bytes(
                operation="rename_current_pointer",
                requested_bytes=0,
                rescan=True,
            )
            os.replace(temporary, self.root / CURRENT_NAME)
            _fsync_directory(self.root)
        finally:
            if temporary.exists():
                temporary.unlink()
                _fsync_directory(self.root)

    def commit(self, *, tick: int, files: Mapping[str, Any],
               publish_current: bool = True,
               generation_uuid: str | None = None) -> LoadedGeneration:
        """Create and verify a generation; optionally publish CURRENT.

        Network-backed callers must defer CURRENT until their remote read-back
        proof succeeds.  The default preserves the local-only atomic commit
        contract.
        """
        tick = _validated_tick(tick)
        if not isinstance(files, Mapping):
            raise GenerationValidationError("files must be a mapping of path to source")
        supplied_paths = set()
        canonical_files = {}
        dynamic_path_bytes = 0
        for relative_path, source in files.items():
            canonical = _validated_relative_path(relative_path)
            supplied_paths.add(canonical)
            canonical_files[canonical] = source
            if self._required_set is None:
                dynamic_path_bytes += len(canonical.encode("utf-8"))
                if (
                    len(canonical_files)
                    > self.max_dynamic_required_files
                ):
                    raise GenerationCapacityError(
                        "dynamic generation exceeds required-file count "
                        "capacity before staging")
                if dynamic_path_bytes > self.max_dynamic_path_bytes:
                    raise GenerationCapacityError(
                        "dynamic generation exceeds required-path byte "
                        "capacity before staging")
        if len(canonical_files) != len(files) or not canonical_files:
            raise GenerationValidationError(
                "caller file set is empty, duplicated, or noncanonical")
        if self._required_set is None:
            required_files = tuple(sorted(canonical_files))
        else:
            if supplied_paths != self._required_set:
                missing = sorted(self._required_set - supplied_paths)
                extra = sorted(supplied_paths - self._required_set)
                raise GenerationValidationError(
                    f"caller file set mismatch: missing={missing}, "
                    f"extra={extra}")
            required_files = self.required_files

        if generation_uuid is None:
            generation_uuid = str(uuid.uuid4())
        else:
            generation_uuid = _canonical_generation_uuid(generation_uuid)
        building = self.generations_directory / f".building-{generation_uuid}"
        final = self.generations_directory / generation_uuid

        with self._exclusive_physical_scope():
            with self._exclusive_writer():
                if building.exists() or final.exists():
                    raise GenerationStoreError(
                        f"generation UUID collision {generation_uuid}")
                try:
                    encoded_bytes = self._write_generation_directory(
                        building,
                        generation_uuid,
                        tick,
                        canonical_files,
                        required_files,
                    )
                    prepublication = self._verify_directory(
                        building,
                        generation_uuid,
                    )
                    certificate_bytes = self._enforce_verified_capacity(
                        prepublication,
                        description="candidate generation",
                    )
                    if certificate_bytes != encoded_bytes:
                        raise GenerationValidationError(
                            "candidate encoded-byte census changed before "
                            "publication")
                    pointer_bytes = (
                        len(self._current_pointer_bytes(prepublication))
                        if publish_current
                        else 0
                    )
                    self._admit_physical_bytes(
                        operation="rename_prepared_generation",
                        requested_bytes=pointer_bytes,
                        rescan=True,
                        reserve=False,
                    )
                    os.rename(building, final)
                    _fsync_directory(self.generations_directory)
                    published = self._verify_directory(final, generation_uuid)
                    if (prepublication.recovery_certificate_bytes()
                            != published.recovery_certificate_bytes()):
                        raise GenerationValidationError(
                            "generation changed across publication rename")
                    if publish_current:
                        self._write_current(published)
                    return published
                except Exception:
                    if building.exists():
                        self._remove_building_directory(building)
                    if final.exists():
                        current_uuid = None
                        try:
                            pointer, canonical = self._read_current()
                        except CurrentPointerError:
                            pointer = None
                            canonical = False
                            if (self.root / CURRENT_NAME).exists():
                                current_uuid = generation_uuid
                        if canonical:
                            current_uuid = pointer["generation_uuid"]
                        if current_uuid != generation_uuid:
                            self._remove_retired_generation(final)
                            _fsync_directory(self.generations_directory)
                    self._reconcile_content_chunks_locked()
                    raise

    def publish(self, generation: LoadedGeneration) -> LoadedGeneration:
        """Reverify and atomically point CURRENT at a named generation."""
        if not isinstance(generation, LoadedGeneration):
            raise TypeError("generation must be a LoadedGeneration")
        if generation.identity != self.identity:
            raise GenerationValidationError("generation identity mismatch")
        if (
            self.required_files is not None
            and tuple(generation.required_files) != self.required_files
        ):
            raise GenerationValidationError("generation file contract mismatch")
        generation_uuid = _canonical_generation_uuid(
            generation.generation_uuid)
        with self._exclusive_physical_scope():
            with self._exclusive_writer():
                verified = self._verify_directory(
                    self.generations_directory / generation_uuid,
                    generation_uuid,
                )
                if (verified.recovery_certificate_bytes()
                        != generation.recovery_certificate_bytes()):
                    raise GenerationValidationError(
                        "generation changed before CURRENT publication")
                self._enforce_verified_capacity(
                    verified,
                    description="published generation",
                )
                self._write_current(verified)
                return verified

    @staticmethod
    def _remove_retired_generation(path: Path) -> None:
        """Remove one exact non-CURRENT generation without following links."""
        try:
            root_info = path.lstat()
        except FileNotFoundError as error:
            raise GenerationValidationError(
                f"retired generation {path.name!r} disappeared"
            ) from error
        if (
            path.is_symlink()
            or not stat.S_ISDIR(root_info.st_mode)
            or stat.S_IMODE(root_info.st_mode) != 0o555
        ):
            raise GenerationValidationError(
                f"retired generation {path.name!r} is unsafe"
            )
        directories = []
        for current_root, directory_names, file_names in os.walk(
                path, topdown=True, followlinks=False):
            current = Path(current_root)
            if current.is_symlink() or not current.is_dir():
                raise GenerationValidationError(
                    f"retired generation contains unsafe directory {current}"
                )
            directories.append(current)
            for name in directory_names:
                child = current / name
                if child.is_symlink() or not child.is_dir():
                    raise GenerationValidationError(
                        f"retired generation contains unsafe directory {child}"
                    )
            for name in file_names:
                child = current / name
                info = child.lstat()
                if child.is_symlink() or not stat.S_ISREG(info.st_mode):
                    raise GenerationValidationError(
                        f"retired generation contains unsafe file {child}"
                    )
        for directory in reversed(directories):
            os.chmod(directory, 0o700)
        shutil.rmtree(path)

    def _referenced_content_chunk_hashes(self) -> set[str]:
        referenced: set[str] = set()
        for generation_path in self.generations_directory.iterdir():
            if generation_path.name.startswith(".building-"):
                raise GenerationValidationError(
                    "unfinished generation prevents content reconciliation")
            generation_uuid = _canonical_generation_uuid(
                generation_path.name)
            generation = self._verify_directory(
                generation_path,
                generation_uuid,
                validate_json_envelopes=False,
            )
            if not generation.content_addressed:
                continue
            for record in generation.recovery_certificate()["required_files"]:
                for chunk in record["chunks"]:
                    referenced.add(chunk["sha256"])
        return referenced

    def _reconcile_content_chunks_locked(self) -> tuple[str, ...]:
        if not self.content_addressed:
            return ()
        referenced = self._referenced_content_chunk_hashes()
        removed: list[str] = []
        for prefix_path in tuple(self.content_chunks_directory.iterdir()):
            prefix = prefix_path.name
            if (
                prefix_path.is_symlink()
                or not prefix_path.is_dir()
                or len(prefix) != 2
                or any(character not in "0123456789abcdef"
                       for character in prefix)
            ):
                raise GenerationValidationError(
                    f"content chunk prefix {prefix!r} is unsafe")
            for candidate in tuple(prefix_path.iterdir()):
                name = candidate.name
                temporary_parts = name.split(".")
                is_abandoned_temporary = (
                    len(temporary_parts) == 4
                    and temporary_parts[0] == ""
                    and len(temporary_parts[1]) == 64
                    and all(character in "0123456789abcdef"
                            for character in temporary_parts[1])
                    and len(temporary_parts[2]) == 32
                    and all(character in "0123456789abcdef"
                            for character in temporary_parts[2])
                    and temporary_parts[3] == "tmp"
                )
                if is_abandoned_temporary:
                    info = candidate.lstat()
                    if (
                        candidate.is_symlink()
                        or not stat.S_ISREG(info.st_mode)
                        or info.st_nlink != 1
                    ):
                        raise GenerationValidationError(
                            f"abandoned content temporary {name!r} is unsafe")
                    candidate.unlink()
                    removed.append(name)
                    continue
                if (
                    len(name) != 64
                    or name[:2] != prefix
                    or any(character not in "0123456789abcdef"
                           for character in name)
                ):
                    raise GenerationValidationError(
                        f"content chunk name {name!r} is unsafe")
                _assert_content_chunk_file(
                    candidate, f"content chunk {name}")
                if name not in referenced:
                    candidate.unlink()
                    removed.append(name)
            if not any(prefix_path.iterdir()):
                prefix_path.rmdir()
            else:
                _fsync_directory(prefix_path)
        if removed:
            _fsync_directory(self.content_chunks_directory)
        return tuple(sorted(removed))

    def reconcile_content_chunks(self) -> tuple[str, ...]:
        """Remove only exact chunks unreachable from every finalized manifest."""
        with self._exclusive_physical_scope():
            with self._exclusive_writer():
                return self._reconcile_content_chunks_locked()

    def _retention_metadata(self, path: Path) -> tuple[int, str]:
        generation_uuid = _canonical_generation_uuid(path.name)
        manifest, manifest_bytes = _read_strict_json_file(
            path / MANIFEST_NAME,
            f"retention manifest {generation_uuid!r}",
        )
        if (
            not isinstance(manifest, dict)
            or set(manifest) != _MANIFEST_KEYS
            or manifest.get("schema") not in {
                MANIFEST_SCHEMA, CONTENT_MANIFEST_SCHEMA}
            or manifest.get("generation_uuid") != generation_uuid
            or manifest.get("identity") != self.identity
        ):
            raise GenerationValidationError(
                f"retention manifest {generation_uuid!r} is invalid"
            )
        tick = _validated_tick(manifest.get("tick"))
        if manifest_bytes != _canonical_json(manifest):
            raise GenerationValidationError(
                f"retention manifest {generation_uuid!r} is not canonical"
            )
        return tick, generation_uuid

    def prune_generations(
        self,
        *,
        retain: int = 3,
        verified_current: LoadedGeneration | None = None,
        protected_generation_uuids: Sequence[str] = (),
    ) -> tuple[str, ...]:
        """Retain CURRENT plus the newest immutable-manifest predecessors.

        The CURRENT generation is fully verified before any retirement.  A
        non-CURRENT directory is eligible only when its immutable manifest
        identifies this store and its UUID-derived path.  The finite retained
        count is a persistence resource boundary; it never changes substrate
        state or the remote sealed generations.
        """
        if (
            isinstance(retain, bool)
            or not isinstance(retain, int)
            or retain < MINIMUM_RETAINED_GENERATIONS
        ):
            raise GenerationValidationError(
                "generation retention must preserve CURRENT and a predecessor"
            )
        protected = tuple(
            _canonical_generation_uuid(generation_uuid)
            for generation_uuid in protected_generation_uuids
        )
        if len(protected) != len(set(protected)):
            raise GenerationValidationError(
                "protected generation retention identities must be unique"
            )
        if len(protected) >= retain:
            raise GenerationValidationError(
                "protected generation retention leaves no capacity for CURRENT"
            )
        with self._exclusive_writer():
            if verified_current is None:
                current = self.load_current()
            else:
                if (
                    not isinstance(verified_current, LoadedGeneration)
                    or verified_current.identity != self.identity
                    or (
                        self.required_files is not None
                        and verified_current.required_files
                        != self.required_files
                    )
                    or verified_current.directory.parent
                    != self.generations_directory
                ):
                    raise GenerationValidationError(
                        "verified CURRENT does not belong to this generation store"
                    )
                pointer, canonical = self._read_current()
                if (
                    not canonical
                    or pointer["generation_uuid"]
                    != verified_current.generation_uuid
                    or pointer["tick"] != verified_current.tick
                    or pointer["manifest_sha256"]
                    != verified_current.manifest_sha256
                ):
                    raise GenerationValidationError(
                        "verified CURRENT differs from the published pointer"
                    )
                current = verified_current
            metadata = []
            for path in self.generations_directory.iterdir():
                if path.name.startswith(".building-"):
                    raise GenerationValidationError(
                        "unfinished generation requires inspection before retention"
                    )
                metadata.append((*self._retention_metadata(path), path))
            metadata.sort(
                key=lambda item: (item[0], item[1]),
                reverse=True,
            )
            available = {
                generation_uuid
                for _tick, generation_uuid, _path in metadata
            }
            if current.generation_uuid in protected:
                raise GenerationValidationError(
                    "CURRENT cannot also be a protected predecessor"
                )
            absent_protected = sorted(set(protected) - available)
            if absent_protected:
                raise GenerationValidationError(
                    "protected generation retention identity is absent: "
                    + ", ".join(absent_protected)
                )
            retained = {
                current.generation_uuid,
                *protected,
            }
            for _tick, generation_uuid, _path in metadata:
                if generation_uuid == current.generation_uuid:
                    continue
                if len(retained) >= retain:
                    break
                retained.add(generation_uuid)
            removable = tuple(
                (generation_uuid, path)
                for _tick, generation_uuid, path in metadata
                if generation_uuid not in retained
            )
            for generation_uuid, path in removable:
                if generation_uuid == current.generation_uuid:
                    raise GenerationValidationError(
                        "generation retention selected CURRENT for removal"
                    )
                self._remove_retired_generation(path)
            if removable:
                _fsync_directory(self.generations_directory)
            self._reconcile_content_chunks_locked()
            if verified_current is None:
                self.load_current()
            else:
                pointer, canonical = self._read_current()
                if (
                    not canonical
                    or pointer["generation_uuid"] != current.generation_uuid
                    or not current.directory.is_dir()
                ):
                    raise GenerationValidationError(
                        "generation retention changed CURRENT"
                    )
            return tuple(generation_uuid for generation_uuid, _path in removable)

    @staticmethod
    def _remove_building_directory(building: Path) -> None:
        """Remove only this call's unpublished private directory."""
        for current_root, directory_names, _file_names in os.walk(
                building, topdown=False, followlinks=False):
            for name in directory_names:
                candidate = Path(current_root) / name
                if not candidate.is_symlink():
                    os.chmod(candidate, 0o700)
            os.chmod(current_root, 0o700)
        shutil.rmtree(building)

    def discard_orphan_building_directories(self) -> tuple[str, ...]:
        """Remove never-published private build trees under the writer lock."""
        removed = []
        with self._exclusive_writer():
            for building in self.generations_directory.iterdir():
                if not building.name.startswith(".building-"):
                    continue
                generation_uuid = building.name.removeprefix(".building-")
                _canonical_generation_uuid(generation_uuid)
                try:
                    info = building.lstat()
                except FileNotFoundError:
                    continue
                if building.is_symlink() or not stat.S_ISDIR(info.st_mode):
                    raise GenerationValidationError(
                        f"orphan building path {building.name!r} is unsafe")
                self._remove_building_directory(building)
                removed.append(generation_uuid)
            if removed:
                _fsync_directory(self.generations_directory)
            self._reconcile_content_chunks_locked()
        return tuple(removed)

    def verify_generation(self, generation_uuid: str) -> LoadedGeneration:
        """Verify a named immutable generation without changing CURRENT."""
        generation_uuid = _canonical_generation_uuid(generation_uuid)
        return self._verify_directory(
            self.generations_directory / generation_uuid,
            generation_uuid,
        )

    def verify_sealed_generation_integrity(
        self,
        generation_uuid: str,
    ) -> LoadedGeneration:
        """Stream-verify a previously sealed generation without JSON decoding.

        The exact tree, immutable modes, manifest, file sizes, and SHA-256
        hashes are still verified.  JSON payload interpretation remains a
        creation/reconciliation proof and the responsibility of the one real
        engine restore during boot.
        """
        generation_uuid = _canonical_generation_uuid(generation_uuid)
        return self._verify_directory(
            self.generations_directory / generation_uuid,
            generation_uuid,
            validate_json_envelopes=False,
        )

    def discard_unpublished(self, generation: LoadedGeneration) -> None:
        """Remove one verified candidate only when CURRENT cannot reference it."""
        if not isinstance(generation, LoadedGeneration):
            raise TypeError("generation must be a LoadedGeneration")
        if generation.identity != self.identity:
            raise GenerationValidationError("generation identity mismatch")
        if (
            self.required_files is not None
            and tuple(generation.required_files) != self.required_files
        ):
            raise GenerationValidationError("generation file contract mismatch")
        generation_uuid = _canonical_generation_uuid(
            generation.generation_uuid)

        with self._exclusive_writer():
            current_path = self.root / CURRENT_NAME
            try:
                current_path.lstat()
            except FileNotFoundError:
                pass
            else:
                pointer, canonical = self._read_current()
                if not canonical:
                    raise CurrentPointerError(
                        "CURRENT pointer is not canonical JSON")
                if pointer["generation_uuid"] == generation_uuid:
                    raise GenerationValidationError(
                        "refusing to discard the CURRENT generation")

            verified = self._verify_directory(
                self.generations_directory / generation_uuid,
                generation_uuid,
            )
            if (
                verified.recovery_certificate_bytes()
                != generation.recovery_certificate_bytes()
            ):
                raise GenerationValidationError(
                    "unpublished generation changed before discard")
            self._remove_retired_generation(verified.directory)
            _fsync_directory(self.generations_directory)
            self._reconcile_content_chunks_locked()

    def _read_current(self) -> tuple[dict, bool]:
        current_path = self.root / CURRENT_NAME
        try:
            info = current_path.lstat()
        except FileNotFoundError as error:
            raise CurrentPointerError("CURRENT pointer is missing") from error
        if (not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o444
                or info.st_nlink != 1):
            raise CurrentPointerError(
                "CURRENT pointer is not an immutable regular file")
        try:
            current_bytes = current_path.read_bytes()
            pointer = _strict_json_loads(
                current_bytes, "CURRENT pointer")
        except GenerationValidationError as error:
            raise CurrentPointerError(str(error)) from error
        if not isinstance(pointer, dict) or set(pointer) != _CURRENT_KEYS:
            raise CurrentPointerError("CURRENT pointer has an invalid field set")
        if pointer.get("schema") != CURRENT_SCHEMA:
            raise CurrentPointerError("CURRENT pointer schema is unsupported")
        try:
            generation_uuid = _canonical_generation_uuid(
                pointer.get("generation_uuid"))
            tick = _validated_tick(pointer.get("tick"))
        except GenerationValidationError as error:
            raise CurrentPointerError(str(error)) from error
        if pointer.get("identity") != self.identity:
            raise CurrentPointerError("CURRENT pointer identity mismatch")
        expected_path = f"{GENERATIONS_DIRECTORY}/{generation_uuid}"
        if pointer.get("generation_path") != expected_path:
            raise CurrentPointerError("CURRENT pointer generation path mismatch")
        digest = pointer.get("manifest_sha256")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)):
            raise CurrentPointerError("CURRENT pointer manifest SHA-256 is invalid")
        pointer["tick"] = tick
        return pointer, current_bytes == _canonical_json(pointer)

    def load_current(self) -> LoadedGeneration:
        """Load CURRENT only after exact pointer and generation verification."""
        pointer, current_is_canonical = self._read_current()
        try:
            loaded = self.verify_generation(pointer["generation_uuid"])
        except GenerationValidationError as error:
            raise CurrentPointerError(
                f"CURRENT generation failed verification: {error}") from error
        if loaded.tick != pointer["tick"]:
            raise CurrentPointerError("CURRENT pointer tick mismatch")
        if loaded.manifest_sha256 != pointer["manifest_sha256"]:
            raise CurrentPointerError("CURRENT pointer manifest hash mismatch")
        if not current_is_canonical:
            raise CurrentPointerError("CURRENT pointer is not canonical JSON")
        try:
            self._enforce_verified_capacity(
                loaded,
                description="CURRENT generation",
            )
        except GenerationCapacityError as error:
            raise CurrentPointerError(str(error)) from error
        return loaded

    def load_sealed_current_integrity(self) -> LoadedGeneration:
        """Stream-verify sealed CURRENT without decoding JSON payload bodies."""
        pointer, current_is_canonical = self._read_current()
        try:
            loaded = self.verify_sealed_generation_integrity(
                pointer["generation_uuid"]
            )
        except GenerationValidationError as error:
            raise CurrentPointerError(
                f"sealed CURRENT generation failed integrity verification: "
                f"{error}"
            ) from error
        if loaded.tick != pointer["tick"]:
            raise CurrentPointerError("CURRENT pointer tick mismatch")
        if loaded.manifest_sha256 != pointer["manifest_sha256"]:
            raise CurrentPointerError("CURRENT pointer manifest hash mismatch")
        if not current_is_canonical:
            raise CurrentPointerError("CURRENT pointer is not canonical JSON")
        try:
            self._enforce_verified_capacity(
                loaded,
                description="sealed CURRENT generation",
            )
        except GenerationCapacityError as error:
            raise CurrentPointerError(str(error)) from error
        return loaded


__all__ = [
    "CERTIFICATE_SCHEMA",
    "CURRENT_NAME",
    "CurrentPointerError",
    "GenerationCapacityError",
    "GenerationStoreError",
    "GenerationValidationError",
    "ImmutableGenerationStore",
    "LoadedGeneration",
    "MANIFEST_NAME",
    "MINIMUM_RETAINED_GENERATIONS",
    "PHYSICAL_BYTE_CEILING_RECEIPT_NAME",
    "PHYSICAL_BYTE_CEILING_SCHEMA",
    "PHYSICAL_BYTE_STATUS_SCHEMA",
    "PhysicalByteCeilingError",
]
