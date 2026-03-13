"use client";

import { useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import ScreenerChart, {
  DEFAULT_SCREENER_CHART_CONTROLS,
  type ScreenerChartControls,
  type ScreenerChartInterval,
  type ScreenerChartRange,
  type MarketTimeframe,
} from "@/components/ScreenerChart";
import ClientPortal from "@/components/ClientPortal";
import { buildMarketStatColumns, type MarketQuoteSummary } from "@/lib/market-analysis";
import {
  SCREENER_FILTER_FIELDS,
  SCREENER_FILTER_GROUP_LAYOUTS,
  SCREENER_ORDER_OPTIONS,
  SCREENER_SIGNAL_OPTIONS,
  type ScreenerFilterGroup,
  type ScreenerFilterOption,
} from "@/lib/screener-filter-schema-v111";

type ScreenerTab = "overview" | "valuation" | "financial" | "ownership" | "performance" | "technical" | "etf";
type ScreenerDataTab =
  | ScreenerTab
  | "etfPerf"
  | "basic"
  | "ta"
  | "newsTab"
  | "maps";
type Decision = "Accumulate" | "Hold" | "Avoid";
type AssetType = "equities" | "index" | "crypto" | "etf" | "other";
type SortDirection = "asc" | "desc";
type MapDataType = "1d" | "1w" | "1m" | "3m" | "6m" | "ytd" | "1y";

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

type SortKey = string;

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

type MapRect = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type MapSectorModel = {
  id: string;
  sector: string;
  marketCap: number;
  volume: number;
  tickers: number;
  avgChangePct: number | null;
  industries: MapIndustryModel[];
  leaders: ScreenerMapTicker[];
};

type MapIndustryModel = {
  id: string;
  sector: string;
  industry: string;
  marketCap: number;
  volume: number;
  tickers: number;
  avgChangePct: number | null;
  symbols: ScreenerMapTicker[];
};

type MapDetailModel = {
  id: string;
  kind: "sector" | "industry" | "ticker";
  sector: string;
  industry: string;
  ticker: string;
  name: string;
  companyName: string | null;
  marketCap: number;
  volume: number;
  tickers: number;
  changePct: number | null;
  price: number | null;
  members: ScreenerMapTicker[];
};

type MapTickerLayout = {
  ticker: ScreenerMapTicker;
  rect: MapRect;
};

type MapIndustryLayout = {
  industry: MapIndustryModel;
  rect: MapRect;
  headerHeight: number;
  tickers: MapTickerLayout[];
};

type MapSectorLayout = {
  sector: MapSectorModel;
  rect: MapRect;
  headerHeight: number;
  industries: MapIndustryLayout[];
};

type ScreenerResponse = {
  tab: ScreenerTab;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  rows: ScreenerRow[];
  pageQuotes?: Record<string, QuoteSummary>;
  mapCells?: ScreenerMapCell[];
  mapTickers?: ScreenerMapTicker[];
  options: {
    regimes: string[];
    assetTypes: AssetType[];
    decisions: Decision[];
    tabs: ScreenerTab[];
    sortKeys: string[];
  };
  advancedFilterExternal?: {
    sourceConfigured?: boolean;
    country?: {
      requested?: string | null;
      sourceConfigured?: boolean;
      resolved?: boolean;
      tickerCount?: number | null;
    };
    theme?: {
      requested?: string | null;
      sourceConfigured?: boolean;
      resolved?: boolean;
      tickerCount?: number | null;
    };
    subTheme?: {
      requested?: string | null;
      sourceConfigured?: boolean;
      resolved?: boolean;
      tickerCount?: number | null;
    };
  };
  error?: string;
};

type ChartBar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type ChartSummary = {
  open: number;
  high: number;
  low: number;
  prevClose: number;
  close: number;
  change: number;
  changePct: number;
  high52: number;
  low52: number;
};

type NewsItem = {
  title: string;
  publisher: string;
  link: string;
  publishedAt: number | null;
  relatedTickers: string[];
};

type QuoteSummary = MarketQuoteSummary & {
  news?: NewsItem[];
  newsFetched?: boolean;
  newsHeadline?: string | null;
  newsPublisher?: string | null;
  newsPublishedAt?: number | null;
  newsLink?: string | null;
  newsCount?: number | null;
  miniBars?: ChartBar[];
  miniChartFetched?: boolean;
  miniChartInterval?: string | null;
  miniChartRange?: string | null;
  miniChartNote?: string | null;
};

type ChartResponse = {
  ticker: string;
  bars: ChartBar[];
  summary: ChartSummary | null;
  quote?: QuoteSummary;
  news?: NewsItem[];
  interval?: string;
  range?: string;
  note?: string | null;
  error?: string;
};

type AdvancedFilterState = Record<string, string>;
type AdvancedFilterKey = string;

type ScreenerPresetState = {
  tab: ScreenerTab;
  dataTab: ScreenerDataTab;
  filterGroup: ScreenerFilterGroup;
  search: string;
  assetType: string;
  signal: string;
  minPrice: string;
  maxPrice: string;
  minBars: string;
  maxBars: string;
  sortKey: SortKey;
  sortDir: SortDirection;
  pageSize: number;
  advancedFilters: AdvancedFilterState;
};

type ScreenerPresetRecord = {
  id: string;
  name: string;
  createdAtUtc: string;
  updatedAtUtc: string;
  state: ScreenerPresetState;
};

type ScreenerTableColumn = {
  id: string;
  label: string;
  align?: "left" | "right";
  render: (row: ScreenerRow, quote: QuoteSummary) => ReactNode;
};

type FlyoutRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const FILTER_GROUPS: Array<{ id: ScreenerFilterGroup; label: string }> = [
  { id: "descriptive", label: "Descriptive" },
  { id: "fundamental", label: "Fundamental" },
  { id: "technical", label: "Technical" },
  { id: "news", label: "News" },
  { id: "etf", label: "ETF" },
  { id: "all", label: "All" },
];

const DATA_TABS: Array<{ key: ScreenerDataTab; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "valuation", label: "Valuation" },
  { key: "financial", label: "Financial" },
  { key: "ownership", label: "Ownership" },
  { key: "performance", label: "Performance" },
  { key: "technical", label: "Technical" },
  { key: "etf", label: "ETF" },
  { key: "etfPerf", label: "ETF Perf" },
  { key: "basic", label: "Basic" },
  { key: "ta", label: "TA" },
  { key: "newsTab", label: "News" },
  { key: "maps", label: "Maps" },
];

const API_DATA_TABS: ReadonlyArray<ScreenerTab> = ["overview", "valuation", "financial", "ownership", "performance", "technical", "etf"];

const FLYOUT_MAX_WIDTH = 1160;
const FLYOUT_MAX_HEIGHT = 900;
const FLYOUT_MIN_WIDTH = 760;
const FLYOUT_MIN_HEIGHT = 460;
const FLYOUT_MARGIN_DESKTOP = 14;
const FLYOUT_MARGIN_MOBILE = 6;
const NEWS_PANEL_DEFAULT_CONTROLS: ScreenerChartControls = {
  ...DEFAULT_SCREENER_CHART_CONTROLS,
  interval: "1d",
  timeframe: "daily",
  range: "1y",
};

const ADVANCED_FILTER_OPTIONS: Record<AdvancedFilterKey, ScreenerFilterOption[]> = Object.fromEntries(
  Object.entries(SCREENER_FILTER_FIELDS).map(([key, field]) => [key, field.options]),
);

const ADVANCED_FILTER_DEFAULTS: AdvancedFilterState = Object.fromEntries(
  Object.keys(SCREENER_FILTER_FIELDS).map((key) => [key, ""]),
);

const MAP_DATA_TYPE_OPTIONS: Array<{ value: MapDataType; label: string }> = [
  { value: "1d", label: "1-Day Performance" },
  { value: "1w", label: "1-Week Performance" },
  { value: "1m", label: "1-Month Performance" },
  { value: "3m", label: "3-Month Performance" },
  { value: "6m", label: "6-Month Performance" },
  { value: "ytd", label: "YTD Performance" },
  { value: "1y", label: "1-Year Performance" },
];

const SUPPORTED_ORDER_KEYS = new Set<string>(["ticker", "assetType", "price", "company", "sector", "industry", "country", "marketcap", "change", "volume"]);
const TA_MINI_CHART_RETRY_INTERVAL_MS = 1500;
const TA_MINI_CHART_ATTEMPT_CAP = 20;
const TA_MINI_CHART_FETCH_CONCURRENCY = 10;
const SCREENER_LOAD_MAX_ATTEMPTS = 3;
const SCREENER_LOAD_RETRY_DELAY_MS = 300;
const SUPPORTED_ORDER_OPTIONS = SCREENER_ORDER_OPTIONS.filter((option) => SUPPORTED_ORDER_KEYS.has(option.value));
const COLUMN_SORT_KEY_BY_ID: Record<string, SortKey> = {
  ticker: "ticker",
  assetType: "assetType",
  company: "company",
  sector: "sector",
  industry: "industry",
  country: "country",
  marketCap: "marketcap",
  price: "price",
  change: "change",
  volume: "volume",
};
const SCREENER_PRESETS_STORAGE_KEY = "tfe_screener_presets_v1";
const SCREENER_PRESET_MAX_COUNT = 30;
const PRESET_ACTION_SAVE = "__action_save_screen__";
const PRESET_ACTION_EDIT = "__action_edit_screens__";

const MAP_DATA_TYPE_KEYS: Record<MapDataType, string[]> = {
  "1d": ["changePct"],
  "1w": ["perfWeek", "changePct"],
  "1m": ["perfMonth", "changePct"],
  "3m": ["perfQuarter", "changePct"],
  "6m": ["perfHalf", "changePct"],
  ytd: ["perfYtd", "changePct"],
  "1y": ["perfYear", "changePct"],
};

function resolveApiTabForDataTab(tab: ScreenerTab, dataTab: ScreenerDataTab): ScreenerTab {
  if (API_DATA_TABS.includes(dataTab as ScreenerTab)) return dataTab as ScreenerTab;
  if (dataTab === "etfPerf") return "etf";
  if (dataTab === "ta") return "technical";
  if (dataTab === "newsTab") return "performance";
  if (dataTab === "basic" || dataTab === "maps") return "overview";
  return tab;
}

function normalizeText(value: string | null | undefined): string {
  if (!value) return "";
  return value.trim().toUpperCase();
}

function sleepMs(delayMs: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, Math.max(0, Math.floor(delayMs)));
  });
}

function shouldRetryScreenerLoad(statusCode: number, errorMessage: string): boolean {
  if (statusCode !== 503) return false;
  const message = String(errorMessage || "").toLowerCase();
  if (!message) return false;
  return message.includes("runtime postgres quote cache is unavailable or empty") || message.includes("runtime postgres snapshot is unavailable or empty");
}

type EasternDateParts = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
};

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

const COUNTRY_REGION_PASSTHROUGH = new Set(["asia", "europe", "latinamerica", "bric", "benelux", "chinahongkong"]);

function isFiniteValue(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function optionLabelFor(key: AdvancedFilterKey, value: string): string {
  if (!value) return "";
  const option = ADVANCED_FILTER_OPTIONS[key].find((entry) => entry.value === value);
  return option?.label ?? value;
}

function parseUnderOver(bucket: string): { kind: "under" | "over"; threshold: number } | null {
  if (bucket.length < 2) return null;
  const prefix = bucket[0];
  if (prefix !== "u" && prefix !== "o") return null;
  const threshold = Number(bucket.slice(1));
  if (!Number.isFinite(threshold)) return null;
  return { kind: prefix === "u" ? "under" : "over", threshold };
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
  if (COUNTRY_REGION_PASSTHROUGH.has(filter)) return true;

  const expectedLabel = optionLabelFor("country", filter);
  if (!expectedLabel || normalizeText(expectedLabel) === "ANY") return true;
  return country === normalizeText(expectedLabel);
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

  if (bucket === "add_tad_0_close::close:d") return true;

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

function matchOptionShortFilter(optionable: boolean | null | undefined, shortable: boolean | null | undefined, bucket: string): boolean {
  if (!bucket || bucket === "custom_subscription") return true;
  if (bucket === "option") return optionable === true;
  if (bucket === "short") return shortable === true;
  if (bucket === "notoption") return optionable === false;
  if (bucket === "notshort") return shortable === false;
  if (bucket === "optionshort") return optionable === true && shortable === true;
  if (bucket === "optionnotshort") return optionable === true && shortable === false;
  if (bucket === "notoptionshort") return optionable === false && shortable === true;
  if (bucket === "notoptionnotshort") return optionable === false && shortable === false;
  return true;
}

function matchTradesFilter(_bucket: string): boolean {
  return true;
}

function matchThemeFilter(_bucket: string): boolean {
  return true;
}

function matchSubThemeFilter(_bucket: string): boolean {
  return true;
}

const EMPTY_MAP_TAXONOMY_LABELS = new Set(["", "NONE", "NULL", "N/A", "NA", "UNCLASSIFIED", "UNKNOWN"]);

function normalizeMapTaxonomyLabel(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  if (!text) return null;
  if (EMPTY_MAP_TAXONOMY_LABELS.has(text.toUpperCase())) return null;
  return text;
}

function isMapEtfTicker(ticker: ScreenerMapTicker): boolean {
  const quoteType = String(ticker.quoteType ?? "")
    .trim()
    .toUpperCase();
  const industry = String(ticker.industry ?? "")
    .trim()
    .toUpperCase();
  return ticker.assetType === "etf" || quoteType.includes("ETF") || quoteType.includes("FUND") || industry === "EXCHANGE TRADED FUND";
}

function resolveMapTickerTaxonomy(ticker: ScreenerMapTicker): { sector: string; industry: string } {
  const sector = normalizeMapTaxonomyLabel(ticker.sector);
  const industry = normalizeMapTaxonomyLabel(ticker.industry);
  if (sector && industry) return { sector, industry };

  if (ticker.assetType === "crypto") {
    return { sector: "Cryptocurrency", industry: "Digital Assets" };
  }
  if (ticker.assetType === "index") {
    return { sector: "Index", industry: "Market Index" };
  }
  if (isMapEtfTicker(ticker)) {
    return { sector: "ETF", industry: "Exchange Traded Fund" };
  }

  return {
    sector: sector ?? "Unclassified",
    industry: industry ?? "Unclassified",
  };
}

function mapToneClass(changePct: number | null): string {
  if (!isFiniteValue(changePct)) return "is-neutral";
  if (changePct >= 3) return "is-strong-up";
  if (changePct > 0) return "is-up";
  if (changePct <= -3) return "is-strong-down";
  if (changePct < 0) return "is-down";
  return "is-neutral";
}

function heatColorForChangePct(changePct: number | null): string {
  if (!isFiniteValue(changePct)) return "hsl(213 18% 30%)";
  const bounded = clampNumber(changePct, -6, 6);
  if (bounded > 0) {
    const ratio = bounded / 6;
    const light = 42 - ratio * 16;
    const sat = 46 + ratio * 25;
    return `hsl(145 ${sat}% ${light}%)`;
  }
  if (bounded < 0) {
    const ratio = Math.abs(bounded) / 6;
    const light = 42 - ratio * 14;
    const sat = 48 + ratio * 23;
    return `hsl(3 ${sat}% ${light}%)`;
  }
  return "hsl(213 14% 34%)";
}

function mapHeaderColorForChangePct(changePct: number | null): string {
  if (!isFiniteValue(changePct)) return "hsl(214 18% 22%)";
  const bounded = clampNumber(changePct, -6, 6);
  if (bounded > 0) {
    const ratio = bounded / 6;
    return `hsl(148 ${56 + ratio * 18}% ${25 - ratio * 6}%)`;
  }
  if (bounded < 0) {
    const ratio = Math.abs(bounded) / 6;
    return `hsl(4 ${62 + ratio * 16}% ${27 - ratio * 6}%)`;
  }
  return "hsl(214 20% 24%)";
}

function mapSizeValue(ticker: ScreenerMapTicker): number {
  if (ticker.marketCap > 0) return ticker.marketCap;
  const dollarFlow = (ticker.price ?? 0) * ticker.volume;
  if (dollarFlow > 0) return dollarFlow;
  return 1;
}

function insetRect(rect: MapRect, pad: number): MapRect {
  const width = Math.max(0, rect.width - pad * 2);
  const height = Math.max(0, rect.height - pad * 2);
  return {
    x: rect.x + pad,
    y: rect.y + pad,
    width,
    height,
  };
}

function mapRectStyle(rect: MapRect): { left: number; top: number; width: number; height: number } {
  return {
    left: Math.round(rect.x * 100) / 100,
    top: Math.round(rect.y * 100) / 100,
    width: Math.round(rect.width * 100) / 100,
    height: Math.round(rect.height * 100) / 100,
  };
}

function mapRectStyleRelative(rect: MapRect, parent: MapRect): { left: number; top: number; width: number; height: number } {
  return mapRectStyle({
    x: rect.x - parent.x,
    y: rect.y - parent.y,
    width: rect.width,
    height: rect.height,
  });
}

function normalizeTreemapItems<T>(items: Array<{ value: number; data: T }>, totalArea: number): Array<{ area: number; data: T }> {
  const positive = items
    .map((item) => ({
      value: Number.isFinite(item.value) && item.value > 0 ? item.value : 0,
      data: item.data,
    }))
    .filter((item) => item.value > 0);

  if (positive.length === 0) return [];
  const total = positive.reduce((sum, item) => sum + item.value, 0);
  if (total <= 0 || totalArea <= 0) return [];
  return positive
    .map((item) => ({ data: item.data, area: (item.value / total) * totalArea }))
    .sort((a, b) => b.area - a.area);
}

function splitIndexByArea<T>(items: Array<{ area: number; data: T }>): number {
  if (items.length <= 1) return items.length;
  const total = items.reduce((sum, item) => sum + item.area, 0);
  const target = total / 2;
  let running = 0;
  let bestIndex = 1;
  let bestDiff = Number.POSITIVE_INFINITY;

  for (let index = 1; index < items.length; index += 1) {
    running += items[index - 1].area;
    const diff = Math.abs(target - running);
    if (diff < bestDiff) {
      bestDiff = diff;
      bestIndex = index;
    }
  }

  return bestIndex;
}

function layoutTreemap<T>(items: Array<{ value: number; data: T }>, rect: MapRect): Array<{ data: T; rect: MapRect }> {
  const totalArea = Math.max(0, rect.width) * Math.max(0, rect.height);
  const normalized = normalizeTreemapItems(items, totalArea);
  if (normalized.length === 0) return [];

  const out: Array<{ data: T; rect: MapRect }> = [];
  const place = (nodes: Array<{ area: number; data: T }>, frame: MapRect, depth: number): void => {
    if (nodes.length === 0) return;
    if (nodes.length === 1) {
      out.push({
        data: nodes[0].data,
        rect: {
          x: frame.x,
          y: frame.y,
          width: Math.max(0, frame.width),
          height: Math.max(0, frame.height),
        },
      });
      return;
    }

    const split = splitIndexByArea(nodes);
    const left = nodes.slice(0, split);
    const right = nodes.slice(split);
    const leftArea = left.reduce((sum, item) => sum + item.area, 0);
    const total = nodes.reduce((sum, item) => sum + item.area, 0);
    const ratio = total > 0 ? leftArea / total : 0.5;

    const horizontal = depth % 2 === 0 ? frame.width >= frame.height : frame.width < frame.height;
    if (horizontal) {
      const leftWidth = frame.width * ratio;
      place(
        left,
        {
          x: frame.x,
          y: frame.y,
          width: leftWidth,
          height: frame.height,
        },
        depth + 1,
      );
      place(
        right,
        {
          x: frame.x + leftWidth,
          y: frame.y,
          width: Math.max(0, frame.width - leftWidth),
          height: frame.height,
        },
        depth + 1,
      );
      return;
    }

    const topHeight = frame.height * ratio;
    place(
      left,
      {
        x: frame.x,
        y: frame.y,
        width: frame.width,
        height: topHeight,
      },
      depth + 1,
    );
    place(
      right,
      {
        x: frame.x,
        y: frame.y + topHeight,
        width: frame.width,
        height: Math.max(0, frame.height - topHeight),
      },
      depth + 1,
    );
  };

  place(normalized, rect, 0);

  return out.filter((item) => item.rect.width > 0.08 && item.rect.height > 0.08);
}

function fmtNum(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return value.toFixed(decimals);
}

function clampNumber(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

function flyoutMargin(viewportWidth: number): number {
  return viewportWidth <= 920 ? FLYOUT_MARGIN_MOBILE : FLYOUT_MARGIN_DESKTOP;
}

function clampFlyoutRect(rect: FlyoutRect, viewportWidth: number, viewportHeight: number): FlyoutRect {
  const margin = flyoutMargin(viewportWidth);
  const maxWidth = Math.max(320, viewportWidth - margin * 2);
  const maxHeight = Math.max(260, viewportHeight - margin * 2);
  const minWidth = Math.min(FLYOUT_MIN_WIDTH, maxWidth);
  const minHeight = Math.min(FLYOUT_MIN_HEIGHT, maxHeight);
  const width = clampNumber(rect.width, minWidth, Math.min(FLYOUT_MAX_WIDTH, maxWidth));
  const height = clampNumber(rect.height, minHeight, Math.min(FLYOUT_MAX_HEIGHT, maxHeight));

  return {
    left: clampNumber(rect.left, margin, viewportWidth - margin - width),
    top: clampNumber(rect.top, margin, viewportHeight - margin - height),
    width,
    height,
  };
}

function defaultFlyoutRect(viewportWidth: number, viewportHeight: number): FlyoutRect {
  const margin = flyoutMargin(viewportWidth);
  const width = Math.min(FLYOUT_MAX_WIDTH, Math.max(Math.min(FLYOUT_MIN_WIDTH, viewportWidth - margin * 2), viewportWidth - margin * 2));
  const height = Math.min(FLYOUT_MAX_HEIGHT, Math.max(Math.min(FLYOUT_MIN_HEIGHT, viewportHeight - margin * 2), viewportHeight - margin * 2));

  return clampFlyoutRect(
    {
      left: Math.round((viewportWidth - width) / 2),
      top: Math.max(margin, Math.round((viewportHeight - height) / 2)),
      width,
      height,
    },
    viewportWidth,
    viewportHeight,
  );
}

function maximizedFlyoutRect(viewportWidth: number, viewportHeight: number): FlyoutRect {
  const margin = flyoutMargin(viewportWidth);
  return clampFlyoutRect(
    {
      left: margin,
      top: margin,
      width: viewportWidth - margin * 2,
      height: viewportHeight - margin * 2,
    },
    viewportWidth,
    viewportHeight,
  );
}

function fmtPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function fmtCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "n/a";
  const n = value;
  if (Math.abs(n) >= 1_000_000_000_000) return `${(n / 1_000_000_000_000).toFixed(2)}T`;
  if (Math.abs(n) >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(2);
}

function toDecisionClass(value: Decision): "accumulate" | "hold" | "avoid" {
  if (value === "Accumulate") return "accumulate";
  if (value === "Avoid") return "avoid";
  return "hold";
}

function formatAssetType(value: AssetType): string {
  if (value === "equities") return "Equities";
  if (value === "index") return "Index";
  if (value === "crypto") return "Crypto";
  if (value === "etf") return "ETF";
  return "Other";
}

function normalizeChartInterval(value: string | undefined, fallback: ScreenerChartInterval): ScreenerChartInterval {
  if (value === "1m") return "1m";
  if (value === "5m") return "5m";
  if (value === "15m") return "15m";
  if (value === "30m") return "30m";
  if (value === "60m") return "60m";
  if (value === "1wk") return "1wk";
  if (value === "1mo") return "1mo";
  if (value === "1d") return "1d";
  return fallback;
}

function normalizeChartRange(value: string | undefined, fallback: ScreenerChartRange): ScreenerChartRange {
  if (value === "1d") return "1d";
  if (value === "5d") return "5d";
  if (value === "1mo") return "1mo";
  if (value === "3mo") return "3mo";
  if (value === "6mo") return "6mo";
  if (value === "ytd") return "ytd";
  if (value === "1y") return "1y";
  if (value === "2y") return "2y";
  if (value === "5y") return "5y";
  if (value === "max") return "max";
  return fallback;
}

function timeframeFromInterval(interval: ScreenerChartInterval): MarketTimeframe {
  if (interval === "1wk") return "weekly";
  if (interval === "1mo") return "monthly";
  if (interval === "1d") return "daily";
  return "intraday";
}

function fmtText(value: string | null | undefined): string {
  if (!value) return "n/a";
  return value;
}

function toPresetName(raw: string): string {
  const trimmed = String(raw ?? "").trim();
  return trimmed.slice(0, 80);
}

function readScreenerPresets(): ScreenerPresetRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(SCREENER_PRESETS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const out: ScreenerPresetRecord[] = [];
    for (const entry of parsed) {
      if (!entry || typeof entry !== "object") continue;
      const record = entry as Partial<ScreenerPresetRecord>;
      const state = record.state;
      if (!state || typeof state !== "object") continue;
      const name = toPresetName(String(record.name ?? ""));
      if (!name) continue;
      const id = String(record.id ?? "").trim();
      if (!id) continue;
      out.push({
        id,
        name,
        createdAtUtc: String(record.createdAtUtc ?? ""),
        updatedAtUtc: String(record.updatedAtUtc ?? ""),
        state: {
          tab: (state.tab as ScreenerTab) ?? "overview",
          dataTab: (state.dataTab as ScreenerDataTab) ?? "overview",
          filterGroup: (state.filterGroup as ScreenerFilterGroup) ?? "descriptive",
          search: String(state.search ?? ""),
          assetType: String(state.assetType ?? ""),
          signal: String(state.signal ?? ""),
          minPrice: String(state.minPrice ?? ""),
          maxPrice: String(state.maxPrice ?? ""),
          minBars: String(state.minBars ?? ""),
          maxBars: String(state.maxBars ?? ""),
          sortKey: String(state.sortKey ?? "ticker"),
          sortDir: state.sortDir === "desc" ? "desc" : "asc",
          pageSize: Number.isFinite(Number(state.pageSize)) ? Math.max(10, Math.min(200, Number(state.pageSize))) : 25,
          advancedFilters:
            state.advancedFilters && typeof state.advancedFilters === "object"
              ? (state.advancedFilters as AdvancedFilterState)
              : { ...ADVANCED_FILTER_DEFAULTS },
        },
      });
    }
    return out.slice(0, SCREENER_PRESET_MAX_COUNT);
  } catch {
    return [];
  }
}

function writeScreenerPresets(records: ScreenerPresetRecord[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      SCREENER_PRESETS_STORAGE_KEY,
      JSON.stringify(records.slice(0, SCREENER_PRESET_MAX_COUNT)),
    );
  } catch {
    // Intentionally ignore localStorage write failures.
  }
}

function inferTone(value: string): "up" | "down" | null {
  const v = value.trim();
  if (v.startsWith("+")) return "up";
  if (v.startsWith("-")) return "down";
  return null;
}

function pathFromPoints(points: Array<{ x: number; y: number }>): string {
  if (points.length === 0) return "";
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(" ");
}

function miniSparklineFromBars(
  bars: ChartBar[],
  options?: {
    width?: number;
    height?: number;
    padX?: number;
    padY?: number;
    limit?: number;
  },
): {
  path: string;
  tone: "up" | "down" | "flat";
  deltaPct: number | null;
  width: number;
  height: number;
} | null {
  if (!Array.isArray(bars) || bars.length < 2) return null;

  const width = Number.isFinite(Number(options?.width)) ? Math.max(32, Number(options?.width)) : 116;
  const height = Number.isFinite(Number(options?.height)) ? Math.max(20, Number(options?.height)) : 30;
  const padX = Number.isFinite(Number(options?.padX)) ? Math.max(0, Number(options?.padX)) : 2;
  const padY = Number.isFinite(Number(options?.padY)) ? Math.max(0, Number(options?.padY)) : 2;
  const limit = Number.isFinite(Number(options?.limit)) ? Math.max(12, Math.floor(Number(options?.limit))) : 80;

  const closes = bars
    .map((bar) => Number(bar.close))
    .filter((value) => Number.isFinite(value))
    .slice(-limit);
  if (closes.length < 2) return null;

  const minClose = Math.min(...closes);
  const maxClose = Math.max(...closes);
  const span = Math.max(maxClose - minClose, 0.0000001);

  const points = closes.map((close, index) => {
    const x = padX + (index / Math.max(closes.length - 1, 1)) * (width - padX * 2);
    const normalized = (close - minClose) / span;
    const y = height - padY - normalized * (height - padY * 2);
    return { x, y };
  });

  const first = closes[0];
  const last = closes[closes.length - 1];
  const deltaPct = first === 0 ? null : ((last - first) / first) * 100;
  let tone: "up" | "down" | "flat" = "flat";
  if (deltaPct !== null) {
    if (deltaPct > 0.05) tone = "up";
    if (deltaPct < -0.05) tone = "down";
  }

  return {
    path: pathFromPoints(points),
    tone,
    deltaPct,
    width,
    height,
  };
}

type MiniTaCandle = {
  x: number;
  openY: number;
  closeY: number;
  highY: number;
  lowY: number;
  rising: boolean;
  bodyHeight: number;
  bodyTop: number;
};

type MiniTaChartModel = {
  width: number;
  height: number;
  candles: MiniTaCandle[];
  candleBodyWidth: number;
  tone: "up" | "down" | "flat";
  deltaPct: number | null;
  ma20Path: string;
  ma50Path: string;
  ma200Path: string;
  gridLines: number[];
};

function miniTaChartFromBars(
  bars: ChartBar[],
  options?: {
    width?: number;
    height?: number;
    padX?: number;
    padY?: number;
    limit?: number;
  },
): MiniTaChartModel | null {
  if (!Array.isArray(bars) || bars.length < 2) return null;

  const width = Number.isFinite(Number(options?.width)) ? Math.max(160, Number(options?.width)) : 760;
  const height = Number.isFinite(Number(options?.height)) ? Math.max(80, Number(options?.height)) : 182;
  const padX = Number.isFinite(Number(options?.padX)) ? Math.max(0, Number(options?.padX)) : 8;
  const padY = Number.isFinite(Number(options?.padY)) ? Math.max(0, Number(options?.padY)) : 8;
  const limit = Number.isFinite(Number(options?.limit)) ? Math.max(24, Math.floor(Number(options?.limit))) : 120;

  const source = bars
    .slice(-limit)
    .map((bar) => ({
      openRaw: Number(bar.open),
      highRaw: Number(bar.high),
      lowRaw: Number(bar.low),
      closeRaw: Number(bar.close),
    }))
    .map((bar) => {
      const close = Number.isFinite(bar.closeRaw) && bar.closeRaw > 0 ? bar.closeRaw : null;
      if (close === null) return null;

      const open = Number.isFinite(bar.openRaw) && bar.openRaw > 0 ? bar.openRaw : close;
      const highCandidate = Number.isFinite(bar.highRaw) && bar.highRaw > 0 ? bar.highRaw : Math.max(open, close);
      const lowCandidate = Number.isFinite(bar.lowRaw) && bar.lowRaw > 0 ? bar.lowRaw : Math.min(open, close);

      const high = Math.max(highCandidate, open, close);
      const low = Math.min(lowCandidate, open, close);
      return { open, high, low, close };
    })
    .filter((bar): bar is { open: number; high: number; low: number; close: number } => bar !== null);

  if (source.length < 2) return null;

  const minPrice = Math.min(...source.map((bar) => bar.low));
  const maxPrice = Math.max(...source.map((bar) => bar.high));
  const priceSpan = Math.max(maxPrice - minPrice, 0.0000001);
  const plotWidth = Math.max(width - padX * 2, 24);
  const plotHeight = Math.max(height - padY * 2, 24);
  const step = plotWidth / source.length;
  const candleBodyWidth = Math.max(2.0, Math.min(6, step * 0.62));

  const yForPrice = (price: number): number => padY + ((maxPrice - price) / priceSpan) * plotHeight;
  const xForIndex = (index: number): number => padX + (index + 0.5) * step;

  const candles = source.map((bar, index) => {
    const openY = yForPrice(bar.open);
    const closeY = yForPrice(bar.close);
    const highY = yForPrice(bar.high);
    const lowY = yForPrice(bar.low);
    const rising = bar.close >= bar.open;
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(Math.abs(closeY - openY), 1.1);

    return {
      x: xForIndex(index),
      openY,
      closeY,
      highY,
      lowY,
      rising,
      bodyHeight,
      bodyTop,
    };
  });

  const closes = source.map((bar) => bar.close);
  const first = closes[0];
  const last = closes[closes.length - 1];
  const deltaPct = first === 0 ? null : ((last - first) / first) * 100;
  let tone: "up" | "down" | "flat" = "flat";
  if (deltaPct !== null) {
    if (deltaPct > 0.05) tone = "up";
    if (deltaPct < -0.05) tone = "down";
  }

  const movingAveragePath = (period: number): string => {
    if (closes.length < period) return "";
    const points: Array<{ x: number; y: number }> = [];
    for (let index = period - 1; index < closes.length; index += 1) {
      let sum = 0;
      for (let i = index - period + 1; i <= index; i += 1) {
        sum += closes[i];
      }
      const average = sum / period;
      points.push({ x: xForIndex(index), y: yForPrice(average) });
    }
    return pathFromPoints(points);
  };

  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((fraction) => padY + fraction * plotHeight);

  return {
    width,
    height,
    candles,
    candleBodyWidth,
    tone,
    deltaPct,
    ma20Path: movingAveragePath(20),
    ma50Path: movingAveragePath(50),
    ma200Path: movingAveragePath(200),
    gridLines,
  };
}

function fmtPercentFromRatio(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return `${(value * 100).toFixed(decimals)}%`;
}

function fmtPercentSigned(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

function fmtPercentSmart(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const normalized = Math.abs(value) <= 1 ? value * 100 : value;
  const sign = normalized > 0 ? "+" : "";
  return `${sign}${normalized.toFixed(decimals)}%`;
}

function fmtDate(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value) || value <= 0) return "n/a";
  const date = new Date(value * 1000);
  if (Number.isNaN(date.getTime())) return "n/a";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(date);
}

function fmtDateTime(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value) || value <= 0) return "n/a";
  const date = new Date(value * 1000);
  if (Number.isNaN(date.getTime())) return "n/a";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function fmtClockTime(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value) || value <= 0) return "--:--";
  const date = new Date(value * 1000);
  if (Number.isNaN(date.getTime())) return "--:--";
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function fmtNewsDayLabel(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value) || value <= 0) return "Undated";
  const date = new Date(value * 1000);
  if (Number.isNaN(date.getTime())) return "Undated";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(date);
}

function fmtMapAsOfNow(): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
    month: "short",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(new Date());
}

function firstFiniteMetric(quote: QuoteSummary, keys: string[]): number | null {
  const bag = quote as Record<string, unknown>;
  for (const key of keys) {
    const n = Number(bag[key]);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function normalizePercentMetricValue(value: unknown): number | null {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

function metricFromBag(keys: string[], bag: Record<string, unknown> | null | undefined): number | null {
  if (!bag) return null;
  for (const key of keys) {
    const normalized = normalizePercentMetricValue(bag[key]);
    if (normalized !== null) return normalized;
  }
  return null;
}

function resolveMapTickerChangePct(ticker: ScreenerMapTicker, quote: QuoteSummary | undefined, dataType: MapDataType): number | null {
  const keys = MAP_DATA_TYPE_KEYS[dataType];
  const fromTicker = metricFromBag(keys, ticker as Record<string, unknown>);
  if (fromTicker !== null) return fromTicker;
  const fromQuote = metricFromBag(keys, (quote ?? {}) as Record<string, unknown>);
  if (fromQuote !== null) return fromQuote;
  const fallbackTicker = metricFromBag(MAP_DATA_TYPE_KEYS["1d"], ticker as Record<string, unknown>);
  if (fallbackTicker !== null) return fallbackTicker;
  return metricFromBag(MAP_DATA_TYPE_KEYS["1d"], (quote ?? {}) as Record<string, unknown>);
}

function quoteOrDefault(quote: QuoteSummary | undefined): QuoteSummary {
  if (!quote) return {};
  return quote;
}

function optionValueForLabel(key: AdvancedFilterKey, label: string): string {
  const normalized = normalizeText(label);
  if (!normalized) return "";

  const options = ADVANCED_FILTER_OPTIONS[key] ?? [];
  const match = options.find((option) => normalizeText(option.label) === normalized);
  return match?.value ?? "";
}

function hasCoreQuoteData(quote: QuoteSummary | undefined): boolean {
  if (!quote) return false;

  const hasSector = typeof quote.sector === "string" && quote.sector.trim().length > 0;
  const hasIndustry = typeof quote.industry === "string" && quote.industry.trim().length > 0;
  const hasCountry = typeof quote.country === "string" && quote.country.trim().length > 0;
  const hasCategory = typeof quote.category === "string" && quote.category.trim().length > 0;
  const quoteType = String(quote.quoteType ?? quote.assetType ?? "")
    .trim()
    .toUpperCase();

  const hasPrice = Number.isFinite(Number(quote.price));
  const hasVolume = Number.isFinite(Number(quote.volume));

  if (hasSector && hasIndustry && hasCountry) return true;

  if ((quoteType === "ETF" || quoteType === "MUTUALFUND" || quoteType === "MUTUAL FUND") && (hasSector || hasCategory) && hasIndustry && hasCountry) {
    return true;
  }

  if (quoteType === "CRYPTOCURRENCY" && hasPrice && hasVolume) return true;

  if (quoteType === "INDEX" || quoteType === "CURRENCY" || quoteType === "FUTURE") {
    return hasPrice || hasVolume;
  }

  return false;
}

function hasMiniChartData(quote: QuoteSummary | undefined): boolean {
  if (!quote) return false;
  if (!Array.isArray(quote.miniBars)) return false;
  return quote.miniBars.length > 1;
}

function columnsForDataTab(tab: ScreenerDataTab): ScreenerTableColumn[] {
  const byTicker: ScreenerTableColumn = {
    id: "ticker",
    label: "Ticker",
    render: (row) => row.ticker,
  };

  const byCompany: ScreenerTableColumn = {
    id: "company",
    label: "Company",
    render: (row, quote) => fmtText(quote.companyName ?? row.ticker),
  };

  const bySector: ScreenerTableColumn = {
    id: "sector",
    label: "Sector",
    render: (_row, quote) => fmtText(quote.sector),
  };

  const byIndustry: ScreenerTableColumn = {
    id: "industry",
    label: "Industry",
    render: (_row, quote) => fmtText(quote.industry),
  };

  const byCountry: ScreenerTableColumn = {
    id: "country",
    label: "Country",
    render: (_row, quote) => fmtText(quote.country),
  };

  const byNewsHeadline: ScreenerTableColumn = {
    id: "newsHeadline",
    label: "Headline",
    render: (_row, quote) => {
      if (quote.newsHeadline) {
        if (quote.newsLink) {
          return (
            <a className="tfe-news-link" href={quote.newsLink} target="_blank" rel="noreferrer noopener">
              {quote.newsHeadline}
            </a>
          );
        }
        return quote.newsHeadline;
      }
      const top = Array.isArray(quote.news) && quote.news.length > 0 ? quote.news[0] : null;
      if (top?.title && top.link) {
        return (
          <a className="tfe-news-link" href={top.link} target="_blank" rel="noreferrer noopener">
            {top.title}
          </a>
        );
      }
      return fmtText(top?.title);
    },
  };

  const byNewsPublisher: ScreenerTableColumn = {
    id: "newsPublisher",
    label: "Source",
    render: (_row, quote) => {
      if (quote.newsPublisher) return quote.newsPublisher;
      const top = Array.isArray(quote.news) && quote.news.length > 0 ? quote.news[0] : null;
      return fmtText(top?.publisher);
    },
  };

  const byNewsPublished: ScreenerTableColumn = {
    id: "newsPublishedAt",
    label: "Published",
    render: (_row, quote) => {
      if (typeof quote.newsPublishedAt === "number") return fmtDateTime(quote.newsPublishedAt);
      const top = Array.isArray(quote.news) && quote.news.length > 0 ? quote.news[0] : null;
      return fmtDateTime(top?.publishedAt ?? null);
    },
  };

  const byNewsCount: ScreenerTableColumn = {
    id: "newsCount",
    label: "Stories",
    align: "right",
    render: (_row, quote) => {
      if (typeof quote.newsCount === "number") return fmtNum(quote.newsCount, 0);
      return Array.isArray(quote.news) ? fmtNum(quote.news.length, 0) : "0";
    },
  };

  const byMarketCap: ScreenerTableColumn = {
    id: "marketCap",
    label: "Market Cap",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(quote.marketCap),
  };

  const byPrice: ScreenerTableColumn = {
    id: "price",
    label: "Price",
    align: "right",
    render: (row, quote) => fmtPrice(row.price ?? quote.price ?? null),
  };

  const byChange: ScreenerTableColumn = {
    id: "change",
    label: "Change",
    align: "right",
    render: (_row, quote) => fmtPercentSigned(quote.changePct),
  };

  const byMiniChart: ScreenerTableColumn = {
    id: "miniChart",
    label: "Chart",
    render: (_row, quote) => {
      const model = miniSparklineFromBars(Array.isArray(quote.miniBars) ? quote.miniBars : []);
      if (!model) return <span className="tfe-mini-sparkline-empty">n/a</span>;
      const toneClass = model.tone === "up" ? "is-up" : model.tone === "down" ? "is-down" : "is-flat";
      const deltaText = model.deltaPct === null ? "n/a" : fmtPercentSigned(model.deltaPct, 2);

      return (
        <span className={`tfe-mini-sparkline ${toneClass}`} title={`3M ${deltaText}`}>
          <svg viewBox="0 0 116 30" role="img" aria-label={`3-month trend ${deltaText}`}>
            <path d={model.path} />
          </svg>
        </span>
      );
    },
  };

  const byChangeFromOpen: ScreenerTableColumn = {
    id: "changeFromOpen",
    label: "Change from Open",
    align: "right",
    render: (_row, quote) => {
      if (!isFiniteValue(quote.price) || !isFiniteValue(quote.open) || quote.open === 0) return "n/a";
      return fmtPercentSigned(((quote.price - quote.open) / quote.open) * 100);
    },
  };

  const byGap: ScreenerTableColumn = {
    id: "gap",
    label: "Gap",
    align: "right",
    render: (_row, quote) => {
      if (!isFiniteValue(quote.open) || !isFiniteValue(quote.prevClose) || quote.prevClose === 0) return "n/a";
      return fmtPercentSigned(((quote.open - quote.prevClose) / quote.prevClose) * 100);
    },
  };

  const byVolume: ScreenerTableColumn = {
    id: "volume",
    label: "Volume",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(quote.volume),
  };

  const byAvgVolume: ScreenerTableColumn = {
    id: "avgVolume",
    label: "Avg Volume",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(quote.avgVolume),
  };

  const byRelVolume: ScreenerTableColumn = {
    id: "relVolume",
    label: "Rel Volume",
    align: "right",
    render: (_row, quote) => fmtNum(quote.relVolume, 2),
  };

  const byPe: ScreenerTableColumn = {
    id: "pe",
    label: "P/E",
    align: "right",
    render: (_row, quote) => fmtNum(quote.peRatio, 2),
  };

  const byForwardPe: ScreenerTableColumn = {
    id: "forwardPE",
    label: "Forward P/E",
    align: "right",
    render: (_row, quote) => fmtNum(quote.forwardPE, 2),
  };

  const byPeg: ScreenerTableColumn = {
    id: "peg",
    label: "PEG",
    align: "right",
    render: (_row, quote) => fmtNum(quote.pegRatio, 2),
  };

  const byPb: ScreenerTableColumn = {
    id: "pb",
    label: "P/B",
    align: "right",
    render: (_row, quote) => fmtNum(quote.priceToBook, 2),
  };

  const byPs: ScreenerTableColumn = {
    id: "ps",
    label: "P/S",
    align: "right",
    render: (_row, quote) => fmtNum(quote.priceToSales, 2),
  };

  const byEvEbitda: ScreenerTableColumn = {
    id: "evebitda",
    label: "EV/EBITDA",
    align: "right",
    render: (_row, quote) => fmtNum(quote.evToEbitda, 2),
  };

  const byPriceToCash: ScreenerTableColumn = {
    id: "pc",
    label: "P/C",
    align: "right",
    render: (_row, quote) => fmtNum(quote.priceToCash, 2),
  };

  const byPriceToFcf: ScreenerTableColumn = {
    id: "pfcf",
    label: "P/FCF",
    align: "right",
    render: (_row, quote) => fmtNum(quote.priceToFreeCashFlow, 2),
  };

  const byDividend: ScreenerTableColumn = {
    id: "dividend",
    label: "Dividend",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.dividendYield),
  };

  const byEps: ScreenerTableColumn = {
    id: "eps",
    label: "EPS (ttm)",
    align: "right",
    render: (_row, quote) => fmtNum(quote.eps, 2),
  };

  const byForwardEps: ScreenerTableColumn = {
    id: "epsForward",
    label: "EPS next Y",
    align: "right",
    render: (_row, quote) => fmtNum(quote.forwardEps, 2),
  };

  const byEpsThisY: ScreenerTableColumn = {
    id: "epsThisY",
    label: "EPS this Y",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.earningsGrowth),
  };

  const byEpsNextY: ScreenerTableColumn = {
    id: "epsNextY",
    label: "EPS next Y",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.earningsQuarterlyGrowth),
  };

  const byEpsPast5Y: ScreenerTableColumn = {
    id: "epsPast5Y",
    label: "EPS Past 5Y",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["epsPast5Y", "earningsGrowth"]), 2),
  };

  const byEpsNext5Y: ScreenerTableColumn = {
    id: "epsNext5Y",
    label: "EPS Next 5Y",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["epsNext5Y"]), 2),
  };

  const bySales: ScreenerTableColumn = {
    id: "sales",
    label: "Sales",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(quote.sales),
  };

  const byIncome: ScreenerTableColumn = {
    id: "income",
    label: "Income",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(quote.income),
  };

  const byEmployees: ScreenerTableColumn = {
    id: "employees",
    label: "Employees",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(firstFiniteMetric(quote, ["employees"])),
  };

  const byGrossMargin: ScreenerTableColumn = {
    id: "grossMargin",
    label: "Gross Margin",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.grossMargin),
  };

  const byOperMargin: ScreenerTableColumn = {
    id: "operMargin",
    label: "Oper. Margin",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.operatingMargin),
  };

  const bySalesPast5Y: ScreenerTableColumn = {
    id: "salesPast5Y",
    label: "Sales past 5Y",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.revenueGrowth),
  };

  const byProfitMargin: ScreenerTableColumn = {
    id: "profitMargin",
    label: "Profit Margin",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.profitMargin),
  };

  const byRoe: ScreenerTableColumn = {
    id: "roe",
    label: "ROE",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.roe),
  };

  const byRoic: ScreenerTableColumn = {
    id: "roic",
    label: "ROIC",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.roic),
  };

  const byRoa: ScreenerTableColumn = {
    id: "roa",
    label: "ROA",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.roa),
  };

  const byCurrRatio: ScreenerTableColumn = {
    id: "currentRatio",
    label: "Curr R",
    align: "right",
    render: (_row, quote) => fmtNum(quote.currentRatio, 2),
  };

  const byQuickRatio: ScreenerTableColumn = {
    id: "quickRatio",
    label: "Quick R",
    align: "right",
    render: (_row, quote) => fmtNum(quote.quickRatio, 2),
  };

  const byLongDebtEq: ScreenerTableColumn = {
    id: "longDebtEq",
    label: "LTDebt/Eq",
    align: "right",
    render: (_row, quote) => fmtNum(quote.longTermDebtToEquity, 2),
  };

  const byDebtEq: ScreenerTableColumn = {
    id: "debtEq",
    label: "Debt/Eq",
    align: "right",
    render: (_row, quote) => fmtNum(quote.debtToEquity, 2),
  };

  const byEarningsDate: ScreenerTableColumn = {
    id: "earningsDate",
    label: "Earnings",
    align: "right",
    render: (_row, quote) => fmtDate(quote.earningsDate),
  };

  const byInsiderOwn: ScreenerTableColumn = {
    id: "insiderOwn",
    label: "Insider Own",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.insiderOwn),
  };

  const byInstOwn: ScreenerTableColumn = {
    id: "instOwn",
    label: "Inst Own",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.instOwn),
  };

  const byInsiderTrans: ScreenerTableColumn = {
    id: "insiderTrans",
    label: "Insider Trans",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(quote.insiderTrans, 2),
  };

  const byInstTrans: ScreenerTableColumn = {
    id: "instTrans",
    label: "Inst Trans",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(quote.instTrans, 2),
  };

  const byShortFloat: ScreenerTableColumn = {
    id: "shortFloat",
    label: "Short Float",
    align: "right",
    render: (_row, quote) => fmtPercentFromRatio(quote.shortFloat),
  };

  const byShortRatio: ScreenerTableColumn = {
    id: "shortRatio",
    label: "Short Ratio",
    align: "right",
    render: (_row, quote) => fmtNum(quote.shortRatio, 2),
  };

  const byShsOut: ScreenerTableColumn = {
    id: "shsOut",
    label: "Shs Outstand",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(quote.sharesOutstanding),
  };

  const byFloat: ScreenerTableColumn = {
    id: "float",
    label: "Shs Float",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(quote.sharesFloat),
  };

  const byHigh52: ScreenerTableColumn = {
    id: "high52",
    label: "52W High",
    align: "right",
    render: (_row, quote) => fmtNum(quote.high52, 2),
  };

  const byLow52: ScreenerTableColumn = {
    id: "low52",
    label: "52W Low",
    align: "right",
    render: (_row, quote) => fmtNum(quote.low52, 2),
  };

  const byPerfWeek: ScreenerTableColumn = {
    id: "perfWeek",
    label: "Perf Week",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["perfWeek", "changePct"]), 2),
  };

  const byPerfMonth: ScreenerTableColumn = {
    id: "perfMonth",
    label: "Perf Month",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["perfMonth"]), 2),
  };

  const byPerfQuarter: ScreenerTableColumn = {
    id: "perfQuarter",
    label: "Perf Quart",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["perfQuarter"]), 2),
  };

  const byPerfHalf: ScreenerTableColumn = {
    id: "perfHalf",
    label: "Perf Half",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["perfHalf"]), 2),
  };

  const byPerfYtd: ScreenerTableColumn = {
    id: "perfYtd",
    label: "Perf YTD",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["perfYtd"]), 2),
  };

  const byPerfYear: ScreenerTableColumn = {
    id: "perfYear",
    label: "Perf Year",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["perfYear"]), 2),
  };

  const byPerf3Y: ScreenerTableColumn = {
    id: "perf3Y",
    label: "Perf 3Y",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["perf3Y"]), 2),
  };

  const byPerf5Y: ScreenerTableColumn = {
    id: "perf5Y",
    label: "Perf 5Y",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["perf5Y"]), 2),
  };

  const byPerf10Y: ScreenerTableColumn = {
    id: "perf10Y",
    label: "Perf 10Y",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["perf10Y"]), 2),
  };

  const byVolatilityW: ScreenerTableColumn = {
    id: "volW",
    label: "Volatility W",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["volatilityW"]), 2),
  };

  const byVolatilityM: ScreenerTableColumn = {
    id: "volM",
    label: "Volatility M",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["volatilityM"]), 2),
  };

  const byBeta: ScreenerTableColumn = {
    id: "beta",
    label: "Beta",
    align: "right",
    render: (_row, quote) => fmtNum(quote.beta, 2),
  };

  const bySma20: ScreenerTableColumn = {
    id: "sma20",
    label: "SMA20",
    align: "right",
    render: (_row, quote) => fmtNum(quote.sma20, 2),
  };

  const bySma50: ScreenerTableColumn = {
    id: "sma50",
    label: "SMA50",
    align: "right",
    render: (_row, quote) => fmtNum(quote.sma50, 2),
  };

  const bySma200: ScreenerTableColumn = {
    id: "sma200",
    label: "SMA200",
    align: "right",
    render: (_row, quote) => fmtNum(quote.sma200, 2),
  };

  const byRsi: ScreenerTableColumn = {
    id: "rsi14",
    label: "RSI (14)",
    align: "right",
    render: (_row, quote) => fmtNum(quote.rsi14, 2),
  };

  const byAtr: ScreenerTableColumn = {
    id: "atr14",
    label: "ATR (14)",
    align: "right",
    render: (_row, quote) => fmtNum(quote.atr14, 2),
  };

  const byCategory: ScreenerTableColumn = {
    id: "category",
    label: "Single Category",
    render: (_row, quote) => fmtText(quote.category),
  };

  const byTags: ScreenerTableColumn = {
    id: "tags",
    label: "Tags",
    render: (_row, quote) => fmtText(quote.fundFamily),
  };

  const byHoldings: ScreenerTableColumn = {
    id: "holdings",
    label: "Holdings",
    align: "right",
    render: (_row, quote) => fmtNum(firstFiniteMetric(quote, ["totalHoldings"]), 0),
  };

  const byAum: ScreenerTableColumn = {
    id: "aum",
    label: "AUM",
    align: "right",
    render: (_row, quote) => fmtCompactNumber(firstFiniteMetric(quote, ["assetsUnderManagement", "marketCap"])),
  };

  const byFlows1M: ScreenerTableColumn = {
    id: "flows1m",
    label: "Flows% 1M",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["netFlows1MonthPct"]), 2),
  };

  const byFlows3M: ScreenerTableColumn = {
    id: "flows3m",
    label: "Flows% 3M",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["netFlows3MonthPct"]), 2),
  };

  const byFlowsYtd: ScreenerTableColumn = {
    id: "flowsYtd",
    label: "Flows% YTD",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["netFlowsYtdPct"]), 2),
  };

  const byReturn1Y: ScreenerTableColumn = {
    id: "ret1y",
    label: "Return% 1Y",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["return1Year"]), 2),
  };

  const byReturn3Y: ScreenerTableColumn = {
    id: "ret3y",
    label: "Return% 3Y",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["return3Year"]), 2),
  };

  const byReturn5Y: ScreenerTableColumn = {
    id: "ret5y",
    label: "Return% 5Y",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["return5Year"]), 2),
  };

  const byExpense: ScreenerTableColumn = {
    id: "expense",
    label: "Expense",
    align: "right",
    render: (_row, quote) => fmtPercentSmart(firstFiniteMetric(quote, ["netExpenseRatio"]), 2),
  };

  if (tab === "valuation") {
    return [byTicker, byMarketCap, byPe, byForwardPe, byPeg, byPs, byPb, byPriceToCash, byPriceToFcf, byEpsThisY, byEpsNextY, byEpsPast5Y, byEpsNext5Y, bySalesPast5Y, byPrice, byChange, byVolume];
  }
  if (tab === "financial") {
    return [byTicker, byMarketCap, byDividend, byRoa, byRoe, byRoic, byCurrRatio, byQuickRatio, byLongDebtEq, byDebtEq, byGrossMargin, byOperMargin, byProfitMargin, byEarningsDate, byPrice, byChange, byVolume];
  }
  if (tab === "ownership") {
    return [byTicker, byMarketCap, byShsOut, byFloat, byInsiderOwn, byInsiderTrans, byInstOwn, byInstTrans, byShortFloat, byShortRatio, byAvgVolume, byPrice, byChange, byVolume];
  }
  if (tab === "performance") {
    return [
      byTicker,
      byPerfWeek,
      byPerfMonth,
      byPerfQuarter,
      byPerfHalf,
      byPerfYtd,
      byPerfYear,
      byPerf3Y,
      byPerf5Y,
      byPerf10Y,
      byVolatilityW,
      byVolatilityM,
      byAvgVolume,
      byRelVolume,
      byPrice,
      byChange,
      byVolume,
    ];
  }
  if (tab === "technical" || tab === "ta") {
    return [byTicker, byBeta, byAtr, bySma20, bySma50, bySma200, byHigh52, byLow52, byRsi, byPrice, byChange, byChangeFromOpen, byGap, byVolume];
  }
  if (tab === "etf") return [byTicker, byCompany, byCategory, byTags, byDividend, byPrice, byChange];
  if (tab === "etfPerf") return [byTicker, byHoldings, byAum, byFlows1M, byFlows3M, byFlowsYtd, byReturn1Y, byReturn3Y, byReturn5Y, byExpense, byPrice, byChange];
  if (tab === "newsTab") {
    return [byTicker, byCompany, byNewsHeadline, byNewsPublisher, byNewsPublished, byNewsCount, byPrice, byChange, byVolume];
  }
  if (tab === "basic") {
    return [byTicker, byCompany, bySector, byIndustry, byCountry, byMarketCap, byPrice, byChange, byVolume, byAvgVolume, byRelVolume];
  }
  if (tab === "maps") {
    return [byTicker, byCompany, bySector, byIndustry, byCountry, byMarketCap, byPe, byPrice, byChange, byVolume];
  }

  return [byTicker, byCompany, bySector, byIndustry, byCountry, byMarketCap, byPe, byPrice, byChange, byVolume];
}

function AnalysisPanel({
  ticker,
  row,
  chartLoading,
  chartError,
  chartSummary,
  chartNote,
  quoteSummary,
  chartBars,
  chartControls,
  onChartControlsChange,
}: {
  ticker: string;
  row: ScreenerRow | null;
  chartLoading: boolean;
  chartError: string;
  chartSummary: ChartSummary | null;
  chartNote: string;
  quoteSummary: QuoteSummary;
  chartBars: ChartBar[];
  chartControls: ScreenerChartControls;
  onChartControlsChange: (next: ScreenerChartControls) => void;
}) {
  const hasChart = Boolean(chartSummary);
  const decision = row?.decision ?? "Hold";
  const peerLine = "SPY IVV SPLG VTI QQQ VTV DIA VIG VYM VUG";
  const heldByLine = "KHPI TSPX OVL OVLH SPYA RSEE LFEQ HNDL BAMO OCIO";

  const statColumns = useMemo(
    () =>
      buildMarketStatColumns({
        quote: quoteSummary,
        chartSummary,
        chartBars,
      }),
    [chartBars, chartSummary, quoteSummary],
  );

  const statRowCount = useMemo(() => Math.max(...statColumns.map((column) => column.length)), [statColumns]);

  const holdingsLegend = useMemo(
    () => [
      { name: "Electronic Technology", value: 25.3, color: "#8a6fe8" },
      { name: "Technology Services", value: 19.7, color: "#2dbb9a" },
      { name: "Finance", value: 13.9, color: "#ef9f2a" },
      { name: "Retail Trade", value: 7.9, color: "#1ab7d8" },
      { name: "Health Technology", value: 7.8, color: "#e44f90" },
      { name: "Consumer Non Durables", value: 3.3, color: "#9c6ce2" },
      { name: "Energy Minerals", value: 2.4, color: "#5aa7f0" },
      { name: "Other", value: 19.7, color: "#dbdbdb" },
    ],
    [],
  );

  const donutGradient = useMemo(() => {
    let start = 0;
    const stops: string[] = [];
    for (const slice of holdingsLegend) {
      const end = start + (slice.value / 100) * 360;
      stops.push(`${slice.color} ${start.toFixed(2)}deg ${end.toFixed(2)}deg`);
      start = end;
    }
    return `conic-gradient(${stops.join(", ")})`;
  }, [holdingsLegend]);

  const topHoldings = [
    { name: "NVIDIA Corp", pct: "7.83%", sector: "Electronic Technology" },
    { name: "Apple Inc", pct: "6.46%", sector: "Electronic Technology" },
    { name: "Microsoft Corporation", pct: "5.39%", sector: "Technology Services" },
    { name: "Amazon.com Inc.", pct: "3.92%", sector: "Retail Trade" },
    { name: "Alphabet Inc - Class A", pct: "3.31%", sector: "Technology Services" },
    { name: "Alphabet Inc - Class C", pct: "2.65%", sector: "Technology Services" },
    { name: "Broadcom Inc", pct: "2.64%", sector: "Electronic Technology" },
    { name: "Meta Platforms Inc - Class A", pct: "2.63%", sector: "Technology Services" },
    { name: "Tesla Inc", pct: "2.04%", sector: "Consumer Durables" },
    { name: "Berkshire Hathaway Inc - Class B", pct: "1.48%", sector: "Finance" },
  ];

  const flowChart = useMemo(() => {
    const source = chartBars.slice(-140);
    if (source.length < 2) {
      return {
        width: 1000,
        height: 230,
        points: [] as Array<{ x: number; y: number }>,
        bars: [] as Array<{ x: number; y: number; w: number; h: number; up: boolean }>,
        minClose: null as number | null,
        maxClose: null as number | null,
        lastClose: null as number | null,
        netChange: null as number | null,
        netChangePct: null as number | null,
        avgVol: null as number | null,
      };
    }

    const width = 1000;
    const height = 230;
    const left = 22;
    const right = width - 22;
    const lineTop = 16;
    const lineBottom = 162;
    const barBase = 178;
    const barMax = 40;

    const closes = source.map((bar) => bar.close);
    const volumes = source.map((bar) => Math.max(0, bar.volume));
    const minClose = Math.min(...closes);
    const maxClose = Math.max(...closes);
    const closeSpan = Math.max(maxClose - minClose, 0.000001);
    const maxVol = Math.max(...volumes, 1);
    const firstClose = closes[0] ?? null;
    const lastClose = closes[closes.length - 1] ?? null;
    const netChange = firstClose !== null && lastClose !== null ? lastClose - firstClose : null;
    const netChangePct = netChange !== null && firstClose !== null && firstClose !== 0 ? (netChange / firstClose) * 100 : null;
    const avgVol = volumes.length > 0 ? volumes.reduce((sum, value) => sum + value, 0) / volumes.length : null;

    const points = source.map((bar, index) => {
      const ratio = index / Math.max(source.length - 1, 1);
      const x = left + ratio * (right - left);
      const y = lineBottom - ((bar.close - minClose) / closeSpan) * (lineBottom - lineTop);
      return { x, y };
    });

    const barWidth = Math.max(((right - left) / source.length) * 0.6, 1.3);
    const bars = source.map((bar, index) => {
      const ratio = index / Math.max(source.length - 1, 1);
      const x = left + ratio * (right - left) - barWidth / 2;
      const h = (Math.max(0, bar.volume) / maxVol) * barMax;
      const prevClose = index > 0 ? source[index - 1].close : bar.close;
      const up = bar.close >= prevClose;
      return {
        x,
        y: up ? barBase - h : barBase,
        w: barWidth,
        h,
        up,
      };
    });

    return { width, height, points, bars, minClose, maxClose, lastClose, netChange, netChangePct, avgVol };
  }, [chartBars]);

  const flowPath = useMemo(() => pathFromPoints(flowChart.points), [flowChart.points]);

  return (
    <div className="tfe-analysis-panel">
      <h3 style={{ margin: "0 0 8px", fontSize: "0.96rem" }}>
        {ticker} Analysis <span className={`tfe-chip ${toDecisionClass(decision)}`}>{decision}</span>
      </h3>

      {chartLoading ? <p className="tfe-muted">Loading analysis...</p> : null}
      {chartError ? <p className="tfe-error">{chartError}</p> : null}

      {!chartLoading && !chartError ? (
        <div className="tfe-screener-analysis-stack">
          <div className="tfe-screener-info-strip">
            <span>
              <strong>Peers:</strong> {peerLine}
            </span>
            <span>
              <strong>Held by:</strong> {heldByLine}
            </span>
          </div>

          {hasChart ? (
            <ScreenerChart
              ticker={ticker}
              bars={chartBars}
              controls={chartControls}
              loading={chartLoading}
              onControlsChange={onChartControlsChange}
            />
          ) : (
            <p className="tfe-muted">{chartNote || `No chart data available for ${ticker}.`}</p>
          )}

          <section className="tfe-screener-panel">
            <table className="tfe-screener-stat-table">
              <tbody>
                {Array.from({ length: statRowCount }).map((_, rowIndex) => (
                  <tr key={`screener-stat-row-${rowIndex}`}>
                    {statColumns.map((column, columnIndex) => {
                      const cell = column[rowIndex];
                      const tone = cell ? inferTone(cell.value) : null;
                      return (
                        [
                          <td key={`screener-stat-cell-label-${columnIndex}-${rowIndex}`} className="k">
                            {cell?.label ?? ""}
                          </td>,
                          <td key={`screener-stat-cell-value-${columnIndex}-${rowIndex}`} className={tone ? `v tone-${tone}` : "v"}>
                            {cell?.value ?? ""}
                          </td>,
                        ]
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <div className="tfe-screener-duo">
            <section className="tfe-screener-panel">
              <div className="tfe-screener-panel-head">
                <h4>Holdings Breakdown</h4>
                <span>View Holdings as</span>
              </div>

              <div className="tfe-screener-holdings-wrap">
                <div className="tfe-screener-donut-wrap">
                  <div className="tfe-screener-donut" style={{ backgroundImage: donutGradient }} />
                </div>
                <div className="tfe-screener-legend">
                  {holdingsLegend.map((slice) => (
                    <div key={slice.name} className="tfe-screener-legend-item">
                      <span className="tfe-color-dot" style={{ background: slice.color }} />
                      <span>{slice.name}</span>
                      <span>{slice.value.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="tfe-screener-panel">
              <div className="tfe-screener-panel-head">
                <h4>Top 10 Holdings</h4>
                <span>View Holdings as</span>
              </div>
              <table className="tfe-screener-holdings-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>% Holdings</th>
                    <th>Sector</th>
                  </tr>
                </thead>
                <tbody>
                  {topHoldings.map((holding) => (
                    <tr key={`${holding.name}-${holding.pct}`}>
                      <td>{holding.name}</td>
                      <td>{holding.pct}</td>
                      <td>{holding.sector}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="tfe-screener-panel-foot">10 Holdings</div>
            </section>
          </div>

          <section className="tfe-screener-panel">
            <div className="tfe-screener-panel-head">
              <h4>Fund Flows</h4>
            </div>

            {flowChart.points.length < 2 ? (
              <p className="tfe-muted">No flow chart data available.</p>
            ) : (
              <>
                <div className="tfe-screener-flow-metrics">
                  <span>Last: {fmtPrice(flowChart.lastClose)}</span>
                  <span>
                    Range: {fmtPrice(flowChart.minClose)} - {fmtPrice(flowChart.maxClose)}
                  </span>
                  <span>
                    Net: {fmtPercentSigned(flowChart.netChangePct)}
                  </span>
                  <span>Avg Vol: {fmtCompactNumber(flowChart.avgVol)}</span>
                </div>
                <svg viewBox={`0 0 ${flowChart.width} ${flowChart.height}`} className="tfe-screener-flow-canvas" aria-label="Fund flows chart">
                  <rect x="0" y="0" width={flowChart.width} height={flowChart.height} fill="rgba(247,250,247,0.86)" />
                  {[0, 1, 2, 3, 4].map((gridIndex) => {
                    const ratio = 1 - gridIndex / 4;
                    const y = 16 + (gridIndex / 4) * 146;
                    const min = flowChart.minClose ?? 0;
                    const max = flowChart.maxClose ?? min;
                    const price = min + ratio * (max - min);

                    return (
                      <g key={`flow-grid-${gridIndex}`}>
                        <line x1="20" y1={y} x2={flowChart.width - 20} y2={y} stroke="rgba(31,56,47,0.14)" strokeWidth="1" />
                        <text x={flowChart.width - 6} y={y + 3} textAnchor="end" fontSize="10" fill="rgba(31,56,47,0.72)">
                          {fmtPrice(price)}
                        </text>
                      </g>
                    );
                  })}

                  {flowChart.bars.map((bar, index) => (
                    <rect
                      key={`flow-bar-${index}`}
                      x={bar.x}
                      y={bar.y}
                      width={bar.w}
                      height={bar.h}
                      fill={bar.up ? "rgba(57,182,114,0.70)" : "rgba(219,87,87,0.68)"}
                      rx="1"
                    />
                  ))}

                  <path d={flowPath} fill="none" stroke="#4d90e2" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}

export default function ScreenerWorkbench() {
  const [tab, setTab] = useState<ScreenerTab>("overview");
  const [dataTab, setDataTab] = useState<ScreenerDataTab>("overview");
  const [filterGroup, setFilterGroup] = useState<ScreenerFilterGroup>("descriptive");
  const [filtersVisible, setFiltersVisible] = useState(true);
  const [search, setSearch] = useState("");
  const [assetType, setAssetType] = useState("");
  const [signal, setSignal] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minBars, setMinBars] = useState("");
  const [maxBars, setMaxBars] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>(SUPPORTED_ORDER_OPTIONS[0]?.value ?? "ticker");
  const [sortDir, setSortDir] = useState<SortDirection>("asc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [advancedFilters, setAdvancedFilters] = useState<AdvancedFilterState>(ADVANCED_FILTER_DEFAULTS);
  const [presetRecords, setPresetRecords] = useState<ScreenerPresetRecord[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState("");
  const [presetEditorOpen, setPresetEditorOpen] = useState(false);
  const [presetNotice, setPresetNotice] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [rows, setRows] = useState<ScreenerRow[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [pageJumpValue, setPageJumpValue] = useState("");
  const [assetOptions, setAssetOptions] = useState<AssetType[]>(["equities", "index", "crypto", "etf", "other"]);

  const [selectedTicker, setSelectedTicker] = useState("");
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [chartNote, setChartNote] = useState("");
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartSummary | null>(null);
  const [quoteSummary, setQuoteSummary] = useState<QuoteSummary>({});
  const [chartControls, setChartControls] = useState<ScreenerChartControls>(DEFAULT_SCREENER_CHART_CONTROLS);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [flyoutRect, setFlyoutRect] = useState<FlyoutRect | null>(null);
  const [flyoutMaximized, setFlyoutMaximized] = useState(false);
  const [quoteByTicker, setQuoteByTicker] = useState<Record<string, QuoteSummary>>({});
  const [quoteLoadingByTicker, setQuoteLoadingByTicker] = useState<Record<string, boolean>>({});
  const [quoteAttemptsByTicker, setQuoteAttemptsByTicker] = useState<Record<string, number>>({});
  const [quoteLastAttemptMsByTicker, setQuoteLastAttemptMsByTicker] = useState<Record<string, number>>({});
  const [mapTickers, setMapTickers] = useState<ScreenerMapTicker[]>([]);
  const [mapHover, setMapHover] = useState<{ id: string; x: number; y: number } | null>(null);
  const [mapFocusSector, setMapFocusSector] = useState("");
  const [mapFocusIndustry, setMapFocusIndustry] = useState("");
  const [mapDataType, setMapDataType] = useState<MapDataType>("1d");
  const [mapSidebarSearch, setMapSidebarSearch] = useState("");
  const [mapShowEtf, setMapShowEtf] = useState(false);
  const [mapViewportSize, setMapViewportSize] = useState({ width: 1280, height: 760 });
  const mapViewportRef = useRef<HTMLDivElement | null>(null);
  const mapSidebarListRef = useRef<HTMLDivElement | null>(null);
  const [newsFocusTicker, setNewsFocusTicker] = useState("");
  const [newsPanelLoading, setNewsPanelLoading] = useState(false);
  const [newsPanelError, setNewsPanelError] = useState("");
  const [newsPanelNote, setNewsPanelNote] = useState("");
  const [newsPanelBars, setNewsPanelBars] = useState<ChartBar[]>([]);
  const [newsPanelSummary, setNewsPanelSummary] = useState<ChartSummary | null>(null);
  const [newsPanelQuote, setNewsPanelQuote] = useState<QuoteSummary>({});
  const [newsPanelStories, setNewsPanelStories] = useState<NewsItem[]>([]);
  const [newsChartControls, setNewsChartControls] = useState<ScreenerChartControls>(NEWS_PANEL_DEFAULT_CONTROLS);
  const [advancedExternalMeta, setAdvancedExternalMeta] = useState<ScreenerResponse["advancedFilterExternal"] | null>(null);
  const componentMountedRef = useRef(true);
  const flyoutRestoreRef = useRef<FlyoutRect | null>(null);
  const flyoutDragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    origin: FlyoutRect;
  } | null>(null);
  const flyoutResizeRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    origin: FlyoutRect;
  } | null>(null);

  const selectedRow = useMemo(() => rows.find((row) => row.ticker === selectedTicker) ?? null, [rows, selectedTicker]);
  const analysisTicker = selectedRow?.ticker ?? selectedTicker;
  const newsFocusRow = useMemo(() => rows.find((row) => row.ticker === newsFocusTicker) ?? null, [rows, newsFocusTicker]);
  const apiTab = useMemo(() => resolveApiTabForDataTab(tab, dataTab), [tab, dataTab]);

  useEffect(() => {
    return () => {
      componentMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const loaded = readScreenerPresets();
    setPresetRecords(loaded);
  }, []);

  useEffect(() => {
    writeScreenerPresets(presetRecords);
  }, [presetRecords]);

  useEffect(() => {
    if (!selectedPresetId) return;
    if (presetRecords.some((record) => record.id === selectedPresetId)) return;
    setSelectedPresetId("");
  }, [presetRecords, selectedPresetId]);

  useEffect(() => {
    if (!analysisOpen) return;

    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setAnalysisOpen(false);
        setSelectedTicker("");
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [analysisOpen]);

  useEffect(() => {
    if (!analysisOpen) {
      setFlyoutRect(null);
      setFlyoutMaximized(false);
      flyoutRestoreRef.current = null;
      flyoutDragRef.current = null;
      flyoutResizeRef.current = null;
      return;
    }

    const rect = defaultFlyoutRect(window.innerWidth, window.innerHeight);
    setFlyoutRect(rect);
    setFlyoutMaximized(false);
    flyoutRestoreRef.current = rect;
  }, [analysisOpen]);

  useEffect(() => {
    if (!analysisOpen) return;

    const onResize = () => {
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      setFlyoutRect((current) => {
        if (flyoutMaximized) return maximizedFlyoutRect(viewportWidth, viewportHeight);
        const base = current ?? defaultFlyoutRect(viewportWidth, viewportHeight);
        return clampFlyoutRect(base, viewportWidth, viewportHeight);
      });
    };

    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [analysisOpen, flyoutMaximized]);

  useEffect(() => {
    if (!analysisOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [analysisOpen]);

  useEffect(() => {
    setPage(1);
  }, [apiTab, search, assetType, signal, minPrice, maxPrice, minBars, maxBars, sortKey, sortDir, pageSize, advancedFilters]);

  useEffect(() => {
    if (totalPages < 1) {
      setPageJumpValue("");
      return;
    }
    const safeCurrent = Math.min(Math.max(1, page), totalPages);
    setPageJumpValue(String(safeCurrent));
  }, [page, totalPages]);

  useEffect(() => {
    const controller = new AbortController();

    async function load(): Promise<void> {
      setLoading(true);
      setError("");

      try {
        const query = new URLSearchParams({
          tab: apiTab,
          page: String(page),
          pageSize: String(pageSize),
          sortKey,
          sortDir,
        });

        if (search.trim()) query.set("search", search.trim());
        if (assetType) query.set("assetType", assetType);
        if (signal) query.set("signal", signal);
        query.set("filterGroup", filterGroup);
        if (minPrice.trim()) query.set("minPrice", minPrice.trim());
        if (maxPrice.trim()) query.set("maxPrice", maxPrice.trim());
        if (minBars.trim()) query.set("minBars", minBars.trim());
        if (maxBars.trim()) query.set("maxBars", maxBars.trim());
        if (dataTab === "maps") query.set("includeMap", "1");
        for (const [key, value] of Object.entries(advancedFilters)) {
          const normalized = String(value ?? "").trim();
          if (!normalized) continue;
          query.set(key, normalized);
        }

        let payload: ScreenerResponse | null = null;
        let responseStatus = 0;
        let responseOk = false;

        for (let attempt = 1; attempt <= SCREENER_LOAD_MAX_ATTEMPTS; attempt += 1) {
          const response = await fetch(`/api/screener?${query.toString()}`, {
            method: "GET",
            cache: "no-store",
            signal: controller.signal,
          });

          responseStatus = response.status;
          let nextPayload: ScreenerResponse;
          try {
            nextPayload = (await response.json()) as ScreenerResponse;
          } catch {
            nextPayload = {
              tab: apiTab,
              page,
              pageSize,
              total: 0,
              totalPages: 1,
              rows: [],
              options: {
                regimes: [],
                assetTypes: ["equities", "index", "crypto", "etf", "other"],
                decisions: [],
                tabs: [],
                sortKeys: [],
              },
              error: "Failed to parse screener response.",
            };
          }

          payload = nextPayload;
          responseOk = response.ok;
          const retryable = !responseOk && shouldRetryScreenerLoad(responseStatus, payload.error ?? "");
          if (responseOk || !retryable || attempt >= SCREENER_LOAD_MAX_ATTEMPTS) {
            break;
          }
          await sleepMs(SCREENER_LOAD_RETRY_DELAY_MS * attempt);
        }

        if (!payload) {
          setRows([]);
          setMapTickers([]);
          setAdvancedExternalMeta(null);
          setTotal(0);
          setTotalPages(1);
          setError("Failed to load screener.");
          return;
        }

        if (!responseOk) {
          setRows([]);
          setMapTickers([]);
          setAdvancedExternalMeta(payload.advancedFilterExternal ?? null);
          setTotal(0);
          setTotalPages(1);
          setError(payload.error ?? `Failed to load screener (HTTP ${responseStatus}).`);
          return;
        }

        setRows(Array.isArray(payload.rows) ? payload.rows : []);
        setMapTickers(Array.isArray(payload.mapTickers) ? payload.mapTickers : []);
        setAdvancedExternalMeta(payload.advancedFilterExternal ?? null);
        setPage(Number(payload.page ?? page) || 1);
        setTotal(Number(payload.total ?? 0));
        setTotalPages(Number(payload.totalPages ?? 1) || 1);
        setAssetOptions(Array.isArray(payload.options?.assetTypes) ? payload.options.assetTypes : ["equities", "index", "crypto", "etf", "other"]);
        if (payload.pageQuotes && typeof payload.pageQuotes === "object") {
          setQuoteByTicker((current) => {
            const next = { ...current };
            for (const [ticker, quote] of Object.entries(payload.pageQuotes ?? {})) {
              const normalizedTicker = String(ticker ?? "").trim().toUpperCase();
              if (!normalizedTicker) continue;
              const incoming = quote && typeof quote === "object" ? quote : {};
              next[normalizedTicker] = {
                ...(current[normalizedTicker] ?? {}),
                ...(incoming as QuoteSummary),
              };
            }
            return next;
          });
        }
      } catch (requestError) {
        if ((requestError as Error).name === "AbortError") return;
        setRows([]);
        setMapTickers([]);
        setAdvancedExternalMeta(null);
        setTotal(0);
        setTotalPages(1);
        setError("Failed to load screener due to network error.");
      } finally {
        setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, [apiTab, dataTab, page, pageSize, search, assetType, signal, filterGroup, minPrice, maxPrice, minBars, maxBars, sortKey, sortDir, advancedFilters]);

  useEffect(() => {
    if (dataTab !== "ta") return;
    const visibleTickers = new Set(rows.map((row) => row.ticker));
    if (visibleTickers.size === 0) return;

    setQuoteAttemptsByTicker((current) => {
      let changed = false;
      const next = { ...current };
      for (const ticker of visibleTickers) {
        if (ticker in next) {
          delete next[ticker];
          changed = true;
        }
      }
      return changed ? next : current;
    });

    setQuoteLastAttemptMsByTicker((current) => {
      let changed = false;
      const next = { ...current };
      for (const ticker of visibleTickers) {
        if (ticker in next) {
          delete next[ticker];
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [dataTab, rows]);

  useEffect(() => {
    const now = Date.now();

    const missing = rows
      .map((row) => row.ticker)
      .filter((ticker) => {
        if (quoteLoadingByTicker[ticker]) return false;
        const quote = quoteByTicker[ticker];
        const attempts = quoteAttemptsByTicker[ticker] ?? 0;

        if (dataTab === "ta") {
          if (attempts >= TA_MINI_CHART_ATTEMPT_CAP) return false;
          const lastAttemptMs = quoteLastAttemptMsByTicker[ticker] ?? 0;
          if (lastAttemptMs > 0 && now - lastAttemptMs < TA_MINI_CHART_RETRY_INTERVAL_MS) return false;
          if (!quote) return true;
          if (hasCoreQuoteData(quote) && hasMiniChartData(quote)) return false;
          return true;
        }

        if (attempts >= 3) return false;
        if (!quote) return true;
        if (dataTab === "newsTab") return quote.newsFetched !== true;
        return !hasCoreQuoteData(quote);
      });

    if (missing.length === 0) return;

    function markQuoteAttemptFailed(ticker: string): void {
      setQuoteAttemptsByTicker((current) => {
        const prev = current[ticker] ?? 0;
        const maxAttempts = dataTab === "ta" ? TA_MINI_CHART_ATTEMPT_CAP : 3;
        if (prev >= maxAttempts) return current;
        return { ...current, [ticker]: prev + 1 };
      });
    }

    function clearQuoteAttempt(ticker: string): void {
      setQuoteAttemptsByTicker((current) => {
        if (!(ticker in current)) return current;
        const next = { ...current };
        delete next[ticker];
        return next;
      });
    }

    async function loadSingleTickerQuote(ticker: string): Promise<void> {
      setQuoteLoadingByTicker((current) => ({ ...current, [ticker]: true }));
      setQuoteLastAttemptMsByTicker((current) => ({ ...current, [ticker]: Date.now() }));
      try {
        const params = new URLSearchParams({ ticker });
        if (dataTab === "newsTab") {
          params.set("quoteOnly", "1");
          params.set("includeNews", "1");
        } else if (dataTab === "ta") {
          params.set("quoteOnly", "1");
          params.set("includeMiniBars", "1");
          params.set("interval", "1d");
          params.set("range", "1y");
        } else {
          params.set("quoteOnly", "1");
        }

        const response = await fetch(`/api/watchlist/chart?${params.toString()}`, {
          method: "GET",
          cache: "no-store",
        });

        if (!response.ok) {
          if (!componentMountedRef.current) return;
          markQuoteAttemptFailed(ticker);
          setQuoteByTicker((current) => ({
            ...current,
            [ticker]:
              dataTab === "newsTab"
                ? { ...(current[ticker] ?? {}), newsFetched: true, news: [], newsCount: 0 }
                : { ...(current[ticker] ?? {}) },
          }));
          return;
        }

        const payload = (await response.json()) as ChartResponse;
        if (!componentMountedRef.current) return;

        const news = Array.isArray(payload.news) ? payload.news : [];
        const topNews = news.length > 0 ? news[0] : null;
        const miniBars = Array.isArray(payload.bars) ? payload.bars : [];

        setQuoteByTicker((current) => ({
          ...current,
          [ticker]: {
            ...(current[ticker] ?? {}),
            ...(payload.quote ?? {}),
            ...(dataTab === "ta"
              ? {
                  miniBars,
                  miniChartFetched: true,
                  miniChartInterval: payload.interval ?? null,
                  miniChartRange: payload.range ?? null,
                  miniChartNote: typeof payload.note === "string" ? payload.note : null,
                }
              : {}),
            ...(dataTab === "newsTab"
              ? {
                  newsFetched: true,
                  news,
                  newsCount: news.length,
                  newsHeadline: topNews?.title ?? null,
                  newsPublisher: topNews?.publisher ?? null,
                  newsPublishedAt: topNews?.publishedAt ?? null,
                  newsLink: topNews?.link ?? null,
                }
                : {}),
          },
        }));

        if (dataTab === "newsTab") {
          clearQuoteAttempt(ticker);
        } else if (dataTab === "ta") {
          const merged = {
            ...(quoteByTicker[ticker] ?? {}),
            ...(payload.quote ?? {}),
            miniBars,
          } as QuoteSummary;

          if (hasCoreQuoteData(merged) && hasMiniChartData(merged)) {
            clearQuoteAttempt(ticker);
            setQuoteLastAttemptMsByTicker((current) => {
              if (!(ticker in current)) return current;
              const next = { ...current };
              delete next[ticker];
              return next;
            });
          } else {
            markQuoteAttemptFailed(ticker);
          }
        } else {
          const merged = {
            ...(quoteByTicker[ticker] ?? {}),
            ...(payload.quote ?? {}),
          } as QuoteSummary;

          if (hasCoreQuoteData(merged)) {
            clearQuoteAttempt(ticker);
          } else {
            markQuoteAttemptFailed(ticker);
          }
        }
      } catch {
        if (!componentMountedRef.current) return;
        markQuoteAttemptFailed(ticker);
        setQuoteByTicker((current) => ({
          ...current,
          [ticker]:
            dataTab === "newsTab"
              ? { ...(current[ticker] ?? {}), newsFetched: true, news: [], newsCount: 0 }
              : { ...(current[ticker] ?? {}) },
        }));
      } finally {
        setQuoteLoadingByTicker((current) => {
          const next = { ...current };
          delete next[ticker];
          return next;
        });
      }
    }

    async function loadRowQuotes(): Promise<void> {
      const concurrency = dataTab === "ta" ? TA_MINI_CHART_FETCH_CONCURRENCY : 6;
      for (let index = 0; index < missing.length; index += concurrency) {
        if (!componentMountedRef.current) return;
        const batch = missing.slice(index, index + concurrency);
        await Promise.all(batch.map((ticker) => loadSingleTickerQuote(ticker)));
      }
    }

    void loadRowQuotes();
  }, [rows, quoteAttemptsByTicker, quoteByTicker, quoteLoadingByTicker, quoteLastAttemptMsByTicker, dataTab]);

  useEffect(() => {
    if (dataTab !== "newsTab") return;
    setNewsFocusTicker((current) => {
      if (current && rows.some((row) => row.ticker === current)) return current;
      return rows[0]?.ticker ?? "";
    });
  }, [dataTab, rows]);

  useEffect(() => {
    if (dataTab !== "newsTab") return;
    if (!newsFocusTicker) {
      setNewsPanelBars([]);
      setNewsPanelSummary(null);
      setNewsPanelQuote({});
      setNewsPanelStories([]);
      setNewsPanelError("");
      setNewsPanelNote("");
      setNewsPanelLoading(false);
      return;
    }

    const controller = new AbortController();
    const ticker = newsFocusTicker;
    const nextControls = newsChartControls;

    async function loadNewsPanel(): Promise<void> {
      setNewsPanelLoading(true);
      setNewsPanelError("");
      setNewsPanelNote("");

      try {
        const params = new URLSearchParams({
          ticker,
          interval: nextControls.interval,
          range: nextControls.range,
          includeNews: "1",
        });

        const response = await fetch(`/api/watchlist/chart?${params.toString()}`, {
          method: "GET",
          cache: "no-store",
          signal: controller.signal,
        });
        const payload = (await response.json()) as ChartResponse;
        if (controller.signal.aborted) return;

        if (!response.ok) {
          setNewsPanelBars([]);
          setNewsPanelSummary(null);
          setNewsPanelQuote({});
          setNewsPanelStories([]);
          setNewsPanelNote("");
          setNewsPanelError(payload.error ?? "Failed to load news panel.");
          return;
        }

        const stories = Array.isArray(payload.news) ? payload.news : [];
        const topStory = stories[0] ?? null;

        setNewsPanelBars(Array.isArray(payload.bars) ? payload.bars : []);
        setNewsPanelSummary(payload.summary ?? null);
        setNewsPanelQuote(payload.quote ?? {});
        setNewsPanelStories(stories);
        setNewsPanelNote(typeof payload.note === "string" ? payload.note : "");
        setNewsPanelError("");

        setQuoteByTicker((current) => ({
          ...current,
          [ticker]: {
            ...(current[ticker] ?? {}),
            ...(payload.quote ?? {}),
            newsFetched: true,
            news: stories,
            newsCount: stories.length,
            newsHeadline: topStory?.title ?? null,
            newsPublisher: topStory?.publisher ?? null,
            newsPublishedAt: topStory?.publishedAt ?? null,
            newsLink: topStory?.link ?? null,
          },
        }));

        const resolvedInterval = normalizeChartInterval(payload.interval, nextControls.interval);
        const resolvedRange = normalizeChartRange(payload.range, nextControls.range);
        setNewsChartControls((current) => {
          const timeframe = timeframeFromInterval(resolvedInterval);
          if (current.interval === resolvedInterval && current.range === resolvedRange && current.timeframe === timeframe) {
            return current;
          }
          return {
            ...current,
            interval: resolvedInterval,
            range: resolvedRange,
            timeframe,
          };
        });
      } catch (requestError) {
        if ((requestError as Error).name === "AbortError") return;
        setNewsPanelBars([]);
        setNewsPanelSummary(null);
        setNewsPanelQuote({});
        setNewsPanelStories([]);
        setNewsPanelNote("");
        setNewsPanelError("Failed to load news panel due to network error.");
      } finally {
        if (!controller.signal.aborted) {
          setNewsPanelLoading(false);
        }
      }
    }

    void loadNewsPanel();
    return () => controller.abort();
  }, [dataTab, newsFocusTicker, newsChartControls.interval, newsChartControls.range]);

  async function loadChart(ticker: string, controls?: ScreenerChartControls): Promise<void> {
    const nextControls = controls ?? chartControls;

    setSelectedTicker(ticker);
    setChartControls(nextControls);
    setChartLoading(true);
    setChartError("");
    setChartNote("");

    try {
      const params = new URLSearchParams({
        ticker,
        interval: nextControls.interval,
        range: nextControls.range,
      });

      const res = await fetch(`/api/watchlist/chart?${params.toString()}`, {
        method: "GET",
        cache: "no-store",
      });

      const data = (await res.json()) as ChartResponse;

      if (!res.ok) {
        setChartBars([]);
        setChartSummary(null);
        setQuoteSummary({});
        setChartNote("");
        setChartError(data.error ?? "Failed to load chart.");
        return;
      }

      setChartBars(Array.isArray(data.bars) ? data.bars : []);
      setChartSummary(data.summary ?? null);
      setQuoteSummary(data.quote ?? {});
      setChartNote(typeof data.note === "string" ? data.note : "");

      const resolvedInterval = normalizeChartInterval(data.interval, nextControls.interval);
      const resolvedRange = normalizeChartRange(data.range, nextControls.range);

      setChartControls({
        ...nextControls,
        interval: resolvedInterval,
        range: resolvedRange,
        timeframe: timeframeFromInterval(resolvedInterval),
      });
    } catch {
      setChartBars([]);
      setChartSummary(null);
      setQuoteSummary({});
      setChartNote("");
      setChartError("Failed to load chart due to network error.");
    } finally {
      setChartLoading(false);
    }
  }

  function closeAnalysis(): void {
    setAnalysisOpen(false);
    setSelectedTicker("");
  }

  function goToPage(nextPage: number): void {
    const safeTotalPages = Math.max(1, totalPages);
    const safePage = Math.min(Math.max(1, Math.round(nextPage)), safeTotalPages);
    setPage(safePage);
  }

  function applyJumpPageValue(): void {
    const parsed = Number(pageJumpValue);
    if (!Number.isFinite(parsed)) return;
    goToPage(parsed);
  }

  function toggleFlyoutMaximize(): void {
    if (!flyoutRect) return;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    if (flyoutMaximized) {
      const restored = clampFlyoutRect(flyoutRestoreRef.current ?? defaultFlyoutRect(viewportWidth, viewportHeight), viewportWidth, viewportHeight);
      setFlyoutRect(restored);
      setFlyoutMaximized(false);
      flyoutRestoreRef.current = restored;
      return;
    }

    flyoutRestoreRef.current = flyoutRect;
    setFlyoutRect(maximizedFlyoutRect(viewportWidth, viewportHeight));
    setFlyoutMaximized(true);
  }

  function handleFlyoutDragStart(event: ReactPointerEvent<HTMLElement>): void {
    if (flyoutMaximized || !flyoutRect) return;
    if (event.button !== 0) return;

    const target = event.target as HTMLElement;
    if (target.closest('[data-flyout-control="true"]')) return;

    flyoutDragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origin: flyoutRect,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
  }

  function handleFlyoutDragMove(event: ReactPointerEvent<HTMLElement>): void {
    const drag = flyoutDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    const next = {
      ...drag.origin,
      left: drag.origin.left + dx,
      top: drag.origin.top + dy,
    };
    const clamped = clampFlyoutRect(next, window.innerWidth, window.innerHeight);
    setFlyoutRect(clamped);
    flyoutRestoreRef.current = clamped;
  }

  function handleFlyoutDragEnd(event: ReactPointerEvent<HTMLElement>): void {
    const drag = flyoutDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    flyoutDragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function handleFlyoutResizeStart(event: ReactPointerEvent<HTMLDivElement>): void {
    if (flyoutMaximized || !flyoutRect) return;
    if (event.button !== 0) return;

    flyoutResizeRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origin: flyoutRect,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.stopPropagation();
    event.preventDefault();
  }

  function handleFlyoutResizeMove(event: ReactPointerEvent<HTMLDivElement>): void {
    const resize = flyoutResizeRef.current;
    if (!resize || resize.pointerId !== event.pointerId) return;

    const dx = event.clientX - resize.startX;
    const dy = event.clientY - resize.startY;
    const next = {
      ...resize.origin,
      width: resize.origin.width + dx,
      height: resize.origin.height + dy,
    };
    const clamped = clampFlyoutRect(next, window.innerWidth, window.innerHeight);
    setFlyoutRect(clamped);
    flyoutRestoreRef.current = clamped;
  }

  function handleFlyoutResizeEnd(event: ReactPointerEvent<HTMLDivElement>): void {
    const resize = flyoutResizeRef.current;
    if (!resize || resize.pointerId !== event.pointerId) return;
    flyoutResizeRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function toggleRow(row: ScreenerRow): void {
    const isActive = analysisOpen && selectedTicker === row.ticker;
    if (isActive) {
      closeAnalysis();
      return;
    }

    setAnalysisOpen(true);
    void loadChart(row.ticker);
  }

  function openAnalysisForTicker(ticker: string): void {
    if (!ticker) return;
    setAnalysisOpen(true);
    void loadChart(ticker);
  }

  function applyMapFilters(detail: MapDetailModel | null): void {
    if (!detail) return;
    const sectorFilterValue = detail.sector ? optionValueForLabel("sector", detail.sector) : "";
    const industryFilterValue = detail.industry ? optionValueForLabel("industry", detail.industry) : "";

    setAdvancedFilters((current) => ({
      ...current,
      sector: sectorFilterValue || "",
      industry: industryFilterValue || "",
    }));
    setDataTab("overview");
    setTab("overview");
    setPage(1);
  }

  function setMapHoverFromMouse(id: string, event: ReactMouseEvent<HTMLElement>): void {
    const canvasRect = mapViewportRef.current?.getBoundingClientRect();
    const rawX = canvasRect ? event.clientX - canvasRect.left : event.clientX;
    const rawY = canvasRect ? event.clientY - canvasRect.top : event.clientY;
    const nextX = clampNumber(rawX, 0, Math.max(0, mapViewportSize.width - 1));
    const nextY = clampNumber(rawY, 0, Math.max(0, mapViewportSize.height - 1));

    setMapHover((current) => {
      if (current && current.id === id && Math.abs(current.x - nextX) < 3 && Math.abs(current.y - nextY) < 3) {
        return current;
      }
      return { id, x: nextX, y: nextY };
    });
  }

  function resetMapView(): void {
    setMapFocusSector("");
    setMapFocusIndustry("");
    setMapHover(null);
    setMapSidebarSearch("");
    setMapShowEtf(false);
    setMapDataType("1d");
    const list = mapSidebarListRef.current;
    if (list) list.scrollTop = 0;
    const viewport = mapViewportRef.current;
    if (viewport) {
      viewport.scrollLeft = 0;
      viewport.scrollTop = 0;
    }
  }

  const tableColumns = useMemo(() => columnsForDataTab(dataTab), [dataTab]);

  const filteredRows = useMemo(() => rows, [rows]);

  const mapTickersWithMetric = useMemo(() => {
    return mapTickers.map((ticker) => {
      const quote = quoteByTicker[ticker.ticker];
      return {
        ...ticker,
        changePct: resolveMapTickerChangePct(ticker, quote, mapDataType),
      };
    });
  }, [mapDataType, mapTickers, quoteByTicker]);

  const mapRenderableTickers = useMemo(() => {
    const normalized = mapTickersWithMetric.map((ticker) => {
      const taxonomy = resolveMapTickerTaxonomy(ticker);
      return {
        ...ticker,
        sector: taxonomy.sector,
        industry: taxonomy.industry,
      };
    });

    const base = normalized.filter((ticker) => ticker.assetType !== "index" && ticker.assetType !== "crypto");
    const etfFiltered = mapShowEtf ? base : base.filter((ticker) => !isMapEtfTicker(ticker));
    const hasClassified = etfFiltered.some((ticker) => ticker.sector !== "Unclassified" || ticker.industry !== "Unclassified");

    if (!hasClassified) return etfFiltered;
    return etfFiltered.filter((ticker) => ticker.sector !== "Unclassified" || ticker.industry !== "Unclassified");
  }, [mapShowEtf, mapTickersWithMetric]);

  const mapModel = useMemo(() => {
    const sectors = new Map<
      string,
      {
        sector: string;
        marketCap: number;
        volume: number;
        tickers: number;
        changeWeighted: number;
        changeWeight: number;
        industries: Map<
          string,
          {
            industry: string;
            marketCap: number;
            volume: number;
            tickers: number;
            changeWeighted: number;
            changeWeight: number;
            symbols: ScreenerMapTicker[];
          }
        >;
      }
    >();

    for (const raw of mapRenderableTickers) {
      const ticker = String(raw.ticker ?? "").trim().toUpperCase();
      if (!ticker) continue;
      const sector = String(raw.sector ?? "").trim() || "Unclassified";
      const industry = String(raw.industry ?? "").trim() || "Unclassified";
      const marketCap = Math.max(0, Number(raw.marketCap) || 0);
      const volume = Math.max(0, Number(raw.volume) || 0);
      const changePct = isFiniteValue(raw.changePct) ? raw.changePct : null;
      const price = isFiniteValue(raw.price) ? raw.price : null;
      const symbol: ScreenerMapTicker = {
        ticker,
        companyName: raw.companyName ? String(raw.companyName) : null,
        sector,
        industry,
        assetType: raw.assetType,
        quoteType: raw.quoteType ?? null,
        marketCap,
        changePct,
        price,
        volume,
      };

      const sectorEntry = sectors.get(sector) ?? {
        sector,
        marketCap: 0,
        volume: 0,
        tickers: 0,
        changeWeighted: 0,
        changeWeight: 0,
        industries: new Map(),
      };

      const industryEntry = sectorEntry.industries.get(industry) ?? {
        industry,
        marketCap: 0,
        volume: 0,
        tickers: 0,
        changeWeighted: 0,
        changeWeight: 0,
        symbols: [],
      };

      const weight = marketCap > 0 ? marketCap : 1;
      sectorEntry.marketCap += marketCap;
      sectorEntry.volume += volume;
      sectorEntry.tickers += 1;
      if (changePct !== null) {
        sectorEntry.changeWeighted += changePct * weight;
        sectorEntry.changeWeight += weight;
      }

      industryEntry.marketCap += marketCap;
      industryEntry.volume += volume;
      industryEntry.tickers += 1;
      if (changePct !== null) {
        industryEntry.changeWeighted += changePct * weight;
        industryEntry.changeWeight += weight;
      }
      industryEntry.symbols.push(symbol);

      sectorEntry.industries.set(industry, industryEntry);
      sectors.set(sector, sectorEntry);
    }

    const byInfluence = (a: ScreenerMapTicker, b: ScreenerMapTicker): number => {
      const sizeA = mapSizeValue(a);
      const sizeB = mapSizeValue(b);
      if (sizeB !== sizeA) return sizeB - sizeA;
      if (b.volume !== a.volume) return b.volume - a.volume;
      return a.ticker.localeCompare(b.ticker);
    };

    const detailById = new Map<string, MapDetailModel>();
    const sectorList: MapSectorModel[] = [];

    for (const sectorEntry of sectors.values()) {
      const industryList: MapIndustryModel[] = [];
      const sectorMembers: ScreenerMapTicker[] = [];

      for (const industryEntry of sectorEntry.industries.values()) {
        const sortedSymbols = [...industryEntry.symbols].sort(byInfluence);
        const displaySymbols = sortedSymbols.slice(0, 120);
        sectorMembers.push(...sortedSymbols);
        const industryId = `industry:${sectorEntry.sector}::${industryEntry.industry}`;
        const industryModel: MapIndustryModel = {
          id: industryId,
          sector: sectorEntry.sector,
          industry: industryEntry.industry,
          marketCap: industryEntry.marketCap,
          volume: industryEntry.volume,
          tickers: industryEntry.tickers,
          avgChangePct: industryEntry.changeWeight > 0 ? industryEntry.changeWeighted / industryEntry.changeWeight : null,
          symbols: displaySymbols,
        };
        industryList.push(industryModel);

        detailById.set(industryId, {
          id: industryId,
          kind: "industry",
          sector: sectorEntry.sector,
          industry: industryEntry.industry,
          ticker: "",
          name: industryEntry.industry,
          companyName: null,
          marketCap: industryEntry.marketCap,
          volume: industryEntry.volume,
          tickers: industryEntry.tickers,
          changePct: industryModel.avgChangePct,
          price: null,
          members: sortedSymbols,
        });

        for (const symbol of sortedSymbols) {
          const tickerId = `ticker:${symbol.ticker}`;
          detailById.set(tickerId, {
            id: tickerId,
            kind: "ticker",
            sector: symbol.sector,
            industry: symbol.industry,
            ticker: symbol.ticker,
            name: symbol.ticker,
            companyName: symbol.companyName,
            marketCap: symbol.marketCap,
            volume: symbol.volume,
            tickers: 1,
            changePct: symbol.changePct,
            price: symbol.price,
            members: [symbol],
          });
        }
      }

      const sortedIndustries = industryList.sort((a, b) => b.marketCap - a.marketCap);
      const sortedMembers = [...sectorMembers].sort(byInfluence);
      const sectorId = `sector:${sectorEntry.sector}`;
      const sectorModel: MapSectorModel = {
        id: sectorId,
        sector: sectorEntry.sector,
        marketCap: sectorEntry.marketCap,
        volume: sectorEntry.volume,
        tickers: sectorEntry.tickers,
        avgChangePct: sectorEntry.changeWeight > 0 ? sectorEntry.changeWeighted / sectorEntry.changeWeight : null,
        industries: sortedIndustries,
        leaders: sortedMembers.slice(0, 120),
      };

      detailById.set(sectorId, {
        id: sectorId,
        kind: "sector",
        sector: sectorEntry.sector,
        industry: "",
        ticker: "",
        name: sectorEntry.sector,
        companyName: null,
        marketCap: sectorEntry.marketCap,
        volume: sectorEntry.volume,
        tickers: sectorEntry.tickers,
        changePct: sectorModel.avgChangePct,
        price: null,
        members: sortedMembers,
      });

      sectorList.push(sectorModel);
    }

    sectorList.sort((a, b) => b.marketCap - a.marketCap);

    return {
      sectors: sectorList,
      detailById,
    };
  }, [mapRenderableTickers]);

  const mapActiveSector = useMemo(
    () => mapModel.sectors.find((sector) => sector.sector === mapFocusSector) ?? null,
    [mapModel.sectors, mapFocusSector],
  );

  const mapActiveIndustry = useMemo(() => {
    if (!mapActiveSector || !mapFocusIndustry) return null;
    return mapActiveSector.industries.find((industry) => industry.industry === mapFocusIndustry) ?? null;
  }, [mapActiveSector, mapFocusIndustry]);

  const mapSectorTotal = useMemo(
    () => mapModel.sectors.reduce((sum, sector) => sum + (sector.marketCap > 0 ? sector.marketCap : sector.tickers), 0),
    [mapModel.sectors],
  );

  const mapDefaultDetailId = useMemo(() => {
    if (mapActiveIndustry) return mapActiveIndustry.id;
    if (mapActiveSector) return mapActiveSector.id;
    return mapModel.sectors[0]?.id ?? "";
  }, [mapActiveIndustry, mapActiveSector, mapModel.sectors]);

  const mapPrimaryDetail = useMemo(() => {
    const key = mapHover?.id || mapDefaultDetailId;
    if (!key) return null;
    return mapModel.detailById.get(key) ?? null;
  }, [mapDefaultDetailId, mapHover, mapModel.detailById]);

  const mapHoverDetail = useMemo(() => {
    const key = mapHover?.id ?? "";
    if (!key) return null;
    return mapModel.detailById.get(key) ?? null;
  }, [mapHover, mapModel.detailById]);

  const mapLayout = useMemo(() => {
    const width = Math.max(960, Math.floor(mapViewportSize.width));
    const height = Math.max(560, Math.floor(mapViewportSize.height));
    const baseRect: MapRect = { x: 0, y: 0, width, height };
    const sectorScope = mapActiveSector ? [mapActiveSector] : mapModel.sectors;
    const sectorRects = layoutTreemap(
      sectorScope.map((sector) => ({
        data: sector,
        value: sector.marketCap > 0 ? sector.marketCap : sector.tickers,
      })),
      baseRect,
    );

    const layout: MapSectorLayout[] = sectorRects.map((entry) => {
      const sectorRect = insetRect(entry.rect, 2);
      const sectorHeader = sectorRect.height >= 92 ? 20 : sectorRect.height >= 56 ? 16 : 0;
      const industryRect = {
        x: sectorRect.x + 1,
        y: sectorRect.y + sectorHeader,
        width: Math.max(0, sectorRect.width - 2),
        height: Math.max(0, sectorRect.height - sectorHeader - 1),
      };
      const industryScope = mapActiveIndustry && mapActiveIndustry.sector === entry.data.sector ? [mapActiveIndustry] : entry.data.industries;
      const industryRects = layoutTreemap(
        industryScope.map((industry) => ({
          data: industry,
          value: industry.marketCap > 0 ? industry.marketCap : industry.tickers,
        })),
        industryRect,
      );

      const industries: MapIndustryLayout[] = industryRects.map((industryEntry) => {
        const industryFrame = insetRect(industryEntry.rect, 1);
        const industryHeader = industryFrame.height >= 64 ? 14 : 0;
        const tickerRect = {
          x: industryFrame.x + 1,
          y: industryFrame.y + industryHeader,
          width: Math.max(0, industryFrame.width - 2),
          height: Math.max(0, industryFrame.height - industryHeader - 1),
        };
        const tickerRects = layoutTreemap(
          industryEntry.data.symbols.map((symbol) => ({
            data: symbol,
            value: mapSizeValue(symbol),
          })),
          tickerRect,
        );

        return {
          industry: industryEntry.data,
          rect: industryFrame,
          headerHeight: industryHeader,
          tickers: tickerRects.map((tickerEntry) => ({
            ticker: tickerEntry.data,
            rect: insetRect(tickerEntry.rect, 0.6),
          })),
        };
      });

      return {
        sector: entry.data,
        rect: sectorRect,
        headerHeight: sectorHeader,
        industries,
      };
    });

    return { width, height, sectors: layout };
  }, [mapActiveIndustry, mapActiveSector, mapModel.sectors, mapViewportSize.height, mapViewportSize.width]);

  const mapHoverMembers = useMemo(() => {
    if (!mapHoverDetail) return [];
    return [...mapHoverDetail.members]
      .sort((a, b) => {
        const sizeA = mapSizeValue(a);
        const sizeB = mapSizeValue(b);
        if (sizeB !== sizeA) return sizeB - sizeA;
        return a.ticker.localeCompare(b.ticker);
      })
      .slice(0, 20);
  }, [mapHoverDetail]);

  const mapSidebarRows = useMemo(() => {
    const needle = mapSidebarSearch.trim().toUpperCase();
    const filtered = mapRenderableTickers.filter((ticker) => {
      if (!needle) return true;
      const symbol = ticker.ticker.toUpperCase();
      const company = String(ticker.companyName ?? "").toUpperCase();
      const sector = String(ticker.sector ?? "").toUpperCase();
      const industry = String(ticker.industry ?? "").toUpperCase();
      return symbol.includes(needle) || company.includes(needle) || sector.includes(needle) || industry.includes(needle);
    });

    return filtered.sort((a, b) => a.ticker.localeCompare(b.ticker));
  }, [mapRenderableTickers, mapSidebarSearch]);

  const mapSidebarVisibleRows = useMemo(() => mapSidebarRows.slice(0, 560), [mapSidebarRows]);

  const mapHoverPanelStyle = useMemo(() => {
    if (!mapHover || !mapHoverDetail) return null;
    const maxWidth = 360;
    const width = Math.min(maxWidth, Math.max(280, Math.floor(mapViewportSize.width * 0.34)));
    const estimatedHeight = Math.min(530, 112 + mapHoverMembers.length * 24);
    const margin = 10;
    let left = mapHover.x + 14;
    let top = mapHover.y + 14;
    if (left + width + margin > mapViewportSize.width) {
      left = Math.max(margin, mapHover.x - width - 14);
    }
    if (top + estimatedHeight + margin > mapViewportSize.height) {
      top = Math.max(margin, mapViewportSize.height - estimatedHeight - margin);
    }
    return {
      left: Math.round(left),
      top: Math.round(top),
      width: Math.round(width),
    };
  }, [mapHover, mapHoverDetail, mapHoverMembers.length, mapViewportSize.height, mapViewportSize.width]);

  const mapAsOfText = fmtMapAsOfNow();

  useEffect(() => {
    if (dataTab !== "maps") return;
    if (!mapFocusSector) {
      if (mapFocusIndustry) setMapFocusIndustry("");
      return;
    }

    const sectorExists = mapModel.sectors.some((sector) => sector.sector === mapFocusSector);
    if (!sectorExists) {
      setMapFocusSector("");
      setMapFocusIndustry("");
      return;
    }

    if (mapFocusIndustry) {
      const industryExists =
        mapModel.sectors
          .find((sector) => sector.sector === mapFocusSector)
          ?.industries.some((industry) => industry.industry === mapFocusIndustry) ?? false;
      if (!industryExists) setMapFocusIndustry("");
    }
  }, [dataTab, mapFocusIndustry, mapFocusSector, mapModel.sectors]);

  useEffect(() => {
    if (dataTab !== "maps") return;
    const element = mapViewportRef.current;
    if (!element) return;

    const updateSize = (): void => {
      const rect = element.getBoundingClientRect();
      const width = Math.max(960, Math.floor(rect.width || element.clientWidth));
      const height = Math.max(560, Math.floor(rect.height || element.clientHeight));
      setMapViewportSize((current) => {
        if (current.width === width && current.height === height) return current;
        return { width, height };
      });
    };

    updateSize();
    const observer = new ResizeObserver(() => updateSize());
    observer.observe(element);
    return () => observer.disconnect();
  }, [dataTab]);

  useEffect(() => {
    if (dataTab === "maps") return;
    setMapHover(null);
  }, [dataTab]);

  const newsFocusQuote = useMemo(() => {
    const base = quoteOrDefault(quoteByTicker[newsFocusTicker]);
    return {
      ...base,
      ...newsPanelQuote,
    };
  }, [newsFocusTicker, newsPanelQuote, quoteByTicker]);

  const newsFocusStoryList = useMemo(() => {
    const fromPanel = Array.isArray(newsPanelStories) ? newsPanelStories : [];
    const fromCache = Array.isArray(newsFocusQuote.news) ? newsFocusQuote.news : [];
    const merged = fromPanel.length > 0 ? fromPanel : fromCache;
    return [...merged].sort((a, b) => (b.publishedAt ?? 0) - (a.publishedAt ?? 0));
  }, [newsFocusQuote.news, newsPanelStories]);

  const groupedNewsStories = useMemo(() => {
    const buckets = new Map<
      string,
      {
        label: string;
        sortTs: number;
        items: NewsItem[];
      }
    >();

    for (const item of newsFocusStoryList) {
      const ts = typeof item.publishedAt === "number" ? item.publishedAt : 0;
      const key = ts > 0 ? fmtNewsDayLabel(ts) : "Undated";
      const entry = buckets.get(key) ?? { label: key, sortTs: ts, items: [] };
      entry.items.push(item);
      if (ts > entry.sortTs) entry.sortTs = ts;
      buckets.set(key, entry);
    }

    return Array.from(buckets.values()).sort((a, b) => b.sortTs - a.sortTs);
  }, [newsFocusStoryList]);

  const newsFocusStatColumns = useMemo(
    () =>
      buildMarketStatColumns({
        quote: newsFocusQuote,
        chartSummary: newsPanelSummary,
        chartBars: newsPanelBars,
      }),
    [newsFocusQuote, newsPanelBars, newsPanelSummary],
  );

  const newsFocusHighlights = useMemo(() => {
    return {
      company: fmtText(newsFocusQuote.companyName ?? newsFocusRow?.ticker ?? newsFocusTicker),
      country: fmtText(newsFocusQuote.country),
      industry: fmtText(newsFocusQuote.industry),
      marketCap: fmtCompactNumber(newsFocusQuote.marketCap),
      pe: fmtNum(newsFocusQuote.peRatio, 2),
      eps: fmtNum(newsFocusQuote.eps, 2),
      avgVolume: fmtCompactNumber(newsFocusQuote.avgVolume),
      change: fmtPercentSigned(newsFocusQuote.changePct),
      price: fmtPrice(newsFocusQuote.price ?? newsFocusRow?.price ?? null),
    };
  }, [newsFocusQuote, newsFocusRow, newsFocusTicker]);

  const newsFocusQuickStats = useMemo(() => newsFocusStatColumns.slice(0, 3).flat().slice(0, 15), [newsFocusStatColumns]);

  const advancedFilterOptions = ADVANCED_FILTER_OPTIONS;
  const activeFilterMatrix = useMemo(() => {
    return SCREENER_FILTER_GROUP_LAYOUTS[filterGroup] ?? [];
  }, [filterGroup]);

  const paginationNumberPages = useMemo(() => {
    const safeTotalPages = Math.max(1, totalPages);
    const pages = new Set<number>();
    const firstRangeEnd = Math.min(6, safeTotalPages);
    for (let current = 1; current <= firstRangeEnd; current += 1) {
      pages.add(current);
    }
    for (let current = 100; current <= safeTotalPages; current += 100) {
      pages.add(current);
    }
    pages.add(safeTotalPages);
    pages.add(Math.min(Math.max(1, page), safeTotalPages));
    return Array.from(pages).sort((a, b) => a - b);
  }, [page, totalPages]);

  const paginationTokens = useMemo(() => {
    const tokens: Array<{ kind: "page"; value: number } | { kind: "ellipsis"; key: string }> = [];
    let previous = 0;
    for (const current of paginationNumberPages) {
      if (previous > 0 && current - previous > 1) {
        tokens.push({ kind: "ellipsis", key: `ellipsis-${previous}-${current}` });
      }
      tokens.push({ kind: "page", value: current });
      previous = current;
    }
    return tokens;
  }, [paginationNumberPages]);

  function capturePresetState(): ScreenerPresetState {
    return {
      tab,
      dataTab,
      filterGroup,
      search,
      assetType,
      signal,
      minPrice,
      maxPrice,
      minBars,
      maxBars,
      sortKey,
      sortDir,
      pageSize,
      advancedFilters: { ...advancedFilters },
    };
  }

  function applyPresetState(record: ScreenerPresetRecord): void {
    const state = record.state;
    setTab(state.tab);
    setDataTab(state.dataTab);
    setFilterGroup(state.filterGroup);
    setSearch(state.search);
    setAssetType(state.assetType);
    setSignal(state.signal);
    setMinPrice(state.minPrice);
    setMaxPrice(state.maxPrice);
    setMinBars(state.minBars);
    setMaxBars(state.maxBars);
    setSortKey(state.sortKey);
    setSortDir(state.sortDir);
    setPageSize(state.pageSize);
    setAdvancedFilters({
      ...ADVANCED_FILTER_DEFAULTS,
      ...(state.advancedFilters ?? {}),
    });
    setPage(1);
    setSelectedPresetId(record.id);
    setPresetNotice(`Loaded preset: ${record.name}`);
  }

  function upsertPresetRecord(nameInput: string): void {
    const name = toPresetName(nameInput);
    if (!name) {
      setPresetNotice("Preset name is required.");
      return;
    }
    const now = new Date().toISOString();
    const existing = presetRecords.find((record) => record.name.toLowerCase() === name.toLowerCase());
    const nextRecord: ScreenerPresetRecord = existing
      ? {
          ...existing,
          name,
          updatedAtUtc: now,
          state: capturePresetState(),
        }
      : {
          id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
          name,
          createdAtUtc: now,
          updatedAtUtc: now,
          state: capturePresetState(),
        };

    const merged = existing
      ? presetRecords.map((record) => (record.id === existing.id ? nextRecord : record))
      : [nextRecord, ...presetRecords];

    const limited = merged
      .sort((a, b) => String(b.updatedAtUtc).localeCompare(String(a.updatedAtUtc)))
      .slice(0, SCREENER_PRESET_MAX_COUNT);

    setPresetRecords(limited);
    setSelectedPresetId(nextRecord.id);
    setPresetNotice(existing ? `Updated preset: ${name}` : `Saved preset: ${name}`);
  }

  function saveCurrentPreset(): void {
    const fallback = selectedPresetId ? presetRecords.find((record) => record.id === selectedPresetId)?.name ?? "" : "";
    const response = window.prompt("Save Screen preset name", fallback);
    if (response === null) return;
    upsertPresetRecord(response);
  }

  function renamePreset(record: ScreenerPresetRecord): void {
    const response = window.prompt("Rename preset", record.name);
    if (response === null) return;
    const name = toPresetName(response);
    if (!name) {
      setPresetNotice("Preset name is required.");
      return;
    }
    setPresetRecords((current) =>
      current.map((entry) =>
        entry.id === record.id
          ? {
              ...entry,
              name,
              updatedAtUtc: new Date().toISOString(),
            }
          : entry,
      ),
    );
    setPresetNotice(`Renamed preset to: ${name}`);
  }

  function deletePreset(record: ScreenerPresetRecord): void {
    const ok = window.confirm(`Delete preset \"${record.name}\"?`);
    if (!ok) return;
    setPresetRecords((current) => current.filter((entry) => entry.id !== record.id));
    if (selectedPresetId === record.id) {
      setSelectedPresetId("");
    }
    setPresetNotice(`Deleted preset: ${record.name}`);
  }

  function applyColumnSort(columnId: string): void {
    const mappedSortKey = COLUMN_SORT_KEY_BY_ID[columnId];
    if (!mappedSortKey) return;

    setPage(1);
    if (sortKey === mappedSortKey) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortKey(mappedSortKey);
    setSortDir("asc");
  }

  return (
    <div className="section-stack">
      <section className="tfe-panel">
        <div className="tfe-toolbar-grid" style={{ gridTemplateColumns: "220px 260px 100px 220px minmax(0, 1fr) 96px" }}>
          <select
            className="tfe-select"
            value={selectedPresetId}
            onChange={(event) => {
              const nextId = String(event.target.value ?? "");
              if (nextId === PRESET_ACTION_SAVE) {
                saveCurrentPreset();
                return;
              }
              if (nextId === PRESET_ACTION_EDIT) {
                setPresetEditorOpen((current) => !current);
                return;
              }
              setSelectedPresetId(nextId);
              if (!nextId) return;
              const selected = presetRecords.find((record) => record.id === nextId);
              if (!selected) return;
              applyPresetState(selected);
            }}
          >
            <option value="">My Presets</option>
            <option value={PRESET_ACTION_SAVE}>Save Screen...</option>
            <option value={PRESET_ACTION_EDIT}>{presetEditorOpen ? "Close Edit Screens..." : "Edit Screens..."}</option>
            {presetRecords.map((record) => (
              <option key={record.id} value={record.id}>
                {record.name}
              </option>
            ))}
            {presetRecords.length === 0 ? <option value="" disabled>No saved presets yet</option> : null}
          </select>

          <select className="tfe-select" value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
            {SUPPORTED_ORDER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                Order by {option.label}
              </option>
            ))}
          </select>

          <select className="tfe-select" value={sortDir} onChange={(event) => setSortDir(event.target.value as SortDirection)}>
            <option value="asc">Asc</option>
            <option value="desc">Desc</option>
          </select>

          <select className="tfe-select" value={signal} onChange={(event) => setSignal(event.target.value)}>
            {SCREENER_SIGNAL_OPTIONS.map((option) => (
              <option key={`signal-${option.value || "none"}`} value={option.value}>
                Signal: {option.label}
              </option>
            ))}
          </select>

          <input
            className="tfe-input"
            value={search}
            onChange={(event) => setSearch(event.target.value.toUpperCase())}
            placeholder="Tickers"
            autoComplete="off"
            spellCheck={false}
          />

          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => setFiltersVisible((current) => !current)}
            aria-expanded={filtersVisible}
          >
            {filtersVisible ? "Hide Filters" : "Show Filters"}
          </button>
        </div>

        <div className="tfe-toolbar-actions" style={{ marginTop: 8, gap: 8, flexWrap: "wrap" }}>
          <button type="button" className="btn btn-ghost" onClick={() => saveCurrentPreset()}>
            Save Screen
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => setPresetEditorOpen((current) => !current)}>
            {presetEditorOpen ? "Close Edit Screens" : "Edit Screens"}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              setPage(1);
              setAdvancedFilters(ADVANCED_FILTER_DEFAULTS);
              setSearch("");
              setAssetType("");
              setSignal("");
              setMinPrice("");
              setMaxPrice("");
              setMinBars("");
              setMaxBars("");
              setSortKey(SUPPORTED_ORDER_OPTIONS[0]?.value ?? "ticker");
              setSortDir("asc");
              setFilterGroup("descriptive");
              setPresetNotice("Filters reset.");
            }}
          >
            Reset Filters
          </button>
        </div>

        {presetNotice ? (
          <p className="tfe-muted" style={{ marginTop: 8, marginBottom: 0 }}>
            {presetNotice}
          </p>
        ) : null}

        {presetEditorOpen ? (
          <div className="tfe-table-wrap" style={{ marginTop: 8, maxHeight: 260 }}>
            <table className="tfe-table" style={{ minWidth: 680 }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Updated (UTC)</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {presetRecords.length === 0 ? (
                  <tr>
                    <td colSpan={3}>No presets saved.</td>
                  </tr>
                ) : (
                  presetRecords.map((record) => (
                    <tr key={`preset-row-${record.id}`}>
                      <td>{record.name}</td>
                      <td>{record.updatedAtUtc || "n/a"}</td>
                      <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                        <button type="button" className="btn btn-ghost" onClick={() => applyPresetState(record)}>
                          Load
                        </button>
                        <button type="button" className="btn btn-ghost" onClick={() => renamePreset(record)}>
                          Rename
                        </button>
                        <button type="button" className="btn btn-ghost" onClick={() => deletePreset(record)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : null}

        {filtersVisible ? (
          <>
            <div className="tfe-toolbar-actions" style={{ marginTop: 8, flexWrap: "wrap" }}>
              {FILTER_GROUPS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={filterGroup === item.id ? "btn btn-primary" : "btn btn-ghost"}
                  onClick={() => {
                    setFilterGroup(item.id);
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="tfe-toolbar-grid" style={{ marginTop: 8, gridTemplateColumns: "220px 170px 170px 130px 130px" }}>
              <select className="tfe-select" value={assetType} onChange={(event) => setAssetType(event.target.value)}>
                <option value="">Asset: Any</option>
                {assetOptions.map((value) => (
                  <option key={value} value={value}>
                    Asset: {formatAssetType(value)}
                  </option>
                ))}
              </select>

              <input
                className="tfe-input"
                value={minPrice}
                onChange={(event) => setMinPrice(event.target.value)}
                placeholder="Min Price"
                inputMode="decimal"
              />

              <input
                className="tfe-input"
                value={maxPrice}
                onChange={(event) => setMaxPrice(event.target.value)}
                placeholder="Max Price"
                inputMode="decimal"
              />

              <input
                className="tfe-input"
                value={minBars}
                onChange={(event) => setMinBars(event.target.value)}
                placeholder="Min Bars"
                inputMode="numeric"
              />

              <input
                className="tfe-input"
                value={maxBars}
                onChange={(event) => setMaxBars(event.target.value)}
                placeholder="Max Bars"
                inputMode="numeric"
              />
            </div>
          </>
        ) : null}
      </section>

      {filtersVisible ? (
        <section className="tfe-toolbar-actions" aria-label="Screener filters">
          <div className="tfe-toolbar-grid tfe-advanced-filter-grid">
            {activeFilterMatrix.map((row, rowIndex) =>
              row.map((cell) => (
                <div key={`${cell.key}-${rowIndex}`} className="tfe-field tfe-field-inline">
                  <label className="tfe-field-inline-label" htmlFor={`screener-filter-${cell.key}`}>
                    {cell.label}
                  </label>
                  <select
                    id={`screener-filter-${cell.key}`}
                    className="tfe-select tfe-select-compact"
                    value={advancedFilters[cell.key]}
                    onChange={(event) => {
                      const value = event.target.value;
                      setAdvancedFilters((current) => ({
                        ...current,
                        [cell.key]: value,
                      }));
                    }}
                  >
                    {(advancedFilterOptions[cell.key] ?? []).map((option, optionIndex) => (
                      <option key={`${cell.key}-${option.value}-${optionIndex}`} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              )),
            )}
          </div>
        </section>
      ) : null}

      <section className="tfe-toolbar-actions" aria-label="Screener data tabs">
        {DATA_TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={dataTab === item.key ? "btn btn-primary" : "btn btn-ghost"}
            onClick={() => {
              setDataTab(item.key);
              if (API_DATA_TABS.includes(item.key as ScreenerTab)) {
                setTab(item.key as ScreenerTab);
              }
            }}
          >
            {item.label}
          </button>
        ))}
      </section>

      <p className="tfe-muted" style={{ marginTop: 0 }}>
        Market-style market-field filters and map cells apply to the full filtered universe using live quote enrichment.
      </p>
      {advancedExternalMeta && advancedExternalMeta.sourceConfigured === false ? (
        <p className="tfe-error" style={{ marginTop: 0 }}>
          External filter feed is not configured. Selected region/theme/sub-theme filters cannot be resolved.
        </p>
      ) : null}
      {advancedExternalMeta?.theme?.requested && advancedExternalMeta.theme.resolved === false ? (
        <p className="tfe-error" style={{ marginTop: 0 }}>
          Theme filter source request failed for {advancedExternalMeta.theme.requested}. Results may be incomplete.
        </p>
      ) : null}
      {advancedExternalMeta?.subTheme?.requested && advancedExternalMeta.subTheme.resolved === false ? (
        <p className="tfe-error" style={{ marginTop: 0 }}>
          Sub-theme filter source request failed for {advancedExternalMeta.subTheme.requested}. Results may be incomplete.
        </p>
      ) : null}
      {advancedExternalMeta?.country?.requested && advancedExternalMeta.country.resolved === false ? (
        <p className="tfe-error" style={{ marginTop: 0 }}>
          Region filter source request failed for {advancedExternalMeta.country.requested}. Results may be incomplete.
        </p>
      ) : null}

      {dataTab === "newsTab" ? (
        <section className="tfe-panel tfe-news-tab-surface" aria-label="News screener workspace">
          <div className="tfe-news-tab-head">
            <div>
              <strong>News Workspace</strong>
              <span>
                {newsFocusTicker
                  ? `${newsFocusTicker} · ${newsFocusHighlights.company}`
                  : "Select a ticker from the table to load chart + stories."}
              </span>
            </div>
            <div className="tfe-news-tab-head-actions">
              {newsFocusRow ? <span className={`tfe-chip ${toDecisionClass(newsFocusRow.decision)}`}>{newsFocusRow.decision}</span> : null}
              {newsFocusTicker ? (
                <button
                  type="button"
                  className="btn btn-ghost tfe-news-open-detail"
                  onClick={() => {
                    setAnalysisOpen(true);
                    void loadChart(newsFocusTicker);
                  }}
                >
                  Open Detail
                </button>
              ) : null}
            </div>
          </div>

          {newsFocusTicker ? (
            <>
              <div className="tfe-news-tab-grid">
                <section className="tfe-news-chart-shell">
                  <ScreenerChart
                    ticker={newsFocusTicker}
                    bars={newsPanelBars}
                    controls={newsChartControls}
                    loading={newsPanelLoading}
                    onControlsChange={(next) => setNewsChartControls(next)}
                  />
                  {newsPanelError ? <p className="tfe-error">{newsPanelError}</p> : null}
                  {!newsPanelError && newsPanelNote ? <p className="tfe-muted">{newsPanelNote}</p> : null}
                </section>

                <aside className="tfe-news-stat-shell">
                  <div className="tfe-news-quote-grid">
                    <div className="k">Ticker</div>
                    <div className="v">{newsFocusTicker}</div>
                    <div className="k">Company</div>
                    <div className="v">{newsFocusHighlights.company}</div>
                    <div className="k">Country</div>
                    <div className="v">{newsFocusHighlights.country}</div>
                    <div className="k">Industry</div>
                    <div className="v">{newsFocusHighlights.industry}</div>
                    <div className="k">Market Cap</div>
                    <div className="v">{newsFocusHighlights.marketCap}</div>
                    <div className="k">P/E</div>
                    <div className="v">{newsFocusHighlights.pe}</div>
                    <div className="k">EPS (TTM)</div>
                    <div className="v">{newsFocusHighlights.eps}</div>
                    <div className="k">Avg Volume</div>
                    <div className="v">{newsFocusHighlights.avgVolume}</div>
                    <div className="k">Price</div>
                    <div className="v">{newsFocusHighlights.price}</div>
                    <div className="k">Change</div>
                    <div className="v">{newsFocusHighlights.change}</div>
                  </div>

                  <table className="tfe-news-quick-stats">
                    <tbody>
                      {newsFocusQuickStats.map((cell) => (
                        <tr key={`${cell.label}-${cell.value}`}>
                          <td className="k">{cell.label}</td>
                          <td className={inferTone(cell.value) ? `v tone-${inferTone(cell.value)}` : "v"}>{cell.value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </aside>
              </div>

              <section className="tfe-news-feed-shell">
                {newsFocusStoryList.length === 0 ? (
                  <p className="tfe-muted" style={{ marginBottom: 0 }}>
                    No news stories are currently available for {newsFocusTicker}.
                  </p>
                ) : (
                  groupedNewsStories.map((group) => (
                    <div key={`news-group-${group.label}`} className="tfe-news-feed-day">
                      <h4>{group.label}</h4>
                      <ul>
                        {group.items.slice(0, 14).map((item, idx) => (
                          <li key={`${item.link}-${idx}`}>
                            <span className="time">{fmtClockTime(item.publishedAt)}</span>
                            <a href={item.link} target="_blank" rel="noreferrer noopener">
                              {item.title}
                            </a>
                            <span className="publisher">{item.publisher || "Source unavailable"}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))
                )}
              </section>
            </>
          ) : (
            <p className="tfe-muted" style={{ marginBottom: 0 }}>
              No ticker rows are available to populate the News workspace.
            </p>
          )}
        </section>
      ) : null}

      {dataTab === "maps" ? (
        <section className="tfe-panel tfe-map-shell" aria-label="Ticker treemap">
          <div className="tfe-map-topbar">
            <div className="tfe-map-view-toggle">
              <span>View</span>
              <strong>Map</strong>
            </div>
            <p className="tfe-map-topbar-note">All stocks listed on US stock exchanges, categorized by sectors and industries. Stock size represents market cap.</p>
            <div className="tfe-map-topbar-right">
              <button type="button" className="btn btn-ghost" onClick={resetMapView}>
                Reset View
              </button>
              <span className="tfe-map-asof">{mapAsOfText} ET</span>
            </div>
          </div>

          {mapModel.sectors.length === 0 ? (
            <p className="tfe-muted" style={{ marginBottom: 0 }}>
              No symbols available to render map.
            </p>
          ) : (
            <div className="tfe-map-workspace">
              <aside className="tfe-map-sidebar">
                <div className="tfe-map-sidebar-controls">
                  <label className="tfe-map-control-block">
                    <span>Data Type</span>
                    <select className="tfe-select" value={mapDataType} onChange={(event) => setMapDataType(event.target.value as MapDataType)}>
                      {MAP_DATA_TYPE_OPTIONS.map((option) => (
                        <option key={`map-data-type-${option.value}`} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="tfe-map-sidebar-check">
                    <input type="checkbox" checked={mapShowEtf} onChange={(event) => setMapShowEtf(event.target.checked)} />
                    Show ETFs
                  </label>
                  <label className="tfe-map-control-block">
                    <span>Quick search ticker</span>
                    <input
                      className="tfe-input"
                      type="search"
                      placeholder="Quick search ticker"
                      value={mapSidebarSearch}
                      onChange={(event) => setMapSidebarSearch(event.target.value)}
                    />
                  </label>
                </div>

                <div className="tfe-map-sidebar-list-head">
                  <strong>
                    {mapSidebarRows.length} symbols | {mapModel.sectors.length} sectors | {fmtCompactNumber(mapSectorTotal)} total cap
                  </strong>
                  <span>
                    Focus: {mapPrimaryDetail ? mapPrimaryDetail.name : "All Sectors"}
                    {mapSidebarRows.length > mapSidebarVisibleRows.length ? ` | showing first ${mapSidebarVisibleRows.length}` : ""}
                  </span>
                </div>

                <div ref={mapSidebarListRef} className="tfe-map-sidebar-list-wrap">
                  <ul className="tfe-map-sidebar-list">
                    {mapSidebarVisibleRows.map((symbol) => {
                      const id = `ticker:${symbol.ticker}`;
                      return (
                        <li key={`map-sidebar-${symbol.ticker}`} className={mapHover?.id === id ? "is-active" : ""}>
                          <button
                            type="button"
                            onMouseEnter={(event) => setMapHoverFromMouse(id, event)}
                            onMouseMove={(event) => setMapHoverFromMouse(id, event)}
                            onClick={() => openAnalysisForTicker(symbol.ticker)}
                          >
                            <span className="ticker">{symbol.ticker}</span>
                            <span className="company">{fmtText(symbol.companyName)}</span>
                          </button>
                          <span className={`change ${mapToneClass(symbol.changePct)}`}>{fmtPercentSigned(symbol.changePct)}</span>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                <p className="tfe-map-sidebar-footnote">
                  Only the ticker with the highest market cap for each company is included. Use the grid cells for sector and industry filtering.
                </p>
              </aside>

              <div className="tfe-map-canvas-wrap">
                <div ref={mapViewportRef} className="tfe-map-canvas" onMouseLeave={() => setMapHover(null)}>
                  <div className="tfe-map-stage" style={{ width: mapLayout.width, height: mapLayout.height }}>
                    {mapLayout.sectors.map((sectorLayout) => {
                      const sector = sectorLayout.sector;
                      const sectorId = sector.id;
                      const showSectorLabel = sectorLayout.headerHeight > 0 && sectorLayout.rect.width > 74;

                      return (
                        <section
                          key={sectorId}
                          className={`tfe-map-sector-block ${mapToneClass(sector.avgChangePct)}`}
                          style={mapRectStyle(sectorLayout.rect)}
                          onMouseEnter={(event) => setMapHoverFromMouse(sectorId, event)}
                          onMouseMove={(event) => setMapHoverFromMouse(sectorId, event)}
                          data-map-cell="true"
                        >
                          {showSectorLabel ? (
                            <button
                              type="button"
                              className="tfe-map-sector-label"
                              style={{
                                background: mapHeaderColorForChangePct(sector.avgChangePct),
                                height: sectorLayout.headerHeight,
                              }}
                              onClick={() => {
                                setMapFocusSector(sector.sector);
                                setMapFocusIndustry("");
                              }}
                              onDoubleClick={() => applyMapFilters(mapModel.detailById.get(sectorId) ?? null)}
                              title={`${sector.sector} | ${sector.tickers} tickers`}
                              data-map-cell="true"
                            >
                              <strong>{sector.sector}</strong>
                            </button>
                          ) : null}

                          <div className="tfe-map-sector-layer">
                            {sectorLayout.industries.map((industryLayout) => {
                              const industry = industryLayout.industry;
                              const industryId = industry.id;
                              const showIndustryLabel =
                                industryLayout.headerHeight > 0 && industryLayout.rect.width > 98 && industryLayout.rect.height > 42;

                              return (
                                <article
                                  key={industryId}
                                  className={`tfe-map-industry-block ${mapToneClass(industry.avgChangePct)}`}
                                  style={mapRectStyleRelative(industryLayout.rect, sectorLayout.rect)}
                                  onMouseEnter={(event) => setMapHoverFromMouse(industryId, event)}
                                  onMouseMove={(event) => setMapHoverFromMouse(industryId, event)}
                                  data-map-cell="true"
                                >
                                  {showIndustryLabel ? (
                                    <button
                                      type="button"
                                      className="tfe-map-industry-label"
                                      style={{
                                        background: mapHeaderColorForChangePct(industry.avgChangePct),
                                        height: industryLayout.headerHeight,
                                      }}
                                      onClick={() => {
                                        setMapFocusSector(industry.sector);
                                        setMapFocusIndustry(industry.industry);
                                      }}
                                      onDoubleClick={() => applyMapFilters(mapModel.detailById.get(industryId) ?? null)}
                                      title={`${industry.industry} | ${industry.tickers} tickers`}
                                      data-map-cell="true"
                                    >
                                      <strong>{industry.industry}</strong>
                                    </button>
                                  ) : null}

                                  <div className="tfe-map-industry-layer">
                                    {industryLayout.tickers.map((tickerLayout) => {
                                      const symbol = tickerLayout.ticker;
                                      const tickerId = `ticker:${symbol.ticker}`;
                                      const area = tickerLayout.rect.width * tickerLayout.rect.height;
                                      const showTicker = area > 900 || (tickerLayout.rect.width > 50 && tickerLayout.rect.height > 24);
                                      const showFull = area > 4200 || (tickerLayout.rect.width > 112 && tickerLayout.rect.height > 54);

                                      return (
                                        <button
                                          key={tickerId}
                                          type="button"
                                          className={`tfe-map-ticker ${mapToneClass(symbol.changePct)}`}
                                          style={{
                                            ...mapRectStyleRelative(tickerLayout.rect, industryLayout.rect),
                                            background: heatColorForChangePct(symbol.changePct),
                                          }}
                                          title={`${symbol.ticker} | ${fmtPrice(symbol.price)} | ${fmtPercentSigned(symbol.changePct)}`}
                                          onMouseEnter={(event) => setMapHoverFromMouse(tickerId, event)}
                                          onMouseMove={(event) => setMapHoverFromMouse(tickerId, event)}
                                          onDoubleClick={() => openAnalysisForTicker(symbol.ticker)}
                                          data-map-cell="true"
                                        >
                                          {showFull ? (
                                            <span className="tfe-map-ticker-label">
                                              <strong>{symbol.ticker}</strong>
                                              <span>{fmtPercentSigned(symbol.changePct)}</span>
                                            </span>
                                          ) : showTicker ? (
                                            <span className="tfe-map-ticker-mini">{symbol.ticker}</span>
                                          ) : null}
                                        </button>
                                      );
                                    })}
                                  </div>
                                </article>
                              );
                            })}
                          </div>
                        </section>
                      );
                    })}
                  </div>

                  {mapHoverDetail && mapHoverPanelStyle ? (
                    <div className="tfe-map-hover-panel" style={mapHoverPanelStyle}>
                      <header>
                        <span>{mapHoverDetail.kind.toUpperCase()}</span>
                        <strong>{mapHoverDetail.name}</strong>
                        <em>{fmtPercentSigned(mapHoverDetail.changePct)}</em>
                      </header>
                      <div className="tfe-map-hover-meta">
                        <span>{mapHoverDetail.sector || "Unclassified"}</span>
                        <span>{mapHoverDetail.industry || "Unclassified"}</span>
                        <span>{fmtCompactNumber(mapHoverDetail.marketCap)}</span>
                      </div>
                      <div className="tfe-map-hover-table-wrap">
                        <table className="tfe-map-hover-table">
                          <thead>
                            <tr>
                              <th>Ticker</th>
                              <th>Price</th>
                              <th>Change</th>
                            </tr>
                          </thead>
                          <tbody>
                            {mapHoverMembers.map((symbol) => (
                              <tr key={`hover-member-${mapHoverDetail.id}-${symbol.ticker}`}>
                                <td>{symbol.ticker}</td>
                                <td>{fmtPrice(symbol.price)}</td>
                                <td className={mapToneClass(symbol.changePct)}>{fmtPercentSigned(symbol.changePct)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : null}

                  <div className="tfe-map-scale-band tfe-map-scale-band--bottom" aria-hidden="true">
                    <span>-3%</span>
                    <span>-2%</span>
                    <span>-1%</span>
                    <span>0%</span>
                    <span>+1%</span>
                    <span>+2%</span>
                    <span>+3%</span>
                  </div>
                </div>

                <p className="tfe-map-canvas-footnote">
                  Double-click any ticker to open detailed analysis.
                </p>
              </div>
            </div>
          )}
        </section>
      ) : null}

      {dataTab === "ta" ? (
        <section className="tfe-panel tfe-ta-tab-surface" aria-label="TA screener workspace">
          {loading ? (
            <p className="tfe-muted" style={{ marginBottom: 0 }}>
              Loading TA rows...
            </p>
          ) : error ? (
            <p className="tfe-error" style={{ marginBottom: 0 }}>
              {error}
            </p>
          ) : filteredRows.length === 0 ? (
            <p className="tfe-muted" style={{ marginBottom: 0 }}>
              No symbols match current filters.
            </p>
          ) : (
            <div className="tfe-ta-card-list">
              {filteredRows.map((row, rowIndex) => {
                const quote = quoteOrDefault(quoteByTicker[row.ticker]);
                const taAttempts = quoteAttemptsByTicker[row.ticker] ?? 0;
                const miniChartLoading = Boolean(quoteLoadingByTicker[row.ticker]) || (!quote.miniChartFetched && taAttempts < TA_MINI_CHART_ATTEMPT_CAP);
                const miniChartNote = typeof quote.miniChartNote === "string" ? quote.miniChartNote.trim() : "";
                const rowNumber = (page - 1) * pageSize + rowIndex + 1;
                const chartModel = miniTaChartFromBars(Array.isArray(quote.miniBars) ? quote.miniBars : [], {
                  width: 760,
                  height: 182,
                  padX: 8,
                  padY: 8,
                  limit: 120,
                });
                const displayPrice = fmtPrice(row.price ?? quote.price ?? null);
                const displayChange = fmtPercentSigned(quote.changePct);
                const changeTone = inferTone(displayChange);
                const active = analysisOpen && selectedTicker === row.ticker;
                const changeFromOpen =
                  isFiniteValue(quote.price) && isFiniteValue(quote.open) && quote.open !== 0
                    ? fmtPercentSigned(((quote.price - quote.open) / quote.open) * 100)
                    : "n/a";
                const gap =
                  isFiniteValue(quote.open) && isFiniteValue(quote.prevClose) && quote.prevClose !== 0
                    ? fmtPercentSigned(((quote.open - quote.prevClose) / quote.prevClose) * 100)
                    : "n/a";

                const leftStats: Array<{ label: string; value: string }> = [
                  { label: "Company", value: fmtText(quote.companyName ?? row.ticker) },
                  { label: "Country", value: fmtText(quote.country) },
                  { label: "Industry", value: fmtText(quote.industry) },
                  { label: "Market Cap", value: fmtCompactNumber(quote.marketCap) },
                  { label: "Beta", value: fmtNum(quote.beta, 2) },
                  { label: "ATR (14)", value: fmtNum(quote.atr14, 2) },
                  { label: "Volatility W", value: fmtPercentSmart(firstFiniteMetric(quote, ["volatilityW"]), 2) },
                  { label: "Volatility M", value: fmtPercentSmart(firstFiniteMetric(quote, ["volatilityM"]), 2) },
                  { label: "SMA20", value: fmtPercentSmart(firstFiniteMetric(quote, ["sma20"]), 2) },
                  { label: "SMA50", value: fmtPercentSmart(firstFiniteMetric(quote, ["sma50"]), 2) },
                  { label: "SMA200", value: fmtPercentSmart(firstFiniteMetric(quote, ["sma200"]), 2) },
                  { label: "52W High", value: fmtPercentSmart(firstFiniteMetric(quote, ["high52"]), 2) },
                  { label: "52W Low", value: fmtPercentSmart(firstFiniteMetric(quote, ["low52"]), 2) },
                  { label: "RSI (14)", value: fmtNum(quote.rsi14, 2) },
                ];

                const rightStats: Array<{ label: string; value: string }> = [
                  { label: "Perf Week", value: fmtPercentSmart(firstFiniteMetric(quote, ["perfWeek"]), 2) },
                  { label: "Perf Month", value: fmtPercentSmart(firstFiniteMetric(quote, ["perfMonth"]), 2) },
                  { label: "Perf Quarter", value: fmtPercentSmart(firstFiniteMetric(quote, ["perfQuarter"]), 2) },
                  { label: "Perf Half Y", value: fmtPercentSmart(firstFiniteMetric(quote, ["perfHalf"]), 2) },
                  { label: "Perf YTD", value: fmtPercentSmart(firstFiniteMetric(quote, ["perfYtd"]), 2) },
                  { label: "Perf Year", value: fmtPercentSmart(firstFiniteMetric(quote, ["perfYear"]), 2) },
                  { label: "Change from Open", value: changeFromOpen },
                  { label: "Gap", value: gap },
                  { label: "Price", value: displayPrice },
                  { label: "Change", value: displayChange },
                  { label: "Rel Volume", value: fmtNum(quote.relVolume, 2) },
                  { label: "Avg Volume", value: fmtCompactNumber(quote.avgVolume) },
                  { label: "Volume", value: fmtCompactNumber(quote.volume) },
                  { label: "Signal", value: row.decision },
                ];

                return (
                  <article key={`ta-card-${row.ticker}-${row.assetType}`} className={`tfe-ta-card${active ? " is-active" : ""}`}>
                    <header className="tfe-ta-card-head">
                      <span className="tfe-ta-card-no">#{rowNumber}</span>
                      <button type="button" className="tfe-row-button tfe-ta-card-ticker" onClick={() => toggleRow(row)}>
                        {row.ticker}
                      </button>
                      <span className="tfe-ta-card-price">{displayPrice}</span>
                      <span className={changeTone ? `tfe-ta-card-change tone-${changeTone}` : "tfe-ta-card-change"}>{displayChange}</span>
                    </header>

                    <div className="tfe-ta-card-grid">
                      <section className="tfe-ta-chart-shell">
                        <div className="tfe-ta-chart-headline">
                          <span>{fmtText(quote.companyName ?? row.ticker)}</span>
                          <span>{fmtText(quote.industry)}</span>
                        </div>
                        {chartModel ? (
                          <svg
                            className={`tfe-ta-chart-svg tone-${chartModel.tone}`}
                            viewBox={`0 0 ${chartModel.width} ${chartModel.height}`}
                            role="img"
                            aria-label={`${row.ticker} trend`}
                            preserveAspectRatio="xMidYMid meet"
                          >
                            {chartModel.gridLines.map((y, index) => (
                              <line
                                key={`grid-${row.ticker}-${index}`}
                                className="tfe-ta-chart-grid"
                                x1={0}
                                y1={y}
                                x2={chartModel.width}
                                y2={y}
                              />
                            ))}

                            {chartModel.candles.map((candle, index) => (
                              <g key={`candle-${row.ticker}-${index}`}>
                                <line
                                  className={`tfe-ta-chart-wick ${candle.rising ? "up" : "down"}`}
                                  x1={candle.x}
                                  y1={candle.highY}
                                  x2={candle.x}
                                  y2={candle.lowY}
                                />
                                <rect
                                  className={`tfe-ta-chart-body ${candle.rising ? "up" : "down"}`}
                                  x={candle.x - chartModel.candleBodyWidth / 2}
                                  y={candle.bodyTop}
                                  width={chartModel.candleBodyWidth}
                                  height={candle.bodyHeight}
                                  rx={0.45}
                                  ry={0.45}
                                />
                              </g>
                            ))}

                            {chartModel.ma20Path ? <path className="tfe-ta-chart-ma20" d={chartModel.ma20Path} /> : null}
                            {chartModel.ma50Path ? <path className="tfe-ta-chart-ma50" d={chartModel.ma50Path} /> : null}
                            {chartModel.ma200Path ? <path className="tfe-ta-chart-ma200" d={chartModel.ma200Path} /> : null}
                          </svg>
                        ) : miniChartLoading ? (
                          <div className="tfe-ta-chart-empty">Loading mini chart...</div>
                        ) : (
                          <div className="tfe-ta-chart-empty">{miniChartNote || "Mini chart unavailable for this ticker."}</div>
                        )}
                        <div className="tfe-ta-chart-meta">
                          <span>O {fmtPrice(quote.open)}</span>
                          <span>H {fmtPrice(quote.dayHigh)}</span>
                          <span>L {fmtPrice(quote.dayLow)}</span>
                          <span>C {displayPrice}</span>
                        </div>
                      </section>

                      <aside className="tfe-ta-stats-shell">
                        <div className="tfe-ta-stat-columns">
                          <div className="tfe-ta-stat-col">
                            {leftStats.map((item) => {
                              const tone = inferTone(item.value);
                              return (
                                <div key={`ta-left-${row.ticker}-${item.label}`} className="tfe-ta-stat-row">
                                  <span className="k">{item.label}</span>
                                  <span className={tone ? `v tone-${tone}` : "v"}>{item.value}</span>
                                </div>
                              );
                            })}
                          </div>
                          <div className="tfe-ta-stat-col">
                            {rightStats.map((item) => {
                              const tone = inferTone(item.value);
                              return (
                                <div key={`ta-right-${row.ticker}-${item.label}`} className="tfe-ta-stat-row">
                                  <span className="k">{item.label}</span>
                                  <span className={tone ? `v tone-${tone}` : "v"}>{item.value}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </aside>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      ) : null}

      {dataTab === "ta" ? null : (
        <section className="tfe-table-wrap" style={{ maxHeight: 760 }}>
          <table className="tfe-table" style={{ minWidth: 1400 }}>
            <thead>
              <tr>
                <th>No.</th>
                {tableColumns.map((column) => {
                  const mappedSortKey = COLUMN_SORT_KEY_BY_ID[column.id] ?? null;
                  const sortActive = mappedSortKey !== null && sortKey === mappedSortKey;

                  return (
                    <th key={`screener-header-${column.id}`} style={column.align ? { textAlign: column.align } : undefined}>
                      {mappedSortKey ? (
                        <button type="button" className="tfe-sort-btn" onClick={() => applyColumnSort(column.id)}>
                          {column.label}
                          {sortActive ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                        </button>
                      ) : (
                        column.label
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={tableColumns.length + 1}>Loading screener rows...</td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={tableColumns.length + 1}>{error}</td>
                </tr>
              ) : filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={tableColumns.length + 1}>No symbols match current filters.</td>
                </tr>
              ) : (
                filteredRows.map((row, rowIndex) => {
                  const active = dataTab === "newsTab" ? newsFocusTicker === row.ticker : analysisOpen && selectedTicker === row.ticker;
                  const quote = quoteOrDefault(quoteByTicker[row.ticker]);
                  const rowNumber = (page - 1) * pageSize + rowIndex + 1;

                  return (
                    <tr key={`${row.ticker}-${row.assetType}`} className={active ? "active-row" : ""}>
                      <td>{rowNumber}</td>
                      {tableColumns.map((column) => (
                        <td key={`${row.ticker}-${column.id}`} style={column.align ? { textAlign: column.align } : undefined}>
                          {column.id === "ticker" ? (
                            <button
                              type="button"
                              className="tfe-row-button"
                              onClick={() => {
                                if (dataTab === "newsTab") {
                                  setNewsFocusTicker(row.ticker);
                                  return;
                                }
                                toggleRow(row);
                              }}
                            >
                              {column.render(row, quote)}
                            </button>
                          ) : column.id === "signal" ? (
                            <span className={`tfe-chip ${toDecisionClass(row.decision)}`}>{row.decision}</span>
                          ) : (
                            column.render(row, quote)
                          )}
                        </td>
                      ))}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </section>
      )}

      {analysisOpen && analysisTicker ? (
        <ClientPortal>
          <div
          className="tfe-flyout-backdrop"
          role="presentation"
          onClick={() => closeAnalysis()}
          >
            <section
            className="tfe-flyout-panel"
            role="dialog"
            aria-modal="true"
            aria-label={`${analysisTicker} analysis`}
            onClick={(event) => event.stopPropagation()}
            style={
              flyoutRect
                ? {
                    position: "fixed",
                    left: flyoutRect.left,
                    top: flyoutRect.top,
                    width: flyoutRect.width,
                    height: flyoutRect.height,
                  }
                : undefined
            }
          >
            <header
              className={`tfe-flyout-header tfe-flyout-drag-handle${flyoutMaximized ? " is-maximized" : ""}`}
              onPointerDown={handleFlyoutDragStart}
              onPointerMove={handleFlyoutDragMove}
              onPointerUp={handleFlyoutDragEnd}
              onPointerCancel={handleFlyoutDragEnd}
            >
              <h2 style={{ margin: 0, fontSize: "1rem" }}>{analysisTicker} Details</h2>
              <div className="tfe-flyout-actions">
                <button type="button" className="btn btn-ghost tfe-flyout-btn" data-flyout-control="true" onClick={() => toggleFlyoutMaximize()}>
                  {flyoutMaximized ? "Restore" : "Maximize"}
                </button>
                <button type="button" className="btn btn-ghost tfe-flyout-btn" data-flyout-control="true" onClick={() => closeAnalysis()}>
                  Close
                </button>
              </div>
            </header>

            <div className="tfe-flyout-body">
              <AnalysisPanel
                ticker={analysisTicker}
                row={selectedRow}
                chartLoading={chartLoading}
                chartError={chartError}
                chartSummary={chartSummary}
                chartNote={chartNote}
                quoteSummary={quoteSummary}
                chartBars={chartBars}
                chartControls={chartControls}
                onChartControlsChange={(next) => {
                  if (!analysisTicker) return;
                  void loadChart(analysisTicker, next);
                }}
              />
            </div>
            <div
              className={`tfe-flyout-resize-handle${flyoutMaximized ? " is-disabled" : ""}`}
              data-flyout-control="true"
              role="presentation"
              onPointerDown={handleFlyoutResizeStart}
              onPointerMove={handleFlyoutResizeMove}
              onPointerUp={handleFlyoutResizeEnd}
              onPointerCancel={handleFlyoutResizeEnd}
            />
            </section>
          </div>
        </ClientPortal>
      ) : null}

      <section className="tfe-toolbar-actions" style={{ justifyContent: "space-between" }}>
        <div className="tfe-muted">
          {filteredRows.length > 0 ? `${filteredRows.length} shown / ${rows.length} page rows / ${total} total` : `${total} total`}
        </div>

        <div className="tfe-toolbar-actions">
          <label className="tfe-muted" htmlFor="screenerPageSize">
            Rows
          </label>
          <select
            id="screenerPageSize"
            className="tfe-select"
            style={{ minWidth: 90 }}
            value={pageSize}
            onChange={(event) => setPageSize(Number(event.target.value))}
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>

          <button type="button" className="btn btn-ghost" onClick={() => goToPage(page - 1)} disabled={page <= 1}>
            Prev
          </button>
          <div className="tfe-toolbar-actions" aria-label="Pagination">
            {paginationTokens.map((token) =>
              token.kind === "ellipsis" ? (
                <span key={token.key} className="tfe-muted" aria-hidden="true">
                  ...
                </span>
              ) : (
                <button
                  key={`pagination-page-${token.value}`}
                  type="button"
                  className="btn btn-ghost"
                  aria-label={`Go to page ${token.value}`}
                  aria-current={token.value === page ? "page" : undefined}
                  disabled={token.value === page}
                  onClick={() => goToPage(token.value)}
                >
                  {token.value}
                </button>
              ),
            )}
          </div>
          <label className="tfe-muted" htmlFor="screenerJumpPage">
            Jump
          </label>
          <select
            id="screenerJumpPage"
            className="tfe-select"
            aria-label="Jump to page"
            style={{ minWidth: 90 }}
            value={pageJumpValue}
            onChange={(event) => setPageJumpValue(event.target.value)}
          >
            {paginationNumberPages.map((optionPage) => (
              <option key={`jump-page-${optionPage}`} value={optionPage}>
                {optionPage}
              </option>
            ))}
          </select>
          <button type="button" className="btn btn-ghost" onClick={applyJumpPageValue}>
            Go
          </button>
          <span className="tfe-muted">
            Page {page} / {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages}
          >
            Next
          </button>
        </div>
      </section>
    </div>
  );
}
