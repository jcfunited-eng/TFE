import assert from "node:assert/strict";

import {
  reconcileCustody,
  type AlpacaOpenOrder,
  type AlpacaPosition,
  type LedgerOpenPosition,
} from "../src/lib/alpaca-custody";


function ledger(id: number, ticker: string, status = "filled", shares = 10): LedgerOpenPosition {
  return {
    id,
    ticker,
    signal_class: "CH2",
    shares,
    entry_filled_price: status === "filled" ? "10" : null,
    dollar_allocation: "100",
    atr_14: null,
    spy_dk: 1,
    s_uf: "0.8",
    bar_count: 20,
    status,
    signal_detected_at: "2026-08-18T00:00:00Z",
    entry_filled_at: status === "filled" ? "2026-08-18T00:01:00Z" : null,
    alpaca_order_id: status === "filled" ? "filled-order" : "pending-order",
  };
}


function broker(symbol: string, quantity: number): AlpacaPosition {
  return {
    symbol,
    side: "long",
    quantity,
    averageEntryPrice: 10,
    currentPrice: 11,
    marketValue: 11 * quantity,
    unrealizedPnl: quantity,
    unrealizedPnlPct: 0.1,
  };
}


const union = reconcileCustody(
  [ledger(1, "MATCH")],
  [broker("MATCH", 10), broker("CWAN", 100), broker("HTBK", 67)],
  [],
);
assert.equal(union.summary.brokerPositions, 3);
assert.equal(union.summary.ledgerSymbols, 1);
assert.equal(union.summary.matched, 1);
assert.equal(union.summary.discrepancies, 2);
assert.deepEqual(
  union.positions.filter((position) => position.status === "broker_only").map((position) => position.ticker),
  ["CWAN", "HTBK"],
);
assert.equal(union.positions.find((position) => position.ticker === "CWAN")?.signal_class, "BROKER");

const unavailable = reconcileCustody([ledger(1, "MATCH")], null, null);
assert.equal(unavailable.positions[0].status, "broker_unavailable");
assert.equal(unavailable.summary.discrepancies, 0);
assert.equal(unavailable.summary.unknownBecauseBrokerUnavailable, 1);

const openOrders: AlpacaOpenOrder[] = [
  { id: "pending-order", symbol: "PEND", side: "buy", quantity: 10, filledQuantity: 0, status: "new" },
];
const pending = reconcileCustody([ledger(2, "PEND", "submitted")], [], openOrders);
assert.equal(pending.positions[0].status, "pending_order");
assert.equal(pending.summary.discrepancies, 0);

const mismatch = reconcileCustody([ledger(3, "MISMATCH", "filled", 10)], [broker("MISMATCH", 9)], []);
assert.equal(mismatch.positions[0].status, "quantity_mismatch");
assert.equal(mismatch.summary.discrepancies, 1);

const duplicates = reconcileCustody([ledger(4, "DUP"), ledger(5, "DUP")], [broker("DUP", 20)], []);
assert.equal(duplicates.positions[0].status, "duplicate_ledger");
assert.equal(duplicates.summary.discrepancies, 1);

console.log("alpaca custody reconciliation: 5 assertions groups passed");
