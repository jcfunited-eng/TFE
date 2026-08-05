export type MarketQuoteSummary = {
  companyName?: string | null;
  category?: string | null;
  assetType?: string | null;
  quoteType?: string | null;
  exchange?: string | null;
  country?: string | null;
  sector?: string | null;
  industry?: string | null;
  fundFamily?: string | null;
  employees?: number | null;
  ipoDate?: number | null;
  earningsDate?: number | null;
  indexName?: string | null;
  marketCap?: number | null;
  enterpriseValue?: number | null;
  income?: number | null;
  sales?: number | null;
  bookValue?: number | null;
  cashPerShare?: number | null;
  freeCashflow?: number | null;
  ebitda?: number | null;
  dividendRate?: number | null;
  dividendYield?: number | null;
  trailingDividendRate?: number | null;
  trailingDividendYield?: number | null;
  exDividendDate?: number | null;
  payoutRatio?: number | null;
  peRatio?: number | null;
  forwardPE?: number | null;
  pegRatio?: number | null;
  priceToSales?: number | null;
  priceToBook?: number | null;
  priceToCash?: number | null;
  priceToFreeCashFlow?: number | null;
  evToEbitda?: number | null;
  evToSales?: number | null;
  quickRatio?: number | null;
  currentRatio?: number | null;
  debtToEquity?: number | null;
  longTermDebtToEquity?: number | null;
  eps?: number | null;
  forwardEps?: number | null;
  epsNextQ?: number | null;
  earningsGrowth?: number | null;
  earningsQuarterlyGrowth?: number | null;
  revenueGrowth?: number | null;
  revenueQuarterlyGrowth?: number | null;
  grossMargin?: number | null;
  operatingMargin?: number | null;
  profitMargin?: number | null;
  roa?: number | null;
  roe?: number | null;
  roic?: number | null;
  insiderOwn?: number | null;
  insiderTrans?: number | null;
  instOwn?: number | null;
  instTrans?: number | null;
  sharesOutstanding?: number | null;
  sharesFloat?: number | null;
  shortFloat?: number | null;
  shortInterest?: number | null;
  shortRatio?: number | null;
  beta?: number | null;
  target1Y?: number | null;
  targetLow?: number | null;
  targetHigh?: number | null;
  recommendationMean?: number | null;
  avgVolume?: number | null;
  volume?: number | null;
  relVolume?: number | null;
  prevClose?: number | null;
  price?: number | null;
  open?: number | null;
  dayHigh?: number | null;
  dayLow?: number | null;
  change?: number | null;
  changePct?: number | null;
  high52?: number | null;
  low52?: number | null;
  sma20?: number | null;
  sma50?: number | null;
  sma200?: number | null;
  atr14?: number | null;
  rsi14?: number | null;
  bid?: number | null;
  ask?: number | null;
  optionable?: boolean | null;
  shortable?: boolean | null;
};

export type MarketBar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type MarketSummary = {
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

export type MarketStatCell = {
  label: string;
  value: string;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function fmtNum(value: number | null | undefined, decimals = 2): string {
  if (!isFiniteNumber(value)) return "n/a";
  return value.toFixed(decimals);
}

function fmtSigned(value: number | null | undefined, decimals = 2): string {
  if (!isFiniteNumber(value)) return "n/a";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(decimals)}`;
}

function fmtCompactNumber(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return "n/a";
  const n = value;
  const abs = Math.abs(n);
  if (abs >= 1_000_000_000_000) return `${(n / 1_000_000_000_000).toFixed(2)}T`;
  if (abs >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(2);
}

function fmtWholeNumber(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return "n/a";
  return Math.round(value).toLocaleString();
}

function fmtDate(epochSec: number | null | undefined): string {
  if (!isFiniteNumber(epochSec) || epochSec <= 0) return "n/a";
  const d = new Date(epochSec * 1000);
  if (Number.isNaN(d.getTime())) return "n/a";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(d);
}

function fmtPercentFromRatio(
  value: number | null | undefined,
  options?: { decimals?: number; signed?: boolean; allowPlus?: boolean },
): string {
  if (!isFiniteNumber(value)) return "n/a";
  const decimals = options?.decimals ?? 2;
  const pct = value * 100;
  if (options?.signed) {
    const prefix = pct > 0 && options.allowPlus !== false ? "+" : "";
    return `${prefix}${pct.toFixed(decimals)}%`;
  }
  return `${pct.toFixed(decimals)}%`;
}

function fmtPercentFromPercentValue(
  value: number | null | undefined,
  options?: { decimals?: number; signed?: boolean; allowPlus?: boolean },
): string {
  if (!isFiniteNumber(value)) return "n/a";
  const decimals = options?.decimals ?? 2;
  if (options?.signed) {
    const prefix = value > 0 && options.allowPlus !== false ? "+" : "";
    return `${prefix}${value.toFixed(decimals)}%`;
  }
  return `${value.toFixed(decimals)}%`;
}

function fmtDividend(rate: number | null | undefined, yieldRatio: number | null | undefined): string {
  const rateText = fmtNum(rate, 2);
  const yieldText = fmtPercentFromRatio(yieldRatio, { decimals: 2 });

  if (rateText === "n/a" && yieldText === "n/a") return "n/a";
  if (rateText === "n/a") return yieldText;
  if (yieldText === "n/a") return rateText;
  return `${rateText} (${yieldText})`;
}

function parseBarTime(input: string): number | null {
  const ts = Date.parse(input);
  if (!Number.isFinite(ts)) return null;
  return ts;
}

function sortedBars(bars: MarketBar[]): MarketBar[] {
  const next = [...bars];
  next.sort((a, b) => {
    const ta = parseBarTime(a.time) ?? 0;
    const tb = parseBarTime(b.time) ?? 0;
    return ta - tb;
  });
  return next;
}

function closesFromBars(bars: MarketBar[]): number[] {
  return bars.map((bar) => bar.close).filter((value) => isFiniteNumber(value));
}

function calcLookbackPerf(bars: MarketBar[], lookback: number): number | null {
  if (bars.length <= lookback) return null;
  const latest = bars[bars.length - 1]?.close;
  const ref = bars[bars.length - 1 - lookback]?.close;
  if (!isFiniteNumber(latest) || !isFiniteNumber(ref) || ref === 0) return null;
  return ((latest - ref) / ref) * 100;
}

function calcYtdPerf(bars: MarketBar[]): number | null {
  if (bars.length < 2) return null;

  const latestBar = bars[bars.length - 1];
  const latestTs = parseBarTime(latestBar.time);
  if (latestTs == null) return null;

  const year = new Date(latestTs).getUTCFullYear();
  let firstOfYear: MarketBar | null = null;

  for (const bar of bars) {
    const ts = parseBarTime(bar.time);
    if (ts == null) continue;
    if (new Date(ts).getUTCFullYear() === year) {
      firstOfYear = bar;
      break;
    }
  }

  if (!firstOfYear) return null;
  const latest = latestBar.close;
  const ref = firstOfYear.close;
  if (!isFiniteNumber(latest) || !isFiniteNumber(ref) || ref === 0) return null;
  return ((latest - ref) / ref) * 100;
}

function calcStd(values: number[]): number | null {
  if (values.length < 2) return null;
  const mean = values.reduce((acc, v) => acc + v, 0) / values.length;
  const variance = values.reduce((acc, v) => acc + (v - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function calcVolatilityPair(bars: MarketBar[]): string {
  if (bars.length < 22) return "n/a";

  const returns: number[] = [];
  for (let i = 1; i < bars.length; i += 1) {
    const prev = bars[i - 1]?.close;
    const next = bars[i]?.close;
    if (!isFiniteNumber(prev) || !isFiniteNumber(next) || prev === 0) continue;
    returns.push(((next - prev) / prev) * 100);
  }

  if (returns.length < 21) return "n/a";
  const weekStd = calcStd(returns.slice(-5));
  const monthStd = calcStd(returns.slice(-21));

  if (!isFiniteNumber(weekStd) || !isFiniteNumber(monthStd)) return "n/a";
  return `${weekStd.toFixed(2)}% ${monthStd.toFixed(2)}%`;
}

function distFromAnchor(price: number | null, anchor: number | null): string {
  if (!isFiniteNumber(anchor)) return "n/a";
  if (!isFiniteNumber(price) || anchor === 0) return fmtNum(anchor, 2);
  const pct = ((price - anchor) / anchor) * 100;
  return `${fmtNum(anchor, 2)} ${fmtSigned(pct, 2)}%`;
}

function calcSmaDriftPercent(price: number | null, sma: number | null): string {
  if (!isFiniteNumber(price) || !isFiniteNumber(sma) || sma === 0) return "n/a";
  const pct = ((price - sma) / sma) * 100;
  return `${fmtSigned(pct, 2)}%`;
}

function normalizeAssetType(value: string | null | undefined): string {
  if (!value) return "n/a";
  const v = value.toUpperCase();
  if (v === "EQUITY") return "Equities";
  if (v === "ETF") return "ETF";
  if (v === "CRYPTOCURRENCY") return "Crypto";
  return value;
}

export function buildMarketStatColumns(args: {
  quote: MarketQuoteSummary;
  chartSummary: MarketSummary | null;
  chartBars: MarketBar[];
}): MarketStatCell[][] {
  const bars = sortedBars(args.chartBars);
  const quote = args.quote;

  const price =
    (isFiniteNumber(args.chartSummary?.close) ? args.chartSummary?.close : null) ??
    (isFiniteNumber(quote.price) ? quote.price : null);

  const prevClose =
    (isFiniteNumber(args.chartSummary?.prevClose) ? args.chartSummary?.prevClose : null) ??
    (isFiniteNumber(quote.prevClose) ? quote.prevClose : null);

  const volume =
    (bars.length > 0 && isFiniteNumber(bars[bars.length - 1]?.volume) ? bars[bars.length - 1]?.volume : null) ??
    (isFiniteNumber(quote.volume) ? quote.volume : null);

  const avgVolume = isFiniteNumber(quote.avgVolume) ? quote.avgVolume : null;
  const relVolume =
    (isFiniteNumber(quote.relVolume) ? quote.relVolume : null) ??
    (isFiniteNumber(volume) && isFiniteNumber(avgVolume) && avgVolume !== 0 ? volume / avgVolume : null);

  const high52 =
    (isFiniteNumber(args.chartSummary?.high52) ? args.chartSummary?.high52 : null) ??
    (isFiniteNumber(quote.high52) ? quote.high52 : null);
  const low52 =
    (isFiniteNumber(args.chartSummary?.low52) ? args.chartSummary?.low52 : null) ??
    (isFiniteNumber(quote.low52) ? quote.low52 : null);

  const perfWeek = calcLookbackPerf(bars, 5);
  const perfMonth = calcLookbackPerf(bars, 21);
  const perfQuarter = calcLookbackPerf(bars, 63);
  const perfHalfY = calcLookbackPerf(bars, 126);
  const perfYear = calcLookbackPerf(bars, 252);
  const perf3Y = calcLookbackPerf(bars, 756);
  const perf5Y = calcLookbackPerf(bars, 1260);
  const perf10Y = calcLookbackPerf(bars, 2520);
  const perfYtd = calcYtdPerf(bars);

  const changePct =
    (isFiniteNumber(args.chartSummary?.changePct) ? args.chartSummary?.changePct : null) ??
    (isFiniteNumber(quote.changePct) ? quote.changePct : null) ??
    (isFiniteNumber(price) && isFiniteNumber(prevClose) && prevClose !== 0 ? ((price - prevClose) / prevClose) * 100 : null);

  const columns: MarketStatCell[][] = [
    [
      { label: "Index", value: quote.indexName ?? "n/a" },
      { label: "Market Cap", value: fmtCompactNumber(quote.marketCap) },
      { label: "Enterprise Value", value: fmtCompactNumber(quote.enterpriseValue) },
      { label: "Income", value: fmtCompactNumber(quote.income) },
      { label: "Sales", value: fmtCompactNumber(quote.sales) },
      { label: "Book/sh", value: fmtNum(quote.bookValue, 2) },
      { label: "Cash/sh", value: fmtNum(quote.cashPerShare, 2) },
      { label: "Dividend Est.", value: fmtDividend(quote.dividendRate, quote.dividendYield) },
      { label: "Dividend TTM", value: fmtDividend(quote.trailingDividendRate, quote.trailingDividendYield) },
      { label: "Dividend Ex-Date", value: fmtDate(quote.exDividendDate) },
      { label: "Dividend Gr. 3/5Y", value: "n/a" },
      { label: "Payout", value: fmtPercentFromRatio(quote.payoutRatio, { decimals: 2 }) },
      { label: "Employees", value: fmtWholeNumber(quote.employees) },
      { label: "IPO", value: fmtDate(quote.ipoDate) },
    ],
    [
      { label: "P/E", value: fmtNum(quote.peRatio, 2) },
      { label: "Forward P/E", value: fmtNum(quote.forwardPE, 2) },
      { label: "PEG", value: fmtNum(quote.pegRatio, 2) },
      { label: "P/S", value: fmtNum(quote.priceToSales, 2) },
      { label: "P/B", value: fmtNum(quote.priceToBook, 2) },
      { label: "P/C", value: fmtNum(quote.priceToCash, 2) },
      { label: "P/FCF", value: fmtNum(quote.priceToFreeCashFlow, 2) },
      { label: "P/EF", value: "n/a" },
      { label: "EV/EBITDA", value: fmtNum(quote.evToEbitda, 2) },
      { label: "EV/Sales", value: fmtNum(quote.evToSales, 2) },
      { label: "Quick Ratio", value: fmtNum(quote.quickRatio, 2) },
      { label: "Current Ratio", value: fmtNum(quote.currentRatio, 2) },
      { label: "Debt/Eq", value: fmtNum(quote.debtToEquity, 2) },
      { label: "LT Debt/Eq", value: fmtNum(quote.longTermDebtToEquity, 2) },
    ],
    [
      { label: "EPS (ttm)", value: fmtNum(quote.eps, 2) },
      { label: "EPS next Y", value: fmtNum(quote.forwardEps, 2) },
      { label: "EPS next Q", value: fmtNum(quote.epsNextQ, 2) },
      { label: "EPS this Y", value: fmtPercentFromRatio(quote.earningsGrowth, { decimals: 2, signed: true }) },
      { label: "EPS next 5Y", value: "n/a" },
      { label: "EPS past 5Y", value: "n/a" },
      { label: "Sales past 5Y", value: "n/a" },
      { label: "EPS Y/Y TTM", value: fmtPercentFromRatio(quote.earningsGrowth, { decimals: 2, signed: true }) },
      { label: "Sales Y/Y TTM", value: fmtPercentFromRatio(quote.revenueGrowth, { decimals: 2, signed: true }) },
      { label: "EPS Q/Q", value: fmtPercentFromRatio(quote.earningsQuarterlyGrowth, { decimals: 2, signed: true }) },
      { label: "Sales Q/Q", value: fmtPercentFromRatio(quote.revenueQuarterlyGrowth, { decimals: 2, signed: true }) },
      { label: "Earnings", value: fmtDate(quote.earningsDate) },
      { label: "EPS/Sales Surpr.", value: "n/a" },
    ],
    [
      { label: "Insider Own", value: fmtPercentFromRatio(quote.insiderOwn, { decimals: 2 }) },
      { label: "Insider Trans", value: fmtPercentFromRatio(quote.insiderTrans, { decimals: 2, signed: true }) },
      { label: "Inst Own", value: fmtPercentFromRatio(quote.instOwn, { decimals: 2 }) },
      { label: "Inst Trans", value: fmtPercentFromRatio(quote.instTrans, { decimals: 2, signed: true }) },
      { label: "Short Ratio", value: fmtNum(quote.shortRatio, 2) },
      { label: "ROA", value: fmtPercentFromRatio(quote.roa, { decimals: 2 }) },
      { label: "ROE", value: fmtPercentFromRatio(quote.roe, { decimals: 2 }) },
      { label: "ROIC", value: fmtPercentFromRatio(quote.roic, { decimals: 2 }) },
      { label: "Gross Margin", value: fmtPercentFromRatio(quote.grossMargin, { decimals: 2 }) },
      { label: "Oper. Margin", value: fmtPercentFromRatio(quote.operatingMargin, { decimals: 2 }) },
      { label: "Profit Margin", value: fmtPercentFromRatio(quote.profitMargin, { decimals: 2 }) },
      { label: "SMA20", value: calcSmaDriftPercent(price, quote.sma20 ?? null) },
      { label: "SMA50", value: calcSmaDriftPercent(price, quote.sma50 ?? null) },
      { label: "SMA200", value: calcSmaDriftPercent(price, quote.sma200 ?? null) },
    ],
    [
      { label: "Shs Outstand", value: fmtCompactNumber(quote.sharesOutstanding) },
      { label: "Shs Float", value: fmtCompactNumber(quote.sharesFloat) },
      { label: "Short Float", value: fmtPercentFromRatio(quote.shortFloat, { decimals: 2 }) },
      { label: "Short Interest", value: fmtCompactNumber(quote.shortInterest) },
      { label: "52W High", value: distFromAnchor(price, high52) },
      { label: "52W Low", value: distFromAnchor(price, low52) },
      { label: "Volatility", value: calcVolatilityPair(bars) },
      { label: "ATR (14)", value: fmtNum(quote.atr14, 2) },
      { label: "RSI (14)", value: fmtNum(quote.rsi14, 2) },
      { label: "Beta", value: fmtNum(quote.beta, 2) },
      { label: "Rel Volume", value: fmtNum(relVolume, 2) },
      { label: "Avg Volume", value: fmtCompactNumber(avgVolume) },
      { label: "Volume", value: fmtWholeNumber(volume) },
    ],
    [
      { label: "Perf Week", value: fmtPercentFromPercentValue(perfWeek, { signed: true }) },
      { label: "Perf Month", value: fmtPercentFromPercentValue(perfMonth, { signed: true }) },
      { label: "Perf Quarter", value: fmtPercentFromPercentValue(perfQuarter, { signed: true }) },
      { label: "Perf Half Y", value: fmtPercentFromPercentValue(perfHalfY, { signed: true }) },
      { label: "Perf YTD", value: fmtPercentFromPercentValue(perfYtd, { signed: true }) },
      { label: "Perf Year", value: fmtPercentFromPercentValue(perfYear, { signed: true }) },
      { label: "Perf 3Y", value: fmtPercentFromPercentValue(perf3Y, { signed: true }) },
      { label: "Perf 5Y", value: fmtPercentFromPercentValue(perf5Y, { signed: true }) },
      { label: "Perf 10Y", value: fmtPercentFromPercentValue(perf10Y, { signed: true }) },
      { label: "Recom", value: fmtNum(quote.recommendationMean, 2) },
      { label: "Target Price", value: fmtNum(quote.target1Y, 2) },
      { label: "Prev Close", value: fmtNum(prevClose, 2) },
      { label: "Price", value: fmtNum(price, 2) },
      { label: "Change", value: fmtPercentFromPercentValue(changePct, { signed: true }) },
    ],
  ];

  return columns;
}

export function analysisHeaderSummary(args: {
  quote: MarketQuoteSummary;
  chartSummary: MarketSummary | null;
}): MarketStatCell[] {
  const quote = args.quote;
  const summary = args.chartSummary;

  const price = (isFiniteNumber(summary?.close) ? summary?.close : null) ?? (isFiniteNumber(quote.price) ? quote.price : null);
  const prevClose =
    (isFiniteNumber(summary?.prevClose) ? summary?.prevClose : null) ??
    (isFiniteNumber(quote.prevClose) ? quote.prevClose : null);
  const change =
    (isFiniteNumber(summary?.change) ? summary?.change : null) ??
    (isFiniteNumber(quote.change) ? quote.change : null) ??
    (isFiniteNumber(price) && isFiniteNumber(prevClose) ? price - prevClose : null);
  const changePct =
    (isFiniteNumber(summary?.changePct) ? summary?.changePct : null) ??
    (isFiniteNumber(quote.changePct) ? quote.changePct : null) ??
    (isFiniteNumber(price) && isFiniteNumber(prevClose) && prevClose !== 0 ? ((price - prevClose) / prevClose) * 100 : null);

  return [
    { label: "Open", value: fmtNum((isFiniteNumber(summary?.open) ? summary?.open : null) ?? quote.open ?? null, 2) },
    { label: "High", value: fmtNum((isFiniteNumber(summary?.high) ? summary?.high : null) ?? quote.dayHigh ?? null, 2) },
    { label: "Low", value: fmtNum((isFiniteNumber(summary?.low) ? summary?.low : null) ?? quote.dayLow ?? null, 2) },
    { label: "Prev Close", value: fmtNum(prevClose, 2) },
    { label: "Change", value: fmtSigned(change, 2) },
    { label: "Change %", value: fmtPercentFromPercentValue(changePct, { signed: true }) },
    { label: "52W High", value: fmtNum((isFiniteNumber(summary?.high52) ? summary?.high52 : null) ?? quote.high52 ?? null, 2) },
    { label: "52W Low", value: fmtNum((isFiniteNumber(summary?.low52) ? summary?.low52 : null) ?? quote.low52 ?? null, 2) },
    { label: "Mkt Cap", value: fmtCompactNumber(quote.marketCap) },
    { label: "P/E", value: fmtNum(quote.peRatio, 2) },
    { label: "Beta", value: fmtNum(quote.beta, 2) },
    { label: "EPS", value: fmtNum(quote.eps, 2) },
    { label: "Avg Vol", value: fmtCompactNumber(quote.avgVolume) },
    { label: "Div Yield", value: fmtPercentFromRatio(quote.dividendYield) },
    { label: "Bid", value: fmtNum(quote.bid, 2) },
    { label: "Ask", value: fmtNum(quote.ask, 2) },
    { label: "Sector", value: quote.sector ?? "n/a" },
    { label: "Industry", value: quote.industry ?? "n/a" },
    { label: "Asset", value: normalizeAssetType(quote.assetType ?? quote.quoteType) },
    { label: "Exchange", value: quote.exchange ?? "n/a" },
  ];
}
