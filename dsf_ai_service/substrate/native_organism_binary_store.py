"""Exact one-object persistence for a native resident organism.

The cognitive authority is one raw ``GLORUN01`` byte string.  Its immutable
generation is stored in one deterministic lossless representation; cold
restore reconstructs and verifies the exact authoritative bytes before native
admission.  ``CURRENT`` remains a fixed-width atomic publication pointer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import lzma
import os
from pathlib import Path
import stat
import struct
from typing import Callable, Iterable, Protocol
import uuid

from dsf_ai_service.glew_runtime.native_resident_organism import (
    NativeResidentOrganism,
    migrate_native_resident_organism_exact_energy,
    restore_native_resident_organism,
)


STATE_MAGIC = b"GLORUN01"
COMPACT_STATE_MAGIC = b"GLCMP001"
COMPACT_STATE_VERSION = 1
COMPACT_STATE_CODEC_LZMA2 = 1
COMPACT_STATE_PRESET = 0
CURRENT_MAGIC = b"GLCUR001"
CURRENT_VERSION = 1
STATE_SUFFIX = ".glorun"
GENERATIONS_DIRECTORY = "generations"
CURRENT_NAME = "CURRENT"
REMOTE_PREFIX = "guala/native-organism"
IDENTITY_BYTES = 36
SHA256_BYTES = 32
STREAM_BYTES = 1024 * 1024
_POINTER_BODY = struct.Struct("<8sH36sQQ32s32s")
POINTER_BYTES = _POINTER_BODY.size + SHA256_BYTES
_COMPACT_STATE_HEADER = struct.Struct("<8sHBBQ32sQ")


class NativeOrganismBinaryStoreError(RuntimeError):
    """An exact binary persistence contract was refused."""


class StreamingObjectStore(Protocol):
    """Injected immutable streaming transport for an object-store adapter."""

    def put_if_absent(
        self,
        key: str,
        chunks: Iterable[bytes],
        *,
        byte_count: int,
        sha256: str,
    ) -> bool: ...

    def iter_bytes(self, key: str) -> Iterable[bytes]: ...

    def delete_if_exact(
        self,
        key: str,
        *,
        byte_count: int,
        sha256: str,
    ) -> None: ...


FailureInjector = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class NativeOrganismPointer:
    identity: str
    organism_tick: int
    state_bytes: int
    state_sha256: str
    predecessor_state_sha256: str | None


@dataclass(frozen=True, slots=True)
class StagedNativeOrganism:
    store_root: Path
    path: Path
    identity: str
    organism_tick: int
    state_bytes: int
    state_sha256: str
    stored_bytes: int
    stored_sha256: str


@dataclass(frozen=True, slots=True)
class NativeOrganismBodyAccounting:
    current_bytes: int
    retained_predecessor_bytes: int
    staged_bytes: int
    exact_peak_bytes: int


@dataclass(frozen=True, slots=True)
class RestoredNativeOrganism:
    organism: NativeResidentOrganism
    pointer: NativeOrganismPointer


@dataclass(frozen=True, slots=True)
class PublishedNativeOrganism:
    pointer: NativeOrganismPointer
    accounting: NativeOrganismBodyAccounting
    remote_key: str


@dataclass(frozen=True, slots=True)
class _NativeBodyFacts:
    identity: str
    organism_tick: int
    state_bytes: int
    state_sha256: str


def _fault(injector: FailureInjector | None, step: str) -> None:
    if injector is not None:
        injector(step)


def _canonical_digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise NativeOrganismBinaryStoreError(
            f"native organism {label} is not canonical SHA-256"
        )
    return value


def _canonical_identity(value: object) -> str:
    if not isinstance(value, str):
        raise NativeOrganismBinaryStoreError(
            "native organism identity is not text"
        )
    try:
        canonical = str(uuid.UUID(value))
        encoded = value.encode("ascii")
    except (AttributeError, UnicodeEncodeError, ValueError) as error:
        raise NativeOrganismBinaryStoreError(
            "native organism identity is not canonical"
        ) from error
    if canonical != value or len(encoded) != IDENTITY_BYTES:
        raise NativeOrganismBinaryStoreError(
            "native organism identity is not canonical"
        )
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise NativeOrganismBinaryStoreError(
            f"native organism {label} is not a nonnegative integer"
        )
    return value


def _positive_integer(value: object, label: str) -> int:
    result = _nonnegative_integer(value, label)
    if result == 0:
        raise NativeOrganismBinaryStoreError(
            f"native organism {label} is not positive"
        )
    return result


def _store_root(value: str | os.PathLike[str]) -> Path:
    candidate = Path(value)
    if candidate.exists() and candidate.is_symlink():
        raise NativeOrganismBinaryStoreError(
            "native organism store root cannot be a symbolic link"
        )
    root = candidate.resolve()
    if root == Path(root.anchor):
        raise NativeOrganismBinaryStoreError(
            "native organism store root cannot be a filesystem root"
        )
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise NativeOrganismBinaryStoreError(
            "native organism store root is not a real directory"
        )
    generations = root / GENERATIONS_DIRECTORY
    generations.mkdir(mode=0o700, exist_ok=True)
    if generations.is_symlink() or not generations.is_dir():
        raise NativeOrganismBinaryStoreError(
            "native organism generations path is not a real directory"
        )
    return root


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, body: bytes) -> None:
    view = memoryview(body)
    offset = 0
    while offset < len(view):
        written = os.write(descriptor, view[offset:])
        if written <= 0:
            raise NativeOrganismBinaryStoreError(
                "native organism write ended early"
            )
        offset += written


def _regular_file(path: Path, label: str) -> os.stat_result:
    try:
        information = path.lstat()
    except FileNotFoundError as error:
        raise NativeOrganismBinaryStoreError(
            f"native organism {label} is absent"
        ) from error
    if (
        path.is_symlink()
        or not stat.S_ISREG(information.st_mode)
        or information.st_nlink != 1
    ):
        raise NativeOrganismBinaryStoreError(
            f"native organism {label} is not a private regular file"
        )
    return information


def _stream_file(path: Path) -> Iterable[bytes]:
    with path.open("rb") as source:
        while True:
            block = source.read(STREAM_BYTES)
            if not block:
                return
            yield block


def _file_receipt(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    byte_count = 0
    for block in _stream_file(path):
        digest.update(block)
        byte_count += len(block)
    return byte_count, digest.hexdigest()


def _compact_filters() -> list[dict[str, int]]:
    """The one fixed, lowest-work lossless storage transform."""

    return [{"id": lzma.FILTER_LZMA2, "preset": COMPACT_STATE_PRESET}]


def _encode_stored_state(state: bytes) -> bytes:
    """Encode canonical GLORUN bytes without changing their authority."""

    if not isinstance(state, bytes) or not state.startswith(STATE_MAGIC):
        raise NativeOrganismBinaryStoreError(
            "native organism compact source is not exact GLORUN"
        )
    raw_sha256 = hashlib.sha256(state).digest()
    payload = lzma.compress(
        state,
        format=lzma.FORMAT_RAW,
        filters=_compact_filters(),
    )
    header = _COMPACT_STATE_HEADER.pack(
        COMPACT_STATE_MAGIC,
        COMPACT_STATE_VERSION,
        COMPACT_STATE_CODEC_LZMA2,
        COMPACT_STATE_PRESET,
        len(state),
        raw_sha256,
        len(payload),
    )
    return header + payload


def _decode_stored_state(
    stored: bytes,
    *,
    expected_bytes: int,
    expected_sha256: str,
    max_envelope_bytes: int,
) -> bytes:
    """Recover one exact raw GLORUN from current or predecessor storage."""

    expected_count = _positive_integer(expected_bytes, "state byte count")
    maximum = _positive_integer(max_envelope_bytes, "envelope admission")
    expected_digest = _canonical_digest(expected_sha256, "state receipt")
    if expected_count > maximum or not isinstance(stored, bytes):
        raise NativeOrganismBinaryStoreError(
            "native organism state exceeds admission or changed byte count"
        )
    # One-way rollout compatibility: task1089's current and predecessor are
    # canonical raw GLORUN files. New publications are compact. After two
    # ordinary successors no raw generation remains retained.
    if stored.startswith(STATE_MAGIC):
        state = stored
    else:
        if len(stored) < _COMPACT_STATE_HEADER.size:
            raise NativeOrganismBinaryStoreError(
                "native organism compact state ended before its header"
            )
        (
            magic,
            version,
            codec,
            preset,
            raw_bytes,
            raw_sha256,
            payload_bytes,
        ) = _COMPACT_STATE_HEADER.unpack_from(stored)
        payload = stored[_COMPACT_STATE_HEADER.size :]
        if (
            magic != COMPACT_STATE_MAGIC
            or version != COMPACT_STATE_VERSION
            or codec != COMPACT_STATE_CODEC_LZMA2
            or preset != COMPACT_STATE_PRESET
            or raw_bytes != expected_count
            or raw_sha256.hex() != expected_digest
            or payload_bytes != len(payload)
        ):
            raise NativeOrganismBinaryStoreError(
                "native organism compact state header changed"
            )
        try:
            decoder = lzma.LZMADecompressor(
                format=lzma.FORMAT_RAW,
                filters=_compact_filters(),
            )
            # ``max_length`` makes the raw envelope admission an allocation
            # boundary even if the compact bytes are corrupt or adversarial.
            state = decoder.decompress(payload, max_length=expected_count + 1)
        except lzma.LZMAError as error:
            raise NativeOrganismBinaryStoreError(
                "native organism compact state could not be reconstructed"
            ) from error
        if not decoder.eof or decoder.unused_data:
            raise NativeOrganismBinaryStoreError(
                "native organism compact state did not end exactly"
            )
    if (
        len(state) != expected_count
        or not state.startswith(STATE_MAGIC)
        or hashlib.sha256(state).hexdigest() != expected_digest
    ):
        raise NativeOrganismBinaryStoreError(
            "native organism state is not exact current GLORUN"
        )
    return state


def _stored_state_raw_bytes(path: Path, expected_sha256: str) -> int:
    """Read only the retained representation header's canonical raw size."""

    information = _regular_file(path, "state body")
    expected_digest = _canonical_digest(expected_sha256, "state receipt")
    with path.open("rb") as source:
        prefix = source.read(_COMPACT_STATE_HEADER.size)
    if prefix.startswith(STATE_MAGIC):
        stored_bytes, stored_sha256 = _file_receipt(path)
        if stored_sha256 != expected_digest:
            raise NativeOrganismBinaryStoreError(
                "native organism raw retained state changed"
            )
        return _positive_integer(stored_bytes, "state byte count")
    if len(prefix) != _COMPACT_STATE_HEADER.size:
        raise NativeOrganismBinaryStoreError(
            "native organism compact state ended before its header"
        )
    (
        magic,
        version,
        codec,
        preset,
        raw_bytes,
        raw_sha256,
        payload_bytes,
    ) = _COMPACT_STATE_HEADER.unpack(prefix)
    if (
        magic != COMPACT_STATE_MAGIC
        or version != COMPACT_STATE_VERSION
        or codec != COMPACT_STATE_CODEC_LZMA2
        or preset != COMPACT_STATE_PRESET
        or raw_sha256.hex() != expected_digest
        or payload_bytes != information.st_size - _COMPACT_STATE_HEADER.size
    ):
        raise NativeOrganismBinaryStoreError(
            "native organism compact state header changed"
        )
    return _positive_integer(raw_bytes, "state byte count")


def _read_exact_state(
    path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
    max_envelope_bytes: int,
) -> bytes:
    _regular_file(path, "state body")
    return _decode_stored_state(
        path.read_bytes(),
        expected_bytes=expected_bytes,
        expected_sha256=expected_sha256,
        max_envelope_bytes=max_envelope_bytes,
    )


def _encode_pointer(pointer: NativeOrganismPointer) -> bytes:
    identity = _canonical_identity(pointer.identity).encode("ascii")
    tick = _nonnegative_integer(pointer.organism_tick, "organism tick")
    byte_count = _positive_integer(pointer.state_bytes, "state byte count")
    state_digest = bytes.fromhex(
        _canonical_digest(pointer.state_sha256, "state receipt")
    )
    predecessor_digest = (
        bytes(SHA256_BYTES)
        if pointer.predecessor_state_sha256 is None
        else bytes.fromhex(
            _canonical_digest(
                pointer.predecessor_state_sha256,
                "predecessor state receipt",
            )
        )
    )
    if predecessor_digest == state_digest:
        raise NativeOrganismBinaryStoreError(
            "native organism predecessor equals current state"
        )
    record = _POINTER_BODY.pack(
        CURRENT_MAGIC,
        CURRENT_VERSION,
        identity,
        tick,
        byte_count,
        state_digest,
        predecessor_digest,
    )
    return record + hashlib.sha256(record).digest()


def _decode_pointer(body: bytes) -> NativeOrganismPointer:
    if not isinstance(body, bytes) or len(body) != POINTER_BYTES:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT pointer has changed width"
        )
    record = body[:-SHA256_BYTES]
    if hashlib.sha256(record).digest() != body[-SHA256_BYTES:]:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT pointer receipt changed"
        )
    (
        magic,
        version,
        identity,
        tick,
        byte_count,
        state_digest,
        predecessor_digest,
    ) = _POINTER_BODY.unpack(record)
    if magic != CURRENT_MAGIC or version != CURRENT_VERSION:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT pointer schema changed"
        )
    try:
        identity_text = identity.decode("ascii")
    except UnicodeDecodeError as error:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT identity is invalid"
        ) from error
    predecessor = (
        None
        if predecessor_digest == bytes(SHA256_BYTES)
        else predecessor_digest.hex()
    )
    return NativeOrganismPointer(
        identity=_canonical_identity(identity_text),
        organism_tick=_nonnegative_integer(tick, "organism tick"),
        state_bytes=_positive_integer(byte_count, "state byte count"),
        state_sha256=_canonical_digest(state_digest.hex(), "state receipt"),
        predecessor_state_sha256=predecessor,
    )


def _read_current(root: Path) -> NativeOrganismPointer | None:
    path = root / CURRENT_NAME
    if not path.exists():
        return None
    information = _regular_file(path, "CURRENT pointer")
    if information.st_size != POINTER_BYTES:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT pointer changed byte count"
        )
    return _decode_pointer(path.read_bytes())


def _generation_path(root: Path, state_sha256: str) -> Path:
    digest = _canonical_digest(state_sha256, "generation receipt")
    return root / GENERATIONS_DIRECTORY / f"{digest}{STATE_SUFFIX}"


def _remote_key(state_sha256: str) -> str:
    digest = _canonical_digest(state_sha256, "remote receipt")
    return f"{REMOTE_PREFIX}/{digest}{STATE_SUFFIX}"


def _observe(organism: NativeResidentOrganism) -> _NativeBodyFacts:
    if not isinstance(organism, NativeResidentOrganism):
        raise TypeError(
            "binary persistence requires a concrete NativeResidentOrganism"
        )
    observation = organism.readiness()
    return _NativeBodyFacts(
        identity=_canonical_identity(observation.identity),
        organism_tick=_nonnegative_integer(
            observation.organism_tick, "organism tick"
        ),
        state_bytes=_positive_integer(
            observation.state_bytes, "state byte count"
        ),
        state_sha256=_canonical_digest(
            observation.state_sha256, "state receipt"
        ),
    )


def _prove_restored_body(
    body: bytes,
    *,
    expected_identity: str,
    expected_bytes: int,
    expected_sha256: str,
    expected_tick: int | None,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> tuple[NativeResidentOrganism, _NativeBodyFacts]:
    maximum = _positive_integer(max_envelope_bytes, "envelope admission")
    expected_identity = _canonical_identity(expected_identity)
    expected_bytes = _positive_integer(expected_bytes, "state byte count")
    expected_sha256 = _canonical_digest(expected_sha256, "state receipt")
    if (
        not isinstance(body, bytes)
        or len(body) != expected_bytes
        or len(body) > maximum
        or not body.startswith(STATE_MAGIC)
        or hashlib.sha256(body).hexdigest() != expected_sha256
    ):
        raise NativeOrganismBinaryStoreError(
            "native organism restore input is not the exact binary body"
        )
    try:
        organism = restore_native_resident_organism(
            current_envelope=body,
            max_envelope_bytes=maximum,
            max_fabric_bytes=max_fabric_bytes,
            max_logical_peak_bytes=max_logical_peak_bytes,
        )
    except (TypeError, ValueError, RuntimeError) as error:
        raise NativeOrganismBinaryStoreError(
            "native organism exact binary restore was refused"
        ) from error
    before = _observe(organism)
    saved = organism.save()
    after = _observe(organism)
    if before != after:
        raise NativeOrganismBinaryStoreError(
            "native organism readiness changed while proving restored state"
        )
    if (
        before.identity != expected_identity
        or before.state_bytes != expected_bytes
        or before.state_sha256 != expected_sha256
        or not isinstance(saved, bytes)
        or saved != body
        or len(saved) != expected_bytes
        or hashlib.sha256(saved).hexdigest() != expected_sha256
    ):
        raise NativeOrganismBinaryStoreError(
            "native organism restored body, identity, readiness, or save differs"
        )
    if expected_tick is not None and before.organism_tick != _nonnegative_integer(
        expected_tick, "expected organism tick"
    ):
        raise NativeOrganismBinaryStoreError(
            "native organism restored tick differs from CURRENT"
        )
    return organism, before


def stage_active_native_organism(
    store_root: str | os.PathLike[str],
    organism: NativeResidentOrganism,
    *,
    max_envelope_bytes: int,
    failure_injector: FailureInjector | None = None,
) -> StagedNativeOrganism:
    """Durably stage the exact save of one active native organism."""

    root = _store_root(store_root)
    maximum = _positive_integer(max_envelope_bytes, "envelope admission")
    before = _observe(organism)
    state = organism.save()
    after = _observe(organism)
    if before != after:
        raise NativeOrganismBinaryStoreError(
            "native organism active state changed during persistence"
        )
    if (
        not isinstance(state, bytes)
        or not state.startswith(STATE_MAGIC)
        or len(state) > maximum
        or len(state) != before.state_bytes
        or hashlib.sha256(state).hexdigest() != before.state_sha256
    ):
        raise NativeOrganismBinaryStoreError(
            "native organism active save is not exact GLORUN"
        )
    stored = _encode_stored_state(state)
    stored_sha256 = hashlib.sha256(stored).hexdigest()
    stage = root / f".stage-{uuid.uuid4()}{STATE_SUFFIX}"
    descriptor = os.open(
        stage,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        _write_all(descriptor, stored)
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
    del state, stored
    _sync_directory(root)
    staged = StagedNativeOrganism(
        store_root=root,
        path=stage,
        identity=before.identity,
        organism_tick=before.organism_tick,
        state_bytes=before.state_bytes,
        state_sha256=before.state_sha256,
        stored_bytes=stage.stat().st_size,
        stored_sha256=stored_sha256,
    )
    byte_count, receipt = _file_receipt(stage)
    if byte_count != staged.stored_bytes or receipt != staged.stored_sha256:
        discard_staged_native_organism(staged)
        raise NativeOrganismBinaryStoreError(
            "native organism durable stage read-back changed"
        )
    try:
        _read_exact_state(
            stage,
            expected_bytes=staged.state_bytes,
            expected_sha256=staged.state_sha256,
            max_envelope_bytes=maximum,
        )
    except BaseException:
        discard_staged_native_organism(staged)
        raise
    try:
        _fault(failure_injector, "after_stage_fsync")
    except BaseException:
        discard_staged_native_organism(staged)
        raise
    return staged


def discard_staged_native_organism(staged: StagedNativeOrganism) -> None:
    """Remove exactly one private stage and no neighboring artifact."""

    if not isinstance(staged, StagedNativeOrganism):
        raise TypeError("staged native organism descriptor is required")
    root = staged.store_root.resolve()
    path = staged.path.resolve()
    if (
        path.parent != root
        or not path.name.startswith(".stage-")
        or not path.name.endswith(STATE_SUFFIX)
    ):
        raise NativeOrganismBinaryStoreError(
            "native organism stage path escaped its exact store root"
        )
    try:
        information = path.lstat()
    except FileNotFoundError:
        return
    if path.is_symlink() or not stat.S_ISREG(information.st_mode):
        raise NativeOrganismBinaryStoreError(
            "native organism stage is not a removable regular file"
        )
    path.unlink()
    _sync_directory(root)


def _verify_remote(
    object_store: StreamingObjectStore,
    key: str,
    expected_bytes: int,
    expected_sha256: str,
) -> None:
    digest = hashlib.sha256()
    byte_count = 0
    for block in object_store.iter_bytes(key):
        if not isinstance(block, bytes) or not block:
            raise NativeOrganismBinaryStoreError(
                "native organism remote stream returned an invalid block"
            )
        digest.update(block)
        byte_count += len(block)
        if byte_count > expected_bytes:
            raise NativeOrganismBinaryStoreError(
                "native organism remote stream exceeded expected bytes"
            )
    if byte_count != expected_bytes or digest.hexdigest() != expected_sha256:
        raise NativeOrganismBinaryStoreError(
            "native organism remote read-back changed"
        )


def restore_current_native_organism(
    store_root: str | os.PathLike[str],
    *,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> RestoredNativeOrganism:
    """Cold restore only CURRENT; never select a predecessor automatically."""

    root = _store_root(store_root)
    pointer = _read_current(root)
    if pointer is None:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT is absent"
        )
    body = _read_exact_state(
        _generation_path(root, pointer.state_sha256),
        expected_bytes=pointer.state_bytes,
        expected_sha256=pointer.state_sha256,
        max_envelope_bytes=max_envelope_bytes,
    )
    organism, _facts = _prove_restored_body(
        body,
        expected_identity=pointer.identity,
        expected_bytes=pointer.state_bytes,
        expected_sha256=pointer.state_sha256,
        expected_tick=pointer.organism_tick,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )
    return RestoredNativeOrganism(organism=organism, pointer=pointer)


def _atomic_replace_current(root: Path, pointer: NativeOrganismPointer) -> None:
    stage = root / f".CURRENT-{uuid.uuid4()}.stage"
    body = _encode_pointer(pointer)
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
    os.replace(stage, root / CURRENT_NAME)
    os.chmod(root / CURRENT_NAME, 0o444)
    _sync_directory(root)


def _body_accounting(
    root: Path,
    current: NativeOrganismPointer | None,
    staged_bytes: int,
    *,
    max_envelope_bytes: int,
) -> NativeOrganismBodyAccounting:
    maximum = _positive_integer(max_envelope_bytes, "envelope admission")
    expected_generations: set[str] = set()
    current_bytes = 0
    if current is not None:
        current_path = _generation_path(root, current.state_sha256)
        current_raw_bytes = _stored_state_raw_bytes(
            current_path, current.state_sha256
        )
        if current_raw_bytes != current.state_bytes or current_raw_bytes > maximum:
            raise NativeOrganismBinaryStoreError(
                "native organism current raw byte count changed"
            )
        current_bytes = _regular_file(current_path, "current generation").st_size
        expected_generations.add(current.state_sha256)
    predecessor_bytes = 0
    if current is not None and current.predecessor_state_sha256 is not None:
        predecessor_path = _generation_path(
            root, current.predecessor_state_sha256
        )
        predecessor_bytes = _regular_file(
            predecessor_path, "retained predecessor"
        ).st_size
        predecessor_raw_bytes = _stored_state_raw_bytes(
            predecessor_path,
            current.predecessor_state_sha256,
        )
        if predecessor_raw_bytes > maximum:
            raise NativeOrganismBinaryStoreError(
                "native organism predecessor exceeds envelope admission"
            )
        expected_generations.add(current.predecessor_state_sha256)
    observed_generations: set[str] = set()
    for path in (root / GENERATIONS_DIRECTORY).iterdir():
        if not path.name.endswith(STATE_SUFFIX):
            raise NativeOrganismBinaryStoreError(
                "native organism generations contain an unknown artifact"
            )
        digest = path.name[: -len(STATE_SUFFIX)]
        _canonical_digest(digest, "generation filename")
        _regular_file(path, "generation body")
        observed_generations.add(digest)
    if observed_generations != expected_generations:
        raise NativeOrganismBinaryStoreError(
            "native organism retained generations exceed current and predecessor"
        )
    staged_count = _positive_integer(staged_bytes, "staged byte count")
    return NativeOrganismBodyAccounting(
        current_bytes=current_bytes,
        retained_predecessor_bytes=predecessor_bytes,
        staged_bytes=staged_count,
        exact_peak_bytes=current_bytes + predecessor_bytes + staged_count,
    )


def _retire_unreferenced_predecessor(
    root: Path,
    prior: NativeOrganismPointer | None,
    successor: NativeOrganismPointer,
    accounting: NativeOrganismBodyAccounting,
    object_store: StreamingObjectStore,
    *,
    max_envelope_bytes: int,
) -> None:
    if prior is None or prior.predecessor_state_sha256 is None:
        return
    retired_sha256 = prior.predecessor_state_sha256
    if retired_sha256 in {
        successor.state_sha256,
        successor.predecessor_state_sha256,
    }:
        return
    retired_path = _generation_path(root, retired_sha256)
    retired_raw_bytes = _stored_state_raw_bytes(retired_path, retired_sha256)
    if retired_raw_bytes > _positive_integer(
        max_envelope_bytes, "envelope admission"
    ):
        raise NativeOrganismBinaryStoreError(
            "native organism retired predecessor exceeds envelope admission"
        )
    retired_stored_bytes, retired_stored_sha256 = _file_receipt(retired_path)
    if retired_stored_bytes != accounting.retained_predecessor_bytes:
        raise NativeOrganismBinaryStoreError(
            "native organism retained predecessor accounting changed"
        )
    object_store.delete_if_exact(
        _remote_key(retired_sha256),
        byte_count=retired_stored_bytes,
        sha256=retired_stored_sha256,
    )
    retired_path.unlink()
    _sync_directory(retired_path.parent)


def publish_staged_native_organism(
    staged: StagedNativeOrganism,
    *,
    expected_predecessor_sha256: str | None,
    object_store: StreamingObjectStore,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
    failure_injector: FailureInjector | None = None,
) -> PublishedNativeOrganism:
    """Publish one staged body and atomically advance binary CURRENT."""

    if not isinstance(staged, StagedNativeOrganism):
        raise TypeError("staged native organism descriptor is required")
    root = _store_root(staged.store_root)
    if staged.path.resolve().parent != root:
        raise NativeOrganismBinaryStoreError(
            "native organism stage escaped its store"
        )
    current = _read_current(root)
    if expected_predecessor_sha256 is None:
        if current is not None:
            raise NativeOrganismBinaryStoreError(
                "native organism initial publication found CURRENT"
            )
    else:
        expected_predecessor_sha256 = _canonical_digest(
            expected_predecessor_sha256,
            "expected predecessor receipt",
        )
        if current is None or current.state_sha256 != expected_predecessor_sha256:
            raise NativeOrganismBinaryStoreError(
                "native organism CURRENT differs from expected predecessor"
            )
        if current.identity != staged.identity:
            raise NativeOrganismBinaryStoreError(
                "native organism staged identity differs from CURRENT"
            )
    accounting = _body_accounting(
        root,
        current,
        staged.stored_bytes,
        max_envelope_bytes=max_envelope_bytes,
    )
    # These are cold-restore budgets, not ordinary-publication work. Validate
    # their type now; the deployment rehearsal and actual startup exercise
    # them against the reconstructed canonical body.
    _positive_integer(max_fabric_bytes, "fabric admission")
    _positive_integer(max_logical_peak_bytes, "logical peak admission")
    generation: Path | None = None
    generation_existed = False
    remote_created = False
    current_replaced = False
    key = _remote_key(staged.state_sha256)
    try:
        staged_bytes, staged_sha256 = _file_receipt(staged.path)
        if (
            staged_bytes != staged.stored_bytes
            or staged_sha256 != staged.stored_sha256
        ):
            raise NativeOrganismBinaryStoreError(
                "native organism durable stage changed before publication"
            )
        _fault(failure_injector, "after_stage_readback")
        pointer = NativeOrganismPointer(
            identity=staged.identity,
            organism_tick=staged.organism_tick,
            state_bytes=staged.state_bytes,
            state_sha256=staged.state_sha256,
            predecessor_state_sha256=(
                None if current is None else current.state_sha256
            ),
        )
        _fault(failure_injector, "after_compact_roundtrip")
        created = object_store.put_if_absent(
            key,
            _stream_file(staged.path),
            byte_count=staged.stored_bytes,
            sha256=staged.stored_sha256,
        )
        if not isinstance(created, bool):
            raise NativeOrganismBinaryStoreError(
                "native organism remote creation result is not boolean"
            )
        remote_created = created
        _fault(failure_injector, "after_object_upload")
        _verify_remote(
            object_store,
            key,
            staged.stored_bytes,
            staged.stored_sha256,
        )
        _fault(failure_injector, "after_object_readback")
        generation = _generation_path(root, staged.state_sha256)
        generation_existed = generation.exists()
        if generation_existed:
            existing_stored_bytes, existing_stored_sha256 = _file_receipt(generation)
            if (
                existing_stored_bytes != staged.stored_bytes
                or existing_stored_sha256 != staged.stored_sha256
            ):
                raise NativeOrganismBinaryStoreError(
                    "native organism generation representation changed"
                )
            discard_staged_native_organism(staged)
        else:
            os.replace(staged.path, generation)
            os.chmod(generation, 0o444)
            _sync_directory(generation.parent)
        _fault(failure_injector, "after_generation_placement")
        if _read_current(root) != current:
            raise NativeOrganismBinaryStoreError(
                "native organism CURRENT changed before atomic publication"
            )
        _fault(failure_injector, "before_current_replace")
        _atomic_replace_current(root, pointer)
        current_replaced = True
        _fault(failure_injector, "after_current_replace")
        if _read_current(root) != pointer:
            raise NativeOrganismBinaryStoreError(
                "native organism CURRENT changed after publication"
            )
        _retire_unreferenced_predecessor(
            root,
            current,
            pointer,
            accounting,
            object_store,
            max_envelope_bytes=max_envelope_bytes,
        )
        return PublishedNativeOrganism(
            pointer=pointer,
            accounting=accounting,
            remote_key=key,
        )
    except BaseException:
        discard_staged_native_organism(staged)
        if not current_replaced:
            if (
                generation is not None
                and not generation_existed
                and generation.exists()
            ):
                existing_bytes, existing_sha256 = _file_receipt(generation)
                if (
                    existing_bytes != staged.stored_bytes
                    or existing_sha256 != staged.stored_sha256
                ):
                    raise NativeOrganismBinaryStoreError(
                        "native organism failed candidate generation changed"
                    )
                generation.unlink()
                _sync_directory(generation.parent)
            if remote_created:
                object_store.delete_if_exact(
                    key,
                    byte_count=staged.stored_bytes,
                    sha256=staged.stored_sha256,
                )
        else:
            _retire_unreferenced_predecessor(
                root,
                current,
                pointer,
                accounting,
                object_store,
                max_envelope_bytes=max_envelope_bytes,
            )
        raise


def rehearse_current_native_organism_exact_energy(
    store_root: str | os.PathLike[str],
    *,
    expected_predecessor_sha256: str,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> RestoredNativeOrganism:
    """Migrate one exact CURRENT body in memory without publishing it."""

    root = _store_root(store_root)
    expected = _canonical_digest(
        expected_predecessor_sha256, "exact-energy predecessor receipt"
    )
    current = _read_current(root)
    if current is None or current.state_sha256 != expected:
        raise NativeOrganismBinaryStoreError(
            "exact-energy migration CURRENT differs from expected predecessor"
        )
    body = _read_exact_state(
        _generation_path(root, current.state_sha256),
        expected_bytes=current.state_bytes,
        expected_sha256=current.state_sha256,
        max_envelope_bytes=max_envelope_bytes,
    )
    migrated = migrate_native_resident_organism_exact_energy(
        current_envelope=body,
        expected_predecessor_sha256=expected,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )
    organism = restore_native_resident_organism(
        current_envelope=migrated,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )
    facts = _observe(organism)
    if facts.identity != current.identity or facts.organism_tick != current.organism_tick:
        raise NativeOrganismBinaryStoreError(
            "exact-energy migration changed identity or organism time"
        )
    pointer = NativeOrganismPointer(
        identity=facts.identity,
        organism_tick=facts.organism_tick,
        state_bytes=facts.state_bytes,
        state_sha256=facts.state_sha256,
        predecessor_state_sha256=current.state_sha256,
    )
    return RestoredNativeOrganism(organism=organism, pointer=pointer)


def migrate_current_native_organism_exact_energy(
    store_root: str | os.PathLike[str],
    *,
    expected_predecessor_sha256: str,
    object_store: StreamingObjectStore,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> PublishedNativeOrganism:
    """Replace exactly one authenticated retired-energy CURRENT body."""

    restored = rehearse_current_native_organism_exact_energy(
        store_root,
        expected_predecessor_sha256=expected_predecessor_sha256,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )
    root = _store_root(store_root)
    staged = stage_active_native_organism(
        root,
        restored.organism,
        max_envelope_bytes=max_envelope_bytes,
    )
    return publish_staged_native_organism(
        staged,
        expected_predecessor_sha256=expected_predecessor_sha256,
        object_store=object_store,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )


def rehearse_current_native_organism_current_format(
    store_root: str | os.PathLike[str],
    *,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> RestoredNativeOrganism:
    """Migrate the exact CURRENT body observed at migration time in memory.

    Continuous life may advance ``CURRENT`` while a release image is built.
    The migration therefore obtains its predecessor from the body itself at
    the instant the migration begins, rather than from deployment metadata.
    The existing exact-predecessor rehearsal remains the sole transition law.
    """

    root = _store_root(store_root)
    current = _read_current(root)
    if current is None:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT is absent"
        )
    return rehearse_current_native_organism_exact_energy(
        root,
        expected_predecessor_sha256=current.state_sha256,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )


def migrate_current_native_organism_current_format(
    store_root: str | os.PathLike[str],
    *,
    object_store: StreamingObjectStore,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> PublishedNativeOrganism:
    """Publish one current-format successor of the exact body now CURRENT.

    Publication still compares ``CURRENT`` with the exact predecessor read by
    the rehearsal. If the living organism advances before publication, the
    existing publication law refuses this successor instead of overwriting
    newer life.
    """

    restored = rehearse_current_native_organism_current_format(
        store_root,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )
    predecessor = restored.pointer.predecessor_state_sha256
    if predecessor is None:
        raise NativeOrganismBinaryStoreError(
            "current-format migration carries no exact predecessor"
        )
    root = _store_root(store_root)
    current = _read_current(root)
    if current is None or current.state_sha256 != predecessor:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT changed during current-format rehearsal"
        )
    if restored.pointer.state_sha256 == current.state_sha256:
        # Already-current is a physical no-op. Publishing the same bytes over
        # themselves would make CURRENT name itself as its predecessor and
        # turn every restart with explicit migration authorization into a
        # false state transition.
        return PublishedNativeOrganism(
            pointer=current,
            accounting=_body_accounting(
                root,
                current,
                _regular_file(
                    _generation_path(root, current.state_sha256),
                    "current generation",
                ).st_size,
                max_envelope_bytes=max_envelope_bytes,
            ),
            remote_key=_remote_key(current.state_sha256),
        )
    staged = stage_active_native_organism(
        root,
        restored.organism,
        max_envelope_bytes=max_envelope_bytes,
    )
    return publish_staged_native_organism(
        staged,
        expected_predecessor_sha256=predecessor,
        object_store=object_store,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )


def rollback_to_verified_predecessor(
    store_root: str | os.PathLike[str],
    *,
    expected_current_sha256: str,
    object_store: StreamingObjectStore,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
    failure_injector: FailureInjector | None = None,
) -> NativeOrganismPointer:
    """Explicitly prove and publish CURRENT's exact predecessor."""

    root = _store_root(store_root)
    expected = _canonical_digest(
        expected_current_sha256, "expected rollback current receipt"
    )
    current = _read_current(root)
    if current is None or current.state_sha256 != expected:
        raise NativeOrganismBinaryStoreError(
            "native organism rollback CURRENT differs"
        )
    predecessor_sha256 = current.predecessor_state_sha256
    if predecessor_sha256 is None:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT has no explicit predecessor"
        )
    predecessor_path = _generation_path(root, predecessor_sha256)
    predecessor_stored_bytes = _regular_file(
        predecessor_path, "rollback predecessor"
    ).st_size
    predecessor_bytes = _stored_state_raw_bytes(
        predecessor_path,
        predecessor_sha256,
    )
    body = _read_exact_state(
        predecessor_path,
        expected_bytes=predecessor_bytes,
        expected_sha256=predecessor_sha256,
        max_envelope_bytes=max_envelope_bytes,
    )
    observed_stored_bytes, observed_stored_sha256 = _file_receipt(predecessor_path)
    if observed_stored_bytes != predecessor_stored_bytes:
        raise NativeOrganismBinaryStoreError(
            "native organism rollback predecessor accounting changed"
        )
    _verify_remote(
        object_store,
        _remote_key(predecessor_sha256),
        predecessor_stored_bytes,
        observed_stored_sha256,
    )
    _organism, facts = _prove_restored_body(
        body,
        expected_identity=current.identity,
        expected_bytes=predecessor_bytes,
        expected_sha256=predecessor_sha256,
        expected_tick=None,
        max_envelope_bytes=max_envelope_bytes,
        max_fabric_bytes=max_fabric_bytes,
        max_logical_peak_bytes=max_logical_peak_bytes,
    )
    rollback = NativeOrganismPointer(
        identity=current.identity,
        organism_tick=facts.organism_tick,
        state_bytes=facts.state_bytes,
        state_sha256=facts.state_sha256,
        predecessor_state_sha256=current.state_sha256,
    )
    _fault(failure_injector, "before_rollback_current_replace")
    if _read_current(root) != current:
        raise NativeOrganismBinaryStoreError(
            "native organism CURRENT changed before rollback"
        )
    _atomic_replace_current(root, rollback)
    _fault(failure_injector, "after_rollback_current_replace")
    if _read_current(root) != rollback:
        raise NativeOrganismBinaryStoreError(
            "native organism rollback CURRENT changed"
        )
    return rollback


__all__ = (
    "CURRENT_NAME",
    "GENERATIONS_DIRECTORY",
    "NativeOrganismBinaryStoreError",
    "NativeOrganismBodyAccounting",
    "NativeOrganismPointer",
    "PublishedNativeOrganism",
    "RestoredNativeOrganism",
    "STATE_MAGIC",
    "StagedNativeOrganism",
    "StreamingObjectStore",
    "discard_staged_native_organism",
    "migrate_current_native_organism_exact_energy",
    "migrate_current_native_organism_current_format",
    "publish_staged_native_organism",
    "rehearse_current_native_organism_exact_energy",
    "rehearse_current_native_organism_current_format",
    "restore_current_native_organism",
    "rollback_to_verified_predecessor",
    "stage_active_native_organism",
)
