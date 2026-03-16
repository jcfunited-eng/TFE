import { NextResponse } from "next/server";

import {
  classificationFromDecision,
  findTickerRow,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { loadLivePriceMap, type LivePriceQuote } from "@/lib/live-price";
import { loadCanonicalPublicationState, publicationContractFields } from "@/lib/publication-state";
import {
  loadPublishedDecisionMapForRows,
  type PublishedDecisionLoadResult,
  type PublishedDecisionRecord,
} from "@/lib/published-decision";
import {
  quoteCachePriceFromRow,
  type ScreenerQuoteCacheRow,
} from "@/lib/screener-quote-cache";
import {
  loadRuntimeQuoteCacheFromPostgres,
  loadRuntimeSnapshotRowsFromPostgres,
} from "@/lib/runtime-postgres";
import {
  addPortfolioLot,
  loadPortfolioLots,
  removePortfolioLot,
  updatePortfolioLot,
  type PortfolioLot,
} from "@/lib/portfolio-store";

export const runtime = "nodejs";

type PositionRow = {
  ticker: string;
  assetType: "Equities" | "Index" | "Crypto" | "ETF" | "Other";
  units: number;
  avgCost: number;
  costBasis: number;
  currentPrice: number | null;
  marketValue: number | null;
  unrealizedPnL: number | null;
  unrealizedPnLPct: number | null;
  decision: "Accumulate" | "Hold" | "Avoid";
  decisionReason: string;
  decisionReasonCode: string;
  classification: "BUY" | "HOLD" | "SELL";
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
};

type Summary = {
  totalLots: number;
  totalPositions: number;
  totalUnits: number;
  totalCostBasis: number;
  totalMarketValue: number | null;
  totalUnrealizedPnL: number | null;
  totalUnrealizedPnLPct: number | null;
  realizedPnL: number | null;
  realizedPnLPct: number | null;
  realizedPnLStatus: "unavailable_no_trade_ledger" | "computed_from_trade_ledger";
  realizedPnLMethod: "trade_ledger_required" | "trade_ledger_v1";
};

type UnresolvedPortfolioTicker = {
  ticker: string;
  status: "missing" | "invalid";
  lots: number;
  units: number;
  costBasis: number;
};

type PortfolioProvenance = {
  status: "ok" | "partial";
  sourcePath: string | null;
  failureCount: number;
  rows_required: number;
  rows_valid: number;
  missingTickers: string[];
  invalidTickers: string[];
  unresolvedTickers: UnresolvedPortfolioTicker[];
};

type BenchmarkComparison = {
  symbol: "SPY";
  portfolioReturnPct: number | null;
  benchmarkReturnPct: number | null;
  relativeReturnPctPoints: number | null;
  status: "unavailable_same_dates_same_dollars_ledger_required" | "computed_same_dates_same_dollars_v1";
  method: "same_dates_same_dollars_ledger_required" | "same_dates_same_dollars_v1";
};

type AllocatorAction = "BUY_MORE" | "TRIM" | "EXIT" | "HOLD";

type AllocatorRow = {
  ticker: string;
  decision: "Accumulate" | "Hold" | "Avoid";
  classification: "BUY" | "HOLD" | "SELL";
  confidence: number;
  currentWeightPct: number;
  targetWeightPct: number;
  currentValue: number;
  targetValue: number;
  driftPctPoints: number;
  action: AllocatorAction;
  rebalanceDollar: number;
  rebalanceUnits: number | null;
  reason: string;
};

type AllocatorPlan = {
  generatedAtUtc: string;
  method: "PFSC_STRUCTURAL_ALLOCATOR_V1";
  rebalanceThresholdPctPoints: number;
  portfolioValueUsed: number;
  status: "ok" | "no_priced_positions" | "no_allocatable_scores";
  missingPriceTickers: string[];
  totals: {
    buyDollar: number;
    trimDollar: number;
    exitDollar: number;
  };
  rows: AllocatorRow[];
};

type PostBody = {
  ticker?: unknown;
  units?: unknown;
  unitCost?: unknown;
};

type PutBody = {
  id?: unknown;
  units?: unknown;
  unitCost?: unknown;
};

type SnapshotLoadResult = Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>;

const HOLD_DECISION_MULTIPLIER = 0.5;
const HOLD_FALLBACK_UNMAPPED_REASON_CODE = "PSCF_FALLBACK_CELL_UNMAPPED";
const ALLOW_TRIM_WHEN_DECISION_IS_ACCUMULATE = false;
const REBALANCE_THRESHOLD_PCT_POINTS = 1.0;
const SNAPSHOT_LOAD_TIMEOUT_MS = normalizeTimeoutMs(process.env.TFE_PORTFOLIO_SNAPSHOT_TIMEOUT_MS, 20000);

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function normalizeTicker(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeTimeoutMs(value: unknown, fallbackMs: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallbackMs;

  const whole = Math.floor(n);
  if (whole < 1000) return 1000;
  if (whole > 45000) return 45000;
  return whole;
}

async function loadSnapshotRowsWithTimeout(): Promise<SnapshotLoadResult> {
  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  try {
    return await Promise.race([
      loadRuntimeSnapshotRowsFromPostgres(),
      new Promise<SnapshotLoadResult>((_, reject) => {
        timeoutHandle = setTimeout(() => {
          reject(new Error(`Portfolio snapshot load timed out after ${SNAPSHOT_LOAD_TIMEOUT_MS}ms.`));
        }, SNAPSHOT_LOAD_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle);
  }
}

function normalizeAssetType(value: unknown): PositionRow["assetType"] {
  const raw = String(value ?? "")
    .trim()
    .toLowerCase();

  if (["equity", "equities", "stock", "stocks"].includes(raw)) return "Equities";
  if (["index", "indices"].includes(raw)) return "Index";
  if (["crypto", "cryptocurrency", "coin", "token"].includes(raw)) return "Crypto";
  if (["etf", "fund"].includes(raw)) return "ETF";

  return "Other";
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  if (value <= 0) return 0;
  if (value >= 1) return 1;
  return value;
}

function buildAllocatorPlan(positions: PositionRow[], summary: Summary): AllocatorPlan {
  const generatedAtUtc = new Date().toISOString();
  const missingPriceTickers: string[] = [];

  let pricedPortfolioValue = 0;
  for (const row of positions) {
    if (row.marketValue === null || row.marketValue <= 0) {
      missingPriceTickers.push(row.ticker);
      continue;
    }
    pricedPortfolioValue += row.marketValue;
  }

  if (!(pricedPortfolioValue > 0)) {
    return {
      generatedAtUtc,
      method: "PFSC_STRUCTURAL_ALLOCATOR_V1",
      rebalanceThresholdPctPoints: REBALANCE_THRESHOLD_PCT_POINTS,
      portfolioValueUsed: 0,
      status: "no_priced_positions",
      missingPriceTickers,
      totals: {
        buyDollar: 0,
        trimDollar: 0,
        exitDollar: 0,
      },
      rows: [],
    };
  }

  const portfolioValueUsed =
    summary.totalMarketValue !== null && summary.totalMarketValue > 0 ? summary.totalMarketValue : pricedPortfolioValue;

  const scored = positions
    .filter((row) => row.marketValue !== null && row.marketValue > 0)
    .map((row) => {
      const confidence = clamp01((row.S_UF + row.R_UF) / 2);
      const holdIsFallbackUnmapped =
        row.decision === "Hold" && row.decisionReasonCode === HOLD_FALLBACK_UNMAPPED_REASON_CODE;
      let score = 0;

      if (row.decision === "Accumulate") {
        score = confidence;
      } else if (row.decision === "Hold") {
        score = confidence * HOLD_DECISION_MULTIPLIER;
      } else {
        score = 0;
      }

      return { row, confidence, score, holdIsFallbackUnmapped };
    });

  const scoreTotal = scored.reduce((sum, item) => sum + item.score, 0);
  if (!(scoreTotal > 0)) {
    return {
      generatedAtUtc,
      method: "PFSC_STRUCTURAL_ALLOCATOR_V1",
      rebalanceThresholdPctPoints: REBALANCE_THRESHOLD_PCT_POINTS,
      portfolioValueUsed,
      status: "no_allocatable_scores",
      missingPriceTickers,
      totals: {
        buyDollar: 0,
        trimDollar: 0,
        exitDollar: 0,
      },
      rows: [],
    };
  }

  let buyDollar = 0;
  let trimDollar = 0;
  let exitDollar = 0;

  const rows: AllocatorRow[] = scored.map((item) => {
    const { row, confidence, score, holdIsFallbackUnmapped } = item;
    const currentValue = row.marketValue ?? 0;
    const currentWeight = portfolioValueUsed > 0 ? currentValue / portfolioValueUsed : 0;
    const targetWeight = row.decision === "Avoid" ? 0 : score / scoreTotal;
    const targetValue = portfolioValueUsed * targetWeight;
    const driftPctPoints = (targetWeight - currentWeight) * 100;

    let action: AllocatorAction = "HOLD";
    let rebalanceDollar = 0;
    let rebalanceUnits: number | null = null;

    if (row.decision === "Avoid" && currentValue > 0) {
      action = "EXIT";
      rebalanceDollar = -currentValue;
      exitDollar += Math.abs(rebalanceDollar);
    } else if (Math.abs(driftPctPoints) > REBALANCE_THRESHOLD_PCT_POINTS) {
      rebalanceDollar = targetValue - currentValue;
      if (rebalanceDollar > 0) {
        if (holdIsFallbackUnmapped) {
          action = "HOLD";
          rebalanceDollar = 0;
        } else {
          action = "BUY_MORE";
          buyDollar += rebalanceDollar;
        }
      } else if (rebalanceDollar < 0) {
        if (row.decision === "Accumulate" && !ALLOW_TRIM_WHEN_DECISION_IS_ACCUMULATE) {
          action = "HOLD";
          rebalanceDollar = 0;
        } else {
          action = "TRIM";
          trimDollar += Math.abs(rebalanceDollar);
        }
      }
    }

    if (row.currentPrice !== null && row.currentPrice > 0 && action !== "HOLD") {
      rebalanceUnits = Math.abs(rebalanceDollar) / row.currentPrice;
    }

    const reason =
      row.decision === "Avoid"
        ? `PFSC decision is Avoid; target set to 0% for this position. confidence=${confidence.toFixed(3)}.`
        : holdIsFallbackUnmapped && driftPctPoints > REBALANCE_THRESHOLD_PCT_POINTS
          ? `Fallback Hold (unmapped PSCF cell) suppresses BUY_MORE; confidence=${confidence.toFixed(3)}.`
          : row.decision === "Accumulate" && rebalanceDollar === 0 && driftPctPoints < 0 && !ALLOW_TRIM_WHEN_DECISION_IS_ACCUMULATE
            ? `PFSC decision is Accumulate; overweight trim is suppressed for decision alignment. confidence=${confidence.toFixed(3)}.`
            : `PFSC target derived from decision=${row.decision}, confidence=${confidence.toFixed(3)}, hold_multiplier=${HOLD_DECISION_MULTIPLIER}.`;

    return {
      ticker: row.ticker,
      decision: row.decision,
      classification: row.classification,
      confidence,
      currentWeightPct: currentWeight * 100,
      targetWeightPct: targetWeight * 100,
      currentValue,
      targetValue,
      driftPctPoints,
      action,
      rebalanceDollar,
      rebalanceUnits,
      reason,
    };
  });

  rows.sort((a, b) => Math.abs(b.rebalanceDollar) - Math.abs(a.rebalanceDollar));

  return {
    generatedAtUtc,
    method: "PFSC_STRUCTURAL_ALLOCATOR_V1",
    rebalanceThresholdPctPoints: REBALANCE_THRESHOLD_PCT_POINTS,
    portfolioValueUsed,
    status: "ok",
    missingPriceTickers,
    totals: {
      buyDollar,
      trimDollar,
      exitDollar,
    },
    rows,
  };
}

function buildUnresolvedPortfolioTickers(
  lots: PortfolioLot[],
  publishedDecisionLoad: PublishedDecisionLoadResult,
): UnresolvedPortfolioTicker[] {
  const statusByTicker = new Map<string, UnresolvedPortfolioTicker["status"]>();

  for (const ticker of publishedDecisionLoad.missingTickers) {
    statusByTicker.set(ticker, "missing");
  }
  for (const ticker of publishedDecisionLoad.invalidTickers) {
    statusByTicker.set(ticker, "invalid");
  }

  const aggregate = new Map<string, UnresolvedPortfolioTicker>();
  for (const lot of lots) {
    const ticker = normalizeTicker(lot.ticker);
    const status = statusByTicker.get(ticker);
    if (!ticker || !status) continue;

    const existing = aggregate.get(ticker);
    if (existing) {
      existing.lots += 1;
      existing.units += lot.units;
      existing.costBasis += lot.units * lot.unitCost;
      continue;
    }

    aggregate.set(ticker, {
      ticker,
      status,
      lots: 1,
      units: lot.units,
      costBasis: lot.units * lot.unitCost,
    });
  }

  return Array.from(aggregate.values()).sort((a, b) => a.ticker.localeCompare(b.ticker));
}

function buildPortfolioProvenance(
  lots: PortfolioLot[],
  publishedDecisionLoad: PublishedDecisionLoadResult,
): PortfolioProvenance {
  const unresolvedTickers = buildUnresolvedPortfolioTickers(lots, publishedDecisionLoad);
  return {
    status: unresolvedTickers.length > 0 ? "partial" : "ok",
    sourcePath: publishedDecisionLoad.sourcePath,
    failureCount: publishedDecisionLoad.failures.length,
    rows_required: publishedDecisionLoad.rowsRequired,
    rows_valid: publishedDecisionLoad.rowsValid,
    missingTickers: publishedDecisionLoad.missingTickers,
    invalidTickers: publishedDecisionLoad.invalidTickers,
    unresolvedTickers,
  };
}

function buildPortfolioWarning(unresolvedTickers: UnresolvedPortfolioTicker[]): string | null {
  if (unresolvedTickers.length === 0) return null;

  const labels = unresolvedTickers.map((row) => row.ticker).join(", ");
  const unresolvedLotCount = unresolvedTickers.reduce((sum, row) => sum + row.lots, 0);
  const unresolvedCostBasis = unresolvedTickers.reduce((sum, row) => sum + row.costBasis, 0);

  return `Portfolio analytics exclude unresolved published decision provenance for ${labels}. Excluded lots=${unresolvedLotCount}. Excluded cost basis=${unresolvedCostBasis.toFixed(2)}.`;
}

function aggregatePositions(
  lots: PortfolioLot[],
  snapshotRows: SnapshotLoadResult["rows"],
  livePriceMap: Map<string, LivePriceQuote>,
  quoteCacheQuotes: Record<string, ScreenerQuoteCacheRow>,
  publishedDecisionMap: Record<string, PublishedDecisionRecord>,
): PositionRow[] {
  const groups = new Map<string, PortfolioLot[]>();

  for (const lot of lots) {
    const ticker = normalizeTicker(lot.ticker);
    if (!ticker) continue;

    const bucket = groups.get(ticker);
    if (bucket) {
      bucket.push(lot);
    } else {
      groups.set(ticker, [lot]);
    }
  }

  const positions: PositionRow[] = [];

  for (const [ticker, tickerLots] of groups.entries()) {
    let units = 0;
    let costBasis = 0;

    for (const lot of tickerLots) {
      units += lot.units;
      costBasis += lot.units * lot.unitCost;
    }

    const avgCost = units > 0 ? costBasis / units : 0;

    const row = findTickerRow(snapshotRows, ticker);
    const published = row ? publishedDecisionMap[ticker] : null;
    if (!row || !published) {
      continue;
    }

    const livePrice = livePriceMap.get(ticker)?.price ?? null;
    const quoteCachePrice = quoteCachePriceFromRow(quoteCacheQuotes[ticker]);
    const snapshotPrice = toNumberOrNull(row.price);
    const currentPrice = livePrice ?? quoteCachePrice ?? snapshotPrice;
    const marketValue = currentPrice === null ? null : currentPrice * units;
    const unrealizedPnL = marketValue === null ? null : marketValue - costBasis;
    const unrealizedPnLPct = unrealizedPnL === null || costBasis <= 0 ? null : unrealizedPnL / costBasis;

    positions.push({
      ticker,
      assetType: normalizeAssetType(row?.asset_type),
      units,
      avgCost,
      costBasis,
      currentPrice,
      marketValue,
      unrealizedPnL,
      unrealizedPnLPct,
      decision: published.decision,
      decisionReason: published.decisionReason,
      decisionReasonCode: published.decisionReasonCode,
      classification: classificationFromDecision(published.decision),
      S_UF: toNumber(row.S_UF),
      R_UF: toNumber(row.R_UF),
      barCount: published.barCount,
      minBarsForAccumulate: published.minBarsForAccumulate,
    });
  }

  positions.sort((a, b) => a.ticker.localeCompare(b.ticker));
  return positions;
}

function buildSummary(lots: PortfolioLot[], positions: PositionRow[]): Summary {
  let totalUnits = 0;
  let totalCostBasis = 0;

  for (const position of positions) {
    totalUnits += position.units;
    totalCostBasis += position.costBasis;
  }

  let totalMarketValue = 0;
  let anyMissingPrice = false;

  for (const position of positions) {
    if (position.marketValue === null) {
      anyMissingPrice = true;
      continue;
    }
    totalMarketValue += position.marketValue;
  }

  const resolvedMarketValue = anyMissingPrice ? null : totalMarketValue;
  const totalUnrealizedPnL = resolvedMarketValue === null ? null : resolvedMarketValue - totalCostBasis;
  const totalUnrealizedPnLPct =
    totalUnrealizedPnL === null || totalCostBasis <= 0 ? null : totalUnrealizedPnL / totalCostBasis;

  // Portfolio lots are current-holdings records only; no trade ledger exists yet for realized P/L.
  const realizedPnL: number | null = null;
  const realizedPnLPct: number | null = null;
  const realizedPnLStatus: Summary["realizedPnLStatus"] = "unavailable_no_trade_ledger";
  const realizedPnLMethod: Summary["realizedPnLMethod"] = "trade_ledger_required";

  return {
    totalLots: lots.length,
    totalPositions: positions.length,
    totalUnits,
    totalCostBasis,
    totalMarketValue: resolvedMarketValue,
    totalUnrealizedPnL,
    totalUnrealizedPnLPct,
    realizedPnL,
    realizedPnLPct,
    realizedPnLStatus,
    realizedPnLMethod,
  };
}

function buildBenchmarkComparison(): BenchmarkComparison {
  return {
    symbol: "SPY",
    portfolioReturnPct: null,
    benchmarkReturnPct: null,
    relativeReturnPctPoints: null,
    status: "unavailable_same_dates_same_dollars_ledger_required",
    method: "same_dates_same_dollars_ledger_required",
  };
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const portfolio = await loadPortfolioLots(sessionUser.username);

  let snapshotRows: SnapshotLoadResult["rows"] = [];
  let snapshotSource: string | null = null;
  let snapshotFailures: SnapshotLoadResult["failures"] = [];
  let snapshotRunId: string | null = null;
  let snapshotGeneratedAtUtc: string | null = null;

  try {
    const snapshot = await loadSnapshotRowsWithTimeout();
    snapshotRows = snapshot.rows;
    snapshotSource = snapshot.sourcePath;
    snapshotFailures = snapshot.failures;
    snapshotRunId = snapshot.runId;
    snapshotGeneratedAtUtc = snapshot.generatedAtUtc;
  } catch (error) {
    const reason = error instanceof Error ? error.message : "Unknown snapshot load failure.";
    snapshotFailures = [{ path: "runtime_decisions_latest", reason }];
  }

  if (!snapshotSource || snapshotRows.length === 0) {
    const publicationState = await loadCanonicalPublicationState({
      snapshot: {
        available: false,
        runId: snapshotRunId,
        generatedAtUtc: snapshotGeneratedAtUtc,
      },
      quote: { available: false, runId: null },
    });
    return NextResponse.json(
      {
        error: "Portfolio unavailable because runtime Postgres snapshot is unavailable or empty.",
        source: portfolio.filePath,
        snapshotSource,
        snapshotFailures,
        ...publicationContractFields(publicationState),
      },
      { status: 503 },
    );
  }

  const uniqueTickers = Array.from(
    new Set(
      portfolio.lots
        .map((lot) => normalizeTicker(lot.ticker))
        .filter((ticker) => ticker.length > 0),
    ),
  );

  const livePriceMap = await loadLivePriceMap(
    uniqueTickers.map((ticker) => {
      const row = findTickerRow(snapshotRows, ticker);
      return {
        ticker,
        assetType: row?.asset_type,
      };
    }),
  );

  const quoteCache = await loadRuntimeQuoteCacheFromPostgres();
  const publicationState = await loadCanonicalPublicationState({
    snapshot: {
      available: true,
      runId: snapshotRunId,
      generatedAtUtc: snapshotGeneratedAtUtc,
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
        error: "Portfolio unavailable because runtime Postgres quote cache is unavailable or empty.",
        source: portfolio.filePath,
        snapshotSource,
        snapshotFailures,
        quoteFailures: quoteCache.failures,
        ...publicationFields,
      },
      { status: 503 },
    );
  }

  if (publicationState.servingState === "blocked") {
    return NextResponse.json(
      {
        error: "Portfolio is unavailable. Canonical publication state blocked this response.",
        blocked: true,
        status: "blocked",
        ...publicationFields,
        source: portfolio.filePath,
        snapshotSource,
        snapshotFailures,
        quoteSource: quoteCache.sourcePath,
        quoteFailures: quoteCache.failures,
        data_source: "postgres",
        snapshot_generated_at_utc: snapshotGeneratedAtUtc,
        freshness: publicationState.freshness,
        sourceRuns: {
          publication_run_id: publicationState.runId,
          snapshot_run_id: snapshotRunId,
          quote_run_id: quoteCache.runId,
          active_runtime_run_id: publicationState.activeRuntimeRunId,
        },
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
          run_id: publicationState.servingRunId,
          active_runtime_run_id: publicationState.activeRuntimeRunId,
          active_runtime_bundle_valid: publicationState.activationState === "activated",
          fallback_applied: publicationState.servingFallbackApplied,
          fallback_reason: publicationState.servingFallbackReason,
          generated_at_utc: publicationState.generatedAtUtc,
          validation_status: publicationState.validationStatus,
          snapshot_publication_id: publicationState.snapshotPublicationId,
          quote_publication_id: publicationState.quotePublicationId,
          quote_binding_status: publicationState.quoteBindingStatus,
        },
      },
      { status: 503 },
    );
  }

  const publishedDecisionLoad = await loadPublishedDecisionMapForRows(
    publicationState.servingRunId ?? publicationState.runId,
    snapshotRows,
    uniqueTickers,
  );
  const portfolioProvenance = buildPortfolioProvenance(portfolio.lots, publishedDecisionLoad);
  const portfolioWarning = buildPortfolioWarning(portfolioProvenance.unresolvedTickers);

  const positions = aggregatePositions(
    portfolio.lots,
    snapshotRows,
    livePriceMap,
    quoteCache.quotes,
    publishedDecisionLoad.rows,
  );
  const summary = buildSummary(portfolio.lots, positions);
  const benchmark = buildBenchmarkComparison();
  const allocatorPlan = buildAllocatorPlan(positions, summary);

  return NextResponse.json({
    ...publicationFields,
    lots: portfolio.lots,
    positions,
    summary,
    benchmark,
    allocatorPlan,
    warning: portfolioWarning,
    provenance: portfolioProvenance,
    source: portfolio.filePath,
    snapshotSource,
    snapshotFailures,
    data_source: "postgres",
    snapshot_generated_at_utc: snapshotGeneratedAtUtc,
    freshness: publicationState.freshness,
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
      run_id: publicationState.servingRunId,
      active_runtime_run_id: publicationState.activeRuntimeRunId,
      active_runtime_bundle_valid: publicationState.activationState === "activated",
      fallback_applied: publicationState.servingFallbackApplied,
      fallback_reason: publicationState.servingFallbackReason,
      generated_at_utc: publicationState.generatedAtUtc,
      validation_status: publicationState.validationStatus,
      snapshot_publication_id: publicationState.snapshotPublicationId,
      quote_publication_id: publicationState.quotePublicationId,
      quote_binding_status: publicationState.quoteBindingStatus,
    },
    quoteSource: quoteCache.sourcePath,
    quoteFailures: quoteCache.failures,
  });
}

export async function POST(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  let body: PostBody;

  try {
    body = (await request.json()) as PostBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const ticker = normalizeTicker(body.ticker);
  const units = toNumber(body.units);

  if (!ticker) {
    return NextResponse.json({ error: "Ticker is required." }, { status: 400 });
  }

  if (!(units > 0)) {
    return NextResponse.json({ error: "Units must be greater than zero." }, { status: 400 });
  }

  let unitCost = toNumber(body.unitCost);
  let snapshotLoadError: string | null = null;

  if (!(unitCost > 0)) {
    const livePriceMap = await loadLivePriceMap([{ ticker }]);
    const livePrice = livePriceMap.get(ticker)?.price ?? null;
    if (livePrice !== null && livePrice > 0) {
      unitCost = livePrice;
    }
  }

  if (!(unitCost > 0)) {
    const quoteCache = await loadRuntimeQuoteCacheFromPostgres();
    const quoteCachePrice = quoteCachePriceFromRow(quoteCache.quotes[ticker]);
    if (quoteCachePrice !== null && quoteCachePrice > 0) {
      unitCost = quoteCachePrice;
    }
  }

  if (!(unitCost > 0)) {
    let snapshotRows: SnapshotLoadResult["rows"] = [];

    try {
      const snapshot = await loadSnapshotRowsWithTimeout();
      snapshotRows = snapshot.rows;
    } catch (error) {
      snapshotLoadError = error instanceof Error ? error.message : "Unknown snapshot load failure.";
    }

    const row = findTickerRow(snapshotRows, ticker);
    const price = row ? toNumber(row.price) : 0;
    unitCost = price;
  }

  if (!(unitCost > 0)) {
    return NextResponse.json(
      {
        error: snapshotLoadError
          ? `Unit cost is required because runtime snapshot is unavailable (${snapshotLoadError}).`
          : "Unit cost is required because no valid current price was found from live feed or runtime Postgres data.",
      },
      { status: 400 },
    );
  }

  try {
    const result = await addPortfolioLot(sessionUser.username, {
      ticker,
      units,
      unitCost,
    });

    return NextResponse.json({
      added: true,
      addedLot: result.addedLot,
      lots: result.lots,
      source: result.filePath,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to add portfolio lot.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PUT(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  let body: PutBody;

  try {
    body = (await request.json()) as PutBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const id = String(body.id ?? "").trim();
  if (!id) {
    return NextResponse.json({ error: "Lot id is required." }, { status: 400 });
  }

  const hasUnits = body.units !== undefined;
  const hasUnitCost = body.unitCost !== undefined;

  if (!hasUnits && !hasUnitCost) {
    return NextResponse.json({ error: "Provide units or unitCost to update." }, { status: 400 });
  }

  const patch: { units?: number; unitCost?: number } = {};

  if (hasUnits) {
    const units = toNumber(body.units);
    if (!(units > 0)) {
      return NextResponse.json({ error: "Units must be greater than zero." }, { status: 400 });
    }
    patch.units = units;
  }

  if (hasUnitCost) {
    const unitCost = toNumber(body.unitCost);
    if (!(unitCost >= 0)) {
      return NextResponse.json({ error: "Unit cost must be zero or greater." }, { status: 400 });
    }
    patch.unitCost = unitCost;
  }

  try {
    const result = await updatePortfolioLot(sessionUser.username, id, patch);

    return NextResponse.json({
      updated: true,
      updatedLot: result.updatedLot,
      lots: result.lots,
      source: result.filePath,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to update portfolio lot.";
    const status = message.toLowerCase().includes("not found") ? 404 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}

export async function DELETE(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const id = String(searchParams.get("id") ?? "").trim();

  if (!id) {
    return NextResponse.json({ error: "Lot id is required." }, { status: 400 });
  }

  try {
    const result = await removePortfolioLot(sessionUser.username, id);

    return NextResponse.json({
      removed: result.removed,
      lots: result.lots,
      source: result.filePath,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to remove lot.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
