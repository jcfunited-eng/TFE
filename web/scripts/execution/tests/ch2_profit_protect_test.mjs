/**
 * Tests for the CH2 profit-protect floor (free-fall guard):
 *   1. UTZ 2026-07-21 replay — +90% peak ratchets a +60% floor
 *   2. Never engages below +20% (EXIT-A's winner-capping sin stays dead;
 *      engage lowered 25→20 on Joe's order 2026-08-13)
 *   3. Floor ratchets up with the peak, never down
 *   4. Garbage inputs never fire
 *
 * Run: node web/scripts/execution/tests/ch2_profit_protect_test.mjs
 */

import { profitProtectFloor, PROFIT_PROTECT_ENGAGE, PROFIT_PROTECT_GIVEBACK } from "../sentinel_monitor.mjs";

let passed = 0;
let failed = 0;

function assert(condition, label) {
  if (condition) { console.log(`  ✓ ${label}`); passed++; }
  else { console.error(`  ✗ FAIL: ${label}`); failed++; }
}

console.log("\n1. UTZ replay — the gain that started this");
{
  const floor = profitProtectFloor(7.40, 14.08);
  assert(floor !== null && Math.abs(floor - 11.85) < 0.02,
    `entry $7.40, peak $14.08 (+90.3%) → floor ≈ $11.85 / +60.2% (got ${floor?.toFixed(2)})`);
  assert(12.0 > floor, "price $12 (the manual stop) sits above the ratchet floor — stop fires first");
  assert(profitProtectFloor(7.40, 14.08) > 7.40 * 1.5, "floor locks in well over +50%");
}

console.log("\n2. Never engages below +20%");
{
  assert(profitProtectFloor(100, 110) === null, "+10% → not engaged");
  assert(profitProtectFloor(100, 119.9) === null, "+19.9% → not engaged");
  const atEngage = profitProtectFloor(100, 120.01);
  assert(atEngage !== null && Math.abs(atEngage - (100 * (1 + 0.2001 * (1 - PROFIT_PROTECT_GIVEBACK)))) < 1e-6,
    `just over +20% → engaged, floor at two-thirds of the gain`);
  assert(PROFIT_PROTECT_ENGAGE === 0.20, "engage threshold pinned at +20% (Joe, 2026-08-13)");
}

console.log("\n3. Floor ratchets with the peak");
{
  const f30 = profitProtectFloor(10, 13);
  const f50 = profitProtectFloor(10, 15);
  const f90 = profitProtectFloor(10, 19);
  assert(f30 < f50 && f50 < f90, "higher peak → higher floor, monotonic");
  assert(Math.abs(f50 - 13.3333) < 0.001, "+50% peak → floor +33.3% (keeps 2/3 of the gain)");
  assert(f90 > 15.9 && f90 < 16.1, "+90% peak → floor ≈ +60%");
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
