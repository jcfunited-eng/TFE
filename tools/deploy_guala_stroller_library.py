"""Stroller Library Parking & Caretaker Deployment (Task 1558), one image, one definition, one writer cutover.

Includes full release:
- Stroller carriage relocated to south-west corner of library (9600, 5600, 0) across home world definitions.
- Caretaker presentation dispatch for park-stroller-library / stroller-park.
- Nocturnal house tidying maintains stroller parking perch in library south-west corner.
- Library expansion books aligned to bookshelf perches with zero floor disc collisions.
- Single-writer cutover from task definition dsf-ai-task:1557 to task definition 1558.

Invoke --plan first; --execute runs this same plan after local proof clearance.
"""
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
OLD_TASK = "b35c96647179444cabf98b6441c30fed"
OLD_DEFINITION = "arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:1557"
BASE = ACCOUNT + ".dkr.ecr." + REGION + ".amazonaws.com/dsf-ai@sha256:b5925e5fcaab71bac3fefcbaada587f85f62bad6b0a3153c1b7f74b04e655fa7"
REPOSITORY = BASE.split("@")[0]
FILES = {
    "dsf_ai_service/substrate/embodiment_world.py": "ebb7b69f726098fae70f9a75f801c2f7265829e40ff09001ff7941652b0b1a93",
    "dsf_ai_service/guala_caretaker_hand.py": "68ab2985906ef73730ab295b9ed9c6a806999c5d5132b81c9781b7a5cafe0427",
    "dsf_ai_service/lean_production_app.py": "8131709b6ec6782533f4bd63cbbbd197be75930b4ea3210367686961be8fcef7",
    "dsf_ai_service/guala_functional_organism.py": "60702d21cb72742b0bc64d94c30764b8b31981e895f1b886e1b4adf4ba5b01f8",
    "dsf_ai_service/guala_functional_loop.py": "505f2d1ed231cfc3b5ada0757bc05618db05092fdb067d9452546b1fdf347a9c",
    "dsf_ai_service/lean_actor.py": "885a5dd086db7d3a125d06c693edeb084b39b47c5308f34b05bd7be93fa96172",
    "dsf_ai_service/episodic_binding_engine.py": "dda3b1be483a0867a61f277b84b7d723beda63d05791584fc0a59b3f3590bb37",
    "dsf_ai_service/substrate/native_core.py": "7144580489e9b739538a90f1c0360209b3a4e2ecb94d6a6362db6b4aa902fbe3",
    "dsf_ai_service/guala_home_world.py": "7c84e0635b1b23d226c0246d1a0bb6ecd242df5c05c4de48b3edab6172a43ab0",
    "dsf_ai_service/lean_sensory_occurrence.py": "cb7ebef4b506c04f1f87e0f2dc593d53d21dd3d76badf3d41d514c8dc93f8b6d",
    "dsf_ai_service/static/gualaloom.html": "bbf5268f70b930a469b49212dc6ee5ecdadc0b89985d440ef9f103c805f480f8",
}
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
    return messages


def zero_writers(known_arns):
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
                        or ["python3", "/opt/a1_retention_release_operator.py", mode]
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
    backup_path = backup["output_zip"]
    operator_task = backup["source_task_arn"]
    emit(
        "final_backup_verified",
        backup=backup_path,
        operator_task=operator_task,
        digest=backup["zip_sha256"],
        persisted_tick=backup["current"]["organism_tick"],
    )
    emit("service_update_definition", definition=definition)
    ecs.update_service(
        cluster=CLUSTER,
        service=SERVICE,
        taskDefinition=definition,
        desiredCount=0,
    )
    emit("candidate_restore_from_backup_start", backup=backup_path)
    restore_messages = oneoff(
        definition,
        service()["networkConfiguration"],
        "restore",
        ["python3", "/opt/a1_retention_release_operator.py", "restore", backup_path],
    )
    restores = records(restore_messages, "a1.retention.restore_receipt.v1")
    assert len(restores) == 1
    restore = restores[0]
    assert restore["backup_zip"] == backup_path
    assert restore["restored_identity"] == IDENTITY
    assert restore["restored_tick"] == backup["current"]["organism_tick"]
    emit("candidate_restore_from_backup_verified", receipt=restore)
    zero_writers([source_arn])
    emit("service_desired_count_one", definition=definition)
    ecs.update_service(
        cluster=CLUSTER,
        service=SERVICE,
        taskDefinition=definition,
        desiredCount=1,
    )
    candidate_arn = None
    for _ in range(60):
        current_running = ecs.list_tasks(
            cluster=CLUSTER,
            serviceName=SERVICE,
            desiredStatus="RUNNING",
        )["taskArns"]
        candidates = [arn for arn in current_running if arn != source_arn]
        if len(candidates) == 1:
            candidate_arn = candidates[0]
            candidate_arns.add(candidate_arn)
            break
        time.sleep(2)
    assert candidate_arn, "candidate did not reach RUNNING status"
    emit("candidate_running", task=candidate_arn)
    candidate = task(candidate_arn)
    assert next(c for c in candidate["containers"] if c["name"] == "dsf-ai")["imageDigest"] == digest
    live = None
    for _ in range(60):
        try:
            live = observation()
            if (
                live["available"]
                and not live["checkpoint_error"]
                and not live["durability_blocked"]
                and live["persisted_tick"] >= backup["current"]["organism_tick"]
            ):
                break
        except Exception:
            pass
        time.sleep(2)
    assert live is not None
    assert live["identity"] == IDENTITY
    assert not live["checkpoint_error"]
    assert not live["durability_blocked"]
    assert live["persisted_tick"] >= backup["current"]["organism_tick"]
    ticks = []
    for _ in range(4):
        time.sleep(2)
        ticks.append(observation()["live_tick"])
    assert len(set(ticks)) > 1 and ticks[-1] > ticks[0]
    emit("candidate_live_and_advancing", initial=live, ticks=ticks)
    proof_messages = oneoff(definition, service()["networkConfiguration"], "proof")
    proofs = records(proof_messages, "a1.retention.proof.v1")
    assert len(proofs) == 1
    proof = proofs[0]
    assert proof["proof_string"] == "RETENTION_MATURE_CAUSAL_PERSISTENCE_FRESH_PROCESS_PASS"
    emit("candidate_memory_proof_verified", proof=proof)
    emit(
        "release_complete",
        task_definition=definition,
        running_task=candidate_arn,
        image_digest=digest,
        final_backup=backup_path,
        persisted_tick=live["persisted_tick"],
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
        "tools/guala_retention_actor_proof.py",
        "tools/guala_retention_release_operator.py",
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
    proof = (ROOT / "backups/runtime/a1-retention-only-proof-20260924.log").read_text()
    assert "RETENTION_MATURE_CAUSAL_PERSISTENCE_FRESH_PROCESS_PASS" in proof
    emit(
        "plan_verified",
        commit=commit,
        base=BASE,
        source_files=FILES,
        old_task=old["taskArn"],
        resources={"cpu": td["cpu"], "memory": td["memory"]},
        observation=ob,
        sequence="build, push, register, discarded-state rehearsal, recheck, drain, clean stop, final backup, start same candidate, exact restore/live verification",
        memory_candidate_included=True,
    )
    if not args.execute:
        return
    folder = ROOT / "backups/runtime" / ("stroller-library-release-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    folder.mkdir()
    journal = folder / "receipt.jsonl"
    emit("release_start", commit=commit)
    context = Path(tempfile.mkdtemp(prefix="stroller-library-build-"))
    dockerfile = ["FROM " + BASE, "ARG RELEASE_COMMIT", "ENV GIT_SHA=${RELEASE_COMMIT}"]
    for path in FILES:
        destination = context / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, destination)
        dockerfile.append("COPY " + path + " /app/" + path)
    for source, name in (
        ("tools/guala_retention_actor_proof.py", "a1_retention_actor_proof.py"),
        ("tools/guala_retention_release_operator.py", "a1_retention_release_operator.py"),
    ):
        shutil.copyfile(ROOT / source, context / name)
        dockerfile.append("COPY " + name + " /opt/" + name)
    (context / "Dockerfile").write_text("\n".join(dockerfile) + "\n")
    tag = REPOSITORY + ":stroller-library-" + commit[:12]
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
    assert any("RETENTION_MATURE_CAUSAL_PERSISTENCE_FRESH_PROCESS_PASS" in line for line in messages)
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
        assert backup["current"]["organism_tick"] >= before["persisted_tick"]
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
