import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const FALLBACK_DECISION = "Hold";
const DECISION_VALUES = new Set(["Accumulate", "Hold", "Avoid"]);
const DEFAULT_PROVENANCE_SCHEMA_VERSION = "v1";
const DEFAULT_WRITER_COMPONENT = "web/scripts/sync_runtime_postgres.mjs";
const DEFAULT_CP_PROFILE = "CP-0";
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
    description: "Exact matched key with no fallback.",
  },
  {
    id: "L1_RELAXED_STRUCTURAL_MATCH",
    order: 1,
    structural_coverage: true,
    exact_structural: false,
    quality_assessed_under_current_contract: true,
    description: "Matched via allowed candidate-key relaxation path.",
  },
  {
    id: "L2_SAFE_POLICY_FALLBACK",
    order: 2,
    structural_coverage: false,
    exact_structural: false,
    quality_assessed_under_current_contract: false,
    description: "Safe fallback path used instead of a reliable structural recommendation.",
  },
  {
    id: "L3_DEGRADED_UNMAPPED",
    order: 3,
    structural_coverage: false,
    exact_structural: false,
    quality_assessed_under_current_contract: false,
    description: "Policy missing, cell unavailable, or structurally unmapped/degraded.",
  },
  {
    id: "L4_UNAVAILABLE_OR_BLOCKED",
    order: 4,
    structural_coverage: false,
    exact_structural: false,
    quality_assessed_under_current_contract: false,
    description: "Unavailable or blocked due to insufficiency/incompleteness at decision time.",
  },
];

export const TYPED_FALLBACK_ORTHOGONAL_FLAGS = [
  "anomaly_flag",
  "freshness_or_stale_flag",
  "provenance_source",
  "insufficiency_or_block_reason_code",
  "matched_exact_bool",
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

export function normalizeTicker(value) {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeBoolean(value, fallback = false) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const text = value.trim().toLowerCase();
    if (["1", "true", "yes", "on", "y"].includes(text)) return true;
    if (["0", "false", "no", "off", "n", ""].includes(text)) return false;
  }
  return fallback;
}

function toFinite(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

function toInt(value) {
  const n = toFinite(value);
  if (n === null) return null;
  return Math.trunc(n);
}

function toBoolean(value) {
  return normalizeBoolean(value, false);
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

function anomalyFallbackEnabled() {
  return normalizeBoolean(process.env.TFE_RECOMMENDATIONS_ANOMALY_FALLBACK, false);
}

function sign3(value) {
  if (value > 0) return 1;
  if (value < 0) return -1;
  return 0;
}

function toRecord(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value;
}

function dvValue(row, index) {
  const dv = row.decision_vector;
  if (!Array.isArray(dv)) return null;
  if (index < 0 || index >= dv.length) return null;
  return toFinite(dv[index]);
}

function rowNumberField(row, key) {
  return toFinite(row[key]);
}

function resolveBasis(row) {
  const regime = String(row?.regime ?? "UNKNOWN");

  let dVal = dvValue(row, 0);
  if (dVal === null) dVal = rowNumberField(row, "D_k");

  let mVal = dvValue(row, 1);
  if (mVal === null) mVal = rowNumberField(row, "M_k");

  let rVal = dvValue(row, 2);
  if (rVal === null) rVal = rowNumberField(row, "R_rev_k");

  let uVal = dvValue(row, 3);
  if (uVal === null) uVal = rowNumberField(row, "U_star_k");

  const dv = row.decision_vector;
  const dvLen = Array.isArray(dv) ? dv.length : 0;

  let cVal = null;
  let pVal = null;
  let bVal = null;

  if (dvLen >= 7) {
    cVal = dvValue(row, 4);
    pVal = dvValue(row, 5);
    bVal = dvValue(row, 6);
  } else if (dvLen >= 6) {
    pVal = dvValue(row, 4);
    bVal = dvValue(row, 5);
  }

  if (cVal === null) cVal = rowNumberField(row, "C_k");
  if (pVal === null) pVal = rowNumberField(row, "P_k");
  if (bVal === null) bVal = rowNumberField(row, "B_k");

  const basis = {
    regime,
    D_k: dVal === null ? null : Math.round(dVal),
    M_k: mVal,
    M_sign: mVal === null ? null : sign3(mVal),
    R_rev_k: rVal === null ? null : (rVal > 0.5 ? 1 : 0),
    U_star_k: uVal,
    C_k: cVal === null ? null : Math.round(cVal),
    P_k: pVal === null ? null : Math.round(pVal),
    B_k: bVal === null ? null : sign3(bVal),
    missing_fields: [],
  };

  if (basis.D_k === null) basis.missing_fields.push("D_k");
  if (basis.M_k === null) basis.missing_fields.push("M_k");
  if (basis.R_rev_k === null) basis.missing_fields.push("R_rev_k");
  if (basis.U_star_k === null) basis.missing_fields.push("U_star_k");
  if (basis.C_k === null) basis.missing_fields.push("C_k");
  if (basis.P_k === null) basis.missing_fields.push("P_k");
  if (basis.B_k === null) basis.missing_fields.push("B_k");

  return basis;
}

function uBucket(value) {
  if (value < 0.33) return "U0";
  if (value < 0.66) return "U1";
  return "U2";
}

function pBucket(value) {
  if (value <= 0) return "P0";
  if (value === 1) return "P1";
  return "P2";
}

function bucket3(value) {
  if (value < 0.33) return "B0";
  if (value < 0.66) return "B1";
  return "B2";
}

function bucketCdOpt(value) {
  if (value < -0.6) return "B0";
  if (value < -0.4) return "B1";
  if (value < -0.3) return "B2";
  if (value < -0.2) return "B3";
  return "B4";
}

function bucketStability(value) {
  if (value < 0.33) return "B0";
  if (value < 0.66) return "B1";
  return "B2";
}

function irfPhase(mSign, rUf) {
  if (rUf < 0.33 && mSign > 0) return "U2UP";
  if (rUf > 0.66 && mSign < 0) return "U2DN";
  return "UFLAT";
}

function anomalyFlagsFromRow(row) {
  const guard = toRecord(row.decision_guard);
  const guardGateUnlock = guard
    ? toBoolean(guard.gate_unlock_transient_neutralized)
    : toBoolean(row.gate_unlock_transient_neutralized);

  const hardening = toRecord(row.hardening);
  const hardeningFlags = hardening ? toRecord(hardening.flags) : null;
  const hardeningHysteresisOverload = hardeningFlags
    ? toBoolean(hardeningFlags.hysteresis_overload)
    : toBoolean(row.hysteresis_overload);

  return {
    guard_gate_unlock_transient_neutralized: guardGateUnlock,
    hardening_hysteresis_overload: hardeningHysteresisOverload,
    anomaly_any: guardGateUnlock || hardeningHysteresisOverload,
  };
}

function spiderEyesTag(flags) {
  if (flags.guard_gate_unlock_transient_neutralized && flags.hardening_hysteresis_overload) return "GU_HO";
  if (flags.guard_gate_unlock_transient_neutralized) return "GU";
  if (flags.hardening_hysteresis_overload) return "HO";
  return "NONE";
}

function suffixVariants(core, phaseTag, spiderTag) {
  const keys = [];
  if (phaseTag && spiderTag) keys.push(`${core}${phaseTag}${spiderTag}`);
  if (phaseTag) keys.push(`${core}${phaseTag}`);
  if (spiderTag) keys.push(`${core}${spiderTag}`);
  keys.push(core);
  return keys;
}

function uniqueStrings(values) {
  const out = [];
  const seen = new Set();
  for (const value of values) {
    const text = String(value ?? "");
    if (!text || seen.has(text)) continue;
    seen.add(text);
    out.push(text);
  }
  return out;
}

function exactFamilyOrder(exactAnchorMode = DEFAULT_PSCF_EXACT_ANCHOR_MODE) {
  if (exactAnchorMode === CURRENT_ST_ANCHORED_EXACT_FAMILY) {
    return ["enrichedCdSt", "enrichedSrSt", "enrichedCd", "enrichedSr", "baseSpider", "baseOnly"];
  }

  return ["enrichedCd", "enrichedCdSt", "enrichedSrSt", "enrichedSr", "baseSpider", "baseOnly"];
}

function keyCandidates(row, basis, anomalyFlags, exactAnchorMode = DEFAULT_PSCF_EXACT_ANCHOR_MODE) {
  if (basis.missing_fields.length > 0) return [];

  const base =
    `reg=${basis.regime}|D=${basis.D_k}|M=${basis.M_sign}|Rrev=${basis.R_rev_k}|` +
    `${uBucket(basis.U_star_k)}|C=${basis.C_k}|${pBucket(basis.P_k)}|B=${basis.B_k}`;

  const sUf = toFinite(row.S_UF) ?? 0;
  const rUf = toFinite(row.R_UF) ?? 0;
  const cd = sUf - rUf;
  const st = bucketStability(toFinite(row.stability_score) ?? 0);
  const phaseTag = `|PH=${irfPhase(basis.M_sign ?? 0, rUf)}`;
  const spiderTag = `|SE=${spiderEyesTag(anomalyFlags)}`;

  const familyKeys = {
    enrichedCdSt: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|CD=${bucketCdOpt(cd)}|ST=${st}`,
    enrichedSrSt: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|ST=${st}`,
    enrichedCd: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|CD=${bucketCdOpt(cd)}`,
    enrichedSr: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}`,
    baseSpider: `${base}|SE=${spiderEyesTag(anomalyFlags)}`,
    baseOnly: base,
  };

  const keys = [];
  for (const familyId of exactFamilyOrder(exactAnchorMode)) {
    if (familyId === "baseSpider") {
      keys.push(familyKeys.baseSpider);
      continue;
    }
    if (familyId === "baseOnly") {
      keys.push(familyKeys.baseOnly);
      continue;
    }
    keys.push(...suffixVariants(familyKeys[familyId], phaseTag, spiderTag));
  }

  return uniqueStrings(keys);
}

function decisionLabel(value) {
  if (DECISION_VALUES.has(value)) return value;
  return FALLBACK_DECISION;
}

function extractStructuralRecencyComponents(row) {
  const components = {};
  for (const [key, value] of Object.entries(row)) {
    if (key.startsWith("steps_since_")) {
      components[key] = value;
      continue;
    }
    if (key.includes("recency")) {
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

export function deriveTypedFallbackLadderLevel({ decisionReasonCode, matchedIndex }) {
  const reasonCode = String(decisionReasonCode ?? "").trim();
  const index = Number.isFinite(Number(matchedIndex)) ? Number(matchedIndex) : -1;

  if (reasonCode === "PSCF_POLICY_DECISION") {
    if (index === 0) return "L0_EXACT_STRUCTURAL_MATCH";
    if (index > 0) return "L1_RELAXED_STRUCTURAL_MATCH";
  }

  if (reasonCode === "PSCF_FALLBACK_ANOMALOUS") {
    return "L2_SAFE_POLICY_FALLBACK";
  }

  if (
    reasonCode === "PSCF_FALLBACK_POLICY_MISSING" ||
    reasonCode === "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE" ||
    reasonCode === "PSCF_FALLBACK_CELL_UNMAPPED"
  ) {
    return "L3_DEGRADED_UNMAPPED";
  }

  if (
    reasonCode === "PSCF_FALLBACK_INSUFFICIENT_BARS" ||
    reasonCode === "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE"
  ) {
    return "L4_UNAVAILABLE_OR_BLOCKED";
  }

  return "L3_DEGRADED_UNMAPPED";
}

function matchLevelFromDecision(decisionReasonCode, matchedIndex) {
  if (decisionReasonCode !== "PSCF_POLICY_DECISION") {
    return "L3_ABSTAIN_HOLD_ONLY";
  }

  if (!Number.isFinite(matchedIndex) || matchedIndex < 0) {
    return "L3_ABSTAIN_HOLD_ONLY";
  }
  if (matchedIndex === 0) return "L0_EXACT_STRUCTURAL_KEY";
  if (matchedIndex <= 5) return "L1_EXACT_CORE_RELAXED_SUFFIX";
  return "L2_REGIME_RECENCY_CORE_RELAXED_BUCKETS";
}

function coverageClassFromTrace(decisionReasonCode, matchedIndex) {
  if (decisionReasonCode !== "PSCF_POLICY_DECISION") return "fallback";
  if (matchedIndex === 0) return "exact";
  if (matchedIndex > 0) return "degraded";
  return "fallback";
}

export function computeDecisionTrace(
  row,
  policyRuntime,
  minBars,
  exactAnchorMode = DEFAULT_PSCF_EXACT_ANCHOR_MODE,
) {
  const basis = resolveBasis(row);
  const anomalyFlags = anomalyFlagsFromRow(row);
  const candidates = keyCandidates(row, basis, anomalyFlags, exactAnchorMode);
  const barCount = Math.max(0, toInt(row.bar_count) ?? 0);

  const cells = policyRuntime?.cells && typeof policyRuntime.cells === "object" ? policyRuntime.cells : null;

  let decision = FALLBACK_DECISION;
  let decisionReasonCode = "PSCF_FALLBACK_POLICY_MISSING";
  let fallbackReasonCode = "policy_missing";
  let matchedKey = null;
  let matchedIndex = -1;

  if (barCount < minBars) {
    decisionReasonCode = "PSCF_FALLBACK_INSUFFICIENT_BARS";
    fallbackReasonCode = "insufficient_bars";
  } else if (basis.missing_fields.length > 0) {
    decisionReasonCode = "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE";
    fallbackReasonCode = "structural_incomplete";
  } else if (!cells || Object.keys(cells).length === 0) {
    decisionReasonCode = "PSCF_FALLBACK_POLICY_MISSING";
    fallbackReasonCode = "policy_missing";
  } else if (candidates.length === 0) {
    decisionReasonCode = "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE";
    fallbackReasonCode = "cell_key_unavailable";
  } else {
    for (let index = 0; index < candidates.length; index += 1) {
      const candidate = candidates[index];
      const cell = cells[candidate];
      if (!cell || typeof cell !== "object") continue;
      matchedKey = candidate;
      matchedIndex = index;
      break;
    }

    if (!matchedKey) {
      decisionReasonCode = "PSCF_FALLBACK_CELL_UNMAPPED";
      fallbackReasonCode = "cell_unmapped";
    } else if (anomalyFallbackEnabled() && anomalyFlags.anomaly_any) {
      decisionReasonCode = "PSCF_FALLBACK_ANOMALOUS";
      fallbackReasonCode = "anomalous_row";
    } else {
      const matchedCell = cells[matchedKey] ?? {};
      decision = decisionLabel(matchedCell.decision);
      decisionReasonCode = "PSCF_POLICY_DECISION";
      fallbackReasonCode = null;
    }
  }

  const fallbackUsed = decisionReasonCode !== "PSCF_POLICY_DECISION";
  const matchLevel = matchLevelFromDecision(decisionReasonCode, matchedIndex);
  const fallbackLadderLevel = deriveTypedFallbackLadderLevel({
    decisionReasonCode,
    matchedIndex,
  });
  const coverageClass = coverageClassFromTrace(decisionReasonCode, matchedIndex);

  return {
    basis,
    anomalyFlags,
    candidateKeyChain: candidates,
    matchedKey,
    matchedIndex,
    matchLevel,
    fallbackLadderLevel,
    matchedExactBool: matchedIndex === 0,
    fallbackUsed,
    fallbackReasonCode,
    decision,
    decisionReasonCode,
    coverageClass,
  };
}

export function loadPolicyRuntimeArtifact(rootDir) {
  const configured = String(process.env.TFE_PSCF_POLICY_PATH ?? "").trim();
  const candidates = [];
  if (configured) candidates.push(path.resolve(configured));
  candidates.push(path.resolve(rootDir, "pscf_policy_runtime.json"));
  candidates.push(path.resolve(rootDir, "backups", "runtime", "pscf_policy_runtime.json"));

  for (const candidate of candidates) {
    if (!existsSync(candidate)) continue;
    try {
      const raw = readFileSync(candidate, "utf-8");
      const payload = JSON.parse(raw);
      if (!payload || typeof payload !== "object" || Array.isArray(payload)) continue;
      const cells = payload.cells && typeof payload.cells === "object" ? payload.cells : {};
      const generatedAtUtc = typeof payload.generated_at_utc === "string" ? payload.generated_at_utc : null;
      const artifactHash = sha256Hex(raw);
      return {
        source_path: candidate,
        policy_artifact_id: path.basename(candidate),
        policy_artifact_hash_sha256: artifactHash,
        policy_source_mode: String(process.env.TFE_POLICY_SOURCE_MODE ?? "runtime_file") || "runtime_file",
        generated_at_utc: generatedAtUtc,
        cells,
      };
    } catch {
      // Try next candidate.
    }
  }

  return {
    source_path: null,
    policy_artifact_id: "policy_unavailable",
    policy_artifact_hash_sha256: sha256Hex("policy_unavailable"),
    policy_source_mode: String(process.env.TFE_POLICY_SOURCE_MODE ?? "runtime_file") || "runtime_file",
    generated_at_utc: null,
    cells: {},
  };
}

function isNonEmptyArray(value) {
  return Array.isArray(value) && value.length > 0;
}

export function isProvenanceRecordValid(record) {
  for (const field of PROVENANCE_REQUIRED_NON_NULL_FIELDS) {
    const value = record[field];
    if (value === null || value === undefined) return false;
    if (typeof value === "string" && !value.trim()) return false;
    if ((field === "candidate_key_chain_json" || field.endsWith("_json")) && !Array.isArray(value) && typeof value !== "object") {
      return false;
    }
  }

  if (!isNonEmptyArray(record.candidate_key_chain_json) && record.decision_reason_code === "PSCF_POLICY_DECISION") {
    return false;
  }

  return true;
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
  const snapshotRow = { ...(row && typeof row === "object" ? row : {}), ticker: normalizedTicker };
  const snapshotTimestamp = String(snapshotTimestampUtc ?? generatedAtUtc ?? "").trim() || new Date().toISOString();
  const runtimeSyncCompleted = String(runtimeSyncCompletedUtc ?? generatedAtUtc ?? "").trim() || snapshotTimestamp;
  const decisionTimestampUtc = String(generatedAtUtc ?? "").trim() || snapshotTimestamp;
  const provenanceGeneratedUtc = new Date().toISOString();
  const effectiveWriterBuildHash =
    String(writerBuildHash ?? "").trim() || sha256Hex(`${writerComponent}:${provenanceSchemaVersion}`);
  const trace = computeDecisionTrace(snapshotRow, policyRuntime, minBars);

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
    policy_artifact_id: String(policyRuntime?.policy_artifact_id ?? "policy_unavailable"),
    policy_artifact_hash_sha256: String(policyRuntime?.policy_artifact_hash_sha256 ?? sha256Hex("policy_unavailable")),
    policy_source_mode: String(policyRuntime?.policy_source_mode ?? "runtime_file"),
    candidate_key_chain_json: trace.candidateKeyChain,
    matched_key: trace.matchedKey,
    match_level: trace.matchLevel,
    fallback_ladder_level: trace.fallbackLadderLevel,
    matched_exact_bool: trace.matchedExactBool,
    fallback_used: trace.fallbackUsed,
    fallback_reason_code: trace.fallbackReasonCode,
    decision: trace.decision,
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
