/**
 * Tests for the CH3 stop re-anchor (reanchoredStopPrice):
 *   1. 2026-07-21/22 replays — AFRI's above-fill stop and EOLS's at-fill
 *      stop both re-anchor to a real -1% below the actual fill
 *   2. BLFS-style good fills only ever loosen toward design, never tighten
 *   3. Garbage inputs never produce a price
 *
 * Run: node web/scripts/execution/tests/ch3_stop_reanchor_test.mjs
 */

import { reanchoredStopPrice, CH3_STOP_PCT } from "../sentinel_monitor.mjs";

let passed = 0;
let failed = 0;

function assert(condition, label) {
  if (condition) { console.log(`  ✓ ${label}`); passed++; }
  else { console.error(`  ✗ FAIL: ${label}`); failed++; }
}

console.log("\n1. Replays — the two bad geometries");
{
  const afri = reanchoredStopPrice(11.00);
  assert(afri === 10.89, `AFRI fill $11.00 → stop $10.89 (was $11.02, ABOVE the fill; got ${afri})`);
  const eols = reanchoredStopPrice(5.77);
  assert(eols === 5.71, `EOLS fill $5.77 → stop $5.71 (was $5.77, AT the fill; got ${eols})`);
  assert(afri < 11.00 && eols < 5.77, "re-anchored stops always sit below the fill");
}

console.log("\n2. Good fills keep design distance");
{
  const blfs = reanchoredStopPrice(30.86);
  assert(blfs === 30.55, `BLFS fill $30.86 → stop $30.55 (cap-anchored was $30.60; got ${blfs})`);
  const exact = reanchoredStopPrice(100.0);
  assert(exact === 99.0, "fill $100 → stop $99.00, exactly -1%");
  assert(CH3_STOP_PCT === 0.01, "stop distance pinned at -1%");
}

console.log("\n3. Garbage never fires");
{
  assert(reanchoredStopPrice(0) === null, "zero fill → null");
  assert(reanchoredStopPrice(-5) === null, "negative fill → null");
  assert(reanchoredStopPrice(NaN) === null, "NaN fill → null");
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
