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
  | "TUPLE_PROXIMITY_DECISION"
  | "TUPLE_PROXIMITY_DECISION_LABEL_MISSING"
  // Legacy codes — still referenced by published-decision.ts for provenance records
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

const SNAPSHOT_ENVELOPE_FILENAME = "uf_snapshot.ses.json";
const SNAPSHOT_ENVELOPE_BACKUP_FILENAME = "uf_snapshot_old_backup.ses.json";
const SNAPSHOT_PLAINTEXT_FILENAME = "uf_snapshot.json";
const SNAPSHOT_SES_PURPOSE = "uf-snapshot";
const SNAPSHOT_SES_ACTOR = "web-snapshot-pipeline";
const SNAPSHOT_SES_ASSET = "uf_snapshot:web";
// PscfExactAnchorMode kept as export — used by decisionInfoFromRowWithExactAnchor signature
export type PscfExactAnchorMode =
  | "CURRENT_ST_ANCHORED_EXACT_FAMILY"
  | "NO_ST_EXACT_FAMILY_KEEP_CD_PHASE_SPIDER_STRICT";
function normalizeMinBars(value: unknown, fallback: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  const whole = Math.floor(n);
  if (whole < 20) return 20;
  if (whole > 2520) return 2520;
  return whole;
}

export const ACCUMULATE_MIN_BARS = normalizeMinBars(process.env.TFE_RECOMMENDATIONS_MIN_BARS, 180);
// V3 basin fallback REMOVED. Decision source is runtime_decisions_latest.decision_label
// (tuple-proximity engine). If decision_label is missing, default to Hold.
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

// ── V3 basin scaffold DELETED ───────────────────────────────────────────
// ~450 lines removed: resolveStructuralBasis, bucket functions, cell key
// generation, policyDecisionFromRow, fallbackDecisionInfo, anomalyFlagsFromRow,
// and all PSCF cell lookup logic. Decision source is now
// runtime_decisions_latest.decision_label (tuple-proximity engine).
// See commit 048ab3c for the V3 formula removal.
// ────────────────────────────────────────────────────────────────────────

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

/**
 * Read decision directly from runtime_decisions_latest.decision_label.
 * No V3 basin. No PSCF policy cells. The tuple-proximity engine writes the
 * decision_label column; this function reads it. If the column is missing or
 * empty, return null decision — don't fabricate "Hold."
 */
function parseDecisionLabel(raw: unknown): DecisionLabel | null {
  const s = String(raw ?? "").trim();
  if (s === "Accumulate") return "Accumulate";
  if (s === "Hold") return "Hold";
  if (s === "Avoid") return "Avoid";
  return null;
}

const EMPTY_PROVENANCE: DecisionProvenance = {
  policySourcePath: null,
  policyGeneratedAtUtc: null,
  policyMatched: false,
  policyCellKeyRequested: null,
  policyCellKeyMatched: null,
  policyScoringMode: null,
  fallbackUsed: false,
  fallbackReason: null,
  anomalyFlagged: false,
  structuralComplete: true,
  structuralMissingFields: [],
  l4Vector: { regime: "UNKNOWN", D_k: null, M_k: null, M_sign: null, R_rev_k: null, U_star_k: null, C_k: null, P_k: null, B_k: null },
};

export function decisionInfoFromRowWithExactAnchor(
  row: SnapshotRow | null,
  _exactAnchorMode: PscfExactAnchorMode,
): DecisionInfo {
  return decisionInfoFromRow(row);
}

export function decisionInfoFromRow(row: SnapshotRow | null): DecisionInfo {
  if (!row) {
    return {
      decision: "Hold",
      reasonCode: "ROW_NOT_FOUND",
      reasonText: "No snapshot row found.",
      barCount: 0,
      minBarsForAccumulate: ACCUMULATE_MIN_BARS,
      provenance: EMPTY_PROVENANCE,
    };
  }

  const cached = DECISION_INFO_CACHE.get(row);
  if (cached) return cached;

  const label = parseDecisionLabel(row.decision_label);
  const barCount = Math.max(0, Math.floor(toNumber(row.bar_count)));

  const info: DecisionInfo = label
    ? {
        decision: label,
        reasonCode: "TUPLE_PROXIMITY_DECISION",
        reasonText: `Tuple-proximity decision: ${label}.`,
        barCount,
        minBarsForAccumulate: ACCUMULATE_MIN_BARS,
        provenance: EMPTY_PROVENANCE,
      }
    : {
        decision: "Hold",
        reasonCode: "TUPLE_PROXIMITY_DECISION_LABEL_MISSING",
        reasonText: "decision_label not present on row; defaulting to Hold.",
        barCount,
        minBarsForAccumulate: ACCUMULATE_MIN_BARS,
        provenance: EMPTY_PROVENANCE,
      };

  DECISION_INFO_CACHE.set(row, info);
  return info;
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
