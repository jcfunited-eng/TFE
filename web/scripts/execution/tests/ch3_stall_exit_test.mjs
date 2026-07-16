/**
 * Tests for the CH3 same-day stall exit (shouldCh3StallExit):
 *   1. AD 2026-07-16 replay — dead 5.2h at -0.55% must exit
 *   2. Fresh positions are left alone (brackets' job)
 *   3. Winners above the dead zone ride toward their TP
 *   4. Losers below -1% are EXIT-F/stop territory, not stall territory
 *   5. Boundary behavior at exactly 3 hours
 *
 * Run: node web/scripts/execution/tests/ch3_stall_exit_test.mjs
 */

import { shouldCh3StallExit, CH3_STALL_EXIT_HOURS } from "../sentinel_monitor.mjs";

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

const H = 3600 * 1000;
const entry = new Date("2026-07-16T13:48:00Z").getTime();

console.log("\n1. AD replay — dead hold must exit");
assert(shouldCh3StallExit(new Date(entry).toISOString(), -0.0055, entry + 5.2 * H) === true,
  "5.2h at -0.55% → exit");
assert(shouldCh3StallExit(new Date(entry).toISOString(), 0.001, entry + 4 * H) === true,
  "4h at +0.10% → exit");

console.log("\n2. Fresh positions are the brackets' job");
assert(shouldCh3StallExit(new Date(entry).toISOString(), -0.005, entry + 1 * H) === false,
  "1h at -0.50% → hold");
assert(shouldCh3StallExit(new Date(entry).toISOString(), 0.0, entry + 2.9 * H) === false,
  "2.9h flat → hold");

console.log("\n3. Winners ride");
assert(shouldCh3StallExit(new Date(entry).toISOString(), 0.006, entry + 5 * H) === false,
  "5h at +0.60% → hold (TP bracket working)");
assert(shouldCh3StallExit(new Date(entry).toISOString(), 0.012, entry + 5 * H) === false,
  "5h at +1.20% → hold");

console.log("\n4. Deep losers belong to EXIT-F / the stop");
assert(shouldCh3StallExit(new Date(entry).toISOString(), -0.012, entry + 5 * H) === false,
  "5h at -1.20% → not stall territory");

console.log("\n5. Boundary + garbage inputs");
assert(shouldCh3StallExit(new Date(entry).toISOString(), 0.0, entry + CH3_STALL_EXIT_HOURS * H + 1) === true,
  "just past 3h flat → exit");
assert(shouldCh3StallExit(null, 0.0, entry + 5 * H) === false, "no fill time → never");
assert(shouldCh3StallExit(new Date(entry).toISOString(), NaN, entry + 5 * H) === false, "NaN P&L → never");
assert(shouldCh3StallExit("garbage-date", 0.0, entry + 5 * H) === false, "unparseable date → never");

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
