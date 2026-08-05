"""Bounded immutable recovery generations for Guala's hot state.

The deployment generation remains the complete, immutable baseline.  A live
recovery generation contains only the engine's declared hot-state files plus
an HMAC-authenticated lineage record naming that exact baseline.  Boot first
materializes the baseline and then applies one fully verified hot overlay
before the engine is allowed to load.

This is persistence, not interpretation: no DSF field is projected, scored,
or otherwise reduced here.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import stat
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from dsf_ai_service.substrate.deployment_generation import (
    MATERIALIZATION_SCHEMA,
    MaterializedGeneration,
    discover_and_load_current,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    CONTENT_CHUNKS_DIRECTORY,
    CURRENT_NAME,
    GENERATIONS_DIRECTORY,
    LOCK_NAME,
    ImmutableGenerationStore,
    LoadedGeneration,
)


LIVE_RECOVERY_LINEAGE_FILE = "LIVE_RECOVERY_LINEAGE.json"
LIVE_RECOVERY_LINEAGE_SCHEMA = "guala_live_recovery_lineage_v1"
LIVE_RECOVERY_HMAC_ALGORITHM = "HMAC-SHA256"


class LiveRecoveryError(RuntimeError):
    """A live recovery generation is absent, invalid, or cannot be committed."""


@dataclass(frozen=True)
class BaselineIdentity:
    generation_uuid: str
    identity: str
    tick: int
    manifest_sha256: str

    @classmethod
    def from_generation(cls, generation) -> "BaselineIdentity":
        return cls(
            generation_uuid=str(generation.generation_uuid),
            identity=str(generation.identity),
            tick=int(generation.tick),
            manifest_sha256=str(generation.manifest_sha256),
        )


def _canonical_json(value) -> bytes:
    try:
        return (json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise LiveRecoveryError(
            f"live recovery value is not deterministic JSON: {error}") from error


def _hmac_key(value) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise LiveRecoveryError("live recovery HMAC key must be bytes")
    key = bytes(value)
    if len(key) < 32:
        raise LiveRecoveryError(
            "live recovery HMAC key must contain at least 32 bytes")
    return key


def _validated_hot_files(files: Sequence[str]) -> tuple[str, ...]:
    if isinstance(files, (str, bytes)):
        raise LiveRecoveryError("hot-state file contract must be a sequence")
    canonical = tuple(sorted(
        _validated_relative_path(item, role="hot-state")
        for item in files
    ))
    if (not canonical or len(canonical) != len(set(canonical))
            or LIVE_RECOVERY_LINEAGE_FILE in canonical):
        raise LiveRecoveryError("hot-state file contract is empty or duplicated")
    return canonical


def _validated_relative_path(value, *, role: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
    ):
        raise LiveRecoveryError(
            f"{role} path is not canonical POSIX syntax")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
        or any(
            part.endswith((
                ".live-recovery.tmp",
                ".live-recovery.prior",
            ))
            for part in path.parts
        )
    ):
        raise LiveRecoveryError(
            f"{role} path is unsafe or noncanonical: {value!r}")
    return value


def _lineage_unsigned(
        baseline: BaselineIdentity, *, live_tick: int,
        hot_files: tuple[str, ...]) -> dict:
    if isinstance(live_tick, bool) or not isinstance(live_tick, int):
        raise LiveRecoveryError("live recovery tick must be an integer")
    if live_tick < baseline.tick:
        raise LiveRecoveryError(
            "live recovery tick cannot precede its deployment baseline")
    return {
        "schema": LIVE_RECOVERY_LINEAGE_SCHEMA,
        "algorithm": LIVE_RECOVERY_HMAC_ALGORITHM,
        "identity": baseline.identity,
        "live_tick": live_tick,
        "hot_files": list(hot_files),
        "baseline_generation_uuid": baseline.generation_uuid,
        "baseline_manifest_sha256": baseline.manifest_sha256,
        "baseline_tick": baseline.tick,
    }


def _signed_lineage(
        baseline: BaselineIdentity, *, live_tick: int,
        hot_files: tuple[str, ...], key: bytes) -> dict:
    unsigned = _lineage_unsigned(
        baseline, live_tick=live_tick, hot_files=hot_files)
    return {
        **unsigned,
        "lineage_hmac_sha256": hmac.new(
            key, _canonical_json(unsigned), hashlib.sha256).hexdigest(),
    }


def _verify_lineage(
        value, *, baseline: BaselineIdentity, generation: LoadedGeneration,
        hot_files: tuple[str, ...], key: bytes) -> None:
    expected_fields = {
        "schema", "algorithm", "identity", "live_tick", "hot_files",
        "baseline_generation_uuid", "baseline_manifest_sha256",
        "baseline_tick", "lineage_hmac_sha256",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise LiveRecoveryError("live recovery lineage field set is invalid")
    supplied_hmac = value.get("lineage_hmac_sha256")
    if (not isinstance(supplied_hmac, str) or len(supplied_hmac) != 64
            or any(character not in "0123456789abcdef"
                   for character in supplied_hmac)):
        raise LiveRecoveryError("live recovery lineage HMAC is invalid")
    unsigned = dict(value)
    del unsigned["lineage_hmac_sha256"]
    expected_hmac = hmac.new(
        key, _canonical_json(unsigned), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_hmac, expected_hmac):
        raise LiveRecoveryError("live recovery lineage HMAC mismatch")
    expected = _lineage_unsigned(
        baseline, live_tick=generation.tick, hot_files=hot_files)
    if unsigned != expected:
        raise LiveRecoveryError(
            "live recovery lineage does not name the active deployment baseline")
    if generation.identity != baseline.identity:
        raise LiveRecoveryError("live recovery identity differs from baseline")


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    written = 0
    while written < len(view):
        count = os.write(fd, view[written:])
        if count <= 0:
            raise OSError("live recovery write made no forward progress")
        written += count


@dataclass(frozen=True)
class _HotTarget:
    relative_path: str
    parent_fd: int
    leaf_name: str
    temporary_name: str
    backup_name: str


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _open_parent_directory(
        root_fd: int, relative_path: str) -> tuple[int, str]:
    parts = PurePosixPath(relative_path).parts
    parent_fd = os.dup(root_fd)
    try:
        for component in parts[:-1]:
            next_fd = os.open(
                component,
                _directory_open_flags(),
                dir_fd=parent_fd,
            )
            os.close(parent_fd)
            parent_fd = next_fd
        info = os.fstat(parent_fd)
        if not stat.S_ISDIR(info.st_mode):
            raise LiveRecoveryError(
                f"baseline hot-state parent is unsafe: {relative_path}")
        return parent_fd, parts[-1]
    except BaseException:
        os.close(parent_fd)
        raise


def _verify_regular_target(
        parent_fd: int, leaf_name: str, relative_path: str) -> None:
    try:
        info = os.stat(
            leaf_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError as error:
        raise LiveRecoveryError(
            f"baseline hot-state target is absent or unsafe: {relative_path}"
        ) from error
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise LiveRecoveryError(
            f"baseline hot-state target is absent or unsafe: {relative_path}")


def _entry_exists(parent_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _unlink_if_present(parent_fd: int, name: str) -> None:
    try:
        info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise LiveRecoveryError(
            f"live recovery transaction entry is unsafe: {name}")
    os.unlink(name, dir_fd=parent_fd)


def _fsync_target_parents(targets: Sequence[_HotTarget]) -> None:
    seen = set()
    for target in targets:
        info = os.fstat(target.parent_fd)
        identity = (info.st_dev, info.st_ino)
        if identity in seen:
            continue
        os.fsync(target.parent_fd)
        seen.add(identity)


class LiveRecoveryGenerationStore:
    """Own the signed hot overlay for one immutable deployment baseline."""

    def __init__(
            self, root, *, baseline, hot_files: Sequence[str], hmac_key,
            keep_generations: int = 3,
            state_file_tick_manifest: str | None = None,
            max_encoded_generation_bytes: int | None = None,
            physical_byte_ceiling: int | None = None,
            physical_byte_scope=None):
        self.root = Path(root)
        self.baseline = BaselineIdentity.from_generation(baseline)
        self.hot_files = _validated_hot_files(hot_files)
        self.hmac_key = _hmac_key(hmac_key)
        if (isinstance(keep_generations, bool)
                or not isinstance(keep_generations, int)
                or keep_generations < 2):
            raise LiveRecoveryError(
                "at least two live recovery generations must be retained")
        self.keep_generations = keep_generations
        if max_encoded_generation_bytes is not None and (
                isinstance(max_encoded_generation_bytes, bool)
                or not isinstance(max_encoded_generation_bytes, int)
                or max_encoded_generation_bytes <= 0):
            raise LiveRecoveryError(
                "live-recovery generation capacity must be a positive integer")
        if (
            physical_byte_ceiling is not None
            and max_encoded_generation_bytes is None
        ):
            raise LiveRecoveryError(
                "bounded live recovery requires an encoded generation capacity")
        self.max_encoded_generation_bytes = max_encoded_generation_bytes
        if state_file_tick_manifest is not None:
            manifest_path = str(state_file_tick_manifest)
            if manifest_path not in self.hot_files:
                raise LiveRecoveryError(
                    "state-file tick manifest must be a declared hot-state file")
            self.state_file_tick_manifest = manifest_path
            self._baseline_state_file_ticks = (
                self._read_state_file_ticks_from_generation(
                    baseline,
                    role="deployment baseline",
                )
            )
        else:
            self.state_file_tick_manifest = None
            self._baseline_state_file_ticks = None
        self.physical_byte_ceiling = physical_byte_ceiling
        self.physical_byte_scope = (
            None if physical_byte_scope is None else Path(physical_byte_scope))

    @property
    def required_files(self) -> tuple[str, ...]:
        return tuple(sorted((*self.hot_files, LIVE_RECOVERY_LINEAGE_FILE)))

    def _store(self) -> ImmutableGenerationStore:
        return ImmutableGenerationStore(
            self.root,
            identity=self.baseline.identity,
            required_files=self.required_files,
            content_addressed=True,
            max_encoded_generation_bytes=self.max_encoded_generation_bytes,
            physical_byte_ceiling=self.physical_byte_ceiling,
            physical_byte_scope=self.physical_byte_scope,
        )

    def physical_byte_status(self) -> dict | None:
        """Return the exact shared-scope status used by hot-state commits."""
        return self._store().physical_byte_status()

    def persistence_status(self) -> dict[str, object]:
        """Expose the exact bounded hot-recovery storage contract."""
        return {
            "schema": "guala.live_recovery_generation.storage.v1",
            "content_addressed": True,
            "retained_generation_capacity": self.keep_generations,
            "generation_capacity_bytes": (
                self.max_encoded_generation_bytes
            ),
            "physical_bytes": (
                self._store().physical_byte_configuration()
            ),
        }

    @staticmethod
    def _state_file_ticks_from_payload(payload, *, role: str) -> dict[str, int]:
        if not isinstance(payload, dict):
            raise LiveRecoveryError(
                f"{role} state-file tick manifest is not a JSON object")
        data = payload.get("data", payload)
        if not isinstance(data, dict):
            raise LiveRecoveryError(
                f"{role} state-file tick manifest data is not an object")
        supplied = data.get("state_file_ticks")
        if not isinstance(supplied, dict) or not supplied:
            raise LiveRecoveryError(
                f"{role} has no authoritative state_file_ticks mapping")
        validated = {}
        for relative, tick in supplied.items():
            try:
                canonical = _validated_relative_path(
                    relative,
                    role=f"{role} state_file_ticks",
                )
            except LiveRecoveryError as error:
                raise LiveRecoveryError(
                    f"{role} state_file_ticks mapping is invalid"
                ) from error
            if (
                isinstance(tick, bool)
                or not isinstance(tick, int)
                or tick < 0
            ):
                raise LiveRecoveryError(
                    f"{role} state_file_ticks mapping is invalid")
            validated[canonical] = tick
        return validated

    def _read_state_file_ticks_from_generation(
            self, generation, *, role: str) -> dict[str, int]:
        try:
            payload = generation.payload(self.state_file_tick_manifest)
        except Exception as error:
            raise LiveRecoveryError(
                f"{role} state-file tick manifest cannot be read: {error}"
            ) from error
        return self._state_file_ticks_from_payload(payload, role=role)

    def _verify_state_file_tick_lineage(
            self, generation: LoadedGeneration) -> None:
        if self.state_file_tick_manifest is None:
            return
        live_ticks = self._read_state_file_ticks_from_generation(
            generation,
            role="live recovery generation",
        )
        self._verify_state_file_ticks(
            live_ticks,
            live_tick=generation.tick,
        )

    def _verify_state_file_ticks(
            self, live_ticks: dict[str, int], *, live_tick: int) -> None:
        baseline_ticks = self._baseline_state_file_ticks
        if set(live_ticks) != set(baseline_ticks):
            raise LiveRecoveryError(
                "live recovery state-file contract differs from its "
                "deployment baseline")
        cold_files = set(baseline_ticks).difference(self.hot_files)
        changed_cold = sorted(
            relative for relative in cold_files
            if live_ticks[relative] != baseline_ticks[relative]
        )
        if changed_cold:
            raise LiveRecoveryError(
                "live recovery references cold state not contained by its "
                "deployment baseline: " + ", ".join(changed_cold)
            )
        invalid_hot = sorted(
            relative for relative in self.hot_files
            if relative not in live_ticks
            or live_ticks[relative] != live_tick
        )
        if invalid_hot:
            raise LiveRecoveryError(
                "live recovery hot-state ticks do not name their immutable "
                "generation: " + ", ".join(invalid_hot)
            )

    def _validated_generation(self, generation: LoadedGeneration) -> LoadedGeneration:
        try:
            lineage = generation.payload(LIVE_RECOVERY_LINEAGE_FILE)
        except Exception as error:
            raise LiveRecoveryError(
                f"live recovery lineage cannot be read: {error}") from error
        _verify_lineage(
            lineage,
            baseline=self.baseline,
            generation=generation,
            hot_files=self.hot_files,
            key=self.hmac_key,
        )
        self._verify_state_file_tick_lineage(generation)
        return generation

    def load_current(self) -> LoadedGeneration | None:
        if not self.root.exists():
            return None
        if self.root.is_symlink() or not self.root.is_dir():
            raise LiveRecoveryError("live recovery root is not a real directory")
        current = self.root / CURRENT_NAME
        if not current.exists():
            entries = {item.name: item for item in self.root.iterdir()}
            allowed = {
                GENERATIONS_DIRECTORY,
                CONTENT_CHUNKS_DIRECTORY,
                LOCK_NAME,
            }
            generation_directory = entries.get(GENERATIONS_DIRECTORY)
            content_chunks_directory = entries.get(
                CONTENT_CHUNKS_DIRECTORY
            )
            lock_file = entries.get(LOCK_NAME)
            generation_directory_is_empty = (
                generation_directory is None
                or (
                    not generation_directory.is_symlink()
                    and generation_directory.is_dir()
                    and not any(generation_directory.iterdir())
                )
            )
            content_chunks_directory_is_empty = (
                content_chunks_directory is None
                or (
                    not content_chunks_directory.is_symlink()
                    and content_chunks_directory.is_dir()
                    and not any(content_chunks_directory.iterdir())
                )
            )
            lock_is_exact = (
                lock_file is None
                or (
                    not lock_file.is_symlink()
                    and lock_file.is_file()
                    and lock_file.stat().st_nlink == 1
                )
            )
            if (
                set(entries).issubset(allowed)
                and generation_directory_is_empty
                and content_chunks_directory_is_empty
                and lock_is_exact
            ):
                return None
            raise LiveRecoveryError(
                "live recovery store exists without an authoritative CURRENT")
        try:
            discovered = discover_and_load_current(self.root)
            generation = discovered.generation
            return self._validated_generation(generation)
        except Exception as error:
            if isinstance(error, LiveRecoveryError):
                raise
            raise LiveRecoveryError(
                f"live recovery CURRENT failed verification: {error}") from error

    def apply_current(
            self, active_directory, *,
            physical_byte_authority=None) -> MaterializedGeneration | None:
        generation = self.load_current()
        if generation is None:
            return None
        active = Path(active_directory)
        if active.is_symlink() or not active.is_dir():
            raise LiveRecoveryError(
                "deployment baseline must be materialized before live recovery")
        root_fd = None
        targets = []
        try:
            try:
                root_fd = os.open(active, _directory_open_flags())
            except OSError as error:
                raise LiveRecoveryError(
                    "deployment baseline must be a real directory"
                ) from error
            if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
                raise LiveRecoveryError(
                    "deployment baseline must be a real directory")
            encoded_payloads = {}
            for relative in self.hot_files:
                try:
                    parent_fd, leaf_name = _open_parent_directory(
                        root_fd,
                        relative,
                    )
                except OSError as error:
                    raise LiveRecoveryError(
                        "baseline hot-state parent is absent or unsafe: "
                        f"{relative}"
                    ) from error
                target = _HotTarget(
                    relative_path=relative,
                    parent_fd=parent_fd,
                    leaf_name=leaf_name,
                    temporary_name=(
                        f".{leaf_name}.live-recovery.tmp"
                    ),
                    backup_name=(
                        f".{leaf_name}.live-recovery.prior"
                    ),
                )
                targets.append(target)
                payload = generation.payload(relative)
                stored = generation.stored_bytes(relative)
                if relative.endswith(".json"):
                    if not isinstance(payload, dict):
                        raise LiveRecoveryError(
                            "live recovery JSON payload is not an object: "
                            f"{relative}"
                        )
                    encoded_payloads[relative] = stored
                elif isinstance(payload, bytes):
                    if payload != stored:
                        raise LiveRecoveryError(
                            "live recovery binary payload differs from its "
                            f"stored bytes: {relative}"
                        )
                    encoded_payloads[relative] = stored
                else:
                    raise LiveRecoveryError(
                        "live recovery non-JSON payload is not bytes: "
                        f"{relative}"
                    )
            self._apply_payloads_transactionally(
                targets,
                encoded_payloads,
                physical_byte_authority,
            )
        finally:
            for target in targets:
                os.close(target.parent_fd)
            if root_fd is not None:
                os.close(root_fd)
        return MaterializedGeneration(
            schema=MATERIALIZATION_SCHEMA,
            generation_uuid=generation.generation_uuid,
            identity=generation.identity,
            tick=generation.tick,
            manifest_sha256=generation.manifest_sha256,
            active_directory=active,
            materialized_files=self.hot_files,
        )

    @staticmethod
    def _recover_interrupted_transaction(
            targets: Sequence[_HotTarget]) -> None:
        recovered = False
        for target in reversed(tuple(targets)):
            if _entry_exists(target.parent_fd, target.backup_name):
                backup_info = os.stat(
                    target.backup_name,
                    dir_fd=target.parent_fd,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISREG(backup_info.st_mode)
                    or backup_info.st_nlink != 1
                ):
                    raise LiveRecoveryError(
                        "live recovery prior-state entry is unsafe: "
                        f"{target.relative_path}"
                    )
                _unlink_if_present(
                    target.parent_fd,
                    target.leaf_name,
                )
                os.rename(
                    target.backup_name,
                    target.leaf_name,
                    src_dir_fd=target.parent_fd,
                    dst_dir_fd=target.parent_fd,
                )
                recovered = True
            if _entry_exists(target.parent_fd, target.temporary_name):
                _unlink_if_present(
                    target.parent_fd,
                    target.temporary_name,
                )
                recovered = True
        if recovered:
            _fsync_target_parents(targets)

    @staticmethod
    def _apply_payloads_transactionally(
            targets: Sequence[_HotTarget],
            encoded_payloads: Mapping[str, bytes],
            physical_byte_authority) -> None:
        requested_bytes = sum(
            len(encoded) for encoded in encoded_payloads.values())
        authority = (
            nullcontext()
            if physical_byte_authority is None
            else physical_byte_authority.admitted_mutation(
                operation="apply_live_recovery_generation",
                requested_bytes=requested_bytes,
            )
        )
        ordered = tuple(sorted(
            targets,
            key=lambda item: item.relative_path,
        ))
        LiveRecoveryGenerationStore._recover_interrupted_transaction(ordered)
        for target in ordered:
            _verify_regular_target(
                target.parent_fd,
                target.leaf_name,
                target.relative_path,
            )
        backed_up = []
        with authority:
            try:
                for target in ordered:
                    if (
                        _entry_exists(
                            target.parent_fd,
                            target.temporary_name,
                        )
                        or _entry_exists(
                            target.parent_fd,
                            target.backup_name,
                        )
                    ):
                        raise LiveRecoveryError(
                            "live recovery transaction name collision")
                    descriptor = os.open(
                        target.temporary_name,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | getattr(os, "O_CLOEXEC", 0)
                        | getattr(os, "O_NOFOLLOW", 0),
                        0o600,
                        dir_fd=target.parent_fd,
                    )
                    try:
                        _write_all(
                            descriptor,
                            encoded_payloads[target.relative_path],
                        )
                        os.fchmod(descriptor, 0o644)
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
                _fsync_target_parents(ordered)
                for target in ordered:
                    _verify_regular_target(
                        target.parent_fd,
                        target.leaf_name,
                        target.relative_path,
                    )
                    os.rename(
                        target.leaf_name,
                        target.backup_name,
                        src_dir_fd=target.parent_fd,
                        dst_dir_fd=target.parent_fd,
                    )
                    backed_up.append(target)
                    os.rename(
                        target.temporary_name,
                        target.leaf_name,
                        src_dir_fd=target.parent_fd,
                        dst_dir_fd=target.parent_fd,
                    )
                _fsync_target_parents(ordered)
            except BaseException as activation_error:
                rollback_error = None
                for target in reversed(backed_up):
                    try:
                        _unlink_if_present(
                            target.parent_fd,
                            target.leaf_name,
                        )
                        if not _entry_exists(
                            target.parent_fd,
                            target.backup_name,
                        ):
                            raise LiveRecoveryError(
                                "live recovery rollback backup is absent: "
                                f"{target.relative_path}"
                            )
                        os.rename(
                            target.backup_name,
                            target.leaf_name,
                            src_dir_fd=target.parent_fd,
                            dst_dir_fd=target.parent_fd,
                        )
                    except BaseException as error:
                        if rollback_error is None:
                            rollback_error = error
                try:
                    _fsync_target_parents(ordered)
                except BaseException as error:
                    if rollback_error is None:
                        rollback_error = error
                if rollback_error is not None:
                    raise LiveRecoveryError(
                        "live recovery activation failed and prior hot state "
                        "could not be fully restored"
                    ) from rollback_error
                raise activation_error
            else:
                for target in backed_up:
                    _unlink_if_present(
                        target.parent_fd,
                        target.backup_name,
                    )
                _fsync_target_parents(ordered)
            finally:
                for target in ordered:
                    _unlink_if_present(
                        target.parent_fd,
                        target.temporary_name,
                    )
                _fsync_target_parents(ordered)

    def _prune_after_commit(
            self, store: ImmutableGenerationStore,
            current: LoadedGeneration) -> None:
        store.prune_generations(
            retain=self.keep_generations,
            verified_current=current,
        )

    def commit_hot_state(
            self, *, tick: int, files: Mapping[str, object]) -> LoadedGeneration:
        supplied = {str(path): source for path, source in files.items()}
        if set(supplied) != set(self.hot_files):
            raise LiveRecoveryError(
                "live recovery commit does not match the hot-state contract")
        for relative, source in supplied.items():
            path = Path(source)
            if path.is_symlink() or not path.is_file():
                raise LiveRecoveryError(
                    f"hot-state source is absent or unsafe: {relative}")
        store = self._store()
        lineage = _signed_lineage(
            self.baseline,
            live_tick=tick,
            hot_files=self.hot_files,
            key=self.hmac_key,
        )
        with store.exclusive_transaction():
            candidate = store.commit(
                tick=tick,
                files={
                    **supplied,
                    LIVE_RECOVERY_LINEAGE_FILE: _canonical_json(lineage),
                },
                publish_current=False,
            )
            published = None
            try:
                self._validated_generation(candidate)
                published = store.publish(candidate)
                self._prune_after_commit(store, published)
                return published
            except BaseException:
                if published is None:
                    store.discard_unpublished(candidate)
                raise

    def rebase_after_deployment_seal(
            self, *, baseline, tick: int,
            files: Mapping[str, object]) -> LoadedGeneration:
        """Advance CURRENT to a newly sealed full baseline without a gap.

        The old CURRENT is verified first and remains authoritative until the
        newly signed generation has been completely committed.  The new full
        deployment baseline already contains these same hot files; retaining
        them as an overlay makes the first post-deploy boot contract explicit.
        """
        self.load_current()
        replacement = LiveRecoveryGenerationStore(
            self.root,
            baseline=baseline,
            hot_files=self.hot_files,
            hmac_key=self.hmac_key,
            keep_generations=self.keep_generations,
            state_file_tick_manifest=self.state_file_tick_manifest,
            max_encoded_generation_bytes=self.max_encoded_generation_bytes,
            physical_byte_ceiling=self.physical_byte_ceiling,
            physical_byte_scope=self.physical_byte_scope,
        )
        if replacement.baseline.identity != self.baseline.identity:
            raise LiveRecoveryError(
                "a deployment seal cannot change live recovery identity")
        supplied = {str(path): source for path, source in files.items()}
        if set(supplied) != set(self.hot_files):
            raise LiveRecoveryError(
                "deployment rebase does not match the hot-state contract")
        lineage = _signed_lineage(
            replacement.baseline,
            live_tick=tick,
            hot_files=replacement.hot_files,
            key=replacement.hmac_key,
        )
        replacement_store = replacement._store()
        with replacement_store.exclusive_transaction():
            candidate = replacement_store.commit(
                tick=tick,
                files={
                    **supplied,
                    LIVE_RECOVERY_LINEAGE_FILE: _canonical_json(lineage),
                },
                publish_current=False,
            )
            published = None
            try:
                replacement._validated_generation(candidate)
                published = replacement_store.publish(candidate)
                replacement._prune_after_commit(
                    replacement_store,
                    published,
                )
                validated = published
            except BaseException:
                if published is None:
                    replacement_store.discard_unpublished(candidate)
                raise
        self.baseline = replacement.baseline
        self._baseline_state_file_ticks = (
            replacement._baseline_state_file_ticks
        )
        return validated


def _verified_predecessor_current(
        root: Path, *, baseline, hmac_key: bytes,
        require_redundant: bool) -> LoadedGeneration:
    discovered = discover_and_load_current(root)
    generation = discovered.generation
    try:
        lineage = generation.payload(LIVE_RECOVERY_LINEAGE_FILE)
    except Exception as error:
        raise LiveRecoveryError(
            f"predecessor live recovery lineage cannot be read: {error}"
        ) from error
    if not isinstance(lineage, dict):
        raise LiveRecoveryError(
            "predecessor live recovery lineage is not an object")
    try:
        hot_files = _validated_hot_files(lineage.get("hot_files"))
    except (TypeError, LiveRecoveryError) as error:
        raise LiveRecoveryError(
            "predecessor live recovery hot-file contract is invalid"
        ) from error
    baseline_identity = BaselineIdentity.from_generation(baseline)
    _verify_lineage(
        lineage,
        baseline=baseline_identity,
        generation=generation,
        hot_files=hot_files,
        key=_hmac_key(hmac_key),
    )
    if not set(hot_files).issubset(set(baseline.required_files)):
        raise LiveRecoveryError(
            "predecessor live recovery contains state outside its sealed "
            "baseline")
    if not require_redundant:
        return generation
    if generation.tick != baseline_identity.tick:
        raise LiveRecoveryError(
            "predecessor live recovery is newer than its sealed baseline")
    changed = []
    for relative in hot_files:
        if generation.payload(relative) != baseline.payload(relative):
            changed.append(relative)
    if changed:
        raise LiveRecoveryError(
            "predecessor live recovery differs from its sealed baseline: "
            + ", ".join(changed)
        )
    return generation


def verify_predecessor_current(
        root, *, baseline, hmac_key,
        expected_generation_uuid: str,
        expected_manifest_sha256: str,
        expected_tick: int,
        state_file_tick_manifest: str | None = None) -> LoadedGeneration:
    """Prove one exact signed hot overlay without changing its custody."""
    generation = _verified_predecessor_current(
        Path(root),
        baseline=baseline,
        hmac_key=hmac_key,
        require_redundant=False,
    )
    expected = {
        "generation_uuid": expected_generation_uuid,
        "manifest_sha256": expected_manifest_sha256,
        "tick": expected_tick,
    }
    for field, value in expected.items():
        if getattr(generation, field) != value:
            raise LiveRecoveryError(
                "predecessor differs from expected " + field
            )
    if state_file_tick_manifest is not None:
        lineage = generation.payload(LIVE_RECOVERY_LINEAGE_FILE)
        manager = LiveRecoveryGenerationStore(
            root,
            baseline=baseline,
            hot_files=tuple(lineage["hot_files"]),
            hmac_key=hmac_key,
            state_file_tick_manifest=state_file_tick_manifest,
        )
        fully_validated = manager.load_current()
        if (
            fully_validated is None
            or fully_validated.recovery_certificate_bytes()
            != generation.recovery_certificate_bytes()
        ):
            raise LiveRecoveryError(
                "predecessor state-file lineage changed during verification"
            )
    return generation


def verify_redundant_predecessor_current(
        root, *, baseline, hmac_key,
        expected_generation_uuid: str,
        expected_manifest_sha256: str,
        expected_tick: int,
        state_file_tick_manifest: str | None = None) -> LoadedGeneration:
    """Prove one unchanged hot overlay without modifying its custody.

    This is the read-only handoff boundary for a code-only deployment whose
    living tick did not advance.  The lineage HMAC, baseline identity, hot-file
    set, tick, and every hot payload are verified by
    ``_verified_predecessor_current`` before the caller-provided immutable
    overlay identity is compared.
    """
    generation = _verified_predecessor_current(
        Path(root),
        baseline=baseline,
        hmac_key=hmac_key,
        require_redundant=True,
    )
    expected = {
        "generation_uuid": expected_generation_uuid,
        "manifest_sha256": expected_manifest_sha256,
        "tick": expected_tick,
    }
    for field, value in expected.items():
        if getattr(generation, field) != value:
            raise LiveRecoveryError(
                "redundant predecessor differs from expected "
                + field
            )
    if state_file_tick_manifest is not None:
        lineage = generation.payload(LIVE_RECOVERY_LINEAGE_FILE)
        manager = LiveRecoveryGenerationStore(
            root,
            baseline=baseline,
            hot_files=tuple(lineage["hot_files"]),
            hmac_key=hmac_key,
            state_file_tick_manifest=state_file_tick_manifest,
        )
        fully_validated = manager.load_current()
        if (
            fully_validated is None
            or fully_validated.recovery_certificate_bytes()
            != generation.recovery_certificate_bytes()
        ):
            raise LiveRecoveryError(
                "redundant predecessor state-file lineage changed during "
                "verification"
            )
    return generation


def retire_redundant_predecessor_current(
        root, *, baseline, hmac_key,
        physical_byte_authority) -> tuple[str, ...]:
    """Retire only HMAC-proven overlays already contained by the baseline.

    This is the one-way bridge from a predecessor hot-file contract to a new
    contract.  It never projects, merges, or guesses state.  Every retired
    overlay must name the exact active baseline, have the same tick, contain
    only baseline paths, and carry values exactly equal to that baseline.
    """
    if physical_byte_authority is None:
        raise LiveRecoveryError(
            "predecessor retirement requires a physical-byte authority")
    root = Path(root)
    parent = root.parent
    parent.mkdir(parents=True, exist_ok=True)
    retired = []
    with physical_byte_authority.exclusive_writer():
        stale = tuple(sorted(
            parent.glob(f".{root.name}.redundant-*")
        ))
        candidates = (*stale, *((root,) if root.exists() else ()))
        for candidate in candidates:
            if candidate.is_symlink() or not candidate.is_dir():
                raise LiveRecoveryError(
                    "predecessor live recovery path is not a real directory")
            generation = _verified_predecessor_current(
                candidate,
                baseline=baseline,
                hmac_key=hmac_key,
                require_redundant=True,
            )
            retirement = candidate
            if candidate == root:
                retirement = parent / (
                    f".{root.name}.redundant-{generation.generation_uuid}"
                )
                if retirement.exists():
                    raise LiveRecoveryError(
                        "predecessor live recovery retirement path exists")
                os.rename(candidate, retirement)
                parent_fd = os.open(
                    parent,
                    os.O_RDONLY
                    | os.O_DIRECTORY
                    | getattr(os, "O_CLOEXEC", 0),
                )
                try:
                    os.fsync(parent_fd)
                finally:
                    os.close(parent_fd)
            shutil.rmtree(retirement)
            parent_fd = os.open(
                parent,
                os.O_RDONLY
                | os.O_DIRECTORY
                | getattr(os, "O_CLOEXEC", 0),
            )
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
            retired.append(generation.generation_uuid)
    return tuple(retired)


__all__ = [
    "BaselineIdentity",
    "LIVE_RECOVERY_LINEAGE_FILE",
    "LIVE_RECOVERY_LINEAGE_SCHEMA",
    "LiveRecoveryError",
    "LiveRecoveryGenerationStore",
    "retire_redundant_predecessor_current",
    "verify_predecessor_current",
    "verify_redundant_predecessor_current",
]
