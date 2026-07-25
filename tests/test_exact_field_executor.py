from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import itertools
import os
import signal
import time

import numpy as np
import pytest

import dsf_ai_service.glew_runtime.exact_field_executor as executor_module
from dsf_ai_service.glew_runtime.exact_field_executor import (
    EXACT_FIELD_PORT_LIMIT,
    exact_field_executor,
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5Owner,
    _verify_constructed_experience,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


SOURCE_START = Fraction(17, 5)
SOURCE_END = SOURCE_START + 5


def _sound_inputs():
    sample_count = REQUIRED_SAMPLE_RATE_HZ * 5
    source_time = (
        np.arange(sample_count, dtype=np.float64)
        / REQUIRED_SAMPLE_RATE_HZ
    )
    capture = transduce_auditory_full_field(
        0.4 * np.sin(2.0 * np.pi * 440.0 * source_time),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    return tuple(auditory_kernel_component_inputs(
        capture,
        source_anchor=SOURCE_START,
    ))


def _sight_inputs():
    source_times = tuple(
        SOURCE_START + Fraction(index, 200)
        for index in range(8)
    )
    return tuple(
        NativeSensorySubstreamInput(
            sense=PhysicalSense.SIGHT,
            sensor_id="test-camera",
            substream_id=f"region-{topology_index}",
            topology_index=topology_index,
            coordinates=(
                NativeAxisCoordinate(
                    "retinal-region",
                    str(topology_index),
                ),
            ),
            physical_quantity="light-intensity",
            physical_unit="normalized-intensity",
            source_times=source_times,
            normalized_signal=tuple(
                (topology_index + sample_index) / 64
                for sample_index in range(8)
            ),
            phase_turns=(Fraction(0),) * 8,
        )
        for topology_index in range(34)
    )


def _build(inputs):
    return build_six_sense_full_field(
        assembly_id="exact-field-executor-equivalence",
        source_time_start=SOURCE_START,
        source_time_end=SOURCE_END,
        observed_substreams={
            PhysicalSense.SIGHT: _sight_inputs(),
            PhysicalSense.SOUND: inputs,
        },
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in (PhysicalSense.SIGHT, PhysicalSense.SOUND)
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )


def _build_transaction(inputs):
    return build_transaction_owned_six_sense_full_field(
        assembly_id="exact-field-executor-equivalence",
        source_time_start=SOURCE_START,
        source_time_end=SOURCE_END,
        observed_substreams={
            PhysicalSense.SIGHT: _sight_inputs(),
            PhysicalSense.SOUND: inputs,
        },
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in (PhysicalSense.SIGHT, PhysicalSense.SOUND)
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )


def test_parallel_port_construction_is_byte_exact_to_serial() -> None:
    stop_exact_field_executor()
    inputs = _sound_inputs()
    assert len(inputs) == 32
    assert {len(item.normalized_signal) for item in inputs} == {500}
    assert sum(len(item.normalized_signal) for item in inputs) == 16_000
    serial = _build(inputs)
    try:
        owner = start_exact_field_executor()
        assert owner.worker_count == 4
        assert len(owner.worker_pids) == 4
        owner.assert_healthy()
        parallel = _build(inputs)
    finally:
        stop_exact_field_executor()

    assert exact_field_executor() is None
    assert parallel.boundary == serial.boundary
    assert parallel.receipt_registry == serial.receipt_registry
    assert (
        parallel.source_sample_commitments
        == serial.source_sample_commitments
    )
    parallel.boundary.verify(parallel.receipt_registry)


def test_transaction_authority_cannot_be_copied_onto_changed_objects() -> None:
    inputs = _sound_inputs()
    public = _build(inputs)
    transaction = _build_transaction(inputs)
    transaction.verify_construction()
    assert not public.has_transaction_construction_authority

    copied_boundary = replace(
        transaction,
        boundary=public.boundary,
    )
    copied_registry = replace(
        transaction,
        receipt_registry=public.receipt_registry,
    )
    copied_commitments = replace(
        transaction,
        source_sample_commitments=tuple(
            list(transaction.source_sample_commitments)
        ),
    )
    for copied in (
        copied_boundary,
        copied_registry,
        copied_commitments,
    ):
        with pytest.raises(
            ValueError,
            match="construction authority was copied",
        ):
            copied.verify_construction()


def test_parent_rejects_worker_changed_source_authority(
    monkeypatch,
) -> None:
    inputs = _sound_inputs()
    stop_exact_field_executor()
    try:
        owner = start_exact_field_executor()
        canonical_build_ports = owner.build_ports

        def changed_build_ports(jobs):
            results = canonical_build_ports(jobs)
            return (
                replace(
                    results[0],
                    source_sample_commitment_sha256="f" * 64,
                ),
                *results[1:],
            )

        monkeypatch.setattr(owner, "build_ports", changed_build_ports)
        with pytest.raises(
            RuntimeError,
            match="changed native input authority",
        ):
            _build_transaction(inputs)
    finally:
        stop_exact_field_executor()


def test_transaction_l5_verifier_rejects_changed_identity() -> None:
    built = _build_transaction(_sound_inputs())
    experience = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        event_boundary="utterance",
    )
    assert experience is not None
    changed = replace(
        experience,
        experience_id="wrong-experience-id",
    )
    with pytest.raises(
        ReceiptError,
        match="experience identity was altered",
    ):
        _verify_constructed_experience(
            experience=changed,
            built=built,
        )


def test_required_executor_never_silently_runs_serial(
    monkeypatch,
) -> None:
    stop_exact_field_executor()
    monkeypatch.setenv(
        "GUALA_EXACT_FIELD_EXECUTOR_REQUIRED",
        "1",
    )
    with pytest.raises(
        RuntimeError,
        match="required exact field executor owner is absent",
    ):
        _build(_sound_inputs())


def test_executor_rejects_unbounded_port_input_before_submission() -> None:
    stop_exact_field_executor()
    try:
        owner = start_exact_field_executor()
        native = _sight_inputs()[0]
        with pytest.raises(
            ValueError,
            match="port boundary exceeded",
        ):
            owner.build_ports(itertools.repeat(
                (native, "unbounded-input"),
                EXACT_FIELD_PORT_LIMIT + 1,
            ))
        owner.assert_healthy()
    finally:
        stop_exact_field_executor()


def test_worker_death_fails_health_without_serial_fallback() -> None:
    stop_exact_field_executor()
    try:
        owner = start_exact_field_executor()
        os.kill(owner.worker_pids[0], signal.SIGKILL)
        deadline = time.monotonic() + 3.0
        while True:
            try:
                owner.assert_healthy()
            except RuntimeError:
                break
            assert time.monotonic() < deadline
            time.sleep(0.01)
        with pytest.raises(RuntimeError):
            owner.build_ports((
                (_sight_inputs()[0], "worker-death"),
            ))
    finally:
        stop_exact_field_executor()


def test_startup_deadline_terminates_unready_workers(
    monkeypatch,
) -> None:
    stop_exact_field_executor()
    monkeypatch.setattr(
        executor_module,
        "EXACT_FIELD_STARTUP_DEADLINE_SECONDS",
        0.001,
    )
    started = time.monotonic()
    with pytest.raises(
        ExceptionGroup,
        match="worker startup failed",
    ):
        start_exact_field_executor()
    assert time.monotonic() - started < 5.0
    assert exact_field_executor() is None


def test_batch_deadline_terminates_pool_before_releasing_admission(
    monkeypatch,
) -> None:
    stop_exact_field_executor()
    owner = start_exact_field_executor()
    monkeypatch.setattr(
        executor_module,
        "EXACT_FIELD_BATCH_DEADLINE_SECONDS",
        0.001,
    )
    started = time.monotonic()
    try:
        with pytest.raises(
            ExceptionGroup,
            match="worker partition failed",
        ):
            owner.build_ports((
                (_sight_inputs()[0], "batch-timeout"),
            ))
        assert time.monotonic() - started < 5.0
        with pytest.raises(RuntimeError, match="closed"):
            owner.assert_healthy()
    finally:
        stop_exact_field_executor()
