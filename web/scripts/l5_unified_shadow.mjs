/**
 * L5 Unified Shadow Engine — shadows all five L5 components alongside production.
 *
 * Components (all shadow-only until individually promoted):
 * 1. ENTRY: Horse tuple-proximity + 3WA high-confidence layer
 * 2. SIZING: Graduated by signal confidence (3WA / horse >= 0.70 / horse 0.65-0.70)
 * 3. EPOCH GOVERNANCE: Sector pressure block + upheaval sizing reduction
 * 4. EXIT ASSESSMENT: Tuple-distance CUT/HOLD in -2% to -10% zone
 * 5. REGIME EXPOSURE: SPY D_k gates on position count and cash buffer
 *
 * Feature flags (env vars):
 *   TFE_L5_ENTRY_MODE       = "SHADOW" | "ACTIVE" | "OFF" (default: SHADOW)
 *   TFE_L5_SIZING_MODE      = "SHADOW" | "ACTIVE" | "OFF" (default: SHADOW)
 *   TFE_L5_EPOCH_MODE       = "SHADOW" | "ACTIVE" | "OFF" (default: SHADOW)
 *   TFE_L5_EXIT_MODE        = "SHADOW" | "ACTIVE" | "OFF" (default: SHADOW)
 *   TFE_L5_REGIME_MODE      = "SHADOW" | "ACTIVE" | "OFF" (default: SHADOW)
 */

import { readFileSync } from "node:fs";
import { computeHorseDecision, HORSE_CONFIG } from "./horse_decision_engine.mjs";

// ── Feature Flags ───────────────────────────────────────────────────
function mode(envVar) {
  return (process.env[envVar] ?? "SHADOW").toUpperCase();
}

export const L5_MODES = {
  entry:  () => mode("TFE_L5_ENTRY_MODE"),
  sizing: () => mode("TFE_L5_SIZING_MODE"),
  epoch:  () => mode("TFE_L5_EPOCH_MODE"),
  exit:   () => mode("TFE_L5_EXIT_MODE"),
  regime: () => mode("TFE_L5_REGIME_MODE"),
};

// ── Constants ───────────────────────────────────────────────────────
const ENTRY_HORSE_THRESHOLD = 0.65;
const ENTRY_3WA_BAR_MAX = 20;
const ENTRY_3WA_SUF_LOW = 0.954;
const ENTRY_3WA_SUF_HIGH = 0.969;

const SIZING_3WA = 0.035;       // 3.5% for 3WA-aligned
const SIZING_HORSE_HIGH = 0.025; // 2.5% for horse >= 0.70
const SIZING_HORSE_MED = 0.015;  // 1.5% for horse 0.65-0.70
const SIZING_DEFAULT = 0.025;    // Current default

const EPOCH_ADVERSE_THRESHOLD = -0.5;
const EPOCH_UPHEAVAL_SIZING_MULT = 0.5;

const EXIT_LOSS_FLOOR = -0.10;      // Unconditional catastrophic
const EXIT_ASSESSMENT_LOW = -0.02;   // Start assessment zone
const EXIT_ASSESSMENT_HIGH = -0.10;  // End assessment zone (= floor)
const EXIT_CUT_WR = 0.50;           // Horse WR threshold for CUT
const EXIT_HOLD_WR = 0.55;          // Horse WR threshold for HOLD

const REGIME_DEFENSIVE_POSITION_MULT = 0.5;
const REGIME_DEFENSIVE_CASH_MIN = 0.20;

// ── 1. Entry Assessment ─────────────────────────────────────────────

/**
 * Assess entry signal using horse + 3WA layers.
 *
 * @param {object} snap - Current kernel snapshot for this ticker
 * @param {number|null} neighborWR - Pre-computed horse neighbor WR (or null)
 * @param {object} spySnap - SPY's kernel snapshot
 * @returns {{ enter: boolean, layer: string, confidence: string, reason: string }}
 */
export function assessEntry(snap, neighborWR, spySnap) {
  const barCount = Number(snap?.bar_count ?? Infinity);
  const sUf = Number(snap?.S_UF ?? snap?.s_uf ?? NaN);
  const spyDk = Number(spySnap?.D_k ?? spySnap?.d_k ?? NaN);

  // Layer 1: 3WA high-confidence (Wave 1 + Wave 3)
  if (barCount <= ENTRY_3WA_BAR_MAX &&
      sUf >= ENTRY_3WA_SUF_LOW && sUf <= ENTRY_3WA_SUF_HIGH &&
      spyDk === 1) {
    return {
      enter: true,
      layer: "3WA",
      confidence: "HIGH",
      reason: `3WA_WAVE1_WAVE3 bars=${barCount} suf=${sUf.toFixed(3)} spy_dk=1`,
    };
  }

  // Layer 2: Horse tuple-proximity
  if (neighborWR !== null && neighborWR >= ENTRY_HORSE_THRESHOLD) {
    const conf = neighborWR >= 0.70 ? "MEDIUM" : "LOW";
    return {
      enter: true,
      layer: "HORSE",
      confidence: conf,
      reason: `HORSE_WR_${(neighborWR * 100).toFixed(0)} threshold=${ENTRY_HORSE_THRESHOLD}`,
    };
  }

  return {
    enter: false,
    layer: "NONE",
    confidence: "NONE",
    reason: neighborWR !== null
      ? `WR_${(neighborWR * 100).toFixed(0)}_BELOW_THRESHOLD`
      : "NO_HORSE_DATA",
  };
}

// ── 2. Position Sizing ──────────────────────────────────────────────

/**
 * Compute position size based on entry confidence and epoch state.
 *
 * @param {string} entryLayer - "3WA" | "HORSE"
 * @param {string} confidence - "HIGH" | "MEDIUM" | "LOW"
 * @param {number|null} neighborWR - Horse WR
 * @param {string} epochPhase - "UPHEAVAL" | "TRANSITIONING" | "SETTLED"
 * @returns {{ sizePct: number, reason: string }}
 */
export function computeSizing(entryLayer, confidence, neighborWR, epochPhase) {
  let basePct;
  let reason;

  if (entryLayer === "3WA") {
    basePct = SIZING_3WA;
    reason = "3WA_FULL";
  } else if (neighborWR !== null && neighborWR >= 0.70) {
    basePct = SIZING_HORSE_HIGH;
    reason = "HORSE_HIGH";
  } else {
    basePct = SIZING_HORSE_MED;
    reason = "HORSE_MED";
  }

  // Epoch upheaval reduction
  if (epochPhase === "UPHEAVAL") {
    basePct *= EPOCH_UPHEAVAL_SIZING_MULT;
    reason += "_UPHEAVAL_HALVED";
  }

  return { sizePct: basePct, reason };
}

// ── 3. Epoch Governance ─────────────────────────────────────────────

/**
 * Check epoch governance for a sector.
 *
 * @returns {{ blocked: boolean, phase: string, sectorPressure: number, reason: string }}
 */
export function checkEpochGovernance(sector) {
  let g32 = {};
  try {
    g32 = JSON.parse(readFileSync("/app/g32_state.json", "utf-8"));
  } catch {
    return { blocked: false, phase: "UNKNOWN", sectorPressure: 0, reason: "G32_UNAVAILABLE" };
  }

  // Sector pressure
  const sectorPressures = g32.sector_pressures ?? {};
  const pressure = sectorPressures[sector] ?? 0;
  const blocked = pressure <= EPOCH_ADVERSE_THRESHOLD;

  // Phase from delta
  const deltaMag = g32.xi_delta
    ? Math.sqrt(Object.values(g32.xi_delta).reduce((s, v) => s + v * v, 0))
    : 0;

  let phase;
  if (deltaMag > 0.15) phase = "UPHEAVAL";
  else if (deltaMag > 0.05) phase = "TRANSITIONING";
  else phase = "SETTLED";

  return {
    blocked,
    phase,
    sectorPressure: pressure,
    reason: blocked
      ? `ADVERSE_${sector}_pressure=${pressure.toFixed(2)}`
      : `${phase}_${sector}_pressure=${pressure.toFixed(2)}`,
  };
}

// ── 4. Exit Assessment ──────────────────────────────────────────────

/**
 * Assess whether to CUT or HOLD a position in the -2% to -10% loss zone.
 *
 * @param {number} unrealizedReturn - Current P&L as fraction (e.g., -0.05 = -5%)
 * @param {number|null} neighborWR - Horse WR for current tuple state
 * @returns {{ action: string, reason: string }}
 */
export function assessExit(unrealizedReturn, neighborWR) {
  // Catastrophic floor — unconditional
  if (unrealizedReturn <= EXIT_LOSS_FLOOR) {
    return { action: "CUT_CATASTROPHIC", reason: `FLOOR_${(unrealizedReturn * 100).toFixed(1)}pct` };
  }

  // Only assess in the intermediate zone
  if (unrealizedReturn > EXIT_ASSESSMENT_LOW) {
    return { action: "HOLD_ABOVE_ZONE", reason: "NOT_IN_ASSESSMENT_ZONE" };
  }

  // In the -2% to -10% zone
  if (neighborWR === null) {
    return { action: "HOLD_NO_DATA", reason: "NO_HORSE_DATA_IN_ZONE" };
  }

  if (neighborWR <= EXIT_CUT_WR) {
    return {
      action: "CUT_STRUCTURAL",
      reason: `WR_${(neighborWR * 100).toFixed(0)}_BELOW_${(EXIT_CUT_WR * 100).toFixed(0)}`,
    };
  }

  if (neighborWR > EXIT_HOLD_WR) {
    return {
      action: "HOLD_STRUCTURAL",
      reason: `WR_${(neighborWR * 100).toFixed(0)}_ABOVE_${(EXIT_HOLD_WR * 100).toFixed(0)}`,
    };
  }

  return { action: "AMBIGUOUS", reason: `WR_${(neighborWR * 100).toFixed(0)}_IN_GRAY_ZONE` };
}

// ── 5. Regime Exposure ──────────────────────────────────────────────

/**
 * Compute regime-adjusted parameters based on SPY D_k.
 *
 * @param {number} spyDk - SPY's directional indicator
 * @param {number} currentPositionCount - Number of open positions
 * @param {number} maxPositions - Normal max positions
 * @param {number} cashPct - Current cash percentage
 * @returns {{ maxPositions: number, cashMinPct: number, newEntriesAllowed: boolean, reason: string }}
 */
export function computeRegimeExposure(spyDk, currentPositionCount, maxPositions, cashPct) {
  if (spyDk === -1) {
    const adjustedMax = Math.floor(maxPositions * REGIME_DEFENSIVE_POSITION_MULT);
    const newEntries = currentPositionCount < adjustedMax;
    return {
      maxPositions: adjustedMax,
      cashMinPct: REGIME_DEFENSIVE_CASH_MIN,
      newEntriesAllowed: newEntries,
      reason: `SPY_DK_NEG1_DEFENSIVE max=${adjustedMax} cash_min=20%`,
    };
  }

  return {
    maxPositions,
    cashMinPct: 0,
    newEntriesAllowed: true,
    reason: `SPY_DK_${spyDk}_NORMAL`,
  };
}

// ── Shadow Logger ───────────────────────────────────────────────────

/**
 * Run all L5 components in shadow mode and log results.
 *
 * @param {object} params
 * @param {string} params.ticker
 * @param {object} params.snap - Current kernel snapshot
 * @param {number|null} params.neighborWR - Horse WR
 * @param {object} params.spySnap - SPY kernel snapshot
 * @param {string} params.sector
 * @param {number|null} params.unrealizedReturn - If position is open
 * @param {number} params.currentPositionCount
 * @param {number} params.maxPositions
 * @param {number} params.cashPct
 * @param {string} params.currentDecision - What production is currently doing
 */
export function shadowLog(params) {
  const {
    ticker, snap, neighborWR, spySnap, sector,
    unrealizedReturn, currentPositionCount, maxPositions,
    cashPct, currentDecision,
  } = params;

  const entry = assessEntry(snap, neighborWR, spySnap);
  const sizing = entry.enter
    ? computeSizing(entry.layer, entry.confidence, neighborWR,
        checkEpochGovernance(sector).phase)
    : { sizePct: 0, reason: "NO_ENTRY" };
  const epoch = checkEpochGovernance(sector);
  const regime = computeRegimeExposure(
    Number(spySnap?.D_k ?? spySnap?.d_k ?? 0),
    currentPositionCount, maxPositions, cashPct
  );

  let exitAssessment = null;
  if (unrealizedReturn !== null && unrealizedReturn !== undefined) {
    exitAssessment = assessExit(unrealizedReturn, neighborWR);
  }

  // Build shadow line
  const parts = [
    `[L5-SHADOW] ${ticker}`,
    `prod=${currentDecision}`,
    `entry=${entry.enter ? entry.layer : "NO"}(${entry.reason})`,
    `size=${(sizing.sizePct * 100).toFixed(1)}%(${sizing.reason})`,
    `epoch=${epoch.blocked ? "BLOCKED" : epoch.phase}(${epoch.reason})`,
    `regime=${regime.reason}`,
  ];

  if (exitAssessment) {
    parts.push(`exit=${exitAssessment.action}(${exitAssessment.reason})`);
  }

  // Final decision: would L5 unified override production?
  let l5Decision = currentDecision;
  if (entry.enter && !epoch.blocked && regime.newEntriesAllowed) {
    l5Decision = "Accumulate";
  } else if (epoch.blocked) {
    l5Decision = "Avoid";
  } else if (!entry.enter) {
    l5Decision = neighborWR !== null && neighborWR < 0.40 ? "Avoid" : "Hold";
  }

  const override = l5Decision !== currentDecision;
  parts.push(`l5=${l5Decision}${override ? " OVERRIDE" : ""}`);

  console.log(parts.join(" | "));

  return {
    ticker,
    entry,
    sizing,
    epoch,
    regime,
    exitAssessment,
    l5Decision,
    currentDecision,
    override,
  };
}
