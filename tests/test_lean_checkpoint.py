from __future__ import annotations

from dataclasses import dataclass
import gc
import hashlib
from pathlib import Path
import time
import weakref

import pytest

from dsf_ai_service.lean_checkpoint import CheckpointWork, LeanCheckpointWorker
from dsf_ai_service.paired_current_store import PairedCurrentStore


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


@dataclass(slots=True)
class _Checkpoint:
    organism_tick: int
    body: bytes

    @property
    def state_bytes(self) -> int:
        return len(self.body)

    @property
    def state_sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()

    def encoded_generation(self) -> bytes:
        return self.body


@dataclass(slots=True, weakref_slot=True)
class _Snapshot:
    organism_tick: int
    body: bytes
    failure: BaseException | None = None

    def prepare_checkpoint(self) -> _Checkpoint:
        if self.failure is not None:
            raise self.failure
        return _Checkpoint(self.organism_tick, self.body)


def _store(root: Path) -> PairedCurrentStore:
    store = PairedCurrentStore(
        root,
        max_body_bytes=4096,
        max_world_bytes=4096,
    )
    store.publish(
        identity=IDENTITY,
        organism_tick=10,
        body=b"body-zero",
        world=b"world-zero",
        expected_current_body_sha256=None,
    )
    return store


def test_worker_publishes_one_exact_pair_without_runtime_access(tmp_path: Path) -> None:
    store = _store(tmp_path)
    before = store.read_pointer().current
    worker = LeanCheckpointWorker(store)
    try:
        worker.submit(CheckpointWork(
            snapshot=_Snapshot(14, b"body-fourteen"),
            world=b"world-fourteen",
            identity=IDENTITY,
            expected_current_body_sha256=before.body_sha256,
        ))
        result = worker.receive(timeout=5)
    finally:
        worker.close()

    assert result.committed is True
    assert result.error is None
    assert result.cleanup_error is None
    assert result.pointer is not None
    assert result.pointer.current.organism_tick == 14
    assert result.pointer.predecessor == before
    restored = store.restore()
    assert restored.body == b"body-fourteen"
    assert restored.world == b"world-fourteen"


def test_worker_releases_completed_snapshot_while_idle(tmp_path: Path) -> None:
    store = _store(tmp_path)
    before = store.read_pointer().current
    snapshot = _Snapshot(14, b"body-fourteen")
    held_snapshot = weakref.ref(snapshot)
    worker = LeanCheckpointWorker(store)
    try:
        worker.submit(CheckpointWork(
            snapshot=snapshot,
            world=b"world-fourteen",
            identity=IDENTITY,
            expected_current_body_sha256=before.body_sha256,
        ))
        del snapshot
        assert worker.receive(timeout=5).committed is True
        for _ in range(20):
            gc.collect()
            if held_snapshot() is None:
                break
            time.sleep(0.01)
        assert held_snapshot() is None
    finally:
        worker.close()


def test_worker_refuses_a_second_outstanding_snapshot(tmp_path: Path) -> None:
    store = _store(tmp_path)
    before = store.read_pointer().current
    worker = LeanCheckpointWorker(store)
    work = CheckpointWork(
        snapshot=_Snapshot(11, b"body-eleven"),
        world=b"world-eleven",
        identity=IDENTITY,
        expected_current_body_sha256=before.body_sha256,
    )
    try:
        worker.submit(work)
        with pytest.raises(RuntimeError, match="already outstanding"):
            worker.submit(work)
        assert worker.receive(timeout=5).committed is True
    finally:
        worker.close()


def test_encode_failure_changes_no_current_and_reopens_slot(tmp_path: Path) -> None:
    store = _store(tmp_path)
    before = store.read_pointer().current
    worker = LeanCheckpointWorker(store)
    try:
        worker.submit(CheckpointWork(
            snapshot=_Snapshot(11, b"unused", RuntimeError("encode refused")),
            world=b"world-eleven",
            identity=IDENTITY,
            expected_current_body_sha256=before.body_sha256,
        ))
        failed = worker.receive(timeout=5)
        assert failed.committed is False
        assert isinstance(failed.error, RuntimeError)
        assert store.read_pointer().current == before

        worker.submit(CheckpointWork(
            snapshot=_Snapshot(12, b"body-twelve"),
            world=b"world-twelve",
            identity=IDENTITY,
            expected_current_body_sha256=before.body_sha256,
        ))
        recovered = worker.receive(timeout=5)
    finally:
        worker.close()

    assert recovered.committed is True
    assert store.restore().body == b"body-twelve"
