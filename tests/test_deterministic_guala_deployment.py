from pathlib import Path
import json
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "deploy_dsf_ai.sh"
SCRIPT = SCRIPT_PATH.read_text(encoding="utf-8")


def test_controller_is_one_bounded_reviewed_path() -> None:
    assert SCRIPT.count("package_guala_release.py package") == 1
    assert SCRIPT.count("codebuild start-build") == 1
    assert SCRIPT.count("ecs register-task-definition") == 1
    assert SCRIPT.count("preflight_guala_production.py") == 1
    assert SCRIPT.count(
        "python3 tools/run_guala_candidate_rehearsal_task.py"
    ) == 3
    assert "--mode rehearse" in SCRIPT
    assert "--mode publish" in SCRIPT
    assert "--mode cold-restore" in SCRIPT
    assert SCRIPT.count("aws ecs update-service") == 1
    assert "--repeat-cutover" not in SCRIPT
    assert "--rehearse-only" in SCRIPT


def test_controller_has_no_old_image_rollback_or_seal_ceremony() -> None:
    for forbidden in (
        "rollback=true",
        "GUALA_OWNER_LOCK_PATH",
        "GUALA_REQUIRE_SEALED_STATE",
        "GUALA_GENERATION_STORE_ROOT",
        "tools/ecs_seal_transport.py",
        "/internal/deployment/quiesce",
        "seal_live_organism",
        "interpret_guala_seal_response",
        "SEAL_LIFECYCLE_STATE_FILE",
        "tfe-web-service-lb",
    ):
        assert forbidden not in SCRIPT
    assert (
        "deploymentCircuitBreaker={enable=true,rollback=false}"
        in SCRIPT
    )


def test_candidate_is_digest_pinned_and_legacy_environment_is_removed() -> None:
    assert 'PINNED_IMAGE_URI="${ECR_URI}@${IMAGE_DIGEST}"' in SCRIPT
    assert 'container["image"] = os.environ["PINNED_IMAGE_URI"]' in SCRIPT
    assert (
        'container.get("image") != os.environ["PINNED_IMAGE_URI"]'
        in SCRIPT
    )
    assert '"GUALA_" + "OWNER_LOCK_PATH"' in SCRIPT
    assert '"GUALA_" + "REQUIRE_SEALED_STATE"' in SCRIPT
    assert '"GUALA_" + "GENERATION_STORE_ROOT"' in SCRIPT
    assert "candidate retains legacy authority environment" in SCRIPT
    assert "candidate contains database environment" in SCRIPT


def test_preflight_and_rehearsal_precede_cutover() -> None:
    preflight = SCRIPT.index("python3 tools/preflight_guala_production.py")
    rehearsal = SCRIPT.index(
        "python3 tools/run_guala_candidate_rehearsal_task.py"
    )
    update = SCRIPT.index("aws ecs update-service")
    live_proof = SCRIPT.index("CURRENT_RUNNING_TASK=$(verify_live_organism")
    pin = SCRIPT.index("image-tag production-current")
    assert preflight < rehearsal < update < live_proof < pin


def test_live_proof_is_native_resident_not_old_storage_cutover() -> None:
    assert 'native = value.get("native_resident", {})' in SCRIPT
    assert 'value.get("ready_scope")' in SCRIPT
    assert 'native.get("python_callback_count") != 0' in SCRIPT
    assert 'native.get("state_sha256")' in SCRIPT
    assert 'value.get("storage_cutover"' not in SCRIPT
    assert "retired_flat_full_copy_producer" not in SCRIPT


def test_controller_preserves_physical_resource_transport() -> None:
    assert '"sourceVolume": "gualaloom-state"' in SCRIPT
    assert '"containerPath": "/app/guala"' in SCRIPT
    assert 'efs.get("transitEncryption") != "ENABLED"' in SCRIPT
    assert 'for field in ("cpu", "memory")' in SCRIPT


def test_unknown_argument_fails_before_external_action() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--obsolete-path"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unknown argument" in result.stderr


def test_repeat_cutover_option_is_retired() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--repeat-cutover", "3"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unknown argument" in result.stderr


def test_rehearsal_only_rejects_retired_repeat_option() -> None:
    result = subprocess.run(
        [
            "bash",
            str(SCRIPT_PATH),
            "--rehearse-only",
            "--repeat-cutover",
            "2",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unknown argument" in result.stderr


def test_release_packages_preflight_and_binary_store_without_seal_transport(
) -> None:
    manifest = json.loads(
        (ROOT / "deploy" / "guala_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    categories = {
        category["name"]: category for category in manifest["categories"]
    }
    assert "migration_control" not in categories
    assert categories["build_control"]["files"] == [
        "deploy/guala_release_manifest.json",
        "dsf_ai_service/Dockerfile",
        "dsf_ai_service/buildspec.yml",
        "tools/deploy_dsf_ai.sh",
        "tools/package_guala_release.py",
        "tools/preflight_guala_production.py",
        "tools/run_guala_candidate_rehearsal_task.py",
    ]
    packaged = set().union(*(
        set(category["files"])
        for category in manifest["categories"]
    ))
    assert (
        "dsf_ai_service/substrate/native_organism_binary_store.py"
        in packaged
    )
    assert "tools/ecs_seal_transport.py" not in packaged
    assert (
        "dsf_ai_service/substrate/native_organism_binary_store.py"
        in manifest["runtime_entrypoints"]
    )
