import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";

import { resolveWorkspaceRoot } from "../workspace-root";
import {
  buildStep1RequestArtifactRelativePath,
  createCandidateBuildPhaseRow,
  createStep1RunRow,
  resolveStep1RequestArtifactPath,
  type Step1RunRequestPersistence,
  type Step1RunRequestRecord,
} from "./schema";

export type Step1RunRequestInput = {
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
  mode?: string;
  triggerSource?: string;
};

export type Step1RunRequestResult = {
  requestRecord: Step1RunRequestRecord;
  requestArtifactPath: string;
  requestArtifactRelativePath: string;
  runRow: ReturnType<typeof createStep1RunRow>;
  phaseRow: ReturnType<typeof createCandidateBuildPhaseRow>;
};

export class Step1RunRequestError extends Error {
  code: "request_invalid" | "dependency_classification_missing" | "request_state_persistence_failure";
  detail: string;
  runId: string;

  constructor(params: {
    code: "request_invalid" | "dependency_classification_missing" | "request_state_persistence_failure";
    detail: string;
    runId: string;
  }) {
    super(
      `Step 1 request rejected. run_id=${params.runId}; code=${params.code}; `
      + `detail=${params.detail}. No publication work started.`,
    );
    this.name = "Step1RunRequestError";
    this.code = params.code;
    this.detail = params.detail;
    this.runId = params.runId;
  }
}

type CreateStep1RunRequestOptions = {
  persistence: Step1RunRequestPersistence;
  workspaceRoot?: string;
};

function requireText(value: unknown, fieldName: string, runId: string): string {
  const text = String(value ?? "").trim();
  if (!text) {
    throw new Step1RunRequestError({
      code: "request_invalid",
      detail: `${fieldName} must be a non-empty string.`,
      runId,
    });
  }
  return text;
}

function requireIsoTimestamp(value: unknown, fieldName: string, runId: string): string {
  const text = requireText(value, fieldName, runId);
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) {
    throw new Step1RunRequestError({
      code: "request_invalid",
      detail: `${fieldName} must be a valid ISO timestamp.`,
      runId,
    });
  }
  return new Date(parsed).toISOString();
}

function normalizeDependencyClassificationRegister(
  value: unknown,
  runId: string,
): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Step1RunRequestError({
      code: "dependency_classification_missing",
      detail: "dependency_classification_register must be a non-empty object.",
      runId,
    });
  }

  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).map((key) => key.trim()).filter(Boolean);
  if (keys.length === 0) {
    throw new Step1RunRequestError({
      code: "dependency_classification_missing",
      detail: "dependency_classification_register must classify at least one dependency.",
      runId,
    });
  }

  for (const key of keys) {
    const entry = record[key];
    const entryText = typeof entry === "string" ? entry.trim() : "";
    const entryObject = entry && typeof entry === "object" && !Array.isArray(entry);
    if (!entryObject && !entryText) {
      throw new Step1RunRequestError({
        code: "dependency_classification_missing",
        detail: `dependency_classification_register is missing a classification for '${key}'.`,
        runId,
      });
    }
  }

  return record;
}

function createRequestRecord(input: Step1RunRequestInput, runId: string): Step1RunRequestRecord {
  return {
    run_id: runId,
    normalized_package_id: requireText(input.normalizedPackageId, "normalized_package_id", runId),
    policy_set_id: requireText(input.policySetId, "policy_set_id", runId),
    model_set_id: requireText(input.modelSetId, "model_set_id", runId),
    config_set_id: requireText(input.configSetId, "config_set_id", runId),
    bundle_class: requireText(input.bundleClass, "bundle_class", runId),
    dependency_classification_register: normalizeDependencyClassificationRegister(
      input.dependencyClassificationRegister,
      runId,
    ),
    target_environment: requireText(input.targetEnvironment, "target_environment", runId),
    requested_by: requireText(input.requestedBy, "requested_by", runId),
    requested_at_utc: requireIsoTimestamp(input.requestedAtUtc ?? new Date().toISOString(), "requested_at_utc", runId),
  };
}

export async function createStep1RunRequest(
  input: Step1RunRequestInput,
  options: CreateStep1RunRequestOptions,
): Promise<Step1RunRequestResult> {
  const runId = requireText(input.runId ?? randomUUID(), "run_id", input.runId ?? "pending");
  const persistence = options.persistence;
  const workspaceRoot = options.workspaceRoot ?? resolveWorkspaceRoot();
  const requestRecord = createRequestRecord(input, runId);
  const requestArtifactPath = resolveStep1RequestArtifactPath(workspaceRoot, runId);
  const requestArtifactRelativePath = buildStep1RequestArtifactRelativePath(runId);

  const runRow = createStep1RunRow({
    runId,
    mode: requireText(input.mode ?? "step1_cutover", "mode", runId),
    triggerSource: requireText(input.triggerSource ?? "step1_cutover_dark", "trigger_source", runId),
    requestedBy: requestRecord.requested_by,
    requestedAtUtc: requestRecord.requested_at_utc,
    requestArtifactPath,
    phaseName: "candidate_build",
    phaseProcessStatus: "pending",
  });

  const phaseRow = createCandidateBuildPhaseRow({
    runId,
    requestedAtUtc: requestRecord.requested_at_utc,
    requestArtifactPath,
    requestRecord,
  });

  try {
    await mkdir(path.dirname(requestArtifactPath), { recursive: true });
    await writeFile(
      requestArtifactPath,
      `${JSON.stringify(
        {
          ...requestRecord,
          request_artifact_path: requestArtifactPath,
          request_artifact_relative_path: requestArtifactRelativePath,
        },
        null,
        2,
      )}\n`,
      "utf8",
    );

    await persistence.ensureReady();
    await persistence.writeRunRow(runRow);
    await persistence.writePhaseRow(phaseRow);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown request state persistence failure.";
    throw new Step1RunRequestError({
      code: "request_state_persistence_failure",
      detail,
      runId,
    });
  }

  return {
    requestRecord,
    requestArtifactPath,
    requestArtifactRelativePath,
    runRow,
    phaseRow,
  };
}
