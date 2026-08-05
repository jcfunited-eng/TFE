from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.live_recovery_generation import (
    LiveRecoveryError,
    LiveRecoveryGenerationStore,
    retire_redundant_predecessor_current,
)
from dsf_ai_service.substrate import live_recovery_generation as live_module
from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)


IDENTITY = "nested-live-recovery-test-ae"
HMAC_KEY = b"nested-live-recovery-test-key-material-32-bytes"
NESTED_HOT_FILES = (
    "core.json",
    "owner_state/causal_relation.state",
    "owner_state/mosaic.json",
)


def _write(path: Path, body: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def _json(path: Path, value: object) -> Path:
    return _write(
        path,
        json.dumps(value, sort_keys=True).encode("utf-8"),
    )


def _baseline(tmp_path: Path):
    source = tmp_path / "nested-baseline-source"
    files = {
        "core.json": _json(source / "core.json", {"tick": 10}),
        "owner_state/causal_relation.state": _write(
            source / "owner_state/causal_relation.state",
            b"prior-causal-relation",
        ),
        "owner_state/mosaic.json": _json(
            source / "owner_state/mosaic.json",
            {"mosaics": []},
        ),
        "cold.json": _json(source / "cold.json", {"preserved": True}),
    }
    store = ImmutableGenerationStore(
        tmp_path / "nested-baseline-store",
        identity=IDENTITY,
        required_files=tuple(files),
    )
    return store.commit(tick=10, files=files)


def _hot_sources(tmp_path: Path):
    source = tmp_path / "nested-hot-source"
    return {
        "core.json": _json(source / "core.json", {"tick": 11}),
        "owner_state/causal_relation.state": _write(
            source / "owner_state/causal_relation.state",
            b"grown-causal-relation",
        ),
        "owner_state/mosaic.json": _json(
            source / "owner_state/mosaic.json",
            {"mosaics": [{"sequence": 1}]},
        ),
    }


def _materialized_baseline(tmp_path: Path) -> Path:
    active = tmp_path / "active"
    _json(active / "core.json", {"tick": 10})
    _write(
        active / "owner_state/causal_relation.state",
        b"prior-causal-relation",
    )
    _json(active / "owner_state/mosaic.json", {"mosaics": []})
    _json(active / "cold.json", {"preserved": True})
    return active


def _manager(tmp_path: Path) -> LiveRecoveryGenerationStore:
    return LiveRecoveryGenerationStore(
        tmp_path / "nested-live",
        baseline=_baseline(tmp_path),
        hot_files=NESTED_HOT_FILES,
        hmac_key=HMAC_KEY,
    )


def _stateful_nested_baseline(tmp_path: Path):
    source = tmp_path / "stateful-nested-baseline-source"
    ticks = {
        "cold.json": 10,
        "core.json": 10,
        "owner_state/causal_relation.state": 10,
        "owner_state/mosaic.json": 10,
    }
    files = {
        "core.json": _json(
            source / "core.json",
            {"data": {"state_file_ticks": ticks}},
        ),
        "owner_state/causal_relation.state": _write(
            source / "owner_state/causal_relation.state",
            b"prior-causal-relation",
        ),
        "owner_state/mosaic.json": _json(
            source / "owner_state/mosaic.json",
            {"mosaics": []},
        ),
        "cold.json": _json(source / "cold.json", {"preserved": True}),
    }
    return ImmutableGenerationStore(
        tmp_path / "stateful-nested-baseline-store",
        identity=IDENTITY,
        required_files=tuple(files),
    ).commit(tick=10, files=files)


def test_nested_json_and_binary_owner_state_apply_exactly(tmp_path) -> None:
    active = _materialized_baseline(tmp_path)
    manager = _manager(tmp_path)
    committed = manager.commit_hot_state(
        tick=11,
        files=_hot_sources(tmp_path),
    )

    applied = manager.apply_current(active)

    assert applied is not None
    assert applied.generation_uuid == committed.generation_uuid
    assert json.loads((active / "core.json").read_text()) == {"tick": 11}
    assert (
        active / "owner_state/causal_relation.state"
    ).read_bytes() == b"grown-causal-relation"
    assert json.loads(
        (active / "owner_state/mosaic.json").read_text()
    ) == {"mosaics": [{"sequence": 1}]}
    assert json.loads((active / "cold.json").read_text()) == {
        "preserved": True,
    }


def test_owner_state_json_restores_exact_canonical_bytes_for_core_hash(
        tmp_path) -> None:
    baseline = _baseline(tmp_path)
    active = _materialized_baseline(tmp_path)
    owner_body = json.dumps(
        {
            "owner_id": "mosaic",
            "schema": "guala.owner_state_body.v1",
            "state": {"mosaics": [{"felt": "piñata"}]},
        },
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    core = {
        "data": {
            "owner_state": {
                "owner_state/mosaic.json": {
                    "bytes": len(owner_body),
                    "sha256": hashlib.sha256(owner_body).hexdigest(),
                },
            },
            "state_file_ticks": {
                "core.json": 11,
                "owner_state/causal_relation.state": 11,
                "owner_state/mosaic.json": 11,
            },
        },
    }
    source = tmp_path / "canonical-owner-hot-source"
    files = {
        "core.json": _json(source / "core.json", core),
        "owner_state/causal_relation.state": _write(
            source / "owner_state/causal_relation.state",
            b"grown-causal-relation",
        ),
        "owner_state/mosaic.json": _write(
            source / "owner_state/mosaic.json",
            owner_body,
        ),
    }
    manager = LiveRecoveryGenerationStore(
        tmp_path / "canonical-owner-live",
        baseline=baseline,
        hot_files=NESTED_HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    manager.commit_hot_state(tick=11, files=files)

    manager.apply_current(active)

    restored = (active / "owner_state/mosaic.json").read_bytes()
    restored_core_bytes = (active / "core.json").read_bytes()
    restored_core = json.loads((active / "core.json").read_text())
    measurement = restored_core["data"]["owner_state"][
        "owner_state/mosaic.json"
    ]
    assert restored_core_bytes == (source / "core.json").read_bytes()
    assert restored == owner_body
    assert len(restored) == measurement["bytes"]
    assert hashlib.sha256(restored).hexdigest() == measurement["sha256"]


def test_exact_redundant_predecessor_overlay_is_retired(tmp_path) -> None:
    baseline = _baseline(tmp_path)
    root = tmp_path / "redundant-predecessor-live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=NESTED_HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    source = tmp_path / "redundant-predecessor-source"
    manager.commit_hot_state(
        tick=baseline.tick,
        files={
            "core.json": _json(source / "core.json", {"tick": 10}),
            "owner_state/causal_relation.state": _write(
                source / "owner_state/causal_relation.state",
                b"prior-causal-relation",
            ),
            "owner_state/mosaic.json": _json(
                source / "owner_state/mosaic.json",
                {"mosaics": []},
            ),
        },
    )
    authority = PhysicalByteCeilingAuthority(
        tmp_path,
        10 * 1024 * 1024,
    )

    retired = retire_redundant_predecessor_current(
        root,
        baseline=baseline,
        hmac_key=HMAC_KEY,
        physical_byte_authority=authority,
    )

    assert len(retired) == 1
    assert not root.exists()
    assert not tuple(
        tmp_path.glob(".redundant-predecessor-live.redundant-*")
    )


def test_changed_predecessor_overlay_is_preserved_and_refused(
        tmp_path) -> None:
    baseline = _baseline(tmp_path)
    root = tmp_path / "changed-predecessor-live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=NESTED_HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    manager.commit_hot_state(
        tick=baseline.tick + 1,
        files=_hot_sources(tmp_path),
    )
    authority = PhysicalByteCeilingAuthority(
        tmp_path,
        10 * 1024 * 1024,
    )

    with pytest.raises(
            LiveRecoveryError,
            match="newer than its sealed baseline"):
        retire_redundant_predecessor_current(
            root,
            baseline=baseline,
            hmac_key=HMAC_KEY,
            physical_byte_authority=authority,
        )

    assert root.exists()
    assert manager.load_current().tick == baseline.tick + 1


def test_same_tick_changed_predecessor_overlay_is_preserved_and_refused(
        tmp_path) -> None:
    baseline = _baseline(tmp_path)
    root = tmp_path / "same-tick-changed-predecessor-live"
    manager = LiveRecoveryGenerationStore(
        root,
        baseline=baseline,
        hot_files=NESTED_HOT_FILES,
        hmac_key=HMAC_KEY,
    )
    source = tmp_path / "same-tick-changed-predecessor-source"
    manager.commit_hot_state(
        tick=baseline.tick,
        files={
            "core.json": _json(source / "core.json", {"tick": 10}),
            "owner_state/causal_relation.state": _write(
                source / "owner_state/causal_relation.state",
                b"changed-causal-relation",
            ),
            "owner_state/mosaic.json": _json(
                source / "owner_state/mosaic.json",
                {"mosaics": []},
            ),
        },
    )
    authority = PhysicalByteCeilingAuthority(
        tmp_path,
        10 * 1024 * 1024,
    )

    with pytest.raises(
            LiveRecoveryError,
            match="differs from its sealed baseline"):
        retire_redundant_predecessor_current(
            root,
            baseline=baseline,
            hmac_key=HMAC_KEY,
            physical_byte_authority=authority,
        )

    assert root.exists()
    assert manager.load_current().tick == baseline.tick


def test_nested_state_file_tick_lineage_is_verified(tmp_path) -> None:
    baseline = _stateful_nested_baseline(tmp_path)
    source = tmp_path / "stateful-nested-hot-source"
    ticks = {
        "cold.json": 10,
        "core.json": 11,
        "owner_state/causal_relation.state": 11,
        "owner_state/mosaic.json": 11,
    }
    files = {
        "core.json": _json(
            source / "core.json",
            {"data": {"state_file_ticks": ticks}},
        ),
        "owner_state/causal_relation.state": _write(
            source / "owner_state/causal_relation.state",
            b"grown-causal-relation",
        ),
        "owner_state/mosaic.json": _json(
            source / "owner_state/mosaic.json",
            {"mosaics": [{"sequence": 1}]},
        ),
    }
    manager = LiveRecoveryGenerationStore(
        tmp_path / "stateful-nested-live",
        baseline=baseline,
        hot_files=NESTED_HOT_FILES,
        hmac_key=HMAC_KEY,
        state_file_tick_manifest="core.json",
    )

    committed = manager.commit_hot_state(tick=11, files=files)

    assert manager.load_current().generation_uuid == committed.generation_uuid


@pytest.mark.parametrize(
    "relative_path",
    (
        "../escape.state",
        "/absolute.state",
        "owner_state/../escape.state",
        "owner_state/./escape.state",
        "owner_state//escape.state",
        "owner_state\\escape.state",
        "owner_state/\x00escape.state",
        "owner_state/.mosaic.json.live-recovery.tmp",
        "owner_state/.mosaic.json.live-recovery.prior",
    ),
)
def test_nested_hot_contract_rejects_escape_syntax(
        tmp_path, relative_path) -> None:
    with pytest.raises(LiveRecoveryError, match="path"):
        LiveRecoveryGenerationStore(
            tmp_path / "invalid-live",
            baseline=_baseline(tmp_path),
            hot_files=(relative_path,),
            hmac_key=HMAC_KEY,
        )


def test_nested_parent_symlink_cannot_escape_active_root(tmp_path) -> None:
    active = tmp_path / "active-parent-symlink"
    active.mkdir()
    _json(active / "core.json", {"tick": 10})
    outside = tmp_path / "outside"
    _write(outside / "causal_relation.state", b"outside-prior")
    _json(outside / "mosaic.json", {"outside": "prior"})
    (active / "owner_state").symlink_to(outside, target_is_directory=True)
    manager = _manager(tmp_path)
    manager.commit_hot_state(tick=11, files=_hot_sources(tmp_path))

    with pytest.raises(LiveRecoveryError, match="parent"):
        manager.apply_current(active)

    assert (outside / "causal_relation.state").read_bytes() == b"outside-prior"
    assert json.loads((outside / "mosaic.json").read_text()) == {
        "outside": "prior",
    }


def test_nested_leaf_symlink_cannot_escape_active_root(tmp_path) -> None:
    active = _materialized_baseline(tmp_path)
    outside = _write(tmp_path / "outside.state", b"outside-prior")
    target = active / "owner_state/causal_relation.state"
    target.unlink()
    target.symlink_to(outside)
    manager = _manager(tmp_path)
    manager.commit_hot_state(tick=11, files=_hot_sources(tmp_path))

    with pytest.raises(LiveRecoveryError, match="target"):
        manager.apply_current(active)

    assert outside.read_bytes() == b"outside-prior"


def test_nested_apply_failure_restores_every_prior_file(
        tmp_path, monkeypatch) -> None:
    active = _materialized_baseline(tmp_path)
    prior = {
        relative: (active / relative).read_bytes()
        for relative in NESTED_HOT_FILES
    }
    manager = _manager(tmp_path)
    manager.commit_hot_state(tick=11, files=_hot_sources(tmp_path))
    real_rename = live_module.os.rename

    def reject_nested_mosaic(source, destination, **kwargs):
        if (
            str(source).startswith(".mosaic.json.")
            and str(source).endswith(".live-recovery.tmp")
        ):
            raise OSError("injected nested activation failure")
        return real_rename(source, destination, **kwargs)

    monkeypatch.setattr(live_module.os, "rename", reject_nested_mosaic)
    with pytest.raises(OSError, match="nested activation failure"):
        manager.apply_current(active)

    assert {
        relative: (active / relative).read_bytes()
        for relative in NESTED_HOT_FILES
    } == prior
    assert not tuple(
        path
        for path in active.rglob("*")
        if ".live-recovery." in path.name
    )


def test_interrupted_nested_activation_is_recovered_before_reapply(
        tmp_path) -> None:
    active = _materialized_baseline(tmp_path)
    manager = _manager(tmp_path)
    manager.commit_hot_state(tick=11, files=_hot_sources(tmp_path))
    owner_directory = active / "owner_state"
    target = owner_directory / "causal_relation.state"
    backup = owner_directory / (
        ".causal_relation.state.live-recovery.prior"
    )
    temporary = owner_directory / (
        ".causal_relation.state.live-recovery.tmp"
    )
    target.rename(backup)
    temporary.write_bytes(b"incomplete-new-state")

    manager.apply_current(active)

    assert target.read_bytes() == b"grown-causal-relation"
    assert not backup.exists()
    assert not temporary.exists()
