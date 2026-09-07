"""One atomic current body/world authority for the lean Guala runtime.

The store knows nothing about cognition. It durably places two immutable,
content-addressed physical state bodies and then atomically replaces one small
checksummed record naming the pair. The caller remains the sole writer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path
import struct
import uuid


MAGIC = b"GLPAIR01"
VERSION = 1
CURRENT_FILE = "CURRENT"
BODY_DIRECTORY = "body-generations"
WORLD_DIRECTORY = "world-generations"
BODY_SUFFIX = ".glorun"
WORLD_SUFFIX = ".glworld"
_DIGEST_BYTES = hashlib.sha256().digest_size
_RECORD = struct.Struct("<8sH36sQ32sQ32sQBQ32sQ32sQ")
RECORD_BYTES = _RECORD.size + _DIGEST_BYTES
_COPY_CHUNK_BYTES = 1024 * 1024


class PairedCurrentStoreError(RuntimeError):
    """The paired current authority is absent, damaged, or inconsistent."""


@dataclass(frozen=True, slots=True)
class PairDescriptor:
    identity: str
    organism_tick: int
    body_sha256: str
    body_bytes: int
    world_sha256: str
    world_bytes: int


@dataclass(frozen=True, slots=True)
class CurrentPair:
    current: PairDescriptor
    predecessor: PairDescriptor | None


@dataclass(frozen=True, slots=True)
class RestoredPair:
    pointer: CurrentPair
    body: bytes
    world: bytes


def _canonical_identity(value: object) -> str:
    if not isinstance(value, str):
        raise PairedCurrentStoreError("organism identity is not text")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as error:
        raise PairedCurrentStoreError("organism identity is not a UUID") from error
    if str(parsed) != value:
        raise PairedCurrentStoreError("organism identity is not canonical")
    return value


def _canonical_tick(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > (1 << 64) - 1
    ):
        raise PairedCurrentStoreError("organism tick is outside unsigned 64-bit")
    return value


def _canonical_digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PairedCurrentStoreError(f"{label} is not a canonical SHA-256")
    return value


def _canonical_size(value: object, maximum: int, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > maximum
    ):
        raise PairedCurrentStoreError(f"{label} is outside its byte bound")
    return value


def _descriptor(
    *,
    identity: object,
    organism_tick: object,
    body_sha256: object,
    body_bytes: object,
    world_sha256: object,
    world_bytes: object,
    max_body_bytes: int,
    max_world_bytes: int,
) -> PairDescriptor:
    return PairDescriptor(
        identity=_canonical_identity(identity),
        organism_tick=_canonical_tick(organism_tick),
        body_sha256=_canonical_digest(body_sha256, "body receipt"),
        body_bytes=_canonical_size(body_bytes, max_body_bytes, "body size"),
        world_sha256=_canonical_digest(world_sha256, "world receipt"),
        world_bytes=_canonical_size(world_bytes, max_world_bytes, "world size"),
    )


def _encode(pointer: CurrentPair) -> bytes:
    current = pointer.current
    predecessor = pointer.predecessor
    if predecessor is not None and predecessor.identity != current.identity:
        raise PairedCurrentStoreError("predecessor identity differs from current")
    core = _RECORD.pack(
        MAGIC,
        VERSION,
        current.identity.encode("ascii"),
        current.organism_tick,
        bytes.fromhex(current.body_sha256),
        current.body_bytes,
        bytes.fromhex(current.world_sha256),
        current.world_bytes,
        int(predecessor is not None),
        predecessor.organism_tick if predecessor else 0,
        bytes.fromhex(predecessor.body_sha256) if predecessor else bytes(32),
        predecessor.body_bytes if predecessor else 0,
        bytes.fromhex(predecessor.world_sha256) if predecessor else bytes(32),
        predecessor.world_bytes if predecessor else 0,
    )
    return core + hashlib.sha256(core).digest()


def _decode(
    body: bytes,
    *,
    max_body_bytes: int,
    max_world_bytes: int,
) -> CurrentPair:
    if len(body) != RECORD_BYTES:
        raise PairedCurrentStoreError("CURRENT changed byte count")
    core, receipt = body[:-_DIGEST_BYTES], body[-_DIGEST_BYTES:]
    if not hmac.compare_digest(receipt, hashlib.sha256(core).digest()):
        raise PairedCurrentStoreError("CURRENT checksum changed")
    (
        magic,
        version,
        raw_identity,
        tick,
        body_digest,
        body_size,
        world_digest,
        world_size,
        has_predecessor,
        predecessor_tick,
        predecessor_body_digest,
        predecessor_body_size,
        predecessor_world_digest,
        predecessor_world_size,
    ) = _RECORD.unpack(core)
    if magic != MAGIC or version != VERSION:
        raise PairedCurrentStoreError("CURRENT schema is unsupported")
    try:
        identity = raw_identity.decode("ascii")
    except UnicodeDecodeError as error:
        raise PairedCurrentStoreError("CURRENT identity is not ASCII") from error
    current = _descriptor(
        identity=identity,
        organism_tick=tick,
        body_sha256=body_digest.hex(),
        body_bytes=body_size,
        world_sha256=world_digest.hex(),
        world_bytes=world_size,
        max_body_bytes=max_body_bytes,
        max_world_bytes=max_world_bytes,
    )
    if has_predecessor not in (0, 1):
        raise PairedCurrentStoreError("CURRENT predecessor flag is invalid")
    if not has_predecessor:
        if predecessor_tick or predecessor_body_size or predecessor_world_size:
            raise PairedCurrentStoreError("CURRENT has hidden predecessor values")
        if any(predecessor_body_digest) or any(predecessor_world_digest):
            raise PairedCurrentStoreError("CURRENT has hidden predecessor receipts")
        return CurrentPair(current=current, predecessor=None)
    predecessor = _descriptor(
        identity=identity,
        organism_tick=predecessor_tick,
        body_sha256=predecessor_body_digest.hex(),
        body_bytes=predecessor_body_size,
        world_sha256=predecessor_world_digest.hex(),
        world_bytes=predecessor_world_size,
        max_body_bytes=max_body_bytes,
        max_world_bytes=max_world_bytes,
    )
    if predecessor.organism_tick > current.organism_tick:
        raise PairedCurrentStoreError("predecessor tick is ahead of current")
    return CurrentPair(current=current, predecessor=predecessor)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _require_real_directory(path: Path, *, create: bool) -> None:
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise PairedCurrentStoreError(f"{path.name} is not a real directory")


def _write_all(descriptor: int, body: bytes) -> None:
    view = memoryview(body)
    offset = 0
    while offset < len(view):
        written = os.write(descriptor, view[offset:])
        if written <= 0:
            raise PairedCurrentStoreError("durable write ended early")
        offset += written


def _release_file_cache(descriptor: int) -> None:
    os.posix_fadvise(descriptor, 0, 0, os.POSIX_FADV_DONTNEED)


def _read_verified(path: Path, expected_size: int, expected_digest: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise PairedCurrentStoreError(f"{path.name} is not a real file")
    if path.stat().st_size != expected_size:
        raise PairedCurrentStoreError(f"{path.name} changed byte count")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    chunks: list[bytes] = []
    digest = hashlib.sha256()
    read_bytes = 0
    try:
        while True:
            block = os.read(descriptor, _COPY_CHUNK_BYTES)
            if not block:
                break
            read_bytes += len(block)
            if read_bytes > expected_size:
                raise PairedCurrentStoreError(f"{path.name} exceeded its byte count")
            digest.update(block)
            chunks.append(block)
        _release_file_cache(descriptor)
    finally:
        os.close(descriptor)
    if read_bytes != expected_size or digest.hexdigest() != expected_digest:
        raise PairedCurrentStoreError(f"{path.name} receipt changed")
    return b"".join(chunks)


class PairedCurrentStore:
    """Sole-writer paired body/world persistence with fixed byte bounds."""

    def __init__(
        self,
        root: Path,
        *,
        max_body_bytes: int,
        max_world_bytes: int,
    ) -> None:
        if not isinstance(root, Path):
            raise TypeError("paired store root must be a Path")
        if max_body_bytes <= 0 or max_world_bytes <= 0:
            raise ValueError("paired store byte bounds must be positive")
        self._root = root
        self._max_body_bytes = max_body_bytes
        self._max_world_bytes = max_world_bytes
        self._bodies = root / BODY_DIRECTORY
        self._worlds = root / WORLD_DIRECTORY

    def initialize_empty(self) -> None:
        _require_real_directory(self._root, create=True)
        _require_real_directory(self._bodies, create=True)
        _require_real_directory(self._worlds, create=True)
        _sync_directory(self._root)

    def read_pointer(self) -> CurrentPair:
        _require_real_directory(self._root, create=False)
        path = self._root / CURRENT_FILE
        if path.is_symlink() or not path.is_file():
            raise PairedCurrentStoreError("paired CURRENT is absent")
        return _decode(
            path.read_bytes(),
            max_body_bytes=self._max_body_bytes,
            max_world_bytes=self._max_world_bytes,
        )

    def restore(self) -> RestoredPair:
        pointer = self.read_pointer()
        _require_real_directory(self._bodies, create=False)
        _require_real_directory(self._worlds, create=False)
        current = pointer.current
        body = _read_verified(
            self._bodies / f"{current.body_sha256}{BODY_SUFFIX}",
            current.body_bytes,
            current.body_sha256,
        )
        world = _read_verified(
            self._worlds / f"{current.world_sha256}{WORLD_SUFFIX}",
            current.world_bytes,
            current.world_sha256,
        )
        return RestoredPair(pointer=pointer, body=body, world=world)

    def publish(
        self,
        *,
        identity: str,
        organism_tick: int,
        body: bytes,
        world: bytes,
        expected_current_body_sha256: str | None,
    ) -> CurrentPair:
        if not isinstance(body, bytes) or not isinstance(world, bytes):
            raise TypeError("paired generations must be bytes")
        body_digest = hashlib.sha256(body).hexdigest()
        world_digest = hashlib.sha256(world).hexdigest()
        current = _descriptor(
            identity=identity,
            organism_tick=organism_tick,
            body_sha256=body_digest,
            body_bytes=len(body),
            world_sha256=world_digest,
            world_bytes=len(world),
            max_body_bytes=self._max_body_bytes,
            max_world_bytes=self._max_world_bytes,
        )
        self.initialize_empty()
        current_path = self._root / CURRENT_FILE
        if current_path.is_symlink():
            raise PairedCurrentStoreError("CURRENT changed path type")
        predecessor = None
        if current_path.exists():
            held = self.read_pointer()
            if expected_current_body_sha256 is None:
                raise PairedCurrentStoreError("existing CURRENT was not expected")
            expected = _canonical_digest(
                expected_current_body_sha256, "expected current body receipt"
            )
            if held.current.body_sha256 != expected:
                raise PairedCurrentStoreError("CURRENT advanced from another writer")
            if held.current.identity != current.identity:
                raise PairedCurrentStoreError("organism identity changed")
            if current.organism_tick < held.current.organism_tick:
                raise PairedCurrentStoreError("organism tick moved backward")
            predecessor = held.current
        elif expected_current_body_sha256 is not None:
            raise PairedCurrentStoreError("expected CURRENT is absent")

        self._write_immutable(
            self._bodies / f"{body_digest}{BODY_SUFFIX}", body, body_digest
        )
        self._write_immutable(
            self._worlds / f"{world_digest}{WORLD_SUFFIX}", world, world_digest
        )
        pointer = CurrentPair(current=current, predecessor=predecessor)
        self._replace_current(_encode(pointer))
        return pointer

    def _write_immutable(
        self, destination: Path, body: bytes, expected_digest: str
    ) -> None:
        if destination.exists() or destination.is_symlink():
            _read_verified(destination, len(body), expected_digest)
            return
        stage = destination.parent / f".stage-{uuid.uuid4()}"
        descriptor = os.open(
            stage,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        try:
            _write_all(descriptor, body)
            os.fsync(descriptor)
            _release_file_cache(descriptor)
        except BaseException:
            os.close(descriptor)
            try:
                stage.unlink()
            except FileNotFoundError:
                pass
            raise
        else:
            os.close(descriptor)
        try:
            if destination.exists() or destination.is_symlink():
                _read_verified(destination, len(body), expected_digest)
            else:
                os.replace(stage, destination)
                os.chmod(destination, 0o400)
            _sync_directory(destination.parent)
        finally:
            try:
                stage.unlink()
            except FileNotFoundError:
                pass

    def _replace_current(self, body: bytes) -> None:
        stage = self._root / f".current-{uuid.uuid4()}.stage"
        descriptor = os.open(
            stage,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        try:
            _write_all(descriptor, body)
            os.fsync(descriptor)
        except BaseException:
            os.close(descriptor)
            try:
                stage.unlink()
            except FileNotFoundError:
                pass
            raise
        else:
            os.close(descriptor)
        os.replace(stage, self._root / CURRENT_FILE)
        _sync_directory(self._root)

    def reconcile(self, pointer: CurrentPair | None = None) -> tuple[int, int]:
        held = pointer or self.read_pointer()
        retained_bodies = {held.current.body_sha256}
        retained_worlds = {held.current.world_sha256}
        if held.predecessor is not None:
            retained_bodies.add(held.predecessor.body_sha256)
            retained_worlds.add(held.predecessor.world_sha256)
        removed_count = 0
        removed_bytes = 0
        for directory, suffix, retained in (
            (self._bodies, BODY_SUFFIX, retained_bodies),
            (self._worlds, WORLD_SUFFIX, retained_worlds),
        ):
            _require_real_directory(directory, create=False)
            for path in tuple(directory.iterdir()):
                if path.name.startswith(".stage-"):
                    if path.is_symlink() or not path.is_file():
                        raise PairedCurrentStoreError("stage changed path type")
                    removed_bytes += path.stat().st_size
                    removed_count += 1
                    path.unlink()
                    continue
                if path.is_symlink() or not path.is_file() or not path.name.endswith(suffix):
                    raise PairedCurrentStoreError("generation directory has unknown artifact")
                receipt = path.name[: -len(suffix)]
                _canonical_digest(receipt, "generation filename")
                if receipt not in retained:
                    removed_bytes += path.stat().st_size
                    removed_count += 1
                    path.unlink()
            _sync_directory(directory)
        for stage in tuple(self._root.glob(".current-*.stage")):
            if stage.is_symlink() or not stage.is_file():
                raise PairedCurrentStoreError("CURRENT stage changed path type")
            removed_bytes += stage.stat().st_size
            removed_count += 1
            stage.unlink()
        _sync_directory(self._root)
        return removed_count, removed_bytes
