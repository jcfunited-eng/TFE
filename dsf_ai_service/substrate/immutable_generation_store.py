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


def _copy_new_file(source: Path, destination: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as source_handle:
        source_stat = os.fstat(source_handle.fileno())
        if not stat.S_ISREG(source_stat.st_mode):
            raise GenerationValidationError(
                f"generation source {source} is not a regular file")
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            while True:
                chunk = source_handle.read(1024 * 1024)
                if not chunk:
                    break
                _write_all(fd, chunk)
                digest.update(chunk)
                size += len(chunk)
            os.fchmod(fd, 0o444)
            os.fsync(fd)
        finally:
            os.close(fd)
    return digest.hexdigest(), size


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
                 required_files: Sequence[str]):
        self.root = Path(root)
        self.identity = _validated_identity(identity)
        if isinstance(required_files, (str, bytes)):
            raise GenerationValidationError(
                "required_files must be a sequence of relative paths")
        validated = tuple(_validated_relative_path(item) for item in required_files)
        if not validated:
            raise GenerationValidationError("at least one required file is mandatory")
        if len(set(validated)) != len(validated):
            raise GenerationValidationError("required file paths must be unique")
        self.required_files = tuple(sorted(validated))
        self._required_set = frozenset(self.required_files)
        self._expected_directories = _expected_directories(self.required_files)

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

    @contextlib.contextmanager
    def _exclusive_writer(self) -> Iterator[None]:
        lock_path = self.root / LOCK_NAME
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    @staticmethod
    def _source_bytes(source: Any, description: str) -> bytes:
        if isinstance(source, bytes):
            return source
        if isinstance(source, (bytearray, memoryview)):
            return bytes(source)
        if isinstance(source, (str, os.PathLike)):
            source_path = Path(source)
            try:
                info = source_path.stat()
            except OSError as error:
                raise GenerationValidationError(
                    f"{description} source cannot be read: {error}") from error
            if not stat.S_ISREG(info.st_mode):
                raise GenerationValidationError(
                    f"{description} source is not a regular file")
            return source_path.read_bytes()
        raise GenerationValidationError(
            f"{description} source must be bytes or a filesystem path")

    def _json_envelope(self, relative_path: str, source: Any,
                       generation_uuid: str, tick: int) -> bytes:
        raw = self._source_bytes(source, f"JSON payload {relative_path!r}")
        payload = _strict_json_loads(raw, f"JSON payload {relative_path!r}")
        return _canonical_json({
            "schema": ENVELOPE_SCHEMA,
            "generation_uuid": generation_uuid,
            "identity": self.identity,
            "tick": tick,
            "relative_path": relative_path,
            "payload": payload,
        })

    def _create_required_directories(self, building: Path) -> None:
        for relative_directory in sorted(
                self._expected_directories,
                key=lambda value: (len(PurePosixPath(value).parts), value)):
            (building / Path(relative_directory)).mkdir(exist_ok=False)

    def _freeze_and_sync_directories(self, generation_directory: Path) -> None:
        directories = [generation_directory]
        directories.extend(
            generation_directory / Path(relative)
            for relative in self._expected_directories)
        for directory in sorted(
                directories, key=lambda path: len(path.parts), reverse=True):
            os.chmod(directory, 0o555)
            _fsync_directory(directory)

    def _write_generation_directory(self, building: Path, generation_uuid: str,
                                    tick: int, files: Mapping[str, Any]) -> None:
        building.mkdir(mode=0o700)
        self._create_required_directories(building)
        records = []

        for relative_path in self.required_files:
            destination = building / Path(relative_path)
            source = files[relative_path]
            if relative_path.endswith(".json"):
                stored = self._json_envelope(
                    relative_path, source, generation_uuid, tick)
                digest, size = _write_new_bytes(destination, stored)
            elif isinstance(source, (str, os.PathLike)):
                source_path = Path(source)
                try:
                    digest, size = _copy_new_file(source_path, destination)
                except OSError as error:
                    raise GenerationValidationError(
                        f"binary payload {relative_path!r} cannot be copied: {error}") from error
            elif isinstance(source, (bytes, bytearray, memoryview)):
                digest, size = _write_new_bytes(destination, bytes(source))
            else:
                raise GenerationValidationError(
                    f"binary payload {relative_path!r} must be bytes or a filesystem path")

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
        _write_new_bytes(building / MANIFEST_NAME, _canonical_json(manifest))
        self._freeze_and_sync_directories(building)

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

        actual_files, actual_directories = self._actual_tree(generation_directory)
        expected_files = set(self.required_files) | {MANIFEST_NAME}
        if actual_files != expected_files:
            missing = sorted(expected_files - actual_files)
            extra = sorted(actual_files - expected_files)
            raise GenerationValidationError(
                f"generation required-file set mismatch: missing={missing}, extra={extra}")
        if actual_directories != self._expected_directories:
            missing = sorted(self._expected_directories - actual_directories)
            extra = sorted(actual_directories - self._expected_directories)
            raise GenerationValidationError(
                f"generation directory set mismatch: missing={missing}, extra={extra}")

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
            actual_digest, actual_size = _sha256_file(
                generation_directory / Path(relative_path))
            if actual_digest != digest or actual_size != size:
                raise GenerationValidationError(
                    f"required file {relative_path!r} hash or size mismatch")

        if tuple(record_paths) != self.required_files:
            raise GenerationValidationError(
                "manifest required-file records are missing, duplicated, extra, or unordered")
        if manifest_bytes != _canonical_json(manifest):
            raise GenerationValidationError(
                "generation manifest is not canonical JSON")

        # Verification above must use the supplied directory, including during
        # pre-publication verification.  Envelope verification is therefore
        # performed directly here rather than through CURRENT.
        for relative_path in self.required_files:
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
            _required_files=self.required_files,
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
        for relative_path, source in files.items():
            canonical = _validated_relative_path(relative_path)
            supplied_paths.add(canonical)
            canonical_files[canonical] = source
        if supplied_paths != self._required_set or len(canonical_files) != len(files):
            missing = sorted(self._required_set - supplied_paths)
            extra = sorted(supplied_paths - self._required_set)
            raise GenerationValidationError(
                f"caller file set mismatch: missing={missing}, extra={extra}")

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
                self._write_generation_directory(
                    building, generation_uuid, tick, canonical_files)
                prepublication = self._verify_directory(building, generation_uuid)
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
        if tuple(generation.required_files) != self.required_files:
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
            self._write_current(verified)
            return verified

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

    def verify_generation(self, generation_uuid: str) -> LoadedGeneration:
        """Verify a named immutable generation without changing CURRENT."""
        generation_uuid = _canonical_generation_uuid(generation_uuid)
        return self._verify_directory(
            self.generations_directory / generation_uuid,
            generation_uuid,
        )

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
        return loaded


__all__ = [
    "CERTIFICATE_SCHEMA",
    "CURRENT_NAME",
    "CurrentPointerError",
    "GenerationStoreError",
    "GenerationValidationError",
    "ImmutableGenerationStore",
    "LoadedGeneration",
    "MANIFEST_NAME",
]
