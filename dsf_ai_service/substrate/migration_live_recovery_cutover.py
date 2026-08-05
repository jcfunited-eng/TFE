"""Authenticated live-recovery custody for one schema-migration cutover.

This module coordinates only the separate live-recovery store.  It does not
interpret owner state or publish cold generations itself.  Forward handoff
invokes its publication callback only after an HMAC-proven overlay has been
shown byte-identical to the sealed source and retired.  Rollback preserves a
valid destination overlay by atomic quarantine before invoking source
restoration.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dsf_ai_service.substrate.deployment_generation import (
    discover_and_load_current,
)
from dsf_ai_service.substrate.live_recovery_generation import (
    LIVE_RECOVERY_LINEAGE_FILE,
    LiveRecoveryError,
    LiveRecoveryGenerationStore,
    retire_redundant_predecessor_current,
)
from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)


INTENT_SCHEMA = "guala.migration_live_recovery_cutover.intent.v1"
MAX_INTENT_BYTES = 16 * 1024
MAX_ROLLBACK_QUARANTINES = 1
_INTENT_DOMAIN = b"guala-migration-live-recovery-cutover-intent-v1\0"
_HEX = frozenset("0123456789abcdef")


class MigrationLiveRecoveryCutoverError(RuntimeError):
    """Live-recovery state cannot cross the migration boundary safely."""


@dataclass(frozen=True, slots=True)
class HandoffLiveRecoveryResult:
    publication: object
    source_overlay_generation: str
    source_overlay_manifest_sha256: str
    source_overlay_tick: int
    destination_generation: str
    destination_manifest_sha256: str
    destination_tick: int
    intent_sha256: str


@dataclass(frozen=True, slots=True)
class RollbackLiveRecoveryResult:
    restoration: object
    overlay_disposition: str
    quarantined_path: str | None
    intent_sha256: str


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _key(value: bytes | bytearray | memoryview) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise MigrationLiveRecoveryCutoverError(
            "cutover HMAC key must be bytes"
        )
    raw = bytes(value)
    if len(raw) < 32:
        raise MigrationLiveRecoveryCutoverError(
            "cutover HMAC key must contain at least 32 bytes"
        )
    return hashlib.sha256(_INTENT_DOMAIN + raw).digest()


def _digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise MigrationLiveRecoveryCutoverError(
            f"{label} is not a lowercase SHA-256"
        )
    return value


def _generation_record(generation, label: str) -> dict[str, object]:
    try:
        generation_uuid = str(generation.generation_uuid)
        identity = str(generation.identity)
        tick = generation.tick
        manifest = generation.manifest_sha256
    except AttributeError as error:
        raise MigrationLiveRecoveryCutoverError(
            f"{label} is not a verified generation"
        ) from error
    if (
        not generation_uuid
        or not identity
        or isinstance(tick, bool)
        or not isinstance(tick, int)
        or tick < 0
    ):
        raise MigrationLiveRecoveryCutoverError(
            f"{label} metadata changed"
        )
    return {
        "generation_uuid": generation_uuid,
        "identity": identity,
        "manifest_sha256": _digest(
            manifest,
            f"{label} manifest",
        ),
        "tick": tick,
    }


def _signed_intent(body: dict[str, object], key: bytes) -> bytes:
    envelope = {
        "authority_hmac_sha256": hmac.new(
            key,
            _INTENT_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest(),
        "body": body,
        "schema": INTENT_SCHEMA,
    }
    encoded = _canonical(envelope)
    if len(encoded) > MAX_INTENT_BYTES:
        raise MigrationLiveRecoveryCutoverError(
            "cutover intent exceeds its byte boundary"
        )
    return encoded


def _load_intent(path: Path, key: bytes) -> dict[str, object] | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if (
        path.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_size <= 0
        or info.st_size > MAX_INTENT_BYTES
    ):
        raise MigrationLiveRecoveryCutoverError(
            "cutover intent path is unsafe"
        )
    encoded = path.read_bytes()
    try:
        envelope = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MigrationLiveRecoveryCutoverError(
            "cutover intent is unreadable"
        ) from error
    if (
        _canonical(envelope) != encoded
        or not isinstance(envelope, dict)
        or set(envelope)
        != {"authority_hmac_sha256", "body", "schema"}
        or envelope.get("schema") != INTENT_SCHEMA
        or not isinstance(envelope.get("body"), dict)
    ):
        raise MigrationLiveRecoveryCutoverError(
            "cutover intent envelope changed"
        )
    expected = hmac.new(
        key,
        _INTENT_DOMAIN + _canonical(envelope["body"]),
        hashlib.sha256,
    ).hexdigest()
    supplied = envelope.get("authority_hmac_sha256")
    if (
        not isinstance(supplied, str)
        or not hmac.compare_digest(expected, supplied)
    ):
        raise MigrationLiveRecoveryCutoverError(
            "cutover intent authentication failed"
        )
    return envelope["body"]


def _persist_intent(
    path: Path,
    body: dict[str, object],
    *,
    key: bytes,
    physical_byte_authority: PhysicalByteCeilingAuthority,
) -> str:
    encoded = _signed_intent(body, key)
    physical_byte_authority.atomic_replace_bytes(
        path,
        encoded,
        operation="persist_migration_live_recovery_cutover_intent",
        mode=0o600,
    )
    return hashlib.sha256(encoded).hexdigest()


def _scoped_path(
    value: Path,
    *,
    physical_byte_authority: PhysicalByteCeilingAuthority,
    label: str,
) -> Path:
    supplied = Path(value)
    try:
        parent = supplied.parent.resolve(strict=True)
        parent.relative_to(physical_byte_authority.scope_root)
    except (OSError, ValueError) as error:
        raise MigrationLiveRecoveryCutoverError(
            f"{label} is outside the physical-byte scope"
        ) from error
    resolved = parent / supplied.name
    if resolved.exists() and resolved.is_symlink():
        raise MigrationLiveRecoveryCutoverError(
            f"{label} cannot be a symbolic link"
        )
    return resolved


def _lineage_hot_files(generation) -> tuple[str, ...]:
    try:
        lineage = generation.payload(LIVE_RECOVERY_LINEAGE_FILE)
    except Exception as error:
        raise MigrationLiveRecoveryCutoverError(
            f"live-recovery lineage cannot be read: {error}"
        ) from error
    hot_files = (
        lineage.get("hot_files")
        if isinstance(lineage, dict)
        else None
    )
    if (
        not isinstance(hot_files, list)
        or not hot_files
        or any(not isinstance(value, str) for value in hot_files)
    ):
        raise MigrationLiveRecoveryCutoverError(
            "live-recovery hot-file lineage changed"
        )
    return tuple(hot_files)


def _declared_overlay_baseline(root: Path) -> str:
    try:
        generation = discover_and_load_current(root).generation
        lineage = generation.payload(LIVE_RECOVERY_LINEAGE_FILE)
    except Exception as error:
        raise MigrationLiveRecoveryCutoverError(
            f"live-recovery lineage cannot be read: {error}"
        ) from error
    value = (
        lineage.get("baseline_generation_uuid")
        if isinstance(lineage, dict)
        else None
    )
    if not isinstance(value, str) or not value:
        raise MigrationLiveRecoveryCutoverError(
            "live-recovery baseline lineage changed"
        )
    return value


def _verified_overlay(
    root: Path,
    *,
    baseline,
    hmac_key: bytes,
):
    try:
        discovered = discover_and_load_current(root).generation
        hot_files = _lineage_hot_files(discovered)
        manager = LiveRecoveryGenerationStore(
            root,
            baseline=baseline,
            hot_files=hot_files,
            hmac_key=hmac_key,
            state_file_tick_manifest=(
                "guala_core.json"
                if "guala_core.json" in hot_files
                else None
            ),
        )
        verified = manager.load_current()
    except Exception as error:
        raise MigrationLiveRecoveryCutoverError(
            f"live-recovery overlay verification failed: {error}"
        ) from error
    if verified is None:
        raise MigrationLiveRecoveryCutoverError(
            "live-recovery overlay disappeared"
        )
    return verified, hot_files


def _exact_payload_bytes(generation, relative_path: str) -> bytes:
    value = generation.payload(relative_path)
    if relative_path.endswith(".json"):
        return _canonical(value)
    if not isinstance(value, bytes):
        raise MigrationLiveRecoveryCutoverError(
            "non-JSON live-recovery payload is not bytes: "
            + relative_path
        )
    return value


def _verify_redundant_source_overlay(
    root: Path,
    *,
    source,
    hmac_key: bytes,
):
    overlay, hot_files = _verified_overlay(
        root,
        baseline=source,
        hmac_key=hmac_key,
    )
    if overlay.tick != source.tick:
        raise MigrationLiveRecoveryCutoverError(
            "source overlay is newer than the sealed source"
        )
    if not set(hot_files).issubset(set(source.required_files)):
        raise MigrationLiveRecoveryCutoverError(
            "source overlay contains paths absent from the sealed source"
        )
    changed = tuple(
        relative
        for relative in hot_files
        if _exact_payload_bytes(overlay, relative)
        != _exact_payload_bytes(source, relative)
    )
    if changed:
        raise MigrationLiveRecoveryCutoverError(
            "source overlay differs from the sealed source: "
            + ", ".join(changed)
        )
    return overlay


def _publication_generation(value: object):
    return getattr(value, "generation", value)


def _same_generation(
    first: dict[str, object],
    second: dict[str, object],
) -> bool:
    return all(
        first[name] == second[name]
        for name in (
            "generation_uuid",
            "identity",
            "manifest_sha256",
            "tick",
        )
    )


def _authenticated_intent_generation_record(
    value: object,
    label: str,
) -> dict[str, object]:
    expected_fields = {
        "generation_uuid",
        "identity",
        "manifest_sha256",
        "tick",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise MigrationLiveRecoveryCutoverError(
            f"{label} has incomplete generation custody"
        )
    generation_uuid = value.get("generation_uuid")
    identity = value.get("identity")
    tick = value.get("tick")
    try:
        canonical_generation_uuid = str(uuid.UUID(generation_uuid))
    except (AttributeError, TypeError, ValueError) as error:
        raise MigrationLiveRecoveryCutoverError(
            f"{label} generation UUID changed"
        ) from error
    if (
        not isinstance(generation_uuid, str)
        or canonical_generation_uuid != generation_uuid
        or not isinstance(identity, str)
        or not identity
        or isinstance(tick, bool)
        or not isinstance(tick, int)
        or tick < 0
    ):
        raise MigrationLiveRecoveryCutoverError(
            f"{label} metadata changed"
        )
    return {
        "generation_uuid": generation_uuid,
        "identity": identity,
        "manifest_sha256": _digest(
            value.get("manifest_sha256"),
            f"{label} manifest",
        ),
        "tick": tick,
    }


def _authorize_terminal_source_restored_rollover(
    *,
    prior: dict[str, object],
    source_record: dict[str, object],
    live_recovery_root: Path,
) -> None:
    if prior.get("state") != "source_restored":
        raise MigrationLiveRecoveryCutoverError(
            "existing cutover intent is not a terminal source restoration"
        )
    if set(prior) != {
        "destination",
        "overlay_disposition",
        "quarantined_path",
        "rollback_overlay",
        "schema",
        "source",
        "source_overlay",
        "state",
    } or prior.get("schema") != INTENT_SCHEMA:
        raise MigrationLiveRecoveryCutoverError(
            "terminal cutover intent structure changed"
        )
    try:
        prior_source_record = _authenticated_intent_generation_record(
            prior.get("source"),
            "terminal cutover source",
        )
        prior_destination_record = (
            _authenticated_intent_generation_record(
                prior.get("destination"),
                "terminal cutover destination",
            )
        )
        prior_overlay_record = _authenticated_intent_generation_record(
            prior.get("source_overlay"),
            "terminal cutover source overlay",
        )
    except MigrationLiveRecoveryCutoverError as error:
        raise MigrationLiveRecoveryCutoverError(
            "terminal cutover intent has incomplete generation custody"
        ) from error
    if (
        prior_source_record["identity"] != source_record["identity"]
        or prior_destination_record["identity"] != source_record["identity"]
        or prior_overlay_record["identity"] != source_record["identity"]
    ):
        raise MigrationLiveRecoveryCutoverError(
            "terminal cutover intent belongs to another identity"
        )
    if source_record["tick"] < max(
        prior_source_record["tick"],
        prior_destination_record["tick"],
        prior_overlay_record["tick"],
    ):
        raise MigrationLiveRecoveryCutoverError(
            "new sealed source precedes the restored source"
        )
    if source_record["generation_uuid"] in {
        prior_source_record["generation_uuid"],
        prior_destination_record["generation_uuid"],
    }:
        raise MigrationLiveRecoveryCutoverError(
            "new sealed source is not a distinct successor generation"
        )
    if (
        prior_source_record["generation_uuid"]
        == prior_destination_record["generation_uuid"]
        or prior.get("overlay_disposition") != "overlay_absent"
    ):
        raise MigrationLiveRecoveryCutoverError(
            "terminal cutover intent is not an exact completed rollback"
        )
    if (
        prior.get("quarantined_path") is not None
        or prior.get("rollback_overlay") is not None
    ):
        raise MigrationLiveRecoveryCutoverError(
            "terminal cutover intent retains rollback quarantine custody"
        )
    occupied = tuple(
        live_recovery_root.parent.glob(
            f".{live_recovery_root.name}.rollback-quarantine-*"
        )
    )
    if occupied:
        raise MigrationLiveRecoveryCutoverError(
            "rollback live-recovery quarantine capacity is occupied"
        )


def _terminal_same_source_retry_overlay(
    *,
    prior: dict[str, object],
    source_record: dict[str, object],
    live_recovery_root: Path,
) -> dict[str, object]:
    """Recover retired overlay custody for one exact post-rollback retry."""
    if (
        prior.get("state") != "source_restored"
        or set(prior) != {
            "destination",
            "overlay_disposition",
            "quarantined_path",
            "rollback_overlay",
            "schema",
            "source",
            "source_overlay",
            "state",
        }
        or prior.get("schema") != INTENT_SCHEMA
    ):
        raise MigrationLiveRecoveryCutoverError(
            "same-source retry lacks an exact terminal source restoration"
        )
    try:
        prior_source = _authenticated_intent_generation_record(
            prior.get("source"),
            "same-source retry source",
        )
        prior_destination = _authenticated_intent_generation_record(
            prior.get("destination"),
            "same-source retry failed destination",
        )
        prior_overlay = _authenticated_intent_generation_record(
            prior.get("source_overlay"),
            "same-source retry retired source overlay",
        )
    except MigrationLiveRecoveryCutoverError as error:
        raise MigrationLiveRecoveryCutoverError(
            "same-source retry has incomplete generation custody"
        ) from error
    if not _same_generation(prior_source, source_record):
        raise MigrationLiveRecoveryCutoverError(
            "same-source retry does not name the restored source"
        )
    if (
        prior_destination["generation_uuid"]
        == source_record["generation_uuid"]
        or prior_overlay["generation_uuid"]
        in {
            source_record["generation_uuid"],
            prior_destination["generation_uuid"],
        }
        or prior_destination["identity"] != source_record["identity"]
        or prior_overlay["identity"] != source_record["identity"]
        or prior_destination["tick"] != source_record["tick"]
        or prior_overlay["tick"] != source_record["tick"]
    ):
        raise MigrationLiveRecoveryCutoverError(
            "same-source retry generation custody changed"
        )
    if (
        prior.get("overlay_disposition") != "overlay_absent"
        or prior.get("quarantined_path") is not None
        or prior.get("rollback_overlay") is not None
    ):
        raise MigrationLiveRecoveryCutoverError(
            "same-source retry retains destination overlay custody"
        )
    if live_recovery_root.exists() or live_recovery_root.is_symlink():
        raise MigrationLiveRecoveryCutoverError(
            "same-source retry live-recovery root reappeared"
        )
    occupied = tuple(
        live_recovery_root.parent.glob(
            f".{live_recovery_root.name}.rollback-quarantine-*"
        )
    )
    if occupied:
        raise MigrationLiveRecoveryCutoverError(
            "same-source retry rollback quarantine is occupied"
        )
    return prior_overlay


def authenticated_terminal_same_source_retry_custody(
    *,
    live_recovery_root: Path,
    intent_path: Path,
    source,
    hmac_key: bytes,
) -> dict[str, dict[str, object]]:
    """Return only HMAC-proven custody for one clean same-source retry."""
    root = Path(live_recovery_root).resolve()
    intent = Path(intent_path).resolve()
    prior = _load_intent(intent, _key(hmac_key))
    if prior is None:
        raise MigrationLiveRecoveryCutoverError(
            "same-source retry has no authenticated terminal intent"
        )
    source_record = _generation_record(source, "same-source retry source")
    overlay_record = _terminal_same_source_retry_overlay(
        prior=prior,
        source_record=source_record,
        live_recovery_root=root,
    )
    destination_record = _authenticated_intent_generation_record(
        prior.get("destination"),
        "same-source retry failed destination",
    )
    return {
        "destination": dict(destination_record),
        "source_overlay": dict(overlay_record),
    }


def publish_after_source_overlay_retirement(
    *,
    live_recovery_root: Path,
    intent_path: Path,
    source,
    hmac_key: bytes,
    physical_byte_authority: PhysicalByteCeilingAuthority,
    publish_destination: Callable[[], object],
) -> HandoffLiveRecoveryResult:
    """Retire only a source-redundant overlay, then publish destination."""

    if not isinstance(
        physical_byte_authority,
        PhysicalByteCeilingAuthority,
    ):
        raise TypeError(
            "physical_byte_authority must be a "
            "PhysicalByteCeilingAuthority"
        )
    if not callable(publish_destination):
        raise TypeError("publish_destination must be callable")
    root = _scoped_path(
        Path(live_recovery_root),
        physical_byte_authority=physical_byte_authority,
        label="live-recovery root",
    )
    intent = _scoped_path(
        Path(intent_path),
        physical_byte_authority=physical_byte_authority,
        label="cutover intent",
    )
    if root == intent:
        raise MigrationLiveRecoveryCutoverError(
            "live-recovery root and cutover intent must differ"
        )
    intent_key = _key(hmac_key)
    source_record = _generation_record(source, "sealed source")
    prior = _load_intent(intent, intent_key)
    overlay_record = None

    if root.exists() or root.is_symlink():
        if root.is_symlink() or not root.is_dir():
            raise MigrationLiveRecoveryCutoverError(
                "live-recovery root is unsafe"
            )
        overlay = _verify_redundant_source_overlay(
            root,
            source=source,
            hmac_key=hmac_key,
        )
        overlay_record = _generation_record(
            overlay,
            "source live-recovery overlay",
        )
        prepared = {
            "destination": None,
            "overlay_disposition": "verified_source_redundant",
            "quarantined_path": None,
            "schema": INTENT_SCHEMA,
            "source": source_record,
            "source_overlay": overlay_record,
            "state": "prepared_source_overlay_retirement",
        }
        if prior is not None and prior != prepared:
            _authorize_terminal_source_restored_rollover(
                prior=prior,
                source_record=source_record,
                live_recovery_root=root,
            )
        _persist_intent(
            intent,
            prepared,
            key=intent_key,
            physical_byte_authority=physical_byte_authority,
        )
        try:
            retired = retire_redundant_predecessor_current(
                root,
                baseline=source,
                hmac_key=hmac_key,
                physical_byte_authority=physical_byte_authority,
            )
        except LiveRecoveryError as error:
            raise MigrationLiveRecoveryCutoverError(str(error)) from error
        if retired != (overlay.generation_uuid,) or root.exists():
            raise MigrationLiveRecoveryCutoverError(
                "source overlay retirement did not complete exactly"
            )
        retired_body = {
            **prepared,
            "overlay_disposition": "source_overlay_retired",
            "state": "source_overlay_retired",
        }
        _persist_intent(
            intent,
            retired_body,
            key=intent_key,
            physical_byte_authority=physical_byte_authority,
        )
        prior = retired_body
    else:
        if (
            prior is not None
            and prior.get("state") == "source_restored"
        ):
            overlay_record = _terminal_same_source_retry_overlay(
                prior=prior,
                source_record=source_record,
                live_recovery_root=root,
            )
        elif (
            prior is not None
            and prior.get("state")
            in {"source_overlay_retired", "destination_published"}
            and isinstance(prior.get("source"), dict)
            and _same_generation(prior["source"], source_record)
            and isinstance(prior.get("source_overlay"), dict)
        ):
            overlay_record = prior["source_overlay"]
        else:
            raise MigrationLiveRecoveryCutoverError(
                "source overlay is absent without an authenticated "
                "retirement intent"
            )

    publication = publish_destination()
    destination = _publication_generation(publication)
    destination_record = _generation_record(
        destination,
        "published destination",
    )
    if (
        destination_record["generation_uuid"]
        == source_record["generation_uuid"]
        or destination_record["identity"] != source_record["identity"]
        or destination_record["tick"] < source_record["tick"]
    ):
        raise MigrationLiveRecoveryCutoverError(
            "published destination does not succeed the sealed source"
        )
    committed = {
        "destination": destination_record,
        "overlay_disposition": "source_overlay_retired",
        "quarantined_path": None,
        "schema": INTENT_SCHEMA,
        "source": source_record,
        "source_overlay": overlay_record,
        "state": "destination_published",
    }
    intent_sha = _persist_intent(
        intent,
        committed,
        key=intent_key,
        physical_byte_authority=physical_byte_authority,
    )
    return HandoffLiveRecoveryResult(
        publication=publication,
        source_overlay_generation=overlay_record["generation_uuid"],
        source_overlay_manifest_sha256=(
            overlay_record["manifest_sha256"]
        ),
        source_overlay_tick=overlay_record["tick"],
        destination_generation=destination_record["generation_uuid"],
        destination_manifest_sha256=(
            destination_record["manifest_sha256"]
        ),
        destination_tick=destination_record["tick"],
        intent_sha256=intent_sha,
    )


def _quarantine_path(root: Path, generation_uuid: str) -> Path:
    return root.parent / (
        f".{root.name}.rollback-quarantine-{generation_uuid}"
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY
        | os.O_DIRECTORY
        | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def restore_source_after_destination_overlay_custody(
    *,
    live_recovery_root: Path,
    intent_path: Path,
    source,
    destination,
    hmac_key: bytes,
    physical_byte_authority: PhysicalByteCeilingAuthority,
    restore_source: Callable[[], object],
) -> RollbackLiveRecoveryResult:
    """Quarantine a verified destination overlay, then restore source."""

    if not isinstance(
        physical_byte_authority,
        PhysicalByteCeilingAuthority,
    ):
        raise TypeError(
            "physical_byte_authority must be a "
            "PhysicalByteCeilingAuthority"
        )
    if not callable(restore_source):
        raise TypeError("restore_source must be callable")
    root = _scoped_path(
        Path(live_recovery_root),
        physical_byte_authority=physical_byte_authority,
        label="live-recovery root",
    )
    intent = _scoped_path(
        Path(intent_path),
        physical_byte_authority=physical_byte_authority,
        label="cutover intent",
    )
    if root == intent:
        raise MigrationLiveRecoveryCutoverError(
            "live-recovery root and cutover intent must differ"
        )
    intent_key = _key(hmac_key)
    source_record = _generation_record(source, "rollback source")
    destination_record = _generation_record(
        destination,
        "rollback destination",
    )
    if source_record["identity"] != destination_record["identity"]:
        raise MigrationLiveRecoveryCutoverError(
            "rollback source and destination identities differ"
        )
    prior = _load_intent(intent, intent_key)
    if prior is not None:
        supplied_source = prior.get("source")
        supplied_destination = prior.get("destination")
        if (
            not isinstance(supplied_source, dict)
            or not _same_generation(supplied_source, source_record)
            or (
                supplied_destination is not None
                and (
                    not isinstance(supplied_destination, dict)
                    or not _same_generation(
                        supplied_destination,
                        destination_record,
                    )
                )
            )
        ):
            raise MigrationLiveRecoveryCutoverError(
                "rollback differs from authenticated cutover intent"
            )

    disposition = "overlay_absent"
    quarantine = None
    overlay_record = None
    if root.exists() or root.is_symlink():
        if root.is_symlink() or not root.is_dir():
            raise MigrationLiveRecoveryCutoverError(
                "rollback live-recovery root is unsafe"
            )
        declared_baseline = _declared_overlay_baseline(root)
        if declared_baseline == source_record["generation_uuid"]:
            _verified_overlay(
                root,
                baseline=source,
                hmac_key=hmac_key,
            )
            disposition = "source_overlay_preserved"
        elif declared_baseline == destination_record["generation_uuid"]:
            overlay, _hot_files = _verified_overlay(
                root,
                baseline=destination,
                hmac_key=hmac_key,
            )
            overlay_record = _generation_record(
                overlay,
                "destination live-recovery overlay",
            )
            quarantine = _quarantine_path(
                root,
                overlay.generation_uuid,
            )
            existing = tuple(
                root.parent.glob(
                    f".{root.name}.rollback-quarantine-*"
                )
            )
            if (
                len(existing) >= MAX_ROLLBACK_QUARANTINES
                or quarantine.exists()
            ):
                raise MigrationLiveRecoveryCutoverError(
                    "rollback live-recovery quarantine capacity is occupied"
                )
            prepared = {
                "destination": destination_record,
                "overlay_disposition": (
                    "verified_destination_overlay_for_quarantine"
                ),
                "quarantined_path": str(quarantine),
                "rollback_overlay": overlay_record,
                "schema": INTENT_SCHEMA,
                "source": source_record,
                "source_overlay": (
                    None if prior is None
                    else prior.get("source_overlay")
                ),
                "state": "prepared_destination_overlay_quarantine",
            }
            _persist_intent(
                intent,
                prepared,
                key=intent_key,
                physical_byte_authority=physical_byte_authority,
            )
            with physical_byte_authority.exclusive_writer():
                if (
                    root.is_symlink()
                    or not root.is_dir()
                    or quarantine.exists()
                ):
                    raise MigrationLiveRecoveryCutoverError(
                        "rollback overlay changed before quarantine"
                    )
                reverified, _ = _verified_overlay(
                    root,
                    baseline=destination,
                    hmac_key=hmac_key,
                )
                if (
                    reverified.recovery_certificate_bytes()
                    != overlay.recovery_certificate_bytes()
                ):
                    raise MigrationLiveRecoveryCutoverError(
                        "rollback overlay changed before quarantine"
                    )
                os.rename(root, quarantine)
                _fsync_directory(root.parent)
            disposition = "destination_overlay_quarantined"
            quarantined = {
                **prepared,
                "overlay_disposition": disposition,
                "state": "destination_overlay_quarantined",
            }
            _persist_intent(
                intent,
                quarantined,
                key=intent_key,
                physical_byte_authority=physical_byte_authority,
            )
            prior = quarantined
        else:
            raise MigrationLiveRecoveryCutoverError(
                "rollback overlay names neither source nor destination"
            )
    elif prior is not None and prior.get("state") in {
        "destination_overlay_quarantined",
        "source_restored",
    }:
        path_value = prior.get("quarantined_path")
        if (
            not isinstance(path_value, str)
            or not Path(path_value).is_dir()
        ):
            raise MigrationLiveRecoveryCutoverError(
                "authenticated rollback quarantine is absent"
            )
        quarantine = Path(path_value)
        disposition = "destination_overlay_quarantined"
        prior_overlay = prior.get("rollback_overlay")
        if not isinstance(prior_overlay, dict):
            raise MigrationLiveRecoveryCutoverError(
                "authenticated rollback overlay record is absent"
            )
        overlay_record = prior_overlay

    restoration = restore_source()
    restored = _publication_generation(restoration)
    restored_record = _generation_record(restored, "restored source")
    if not _same_generation(restored_record, source_record):
        raise MigrationLiveRecoveryCutoverError(
            "rollback callback did not restore the exact source"
        )
    complete = {
        "destination": destination_record,
        "overlay_disposition": disposition,
        "quarantined_path": (
            None if quarantine is None else str(quarantine)
        ),
        "rollback_overlay": overlay_record,
        "schema": INTENT_SCHEMA,
        "source": source_record,
        "source_overlay": (
            None if prior is None else prior.get("source_overlay")
        ),
        "state": "source_restored",
    }
    intent_sha = _persist_intent(
        intent,
        complete,
        key=intent_key,
        physical_byte_authority=physical_byte_authority,
    )
    return RollbackLiveRecoveryResult(
        restoration=restoration,
        overlay_disposition=disposition,
        quarantined_path=(
            None if quarantine is None else str(quarantine)
        ),
        intent_sha256=intent_sha,
    )


__all__ = (
    "HandoffLiveRecoveryResult",
    "INTENT_SCHEMA",
    "MAX_INTENT_BYTES",
    "MAX_ROLLBACK_QUARANTINES",
    "MigrationLiveRecoveryCutoverError",
    "RollbackLiveRecoveryResult",
    "publish_after_source_overlay_retirement",
    "restore_source_after_destination_overlay_custody",
)
