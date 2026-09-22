"""Shared fail-closed authority for persistent regular-file bytes.

Every cooperating writer configured with the same scope acquires the same
filesystem lock before admission and mutation.  The authority counts unique
regular-file content by device/inode identity, so hard links are physical
references to one retained byte body rather than duplicated capacity.

This module never deletes, prunes, compacts, or evicts state.  It either admits
an exact byte allocation or raises a typed refusal containing the complete
capacity receipt.
"""

from __future__ import annotations

import contextlib
import copy
import json
import os
import stat
import uuid
from pathlib import Path
from typing import Any, Iterator, Mapping

import fcntl


PHYSICAL_BYTE_CEILING_SCHEMA = "physical_byte_ceiling_v1"
PHYSICAL_BYTE_STATUS_SCHEMA = "physical_byte_status_v1"
PHYSICAL_BYTE_CEILING_RECEIPT_NAME = ".physical-byte-ceiling.json"
PHYSICAL_BYTE_CEILING_LOCK_NAME = ".physical-byte-ceiling.lock"


class PhysicalByteCeilingConfigurationError(ValueError):
    """The shared scope or its durable configuration receipt is invalid."""


class PhysicalByteCeilingError(RuntimeError):
    """A typed refusal before a persistence write would exceed its scope."""

    def __init__(self, receipt: Mapping[str, Any]):
        self.receipt = copy.deepcopy(dict(receipt))
        super().__init__(
            f"physical-byte ceiling refused {self.receipt['operation']}: "
            f"used={self.receipt['used_bytes']} bytes, "
            f"remaining={self.receipt['remaining_bytes']} bytes, "
            f"requested={self.receipt['requested_bytes']} bytes, "
            f"ceiling={self.receipt['ceiling_bytes']} bytes")


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
        raise PhysicalByteCeilingConfigurationError(
            f"physical-byte receipt is not canonical JSON: {error}") from error


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value!r}")


def _strict_json(data: bytes) -> Any:
    try:
        return json.loads(
            data.decode("utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise PhysicalByteCeilingConfigurationError(
            f"physical-byte receipt is not strict UTF-8 JSON: {error}") from error


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    written = 0
    while written < len(view):
        count = os.write(descriptor, view[written:])
        if count <= 0:
            raise OSError("physical-byte receipt write made no progress")
        written += count


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class PhysicalByteCeilingAuthority:
    """One durable lock and byte census shared by persistence writers."""

    def __init__(self, scope_root: str | os.PathLike[str], ceiling_bytes: int):
        if (
            isinstance(ceiling_bytes, bool)
            or not isinstance(ceiling_bytes, int)
            or ceiling_bytes <= 0
        ):
            raise PhysicalByteCeilingConfigurationError(
                "physical-byte ceiling must be a positive integer")
        supplied_scope = Path(scope_root)
        try:
            supplied_info = supplied_scope.lstat()
        except OSError as error:
            raise PhysicalByteCeilingConfigurationError(
                f"physical-byte scope cannot be inspected: {error}") from error
        if (
            supplied_scope.is_symlink()
            or not stat.S_ISDIR(supplied_info.st_mode)
        ):
            raise PhysicalByteCeilingConfigurationError(
                "physical-byte scope must be a real directory")
        self.scope_root = supplied_scope.resolve()
        self.ceiling_bytes = ceiling_bytes
        self.receipt_path = (
            self.scope_root / PHYSICAL_BYTE_CEILING_RECEIPT_NAME)
        self.lock_path = self.scope_root / PHYSICAL_BYTE_CEILING_LOCK_NAME
        with self.exclusive_writer():
            self._ensure_configuration_receipt()

    @contextlib.contextmanager
    def exclusive_writer(self) -> Iterator[None]:
        descriptor = os.open(
            self.lock_path,
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
            0o600,
        )
        try:
            lock_info = os.fstat(descriptor)
            if (
                not stat.S_ISREG(lock_info.st_mode)
                or lock_info.st_nlink != 1
            ):
                raise PhysicalByteCeilingConfigurationError(
                    "physical-byte lock must be a private regular file")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def configuration(self) -> dict:
        return {
            "schema": PHYSICAL_BYTE_CEILING_SCHEMA,
            "scope_root": str(self.scope_root),
            "ceiling_bytes": self.ceiling_bytes,
            "accounting": "unique_regular_file_logical_bytes",
        }

    def _ensure_configuration_receipt(self) -> None:
        expected = self.configuration()
        if self.receipt_path.exists():
            try:
                info = self.receipt_path.lstat()
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or stat.S_IMODE(info.st_mode) != 0o444
                ):
                    raise PhysicalByteCeilingConfigurationError(
                        "physical-byte receipt must be an immutable private "
                        "regular file")
                receipt_bytes = self.receipt_path.read_bytes()
                actual = _strict_json(receipt_bytes)
            except OSError as error:
                raise PhysicalByteCeilingConfigurationError(
                    f"physical-byte receipt cannot be read: {error}") from error
            if actual != expected or receipt_bytes != _canonical_json(actual):
                raise PhysicalByteCeilingConfigurationError(
                    "physical-byte ceiling configuration differs from the "
                    "durable scope receipt")
            return
        encoded = _canonical_json(expected)
        self.admit(
            operation="configure_physical_byte_ceiling",
            requested_bytes=len(encoded),
        )
        temporary = self.scope_root / (
            f".{PHYSICAL_BYTE_CEILING_RECEIPT_NAME}.{uuid.uuid4()}.tmp")
        descriptor = None
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            _write_all(descriptor, encoded)
            os.fchmod(descriptor, 0o444)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            self.admit(
                operation="publish_physical_byte_ceiling_receipt",
                requested_bytes=0,
            )
            os.replace(temporary, self.receipt_path)
            _fsync_directory(self.scope_root)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary.exists():
                temporary.unlink()
                _fsync_directory(self.scope_root)

    def used_bytes(self) -> int:
        seen: set[tuple[int, int]] = set()
        total = 0
        for current_root, directory_names, file_names in os.walk(
                self.scope_root, topdown=True, followlinks=False):
            root = Path(current_root)
            directory_names[:] = [
                name
                for name in directory_names
                if not (root / name).is_symlink()
            ]
            for name in file_names:
                path = root / name
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(info.st_mode):
                    continue
                inode = (info.st_dev, info.st_ino)
                if inode in seen:
                    continue
                seen.add(inode)
                total += info.st_size
        return total

    def _status(
            self, *, operation: str, used_bytes: int,
            requested_bytes: int, admitted: bool) -> dict:
        projected = used_bytes + requested_bytes
        return {
            "schema": PHYSICAL_BYTE_STATUS_SCHEMA,
            "status": "admitted" if admitted else "refused",
            "operation": operation,
            "scope_root": str(self.scope_root),
            "accounting": "unique_regular_file_logical_bytes",
            "ceiling_bytes": self.ceiling_bytes,
            "used_bytes": used_bytes,
            "remaining_bytes": max(0, self.ceiling_bytes - used_bytes),
            "requested_bytes": requested_bytes,
            "projected_bytes": projected,
            "over_ceiling_bytes": max(0, projected - self.ceiling_bytes),
        }

    def status(self) -> dict:
        used = self.used_bytes()
        return self._status(
            operation="status",
            used_bytes=used,
            requested_bytes=0,
            admitted=used <= self.ceiling_bytes,
        )

    def admit(self, *, operation: str, requested_bytes: int) -> dict:
        return self.admit_at(
            operation=operation,
            used_bytes=self.used_bytes(),
            requested_bytes=requested_bytes,
        )

    def admit_at(
            self, *, operation: str, used_bytes: int,
            requested_bytes: int) -> dict:
        for value, description in (
            (used_bytes, "used physical bytes"),
            (requested_bytes, "requested physical bytes"),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise PhysicalByteCeilingConfigurationError(
                    f"{description} must be a non-negative integer")
        admitted = used_bytes + requested_bytes <= self.ceiling_bytes
        receipt = self._status(
            operation=operation,
            used_bytes=used_bytes,
            requested_bytes=requested_bytes,
            admitted=admitted,
        )
        if not admitted:
            raise PhysicalByteCeilingError(receipt)
        return receipt

    def _target_path(
            self, path: str | os.PathLike[str], *,
            description: str) -> Path:
        target = Path(path)
        resolved_parent = target.parent.resolve(strict=True)
        try:
            resolved_parent.relative_to(self.scope_root)
        except ValueError as error:
            raise PhysicalByteCeilingConfigurationError(
                f"{description} is outside the physical-byte scope") from error
        if target.exists() and target.is_symlink():
            raise PhysicalByteCeilingConfigurationError(
                f"{description} must not be a symbolic link")
        return resolved_parent / target.name

    @contextlib.contextmanager
    def admitted_mutation(
            self, *, operation: str,
            requested_bytes: int) -> Iterator[dict]:
        """Hold the shared lock from exact admission through caller mutation.

        The caller must remove only its own incomplete temporary allocation if
        the mutation fails.  Existing authoritative state must remain intact.
        """
        with self.exclusive_writer():
            receipt = self.admit(
                operation=operation,
                requested_bytes=requested_bytes,
            )
            yield receipt

    def append_bytes(
            self, path: str | os.PathLike[str], data: bytes, *,
            operation: str, mode: int = 0o600) -> dict:
        """Append exact bytes and restore the prior file length on failure."""
        if not isinstance(data, bytes):
            raise TypeError("physical-byte append data must be bytes")
        target = self._target_path(path, description="append target")
        with self.admitted_mutation(
                operation=operation,
                requested_bytes=len(data)) as receipt:
            descriptor = os.open(
                target,
                os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
                mode,
            )
            prior_size = os.fstat(descriptor).st_size
            try:
                _write_all(descriptor, data)
                os.fsync(descriptor)
            except BaseException:
                os.ftruncate(descriptor, prior_size)
                os.fsync(descriptor)
                raise
            finally:
                os.close(descriptor)
            _fsync_directory(target.parent)
            return receipt

    def append_bytes_under_shared_lock(
            self, path: str | os.PathLike[str], data: bytes, *,
            operation: str, mode: int = 0o600) -> dict:
        """Append exactly when the caller already owns ``exclusive_writer``."""
        if not isinstance(data, bytes):
            raise TypeError("physical-byte append data must be bytes")
        target = self._target_path(path, description="append target")
        receipt = self.admit(
            operation=operation,
            requested_bytes=len(data),
        )
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
            mode,
        )
        prior_size = os.fstat(descriptor).st_size
        try:
            _write_all(descriptor, data)
            os.fsync(descriptor)
        except BaseException:
            os.ftruncate(descriptor, prior_size)
            os.fsync(descriptor)
            raise
        finally:
            os.close(descriptor)
        _fsync_directory(target.parent)
        return receipt

    def atomic_replace_bytes(
            self, path: str | os.PathLike[str], data: bytes, *,
            operation: str, mode: int = 0o600) -> dict:
        """Publish exact bytes while retaining the prior file until replace."""
        if not isinstance(data, bytes):
            raise TypeError("physical-byte replacement data must be bytes")
        with self.admitted_mutation(
                operation=operation,
                requested_bytes=len(data)) as receipt:
            self._atomic_replace_bytes_under_lock(
                path,
                data,
                mode=mode,
            )
            return receipt

    def atomic_replace_bytes_under_shared_lock(
            self, path: str | os.PathLike[str], data: bytes, *,
            operation: str, mode: int = 0o600) -> dict:
        """Admit and replace when the caller already holds ``exclusive_writer``."""
        if not isinstance(data, bytes):
            raise TypeError("physical-byte replacement data must be bytes")
        receipt = self.admit(
            operation=operation,
            requested_bytes=len(data),
        )
        self._atomic_replace_bytes_under_lock(path, data, mode=mode)
        return receipt

    def _atomic_replace_bytes_under_lock(
            self, path: str | os.PathLike[str], data: bytes, *,
            mode: int) -> None:
        target = self._target_path(path, description="replacement target")
        temporary = target.parent / f".{target.name}.{uuid.uuid4()}.tmp"
        descriptor = None
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                mode,
            )
            _write_all(descriptor, data)
            os.fchmod(descriptor, mode)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.replace(temporary, target)
            _fsync_directory(target.parent)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary.exists():
                temporary.unlink()
                _fsync_directory(target.parent)


__all__ = [
    "PHYSICAL_BYTE_CEILING_LOCK_NAME",
    "PHYSICAL_BYTE_CEILING_RECEIPT_NAME",
    "PHYSICAL_BYTE_CEILING_SCHEMA",
    "PHYSICAL_BYTE_STATUS_SCHEMA",
    "PhysicalByteCeilingAuthority",
    "PhysicalByteCeilingConfigurationError",
    "PhysicalByteCeilingError",
]
