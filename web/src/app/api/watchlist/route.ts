import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import {
  classificationFromDecision,
  decisionInfoFromRow,
  findTickerRow,
  type SnapshotRow,
} from "@/lib/uf-snapshot";
import {
  loadRuntimeQuoteCacheFromPostgres,
  loadRuntimeSnapshotRowsFromPostgres,
} from "@/lib/runtime-postgres";
import { quoteCachePriceFromRow } from "@/lib/screener-quote-cache";
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
  changePct: number | null;
  regime: string;
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
  stability_score: number | null;
  max_dd: number | null;
};

type WatchlistResponse = {
  symbols: string[];
  source: string | null;
  metrics: WatchlistMetricRow[];
  missingSymbols: string[];
  data_source?: "postgres";
  snapshotSource?: string | null;
  snapshotFailures?: Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>["failures"];
  quoteSource?: string | null;
  quoteFailures?: Awaited<ReturnType<typeof loadRuntimeQuoteCacheFromPostgres>>["failures"];
  error?: string;
};

type SnapshotLoadResult = Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>;
type QuoteLoadResult = Awaited<ReturnType<typeof loadRuntimeQuoteCacheFromPostgres>>;
type SnapshotMetricCompatRow = SnapshotRow & {
  s_uf?: unknown;
  r_uf?: unknown;
  barCount?: unknown;
  assetType?: unknown;
  stabilityScore?: unknown;
  maxDrawdown?: unknown;
};

function normalizeTicker(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeSymbols(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const out: string[] = [];

  for (const item of value) {
    const ticker = normalizeTicker(item);
    if (!ticker || seen.has(ticker)) continue;
    seen.add(ticker);
    out.push(ticker);
  }

  return out;
}

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function normalizeRuntimeSnapshotRow(row: SnapshotRow | null | undefined): SnapshotRow | null {
  if (!row) return null;

  const source = row as SnapshotMetricCompatRow;
  const normalized: SnapshotRow = { ...source };

  if (normalized.S_UF === undefined && source.s_uf !== undefined && source.s_uf !== null) {
    normalized.S_UF = source.s_uf as number | string;
  }
  if (normalized.R_UF === undefined && source.r_uf !== undefined && source.r_uf !== null) {
    normalized.R_UF = source.r_uf as number | string;
  }
  if (normalized.bar_count === undefined && source.barCount !== undefined && source.barCount !== null) {
    normalized.bar_count = source.barCount as number | string;
  }
  if (normalized.asset_type === undefined && source.assetType !== undefined && source.assetType !== null) {
    normalized.asset_type = String(source.assetType);
  }
  if (normalized.stability_score === undefined && source.stabilityScore !== undefined && source.stabilityScore !== null) {
    normalized.stability_score = source.stabilityScore as number | string;
  }
  if (normalized.max_dd === undefined && source.maxDrawdown !== undefined && source.maxDrawdown !== null) {
    normalized.max_dd = source.maxDrawdown as number | string;
  }

  return normalized;
}

function normalizeRuntimeSnapshotRows(rows: SnapshotRow[]): SnapshotRow[] {
  const normalized: SnapshotRow[] = [];

  for (const row of rows) {
    const next = normalizeRuntimeSnapshotRow(row);
    if (!next) continue;
    normalized.push(next);
  }

  return normalized;
}

function summarizeFailures(
  failures: Array<{ path: string; reason: string }>,
  fallback: string,
): string {
  if (failures.length === 0) return fallback;
  return failures
    .map((failure) => `${failure.path}: ${failure.reason}`)
    .join(" | ");
}

function buildMetricRow(
  row: SnapshotRow,
  quoteLoad: QuoteLoadResult,
): WatchlistMetricRow {
  const ticker = normalizeTicker(row.ticker);
  const decisionInfo = decisionInfoFromRow(row);
  const quoteRow = quoteLoad.quotes[ticker] ?? null;

  return {
    ticker,
    decision: decisionInfo.decision,
    decisionReason: decisionInfo.reasonText,
    decisionReasonCode: decisionInfo.reasonCode,
    classification: classificationFromDecision(decisionInfo.decision),
    price: quoteCachePriceFromRow(quoteRow) ?? toNumberOrNull(row.price),
    changePct: quoteRow ? toNumberOrNull(quoteRow.changePct) : null,
    regime: String(row.regime ?? "").trim() || "UNKNOWN",
    S_UF: toNumber(row.S_UF),
    R_UF: toNumber(row.R_UF),
    barCount: Math.max(0, Math.trunc(toNumber(row.bar_count ?? decisionInfo.barCount))),
    minBarsForAccumulate: Math.max(0, Math.trunc(decisionInfo.minBarsForAccumulate)),
    stability_score: toNumberOrNull(row.stability_score),
    max_dd: toNumberOrNull(row.max_dd),
  };
}

function buildWatchlistPayload(
  symbols: string[],
  snapshotRows: SnapshotRow[],
  quoteLoad: QuoteLoadResult,
): Pick<WatchlistResponse, "metrics" | "missingSymbols"> {
  const metrics: WatchlistMetricRow[] = [];
  const missingSymbols: string[] = [];

  for (const ticker of symbols) {
    const row = findTickerRow(snapshotRows, ticker);
    if (!row) {
      missingSymbols.push(ticker);
      continue;
    }
    metrics.push(buildMetricRow(row, quoteLoad));
  }

  return {
    metrics,
    missingSymbols,
  };
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const watchlist = await loadWatchlistSymbols(sessionUser.username);
  if (watchlist.symbols.length === 0) {
    return NextResponse.json({
      symbols: [],
      source: watchlist.filePath,
      metrics: [],
      missingSymbols: [],
    } satisfies WatchlistResponse);
  }

  try {
    const [snapshotLoad, quoteLoad] = await Promise.all([
      loadRuntimeSnapshotRowsFromPostgres(),
      loadRuntimeQuoteCacheFromPostgres(),
    ]);
    const snapshotRows = normalizeRuntimeSnapshotRows(snapshotLoad.rows);

    if (!snapshotLoad.sourcePath || snapshotRows.length === 0) {
      return NextResponse.json(
        {
          error: summarizeFailures(
            snapshotLoad.failures,
            "Watchlist unavailable because runtime Postgres snapshot is unavailable or empty.",
          ),
          symbols: watchlist.symbols,
          source: watchlist.filePath,
          metrics: [],
          missingSymbols: watchlist.symbols,
          data_source: "postgres",
          snapshotSource: snapshotLoad.sourcePath,
          snapshotFailures: snapshotLoad.failures,
          quoteSource: quoteLoad.sourcePath,
          quoteFailures: quoteLoad.failures,
        } satisfies WatchlistResponse,
        { status: 503 },
      );
    }

    const payload = buildWatchlistPayload(watchlist.symbols, snapshotRows, quoteLoad);
    return NextResponse.json({
      symbols: watchlist.symbols,
      source: watchlist.filePath,
      metrics: payload.metrics,
      missingSymbols: payload.missingSymbols,
      data_source: "postgres",
      snapshotSource: snapshotLoad.sourcePath,
      snapshotFailures: snapshotLoad.failures,
      quoteSource: quoteLoad.sourcePath,
      quoteFailures: quoteLoad.failures,
    } satisfies WatchlistResponse);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown watchlist runtime load failure.";
    return NextResponse.json(
      {
        error: message,
        symbols: watchlist.symbols,
        source: watchlist.filePath,
        metrics: [],
        missingSymbols: watchlist.symbols,
      } satisfies WatchlistResponse,
      { status: 500 },
    );
  }
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

  const incomingSymbols = normalizeSymbols(body.symbols);

  try {
    const saved = await saveWatchlistSymbols(sessionUser.username, incomingSymbols);

    return NextResponse.json({
      symbols: saved.symbols,
      source: saved.filePath,
      metrics: [],
      missingSymbols: [],
    } satisfies WatchlistResponse);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown watchlist save failure.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
