"""Depth-one checkpoint encoding for the lean Guala runtime.

The worker receives an already-taken native snapshot and matched world bytes.
It can encode and persist those values, but it has no reference to the living
runtime and therefore cannot advance, validate, adopt, or roll back cognition.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from queue import Empty, Full, Queue
import threading
import time
from typing import Any

from dsf_ai_service.paired_current_store import CurrentPair, PairedCurrentStore


@dataclass(frozen=True, slots=True)
class CheckpointWork:
    snapshot: Any
    world: bytes
    identity: str
    expected_current_body_sha256: str


@dataclass(frozen=True, slots=True)
class CheckpointOutcome:
    checkpoint: Any | None
    pointer: CurrentPair | None
    error: BaseException | None
    cleanup_error: BaseException | None
    encode_wall_ms: float
    publish_wall_ms: float
    body_bytes: int
    world_bytes: int

    @property
    def committed(self) -> bool:
        return self.pointer is not None and self.error is None


_STOP = object()


class LeanCheckpointWorker:
    """One worker, one outstanding snapshot, no retry or cognition access."""

    def __init__(self, store: PairedCurrentStore) -> None:
        if not isinstance(store, PairedCurrentStore):
            raise TypeError("checkpoint worker requires a paired current store")
        self._store = store
        self._work: Queue[CheckpointWork | object] = Queue(maxsize=1)
        self._results: Queue[CheckpointOutcome] = Queue(maxsize=1)
        self._outstanding = False
        self._closed = False
        self._thread = threading.Thread(
            target=self._run,
            name="guala-checkpoint",
            daemon=False,
        )
        self._thread.start()

    @property
    def outstanding(self) -> bool:
        return self._outstanding

    def submit(self, work: CheckpointWork) -> None:
        """Submit from the sole organism actor; never queues a second body."""

        if self._closed:
            raise RuntimeError("checkpoint worker is closed")
        if self._outstanding:
            raise RuntimeError("one checkpoint is already outstanding")
        if not isinstance(work, CheckpointWork):
            raise TypeError("checkpoint work changed type")
        if not isinstance(work.world, bytes) or not work.world:
            raise ValueError("checkpoint world is empty")
        try:
            self._work.put_nowait(work)
        except Full as error:
            raise RuntimeError("checkpoint work queue exceeded depth one") from error
        self._outstanding = True

    def receive(self, timeout: float | None = None) -> CheckpointOutcome:
        """Receive from the sole actor and reopen the single submission slot."""

        if not self._outstanding:
            raise RuntimeError("no checkpoint is outstanding")
        try:
            result = self._results.get(timeout=timeout)
        except Empty as error:
            raise TimeoutError("checkpoint outcome is not ready") from error
        self._outstanding = False
        return result

    def close(self) -> None:
        if self._closed:
            return
        if self._outstanding:
            raise RuntimeError("cannot close with an outstanding checkpoint")
        self._closed = True
        self._work.put(_STOP)
        self._thread.join()

    def _run(self) -> None:
        while True:
            work = self._work.get()
            if work is _STOP:
                return
            assert isinstance(work, CheckpointWork)
            self._results.put(self._execute(work))

    def _execute(self, work: CheckpointWork) -> CheckpointOutcome:
        checkpoint = None
        pointer = None
        error = None
        cleanup_error = None
        encode_wall_ms = 0.0
        publish_wall_ms = 0.0
        body_bytes = 0
        try:
            encode_started = time.perf_counter()
            checkpoint = work.snapshot.prepare_checkpoint()
            body = bytes(checkpoint.encoded_generation())
            encode_wall_ms = (time.perf_counter() - encode_started) * 1000.0
            body_bytes = len(body)
            if checkpoint.organism_tick != work.snapshot.organism_tick:
                raise RuntimeError("checkpoint changed snapshot tick")
            if checkpoint.state_bytes != body_bytes:
                raise RuntimeError("checkpoint changed encoded byte count")
            if checkpoint.state_sha256 != hashlib.sha256(body).hexdigest():
                raise RuntimeError("checkpoint changed encoded receipt")
            publish_started = time.perf_counter()
            pointer = self._store.publish(
                identity=work.identity,
                organism_tick=checkpoint.organism_tick,
                body=body,
                world=work.world,
                expected_current_body_sha256=(
                    work.expected_current_body_sha256
                ),
            )
            publish_wall_ms = (time.perf_counter() - publish_started) * 1000.0
            try:
                self._store.reconcile(pointer)
            except BaseException as caught_cleanup_error:
                cleanup_error = caught_cleanup_error
        except BaseException as caught_error:
            error = caught_error
        return CheckpointOutcome(
            checkpoint=checkpoint if pointer is not None else None,
            pointer=pointer,
            error=error,
            cleanup_error=cleanup_error,
            encode_wall_ms=encode_wall_ms,
            publish_wall_ms=publish_wall_ms,
            body_bytes=body_bytes,
            world_bytes=len(work.world),
        )
