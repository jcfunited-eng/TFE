#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/workspaces/Tao_Financial_Engine")
RUNTIME_DIR = ROOT / "backups" / "runtime"
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RUN_DIR = RUNTIME_DIR / f"phase-d-deployment-record-proof-{TS}"
RUN_DIR.mkdir(parents=True, exist_ok=True)
PROOF_ARTIFACT = RUNTIME_DIR / f"phase-d-deployment-record-proof-{TS}.json"
BLOCKER_ARTIFACT = RUNTIME_DIR / f"phase-d-deployment-record-proof-blocker-{TS}.json"

REQUIRED_FIELDS = [
    "deployment_record_id",
    "generated_at_utc",
    "environment",
    "release_lane",
    "release_gate_class_results",
    "blocking_gate_classes",
    "non_blocking_gate_classes",
    "deployed_commit_sha",
    "deployed_image_uri",
    "deployed_image_tag",
    "ecs_task_definition_arn",
    "service_name",
    "cluster_name",
    "deployment_started_at_utc",
    "deployment_completed_at_utc",
    "deployment_status",
    "evidence_artifact_paths",
]


def extract_image_tag(image_uri: str) -> str:
    image_name = str(image_uri or "").rsplit("/", 1)[-1]
    if ":" not in image_name:
        return ""
    return image_name.rsplit(":", 1)[-1].strip()


def run_shell() -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["TFE_DEPLOY_PROOF_ONLY"] = "1"
    return subprocess.run(
        ["bash", str(ROOT / "tools" / "deploy_to_prod_with_evidence.sh")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def parse_evidence_dir(stdout: str, stderr: str) -> Path | None:
    combined = "\n".join([stdout, stderr])
    match = re.search(r"(?:DEPLOY_GATE_PROOF_ONLY_EVIDENCE_DIR|DEPLOY_FAILED evidence_dir)=([^\s]+)", combined)
    if not match:
        return None
    return Path(match.group(1))


def fail(*, error: str, shell_proc: subprocess.CompletedProcess[str], evidence_dir: str | None, record_path: str | None) -> int:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "blocked",
        "proof_scope": "phase_d_deployment_record_proof_only",
        "error": error,
        "shell_return_code": shell_proc.returncode,
        "stdout_path": str(RUN_DIR / "deploy-shell.stdout.txt"),
        "stderr_path": str(RUN_DIR / "deploy-shell.stderr.txt"),
        "evidence_dir": evidence_dir,
        "deployment_record_path": record_path,
    }
    BLOCKER_ARTIFACT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(str(BLOCKER_ARTIFACT))
    return 1


def main() -> int:
    shell_proc = run_shell()
    stdout_path = RUN_DIR / "deploy-shell.stdout.txt"
    stderr_path = RUN_DIR / "deploy-shell.stderr.txt"
    stdout_path.write_text(shell_proc.stdout, encoding="utf-8")
    stderr_path.write_text(shell_proc.stderr, encoding="utf-8")

    evidence_dir = parse_evidence_dir(shell_proc.stdout, shell_proc.stderr)
    if evidence_dir is None:
        return fail(
            error="proof_only_shell_missing_evidence_dir",
            shell_proc=shell_proc,
            evidence_dir=None,
            record_path=None,
        )

    record_path = evidence_dir / "deployment-record.json"
    if shell_proc.returncode != 0:
        return fail(
            error=f"proof_only_shell_failed_rc_{shell_proc.returncode}",
            shell_proc=shell_proc,
            evidence_dir=str(evidence_dir),
            record_path=str(record_path),
        )
    if not record_path.exists():
        return fail(
            error="deployment_record_missing",
            shell_proc=shell_proc,
            evidence_dir=str(evidence_dir),
            record_path=str(record_path),
        )

    record = json.loads(record_path.read_text(encoding="utf-8"))
    summary_path = evidence_dir / "delta-contract-summary.json"
    service_pre_path = evidence_dir / "ecs-service-pre.json"
    taskdef_current_path = evidence_dir / "taskdef-current.json"
    proof_only_stop_path = evidence_dir / "proof-only-stop.json"
    validation_state_path = ROOT / "backups" / "runtime" / "deploy-validation-state.json"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    service_pre = json.loads(service_pre_path.read_text(encoding="utf-8"))
    taskdef_current = json.loads(taskdef_current_path.read_text(encoding="utf-8"))

    missing_fields: list[str] = []
    for field_name in REQUIRED_FIELDS:
        value = record.get(field_name)
        if isinstance(value, list):
            if len(value) == 0:
                missing_fields.append(field_name)
            continue
        if str(value or "").strip() == "":
            missing_fields.append(field_name)
    if missing_fields:
        return fail(
            error=f"deployment_record_missing_fields: {', '.join(missing_fields)}",
            shell_proc=shell_proc,
            evidence_dir=str(evidence_dir),
            record_path=str(record_path),
        )

    current_taskdef = str(((service_pre.get("services") or [{}])[0]).get("taskDefinition") or "").strip()
    current_image = str((((taskdef_current.get("taskDefinition") or {}).get("containerDefinitions") or [{}])[0]).get("image") or "").strip()
    current_commit = ""
    for item in (((taskdef_current.get("taskDefinition") or {}).get("containerDefinitions") or [{}])[0].get("environment") or []):
        if isinstance(item, dict) and item.get("name") == "TFE_GIT_COMMIT_SHA":
            current_commit = str(item.get("value") or "").strip()
            break

    expected_paths = {
        str(summary_path),
        str(validation_state_path),
        str(proof_only_stop_path),
        str(service_pre_path),
        str(taskdef_current_path),
    }
    actual_paths = {str(path) for path in record.get("evidence_artifact_paths") or []}

    errors: list[str] = []
    if record.get("deployment_status") != "proof_only_no_deploy":
        errors.append(f"unexpected_deployment_status={record.get('deployment_status')!r}")
    if record.get("environment") != "production":
        errors.append(f"unexpected_environment={record.get('environment')!r}")
    if record.get("service_name") != "tfe-web-service-lb":
        errors.append(f"unexpected_service_name={record.get('service_name')!r}")
    if record.get("cluster_name") != "tfe-web-cluster":
        errors.append(f"unexpected_cluster_name={record.get('cluster_name')!r}")
    if record.get("release_lane") != summary.get("release_lane"):
        errors.append("release_lane_mismatch")
    if record.get("release_gate_class_results") != summary.get("release_gate_class_results"):
        errors.append("release_gate_class_results_mismatch")
    if record.get("blocking_gate_classes") != summary.get("blocking_gate_classes"):
        errors.append("blocking_gate_classes_mismatch")
    if record.get("non_blocking_gate_classes") != summary.get("non_blocking_gate_classes"):
        errors.append("non_blocking_gate_classes_mismatch")
    if record.get("ecs_task_definition_arn") != current_taskdef:
        errors.append("ecs_task_definition_arn_mismatch")
    if record.get("deployed_image_uri") != current_image:
        errors.append("deployed_image_uri_mismatch")
    if record.get("deployed_image_tag") != extract_image_tag(current_image):
        errors.append("deployed_image_tag_mismatch")
    if record.get("deployed_commit_sha") != current_commit:
        errors.append("deployed_commit_sha_mismatch")
    if not expected_paths.issubset(actual_paths):
        errors.append("evidence_artifact_paths_incomplete")

    if errors:
        return fail(
            error="; ".join(errors),
            shell_proc=shell_proc,
            evidence_dir=str(evidence_dir),
            record_path=str(record_path),
        )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "proof_status": "ok",
        "proof_scope": "phase_d_deployment_record_proof_only",
        "shell_return_code": shell_proc.returncode,
        "evidence_dir": str(evidence_dir),
        "deployment_record_path": str(record_path),
        "record_excerpt": {
            "deployment_record_id": record["deployment_record_id"],
            "release_lane": record["release_lane"],
            "deployed_commit_sha": record["deployed_commit_sha"],
            "deployed_image_uri": record["deployed_image_uri"],
            "deployed_image_tag": record["deployed_image_tag"],
            "ecs_task_definition_arn": record["ecs_task_definition_arn"],
            "deployment_status": record["deployment_status"],
        },
        "requirements_proved": {
            "deployment_record_output_exists": True,
            "deployment_record_contains_required_contract_fields": True,
            "proof_only_mode_honestly_cites_current_deployed_identity_fields": True,
        },
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }
    PROOF_ARTIFACT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(str(PROOF_ARTIFACT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
