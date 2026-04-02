/**
 * web/scripts/execution/capital_allocator.mjs
 * PEE-1 Capital Allocator
 *
 * Calculates position size: Vault_Equity * (Risk_Per_Trade_Pct / 100)
 * Standard risk: 1.5% per trade.
 * Hard cap: never more than 5% in a single position.
 * If equity is unavailable → fail. No guessing.
 */

const RISK_PCT_DEFAULT = 1.5;
const RISK_PCT_MAX     = 5.0;
const RISK_PCT_MIN     = 0.1;

/**
 * @param {number} vaultEquity  — live account equity in USD
 * @param {number} [riskPct]    — optional override (default 1.5%)
 * @returns {{ dollarAllocation: number, riskPct: number }}
 */
export function allocate(vaultEquity, riskPct = RISK_PCT_DEFAULT) {
  if (!isFinite(vaultEquity) || vaultEquity <= 0) {
    throw new Error(`[ALLOCATOR] vault_equity invalid: ${vaultEquity}`);
  }

  const clampedRisk = Math.min(Math.max(parseFloat(riskPct), RISK_PCT_MIN), RISK_PCT_MAX);
  const dollarAllocation = vaultEquity * (clampedRisk / 100);

  return { dollarAllocation, riskPct: clampedRisk };
}

/**
 * Given dollar allocation and entry price, return integer share count.
 * Returns 0 if the result is less than 1 share — caller must reject.
 */
export function sharesFromAllocation(dollarAllocation, entryPrice) {
  if (!isFinite(entryPrice) || entryPrice <= 0) {
    throw new Error(`[ALLOCATOR] entry_price invalid: ${entryPrice}`);
  }
  return Math.floor(dollarAllocation / entryPrice);
}
