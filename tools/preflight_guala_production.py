#!/usr/bin/env python3
"""Fail-closed, non-mutating preflight for one Guala production release.

The program reads Git, the reviewed release package, ECS, ECR, Secrets
Manager, and the live readiness surface.  It never creates, registers,
updates, scales, stops, uploads, publishes, invalidates, or deletes anything.
On success it emits the exact candidate-rehearsal and ECS-cutover command
shapes as data; it does not execute them.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence
import uuid


SCHEMA = "guala.production.preflight.v1"
AWS_REGION = "us-east-1"
AWS_ACCOUNT = "418384447921"
ECR_REPOSITORY = "dsf-ai"
ECR_URI = (
    f"{AWS_ACCOUNT}.dkr.ecr.{AWS_REGION}.amazonaws.com/{ECR_REPOSITORY}"
)
ECS_CLUSTER = "tfe-web-cluster"
ECS_SERVICE = "dsf-ai-service-lb"
TASK_FAMILY = "dsf-ai-task"
CONTAINER_NAME = "dsf-ai"
CONTROL_ORIGIN = "https://dsf-ai.com"
ALB_DNS = "dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
CONTROL_SECRET_ID = "gualaloom/api-key/prod"
RELEASE_MANIFEST = "deploy/guala_release_manifest.json"
DEPLOY_CONTROLLER = "tools/deploy_dsf_ai.sh"
# How long the read-only readiness capture may WAIT behind a lesson in flight.
# It bounds patience, never correctness: see ``_read_live_readiness``.
READINESS_MAX_SECONDS = 900
REHEARSAL_CONTROLLER = "tools/run_guala_candidate_rehearsal_task.py"

SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")

READ_ONLY_AWS_CALLS = frozenset({
    ("cloudfront", "get-distribution"),
    ("ecr", "describe-images"),
    ("ecs", "describe-services"),
    ("ecs", "describe-task-definition"),
    ("ecs", "describe-tasks"),
    ("ecs", "list-tasks"),
    ("s3api", "get-bucket-location"),
    ("secretsmanager", "get-secret-value"),
})

REQUIRED_BUILD_CONTROL = frozenset({
    "deploy/guala_release_manifest.json",
    "dsf_ai_service/Dockerfile",
    "dsf_ai_service/buildspec.yml",
    "tools/deploy_dsf_ai.sh",
    "tools/package_guala_release.py",
    "tools/preflight_guala_production.py",
    "tools/run_guala_candidate_rehearsal_task.py",
})
REQUIRED_NATIVE_CORE = frozenset({
    "native/guala_core/Cargo.lock",
    "native/guala_core/Cargo.toml",
    "native/guala_core/pyproject.toml",
    "native/guala_core/src/lib.rs",
    "native/guala_core/src/organism_runtime.rs",
    "native/guala_core/src/resident_cognitive_formation.rs",
    "native/guala_core/src/resident_receptor_transition.rs",
})
REQUIRED_NATIVE_RUNTIME = frozenset({
    "dsf_ai_service/glew_runtime/native_resident_organism.py",
    "dsf_ai_service/substrate/native_organism_binary_store.py",
    "dsf_ai_service/substrate/native_resident_resource_admission.py",
})

# These paths can restore the rejected Python-owner/generation cognition or a
# separate deployment-seal ceremony.  A reviewed native release may not ship
# them merely as a fallback.
FORBIDDEN_RELEASE_PATHS = frozenset({
    "dsf_ai_service/substrate/authoritative_cold_generation_store.py",
    "dsf_ai_service/substrate/deployment_generation.py",
    "dsf_ai_service/substrate/live_recovery_generation.py",
    "dsf_ai_service/substrate/native_core.py",
    "dsf_ai_service/substrate/owner_scoped_persistence.py",
    "dsf_ai_service/v4/guala_physical_runtime.py",
    "dsf_ai_service/v4/guala_physical_runtime_core.py",
    "tools/ecs_seal_transport.py",
})

FORBIDDEN_ENVIRONMENT_NAMES = frozenset({
    "FORCE_S3_RESTORE",
    "GUALA_EXACT_FIELD_EXECUTOR_REQUIRED",
    "GUALA_GENERATION_STORE_ROOT",
    "GUALA_LIVE_RECOVERY_STORE_ROOT",
    "GUALA_OWNER_LOCK_PATH",
    "GUALA_REQUIRE_SEALED_STATE",
    "STATE_DIR",
})
FORBIDDEN_DATABASE_ENVIRONMENT = re.compile(
    r"(?:^|_)(?:DATABASE|DB|MONGO|MYSQL|POSTGRES|REDIS|SQLALCHEMY)(?:_|$)",
    re.IGNORECASE,
)


class PreflightError(RuntimeError):
    """One exact preflight gate failed."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_commit(value: object, label: str) -> str:
    if not isinstance(value, str) or COMMIT_RE.fullmatch(value) is None:
        raise PreflightError(f"{label} is not an exact Git commit")
    return value


def _require_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise PreflightError(f"{label} is not an immutable image digest")
    return value


def _require_uuid(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise PreflightError(f"{label} is not a canonical UUID")
    try:
        canonical = str(uuid.UUID(value))
    except ValueError as error:
        raise PreflightError(f"{label} is not a canonical UUID") from error
    if value != canonical:
        raise PreflightError(f"{label} is not a canonical UUID")
    return value


def _task_definition_name(value: str) -> str:
    name = value.rsplit("/", 1)[-1]
    if not re.fullmatch(rf"{re.escape(TASK_FAMILY)}:[1-9][0-9]*", name):
        raise PreflightError(
            f"task definition is not in the {TASK_FAMILY} family: {value}"
        )
    return name


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str


class Commands:
    """Local command boundary with an explicit AWS read-only allowlist."""

    def run(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        redactions: Sequence[str] = (),
        timeout: int = 300,
    ) -> CommandResult:
        completed = subprocess.run(
            list(arguments),
            cwd=cwd,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        if completed.returncode != 0:
            rendered = " ".join(arguments)
            detail = completed.stderr.strip() or completed.stdout.strip()
            for secret in redactions:
                if secret:
                    rendered = rendered.replace(secret, "<redacted>")
                    detail = detail.replace(secret, "<redacted>")
            raise PreflightError(f"command failed: {rendered}: {detail}")
        return CommandResult(completed.stdout, completed.stderr)

    def aws(self, service: str, operation: str, *arguments: str) -> object:
        if (service, operation) not in READ_ONLY_AWS_CALLS:
            raise PreflightError(
                f"preflight attempted a mutating or unreviewed AWS call: "
                f"{service} {operation}"
            )
        result = self.run(
            [
                "aws",
                service,
                operation,
                "--region",
                AWS_REGION,
                *arguments,
                "--output",
                "json",
            ]
        )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise PreflightError(
                f"AWS {service} {operation} returned non-JSON output"
            ) from error


def validate_worktree(
    root: Path,
    expected_commit: str,
    commands: Commands,
) -> dict[str, object]:
    expected = _require_commit(expected_commit, "expected commit")
    root = root.resolve(strict=True)
    top = Path(commands.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"]
    ).stdout.strip()).resolve(strict=True)
    if top != root:
        raise PreflightError(
            f"requested root {root} is not exact Git root {top}"
        )
    commit = commands.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"]
    ).stdout.strip()
    if commit != expected:
        raise PreflightError(
            f"reviewed HEAD {commit} differs from expected commit {expected}"
        )
    dirty = commands.run([
        "git",
        "-C",
        str(root),
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ]).stdout
    if dirty:
        first = dirty.splitlines()[0]
        raise PreflightError(f"reviewed Guala worktree is dirty: {first}")
    commands.run(["git", "-C", str(root), "diff", "--check"])
    return {"commit": commit, "root": str(root), "status": "clean"}


def _strict_json_file(path: Path) -> object:
    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in pairs:
            if name in result:
                raise PreflightError(f"duplicate JSON key in {path}: {name}")
            result[name] = value
        return result

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate,
        )
    except json.JSONDecodeError as error:
        raise PreflightError(f"invalid JSON in {path}: {error}") from error


def validate_manifest(root: Path) -> dict[str, object]:
    manifest_path = root / RELEASE_MANIFEST
    value = _strict_json_file(manifest_path)
    if not isinstance(value, dict):
        raise PreflightError("release manifest root is not an object")
    if (
        value.get("schema") != "guala.reviewed_release_manifest.v1"
        or value.get("release_name") != "guala-production"
    ):
        raise PreflightError("release manifest identity changed")
    categories = value.get("categories")
    if not isinstance(categories, list):
        raise PreflightError("release manifest categories are absent")
    by_category: dict[str, set[str]] = {}
    all_files: set[str] = set()
    for category in categories:
        if not isinstance(category, dict):
            raise PreflightError("release manifest category is not an object")
        name = category.get("name")
        files = category.get("files")
        if (
            not isinstance(name, str)
            or name in by_category
            or not isinstance(files, list)
            or any(not isinstance(item, str) for item in files)
        ):
            raise PreflightError("release manifest category is invalid")
        file_set = set(files)
        if len(file_set) != len(files):
            raise PreflightError(f"release category {name} has duplicates")
        overlap = all_files & file_set
        if overlap:
            raise PreflightError(
                f"release files occur in multiple categories: {sorted(overlap)}"
            )
        all_files.update(file_set)
        by_category[name] = file_set

    requirements = {
        "build_control": REQUIRED_BUILD_CONTROL,
        "native_core": REQUIRED_NATIVE_CORE,
        "runtime_python": REQUIRED_NATIVE_RUNTIME,
    }
    missing: dict[str, list[str]] = {}
    for category, required in requirements.items():
        absent = sorted(required - by_category.get(category, set()))
        if absent:
            missing[category] = absent
    if missing:
        raise PreflightError(
            "release manifest omits native production closure: "
            + json.dumps(missing, sort_keys=True)
        )
    forbidden = sorted(all_files & FORBIDDEN_RELEASE_PATHS)
    if forbidden:
        raise PreflightError(
            f"release manifest can resurrect legacy cognition: {forbidden}"
        )
    for relative in sorted(all_files):
        source = root / relative
        if not source.is_file() or source.is_symlink():
            raise PreflightError(
                f"manifest source is missing or not a regular file: {relative}"
            )
    return {
        "file_count": len(all_files),
        "manifest_sha256": _sha256(manifest_path.read_bytes()),
        "native_core_files": len(by_category.get("native_core", set())),
        "runtime_python_files": len(
            by_category.get("runtime_python", set())
        ),
    }


def validate_controller(root: Path) -> dict[str, object]:
    source = (root / DEPLOY_CONTROLLER).read_text(encoding="utf-8")
    if 'ECS_CLUSTER="tfe-web-cluster"' not in source:
        raise PreflightError("deployment controller cluster changed")
    if 'ECS_SERVICE="dsf-ai-service-lb"' not in source:
        raise PreflightError("deployment controller service changed")
    if "tfe-web-service-lb" in source:
        raise PreflightError("deployment controller references the TFE service")
    forbidden_tokens = {
        "automatic rollback to an older organism": "rollback=true",
        "legacy generation-store requirement": "GUALA_GENERATION_STORE_ROOT",
        "legacy sealed-state requirement": "GUALA_REQUIRE_SEALED_STATE",
        "owner-lock requirement": "GUALA_OWNER_LOCK_PATH",
        "separate seal transport": "ecs_seal_transport.py",
        "separate quiesce/seal route": "/internal/deployment/quiesce",
    }
    found = [
        label for label, token in forbidden_tokens.items() if token in source
    ]
    if found:
        raise PreflightError(
            "deployment controller retains prohibited cutover mechanisms: "
            f"{found}"
        )
    if "rollback=false" not in source:
        raise PreflightError(
            "deployment controller does not explicitly fail closed without "
            "automatic old-image rollback"
        )
    return {
        "controller_sha256": _sha256(source.encode("utf-8")),
        "fail_closed_rollback": True,
        "service": ECS_SERVICE,
    }


def verify_package_and_native_build(
    root: Path,
    expected_commit: str,
    commands: Commands,
) -> dict[str, object]:
    commands.run([
        "cargo",
        "test",
        "--locked",
        "--manifest-path",
        str(root / "native/guala_core/Cargo.toml"),
    ], cwd=root, timeout=1800)
    with tempfile.TemporaryDirectory(prefix="guala-preflight-") as temporary:
        temporary_root = Path(temporary)
        stage = temporary_root / "stage"
        archive = temporary_root / "guala-release.zip"
        package = commands.run([
            sys.executable,
            str(root / "tools/package_guala_release.py"),
            "package",
            "--source-root",
            str(root),
            "--manifest",
            str(root / RELEASE_MANIFEST),
            "--stage-dir",
            str(stage),
            "--zip-path",
            str(archive),
        ], cwd=root, timeout=600)
        try:
            receipt = json.loads(package.stdout)
        except json.JSONDecodeError as error:
            raise PreflightError("release packager returned non-JSON") from error
        if receipt.get("git_commit") != expected_commit:
            raise PreflightError("packaged commit differs from reviewed commit")
        commands.run([
            sys.executable,
            str(root / "tools/package_guala_release.py"),
            "verify-context",
            "--context",
            str(stage),
        ], cwd=root)
        commands.run([
            sys.executable,
            str(root / "tools/package_guala_release.py"),
            "verify-archive",
            "--archive",
            str(archive),
        ], cwd=root)
        staged_required = {
            *(stage / path for path in REQUIRED_NATIVE_CORE),
            *(stage / "runtime" / path for path in REQUIRED_NATIVE_RUNTIME),
        }
        absent = sorted(
            str(path.relative_to(stage))
            for path in staged_required
            if not path.is_file()
        )
        if absent:
            raise PreflightError(
                f"packaged candidate omits native runtime files: {absent}"
            )
        commands.run([
            "cargo",
            "test",
            "--locked",
            "--manifest-path",
            str(stage / "native/guala_core/Cargo.toml"),
            "--target-dir",
            str(temporary_root / "packaged-native-target"),
        ], cwd=stage, timeout=1800)
        return {
            "archive_sha256": receipt.get("archive_sha256"),
            "git_commit": receipt.get("git_commit"),
            "receipt_sha256": receipt.get("receipt_sha256"),
            "source_file_count": receipt.get("source_file_count"),
        }


def validate_service(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise PreflightError("ECS describe-services response is invalid")
    if value.get("failures"):
        raise PreflightError(f"ECS service lookup failed: {value['failures']}")
    services = value.get("services")
    if not isinstance(services, list) or len(services) != 1:
        raise PreflightError("exactly one Guala service was not resolved")
    service = services[0]
    if (
        not isinstance(service, dict)
        or service.get("serviceName") != ECS_SERVICE
        or service.get("clusterArn", "").rsplit("/", 1)[-1] != ECS_CLUSTER
        or service.get("status") != "ACTIVE"
    ):
        raise PreflightError("resolved ECS target is not the active Guala service")
    counts = {
        key: service.get(key)
        for key in ("desiredCount", "runningCount", "pendingCount")
    }
    if counts != {"desiredCount": 1, "runningCount": 1, "pendingCount": 0}:
        raise PreflightError(f"Guala target is not settled at one process: {counts}")
    deployments = service.get("deployments")
    if (
        not isinstance(deployments, list)
        or len(deployments) != 1
        or deployments[0].get("status") != "PRIMARY"
        or deployments[0].get("rolloutState") != "COMPLETED"
    ):
        raise PreflightError("Guala target has overlapping deployment authority")
    task_definition = service.get("taskDefinition")
    if not isinstance(task_definition, str):
        raise PreflightError("Guala service has no task definition")
    _task_definition_name(task_definition)
    return {
        "service_arn": str(service.get("serviceArn", "")),
        "task_definition": task_definition,
    }


def validate_running_task(
    listed: object,
    described: object,
    expected_task_definition: str,
) -> dict[str, str]:
    if not isinstance(listed, dict) or listed.get("failures"):
        raise PreflightError("ECS list-tasks failed")
    task_arns = listed.get("taskArns")
    if not isinstance(task_arns, list) or len(task_arns) != 1:
        raise PreflightError("Guala service does not have exactly one running task")
    if not isinstance(described, dict) or described.get("failures"):
        raise PreflightError("ECS describe-tasks failed")
    tasks = described.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 1:
        raise PreflightError("exactly one running Guala task was not described")
    task = tasks[0]
    containers = task.get("containers")
    if (
        task.get("taskArn") != task_arns[0]
        or task.get("taskDefinitionArn") != expected_task_definition
        or task.get("lastStatus") != "RUNNING"
        or task.get("healthStatus") != "HEALTHY"
        or not isinstance(containers, list)
        or len(containers) != 1
        or containers[0].get("name") != CONTAINER_NAME
    ):
        raise PreflightError("running Guala task identity or health changed")
    digest = _require_digest(
        containers[0].get("imageDigest"), "running image digest"
    )
    return {"image_digest": digest, "task_arn": task_arns[0]}


def _single_container(task_definition: Mapping[str, object]) -> Mapping[str, object]:
    containers = task_definition.get("containerDefinitions")
    if (
        not isinstance(containers, list)
        or len(containers) != 1
        or not isinstance(containers[0], dict)
        or containers[0].get("name") != CONTAINER_NAME
        or containers[0].get("essential") is not True
    ):
        raise PreflightError("task definition does not contain one essential dsf-ai container")
    return containers[0]


def validate_candidate_task_definition(
    value: object,
    *,
    expected_task_definition: str,
    expected_commit: str,
    expected_digest: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or not isinstance(
        value.get("taskDefinition"), dict
    ):
        raise PreflightError("candidate task definition response is invalid")
    task = value["taskDefinition"]
    arn = task.get("taskDefinitionArn")
    if arn != expected_task_definition:
        raise PreflightError("candidate task definition ARN changed")
    _task_definition_name(expected_task_definition)
    if task.get("family") != TASK_FAMILY or task.get("status") != "ACTIVE":
        raise PreflightError("candidate is not an active Guala task definition")
    container = _single_container(task)
    exact_image = f"{ECR_URI}@{expected_digest}"
    if container.get("image") != exact_image:
        raise PreflightError(
            "candidate image is not digest-pinned to the reviewed ECR artifact"
        )
    environment = container.get("environment", [])
    if not isinstance(environment, list) or any(
        not isinstance(item, dict) for item in environment
    ):
        raise PreflightError("candidate environment is invalid")
    names = [item.get("name") for item in environment]
    if any(not isinstance(name, str) or not name for name in names):
        raise PreflightError("candidate environment has an invalid name")
    if len(names) != len(set(names)):
        raise PreflightError("candidate environment has duplicate authority")
    values = {item["name"]: item.get("value") for item in environment}
    forbidden = sorted(
        name
        for name in names
        if name in FORBIDDEN_ENVIRONMENT_NAMES
        or FORBIDDEN_DATABASE_ENVIRONMENT.search(name)
    )
    if forbidden:
        raise PreflightError(
            f"candidate restores owner/lock/seal/database environment: {forbidden}"
        )
    if values.get("DEPLOY_EXPECTED_GIT_SHA") != expected_commit:
        raise PreflightError("candidate expected commit differs")
    if values.get("DEPLOY_EXPECTED_IMAGE_DIGEST") != expected_digest:
        raise PreflightError("candidate expected image digest differs")
    cpu = task.get("cpu")
    memory = task.get("memory")
    if not isinstance(cpu, str) or not cpu.isdigit() or int(cpu) <= 0:
        raise PreflightError("candidate CPU envelope is absent")
    if not isinstance(memory, str) or not memory.isdigit() or int(memory) <= 0:
        raise PreflightError("candidate RAM envelope is absent")
    return {
        "cpu": int(cpu),
        "image": exact_image,
        "memory_mib": int(memory),
        "task_definition": expected_task_definition,
    }


def validate_ecr_artifact(value: object, expected_digest: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PreflightError("ECR artifact response is invalid")
    details = value.get("imageDetails")
    if not isinstance(details, list) or len(details) != 1:
        raise PreflightError("exactly one immutable ECR artifact was not resolved")
    detail = details[0]
    if detail.get("imageDigest") != expected_digest:
        raise PreflightError("ECR artifact digest changed")
    size = detail.get("imageSizeInBytes")
    if not isinstance(size, int) or size <= 0:
        raise PreflightError("ECR artifact has no physical byte size")
    return {"image_digest": expected_digest, "image_size_bytes": size}


def validate_readiness(
    value: object,
    *,
    expected_task_definition: str,
    expected_image_digest: str,
    genesis_cutover: bool = False,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PreflightError("live readiness is not an object")
    if value.get("ready") is not True or value.get("native_state") is not True:
        raise PreflightError("live predecessor is not ready native state")
    expected_name = _task_definition_name(expected_task_definition)
    if value.get("task_definition") != expected_name:
        raise PreflightError("readiness task definition differs from ECS")
    if value.get("image_digest") != expected_image_digest:
        raise PreflightError("readiness image digest differs from ECS")
    current_commit = _require_commit(value.get("git_sha"), "live Git commit")
    identity = _require_uuid(value.get("identity"), "live organism identity")
    native = value.get("native_resident")
    if native is not None:
        # Under a declared genesis cutover the predecessor's scope and
        # cognition claims are recorded historical facts, not inheritance
        # requirements: the candidate inherits no state. Outside a genesis
        # cutover the original strict pins apply.
        if not genesis_cutover:
            # 2026-08-07 correction: these pins asserted the retired
            # transport-only readiness shape and a body with NO neurons
            # and NO cognition.  They could never pass against any living
            # (or newborn) predecessor, and were only ever "passing"
            # because the deploy controller waived them by declaring a
            # genesis cutover unconditionally.  Continuity is now the
            # default, so the pins assert the TRUE served shape: the
            # sensory-transitions scope and a living cognitive body.
            # genuine_neuronal_fractal_available is deliberately not
            # asserted (a step fact, not body state, before the truth
            # repair; body state after it — either way not a continuity
            # requirement).
            if (
                value.get("ready_scope")
                != "http_native_current_and_admitted_sensory_transitions"
            ):
                raise PreflightError(
                    "native readiness scope is not the reviewed "
                    "sensory-transitions scope"
                )
            if (
                native.get("complete_neuron_available") is not True
                or native.get("cognition_available") is not True
            ):
                raise PreflightError(
                    "live predecessor does not present a living "
                    "cognitive body"
                )
    else:
        native = value.get("native_joint_fractal")
    if not isinstance(native, dict) or native.get("available") is not True:
        raise PreflightError("live native resident observation is unavailable")
    if native.get("python_callback_count") != 0:
        # The pre-native predecessor surface (native_joint_fractal) predates
        # the callback counter entirely. Under an explicit genesis cutover the
        # candidate inherits NO cognitive state from the predecessor, so the
        # missing counter is recorded as a legacy-surface fact instead of
        # refusing; any nonzero count, and any missing count outside a
        # declared genesis cutover, still refuses.
        legacy_surface_without_counter = (
            "python_callback_count" not in native
            and value.get("native_resident") is None
        )
        if not (genesis_cutover and legacy_surface_without_counter):
            raise PreflightError(
                "live resident reports Python cognition callbacks"
            )
    state_sha = native.get("state_sha256")
    if not isinstance(state_sha, str) or re.fullmatch(r"[0-9a-f]{64}", state_sha) is None:
        raise PreflightError("live resident has no immutable state identity")
    state_bytes = native.get("state_bytes")
    tick = native.get(
        "organism_tick",
        value.get("organism_tick", value.get("active_recovery_tick")),
    )
    if not isinstance(state_bytes, int) or state_bytes <= 0:
        raise PreflightError("live resident state byte count is invalid")
    if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
        raise PreflightError("live organism tick is invalid")
    generation = value.get("generation")
    active_generation = value.get("active_recovery_generation")
    if generation is not None:
        _require_uuid(generation, "live baseline generation")
    if active_generation is not None:
        _require_uuid(active_generation, "live active generation")
    return {
        "active_generation": active_generation,
        "baseline_generation": generation,
        "git_commit": current_commit,
        "identity": identity,
        "state_bytes": state_bytes,
        "state_sha256": state_sha,
        "tick": tick,
    }


def _read_live_readiness(commands: Commands, api_key: str) -> object:
    health = commands.run([
        "curl",
        "--fail",
        "--silent",
        "--show-error",
        "--connect-to",
        f"dsf-ai.com:443:{ALB_DNS}:443",
        "--connect-timeout",
        "10",
        "--max-time",
        "30",
        f"{CONTROL_ORIGIN}/health",
    ]).stdout
    try:
        health_value = json.loads(health)
    except json.JSONDecodeError as error:
        raise PreflightError("live health returned non-JSON") from error
    if health_value.get("status") != "ok":
        raise PreflightError("live health is not ok")
    nonce = hashlib.sha256(
        f"{api_key}\0guala-read-only-preflight".encode("utf-8")
    ).hexdigest()
    # ``/ready/guala`` acquires the transition lock deliberately, so that it
    # can only ever report PERSISTED state -- and that lock is held for a whole
    # lesson.  Capping the wait at a network round trip fails a healthy body
    # that merely happens to be mid-lesson.  Only the patience changes here;
    # every readiness assertion downstream is unchanged and still must pass.
    body = commands.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--connect-to",
            f"dsf-ai.com:443:{ALB_DNS}:443",
            "--connect-timeout",
            "10",
            "--max-time",
            str(READINESS_MAX_SECONDS),
            "-H",
            f"X-API-Key: {api_key}",
            "-H",
            f"X-Deploy-Nonce: {nonce}",
            f"{CONTROL_ORIGIN}/ready/guala",
        ],
        redactions=(api_key, nonce),
        # The runner's own default would kill curl before curl's deadline,
        # so the two budgets have to agree or the longer one is a fiction.
        timeout=READINESS_MAX_SECONDS + 30,
    ).stdout
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise PreflightError("live readiness returned non-JSON") from error


def _target_snapshot(commands: Commands) -> tuple[dict[str, object], dict[str, object]]:
    service_response = commands.aws(
        "ecs",
        "describe-services",
        "--cluster",
        ECS_CLUSTER,
        "--services",
        ECS_SERVICE,
    )
    service = validate_service(service_response)
    listed = commands.aws(
        "ecs",
        "list-tasks",
        "--cluster",
        ECS_CLUSTER,
        "--service-name",
        ECS_SERVICE,
        "--desired-status",
        "RUNNING",
    )
    if not isinstance(listed, dict) or not isinstance(listed.get("taskArns"), list):
        raise PreflightError("ECS list-tasks response is invalid")
    described = commands.aws(
        "ecs",
        "describe-tasks",
        "--cluster",
        ECS_CLUSTER,
        "--tasks",
        *listed["taskArns"],
    )
    task = validate_running_task(
        listed,
        described,
        str(service["task_definition"]),
    )
    snapshot = {**service, **task}
    return snapshot, {
        "service": service_response,
        "listed": listed,
        "described": described,
    }


def build_dry_run_plan(
    *,
    candidate_task_definition: str,
    expected_commit: str,
    expected_digest: str,
    predecessor: Mapping[str, object],
) -> dict[str, object]:
    rehearsal = [
        sys.executable,
        REHEARSAL_CONTROLLER,
        "--cluster",
        ECS_CLUSTER,
        "--service",
        ECS_SERVICE,
        "--candidate-task-definition",
        candidate_task_definition,
        "--candidate-git-sha",
        expected_commit,
        "--candidate-image-digest",
        expected_digest,
        "--expected-identity",
        str(predecessor["identity"]),
        "--expected-tick",
        str(predecessor["tick"]),
    ]
    if predecessor.get("baseline_generation") is not None:
        rehearsal.extend([
            "--expected-baseline-generation",
            str(predecessor["baseline_generation"]),
        ])
    if predecessor.get("active_generation") is not None:
        rehearsal.extend([
            "--expected-active-generation",
            str(predecessor["active_generation"]),
        ])
    drain = [
        "aws",
        "ecs",
        "update-service",
        "--region",
        AWS_REGION,
        "--cluster",
        ECS_CLUSTER,
        "--service",
        ECS_SERVICE,
        "--desired-count",
        "0",
        "--deployment-configuration",
        "maximumPercent=100,minimumHealthyPercent=0,"
        "deploymentCircuitBreaker={enable=true,rollback=false}",
    ]
    drain_wait = [
        "aws",
        "ecs",
        "wait",
        "services-stable",
        "--region",
        AWS_REGION,
        "--cluster",
        ECS_CLUSTER,
        "--services",
        ECS_SERVICE,
    ]
    cutover = [
        "aws",
        "ecs",
        "update-service",
        "--region",
        AWS_REGION,
        "--cluster",
        ECS_CLUSTER,
        "--service",
        ECS_SERVICE,
        "--task-definition",
        candidate_task_definition,
        "--desired-count",
        "1",
        "--deployment-configuration",
        "maximumPercent=100,minimumHealthyPercent=0,"
        "deploymentCircuitBreaker={enable=true,rollback=false}",
        "--force-new-deployment",
    ]
    wait = [
        "aws",
        "ecs",
        "wait",
        "services-stable",
        "--region",
        AWS_REGION,
        "--cluster",
        ECS_CLUSTER,
        "--services",
        ECS_SERVICE,
    ]
    record = {
        "candidate_rehearsal": rehearsal,
        "drain": drain,
        "post_drain_wait": drain_wait,
        "cutover": cutover,
        "post_cutover_wait": wait,
        "executed": False,
        "failure_mode": "closed_without_legacy_automatic_rollback",
        "predecessor_state_sha256": predecessor["state_sha256"],
        "schema": "guala.production.cutover_dry_run.v1",
    }
    return {**record, "plan_sha256": _sha256(_canonical_json(record))}


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--candidate-task-definition", required=True)
    parser.add_argument("--candidate-image-digest", required=True)
    parser.add_argument(
        "--genesis-cutover",
        action="store_true",
        help=(
            "declare that the candidate performs a fresh identity-pinned "
            "genesis and inherits no predecessor cognitive state"
        ),
    )
    return parser.parse_args(argv)


def run_preflight(values: argparse.Namespace, commands: Commands) -> dict[str, object]:
    root = values.root.resolve(strict=True)
    expected_commit = _require_commit(values.expected_commit, "expected commit")
    expected_digest = _require_digest(
        values.candidate_image_digest,
        "candidate image digest",
    )
    candidate_name = _task_definition_name(values.candidate_task_definition)

    worktree = validate_worktree(root, expected_commit, commands)
    manifest = validate_manifest(root)
    controller = validate_controller(root)
    package = verify_package_and_native_build(root, expected_commit, commands)

    before, _ = _target_snapshot(commands)
    if before["task_definition"] == values.candidate_task_definition:
        raise PreflightError("candidate task definition is already live")

    current_definition = commands.aws(
        "ecs",
        "describe-task-definition",
        "--task-definition",
        str(before["task_definition"]),
    )
    if not isinstance(current_definition, dict) or not isinstance(
        current_definition.get("taskDefinition"), dict
    ):
        raise PreflightError("current task definition response is invalid")
    _single_container(current_definition["taskDefinition"])

    candidate_response = commands.aws(
        "ecs",
        "describe-task-definition",
        "--task-definition",
        values.candidate_task_definition,
    )
    candidate = validate_candidate_task_definition(
        candidate_response,
        expected_task_definition=values.candidate_task_definition,
        expected_commit=expected_commit,
        expected_digest=expected_digest,
    )
    artifact_response = commands.aws(
        "ecr",
        "describe-images",
        "--repository-name",
        ECR_REPOSITORY,
        "--image-ids",
        f"imageDigest={expected_digest}",
    )
    artifact = validate_ecr_artifact(artifact_response, expected_digest)

    secret_response = commands.aws(
        "secretsmanager",
        "get-secret-value",
        "--secret-id",
        CONTROL_SECRET_ID,
    )
    if not isinstance(secret_response, dict):
        raise PreflightError("control secret response is invalid")
    api_key = secret_response.get("SecretString")
    if not isinstance(api_key, str) or not api_key:
        raise PreflightError("control secret is unavailable")
    readiness = validate_readiness(
        _read_live_readiness(commands, api_key),
        expected_task_definition=str(before["task_definition"]),
        expected_image_digest=str(before["image_digest"]),
        genesis_cutover=bool(getattr(values, "genesis_cutover", False)),
    )

    # Resolve, but never modify, the separate public UI targets named by the
    # deployment law.  This prevents a similarly named backup bucket or stale
    # distribution from entering a later publication plan.
    commands.aws(
        "s3api",
        "get-bucket-location",
        "--bucket",
        "dsf-ai-site",
    )
    distribution = commands.aws(
        "cloudfront",
        "get-distribution",
        "--id",
        "E17JT9XGBFU493",
    )
    if not isinstance(distribution, dict) or not isinstance(
        distribution.get("Distribution"), dict
    ):
        raise PreflightError("Guala UI distribution was not resolved")
    if distribution["Distribution"].get("Status") != "Deployed":
        raise PreflightError("Guala UI distribution is not deployed")

    plan = build_dry_run_plan(
        candidate_task_definition=values.candidate_task_definition,
        expected_commit=expected_commit,
        expected_digest=expected_digest,
        predecessor=readiness,
    )

    after, _ = _target_snapshot(commands)
    if after != before:
        raise PreflightError(
            "production target drifted during preflight; no cutover is admitted"
        )
    record = {
        "artifact": artifact,
        "candidate": candidate,
        "controller": controller,
        "dry_run": plan,
        "manifest": manifest,
        "package": package,
        "predecessor": readiness,
        "schema": SCHEMA,
        "status": "ready_for_discarded_state_rehearsal_not_deployed",
        "target": before,
        "ui_target": {
            "bucket": "dsf-ai-site",
            "distribution": "E17JT9XGBFU493",
            "status": "resolved_read_only",
        },
        "worktree": worktree,
    }
    return {**record, "receipt_sha256": _sha256(_canonical_json(record))}


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = run_preflight(_arguments(argv), Commands())
    except (OSError, PreflightError, subprocess.TimeoutExpired) as error:
        print(f"PREFLIGHT BLOCKED: {error}", file=sys.stderr)
        return 1
    print(_canonical_json(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
