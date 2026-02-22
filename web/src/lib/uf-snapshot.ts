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
  | "PSCF_POLICY_CELL"
  | "PSCF_POLICY_CELL_ANOMALOUS"
  | "PSCF_POLICY_FALLBACK_ALL_ANOMALOUS"
  | "PSCF_POLICY_MISSING"
  | "PSCF_CELL_UNMAPPED"
  | "PSCF_CELL_KEY_UNAVAILABLE"
  | "S_UF_BELOW_MIN"
  | "ACCUMULATE_CONFIRMED"
  | "INSUFFICIENT_EVIDENCE_BARS"
  | "D_NEUTRAL"
  | "D_NEGATIVE"
  | "PRODUCTION_OVERRIDE";

export type DecisionInfo = {
  decision: DecisionLabel;
  reasonCode: DecisionReasonCode;
  reasonText: string;
  barCount: number;
  minBarsForAccumulate: number;
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

const SNAPSHOT_ENVELOPE_FILENAME = "uf_snapshot.ses.json";
const SNAPSHOT_ENVELOPE_BACKUP_FILENAME = "uf_snapshot_old_backup.ses.json";
const SNAPSHOT_SES_PURPOSE = "uf-snapshot";
const SNAPSHOT_SES_ACTOR = "web-snapshot-pipeline";
const SNAPSHOT_SES_ASSET = "uf_snapshot:web";
const PSCF_POLICY_FILENAME = "pscf_policy_runtime.json";
const PSCF_POLICY_FALLBACK_FILENAME = "pscf-policy-anomaly-watch-20260218T142043Z.json";
export const ACCUMULATE_MIN_BARS = 514;
const S_UF_MIN = 0.30;
const PRODUCTION_DECISION_OVERRIDE_PATTERN = "reg=TRANSITIONAL|D=-1|P=2|Rrev=1|Bsgn=-1";
const SNAPSHOT_SES_ACTOR_CANDIDATES = actorCandidates();

let SNAPSHOT_CACHE: SnapshotEnvelopeCache | null = null;
let SNAPSHOT_CACHE_INFLIGHT: { cacheKey: string; promise: Promise<SnapshotRow[]> } | null = null;
let SNAPSHOT_PRIME_STARTED = false;

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

function sign3(value: number): number {
  if (value > 0) return 1;
  if (value < 0) return -1;
  return 0;
}

function decisionVectorValue(row: SnapshotRow, index: number): number {
  const dv = row.decision_vector;
  if (!Array.isArray(dv)) return 0;
  return toNumber(dv[index]);
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

function basePscfCellKeyFromRow(row: SnapshotRow): string | null {
  if (!Array.isArray(row.decision_vector)) {
    return null;
  }

  const regime = String(row.regime ?? "UNKNOWN");
  const dVal = Math.round(decisionVectorValue(row, 0));
  const mSign = sign3(decisionVectorValue(row, 1));
  const rRev = decisionVectorValue(row, 2) > 0.5 ? 1 : 0;
  const uPart = uBucket(decisionVectorValue(row, 3));
  const pPart = pBucket(decisionVectorValue(row, 4));
  const bSign = sign3(decisionVectorValue(row, 5));

  return `reg=${regime}|D=${dVal}|M=${mSign}|Rrev=${rRev}|${uPart}|${pPart}|B=${bSign}`;
}

function pscfCellKeyCandidatesFromRow(row: SnapshotRow): string[] {
  const base = basePscfCellKeyFromRow(row);
  if (!base) return [];

  const sUf = toNumber(row.S_UF);
  const rUf = toNumber(row.R_UF);
  const cd = sUf - rUf;
  const mSign = sign3(decisionVectorValue(row, 1));
  const phaseTag = `|PH=${irfPhase(mSign, rUf)}`;
  const stabilityScore = toNumber(row.stability_score);
  const st = bucketStability(stabilityScore);

  const enrichedCdSt = `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|CD=${bucketCdOpt(cd)}|ST=${st}`;
  const enrichedSrSt = `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|ST=${st}`;
  const enrichedCd = `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}|CD=${bucketCdOpt(cd)}`;
  const enrichedSr = `${base}|S=${bucket3(sUf)}|R=${bucket3(rUf)}`;

  const keys = [
    `${enrichedCdSt}${phaseTag}`,
    `${enrichedSrSt}${phaseTag}`,
    `${enrichedCd}${phaseTag}`,
    `${enrichedSr}${phaseTag}`,
    enrichedCdSt,
    enrichedSrSt,
    enrichedCd,
    enrichedSr,
    base,
  ];

  const deduped: string[] = [];
  const seen = new Set<string>();
  for (const key of keys) {
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(key);
  }

  return deduped;
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
  const guardGateUnlock = guard ? Boolean(guard.gate_unlock_transient_neutralized) : false;

  const hardening = asRecord(row.hardening);
  const hardeningFlags = hardening ? asRecord(hardening.flags) : null;
  const hardeningHysteresisOverload = hardeningFlags ? Boolean(hardeningFlags.hysteresis_overload) : false;

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

function productionPatternKeyFromRow(row: SnapshotRow): string {
  const regime = String(row.regime ?? "UNKNOWN");
  const dVal = Math.round(decisionVectorValue(row, 0));
  const pVal = Math.round(decisionVectorValue(row, 4));
  const rRev = Math.round(decisionVectorValue(row, 2));
  const bSign = sign3(decisionVectorValue(row, 5));
  return `reg=${regime}|D=${dVal}|P=${pVal}|Rrev=${rRev}|Bsgn=${bSign}`;
}

function productionDecisionFromRow(
  row: SnapshotRow,
  barCount: number,
): Pick<DecisionInfo, "decision" | "reasonCode" | "reasonText"> {
  const sUf = toNumber(row.S_UF);
  const dVal = decisionVectorValue(row, 0);

  let decision: DecisionLabel;
  let reasonCode: DecisionReasonCode;
  let reasonText: string;

  if (sUf < S_UF_MIN) {
    decision = "Avoid";
    reasonCode = "S_UF_BELOW_MIN";
    reasonText = `S_UF=${sUf.toFixed(6)} is below production floor ${S_UF_MIN.toFixed(2)}.`;
  } else if (barCount < ACCUMULATE_MIN_BARS) {
    decision = "Hold";
    reasonCode = "INSUFFICIENT_EVIDENCE_BARS";
    reasonText = `bar_count=${barCount} is below minimum ${ACCUMULATE_MIN_BARS} for Accumulate.`;
  } else if (dVal > 0) {
    decision = "Accumulate";
    reasonCode = "ACCUMULATE_CONFIRMED";
    reasonText = `D=${dVal.toFixed(6)} > 0 with production gates satisfied (S_UF and bar_count).`;
  } else if (dVal === 0) {
    decision = "Hold";
    reasonCode = "D_NEUTRAL";
    reasonText = `D=${dVal.toFixed(6)} is neutral.`;
  } else {
    decision = "Avoid";
    reasonCode = "D_NEGATIVE";
    reasonText = `D=${dVal.toFixed(6)} < 0.`;
  }

  const patternKey = productionPatternKeyFromRow(row);
  if (decision === "Avoid" && patternKey === PRODUCTION_DECISION_OVERRIDE_PATTERN) {
    return {
      decision: "Hold",
      reasonCode: "PRODUCTION_OVERRIDE",
      reasonText: `Production override pattern matched (${PRODUCTION_DECISION_OVERRIDE_PATTERN}).`,
    };
  }

  return { decision, reasonCode, reasonText };
}

function pscfDiagnosticTextFromRow(row: SnapshotRow): string {
  const cellKeyCandidates = pscfCellKeyCandidatesFromRow(row);
  const firstCandidate = cellKeyCandidates[0] ?? "n/a";

  if (cellKeyCandidates.length === 0) {
    return "PSCF diagnostic: cell key unavailable.";
  }

  if (!PSCF_POLICY_RUNTIME.policy || !PSCF_POLICY_RUNTIME.policy.cells) {
    return `PSCF diagnostic: policy missing (attempted_paths=${PSCF_POLICY_RUNTIME.attemptedPaths.length}).`;
  }

  let selectedKey: string | null = null;
  let cell: PscfPolicyCell | undefined;
  for (const candidate of cellKeyCandidates) {
    const found = PSCF_POLICY_RUNTIME.policy.cells[candidate];
    if (found) {
      selectedKey = candidate;
      cell = found;
      break;
    }
  }

  if (!cell) {
    return `PSCF diagnostic: cell unmapped (first_candidate=${firstCandidate}).`;
  }

  const decision = policyDecisionLabel(cell.decision);
  const anomaly = anomalyFlagsFromRow(row);
  const scoringMode = String(cell.scoring_mode ?? "unknown");
  const sourcePath = PSCF_POLICY_RUNTIME.sourcePath ? path.basename(PSCF_POLICY_RUNTIME.sourcePath) : "unknown";

  if (anomaly.anomalyAny) {
    return `PSCF diagnostic: mapped cell=${selectedKey ?? firstCandidate}, decision=${decision}, scoring_mode=${scoringMode}, anomaly_flagged=true, source=${sourcePath}.`;
  }

  return `PSCF diagnostic: mapped cell=${selectedKey ?? firstCandidate}, decision=${decision}, scoring_mode=${scoringMode}, source=${sourcePath}.`;
}

export async function loadSnapshotRows(): Promise<{
  rows: SnapshotRow[];
  sourcePath: string | null;
  attemptedPaths: string[];
  failures: AttemptFailure[];
}> {
  const attemptedPaths = snapshotCandidates();
  const failures: AttemptFailure[] = [];

  for (const candidate of attemptedPaths) {
    if (!existsSync(candidate)) {
      failures.push({ path: candidate, reason: "Envelope file not found." });
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
    } catch (error) {
      SNAPSHOT_CACHE_INFLIGHT = null;
      const reason = error instanceof Error ? error.message : "Unknown envelope decrypt/parse error";
      failures.push({ path: candidate, reason });
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
  const barCount = Math.max(0, Math.floor(toNumber(row.bar_count)));
  const productionDecision = productionDecisionFromRow(row, barCount);
  const pscfDiagnostic = pscfDiagnosticTextFromRow(row);

  return {
    decision: productionDecision.decision,
    reasonCode: productionDecision.reasonCode,
    reasonText: `${productionDecision.reasonText} ${pscfDiagnostic}`,
    barCount,
    minBarsForAccumulate: ACCUMULATE_MIN_BARS,
  };
}

export function decisionInfoFromRow(row: SnapshotRow | null): DecisionInfo {
  if (!row) {
    return {
      decision: "Hold",
      reasonCode: "ROW_NOT_FOUND",
      reasonText: "No snapshot row found. Defaulting to Hold.",
      barCount: 0,
      minBarsForAccumulate: ACCUMULATE_MIN_BARS,
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
