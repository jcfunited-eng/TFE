import { resolveWorkspaceRoot } from "../workspace-root";
import { createAssessmentReportRecord } from "./assessment-report";
import { createCandidateBundleRecord } from "./candidate-bundle";
import { createQuoteCacheFollowupTicket } from "./followup-ticket";
import { createPublicationCommitRecord } from "./publication-commit";
import { createStep1RunRequest } from "./run-request";
import {
  createFileProofStep1Persistence,
  createPostgresStep1Persistence,
  createStep1SuccessMirrorRunRow,
  type Step1FollowupStatus,
  type Step1Persistence,
} from "./schema";

export const STEP1_CUTOVER_REQUEST_MODE = "step1_cutover";
export const STEP1_EXISTING_ADMIN_REFRESH_MODE = "snapshot";
export const STEP1_CUTOVER_EXECUTION_PATH = "step1_orchestrator";
export const STEP1_LEGACY_PATH_STATUS = "read_only_history_only";
export const STEP1_CUTOVER_MODE_ENV = "TFE_STEP1_CUTOVER_MODE";
export const STEP1_CUTOVER_PROOF_STORE_ENV = "TFE_STEP1_FILE_PROOF_STORE_PATH";
export const STEP1_CUTOVER_REQUEST_CONTRACT_ENV = "TFE_STEP1_CUTOVER_REQUEST_CONTRACT_JSON";

export type Step1CutoverExecutionMode = "readonly" | "enabled";

export type Step1OrchestratorInput = {
  runId?: string;
  normalizedPackageId: string;
  policySetId: string;
  modelSetId: string;
  configSetId: string;
  bundleClass: string;
  dependencyClassificationRegister: Record<string, unknown>;
  targetEnvironment: string;
  requestedBy: string;
  requestedAtUtc?: string;
  assessmentRuleSetId: string;
  followupDesiredStatus?: "deferred" | "launched";
  mode?: string;
  triggerSource?: string;
};

export type Step1OrchestratorOptions = {
  executionMode: Step1CutoverExecutionMode;
  proofStorePath?: string;
  workspaceRoot?: string;
};

export type Step1AdminRefreshInputResolution = {
  input: Step1OrchestratorInput;
  contractSource: "request_body" | "env_contract" | "merged";
};

export type Step1OrchestratorResult = {
  executionPath: typeof STEP1_CUTOVER_EXECUTION_PATH;
  legacyStep1PathStatus: typeof STEP1_LEGACY_PATH_STATUS;
  legacyRunnerDispatched: false;
  cutoverMode: Step1CutoverExecutionMode;
  persistenceKind: Step1Persistence["kind"];
  runId: string;
  requestArtifactPath: string;
  candidateBundleManifestPath: string;
  candidateBundleId: string;
  assessmentReportPath: string;
  assessmentReportId: string;
  publicationManifestPath: string;
  publicationBundleId: string;
  followupTicketPath: string;
  followupJobId: string;
  followupStatus: Step1FollowupStatus;
};

export class Step1OrchestratorError extends Error {
  code: "cutover_mode_invalid" | "proof_store_required";
  detail: string;

  constructor(params: { code: "cutover_mode_invalid" | "proof_store_required"; detail: string }) {
    super(`Step 1 orchestrator rejected dispatch. code=${params.code}; detail=${params.detail}`);
    this.name = "Step1OrchestratorError";
    this.code = params.code;
    this.detail = params.detail;
  }
}

export class Step1AdminRefreshContractError extends Error {
  code: "request_contract_missing" | "request_contract_invalid";
  detail: string;

  constructor(params: { code: "request_contract_missing" | "request_contract_invalid"; detail: string }) {
    super(`Step 1 admin refresh cutover rejected dispatch. code=${params.code}; detail=${params.detail}`);
    this.name = "Step1AdminRefreshContractError";
    this.code = params.code;
    this.detail = params.detail;
  }
}

function asObjectRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function readTrimmedText(value: unknown): string | null {
  const text = String(value ?? "").trim();
  return text || null;
}

function requireAdminRefreshText(
  value: unknown,
  fieldName: string,
): string {
  const text = readTrimmedText(value);
  if (!text) {
    throw new Step1AdminRefreshContractError({
      code: "request_contract_missing",
      detail: `${fieldName} is required for Step 1 cutover. Supply it in the request body or ${STEP1_CUTOVER_REQUEST_CONTRACT_ENV}.`,
    });
  }
  return text;
}

function requireAdminRefreshDependencyClassificationRegister(value: unknown): Record<string, unknown> {
  const record = asObjectRecord(value);
  if (!record || Object.keys(record).length === 0) {
    throw new Step1AdminRefreshContractError({
      code: "request_contract_missing",
      detail: `dependencyClassificationRegister is required for Step 1 cutover. Supply it in the request body or ${STEP1_CUTOVER_REQUEST_CONTRACT_ENV}.`,
    });
  }
  return record;
}

function parseRequestContractFromEnv(env: NodeJS.ProcessEnv): Record<string, unknown> {
  const raw = String(env[STEP1_CUTOVER_REQUEST_CONTRACT_ENV] ?? "").trim();
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    const record = asObjectRecord(parsed);
    if (!record) {
      throw new Error("must decode to a JSON object");
    }
    return record;
  } catch (error) {
    throw new Step1AdminRefreshContractError({
      code: "request_contract_invalid",
      detail: `${STEP1_CUTOVER_REQUEST_CONTRACT_ENV} ${error instanceof Error ? error.message : "is invalid."}`,
    });
  }
}

export function resolveStep1OrchestratorInputFromAdminRefreshRequest(params: {
  requestBody: Record<string, unknown> | null;
  requestedBy: string;
  executionMode: Step1CutoverExecutionMode;
  requestedMode: string;
  env?: NodeJS.ProcessEnv;
}): Step1AdminRefreshInputResolution {
  const requestBody = params.requestBody ?? {};
  const envContract = parseRequestContractFromEnv(params.env ?? process.env);
  const requestRecord = asObjectRecord(requestBody) ?? {};
  const mergedRecord = {
    ...envContract,
    ...requestRecord,
  };
  const requestContractKeys = [
    "normalizedPackageId",
    "policySetId",
    "modelSetId",
    "configSetId",
    "bundleClass",
    "dependencyClassificationRegister",
    "targetEnvironment",
    "assessmentRuleSetId",
  ];
  const requestHasContract = requestContractKeys.some((key) => key in requestRecord);
  const envHasContract = Object.keys(envContract).length > 0;
  if (!requestHasContract && !envHasContract) {
    throw new Step1AdminRefreshContractError({
      code: "request_contract_missing",
      detail: `Existing Step 1 admin refresh requests need ${STEP1_CUTOVER_REQUEST_CONTRACT_ENV} or equivalent request-body Step 1 fields while cutover is enabled.`,
    });
  }

  const contractSource =
    requestHasContract && envHasContract
      ? "merged"
      : requestHasContract
        ? "request_body"
        : "env_contract";

  return {
    contractSource,
    input: {
      runId: readTrimmedText(mergedRecord.runId) ?? undefined,
      normalizedPackageId: requireAdminRefreshText(mergedRecord.normalizedPackageId, "normalizedPackageId"),
      policySetId: requireAdminRefreshText(mergedRecord.policySetId, "policySetId"),
      modelSetId: requireAdminRefreshText(mergedRecord.modelSetId, "modelSetId"),
      configSetId: requireAdminRefreshText(mergedRecord.configSetId, "configSetId"),
      bundleClass: requireAdminRefreshText(mergedRecord.bundleClass, "bundleClass"),
      dependencyClassificationRegister: requireAdminRefreshDependencyClassificationRegister(
        mergedRecord.dependencyClassificationRegister,
      ),
      targetEnvironment: requireAdminRefreshText(mergedRecord.targetEnvironment, "targetEnvironment"),
      requestedBy: params.requestedBy,
      requestedAtUtc: readTrimmedText(mergedRecord.requestedAtUtc) ?? undefined,
      assessmentRuleSetId: requireAdminRefreshText(mergedRecord.assessmentRuleSetId, "assessmentRuleSetId"),
      followupDesiredStatus: readTrimmedText(mergedRecord.followupDesiredStatus) === "launched"
        ? "launched"
        : "deferred",
      mode: params.requestedMode,
      triggerSource: params.executionMode === "readonly"
        ? "step1_admin_refresh_snapshot_readonly"
        : "step1_admin_refresh_snapshot_enabled",
    },
  };
}

function resolveStep1Persistence(options: Step1OrchestratorOptions): Step1Persistence {
  if (options.executionMode === "readonly") {
    const proofStorePath = String(options.proofStorePath ?? "").trim();
    if (!proofStorePath) {
      throw new Step1OrchestratorError({
        code: "proof_store_required",
        detail: "readonly Step 1 cutover requires a proof store path.",
      });
    }
    return createFileProofStep1Persistence(proofStorePath);
  }

  if (options.executionMode === "enabled") {
    return createPostgresStep1Persistence();
  }

  throw new Step1OrchestratorError({
    code: "cutover_mode_invalid",
    detail: `unsupported execution_mode='${String(options.executionMode)}'.`,
  });
}

function normalizeFollowupDesiredStatus(value: unknown): "deferred" | "launched" {
  return String(value ?? "").trim().toLowerCase() === "launched" ? "launched" : "deferred";
}

export async function dispatchStep1Orchestrator(
  input: Step1OrchestratorInput,
  options: Step1OrchestratorOptions,
): Promise<Step1OrchestratorResult> {
  const workspaceRoot = options.workspaceRoot ?? resolveWorkspaceRoot();
  const persistence = resolveStep1Persistence(options);
  const request = await createStep1RunRequest(
    {
      runId: input.runId,
      normalizedPackageId: input.normalizedPackageId,
      policySetId: input.policySetId,
      modelSetId: input.modelSetId,
      configSetId: input.configSetId,
      bundleClass: input.bundleClass,
      dependencyClassificationRegister: input.dependencyClassificationRegister,
      targetEnvironment: input.targetEnvironment,
      requestedBy: input.requestedBy,
      requestedAtUtc: input.requestedAtUtc,
      mode: input.mode ?? STEP1_CUTOVER_REQUEST_MODE,
      triggerSource: input.triggerSource ?? "step1_cutover_orchestrator",
    },
    {
      persistence,
      workspaceRoot,
    },
  );

  const candidate = await createCandidateBundleRecord(
    {
      runId: request.requestRecord.run_id,
      requestArtifactPath: request.requestArtifactPath,
      requestedRunMode: input.mode ?? STEP1_CUTOVER_REQUEST_MODE,
    },
    {
      persistence,
      workspaceRoot,
    },
  );

  const assessment = await createAssessmentReportRecord(
    {
      runId: request.requestRecord.run_id,
      candidateBundleManifestPath: candidate.manifestPath,
      assessmentRuleSetId: input.assessmentRuleSetId,
    },
    {
      persistence,
      workspaceRoot,
    },
  );

  const publicationCommit = await createPublicationCommitRecord(
    {
      runId: request.requestRecord.run_id,
      assessmentReportPath: assessment.reportPath,
      targetEnvironment: input.targetEnvironment,
    },
    {
      persistence,
      workspaceRoot,
    },
  );

  const followup = await createQuoteCacheFollowupTicket(
    {
      runId: request.requestRecord.run_id,
      publicationManifestPath: publicationCommit.manifestPath,
      classification: "non_critical_follow_up",
      desiredStatus: normalizeFollowupDesiredStatus(input.followupDesiredStatus),
    },
    {
      persistence,
      workspaceRoot,
    },
  );

  await persistence.writeRunRow(
    createStep1SuccessMirrorRunRow({
      baseRunRow: request.runRow,
      publicationCommittedAtUtc: publicationCommit.manifest.committed_at_utc,
      followupStatus: followup.ticket.status,
      followupCreatedAtUtc: followup.ticket.created_at_utc,
    }),
  );

  return {
    executionPath: STEP1_CUTOVER_EXECUTION_PATH,
    legacyStep1PathStatus: STEP1_LEGACY_PATH_STATUS,
    legacyRunnerDispatched: false,
    cutoverMode: options.executionMode,
    persistenceKind: persistence.kind,
    runId: request.requestRecord.run_id,
    requestArtifactPath: request.requestArtifactPath,
    candidateBundleManifestPath: candidate.manifestPath,
    candidateBundleId: candidate.manifest.candidate_bundle_id,
    assessmentReportPath: assessment.reportPath,
    assessmentReportId: assessment.report.assessment_report_id,
    publicationManifestPath: publicationCommit.manifestPath,
    publicationBundleId: publicationCommit.manifest.publication_bundle_id,
    followupTicketPath: followup.ticketPath,
    followupJobId: followup.ticket.followup_job_id,
    followupStatus: followup.ticket.status,
  };
}
