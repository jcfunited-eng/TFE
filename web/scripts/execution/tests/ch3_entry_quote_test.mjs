/**
 * Tests for CH3 live-ask entry anchoring (resolveCh3EntryQuote):
 *   1. OSPN 2026-07-27 regression — a stale IEX last trade below the live
 *      book can no longer anchor the entry (trade 15.12 vs book 15.49/15.60
 *      put the marketable limit 2.8% under the ask; 4 straight CH3 entries
 *      7/24–7/27 died unfilled in the stale-entry cancel)
 *   2. Junk-quote guard — an ask >10% above the last print is refused
 *   3. Fallbacks — missing ask uses trade; missing both resolves to null
 *   4. End-to-end with computeCh3EntryPrices — the OSPN limit clears the ask
 *
 * Run: node web/scripts/execution/tests/ch3_entry_quote_test.mjs
 */

process.env.APCA_API_KEY_ID     ??= "test";
process.env.APCA_API_SECRET_KEY ??= "test";
process.env.PGHOST     ??= "localhost";
process.env.PGDATABASE ??= "test";
process.env.PGUSER     ??= "test";
process.env.PGPASSWORD ??= "test";

const { resolveCh3EntryQuote, computeCh3EntryPrices } = await import("../alpaca_bridge.mjs");

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

// ── 1. OSPN regression — live ask beats stale trade ─────────────────────
console.log("\n1. OSPN 2026-07-27 regression — stale trade cannot anchor entry");
{
  const { quote, source } = resolveCh3EntryQuote({ trade: 15.12, ask: 15.60 });
  assert(quote === 15.60, `anchor is the live ask 15.60 (got ${quote})`);
  assert(source === "ask", `source is "ask" (got ${source})`);
}

// ── 2. Junk-quote guard ─────────────────────────────────────────────────
console.log("\n2. Ask >10% above last print is refused as junk");
{
  const { quote, source } = resolveCh3EntryQuote({ trade: 15.12, ask: 17.00 });
  assert(quote === 15.12, `falls back to trade 15.12 (got ${quote})`);
  assert(source === "trade", `source is "trade" (got ${source})`);
  const edge = resolveCh3EntryQuote({ trade: 100.0, ask: 110.0 });
  assert(edge.quote === 110.0 && edge.source === "ask",
    `exactly +10% is still accepted (got ${edge.quote}/${edge.source})`);
}

// ── 3. Fallbacks ────────────────────────────────────────────────────────
console.log("\n3. Degradation ladder");
{
  const noAsk = resolveCh3EntryQuote({ trade: 15.12, ask: null });
  assert(noAsk.quote === 15.12 && noAsk.source === "trade",
    `no ask → trade (got ${noAsk.quote}/${noAsk.source})`);
  const noTrade = resolveCh3EntryQuote({ trade: null, ask: 15.60 });
  assert(noTrade.quote === 15.60 && noTrade.source === "ask",
    `no trade → ask, no sanity bound possible (got ${noTrade.quote}/${noTrade.source})`);
  const neither = resolveCh3EntryQuote({ trade: null, ask: null });
  assert(neither.quote === null && neither.source === "none",
    `neither → null (got ${neither.quote}/${neither.source})`);
  const zeros = resolveCh3EntryQuote({ trade: 0, ask: -1 });
  assert(zeros.quote === null, `zero/negative inputs → null (got ${zeros.quote})`);
}

// ── 4. End-to-end: the OSPN order is now marketable ─────────────────────
console.log("\n4. OSPN end-to-end — limit clears the ask it must cross");
{
  const { quote } = resolveCh3EntryQuote({ trade: 15.12, ask: 15.60 });
  const { limitPrice } = computeCh3EntryPrices(quote, 0.015, 0.01);
  assert(limitPrice >= 15.60, `limit ${limitPrice} ≥ ask 15.60 — order can fill immediately`);
  // The old path, for contrast: anchoring to the stale trade rested below the book
  const { limitPrice: oldLimit } = computeCh3EntryPrices(15.12, 0.015, 0.01);
  assert(oldLimit < 15.49, `old anchoring (${oldLimit}) sat below even the bid — the bug this fixes`);
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
