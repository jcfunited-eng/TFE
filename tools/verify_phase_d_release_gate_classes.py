#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/workspaces/Tao_Financial_Engine")
WEB_ROOT = ROOT / "web"
MODULE_PATH = WEB_ROOT / "src" / "lib" / "release-gate-classes.ts"
TSC_PATH = ROOT / "web" / "node_modules" / ".bin" / "tsc"
BACKUP_DIR = ROOT / "backups" / "runtime"


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_cmd(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd or ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def require_tool(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"required tool missing: {path}")


def build_node_program(compiled_module_path: Path) -> str:
    module_path_json = json.dumps(str(compiled_module_path))
    return f"""
const mod = require({module_path_json});

const perClassResults = [
  {{ gate_id: "runtime_validation", gate_class: "runtime_critical", status: "fail", detail: "runtime validator failed" }},
  {{ gate_id: "publication_contract", gate_class: "publication_consistency", status: "fail", detail: "publication contract mismatch" }},
  {{ gate_id: "auxiliary_live_verifier", gate_class: "non_critical_observability", status: "fail", detail: "legacy verifier drift" }},
  {{ gate_id: "ui_parity", gate_class: "non_critical_product_parity", status: "fail", detail: "ui parity mismatch" }}
].map((row) => mod.classifyReleaseGateResult(row));

const blockingEvaluation = mod.evaluateDefaultHotfixLane([
  {{ gate_id: "runtime_validation", gate_class: "runtime_critical", status: "fail", detail: "runtime validator failed" }},
  {{ gate_id: "publication_contract", gate_class: "publication_consistency", status: "fail", detail: "publication contract mismatch" }}
]);

const recordOnlyEvaluation = mod.evaluateDefaultHotfixLane([
  {{ gate_id: "auxiliary_live_verifier", gate_class: "non_critical_observability", status: "fail", detail: "legacy verifier drift" }},
  {{ gate_id: "ui_parity", gate_class: "non_critical_product_parity", status: "fail", detail: "ui parity mismatch" }}
]);

const incompleteRecord = mod.validatePhaseDDeploymentRecord({{
  deployment_record_id: "deployment_record_v1_demo",
  generated_at_utc: "2026-03-16T05:00:00Z",
  environment: "production",
  release_lane: "hotfix",
  release_gate_class_results: perClassResults,
  blocking_gate_classes: mod.DEFAULT_BLOCKING_GATE_CLASSES.slice(),
  non_blocking_gate_classes: mod.DEFAULT_NON_BLOCKING_GATE_CLASSES.slice(),
  deployed_commit_sha: "",
  deployed_image_uri: "",
  deployed_image_tag: "",
  ecs_task_definition_arn: "",
  service_name: "tfe-web-service-lb",
  cluster_name: "tfe-web-cluster",
  deployment_started_at_utc: "2026-03-16T05:00:00Z",
  deployment_completed_at_utc: "2026-03-16T05:00:30Z",
  deployment_status: "blocked",
  evidence_artifact_paths: ["/tmp/demo.json"]
}});

const completeRecord = mod.validatePhaseDDeploymentRecord({{
  deployment_record_id: "deployment_record_v1_demo",
  generated_at_utc: "2026-03-16T05:00:00Z",
  environment: "production",
  release_lane: "hotfix",
  release_gate_class_results: perClassResults,
  blocking_gate_classes: mod.DEFAULT_BLOCKING_GATE_CLASSES.slice(),
  non_blocking_gate_classes: mod.DEFAULT_NON_BLOCKING_GATE_CLASSES.slice(),
  deployed_commit_sha: "310fb83c769c54b4de2a762f22d1e60819fe2e1f",
  deployed_image_uri: "418384447921.dkr.ecr.us-east-1.amazonaws.com/tfe-web:manual-20260316T041214Z",
  deployed_image_tag: "manual-20260316T041214Z",
  ecs_task_definition_arn: "arn:aws:ecs:us-east-1:418384447921:task-definition/tfe-web-task:235",
  service_name: "tfe-web-service-lb",
  cluster_name: "tfe-web-cluster",
  deployment_started_at_utc: "2026-03-16T05:00:00Z",
  deployment_completed_at_utc: "2026-03-16T05:00:30Z",
  deployment_status: "ok",
  evidence_artifact_paths: ["/tmp/demo.json"]
}});

console.log(JSON.stringify({{
  release_gate_classes: mod.RELEASE_GATE_CLASSES,
  default_blocking_gate_classes: mod.DEFAULT_BLOCKING_GATE_CLASSES,
  default_non_blocking_gate_classes: mod.DEFAULT_NON_BLOCKING_GATE_CLASSES,
  per_class_results: perClassResults,
  blocking_evaluation: blockingEvaluation,
  record_only_evaluation: recordOnlyEvaluation,
  phase_d_deployment_record_fields: mod.PHASE_D_DEPLOYMENT_RECORD_FIELDS,
  required_identity_fields: mod.REQUIRED_DEPLOYMENT_IDENTITY_FIELDS,
  incomplete_record_validation: incompleteRecord,
  complete_record_validation: completeRecord
}}, null, 2));
"""


def main() -> int:
    timestamp = utc_now_compact()
    artifact_path = BACKUP_DIR / f"phase-d-slice1-release-gate-classes-proof-{timestamp}.json"
    require_tool(TSC_PATH)

    with tempfile.TemporaryDirectory(prefix="phase-d-slice1-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        compile_dir = temp_dir / "compiled"
        compile_dir.mkdir(parents=True, exist_ok=True)

        compile_cmd = [
            str(TSC_PATH),
            "--pretty",
            "false",
            "--module",
            "commonjs",
            "--target",
            "ES2020",
            "--outDir",
            str(compile_dir),
            "src/lib/release-gate-classes.ts",
        ]
        compile_res = run_cmd(compile_cmd, cwd=WEB_ROOT)
        if compile_res.returncode != 0:
            raise RuntimeError(compile_res.stderr.strip() or compile_res.stdout.strip() or "tsc failed")

        compiled_candidates = list(compile_dir.rglob("release-gate-classes.js"))
        if len(compiled_candidates) != 1:
            raise RuntimeError(f"expected one compiled module, found {len(compiled_candidates)}")
        compiled_module_path = compiled_candidates[0]

        node_program = build_node_program(compiled_module_path)
        node_res = run_cmd(["node", "-e", node_program], cwd=ROOT)
        if node_res.returncode != 0:
            raise RuntimeError(node_res.stderr.strip() or node_res.stdout.strip() or "node verifier failed")

        result = json.loads(node_res.stdout)

        per_class = result["per_class_results"]
        blocking_eval = result["blocking_evaluation"]
        record_only_eval = result["record_only_evaluation"]
        incomplete_record = result["incomplete_record_validation"]
        complete_record = result["complete_record_validation"]

        assert len(per_class) == 4
        assert {row["gate_class"] for row in per_class} == {
            "runtime_critical",
            "publication_consistency",
            "non_critical_observability",
            "non_critical_product_parity",
        }
        assert result["default_blocking_gate_classes"] == [
            "runtime_critical",
            "publication_consistency",
        ]
        assert result["default_non_blocking_gate_classes"] == [
            "non_critical_observability",
            "non_critical_product_parity",
        ]
        assert blocking_eval["allowed_to_proceed"] is False
        assert [row["gate_class"] for row in blocking_eval["blocking_results"]] == [
            "runtime_critical",
            "publication_consistency",
        ]
        assert record_only_eval["allowed_to_proceed"] is True
        assert [row["gate_class"] for row in record_only_eval["recorded_non_blocking_results"]] == [
            "non_critical_observability",
            "non_critical_product_parity",
        ]
        assert incomplete_record["valid"] is False
        assert incomplete_record["missing_identity_fields"] == [
            "deployed_commit_sha",
            "deployed_image_uri",
            "deployed_image_tag",
            "ecs_task_definition_arn",
        ]
        assert complete_record["valid"] is True

        artifact = {
            "proof_generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "proof_status": "ok",
            "proof_scope": "phase_d_slice1_release_gate_classes_readonly_local",
            "contract_module_path": str(MODULE_PATH),
            "verifier_script_path": str(Path(__file__).resolve()),
            "release_gate_classes": result["release_gate_classes"],
            "default_blocking_gate_classes": result["default_blocking_gate_classes"],
            "default_non_blocking_gate_classes": result["default_non_blocking_gate_classes"],
            "per_class_results": per_class,
            "blocking_evaluation": blocking_eval,
            "record_only_evaluation": record_only_eval,
            "phase_d_deployment_record_fields": result["phase_d_deployment_record_fields"],
            "required_identity_fields": result["required_identity_fields"],
            "incomplete_record_validation": incomplete_record,
            "complete_record_validation": complete_record,
            "proof_harness_failure_family_status": "residual_process_debt",
            "requirements_proved": {
                "gate_result_can_be_classified_into_defined_release_gate_class": True,
                "runtime_critical_and_publication_consistency_block_by_default": True,
                "non_critical_observability_and_non_critical_product_parity_record_without_blocking_by_default": True,
                "deployment_record_requires_commit_sha_image_uri_image_tag_and_task_definition_arn": True,
            },
        }
        artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    print(str(artifact_path))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"phase_d_slice1_release_gate_classes_verifier_failed: {exc}", file=sys.stderr)
        raise
