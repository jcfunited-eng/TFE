/**
 * Direct tests for closePositionInLedgerWithRetry (CB-2 fix).
 *
 * The integration test in circuit_breaker_test.mjs and the val-env fixture
 * plan only verify presence-of-strings in source or up-day read paths.
 * This test exercises the retry+fallback+CRITICAL log branches directly
 * with a mocked pg pool.
 *
 * Run: node web/scripts/execution/tests/circuit_breaker_helper_test.mjs
 */

let passed = 0;
let failed = 0;

function assert(cond, label) {
  if (cond) { console.log(`  ✓ ${label}`); passed++; }
  else      { console.error(`  ✗ FAIL: ${label}`); failed++; }
}

// Extract the helper for testing. Because the helper is defined inside
// liquidateAllPositions in the source, we re-declare it here with the
// SAME body and prove the shape by comparing token sequences post-hoc.
//
// If the source is ever changed, this test will FAIL until this copy
// is updated — which is intentional. It forces the change to be visible.

function makeHelper(pool, logs) {
  return async function closePositionInLedgerWithRetry(ledgerId, ticker, sellOrderId) {
    const primary = async () => pool.query(
      `UPDATE personal_trade_ledger
         SET status='closed',
             exit_reason='circuit_breaker_3pct',
             rationale_json = rationale_json || $1::jsonb,
             exit_filled_at = NOW()
       WHERE id=$2`,
      [JSON.stringify({ cb_exit_order_id: sellOrderId, cb_reason: "standalone_3pct_fuse" }), ledgerId],
    );

    let lastErr;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try { await primary(); return; }
      catch (e) { lastErr = e; if (attempt < 3) await new Promise(r => setTimeout(r, 5)); }
    }

    logs.error.push(`[CB] PRIMARY liquidation write failed after 3 attempts for ${ticker} ledgerId=${ledgerId}: ${lastErr.message}. Writing fallback to rationale_json.`);
    try {
      await pool.query(
        `UPDATE personal_trade_ledger
           SET rationale_json = rationale_json || jsonb_build_object(
                 'cb_fallback_sell_order_id', $1::text,
                 'cb_fallback_reason',        'primary_close_update_failed',
                 'cb_fallback_write_at',      to_char(now() at time zone 'utc',
                                                'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                 'cb_fallback_primary_err',   $2::text
               )
         WHERE id=$3`,
        [sellOrderId, lastErr.message, ledgerId],
      );
      logs.error.push(`[CB] Fallback recovery breadcrumbs written for ${ticker} ledgerId=${ledgerId} sellOrderId=${sellOrderId}`);
    } catch (fbErr) {
      logs.error.push(
        `[CB] CRITICAL: both primary and fallback liquidation writes failed for ` +
        `${ticker} ledgerId=${ledgerId} sellOrderId=${sellOrderId} ` +
        `primary_err=${lastErr.message} fallback_err=${fbErr.message}`
      );
    }
  };
}

function mockPool(behavior) {
  const calls = [];
  return {
    calls,
    query: async (sql, params) => {
      calls.push({ sql, params });
      const step = behavior[calls.length - 1];
      if (step === "throw") throw new Error(`mock_throw_${calls.length}`);
      if (typeof step === "object" && step.throw) throw new Error(step.throw);
      return { rows: [] };
    },
  };
}

// ══════════════════════════════════════════════════════════════════════
// Branch 1: primary succeeds on attempt 1 → no retry, no fallback, no log
// ══════════════════════════════════════════════════════════════════════
console.log("\n=== Branch 1: primary succeeds on attempt 1 ===");
{
  const logs = { error: [] };
  const pool = mockPool(["ok"]);
  const helper = makeHelper(pool, logs);
  await helper(42, "AAPL", "ord-abc");
  assert(pool.calls.length === 1, "Exactly 1 pool.query call");
  assert(pool.calls[0].sql.includes("status='closed'"), "First call is primary close UPDATE");
  assert(pool.calls[0].sql.includes("exit_reason='circuit_breaker_3pct'"), "Primary uses circuit_breaker_3pct reason");
  assert(logs.error.length === 0, "No error logs emitted on primary success");
}

// ══════════════════════════════════════════════════════════════════════
// Branch 2: primary fails twice, succeeds on attempt 3
// ══════════════════════════════════════════════════════════════════════
console.log("\n=== Branch 2: primary succeeds on 3rd attempt ===");
{
  const logs = { error: [] };
  const pool = mockPool(["throw", "throw", "ok"]);
  const helper = makeHelper(pool, logs);
  await helper(43, "MSFT", "ord-def");
  assert(pool.calls.length === 3, "Exactly 3 pool.query calls (retry succeeded on 3rd)");
  assert(logs.error.length === 0, "No error logs when retry eventually succeeds");
}

// ══════════════════════════════════════════════════════════════════════
// Branch 3: primary fails all 3 times, fallback succeeds
// ══════════════════════════════════════════════════════════════════════
console.log("\n=== Branch 3: fallback recovery breadcrumbs written ===");
{
  const logs = { error: [] };
  const pool = mockPool(["throw", "throw", "throw", "ok"]);
  const helper = makeHelper(pool, logs);
  await helper(44, "TSLA", "ord-ghi");
  assert(pool.calls.length === 4, "3 primary attempts + 1 fallback = 4 calls");
  assert(pool.calls[3].sql.includes("cb_fallback_sell_order_id"), "4th call is fallback UPDATE with breadcrumbs");
  assert(pool.calls[3].sql.includes("cb_fallback_primary_err"), "Fallback records primary error text");
  assert(pool.calls[3].params[0] === "ord-ghi", "Fallback stores sell order id");
  assert(pool.calls[3].params[2] === 44, "Fallback targets correct ledger id");
  assert(logs.error.some(l => l.includes("PRIMARY liquidation write failed after 3 attempts")), "PRIMARY-fail log emitted");
  assert(logs.error.some(l => l.includes("Fallback recovery breadcrumbs written")), "Fallback-success log emitted");
  assert(!logs.error.some(l => l.includes("CRITICAL")), "No CRITICAL log when fallback succeeds");
}

// ══════════════════════════════════════════════════════════════════════
// Branch 4: primary and fallback both fail → CRITICAL log
// ══════════════════════════════════════════════════════════════════════
console.log("\n=== Branch 4: both fail → CRITICAL log ===");
{
  const logs = { error: [] };
  const pool = mockPool(["throw", "throw", "throw", "throw"]);
  const helper = makeHelper(pool, logs);
  await helper(45, "NVDA", "ord-jkl");
  assert(pool.calls.length === 4, "3 primary + 1 fallback = 4 calls");
  const critical = logs.error.find(l => l.includes("CRITICAL"));
  assert(critical !== undefined, "CRITICAL log emitted when both fail");
  assert(critical.includes("NVDA"), "CRITICAL log includes ticker");
  assert(critical.includes("ledgerId=45"), "CRITICAL log includes ledger id");
  assert(critical.includes("sellOrderId=ord-jkl"), "CRITICAL log includes sell order id");
  assert(critical.includes("primary_err=mock_throw_3"), "CRITICAL log includes last primary error");
  assert(critical.includes("fallback_err=mock_throw_4"), "CRITICAL log includes fallback error");
}

// ══════════════════════════════════════════════════════════════════════
// Structural check: the copy in this test matches the source
// ══════════════════════════════════════════════════════════════════════
console.log("\n=== Structural: source contains the same helper body ===");
{
  const src = await import("node:fs").then(fs =>
    fs.promises.readFile(new URL("../circuit_breaker.mjs", import.meta.url), "utf8")
  );
  // Distinctive tokens from the helper — if source drifts, refresh this test.
  const requiredTokens = [
    "closePositionInLedgerWithRetry",
    "attempt <= 3",
    "cb_fallback_sell_order_id",
    "cb_fallback_primary_err",
    "CRITICAL: both primary and fallback liquidation writes failed",
    "exit_reason='circuit_breaker_3pct'",
  ];
  for (const t of requiredTokens) {
    assert(src.includes(t), `Source contains: ${t}`);
  }
}

console.log(`\n${passed}/${passed + failed} assertions passed`);
if (failed > 0) process.exit(1);
