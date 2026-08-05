import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

export type ScreenerQuoteCacheRow = Record<string, unknown>;

type AttemptFailure = {
  path: string;
  reason: string;
};

type QuoteCacheLoadResult = {
  quotes: Record<string, ScreenerQuoteCacheRow>;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

type QuoteCacheRuntime = {
  cacheKey: string;
  sourcePath: string;
  quotes: Record<string, ScreenerQuoteCacheRow>;
};

const CACHE_FILENAME = "screener-quote-cache.json";
const PRICE_CANDIDATE_FIELDS = [
  "regularMarketPrice",
  "currentPrice",
  "price",
  "close",
  "previousClose",
  "lastPrice",
  "navPrice",
] as const;

let QUOTE_CACHE: QuoteCacheRuntime | null = null;

function uniquePaths(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const value of values) {
    const normalized = path.normalize(value);
    if (seen.has(normalized)) continue;
    seen.add(normalized);
    out.push(normalized);
  }
  return out;
}

function quoteCacheCandidates(): string[] {
  const cwd = process.cwd();
  return uniquePaths([
    path.resolve(cwd, "data", CACHE_FILENAME),
    path.resolve(cwd, "web", "data", CACHE_FILENAME),
    path.resolve(cwd, "..", "web", "data", CACHE_FILENAME),
    path.resolve(cwd, "..", "..", "web", "data", CACHE_FILENAME),
    path.resolve("/workspaces/Tao_Financial_Engine/web/data", CACHE_FILENAME),
  ]);
}

function cacheKeyFor(filePath: string): string {
  const stats = statSync(filePath);
  return `${path.normalize(filePath)}|${Math.floor(stats.mtimeMs)}|${stats.size}`;
}

function normalizeQuoteMap(raw: unknown): Record<string, ScreenerQuoteCacheRow> {
  const out: Record<string, ScreenerQuoteCacheRow> = {};

  if (!raw || typeof raw !== "object") {
    return out;
  }

  if (Array.isArray(raw)) {
    for (const row of raw) {
      if (!row || typeof row !== "object") continue;
      const bag = row as Record<string, unknown>;
      const ticker = String(bag.ticker ?? "").trim().toUpperCase();
      const quote = bag.quote;
      if (!ticker || !quote || typeof quote !== "object" || Array.isArray(quote)) continue;
      out[ticker] = quote as ScreenerQuoteCacheRow;
    }
    return out;
  }

  const bag = raw as Record<string, unknown>;

  if (bag.rows && typeof bag.rows === "object") {
    return normalizeQuoteMap(bag.rows);
  }

  for (const [key, value] of Object.entries(bag)) {
    const ticker = String(key).trim().toUpperCase();
    if (!ticker) continue;
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    out[ticker] = value as ScreenerQuoteCacheRow;
  }

  return out;
}

function toPositiveNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

export function quoteCachePriceFromRow(row: ScreenerQuoteCacheRow | null | undefined): number | null {
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;

  for (const field of PRICE_CANDIDATE_FIELDS) {
    const value = toPositiveNumberOrNull(row[field]);
    if (value !== null) return value;
  }

  return null;
}

export function loadScreenerQuoteCache(): QuoteCacheLoadResult {
  const candidates = quoteCacheCandidates();
  const failures: AttemptFailure[] = [];

  for (const candidate of candidates) {
    if (!existsSync(candidate)) {
      failures.push({ path: candidate, reason: "Cache file not found." });
      continue;
    }

    try {
      const key = cacheKeyFor(candidate);
      if (QUOTE_CACHE && QUOTE_CACHE.cacheKey === key) {
        return {
          quotes: QUOTE_CACHE.quotes,
          sourcePath: QUOTE_CACHE.sourcePath,
          failures,
        };
      }

      const text = readFileSync(candidate, "utf-8");
      const parsed = JSON.parse(text) as unknown;
      const quotes = normalizeQuoteMap(parsed);
      if (Object.keys(quotes).length === 0) {
        failures.push({ path: candidate, reason: "Parsed cache file but no quote rows were found." });
        continue;
      }

      QUOTE_CACHE = {
        cacheKey: key,
        sourcePath: candidate,
        quotes,
      };

      return {
        quotes,
        sourcePath: candidate,
        failures,
      };
    } catch (error) {
      const reason = error instanceof Error ? error.message : "Unknown read/parse failure.";
      failures.push({ path: candidate, reason });
    }
  }

  return {
    quotes: {},
    sourcePath: null,
    failures,
  };
}
