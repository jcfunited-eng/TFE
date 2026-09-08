"""Exact five-route Candidate 55 proof against one copied paired organism."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from fastapi.testclient import TestClient

from dsf_ai_service.lean_production_app import (
    OBSERVATION_ROUTE,
    OCCURRENCE_ROUTE,
    PRESSURE_ROUTE,
    create_lean_production_app,
)
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import (
    derive_native_resident_resource_admission,
)


TARGET_AXES = (37, 38, 39, 44)
GUIDE_CARRIERS = 1_500
RECOVERY_INTERVALS = 32
SEQUENCE_DIRECTIONS = (0, 1, 0, 1) * 8
CONTINUATION_INTERVALS = 256
EXPECTED_IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def _bytes(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label} is not a regular file")
    return path.read_bytes()


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _emit(stage: str, **evidence: object) -> None:
    print(json.dumps({"stage": stage, **evidence}, sort_keys=True), flush=True)


def _initialize_store(
    root: Path,
    *,
    body: bytes,
    world: bytes,
    identity: str,
    tick: int,
) -> PairedCurrentStore:
    if root.exists():
        raise RuntimeError(f"probe root already exists: {root}")
    admission = derive_native_resident_resource_admission(root)
    store = PairedCurrentStore(
        root,
        max_body_bytes=admission.max_envelope_bytes,
        max_world_bytes=16_777_216,
    )
    pointer = store.publish(
        identity=identity,
        organism_tick=tick,
        body=body,
        world=world,
        expected_current_body_sha256=None,
    )
    if pointer.current.body_sha256 != _sha256(body):
        raise RuntimeError("initialized body receipt changed")
    if pointer.current.world_sha256 != _sha256(world):
        raise RuntimeError("initialized world receipt changed")
    return store


def _await_ready(client: TestClient) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        response = client.get("/ready")
        if response.status_code == 200 and response.json() == {"ready": True}:
            return
        if response.status_code != 503:
            raise RuntimeError(
                f"production readiness changed {response.status_code}: {response.text}"
            )
        time.sleep(0.01)
    raise RuntimeError("production wrapper did not regain durable readiness")


def _post(client: TestClient, body: dict[str, object]) -> dict[str, Any]:
    _await_ready(client)
    response = client.post(OCCURRENCE_ROUTE, json=body)
    if response.status_code != 200:
        raise RuntimeError(
            f"production occurrence refused {response.status_code}: {response.text}"
        )
    record = response.json()
    if record.get("schema") != "guala.lean_occurrence_result.v1":
        raise RuntimeError("production occurrence schema changed")
    return record


def _unattended(client: TestClient) -> dict[str, Any]:
    return _post(client, {"kind": "unattended", "payload": None})


def _guided(
    client: TestClient,
    *,
    pressure: bytes,
    direction: int,
) -> dict[str, Any]:
    return _post(
        client,
        {
            "kind": "sensory",
            "payload": {
                "source": "guided-vocal-microphone",
                "pcm_s16le_base64": base64.b64encode(pressure).decode("ascii"),
                "guided_vocal_drives": [
                    {
                        "axis_ordinal": axis,
                        "direction_ordinal": direction,
                        "outward_elementary_carriers": GUIDE_CARRIERS,
                    }
                    for axis in TARGET_AXES
                ],
            },
        },
    )


def _last(record: dict[str, Any]) -> dict[str, Any]:
    observation = record.get("observation")
    if not isinstance(observation, dict):
        raise RuntimeError("actor observation is absent")
    last = observation.get("last_occurrence")
    if not isinstance(last, dict):
        raise RuntimeError("last physical occurrence is absent")
    return last


def _held_pressure(client: TestClient, receipt: str) -> bytes:
    response = client.get(PRESSURE_ROUTE.format(receipt=receipt))
    if response.status_code != 200:
        raise RuntimeError("held pressure route refused its exact receipt")
    body = bytes(response.content)
    if _sha256(body) != receipt:
        raise RuntimeError("held pressure differs from its receipt")
    return body


def _pressure_measurement(body: bytes) -> dict[str, int]:
    samples = [
        int.from_bytes(body[offset : offset + 2], "little", signed=True)
        for offset in range(0, len(body), 2)
    ]
    return {
        "bytes": len(body),
        "nonzero_samples": sum(sample != 0 for sample in samples),
        "peak": max((abs(sample) for sample in samples), default=0),
    }


def _drain_pending_self_pressure(
    client: TestClient,
    record: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, object]]]:
    drains: list[dict[str, object]] = []
    while bool(_last(record).get("self_pressure_pending")):
        if len(drains) >= CONTINUATION_INTERVALS:
            raise RuntimeError("body-owned pressure did not clear within its bound")
        record = _unattended(client)
        last = _last(record)
        if int(last.get("self_heard_sample_count", 0)) <= 0:
            raise RuntimeError("pending body-owned pressure was not self-heard")
        drains.append({
            "tick": last["native_tick"],
            "sample_count": last["self_heard_sample_count"],
            "source_tick": last["self_hearing_source_tick"],
            "new_pressure_sha256": record.get("pressure_sha256"),
        })
    return record, drains


def _train(root: Path, tutor_pressure: bytes) -> dict[str, object]:
    app = create_lean_production_app()
    guided_records: list[dict[str, object]] = []
    self_pressure_drains: list[dict[str, object]] = []
    with TestClient(app) as client:
        initial = client.get(OBSERVATION_ROUTE).json()
        if initial.get("identity") != EXPECTED_IDENTITY:
            raise RuntimeError("production wrapper restored the wrong identity")

        first = _guided(client, pressure=tutor_pressure, direction=0)
        first_last = _last(first)
        if first_last.get("external_guided_vocal_axis_count") != len(TARGET_AXES):
            raise RuntimeError("first guide did not reach all target axes")
        if first_last.get("external_heard_sample_count") != 4_000:
            raise RuntimeError("first guide did not co-admit tutor pressure")
        guided_records.append({
            "direction": 0,
            "tick": first_last["native_tick"],
            "body_consequence_count": first_last["body_consequence_count"],
            "dsf_delivery_count": first_last["dsf_delivery_count"],
            "changed_neurons": first_last["physically_transitioned_neuron_count"],
            "pressure_sha256": first["pressure_sha256"],
        })
        _emit("first-guided-occurrence-passed", **guided_records[-1])

        recovery = first
        for _ in range(RECOVERY_INTERVALS):
            recovery = _unattended(client)
        _recovery, drains = _drain_pending_self_pressure(client, recovery)
        self_pressure_drains.extend(drains)
        if drains:
            _emit("recovery-self-pressure-heard", drains=drains)

        second = _guided(client, pressure=tutor_pressure, direction=1)
        second_last = _last(second)
        guided_records.append({
            "direction": 1,
            "tick": second_last["native_tick"],
            "body_consequence_count": second_last["body_consequence_count"],
            "dsf_delivery_count": second_last["dsf_delivery_count"],
            "changed_neurons": second_last["physically_transitioned_neuron_count"],
            "pressure_sha256": second["pressure_sha256"],
        })
        _emit("opposed-guided-population-passed", **guided_records[-1])
        _settled, drains = _drain_pending_self_pressure(client, second)
        self_pressure_drains.extend(drains)

        for direction in SEQUENCE_DIRECTIONS:
            record = _guided(
                client,
                pressure=tutor_pressure,
                direction=direction,
            )
            last = _last(record)
            guided_records.append({
                "direction": direction,
                "tick": last["native_tick"],
                "body_consequence_count": last["body_consequence_count"],
                "dsf_delivery_count": last["dsf_delivery_count"],
                "changed_neurons": last["physically_transitioned_neuron_count"],
                "pressure_sha256": record["pressure_sha256"],
            })
            _settled, drains = _drain_pending_self_pressure(client, record)
            self_pressure_drains.extend(drains)
        _emit(
            "bounded-sequence-training-passed",
            guided_occurrences=len(guided_records),
            sequence_steps=len(SEQUENCE_DIRECTIONS),
            final_tick=guided_records[-1]["tick"],
        )

    admission = derive_native_resident_resource_admission(root)
    store = PairedCurrentStore(
        root,
        max_body_bytes=admission.max_envelope_bytes,
        max_world_bytes=16_777_216,
    )
    trained = store.restore()
    return {
        "body_sha256": trained.pointer.current.body_sha256,
        "body_bytes": trained.pointer.current.body_bytes,
        "world_sha256": trained.pointer.current.world_sha256,
        "world_bytes": trained.pointer.current.world_bytes,
        "tick": trained.pointer.current.organism_tick,
        "guided_records": guided_records,
        "self_pressure_drains": self_pressure_drains,
    }


def _continue_after_cold(root: Path) -> dict[str, object]:
    zero_pressure = bytes(8_000)
    app = create_lean_production_app()
    pulses: list[dict[str, object]] = []
    pressures: list[dict[str, object]] = []
    self_hearing: list[dict[str, object]] = []
    with TestClient(app) as client:
        cold = client.get(OBSERVATION_ROUTE).json()
        cue = _guided(client, pressure=zero_pressure, direction=0)
        cue_last = _last(cue)
        if cue_last.get("external_guided_vocal_axis_count") != len(TARGET_AXES):
            raise RuntimeError("cold partial cue lost guided body work")
        if cue_last.get("external_heard_sample_count") != 4_000:
            raise RuntimeError("cold partial cue lost its exact zero-pressure source")
        for clock in range(1, CONTINUATION_INTERVALS + 1):
            record = _unattended(client)
            last = _last(record)
            if int(last.get("body_consequence_count", 0)) > 0:
                pulses.append({
                    "clock": clock,
                    "tick": last["native_tick"],
                    "body_consequence_count": last["body_consequence_count"],
                    "requested_world_action": last["requested_world_action"],
                })
            if int(last.get("self_heard_sample_count", 0)) > 0:
                self_hearing.append({
                    "clock": clock,
                    "tick": last["native_tick"],
                    "sample_count": last["self_heard_sample_count"],
                    "source_tick": last["self_hearing_source_tick"],
                    "dsf_delivery_count": last["dsf_delivery_count"],
                    "changed_neurons": last["physically_transitioned_neuron_count"],
                })
            receipt = record.get("pressure_sha256")
            if isinstance(receipt, str):
                body = _held_pressure(client, receipt)
                measurement = _pressure_measurement(body)
                if measurement["nonzero_samples"]:
                    pressures.append({
                        "clock": clock,
                        "tick": last["native_tick"],
                        "sha256": receipt,
                        **measurement,
                    })
            if pressures and self_hearing:
                break
        final = client.get(OBSERVATION_ROUTE).json()
    return {
        "cold_identity": cold["identity"],
        "cold_live_tick": cold["live_tick"],
        "cold_persisted_tick": cold["persisted_tick"],
        "cue": {
            "tick": cue_last["native_tick"],
            "external_guided_vocal_axis_count": cue_last[
                "external_guided_vocal_axis_count"
            ],
            "external_heard_sample_count": cue_last[
                "external_heard_sample_count"
            ],
        },
        "pulses": pulses,
        "pressures": pressures,
        "self_hearing": self_hearing,
        "final_tick": final["live_tick"],
        "success": bool(pulses and pressures and self_hearing),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--world", type=Path, required=True)
    parser.add_argument("--pointer", type=Path, required=True)
    parser.add_argument("--tutor-pressure", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pointer = json.loads(_bytes(args.pointer, "pointer").decode("utf-8"))
    current = pointer.get("current")
    if not isinstance(current, dict):
        raise RuntimeError("copied pointer lacks its current descriptor")
    body = _bytes(args.body, "copied body")
    world = _bytes(args.world, "copied world")
    tutor_pressure = _bytes(args.tutor_pressure, "tutor pressure")
    if current.get("identity") != EXPECTED_IDENTITY:
        raise RuntimeError("copied pointer identity changed")
    if current.get("body_sha256") != _sha256(body):
        raise RuntimeError("copied body differs from CURRENT")
    if current.get("world_sha256") != _sha256(world):
        raise RuntimeError("copied world differs from CURRENT")
    if len(tutor_pressure) != 8_000 or _sha256(tutor_pressure) != (
        "00c6ec35000e84c01ceb41f5349559156ea70ed398614a1c4a14328e3afb166c"
    ):
        raise RuntimeError("tutor pressure differs from the frozen input")
    if args.output.exists() or args.output.is_symlink():
        raise RuntimeError("proof output already exists")

    _initialize_store(
        args.root,
        body=body,
        world=world,
        identity=current["identity"],
        tick=current["organism_tick"],
    )
    os.environ["GUALA_PAIRED_ROOT"] = str(args.root)
    os.environ["GUALA_MAX_WORLD_BYTES"] = "16777216"
    _emit(
        "copied-pair-initialized",
        identity=current["identity"],
        tick=current["organism_tick"],
        body_sha256=current["body_sha256"],
        world_sha256=current["world_sha256"],
    )

    trained = _train(args.root, tutor_pressure)
    _emit("cold-restore-starting", trained_tick=trained["tick"])
    continuation = _continue_after_cold(args.root)
    proof = {
        "schema": "guala.candidate55.production_wrapper_proof.v1",
        "source": current,
        "trained": trained,
        "continuation": continuation,
    }
    args.output.write_bytes(_canonical_json(proof))
    _emit(
        "proof-complete",
        success=continuation["success"],
        proof_path=str(args.output),
        proof_sha256=_sha256(args.output.read_bytes()),
    )
    if not continuation["success"]:
        raise RuntimeError("cold learned cue did not close the speech chain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
