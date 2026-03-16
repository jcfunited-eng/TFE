import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

import { NextResponse } from "next/server";
import {
  findTickerRow,
  type SnapshotRow,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { loadLivePriceMap } from "@/lib/live-price";
import { loadCanonicalPublicationState, publicationContractFields } from "@/lib/publication-state";
import { loadPublishedDecisionMapForRows, type PublishedDecisionRecord } from "@/lib/published-decision";
import {
  loadRuntimeQuoteCacheFromPostgres,
  loadRuntimeSnapshotRowsFromPostgres,
} from "@/lib/runtime-postgres";
import { quoteCachePriceFromRow, type ScreenerQuoteCacheRow } from "@/lib/screener-quote-cache";

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

type NewsItem = {
  title: string;
  publisher: string;
  link: string;
  publishedAt: number | null;
  relatedTickers: string[];
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

type SnapshotLoadResult = Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>;
type QuoteLoadResult = Awaited<ReturnType<typeof loadRuntimeQuoteCacheFromPostgres>>;

const SNAPSHOT_LOAD_TIMEOUT_MS = normalizeTimeoutMs(process.env.TFE_WATCHLIST_CHART_SNAPSHOT_TIMEOUT_MS, 20000);
const QUOTE_LOAD_TIMEOUT_MS = normalizeTimeoutMs(process.env.TFE_WATCHLIST_CHART_QUOTE_TIMEOUT_MS, 20000);
const NEWS_MAX_ITEMS = 24;
const NEWS_FALLBACK_MAX_ITEMS = 12;

const ALLOWED_INTERVALS: readonly ChartInterval[] = ["1m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo"];
const ALLOWED_RANGES: readonly ChartRange[] = ["1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y", "max"];

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

function normalizeTimeoutMs(value: unknown, fallbackMs: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallbackMs;

  const whole = Math.floor(n);
  if (whole < 1000) return 1000;
  if (whole > 45000) return 45000;
  return whole;
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

async function loadSnapshotRowsWithTimeout(): Promise<SnapshotLoadResult> {
  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  try {
    return await Promise.race([
      loadRuntimeSnapshotRowsFromPostgres(),
      new Promise<SnapshotLoadResult>((_, reject) => {
        timeoutHandle = setTimeout(() => {
          reject(new Error(`Watchlist chart Postgres snapshot load timed out after ${SNAPSHOT_LOAD_TIMEOUT_MS}ms.`));
        }, SNAPSHOT_LOAD_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle);
  }
}

async function loadQuoteRowsWithTimeout(): Promise<QuoteLoadResult> {
  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  try {
    return await Promise.race([
      loadRuntimeQuoteCacheFromPostgres(),
      new Promise<QuoteLoadResult>((_, reject) => {
        timeoutHandle = setTimeout(() => {
          reject(new Error(`Watchlist chart Postgres quote load timed out after ${QUOTE_LOAD_TIMEOUT_MS}ms.`));
        }, QUOTE_LOAD_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle);
  }
}

function toUfMetric(
  row: SnapshotRow,
  livePrice: number | null,
  quoteCachePrice: number | null,
  published: PublishedDecisionRecord,
): UfMetric {
  const snapshotPrice = toNumberOrNull(row.price);

  return {
    ticker: String(row.ticker ?? ""),
    decision: published.decision,
    decisionReason: published.decisionReason,
    decisionReasonCode: published.decisionReasonCode,
    classification: published.classification,
    price: livePrice ?? quoteCachePrice ?? snapshotPrice,
    regime: String(row.regime ?? "UNKNOWN"),
    S_UF: toNumber(row.S_UF),
    R_UF: toNumber(row.R_UF),
    barCount: published.barCount,
    minBarsForAccumulate: published.minBarsForAccumulate,
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

function cachedQuoteRowForTicker(quotes: Record<string, ScreenerQuoteCacheRow>, ticker: string): ScreenerQuoteCacheRow | null {
  const key = String(ticker ?? "").trim().toUpperCase();
  const row = quotes[key];
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  return row;
}

function mergeQuoteWithFallback(primary: Quote | undefined, fallback: Quote): Quote {
  const merged: Record<string, unknown> = { ...(fallback as Record<string, unknown>) };
  const source = primary && typeof primary === "object" ? (primary as Record<string, unknown>) : {};

  for (const [key, value] of Object.entries(source)) {
    if (value === null || value === undefined) {
      if (!(key in merged)) merged[key] = value;
      continue;
    }
    merged[key] = value;
  }

  return merged as Quote;
}

function normalizeNewsUrl(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text) return "";
  try {
    const parsed = new URL(text);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return "";
    return parsed.toString();
  } catch {
    return "";
  }
}

function textOrEmpty(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function decodeHtmlEntities(value: string): string {
  return value
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'");
}

function stripHtmlTags(value: string): string {
  return decodeHtmlEntities(value).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function xmlTagText(block: string, tag: string): string {
  const regex = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, "i");
  const match = block.match(regex);
  return match?.[1] ? stripHtmlTags(match[1]) : "";
}

function xmlSourceText(block: string): string {
  const sourceTag = block.match(/<source\b[^>]*>([\s\S]*?)<\/source>/i);
  if (sourceTag?.[1]) return stripHtmlTags(sourceTag[1]);

  const title = xmlTagText(block, "title");
  const sep = title.lastIndexOf(" - ");
  if (sep > 0) return title.slice(sep + 3).trim();
  return "";
}

function normalizeNewsItems(items: NewsItem[], ticker: string): NewsItem[] {
  const keyTicker = String(ticker ?? "").trim().toUpperCase();
  const dedupe = new Map<string, NewsItem>();

  for (const item of items) {
    const title = textOrEmpty(item.title);
    const publisher = textOrEmpty(item.publisher);
    const link = normalizeNewsUrl(item.link);
    if (!title || !link) continue;

    const relatedTickers = Array.isArray(item.relatedTickers)
      ? item.relatedTickers.map((value) => String(value).trim().toUpperCase()).filter(Boolean)
      : [];

    if (keyTicker && !relatedTickers.includes(keyTicker)) {
      relatedTickers.unshift(keyTicker);
    }

    const normalized: NewsItem = {
      title,
      publisher,
      link,
      publishedAt: Number.isFinite(Number(item.publishedAt)) ? Number(item.publishedAt) : null,
      relatedTickers,
    };

    const dedupeKey = `${normalized.link}|${normalized.title.toUpperCase()}`;
    const existing = dedupe.get(dedupeKey);
    if (!existing) {
      dedupe.set(dedupeKey, normalized);
      continue;
    }

    const existingTs = existing.publishedAt ?? 0;
    const incomingTs = normalized.publishedAt ?? 0;
    if (incomingTs > existingTs) dedupe.set(dedupeKey, normalized);
  }

  return Array.from(dedupe.values()).sort((a, b) => (b.publishedAt ?? 0) - (a.publishedAt ?? 0));
}

function parseGoogleNewsRss(xml: string, ticker: string): NewsItem[] {
  if (!xml || !xml.includes("<item")) return [];

  const items = xml.match(/<item\b[\s\S]*?<\/item>/gi) ?? [];
  const out: NewsItem[] = [];

  for (const item of items) {
    const title = xmlTagText(item, "title");
    const link = normalizeNewsUrl(xmlTagText(item, "link"));
    const publisher = xmlSourceText(item);
    const pubDateText = xmlTagText(item, "pubDate");
    const ts = Date.parse(pubDateText);
    const publishedAt = Number.isFinite(ts) ? Math.floor(ts / 1000) : null;
    if (!title || !link) continue;

    out.push({
      title,
      link,
      publisher,
      publishedAt,
      relatedTickers: [String(ticker ?? "").trim().toUpperCase()].filter(Boolean),
    });
  }

  return normalizeNewsItems(out, ticker);
}

async function fetchYahooNews(ticker: string): Promise<NewsItem[]> {
  const query = encodeURIComponent(ticker);
  const url =
    `https://query1.finance.yahoo.com/v1/finance/search?q=${query}` +
    "&quotesCount=0&newsCount=12&enableFuzzyQuery=false&recommendedCount=0";

  try {
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      headers: {
        "User-Agent": "Mozilla/5.0",
        Accept: "application/json",
      },
    });

    if (!response.ok) return [];

    const payload = (await response.json()) as {
      news?: Array<Record<string, unknown>>;
    };

    const source = Array.isArray(payload.news) ? payload.news : [];
    const out: NewsItem[] = [];

    for (const item of source) {
      const title = textOrEmpty(item.title);
      const publisher = textOrEmpty(item.publisher);
      const link = normalizeNewsUrl(item.link ?? (item.canonicalUrl as { url?: string } | undefined)?.url);
      const publishedAtRaw = Number(item.providerPublishTime);
      const publishedAt = Number.isFinite(publishedAtRaw) ? Math.floor(publishedAtRaw) : null;
      const relatedTickers = Array.isArray(item.relatedTickers)
        ? item.relatedTickers.map((value) => String(value).trim().toUpperCase()).filter(Boolean)
        : [];

      if (!title || !link) continue;

      out.push({
        title,
        publisher,
        link,
        publishedAt,
        relatedTickers,
      });
    }

    return normalizeNewsItems(out, ticker).slice(0, NEWS_FALLBACK_MAX_ITEMS);
  } catch {
    return [];
  }
}

async function fetchGoogleNewsFeed(query: string, ticker: string): Promise<NewsItem[]> {
  const trimmed = query.trim();
  if (!trimmed) return [];

  const url =
    `https://news.google.com/rss/search?q=${encodeURIComponent(trimmed)}` +
    "&hl=en-US&gl=US&ceid=US:en";

  try {
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      headers: {
        "User-Agent": "Mozilla/5.0",
        Accept: "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
      },
    });
    if (!response.ok) return [];
    const xml = await response.text();
    return parseGoogleNewsRss(xml, ticker);
  } catch {
    return [];
  }
}

async function fetchMarketNews(ticker: string, quote: Quote): Promise<NewsItem[]> {
  const cleanTicker = String(ticker ?? "").trim().toUpperCase();
  const company = textOrEmpty(quote.companyName);
  const exchange = textOrEmpty(quote.exchange);

  const queryPrimary = company
    ? `${cleanTicker} ${company} stock ${exchange}`.trim()
    : `${cleanTicker} stock ${exchange}`.trim();
  const queryFallback = `${cleanTicker} stock`.trim();

  const [googlePrimary, googleFallback, yahoo] = await Promise.all([
    fetchGoogleNewsFeed(queryPrimary, cleanTicker),
    fetchGoogleNewsFeed(queryFallback, cleanTicker),
    fetchYahooNews(cleanTicker),
  ]);

  const merged = normalizeNewsItems([...googlePrimary, ...googleFallback, ...yahoo], cleanTicker);
  return merged.slice(0, NEWS_MAX_ITEMS);
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const tickerInput = (searchParams.get("ticker") ?? "").trim();
  const interval = normalizeInterval(searchParams.get("interval"));
  const range = normalizeRange(searchParams.get("range"));
  const days = clampDays(searchParams.get("days"), daysForRange(range));
  const quoteOnly = ["1", "true", "yes", "on"].includes(String(searchParams.get("quoteOnly") ?? "").trim().toLowerCase());
  const includeNews = ["1", "true", "yes", "on"].includes(String(searchParams.get("includeNews") ?? "").trim().toLowerCase());
  const includeMiniBars = ["1", "true", "yes", "on"].includes(String(searchParams.get("includeMiniBars") ?? "").trim().toLowerCase());

  if (!tickerInput) {
    return NextResponse.json({ error: "Ticker is required." }, { status: 400 });
  }

  let snapshotRows: SnapshotLoadResult["rows"] = [];
  let snapshotFailures: SnapshotLoadResult["failures"] = [];
  let snapshotRunId: string | null = null;
  let snapshotGeneratedAtUtc: string | null = null;
  let quoteFailures: QuoteLoadResult["failures"] = [];
  let quoteRunId: string | null = null;
  let quoteGeneratedAtUtc: string | null = null;
  let quoteRows: Record<string, ScreenerQuoteCacheRow> = {};
  let ufRowForInput: SnapshotRow | null = null;
  let publicationFields = publicationContractFields(
    await loadCanonicalPublicationState({
      snapshot: { available: false, runId: null, generatedAtUtc: null },
      quote: { available: false, runId: null },
    }),
  );

  try {
    const runtimeQuotes = await loadQuoteRowsWithTimeout();
    quoteRows = runtimeQuotes.quotes;
    quoteFailures = runtimeQuotes.failures;
    quoteRunId = runtimeQuotes.runId;
    quoteGeneratedAtUtc = runtimeQuotes.generatedAtUtc;
  } catch (error) {
    const reason = error instanceof Error ? error.message : "Unknown Postgres quote load failure.";
    quoteFailures = [{ path: "runtime_symbols", reason }];
  }

  try {
    const snapshot = await loadSnapshotRowsWithTimeout();
    snapshotRows = snapshot.rows;
    snapshotFailures = snapshot.failures;
    snapshotRunId = snapshot.runId;
    snapshotGeneratedAtUtc = snapshot.generatedAtUtc;
  } catch (error) {
    const reason = error instanceof Error ? error.message : "Unknown Postgres snapshot load failure.";
    snapshotFailures = [{ path: "runtime_decisions_latest", reason }];
  }

  const publicationState = await loadCanonicalPublicationState({
    snapshot: {
      available: snapshotRows.length > 0,
      runId: snapshotRunId,
      generatedAtUtc: snapshotGeneratedAtUtc,
    },
    quote: {
      available: Object.keys(quoteRows).length > 0,
      runId: quoteRunId,
    },
  });
  publicationFields = publicationContractFields(publicationState);

  if (Object.keys(quoteRows).length === 0) {
    return NextResponse.json(
      {
        error: "Chart API unavailable because runtime Postgres quote rows are missing.",
        snapshotFailures,
        quoteFailures,
        ...publicationFields,
      },
      { status: 503 },
    );
  }

  if (snapshotRows.length === 0) {
    return NextResponse.json(
      {
        error: "Chart API unavailable because runtime Postgres snapshot rows are missing.",
        snapshotFailures,
        quoteFailures,
        ...publicationFields,
      },
      { status: 503 },
    );
  }

  if (publicationState.servingState === "blocked") {
    return NextResponse.json(
      {
        error: "Chart API unavailable because canonical publication state blocked investor serving.",
        blocked: true,
        status: "blocked",
        snapshotFailures,
        quoteFailures,
        ...publicationFields,
      },
      { status: 503 },
    );
  }

  ufRowForInput = findTickerRow(snapshotRows, tickerInput);
  const ticker = String(ufRowForInput?.ticker ?? tickerInput).trim().toUpperCase();
  const publishedDecisionLoad = await loadPublishedDecisionMapForRows(
    publicationState.servingRunId ?? publicationState.runId,
    snapshotRows,
    [ticker],
  );
  const publishedDecision = publishedDecisionLoad.rows[ticker];

  if (!publishedDecisionLoad.ok || !publishedDecision || !ufRowForInput) {
    return NextResponse.json(
      {
        error: ufRowForInput
          ? "Chart API unavailable because persisted published decision provenance is missing or invalid for this ticker."
          : `Chart API unavailable because ticker '${ticker}' is not present in the active published snapshot.`,
        blocked: true,
        status: "blocked",
        snapshotFailures,
        quoteFailures,
        provenance: {
          sourcePath: publishedDecisionLoad.sourcePath,
          failureCount: publishedDecisionLoad.failures.length,
          rows_required: publishedDecisionLoad.rowsRequired,
          rows_valid: publishedDecisionLoad.rowsValid,
          missingTickers: publishedDecisionLoad.missingTickers,
          invalidTickers: publishedDecisionLoad.invalidTickers,
        },
        ...publicationFields,
      },
      { status: 503 },
    );
  }

  const fallbackQuoteRow = cachedQuoteRowForTicker(quoteRows, ticker);
  const fallbackQuote = fallbackQuoteRow ? (fallbackQuoteRow as Quote) : {};
  const fallbackQuotePrice = quoteCachePriceFromRow(fallbackQuoteRow);
  const fallbackUfMetric = toUfMetric(ufRowForInput, null, fallbackQuotePrice, publishedDecision);
  const responseRunId = snapshotRunId ?? quoteRunId;
  const responseGeneratedAtUtc = snapshotGeneratedAtUtc ?? quoteGeneratedAtUtc;

  if (quoteOnly && includeNews) {
    const news = await fetchMarketNews(ticker, fallbackQuote);
    return NextResponse.json({
      ticker,
      bars: [],
      summary: null,
      quote: fallbackQuote,
      news,
      interval,
      range,
      ufMetric: fallbackUfMetric,
      note: news.length === 0 ? "No news feed items are currently available for this ticker." : null,
      snapshotFailures,
      quoteFailures,
      data_source: "postgres",
      ...publicationFields,
      runtime_run_id: responseRunId,
      runtime_generated_at_utc: responseGeneratedAtUtc,
    });
  }

  const scriptPath = path.resolve(process.cwd(), "scripts", "get_history_json.py");

  try {
    let stdout = "";
    let stderr = "";

    try {
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
          ...(quoteOnly && !includeMiniBars ? ["--quote-only"] : []),
        ],
        {
          timeout: 25000,
          maxBuffer: 10 * 1024 * 1024,
        },
      );
      stdout = result.stdout;
      stderr = result.stderr;
    } catch (error) {
      const execError = error as Error & { stdout?: string; stderr?: string };
      stdout = typeof execError.stdout === "string" ? execError.stdout : "";
      stderr = typeof execError.stderr === "string" ? execError.stderr : "";

      if (!stdout.trim()) {
        const news = includeNews ? await fetchMarketNews(ticker, fallbackQuote) : [];
        const message = execError.message || "History chart request failed.";
        return NextResponse.json({
          ticker,
          bars: [],
          summary: null,
          quote: fallbackQuote,
          news,
          interval,
          range,
          ufMetric: fallbackUfMetric,
          note: `Chart data temporarily unavailable: ${message}`,
          snapshotFailures,
          quoteFailures,
          data_source: "postgres",
          ...publicationFields,
          runtime_run_id: responseRunId,
          runtime_generated_at_utc: responseGeneratedAtUtc,
        });
      }
    }

    if (stderr && stderr.trim() && !stdout.trim()) {
      const news = includeNews ? await fetchMarketNews(ticker, fallbackQuote) : [];
      return NextResponse.json({
        ticker,
        bars: [],
        summary: null,
        quote: fallbackQuote,
        news,
        interval,
        range,
        ufMetric: fallbackUfMetric,
        note: `Chart data temporarily unavailable: ${stderr.trim()}`,
        snapshotFailures,
        quoteFailures,
        data_source: "postgres",
        ...publicationFields,
        runtime_run_id: responseRunId,
        runtime_generated_at_utc: responseGeneratedAtUtc,
      });
    }

    const parsed = parseScriptPayload(stdout);
    if (!parsed) {
      const news = includeNews ? await fetchMarketNews(ticker, fallbackQuote) : [];
      return NextResponse.json({
        ticker,
        bars: [],
        summary: null,
        quote: fallbackQuote,
        news,
        interval,
        range,
        ufMetric: fallbackUfMetric,
        note: "Chart parser fallback in use.",
        snapshotFailures,
        quoteFailures,
        data_source: "postgres",
        ...publicationFields,
        runtime_run_id: responseRunId,
        runtime_generated_at_utc: responseGeneratedAtUtc,
      });
    }

    const bars = Array.isArray(parsed.bars) ? parsed.bars : [];
    const ufRow = ufRowForInput;
    const chartNotice = parsed.error && isNoChartDataError(parsed.error) ? parsed.error : null;
    const softNotice = parsed.error && !chartNotice ? parsed.error : null;
    const mergedQuote = mergeQuoteWithFallback(parsed.quote ?? {}, fallbackQuote);

    let livePrice: number | null = null;
    let ufQuoteCachePrice = fallbackQuotePrice;
    if (!quoteOnly && ufRow) {
      const ufTicker = String(ufRow.ticker ?? ticker).trim().toUpperCase();
      if (ufTicker !== ticker) {
        ufQuoteCachePrice = quoteCachePriceFromRow(cachedQuoteRowForTicker(quoteRows, ufTicker));
      }
      const livePriceMap = await loadLivePriceMap([
        {
          ticker: ufTicker,
          assetType: ufRow.asset_type,
        },
      ]);
      livePrice = livePriceMap.get(ufTicker)?.price ?? null;
    }

    const news = includeNews ? await fetchMarketNews(ticker, mergedQuote) : [];

    return NextResponse.json({
      ticker,
      bars,
      summary: summarize(bars),
      quote: mergedQuote,
      news,
      interval: parsed.interval ?? interval,
      range: parsed.range ?? range,
      ufMetric: ufRow ? toUfMetric(ufRow, livePrice, ufQuoteCachePrice, publishedDecision) : null,
      note: chartNotice ?? softNotice ?? null,
      snapshotFailures,
      quoteFailures,
      data_source: "postgres",
      ...publicationFields,
      runtime_run_id: responseRunId,
      runtime_generated_at_utc: responseGeneratedAtUtc,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "History chart request failed.";
    const news = includeNews ? await fetchMarketNews(ticker, fallbackQuote) : [];
    return NextResponse.json({
      ticker,
      bars: [],
      summary: null,
      quote: fallbackQuote,
      news,
      interval,
      range,
      ufMetric: fallbackUfMetric,
      note: `Chart fallback in use: ${message}`,
      snapshotFailures,
      quoteFailures,
      data_source: "postgres",
      ...publicationFields,
      runtime_run_id: responseRunId,
      runtime_generated_at_utc: responseGeneratedAtUtc,
    });
  }
}
