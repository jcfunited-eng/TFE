#!/usr/bin/env python3
"""Stage P6 Production Cutover & Delivery Script for Guala Bio-Functional Architecture.

Adheres strictly to §12 of docs/GUALA_BIOFUNCTIONAL_PLANNING_IMPLEMENTATION_PLAN_2026-09-27.md
and the proven single-writer cutover sequence:
1. Preflight truth verification (live task, image, observation, 44/44 native tests).
2. Build and push immutable container image to Amazon ECR with qualified native guala_core wheel and updated dsf_ai_service.
3. Register new ECS task definition (dsf-ai-task:1563).
4. Drain live service to zero writers and wait for predecessor to STOP cleanly with exitCode 0.
5. Execute one-off durable backup task to freeze immutable state checkpoint on EFS.
6. Deploy successor task definition, converge at count 0, then start exactly 1 instance.
7. Verify live health, image digest, single-writer invariant, and continuous tick advancement past predecessor.
"""

from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import boto3
from botocore.config import Config

REGION = "us-east-1"
ACCOUNT = "418384447921"
CLUSTER = "tfe-web-cluster"
SERVICE = "dsf-ai-service-lb"
OLD_DEFINITION = "arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:1562"
BASE = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/dsf-ai@sha256:d5ef18f5dd59ef41b654542895abdf989378cc25a1cfb107e465eca0948cb968"
REPOSITORY = BASE.split("@")[0]
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
ROOT = Path(__file__).resolve().parents[1]
WHEEL_NAME = "guala_core-0.1.0-cp311-cp311-manylinux_2_35_x86_64.whl"
WHEEL_PATH = ROOT / "native/guala_core/target/wheels" / WHEEL_NAME

CONFIG = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 2})
ecs = boto3.client("ecs", region_name=REGION, config=CONFIG)
ecr = boto3.client("ecr", region_name=REGION, config=CONFIG)
logs = boto3.client("logs", region_name=REGION, config=CONFIG)
journal = None


def emit(event: str, **data: object) -> None:
    record = {"at": datetime.now(timezone.utc).isoformat(), "event": event, **data}
    line = json.dumps(record, default=str)
    print(line, flush=True)
    if journal:
        with journal.open("a") as output:
            output.write(line + "\n")
            output.flush()
            os.fsync(output.fileno())


def service() -> dict:
    response = ecs.describe_services(cluster=CLUSTER, services=[SERVICE])
    assert not response.get("failures"), response.get("failures")
    return response["services"][0]


def task(arn: str) -> dict:
    response = ecs.describe_tasks(cluster=CLUSTER, tasks=[arn])
    assert not response.get("failures"), response.get("failures")
    return response["tasks"][0]


def observation() -> dict:
    url = "https://dsf-ai.com/api/v1/guala/observation"
    req = urllib.request.Request(url, headers={"User-Agent": "Biofunctional-Deployer/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read(8_000_001)
    assert len(data) <= 8_000_000
    value = json.loads(data)
    assert value["identity"] == IDENTITY
    return {
        key: value.get(key)
        for key in (
            "identity",
            "live_tick",
            "persisted_tick",
            "available",
            "checkpoint_error",
            "cleanup_error",
            "durability_blocked",
        )
    }


def wait_stopped(arn: str) -> dict:
    waiter = ecs.get_waiter("tasks_stopped")
    waiter.wait(cluster=CLUSTER, tasks=[arn], WaiterConfig={"Delay": 2, "MaxAttempts": 150})
    return task(arn)


def log_messages(arn: str, start_time_ms: int | None = None) -> list[str]:
    task_id = arn.split("/")[-1]
    params = {
        "logGroupName": "/ecs/dsf-ai",
        "logStreamName": "dsf-ai/dsf-ai/" + task_id,
        "startFromHead": True,
    }
    if start_time_ms is not None:
        params["startTime"] = start_time_ms
    messages = []
    token = None
    for _ in range(60):
        if token:
            params["nextToken"] = token
        batch = logs.get_log_events(**params)
        for event in batch["events"]:
            messages.append(event["message"])
        next_token = batch.get("nextForwardToken")
        if next_token == token:
            break
        token = next_token
    else:
        raise RuntimeError("log pagination exceeded its bounded completeness check")
    return messages


def zero_writers(known_arns: list[str]) -> None:
    for arn in known_arns:
        if task(arn)["lastStatus"] != "STOPPED":
            raise RuntimeError("known writer has not stopped: " + arn)
    if tuple(service()[k] for k in ("desiredCount", "runningCount", "pendingCount")) != (0, 0, 0):
        raise RuntimeError("service has not reached zero writers")
    for status in ("RUNNING", "PENDING"):
        arns = ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE, desiredStatus=status)["taskArns"]
        for arn in arns:
            if arn not in known_arns:
                raise RuntimeError("unexpected active task in service: " + arn)
    arns = ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE, desiredStatus="RUNNING")["taskArns"]
    assert not arns, "zero writers invariant violated: tasks still running: " + str(arns)


def oneoff(definition: str, network: dict, mode: str, command: list[str] | None = None) -> list[str]:
    response = ecs.run_task(
        cluster=CLUSTER,
        taskDefinition=definition,
        launchType="FARGATE",
        count=1,
        networkConfiguration=network,
        overrides={
            "containerOverrides": [
                {
                    "name": "dsf-ai",
                    "command": (
                        command
                        or ["python3", "/opt/a1_oscillation_operator.py", mode]
                    ),
                }
            ]
        },
    )
    assert not response.get("failures"), response.get("failures")
    arn = response["tasks"][0]["taskArn"]
    emit("operator_started", mode=mode, task=arn)
    final = wait_stopped(arn)
    container = next(c for c in final["containers"] if c["name"] == "dsf-ai")
    messages = log_messages(arn)
    emit(
        "operator_finished",
        mode=mode,
        task=arn,
        exit=container.get("exitCode"),
        logs=messages,
        reason=final.get("stoppedReason"),
    )
    assert container.get("exitCode") == 0, f"Operator {mode} failed with exit code {container.get('exitCode')}"
    return messages


def records(messages: list[str], schema: str) -> list[dict]:
    found = []
    for line in messages:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema") == schema:
            found.append(value)
    return found


def activate(definition: str, backup: dict, source_arn: str | None, candidate_arns: set[str], digest: str) -> None:
    zero_writers([source_arn] if source_arn else [])
    ecs.update_service(cluster=CLUSTER, service=SERVICE, taskDefinition=definition, desiredCount=0)
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        s = service()
        deployments = s["deployments"]
        if (
            s["taskDefinition"] == definition
            and (s["desiredCount"], s["runningCount"], s["pendingCount"]) == (0, 0, 0)
            and len(deployments) == 1
        ):
            d = deployments[0]
            if (
                d["status"] == "PRIMARY"
                and d["taskDefinition"] == definition
                and d.get("rolloutState") == "COMPLETED"
                and (d["desiredCount"], d["runningCount"], d["pendingCount"]) == (0, 0, 0)
            ):
                break
        emit("waiting_zero_definition_convergence", definition=definition)
        time.sleep(10)
    else:
        raise RuntimeError("zero-count candidate deployment did not converge")

    zero_writers([source_arn] if source_arn else [])
    ecs.update_service(cluster=CLUSTER, service=SERVICE, desiredCount=1)
    emit("candidate_start_requested", definition=definition, backup=backup)
    deadline = time.monotonic() + 600
    live = None
    while time.monotonic() < deadline:
        listed = ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE, desiredStatus="RUNNING")["taskArns"]
        candidate_arns.update(listed)
        for arn in listed:
            value = task(arn)
            assert value["taskDefinitionArn"] == definition
            if value["lastStatus"] == "RUNNING" and value.get("healthStatus") == "HEALTHY":
                live = value
        if live is not None:
            break
        emit("waiting_candidate", tasks=listed)
        time.sleep(10)
    assert live is not None, "candidate failed to become healthy"
    assert len(ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE, desiredStatus="RUNNING")["taskArns"]) == 1
    assert next(c for c in live["containers"] if c["name"] == "dsf-ai")["imageDigest"] == digest

    receipts = records(log_messages(live["taskArn"]), "guala.paired_predecessor.v1")
    assert len(receipts) == 1, f"Expected 1 paired_predecessor receipt, found {len(receipts)}"
    for key in ("identity", "organism_tick", "body_sha256", "body_bytes", "world_sha256", "world_bytes"):
        assert receipts[0][key] == backup["current"][key], f"Mismatch on {key}: receipt={receipts[0][key]} != backup={backup['current'][key]}"
    assert receipts[0]["functional_conversion"] is False

    first = observation()
    assert first["available"] and not first["checkpoint_error"] and not first["cleanup_error"]
    assert first["live_tick"] >= backup["current"]["organism_tick"]

    deadline = time.monotonic() + 90
    second = None
    while time.monotonic() < deadline:
        time.sleep(3)
        obs = observation()
        if (
            obs["available"]
            and obs["live_tick"] > first["live_tick"]
            and obs["persisted_tick"] > backup["current"]["organism_tick"]
            and not obs["checkpoint_error"]
            and not obs["cleanup_error"]
            and not obs["durability_blocked"]
        ):
            second = obs
            break
    assert second is not None, f"persisted_tick did not advance past {backup['current']['organism_tick']} within 90s"

    final_service = service()
    assert final_service["taskDefinition"] == definition
    assert (final_service["desiredCount"], final_service["runningCount"], final_service["pendingCount"]) == (1, 1, 0)
    final_task = task(live["taskArn"])
    assert final_task["lastStatus"] == "RUNNING" and final_task.get("healthStatus") == "HEALTHY"
    assert ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE, desiredStatus="RUNNING")["taskArns"] == [live["taskArn"]]
    emit(
        "live_restore_and_progress_verified",
        task=live["taskArn"],
        definition=definition,
        digest=digest,
        first=first,
        second=second,
    )


def main() -> None:
    global journal
    parser = argparse.ArgumentParser(description="Deploy bio-functional release candidate.")
    parser.add_argument("--execute", action="store_true", help="Execute live cutover on AWS.")
    args = parser.parse_args()

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    emit("preflight_check", commit=commit)

    # 1. Native test suite check
    print("Running 44 native tests in native/guala_core...")
    test_out = subprocess.check_output(
        ["cargo", "test", "--manifest-path", "native/guala_core/Cargo.toml"],
        text=True,
    )
    assert "test result: ok. 44 passed" in test_out, "All 44 native tests must pass"
    print("Native Tests: 44/44 PASSED")

    # 2. Check wheel existence
    assert WHEEL_PATH.exists(), f"Wheel must exist at {WHEEL_PATH}"

    # 3. Check live service and task
    s = service()
    running_tasks = ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE, desiredStatus="RUNNING")["taskArns"]
    if running_tasks:
        assert len(running_tasks) == 1, f"Expected at most 1 running task, got {running_tasks}"
        source_arn = running_tasks[0]
        old_task = task(source_arn)
        assert old_task["lastStatus"] == "RUNNING" and old_task.get("healthStatus") == "HEALTHY"
        ob = observation()
        assert ob["available"] and not ob["checkpoint_error"] and not ob["durability_blocked"]
        live_tick = ob["live_tick"]
        persisted_tick = ob["persisted_tick"]
    else:
        source_arn = None
        zero_writers([])
        live_tick = None
        persisted_tick = None

    td = ecs.describe_task_definition(taskDefinition=s["taskDefinition"])["taskDefinition"]

    emit(
        "plan_verified",
        commit=commit,
        base=BASE,
        old_task=source_arn,
        old_definition=s["taskDefinition"],
        live_tick=live_tick,
        persisted_tick=persisted_tick,
    )

    if not args.execute:
        print("\nDry-run verified successfully. To execute live cutover, pass --execute.")
        return

    folder = Path("/tmp") / ("biofunctional-release-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    folder.mkdir()
    journal = folder / "receipt.jsonl"
    emit("release_start", commit=commit)

    # Build container image
    context = Path(tempfile.mkdtemp(prefix="biofunctional-build-"))
    shutil.copyfile(WHEEL_PATH, context / WHEEL_NAME)
    shutil.copyfile(ROOT / "tools/guala_retention_release_operator.py", context / "a1_retention_release_operator.py")
    shutil.copyfile(ROOT / "tools/guala_oscillation_release_operator.py", context / "a1_oscillation_operator.py")
    shutil.copytree(
        ROOT / "dsf_ai_service",
        context / "dsf_ai_service",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )

    dockerfile = [
        f"FROM {BASE}",
        "ARG RELEASE_COMMIT",
        "ENV GIT_SHA=${RELEASE_COMMIT}",
        f"COPY {WHEEL_NAME} /tmp/{WHEEL_NAME}",
        f"RUN pip install --no-deps --force-reinstall /tmp/{WHEEL_NAME} && rm /tmp/{WHEEL_NAME}",
        "COPY dsf_ai_service /app/dsf_ai_service",
        "COPY a1_retention_release_operator.py /opt/a1_retention_release_operator.py",
        "COPY a1_oscillation_operator.py /opt/a1_oscillation_operator.py",
    ]
    (context / "Dockerfile").write_text("\n".join(dockerfile) + "\n")

    tag = f"{REPOSITORY}:biofunctional-{commit[:12]}"
    print(f"Building image {tag}...")
    with (folder / "build.log").open("w") as output:
        subprocess.run(
            ["docker", "build", "--build-arg", f"RELEASE_COMMIT={commit}", "-t", tag, str(context)],
            stdout=output,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=600,
        )
    emit("image_built", tag=tag)

    # Docker push
    print("Pushing image to ECR...")
    auth = ecr.get_authorization_token()["authorizationData"][0]
    username, password = base64.b64decode(auth["authorizationToken"]).decode().split(":", 1)
    subprocess.run(
        ["docker", "login", "--username", username, "--password-stdin", auth["proxyEndpoint"]],
        input=password,
        text=True,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with (folder / "push.log").open("w") as output:
        subprocess.run(
            ["docker", "push", tag],
            stdout=output,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=600,
        )

    detail = ecr.describe_images(repositoryName="dsf-ai", imageIds=[{"imageTag": tag.split(":")[-1]}])["imageDetails"][0]
    digest = detail["imageDigest"]
    manifest = ecr.batch_get_image(repositoryName="dsf-ai", imageIds=[{"imageDigest": digest}])
    assert len(manifest.get("images", [])) == 1 and not manifest.get("failures")
    emit("immutable_image", image=f"{REPOSITORY}@{digest}")

    # Register task definition
    allowed = set(ecs.meta.service_model.operation_model("RegisterTaskDefinition").input_shape.members)
    registration = {k: copy.deepcopy(v) for k, v in td.items() if k in allowed}
    registration["containerDefinitions"][0]["image"] = f"{REPOSITORY}@{digest}"
    new_def = ecs.register_task_definition(**registration)["taskDefinition"]["taskDefinitionArn"]
    emit("registered", definition=new_def)
    print(f"Registered new task definition: {new_def}")

    # Execute cutover
    drained = False
    candidate_arns = set()
    start_ms = int(time.time() * 1000) - 1000

    try:
        drained = True
        if source_arn:
            before = observation()
            assert before["available"] and not before["checkpoint_error"]
            print(f"Draining service from task {source_arn}...")
            ecs.update_service(cluster=CLUSTER, service=SERVICE, desiredCount=0)
            emit("drain_requested", task=source_arn, observation=before)

            stopped = wait_stopped(source_arn)
            assert next(c for c in stopped["containers"] if c["name"] == "dsf-ai").get("exitCode") == 0
            for _ in range(30):
                current = service()
                if (current["desiredCount"], current["runningCount"], current["pendingCount"]) == (0, 0, 0):
                    break
                time.sleep(2)
            zero_writers([source_arn])

            shutdown = log_messages(source_arn, start_ms)
            assert any("Application shutdown complete" in line for line in shutdown)
            assert not any("Traceback" in line or "Application shutdown failed" in line for line in shutdown)
            emit("clean_zero_writer", task=source_arn, logs=shutdown)
        else:
            zero_writers([])
            emit("clean_zero_writer_preexisting")

        print("Zero writers verified. Taking durable state backup...")
        backups = records(oneoff(new_def, s["networkConfiguration"], "backup"), "a1.retention.final_backup.v1")
        assert len(backups) == 1, f"Expected 1 backup record, got {len(backups)}"
        backup = backups[0]
        assert backup["current"]["identity"] == IDENTITY
        zero_writers([source_arn] if source_arn else [])
        print(f"Backup verified at organism tick {backup['current']['organism_tick']}.")

        print("Activating successor task definition...")
        activate(new_def, backup, source_arn, candidate_arns, digest)
        print("SUCCESS: Successor task healthy, single-writer verified, live tick advancing.")
        emit("cutover_success", definition=new_def, digest=digest)
    except BaseException as e:
        emit("cutover_failure", error=str(e))
        if drained:
            print("CUTOVER FAILED: Ensuring fail-closed zero writers...")
            ecs.update_service(cluster=CLUSTER, service=SERVICE, desiredCount=0)
            for desired in ("RUNNING", "STOPPED"):
                candidate_arns.update(
                    ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE, desiredStatus=desired)["taskArns"]
                )
            for arn in candidate_arns | ({source_arn} if source_arn else set()):
                wait_stopped(arn)
            for _ in range(30):
                current = service()
                if (current["desiredCount"], current["runningCount"], current["pendingCount"]) == (0, 0, 0):
                    break
                time.sleep(2)
            zero_writers(candidate_arns | ({source_arn} if source_arn else set()))
            emit("failure_zero_writers_verified", state_preserved=True, no_old_checkpoint_restored=True)
        raise


if __name__ == "__main__":
    main()
