"""Single-authority bounded persistence for complete Guala generations.

This facade narrows :class:`ImmutableGenerationStore` to the persistence
contract required by the live substrate:

* one CURRENT generation;
* one fully verified predecessor;
* one transient candidate during an atomic commit;
* an exact encoded-byte ceiling for every generation;
* a caller-supplied cold-restore proof before CURRENT can change.

It owns storage mechanics only.  It does not interpret, score, merge, prune,
or otherwise alter cognition or any DSF field.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from dsf_ai_service.substrate.immutable_generation_store import (
    CURRENT_NAME,
    GENERATIONS_DIRECTORY,
    LOCK_NAME,
    MANIFEST_NAME,
    CurrentPointerError,
    GenerationStoreError,
    ImmutableGenerationStore,
    LoadedGeneration,
)


RETAINED_AUTHORITATIVE_GENERATIONS = 2
TRANSIENT_AUTHORITATIVE_GENERATIONS = 3
SEALED_BOOT_MAX_GENERATION_PATHS = (
    TRANSIENT_AUTHORITATIVE_GENERATIONS + 1
)
SEALED_BOOT_MAX_NEVER_PUBLISHED_PATHS = 1


class AuthoritativeColdGenerationError(RuntimeError):
    """The sole cold-generation authority is absent, ambiguous, or unsafe."""


@dataclass(frozen=True)
class EncodedGenerationCensus:
    generation_uuid: str
    tick: int
    state_revision: int
    encoded_bytes: int
    current: bool


@dataclass(frozen=True)
class AuthoritativeColdState:
    current: LoadedGeneration
    predecessor: LoadedGeneration | None
    census: tuple[EncodedGenerationCensus, ...]
    current_authority: Any
    predecessor_authority: Any


class AuthoritativeColdGenerationStore:
    """Commit complete state through one bounded immutable authority."""

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        identity: str,
        required_files: Sequence[str] | None,
        max_encoded_generation_bytes: int,
        pre_publish_validator: Callable[[LoadedGeneration], bool],
        generation_revision: Callable[[LoadedGeneration], Any] | None = None,
        max_dynamic_required_files: int | None = None,
        max_dynamic_path_bytes: int | None = None,
        physical_byte_ceiling: int | None = None,
        physical_byte_scope: str | os.PathLike[str] | None = None,
    ):
        if (
            isinstance(max_encoded_generation_bytes, bool)
            or not isinstance(max_encoded_generation_bytes, int)
            or max_encoded_generation_bytes <= 0
        ):
            raise AuthoritativeColdGenerationError(
                "cold-generation encoded capacity must be a positive integer"
            )
        if not callable(pre_publish_validator):
            raise AuthoritativeColdGenerationError(
                "cold-generation pre-publication validator must be callable"
            )
        if generation_revision is not None and not callable(
                generation_revision):
            raise AuthoritativeColdGenerationError(
                "cold-generation revision authority must be callable")
        self.root = Path(root)
        self.max_encoded_generation_bytes = max_encoded_generation_bytes
        self.max_transient_encoded_bytes = (
            TRANSIENT_AUTHORITATIVE_GENERATIONS
            * max_encoded_generation_bytes
        )
        self._pre_publish_validator = pre_publish_validator
        self._generation_revision = (
            (lambda generation: 0)
            if generation_revision is None
            else generation_revision
        )
        self._store = ImmutableGenerationStore(
            self.root,
            identity=identity,
            required_files=required_files,
            content_addressed=True,
            max_encoded_generation_bytes=max_encoded_generation_bytes,
            max_dynamic_required_files=max_dynamic_required_files,
            max_dynamic_path_bytes=max_dynamic_path_bytes,
            physical_byte_ceiling=physical_byte_ceiling,
            physical_byte_scope=physical_byte_scope,
        )
        self._blocked_reason: str | None = None

    @property
    def blocked_reason(self) -> str | None:
        return self._blocked_reason

    def persistence_status(self) -> dict[str, Any]:
        """Expose the exact bounded production storage contract."""
        physical = self._store.physical_byte_configuration()
        return {
            "schema": "guala.authoritative_cold_generation.storage.v1",
            "content_addressed": self._store.content_addressed,
            "retained_generation_capacity": (
                RETAINED_AUTHORITATIVE_GENERATIONS
            ),
            "transaction_generation_capacity": (
                TRANSIENT_AUTHORITATIVE_GENERATIONS
            ),
            "generation_capacity_bytes": (
                self.max_encoded_generation_bytes
            ),
            "transaction_capacity_bytes": (
                self.max_transient_encoded_bytes
            ),
            "physical_bytes": physical,
        }

    def _block(self, reason: object) -> None:
        self._blocked_reason = str(reason)

    @staticmethod
    def _encoded_bytes(generation: LoadedGeneration) -> int:
        certificate = generation.recovery_certificate()
        return sum(
            int(record["size_bytes"])
            for record in certificate["required_files"]
        ) + (generation.directory / MANIFEST_NAME).stat().st_size

    @staticmethod
    def _authority_key(
        generation: LoadedGeneration,
    ) -> tuple[str, str]:
        return generation.generation_uuid, generation.manifest_sha256

    def _authority(
        self,
        generation: LoadedGeneration,
        authority_cache: dict[tuple[str, str], Any] | None,
    ) -> Any:
        key = self._authority_key(generation)
        if authority_cache is not None and key in authority_cache:
            return authority_cache[key]
        try:
            authority = self._generation_revision(generation)
        except Exception as error:
            raise AuthoritativeColdGenerationError(
                f"cold generation {generation.generation_uuid} has no "
                f"valid revision authority: {error}"
            ) from error
        if authority_cache is not None:
            authority_cache[key] = authority
        return authority

    def _revision(
        self,
        generation: LoadedGeneration,
        authority_cache: dict[tuple[str, str], Any] | None = None,
    ) -> int:
        authority = self._authority(generation, authority_cache)
        if authority is None:
            revision = 0
        elif hasattr(authority, "state_revision"):
            revision = authority.state_revision
        else:
            revision = authority
        if (
            isinstance(revision, bool)
            or not isinstance(revision, int)
            or revision < 0
        ):
            raise AuthoritativeColdGenerationError(
                f"cold generation {generation.generation_uuid} has an "
                "invalid state revision"
            )
        return revision

    def _order_key(
        self,
        generation: LoadedGeneration,
        authority_cache: dict[tuple[str, str], Any] | None = None,
    ) -> tuple[int, int]:
        return generation.tick, self._revision(
            generation,
            authority_cache,
        )

    def _generation_paths(self) -> tuple[Path, ...]:
        directory = self.root / GENERATIONS_DIRECTORY
        if not directory.is_dir():
            raise AuthoritativeColdGenerationError(
                "cold-generation directory is absent"
            )
        paths = []
        for path in directory.iterdir():
            if path.name.startswith(".building-"):
                raise AuthoritativeColdGenerationError(
                    "unfinished cold generation requires inspection"
                )
            try:
                canonical = str(uuid.UUID(path.name))
            except (ValueError, AttributeError) as error:
                raise AuthoritativeColdGenerationError(
                    f"unexpected cold-generation path {path.name!r}"
                ) from error
            if canonical != path.name:
                raise AuthoritativeColdGenerationError(
                    f"noncanonical cold-generation path {path.name!r}"
                )
            paths.append(path)
        return tuple(paths)

    def _assert_bounded_sealed_boot_path_count(self) -> None:
        """Stop at max+1 before sealed-boot verification or retirement.

        With CURRENT, the largest supported crash state is the legacy
        CURRENT plus two predecessors plus one interrupted unpublished
        candidate.  Without CURRENT, single-writer first publication can
        leave only its one unpublished candidate.
        """
        directory = self.root / GENERATIONS_DIRECTORY
        try:
            directory_info = directory.lstat()
        except FileNotFoundError as error:
            raise AuthoritativeColdGenerationError(
                "cold-generation directory is absent"
            ) from error
        if directory.is_symlink() or not stat.S_ISDIR(directory_info.st_mode):
            raise AuthoritativeColdGenerationError(
                "cold-generation directory is not a real directory"
            )
        current_exists = (self.root / CURRENT_NAME).exists()
        maximum = (
            SEALED_BOOT_MAX_GENERATION_PATHS
            if current_exists
            else SEALED_BOOT_MAX_NEVER_PUBLISHED_PATHS
        )
        count = 0
        for _path in directory.iterdir():
            count += 1
            if count > maximum:
                raise AuthoritativeColdGenerationError(
                    "sealed-boot generation path count exceeds bounded "
                    f"recovery capacity {maximum}"
                )

    def _audit(
        self,
        *,
        require_predecessor: bool,
        allow_empty: bool,
        maximum_generations: int = RETAINED_AUTHORITATIVE_GENERATIONS,
        sealed_integrity: bool = False,
        authority_cache: dict[tuple[str, str], Any] | None = None,
    ) -> AuthoritativeColdState | None:
        if authority_cache is None:
            authority_cache = {}
        current_path = self.root / CURRENT_NAME
        paths = self._generation_paths()
        try:
            current_path.lstat()
        except FileNotFoundError:
            if allow_empty and not paths:
                return None
            raise AuthoritativeColdGenerationError(
                "cold-generation store has no authoritative CURRENT"
            )
        try:
            current = (
                self._store.load_sealed_current_integrity()
                if sealed_integrity
                else self._store.load_current()
            )
            verifier = (
                self._store.verify_sealed_generation_integrity
                if sealed_integrity
                else self._store.verify_generation
            )
            verified = tuple(
                (
                    current
                    if path.name == current.generation_uuid
                    else verifier(path.name)
                )
                for path in paths
            )
        except Exception as error:
            raise AuthoritativeColdGenerationError(
                f"cold-generation verification failed: {error}"
            ) from error
        if len(verified) > maximum_generations:
            if maximum_generations == RETAINED_AUTHORITATIVE_GENERATIONS:
                raise AuthoritativeColdGenerationError(
                    "cold-generation authority exceeds CURRENT plus predecessor"
                )
            raise AuthoritativeColdGenerationError(
                "cold-generation authority exceeds verified reconciliation "
                "retention"
            )
        by_uuid = {
            generation.generation_uuid: generation
            for generation in verified
        }
        if len(by_uuid) != len(verified) or current.generation_uuid not in by_uuid:
            raise AuthoritativeColdGenerationError(
                "cold-generation CURRENT is absent or duplicated"
            )
        if require_predecessor and len(verified) < 2:
            raise AuthoritativeColdGenerationError(
                "cold-generation authority has no verified predecessor"
            )

        predecessor_candidates = sorted(
            (
                generation
                for generation in verified
                if generation.generation_uuid != current.generation_uuid
            ),
            key=lambda generation: (
                self._order_key(generation, authority_cache),
                generation.generation_uuid,
            ),
            reverse=True,
        )
        if any(
            self._order_key(generation, authority_cache)
            >= self._order_key(current, authority_cache)
            for generation in predecessor_candidates
        ):
            raise AuthoritativeColdGenerationError(
                "cold-generation predecessor is not strictly older than "
                "CURRENT"
            )
        predecessor = (
            predecessor_candidates[0]
            if predecessor_candidates
            else None
        )
        census = tuple(
            EncodedGenerationCensus(
                generation_uuid=generation.generation_uuid,
                tick=generation.tick,
                state_revision=self._revision(
                    generation,
                    authority_cache,
                ),
                encoded_bytes=self._encoded_bytes(generation),
                current=(
                    generation.generation_uuid
                    == current.generation_uuid
                ),
            )
            for generation in sorted(
                verified,
                key=lambda item: (
                    self._order_key(item, authority_cache),
                    item.generation_uuid,
                ),
                reverse=True,
            )
        )
        for record in census:
            if record.encoded_bytes > self.max_encoded_generation_bytes:
                raise AuthoritativeColdGenerationError(
                    f"cold generation {record.generation_uuid} exceeds "
                    f"encoded capacity: {record.encoded_bytes}>"
                    f"{self.max_encoded_generation_bytes}"
                )
        if (
            sum(record.encoded_bytes for record in census)
            > maximum_generations * self.max_encoded_generation_bytes
        ):
            raise AuthoritativeColdGenerationError(
                "cold-generation census exceeds its exact capacity"
            )
        return AuthoritativeColdState(
            current=current,
            predecessor=predecessor,
            census=census,
            current_authority=self._authority(
                current,
                authority_cache,
            ),
            predecessor_authority=(
                None
                if predecessor is None
                else self._authority(predecessor, authority_cache)
            ),
        )

    def _retire_interrupted_unpublished_candidates(
        self,
        authority_cache: dict[tuple[str, str], Any] | None = None,
    ) -> tuple[str, ...]:
        """Retire verified newer non-CURRENT state left by an abrupt crash."""
        try:
            self._store.discard_orphan_building_directories()
        except Exception as error:
            raise AuthoritativeColdGenerationError(
                f"interrupted-candidate verification failed: {error}"
            ) from error
        current_path = self.root / CURRENT_NAME
        try:
            current_path.lstat()
        except FileNotFoundError:
            paths = self._generation_paths()
            if not paths:
                return ()
            try:
                never_published = tuple(
                    self._store.verify_generation(path.name)
                    for path in paths
                )
            except Exception as error:
                raise AuthoritativeColdGenerationError(
                    f"never-published candidate verification failed: {error}"
                ) from error
            for generation in never_published:
                if (
                    self._encoded_bytes(generation)
                    > self.max_encoded_generation_bytes
                ):
                    raise AuthoritativeColdGenerationError(
                        "never-published cold generation exceeds encoded "
                        "capacity"
                    )
            for generation in never_published:
                self._store.discard_unpublished(generation)
            return tuple(
                generation.generation_uuid
                for generation in never_published
            )

        paths = self._generation_paths()
        try:
            current = self._store.load_current()
            verified = tuple(
                self._store.verify_generation(path.name)
                for path in paths
            )
        except Exception as error:
            raise AuthoritativeColdGenerationError(
                f"interrupted-candidate verification failed: {error}"
            ) from error
        by_uuid = {
            generation.generation_uuid: generation
            for generation in verified
        }
        if len(by_uuid) != len(verified) or current.generation_uuid not in by_uuid:
            raise AuthoritativeColdGenerationError(
                "interrupted-candidate census does not contain unique CURRENT"
            )
        for generation in verified:
            encoded_bytes = self._encoded_bytes(generation)
            if encoded_bytes > self.max_encoded_generation_bytes:
                raise AuthoritativeColdGenerationError(
                    f"interrupted cold generation {generation.generation_uuid} "
                    f"exceeds encoded capacity: {encoded_bytes}>"
                    f"{self.max_encoded_generation_bytes}"
                )
        interrupted = tuple(
            generation
            for generation in verified
            if (
                generation.generation_uuid != current.generation_uuid
                and self._order_key(generation, authority_cache)
                > self._order_key(current, authority_cache)
            )
        )
        for generation in interrupted:
            self._store.discard_unpublished(generation)
        return tuple(
            generation.generation_uuid
            for generation in interrupted
        )

    def inspect(
        self,
        *,
        require_predecessor: bool = True,
    ) -> AuthoritativeColdState:
        if self._blocked_reason is not None:
            raise AuthoritativeColdGenerationError(
                f"cold-generation authority is blocked: "
                f"{self._blocked_reason}"
            )
        with self._store.exclusive_transaction():
            self._retire_interrupted_unpublished_candidates()
            state = self._audit(
                require_predecessor=require_predecessor,
                allow_empty=False,
            )
        if state is None:
            raise AuthoritativeColdGenerationError(
                "cold-generation authority is empty"
            )
        return state

    @contextlib.contextmanager
    def exclusive_read_only_transaction(
        self,
        *,
        require_predecessor: bool = True,
    ):
        """Hold the authority lock across one mutation-free exact audit.

        Unlike ``inspect`` this path never retires interrupted candidates,
        never changes modes, and never removes a building directory.  Any
        residue or ambiguous ordering is a loud failure.
        """
        if self._blocked_reason is not None:
            raise AuthoritativeColdGenerationError(
                f"cold-generation authority is blocked: "
                f"{self._blocked_reason}"
            )
        lock_path = self.root / LOCK_NAME
        # EFS implements flock through NFSv4 whole-file fcntl locking.
        # An exclusive NFS lock requires a write-open descriptor even though
        # this transaction never writes through it. O_CREAT remains absent:
        # the authority lock must already exist and this audit stays
        # mutation-free.
        flags = os.O_RDWR | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags)
        except OSError as error:
            raise AuthoritativeColdGenerationError(
                "cold-generation read-only authority lock is absent or "
                f"unsafe: {error}"
            ) from error
        try:
            lock_info = os.fstat(descriptor)
            if (
                not stat.S_ISREG(lock_info.st_mode)
                or stat.S_IMODE(lock_info.st_mode) != 0o600
                or lock_info.st_nlink != 1
            ):
                raise AuthoritativeColdGenerationError(
                    "cold-generation read-only authority lock is not a "
                    "unique private regular file"
                )
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            state = self._audit(
                require_predecessor=require_predecessor,
                allow_empty=False,
            )
            if state is None:
                raise AuthoritativeColdGenerationError(
                    "cold-generation authority is empty"
                )
            yield state
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def inspect_sealed_boot(
        self,
        *,
        require_predecessor: bool = True,
    ) -> AuthoritativeColdState:
        """Retire verified crash residue, then stream-audit retained seals."""
        if self._blocked_reason is not None:
            raise AuthoritativeColdGenerationError(
                f"cold-generation authority is blocked: "
                f"{self._blocked_reason}"
            )
        with self._store.exclusive_transaction():
            authority_cache: dict[tuple[str, str], Any] = {}
            self._assert_bounded_sealed_boot_path_count()
            # A crash after candidate rename but before CURRENT publication
            # legitimately leaves CURRENT, its predecessor, and one newer
            # verified candidate. Retire only that strictly newer non-CURRENT
            # generation before enforcing the steady-state retain-two census.
            # Older legacy predecessors remain untouched for the separately
            # authenticated retain-three transition.
            self._retire_interrupted_unpublished_candidates(authority_cache)
            state = self._audit(
                require_predecessor=require_predecessor,
                allow_empty=False,
                sealed_integrity=True,
                authority_cache=authority_cache,
            )
        if state is None:
            raise AuthoritativeColdGenerationError(
                "cold-generation authority is empty"
            )
        return state

    def assert_current_reference(
        self,
        expected_current: LoadedGeneration,
    ) -> LoadedGeneration:
        """Prove the published pointer still names the boot-verified CURRENT.

        This constant-size proof is for recurring readiness checks after a
        complete generation has already crossed the cold-store audit and the
        real engine restore.  It never substitutes for those boundary proofs.
        """
        if not isinstance(expected_current, LoadedGeneration):
            raise TypeError("expected_current must be a verified generation")
        if (
            expected_current.identity != self._store.identity
            or expected_current.directory.parent
            != self._store.generations_directory
        ):
            raise AuthoritativeColdGenerationError(
                "readiness CURRENT does not belong to this authority"
            )
        with self._store.exclusive_transaction():
            try:
                pointer, canonical = self._store._read_current()
            except Exception as error:
                raise AuthoritativeColdGenerationError(
                    f"readiness CURRENT cannot be verified: {error}"
                ) from error
            if (
                not canonical
                or pointer["generation_uuid"]
                != expected_current.generation_uuid
                or pointer["identity"] != expected_current.identity
                or pointer["tick"] != expected_current.tick
                or pointer["manifest_sha256"]
                != expected_current.manifest_sha256
            ):
                raise AuthoritativeColdGenerationError(
                    "readiness CURRENT differs from the boot-verified generation"
                )
            try:
                directory_info = expected_current.directory.lstat()
                manifest_info = (
                    expected_current.directory / MANIFEST_NAME
                ).lstat()
            except FileNotFoundError as error:
                raise AuthoritativeColdGenerationError(
                    "readiness CURRENT generation is absent"
                ) from error
            if (
                expected_current.directory.is_symlink()
                or not stat.S_ISDIR(directory_info.st_mode)
                or stat.S_IMODE(directory_info.st_mode) != 0o555
                or not stat.S_ISREG(manifest_info.st_mode)
                or stat.S_IMODE(manifest_info.st_mode) != 0o444
                or manifest_info.st_nlink != 1
            ):
                raise AuthoritativeColdGenerationError(
                    "readiness CURRENT generation lost immutable structure"
                )
        return expected_current

    def inspect_legacy_retention_transition(self) -> AuthoritativeColdState:
        """Audit one exact retain-three predecessor without retiring it.

        This is the read-only half of the one-time transition from the legacy
        deployment writer, which retained three published generations.  It
        deliberately does not call the engine validator and deliberately does
        not remove anything.  Retirement is permitted only after the caller
        has restored the audited CURRENT generation in the real engine and
        supplies that exact restore proof to
        :meth:`complete_legacy_retention_transition`.
        """
        if self._blocked_reason is not None:
            raise AuthoritativeColdGenerationError(
                f"cold-generation authority is blocked: "
                f"{self._blocked_reason}"
            )
        with self._store.exclusive_transaction():
            state = self._audit(
                require_predecessor=True,
                allow_empty=False,
                maximum_generations=TRANSIENT_AUTHORITATIVE_GENERATIONS,
                sealed_integrity=True,
            )
        if state is None or len(state.census) != TRANSIENT_AUTHORITATIVE_GENERATIONS:
            raise AuthoritativeColdGenerationError(
                "legacy cold-generation transition requires exactly "
                "CURRENT plus two predecessors"
            )
        return state

    def complete_legacy_retention_transition(
        self,
        *,
        audited_current: LoadedGeneration,
        restored_identity: str,
        restored_tick: int,
    ) -> AuthoritativeColdState:
        """Retire the oldest legacy generation after one exact CURRENT restore."""
        if not isinstance(audited_current, LoadedGeneration):
            raise TypeError("audited_current must be a verified generation")
        if (
            restored_identity != audited_current.identity
            or isinstance(restored_tick, bool)
            or not isinstance(restored_tick, int)
            or restored_tick != audited_current.tick
        ):
            raise AuthoritativeColdGenerationError(
                "legacy retention transition lacks an exact CURRENT "
                "engine-restore proof"
            )
        try:
            with self._store.exclusive_transaction():
                state = self._audit(
                    require_predecessor=True,
                    allow_empty=False,
                    maximum_generations=TRANSIENT_AUTHORITATIVE_GENERATIONS,
                    sealed_integrity=True,
                )
                if (
                    state is None
                    or len(state.census)
                    != TRANSIENT_AUTHORITATIVE_GENERATIONS
                ):
                    raise AuthoritativeColdGenerationError(
                        "legacy cold-generation transition changed before "
                        "retirement"
                    )
                if (
                    state.current.recovery_certificate_bytes()
                    != audited_current.recovery_certificate_bytes()
                ):
                    raise AuthoritativeColdGenerationError(
                        "legacy cold-generation CURRENT changed after its "
                        "engine restore"
                    )
                removed = self._store.prune_generations(
                    retain=RETAINED_AUTHORITATIVE_GENERATIONS,
                    verified_current=state.current,
                )
                expected_removed = tuple(
                    record.generation_uuid
                    for record in state.census[
                        RETAINED_AUTHORITATIVE_GENERATIONS:
                    ]
                )
                if removed != expected_removed:
                    raise AuthoritativeColdGenerationError(
                        "legacy cold-generation transition retired an "
                        "unexpected generation"
                    )
                transitioned = AuthoritativeColdState(
                    current=state.current,
                    predecessor=state.predecessor,
                    census=state.census[
                        :RETAINED_AUTHORITATIVE_GENERATIONS
                    ],
                    current_authority=state.current_authority,
                    predecessor_authority=state.predecessor_authority,
                )
            self._blocked_reason = None
            return transitioned
        except Exception as error:
            self._block(error)
            if isinstance(error, AuthoritativeColdGenerationError):
                raise
            raise AuthoritativeColdGenerationError(
                f"legacy cold-generation transition failed: {error}"
            ) from error

    def purge_verified_migration_escrow(
        self,
        *,
        verified_current: LoadedGeneration,
        escrow_path_prefix: str,
    ) -> AuthoritativeColdState:
        """Retire the escrow-bearing predecessor after exact cutover proof."""
        if (
            not isinstance(escrow_path_prefix, str)
            or not escrow_path_prefix
            or not escrow_path_prefix.endswith("/")
        ):
            raise AuthoritativeColdGenerationError(
                "migration escrow prefix must be non-empty and end in '/'"
            )
        state = self.inspect(require_predecessor=True)
        if (
            state.current.generation_uuid
            != verified_current.generation_uuid
            or state.current.manifest_sha256
            != verified_current.manifest_sha256
        ):
            raise AuthoritativeColdGenerationError(
                "migration escrow purge proof differs from CURRENT"
            )
        if any(
            path.startswith(escrow_path_prefix)
            for path in state.current.required_files
        ):
            raise AuthoritativeColdGenerationError(
                "CURRENT still references migration escrow"
            )
        predecessor = state.predecessor
        if predecessor is None or not any(
            path.startswith(escrow_path_prefix)
            for path in predecessor.required_files
        ):
            raise AuthoritativeColdGenerationError(
                "predecessor does not contain the verified migration escrow"
            )
        self._store.discard_unpublished(predecessor)
        return self.inspect(require_predecessor=False)

    def _discard_candidate_when_provably_unpublished(
        self,
        candidate: LoadedGeneration,
    ) -> None:
        try:
            current = self._store.load_current()
        except CurrentPointerError:
            current_path = self.root / CURRENT_NAME
            try:
                current_path.lstat()
            except FileNotFoundError:
                self._store.discard_unpublished(candidate)
            return
        if current.generation_uuid != candidate.generation_uuid:
            self._store.discard_unpublished(candidate)

    def _raise_transaction_error(self, error: Exception) -> None:
        if isinstance(error, AuthoritativeColdGenerationError):
            raise error
        if isinstance(error, GenerationStoreError):
            raise AuthoritativeColdGenerationError(
                f"cold-generation commit failed: {error}"
            ) from error
        raise AuthoritativeColdGenerationError(
            f"cold-generation transaction failed: {error}"
        ) from error

    def commit(
        self,
        *,
        tick: int,
        state_revision: int = 0,
        files: Mapping[str, Any],
        generation_uuid: str | None = None,
        pre_publish_action: Callable[[LoadedGeneration], bool] | None = None,
        allow_equal_tick_schema_migration: bool = False,
    ) -> AuthoritativeColdState:
        if self._blocked_reason is not None:
            raise AuthoritativeColdGenerationError(
                f"cold-generation authority is blocked: "
                f"{self._blocked_reason}"
            )
        if pre_publish_action is not None and not callable(pre_publish_action):
            raise AuthoritativeColdGenerationError(
                "cold-generation pre-publication action must be callable"
            )
        if not isinstance(allow_equal_tick_schema_migration, bool):
            raise AuthoritativeColdGenerationError(
                "equal-tick schema-migration authority must be a boolean"
            )
        if (
            isinstance(state_revision, bool)
            or not isinstance(state_revision, int)
            or state_revision < 0
        ):
            raise AuthoritativeColdGenerationError(
                "candidate state revision must be a non-negative integer")
        candidate: LoadedGeneration | None = None
        try:
            with self._store.exclusive_transaction():
                self._retire_interrupted_unpublished_candidates()
                before = self._audit(
                    require_predecessor=False,
                    allow_empty=True,
                )
                if (
                    before is not None
                    and tick == before.current.tick
                    and not allow_equal_tick_schema_migration
                ):
                    raise AuthoritativeColdGenerationError(
                        "equal-tick generation change requires explicit "
                        "schema-migration authority"
                    )
                if (
                    before is not None
                    and (
                        isinstance(tick, bool)
                        or not isinstance(tick, int)
                        or (tick, state_revision)
                        <= self._order_key(before.current)
                    )
                ):
                    raise AuthoritativeColdGenerationError(
                        "candidate (tick, state revision) must be strictly "
                        "newer than CURRENT"
                    )

                candidate = self._store.commit(
                    tick=tick,
                    files=files,
                    generation_uuid=generation_uuid,
                    publish_current=False,
                )
                if self._revision(candidate) != state_revision:
                    raise AuthoritativeColdGenerationError(
                        "candidate receipt state revision differs from its "
                        "commit order authority"
                    )
                candidate_bytes = self._encoded_bytes(candidate)
                retained_bytes = (
                    0
                    if before is None
                    else sum(record.encoded_bytes for record in before.census)
                )
                if (
                    retained_bytes + candidate_bytes
                    > self.max_transient_encoded_bytes
                ):
                    raise AuthoritativeColdGenerationError(
                        "cold-generation candidate exceeds exact transient "
                        "CURRENT plus predecessor plus candidate capacity"
                    )

                validation_result = self._pre_publish_validator(candidate)
                if validation_result is not True:
                    raise AuthoritativeColdGenerationError(
                        "cold-generation candidate failed cold-restore validation"
                    )
                if (
                    pre_publish_action is not None
                    and pre_publish_action(candidate) is not True
                ):
                    raise AuthoritativeColdGenerationError(
                        "cold-generation candidate failed its pre-publication "
                        "action"
                    )

                published = self._store.publish(candidate)
                self._store.prune_generations(
                    retain=RETAINED_AUTHORITATIVE_GENERATIONS,
                    verified_current=published,
                    protected_generation_uuids=(
                        ()
                        if before is None
                        else (before.current.generation_uuid,)
                    ),
                )
                after = self._audit(
                    require_predecessor=before is not None,
                    allow_empty=False,
                )
                if after is None:
                    raise AuthoritativeColdGenerationError(
                        "cold-generation commit produced no CURRENT"
                    )
                return after
        except Exception as error:
            cleanup_error: Exception | None = None
            if candidate is not None:
                try:
                    with self._store.exclusive_transaction():
                        self._discard_candidate_when_provably_unpublished(
                            candidate
                        )
                except Exception as failure:
                    cleanup_error = failure
            if cleanup_error is not None:
                error = AuthoritativeColdGenerationError(
                    f"{error}; unpublished-candidate cleanup was unsafe: "
                    f"{cleanup_error}"
                )
            self._block(error)
            self._raise_transaction_error(error)

    def reconcile_verified_retention(self) -> AuthoritativeColdState:
        """Reduce a verified legacy retain-three store to CURRENT plus predecessor."""
        try:
            with self._store.exclusive_transaction():
                self._retire_interrupted_unpublished_candidates()
                state = self._audit(
                    require_predecessor=False,
                    allow_empty=False,
                    maximum_generations=TRANSIENT_AUTHORITATIVE_GENERATIONS,
                )
                if state is None:
                    raise AuthoritativeColdGenerationError(
                        "cold-generation reconciliation found no CURRENT"
                    )
                if self._pre_publish_validator(state.current) is not True:
                    raise AuthoritativeColdGenerationError(
                        "cold-generation CURRENT failed cold-restore "
                        "validation during reconciliation"
                    )
                if (
                    state.predecessor is not None
                    and self._pre_publish_validator(state.predecessor) is not True
                ):
                    raise AuthoritativeColdGenerationError(
                        "cold-generation predecessor failed cold-restore "
                        "validation during reconciliation"
                    )
                reverified_current = self._store.verify_generation(
                    state.current.generation_uuid
                )
                if (
                    reverified_current.recovery_certificate_bytes()
                    != state.current.recovery_certificate_bytes()
                ):
                    raise AuthoritativeColdGenerationError(
                        "cold-generation CURRENT changed during reconciliation "
                        "validation"
                    )
                if state.predecessor is not None:
                    reverified_predecessor = self._store.verify_generation(
                        state.predecessor.generation_uuid
                    )
                    if (
                        reverified_predecessor.recovery_certificate_bytes()
                        != state.predecessor.recovery_certificate_bytes()
                    ):
                        raise AuthoritativeColdGenerationError(
                            "cold-generation predecessor changed during "
                            "reconciliation validation"
                        )
                self._store.prune_generations(
                    retain=RETAINED_AUTHORITATIVE_GENERATIONS,
                    verified_current=reverified_current,
                )
                reconciled = self._audit(
                    require_predecessor=state.predecessor is not None,
                    allow_empty=False,
                )
                if reconciled is None:
                    raise AuthoritativeColdGenerationError(
                        "cold-generation reconciliation produced no CURRENT"
                    )
            self._blocked_reason = None
            return reconciled
        except Exception as error:
            self._block(error)
            if isinstance(error, AuthoritativeColdGenerationError):
                raise
            raise AuthoritativeColdGenerationError(
                f"cold-generation reconciliation failed: {error}"
            ) from error


__all__ = [
    "AuthoritativeColdGenerationError",
    "AuthoritativeColdGenerationStore",
    "AuthoritativeColdState",
    "EncodedGenerationCensus",
    "RETAINED_AUTHORITATIVE_GENERATIONS",
    "TRANSIENT_AUTHORITATIVE_GENERATIONS",
]
