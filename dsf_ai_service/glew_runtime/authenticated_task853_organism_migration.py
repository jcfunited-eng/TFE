"""One-shot boundary for the authenticated task-853 organism migration.

This module admits exactly the production ``GLMFAB03`` predecessor identified
below and returns one sealed ``GLORUN01`` envelope. It is an isolated migration
rehearsal boundary, not an ordinary boot path or a production resource
certificate. The byte ceilings admit the rehearsal; they do not certify exact
allocator or RSS use.

No intermediate materialized-fabric body, owner, lock, database, persistence,
physical-transition, or cognition authority is exposed here.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib


TASK853_GLMFAB03_BYTES = 4_148_843
TASK853_GLMFAB03_SHA256 = bytes.fromhex(
    "b1f538e25d0bf59584266172ccb473b2b2db6ad7ddf1fc1f7ffa542bd2cc7e14"
)
TASK853_IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
TASK853_AUTHENTICATED_PREDECESSOR_TICK = 23_723_846

REHEARSAL_MAX_ENVELOPE_BYTES = 67_108_864
REHEARSAL_MAX_FABRIC_BYTES = 67_108_000
REHEARSAL_MAX_LOGICAL_PEAK_BYTES = 536_870_912

MIGRATION_SCHEMA = "guala.native.task853_organism_runtime_migration.v1"
MIGRATION_SCOPE = "authenticated_task853_predecessor_migration_only"
EXPECTED_CURRENT_FABRIC_BYTES = 442_352
EXPECTED_CURRENT_FABRIC_SHA256 = (
    "2fd667d8446b7fadea2308dd368411080d80487ddbb1c770471f16a0d5add952"
)
EXPECTED_FABRIC_GENERATION = 13
EXPECTED_MOUNTED_GENERATION = 2
EXPECTED_JOINT_FIELD_COUNT = 2
EXPECTED_JOINT_NEURON_COUNT = 96


@dataclass(frozen=True, slots=True)
class VerifiedTask853OrganismMigration:
    """The sealed current envelope and non-authoritative migration evidence."""

    envelope: bytes
    state_sha256: str
    legacy_fabric_sha256: str
    current_fabric_sha256: str
    organism_identity: str
    organism_tick: int
    fabric_generation: int
    mounted_generation: int
    joint_field_count: int
    joint_neuron_count: int

    def as_bytes(self) -> bytes:
        return self.envelope


def _native_core():
    return importlib.import_module("guala_core")


def _canonical_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"task-853 migration {label} is not canonical SHA-256")
    return value


def _authenticate_exact_predecessor(legacy_glmfab03: bytes) -> None:
    if not isinstance(legacy_glmfab03, bytes):
        raise TypeError("task-853 predecessor must be immutable bytes")
    if len(legacy_glmfab03) != TASK853_GLMFAB03_BYTES:
        raise ValueError("task-853 predecessor byte count is not authenticated")
    if not legacy_glmfab03.startswith(b"GLMFAB03"):
        raise ValueError("task-853 predecessor is not GLMFAB03")
    if hashlib.sha256(legacy_glmfab03).digest() != TASK853_GLMFAB03_SHA256:
        raise ValueError("task-853 predecessor SHA-256 is not authenticated")


def _concrete_migration_type(core: object) -> type:
    candidate = getattr(
        core,
        "NativeAuthenticatedTask853RuntimeMigration",
        None,
    )
    if not isinstance(candidate, type):
        raise RuntimeError("task-853 concrete native migration type is unavailable")
    return candidate


def _verify_native_result(
    result: object,
    *,
    concrete_type: type,
) -> VerifiedTask853OrganismMigration:
    if type(result) is not concrete_type:
        raise TypeError("task-853 migration returned a structural impostor")
    envelope = result.as_bytes()
    if not isinstance(envelope, bytes) or not envelope.startswith(b"GLORUN01"):
        raise RuntimeError("task-853 migration did not return one GLORUN01 envelope")

    state_sha256 = _canonical_sha256(result.state_sha256, "state receipt")
    legacy_sha256 = _canonical_sha256(
        result.legacy_fabric_sha256,
        "legacy receipt",
    )
    current_fabric_sha256 = _canonical_sha256(
        result.fabric_sha256,
        "current fabric receipt",
    )
    if (
        result.schema != MIGRATION_SCHEMA
        or result.scope != MIGRATION_SCOPE
        or result.identity != TASK853_IDENTITY
        or result.authenticated_predecessor_organism_tick
        != TASK853_AUTHENTICATED_PREDECESSOR_TICK
        or result.organism_tick != TASK853_AUTHENTICATED_PREDECESSOR_TICK
        or legacy_sha256 != TASK853_GLMFAB03_SHA256.hex()
        or result.state_bytes != len(envelope)
        or state_sha256 != hashlib.sha256(envelope).hexdigest()
        or result.fabric_bytes != EXPECTED_CURRENT_FABRIC_BYTES
        or current_fabric_sha256 != EXPECTED_CURRENT_FABRIC_SHA256
        or result.fabric_generation != EXPECTED_FABRIC_GENERATION
        or result.mounted_generation != EXPECTED_MOUNTED_GENERATION
        or result.joint_field_count != EXPECTED_JOINT_FIELD_COUNT
        or result.joint_neuron_count != EXPECTED_JOINT_NEURON_COUNT
        or result.mounted_step_completed
        or result.physical_transition_claimed
        or result.cognitive_formation_claimed
        or result.python_callback_count != 0
    ):
        raise RuntimeError("task-853 migration changed its authenticated contract")

    return VerifiedTask853OrganismMigration(
        envelope=envelope,
        state_sha256=state_sha256,
        legacy_fabric_sha256=legacy_sha256,
        current_fabric_sha256=current_fabric_sha256,
        organism_identity=result.identity,
        organism_tick=result.organism_tick,
        fabric_generation=result.fabric_generation,
        mounted_generation=result.mounted_generation,
        joint_field_count=result.joint_field_count,
        joint_neuron_count=result.joint_neuron_count,
    )


def migrate_authenticated_task853_predecessor(
    *,
    legacy_glmfab03: bytes,
) -> VerifiedTask853OrganismMigration:
    """Migrate the one authenticated predecessor through the one native seam."""

    _authenticate_exact_predecessor(legacy_glmfab03)
    core = _native_core()
    concrete_type = _concrete_migration_type(core)
    migrate = getattr(
        core,
        "migrate_authenticated_task853_predecessor_to_native_organism_runtime",
        None,
    )
    if not callable(migrate):
        raise RuntimeError("task-853 native migration callable is unavailable")
    result = migrate(
        legacy_glmfab03,
        TASK853_GLMFAB03_SHA256,
        TASK853_IDENTITY,
        TASK853_AUTHENTICATED_PREDECESSOR_TICK,
        REHEARSAL_MAX_ENVELOPE_BYTES,
        REHEARSAL_MAX_FABRIC_BYTES,
        REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
    )
    return _verify_native_result(result, concrete_type=concrete_type)


__all__ = (
    "REHEARSAL_MAX_ENVELOPE_BYTES",
    "REHEARSAL_MAX_FABRIC_BYTES",
    "REHEARSAL_MAX_LOGICAL_PEAK_BYTES",
    "TASK853_AUTHENTICATED_PREDECESSOR_TICK",
    "TASK853_GLMFAB03_BYTES",
    "TASK853_GLMFAB03_SHA256",
    "TASK853_IDENTITY",
    "VerifiedTask853OrganismMigration",
    "migrate_authenticated_task853_predecessor",
)
