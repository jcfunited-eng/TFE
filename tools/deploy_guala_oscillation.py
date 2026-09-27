"""OSC-01 release using the proven task1559 single-writer cutover sequence."""
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
OLD_TASK = "5b56802a81ba4978a36aafb995e829a3"
OLD_DEFINITION = "arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:1559"
BASE = ACCOUNT + ".dkr.ecr." + REGION + ".amazonaws.com/dsf-ai@sha256:3c9fce0ce0eaed2196b883a061b424d27c7f1d1709f433039394fba51d2e4b5d"
REPOSITORY = BASE.split("@")[0]
FILES = {"dsf_ai_service/guala_functional_organism.py": "10e23e1a7eb169b6b5b03995a857b55183d718788787e01cdc8735984d10e08c"}
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
ROOT = Path(__file__).resolve().parents[1]
CONFIG = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 2})
ecs = boto3.client("ecs", region_name=REGION, config=CONFIG)
ecr = boto3.client("ecr", region_name=REGION, config=CONFIG)
logs = boto3.client("logs", region_name=REGION, config=CONFIG)
journal = None


def emit(event, **data):
    record = {"at": datetime.now(timezone.utc).isoformat(), "event": event, **data}
    line = json.dumps(record, default=str)
    print(line, flush=True)
    if journal:
        with journal.open("a") as output:
            output.write(line + "\n")
            output.flush()
            os.fsync(output.fileno())


def service():
    response = ecs.describe_services(cluster=CLUSTER, services=[SERVICE])
    assert not response.get("failures"), response.get("failures")
    return response["services"][0]


def task(arn):
    response = ecs.describe_tasks(cluster=CLUSTER, tasks=[arn])
    assert not response.get("failures"), response.get("failures")
    return response["tasks"][0]


def observation():
    with urllib.request.urlopen("https://dsf-ai.com/api/v1/guala/observation", timeout=20) as response:
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


def wait_stopped(arn):
    waiter = ecs.get_waiter("tasks_stopped")
    waiter.wait(cluster=CLUSTER, tasks=[arn], WaiterConfig={"Delay": 2, "MaxAttempts": 150})
    return task(arn)


def log_messages(arn, start_time_ms=None):
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


def zero_writers(known_arns):
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


def oneoff(definition, network, mode, command=None):
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
    assert container.get("exitCode") == 0
    return messages


def records(messages, schema):
    found = []
    for line in messages:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema") == schema:
            found.append(value)
    return found


def activate(definition, backup, source_arn, candidate_arns, digest):
    zero_writers([source_arn])
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
    zero_writers([source_arn])
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
    assert len(receipts) == 1
    for key in ("identity", "organism_tick", "body_sha256", "body_bytes", "world_sha256", "world_bytes"):
        assert receipts[0][key] == backup["current"][key], key
    assert receipts[0]["functional_conversion"] is False
    first = observation()
    assert first["available"] and not first["checkpoint_error"] and not first["cleanup_error"]
    assert first["live_tick"] >= backup["current"]["organism_tick"]
    deadline = time.monotonic() + 60
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
    assert second is not None, f"persisted_tick did not advance past {backup['current']['organism_tick']} within 60s"
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


def main():
    global journal
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    assert boto3.client("sts", config=CONFIG).get_caller_identity()["Account"] == ACCOUNT
    assert shutil.which("docker")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    for path, digest in FILES.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
        committed = subprocess.check_output(["git", "show", commit + ":" + path])
        assert hashlib.sha256(committed).hexdigest() == digest, path + " is not committed"
    for path in (
        "tools/guala_oscillation_proof.py",
        "tools/guala_oscillation_release_operator.py",
        __file__,
    ):
        relative = str(Path(path).resolve().relative_to(ROOT))
        assert subprocess.check_output(["git", "show", commit + ":" + relative]) == Path(path).read_bytes()
    s = service()
    assert s["taskDefinition"] == OLD_DEFINITION
    deployment = s["deploymentConfiguration"]
    assert not deployment.get("deploymentCircuitBreaker", {}).get("rollback", False)
    assert not deployment.get("alarms", {}).get("rollback", False)
    scaling = boto3.client("application-autoscaling", region_name=REGION, config=CONFIG)
    targets = scaling.describe_scalable_targets(
        ServiceNamespace="ecs",
        ResourceIds=["service/" + CLUSTER + "/" + SERVICE],
    )["ScalableTargets"]
    assert not targets, "automatic scaling must not compete with single-writer cutover"
    assert (s["desiredCount"], s["runningCount"], s["pendingCount"]) == (1, 1, 0)
    old = task(OLD_TASK)
    assert old["lastStatus"] == "RUNNING"
    assert next(c for c in old["containers"] if c["name"] == "dsf-ai")["imageDigest"] == BASE.split("@")[1]
    assert ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE, desiredStatus="RUNNING")["taskArns"] == [old["taskArn"]]
    td = ecs.describe_task_definition(taskDefinition=OLD_DEFINITION)["taskDefinition"]
    assert td["cpu"] == "2048" and td["memory"] == "8192"
    assert len(td["containerDefinitions"]) == 1
    c = td["containerDefinitions"][0]
    assert c["name"] == "dsf-ai"
    env = {e["name"]: e["value"] for e in c["environment"]}
    assert env["GUALA_PAIRED_ROOT"] == "/app/guala/paired-current-gen2"
    assert env["GUALA_MAX_WORLD_BYTES"] == "16777216"
    ob = observation()
    assert ob["available"] and not ob["checkpoint_error"] and not ob["durability_blocked"]
    proof = (ROOT / "OSC01-proof.log").read_text()
    assert "OSC01_MATURE_PASS" in proof
    emit(
        "plan_verified",
        commit=commit,
        base=BASE,
        source_files=FILES,
        old_task=old["taskArn"],
        resources={"cpu": td["cpu"], "memory": td["memory"]},
        observation=ob,
        sequence="build, push, register, discarded-state rehearsal, recheck, drain, clean stop, final backup, start same candidate, exact restore/live verification",
        memory_candidate_included=False,
    )
    if not args.execute:
        return
    folder = Path("/tmp") / ("osc01-release-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    folder.mkdir()
    journal = folder / "receipt.jsonl"
    emit("release_start", commit=commit)
    context = Path(tempfile.mkdtemp(prefix="osc01-build-"))
    dockerfile = ["FROM " + BASE, "ARG RELEASE_COMMIT", "ENV GIT_SHA=${RELEASE_COMMIT}"]
    for path in FILES:
        destination = context / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, destination)
        dockerfile.append("COPY " + path + " /app/" + path)
    for source, name in (
        ("tools/guala_oscillation_proof.py", "guala_oscillation_proof.py"),
        ("tools/guala_oscillation_release_operator.py", "a1_oscillation_operator.py"),
    ):
        shutil.copyfile(ROOT / source, context / name)
        dockerfile.append("COPY " + name + " /opt/" + name)
    capture = Path("/tmp/guala-a1-oscillation-20260927.json")
    assert hashlib.sha256(capture.read_bytes()).hexdigest() == "c5c80e2baa61f3572e5b14118d090236f26f05b6fbd08c650c61a3dd71490373"
    shutil.copyfile(capture, context / "osc01-capture.json")
    dockerfile.append("COPY osc01-capture.json /opt/osc01-capture.json")
    (context / "Dockerfile").write_text("\n".join(dockerfile) + "\n")
    tag = REPOSITORY + ":osc01-" + commit[:12]
    with (folder / "build.log").open("w") as output:
        subprocess.run(
            ["docker", "build", "--build-arg", "RELEASE_COMMIT=" + commit, "-t", tag, str(context)],
            stdout=output,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=600,
        )
    emit("image_built", tag=tag)
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
    emit("immutable_image", image=REPOSITORY + "@" + digest)
    allowed = set(ecs.meta.service_model.operation_model("RegisterTaskDefinition").input_shape.members)
    registration = {k: copy.deepcopy(v) for k, v in td.items() if k in allowed}
    registration["containerDefinitions"][0]["image"] = REPOSITORY + "@" + digest
    definition = ecs.register_task_definition(**registration)["taskDefinition"]["taskDefinitionArn"]
    emit("registered", definition=definition)
    messages = oneoff(definition, s["networkConfiguration"], "rehearse")
    assert any("OSC01_MATURE_PASS" in line for line in messages)
    assert service()["taskDefinition"] == OLD_DEFINITION and task(OLD_TASK)["lastStatus"] == "RUNNING"
    before = observation()
    assert before["available"] and not before["checkpoint_error"]
    drained = False
    source_arn = old["taskArn"]
    candidate_arns = set()
    start_ms = int(time.time() * 1000) - 1000
    try:
        drained = True
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
        backups = records(oneoff(definition, s["networkConfiguration"], "backup"), "a1.retention.final_backup.v1")
        assert len(backups) == 1
        backup = backups[0]
        assert backup["current"]["identity"] == IDENTITY
        assert backup["current"]["organism_tick"] >= before["live_tick"]
        zero_writers([source_arn])
        activate(definition, backup, source_arn, candidate_arns, digest)
    except BaseException:
        if drained:
            ecs.update_service(cluster=CLUSTER, service=SERVICE, desiredCount=0)
            for desired in ("RUNNING", "STOPPED"):
                candidate_arns.update(
                    ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE, desiredStatus=desired)["taskArns"]
                )
            for arn in candidate_arns | {source_arn}:
                wait_stopped(arn)
            for _ in range(30):
                current = service()
                if (current["desiredCount"], current["runningCount"], current["pendingCount"]) == (0, 0, 0):
                    break
                time.sleep(2)
            zero_writers(candidate_arns | {source_arn})
            emit("failure_zero_writers_verified", state_preserved=True, no_old_checkpoint_restored=True)
        raise


if __name__ == "__main__":
    main()
