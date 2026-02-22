import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

import { NextResponse } from "next/server";
import {
  classificationFromDecision,
  decisionInfoFromRow,
  findTickerRow,
  loadSnapshotRows,
  type SnapshotRow,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";

export const runtime = "nodejs";

const execFileAsync = promisify(execFile);

type Bar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type Quote = {
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
};

type UfMetric = {
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

function toNum(value: number | undefined): number {
  return Number.isFinite(value) ? Number(value) : 0;
}

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function toUfMetric(row: SnapshotRow): UfMetric {
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

function summarize(bars: Bar[]) {
  if (bars.length === 0) {
    return null;
  }

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
    const parsed = JSON.parse(text) as ScriptPayload;
    return parsed;
  } catch {
    return null;
  }
}

function isNoChartDataError(message: string | undefined): boolean {
  if (!message) return false;
  return message.toLowerCase().includes("no chart data available");
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const tickerInput = (searchParams.get("ticker") ?? "").trim();
  const days = Number(searchParams.get("days") ?? "365");

  if (!tickerInput) {
    return NextResponse.json({ error: "Ticker is required." }, { status: 400 });
  }

  const snapshot = await loadSnapshotRows();
  const ufRowForInput = findTickerRow(snapshot.rows, tickerInput);
  const ticker = String(ufRowForInput?.ticker ?? tickerInput).trim();

  const scriptPath = path.resolve(process.cwd(), "scripts", "get_history_json.py");

  try {
    let stdout = "";
    let stderr = "";

    try {
      const result = await execFileAsync("python3", [scriptPath, "--ticker", ticker, "--days", String(days)], {
        timeout: 25000,
        maxBuffer: 10 * 1024 * 1024,
      });
      stdout = result.stdout;
      stderr = result.stderr;
    } catch (error) {
      const execError = error as Error & { stdout?: string; stderr?: string };
      stdout = typeof execError.stdout === "string" ? execError.stdout : "";
      stderr = typeof execError.stderr === "string" ? execError.stderr : "";

      if (!stdout.trim()) {
        const message = execError.message || "History chart request failed.";
        return NextResponse.json({ error: message }, { status: 500 });
      }
    }

    if (stderr && stderr.trim() && !stdout.trim()) {
      return NextResponse.json({ error: stderr.trim() }, { status: 500 });
    }

    const parsed = parseScriptPayload(stdout);
    if (!parsed) {
      return NextResponse.json({ error: "Chart script returned invalid JSON." }, { status: 500 });
    }

    const bars = Array.isArray(parsed.bars) ? parsed.bars : [];
    const ufRow = ufRowForInput ?? findTickerRow(snapshot.rows, ticker);
    const chartNotice = parsed.error && isNoChartDataError(parsed.error) ? parsed.error : null;

    if (parsed.error && !chartNotice) {
      return NextResponse.json({ error: parsed.error }, { status: 500 });
    }

    return NextResponse.json({
      ticker,
      bars,
      summary: summarize(bars),
      quote: parsed.quote ?? {},
      ufMetric: ufRow ? toUfMetric(ufRow) : null,
      note: chartNotice,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "History chart request failed.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
