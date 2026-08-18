import assert from "node:assert/strict";
import {
  calculateOpenBuyCommitment,
  fetchPaperEntryCustody,
  normalizeEntryAccount,
  requireFundedCapital,
  requirePaperExecutionMode,
} from "../broker_entry_custody.mjs";

assert.equal(requirePaperExecutionMode("paper"), "https://paper-api.alpaca.markets");
assert.throws(() => requirePaperExecutionMode("live"), /execution_mode_not_authorized:live/);
assert.throws(() => requirePaperExecutionMode(undefined), /execution_mode_not_authorized:missing/);
assert.equal(requireFundedCapital("100000"), 100000);
assert.throws(() => requireFundedCapital("0"), /vault_funded_amount_missing_or_invalid/);

const orders = [
  { side: "buy", symbol: "AAA", qty: "10", filled_qty: "2", limit_price: "12.50" },
  { side: "buy", symbol: "BBB", qty: "4", filled_qty: "0", stop_price: "20" },
  { side: "sell", symbol: "CCC", qty: "9", filled_qty: "0", limit_price: "50" },
];
assert.equal(calculateOpenBuyCommitment(orders), 180);
assert.throws(
  () => calculateOpenBuyCommitment([{ side: "buy", symbol: "UNPRICED", qty: "1", filled_qty: "0" }]),
  /open_buy_commitment_unpriced:UNPRICED/,
);

const state = normalizeEntryAccount(
  {
    cash: "30000",
    buying_power: "25000",
    long_market_value: "40000",
    short_market_value: "-7000",
    account_blocked: false,
    trading_blocked: false,
    trade_suspended_by_user: false,
  },
  orders,
  "100000",
);
assert.equal(state.cash, 25000);
assert.equal(state.grossMarketExposure, 47000);
assert.equal(state.openBuyCommitment, 180);
assert.equal(state.invested, 47180);
assert.equal(state.funded, 100000);
assert.throws(
  () => normalizeEntryAccount({ cash: "1", buying_power: "1", long_market_value: "0", short_market_value: "0", trading_blocked: true }, [], 100),
  /alpaca_account_entry_blocked/,
);

process.env.APCA_API_KEY_ID = "test-key";
process.env.APCA_API_SECRET_KEY = "test-secret";
const successfulFetch = async (url) => {
  if (String(url).endsWith("/v2/account")) {
    return new Response(JSON.stringify({
      cash: "5000",
      buying_power: "5000",
      long_market_value: "1000",
      short_market_value: "0",
      account_blocked: false,
      trading_blocked: false,
      trade_suspended_by_user: false,
    }), { status: 200 });
  }
  return new Response(JSON.stringify([]), { status: 200 });
};
const fetched = await fetchPaperEntryCustody({
  executionMode: "paper",
  fundedCapital: "10000",
  fetchImpl: successfulFetch,
});
assert.equal(fetched.invested, 1000);

await assert.rejects(
  fetchPaperEntryCustody({
    executionMode: "paper",
    fundedCapital: "10000",
    fetchImpl: async () => new Response(JSON.stringify({ message: "unavailable" }), { status: 503 }),
  }),
  /alpaca_http_503:unavailable/,
);

console.log("broker entry custody: all assertions passed");
