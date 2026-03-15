import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { resolveWorkspaceRoot } from "../workspace-root";
import {
  createCandidateBuildCompletedPhaseRow,
  createCandidateBundleRow,
  deterministicTimestampFromDigest,
  parseStoredStep1RunRequestRecord,
  resolveStep1CandidateBundleManifestPath,
  sha256Text,
  stableJsonStringify,
  type Step1AssessmentArtifactReference,
  type Step1CandidateBundleManifest,
  type Step1CandidateBundlePersistence,
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

function buildAssessmentArtifactReferences(params: {
  normalizedPackageId: string;
  dependencyClassificationRegister: Record<string, unknown>;
  candidateInputDigestSha256: string;
}): Step1AssessmentArtifactReference[] {
  return [
    {
      artifact_kind: "normalized_package_identity",
      artifact_id: params.normalizedPackageId,
      artifact_digest_sha256: null,
    },
    {
      artifact_kind: "dependency_classification_register",
      artifact_id: "dependency_classification_register",
      artifact_digest_sha256: sha256Text(stableJsonStringify(params.dependencyClassificationRegister)),
    },
    {
      artifact_kind: "candidate_input_digest",
      artifact_id: "candidate_input_digest",
      artifact_digest_sha256: params.candidateInputDigestSha256,
    },
  ];
}

function buildCandidateManifest(params: {
  normalizedPackageId: string;
  policySetId: string;
  modelSetId: string;
  configSetId: string;
  bundleClass: string;
  requestedRunMode: string;
  targetEnvironment: string;
  dependencyClassificationRegister: Record<string, unknown>;
}): Step1CandidateBundleManifest {
  const manifestInput = {
    normalized_package_id: params.normalizedPackageId,
    policy_set_id: params.policySetId,
    model_set_id: params.modelSetId,
    config_set_id: params.configSetId,
    bundle_class: params.bundleClass,
    requested_run_mode: params.requestedRunMode,
    target_environment: params.targetEnvironment,
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
    requested_run_mode: params.requestedRunMode,
    deterministic_build_timestamp_utc: deterministicTimestampFromDigest(candidateInputDigestSha256),
    target_environment: params.targetEnvironment,
    dependency_classification_register: params.dependencyClassificationRegister,
    assessment_artifact_references: buildAssessmentArtifactReferences({
      normalizedPackageId: params.normalizedPackageId,
      dependencyClassificationRegister: params.dependencyClassificationRegister,
      candidateInputDigestSha256,
    }),
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

  const manifest = buildCandidateManifest({
    normalizedPackageId: requestRecord.normalized_package_id,
    policySetId: requestRecord.policy_set_id,
    modelSetId: requestRecord.model_set_id,
    configSetId: requestRecord.config_set_id,
    bundleClass: requestRecord.bundle_class,
    requestedRunMode,
    targetEnvironment: requestRecord.target_environment,
    dependencyClassificationRegister: requestRecord.dependency_classification_register,
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
