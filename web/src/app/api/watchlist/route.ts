import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import { loadOrIngestWatchlistMetrics } from "@/lib/watchlist-live-ingestion";
import { loadWatchlistSymbols, saveWatchlistSymbols } from "@/lib/watchlist-store";

export const runtime = "nodejs";

type SaveBody = {
  symbols?: unknown;
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
    });
  }

  try {
    const metrics = await loadOrIngestWatchlistMetrics(watchlist.symbols);
    return NextResponse.json({
      symbols: watchlist.symbols,
      source: watchlist.filePath,
      metrics: metrics.metrics,
      missingSymbols: metrics.missingSymbols,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown watchlist ingestion failure.";
    return NextResponse.json({ error: message }, { status: 500 });
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

  const cleanSymbols = normalizeSymbols(body.symbols);

  try {
    const saved = await saveWatchlistSymbols(sessionUser.username, cleanSymbols);
    return NextResponse.json({
      symbols: saved.symbols,
      source: saved.filePath,
      metrics: [],
      missingSymbols: [],
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown watchlist save failure.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
