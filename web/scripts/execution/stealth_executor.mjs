/**
 * Retired queued stealth executor.
 *
 * Pending randomized slices are not an authorized TFE execution mechanism.
 * This compatibility entry point performs no broker or database mutation.
 */

export const STEALTH_EXECUTOR_RETIREMENT_REASON =
  "queued_stealth_execution_retired_use_supervised_sentinel";

export async function runStealthExecutor() {
  return {
    disabled: true,
    reason: STEALTH_EXECUTOR_RETIREMENT_REASON,
    orders_submitted: 0,
  };
}

export async function closeStealthExecutorPool() {
  return undefined;
}

if (process.argv[1]?.endsWith("stealth_executor.mjs")) {
  const result = await runStealthExecutor();
  console.error(`[STEALTH] ${result.reason}; no broker or ledger mutation performed.`);
}
