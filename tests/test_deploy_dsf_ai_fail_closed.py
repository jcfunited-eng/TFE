"""Guardrails for the production deployment handoff.

The tests inspect the deploy program without invoking AWS.  The task-authority
classifier itself is also executed against synthetic ECS observations so its
decisions are proven without mutating production.
"""

import json
import os
from pathlib import Path
import subprocess


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "deploy_dsf_ai.sh"
LEGACY_SEALER = (
    Path(__file__).resolve().parents[1] / "tools" / "seal_legacy_guala_state.py"
)
TEXT = SCRIPT.read_text()


def _between(start, end):
    assert start in TEXT, start
    assert end in TEXT, end
    return TEXT.split(start, 1)[1].split(end, 1)[0]


def test_release_must_be_a_clean_commit_and_one_archive():
    preflight = _between("[0/6] Preflight checks", "── Step 1: Package source")
    package = _between("── Step 1: Package source", "── Step 2: Upload")
    static = _between("Syncing static files to S3", "create-invalidation")

    assert "git status --porcelain=v1 --untracked-files=all" in preflight
    assert "working tree is dirty or has untracked files" in preflight
    assert "exit 1" in preflight
    assert 'git archive "${GIT_SHA}"' in package
    assert "git archive HEAD" not in package
    assert '"${STAGING}/dsf_ai_service/static/"' in static
    assert "aws s3 sync dsf_ai_service/static/" not in static


def test_efs_transport_and_fargate_shutdown_ceiling_are_explicit():
    assert "'transitEncryption': 'ENABLED'" in TEXT
    assert "'transitEncryption': 'DISABLED'" not in TEXT
    assert "'cpu': '4096'" in TEXT
    assert "'memory': '16384'" in TEXT
    assert "'cpu', 'memory'" not in TEXT.split("keep =", 1)[1].split("\n", 1)[0]
    # AWS Fargate rejects values above 120; persistence must already be SEALED.
    assert "'stopTimeout': 120" in TEXT
    assert "shutdown save-free" in TEXT


def test_ecs_health_check_is_liveness_not_deep_readiness():
    """Quiescence intentionally makes deep readiness false during sealing."""
    health_check = _between("'healthCheck': {", "'stopTimeout': 120")
    assert "http://localhost:8080/health" in health_check
    assert "http://localhost:8080/ready" not in health_check


def test_service_configuration_forbids_owner_overlap_and_arms_rollback():
    assert (
        'DEPLOY_CONFIG="maximumPercent=100,minimumHealthyPercent=0,'
        'deploymentCircuitBreaker={enable=true,rollback=true}"'
    ) in TEXT
    assert TEXT.count('--deployment-configuration "${DEPLOY_CONFIG}"') >= 2
    final_check = _between("FINAL_SERVICE_JSON=", "── Step 8")
    assert 'config.get("maximumPercent") != 100' in final_check
    assert 'config.get("minimumHealthyPercent") != 0' in final_check
    assert 'breaker.get("rollback") is not True' in final_check


def test_runtime_credentials_are_secret_references_not_plain_environment():
    environment = _between("'environment': [", "] + ([{'name': 'FORCE_S3_RESTORE'")
    secret_block = _between("'secrets': [", "'mountPoints': [")
    names = (
        "GUALALOOM_API_KEY",
        "TAVILY_API_KEY",
        "ANTHROPIC_API_KEY",
        # 0238cc3 (Change 4 feeds): optional YouTube feed key — allowed
        # ONLY as a Secrets Manager reference, injected only when the
        # secret exists (the two conditional-shape assertions below).
        # The previous rows forbidding YOUTUBE entirely predate Change 4.
        "YOUTUBE_API_KEY",
    )
    for name in names:
        assert f"'name': '{name}'" not in environment
        assert f"'name': '{name}'" in secret_block
    assert secret_block.count("'valueFrom':") == len(names)
    # YouTube stays conditional and reference-only: never a plaintext value,
    # never unconditionally required.
    assert "'valueFrom': os.environ['YOUTUBE_SECRET_ARN']" in secret_block
    assert "if os.environ.get('YOUTUBE_SECRET_ARN') else []" in secret_block
    assert "_envval" not in TEXT
    assert "simulate-principal-policy" in TEXT
    assert "required Secrets Manager secret is absent" in TEXT
    assert "OPENAI_API_KEY" not in TEXT
    assert "OPENAI_SECRET" not in TEXT
    assert "LOOKUP_AUTONOMOUS" not in TEXT


def test_control_plane_uses_verified_tls_credential_and_nonce():
    seal = _between("Requesting authenticated sealed-generation handoff", "Scaling service to zero")
    ready = _between("Waiting for authenticated deep generation/build proof", "Deep readiness verified")

    assert 'CONTROL_ORIGIN="https://dsf-ai.com"' in TEXT
    assert '--connect-to "dsf-ai.com:443:${ALB_DNS}:443"' in TEXT
    assert "http://dsf-ai-alb" not in TEXT
    for block in (seal, ready):
        assert 'X-API-Key: ${DEPLOY_API_KEY}' in block
        assert 'X-Deploy-Nonce: ${DEPLOY_NONCE}' in block
    assert 'value.get("deploy_nonce") != os.environ["DEPLOY_NONCE"]' in seal
    assert 'value.get("state") != "SEALED"' in seal
    assert "manifest_sha256" in seal
    assert "generation" in seal


def test_old_owner_is_proven_stopped_before_new_owner_can_start():
    turnover = TEXT.index("Scaling service to zero before any new owner may start")
    zero = TEXT.index("--desired-count 0", turnover)
    stopped_wait = TEXT.index("aws ecs wait tasks-stopped", turnover)
    stopped_exact = TEXT.index('if [ "${OLD_STATUS}" != "STOPPED" ]', turnover)
    no_remaining = TEXT.index('if [ "${REMAINING_TASKS}" != "0" ]', turnover)
    # The success-path new-owner start is the first desired-count 1 AFTER the
    # turnover marker (the EXIT trap's fail-back, which appears earlier in the
    # file, restores the ORIGINAL owner and only after zero owners is proven —
    # asserted separately below).
    one = TEXT.index("--desired-count 1", turnover)
    assert zero < stopped_wait < stopped_exact < no_remaining < one
    assert "Old owner STOPPED; new owner start is now permitted" in TEXT


def test_new_scheduling_authority_settles_at_zero_and_rejects_stale_tasks():
    """The zero-to-one transition cannot resurrect an older ECS deployment."""
    turnover = TEXT.index("Old owner STOPPED; new owner start is now permitted")
    install = TEXT.index("Installing the new scheduling authority at zero owners", turnover)
    target_zero = TEXT.index(
        '--desired-count 0 --task-definition "${NEW_TASK_DEFINITION_ARN}"',
        install,
    )
    zero_proof = TEXT.index(
        "New scheduling authority proven while state ownership remains zero",
        target_zero,
    )
    start = TEXT.index("[7/7] Starting exactly one new owner", zero_proof)
    desired_one = TEXT.index("--desired-count 1", start)
    assert turnover < install < target_zero < zero_proof < start < desired_one

    authority = _between(
        "Waiting for exactly one running task with the new immutable build",
        "Waiting for authenticated deep generation/build proof",
    )
    assert '--family "${TASK_FAMILY}" --desired-status RUNNING' in authority
    assert 'task.get("taskDefinitionArn") != os.environ["NEW_TASK_DEFINITION_ARN"]' in authority
    assert 'print("reject:wrong-task-definition")' in authority
    assert 'print("reject:wrong-image-digest")' in authority
    assert "aws ecs stop-task" in authority
    assert "aws ecs wait tasks-stopped" in authority
    assert authority.index('print("reject:wrong-task-definition")') < authority.index(
        "aws ecs stop-task"
    )


def test_task_authority_classifier_decisions_are_exact():
    authority = _between(
        "CANDIDATE_AUTHORITY=$(",
        "\n        case \"${CANDIDATE_AUTHORITY}\"",
    )
    source = authority.split("python3 -c '\n", 1)[1].rsplit("\n')", 1)[0]
    expected_definition = (
        "arn:aws:ecs:us-east-1:418384447921:"
        "task-definition/dsf-ai-task:739"
    )
    expected_digest = "sha256:" + ("a" * 64)
    task_arn = "arn:aws:ecs:us-east-1:418384447921:task/cluster/target"

    def decide(*, definition=expected_definition, digest=expected_digest, service=True):
        task = {
            "taskArn": task_arn,
            "taskDefinitionArn": definition,
            "lastStatus": "RUNNING",
            "containers": [{"imageDigest": digest}],
        }
        env = os.environ.copy()
        env.update(
            {
                "CANDIDATE_TASK_JSON": json.dumps(task),
                "CANDIDATE_TASK_ARN": task_arn,
                "SERVICE_TASKS_TEXT": task_arn if service else "None",
                "NEW_TASK_DEFINITION_ARN": expected_definition,
                "EXPECTED_IMAGE_DIGEST": expected_digest,
            }
        )
        return subprocess.run(
            ["python3", "-c", source],
            check=True,
            capture_output=True,
            env=env,
            text=True,
        ).stdout.strip()

    assert decide() == "match"
    assert decide(definition=expected_definition.replace(":739", ":738")) == (
        "reject:wrong-task-definition"
    )
    assert decide(digest="sha256:" + ("b" * 64)) == "reject:wrong-image-digest"
    assert decide(service=False) == "reject:not-service-owned"
    assert decide(digest=None) == "wait"


def test_failed_turnover_fails_back_to_the_original_owner():
    """GL-RPT-RAM-FIXES-DEPLOYED-AND-SEAL-DEFECTS defect 5: a failed handoff
    must not strand production at zero owners; after the zero-owner proof the
    trap restores exactly one task on the ORIGINAL task definition."""
    trap = TEXT.index("deployment_exit_cleanup()")
    cleanup_call = TEXT.index("fail_closed_owner_cleanup", trap)
    fail_back = TEXT.index("[fail-back] Restoring the original owner", trap)
    restore = TEXT.index('--task-definition "${OLD_TASK_DEFINITION_ARN}"', trap)
    restore_one = TEXT.index("--desired-count 1", trap)
    trap_end = TEXT.index("trap deployment_exit_cleanup EXIT")
    assert trap < cleanup_call < fail_back < restore < trap_end
    assert trap < restore_one < trap_end
    assert "production is DOWN and needs manual desired-count=1" in TEXT


def test_transitional_owner_requires_live_seal_capability_before_mutation():
    capability = TEXT.index("LEGACY_OPENAPI=")
    security_group_mutation = TEXT.index("aws ec2 revoke-security-group-ingress")
    package = TEXT.index("── Step 1: Package source")
    handoff = TEXT.index("Requesting authenticated sealed-generation handoff")
    owner_stop = TEXT.index("Scaling service to zero")

    assert capability < security_group_mutation < package < handoff < owner_stop
    assert 'paths.get("/sleep_for_deploy", {})' in TEXT
    assert "live owner has no authenticated generation-seal endpoint" in TEXT
    assert "Production remains online and untouched" in TEXT
    assert 'if [ "${OLD_SEALED_BOOT}" != "1" ]' in TEXT


def test_efs_backup_policy_remains_a_hard_gate_for_sealed_generations():
    assert "aws efs put-backup-policy" in TEXT
    assert 'if [ "${EFS_BACKUP_POLICY}" != "ENABLED" ]' in TEXT
    assert TEXT.index("aws efs put-backup-policy") < TEXT.index(
        "if ! SLEEP_RESPONSE=")


def test_exit_cleanup_is_composite_and_proves_zero_owners():
    assert TEXT.count("trap deployment_exit_cleanup EXIT") == 1
    assert "trap cleanup_staging EXIT" not in TEXT
    assert "trap fail_closed_owner_cleanup EXIT" not in TEXT
    cleanup = _between("fail_closed_owner_cleanup()", "deployment_exit_cleanup()")
    exit_cleanup = _between("deployment_exit_cleanup()", "trap deployment_exit_cleanup EXIT")

    assert '--service "${ECS_SERVICE}" --desired-count 0' in cleanup
    assert '"desiredCount": 0, "runningCount": 0, "pendingCount": 0' in cleanup
    assert '--family "${TASK_FAMILY}" --desired-status RUNNING' in cleanup
    assert "aws ecs wait services-stable" not in cleanup
    assert cleanup.index("--desired-count 0") < cleanup.index(
        '--family "${TASK_FAMILY}" --desired-status RUNNING'
    )
    assert cleanup.index(
        '--family "${TASK_FAMILY}" --desired-status RUNNING'
    ) < cleanup.index("aws ecs stop-task")
    assert 'if [ "${FAMILY_REMAINING}" != "0" ]' in cleanup
    assert 'if ! rm -rf "${DEPLOY_WORK_DIR}"' in exit_cleanup
    assert 'if ! fail_closed_owner_cleanup' in exit_cleanup
    assert "set +e" not in cleanup


def test_legacy_migration_and_resume_mechanisms_are_absent():
    forbidden = (
        "seal_legacy_guala_state",
        "guala_legacy_migration_receipt",
        "MIGRATION_TASK_ARN",
        "BOOTSTRAP_MIGRATION",
        "--resume-bootstrap",
        "RESUME_BOOTSTRAP",
        "bootstrap-intent",
        "bootstrap-resume",
        "aws backup start-backup-job",
    )
    for token in forbidden:
        assert token not in TEXT
    assert not LEGACY_SEALER.exists()


def test_original_owner_is_reproven_immediately_before_handoff():
    reproving = _between(
        "Image construction can take long enough",
        'echo "[turnover] Original sole owner re-proven immediately before handoff."',
    )
    sleep = TEXT.index("if ! SLEEP_RESPONSE=")
    proof = TEXT.index("Original sole owner re-proven immediately before handoff")
    final_proof = TEXT.index(
        "Original sole owner re-proven directly before the seal request"
    )

    assert proof < final_proof < sleep
    assert 'service_tasks != [old_arn] or family_tasks != [old_arn]' in reproving
    assert '"desiredCount": 1, "runningCount": 1, "pendingCount": 0' in reproving
    assert 'task.get("taskDefinitionArn")' in reproving
    assert 'containers[0].get("imageDigest")' in reproving
    assert "FINAL_OLD_FAMILY_TASKS" in TEXT
    assert "service ownership counts changed immediately before handoff" in TEXT
    assert TEXT.index("OWNER_FAIL_CLOSED=1") < sleep
def test_new_task_and_deep_readiness_are_exact_before_wake():
    task_check = _between("NEW_TASK_JSON=", "Waiting for authenticated deep generation/build proof")
    ready = _between("Waiting for authenticated deep generation/build proof", "Deep readiness verified")
    wake = TEXT.index('echo "[wake] Deep readiness verified')

    assert 'containers[0].get("imageDigest")' in task_check
    assert "taskDefinitionArn" in task_check
    for field in (
        'value.get("ready") is True',
        'value.get("owner") is True',
        'value.get("git_sha")',
        'value.get("generation")',
        'value.get("identity")',
        'value.get("manifest_sha256")',
        'value.get("task_definition")',
        'value.get("image_digest")',
    ):
        assert field in ready
    assert TEXT.index("Waiting for authenticated deep generation/build proof") < wake
    assert 'if [ "${READINESS_VERIFIED}" != "1" ]' in ready
    new_owner = _between(
        "Waiting for exactly one running task with the new immutable build",
        "Waiting for authenticated deep generation/build proof",
    )
    assert 'task.get("lastStatus") != "RUNNING"' in new_owner
    assert 'containers[0].get("imageDigest")' in new_owner
    assert 'if [ "${ROLLOUT_STATE}" = "FAILED" ]' in new_owner
    assert "aws ecs wait services-stable" not in new_owner
    post_ready = _between(
        'if [ "${READINESS_VERIFIED}" != "1" ]',
        'echo "[wake] Deep readiness verified',
    )
    assert "aws ecs wait services-stable" in post_ready


def test_task_security_group_removes_direct_internet_ingress_and_verifies_alb_only():
    preflight = _between("Remove direct internet access", "echo \"  Git SHA")
    assert 'TASK_SECURITY_GROUP="sg-057566437ba8d4b48"' in TEXT
    assert 'ALB_SECURITY_GROUP="sg-0c9ff138eba21a6fa"' in TEXT
    assert "aws ec2 revoke-security-group-ingress" in preflight
    assert "--cidr 0.0.0.0/0" in preflight
    assert "task port 8080 still has CIDR ingress" in preflight
    assert "task port 8080 is not restricted to the ALB security group" in preflight


def test_image_digest_service_wait_wake_and_static_invalidation_fail_closed():
    assert 're.fullmatch(r"sha256:[0-9a-f]{64}"' in TEXT
    assert "EXPECTED_IMAGE_DIGEST" in TEXT
    assert "aws ecs wait services-stable" in TEXT
    assert "circuit-breaker rollback is authoritative" in TEXT
    assert 'if [ "${AWAKE_VERIFIED}" != "1" ]' in TEXT
    assert "|| true" not in TEXT
    invalidation = _between("aws cloudfront wait invalidation-completed", "── Summary")
    assert "exit 1" in invalidation
    assert "WARNING" not in invalidation
