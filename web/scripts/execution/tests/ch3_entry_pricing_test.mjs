/**
 * Tests for CH3 slippage-capped entry pricing (computeCh3EntryPrices):
 *   1. Limit price caps the fill at quote × 1.003
 *   2. Brackets anchor to the limit (worst-case fill), not the quote
 *   3. AMAL 2026-07-16 regression — a +1.27% slippage fill can no longer
 *      compress the take-profit distance (old anchoring gave +0.23% TP
 *      against a -2.24% stop on a +1.5%/-1% design)
 *   4. Designed TP/SL distances survive across the tradable price range
 *
 * Run: node web/scripts/execution/tests/ch3_entry_pricing_test.mjs
 */

process.env.APCA_API_KEY_ID    ??= "test";
process.env.APCA_API_SECRET_KEY ??= "test";
process.env.PGHOST     ??= "localhost";
process.env.PGDATABASE ??= "test";
process.env.PGUSER     ??= "test";
process.env.PGPASSWORD ??= "test";

const { computeCh3EntryPrices } = await import("../alpaca_bridge.mjs");

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

const TP_PCT = 0.015;
const SL_PCT = 0.01;

// ── 1. Limit caps the fill ──────────────────────────────────────────────
console.log("\n1. Limit price caps slippage at 0.3%");
{
  const { limitPrice } = computeCh3EntryPrices(100.0, TP_PCT, SL_PCT);
  assert(limitPrice === 100.3, `quote 100.00 → limit 100.30 (got ${limitPrice})`);
}

// ── 2. Brackets anchor to the limit, not the quote ──────────────────────
console.log("\n2. Brackets anchor to worst-case fill");
{
  const { limitPrice, takeProfitPrice, stopLossPrice } = computeCh3EntryPrices(100.0, TP_PCT, SL_PCT);
  assert(Math.abs(takeProfitPrice - limitPrice * (1 + TP_PCT)) < 0.005 + 1e-9,
    `TP ${takeProfitPrice} = limit × 1.015`);
  assert(Math.abs(stopLossPrice - limitPrice * (1 - SL_PCT)) < 0.005 + 1e-9,
    `SL ${stopLossPrice} = limit × 0.99`);
}

// ── 3. AMAL regression ──────────────────────────────────────────────────
console.log("\n3. AMAL 2026-07-16 regression — slippage cannot eat the target");
{
  // AMAL: quote 47.16 at submit; market order filled 47.76 (+1.27%).
  // Old anchoring: TP 47.87 → +0.23% from fill; SL 46.69 → -2.24% from fill.
  const quote = 47.16;
  const { limitPrice, takeProfitPrice, stopLossPrice } = computeCh3EntryPrices(quote, TP_PCT, SL_PCT);
  assert(limitPrice < 47.76, `a 47.76 fill is refused (limit ${limitPrice})`);
  const effTp = takeProfitPrice / limitPrice - 1;
  const effSl = 1 - stopLossPrice / limitPrice;
  assert(effTp >= TP_PCT - 0.0025, `worst-case effective TP ${(effTp * 100).toFixed(2)}% ≥ ~1.5%`);
  assert(effSl <= SL_PCT + 0.0025, `worst-case effective SL ${(effSl * 100).toFixed(2)}% ≤ ~1%`);
}

// ── 4. Distances survive across the tradable price range ────────────────
console.log("\n4. Designed distances hold from $5 to $1000");
{
  let ok = true;
  for (const quote of [5.0, 7.37, 12.5, 34.98, 47.16, 99.99, 250.0, 512.34, 1000.0]) {
    const { limitPrice, takeProfitPrice, stopLossPrice } = computeCh3EntryPrices(quote, TP_PCT, SL_PCT);
    const effTp = takeProfitPrice / limitPrice - 1;
    const effSl = 1 - stopLossPrice / limitPrice;
    // 0.25% tolerance covers penny rounding at the $5 minimum share price
    if (effTp < TP_PCT - 0.0025 || effSl > SL_PCT + 0.0025 || stopLossPrice <= 0) {
      console.error(`    drift at quote=${quote}: effTp=${effTp} effSl=${effSl}`);
      ok = false;
    }
  }
  assert(ok, "TP ≥ ~1.5% and SL ≤ ~1% at every price point");
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
