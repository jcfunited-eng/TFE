import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { decryptEnvelopeToJson } from "@/lib/ses-web-blob";

export type DecisionLabel = "Accumulate" | "Hold" | "Avoid";
export type Classification = "BUY" | "HOLD" | "SELL";

export type SnapshotRow = {
  ticker?: string;
  S_UF?: number | string;
  R_UF?: number | string;
  asset_type?: string;
  price?: number | string;
  regime?: string;
  decision_vector?: unknown;
  bar_count?: number | string;
  [key: string]: unknown;
};

export type DecisionReasonCode =
  | "ROW_NOT_FOUND"
  | "PSCF_POLICY_DECISION"
  | "PSCF_FALLBACK_INSUFFICIENT_BARS"
  | "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE"
  | "PSCF_FALLBACK_POLICY_MISSING"
  | "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE"
  | "PSCF_FALLBACK_CELL_UNMAPPED"
  | "PSCF_FALLBACK_ANOMALOUS";

export type DecisionProvenance = {
  policySourcePath: string | null;
  policyGeneratedAtUtc: string | null;
  policyMatched: boolean;
  policyCellKeyRequested: string | null;
  policyCellKeyMatched: string | null;
  policyScoringMode: string | null;
  fallbackUsed: boolean;
  fallbackReason: string | null;
  anomalyFlagged: boolean;
  structuralComplete: boolean;
  structuralMissingFields: string[];
  l4Vector: {
    regime: string;
    D_k: number | null;
    M_k: number | null;
    M_sign: number | null;
    R_rev_k: number | null;
    U_star_k: number | null;
    C_k: number | null;
    P_k: number | null;
    B_k: number | null;
  };
};

export type DecisionInfo = {
  decision: DecisionLabel;
  reasonCode: DecisionReasonCode;
  reasonText: string;
  barCount: number;
  minBarsForAccumulate: number;
  provenance: DecisionProvenance;
};

type AttemptFailure = {
  path: string;
  reason: string;
};

type SnapshotEnvelopeCache = {
  cacheKey: string;
  sourcePath: string;
  rows: SnapshotRow[];
};

type PscfPolicyCell = {
  decision?: unknown;
  mean_excess_vs_spy?: unknown;
  scoring_mode?: unknown;
  anomaly_profile?: {
    anomaly_any_rate_pct?: unknown;
    [key: string]: unknown;
  };
  [key: string]: unknown;
};

type PscfPolicyPayload = {
  generated_at_utc?: unknown;
  cells?: Record<string, PscfPolicyCell>;
  [key: string]: unknown;
};

type PscfPolicyRuntime = {
  policy: PscfPolicyPayload | null;
  sourcePath: string | null;
  attemptedPaths: string[];
  failures: AttemptFailure[];
};

type StructuralBasis = {
  regime: string;
  D_k: number | null;
  M_k: number | null;
  M_sign: number | null;
  R_rev_k: number | null;
  U_star_k: number | null;
  C_k: number | null;
  P_k: number | null;
  B_k: number | null;
  missingFields: string[];
};

const SNAPSHOT_ENVELOPE_FILENAME = "uf_snapshot.ses.json";
const SNAPSHOT_ENVELOPE_BACKUP_FILENAME = "uf_snapshot_old_backup.ses.json";
const SNAPSHOT_PLAINTEXT_FILENAME = "uf_snapshot.json";
const SNAPSHOT_SES_PURPOSE = "uf-snapshot";
const SNAPSHOT_SES_ACTOR = "web-snapshot-pipeline";
const SNAPSHOT_SES_ASSET = "uf_snapshot:web";
const PSCF_POLICY_FILENAME = "pscf_policy_runtime.json";
const PSCF_POLICY_FALLBACK_FILENAME = "pscf-policy-anomaly-watch-20260218T142043Z.json";
export type PscfExactAnchorMode =
  | "CURRENT_ST_ANCHORED_EXACT_FAMILY"
  | "NO_ST_EXACT_FAMILY_KEEP_CD_PHASE_SPIDER_STRICT";
const PSCF_EXACT_ANCHOR_MODE: PscfExactAnchorMode = "NO_ST_EXACT_FAMILY_KEEP_CD_PHASE_SPIDER_STRICT";
function normalizeMinBars(value: unknown, fallback: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  const whole = Math.floor(n);
  if (whole < 20) return 20;
  if (whole > 2520) return 2520;
  return whole;
}

function normalizeBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const text = value.trim().toLowerCase();
    if (["1", "true", "yes", "on", "y"].includes(text)) return true;
    if (["0", "false", "no", "off", "n", ""].includes(text)) return false;
  }
  return fallback;
}

export const ACCUMULATE_MIN_BARS = normalizeMinBars(process.env.TFE_RECOMMENDATIONS_MIN_BARS, 180);
const ANOMALY_FALLBACK_ENABLED = normalizeBoolean(process.env.TFE_RECOMMENDATIONS_ANOMALY_FALLBACK, false);
const PSCF_FALLBACK_DECISION: DecisionLabel = "Hold";
const SNAPSHOT_SES_ACTOR_CANDIDATES = actorCandidates();

let SNAPSHOT_CACHE: SnapshotEnvelopeCache | null = null;
let SNAPSHOT_CACHE_INFLIGHT: { cacheKey: string; promise: Promise<SnapshotRow[]> } | null = null;
let SNAPSHOT_PRIME_STARTED = false;
const DECISION_INFO_CACHE = new WeakMap<SnapshotRow, DecisionInfo>();

function actorCandidates(): string[] {
  const configured = String(process.env.TFE_SNAPSHOT_SES_ACTOR_IDS ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);

  if (configured.length > 0) {
    return Array.from(new Set(configured));
  }

  return [SNAPSHOT_SES_ACTOR];
}

function uniquePaths(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];

  for (const value of values) {
    const normalized = path.normalize(value);
    if (seen.has(normalized)) continue;
    seen.add(normalized);
    out.push(normalized);
  }

  return out;
}

function snapshotCacheKey(filePath: string): string {
  const stats = statSync(filePath);
  return `${path.normalize(filePath)}|${Math.floor(stats.mtimeMs)}|${stats.size}`;
}

function snapshotCandidates(): string[] {
  const cwd = process.cwd();

  return uniquePaths([
    path.resolve(cwd, SNAPSHOT_ENVELOPE_FILENAME),
    path.resolve(cwd, "..", SNAPSHOT_ENVELOPE_FILENAME),
    path.resolve(cwd, "..", "..", SNAPSHOT_ENVELOPE_FILENAME),
    path.resolve("/workspaces/Tao_Financial_Engine", SNAPSHOT_ENVELOPE_FILENAME),
    path.resolve(cwd, SNAPSHOT_ENVELOPE_BACKUP_FILENAME),
    path.resolve(cwd, "..", SNAPSHOT_ENVELOPE_BACKUP_FILENAME),
    path.resolve(cwd, "..", "..", SNAPSHOT_ENVELOPE_BACKUP_FILENAME),
    path.resolve("/workspaces/Tao_Financial_Engine", SNAPSHOT_ENVELOPE_BACKUP_FILENAME),
  ]);
}

function snapshotPlaintextCandidates(): string[] {
  const cwd = process.cwd();

  return uniquePaths([
    path.resolve(cwd, SNAPSHOT_PLAINTEXT_FILENAME),
    path.resolve(cwd, "..", SNAPSHOT_PLAINTEXT_FILENAME),
    path.resolve(cwd, "..", "..", SNAPSHOT_PLAINTEXT_FILENAME),
    path.resolve("/workspaces/Tao_Financial_Engine", SNAPSHOT_PLAINTEXT_FILENAME),
  ]);
}

function policyCandidates(): string[] {
  const cwd = process.cwd();
  const envPath = String(process.env.TFE_PSCF_POLICY_PATH ?? "").trim();

  const out: string[] = [];

  if (envPath) {
    out.push(path.resolve(envPath));
  }

  out.push(path.resolve(cwd, PSCF_POLICY_FILENAME));
  out.push(path.resolve(cwd, "..", PSCF_POLICY_FILENAME));
  out.push(path.resolve(cwd, "..", "..", PSCF_POLICY_FILENAME));

  out.push(path.resolve("/workspaces/Tao_Financial_Engine", PSCF_POLICY_FILENAME));
  out.push(path.resolve("/workspaces/Tao_Financial_Engine", "backups", PSCF_POLICY_FALLBACK_FILENAME));

  return uniquePaths(out);
}

function parseEnvelopeRows(payload: unknown): SnapshotRow[] {
  if (Array.isArray(payload)) {
    return payload as SnapshotRow[];
  }

  if (payload && typeof payload === "object") {
    const obj = payload as { rows?: unknown };
    if (Array.isArray(obj.rows)) {
      return obj.rows as SnapshotRow[];
    }
  }

  return [];
}

function loadRowsFromPlaintextSnapshot(filePath: string): SnapshotRow[] {
  const text = readFileSync(filePath, "utf-8");
  const normalized = text
    .replace(/\bNaN\b/g, "null")
    .replace(/\b-Infinity\b/g, "null")
    .replace(/\bInfinity\b/g, "null");
  const parsed = JSON.parse(normalized) as unknown;
  return parseEnvelopeRows(parsed);
}

function parsePscfPolicy(text: string): PscfPolicyPayload | null {
  const parsed = JSON.parse(text);

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return null;
  }

  const cells = (parsed as { cells?: unknown }).cells;
  if (!cells || typeof cells !== "object" || Array.isArray(cells)) {
    return null;
  }

  return parsed as PscfPolicyPayload;
}

function loadPscfPolicyRuntime(): PscfPolicyRuntime {
  const attemptedPaths = policyCandidates();
  const failures: AttemptFailure[] = [];

  for (const candidate of attemptedPaths) {
    try {
      const text = readFileSync(candidate, "utf-8");
      const policy = parsePscfPolicy(text);

      if (!policy || !policy.cells || Object.keys(policy.cells).length === 0) {
        failures.push({ path: candidate, reason: "File parsed but no policy cells were available." });
        continue;
      }

      return {
        policy,
        sourcePath: candidate,
        attemptedPaths,
        failures,
      };
    } catch (error) {
      const reason = error instanceof Error ? error.message : "Unknown policy read/parse error";
      failures.push({ path: candidate, reason });
    }
  }

  return {
    policy: null,
    sourcePath: null,
    attemptedPaths,
    failures,
  };
}

const PSCF_POLICY_RUNTIME = loadPscfPolicyRuntime();

async function loadRowsFromEnvelope(envelopePath: string): Promise<SnapshotRow[]> {
  if (!existsSync(envelopePath)) {
    throw new Error(`Envelope path not found: ${envelopePath}`);
  }

  const failures: string[] = [];

  for (const actorId of SNAPSHOT_SES_ACTOR_CANDIDATES) {
    try {
      const payload = await decryptEnvelopeToJson<unknown>({
        envelopePath,
        purposeSuffix: SNAPSHOT_SES_PURPOSE,
        actorId,
        assetId: SNAPSHOT_SES_ASSET,
      });
      return parseEnvelopeRows(payload);
    } catch (error) {
      const reason = error instanceof Error ? error.message : "Unknown decrypt failure";
      failures.push(`${actorId}: ${reason}`);
    }
  }

  throw new Error(
    `Snapshot envelope decrypt failed for actor candidates [${SNAPSHOT_SES_ACTOR_CANDIDATES.join(", ")}]. ${failures.join(" | ")}`,
  );
}

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toFiniteOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function toBoolean(value: unknown): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "on", "y"].includes(normalized)) return true;
    if (["0", "false", "no", "off", "n", ""].includes(normalized)) return false;
  }
  return false;
}

function sign3(value: number): number {
  if (value > 0) return 1;
  if (value < 0) return -1;
  return 0;
}

function decisionVectorValue(row: SnapshotRow, index: number): number | null {
  const dv = row.decision_vector;
  if (!Array.isArray(dv)) return null;
  const value = Number(dv[index]);
  return Number.isFinite(value) ? value : null;
}

function rowNumberField(row: SnapshotRow, key: string): number | null {
  return toFiniteOrNull(row[key]);
}

function uniqueStrings(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];

  for (const value of values) {
    if (seen.has(value)) continue;
    seen.add(value);
    out.push(value);
  }

  return out;
}

function resolveStructuralBasis(row: SnapshotRow): StructuralBasis {
  const regime = String(row.regime ?? "UNKNOWN");
  const barCount = Math.max(0, Math.floor(toNumber(row.bar_count)));

  let dVal = decisionVectorValue(row, 0);
  if (dVal === null) dVal = rowNumberField(row, "D_k");

  let mVal = decisionVectorValue(row, 1);
  if (mVal === null) mVal = rowNumberField(row, "M_k");

  let rVal = decisionVectorValue(row, 2);
  if (rVal === null) rVal = rowNumberField(row, "R_rev_k");

  let uVal = decisionVectorValue(row, 3);
  if (uVal === null) uVal = rowNumberField(row, "U_star_k");

  const dv = row.decision_vector;
  const dvLength = Array.isArray(dv) ? dv.length : 0;

  let cVal: number | null = null;
  let pVal: number | null = null;
  let bVal: number | null = null;

  if (dvLength >= 7) {
    cVal = decisionVectorValue(row, 4);
    pVal = decisionVectorValue(row, 5);
    bVal = decisionVectorValue(row, 6);
  } else if (dvLength >= 6) {
    pVal = decisionVectorValue(row, 4);
    bVal = decisionVectorValue(row, 5);
  }

  if (cVal === null) cVal = rowNumberField(row, "C_k");
  if (pVal === null) pVal = rowNumberField(row, "P_k");
  if (bVal === null) bVal = rowNumberField(row, "B_k");

  // For low-history rows, keep basis shape complete with neutral defaults so
  // provenance/L4 payload remains explicit; decisioning is still Hold-gated by
  // the insufficient-bars fallback rule.
  if (barCount < ACCUMULATE_MIN_BARS) {
    if (dVal === null) dVal = 0;
    if (mVal === null) mVal = 0;
    if (rVal === null) rVal = 0;
    if (uVal === null) uVal = 0;
    if (cVal === null) cVal = 0;
    if (pVal === null) pVal = 0;
    if (bVal === null) bVal = 0;
  }

  const D_k = dVal === null ? null : Math.round(dVal);
  const M_k = mVal;
  const M_sign = mVal === null ? null : sign3(mVal);
  const R_rev_k = rVal === null ? null : (rVal > 0.5 ? 1 : 0);
  const U_star_k = uVal;
  const C_k = cVal === null ? null : Math.round(cVal);
  const P_k = pVal === null ? null : Math.round(pVal);
  const B_k = bVal === null ? null : sign3(bVal);

  const missingFields: string[] = [];
  if (D_k === null) missingFields.push("D_k");
  if (M_k === null) missingFields.push("M_k");
  if (R_rev_k === null) missingFields.push("R_rev_k");
  if (U_star_k === null) missingFields.push("U_star_k");
  if (C_k === null) missingFields.push("C_k");
  if (P_k === null) missingFields.push("P_k");
  if (B_k === null) missingFields.push("B_k");

  return {
    regime,
    D_k,
    M_k,
    M_sign,
    R_rev_k,
    U_star_k,
    C_k,
    P_k,
    B_k,
    missingFields: uniqueStrings(missingFields),
  };
}

function uBucket(uStar: number): string {
  if (uStar < 0.33) return "U0";
  if (uStar < 0.66) return "U1";
  return "U2";
}

function pBucket(pValue: number): string {
  const pRounded = Math.round(pValue);
  if (pRounded <= 0) return "P0";
  if (pRounded === 1) return "P1";
  return "P2";
}

function bucket3(value: number): string {
  if (value < 0.33) return "B0";
  if (value < 0.66) return "B1";
  return "B2";
}

function bucketCdOpt(value: number): string {
  if (value < -0.6) return "B0";
  if (value < -0.4) return "B1";
  if (value < -0.3) return "B2";
  if (value < -0.2) return "B3";
  return "B4";
}

function bucketStability(value: number): string {
  if (value < 0.33) return "B0";
  if (value < 0.66) return "B1";
  return "B2";
}

function irfPhase(mSign: number, rUf: number): string {
  if (rUf < 0.33 && mSign > 0) return "U2UP";
  if (rUf > 0.66 && mSign < 0) return "U2DN";
  return "UFLAT";
}

function spiderEyesTagFromRow(row: SnapshotRow): string {
  const guard = asRecord(row.decision_guard);
  const guardGateUnlock = guard
    ? toBoolean(guard.gate_unlock_transient_neutralized)
    : toBoolean(row.gate_unlock_transient_neutralized);

  const hardening = asRecord(row.hardening);
  const hardeningFlags = hardening ? asRecord(hardening.flags) : null;
  const hardeningHysteresisOverload = hardeningFlags
    ? toBoolean(hardeningFlags.hysteresis_overload)
    : toBoolean(row.hysteresis_overload);

  if (guardGateUnlock && hardeningHysteresisOverload) return "GU_HO";
  if (guardGateUnlock) return "GU";
  if (hardeningHysteresisOverload) return "HO";
  return "NONE";
}

function spiderEyesSuffixFromRow(row: SnapshotRow): string {
  return `|SE=${spiderEyesTagFromRow(row)}`;
}

function suffixVariants(core: string, phaseTag: string, spiderTag: string): string[] {
  const out: string[] = [];
  if (phaseTag && spiderTag) out.push(`${core}${phaseTag}${spiderTag}`);
  if (phaseTag) out.push(`${core}${phaseTag}`);
  if (spiderTag) out.push(`${core}${spiderTag}`);
  out.push(core);
  return out;
}

function basePscfCellKeyFromBasis(basis: StructuralBasis): string | null {
  if (
    basis.D_k === null ||
    basis.M_sign === null ||
    basis.R_rev_k === null ||
    basis.U_star_k === null ||
    basis.C_k === null ||
    basis.P_k === null ||
    basis.B_k === null
  ) {
    return null;
  }

  return `reg=${basis.regime}|D=${basis.D_k}|M=${basis.M_sign}|Rrev=${basis.R_rev_k}|${uBucket(basis.U_star_k)}|C=${basis.C_k}|${pBucket(basis.P_k)}|B=${basis.B_k}`;
}

function exactFamilyOrder(exactAnchorMode: PscfExactAnchorMode): string[] {
  if (exactAnchorMode === "CURRENT_ST_ANCHORED_EXACT_FAMILY") {
    return ["enrichedCdSt", "enrichedSrSt", "enrichedCd", "enrichedSr", "baseSpider", "baseOnly"];
  }

  return ["enrichedCd", "enrichedCdSt", "enrichedSrSt", "enrichedSr", "baseSpider", "baseOnly"];
}

function pscfCellKeyCandidatesFromRow(
  row: SnapshotRow,
  basis: StructuralBasis,
  exactAnchorMode: PscfExactAnchorMode = PSCF_EXACT_ANCHOR_MODE,
): string[] {
  const base = basePscfCellKeyFromBasis(basis);
  if (!base) return [];

  const sUf = toNumber(row.S_UF);
  const rUf = toNumber(row.R_UF);
  const cd = sUf - rUf;
  const mSign = basis.M_sign ?? 0;
  const phaseTag = `|PH=${irfPhase(mSign, rUf)}`;
  const spiderTag = spiderEyesSuffixFromRow(row);
  const stabilityScore = toNumber(row.stability_score);
  const st = bucketStability(stabilityScore);

  const familyKeys = {
    enrichedCdSt: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|CD=${bucketCdOpt(cd)}|ST=${st}`,
    enrichedSrSt: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|ST=${st}`,
    enrichedCd: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|CD=${bucketCdOpt(cd)}`,
    enrichedSr: `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}`,
    baseSpider: `${base}|SE=${spiderEyesTagFromRow(row)}`,
    baseOnly: base,
  };

  const keys: string[] = [];
  for (const familyId of exactFamilyOrder(exactAnchorMode)) {
    if (familyId === "baseSpider") {
      keys.push(familyKeys.baseSpider);
      continue;
    }
    if (familyId === "baseOnly") {
      keys.push(familyKeys.baseOnly);
      continue;
    }
    keys.push(...suffixVariants(familyKeys[familyId as keyof typeof familyKeys], phaseTag, spiderTag));
  }

  return uniqueStrings(keys);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function anomalyFlagsFromRow(row: SnapshotRow): {
  anomalyAny: boolean;
  guardGateUnlock: boolean;
  hardeningHysteresisOverload: boolean;
} {
  const guard = asRecord(row.decision_guard);
  const guardGateUnlock = guard
    ? toBoolean(guard.gate_unlock_transient_neutralized)
    : toBoolean(row.gate_unlock_transient_neutralized);

  const hardening = asRecord(row.hardening);
  const hardeningFlags = hardening ? asRecord(hardening.flags) : null;
  const hardeningHysteresisOverload = hardeningFlags
    ? toBoolean(hardeningFlags.hysteresis_overload)
    : toBoolean(row.hysteresis_overload);

  return {
    anomalyAny: guardGateUnlock || hardeningHysteresisOverload,
    guardGateUnlock,
    hardeningHysteresisOverload,
  };
}

function policyDecisionLabel(value: unknown): DecisionLabel {
  if (value === "Accumulate" || value === "Hold" || value === "Avoid") {
    return value;
  }
  return "Hold";
}

function defaultProvenance(basis: StructuralBasis): DecisionProvenance {
  return {
    policySourcePath: PSCF_POLICY_RUNTIME.sourcePath,
    policyGeneratedAtUtc:
      PSCF_POLICY_RUNTIME.policy && typeof PSCF_POLICY_RUNTIME.policy.generated_at_utc === "string"
        ? PSCF_POLICY_RUNTIME.policy.generated_at_utc
        : null,
    policyMatched: false,
    policyCellKeyRequested: null,
    policyCellKeyMatched: null,
    policyScoringMode: null,
    fallbackUsed: true,
    fallbackReason: null,
    anomalyFlagged: false,
    structuralComplete: basis.missingFields.length === 0,
    structuralMissingFields: [...basis.missingFields],
    l4Vector: {
      regime: basis.regime,
      D_k: basis.D_k,
      M_k: basis.M_k,
      M_sign: basis.M_sign,
      R_rev_k: basis.R_rev_k,
      U_star_k: basis.U_star_k,
      C_k: basis.C_k,
      P_k: basis.P_k,
      B_k: basis.B_k,
    },
  };
}

function fallbackDecisionInfo(
  reasonCode: Exclude<DecisionReasonCode, "ROW_NOT_FOUND" | "PSCF_POLICY_DECISION">,
  reasonText: string,
  barCount: number,
  basis: StructuralBasis,
  extras?: Partial<DecisionProvenance>,
): DecisionInfo {
  const provenance = {
    ...defaultProvenance(basis),
    ...extras,
    fallbackUsed: true,
  };

  return {
    decision: PSCF_FALLBACK_DECISION,
    reasonCode,
    reasonText,
    barCount,
    minBarsForAccumulate: ACCUMULATE_MIN_BARS,
    provenance,
  };
}

function policyDecisionFromRow(
  row: SnapshotRow,
  exactAnchorMode: PscfExactAnchorMode = PSCF_EXACT_ANCHOR_MODE,
): DecisionInfo {
  const barCount = Math.max(0, Math.floor(toNumber(row.bar_count)));
  const basis = resolveStructuralBasis(row);
  const candidates = pscfCellKeyCandidatesFromRow(row, basis, exactAnchorMode);
  const requestedKey = candidates[0] ?? null;

  if (barCount < ACCUMULATE_MIN_BARS) {
    return fallbackDecisionInfo(
      "PSCF_FALLBACK_INSUFFICIENT_BARS",
      `Fallback to ${PSCF_FALLBACK_DECISION}: insufficient bar history (${barCount} < ${ACCUMULATE_MIN_BARS}).`,
      barCount,
      basis,
      {
        policyCellKeyRequested: requestedKey,
        fallbackReason: "insufficient_bars",
      },
    );
  }

  if (basis.missingFields.length > 0) {
    return fallbackDecisionInfo(
      "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE",
      `Fallback to ${PSCF_FALLBACK_DECISION}: missing required L4 fields (${basis.missingFields.join(", ")}).`,
      barCount,
      basis,
      {
        policyCellKeyRequested: requestedKey,
        fallbackReason: "structural_incomplete",
      },
    );
  }

  if (!PSCF_POLICY_RUNTIME.policy || !PSCF_POLICY_RUNTIME.policy.cells) {
    return fallbackDecisionInfo(
      "PSCF_FALLBACK_POLICY_MISSING",
      `Fallback to ${PSCF_FALLBACK_DECISION}: PSCF/L5 policy runtime is unavailable.`,
      barCount,
      basis,
      {
        policyCellKeyRequested: requestedKey,
        fallbackReason: "policy_missing",
      },
    );
  }

  if (candidates.length === 0) {
    return fallbackDecisionInfo(
      "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE",
      `Fallback to ${PSCF_FALLBACK_DECISION}: no policy cell key could be formed from row data.`,
      barCount,
      basis,
      {
        policyCellKeyRequested: requestedKey,
        fallbackReason: "cell_key_unavailable",
      },
    );
  }

  let matchedKey: string | null = null;
  let matchedCell: PscfPolicyCell | undefined;

  for (const candidate of candidates) {
    const cell = PSCF_POLICY_RUNTIME.policy.cells[candidate];
    if (!cell) continue;
    matchedKey = candidate;
    matchedCell = cell;
    break;
  }

  if (!matchedCell || !matchedKey) {
    return fallbackDecisionInfo(
      "PSCF_FALLBACK_CELL_UNMAPPED",
      `Fallback to ${PSCF_FALLBACK_DECISION}: no mapped PSCF/L5 cell for key ${requestedKey ?? "n/a"}.`,
      barCount,
      basis,
      {
        policyCellKeyRequested: requestedKey,
        fallbackReason: "cell_unmapped",
      },
    );
  }

  const anomaly = anomalyFlagsFromRow(row);
  if (ANOMALY_FALLBACK_ENABLED && anomaly.anomalyAny) {
    return fallbackDecisionInfo(
      "PSCF_FALLBACK_ANOMALOUS",
      `Fallback to ${PSCF_FALLBACK_DECISION}: anomaly flags active for mapped cell ${matchedKey}.`,
      barCount,
      basis,
      {
        policyMatched: true,
        policyCellKeyRequested: requestedKey,
        policyCellKeyMatched: matchedKey,
        policyScoringMode: String(matchedCell.scoring_mode ?? "unknown"),
        anomalyFlagged: true,
        fallbackReason: "anomalous_row",
      },
    );
  }

  const policyDecision = policyDecisionLabel(matchedCell.decision);
  const sourcePath = PSCF_POLICY_RUNTIME.sourcePath ? path.basename(PSCF_POLICY_RUNTIME.sourcePath) : "unknown";

  return {
    decision: policyDecision,
    reasonCode: "PSCF_POLICY_DECISION",
    reasonText: `PSCF/L5 policy decision ${policyDecision} from matched cell ${matchedKey} (source=${sourcePath}).`,
    barCount,
    minBarsForAccumulate: ACCUMULATE_MIN_BARS,
    provenance: {
      ...defaultProvenance(basis),
      policyMatched: true,
      policyCellKeyRequested: requestedKey,
      policyCellKeyMatched: matchedKey,
      policyScoringMode: String(matchedCell.scoring_mode ?? "unknown"),
      fallbackUsed: false,
      fallbackReason: null,
      anomalyFlagged: false,
    },
  };
}

export async function loadSnapshotRows(): Promise<{
  rows: SnapshotRow[];
  sourcePath: string | null;
  attemptedPaths: string[];
  failures: AttemptFailure[];
}> {
  const envelopePaths = snapshotCandidates();
  const plaintextPaths = snapshotPlaintextCandidates();
  const attemptedPaths = uniquePaths([...plaintextPaths, ...envelopePaths]);
  const failures: AttemptFailure[] = [];
  let envelopeAttempted = false;

  for (const candidate of plaintextPaths) {
    if (!existsSync(candidate)) {
      failures.push({ path: candidate, reason: "Plaintext snapshot file not found." });
      continue;
    }

    try {
      const cacheKey = snapshotCacheKey(candidate);

      if (SNAPSHOT_CACHE && SNAPSHOT_CACHE.cacheKey === cacheKey && SNAPSHOT_CACHE.rows.length > 0) {
        return {
          rows: SNAPSHOT_CACHE.rows,
          sourcePath: SNAPSHOT_CACHE.sourcePath,
          attemptedPaths,
          failures,
        };
      }

      const rows = loadRowsFromPlaintextSnapshot(candidate);
      if (rows.length > 0) {
        SNAPSHOT_CACHE = {
          cacheKey,
          sourcePath: candidate,
          rows,
        };
        return { rows, sourcePath: candidate, attemptedPaths, failures };
      }

      failures.push({ path: candidate, reason: "Plaintext snapshot parsed, but had zero rows." });
    } catch (error) {
      const reason = error instanceof Error ? error.message : "Unknown plaintext snapshot read/parse error";
      failures.push({ path: candidate, reason });
    }
  }

  for (const candidate of envelopePaths) {
    if (!existsSync(candidate)) {
      failures.push({ path: candidate, reason: "Envelope file not found." });
      continue;
    }

    if (envelopeAttempted) {
      failures.push({ path: candidate, reason: "Skipped envelope candidate after primary envelope attempt." });
      continue;
    }

    envelopeAttempted = true;

    try {
      const cacheKey = snapshotCacheKey(candidate);

      if (SNAPSHOT_CACHE && SNAPSHOT_CACHE.cacheKey === cacheKey && SNAPSHOT_CACHE.rows.length > 0) {
        return {
          rows: SNAPSHOT_CACHE.rows,
          sourcePath: SNAPSHOT_CACHE.sourcePath,
          attemptedPaths,
          failures,
        };
      }

      if (SNAPSHOT_CACHE_INFLIGHT && SNAPSHOT_CACHE_INFLIGHT.cacheKey === cacheKey) {
        const inflightRows = await SNAPSHOT_CACHE_INFLIGHT.promise;
        if (inflightRows.length > 0) {
          return { rows: inflightRows, sourcePath: candidate, attemptedPaths, failures };
        }
      }

      const loadPromise = loadRowsFromEnvelope(candidate);
      SNAPSHOT_CACHE_INFLIGHT = { cacheKey, promise: loadPromise };
      const rows = await loadPromise;
      if (SNAPSHOT_CACHE_INFLIGHT?.promise === loadPromise) {
        SNAPSHOT_CACHE_INFLIGHT = null;
      }

      if (rows.length > 0) {
        SNAPSHOT_CACHE = {
          cacheKey,
          sourcePath: candidate,
          rows,
        };
        return { rows, sourcePath: candidate, attemptedPaths, failures };
      }

      failures.push({ path: candidate, reason: "Envelope decrypted, but had zero rows." });
      break;
    } catch (error) {
      SNAPSHOT_CACHE_INFLIGHT = null;
      const reason = error instanceof Error ? error.message : "Unknown envelope decrypt/parse error";
      failures.push({ path: candidate, reason });
      break;
    }
  }

  return { rows: [], sourcePath: null, attemptedPaths, failures };
}

export function primeSnapshotRowsCache(): void {
  if (SNAPSHOT_CACHE || SNAPSHOT_CACHE_INFLIGHT || SNAPSHOT_PRIME_STARTED) {
    return;
  }

  SNAPSHOT_PRIME_STARTED = true;
  void loadSnapshotRows().finally(() => {
    SNAPSHOT_PRIME_STARTED = false;
  });
}

function decisionInfoFromResolvedRow(row: SnapshotRow): DecisionInfo {
  const cached = DECISION_INFO_CACHE.get(row);
  if (cached) return cached;

  const resolved = policyDecisionFromRow(row, PSCF_EXACT_ANCHOR_MODE);
  DECISION_INFO_CACHE.set(row, resolved);
  return resolved;
}

export function decisionInfoFromRowWithExactAnchor(
  row: SnapshotRow | null,
  exactAnchorMode: PscfExactAnchorMode,
): DecisionInfo {
  if (!row) {
    return decisionInfoFromRow(row);
  }

  if (exactAnchorMode === PSCF_EXACT_ANCHOR_MODE) {
    return decisionInfoFromResolvedRow(row);
  }

  return policyDecisionFromRow(row, exactAnchorMode);
}

export function decisionInfoFromRow(row: SnapshotRow | null): DecisionInfo {
  if (!row) {
    return {
      decision: PSCF_FALLBACK_DECISION,
      reasonCode: "ROW_NOT_FOUND",
      reasonText: `No snapshot row found. Fallback to ${PSCF_FALLBACK_DECISION}.`,
      barCount: 0,
      minBarsForAccumulate: ACCUMULATE_MIN_BARS,
      provenance: {
        policySourcePath: PSCF_POLICY_RUNTIME.sourcePath,
        policyGeneratedAtUtc:
          PSCF_POLICY_RUNTIME.policy && typeof PSCF_POLICY_RUNTIME.policy.generated_at_utc === "string"
            ? PSCF_POLICY_RUNTIME.policy.generated_at_utc
            : null,
        policyMatched: false,
        policyCellKeyRequested: null,
        policyCellKeyMatched: null,
        policyScoringMode: null,
        fallbackUsed: true,
        fallbackReason: "row_not_found",
        anomalyFlagged: false,
        structuralComplete: false,
        structuralMissingFields: ["row"],
        l4Vector: {
          regime: "UNKNOWN",
          D_k: null,
          M_k: null,
          M_sign: null,
          R_rev_k: null,
          U_star_k: null,
          C_k: null,
          P_k: null,
          B_k: null,
        },
      },
    };
  }

  return decisionInfoFromResolvedRow(row);
}

export function decisionTextFromRow(row: SnapshotRow | null): DecisionLabel {
  return decisionInfoFromRow(row).decision;
}

export function classificationFromDecision(decision: DecisionLabel): Classification {
  if (decision === "Accumulate") return "BUY";
  if (decision === "Avoid") return "SELL";
  return "HOLD";
}

export function classificationFromRow(row: SnapshotRow | null): Classification {
  const decision = decisionInfoFromRow(row).decision;
  return classificationFromDecision(decision);
}

export function findTickerRow(rows: SnapshotRow[], ticker: string): SnapshotRow | null {
  const target = ticker.trim().toUpperCase();
  if (!target) return null;

  for (const row of rows) {
    if (String(row.ticker ?? "").toUpperCase() === target) {
      return row;
    }
  }

  return null;
}
