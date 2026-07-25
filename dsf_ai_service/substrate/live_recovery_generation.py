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
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from dsf_ai_service.substrate.deployment_generation import (
    MATERIALIZATION_SCHEMA,
    MaterializedGeneration,
    discover_and_load_current,
)
from dsf_ai_service.substrate.immutable_generation_store import (
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
    canonical = tuple(sorted(str(item) for item in files))
    if (not canonical or len(canonical) != len(set(canonical))
            or LIVE_RECOVERY_LINEAGE_FILE in canonical):
        raise LiveRecoveryError("hot-state file contract is empty or duplicated")
    for relative in canonical:
        path = Path(relative)
        if (path.is_absolute() or path.as_posix() != relative
                or len(path.parts) != 1 or not relative.endswith(".json")):
            raise LiveRecoveryError(
                f"hot-state path is not a top-level JSON file: {relative!r}")
    return canonical


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


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_replace(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.live-recovery-{uuid.uuid4()}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        written = 0
        while written < len(view):
            count = os.write(fd, view[written:])
            if count <= 0:
                raise OSError("live recovery write made no forward progress")
            written += count
        os.fchmod(fd, 0o644)
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()
            _fsync_directory(path.parent)


def _remove_generation_directory(path: Path) -> None:
    """Remove only one verified, non-CURRENT UUID generation directory."""
    for current_root, directory_names, _file_names in os.walk(
            path, topdown=False, followlinks=False):
        current = Path(current_root)
        if current.is_symlink() or not current.is_dir():
            raise LiveRecoveryError(
                f"refusing to prune unsafe recovery directory {current}")
        for name in directory_names:
            child = current / name
            if child.is_symlink():
                raise LiveRecoveryError(
                    f"refusing to prune recovery symlink {child}")
            os.chmod(child, 0o700)
        os.chmod(current, 0o700)
    shutil.rmtree(path)


class LiveRecoveryGenerationStore:
    """Own the signed hot overlay for one immutable deployment baseline."""

    def __init__(
            self, root, *, baseline, hot_files: Sequence[str], hmac_key,
            keep_generations: int = 3):
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

    @property
    def required_files(self) -> tuple[str, ...]:
        return tuple(sorted((*self.hot_files, LIVE_RECOVERY_LINEAGE_FILE)))

    def _store(self) -> ImmutableGenerationStore:
        return ImmutableGenerationStore(
            self.root,
            identity=self.baseline.identity,
            required_files=self.required_files,
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
        return generation

    def load_current(self) -> LoadedGeneration | None:
        if not self.root.exists():
            return None
        if self.root.is_symlink() or not self.root.is_dir():
            raise LiveRecoveryError("live recovery root is not a real directory")
        current = self.root / CURRENT_NAME
        if not current.exists():
            entries = {item.name: item for item in self.root.iterdir()}
            allowed = {GENERATIONS_DIRECTORY, LOCK_NAME}
            generation_directory = entries.get(GENERATIONS_DIRECTORY)
            if (set(entries).issubset(allowed)
                    and (generation_directory is None
                         or (generation_directory.is_dir()
                             and not any(generation_directory.iterdir())))):
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

    def apply_current(self, active_directory) -> MaterializedGeneration | None:
        generation = self.load_current()
        if generation is None:
            return None
        active = Path(active_directory)
        if active.is_symlink() or not active.is_dir():
            raise LiveRecoveryError(
                "deployment baseline must be materialized before live recovery")
        for relative in self.hot_files:
            target = active / relative
            if target.is_symlink() or not target.is_file():
                raise LiveRecoveryError(
                    f"baseline hot-state target is absent or unsafe: {relative}")
            payload = generation.payload(relative)
            if not isinstance(payload, dict):
                raise LiveRecoveryError(
                    f"live recovery JSON payload is not an object: {relative}")
            _atomic_replace(target, _canonical_json(payload))
        return MaterializedGeneration(
            schema=MATERIALIZATION_SCHEMA,
            generation_uuid=generation.generation_uuid,
            identity=generation.identity,
            tick=generation.tick,
            manifest_sha256=generation.manifest_sha256,
            active_directory=active,
            materialized_files=self.hot_files,
        )

    def _prune_before_commit(self, store: ImmutableGenerationStore) -> None:
        generations = self.root / GENERATIONS_DIRECTORY
        if not generations.exists():
            return
        current = self.load_current()
        current_uuid = current.generation_uuid if current is not None else None
        verified = []
        for path in generations.iterdir():
            if path.name.startswith(".building-"):
                raise LiveRecoveryError(
                    "unfinished live recovery generation requires inspection")
            try:
                canonical = str(uuid.UUID(path.name))
            except (ValueError, AttributeError) as error:
                raise LiveRecoveryError(
                    f"unexpected live recovery generation path {path.name!r}") from error
            if canonical != path.name:
                raise LiveRecoveryError(
                    f"noncanonical live recovery generation path {path.name!r}")
            loaded = store.verify_generation(path.name)
            verified.append(loaded)
        verified.sort(key=lambda item: (item.tick, item.generation_uuid))
        target_count = self.keep_generations - 1
        removable = [item for item in verified
                     if item.generation_uuid != current_uuid]
        while len(verified) > target_count and removable:
            victim = removable.pop(0)
            _remove_generation_directory(victim.directory)
            verified = [item for item in verified
                        if item.generation_uuid != victim.generation_uuid]
            _fsync_directory(generations)

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
        self._prune_before_commit(store)
        lineage = _signed_lineage(
            self.baseline,
            live_tick=int(tick),
            hot_files=self.hot_files,
            key=self.hmac_key,
        )
        committed = store.commit(
            tick=int(tick),
            files={
                **supplied,
                LIVE_RECOVERY_LINEAGE_FILE: _canonical_json(lineage),
            },
        )
        return self._validated_generation(committed)

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
            live_tick=int(tick),
            hot_files=replacement.hot_files,
            key=replacement.hmac_key,
        )
        committed = replacement._store().commit(
            tick=int(tick),
            files={
                **supplied,
                LIVE_RECOVERY_LINEAGE_FILE: _canonical_json(lineage),
            },
        )
        validated = replacement._validated_generation(committed)
        self.baseline = replacement.baseline
        return validated


__all__ = [
    "BaselineIdentity",
    "LIVE_RECOVERY_LINEAGE_FILE",
    "LIVE_RECOVERY_LINEAGE_SCHEMA",
    "LiveRecoveryError",
    "LiveRecoveryGenerationStore",
]
