export type ScreenerSortDirection = "asc" | "desc";

export type ScreenerSortableRow = {
  ticker: string;
  assetType: string;
  decision: string;
  regime: string;
  price: number | null;
  barCount: number;
  stabilityScore: number | null;
  maxDrawdown: number | null;
};

export type ScreenerSortableQuote = {
  companyName?: string | null;
  sector?: string | null;
  industry?: string | null;
  country?: string | null;
  marketCap?: number | null;
  changePct?: number | null;
  volume?: number | null;
};

function compareNullableNumber(a: number | null, b: number | null, direction: ScreenerSortDirection): number {
  const av = a ?? Number.NEGATIVE_INFINITY;
  const bv = b ?? Number.NEGATIVE_INFINITY;
  const base = av - bv;
  return direction === "asc" ? base : -base;
}

function compareNumber(a: number, b: number, direction: ScreenerSortDirection): number {
  const base = a - b;
  return direction === "asc" ? base : -base;
}

function compareString(a: string, b: string, direction: ScreenerSortDirection): number {
  const base = a.localeCompare(b);
  return direction === "asc" ? base : -base;
}

function quoteSortString(quote: ScreenerSortableQuote | undefined, key: keyof ScreenerSortableQuote): string {
  const value = quote?.[key];
  return typeof value === "string" && value.trim() ? value.trim().toUpperCase() : "";
}

function quoteSortNumber(quote: ScreenerSortableQuote | undefined, key: keyof ScreenerSortableQuote): number | null {
  const value = quote?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function sortScreenerRows<Row extends ScreenerSortableRow, Quote extends ScreenerSortableQuote>(
  rows: Row[],
  quoteByTicker: Record<string, Quote | undefined>,
  sortKey: string,
  direction: ScreenerSortDirection,
): Row[] {
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
    if (sortKey === "company") return compareString(quoteSortString(quoteByTicker[a.ticker], "companyName"), quoteSortString(quoteByTicker[b.ticker], "companyName"), direction);
    if (sortKey === "sector") return compareString(quoteSortString(quoteByTicker[a.ticker], "sector"), quoteSortString(quoteByTicker[b.ticker], "sector"), direction);
    if (sortKey === "industry") return compareString(quoteSortString(quoteByTicker[a.ticker], "industry"), quoteSortString(quoteByTicker[b.ticker], "industry"), direction);
    if (sortKey === "country") return compareString(quoteSortString(quoteByTicker[a.ticker], "country"), quoteSortString(quoteByTicker[b.ticker], "country"), direction);
    if (sortKey === "marketcap") return compareNullableNumber(quoteSortNumber(quoteByTicker[a.ticker], "marketCap"), quoteSortNumber(quoteByTicker[b.ticker], "marketCap"), direction);
    if (sortKey === "change") return compareNullableNumber(quoteSortNumber(quoteByTicker[a.ticker], "changePct"), quoteSortNumber(quoteByTicker[b.ticker], "changePct"), direction);
    if (sortKey === "volume") return compareNullableNumber(quoteSortNumber(quoteByTicker[a.ticker], "volume"), quoteSortNumber(quoteByTicker[b.ticker], "volume"), direction);
    return compareString(a.ticker, b.ticker, "asc");
  });

  return next;
}
