/**
 * Tests for sentinel bug fixes:
 *   1. Orphan adoption loop — recently-killed tickers must not be re-adopted
 *   2. EXIT-F outside market hours — catastrophic floor must not fire when market closed
 *   3. Premature phantom cleanup — submitted orders need grace period before declaring phantom
 *
 * Run: node web/scripts/execution/tests/sentinel_bugs_test.mjs
 */

import {
  recentlyKilledTickers,
  markRecentlyKilled,
  isRecentlyKilled,
  isMarketHoursForExitF,
  shouldPhantomCleanup,
} from "../sentinel_monitor.mjs";

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

// ═══════════════════════════════════════════════════════════════════════════
// BUG 1: Orphan adoption loop
// ═══════════════════════════════════════════════════════════════════════════
console.log("\n=== BUG 1: Orphan Adoption Loop ===");

// Clear state
recentlyKilledTickers.clear();

// After killing a position, it should be marked
markRecentlyKilled("AM");
assert(isRecentlyKilled("AM") === true, "AM is recently killed immediately after marking");
assert(isRecentlyKilled("FOXA") === false, "FOXA is NOT recently killed (never marked)");

// Case-insensitive check
markRecentlyKilled("bcpc");
assert(isRecentlyKilled("BCPC") === true, "Case-insensitive: bcpc marked, BCPC found");

// Expiry: simulate 16 minutes passing (should expire after 15 min)
{
  recentlyKilledTickers.clear();
  const sixteenMinAgo = Date.now() - 16 * 60 * 1000;
  recentlyKilledTickers.set("OLD", sixteenMinAgo);
  assert(isRecentlyKilled("OLD") === false, "Expired kill (16 min old) is NOT recently killed");
}

// Non-expired: 5 minutes ago should still be active
{
  recentlyKilledTickers.clear();
  const fiveMinAgo = Date.now() - 5 * 60 * 1000;
  recentlyKilledTickers.set("FRESH", fiveMinAgo);
  assert(isRecentlyKilled("FRESH") === true, "Recent kill (5 min old) IS recently killed");
}

// ═══════════════════════════════════════════════════════════════════════════
// BUG 2: EXIT-F outside market hours
// ═══════════════════════════════════════════════════════════════════════════
console.log("\n=== BUG 2: EXIT-F Outside Market Hours ===");

// 14:00 UTC (9:00 AM ET) = market hours
assert(isMarketHoursForExitF(new Date("2026-05-20T14:00:00Z")) === true, "14:00 UTC (market open) → EXIT-F allowed");

// 19:30 UTC (3:30 PM ET) = market hours
assert(isMarketHoursForExitF(new Date("2026-05-20T19:30:00Z")) === true, "19:30 UTC (market hours) → EXIT-F allowed");

// 00:50 UTC = overnight → EXIT-F must NOT run
assert(isMarketHoursForExitF(new Date("2026-05-20T00:50:00Z")) === false, "00:50 UTC (overnight) → EXIT-F BLOCKED");

// 12:00 UTC (pre-market) = too early
assert(isMarketHoursForExitF(new Date("2026-05-20T12:00:00Z")) === false, "12:00 UTC (pre-market) → EXIT-F BLOCKED");

// 21:00 UTC (after hours) = too late
assert(isMarketHoursForExitF(new Date("2026-05-20T21:00:00Z")) === false, "21:00 UTC (after hours) → EXIT-F BLOCKED");

// 13:30 UTC (exactly market open)
assert(isMarketHoursForExitF(new Date("2026-05-20T13:30:00Z")) === true, "13:30 UTC (exactly open) → EXIT-F allowed");

// 20:00 UTC (exactly market close)
assert(isMarketHoursForExitF(new Date("2026-05-20T20:00:00Z")) === true, "20:00 UTC (exactly close) → EXIT-F allowed");

// ═══════════════════════════════════════════════════════════════════════════
// BUG 3: Premature phantom cleanup
// ═══════════════════════════════════════════════════════════════════════════
console.log("\n=== BUG 3: Premature Phantom Cleanup ===");

// Position submitted 5 min ago → too soon to declare phantom
{
  const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
  assert(
    shouldPhantomCleanup({ status: "submitted", created_at: fiveMinAgo, entry_filled_at: null }) === false,
    "5 min old submitted order → NOT phantom (too soon)"
  );
}

// Position submitted 35 min ago → safe to declare phantom
{
  const thirtyFiveMinAgo = new Date(Date.now() - 35 * 60 * 1000).toISOString();
  assert(
    shouldPhantomCleanup({ status: "submitted", created_at: thirtyFiveMinAgo, entry_filled_at: null }) === true,
    "35 min old submitted order → IS phantom (grace period exceeded)"
  );
}

// Position submitted 20 min ago → still within grace period
{
  const twentyMinAgo = new Date(Date.now() - 20 * 60 * 1000).toISOString();
  assert(
    shouldPhantomCleanup({ status: "submitted", created_at: twentyMinAgo, entry_filled_at: null }) === false,
    "20 min old submitted order → NOT phantom (within 30 min grace)"
  );
}

// Position that has entry_filled_at → never phantom
{
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
  assert(
    shouldPhantomCleanup({ status: "submitted", created_at: oneHourAgo, entry_filled_at: oneHourAgo }) === false,
    "Filled position → never phantom regardless of age"
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Summary
// ═══════════════════════════════════════════════════════════════════════════
console.log(`\n=== RESULTS: ${passed} passed, ${failed} failed ===`);
if (failed > 0) {
  process.exit(1);
} else {
  console.log("All tests passed.");
  process.exit(0);
}
