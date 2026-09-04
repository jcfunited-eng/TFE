#!/usr/bin/env python3
"""Exercise Guala's current speech/self-hearing path on one exact copied body.

This probe is deliberately outside the serving process.  It restores the
supplied GLORUN bytes into one local native runtime, advances only dark/silent
whole-sensorium intervals through the same one-timeline functions production
uses, seals the successor once, cold-restores it, and reports exact receipts.
It also performs the required read-only AWS health check before touching the
copy.  It never writes production state or calls a production intake endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import struct
import sys
import time
from typing import Any
import wave


DEFAULT_IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
DEFAULT_REGION = "us-east-1"
DEFAULT_CLUSTER = "tfe-web-cluster"
DEFAULT_SERVICE = "dsf-ai-service-lb"
ALARM_NAMES = (
    "guala-clock-stalled",
    "guala-cpu-runaway",
    "guala-efs-storage-runaway",
    "guala-interval-refusal-loop",
    "guala-memory-runaway",
)


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _current_rss_bytes() -> int:
    resident_pages = int(Path("/proc/self/statm").read_text(encoding="ascii").split()[1])
    return resident_pages * int(os.sysconf("SC_PAGE_SIZE"))


def _aws_json(*arguments: str) -> Any:
    completed = subprocess.run(
        ("aws", *arguments, "--output", "json"),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return json.loads(completed.stdout)


def _aws_health(
    *,
    region: str,
    cluster: str,
    service: str,
    expected_task_definition: str,
) -> dict[str, Any]:
    services = _aws_json(
        "ecs",
        "describe-services",
        "--region",
        region,
        "--cluster",
        cluster,
        "--services",
        service,
    ).get("services", [])
    if len(services) != 1:
        raise RuntimeError("AWS health check did not resolve exactly one ECS service")
    observed = services[0]
    task_definition = str(observed.get("taskDefinition", ""))
    if expected_task_definition and not task_definition.endswith(
        f":{expected_task_definition}"
    ):
        raise RuntimeError(
            "AWS task definition changed: "
            f"expected revision {expected_task_definition}, observed {task_definition}"
        )
    task_arns = _aws_json(
        "ecs",
        "list-tasks",
        "--region",
        region,
        "--cluster",
        cluster,
        "--service-name",
        service,
        "--desired-status",
        "RUNNING",
    ).get("taskArns", [])
    tasks = (
        _aws_json(
            "ecs",
            "describe-tasks",
            "--region",
            region,
            "--cluster",
            cluster,
            "--tasks",
            *task_arns,
        ).get("tasks", [])
        if task_arns
        else []
    )
    alarms = _aws_json(
        "cloudwatch",
        "describe-alarms",
        "--region",
        region,
        "--alarm-names",
        *ALARM_NAMES,
    ).get("MetricAlarms", [])
    alarm_states = {
        str(alarm.get("AlarmName")): str(alarm.get("StateValue"))
        for alarm in alarms
    }
    bad_alarms = {
        name: state for name, state in alarm_states.items() if state != "OK"
    }
    running = int(observed.get("runningCount", -1))
    desired = int(observed.get("desiredCount", -1))
    pending = int(observed.get("pendingCount", -1))
    task_health = tuple(
        {
            "health_status": str(task.get("healthStatus", "UNKNOWN")),
            "last_status": str(task.get("lastStatus", "")),
            "task_arn": str(task.get("taskArn", "")),
            "task_definition_arn": str(task.get("taskDefinitionArn", "")),
        }
        for task in tasks
    )
    if (
        desired != 1
        or running != 1
        or pending != 0
        or len(task_health) != 1
        or task_health[0]["last_status"] != "RUNNING"
        or task_health[0]["health_status"] != "HEALTHY"
        or bad_alarms
    ):
        raise RuntimeError(
            "AWS health gate failed: "
            + json.dumps(
                {
                    "desired": desired,
                    "running": running,
                    "pending": pending,
                    "tasks": task_health,
                    "non_ok_alarms": bad_alarms,
                },
                sort_keys=True,
            )
        )
    return {
        "alarm_states": alarm_states,
        "desired_count": desired,
        "pending_count": pending,
        "running_count": running,
        "service": service,
        "task_definition_arn": task_definition,
        "tasks": task_health,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-tick", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--wav-output",
        type=Path,
        help=(
            "optional exact concatenation of each copied-body successor "
            "pressure interval; observation only, never fed back into the organism"
        ),
    )
    parser.add_argument("--identity", default=DEFAULT_IDENTITY)
    parser.add_argument("--hops", type=int, default=8)
    # A GLORUN envelope adds its fixed 57-byte header around GLMFAB11.
    parser.add_argument("--max-envelope-bytes", type=int, default=268_435_513)
    parser.add_argument("--max-fabric-bytes", type=int, default=268_435_456)
    parser.add_argument("--max-logical-peak-bytes", type=int, default=1_073_741_824)
    parser.add_argument("--aws-region", default=DEFAULT_REGION)
    parser.add_argument("--aws-cluster", default=DEFAULT_CLUSTER)
    parser.add_argument("--aws-service", default=DEFAULT_SERVICE)
    parser.add_argument("--expected-task-definition", default="1428")
    arguments = parser.parse_args()
    if arguments.hops < 2 or arguments.hops > 512:
        parser.error("--hops must be between 2 and 512")
    return arguments


def main() -> int:
    arguments = _parse_arguments()
    aws_health = _aws_health(
        region=arguments.aws_region,
        cluster=arguments.aws_cluster,
        service=arguments.aws_service,
        expected_task_definition=arguments.expected_task_definition,
    )

    # Match the immutable anatomy switches of task 1428 before importing the
    # production module, whose mounted roster is fixed at import time.
    os.environ.update(
        {
            "GUALA_CHEMORECEPTION": "1",
            "GUALA_COCHLEAR_EARS": "1",
            "GUALA_INTEROCEPTION": "1",
            "GUALA_NATIVE_ORGANISM_IDENTITY": arguments.identity,
            "GUALA_TOUCH_RECEPTORS": "1",
            "GUALA_VESTIBULAR": "1",
            "GUALA_WORLD": "1",
        }
    )

    from dsf_ai_service import native_production_app as production
    from dsf_ai_service.glew_runtime.native_resident_organism import (
        restore_native_resident_organism,
    )

    body = arguments.body.read_bytes()
    body_sha256 = _sha256(body)
    if body_sha256 != arguments.expected_sha256:
        raise RuntimeError(
            f"copied body changed: expected {arguments.expected_sha256}, "
            f"observed {body_sha256}"
        )
    budget = {
        "max_envelope_bytes": arguments.max_envelope_bytes,
        "max_fabric_bytes": arguments.max_fabric_bytes,
        "max_logical_peak_bytes": arguments.max_logical_peak_bytes,
    }

    def restored_copy() -> Any:
        organism = restore_native_resident_organism(
            current_envelope=body,
            **budget,
        )
        readiness = organism.readiness()
        if (
            readiness.identity != arguments.identity
            or readiness.organism_tick != arguments.expected_tick
            or readiness.state_sha256 != body_sha256
            or organism.save() != body
        ):
            raise RuntimeError("exact copied body failed cold-restore identity gate")
        return organism

    organism = restored_copy()
    initial = organism.readiness()
    initial_rss_bytes = _current_rss_bytes()
    # The serving helper reads these same persisted axes through its singleton
    # runtime.  This isolated probe has no singleton by construction, so bind
    # that read-only accessor to the exact copied predecessor instead.
    persisted_retinal_axes = tuple(initial.articulated_body_axes)
    production._current_retinal_body_axes = lambda: persisted_retinal_axes
    hop_receipts: list[dict[str, Any]] = []
    pressure_receipts: list[str] = []
    observed_pressure_intervals: list[bytes] = []
    started = time.perf_counter()
    for hop_index in range(arguments.hops):
        planned = production._mono_pcm_hop_episodes(
            assembly_prefix=f"speech-attempt44-exact-copy-{hop_index}",
            samples=(0,) * 4_000,
            sample_rate_hz=16_000,
        )
        if len(planned) != 1:
            raise RuntimeError("one 250-ms proof interval changed hop cardinality")
        plan, admissions = planned[0]
        prior_pressure = organism.in_flight_acoustic_pressure_s16le
        prior_pressure_sha256 = (
            _sha256(bytes(prior_pressure)) if prior_pressure is not None else None
        )
        before = organism.live_organism_tick
        hop, consumed = production._commit_one_timeline_hop(
            organism,
            plan,
            admissions,
            purpose="speech_attempt44_exact_copy",
        )
        after = organism.live_organism_tick
        successor_pressure = organism.in_flight_acoustic_pressure_s16le
        successor_mechanics = organism.in_flight_acoustic_body_s16le
        successor_pressure_body = (
            bytes(successor_pressure) if successor_pressure is not None else b""
        )
        successor_mechanics_body = (
            bytes(successor_mechanics) if successor_mechanics is not None else b""
        )
        mechanics_samples = (
            struct.unpack(
                f"<{len(successor_mechanics_body) // 2}h",
                successor_mechanics_body,
            )
            if successor_mechanics_body
            else ()
        )
        per_channel_samples = len(successor_pressure_body) // 2
        respiratory_flow = mechanics_samples[:per_channel_samples]
        pressure_samples = (
            struct.unpack(
                f"<{len(successor_pressure_body) // 2}h",
                successor_pressure_body,
            )
            if successor_pressure_body
            else ()
        )
        successor_pressure_sha256 = (
            _sha256(successor_pressure_body) if successor_pressure_body else None
        )
        after_body = organism.readiness()
        observed_axes = {
            name: position
            for (_ordinal, name, _unit, position, _minimum, _neutral, _maximum)
            in after_body.articulated_body_axes
            if name
            in {
                "glottal_aperture",
                "jaw_opening",
                "lip_aperture",
                "lip_width",
                "vocal_tract_section_0_area",
                "vocal_tract_section_7_area",
            }
        }
        if successor_pressure_sha256 is not None:
            pressure_receipts.append(successor_pressure_sha256)
        observed_pressure_intervals.append(
            successor_pressure_body
            if successor_pressure_body
            else b"\x00\x00" * 4_000
        )
        hop_receipts.append(
            {
                "articulated_body_lung_air_microlitres": (
                    after_body.articulated_body_lung_air_microlitres
                ),
                "articulated_body_selected_axes": observed_axes,
                "articulatory_recruitments": hop[
                    "articulatory_unit_recruitments"
                ],
                "articulatory_recruitment_count": len(
                    hop["articulatory_unit_recruitments"]
                ),
                "articulatory_applied_motor_quanta": hop.get(
                    "articulatory_applied_motor_quanta"
                ),
                "articulatory_stalled_motor_quanta": hop.get(
                    "articulatory_stalled_motor_quanta"
                ),
                "consumed_in_flight_pressure": consumed is not None,
                "consumed_pressure_sha256": (
                    consumed.get("pressure_sha256") if consumed else None
                ),
                "hop_index": hop_index,
                "motor_unit_recruitments": hop["motor_unit_recruitments"],
                "organism_tick_before": before,
                "organism_tick_after": after,
                "physically_transitioned_neuron_count": hop[
                    "physically_transitioned_neuron_count"
                ],
                "process_rss_bytes": _current_rss_bytes(),
                "prior_pressure_sha256": prior_pressure_sha256,
                "receptor_ingress_changing_count": hop[
                    "receptor_ingress_changing_count"
                ],
                "receptor_ingress_sound_count": hop[
                    "receptor_ingress_sense_counts"
                ]["sound"],
                "resident_cognitive_trace_count": after_body.cognitive_trace_count,
                "resident_formation_activation_count": (
                    after_body.formation_activation_count
                ),
                "resident_state_bytes": after_body.state_bytes,
                "successor_pressure_bytes": len(successor_pressure_body),
                "successor_pressure_nonzero_samples": sum(
                    successor_pressure_body[index : index + 2] != b"\x00\x00"
                    for index in range(0, len(successor_pressure_body), 2)
                ),
                "successor_pressure_peak": max(
                    (abs(sample) for sample in pressure_samples),
                    default=0,
                ),
                "successor_pressure_sha256": successor_pressure_sha256,
                "successor_respiratory_flow_peak": max(
                    (abs(sample) for sample in respiratory_flow),
                    default=0,
                ),
                "successor_respiratory_flow_signed_sum": sum(respiratory_flow),
                "successor_respiratory_inflow_sum": sum(
                    -sample for sample in respiratory_flow if sample < 0
                ),
                "successor_respiratory_outflow_sum": sum(
                    sample for sample in respiratory_flow if sample > 0
                ),
            }
        )
    elapsed_ms = (time.perf_counter() - started) * 1_000.0

    sealed = organism.seal_unsealed_trajectory_direct()
    successor = organism.save()
    successor_sha256 = _sha256(successor)
    if successor_sha256 != sealed.state_sha256:
        raise RuntimeError("sealed successor receipt did not bind exact bytes")
    organism.acknowledge_sealed_trajectory()
    cold = restore_native_resident_organism(
        current_envelope=successor,
        **budget,
    )
    cold_readiness = cold.readiness()
    hot_pressure = organism.in_flight_acoustic_pressure_s16le
    cold_pressure = cold.in_flight_acoustic_pressure_s16le
    hot_body = organism.in_flight_acoustic_body_s16le
    cold_body = cold.in_flight_acoustic_body_s16le
    cold_exact = (
        cold.save() == successor
        and cold_readiness.state_sha256 == successor_sha256
        and cold_readiness.identity == initial.identity
        and cold_readiness.organism_tick == sealed.organism_tick
        and cold_pressure == hot_pressure
        and cold_body == hot_body
    )
    if not cold_exact:
        raise RuntimeError("speech/self-hearing successor did not cold-restore exactly")
    if not any(item["articulatory_recruitment_count"] for item in hop_receipts):
        raise RuntimeError("copied-body range produced no respiratory recruitment")
    if not any(item["consumed_in_flight_pressure"] for item in hop_receipts[1:]):
        raise RuntimeError("copied-body range never consumed its own pressure")

    report = {
        "aws_health": aws_health,
        "cold_restore_exact": cold_exact,
        "elapsed_ms": elapsed_ms,
        "hops": hop_receipts,
        "input": {
            "bytes": len(body),
            "identity": initial.identity,
            "sha256": body_sha256,
            "tick": initial.organism_tick,
        },
        "pressure_receipt_count": len(pressure_receipts),
        "pressure_receipts": pressure_receipts,
        "resource_observation": {
            "initial_rss_bytes": initial_rss_bytes,
            "maximum_hop_rss_bytes": max(
                item["process_rss_bytes"] for item in hop_receipts
            ),
            "final_hop_rss_bytes": hop_receipts[-1]["process_rss_bytes"],
            "minimum_hop_rss_bytes": min(
                item["process_rss_bytes"] for item in hop_receipts
            ),
        },
        "schema": "guala.speech.attempt44.exact_copy_self_hearing_probe.v1",
        "successor": {
            "bytes": len(successor),
            "in_flight_pressure_bytes": len(bytes(hot_pressure or b"")),
            "sha256": successor_sha256,
            "tick": sealed.organism_tick,
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if arguments.wav_output is not None:
        arguments.wav_output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(arguments.wav_output), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16_000)
            wav_file.writeframes(b"".join(observed_pressure_intervals))
    print(json.dumps(report, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
