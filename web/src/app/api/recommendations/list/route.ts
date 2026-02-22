import { NextResponse } from "next/server";

import {
  classificationFromDecision,
  decisionInfoFromRow,
  loadSnapshotRows,
  type SnapshotRow,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";

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

function toRecommendationRow(row: SnapshotRow): RecommendationRow | null {
  const ticker = String(row.ticker ?? "").trim().toUpperCase();
  if (!ticker) return null;

  const sUf = toNumber(row.S_UF);
  const rUf = toNumber(row.R_UF);
  const decisionInfo = decisionInfoFromRow(row);
  const classification = classificationFromDecision(decisionInfo.decision);

  return {
    ticker,
    assetType: normalizeAssetType(row.asset_type),
    price: toNumberOrNull(row.price),
    decision: decisionInfo.decision,
    decisionReason: decisionInfo.reasonText,
    decisionReasonCode: decisionInfo.reasonCode,
    confidence: (sUf + rUf) / 2,
    S_UF: sUf,
    R_UF: rUf,
    barCount: decisionInfo.barCount,
    minBarsForAccumulate: decisionInfo.minBarsForAccumulate,
    classification,
    regime: String(row.regime ?? "UNKNOWN"),
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
  if (whole > 180000) return 180000;
  return whole;
}

const SNAPSHOT_LOAD_TIMEOUT_MS = normalizeTimeoutMs(process.env.TFE_RECOMMENDATIONS_SNAPSHOT_TIMEOUT_MS, 45000);

async function loadSnapshotRowsWithTimeout(): Promise<Awaited<ReturnType<typeof loadSnapshotRows>>> {
  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  try {
    return await Promise.race([
      loadSnapshotRows(),
      new Promise<Awaited<ReturnType<typeof loadSnapshotRows>>>((_, reject) => {
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

function degradedEmptyResponse(extra: Record<string, unknown>) {
  return NextResponse.json({
    topUnder50: [],
    topByAssetType: {
      equities: [],
      index: [],
      crypto: [],
      etf: [],
    },
    allMarket: [],
    universeStats: {
      totalRows: 0,
      processedRows: 0,
      excludedRows: 0,
    },
    snapshotSource: null,
    degraded: true,
    ...extra,
  });
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  let snapshot: Awaited<ReturnType<typeof loadSnapshotRows>>;

  try {
    snapshot = await loadSnapshotRowsWithTimeout();
  } catch (error) {
    const details = error instanceof Error ? error.message : "Unknown snapshot load error.";
    const timedOut = details.toLowerCase().includes("timed out");

    console.error("[recommendations/list] snapshot load failed", {
      timedOut,
      timeoutMs: SNAPSHOT_LOAD_TIMEOUT_MS,
      details,
    });

    return degradedEmptyResponse({
      degradedReason: timedOut ? "snapshot_load_timeout" : "snapshot_load_failed",
      details,
      timeoutMs: SNAPSHOT_LOAD_TIMEOUT_MS,
    });
  }

  if (!snapshot.sourcePath || snapshot.rows.length === 0) {
    return degradedEmptyResponse({
      degradedReason: "snapshot_unavailable_or_empty",
      details: "Could not load uf_snapshot.ses.json envelope.",
      attemptedPaths: snapshot.attemptedPaths,
      failures: snapshot.failures,
    });
  }

  const allRows: RecommendationRow[] = [];

  for (const row of snapshot.rows) {
    const transformed = toRecommendationRow(row);
    if (transformed) allRows.push(transformed);
  }

  const processedUniverse = allRows.filter(isProcessedUfRow);

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
    topUnder50,
    topByAssetType,
    allMarket: sortByTicker(processedUniverse),
    universeStats: {
      totalRows: allRows.length,
      processedRows: processedUniverse.length,
      excludedRows: allRows.length - processedUniverse.length,
    },
    snapshotSource: snapshot.sourcePath,
    degraded: false,
  });
}
