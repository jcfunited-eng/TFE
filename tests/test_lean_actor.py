from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import threading
import time

import pytest

from dsf_ai_service.lean_actor import (
    LeanOrganismActor,
    PhysicalOccurrence,
    PhysicalSettlementFailure,
    SettlementResult,
)
from dsf_ai_service.paired_current_store import PairedCurrentStore


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


@dataclass(slots=True)
class _Readiness:
    identity: str
    organism_tick: int
    state_sha256: str
    state_bytes: int
    python_callback_count: int = 0


@dataclass(slots=True)
class _Checkpoint:
    organism_tick: int
    body: bytes

    @property
    def state_sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()

    @property
    def state_bytes(self) -> int:
        return len(self.body)

    def encoded_generation(self) -> bytes:
        return self.body


@dataclass(slots=True)
class _Snapshot:
    organism_tick: int
    body: bytes

    def prepare_checkpoint(self) -> _Checkpoint:
        return _Checkpoint(self.organism_tick, self.body)


class _Runtime:
    def __init__(self, body: bytes, tick: int) -> None:
        self.live_tick = tick
        self.persisted_tick = tick
        self.persisted = body
        self.owner_threads: set[int] = set()

    def _owned(self) -> None:
        self.owner_threads.add(threading.get_ident())

    @property
    def live_organism_tick(self) -> int:
        self._owned()
        return self.live_tick

    def readiness(self) -> _Readiness:
        self._owned()
        return _Readiness(
            IDENTITY,
            self.persisted_tick,
            hashlib.sha256(self.persisted).hexdigest(),
            len(self.persisted),
        )

    def advance(self) -> None:
        self._owned()
        self.live_tick += 1

    def snapshot_lived_state(self) -> _Snapshot:
        self._owned()
        return _Snapshot(self.live_tick, f"body-{self.live_tick}".encode())

    def validate_lived_checkpoint(self, checkpoint: _Checkpoint) -> None:
        self._owned()
        assert checkpoint.organism_tick <= self.live_tick

    def adopt_published_lived_checkpoint(self, checkpoint: _Checkpoint) -> None:
        self._owned()
        self.persisted = checkpoint.body
        self.persisted_tick = checkpoint.organism_tick


class _World:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def encoded_snapshot(self) -> bytes:
        return self.body


class _Physical:
    @property
    def maximum_native_intervals_per_occurrence(self) -> int:
        return 1

    def settle(
        self,
        runtime: _Runtime,
        world: _World,
        occurrence: PhysicalOccurrence,
    ) -> SettlementResult:
        if occurrence.kind == "refuse":
            raise RuntimeError("physical refusal")
        runtime.advance()
        world.body = f"world-{runtime.live_tick}".encode()
        return SettlementResult(
            native_interval_count=1,
            observation={"accepted": True},
        )

    def unattended(self, runtime: _Runtime, world: _World) -> SettlementResult:
        return self.settle(runtime, world, PhysicalOccurrence("unattended", None))


class _FailingPublishStore(PairedCurrentStore):
    def __init__(self, root: Path) -> None:
        super().__init__(root, max_body_bytes=4096, max_world_bytes=4096)
        self.fail_publish = False
        self.checkpoint_publish_count = 0

    def publish(self, **values):  # type: ignore[no-untyped-def]
        if self.fail_publish:
            self.checkpoint_publish_count += 1
            raise RuntimeError("checkpoint publish failed")
        return super().publish(**values)


class _BlockingPublishStore(PairedCurrentStore):
    def __init__(self, root: Path) -> None:
        super().__init__(root, max_body_bytes=4096, max_world_bytes=4096)
        self.block_publish = False
        self.checkpoint_publish_count = 0
        self.publish_started = threading.Event()
        self.publish_release = threading.Event()

    def publish(self, **values):  # type: ignore[no-untyped-def]
        if self.block_publish:
            self.checkpoint_publish_count += 1
            self.publish_started.set()
            if not self.publish_release.wait(timeout=5):
                raise RuntimeError("test checkpoint release was absent")
        return super().publish(**values)


class _FailingCleanupStore(PairedCurrentStore):
    def __init__(self, root: Path) -> None:
        super().__init__(root, max_body_bytes=4096, max_world_bytes=4096)
        self.fail_cleanup = False
        self.cleanup_count = 0

    def reconcile(self, pointer=None):  # type: ignore[no-untyped-def]
        self.cleanup_count += 1
        if self.fail_cleanup:
            raise RuntimeError("checkpoint cleanup failed")
        return super().reconcile(pointer)


def _actor(
    root: Path,
    *,
    store: PairedCurrentStore | None = None,
    checkpoint_every_intervals: int = 2,
    unattended_interval_seconds: float = 60,
) -> tuple[LeanOrganismActor, _Runtime, PairedCurrentStore]:
    body = b"body-10"
    world_body = b"world-10"
    held_store = store or PairedCurrentStore(
        root,
        max_body_bytes=4096,
        max_world_bytes=4096,
    )
    pointer = held_store.publish(
        identity=IDENTITY,
        organism_tick=10,
        body=body,
        world=world_body,
        expected_current_body_sha256=None,
    )
    runtime = _Runtime(body, 10)
    actor = LeanOrganismActor(
        runtime=runtime,
        world=_World(world_body),
        pointer=pointer,
        store=held_store,
        physical=_Physical(),
        mailbox_capacity=2,
        checkpoint_every_intervals=checkpoint_every_intervals,
        unattended_interval_seconds=unattended_interval_seconds,
    )
    return actor, runtime, held_store


def _wait_until_unavailable(actor: LeanOrganismActor) -> dict[str, object]:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        observation = actor.observation()
        if observation["available"] is False:
            return observation
        time.sleep(0.005)
    raise AssertionError("actor did not expose its fatal custody failure")


def test_actor_uses_one_owner_and_distinguishes_live_from_durable_tick(
    tmp_path: Path,
) -> None:
    actor, runtime, store = _actor(tmp_path)
    actor.start()
    try:
        first = actor.submit(PhysicalOccurrence("light", b"one"), timeout=5)
        assert first.native_interval_count == 1
        first_observation = actor.observation()
        assert first_observation["live_tick"] == 11
        assert first_observation["persisted_tick"] == 10
        actor.submit(PhysicalOccurrence("sound", b"two"), timeout=5)
        actor.submit(PhysicalOccurrence("touch", b"three"), timeout=5)
    finally:
        actor.close()

    restored = store.restore()
    assert restored.pointer.current.organism_tick == 13
    assert restored.body == b"body-13"
    assert restored.world == b"world-13"
    assert len(runtime.owner_threads) == 1


def test_observation_is_cached_and_does_not_call_runtime(tmp_path: Path) -> None:
    actor, runtime, _store = _actor(tmp_path)
    actor.start()
    try:
        actor.submit(PhysicalOccurrence("light", b"one"), timeout=5)
        owner_calls = set(runtime.owner_threads)
        observation = actor.observation()
        assert observation["live_tick"] == 11
        assert observation["last_occurrence"]["kind"] == "light"
        assert runtime.owner_threads == owner_calls
    finally:
        actor.close()


def test_one_refused_occurrence_does_not_kill_actor(tmp_path: Path) -> None:
    actor, _runtime, store = _actor(tmp_path)
    actor.start()
    try:
        with pytest.raises(RuntimeError, match="physical refusal"):
            actor.submit(PhysicalOccurrence("refuse", None), timeout=5)
        accepted = actor.submit(PhysicalOccurrence("light", b"one"), timeout=5)
        assert accepted.observation == {"accepted": True}
    finally:
        actor.close()

    assert store.restore().pointer.current.organism_tick == 11


def test_failed_checkpoint_kills_actor_once_without_retry(tmp_path: Path) -> None:
    failing_store = _FailingPublishStore(tmp_path)
    actor, _runtime, store = _actor(
        tmp_path,
        store=failing_store,
        checkpoint_every_intervals=1,
        unattended_interval_seconds=0.02,
    )
    failing_store.fail_publish = True
    actor.start()
    actor.submit(PhysicalOccurrence("light", b"one"), timeout=5)

    observation = _wait_until_unavailable(actor)
    assert failing_store.checkpoint_publish_count == 1
    assert observation["checkpoint_error"] == (
        "RuntimeError: checkpoint publish failed"
    )
    assert store.restore().pointer.current.organism_tick == 10
    with pytest.raises(RuntimeError, match="organism actor failed"):
        actor.offer(PhysicalOccurrence("light", b"two"))
    with pytest.raises(RuntimeError, match="organism actor stopped after failure"):
        actor.close()


def test_hung_checkpoint_stops_life_before_two_custody_cadences(
    tmp_path: Path,
) -> None:
    blocking_store = _BlockingPublishStore(tmp_path)
    actor, runtime, _store = _actor(
        tmp_path,
        store=blocking_store,
        checkpoint_every_intervals=1,
    )
    blocking_store.block_publish = True
    actor.start()
    actor.submit(PhysicalOccurrence("light", b"one"), timeout=5)
    assert blocking_store.publish_started.wait(timeout=1)
    actor.submit(PhysicalOccurrence("sound", b"two"), timeout=5)

    observation = actor.observation()
    assert observation["live_tick"] == 12
    assert observation["pending_interval_count"] == 2
    assert observation["durability_blocked"] is True
    first_waiting = actor.offer(PhysicalOccurrence("touch", b"three"))
    second_waiting = actor.offer(PhysicalOccurrence("light", b"four"))
    assert first_waiting.done() is False
    assert second_waiting.done() is False
    with pytest.raises(RuntimeError, match="mailbox is full"):
        actor.offer(PhysicalOccurrence("sound", b"five"))
    assert runtime.live_tick == 12

    blocking_store.publish_release.set()
    assert first_waiting.result(timeout=5).observation == {"accepted": True}
    assert second_waiting.result(timeout=5).observation == {"accepted": True}
    actor.close()
    assert blocking_store.checkpoint_publish_count == 4
    assert blocking_store.restore().pointer.current.organism_tick == 14


def test_failed_generation_cleanup_kills_actor_after_safe_commit(
    tmp_path: Path,
) -> None:
    failing_store = _FailingCleanupStore(tmp_path)
    actor, _runtime, store = _actor(
        tmp_path,
        store=failing_store,
        checkpoint_every_intervals=1,
        unattended_interval_seconds=0.02,
    )
    failing_store.fail_cleanup = True
    actor.start()
    actor.submit(PhysicalOccurrence("light", b"one"), timeout=5)

    observation = _wait_until_unavailable(actor)
    assert failing_store.cleanup_count == 1
    assert observation["cleanup_error"] == (
        "RuntimeError: checkpoint cleanup failed"
    )
    assert store.restore().pointer.current.organism_tick == 11
    with pytest.raises(RuntimeError, match="organism actor stopped after failure"):
        actor.close()


def test_post_native_failure_stops_without_publishing_mismatched_world(
    tmp_path: Path, monkeypatch,
) -> None:
    actor, runtime, store = _actor(tmp_path)

    def fail_after_native(self, runtime, world, occurrence):
        runtime.advance()
        raise PhysicalSettlementFailure("world consequence could not commit")

    monkeypatch.setattr(_Physical, "settle", fail_after_native)
    actor.start()
    with pytest.raises(PhysicalSettlementFailure, match="world consequence"):
        actor.submit(PhysicalOccurrence("light", b"one"), timeout=5)
    _wait_until_unavailable(actor)
    with pytest.raises(RuntimeError, match="organism actor stopped after failure"):
        actor.close()
    assert runtime.live_tick == 11
    restored = store.restore()
    assert restored.pointer.current.organism_tick == 10
    assert restored.body == b"body-10"
    assert restored.world == b"world-10"


def test_cancelled_queued_request_never_advances_physics(
    tmp_path: Path, monkeypatch,
) -> None:
    actor, runtime, store = _actor(tmp_path)
    entered, release = threading.Event(), threading.Event()
    settled = []
    original = _Physical.settle

    def blocked(self, runtime, world, occurrence):
        if occurrence.kind == "first":
            entered.set()
            if not release.wait(timeout=5):
                raise RuntimeError("test release absent")
        settled.append(occurrence.kind)
        return original(self, runtime, world, occurrence)

    monkeypatch.setattr(_Physical, "settle", blocked)
    actor.start()
    try:
        first = actor.offer(PhysicalOccurrence("first", None))
        assert entered.wait(timeout=5)
        cancelled = actor.offer(PhysicalOccurrence("cancelled", None))
        assert cancelled.cancel()
        release.set()
        assert first.result(timeout=5).native_interval_count == 1
        actor.submit(PhysicalOccurrence("last", None), timeout=5)
    finally:
        release.set()
        actor.close()
    assert settled == ["first", "last"]
    assert runtime.live_tick == 12
    assert store.restore().pointer.current.organism_tick == 12


def test_fatal_interval_drains_only_already_submitted_good_checkpoint(tmp_path, monkeypatch):
    blocking = _BlockingPublishStore(tmp_path)
    actor, runtime, store = _actor(tmp_path, store=blocking, checkpoint_every_intervals=1)
    original = _Physical.settle
    def settle(self, runtime, world, occurrence):
        if occurrence.kind == "fatal":
            runtime.advance()
            raise PhysicalSettlementFailure("after native, before world")
        return original(self, runtime, world, occurrence)
    monkeypatch.setattr(_Physical, "settle", settle)
    blocking.block_publish = True
    actor.start()
    try:
        actor.submit(PhysicalOccurrence("good", None), timeout=5)
        assert blocking.publish_started.wait(timeout=5)
        with pytest.raises(PhysicalSettlementFailure):
            actor.submit(PhysicalOccurrence("fatal", None), timeout=5)
        _wait_until_unavailable(actor)
    finally:
        blocking.publish_release.set()
        with pytest.raises(RuntimeError, match="organism actor stopped after failure"):
            actor.close()
    current = store.restore()
    assert runtime.live_tick == 12
    assert blocking.checkpoint_publish_count == 1
    assert current.pointer.current.organism_tick == 11
    assert current.body == b"body-11" and current.world == b"world-11"


def test_actor_stop_and_cold_next_preserve_and_consume_world_return(tmp_path):
    # Custody fixture: actual actor, paired store and world codec; fake native
    # body and fixed sensory bytes. This is not a cognition/physical proof.
    from dsf_ai_service.guala_home_world import home_world_authority
    from dsf_ai_service.guala_physical_return import PendingPhysicalReturn, RETURN_SAMPLE_BYTES
    from dsf_ai_service.guala_world_sensorium import prepare_passive_world_interval

    class ReturnPhysical:
        maximum_native_intervals_per_occurrence = 1

        def settle(self, runtime, world, occurrence):
            runtime.advance()
            if occurrence.kind == "make-return":
                prepared = prepare_passive_world_interval(world)
                after = prepared.execution_receipt.after
                pending = PendingPhysicalReturn(
                    IDENTITY, runtime.live_tick, "a" * 64, after.revision,
                    after.authority_receipt_sha256, bytes(RETURN_SAMPLE_BYTES), (), None,
                )
                world.commit_prepared_action(prepared, physical_return=pending)
            else:
                world.consume_physical_return(world.pending_physical_return)
            return SettlementResult(1, {"custody_fixture": True})

        def unattended(self, runtime, world):
            return self.settle(runtime, world, PhysicalOccurrence("consume", None))

    world = home_world_authority(identity=IDENTITY)
    store = PairedCurrentStore(tmp_path, max_body_bytes=4096, max_world_bytes=4 * 1024 * 1024)
    pointer = store.publish(
        identity=IDENTITY, organism_tick=10, body=b"body-10",
        world=bytes(world.encoded_snapshot()), expected_current_body_sha256=None,
    )
    actor = LeanOrganismActor(
        runtime=_Runtime(b"body-10", 10), world=world, pointer=pointer, store=store,
        physical=ReturnPhysical(), mailbox_capacity=1,
        checkpoint_every_intervals=32, unattended_interval_seconds=60,
    )
    actor.start()
    actor.submit(PhysicalOccurrence("make-return", None), timeout=5)
    held = world.pending_physical_return
    actor.close()
    saved = store.restore()
    cold_world = home_world_authority(identity=IDENTITY, encoded_world=saved.world)
    assert cold_world.pending_physical_return == held
    revision = cold_world.observation_snapshot().revision
    cold = LeanOrganismActor(
        runtime=_Runtime(saved.body, saved.pointer.current.organism_tick),
        world=cold_world, pointer=saved.pointer, store=store,
        physical=ReturnPhysical(), mailbox_capacity=1,
        checkpoint_every_intervals=32, unattended_interval_seconds=60,
    )
    cold.start()
    try:
        cold.submit(PhysicalOccurrence("consume", None), timeout=5)
        assert cold_world.pending_physical_return is None
        assert cold_world.observation_snapshot().revision == revision
    finally:
        cold.close()
    restored = store.restore()
    assert restored.pointer.current.organism_tick == 12
    assert home_world_authority(identity=IDENTITY, encoded_world=restored.world).pending_physical_return is None
