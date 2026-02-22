import { NextResponse } from "next/server";

import {
  classificationFromDecision,
  decisionInfoFromRow,
  findTickerRow,
  loadSnapshotRows,
  type SnapshotRow,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { loadWatchlistSymbols, saveWatchlistSymbols } from "@/lib/watchlist-store";

export const runtime = "nodejs";

type SaveBody = {
  symbols?: unknown;
};

type WatchlistMetricRow = {
  ticker: string;
  decision: "Accumulate" | "Hold" | "Avoid";
  decisionReason: string;
  decisionReasonCode: string;
  classification: "BUY" | "HOLD" | "SELL";
  price: number | null;
  regime: string;
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
  stability_score: number | null;
  max_dd: number | null;
};

type SnapshotLoadResult = Awaited<ReturnType<typeof loadSnapshotRows>>;

const SNAPSHOT_LOAD_TIMEOUT_MS = normalizeTimeoutMs(process.env.TFE_WATCHLIST_SNAPSHOT_TIMEOUT_MS, 20000);

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
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
          reject(new Error(`Watchlist snapshot load timed out after ${SNAPSHOT_LOAD_TIMEOUT_MS}ms.`));
        }, SNAPSHOT_LOAD_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle);
  }
}

function toMetricRow(row: SnapshotRow): WatchlistMetricRow {
  const decisionInfo = decisionInfoFromRow(row);
  return {
    ticker: String(row.ticker ?? ""),
    decision: decisionInfo.decision,
    decisionReason: decisionInfo.reasonText,
    decisionReasonCode: decisionInfo.reasonCode,
    classification: classificationFromDecision(decisionInfo.decision),
    price: toNumberOrNull(row.price),
    regime: String(row.regime ?? "UNKNOWN"),
    S_UF: toNumber(row.S_UF),
    R_UF: toNumber(row.R_UF),
    barCount: decisionInfo.barCount,
    minBarsForAccumulate: decisionInfo.minBarsForAccumulate,
    stability_score: toNumberOrNull(row.stability_score),
    max_dd: toNumberOrNull(row.max_dd),
  };
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const watchlist = await loadWatchlistSymbols(sessionUser.username);

  // When watchlist is empty, skip snapshot loading and return immediately.
  if (watchlist.symbols.length === 0) {
    return NextResponse.json({
      symbols: [],
      source: watchlist.filePath,
      metrics: [],
      missingSymbols: [],
      snapshotSource: null,
      snapshotFailures: [],
    });
  }

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

  const metricRows: WatchlistMetricRow[] = [];
  const missingSymbols: string[] = [];

  for (const symbol of watchlist.symbols) {
    const row = findTickerRow(snapshotRows, symbol);
    if (!row) {
      missingSymbols.push(symbol);
      continue;
    }
    metricRows.push(toMetricRow(row));
  }

  return NextResponse.json({
    symbols: watchlist.symbols,
    source: watchlist.filePath,
    metrics: metricRows,
    missingSymbols,
    snapshotSource,
    snapshotFailures,
  });
}

export async function POST(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  let body: SaveBody;

  try {
    body = (await request.json()) as SaveBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  if (!Array.isArray(body.symbols)) {
    return NextResponse.json({ error: "Body must include symbols array." }, { status: 400 });
  }

  const symbols = body.symbols.map((value) => String(value));
  const result = await saveWatchlistSymbols(sessionUser.username, symbols);

  return NextResponse.json({
    saved: true,
    symbols: result.symbols,
    source: result.filePath,
  });
}
