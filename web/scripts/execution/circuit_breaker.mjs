/**
 * Retired standalone circuit-breaker entry point.
 *
 * The supervised sentinel owns the active drawdown fuse and position exits.
 * Keeping a second liquidator allowed duplicate market sells and could mark a
 * ledger row closed before the broker confirmed a fill. This module remains
 * only as an explicit compatibility refusal for any stale scheduler or command.
 */

export const CIRCUIT_BREAKER_RETIREMENT_REASON =
  "standalone_circuit_breaker_retired_use_supervised_sentinel";

export async function runCircuitBreaker() {
  return {
    disabled: true,
    reason: CIRCUIT_BREAKER_RETIREMENT_REASON,
    orders_submitted: 0,
  };
}

export async function closeCircuitBreakerPool() {
  return undefined;
}

if (process.argv[1]?.endsWith("circuit_breaker.mjs")) {
  const result = await runCircuitBreaker();
  console.error(`[CB] ${result.reason}; no broker or ledger mutation performed.`);
}
