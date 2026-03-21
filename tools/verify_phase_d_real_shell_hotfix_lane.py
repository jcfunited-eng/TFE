#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


ROOT = Path("/workspaces/Tao_Financial_Engine")
RUNTIME_DIR = ROOT / "backups" / "runtime"
STATE_PATH = RUNTIME_DIR / "deploy-validation-state.json"
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
PROOF_ARTIFACT = RUNTIME_DIR / f"phase-d-real-shell-hotfix-lane-proof-{TS}.json"
BLOCKER_ARTIFACT = RUNTIME_DIR / f"phase-d-real-shell-hotfix-lane-proof-blocker-{TS}.json"
RUN_DIR = RUNTIME_DIR / f"phase-d-real-shell-hotfix-lane-proof-{TS}"
RUN_DIR.mkdir(parents=True, exist_ok=True)
ORIGINAL_HEAD = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
ORIGINAL_STATE = STATE_PATH.read_text(encoding="utf-8") if STATE_PATH.exists() else None


def run_cmd(args: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=str(ROOT), text=True, capture_output=True, env=env, check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed rc={proc.returncode}: {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def restore_state_file() -> None:
    if ORIGINAL_STATE is None:
        if STATE_PATH.exists():
            STATE_PATH.unlink()
    else:
        STATE_PATH.write_text(ORIGINAL_STATE, encoding="utf-8")


def restore_head() -> None:
    run_cmd(["git", "-C", str(ROOT), "checkout", "--quiet", ORIGINAL_HEAD], check=True)


def insert_js_guard(text: str, env_name: str, message: str) -> str:
    lines = text.splitlines(keepends=True)
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    while insert_at < len(lines):
        stripped = lines[insert_at].strip()
        if stripped.startswith("import "):
            insert_at += 1
            continue
        if stripped == "":
            insert_at += 1
            continue
        break
    injection = (
        f"if (process.env.{env_name} === '1') {{\n"
        f"  console.error('{message}');\n"
        f"  process.exit(1);\n"
        f"}}\n\n"
    )
    return "".join(lines[:insert_at] + [injection] + lines[insert_at:])


def insert_python_guard(text: str, env_name: str, message: str) -> str:
    lines = text.splitlines(keepends=True)
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    while insert_at < len(lines):
        stripped = lines[insert_at].strip()
        if stripped.startswith("from __future__") or stripped.startswith("import ") or stripped.startswith("from "):
            insert_at += 1
            continue
        if stripped == "":
            insert_at += 1
            continue
        break
    injection = (
        f"if os.environ.get('{env_name}') == '1':\n"
        f"    raise SystemExit('{message}')\n\n"
    )
    return "".join(lines[:insert_at] + [injection] + lines[insert_at:])


def write_full_text(path: Path, new_text: str) -> None:
    path.write_text(new_text, encoding="utf-8")


def find_gate_class_result(summary: dict, unit_id: str) -> dict | None:
    rows = summary.get("release_gate_class_results")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("unit_id") == unit_id:
            return row
    return None


def parse_evidence_dir(stdout: str, stderr: str) -> Path | None:
    combined = "\n".join([stdout, stderr])
    match = re.search(r"(?:DEPLOY_GATE_PROOF_ONLY_EVIDENCE_DIR|DEPLOY_FAILED evidence_dir)=([^\s]+)", combined)
    if not match:
        return None
    return Path(match.group(1))


def run_shell_for_scenario(
    *,
    name: str,
    env_name: str,
    file_rel: str,
    expected_unit: str,
    expected_gate_class: str,
    expect_exact_blocker: bool,
    expected_failure_code: str | None,
    local_runtime_validation: bool,
    make_text: Callable[[str], str],
) -> dict:
    scenario_dir = RUN_DIR / name
    scenario_dir.mkdir(parents=True, exist_ok=True)
    restore_state_file()
    restore_head()

    target = ROOT / file_rel
    original = target.read_text(encoding="utf-8")
    modified = make_text(original)
    write_full_text(target, modified)

    run_cmd(["git", "-C", str(ROOT), "add", "--", file_rel])
    run_cmd(["git", "-C", str(ROOT), "commit", "-m", f"Phase D shell proof scenario: {name}", "--", file_rel])
    scenario_head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()

    env = os.environ.copy()
    env["TFE_DEPLOY_PROOF_ONLY"] = "1"
    env[env_name] = "1"
    if local_runtime_validation:
        env["TFE_DEPLOY_VALIDATION_MODE"] = "local"

    shell_proc = subprocess.run(
        ["bash", str(ROOT / "tools" / "deploy_to_prod_with_evidence.sh")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    stdout_path = scenario_dir / "deploy-shell.stdout.txt"
    stderr_path = scenario_dir / "deploy-shell.stderr.txt"
    stdout_path.write_text(shell_proc.stdout, encoding="utf-8")
    stderr_path.write_text(shell_proc.stderr, encoding="utf-8")

    evidence_dir = parse_evidence_dir(shell_proc.stdout, shell_proc.stderr)
    if evidence_dir is None:
        raise RuntimeError(f"evidence_dir_missing_for_{name}")

    summary_path = evidence_dir / "delta-contract-summary.json"
    if not summary_path.exists():
        raise RuntimeError(f"summary_missing_for_{name}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    unit_path = evidence_dir / "validation-blocks" / f"{expected_unit}.json"
    if not unit_path.exists():
        raise RuntimeError(f"unit_artifact_missing_for_{name}: {expected_unit}")
    unit_payload = json.loads(unit_path.read_text(encoding="utf-8"))

    proof_only_stop_path = evidence_dir / "proof-only-stop.json"
    exact_blocker = summary.get("exact_blocker") if isinstance(summary, dict) else None
    release_lane = summary.get("release_lane") if isinstance(summary, dict) else None
    blocking_gate_classes = summary.get("blocking_gate_classes") if isinstance(summary, dict) else None
    non_blocking_gate_classes = summary.get("non_blocking_gate_classes") if isinstance(summary, dict) else None
    release_gate_class_results = summary.get("release_gate_class_results") if isinstance(summary, dict) else None
    class_result = find_gate_class_result(summary, expected_unit)

    if release_lane != "hotfix":
        raise RuntimeError(f"release_lane_not_hotfix_for_{name}: {release_lane!r}")
    if not isinstance(blocking_gate_classes, list) or not isinstance(non_blocking_gate_classes, list):
        raise RuntimeError(f"gate_class_lists_missing_for_{name}")
    if not isinstance(release_gate_class_results, list):
        raise RuntimeError(f"release_gate_class_results_missing_for_{name}")
    if not isinstance(class_result, dict):
        raise RuntimeError(f"release_gate_class_result_missing_for_{name}: {expected_unit}")
    if class_result.get("gate_class") != expected_gate_class:
        raise RuntimeError(f"unexpected_gate_class_for_{name}: {class_result.get('gate_class')!r}")
    if unit_payload.get("status") != "fail":
        raise RuntimeError(f"expected_fail_status_for_{name}: {unit_payload.get('status')!r}")
    if expected_failure_code and unit_payload.get("failure_code") != expected_failure_code:
        raise RuntimeError(f"unexpected_failure_code_for_{name}: {unit_payload.get('failure_code')!r}")

    if expect_exact_blocker:
        if not isinstance(exact_blocker, dict) or exact_blocker.get("unit_id") != expected_unit:
            raise RuntimeError(f"exact_blocker_mismatch_for_{name}: {exact_blocker!r}")
        if shell_proc.returncode == 0:
            raise RuntimeError(f"expected_nonzero_shell_rc_for_{name}")
    else:
        if exact_blocker is not None:
            raise RuntimeError(f"unexpected_exact_blocker_for_{name}: {exact_blocker!r}")
        if shell_proc.returncode != 0:
            raise RuntimeError(f"unexpected_nonzero_shell_rc_for_{name}: {shell_proc.returncode}")
        if not proof_only_stop_path.exists():
            raise RuntimeError(f"proof_only_stop_missing_for_{name}")

    return {
        "scenario": name,
        "scenario_commit_sha": scenario_head,
        "target_file": str(target),
        "expected_unit_id": expected_unit,
        "expected_gate_class": expected_gate_class,
        "shell_return_code": shell_proc.returncode,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "evidence_dir": str(evidence_dir),
        "delta_contract_summary_path": str(summary_path),
        "proof_only_stop_path": str(proof_only_stop_path) if proof_only_stop_path.exists() else None,
        "unit_artifact_path": str(unit_path),
        "release_lane": release_lane,
        "blocking_gate_classes": blocking_gate_classes,
        "non_blocking_gate_classes": non_blocking_gate_classes,
        "release_gate_class_result": class_result,
        "release_gate_class_results": release_gate_class_results,
        "exact_blocker": exact_blocker,
        "unit_artifact": {
            "status": unit_payload.get("status"),
            "failure_code": unit_payload.get("failure_code"),
            "failure_message": unit_payload.get("failure_message"),
            "blocking": unit_payload.get("blocking"),
            "details": unit_payload.get("details"),
        },
    }


def main() -> int:
    results: list[dict] = []
    blocker_payload: dict | None = None

    try:
        scenarios = [
            {
                "name": "non_critical_product_parity",
                "env_name": "TFE_PHASE_D_FORCE_SCREENER_PARITY_FAIL",
                "file_rel": "web/scripts/screener_ui_parity_probe.mjs",
                "expected_unit": "site_reliability_screener",
                "expected_gate_class": "non_critical_product_parity",
                "expect_exact_blocker": False,
                "expected_failure_code": "screener_lane_failed",
                "local_runtime_validation": False,
                "make_text": lambda text: insert_js_guard(
                    text,
                    "TFE_PHASE_D_FORCE_SCREENER_PARITY_FAIL",
                    "phase_d_forced_screener_parity_failure",
                ),
            },
            {
                "name": "non_critical_observability",
                "env_name": "TFE_PHASE_D_FORCE_RECO_QUALITY_FAIL",
                "file_rel": "tools/recommendation_quality_audit_lane.py",
                "expected_unit": "site_reliability_recommendations_quality",
                "expected_gate_class": "non_critical_observability",
                "expect_exact_blocker": False,
                "expected_failure_code": "recommendations_quality_lane_failed",
                "local_runtime_validation": False,
                "make_text": lambda text: insert_python_guard(
                    text,
                    "TFE_PHASE_D_FORCE_RECO_QUALITY_FAIL",
                    "phase_d_forced_recommendation_quality_failure",
                ),
            },
            {
                "name": "runtime_critical",
                "env_name": "TFE_PHASE_D_FORCE_RUNTIME_VALIDATION_FAIL",
                "file_rel": "web/scripts/run_validation_gate_v1.mjs",
                "expected_unit": "runtime_validation",
                "expected_gate_class": "runtime_critical",
                "expect_exact_blocker": True,
                "expected_failure_code": "runtime_validation_local_failed",
                "local_runtime_validation": True,
                "make_text": lambda text: insert_js_guard(
                    text,
                    "TFE_PHASE_D_FORCE_RUNTIME_VALIDATION_FAIL",
                    "phase_d_forced_runtime_validation_failure",
                ),
            },
        ]

        for scenario in scenarios:
            try:
                results.append(run_shell_for_scenario(**scenario))
            except Exception as exc:
                blocker_payload = {
                    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "proof_scope": "phase_d_real_deploy_shell_hotfix_lane_rerun",
                    "status": "blocked",
                    "original_head_sha": ORIGINAL_HEAD,
                    "current_head_sha": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True)
                    .strip(),
                    "scenario": scenario["name"],
                    "target_file": str(ROOT / scenario["file_rel"]),
                    "error": str(exc),
                    "partial_results": results,
                }
                BLOCKER_ARTIFACT.write_text(f"{json.dumps(blocker_payload, indent=2)}\n", encoding="utf-8")
                raise
    finally:
        restore_state_file()
        restore_head()

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "proof_status": "ok",
        "proof_scope": "phase_d_real_deploy_shell_hotfix_lane_rerun",
        "original_head_sha": ORIGINAL_HEAD,
        "restored_head_sha": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "scenarios": results,
        "requirements_proved": {
            "changed_non_critical_product_parity_failure_recorded_without_exact_blocker_default_hotfix_lane": True,
            "changed_non_critical_observability_failure_recorded_without_exact_blocker_default_hotfix_lane": True,
            "runtime_critical_scenario_makes_runtime_validation_exact_blocker": True,
            "runtime_critical_unit_records_failure_code_runtime_validation_local_failed": True,
            "proof_only_output_includes_release_lane_blocking_gate_classes_non_blocking_gate_classes_release_gate_class_results": True,
        },
    }
    PROOF_ARTIFACT.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    print(str(PROOF_ARTIFACT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
