"""Single-owner causal actor for the lean Guala production shell."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass, replace
import hashlib
import hmac
from queue import Empty, Full, Queue
import threading
import time
from typing import Any, Protocol

from dsf_ai_service.lean_checkpoint import (
    CheckpointOutcome,
    CheckpointWork,
    LeanCheckpointWorker,
)
from dsf_ai_service.paired_current_store import CurrentPair, PairedCurrentStore


MAX_PRESSURE_BYTES = 8_000


@dataclass(frozen=True, slots=True)
class PhysicalOccurrence:
    kind: str
    payload: object


@dataclass(frozen=True, slots=True)
class SettlementResult:
    native_interval_count: int
    observation: dict[str, object]
    pressure: tuple[str, bytes] | None = None


class PhysicalSettlementBoundary(Protocol):
    @property
    def maximum_native_intervals_per_occurrence(self) -> int: ...

    def settle(
        self,
        runtime: Any,
        world: Any,
        occurrence: PhysicalOccurrence,
    ) -> SettlementResult: ...

    def unattended(self, runtime: Any, world: Any) -> SettlementResult: ...


@dataclass(frozen=True, slots=True)
class ActorObservation:
    available: bool
    identity: str
    live_tick: int
    persisted_tick: int
    persisted_body_sha256: str
    persisted_world_sha256: str
    checkpoint_outstanding: bool
    durability_blocked: bool
    pending_interval_count: int
    last_occurrence: dict[str, object] | None
    pressure_sha256: str | None
    checkpoint_error: str | None
    cleanup_error: str | None

    def record(self) -> dict[str, object]:
        return {
            "available": self.available,
            "checkpoint_error": self.checkpoint_error,
            "checkpoint_outstanding": self.checkpoint_outstanding,
            "cleanup_error": self.cleanup_error,
            "durability_blocked": self.durability_blocked,
            "identity": self.identity,
            "last_occurrence": self.last_occurrence,
            "live_tick": self.live_tick,
            "pending_interval_count": self.pending_interval_count,
            "persisted_body_sha256": self.persisted_body_sha256,
            "persisted_tick": self.persisted_tick,
            "persisted_world_sha256": self.persisted_world_sha256,
            "pressure_sha256": self.pressure_sha256,
            "schema": "guala.lean_actor_observation.v1",
        }


@dataclass(slots=True)
class _ActorMessage:
    occurrence: PhysicalOccurrence
    result: Future[SettlementResult]


_STOP = object()


class LeanOrganismActor:
    """The only object permitted to call or mutate the runtime and world."""

    def __init__(
        self,
        *,
        runtime: Any,
        world: Any,
        pointer: CurrentPair,
        store: PairedCurrentStore,
        physical: PhysicalSettlementBoundary,
        mailbox_capacity: int,
        checkpoint_every_intervals: int,
        unattended_interval_seconds: float,
    ) -> None:
        if mailbox_capacity <= 0:
            raise ValueError("actor mailbox capacity must be positive")
        if checkpoint_every_intervals <= 0:
            raise ValueError("checkpoint interval count must be positive")
        if unattended_interval_seconds <= 0:
            raise ValueError("unattended interval duration must be positive")
        maximum = physical.maximum_native_intervals_per_occurrence
        if (
            isinstance(maximum, bool)
            or not isinstance(maximum, int)
            or maximum <= 0
            or maximum > checkpoint_every_intervals
        ):
            raise ValueError(
                "physical occurrence bound exceeds one custody cadence"
            )
        self._runtime = runtime
        self._world = world
        self._pointer = pointer
        self._store = store
        self._physical = physical
        self._mailbox: Queue[_ActorMessage | object] = Queue(
            maxsize=mailbox_capacity
        )
        self._checkpoint_every = checkpoint_every_intervals
        self._pending_ceiling = checkpoint_every_intervals * 2
        self._maximum_occurrence_intervals = maximum
        self._unattended_seconds = unattended_interval_seconds
        self._checkpoint = LeanCheckpointWorker(store)
        self._pending_intervals = 0
        self._last_occurrence: dict[str, object] | None = None
        self._pressures: tuple[tuple[str, bytes], ...] = ()
        self._checkpoint_error: str | None = None
        self._cleanup_error: str | None = None
        self._fatal: BaseException | None = None
        self._observation = self._make_observation()
        self._startup_complete = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="guala-organism",
            daemon=False,
        )
        self._started = False

    def start(self) -> None:
        if self._started:
            raise RuntimeError("organism actor already started")
        self._started = True
        self._thread.start()
        self._startup_complete.wait()
        if self._fatal is not None:
            self._thread.join()
            self._started = False
            raise RuntimeError("organism restore verification failed") from self._fatal

    def offer(self, occurrence: PhysicalOccurrence) -> Future[SettlementResult]:
        """Offer one occurrence without adding a web-server worker thread."""

        if not self._started or not self._thread.is_alive():
            if self._fatal is not None:
                raise RuntimeError("organism actor failed") from self._fatal
            raise RuntimeError("organism actor is not running")
        if not isinstance(occurrence, PhysicalOccurrence):
            raise TypeError("actor occurrence changed type")
        future: Future[SettlementResult] = Future()
        try:
            self._mailbox.put_nowait(_ActorMessage(occurrence, future))
        except Full as error:
            raise RuntimeError("organism mailbox is full") from error
        return future

    def submit(
        self,
        occurrence: PhysicalOccurrence,
        *,
        timeout: float | None = None,
    ) -> SettlementResult:
        return self.offer(occurrence).result(timeout=timeout)

    def observation(self) -> dict[str, object]:
        """Return one immutable projection; never call runtime or world."""

        return self._observation.record()

    def pressure(self, receipt: str) -> bytes | None:
        """Return the one bounded cached pressure body; never call the organism."""

        if not isinstance(receipt, str) or len(receipt) != 64:
            return None
        try:
            canonical = bytes.fromhex(receipt).hex()
        except ValueError:
            return None
        held_pressures = self._pressures
        for held_receipt, held_body in held_pressures:
            if hmac.compare_digest(held_receipt, canonical):
                return held_body
        return None

    def close(self) -> None:
        if not self._started:
            self._checkpoint.close()
            return
        if self._thread.is_alive():
            self._mailbox.put(_STOP)
            self._thread.join()
        self._started = False
        if self._fatal is not None:
            raise RuntimeError("organism actor stopped after failure") from self._fatal

    def _live_tick(self) -> int:
        value = self._runtime.live_organism_tick
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RuntimeError("native runtime live tick changed representation")
        return value

    def _verify_restored_authorities(self) -> None:
        current = self._pointer.current
        readiness = self._runtime.readiness()
        if (
            readiness.identity != current.identity
            or readiness.organism_tick != current.organism_tick
            or readiness.state_sha256 != current.body_sha256
            or readiness.state_bytes != current.body_bytes
            or readiness.python_callback_count != 0
            or self._live_tick() != current.organism_tick
        ):
            raise RuntimeError("native runtime differs from paired CURRENT")
        world_body = bytes(self._world.encoded_snapshot())
        if (
            len(world_body) != current.world_bytes
            or hashlib.sha256(world_body).hexdigest() != current.world_sha256
        ):
            raise RuntimeError("physical world differs from paired CURRENT")

    def _durability_blocked(self) -> bool:
        return (
            self._pending_intervals + self._maximum_occurrence_intervals
            > self._pending_ceiling
        )

    def _run(self) -> None:
        next_unattended = time.monotonic() + self._unattended_seconds
        try:
            self._verify_restored_authorities()
            self._startup_complete.set()
            while True:
                self._adopt_checkpoint_if_ready()
                if self._durability_blocked():
                    if not self._checkpoint.outstanding:
                        raise RuntimeError("durability ceiling has no checkpoint")
                    self._refresh_observation(self._live_tick())
                    self._receive_required_checkpoint()
                    continue
                wait = max(0.0, next_unattended - time.monotonic())
                try:
                    message = self._mailbox.get(timeout=wait)
                except Empty:
                    message = None
                if message is _STOP:
                    self._finish_checkpoint()
                    return
                if message is None:
                    self._settle_unattended()
                    next_unattended = time.monotonic() + self._unattended_seconds
                    continue
                assert isinstance(message, _ActorMessage)
                try:
                    result = self._settle(message.occurrence)
                except BaseException as error:
                    message.result.set_exception(error)
                else:
                    message.result.set_result(result)
                next_unattended = time.monotonic() + self._unattended_seconds
        except BaseException as error:
            self._fatal = error
            self._observation = replace(self._observation, available=False)
            self._startup_complete.set()
            self._fail_queued_messages(error)
        finally:
            self._drain_checkpoint_after_stop()
            self._checkpoint.close()

    def _settle_unattended(self) -> None:
        before_tick = self._live_tick()
        result = self._physical.unattended(self._runtime, self._world)
        self._accept_result("unattended", before_tick, result)

    def _settle(self, occurrence: PhysicalOccurrence) -> SettlementResult:
        before_tick = self._live_tick()
        result = self._physical.settle(self._runtime, self._world, occurrence)
        self._accept_result(occurrence.kind, before_tick, result)
        return result

    def _accept_result(
        self,
        kind: str,
        before_tick: int,
        result: SettlementResult,
    ) -> None:
        if not isinstance(result, SettlementResult):
            raise TypeError("physical settlement result changed type")
        if (
            result.native_interval_count <= 0
            or result.native_interval_count > self._maximum_occurrence_intervals
        ):
            raise RuntimeError("physical settlement changed its interval bound")
        pressure_sha256 = None
        if result.pressure is not None:
            pressure_sha256, pressure_body = result.pressure
            if (
                not isinstance(pressure_sha256, str)
                or not isinstance(pressure_body, bytes)
                or not pressure_body
                or len(pressure_body) > MAX_PRESSURE_BYTES
                or len(pressure_body) % 2
                or hashlib.sha256(pressure_body).hexdigest() != pressure_sha256
            ):
                raise RuntimeError("physical pressure receipt changed")
        readiness = self._runtime.readiness()
        live_tick = self._live_tick()
        if readiness.identity != self._pointer.current.identity:
            raise RuntimeError("organism identity changed after settlement")
        if live_tick - before_tick != result.native_interval_count:
            raise RuntimeError("physical settlement changed native interval count")
        if self._pending_intervals + result.native_interval_count > self._pending_ceiling:
            raise RuntimeError("physical settlement breached its declared interval bound")
        if result.pressure is not None:
            prior = tuple(
                held
                for held in self._pressures[:1]
                if not hmac.compare_digest(held[0], result.pressure[0])
            )
            self._pressures = (result.pressure, *prior)
        self._pending_intervals += result.native_interval_count
        self._last_occurrence = {
            "kind": kind,
            "native_interval_count": result.native_interval_count,
            "native_tick": live_tick,
            "pressure_sha256": pressure_sha256,
            **result.observation,
        }
        self._request_checkpoint_if_due()
        self._refresh_observation(live_tick)

    def _request_checkpoint_if_due(self, *, force: bool = False) -> None:
        if self._checkpoint.outstanding or not self._pending_intervals:
            return
        if not force and self._pending_intervals < self._checkpoint_every:
            return
        self._checkpoint.submit(CheckpointWork(
            snapshot=self._runtime.snapshot_lived_state(),
            world=bytes(self._world.encoded_snapshot()),
            identity=self._pointer.current.identity,
            expected_current_body_sha256=self._pointer.current.body_sha256,
        ))

    @staticmethod
    def _outcome_failure(outcome: CheckpointOutcome) -> BaseException | None:
        if outcome.error is not None:
            return outcome.error
        return outcome.cleanup_error

    def _adopt_checkpoint_if_ready(self) -> None:
        if not self._checkpoint.outstanding:
            return
        try:
            outcome = self._checkpoint.receive(timeout=0)
        except TimeoutError:
            return
        self._adopt_checkpoint(outcome)
        failure = self._outcome_failure(outcome)
        if failure is not None:
            raise failure
        self._request_checkpoint_if_due()

    def _receive_required_checkpoint(self) -> None:
        outcome = self._checkpoint.receive(timeout=None)
        self._adopt_checkpoint(outcome)
        failure = self._outcome_failure(outcome)
        if failure is not None:
            raise failure
        self._request_checkpoint_if_due()

    def _adopt_checkpoint(self, outcome: CheckpointOutcome) -> None:
        if not outcome.committed:
            assert outcome.error is not None
            self._checkpoint_error = f"{type(outcome.error).__name__}: {outcome.error}"
            self._refresh_observation(self._live_tick())
            return
        assert outcome.checkpoint is not None and outcome.pointer is not None
        self._runtime.validate_lived_checkpoint(outcome.checkpoint)
        self._runtime.adopt_published_lived_checkpoint(outcome.checkpoint)
        captured = outcome.pointer.current.organism_tick - self._pointer.current.organism_tick
        if captured <= 0 or captured > self._pending_intervals:
            raise RuntimeError("checkpoint interval accounting changed")
        self._pending_intervals -= captured
        self._pointer = outcome.pointer
        self._checkpoint_error = None
        self._cleanup_error = (
            None
            if outcome.cleanup_error is None
            else f"{type(outcome.cleanup_error).__name__}: {outcome.cleanup_error}"
        )
        self._refresh_observation(self._live_tick())

    def _finish_checkpoint(self) -> None:
        while self._pending_intervals or self._checkpoint.outstanding:
            if not self._checkpoint.outstanding:
                self._request_checkpoint_if_due(force=True)
            self._receive_required_checkpoint()

    def _drain_checkpoint_after_stop(self) -> None:
        if not self._checkpoint.outstanding:
            return
        outcome = self._checkpoint.receive(timeout=None)
        if outcome.pointer is not None:
            self._pointer = outcome.pointer

    def _refresh_observation(self, live_tick: int) -> None:
        self._observation = self._make_observation(live_tick)

    def _make_observation(self, live_tick: int | None = None) -> ActorObservation:
        current = self._pointer.current
        return ActorObservation(
            available=True,
            identity=current.identity,
            live_tick=current.organism_tick if live_tick is None else live_tick,
            persisted_tick=current.organism_tick,
            persisted_body_sha256=current.body_sha256,
            persisted_world_sha256=current.world_sha256,
            checkpoint_outstanding=self._checkpoint.outstanding,
            durability_blocked=self._durability_blocked(),
            pending_interval_count=self._pending_intervals,
            last_occurrence=self._last_occurrence,
            pressure_sha256=(
                None if not self._pressures else self._pressures[0][0]
            ),
            checkpoint_error=self._checkpoint_error,
            cleanup_error=self._cleanup_error,
        )

    def _fail_queued_messages(self, error: BaseException) -> None:
        while True:
            try:
                message = self._mailbox.get_nowait()
            except Empty:
                return
            if isinstance(message, _ActorMessage):
                message.result.set_exception(error)
