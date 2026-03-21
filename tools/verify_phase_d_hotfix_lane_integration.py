#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType


ROOT = Path("/workspaces/Tao_Financial_Engine")
MODULE_PATH = ROOT / "tools" / "validation_state_contract.py"
BACKUP_DIR = ROOT / "backups" / "runtime"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_cmd(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_module(module_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("phase_d_validation_state_contract", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_temp_repo(repo_dir: Path) -> None:
    write_text(repo_dir / "tools" / "deploy_to_prod_with_evidence.sh", "#!/usr/bin/env bash\nset -euo pipefail\n")
    write_text(repo_dir / "tools" / "validation_state_contract.py", "# placeholder\n")
    write_text(repo_dir / "web" / "src" / "app" / "screener" / "page.tsx", "export default function Page() { return null; }\n")
    write_text(repo_dir / "web" / "src" / "app" / "api" / "admin" / "refresh" / "route.ts", "export const dynamic = 'force-dynamic';\n")
    write_text(repo_dir / "tools" / "run_recommendation_quality_audit_lane.sh", "#!/usr/bin/env bash\necho quality\n")

    run_cmd(["git", "init"], cwd=repo_dir)
    run_cmd(["git", "config", "user.email", "phase-d@example.com"], cwd=repo_dir)
    run_cmd(["git", "config", "user.name", "Phase D Verifier"], cwd=repo_dir)
    add_res = run_cmd(["git", "add", "."], cwd=repo_dir)
    if add_res.returncode != 0:
        raise RuntimeError(add_res.stderr.strip() or add_res.stdout.strip() or "git add failed")
    commit_res = run_cmd(["git", "commit", "-m", "baseline"], cwd=repo_dir)
    if commit_res.returncode != 0:
        raise RuntimeError(commit_res.stderr.strip() or commit_res.stdout.strip() or "git commit failed")


def prepare_selection(module: ModuleType, repo_dir: Path, evidence_dir: Path, state_path: Path) -> dict:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    deploy_pattern_file = evidence_dir / "deploy-patterns.txt"
    deploy_pattern_file.write_text("", encoding="utf-8")
    head = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_dir)
    if head.returncode != 0:
        raise RuntimeError(head.stderr.strip() or head.stdout.strip() or "git rev-parse failed")
    head_rev = head.stdout.strip()
    args = argparse.Namespace(
        repo_root=str(repo_dir),
        state_path=str(state_path),
        evidence_dir=str(evidence_dir),
        deploy_pattern_file=str(deploy_pattern_file),
        base_rev=head_rev,
        head_rev=head_rev,
    )
    result = module.prepare(args)
    if result != 0:
        raise RuntimeError(f"prepare returned {result}")
    selection_path = evidence_dir / "delta-unit-selection.json"
    return json.loads(selection_path.read_text(encoding="utf-8"))


def write_block_artifacts(selection: dict, block_dir: Path, failing_unit_id: str) -> None:
    block_dir.mkdir(parents=True, exist_ok=True)
    for unit in selection.get("units", []):
        if not bool(unit.get("selected")):
            continue
        unit_id = str(unit.get("unit_id") or "")
        status = "fail" if unit_id == failing_unit_id else "pass"
        payload = {
            "unit_id": unit_id,
            "status": status,
            "selected": True,
            "release_lane": str(unit.get("release_lane") or "hotfix"),
            "gate_class": str(unit.get("gate_class") or ""),
            "blocking_by_default": bool(unit.get("blocking_by_default")),
            "hotfix_lane_default_action": str(unit.get("hotfix_lane_default_action") or ""),
            "base_blocking": bool(unit.get("base_blocking")),
            "blocking": bool(unit.get("blocking")),
            "blocking_reason": str(unit.get("blocking_reason") or ""),
            "skip_reason": None,
            "failure_code": f"{unit_id}_failed" if status == "fail" else None,
            "failure_message": f"{unit_id} failed" if status == "fail" else "",
            "state_update_inputs": list(unit.get("changed_inputs") or []),
            "inputs": {
                "changed_inputs": list(unit.get("changed_inputs") or []),
            },
            "recorded_at_utc": utc_now(),
        }
        (block_dir / f"{unit_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def finalize_selection(module: ModuleType, evidence_dir: Path, state_path: Path, selection_path: Path, block_dir: Path) -> dict:
    args = argparse.Namespace(
        state_path=str(state_path),
        evidence_dir=str(evidence_dir),
        selection_json=str(selection_path),
        block_artifact_dir=str(block_dir),
    )
    result = module.finalize(args)
    if result != 0:
        raise RuntimeError(f"finalize returned {result}")
    summary_path = evidence_dir / "delta-contract-summary.json"
    return json.loads(summary_path.read_text(encoding="utf-8"))


def run_scenario(module: ModuleType, *, scenario_name: str, changed_file: str, change_text: str, expected_unit: str) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"phase-d-{scenario_name}-") as temp_dir_raw:
        repo_dir = Path(temp_dir_raw) / "repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        build_temp_repo(repo_dir)

        target_path = repo_dir / changed_file
        target_path.write_text(target_path.read_text(encoding="utf-8") + change_text, encoding="utf-8")

        evidence_dir = Path(temp_dir_raw) / "evidence"
        state_path = Path(temp_dir_raw) / "validation-state.json"
        selection = prepare_selection(module, repo_dir, evidence_dir, state_path)
        selection_path = evidence_dir / "delta-unit-selection.json"

        unit_payload = next(
            unit for unit in selection.get("units", [])
            if str(unit.get("unit_id") or "") == expected_unit
        )

        block_dir = Path(temp_dir_raw) / "blocks"
        write_block_artifacts(selection, block_dir, expected_unit)
        summary = finalize_selection(module, evidence_dir, state_path, selection_path, block_dir)

        return {
            "selection": selection,
            "unit_payload": unit_payload,
            "summary": summary,
        }


def main() -> int:
    module = load_module(MODULE_PATH)
    timestamp = utc_now_compact()
    artifact_path = BACKUP_DIR / f"phase-d-hotfix-lane-integration-proof-{timestamp}.json"

    product_parity = run_scenario(
        module,
        scenario_name="product-parity",
        changed_file="web/src/app/screener/page.tsx",
        change_text="// product parity delta\n",
        expected_unit="site_reliability_screener",
    )
    observability = run_scenario(
        module,
        scenario_name="observability",
        changed_file="tools/run_recommendation_quality_audit_lane.sh",
        change_text="# observability delta\n",
        expected_unit="site_reliability_recommendations_quality",
    )
    runtime_critical = run_scenario(
        module,
        scenario_name="runtime-critical",
        changed_file="web/src/app/api/admin/refresh/route.ts",
        change_text="// runtime critical delta\n",
        expected_unit="runtime_validation",
    )

    product_unit = product_parity["unit_payload"]
    observability_unit = observability["unit_payload"]
    runtime_unit = runtime_critical["unit_payload"]

    assert product_unit["gate_class"] == "non_critical_product_parity"
    assert product_unit["blocking"] is False
    assert product_unit["hotfix_lane_default_action"] == "record_only"
    assert product_parity["summary"]["exact_blocker"] is None
    assert "site_reliability_screener" in product_parity["summary"]["changed_selected_nonblocking_units"]

    assert observability_unit["gate_class"] == "non_critical_observability"
    assert observability_unit["blocking"] is False
    assert observability_unit["hotfix_lane_default_action"] == "record_only"
    assert observability["summary"]["exact_blocker"] is None
    assert "site_reliability_recommendations_quality" in observability["summary"]["changed_selected_nonblocking_units"]

    assert runtime_unit["gate_class"] == "runtime_critical"
    assert runtime_unit["blocking"] is True
    assert runtime_unit["hotfix_lane_default_action"] == "block"
    assert runtime_critical["summary"]["exact_blocker"]["unit_id"] == "runtime_validation"
    assert "runtime_validation" in runtime_critical["summary"]["changed_selected_blocking_units"]

    for scenario in (product_parity, observability, runtime_critical):
        assert scenario["summary"]["release_lane"] == "hotfix"
        assert scenario["summary"]["blocking_gate_classes"] == [
            "runtime_critical",
            "publication_consistency",
        ]
        assert scenario["summary"]["non_blocking_gate_classes"] == [
            "non_critical_observability",
            "non_critical_product_parity",
        ]
        assert any(
            row["unit_id"] == scenario["unit_payload"]["unit_id"] and row["gate_class"] == scenario["unit_payload"]["gate_class"]
            for row in scenario["summary"]["release_gate_class_results"]
        )

    artifact = {
        "proof_generated_at_utc": utc_now(),
        "proof_status": "ok",
        "proof_scope": "phase_d_hotfix_lane_integration_local",
        "validation_contract_path": str(MODULE_PATH),
        "verifier_script_path": str(Path(__file__).resolve()),
        "scenarios": {
            "non_critical_product_parity": {
                "unit_id": product_unit["unit_id"],
                "gate_class": product_unit["gate_class"],
                "blocking": product_unit["blocking"],
                "summary": product_parity["summary"],
            },
            "non_critical_observability": {
                "unit_id": observability_unit["unit_id"],
                "gate_class": observability_unit["gate_class"],
                "blocking": observability_unit["blocking"],
                "summary": observability["summary"],
            },
            "runtime_critical": {
                "unit_id": runtime_unit["unit_id"],
                "gate_class": runtime_unit["gate_class"],
                "blocking": runtime_unit["blocking"],
                "summary": runtime_critical["summary"],
            },
        },
        "requirements_proved": {
            "changed_non_critical_product_parity_failures_record_without_blocking_default_hotfix_lane": True,
            "changed_non_critical_observability_failures_record_without_blocking_default_hotfix_lane": True,
            "changed_runtime_critical_failures_block_default_hotfix_lane": True,
            "delta_contract_summary_emits_release_lane_and_gate_class_results": True,
        },
    }
    artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(str(artifact_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
