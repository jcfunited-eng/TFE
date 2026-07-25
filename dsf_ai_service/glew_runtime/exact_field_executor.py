"""Bounded multi-process execution of independent exact native field ports.

Workers run only immutable per-port preparation, the unchanged canonical
L0--L4 trace, and exact basin construction. They never receive Guala, Atlas,
L5, causal-owner, prediction, or persistence state. The parent remains the
sole authority: it reconstructs and verifies the complete six-sense assembly
before any result can enter cognition.
"""

from __future__ import annotations

import atexit
import itertools
import multiprocessing
import os
import queue
import signal
import threading
import time
from dataclasses import dataclass
from typing import Iterable


EXACT_FIELD_WORKER_LIMIT = 4
EXACT_FIELD_PARTITION_LIMIT = 4
# 76 sight + 32 sound + 8 each for touch, smell, taste, and body.
EXACT_FIELD_PORT_LIMIT = 140
EXACT_FIELD_BATCH_DEADLINE_SECONDS = 5.0
EXACT_FIELD_STARTUP_DEADLINE_SECONDS = 30.0
EXACT_FIELD_WORKER_STOP_SECONDS = 2.0


def _set_exact_numeric_thread_boundary() -> None:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"


def _worker_initialize() -> None:
    _set_exact_numeric_thread_boundary()
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _worker_ready() -> int:
    """Prove that each fixed worker can execute the exact native path."""

    # The bounded pause ensures spawn creates and proves the complete fixed
    # worker set rather than allowing one early worker to consume every proof.
    time.sleep(1.0)
    from fractions import Fraction

    from dsf_ai_service.glew_runtime.native_sensory_full_field import (
        NativeSensorySubstreamInput,
    )
    from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
        NativeAxisCoordinate,
        PhysicalSense,
    )

    native = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="exact-field-startup-proof",
        substream_id="startup-proof-0",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("startup-proof", "0"),
        ),
        physical_quantity="light-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(
            Fraction(index, 4) for index in range(5)
        ),
        normalized_signal=(0.0, 0.25, 0.5, 0.25, 0.0),
        phase_turns=(Fraction(0),) * 5,
    )
    results = _build_partition(((
        0,
        native,
        "exact-field-startup-proof",
    ),))
    if (
        len(results) != 1
        or not results[0][4].exact_dsf_field_tuples
    ):
        raise RuntimeError(
            "exact field worker startup proof was incomplete"
        )
    return os.getpid()


def _build_partition(
    jobs: tuple[tuple[int, object, str], ...],
) -> tuple[
    tuple[
        int,
        object,
        tuple[bytes, ...],
        object,
        object,
        tuple[bytes, ...],
        str,
    ],
    ...,
]:
    from dsf_ai_service.glew_runtime.closed_experience import (
        run_ratified_native_l0_l4_trace,
    )
    from dsf_ai_service.glew_runtime.model import ReceiptRegistry
    from dsf_ai_service.glew_runtime.native_sensory_full_field import (
        PROFILE_PAYLOAD,
        _prepare_port,
        _unique_payloads,
    )
    from dsf_ai_service.glew_runtime.story_global_uf_basin import (
        port_kernel_basin_from_trace_record,
    )

    results = []
    for global_index, native, assembly_id in jobs:
        prepared = _prepare_port(native, assembly_id=assembly_id)
        local_registry = ReceiptRegistry.from_payloads(
            profile_payload=PROFILE_PAYLOAD,
            receipt_payloads=tuple(
                payload
                for payload in _unique_payloads(
                    list(prepared.input_payloads)
                )
                if payload != PROFILE_PAYLOAD
            ),
        )
        trace = run_ratified_native_l0_l4_trace(
            stream=prepared.stream,
            adapter=prepared.adapter,
            receipt_registry=local_registry,
        )
        basin, basin_payloads = port_kernel_basin_from_trace_record(
            lane_id=native.sense.value,
            port_id=native.substream_id,
            trace_record=trace,
        )
        results.append((
            global_index,
            prepared.profile,
            prepared.input_payloads,
            trace,
            basin,
            basin_payloads,
            prepared.source_sample_commitment_sha256,
        ))
    return tuple(results)


def _worker_main(
    worker_index: int,
    input_queue: object,
    result_queue: object,
) -> None:
    _worker_initialize()
    try:
        process_id = _worker_ready()
        result_queue.put((
            "ready",
            worker_index,
            process_id,
            None,
        ))
    except BaseException as error:
        result_queue.put((
            "startup_error",
            worker_index,
            os.getpid(),
            f"{type(error).__name__}: {error}",
        ))
        return

    while True:
        command = input_queue.get()
        if command is None:
            return
        batch_id, partition_index, jobs = command
        try:
            result = _build_partition(jobs)
            result_queue.put((
                "result",
                batch_id,
                partition_index,
                result,
            ))
        except BaseException as error:
            result_queue.put((
                "error",
                batch_id,
                partition_index,
                f"{type(error).__name__}: {error}",
            ))


@dataclass(frozen=True, slots=True)
class ExactFieldPortResult:
    global_index: int
    profile: object
    input_payloads: tuple[bytes, ...]
    trace: object
    basin: object
    basin_payloads: tuple[bytes, ...]
    source_sample_commitment_sha256: str


class ExactFieldExecutor:
    """One admitted, statically partitioned exact-field batch at a time."""

    def __init__(self, worker_count: int) -> None:
        if (
            isinstance(worker_count, bool)
            or not isinstance(worker_count, int)
            or not 1 <= worker_count <= EXACT_FIELD_WORKER_LIMIT
        ):
            raise ValueError(
                "exact field worker count is outside its boundary"
            )

        self.worker_count = worker_count
        self._batch_admission = threading.Lock()
        self._worker_control_lock = threading.Lock()
        self._closed = False
        self._resources_closed = False
        self._broken_error: str | None = None
        self._batch_started_at: float | None = None
        self._batch_sequence = 0

        context = multiprocessing.get_context("spawn")
        self._result_queue = context.Queue()
        self._input_queues = tuple(
            context.Queue(maxsize=1)
            for _index in range(worker_count)
        )
        self._workers = tuple(
            context.Process(
                target=_worker_main,
                args=(
                    worker_index,
                    self._input_queues[worker_index],
                    self._result_queue,
                ),
                name=f"guala-exact-field-{worker_index}",
                daemon=False,
            )
            for worker_index in range(worker_count)
        )
        for process in self._workers:
            process.start()

        failures: list[Exception] = []
        ready: dict[int, int] = {}
        pending = set(range(worker_count))
        deadline = (
            time.monotonic()
            + EXACT_FIELD_STARTUP_DEADLINE_SECONDS
        )
        while pending and not failures:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failures.append(RuntimeError(
                    "exact field worker startup exceeded its boundary"
                ))
                break
            try:
                message = self._result_queue.get(
                    timeout=min(0.1, remaining)
                )
            except queue.Empty:
                for worker_index in tuple(pending):
                    process = self._workers[worker_index]
                    if not process.is_alive():
                        pending.remove(worker_index)
                        failures.append(RuntimeError(
                            "exact field worker exited during startup: "
                            f"worker={worker_index} "
                            f"exitcode={process.exitcode}"
                        ))
                continue

            kind, worker_index, process_id, detail = message
            if worker_index not in pending:
                failures.append(RuntimeError(
                    "exact field worker sent duplicate or invalid "
                    f"startup proof: worker={worker_index}"
                ))
                break
            pending.remove(worker_index)
            expected_id = self._workers[worker_index].pid
            if kind != "ready":
                failures.append(RuntimeError(
                    "exact field worker startup failed: "
                    f"worker={worker_index} detail={detail}"
                ))
            elif process_id != expected_id:
                failures.append(RuntimeError(
                    "exact field worker startup identity changed: "
                    f"worker={worker_index} expected={expected_id} "
                    f"observed={process_id}"
                ))
            else:
                ready[worker_index] = process_id

        if failures or len(ready) != worker_count:
            self._closed = True
            self._broken_error = (
                str(failures[0])
                if failures
                else "exact field worker startup proof was incomplete"
            )
            self._terminate_workers()
            if not failures:
                failures.append(RuntimeError(self._broken_error))
            raise ExceptionGroup(
                "exact field worker startup failed",
                failures,
            )

        self.worker_pids = tuple(
            ready[index]
            for index in range(worker_count)
        )

    def _close_queues_locked(self) -> None:
        if self._resources_closed:
            return
        for owned_queue in (
            *self._input_queues,
            self._result_queue,
        ):
            try:
                owned_queue.cancel_join_thread()
            except (AttributeError, OSError, ValueError):
                pass
            try:
                owned_queue.close()
            except (OSError, ValueError):
                pass
        self._resources_closed = True

    def _terminate_workers_locked(self) -> None:
        if self._resources_closed:
            return
        for process in self._workers:
            if process.is_alive():
                process.terminate()
        deadline = time.monotonic() + EXACT_FIELD_WORKER_STOP_SECONDS
        for process in self._workers:
            remaining = max(0.0, deadline - time.monotonic())
            process.join(timeout=remaining)
        survivors = tuple(
            process
            for process in self._workers
            if process.is_alive()
        )
        for process in survivors:
            process.kill()
        kill_deadline = (
            time.monotonic()
            + EXACT_FIELD_WORKER_STOP_SECONDS
        )
        for process in survivors:
            remaining = max(0.0, kill_deadline - time.monotonic())
            process.join(timeout=remaining)
        final_survivors = tuple(
            process.pid
            for process in self._workers
            if process.is_alive()
        )
        self._close_queues_locked()
        if final_survivors:
            raise RuntimeError(
                "exact field workers could not be stopped: "
                f"{final_survivors}"
            )

    def _terminate_workers(self) -> None:
        with self._worker_control_lock:
            self._terminate_workers_locked()

    def _graceful_stop_workers_locked(self) -> None:
        if self._resources_closed:
            return
        sentinel_failure = False
        for input_queue in self._input_queues:
            try:
                input_queue.put(None, timeout=0.1)
            except (OSError, ValueError, queue.Full):
                sentinel_failure = True
                break
        if not sentinel_failure:
            deadline = (
                time.monotonic()
                + EXACT_FIELD_WORKER_STOP_SECONDS
            )
            for process in self._workers:
                remaining = max(0.0, deadline - time.monotonic())
                process.join(timeout=remaining)
        if (
            sentinel_failure
            or any(process.is_alive() for process in self._workers)
        ):
            self._terminate_workers_locked()
            return
        self._close_queues_locked()

    def _break_executor(self, error: str) -> None:
        self._broken_error = error
        self._closed = True
        self._terminate_workers()

    def build_ports(
        self,
        jobs: Iterable[tuple[object, str]],
    ) -> tuple[ExactFieldPortResult, ...]:
        self.assert_healthy()
        if not self._batch_admission.acquire(blocking=False):
            raise RuntimeError(
                "exact field executor batch capacity is full"
            )

        raw: tuple[tuple[object, ...], ...] = ()
        indexed: tuple[tuple[int, object, str], ...] = ()
        try:
            self.assert_healthy()
            bounded_jobs = tuple(itertools.islice(
                jobs,
                EXACT_FIELD_PORT_LIMIT + 1,
            ))
            if not bounded_jobs:
                raise ValueError(
                    "exact field executor requires at least one port"
                )
            if len(bounded_jobs) > EXACT_FIELD_PORT_LIMIT:
                raise ValueError(
                    "exact field executor port boundary exceeded"
                )
            indexed = tuple(
                (index, native, assembly_id)
                for index, (native, assembly_id)
                in enumerate(bounded_jobs)
            )
            self._batch_started_at = time.monotonic()
            self._batch_sequence += 1
            batch_id = self._batch_sequence
            partition_count = min(
                self.worker_count,
                EXACT_FIELD_PARTITION_LIMIT,
                len(indexed),
            )
            partitions = tuple(
                tuple(indexed[start:end])
                for partition_index in range(partition_count)
                for start, end in ((
                    partition_index
                    * len(indexed)
                    // partition_count,
                    (partition_index + 1)
                    * len(indexed)
                    // partition_count,
                ),)
            )
            deadline = (
                self._batch_started_at
                + EXACT_FIELD_BATCH_DEADLINE_SECONDS
            )
            try:
                for partition_index, partition in enumerate(partitions):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError(
                            "exact field batch exceeded its source interval"
                        )
                    self._input_queues[partition_index].put(
                        (
                            batch_id,
                            partition_index,
                            partition,
                        ),
                        timeout=min(0.1, remaining),
                    )
            except (OSError, ValueError, queue.Full, TimeoutError) as error:
                self._break_executor(str(error))
                raise ExceptionGroup(
                    "exact field worker partition failed",
                    [RuntimeError(str(error))],
                ) from error

            pending = set(range(partition_count))
            completed: list[tuple[object, ...]] = []
            failures: list[Exception] = []
            fatal_error: str | None = None
            while pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    fatal_error = (
                        "exact field batch exceeded its source interval"
                    )
                    failures.append(RuntimeError(fatal_error))
                    break
                try:
                    message = self._result_queue.get(
                        timeout=min(0.1, remaining)
                    )
                except queue.Empty:
                    dead = tuple(
                        partition_index
                        for partition_index in pending
                        if not self._workers[
                            partition_index
                        ].is_alive()
                    )
                    if dead:
                        fatal_error = (
                            "exact field worker exited during batch: "
                            f"partitions={dead}"
                        )
                        failures.append(RuntimeError(fatal_error))
                        break
                    continue

                kind, observed_batch, partition_index, payload = (
                    message
                )
                if (
                    observed_batch != batch_id
                    or partition_index not in pending
                ):
                    fatal_error = (
                        "exact field worker returned an invalid batch "
                        "identity"
                    )
                    failures.append(RuntimeError(fatal_error))
                    break
                pending.remove(partition_index)
                if kind == "result":
                    completed.extend(payload)
                elif kind == "error":
                    failures.append(RuntimeError(
                        "exact field worker partition failed: "
                        f"partition={partition_index} {payload}"
                    ))
                else:
                    fatal_error = (
                        "exact field worker returned an invalid result "
                        f"kind: {kind}"
                    )
                    failures.append(RuntimeError(fatal_error))
                    break

            if fatal_error is not None:
                self._break_executor(fatal_error)
            if failures:
                raise ExceptionGroup(
                    "exact field worker partition failed",
                    failures,
                )
            raw = tuple(completed)
        finally:
            self._batch_started_at = None
            self._batch_admission.release()

        ordered = tuple(sorted(raw, key=lambda item: item[0]))
        if tuple(item[0] for item in ordered) != tuple(
            range(len(indexed))
        ):
            raise RuntimeError(
                "exact field executor changed canonical topology order"
            )
        return tuple(
            ExactFieldPortResult(
                global_index=item[0],
                profile=item[1],
                input_payloads=item[2],
                trace=item[3],
                basin=item[4],
                basin_payloads=item[5],
                source_sample_commitment_sha256=item[6],
            )
            for item in ordered
        )

    def close(self) -> None:
        self._closed = True
        if self._batch_admission.acquire(blocking=False):
            try:
                with self._worker_control_lock:
                    if self._broken_error is None:
                        self._graceful_stop_workers_locked()
                    else:
                        self._terminate_workers_locked()
            finally:
                self._batch_admission.release()
            return
        self._terminate_workers()

    def assert_healthy(self) -> None:
        if self._closed:
            raise RuntimeError("exact field executor is closed")
        if self._broken_error is not None:
            raise RuntimeError(
                "exact field executor worker failed: "
                f"{self._broken_error}"
            )
        if (
            self._batch_started_at is not None
            and time.monotonic() - self._batch_started_at
            > EXACT_FIELD_BATCH_DEADLINE_SECONDS
        ):
            raise RuntimeError(
                "exact field executor batch exceeded its source interval"
            )
        unavailable = tuple(
            (
                worker_index,
                process.pid,
                process.exitcode,
            )
            for worker_index, process in enumerate(self._workers)
            if (
                process.pid != self.worker_pids[worker_index]
                or not process.is_alive()
            )
        )
        if unavailable:
            raise RuntimeError(
                "exact field executor workers are unavailable: "
                f"{unavailable}"
            )


_OWNER_LOCK = threading.Lock()
_OWNER: ExactFieldExecutor | None = None


def start_exact_field_executor() -> ExactFieldExecutor:
    global _OWNER
    with _OWNER_LOCK:
        if _OWNER is not None:
            return _OWNER
        cpu_count = os.cpu_count() or 1
        if cpu_count < EXACT_FIELD_WORKER_LIMIT:
            raise RuntimeError(
                "production exact field executor requires four CPUs"
            )
        # Spawned interpreters inherit this boundary before importing NumPy;
        # setting it only in worker initialization can be too late.
        _set_exact_numeric_thread_boundary()
        _OWNER = ExactFieldExecutor(EXACT_FIELD_WORKER_LIMIT)
        return _OWNER


def exact_field_executor() -> ExactFieldExecutor | None:
    with _OWNER_LOCK:
        return _OWNER


def stop_exact_field_executor() -> None:
    global _OWNER
    with _OWNER_LOCK:
        owner = _OWNER
        _OWNER = None
    if owner is not None:
        owner.close()


atexit.register(stop_exact_field_executor)


__all__ = (
    "EXACT_FIELD_PARTITION_LIMIT",
    "EXACT_FIELD_PORT_LIMIT",
    "EXACT_FIELD_WORKER_LIMIT",
    "ExactFieldExecutor",
    "ExactFieldPortResult",
    "exact_field_executor",
    "start_exact_field_executor",
    "stop_exact_field_executor",
)
