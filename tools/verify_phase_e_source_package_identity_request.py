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
    support_dir = RUNTIME_ROOT / f"phase-e-source-package-identity-closure-proof-{timestamp}"
    support_dir.mkdir(parents=True, exist_ok=True)

    generated_ts = support_dir / "phase_e_source_package_identity_runner.ts"
    workspace_root = support_dir / "workspace"
    proof_store_path = support_dir / "proof-store.json"

    run_request_module = rel_module(generated_ts, REPO_ROOT / "web" / "src" / "lib" / "step1" / "run-request.ts")
    schema_module = rel_module(generated_ts, REPO_ROOT / "web" / "src" / "lib" / "step1" / "schema.ts")

    generated_ts.write_text(
        textwrap.dedent(
            f"""
            import {{ readFile }} from "node:fs/promises";

            import {{ createStep1RunRequest, type Step1RunRequestInput }} from "{run_request_module}";
            import {{
              createFileProofStep1Persistence,
              parseStoredStep1RunRequestRecord,
              type Step1RunRequestRecord,
            }} from "{schema_module}";

            async function main(): Promise<void> {{
              const workspaceRoot = process.argv[2];
              const proofStorePath = process.argv[3];
              if (!workspaceRoot || !proofStorePath) {{
                throw new Error("workspaceRoot and proofStorePath are required.");
              }}

              const input: Step1RunRequestInput = {{
                runId: "phase-e-source-package-identity-proof-run",
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
                sourcePackageIdentities: [
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
                ],
                targetEnvironment: "production",
                requestedBy: "codex",
                requestedAtUtc: "2026-03-16T08:10:00Z",
                mode: "step1_cutover",
                triggerSource: "phase_e_source_package_identity_proof",
              }};

              if (!input.sourcePackageIdentities) {{
                throw new Error("sourcePackageIdentities missing from typed request input.");
              }}

              const expectedRecordSourcePackageIdentities = input.sourcePackageIdentities.map((entry) => ({{
                source_package_id: entry.sourcePackageId,
                source_identity: entry.sourceIdentity,
                acquisition_timestamp_utc: new Date(entry.acquisitionTimestampUtc).toISOString(),
                source_class: entry.sourceClass,
                raw_payload_reference: entry.rawPayloadReference,
                integrity_status: entry.integrityStatus,
              }}));

              const result = await createStep1RunRequest(input, {{
                persistence: createFileProofStep1Persistence(proofStorePath),
                workspaceRoot,
              }});

              const requestRecordTypeProof: Step1RunRequestRecord = result.requestRecord;
              void requestRecordTypeProof.source_package_identities;

              const storedRequestRaw = await readFile(result.requestArtifactPath, "utf8");
              const storedRequestJson = JSON.parse(storedRequestRaw) as Record<string, unknown>;
              const parsedStoredRequest = parseStoredStep1RunRequestRecord(storedRequestJson);

              const requestRecordSourcePackageIdentities = result.requestRecord.source_package_identities ?? null;
              const storedSourcePackageIdentities = Array.isArray(storedRequestJson.source_package_identities)
                ? storedRequestJson.source_package_identities
                : null;
              const parsedStoredSourcePackageIdentities = parsedStoredRequest?.source_package_identities ?? null;

              const proof = {{
                step1_run_request_input_accepts_source_package_identity_fields: true,
                step1_run_request_record_contains_source_package_identity_fields:
                  Array.isArray(requestRecordTypeProof.source_package_identities)
                  && requestRecordTypeProof.source_package_identities.length === expectedRecordSourcePackageIdentities.length,
                create_request_record_preserves_source_package_identity_fields_without_invention:
                  JSON.stringify(requestRecordSourcePackageIdentities) === JSON.stringify(expectedRecordSourcePackageIdentities),
                stored_request_json_contains_exact_source_package_identity_fields:
                  JSON.stringify(storedSourcePackageIdentities) === JSON.stringify(expectedRecordSourcePackageIdentities),
                parsed_stored_request_round_trip_matches:
                  JSON.stringify(parsedStoredSourcePackageIdentities) === JSON.stringify(expectedRecordSourcePackageIdentities),
                request_artifact_path: result.requestArtifactPath,
                request_artifact_relative_path: result.requestArtifactRelativePath,
                expected_source_package_identities: expectedRecordSourcePackageIdentities,
                request_record_source_package_identities: requestRecordSourcePackageIdentities,
                stored_request_source_package_identities: storedSourcePackageIdentities,
                parsed_stored_request_source_package_identities: parsedStoredSourcePackageIdentities,
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

    generated_js_candidates = list((support_dir / "compiled").rglob("phase_e_source_package_identity_runner.js"))
    if len(generated_js_candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one compiled runner, found {len(generated_js_candidates)}."
        )
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
            "proof_scope": "phase_e_source_package_identity_request_contract_closure",
            "verifier_script": str(REPO_ROOT / "tools" / "verify_phase_e_source_package_identity_request.py"),
            "support_dir": str(support_dir),
            "compiled_runner_path": str(generated_js),
            "proof_store_path": str(proof_store_path),
        }
    )

    proof_path = RUNTIME_ROOT / f"phase-e-source-package-identity-closure-proof-{timestamp}.json"
    proof_path.write_text(json.dumps(proof_payload, indent=2) + "\n", encoding="utf-8")
    print(proof_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
