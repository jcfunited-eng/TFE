"""Focused release-control proofs. These fakes test commands, never organism behavior."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "tools/deploy_dsf_ai.sh"
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
MANIFEST = '{"schemaVersion":2,"mediaType":"application/vnd.docker.distribution.manifest.v2+json"}'
DIGEST = "sha256:" + hashlib.sha256(MANIFEST.encode()).hexdigest()

# Each executable is a separate process, as the actual controller invokes it.
# Every call is recorded; state changes are confined to this test's temporary directory.
CLI = r'''
import json, os
from pathlib import Path
import sys
root = Path(os.environ["RELEASE_TEST_ROOT"])
state_path = root / "state.json"
state = json.loads(state_path.read_text())
args = sys.argv[1:]
name = Path(sys.argv[0]).name
with (root / "calls.jsonl").open("a") as out:
    out.write(json.dumps([name, *args]) + "\n")
def reply(value):
    state_path.write_text(json.dumps(state))
    print(value if isinstance(value, str) else json.dumps(value))
    raise SystemExit(0)
def refuse(message):
    state_path.write_text(json.dumps(state))
    print(message, file=sys.stderr)
    raise SystemExit(1)
def opt(key):
    return args[args.index(key) + 1]
identity = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
prefix = "arn:aws:ecs:us-east-1:418384447921:"
old_definition = prefix + "task-definition/dsf-ai-task:1456"
new_definition = prefix + "task-definition/dsf-ai-task:1457"
old_task = prefix + "task/tfe-web-cluster/source"
new_task = prefix + "task/tfe-web-cluster/candidate"
digest = os.environ["RELEASE_TEST_DIGEST"]
image = "418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai@" + digest
new = state.get("definition") == new_definition
definition = new_definition if new else old_definition
desired = state.get("desired", 1)
scenario = state.get("scenario", "")
base = {
    "family": "dsf-ai-task", "cpu": "4096", "memory": "16384",
    "networkMode": "awsvpc", "requiresCompatibilities": ["FARGATE"],
    "containerDefinitions": [{
        "name": "dsf-ai", "image": "old@sha256:" + "a" * 64,
        "command": ["retired-override"],
        "environment": [
            {"name": "GUALA_PAIRED_ROOT", "value": "/app/guala/paired-current-gen2"},
            {"name": "GUALA_MAX_WORLD_BYTES", "value": "16777216"},
            {"name": "PYTHONUNBUFFERED", "value": "1"},
        ],
        "mountPoints": [{"sourceVolume": "gualaloom-state",
                         "containerPath": "/app/guala", "readOnly": False}],
        "logConfiguration": {"logDriver": "awslogs", "options": {
            "awslogs-group": "/ecs/dsf-ai", "awslogs-region": "us-east-1",
            "awslogs-stream-prefix": "dsf-ai",
        }},
    }],
    "volumes": [{"name": "gualaloom-state", "efsVolumeConfiguration": {
        "fileSystemId": "fs-real-shape", "transitEncryption": "ENABLED",
    }}],
}
if name == "git":
    if args == ["rev-parse", "--show-toplevel"]: reply(str(root))
    if args == ["rev-parse", "--verify", "HEAD"]: reply("e" * 40 if scenario.startswith("revision-") else "f" * 40)
    if args == ["rev-parse", "--verify", "f" * 40 + "^{commit}"]: reply("f" * 40)
    if args[:4] == ["diff", "--no-renames", "--name-only", "-z"]:
        reply("native/guala_core/src/lib.rs" if scenario == "revision-runtime"
              else "tools/deploy_dsf_ai.sh" + chr(0) + "tests/test_deterministic_guala_deployment.py")
    if args == ["status", "--porcelain=v1", "--untracked-files=all"]: reply("")
if name == "docker":
    if args == ["image", "inspect", image]:
        reply([{"RepoDigests": [image], "Config": {"Labels": {
            "org.opencontainers.image.revision": "f" * 40,
        }}}])
if name == "curl":
    url = args[-1]
    if url.endswith("/health"): reply({"alive": True, "schema": "guala.lean_health.v1"})
    if url.endswith("/ready"): reply({"ready": True})
    if url.endswith("/observation"):
        state["observations"] = state.get("observations", 0) + 1
        busy = scenario == "busy" and state["observations"] == 1
        reply({
            "schema": "guala.lean_actor_observation.v1",
            "identity": "wrong" if scenario == "identity" else identity,
            "available": True, "checkpoint_error": None, "cleanup_error": None,
            "checkpoint_outstanding": busy, "durability_blocked": False,
            "live_tick": 103 if new else 100, "persisted_tick": 102 if new else 100,
            "persisted_body_sha256": "b" * 64, "persisted_world_sha256": "c" * 64,
        })
if name == "aws":
    operation = tuple(args[:2])
    if operation == ("ecr", "batch-get-image"):
        reply({"images": [{"imageId": {"imageDigest": digest},
                           "imageManifest": os.environ["RELEASE_TEST_MANIFEST"]}]})
    if operation == ("ecr", "put-image"): reply({})
    if operation == ("ecr", "describe-images"):
        reply({"imageDetails": [{"imageDigest": digest}]})
    if operation == ("ecs", "describe-services"):
        if new and desired and scenario == "startup-unselected" and not state.get("startup_failed"):
            state["startup_failed"] = True
            refuse("candidate startup status temporarily unavailable before ARN selection")
        reply({"services": [{
            "status": "ACTIVE", "taskDefinition": definition,
            "desiredCount": desired, "runningCount": desired, "pendingCount": 0,
            "deployments": [{"status": "PRIMARY", "rolloutState": "COMPLETED"}],
        }]})
    if operation == ("ecs", "list-tasks"):
        if opt("--desired-status") == "STOPPED":
            reply({"taskArns": ([old_task] if state.get("drained") else [])
                   + ([new_task] if new and not desired else [])})
        reply({"taskArns": ([new_task if new else old_task] if desired else [])})
    if operation == ("ecs", "describe-tasks"):
        arn = opt("--tasks")
        stopped = arn == old_task and state.get("drained", False) and scenario != "resume-source-running"
        if arn == new_task and not desired:
            state["candidate_stop_reads"] = state.get("candidate_stop_reads", 0) + 1
            stopped = scenario != "cleanup-never-stops"
            if scenario in ("cleanup-late", "startup-unselected"):
                stopped = state["candidate_stop_reads"] >= 2
        reply({"tasks": [{
            "taskArn": arn, "taskDefinitionArn": new_definition if arn == new_task else old_definition,
            "lastStatus": "STOPPED" if stopped else "RUNNING", "healthStatus": "HEALTHY",
            "containers": [{"name": "dsf-ai",
                            "exitCode": 1 if scenario == "exit" else 0,
                            "imageDigest": digest if arn == new_task else "sha256:" + "a" * 64}],
        }]})
    if operation == ("ecs", "describe-task-definition"):
        arn = opt("--task-definition")
        result = state.get("registered", base) if arn == new_definition else base
        if arn == new_definition and state.get("resume"):
            result = json.loads(json.dumps(base))
            result["containerDefinitions"][0]["image"] = image
            result["containerDefinitions"][0].pop("command")
            if scenario == "resume-wrong-candidate": result["cpu"] = "8192"
        reply({"taskDefinition": {**result, "taskDefinitionArn": arn}})
    if operation == ("ecs", "register-task-definition"):
        if "--generate-cli-skeleton" in args: reply({})
        state["registered"] = json.loads(opt("--cli-input-json"))
        reply({"taskDefinition": {"taskDefinitionArn": new_definition, **state["registered"]}})
    if operation == ("ecs", "update-service"):
        count = int(opt("--desired-count"))
        if count == 0:
            state["stops"] = state.get("stops", 0) + 1
            if scenario == "cleanup-refused" and state["stops"] > 1:
                refuse("cleanup stop refused")
            state["drained"] = True
        state["desired"] = count
        if "--task-definition" in args: state["definition"] = opt("--task-definition")
        reply({})
    if operation == ("logs", "filter-log-events"):
        if opt("--log-stream-names").endswith("/source"):
            if scenario == "no-shutdown": reply({"events": []})
            if scenario.startswith("pages-"):
                page = int(opt("--next-token")) if "--next-token" in args else 0
                if scenario == "pages-repeat":
                    reply({"events": [], "nextToken": "1"})
                if scenario == "pages-bound":
                    reply({"events": [], "nextToken": str(page + 1)})
                if scenario == "pages-events":
                    reply({"events": [{"message": "Application shutdown complete."}] * (100 if page == 0 else 1),
                           **({"nextToken": "1"} if page == 0 else {})})
                if page == 0:
                    reply({"events": [{"message": "Application shutdown complete."}], "nextToken": "1"})
                reply({"events": [{"message": "Application shutdown failed."}]
                       if scenario == "pages-late-failure" else []})
            line = ("Application shutdown failed. Exiting."
                    if scenario in ("shutdown", "cleanup-refused")
                    else "INFO: Application shutdown complete.")
            reply({"events": [{"message": line}]})
        receipt = {
            "schema": "guala.paired_predecessor.v1", "identity": identity, "organism_tick": 101,
            "body_sha256": "d" * 64, "body_bytes": 100,
            "world_sha256": "e" * 64, "world_bytes": 10,
        }
        if scenario in ("startup-behind", "cleanup-late", "cleanup-never-stops"):
            receipt["organism_tick"] = 99
        reply({"events": [{"message": json.dumps(receipt)}]})
refuse("unexpected fake command: " + name + " " + repr(args))
'''


@pytest.fixture
def release(tmp_path):
    commands = tmp_path / "bin"
    commands.mkdir()
    for name in ("aws", "docker", "git", "curl"):
        path = commands / name
        path.write_text(f"#!{sys.executable}\n" + CLI)
        path.chmod(0o755)
    (tmp_path / "state.json").write_text("{}")
    backup = tmp_path / "backup.zip"
    body, world = b"saved-body", b'{"world":"saved"}'
    current = {"identity": IDENTITY, "organism_tick": 90}
    for kind, value in (("body", body), ("world", world)):
        current[f"{kind}_bytes"] = len(value)
        current[f"{kind}_sha256"] = hashlib.sha256(value).hexdigest()
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("body.glorun.gz", gzip.compress(body))
        archive.writestr("world.json", world)
        archive.writestr("pointer.json", json.dumps({"current": current}))
    env = {
        **os.environ, "PATH": str(commands) + os.pathsep + os.environ["PATH"],
        "RELEASE_TEST_ROOT": str(tmp_path), "RELEASE_TEST_DIGEST": DIGEST,
        "RELEASE_TEST_MANIFEST": MANIFEST, "HTTP_WAIT_SECONDS": "1",
        "SERVICE_WAIT_SECONDS": "1",
    }

    def run(mode="--dry-run", scenario="", digest=DIGEST):
        state = {"scenario": scenario}
        extra = []
        if mode == "--resume-cutover":
            state.update(resume=True, desired=0, drained=True)
            if scenario == "resume-service-live": state["desired"] = 1
            prefix = "arn:aws:ecs:us-east-1:418384447921:"
            plan = {
                "schema": "guala.release_plan.v1", "mode": "--cutover", "cloud_writes": False,
                "source_task": prefix + "task/tfe-web-cluster/source",
                "source_definition": prefix + "task-definition/dsf-ai-task:1456",
                "image": "418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai@" + DIGEST,
                "git_sha": "f" * 40, "live_tick": 100,
                "backup": {"archive_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(), **current},
            }
            failure = {"status": "failed_closed", "zero_writers": "verified",
                       "automatic_legacy_rollback": False}
            if scenario == "resume-wrong-backup": plan["backup"]["archive_sha256"] = "0" * 64
            if scenario == "resume-unverified": failure["zero_writers"] = "UNVERIFIED"
            prior = tmp_path / "prior.log"
            prior.write_text(chr(10).join([json.dumps(plan),
                                         "ERROR: task receipt query exceeded its bounded page",
                                         json.dumps(failure), ""]))
            extra = [str(prior), prefix + "task-definition/dsf-ai-task:1457"]
        (tmp_path / "state.json").write_text(json.dumps(state))
        result = subprocess.run(
            ["bash", str(CONTROLLER), mode, digest, str(backup), *extra],
            env=env, text=True, capture_output=True, timeout=25,
        )
        log = tmp_path / "calls.jsonl"
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, calls

    return run, backup


def mutations(calls):
    return [
        call for call in calls if call[:3] in (
            ["aws", "ecs", "update-service"], ["aws", "ecs", "register-task-definition"],
            ["aws", "ecr", "put-image"],
        ) and "--generate-cli-skeleton" not in call
    ]


def test_real_controller_dry_run_validates_registration_without_cloud_writes(release):
    run, _ = release
    result, calls = run()
    assert result.returncode == 0, result.stderr
    assert mutations(calls) == []
    assert len([c for c in calls if "--generate-cli-skeleton" in c]) == 1
    assert json.loads(result.stdout)["cloud_writes"] is False
    assert not any(c[:3] == ["docker", "container", "start"] for c in calls)


def test_cutover_orders_exact_stop_final_receipt_zero_then_one_candidate(release):
    run, _ = release
    result, calls = run("--cutover")
    assert result.returncode == 0, result.stderr
    writes = mutations(calls)
    assert sum(c[:3] == ["aws", "ecs", "register-task-definition"] for c in writes) == 1
    updates = [c for c in writes if c[:3] == ["aws", "ecs", "update-service"]]
    assert [c[c.index("--desired-count") + 1] for c in updates] == ["0", "0", "1"]
    start = calls.index(updates[-1])
    shutdown = next(i for i, c in enumerate(calls)
                    if c[:3] == ["aws", "logs", "filter-log-events"]
                    and c[c.index("--log-stream-names") + 1].endswith("/source"))
    assert shutdown < calls.index(updates[1]) < start
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt["status"] == "continuity_health_verified"
    assert receipt["behavioral_acceptance"] == "pending"
    assert receipt["predecessor"]["organism_tick"] == 101  # final live, not backup's 90
    assert receipt["native_tick"] > receipt["predecessor"]["organism_tick"]
    register = next(c for c in writes if c[:3] == ["aws", "ecs", "register-task-definition"])
    target = json.loads(register[register.index("--cli-input-json") + 1])
    assert target["cpu"] == "4096" and target["memory"] == "16384"
    assert "command" not in target["containerDefinitions"][0]


def test_only_healthy_busy_custody_is_retried(release):
    run, _ = release
    result, calls = run(scenario="busy")
    assert result.returncode == 0, result.stderr
    assert len([c for c in calls if c[0] == "curl" and c[-1].endswith("/observation")]) == 2
    assert mutations(calls) == []


def test_identity_failure_is_immediate_and_non_mutating(release):
    run, _ = release
    result, calls = run("--cutover", "identity")
    assert result.returncode != 0 and "identity changed" in result.stderr
    assert len([c for c in calls if c[0] == "curl"]) == 1
    assert mutations(calls) == []


@pytest.mark.parametrize("mode,digest", [("--anything", DIGEST), ("--cutover", "latest")])
def test_invalid_invocation_never_reaches_external_commands(release, mode, digest):
    run, _ = release
    result, calls = run(mode, digest=digest)
    assert result.returncode != 0 and calls == []


def test_corrupt_backup_refuses_before_external_commands(release):
    run, backup = release
    backup.write_bytes(b"not a zip")
    result, calls = run("--cutover")
    assert result.returncode != 0 and calls == []


@pytest.mark.parametrize("scenario", ["shutdown", "no-shutdown", "exit", "startup-behind"])
def test_uncertain_custody_fails_closed_with_verified_zero(release, scenario):
    run, _ = release
    result, calls = run("--cutover", scenario)
    assert result.returncode != 0
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt["status"] == "failed_closed" and receipt["zero_writers"] == "verified"
    updates = [c for c in mutations(calls) if c[:3] == ["aws", "ecs", "update-service"]]
    assert updates[-1][updates[-1].index("--desired-count") + 1] == "0"
    if scenario != "startup-behind":
        assert all(c[c.index("--desired-count") + 1] == "0" for c in updates)


def test_failed_cleanup_never_claims_zero(release):
    run, _ = release
    result, _ = run("--cutover", "cleanup-refused")
    assert result.returncode != 0
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt["zero_writers"] == "UNVERIFIED"
    assert receipt["automatic_legacy_rollback"] is False


@pytest.mark.parametrize("scenario", ["cleanup-late", "startup-unselected"])
def test_zero_counts_cannot_hide_a_candidate_still_shutting_down(release, scenario):
    run, _ = release
    result, calls = run("--cutover", scenario)
    assert result.returncode != 0
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt["zero_writers"] == "verified"
    last_stop = max(i for i, c in enumerate(calls)
                    if c[:3] == ["aws", "ecs", "update-service"]
                    and c[c.index("--desired-count") + 1] == "0")
    shutdown_reads = [
        c for c in calls[last_stop + 1:]
        if c[:3] == ["aws", "ecs", "describe-tasks"]
        and c[c.index("--tasks") + 1].endswith("/candidate")
    ]
    assert len(shutdown_reads) >= 2  # first read is still actually RUNNING
    assert any(
        c[:3] == ["aws", "ecs", "list-tasks"]
        and c[c.index("--desired-status") + 1] == "STOPPED"
        for c in calls[last_stop + 1:]
    )


def test_candidate_that_never_stops_cannot_be_reported_as_zero_writers(release):
    run, _ = release
    result, calls = run("--cutover", "cleanup-never-stops")
    assert result.returncode != 0
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt["zero_writers"] == "UNVERIFIED"
    assert any(
        c[:3] == ["aws", "ecs", "describe-tasks"]
        and c[c.index("--tasks") + 1].endswith("/candidate")
        for c in calls
    )


def test_log_pagination_is_exhausted_before_candidate_start(release):
    run, _ = release
    result, calls = run("--cutover", "pages-pass")
    assert result.returncode == 0, result.stderr
    pages = [i for i, c in enumerate(calls)
             if c[:3] == ["aws", "logs", "filter-log-events"]
             and c[c.index("--log-stream-names") + 1].endswith("/source")]
    assert len(pages) == 2
    start = next(i for i, c in enumerate(calls)
                 if c[:3] == ["aws", "ecs", "update-service"]
                 and c[c.index("--desired-count") + 1] == "1")
    assert pages[-1] < start


@pytest.mark.parametrize("scenario", [
    "pages-late-failure", "pages-repeat", "pages-bound", "pages-events",
])
def test_log_success_cannot_hide_later_failure_or_unbounded_pages(release, scenario):
    run, _ = release
    result, calls = run("--cutover", scenario)
    assert result.returncode != 0
    assert not any(c[:3] == ["aws", "ecs", "update-service"]
                   and c[c.index("--desired-count") + 1] == "1" for c in calls)
    assert json.loads(result.stdout.splitlines()[-1])["zero_writers"] == "verified"


@pytest.mark.parametrize("scenario", ["pages-pass", "revision-controller"])
def test_resume_reuses_existing_candidate_without_registration_or_live_source_observation(release, scenario):
    run, _ = release
    result, calls = run("--resume-cutover", scenario)
    assert result.returncode == 0, result.stderr
    assert not any(c[:3] == ["aws", "ecs", "register-task-definition"] for c in calls)
    updates = [c for c in mutations(calls) if c[:3] == ["aws", "ecs", "update-service"]]
    assert [c[c.index("--desired-count") + 1] for c in updates] == ["0", "1"]
    first_write = calls.index(updates[0])
    assert not any(c[0] == "curl" for c in calls[:first_write])
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt["git_sha"] == "f" * 40
    assert receipt["controller_git_sha"] == ("e" * 40 if scenario.startswith("revision-") else "f" * 40)
    assert receipt["behavioral_acceptance"] == "pending"
    assert json.loads(result.stdout.splitlines()[0])["retained_tick_lower_bound"] == 100


@pytest.mark.parametrize("scenario", [
    "resume-wrong-backup", "resume-unverified", "resume-source-running",
    "resume-service-live", "resume-wrong-candidate", "pages-late-failure", "revision-runtime",
])
def test_resume_refuses_drift_without_any_cloud_write(release, scenario):
    run, _ = release
    result, calls = run("--resume-cutover", scenario)
    assert result.returncode != 0
    assert mutations(calls) == []
