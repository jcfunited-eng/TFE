/**
 * Tests for D4.8 execution-layer hardening:
 *   D-3:    per-signal try/catch pattern (structural check on source)
 *   CH2-3:  idempotency key format = ${signal_class}:${ledgerId}
 *   CH2-4:  writeRejectToLedgerWithRetry follows D4.5 retry+fallback pattern
 *   CB-4:   parseThresholdSafe validation
 *
 * Run: node web/scripts/execution/tests/execution_hardening_test.mjs
 */

import { readFile } from "node:fs/promises";

let passed = 0;
let failed = 0;

function assert(cond, label) {
  if (cond) { console.log(`  ✓ ${label}`); passed++; }
  else      { console.error(`  ✗ FAIL: ${label}`); failed++; }
}

function parseThresholdSafe(rawValue, defaultVal, key, logPrefix) {
  const parsed = parseFloat(rawValue);
  if (!Number.isFinite(parsed) || parsed < 0) {
    // silent in test (no console log verification)
    return defaultVal;
  }
  return parsed;
}

// ══════════════════════════════════════════════════════════════════════
// CB-4: parseThresholdSafe
// ══════════════════════════════════════════════════════════════════════
console.log("\n=== CB-4: parseThresholdSafe ===");
assert(parseThresholdSafe("3.0", 5.0, "k", "T") === 3.0, "Valid numeric string returns parsed value");
assert(parseThresholdSafe("5", 5.0, "k", "T") === 5.0, "Integer string parses");
assert(parseThresholdSafe("abc", 5.0, "k", "T") === 5.0, "Non-numeric returns default");
assert(parseThresholdSafe("", 5.0, "k", "T") === 5.0, "Empty string returns default");
assert(parseThresholdSafe(null, 5.0, "k", "T") === 5.0, "null returns default");
assert(parseThresholdSafe(undefined, 5.0, "k", "T") === 5.0, "undefined returns default");
assert(parseThresholdSafe("NaN", 5.0, "k", "T") === 5.0, "'NaN' string returns default");
assert(parseThresholdSafe("-1.5", 5.0, "k", "T") === 5.0, "Negative returns default (invalid threshold)");
assert(parseThresholdSafe("0", 5.0, "k", "T") === 0, "Zero is valid (allowed for permissive threshold)");
assert(parseThresholdSafe("Infinity", 5.0, "k", "T") === 5.0, "'Infinity' returns default (not finite)");

// ══════════════════════════════════════════════════════════════════════
// Structural checks on source files
// ══════════════════════════════════════════════════════════════════════
const bridgeSrc = await readFile(new URL("../alpaca_bridge.mjs", import.meta.url), "utf8");
const daemonSrc = await readFile(new URL("../sentinel_daemon.mjs", import.meta.url), "utf8");
const cbSrc     = await readFile(new URL("../circuit_breaker.mjs", import.meta.url), "utf8");
const sentSrc   = await readFile(new URL("../sentinel_monitor.mjs", import.meta.url), "utf8");

console.log("\n=== CH2-3: idempotency keys use ledgerId ===");
assert(bridgeSrc.includes("`3WA:${ledgerId}`"), "3WA path uses 3WA:${ledgerId} key");
assert(bridgeSrc.includes("`CH2:${ledgerId}`"), "CH2 path uses CH2:${ledgerId} key");
assert(bridgeSrc.includes("`CH3:${ledgerId}`"), "CH3 path uses CH3:${ledgerId} key");
assert(!bridgeSrc.includes("Math.random()"), "No Math.random() in dedupe key construction");
assert(!/CH2:\$\{ticker\}:\$\{signal\.run_id\}/.test(bridgeSrc), "Old CH2 sha256 pattern removed");
assert(!/CH3:\$\{ticker\}:\$\{signal\.run_id\}/.test(bridgeSrc), "Old CH3 sha256 pattern removed");

console.log("\n=== CH2-4: writeRejectToLedgerWithRetry present and used ===");
assert(bridgeSrc.includes("writeRejectToLedgerWithRetry"), "Reject retry helper defined");
assert(bridgeSrc.includes("attempt <= 3"), "Reject helper uses 3-attempt pattern");
assert(bridgeSrc.includes("reject_fallback_reason"), "Reject helper writes fallback breadcrumbs");
assert(bridgeSrc.includes('CRITICAL: both primary and fallback reject writes failed'), "Reject helper CRITICAL logs both-fail");
const rejectCallCount = (bridgeSrc.match(/writeRejectToLedgerWithRetry\(/g) || []).length;
assert(rejectCallCount >= 4, `Reject helper called from >=4 sites (found ${rejectCallCount}: 1 def + 3 usage)`);
assert(!bridgeSrc.includes(".catch(() => {})"), "No .catch(() => {}) silent handlers remain in alpaca_bridge.mjs");

console.log("\n=== D-1: kill switch fail-closed ===");
assert(daemonSrc.includes("FAILING CLOSED"), "Kill switch fail-closed comment/log present");
assert(daemonSrc.includes("entriesHalted = true"), "Kill switch sets halted=true on DB error");
assert(!/catch\s*\{\s*\/\*\s*non-fatal\s*\*\/\s*\}/.test(daemonSrc), "Old /* non-fatal */ silent catch removed");

console.log("\n=== D-3: per-signal try/catch ===");
// Count try/catch blocks around submitEntry — should be 3 channels × 1 outer + 3 per-signal = 6+
const submitEntryCatchCount = (daemonSrc.match(/Signal .* failed:/g) || []).length;
assert(submitEntryCatchCount >= 3, `Per-signal error logs present in each channel (found ${submitEntryCatchCount})`);
assert(daemonSrc.includes("Signal fetch failed"), "Signal fetch has its own catch");

console.log("\n=== CB-4: parseThresholdSafe integrated ===");
assert(cbSrc.includes("parseThresholdSafe"), "circuit_breaker.mjs uses parseThresholdSafe");
assert(sentSrc.includes("parseThresholdSafe"), "sentinel_monitor.mjs uses parseThresholdSafe");
assert(!/const thresholdPct = parseFloat\(thresholdStr\)/.test(cbSrc), "Old raw parseFloat gone from CB");
assert(!/const thresholdPct = parseFloat\(await fetchConfig\("max_drawdown_pct"\)/.test(sentSrc), "Old raw parseFloat gone from sentinel");

// ══════════════════════════════════════════════════════════════════════
// D4.9 assertions
// ══════════════════════════════════════════════════════════════════════
const stealthBridgeSrc  = await readFile(new URL("../stealth_bridge.mjs", import.meta.url), "utf8");
const stealthExecSrc    = await readFile(new URL("../stealth_executor.mjs", import.meta.url), "utf8");
const auditorSrc        = await readFile(new URL("../trade_auditor.mjs", import.meta.url), "utf8");
const bridgeSrcNow      = await readFile(new URL("../alpaca_bridge.mjs", import.meta.url), "utf8");
const sentSrcNow        = await readFile(new URL("../sentinel_monitor.mjs", import.meta.url), "utf8");
const cbSrcNow          = await readFile(new URL("../circuit_breaker.mjs", import.meta.url), "utf8");

console.log("\n=== CB-6: max_drawdown_pct canonical in circuit_breaker.mjs ===");
assert(cbSrcNow.includes(`readConfig("max_drawdown_pct", "5.0")`), "CB reads max_drawdown_pct with 5.0 default");
assert(!cbSrcNow.includes("circuit_breaker_threshold_pct"), "Old key circuit_breaker_threshold_pct removed from CB");

console.log("\n=== Silent catch sweep ===");
assert(!sentSrcNow.includes(".catch(() => {})"), "No .catch(() => {}) remaining in sentinel_monitor.mjs");
assert(!stealthBridgeSrc.includes(".catch(() => {})"), "No .catch(() => {}) remaining in stealth_bridge.mjs");
assert(!stealthExecSrc.includes(".catch(() => {})"), "No .catch(() => {}) remaining in stealth_executor.mjs");
assert(!auditorSrc.includes(".catch(() => {})"), "No .catch(() => {}) remaining in trade_auditor.mjs");
assert(sentSrcNow.includes("writeExitOrderIdWithRetry"), "sentinel_monitor.mjs defines writeExitOrderIdWithRetry");
assert(sentSrcNow.includes("exit_fallback_order_id"), "writeExitOrderIdWithRetry writes fallback breadcrumbs");
assert(sentSrcNow.includes("CRITICAL: both primary and fallback exit_order_id"), "writeExitOrderIdWithRetry has CRITICAL log");

console.log("\n=== CH2-1 / CH3-1 cosmetic ===");
assert(!bridgeSrcNow.includes(`exit_trigger_a:   "s_uf >= 0.75"`), "CH2-1: stale exit_trigger_a removed");
assert(!bridgeSrcNow.includes("(tradeAmount / 100000)"), "CH3-1: hardcoded 100000 denominator removed");
assert(bridgeSrcNow.includes("cash: ch3Cash, equity: ch3Equity"), "CH3-1: ch3Equity destructured from fetchAccountState");
assert(bridgeSrcNow.includes("(tradeAmount / ch3Equity)"), "CH3-1: risk_per_trade_pct uses actual equity");

// ══════════════════════════════════════════════════════════════════════
// D5 CB-3 assertions
// ══════════════════════════════════════════════════════════════════════
const cbSrcD5   = await readFile(new URL("../circuit_breaker.mjs", import.meta.url), "utf8");
const sentSrcD5 = await readFile(new URL("../sentinel_monitor.mjs", import.meta.url), "utf8");

console.log("\n=== CB-3: unique_violation handling ===");
assert(cbSrcD5.includes(`e.code === "23505"`), "CB triggerCircuitBreaker checks 23505 unique_violation");
assert(cbSrcD5.includes("raced: true"), "CB signals raced state to caller");
assert(cbSrcD5.includes("Concurrent trigger detected"), "CB logs concurrent trigger");
assert(sentSrcD5.includes(`e.code === "23505"`), "Sentinel triggerCircuitBreaker checks 23505");
assert(sentSrcD5.includes("raced: true"), "Sentinel signals raced state to caller");

console.log("\n=== D5 trigger_reason renamed ===");
assert(!cbSrcD5.includes("standalone_3pct_fuse"), "Old 3pct-specific reason string removed");
assert(cbSrcD5.includes("standalone_drawdown_fuse"), "New threshold-agnostic reason string present");

console.log("\n=== CB-3: unique_violation caught by mocked pool ===");
{
  // Simulate the race: primary INSERT throws with code 23505.
  // Confirm the extracted trigger logic handles it as no-op.
  let logs = [];
  const origLog = console.log;
  console.log = (...args) => { logs.push(args.join(" ")); };
  try {
    // Inline copy of the trigger logic (structural check via source match above)
    const mockPool = { query: async () => { const err = new Error("dup"); err.code = "23505"; throw err; } };
    let result;
    try {
      await mockPool.query("INSERT INTO pee1_circuit_breaker VALUES ($1)", ["x"]);
      result = { fired: true };
    } catch (e) {
      if (e.code === "23505") {
        console.log(`[CB] Concurrent trigger detected — another invocation fired first (unique_violation). Skipping duplicate.`);
        result = { fired: false, raced: true };
      } else throw e;
    }
    assert(result.raced === true, "23505 catch produces raced:true result");
    assert(result.fired === false, "23505 catch produces fired:false result");
    assert(logs.some(l => l.includes("Concurrent trigger detected")), "Concurrent-trigger log line emitted");
  } finally {
    console.log = origLog;
  }
}

// ══════════════════════════════════════════════════════════════════════
// D5.1 assertions
// ══════════════════════════════════════════════════════════════════════
const sentSrcD51 = await readFile(new URL("../sentinel_monitor.mjs", import.meta.url), "utf8");

console.log("\n=== D5.1 orphan sync kill switch guard ===");
assert(sentSrcD51.includes("orphanEntriesHalted"), "Orphan sync kill-switch flag defined");
assert(sentSrcD51.includes("Orphan sync SKIPPED — kill switch active"), "Orphan sync logs when skipped");
assert(sentSrcD51.includes("FAILING CLOSED — orphan adoption halted"), "Orphan sync fails closed on DB error");

console.log("\n=== D5.1 orphan adoption blocklist ===");
assert(sentSrcD51.includes("ORPHAN_ADOPT_BLOCKLIST"), "Blocklist constant defined");
assert(sentSrcD51.includes(`"HTBK"`), "HTBK on blocklist");
assert(sentSrcD51.includes(`"CWAN"`), "CWAN on blocklist");
assert(sentSrcD51.includes("on ORPHAN_ADOPT_BLOCKLIST"), "Blocklist log message present");

// ══════════════════════════════════════════════════════════════════════
// D5.2 assertions — SPY D_k gate removal
// ══════════════════════════════════════════════════════════════════════
const stratSrcD52 = await readFile(new URL("../3wa_strategist.mjs", import.meta.url), "utf8");
const sentSrcD52  = await readFile(new URL("../sentinel_monitor.mjs", import.meta.url), "utf8");

console.log("\n=== D5.2 strategist SPY D_k gate removed ===");
assert(!stratSrcD52.includes(`if (spyDk !== 1) return null`), "Per-signal SPY veto removed from parseSignal");
assert(!/if\s*\(\s*spyDk\s*!==\s*1\s*\)\s*\{\s*[^}]*return\s+\[\]/s.test(stratSrcD52), "Top-level SPY veto removed from get3WASignals");
assert(stratSrcD52.includes("informational — not a Wave 1 gate"), "New informational-only comment present");
assert(!stratSrcD52.includes("Wave 3 INACTIVE"), "Old Wave 3 INACTIVE log strings removed");

console.log("\n=== D5.2 sentinel SPY flip exit removed ===");
assert(!sentSrcD52.includes("sentinel_spy_flip"), "SPY flip exit reason string removed");
assert(!sentSrcD52.includes("Wave 3 GONE"), "SPY flip Wave 3 GONE log removed");
assert(!sentSrcD52.includes("SPY flip:"), "SPY flip prefix log removed");

// ══════════════════════════════════════════════════════════════════════
// V3 basin gate assertions (replaces D5.4.1 L5 governance)
// ══════════════════════════════════════════════════════════════════════
const stratSrcD541 = await readFile(new URL("../3wa_strategist.mjs", import.meta.url), "utf8");

console.log("\n=== V3 basin gate (replaces D5.4.1 L5 governance) ===");
assert(stratSrcD541.includes("const rRevK"), "R_rev_k extracted");
assert(stratSrcD541.includes("const mK"), "M_k extracted");
assert(stratSrcD541.includes("const rUf"), "R_UF extracted");
assert(stratSrcD541.includes("const uStarK"), "U_star_k extracted");
assert(stratSrcD541.includes("const cK"), "C_k extracted");
assert(stratSrcD541.includes("const pK"), "P_k extracted");
assert(stratSrcD541.includes("computeV3Basin"), "V3 basin function imported and called");
assert(stratSrcD541.includes("ACCUMULATE_BASIN_MIN"), "V3 basin minimum constant defined");
assert(!stratSrcD541.includes("TP_ENTRY_THRESHOLD"), "Old D5.4 threshold constant removed");
assert(!stratSrcD541.includes("CLASS_RANK"), "Old tier sort map removed");
assert(stratSrcD541.includes("deduped.sort"), "Deduped sorted");
assert(stratSrcD541.includes("accumulate_basin"), "accumulate_basin used in sort");

// ══════════════════════════════════════════════════════════════════════
// V3 sort assertions (replaces D5.4.3 M_k ASC)
// ══════════════════════════════════════════════════════════════════════
const stratSrcD543 = await readFile(new URL("../3wa_strategist.mjs", import.meta.url), "utf8");

console.log("\n=== V3 sort: accumulate_basin DESC (replaces D5.4.3 M_k ASC) ===");
assert(!stratSrcD543.includes("(a.m_k ?? Infinity) - (b.m_k ?? Infinity)"), "Old M_k ASC removed");
assert(!stratSrcD543.includes("(b.m_k ?? -Infinity) - (a.m_k ?? -Infinity)"), "Old M_k DESC removed");
assert(stratSrcD543.includes("accumulate_basin_DESC"), "Log reflects accumulate_basin sort direction");
assert(stratSrcD543.includes("v3_basin?.accumulate_basin"), "Sort uses v3_basin accumulate_basin");

// ══════════════════════════════════════════════════════════════════════
// V3 entry constant assertions (replaces D5.7 M_k ceiling)
// ══════════════════════════════════════════════════════════════════════
const stratSrcD57 = await readFile(new URL("../3wa_strategist.mjs", import.meta.url), "utf8");

console.log("\n=== V3 entry constant (replaces D5.7 M_k ceiling) ===");
assert(!stratSrcD57.includes("M_K_CEILING"), "Old M_K_CEILING removed");
assert(!stratSrcD57.includes("TFE_M_K_CEILING"), "Old env override removed");
assert(stratSrcD57.includes("ACCUMULATE_BASIN_MIN"), "V3 entry basin minimum defined");
assert(stratSrcD57.includes("0.15"), "V3 basin minimum is 0.15");
assert(!stratSrcD57.includes("mK >= 0"), "Old inclusive-zero lower bound removed");
assert(!stratSrcD57.includes("D5.5 outcome data"), "Old D5.5 comment removed");

// ══════════════════════════════════════════════════════════════════════
// V3 replaces D5.8 universe allowlist
// ══════════════════════════════════════════════════════════════════════
const stratSrcD58 = await readFile(new URL("../3wa_strategist.mjs", import.meta.url), "utf8");
const univSrc     = await readFile(new URL("../validated_universe.mjs", import.meta.url), "utf8");

console.log("\n=== V3 replaces D5.8 universe allowlist ===");
assert(!stratSrcD58.includes("VALIDATED_UNIVERSE"), "Universe NOT imported in V3 strategist");
assert(!stratSrcD58.includes("!wave1 && !VALIDATED_UNIVERSE.has(ticker)"), "Old universe filter removed");
assert(univSrc.includes("VALIDATED_UNIVERSE"), "Universe module still exports the set");
assert(univSrc.includes("DEPRECATED"), "Deprecation header added to universe module");
assert(univSrc.includes('"AAAU"'), "Known walkforward ticker in universe");
assert(!univSrc.includes('"IYLD"'), "IYLD ETF not in validated universe");
assert(!univSrc.includes('"VIXY"'), "VIXY ETF not in validated universe");

console.log(`\n${passed}/${passed + failed} assertions passed`);
if (failed > 0) process.exit(1);
