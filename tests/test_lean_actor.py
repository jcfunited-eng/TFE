from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import threading

from dsf_ai_service.lean_actor import (
    LeanOrganismActor,
    PhysicalOccurrence,
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


def _actor(root: Path) -> tuple[LeanOrganismActor, _Runtime, PairedCurrentStore]:
    body = b"body-10"
    world_body = b"world-10"
    store = PairedCurrentStore(
        root,
        max_body_bytes=4096,
        max_world_bytes=4096,
    )
    pointer = store.publish(
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
        store=store,
        physical=_Physical(),
        mailbox_capacity=2,
        checkpoint_every_intervals=2,
        unattended_interval_seconds=60,
    )
    return actor, runtime, store


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
        try:
            actor.submit(PhysicalOccurrence("refuse", None), timeout=5)
        except RuntimeError as error:
            assert str(error) == "physical refusal"
        else:
            raise AssertionError("physical refusal was hidden")
        accepted = actor.submit(PhysicalOccurrence("light", b"one"), timeout=5)
        assert accepted.observation == {"accepted": True}
    finally:
        actor.close()

    assert store.restore().pointer.current.organism_tick == 11
