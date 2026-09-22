"""Streaming causal coverage for immutable learned-state generations.

The causal receipt is a detached staged file created before the generation
manifest becomes immutable.  It binds every other candidate file through an
exact content root, so it does not hash itself.  The final generation manifest
then seals both the covered files and the detached receipt.

Each changed learned path is bound separately to its owning causal producer.
Candidate files are inspected through fixed-size streaming reads with
``O_NOFOLLOW``; this module never materializes a generation file in memory.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Mapping, Sequence

from dsf_ai_service.substrate.immutable_generation_store import (
    LoadedGeneration,
)
from dsf_ai_service.substrate.owner_scoped_persistence import (
    OwnerScopedPersistenceError,
    OwnerStateSnapshotReceipt,
    ROLE_RECEIPT,
    ownership_for_path,
    verify_owner_state_snapshot_receipt,
)


CAUSAL_MUTATION_RECEIPT_SCHEMA = (
    "guala.causal_generation_mutation_receipt.v2"
)
CONTENT_DELTA_SCHEMA = "guala.generation_content_delta.v1"
DETACHED_CAUSAL_MUTATION_MEMBER_PATH = (
    "receipts/causal_generation_mutation.v2.json"
)
STREAM_READ_BYTES = 1024 * 1024
MAX_DETACHED_MEMBER_BYTES = 2 * 1024 * 1024
_RECEIPT_DOMAIN = b"guala-causal-generation-mutation-receipt-v2\0"
_HEX = frozenset("0123456789abcdef")


class GenerationContentDeltaError(RuntimeError):
    """A generation delta or causal mutation member is invalid."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _hmac_key(value: bytes) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError("content-delta HMAC key must be bytes")
    result = bytes(value)
    if len(result) < 32:
        raise GenerationContentDeltaError(
            "content-delta HMAC key must contain at least 32 bytes"
        )
    return result


def _sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise GenerationContentDeltaError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _path(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\\" in value
    ):
        raise GenerationContentDeltaError(f"{label} is invalid")
    parsed = PurePosixPath(value)
    if (
        parsed.is_absolute()
        or ".." in parsed.parts
        or parsed.as_posix() != value
    ):
        raise GenerationContentDeltaError(f"{label} is invalid")
    return value


def _text(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 256
    ):
        raise GenerationContentDeltaError(f"{label} is invalid")
    return value


def _positive_tick(value: Any, baseline_tick: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= baseline_tick
    ):
        raise GenerationContentDeltaError(
            "candidate tick must be newer than baseline"
        )
    return value


def _generation_records(
    generation: LoadedGeneration,
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(generation, LoadedGeneration):
        raise TypeError("generation must be a verified LoadedGeneration")
    if not generation.content_addressed:
        raise GenerationContentDeltaError(
            "content-delta authority requires content-addressed generations"
        )
    records = generation.recovery_certificate().get("required_files")
    if not isinstance(records, list):
        raise GenerationContentDeltaError(
            "verified generation has no required-file records"
        )
    result: dict[str, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise GenerationContentDeltaError(
                "verified generation file record is invalid"
            )
        relative = _path(
            record.get("relative_path"),
            "verified generation path",
        )
        if relative in result:
            raise GenerationContentDeltaError(
                "verified generation paths are duplicated"
            )
        result[relative] = record
    if tuple(sorted(result)) != generation.required_files:
        raise GenerationContentDeltaError(
            "verified generation certificate differs from required paths"
        )
    return result


def _stream_file_record(root: Path, relative_path: str) -> dict[str, Any]:
    relative = _path(relative_path, "candidate stage path")
    try:
        root_fd = os.open(
            root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
    except OSError as error:
        raise GenerationContentDeltaError(
            "candidate stage root is unavailable or not a real directory"
        ) from error
    directory_fd = root_fd
    file_fd: int | None = None
    try:
        parts = PurePosixPath(relative).parts
        for part in parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            if directory_fd != root_fd:
                os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=directory_fd,
        )
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise GenerationContentDeltaError(
                f"candidate stage path is not a regular file: {relative}"
            )
        digest = hashlib.sha256()
        size = 0
        while True:
            block = os.read(file_fd, STREAM_READ_BYTES)
            if not block:
                break
            digest.update(block)
            size += len(block)
        after = os.fstat(file_fd)
        if (
            size != before.st_size
            or after.st_size != before.st_size
            or after.st_ino != before.st_ino
            or after.st_dev != before.st_dev
            or after.st_mtime_ns != before.st_mtime_ns
        ):
            raise GenerationContentDeltaError(
                f"candidate stage file changed while hashing: {relative}"
            )
        return {
            "relative_path": relative,
            "sha256": digest.hexdigest(),
            "size_bytes": size,
        }
    except OSError as error:
        raise GenerationContentDeltaError(
            f"candidate stage path is unavailable or linked: {relative}"
        ) from error
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd != root_fd:
            os.close(directory_fd)
        os.close(root_fd)


def _stage_records(
    root: Path,
    relative_paths: Sequence[str],
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(root, Path):
        raise TypeError("candidate stage root must be a Path")
    paths = tuple(sorted(
        _path(value, "candidate stage path") for value in relative_paths
    ))
    if not paths or len(paths) != len(set(paths)):
        raise GenerationContentDeltaError(
            "candidate stage paths are empty or duplicated"
        )
    return {
        relative: _stream_file_record(root, relative)
        for relative in paths
    }


def _content_root(
    records: Mapping[str, Mapping[str, Any]],
    *,
    excluded_path: str,
) -> str:
    return _digest({
        "files": [
            {
                "relative_path": path,
                "sha256": records[path]["sha256"],
                "size_bytes": int(records[path]["size_bytes"]),
            }
            for path in sorted(records)
            if path != excluded_path
        ],
        "schema": "guala.generation_candidate_content_root.v1",
    })


@dataclass(frozen=True, slots=True)
class FileContentMutation:
    relative_path: str
    prior_sha256: str | None
    prior_size_bytes: int | None
    candidate_sha256: str | None
    candidate_size_bytes: int | None

    def receipt(self) -> dict[str, Any]:
        return {
            "candidate_sha256": self.candidate_sha256,
            "candidate_size_bytes": self.candidate_size_bytes,
            "prior_sha256": self.prior_sha256,
            "prior_size_bytes": self.prior_size_bytes,
            "relative_path": self.relative_path,
        }


@dataclass(frozen=True, slots=True)
class NewContentChunk:
    sha256: str
    size_bytes: int
    relative_paths: tuple[str, ...]

    def receipt(self) -> dict[str, Any]:
        return {
            "relative_paths": list(self.relative_paths),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class GenerationContentDelta:
    identity: str
    baseline_generation_uuid: str
    baseline_tick: int
    baseline_manifest_sha256: str
    candidate_generation_uuid: str
    candidate_tick: int
    candidate_manifest_sha256: str
    changed_files: tuple[FileContentMutation, ...]
    new_chunks: tuple[NewContentChunk, ...]
    candidate_manifest_bytes: int
    candidate_recovery_receipt_bytes: int

    @property
    def new_unique_content_bytes(self) -> int:
        return sum(value.size_bytes for value in self.new_chunks)


def _mutations(
    baseline: Mapping[str, Mapping[str, Any]],
    candidate: Mapping[str, Mapping[str, Any]],
    *,
    excluded_path: str | None = None,
) -> tuple[FileContentMutation, ...]:
    result = []
    for relative in sorted(set(baseline) | set(candidate)):
        if relative == excluded_path:
            continue
        prior = baseline.get(relative)
        current = candidate.get(relative)
        if (
            prior is not None
            and current is not None
            and prior["sha256"] == current["sha256"]
            and int(prior["size_bytes"]) == int(current["size_bytes"])
        ):
            continue
        result.append(FileContentMutation(
            relative_path=relative,
            prior_sha256=None if prior is None else prior["sha256"],
            prior_size_bytes=(
                None if prior is None else int(prior["size_bytes"])
            ),
            candidate_sha256=(
                None if current is None else current["sha256"]
            ),
            candidate_size_bytes=(
                None if current is None else int(current["size_bytes"])
            ),
        ))
    return tuple(result)


def _bindings(
    mutations: tuple[FileContentMutation, ...],
    *,
    identity: str,
    candidate_tick: int,
    authorities: Mapping[str, OwnerStateSnapshotReceipt],
    owner_snapshot_authority_key: bytes,
) -> list[dict[str, Any]]:
    if not isinstance(authorities, Mapping):
        raise TypeError("causal path authorities must be a mapping")
    changed = []
    for mutation in mutations:
        try:
            ownership = ownership_for_path(mutation.relative_path)
        except OwnerScopedPersistenceError as error:
            raise GenerationContentDeltaError(
                "changed generation path has no exact owner: "
                + mutation.relative_path
            ) from error
        if ownership.requires_split:
            raise GenerationContentDeltaError(
                "changed multi-owner path requires physical split: "
                + mutation.relative_path
            )
        if ownership.stable_body_required:
            changed.append(mutation)
    changed = tuple(changed)
    deleted = tuple(
        value.relative_path
        for value in changed
        if value.candidate_sha256 is None
    )
    if deleted:
        raise GenerationContentDeltaError(
            "additive learned state forbids deleted learned paths: "
            + ", ".join(deleted)
        )
    if tuple(sorted(authorities)) != tuple(
        value.relative_path for value in changed
    ):
        raise GenerationContentDeltaError(
            "causal path authorities must exactly cover changed learned paths"
        )
    result = []
    for mutation in changed:
        authority = verify_owner_state_snapshot_receipt(
            authorities[mutation.relative_path],
            owner_snapshot_authority_key,
        )
        if (
            authority.identity != identity
            or authority.relative_path != mutation.relative_path
            or authority.body_sha256 != mutation.candidate_sha256
            or authority.body_bytes != mutation.candidate_size_bytes
            or authority.frozen_tick != candidate_tick
        ):
            raise GenerationContentDeltaError(
                "owner snapshot receipt does not bind the staged path body"
            )
        result.append({
            "candidate_sha256": mutation.candidate_sha256,
            "candidate_size_bytes": mutation.candidate_size_bytes,
            "relative_path": mutation.relative_path,
            "owner_snapshot_receipt": authority.record(),
        })
    return result


def prepare_causal_mutation_manifest_member(
    baseline: LoadedGeneration,
    *,
    candidate_stage_root: Path,
    candidate_relative_paths: Sequence[str],
    candidate_tick: int,
    path_authorities: Mapping[str, OwnerStateSnapshotReceipt],
    owner_snapshot_authority_key: bytes,
    hmac_key: bytes,
    member_path: str = DETACHED_CAUSAL_MUTATION_MEMBER_PATH,
) -> bytes:
    """Stream the staged candidate and return its detached causal member."""
    baseline_records = _generation_records(baseline)
    detached = _path(member_path, "detached causal member path")
    candidate_paths = tuple(candidate_relative_paths)
    if detached in candidate_paths:
        raise GenerationContentDeltaError(
            "detached causal member already exists in candidate stage"
        )
    candidate_records = _stage_records(
        candidate_stage_root,
        candidate_paths,
    )
    tick = _positive_tick(candidate_tick, baseline.tick)
    mutations = _mutations(
        baseline_records,
        candidate_records,
        excluded_path=detached,
    )
    path_bindings = _bindings(
        mutations,
        identity=baseline.identity,
        candidate_tick=tick,
        authorities=path_authorities,
        owner_snapshot_authority_key=owner_snapshot_authority_key,
    )
    unsigned = {
        "baseline_generation_uuid": baseline.generation_uuid,
        "baseline_manifest_sha256": baseline.manifest_sha256,
        "baseline_tick": baseline.tick,
        "candidate_content_root_sha256": _content_root(
            candidate_records,
            excluded_path=detached,
        ),
        "candidate_tick": tick,
        "changed_files": [value.receipt() for value in mutations],
        "detached_manifest_member_path": detached,
        "identity": baseline.identity,
        "owner_snapshot_paths": [
            value["relative_path"] for value in path_bindings
        ],
        "path_owner_snapshots": path_bindings,
        "schema": CAUSAL_MUTATION_RECEIPT_SCHEMA,
    }
    signature = hmac.new(
        _hmac_key(hmac_key),
        _RECEIPT_DOMAIN + _canonical(unsigned),
        hashlib.sha256,
    ).hexdigest()
    encoded = _canonical(
        unsigned | {"receipt_hmac_sha256": signature}
    )
    if len(encoded) > MAX_DETACHED_MEMBER_BYTES:
        raise GenerationContentDeltaError(
            "detached causal mutation member exceeds capacity"
        )
    return encoded


def changed_stable_stage_paths(
    baseline: LoadedGeneration,
    *,
    candidate_stage_root: Path,
    candidate_relative_paths: Sequence[str],
    member_path: str = DETACHED_CAUSAL_MUTATION_MEMBER_PATH,
) -> tuple[str, ...]:
    """Return exactly the changed single-owner stable paths in a stage."""
    baseline_records = _generation_records(baseline)
    detached = _path(member_path, "detached causal member path")
    candidate_records = _stage_records(
        candidate_stage_root,
        tuple(candidate_relative_paths),
    )
    changed = []
    for mutation in _mutations(
        baseline_records,
        candidate_records,
        excluded_path=detached,
    ):
        try:
            ownership = ownership_for_path(mutation.relative_path)
        except OwnerScopedPersistenceError as error:
            raise GenerationContentDeltaError(
                "changed generation path has no exact owner: "
                + mutation.relative_path
            ) from error
        if ownership.requires_split:
            raise GenerationContentDeltaError(
                "changed multi-owner path requires physical split: "
                + mutation.relative_path
            )
        if ownership.stable_body_required:
            if mutation.candidate_sha256 is None:
                raise GenerationContentDeltaError(
                    "stable owner state forbids a deleted path: "
                    + mutation.relative_path
                )
            changed.append(mutation.relative_path)
    return tuple(changed)


def exact_current_generation_receipt_paths(
    baseline: LoadedGeneration,
    *,
    candidate_stage_root: Path,
    candidate_relative_paths: Sequence[str],
    candidate_tick: int,
    rebuilt_member_paths: Sequence[str],
) -> tuple[str, ...]:
    """Return baseline receipt members needed for exact read-only reuse.

    An equal lived tick cannot authorize a new causal mutation receipt.  The
    only truthful code-only deployment is therefore reuse of the already
    sealed generation.  Runtime staging may omit immutable receipt members
    because ordinary state save owns organism bodies, not generation
    authority.  This census permits those exact baseline receipt members to be
    streamed back into the private stage.  It does not decide equivalence:
    ``stage_authoritative_commit_upload`` still recomputes the complete causal
    projection and admits only exact current-generation reuse.
    """
    if (
        isinstance(candidate_tick, bool)
        or not isinstance(candidate_tick, int)
        or candidate_tick != baseline.tick
    ):
        raise GenerationContentDeltaError(
            "read-only generation reuse requires the exact baseline tick"
        )
    baseline_records = _generation_records(baseline)
    candidate_records = _stage_records(
        candidate_stage_root,
        candidate_relative_paths,
    )
    rebuilt = tuple(sorted(
        _path(value, "rebuilt generation member path")
        for value in rebuilt_member_paths
    ))
    if len(rebuilt) != len(set(rebuilt)):
        raise GenerationContentDeltaError(
            "rebuilt generation member paths are duplicated"
        )
    unknown_rebuilt = set(rebuilt).difference(baseline_records)
    if unknown_rebuilt:
        raise GenerationContentDeltaError(
            "rebuilt generation members are absent from the baseline: "
            + ", ".join(sorted(unknown_rebuilt))
        )
    unexpected = set(candidate_records).difference(baseline_records)
    if unexpected:
        raise GenerationContentDeltaError(
            "equal-tick stage adds paths outside the sealed baseline: "
            + ", ".join(sorted(unexpected))
        )
    supplied_rebuilt = set(rebuilt).intersection(candidate_records)
    if supplied_rebuilt:
        raise GenerationContentDeltaError(
            "runtime stage supplied generation-authority members: "
            + ", ".join(sorted(supplied_rebuilt))
        )
    missing = (
        set(baseline_records)
        .difference(candidate_records)
        .difference(rebuilt)
    )
    receipt_paths = []
    non_receipt_paths = []
    for relative_path in sorted(missing):
        try:
            ownership = ownership_for_path(relative_path)
        except OwnerScopedPersistenceError as error:
            raise GenerationContentDeltaError(
                "missing equal-tick path has no exact owner: "
                + relative_path
            ) from error
        if ownership.role == ROLE_RECEIPT:
            receipt_paths.append(relative_path)
        else:
            non_receipt_paths.append(relative_path)
    if non_receipt_paths:
        raise GenerationContentDeltaError(
            "equal-tick stage omitted causal baseline paths: "
            + ", ".join(non_receipt_paths)
        )
    return tuple(receipt_paths)


def _read_detached_member(
    candidate: LoadedGeneration,
    relative_path: str,
) -> bytes:
    record = _generation_records(candidate)[relative_path]
    size = int(record["size_bytes"])
    if size <= 0 or size > MAX_DETACHED_MEMBER_BYTES:
        raise GenerationContentDeltaError(
            "detached causal mutation member exceeds capacity"
        )
    encoded = candidate.stored_bytes(relative_path)
    if len(encoded) != size:
        raise GenerationContentDeltaError(
            "detached causal mutation member size changed"
        )
    return encoded


def validate_causal_mutation_manifest_member(
    baseline: LoadedGeneration,
    candidate: LoadedGeneration,
    *,
    owner_snapshot_authority_key: bytes,
    hmac_key: bytes,
    member_path: str = DETACHED_CAUSAL_MUTATION_MEMBER_PATH,
) -> dict[str, Any]:
    """Verify the final sealed member and exact per-path causal bindings."""
    baseline_records = _generation_records(baseline)
    candidate_records = _generation_records(candidate)
    detached = _path(member_path, "detached causal member path")
    if (
        candidate.identity != baseline.identity
        or candidate.tick <= baseline.tick
        or detached not in candidate_records
    ):
        raise GenerationContentDeltaError(
            "candidate cannot satisfy detached causal coverage"
        )
    encoded = _read_detached_member(candidate, detached)
    try:
        receipt = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GenerationContentDeltaError(
            "detached causal mutation member is unreadable"
        ) from error
    fields = {
        "baseline_generation_uuid",
        "baseline_manifest_sha256",
        "baseline_tick",
        "candidate_content_root_sha256",
        "candidate_tick",
        "changed_files",
        "detached_manifest_member_path",
        "identity",
        "owner_snapshot_paths",
        "path_owner_snapshots",
        "receipt_hmac_sha256",
        "schema",
    }
    if (
        not isinstance(receipt, dict)
        or set(receipt) != fields
        or _canonical(receipt) != encoded
        or receipt.get("schema") != CAUSAL_MUTATION_RECEIPT_SCHEMA
    ):
        raise GenerationContentDeltaError(
            "detached causal mutation member fields changed"
        )
    signature = receipt.pop("receipt_hmac_sha256")
    expected_signature = hmac.new(
        _hmac_key(hmac_key),
        _RECEIPT_DOMAIN + _canonical(receipt),
        hashlib.sha256,
    ).hexdigest()
    if not isinstance(signature, str) or not hmac.compare_digest(
        signature,
        expected_signature,
    ):
        raise GenerationContentDeltaError(
            "detached causal mutation member authentication failed"
        )
    mutations = _mutations(
        baseline_records,
        candidate_records,
        excluded_path=detached,
    )
    raw_bindings = receipt.get("path_owner_snapshots")
    if not isinstance(raw_bindings, list):
        raise GenerationContentDeltaError(
            "learned path authority records changed"
        )
    mutation_by_path = {
        value.relative_path: value for value in mutations
    }
    authorities: dict[str, OwnerStateSnapshotReceipt] = {}
    for binding in raw_bindings:
        if not isinstance(binding, dict) or set(binding) != {
            "candidate_sha256",
            "candidate_size_bytes",
            "owner_snapshot_receipt",
            "relative_path",
        }:
            raise GenerationContentDeltaError(
                "learned path authority binding changed"
            )
        relative = _path(
            binding["relative_path"],
            "learned authority path",
        )
        mutation = mutation_by_path.get(relative)
        if (
            mutation is None
            or relative in authorities
            or binding["candidate_sha256"] != mutation.candidate_sha256
            or binding["candidate_size_bytes"]
            != mutation.candidate_size_bytes
        ):
            raise GenerationContentDeltaError(
                "learned path authority content binding changed"
            )
        authority = verify_owner_state_snapshot_receipt(
            binding["owner_snapshot_receipt"],
            owner_snapshot_authority_key,
        )
        authorities[relative] = authority
    expected_bindings = _bindings(
        mutations,
        identity=baseline.identity,
        candidate_tick=candidate.tick,
        authorities=authorities,
        owner_snapshot_authority_key=owner_snapshot_authority_key,
    )
    expected = {
        "baseline_generation_uuid": baseline.generation_uuid,
        "baseline_manifest_sha256": baseline.manifest_sha256,
        "baseline_tick": baseline.tick,
        "candidate_content_root_sha256": _content_root(
            candidate_records,
            excluded_path=detached,
        ),
        "candidate_tick": candidate.tick,
        "changed_files": [value.receipt() for value in mutations],
        "detached_manifest_member_path": detached,
        "identity": baseline.identity,
        "owner_snapshot_paths": [
            value["relative_path"] for value in expected_bindings
        ],
        "path_owner_snapshots": expected_bindings,
        "schema": CAUSAL_MUTATION_RECEIPT_SCHEMA,
    }
    if receipt != expected:
        raise GenerationContentDeltaError(
            "detached causal mutation member does not exactly cover "
            "the sealed candidate"
        )
    return receipt | {"receipt_hmac_sha256": signature}


def _chunk_map(
    records: Mapping[str, Mapping[str, Any]],
) -> dict[str, tuple[int, set[str]]]:
    result: dict[str, tuple[int, set[str]]] = {}
    for relative, record in records.items():
        for chunk in record["chunks"]:
            digest = chunk["sha256"]
            size = int(chunk["size_bytes"])
            prior = result.get(digest)
            if prior is None:
                result[digest] = (size, {relative})
            else:
                if prior[0] != size:
                    raise GenerationContentDeltaError(
                        f"content chunk {digest} has conflicting sizes"
                    )
                prior[1].add(relative)
    return result


def census_generation_content_delta(
    baseline: LoadedGeneration,
    candidate: LoadedGeneration,
    *,
    retained_generations: Sequence[LoadedGeneration] = (),
) -> GenerationContentDelta:
    """Return exact post-seal file mutation and unique-chunk allocation."""
    baseline_records = _generation_records(baseline)
    candidate_records = _generation_records(candidate)
    retained = (baseline, *tuple(retained_generations))
    for generation in retained:
        _generation_records(generation)
        if generation.identity != baseline.identity:
            raise GenerationContentDeltaError(
                "retained generation identity differs from baseline"
            )
    if candidate.identity != baseline.identity:
        raise GenerationContentDeltaError(
            "candidate generation identity differs from baseline"
        )
    _positive_tick(candidate.tick, baseline.tick)
    retained_chunks: dict[str, int] = {}
    for generation in retained:
        for digest, (size, _paths) in _chunk_map(
            _generation_records(generation)
        ).items():
            prior = retained_chunks.setdefault(digest, size)
            if prior != size:
                raise GenerationContentDeltaError(
                    f"retained chunk {digest} has conflicting sizes"
                )
    new_chunks = tuple(
        NewContentChunk(
            sha256=digest,
            size_bytes=size,
            relative_paths=tuple(sorted(paths)),
        )
        for digest, (size, paths) in sorted(
            _chunk_map(candidate_records).items()
        )
        if digest not in retained_chunks
    )
    return GenerationContentDelta(
        identity=baseline.identity,
        baseline_generation_uuid=baseline.generation_uuid,
        baseline_tick=baseline.tick,
        baseline_manifest_sha256=baseline.manifest_sha256,
        candidate_generation_uuid=candidate.generation_uuid,
        candidate_tick=candidate.tick,
        candidate_manifest_sha256=candidate.manifest_sha256,
        changed_files=_mutations(baseline_records, candidate_records),
        new_chunks=new_chunks,
        candidate_manifest_bytes=(
            candidate.directory / "MANIFEST.json"
        ).stat().st_size,
        candidate_recovery_receipt_bytes=len(
            candidate.recovery_certificate_bytes()
        ),
    )


__all__ = (
    "CAUSAL_MUTATION_RECEIPT_SCHEMA",
    "CONTENT_DELTA_SCHEMA",
    "DETACHED_CAUSAL_MUTATION_MEMBER_PATH",
    "FileContentMutation",
    "GenerationContentDelta",
    "GenerationContentDeltaError",
    "MAX_DETACHED_MEMBER_BYTES",
    "NewContentChunk",
    "STREAM_READ_BYTES",
    "census_generation_content_delta",
    "changed_stable_stage_paths",
    "exact_current_generation_receipt_paths",
    "prepare_causal_mutation_manifest_member",
    "validate_causal_mutation_manifest_member",
)
