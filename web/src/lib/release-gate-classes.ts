export const RELEASE_GATE_CLASSES = [
  "runtime_critical",
  "publication_consistency",
  "non_critical_observability",
  "non_critical_product_parity",
] as const;

export type ReleaseGateClass = typeof RELEASE_GATE_CLASSES[number];

export type ReleaseGateStatus = "pass" | "fail";

export type ReleaseGateResultInput = {
  gate_id: string;
  gate_class: ReleaseGateClass;
  status: ReleaseGateStatus;
  detail?: string | null;
};

export type ClassifiedReleaseGateResult = ReleaseGateResultInput & {
  blocking_by_default: boolean;
  hotfix_lane_default_action: "block" | "record_only";
};

type ReleaseGateClassPolicy = {
  blocking_by_default: boolean;
  hotfix_lane_default_action: "block" | "record_only";
};

export const RELEASE_GATE_CLASS_POLICY: Record<ReleaseGateClass, ReleaseGateClassPolicy> = {
  runtime_critical: {
    blocking_by_default: true,
    hotfix_lane_default_action: "block",
  },
  publication_consistency: {
    blocking_by_default: true,
    hotfix_lane_default_action: "block",
  },
  non_critical_observability: {
    blocking_by_default: false,
    hotfix_lane_default_action: "record_only",
  },
  non_critical_product_parity: {
    blocking_by_default: false,
    hotfix_lane_default_action: "record_only",
  },
};

export const DEFAULT_BLOCKING_GATE_CLASSES = [
  "runtime_critical",
  "publication_consistency",
] as const satisfies readonly ReleaseGateClass[];

export const DEFAULT_NON_BLOCKING_GATE_CLASSES = [
  "non_critical_observability",
  "non_critical_product_parity",
] as const satisfies readonly ReleaseGateClass[];

export type DefaultHotfixLaneSelection = {
  blocking_gate_classes: ReleaseGateClass[];
  non_blocking_gate_classes: ReleaseGateClass[];
};

export type DefaultHotfixLaneEvaluation = {
  allowed_to_proceed: boolean;
  classified_results: ClassifiedReleaseGateResult[];
  blocking_results: ClassifiedReleaseGateResult[];
  recorded_non_blocking_results: ClassifiedReleaseGateResult[];
  selection: DefaultHotfixLaneSelection;
};

function requireNonEmptyText(value: unknown, fieldName: string): string {
  const text = String(value ?? "").trim();
  if (!text) {
    throw new Error(`${fieldName} is required.`);
  }
  return text;
}

export function classifyReleaseGateResult(input: ReleaseGateResultInput): ClassifiedReleaseGateResult {
  const gateId = requireNonEmptyText(input.gate_id, "gate_id");
  const policy = RELEASE_GATE_CLASS_POLICY[input.gate_class];
  if (!policy) {
    throw new Error(`gate_class='${String(input.gate_class)}' is not defined.`);
  }

  return {
    gate_id: gateId,
    gate_class: input.gate_class,
    status: input.status,
    detail: input.detail ?? null,
    blocking_by_default: policy.blocking_by_default,
    hotfix_lane_default_action: policy.hotfix_lane_default_action,
  };
}

export function selectDefaultHotfixLaneGateClasses(): DefaultHotfixLaneSelection {
  return {
    blocking_gate_classes: [...DEFAULT_BLOCKING_GATE_CLASSES],
    non_blocking_gate_classes: [...DEFAULT_NON_BLOCKING_GATE_CLASSES],
  };
}

export function evaluateDefaultHotfixLane(results: ReleaseGateResultInput[]): DefaultHotfixLaneEvaluation {
  const classifiedResults = results.map((result) => classifyReleaseGateResult(result));
  const failedResults = classifiedResults.filter((result) => result.status === "fail");
  const blockingResults = failedResults.filter((result) => result.blocking_by_default);
  const recordedNonBlockingResults = failedResults.filter((result) => !result.blocking_by_default);

  return {
    allowed_to_proceed: blockingResults.length === 0,
    classified_results: classifiedResults,
    blocking_results: blockingResults,
    recorded_non_blocking_results: recordedNonBlockingResults,
    selection: selectDefaultHotfixLaneGateClasses(),
  };
}

export const PHASE_D_DEPLOYMENT_RECORD_FIELDS = [
  "deployment_record_id",
  "generated_at_utc",
  "environment",
  "release_lane",
  "release_gate_class_results",
  "blocking_gate_classes",
  "non_blocking_gate_classes",
  "deployed_commit_sha",
  "deployed_image_uri",
  "deployed_image_tag",
  "ecs_task_definition_arn",
  "service_name",
  "cluster_name",
  "deployment_started_at_utc",
  "deployment_completed_at_utc",
  "deployment_status",
  "evidence_artifact_paths",
] as const;

export const REQUIRED_DEPLOYMENT_IDENTITY_FIELDS = [
  "deployed_commit_sha",
  "deployed_image_uri",
  "deployed_image_tag",
  "ecs_task_definition_arn",
] as const;

export type PhaseDDeploymentRecord = {
  deployment_record_id: string;
  generated_at_utc: string;
  environment: string;
  release_lane: string;
  release_gate_class_results: ClassifiedReleaseGateResult[];
  blocking_gate_classes: ReleaseGateClass[];
  non_blocking_gate_classes: ReleaseGateClass[];
  deployed_commit_sha: string;
  deployed_image_uri: string;
  deployed_image_tag: string;
  ecs_task_definition_arn: string;
  service_name: string;
  cluster_name: string;
  deployment_started_at_utc: string;
  deployment_completed_at_utc: string;
  deployment_status: string;
  evidence_artifact_paths: string[];
};

export type DeploymentRecordValidation = {
  valid: boolean;
  missing_fields: string[];
  missing_identity_fields: string[];
};

export function validatePhaseDDeploymentRecord(
  record: Partial<PhaseDDeploymentRecord>,
): DeploymentRecordValidation {
  const missingFields = PHASE_D_DEPLOYMENT_RECORD_FIELDS.filter((fieldName) => {
    const value = record[fieldName];
    if (Array.isArray(value)) return value.length === 0;
    return String(value ?? "").trim() === "";
  });
  const missingIdentityFields = REQUIRED_DEPLOYMENT_IDENTITY_FIELDS.filter((fieldName) => {
    return String(record[fieldName] ?? "").trim() === "";
  });

  return {
    valid: missingFields.length === 0 && missingIdentityFields.length === 0,
    missing_fields: [...missingFields],
    missing_identity_fields: [...missingIdentityFields],
  };
}
