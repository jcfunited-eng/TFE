/**
 * Tests for the CH3 momentum verdict (tradability + rocket ceiling):
 *   1. 2026-07-20 replays — WAI and VACH must be excluded
 *   2. Sane movers (the channel's real prey) still pass
 *   3. Rocket ceiling boundaries
 *   4. Original gates unchanged (green day, up-from-open, rvol, gap-down)
 *
 * Run: node web/scripts/execution/tests/ch3_momentum_verdict_test.mjs
 */

process.env.PGHOST ??= "localhost";
process.env.PGDATABASE ??= "test";
process.env.PGUSER ??= "test";
process.env.PGPASSWORD ??= "test";

const { ch3MomentumVerdict } = await import("../ch3_scalp_strategist.mjs");

let passed = 0;
let failed = 0;

function assert(condition, label) {
  if (condition) { console.log(`  ✓ ${label}`); passed++; }
  else { console.error(`  ✗ FAIL: ${label}`); failed++; }
}

const base = { day_pct: 0.025, momentum_pct: 0.012, rvol: 5.0, gap_pct: 0.012, current_price: 40.0 };

console.log("\n1. 2026-07-20 replays — both dead slots now excluded at selection");
{
  const wai = ch3MomentumVerdict({ day_pct: 0.3856, momentum_pct: 0.0633, rvol: 357.06, gap_pct: 0.3032, current_price: 2.605 });
  assert(wai.passes === false && wai.tooHot === true && wai.subMinPrice === true,
    "WAI (+38.6% day, $2.60) → rocket AND sub-$5, never picked");
  const vach = ch3MomentumVerdict({ day_pct: 0.6936, momentum_pct: 0.0854, rvol: 107.15, gap_pct: 0.5604, current_price: 17.8 });
  assert(vach.passes === false && vach.tooHot === true,
    "VACH (+69.4% day, +56% gap) → rocket, never picked");
}

console.log("\n2. Sane movers still pass");
{
  assert(ch3MomentumVerdict(base).passes === true, "+2.5% day, 5x vol, $40 → HOT");
  const amal = ch3MomentumVerdict({ day_pct: 0.0282, momentum_pct: 0.0116, rvol: 31.53, gap_pct: 0.0165, current_price: 47.4 });
  assert(amal.passes === true, "AMAL-style (+2.8% day, 31x vol) → HOT");
  const acog = ch3MomentumVerdict({ day_pct: 0.0095, momentum_pct: 0.0053, rvol: 62.23, gap_pct: 0.0042, current_price: 12.0 });
  assert(acog.passes === true, "ACOG-style (+0.95% day, 62x vol) → HOT");
}

console.log("\n3. Rocket ceiling boundaries");
{
  assert(ch3MomentumVerdict({ ...base, day_pct: 0.15 }).passes === true, "exactly +15% day → still allowed");
  assert(ch3MomentumVerdict({ ...base, day_pct: 0.151 }).passes === false, "+15.1% day → rocket");
  assert(ch3MomentumVerdict({ ...base, gap_pct: 0.10 }).passes === true, "exactly +10% gap → still allowed");
  assert(ch3MomentumVerdict({ ...base, gap_pct: 0.101 }).passes === false, "+10.1% gap → rocket");
  assert(ch3MomentumVerdict({ ...base, current_price: 5.0 }).passes === true, "$5.00 exactly → allowed");
  assert(ch3MomentumVerdict({ ...base, current_price: 4.99 }).passes === false, "$4.99 → sub-minimum");
}

console.log("\n4. Original gates unchanged");
{
  assert(ch3MomentumVerdict({ ...base, day_pct: -0.001 }).passes === false, "red on the day → COLD");
  assert(ch3MomentumVerdict({ ...base, momentum_pct: -0.001 }).passes === false, "fading from open → COLD");
  assert(ch3MomentumVerdict({ ...base, rvol: 1.4 }).passes === false, "rvol below 1.5 → COLD");
  assert(ch3MomentumVerdict({ ...base, gap_pct: -0.02 }).passes === false, "gap-down -2% → COLD");
}


console.log("\n5. Thin-book guard + bid-based floor (LINK 2026-07-21 replay)");
{
  const link = ch3MomentumVerdict({ day_pct: 0.02, momentum_pct: 0.01, rvol: 8.0, gap_pct: 0.01, current_price: 5.02, bid_price: 4.57, spread_pct: 0.03 });
  assert(link.passes === false && link.subMinPrice === true,
    "LINK replay: stale $5.02 last trade, real bid $4.57 → floor uses BID, excluded");
  const thin = ch3MomentumVerdict({ ...{ day_pct: 0.025, momentum_pct: 0.012, rvol: 5.0, gap_pct: 0.012, current_price: 40.0 }, bid_price: 39.5, spread_pct: 0.025 });
  assert(thin.passes === false && thin.tooThin === true, "2.5% spread → too thin to scalp");
  const tight = ch3MomentumVerdict({ day_pct: 0.025, momentum_pct: 0.012, rvol: 5.0, gap_pct: 0.012, current_price: 40.0, bid_price: 39.96, spread_pct: 0.002 });
  assert(tight.passes === true, "0.2% spread, bid $39.96 → passes");
  const noquote = ch3MomentumVerdict({ day_pct: 0.025, momentum_pct: 0.012, rvol: 5.0, gap_pct: 0.012, current_price: 40.0, bid_price: null, spread_pct: null });
  assert(noquote.passes === true, "no quote data → falls back to last trade, passes");
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
