from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from dsf_ai_service.substrate import (
    migration_live_recovery_cutover as cutover_module,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.live_recovery_generation import (
    LiveRecoveryGenerationStore,
)
from dsf_ai_service.substrate.migration_live_recovery_cutover import (
    MAX_INTENT_BYTES,
    MigrationLiveRecoveryCutoverError,
    publish_after_source_overlay_retirement,
    restore_source_after_destination_overlay_custody,
)
from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)


IDENTITY = "migration-live-recovery-cutover-ae"
HMAC_KEY = b"migration-live-recovery-cutover-test-key"
HOT_FILES = ("core.json", "owner_state/physical.json")


def _write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(
            json.dumps(value, sort_keys=True),
            encoding="utf-8",
        )
    return path


def _generation(
    tmp_path: Path,
    *,
    name: str,
    tick: int,
    core_value: str,
    owner_value: str,
    identity: str = IDENTITY,
):
    source = tmp_path / f"{name}-source"
    files = {
        "core.json": _write(
            source / "core.json",
            {"value": core_value},
        ),
        "owner_state/physical.json": _write(
            source / "owner_state/physical.json",
            owner_value,
        ),
        "cold.json": _write(
            source / "cold.json",
            {"generation": name},
        ),
    }
    store = ImmutableGenerationStore(
        tmp_path / f"{name}-store",
        identity=identity,
        required_files=tuple(files),
    )
    return store.commit(tick=tick, files=files)


def _overlay(
    tmp_path: Path,
    *,
    root: Path,
    baseline,
    tick: int,
    core_value: str,
    owner_value: str,
):
    sources = tmp_path / (
        f"overlay-{baseline.generation_uuid}-{tick}"
    )
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    generation = manager.commit_hot_state(
        tick=tick,
        files={
            "core.json": _write(
                sources / "core.json",
                {"value": core_value},
            ),
            "owner_state/physical.json": _write(
                sources / "owner_state/physical.json",
                owner_value,
            ),
        },
    )
    return manager, generation


def _authority(tmp_path: Path) -> PhysicalByteCeilingAuthority:
    return PhysicalByteCeilingAuthority(
        tmp_path,
        64 * 1024 * 1024,
    )


def test_handoff_retires_exact_source_overlay_before_publication(
    tmp_path: Path,
) -> None:
    source = _generation(
        tmp_path,
        name="source",
        tick=10,
        core_value="source",
        owner_value="source-owner",
    )
    destination = _generation(
        tmp_path,
        name="destination",
        tick=10,
        core_value="destination",
        owner_value="destination-owner",
    )
    root = tmp_path / "live-recovery"
    _manager, overlay = _overlay(
        tmp_path,
        root=root,
        baseline=source,
        tick=source.tick,
        core_value="source",
        owner_value="source-owner",
    )
    intent = tmp_path / "cutover-intent.json"
    publication_calls = []

    def _publish():
        assert not root.exists()
        publication_calls.append(True)
        return SimpleNamespace(generation=destination)

    result = publish_after_source_overlay_retirement(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        hmac_key=HMAC_KEY,
        physical_byte_authority=_authority(tmp_path),
        publish_destination=_publish,
    )

    assert publication_calls == [True]
    assert result.source_overlay_generation == overlay.generation_uuid
    assert result.destination_generation == destination.generation_uuid
    assert not root.exists()
    assert intent.stat().st_size <= MAX_INTENT_BYTES
    assert b"destination_published" in intent.read_bytes()


@pytest.mark.parametrize(
    ("tick", "core_value", "owner_value", "message"),
    (
        (11, "newer", "newer-owner", "newer"),
        (10, "source", "changed-owner", "differs"),
    ),
)
def test_handoff_refuses_divergent_overlay_before_publication(
    tmp_path: Path,
    tick: int,
    core_value: str,
    owner_value: str,
    message: str,
) -> None:
    source = _generation(
        tmp_path,
        name="source",
        tick=10,
        core_value="source",
        owner_value="source-owner",
    )
    root = tmp_path / "live-recovery"
    manager, overlay = _overlay(
        tmp_path,
        root=root,
        baseline=source,
        tick=tick,
        core_value=core_value,
        owner_value=owner_value,
    )
    called = []

    with pytest.raises(
        MigrationLiveRecoveryCutoverError,
        match=message,
    ):
        publish_after_source_overlay_retirement(
            live_recovery_root=root,
            intent_path=tmp_path / "cutover-intent.json",
            source=source,
            hmac_key=HMAC_KEY,
            physical_byte_authority=_authority(tmp_path),
            publish_destination=lambda: called.append(True),
        )

    assert called == []
    assert root.is_dir()
    assert (
        manager.load_current().recovery_certificate_bytes()
        == overlay.recovery_certificate_bytes()
    )


def test_failed_publication_leaves_source_safe_and_retryable(
    tmp_path: Path,
) -> None:
    source = _generation(
        tmp_path,
        name="source",
        tick=10,
        core_value="source",
        owner_value="source-owner",
    )
    destination = _generation(
        tmp_path,
        name="destination",
        tick=10,
        core_value="destination",
        owner_value="destination-owner",
    )
    root = tmp_path / "live-recovery"
    _overlay(
        tmp_path,
        root=root,
        baseline=source,
        tick=source.tick,
        core_value="source",
        owner_value="source-owner",
    )
    intent = tmp_path / "cutover-intent.json"
    authority = _authority(tmp_path)

    with pytest.raises(RuntimeError, match="injected publication failure"):
        publish_after_source_overlay_retirement(
            live_recovery_root=root,
            intent_path=intent,
            source=source,
            hmac_key=HMAC_KEY,
            physical_byte_authority=authority,
            publish_destination=lambda: (_ for _ in ()).throw(
                RuntimeError("injected publication failure")
            ),
        )

    assert not root.exists()
    assert b"source_overlay_retired" in intent.read_bytes()
    retried = publish_after_source_overlay_retirement(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        publish_destination=lambda: destination,
    )
    assert retried.destination_generation == destination.generation_uuid


def test_terminal_rollback_allows_next_distinct_sealed_source_handoff(
    tmp_path: Path,
) -> None:
    first_source = _generation(
        tmp_path,
        name="first-source",
        tick=10,
        core_value="first-source",
        owner_value="first-source-owner",
    )
    first_destination = _generation(
        tmp_path,
        name="first-destination",
        tick=10,
        core_value="first-destination",
        owner_value="first-destination-owner",
    )
    root = tmp_path / "live-recovery"
    _overlay(
        tmp_path,
        root=root,
        baseline=first_source,
        tick=first_source.tick,
        core_value="first-source",
        owner_value="first-source-owner",
    )
    intent = tmp_path / "cutover-intent.json"
    authority = _authority(tmp_path)
    publish_after_source_overlay_retirement(
        live_recovery_root=root,
        intent_path=intent,
        source=first_source,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        publish_destination=lambda: first_destination,
    )
    restored = restore_source_after_destination_overlay_custody(
        live_recovery_root=root,
        intent_path=intent,
        source=first_source,
        destination=first_destination,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        restore_source=lambda: first_source,
    )
    assert restored.overlay_disposition == "overlay_absent"
    assert b"source_restored" in intent.read_bytes()

    next_source = _generation(
        tmp_path,
        name="next-source",
        tick=11,
        core_value="next-source",
        owner_value="next-source-owner",
    )
    next_destination = _generation(
        tmp_path,
        name="next-destination",
        tick=11,
        core_value="next-destination",
        owner_value="next-destination-owner",
    )
    _overlay(
        tmp_path,
        root=root,
        baseline=next_source,
        tick=next_source.tick,
        core_value="next-source",
        owner_value="next-source-owner",
    )
    result = publish_after_source_overlay_retirement(
        live_recovery_root=root,
        intent_path=intent,
        source=next_source,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        publish_destination=lambda: next_destination,
    )

    assert result.destination_generation == (
        next_destination.generation_uuid
    )
    assert not root.exists()
    assert b"destination_published" in intent.read_bytes()


def test_terminal_rollback_allows_exact_same_source_corrected_retry(
    tmp_path: Path,
) -> None:
    source = _generation(
        tmp_path,
        name="source",
        tick=10,
        core_value="source",
        owner_value="source-owner",
    )
    rejected_destination = _generation(
        tmp_path,
        name="rejected-destination",
        tick=10,
        core_value="rejected-destination",
        owner_value="rejected-destination-owner",
    )
    corrected_destination = _generation(
        tmp_path,
        name="corrected-destination",
        tick=10,
        core_value="corrected-destination",
        owner_value="corrected-destination-owner",
    )
    root = tmp_path / "live-recovery"
    _manager, source_overlay = _overlay(
        tmp_path,
        root=root,
        baseline=source,
        tick=source.tick,
        core_value="source",
        owner_value="source-owner",
    )
    intent = tmp_path / "cutover-intent.json"
    authority = _authority(tmp_path)
    first = publish_after_source_overlay_retirement(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        publish_destination=lambda: rejected_destination,
    )
    assert first.source_overlay_generation == source_overlay.generation_uuid
    restored = restore_source_after_destination_overlay_custody(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        destination=rejected_destination,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        restore_source=lambda: source,
    )
    assert restored.overlay_disposition == "overlay_absent"
    assert restored.quarantined_path is None
    assert not root.exists()

    corrected = publish_after_source_overlay_retirement(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        publish_destination=lambda: corrected_destination,
    )

    assert corrected.source_overlay_generation == (
        source_overlay.generation_uuid
    )
    assert corrected.destination_generation == (
        corrected_destination.generation_uuid
    )
    assert corrected.destination_generation != (
        rejected_destination.generation_uuid
    )
    assert not root.exists()
    assert b"destination_published" in intent.read_bytes()


def test_same_source_retry_refuses_retained_destination_overlay_custody(
    tmp_path: Path,
) -> None:
    source = _generation(
        tmp_path,
        name="source",
        tick=10,
        core_value="source",
        owner_value="source-owner",
    )
    rejected_destination = _generation(
        tmp_path,
        name="rejected-destination",
        tick=10,
        core_value="rejected-destination",
        owner_value="rejected-destination-owner",
    )
    corrected_destination = _generation(
        tmp_path,
        name="corrected-destination",
        tick=10,
        core_value="corrected-destination",
        owner_value="corrected-destination-owner",
    )
    root = tmp_path / "live-recovery"
    _overlay(
        tmp_path,
        root=root,
        baseline=source,
        tick=source.tick,
        core_value="source",
        owner_value="source-owner",
    )
    intent = tmp_path / "cutover-intent.json"
    authority = _authority(tmp_path)
    publish_after_source_overlay_retirement(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        publish_destination=lambda: rejected_destination,
    )
    _overlay(
        tmp_path,
        root=root,
        baseline=rejected_destination,
        tick=rejected_destination.tick + 1,
        core_value="rejected-destination-newer",
        owner_value="rejected-destination-newer-owner",
    )
    restored = restore_source_after_destination_overlay_custody(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        destination=rejected_destination,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        restore_source=lambda: source,
    )
    assert restored.overlay_disposition == (
        "destination_overlay_quarantined"
    )
    publication_calls = []

    with pytest.raises(
        MigrationLiveRecoveryCutoverError,
        match="retains destination overlay custody",
    ):
        publish_after_source_overlay_retirement(
            live_recovery_root=root,
            intent_path=intent,
            source=source,
            hmac_key=HMAC_KEY,
            physical_byte_authority=authority,
            publish_destination=lambda: publication_calls.append(
                corrected_destination
            ),
        )

    assert publication_calls == []
    assert Path(restored.quarantined_path).is_dir()


def test_rollback_quarantines_destination_overlay_before_source_restore(
    tmp_path: Path,
) -> None:
    source = _generation(
        tmp_path,
        name="source",
        tick=10,
        core_value="source",
        owner_value="source-owner",
    )
    destination = _generation(
        tmp_path,
        name="destination",
        tick=10,
        core_value="destination",
        owner_value="destination-owner",
    )
    root = tmp_path / "live-recovery"
    _overlay(
        tmp_path,
        root=root,
        baseline=source,
        tick=source.tick,
        core_value="source",
        owner_value="source-owner",
    )
    intent = tmp_path / "cutover-intent.json"
    authority = _authority(tmp_path)
    publish_after_source_overlay_retirement(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        publish_destination=lambda: destination,
    )
    destination_manager, destination_overlay = _overlay(
        tmp_path,
        root=root,
        baseline=destination,
        tick=destination.tick + 1,
        core_value="destination-newer",
        owner_value="destination-newer-owner",
    )
    restore_calls = []

    def _restore():
        assert not root.exists()
        quarantine = tuple(
            tmp_path.glob(
                ".live-recovery.rollback-quarantine-*"
            )
        )
        assert len(quarantine) == 1
        restore_calls.append(True)
        return source

    result = restore_source_after_destination_overlay_custody(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        destination=destination,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        restore_source=_restore,
    )

    assert restore_calls == [True]
    assert result.overlay_disposition == (
        "destination_overlay_quarantined"
    )
    quarantine = Path(result.quarantined_path)
    assert quarantine.is_dir()
    quarantined_manager = LiveRecoveryGenerationStore(
        quarantine,
        baseline=destination,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    assert (
        quarantined_manager.load_current().recovery_certificate_bytes()
        == destination_overlay.recovery_certificate_bytes()
    )
    assert destination_manager.root != quarantine
    assert b"source_restored" in intent.read_bytes()


def test_rollback_refuses_overlay_from_unknown_baseline(
    tmp_path: Path,
) -> None:
    source = _generation(
        tmp_path,
        name="source",
        tick=10,
        core_value="source",
        owner_value="source-owner",
    )
    destination = _generation(
        tmp_path,
        name="destination",
        tick=10,
        core_value="destination",
        owner_value="destination-owner",
    )
    unknown = _generation(
        tmp_path,
        name="unknown",
        tick=10,
        core_value="unknown",
        owner_value="unknown-owner",
    )
    root = tmp_path / "live-recovery"
    manager, overlay = _overlay(
        tmp_path,
        root=root,
        baseline=unknown,
        tick=unknown.tick + 1,
        core_value="unknown-newer",
        owner_value="unknown-newer-owner",
    )
    called = []

    with pytest.raises(
        MigrationLiveRecoveryCutoverError,
        match="neither source nor destination",
    ):
        restore_source_after_destination_overlay_custody(
            live_recovery_root=root,
            intent_path=tmp_path / "cutover-intent.json",
            source=source,
            destination=destination,
            hmac_key=HMAC_KEY,
            physical_byte_authority=_authority(tmp_path),
            restore_source=lambda: called.append(True),
        )

    assert called == []
    assert root.is_dir()
    assert (
        manager.load_current().recovery_certificate_bytes()
        == overlay.recovery_certificate_bytes()
    )


def test_rollback_preserves_authenticated_source_overlay(
    tmp_path: Path,
) -> None:
    source = _generation(
        tmp_path,
        name="source",
        tick=10,
        core_value="source",
        owner_value="source-owner",
    )
    destination = _generation(
        tmp_path,
        name="destination",
        tick=10,
        core_value="destination",
        owner_value="destination-owner",
    )
    root = tmp_path / "live-recovery"
    manager, overlay = _overlay(
        tmp_path,
        root=root,
        baseline=source,
        tick=source.tick,
        core_value="source",
        owner_value="source-owner",
    )
    called = []

    def _restore():
        assert root.is_dir()
        called.append(True)
        return source

    result = restore_source_after_destination_overlay_custody(
        live_recovery_root=root,
        intent_path=tmp_path / "cutover-intent.json",
        source=source,
        destination=destination,
        hmac_key=HMAC_KEY,
        physical_byte_authority=_authority(tmp_path),
        restore_source=_restore,
    )

    assert called == [True]
    assert result.overlay_disposition == "source_overlay_preserved"
    assert (
        manager.load_current().recovery_certificate_bytes()
        == overlay.recovery_certificate_bytes()
    )
    assert not tuple(
        tmp_path.glob(".live-recovery.rollback-quarantine-*")
    )


def test_failed_restore_preserves_quarantine_and_is_retryable(
    tmp_path: Path,
) -> None:
    source = _generation(
        tmp_path,
        name="source",
        tick=10,
        core_value="source",
        owner_value="source-owner",
    )
    destination = _generation(
        tmp_path,
        name="destination",
        tick=10,
        core_value="destination",
        owner_value="destination-owner",
    )
    root = tmp_path / "live-recovery"
    _overlay(
        tmp_path,
        root=root,
        baseline=source,
        tick=source.tick,
        core_value="source",
        owner_value="source-owner",
    )
    intent = tmp_path / "cutover-intent.json"
    authority = _authority(tmp_path)
    publish_after_source_overlay_retirement(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        publish_destination=lambda: destination,
    )
    _manager, destination_overlay = _overlay(
        tmp_path,
        root=root,
        baseline=destination,
        tick=destination.tick + 1,
        core_value="destination-newer",
        owner_value="destination-newer-owner",
    )

    with pytest.raises(RuntimeError, match="injected restore failure"):
        restore_source_after_destination_overlay_custody(
            live_recovery_root=root,
            intent_path=intent,
            source=source,
            destination=destination,
            hmac_key=HMAC_KEY,
            physical_byte_authority=authority,
            restore_source=lambda: (_ for _ in ()).throw(
                RuntimeError("injected restore failure")
            ),
        )

    quarantine = tuple(
        tmp_path.glob(".live-recovery.rollback-quarantine-*")
    )
    assert len(quarantine) == 1
    assert not root.exists()
    retried = restore_source_after_destination_overlay_custody(
        live_recovery_root=root,
        intent_path=intent,
        source=source,
        destination=destination,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
        restore_source=lambda: source,
    )
    assert retried.quarantined_path == str(quarantine[0])
    manager = LiveRecoveryGenerationStore(
        quarantine[0],
        baseline=destination,
        hot_files=HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    assert (
        manager.load_current().recovery_certificate_bytes()
        == destination_overlay.recovery_certificate_bytes()
    )
