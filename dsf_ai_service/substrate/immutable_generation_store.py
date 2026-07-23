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


ENVELOPE_SCHEMA = "immutable_generation_envelope_v1"
FILE_RECORD_SCHEMA = "immutable_generation_file_record_v1"
MANIFEST_SCHEMA = "immutable_generation_manifest_v1"
CURRENT_SCHEMA = "immutable_generation_current_v1"
CERTIFICATE_SCHEMA = "immutable_generation_recovery_certificate_v1"

MANIFEST_NAME = "MANIFEST.json"
CURRENT_NAME = "CURRENT"
GENERATIONS_DIRECTORY = "generations"
LOCK_NAME = ".generation-store.lock"
MINIMUM_RETAINED_GENERATIONS = 2

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


class GenerationStoreError(RuntimeError):
    """Base error for generation creation or verification failures."""


class GenerationValidationError(GenerationStoreError):
    """A generation, manifest, payload, or required path is invalid."""


class GenerationCapacityError(GenerationStoreError):
    """A candidate generation exceeds its configured encoded-byte capacity."""


class CurrentPointerError(GenerationStoreError):
    """The CURRENT pointer is absent, torn, corrupt, or inconsistent."""


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
    if value in {MANIFEST_NAME, CURRENT_NAME, GENERATIONS_DIRECTORY, LOCK_NAME}:
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
    with source.open("rb") as source_handle:
        source_stat = os.fstat(source_handle.fileno())
        if not stat.S_ISREG(source_stat.st_mode):
            raise GenerationValidationError(
                f"generation source {source} is not a regular file")
        if max_bytes is not None and source_stat.st_size > max_bytes:
            raise GenerationCapacityError(
                f"binary payload {source} exceeds remaining encoded-byte "
                f"capacity: {source_stat.st_size}>{max_bytes}")
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            while True:
                chunk = source_handle.read(1024 * 1024)
                if not chunk:
                    break
                if max_bytes is not None and size + len(chunk) > max_bytes:
                    raise GenerationCapacityError(
                        f"binary payload {source} changed beyond remaining "
                        "encoded-byte capacity while copied")
                _write_all(fd, chunk)
                digest.update(chunk)
                size += len(chunk)
            os.fchmod(fd, 0o444)
            os.fsync(fd)
        finally:
            os.close(fd)
    return digest.hexdigest(), size


def _read_regular_file(
        source: Path, description: str, *,
        max_bytes: int | None = None) -> bytes:
    chunks = []
    size = 0
    try:
        with source.open("rb") as handle:
            source_stat = os.fstat(handle.fileno())
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
                chunk = handle.read(read_size)
                if not chunk:
                    break
                size += len(chunk)
                if max_bytes is not None and size > max_bytes:
                    raise GenerationCapacityError(
                        f"{description} grew beyond remaining encoded-byte "
                        "capacity while read")
                chunks.append(chunk)
            final_stat = os.fstat(handle.fileno())
            if (
                size != source_stat.st_size
                or final_stat.st_size != source_stat.st_size
            ):
                raise GenerationValidationError(
                    f"{description} changed size while read")
    except OSError as error:
        raise GenerationValidationError(
            f"{description} source cannot be read: {error}") from error
    return b"".join(chunks)


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

    @property
    def required_files(self) -> tuple[str, ...]:
        return self._required_files

    def recovery_certificate(self) -> dict:
        """Return a fresh copy of the deterministic verification certificate."""
        return copy.deepcopy(_strict_json_loads(
            self._certificate_json, "recovery certificate"))

    def recovery_certificate_bytes(self) -> bytes:
        return bytes(self._certificate_json)

    def stored_bytes(self, relative_path: str) -> bytes:
        relative_path = _validated_relative_path(relative_path)
        if relative_path not in self._required_files:
            raise KeyError(relative_path)
        return (self.directory / Path(relative_path)).read_bytes()

    def payload(self, relative_path: str) -> Any:
        """Return the caller payload: decoded JSON or immutable binary bytes."""
        data = self.stored_bytes(relative_path)
        if relative_path.endswith(".json"):
            envelope = _strict_json_loads(data, f"JSON envelope {relative_path!r}")
            return copy.deepcopy(envelope["payload"])
        return data


class ImmutableGenerationStore:
    """Commits and verifies one fixed required-file set for one identity."""

    def __init__(self, root: str | os.PathLike[str], *, identity: str,
                 required_files: Sequence[str] | None,
                 max_encoded_generation_bytes: int | None = None,
                 max_dynamic_required_files: int | None = None,
                 max_dynamic_path_bytes: int | None = None):
        self.root = Path(root)
        self.identity = _validated_identity(identity)
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
        if self.root.is_symlink() or not self.root.is_dir():
            raise GenerationValidationError("generation-store root must be a real directory")
        if (self.generations_directory.is_symlink()
                or not self.generations_directory.is_dir()):
            raise GenerationValidationError(
                "generation directory must be a real directory")
        _fsync_directory(self.generations_directory)
        _fsync_directory(self.root)
        self._writer_local = threading.local()

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

    def _write_generation_directory(
        self,
        building: Path,
        generation_uuid: str,
        tick: int,
        files: Mapping[str, Any],
        required_files: tuple[str, ...],
    ) -> int:
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
                if size != source_size:
                    raise GenerationValidationError(
                        f"binary payload {relative_path!r} changed while copied")
            elif isinstance(source, (bytes, bytearray, memoryview)):
                stored = bytes(source)
                self._admit_encoded_bytes(
                    accumulated=encoded_bytes,
                    additional=len(stored),
                    description=relative_path,
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

    def _verify_directory(self, generation_directory: Path,
                          generation_uuid: str) -> LoadedGeneration:
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
        if manifest.get("schema") != MANIFEST_SCHEMA:
            raise GenerationValidationError("generation manifest schema is unsupported")
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

        # Verification above must use the supplied directory, including during
        # pre-publication verification.  Envelope verification is therefore
        # performed directly here rather than through CURRENT.
        for relative_path in generation_required_files:
            if not relative_path.endswith(".json"):
                continue
            envelope, envelope_bytes = _read_strict_json_file(
                generation_directory / Path(relative_path),
                f"JSON envelope {relative_path!r}")
            if not isinstance(envelope, dict) or set(envelope) != _ENVELOPE_KEYS:
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

    def _write_current(self, loaded: LoadedGeneration) -> None:
        pointer = {
            "schema": CURRENT_SCHEMA,
            "generation_uuid": loaded.generation_uuid,
            "identity": loaded.identity,
            "tick": loaded.tick,
            "generation_path": (
                f"{GENERATIONS_DIRECTORY}/{loaded.generation_uuid}"),
            "manifest_sha256": loaded.manifest_sha256,
        }
        temporary = self.root / f".{CURRENT_NAME}.{loaded.generation_uuid}.tmp"
        try:
            _write_new_bytes(temporary, _canonical_json(pointer))
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
                prepublication = self._verify_directory(building, generation_uuid)
                certificate_bytes = self._enforce_verified_capacity(
                    prepublication,
                    description="candidate generation",
                )
                if certificate_bytes != encoded_bytes:
                    raise GenerationValidationError(
                        "candidate encoded-byte census changed before publication")
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

    def _retention_metadata(self, path: Path) -> tuple[int, str]:
        generation_uuid = _canonical_generation_uuid(path.name)
        manifest, manifest_bytes = _read_strict_json_file(
            path / MANIFEST_NAME,
            f"retention manifest {generation_uuid!r}",
        )
        if (
            not isinstance(manifest, dict)
            or set(manifest) != _MANIFEST_KEYS
            or manifest.get("schema") != MANIFEST_SCHEMA
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
            retained = {current.generation_uuid}
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
        return tuple(removed)

    def verify_generation(self, generation_uuid: str) -> LoadedGeneration:
        """Verify a named immutable generation without changing CURRENT."""
        generation_uuid = _canonical_generation_uuid(generation_uuid)
        return self._verify_directory(
            self.generations_directory / generation_uuid,
            generation_uuid,
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
]
