import assert from "node:assert/strict";
import {
  CIRCUIT_BREAKER_RETIREMENT_REASON,
  runCircuitBreaker,
} from "../circuit_breaker.mjs";
import {
  executeStealthOrder,
  STEALTH_RETIREMENT_REASON,
} from "../stealth_bridge.mjs";
import {
  runStealthExecutor,
  STEALTH_EXECUTOR_RETIREMENT_REASON,
} from "../stealth_executor.mjs";

const circuitResult = await runCircuitBreaker();
assert.deepEqual(circuitResult, {
  disabled: true,
  reason: CIRCUIT_BREAKER_RETIREMENT_REASON,
  orders_submitted: 0,
});

const bridgeResult = await executeStealthOrder({ ticker: "PROOF" });
assert.deepEqual(bridgeResult, {
  ok: false,
  rejected: true,
  reason: STEALTH_RETIREMENT_REASON,
  orders_submitted: 0,
});

const executorResult = await runStealthExecutor();
assert.deepEqual(executorResult, {
  disabled: true,
  reason: STEALTH_EXECUTOR_RETIREMENT_REASON,
  orders_submitted: 0,
});

console.log("duplicate execution mechanisms: all retirement assertions passed");
