/**
 * Tests for the CH3 full-universe candidate pool (chunkSymbols):
 *   1. Chunking splits a big universe into URL-safe batches
 *   2. Remainders and small inputs behave
 *   3. No ticker is lost or duplicated across batches
 *
 * Context: the old pool query was LIMIT 100 with no ORDER BY — the hunter
 * scored ~100 of 2,118 eligible tickers (alphabetically biased; every entry
 * ever taken was an A-name). The pool is now the full universe, fetched in
 * batches.
 *
 * Run: node web/scripts/execution/tests/ch3_pool_test.mjs
 */

process.env.PGHOST ??= "localhost";
process.env.PGDATABASE ??= "test";
process.env.PGUSER ??= "test";
process.env.PGPASSWORD ??= "test";

const { chunkSymbols, CH3_SNAPSHOT_BATCH_SIZE } = await import("../ch3_scalp_strategist.mjs");

let passed = 0;
let failed = 0;

function assert(condition, label) {
  if (condition) { console.log(`  ✓ ${label}`); passed++; }
  else { console.error(`  ✗ FAIL: ${label}`); failed++; }
}

const universe = Array.from({ length: 2118 }, (_, i) => `T${String(i).padStart(4, "0")}`);

console.log("\n1. Batch sizing");
const batches = chunkSymbols(universe);
assert(batches.length === Math.ceil(2118 / CH3_SNAPSHOT_BATCH_SIZE),
  `2118 tickers → ${batches.length} batches of ≤${CH3_SNAPSHOT_BATCH_SIZE}`);
assert(batches.every(b => b.length <= CH3_SNAPSHOT_BATCH_SIZE), "no batch exceeds the size limit");
assert(batches[batches.length - 1].length === 2118 % CH3_SNAPSHOT_BATCH_SIZE || 2118 % CH3_SNAPSHOT_BATCH_SIZE === 0,
  "remainder batch carries the tail");

console.log("\n2. Small inputs");
assert(chunkSymbols([]).length === 0, "empty universe → no batches");
assert(chunkSymbols(["AAPL"]).length === 1 && chunkSymbols(["AAPL"])[0][0] === "AAPL", "single ticker survives");
assert(chunkSymbols(["A", "B", "C"], 2).map(b => b.join("")).join("|") === "AB|C", "custom size splits correctly");

console.log("\n3. Nothing lost, nothing duplicated");
const flat = batches.flat();
assert(flat.length === universe.length, "flattened batches equal universe size");
assert(new Set(flat).size === universe.length, "no duplicates across batches");
assert(flat[0] === "T0000" && flat[flat.length - 1] === "T2117", "order preserved end to end");

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
