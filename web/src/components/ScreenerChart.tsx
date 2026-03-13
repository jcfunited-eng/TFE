"use client";

import { type MouseEvent, useMemo, useState } from "react";

type ChartBar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type ScreenerChartType = "candle-ta" | "candle" | "line" | "ohlc" | "hollow-candle" | "heikin-ashi";
export type MarketTimeframe = "intraday" | "daily" | "weekly" | "monthly";
export type ScreenerChartInterval = "1m" | "5m" | "15m" | "30m" | "60m" | "1d" | "1wk" | "1mo";
export type ScreenerChartRange = "1d" | "5d" | "1mo" | "3mo" | "6mo" | "ytd" | "1y" | "2y" | "5y" | "max";

export type ScreenerChartControls = {
  chartType: ScreenerChartType;
  timeframe: MarketTimeframe;
  interval: ScreenerChartInterval;
  range: ScreenerChartRange;
};

type ScreenerChartProps = {
  ticker: string;
  bars: ChartBar[];
  controls: ScreenerChartControls;
  loading?: boolean;
  onControlsChange: (next: ScreenerChartControls) => void;
};

const SVG_WIDTH = 1120;
const SVG_HEIGHT = 420;
const CHART_LEFT = 62;
const CHART_RIGHT = 996;
const PRICE_TOP = 20;
const PRICE_BOTTOM = 280;
const VOLUME_TOP = 305;
const VOLUME_BOTTOM = 394;
const GRID_ROWS = 6;
const PRICE_LABEL_X = CHART_RIGHT + 14;
const HOVER_PRICE_TAG_WIDTH = 60;
const HOVER_PRICE_TAG_HEIGHT = 18;

const CHART_TYPE_OPTIONS: Array<{ value: ScreenerChartType; label: string }> = [
  { value: "candle", label: "Candle" },
  { value: "candle-ta", label: "Candle - TA" },
  { value: "line", label: "Line" },
  { value: "ohlc", label: "OHLC" },
  { value: "hollow-candle", label: "Hollow Candle" },
  { value: "heikin-ashi", label: "Heikin Ashi" },
];

const TIMEFRAME_OPTIONS: Array<{ value: MarketTimeframe; label: string }> = [
  { value: "intraday", label: "Intraday" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

const RANGE_SECTIONS: Array<{ label: string; values: Array<{ value: ScreenerChartRange; label: string }> }> = [
  {
    label: "Days",
    values: [
      { value: "1d", label: "1 Day" },
      { value: "5d", label: "5 Days" },
    ],
  },
  {
    label: "Months",
    values: [
      { value: "1mo", label: "1 Month" },
      { value: "3mo", label: "3 Months" },
      { value: "6mo", label: "6 Months" },
    ],
  },
  {
    label: "Years",
    values: [
      { value: "ytd", label: "Year to Date" },
      { value: "1y", label: "1 Year" },
      { value: "2y", label: "2 Years" },
      { value: "5y", label: "5 Years" },
      { value: "max", label: "Max" },
    ],
  },
];

const TIMEFRAME_INTERVAL_DEFAULTS: Record<MarketTimeframe, ScreenerChartInterval> = {
  intraday: "5m",
  daily: "1d",
  weekly: "1wk",
  monthly: "1mo",
};

const TIMEFRAME_RANGE_DEFAULTS: Record<MarketTimeframe, ScreenerChartRange> = {
  intraday: "1d",
  daily: "1y",
  weekly: "2y",
  monthly: "5y",
};

function chartTypeLabel(value: ScreenerChartType): string {
  const match = CHART_TYPE_OPTIONS.find((option) => option.value === value);
  return match ? match.label : "Candle - TA";
}

function rangeLabel(value: ScreenerChartRange): string {
  for (const section of RANGE_SECTIONS) {
    const match = section.values.find((item) => item.value === value);
    if (match) return match.label;
  }
  return "1 Year";
}

function clamp(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

function toFiniteNumber(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function parseTimeMs(value: string): number | null {
  const ms = Date.parse(value);
  return Number.isFinite(ms) ? ms : null;
}

function normalizeBars(input: ChartBar[]): ChartBar[] {
  const normalized: Array<ChartBar & { __timeMs: number }> = [];

  for (const bar of input) {
    const time = String(bar.time ?? "").trim();
    const timeMs = parseTimeMs(time);
    const open = toFiniteNumber(bar.open);
    const high = toFiniteNumber(bar.high);
    const low = toFiniteNumber(bar.low);
    const close = toFiniteNumber(bar.close);
    const volume = toFiniteNumber(bar.volume) ?? 0;

    if (!time || timeMs === null) continue;
    if (open === null || high === null || low === null || close === null) continue;
    if (open <= 0 || high <= 0 || low <= 0 || close <= 0) continue;

    let nextHigh = Math.max(high, open, close);
    let nextLow = Math.min(low, open, close);
    if (nextLow > nextHigh) {
      const swap = nextLow;
      nextLow = nextHigh;
      nextHigh = swap;
    }

    normalized.push({
      time,
      open,
      high: nextHigh,
      low: nextLow,
      close,
      volume: Math.max(0, volume),
      __timeMs: timeMs,
    });
  }

  normalized.sort((a, b) => a.__timeMs - b.__timeMs);

  const deduped: ChartBar[] = [];
  let previousTime: number | null = null;
  for (const bar of normalized) {
    if (previousTime !== null && bar.__timeMs === previousTime) {
      deduped[deduped.length - 1] = {
        time: bar.time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
        volume: bar.volume,
      };
      continue;
    }

    deduped.push({
      time: bar.time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
      volume: bar.volume,
    });
    previousTime = bar.__timeMs;
  }

  return deduped;
}

function movingAverage(values: number[], period: number): Array<number | null> {
  const out: Array<number | null> = [];
  let sum = 0;

  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    sum += value;

    if (index >= period) {
      sum -= values[index - period];
    }

    const window = Math.min(index + 1, period);
    out.push(sum / window);
  }

  return out;
}

function pathFromSeries(series: Array<number | null>, xForIndex: (index: number) => number, yForValue: (value: number) => number): string {
  let path = "";
  let drawing = false;

  for (let index = 0; index < series.length; index += 1) {
    const value = series[index];
    if (value === null) {
      drawing = false;
      continue;
    }

    const x = xForIndex(index);
    const y = yForValue(value);

    if (!drawing) {
      path += `M ${x.toFixed(2)} ${y.toFixed(2)} `;
      drawing = true;
    } else {
      path += `L ${x.toFixed(2)} ${y.toFixed(2)} `;
    }
  }

  return path.trim();
}

function toHeikinAshi(bars: ChartBar[]): ChartBar[] {
  if (bars.length === 0) return [];

  const out: ChartBar[] = [];
  let prevHaOpen = (bars[0].open + bars[0].close) / 2;
  let prevHaClose = (bars[0].open + bars[0].high + bars[0].low + bars[0].close) / 4;

  for (let index = 0; index < bars.length; index += 1) {
    const bar = bars[index];
    const haClose = (bar.open + bar.high + bar.low + bar.close) / 4;
    const haOpen = index === 0 ? prevHaOpen : (prevHaOpen + prevHaClose) / 2;
    const haHigh = Math.max(bar.high, haOpen, haClose);
    const haLow = Math.min(bar.low, haOpen, haClose);

    out.push({
      ...bar,
      open: haOpen,
      high: haHigh,
      low: haLow,
      close: haClose,
    });

    prevHaOpen = haOpen;
    prevHaClose = haClose;
  }

  return out;
}

function timeframeFromInterval(interval: ScreenerChartInterval): MarketTimeframe {
  if (["1m", "5m", "15m", "30m", "60m"].includes(interval)) return "intraday";
  if (interval === "1wk") return "weekly";
  if (interval === "1mo") return "monthly";
  return "daily";
}

function supportsCandleBodies(chartType: ScreenerChartType): boolean {
  return chartType === "candle" || chartType === "candle-ta" || chartType === "hollow-candle" || chartType === "heikin-ashi";
}

export const DEFAULT_SCREENER_CHART_CONTROLS: ScreenerChartControls = {
  chartType: "candle-ta",
  timeframe: "daily",
  interval: "1d",
  range: "1y",
};

export default function ScreenerChart({ ticker, bars, controls, loading = false, onControlsChange }: ScreenerChartProps) {
  const [showTypeMenu, setShowTypeMenu] = useState(false);
  const [showRangeMenu, setShowRangeMenu] = useState(false);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const safeControls = useMemo<ScreenerChartControls>(() => {
    const inferredTimeframe = timeframeFromInterval(controls.interval);
    return {
      chartType: controls.chartType,
      timeframe: controls.timeframe ?? inferredTimeframe,
      interval: controls.interval,
      range: controls.range,
    };
  }, [controls]);

  const normalizedBars = useMemo(() => normalizeBars(bars), [bars]);

  const drawBars = useMemo(() => {
    if (safeControls.chartType === "heikin-ashi") {
      return toHeikinAshi(normalizedBars);
    }
    return normalizedBars;
  }, [normalizedBars, safeControls.chartType]);

  const closes = drawBars.map((bar) => bar.close);
  const highs = drawBars.map((bar) => bar.high);
  const lows = drawBars.map((bar) => bar.low);
  const volumes = drawBars.map((bar) => bar.volume);

  const ma20 = movingAverage(closes, 20);
  const ma50 = movingAverage(closes, 50);
  const ma200 = movingAverage(closes, 200);

  const overlayValues: number[] = [...highs, ...lows];
  for (const value of ma20) {
    if (value !== null) overlayValues.push(value);
  }
  for (const value of ma50) {
    if (value !== null) overlayValues.push(value);
  }
  for (const value of ma200) {
    if (value !== null) overlayValues.push(value);
  }

  const maxHigh = overlayValues.length > 0 ? Math.max(...overlayValues) : 0;
  const minLow = overlayValues.length > 0 ? Math.min(...overlayValues) : 0;
  const maxVolume = volumes.length > 0 ? Math.max(...volumes, 1) : 1;

  const span = Math.max(maxHigh - minLow, 0.000001);
  const paddedMin = minLow - span * 0.04;
  const paddedMax = maxHigh + span * 0.04;
  const priceSpan = Math.max(paddedMax - paddedMin, 0.000001);

  const plotWidth = CHART_RIGHT - CHART_LEFT;
  const candleWidthRaw = drawBars.length > 0 ? plotWidth / drawBars.length : 1;
  const candleBodyWidth = clamp(candleWidthRaw * 0.62, 1.2, 6.2);

  const xForIndex = (index: number): number => CHART_LEFT + ((index + 0.5) / Math.max(drawBars.length, 1)) * plotWidth;
  const yForPrice = (value: number): number => PRICE_BOTTOM - ((value - paddedMin) / priceSpan) * (PRICE_BOTTOM - PRICE_TOP);
  const yForVolume = (value: number): number => VOLUME_BOTTOM - (value / maxVolume) * (VOLUME_BOTTOM - VOLUME_TOP);

  const ma20Path = pathFromSeries(ma20, xForIndex, yForPrice);
  const ma50Path = pathFromSeries(ma50, xForIndex, yForPrice);
  const ma200Path = pathFromSeries(ma200, xForIndex, yForPrice);

  const latest = drawBars.length > 0 ? drawBars[drawBars.length - 1] : null;
  const activeIndex =
    hoverIndex !== null && hoverIndex >= 0 && hoverIndex < drawBars.length ? hoverIndex : drawBars.length - 1;
  const activeBar = activeIndex >= 0 ? drawBars[activeIndex] : null;
  const activePrev = activeIndex > 0 ? drawBars[activeIndex - 1] : activeBar;
  const change = activeBar && activePrev ? activeBar.close - activePrev.close : 0;
  const changePct = activeBar && activePrev && activePrev.close !== 0 ? (change / activePrev.close) * 100 : 0;
  const changeColor = change >= 0 ? "#1f8f52" : "#c84a4a";
  const hoverBar = hoverIndex !== null && hoverIndex >= 0 && hoverIndex < drawBars.length ? drawBars[hoverIndex] : null;
  const hoverX = hoverIndex !== null ? xForIndex(hoverIndex) : null;
  const hoverY = hoverBar ? yForPrice(hoverBar.close) : null;

  function updateControls(partial: Partial<ScreenerChartControls>): void {
    onControlsChange({ ...safeControls, ...partial });
  }

  function onSelectTimeframe(nextTimeframe: MarketTimeframe): void {
    const nextInterval = TIMEFRAME_INTERVAL_DEFAULTS[nextTimeframe];
    const fallbackRange = TIMEFRAME_RANGE_DEFAULTS[nextTimeframe];

    let nextRange = safeControls.range;
    if (nextTimeframe === "intraday" && ["2y", "5y", "max"].includes(nextRange)) {
      nextRange = fallbackRange;
    }

    updateControls({
      timeframe: nextTimeframe,
      interval: nextInterval,
      range: nextRange,
    });
  }

  function onSelectRange(nextRange: ScreenerChartRange): void {
    updateControls({ range: nextRange });
    setShowRangeMenu(false);
  }

  function onSelectChartType(nextType: ScreenerChartType): void {
    updateControls({ chartType: nextType });
    setShowTypeMenu(false);
  }

  function onChartMouseMove(event: MouseEvent<SVGSVGElement>): void {
    if (drawBars.length < 2) {
      setHoverIndex(null);
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    if (rect.width <= 0) {
      setHoverIndex(null);
      return;
    }

    const localX = ((event.clientX - rect.left) / rect.width) * SVG_WIDTH;
    if (localX < CHART_LEFT || localX > CHART_RIGHT) {
      setHoverIndex(null);
      return;
    }

    const normalized = (localX - CHART_LEFT) / plotWidth;
    const rawIndex = Math.round(normalized * drawBars.length - 0.5);
    const nextIndex = Math.max(0, Math.min(drawBars.length - 1, rawIndex));
    setHoverIndex(nextIndex);
  }

  function onChartMouseLeave(): void {
    setHoverIndex(null);
  }

  return (
    <div className="screener-chart-shell">
      <div className="screener-chart-toolbar">
        <div className="screener-dropdown-wrap">
          <button
            type="button"
            className="screener-dropdown-trigger"
            onClick={() => {
              setShowTypeMenu((current) => !current);
              setShowRangeMenu(false);
            }}
            disabled={loading}
          >
            {chartTypeLabel(safeControls.chartType)} <span aria-hidden="true">▾</span>
          </button>

          {showTypeMenu ? (
            <div className="screener-dropdown-menu" role="menu" aria-label="Chart type options">
              {CHART_TYPE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={safeControls.chartType === option.value ? "active" : ""}
                  onClick={() => onSelectChartType(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="screener-timeframe-tabs">
          {TIMEFRAME_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={safeControls.timeframe === option.value ? "active" : ""}
              onClick={() => onSelectTimeframe(option.value)}
              disabled={loading}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="screener-dropdown-wrap">
          <button
            type="button"
            className="screener-dropdown-trigger"
            onClick={() => {
              setShowRangeMenu((current) => !current);
              setShowTypeMenu(false);
            }}
            disabled={loading}
            title="Range"
          >
            {rangeLabel(safeControls.range)} <span aria-hidden="true">▾</span>
          </button>

          {showRangeMenu ? (
            <div className="screener-dropdown-menu screener-range-menu" role="menu" aria-label="Range options">
              {RANGE_SECTIONS.map((section) => (
                <div key={section.label} className="screener-range-section">
                  <div className="screener-range-title">{section.label}</div>
                  {section.values.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      className={safeControls.range === option.value ? "active" : ""}
                      onClick={() => onSelectRange(option.value)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {drawBars.length < 2 ? (
        <p className="tfe-muted">No chart data available for {ticker}.</p>
      ) : (
        <>
          {activeBar ? (
            <div className="screener-chart-meta">
              <span>{activeBar.time.slice(0, 16)}</span>
              <span>O {activeBar.open.toFixed(2)}</span>
              <span>H {activeBar.high.toFixed(2)}</span>
              <span>L {activeBar.low.toFixed(2)}</span>
              <span>C {activeBar.close.toFixed(2)}</span>
              <span style={{ color: changeColor }}>
                {change >= 0 ? "+" : ""}
                {change.toFixed(2)} ({change >= 0 ? "+" : ""}
                {changePct.toFixed(2)}%)
              </span>
            </div>
          ) : null}

          <svg
            viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
            className="screener-chart-canvas"
            aria-label={`${ticker} chart`}
            onMouseMove={onChartMouseMove}
            onMouseLeave={onChartMouseLeave}
            style={{ shapeRendering: "geometricPrecision", textRendering: "geometricPrecision" }}
          >
            <rect x="0" y="0" width={SVG_WIDTH} height={SVG_HEIGHT} fill="rgba(246, 250, 246, 0.95)" />
            <rect x={CHART_LEFT} y={PRICE_TOP} width={plotWidth} height={PRICE_BOTTOM - PRICE_TOP} fill="rgba(249, 252, 249, 0.82)" />
            <rect x={CHART_LEFT} y={VOLUME_TOP} width={plotWidth} height={VOLUME_BOTTOM - VOLUME_TOP} fill="rgba(244, 248, 244, 0.9)" />

            {Array.from({ length: GRID_ROWS + 1 }).map((_, idx) => {
              const y = PRICE_TOP + (idx / GRID_ROWS) * (PRICE_BOTTOM - PRICE_TOP);
              const price = paddedMax - (idx / GRID_ROWS) * priceSpan;
              return (
                <g key={`grid-${idx}`}>
                  <line x1={CHART_LEFT} y1={y} x2={CHART_RIGHT} y2={y} stroke="rgba(38,62,52,0.15)" strokeWidth="1" />
                  <text x={PRICE_LABEL_X} y={y + 4} fontSize="10" fill="#355648">
                    {price.toFixed(2)}
                  </text>
                </g>
              );
            })}

            {drawBars.map((bar, index) => {
              const x = xForIndex(index);
              const openY = yForPrice(bar.open);
              const closeY = yForPrice(bar.close);
              const highY = yForPrice(bar.high);
              const lowY = yForPrice(bar.low);
              const rising = bar.close >= bar.open;
              const color = rising ? "#1f8f52" : "#ca4e4e";

              const top = Math.min(openY, closeY);
              const bottom = Math.max(openY, closeY);
              const bodyHeight = Math.max(bottom - top, 1.2);

              const volumeY = yForVolume(bar.volume);
              const volumeHeight = Math.max(VOLUME_BOTTOM - volumeY, 1.2);
              const volumeColor = rising ? "rgba(43,155,84,0.34)" : "rgba(198,76,76,0.34)";

              return (
                <g key={`${bar.time}-${index}`}>
                  <rect x={x - candleBodyWidth / 2} y={volumeY} width={candleBodyWidth} height={volumeHeight} fill={volumeColor} />

                  {safeControls.chartType === "line" ? null : (
                    <line x1={x} y1={highY} x2={x} y2={lowY} stroke={color} strokeWidth="1" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
                  )}

                  {safeControls.chartType === "ohlc" ? (
                    <>
                      <line
                        x1={x - candleBodyWidth / 2}
                        y1={openY}
                        x2={x}
                        y2={openY}
                        stroke={color}
                        strokeWidth="1"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                      />
                      <line
                        x1={x}
                        y1={closeY}
                        x2={x + candleBodyWidth / 2}
                        y2={closeY}
                        stroke={color}
                        strokeWidth="1"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                      />
                    </>
                  ) : null}

                  {supportsCandleBodies(safeControls.chartType) ? (
                    <rect
                      x={x - candleBodyWidth / 2}
                      y={top}
                      width={candleBodyWidth}
                      height={bodyHeight}
                      fill={
                        safeControls.chartType === "hollow-candle"
                          ? rising
                            ? "rgba(0,0,0,0)"
                            : "rgba(202,78,78,0.9)"
                          : rising
                            ? "rgba(31,143,82,0.9)"
                            : "rgba(202,78,78,0.9)"
                      }
                      stroke={color}
                      strokeWidth="0.8"
                      vectorEffect="non-scaling-stroke"
                    />
                  ) : null}
                </g>
              );
            })}

            {safeControls.chartType === "line" ? (
              <path
                d={pathFromSeries(closes, xForIndex, yForPrice)}
                fill="none"
                stroke="#4e8bc4"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
              />
            ) : null}

            {safeControls.chartType === "candle-ta" && ma20Path ? (
              <path d={ma20Path} fill="none" stroke="#dd7e2f" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
            ) : null}
            {safeControls.chartType === "candle-ta" && ma50Path ? (
              <path d={ma50Path} fill="none" stroke="#a960d1" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
            ) : null}
            {safeControls.chartType === "candle-ta" && ma200Path ? (
              <path d={ma200Path} fill="none" stroke="#4f93d4" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
            ) : null}

            {hoverBar && hoverX !== null && hoverY !== null ? (
              <>
                <line
                  x1={CHART_LEFT}
                  y1={hoverY}
                  x2={CHART_RIGHT}
                  y2={hoverY}
                  stroke="rgba(41, 75, 60, 0.55)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <line
                  x1={hoverX}
                  y1={PRICE_TOP}
                  x2={hoverX}
                  y2={VOLUME_BOTTOM}
                  stroke="rgba(41, 75, 60, 0.55)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <rect
                  x={CHART_RIGHT + 8}
                  y={hoverY - HOVER_PRICE_TAG_HEIGHT / 2}
                  width={HOVER_PRICE_TAG_WIDTH}
                  height={HOVER_PRICE_TAG_HEIGHT}
                  rx={3}
                  fill="rgba(243, 249, 244, 0.97)"
                  stroke="rgba(38, 68, 54, 0.45)"
                />
                <text
                  x={CHART_RIGHT + 8 + HOVER_PRICE_TAG_WIDTH / 2}
                  y={hoverY + 3}
                  textAnchor="middle"
                  fontSize="10"
                  fill="#1f3f31"
                >
                  {hoverBar.close.toFixed(2)}
                </text>
              </>
            ) : null}

            <line x1={CHART_LEFT} y1={PRICE_BOTTOM} x2={CHART_RIGHT} y2={PRICE_BOTTOM} stroke="rgba(38,62,52,0.3)" strokeWidth="1" />
            <line x1={CHART_LEFT} y1={VOLUME_BOTTOM} x2={CHART_RIGHT} y2={VOLUME_BOTTOM} stroke="rgba(38,62,52,0.28)" strokeWidth="1" />
          </svg>

          {safeControls.chartType === "candle-ta" ? (
            <div className="screener-chart-legend">
              <span className="line line-ma20">MA20</span>
              <span className="line line-ma50">MA50</span>
              <span className="line line-ma200">MA200</span>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
