"""Exact task-853 preflight for the raw native-organism binary store.

This test is dormant during ordinary unit runs because the authenticated
production predecessor is not a repository fixture.  Release preflight supplies
its explicit path and the freshly built native wheel, then exercises the real
migration, resident runtime, durable publication, and cold restore without a
mock native boundary.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.authenticated_task853_organism_migration import (
    REHEARSAL_MAX_ENVELOPE_BYTES,
    REHEARSAL_MAX_FABRIC_BYTES,
    REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
    TASK853_AUTHENTICATED_PREDECESSOR_TICK,
    TASK853_GLMFAB03_SHA256,
    TASK853_IDENTITY,
    migrate_authenticated_task853_predecessor,
)
from dsf_ai_service.glew_runtime.native_resident_organism import (
    restore_native_resident_organism,
)
from dsf_ai_service.substrate.native_organism_binary_store import (
    publish_staged_native_organism,
    restore_current_native_organism,
    stage_active_native_organism,
)


class _ExactMemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_if_absent(
        self,
        key: str,
        chunks,
        *,
        byte_count: int,
        sha256: str,
    ) -> bool:
        body = b"".join(chunks)
        assert len(body) == byte_count
        assert hashlib.sha256(body).hexdigest() == sha256
        prior = self.objects.get(key)
        if prior is not None:
            assert prior == body
            return False
        self.objects[key] = body
        return True

    def iter_bytes(self, key: str):
        body = self.objects[key]
        for offset in range(0, len(body), 65_536):
            yield body[offset : offset + 65_536]

    def delete_if_exact(
        self,
        key: str,
        *,
        byte_count: int,
        sha256: str,
    ) -> None:
        body = self.objects[key]
        assert len(body) == byte_count
        assert hashlib.sha256(body).hexdigest() == sha256
        del self.objects[key]


def test_exact_task853_migrates_publishes_and_cold_restores_raw_glorun(
    tmp_path: Path,
) -> None:
    predecessor_path = os.environ.get("GUALA_TASK853_GLMFAB03")
    if predecessor_path is None:
        pytest.skip("exact task-853 predecessor path was not supplied")

    predecessor = Path(predecessor_path).read_bytes()
    assert hashlib.sha256(predecessor).digest() == TASK853_GLMFAB03_SHA256
    migration = migrate_authenticated_task853_predecessor(
        legacy_glmfab03=predecessor
    )
    del predecessor

    organism = restore_native_resident_organism(
        current_envelope=migration.envelope,
        max_envelope_bytes=REHEARSAL_MAX_ENVELOPE_BYTES,
        max_fabric_bytes=REHEARSAL_MAX_FABRIC_BYTES,
        max_logical_peak_bytes=REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
    )
    remote = _ExactMemoryObjectStore()
    staged = stage_active_native_organism(
        tmp_path,
        organism,
        max_envelope_bytes=REHEARSAL_MAX_ENVELOPE_BYTES,
    )
    published = publish_staged_native_organism(
        staged,
        expected_predecessor_sha256=None,
        object_store=remote,
        max_envelope_bytes=REHEARSAL_MAX_ENVELOPE_BYTES,
        max_fabric_bytes=REHEARSAL_MAX_FABRIC_BYTES,
        max_logical_peak_bytes=REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
    )
    restored = restore_current_native_organism(
        tmp_path,
        max_envelope_bytes=REHEARSAL_MAX_ENVELOPE_BYTES,
        max_fabric_bytes=REHEARSAL_MAX_FABRIC_BYTES,
        max_logical_peak_bytes=REHEARSAL_MAX_LOGICAL_PEAK_BYTES,
    )

    observation = restored.organism.readiness()
    assert restored.pointer == published.pointer
    assert restored.organism.save() == migration.envelope
    assert published.pointer.identity == TASK853_IDENTITY
    assert observation.identity == TASK853_IDENTITY
    assert observation.organism_tick == TASK853_AUTHENTICATED_PREDECESSOR_TICK
    assert published.pointer.state_bytes == len(migration.envelope)
    assert published.pointer.state_sha256 == migration.state_sha256
    assert published.accounting.current_bytes == 0
    assert published.accounting.retained_predecessor_bytes == 0
    assert published.accounting.staged_bytes == len(migration.envelope)
    assert published.accounting.exact_peak_bytes == len(migration.envelope)
    assert list(remote.objects.values()) == [migration.envelope]
