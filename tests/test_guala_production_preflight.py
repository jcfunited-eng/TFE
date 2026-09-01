from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "preflight_guala_production.py"
)
SPEC = importlib.util.spec_from_file_location(
    "guala_production_preflight_under_test",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
preflight = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)

COMMIT = "a" * 40
DIGEST = "sha256:" + "b" * 64
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
CURRENT_TASK = (
    "arn:aws:ecs:us-east-1:418384447921:"
    "task-definition/dsf-ai-task:853"
)
CANDIDATE_TASK = (
    "arn:aws:ecs:us-east-1:418384447921:"
    "task-definition/dsf-ai-task:900"
)


def _write_manifest(root: Path, *, extra: set[str] | None = None) -> None:
    categories = {
        "build_control": set(preflight.REQUIRED_BUILD_CONTROL),
        "native_core": set(preflight.REQUIRED_NATIVE_CORE),
        "runtime_python": set(preflight.REQUIRED_NATIVE_RUNTIME),
    }
    for relative in extra or set():
        categories.setdefault("legacy", set()).add(relative)
    value = {
        "categories": [
            {
                "archive_prefix": (
                    "runtime" if name == "runtime_python" else ""
                ),
                "files": sorted(files),
                "name": name,
                "reason": "test release closure",
            }
            for name, files in sorted(categories.items())
        ],
        "forbidden_source_patterns": ["never-match-this-test"],
        "internal_import_aliases": {},
        "internal_import_roots": ["dsf_ai_service"],
        "release_name": "guala-production",
        "runtime_entrypoints": ["dsf_ai_service/app.py"],
        "schema": "guala.reviewed_release_manifest.v1",
    }
    for relative in set().union(*categories.values()):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("test\n", encoding="utf-8")
    manifest = root / preflight.RELEASE_MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _candidate_definition(
    *,
    image: str | None = None,
    environment: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "taskDefinition": {
            "containerDefinitions": [{
                "environment": environment or [
                    {"name": "DEPLOY_EXPECTED_GIT_SHA", "value": COMMIT},
                    {
                        "name": "DEPLOY_EXPECTED_IMAGE_DIGEST",
                        "value": DIGEST,
                    },
                ],
                "essential": True,
                "image": image or f"{preflight.ECR_URI}@{DIGEST}",
                "name": preflight.CONTAINER_NAME,
            }],
            "cpu": "4096",
            "family": preflight.TASK_FAMILY,
            "memory": "16384",
            "status": "ACTIVE",
            "taskDefinitionArn": CANDIDATE_TASK,
        },
    }


def _service() -> dict[str, object]:
    return {
        "failures": [],
        "services": [{
            "clusterArn": (
                "arn:aws:ecs:us-east-1:418384447921:"
                "cluster/tfe-web-cluster"
            ),
            "deployments": [{
                "rolloutState": "COMPLETED",
                "status": "PRIMARY",
            }],
            "desiredCount": 1,
            "pendingCount": 0,
            "runningCount": 1,
            "serviceArn": (
                "arn:aws:ecs:us-east-1:418384447921:"
                "service/tfe-web-cluster/dsf-ai-service-lb"
            ),
            "serviceName": preflight.ECS_SERVICE,
            "status": "ACTIVE",
            "taskDefinition": CURRENT_TASK,
        }],
    }


def _readiness() -> dict[str, object]:
    return {
        "active_recovery_generation": (
            "d44d203f-5d1e-4f9e-869c-795751fc7597"
        ),
        "active_recovery_tick": 23_723_846,
        "generation": "ea2c5fc1-c0b7-47b6-be4c-73f6c938cfca",
        "git_sha": "c" * 40,
        "identity": IDENTITY,
        "image_digest": "sha256:" + "d" * 64,
        "native_joint_fractal": {
            "available": True,
            "organism_tick": 23_723_846,
            "python_callback_count": 0,
            "state_bytes": 500_000,
            "state_sha256": "e" * 64,
        },
        "native_state": True,
        "ready": True,
        "task_definition": "dsf-ai-task:853",
    }


def test_manifest_accepts_complete_native_release(tmp_path: Path) -> None:
    _write_manifest(tmp_path)
    result = preflight.validate_manifest(tmp_path)
    assert result["native_core_files"] == len(
        preflight.REQUIRED_NATIVE_CORE
    )
    assert result["runtime_python_files"] == len(
        preflight.REQUIRED_NATIVE_RUNTIME
    )


def test_manifest_fails_when_binary_store_is_not_packaged(
    tmp_path: Path,
) -> None:
    _write_manifest(tmp_path)
    path = tmp_path / preflight.RELEASE_MANIFEST
    value = json.loads(path.read_text(encoding="utf-8"))
    for category in value["categories"]:
        if category["name"] == "runtime_python":
            category["files"].remove(
                "dsf_ai_service/substrate/native_organism_binary_store.py"
            )
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(preflight.PreflightError, match="omits native"):
        preflight.validate_manifest(tmp_path)


def test_manifest_fails_if_legacy_owner_runtime_can_ship(
    tmp_path: Path,
) -> None:
    _write_manifest(
        tmp_path,
        extra={"dsf_ai_service/v4/guala_physical_runtime.py"},
    )
    with pytest.raises(preflight.PreflightError, match="resurrect"):
        preflight.validate_manifest(tmp_path)


def test_controller_accepts_fail_closed_cutover_without_seal(
    tmp_path: Path,
) -> None:
    controller = tmp_path / preflight.DEPLOY_CONTROLLER
    controller.parent.mkdir(parents=True)
    controller.write_text(
        'ECS_CLUSTER="tfe-web-cluster"\n'
        'ECS_SERVICE="dsf-ai-service-lb"\n'
        'DEPLOY_CONFIGURATION="rollback=false"\n',
        encoding="utf-8",
    )
    assert preflight.validate_controller(tmp_path)[
        "fail_closed_rollback"
    ] is True


@pytest.mark.parametrize(
    "rejected",
    [
        "rollback=true",
        "GUALA_OWNER_LOCK_PATH",
        "GUALA_REQUIRE_SEALED_STATE",
        "GUALA_GENERATION_STORE_ROOT",
        "ecs_seal_transport.py",
        "/internal/deployment/quiesce",
    ],
)
def test_controller_rejects_old_rollback_and_ceremony(
    tmp_path: Path,
    rejected: str,
) -> None:
    controller = tmp_path / preflight.DEPLOY_CONTROLLER
    controller.parent.mkdir(parents=True)
    controller.write_text(
        'ECS_CLUSTER="tfe-web-cluster"\n'
        'ECS_SERVICE="dsf-ai-service-lb"\n'
        'DEPLOY_CONFIGURATION="rollback=false"\n'
        f"# {rejected}\n",
        encoding="utf-8",
    )
    with pytest.raises(preflight.PreflightError, match="prohibited"):
        preflight.validate_controller(tmp_path)


def test_service_accepts_only_one_settled_guala_process() -> None:
    assert preflight.validate_service(_service())["task_definition"] == (
        CURRENT_TASK
    )


def test_service_rejects_tfe_target() -> None:
    value = _service()
    value["services"][0]["serviceName"] = "tfe-web-service-lb"
    with pytest.raises(preflight.PreflightError, match="not the active Guala"):
        preflight.validate_service(value)


def test_candidate_requires_digest_pinned_image_and_resources() -> None:
    result = preflight.validate_candidate_task_definition(
        _candidate_definition(),
        expected_task_definition=CANDIDATE_TASK,
        expected_commit=COMMIT,
        expected_digest=DIGEST,
    )
    assert result["cpu"] == 4096
    assert result["memory_mib"] == 16384
    assert result["image"] == f"{preflight.ECR_URI}@{DIGEST}"


def test_candidate_rejects_mutable_image_tag() -> None:
    with pytest.raises(preflight.PreflightError, match="digest-pinned"):
        preflight.validate_candidate_task_definition(
            _candidate_definition(image=f"{preflight.ECR_URI}:deploy-now"),
            expected_task_definition=CANDIDATE_TASK,
            expected_commit=COMMIT,
            expected_digest=DIGEST,
        )


@pytest.mark.parametrize(
    "name",
    [
        "GUALA_OWNER_LOCK_PATH",
        "GUALA_REQUIRE_SEALED_STATE",
        "DATABASE_URL",
        "REDIS_HOST",
    ],
)
def test_candidate_rejects_legacy_authority_environment(name: str) -> None:
    environment = [
        {"name": "DEPLOY_EXPECTED_GIT_SHA", "value": COMMIT},
        {"name": "DEPLOY_EXPECTED_IMAGE_DIGEST", "value": DIGEST},
        {"name": name, "value": "rejected"},
    ]
    with pytest.raises(preflight.PreflightError, match="environment"):
        preflight.validate_candidate_task_definition(
            _candidate_definition(environment=environment),
            expected_task_definition=CANDIDATE_TASK,
            expected_commit=COMMIT,
            expected_digest=DIGEST,
        )


def test_readiness_binds_ecs_image_identity_and_native_state() -> None:
    result = preflight.validate_readiness(
        _readiness(),
        expected_task_definition=CURRENT_TASK,
        expected_image_digest="sha256:" + "d" * 64,
    )
    assert result["identity"] == IDENTITY
    assert result["state_sha256"] == "e" * 64
    assert result["tick"] == 23_723_846


def test_readiness_rejects_python_cognition_callbacks() -> None:
    value = _readiness()
    value["native_joint_fractal"]["python_callback_count"] = 1
    with pytest.raises(preflight.PreflightError, match="Python cognition"):
        preflight.validate_readiness(
            value,
            expected_task_definition=CURRENT_TASK,
            expected_image_digest="sha256:" + "d" * 64,
        )


def test_dry_run_never_executes_and_disables_old_image_rollback() -> None:
    predecessor = preflight.validate_readiness(
        _readiness(),
        expected_task_definition=CURRENT_TASK,
        expected_image_digest="sha256:" + "d" * 64,
    )
    plan = preflight.build_dry_run_plan(
        candidate_task_definition=CANDIDATE_TASK,
        expected_commit=COMMIT,
        expected_digest=DIGEST,
        predecessor=predecessor,
    )
    assert plan["executed"] is False
    assert "update-service" in plan["drain"]
    assert plan["drain"][plan["drain"].index("--desired-count") + 1] == "0"
    assert "update-service" in plan["cutover"]
    assert any("rollback=false" in item for item in plan["cutover"])
    assert not any("rollback=true" in item for item in plan["cutover"])
    assert "--expected-identity" in plan["candidate_rehearsal"]
    assert len(plan["plan_sha256"]) == 64


def test_aws_boundary_refuses_mutation_before_subprocess() -> None:
    with pytest.raises(preflight.PreflightError, match="mutating"):
        preflight.Commands().aws(
            "ecs",
            "update-service",
            "--cluster",
            preflight.ECS_CLUSTER,
        )


def test_command_failure_redacts_deployment_credential() -> None:
    secret = "deployment-secret-must-not-escape"
    with pytest.raises(preflight.PreflightError) as captured:
        preflight.Commands().run(
            [
                sys.executable,
                "-c",
                "import sys; print(sys.argv[1], file=sys.stderr); raise SystemExit(1)",
                secret,
            ],
            redactions=(secret,),
        )
    assert secret not in str(captured.value)
    assert "<redacted>" in str(captured.value)


def test_native_failure_parser_collects_every_failed_binary_roster() -> None:
    output = """
failures:

    organism_runtime::tests::first_known_failure

test result: FAILED. 1 passed; 1 failed

failures:

    resident_cognitive_formation::tests::second_known_failure

test result: FAILED. 2 passed; 1 failed
"""
    assert preflight._failed_native_tests(output) == frozenset({
        "organism_runtime::tests::first_known_failure",
        "resident_cognitive_formation::tests::second_known_failure",
    })


def test_native_failure_parser_refuses_failed_result_without_roster() -> None:
    with pytest.raises(preflight.PreflightError, match="failure roster"):
        preflight._failed_native_tests("test result: FAILED. 0 passed\n")


def test_native_test_list_parser_requires_exact_test_identifiers() -> None:
    output = (
        "organism_runtime::tests::one: test\n"
        "not a test line\n"
        "resident_cognitive_formation::tests::two: test\n"
    )
    assert preflight._listed_native_tests(output) == frozenset({
        "organism_runtime::tests::one",
        "resident_cognitive_formation::tests::two",
    })


class _NativeTestCommands:
    def __init__(
        self,
        *,
        listed: set[str],
        failed: set[str],
        returncode: int = 101,
    ) -> None:
        self.listed = listed
        self.failed = failed
        self.returncode = returncode

    def run(self, arguments, **kwargs):
        if "--list" in arguments:
            return preflight.CommandResult(
                "".join(f"{name}: test\n" for name in sorted(self.listed)),
                "",
            )
        return preflight.CommandResult("", "")

    def observe(self, arguments, **kwargs):
        roster = "".join(f"    {name}\n" for name in sorted(self.failed))
        output = (
            f"\nfailures:\n\n{roster}\n"
            "test result: FAILED. 0 passed; 1 failed\n"
        )
        return preflight.CommandResult(output, "", self.returncode)


def _write_native_test_baseline(root: Path, failures: set[str]) -> None:
    path = root / preflight.NATIVE_TEST_BASELINE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "failures": sorted(failures),
            "first_proven_commit": COMMIT,
            "production_baseline_commit": COMMIT,
            "schema": "guala.native-test-baseline.v1",
        }),
        encoding="utf-8",
    )


def test_native_gate_accepts_only_named_present_baseline_failures(
    tmp_path: Path,
) -> None:
    known = {"organism_runtime::tests::known_failure"}
    _write_native_test_baseline(tmp_path, known)
    commands = _NativeTestCommands(listed=known, failed=known)
    result = preflight.verify_native_tests(
        root=tmp_path,
        manifest_path=tmp_path / "native/guala_core/Cargo.toml",
        expected_commit=COMMIT,
        commands=commands,
    )
    assert result["remaining_known_failures"] == sorted(known)


def test_native_gate_rejects_new_failure(tmp_path: Path) -> None:
    known = {"organism_runtime::tests::known_failure"}
    new = "organism_runtime::tests::new_failure"
    _write_native_test_baseline(tmp_path, known)
    commands = _NativeTestCommands(
        listed=known | {new},
        failed=known | {new},
    )
    with pytest.raises(preflight.PreflightError, match="introduces"):
        preflight.verify_native_tests(
            root=tmp_path,
            manifest_path=tmp_path / "native/guala_core/Cargo.toml",
            expected_commit=COMMIT,
            commands=commands,
        )


def test_native_gate_rejects_removed_baseline_test(tmp_path: Path) -> None:
    known = {"organism_runtime::tests::known_failure"}
    _write_native_test_baseline(tmp_path, known)
    commands = _NativeTestCommands(listed=set(), failed=set())
    with pytest.raises(preflight.PreflightError, match="removed or renamed"):
        preflight.verify_native_tests(
            root=tmp_path,
            manifest_path=tmp_path / "native/guala_core/Cargo.toml",
            expected_commit=COMMIT,
            commands=commands,
        )
