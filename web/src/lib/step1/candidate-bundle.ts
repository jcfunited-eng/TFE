import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { resolveWorkspaceRoot } from "../workspace-root";
import {
  buildNormalizedPackageManifest,
  buildPhaseEPackageArtifactReferences,
  writeStep1PackageContractArtifacts,
} from "./package-contract";
import {
  createCandidateBuildCompletedPhaseRow,
  createCandidateBundleRow,
  deterministicTimestampFromDigest,
  parseStoredStep1RunRequestRecord,
  resolveStep1CandidateBundleManifestPath,
  sha256Text,
  stableJsonStringify,
  type Step1CandidateBundleManifest,
  type Step1CandidateBundlePersistence,
  type Step1SourcePackageIdentityRecord,
} from "./schema";

export type CandidateBundleRecordInput = {
  runId: string;
  requestArtifactPath: string;
  requestedRunMode: string;
};

export type CandidateBundleRecordResult = {
  manifest: Step1CandidateBundleManifest;
  manifestPath: string;
  manifestDigestSha256: string;
  candidateBundleRow: ReturnType<typeof createCandidateBundleRow>;
  phaseRow: ReturnType<typeof createCandidateBuildCompletedPhaseRow>;
};

export class CandidateBundleRecordError extends Error {
  code:
    | "candidate_input_missing"
    | "candidate_build_failure"
    | "candidate_manifest_invalid"
    | "state_persistence_failure";
  detail: string;
  runId: string;

  constructor(params: {
    code:
      | "candidate_input_missing"
      | "candidate_build_failure"
      | "candidate_manifest_invalid"
      | "state_persistence_failure";
    detail: string;
    runId: string;
  }) {
    super(
      `Candidate build failed. run_id=${params.runId}; code=${params.code}; `
      + `detail=${params.detail}; no assessment or publication will run.`,
    );
    this.name = "CandidateBundleRecordError";
    this.code = params.code;
    this.detail = params.detail;
    this.runId = params.runId;
  }
}

type CreateCandidateBundleRecordOptions = {
  persistence: Step1CandidateBundlePersistence;
  workspaceRoot?: string;
};

function requireText(value: unknown, fieldName: string, runId: string): string {
  const text = String(value ?? "").trim();
  if (!text) {
    throw new CandidateBundleRecordError({
      code: "candidate_input_missing",
      detail: `${fieldName} must be a non-empty string.`,
      runId,
    });
  }
  return text;
}

function requireSourcePackageIdentities(
  value: Step1SourcePackageIdentityRecord[] | undefined,
  runId: string,
): Step1SourcePackageIdentityRecord[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new CandidateBundleRecordError({
      code: "candidate_input_missing",
      detail: "request_artifact_path is missing exact source_package_identities required by the Phase E package contract.",
      runId,
    });
  }
  return value;
}

function buildCandidateManifest(params: {
  normalizedPackageId: string;
  normalizedPackageManifestId: string;
  normalizedPackageManifestPath: string;
  normalizedPackageManifestDigestSha256: string;
  policySetId: string;
  modelSetId: string;
  configSetId: string;
  bundleClass: string;
  requestedRunMode: string;
  targetEnvironment: string;
  dependencyClassificationRegister: Record<string, unknown>;
  sourcePackageIdentities: Step1SourcePackageIdentityRecord[];
  phaseEPackageArtifactReferences: Step1CandidateBundleManifest["assessment_artifact_references"];
}): Step1CandidateBundleManifest {
  const manifestInput = {
    normalized_package_id: params.normalizedPackageId,
    normalized_package_manifest_id: params.normalizedPackageManifestId,
    policy_set_id: params.policySetId,
    model_set_id: params.modelSetId,
    config_set_id: params.configSetId,
    bundle_class: params.bundleClass,
    requested_run_mode: params.requestedRunMode,
    target_environment: params.targetEnvironment,
    source_package_identities: params.sourcePackageIdentities,
    dependency_classification_register: params.dependencyClassificationRegister,
  };
  const candidateInputDigestSha256 = sha256Text(stableJsonStringify(manifestInput));

  // The timestamp is derived from canonical inputs so equivalent builds stay byte-identical across runs.
  return {
    candidate_bundle_id: `candidate_bundle_v1_${candidateInputDigestSha256.slice(0, 24)}`,
    normalized_package_id: params.normalizedPackageId,
    policy_set_id: params.policySetId,
    model_set_id: params.modelSetId,
    config_set_id: params.configSetId,
    bundle_class: params.bundleClass,
    normalized_package_manifest_id: params.normalizedPackageManifestId,
    normalized_package_manifest_path: params.normalizedPackageManifestPath,
    normalized_package_manifest_digest_sha256: params.normalizedPackageManifestDigestSha256,
    source_package_identities: params.sourcePackageIdentities,
    requested_run_mode: params.requestedRunMode,
    deterministic_build_timestamp_utc: deterministicTimestampFromDigest(candidateInputDigestSha256),
    target_environment: params.targetEnvironment,
    dependency_classification_register: params.dependencyClassificationRegister,
    assessment_artifact_references: params.phaseEPackageArtifactReferences,
  };
}

async function loadRequestArtifact(
  requestArtifactPath: string,
  runId: string,
): Promise<ReturnType<typeof parseStoredStep1RunRequestRecord>> {
  try {
    const raw = await readFile(requestArtifactPath, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    return parseStoredStep1RunRequestRecord(parsed);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unable to read request artifact.";
    throw new CandidateBundleRecordError({
      code: "candidate_input_missing",
      detail: `request_artifact_path read failed: ${detail}`,
      runId,
    });
  }
}

export async function createCandidateBundleRecord(
  input: CandidateBundleRecordInput,
  options: CreateCandidateBundleRecordOptions,
): Promise<CandidateBundleRecordResult> {
  const runId = requireText(input.runId, "run_id", input.runId || "pending");
  const requestArtifactPath = requireText(input.requestArtifactPath, "request_artifact_path", runId);
  const requestedRunMode = requireText(input.requestedRunMode, "requested_run_mode", runId);
  const workspaceRoot = options.workspaceRoot ?? resolveWorkspaceRoot();
  const persistence = options.persistence;
  const requestRecord = await loadRequestArtifact(requestArtifactPath, runId);

  if (!requestRecord) {
    throw new CandidateBundleRecordError({
      code: "candidate_manifest_invalid",
      detail: "request_artifact_path does not contain a valid Step 1 request record.",
      runId,
    });
  }

  if (requestRecord.run_id !== runId) {
    throw new CandidateBundleRecordError({
      code: "candidate_manifest_invalid",
      detail: `request_artifact_path run_id=${requestRecord.run_id} does not match input run_id=${runId}.`,
      runId,
    });
  }

  const sourcePackageIdentities = requireSourcePackageIdentities(requestRecord.source_package_identities, runId);
  const packageArtifacts = await writeStep1PackageContractArtifacts({
    workspaceRoot,
    runId,
    normalizedPackageId: requestRecord.normalized_package_id,
    sourcePackageIdentities,
  });
  const normalizedPackageManifestIdentity = buildNormalizedPackageManifest({
    normalizedPackageId: requestRecord.normalized_package_id,
    sourcePackageManifests: packageArtifacts.sourcePackageManifests,
  });
  const phaseEPackageArtifactReferences = buildPhaseEPackageArtifactReferences({
    normalizedPackageId: requestRecord.normalized_package_id,
    normalizedPackageManifest: packageArtifacts.normalizedPackageManifest,
    sourcePackageManifests: packageArtifacts.sourcePackageManifests,
    dependencyClassificationRegister: requestRecord.dependency_classification_register,
    candidateInputDigestSha256: sha256Text(
      stableJsonStringify({
        normalized_package_id: requestRecord.normalized_package_id,
        normalized_package_manifest_id: normalizedPackageManifestIdentity.normalized_package_manifest_id,
        policy_set_id: requestRecord.policy_set_id,
        model_set_id: requestRecord.model_set_id,
        config_set_id: requestRecord.config_set_id,
        bundle_class: requestRecord.bundle_class,
        requested_run_mode: requestedRunMode,
        target_environment: requestRecord.target_environment,
        source_package_identities: sourcePackageIdentities,
        dependency_classification_register: requestRecord.dependency_classification_register,
      }),
    ),
  });
  const manifest = buildCandidateManifest({
    normalizedPackageId: requestRecord.normalized_package_id,
    normalizedPackageManifestId: packageArtifacts.normalizedPackageManifest.manifest.normalized_package_manifest_id,
    normalizedPackageManifestPath: packageArtifacts.normalizedPackageManifest.manifestPath,
    normalizedPackageManifestDigestSha256: packageArtifacts.normalizedPackageManifest.manifestDigestSha256,
    policySetId: requestRecord.policy_set_id,
    modelSetId: requestRecord.model_set_id,
    configSetId: requestRecord.config_set_id,
    bundleClass: requestRecord.bundle_class,
    requestedRunMode,
    targetEnvironment: requestRecord.target_environment,
    dependencyClassificationRegister: requestRecord.dependency_classification_register,
    sourcePackageIdentities,
    phaseEPackageArtifactReferences,
  });
  const manifestDigestSha256 = sha256Text(stableJsonStringify(manifest));
  const manifestPath = resolveStep1CandidateBundleManifestPath(workspaceRoot, runId);
  const candidateBundleRow = createCandidateBundleRow({
    runId,
    requestArtifactPath,
    manifestPath,
    manifestDigestSha256,
    createdAtUtc: requestRecord.requested_at_utc,
    manifest,
  });
  const phaseRow = createCandidateBuildCompletedPhaseRow({
    runId,
    startedAtUtc: requestRecord.requested_at_utc,
    completedAtUtc: requestRecord.requested_at_utc,
    requestArtifactPath,
    requestRecord,
    manifestPath,
    candidateBundleId: manifest.candidate_bundle_id,
    manifestDigestSha256,
    normalizedPackageManifestId: manifest.normalized_package_manifest_id,
    normalizedPackageManifestPath: manifest.normalized_package_manifest_path,
    normalizedPackageManifestDigestSha256: manifest.normalized_package_manifest_digest_sha256,
    sourcePackageIds: manifest.source_package_identities.map((entry) => entry.source_package_id),
  });

  try {
    await mkdir(path.dirname(manifestPath), { recursive: true });
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
    await persistence.ensureReady();
    await persistence.writeCandidateBundleRow(candidateBundleRow);
    await persistence.writePhaseRow(phaseRow);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown candidate bundle persistence failure.";
    throw new CandidateBundleRecordError({
      code: "state_persistence_failure",
      detail,
      runId,
    });
  }

  return {
    manifest,
    manifestPath,
    manifestDigestSha256,
    candidateBundleRow,
    phaseRow,
  };
}
