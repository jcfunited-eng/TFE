from __future__ import annotations

from dataclasses import dataclass
import hashlib

import pytest

from dsf_ai_service.glew_runtime import (
    authenticated_task853_organism_migration as boundary,
)


@dataclass
class _NativeResult:
    payload: bytes = b"GLORUN01-sealed-current-organism"
    schema: str = boundary.MIGRATION_SCHEMA
    scope: str = boundary.MIGRATION_SCOPE
    identity: str = boundary.TASK853_IDENTITY
    authenticated_predecessor_organism_tick: int = (
        boundary.TASK853_AUTHENTICATED_PREDECESSOR_TICK
    )
    organism_tick: int = boundary.TASK853_AUTHENTICATED_PREDECESSOR_TICK
    legacy_fabric_sha256: str = boundary.TASK853_GLMFAB03_SHA256.hex()
    fabric_bytes: int = boundary.EXPECTED_CURRENT_FABRIC_BYTES
    fabric_sha256: str = boundary.EXPECTED_CURRENT_FABRIC_SHA256
    fabric_generation: int = boundary.EXPECTED_FABRIC_GENERATION
    mounted_generation: int = boundary.EXPECTED_MOUNTED_GENERATION
    joint_field_count: int = boundary.EXPECTED_JOINT_FIELD_COUNT
    joint_neuron_count: int = boundary.EXPECTED_JOINT_NEURON_COUNT
    mounted_step_completed: bool = False
    physical_transition_claimed: bool = False
    cognitive_formation_claimed: bool = False
    python_callback_count: int = 0

    @property
    def state_bytes(self) -> int:
        return len(self.payload)

    @property
    def state_sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()

    def as_bytes(self) -> bytes:
        return self.payload


class _StructuralImpostor(_NativeResult):
    pass


class _Native:
    NativeAuthenticatedTask853RuntimeMigration = _NativeResult

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []

    def migrate_authenticated_task853_predecessor_to_native_organism_runtime(
        self,
        *values: object,
    ) -> object:
        self.calls.append(values)
        return self.result


def _admit_synthetic_predecessor(monkeypatch) -> bytes:
    predecessor = b"GLMFAB03-synthetic-authenticated-body"
    monkeypatch.setattr(boundary, "TASK853_GLMFAB03_BYTES", len(predecessor))
    monkeypatch.setattr(
        boundary,
        "TASK853_GLMFAB03_SHA256",
        hashlib.sha256(predecessor).digest(),
    )
    return predecessor


def test_boundary_calls_only_the_one_shot_native_migration(monkeypatch) -> None:
    predecessor = _admit_synthetic_predecessor(monkeypatch)
    native_result = _NativeResult(
        legacy_fabric_sha256=hashlib.sha256(predecessor).hexdigest()
    )
    native = _Native(native_result)
    monkeypatch.setattr(boundary, "_native_core", lambda: native)

    migrated = boundary.migrate_authenticated_task853_predecessor(
        legacy_glmfab03=predecessor
    )

    assert native.calls == [
        (
            predecessor,
            hashlib.sha256(predecessor).digest(),
            "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1",
            23_723_846,
            67_108_864,
            67_108_000,
            536_870_912,
        )
    ]
    assert isinstance(migrated, boundary.VerifiedTask853OrganismMigration)
    assert migrated.as_bytes() == native_result.payload
    assert migrated.as_bytes().startswith(b"GLORUN01")
    assert not hasattr(migrated, "fabric_bytes")
    assert not hasattr(migrated, "legacy_glmfab03")


def test_boundary_constants_bind_the_authenticated_task853_predecessor() -> None:
    assert boundary.TASK853_GLMFAB03_BYTES == 4_148_843
    assert boundary.TASK853_GLMFAB03_SHA256.hex() == (
        "b1f538e25d0bf59584266172ccb473b2b2db6ad7ddf1fc1f7ffa542bd2cc7e14"
    )
    assert boundary.TASK853_IDENTITY == "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
    assert boundary.TASK853_AUTHENTICATED_PREDECESSOR_TICK == 23_723_846


def test_rehearsal_ceilings_are_not_exported_as_resource_authority() -> None:
    assert "MAX_ENVELOPE_BYTES" not in boundary.__all__
    assert "MAX_FABRIC_BYTES" not in boundary.__all__
    assert "MAX_LOGICAL_PEAK_BYTES" not in boundary.__all__
    assert boundary.REHEARSAL_MAX_ENVELOPE_BYTES == 67_108_864
    assert boundary.REHEARSAL_MAX_FABRIC_BYTES == 67_108_000
    assert boundary.REHEARSAL_MAX_LOGICAL_PEAK_BYTES == 536_870_912


def test_boundary_refuses_unauthenticated_input_before_native_call(
    monkeypatch,
) -> None:
    native = _Native(_NativeResult())
    monkeypatch.setattr(boundary, "_native_core", lambda: native)

    with pytest.raises(ValueError, match="byte count is not authenticated"):
        boundary.migrate_authenticated_task853_predecessor(
            legacy_glmfab03=b"GLMFAB03-not-the-production-body"
        )

    assert native.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("payload", b"GLMFAB04-intermediate"),
        ("schema", "wrong"),
        ("scope", "wrong"),
        ("identity", "12345678-9abc-4def-8123-456789abcdef"),
        ("organism_tick", 23_723_847),
        ("fabric_sha256", "f" * 64),
        ("joint_neuron_count", 95),
        ("mounted_step_completed", True),
        ("physical_transition_claimed", True),
        ("cognitive_formation_claimed", True),
        ("python_callback_count", 1),
    ),
)
def test_boundary_refuses_intermediate_or_changed_native_results(
    monkeypatch,
    field: str,
    value: object,
) -> None:
    predecessor = _admit_synthetic_predecessor(monkeypatch)
    result = _NativeResult(
        legacy_fabric_sha256=hashlib.sha256(predecessor).hexdigest()
    )
    setattr(result, field, value)
    native = _Native(result)
    monkeypatch.setattr(boundary, "_native_core", lambda: native)

    with pytest.raises(
        RuntimeError,
        match="did not return one GLORUN01|changed its authenticated contract",
    ):
        boundary.migrate_authenticated_task853_predecessor(
            legacy_glmfab03=predecessor
        )

    assert len(native.calls) == 1


def test_boundary_refuses_structural_impostor(monkeypatch) -> None:
    predecessor = _admit_synthetic_predecessor(monkeypatch)
    result = _StructuralImpostor(
        legacy_fabric_sha256=hashlib.sha256(predecessor).hexdigest()
    )
    native = _Native(result)
    monkeypatch.setattr(boundary, "_native_core", lambda: native)

    with pytest.raises(TypeError, match="structural impostor"):
        boundary.migrate_authenticated_task853_predecessor(
            legacy_glmfab03=predecessor
        )

    assert len(native.calls) == 1


def test_boundary_refuses_missing_concrete_native_type(monkeypatch) -> None:
    predecessor = _admit_synthetic_predecessor(monkeypatch)

    class _MissingTypeNative:
        def migrate_authenticated_task853_predecessor_to_native_organism_runtime(
            self,
            *_values: object,
        ) -> object:
            raise AssertionError("migration must not run without concrete type")

    monkeypatch.setattr(boundary, "_native_core", _MissingTypeNative)
    with pytest.raises(RuntimeError, match="concrete native migration type"):
        boundary.migrate_authenticated_task853_predecessor(
            legacy_glmfab03=predecessor
        )
