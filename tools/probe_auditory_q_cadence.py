"""Measure the authenticated 48-second PCM schedule through live mono q.

The probe uses the public sound-frame boundary and the receipted candidate
schedule.  It reports deterministic transport continuity, per-two-second
settlement latency, source-clock backlog, exact q state bytes, and whether a
cell grown from the independent Hello experiences fires in the later
Hello-plus-Daddy overlap.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import statistics
import time
import wave

import dsf_ai_service.app as app_module
import dsf_ai_service.substrate.auditory_live_motif as live_motif_module
import dsf_ai_service.substrate.auditory_q_process as q_process_module
import dsf_ai_service.substrate.auditory_recurrent_motif as peak_module
from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_CHUNK_SAMPLES,
    PCM_SAMPLE_RATE_HZ,
    AuditoryPCMStreamRegistry,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from tools.probe_guala_candidate_browser import (
    HELLO_LEARNING_SETTLEMENT_SEQUENCE,
    OVERLAP_FIRING_SETTLEMENT_SEQUENCE,
    build_cognitive_proof_wav,
)
from tools.probe_guala_pcm_cadence import _post


def _percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[(95 * (len(ordered) - 1) + 99) // 100]


def main() -> None:
    admission_only = (
        os.environ.get("GUALA_Q_CADENCE_ADMISSION_ONLY") == "1"
    )
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "0"
    os.environ["WAVE_ATLAS_ENABLED"] = "0"
    os.environ["WAVE_SUMMARY_ENQUEUE_ENABLED"] = "0"
    os.environ["SELF_HEARING_ENABLED"] = "0"
    os.environ["GUALA_EXACT_FIELD_EXECUTOR_REQUIRED"] = "1"
    os.environ["GUALA_CAUSAL_ACTION_KEY"] = (
        "authenticated-q-cadence-probe-authority"
    )

    schedule = build_cognitive_proof_wav()
    with wave.open(str(schedule["wav_path"]), "rb") as source:
        pcm = source.readframes(source.getnframes())
    chunk_bytes = PCM_CHUNK_SAMPLES * 2
    chunks = tuple(
        pcm[offset:offset + chunk_bytes]
        for offset in range(0, len(pcm), chunk_bytes)
    )
    if any(len(value) != chunk_bytes for value in chunks):
        raise RuntimeError("authenticated cadence schedule is not 2s aligned")

    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    peak_extraction_records: list[tuple[str, float]] = []
    q_operation_seconds: dict[str, list[float]] = {
        "compose": [],
        "fire": [],
        "live_result": [],
        "observe": [],
        "prepare": [],
        "process_commit": [],
        "process_prepare": [],
        "receptor_experience": [],
        "state_encode": [],
    }
    original_peak_extractor = peak_module._peak_atoms_from_experience
    original_compose = peak_module.compose_contiguous_receptor_experiences
    original_fire = peak_module.AuditoryRecurrentMotifOwner.fire
    original_live_result = live_motif_module.build_live_motif_result
    original_observe = peak_module.AuditoryRecurrentMotifOwner.observe
    original_prepare = peak_module.AuditoryRecurrentMotifOwner.prepare
    original_receptor_experience = (
        peak_module.receptor_experience_from_full_field_event
    )
    original_state_encode = peak_module._peak_state_encoded
    original_process_commit = q_process_module.AuditoryQProcessOwner.commit
    original_process_prepare = q_process_module.AuditoryQProcessOwner.prepare

    def measured(name, function):
        def invoke(*args, **kwargs):
            started = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - started
                q_operation_seconds[name].append(elapsed)
                if name.startswith("process_"):
                    print(
                        f"[auditory-q-process] {name}={elapsed:.6f}",
                        flush=True,
                    )
        return invoke

    def measured_peak_extractor(*args, **kwargs):
        started = time.perf_counter()
        result = original_peak_extractor(*args, **kwargs)
        peak_extraction_records.append((
            args[0].authority_receipt_sha256,
            time.perf_counter() - started,
        ))
        return result

    peak_module._peak_atoms_from_experience = measured_peak_extractor
    peak_module.compose_contiguous_receptor_experiences = measured(
        "compose",
        original_compose,
    )
    peak_module.AuditoryRecurrentMotifOwner.fire = measured(
        "fire",
        original_fire,
    )
    live_motif_module.build_live_motif_result = measured(
        "live_result",
        original_live_result,
    )
    peak_module.AuditoryRecurrentMotifOwner.observe = measured(
        "observe",
        original_observe,
    )
    peak_module.AuditoryRecurrentMotifOwner.prepare = measured(
        "prepare",
        original_prepare,
    )
    peak_module.receptor_experience_from_full_field_event = measured(
        "receptor_experience",
        original_receptor_experience,
    )
    peak_module._peak_state_encoded = measured(
        "state_encode",
        original_state_encode,
    )
    q_process_module.AuditoryQProcessOwner.commit = measured(
        "process_commit",
        original_process_commit,
    )
    q_process_module.AuditoryQProcessOwner.prepare = measured(
        "process_prepare",
        original_process_prepare,
    )
    engine = Guala()
    neutral_status = engine._auditory_recurrent_motif_owner.status()
    if (
        neutral_status["motif_neuron_count"] != 0
        or neutral_status["pending_peak_cell_count"] != 0
    ):
        raise RuntimeError(
            "auditory q cadence did not begin from a neutral q bank"
        )
    engine.prewarm_auditory_q_process()
    prewarmed_status = engine._auditory_recurrent_motif_owner.status()
    if (
        prewarmed_status["motif_neuron_count"] != 0
        or prewarmed_status["pending_peak_cell_count"] != 0
        or prewarmed_status != neutral_status
    ):
        raise RuntimeError(
            "auditory q prewarm observed or cached scheduled experience"
        )
    original_terminal_advance = (
        engine.advance_continuous_auditory_terminal
    )
    original_q_settle = engine._settle_auditory_q_process_task
    if admission_only:
        from dsf_ai_service.substrate.auditory_live_motif import (
            build_pending_live_motif_result,
        )
        from dsf_ai_service.substrate.auditory_recurrent_motif import (
            verified_receptor_experience_from_full_field_event,
        )

        def settle_without_q(task):
            with engine._auditory_terminal_pipeline_lock:
                transferred = (
                    engine._auditory_terminal_pipeline_capabilities.get(
                        task.task_id
                    )
                )
            if transferred is None:
                raise RuntimeError(
                    "auditory admission baseline lost transferred custody"
                )
            experience, experience_capability = (
                verified_receptor_experience_from_full_field_event(
                    task.full_field_event,
                    verified_capability=transferred[4],
                )
            )
            return (
                task.joint_settlement,
                build_pending_live_motif_result(
                    experience,
                    verified_capability=experience_capability,
                ),
            )

        engine._settle_auditory_q_process_task = settle_without_q

    def submit_terminal(**values):
        transport = values["transport"]
        with engine._auditory_transaction_lock:
            joint = engine._auditory_prediction_joint_by_transport.get(
                transport.receipt_sha256
            )
        if joint is None:
            raise RuntimeError(
                "auditory cadence task lacks joint settlement before admission"
            )
        admission = engine.submit_continuous_auditory_terminal(**values)
        if admission.state != "queued":
            raise RuntimeError(
                "auditory cadence terminal pipeline reached capacity"
            )
        return joint, admission

    engine.advance_continuous_auditory_terminal = submit_terminal
    app_module._guala = engine
    app_module._is_remote = lambda: False
    app_module._converse_inflight = 0
    app_module._converse_window_started_at = 0.0
    app_module._auditory_pcm_streams = AuditoryPCMStreamRegistry()
    opened = asyncio.run(app_module.auditory_pcm_stream_open())
    stream_id = opened["stream_id"]
    durations: list[float] = []
    backlog = 0.0
    maximum_backlog = 0.0
    records = []
    settled_by_sequence = {}
    acknowledged_sequence = -1
    try:
        source_clock_started = time.perf_counter()
        for sequence, chunk in enumerate(chunks):
            source_arrival = source_clock_started + sequence * 2.0
            until_arrival = source_arrival - time.perf_counter()
            if until_arrival > 0.0:
                time.sleep(until_arrival)
            started = time.perf_counter()
            response = _post(
                stream_id=stream_id,
                sequence=sequence,
                sample_count=PCM_CHUNK_SAMPLES,
                pcm=chunk,
            )
            elapsed = time.perf_counter() - started
            durations.append(elapsed)
            source_deadline = source_clock_started + (sequence + 1) * 2.0
            backlog = max(0.0, time.perf_counter() - source_deadline)
            maximum_backlog = max(maximum_backlog, backlog)
            records.append(response)
            settled = engine.poll_continuous_auditory_terminals(
                stream_id=stream_id,
                after_sequence=acknowledged_sequence,
            )
            if settled["failures"]:
                raise RuntimeError(
                    "auditory terminal pipeline failed: "
                    f"{settled['failures']}"
                )
            for value in settled["results"]:
                settled_by_sequence[value["sequence"]] = (
                    value["auditory_motif"]
                )
            if settled["results"]:
                acknowledged_sequence = max(
                    value["sequence"] for value in settled["results"]
                )
        engine.wait_for_auditory_terminal_pipeline()
        settled = engine.poll_continuous_auditory_terminals(
            stream_id=stream_id,
            after_sequence=acknowledged_sequence,
        )
        if settled["failures"]:
            raise RuntimeError(
                f"auditory terminal pipeline failed: {settled['failures']}"
            )
        for value in settled["results"]:
            settled_by_sequence[value["sequence"]] = (
                value["auditory_motif"]
            )
        if set(settled_by_sequence) != set(range(len(chunks))):
            raise RuntimeError(
                "auditory terminal pipeline lost a scheduled result"
            )
        for sequence, response in enumerate(records):
            response["auditory_motif"] = settled_by_sequence[sequence]
        engine.synchronize_auditory_q_process_state()
    finally:
        cleanup_errors = []
        engine.advance_continuous_auditory_terminal = (
            original_terminal_advance
        )
        engine._settle_auditory_q_process_task = original_q_settle
        peak_module._peak_atoms_from_experience = original_peak_extractor
        peak_module.compose_contiguous_receptor_experiences = original_compose
        peak_module.AuditoryRecurrentMotifOwner.fire = original_fire
        live_motif_module.build_live_motif_result = original_live_result
        peak_module.AuditoryRecurrentMotifOwner.observe = original_observe
        peak_module.AuditoryRecurrentMotifOwner.prepare = original_prepare
        peak_module.receptor_experience_from_full_field_event = (
            original_receptor_experience
        )
        peak_module._peak_state_encoded = original_state_encode
        q_process_module.AuditoryQProcessOwner.commit = (
            original_process_commit
        )
        q_process_module.AuditoryQProcessOwner.prepare = (
            original_process_prepare
        )
        try:
            engine.wait_for_auditory_terminal_pipeline()
        except BaseException as error:
            cleanup_errors.append(error)
        try:
            engine.poll_continuous_auditory_terminals(
                stream_id=stream_id,
                after_sequence=len(chunks) - 1,
            )
        except BaseException as error:
            cleanup_errors.append(error)
        try:
            engine.close_auditory_pcm_stream(
                stream_id,
                release_terminal=False,
            )
        except BaseException as error:
            cleanup_errors.append(error)
        try:
            app_module._auditory_pcm_streams.close(stream_id)
        except BaseException as error:
            cleanup_errors.append(error)
        try:
            engine.shutdown()
        except BaseException as error:
            cleanup_errors.append(error)
        try:
            stop_exact_field_executor()
        except BaseException as error:
            cleanup_errors.append(error)
        if cleanup_errors:
            raise BaseExceptionGroup(
                "auditory q cadence cleanup failed",
                cleanup_errors,
            )

    learning = records[HELLO_LEARNING_SETTLEMENT_SEQUENCE].get(
        "auditory_motif",
        {},
    )
    overlap = records[OVERLAP_FIRING_SETTLEMENT_SEQUENCE].get(
        "auditory_motif",
        {},
    )
    grown = set(learning.get("newly_grown_motif_neuron_ids", ()))
    overlap_firing = set(
        overlap.get("firing_motif_neuron_ids", ())
    )
    co_firing = tuple(sorted(grown.intersection(overlap_firing)))
    status = engine._auditory_recurrent_motif_owner.status()
    extraction_receipts = [
        value[0] for value in peak_extraction_records
    ]
    report = {
        "authenticated_schedule_pcm_sha256": schedule["pcm_sha256"],
        "backlog_at_end_seconds": backlog,
        "chunk_count": len(chunks),
        "hello_overlap_co_firing_count": len(co_firing),
        "hello_overlap_co_firing_sha256": hashlib.sha256(
            json.dumps(
                co_firing,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "maximum_backlog_seconds": maximum_backlog,
        "mode": (
            "full_q"
            if not admission_only
            else "admission_without_q_interpretation"
        ),
        "maximum_settlement_seconds": max(durations),
        "p50_settlement_seconds": statistics.median(durations),
        "overlap_firing_count": len(overlap_firing),
        "peak_extraction_call_count": len(peak_extraction_records),
        "peak_extraction_duplicate_call_count": (
            len(extraction_receipts) - len(set(extraction_receipts))
        ),
        "peak_extraction_total_seconds": sum(
            value[1] for value in peak_extraction_records
        ),
        "p95_settlement_seconds": _percentile_95(durations),
        "q_bank_state_allocation_bytes": (
            status["canonical_state_allocation_bytes"]
        ),
        "q_bank_state_remaining_bytes": (
            status["canonical_state_remaining_bytes"]
        ),
        "q_bank_state_used_bytes": status["canonical_state_used_bytes"],
        "q_motif_neuron_count": status["motif_neuron_count"],
        "q_pending_peak_cell_count": status["pending_peak_cell_count"],
        "q_operation_seconds": {
            name: {
                "calls": len(values),
                "maximum": max(values) if values else 0.0,
                "total": sum(values),
            }
            for name, values in q_operation_seconds.items()
        },
        "source_seconds_per_chunk": 2,
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
