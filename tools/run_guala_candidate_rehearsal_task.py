#!/usr/bin/env python3
"""Run one bounded migration, publication, or native CURRENT proof task."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time


PROBE_FAMILY = "dsf-ai-native-candidate"
SOURCE_MOUNT = "/source/guala"
NATIVE_STORE = SOURCE_MOUNT + "/native-organism"
EPHEMERAL_GIB = 30
_SHA = re.compile(r"[0-9a-f]{64}")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("rehearse", "publish", "cold-restore"),
        required=True,
    )
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--candidate-task-definition", required=True)
    parser.add_argument("--candidate-git-sha", required=True)
    parser.add_argument("--candidate-image-digest", required=True)
    parser.add_argument("--expected-baseline-generation")
    parser.add_argument("--expected-active-generation")
    parser.add_argument("--expected-identity", required=True)
    parser.add_argument("--expected-tick", required=True, type=int)
    parser.add_argument("--expected-state-sha256")
    parser.add_argument("--region", default="us-east-1")
    return parser.parse_args()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def probe_task_definition(
    source: dict[str, object],
    *,
    mode: str,
    candidate_git_sha: str,
    candidate_image_digest: str,
    expected_identity: str,
    expected_tick: int,
    expected_baseline_generation: str | None = None,
    expected_active_generation: str | None = None,
    expected_state_sha256: str | None = None,
) -> dict[str, object]:
    containers = source.get("containerDefinitions")
    if not isinstance(containers, list) or len(containers) != 1:
        raise RuntimeError("candidate task must contain one container")
    original = containers[0]
    if not isinstance(original, dict) or original.get("name") != "dsf-ai":
        raise RuntimeError("candidate container changed")
    environment = [
        item
        for item in original.get("environment", [])
        if isinstance(item, dict)
        and item.get("name")
        not in {
            "FORCE_S3_RESTORE",
            "GUALA_EXACT_FIELD_EXECUTOR_REQUIRED",
            "GUALA_GENERATION_STORE_ROOT",
            "GUALA_LIVE_RECOVERY_STORE_ROOT",
            "GUALA_OWNER_LOCK_PATH",
            "GUALA_REQUIRE_SEALED_STATE",
            "STATE_DIR",
        }
    ]
    if mode == "cold-restore":
        if expected_state_sha256 is None:
            raise ValueError("cold restore requires expected state SHA-256")
        command = [
            "python3",
            "-m",
            "dsf_ai_service.cold_restore_probe",
            "--native-store-root",
            NATIVE_STORE,
            "--expected-identity",
            expected_identity,
            "--expected-tick",
            str(expected_tick),
            "--expected-state-sha256",
            expected_state_sha256,
            "--candidate-git-sha",
            candidate_git_sha,
            "--candidate-image-digest",
            candidate_image_digest,
        ]
    else:
        if expected_baseline_generation is None or expected_active_generation is None:
            raise ValueError("migration task requires exact generation identities")
        command = [
            "python3",
            "-m",
            "dsf_ai_service.candidate_release_rehearsal",
            "--mode",
            mode,
            "--source-root",
            SOURCE_MOUNT,
            "--expected-baseline-generation",
            expected_baseline_generation,
            "--expected-active-generation",
            expected_active_generation,
            "--expected-identity",
            expected_identity,
            "--expected-tick",
            str(expected_tick),
            "--candidate-git-sha",
            candidate_git_sha,
            "--candidate-image-digest",
            candidate_image_digest,
        ]
        if mode == "publish":
            command.extend(("--native-store-root", NATIVE_STORE))
    log_configuration = original.get("logConfiguration")
    if not isinstance(log_configuration, dict):
        raise RuntimeError("candidate log transport is absent")
    options = dict(log_configuration.get("options") or {})
    options["awslogs-stream-prefix"] = "guala-native-" + mode
    read_only = mode in {"rehearse", "cold-restore"}
    container = {
        "command": command,
        "environment": environment,
        "essential": True,
        "image": original.get("image"),
        "logConfiguration": {**log_configuration, "options": options},
        "mountPoints": [{
            "containerPath": SOURCE_MOUNT,
            "readOnly": read_only,
            "sourceVolume": "gualaloom-state",
        }],
        "name": "dsf-ai",
        "secrets": original.get("secrets", []),
        "stopTimeout": 120,
    }
    keep = (
        "cpu",
        "executionRoleArn",
        "memory",
        "networkMode",
        "requiresCompatibilities",
        "runtimePlatform",
        "taskRoleArn",
        "volumes",
    )
    task = {name: source[name] for name in keep if name in source}
    task.update({
        "containerDefinitions": [container],
        "ephemeralStorage": {"sizeInGiB": EPHEMERAL_GIB},
        "family": PROBE_FAMILY + "-" + mode,
    })
    return task


def _validate_proof(
    proof: object,
    *,
    mode: str,
    candidate_git_sha: str,
    candidate_image_digest: str,
    expected_identity: str,
    expected_tick: int,
    expected_state_sha256: str | None,
) -> dict[str, object]:
    schemas = {
        "rehearse": "guala.production_candidate_native_restore_rehearsal.v5",
        "publish": "guala.production_native_current_publication.v1",
        "cold-restore": "guala.production_native_current_cold_restore.v1",
    }
    if not isinstance(proof, dict):
        raise RuntimeError("native candidate proof is not an object")
    receipt = proof.get("receipt_sha256")
    record = dict(proof)
    record.pop("receipt_sha256", None)
    if (
        proof.get("schema") != schemas[mode]
        or proof.get("mode") != mode
        or proof.get("candidate_git_sha") != candidate_git_sha
        or proof.get("candidate_image_digest") != candidate_image_digest
        or proof.get("source_identity") != expected_identity
        or proof.get("tick") != expected_tick
        or proof.get("cold_restore_exact") is not True
        or proof.get("raw_glorun_current_only") is not True
        or proof.get("python_callback_count") != 0
        or proof.get("python_cognition_workers_started") != 0
        or not isinstance(proof.get("resident_state_bytes"), int)
        or isinstance(proof.get("resident_state_bytes"), bool)
        or proof["resident_state_bytes"] <= 0
        or not isinstance(proof.get("resident_state_sha256"), str)
        or _SHA.fullmatch(proof["resident_state_sha256"]) is None
        or (
            expected_state_sha256 is not None
            and proof["resident_state_sha256"] != expected_state_sha256
        )
        or receipt != hashlib.sha256(_canonical(record)).hexdigest()
    ):
        raise RuntimeError("native candidate proof changed")
    return proof


def _proof_from_logs(logs, *, group: str, stream: str) -> object:
    token = None
    messages: list[str] = []
    while True:
        values = {
            "logGroupName": group,
            "logStreamName": stream,
            "startFromHead": True,
        }
        if token is not None:
            values["nextToken"] = token
        page = logs.get_log_events(**values)
        messages.extend(
            event.get("message", "")
            for event in page.get("events", [])
            if isinstance(event, dict)
        )
        next_token = page.get("nextForwardToken")
        if next_token == token:
            break
        token = next_token
    proofs = []
    for message in messages:
        try:
            value = json.loads(message)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and str(value.get("schema", "")).startswith(
            "guala.production_"
        ):
            proofs.append(value)
    if len(proofs) != 1:
        raise RuntimeError("candidate task did not emit one exact proof")
    return proofs[0]


def main() -> int:
    values = _arguments()
    if values.mode in {"rehearse", "publish"} and (
        not values.expected_baseline_generation
        or not values.expected_active_generation
    ):
        raise ValueError("migration task requires exact generation identities")
    if values.mode == "cold-restore" and not values.expected_state_sha256:
        raise ValueError("cold restore requires expected state SHA-256")
    import boto3

    ecs = boto3.client("ecs", region_name=values.region)
    logs = boto3.client("logs", region_name=values.region)
    source = ecs.describe_task_definition(
        taskDefinition=values.candidate_task_definition
    )["taskDefinition"]
    task_input = probe_task_definition(
        source,
        mode=values.mode,
        candidate_git_sha=values.candidate_git_sha,
        candidate_image_digest=values.candidate_image_digest,
        expected_baseline_generation=values.expected_baseline_generation,
        expected_active_generation=values.expected_active_generation,
        expected_identity=values.expected_identity,
        expected_tick=values.expected_tick,
        expected_state_sha256=values.expected_state_sha256,
    )
    registered = ecs.register_task_definition(**task_input)["taskDefinition"]
    task_definition_arn = registered["taskDefinitionArn"]
    task_arn = None
    try:
        service = ecs.describe_services(
            cluster=values.cluster,
            services=[values.service],
        )["services"][0]
        response = ecs.run_task(
            cluster=values.cluster,
            taskDefinition=task_definition_arn,
            launchType="FARGATE",
            networkConfiguration=service["networkConfiguration"],
            count=1,
        )
        if response.get("failures") or len(response.get("tasks", [])) != 1:
            raise RuntimeError("native candidate task failed admission")
        task_arn = response["tasks"][0]["taskArn"]
        ecs.get_waiter("tasks_stopped").wait(
            cluster=values.cluster,
            tasks=[task_arn],
            WaiterConfig={"Delay": 5, "MaxAttempts": 180},
        )
        task = ecs.describe_tasks(
            cluster=values.cluster,
            tasks=[task_arn],
        )["tasks"][0]
        containers = task.get("containers", [])
        if (
            len(containers) != 1
            or containers[0].get("exitCode") != 0
            or not containers[0].get("logStreamName")
        ):
            raise RuntimeError(
                "native candidate task failed: "
                + json.dumps(task.get("stoppedReason"), sort_keys=True)
            )
        group = task_input["containerDefinitions"][0]["logConfiguration"][
            "options"
        ]["awslogs-group"]
        for _attempt in range(30):
            try:
                proof = _proof_from_logs(
                    logs,
                    group=group,
                    stream=containers[0]["logStreamName"],
                )
                break
            except RuntimeError:
                time.sleep(2)
        else:
            raise RuntimeError("native candidate proof was not delivered to logs")
        validated = _validate_proof(
            proof,
            mode=values.mode,
            candidate_git_sha=values.candidate_git_sha,
            candidate_image_digest=values.candidate_image_digest,
            expected_identity=values.expected_identity,
            expected_tick=values.expected_tick,
            expected_state_sha256=values.expected_state_sha256,
        )
        print(_canonical(validated).decode("ascii"))
        return 0
    finally:
        if task_arn is not None:
            try:
                ecs.stop_task(
                    cluster=values.cluster,
                    task=task_arn,
                    reason="native candidate task complete",
                )
            except Exception:
                pass
        ecs.deregister_task_definition(taskDefinition=task_definition_arn)


if __name__ == "__main__":
    raise SystemExit(main())
