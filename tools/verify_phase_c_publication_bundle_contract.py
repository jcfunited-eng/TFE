#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine")
WEB_ROOT = REPO_ROOT / "web"
SRC_ROOT = WEB_ROOT / "src"
BACKUPS_ROOT = REPO_ROOT / "backups" / "runtime"
TSC_BIN = WEB_ROOT / "node_modules" / ".bin" / "tsc"
PUBLICATION_COMMIT_PATH = SRC_ROOT / "lib" / "step1" / "publication-commit.ts"
PUBLICATION_STATE_PATH = SRC_ROOT / "lib" / "publication-state.ts"
RUNTIME_PUBLICATION_BUNDLE_PATH = SRC_ROOT / "lib" / "runtime-publication-bundle.ts"


@dataclass(frozen=True)
class Paths:
    temp_root: Path
    runtime_tsconfig_path: Path
    emit_root: Path
    harness_path: Path
    harness_result_path: Path
    proof_store_path: Path
    artifact_path: Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_token(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_paths(now: datetime) -> Paths:
    token = timestamp_token(now)
    temp_root = Path(tempfile.mkdtemp(prefix=f"phase-c-bundle-contract-{token}-", dir=str(BACKUPS_ROOT)))
    return Paths(
        temp_root=temp_root,
        runtime_tsconfig_path=temp_root / "tsconfig.runtime.json",
        emit_root=temp_root / "emit",
        harness_path=temp_root / "run-proof.js",
        harness_result_path=temp_root / "harness-result.json",
        proof_store_path=temp_root / "step1-proof-store.json",
        artifact_path=BACKUPS_ROOT / f"phase-c-publication-bundle-contract-proof-{token}.json",
    )


def write_runtime_tsconfig(paths: Paths) -> None:
    config = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "commonjs",
            "moduleResolution": "node",
            "esModuleInterop": True,
            "strict": True,
            "skipLibCheck": True,
            "resolveJsonModule": True,
            "outDir": str(paths.emit_root),
            "rootDir": str(SRC_ROOT),
            "baseUrl": str(WEB_ROOT),
            "paths": {"@/*": ["./src/*"]},
            "types": ["node"],
            "typeRoots": [str(WEB_ROOT / "node_modules" / "@types")],
        },
        "include": [
            str(SRC_ROOT / "lib" / "runtime-db.ts"),
            str(SRC_ROOT / "lib" / "workspace-root.ts"),
            str(SRC_ROOT / "lib" / "publication-bundle-contract.ts"),
            str(SRC_ROOT / "lib" / "publication-state.ts"),
            str(SRC_ROOT / "lib" / "runtime-publication-bundle.ts"),
            str(SRC_ROOT / "lib" / "step1" / "schema.ts"),
            str(SRC_ROOT / "lib" / "step1" / "run-request.ts"),
            str(SRC_ROOT / "lib" / "step1" / "candidate-bundle.ts"),
            str(SRC_ROOT / "lib" / "step1" / "assessment-report.ts"),
            str(SRC_ROOT / "lib" / "step1" / "publication-commit.ts"),
            str(SRC_ROOT / "lib" / "step1" / "followup-ticket.ts"),
            str(SRC_ROOT / "lib" / "step1" / "orchestrator.ts"),
        ],
    }
    write_json(paths.runtime_tsconfig_path, config)


def run_tsc(project_path: Path) -> None:
    env = os.environ.copy()
    env["NODE_PATH"] = str(WEB_ROOT / "node_modules")
    subprocess.run(
        [str(TSC_BIN), "-p", str(project_path)],
        cwd=str(REPO_ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def write_runtime_aliases(paths: Paths) -> None:
    node_modules_root = paths.temp_root / "node_modules"
    for module_name in [
        "runtime-db",
        "workspace-root",
        "publication-bundle-contract",
        "publication-state",
        "runtime-publication-bundle",
    ]:
        write_text(
            node_modules_root / "@" / "lib" / f"{module_name}.js",
            f"""const path = require("node:path");
module.exports = require(path.join({json.dumps(str(paths.emit_root))}, "lib", "{module_name}.js"));
""",
        )


def build_source_contract_proof() -> dict[str, object]:
    publication_commit_source = PUBLICATION_COMMIT_PATH.read_text(encoding="utf-8")
    publication_state_source = PUBLICATION_STATE_PATH.read_text(encoding="utf-8")
    runtime_bundle_source = RUNTIME_PUBLICATION_BUNDLE_PATH.read_text(encoding="utf-8")

    if "../publication-bundle-contract" not in publication_commit_source:
        raise AssertionError("publication-commit.ts does not import the canonical publication bundle contract module.")
    if "buildCanonicalPublicationBundleWriteContract(" not in publication_commit_source:
        raise AssertionError("publication-commit.ts does not write through the canonical publication bundle contract layer.")
    if "@/lib/publication-bundle-contract" not in publication_state_source:
        raise AssertionError("publication-state.ts does not import the canonical publication bundle contract module.")
    if "resolveCanonicalPublicationBundleContract(" not in publication_state_source:
        raise AssertionError("publication-state.ts does not read through the canonical publication bundle contract layer.")
    if "@/lib/publication-bundle-contract" not in runtime_bundle_source:
        raise AssertionError("runtime-publication-bundle.ts does not import the canonical publication bundle contract module.")
    if "resolveCanonicalPublicationBundleContract(" not in runtime_bundle_source:
        raise AssertionError("runtime-publication-bundle.ts does not read through the canonical publication bundle contract layer.")

    return {
        "publication_commit_imports_contract": True,
        "publication_commit_writes_through_contract": True,
        "publication_state_reads_through_contract": True,
        "runtime_publication_bundle_reads_through_contract": True,
    }


def write_harness(paths: Paths, now: datetime) -> None:
    requested_at = iso_z(now)
    run_id = f"phase-c-contract-proof-{timestamp_token(now).lower()}"
    harness = f"""const fs = require("node:fs");
const path = require("node:path");

const repoRoot = {json.dumps(str(REPO_ROOT))};
const emitRoot = {json.dumps(str(paths.emit_root))};
const proofStorePath = {json.dumps(str(paths.proof_store_path))};
const harnessResultPath = {json.dumps(str(paths.harness_result_path))};

async function main() {{
  const schema = require(path.join(emitRoot, "lib", "step1", "schema.js"));
  const orchestrator = require(path.join(emitRoot, "lib", "step1", "orchestrator.js"));
  const publicationBundleContract = require(path.join(emitRoot, "lib", "publication-bundle-contract.js"));
  const publicationState = require(path.join(emitRoot, "lib", "publication-state.js"));
  const runtimePublicationBundle = require(path.join(emitRoot, "lib", "runtime-publication-bundle.js"));

  process.env.TFE_STEP1_ACTIVE_POINTER_SOURCE = "cutover";
  process.env.TFE_STEP1_FILE_PROOF_STORE_PATH = proofStorePath;
  process.env.TFE_STEP1_TARGET_ENVIRONMENT = "production";

  const result = await orchestrator.dispatchStep1Orchestrator(
    {{
      runId: {json.dumps(run_id)},
      normalizedPackageId: "normalized-package-demo",
      policySetId: "policy-set-demo",
      modelSetId: "model-set-demo",
      configSetId: "config-set-demo",
      bundleClass: "publication_candidate",
      dependencyClassificationRegister: {{
        normalized_package: "classified",
        policy_bundle: "classified",
        model_bundle: "classified",
        config_bundle: "classified"
      }},
      targetEnvironment: "production",
      requestedBy: "codex",
      requestedAtUtc: {json.dumps(requested_at)},
      assessmentRuleSetId: "assessment-rules-v1",
      followupDesiredStatus: "deferred",
      mode: "snapshot",
      triggerSource: "phase_c_publication_bundle_contract_readonly"
    }},
    {{
      executionMode: "readonly",
      proofStorePath,
      workspaceRoot: repoRoot
    }}
  );

  const store = await schema.readStep1ProofStore(proofStorePath);
  const runRow = store.runtime_refresh_runs.find((row) => row.run_id === result.runId) || null;
  const publicationBundleRow = schema.selectStep1PublicationBundleRow(store, result.publicationBundleId);
  const activePointer = schema.selectStep1ActivePublicationPointerRow(store, "production");
  const manifestArtifact = await publicationBundleContract.readCanonicalPublicationBundleManifestArtifact(
    result.publicationManifestPath
  );
  const rowManifestMatch = publicationBundleContract.publicationBundleRowMatchesManifestContract({{
    row: publicationBundleRow,
    manifest: manifestArtifact.manifest,
    manifestPath: result.publicationManifestPath,
    manifestDigestSha256: manifestArtifact.manifestDigestSha256
  }});
  const contractResolution = await publicationBundleContract.resolveCanonicalPublicationBundleContract({{
    targetEnvironment: "production",
    proofStorePath
  }});
  const investorResolution = await runtimePublicationBundle.resolveInvestorActivePublicationBundleId();
  const servingMeta = await runtimePublicationBundle.loadServingRuntimePublicationBundleMeta();
  const canonicalState = await publicationState.loadCanonicalPublicationState({{
    snapshot: {{
      available: true,
      runId: result.runId,
      generatedAtUtc: null
    }},
    quote: {{
      available: true,
      runId: result.runId
    }}
  }});
  const legacyRuntimeValidityMirror = runRow
    ? {{
        validation_status: Object.prototype.hasOwnProperty.call(runRow, "validation_status") ? runRow.validation_status ?? null : null,
        snapshot_publication_id: Object.prototype.hasOwnProperty.call(runRow, "snapshot_publication_id") ? runRow.snapshot_publication_id ?? null : null,
        quote_publication_id: Object.prototype.hasOwnProperty.call(runRow, "quote_publication_id") ? runRow.quote_publication_id ?? null : null,
        quote_binding_status: Object.prototype.hasOwnProperty.call(runRow, "quote_binding_status") ? runRow.quote_binding_status ?? null : null,
        is_active_publication: Object.prototype.hasOwnProperty.call(runRow, "is_active_publication") ? runRow.is_active_publication ?? null : null
      }}
    : null;

  fs.writeFileSync(
    harnessResultPath,
    JSON.stringify(
      {{
        result,
        runRow,
        publicationBundleRow,
        activePointer,
        manifestArtifact,
        rowManifestMatch,
        contractResolution,
        investorResolution,
        servingMeta,
        canonicalState,
        legacyRuntimeValidityMirror
      }},
      null,
      2
    ) + "\\n"
  );
}}

main().catch((error) => {{
  fs.writeFileSync(
    harnessResultPath,
    JSON.stringify({{
      error: error instanceof Error ? error.message : String(error)
    }}, null, 2) + "\\n"
  );
  process.exitCode = 1;
}});
"""
    write_text(paths.harness_path, harness)


def run_harness(paths: Paths) -> dict[str, object]:
    env = os.environ.copy()
    env["NODE_PATH"] = os.pathsep.join([str(paths.temp_root / "node_modules"), str(WEB_ROOT / "node_modules")])
    subprocess.run(
        ["node", str(paths.harness_path)],
        cwd=str(REPO_ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(paths.harness_result_path.read_text(encoding="utf-8"))


def build_readonly_execution_proof(harness_result: dict[str, object], proof_store_path: Path) -> dict[str, object]:
    if "error" in harness_result:
        raise AssertionError(f"Phase C publication bundle harness failed: {harness_result['error']}")

    result = harness_result.get("result")
    run_row = harness_result.get("runRow")
    publication_bundle_row = harness_result.get("publicationBundleRow")
    active_pointer = harness_result.get("activePointer")
    manifest_artifact = harness_result.get("manifestArtifact")
    row_manifest_match = harness_result.get("rowManifestMatch")
    contract_resolution = harness_result.get("contractResolution")
    investor_resolution = harness_result.get("investorResolution")
    serving_meta = harness_result.get("servingMeta")
    canonical_state = harness_result.get("canonicalState")
    legacy_runtime_validity_mirror = harness_result.get("legacyRuntimeValidityMirror")

    for name, value in [
        ("result", result),
        ("runRow", run_row),
        ("publicationBundleRow", publication_bundle_row),
        ("activePointer", active_pointer),
        ("manifestArtifact", manifest_artifact),
        ("rowManifestMatch", row_manifest_match),
        ("contractResolution", contract_resolution),
        ("investorResolution", investor_resolution),
        ("servingMeta", serving_meta),
        ("canonicalState", canonical_state),
        ("legacyRuntimeValidityMirror", legacy_runtime_validity_mirror),
    ]:
        if not isinstance(value, dict):
            raise AssertionError(f"Harness did not capture {name}.")

    if result.get("executionPath") != "step1_orchestrator":
        raise AssertionError("Readonly harness did not execute through the Step 1 orchestrator.")
    if result.get("followupStatus") != "deferred":
        raise AssertionError("Readonly harness did not complete through a durable deferred followup ticket.")
    if row_manifest_match.get("matches") is not True:
        raise AssertionError(f"publication_bundle row and manifest fields do not match exactly: {row_manifest_match.get('mismatches')}")
    if publication_bundle_row.get("manifest_digest_sha256") != manifest_artifact.get("manifestDigestSha256"):
        raise AssertionError("manifest_digest_sha256 does not match the persisted manifest bytes digest.")
    if active_pointer.get("publication_bundle_id") != publication_bundle_row.get("publication_bundle_id"):
        raise AssertionError("active_publication_pointer did not resolve exactly one publication_bundle for the target environment.")
    if contract_resolution.get("publicationBundleId") != publication_bundle_row.get("publication_bundle_id"):
        raise AssertionError("Canonical publication bundle contract did not resolve the active pointer to the committed publication_bundle_id.")
    if investor_resolution.get("publicationBundleId") != publication_bundle_row.get("publication_bundle_id"):
        raise AssertionError("Investor-serving resolution did not return the active publication_bundle_id.")
    if serving_meta.get("snapshotPublicationId") != publication_bundle_row.get("publication_bundle_id"):
        raise AssertionError("Serving metadata did not resolve the same publication_bundle_id.")
    if canonical_state.get("snapshotPublicationId") != publication_bundle_row.get("publication_bundle_id"):
        raise AssertionError("Canonical publication state did not resolve the same publication_bundle_id.")
    if canonical_state.get("candidateValid") is not True:
        raise AssertionError("Canonical publication state did not derive validity from publication_bundles plus assessment_reports.")
    if canonical_state.get("activationState") != "activated" or canonical_state.get("servingState") != "allowed":
        raise AssertionError("Canonical publication state did not preserve pointer-owned activation/serving truth.")
    if serving_meta.get("activeRuntimeBundleValid") is not True:
        raise AssertionError("Investor-serving metadata did not preserve publication_bundles plus assessment_reports as validity authority.")

    if legacy_runtime_validity_mirror.get("validation_status") is not None:
        raise AssertionError("Legacy runtime_refresh_runs.validation_status unexpectedly became publication-validity authority again.")
    if legacy_runtime_validity_mirror.get("snapshot_publication_id") is not None:
        raise AssertionError("Legacy runtime_refresh_runs.snapshot_publication_id unexpectedly became publication-validity authority again.")
    if legacy_runtime_validity_mirror.get("quote_publication_id") is not None:
        raise AssertionError("Legacy runtime_refresh_runs.quote_publication_id unexpectedly became publication-validity authority again.")
    if legacy_runtime_validity_mirror.get("quote_binding_status") is not None:
        raise AssertionError("Legacy runtime_refresh_runs.quote_binding_status unexpectedly became publication-validity authority again.")
    if legacy_runtime_validity_mirror.get("is_active_publication") not in {None, False}:
        raise AssertionError("Legacy runtime_refresh_runs.is_active_publication unexpectedly became publication-validity authority again.")

    return {
        "proof_store_path": str(proof_store_path),
        "run_id": result.get("runId"),
        "followup_status": result.get("followupStatus"),
        "publication_bundle_row_manifest_match": True,
        "manifest_digest_matches_persisted_bytes": True,
        "active_pointer_resolves_one_publication_bundle": True,
        "investor_serving_resolution_matches_active_pointer": True,
        "legacy_runtime_validity_fields_are_non_authoritative": True,
        "publication_bundle_id": publication_bundle_row.get("publication_bundle_id"),
        "publication_manifest_path": result.get("publicationManifestPath"),
        "manifest_digest_sha256": publication_bundle_row.get("manifest_digest_sha256"),
        "persisted_manifest_bytes_digest_sha256": manifest_artifact.get("manifestDigestSha256"),
        "active_pointer_publication_bundle_id": active_pointer.get("publication_bundle_id"),
        "contract_resolved_publication_bundle_id": contract_resolution.get("publicationBundleId"),
        "investor_resolved_publication_bundle_id": investor_resolution.get("publicationBundleId"),
        "serving_resolved_publication_bundle_id": serving_meta.get("snapshotPublicationId"),
        "canonical_state_candidate_valid": canonical_state.get("candidateValid"),
        "canonical_state_activation_state": canonical_state.get("activationState"),
        "canonical_state_serving_state": canonical_state.get("servingState"),
        "legacy_runtime_validity_mirror": legacy_runtime_validity_mirror,
    }


def build_artifact(paths: Paths, now: datetime) -> dict[str, object]:
    write_runtime_tsconfig(paths)
    run_tsc(paths.runtime_tsconfig_path)
    write_runtime_aliases(paths)
    write_harness(paths, now)
    source_contract_proof = build_source_contract_proof()
    harness_result = run_harness(paths)
    readonly_execution_proof = build_readonly_execution_proof(harness_result, paths.proof_store_path)
    return {
        "proof_generated_at_utc": iso_z(utc_now()),
        "proof_status": "ok",
        "proof_scope": "phase_c_publication_bundle_contract_readonly",
        "source_contract_proof": source_contract_proof,
        "readonly_execution_proof": readonly_execution_proof,
    }


def main() -> int:
    now = utc_now()
    paths = build_paths(now)
    try:
        artifact = build_artifact(paths, now)
        write_json(paths.artifact_path, artifact)
    except Exception as error:  # noqa: BLE001
        write_json(
            paths.artifact_path,
            {
                "proof_generated_at_utc": iso_z(utc_now()),
                "proof_status": "error",
                "proof_scope": "phase_c_publication_bundle_contract_readonly",
                "error": str(error),
            },
        )
        print(str(paths.artifact_path))
        return 1

    print(str(paths.artifact_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
