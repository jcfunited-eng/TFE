import { NextResponse } from "next/server";

import {
  type SnapshotRow,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { loadCanonicalPublicationState, publicationContractFields } from "@/lib/publication-state";
import { loadPublishedDecisionMapForRows, type PublishedDecisionRecord } from "@/lib/published-decision";
import {
  quoteCachePriceFromRow,
  type ScreenerQuoteCacheRow,
} from "@/lib/screener-quote-cache";
import {
  loadRuntimeQuoteCacheFromPostgres,
  loadRuntimeSnapshotRowsFromPostgres,
} from "@/lib/runtime-postgres";
import {
  loadScreenerProfileOverrides,
  type ScreenerProfileOverrideRow,
} from "@/lib/screener-profile-overrides";
import {
  SCREENER_FILTER_FIELDS,
  SCREENER_FILTER_KEYS,
  SCREENER_FILTER_GROUP_LAYOUTS,
  SCREENER_ORDER_OPTIONS,
  SCREENER_SIGNAL_OPTIONS,
} from "@/lib/screener-filter-schema-v111";

export const runtime = "nodejs";

type ScreenerTab = "overview" | "valuation" | "financial" | "ownership" | "performance" | "technical" | "etf";
type Decision = "Accumulate" | "Hold" | "Avoid";
type AssetType = "equities" | "index" | "crypto" | "etf" | "other";
type SortDirection = "asc" | "desc";

type AdvancedFilterState = {
  exchange: string;
  index: string;
  sector: string;
  industry: string;
  country: string;
  marketCap: string;
  dividendYield: string;
  shortFloat: string;
  analystRecom: string;
  optionShort: string;
  earningsDate: string;
  avgVolume: string;
  relVolume: string;
  currentVolume: string;
  trades: string;
  priceBand: string;
  targetPrice: string;
  ipoDate: string;
  sharesOutstanding: string;
  float: string;
  theme: string;
  subTheme: string;
  [key: string]: string;
};

type AdvancedFilterKey = string;

type ScreenerRow = {
  ticker: string;
  assetType: AssetType;
  decision: Decision;
  classification: "BUY" | "HOLD" | "SELL";
  regime: string;
  price: number | null;
  barCount: number;
  minBarsForAccumulate: number;
  stabilityScore: number | null;
  maxDrawdown: number | null;
};

type ScreenerMapCell = {
  sector: string;
  industry: string;
  marketCap: number;
  avgChangePct: number | null;
  tickers: number;
  volume: number;
  leaders: Array<{
    ticker: string;
    price: number | null;
    changePct: number | null;
    marketCap: number | null;
    volume: number | null;
  }>;
};

type ScreenerMapTicker = {
  ticker: string;
  companyName: string | null;
  sector: string;
  industry: string;
  assetType: AssetType;
  quoteType: string | null;
  marketCap: number;
  changePct: number | null;
  perfWeek?: number | null;
  perfMonth?: number | null;
  perfQuarter?: number | null;
  perfHalf?: number | null;
  perfYtd?: number | null;
  perfYear?: number | null;
  price: number | null;
  volume: number;
};

type SortKey = string;

type EasternDateParts = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
};

type ExternalTickerSet = {
  queryKey: string;
  filterToken: string | null;
  signalToken: string | null;
  tickers: Set<string>;
  orderedTickers: string[];
  total: number | null;
  pagesFetched: number;
  sourceBaseUrl: string;
  fetchedAtUtc: string;
};

type ExternalTickerSetCacheEntry = {
  expiresAtMs: number;
  value: ExternalTickerSet | null;
};

type AdvancedExternalFilterContext = {
  countryRegionTickers: Set<string> | null;
  themeTickers: Set<string> | null;
  subThemeTickers: Set<string> | null;
  compositeFilterToken: string | null;
  compositeSignalToken: string | null;
  compositeTickers: Set<string> | null;
  compositeOrderedTickers: string[] | null;
};

const DEFAULT_PAGE_SIZE = 25;
const MAX_PAGE_SIZE = 200;
const DEFAULT_TIMEOUT_MS = 20000;
const DEFAULT_EXTERNAL_FILTER_TIMEOUT_MS = 12000;
const DEFAULT_EXTERNAL_FILTER_TTL_MS = 10 * 60 * 1000;
const DEFAULT_EXTERNAL_FILTER_MAX_PAGES = 600;

const LEGACY_ADVANCED_FILTER_DEFAULTS: AdvancedFilterState = {
  exchange: "",
  index: "",
  sector: "",
  industry: "",
  country: "",
  marketCap: "",
  dividendYield: "",
  shortFloat: "",
  analystRecom: "",
  optionShort: "",
  earningsDate: "",
  avgVolume: "",
  relVolume: "",
  currentVolume: "",
  trades: "",
  priceBand: "",
  targetPrice: "",
  ipoDate: "",
  sharesOutstanding: "",
  float: "",
  theme: "",
  subTheme: "",
};

const ADVANCED_FILTER_DEFAULTS: AdvancedFilterState = {
  ...LEGACY_ADVANCED_FILTER_DEFAULTS,
  ...Object.fromEntries(SCREENER_FILTER_KEYS.map((key) => [key, ""])),
};

const ADVANCED_FILTER_KEYS: AdvancedFilterKey[] = Array.from(
  new Set<string>([...Object.keys(ADVANCED_FILTER_DEFAULTS), ...SCREENER_FILTER_KEYS]),
);

const ADVANCED_FILTER_OPTIONS: Record<string, Array<{ value: string; label: string; eliteOnly: boolean }>> = Object.fromEntries(
  Object.entries(SCREENER_FILTER_FIELDS).map(([key, field]) => [key, field.options]),
);

const AVG_CURR_VOLUME_THRESHOLDS: Record<string, number> = {
  "0": 0,
  "50": 50_000,
  "100": 100_000,
  "200": 200_000,
  "300": 300_000,
  "400": 400_000,
  "500": 500_000,
  "750": 750_000,
  "1000": 1_000_000,
  "2000": 2_000_000,
  "5000": 5_000_000,
  "10000": 10_000_000,
  "20000": 20_000_000,
};

const AVG_VOLUME_RANGE_CODES: Record<string, readonly [number, number]> = {
  "100to500": [100_000, 500_000],
  "100to1000": [100_000, 1_000_000],
  "500to1000": [500_000, 1_000_000],
  "500to10000": [500_000, 10_000_000],
};

const PRICE_RANGE_CODES: Record<string, readonly [number, number]> = {
  "1to5": [1, 5],
  "1to10": [1, 10],
  "1to20": [1, 20],
  "5to10": [5, 10],
  "5to20": [5, 20],
  "5to50": [5, 50],
  "10to20": [10, 20],
  "10to50": [10, 50],
  "20to50": [20, 50],
  "50to100": [50, 100],
};

const CURRENT_VOLUME_DOLLAR_THRESHOLDS: Record<string, number> = {
  "1000": 1_000_000,
  "10000": 10_000_000,
  "100000": 100_000_000,
  "1000000": 1_000_000_000,
};

const COUNTRY_REGION_FILTERS = new Set(["asia", "europe", "latinamerica", "bric", "benelux", "chinahongkong"]);
const EXTERNAL_FILTER_SOURCE_BASE_URL = String(process.env.TFE_SCREENER_FILTER_SOURCE_BASE_URL ?? "https://finviz.com")
  .trim()
  .replace(/\/+$/, "");
const EXTERNAL_FILTER_TIMEOUT_MS = normalizeBoundedInt(
  process.env.TFE_SCREENER_FILTER_SOURCE_TIMEOUT_MS,
  DEFAULT_EXTERNAL_FILTER_TIMEOUT_MS,
  1500,
  60000,
);
const EXTERNAL_FILTER_TTL_MS = normalizeBoundedInt(
  process.env.TFE_SCREENER_FILTER_SOURCE_TTL_MS,
  DEFAULT_EXTERNAL_FILTER_TTL_MS,
  30000,
  24 * 60 * 60 * 1000,
);
const EXTERNAL_FILTER_MAX_PAGES = normalizeBoundedInt(
  process.env.TFE_SCREENER_FILTER_SOURCE_MAX_PAGES,
  DEFAULT_EXTERNAL_FILTER_MAX_PAGES,
  1,
  5000,
);

const EXTERNAL_FILTER_CACHE = new Map<string, ExternalTickerSetCacheEntry>();
const EXTERNAL_FILTER_INFLIGHT = new Map<string, Promise<ExternalTickerSet | null>>();
const EMPTY_TAXONOMY_LABELS = new Set(["", "NONE", "NULL", "N/A", "NA", "UNCLASSIFIED", "UNKNOWN"]);

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function parseQueryNumber(value: string | null): number | null {
  if (value === null) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : null;
}

function parseBooleanQueryFlag(value: string | null): boolean {
  const normalized = String(value ?? "").trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(normalized);
}

function normalizeBoundedInt(value: unknown, fallback: number, min: number, max: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  const whole = Math.floor(n);
  if (whole < min) return min;
  if (whole > max) return max;
  return whole;
}

function normalizePageSize(value: string | null): number {
  const n = Number(value ?? DEFAULT_PAGE_SIZE);
  if (!Number.isFinite(n)) return DEFAULT_PAGE_SIZE;
  const whole = Math.floor(n);
  if (whole < 1) return 1;
  if (whole > MAX_PAGE_SIZE) return MAX_PAGE_SIZE;
  return whole;
}

function normalizePage(value: string | null): number {
  const n = Number(value ?? 1);
  if (!Number.isFinite(n)) return 1;
  const whole = Math.floor(n);
  if (whole < 1) return 1;
  return whole;
}

function normalizeTab(value: string | null): ScreenerTab {
  const raw = String(value ?? "overview").trim().toLowerCase();
  if (raw === "valuation") return "valuation";
  if (raw === "financial") return "financial";
  if (raw === "ownership") return "ownership";
  if (raw === "performance") return "performance";
  if (raw === "technical") return "technical";
  if (raw === "etf") return "etf";
  return "overview";
}

function normalizeSortDirection(value: string | null): SortDirection {
  const raw = String(value ?? "asc").trim().toLowerCase();
  if (raw === "desc") return "desc";
  return "asc";
}

function normalizeSortKey(value: string | null): SortKey {
  const raw = String(value ?? "ticker").trim();
  const allowed = new Set<string>(["ticker", "assetType", "price", "company", "sector", "industry", "country", "marketcap", "change", "volume"]);
  return allowed.has(raw) ? raw : "ticker";
}

function normalizeAssetType(value: unknown): AssetType {
  const raw = String(value ?? "").trim().toLowerCase();
  if (["equity", "equities", "stock", "stocks"].includes(raw)) return "equities";
  if (["index", "indices"].includes(raw)) return "index";
  if (["crypto", "cryptocurrency", "coin", "token"].includes(raw)) return "crypto";
  if (["etf", "fund"].includes(raw)) return "etf";
  return "other";
}

function normalizeTimeoutMs(value: unknown, fallbackMs: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallbackMs;
  const whole = Math.floor(n);
  if (whole < 1000) return 1000;
  if (whole > 45000) return 45000;
  return whole;
}

function toScreenerRow(
  row: SnapshotRow,
  quoteCacheQuotes: Record<string, ScreenerQuoteCacheRow>,
  publishedDecisionMap: Record<string, PublishedDecisionRecord>,
): ScreenerRow | null {
  const ticker = String(row.ticker ?? "").trim().toUpperCase();
  if (!ticker) return null;

  const published = publishedDecisionMap[ticker];
  if (!published) return null;
  const snapshotPrice = toNumberOrNull(row.price);
  const quoteCachePrice = quoteCachePriceFromRow(quoteCacheQuotes[ticker]);

  return {
    ticker,
    assetType: normalizeAssetType(row.asset_type),
    decision: published.decision,
    classification: published.classification,
    regime: String(row.regime ?? "UNKNOWN"),
    price: quoteCachePrice ?? snapshotPrice,
    barCount: published.barCount,
    minBarsForAccumulate: published.minBarsForAccumulate,
    stabilityScore: toNumberOrNull(row.stability_score),
    maxDrawdown: toNumberOrNull(row.max_dd),
  };
}

function compareNullableNumber(a: number | null, b: number | null, direction: SortDirection): number {
  const av = a ?? Number.NEGATIVE_INFINITY;
  const bv = b ?? Number.NEGATIVE_INFINITY;
  const base = av - bv;
  return direction === "asc" ? base : -base;
}

function compareNumber(a: number, b: number, direction: SortDirection): number {
  const base = a - b;
  return direction === "asc" ? base : -base;
}

function compareString(a: string, b: string, direction: SortDirection): number {
  const base = a.localeCompare(b);
  return direction === "asc" ? base : -base;
}

function quoteSortString(quote: ScreenerQuoteCacheRow | undefined, key: string): string {
  const value = quoteText(quote, key);
  return value ? value.toUpperCase() : "";
}

function quoteSortNumber(quote: ScreenerQuoteCacheRow | undefined, key: string): number | null {
  return quoteNumber(quote, key);
}

function sortRows(
  rows: ScreenerRow[],
  quoteCacheQuotes: Record<string, ScreenerQuoteCacheRow>,
  sortKey: SortKey,
  direction: SortDirection,
): ScreenerRow[] {
  const next = [...rows];

  next.sort((a, b) => {
    if (sortKey === "ticker") return compareString(a.ticker, b.ticker, direction);
    if (sortKey === "assetType") return compareString(a.assetType, b.assetType, direction);
    if (sortKey === "decision") return compareString(a.decision, b.decision, direction);
    if (sortKey === "regime") return compareString(a.regime, b.regime, direction);
    if (sortKey === "price") return compareNullableNumber(a.price, b.price, direction);
    if (sortKey === "barCount") return compareNumber(a.barCount, b.barCount, direction);
    if (sortKey === "stabilityScore") return compareNullableNumber(a.stabilityScore, b.stabilityScore, direction);
    if (sortKey === "maxDrawdown") return compareNullableNumber(a.maxDrawdown, b.maxDrawdown, direction);
    if (sortKey === "company") return compareString(quoteSortString(quoteCacheQuotes[a.ticker], "companyName"), quoteSortString(quoteCacheQuotes[b.ticker], "companyName"), direction);
    if (sortKey === "sector") return compareString(quoteSortString(quoteCacheQuotes[a.ticker], "sector"), quoteSortString(quoteCacheQuotes[b.ticker], "sector"), direction);
    if (sortKey === "industry") return compareString(quoteSortString(quoteCacheQuotes[a.ticker], "industry"), quoteSortString(quoteCacheQuotes[b.ticker], "industry"), direction);
    if (sortKey === "country") return compareString(quoteSortString(quoteCacheQuotes[a.ticker], "country"), quoteSortString(quoteCacheQuotes[b.ticker], "country"), direction);
    if (sortKey === "marketcap") return compareNullableNumber(quoteSortNumber(quoteCacheQuotes[a.ticker], "marketCap"), quoteSortNumber(quoteCacheQuotes[b.ticker], "marketCap"), direction);
    if (sortKey === "change") return compareNullableNumber(quoteSortNumber(quoteCacheQuotes[a.ticker], "changePct"), quoteSortNumber(quoteCacheQuotes[b.ticker], "changePct"), direction);
    if (sortKey === "volume") return compareNullableNumber(quoteSortNumber(quoteCacheQuotes[a.ticker], "volume"), quoteSortNumber(quoteCacheQuotes[b.ticker], "volume"), direction);
    return compareString(a.ticker, b.ticker, "asc");
  });

  return next;
}

function filterRows(
  rows: ScreenerRow[],
  options: {
    tab: ScreenerTab;
    search: string;
    decision: string;
    regime: string;
    assetType: string;
    minPrice: number | null;
    maxPrice: number | null;
    minBars: number | null;
    maxBars: number | null;
  },
): ScreenerRow[] {
  const search = options.search.trim().toUpperCase();
  const decision = options.decision.trim();
  const regime = options.regime.trim();
  const assetType = options.assetType.trim();

  return rows.filter((row) => {
    if (search && !row.ticker.includes(search)) return false;
    if (decision && row.decision !== decision) return false;
    if (regime && row.regime !== regime) return false;

    if (options.tab === "etf") {
      if (assetType) {
        if (row.assetType !== assetType) return false;
      } else if (row.assetType !== "etf") {
        return false;
      }
    } else if (assetType && row.assetType !== assetType) {
      return false;
    }

    if (options.minPrice !== null) {
      if (row.price === null || row.price < options.minPrice) return false;
    }

    if (options.maxPrice !== null) {
      if (row.price === null || row.price > options.maxPrice) return false;
    }

    if (options.minBars !== null && row.barCount < options.minBars) return false;
    if (options.maxBars !== null && row.barCount > options.maxBars) return false;

    return true;
  });
}

function normalizeText(value: string | null | undefined): string {
  if (!value) return "";
  return value.trim().toUpperCase();
}

function isFiniteValue(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function parseUnderOver(bucket: string): { kind: "under" | "over"; threshold: number } | null {
  if (bucket.length < 2) return null;
  const prefix = bucket[0];
  if (prefix !== "u" && prefix !== "o") return null;
  const threshold = Number(bucket.slice(1));
  if (!Number.isFinite(threshold)) return null;
  return { kind: prefix === "u" ? "under" : "over", threshold };
}

function quoteText(quote: ScreenerQuoteCacheRow | undefined, key: string): string | null {
  if (!quote) return null;
  const value = quote[key];
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  return text ? text : null;
}

function normalizeTaxonomyLabel(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  if (!text) return null;
  const normalized = text.toUpperCase();
  if (EMPTY_TAXONOMY_LABELS.has(normalized)) return null;
  return text;
}

function mapTaxonomyFallback(assetType: AssetType, quoteType: string | null): { sector: string; industry: string } {
  const quoteTypeNormalized = String(quoteType ?? "")
    .trim()
    .toUpperCase();
  const isEtf = assetType === "etf" || quoteTypeNormalized.includes("ETF") || quoteTypeNormalized.includes("FUND");
  if (assetType === "crypto" || quoteTypeNormalized.includes("CRYPTO")) {
    return { sector: "Cryptocurrency", industry: "Digital Assets" };
  }
  if (assetType === "index" || quoteTypeNormalized.includes("INDEX")) {
    return { sector: "Index", industry: "Market Index" };
  }
  if (isEtf) {
    return { sector: "ETF", industry: "Exchange Traded Fund" };
  }
  return { sector: "Unclassified", industry: "Unclassified" };
}

function resolveMapTaxonomy(
  row: ScreenerRow,
  quote: ScreenerQuoteCacheRow | undefined,
  profileOverride: ScreenerProfileOverrideRow | undefined,
): { sector: string; industry: string; quoteType: string | null; companyName: string | null } {
  const quoteType =
    normalizeTaxonomyLabel(quoteText(quote, "quoteType")) ??
    normalizeTaxonomyLabel(profileOverride?.quoteType) ??
    null;
  const companyName =
    normalizeTaxonomyLabel(quoteText(quote, "companyName")) ??
    normalizeTaxonomyLabel(quoteText(quote, "shortName")) ??
    normalizeTaxonomyLabel(quoteText(quote, "longName")) ??
    normalizeTaxonomyLabel(profileOverride?.companyName) ??
    null;

  const sector =
    normalizeTaxonomyLabel(quoteText(quote, "sector")) ??
    normalizeTaxonomyLabel(profileOverride?.sector);
  const industry =
    normalizeTaxonomyLabel(quoteText(quote, "industry")) ??
    normalizeTaxonomyLabel(profileOverride?.industry);

  if (sector && industry) {
    return { sector, industry, quoteType, companyName };
  }

  const fallback = mapTaxonomyFallback(row.assetType, quoteType);
  return {
    sector: sector ?? fallback.sector,
    industry: industry ?? fallback.industry,
    quoteType,
    companyName,
  };
}

function quoteNumber(quote: ScreenerQuoteCacheRow | undefined, key: string): number | null {
  if (!quote) return null;
  const n = Number(quote[key]);
  return Number.isFinite(n) ? n : null;
}

function quoteBoolean(quote: ScreenerQuoteCacheRow | undefined, key: string): boolean | null {
  if (!quote) return null;
  const value = quote[key];
  if (typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (value === 1) return true;
    if (value === 0) return false;
  }
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "y"].includes(normalized)) return true;
    if (["0", "false", "no", "n"].includes(normalized)) return false;
  }
  return null;
}

function optionLabelFor(key: AdvancedFilterKey, value: string): string {
  if (!value) return "";
  const option = (ADVANCED_FILTER_OPTIONS[key] ?? []).find((entry) => entry.value === value);
  return option?.label ?? value;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseScreenerTotal(html: string): number | null {
  const match = html.match(/#\s*\d+\s*\/\s*([0-9,]+)\s*Total/i);
  if (!match) return null;
  const n = Number(match[1].replace(/,/g, ""));
  return Number.isFinite(n) ? n : null;
}

function parseTickersFromScreenerHtml(html: string): string[] {
  const out = new Set<string>();
  const regex = /quote\.ashx\?t=([A-Z0-9.\-]+)/gi;
  let match: RegExpExecArray | null = regex.exec(html);
  while (match) {
    const ticker = String(match[1] ?? "").trim().toUpperCase();
    if (ticker) out.add(ticker);
    match = regex.exec(html);
  }
  return Array.from(out);
}

async function fetchScreenerHtmlPage(url: string): Promise<string | null> {
  const attemptLimit = 4;
  for (let attempt = 0; attempt < attemptLimit; attempt += 1) {
    const controller = new AbortController();
    const timeoutHandle = setTimeout(() => controller.abort(), EXTERNAL_FILTER_TIMEOUT_MS);
    try {
      const response = await fetch(url, {
        method: "GET",
        cache: "no-store",
        headers: {
          "User-Agent": "Mozilla/5.0",
          Accept: "text/html,application/xhtml+xml",
          "Accept-Language": "en-US,en;q=0.9",
        },
        signal: controller.signal,
      });

      if (response.status === 429) {
        await sleep(Math.min(5000, 500 * 2 ** attempt));
        continue;
      }

      if (!response.ok) return null;
      return await response.text();
    } catch {
      await sleep(300 * (attempt + 1));
    } finally {
      clearTimeout(timeoutHandle);
    }
  }
  return null;
}

type ExternalTickerQueryOptions = {
  filterToken?: string | null;
  signalToken?: string | null;
  orderToken?: string | null;
};

function normalizeQueryToken(value: string | null | undefined): string {
  return String(value ?? "").trim();
}

function buildCompositeFilterToken(advanced: AdvancedFilterState): string | null {
  const tokens: string[] = [];
  for (const key of ADVANCED_FILTER_KEYS) {
    const value = normalizeQueryToken(advanced[key]);
    if (!value || value === "custom_subscription") continue;
    const field = SCREENER_FILTER_FIELDS[key];
    if (!field?.dataFilter) continue;
    tokens.push(`${field.dataFilter}_${value}`);
  }
  if (tokens.length === 0) return null;
  return tokens.sort((a, b) => a.localeCompare(b)).join(",");
}

async function loadExternalTickerSet(options: ExternalTickerQueryOptions): Promise<ExternalTickerSet | null> {
  const filterToken = normalizeQueryToken(options.filterToken);
  const signalToken = normalizeQueryToken(options.signalToken);
  const orderToken = normalizeQueryToken(options.orderToken);
  if (!filterToken && !signalToken && !orderToken) return null;
  if (!EXTERNAL_FILTER_SOURCE_BASE_URL) return null;

  const cacheKey = `f=${filterToken.toLowerCase()}|s=${signalToken.toLowerCase()}|o=${orderToken.toLowerCase()}`;
  if (!cacheKey) return null;

  const now = Date.now();
  const cached = EXTERNAL_FILTER_CACHE.get(cacheKey);
  if (cached && cached.expiresAtMs > now) {
    return cached.value;
  }

  const existingInflight = EXTERNAL_FILTER_INFLIGHT.get(cacheKey);
  if (existingInflight) {
    return existingInflight;
  }

  const pending = (async (): Promise<ExternalTickerSet | null> => {
    const tickers = new Set<string>();
    const orderedTickers: string[] = [];
    let total: number | null = null;
    let pagesFetched = 0;
    let firstRequest = true;

    for (let pageStart = 1; pagesFetched < EXTERNAL_FILTER_MAX_PAGES; pageStart += 20) {
      if (!firstRequest) {
        await sleep(150);
      }
      firstRequest = false;
      pagesFetched += 1;

      const params = new URLSearchParams({ v: "111", r: String(pageStart) });
      if (filterToken) params.set("f", filterToken);
      if (signalToken) params.set("s", signalToken);
      if (orderToken) params.set("o", orderToken);
      const url = `${EXTERNAL_FILTER_SOURCE_BASE_URL}/screener.ashx?${params.toString()}`;
      const html = await fetchScreenerHtmlPage(url);
      if (!html) break;

      if (total === null) {
        total = parseScreenerTotal(html);
      }

      const pageTickers = parseTickersFromScreenerHtml(html);
      if (pageTickers.length === 0) break;

      for (const ticker of pageTickers) {
        if (!tickers.has(ticker)) orderedTickers.push(ticker);
        tickers.add(ticker);
      }

      if (total !== null && tickers.size >= total) break;
      if (pageTickers.length < 20) break;
    }

    if (pagesFetched === 0) return null;

    return {
      queryKey: cacheKey,
      filterToken: filterToken || null,
      signalToken: signalToken || null,
      tickers,
      orderedTickers,
      total,
      pagesFetched,
      sourceBaseUrl: EXTERNAL_FILTER_SOURCE_BASE_URL,
      fetchedAtUtc: new Date().toISOString(),
    };
  })();

  EXTERNAL_FILTER_INFLIGHT.set(cacheKey, pending);

  try {
    const resolved = await pending;
    EXTERNAL_FILTER_CACHE.set(cacheKey, {
      expiresAtMs: Date.now() + EXTERNAL_FILTER_TTL_MS,
      value: resolved,
    });
    return resolved;
  } finally {
    EXTERNAL_FILTER_INFLIGHT.delete(cacheKey);
  }
}

async function resolveAdvancedExternalContext(
  advanced: AdvancedFilterState,
  signalToken: string,
): Promise<AdvancedExternalFilterContext> {
  const normalizedSignalToken = normalizeQueryToken(signalToken);
  const resolveCompositeExternally = Boolean(normalizedSignalToken);
  const compositeFilterToken = resolveCompositeExternally ? buildCompositeFilterToken(advanced) : null;

  const compositePromise =
    resolveCompositeExternally
      ? loadExternalTickerSet({ filterToken: compositeFilterToken, signalToken: normalizedSignalToken })
      : Promise.resolve(null);

  const countryPromise =
    COUNTRY_REGION_FILTERS.has(advanced.country) && advanced.country !== "custom_subscription"
      ? loadExternalTickerSet({ filterToken: `geo_${advanced.country}` })
      : Promise.resolve(null);

  const themePromise =
    advanced.theme && advanced.theme !== "custom_subscription"
      ? loadExternalTickerSet({ filterToken: `theme_${advanced.theme}` })
      : Promise.resolve(null);

  const subThemePromise =
    advanced.subTheme && advanced.subTheme !== "custom_subscription"
      ? loadExternalTickerSet({ filterToken: `subtheme_${advanced.subTheme}` })
      : Promise.resolve(null);

  const [compositeRows, countryRows, themeRows, subThemeRows] = await Promise.all([
    compositePromise,
    countryPromise,
    themePromise,
    subThemePromise,
  ]);

  return {
    countryRegionTickers: countryRows?.tickers ?? null,
    themeTickers: themeRows?.tickers ?? null,
    subThemeTickers: subThemeRows?.tickers ?? null,
    compositeFilterToken,
    compositeSignalToken: normalizedSignalToken || null,
    compositeTickers: compositeRows?.tickers ?? null,
    compositeOrderedTickers: compositeRows?.orderedTickers ?? null,
  };
}

function externalFilterDiagnostics(
  filterToken: string | null,
  data: Set<string> | null,
): {
  requested: string | null;
  sourceConfigured: boolean;
  resolved: boolean;
  tickerCount: number | null;
} {
  return {
    requested: filterToken,
    sourceConfigured: Boolean(EXTERNAL_FILTER_SOURCE_BASE_URL),
    resolved: filterToken ? Boolean(data) : true,
    tickerCount: data ? data.size : null,
  };
}

function easternDateParts(date: Date): EasternDateParts | null {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);

  const out: Partial<EasternDateParts> = {};
  for (const part of parts) {
    if (part.type === "year") out.year = Number(part.value);
    if (part.type === "month") out.month = Number(part.value);
    if (part.type === "day") out.day = Number(part.value);
    if (part.type === "hour") out.hour = Number(part.value);
    if (part.type === "minute") out.minute = Number(part.value);
  }

  if (!Number.isFinite(out.year) || !Number.isFinite(out.month) || !Number.isFinite(out.day)) return null;
  return {
    year: Number(out.year),
    month: Number(out.month),
    day: Number(out.day),
    hour: Number(out.hour ?? 0),
    minute: Number(out.minute ?? 0),
  };
}

function toDayIndex(parts: EasternDateParts): number {
  const utcDay = Date.UTC(parts.year, parts.month - 1, parts.day);
  return Math.floor(utcDay / 86_400_000);
}

function weekdayFromParts(parts: EasternDateParts): number {
  return new Date(Date.UTC(parts.year, parts.month - 1, parts.day)).getUTCDay();
}

function weekStartIndex(dayIndex: number, weekday: number): number {
  const mondayOffset = (weekday + 6) % 7;
  return dayIndex - mondayOffset;
}

function earningsSession(parts: EasternDateParts): "bmo" | "amc" | "during" {
  const minutes = parts.hour * 60 + parts.minute;
  if (minutes < 9 * 60 + 30) return "bmo";
  if (minutes >= 16 * 60) return "amc";
  return "during";
}

function normalizeExchangeBucket(value: string | null | undefined): string {
  const text = normalizeText(value);
  if (!text) return "";
  if (text.includes("NASDAQ") || text.includes("NMS") || text.includes("NGM")) return "NASDAQ";
  if (text.includes("AMEX") || text.includes("NYSEAMERICAN") || text.includes("NYSE MKT")) return "AMEX";
  if (text.includes("CBOE") || text.includes("BATS") || text.includes("BYX") || text.includes("EDGX")) return "CBOE";
  if (text.includes("NYSE")) return "NYSE";
  return text;
}

function matchExchangeFilter(exchangeValue: string | null | undefined, filter: string): boolean {
  if (!filter || filter === "custom_subscription") return true;
  const exchange = normalizeExchangeBucket(exchangeValue);
  if (!exchange) return false;
  if (filter === "amex") return exchange === "AMEX";
  if (filter === "cboe") return exchange === "CBOE";
  if (filter === "nasd") return exchange === "NASDAQ";
  if (filter === "nyse") return exchange === "NYSE";
  return true;
}

function matchIndexFilter(indexName: string | null | undefined, filter: string): boolean {
  if (!filter || filter === "custom_subscription") return true;
  const text = normalizeText(indexName);
  if (!text) return false;
  if (filter === "sp500") return text.includes("S&P 500") || text.includes("SP500");
  if (filter === "ndx") return text.includes("NASDAQ 100") || text.includes("NDX");
  if (filter === "dji") return text.includes("DJIA") || text.includes("DOW JONES");
  if (filter === "rut") return text.includes("RUSSELL 2000") || text.includes("RUT");
  return true;
}

function matchLabeledTextFilter(value: string | null | undefined, filter: string, key: AdvancedFilterKey): boolean {
  if (!filter || filter === "custom_subscription") return true;
  const expectedLabel = optionLabelFor(key, filter);
  if (!expectedLabel || normalizeText(expectedLabel) === "ANY") return true;
  const actual = normalizeText(value);
  if (!actual) return false;
  return actual === normalizeText(expectedLabel);
}

function matchCountryFilter(countryValue: string | null | undefined, filter: string): boolean {
  if (!filter || filter === "custom_subscription") return true;
  const country = normalizeText(countryValue);
  if (!country) return false;

  if (filter === "usa") return country === "USA";
  if (filter === "notusa") return country !== "USA";

  const expectedLabel = optionLabelFor("country", filter);
  if (!expectedLabel || normalizeText(expectedLabel) === "ANY") return true;
  return country === normalizeText(expectedLabel);
}

function matchIndustryFilter(quote: ScreenerQuoteCacheRow | undefined, filter: string): boolean {
  if (!filter || filter === "custom_subscription") return true;
  const industry = normalizeText(quoteText(quote, "industry"));
  const category = normalizeText(quoteText(quote, "category"));
  const quoteType = normalizeText(quoteText(quote, "quoteType"));

  const isEtf =
    industry === "EXCHANGE TRADED FUND" ||
    category.includes("ETF") ||
    quoteType === "ETF" ||
    quoteType === "MUTUALFUND" ||
    quoteType === "MUTUAL FUND";

  if (filter === "stocksonly") return !isEtf;
  if (filter === "exchangetradedfund") return isEtf;

  return matchLabeledTextFilter(quoteText(quote, "industry"), filter, "industry");
}

function matchEarningsDateFilter(epochSec: number | null | undefined, filter: string): boolean {
  if (!filter) return true;
  if (filter === "custom_subscription") return true;
  if (epochSec === null || epochSec === undefined || Number.isNaN(epochSec)) return false;

  const earnings = easternDateParts(new Date(epochSec * 1000));
  const today = easternDateParts(new Date());
  if (!earnings || !today) return false;

  const earningsDay = toDayIndex(earnings);
  const todayDay = toDayIndex(today);
  const deltaDays = earningsDay - todayDay;
  const session = earningsSession(earnings);

  const earningsWeekStart = weekStartIndex(earningsDay, weekdayFromParts(earnings));
  const todayWeekStart = weekStartIndex(todayDay, weekdayFromParts(today));

  if (filter === "today") return deltaDays === 0;
  if (filter === "todaybefore" || filter === "today_bmo") return deltaDays === 0 && session === "bmo";
  if (filter === "todayafter" || filter === "today_amc") return deltaDays === 0 && session === "amc";

  if (filter === "tomorrow") return deltaDays === 1;
  if (filter === "tomorrowbefore" || filter === "tomorrow_bmo") return deltaDays === 1 && session === "bmo";
  if (filter === "tomorrowafter" || filter === "tomorrow_amc") return deltaDays === 1 && session === "amc";

  if (filter === "yesterday") return deltaDays === -1;
  if (filter === "yesterdaybefore" || filter === "yesterday_bmo") return deltaDays === -1 && session === "bmo";
  if (filter === "yesterdayafter" || filter === "yesterday_amc") return deltaDays === -1 && session === "amc";

  if (filter === "nextdays5" || filter === "next_5_days") return deltaDays >= 1 && deltaDays <= 5;
  if (filter === "prevdays5" || filter === "previous_5_days") return deltaDays <= -1 && deltaDays >= -5;

  if (filter === "thisweek" || filter === "this_week") return earningsWeekStart === todayWeekStart;
  if (filter === "nextweek" || filter === "next_week") return earningsWeekStart === todayWeekStart + 7;
  if (filter === "prevweek" || filter === "previous_week") return earningsWeekStart === todayWeekStart - 7;

  if (filter === "thismonth" || filter === "this_month") return earnings.year === today.year && earnings.month === today.month;

  return true;
}

function matchMarketCapFilter(value: number | null | undefined, bucket: string): boolean {
  if (!bucket) return true;
  if (bucket === "custom_subscription") return true;
  if (value === null || value === undefined || Number.isNaN(value)) return false;

  if (bucket === "mega") return value >= 200_000_000_000;
  if (bucket === "large") return value >= 10_000_000_000 && value < 200_000_000_000;
  if (bucket === "mid") return value >= 2_000_000_000 && value < 10_000_000_000;
  if (bucket === "small") return value >= 300_000_000 && value < 2_000_000_000;
  if (bucket === "micro") return value >= 50_000_000 && value < 300_000_000;
  if (bucket === "nano") return value < 50_000_000;

  if (bucket === "largeover" || bucket === "plus_large") return value > 10_000_000_000;
  if (bucket === "midover" || bucket === "plus_mid") return value > 2_000_000_000;
  if (bucket === "smallover" || bucket === "plus_small") return value > 300_000_000;
  if (bucket === "microover" || bucket === "plus_micro") return value > 50_000_000;

  if (bucket === "largeunder" || bucket === "minus_large") return value < 200_000_000_000;
  if (bucket === "midunder" || bucket === "minus_mid") return value < 10_000_000_000;
  if (bucket === "smallunder" || bucket === "minus_small") return value < 2_000_000_000;
  if (bucket === "microunder" || bucket === "minus_micro") return value < 300_000_000;

  return true;
}

function matchPriceBucket(value: number | null | undefined, bucket: string): boolean {
  if (!bucket) return true;
  if (bucket === "custom_subscription") return true;
  if (value === null || value === undefined || Number.isNaN(value)) return false;

  const underOver = parseUnderOver(bucket);
  if (underOver) {
    return underOver.kind === "under" ? value < underOver.threshold : value > underOver.threshold;
  }

  const range = PRICE_RANGE_CODES[bucket];
  if (range) return value >= range[0] && value <= range[1];

  if (bucket.startsWith("under_")) {
    const threshold = Number(bucket.slice("under_".length));
    if (Number.isFinite(threshold)) return value < threshold;
  }

  if (bucket.startsWith("over_")) {
    const threshold = Number(bucket.slice("over_".length));
    if (Number.isFinite(threshold)) return value > threshold;
  }

  if (bucket.startsWith("range_")) {
    const payload = bucket.slice("range_".length);
    const [lowerText, upperText] = payload.split("_", 2);
    const lower = Number(lowerText);
    const upper = Number(upperText);
    if (Number.isFinite(lower) && Number.isFinite(upper)) return value >= lower && value <= upper;
  }

  return true;
}

function matchDividendYieldFilter(value: number | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(value)) return false;
  if (bucket === "none") return value <= 0;
  if (bucket === "pos") return value > 0;
  if (bucket === "high") return value > 0.05;
  if (bucket === "veryhigh") return value > 0.1;
  const parsed = parseUnderOver(bucket);
  if (parsed && parsed.kind === "over") {
    return value > parsed.threshold / 100;
  }
  return true;
}

function matchShortFloatFilter(value: number | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(value)) return false;
  if (bucket === "low") return value < 0.05;
  if (bucket === "high") return value > 0.2;
  const parsed = parseUnderOver(bucket);
  if (parsed) {
    const threshold = parsed.threshold / 100;
    return parsed.kind === "under" ? value < threshold : value > threshold;
  }
  return true;
}

function matchAverageVolumeFilter(value: number | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(value)) return false;
  const parsed = parseUnderOver(bucket);
  if (parsed) {
    const threshold = AVG_CURR_VOLUME_THRESHOLDS[String(parsed.threshold)];
    if (threshold !== undefined) return parsed.kind === "under" ? value < threshold : value > threshold;
  }
  const range = AVG_VOLUME_RANGE_CODES[bucket];
  if (range) return value >= range[0] && value <= range[1];
  if (bucket === "over500k") return value > 500_000;
  if (bucket === "over2m") return value > 2_000_000;
  return true;
}

function matchRelativeVolumeFilter(value: number | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(value)) return false;
  const parsed = parseUnderOver(bucket);
  if (!parsed) return true;
  return parsed.kind === "under" ? value < parsed.threshold : value > parsed.threshold;
}

function matchCurrentVolumeFilter(
  value: number | null | undefined,
  bucket: string,
  price: number | null | undefined,
  sharesFloat: number | null | undefined,
): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(value)) return false;

  const parsed = parseUnderOver(bucket);
  if (parsed) {
    const threshold = AVG_CURR_VOLUME_THRESHOLDS[String(parsed.threshold)];
    if (threshold !== undefined) return parsed.kind === "under" ? value < threshold : value > threshold;
  }

  if (bucket === "o50sf") {
    if (!isFiniteValue(sharesFloat) || sharesFloat <= 0) return false;
    return value > sharesFloat * 0.5;
  }
  if (bucket === "o100sf") {
    if (!isFiniteValue(sharesFloat) || sharesFloat <= 0) return false;
    return value > sharesFloat;
  }

  if (bucket.startsWith("uusd")) {
    const threshold = CURRENT_VOLUME_DOLLAR_THRESHOLDS[bucket.slice("uusd".length)];
    if (threshold === undefined) return true;
    if (!isFiniteValue(price)) return false;
    return value * price < threshold;
  }
  if (bucket.startsWith("ousd")) {
    const threshold = CURRENT_VOLUME_DOLLAR_THRESHOLDS[bucket.slice("ousd".length)];
    if (threshold === undefined) return true;
    if (!isFiniteValue(price)) return false;
    return value * price > threshold;
  }

  return true;
}

function matchTargetPriceFilter(targetPrice: number | null | undefined, price: number | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(targetPrice) || !isFiniteValue(price) || price === 0) return false;

  const ratio = (targetPrice - price) / price;
  if (bucket === "above") return ratio > 0;
  if (bucket === "below") return ratio < 0;

  if (bucket.startsWith("a")) {
    const threshold = Number(bucket.slice(1));
    if (Number.isFinite(threshold)) return ratio >= threshold / 100;
  }
  if (bucket.startsWith("b")) {
    const threshold = Number(bucket.slice(1));
    if (Number.isFinite(threshold)) return ratio <= -(threshold / 100);
  }

  return true;
}

function matchIpoDateFilter(epochSec: number | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(epochSec)) return false;

  const ipo = easternDateParts(new Date(epochSec * 1000));
  const today = easternDateParts(new Date());
  if (!ipo || !today) return false;

  const ipoDay = toDayIndex(ipo);
  const todayDay = toDayIndex(today);
  const ageDays = todayDay - ipoDay;

  if (bucket === "today") return ageDays === 0;
  if (bucket === "yesterday") return ageDays === 1;
  if (bucket === "prevweek") return ageDays >= 0 && ageDays <= 7;
  if (bucket === "prevmonth") return ageDays >= 0 && ageDays <= 31;
  if (bucket === "prevquarter") return ageDays >= 0 && ageDays <= 92;
  if (bucket === "prevyear") return ageDays >= 0 && ageDays <= 366;
  if (bucket === "prev2yrs") return ageDays >= 0 && ageDays <= 732;
  if (bucket === "prev3yrs") return ageDays >= 0 && ageDays <= 1098;
  if (bucket === "prev5yrs") return ageDays >= 0 && ageDays <= 1830;
  if (bucket === "more1") return ageDays > 365;
  if (bucket === "more5") return ageDays > 1825;
  if (bucket === "more10") return ageDays > 3650;
  if (bucket === "more15") return ageDays > 5475;
  if (bucket === "more20") return ageDays > 7300;
  if (bucket === "more25") return ageDays > 9125;

  return true;
}

function matchSharesOutstandingFilter(value: number | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(value)) return false;
  const parsed = parseUnderOver(bucket);
  if (!parsed) return true;
  const threshold = parsed.threshold * 1_000_000;
  return parsed.kind === "under" ? value < threshold : value > threshold;
}

function matchFloatFilter(
  floatValue: number | null | undefined,
  sharesOutstanding: number | null | undefined,
  bucket: string,
): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(floatValue)) return false;

  if (bucket.endsWith("p")) {
    if (!isFiniteValue(sharesOutstanding) || sharesOutstanding <= 0) return false;
    const parsed = parseUnderOver(bucket.slice(0, -1));
    if (!parsed) return true;
    const ratio = floatValue / sharesOutstanding;
    const threshold = parsed.threshold / 100;
    return parsed.kind === "under" ? ratio < threshold : ratio > threshold;
  }

  const parsed = parseUnderOver(bucket);
  if (!parsed) return true;
  const threshold = parsed.threshold * 1_000_000;
  return parsed.kind === "under" ? floatValue < threshold : floatValue > threshold;
}

function matchAnalystRecomFilter(value: number | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (!isFiniteValue(value)) return false;
  if (bucket === "strongbuy") return value <= 1.5;
  if (bucket === "buybetter") return value <= 2;
  if (bucket === "buy") return value > 1.5 && value <= 2.5;
  if (bucket === "holdbetter") return value <= 3;
  if (bucket === "hold") return value > 2.5 && value <= 3.5;
  if (bucket === "holdworse") return value >= 3;
  if (bucket === "sell") return value > 3.5 && value <= 4.5;
  if (bucket === "sellworse") return value >= 4;
  if (bucket === "strongsell") return value >= 4.5;
  return true;
}

function matchOptionShortFilter(
  optionable: boolean | null | undefined,
  shortable: boolean | null | undefined,
  shortableShares: number | null | undefined,
  shortableUsd: number | null | undefined,
  restricted: boolean | null | undefined,
  halted: boolean | null | undefined,
  bucket: string,
): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (bucket === "option") return optionable === true;
  if (bucket === "short") return shortable === true;
  if (bucket === "notoption") return optionable === false;
  if (bucket === "notshort") return shortable === false;
  if (bucket === "optionshort") return optionable === true && shortable === true;
  if (bucket === "optionnotshort") return optionable === true && shortable === false;
  if (bucket === "notoptionshort") return optionable === false && shortable === true;
  if (bucket === "notoptionnotshort") return optionable === false && shortable === false;

  if (bucket === "restricted") {
    return restricted === true || halted === true;
  }

  if (bucket === "so10k") return isFiniteValue(shortableShares) && shortableShares > 10_000;
  if (bucket === "so100k") return isFiniteValue(shortableShares) && shortableShares > 100_000;
  if (bucket === "so1m") return isFiniteValue(shortableShares) && shortableShares > 1_000_000;
  if (bucket === "so10m") return isFiniteValue(shortableShares) && shortableShares > 10_000_000;

  if (bucket === "uo1m") return isFiniteValue(shortableUsd) && shortableUsd > 1_000_000;
  if (bucket === "uo10m") return isFiniteValue(shortableUsd) && shortableUsd > 10_000_000;
  if (bucket === "uo100m") return isFiniteValue(shortableUsd) && shortableUsd > 100_000_000;
  if (bucket === "uo1b") return isFiniteValue(shortableUsd) && shortableUsd > 1_000_000_000;

  return false;
}

function matchTradesFilter(tradesValue: string | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  const expectedLabel = optionLabelFor("trades", bucket);
  if (!expectedLabel || normalizeText(expectedLabel) === "ANY") return true;
  const actual = normalizeText(tradesValue);
  if (!actual) return false;
  return actual === normalizeText(expectedLabel);
}

function matchThemeFilter(
  ticker: string,
  quote: ScreenerQuoteCacheRow | undefined,
  bucket: string,
  externalSet: Set<string> | null,
): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (externalSet) return externalSet.has(ticker);

  const expectedLabel = optionLabelFor("theme", bucket);
  if (!expectedLabel || normalizeText(expectedLabel) === "ANY") return true;

  const actual = normalizeText(quoteText(quote, "theme"));
  if (!actual) return false;
  return actual === normalizeText(expectedLabel);
}

function matchSubThemeFilter(
  ticker: string,
  quote: ScreenerQuoteCacheRow | undefined,
  bucket: string,
  externalSet: Set<string> | null,
): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (externalSet) return externalSet.has(ticker);

  const expectedLabel = optionLabelFor("subTheme", bucket);
  if (!expectedLabel || normalizeText(expectedLabel) === "ANY") return true;

  const actual = normalizeText(quoteText(quote, "subTheme"));
  if (!actual) return false;
  return actual === normalizeText(expectedLabel);
}

function normalizeAdvancedFilters(searchParams: URLSearchParams): AdvancedFilterState {
  const next: AdvancedFilterState = { ...ADVANCED_FILTER_DEFAULTS };
  for (const key of ADVANCED_FILTER_KEYS) {
    next[key] = String(searchParams.get(key) ?? "").trim();
  }
  return next;
}

function hasAdvancedFilters(filters: AdvancedFilterState): boolean {
  for (const key of ADVANCED_FILTER_KEYS) {
    if (filters[key]) return true;
  }
  return false;
}

function matchAdvancedFilters(
  row: ScreenerRow,
  quote: ScreenerQuoteCacheRow | undefined,
  advanced: AdvancedFilterState,
  externalContext: AdvancedExternalFilterContext,
): boolean {
  if (externalContext.compositeFilterToken || externalContext.compositeSignalToken) {
    if (externalContext.compositeTickers) {
      return externalContext.compositeTickers.has(row.ticker);
    }
  }

  const livePrice = row.price ?? quoteNumber(quote, "price");
  const countryRequiresExternal = COUNTRY_REGION_FILTERS.has(advanced.country) && advanced.country !== "custom_subscription";

  if (!matchExchangeFilter(quoteText(quote, "exchange"), advanced.exchange)) return false;
  if (!matchIndexFilter(quoteText(quote, "indexName"), advanced.index)) return false;
  if (!matchLabeledTextFilter(quoteText(quote, "sector"), advanced.sector, "sector")) return false;
  if (!matchIndustryFilter(quote, advanced.industry)) return false;
  if (countryRequiresExternal) {
    if (!externalContext.countryRegionTickers || !externalContext.countryRegionTickers.has(row.ticker)) return false;
  } else if (!matchCountryFilter(quoteText(quote, "country"), advanced.country)) {
    return false;
  }
  if (!matchMarketCapFilter(quoteNumber(quote, "marketCap"), advanced.marketCap)) return false;
  if (!matchDividendYieldFilter(quoteNumber(quote, "dividendYield"), advanced.dividendYield)) return false;
  if (!matchShortFloatFilter(quoteNumber(quote, "shortFloat"), advanced.shortFloat)) return false;
  if (!matchAnalystRecomFilter(quoteNumber(quote, "recommendationMean"), advanced.analystRecom)) return false;
  if (
    !matchOptionShortFilter(
      quoteBoolean(quote, "optionable"),
      quoteBoolean(quote, "shortable"),
      quoteNumber(quote, "shortableShares"),
      quoteNumber(quote, "shortableUsd"),
      quoteBoolean(quote, "shortRestricted"),
      quoteBoolean(quote, "halted"),
      advanced.optionShort,
    )
  ) {
    return false;
  }
  if (!matchPriceBucket(livePrice, advanced.priceBand)) return false;
  if (!matchEarningsDateFilter(quoteNumber(quote, "earningsDate"), advanced.earningsDate)) return false;
  if (!matchAverageVolumeFilter(quoteNumber(quote, "avgVolume"), advanced.avgVolume)) return false;
  if (!matchRelativeVolumeFilter(quoteNumber(quote, "relVolume"), advanced.relVolume)) return false;
  if (!matchCurrentVolumeFilter(quoteNumber(quote, "volume"), advanced.currentVolume, livePrice, quoteNumber(quote, "sharesFloat"))) return false;
  if (!matchTargetPriceFilter(quoteNumber(quote, "target1Y"), livePrice, advanced.targetPrice)) return false;
  if (!matchIpoDateFilter(quoteNumber(quote, "ipoDate"), advanced.ipoDate)) return false;
  if (!matchSharesOutstandingFilter(quoteNumber(quote, "sharesOutstanding"), advanced.sharesOutstanding)) return false;
  if (!matchFloatFilter(quoteNumber(quote, "sharesFloat"), quoteNumber(quote, "sharesOutstanding"), advanced.float)) return false;
  if (!matchTradesFilter(quoteText(quote, "trades"), advanced.trades)) return false;
  if (!matchThemeFilter(row.ticker, quote, advanced.theme, externalContext.themeTickers)) return false;
  if (!matchSubThemeFilter(row.ticker, quote, advanced.subTheme, externalContext.subThemeTickers)) return false;

  return true;
}

function buildMapTickers(
  rows: ScreenerRow[],
  quotes: Record<string, ScreenerQuoteCacheRow>,
  profileOverrides: Record<string, ScreenerProfileOverrideRow>,
): ScreenerMapTicker[] {
  const out: ScreenerMapTicker[] = [];

  for (const row of rows) {
    const quote = quotes[row.ticker];
    if (!quote) continue;

    const ticker = String(row.ticker ?? "").trim().toUpperCase();
    if (!ticker) continue;

    const taxonomy = resolveMapTaxonomy(row, quote, profileOverrides[ticker]);
    const marketCap = Math.max(0, quoteNumber(quote, "marketCap") ?? 0);
    const volume = Math.max(0, quoteNumber(quote, "volume") ?? 0);
    const changePct = quoteNumber(quote, "changePct");
    const perfWeek = quoteNumber(quote, "perfWeek");
    const perfMonth = quoteNumber(quote, "perfMonth");
    const perfQuarter = quoteNumber(quote, "perfQuarter");
    const perfHalf = quoteNumber(quote, "perfHalf");
    const perfYtd = quoteNumber(quote, "perfYtd");
    const perfYear = quoteNumber(quote, "perfYear");
    const price = quoteNumber(quote, "price");
    out.push({
      ticker,
      companyName: taxonomy.companyName,
      sector: taxonomy.sector,
      industry: taxonomy.industry,
      assetType: row.assetType,
      quoteType: taxonomy.quoteType,
      marketCap,
      changePct: isFiniteValue(changePct) ? changePct : null,
      perfWeek: isFiniteValue(perfWeek) ? perfWeek : null,
      perfMonth: isFiniteValue(perfMonth) ? perfMonth : null,
      perfQuarter: isFiniteValue(perfQuarter) ? perfQuarter : null,
      perfHalf: isFiniteValue(perfHalf) ? perfHalf : null,
      perfYtd: isFiniteValue(perfYtd) ? perfYtd : null,
      perfYear: isFiniteValue(perfYear) ? perfYear : null,
      price: isFiniteValue(price) ? price : null,
      volume,
    });
  }

  return out.sort((a, b) => {
    if (b.marketCap !== a.marketCap) return b.marketCap - a.marketCap;
    if (b.volume !== a.volume) return b.volume - a.volume;
    return a.ticker.localeCompare(b.ticker);
  });
}

function buildMapCells(
  rows: ScreenerRow[],
  quotes: Record<string, ScreenerQuoteCacheRow>,
  profileOverrides: Record<string, ScreenerProfileOverrideRow>,
): ScreenerMapCell[] {
  const bucket = new Map<
    string,
    {
      sector: string;
      industry: string;
      marketCap: number;
      tickers: number;
      volume: number;
      changeWeighted: number;
      changeWeight: number;
      leaders: Array<{
        ticker: string;
        price: number | null;
        changePct: number | null;
        marketCap: number | null;
        volume: number | null;
      }>;
    }
  >();

  for (const row of rows) {
    const quote = quotes[row.ticker];
    if (!quote) continue;

    const taxonomy = resolveMapTaxonomy(row, quote, profileOverrides[row.ticker]);
    const sector = taxonomy.sector;
    const industry = taxonomy.industry;
    const key = `${sector}::${industry}`;
    const marketCap = Math.max(0, quoteNumber(quote, "marketCap") ?? 0);
    const volume = Math.max(0, quoteNumber(quote, "volume") ?? 0);
    const changePct = quoteNumber(quote, "changePct");
    const price = quoteNumber(quote, "price");

    const entry = bucket.get(key) ?? {
      sector,
      industry,
      marketCap: 0,
      tickers: 0,
      volume: 0,
      changeWeighted: 0,
      changeWeight: 0,
      leaders: [],
    };

    entry.marketCap += marketCap;
    entry.volume += volume;
    entry.tickers += 1;

    if (isFiniteValue(changePct)) {
      const weight = marketCap > 0 ? marketCap : 1;
      entry.changeWeighted += changePct * weight;
      entry.changeWeight += weight;
    }

    entry.leaders.push({
      ticker: row.ticker,
      price: isFiniteValue(price) ? price : null,
      changePct: isFiniteValue(changePct) ? changePct : null,
      marketCap: marketCap > 0 ? marketCap : null,
      volume: volume > 0 ? volume : null,
    });

    bucket.set(key, entry);
  }

  return Array.from(bucket.values())
    .map((entry) => ({
      sector: entry.sector,
      industry: entry.industry,
      marketCap: entry.marketCap,
      avgChangePct: entry.changeWeight > 0 ? entry.changeWeighted / entry.changeWeight : null,
      tickers: entry.tickers,
      volume: entry.volume,
      leaders: entry.leaders
        .sort((a, b) => {
          const capA = a.marketCap ?? 0;
          const capB = b.marketCap ?? 0;
          if (capB !== capA) return capB - capA;
          const volA = a.volume ?? 0;
          const volB = b.volume ?? 0;
          return volB - volA;
        })
        .slice(0, 20),
    }))
    .sort((a, b) => {
      if (b.marketCap !== a.marketCap) return b.marketCap - a.marketCap;
      return b.tickers - a.tickers;
    })
    .slice(0, 500);
}

async function loadSnapshotRowsWithTimeout(
  timeoutMs: number,
): Promise<Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>> {
  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  try {
    return await Promise.race([
      loadRuntimeSnapshotRowsFromPostgres(),
      new Promise<Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>>((_, reject) => {
        timeoutHandle = setTimeout(() => {
          reject(new Error(`Screener snapshot load timed out after ${timeoutMs}ms.`));
        }, timeoutMs);
      }),
    ]);
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle);
  }
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const requestStartedAtMs = Date.now();
  const timeoutMs = normalizeTimeoutMs(process.env.TFE_SCREENER_SNAPSHOT_TIMEOUT_MS, DEFAULT_TIMEOUT_MS);
  const { searchParams } = new URL(request.url);

  const tab = normalizeTab(searchParams.get("tab"));
  const page = normalizePage(searchParams.get("page"));
  const pageSize = normalizePageSize(searchParams.get("pageSize"));
  const search = String(searchParams.get("search") ?? "");
  const decision = String(searchParams.get("decision") ?? "");
  const signal = String(searchParams.get("signal") ?? "");
  const filterGroup = String(searchParams.get("filterGroup") ?? "");
  const regime = String(searchParams.get("regime") ?? "");
  const assetType = String(searchParams.get("assetType") ?? "");
  const minPrice = parseQueryNumber(searchParams.get("minPrice"));
  const maxPrice = parseQueryNumber(searchParams.get("maxPrice"));
  const minBars = parseQueryNumber(searchParams.get("minBars"));
  const maxBars = parseQueryNumber(searchParams.get("maxBars"));
  const sortKey = normalizeSortKey(searchParams.get("sortKey"));
  const sortDir = normalizeSortDirection(searchParams.get("sortDir"));
  const advancedFilters = normalizeAdvancedFilters(searchParams);
  const includeMap = parseBooleanQueryFlag(searchParams.get("includeMap"));
  const diagnosticsEnabled = parseBooleanQueryFlag(searchParams.get("diagnostics"));

  const phaseTimings: {
    snapshot_load_ms: number | null;
    quote_load_ms: number | null;
    map_filter_ms: number | null;
    advanced_external_ms: number | null;
    sort_page_ms: number | null;
    map_build_ms: number | null;
  } = {
    snapshot_load_ms: null,
    quote_load_ms: null,
    map_filter_ms: null,
    advanced_external_ms: null,
    sort_page_ms: null,
    map_build_ms: null,
  };

  const withDiagnostics = (payload: Record<string, unknown>, phase: string): Record<string, unknown> => {
    if (!diagnosticsEnabled) return payload;
    return {
      ...payload,
      diagnostics: {
        enabled: true,
        phase,
        timings: {
          ...phaseTimings,
          total_ms: Date.now() - requestStartedAtMs,
        },
      },
    };
  };

  let snapshot: Awaited<ReturnType<typeof loadRuntimeSnapshotRowsFromPostgres>>;
  const snapshotLoadStartedAtMs = Date.now();
  try {
    snapshot = await loadSnapshotRowsWithTimeout(timeoutMs);
    phaseTimings.snapshot_load_ms = Date.now() - snapshotLoadStartedAtMs;
  } catch (error) {
    phaseTimings.snapshot_load_ms = Date.now() - snapshotLoadStartedAtMs;
    const details = error instanceof Error ? error.message : "Unknown snapshot load failure.";
    const publicationState = await loadCanonicalPublicationState({
      snapshot: { available: false, runId: null, generatedAtUtc: null },
      quote: { available: false, runId: null },
    });
    return NextResponse.json(withDiagnostics({
        error: "Screener unavailable because snapshot load failed.",
        details,
        tab,
        ...publicationContractFields(publicationState),
      }, "snapshot_load_failed"),
      { status: 503 },
    );
  }

  if (!snapshot.sourcePath || snapshot.rows.length === 0) {
    const publicationState = await loadCanonicalPublicationState({
      snapshot: {
        available: false,
        runId: snapshot.runId,
        generatedAtUtc: snapshot.generatedAtUtc,
      },
      quote: { available: false, runId: null },
    });
    return NextResponse.json(withDiagnostics({
        error: "Screener unavailable because runtime Postgres snapshot is unavailable or empty.",
        snapshotFailures: snapshot.failures,
        tab,
        ...publicationContractFields(publicationState),
      }, "snapshot_unavailable"),
      { status: 503 },
    );
  }

  const quoteLoadStartedAtMs = Date.now();
  const quoteCache = await loadRuntimeQuoteCacheFromPostgres();
  phaseTimings.quote_load_ms = Date.now() - quoteLoadStartedAtMs;
  const publicationState = await loadCanonicalPublicationState({
    snapshot: {
      available: true,
      runId: snapshot.runId,
      generatedAtUtc: snapshot.generatedAtUtc,
    },
    quote: {
      available: Boolean(quoteCache.sourcePath && Object.keys(quoteCache.quotes).length > 0),
      runId: quoteCache.runId,
    },
  });
  const publicationFields = publicationContractFields(publicationState);

  if (!quoteCache.sourcePath || Object.keys(quoteCache.quotes).length === 0) {
    return NextResponse.json(withDiagnostics({
        error: "Screener unavailable because runtime Postgres quote cache is unavailable or empty.",
        quoteFailures: quoteCache.failures,
        tab,
        ...publicationFields,
      }, "quote_cache_unavailable"),
      { status: 503 },
    );
  }

  if (publicationState.servingState === "blocked") {
    return NextResponse.json(withDiagnostics({
        error: "Screener unavailable because canonical publication state blocked this response.",
        blocked: true,
        status: "blocked",
        tab,
        ...publicationFields,
      }, "publication_state_blocked"),
      { status: 503 },
    );
  }

  const publishedDecisionLoad = await loadPublishedDecisionMapForRows(publicationState.runId, snapshot.rows);
  if (!publishedDecisionLoad.ok) {
    return NextResponse.json(withDiagnostics({
        error: "Screener unavailable because persisted published decision provenance is missing or invalid.",
        blocked: true,
        status: "blocked",
        tab,
        ...publicationFields,
        provenance: {
          sourcePath: publishedDecisionLoad.sourcePath,
          failureCount: publishedDecisionLoad.failures.length,
          rows_required: publishedDecisionLoad.rowsRequired,
          rows_valid: publishedDecisionLoad.rowsValid,
          missingTickers: publishedDecisionLoad.missingTickers,
          invalidTickers: publishedDecisionLoad.invalidTickers,
        },
      }, "persisted_provenance_unavailable"),
      { status: 503 },
    );
  }

  const quoteCacheQuotes: Record<string, ScreenerQuoteCacheRow> = quoteCache.quotes;
  const quoteCacheSource: string | null = quoteCache.sourcePath;
  const quoteCacheFailureCount = quoteCache.failures.length;
  const profileOverrides = loadScreenerProfileOverrides().rows;

  const mapFilterStartedAtMs = Date.now();
  const mappedRows = snapshot.rows
    .map((row) => toScreenerRow(row, quoteCacheQuotes, publishedDecisionLoad.rows))
    .filter((row): row is ScreenerRow => row !== null);

  let filtered = filterRows(mappedRows, {
    tab,
    search,
    decision,
    regime,
    assetType,
    minPrice,
    maxPrice,
    minBars,
    maxBars,
  });
  phaseTimings.map_filter_ms = Date.now() - mapFilterStartedAtMs;

  const advancedEnabled = hasAdvancedFilters(advancedFilters);
  let advancedExternalContext: AdvancedExternalFilterContext = {
    countryRegionTickers: null,
    themeTickers: null,
    subThemeTickers: null,
    compositeFilterToken: null,
    compositeSignalToken: null,
    compositeTickers: null,
    compositeOrderedTickers: null,
  };

  if (advancedEnabled || signal.trim()) {
    const advancedExternalStartedAtMs = Date.now();
    advancedExternalContext = await resolveAdvancedExternalContext(advancedFilters, signal);
    filtered = filtered.filter((row) => matchAdvancedFilters(row, quoteCacheQuotes[row.ticker], advancedFilters, advancedExternalContext));
    phaseTimings.advanced_external_ms = Date.now() - advancedExternalStartedAtMs;
  }

  let mapTickers = [] as ReturnType<typeof buildMapTickers>;
  let mapCells = [] as ReturnType<typeof buildMapCells>;
  if (includeMap) {
    const mapBuildStartedAtMs = Date.now();
    mapTickers = buildMapTickers(filtered, quoteCacheQuotes, profileOverrides);
    mapCells = buildMapCells(filtered, quoteCacheQuotes, profileOverrides);
    phaseTimings.map_build_ms = Date.now() - mapBuildStartedAtMs;
  }

  const sortPageStartedAtMs = Date.now();
  const sorted = sortRows(filtered, quoteCacheQuotes, sortKey, sortDir);

  const total = sorted.length;
  const totalPages = total > 0 ? Math.ceil(total / pageSize) : 1;
  const safePage = Math.min(page, totalPages);
  const start = (safePage - 1) * pageSize;
  const rows = sorted.slice(start, start + pageSize);
  const pageQuotes = Object.fromEntries(rows.map((row) => [row.ticker, quoteCacheQuotes[row.ticker] ?? {}]));

  const regimeValues = Array.from(new Set(mappedRows.map((row) => row.regime))).sort((a, b) => a.localeCompare(b));
  phaseTimings.sort_page_ms = Date.now() - sortPageStartedAtMs;

  return NextResponse.json(withDiagnostics({
    ...publicationFields,
    tab,
    page: safePage,
    pageSize,
    total,
    totalPages,
    sort: {
      key: sortKey,
      direction: sortDir,
    },
    filters: {
      search,
      decision,
      signal,
      filterGroup,
      regime,
      assetType,
      minPrice,
      maxPrice,
      minBars,
      maxBars,
      ...advancedFilters,
    },
    rows,
    pageQuotes,
    mapTickers,
    mapCells,
    source: snapshot.sourcePath,
    data_source: snapshot.dataSource,
    run_id: snapshot.runId,
    generated_at_utc: snapshot.generatedAtUtc,
    snapshotFailures: snapshot.failures,
    advancedFilterCache: {
      enabled: advancedEnabled,
      sourcePath: quoteCacheSource,
      failureCount: quoteCacheFailureCount,
    },
    advancedFilterExternal: {
      sourceConfigured: Boolean(EXTERNAL_FILTER_SOURCE_BASE_URL),
      composite: externalFilterDiagnostics(
        advancedExternalContext.compositeFilterToken || advancedExternalContext.compositeSignalToken,
        advancedExternalContext.compositeTickers,
      ),
      country: externalFilterDiagnostics(
        COUNTRY_REGION_FILTERS.has(advancedFilters.country) && advancedFilters.country !== "custom_subscription"
          ? `geo_${advancedFilters.country}`
          : null,
        advancedExternalContext.countryRegionTickers,
      ),
      theme: externalFilterDiagnostics(
        advancedFilters.theme && advancedFilters.theme !== "custom_subscription" ? `theme_${advancedFilters.theme}` : null,
        advancedExternalContext.themeTickers,
      ),
      subTheme: externalFilterDiagnostics(
        advancedFilters.subTheme && advancedFilters.subTheme !== "custom_subscription" ? `subtheme_${advancedFilters.subTheme}` : null,
        advancedExternalContext.subThemeTickers,
      ),
    },
    options: {
      regimes: regimeValues,
      assetTypes: ["equities", "index", "crypto", "etf", "other"],
      decisions: ["Accumulate", "Hold", "Avoid"],
      tabs: ["overview", "valuation", "financial", "ownership", "performance", "technical", "etf"],
      sortKeys: ["ticker", "assetType", "price", "company", "sector", "industry", "country", "marketcap", "change", "volume"],
    },
    orderOptions: SCREENER_ORDER_OPTIONS.filter((option) =>
      ["ticker", "assetType", "price", "company", "sector", "industry", "country", "marketcap", "change", "volume"].includes(option.value),
    ),
    signalOptions: SCREENER_SIGNAL_OPTIONS,
    advancedFilterOptions: ADVANCED_FILTER_OPTIONS,
    filterGroupLayouts: SCREENER_FILTER_GROUP_LAYOUTS,
  }, "complete"));
}
