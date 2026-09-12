#!/usr/bin/env bash
# One explicit, continuity-only cutover. No build, legacy restore, or second brain.
set -euo pipefail
exec python3 - "$@" <<'PY'
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import zipfile

REGION = "us-east-1"
CLUSTER = "tfe-web-cluster"
SERVICE = "dsf-ai-service-lb"
REPOSITORY = "dsf-ai"
ECR = "418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai"
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
ALB = "dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
CONFIGURATION = "maximumPercent=200,minimumHealthyPercent=0,deploymentCircuitBreaker={enable=true,rollback=false}"
SHA = r"[0-9a-f]{64}"
armed = False
known_writers = set()
candidate_definition_arn = None
candidate_start_attempted = False


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def emit(**value):
    print(json.dumps(value, sort_keys=True), flush=True)


def command(*args):
    result = subprocess.run(args, text=True, capture_output=True, timeout=90)
    require(result.returncode == 0,
            f"{args[0]} {args[1]} failed: {result.stderr[-2000:].strip()}")
    return result.stdout.strip()


def aws(service, operation, *args):
    return json.loads(command(
        "aws", service, operation, "--region", REGION, "--output", "json",
        "--cli-connect-timeout", "10", "--cli-read-timeout", "60", *args,
    ))


def interval_bound(name, default):
    value = os.environ.get(name, str(default))
    require(value.isdigit() and 0 < int(value) <= 86400,
            f"{name} must be a positive bounded integer")
    return int(value)


def wait_until(probe, seconds, message):
    deadline = time.monotonic() + seconds
    while True:
        result = probe()
        if result:
            return result
        require(time.monotonic() < deadline, message)
        time.sleep(1)


def service():
    result = aws("ecs", "describe-services", "--cluster", CLUSTER, "--services", SERVICE)
    require(not result.get("failures") and len(result.get("services", [])) == 1,
            "service resolution is not singular")
    value = result["services"][0]
    require(value.get("status") == "ACTIVE", "service is not active")
    return value


def tasks(desired="RUNNING"):
    result = aws("ecs", "list-tasks", "--cluster", CLUSTER,
                 "--service-name", SERVICE, "--desired-status", desired,
                 "--max-results", "100", "--no-paginate")
    require(not result.get("nextToken"), "service task census exceeds its bounded page")
    return result["taskArns"]


def task(arn):
    result = aws("ecs", "describe-tasks", "--cluster", CLUSTER, "--tasks", arn)
    require(not result.get("failures") and len(result.get("tasks", [])) == 1,
            "task resolution is not singular")
    value = result["tasks"][0]
    require(value.get("taskArn") == arn and len(value.get("containers", [])) == 1,
            "task identity or container cardinality changed")
    require(value["containers"][0].get("name") == "dsf-ai", "unexpected container")
    return value


def settled(value, definition, count):
    deployments = value.get("deployments", [])
    return (
        value.get("taskDefinition") == definition
        and [value.get(k) for k in ("desiredCount", "runningCount", "pendingCount")]
        == [count, count, 0]
        and len(deployments) == 1
        and deployments[0].get("status") == "PRIMARY"
        and deployments[0].get("rolloutState") == "COMPLETED"
    )


def zero():
    value = service()
    return (
        [value.get(k) for k in ("desiredCount", "runningCount", "pendingCount")]
        == [0, 0, 0] and not tasks()
    )


def all_writers_stopped():
    # Desired STOPPED includes tasks still saving during shutdown. Keep their
    # exact identities even after they disappear from later task-list responses.
    known_writers.update(tasks())
    known_writers.update(tasks("STOPPED"))
    require(len(known_writers) <= 100, "writer identity census exceeds its release bound")
    observed = [task(arn) for arn in sorted(known_writers)]
    if candidate_start_attempted and not any(
        value.get("taskDefinitionArn") == candidate_definition_arn for value in observed
    ):
        return False  # Creation may have been accepted, but its writer is unobserved.
    return all(value.get("lastStatus") == "STOPPED" for value in observed) and zero()


def update(count, definition=None):
    args = ["--cluster", CLUSTER, "--service", SERVICE,
            "--desired-count", str(count), "--deployment-configuration", CONFIGURATION]
    if definition is not None:
        args += ["--task-definition", definition]
    return aws("ecs", "update-service", *args)


def http(path):
    return json.loads(command(
        "curl", "-fsS", "--connect-to", f"dsf-ai.com:443:{ALB}:443",
        "--connect-timeout", "10", "--max-time", "30", f"https://dsf-ai.com{path}",
    ))


def observation(minimum=0):
    value = http("/api/v1/guala/observation")
    require(value.get("schema") == "guala.lean_actor_observation.v1",
            "observation schema changed")
    require(value.get("identity") == IDENTITY, "organism identity changed")
    require(value.get("available") is True, "native actor is unavailable")
    require(value.get("checkpoint_error") is None and value.get("cleanup_error") is None,
            "durable custody failed")
    live, saved = value.get("live_tick"), value.get("persisted_tick")
    require(type(live) is int and type(saved) is int and live >= saved >= minimum,
            "native/custody clock is invalid or behind predecessor")
    for key in ("persisted_body_sha256", "persisted_world_sha256"):
        require(re.fullmatch(SHA, value.get(key, "")), f"{key} is invalid")
    for key in ("checkpoint_outstanding", "durability_blocked"):
        require(type(value.get(key)) is bool, f"{key} is not a Boolean")
    # Only healthy temporary custody work is retried. All failures above are hard.
    if value["checkpoint_outstanding"] or value["durability_blocked"]:
        return None
    return value


def backup_receipt(path):
    require(path.is_file(), "backup archive is absent")
    with zipfile.ZipFile(path) as archive:
        require(sorted(archive.namelist()) == ["body.glorun.gz", "pointer.json", "world.json"],
                "backup must contain exactly the paired body, world and pointer")
        require(archive.getinfo("pointer.json").file_size <= 16384, "backup pointer is oversized")
        current = json.loads(archive.read("pointer.json"))["current"]
        require(current.get("identity") == IDENTITY, "backup identity changed")
        require(type(current.get("organism_tick")) is int and current["organism_tick"] >= 0,
                "backup clock is invalid")
        for kind, limit in (("body", 16 * 1024**3), ("world", 16 * 1024**2)):
            size, digest = current.get(f"{kind}_bytes"), current.get(f"{kind}_sha256")
            require(type(size) is int and 0 < size <= limit, f"backup {kind} size is invalid")
            require(re.fullmatch(SHA, digest or ""), f"backup {kind} hash is invalid")
            member = "body.glorun.gz" if kind == "body" else "world.json"
            require(archive.getinfo(member).file_size <= limit + 1024**2,
                    f"backup {kind} member is oversized")
            actual, count = hashlib.sha256(), 0
            with archive.open(member) as raw:
                source = gzip.GzipFile(fileobj=raw) if kind == "body" else raw
                try:
                    while block := source.read(min(1024**2, size - count + 1)):
                        count += len(block)
                        require(count <= size, f"backup {kind} expands beyond declared size")
                        actual.update(block)
                finally:
                    if source is not raw:
                        source.close()
            require(count == size and actual.hexdigest() == digest,
                    f"backup {kind} bytes do not match CURRENT")
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    return {"archive_sha256": digest, **current}


def candidate_definition(source, image):
    allowed = (
        "family", "taskRoleArn", "executionRoleArn", "networkMode", "containerDefinitions",
        "volumes", "placementConstraints", "requiresCompatibilities", "cpu", "memory",
        "runtimePlatform", "ephemeralStorage", "pidMode", "ipcMode", "proxyConfiguration",
        "inferenceAccelerators",
    )
    target = copy.deepcopy({key: source[key] for key in allowed if key in source})
    require(target.get("family") == "dsf-ai-task", "unexpected task family")
    require((target.get("cpu"), target.get("memory")) == ("4096", "16384"),
            "approved CPU/RAM envelope changed")
    containers = target.get("containerDefinitions", [])
    require(len(containers) == 1 and containers[0].get("name") == "dsf-ai",
            "task definition has unexpected containers")
    container = containers[0]
    require(not container.get("entryPoint") and not container.get("secrets"),
            "unreviewed entrypoint or secret environment override")
    require(container.get("mountPoints") == [{
        "sourceVolume": "gualaloom-state", "containerPath": "/app/guala", "readOnly": False,
    }], "persistent mount changed")
    volumes = target.get("volumes", [])
    require(len(volumes) == 1 and volumes[0].get("name") == "gualaloom-state",
            "persistent volume changed")
    require(volumes[0].get("efsVolumeConfiguration", {}).get("transitEncryption") == "ENABLED",
            "persistent transport encryption changed")
    pairs = container.get("environment", [])
    env = {item["name"]: item["value"] for item in pairs}
    require(len(env) == len(pairs), "duplicate environment authority")
    root = env.get("GUALA_PAIRED_ROOT", "")
    require(root.startswith("/app/guala/") and ".." not in Path(root).parts,
            "paired CURRENT root is outside the persistent mount")
    require(env.get("GUALA_MAX_WORLD_BYTES") == "16777216", "world resource bound changed")
    log = container.get("logConfiguration", {})
    require(log.get("logDriver") == "awslogs"
            and log.get("options", {}).get("awslogs-region") == REGION
            and all(log["options"].get(k) for k in ("awslogs-group", "awslogs-stream-prefix")),
            "task-bound startup/shutdown evidence is unavailable")
    container["image"] = image
    container.pop("command", None)
    container["environment"] = [
        {"name": key, "value": value} for key, value in (
            ("GUALA_PAIRED_ROOT", root), ("GUALA_MAX_WORLD_BYTES", "16777216"),
            ("PYTHONUNBUFFERED", "1"),
        )
    ]
    return target


def messages(definition, arn, pattern):
    options = definition["containerDefinitions"][0]["logConfiguration"]["options"]
    stream = f'{options["awslogs-stream-prefix"]}/dsf-ai/{arn.rsplit("/", 1)[-1]}'
    lines, tokens, token = [], set(), None
    for _ in range(10):
        args = ["--log-group-name", options["awslogs-group"],
                "--log-stream-names", stream, "--filter-pattern", pattern,
                "--limit", "100", "--no-paginate"]
        if token is not None:
            args += ["--next-token", token]
        result = aws("logs", "filter-log-events", *args)
        lines.extend(event["message"] for event in result.get("events", []))
        require(len(lines) <= 100, "task receipt query exceeded 100 events")
        token = result.get("nextToken")
        if not token:
            return lines
        require(isinstance(token, str) and token not in tokens,
                "task receipt query repeated a continuation token")
        tokens.add(token)
    raise RuntimeError("task receipt query exceeded 10 pages")



def shutdown_complete(definition, arn):
    lines = messages(definition, arn, '"Application shutdown"')
    require(not any("failed" in line.lower() for line in lines), "old application shutdown failed")
    return any("Application shutdown complete." in line for line in lines)


def startup_receipt(definition, arn, minimum):
    lines = messages(definition, arn, '"guala.paired_predecessor.v1"')
    if not lines:
        return None
    require(len(lines) == 1, "candidate has multiple startup predecessor receipts")
    value = json.loads(lines[0])
    require(value.get("schema") == "guala.paired_predecessor.v1"
            and value.get("identity") == IDENTITY, "startup predecessor identity/schema changed")
    tick = value.get("organism_tick")
    require(type(tick) is int and tick >= minimum, "candidate restored behind final source")
    for kind in ("body", "world"):
        require(re.fullmatch(SHA, value.get(f"{kind}_sha256", "")), "startup hash is invalid")
        require(type(value.get(f"{kind}_bytes")) is int and value[f"{kind}_bytes"] > 0,
                "startup size is invalid")
    return value



def prior_cutover(path, image, image_revision, backup):
    require(path.is_file() and path.stat().st_size <= 65536,
            "prior cutover log is absent or oversized")
    records = []
    for line in path.read_text().splitlines():
        if line.startswith("{"):
            records.append(json.loads(line))
    require(len(records) == 2, "prior cutover log must contain one plan and one failure")
    plan, failure = records
    require(plan.get("schema") == "guala.release_plan.v1"
            and plan.get("mode") == "--cutover"
            and plan.get("cloud_writes") is False,
            "prior log is not an original cutover plan")
    require(failure == {"status": "failed_closed", "zero_writers": "verified",
                        "automatic_legacy_rollback": False},
            "prior cutover did not verify zero writers")
    require(plan.get("image") == image and plan.get("git_sha") == image_revision
            and plan.get("backup") == backup, "prior image/revision/backup differs")
    require(re.fullmatch(
        r"arn:aws:ecs:us-east-1:418384447921:task/tfe-web-cluster/[a-zA-Z0-9]+",
        plan.get("source_task", "")), "prior source task is outside the target")
    require(re.fullmatch(
        r"arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:[0-9]+",
        plan.get("source_definition", "")), "prior source definition is outside the target")
    require(type(plan.get("live_tick")) is int
            and plan["live_tick"] >= backup["organism_tick"], "prior clock is invalid")
    return plan

def interrupted(signum, frame):
    raise RuntimeError(f"release interrupted by signal {signum}")


def main():
    global armed, candidate_definition_arn, candidate_start_attempted
    resume = len(sys.argv) == 6 and sys.argv[1] == "--resume-cutover"
    require(resume or (len(sys.argv) == 4 and sys.argv[1] in ("--dry-run", "--cutover")),
            "Usage: bash tools/deploy_dsf_ai.sh --dry-run|--cutover DIGEST BACKUP_ZIP "
            "or --resume-cutover DIGEST BACKUP_ZIP PRIOR_LOG CANDIDATE_TASK_DEFINITION")
    mode, digest, backup = sys.argv[1:4]
    require(re.fullmatch("sha256:" + SHA, digest), "image must be an immutable sha256 digest")
    backup = backup_receipt(Path(backup).resolve())
    service_wait = interval_bound("SERVICE_WAIT_SECONDS", 2400)
    http_wait = interval_bound("HTTP_WAIT_SECONDS", 600)
    root = Path(command("git", "rev-parse", "--show-toplevel"))
    os.chdir(root)
    revision = command("git", "rev-parse", "--verify", "HEAD")
    require(not command("git", "status", "--porcelain=v1", "--untracked-files=all"),
            "release requires one clean reviewed Git commit")
    image = f"{ECR}@{digest}"
    registry = aws("ecr", "batch-get-image", "--repository-name", REPOSITORY,
                   "--image-ids", f"imageDigest={digest}")
    require(not registry.get("failures") and len(registry.get("images", [])) == 1,
            "immutable ECR image is absent")
    record = registry["images"][0]
    require(record["imageId"]["imageDigest"] == digest, "registry digest changed")
    manifest = record["imageManifest"]
    require("sha256:" + hashlib.sha256(manifest.encode()).hexdigest() == digest,
            "registry manifest does not match digest")
    local = json.loads(command("docker", "image", "inspect", image))
    require(len(local) == 1 and image in local[0].get("RepoDigests", []),
            "exact immutable image must already be pulled locally")
    image_revision = local[0].get("Config", {}).get("Labels", {}).get(
        "org.opencontainers.image.revision", "")
    require(re.fullmatch(r"[0-9a-f]{40}", image_revision), "image revision is invalid")
    require(command("git", "rev-parse", "--verify", image_revision + "^{commit}")
            == image_revision, "image source commit is unavailable")
    if image_revision != revision:
        changes = command("git", "diff", "--no-renames", "--name-only", "-z",
                          image_revision, revision, "--").split(chr(0))
        allowed = {
            "tools/deploy_dsf_ai.sh", "tests/test_deterministic_guala_deployment.py",
            "docs/GUALA_SPEECH_REPAIR_ATTEMPT_54_LEAN_SENSORIMOTOR_ROUTE_2026-09-08.md",
        }
        require(set(changes) - {""} <= allowed,
                "runtime/build source differs from the proven image")

    source_service = service()
    if resume:
        prior = prior_cutover(Path(sys.argv[4]).resolve(), image, image_revision, backup)
        source_definition, source_arn = prior["source_definition"], prior["source_task"]
        candidate = sys.argv[5]
        require(re.fullmatch(
            r"arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:[0-9]+",
            candidate) and candidate != source_definition, "invalid resume candidate definition")
        require(settled(source_service, source_definition, 0) and zero(),
                "resume requires the original service at zero")
        source_task = task(source_arn)
        require(source_task.get("taskDefinitionArn") == source_definition
                and source_task.get("lastStatus") == "STOPPED"
                and source_task["containers"][0].get("exitCode") == 0,
                "resume source is not the exact cleanly stopped predecessor")
        known_writers.add(source_arn)
        require(all_writers_stopped(), "resume found a writer still stopping")
        # The retained plan is a lower bound, not the last unrecorded pre-drain sample.
        cutover = {"live_tick": prior["live_tick"]}
    else:
        source_definition = source_service.get("taskDefinition")
        require(isinstance(source_definition, str) and "/dsf-ai-task:" in source_definition
                and settled(source_service, source_definition, 1), "source is not one settled writer")
        source_tasks = tasks()
        require(len(source_tasks) == 1, "source task is not singular")
        source_arn = source_tasks[0]
        known_writers.add(source_arn)
        source_task = task(source_arn)
        require(source_task.get("taskDefinitionArn") == source_definition
                and source_task.get("lastStatus") == "RUNNING", "source task drifted")
    base = aws("ecs", "describe-task-definition",
               "--task-definition", source_definition)["taskDefinition"]
    target = candidate_definition(base, image)
    if not resume:
        predecessor = wait_until(observation, http_wait, "predecessor custody stayed busy")
        require(backup["organism_tick"] <= predecessor["persisted_tick"],
                "backup is ahead of the current production predecessor")
        encoded = json.dumps(target, separators=(",", ":"))
        # AWS CLI validates this exact registration shape locally; it makes no service call.
        aws("ecs", "register-task-definition", "--cli-input-json", encoded,
            "--generate-cli-skeleton", "output")
        emit(schema="guala.release_plan.v1", mode=mode, source_task=source_arn,
             source_definition=source_definition, image=image, git_sha=image_revision,
             controller_git_sha=revision, backup=backup,
             live_tick=predecessor["live_tick"], cloud_writes=False)
        if mode == "--dry-run":
            return
        registered = aws("ecs", "register-task-definition",
                         "--cli-input-json", encoded)["taskDefinition"]
        candidate = registered["taskDefinitionArn"]
    candidate_definition_arn = candidate
    actual = aws("ecs", "describe-task-definition", "--task-definition", candidate)["taskDefinition"]
    require(all(actual.get(key) == value for key, value in target.items()),
            "registered task differs from reviewed clone")
    if not resume:
        require(settled(service(), source_definition, 1) and tasks() == [source_arn],
                "source changed before drain")
        cutover = wait_until(observation, http_wait, "pre-drain custody stayed busy")
        require(settled(service(), source_definition, 1) and tasks() == [source_arn],
                "source changed during pre-drain custody wait")
        armed = True
        update(0)
        stopped = wait_until(
            lambda: (value if (value := task(source_arn)).get("lastStatus") == "STOPPED" else None),
            service_wait, "exact source task did not stop",
        )
        wait_until(zero, service_wait, "source did not reach verified zero writers")
        require(stopped["containers"][0].get("exitCode") == 0, "old container did not exit cleanly")
    wait_until(lambda: shutdown_complete(base, source_arn), http_wait,
               "old task has no successful final-shutdown receipt")
    if resume:
        require(settled(service(), source_definition, 0) and all_writers_stopped(),
                "resume authority changed before candidate installation")
        emit(schema="guala.release_resume.v1", source_task=source_arn,
             source_definition=source_definition, task_definition=candidate,
             image=image, git_sha=image_revision, controller_git_sha=revision,
             backup=backup, retained_tick_lower_bound=cutover["live_tick"])
        armed = True
    update(0, candidate)
    wait_until(lambda: settled(service(), candidate, 0) and zero(), service_wait,
               "candidate definition was not installed at zero writers")
    candidate_start_attempted = True
    update(1)
    wait_until(lambda: settled(service(), candidate, 1), service_wait,
               "candidate service did not settle")
    candidate_tasks = tasks()
    require(len(candidate_tasks) == 1 and candidate_tasks[0] != source_arn,
            "candidate task is not singular and new")
    candidate_arn = candidate_tasks[0]
    known_writers.add(candidate_arn)

    def healthy_task():
        value = task(candidate_arn)
        require(value.get("taskDefinitionArn") == candidate
                and value["containers"][0].get("imageDigest") == digest,
                "running candidate artifact changed")
        require(value.get("lastStatus") == "RUNNING", "candidate stopped during health check")
        return value if value.get("healthStatus") == "HEALTHY" else None

    wait_until(healthy_task, service_wait, "candidate never became healthy")
    startup = wait_until(lambda: startup_receipt(actual, candidate_arn, cutover["live_tick"]),
                         http_wait, "candidate did not record its actual CURRENT predecessor")

    def advancing():
        if http("/health") != {"alive": True, "schema": "guala.lean_health.v1"}:
            return None
        if http("/ready") != {"ready": True}:
            return None
        value = observation(startup["organism_tick"])
        return value if value and value["live_tick"] > startup["organism_tick"] else None

    current = wait_until(advancing, http_wait, "candidate did not advance from its real predecessor")
    require(settled(service(), candidate, 1) and tasks() == [candidate_arn],
            "candidate authority changed during verification")
    armed = False
    # The tag describes the running artifact, not successful speech acceptance.
    aws("ecr", "put-image", "--repository-name", REPOSITORY,
        "--image-tag", "production-current", "--image-manifest", manifest)
    pinned = aws("ecr", "describe-images", "--repository-name", REPOSITORY,
                 "--image-ids", "imageTag=production-current")
    require(pinned["imageDetails"][0]["imageDigest"] == digest, "production tag differs from live image")
    emit(schema="guala.lean_deployment.v1", status="continuity_health_verified",
         behavioral_acceptance="pending", task=candidate_arn, task_definition=candidate,
         image_digest=digest, git_sha=image_revision, controller_git_sha=revision, identity=IDENTITY,
         predecessor=startup, native_tick=current["live_tick"], automatic_legacy_rollback=False)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        if armed:
            # Never claim zero writers merely because a stop request was sent.
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                update(0)
                wait_until(all_writers_stopped, interval_bound("SERVICE_WAIT_SECONDS", 2400),
                           "failure cleanup did not reach zero writers")
                emit(status="failed_closed", zero_writers="verified", automatic_legacy_rollback=False)
            except Exception as cleanup_error:
                emit(status="failed", zero_writers="UNVERIFIED", cleanup_error=str(cleanup_error),
                     automatic_legacy_rollback=False)
        sys.exit(1)
PY
