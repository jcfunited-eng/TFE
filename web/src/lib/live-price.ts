import { setTimeout as delay } from "node:timers/promises";

export type LivePriceRequest = {
  ticker: string;
  assetType?: unknown;
};

export type LivePriceSource =
  | "polygon_stocks_last_trade"
  | "polygon_stocks_minute"
  | "polygon_stocks_day"
  | "polygon_stocks_prev_day"
  | "polygon_crypto_last_trade"
  | "polygon_crypto_minute"
  | "polygon_crypto_day"
  | "polygon_crypto_prev_day"
  | "polygon_minute_agg"
  | "polygon_prev_close"
  | "coinbase_spot"
  | "unavailable";

export type LivePriceQuote = {
  ticker: string;
  price: number | null;
  asOfIsoUtc: string | null;
  source: LivePriceSource;
  error: string | null;
};

const DEFAULT_BASE_URL = "https://api.polygon.io";
const API_KEY = String(process.env.MASSIVE_API_KEY ?? process.env.POLYGON_API_KEY ?? "").trim();
const BASE_URL = String(process.env.MASSIVE_API_BASE ?? DEFAULT_BASE_URL).trim() || DEFAULT_BASE_URL;
const REQUEST_TIMEOUT_MS = normalizeInt(process.env.TFE_LIVE_PRICE_TIMEOUT_MS, 2500, 1000, 20000);
const MAX_RETRIES = normalizeInt(process.env.TFE_LIVE_PRICE_MAX_RETRIES, 0, 0, 6);
const CONCURRENCY = normalizeInt(process.env.TFE_LIVE_PRICE_CONCURRENCY, 4, 1, 10);
const MINUTE_LOOKBACK_DAYS = normalizeInt(process.env.TFE_LIVE_PRICE_MINUTE_LOOKBACK_DAYS, 7, 1, 30);
const RETRY_BASE_DELAY_MS = normalizeInt(process.env.TFE_LIVE_PRICE_RETRY_BASE_DELAY_MS, 600, 100, 10000);
const TOTAL_TIMEOUT_MS = normalizeInt(process.env.TFE_LIVE_PRICE_TOTAL_TIMEOUT_MS, 12000, 1000, 120000);
const PER_TICKER_TIMEOUT_MS = normalizeInt(process.env.TFE_LIVE_PRICE_PER_TICKER_TIMEOUT_MS, 4500, 500, 30000);
const MINUTE_AGG_FALLBACK_ENABLED =
  String(process.env.TFE_LIVE_PRICE_MINUTE_AGG_FALLBACK_ENABLED ?? "false").trim().toLowerCase() === "true";
const COINBASE_CRYPTO_FALLBACK_ENABLED = String(process.env.TFE_LIVE_PRICE_COINBASE_ENABLED ?? "true").trim().toLowerCase() !== "false";

function normalizeInt(value: unknown, fallback: number, min: number, max: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;

  const whole = Math.floor(n);
  if (whole < min) return min;
  if (whole > max) return max;
  return whole;
}

function normalizeTicker(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function toPositiveNumber(value: unknown): number | null {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  if (!(n > 0)) return null;
  return n;
}

function toIsoUtc(value: unknown): string | null {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;

  let epochMs: number;

  if (n > 1e17) {
    epochMs = n / 1_000_000;
  } else if (n > 1e14) {
    epochMs = n / 1_000;
  } else if (n > 1e12) {
    epochMs = n;
  } else if (n > 1e9) {
    epochMs = n * 1_000;
  } else {
    return null;
  }

  if (!Number.isFinite(epochMs)) return null;

  const date = new Date(epochMs);
  if (Number.isNaN(date.getTime())) return null;

  return date.toISOString();
}

function utcDateString(offsetDays: number): string {
  const now = new Date();
  const shifted = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + offsetDays));
  return shifted.toISOString().slice(0, 10);
}

function buildApiUrl(pathname: string, query: Record<string, string>): string {
  const base = BASE_URL.endsWith("/") ? BASE_URL.slice(0, -1) : BASE_URL;
  const url = new URL(`${base}${pathname}`);

  for (const [key, value] of Object.entries(query)) {
    url.searchParams.set(key, value);
  }

  url.searchParams.set("apiKey", API_KEY);
  return url.toString();
}

function isRetriableStatus(status: number): boolean {
  return status === 429 || status === 500 || status === 502 || status === 503 || status === 504;
}

function computeBackoffMs(attempt: number, status?: number): number {
  const base = RETRY_BASE_DELAY_MS * (2 ** Math.max(0, attempt));
  if (status === 429) {
    return Math.max(1000, base);
  }
  return base;
}

function unavailableQuote(ticker: string, error: string): LivePriceQuote {
  return {
    ticker,
    price: null,
    asOfIsoUtc: null,
    source: "unavailable",
    error,
  };
}

async function fetchUrlJsonWithRetry(url: string): Promise<{ payload: unknown | null; error: string | null }> {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
        cache: "no-store",
        signal: controller.signal,
      });

      if (response.ok) {
        const payload = (await response.json()) as unknown;
        return { payload, error: null };
      }

      const text = await response.text();
      const bodyPreview = text.slice(0, 240);

      if (attempt < MAX_RETRIES && isRetriableStatus(response.status)) {
        await delay(computeBackoffMs(attempt, response.status));
        continue;
      }

      return {
        payload: null,
        error: `HTTP ${response.status}: ${bodyPreview || "No response body"}`,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown request failure.";

      if (attempt < MAX_RETRIES) {
        await delay(computeBackoffMs(attempt));
        continue;
      }

      return {
        payload: null,
        error: message,
      };
    } finally {
      clearTimeout(timer);
    }
  }

  return {
    payload: null,
    error: "Exhausted retries.",
  };
}

async function fetchJsonWithRetry(pathname: string, query: Record<string, string>): Promise<{ payload: unknown | null; error: string | null }> {
  if (!API_KEY) {
    return {
      payload: null,
      error: "MASSIVE_API_KEY/POLYGON_API_KEY is not configured.",
    };
  }

  const url = buildApiUrl(pathname, query);
  const result = await fetchUrlJsonWithRetry(url);

  if (result.error) {
    return {
      payload: null,
      error: `${pathname} request failed: ${result.error}`,
    };
  }

  return result;
}

function isCryptoRequest(ticker: string, assetType: unknown): boolean {
  const normalizedAssetType = String(assetType ?? "")
    .trim()
    .toLowerCase();

  if (["crypto", "cryptocurrency", "coin", "token"].includes(normalizedAssetType)) {
    return true;
  }

  return ticker.startsWith("X:");
}

function parseStockSnapshot(payload: unknown, ticker: string): LivePriceQuote {
  const root = asRecord(payload);
  const tickerNode = asRecord(root?.ticker);

  if (!tickerNode) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error: "Stocks snapshot response did not include ticker payload.",
    };
  }

  const candidates: Array<{
    price: number | null;
    asOfIsoUtc: string | null;
    source: LivePriceSource;
  }> = [
    {
      price: toPositiveNumber(asRecord(tickerNode.lastTrade)?.p),
      asOfIsoUtc: toIsoUtc(asRecord(tickerNode.lastTrade)?.t),
      source: "polygon_stocks_last_trade",
    },
    {
      price: toPositiveNumber(asRecord(tickerNode.min)?.c),
      asOfIsoUtc: toIsoUtc(asRecord(tickerNode.min)?.t),
      source: "polygon_stocks_minute",
    },
    {
      price: toPositiveNumber(asRecord(tickerNode.day)?.c),
      asOfIsoUtc: toIsoUtc(asRecord(tickerNode.day)?.t),
      source: "polygon_stocks_day",
    },
    {
      price: toPositiveNumber(asRecord(tickerNode.prevDay)?.c),
      asOfIsoUtc: toIsoUtc(asRecord(tickerNode.prevDay)?.t),
      source: "polygon_stocks_prev_day",
    },
  ];

  for (const candidate of candidates) {
    if (candidate.price !== null) {
      return {
        ticker,
        price: candidate.price,
        asOfIsoUtc: candidate.asOfIsoUtc,
        source: candidate.source,
        error: null,
      };
    }
  }

  return {
    ticker,
    price: null,
    asOfIsoUtc: null,
    source: "unavailable",
    error: "Stocks snapshot payload had no usable price fields.",
  };
}

function parseCryptoSnapshot(payload: unknown, ticker: string): LivePriceQuote {
  const root = asRecord(payload);
  const tickerNode = asRecord(root?.ticker);

  if (!tickerNode) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error: "Crypto snapshot response did not include ticker payload.",
    };
  }

  const candidates: Array<{
    price: number | null;
    asOfIsoUtc: string | null;
    source: LivePriceSource;
  }> = [
    {
      price: toPositiveNumber(asRecord(tickerNode.lastTrade)?.p),
      asOfIsoUtc: toIsoUtc(asRecord(tickerNode.lastTrade)?.t),
      source: "polygon_crypto_last_trade",
    },
    {
      price: toPositiveNumber(asRecord(tickerNode.min)?.c),
      asOfIsoUtc: toIsoUtc(asRecord(tickerNode.min)?.t),
      source: "polygon_crypto_minute",
    },
    {
      price: toPositiveNumber(asRecord(tickerNode.day)?.c),
      asOfIsoUtc: toIsoUtc(asRecord(tickerNode.day)?.t),
      source: "polygon_crypto_day",
    },
    {
      price: toPositiveNumber(asRecord(tickerNode.prevDay)?.c),
      asOfIsoUtc: toIsoUtc(asRecord(tickerNode.prevDay)?.t),
      source: "polygon_crypto_prev_day",
    },
  ];

  for (const candidate of candidates) {
    if (candidate.price !== null) {
      return {
        ticker,
        price: candidate.price,
        asOfIsoUtc: candidate.asOfIsoUtc,
        source: candidate.source,
        error: null,
      };
    }
  }

  return {
    ticker,
    price: null,
    asOfIsoUtc: null,
    source: "unavailable",
    error: "Crypto snapshot payload had no usable price fields.",
  };
}

function parseAggregatePayload(payload: unknown, ticker: string, source: LivePriceSource): LivePriceQuote {
  const root = asRecord(payload);
  const results = Array.isArray(root?.results) ? root.results : [];

  if (results.length === 0) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error: "Aggregate payload returned no results.",
    };
  }

  const latest = asRecord(results[0]);
  const price = toPositiveNumber(latest?.c);

  if (price === null) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error: "Aggregate payload had no usable close price.",
    };
  }

  return {
    ticker,
    price,
    asOfIsoUtc: toIsoUtc(latest?.t),
    source,
    error: null,
  };
}

function parseCoinbasePairFromTicker(ticker: string): { base: string; quote: string } | null {
  const normalized = normalizeTicker(ticker);
  const match = normalized.match(/^X:([A-Z0-9]{2,12})(USD|USDC|USDT|EUR|GBP)$/);
  if (!match) return null;
  return { base: match[1], quote: match[2] };
}

async function loadCoinbaseSpotQuote(ticker: string): Promise<LivePriceQuote> {
  if (!COINBASE_CRYPTO_FALLBACK_ENABLED) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error: "Coinbase crypto fallback is disabled.",
    };
  }

  const pair = parseCoinbasePairFromTicker(ticker);
  if (!pair) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error: "Ticker format is not supported for Coinbase fallback.",
    };
  }

  const url = `https://api.coinbase.com/v2/prices/${encodeURIComponent(pair.base)}-${encodeURIComponent(pair.quote)}/spot`;
  const { payload, error } = await fetchUrlJsonWithRetry(url);

  if (error) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error: `Coinbase spot request failed: ${error}`,
    };
  }

  const root = asRecord(payload);
  const data = asRecord(root?.data);
  const amount = toPositiveNumber(data?.amount);
  if (amount === null) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error: "Coinbase spot payload had no usable amount.",
    };
  }

  return {
    ticker,
    price: amount,
    asOfIsoUtc: new Date().toISOString(),
    source: "coinbase_spot",
    error: null,
  };
}

async function loadMinuteAggregateQuote(ticker: string): Promise<LivePriceQuote> {
  const start = utcDateString(-MINUTE_LOOKBACK_DAYS);
  const end = utcDateString(0);

  const { payload, error } = await fetchJsonWithRetry(
    `/v2/aggs/ticker/${encodeURIComponent(ticker)}/range/1/minute/${start}/${end}`,
    {
      adjusted: "true",
      sort: "desc",
      limit: "1",
    },
  );

  if (error) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error,
    };
  }

  return parseAggregatePayload(payload, ticker, "polygon_minute_agg");
}

async function loadPrevCloseQuote(ticker: string): Promise<LivePriceQuote> {
  const { payload, error } = await fetchJsonWithRetry(`/v2/aggs/ticker/${encodeURIComponent(ticker)}/prev`, {
    adjusted: "true",
  });

  if (error) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error,
    };
  }

  return parseAggregatePayload(payload, ticker, "polygon_prev_close");
}

async function loadStockSnapshotQuote(ticker: string): Promise<LivePriceQuote> {
  const { payload, error } = await fetchJsonWithRetry(`/v2/snapshot/locale/us/markets/stocks/tickers/${encodeURIComponent(ticker)}`, {});

  if (error) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error,
    };
  }

  return parseStockSnapshot(payload, ticker);
}

async function loadCryptoSnapshotQuote(ticker: string): Promise<LivePriceQuote> {
  const { payload, error } = await fetchJsonWithRetry(`/v2/snapshot/locale/global/markets/crypto/tickers/${encodeURIComponent(ticker)}`, {});

  if (error) {
    return {
      ticker,
      price: null,
      asOfIsoUtc: null,
      source: "unavailable",
      error,
    };
  }

  return parseCryptoSnapshot(payload, ticker);
}

async function loadLiveQuote(request: LivePriceRequest): Promise<LivePriceQuote> {
  const ticker = normalizeTicker(request.ticker);
  if (!ticker) {
    return unavailableQuote(ticker, "Ticker is empty.");
  }

  const crypto = isCryptoRequest(ticker, request.assetType);

  if (!crypto) {
    if (!API_KEY) {
      return unavailableQuote(ticker, "MASSIVE_API_KEY/POLYGON_API_KEY is not configured.");
    }

    const stockSnapshot = await loadStockSnapshotQuote(ticker);
    if (stockSnapshot.price !== null) {
      return stockSnapshot;
    }

    const prev = await loadPrevCloseQuote(ticker);
    if (prev.price !== null) {
      return prev;
    }

    if (!MINUTE_AGG_FALLBACK_ENABLED) {
      return unavailableQuote(
        ticker,
        [stockSnapshot.error, prev.error].filter(Boolean).join(" | ") || "No live stock price available.",
      );
    }

    const minute = await loadMinuteAggregateQuote(ticker);
    if (minute.price !== null) {
      return minute;
    }

    return unavailableQuote(
      ticker,
      [stockSnapshot.error, prev.error, minute.error].filter(Boolean).join(" | ") || "No live stock price available.",
    );
  }

  const coinbase = await loadCoinbaseSpotQuote(ticker);
  if (coinbase.price !== null) {
    return coinbase;
  }

  if (!API_KEY) {
    return unavailableQuote(ticker, [coinbase.error, "MASSIVE_API_KEY/POLYGON_API_KEY is not configured."].filter(Boolean).join(" | "));
  }

  const cryptoSnapshot = await loadCryptoSnapshotQuote(ticker);
  if (cryptoSnapshot.price !== null) {
    return cryptoSnapshot;
  }

  const prev = await loadPrevCloseQuote(ticker);
  if (prev.price !== null) {
    return prev;
  }

  if (!MINUTE_AGG_FALLBACK_ENABLED) {
    return unavailableQuote(
      ticker,
      [coinbase.error, cryptoSnapshot.error, prev.error].filter(Boolean).join(" | ") || "No live crypto price available.",
    );
  }

  const minute = await loadMinuteAggregateQuote(ticker);
  if (minute.price !== null) {
    return minute;
  }

  return unavailableQuote(
    ticker,
    [coinbase.error, cryptoSnapshot.error, prev.error, minute.error].filter(Boolean).join(" | ") || "No live crypto price available.",
  );
}

async function loadLiveQuoteWithTimeout(request: LivePriceRequest): Promise<LivePriceQuote> {
  const ticker = normalizeTicker(request.ticker);

  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  const timeoutPromise = new Promise<LivePriceQuote>((resolve) => {
    timeoutHandle = setTimeout(() => {
      resolve(unavailableQuote(ticker, `Live quote timed out after ${PER_TICKER_TIMEOUT_MS}ms.`));
    }, PER_TICKER_TIMEOUT_MS);
  });

  const quotePromise = loadLiveQuote(request).catch((error) => {
    const reason = error instanceof Error ? error.message : "Unknown live quote failure.";
    return unavailableQuote(ticker, reason);
  });

  try {
    return await Promise.race([quotePromise, timeoutPromise]);
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle);
  }
}

export async function loadLivePriceMap(requests: LivePriceRequest[]): Promise<Map<string, LivePriceQuote>> {
  const deduped = new Map<string, LivePriceRequest>();

  for (const request of requests) {
    const ticker = normalizeTicker(request.ticker);
    if (!ticker) continue;

    const existing = deduped.get(ticker);
    if (existing) {
      if ((existing.assetType === undefined || existing.assetType === null) && request.assetType !== undefined && request.assetType !== null) {
        deduped.set(ticker, { ticker, assetType: request.assetType });
      }
      continue;
    }

    deduped.set(ticker, { ticker, assetType: request.assetType });
  }

  const entries = Array.from(deduped.values());
  const out = new Map<string, LivePriceQuote>();
  const deadlineEpoch = Date.now() + TOTAL_TIMEOUT_MS;

  if (entries.length === 0) {
    return out;
  }

  const workerCount = Math.min(CONCURRENCY, entries.length);
  let cursor = 0;

  async function worker(): Promise<void> {
    while (cursor < entries.length) {
      if (Date.now() >= deadlineEpoch) {
        return;
      }

      const current = cursor;
      cursor += 1;

      const request = entries[current];
      const quote = await loadLiveQuoteWithTimeout(request);
      out.set(request.ticker, quote);
    }
  }

  await Promise.all(Array.from({ length: workerCount }, () => worker()));

  if (Date.now() >= deadlineEpoch) {
    for (const request of entries) {
      if (!out.has(request.ticker)) {
        out.set(request.ticker, unavailableQuote(request.ticker, `Live quote batch exceeded ${TOTAL_TIMEOUT_MS}ms.`));
      }
    }
  }

  return out;
}
