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
    support_dir = RUNTIME_ROOT / f"phase-e-package-contract-proof-{timestamp}"
    support_dir.mkdir(parents=True, exist_ok=True)

    generated_ts = support_dir / "phase_e_package_contract_runner.ts"
    workspace_root = support_dir / "workspace"
    proof_store_path = support_dir / "proof-store.json"

    run_request_module = rel_module(generated_ts, REPO_ROOT / "web" / "src" / "lib" / "step1" / "run-request.ts")
    candidate_bundle_module = rel_module(generated_ts, REPO_ROOT / "web" / "src" / "lib" / "step1" / "candidate-bundle.ts")
    assessment_report_module = rel_module(generated_ts, REPO_ROOT / "web" / "src" / "lib" / "step1" / "assessment-report.ts")
    package_contract_module = rel_module(generated_ts, REPO_ROOT / "web" / "src" / "lib" / "step1" / "package-contract.ts")
    schema_module = rel_module(generated_ts, REPO_ROOT / "web" / "src" / "lib" / "step1" / "schema.ts")

    generated_ts.write_text(
        textwrap.dedent(
            f"""
            import {{ readFile }} from "node:fs/promises";

            import {{ createStep1RunRequest, type Step1RunRequestInput }} from "{run_request_module}";
            import {{ createCandidateBundleRecord }} from "{candidate_bundle_module}";
            import {{ createAssessmentReportRecord }} from "{assessment_report_module}";
            import {{ buildNormalizedPackageManifest, buildSourcePackageManifest }} from "{package_contract_module}";
            import {{
              createFileProofStep1Persistence,
              parseStoredStep1CandidateBundleManifest,
              parseStoredStep1AssessmentReportArtifact,
              sha256Text,
              type Step1SourcePackageIdentityRecord,
            }} from "{schema_module}";

            async function main(): Promise<void> {{
              const workspaceRoot = process.argv[2];
              const proofStorePath = process.argv[3];
              if (!workspaceRoot || !proofStorePath) {{
                throw new Error("workspaceRoot and proofStorePath are required.");
              }}

              const sourcePackageIdentities: Step1RunRequestInput["sourcePackageIdentities"] = [
                {{
                  sourcePackageId: "source_package_v1_vendor_prices_primary_20260316t080000z",
                  sourceIdentity: "vendor_prices_primary",
                  acquisitionTimestampUtc: "2026-03-16T08:00:00Z",
                  sourceClass: "tier1_vendor_feed",
                  rawPayloadReference: "s3://tfe-source/vendor_prices_primary/2026-03-16T08:00:00Z.json",
                  integrityStatus: "complete",
                }},
                {{
                  sourcePackageId: "source_package_v1_vendor_reference_primary_20260316t080500z",
                  sourceIdentity: "vendor_reference_primary",
                  acquisitionTimestampUtc: "2026-03-16T08:05:00Z",
                  sourceClass: "tier1_vendor_feed",
                  rawPayloadReference: "s3://tfe-source/vendor_reference_primary/2026-03-16T08:05:00Z.json",
                  integrityStatus: "complete",
                }},
              ];

              const requestInput: Step1RunRequestInput = {{
                runId: "phase-e-package-contract-proof-run",
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
                requestedBy: "codex",
                requestedAtUtc: "2026-03-16T08:10:00Z",
                mode: "step1_cutover",
                triggerSource: "phase_e_package_contract_proof",
              }};

              const persistence = createFileProofStep1Persistence(proofStorePath);
              const requestResult = await createStep1RunRequest(requestInput, {{
                persistence,
                workspaceRoot,
              }});
              const candidateResult = await createCandidateBundleRecord(
                {{
                  runId: requestResult.requestRecord.run_id,
                  requestArtifactPath: requestResult.requestArtifactPath,
                  requestedRunMode: "step1_cutover",
                }},
                {{
                  persistence,
                  workspaceRoot,
                }},
              );
              const assessmentResult = await createAssessmentReportRecord(
                {{
                  runId: requestResult.requestRecord.run_id,
                  candidateBundleManifestPath: candidateResult.manifestPath,
                  assessmentRuleSetId: "assessment_rule_set_v1_publication_safety",
                }},
                {{
                  persistence,
                  workspaceRoot,
                }},
              );

              const normalizedManifestRaw = await readFile(candidateResult.manifest.normalized_package_manifest_path, "utf8");
              const normalizedManifest = JSON.parse(normalizedManifestRaw) as Record<string, unknown>;
              const candidateManifestRaw = await readFile(candidateResult.manifestPath, "utf8");
              const candidateManifest = parseStoredStep1CandidateBundleManifest(JSON.parse(candidateManifestRaw));
              if (!candidateManifest) {{
                throw new Error("candidate manifest parse failed");
              }}
              const assessmentReportRaw = await readFile(assessmentResult.reportPath, "utf8");
              const assessmentReport = parseStoredStep1AssessmentReportArtifact(JSON.parse(assessmentReportRaw));
              if (!assessmentReport) {{
                throw new Error("assessment report parse failed");
              }}

              const sourcePackageManifestRefs = candidateManifest.assessment_artifact_references
                .filter((entry) => entry.artifact_kind === "source_package_manifest" && entry.artifact_path && entry.artifact_digest_sha256);
              const sourcePackageManifestPayloads = await Promise.all(
                sourcePackageManifestRefs.map(async (entry) => {{
                  const raw = await readFile(String(entry.artifact_path), "utf8");
                  const manifest = JSON.parse(raw) as Record<string, unknown>;
                  return {{
                    manifest: buildSourcePackageManifest({{
                      source_package_id: String(manifest.source_package_id),
                      source_identity: String(manifest.source_identity),
                      acquisition_timestamp_utc: String(manifest.acquisition_timestamp_utc),
                      source_class: String(manifest.source_class),
                      raw_payload_reference: String(manifest.raw_payload_reference),
                      integrity_status: String(manifest.integrity_status),
                    }} as Step1SourcePackageIdentityRecord),
                    manifestPath: String(entry.artifact_path),
                    manifestDigestSha256: String(entry.artifact_digest_sha256),
                  }};
                }}),
              );

              const deterministicNormalizedManifest = buildNormalizedPackageManifest({{
                normalizedPackageId: candidateManifest.normalized_package_id,
                sourcePackageManifests: sourcePackageManifestPayloads,
              }});

              const normalizedPackageManifestRef = candidateManifest.assessment_artifact_references.find(
                (entry) => entry.artifact_kind === "normalized_package_manifest",
              );
              const normalizedPackageIdentityRef = candidateManifest.assessment_artifact_references.find(
                (entry) => entry.artifact_kind === "normalized_package_identity",
              );
              const sourcePackageManifestEvidence = assessmentReport.evidence_references.filter(
                (entry) => entry.evidence_kind === "source_package_manifest",
              );
              const normalizedPackageManifestEvidence = assessmentReport.evidence_references.find(
                (entry) => entry.evidence_kind === "normalized_package_manifest",
              );
              const normalizedPackageIdentityEvidence = assessmentReport.evidence_references.find(
                (entry) => entry.evidence_kind === "normalized_package_identity",
              );

              const expectedSourcePackageIds = (requestResult.requestRecord.source_package_identities ?? [])
                .map((entry) => entry.source_package_id)
                .sort();
              const observedSourcePackageIds = sourcePackageManifestEvidence.map((entry) => entry.evidence_id).sort();

              const proof = {{
                normalized_package_manifest_exists_and_is_versioned:
                  normalizedManifest.normalized_package_manifest_version === 1,
                normalized_package_manifest_cites_exact_source_package_identities:
                  JSON.stringify(normalizedManifest.source_package_identities) === JSON.stringify(candidateManifest.source_package_identities),
                deterministic_identity_stable_for_equivalent_manifest_input:
                  deterministicNormalizedManifest.normalized_package_manifest_id === candidateManifest.normalized_package_manifest_id,
                candidate_bundle_manifest_cites_exact_normalized_package_identity:
                  candidateManifest.normalized_package_id === requestResult.requestRecord.normalized_package_id
                  && Boolean(normalizedPackageManifestRef?.artifact_path)
                  && normalizedPackageManifestRef?.artifact_id === candidateManifest.normalized_package_manifest_id,
                assessment_evidence_cites_same_normalized_package_identity_and_exact_source_package_identities:
                  normalizedPackageIdentityEvidence?.evidence_id === candidateManifest.normalized_package_id
                  && normalizedPackageManifestEvidence?.evidence_id === candidateManifest.normalized_package_manifest_id
                  && JSON.stringify(observedSourcePackageIds) === JSON.stringify(expectedSourcePackageIds),
                source_package_manifests_exist_and_are_versioned:
                  sourcePackageManifestPayloads.every((entry) => entry.manifest.source_package_manifest_version === 1),
                request_artifact_path: requestResult.requestArtifactPath,
                candidate_bundle_manifest_path: candidateResult.manifestPath,
                normalized_package_manifest_path: candidateResult.manifest.normalized_package_manifest_path,
                assessment_report_path: assessmentResult.reportPath,
                candidate_bundle_manifest: candidateManifest,
                normalized_package_manifest: normalizedManifest,
                assessment_evidence_references: assessmentReport.evidence_references,
                source_package_manifest_paths: sourcePackageManifestRefs.map((entry) => entry.artifact_path),
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

    compile_cmd = [
        str(TSC_PATH),
        "--pretty",
        "false",
        "--skipLibCheck",
        "--target",
        "ES2022",
        "--module",
        "commonjs",
        "--moduleResolution",
        "node",
        "--esModuleInterop",
        "--resolveJsonModule",
        "--outDir",
        str(support_dir / "compiled"),
        str(generated_ts),
    ]
    compile_result = run_checked(compile_cmd, REPO_ROOT)
    (support_dir / "tsc.stdout.txt").write_text(compile_result.stdout, encoding="utf-8")
    (support_dir / "tsc.stderr.txt").write_text(compile_result.stderr, encoding="utf-8")

    generated_js_candidates = list((support_dir / "compiled").rglob("phase_e_package_contract_runner.js"))
    if len(generated_js_candidates) != 1:
        raise RuntimeError(f"Expected exactly one compiled runner, found {len(generated_js_candidates)}.")
    generated_js = generated_js_candidates[0]

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
            "proof_scope": "phase_e_package_contract_slice1",
            "verifier_script": str(REPO_ROOT / "tools" / "verify_phase_e_package_contract.py"),
            "support_dir": str(support_dir),
            "compiled_runner_path": str(generated_js),
            "proof_store_path": str(proof_store_path),
        }
    )

    proof_path = RUNTIME_ROOT / f"phase-e-package-contract-proof-{timestamp}.json"
    proof_path.write_text(json.dumps(proof_payload, indent=2) + "\n", encoding="utf-8")
    print(proof_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
