import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import { loadOrIngestWatchlistMetric } from "@/lib/watchlist-live-ingestion";

export const runtime = "nodejs";

const execFileAsync = promisify(execFile);

type ChartInterval = "1m" | "5m" | "15m" | "30m" | "60m" | "1d" | "1wk" | "1mo";
type ChartRange = "1d" | "5d" | "1mo" | "3mo" | "6mo" | "ytd" | "1y" | "2y" | "5y" | "max";

type Bar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type Quote = {
  companyName?: string | null;
  exchange?: string | null;
  sector?: string | null;
  industry?: string | null;
  country?: string | null;
  marketCap?: number | null;
  peRatio?: number | null;
  beta?: number | null;
  eps?: number | null;
  avgVolume?: number | null;
  dividendYield?: number | null;
  target1Y?: number | null;
  bid?: number | null;
  ask?: number | null;
};

type ScriptPayload = {
  ticker?: string;
  bars?: Bar[];
  quote?: Quote;
  error?: string;
  source?: string;
  interval?: string;
  range?: string;
};

const ALLOWED_INTERVALS: readonly ChartInterval[] = ["1m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo"];
const ALLOWED_RANGES: readonly ChartRange[] = ["1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y", "max"];

function normalizeTicker(value: string | null): string {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeInterval(value: string | null): ChartInterval {
  const interval = String(value ?? "1d").trim().toLowerCase();
  return ALLOWED_INTERVALS.includes(interval as ChartInterval) ? (interval as ChartInterval) : "1d";
}

function normalizeRange(value: string | null): ChartRange {
  const range = String(value ?? "1y").trim().toLowerCase();
  return ALLOWED_RANGES.includes(range as ChartRange) ? (range as ChartRange) : "1y";
}

function clampDays(value: unknown, fallback: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  const whole = Math.floor(n);
  if (whole < 1) return 1;
  if (whole > 10000) return 10000;
  return whole;
}

function daysForRange(range: ChartRange): number {
  if (range === "1d") return 1;
  if (range === "5d") return 5;
  if (range === "1mo") return 31;
  if (range === "3mo") return 92;
  if (range === "6mo") return 183;
  if (range === "ytd") return 366;
  if (range === "1y") return 366;
  if (range === "2y") return 732;
  if (range === "5y") return 1830;
  return 7300;
}

function toNum(value: number | undefined): number {
  return Number.isFinite(value) ? Number(value) : 0;
}

function summarize(bars: Bar[]) {
  if (bars.length === 0) return null;

  const latest = bars[bars.length - 1];
  const prev = bars.length > 1 ? bars[bars.length - 2] : latest;

  let high52 = Number.NEGATIVE_INFINITY;
  let low52 = Number.POSITIVE_INFINITY;

  for (const bar of bars) {
    const h = toNum(bar.high);
    const l = toNum(bar.low);
    if (h > high52) high52 = h;
    if (l < low52) low52 = l;
  }

  const change = toNum(latest.close) - toNum(prev.close);
  const changePct = toNum(prev.close) === 0 ? 0 : (change / toNum(prev.close)) * 100;

  return {
    open: toNum(latest.open),
    high: toNum(latest.high),
    low: toNum(latest.low),
    prevClose: toNum(prev.close),
    close: toNum(latest.close),
    change,
    changePct,
    high52: Number.isFinite(high52) ? high52 : 0,
    low52: Number.isFinite(low52) ? low52 : 0,
  };
}

function parseScriptPayload(text: string): ScriptPayload | null {
  try {
    return JSON.parse(text) as ScriptPayload;
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const ticker = normalizeTicker(searchParams.get("ticker"));
  const interval = normalizeInterval(searchParams.get("interval"));
  const range = normalizeRange(searchParams.get("range"));
  const days = clampDays(searchParams.get("days"), daysForRange(range));
  const quoteOnly = ["1", "true", "yes", "on"].includes(String(searchParams.get("quoteOnly") ?? "").trim().toLowerCase());

  if (!ticker) {
    return NextResponse.json({ error: "Ticker is required." }, { status: 400 });
  }

  let ufMetric: any = null;
  const scriptPath = path.resolve(process.cwd(), "scripts", "get_history_json.py");

  try {
    ufMetric = await loadOrIngestWatchlistMetric(ticker);
    const result = await execFileAsync(
      "python3",
      [
        scriptPath,
        "--ticker",
        ticker,
        "--days",
        String(days),
        "--interval",
        interval,
        "--range",
        range,
        ...(quoteOnly ? ["--quote-only"] : []),
      ],
      {
        timeout: 25_000,
        maxBuffer: 10 * 1024 * 1024,
      },
    );

    const parsed = parseScriptPayload(result.stdout);
    if (!parsed) {
      return NextResponse.json({
        ticker,
        bars: [],
        summary: null,
        quote: {},
        interval,
        range,
        ufMetric,
        note: "Chart parser fallback in use.",
      });
    }

    const bars = Array.isArray(parsed.bars) ? parsed.bars : [];
    return NextResponse.json({
      ticker,
      bars,
      summary: summarize(bars),
      quote: parsed.quote ?? {},
      interval: parsed.interval ?? interval,
      range: parsed.range ?? range,
      ufMetric,
      note: parsed.error ? `Chart data temporarily unavailable: ${parsed.error}` : null,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "History chart request failed.";
    return NextResponse.json({
      ticker,
      bars: [],
      summary: null,
      quote: {},
      interval,
      range,
      ufMetric,
      note: `Chart data temporarily unavailable: ${message}`,
    });
  }
}
