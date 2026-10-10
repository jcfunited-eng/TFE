"""Single-owner causal actor for the lean Guala production shell."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass, replace
import base64
import collections
import hashlib
import hmac
from queue import Empty, Full, Queue
import threading
import time
from typing import Any, Protocol
from uuid import uuid4

from dsf_ai_service.lean_checkpoint import (
    CheckpointOutcome,
    CheckpointWork,
    LeanCheckpointWorker,
)
from dsf_ai_service.paired_current_store import CurrentPair, PairedCurrentStore


MAX_PRESSURE_BYTES = 8_000
# External listening budget, never a cognitive or physical limit.
MAX_HELD_PRESSURE_BYTES = 256_000
MAX_HELD_PRESSURES = MAX_HELD_PRESSURE_BYTES // MAX_PRESSURE_BYTES
MAX_PRESSURE_BATCH = 8

from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence


class PhysicalSettlementFailure(RuntimeError):
    """The live pair cannot continue; only its good checkpoint may recover."""


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
        self._mailbox_capacity = mailbox_capacity
        self._checkpoint_every = checkpoint_every_intervals
        self._pending_ceiling = checkpoint_every_intervals * 2
        self._maximum_occurrence_intervals = maximum
        self._unattended_seconds = unattended_interval_seconds
        self._checkpoint = LeanCheckpointWorker(store)
        self._pending_intervals = 0
        self._last_occurrence: dict[str, object] | None = None
        # Stream nonce is ephemeral HTTP transport identity, not organism identity.
        self._pressure_stream = uuid4().hex
        self._pressure_feed: tuple[int, tuple[tuple[int, str, bytes], ...]] = (0, ())
        self._checkpoint_error: str | None = None
        self._cleanup_error: str | None = None
        self._fatal: BaseException | None = None
        self._observation = self._make_observation()
        self._published = threading.Condition()
        self._startup_complete = threading.Event()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._lock = threading.Lock()
        self._staged_visual: tuple[PhysicalOccurrence, list[Future[SettlementResult]]] | None = None
        self._staged_audio: collections.deque[tuple[PhysicalOccurrence, Future[SettlementResult]]] = collections.deque(maxlen=32)
        self._staged_caregiver: collections.deque[tuple[PhysicalOccurrence, Future[SettlementResult]]] = collections.deque(maxlen=mailbox_capacity)
        self._staged_legacy: collections.deque[tuple[PhysicalOccurrence, Future[SettlementResult]]] = collections.deque(maxlen=mailbox_capacity)
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
        """Offer one occurrence through independent sensory admission lanes."""

        if not self._started or not self._thread.is_alive():
            if self._fatal is not None:
                raise RuntimeError("organism actor failed") from self._fatal
            raise RuntimeError("organism actor is not running")
        if not isinstance(occurrence, PhysicalOccurrence):
            raise TypeError("actor occurrence changed type")
        future: Future[SettlementResult] = Future()
        with self._lock:
            payload = occurrence.payload
            if occurrence.kind == "sensory" and isinstance(payload, LeanSensoryOccurrence):
                if payload.source == "camera":
                    # V23: superseded frames receive explicit superseded status with their own receipt
                    if self._staged_visual is not None:
                        old_occ, old_futures = self._staged_visual
                        old_payload = old_occ.payload
                        old_receipt = getattr(old_payload, "source_receipt_sha256", None) if old_payload else None
                        superseded_result = SettlementResult(
                            native_interval_count=0,
                            observation={
                                "status": "superseded",
                                "delivered": False,
                                "superseded": True,
                                "source_receipt_sha256": old_receipt,
                            },
                        )
                        for old_f in old_futures:
                            if old_f.set_running_or_notify_cancel():
                                old_f.set_result(superseded_result)
                    self._staged_visual = (occurrence, [future])
                    self._wake_event.set()
                    return future
                elif payload.source == "microphone":
                    if len(self._staged_audio) >= self._staged_audio.maxlen:
                        raise RuntimeError("acoustic admission queue is full")
                    self._staged_audio.append((occurrence, future))
                    self._wake_event.set()
                    return future
                elif (
                    payload.present_food is not None
                    or payload.from_object is not None
                    or payload.guided_vocal_drives is not None
                    or payload.source in ("guided-vocal-microphone", "guided-body-microphone", "card-microphone")
                ):
                    if len(self._staged_caregiver) >= self._staged_caregiver.maxlen:
                        raise RuntimeError("caregiver admission queue is full")
                    self._staged_caregiver.append((occurrence, future))
                    self._wake_event.set()
                    return future

            if len(self._staged_legacy) >= self._staged_legacy.maxlen:
                raise RuntimeError("organism mailbox is full")
            self._staged_legacy.append((occurrence, future))
            self._wake_event.set()
            return future

    def submit(
        self,
        occurrence: PhysicalOccurrence,
        timeout: float | None = None,
    ) -> SettlementResult:
        return self.offer(occurrence).result(timeout=timeout)

    def observation(self) -> dict[str, object]:
        return self._observation.record()

    def observation_after(
        self,
        tick: int,
        timeout: float,
    ) -> dict[str, object]:
        with self._published:
            if self._observation.live_tick > tick:
                return self._observation.record()
            deadline = time.monotonic() + timeout
            while self._observation.live_tick <= tick:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._published.wait(timeout=remaining)
            return self._observation.record()

    def pressure_feed(
        self,
        stream: str | None,
        after: int | None,
    ) -> dict[str, object]:
        if stream is not None and stream != self._pressure_stream:
            raise ValueError("pressure feed stream changed")
        evicted, held = self._pressure_feed
        if after is not None and after < evicted:
            raise ValueError("pressure history was evicted")
        selected = held if after is None else tuple(p for p in held if p[0] > after)
        items = selected[:MAX_PRESSURE_BATCH]
        next_after = items[-1][0] if items else (evicted if after is None else after)
        return {
            "after": next_after,
            "pressures": [
                {
                    "native_tick": tick,
                    "receipt_sha256": receipt,
                    "sample_count": len(body) // 2,
                }
                for tick, receipt, body in items
            ],
            "schema": "guala.lean_pressure_feed.v1",
            "stream": self._pressure_stream,
        }

    def pressure(self, receipt: str) -> bytes | None:
        for _tick, held_receipt, body in reversed(self._pressure_feed[1]):
            if held_receipt == receipt:
                return body
        return None

    def close(self) -> None:
        if not self._started:
            return
        self._stop_event.set()
        self._wake_event.set()
        self._thread.join()
        self._started = False

    def _verify_restored_authorities(self) -> None:
        readiness = self._runtime.readiness()
        current = self._pointer.current
        if readiness.identity != current.identity:
            raise RuntimeError("restored runtime identity differs from paired CURRENT")
        if readiness.organism_tick != current.organism_tick:
            raise RuntimeError("restored runtime tick differs from paired CURRENT")

    def _live_tick(self) -> int:
        return self._runtime.readiness().organism_tick

    def _durability_blocked(self) -> bool:
        return self._pending_intervals >= self._pending_ceiling

    def _extract_settlement_work(
        self,
    ) -> tuple[PhysicalOccurrence, list[Future[SettlementResult]]] | None:
        with self._lock:
            # Caregiver lane takes precedence
            if self._staged_caregiver:
                occ, fut = self._staged_caregiver.popleft()
                return (occ, [fut])

            # Legacy queue
            if self._staged_legacy:
                occ, fut = self._staged_legacy.popleft()
                return (occ, [fut])

            # Simultaneous visual + acoustic streams unite into time-aligned occurrence (V24: verified clock overlap)
            if self._staged_visual is not None and self._staged_audio:
                vis_occ, vis_futures = self._staged_visual
                aud_occ, aud_future = self._staged_audio[0]
                vis_payload = vis_occ.payload
                aud_payload = aud_occ.payload
                assert isinstance(vis_payload, LeanSensoryOccurrence)
                assert isinstance(aud_payload, LeanSensoryOccurrence)
                t_vis = vis_payload.t_capture_ms
                t_aud = aud_payload.t_capture_ms
                # Strict clock alignment: join only if both have capture timestamps within 250ms interval
                if t_vis is not None and t_aud is not None and abs(t_vis - t_aud) <= 250:
                    self._staged_visual = None
                    self._staged_audio.popleft()
                    united = LeanSensoryOccurrence(
                        source="camera-microphone",
                        retina_rgb_u8=vis_payload.retina_rgb_u8,
                        pressure_s16le=aud_payload.pressure_s16le,
                        guided_vocal_drives=None,
                        present_food=None,
                        from_object=None,
                        focal_origin=vis_payload.focal_origin,
                        focal_pitch_millidegrees=vis_payload.focal_pitch_millidegrees,
                        focal_crop_dimensions=vis_payload.focal_crop_dimensions,
                        t_capture_ms=min(t_vis, t_aud),
                    )
                    return (PhysicalOccurrence("sensory", united), [*vis_futures, aud_future])
                elif t_aud is not None and t_vis is not None and t_aud < t_vis:
                    self._staged_audio.popleft()
                    return (aud_occ, [aud_future])
                elif t_vis is not None and t_aud is not None and t_vis < t_aud:
                    self._staged_visual = None
                    return (vis_occ, vis_futures)
                else:
                    self._staged_audio.popleft()
                    return (aud_occ, [aud_future])

            # Visual only
            if self._staged_visual is not None:
                vis_occ, vis_futures = self._staged_visual
                self._staged_visual = None
                return (vis_occ, vis_futures)

            # Acoustic only
            if self._staged_audio:
                aud_occ, aud_future = self._staged_audio.popleft()
                return (aud_occ, [aud_future])

            return None

    def _run(self) -> None:
        next_interval = time.monotonic() + self._unattended_seconds
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

                if self._stop_event.is_set():
                    self._finish_checkpoint()
                    return

                wait = max(0.0, next_interval - time.monotonic())
                # V26: wait for wake event or scheduled interval timeout
                self._wake_event.wait(timeout=wait)
                self._wake_event.clear()

                if self._stop_event.is_set():
                    self._finish_checkpoint()
                    return

                now = time.monotonic()
                work = self._extract_settlement_work()
                if work is None:
                    if now < next_interval:
                        continue
                    next_interval = max(now, next_interval + self._unattended_seconds)
                    self._settle_unattended()
                    continue

                next_interval = max(now, next_interval + self._unattended_seconds)
                occurrence, futures = work
                active_futures = [f for f in futures if f.set_running_or_notify_cancel()]
                try:
                    result = self._settle(occurrence)
                except BaseException as error:
                    for f in active_futures:
                        f.set_exception(error)
                    if isinstance(error, PhysicalSettlementFailure):
                        raise
                else:
                    for f in active_futures:
                        f.set_result(result)
        except BaseException as error:
            self._fatal = error
            # The cause of an actor's death is written where it can be read
            # (the container log); a silent death cost a live diagnosis.
            import traceback
            print("FATAL: physical actor stopped at tick", self._observation.live_tick, "-", repr(error), flush=True)
            traceback.print_exc()
            self._observation = replace(self._observation, available=False)
            with self._published:
                self._published.notify_all()  # waiting observers learn of failure now
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
        try:
            self._accept_result(occurrence.kind, before_tick, result)
        except BaseException as error:
            raise PhysicalSettlementFailure("post-settlement acceptance failed") from error
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
            evicted, held = self._pressure_feed
            if len(held) == MAX_HELD_PRESSURES:
                evicted, held = held[0][0], held[1:]
            # Identical PCM from distinct native intervals remains distinct.
            self._pressure_feed = (
                evicted, (*held, (live_tick, *result.pressure)),
            )
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
        with self._published:
            self._published.notify_all()

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
                None if not self._pressure_feed[1] else self._pressure_feed[1][-1][1]
            ),
            checkpoint_error=self._checkpoint_error,
            cleanup_error=self._cleanup_error,
        )

    def _fail_queued_messages(self, error: BaseException) -> None:
        with self._lock:
            if self._staged_visual is not None:
                _, futures = self._staged_visual
                for f in futures:
                    f.set_exception(error)
                self._staged_visual = None
            while self._staged_audio:
                _, f = self._staged_audio.popleft()
                f.set_exception(error)
            while self._staged_caregiver:
                _, f = self._staged_caregiver.popleft()
                f.set_exception(error)
            while self._staged_legacy:
                _, f = self._staged_legacy.popleft()
                f.set_exception(error)
