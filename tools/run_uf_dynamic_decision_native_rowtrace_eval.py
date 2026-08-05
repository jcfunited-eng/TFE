#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
WEB_ROOT = REPO_ROOT / "web"
EXPORTER = REPO_ROOT / "real_world_cleaned_universe_l5_primitive_only_row_trace_export.py"
OUT_DIR = REPO_ROOT / "backups/runtime"
ENV_PATH = REPO_ROOT / ".env"
RUNTIME_SOURCE = REPO_ROOT / "web/src/lib/uf-dynamic-decision.ts"
PRESSURE_SOURCE = REPO_ROOT / "web/src/lib/uf-dynamic-decision-pressure-test.ts"
DOC_SOURCE = REPO_ROOT / "DSF_PRIMITIVE_INTERPRETATION_RECOVERY.md"

EXPECTED_COLUMNS = [
    "symbol",
    "decision_timestamp",
    "bar_count",
    "S_UF",
    "R_UF",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
]

REQUIRED_NUMERIC_COLUMNS = [
    "bar_count",
    "S_UF",
    "R_UF",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
]

FORBIDDEN_RUNTIME_TOKENS = [
    "stabilityScore",
    "stability_score",
    "decision_vector",
    "S_local",
    "R_local",
    "forward_return",
    "oracle",
    "proxy",
    "SPY",
    "excess",
]

FORBIDDEN_DOC_TOKENS = [
    "S_local",
    "R_local",
    "IS_h",
    "IS_H",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Generate a fresh primitive-only row-trace artifact and enforce the primitive recovery lane "
            "contract plus direct runtime behavior checks."
        )
    )
    p.add_argument("--years-history", type=int, default=5)
    p.add_argument("--min-bars", type=int, default=120)
    p.add_argument("--learning-bars", type=int, default=252)
    p.add_argument("--max-symbols", type=int, default=0)
    p.add_argument("--force-refresh-universe", action="store_true")
    p.add_argument("--export-timeout-seconds", type=int, default=600)
    return p.parse_args()


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_dotenv_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        env_key = key.strip()
        env_value = raw_value.strip().strip('"').strip("'")
        if env_key:
            values[env_key] = env_value
    return values


def build_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    dotenv_values = read_dotenv_values(ENV_PATH)
    for key, value in dotenv_values.items():
        if key not in env or not str(env.get(key, "")).strip():
            env[key] = value
    if ENV_PATH.exists():
        env["DOTENV_PATH_USED"] = str(ENV_PATH)
    return env


def scan_source(path: Path, forbidden_tokens: list[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    hits = {token: (token in text) for token in forbidden_tokens}
    return {
        "path": str(path),
        "forbidden_hits": {token: present for token, present in hits.items() if present},
        "clean": not any(hits.values()),
    }


def to_float(raw: Any) -> float | None:
    try:
        value = float(raw)
    except Exception:
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def validate_rows(
    rows: list[dict[str, str]],
    *,
    min_required_bar_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    violations: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        row_violations: list[str] = []

        for column in REQUIRED_NUMERIC_COLUMNS:
            raw = row.get(column)
            if raw is None or str(raw).strip() == "":
                row_violations.append(f"blank:{column}")
                continue
            parsed = to_float(raw)
            if parsed is None:
                row_violations.append(f"nonfinite:{column}")
                continue
            if column == "bar_count":
                if int(parsed) != parsed:
                    row_violations.append("non_integer:bar_count")
                elif int(parsed) < min_required_bar_count:
                    row_violations.append(f"below_required_bar_count:{int(parsed)}<{min_required_bar_count}")

        if row_violations:
            violations.append(
                {
                    "row_index": idx,
                    "symbol": row.get("symbol"),
                    "decision_timestamp": row.get("decision_timestamp"),
                    "violations": row_violations,
                }
            )
            if len(samples) < 25:
                samples.append(violations[-1])

    return violations, samples


def run_runtime_behavior_tests() -> dict[str, Any]:
    node_script = f"""
const fs = require("fs");
const os = require("os");
const path = require("path");
const ts = require("typescript");

const runtimePath = {json.dumps(str(RUNTIME_SOURCE))};
const source = fs.readFileSync(runtimePath, "utf8");
const transpiled = ts.transpileModule(source, {{
  compilerOptions: {{
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  }},
}}).outputText;

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "uf-dynamic-runtime-audit-"));
const tempModulePath = path.join(tempDir, "uf-dynamic-decision.cjs");
fs.writeFileSync(tempModulePath, transpiled);
const mod = require(tempModulePath);

const profile = {{
  profileId: "runtime_behavior_audit",
  generatedAtUtc: "2026-03-19T00:00:00Z",
  minBars: 180,
}};

const validInput = {{
  symbol: "TEST",
  barCount: 200,
  S_UF: 0.9,
  R_UF: 0.8,
  D_k: 1,
  M_k: 0,
  R_rev_k: 0,
  U_star_k: 0.2,
  C_k: 3,
  P_k: 0,
  B_k: 0,
}};

function runCase(name, input, expect) {{
  const result = mod.computePrimitiveDynamicDecision(input, profile);
  const ok = expect(result);
  return {{
    name,
    ok,
    blockerCode: result.blockerCode,
    blockerActive: result.blockerActive,
    decision: result.decision,
    structuralMissingFields: result.provenance.structuralMissingFields,
    rawInputIsNull: result.provenance.rawInput === null,
    termBreakdownPresent: result.termBreakdown !== null,
  }};
}}

const cases = [];

cases.push(runCase("row_not_found_blocks", null, (result) =>
  result.blockerCode === "ROW_NOT_FOUND" &&
  result.blockerActive === true &&
  result.provenance.rawInput === null
));

cases.push(runCase("insufficient_bars_blocks", {{ ...validInput, barCount: 100 }}, (result) =>
  result.blockerCode === "INSUFFICIENT_BARS" &&
  result.blockerActive === true
));

for (const fieldName of ["S_UF","R_UF","D_k","M_k","R_rev_k","U_star_k","C_k","P_k","B_k"]) {{
  cases.push(runCase(`missing_${{fieldName}}_blocks`, {{ ...validInput, [fieldName]: null }}, (result) =>
    result.blockerCode === "STRUCTURAL_INCOMPLETE" &&
    result.blockerActive === true &&
    Array.isArray(result.provenance.structuralMissingFields) &&
    result.provenance.structuralMissingFields.includes(fieldName)
  ));
}}

for (const fieldName of ["S_UF","R_UF","D_k","M_k","R_rev_k","U_star_k","C_k","P_k","B_k"]) {{
  cases.push(runCase(`blank_${{fieldName}}_blocks`, {{ ...validInput, [fieldName]: " " }}, (result) =>
    result.blockerCode === "STRUCTURAL_INCOMPLETE" &&
    result.blockerActive === true &&
    Array.isArray(result.provenance.structuralMissingFields) &&
    result.provenance.structuralMissingFields.includes(fieldName)
  ));
}}

cases.push(runCase("nan_bar_count_blocks", {{ ...validInput, barCount: Number.NaN }}, (result) =>
  result.blockerCode === "STRUCTURAL_INCOMPLETE" &&
  result.blockerActive === true &&
  Array.isArray(result.provenance.structuralMissingFields) &&
  result.provenance.structuralMissingFields.includes("barCount")
));

cases.push(runCase("valid_row_unblocked", validInput, (result) =>
  result.blockerCode === "NONE" &&
  result.blockerActive === false &&
  result.provenance.rawInput !== null &&
  result.termBreakdown !== null
));

process.stdout.write(JSON.stringify({{
  all_passed: cases.every((item) => item.ok),
  cases,
}}));
"""

    proc = subprocess.run(
        ["node", "-e", node_script],
        cwd=str(WEB_ROOT),
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return {
            "all_passed": False,
            "execution_failed": True,
            "stdout_tail": proc.stdout.splitlines()[-40:],
            "stderr_tail": proc.stderr.splitlines()[-40:],
            "cases": [],
        }

    payload = json.loads(proc.stdout)
    payload["execution_failed"] = False
    return payload


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    violations: list[dict[str, Any]] = []
    subprocess_env = build_subprocess_env()

    with tempfile.TemporaryDirectory(prefix="uf_native_rowtrace_audit_") as td:
        temp_dir = Path(td)
        cmd = [
            sys.executable,
            str(EXPORTER),
            "--years-history",
            str(int(args.years_history)),
            "--min-bars",
            str(int(args.min_bars)),
            "--learning-bars",
            str(int(args.learning_bars)),
        ]
        if int(args.max_symbols) > 0:
            cmd.extend(["--max-symbols", str(int(args.max_symbols))])
        if bool(args.force_refresh_universe):
            cmd.append("--force-refresh-universe")

        report: dict[str, Any] = {
            "generated_at_utc": utc_iso(),
            "method": {
                "type": "native_rowtrace_primitive_contract_audit",
                "note": (
                    "Enforcement audit for the primitive recovery lane. Fails on contract drift, empty or invalid "
                    "artifacts, and direct runtime behavior violations."
                ),
                "runtime_source": str(RUNTIME_SOURCE),
                "pressure_test_source": str(PRESSURE_SOURCE),
                "exporter_source": str(EXPORTER),
                "document_source": str(DOC_SOURCE),
            },
        }

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(temp_dir),
                env=subprocess_env,
                capture_output=True,
                text=True,
                timeout=max(1, int(args.export_timeout_seconds)),
            )
        except subprocess.TimeoutExpired as exc:
            report["status"] = "failed"
            report["artifact_generation"] = {
                "command": cmd,
                "timed_out": True,
                "timeout_seconds": int(args.export_timeout_seconds),
                "stdout_tail": (exc.stdout or "").splitlines()[-40:],
                "stderr_tail": (exc.stderr or "").splitlines()[-40:],
                "dotenv_path_used": str(ENV_PATH) if ENV_PATH.exists() else None,
                "massive_api_key_present": bool(subprocess_env.get("MASSIVE_API_KEY")),
                "polygon_api_key_present": bool(subprocess_env.get("POLYGON_API_KEY")),
            }
            violations.append({"code": "export_timeout"})
            report["violations"] = violations
            out_path = OUT_DIR / f"uf_dynamic_decision_native_rowtrace_eval_{utc_stamp()}.json"
            out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps({"report_path": str(out_path), "status": "failed", "violations": violations}, indent=2))
            return 2

        artifact_path = temp_dir / "real_world_cleaned_universe_l5_primitive_only_row_trace.csv"
        metadata_path = temp_dir / "real_world_cleaned_universe_l5_primitive_only_row_trace_metadata.json"

        report["artifact_generation"] = {
            "command": cmd,
            "returncode": int(proc.returncode),
            "stdout_tail": proc.stdout.splitlines()[-40:],
            "stderr_tail": proc.stderr.splitlines()[-40:],
            "dotenv_path_used": str(ENV_PATH) if ENV_PATH.exists() else None,
            "massive_api_key_present": bool(subprocess_env.get("MASSIVE_API_KEY")),
            "polygon_api_key_present": bool(subprocess_env.get("POLYGON_API_KEY")),
        }

        if proc.returncode != 0:
            violations.append({"code": "export_failed"})
        if not artifact_path.exists():
            violations.append({"code": "artifact_csv_missing"})
        if not metadata_path.exists():
            violations.append({"code": "artifact_metadata_missing"})

        rows: list[dict[str, str]] = []
        artifact_columns: list[str] = []
        metadata: dict[str, Any] = {}

        if artifact_path.exists():
            with artifact_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                artifact_columns = reader.fieldnames or []

        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        runtime_scan = scan_source(RUNTIME_SOURCE, FORBIDDEN_RUNTIME_TOKENS)
        pressure_scan = scan_source(PRESSURE_SOURCE, ["S_local", "R_local", "decision_vector"])
        doc_scan = scan_source(DOC_SOURCE, FORBIDDEN_DOC_TOKENS)

        if artifact_columns != EXPECTED_COLUMNS:
            violations.append(
                {
                    "code": "artifact_columns_mismatch",
                    "expected_columns": EXPECTED_COLUMNS,
                    "artifact_columns": artifact_columns,
                }
            )

        if len(rows) <= 0:
            violations.append({"code": "artifact_rows_empty"})

        row_violations, row_violation_samples = validate_rows(
            rows,
            min_required_bar_count=max(int(args.min_bars), int(args.learning_bars)),
        )
        if row_violations:
            violations.append({"code": "row_content_invalid", "count": len(row_violations)})

        metadata_checks = {
            "feed_adjusted": metadata.get("config", {}).get("feed_adjusted"),
            "integrity_filter_applied": metadata.get("config", {}).get("integrity_filter_applied"),
            "primitive_authoritative_fields_only": metadata.get("row_contract", {}).get("primitive_authoritative_fields_only"),
            "approved_primitive_inputs_only": metadata.get("row_contract", {}).get("approved_primitive_inputs_only"),
            "explicit_level4_fields_authoritative": metadata.get("row_contract", {}).get("explicit_level4_fields_authoritative"),
            "explicit_level5_fields_authoritative": metadata.get("row_contract", {}).get("explicit_level5_fields_authoritative"),
            "transport_fallback_used": metadata.get("row_contract", {}).get("transport_fallback_used"),
            "noncanonical_fields_removed": metadata.get("row_contract", {}).get("noncanonical_fields_removed"),
        }

        metadata_expectations = {
            "feed_adjusted": False,
            "integrity_filter_applied": False,
            "primitive_authoritative_fields_only": True,
            "approved_primitive_inputs_only": True,
            "explicit_level4_fields_authoritative": True,
            "explicit_level5_fields_authoritative": True,
            "transport_fallback_used": False,
        }

        metadata_mismatches: dict[str, Any] = {}
        for key, expected in metadata_expectations.items():
            actual = metadata_checks.get(key)
            if actual != expected:
                metadata_mismatches[key] = {"expected": expected, "actual": actual}
        if metadata_mismatches:
            violations.append({"code": "metadata_mismatch", "mismatches": metadata_mismatches})

        if not runtime_scan["clean"]:
            violations.append({"code": "runtime_source_forbidden_tokens", "hits": runtime_scan["forbidden_hits"]})
        if not pressure_scan["clean"]:
            violations.append({"code": "pressure_source_forbidden_tokens", "hits": pressure_scan["forbidden_hits"]})
        if not doc_scan["clean"]:
            violations.append({"code": "document_forbidden_tokens", "hits": doc_scan["forbidden_hits"]})

        runtime_behavior = run_runtime_behavior_tests()
        if runtime_behavior.get("execution_failed"):
            violations.append({"code": "runtime_behavior_execution_failed"})
        elif not runtime_behavior.get("all_passed", False):
            failing_cases = [case for case in runtime_behavior.get("cases", []) if not case.get("ok")]
            violations.append({"code": "runtime_behavior_failed", "failing_cases": failing_cases})

        report["runtime_behavior"] = runtime_behavior
        report["summary"] = {
            "rows_emitted": int(len(rows)),
            "artifact_columns_exact_match": artifact_columns == EXPECTED_COLUMNS,
            "runtime_source_clean": bool(runtime_scan["clean"]),
            "pressure_test_source_clean": bool(pressure_scan["clean"]),
            "document_clean": bool(doc_scan["clean"]),
            "row_violation_count": len(row_violations),
            "violation_count": len(violations),
        }
        report["artifact_columns"] = {
            "artifact_columns": artifact_columns,
            "expected_columns": EXPECTED_COLUMNS,
        }
        report["metadata_checks"] = metadata_checks
        report["metadata_expectations"] = metadata_expectations
        report["row_validation"] = {
            "violations": row_violations[:200],
            "samples": row_violation_samples,
        }
        report["source_scans"] = {
            "runtime": runtime_scan,
            "pressure_test": pressure_scan,
            "document": doc_scan,
        }
        report["violations"] = violations
        report["status"] = "completed" if not violations else "failed"

        out_path = OUT_DIR / f"uf_dynamic_decision_native_rowtrace_eval_{utc_stamp()}.json"
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "report_path": str(out_path),
                    "status": report["status"],
                    "rows_emitted": len(rows),
                    "violation_count": len(violations),
                },
                indent=2,
            )
        )
        return 0 if not violations else 2


if __name__ == "__main__":
    raise SystemExit(main())
