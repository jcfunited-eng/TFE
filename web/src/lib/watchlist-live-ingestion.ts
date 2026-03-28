import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

type DecisionLabel = "Accumulate" | "Hold" | "Avoid";
type Classification = "BUY" | "HOLD" | "SELL";

type RuntimeJoinedRow = {
  ticker: string;
  decision_label: string | null;
  decision_reason: string | null;
  regime: string | null;
  price: number | string | null;
  s_uf: number | string | null;
  r_uf: number | string | null;
  bar_count: number | string | null;
  min_bars_for_accumulate: number | string | null;
  stability_score: number | string | null;
  max_dd: number | string | null;
  current_ratio: number | string | null;
  free_cash_flow: number | string | null;
  gross_margin: number | string | null;
  gross_profit: number | string | null;
  operating_cash_flow: number | string | null;
  revenues: number | string | null;
  market_cap: number | string | null;
  sector: string | null;
};

export type WatchlistMetricRow = {
  ticker: string;
  decision: DecisionLabel;
  decisionReason: string;
  decisionReasonCode: string;
  classification: Classification;
  price: number | null;
  regime: string;
  S_UF: number;
  R_UF: number;
  barCount: number;
  minBarsForAccumulate: number;
  stability_score: number | null;
  max_dd: number | null;
};

type MetricLoadResult = {
  metrics: WatchlistMetricRow[];
  missingSymbols: string[];
};

function normalizeTicker(value: unknown): string {
  return String(value ?? "").trim().toUpperCase();
}

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function normalizeDecision(value: unknown): DecisionLabel {
  const text = String(value ?? "").trim();
  if (text === "Accumulate") return "Accumulate";
  if (text === "Avoid") return "Avoid";
  return "Hold";
}

function classificationFromDecision(decision: DecisionLabel): Classification {
  if (decision === "Accumulate") return "BUY";
  if (decision === "Avoid") return "SELL";
  return "HOLD";
}

function reasonCodeFromDecision(decision: DecisionLabel): string {
  if (decision === "Accumulate") return "RUNTIME_ACCUMULATE";
  if (decision === "Avoid") return "RUNTIME_AVOID";
  return "RUNTIME_HOLD";
}

function toMetricRow(row: RuntimeJoinedRow): WatchlistMetricRow {
  const decision = normalizeDecision(row.decision_label);
  return {
    ticker: normalizeTicker(row.ticker),
    decision,
    decisionReason: String(row.decision_reason ?? "").trim() || "Runtime decision selected from latest table.",
    decisionReasonCode: reasonCodeFromDecision(decision),
    classification: classificationFromDecision(decision),
    price: toNumberOrNull(row.price),
    regime: String(row.regime ?? "").trim() || "UNKNOWN",
    S_UF: toNumber(row.s_uf),
    R_UF: toNumber(row.r_uf),
    barCount: Math.max(0, Math.trunc(toNumber(row.bar_count))),
    minBarsForAccumulate: Math.max(0, Math.trunc(toNumber(row.min_bars_for_accumulate))),
    stability_score: toNumberOrNull(row.stability_score),
    max_dd: toNumberOrNull(row.max_dd),
  };
}

async function queryRuntimeJoinedMetrics(symbols: string[]): Promise<Map<string, RuntimeJoinedRow>> {
  if (symbols.length === 0) return new Map<string, RuntimeJoinedRow>();

  const query = `
    SELECT
      r.ticker,
      r.decision_label,
      COALESCE(NULLIF(TRIM(r.reason_text), ''), NULLIF(TRIM(r.reason_code), '')) AS decision_reason,
      COALESCE(NULLIF(TRIM(r.regime), ''), NULLIF(TRIM(r.snapshot_row_json->>'regime'), '')) AS regime,
      COALESCE(
        CAST(NULLIF(r.snapshot_row_json->>'price', '') AS DOUBLE PRECISION),
        CAST(NULLIF(r.snapshot_row_json->>'close', '') AS DOUBLE PRECISION)
      ) AS price,
      CAST(NULLIF(r.snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) AS s_uf,
      CAST(NULLIF(r.snapshot_row_json->>'R_UF', '') AS DOUBLE PRECISION) AS r_uf,
      COALESCE(r.bar_count, CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER)) AS bar_count,
      COALESCE(r.min_bars_for_accumulate, 0) AS min_bars_for_accumulate,
      r.stability_score,
      r.max_dd,
      COALESCE(
        f.current_ratio,
        CAST(NULLIF(r.snapshot_row_json->>'current_ratio', '') AS DOUBLE PRECISION)
      ) AS current_ratio,
      COALESCE(
        f.free_cash_flow,
        CAST(NULLIF(r.snapshot_row_json->>'free_cash_flow', '') AS DOUBLE PRECISION)
      ) AS free_cash_flow,
      COALESCE(
        f.gross_margin,
        CAST(NULLIF(r.snapshot_row_json->>'gross_margin', '') AS DOUBLE PRECISION)
      ) AS gross_margin,
      COALESCE(
        f.gross_profit,
        CAST(NULLIF(r.snapshot_row_json->>'gross_profit', '') AS DOUBLE PRECISION)
      ) AS gross_profit,
      COALESCE(
        f.operating_cash_flow,
        CAST(NULLIF(r.snapshot_row_json->>'operating_cash_flow', '') AS DOUBLE PRECISION)
      ) AS operating_cash_flow,
      COALESCE(
        f.revenues,
        CAST(NULLIF(r.snapshot_row_json->>'revenues', '') AS DOUBLE PRECISION)
      ) AS revenues,
      COALESCE(
        f.market_cap,
        CAST(NULLIF(r.snapshot_row_json->>'market_cap', '') AS DOUBLE PRECISION)
      ) AS market_cap,
      COALESCE(NULLIF(TRIM(f.sector), ''), NULLIF(TRIM(r.snapshot_row_json->>'sector'), '')) AS sector
    FROM runtime_decisions_latest AS r
    LEFT JOIN l5_fundamentals_normalized AS f
      ON f.ticker = r.ticker
    WHERE r.ticker = ANY($1::text[])
    ORDER BY r.ticker ASC
  `;

  const result = await resolveRuntimePostgresPool().query<RuntimeJoinedRow>(query, [symbols]);
  const rows = new Map<string, RuntimeJoinedRow>();
  for (const row of result.rows) {
    const ticker = normalizeTicker(row.ticker);
    if (!ticker) continue;
    rows.set(ticker, row);
  }
  return rows;
}

export async function loadOrIngestWatchlistMetrics(symbols: string[]): Promise<MetricLoadResult> {
  const normalizedSymbols = Array.from(new Set(symbols.map((ticker) => normalizeTicker(ticker)).filter(Boolean)));
  if (normalizedSymbols.length === 0) {
    return { metrics: [], missingSymbols: [] };
  }

  const rows = await queryRuntimeJoinedMetrics(normalizedSymbols);
  const metrics: WatchlistMetricRow[] = [];
  const missingSymbols: string[] = [];

  for (const ticker of normalizedSymbols) {
    const row = rows.get(ticker);
    if (!row) {
      missingSymbols.push(ticker);
      continue;
    }
    metrics.push(toMetricRow(row));
  }

  return {
    metrics,
    missingSymbols: Array.from(new Set(missingSymbols)).sort(),
  };
}

export async function loadOrIngestWatchlistMetric(ticker: string): Promise<WatchlistMetricRow | null> {
  const normalized = normalizeTicker(ticker);
  if (!normalized) return null;
  const result = await loadOrIngestWatchlistMetrics([normalized]);
  return result.metrics[0] ?? null;
}
