#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List


SCHEMA_VERSION = "validation_state_schema_v1"
CONTRACT_VERSION = "validation_state_contract_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def git_output(repo_root: Path, args: List[str]) -> str:
    return subprocess.check_output(["git", "-C", str(repo_root), *args], text=True).strip()


def git_lines(repo_root: Path, args: List[str]) -> List[str]:
    output = git_output(repo_root, args)
    return [line for line in output.splitlines() if line.strip()]


def matches_any(path_str: str, patterns: Iterable[str]) -> bool:
    pure_path = PurePosixPath(path_str)
    return any(pure_path.match(pattern) for pattern in patterns)


def sanitize_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()})


def sanitize_dict_of_strings(value: Any) -> Dict[str, str]:
    if not isinstance(value, dict):
        return {}
    payload: Dict[str, str] = {}
    for key, item in value.items():
        key_str = str(key).strip()
        item_str = str(item).strip()
        if key_str:
            payload[key_str] = item_str
    return payload


@dataclass(frozen=True)
class UnitDefinition:
    unit_id: str
    blocking: bool
    patterns: List[str]
    wrappers: List[str]
    outputs_expected: List[str]
    process: str
    description: str
    always_run: bool = False


AUTH_SHARED_PATTERNS = [
    "web/src/app/sign-in/**",
    "web/src/app/api/auth/**",
    "web/src/lib/auth*.ts",
    "web/src/lib/auth*.tsx",
    "web/src/lib/session*.ts",
    "web/src/lib/session*.tsx",
    "tools/run_validation_gate_v1_in_ecs_network.py",
]

RECOMMENDATION_PATTERNS = [
    "web/src/app/recommendations/**",
    "web/src/app/api/recommendations/**",
    "web/src/components/*Recommendation*.tsx",
    "web/src/lib/recommendation*.ts",
    "web/src/lib/recommendation*.tsx",
    "web/scripts/recommendations_consistency_probe.mjs",
    "tools/run_recommendations_consistency_probe_lane.sh",
    "tools/run_recommendation_quality_audit_lane.sh",
    "tools/run_site_reliability_contract_gate.sh",
    "tools/recommendation_quality_audit_lane.py",
    "tools/evaluate_recommendation_policy_snapshot.py",
    "pscf_policy_runtime.json",
    "uf_snapshot.json",
]

SCREENER_PATTERNS = [
    "web/src/app/screener/**",
    "web/src/app/api/screener/**",
    "web/src/components/*Screener*.tsx",
    "web/src/lib/screener*.ts",
    "web/src/lib/screener*.tsx",
    "web/scripts/screener_ui_parity_probe.mjs",
    "tools/run_screener_ui_parity_probe_lane.sh",
    "tools/run_site_reliability_contract_gate.sh",
    "tools/verify_screener_parity_matrix.mjs",
    "tools/verify_screener_table_filter_behavior.mjs",
]

PORTFOLIO_PATTERNS = [
    "web/src/app/portfolio/**",
    "web/src/app/api/portfolio/**",
    "web/src/components/*Portfolio*.tsx",
    "web/src/lib/portfolio*.ts",
    "web/src/lib/portfolio*.tsx",
    "web/scripts/portfolio_advisor_confidence_probe.mjs",
    "tools/run_portfolio_advisor_confidence_probe_lane.sh",
    "tools/run_site_reliability_contract_gate.sh",
]

FRONTEND_LINT_PATTERNS = [
    "web/src/**/*.ts",
    "web/src/**/*.tsx",
    "web/src/**/*.js",
    "web/src/**/*.jsx",
    "web/scripts/**/*.ts",
    "web/scripts/**/*.tsx",
    "web/scripts/**/*.js",
    "web/scripts/**/*.mjs",
    "web/package.json",
    "web/package-lock.json",
    "web/next.config.ts",
    "web/next-env.d.ts",
    "web/postcss.config.mjs",
    "web/tsconfig.json",
]

WEB_BUILD_PATTERNS = FRONTEND_LINT_PATTERNS + [
    "web/public/**",
    "web/data/ui-config.json",
]

RUNTIME_VALIDATION_PATTERNS = [
    "web/src/app/api/admin/refresh/**",
    "web/scripts/run_validation_gate_v1.mjs",
    "web/scripts/sync_runtime_postgres.mjs",
    "web/scripts/update_refresh_phase_ledger.mjs",
    "run_refresh_with_l5_learning.py",
    "rebuild_uf_snapshot.py",
    "tools/run_validation_gate_v1_in_ecs_network.py",
    "tools/verify_refresh_phase_truth_readonly.py",
]

CACHE_PATTERNS = [
    "web/data/screener-quote-cache.json",
    "web/data/screener-quote-cache.failures.json",
    "web/scripts/build_screener_quote_cache*.py",
    "web/scripts/build_screener_quote_cache*.mjs",
    "web/scripts/build_screener_profile_overrides.py",
]

ACCEPTANCE_PATTERNS = [
    "tools/evaluate_recommendation_policy_snapshot.py",
    "pscf_policy_runtime.json",
    "uf_snapshot.json",
    "run_refresh_with_l5_learning.py",
    "rebuild_uf_snapshot.py",
    "l5_policy_learning_pipeline.py",
]

CONTRACT_CONTROL_FILES = [
    "tools/deploy_to_prod_with_evidence.sh",
    "tools/validation_state_contract.py",
]


UNIT_DEFINITIONS: List[UnitDefinition] = [
    UnitDefinition(
        unit_id="deploy_contract_syntax",
        blocking=True,
        patterns=CONTRACT_CONTROL_FILES,
        wrappers=[],
        outputs_expected=["deploy-contract-syntax.log"],
        process="bash -n tools/deploy_to_prod_with_evidence.sh && python3 -m py_compile tools/validation_state_contract.py",
        description="Validate the deploy contract scripts themselves before any gate execution.",
    ),
    UnitDefinition(
        unit_id="deploy_workspace_integrity",
        blocking=True,
        patterns=[],
        wrappers=[],
        outputs_expected=[
            "dockerfile-copy-sources.txt",
            "deploy-relevant-dirty-tracked.txt",
            "deploy-relevant-untracked.txt",
            "deploy-package-decision.json",
        ],
        process="git diff/ls-files against HEAD for deploy package plus contract control files",
        description="Ensure the exact deploy package and gate scripts are committed before packaging.",
        always_run=True,
    ),
    UnitDefinition(
        unit_id="recommendation_acceptance",
        blocking=True,
        patterns=ACCEPTANCE_PATTERNS,
        wrappers=["tools/evaluate_recommendation_policy_snapshot.py"],
        outputs_expected=["recommendation-acceptance-gate.json"],
        process="python3 tools/evaluate_recommendation_policy_snapshot.py --strict-conformance ...",
        description="Protect recommendation policy decision correctness when recommendation logic changes.",
    ),
    UnitDefinition(
        unit_id="typescript",
        blocking=True,
        patterns=FRONTEND_LINT_PATTERNS,
        wrappers=[],
        outputs_expected=["strict-gate-tsc.log"],
        process="cd web && npx tsc --noEmit",
        description="TypeScript static contract for changed frontend code.",
    ),
    UnitDefinition(
        unit_id="eslint",
        blocking=True,
        patterns=FRONTEND_LINT_PATTERNS,
        wrappers=[],
        outputs_expected=["strict-gate-eslint.log", "strict-gate-eslint-files.txt"],
        process="cd web && npx eslint <delta-selected files>",
        description="Lint contract for changed frontend code only.",
    ),
    UnitDefinition(
        unit_id="web_build",
        blocking=True,
        patterns=WEB_BUILD_PATTERNS,
        wrappers=[],
        outputs_expected=["strict-gate-web-build.log"],
        process="cd web && npm run build",
        description="Production build validation for changed frontend/build inputs.",
    ),
    UnitDefinition(
        unit_id="cache_coverage",
        blocking=True,
        patterns=CACHE_PATTERNS,
        wrappers=[],
        outputs_expected=["strict-gate-cache-coverage.json"],
        process="python3 inline quote-cache coverage threshold check",
        description="Quote-cache completeness contract when quote-cache inputs change.",
    ),
    UnitDefinition(
        unit_id="runtime_validation",
        blocking=True,
        patterns=RUNTIME_VALIDATION_PATTERNS,
        wrappers=["tools/run_validation_gate_v1_in_ecs_network.py"],
        outputs_expected=["strict-gate-validation*.json", "strict-gate-validation*.log"],
        process="local runtime validation with ECS fallback",
        description="Refresh/runtime validation contract for admin refresh and runtime schema changes.",
    ),
    UnitDefinition(
        unit_id="site_reliability_recommendations",
        blocking=True,
        patterns=RECOMMENDATION_PATTERNS + AUTH_SHARED_PATTERNS,
        wrappers=["tools/run_recommendations_consistency_probe_lane.sh"],
        outputs_expected=["recommendations lane summary", "recommendations probe summary"],
        process="tools/run_recommendations_consistency_probe_lane.sh",
        description="Recommendations live commercial contract.",
    ),
    UnitDefinition(
        unit_id="site_reliability_recommendations_nonregression",
        blocking=False,
        patterns=RECOMMENDATION_PATTERNS + AUTH_SHARED_PATTERNS,
        wrappers=[],
        outputs_expected=["recommendations nonregression report"],
        process="inline recommendations nonregression comparator",
        description="Recommendations nonregression contract.",
    ),
    UnitDefinition(
        unit_id="site_reliability_recommendations_quality",
        blocking=False,
        patterns=RECOMMENDATION_PATTERNS + AUTH_SHARED_PATTERNS,
        wrappers=["tools/run_recommendation_quality_audit_lane.sh"],
        outputs_expected=["recommendation quality lane summary"],
        process="tools/run_recommendation_quality_audit_lane.sh",
        description="Recommendations quality live contract.",
    ),
    UnitDefinition(
        unit_id="site_reliability_recommendations_quality_nonregression",
        blocking=False,
        patterns=RECOMMENDATION_PATTERNS + AUTH_SHARED_PATTERNS,
        wrappers=[],
        outputs_expected=["recommendations quality nonregression report"],
        process="inline recommendation-quality nonregression comparator",
        description="Recommendations quality nonregression contract.",
    ),
    UnitDefinition(
        unit_id="site_reliability_screener",
        blocking=False,
        patterns=SCREENER_PATTERNS + AUTH_SHARED_PATTERNS,
        wrappers=["tools/run_screener_ui_parity_probe_lane.sh"],
        outputs_expected=["screener lane summary", "check-summary.json"],
        process="tools/run_screener_ui_parity_probe_lane.sh",
        description="Screener live commercial contract.",
    ),
    UnitDefinition(
        unit_id="site_reliability_portfolio",
        blocking=True,
        patterns=PORTFOLIO_PATTERNS + AUTH_SHARED_PATTERNS,
        wrappers=["tools/run_portfolio_advisor_confidence_probe_lane.sh"],
        outputs_expected=["portfolio lane summary", "portfolio probe summary"],
        process="tools/run_portfolio_advisor_confidence_probe_lane.sh",
        description="Portfolio live commercial contract.",
    ),
]


def unit_by_id() -> Dict[str, UnitDefinition]:
    return {unit.unit_id: unit for unit in UNIT_DEFINITIONS}


def tracked_files(repo_root: Path) -> List[str]:
    return git_lines(repo_root, ["ls-files"])


def repo_dirty_tracked_files(repo_root: Path) -> List[str]:
    return git_lines(repo_root, ["ls-files", "-m"])


def git_changed_files_between(repo_root: Path, base_rev: str, head_rev: str) -> List[str]:
    return git_lines(repo_root, ["diff", "--name-only", "--diff-filter=ACMR", base_rev, head_rev, "--"])


def git_untracked_files(repo_root: Path, patterns: List[str]) -> List[str]:
    if not patterns:
        return []
    return git_lines(repo_root, ["ls-files", "--others", "--exclude-standard", "--", *patterns])


def current_content_hashes(repo_root: Path, tracked: List[str]) -> Dict[str, str]:
    tracked_hashes: Dict[str, str] = {}
    for line in git_lines(repo_root, ["ls-files", "-s"]):
        parts = line.split(maxsplit=3)
        if len(parts) != 4:
            continue
        tracked_hashes[parts[3]] = parts[1]

    dirty_paths = set(repo_dirty_tracked_files(repo_root))
    for rel_path in tracked:
        absolute_path = repo_root / rel_path
        if rel_path in dirty_paths and absolute_path.exists():
            tracked_hashes[rel_path] = git_output(repo_root, ["hash-object", "--", rel_path])
        elif rel_path not in tracked_hashes:
            if absolute_path.exists():
                tracked_hashes[rel_path] = git_output(repo_root, ["hash-object", "--", rel_path])
            else:
                tracked_hashes[rel_path] = "missing"
    return tracked_hashes


def load_or_initialize_state(
    *,
    repo_root: Path,
    state_path: Path,
    tracked: List[str],
    current_hashes: Dict[str, str],
) -> tuple[Dict[str, Any], bool]:
    existing = load_json(state_path)
    state_exists = bool(isinstance(existing, dict) and existing.get("contract_version") == CONTRACT_VERSION)
    existing_files = existing.get("files") if state_exists else {}
    if not isinstance(existing_files, dict):
        existing_files = {}

    files_payload: Dict[str, Dict[str, Any]] = {}
    for rel_path in tracked:
        previous = existing_files.get(rel_path)
        if not isinstance(previous, dict):
            previous = {}
        last_result = str(previous.get("last_validation_result") or "unvalidated")
        if last_result not in {"pass", "fail", "unvalidated"}:
            last_result = "unvalidated"
        last_validated_hash = previous.get("last_validated_hash")
        if not isinstance(last_validated_hash, str):
            last_validated_hash = None
        record = {
            "content_hash": current_hashes[rel_path],
            "contract_version": CONTRACT_VERSION,
            "last_validated_at_utc": str(previous.get("last_validated_at_utc") or "") or None,
            "last_validation_result": last_result,
            "last_validation_scopes": sanitize_list(previous.get("last_validation_scopes")),
            "last_validation_scope_results": sanitize_dict_of_strings(previous.get("last_validation_scope_results")),
            "last_validation_sources": sanitize_dict_of_strings(previous.get("last_validation_sources")),
            "last_validated_hash": last_validated_hash,
            "dirty_since_validation": True,
        }
        record["dirty_since_validation"] = not (
            isinstance(record["last_validated_hash"], str)
            and record["last_validated_hash"] == current_hashes[rel_path]
        )
        files_payload[rel_path] = record

    state = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "generated_at_utc": utc_now(),
        "repo_root": str(repo_root),
        "tracked_file_count": len(tracked),
        "files": files_payload,
    }
    return state, state_exists


def write_schema_artifact(path: Path) -> None:
    write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "required_file_fields": [
                "content_hash",
                "contract_version",
                "last_validated_at_utc",
                "last_validation_result",
                "last_validation_scopes",
                "dirty_since_validation",
            ],
            "additional_file_fields": [
                "last_validation_scope_results",
                "last_validation_sources",
                "last_validated_hash",
            ],
        },
    )


def build_relevant_patterns(deploy_patterns: List[str]) -> List[str]:
    patterns: List[str] = list(CONTRACT_CONTROL_FILES)
    patterns.extend(deploy_patterns)
    for unit in UNIT_DEFINITIONS:
        patterns.extend(unit.patterns)
        patterns.extend(unit.wrappers)
    return sorted({pattern for pattern in patterns if pattern})


def prepare(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    evidence_dir = Path(args.evidence_dir).resolve()
    state_path = Path(args.state_path).resolve()
    deploy_pattern_file = Path(args.deploy_pattern_file).resolve()

    evidence_dir.mkdir(parents=True, exist_ok=True)

    tracked = tracked_files(repo_root)
    current_hashes = current_content_hashes(repo_root, tracked)
    state, state_exists = load_or_initialize_state(
        repo_root=repo_root,
        state_path=state_path,
        tracked=tracked,
        current_hashes=current_hashes,
    )

    deploy_patterns = [
        line.strip()
        for line in deploy_pattern_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    relevant_patterns = build_relevant_patterns(deploy_patterns)
    untracked_patterns = sorted(set(deploy_patterns + CONTRACT_CONTROL_FILES))
    relevant_tracked = sorted([path for path in tracked if matches_any(path, relevant_patterns)])
    relevant_untracked = sorted(git_untracked_files(repo_root, untracked_patterns))

    if state_exists:
        tracked_changed = sorted([path for path in relevant_tracked if bool(state["files"][path]["dirty_since_validation"])])
        delta_mode = "validation_state"
        delta_reason = "tracked_hash_changed_since_validation"
    else:
        git_delta = set(git_changed_files_between(repo_root, args.base_rev, args.head_rev))
        worktree_dirty = set(repo_dirty_tracked_files(repo_root))
        tracked_changed = sorted([path for path in relevant_tracked if path in git_delta or path in worktree_dirty])
        delta_mode = "bootstrap_current_delta"
        delta_reason = "state_missing_using_current_git_delta"

    changed_union = sorted(set(tracked_changed) | set(relevant_untracked))
    unchanged_tracked = sorted([path for path in relevant_tracked if path not in tracked_changed])

    delta_payload = {
        "generated_at_utc": utc_now(),
        "state_exists": state_exists,
        "delta_mode": delta_mode,
        "delta_reason": delta_reason,
        "base_rev": args.base_rev,
        "head_rev": args.head_rev,
        "tracked_changed_files": tracked_changed,
        "tracked_unchanged_files": unchanged_tracked,
        "relevant_untracked_files": relevant_untracked,
        "changed_files_union": changed_union,
    }

    write_schema_artifact(evidence_dir / "validation-state-schema.json")
    write_json(evidence_dir / "validation-state-before.json", state)
    write_json(evidence_dir / "delta-selected-files.json", delta_payload)
    (evidence_dir / "delta-selected-files.txt").write_text(
        "\n".join(changed_union) + ("\n" if changed_union else ""),
        encoding="utf-8",
    )

    deploy_script_text = (repo_root / "tools/deploy_to_prod_with_evidence.sh").read_text(encoding="utf-8")
    split_tokens = {
        "deploy_script": {
            "TFE_DEPLOY_GATE_PROFILE": "TFE_DEPLOY_GATE_PROFILE" not in deploy_script_text,
            "skipped_by_fast_profile": "skipped_by_fast_profile" not in deploy_script_text,
            "strict_gate_profile": "strict_gate_profile" not in deploy_script_text,
            "strict-gate-profile.json": "strict-gate-profile.json" not in deploy_script_text,
        }
    }
    split_model_removed = all(split_tokens["deploy_script"].values())
    write_json(
        evidence_dir / "split-model-proof.json",
        {
            "generated_at_utc": utc_now(),
            "contract_version": CONTRACT_VERSION,
            "files": split_tokens,
            "split_model_removed": split_model_removed,
        },
    )

    files_payload = state["files"]
    units_payload = []
    mapped_units_by_changed_file: Dict[str, List[str]] = {path: [] for path in changed_union}

    for unit in UNIT_DEFINITIONS:
        if unit.always_run and not unit.patterns:
            mapped_tracked_inputs = list(relevant_tracked)
            mapped_untracked_inputs = list(relevant_untracked)
            changed_inputs = list(changed_union)
        else:
            mapped_tracked_inputs = [path for path in relevant_tracked if matches_any(path, unit.patterns)]
            mapped_untracked_inputs = [path for path in relevant_untracked if matches_any(path, unit.patterns)]
            changed_inputs = [path for path in changed_union if matches_any(path, unit.patterns)]

        for changed_path in changed_inputs:
            mapped_units_by_changed_file.setdefault(changed_path, []).append(unit.unit_id)

        dirty_or_unvalidated_inputs = []
        unchanged_validated_inputs = []
        for path in mapped_tracked_inputs:
            scope_results = sanitize_dict_of_strings(files_payload[path].get("last_validation_scope_results"))
            scope_status = str(scope_results.get(unit.unit_id) or "")
            if scope_status and not bool(files_payload[path]["dirty_since_validation"]):
                unchanged_validated_inputs.append(path)
            else:
                dirty_or_unvalidated_inputs.append(path)

        selected = False
        selection_reason: str | None = None
        skip_reason: str | None = None

        if unit.always_run:
            selected = True
            selection_reason = "always_run_deploy_integrity"
        elif changed_inputs:
            selected = True
            selection_reason = "changed_hash_delta" if state_exists else "state_bootstrap_current_delta"
        elif mapped_tracked_inputs or mapped_untracked_inputs:
            if state_exists and unchanged_validated_inputs and not mapped_untracked_inputs:
                skip_reason = "unchanged_since_last_validated"
            else:
                skip_reason = "no_relevant_delta_selected"
        else:
            skip_reason = "no_mapped_inputs"

        units_payload.append(
            {
                "unit_id": unit.unit_id,
                "description": unit.description,
                "blocking": unit.blocking,
                "patterns": unit.patterns,
                "wrappers": unit.wrappers,
                "process": unit.process,
                "outputs_expected": unit.outputs_expected,
                "selected": selected,
                "selection_reason": selection_reason,
                "skip_reason": skip_reason,
                "mapped_tracked_inputs": mapped_tracked_inputs,
                "mapped_untracked_inputs": mapped_untracked_inputs,
                "changed_inputs": changed_inputs,
                "dirty_or_unvalidated_inputs": dirty_or_unvalidated_inputs,
                "unchanged_validated_inputs": unchanged_validated_inputs,
            }
        )

    unmapped_changed = sorted([path for path, units in mapped_units_by_changed_file.items() if not units])
    selection_payload = {
        "generated_at_utc": utc_now(),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "state_path": str(state_path),
        "single_delta_contract_active": True,
        "profile_model_present": False,
        "split_model_removed": split_model_removed,
        "changed_files": delta_payload,
        "units": units_payload,
        "unmapped_changed_files": unmapped_changed,
    }
    write_json(evidence_dir / "delta-unit-selection.json", selection_payload)

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(str(evidence_dir / "delta-unit-selection.json"))
    return 0


def finalize(args: argparse.Namespace) -> int:
    evidence_dir = Path(args.evidence_dir).resolve()
    state_path = Path(args.state_path).resolve()
    selection = load_json(Path(args.selection_json).resolve()) or {}
    state = load_json(state_path) or {}
    files_payload: Dict[str, Dict[str, Any]] = state.get("files", {})
    block_dir = Path(args.block_artifact_dir).resolve()

    artifacts: List[Dict[str, Any]] = []
    blocking_failures: List[Dict[str, Any]] = []

    for unit_payload in selection.get("units", []):
        unit_id = str(unit_payload.get("unit_id") or "")
        artifact_path = block_dir / f"{unit_id}.json"
        artifact = load_json(artifact_path)
        if not isinstance(artifact, dict):
            artifact = {
                "unit_id": unit_id,
                "status": "skip",
                "selected": False,
                "blocking": bool(unit_payload.get("blocking")),
                "skip_reason": "artifact_missing",
                "failure_code": None,
                "failure_message": "",
                "state_update_inputs": [],
            }

        artifacts.append(artifact)

        update_inputs = artifact.get("state_update_inputs")
        if not isinstance(update_inputs, list):
            update_inputs = []
        if not update_inputs and bool(artifact.get("selected")):
            update_inputs = unit_payload.get("changed_inputs") or []

        if bool(artifact.get("selected")):
            for rel_path in update_inputs:
                if rel_path not in files_payload:
                    continue
                record = files_payload[rel_path]
                scope_results = sanitize_dict_of_strings(record.get("last_validation_scope_results"))
                if str(artifact.get("status")) == "pass":
                    scope_results[unit_id] = "pass"
                else:
                    scope_results[unit_id] = "fail"
                record["last_validation_scope_results"] = scope_results
                record["last_validation_scopes"] = sorted(scope_results.keys())
                source_map = sanitize_dict_of_strings(record.get("last_validation_sources"))
                source_map[unit_id] = str(artifact_path)
                record["last_validation_sources"] = source_map
                record["last_validated_at_utc"] = str(artifact.get("recorded_at_utc") or utc_now())
                record["last_validated_hash"] = record.get("content_hash")
                record["last_validation_result"] = "fail" if "fail" in scope_results.values() else "pass"

        if bool(artifact.get("blocking")) and str(artifact.get("status")) == "fail":
            blocking_failures.append(artifact)

    for rel_path, record in files_payload.items():
        content_hash = str(record.get("content_hash") or "")
        last_validated_hash = record.get("last_validated_hash")
        record["dirty_since_validation"] = not (
            isinstance(last_validated_hash, str)
            and last_validated_hash == content_hash
        )

    state["generated_at_utc"] = utc_now()
    state["tracked_file_count"] = len(files_payload)
    write_json(evidence_dir / "validation-state-after.json", state)
    write_json(state_path, state)

    summary = {
        "generated_at_utc": utc_now(),
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "state_path": str(state_path),
        "selection_json": str(args.selection_json),
        "split_model_removed": bool(selection.get("split_model_removed")),
        "single_delta_contract_active": bool(selection.get("single_delta_contract_active")),
        "changed_files": selection.get("changed_files"),
        "units": artifacts,
        "blocking_failures": blocking_failures,
        "exact_blocker": blocking_failures[0] if blocking_failures else None,
        "unchanged_validated_units_skipped": [
            artifact["unit_id"]
            for artifact in artifacts
            if str(artifact.get("status")) == "skip"
            and str(artifact.get("skip_reason")) == "unchanged_since_last_validated"
        ],
        "delta_not_selected_units_skipped": [
            artifact["unit_id"]
            for artifact in artifacts
            if str(artifact.get("status")) == "skip"
            and str(artifact.get("skip_reason")) == "no_relevant_delta_selected"
        ],
    }
    write_json(evidence_dir / "delta-contract-summary.json", summary)
    print(str(evidence_dir / "delta-contract-summary.json"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--repo-root", required=True)
    prepare_parser.add_argument("--state-path", required=True)
    prepare_parser.add_argument("--evidence-dir", required=True)
    prepare_parser.add_argument("--deploy-pattern-file", required=True)
    prepare_parser.add_argument("--base-rev", required=True)
    prepare_parser.add_argument("--head-rev", required=True)

    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--state-path", required=True)
    finalize_parser.add_argument("--evidence-dir", required=True)
    finalize_parser.add_argument("--selection-json", required=True)
    finalize_parser.add_argument("--block_artifact_dir", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "prepare":
        return prepare(args)
    if args.command == "finalize":
        return finalize(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
