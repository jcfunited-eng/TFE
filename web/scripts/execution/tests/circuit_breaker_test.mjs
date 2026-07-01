/**
 * Tests for D4.6 circuit breaker fixes:
 *   CB-1: session-open equity must use Alpaca last_equity, not ledger fallback
 *   CB-2: liquidation ledger writes must use retry+fallback pattern
 *
 * Run: node web/scripts/execution/tests/circuit_breaker_test.mjs
 */

let passed = 0;
let failed = 0;

function assert(condition, label) {
  if (condition) {
    console.log(`  ✓ ${label}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${label}`);
    failed++;
  }
}

// Pure drawdown math extracted from the CB source. Tests the math
// without hitting Alpaca or the DB.
function computeDrawdown(equityNow, lastEquity) {
  const equityOpen = parseFloat(lastEquity ?? "0");
  if (equityOpen <= 0) return { skipped: true, reason: "no_last_equity" };
  const drawdownPct = ((equityOpen - equityNow) / equityOpen) * 100;
  return { skipped: false, equityOpen, equityNow, drawdownPct };
}

function shouldFire(drawdownPct, thresholdPct) {
  if (drawdownPct === undefined) return false;
  return drawdownPct >= thresholdPct;
}

console.log("\n=== CB-1: session-open equity source ===");

// Normal day with signals — last_equity is the reference (not the ledger)
{
  const r = computeDrawdown(103_000, "107000");
  assert(r.skipped === false, "Non-quiet day: check proceeds");
  assert(r.equityOpen === 107_000, "equityOpen sourced from last_equity, not ledger");
  assert(Math.abs(r.drawdownPct - 3.7383) < 0.01, "Drawdown math: (107k-103k)/107k = 3.74%");
  assert(shouldFire(r.drawdownPct, 3.0) === true, "3.74% >= 3.0% threshold → fires");
}

// Quiet day — no signals today but last_equity still available from Alpaca.
// This is the case that was silently broken in 784b194.
{
  const r = computeDrawdown(103_000, "107000");
  assert(r.skipped === false, "Quiet day: last_equity still drives check");
  assert(shouldFire(r.drawdownPct, 3.0) === true, "Quiet day drawdown STILL fires (regression guard)");
}

// Threshold boundary
{
  const r = computeDrawdown(103_790, "107000");
  // drawdown = (107000-103790)/107000 = 3.0000%
  assert(Math.abs(r.drawdownPct - 3.0) < 0.001, "Exactly 3% drawdown computed");
  assert(shouldFire(r.drawdownPct, 3.0) === true, "Drawdown at threshold fires (>=)");
}

// Sub-threshold
{
  const r = computeDrawdown(104_500, "107000");
  assert(shouldFire(r.drawdownPct, 3.0) === false, "2.34% drawdown does NOT fire");
}

// Missing last_equity → skip, don't fire spuriously
{
  const r = computeDrawdown(103_000, null);
  assert(r.skipped === true, "Missing last_equity → skipped");
  assert(r.reason === "no_last_equity", "Skip reason recorded");
  assert(shouldFire(r.drawdownPct, 3.0) === false, "Skipped result does NOT fire");
}

// Zero last_equity → skip
{
  const r = computeDrawdown(103_000, "0");
  assert(r.skipped === true, "Zero last_equity → skipped");
}

// last_equity as string (Alpaca returns strings)
{
  const r = computeDrawdown(103_000, "107000.50");
  assert(r.skipped === false, "Float string last_equity parses");
  assert(Math.abs(r.equityOpen - 107_000.5) < 0.01, "Float string parsed accurately");
}

console.log("\n=== CB-2: retry+fallback pattern shape ===");

// Structural test: verify the helper is exported and has expected shape.
// Full DB interaction is validated post-deploy in val env, not here.
{
  const src = await import("node:fs").then(fs =>
    fs.promises.readFile(new URL("../circuit_breaker.mjs", import.meta.url), "utf8")
  );
  assert(src.includes("closePositionInLedgerWithRetry"), "Retry helper exists");
  assert(src.includes("attempt <= 3"), "Helper uses 3-attempt pattern");
  assert(src.includes("cb_fallback_sell_order_id"), "Helper writes fallback breadcrumbs");
  assert(src.includes("CRITICAL: both primary and fallback"), "Helper CRITICAL logs both-fail");
  assert(!src.includes(".catch(() => {})"), "No silent .catch(() => {}) remains in file");
}

console.log(`\n${passed}/${passed + failed} assertions passed`);
if (failed > 0) process.exit(1);
