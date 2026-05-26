/**
 * Tests for market holiday calendar.
 * Run: node web/scripts/execution/tests/market_calendar_test.mjs
 */

import { isMarketHoliday, isTradingDay, getHolidayName } from "../market_calendar.mjs";

let passed = 0;
let failed = 0;

function assert(condition, label) {
  if (condition) { console.log(`  ✓ ${label}`); passed++; }
  else { console.error(`  ✗ FAIL: ${label}`); failed++; }
}

console.log("\n=== Market Holiday Calendar ===");

// Memorial Day 2026 — the one that bit us
assert(isMarketHoliday(new Date("2026-05-25T14:00:00Z")) === true, "Memorial Day 2026 (May 25) IS a holiday");
assert(isTradingDay(new Date("2026-05-25T14:00:00Z")) === false, "Memorial Day 2026 is NOT a trading day");
assert(getHolidayName(new Date("2026-05-25T14:00:00Z")) === "Memorial Day", "Holiday name: Memorial Day");

// Normal Tuesday
assert(isMarketHoliday(new Date("2026-05-26T14:00:00Z")) === false, "May 26 2026 (Tue) is NOT a holiday");
assert(isTradingDay(new Date("2026-05-26T14:00:00Z")) === true, "May 26 2026 (Tue) IS a trading day");

// Christmas 2026
assert(isMarketHoliday(new Date("2026-12-25T14:00:00Z")) === true, "Christmas 2026 IS a holiday");

// Independence Day observed 2026 (July 4 is Saturday → observed Friday July 3)
assert(isMarketHoliday(new Date("2026-07-03T14:00:00Z")) === true, "July 3 2026 (Independence Day observed) IS a holiday");
assert(isMarketHoliday(new Date("2026-07-04T14:00:00Z")) === false, "July 4 2026 (Saturday, actual) is NOT in holiday list (it's a weekend)");

// Weekend — not a holiday but not a trading day
assert(isMarketHoliday(new Date("2026-05-23T14:00:00Z")) === false, "Saturday May 23 is NOT a holiday");
assert(isTradingDay(new Date("2026-05-23T14:00:00Z")) === false, "Saturday May 23 is NOT a trading day");

// Labor Day 2026
assert(isMarketHoliday(new Date("2026-09-07T14:00:00Z")) === true, "Labor Day 2026 IS a holiday");

// Thanksgiving 2026
assert(isMarketHoliday(new Date("2026-11-26T14:00:00Z")) === true, "Thanksgiving 2026 IS a holiday");

// 2027 holidays
assert(isMarketHoliday(new Date("2027-05-31T14:00:00Z")) === true, "Memorial Day 2027 IS a holiday");
assert(isMarketHoliday(new Date("2027-07-05T14:00:00Z")) === true, "July 5 2027 (Independence Day observed) IS a holiday");

console.log(`\n=== RESULTS: ${passed} passed, ${failed} failed ===`);
if (failed > 0) process.exit(1);
else { console.log("All tests passed."); process.exit(0); }
