/**
 * Retired randomized order-slicing bridge.
 *
 * Randomized execution is incompatible with deterministic TFE custody and the
 * supervised sentinel is the sole order origin. The exports remain as explicit
 * refusals so stale imports cannot submit broker orders.
 */

export const STEALTH_RETIREMENT_REASON =
  "randomized_stealth_execution_retired_use_supervised_sentinel";

export async function executeStealthOrder() {
  return {
    ok: false,
    rejected: true,
    reason: STEALTH_RETIREMENT_REASON,
    orders_submitted: 0,
  };
}

export async function closeStealthPool() {
  return undefined;
}
