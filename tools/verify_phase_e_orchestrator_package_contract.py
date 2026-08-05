#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine")
WEB_ROOT = REPO_ROOT / "web"
RUNTIME_ROOT = REPO_ROOT / "backups" / "runtime"
TSC_PATH = WEB_ROOT / "node_modules" / ".bin" / "tsc"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def rel_module(from_path: Path, module_path: Path) -> str:
    text = os.path.relpath(module_path.with_suffix(""), from_path.parent).replace("\\", "/")
    return text if text.startswith(".") else f"./{text}"


def run_checked(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )


def main() -> int:
    timestamp = utc_stamp()
    support_dir = RUNTIME_ROOT / f"phase-e-orchestrator-package-contract-proof-{timestamp}"
    support_dir.mkdir(parents=True, exist_ok=True)

    generated_ts = support_dir / "phase_e_orchestrator_package_contract_runner.ts"
    generated_tsconfig = support_dir / "tsconfig.verify.json"
    workspace_root = support_dir / "workspace"
    proof_store_path = support_dir / "proof-store.json"
    compiled_dir = support_dir / "compiled"

    orchestrator_module = rel_module(generated_ts, REPO_ROOT / "web" / "src" / "lib" / "step1" / "orchestrator.ts")
    schema_module = rel_module(generated_ts, REPO_ROOT / "web" / "src" / "lib" / "step1" / "schema.ts")

    generated_ts.write_text(
        textwrap.dedent(
            f"""
            import {{ readFile }} from "node:fs/promises";

            import {{
              STEP1_CUTOVER_EXECUTION_PATH,
              dispatchStep1Orchestrator,
              resolveStep1OrchestratorInputFromAdminRefreshRequest,
            }} from "{orchestrator_module}";
            import {{
              parseStoredStep1AssessmentReportArtifact,
              parseStoredStep1CandidateBundleManifest,
              parseStoredStep1RunRequestRecord,
            }} from "{schema_module}";

            async function main(): Promise<void> {{
              const workspaceRoot = process.argv[2];
              const proofStorePath = process.argv[3];
              if (!workspaceRoot || !proofStorePath) {{
                throw new Error("workspaceRoot and proofStorePath are required.");
              }}

              const sourcePackageIdentities = [
                {{
                  sourcePackageId: "source_package_v1_vendor_prices_primary_20260316t081500z",
                  sourceIdentity: "vendor_prices_primary",
                  acquisitionTimestampUtc: "2026-03-16T08:15:00Z",
                  sourceClass: "tier1_vendor_feed",
                  rawPayloadReference: "s3://tfe-source/vendor_prices_primary/2026-03-16T08:15:00Z.json",
                  integrityStatus: "complete",
                }},
                {{
                  sourcePackageId: "source_package_v1_vendor_reference_primary_20260316t082000z",
                  sourceIdentity: "vendor_reference_primary",
                  acquisitionTimestampUtc: "2026-03-16T08:20:00Z",
                  sourceClass: "tier1_vendor_feed",
                  rawPayloadReference: "s3://tfe-source/vendor_reference_primary/2026-03-16T08:20:00Z.json",
                  integrityStatus: "complete",
                }},
              ];

              const resolution = resolveStep1OrchestratorInputFromAdminRefreshRequest({{
                requestBody: {{
                  runId: "phase-e-orchestrator-package-contract-proof-run",
                  normalizedPackageId: "normalized_package_v1_prices_us_equities_20260316",
                  policySetId: "policy_set_v1_publication_safety",
                  modelSetId: "model_set_v1_advisor_core",
                  configSetId: "config_set_v1_prod_snapshot",
                  bundleClass: "publication_candidate",
                  dependencyClassificationRegister: {{
                    normalized_package: "publication_critical",
                    policy_bundle: "publication_critical",
                    model_bundle: "publication_critical",
                    config_bundle: "publication_critical",
                  }},
                  sourcePackageIdentities,
                  targetEnvironment: "production",
                  requestedAtUtc: "2026-03-16T08:25:00Z",
                  assessmentRuleSetId: "assessment_rule_set_v1_publication_safety",
                  followupDesiredStatus: "deferred",
                }},
                requestedBy: "codex",
                executionMode: "readonly",
                requestedMode: "snapshot",
                env: {{}},
              }});

              const result = await dispatchStep1Orchestrator(resolution.input, {{
                executionMode: "readonly",
                proofStorePath,
                workspaceRoot,
              }});

              const requestRecord = parseStoredStep1RunRequestRecord(
                JSON.parse(await readFile(result.requestArtifactPath, "utf8")),
              );
              if (!requestRecord) {{
                throw new Error("request artifact parse failed.");
              }}

              const candidateManifest = parseStoredStep1CandidateBundleManifest(
                JSON.parse(await readFile(result.candidateBundleManifestPath, "utf8")),
              );
              if (!candidateManifest) {{
                throw new Error("candidate manifest parse failed.");
              }}

              const assessmentReport = parseStoredStep1AssessmentReportArtifact(
                JSON.parse(await readFile(result.assessmentReportPath, "utf8")),
              );
              if (!assessmentReport) {{
                throw new Error("assessment report parse failed.");
              }}

              const normalizedPackageManifest = JSON.parse(
                await readFile(candidateManifest.normalized_package_manifest_path, "utf8"),
              ) as Record<string, unknown>;

              const expectedSourcePackageIds = sourcePackageIdentities.map((entry) => entry.sourcePackageId).sort();
              const resolvedSourcePackageIds = (resolution.input.sourcePackageIdentities ?? [])
                .map((entry) => entry.sourcePackageId)
                .sort();
              const requestSourcePackageIds = (requestRecord.source_package_identities ?? [])
                .map((entry) => entry.source_package_id)
                .sort();
              const candidateSourcePackageIds = candidateManifest.source_package_identities
                .map((entry) => entry.source_package_id)
                .sort();
              const assessmentSourcePackageIds = assessmentReport.evidence_references
                .filter((entry) => entry.evidence_kind === "source_package_manifest")
                .map((entry) => entry.evidence_id)
                .sort();
              const normalizedPackageIdentityEvidence = assessmentReport.evidence_references.find(
                (entry) => entry.evidence_kind === "normalized_package_identity",
              );
              const normalizedPackageManifestEvidence = assessmentReport.evidence_references.find(
                (entry) => entry.evidence_kind === "normalized_package_manifest",
              );

              const proof = {{
                dispatch_path_remains_step1_orchestrator:
                  result.executionPath === STEP1_CUTOVER_EXECUTION_PATH,
                orchestrator_input_carries_exact_source_package_identities:
                  resolution.contractSource === "request_body"
                  && JSON.stringify(resolvedSourcePackageIds) === JSON.stringify(expectedSourcePackageIds),
                request_artifact_contains_exact_source_package_identities:
                  JSON.stringify(requestSourcePackageIds) === JSON.stringify(expectedSourcePackageIds),
                candidate_bundle_manifest_cites_exact_normalized_package_identity:
                  candidateManifest.normalized_package_id === requestRecord.normalized_package_id
                  && String(normalizedPackageManifest.normalized_package_manifest_id ?? "")
                    === candidateManifest.normalized_package_manifest_id,
                candidate_bundle_manifest_cites_exact_source_package_identities:
                  JSON.stringify(candidateSourcePackageIds) === JSON.stringify(expectedSourcePackageIds),
                assessment_evidence_cites_same_normalized_package_identity_and_exact_source_package_identities:
                  normalizedPackageIdentityEvidence?.evidence_id === candidateManifest.normalized_package_id
                  && normalizedPackageManifestEvidence?.evidence_id === candidateManifest.normalized_package_manifest_id
                  && JSON.stringify(assessmentSourcePackageIds) === JSON.stringify(expectedSourcePackageIds),
                request_artifact_path: result.requestArtifactPath,
                candidate_bundle_manifest_path: result.candidateBundleManifestPath,
                normalized_package_manifest_path: candidateManifest.normalized_package_manifest_path,
                assessment_report_path: result.assessmentReportPath,
                publication_manifest_path: result.publicationManifestPath,
                followup_ticket_path: result.followupTicketPath,
                request_source_package_ids: requestSourcePackageIds,
                candidate_source_package_ids: candidateSourcePackageIds,
                assessment_source_package_ids: assessmentSourcePackageIds,
                normalized_package_id: candidateManifest.normalized_package_id,
                normalized_package_manifest_id: candidateManifest.normalized_package_manifest_id,
                followup_status: result.followupStatus,
              }};

              process.stdout.write(`${{JSON.stringify(proof, null, 2)}}\\n`);
            }}

            main().catch((error) => {{
              const message = error instanceof Error ? error.stack ?? error.message : String(error);
              console.error(message);
              process.exit(1);
            }});
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    generated_tsconfig.write_text(
        json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2022",
                    "module": "nodenext",
                    "moduleResolution": "nodenext",
                    "esModuleInterop": True,
                    "resolveJsonModule": True,
                    "skipLibCheck": True,
                    "baseUrl": os.path.relpath(WEB_ROOT, support_dir),
                    "paths": {
                        "@/*": ["./src/*"],
                    },
                    "outDir": "./compiled",
                },
                "include": [
                    "./phase_e_orchestrator_package_contract_runner.ts",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    compile_cmd = [
        str(TSC_PATH),
        "--pretty",
        "false",
        "-p",
        str(generated_tsconfig),
    ]
    compile_result = run_checked(compile_cmd, REPO_ROOT)
    (support_dir / "tsc.stdout.txt").write_text(compile_result.stdout, encoding="utf-8")
    (support_dir / "tsc.stderr.txt").write_text(compile_result.stderr, encoding="utf-8")

    generated_js_candidates = list(compiled_dir.rglob("phase_e_orchestrator_package_contract_runner.js"))
    if len(generated_js_candidates) != 1:
        raise RuntimeError(f"Expected exactly one compiled runner, found {len(generated_js_candidates)}.")
    generated_js = generated_js_candidates[0]

    alias_scope_dir = compiled_dir / "node_modules" / "@"
    alias_scope_dir.mkdir(parents=True, exist_ok=True)
    alias_lib_link = alias_scope_dir / "lib"
    if alias_lib_link.exists() or alias_lib_link.is_symlink():
        alias_lib_link.unlink()
    alias_lib_link.symlink_to(os.path.relpath(compiled_dir / "web" / "src" / "lib", alias_scope_dir))

    node_env = dict(os.environ)
    existing_node_path = node_env.get("NODE_PATH", "").strip()
    web_node_modules = str(WEB_ROOT / "node_modules")
    node_env["NODE_PATH"] = (
        web_node_modules
        if not existing_node_path
        else os.pathsep.join([web_node_modules, existing_node_path])
    )
    node_result = run_checked(
        ["node", str(generated_js), str(workspace_root), str(proof_store_path)],
        REPO_ROOT,
        env=node_env,
    )
    (support_dir / "node.stdout.json").write_text(node_result.stdout, encoding="utf-8")
    (support_dir / "node.stderr.txt").write_text(node_result.stderr, encoding="utf-8")

    proof_payload = json.loads(node_result.stdout)
    proof_payload.update(
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "ok",
            "proof_scope": "phase_e_orchestrator_package_contract_slice1",
            "verifier_script": str(REPO_ROOT / "tools" / "verify_phase_e_orchestrator_package_contract.py"),
            "support_dir": str(support_dir),
            "compiled_runner_path": str(generated_js),
            "proof_store_path": str(proof_store_path),
            "tsconfig_path": str(generated_tsconfig),
        }
    )

    proof_path = RUNTIME_ROOT / f"phase-e-orchestrator-package-contract-proof-{timestamp}.json"
    proof_path.write_text(json.dumps(proof_payload, indent=2) + "\n", encoding="utf-8")
    print(proof_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
