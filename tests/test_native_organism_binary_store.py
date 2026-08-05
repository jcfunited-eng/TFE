from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

import pytest

from dsf_ai_service.substrate import native_organism_binary_store as store


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
OTHER_IDENTITY = "7e45ec7a-7b39-4213-bff3-424b445a7f2e"
MAX_ENVELOPE_BYTES = 4096
MAX_FABRIC_BYTES = 4000
MAX_LOGICAL_PEAK_BYTES = 9000


def _state(label: str) -> bytes:
    return store.STATE_MAGIC + b"\0" + label.encode("ascii")


@dataclass(frozen=True)
class _Observation:
    identity: str
    organism_tick: int
    state: bytes

    @property
    def state_bytes(self) -> int:
        return len(self.state)

    @property
    def state_sha256(self) -> str:
        return hashlib.sha256(self.state).hexdigest()


class _Resident:
    def __init__(
        self,
        state: bytes,
        tick: int,
        identity: str = IDENTITY,
    ) -> None:
        self.state = state
        self.tick = tick
        self.identity = identity
        self.prepare_calls = 0

    def readiness(self) -> _Observation:
        return _Observation(self.identity, self.tick, self.state)

    def save(self) -> bytes:
        return self.state

    def prepare(self, _source) -> None:
        self.prepare_calls += 1
        raise AssertionError("persistence called forbidden method")


class _ObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.puts: list[tuple[str, int, str]] = []

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
        created = key not in self.objects
        prior = self.objects.setdefault(key, body)
        if prior != body:
            raise RuntimeError("immutable remote collision")
        self.puts.append((key, byte_count, sha256))
        return created

    def iter_bytes(self, key: str):
        body = self.objects[key]
        midpoint = max(1, len(body) // 2)
        yield body[:midpoint]
        if midpoint < len(body):
            yield body[midpoint:]

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


@pytest.fixture(autouse=True)
def _concrete_native_boundary(monkeypatch):
    known: dict[str, tuple[bytes, int, str]] = {}

    def register(resident: _Resident) -> _Resident:
        known[hashlib.sha256(resident.state).hexdigest()] = (
            resident.state,
            resident.tick,
            resident.identity,
        )
        return resident

    def restore(**values):
        body = values["current_envelope"]
        digest = hashlib.sha256(body).hexdigest()
        expected, tick, identity = known[digest]
        assert body == expected
        return _Resident(body, tick, identity)

    monkeypatch.setattr(store, "NativeResidentOrganism", _Resident)
    monkeypatch.setattr(store, "restore_native_resident_organism", restore)
    return register


def _stage(root: Path, register, label: str, tick: int):
    resident = register(_Resident(_state(label), tick))
    staged = store.stage_active_native_organism(
        root,
        resident,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
    )
    assert resident.prepare_calls == 0
    return resident, staged


def _publish(staged, remote, predecessor=None, injector=None):
    return store.publish_staged_native_organism(
        staged,
        expected_predecessor_sha256=predecessor,
        object_store=remote,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
        max_fabric_bytes=MAX_FABRIC_BYTES,
        max_logical_peak_bytes=MAX_LOGICAL_PEAK_BYTES,
        failure_injector=injector,
    )


def _restore(root: Path):
    return store.restore_current_native_organism(
        root,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
        max_fabric_bytes=MAX_FABRIC_BYTES,
        max_logical_peak_bytes=MAX_LOGICAL_PEAK_BYTES,
    )


def _publish_pair(root: Path, register, remote: _ObjectStore):
    first, first_stage = _stage(root, register, "first", 10)
    first_publication = _publish(first_stage, remote)
    second, second_stage = _stage(root, register, "second", 11)
    second_publication = _publish(
        second_stage,
        remote,
        first_publication.pointer.state_sha256,
    )
    return first, first_publication, second, second_publication


def _rollback(root: Path, remote: _ObjectStore, current_sha256: str):
    return store.rollback_to_verified_predecessor(
        root,
        expected_current_sha256=current_sha256,
        object_store=remote,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
        max_fabric_bytes=MAX_FABRIC_BYTES,
        max_logical_peak_bytes=MAX_LOGICAL_PEAK_BYTES,
    )


def test_raw_glorun_publication_and_current_only_restore(
    tmp_path: Path,
    _concrete_native_boundary,
) -> None:
    remote = _ObjectStore()
    resident, staged = _stage(
        tmp_path, _concrete_native_boundary, "first", 23_723_846
    )

    published = _publish(staged, remote)
    restored = _restore(tmp_path)

    assert restored.organism.save() == resident.save()
    assert restored.pointer == published.pointer
    assert published.pointer.identity == IDENTITY
    assert published.pointer.organism_tick == 23_723_846
    assert published.pointer.predecessor_state_sha256 is None
    assert published.accounting.exact_peak_bytes == len(resident.save())
    generation = (
        tmp_path
        / store.GENERATIONS_DIRECTORY
        / f"{published.pointer.state_sha256}.glorun"
    )
    assert generation.read_bytes() == resident.save()
    assert remote.objects[published.remote_key] == resident.save()
    assert resident.prepare_calls == 0
    assert not staged.path.exists()
    names = {path.name for path in tmp_path.rglob("*")}
    assert not any("owner" in name.lower() or "lock" in name.lower() for name in names)


def test_stage_fsync_failure_cleans_only_its_private_stage(
    tmp_path: Path,
    _concrete_native_boundary,
) -> None:
    sentinel = tmp_path / "retained.txt"
    sentinel.write_text("retained", encoding="utf-8")
    resident = _concrete_native_boundary(_Resident(_state("stage-fault"), 1))

    def inject(step: str) -> None:
        if step == "after_stage_fsync":
            raise RuntimeError("injected stage fault")

    with pytest.raises(RuntimeError, match="injected stage fault"):
        store.stage_active_native_organism(
            tmp_path,
            resident,
            max_envelope_bytes=MAX_ENVELOPE_BYTES,
            failure_injector=inject,
        )

    assert list(tmp_path.glob(".stage-*.glorun")) == []
    assert sentinel.read_text(encoding="utf-8") == "retained"


@pytest.mark.parametrize("magic", (b"GLMFAB03", b"GLMFAB04", b"GLJNFT03"))
def test_stage_refuses_every_legacy_or_inner_state(
    tmp_path: Path,
    _concrete_native_boundary,
    magic: bytes,
) -> None:
    resident = _concrete_native_boundary(_Resident(magic + b"-body", 7))

    with pytest.raises(
        store.NativeOrganismBinaryStoreError,
        match="exact GLORUN",
    ):
        store.stage_active_native_organism(
            tmp_path,
            resident,
            max_envelope_bytes=MAX_ENVELOPE_BYTES,
        )

    assert list(tmp_path.glob(".stage-*.glorun")) == []
    assert resident.prepare_calls == 0


@pytest.mark.parametrize(
    "step",
    (
        "after_stage_readback",
        "after_cold_restore",
        "after_object_upload",
        "after_object_readback",
        "after_generation_placement",
        "before_current_replace",
    ),
)
def test_failure_before_current_preserves_predecessor_and_cleans_candidate(
    tmp_path: Path,
    _concrete_native_boundary,
    step: str,
) -> None:
    remote = _ObjectStore()
    first, first_stage = _stage(
        tmp_path, _concrete_native_boundary, "first", 10
    )
    first_publication = _publish(first_stage, remote)
    second, second_stage = _stage(
        tmp_path, _concrete_native_boundary, "second", 11
    )

    def inject(observed: str) -> None:
        if observed == step:
            raise RuntimeError(f"injected {step}")

    with pytest.raises(RuntimeError, match=f"injected {step}"):
        _publish(
            second_stage,
            remote,
            first_publication.pointer.state_sha256,
            inject,
        )

    assert _restore(tmp_path).organism.save() == first.save()
    assert not second_stage.path.exists()
    generations = list(
        (tmp_path / store.GENERATIONS_DIRECTORY).glob("*.glorun")
    )
    assert [path.read_bytes() for path in generations] == [first.save()]
    assert second.prepare_calls == 0


def test_failure_after_current_replace_reports_new_durable_current(
    tmp_path: Path,
    _concrete_native_boundary,
) -> None:
    remote = _ObjectStore()
    _first, first_publication, second, second_publication = _publish_pair(
        tmp_path, _concrete_native_boundary, remote
    )
    third, third_stage = _stage(
        tmp_path, _concrete_native_boundary, "third", 12
    )

    def inject(step: str) -> None:
        if step == "after_current_replace":
            raise RuntimeError("injected committed publication")

    with pytest.raises(RuntimeError, match="committed publication"):
        _publish(
            third_stage,
            remote,
            second_publication.pointer.state_sha256,
            inject,
        )

    restored = _restore(tmp_path)
    assert restored.organism.save() == third.save()
    assert restored.pointer.predecessor_state_sha256 == (
        second_publication.pointer.state_sha256
    )
    generations = {
        path.read_bytes()
        for path in (tmp_path / store.GENERATIONS_DIRECTORY).glob("*.glorun")
    }
    assert generations == {second.save(), third.save()}
    assert set(remote.objects.values()) == {second.save(), third.save()}
    assert first_publication.pointer.state_sha256 not in remote.objects


def test_expected_predecessor_is_mandatory_and_exact(
    tmp_path: Path,
    _concrete_native_boundary,
) -> None:
    remote = _ObjectStore()
    first, first_stage = _stage(
        tmp_path, _concrete_native_boundary, "first", 10
    )
    first_publication = _publish(first_stage, remote)
    _second, second_stage = _stage(
        tmp_path, _concrete_native_boundary, "second", 11
    )

    with pytest.raises(
        store.NativeOrganismBinaryStoreError,
        match="expected predecessor",
    ):
        _publish(second_stage, remote, "f" * 64)

    assert _restore(tmp_path).organism.save() == first.save()
    assert second_stage.path.exists()
    store.discard_staged_native_organism(second_stage)
    assert not second_stage.path.exists()
    assert first_publication.pointer.state_sha256 != "f" * 64


def test_boot_never_falls_back_and_explicit_rollback_uses_authentic_tick(
    tmp_path: Path,
    _concrete_native_boundary,
) -> None:
    remote = _ObjectStore()
    first, first_publication, _second, second_publication = _publish_pair(
        tmp_path, _concrete_native_boundary, remote
    )
    current_path = (
        tmp_path
        / store.GENERATIONS_DIRECTORY
        / f"{second_publication.pointer.state_sha256}.glorun"
    )
    current_path.chmod(0o600)
    current_path.write_bytes(_state("corrupt"))

    with pytest.raises(store.NativeOrganismBinaryStoreError):
        _restore(tmp_path)

    rollback = _rollback(
        tmp_path,
        remote,
        second_publication.pointer.state_sha256,
    )

    assert rollback.identity == IDENTITY
    assert rollback.organism_tick == 10
    assert rollback.state_bytes == len(first.save())
    assert rollback.state_sha256 == first_publication.pointer.state_sha256
    assert rollback.predecessor_state_sha256 == (
        second_publication.pointer.state_sha256
    )
    restored = _restore(tmp_path)
    assert restored.organism.save() == first.save()
    assert restored.pointer == rollback


def test_rollback_refuses_identity_discontinuity_before_current_replace(
    tmp_path: Path,
    _concrete_native_boundary,
    monkeypatch,
) -> None:
    remote = _ObjectStore()
    first, _first_publication, _second, second_publication = _publish_pair(
        tmp_path, _concrete_native_boundary, remote
    )

    def wrong_identity_restore(**values):
        return _Resident(values["current_envelope"], 10, OTHER_IDENTITY)

    monkeypatch.setattr(
        store, "restore_native_resident_organism", wrong_identity_restore
    )

    with pytest.raises(
        store.NativeOrganismBinaryStoreError,
        match="identity, readiness, or save differs",
    ):
        _rollback(
            tmp_path,
            remote,
            second_publication.pointer.state_sha256,
        )

    assert store._read_current(tmp_path) == second_publication.pointer
    predecessor_path = (
        tmp_path
        / store.GENERATIONS_DIRECTORY
        / f"{hashlib.sha256(first.save()).hexdigest()}.glorun"
    )
    assert predecessor_path.read_bytes() == first.save()


def test_rollback_refuses_save_that_differs_from_exact_predecessor(
    tmp_path: Path,
    _concrete_native_boundary,
    monkeypatch,
) -> None:
    remote = _ObjectStore()
    _first, _first_publication, _second, second_publication = _publish_pair(
        tmp_path, _concrete_native_boundary, remote
    )

    class DishonestSaveResident(_Resident):
        def save(self) -> bytes:
            return _state("different-save")

    def dishonest_restore(**values):
        return DishonestSaveResident(values["current_envelope"], 10)

    monkeypatch.setattr(store, "restore_native_resident_organism", dishonest_restore)

    with pytest.raises(
        store.NativeOrganismBinaryStoreError,
        match="identity, readiness, or save differs",
    ):
        _rollback(
            tmp_path,
            remote,
            second_publication.pointer.state_sha256,
        )

    assert store._read_current(tmp_path) == second_publication.pointer


def test_rollback_refuses_readiness_change_during_exact_save_proof(
    tmp_path: Path,
    _concrete_native_boundary,
    monkeypatch,
) -> None:
    remote = _ObjectStore()
    _first, _first_publication, _second, second_publication = _publish_pair(
        tmp_path, _concrete_native_boundary, remote
    )

    class MovingReadinessResident(_Resident):
        def __init__(self, state: bytes) -> None:
            super().__init__(state, 10)
            self.observations = 0

        def readiness(self) -> _Observation:
            self.observations += 1
            return _Observation(
                self.identity,
                self.tick + self.observations - 1,
                self.state,
            )

    def moving_restore(**values):
        return MovingReadinessResident(values["current_envelope"])

    monkeypatch.setattr(store, "restore_native_resident_organism", moving_restore)

    with pytest.raises(
        store.NativeOrganismBinaryStoreError,
        match="readiness changed",
    ):
        _rollback(
            tmp_path,
            remote,
            second_publication.pointer.state_sha256,
        )

    assert store._read_current(tmp_path) == second_publication.pointer


def test_retention_and_peak_are_current_predecessor_and_one_stage(
    tmp_path: Path,
    _concrete_native_boundary,
) -> None:
    remote = _ObjectStore()
    first, stage = _stage(tmp_path, _concrete_native_boundary, "one", 1)
    first_published = _publish(stage, remote)
    second, stage = _stage(tmp_path, _concrete_native_boundary, "two-two", 2)
    second_published = _publish(
        stage, remote, first_published.pointer.state_sha256
    )
    third, stage = _stage(
        tmp_path, _concrete_native_boundary, "three-three-three", 3
    )
    third_published = _publish(
        stage, remote, second_published.pointer.state_sha256
    )

    assert third_published.accounting.current_bytes == len(second.save())
    assert third_published.accounting.retained_predecessor_bytes == len(
        first.save()
    )
    assert third_published.accounting.staged_bytes == len(third.save())
    assert third_published.accounting.exact_peak_bytes == sum(
        map(len, (first.save(), second.save(), third.save()))
    )
    generations = {
        path.read_bytes()
        for path in (tmp_path / store.GENERATIONS_DIRECTORY).glob("*.glorun")
    }
    assert generations == {second.save(), third.save()}
    assert set(remote.objects.values()) == {second.save(), third.save()}


def test_remote_readback_drift_refuses_before_current(
    tmp_path: Path,
    _concrete_native_boundary,
) -> None:
    class DriftStore(_ObjectStore):
        def iter_bytes(self, key: str):
            yield self.objects[key] + b"drift"

    remote = DriftStore()
    _resident, staged = _stage(
        tmp_path, _concrete_native_boundary, "remote-drift", 1
    )

    with pytest.raises(
        store.NativeOrganismBinaryStoreError,
        match="remote stream exceeded expected bytes",
    ):
        _publish(staged, remote)

    assert not (tmp_path / store.CURRENT_NAME).exists()
    assert list((tmp_path / store.GENERATIONS_DIRECTORY).iterdir()) == []
    assert not staged.path.exists()


def test_discard_is_exactly_scoped_and_never_removes_neighbor(
    tmp_path: Path,
    _concrete_native_boundary,
) -> None:
    sentinel = tmp_path / "do-not-remove.txt"
    sentinel.write_text("retained", encoding="utf-8")
    _resident, staged = _stage(
        tmp_path, _concrete_native_boundary, "discard", 1
    )

    store.discard_staged_native_organism(staged)

    assert sentinel.read_text(encoding="utf-8") == "retained"
    assert not staged.path.exists()
    escaped = store.StagedNativeOrganism(
        store_root=tmp_path,
        path=sentinel,
        identity=IDENTITY,
        organism_tick=1,
        state_bytes=sentinel.stat().st_size,
        state_sha256=hashlib.sha256(sentinel.read_bytes()).hexdigest(),
    )
    with pytest.raises(
        store.NativeOrganismBinaryStoreError,
        match="escaped",
    ):
        store.discard_staged_native_organism(escaped)
    assert sentinel.exists()


def test_module_has_no_forbidden_or_provisional_persistence_surface() -> None:
    source = Path(store.__file__).read_text(encoding="utf-8")

    assert "import json" not in source
    assert "import base64" not in source
    assert "state_base64" not in source
    assert "native_materialized_fabric" not in source
    assert "GLMFAB" not in source
    assert "prepare(" not in source
    assert "provisional" not in source
