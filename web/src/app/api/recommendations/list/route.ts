import { NextResponse } from "next/server";

import {
  classificationFromDecision,
  type SnapshotRow,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { loadCanonicalPublicationState, publicationContractFields } from "@/lib/publication-state";
import { loadPublishedDecisionMapForRows, type PublishedDecisionRecord } from "@/lib/published-decision";
import {
  quoteCachePriceFromRow,
  type ScreenerQuoteCacheRow,
} from "@/lib/screener-quote-cache";
import {
  loadRuntimeQuoteCacheFromPostgres,
  loadRuntimeSnapshotRowsFromPostgres,
} from "@/lib/runtime-postgres";

export const runtime = "nodejs";

type RecommendationRow = {
  ticker: string;
  assetType: "equities" | "index" | "crypto" | "etf" | "other";
  price: number | null;
  decision: "Accumulate" | "Hold" | "Avoid";
  decisionReason: string;
  decisionReasonCode: string;
  confidence: number;
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
  classification: "BUY" | "HOLD" | "SELL";
  regime: string;
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
  provenanceSource: "persisted";
  persistedProvenanceAvailable: boolean;
  persistedProvenanceValid: boolean;
  assessmentStatus: "ASSESSED" | "NOT_ASSESSED";
  assessmentLabel: string;
};

type RecommendationHealth = {
  totalRows: number;
  assessedRows: number;
  notAssessedRows: number;
  assessedRate: number;
  notAssessedRate: number;
  accuracyScoringScope: "ASSESSED_ONLY";
  policyMappedRows: number;
  fallbackRows: number;
  insufficientBarsRows: number;
  structuralIncompleteRows: number;
  unmappedRows: number;
  policyMissingRows: number;
  anomalousRows: number;
  coverageRate: number;
  fallbackRate: number;
  thresholds: { minCoverage: number; maxFallback: number };
  alerts: string[];
};

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function normalizeAssetType(value: unknown): RecommendationRow["assetType"] {
  const raw = String(value ?? "").trim().toLowerCase();

  if (["equity", "equities", "stock", "stocks"].includes(raw)) return "equities";
  if (["index", "indices"].includes(raw)) return "index";
  if (["crypto", "cryptocurrency", "coin", "token"].includes(raw)) return "crypto";
  if (["etf", "fund"].includes(raw)) return "etf";

  return "other";
}

type RecommendationTransformResult = {
  row: RecommendationRow | null;
  provenanceUsedPersisted: boolean;
  persistedAvailable: boolean;
  persistedValid: boolean;
};

function toRecommendationRow(
  row: SnapshotRow,
  quoteCacheQuotes: Record<string, ScreenerQuoteCacheRow>,
  publishedDecisionMap: Record<string, PublishedDecisionRecord>,
): RecommendationTransformResult {
  const ticker = String(row.ticker ?? "").trim().toUpperCase();
  if (!ticker) {
    return {
      row: null,
      provenanceUsedPersisted: false,
      persistedAvailable: false,
      persistedValid: false,
    };
  }

  const sUf = toNumber(row.S_UF);
  const rUf = toNumber(row.R_UF);
  const snapshotPrice = toNumberOrNull(row.price);
  const quoteCachePrice = quoteCachePriceFromRow(quoteCacheQuotes[ticker]);
  const published = publishedDecisionMap[ticker];
  if (!published) {
    return {
      row: null,
      provenanceUsedPersisted: false,
      persistedAvailable: false,
      persistedValid: false,
    };
  }

  const assessed = published.decisionReasonCode === "PSCF_POLICY_DECISION";
  const assessmentStatus: RecommendationRow["assessmentStatus"] = assessed ? "ASSESSED" : "NOT_ASSESSED";
  const assessmentLabel = assessed
    ? "Assessed"
    : published.decisionReasonCode === "PSCF_FALLBACK_INSUFFICIENT_BARS"
      ? "Not Assessed (Insufficient Data)"
      : "Not Assessed (Fallback Hold)";

  return {
    row: {
      ticker,
      assetType: normalizeAssetType(row.asset_type),
      price: quoteCachePrice ?? snapshotPrice,
      decision: published.decision,
      decisionReason: published.decisionReason,
      decisionReasonCode: published.decisionReasonCode,
      confidence: (sUf + rUf) / 2,
      S_UF: sUf,
      R_UF: rUf,
      barCount: published.barCount,
      minBarsForAccumulate: published.minBarsForAccumulate,
      classification: classificationFromDecision(published.decision),
      regime: String(row.regime ?? "UNKNOWN"),
      fallbackUsed: published.fallbackUsed,
      fallbackReason: published.fallbackReason,
      policyCellKeyRequested: published.policyCellKeyRequested,
      policyCellKeyMatched: published.policyCellKeyMatched,
      policySourcePath: published.policySourcePath,
      policyGeneratedAtUtc: published.policyGeneratedAtUtc,
      policyScoringMode: published.policyScoringMode,
      anomalyFlagged: published.anomalyFlagged,
      structuralComplete: published.structuralComplete,
      structuralMissingFields: published.structuralMissingFields,
      provenanceSource: "persisted",
      persistedProvenanceAvailable: true,
      persistedProvenanceValid: true,
      assessmentStatus,
      assessmentLabel,
    },
    provenanceUsedPersisted: true,
    persistedAvailable: true,
    persistedValid: true,
  };
}

function sortByConfidence(rows: RecommendationRow[]): RecommendationRow[] {
  return [...rows].sort((a, b) => {
    if (b.confidence !== a.confidence) return b.confidence - a.confidence;

    const aPrice = a.price ?? Number.POSITIVE_INFINITY;
    const bPrice = b.price ?? Number.POSITIVE_INFINITY;
    if (aPrice !== bPrice) return aPrice - bPrice;

    return a.ticker.localeCompare(b.ticker);
  });
}

function sortByTicker(rows: RecommendationRow[]): RecommendationRow[] {
  return [...rows].sort((a, b) => a.ticker.localeCompare(b.ticker));
}

function isProcessedUfRow(row: RecommendationRow): boolean {
  return row.regime !== "NO_DATA" && row.regime !== "DEGENERATE" && row.regime !== "INSUFFICIENT_DATA";
}

function normalizeTimeoutMs(value: unknown, fallbackMs: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallbackMs;

  const whole = Math.floor(n);
  if (whole < 1000) return 1000;
  if (whole > 45000) return 45000;
  return whole;
}

function normalizeRate(value: unknown, fallback: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

function buildDecisionSummary(rows: RecommendationRow[]): {
  accumulate: number;
  hold: number;
  avoid: number;
} {
  let accumulate = 0;
  let hold = 0;
  let avoid = 0;

  for (const row of rows) {
    if (row.decision === "Accumulate") {
      accumulate += 1;
    } else if (row.decision === "Avoid") {
      avoid += 1;
    } else {
      hold += 1;
    }
  }

  return { accumulate, hold, avoid };
}

function buildRecommendationHealth(
  rows: RecommendationRow[],
  coverageMin: number,
  fallbackMax: number,
): RecommendationHealth {
  const total = rows.length;
  let policyMappedRows = 0;
  let fallbackRows = 0;
  let insufficientBarsRows = 0;
  let structuralIncompleteRows = 0;
  let unmappedRows = 0;
  let policyMissingRows = 0;
  let anomalousRows = 0;

  for (const row of rows) {
    if (row.decisionReasonCode === "PSCF_POLICY_DECISION") {
      policyMappedRows += 1;
    }

    if (row.fallbackUsed) {
      fallbackRows += 1;
    }

    if (row.decisionReasonCode === "PSCF_FALLBACK_INSUFFICIENT_BARS") {
      insufficientBarsRows += 1;
    }

    if (row.decisionReasonCode === "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE") {
      structuralIncompleteRows += 1;
    }

    if (row.decisionReasonCode === "PSCF_FALLBACK_CELL_UNMAPPED") {
      unmappedRows += 1;
    }

    if (row.decisionReasonCode === "PSCF_FALLBACK_POLICY_MISSING") {
      policyMissingRows += 1;
    }

    if (row.decisionReasonCode === "PSCF_FALLBACK_ANOMALOUS") {
      anomalousRows += 1;
    }
  }

  const assessedRows = policyMappedRows;
  const notAssessedRows = fallbackRows;
  const assessedRate = total > 0 ? assessedRows / total : 0;
  const notAssessedRate = total > 0 ? notAssessedRows / total : 0;
  const coverageRate = assessedRate;
  const fallbackRate = notAssessedRate;
  const alerts: string[] = [];

  if (coverageRate < coverageMin) {
    alerts.push(`coverage_below_min:${coverageRate.toFixed(4)}<${coverageMin.toFixed(4)}`);
  }

  if (fallbackRate > fallbackMax) {
    alerts.push(`fallback_above_max:${fallbackRate.toFixed(4)}>${fallbackMax.toFixed(4)}`);
  }

  return {
    totalRows: total,
    assessedRows,
    notAssessedRows,
    assessedRate,
    notAssessedRate,
    accuracyScoringScope: "ASSESSED_ONLY",
    policyMappedRows,
    fallbackRows,
    insufficientBarsRows,
    structuralIncompleteRows,
    unmappedRows,
    policyMissingRows,
    anomalousRows,
    coverageRate,
    fallbackRate,
    thresholds: {
      minCoverage: coverageMin,
      maxFallback: fallbackMax,
    },
    alerts,
  };
}

const SNAPSHOT_LOAD_TIMEOUT_MS = normalizeTimeoutMs(process.env.TFE_RECOMMENDATIONS_SNAPSHOT_TIMEOUT_MS, 20000);
const POLICY_COVERAGE_MIN = normalizeRate(process.env.TFE_RECOMMENDATIONS_POLICY_COVERAGE_MIN, 0.828);
const POLICY_FALLBACK_MAX = normalizeRate(process.env.TFE_RECOMMENDATIONS_POLICY_FALLBACK_MAX, 0.172);

async function loadSnapshotRowsWithTimeout(): Promise<Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>> {
  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  try {
    return await Promise.race([
      loadRuntimeSnapshotRowsFromPostgres(),
      new Promise<Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>>((_, reject) => {
        timeoutHandle = setTimeout(() => {
          reject(new Error(`UF snapshot load timed out after ${SNAPSHOT_LOAD_TIMEOUT_MS}ms.`));
        }, SNAPSHOT_LOAD_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timeoutHandle) {
      clearTimeout(timeoutHandle);
    }
  }
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  let snapshot: Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>;

  try {
    snapshot = await loadSnapshotRowsWithTimeout();
  } catch (error) {
    const details = error instanceof Error ? error.message : "Unknown snapshot load error.";
    const timedOut = details.toLowerCase().includes("timed out");
    const publicationState = await loadCanonicalPublicationState({
      snapshot: { available: false, runId: null, generatedAtUtc: null },
      quote: { available: false, runId: null },
    });

    console.error("[recommendations/list] snapshot load failed", {
      timedOut,
      timeoutMs: SNAPSHOT_LOAD_TIMEOUT_MS,
      details,
    });

    return NextResponse.json(
      {
        error: "Recommendations unavailable because runtime Postgres snapshot load failed.",
        degradedReason: timedOut ? "snapshot_load_timeout" : "snapshot_load_failed",
        details,
        timeoutMs: SNAPSHOT_LOAD_TIMEOUT_MS,
        ...publicationContractFields(publicationState),
      },
      { status: 503 },
    );
  }

  if (!snapshot.sourcePath || snapshot.rows.length === 0) {
    const publicationState = await loadCanonicalPublicationState({
      snapshot: {
        available: false,
        runId: snapshot.runId,
        generatedAtUtc: snapshot.generatedAtUtc,
      },
      quote: { available: false, runId: null },
    });
    return NextResponse.json(
      {
        error: "Recommendations unavailable because runtime Postgres snapshot is unavailable or empty.",
        degradedReason: "snapshot_unavailable_or_empty",
        attemptedPaths: snapshot.attemptedPaths,
        failures: snapshot.failures,
        ...publicationContractFields(publicationState),
      },
      { status: 503 },
    );
  }

  const quoteCache = await loadRuntimeQuoteCacheFromPostgres();
  const publicationState = await loadCanonicalPublicationState({
    snapshot: {
      available: true,
      runId: snapshot.runId,
      generatedAtUtc: snapshot.generatedAtUtc,
    },
    quote: {
      available: Boolean(quoteCache.sourcePath && Object.keys(quoteCache.quotes).length > 0),
      runId: quoteCache.runId,
    },
  });
  const publicationFields = publicationContractFields(publicationState);

  if (!quoteCache.sourcePath || Object.keys(quoteCache.quotes).length === 0) {
    return NextResponse.json(
      {
        error: "Recommendations unavailable because runtime Postgres quote cache is unavailable or empty.",
        failures: quoteCache.failures,
        ...publicationFields,
      },
      { status: 503 },
    );
  }

  if (publicationState.servingState === "blocked") {
    return NextResponse.json(
      {
        error: "Recommendations are unavailable. Canonical publication state blocked this response.",
        blocked: true,
        status: "blocked",
        ...publicationFields,
        snapshot_generated_at_utc: snapshot.generatedAtUtc,
        freshness: publicationState.freshness,
        sourceRuns: {
          publication_run_id: publicationState.runId,
          snapshot_run_id: snapshot.runId,
          quote_run_id: quoteCache.runId,
          active_runtime_run_id: publicationState.activeRuntimeRunId,
        },
        publicationState: {
          sourcePath: publicationState.sourcePath,
          failureCount: publicationState.failures.length,
          latest_run_id: publicationState.latestRunId,
        },
      },
      { status: 503 },
    );
  }

  const publishedDecisionLoad = await loadPublishedDecisionMapForRows(publicationState.runId, snapshot.rows);
  if (!publishedDecisionLoad.ok) {
    return NextResponse.json(
      {
        error: "Recommendations are unavailable because persisted published decision provenance is missing or invalid.",
        blocked: true,
        status: "blocked",
        ...publicationFields,
        blocking_reason_code: publishedDecisionLoad.blockingReasonCode ?? publicationFields.blocking_reason_code,
        blocking_reason_detail: publishedDecisionLoad.blockingReasonDetail ?? publicationFields.blocking_reason_detail,
        provenance: {
          sourcePath: publishedDecisionLoad.sourcePath,
          failureCount: publishedDecisionLoad.failures.length,
          rows_required: publishedDecisionLoad.rowsRequired,
          rows_valid: publishedDecisionLoad.rowsValid,
          missingTickers: publishedDecisionLoad.missingTickers,
          invalidTickers: publishedDecisionLoad.invalidTickers,
        },
      },
      { status: 503 },
    );
  }

  const allRows: RecommendationRow[] = [];
  let persistedRowsUsed = 0;
  let persistedRowsAvailable = 0;
  let persistedRowsValid = 0;
  for (const row of snapshot.rows) {
    const transformed = toRecommendationRow(row, quoteCache.quotes, publishedDecisionLoad.rows);
    if (transformed.persistedAvailable) persistedRowsAvailable += 1;
    if (transformed.persistedValid) persistedRowsValid += 1;
    if (transformed.provenanceUsedPersisted) persistedRowsUsed += 1;
    if (transformed.row) allRows.push(transformed.row);
  }

  const processedUniverse = allRows.filter(isProcessedUfRow);
  const decisionSummary = buildDecisionSummary(processedUniverse);
  const recommendationHealth = buildRecommendationHealth(processedUniverse, POLICY_COVERAGE_MIN, POLICY_FALLBACK_MAX);

  const degradedReasons: string[] = [];
  const warnings: string[] = [];

  if (recommendationHealth.alerts.length > 0) {
    degradedReasons.push("recommendation_quality_below_threshold");
    warnings.push(
      `Recommendation quality gates failed: ${recommendationHealth.alerts.join(", ")}. Returning latest available rows in degraded mode.`,
    );
  }

  const topUnder50 = sortByConfidence(
    processedUniverse.filter((row) => row.assetType === "equities" && row.price !== null && row.price < 50 && row.classification === "BUY"),
  ).slice(0, 5);

  const topByAssetType = {
    equities: sortByConfidence(processedUniverse.filter((row) => row.assetType === "equities" && row.classification === "BUY")).slice(0, 10),
    index: sortByConfidence(processedUniverse.filter((row) => row.assetType === "index" && row.classification === "BUY")).slice(0, 10),
    crypto: sortByConfidence(processedUniverse.filter((row) => row.assetType === "crypto" && row.classification === "BUY")).slice(0, 10),
    etf: sortByConfidence(processedUniverse.filter((row) => row.assetType === "etf" && row.classification === "BUY")).slice(0, 10),
  };

  return NextResponse.json({
    ...publicationFields,
    topUnder50,
    topByAssetType,
    allMarket: sortByTicker(processedUniverse),
    universeStats: {
      totalRows: allRows.length,
      processedRows: processedUniverse.length,
      excludedRows: allRows.length - processedUniverse.length,
    },
    decisionSummary,
    recommendationHealth,
    snapshotSource: snapshot.sourcePath,
    data_source: snapshot.dataSource,
    snapshot_generated_at_utc: snapshot.generatedAtUtc,
    publicationBundle: {
      sourcePath: publicationState.sourcePath,
      failureCount: publicationState.failures.length,
      generated_at_utc: publicationState.generatedAtUtc,
      completed_at_utc: publicationState.completedAtUtc,
      report_generated_at_utc: publicationState.reportGeneratedAtUtc,
      validation_status: publicationState.validationStatus,
    },
    servingBundle: {
      sourcePath: publicationState.sourcePath,
      failureCount: publicationState.failures.length,
      run_id: publicationState.runId,
      active_runtime_run_id: publicationState.activeRuntimeRunId,
      active_runtime_bundle_valid: publicationState.activationState === "activated",
      fallback_applied: false,
      fallback_reason: publicationState.blockingReasonCode,
      generated_at_utc: publicationState.generatedAtUtc,
      validation_status: publicationState.validationStatus,
      snapshot_publication_id: publicationState.snapshotPublicationId,
      quote_publication_id: publicationState.quotePublicationId,
      quote_binding_status: publicationState.quoteBindingStatus,
    },
    freshness: publicationState.freshness,
    priceCache: {
      sourcePath: quoteCache.sourcePath,
      failureCount: quoteCache.failures.length,
    },
    provenance: {
      use_persisted_requested: true,
      strict_mode: true,
      sourcePath: publishedDecisionLoad.sourcePath,
      failureCount: publishedDecisionLoad.failures.length,
      rows_total: allRows.length,
      rows_persisted_available: persistedRowsAvailable,
      rows_persisted_valid: persistedRowsValid,
      rows_persisted_used: persistedRowsUsed,
      rows_recomputed_used: 0,
    },
    degraded: degradedReasons.length > 0,
    degradedReason: degradedReasons[0] ?? null,
    degradedReasons,
    warnings,
  });
}
