import { NextResponse } from "next/server";

import {
  classificationFromDecision,
  decisionInfoFromRow,
  findTickerRow,
  loadSnapshotRows,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";
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

type SnapshotLoadResult = Awaited<ReturnType<typeof loadSnapshotRows>>;

const HOLD_DECISION_MULTIPLIER = 0.5;
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
  if (whole > 180000) return 180000;
  return whole;
}

async function loadSnapshotRowsWithTimeout(): Promise<SnapshotLoadResult> {
  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  try {
    return await Promise.race([
      loadSnapshotRows(),
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
      let score = 0;

      if (row.decision === "Accumulate") {
        score = confidence;
      } else if (row.decision === "Hold") {
        score = confidence * HOLD_DECISION_MULTIPLIER;
      } else {
        score = 0;
      }

      return { row, confidence, score };
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
    const { row, confidence, score } = item;
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
        action = "BUY_MORE";
        buyDollar += rebalanceDollar;
      } else if (rebalanceDollar < 0) {
        action = "TRIM";
        trimDollar += Math.abs(rebalanceDollar);
      }
    }

    if (row.currentPrice !== null && row.currentPrice > 0 && action !== "HOLD") {
      rebalanceUnits = Math.abs(rebalanceDollar) / row.currentPrice;
    }

    const reason =
      row.decision === "Avoid"
        ? `PFSC decision is Avoid; target set to 0% for this position. confidence=${confidence.toFixed(3)}.`
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

function aggregatePositions(lots: PortfolioLot[], snapshotRows: Awaited<ReturnType<typeof loadSnapshotRows>>["rows"]): PositionRow[] {
  const groups = new Map<string, PortfolioLot[]>();

  for (const lot of lots) {
    const ticker = lot.ticker;
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
    const decisionInfo = decisionInfoFromRow(row);

    const currentPrice = row ? toNumberOrNull(row.price) : null;
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
      decision: decisionInfo.decision,
      decisionReason: decisionInfo.reasonText,
      decisionReasonCode: decisionInfo.reasonCode,
      classification: classificationFromDecision(decisionInfo.decision),
      S_UF: row ? toNumber(row.S_UF) : 0,
      R_UF: row ? toNumber(row.R_UF) : 0,
      barCount: decisionInfo.barCount,
      minBarsForAccumulate: decisionInfo.minBarsForAccumulate,
    });
  }

  positions.sort((a, b) => a.ticker.localeCompare(b.ticker));
  return positions;
}

function buildSummary(lots: PortfolioLot[], positions: PositionRow[]): Summary {
  let totalUnits = 0;
  let totalCostBasis = 0;

  for (const lot of lots) {
    totalUnits += lot.units;
    totalCostBasis += lot.units * lot.unitCost;
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

  return {
    totalLots: lots.length,
    totalPositions: positions.length,
    totalUnits,
    totalCostBasis,
    totalMarketValue: resolvedMarketValue,
    totalUnrealizedPnL,
    totalUnrealizedPnLPct,
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

  try {
    const snapshot = await loadSnapshotRowsWithTimeout();
    snapshotRows = snapshot.rows;
    snapshotSource = snapshot.sourcePath;
    snapshotFailures = snapshot.failures;
  } catch (error) {
    const reason = error instanceof Error ? error.message : "Unknown snapshot load failure.";
    snapshotFailures = [{ path: "uf_snapshot.ses.json", reason }];
  }

  const positions = aggregatePositions(portfolio.lots, snapshotRows);
  const summary = buildSummary(portfolio.lots, positions);
  const allocatorPlan = buildAllocatorPlan(positions, summary);

  return NextResponse.json({
    lots: portfolio.lots,
    positions,
    summary,
    allocatorPlan,
    source: portfolio.filePath,
    snapshotSource,
    snapshotFailures,
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
          ? `Unit cost is required because snapshot is unavailable (${snapshotLoadError}).`
          : "Unit cost is required because no valid current price was found in snapshot.",
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
