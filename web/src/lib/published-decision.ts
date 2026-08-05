import { ACCUMULATE_MIN_BARS, classificationFromDecision, type Classification, type SnapshotRow } from "@/lib/uf-snapshot";
import {
  loadRuntimeDecisionProvenanceByRunIdFromPostgres,
  type RuntimeDecisionPersistedProvenance,
} from "@/lib/runtime-postgres";

export type PublishedDecisionLabel = "Accumulate" | "Hold" | "Avoid";

export type PublishedDecisionRecord = {
  ticker: string;
  decision: PublishedDecisionLabel;
  decisionReasonCode: string;
  decisionReason: string;
  classification: Classification;
  barCount: number;
  minBarsForAccumulate: number;
  fallbackUsed: boolean;
  fallbackReason: string | null;
  policyCellKeyRequested: string | null;
  policyCellKeyMatched: string | null;
  policySourcePath: string | null;
  policyGeneratedAtUtc: string | null;
  policyScoringMode: string | null;
  anomalyFlagged: boolean;
  structuralComplete: boolean;
  structuralMissingFields: string[];
  persistedProvenanceAvailable: boolean;
  persistedProvenanceValid: boolean;
};

export type PublishedDecisionLoadResult = {
  ok: boolean;
  rows: Record<string, PublishedDecisionRecord>;
  sourcePath: string | null;
  failures: Array<{ path: string; reason: string }>;
  missingTickers: string[];
  invalidTickers: string[];
  blockingReasonCode: string | null;
  blockingReasonDetail: string | null;
  rowsRequired: number;
  rowsValid: number;
};

function normalizeTicker(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
}

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function persistedDecisionLabel(value: unknown): PublishedDecisionLabel | null {
  const raw = String(value ?? "").trim().toLowerCase();
  if (raw === "accumulate") return "Accumulate";
  if (raw === "hold") return "Hold";
  if (raw === "avoid") return "Avoid";
  return null;
}

export function persistedProvenanceUsable(value: RuntimeDecisionPersistedProvenance | undefined): boolean {
  if (!value) return false;
  if (!value.provenanceValid) return false;
  if (!value.matchLevel) return false;
  if (!value.policyArtifactHashSha256) return false;
  if (!value.decisionReasonCode) return false;
  if (!persistedDecisionLabel(value.decision)) return false;
  return true;
}

function decisionReasonText(reasonCode: string, decision: PublishedDecisionLabel, matchedKey: string | null): string {
  if (reasonCode === "GEMINI_STEP_1_VIABILITY") {
    return "GEMINI Step 1: S_UF <= 0, so the ticker is Avoid.";
  }
  if (reasonCode === "GEMINI_STEP_2_KILL_SWITCH") {
    return "GEMINI Step 2: R_rev_k > 0, so the kill switch forces Avoid.";
  }
  if (reasonCode === "GEMINI_STEP_3_ACCUMULATE") {
    return "GEMINI Step 3: positive drive, positive R_UF, decelerating C_k, and P_k below B_k triggered Accumulate.";
  }
  if (reasonCode === "GEMINI_STEP_4_HOLD") {
    return "GEMINI Step 4: the ticker stayed inside the Hold orbit gate.";
  }
  if (reasonCode === "GEMINI_STEP_5_DEFAULT_AVOID") {
    return "GEMINI Step 5: no prior gate fired, so the default is Avoid.";
  }
  if (reasonCode === "GEMINI_MISSING_REQUIRED_FIELDS") {
    return "GEMINI input set is incomplete, so the ticker defaults to Avoid.";
  }
  if (reasonCode === "PSCF_POLICY_DECISION") {
    return `PSCF/L5 policy decision ${decision} from matched cell ${matchedKey ?? "unknown"}.`;
  }
  if (reasonCode === "PSCF_FALLBACK_INSUFFICIENT_BARS") {
    return `Fallback to Hold: insufficient bar history for Accumulate threshold (${ACCUMULATE_MIN_BARS}).`;
  }
  if (reasonCode === "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE") {
    return "Fallback to Hold: missing required L4 fields.";
  }
  if (reasonCode === "PSCF_FALLBACK_POLICY_MISSING") {
    return "Fallback to Hold: PSCF/L5 policy runtime is unavailable.";
  }
  if (reasonCode === "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE") {
    return "Fallback to Hold: no policy cell key could be formed from row data.";
  }
  if (reasonCode === "PSCF_FALLBACK_CELL_UNMAPPED") {
    return "Fallback to Hold: no mapped PSCF/L5 cell exists for the requested key.";
  }
  if (reasonCode === "PSCF_FALLBACK_ANOMALOUS") {
    return "Fallback to Hold: anomaly flags were active for the mapped cell.";
  }
  if (reasonCode === "ROW_NOT_FOUND") {
    return "No snapshot row found. Fallback to Hold.";
  }
  return `Persisted published decision ${decision} loaded with reason code '${reasonCode}'.`;
}

function toPublishedDecisionRecord(
  row: SnapshotRow,
  persisted: RuntimeDecisionPersistedProvenance | undefined,
): PublishedDecisionRecord | null {
  const ticker = normalizeTicker(row.ticker);
  if (!ticker) return null;

  const decision = persistedDecisionLabel(persisted?.decision);
  const persistedAvailable = Boolean(persisted);
  const persistedValid = persistedProvenanceUsable(persisted);

  if (!decision || !persistedValid || !persisted) {
    return null;
  }

  const barCount = Math.max(0, Math.floor(toNumber(row.bar_count)));
  const reasonCode = String(persisted.decisionReasonCode ?? "").trim() || "PSCF_FALLBACK_POLICY_MISSING";

  return {
    ticker,
    decision,
    decisionReasonCode: reasonCode,
    decisionReason: decisionReasonText(reasonCode, decision, persisted.matchedKey),
    classification: classificationFromDecision(decision),
    barCount,
    minBarsForAccumulate: ACCUMULATE_MIN_BARS,
    fallbackUsed: Boolean(persisted.fallbackUsed),
    fallbackReason: persisted.fallbackReasonCode ?? null,
    policyCellKeyRequested: persisted.candidateKeyChain[0] ?? null,
    policyCellKeyMatched: persisted.matchedKey ?? null,
    policySourcePath: persisted.policyArtifactId ?? null,
    policyGeneratedAtUtc: persisted.provenanceGeneratedUtc ?? null,
    policyScoringMode: persisted.policySourceMode ?? null,
    anomalyFlagged: Boolean(persisted.anomalyFlagsUsed?.anomaly_any === true),
    structuralComplete: reasonCode === "PSCF_POLICY_DECISION",
    structuralMissingFields: [],
    persistedProvenanceAvailable: persistedAvailable,
    persistedProvenanceValid: persistedValid,
  };
}

export async function loadPublishedDecisionMapForRows(
  runId: string | null,
  rows: SnapshotRow[],
  requiredTickers?: string[],
): Promise<PublishedDecisionLoadResult> {
  const normalizedRunId = String(runId ?? "").trim();
  const required = Array.from(
    new Set(
      (requiredTickers ?? rows.map((row) => normalizeTicker(row.ticker)))
        .map((ticker) => normalizeTicker(ticker))
        .filter(Boolean),
    ),
  );

  if (!normalizedRunId) {
    return {
      ok: false,
      rows: {},
      sourcePath: null,
      failures: [],
      missingTickers: required,
      invalidTickers: [],
      blockingReasonCode: "PERSISTED_PROVENANCE_RUN_ID_MISSING",
      blockingReasonDetail: "Published run_id is missing; persisted decision provenance cannot be loaded.",
      rowsRequired: required.length,
      rowsValid: 0,
    };
  }

  const persisted = await loadRuntimeDecisionProvenanceByRunIdFromPostgres(normalizedRunId);
  const rowByTicker = new Map<string, SnapshotRow>();
  for (const row of rows) {
    const ticker = normalizeTicker(row.ticker);
    if (!ticker || rowByTicker.has(ticker)) continue;
    rowByTicker.set(ticker, row);
  }

  const out: Record<string, PublishedDecisionRecord> = {};
  const missingTickers: string[] = [];
  const invalidTickers: string[] = [];

  for (const ticker of required) {
    const row = rowByTicker.get(ticker);
    const record = row ? toPublishedDecisionRecord(row, persisted.rows[ticker]) : null;
    if (record) {
      out[ticker] = record;
      continue;
    }

    if (!persisted.rows[ticker]) {
      missingTickers.push(ticker);
    } else {
      invalidTickers.push(ticker);
    }
  }

  const failures = [...persisted.failures];
  let blockingReasonCode: string | null = null;
  let blockingReasonDetail: string | null = null;

  if (missingTickers.length > 0 || invalidTickers.length > 0) {
    blockingReasonCode = "PERSISTED_PROVENANCE_MISSING_OR_INVALID";
    blockingReasonDetail = [
      missingTickers.length > 0 ? `missing=${missingTickers.slice(0, 12).join(",")}` : null,
      invalidTickers.length > 0 ? `invalid=${invalidTickers.slice(0, 12).join(",")}` : null,
    ]
      .filter(Boolean)
      .join(" ; ");
  } else if (failures.length > 0 && Object.keys(out).length === 0) {
    blockingReasonCode = "PERSISTED_PROVENANCE_LOAD_FAILED";
    blockingReasonDetail = failures.map((failure) => failure.reason).join(" | ");
  }

  return {
    ok: blockingReasonCode === null,
    rows: out,
    sourcePath: persisted.sourcePath,
    failures,
    missingTickers,
    invalidTickers,
    blockingReasonCode,
    blockingReasonDetail,
    rowsRequired: required.length,
    rowsValid: Object.keys(out).length,
  };
}
