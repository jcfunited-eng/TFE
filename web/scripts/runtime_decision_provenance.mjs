import { createHash } from "node:crypto";

const DECISION_VALUES = new Set(["Accumulate", "Hold", "Avoid"]);
const DEFAULT_PROVENANCE_SCHEMA_VERSION = "v1";
const DEFAULT_WRITER_COMPONENT = "web/scripts/sync_runtime_postgres.mjs";
const DEFAULT_CP_PROFILE = "CP-0";
const PRIMITIVE_ARTIFACT_ID = "gemini_l5_primitive_v1";
const PRIMITIVE_FORMULA_TEXT = [
  "Step 1: if S_UF <= 0 => Avoid",
  "Step 2: if R_rev_k > 0 => Avoid",
  "Step 3: if D_k > 0 and R_UF > 0 and C_k < prev_C_k and P_k < B_k => Accumulate",
  "Step 4: if D_k >= 0 and P_k < (B_k * 1.5) => Hold",
  "Step 5: default => Avoid",
].join(" | ");
const PRIMITIVE_ARTIFACT_HASH = createHash("sha256").update(PRIMITIVE_FORMULA_TEXT).digest("hex");

export const CURRENT_ST_ANCHORED_EXACT_FAMILY = "CURRENT_ST_ANCHORED_EXACT_FAMILY";
export const NO_ST_EXACT_FAMILY_KEEP_CD_PHASE_SPIDER_STRICT = "NO_ST_EXACT_FAMILY_KEEP_CD_PHASE_SPIDER_STRICT";
export const DEFAULT_PSCF_EXACT_ANCHOR_MODE = NO_ST_EXACT_FAMILY_KEEP_CD_PHASE_SPIDER_STRICT;

export const TYPED_FALLBACK_LEVELS = [
  {
    id: "L0_EXACT_STRUCTURAL_MATCH",
    order: 0,
    structural_coverage: true,
    exact_structural: true,
    quality_assessed_under_current_contract: true,
    description: "Exact GEMINI primitive decision with all required inputs present.",
  },
  {
    id: "L1_RELAXED_STRUCTURAL_MATCH",
    order: 1,
    structural_coverage: false,
    exact_structural: false,
    quality_assessed_under_current_contract: false,
    description: "Legacy reserved level. Unused by the GEMINI primitive sorter.",
  },
  {
    id: "L2_SAFE_POLICY_FALLBACK",
    order: 2,
    structural_coverage: false,
    exact_structural: false,
    quality_assessed_under_current_contract: false,
    description: "Legacy reserved level. Unused by the GEMINI primitive sorter.",
  },
  {
    id: "L3_DEGRADED_UNMAPPED",
    order: 3,
    structural_coverage: false,
    exact_structural: false,
    quality_assessed_under_current_contract: false,
    description: "Legacy reserved level. Unused by the GEMINI primitive sorter.",
  },
  {
    id: "L4_UNAVAILABLE_OR_BLOCKED",
    order: 4,
    structural_coverage: false,
    exact_structural: false,
    quality_assessed_under_current_contract: false,
    description: "Required primitive inputs are missing, so the row defaults to Avoid.",
  },
];

export const TYPED_FALLBACK_ORTHOGONAL_FLAGS = [
  "primitive_input_complete",
  "provenance_source",
];

export const PROVENANCE_REQUIRED_NON_NULL_FIELDS = [
  "run_id",
  "ticker",
  "snapshot_row_digest_sha256",
  "snapshot_timestamp_utc",
  "runtime_sync_completed_utc",
  "decision_timestamp_utc",
  "policy_artifact_id",
  "policy_artifact_hash_sha256",
  "policy_source_mode",
  "candidate_key_chain_json",
  "match_level",
  "fallback_ladder_level",
  "matched_exact_bool",
  "fallback_used",
  "decision",
  "decision_reason_code",
  "anomaly_flags_used_json",
  "structural_recency_components_used_json",
  "epoch_components_used_json",
  "coverage_class",
  "provenance_schema_version",
  "writer_component",
  "writer_build_hash",
  "cp_profile",
  "provenance_generated_utc",
];

const REQUIRED_PRIMITIVE_FIELDS = [
  ["s_uf", "S_UF"],
  ["r_uf", "R_UF"],
  ["c_k", "C_k"],
  ["prev_c_k", "prev_C_k"],
  ["p_k", "P_k"],
  ["b_k", "B_k"],
  ["d_k", "D_k"],
  ["r_rev_k", "R_rev_k"],
] ;

export function normalizeTicker(value) {
  return String(value ?? "").trim().toUpperCase();
}

function toRecord(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value;
}

function toFinite(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "string" && value.trim().length === 0) return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

function toBoolean(value, fallback = false) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const text = value.trim().toLowerCase();
    if (["1", "true", "yes", "on", "y"].includes(text)) return true;
    if (["0", "false", "no", "off", "n", ""].includes(text)) return false;
  }
  return fallback;
}

export function stableStringify(value) {
  if (value === null || value === undefined) return "null";
  const t = typeof value;
  if (t === "string") return JSON.stringify(value);
  if (t === "number") return Number.isFinite(value) ? JSON.stringify(value) : "null";
  if (t === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }
  if (t === "object") {
    const keys = Object.keys(value).sort();
    return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
  }
  return "null";
}

export function sha256Hex(text) {
  return createHash("sha256").update(String(text ?? "")).digest("hex");
}

export function minBarsForAccumulate() {
  const raw = Number(process.env.TFE_RECOMMENDATIONS_MIN_BARS ?? 180);
  if (!Number.isFinite(raw)) return 180;
  const whole = Math.floor(raw);
  if (whole < 20) return 20;
  if (whole > 2520) return 2520;
  return whole;
}

export function normalizeDecisionTraceRow(value) {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeDecisionTraceRow(item));
  }

  const record = toRecord(value);
  if (!record) return value;

  return Object.fromEntries(
    Object.entries(record).map(([key, item]) => [
      String(key).toLowerCase(),
      normalizeDecisionTraceRow(item),
    ]),
  );
}

function decisionLabel(value) {
  if (DECISION_VALUES.has(value)) return value;
  return "Avoid";
}

function extractStructuralRecencyComponents(row) {
  const components = {};
  for (const [key, value] of Object.entries(row)) {
    if (key.startsWith("steps_since_") || key.includes("recency")) {
      components[key] = value;
    }
  }

  return {
    available: Object.keys(components).length > 0,
    source: "snapshot_row_top_level",
    components,
    missing_reason: Object.keys(components).length > 0 ? null : "no_structural_recency_fields_present",
  };
}

function extractEpochComponents(row) {
  const components = {};
  const epochObj = toRecord(row.epoch);

  if (epochObj) {
    for (const [key, value] of Object.entries(epochObj)) {
      components[`epoch.${key}`] = value;
    }
  }

  for (const [key, value] of Object.entries(row)) {
    if (key.includes("epoch") || key === "regime_code" || key === "gap_state") {
      components[key] = value;
    }
  }

  return {
    available: Object.keys(components).length > 0,
    source: "snapshot_row_top_level",
    components,
    missing_reason: Object.keys(components).length > 0 ? null : "no_epoch_fields_present",
  };
}

function primitiveInputFromRow(row) {
  const normalized = normalizeDecisionTraceRow(row && typeof row === "object" ? row : {});
  const missingFields = [];

  const extracted = {};
  for (const [lowerKey, label] of REQUIRED_PRIMITIVE_FIELDS) {
    const value = toFinite(normalized[lowerKey]);
    extracted[label] = value;
    if (value === null) {
      missingFields.push(label);
    }
  }

  return {
    regime: String(normalized.regime ?? "UNKNOWN").trim() || "UNKNOWN",
    D_k: extracted.D_k,
    M_k: toFinite(normalized.m_k),
    R_rev_k: extracted.R_rev_k,
    U_star_k: toFinite(normalized.u_star_k),
    C_k: extracted.C_k,
    prev_C_k: extracted.prev_C_k,
    P_k: extracted.P_k,
    B_k: extracted.B_k,
    S_UF: extracted.S_UF,
    R_UF: extracted.R_UF,
    missing_fields: missingFields,
  };
}

function primitiveReasonCodeFromInputs(inputs) {
  if (inputs.missing_fields.length > 0) return "GEMINI_MISSING_REQUIRED_FIELDS";
  if (inputs.S_UF <= 0) return "GEMINI_STEP_1_VIABILITY";
  if (inputs.R_rev_k > 0) return "GEMINI_STEP_2_KILL_SWITCH";
  if (inputs.D_k > 0 && inputs.R_UF > 0 && inputs.C_k < inputs.prev_C_k && inputs.P_k < inputs.B_k) {
    return "GEMINI_STEP_3_ACCUMULATE";
  }
  if (inputs.D_k >= 0 && inputs.P_k < (inputs.B_k * 1.5)) {
    return "GEMINI_STEP_4_HOLD";
  }
  return "GEMINI_STEP_5_DEFAULT_AVOID";
}

function primitiveDecisionFromReasonCode(reasonCode) {
  if (reasonCode === "GEMINI_STEP_3_ACCUMULATE") return "Accumulate";
  if (reasonCode === "GEMINI_STEP_4_HOLD") return "Hold";
  return "Avoid";
}

function primitiveFallbackReason(reasonCode, missingFields) {
  if (reasonCode !== "GEMINI_MISSING_REQUIRED_FIELDS") return null;
  const joined = Array.isArray(missingFields) ? missingFields.join(",") : "";
  return joined ? `missing_required_fields:${joined}` : "missing_required_fields";
}

function primitiveWitness(reasonCode, missingFields) {
  const witness = [PRIMITIVE_ARTIFACT_ID, reasonCode];
  if (reasonCode === "GEMINI_MISSING_REQUIRED_FIELDS" && Array.isArray(missingFields) && missingFields.length > 0) {
    witness.push(`missing:${missingFields.join(",")}`);
  }
  return witness;
}

export function deriveTypedFallbackLadderLevel({ decisionReasonCode }) {
  const reasonCode = String(decisionReasonCode ?? "").trim();
  if (reasonCode === "GEMINI_MISSING_REQUIRED_FIELDS") {
    return "L4_UNAVAILABLE_OR_BLOCKED";
  }
  return "L0_EXACT_STRUCTURAL_MATCH";
}

function matchLevelFromDecision(decisionReasonCode) {
  if (decisionReasonCode === "GEMINI_MISSING_REQUIRED_FIELDS") {
    return "L4_PRIMITIVE_INPUT_MISSING";
  }
  return "L0_PRIMITIVE_DIRECT";
}

function coverageClassFromTrace(decisionReasonCode) {
  if (decisionReasonCode === "GEMINI_MISSING_REQUIRED_FIELDS") return "fallback";
  return "exact";
}

export function computeDecisionTrace(
  row,
  policyRuntime,
  minBars,
  exactAnchorMode = DEFAULT_PSCF_EXACT_ANCHOR_MODE,
) {
  void policyRuntime;
  void minBars;
  void exactAnchorMode;

  const normalizedRow = normalizeDecisionTraceRow(row && typeof row === "object" ? row : {});
  const basis = primitiveInputFromRow(normalizedRow);
  const decisionReasonCode = primitiveReasonCodeFromInputs(basis);
  const decision = primitiveDecisionFromReasonCode(decisionReasonCode);
  const fallbackUsed = decisionReasonCode === "GEMINI_MISSING_REQUIRED_FIELDS";
  const candidateKeyChain = primitiveWitness(decisionReasonCode, basis.missing_fields);
  const matchedKey = fallbackUsed ? null : PRIMITIVE_ARTIFACT_ID;
  const matchedIndex = fallbackUsed ? -1 : 0;
  const anomalyFlags = {
    primitive_input_complete: !fallbackUsed,
    anomaly_any: false,
  };

  return {
    basis,
    anomalyFlags,
    candidateKeyChain,
    matchedKey,
    matchedIndex,
    matchLevel: matchLevelFromDecision(decisionReasonCode),
    fallbackLadderLevel: deriveTypedFallbackLadderLevel({ decisionReasonCode, matchedIndex }),
    matchedExactBool: !fallbackUsed,
    fallbackUsed,
    fallbackReasonCode: primitiveFallbackReason(decisionReasonCode, basis.missing_fields),
    decision,
    decisionReasonCode,
    coverageClass: coverageClassFromTrace(decisionReasonCode),
  };
}

export function loadPolicyRuntimeArtifact(rootDir) {
  void rootDir;
  return {
    source_path: null,
    policy_artifact_id: PRIMITIVE_ARTIFACT_ID,
    policy_artifact_hash_sha256: PRIMITIVE_ARTIFACT_HASH,
    policy_source_mode: "gemini_l5_primitive",
    generated_at_utc: null,
    cells: {},
  };
}

function isProvenanceRecordValid(record) {
  if (!record || typeof record !== "object") return false;

  for (const field of PROVENANCE_REQUIRED_NON_NULL_FIELDS) {
    if (!Object.prototype.hasOwnProperty.call(record, field)) return false;
    if (record[field] === null || record[field] === undefined) return false;
  }

  return DECISION_VALUES.has(String(record.decision ?? ""));
}

export function buildPersistedProvenanceRecord({
  row,
  ticker,
  runId,
  generatedAtUtc,
  snapshotTimestampUtc,
  runtimeSyncCompletedUtc,
  policyRuntime,
  minBars,
  writerBuildHash,
  writerComponent = DEFAULT_WRITER_COMPONENT,
  provenanceSchemaVersion = DEFAULT_PROVENANCE_SCHEMA_VERSION,
  cpProfile = DEFAULT_CP_PROFILE,
}) {
  const normalizedTicker = normalizeTicker(ticker ?? row?.ticker);
  const snapshotRow = normalizeDecisionTraceRow({ ...(row && typeof row === "object" ? row : {}), ticker: normalizedTicker });
  const snapshotTimestamp = String(snapshotTimestampUtc ?? generatedAtUtc ?? "").trim() || new Date().toISOString();
  const runtimeSyncCompleted = String(runtimeSyncCompletedUtc ?? generatedAtUtc ?? "").trim() || snapshotTimestamp;
  const decisionTimestampUtc = String(generatedAtUtc ?? "").trim() || snapshotTimestamp;
  const provenanceGeneratedUtc = new Date().toISOString();
  const effectiveWriterBuildHash =
    String(writerBuildHash ?? "").trim() || sha256Hex(`${writerComponent}:${provenanceSchemaVersion}:${PRIMITIVE_ARTIFACT_ID}`);
  const runtimeArtifact = policyRuntime && typeof policyRuntime === "object" ? policyRuntime : loadPolicyRuntimeArtifact(null);
  const trace = computeDecisionTrace(snapshotRow, runtimeArtifact, minBars);

  const structuralRecency = extractStructuralRecencyComponents(snapshotRow);
  const epochComponents = extractEpochComponents(snapshotRow);

  const record = {
    ticker: normalizedTicker,
    run_id: String(runId ?? "").trim(),
    snapshot_timestamp_utc: snapshotTimestamp,
    runtime_sync_completed_utc: runtimeSyncCompleted,
    generated_at_utc: decisionTimestampUtc,
    decision_timestamp_utc: decisionTimestampUtc,
    snapshot_row_digest_sha256: sha256Hex(stableStringify(snapshotRow)),
    policy_artifact_id: String(runtimeArtifact.policy_artifact_id ?? PRIMITIVE_ARTIFACT_ID),
    policy_artifact_hash_sha256: String(runtimeArtifact.policy_artifact_hash_sha256 ?? PRIMITIVE_ARTIFACT_HASH),
    policy_source_mode: String(runtimeArtifact.policy_source_mode ?? "gemini_l5_primitive"),
    candidate_key_chain_json: trace.candidateKeyChain,
    matched_key: trace.matchedKey,
    match_level: trace.matchLevel,
    fallback_ladder_level: trace.fallbackLadderLevel,
    matched_exact_bool: trace.matchedExactBool,
    fallback_used: trace.fallbackUsed,
    fallback_reason_code: trace.fallbackReasonCode,
    decision: decisionLabel(trace.decision),
    decision_reason_code: trace.decisionReasonCode,
    anomaly_flags_used_json: trace.anomalyFlags,
    structural_recency_components_used_json: structuralRecency,
    epoch_components_used_json: epochComponents,
    coverage_class: trace.coverageClass,
    provenance_schema_version: provenanceSchemaVersion,
    writer_component: writerComponent,
    writer_build_hash: effectiveWriterBuildHash,
    cp_profile: cpProfile,
    provenance_generated_utc: provenanceGeneratedUtc,
  };

  record.provenance_valid = isProvenanceRecordValid(record);
  record.provenance_json = {
    run_id: record.run_id,
    ticker: record.ticker,
    snapshot_timestamp_utc: record.snapshot_timestamp_utc,
    runtime_sync_completed_utc: record.runtime_sync_completed_utc,
    decision_timestamp_utc: record.decision_timestamp_utc,
    policy_artifact_id: record.policy_artifact_id,
    policy_artifact_hash_sha256: record.policy_artifact_hash_sha256,
    policy_source_mode: record.policy_source_mode,
    candidate_key_chain_json: record.candidate_key_chain_json,
    matched_key: record.matched_key,
    match_level: record.match_level,
    fallback_ladder_level: record.fallback_ladder_level,
    matched_exact_bool: record.matched_exact_bool,
    fallback_used: record.fallback_used,
    fallback_reason_code: record.fallback_reason_code,
    decision: record.decision,
    decision_reason_code: record.decision_reason_code,
    anomaly_flags_used_json: record.anomaly_flags_used_json,
    structural_recency_components_used_json: record.structural_recency_components_used_json,
    epoch_components_used_json: record.epoch_components_used_json,
    coverage_class: record.coverage_class,
    provenance_schema_version: record.provenance_schema_version,
    writer_component: record.writer_component,
    writer_build_hash: record.writer_build_hash,
    cp_profile: record.cp_profile,
    provenance_generated_utc: record.provenance_generated_utc,
    snapshot_row_digest_sha256: record.snapshot_row_digest_sha256,
    provenance_valid: record.provenance_valid,
  };

  return record;
}

export function buildIdentityWitness(record) {
  return {
    run_id: String(record?.run_id ?? ""),
    ticker: String(record?.ticker ?? ""),
    snapshot_row_digest_sha256: String(record?.snapshot_row_digest_sha256 ?? ""),
    policy_artifact_hash_sha256: String(record?.policy_artifact_hash_sha256 ?? ""),
  };
}
