/**
 * Tests for bracket-close fill recovery (bracketCloseFill):
 *   1. FOA 2026-07-23 replay — entry + stop-leg fills recovered from the
 *      nested parent order (the ghost-trade bug: closed with NULL fills)
 *   2. TP-leg exits recover the limit leg's fill
 *   3. No filled leg / missing order → nulls, never garbage
 *
 * Run: node web/scripts/execution/tests/ch3_bracket_fill_test.mjs
 */

import { bracketCloseFill, isStaleCh3Entry, CH3_ENTRY_STALE_MS } from "../sentinel_monitor.mjs";

let passed = 0;
let failed = 0;

function assert(condition, label) {
  if (condition) { console.log(`  ✓ ${label}`); passed++; }
  else { console.error(`  ✗ FAIL: ${label}`); failed++; }
}

console.log("\n1. FOA replay — stop-leg exit");
{
  const foa = {
    filled_avg_price: "23.8", filled_at: "2026-07-23T13:58:28Z",
    legs: [
      { id: "tp-1", type: "limit", status: "canceled", filled_avg_price: null },
      { id: "sl-1", type: "stop", status: "filled", filled_avg_price: "22.812788", filled_at: "2026-07-23T18:01:11Z" },
    ],
  };
  const f = bracketCloseFill(foa);
  assert(f.entry === 23.8, `entry recovered: $${f.entry}`);
  assert(f.exit === 22.812788, `exit recovered from stop leg: $${f.exit}`);
  assert(f.exitOrderId === "sl-1" && f.exitAt === "2026-07-23T18:01:11Z", "exit leg id + timestamp recovered");
  assert(Math.abs(104 * (f.exit - f.entry) - -102.67) < 0.01, "implies FOA P&L ≈ -$102.67");
}

console.log("\n2. TP-leg exit");
{
  const win = {
    filled_avg_price: "30.86", filled_at: "t0",
    legs: [
      { id: "tp-2", type: "limit", status: "filled", filled_avg_price: "31.40", filled_at: "t1" },
      { id: "sl-2", type: "stop", status: "canceled", filled_avg_price: null },
    ],
  };
  const f = bracketCloseFill(win);
  assert(f.exit === 31.40 && f.exitOrderId === "tp-2", "take-profit leg recovered");
}

console.log("\n3. Degenerate inputs");
{
  assert(bracketCloseFill({ filled_avg_price: "10", legs: [{ status: "canceled" }, { status: "expired" }] }).exit === null,
    "no filled leg → exit null");
  const empty = bracketCloseFill(null);
  assert(empty.entry === null && empty.exit === null, "missing order → all nulls");
  assert(bracketCloseFill({ legs: [{ status: "filled", filled_avg_price: "0" }] }).exit === null,
    "zero-price fill → null, never garbage");
}


console.log("\n4. Stale-entry cancel (FOA knife-catcher replay)");
{
  const sub = new Date("2026-07-23T13:47:30Z").getTime();
  assert(isStaleCh3Entry("2026-07-23T13:47:30Z", sub + 11 * 60000) === true, "resting 11 min (FOA) → stale, cancel");
  assert(isStaleCh3Entry("2026-07-23T13:47:30Z", sub + 2 * 60000) === false, "2 min → still live");
  assert(isStaleCh3Entry("2026-07-23T13:47:30Z", sub + CH3_ENTRY_STALE_MS + 1000) === true, "just past threshold → stale");
  assert(isStaleCh3Entry(null) === false && isStaleCh3Entry("garbage") === false, "missing/garbage timestamps → never cancel");
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
