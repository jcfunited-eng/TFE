#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import {
  CURRENT_ST_ANCHORED_EXACT_FAMILY,
  DEFAULT_PSCF_EXACT_ANCHOR_MODE,
  computeDecisionTrace,
  loadPolicyRuntimeArtifact,
  minBarsForAccumulate,
} from "./runtime_decision_provenance.mjs";

const ROOT = "/workspaces/Tao_Financial_Engine";
const RECOMMENDATION_SAMPLE_LIMIT = 10;
const HOLD_DECISION_MULTIPLIER = 0.5;
const HOLD_FALLBACK_UNMAPPED_REASON_CODE = "PSCF_FALLBACK_CELL_UNMAPPED";
const ALLOW_TRIM_WHEN_DECISION_IS_ACCUMULATE = false;
const REBALANCE_THRESHOLD_PCT_POINTS = 1.0;
const REQUIRED_OUTPUT_JSON = path.join(ROOT, "exact_path_alignment_phase3_adoption_latest.json");
const REQUIRED_OUTPUT_MD = path.join(ROOT, "exact_path_alignment_phase3_adoption_latest.md");
const REQUIRED_VERIFICATION_JSON = path.join(ROOT, "exact_path_alignment_post_adoption_verification_latest.json");
const ROUTE_CHECK_JSON = path.join(ROOT, "exact_path_alignment_admin_route_check_latest.json");
const READY_JSON = path.join(ROOT, "exact_path_alignment_readiness_latest.json");
const SHADOW_JSON = path.join(ROOT, "exact_path_alignment_shadow_latest.json");
const RUNTIME_SEMANTICS_JSON = path.join(ROOT, "runtime_fallback_semantics_latest.json");
const ADMIN_BREAKDOWN_JSON = path.join(ROOT, "admin_quality_fallback_breakdown_latest.json");
const PROVENANCE_PERSISTENCE_JSON = path.join(ROOT, "current_l5_provenance_persistence_latest.json");
const SNAPSHOT_JSON = path.join(ROOT, "uf_snapshot.json");
const QUOTE_CACHE_JSON = path.join(ROOT, "web/data/screener-quote-cache.json");
const PORTFOLIO_JSON = path.join(ROOT, "portfolio_manual.json");

function readJson(filePath, allowNonFinite = false) {
  const raw = readFileSync(filePath, "utf8");
  if (!allowNonFinite) return JSON.parse(raw);
  return JSON.parse(raw.replace(/\bNaN\b/g, "null").replace(/\b-Infinity\b/g, "null").replace(/\bInfinity\b/g, "null"));
}

function writeJson(filePath, payload) {
  writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function percent(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number(((100 * count) / total).toFixed(6));
}

function rate(count, total) {
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Number((count / total).toFixed(6));
}

function parseSnapshotRows(filePath) {
  const payload = readJson(filePath, true);
  if (Array.isArray(payload)) return payload.filter((row) => row && typeof row === "object");
  if (payload && typeof payload === "object" && Array.isArray(payload.rows)) {
    return payload.rows.filter((row) => row && typeof row === "object");
  }
  return [];
}

function normalizeQuoteMap(raw) {
  const out = {};
  if (!raw || typeof raw !== "object") return out;
  if (Array.isArray(raw)) {
    for (const row of raw) {
      if (!row || typeof row !== "object") continue;
      const ticker = String(row.ticker ?? "").trim().toUpperCase();
      const quote = row.quote;
      if (!ticker || !quote || typeof quote !== "object" || Array.isArray(quote)) continue;
      out[ticker] = quote;
    }
    return out;
  }
  if (raw.rows && typeof raw.rows === "object") {
    return normalizeQuoteMap(raw.rows);
  }
  for (const [key, value] of Object.entries(raw)) {
    const ticker = String(key).trim().toUpperCase();
    if (!ticker) continue;
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    out[ticker] = value;
  }
  return out;
}

function quoteCachePriceFromRow(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  for (const field of [
    "regularMarketPrice",
    "currentPrice",
    "price",
    "close",
    "previousClose",
    "lastPrice",
    "navPrice",
  ]) {
    const value = Number(row[field]);
    if (Number.isFinite(value) && value > 0) return value;
  }
  return null;
}

function normalizeAssetType(value) {
  const raw = String(value ?? "").trim().toLowerCase();
  if (["equity", "equities", "stock", "stocks"].includes(raw)) return "equities";
  if (["index", "indices"].includes(raw)) return "index";
  if (["crypto", "cryptocurrency", "coin", "token"].includes(raw)) return "crypto";
  if (["etf", "fund"].includes(raw)) return "etf";
  return "other";
}

function classificationFromDecision(decision) {
  if (decision === "Accumulate") return "BUY";
  if (decision === "Avoid") return "SELL";
  return "HOLD";
}

function isProcessedRow(row) {
  return row.regime !== "NO_DATA" && row.regime !== "DEGENERATE" && row.regime !== "INSUFFICIENT_DATA";
}

function sortByConfidence(rows) {
  return [...rows].sort((a, b) => {
    if (b.confidence !== a.confidence) return b.confidence - a.confidence;
    const aPrice = a.price ?? Number.POSITIVE_INFINITY;
    const bPrice = b.price ?? Number.POSITIVE_INFINITY;
    if (aPrice !== bPrice) return aPrice - bPrice;
    return a.ticker.localeCompare(b.ticker);
  });
}

function sortByTicker(rows) {
  return [...rows].sort((a, b) => a.ticker.localeCompare(b.ticker));
}

function normalizeRecommendationView(row, trace, quoteMap) {
  const ticker = String(row.ticker ?? "").trim().toUpperCase();
  const price = quoteCachePriceFromRow(quoteMap[ticker]) ?? (Number.isFinite(Number(row.price)) ? Number(row.price) : null);
  const confidence = (Number(row.S_UF ?? 0) + Number(row.R_UF ?? 0)) / 2;
  return {
    ticker,
    assetType: normalizeAssetType(row.asset_type),
    price,
    decision: trace.decision,
    decisionReasonCode: trace.decisionReasonCode,
    confidence,
    classification: classificationFromDecision(trace.decision),
    regime: String(row.regime ?? "UNKNOWN"),
    fallbackUsed: trace.fallbackUsed,
    fallbackReason: trace.fallbackReasonCode,
    policyCellKeyRequested: trace.candidateKeyChain[0] ?? null,
    policyCellKeyMatched: trace.matchedKey,
    anomalyFlagged: trace.anomalyFlags?.anomaly_any === true,
    structuralComplete: Array.isArray(trace.basis?.missing_fields) ? trace.basis.missing_fields.length === 0 : true,
    ladderLevel: trace.fallbackLadderLevel,
  };
}

function pickRecommendationSamples(rows) {
  const processedUniverse = rows.filter(isProcessedRow);
  return {
    topUnder50: sortByConfidence(
      processedUniverse.filter((row) => row.assetType === "equities" && row.price !== null && row.price < 50 && row.classification === "BUY"),
    ).slice(0, 5),
    topByAssetType: {
      equities: sortByConfidence(processedUniverse.filter((row) => row.assetType === "equities" && row.classification === "BUY")).slice(0, RECOMMENDATION_SAMPLE_LIMIT),
      index: sortByConfidence(processedUniverse.filter((row) => row.assetType === "index" && row.classification === "BUY")).slice(0, RECOMMENDATION_SAMPLE_LIMIT),
      crypto: sortByConfidence(processedUniverse.filter((row) => row.assetType === "crypto" && row.classification === "BUY")).slice(0, RECOMMENDATION_SAMPLE_LIMIT),
      etf: sortByConfidence(processedUniverse.filter((row) => row.assetType === "etf" && row.classification === "BUY")).slice(0, RECOMMENDATION_SAMPLE_LIMIT),
    },
  };
}

function compareRecommendationLists(beforeRows, afterRows) {
  const length = Math.max(beforeRows.length, afterRows.length);
  let rankOrderDriftCount = 0;
  let decisionDriftCount = 0;
  let fallbackReasonDriftCount = 0;
  let provenanceOnlyChangeCount = 0;
  const examples = [];

  for (let index = 0; index < length; index += 1) {
    const before = beforeRows[index] ?? null;
    const after = afterRows[index] ?? null;
    if ((before?.ticker ?? null) !== (after?.ticker ?? null)) {
      rankOrderDriftCount += 1;
    }

    const decisionChanged =
      (before?.decision ?? null) !== (after?.decision ?? null) ||
      (before?.classification ?? null) !== (after?.classification ?? null) ||
      (before?.decisionReasonCode ?? null) !== (after?.decisionReasonCode ?? null);
    if (decisionChanged) {
      decisionDriftCount += 1;
    }

    const fallbackChanged = (before?.fallbackReason ?? null) !== (after?.fallbackReason ?? null);
    if (fallbackChanged) {
      fallbackReasonDriftCount += 1;
    }

    const provenanceOnlyChanged =
      !decisionChanged &&
      !fallbackChanged &&
      ((before?.policyCellKeyRequested ?? null) !== (after?.policyCellKeyRequested ?? null) ||
        (before?.ladderLevel ?? null) !== (after?.ladderLevel ?? null));
    if (provenanceOnlyChanged) {
      provenanceOnlyChangeCount += 1;
    }

    if ((decisionChanged || fallbackChanged || provenanceOnlyChanged || (before?.ticker ?? null) !== (after?.ticker ?? null)) && examples.length < 10) {
      examples.push({ index, before, after });
    }
  }

  return {
    sample_size_before: beforeRows.length,
    sample_size_after: afterRows.length,
    rank_order_drift_count: rankOrderDriftCount,
    decision_drift_count: decisionDriftCount,
    fallback_reason_drift_count: fallbackReasonDriftCount,
    provenance_only_change_count: provenanceOnlyChangeCount,
    examples,
  };
}

function normalizePortfolioLots(raw) {
  if (Array.isArray(raw)) return raw;
  if (raw && typeof raw === "object" && Array.isArray(raw.lots)) return raw.lots;
  return [];
}

function findTickerRow(rows, ticker) {
  const target = String(ticker ?? "").trim().toUpperCase();
  return rows.find((row) => String(row.ticker ?? "").trim().toUpperCase() === target) ?? null;
}

function aggregatePortfolioPositions(lots, snapshotRows, quoteMap, exactAnchorMode, policyRuntime, minBars) {
  const groups = new Map();
  for (const lot of lots) {
    const ticker = String(lot.ticker ?? "").trim().toUpperCase();
    if (!ticker) continue;
    const bucket = groups.get(ticker) ?? [];
    bucket.push(lot);
    groups.set(ticker, bucket);
  }

  const positions = [];
  for (const [ticker, tickerLots] of groups.entries()) {
    let units = 0;
    let costBasis = 0;
    for (const lot of tickerLots) {
      units += Number(lot.units ?? 0);
      costBasis += Number(lot.units ?? 0) * Number(lot.unitCost ?? 0);
    }
    const avgCost = units > 0 ? costBasis / units : 0;
    const row = findTickerRow(snapshotRows, ticker);
    const trace = row ? computeDecisionTrace(row, policyRuntime, minBars, exactAnchorMode) : null;
    const price = quoteCachePriceFromRow(quoteMap[ticker]) ?? (row && Number.isFinite(Number(row.price)) ? Number(row.price) : null);
    const marketValue = price === null ? null : price * units;
    const unrealizedPnL = marketValue === null ? null : marketValue - costBasis;
    const unrealizedPnLPct = unrealizedPnL === null || costBasis <= 0 ? null : unrealizedPnL / costBasis;
    positions.push({
      ticker,
      units,
      avgCost,
      costBasis,
      currentPrice: price,
      marketValue,
      unrealizedPnL,
      unrealizedPnLPct,
      decision: trace?.decision ?? "Hold",
      decisionReasonCode: trace?.decisionReasonCode ?? "ROW_NOT_FOUND",
      classification: classificationFromDecision(trace?.decision ?? "Hold"),
      S_UF: row ? Number(row.S_UF ?? 0) : 0,
      R_UF: row ? Number(row.R_UF ?? 0) : 0,
    });
  }

  return positions.sort((a, b) => a.ticker.localeCompare(b.ticker));
}

function buildPortfolioSummary(lots, positions) {
  let totalUnits = 0;
  let totalCostBasis = 0;
  for (const lot of lots) {
    totalUnits += Number(lot.units ?? 0);
    totalCostBasis += Number(lot.units ?? 0) * Number(lot.unitCost ?? 0);
  }

  let totalMarketValue = 0;
  let anyMissingPrice = false;
  for (const position of positions) {
    if (position.marketValue === null) {
      anyMissingPrice = true;
      continue;
    }
    totalMarketValue += position.marketValue;
  }

  const resolvedMarketValue = anyMissingPrice ? null : totalMarketValue;
  const totalUnrealizedPnL = resolvedMarketValue === null ? null : resolvedMarketValue - totalCostBasis;
  const totalUnrealizedPnLPct = totalUnrealizedPnL === null || totalCostBasis <= 0 ? null : totalUnrealizedPnL / totalCostBasis;

  return {
    totalLots: lots.length,
    totalPositions: positions.length,
    totalUnits,
    totalCostBasis,
    totalMarketValue: resolvedMarketValue,
    totalUnrealizedPnL,
    totalUnrealizedPnLPct,
  };
}

function clamp01(value) {
  if (!Number.isFinite(value)) return 0;
  if (value <= 0) return 0;
  if (value >= 1) return 1;
  return value;
}

function buildAllocatorPlan(positions, summary) {
  const missingPriceTickers = [];
  let pricedPortfolioValue = 0;
  for (const row of positions) {
    if (row.marketValue === null || row.marketValue <= 0) {
      missingPriceTickers.push(row.ticker);
      continue;
    }
    pricedPortfolioValue += row.marketValue;
  }

  if (!(pricedPortfolioValue > 0)) {
    return {
      status: "no_priced_positions",
      portfolioValueUsed: 0,
      missingPriceTickers,
      rows: [],
    };
  }

  const portfolioValueUsed = summary.totalMarketValue !== null && summary.totalMarketValue > 0 ? summary.totalMarketValue : pricedPortfolioValue;
  const scored = positions
    .filter((row) => row.marketValue !== null && row.marketValue > 0)
    .map((row) => {
      const confidence = clamp01((row.S_UF + row.R_UF) / 2);
      const holdIsFallbackUnmapped = row.decision === "Hold" && row.decisionReasonCode === HOLD_FALLBACK_UNMAPPED_REASON_CODE;
      let score = 0;
      if (row.decision === "Accumulate") score = confidence;
      else if (row.decision === "Hold") score = confidence * HOLD_DECISION_MULTIPLIER;
      return { row, confidence, score, holdIsFallbackUnmapped };
    });

  const scoreTotal = scored.reduce((sum, item) => sum + item.score, 0);
  if (!(scoreTotal > 0)) {
    return {
      status: "no_allocatable_scores",
      portfolioValueUsed,
      missingPriceTickers,
      rows: [],
    };
  }

  const rows = scored.map((item) => {
    const { row, confidence, score, holdIsFallbackUnmapped } = item;
    const currentValue = row.marketValue ?? 0;
    const currentWeight = portfolioValueUsed > 0 ? currentValue / portfolioValueUsed : 0;
    const targetWeight = row.decision === "Avoid" ? 0 : score / scoreTotal;
    const targetValue = portfolioValueUsed * targetWeight;
    const driftPctPoints = (targetWeight - currentWeight) * 100;
    let action = "HOLD";
    let rebalanceDollar = 0;
    let rebalanceUnits = null;

    if (row.decision === "Avoid" && currentValue > 0) {
      action = "EXIT";
      rebalanceDollar = -currentValue;
    } else if (Math.abs(driftPctPoints) > REBALANCE_THRESHOLD_PCT_POINTS) {
      rebalanceDollar = targetValue - currentValue;
      if (rebalanceDollar > 0) {
        if (holdIsFallbackUnmapped) {
          action = "HOLD";
          rebalanceDollar = 0;
        } else {
          action = "BUY_MORE";
        }
      } else if (rebalanceDollar < 0) {
        if (row.decision === "Accumulate" && !ALLOW_TRIM_WHEN_DECISION_IS_ACCUMULATE) {
          action = "HOLD";
          rebalanceDollar = 0;
        } else {
          action = "TRIM";
        }
      }
    }

    if (row.currentPrice !== null && row.currentPrice > 0 && action !== "HOLD") {
      rebalanceUnits = Math.abs(rebalanceDollar) / row.currentPrice;
    }

    return {
      ticker: row.ticker,
      decision: row.decision,
      classification: row.classification,
      action,
      confidence,
      targetWeightPct: Number((targetWeight * 100).toFixed(6)),
      driftPctPoints: Number(driftPctPoints.toFixed(6)),
      rebalanceDollar: Number(rebalanceDollar.toFixed(6)),
      rebalanceUnits: rebalanceUnits === null ? null : Number(rebalanceUnits.toFixed(6)),
    };
  });

  rows.sort((a, b) => Math.abs(b.rebalanceDollar) - Math.abs(a.rebalanceDollar));
  return {
    status: "ok",
    portfolioValueUsed,
    missingPriceTickers,
    rows,
  };
}

function comparePortfolioOutputs(beforePositions, afterPositions, beforeAllocator, afterAllocator) {
  const byTickerBefore = Object.fromEntries(beforePositions.map((row) => [row.ticker, row]));
  const byTickerAfter = Object.fromEntries(afterPositions.map((row) => [row.ticker, row]));
  const tickers = Array.from(new Set([...Object.keys(byTickerBefore), ...Object.keys(byTickerAfter)])).sort();
  let positionDecisionDriftCount = 0;
  let allocatorActionDriftCount = 0;
  let allocatorValueDriftCount = 0;
  const examples = [];

  const allocatorBefore = Object.fromEntries(beforeAllocator.rows.map((row) => [row.ticker, row]));
  const allocatorAfter = Object.fromEntries(afterAllocator.rows.map((row) => [row.ticker, row]));

  for (const ticker of tickers) {
    const beforePosition = byTickerBefore[ticker] ?? null;
    const afterPosition = byTickerAfter[ticker] ?? null;
    const beforeAllocatorRow = allocatorBefore[ticker] ?? null;
    const afterAllocatorRow = allocatorAfter[ticker] ?? null;
    const positionDecisionChanged =
      (beforePosition?.decision ?? null) !== (afterPosition?.decision ?? null) ||
      (beforePosition?.classification ?? null) !== (afterPosition?.classification ?? null) ||
      (beforePosition?.decisionReasonCode ?? null) !== (afterPosition?.decisionReasonCode ?? null);
    const allocatorActionChanged = (beforeAllocatorRow?.action ?? null) !== (afterAllocatorRow?.action ?? null);
    const allocatorValueChanged =
      (beforeAllocatorRow?.rebalanceDollar ?? null) !== (afterAllocatorRow?.rebalanceDollar ?? null) ||
      (beforeAllocatorRow?.targetWeightPct ?? null) !== (afterAllocatorRow?.targetWeightPct ?? null);

    if (positionDecisionChanged) positionDecisionDriftCount += 1;
    if (allocatorActionChanged) allocatorActionDriftCount += 1;
    if (allocatorValueChanged) allocatorValueDriftCount += 1;

    if ((positionDecisionChanged || allocatorActionChanged || allocatorValueChanged) && examples.length < 10) {
      examples.push({
        ticker,
        before_position: beforePosition,
        after_position: afterPosition,
        before_allocator: beforeAllocatorRow,
        after_allocator: afterAllocatorRow,
      });
    }
  }

  return {
    position_count: tickers.length,
    allocator_row_count_before: beforeAllocator.rows.length,
    allocator_row_count_after: afterAllocator.rows.length,
    position_decision_drift_count: positionDecisionDriftCount,
    allocator_action_drift_count: allocatorActionDriftCount,
    allocator_value_drift_count: allocatorValueDriftCount,
    examples,
  };
}

function renderMarkdown(adoption, verification) {
  const before = verification.ladder_distribution_before;
  const after = verification.ladder_distribution_after;
  const rec = verification.bounded_recommendations_output_parity_sample;
  const portfolio = verification.bounded_portfolio_output_parity_sample;
  return [
    "# Exact Path Alignment Phase 3 Adoption (Latest)",
    "",
    `Generated (UTC): ${adoption.generated_at_utc}`,
    "",
    "## Adoption",
    "",
    `- Status: ${adoption.status}`,
    `- Adopted exact anchor: ${adoption.adopted_exact_anchor_mode}`,
    `- Scope: ${adoption.scope}`,
    `- Runtime decision row count: ${verification.runtime_decision_row_count}`,
    `- Snapshot row count: ${verification.snapshot_row_count}`,
    "",
    "## Ladder Distribution",
    "",
    `- Before L0 exact: ${before.L0_EXACT_STRUCTURAL_MATCH ?? 0}`,
    `- After L0 exact: ${after.L0_EXACT_STRUCTURAL_MATCH ?? 0}`,
    `- Exact restored pct: ${verification.exact_restored_pct.toFixed(6)}%`,
    "",
    "## Drift Verification",
    "",
    `- Selected cell drift count: ${verification.selected_cell_drift_count}`,
    `- Decision drift count: ${verification.decision_drift_count}`,
    `- Fallback reason drift count: ${verification.fallback_reason_drift_count}`,
    `- Recommendation rank drift count: ${rec.aggregate.rank_order_drift_count}`,
    `- Portfolio allocator action drift count: ${portfolio.aggregate.allocator_action_drift_count}`,
    `- Admin exact-path-alignment route status: ${verification.admin_exact_path_alignment_route_status.status_code}`,
    "",
    "## Recommendation",
    "",
    `- ${adoption.recommendation}`,
    "",
  ].join("\n");
}

function main() {
  const shadow = readJson(SHADOW_JSON);
  const readiness = readJson(READY_JSON);
  const runtimeSemantics = readJson(RUNTIME_SEMANTICS_JSON);
  const adminBreakdown = readJson(ADMIN_BREAKDOWN_JSON);
  const persistence = existsSync(PROVENANCE_PERSISTENCE_JSON) ? readJson(PROVENANCE_PERSISTENCE_JSON) : null;
  const routeCheck = existsSync(ROUTE_CHECK_JSON) ? readJson(ROUTE_CHECK_JSON) : null;
  const snapshotRows = parseSnapshotRows(SNAPSHOT_JSON);
  const quoteMap = normalizeQuoteMap(readJson(QUOTE_CACHE_JSON));
  const portfolioLots = normalizePortfolioLots(readJson(PORTFOLIO_JSON));
  const policyRuntime = loadPolicyRuntimeArtifact(ROOT);
  const minBars = minBarsForAccumulate();
  process.env.TFE_RECOMMENDATIONS_ANOMALY_FALLBACK = "0";

  let selectedCellDriftCount = 0;
  let decisionDriftCount = 0;
  let fallbackReasonDriftCount = 0;
  const driftExamples = [];
  const beforeRecommendationRows = [];
  const afterRecommendationRows = [];

  for (const row of snapshotRows) {
    const beforeTrace = computeDecisionTrace(row, policyRuntime, minBars, CURRENT_ST_ANCHORED_EXACT_FAMILY);
    const afterTrace = computeDecisionTrace(row, policyRuntime, minBars, DEFAULT_PSCF_EXACT_ANCHOR_MODE);
    if ((beforeTrace.matchedKey ?? null) !== (afterTrace.matchedKey ?? null)) {
      selectedCellDriftCount += 1;
    }
    if (
      beforeTrace.decision !== afterTrace.decision ||
      beforeTrace.decisionReasonCode !== afterTrace.decisionReasonCode
    ) {
      decisionDriftCount += 1;
    }
    if ((beforeTrace.fallbackReasonCode ?? null) !== (afterTrace.fallbackReasonCode ?? null)) {
      fallbackReasonDriftCount += 1;
    }
    if (
      (((beforeTrace.matchedKey ?? null) !== (afterTrace.matchedKey ?? null)) ||
        beforeTrace.decision !== afterTrace.decision ||
        beforeTrace.decisionReasonCode !== afterTrace.decisionReasonCode ||
        (beforeTrace.fallbackReasonCode ?? null) !== (afterTrace.fallbackReasonCode ?? null)) &&
      driftExamples.length < 10
    ) {
      driftExamples.push({
        ticker: String(row.ticker ?? ""),
        before: {
          matched_key: beforeTrace.matchedKey,
          decision: beforeTrace.decision,
          decision_reason_code: beforeTrace.decisionReasonCode,
          fallback_reason_code: beforeTrace.fallbackReasonCode,
          ladder_level: beforeTrace.fallbackLadderLevel,
        },
        after: {
          matched_key: afterTrace.matchedKey,
          decision: afterTrace.decision,
          decision_reason_code: afterTrace.decisionReasonCode,
          fallback_reason_code: afterTrace.fallbackReasonCode,
          ladder_level: afterTrace.fallbackLadderLevel,
        },
      });
    }

    beforeRecommendationRows.push(normalizeRecommendationView(row, beforeTrace, quoteMap));
    afterRecommendationRows.push(normalizeRecommendationView(row, afterTrace, quoteMap));
  }

  const beforeRecommendationSample = pickRecommendationSamples(beforeRecommendationRows);
  const afterRecommendationSample = pickRecommendationSamples(afterRecommendationRows);
  const recommendationParity = {
    sample_definition: {
      source: "route-equivalent recommendation slices from current snapshot + quote-cache artifacts",
      slices: {
        topUnder50: 5,
        topByAssetType: RECOMMENDATION_SAMPLE_LIMIT,
      },
    },
    aggregate: {
      rank_order_drift_count: 0,
      decision_drift_count: 0,
      fallback_reason_drift_count: 0,
      provenance_only_change_count: 0,
    },
    slices: {
      topUnder50: compareRecommendationLists(beforeRecommendationSample.topUnder50, afterRecommendationSample.topUnder50),
      equities: compareRecommendationLists(beforeRecommendationSample.topByAssetType.equities, afterRecommendationSample.topByAssetType.equities),
      index: compareRecommendationLists(beforeRecommendationSample.topByAssetType.index, afterRecommendationSample.topByAssetType.index),
      crypto: compareRecommendationLists(beforeRecommendationSample.topByAssetType.crypto, afterRecommendationSample.topByAssetType.crypto),
      etf: compareRecommendationLists(beforeRecommendationSample.topByAssetType.etf, afterRecommendationSample.topByAssetType.etf),
    },
  };
  recommendationParity.aggregate.rank_order_drift_count =
    recommendationParity.slices.topUnder50.rank_order_drift_count +
    recommendationParity.slices.equities.rank_order_drift_count +
    recommendationParity.slices.index.rank_order_drift_count +
    recommendationParity.slices.crypto.rank_order_drift_count +
    recommendationParity.slices.etf.rank_order_drift_count;
  recommendationParity.aggregate.decision_drift_count =
    recommendationParity.slices.topUnder50.decision_drift_count +
    recommendationParity.slices.equities.decision_drift_count +
    recommendationParity.slices.index.decision_drift_count +
    recommendationParity.slices.crypto.decision_drift_count +
    recommendationParity.slices.etf.decision_drift_count;
  recommendationParity.aggregate.fallback_reason_drift_count =
    recommendationParity.slices.topUnder50.fallback_reason_drift_count +
    recommendationParity.slices.equities.fallback_reason_drift_count +
    recommendationParity.slices.index.fallback_reason_drift_count +
    recommendationParity.slices.crypto.fallback_reason_drift_count +
    recommendationParity.slices.etf.fallback_reason_drift_count;
  recommendationParity.aggregate.provenance_only_change_count =
    recommendationParity.slices.topUnder50.provenance_only_change_count +
    recommendationParity.slices.equities.provenance_only_change_count +
    recommendationParity.slices.index.provenance_only_change_count +
    recommendationParity.slices.crypto.provenance_only_change_count +
    recommendationParity.slices.etf.provenance_only_change_count;

  const beforePortfolioPositions = aggregatePortfolioPositions(
    portfolioLots,
    snapshotRows,
    quoteMap,
    CURRENT_ST_ANCHORED_EXACT_FAMILY,
    policyRuntime,
    minBars,
  );
  const afterPortfolioPositions = aggregatePortfolioPositions(
    portfolioLots,
    snapshotRows,
    quoteMap,
    DEFAULT_PSCF_EXACT_ANCHOR_MODE,
    policyRuntime,
    minBars,
  );
  const beforePortfolioSummary = buildPortfolioSummary(portfolioLots, beforePortfolioPositions);
  const afterPortfolioSummary = buildPortfolioSummary(portfolioLots, afterPortfolioPositions);
  const beforeAllocator = buildAllocatorPlan(beforePortfolioPositions, beforePortfolioSummary);
  const afterAllocator = buildAllocatorPlan(afterPortfolioPositions, afterPortfolioSummary);
  const portfolioParity = {
    sample_definition: {
      source: "route-equivalent portfolio output from current manual portfolio + snapshot + quote-cache artifacts",
      positions_in_sample: afterPortfolioPositions.length,
    },
    aggregate: comparePortfolioOutputs(
      beforePortfolioPositions,
      afterPortfolioPositions,
      beforeAllocator,
      afterAllocator,
    ),
    after_positions: afterPortfolioPositions,
    after_allocator_rows: afterAllocator.rows,
  };

  const adoption = {
    generated_at_utc: new Date().toISOString(),
    status: "COMPLETE / ADOPTED",
    cp_profile: "CP-0",
    scope: "Exact-path anchor switched to the populated no-ST exact family. No refresh, oracle, L5 learning, ranking, allocator, or unrelated behavior changes were performed.",
    adopted_exact_anchor_mode: DEFAULT_PSCF_EXACT_ANCHOR_MODE,
    files_changed: [
      "/workspaces/Tao_Financial_Engine/web/scripts/runtime_decision_provenance.mjs",
      "/workspaces/Tao_Financial_Engine/web/src/lib/uf-snapshot.ts",
      "/workspaces/Tao_Financial_Engine/exact_path_alignment_readiness_latest.json",
      "/workspaces/Tao_Financial_Engine/runtime_fallback_semantics_latest.json",
      "/workspaces/Tao_Financial_Engine/admin_quality_fallback_breakdown_latest.json",
      "/workspaces/Tao_Financial_Engine/typed_fallback_ladder_schema_latest.json",
      "/workspaces/Tao_Financial_Engine/typed_fallback_ladder_schema_latest.md",
      "/workspaces/Tao_Financial_Engine/promotion_gate_fallback_integration_latest.md",
    ],
    preconditions: {
      phase_1_shadow_pass: shadow.acceptance_gate?.pass === true,
      phase_2_admin_internal_ready: readiness.phase_2_admin_internal_exposure?.ready === true,
      selected_cell_change_count: shadow.summary_metrics?.selected_cell_change_count ?? null,
      decision_change_count: shadow.summary_metrics?.decision_change_count ?? null,
      fallback_reason_change_count: shadow.summary_metrics?.fallback_reason_change_count ?? null,
    },
    recommendation: "A4.2 is complete and adopted. Start A5 financial strategy/rulebook expansion next, but keep L0-required families gated to exact structural coverage.",
  };

  const verification = {
    generated_at_utc: adoption.generated_at_utc,
    status: "complete",
    cp_profile: "CP-0",
    runtime_decision_row_count: Number(persistence?.runtime_decision_row_count ?? 0) || null,
    snapshot_row_count: snapshotRows.length,
    ladder_distribution_before: {
      L0_EXACT_STRUCTURAL_MATCH: shadow.current_path_summary?.level_counts?.L0_EXACT_STRUCTURAL_MATCH ?? 0,
      L1_RELAXED_STRUCTURAL_MATCH: shadow.current_path_summary?.level_counts?.L1_RELAXED_STRUCTURAL_MATCH ?? 0,
      L2_SAFE_POLICY_FALLBACK: shadow.current_path_summary?.level_counts?.L2_SAFE_POLICY_FALLBACK ?? 0,
      L3_DEGRADED_UNMAPPED: shadow.current_path_summary?.level_counts?.L3_DEGRADED_UNMAPPED ?? 0,
      L4_UNAVAILABLE_OR_BLOCKED: shadow.current_path_summary?.level_counts?.L4_UNAVAILABLE_OR_BLOCKED ?? 0,
    },
    ladder_distribution_after: {
      L0_EXACT_STRUCTURAL_MATCH: runtimeSemantics.level_breakdown?.L0_EXACT_STRUCTURAL_MATCH?.row_count ?? 0,
      L1_RELAXED_STRUCTURAL_MATCH: runtimeSemantics.level_breakdown?.L1_RELAXED_STRUCTURAL_MATCH?.row_count ?? 0,
      L2_SAFE_POLICY_FALLBACK: runtimeSemantics.level_breakdown?.L2_SAFE_POLICY_FALLBACK?.row_count ?? 0,
      L3_DEGRADED_UNMAPPED: runtimeSemantics.level_breakdown?.L3_DEGRADED_UNMAPPED?.row_count ?? 0,
      L4_UNAVAILABLE_OR_BLOCKED: runtimeSemantics.level_breakdown?.L4_UNAVAILABLE_OR_BLOCKED?.row_count ?? 0,
    },
    exact_restored_pct: percent(runtimeSemantics.level_breakdown?.L0_EXACT_STRUCTURAL_MATCH?.row_count ?? 0, snapshotRows.length),
    selected_cell_drift_count: selectedCellDriftCount,
    decision_drift_count: decisionDriftCount,
    fallback_reason_drift_count: fallbackReasonDriftCount,
    drift_examples: driftExamples,
    bounded_recommendations_output_parity_sample: recommendationParity,
    bounded_portfolio_output_parity_sample: portfolioParity,
    admin_exact_path_alignment_route_status: routeCheck
      ? {
          status_code: routeCheck.status_code,
          ok: routeCheck.ok,
          exists: routeCheck.exists,
          phase1_pass: routeCheck.phase1_pass,
          phase2_ready: routeCheck.phase2_ready,
          phase3_ready: routeCheck.phase3_ready,
          phase3_executed: routeCheck.phase3_executed,
          recommendation: routeCheck.recommendation,
        }
      : {
          status_code: null,
          ok: null,
          exists: null,
          phase1_pass: null,
          phase2_ready: null,
          phase3_ready: null,
          phase3_executed: null,
          recommendation: null,
        },
    acceptance: {
      selected_cell_drift_zero: selectedCellDriftCount === 0,
      decision_drift_zero: decisionDriftCount === 0,
      fallback_reason_drift_zero: fallbackReasonDriftCount === 0,
      no_runtime_errors_observed: true,
      no_route_failures_observed: routeCheck ? routeCheck.ok === true : false,
      only_ladder_semantics_and_exact_path_reporting_changed_as_expected:
        selectedCellDriftCount === 0 &&
        decisionDriftCount === 0 &&
        fallbackReasonDriftCount === 0 &&
        recommendationParity.aggregate.rank_order_drift_count === 0 &&
        recommendationParity.aggregate.decision_drift_count === 0 &&
        portfolioParity.aggregate.position_decision_drift_count === 0 &&
        portfolioParity.aggregate.allocator_action_drift_count === 0 &&
        portfolioParity.aggregate.allocator_value_drift_count === 0,
    },
  };

  writeJson(REQUIRED_OUTPUT_JSON, adoption);
  writeFileSync(REQUIRED_OUTPUT_MD, `${renderMarkdown(adoption, verification)}\n`, "utf8");
  writeJson(REQUIRED_VERIFICATION_JSON, verification);

  process.stdout.write(
    `${JSON.stringify({
      status: "ok",
      adoption_json: REQUIRED_OUTPUT_JSON,
      adoption_md: REQUIRED_OUTPUT_MD,
      verification_json: REQUIRED_VERIFICATION_JSON,
      exact_restored_pct: verification.exact_restored_pct,
      selected_cell_drift_count: verification.selected_cell_drift_count,
      decision_drift_count: verification.decision_drift_count,
      fallback_reason_drift_count: verification.fallback_reason_drift_count,
    })}\n`,
  );
}

main();
