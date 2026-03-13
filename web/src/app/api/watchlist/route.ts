import { NextResponse } from "next/server";

import {
  findTickerRow,
  type SnapshotRow,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { loadLivePriceMap } from "@/lib/live-price";
import { loadCanonicalPublicationState, publicationContractFields } from "@/lib/publication-state";
import { loadPublishedDecisionMapForRows, type PublishedDecisionRecord } from "@/lib/published-decision";
import { quoteCachePriceFromRow } from "@/lib/screener-quote-cache";
import { loadWatchlistSymbols, saveWatchlistSymbols } from "@/lib/watchlist-store";
import {
  loadRuntimeQuoteCacheFromPostgres,
  loadRuntimeSnapshotRowsFromPostgres,
} from "@/lib/runtime-postgres";

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

type SnapshotLoadResult = Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>;

const SNAPSHOT_LOAD_TIMEOUT_MS = normalizeTimeoutMs(process.env.TFE_WATCHLIST_SNAPSHOT_TIMEOUT_MS, 20000);

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
          reject(new Error(`Watchlist snapshot load timed out after ${SNAPSHOT_LOAD_TIMEOUT_MS}ms.`));
        }, SNAPSHOT_LOAD_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle);
  }
}

function toMetricRow(
  row: SnapshotRow,
  published: PublishedDecisionRecord,
  livePrice: number | null,
  quoteCachePrice: number | null,
): WatchlistMetricRow {
  const fallbackPrice = toNumberOrNull(row.price);

  return {
    ticker: String(row.ticker ?? ""),
    decision: published.decision,
    decisionReason: published.decisionReason,
    decisionReasonCode: published.decisionReasonCode,
    classification: published.classification,
    price: livePrice ?? quoteCachePrice ?? fallbackPrice,
    regime: String(row.regime ?? "UNKNOWN"),
    S_UF: toNumber(row.S_UF),
    R_UF: toNumber(row.R_UF),
    barCount: published.barCount,
    minBarsForAccumulate: published.minBarsForAccumulate,
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
    const publicationState = await loadCanonicalPublicationState({
      snapshot: { available: false, runId: null, generatedAtUtc: null },
      quote: { available: false, runId: null },
    });
    const payload = {
      ...publicationContractFields(publicationState),
      symbols: [],
      source: watchlist.filePath,
      metrics: [],
      missingSymbols: [],
      snapshotSource: null,
      snapshotFailures: [],
    };
    if (publicationState.servingState === "blocked") {
      return NextResponse.json(
        {
          error: "Watchlist is unavailable. Canonical publication state blocked this response.",
          blocked: true,
          status: "blocked",
          ...payload,
        },
        { status: 503 },
      );
    }
    return NextResponse.json(payload);
  }

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
        error: "Watchlist unavailable because runtime Postgres snapshot is unavailable or empty.",
        source: watchlist.filePath,
        snapshotSource,
        snapshotFailures,
        ...publicationContractFields(publicationState),
      },
      { status: 503 },
    );
  }

  const rowByTicker = new Map<string, SnapshotRow>();
  const missingSymbols: string[] = [];

  for (const symbol of watchlist.symbols) {
    const normalizedTicker = normalizeTicker(symbol);
    const row = findTickerRow(snapshotRows, normalizedTicker);
    if (!row) {
      missingSymbols.push(symbol);
      continue;
    }

    rowByTicker.set(normalizedTicker, row);
  }

  const livePriceMap = await loadLivePriceMap(
    Array.from(rowByTicker.entries()).map(([ticker, row]) => ({
      ticker,
      assetType: row.asset_type,
    })),
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
        error: "Watchlist unavailable because runtime Postgres quote cache is unavailable or empty.",
        source: watchlist.filePath,
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
        error: "Watchlist is unavailable. Canonical publication state blocked this response.",
        blocked: true,
        status: "blocked",
        ...publicationFields,
        source: watchlist.filePath,
        snapshotSource,
        snapshotFailures,
        quoteSource: quoteCache.sourcePath,
        quoteFailures: quoteCache.failures,
      },
      { status: 503 },
    );
  }

  const publishedDecisionLoad = await loadPublishedDecisionMapForRows(publicationState.runId, snapshotRows, watchlist.symbols);
  if (!publishedDecisionLoad.ok) {
    return NextResponse.json(
      {
        error: "Watchlist is unavailable because persisted published decision provenance is missing or invalid.",
        blocked: true,
        status: "blocked",
        ...publicationFields,
        source: watchlist.filePath,
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

  const metricRows: WatchlistMetricRow[] = [];

  for (const symbol of watchlist.symbols) {
    const normalizedTicker = normalizeTicker(symbol);
    const row = rowByTicker.get(normalizedTicker);
    if (!row) continue;
    const published = publishedDecisionLoad.rows[normalizedTicker];
    if (!published) continue;

    const liveQuote = livePriceMap.get(normalizedTicker);
    const quoteCachePrice = quoteCachePriceFromRow(quoteCache.quotes[normalizedTicker]);
    metricRows.push(toMetricRow(row, published, liveQuote?.price ?? null, quoteCachePrice));
  }

  return NextResponse.json({
    ...publicationFields,
    symbols: watchlist.symbols,
    source: watchlist.filePath,
    metrics: metricRows,
    missingSymbols,
    snapshotSource,
    snapshotFailures,
    data_source: "postgres",
    quoteSource: quoteCache.sourcePath,
    quoteFailures: quoteCache.failures,
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
