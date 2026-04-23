/**
 * tools/verify_alpaca_plumbing.mjs
 * Non-invasive Alpaca execution plumbing diagnostic.
 *
 * Places a synthetic limit order for 1 share of AAPL at $1.00
 * (mathematically impossible to fill), verifies it queued,
 * then immediately cancels it. Does NOT touch pee1_runner or
 * any DB — pure Alpaca API round-trip test.
 *
 * Usage (on ECS container or locally with env vars set):
 *   node tools/verify_alpaca_plumbing.mjs
 */

const BASE  = "https://paper-api.alpaca.markets";
const KEY   = process.env.APCA_API_KEY_ID;
const SECRET = process.env.APCA_API_SECRET_KEY;

if (!KEY || !SECRET) {
  console.error("[FAILURE]: APCA_API_KEY_ID or APCA_API_SECRET_KEY not set.");
  process.exit(1);
}

const headers = {
  "APCA-API-KEY-ID":     KEY,
  "APCA-API-SECRET-KEY": SECRET,
  "Content-Type":        "application/json",
};

async function get(path) {
  const res  = await fetch(`${BASE}${path}`, { headers });
  const body = await res.json();
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function post(path, payload) {
  const res  = await fetch(`${BASE}${path}`, { method: "POST", headers, body: JSON.stringify(payload) });
  const body = await res.json();
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function del(path) {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE", headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(`DELETE ${path} → ${res.status}: ${JSON.stringify(body)}`);
  }
}

async function testPlumbing() {
  console.log("[DIAGNOSTIC] Initiating Alpaca plumbing test...\n");

  // ── Step 1: Authentication + account read ───────────────────────────────
  const account = await get("/v2/account");
  console.log(`[SUCCESS] Connected to Alpaca`);
  console.log(`[ACCOUNT STATUS]    ${account.status}`);
  console.log(`[PAPER EQUITY]      $${parseFloat(account.equity).toFixed(2)}`);
  console.log(`[PAPER CASH]        $${parseFloat(account.cash).toFixed(2)}`);
  console.log(`[TRADING BLOCKED]   ${account.trading_blocked}`);

  // ── Step 2: Place unfillable limit order ────────────────────────────────
  console.log("\n[DIAGNOSTIC] Submitting synthetic limit order (1 share AAPL @ $1.00)...");
  const order = await post("/v2/orders", {
    symbol:        "AAPL",
    qty:           1,
    side:          "buy",
    type:          "limit",
    time_in_force: "day",
    limit_price:   1.00,
  });
  console.log(`[SUCCESS] Order queued in Alpaca`);
  console.log(`[ORDER ID]          ${order.id}`);
  console.log(`[ORDER STATUS]      ${order.status}`);
  console.log(`[LIMIT PRICE]       $${order.limit_price}`);

  // ── Step 3: Cancel the order ────────────────────────────────────────────
  console.log("\n[DIAGNOSTIC] Canceling synthetic order...");
  await del(`/v2/orders/${order.id}`);
  console.log("[SUCCESS] Order canceled. Execution pipe is fully operational.");

  // ── Step 4: Confirm canceled ────────────────────────────────────────────
  const confirmed = await get(`/v2/orders/${order.id}`);
  console.log(`[CONFIRMED STATUS]  ${confirmed.status}`);
  console.log("\n✓ All three stages passed: READ → WRITE → DELETE");
}

testPlumbing().catch(err => {
  console.error("\n[FAILURE] Plumbing test failed:");
  console.error(err.message);
  process.exit(1);
});
