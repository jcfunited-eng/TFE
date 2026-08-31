from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate.immutable_generation_store import (
    CURRENT_NAME,
    PHYSICAL_BYTE_CEILING_RECEIPT_NAME,
    PHYSICAL_BYTE_CEILING_SCHEMA,
    PHYSICAL_BYTE_STATUS_SCHEMA,
    GenerationValidationError,
    ImmutableGenerationStore,
    PhysicalByteCeilingError,
)


IDENTITY = "physical-byte-ceiling-test-ae"


def _store(
        scope: Path, *, ceiling: int,
        root_name: str = "live-recovery") -> ImmutableGenerationStore:
    return ImmutableGenerationStore(
        scope / root_name,
        identity=IDENTITY,
        required_files=("core.json",),
        physical_byte_ceiling=ceiling,
        physical_byte_scope=scope,
    )


def test_global_scope_counts_current_event_recovery_and_hardlinks_once(
        tmp_path: Path) -> None:
    scope = tmp_path / "physical-scope"
    active = scope / "active"
    retained = scope / "legacy-generations" / "one"
    recovery = scope / "other-recovery"
    active.mkdir(parents=True)
    retained.mkdir(parents=True)
    recovery.mkdir()
    current = active / "current-state.bin"
    current.write_bytes(b"c" * 100)
    (active / "session.events.jsonl").write_bytes(b"e" * 80)
    (recovery / "retained-generation.bin").write_bytes(b"r" * 70)
    os.link(current, retained / "hardlinked-current-state.bin")

    store = _store(scope, ceiling=600)
    receipt_path = scope / PHYSICAL_BYTE_CEILING_RECEIPT_NAME
    configured = json.loads(receipt_path.read_text(encoding="utf-8"))
    status = store.physical_byte_status()

    assert configured == {
        "schema": PHYSICAL_BYTE_CEILING_SCHEMA,
        "scope_root": str(scope.resolve()),
        "ceiling_bytes": 600,
        "accounting": "unique_regular_file_logical_bytes",
    }
    assert status is not None
    assert status["schema"] == PHYSICAL_BYTE_STATUS_SCHEMA
    assert status["used_bytes"] == 100 + 80 + 70 + receipt_path.stat().st_size
    assert status["remaining_bytes"] == 600 - status["used_bytes"]

    before = {
        path: path.read_bytes()
        for path in (
            current,
            active / "session.events.jsonl",
            recovery / "retained-generation.bin",
        )
    }
    with pytest.raises(PhysicalByteCeilingError) as captured:
        store.commit(tick=1, files={"core.json": b"{}"})

    refusal = captured.value.receipt
    assert refusal["operation"] == "allocate_prepared_generation"
    assert refusal["used_bytes"] == status["used_bytes"]
    assert refusal["remaining_bytes"] == status["remaining_bytes"]
    assert refusal["requested_bytes"] > refusal["remaining_bytes"]
    assert refusal["status"] == "refused"
    assert not tuple(store.generations_directory.glob(".building-*"))
    assert not (store.root / CURRENT_NAME).exists()
    assert all(path.read_bytes() == content for path, content in before.items())


def test_ceiling_receipt_and_exact_usage_survive_restart(
        tmp_path: Path) -> None:
    scope = tmp_path / "physical-scope"
    scope.mkdir()
    ceiling = 1_000_000
    first_store = _store(scope, ceiling=ceiling)
    first = first_store.commit(
        tick=1,
        files={"core.json": json.dumps({"learned": "first"}).encode()},
    )
    current_before = (first_store.root / CURRENT_NAME).read_bytes()
    status_before_fill = first_store.physical_byte_status()
    assert status_before_fill is not None
    filler = scope / "session.events.jsonl"
    filler.write_bytes(b"x" * (status_before_fill["remaining_bytes"] - 1))

    restarted = _store(scope, ceiling=ceiling)
    restarted_status = restarted.physical_byte_status()
    assert restarted_status is not None
    assert restarted_status["used_bytes"] == ceiling - 1
    assert restarted_status["remaining_bytes"] == 1

    with pytest.raises(PhysicalByteCeilingError) as captured:
        restarted.commit(
            tick=2,
            files={"core.json": json.dumps({"learned": "second"}).encode()},
        )

    refusal = captured.value.receipt
    assert refusal == restarted.last_physical_byte_receipt()
    assert refusal["used_bytes"] == ceiling - 1
    assert refusal["remaining_bytes"] == 1
    assert refusal["requested_bytes"] > 1
    assert (restarted.root / CURRENT_NAME).read_bytes() == current_before
    assert restarted.load_current().generation_uuid == first.generation_uuid
    assert first.directory.exists()
    assert filler.exists()


def test_external_growth_is_refused_before_generation_rename(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scope = tmp_path / "physical-scope"
    scope.mkdir()
    store = _store(scope, ceiling=50_000)
    first = store.commit(tick=1, files={"core.json": b'{"learned":"first"}'})
    current_before = (store.root / CURRENT_NAME).read_bytes()
    real_write_generation = store._write_generation_directory
    real_rename = os.rename
    generation_renames = []

    def write_then_fill_scope(building, prepared, manifest_bytes):
        real_write_generation(building, prepared, manifest_bytes)
        status = store.physical_byte_status()
        assert status is not None
        (scope / "late.events.jsonl").write_bytes(
            b"e" * (status["remaining_bytes"] + 1))

    def record_generation_rename(source, destination):
        if Path(source).name.startswith(".building-"):
            generation_renames.append((Path(source), Path(destination)))
        return real_rename(source, destination)

    monkeypatch.setattr(
        store, "_write_generation_directory", write_then_fill_scope)
    monkeypatch.setattr(os, "rename", record_generation_rename)

    with pytest.raises(PhysicalByteCeilingError) as captured:
        store.commit(tick=2, files={"core.json": b'{"learned":"second"}'})

    refusal = captured.value.receipt
    assert refusal["operation"] == "rename_prepared_generation"
    assert refusal["used_bytes"] == 50_001
    assert refusal["remaining_bytes"] == 0
    assert refusal["requested_bytes"] > 0
    assert not generation_renames
    assert not tuple(store.generations_directory.glob(".building-*"))
    assert (store.root / CURRENT_NAME).read_bytes() == current_before
    assert store.load_current().generation_uuid == first.generation_uuid
    assert (scope / "late.events.jsonl").exists()


def test_restart_rejects_a_different_ceiling_than_durable_receipt(
        tmp_path: Path) -> None:
    scope = tmp_path / "physical-scope"
    scope.mkdir()
    _store(scope, ceiling=10_000)

    with pytest.raises(
            GenerationValidationError,
            match="configuration differs from the durable scope receipt"):
        _store(scope, ceiling=10_001, root_name="second-store")
