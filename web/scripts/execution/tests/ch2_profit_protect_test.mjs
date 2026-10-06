/**
 * Tests for the CH2 profit-protect floor (free-fall guard):
 *   0. APOG 2026-10-06 — Joe's order: a +20% winner never slides below +15%
 *   1. UTZ 2026-07-21 replay — +90% peak ratchets a +67.7% floor
 *   2. Never engages below +20% (EXIT-A's winner-capping sin stays dead;
 *      engage lowered 25→20 on Joe's order 2026-08-13)
 *   3. Floor ratchets up with the peak, never down
 *   4. Garbage inputs never fire
 *
 * Run: node web/scripts/execution/tests/ch2_profit_protect_test.mjs
 */

import { profitProtectFloor, ch2RaisedStop, PROFIT_PROTECT_ENGAGE, PROFIT_PROTECT_GIVEBACK } from "../sentinel_monitor.mjs";

let passed = 0;
let failed = 0;

function assert(condition, label) {
  if (condition) { console.log(`  ✓ ${label}`); passed++; }
  else { console.error(`  ✗ FAIL: ${label}`); failed++; }
}

console.log("\n0. APOG — Joe 2026-10-06: +20% must keep +15%");
{
  assert(PROFIT_PROTECT_GIVEBACK === 1 / 4, "giveback pinned at a quarter of the peak gain (Joe, 2026-10-06)");
  const f = profitProtectFloor(35.08, 35.08 * 1.20);
  assert(f !== null && Math.abs(f - 35.08 * 1.15) < 1e-9, `entry $35.08, peak +20% → floor $${f?.toFixed(2)} = +15%`);
  const up = ch2RaisedStop(35.08, 42.15, 28.06);
  assert(up !== null && up >= 40.34 && up < 42.15, `standing stop $28.06 raised to $${up} (≥ +15%, below price)`);
  assert(ch2RaisedStop(35.08, 42.15, up) === null, "already at the lock → no change");
  assert(ch2RaisedStop(35.08, 42.15, 41.50) === null, "a higher stop is never lowered");
  assert(ch2RaisedStop(35.08, 40.00, 28.06) === null, "+14% peak → lock not armed, brake untouched");
  assert(ch2RaisedStop(0, 42.15, 28.06) === null, "bad entry → no change");
}

console.log("\n1. UTZ replay — the gain that started this");
{
  const floor = profitProtectFloor(7.40, 14.08);
  assert(floor !== null && Math.abs(floor - 12.41) < 0.02,
    `entry $7.40, peak $14.08 (+90.3%) → floor ≈ $12.41 / +67.7% (got ${floor?.toFixed(2)})`);
  assert(floor > 7.40 * 1.5, "floor locks in well over +50%");
}

console.log("\n2. Never engages below +20%");
{
  assert(profitProtectFloor(100, 110) === null, "+10% → not engaged");
  assert(profitProtectFloor(100, 119.9) === null, "+19.9% → not engaged");
  const atEngage = profitProtectFloor(100, 120.01);
  assert(atEngage !== null && Math.abs(atEngage - (100 * (1 + 0.2001 * (1 - PROFIT_PROTECT_GIVEBACK)))) < 1e-6,
    `just over +20% → engaged, floor at three-quarters of the gain`);
  assert(PROFIT_PROTECT_ENGAGE === 0.20, "engage threshold pinned at +20% (Joe, 2026-08-13)");
}

console.log("\n3. Floor ratchets with the peak");
{
  const f30 = profitProtectFloor(10, 13);
  const f50 = profitProtectFloor(10, 15);
  const f90 = profitProtectFloor(10, 19);
  assert(f30 < f50 && f50 < f90, "higher peak → higher floor, monotonic");
  assert(Math.abs(f50 - 13.75) < 0.001, "+50% peak → floor +37.5% (keeps 3/4 of the gain)");
  assert(f90 > 16.7 && f90 < 16.8, "+90% peak → floor ≈ +67.5%");
}

console.log("\n4. Garbage never fires");
{
  assert(profitProtectFloor(0, 14) === null, "zero entry → null");
  assert(profitProtectFloor(10, 9) === null, "peak below entry → null");
  assert(profitProtectFloor(10, 10) === null, "peak equals entry → null");
  assert(profitProtectFloor(NaN, 14) === null, "NaN entry → null");
  assert(profitProtectFloor(10, NaN) === null, "NaN peak → null");
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
