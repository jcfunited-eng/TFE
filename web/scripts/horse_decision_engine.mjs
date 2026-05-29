/**
 * Horse Decision Engine — pure nearest-neighbor tuple distance.
 *
 * Reads the 7-dim kernel tuple (D_k, M_k, B_k, R_rev_k, U_star_k, C_k, P_k)
 * from historical snapshot rows, computes per-stock-normalized Euclidean
 * distance to find 30 nearest neighbors, and returns neighbor win rate.
 *
 * Entry: neighbor_wr >= ENTRY_THRESHOLD  → "Accumulate"
 * Exit:  neighbor_wr <  EXIT_THRESHOLD   → "Avoid"
 * Otherwise:                              → "Hold"
 *
 * No ML. No heuristics. Pure numpy-equivalent JS math on the coupled tuple.
 */

// ── Config ──────────────────────────────────────────────────────────
const N_NEIGHBORS = 30;
const FORWARD_DAYS = 20;
const ENTRY_THRESHOLD = parseFloat(process.env.TFE_HORSE_ENTRY_THRESHOLD ?? "0.65");
const EXIT_THRESHOLD = 0.40;

// Both lowercase (DB columns) and camelCase (snapshot JSON) variants
const TUPLE_FIELDS = ["d_k", "m_k", "b_k", "r_rev_k", "u_star_k", "c_k", "p_k"];
const TUPLE_FIELDS_ALT = ["D_k", "M_k", "B_k", "R_rev_k", "U_star_k", "C_k", "P_k"];
const N_DIM = TUPLE_FIELDS.length;

/**
 * Extract the 7-dim tuple from a snapshot row (JSON from runtime_decisions_history).
 * Returns null if any field is missing.
 */
function extractTuple(snap) {
  const vals = [];
  for (let i = 0; i < TUPLE_FIELDS.length; i++) {
    const v = snap[TUPLE_FIELDS[i]] ?? snap[TUPLE_FIELDS_ALT[i]] ?? null;
    if (v === null || v === undefined || isNaN(Number(v))) return null;
    vals.push(Number(v));
  }
  return vals;
}

/**
 * Compute neighbor win rate for a current tuple against historical tuples.
 *
 * @param {number[]} currentTuple - 7-dim array
 * @param {number[][]} historyTuples - array of 7-dim arrays
 * @param {number[]} historyReturns - forward returns for each historical point
 * @returns {number|null} - neighbor win rate, or null if insufficient history
 */
function computeNeighborWR(currentTuple, historyTuples, historyReturns) {
  if (historyTuples.length <= N_NEIGHBORS) return null;

  // Per-stock normalization: range of each field
  const ranges = new Array(N_DIM);
  for (let d = 0; d < N_DIM; d++) {
    let min = Infinity, max = -Infinity;
    for (const t of historyTuples) {
      if (t[d] < min) min = t[d];
      if (t[d] > max) max = t[d];
    }
    ranges[d] = max - min;
    if (ranges[d] < 1e-10) ranges[d] = 1.0;
  }

  // Compute Euclidean distances
  const dists = new Array(historyTuples.length);
  for (let i = 0; i < historyTuples.length; i++) {
    let sumSq = 0;
    for (let d = 0; d < N_DIM; d++) {
      const diff = (historyTuples[i][d] - currentTuple[d]) / ranges[d];
      sumSq += diff * diff;
    }
    dists[i] = { dist: Math.sqrt(sumSq), ret: historyReturns[i] };
  }

  // Partial sort: find N_NEIGHBORS closest
  dists.sort((a, b) => a.dist - b.dist);
  const neighbors = dists.slice(0, N_NEIGHBORS);

  // Win rate = fraction with positive forward return
  let wins = 0;
  for (const n of neighbors) {
    if (n.ret > 0) wins++;
  }

  return wins / N_NEIGHBORS;
}

/**
 * Compute horse decision for a single ticker.
 *
 * @param {object} currentSnap - Current kernel snapshot row (from this refresh)
 * @param {object[]} historyRows - Past snapshot rows from runtime_decisions_history
 *   Each must have: snapshot_row_json (parsed), generated_at_utc, and a forward price
 * @param {object} priceHistory - Map of date string → close price for this ticker
 * @returns {{ decision: string, neighborWR: number|null, historySize: number, reason: string }}
 */
export function computeHorseDecision(currentSnap, historyRows, priceHistory) {
  const currentTuple = extractTuple(currentSnap);
  if (!currentTuple) {
    return { decision: "Avoid", neighborWR: null, historySize: 0, reason: "HORSE_MISSING_FIELDS" };
  }

  // Build historical tuples and forward returns
  const historyTuples = [];
  const historyReturns = [];

  for (const row of historyRows) {
    const snap = typeof row.snapshot_row_json === "string"
      ? JSON.parse(row.snapshot_row_json)
      : row.snapshot_row_json;

    const tuple = extractTuple(snap);
    if (!tuple) continue;

    // Get the date of this historical point
    const dateStr = String(row.generated_at_utc ?? "").slice(0, 10);
    if (!dateStr) continue;

    // Get close price on this date and FORWARD_DAYS later
    const entryPrice = priceHistory[dateStr] ?? snap.price;
    if (!entryPrice || entryPrice <= 0) continue;

    // Find price ~FORWARD_DAYS later
    const dates = Object.keys(priceHistory).sort();
    const dateIdx = dates.indexOf(dateStr);
    if (dateIdx < 0) continue;
    const fwdIdx = dateIdx + FORWARD_DAYS;
    if (fwdIdx >= dates.length) continue;

    const exitPrice = priceHistory[dates[fwdIdx]];
    if (!exitPrice || exitPrice <= 0) continue;

    const fwdReturn = (exitPrice - entryPrice) / entryPrice;
    historyTuples.push(tuple);
    historyReturns.push(fwdReturn);
  }

  const wr = computeNeighborWR(currentTuple, historyTuples, historyReturns);

  if (wr === null) {
    return {
      decision: "Hold",
      neighborWR: null,
      historySize: historyTuples.length,
      reason: "HORSE_INSUFFICIENT_HISTORY",
    };
  }

  let decision, reason;
  if (wr >= ENTRY_THRESHOLD) {
    decision = "Accumulate";
    reason = `HORSE_ACCUMULATE_WR_${(wr * 100).toFixed(0)}`;
  } else if (wr < EXIT_THRESHOLD) {
    decision = "Avoid";
    reason = `HORSE_AVOID_WR_${(wr * 100).toFixed(0)}`;
  } else {
    decision = "Hold";
    reason = `HORSE_HOLD_WR_${(wr * 100).toFixed(0)}`;
  }

  return { decision, neighborWR: wr, historySize: historyTuples.length, reason };
}

/**
 * Check if horse decision engine is enabled.
 */
export function isHorseEnabled() {
  return (process.env.TFE_DECISION_ENGINE ?? "V3").toUpperCase() === "HORSE";
}

/**
 * Check if horse shadow mode is enabled (log horse decisions alongside V3).
 */
export function isHorseShadowEnabled() {
  return (process.env.TFE_DECISION_ENGINE ?? "V3").toUpperCase() === "HORSE_SHADOW";
}

export const HORSE_CONFIG = {
  N_NEIGHBORS,
  FORWARD_DAYS,
  ENTRY_THRESHOLD,
  EXIT_THRESHOLD,
  TUPLE_FIELDS,
};
