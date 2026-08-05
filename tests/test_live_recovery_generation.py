from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from dsf_ai_service.substrate.immutable_generation_store import (
    CONTENT_CHUNKS_DIRECTORY,
    CURRENT_NAME,
    GENERATIONS_DIRECTORY,
    MANIFEST_NAME,
    ImmutableGenerationStore,
    PhysicalByteCeilingError,
)
from dsf_ai_service.substrate.live_recovery_generation import (
    LIVE_RECOVERY_LINEAGE_FILE,
    LiveRecoveryError,
    LiveRecoveryGenerationStore,
)
from dsf_ai_service.substrate import live_recovery_generation as live_module
from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)
from dsf_ai_service.substrate.production_storage_profile import (
    ProductionStorageProfile,
)


IDENTITY = "live-recovery-test-ae"
HMAC_KEY = b"live-recovery-test-key-material-32-bytes"
HOT_FILES = ("core.json", "teaching.json")


def _json_file(path: Path, value) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _baseline(tmp_path: Path, *, tick: int = 10):
    source = tmp_path / f"baseline-source-{tick}"
    source.mkdir()
    files = {
        "core.json": _json_file(source / "core.json", {"tick": tick}),
        "teaching.json": _json_file(
            source / "teaching.json", {"classes": []}),
        "cold.json": _json_file(source / "cold.json", {"atlas": "preserved"}),
    }
    store = ImmutableGenerationStore(
        tmp_path / f"baseline-store-{tick}",
        identity=IDENTITY,
        required_files=tuple(files),
    )
    return store.commit(tick=tick, files=files)


def _hot_sources(tmp_path: Path, *, tick: int, label: str):
    source = tmp_path / f"hot-{tick}-{label}"
    source.mkdir()
    return {
        "core.json": _json_file(source / "core.json", {"tick": tick}),
        "teaching.json": _json_file(
            source / "teaching.json", {"classes": [label]}),
    }


def _stateful_baseline(tmp_path: Path, *, tick: int = 10):
    source = tmp_path / f"stateful-baseline-source-{tick}"
    source.mkdir()
    ticks = {
        "cold.json": tick,
        "core.json": tick,
        "teaching.json": tick,
    }
    files = {
        "core.json": _json_file(
            source / "core.json",
            {"data": {"tick": tick, "state_file_ticks": ticks}},
        ),
        "teaching.json": _json_file(
            source / "teaching.json",
            {"saved_at_tick": tick, "data": {"classes": []}},
        ),
        "cold.json": _json_file(
            source / "cold.json",
            {"saved_at_tick": tick, "data": {"atlas": "preserved"}},
        ),
    }
    store = ImmutableGenerationStore(
        tmp_path / f"stateful-baseline-store-{tick}",
        identity=IDENTITY,
        required_files=tuple(files),
    )
    return store.commit(tick=tick, files=files)


def _stateful_hot_sources(
        tmp_path: Path, *, tick: int, baseline_tick: int,
        cold_dependency_tick: int):
    source = tmp_path / f"stateful-hot-{tick}-{cold_dependency_tick}"
    source.mkdir()
    ticks = {
        "cold.json": cold_dependency_tick,
        "core.json": tick,
        "teaching.json": tick,
    }
    return {
        "core.json": _json_file(
            source / "core.json",
            {"data": {"tick": tick, "state_file_ticks": ticks}},
        ),
        "teaching.json": _json_file(
            source / "teaching.json",
            {
                "saved_at_tick": tick,
                "data": {
                    "classes": [f"baseline-{baseline_tick}"],
                },
            },
        ),
    }


def test_live_profile_uses_the_same_total_encoded_store_ceiling_as_cold(
        tmp_path) -> None:
    profile = ProductionStorageProfile.from_environment({
        "GUALA_MAX_COLD_GENERATION_BYTES": "8192",
    })
    manager = LiveRecoveryGenerationStore(
        tmp_path / "bounded-live",
        baseline=_baseline(tmp_path),
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
        max_encoded_generation_bytes=(
            profile.max_live_recovery_generation_bytes),
    )
    immutable_store = manager._store()

    assert profile.max_live_recovery_generation_bytes == 8192
    assert immutable_store.max_encoded_generation_bytes == 8192
    assert immutable_store.required_files == manager.required_files
    assert LIVE_RECOVERY_LINEAGE_FILE in immutable_store.required_files


def test_initialized_empty_content_addressed_store_has_no_current(
        tmp_path) -> None:
    manager = LiveRecoveryGenerationStore(
        tmp_path / "initialized-empty-live",
        baseline=_baseline(tmp_path),
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )

    manager._store()

    assert manager.load_current() is None


def test_verified_live_current_applies_only_declared_hot_state(tmp_path) -> None:
    baseline = _baseline(tmp_path)
    active = tmp_path / "active"
    active.mkdir()
    _json_file(active / "core.json", {"tick": 10})
    _json_file(active / "teaching.json", {"classes": []})
    _json_file(active / "cold.json", {"atlas": "preserved"})
    manager = LiveRecoveryGenerationStore(
        tmp_path / "live",
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )

    assert manager.apply_current(active) is None
    committed = manager.commit_hot_state(
        tick=11, files=_hot_sources(tmp_path, tick=11, label="hello"))
    materialized = manager.apply_current(active)

    assert materialized is not None
    assert materialized.generation_uuid == committed.generation_uuid
    assert materialized.tick == 11
    assert json.loads((active / "core.json").read_text()) == {"tick": 11}
    assert json.loads((active / "teaching.json").read_text()) == {
        "classes": ["hello"]}
    assert json.loads((active / "cold.json").read_text()) == {
        "atlas": "preserved"}
    lineage = committed.payload(LIVE_RECOVERY_LINEAGE_FILE)
    assert lineage["baseline_generation_uuid"] == baseline.generation_uuid
    assert lineage["baseline_manifest_sha256"] == baseline.manifest_sha256


def test_authorized_live_overlay_failure_restores_every_prior_hot_file(
        tmp_path, monkeypatch) -> None:
    baseline = _baseline(tmp_path)
    active = tmp_path / "active-rollback"
    active.mkdir()
    prior = {
        "core.json": b'{"tick":10}',
        "teaching.json": b'{"classes":[]}',
    }
    for relative, data in prior.items():
        (active / relative).write_bytes(data)
    manager = LiveRecoveryGenerationStore(
        tmp_path / "live-rollback",
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    manager.commit_hot_state(
        tick=11,
        files=_hot_sources(tmp_path, tick=11, label="rollback"),
    )
    authority = PhysicalByteCeilingAuthority(tmp_path, 1_000_000)
    real_rename = live_module.os.rename

    def reject_second_hot_file(source, destination, **kwargs):
        if (
            ".teaching.json." in str(source)
            and str(source).endswith(".live-recovery.tmp")
        ):
            raise OSError("injected hot overlay activation failure")
        return real_rename(source, destination, **kwargs)

    monkeypatch.setattr(live_module.os, "rename", reject_second_hot_file)
    with pytest.raises(
            OSError,
            match="injected hot overlay activation failure"):
        manager.apply_current(
            active,
            physical_byte_authority=authority,
        )

    assert {
        relative: (active / relative).read_bytes()
        for relative in prior
    } == prior
    assert not tuple(active.glob(".*.live-recovery.*"))


def test_failed_commit_preserves_prior_current_pointer(
        tmp_path, monkeypatch) -> None:
    baseline = _baseline(tmp_path)
    root = tmp_path / "live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    first = manager.commit_hot_state(
        tick=11, files=_hot_sources(tmp_path, tick=11, label="first"))
    prior_pointer = (root / CURRENT_NAME).read_bytes()
    original = ImmutableGenerationStore._write_current

    def reject_new_current(self, loaded):
        if loaded.generation_uuid != first.generation_uuid:
            raise RuntimeError("injected CURRENT publication failure")
        return original(self, loaded)

    monkeypatch.setattr(
        ImmutableGenerationStore, "_write_current", reject_new_current)
    with pytest.raises(RuntimeError, match="publication failure"):
        manager.commit_hot_state(
            tick=12, files=_hot_sources(tmp_path, tick=12, label="second"))

    assert (root / CURRENT_NAME).read_bytes() == prior_pointer
    assert manager.load_current().generation_uuid == first.generation_uuid


def test_failed_commit_preserves_current_and_predecessor(
        tmp_path, monkeypatch) -> None:
    baseline = _baseline(tmp_path)
    root = tmp_path / "live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
        keep_generations=2,
    )
    manager.commit_hot_state(
        tick=11,
        files=_hot_sources(tmp_path, tick=11, label="first"),
    )
    current = manager.commit_hot_state(
        tick=12,
        files=_hot_sources(tmp_path, tick=12, label="second"),
    )
    generations = root / GENERATIONS_DIRECTORY
    before = {path.name for path in generations.iterdir()}
    original = ImmutableGenerationStore._write_current

    def reject_new_current(self, loaded):
        if loaded.generation_uuid != current.generation_uuid:
            raise RuntimeError("injected CURRENT publication failure")
        return original(self, loaded)

    monkeypatch.setattr(
        ImmutableGenerationStore,
        "_write_current",
        reject_new_current,
    )
    with pytest.raises(RuntimeError, match="publication failure"):
        manager.commit_hot_state(
            tick=13,
            files=_hot_sources(tmp_path, tick=13, label="third"),
        )

    assert {path.name for path in generations.iterdir()} == before
    assert manager.load_current().generation_uuid == current.generation_uuid


@pytest.mark.parametrize("invalid_tick", [11.9, "11", True])
def test_hot_commit_rejects_noninteger_tick_without_coercion(
        tmp_path, invalid_tick) -> None:
    baseline = _baseline(tmp_path)
    root = tmp_path / "live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )

    with pytest.raises(LiveRecoveryError, match="tick must be an integer"):
        manager.commit_hot_state(
            tick=invalid_tick,
            files=_hot_sources(tmp_path, tick=11, label="invalid"),
        )

    assert not (root / CURRENT_NAME).exists()


def test_newer_full_seal_cannot_infer_that_it_contains_an_older_overlay(
        tmp_path) -> None:
    baseline = _baseline(tmp_path, tick=10)
    root = tmp_path / "live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    manager.commit_hot_state(
        tick=11, files=_hot_sources(tmp_path, tick=11, label="old-live"))
    newer_baseline = SimpleNamespace(
        generation_uuid="d9f5412b-1c11-4ef7-96d4-c4aac2a14f13",
        identity=IDENTITY,
        tick=12,
        manifest_sha256="a" * 64,
    )
    replacement = LiveRecoveryGenerationStore(
        root,
        baseline=newer_baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )

    with pytest.raises(LiveRecoveryError, match="cannot precede"):
        replacement.load_current()


def test_deployment_rebase_advances_lineage_after_complete_commit(tmp_path) -> None:
    baseline = _baseline(tmp_path, tick=10)
    root = tmp_path / "live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    first = manager.commit_hot_state(
        tick=11, files=_hot_sources(tmp_path, tick=11, label="old-live"))
    newer_baseline = SimpleNamespace(
        generation_uuid="d9f5412b-1c11-4ef7-96d4-c4aac2a14f13",
        identity=IDENTITY,
        tick=12,
        manifest_sha256="a" * 64,
    )
    rebased = manager.rebase_after_deployment_seal(
        baseline=newer_baseline,
        tick=12,
        files={
            name: json.dumps(value).encode("utf-8")
            for name, value in {
                "core.json": {"tick": 12},
                "teaching.json": {"classes": ["old-live"]},
            }.items()
        },
    )

    assert rebased.generation_uuid != first.generation_uuid
    assert manager.load_current().generation_uuid == rebased.generation_uuid
    lineage = rebased.payload(LIVE_RECOVERY_LINEAGE_FILE)
    assert lineage["baseline_generation_uuid"] == newer_baseline.generation_uuid


def test_deployment_rebase_rejects_noninteger_tick_without_coercion(
        tmp_path) -> None:
    baseline = _baseline(tmp_path, tick=10)
    root = tmp_path / "live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    current = manager.commit_hot_state(
        tick=11,
        files=_hot_sources(tmp_path, tick=11, label="old-live"),
    )
    newer_baseline = _baseline(tmp_path, tick=12)

    with pytest.raises(LiveRecoveryError, match="tick must be an integer"):
        manager.rebase_after_deployment_seal(
            baseline=newer_baseline,
            tick=12.5,
            files=_hot_sources(tmp_path, tick=12, label="new-baseline"),
        )

    assert manager.load_current().generation_uuid == current.generation_uuid


def test_overlay_ahead_of_different_baseline_halts(tmp_path) -> None:
    baseline = _baseline(tmp_path, tick=10)
    root = tmp_path / "live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    manager.commit_hot_state(
        tick=12, files=_hot_sources(tmp_path, tick=12, label="ahead"))
    older_different_baseline = SimpleNamespace(
        generation_uuid="3d38cc14-5705-4db3-9456-c72ff610b95a",
        identity=IDENTITY,
        tick=11,
        manifest_sha256="b" * 64,
    )
    replacement = LiveRecoveryGenerationStore(
        root,
        baseline=older_different_baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )

    with pytest.raises(LiveRecoveryError, match="does not name"):
        replacement.load_current()


def test_live_recovery_retention_is_bounded(tmp_path) -> None:
    baseline = _baseline(tmp_path)
    root = tmp_path / "live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
        keep_generations=3,
    )
    for tick in range(11, 17):
        manager.commit_hot_state(
            tick=tick,
            files=_hot_sources(tmp_path, tick=tick, label=str(tick)),
        )

    generations = root / GENERATIONS_DIRECTORY
    assert len(tuple(generations.iterdir())) <= 3
    assert manager.load_current().tick == 16


def test_live_recovery_content_addresses_unchanged_large_hot_bodies(
        tmp_path) -> None:
    baseline = _baseline(tmp_path)
    root = tmp_path / "content-addressed-live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
        keep_generations=3,
        max_encoded_generation_bytes=64 * 1024 * 1024,
    )
    source = tmp_path / "large-hot-source"
    source.mkdir()
    hot = {
        "core.json": _json_file(source / "core.json", {"tick": 11}),
        "teaching.json": _json_file(
            source / "teaching.json",
            {"classes": ["t" * (7 * 1024 * 1024)]},
        ),
    }

    generations = [
        manager.commit_hot_state(tick=tick, files=hot)
        for tick in (11, 12, 13)
    ]
    teaching_chunks = []
    for generation in generations:
        record = next(
            item
            for item in generation.recovery_certificate()[
                "required_files"
            ]
            if item["relative_path"] == "teaching.json"
        )
        teaching_chunks.append(record["chunks"])
        assert {
            path.name
            for path in generation.directory.iterdir()
        } == {MANIFEST_NAME}

    assert teaching_chunks[1:] == teaching_chunks[:-1]
    addressed = tuple(
        path
        for path in (
            root / CONTENT_CHUNKS_DIRECTORY
        ).rglob("*")
        if path.is_file()
    )
    addressed_digests = {path.name for path in addressed}
    assert all(
        chunk["sha256"] in addressed_digests
        for chunk in teaching_chunks[0]
    )
    assert sum(
        1
        for path in addressed
        if path.name in {
            chunk["sha256"] for chunk in teaching_chunks[0]
        }
    ) == len(teaching_chunks[0])


def test_live_recovery_commit_uses_shared_physical_byte_ceiling(
        tmp_path) -> None:
    baseline = _baseline(tmp_path)
    scope = tmp_path / "shared-physical-scope"
    scope.mkdir()
    root = scope / "live"
    active = scope / "active"
    active.mkdir()
    (active / "events.log").write_bytes(b"history")
    ceiling = 1_000_000
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
        max_encoded_generation_bytes=ceiling,
        physical_byte_ceiling=ceiling,
        physical_byte_scope=scope,
    )
    first = manager.commit_hot_state(
        tick=11,
        files=_hot_sources(tmp_path, tick=11, label="first"),
    )
    status = manager.physical_byte_status()
    assert status is not None
    filler = active / "continued.events.log"
    filler.write_bytes(b"x" * (status["remaining_bytes"] - 1))

    restarted = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
        max_encoded_generation_bytes=ceiling,
        physical_byte_ceiling=ceiling,
        physical_byte_scope=scope,
    )
    with pytest.raises(PhysicalByteCeilingError) as captured:
        restarted.commit_hot_state(
            tick=12,
            files=_hot_sources(tmp_path, tick=12, label="second"),
        )

    assert captured.value.receipt["remaining_bytes"] == 1
    assert restarted.load_current().generation_uuid == first.generation_uuid
    assert filler.exists()


def test_hot_generation_must_retain_exact_cold_baseline_dependency(
        tmp_path) -> None:
    baseline = _stateful_baseline(tmp_path, tick=10)
    root = tmp_path / "stateful-live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
        state_file_tick_manifest="core.json",
    )

    committed = manager.commit_hot_state(
        tick=11,
        files=_stateful_hot_sources(
            tmp_path,
            tick=11,
            baseline_tick=10,
            cold_dependency_tick=10,
        ),
    )

    assert manager.load_current().generation_uuid == committed.generation_uuid


def test_unpublished_cold_dependency_is_rejected_before_current_changes(
        tmp_path) -> None:
    baseline = _stateful_baseline(tmp_path, tick=10)
    root = tmp_path / "stateful-live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
        state_file_tick_manifest="core.json",
    )

    with pytest.raises(
            LiveRecoveryError,
            match="cold state not contained"):
        manager.commit_hot_state(
            tick=12,
            files=_stateful_hot_sources(
                tmp_path,
                tick=12,
                baseline_tick=10,
                cold_dependency_tick=11,
            ),
        )

    assert not (root / CURRENT_NAME).exists()


def test_rebase_changes_the_cold_dependency_for_subsequent_hot_commits(
        tmp_path) -> None:
    baseline = _stateful_baseline(tmp_path, tick=10)
    root = tmp_path / "stateful-live-rebase"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
        state_file_tick_manifest="core.json",
    )
    manager.commit_hot_state(
        tick=11,
        files=_stateful_hot_sources(
            tmp_path,
            tick=11,
            baseline_tick=10,
            cold_dependency_tick=10,
        ),
    )
    newer_baseline = _stateful_baseline(tmp_path, tick=12)
    manager.rebase_after_deployment_seal(
        baseline=newer_baseline,
        tick=12,
        files=_stateful_hot_sources(
            tmp_path,
            tick=12,
            baseline_tick=12,
            cold_dependency_tick=12,
        ),
    )

    committed = manager.commit_hot_state(
        tick=13,
        files=_stateful_hot_sources(
            tmp_path,
            tick=13,
            baseline_tick=12,
            cold_dependency_tick=12,
        ),
    )

    assert manager.load_current().generation_uuid == committed.generation_uuid
